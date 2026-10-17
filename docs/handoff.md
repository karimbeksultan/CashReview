# Cash Review handoff

Cash Review now has a running local application and a verified HTTP service path. Its detector is inadequate for competition: it flagged every clip in the eight-clip held-out test, including all four normal clips. Competition readiness requires the model, semantic categories, rule mapping and deployment gates below.

## Access and operational status

| Item | Handoff status |
| --- | --- |
| Requested GitHub repository | `https://github.com/karimbeksultan/Review.` — implementation pushed to branch codex/cash-review; review and merge status are tracked in GitHub |
| Local UI and API | `http://127.0.0.1:8000` while the local launcher is running |
| Public UI URL | **Not configured** |
| Public jury API base URL | **Not configured** |
| Jury key | Configure on the server and deliver privately; never commit or embed in browser assets |
| Runtime hardware | Windows 11; Intel64 Family 6 Model 142 Stepping 12 CPU; 8 logical CPUs; CPU DNN execution, 2 requested OpenCV threads; OpenCV 5.0.0 and NumPy 2.5.4. RAM was not recorded in the aggregate report |
| Backend verification | **30 tests passed**, including independent sponsor-reference presentation and unchanged jury predictions; contract fixtures are synthetic |
| Frontend build | TypeScript checking and final Vite production build passed after the model/reference comparison and formatting |
| Held-out quality | 8/8 completed; 50% accuracy, 0% specificity; all eight predicted positive. See [evaluation](evaluation.json) and [model card](model_card.md) |
| Upload-to-result timing | **Three sequential loopback HTTP jobs completed in 5.812, 16.485 and 20.375 seconds**; no public-network or concurrent-load claim. See [service verification](service_verification.json) |
| Offline execution after preparation | **Not verified** |
| Semantic event classification | Generic `visual_review_signal` baseline; reviewed event taxonomy remains required |
| Normative grounding | `CR-001` is verified context with legal claims disabled; see [normative mapping](normative_mapping.md) |

## Running and using the project

Use the checked-in README as the authoritative source for the actual installation and startup commands. Prepare dependencies and model artifacts before attempting offline operation. Configure private data/model paths, allowed browser origin, upload limits, job timeout and jury credentials on the backend. Keep `.env`, runtime uploads, derived evidence and downloaded weights out of Git.

From the repository root, after preparation, `./scripts/start.ps1 -ModelDir models` starts the local profile. Its private generated jury key is kept in `runtime/jury-key.txt`; do not copy it into this document. The default runtime is FastAPI, SQLite WAL, private local files and a spawned CPU inference process. It does not require hosted Supabase. Vercel/hosted database profiles would need a separately documented locality and data decision.

The reviewer flow is upload a permitted `.mov`, wait for a real job status, then inspect candidate events and their evidence. A processing error must display failure, never a negative result. A completed `no_violation` means the enabled detector found no supported signal at its threshold; it is not proof of compliance. A `violation` API value is the case's binary output label; the current generic marker still requires human interpretation and does not identify a breached legal clause.

The results screen shows two independent answers. **Model decision** is the pixel-based prediction; its type is the generic `visual_review_signal`. **Sponsor reference** is an optional original binary annotation for recognized supplied content; the source type reads **type not specified** because the workbook supplies no event categories. A new or unmatched upload shows no reference. An optional private content-hash registry supplies that display only after analysis; the engine/worker never consult it, it never overrides a model decision, and jury responses omit it. It is a comparison aid, not model validation or a means to improve accuracy.

## Measured evidence and its limits

The frozen exact-content-group split used 24 training, 8 validation and 8 test groups. Test classes were four positive and four negative, with confusion matrix `[[0,4],[0,4]]` (negative/positive true rows and predicted columns). Precision was 0.50, recall 1.00 and F1 0.667, but these numbers describe an all-positive failure; 0% specificity is the decisive limitation. Accuracy's 95% Wilson interval was 0.215–0.785. Semantic type accuracy and complete event precision/recall were not measurable from the supplied labels. A separate V2 gate achieved validation balanced accuracy 0.375, was rejected, and was neither promoted nor tested; the original test was already exposed by V1.

The real local HTTP smoke submitted clips of 25.933, 71.6 and 142.533 seconds through jury and browser endpoints. All completed and all 12 returned JPEGs decoded with checked source-time/image bounds. Both normal clips were incorrectly flagged. This demonstrates upload, durable jobs, inference, evidence and polling on three sequential loopback requests; it is not a new accuracy benchmark, a concurrency test, an independent-network test or a disconnected-internet test. A larger target-host benchmark remains required.

## Jury integration

The jury uses direct backend requests with no browser account or sign-in. Configure the actual HTTPS backend address and key privately. Videos must not pass through a frontend serverless function.

```powershell
$apiBase = 'http://127.0.0.1:8000' # Replace with the actual HTTPS team backend for jury access.
$juryKey = $env:CASH_REVIEW_API_KEY # Or read the private launcher-generated key locally.
curl.exe -X POST "$apiBase/api/v1/analyze" -H "X-API-Key: $juryKey" -F "file=@C:\permitted\example.mov"
curl.exe "$apiBase/api/v1/jobs/REPLACE-WITH-JOB-ID" -H "X-API-Key: $juryKey"
```

The upload response contains `job_id`. Poll `GET /api/v1/jobs/{job_id}` with a bounded delay and stop at `done`, `failed` or the five-minute deadline. Public states are `processing`, `done`, `failed`. Completed verdicts are exactly `no_violation` or `violation`. Positive events require `type`, `timecode_sec`, `description`, and 1–3 real base64 JPEGs in `evidence_frames`. Missing/invalid keys and unauthorized jobs must fail; do not expose a shared key to the UI.

## Required release gates

1. Improve the detector's failure to distinguish normal content. Preserve the existing split/report and identify any later reuse of the exposed test as exploratory. Verify actual code and weight licenses for release.
2. Replace generic review markers with reviewed semantic categories and verified applicable rule predicates before claiming substantive classification or rule-grounding coverage.
3. Finish browser-level result/comparison verification and retain the final frontend build record. Keep the passed synthetic contract tests separate from real detector evaluation.
4. Extend the three-job loopback timing check to representative concurrency, target hardware and independent-network retrieval. Include failures, timeouts and queue delays.
5. Verify restart/deletion behavior in the intended deployment and complete an outbound-network-disabled full run after preparation. Unit tests do not establish backup/log deletion or offline deployment guarantees.
6. Establish a team-operated public host, TLS, direct backend routing and the documented interpretation of locality. Verify UI and API from a separate network. A hosted frontend/database profile is not evidence of full local operation.
7. Record actual URLs and privately deliver the jury key. Rehearse the [demo](demo_runbook.md), update [jury evidence](jury_evidence.md), and fill the [pitch](pitch_outline.md) only with measured claims.

## Data and limitations

Training media is limited to the hackathon. Jury uploads must not enter training or tuning, be published, or go to third parties. No cloud inference, runtime legal lookup, audio analysis or facial identification is permitted by the case. Keep source and derived media private, choose a documented retention period and remove copies and caches consistently.

The supplied annotations are sparse binary labels and isolated positive timestamps. They do not establish complete event windows, semantic types or legal propositions. Exact duplicate content must remain together across evaluation partitions; conflicting duplicate timestamps remain unresolved until reviewed. Unseen camera angles and unseen types require separate evidence. No zero-error, production-readiness or review-time-saving claim is made.
