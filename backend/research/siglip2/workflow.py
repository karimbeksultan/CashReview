"""Experimental research workflow; the original fixed candidate was rejected.

Imports are deliberately lazy: audit runs without Torch, model loads or media
decoding. No test mode exists. No source pixels or per-case descriptions are
printed. All inference inputs are pixels/hidden states, never source metadata.
"""
from __future__ import annotations

import argparse
import gc
import functools
import hashlib
import json
import os
from pathlib import Path
import random
import threading
import time

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = MODEL = SPLIT = DATA_DIR = None
POLICY = SCRIPT_DIR / "policy.json"
_CACHE_DIGESTS = {}
SEED = 26017
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                  HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false",
                  OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(partial, path)


def policy_hash():
    # Cache identity binds numerical policy, implementation, frozen split and
    # exact official preprocessing/configuration, never a machine-specific path.
    contract = {"policy": digest(POLICY), "workflow": digest(Path(__file__)),
                "data_io": digest(SCRIPT_DIR / "data.py"), "split": digest(SPLIT),
                "asset_preparation": digest(SCRIPT_DIR / "prepare_assets.py"),
                "config": digest(MODEL / "config.json"),
                "processor": digest(MODEL / "preprocessor_config.json"),
                "runtime": runtime_fingerprint()}
    return hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()


@functools.lru_cache(maxsize=1)
def runtime_fingerprint():
    import importlib.metadata
    import platform
    versions = {}
    for name in ("torch", "transformers", "numpy", "Pillow", "safetensors", "scikit-learn",
                 "opencv-python-headless", "opencv-python", "openpyxl"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {"python": platform.python_version(), "os": platform.system(),
            "machine": platform.machine(), "distributions": versions}


def digest(path):
    from data import digest as file_digest
    return file_digest(path)


def groups(phase):
    from data import resolve_groups
    return resolve_groups(SPLIT, DATA_DIR, phase)


def configure(args):
    global ROOT, MODEL, SPLIT, DATA_DIR
    from data import local_path
    ROOT = args.run_dir.resolve()
    MODEL = local_path(args.model_dir)
    SPLIT = local_path(args.split)
    DATA_DIR = local_path(args.data_dir)
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "policy_hash": policy_hash(),
                "runtime": runtime_fingerprint(),
                "purpose": "experimental research reproducibility port; source candidate rejected",
                "source_decodes_at_initialization": 0}
    target = ROOT / "run_manifest.json"
    if target.exists():
        if read(target) != manifest:
            raise ValueError("Run contract changed; use a new run directory")
    else:
        with target.open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, indent=2)
    from prepare_assets import retain_license
    retain_license(ROOT)


def load_hidden(path):
    import numpy as np
    if Path(path).stat().st_size > 700_000:
        raise ValueError("Hidden-state cache exceeds fixed array size")
    expected = _CACHE_DIGESTS.get(str(Path(path).absolute()))
    if ROOT is not None and expected is None:
        raise ValueError("Hidden-state array lacks policy-bound integrity metadata")
    if expected is not None and digest(path) != expected:
        raise ValueError("Hidden-state array integrity mismatch")
    value = np.load(path, allow_pickle=False)
    if value.shape != (196, 768) or value.dtype != np.float32 or not np.isfinite(value).all():
        raise ValueError("Invalid numeric hidden-state cache")
    return value


def fitting_indices(timestamps, positive, annotations, maximum=12):
    """Sparse positive annotations are never converted into false negatives."""
    import numpy as np
    times = np.asarray(timestamps, dtype=float)
    if positive:
        if not annotations or not all(np.isfinite(float(a)) and float(a) >= 0 for a in annotations):
            raise ValueError("Positive fitting group lacks usable annotation")
        allowed = np.flatnonzero(np.min(np.abs(times[:, None] - np.asarray(annotations)[None, :]), axis=1) <= 2.0)
    else:
        allowed = np.arange(len(times))
    if not len(allowed):
        raise ValueError("No eligible fitting samples")
    return allowed[np.unique(np.linspace(0, len(allowed) - 1, min(maximum, len(allowed))).round().astype(int))]


def video_score(probabilities):
    import numpy as np
    p = np.asarray(probabilities, dtype=float)
    if not len(p) or not np.isfinite(p).all():
        raise ValueError("Invalid frame scores")
    return float(np.sort(p)[-min(3, len(p)):].mean())


def anchor_indices(probabilities, timestamps, threshold):
    """Fixed generic local peaks, not a semantic action classification."""
    import numpy as np
    p = np.asarray(probabilities, dtype=float)
    times = np.asarray(timestamps, dtype=float)
    if video_score(p) < threshold:
        return []
    maxima = [i for i in range(len(p)) if p[i] >= threshold and
              (i == 0 or p[i] >= p[i - 1]) and
              (i == len(p) - 1 or p[i] >= p[i + 1])]
    selected = []
    for index in sorted(maxima, key=lambda i: (-p[i], times[i])):
        if all(abs(times[index] - times[previous]) >= 8 for previous in selected):
            selected.append(index)
            if len(selected) == 3:
                break
    if not selected:
        raise ValueError("Positive video lacks a threshold-qualified frame maximum")
    return sorted(selected, key=lambda i: times[i])


def metrics(y, scores, threshold):
    import numpy as np
    y = np.asarray(y, dtype=bool)
    pred = np.asarray(scores) >= threshold
    tp, fn = int((pred & y).sum()), int((~pred & y).sum())
    tn, fp = int((~pred & ~y).sum()), int((pred & ~y).sum())
    recall, specificity = tp / max(tp + fn, 1), tn / max(tn + fp, 1)
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "recall": recall,
            "specificity": specificity, "balanced_accuracy": (recall + specificity) / 2}


def select_threshold(y, scores):
    import numpy as np
    values = np.unique(np.asarray(scores, dtype=float))
    options = [float(np.nextafter(values[0], -np.inf)), *map(float, values),
               float(np.nextafter(values[-1], np.inf))]
    eligible = [(threshold, metrics(y, scores, threshold)) for threshold in options]
    eligible = [item for item in eligible if item[1]["recall"] >= .5 and item[1]["specificity"] >= .5 and item[1]["balanced_accuracy"] > .5]
    return max(eligible, key=lambda item: (item[1]["balanced_accuracy"], item[1]["specificity"],
                                         item[1]["recall"], item[0])) if eligible else None


def torch_setup():
    import torch
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True)
    return torch


def require_weights():
    if digest(MODEL / "vision_tower" / "model.safetensors") != read(POLICY)["vision_sha256"]:
        raise ValueError("Vision tower integrity mismatch")
    for name, expected in {"config.json": "fe8b5fe6d5734360678fd71c11c21e1ea3364bd8598d34295d9206335973ffd7",
        "preprocessor_config.json": "9b36b57ebaf20f09bf4c22100ccc21877ea6bfe5aead0c00c59f8af8ccefacfc"}.items():
        if digest(MODEL / name) != expected:
            raise ValueError("Official preprocessing/configuration integrity mismatch")


def peak_memory():
    from data import peak_working_set
    return peak_working_set()


def cache(phase):
    """Only a pretrained frozen prefix is evaluated; no label enters this network."""
    if phase == "validation":
        selected = read(ROOT / "selection.json")
        if not selected["training_gate_passed"] or selected["policy_hash"] != policy_hash():
            raise ValueError("No frozen passing training selection")
        if digest(ROOT / "candidate.safetensors") != selected["candidate_sha256"]:
            raise ValueError("Frozen candidate changed")
    rows = groups(phase)
    require_weights()
    torch = torch_setup()
    import cv2
    import numpy as np
    from PIL import Image, ImageEnhance
    from transformers import AutoImageProcessor, SiglipVisionConfig, SiglipVisionModel
    model, info = SiglipVisionModel.from_pretrained(str(MODEL / "vision_tower"),
        config=SiglipVisionConfig.from_pretrained(str(MODEL), local_files_only=True),
        local_files_only=True, use_safetensors=True, torch_dtype=torch.float32,
        output_loading_info=True, attn_implementation="sdpa")
    if any(info.get(key) for key in ["missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs"]):
        raise ValueError("Incomplete official vision tower")
    vision = model.vision_model
    if len(vision.encoder.layers) != 12:
        raise ValueError("Prepared plan expects twelve vision blocks")
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    model.eval()
    processor = AutoImageProcessor.from_pretrained(str(MODEL), local_files_only=True, use_fast=False)
    cv2.setNumThreads(1)
    directory = ROOT / "cache" / phase
    directory.mkdir(parents=True, exist_ok=True)

    def prefix(image):
        pixels = processor(images=image, return_tensors="pt")["pixel_values"]
        with torch.inference_mode():
            hidden = vision.embeddings(pixels)
            for layer in vision.encoder.layers[:11]:
                hidden = layer(hidden, attention_mask=None)
        if hidden.shape != (1, 196, 768) or not torch.isfinite(hidden).all():
            raise ValueError("Invalid frozen prefix output")
        return hidden[0].numpy().copy()

    for number, row in enumerate(rows):
        if digest(row["path"]) != row["sha256"]:
            raise ValueError("Source content differs from frozen group")
        target = directory / row["sha256"]
        target.mkdir(exist_ok=True)
        meta_path = target / "meta.json"
        if meta_path.exists():
            _, metadata = cache_meta(row, phase)
            for index in range(len(metadata["timestamps"])):
                load_hidden(target / f"frame-{index:03d}.npy")
            for index in metadata["fit_indices"]:
                load_hidden(target / f"aug-{index:03d}.npy")
            continue
        started = time.perf_counter()
        watchdog = threading.Timer(300, lambda: os._exit(124))
        watchdog.daemon = True
        watchdog.start()
        cap = cv2.VideoCapture(row["path"])
        try:
            fps, count = float(cap.get(cv2.CAP_PROP_FPS)), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if not cap.isOpened() or not np.isfinite(fps) or fps <= 0 or not 0 < count / fps <= 145.5:
                raise ValueError("Invalid source timing")
            if min(w, h) <= 0 or max(w, h) > 4096 or w * h > 8_000_000:
                raise ValueError("Source pixel bound exceeded")
            # Bounded memory: stream one hidden state per file, never a full decoded clip.
            times, raw_times, next_time, origin, previous = [], [], 0., None, -1.
            training_images = []  # bounded146 resized224RGB images, about22MB maximum
            while cap.grab():
                raw_stamp = float(cap.get(cv2.CAP_PROP_POS_MSEC)) / 1000
                stamp = raw_stamp
                if not np.isfinite(stamp):
                    raise ValueError("Invalid presentation timestamp")
                if origin is None:
                    origin = stamp
                stamp -= origin
                if stamp < previous - .0001:
                    raise ValueError("Nonmonotonic timestamp")
                previous = stamp
                if stamp + .0001 < next_time:
                    continue
                ok, frame = cap.retrieve()
                if not ok or frame is None or frame.ndim != 3 or frame.shape[2] != 3:
                    raise ValueError("Decoder failure")
                if max(frame.shape[:2]) > 4096 or frame.shape[0] * frame.shape[1] > 8_000_000:
                    raise ValueError("Decoded pixel bound exceeded")
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                index = len(times)
                np.save(target / f"frame-{index:03d}.npy", prefix(image), allow_pickle=False)
                if phase == "train":
                    training_images.append(image.resize((224, 224), resample=Image.Resampling.BILINEAR))
                times.append(stamp)
                raw_times.append(raw_stamp)
                next_time += 1.
                if len(times) > 146:
                    raise ValueError("Sampling bound exceeded")
            if not times or previous < count / fps - 2:
                raise ValueError("Incomplete source sampling")
            indices = fitting_indices(times, row["positive"], row["timestamps"]) if phase == "train" else []
            # Only selected fitting frames receive mild augmentation; never heldout inputs.
            for index in indices:
                rng = random.Random(f"{SEED}:{row['sha256']}:{int(index)}")
                augmented = ImageEnhance.Brightness(training_images[index]).enhance(rng.uniform(.95, 1.05))
                augmented = ImageEnhance.Contrast(augmented).enhance(rng.uniform(.95, 1.05))
                np.save(target / f"aug-{index:03d}.npy", prefix(augmented), allow_pickle=False)
            selected = set(map(int, indices))
            for augmentation in target.glob("aug-*.npy"):
                if int(augmentation.stem.split("-")[1]) not in selected:
                    augmentation.unlink()
            if not np.allclose(np.asarray(raw_times) - origin, times, atol=1e-9, rtol=0):
                raise ValueError("Presentation timestamp mapping mismatch")
            array_names = [f"frame-{index:03d}.npy" for index in range(len(times))] + [
                f"aug-{int(index):03d}.npy" for index in indices]
            hashes = {name: digest(target / name) for name in array_names}
            write(meta_path, {"policy_hash": policy_hash(), "timestamps": times,
                  "raw_pts_sec": raw_times, "origin_sec": origin,
                  "fit_indices": list(map(int, indices)), "array_sha256": hashes,
                  "seconds": time.perf_counter() - started})
        finally:
            cap.release()
            watchdog.cancel()
        print(json.dumps({"phase": phase, "cached_groups": number + 1, "expected": len(rows)}), flush=True)


def make_suffix():
    import torch
    from safetensors import safe_open
    from transformers import SiglipVisionConfig
    from transformers.models.siglip.modeling_siglip import SiglipEncoderLayer
    config = SiglipVisionConfig.from_pretrained(str(MODEL), local_files_only=True)
    config._attn_implementation = "sdpa"

    class Suffix(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.block = SiglipEncoderLayer(config)
            self.norm = torch.nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
            self.head = torch.nn.Linear(config.hidden_size, 1)
            torch.nn.init.normal_(self.head.weight, std=.01)
            torch.nn.init.zeros_(self.head.bias)
            with safe_open(str(MODEL / "vision_tower" / "model.safetensors"), framework="pt", device="cpu") as source:
                for module, prefix in [(self.block, "vision_model.encoder.layers.11."),
                                       (self.norm, "vision_model.post_layernorm.")]:
                    module.load_state_dict({key[len(prefix):]: source.get_tensor(key)
                                            for key in source.keys() if key.startswith(prefix)}, strict=True)
            for parameter in self.norm.parameters():
                parameter.requires_grad_(False)

        def forward(self, hidden):
            hidden = self.block(hidden, attention_mask=None)
            pooled = self.norm(hidden).mean(dim=1)
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=-1)
            return self.head(pooled).squeeze(-1)

    return Suffix()


def cache_meta(row, phase):
    folder = ROOT / "cache" / phase / row["sha256"]
    meta = read(folder / "meta.json")
    if meta["policy_hash"] != policy_hash():
        raise ValueError("Cache policy mismatch")
    import numpy as np
    times = np.asarray(meta["timestamps"], dtype=float)
    raw = np.asarray(meta["raw_pts_sec"], dtype=float)
    if (times.ndim != 1 or not 0 < len(times) <= 146 or raw.shape != times.shape or
        not np.isfinite(times).all() or not np.isfinite(raw).all() or
        np.any(np.diff(times) < 0) or not np.allclose(raw - float(meta["origin_sec"]), times, atol=1e-9, rtol=0)):
        raise ValueError("Invalid cached presentation timestamps")
    expected = list(map(int, fitting_indices(times, row["positive"], row["timestamps"]))) if phase == "train" else []
    if meta["fit_indices"] != expected:
        raise ValueError("Cached fitting eligibility differs from frozen annotation")
    import re
    names = {f"frame-{index:03d}.npy" for index in range(len(times))} | {
        f"aug-{int(index):03d}.npy" for index in expected}
    if set(meta.get("array_sha256", {})) != names or any(
        not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
        for value in meta["array_sha256"].values()):
        raise ValueError("Cache array integrity manifest is incomplete")
    for name, sha in meta["array_sha256"].items():
        _CACHE_DIGESTS[str((folder / name).absolute())] = sha
    return folder, meta


def predict(model, row, phase, audit_name=None, threshold=None):
    import numpy as np
    import torch
    folder, meta = cache_meta(row, phase)
    model.eval()
    values = []
    started = time.perf_counter()
    with torch.inference_mode():
        for index in range(len(meta["timestamps"])):
            hidden = torch.from_numpy(load_hidden(folder / f"frame-{index:03d}.npy"))[None]
            values.append(float(torch.sigmoid(model(hidden)).item()))
    score = video_score(values)
    seconds = time.perf_counter() - started + meta["seconds"]
    if audit_name is not None:
        directory = ROOT / "scores" / audit_name
        directory.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(directory / (row["sha256"] + ".npz"),
            probabilities=np.asarray(values, dtype=np.float32),
            elapsed_timestamps_sec=np.asarray(meta["timestamps"], dtype=np.float64),
            raw_pts_sec=np.asarray(meta["raw_pts_sec"], dtype=np.float64),
            origin_sec=float(meta["origin_sec"]), video_score=score,
            anchor_indices=np.asarray(anchor_indices(values, meta["timestamps"], threshold) if threshold is not None else [], dtype=np.int64),
            policy_hash=policy_hash())
    return score, seconds


def fit(rows, deadline):
    import numpy as np
    import torch
    torch.manual_seed(SEED)
    model = make_suffix()
    optimizer = torch.optim.AdamW([{"params": model.block.parameters(), "lr": 1e-5},
                                  {"params": model.head.parameters(), "lr": 1e-3}], weight_decay=.01)
    positive = sum(bool(row["positive"]) for row in rows)
    if positive == 0 or positive == len(rows):
        raise ValueError("Both fit classes required")
    class_weights = {True: len(rows) / (2 * positive), False: len(rows) / (2 * (len(rows) - positive))}
    for epoch in range(3):
        order = list(range(len(rows)))
        random.Random(SEED + epoch).shuffle(order)
        for row_index in order:
            if time.monotonic() >= deadline:
                raise TimeoutError("Bounded training wall budget exhausted")
            row = rows[row_index]
            folder, meta = cache_meta(row, "train")
            indices = meta["fit_indices"]
            if not indices:
                raise ValueError("Missing eligible fit frames")
            model.train()
            optimizer.zero_grad(set_to_none=True)
            for offset in range(0, len(indices), 2):
                batch = indices[offset:offset + 2]
                # Original and fixed mild variant alternate; no validation augmentation.
                prefix = "aug" if epoch % 2 else "frame"
                hidden = torch.from_numpy(np.stack([load_hidden(folder / f"{prefix}-{i:03d}.npy") for i in batch]))
                target = torch.full((len(batch),), float(row["positive"]))
                loss = torch.nn.functional.binary_cross_entropy_with_logits(model(hidden), target, reduction="sum")
                loss = loss * class_weights[bool(row["positive"])] / len(indices)
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite training loss")
                loss.backward()
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.)
            optimizer.step()
    return model


def cross_validate():
    import numpy as np
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold
    from safetensors.torch import save_file
    if (ROOT / "selection.json").exists() or (ROOT / "candidate.safetensors").exists():
        raise ValueError("Training selection is immutable; reuse result or use a new run")
    if (ROOT / "cache" / "validation").exists():
        raise ValueError("Validation was accessed before training selection")
    require_weights()
    torch_setup()
    rows = groups("train")
    labels = np.asarray([int(row["positive"]) for row in rows])
    scores = np.full(len(rows), np.nan)
    deadline = time.monotonic() + 3600
    # Entire hash-group is one row, so stratifying rows is group-safe by construction.
    for fold, (fit_ids, heldout_ids) in enumerate(StratifiedKFold(4, shuffle=True, random_state=SEED).split(np.zeros(len(rows)), labels)):
        if set(fit_ids) & set(heldout_ids):
            raise ValueError("Group leakage")
        model = fit([rows[i] for i in fit_ids], deadline)
        for index in heldout_ids:
            scores[index], _ = predict(model, rows[index], "train", audit_name="oof")
        del model
        print(json.dumps({"completed_training_folds": fold + 1, "expected": 4}), flush=True)
    if not np.isfinite(scores).all():
        raise ValueError("Incomplete OOF predictions")
    selected = select_threshold(labels, scores)
    auc = float(roc_auc_score(labels, scores))
    partial_auc = float(roc_auc_score(labels, scores, max_fpr=.25))
    training_passed = selected is not None and auc > .55 and partial_auc > .5
    result = {"policy_hash": policy_hash(), "training_groups": len(rows), "folds": 4,
              "training_gate_passed": training_passed, "test_processed": 0,
              "oof_roc_auc": auc, "oof_standardized_partial_auc_fpr025": partial_auc,
              "validation_processed": 0, "peak_working_set_bytes": peak_memory()}
    if training_passed:
        threshold, statistics = selected
        model = fit(rows, deadline)
        save_file({key: value.detach().contiguous() for key, value in model.state_dict().items()}, str(ROOT / "candidate.safetensors"))
        result.update(threshold=threshold, oof=statistics,
                      candidate_sha256=digest(ROOT / "candidate.safetensors"))
    np.savez(ROOT / "train_oof.npz", labels=labels, scores=scores)
    write(ROOT / "selection.json", result)
    return result


def validate():
    import numpy as np
    from safetensors.torch import load_file
    selection = read(ROOT / "selection.json")
    if not selection["training_gate_passed"] or selection["policy_hash"] != policy_hash():
        raise ValueError("No passing frozen selection")
    if digest(ROOT / "candidate.safetensors") != selection["candidate_sha256"]:
        raise ValueError("Candidate changed after selection")
    report = ROOT / "validation.json"
    if report.exists():
        if read(report)["policy_hash"] != policy_hash():
            raise ValueError("Existing evaluation contract changed")
        return read(report)  # same immutable evaluation result, no new choice
    torch_setup()
    model = make_suffix()
    model.load_state_dict(load_file(str(ROOT / "candidate.safetensors")), strict=True)
    rows = groups("validation")
    outputs = [predict(model, row, "validation", audit_name="validation", threshold=selection["threshold"]) for row in rows]
    np.savez_compressed(ROOT / "validation_scores.npz",
        scores=np.asarray([value[0] for value in outputs]),
        labels=np.asarray([int(row["positive"]) for row in rows]),
        groups=np.asarray([row["sha256"] for row in rows]),
        threshold=selection["threshold"], candidate_sha256=selection["candidate_sha256"],
        policy_hash=policy_hash())
    statistics = metrics([row["positive"] for row in rows], [value[0] for value in outputs], selection["threshold"])
    longest = max(value[1] for value in outputs)
    passed = statistics["specificity"] >= .75 and statistics["recall"] >= .5 and statistics["balanced_accuracy"] > .5
    result = {"policy_hash": policy_hash(), "validation_groups": len(rows), "test_processed": 0,
              "statistics": statistics, "threshold": selection["threshold"], "longest_estimated_processing_sec": longest,
              "validation_quality_gate_passed": passed, "latency_qualified": False,
              "promotion_gate_passed": False, "ready_for_app": False,
              "note": "Processing estimate includes complete pretrained prefix/augmentation cache time plus suffix; fresh end-to-end subprocess benchmark remains required before promotion"}
    write(report, result)
    return result


def synthetic_benchmark():
    torch = torch_setup()
    require_weights()
    from transformers import SiglipVisionConfig, SiglipVisionModel
    # Confirm the cached11block boundary reconstructs the exact full representation.
    full, info = SiglipVisionModel.from_pretrained(str(MODEL / "vision_tower"),
        config=SiglipVisionConfig.from_pretrained(str(MODEL), local_files_only=True),
        local_files_only=True, use_safetensors=True, torch_dtype=torch.float32,
        output_loading_info=True, attn_implementation="sdpa")
    if any(info.get(key) for key in ["missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs"]):
        raise ValueError("Incomplete official vision tower")
    full.eval()
    model = make_suffix().eval()
    pixels = torch.rand((1, 3, 224, 224), dtype=torch.float32) * 2 - 1
    with torch.inference_mode():
        expected = full(pixel_values=pixels).last_hidden_state
        prefix = full.vision_model.embeddings(pixels)
        for layer in full.vision_model.encoder.layers[:11]:
            prefix = layer(prefix, attention_mask=None)
        actual = model.norm(model.block(prefix, attention_mask=None))
        difference = float(torch.max(torch.abs(expected - actual)))
        if difference > .00005 or not torch.allclose(actual, expected, atol=.00001, rtol=.0001):
            raise ValueError("Frozen prefix/suffix numerical parity failed")
        # Recreate a normal tensor; inference tensors cannot enter backward saves.
        hidden_array = prefix.numpy().copy()
    del full, expected, actual, prefix, pixels
    gc.collect()
    hidden = torch.from_numpy(hidden_array).repeat(2, 1, 1)
    model.train()
    block_before = {key: value.detach().clone() for key, value in model.block.state_dict().items()}
    head_before = model.head.weight.detach().clone()
    # Zero decay in the proof: any changed weight must be due to its gradient.
    # Actual predeclared fitting above retains weight_decay=.01 unchanged.
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-5, weight_decay=0)
    times = []
    finite_nonzero_gradients = False
    for _ in range(3):
        start = time.perf_counter()
        optimizer.zero_grad(set_to_none=True)
        torch.nn.functional.binary_cross_entropy_with_logits(model(hidden), torch.zeros(2)).backward()
        block_gradients = [p.grad for p in model.block.parameters() if p.requires_grad]
        head_gradients = [p.grad for p in model.head.parameters() if p.requires_grad]
        def proved(gradients):
            return all(g is not None and torch.isfinite(g).all() for g in gradients) and any(float(g.abs().max()) > 0 for g in gradients)
        block_gradient_proved, head_gradient_proved = proved(block_gradients), proved(head_gradients)
        finite_nonzero_gradients = block_gradient_proved and head_gradient_proved
        if not finite_nonzero_gradients:
            raise ValueError("Missing, nonfinite or all-zero synthetic gradients")
        optimizer.step()
        times.append(time.perf_counter() - start)
    block_change = max(float((value - block_before[key]).abs().max()) for key, value in model.block.state_dict().items())
    head_change = float((model.head.weight - head_before).abs().max())
    if block_change <= 0 or head_change <= 0:
        raise ValueError("Synthetic backward did not change intended parameters")
    result = {"synthetic_only": True, "case_inputs_processed": 0, "microbatch": 2,
              "prefix_suffix_max_absolute_error": difference, "prefix_suffix_parity_passed": True,
              "finite_nonzero_gradients": finite_nonzero_gradients,
              "block_finite_nonzero_gradients": block_gradient_proved,
              "head_finite_nonzero_gradients": head_gradient_proved,
              "synthetic_proof_weight_decay": 0,
              "last_block_max_weight_change": block_change, "head_max_weight_change": head_change,
              "training_step_seconds": times, "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad),
              "peak_working_set_bytes": peak_memory()}
    write(ROOT / "synthetic_benchmark.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["freeze-split", "audit", "synthetic-benchmark", "cache-train", "cv", "cache-validation", "validate"])
    parser.add_argument("--data-dir", type=Path, required=True, help="Local directory containing videos/ and open_labels.xlsx")
    parser.add_argument("--model-dir", type=Path, required=True, help="Prepared official config, processor and vision_tower/")
    parser.add_argument("--run-dir", type=Path, required=True, help="New private run/cache/output directory")
    parser.add_argument("--split", type=Path, required=True, help="Existing frozen split, or new destination for freeze-split")
    parser.add_argument("--execute", action="store_true", help="Allow local model loads, media decoding and training")
    args = parser.parse_args()
    if args.mode == "freeze-split":
        from data import freeze_split
        return freeze_split(args.data_dir, args.split)
    configure(args)
    if args.mode == "audit":
        return {"policy_hash": policy_hash(), "train_groups": len(groups("train")),
                "validation_groups": len(groups("validation")), "test_processed": 0,
                "source_decodes": 0, "model_loads": 0, "status": "metadata_audit_only",
                "experiment_status": read(POLICY)["status"]}
    if not args.execute:
        raise SystemExit("Heavy mode requires --execute and sufficient local memory")
    if args.mode in {"synthetic-benchmark", "cv", "validate"}:
        timeout = 3600 if args.mode == "cv" else 300
        watchdog = threading.Timer(timeout, lambda: os._exit(124))
        watchdog.daemon = True
        watchdog.start()
    if args.mode == "synthetic-benchmark":
        return synthetic_benchmark()
    if args.mode.startswith("cache-"):
        return cache(args.mode.split("-", 1)[1])
    if args.mode == "cv":
        benchmark = read(ROOT / "synthetic_benchmark.json")
        if benchmark["case_inputs_processed"] != 0 or not benchmark["prefix_suffix_parity_passed"]:
            raise ValueError("Missing synthetic training feasibility check")
        return cross_validate()
    return validate()


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
