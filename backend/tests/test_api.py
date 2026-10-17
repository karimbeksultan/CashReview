"""Contract tests use an injected fake detector, never a production fallback."""

import importlib
from pathlib import Path
from types import SimpleNamespace
import time

from fastapi.testclient import TestClient
import pytest

from cash_review.app import create_app
from cash_review.config import Settings


MOV = b"\x00\x00\x00\x18ftypqt  " + b"\0" * 24
KEY = "test-only-key-never-used-in-production"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    registry = tmp_path / "rules.json"
    registry.write_text('{"version":"test","rules":[{"id":"CR-001"}]}', encoding="utf-8")
    return Settings(data_dir=tmp_path / "private", api_key=KEY, rules_path=registry,
                    start_worker=False, max_upload_bytes=1024, upload_rate_limit=30)


@pytest.fixture(autouse=True)
def detector(monkeypatch):
    engine = SimpleNamespace(readiness=lambda: {"ready": True, "reasons": [], "competition_ready": False},
                             analyze_video=lambda *args: {"verdict": "no_violation", "violations": [],
                                                          "metadata": {"duration_sec": 10.0}})
    monkeypatch.setattr(importlib.import_module("cash_review.worker"), "get_engine", lambda: engine)
    monkeypatch.setattr(importlib.import_module("cash_review.worker"), "run_analysis",
                        lambda source, deadline, progress, stop=None: engine.analyze_video(source, deadline, progress))
    return engine


def upload(client: TestClient, ui: bool = True, body: bytes = MOV, filename: str = "sample.mov"):
    return client.post("/api/ui/analyze" if ui else "/api/v1/analyze",
                       files={"file": (filename, body, "video/quicktime")},
                       headers={} if ui else {"X-API-Key": KEY})


def test_exact_jury_contract_requires_key_and_never_returns_ui_token(settings):
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/v1/analyze", files={"file": ("sample.mov", MOV)}).status_code == 401
        assert client.get("/api/v1/jobs/" + "a" * 32).status_code == 401
        response = upload(client, ui=False)
        assert response.status_code == 202
        assert set(response.json()) == {"job_id"}
        job_id = response.json()["job_id"]
        response = client.get(f"/api/v1/jobs/{job_id}", headers={"X-API-Key": KEY})
        assert response.json()["status"] == "processing"
        assert "verdict" not in response.json()


def test_ui_tokens_are_scoped_hash_only_and_media_is_private(settings):
    with TestClient(create_app(settings)) as client:
        first, second = upload(client).json(), upload(client).json()
        path = f"/api/ui/jobs/{first['job_id']}"
        assert client.get(path).status_code == 401
        assert client.get(path, headers={"Authorization": f"Bearer {second['access_token']}"}).status_code == 404
        auth = {"Authorization": f"Bearer {first['access_token']}"}
        assert client.get(path, headers=auth).status_code == 200
        assert client.get(f"/api/v1/jobs/{first['job_id']}", headers={"X-API-Key": KEY}).status_code == 404
        media = client.get(path + "/media", headers=auth)
        assert media.status_code == 200 and media.content == MOV
        assert media.headers["cache-control"] == "no-store"
        stored = client.app.state.store.get(first["job_id"])
        assert stored["token_hash"] != first["access_token"]
        assert first["access_token"] not in settings.data_dir.joinpath("jobs.sqlite3").read_bytes().decode("latin1")


def test_upload_validation_capacity_and_file_cleanup(settings):
    from dataclasses import replace
    with TestClient(create_app(replace(settings, queue_capacity=1))) as client:
        assert upload(client, filename="bad.exe").status_code == 415
        assert upload(client, body=b"not a real video container").status_code == 415
        assert upload(client, body=MOV + b"x" * 1024).status_code == 413
        assert upload(client).status_code == 202
        assert upload(client).status_code == 429
        files = list(client.app.state.store.media_dir.iterdir())
        assert len(files) == 1 and files[0].suffix == ".mov"


def test_body_length_limit_precedes_multipart_parsing(settings):
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/ui/analyze", content=b"garbage", headers={"Content-Length": "999999999"})
        assert response.status_code == 413


def test_origin_and_rate_limits(settings):
    from dataclasses import replace
    with TestClient(create_app(replace(settings, upload_rate_limit=1))) as client:
        bad_origin = client.post("/api/ui/analyze", files={"file": ("sample.mov", MOV)},
                                 headers={"Origin": "https://untrusted.invalid"})
        assert bad_origin.status_code == 403
        assert upload(client).status_code == 202
        assert upload(client).status_code == 429


def test_unready_is_not_reported_as_no_violation(settings, detector):
    detector.readiness = lambda: {"ready": False, "reasons": ["Weights missing"]}
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health/live").status_code == 200
        ready = client.get("/api/health/ready")
        assert ready.status_code == 503 and not ready.json()["ready"]
        assert ready.json()["max_upload_bytes"] == settings.max_upload_bytes
        response = upload(client)
        assert response.status_code == 503 and "verdict" not in response.json()
        assert list(client.app.state.store.media_dir.iterdir()) == []


@pytest.mark.parametrize("fails", [False, True])
def test_worker_publishes_result_or_safe_failed_state(settings, detector, fails):
    from dataclasses import replace
    if fails:
        def raise_private(*args):
            raise RuntimeError("PRIVATE_SECRET and /private/media.mov")
        detector.analyze_video = raise_private
    with TestClient(create_app(replace(settings, start_worker=True))) as client:
        admitted = upload(client, ui=False).json()
        path = f"/api/v1/jobs/{admitted['job_id']}"
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            result = client.get(path, headers={"X-API-Key": KEY}).json()
            if result["status"] != "processing":
                break
            time.sleep(0.05)
        assert result["status"] == ("failed" if fails else "done")
        if fails:
            assert "PRIVATE_SECRET" not in str(result) and "verdict" not in result
        else:
            assert result["verdict"] == "no_violation" and result["violations"] == []


def test_token_expiry_is_enforced(settings):
    with TestClient(create_app(settings)) as client:
        admitted = upload(client).json()
        with client.app.state.store.connection() as db:
            db.execute("UPDATE jobs SET token_expires_at=? WHERE id=?", (time.time() - 1, admitted["job_id"]))
        response = client.get(f"/api/ui/jobs/{admitted['job_id']}",
                              headers={"Authorization": f"Bearer {admitted['access_token']}"})
        assert response.status_code == 404


def test_deadline_includes_queue_wait_and_late_worker_cannot_publish(settings, detector):
    from dataclasses import replace
    import threading
    started = threading.Event()
    def slow_analysis(*args):
        started.set()
        time.sleep(0.8)
        return {"verdict": "no_violation", "violations": [], "metadata": {}}
    detector.analyze_video = slow_analysis
    with TestClient(create_app(replace(settings, start_worker=True, deadline_seconds=0.5))) as client:
        admitted = upload(client, ui=False).json()
        path = f"/api/v1/jobs/{admitted['job_id']}"
        assert started.wait(2)
        time.sleep(0.6)
        failed = client.get(path, headers={"X-API-Key": KEY}).json()
        assert failed["status"] == "failed" and failed["error"]["code"] == "deadline_exceeded"
        time.sleep(0.4)
        assert client.get(path, headers={"X-API-Key": KEY}).json()["status"] == "failed"


def test_multipart_parsing_consumes_deadline_and_slow_upload_times_out(settings):
    import asyncio
    from dataclasses import replace
    from cash_review.app import BoundaryMiddleware
    config = replace(settings, deadline_seconds=0.1)
    observed = {}
    sent = []
    async def target(scope, receive, send):
        observed["admitted_at"] = scope["state"]["admitted_at"]
        await receive()
    async def receive():
        await asyncio.sleep(0.2)
        return {"type": "http.request", "body": b"video", "more_body": False}
    async def send(message):
        sent.append(message)
    scope = {"type": "http", "method": "POST", "path": "/api/ui/analyze", "headers": [],
             "scheme": "http", "client": ("test", 1)}
    started = time.time()
    asyncio.run(BoundaryMiddleware(target, config)(scope, receive, send))
    assert observed["admitted_at"] >= started
    assert sent[0]["status"] == 408


def test_human_review_persists_separately_from_immutable_model_and_jury(settings):
    model_result = {"verdict": "violation", "violations": [{"type": "visual_review_signal"}],
                    "metadata": {"model_version": "test-only"}}
    with TestClient(create_app(settings)) as client:
        known = upload(client).json()
        auth = {"Authorization": f"Bearer {known['access_token']}"}
        path = f"/api/ui/jobs/{known['job_id']}"
        assert client.get(path, headers=auth).json()["human_review"] is None
        store = client.app.state.store
        claim = store.claim(30)
        assert store.finish(known["job_id"], claim["claim_token"], model_result)
        immutable = store.get(known["job_id"])["result_json"]
        saved = client.post(path + "/review", headers=auth,
                            json={"decision": "no_violation", "notes": "Проверено вручную", "event_index": 0})
        assert saved.status_code == 200
        response = client.get(path, headers=auth).json()
        assert response["result"] == model_result
        assert response["human_review"] == saved.json()["human_review"]
        assert response["human_review"]["decision"] == "no_violation"
        assert store.get(known["job_id"])["result_json"] == immutable
        assert "sponsor_reference" not in response
        changed = client.post(path + "/review", headers=auth,
                              json={"decision": "needs_review", "notes": "", "event_index": None})
        assert changed.status_code == 200
        assert client.get(path, headers=auth).json()["human_review"]["decision"] == "needs_review"

        jury = upload(client, ui=False).json()
        claim = store.claim(30)
        assert store.finish(jury["job_id"], claim["claim_token"], model_result)
        # Even a separately stored review can never change or enter jury output.
        store.save_review(jury["job_id"], "no_violation", "Private human judgment")
        jury_response = client.get(f"/api/v1/jobs/{jury['job_id']}", headers={"X-API-Key": KEY}).json()
        assert jury_response["verdict"] == "violation" and "human_review" not in jury_response
        assert "sponsor_reference" not in jury_response


def test_review_requires_same_job_token_completed_analysis_and_allowed_origin(settings):
    with TestClient(create_app(settings)) as client:
        first, second = upload(client).json(), upload(client).json()
        path = f"/api/ui/jobs/{first['job_id']}/review"
        payload = {"decision": "no_violation", "notes": ""}
        auth = {"Authorization": f"Bearer {first['access_token']}"}
        assert client.post(path, json=payload).status_code == 401
        assert client.post(path, headers={"Authorization": f"Bearer {second['access_token']}"}, json=payload).status_code == 404
        assert client.post(path, headers=auth, json=payload).status_code == 409
        assert client.post(path, headers={**auth, "Origin": "https://untrusted.invalid"}, json=payload).status_code == 403
        claim = client.app.state.store.claim(30)
        client.app.state.store.fail(first["job_id"], claim["claim_token"], "test", "test failure")
        assert client.post(path, headers=auth, json=payload).status_code == 409


@pytest.mark.parametrize("payload", [
    {"decision": "invented", "notes": ""},
    {"decision": "violation", "notes": "a" * 4001},
    {"decision": "violation", "notes": 123},
    {"decision": "violation", "notes": "", "event_index": -1},
    {"decision": "violation", "notes": "", "event_index": 1},
    {"decision": "violation", "notes": "", "event_index": 0.5},
    {"decision": "violation", "notes": "", "event_index": True},
    {"decision": "violation", "notes": "", "username": "not-supported"},
])
def test_review_validation_rejects_invalid_decision_notes_and_event(settings, payload):
    with TestClient(create_app(settings)) as client:
        admitted = upload(client).json()
        store = client.app.state.store
        claim = store.claim(30)
        store.finish(admitted["job_id"], claim["claim_token"], {"verdict": "no_violation", "violations": []})
        response = client.post(f"/api/ui/jobs/{admitted['job_id']}/review",
                   headers={"Authorization": f"Bearer {admitted['access_token']}"}, json=payload)
        assert response.status_code == 422
        assert store.get_review(admitted["job_id"]) is None


def test_review_body_has_a_preparse_limit(settings):
    with TestClient(create_app(settings)) as client:
        admitted = upload(client).json()
        response = client.post(f"/api/ui/jobs/{admitted['job_id']}/review",
                    headers={"Authorization": f"Bearer {admitted['access_token']}", "Content-Type": "application/json"},
                    content=b"x" * (32 * 1024 + 1))
        assert response.status_code == 413
        assert client.post("/api/ui/jobs/malformed-id/review", content=b"x" * (32 * 1024 + 1)).status_code == 413


def test_chunked_review_body_is_bounded_before_json_parse(settings):
    with TestClient(create_app(settings)) as client:
        admitted = upload(client).json()
        def oversized_body():
            yield b'{"notes":"'
            yield b"x" * (32 * 1024)
            yield b'"}'
        response = client.post(f"/api/ui/jobs/{admitted['job_id']}/review",
                     headers={"Authorization": f"Bearer {admitted['access_token']}", "Content-Type": "application/json"},
                     content=oversized_body())
        assert response.status_code == 413


def test_concurrent_uploads_are_bounded_and_admission_slot_released(settings):
    import asyncio
    from dataclasses import replace
    from cash_review.app import BoundaryMiddleware
    async def exercise():
        release = asyncio.Event()
        entered = asyncio.Event()
        statuses = []
        async def target(scope, receive, send):
            entered.set()
            await release.wait()
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}
        async def send(message):
            if message["type"] == "http.response.start":
                statuses.append(message["status"])
        boundary = BoundaryMiddleware(target, replace(settings, queue_capacity=1))
        def scope():
            return {"type": "http", "method": "POST", "path": "/api/ui/analyze", "headers": [],
                    "scheme": "http", "client": ("test", 1)}
        first = asyncio.create_task(boundary(scope(), receive, send))
        await entered.wait()
        await boundary(scope(), receive, send)
        assert statuses == [429]
        release.set()
        await first
        await boundary(scope(), receive, send)
        assert statuses == [429, 204, 204]
        assert boundary.uploads_in_flight == 0
    asyncio.run(exercise())
