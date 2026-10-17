# Quality and release checks

Model readiness means valid artifacts and a working runtime. It does not mean every concern is detected or every normal recording is rejected. Detection quality must be assessed separately from software tests.

## Required evidence

1. Reproducible model version, verified artifact hashes, dependency and weight-license records.
2. Content-group-separated training/selection/evaluation. Keep exact duplicates together and review residual session correlation.
3. Per-class confusion matrices, specificity, recall, precision, completion rate, and confidence intervals. Reject trivial all-positive and all-negative models.
4. No filename, hash, source-label or known-identity lookup in inference. No automated training from review feedback or integration submissions.
5. Honest distinction between an untouched holdout, development validation, and a previously seen exploratory test. Do not tune after viewing the test and then call it fresh.
6. Human-reviewed event intervals/types before claiming semantic action accuracy; binary source labels alone cannot establish it.
7. Verified applicable rule predicates before legal claims. Regulatory context is not evidence of a breached rule.
8. Accurate evidence times, decodable real JPEGs, and quality/coverage limitations in the result.
9. Measured upload-to-result latency including queue wait, bounded five-client load, restart recovery and explicit failures.
10. Target-host disconnected operation, TLS and independent-network reachability for remote use.

## Current evidence

Consult `evaluation.json` and the model card for the selected detector and its limitations. Historical baseline failures are retained as diagnostics, not advertised as successful detection. Software contract tests use synthetic inputs; they cannot establish model accuracy. The [software verification record](verification.md) covers the synthetic interface and human-review interaction separately from real-recording API checks. [Model studies](model_studies.md) record candidates rejected during development.

The supplied source labels do not provide semantic event types or complete intervals. Alternate-camera, unseen-action, rule-grounding and target-host release checks need their own evidence. No accuracy guarantee follows from the interface, an API schema, or a small same-camera dataset.
