# Conditional signed-transition DINO temporal MIL study

Status: **rejected_train_gate**. Aggregate experimental record.

The fixed cohort contains 24 training content groups (13 positive, 11 normal), with four group-held-out folds. No original exposed-test groups were evaluated. Outcomes remain exploratory and do not establish event-type accuracy, legal applicability or release readiness.

The declared selection rule chose candidate 1: OOF ROC-AUC **0.412587**, standardized partial AUC (FPR ≤.25) **0.484515**.

| Candidate | Fixed configuration | OOF ROC-AUC | OOF partial AUC | Train gate |
| --- | --- | --- | --- | --- |
| 1 | centered_patch_transition_mean_signed_abs | 0.412587 | 0.484515 | Failed |

The training gate rejected the selected candidate. None of the declared candidates had an eligible joint specificity/recall operating point.

Selection groups evaluated: 0; original test groups evaluated: 0. No serving replacement or independent quality validation is claimed.

Source identifiers, paths, split/cache hashes and per-group labels/scores are excluded. Software/research contract-check counts are separate from these quality measurements.


## Method and software references

- [Scikit-learn: grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html): Separate independent groups and retain a final evaluation set.
- [Scikit-learn: threshold selection](https://scikit-learn.org/stable/modules/classification_threshold.html): Choose an operating point from held-out training scores, without tuning on evaluation outcomes.
- Timothy Kassis, Vinayak Agarwal, Yuhuan He, Darshil Patel, Aubrey M. Brueckner (2026). [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065): Supplementary scikit-learn workflow guidance; latest arXiv record checked 17 October 2026 (v2).
- [DINOv2 primary paper](https://arxiv.org/abs/2304.07193): Source of the frozen visual representation, not a task-specific quality claim.
- [Official base DINOv2 repository and licence](https://github.com/facebookresearch/dinov2): Base code and weights; distinct XRay/Cell terms do not apply to the selected base checkpoint.
- [Pinned official DINOv2-small assets](https://huggingface.co/facebook/dinov2-small/tree/ed25f3a31f01632728cabb09d1542f84ab7b0056): Public asset provenance. The fixed two-tile transform differs from the published processor crop.
- [Real-world Anomaly Detection in Surveillance Videos](https://arxiv.org/abs/1801.04264): Multiple-instance video/segment supervision concept; the fixed small local learner is an adaptation, not a reproduction of the paper.
