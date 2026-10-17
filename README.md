# Cash Review

Local video analysis with large, timestamped evidence and a clear human-review workflow.

Upload a video, inspect candidate moments in the original recording, and record a human decision with notes. The model result stays separate from the reviewer’s assessment. Cash Review does not identify people or establish legal wrongdoing.

**Detection status:** the active V1 baseline failed to distinguish normal clips in its original eight-clip test. Stronger local candidates, including SigLIP2 fine-tuning, Qwen3-VL, DINOv2 normal-memory models and learned local/transition MIL heads, also failed their frozen quality gates. Reliable automatic detection has not been established. The interface and API support experimental analysis and independent human review. See the [measured model studies](docs/model_studies.md).

![Review workspace](docs/interface-preview.jpg)

## Features

- English/Russian interface with a large result summary, video player and timestamp navigation.
- Enlarged evidence frames with an accessible full-size viewer and zoom.
- Persistent **Confirm concern**, **No concern**, and **Needs more review** decisions with notes.
- Neutral **Human review required** summary for any result without recorded quality qualification. Candidate moments remain available; this abstention does not change the model's measured accuracy.
- Local CPU inference, private uploads and actual source-frame JPEGs.
- Durable SQLite jobs, scoped access, isolated analysis processes and a five-minute deadline.
- Keyed integration API, reproducible model evaluation, CI and optional Docker packaging.

See the [model card](docs/model_card.md), [evaluation](docs/evaluation.json), [requirements review](docs/requirements.md) and [quality checks](docs/qualification.md) for the measured detection limits. Passing software tests is separate from model accuracy.

## Install

Use Python 3.12 and Node.js 22. Keep permitted training data and model artifacts outside source control.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.lock.txt
cd frontend
npm ci --no-audit --no-fund
npm run build
cd ..
```

Model preparation commands and required artifacts are in the [model card](docs/model_card.md). The running API never downloads weights.

Training requires a fresh private artifact directory. Prepared backbone files, a frozen split and bound feature caches may exist, but model files or completed validation/evaluation reports block retraining so historical failures and results remain intact. Reuse the frozen split when comparing candidates; a new directory does not make an exposed test cohort fresh.

New models bind the backbone, preprocessing, sampling interval and runtime versions to their caches. Legacy aggregate reports remain readable; `evaluate.py --repeat` or `--runtime-smoke` requires a newly trained model with matching versioned feature bindings in a separate artifact directory. These tooling changes do not retrain or replace the active detector.

After preparing `models/`:

```powershell
./scripts/start.ps1 -ModelDir models
```

Open [Cash Review](http://127.0.0.1:8000). The launcher generates a private integration key in `runtime/api-key.txt` if none is configured. Missing or corrupt model artifacts produce readiness 503 and disable real analysis. The marked synthetic preview remains available.

On Linux/macOS, activate the environment, export `CASH_REVIEW_MODEL_DIR`, `CASH_REVIEW_DATA_DIR`, and a unique `CASH_REVIEW_API_KEY`, then run:

```sh
python -m uvicorn cash_review.app:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Development: run `npm run dev` in `frontend/`; Vite forwards `/api` to port 8000. Production serves the built interface from the backend. Fonts are local. Optional `VITE_API_BASE_URL` must never contain a key.

## Integration API

Send `X-API-Key` on every `/api/v1/` request. The browser receives a separate token scoped to one job.

```sh
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H "X-API-Key: $CASH_REVIEW_API_KEY" -F "file=@clip.mov"
# 202: {"job_id":"..."}
curl http://127.0.0.1:8000/api/v1/jobs/JOB_ID \
  -H "X-API-Key: $CASH_REVIEW_API_KEY"
```

Poll once per second. States: `processing`, `done`, `failed`. Completed model verdicts: `violation` or `no_violation`; both require human interpretation. Failures have an error and no verdict. Events contain type, source time, description, context reference and 1–3 actual base64 JPEGs.

The browser shows a binary assessment only when that job's own metadata records both `quality_validated: true` and `validation_status: "validated"`. Otherwise its summary requires human review, regardless of the raw threshold verdict. Legacy API results and evidence stay immutable. This presentation rule is an abstention safeguard, not a classifier improvement or a qualification claim.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health/live` | Process liveness |
| `GET /api/health/ready` | Configuration, model integrity and registry readiness |
| `POST /api/v1/analyze` | Keyed multipart upload in field `file` |
| `GET /api/v1/jobs/{job_id}` | Keyed status and immutable model result |
| `POST /api/ui/analyze` | Browser upload and scoped token |
| `GET /api/ui/jobs/{job_id}` | Browser result and separate human review |
| `POST /api/ui/jobs/{job_id}/review` | Save the human decision and notes |
| `GET /api/ui/jobs/{job_id}/media` | Authorized private media |
| `GET /api/rules` | Cached regulatory context |
| `GET /docs` | OpenAPI documentation |

Human-review input: `{"decision":"violation|no_violation|needs_review","notes":"...","event_index":null}`. Notes are limited to 4,000 characters. Only completed jobs can be reviewed. Reviews never overwrite model results or enter training automatically.

## Operations

The 300-second deadline includes upload parsing and queue wait. Expired worker claims cannot publish. Native decoding and JPEG validation run in a child process terminated at its deadline. Run one Uvicorn process; `CASH_REVIEW_WORKERS` controls the bounded analysis executor. Benchmark before increasing concurrency.

Uploads are limited to 64 MiB and checked as MOV containers. Decoded dimensions and aggregate evidence size are bounded. Runtime media, results and reviews expire after 24 hours; job tokens expire after two hours. Refreshing the page loses the in-memory token. Keep runtime files, host backups and logs private. See [operations](docs/operations.md).

After dependency and weight preparation, processing uses local files and no cloud AI service. Verify disconnected operation and network reachability on the intended deployment host.

```sh
python -m pytest backend/tests -q
cd frontend && npm ci --no-audit --no-fund && npm run build
# Optional, after preparing models and setting CASH_REVIEW_API_KEY in .env:
docker compose up --build
```

Software tests use synthetic fixtures and test-only engines. Detector evaluation keeps duplicate content together and reports false positives and misses. Never tune on external-client submissions or previously evaluated holdouts.

Original code is MIT licensed. Dependencies and pretrained weights retain their own terms. No license to private source data is granted.
