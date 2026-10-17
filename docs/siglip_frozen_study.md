# SigLIP 2 frozen-feature study

The frozen candidate failed the existing eight-group selection gate and was not deployed. At its unchanged training-selected threshold, selection confusion was **TN 2, FP 2, FN 2, TP 2**. Accuracy, balanced accuracy, precision, recall, specificity and F1 were 50%. The gate required specificity ≥75%, recall ≥50% and balanced accuracy >50%.

Specificity and recall each had 2 successes in 4 trials. Their nominal exact equal-tailed Clopper–Pearson 95% intervals are **6.7586%–93.2414%**. These intervals do not account for repeated selection or shared scenes and actors. These eight reused selection groups are not an independent holdout; the previously exposed eight test groups were excluded entirely.

## Frozen method and selection

[Google's official checkpoint](https://huggingface.co/google/siglip2-base-patch16-224) is Apache 2.0 licensed, revision `75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2`. It ran locally with no remote inference. The official RGB bilinear 224×224 processor and 768D normalized vision outputs were retained. Twelve predeclared generic text vectors supplied uncalibrated cosine features, with no generated case descriptions or legal verdict prompts.

There were 42 original videos and 40 exact-content groups. The study used 24 training and 8 selection groups, with one source copy per content group. Whole clips were sampled at 1 fps using actual normalized presentation timestamps. Six candidates were declared before extraction. Group-isolated four-fold CV fitted scaling and classification inside each training fold. Unknown moments in positive clips were never labelled negative; supplied positive anchors supervised only the weak-window candidate.

| Representation | C | Train OOF ROC-AUC | Standardized partial AUC, FPR≤0.25 |
|---|---:|---:|---:|
| bag_full | 0.01 | 0.6294 | 0.6444 |
| bag_full | 0.1 | 0.6154 | 0.6124 |
| bag_semantic | 0.01 | 0.5455 | 0.6004 |
| bag_semantic | 0.1 | 0.6643 | 0.6563 |
| weak_window_full | 0.01 | 0.5315 | 0.5724 |
| weak_window_full | 0.1 | 0.5455 | 0.6164 |

The training-selected candidate was **bag_semantic, 36 features, C = 0.1**: mean, population std and maximum of 12 cosines. Training OOF ROC-AUC was 0.6643 and standardized partial AUC was 0.6563. Its frozen threshold was `0.5510047078132629`. Training OOF confusion was TN 9 / FP 2 / FN 6 / TP 7, specificity 81.82%, recall 53.85% and balanced accuracy 67.83%. That passed the predeclared training guard; it did not establish independent generalization. The subsequent unchanged selection result failed, so no alternative threshold or candidate was substituted.

## Completion and measured scope

All 24 training and 8 selection groups completed, with 0 failures and **1,031 sampled source frames** (736 training, 295 selection). No test group was decoded by this study. Training feature extraction totalled 558.44 seconds, maximum 101.31 seconds/group; selection extraction totalled 285.50 seconds, maximum 73.14 seconds/group. Peak resident footprints were 806.22 MB and 800.78 MB. These are warm feature-extraction measurements, not upload-to-result service timings.

On an Intel Core i5-10310U (4 cores / 8 logical processors), Windows 11 Pro, 15.76 GiB visible RAM, two CPU threads, float32: the 145-frame synthetic portrait probe took 150.29 seconds full process wall (111.24 seconds model work), peak 764.19 MB. The separate 12-caption-vector process took 119.13 seconds wall, peak 771.93 MB. Both processes exited before source extraction. Torch 2.6.0+cpu, Transformers 4.57.6 and scikit-learn 1.9.1 were used in an isolated environment with read-only reuse of existing local dependencies.

No event localization, action category or legal rule was validated. Generic attribution would only identify a review context and was never used to rescue a failed video score. Source footage, features, labels, per-group predictions and weights remain private. No runtime model changed. Any future distinct candidate still needs its frozen quality gate, preprocessing/numerical parity and a measured full cold pipeline before deployment.

## Frozen artifact checksums

- `classifier.npz`: `8dcf1be75fd17fe3d59890f3e67c0bf20087521621a7f7046675965ab69af2f7`
- `fixed_caption_embeddings.npy`: `25e75742b9b41851c1d5a26e71aad4a5f02ba4866384f1e521edb771aad26712`
- `study_policy.json`: `b068a67d9ada8438814085eb2da7bca0fc0afe9333ae0a712b1b04103ecadf3f`
- `attribution_policy.json`: `946ae32977695dca83cf446c9106ded670187c8bbd1620f071011e38f0e196b7`
- `config.json`: `fe8b5fe6d5734360678fd71c11c21e1ea3364bd8598d34295d9206335973ffd7`
- `preprocessor_config.json`: `9b36b57ebaf20f09bf4c22100ccc21877ea6bfe5aead0c00c59f8af8ccefacfc`
- `vision_tower/model.safetensors`: `47b2fedf5dffe18405c5b6d9e9c6147e4648046d1ddff82364f330abf0a5bf2d`
- `train_selection.json`: `9548b4bb8c22d901804f058d0c48940e042e0892455faa7837a5b73f32c86103`

Full official foundation SHA-256: `612923381c76ec5a9bed335d1c48827e3f2e506ac31b044b63b2031fadee6a0b`. The separate tower preserves exact selected official tensor bytes. Checksums identify model and configuration artifacts, not case identities.

## Software and workflow references

The [Transformers SigLIP 2 documentation](https://huggingface.co/docs/transformers/model_doc/siglip2) and [scikit-learn grouped CV documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html) supplied API context. The scikit-learn skill informed fold-local pipeline and grouping safeguards: Kassis et al. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065). This workflow reference supplies no model-performance evidence.
