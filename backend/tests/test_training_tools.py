"""Offline reproducibility contracts use synthetic values, never source footage/models."""
from datetime import datetime, time as clock_time, timedelta
import hashlib
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from scripts import evaluate, train_baseline
from scripts.training_utils import (parse_source_timestamp, read_feature_cache, write_feature_cache,
                                    configured_evidence_side, source_dimensions, validate_evidence_size)
from scripts.training_utils import require_fresh_training_directory


def test_supported_relative_timestamps_preserve_units_fractions_and_zero():
    cases = [(0, 0.), (57.5, 57.5), ("57,5", 57.5), ("1 мин", 60.),
             ("1 минута 8 секунд", 68.), ("1:08.5", 68.5), ("00:01:08", 68.),
             (clock_time(0, 0, 57, 500000), 57.5), (timedelta(seconds=3.25), 3.25),
             ("57,5 секунды", 57.5), ("0 секунд", 0.)]
    for raw, expected in cases:
        assert parse_source_timestamp(raw) == expected
    assert parse_source_timestamp(None) is None
    assert parse_source_timestamp("  ") is None


def test_ambiguous_partial_calendar_and_nonfinite_timestamps_fail_closed():
    for raw in [True, False, float("nan"), float("inf"), -1, "-1", "57 seconds trailing",
                "1:60", "01:60:00", "12 30", "2:3", "1 минута 60 секунд", datetime(2026, 1, 1)]:
        with pytest.raises(ValueError):
            parse_source_timestamp(raw)


def test_source_reader_preserves_positive_zero_and_binary_class_direction(tmp_path, monkeypatch):
    import openpyxl
    videos = tmp_path / "videos"
    videos.mkdir()
    (videos / "synthetic-positive.mov").write_bytes(b"synthetic-only-positive-no-media")
    (videos / "synthetic-normal.mov").write_bytes(b"synthetic-only-normal-no-media")
    rows = [("name", "time", "label"), ("synthetic-positive", 0, "нарушение"),
            ("synthetic-normal", None, "без нарушения")]
    class Book:
        def __getitem__(self, key):
            return SimpleNamespace(iter_rows=lambda **_: iter(rows))
        def close(self):
            pass
    monkeypatch.setattr(openpyxl, "load_workbook", lambda *_args, **_kwargs: Book())
    groups = train_baseline.read_source(tmp_path)
    assert sorted(int(group["positive"]) for group in groups) == [0, 1]
    assert next(group for group in groups if group["positive"])["timestamps"] == [0.]
    assert next(group for group in groups if not group["positive"])["timestamps"] == []


def payload(dim=3):
    return {"times": np.array([0., 1.], np.float32), "features": np.arange(2 * dim, dtype=np.float32).reshape(2, dim),
            "duration_sec": np.array(2.), "feature_sec": np.array(.01)}


def test_cache_binds_source_backbone_preprocessing_interval_and_payload(tmp_path):
    path = tmp_path / "synthetic.npz"
    spec = {"feature_dim": 3, "backbone_sha256": "backbone-v1", "preprocessing_sha256": "pixels-v1",
            "sample_interval_sec": 1., "opencv_version": "test-v1"}
    values = payload()
    write_feature_cache(path, values, "a" * 64, spec)
    restored = read_feature_cache(path, "a" * 64, spec)
    assert np.array_equal(restored["features"], values["features"])
    for patch in [{"backbone_sha256": "v2"}, {"preprocessing_sha256": "v2"},
                  {"sample_interval_sec": 2.}, {"opencv_version": "test-v2"}]:
        with pytest.raises(ValueError, match="binding"):
            read_feature_cache(path, "a" * 64, {**spec, **patch})
    with pytest.raises(ValueError, match="binding"):
        read_feature_cache(path, "b" * 64, spec)
    with np.load(path, allow_pickle=False) as archive:
        corrupted = {name: archive[name] for name in archive.files}
    corrupted["features"][0, 0] += 1
    np.savez_compressed(path, **corrupted)
    with pytest.raises(ValueError, match="integrity"):
        read_feature_cache(path, "a" * 64, spec)


def test_old_or_changed_feature_cache_rebuilds_once_and_checks_source_bytes(tmp_path, monkeypatch):
    source = tmp_path / "synthetic.mov"
    source.write_bytes(b"synthetic-only-no-media")
    group = {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    folder = tmp_path / "features"
    folder.mkdir()
    np.savez_compressed(folder / (group["sha256"] + ".npz"), **payload(1032))
    calls = []
    def extraction(_path, _extractor, _deadline, interval_sec=1.):
        calls.append(interval_sec)
        return {"times": np.array([0., interval_sec], np.float32),
                "features": np.zeros((2, 1032), np.float32), "duration_sec": 3.}
    monkeypatch.setattr(train_baseline, "extract_video", extraction)
    extractor = SimpleNamespace(feature_layer="synthetic-logits", cv2=SimpleNamespace(__version__="synthetic"))
    train_baseline.load_features(group, tmp_path, extractor)
    train_baseline.load_features(group, tmp_path, extractor)
    assert calls == [1.]
    train_baseline.load_features(group, tmp_path, extractor, interval_sec=2.)
    assert calls == [1., 2.]
    source.write_bytes(b"changed-synthetic-no-media")
    with pytest.raises(ValueError, match="Source content changed"):
        train_baseline.load_features(group, tmp_path, extractor, interval_sec=.5)
    assert calls == [1., 2.]


def test_evaluation_reads_legacy_report_but_rejects_unbound_repeat_or_smoke(tmp_path, monkeypatch, capsys):
    config = {"backbone_sha256": "a" * 64, "feature_layer": "synthetic", "feature_dim": 1032, "sample_interval_sec": 1.}
    monkeypatch.setattr(evaluate, "_load_artifacts", lambda _path: (config, {}))
    (tmp_path / "evaluation_aggregate.json").write_text('{"historical":true}', encoding="utf-8")
    args = SimpleNamespace(model_dir=tmp_path, repeat=False, runtime_smoke=False)
    evaluate.run(args)
    assert '"historical":true' in capsys.readouterr().out
    for repeat, smoke in [(True, False), (False, True)]:
        args.repeat, args.runtime_smoke = repeat, smoke
        with pytest.raises(ValueError, match="versioned feature specification"):
            evaluate.run(args)
    assert not (tmp_path / "split.json").exists()


def test_training_never_overwrites_completed_artifacts_or_opens_source(tmp_path, monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Source/model access must not occur")
    monkeypatch.setattr(train_baseline, "sha", forbidden)
    monkeypatch.setattr(train_baseline, "read_source", forbidden)
    monkeypatch.setattr(train_baseline, "FeatureExtractor", forbidden)
    for name in ["baseline.json", "baseline.npz", "validation_v2.json", "evaluation_aggregate.json", "evaluation_private.json"]:
        directory = tmp_path / name.replace(".", "-")
        directory.mkdir()
        protected = directory / name
        protected.write_bytes(b"historical-synthetic-record")
        args = SimpleNamespace(model_dir=directory, data_dir=tmp_path / "never-opened", model_kind="window")
        with pytest.raises(ValueError, match="fresh private artifact directory"):
            train_baseline.run(args)
        assert protected.read_bytes() == b"historical-synthetic-record"
    prepared = tmp_path / "prepared-only"
    prepared.mkdir()
    for name in ["split.json", "backbone_provenance.json", "mobilenetv2-7.onnx"]:
        (prepared / name).write_bytes(b"synthetic-preparation-only")
    require_fresh_training_directory(prepared)


def test_evidence_validation_accepts_native_detail_and_observes_decoded_rotation(monkeypatch):
    monkeypatch.delenv("CASH_REVIEW_EVIDENCE_MAX_SIDE", raising=False)
    assert configured_evidence_side() == 1280
    validate_evidence_size((848, 464, 3), (464, 848), 1280)
    validate_evidence_size((1280, 853, 3), (1600, 2400), 1280)
    for shape in [(1696, 928, 3), (848, 500, 3), (1281, 854, 3)]:
        with pytest.raises(ValueError, match="native source"):
            validate_evidence_size(shape, (464, 848), 1280)
    class Capture:
        released = False
        def isOpened(self):
            return True
        def get(self, field):
            return 848 if field == cv2.CAP_PROP_FRAME_WIDTH else 464
        def read(self):
            return True, SimpleNamespace(shape=(848, 464, 3), ndim=3)
        def release(self):
            self.released = True
    capture = Capture()
    monkeypatch.setattr(cv2, "VideoCapture", lambda _path: capture)
    assert source_dimensions(Path("synthetic-not-opened.mov")) == (464, 848)
    assert capture.released
