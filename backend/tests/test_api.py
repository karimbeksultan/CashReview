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


def test_sponsor_reference_display_is_independent_of_model_and_absent_from_jury(settings, tmp_path):
    from dataclasses import replace
    import hashlib
    import json
    registry = tmp_path / "private-reference.json"
    digest = hashlib.sha256(MOV).hexdigest()
    registry.write_text(json.dumps({"schema_version": 1, "labels": {digest: {
        "verdict": "no_violation", "type": None, "source": "supplied sponsor workbook", "timestamps_sec": []
    }}}), encoding="utf-8")
    model_result = {"verdict": "violation", "violations": [{"type": "visual_review_signal"}],
                    "metadata": {"model_version": "test-only"}}
    with TestClient(create_app(replace(settings, reference_labels_path=registry))) as client:
        known = upload(client).json()
        auth = {"Authorization": f"Bearer {known['access_token']}"}
        path = f"/api/ui/jobs/{known['job_id']}"
        assert "sponsor_reference" not in client.get(path, headers=auth).json()
        store = client.app.state.store
        claim = store.claim(30)
        assert store.finish(known["job_id"], claim["claim_token"], model_result)
        response = client.get(path, headers=auth).json()
        assert response["result"] == model_result
        assert response["sponsor_reference"] == {"available": True, "verdict": "no_violation", "type": None,
                                                   "source": "supplied sponsor workbook", "timestamps_sec": []}
        assert digest not in str(response) and str(registry) not in str(response)

        jury = upload(client, ui=False).json()
        claim = store.claim(30)
        assert store.finish(jury["job_id"], claim["claim_token"], model_result)
        jury_response = client.get(f"/api/v1/jobs/{jury['job_id']}", headers={"X-API-Key": KEY}).json()
        assert jury_response["verdict"] == "violation" and "sponsor_reference" not in jury_response

        unknown = upload(client, body=MOV + b"unseen source").json()
        claim = store.claim(30)
        assert store.finish(unknown["job_id"], claim["claim_token"], model_result)
        unknown_response = client.get(f"/api/ui/jobs/{unknown['job_id']}",
                           headers={"Authorization": f"Bearer {unknown['access_token']}"}).json()
        assert unknown_response["result"] == model_result
        assert unknown_response["sponsor_reference"] == {"available": False, "verdict": None, "type": None, "source": None}
