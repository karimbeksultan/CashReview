# Experimental DINO local-memory workflow

The original 12-candidate study was rejected by its training gate. This is an experimental source-only reproduction workflow, with no application integration. This copy has not processed source media, loaded a neural model or rerun the study. It preserves the original fixed numerical method; portability and synthetic tests do not establish model quality.

Every data, model, split and output location is explicit. Keep the run directory private: it contains content hashes, caches, split bindings and prediction arrays. The console prints aggregate progress and metrics only. No test-processing command exists. There is no remote inference, runtime download, automatic feedback learning or application adapter.

## Local preparation

Use a separate environment with `requirements-research.txt`; the original experiment used the CPU Torch wheel. On platforms where the generic PyPI Torch wheel is unsuitable, obtain the matching official CPU wheel before installing the other pinned requirements. No preexisting private `.pth` path injection is required by this copy.

`MODEL_DIR` must contain the four pinned public assets and three licence/context files listed in `provenance.example.json`, plus that file copied as `provenance.json` after obtaining the assets. Use only the base model, not XRay/Cell variants. Existing verified assets can be reused by pointing to their directory. For an independent preparation, the four Hugging Face assets can be fetched with:

```sh
hf download facebook/dinov2-small config.json preprocessor_config.json README.md model.safetensors --revision ed25f3a31f01632728cabb09d1542f84ab7b0056 --local-dir "$MODEL_DIR" --max-workers 2
```

The three small upstream files have exact commit-pinned official URLs in the example provenance. Download those public files to their listed names and retain their notices. `audit` verifies every byte digest and official revision offline, without importing Torch or reading source media. The combined asset inventory is below150MB. [Official model](https://huggingface.co/facebook/dinov2-small/tree/ed25f3a31f01632728cabb09d1542f84ab7b0056), [base code/weight licence](https://github.com/facebookresearch/dinov2).

## Split and private paths

Supply an already frozen JSON split, with `source` records containing `sha256`, `path`, boolean `positive`, and numeric nonnegative `timestamps`, plus `assignments` mapping every unique content digest to `train`, `validation` or reserved `test`. This workflow does not create or reshuffle a split. Duplicate bytes must already be combined into one group with all ambiguous positive anchors retained. Four-fold training requires at least four groups per class; validation needs both classes. Counts come from the manifest and do not need to equal the historical24/8 cohort.

`DATA_DIR/videos/` contains the local recordings. A legacy source path is relocated by its exact final Unicode filename into that directory; its old absolute location is never read. Different content groups cannot share a filename. Symlinks escaping the media root are rejected. Labels, timestamps and source digests are research supervision/integrity metadata only, never predictor coordinates or serving lookups.

## Fresh-process phases

```sh
python workflow.py audit --model-dir "$MODEL_DIR" --split "$SPLIT" --run-dir "$RUN_DIR" --data-dir "$DATA_DIR"
python workflow.py freeze --model-dir "$MODEL_DIR" --split "$SPLIT" --run-dir "$RUN_DIR" --data-dir "$DATA_DIR"
python workflow.py probe --model-dir "$MODEL_DIR" --split "$SPLIT" --run-dir "$RUN_DIR" --data-dir "$DATA_DIR" --execute
python workflow.py extract-train --model-dir "$MODEL_DIR" --split "$SPLIT" --run-dir "$RUN_DIR" --data-dir "$DATA_DIR" --execute
python workflow.py train --model-dir "$MODEL_DIR" --split "$SPLIT" --run-dir "$RUN_DIR" --data-dir "$DATA_DIR" --execute
# Continue only if training_gate_passed is true:
python workflow.py extract-validation --model-dir "$MODEL_DIR" --split "$SPLIT" --run-dir "$RUN_DIR" --data-dir "$DATA_DIR" --execute
python workflow.py evaluate --model-dir "$MODEL_DIR" --split "$SPLIT" --run-dir "$RUN_DIR" --data-dir "$DATA_DIR" --execute
```

Coordinate RAM before any `--execute` phase. Use a fresh process for each phase so CPU inter-op thread setup occurs once. `freeze` requires a fresh empty run directory. `audit` does not create the run directory or decode media. Code, policy, manifest I/O, source receipt, split, public asset provenance and metadata-only runtime versions bind the run. An input/code/environment change requires a new run. The original study's caches or freeze are never silently imported into this port. The source receipt links numerical-function AST hashes to the frozen original; the portable run has its own explicitly different contract.

The extraction ledger preserves every started/completed/failed attempt and forbids silent retry. It permits continuation after completely committed groups only. Cache files have SHA256 manifests, safe NPZ loading, float32 shape/norm/finite checks, and raw/source-origin timestamp consistency checks. The 295-second watchdog is per clip after model loading; the synthetic feasibility receipt includes cold load plus estimated74-frame work but is not a complete service benchmark. Queue/upload/evidence/network latency must be measured separately before integration.

## Preserved numerical policy

- Sample the entire input every2seconds at normalized source PTS; maximum146seconds and74samples. No label-based frame extraction.
- Fixed crops, in order: full width, y`[0:ceil(.6H)]`; full width, y`[floor(.4H):H]`. Each becomes RGB224×224 with PIL BILINEAR, float32/255 and ImageNet normalization. This differs from the official resize/crop recipe.
- Frozen DINOv2-small produces two384D CLS vectors and32same-cell patch vectors (16pooled cells per tile). Normalize each. The centered view subtracts each clip's temporal median, then normalizes; it never fits across videos.
- In each fitting fold, normal groups contribute up to16uniform rows; positive groups up to8uniform rows within2.001seconds of sparse positive anchors. Remaining positive times stay unknown.
- Score same-cell cosine novelty or positive-minus-normal nearest similarity. Zero query cells have the frozen minimum-signal convention: novelty0, margin−2. Average the largest4cells, or both CLS positions. Pool time by linear90th percentile or maximum adjacent-two mean.
- Twelve candidates, four fixed stratified content-group folds (seed26017). Rank standardized partialAUC atFPR.25, then ROC-AUC, then declaration order. No held-out group enters its prototype memory.
- OOF threshold requires specificity≥.8, recall≥.5, BA≥.65; maximize BA, precision, specificity, then higher threshold. Training gate additionally needs AUC>.6 and partialAUC>.5. Selection applies the unchanged candidate/threshold once, requiring specificity, recall and BA≥.75. No post-outcome tuning.

Reused selection data provides exploratory support only. Source labels do not provide complete event intervals/types. This workflow does not establish legal claims, identity, precise event localization, new-camera generalization or a release-ready detector.

## Media-free checks

```sh
python check_contract.py
# Optional independent comparison to a private original source:
python check_contract.py --original "$FROZEN_SOURCE"
```

Checks use only synthetic arrays, images, byte files and manifests; no Torch/Transformers imports or media decoding. A passing contract check is separate from the model study's accuracy and should be reported separately.

## Method sources

[DINOv2](https://arxiv.org/abs/2304.07193) supplies the frozen visual representation. [PatchCore](https://arxiv.org/abs/2106.08265) motivates normal patch memory; this implementation is a different fixed adaptation. Official scikit-learn [grouped CV](https://scikit-learn.org/stable/modules/cross_validation.html) and [threshold](https://scikit-learn.org/stable/modules/classification_threshold.html) guidance support the held-out fitting/operating-point separation.

Supplementary software workflow guidance: Timothy Kassis, Vinayak Agarwal, Yuhuan He, Darshil Patel and Aubrey M. Brueckner (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065). Latest arXiv record checked17October2026 (v2).
