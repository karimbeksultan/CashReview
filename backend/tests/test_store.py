import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from cash_review.store import JobStore, QueueFull
from cash_review.worker import validate_result


def add(store: JobStore, name: str, now: float = 100):
    return store.create(name, name + ".mov", 20, "test-sha", 300, 86400, now=now)


def test_durable_jobs_survive_reopen_and_stale_claim_is_fenced(tmp_path: Path):
    original = JobStore(tmp_path)
    add(original, "a")
    first = original.claim(30, now=101)
    assert first is not None
    reopened = JobStore(tmp_path)
    assert reopened.get("a")["status"] == "processing"
    assert reopened.claim(30, now=110) is None
    second = reopened.claim(30, now=132)
    assert second["claim_token"] != first["claim_token"]
    result = {"verdict": "no_violation", "violations": [], "metadata": {}}
    assert not original.finish("a", first["claim_token"], result, now=133)
    assert reopened.finish("a", second["claim_token"], result, now=134)


def test_atomic_admission_does_not_exceed_capacity(tmp_path: Path):
    store = JobStore(tmp_path, capacity=2)
    def attempt(index):
        try:
            add(store, str(index))
            return True
        except QueueFull:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(attempt, range(12)))
    assert sum(outcomes) == 2


def test_claim_is_unique_across_concurrent_workers(tmp_path: Path):
    store = JobStore(tmp_path)
    add(store, "one")
    with ThreadPoolExecutor(max_workers=6) as pool:
        claims = list(pool.map(lambda _: store.claim(30, now=101), range(6)))
    assert len([claim for claim in claims if claim]) == 1


def test_expired_lease_cannot_renew_publish_fail_or_change_progress(tmp_path: Path, monkeypatch):
    store = JobStore(tmp_path)
    add(store, "one")
    claim = store.claim(30, now=101)
    store.heartbeat("one", claim["claim_token"], 30, now=132)
    assert store.get("one")["lease_until"] == 131
    assert not store.finish("one", claim["claim_token"], {"verdict": "no_violation"}, now=132)
    assert not store.fail("one", claim["claim_token"], "test", "test", now=132)
    monkeypatch.setattr("cash_review.store.time.time", lambda: 132)
    store.progress("one", claim["claim_token"], 90, "stale")
    assert store.get("one")["progress"] == 1
    replacement = store.claim(30, now=132)
    assert replacement["claim_token"] != claim["claim_token"]
    assert not store.fail("one", claim["claim_token"], "test", "test", now=133)


def test_deadline_marks_failed_and_prevents_late_publication(tmp_path: Path):
    store = JobStore(tmp_path)
    add(store, "one")
    claim = store.claim(30, now=101)
    assert store.expire_deadlines(now=400) == 1
    assert store.get("one")["error_code"] == "deadline_exceeded"
    assert not store.finish("one", claim["claim_token"], {"verdict": "no_violation"}, now=401)


def test_expired_data_is_deleted_and_paths_cannot_escape(tmp_path: Path):
    store = JobStore(tmp_path)
    add(store, "one")
    path = store.media_path("one.mov")
    path.write_bytes(b"private source")
    claim = store.claim(30, now=101)
    store.finish("one", claim["claim_token"], {"verdict": "no_violation"}, now=102)
    assert store.cleanup(now=90000) == 1
    assert store.get("one") is None and not path.exists()
    with pytest.raises(ValueError):
        store.media_path("../secret")


def test_result_validation_rejects_contradictions_and_missing_evidence():
    with pytest.raises(ValueError):
        validate_result({"verdict": "no_violation", "violations": [{"type": "x"}]})
    with pytest.raises(ValueError):
        validate_result({"verdict": "violation", "violations": []})
    event = {"type": "visual_review_signal", "description": "Review this event", "rule_id": "CR-001",
             "timecode_sec": 2, "evidence_frames": []}
    with pytest.raises(ValueError):
        validate_result({"verdict": "violation", "violations": [event]})
    event["evidence_frames"] = [{"timestamp_sec": 2, "image_base64": base64.b64encode(b"not JPEG").decode()}]
    with pytest.raises(ValueError):
        validate_result({"verdict": "violation", "violations": [event]})
    event["evidence_frames"][0]["image_base64"] = base64.b64encode(b"\xff\xd8broken JPEG\xff\xd9").decode()
    with pytest.raises(ValueError):
        validate_result({"verdict": "violation", "violations": [event]})


def test_upload_admission_time_reduces_processing_budget(tmp_path: Path):
    store = JobStore(tmp_path)
    job = store.create("one", "one.mov", 20, "sha", 300, 86400, now=120, admitted_at=100)
    assert job["created_at"] == 100 and job["deadline_at"] == 400
    with pytest.raises(TimeoutError):
        store.create("two", "two.mov", 20, "sha", 300, 86400, now=500, admitted_at=100)
