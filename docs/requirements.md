# Requirements review

The supplied harness, section prompts, master prompt and strategy addendum were checked against the implementation. The original source document provides the integration obligations. Later user requests replace the original presentation with a general review workspace, large evidence, separate human decisions and a magenta visual palette.

| ID | Required behavior | Current evidence and limit |
| --- | --- | --- |
| R01 | Working upload, processing and review flow | Frontend and durable local backend are integrated; illustrated UI checks and synthetic API contract tests are distinct from detector evaluation. |
| R02 | MOV upload and explicit processing/failure | Bounded multipart ingestion, polling, retry and safe failure states. Browser playback still depends on codec support; JPEG evidence is provided separately. |
| R03 | Two completed verdicts | Integration schema retains `violation` and `no_violation`; failures have no verdict. A negative result does not certify compliance. |
| R04 | Multiple events with type, seconds, explanation and 1–3 real JPEGs | Contract and result validation support these fields. A model-selected review signal is not an independently validated violation category. |
| R05 | Inspectable rule and source | The registry distinguishes verified background context from disabled legal claims. An applicable breached clause is not established by the current binary source labels. |
| R06 | Researched normative reasoning | Official background source is recorded. Enabled action-to-rule predicates still require verified applicability and reviewed action labels. |
| R07 | Local models, prepared offline execution | Prepared weights and local CPU inference; no remote AI processing. A target-host disconnected deployment exercise remains separate qualification work. |
| R08 | Visual analysis without identification | No face embeddings or identity matching. |
| R09 | Public interface and keyed integration access | Keyed routes exist. This release is a loopback service; an independently reachable TLS deployment is not claimed. |
| R10 | Exact asynchronous integration routes | POST `/api/v1/analyze`, multipart `file`; GET `/api/v1/jobs/{job_id}`; `processing`, `done`, `failed`. UI bearer routes share the job service. |
| R11 | Result within 300 seconds | Admission deadlines include queue time and hard-stop isolated processing. Historical latency checks do not qualify every future model or target host. |
| R12 | Restricted data and evaluation separation | Source media, derived features, split identities and predictions remain private. No integration upload is automatically used for training. |
| R13 | Suitable code and weight licenses | Weight preparation checks official provenance and hashes. Every newly considered model needs its own license and performance record before promotion. |
| R14 | Reproducible handoff | README, operations, model card, qualification checks, environment template and startup scripts cover the actual local service and remaining limits. |

The suggested stack in the prompt pack is a proposal. This implementation uses SQLite and private local files to support the available Windows CPU environment without Docker. That is an explicit adaptation; it is not a claim that Supabase or a public hosted profile was deployed. See `decisions.md`.

Software readiness and detection quality are separate. Test passes, a larger model or a polished interface cannot by themselves establish semantic accuracy, changed-camera robustness or release qualification.
