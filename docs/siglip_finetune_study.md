# Fixed SigLIP2 final-block experiment

The predefined last-block fine-tuning experiment failed its training-only chance gate. No final model was fitted, no validation or test clips were evaluated by this study, and no engine or deployment changed. The workflow is experimental research.

## Method

Official SigLIP2 base patch16/224 vision weights were used offline. Embeddings, the first 11 of 12 transformer blocks and the official post-layernorm were frozen. The final block and a new binary head were trained: mean token pooling, L2 normalization, a linear head and sigmoid. The original MAP pooler was excluded. This gives 7,088,641 trainable parameters.

One fixed recipe was used: three epochs; AdamW; backbone/head learning rates 1e-5/1e-3; weight decay 0.01; two-frame microbatches; gradient clipping 1. Each group contributed its mean loss, with class weights computed from the fitting groups only. Positive fitting frames were restricted to supplied training annotations ±2 seconds. Only normal training clips supplied negative frames. At most 12 frames per fitting group and mild brightness/contrast changes were used. Unannotated positive frames were excluded from fitting.

At inference, the complete 1 fps stream was sampled without labels or annotation timestamps. The video score was the mean of its three largest frame probabilities. All four folds used fresh final-block/head initialization and kept each exact-content group in one partition. The threshold rule and chance guard were frozen before source fitting.

## Training results

The 24 training groups contained 13 positive and 11 negative groups. Every group received one held-out prediction across four folds. No threshold met the frozen requirements of recall ≥0.5, specificity ≥0.5 and balanced accuracy >0.5. Therefore there is no selected operating point or selected confusion matrix.

| Metric | Result | Required |
|---|---:|---:|
| OOF ROC-AUC | 0.454545 | >0.55 |
| Standardized partial AUC, FPR ≤0.25 | 0.516484 | >0.5 |
| Eligible operating point | None | Required |
| Overall training gate | Rejected | All conditions |

For descriptive completeness only, the conventional 0.5 cutoff gives TP=4, TN=5, FP=6, FN=9; recall=0.307692, specificity=0.454545, balanced accuracy=0.381119. This cutoff was not selected or used for deployment.

## Resources and numerical checks

- Frozen-prefix caching: 736 original frame representations and 193 fitting variants across 24 groups; 583.249 seconds, excluding cold model startup. Longest group: 98.811 seconds.
- Complete four-fold process: 410.033 seconds including imports; peak working set 567,128,064 bytes (540.9 MiB).
- Fold completion elapsed times: 152.070s, 236.190s, 325.800s, 409.994s (derived from saved held-out score file times).
- Synthetic prefix/suffix numerical check: maximum absolute difference 0.0. Separate block and head gradients were finite/nonzero; both changed weights with synthetic weight decay set to zero. Actual fitting retained the frozen 0.01 decay.
- Synthetic two-frame backward/optimizer steps: 0.494109s, 0.527624s, 0.415956s; peak working set 974,417,920 bytes (929.3 MiB).

No full cold engine, HTTP upload, queue, polling or concurrent-client latency claim follows from these measurements.

## Limits and outcome

The training gate stopped the workflow before final 24-group fitting, validation or ONNX export. The 8 existing test groups were excluded by this study, but the original baseline previously exposed them; a fresh independent holdout is needed for final assessment. Earlier development-family failures were not used to retune this recipe. No action category, legal conclusion or localization accuracy is established. The generic local-peak rule can also select several anchors from one long score plateau.

## Immutable artifacts

Frozen plan, fitting code and source split fingerprints remained intact. The following are aggregate artifact hashes, not case identifiers. The companion JSON contains the same bindings and complete aggregate metrics.

- `plan.json`: `297f34f418c10b53485b9468a52843ab361c7ca025d7ad55e2e6d1e3a82ea31e`
- `finetune.py`: `04cc2f18c8bc958fdeda0435157464880a992db71a72326a8796354e4ce0d638`
- `synthetic_benchmark.json`: `c0bff38ccdd5c718b219dec3c5335e96770ba6686371526436bde381c0e1e7a1`
- `train_cache_report.json`: `0747f284b3bd8649f0ab22697a765907f020bcb0424cbe15c7aa84e106ad0a70`
- `cv_performance.json`: `1715664a6ca845a240c0c19da288191c9bb62115857e3b0690dd588b0340ea11`

Official model source: https://huggingface.co/google/siglip2-base-patch16-224/tree/75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2. Source licensing and provenance are retained with the private weights.
