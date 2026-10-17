"""Experimental local DINO study; explicit paths, no test mode or remote inference."""
from __future__ import annotations
import argparse, functools, hashlib, importlib.metadata, json, os, platform, sys, threading, time
from pathlib import Path

CODE_DIR=Path(__file__).resolve().parent
ROOT: Path
MODEL_DIR: Path
SPLIT_PATH: Path
DATA_DIR: Path
import manifest_io
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
                  TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
SEED=26017

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 temp=p.with_suffix(p.suffix+'.partial');temp.write_text(json.dumps(v,indent=2),encoding='utf-8');os.replace(temp,p)
@functools.lru_cache(maxsize=1)
def runtime():
 return {'python':platform.python_version(),'packages':{n:importlib.metadata.version(n) for n in ('torch','transformers','numpy','Pillow','scikit-learn','opencv-python-headless','safetensors')}}
def binding():
 return {**{k:sha(p) for k,p in {'policy':CODE_DIR/'policy.json','code':Path(__file__),'manifest_io':CODE_DIR/'manifest_io.py','source_receipt':CODE_DIR/'source_receipt.json','split':SPLIT_PATH,'assets':MODEL_DIR/'provenance.json'}.items()},'runtime':runtime()}
def freeze():
 if (ROOT/'freeze.json').exists():raise ValueError('Study freeze already exists')
 save(ROOT/'freeze.json',{'bindings':binding(),'utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'source_inputs_processed':0})
 print(json.dumps({'frozen':True,'source_inputs_processed':0}),flush=True)
def require_freeze():
 if read(ROOT/'freeze.json')['bindings']!=binding():raise ValueError('Locally frozen study changed')
def require_training_freeze():
 f=read(ROOT/'training_freeze.json')
 if f!={'bindings':binding(),'selection':sha(ROOT/'selection.json'),'oof':sha(ROOT/'private_oof.npz')}:raise ValueError('Training selection freeze changed')
 if not read(ROOT/'selection.json')['training_gate_passed']:raise ValueError('Training gate failed')
def groups(phase):
 return manifest_io.groups(SPLIT_PATH,DATA_DIR,phase)
def unit(x):
 import numpy as np
 return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-8)
def load_model():
 import torch
 from transformers import Dinov2Model
 torch.set_num_threads(2);torch.set_num_interop_threads(1)
 torch.manual_seed(SEED)
 model,info=Dinov2Model.from_pretrained(str(MODEL_DIR),local_files_only=True,use_safetensors=True,output_loading_info=True,attn_implementation='sdpa')
 if any(info.get(k) for k in ('missing_keys','unexpected_keys','mismatched_keys','error_msgs')):raise ValueError('Incomplete weights')
 model.eval()
 return torch,model
def single_tile(image,torch,model):
 import numpy as np
 from PIL import Image
 a=np.asarray(image.resize((224,224),resample=Image.Resampling.BILINEAR),dtype=np.float32)/255
 a=(a-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)
 with torch.inference_mode():h=model(pixel_values=torch.from_numpy(a.transpose(2,0,1).copy())[None]).last_hidden_state.numpy()[0]
 if h.shape!=(257,384) or not np.isfinite(h).all():raise ValueError('Invalid embedding')
 cells=h[1:].reshape(4,4,4,4,384).mean((1,3)).reshape(16,384)
 return unit(h[:1]).astype(np.float32),unit(cells).astype(np.float32)
def embedding(image,torch,model):
 import math,numpy as np
 w,h=image.size
 tiles=[image.crop((0,0,w,math.ceil(.6*h))),image.crop((0,math.floor(.4*h),w,h))]
 pairs=[single_tile(tile,torch,model) for tile in tiles]
 return np.concatenate([x[0] for x in pairs]),np.concatenate([x[1] for x in pairs])
def verify_assets():
 p=manifest_io.verify_model(MODEL_DIR)
 # Actual asset names/digests supplied by the preparation receipt.
 records=p.get('files',{})
 if not records:raise ValueError('Missing asset digests')
 for name,v in records.items():
  expected=v if isinstance(v,str) else v['sha256']
  if sha(MODEL_DIR/name)!=expected:raise ValueError('Asset integrity mismatch')
 return p
def probe():
 import numpy as np
 from PIL import Image,ImageDraw
 require_freeze();verify_assets();started=time.perf_counter();print(json.dumps({'stage':'synthetic_model_loading','source_inputs':0}),flush=True);torch,model=load_model();lat=[];loadtime=time.perf_counter()-started
 for i in range(12):
  im=Image.new('RGB',(464,848),(60,60,65));ImageDraw.Draw(im).rectangle((70+i*5,200,300,500),fill=(150,120,90))
  t=time.perf_counter();embedding(im,torch,model);lat.append(time.perf_counter()-t)
 result={'synthetic_only':True,'case_inputs':0,'frames':12,'encoder_calls':24,'seconds':time.perf_counter()-started,'cold_import_and_model_load_seconds':loadtime,'median_infer_seconds':float(np.median(lat)),'estimated74_frames_seconds':float(np.median(lat)*74),'bindings':binding()}
 save(ROOT/'probe.json',result);print(json.dumps(public_summary(result)),flush=True)
def extract(phase):
 import numpy as np,cv2
 from PIL import Image
 require_freeze();verify_assets()
 probe=read(ROOT/'probe.json')
 estimated=probe['estimated74_frames_seconds']+probe['cold_import_and_model_load_seconds']
 if probe['bindings']!=binding() or probe['synthetic_only'] is not True or probe['case_inputs']!=0 or probe['frames']!=12 or probe['encoder_calls']!=24 or not np.isfinite(estimated) or estimated>=240:raise ValueError('Feasibility gate failed')
 if phase=='validation':require_training_freeze()
 rows=groups(phase);ledger=ROOT/(phase+'_extraction.json');outcomes=[]
 if ledger.exists():
  old=read(ledger)
  if old.get('bindings')!=binding() or old.get('expected')!=len(rows) or old.get('attempted')!=len(old['outcomes']):raise ValueError('Inconsistent extraction ledger')
  outcomes=old['outcomes']
  if any(o['state']!='done' for o in outcomes) or len(outcomes)>len(rows):raise ValueError('Failed/unreconciled attempt; no implicit retry')
 print(json.dumps({'stage':'source_extraction_model_loading','phase':phase,'previous_complete':len(outcomes)}),flush=True)
 torch,model=load_model();cv2.setNumThreads(2)
 targetdir=ROOT/'features';targetdir.mkdir(exist_ok=True)
 for i,g in enumerate(rows):
  target=targetdir/(g['sha256']+'.npz')
  if i<len(outcomes):
   load(g,'global')
   continue
  if target.exists():raise ValueError('Unledgered cache; no implicit recovery')
  lock=threading.Lock();attempt={'state':'started'};outcomes.append(attempt)
  def persist():save(ledger,{'expected':len(rows),'attempted':len(outcomes),'outcomes':outcomes,'bindings':binding()})
  persist()
  def hard_timeout():
   with lock:
    if attempt['state']!='started':return
    attempt.update(state='failed',error_type='HardTimeout295s')
    try:persist()
    finally:os._exit(124)
  start=time.perf_counter();timer=threading.Timer(295,hard_timeout);timer.daemon=True;timer.start();cap=None
  try:
   if sha(g['path'])!=g['sha256']:raise ValueError('Source digest changed')
   cap=cv2.VideoCapture(g['path'])
   if not cap.isOpened():raise ValueError('Decoder failed')
   fps=cap.get(cv2.CAP_PROP_FPS);n=cap.get(cv2.CAP_PROP_FRAME_COUNT)
   w,h=cap.get(cv2.CAP_PROP_FRAME_WIDTH),cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
   if not np.isfinite([fps,n,w,h]).all() or min(fps,n,w,h)<=0 or n/fps>146 or max(w,h)>4096 or w*h>8e6:raise ValueError('Media bound')
   times=[];cls=[];patch=[];nextsample=0.;origin=None;previous=-1.
   while cap.grab():
    pts=cap.get(cv2.CAP_PROP_POS_MSEC)/1000.
    if origin is None:origin=pts
    pts-=origin
    if not np.isfinite(pts) or pts<previous-.0001:raise ValueError('Nonmonotonic timing')
    previous=pts
    if pts+.0001<nextsample:continue
    good,frame=cap.retrieve()
    if not good or frame is None or frame.ndim!=3:raise ValueError('Decode failed')
    if max(frame.shape[:2])>4096 or frame.shape[0]*frame.shape[1]>8e6:raise ValueError('Decoded dimensions')
    c,p=embedding(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)),torch,model)
    times.append(pts);cls.append(c);patch.append(p);nextsample+=2
    if len(times)>74:raise ValueError('Sample bound')
   if not times or previous<n/fps-2:raise ValueError('Incomplete decode')
   elapsed=time.perf_counter()-start
   np.savez_compressed(target,global_features=np.stack(cls),patch_features=np.stack(patch),times=np.asarray(times),raw_pts_sec=np.asarray(times)+origin,pts_origin_sec=origin,fps=fps,duration_sec=n/fps,last_relative_pts=previous,source_sha256=g['sha256'],seconds=elapsed,binding=json.dumps(binding(),sort_keys=True))
   mp=ROOT/'cache_manifest.json';manifest=read(mp) if mp.exists() else {}
   manifest[g['sha256']]=sha(target);save(mp,manifest)
   with lock:attempt.update(state='done',seconds=elapsed,samples=len(times));persist()
  except Exception as e:
   with lock:attempt.update(state='failed',error_type=type(e).__name__);persist()
   print(json.dumps({'phase':phase,'processed':len(outcomes),'state':'failed','error_type':type(e).__name__}),flush=True)
   raise SystemExit(1)
  finally:
   if cap is not None:cap.release()
   timer.cancel()
  print(json.dumps({'phase':phase,'processed':i+1,'expected':len(rows),'seconds':round(elapsed,3),'state':'done'}),flush=True)
def load(group,view):
 import numpy as np
 target=ROOT/'features'/(group['sha256']+'.npz')
 if sha(target)!=read(ROOT/'cache_manifest.json').get(group['sha256']):raise ValueError('Cache integrity differs')
 with np.load(target,allow_pickle=False) as d:
  if str(d['binding'])!=json.dumps(binding(),sort_keys=True):raise ValueError('Binding differs')
  if str(d['source_sha256'])!=group['sha256']:raise ValueError('Cache source mismatch')
  n=len(d['times'])
  if not 1<=n<=74 or d['global_features'].shape!=(n,2,384) or d['patch_features'].shape!=(n,32,384) or d['raw_pts_sec'].shape!=(n,):raise ValueError('Cache shape differs')
  for key in ('global_features','patch_features','times','raw_pts_sec','pts_origin_sec','fps','duration_sec','last_relative_pts','seconds'):
   if not np.isfinite(d[key]).all():raise ValueError('Cache nonfinite')
  for key in ('global_features','patch_features'):
   if d[key].dtype!=np.float32 or not np.allclose(np.linalg.norm(d[key],axis=-1),1,atol=2e-4):raise ValueError('Cache vector norm')
  if d['times'].ndim!=1 or np.any(np.diff(d['times'])<=0) or d['times'][0]<0 or d['times'][-1]>float(d['duration_sec'])+.1 or float(d['fps'])<=0:raise ValueError('Cache timing differs')
  if not np.allclose(d['raw_pts_sec']-d['pts_origin_sec'],d['times'],atol=1e-7):raise ValueError('Cache source PTS differs')
  x=d['global_features' if view=='global' else 'patch_features'].copy();times=d['times'].copy()
 if view=='centered_patch':x=unit(x-np.median(x,axis=0,keepdims=True))
 return x,times
def memory(rows,view):
 import numpy as np
 a=[[],[]]
 for g in rows:
  x,t=load(g,view);label=int(g['positive'])
  idx=np.arange(len(t))
  if label:idx=idx[np.min(np.abs(t[:,None]-np.array(g['timestamps'])[None,:]),axis=1)<=2.001]
  if not len(idx):raise ValueError('No eligible sample')
  idx=idx[np.unique(np.linspace(0,len(idx)-1,min(8 if label else 16,len(idx))).round().astype(int))]
  a[label].append(x[idx])
 return tuple(np.concatenate(v) for v in a)
def frame_scores(x,mem,kind):
 import numpy as np
 normal,positive=mem
 n=np.einsum('icd,jcd->cij',x,normal,optimize=True).max(axis=2).T
 s=1-n
 if kind=='positive_normal_margin':s=np.einsum('icd,jcd->cij',x,positive,optimize=True).max(axis=2).T-n
 s=np.where(np.linalg.norm(x,axis=-1)<1e-8,0. if kind=='normal_novelty' else -2.,s)
 k=min(4,s.shape[1]);return np.sort(s,axis=1)[:,-k:].mean(axis=1)
def aggregate(scores,method):
 import numpy as np
 if method=='quantile90':return float(np.quantile(scores,.9,method='linear'))
 if method!='adjacent2_mean_maximum':raise ValueError('Unknown aggregation')
 return float(scores[0]) if len(scores)<2 else float(np.max((scores[:-1]+scores[1:])/2))
def metrics(y,s,t):
 import numpy as np
 y=np.asarray(y,dtype=bool);p=np.asarray(s)>=t
 tn,fp,fn,tp=map(int,[(~y&~p).sum(),(~y&p).sum(),(y&~p).sum(),(y&p).sum()]);r=tp/(tp+fn);sp=tn/(tn+fp)
 return {'tn':tn,'fp':fp,'fn':fn,'tp':tp,'specificity':sp,'recall':r,'balanced_accuracy':(sp+r)/2,'precision':tp/max(tp+fp,1)}
def choose_threshold(y,s):
 import numpy as np
 options=[]
 for t in np.unique(s):
  m=metrics(y,s,t)
  if m['specificity']>=.8 and m['recall']>=.5 and m['balanced_accuracy']>=.65:options.append((float(t),m))
 return max(options,key=lambda q:(q[1]['balanced_accuracy'],q[1]['precision'],q[1]['specificity'],q[0])) if options else None
def train():
 import numpy as np
 from sklearn.model_selection import StratifiedKFold
 from sklearn.metrics import roc_auc_score
 require_freeze()
 if (ROOT/'selection.json').exists():raise ValueError('Preserve completed selection')
 rows=groups('train');y=np.array([int(g['positive']) for g in rows]);cv=list(StratifiedKFold(4,shuffle=True,random_state=SEED).split(y,y));candidates=[];private=[]
 for view in ('global','patch','centered_patch'):
  allx=[load(g,view)[0] for g in rows]
  for kind in ('normal_novelty','positive_normal_margin'):
   oofs={agg:np.full(len(rows),np.nan) for agg in ('quantile90','adjacent2_mean_maximum')}
   for tr,va in cv:
    mem=memory([rows[j] for j in tr],view)
    for j in va:
     s=frame_scores(allx[j],mem,kind)
     for agg in oofs:oofs[agg][j]=aggregate(s,agg)
   for agg,s in oofs.items():
    if not np.isfinite(s).all():raise ValueError('Missing heldout score')
    op=choose_threshold(y,s)
    c={'view':view,'scorer':kind,'aggregation':agg,'auc':float(roc_auc_score(y,s)),'pauc':float(roc_auc_score(y,s,max_fpr=.25)),'threshold':op[0] if op else None,'operating':op[1] if op else None}
    candidates.append(c);private.append(s)
    print(json.dumps({'candidate_completed':len(candidates),'auc':c['auc'],'pauc':c['pauc'],'eligible_threshold':bool(op)}),flush=True)
 selected=max(range(len(candidates)),key=lambda i:(candidates[i]['pauc'],candidates[i]['auc'],-i));c=candidates[selected]
 passed=c['auc']>.6 and c['pauc']>.5 and c['threshold'] is not None
 result={'bindings':binding(),'train_n':len(rows),'candidates':candidates,'selected_index':selected,'selected':c,'training_gate_passed':passed,'selection_evaluated':0,'test_evaluated':0,'quality_validated':False,'promoted':False}
 np.savez_compressed(ROOT/'private_oof.npz',labels=y,scores=np.stack(private))
 save(ROOT/'selection.json',result)
 save(ROOT/'training_freeze.json',{'bindings':binding(),'selection':sha(ROOT/'selection.json'),'oof':sha(ROOT/'private_oof.npz')})
 print(json.dumps({'training_gate_passed':passed,'selected':c,'selection_evaluated':0,'test_evaluated':0}),flush=True)
def evaluate():
 import numpy as np
 from sklearn.metrics import roc_auc_score
 require_freeze();require_training_freeze();frozen=read(ROOT/'selection.json')
 if not frozen['training_gate_passed'] or frozen['bindings']!=binding():raise ValueError('Training qualification failed')
 if (ROOT/'development.json').exists():raise ValueError('Do not repeat development evaluation')
 c=frozen['selected'];mem=memory(groups('train'),c['view']);rows=groups('validation');scores=[]
 for g in rows:scores.append(aggregate(frame_scores(load(g,c['view'])[0],mem,c['scorer']),c['aggregation']))
 y=np.array([int(g['positive']) for g in rows]);m=metrics(y,scores,c['threshold']);passed=m['specificity']>=.75 and m['recall']>=.75 and m['balanced_accuracy']>=.75
 result={'groups':len(rows),'frozen_train_threshold':c['threshold'],'metrics':m,'auc':float(roc_auc_score(y,scores)),'development_gate_passed':passed,'quality_validated':False,'scope':'reused exposed selection; not independent generalization evidence','test_evaluated':0,'bindings':binding()}
 np.savez_compressed(ROOT/'private_development.npz',labels=y,scores=scores)
 save(ROOT/'development.json',result);print(json.dumps(public_summary(result)),flush=True)

def public_summary(result):
 # Binding hashes remain in PRIVATE run records, never console/public summaries.
 return {k:v for k,v in result.items() if k!='bindings'}

def configure(args):
 global ROOT,MODEL_DIR,SPLIT_PATH,DATA_DIR
 ROOT=args.run_dir.resolve();MODEL_DIR=args.model_dir.resolve()
 SPLIT_PATH=args.split.resolve();DATA_DIR=args.data_dir.resolve()
 if not MODEL_DIR.is_dir() or not DATA_DIR.is_dir() or not SPLIT_PATH.is_file():raise ValueError('Required local inputs missing')
 if ROOT==CODE_DIR or CODE_DIR in ROOT.parents or ROOT==DATA_DIR or ROOT==MODEL_DIR or DATA_DIR in ROOT.parents or MODEL_DIR in ROOT.parents:raise ValueError('Use a separate private run directory')
 # Validate metadata and relocation only: no source bytes or pixels are read here.
 manifest_io.groups(SPLIT_PATH,DATA_DIR,'train')
 manifest_io.groups(SPLIT_PATH,DATA_DIR,'validation')
 if args.mode=='freeze' and ROOT.exists() and any(ROOT.iterdir()):raise ValueError('Freeze requires an empty private run directory')
 if args.mode!='audit':ROOT.mkdir(parents=True,exist_ok=True)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('mode',choices=('audit','freeze','probe','extract-train','train','extract-validation','evaluate'))
 p.add_argument('--model-dir',type=Path,required=True)
 p.add_argument('--split',type=Path,required=True)
 p.add_argument('--run-dir',type=Path,required=True)
 p.add_argument('--data-dir',type=Path,required=True)
 p.add_argument('--execute',action='store_true',help='Explicitly authorize a local research phase; coordinate RAM first')
 a=p.parse_args()
 if a.mode not in ('audit','freeze') and not a.execute:p.error('Research phases require --execute')
 try:
  with manifest_io.quiet_dependency_stderr():
   configure(a)
   if a.mode=='audit':
    verify_assets()
    print(json.dumps({'metadata_valid':True,'train_groups':len(groups('train')),'selection_groups':len(groups('validation')),'source_media_reads':0,'neural_loads':0}),flush=True)
   elif a.mode=='freeze':freeze()
   elif a.mode=='probe':probe()
   elif a.mode.startswith('extract'):extract('train' if a.mode=='extract-train' else 'validation')
   elif a.mode=='train':train()
   else:evaluate()
 except KeyboardInterrupt:
  print(json.dumps({'state':'failed','error_type':'Interrupted'}),flush=True);return 130
 except Exception as e:
  # Do not echo private file paths, identifiers, model messages or tracebacks.
  print(json.dumps({'state':'failed','error_type':type(e).__name__}),flush=True);return 1
 return 0

if __name__=='__main__':
 raise SystemExit(main())
