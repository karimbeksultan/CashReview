"""Strict offline I/O and reproducible feature caches, independent of research code."""
from __future__ import annotations

import ast
from datetime import datetime, time as clock_time, timedelta
import hashlib
import inspect
import io
import json
import math
from numbers import Real
import os
from pathlib import Path
import re
import tempfile
import textwrap
import zipfile

import numpy as np

CORE_ARRAYS = ("times", "features", "duration_sec", "feature_sec")
CACHE_FIELDS = set(CORE_ARRAYS) | {"cache_schema", "source_sha256", "feature_spec_json", "payload_sha256"}


def require_fresh_training_directory(directory):
    """Prepared backbone/split/cache may exist; completed model/results may not."""
    directory = Path(directory)
    protected = [directory / "baseline.json", directory / "baseline.npz"]
    protected.extend(directory.glob("validation*.json"))
    protected.extend(directory.glob("evaluation*.json"))
    if any(path.exists() for path in protected):
        raise ValueError("Training requires a fresh private artifact directory; preserve existing models, reports and caches")


def parse_source_timestamp(value):
    """Accept complete relative times only; never infer units by counting digits.

    Formats: finite nonnegative numeric seconds, seconds strings, MM:SS or
    HH:MM:SS (optional fractional seconds), explicit Russian minute/second
    units, datetime.time, and timedelta. Calendar datetimes and booleans fail.
    """
    if value is None:
        return None
    if isinstance(value, (bool, datetime)):
        raise ValueError("Unsupported relative timestamp type")
    if isinstance(value, clock_time):
        if value.tzinfo is not None:
            raise ValueError("Zoned clock time is not a relative timestamp")
        result = value.hour * 3600 + value.minute * 60 + value.second + value.microsecond / 1_000_000
    elif isinstance(value, timedelta):
        result = value.total_seconds()
    elif isinstance(value, Real):
        result = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        number = r"[0-9]+(?:[.,][0-9]+)?"
        minute = r"мин(?:ут(?:а|ы)?)?\.?"
        second = r"сек(?:унд(?:а|ы)?)?\.?"
        if re.fullmatch(number, text):
            result = float(text.replace(",", "."))
        elif match := re.fullmatch(r"([0-9]+):([0-9]{2}(?:[.,][0-9]+)?)", text):
            seconds = float(match[2].replace(",", "."))
            if seconds >= 60:
                raise ValueError("Seconds field must be below sixty")
            result = int(match[1]) * 60 + seconds
        elif match := re.fullmatch(r"([0-9]+):([0-9]{2}):([0-9]{2}(?:[.,][0-9]+)?)", text):
            seconds = float(match[3].replace(",", "."))
            if int(match[2]) >= 60 or seconds >= 60:
                raise ValueError("Clock fields must be below sixty")
            result = int(match[1]) * 3600 + int(match[2]) * 60 + seconds
        elif match := re.fullmatch(rf"(?:([0-9]+)\s*{minute}\s*)?({number})\s*{second}", text, re.IGNORECASE):
            seconds = float(match[2].replace(",", "."))
            if match[1] is not None and seconds >= 60:
                raise ValueError("Seconds field must be below sixty")
            result = (int(match[1]) * 60 if match[1] is not None else 0) + seconds
        elif match := re.fullmatch(rf"({number})\s*{minute}", text, re.IGNORECASE):
            result = float(match[1].replace(",", ".")) * 60
        else:
            raise ValueError("Timestamp does not match a complete supported format")
    else:
        raise ValueError("Unsupported relative timestamp type")
    if not math.isfinite(result) or result < 0:
        raise ValueError("Timestamp must be finite and nonnegative")
    return float(result)


def function_fingerprint(function):
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    return hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()


def build_feature_spec(backbone_sha256, feature_layer, feature_dim, interval_sec,
                       feature_function, sampler_function, initializer_function, opencv_version):
    if not math.isfinite(interval_sec) or interval_sec <= 0:
        raise ValueError("Sampling interval must be finite and positive")
    return {"cache_version": 1, "backbone_sha256": backbone_sha256, "feature_layer": feature_layer,
        "feature_dim": feature_dim, "sample_interval_sec": interval_sec, "numpy_version": np.__version__,
        "opencv_version": opencv_version, "preprocessing_sha256": function_fingerprint(feature_function),
        "sampler_sha256": function_fingerprint(sampler_function),
        "extractor_init_sha256": function_fingerprint(initializer_function)}


def _payload_digest(values):
    result = hashlib.sha256()
    for name in CORE_ARRAYS:
        value = np.ascontiguousarray(values[name])
        result.update(json.dumps([name, value.dtype.str, value.shape]).encode())
        result.update(value.tobytes())
    return result.hexdigest()


def _validate_core(values, spec):
    times, features = values["times"], values["features"]
    if (times.dtype != np.float32 or times.ndim != 1 or not 1 <= len(times) <= 10_000 or
        features.dtype != np.float32 or features.shape != (len(times), spec["feature_dim"])):
        raise ValueError("Invalid cached feature shapes or dtypes")
    if not np.isfinite(times).all() or np.any(times < 0) or np.any(np.diff(times) <= 0) or not np.isfinite(features).all():
        raise ValueError("Invalid cached feature values or timing")
    for name in ("duration_sec", "feature_sec"):
        value = values[name]
        if value.shape != () or value.dtype.kind != "f" or not np.isfinite(value) or float(value) < 0:
            raise ValueError("Invalid cached scalar")
    if float(values["duration_sec"]) <= 0 or float(times[-1]) > float(values["duration_sec"]) + .25:
        raise ValueError("Cached timestamps exceed source duration")


def _read_bounded_arrays(path):
    """Validate NPY headers before allocation, not just compressed ZIP size."""
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Feature cache exceeds bound")
    arrays = {}
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) != len(CACHE_FIELDS) or {entry.filename for entry in entries} != {name + ".npy" for name in CACHE_FIELDS}:
            raise ValueError("Unversioned or incomplete feature cache")
        if sum(entry.file_size for entry in entries) > 16 * 1024 * 1024:
            raise ValueError("Feature cache decompression exceeds bound")
        for entry in entries:
            with archive.open(entry) as stream:
                version = np.lib.format.read_magic(stream)
                if version == (1, 0):
                    shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
                elif version == (2, 0):
                    shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
                else:
                    raise ValueError("Unsupported cache array format")
                size = math.prod(shape) * dtype.itemsize
                if dtype.hasobject or size > 16 * 1024 * 1024 or stream.tell() + size != entry.file_size:
                    raise ValueError("Invalid bounded cache array")
            arrays[entry.filename[:-4]] = np.load(io.BytesIO(archive.read(entry)), allow_pickle=False)
    return arrays


def read_feature_cache(path, source_sha256, spec):
    values = _read_bounded_arrays(Path(path))
    for name in ("cache_schema", "source_sha256", "feature_spec_json", "payload_sha256"):
        if values[name].shape != ():
            raise ValueError("Invalid cache metadata shape")
    if values["cache_schema"].dtype.kind not in "iu" or int(values["cache_schema"]) != 1:
        raise ValueError("Unsupported cache schema")
    if any(values[name].dtype.kind != "U" for name in ("source_sha256", "feature_spec_json", "payload_sha256")):
        raise ValueError("Invalid cache metadata dtype")
    if str(values["source_sha256"]) != source_sha256 or json.loads(str(values["feature_spec_json"])) != spec:
        raise ValueError("Feature cache source or preprocessing binding changed")
    core = {name: values[name] for name in CORE_ARRAYS}
    _validate_core(core, spec)
    if _payload_digest(core) != str(values["payload_sha256"]):
        raise ValueError("Feature cache payload integrity mismatch")
    return core


def write_feature_cache(path, values, source_sha256, spec):
    path = Path(path)
    core = {name: np.asarray(values[name]) for name in CORE_ARRAYS}
    _validate_core(core, spec)
    stored = {**core, "cache_schema": np.array(1, dtype=np.int64), "source_sha256": np.array(source_sha256),
        "feature_spec_json": np.array(json.dumps(spec, sort_keys=True)), "payload_sha256": np.array(_payload_digest(core))}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".feature-", suffix=".npz", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            np.savez_compressed(stream, **stored)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def configured_evidence_side():
    return min(1920, max(640, int(os.environ.get("CASH_REVIEW_EVIDENCE_MAX_SIDE", "1280"))))


def validate_evidence_size(shape, source_size, maximum_side):
    source_width, source_height = source_size
    if min(source_width, source_height) <= 0 or max(source_width, source_height) > 4096 or source_width * source_height > 8_000_000:
        raise ValueError("Invalid source dimensions")
    scale = min(1., maximum_side / max(source_width, source_height))
    expected = (max(1, round(source_height * scale)), max(1, round(source_width * scale)))
    if tuple(shape[:2]) != expected:
        raise ValueError("Evidence does not preserve bounded native source dimensions")


def source_dimensions(path):
    """Observe decoded dimensions so container rotation cannot swap the bounds."""
    import cv2
    capture = cv2.VideoCapture(str(path))
    try:
        width, height = capture.get(cv2.CAP_PROP_FRAME_WIDTH), capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        if not capture.isOpened() or not all(math.isfinite(v) and v > 0 for v in (width, height)) or max(width, height) > 4096 or width * height > 8_000_000:
            raise ValueError("Invalid source dimensions")
        okay, frame = capture.read()
        if not okay or frame is None or frame.ndim != 3 or max(frame.shape[:2]) > 4096 or frame.shape[0] * frame.shape[1] > 8_000_000:
            raise ValueError("Cannot validate native source dimensions")
        return frame.shape[1], frame.shape[0]
    finally:
        capture.release()
