# DINOv2-small two-tile local-memory/prototype comparison

Status: **rejected_train_gate**. Aggregate experimental record.

The fixed cohort contains 24 training content groups (13 positive, 11 normal), with four group-held-out folds. No original exposed-test groups were evaluated. Outcomes remain exploratory and do not establish event-type accuracy, legal applicability or release readiness.

Two fixed full-width60% upper/lower RGB crops, each bilinear224 with ImageNet normalization, every2seconds. Frozen CLS/patch features; optional per-clip temporal-median centering. Fold-only normal16row/positive8row memory; positive rows within2.001seconds of sparse anchors. Same-cell nearest cosine, top4cells, q90 or adjacent-two mean maximum. Zero-query minimum signal is novelty0/margin−2.

The declared selection rule chose candidate 5: OOF ROC-AUC **0.517483**, standardized partial AUC (FPR ≤.25) **0.552448**.

| Candidate | Fixed configuration | OOF ROC-AUC | OOF partial AUC | Train gate |
| --- | --- | --- | --- | --- |
| 1 | global / normal_novelty / quantile90 | 0.503497 | 0.504496 | Failed |
| 2 | global / normal_novelty / adjacent2_mean_maximum | 0.496503 | 0.520480 | Failed |
| 3 | global / positive_normal_margin / quantile90 | 0.475524 | 0.464535 | Failed |
| 4 | global / positive_normal_margin / adjacent2_mean_maximum | 0.475524 | 0.452547 | Failed |
| 5 | patch / normal_novelty / quantile90 | 0.517483 | 0.552448 | Failed |
| 6 | patch / normal_novelty / adjacent2_mean_maximum | 0.510490 | 0.540460 | Failed |
| 7 | patch / positive_normal_margin / quantile90 | 0.447552 | 0.540460 | Failed |
| 8 | patch / positive_normal_margin / adjacent2_mean_maximum | 0.447552 | 0.540460 | Failed |
| 9 | centered_patch / normal_novelty / quantile90 | 0.419580 | 0.452547 | Failed |
| 10 | centered_patch / normal_novelty / adjacent2_mean_maximum | 0.391608 | 0.428571 | Failed |
| 11 | centered_patch / positive_normal_margin / quantile90 | 0.377622 | 0.456543 | Failed |
| 12 | centered_patch / positive_normal_margin / adjacent2_mean_maximum | 0.349650 | 0.472527 | Failed |

The training gate rejected the selected candidate. None of the declared candidates had an eligible joint specificity/recall operating point.

Frozen training rule: Selected ROC-AUC>.6, standardized partialAUC>.5 and a threshold satisfying specificity≥.8, recall≥.5, BA≥.65; rank partialAUC, ROC-AUC, declaration order.

Selection groups evaluated: 0; original test groups evaluated: 0. No serving replacement or independent quality validation is claimed.

Source identifiers, paths, split/cache hashes and per-group labels/scores are excluded. Software/research contract-check counts are separate from these quality measurements.

Local feature extraction completed 24/24 groups with 0 failed groups and 375 sampled frames (750 encoder calls). Recorded per-clip processing ranged 3.874–91.758 seconds (median 8.961).

These research extraction times exclude cold initialization, upload, queue, evidence and retrieval; they do not qualify the 300-second service deadline.


## Method and software references

- [Scikit-learn: grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html): Separate independent groups and retain a final evaluation set.
- [Scikit-learn: threshold selection](https://scikit-learn.org/stable/modules/classification_threshold.html): Choose an operating point from held-out training scores, without tuning on evaluation outcomes.
- Timothy Kassis, Vinayak Agarwal, Yuhuan He, Darshil Patel, Aubrey M. Brueckner (2026). [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065): Supplementary scikit-learn workflow guidance; latest arXiv record checked 17 October 2026 (v2).
- [DINOv2 primary paper](https://arxiv.org/abs/2304.07193): Source of the frozen visual representation, not a task-specific quality claim.
- [Official base DINOv2 repository and licence](https://github.com/facebookresearch/dinov2): Base code and weights; distinct XRay/Cell terms do not apply to the selected base checkpoint.
- [Pinned official DINOv2-small assets](https://huggingface.co/facebook/dinov2-small/tree/ed25f3a31f01632728cabb09d1542f84ab7b0056): Public asset provenance. The fixed two-tile transform differs from the published processor crop.
- [Towards Total Recall in Industrial Anomaly Detection (PatchCore)](https://arxiv.org/abs/2106.08265): Normal patch-memory method inspiration only; this study is not a faithful PatchCore implementation or industrial-benchmark reproduction.
