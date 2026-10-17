"""Offline visual review baseline. This is not a semantic/legal violation detector.

Inference consumes pixels only: labels, clip names and source hashes are never consulted.
Preparation/training live in separate scripts and write private JSON/NPZ artifacts.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Callable

MODEL_SHA256 = "c1c513582d56afceff8516c73804e484c81c6a830712ab6d682253f4a3cd042f"
MODEL_FILE = "mobilenetv2-7.onnx"
SCHEMA_VERSION = 1
WARNINGS = [
    "Experimental visual review signal; the binary verdict is a learned baseline, not a verified legal finding.",
    "No reviewed event-type taxonomy or validated alternate-camera performance is available.",
    "Scores are uncalibrated classifier scores, not probabilities of wrongdoing.",
    "One-second sampling can miss short events; returned events are candidate review moments.",
    "OpenCV presentation timestamps are used where available; unusual edit lists or variable-rate files require independent timing review.",
]


def _model_warnings(config: dict) -> list[str]:
    warnings = list(WARNINGS)
    if config.get("schema_version") == 1:
        warnings.append("The shipped V1 baseline flagged all eight holdout clips, including four normal clips; false positives are a known material failure.")
    return warnings


def model_dir() -> Path:
    return Path(os.environ.get("CASH_REVIEW_MODEL_DIR", "var/models")).resolve()


def _deadline(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise TimeoutError("analysis_deadline_exceeded")


def _validate_dimensions(width: float, height: float) -> None:
    max_dimension = max(1920, int(os.environ.get("CASH_REVIEW_MAX_MODEL_DIMENSION", "4096")))
    max_pixels = max(1920 * 1080, int(os.environ.get("CASH_REVIEW_MAX_MODEL_PIXELS", "8000000")))
    if not math.isfinite(width) or not math.isfinite(height) or width <= 0 or height <= 0:
        raise ValueError("invalid_media_dimensions")
    if max(width, height) > max_dimension or width * height > max_pixels:
        raise ValueError("media_dimensions_limit_exceeded")


def _sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _load_artifacts(directory: Path):
    import numpy as np

    config = json.loads((directory / "baseline.json").read_text(encoding="utf-8"))
    if config.get("schema_version") not in (1, 2):
        raise ValueError("unsupported_model_schema")
    if config.get("backbone_sha256") != MODEL_SHA256 or _sha(directory / MODEL_FILE) != MODEL_SHA256:
        raise ValueError("backbone_integrity_error")
    weights_path = directory / "baseline.npz"
    if _sha(weights_path) != config.get("classifier_sha256"):
        raise ValueError("classifier_integrity_error")
    fields = ["mean", "scale", "coef", "intercept"]
    if config.get("schema_version") == 2:
        fields.extend(["gate_mean", "gate_scale", "gate_coef", "gate_intercept"])
    with np.load(weights_path, allow_pickle=False) as data:
        weights = {name: data[name].astype(np.float32) for name in fields}
    size = config["feature_dim"]
    if any(weights[name].shape != (size,) for name in ("mean", "scale", "coef")):
        raise ValueError("invalid_classifier_shape")
    if any(not np.isfinite(value).all() for value in weights.values()) or (weights["scale"] <= 0).any():
        raise ValueError("invalid_classifier_values")
    if not 0 < float(config["threshold"]) < 1:
        raise ValueError("invalid_classifier_threshold")
    if config.get("schema_version") == 2:
        if config.get("gate_feature_dim") != size * 4 or not 0 < float(config["gate_threshold"]) < 1:
            raise ValueError("invalid_video_gate_configuration")
        if any(weights[name].shape != (size * 4,) for name in ("gate_mean", "gate_scale", "gate_coef")) or (weights["gate_scale"] <= 0).any():
            raise ValueError("invalid_video_gate_shape")
    return config, weights


def readiness() -> dict:
    reasons = []
    config = {}
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
        config, _ = _load_artifacts(model_dir())
    except ImportError:
        reasons.append("Local OpenCV/NumPy dependencies are missing.")
    except FileNotFoundError:
        reasons.append("Private trained model artifacts are missing; run prepare_model.py and train_baseline.py.")
    except (ValueError, KeyError, OSError, json.JSONDecodeError):
        reasons.append("Local model artifacts failed validation; prepare them again.")
    return {
        "ready": not reasons,
        "competition_ready": False,
        "reasons": reasons,
        "model_version": config.get("model_version", "unprepared"),
        "model_kind": "experimental_visual_review_baseline",
        "limitations": _model_warnings(config),
    }


class FeatureExtractor:
    """Frozen MobileNetV2 ImageNet logit representation plus spatial motion/appearance.

    Use the explicit graph output across OpenCV versions. Some graph engines silently
    return that output when an intermediate average-pool layer is requested.
    """

    def __init__(self, directory: Path, feature_layer: str | None = None):
        import cv2
        import numpy as np

        self.cv2, self.np = cv2, np
        cv2.setNumThreads(max(1, min(4, int(os.environ.get("CASH_REVIEW_CV_THREADS", "2")))))
        self.net = cv2.dnn.readNetFromONNX(str(directory / MODEL_FILE))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        names = self.net.getLayerNames()
        self.feature_layer = feature_layer or names[-1]

    def feature(self, frame, previous_gray=None):
        cv2, np = self.cv2, self.np
        _validate_dimensions(frame.shape[1], frame.shape[0])
        small = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        rgb = (rgb - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
        self.net.setInput(np.transpose(rgb, (2, 0, 1))[None].copy())
        embedding = self.net.forward(self.feature_layer).reshape(-1).astype(np.float32)
        if embedding.size != 1000 or not np.isfinite(embedding).all():
            raise ValueError("unexpected_backbone_output")
        # Relative normalization stabilizes the frozen representation across brightness.
        embedding /= max(float(np.linalg.norm(embedding)), 1e-6)
        gray = cv2.cvtColor(cv2.resize(frame, (64, 64), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        difference = np.abs(gray - previous_gray) if previous_gray is not None else np.zeros_like(gray)
        cells = [(slice(y, y + 16), slice(x, x + 16)) for y in range(0, 64, 16) for x in range(0, 64, 16)]
        spatial = np.array([float(grid[cell].mean()) for grid in (gray, difference) for cell in cells], dtype=np.float32)
        return np.concatenate([embedding, spatial]), gray


def extract_video(path: Path, extractor: FeatureExtractor, deadline: float, progress=None, interval_sec: float = 1.0) -> dict:
    """Decode sequentially, retaining features only. Never stores or emits frame pixels."""
    cv2, np = extractor.cv2, extractor.np
    _deadline(deadline)
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise ValueError("unreadable_media")
        # Header limits precede the first explicit decode. Native container opening
        # still occurs inside VideoCapture and is bounded by worker process isolation.
        _validate_dimensions(capture.get(cv2.CAP_PROP_FRAME_WIDTH), capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if not math.isfinite(fps) or fps <= 0 or not math.isfinite(count) or count <= 0:
            raise ValueError("invalid_media_timing")
        duration = count / fps
        if duration > float(os.environ.get("CASH_REVIEW_MAX_MODEL_DURATION", "600")):
            raise ValueError("model_duration_limit_exceeded")
        times, features = [], []
        previous_gray = None
        next_target, index, last_pts = 0.0, 0, -1.0
        fallback = False
        while capture.grab():
            _deadline(deadline)
            okay, frame = capture.retrieve()
            if not okay or frame is None:
                raise ValueError("media_decode_failed")
            _validate_dimensions(frame.shape[1], frame.shape[0])
            pts = float(capture.get(cv2.CAP_PROP_POS_MSEC)) / 1000.0
            if not math.isfinite(pts) or pts < 0 or (index > 0 and pts <= last_pts):
                pts, fallback = index / fps, True
            last_pts = pts
            if pts + 0.5 / fps >= next_target:
                value, previous_gray = extractor.feature(frame, previous_gray)
                times.append(pts)
                features.append(value)
                next_target += interval_sec
                if progress:
                    progress(min(80, 10 + int(70 * pts / max(duration, 0.1))), "Extracting local visual features")
            index += 1
        if not features or index < max(1, int(count * 0.95)):
            raise ValueError("incomplete_media_decode")
        return {"times": np.asarray(times, dtype=np.float32), "features": np.stack(features),
                "duration_sec": round(max(duration, last_pts), 4), "fps": fps,
                "timing_fallback": fallback, "decoded_frames": index}
    finally:
        capture.release()


def score_features(features, weights):
    import numpy as np

    logits = ((features - weights["mean"]) / weights["scale"]) @ weights["coef"] + weights["intercept"].reshape(-1)[0]
    return 1.0 / (1.0 + np.exp(-np.clip(logits, -40, 40)))


def pool_video_features(features):
    """Fixed permutation-invariant bag representation; no duration/identity inputs."""
    import numpy as np

    return np.concatenate([features.mean(axis=0), features.std(axis=0), features.max(axis=0), np.quantile(features, 0.9, axis=0)]).astype(np.float32)


def score_video_gate(features, weights) -> float:
    gate = {name: weights["gate_" + name] for name in ("mean", "scale", "coef", "intercept")}
    return float(score_features(pool_video_features(features)[None], gate)[0])


def _read_at(capture, target: float, fps: float):
    import cv2

    capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, target) * 1000.0)
    okay, frame = capture.read()
    if not okay or frame is None:
        raise ValueError("evidence_decode_failed")
    _validate_dimensions(frame.shape[1], frame.shape[0])
    pts = float(capture.get(cv2.CAP_PROP_POS_MSEC)) / 1000.0
    if not math.isfinite(pts) or pts < 0 or (target > 0.5 and pts == 0):
        pts = max(0, float(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1) / fps
    return frame, pts


def analyze_video(path: Path, deadline: float, progress: Callable[[int, str], None]) -> dict:
    import cv2
    import numpy as np

    started = time.monotonic()
    _deadline(deadline)
    config, weights = _load_artifacts(model_dir())
    extractor = FeatureExtractor(model_dir(), config["feature_layer"])
    progress(8, "Loading local visual baseline")
    extracted = extract_video(path, extractor, deadline, progress)
    scores = score_features(extracted["features"], weights)
    threshold = float(config["threshold"])
    gate_score = score_video_gate(extracted["features"], weights) if config.get("schema_version") == 2 else None
    gate_passed = gate_score is None or gate_score >= float(config["gate_threshold"])
    # Bound dense refinement and suppress adjacent peaks before selecting candidates.
    candidates = []
    for index in np.argsort(-scores, kind="stable"):
        if not gate_passed or float(scores[index]) < threshold:
            break
        timestamp = float(extracted["times"][index])
        if all(abs(timestamp - old[0]) >= 8.0 for old in candidates):
            candidates.append((timestamp, float(scores[index])))
        if len(candidates) == 3:
            break
    events = []
    capture = cv2.VideoCapture(str(path))
    try:
        for event_index, (timestamp, coarse_score) in enumerate(candidates):
            _deadline(deadline)
            best_time, best_score = timestamp, coarse_score
            for target in np.arange(max(0.0, timestamp - 1), min(extracted["duration_sec"] - 0.1, timestamp + 1) + 0.01, 0.25):
                _deadline(deadline)
                previous, _ = _read_at(capture, max(0, float(target) - 1), extracted["fps"])
                previous_gray = cv2.cvtColor(cv2.resize(previous, (64, 64), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
                frame, actual_time = _read_at(capture, float(target), extracted["fps"])
                feature, _ = extractor.feature(frame, previous_gray)
                value = float(score_features(feature[None], weights)[0])
                if value > best_score:
                    best_time, best_score = actual_time, value
            evidence = []
            for target in (max(0, best_time - 0.5), best_time, min(extracted["duration_sec"] - 0.1, best_time + 0.5)):
                _deadline(deadline)
                frame, actual_time = _read_at(capture, target, extracted["fps"])
                scale = min(1.0, 640 / max(frame.shape[:2]))
                if scale < 1:
                    frame = cv2.resize(frame, (max(1, round(frame.shape[1] * scale)), max(1, round(frame.shape[0] * scale))), interpolation=cv2.INTER_AREA)
                okay, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
                if not okay:
                    raise ValueError("evidence_encode_failed")
                evidence.append({"timestamp_sec": round(actual_time, 3), "image_base64": base64.b64encode(jpeg.tobytes()).decode("ascii")})
            events.append({"type": "visual_review_signal", "timecode_sec": round(best_time, 3),
                           "description": "Модель выделила визуальный фрагмент для проверки человеком. Конкретное действие и нарушение нормы не установлены.",
                           "rule_id": "CR-001", "confidence": round(best_score, 4), "evidence_frames": evidence})
            progress(84 + event_index * 4, "Preparing private JPEG evidence")
    finally:
        capture.release()
    _deadline(deadline)
    events.sort(key=lambda event: event["timecode_sec"])
    warnings = _model_warnings(config)
    if extracted["timing_fallback"]:
        warnings.append("Media presentation timestamps were unavailable; frame index / nominal frame rate was used.")
    if not events:
        warnings.append("No signal passed the baseline threshold; this does not certify regulatory compliance.")
    progress(98, "Local analysis complete")
    return {"verdict": "violation" if events else "no_violation", "violations": events,
            "metadata": {"duration_sec": extracted["duration_sec"], "model_version": config["model_version"],
                         "competition_ready": False, "model_kind": "experimental_visual_review_baseline",
                         "warnings": warnings, "sample_interval_sec": 1, "sampled_frames": len(scores),
                         "processing_sec": round(time.monotonic() - started, 3), "threshold": threshold,
                         "max_signal_score": round(float(scores.max()), 4), "score_calibrated": False,
                         "video_gate_score": round(gate_score, 4) if gate_score is not None else None,
                         "video_gate_threshold": config.get("gate_threshold"), "video_gate_passed": gate_passed}}
