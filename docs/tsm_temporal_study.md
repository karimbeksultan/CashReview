# TSM SSv2: training-only temporal study

The selected recipe failed the training gate. No validation, independent accuracy claim or serving promotion follows.

Twenty-four unique training groups (13 positive, 11 normal), four folds, six predefined recipes. Selection/test feature arrays loaded: **0/0**. Training OOF ranking is not fresh independent accuracy.

| Representation | C | OOF ROC-AUC | Standardized pAUC (FPR≤0.25) | Eligible OOF threshold | Training gate |
|---|---:|---:|---:|---:|---|
| action_logits | 0.01 | 0.419580 | 0.428571 | none | fail |
| action_logits | 0.1 | 0.419580 | 0.440559 | none | fail |
| action_logits | 1 | 0.447552 | 0.456543 | none | fail |
| unit_embeddings | 0.01 | 0.461538 | 0.452547 | none | fail |
| unit_embeddings | 0.1 | 0.433566 | 0.468531 | none | fail |
| unit_embeddings | 1 | 0.426573 | 0.452547 | none | fail |

Selected recipe: **unit_embeddings, C=0.1**. Complete eligible confusion counts and derived operating metrics, if any, are preserved in the aggregate JSON.

Official eight-segment TSM ResNet50 SSv2 encoder. Two fixed full-width upper/lower 60% portrait tiles, each RGB 224-square with ImageNet normalization. Top/bottom raw 174-class logits concatenate to 348 features; independently unit-normalized 2048-D vectors concatenate to 4096. Each representation uses C=.01/.1/1. New weighted StandardScaler and logistic regression fit within each unique-content fold; whole-clip score is the linear 90th percentile of all context probabilities.

Normal fitting groups supply all contexts as negatives. Positive fitting groups supply only logical contexts containing sparse annotations; unannotated positive contexts remain unknown. Class and clip sample weights are used once in both scaler and classifier. Held-out scoring uses all contexts without annotations.

Rank training OOF standardized partial AUC at FPR<=.25, then full ROC-AUC, then declared order. The selected candidate must have ROC-AUC>.6, partial AUC>.5 and an OOF threshold with specificity>=.8, recall>=.5, balanced accuracy>=.65.

The original dense 73-context synthetic hardware qualification failed. Version 2 was fixed before any source processing: four-second starts, eight targets at 2 FPS, at most 37 contexts; short tails repeat authentic observations and PTS. This amendment changes coverage and preserves the failed dense preflight.

Code is MIT. Separate hosted-weight terms remain **unconfirmed**. The private checkpoint is not redistributed or promoted. The JSON records the actual local public-download SHA256, official source pin, and generic-code/policy digests; no case/cache/split/OOF digest or prediction record is published.

## Local extraction, separate from service qualification

Completed 24/24 groups, failed 0; 192 contexts. Child elapsed seconds (min/median/max/sum): 15.203/27.281/143.265/859.594. Batch wall seconds: 903.969.

Unique/authentic source-frame and padding totals were not established by the final aggregate. These local extraction times exclude qualification of full cold-engine processing, HTTP upload, queueing, evidence delivery and the receiving party’s host. Docker/host/runtime/end-to-end qualification remains open.

Technical checks: 25 extractor contracts, 39 learner contracts, 12 hardware/arithmetic checks. They are separate from application test counts and recognition accuracy.

## Limits

- The same 24 development groups support exploratory training OOF comparisons. Neither selection8 nor test8 was processed by this study; the historical test was already exposed by the baseline.
- Sparse annotation eligibility is weak supervision; it does not establish complete intervals, action types, event localization, authorization, intent, identity, or legal obligations.
- 2 FPS sampling may miss brief actions, padded contexts repeat observations, and q90 may miss a single brief event in a long clip.
- Passing a training gate, if observed, would not establish independent generalization or permit promotion.
- Checkpoint terms remain unconfirmed. This is private local research; weights are not redistributed and no serving promotion is authorized.
- The receiving party will run the package on its own infrastructure. Docker, target hardware/runtime, offline execution and the full HTTP/queue/cold-start path there remain unqualified. Local feature extraction timing does not qualify that host.

## Primary and software-method references

- [Official TSM repository, pinned source](https://github.com/mit-han-lab/temporal-shift-module/tree/1f6a834b02120441d99fa706b7a13ccc5293c6fa) — Official eight-frame Something-SomethingV2 checkpoint and temporal-shift architecture; task-specific quality is not established by action pretraining.
- [TSM: Temporal Shift Module for Efficient Video Understanding](https://arxiv.org/abs/1811.08383) — Primary temporal-shift method. This local CPU transfer study is not a reproduction of its action-recognition benchmark.
- [Pinned official code licence](https://github.com/mit-han-lab/temporal-shift-module/blob/1f6a834b02120441d99fa706b7a13ccc5293c6fa/LICENSE) — MIT code licence. A distinct grant for the hosted checkpoint has not been confirmed; code licensing is not asserted as weight licensing.
- [Scikit-learn: grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html) — Keep unique-content groups separate and fit preprocessing within each training fold.
- [Scikit-learn: threshold selection](https://scikit-learn.org/stable/modules/classification_threshold.html) — Select an operating point from training OOF scores; no evaluation-outcome threshold tuning.
- [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065) — Supplementary scikit-learn workflow guidance; arXiv v2 checked 17 October 2026.
