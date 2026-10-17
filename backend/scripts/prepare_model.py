"""Preparation-only network download. The service itself never downloads a model."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cash_review.engine import MODEL_FILE, MODEL_SHA256

MODEL_URL = "https://media.githubusercontent.com/media/onnx/models/main/validated/vision/classification/mobilenet/model/mobilenetv2-7.onnx"
LICENSE_URL = "https://raw.githubusercontent.com/onnx/models/main/LICENSE"
README_URL = "https://github.com/onnx/models/blob/main/validated/vision/classification/mobilenet/README.md"


def prepare(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / MODEL_FILE
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != MODEL_SHA256:
        temporary = directory / (MODEL_FILE + ".download")
        try:
            with urllib.request.urlopen(MODEL_URL, timeout=120) as source, temporary.open("wb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != MODEL_SHA256:
                raise RuntimeError("Downloaded backbone does not match the pinned official ONNX LFS hash")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    license_path = directory / "MOBILENET_APACHE_LICENSE.txt"
    if not license_path.exists():
        with urllib.request.urlopen(LICENSE_URL, timeout=30) as response:
            license_path.write_bytes(response.read())
    provenance = {"name": "ONNX Model Zoo MobileNetV2 opset7", "url": MODEL_URL,
                  "sha256": MODEL_SHA256, "bytes": target.stat().st_size,
                  "license": "Apache-2.0", "license_source": README_URL,
                  "purpose": "Frozen ImageNet representation; not a cashier action detector"}
    (directory / "backbone_provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(json.dumps({"prepared": True, "model_dir": str(directory.resolve()), "sha256": MODEL_SHA256}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True, help="Private, ignored artifact directory")
    prepare(parser.parse_args().model_dir)
