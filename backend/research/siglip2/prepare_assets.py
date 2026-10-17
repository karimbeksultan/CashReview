"""Prepare the pinned public vision tower using streaming bytes, without ML loads.

Default operation verifies files already downloaded to --model-dir. The optional
--download flag fetches exact official pinned files, never case data or inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import urllib.request

REPO = "google/siglip2-base-patch16-224"
REVISION = "75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2"
FILES = {
    "README.md": (3375, "39ac3705d62af9ffa1a14675b8ccb220a75f2d81acd530e564a3b1e3dfe418d8"),
    "config.json": (253, "fe8b5fe6d5734360678fd71c11c21e1ea3364bd8598d34295d9206335973ffd7"),
    "preprocessor_config.json": (394, "9b36b57ebaf20f09bf4c22100ccc21877ea6bfe5aead0c00c59f8af8ccefacfc"),
    "model.safetensors": (1500800904, "612923381c76ec5a9bed335d1c48827e3f2e506ac31b044b63b2031fadee6a0b"),
}
VISION_SHA256 = "47b2fedf5dffe18405c5b6d9e9c6147e4648046d1ddff82364f330abf0a5bf2d"
LICENSE_SHA256 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
LICENSE_SOURCE = "https://www.apache.org/licenses/LICENSE-2.0.txt"


def retain_license(root):
    """Retain the actual license and source-model attribution with local weights."""
    bundled = Path(__file__).resolve().parent / "LICENSE-APACHE-2.0.txt"
    if digest(bundled) != LICENSE_SHA256:
        raise ValueError("Canonical Apache2 license integrity mismatch")
    shutil.copyfile(bundled, root / "LICENSE-APACHE-2.0.txt")
    notice = (f"Public pretrained model: {REPO}\nPinned revision: {REVISION}\n"
        f"Source/model card: https://huggingface.co/{REPO}/blob/{REVISION}/README.md\n"
        "The pinned model card declares Apache-2.0. Retain that verified README and\n"
        "the accompanying canonical Apache2 license with these source/derived weights.\n"
        "The recorded upstream file inventory had no separate NOTICE or LICENSE file.\n"
        "The vision tower copies exact selected official tensors without rounding.\n"
        "A learned candidate is a separate derivative with its own digest.\n"
        "Framework/runtime licenses apply separately and do not license these weights.\n"
        "This license does not grant rights to input footage or establish model quality.\n")
    (root / "NOTICE-SIGLIP2.txt").write_text(notice, encoding="utf-8")
    provenance = {"license": "Apache-2.0", "source_url": LICENSE_SOURCE,
        "sha256": LICENSE_SHA256, "file": "LICENSE-APACHE-2.0.txt",
        "model_card_repository": REPO, "model_revision": REVISION,
        "declaration_source": f"https://huggingface.co/{REPO}/blob/{REVISION}/README.md",
        "upstream_notice_basis": "Pinned official repository metadata file inventory; no separate NOTICE listed"}
    (root / "license_provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return provenance


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def verified(path, spec):
    return path.is_file() and path.stat().st_size == spec[0] and digest(path) == spec[1]


def prepare(model_dir, download=False):
    root = Path(model_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    report = []
    for filename, spec in FILES.items():
        target = root / filename
        if not verified(target, spec):
            if not download:
                raise ValueError(f"Missing or corrupt pinned public asset: {filename}")
            partial = target.with_name(target.name + ".partial")
            request = urllib.request.Request(
                f"https://huggingface.co/{REPO}/resolve/{REVISION}/{filename}",
                headers={"User-Agent": "CashReview-LocalAssetPreparation/1"})
            written = 0
            with urllib.request.urlopen(request, timeout=60) as source, partial.open("wb") as output:
                while chunk := source.read(1024 * 1024):
                    written += len(chunk)
                    if written > spec[0]:
                        raise ValueError("Public asset exceeds pinned size")
                    output.write(chunk)
            if not verified(partial, spec):
                raise ValueError("Downloaded public asset integrity mismatch")
            os.replace(partial, target)
        report.append({"file": filename, "bytes": spec[0], "sha256": spec[1]})
    source = root / "model.safetensors"
    with source.open("rb") as stream:
        first = stream.read(8)
        if len(first) != 8:
            raise ValueError("Invalid safetensors header")
        length = struct.unpack("<Q", first)[0]
        if not 2 <= length <= 20 * 1024 * 1024:
            raise ValueError("Invalid safetensors header extent")
        header = json.loads(stream.read(length))
    origin = 8 + length
    selected = sorted(((key, spec) for key, spec in header.items()
        if key.startswith("vision_model.")), key=lambda item: item[1]["data_offsets"][0])
    if not selected:
        raise ValueError("Public model has no vision tensors")
    output_header = {"__metadata__": {"format": "pt"}}
    offset = 0
    for name, spec in selected:
        start, end = spec["data_offsets"]
        if not 0 <= start < end <= source.stat().st_size - origin:
            raise ValueError("Invalid tensor extent")
        output_header[name] = {**spec, "data_offsets": [offset, offset + end - start]}
        offset += end - start
    encoded = json.dumps(output_header, separators=(",", ":")).encode()
    encoded += b" " * (-len(encoded) % 8)
    folder = root / "vision_tower"
    folder.mkdir(exist_ok=True)
    target = folder / "model.safetensors"
    if not target.is_file() or digest(target) != VISION_SHA256:
        partial = target.with_name(target.name + ".partial")
        with source.open("rb") as original, partial.open("wb") as output:
            output.write(struct.pack("<Q", len(encoded)))
            output.write(encoded)
            for _, spec in selected:
                start, end = spec["data_offsets"]
                original.seek(origin + start)
                remaining = end - start
                while remaining:
                    chunk = original.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("Truncated verified tensor stream")
                    output.write(chunk)
                    remaining -= len(chunk)
        if digest(partial) != VISION_SHA256:
            raise ValueError("Extracted official vision tower integrity mismatch")
        os.replace(partial, target)
    provenance = {"repository": REPO, "revision": REVISION,
        "license": "apache-2.0", "license_basis": f"https://huggingface.co/{REPO}/blob/{REVISION}/README.md",
        "derivation": "Exact selected public tensor bytes, no learning or rounding",
        "files": report, "vision_tower_sha256": VISION_SHA256,
        "vision_tower_bytes": target.stat().st_size, "case_inputs_processed": 0,
        "license_text": retain_license(root)}
    (root / "portable_asset_provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return provenance


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(args.model_dir, args.download), indent=2))
