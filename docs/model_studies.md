# Model improvement studies

The first baseline predicted every original test clip as positive, including all four normal clips. That is a detection failure. Replacing it requires evidence of fewer false alarms with nontrivial recall, rather than an all-negative predictor or a more impressive model name.

The following private local studies used 24 unique training groups and the same eight development groups. Candidate selection used training-only cross-validation. These are exploratory development results: repeated development-set use and a shared source camera limit their credibility. None provides a fresh independent test.

| Representation / selected method | Development specificity | Development recall | Balanced accuracy | Outcome |
| --- | --- | --- | --- | --- |
| Optical-flow bags / RBF SVM | 0.00 | 0.25 | 0.125 | Rejected |
| Correct penultimate MobileNet embeddings with deltas / RBF SVM | 0.25 | 0.00 | 0.125 | Rejected |
| Appearance/motion/dynamics comparison / random forest | 0.50 | 0.50 | 0.500 | Rejected |
| R3D18 spatiotemporal features / normal-only anomaly model | No threshold met the joint gate | No threshold met the joint gate | — | Rejected |

For R3D18, the best unconstrained development threshold had specificity 0.25 and recall 1.00. It still falsely flagged three of four normal clips and was not promoted. Seven predefined temporal candidates had near-chance training cross-validation discrimination at low false-positive rates. Its longest-clip feature extraction took 74.844 seconds for 142.533 seconds of footage, with peak resident memory 319.7 MiB; this excludes the full service path.

The [aggregate study record](model_studies.json) contains the measured counts and selection details. Features, source identities, semantic outputs, weights and clip-level predictions remain private. The original eight test groups were not evaluated by these studies; their earlier V1 exposure remains documented.

## Method references

- [Scikit-learn grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html) and [common leakage pitfalls](https://scikit-learn.org/stable/common_pitfalls.html): fit preprocessing within each training fold and split by independent content.
- [Scientific Agent Skills scikit-learn workflow](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/scikit-learn): supplementary guidance for local training, grouping, pipelines and multiple metrics. Kassis, T., Agarwal, V., He, Y., Patel, D., and Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065), latest record checked 17 October 2026.
- [Hugging Face CLI workflow](https://github.com/huggingface/skills/tree/main/skills/hf-cli): prepared artifact downloads and verification. It does not authorize remote processing of private data.

Larger semantic models require the same checks: official weight/license provenance, local-only execution, structured validated outputs, useful per-class discrimination and measured CPU latency. A generated description is not a reviewed ground-truth annotation or a legal conclusion.
