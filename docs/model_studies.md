# Model improvement studies

The first baseline predicted every original test clip as positive, including all four normal clips. That is a detection failure. Replacing it requires evidence of fewer false alarms with nontrivial recall, rather than an all-negative predictor or a more impressive model name.

The following private local studies used 24 unique training groups. Development checks, where performed, reused the same eight groups. A failed training gate can stop a study before that check. Each report preserves its selection procedure. These are exploratory development results: repeated development-set use and a shared source camera limit their credibility. None provides a fresh independent test.

| Representation / selected method | Development specificity | Development recall | Balanced accuracy | Outcome |
| --- | --- | --- | --- | --- |
| Optical-flow bags / RBF SVM | 0.00 | 0.25 | 0.125 | Rejected |
| Correct penultimate MobileNet embeddings with deltas / RBF SVM | 0.25 | 0.00 | 0.125 | Rejected |
| Appearance/motion/dynamics comparison / random forest | 0.50 | 0.50 | 0.500 | Rejected |
| R3D18 spatiotemporal features / normal-only anomaly model | No threshold met the joint gate | No threshold met the joint gate | — | Rejected |
| SigLIP2 semantic features / grouped linear classifier | 0.50 | 0.50 | 0.500 | Rejected |
| SigLIP2 supervised final-block fine-tuning | Not evaluated | Not evaluated | — | Rejected by training gate |
| Qwen3-VL structured observations / grouped classifier selection | Not evaluated | Not evaluated | — | Rejected by training gate |

For R3D18, the best unconstrained development threshold had specificity 0.25 and recall 1.00. It still falsely flagged three of four normal clips and was not promoted. Seven predefined temporal candidates had near-chance training cross-validation discrimination at low false-positive rates. Its longest-clip feature extraction took 74.844 seconds for 142.533 seconds of footage, with peak resident memory 319.7 MiB; this excludes the full service path.

SigLIP2 used a verified official Apache 2.0 checkpoint locally, sampled the whole clip at one second, and selected among six predefined candidates using four-fold training-group CV. The selected semantic bag had training OOF specificity 0.818 and recall 0.538. Its frozen threshold then produced `[[2,2],[2,2]]` on the eight reused development groups and failed the joint gate. Specificity and recall each had only four trials, with nominal exact 95% intervals of 0.068–0.932. No alternate threshold was substituted. All 32 training/development groups completed across 1,031 sampled frames; no runtime model changed. See the [detailed aggregate study](siglip_frozen_study.md) and [machine-readable record](siglip_frozen_study.json).

A separate fixed recipe fine-tuned the final SigLIP2 vision block and a binary head, with 7,088,641 trainable parameters. Four fresh grouped fits scored all 24 training groups. OOF ROC-AUC was 0.454545, below the required 0.55, and no threshold satisfied the joint recall/specificity rule. The training gate stopped the workflow before final fitting or validation. No candidate was deployed or exported. See the [fine-tuning report](siglip_finetune_study.md) and [aggregate record](siglip_finetune_study.json).

Qwen3-VL-2B ran locally with four motion-selected frames per group and twelve strictly parsed ternary observations. All 24 training groups completed. Fixed four-fold OOF selection preferred the predefined ordinal rule, whose ROC-AUC and standardized partial AUC were both 0.50; no threshold met the joint specificity/recall rule. Each logistic candidate had ROC-AUC 0.458042 and partial AUC 0.489011. The failed training gate stopped selection before the eight development groups. The original strict synthetic control failure and subsequent exploratory protocol amendment remain recorded. No Qwen model was deployed. See the [aggregate semantic study](qwen_semantic_study.md) and [machine-readable record](qwen_semantic_study.json).

A further training-only follow-up tested 27 declared variants on the same 24 groups: 12 cached SigLIP/R3D normal-memory or sparse-prototype variants, 12 two-tile DINOv2 variants, two learned local MIL heads and one signed-transition MIL head. Every family failed its frozen training gate; no additional selection or original test group was evaluated. These variants are correlated development attempts, not 27 independent benchmarks. No detector was replaced.

| Training-only family | Selected OOF ROC-AUC | Partial AUC at FPR ≤0.25 | Eligible joint operating point |
| --- | --- | --- | --- |
| [Cached normal memory/prototypes](cached_feature_study.md) | 0.468531 | 0.456543 | None |
| [DINOv2 two-tile memory/prototypes](dino_memory_study.md) | 0.517483 | 0.552448 | None |
| [Learned local patch MIL](dino_mil_study.md) | 0.510490 | 0.516484 | None |
| [Signed local-transition MIL](dino_transition_mil_study.md) | 0.412587 | 0.484515 | None |

DINOv2 extraction completed all 24 groups without failure: 375 sampled frames and 750 tile-encoder calls. Recorded clip processing ranged from 3.874 to 91.758 seconds, excluding cold initialization and service overhead. The supervised MIL recipes trained shared local heads with sparse positive bags, normal hard examples, class/clip balancing and deterministic bounded optimization. They did not mark every patch in a positive clip as a positive instance. All new metrics were independently recomputed; 129 numerical audit checks are separate from application tests and model accuracy.

The [portable DINO research workflow](../backend/research/dino_memory/README.md) preserves the rejected numerical procedure, two fixed portrait tiles, validated private manifests and media-free contract checks. Eleven numerical/extraction functions match the executed source structurally. Its heavy portable path has not been rerun and is not a serving engine.

The [portable SigLIP2 research workflow](../backend/research/siglip2/README.md) preserves the fixed fitting and scoring method with explicit local paths, verified assets and media-free contract checks. Its original candidate was rejected, and the portable heavy workflow has not been rerun. It is experimental research and does not connect to the application engine.

The [aggregate study record](model_studies.json) contains the measured counts and selection details. Features, source identities, semantic outputs, weights and clip-level predictions remain private. The original eight test groups were not evaluated by these studies; their earlier V1 exposure remains documented.

## Method references

- [Scikit-learn grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html) and [common leakage pitfalls](https://scikit-learn.org/stable/common_pitfalls.html): fit preprocessing within each training fold and split by independent content.
- [Scientific Agent Skills scikit-learn workflow](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/scikit-learn): supplementary guidance for local training, grouping, pipelines and multiple metrics. Kassis, T., Agarwal, V., He, Y., Patel, D., and Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065), latest record checked 17 October 2026.
- [Hugging Face CLI workflow](https://github.com/huggingface/skills/tree/main/skills/hf-cli): prepared artifact downloads and verification. It does not authorize remote processing of private data.

Larger semantic models require the same checks: official weight/license provenance, local-only execution, structured validated outputs, useful per-class discrimination and measured CPU latency. A generated description is not a reviewed ground-truth annotation or a legal conclusion.
