"""Lightweight, media-free contracts for the experimental research workflow."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import uuid

import numpy as np
from openpyxl import Workbook

import data
import workflow


def run(original=None):
    results = {}
    # A standard library source audit does not import Torch or any model.
    if original is not None:
        before = {node.name: node for node in ast.parse(Path(original).read_text(encoding="utf-8")).body
                  if isinstance(node, ast.FunctionDef)}
        after = {node.name: node for node in ast.parse(Path(workflow.__file__).read_text(encoding="utf-8")).body
                 if isinstance(node, ast.FunctionDef)}
        names = ["fitting_indices", "video_score", "anchor_indices", "metrics",
                 "select_threshold", "torch_setup", "make_suffix", "synthetic_benchmark"]
        for name in names:
            assert ast.dump(before[name]) == ast.dump(after[name]), name
        class NormalizeLoad(ast.NodeTransformer):
            def visit_Call(self, node):
                self.generic_visit(node)
                if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "np" and node.func.attr == "load"):
                    node.func = ast.Name(id="load_hidden", ctx=ast.Load())
                    node.keywords = []
                return node
        assert ast.dump(NormalizeLoad().visit(before["fit"])) == ast.dump(after["fit"])
        results["unchanged_numerical_functions"] = len(names) + 1
        results["original_source_sha256"] = data.digest(original)
    assert np.array_equal(workflow.fitting_indices([0, 1, 2, 3, 4, 5, 6], True, [5]), [3, 4, 5, 6])
    assert len(workflow.fitting_indices(range(100), False, [])) == 12
    assert workflow.video_score(np.asarray([.1, .3, .9, .4], dtype=np.float32)) == float(np.mean(np.sort(np.asarray([.1, .3, .9, .4], dtype=np.float32).astype(float))[-3:]))
    selected = workflow.select_threshold([0, 0, 1, 1], [.1, .2, .8, .9])
    assert selected[1] == {"tp": 2, "tn": 2, "fp": 0, "fn": 0, "recall": 1., "specificity": 1., "balanced_accuracy": 1.}
    assert workflow.select_threshold([0, 0, 1, 1], [.5] * 4) is None
    results["sparse_positive_and_scoring_checks"] = 5
    valid_timestamps = [(57.0, 57.), (5.5, 5.5), ("5.5", 5.5), ("57.0", 57.),
                        ("01:05.5", 65.5), ("00:00", 0.), (0, 0.), (None, None), (" ", None)]
    for value, expected in valid_timestamps:
        assert data.parse_timestamp(value) == expected
    invalid_timestamps = [True, False, -1, -5.5, float("nan"), float("inf"),
                          "-5", "-00:03", "+5", "x5.5", "5 seconds", "1:60", "1:2",
                          "1:03:04", "1:02x", "NaN", "Infinity", "1..2", object()]
    for value in invalid_timestamps:
        try:
            data.parse_timestamp(value)
        except ValueError:
            pass
        else:
            raise AssertionError("Malformed timestamp was accepted")
    results["strict_timestamp_checks"] = len(valid_timestamps) + len(invalid_timestamps)
    valid_units = [("57 секунд", 57.), ("1минут 5 секунд", 65.), ("1 секунда", 1.),
                   ("2 секунды", 2.), ("2минуты3секунды", 123.), ("1 минута 00.5 секунды", 60.5),
                   ("5.5 секунды", 5.5), ("5,5 секунды", 5.5), (" 57 СЕКУНД ", 57.)]
    for value, expected in valid_units:
        assert data.parse_source_timestamp(value) == expected
    invalid_units = ["-5 секунд", "-1 минут 5 секунд", "1 минута -5 секунд", "1 минута 60 секунд",
                     "5 секунд text", "start5секунд", "5секунд!", "NaN секунд", "inf секунд",
                     "1.5 минуты 5 секунд", "5. секунд", "5, секунд", "5 секундами"]
    for value in invalid_units:
        try:
            data.parse_source_timestamp(value)
        except ValueError:
            pass
        else:
            raise AssertionError("Malformed source-unit timestamp was accepted")
    results["source_unit_timestamp_checks"] = len(valid_units) + len(invalid_units)
    root = Path(__file__).resolve().parent / ("contract-" + uuid.uuid4().hex)
    root.mkdir()
    try:
        source = root / "dataset"
        videos = source / "videos"
        videos.mkdir(parents=True)
        book = Workbook()
        sheet = book.active
        sheet.title = "labels"
        sheet.append(["name", "timestamp", "label"])
        for label in (False, True):
            for number in range(8):
                name = f"Х-{int(label)}-{number}"
                (videos / f"{name}.mov").write_bytes(f"synthetic-not-video:{label}:{number}".encode())
                sheet.append([name, "0:03" if label else None, "нарушение" if label else "без нарушения"])
        # Identical bytes belong to one group even with a second Unicode name.
        (videos / "Х-дубликат.mov").write_bytes((videos / "Х-1-0.mov").read_bytes())
        sheet.append(["Х-дубликат", "0:04", "нарушение"])
        book.save(source / "open_labels.xlsx")
        split = root / "split.json"
        counts = data.freeze_split(source, split)
        assert counts["groups"] == 16 and counts["counts"] == {"train": 8, "validation": 4, "test": 4}
        assert len(data.resolve_groups(split, source, "train")) == 8
        assert len(data.resolve_groups(split, source, "validation")) == 4
        try:
            data.resolve_groups(split, source, "test")
        except ValueError:
            pass
        else:
            raise AssertionError("Test mode was accepted")
        try:
            data.freeze_split(source, split)
        except ValueError:
            pass
        else:
            raise AssertionError("Frozen split overwrite was accepted")
        original = json.loads(split.read_text())
        edited = json.loads(split.read_text())
        train_group = next(row for row in edited["source"] if edited["assignments"][row["sha256"]] == "train")
        train_group["relative_path"] = "../outside.mov"
        (root / "outside.mov").write_bytes(b"synthetic")
        split.write_text(json.dumps(edited))
        try:
            data.resolve_groups(split, source, "train")
        except ValueError:
            pass
        else:
            raise AssertionError("Path traversal accepted")
        split.write_text(json.dumps(original))
        array = root / "array.npy"
        np.save(array, np.zeros((196, 768), np.float32), allow_pickle=False)
        assert workflow.load_hidden(array).shape == (196, 768)
        for value in [np.zeros((196, 768), np.float64), np.full((196, 768), np.nan, np.float32), np.array([object()])]:
            np.save(array, value)
            try:
                workflow.load_hidden(array)
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid hidden-state array accepted")
        np.save(array, np.zeros((196, 768), np.float32), allow_pickle=False)
        workflow._CACHE_DIGESTS[str(array.absolute())] = data.digest(array)
        assert workflow.load_hidden(array).shape == (196, 768)
        np.save(array, np.ones((196, 768), np.float32), allow_pickle=False)
        try:
            workflow.load_hidden(array)
        except ValueError:
            pass
        else:
            raise AssertionError("Finite altered cache array was accepted")
        workflow._CACHE_DIGESTS.clear()
        fingerprint = workflow.runtime_fingerprint()
        assert fingerprint["python"] and fingerprint["distributions"]["numpy"]
    finally:
        # The generated absolute target is verified before recursive cleanup.
        target = root.resolve()
        if target.parent != Path(__file__).resolve().parent or not target.name.startswith("contract-"):
            raise ValueError("Unexpected synthetic fixture cleanup target")
        shutil.rmtree(target)
    results.update(synthetic_manifest_checks=6, safe_numeric_cache_checks=6,
        metadata_only_runtime_fingerprint_checks=1,
        passed=True, model_loads=0, media_decodes=0, case_inputs_processed=0)
    assert "torch" not in __import__("sys").modules
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.original)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
