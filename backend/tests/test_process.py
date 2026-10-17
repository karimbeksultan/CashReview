"""Native decoder isolation and hard deadline tests use explicit child targets."""

import base64
import multiprocessing
from pathlib import Path
import time

import cv2
import numpy as np
import pytest

from cash_review.worker import run_analysis, validate_result


def hanging_child(connection, source, deadline):
    while True:
        time.sleep(1)


def successful_child(connection, source, deadline):
    _, image = cv2.imencode(".jpg", np.zeros((16, 16, 3), dtype=np.uint8))
    result = {"verdict": "violation", "violations": [{"type": "visual_review_signal", "rule_id": "CR-001",
              "description": "Model-selected review moment", "timecode_sec": 1.0,
              "evidence_frames": [{"timestamp_sec": 1.0, "image_base64": base64.b64encode(image).decode()}]}],
              "metadata": {"duration_sec": 10.0}}
    connection.send(("progress", 50, "sampling"))
    connection.send(("result", result))
    connection.close()


def validated_analysis_child(connection, source, deadline):
    from types import SimpleNamespace
    import cash_review.worker as worker
    _, image = cv2.imencode(".jpg", np.zeros((16, 16, 3), dtype=np.uint8))
    encoded = base64.b64encode(image).decode() if source != "broken.mov" else base64.b64encode(b"\xff\xd8broken\xff\xd9").decode()
    result = {"verdict": "violation", "violations": [{"type": "visual_review_signal", "rule_id": "CR-001",
              "description": "Candidate review moment", "timecode_sec": 1.0,
              "evidence_frames": [{"timestamp_sec": 1.0, "image_base64": encoded}]}], "metadata": {"duration_sec": 10.0}}
    worker.get_engine = lambda: SimpleNamespace(analyze_video=lambda *args: result)
    worker._analysis_process(connection, source, deadline)


def test_hanging_decoder_is_killed_then_next_job_can_complete():
    before = {process.pid for process in multiprocessing.active_children()}
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        run_analysis(Path("unused.mov"), time.monotonic() + 0.5, lambda *args: None, child_target=hanging_child)
    assert time.monotonic() - started < 4
    assert {process.pid for process in multiprocessing.active_children()} <= before
    progress = []
    result = run_analysis(Path("unused.mov"), time.monotonic() + 20,
                          lambda *args: progress.append(args), child_target=successful_child)
    assert validate_result(result)["verdict"] == "violation"
    assert progress == [(50, "sampling")]


def test_native_evidence_validation_runs_in_child_and_parent_needs_no_decoder(monkeypatch):
    monkeypatch.setattr(cv2, "imdecode", lambda *args: pytest.fail("Parent process invoked a native JPEG decoder"))
    result = run_analysis(Path("valid.mov"), time.monotonic() + 20, lambda *args: None,
                          child_target=validated_analysis_child)
    assert validate_result(result, decode_images=False)["verdict"] == "violation"
    with pytest.raises(ValueError):
        run_analysis(Path("broken.mov"), time.monotonic() + 20, lambda *args: None,
                     child_target=validated_analysis_child)
