# Demo runbook

The demonstration should make one complete review decision inspectable: upload -> processing -> independent model/reference comparison -> timestamp -> source frame -> source context. Use the running local service at `http://127.0.0.1:8000` and identify the actual build/model version. Rehearsal is not held-out evaluation.

The service path is working, while detection quality is inadequate: V1 flagged all eight held-out clips, including all four normal clips (50% accuracy, 0% specificity). Three sequential loopback HTTP jobs finished in 5.812–20.375 seconds, with 12 decoded bounded JPEGs. These functional checks do not establish public availability, concurrent capacity, offline verification or correct detection. Keep that distinction in the introduction and conclusion.

## Before the demonstration

- Start the exact tested configuration using README instructions; confirm readiness reports the actual model and decoder state.
- Choose permitted footage. Keep hackathon/jury footage and output frames private; use self-created permitted material for any public recording or screenshot.
- Complete an independent API upload/poll check with the real jury key. Check the key is absent from browser assets, presentation, terminal history shown on screen and repository files.
- Record real cold startup and upload-to-result timings on named hardware. If they have not been measured, say so.
- Have [service verification](service_verification.json), [evaluation](evaluation.json) and the [model card](model_card.md) ready. Do not substitute feature-extraction/engine timing for the measured HTTP timing or present an all-positive model as reliable.
- Open the evidence/rule view, check its language and confirm `CR-001` is visibly context only with legal claims disabled.
- Verify negative and failure states separately; a failure must never appear as "no violation".
- If public URLs are unavailable, introduce the demo as local and keep public availability listed as a release blocker.

## Live sequence

| Step | Action | Claim that can be supported |
| --- | --- | --- |
| 1 | State the reviewer need in one sentence | The product helps prioritize visible video fragments for human checking |
| 2 | Upload a permitted known demonstration clip | The reviewer can submit a new file without running code manually |
| 3 | Show actual processing state | A job is running; no invented progress percentage or estimated success |
| 4 | Open the model/reference comparison | Model decision is the independent prediction. Sponsor reference is the optional original binary label for recognized supplied content, with type unspecified; a new unmatched upload has no reference |
| 5 | Select one event and inspect its frame/time | The model-selected moment can be checked against original video content |
| 6 | Open the source context | CR-001 links an official source, while legal applicability and semantic category remain unverified |
| 7 | Briefly show a separate jury client | Exact path, key authentication, job polling and actual JSON are inspectable |
| 8 | Show measured evaluation and one concrete failure case | Only recorded metrics and observed limitations may be stated |

At the current stage, call an event a **visual review signal**. Do not narrate it as theft, unauthorized access, an omitted required action or a legal breach unless a reviewed semantic rule has actually been enabled and tested.

For a known normal demonstration clip, show any disagreement openly: a model flag beside a normal sponsor reference is a false positive, not a corrected model result. The private content-hash reference lookup serves UI comparison only, never inference or the jury API. Sponsor timestamps are source annotations, not predictions. The workbook does not specify event categories, so never fill in a sponsor type from assumptions.

The synthetic preview remains a separate mode with illustrative answers and a visible banner. Use that mode for public interface screenshots; do not treat its scene, scores or frames as model evidence.

## If analysis does not finish during the pitch

Show a previously completed result, clearly identified by its actual run time and model version. Keep the live job visible if useful, without promising a result before it arrives. A saved result demonstrates interface behavior, not a successful live submission or unseen-video generalization. A timeout/failure is disclosed and retained in the completion denominator.

A backup recording may use only permitted footage and outputs. Label it as a recording and keep restricted material off public video hosts. If a model, weight file or rule is missing, show failed readiness and the narrow setup issue; never switch to a silent fake classifier.

## Rehearsal record

Fill this before presenting: build revision; model hash/version; hardware; input identifier held privately; startup time; upload-to-result time; verdict; evidence decode result; API authentication result; network used; failures observed; presenter; rehearsal date.

The case's primary pitch is five minutes plus two minutes of questions. [Pitch outline](pitch_outline.md) gives the sequence and the explicit claims that still need evidence.
