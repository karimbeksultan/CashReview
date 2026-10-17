# Jury evidence register

This register separates passing service checks from model quality and untested release claims. The backend's 30 synthetic contract/security tests passed. Three real sequential loopback HTTP jobs completed, but the model still flagged every held-out test clip, including all four normal clips. Keep media, frames, keys, hashes and private evidence outside the public repository.

## Claims and current evidence

| Claim | Case source | Version / test input | Evidence and status |
| --- | --- | --- | --- |
| New `.mov` runs without manual inference execution | §§2,4,5 | V1; [local HTTP smoke](service_verification.json) | **Passed service path** through browser/jury endpoints. Browser visual result/comparison verification is recorded separately |
| Exact POST + GET jury flow works | §10 | V1; two sequential jury submissions | **Passed locally**; processing/done observed. Public access remains untested |
| Missing, wrong and valid keys behave correctly | §10 | 30-test backend suite; HTTP auth isolation | **Passed covered tests**; never retain key values in public records |
| Completed verdicts use the exact two values | §§4,5,10 | Contract suite and V1 result validation | **Passed schema tests**; all real smoke outputs happened to be positive, including two false flags |
| Positive outputs include 1–3 JPEGs at valid timestamps | §§4,10 | Three real jobs; 12 JPEGs total | **Passed byte decode/time/image-bound checks**; relevance and event correctness remain model questions |
| Multiple events can be returned | §§4,10 | Real 71.6-second job returned two events | **Passed service support**; no exhaustive event-recall claim |
| Model and sponsor reference remain independent | Source-label integrity; §10 | New reference-presentation regression | **Passed backend test**; reference UI-only, never a jury result/engine input; unknown content reports unavailable; source type remains unspecified |
| Semantic violation category is correct | §§4,9 | `visual_review_signal` baseline | **Open gap**; binary labels do not supply semantic types |
| Each event maps to a verified applicable obligation | §§4,6,9 | Registry `2026-10-17.1`, CR-001 | **Open gap**; official context verified, legal-claim flag false |
| Official domain context is traceable | §6 | CR-001 | **Verified context only**; [source and scope](normative_mapping.md), checked 17 October 2026 |
| No cloud AI is used at runtime | §7; FAQ D21 | Local OpenCV CPU model implementation | **Implemented/source reviewed**; network-disabled runtime test not performed |
| Full flow runs with internet blocked after preparation | §7 | Pending offline run | **Not verified**; record installed artifacts and network condition |
| Complete result arrives under 300 seconds | §10; FAQ C14 | [Three sequential loopback jobs](service_verification.json) | **Observed 5.812/16.485/20.375 seconds** for 25.933/71.6/142.533-second clips. No concurrent/public-network guarantee |
| Held-out quality and exact duplicates are reported | §9 | [Frozen holdout evaluation](evaluation.json), seed 26017 | **Measured failure**: 8/8 completed; 4 positive/4 negative; every clip flagged; 50% accuracy, 0% specificity. Exact duplicates grouped; near-duplicate/session review remains open |
| Changed-angle robustness is supported | §9; FAQ A4 | No alternate-view result recorded | **Not verified**; do not equate augmentation with real view coverage |
| Technical errors never become negative verdicts | §§5,10 | Passed backend readiness/failure/deadline tests | **Passed covered synthetic cases**; deployment failure behavior still needs exercising on target host |
| Jobs and evidence are private | §10/data constraint | Passed token, cross-job and jury/browser isolation tests | **Passed covered tests and loopback isolation**; host/backup access controls remain operational responsibilities |
| Durable claims and deadlines survive stale attempts | §§5,10 | Passed queue/fencing/reopen/hard-deadline tests | **Passed covered synthetic cases**; process/host restart rehearsal on target deployment remains open |
| Retention removes runtime artifacts | FAQ A6 | Default 24-hour retention; cleanup unit tests | **Passed covered local cleanup cases**; backups/logs and all target-host copies not verified |
| Model/code/weight licenses permit required use | FAQ D24 | [Model card provenance](model_card.md); project MIT license | **Documented upstream Apache-2.0 backbone and application license**; final dependency/license review remains a release check |
| Public UI and API are reachable from another network | §§8,10; FAQ D23 | No public deployment | **Open gate**; actual URL and external-network run required |
| Handoff instructions and private key delivery are complete | §8 | [Handoff](handoff.md), README launcher | **Partial**; local instructions and measured diagnostics available; public URLs and jury delivery remain open |

## Quality interpretation

The V1 confusion matrix is `[[0,4],[0,4]]` with negative/positive true rows and predicted columns. Precision 0.50, recall 1.00 and F1 0.667 must always be accompanied by the fact that every clip was flagged. The eight-group sample has wide uncertainty; same-camera correlation and unreviewed near duplicates limit generalization. No semantic type accuracy, full event precision/recall or alternate-camera performance is established.

A V2 video gate was rejected at validation balanced accuracy 0.375. It was not promoted or evaluated on test. Its design followed exposure to the failed V1 result, so future reuse of that test is exploratory. See [validation attempt](validation_attempt.json).

The [service verification artifact](service_verification.json) covers three sequential loopback requests, including the longest source clip. Both normal inputs were incorrectly flagged. Twelve real JPEGs passed decode and bounds checks. This is service-path evidence, not an additional accuracy benchmark, load test, public-network check or internet-disconnected run.

## Minimum record per executed check

Store date/time, code revision, model checksum, registry version, configuration/split identifier, hardware, permitted input identifier, command/test name, observed output, pass/fail and private evidence location. An input identifier is enough in public records; do not publish restricted filenames or screenshots merely to make the checklist look complete.

Keep three evidence classes distinct: synthetic contract fixtures validate software behavior; held-out real clips estimate detector performance on the evaluated distribution; public/offline/restart checks validate operational claims. Success in one does not establish the others.

Before release, replace the pending rows with actual records or leave the limitations explicit. Do not fill the register with workshop example metrics, inferred test successes or fictional deployments.
