# Local semantic study v3

Outcome: **rejected_train_gate**. Quality validated: **false**. No serving promotion is established by this study.

The original strict synthetic control remains failed: 0 observed, 11 not observed, 1 unclear. V3 was locally frozen before source inference to preserve unclear as explicit missingness; this did not relabel the original gate passed.

The frozen extractor used four motion-selected source frames, the official local Qwen3-VL-2B Q4 model/Q8 projector, 256 image tokens and 4 CPU threads. All pixels and case findings stayed local. A strict contradiction/support parser was configured to stop on any unrecoverable failure without retry or exclusion. No processing failure occurred.

## Cohort accounting

| Phase | Expected | Attempted | Complete | Failed | Unattempted |
|---|---:|---:|---:|---:|---:|
| Train | 24 | 24 | 24 | 0 | 0 |
| Selection | 8 | 0 | 0 | 0 | 8 |

Test groups processed: 0. Earlier unsupervised motion preparation included the 32 development groups; v3 source inference used a separate namespace and withheld selection extraction until a passing frozen training gate.

## Frozen selection and metrics

The logistic candidates used four training-group folds and fold-local scaling. Three balanced L2 logistic candidates (C=0.01/0.1/1) and one fixed ordinal rule were selected by training OOF partial ROC-AUC, with fixed tie rules. Training required ROC-AUC>0.55, partial AUC>0.5 and a training-only operating point with specificity>=0.75, recall>=0.5, balanced accuracy>0.5. Selection8 could run once at the unchanged model/threshold only after this passed.

Selected candidate: `fixed_observed_risk_rule`. Training gate: **false**. OOF ROC-AUC: 0.500000; partial ROC-AUC: 0.500000.

Separate rejection reasons: chance gate passed = false; eligible training operating point found = false. No threshold was selected, no classifier was fitted for deployment, and selection8 was not run.

## Resources

Train: completed-attempt sum 3584.922 s; mean 149.372 s; maximum 212.266 s; peak CLI RSS 2750.1 MiB.

3584.922 seconds is the sum of 24 fresh v3 attempts, not whole-study elapsed time. Each attempt includes source hashing, a new native full-clip motion scan, four JPEG preparations, prompt creation, local CLI model load/vision-language inference, parsing and response-artifact binding. File timestamps independently confirm 24/24 frame preparations occurred within their attempts; earlier prepared development frames were not reused. The sum excludes earlier unsupervised frame preparation, downloads/setup, synthetic controls, freeze and audit helpers, Python process import/startup outside the attempt, controller persistence outside its timer, final cross-validation/head selection, and HTTP upload/queue/polling. CLI RSS is PeakWorkingSetSize/1024^2 (MiB), excludes the Python controller and other processes. This does not qualify whole-service or concurrent latency.

## Limits and provenance

Two independent numeric audits confirmed the metrics, ordering, frozen artifacts and rejection: 11/11 and 43/43 checks. The model failed the training quality gate.

- The source cohort is small and from a single camera context; train OOF and repeatedly used development selection are not independent generalization validation.
- The original eight test groups were exposed by an earlier baseline and were not processed in this study; there is no new clean held-out test claim.
- Sparse four-frame sampling can miss brief or low-motion actions and 256 image tokens may hide small cash or hand detail.
- Semantic findings, event localization, legal/action taxonomy, intent, identity and authorization are not validated by the binary workbook labels.
- Logistic scores are uncalibrated and the fixed rule is an ordinal 0-5 score, not a probability.
- Any future review anchor is sampled visual context, not causal attribution or a validated per-frame action score.
- No rejected method or failed source attempt is promoted; incomplete cohorts cannot yield a quality pass.

Official [Qwen model](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct-GGUF) revision 52d6c8ffea26cc873ac5ad116f8631268d7eb503 uses Apache-2.0. The separate [llama.cpp runtime](https://github.com/ggml-org/llama.cpp) build 11707 uses MIT. Weight/runtime digests, generic-code digests and runtime versions are in the companion aggregate JSON. No source path, group identifier, source/cache/split/prediction-array digest or per-case fact/prediction is published.
