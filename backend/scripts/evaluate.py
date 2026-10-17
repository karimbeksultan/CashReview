"""Evaluate the frozen test partition once. Public output contains aggregate metrics only."""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cash_review.engine import _load_artifacts, analyze_video, score_features, score_video_gate


def wilson(successes, total):
    if not total:
        return None
    z, p = 1.96, successes / total
    center = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return [round(max(0, center - half), 4), round(min(1, center + half), 4)]


def run(args):
    import cv2
    from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, accuracy_score

    directory = args.model_dir.resolve()
    destination = directory / "evaluation_aggregate.json"
    if destination.exists() and not args.repeat:
        print(destination.read_text(encoding="utf-8"))
        return
    config, weights = _load_artifacts(directory)
    split = json.loads((directory / "split.json").read_text(encoding="utf-8"))
    test = [g for g in split["source"] if split["assignments"][g["sha256"]] == "test"]
    assert all(split["assignments"][g["sha256"]] != "train" for g in test)
    records, failed = [], []
    for group in test:
        try:
            with np.load(directory / "features" / (group["sha256"] + ".npz"), allow_pickle=False) as data:
                scores = score_features(data["features"], weights)
                gate_score = score_video_gate(data["features"], weights) if config.get("schema_version") == 2 else None
                gate_passed = gate_score is None or gate_score >= config["gate_threshold"]
                candidates = []
                for index in np.argsort(-scores, kind="stable"):
                    if not gate_passed or scores[index] < config["threshold"]:
                        break
                    t = float(data["times"][index])
                    if all(abs(t - old) >= 8 for old in candidates):
                        candidates.append(t)
                    if len(candidates) == 3:
                        break
                offsets = [min((abs(t - gt) for t in candidates), default=None) for gt in group["timestamps"]]
                records.append({"sha256": group["sha256"], "truth": int(group["positive"]), "prediction": int(bool(candidates)),
                                "score": float(scores.max()), "gate_score": gate_score, "candidate_times": candidates,
                                "annotation_nearest_signal_errors_sec": offsets,
                                "feature_sec": float(data["feature_sec"]), "duration_sec": float(data["duration_sec"])})
        except (ValueError, OSError, KeyError) as error:
            failed.append({"sha256": group["sha256"], "error_type": type(error).__name__})
    truth = [r["truth"] for r in records]
    predictions = [r["prediction"] for r in records]
    matrix = confusion_matrix(truth, predictions, labels=[0, 1]).tolist() if records else [[0, 0], [0, 0]]
    tn, fp, fn, tp = matrix[0][0], matrix[0][1], matrix[1][0], matrix[1][1]
    positive_records = [r for r in records if r["truth"]]
    # Isolated timestamps are not exhaustive event truth. No event precision is claimed.
    timestamp_hits = sum(any(value is not None and value <= 5 for value in r["annotation_nearest_signal_errors_sec"]) for r in positive_records)
    report = {"model_version": config["model_version"],
              "evaluation_kind": "exploratory_previously_seen_test" if config.get("schema_version") == 2 else "frozen_exact-content-group_holdout",
              "test_exposure_note": "This partition was exposed by v1. These v2 results are exploratory, not an unbiased unseen holdout." if config.get("schema_version") == 2 else "First model evaluation on frozen test partition",
              "seed": split["seed"], "split_sizes": {part: sum(value == part for value in split["assignments"].values()) for part in ("train", "validation", "test")},
              "test_submitted": len(test), "test_completed": len(records), "test_failed": len(failed),
              "test_class_counts": {"positive": sum(g["positive"] for g in test), "negative": sum(not g["positive"] for g in test)},
              "completion_rate": len(records) / len(test), "confusion_matrix_labels": ["negative", "positive"],
              "confusion_matrix_true_rows_predicted_columns": matrix,
              "video_precision": float(precision_score(truth, predictions, zero_division=0)) if records else None,
              "video_recall": float(recall_score(truth, predictions, zero_division=0)) if records else None,
              "video_f1": float(f1_score(truth, predictions, zero_division=0)) if records else None,
              "video_accuracy_completed": float(accuracy_score(truth, predictions)) if records else None,
              "video_accuracy_all_submitted": (tn + tp) / len(test),
              "accuracy_wilson_95": wilson(tn + tp, len(records)), "recall_wilson_95": wilson(tp, tp + fn),
              "specificity_wilson_95": wilson(tn, tn + fp),
              "positive_videos_with_signal_within_5sec_of_any_supplied_timestamp": timestamp_hits,
              "positive_video_timestamp_coverage": timestamp_hits / len(positive_records) if positive_records else None,
              "timestamp_tolerance_sec": 5, "timestamp_tolerance_basis": "Team baseline diagnostic choice, not a brief requirement",
              "event_precision_recall": "not measured: complete event intervals/type annotations unavailable",
              "threshold": config["threshold"], "threshold_selected_on": "validation only",
              "video_gate_threshold": config.get("gate_threshold"),
              "video_gate_validation_balanced_accuracy": config.get("validation_balanced_accuracy"),
              "feature_extraction_sec_test_median": float(np.median([r["feature_sec"] for r in records])) if records else None,
              "hardware": {"platform": platform.platform(), "processor": platform.processor(), "logical_cpus": os.cpu_count(),
                           "opencv": cv2.__version__, "numpy": np.__version__, "cv_threads": 2},
              "quality_validated": False,
              "limitations": ["Only eight unique content groups in the holdout; wide statistical uncertainty.",
                              "Same source camera/setting may correlate across splits; near duplicates/session grouping not reviewed.",
                              "Frozen feature extraction on test pixels is inference; scaler/classifier fitting and threshold selection exclude test groups.",
                              "Positive labels supply isolated timestamps. Duplicate positive annotations retain both 57/68-second possibilities.",
                              "No event taxonomy, semantic action validation, legal correctness or alternate-camera generalization established.",
                              "Feature timing excludes upload/queue/polling and is not end-to-end service latency."]}
    if args.runtime_smoke:
        os.environ["CASH_REVIEW_MODEL_DIR"] = str(directory)
        smoke = []
        def duration(group):
            with np.load(directory / "features" / (group["sha256"] + ".npz"), allow_pickle=False) as values:
                return float(values["duration_sec"])
        benchmarks = [("heldout_negative", next(g for g in test if not g["positive"])),
                      ("heldout_positive", next(g for g in test if g["positive"])),
                      ("longest_source_clip", max(split["source"], key=duration))]
        for case, group in benchmarks:
            started = time.monotonic()
            try:
                result = analyze_video(Path(group["path"]), started + 240, lambda *_: None)
                decoded = 0
                import base64
                for event in result["violations"]:
                    for frame in event["evidence_frames"]:
                        image = cv2.imdecode(np.frombuffer(base64.b64decode(frame["image_base64"], validate=True), np.uint8), cv2.IMREAD_COLOR)
                        if image is None:
                            raise ValueError("Real evidence JPEG failed decoding")
                        if max(image.shape[:2]) > 640:
                            raise ValueError("Evidence exceeds the 640px bound")
                        if not 0 <= frame["timestamp_sec"] <= result["metadata"]["duration_sec"] + 0.1:
                            raise ValueError("Evidence timestamp outside source duration")
                        decoded += 1
                smoke.append({"case": case, "source_class": "positive" if group["positive"] else "negative", "completed": True,
                              "verdict": result["verdict"], "runtime_sec": round(time.monotonic() - started, 3),
                              "duration_sec": result["metadata"]["duration_sec"],
                              "event_count": len(result["violations"]), "validated_jpegs": decoded})
            except Exception as error:
                smoke.append({"case": case, "source_class": "positive" if group["positive"] else "negative", "completed": False, "error_type": type(error).__name__})
        report["runtime_engine_smoke"] = smoke
    (directory / "evaluation_private.json").write_text(json.dumps({"records": records, "failures": failed}, indent=2), encoding="utf-8")
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--runtime-smoke", action="store_true", help="Run real decoding/inference and validate returned JPEGs on one held-out clip per class")
    parser.add_argument("--repeat", action="store_true", help="Repeat fixed evaluation without tuning the model or split")
    run(parser.parse_args())
