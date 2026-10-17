# EXPERIMENTAL RESEARCH: SigLIP2 final-block fine-tuning

The original fixed candidate was **rejected by its training gate**: four-fold
OOF ROC-AUC was 0.454545 and no threshold satisfied the joint operating-point
rule. No final candidate, validation evaluation, export or application integration
resulted. See the [aggregate experiment report](../../../docs/siglip_finetune_study.md).

This directory provides a portable reproduction workflow, **not an available
detector**. The portable heavy workflow has not been rerun. Media-free checks and
an AST comparison verified nine numerical functions against the executed source;
the fitting comparison normalizes only the replacement of raw array loading with
validated array loading. Path handling, cache integrity and runtime fingerprints
are additional portability checks. They do not establish heavy-run equivalence
or model quality.

## Local setup and public assets

Run commands from this directory with Python 3.12. Use a separate research
environment; these packages are not application runtime requirements.

```sh
cd backend/research/siglip2
python -m venv .training-env
# Activate .training-env for your shell, then:
python -m pip install -r requirements-training.txt
python prepare_assets.py --model-dir "$MODEL_DIR" --download
```

Set `DATA_DIR`, `MODEL_DIR`, `RUN_DIR` and `SPLIT_PATH` to explicit local paths.
Keep footage, labels, assets and runs outside source control. The optional
`--download` fetches only public files from the pinned official Google model
repository. Omitting it verifies files already present. Transformers model
loading is offline and local only; no source footage is uploaded.

The source checkpoint is pinned to revision
`75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2`, with SHA-256
`612923381c76ec5a9bed335d1c48827e3f2e506ac31b044b63b2031fadee6a0b`.
The exact streaming vision-tower subset has SHA-256
`47b2fedf5dffe18405c5b6d9e9c6147e4648046d1ddff82364f330abf0a5bf2d`.
Configuration, processor and model-card bytes are also verified. The
[pinned model card](https://huggingface.co/google/siglip2-base-patch16-224/blob/75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2/README.md)
declares Apache 2.0. Preparation retains the actual license, source attribution
and provenance with the local assets and run. Framework licenses apply separately.

## Data and frozen groups

`DATA_DIR` contains `open_labels.xlsx` and `videos/*.mov`. The workbook's `labels`
sheet has identifier, timestamp and binary-label columns. Exact Unicode filename
stems join the rows. Labels are `нарушение` and `без нарушения`.

Generic timestamps accept finite nonnegative numeric seconds or complete
`MM:SS` strings. The source-unit parser also accepts complete Russian second and
minute forms, including grammatical variants and fractional seconds. Minute
components must be whole; seconds must be below 60 when minutes are present.
Negative, boolean, nonfinite, incomplete and malformed values fail. Identical
video bytes form one group; conflicting labels fail. Duplicate positive
annotations are retained as a union. Metadata joins never enter model inference.

Prefer the original frozen membership when reproducing an experiment. Legacy
absolute paths are relocated by their final Unicode filename into the supplied
`DATA_DIR/videos/`; former locations are never read. Content membership and
supervision must still match. For a **new study only**, explicitly create a split:

```sh
python workflow.py freeze-split --data-dir "$DATA_DIR" --model-dir "$MODEL_DIR" --run-dir "$RUN_DIR" --split "$SPLIT_PATH"
```

This operation hashes local files without decoding video. It uses the original
seed 26017 and class-stratified 20% test / 20% validation membership rule, keeping
exact duplicates together. It refuses to overwrite a split. Evaluation never
silently creates one. Four-fold fitting requires at least four training groups
per class. No test-processing command exists.

## Separate processes for each phase

Heavy phases require `--execute` and sufficient local memory. Start each command
in a fresh process. Do not run several model-loading phases concurrently.

```sh
python workflow.py audit --data-dir "$DATA_DIR" --model-dir "$MODEL_DIR" --run-dir "$RUN_DIR" --split "$SPLIT_PATH"
python workflow.py synthetic-benchmark --data-dir "$DATA_DIR" --model-dir "$MODEL_DIR" --run-dir "$RUN_DIR" --split "$SPLIT_PATH" --execute
python workflow.py cache-train --data-dir "$DATA_DIR" --model-dir "$MODEL_DIR" --run-dir "$RUN_DIR" --split "$SPLIT_PATH" --execute
python workflow.py cv --data-dir "$DATA_DIR" --model-dir "$MODEL_DIR" --run-dir "$RUN_DIR" --split "$SPLIT_PATH" --execute
# Only if selection.json records training_gate_passed=true:
python workflow.py cache-validation --data-dir "$DATA_DIR" --model-dir "$MODEL_DIR" --run-dir "$RUN_DIR" --split "$SPLIT_PATH" --execute
python workflow.py validate --data-dir "$DATA_DIR" --model-dir "$MODEL_DIR" --run-dir "$RUN_DIR" --split "$SPLIT_PATH" --execute
```

The original candidate stopped after `cv`. Its failed gate must not be bypassed
to fit a final checkpoint or evaluate validation. A run binds workflow, data I/O,
policy, split, model configuration and processor digests, plus metadata-only
Python/OS/package fingerprints. Changes require a new run directory. Completed
selection cannot be overwritten; validation returns the recorded evaluation.

Checkpoints use safetensors. Hidden-state arrays require bounded size, float32,
expected shape, finite values, per-array SHA-256 and policy-bound metadata, with
`allow_pickle=False`. Score arrays, identities and source paths remain local.

## Fixed numerical method and gates

The official slow processor converts RGB with direct 224×224 Pillow BILINEAR
resize, scaling by 1/255 and mean/std `[0.5, 0.5, 0.5]`. It does not crop and
changes portrait aspect ratio. Sampling uses the complete clip at 1 fps and keeps
raw presentation timestamps, origin and elapsed time. Bounds are 145.5 seconds,
146 samples, 4096 pixels per side and 8 million pixels per decoded frame.

The first 11 of 12 vision blocks are frozen. Only the final block and new 768→1
head are fitted; official postnorm stays frozen. Mean pooling over 196 tokens is
followed by L2 normalization, the linear head and float32 sigmoid. The original
attention-pooling head and rejected caption classifier are excluded.

Positive fitting samples must lie within ±2 seconds of training annotations;
other positive-clip frames remain unknown. Normal clips supply up to 12 uniform
negative samples. Each group contributes one optimizer step with mean frame loss
and class weights computed from fitting groups only. The fixed recipe uses three
epochs, AdamW, block/head learning rates 1e-5/1e-3, weight decay 0.01, gradient
clip 1, microbatch 2 and one mild brightness/contrast variant.

Four fresh group-stratified fits produce OOF scores. Video score is the float64
mean of the three highest float32 frame probabilities. A threshold must achieve
recall and specificity ≥0.5 and balanced accuracy >0.5; ties maximize balanced
accuracy, specificity, recall, then threshold. OOF ROC-AUC must exceed 0.55 and
standardized partial AUC at FPR ≤0.25 must exceed 0.5. Final fitting is permitted
only if all training conditions pass.

Apply that one frozen threshold to validation only after the training gate.
Require specificity ≥0.75, recall ≥0.5 and balanced accuracy >0.5. Do not retune
against the outcome. The original validation cohort served earlier development
experiments, so even a pass would remain `selection_only`. Existing test groups
were excluded from these improvement studies but previously exposed by the
original baseline. Fresh independent holdout data is still required.

Local peaks and 8-second NMS provide at most three generic review moments. The
preserved implementation can choose several anchors from one long score plateau.
Action types, legal conclusions and event attribution remain unvalidated. No
automatic engine integration or source-metadata verdict lookup is included.

Quality alone does not qualify latency. A future candidate would also need
independent embedding/logit/probability parity and fresh cold full-engine timing,
including initialization, decoding, scoring and real JPEG evidence. Such timing
excludes HTTP upload, queue and polling and makes no concurrency claim. Retain
`quality_validated:false`, `validation_status:'selection_only'` and uncalibrated
scores until independent evidence supports stronger claims.

## Media-free checks

```sh
python check_contract.py
python -m compileall -q .
# Optional comparison with an archived source workflow supplied locally:
python check_contract.py --original "$ARCHIVED_WORKFLOW"
```

Checks use synthetic byte files, a synthetic workbook and numeric arrays. They
do not import Torch, load a model or decode media. CI runs these contracts without
installing the research training stack. The portable workflow has a new contract
hash and does not reuse earlier caches or checkpoints.
