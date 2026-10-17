# Operating Cash Review

## Data path

The browser sends a MOV directly to FastAPI. Bounded admission writes it to private local storage and creates a durable SQLite job. The scheduler claims work with a unique token and expiring lease. A separate child process decodes, scores temporal evidence, and validates JPEGs. Only the current unexpired claim can publish a complete result.

Human decisions live in a separate table linked to the job. They never mutate the model’s immutable verdict/evidence and never enter training automatically. Deleting an expired job cascades its review. Refreshing a browser loses its in-memory token; the server retains the review until the job expires.

## Configuration

Read `.env.example` for limits and private directories. The shell launcher accepts `-ModelDir`, `-ApiKey`, `-Python`, and `-Port`. It creates `runtime/api-key.txt` when no key is supplied. Do not commit the key, runtime directory, source recordings, labels, feature caches, or trained artifacts.

Evidence preserves native resolution up to a 1,280-pixel side at JPEG quality 88. `CASH_REVIEW_EVIDENCE_MAX_SIDE` accepts a maximum side clamped to 640–1,920 pixels; smaller source frames are never enlarged. Aggregate result-size validation still applies.

Run one Uvicorn process. Default analysis concurrency is one and queue capacity is eight. API rate limits are process-local; a public ingress must add total connection, body and timeout limits. The request-to-result deadline is 300 seconds, including upload parsing and queue wait. Admission rejects overload explicitly; timed-out jobs fail and their child processes terminate.

## Security and resource boundaries

- Integration routes require `X-API-Key`. They cannot retrieve browser-owned jobs.
- Browser jobs require their own opaque bearer token. Tokens stay out of URLs, source, logs and local storage.
- Write requests validate browser origins; CORS does not replace authorization.
- Upload bodies, concurrent admissions, review JSON, notes, media dimensions and aggregate evidence are bounded.
- Native image/video work is isolated in the killable child; parent validation does not decode attacker-controlled images.
- Results and private media use `Cache-Control: no-store`.
- Default retention is 24 hours; tokens expire after two hours. Include host backups, caches and logs in the retention policy.

Use encrypted, access-controlled host storage. On Windows, filesystem access follows host ACLs; POSIX runtime directories use owner-only permissions. Run the container as its unprivileged user. The compose bind is loopback.

## Deployment verification

Build the frontend before starting the backend. Check liveness separately from readiness: a live process can still lack valid model artifacts. Exercise authorized uploads, invalid keys, per-job isolation, corrupt input, review persistence, restart recovery and retention on the target host.

The intended competition run is on the organizers' infrastructure. This repository and its source archive contain application source and aggregate reports; they contain no prepared detector weights, source recordings, labels or credentials. Arrange a permitted private model directory separately and record its hashes/version. The current failed baseline is suitable only for demonstrating the experimental workflow; no qualified replacement has been established. Do not substitute an unqualified research checkpoint into the serving engine.

For the provided Compose option, prepare `./models`, set a new `CASH_REVIEW_API_KEY` in the host's private `.env`, and run `docker compose up --build -d` from the repository root. Set `CASH_REVIEW_ALLOWED_ORIGINS` to include the exact HTTPS browser origin used by the organizers' ingress; Compose forwards it to the container. The model mount is read-only and runtime state uses the `review-runtime` volume. The port is bound to host loopback; remote access requires the organizers' ingress configuration. Image construction may download dependencies, so prepare the image before the disconnected check. Docker execution and target-host performance have not been verified here.

Record the organizers' CPU/GPU, memory, operating system, model hashes and cold/warm upload-to-result times. Local neural extraction timings are research measurements on this laptop and cannot establish service latency on that host. The binary API contract remains stable; the browser requires human review unless the job itself records both quality qualification fields.

Before exposing the service, verify TLS, direct backend routing, body/time limits, five-client throughput, longest permitted clips and access from another network. Prepare dependencies and weights before testing with network access disabled. Docker packaging is provided; its target-host execution must be checked independently of local Python tests.

## Recovery

Restart the service after replacing model artifacts or configuration. Artifact validation rejects missing/corrupt models. Interrupted jobs can be reclaimed after their lease expires while their admission deadline still permits a retry. Expired jobs cannot be resurrected. Locked media files are retried by later cleanup passes.

Keep a prior qualified artifact directory for rollback. Compare model versions and preprocessing configurations when diagnosing changes. Preserve private error diagnostics without logging videos, frame payloads, notes or credentials.
