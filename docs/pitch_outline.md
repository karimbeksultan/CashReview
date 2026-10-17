# Pitch outline

Use the actual build, [evaluation](evaluation.json), [service verification](service_verification.json) and deployment state. The current project is a working local service with an inadequate detector baseline. Lead with the working flow and disclose its measured failure; do not present this build as competition ready.

## Five-minute pitch

| Time | Show | Message and required evidence |
| --- | --- | --- |
| 0:00–0:20 | Upload screen | "Cash Review helps a reviewer find visible moments that need checking and inspect the evidence." One sentence of task context is enough. |
| 0:20–1:45 | Real upload, status and model/reference comparison | Identify a rehearsed known clip and any saved result honestly. Model prediction and optional original sponsor label are separate. Source type is unspecified; new content has no sponsor reference. A disagreement remains visible. |
| 1:45–2:30 | Selected timestamp and evidence | Show that a human can inspect the source moment. Current `visual_review_signal` is a generic review marker; do not claim a semantic type or a proved breach. |
| 2:30–3:15 | Actual evaluation artifact | Frozen split: 24 train, 8 validation, 8 test groups. All 8 test clips completed and were flagged, including all 4 normal clips: 50% accuracy, 0% specificity. A V2 attempt failed validation and was not tested/promoted. The priority is reducing false flags with reviewed action annotations. |
| 3:15–3:50 | Architecture and service timing | CPU-only local decoding/model execution, SQLite jobs and private evidence. Three sequential loopback HTTP jobs: 5.812/16.485/20.375 seconds; 12 JPEGs validated. Public-network, concurrency and internet-disconnected checks remain open. |
| 3:50–4:25 | Normative source view | Explain that an official contextual source has been researched. CR-001 legal claims remain disabled until an applicable clause and observable event predicate are verified. |
| 4:25–5:00 | Readiness and next improvement | State supported scope, public/API state, largest measured weakness and the next action that addresses it. Avoid a promise of universal coverage. |

## Two-minute fallback

Use 15 seconds for reviewer need; 60 seconds for the real evidence flow; 30 seconds for actual metrics and local-runtime evidence; 15 seconds for the most material limitation and next improvement. Cut optional explanation, not disclosure of a missing deployment, generic taxonomy or unverified rule mapping.

## Questions to rehearse

- **How did you avoid leakage?** Exact duplicate content stayed together; scaler/classifier used 24 train groups and threshold used 8 validation groups. The 8-group V1 test is now exposed. Near-duplicate/session grouping still needs review; future reuse of this test is exploratory.
- **What does the model classify?** The current baseline emits a generic binary review signal. A semantic event catalogue and event-level reviewed annotations remain a competition gap.
- **Does the highlighted timestamp prove an event?** It is a model-selected moment. Show localization measurements only where actual annotated ground truth permits them.
- **Which legal rule was breached?** Current CR-001 is context only. An official source link alone cannot establish a breach; do not invent a clause or internal ForteBank rule.
- **What about another camera angle?** Report actual stress or alternate-view results separately. Same-scene held-out accuracy and augmentations do not establish new-camera reliability.
- **Does it meet five minutes?** Three sequential local HTTP jobs did: 5.812, 16.485 and 20.375 seconds, including a 142.533-second clip. This does not establish concurrent or public-network performance. Hardware/software are recorded in the model card and aggregate evaluation.
- **Are you using the sponsor answers to make predictions?** No. The optional private content-hash reference registry supplies a separately labelled UI comparison after analysis. It is not read by the engine/worker, does not change model outputs and is absent from jury responses; backend regression tests cover this separation.
- **Can it work offline and publicly?** Distinguish local model execution, a verified disconnected run, and tested inbound public reachability. They are separate facts.
- **What happens to data?** State the implemented retention/cleanup behavior; no jury training, public footage or cloud AI processing. Do not claim untested deletion guarantees.
- **Are the licenses suitable?** Name actual code/model/weight licenses and any unresolved license or dependency checks.

## Scoring focus

The case assigns 25 points to detection; 15 each to localization, classification and rule grounding; 10 each to robustness, product readiness and technical/locality. The current generic classification and contextual mapping are substantive gaps in that 70-point core. Address them with reviewed evidence before adding accounts, history, batch upload or export. The required API and locality constraints remain eligibility requirements regardless of weight.

Do not state review-time savings, zero misses, high accuracy, public readiness or legal correctness without their own supporting measurements. Slides are optional; a complete, truthful product demonstration is the priority.
