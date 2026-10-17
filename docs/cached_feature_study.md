# Cached frozen-feature normal-memory/prototype comparison

Status: **rejected_train_gate**. Aggregate experimental record.

The fixed cohort contains 24 training content groups (13 positive, 11 normal), with four group-held-out folds. No original exposed-test groups were evaluated. Outcomes remain exploratory and do not establish event-type accuracy, legal applicability or release readiness.

Cached SigLIP2/R3D18 rows; fitting-group-only normal cosine memory (three distinct groups) or sparse positive-versus-normal prototype ratios (one/three groups), with mean-top3 or adjacent-pair persistence pooling. Positive support only within annotation±2seconds; other positive times remain unknown.

The declared selection rule chose candidate 1: OOF ROC-AUC **0.468531**, standardized partial AUC (FPR ≤.25) **0.456543**.

| Candidate | Fixed configuration | OOF ROC-AUC | OOF partial AUC | Train gate |
| --- | --- | --- | --- | --- |
| 1 | siglip / normal_memory_k3 / mean_top3 | 0.468531 | 0.456543 | Failed |
| 2 | siglip / normal_memory_k3 / max_adjacent_min | 0.482517 | 0.440559 | Failed |
| 3 | siglip / prototype_ratio_k1 / mean_top3 | 0.328671 | 0.428571 | Failed |
| 4 | siglip / prototype_ratio_k1 / max_adjacent_min | 0.335664 | 0.440559 | Failed |
| 5 | siglip / prototype_ratio_k3 / mean_top3 | 0.307692 | 0.428571 | Failed |
| 6 | siglip / prototype_ratio_k3 / max_adjacent_min | 0.307692 | 0.428571 | Failed |
| 7 | r3d / normal_memory_k3 / mean_top3 | 0.391608 | 0.428571 | Failed |
| 8 | r3d / normal_memory_k3 / max_adjacent_min | 0.370629 | 0.428571 | Failed |
| 9 | r3d / prototype_ratio_k1 / mean_top3 | 0.363636 | 0.456543 | Failed |
| 10 | r3d / prototype_ratio_k1 / max_adjacent_min | 0.370629 | 0.456543 | Failed |
| 11 | r3d / prototype_ratio_k3 / mean_top3 | 0.251748 | 0.428571 | Failed |
| 12 | r3d / prototype_ratio_k3 / max_adjacent_min | 0.272727 | 0.428571 | Failed |

The training gate rejected the selected candidate. None of the declared candidates had an eligible joint specificity/recall operating point.

Selection groups evaluated: 0; original test groups evaluated: 0. No serving replacement or independent quality validation is claimed.

Source identifiers, paths, split/cache hashes and per-group labels/scores are excluded. Software/research contract-check counts are separate from these quality measurements.


## Method and software references

- [Scikit-learn: grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html): Separate independent groups and retain a final evaluation set.
- [Scikit-learn: threshold selection](https://scikit-learn.org/stable/modules/classification_threshold.html): Choose an operating point from held-out training scores, without tuning on evaluation outcomes.
- Timothy Kassis, Vinayak Agarwal, Yuhuan He, Darshil Patel, Aubrey M. Brueckner (2026). [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065): Supplementary scikit-learn workflow guidance; latest arXiv record checked 17 October 2026 (v2).
- [Towards Total Recall in Industrial Anomaly Detection (PatchCore)](https://arxiv.org/abs/2106.08265): Normal patch-memory method inspiration only; this study is not a faithful PatchCore implementation or industrial-benchmark reproduction.
