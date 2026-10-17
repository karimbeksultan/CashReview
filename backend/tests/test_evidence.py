"""Evidence preserves real source resolution within explicit resource bounds."""

import base64

import cv2
import numpy as np
import pytest

from cash_review.engine import encode_evidence_frame


def decode(encoded):
    return cv2.imdecode(np.frombuffer(base64.b64decode(encoded), np.uint8), cv2.IMREAD_COLOR)


def test_default_preserves_native_source_resolution_and_uses_jpeg88(monkeypatch):
    monkeypatch.delenv("CASH_REVIEW_EVIDENCE_MAX_SIDE", raising=False)
    frame = np.zeros((848, 464, 3), np.uint8)
    frame[:, :, 1] = np.arange(464, dtype=np.uint16)[None] % 256
    encoded = encode_evidence_frame(frame)
    assert decode(encoded).shape == frame.shape
    okay, expected = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
    assert okay and base64.b64decode(encoded) == expected.tobytes()


@pytest.mark.parametrize("setting,expected", [("640", (640, 427)), ("1280", (1280, 853)),
                                               ("1920", (1920, 1280)), ("1", (640, 427)),
                                               ("99999", (1920, 1280))])
def test_evidence_side_limit_is_bounded_and_preserves_aspect_ratio(monkeypatch, setting, expected):
    monkeypatch.setenv("CASH_REVIEW_EVIDENCE_MAX_SIDE", setting)
    frame = np.zeros((2400, 1600, 3), np.uint8)
    actual = decode(encode_evidence_frame(frame))
    assert actual.shape[:2] == expected
    assert 640 <= max(actual.shape[:2]) <= 1920
    assert abs(actual.shape[1] / actual.shape[0] - 2 / 3) < .002


def test_evidence_never_upscales_and_invalid_config_fails_safely(monkeypatch):
    frame = np.zeros((32, 24, 3), np.uint8)
    monkeypatch.setenv("CASH_REVIEW_EVIDENCE_MAX_SIDE", "1920")
    assert decode(encode_evidence_frame(frame)).shape == frame.shape
    monkeypatch.setenv("CASH_REVIEW_EVIDENCE_MAX_SIDE", "invalid")
    with pytest.raises(ValueError, match="invalid_evidence_side_limit"):
        encode_evidence_frame(frame)
