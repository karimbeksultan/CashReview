# Local visual review baseline

This implementation is an experimental candidate selector for human review. Its binary `violation` / `no_violation` API value is a learned dataset label, not a verified finding of wrongdoing. It does not identify people, interpret regulations or establish a particular cashier action. Operational readiness is separate from detection quality: the current public metadata has `quality_validated: false` and `validation_status: "failed_baseline"`.

## Representation and provenance

The frozen backbone is [ONNX Model Zoo MobileNetV2 opset 7](https://github.com/onnx/models/blob/main/validated/vision/classification/mobilenet/README.md). That model's own README identifies ImageNet training, RGB normalization, and Apache 2.0 licensing. Its repository's [Git LFS pointer](https://github.com/onnx/models/blob/main/validated/vision/classification/mobilenet/model/mobilenetv2-7.onnx) supplies SHA-256 `c1c513582d56afceff8516c73804e484c81c6a830712ab6d682253f4a3cd042f`, verified during preparation and loading. Preparation preserves the upstream [Apache 2.0 license](https://github.com/onnx/models/blob/main/LICENSE) next to the private weights.

OpenCV DNN executes the frozen 1,000 ImageNet output logits on CPU as a generic visual representation. The explicit final graph output is used for consistency across OpenCV graph engines. Input is resized to 224×224, converted BGR→RGB, scaled to `[0,1]`, then normalized by ImageNet means `[0.485,0.456,0.406]` and standard deviations `[0.229,0.224,0.225]`. The representation is L2-normalized. A 4×4 spatial grid adds grayscale means and differences from the preceding sampled frame, giving 1,032 features. This is a generic appearance/motion representation, not a cash or hand detector.

A standard scaler and L2 logistic classifier are fitted locally. Fixed classifier regularization `C=0.1` precedes evaluation. Learned artifacts use JSON and numeric NPZ loaded with `allow_pickle=False`; the runtime does not unpickle models. Artifacts and source features stay private and are excluded from the repository.

## Data and split

The supplied archive has 42 labelled videos, 22 positive and 20 negative. Exact SHA-256 grouping yields 40 unique clips: 21 positive and 19 negative. Two exact duplicate pairs stay in the same partition. One positive pair has different 57/68-second annotations; both timestamps are retained as ambiguous alternatives rather than silently corrected. The workbook provides isolated timestamps and binary labels, not exhaustive event intervals or event types.

The preparation script freezes a class-stratified approximately 60/20/20 split with seed `26017`. The private `split.json` records every content hash and assignment and rejects a changed dataset fingerprint on reuse. The scaler and classifier use training groups only. Positive training examples come from ±2-second neighborhoods of supplied timestamps; unannotated portions of positive videos are not used as known negatives. Negative clips provide normal examples. Sample weights give each clip and each class equal total influence, regardless of duration. Validation video F1 chooses the threshold; ties use balanced accuracy, then the higher threshold. Test labels and predictions do not alter model parameters, threshold, preprocessing, or split.

Exact grouping alone does not resolve possible near duplicates, actor/session overlap, or the shared camera setting. The small held-out set cannot establish alternate-angle performance. The original test was inspected during V1 evaluation; any later reuse is exploratory and cannot become a fresh holdout.

## Inference and timing

The runtime reads pixels from a new local video, without consulting filenames, dataset hashes, source annotations, or known clip identity. It samples at one second, scores all samples, suppresses peaks less than eight seconds apart, and retains at most three candidates. A bounded ±1-second refinement searches at 0.25-second steps. Each candidate includes three real JPEG source frames around its selected time. The service never downloads a model or calls a remote AI service.

OpenCV `CAP_PROP_POS_MSEC` provides presentation times after decode/seek. If unavailable/non-monotonic during sequential extraction, the fallback is frame index divided by nominal frame rate and a warning is returned. Duration uses frame count divided by reported frame rate, checked against the final timestamp. This is adequate for the supplied constant-rate clips but does not validate all variable-rate inputs or QuickTime edit lists. Evidence must be independently checked for unusual inputs. A hard monotonic deadline is checked during decode, feature extraction, refinement and JPEG encoding; the worker additionally enforces its process deadline.

Header dimensions are checked before the first explicit decode; actual dimensions are checked after every decoded frame. Defaults reject dimensions above 4,096 on either side or 8,000,000 pixels. `CASH_REVIEW_MAX_MODEL_DIMENSION` and `CASH_REVIEW_MAX_MODEL_PIXELS` configure those bounds, with a floor that supports 1080p. Evidence JPEGs now retain native resolution up to a 1,280-pixel maximum side at quality 88. `CASH_REVIEW_EVIDENCE_MAX_SIDE` configures a bounded 640–1,920-pixel limit; source images are never enlarged. This preserves the supplied 464×848 recordings instead of reducing them to 350×640. Native `VideoCapture` container opening happens before Python can inspect header dimensions. These checks do not provide a complete decoder resource guarantee on Windows; the isolated worker process and hard process deadline mitigate native hangs and permit termination.

## Meaning of results

Events have type `visual_review_signal` and context rule `CR-001`. Their description explicitly states that the concrete action and regulatory violation are unestablished. Classifier scores are uncalibrated and should not be shown as a percentage likelihood of wrongdoing. A negative result means no baseline signal crossed its threshold; it does not certify compliance. One-second sampling and three-candidate limits can miss events. Source timestamps are not complete event truth, so the evaluation does not claim event precision/recall or typed event accuracy.

The browser abstains from a binary assessment unless the completed job's own metadata contains both `quality_validated: true` and `validation_status: "validated"`. The current baseline therefore displays **Human review required** for either raw verdict. Candidate moments, scores and the immutable API result remain available. This reduces misleading presentation; it does not reduce the classifier's measured false-positive rate.

Reviewers can save an independent human decision and notes for a completed job. These records never change the model result, provide a source-label lookup, or automatically enter training. The source-label comparison has been removed from the runtime.

## Reproduction

Use the backend's pinned runtime dependencies plus `scikit-learn` and `openpyxl` for training. From the repository root, with a Python environment activated:

```powershell
python backend/scripts/prepare_model.py --model-dir PRIVATE_MODEL_DIR
python backend/scripts/train_baseline.py --data-dir PRIVATE_OPEN_DIR --model-dir PRIVATE_MODEL_DIR
python backend/scripts/evaluate.py --model-dir PRIVATE_MODEL_DIR --runtime-smoke
$env:CASH_REVIEW_MODEL_DIR = 'ABSOLUTE_PRIVATE_MODEL_DIR'
```

`PRIVATE_OPEN_DIR` contains `open_labels.xlsx` and `videos/`. Only preparation downloads the official public weights/license. Training and service inference work without internet after dependencies and weights are prepared. Do not commit source videos, labels, feature caches, split manifests, training artifacts, runtime uploads, or private per-clip evaluation output. `evaluation_aggregate.json` is the aggregate report; `evaluation_private.json` contains clip-level records and stays private.

## Measured evaluation

Version `mobilenetv2-local-review-v1-efda07f878` was trained on 24 unique groups (513 timestamp/normal samples), selected its threshold on 8 validation groups, and was evaluated on 8 frozen test groups: 4 positive and 4 negative. All 8 completed. Its confusion matrix, with negative/positive true rows and predicted columns, was `[[0,4],[0,4]]`: **every test video was flagged positive**. This baseline fails to discriminate normal clips and is unsuitable for reliable automatic review.

| V1 diagnostic | Measured result |
| --- | --- |
| Completed / submitted | 8 / 8 |
| Precision | 0.50 |
| Recall | 1.00 |
| Specificity | 0.00 |
| F1 | 0.667; this must not be advertised without the all-positive failure |
| Accuracy over every submitted test | 0.50 |
| Accuracy 95% Wilson interval | 0.215–0.785 |
| Positive test clips with a candidate within 5 seconds of any supplied timestamp | 3 / 4; incomplete annotation diagnostic only |
| Event precision/recall and event-type accuracy | Not measurable from the supplied incomplete/type-free labels |

A second, separately versioned design was attempted after viewing the failed V1 result. It adds a video-level gate using pooled `[mean,std,max,q90]` frozen features and a balanced logistic classifier with fixed `C=0.1`. Only the original 24 training groups fit the gate; the 8 validation groups choose its threshold using balanced accuracy, then precision, then F1. Test features were not inspected for this attempt. Validation balanced accuracy was **0.375**, with confusion matrix `[[1,3],[2,2]]`. The preparation script refused promotion because it did not exceed 0.5. No V2 runtime artifacts were produced and no V2 test evaluation was run. V1's failed artifacts/report and the frozen split were preserved. The optional `--model-kind video-gated` path remains available for a future, properly validated dataset revision. Any future V2 evaluation on the existing test partition is explicitly marked `exploratory_previously_seen_test`, because it cannot constitute a fresh unseen test.

Direct V1 engine checks after dimension checks and bounded evidence generation completed in 12.125 seconds for a 71.6-second negative source clip, 7.343 seconds for a 25.933-second positive source clip, and 35.735 seconds for the longest 142.533-second source clip. All three were predicted positive, and all 12 returned JPEGs decoded successfully, stayed within source time bounds, and had a maximum side of 640 pixels. These are functional/runtime checks, not detection successes. They exclude upload, queueing, subprocess startup and API polling and do not establish the 300-second end-to-end deadline.

The measured environment was Windows 11, Intel64 Family 6 Model 142 Stepping 12 CPU, 8 logical CPUs, OpenCV 5.0.0, NumPy 2.5.4, scikit-learn 1.9.1, with 2 requested OpenCV threads and CPU DNN execution. Native thread scheduling and other concurrent processes affect latency. Source videos, derived features, split IDs, learned arrays and per-clip output remain private; only these aggregate diagnostics belong in the public repository.

## Remaining qualification work

Additional local feature and temporal studies were trained and rejected; see [model studies](model_studies.md). Their development results are kept separate from the original V1 test and do not replace it with a claimed successful detector.

Review event semantics and complete interval/type annotations; implement and validate an observable event taxonomy; verify near-duplicate/session grouping; measure alternate-camera and lighting/occlusion robustness; evaluate all submitted jobs including failures; validate applicable rules; and measure upload-to-result latency on the intended local deployment. The generic baseline is a working engineering starting point with material model limitations.
