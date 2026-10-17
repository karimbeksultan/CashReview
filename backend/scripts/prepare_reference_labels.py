"""Build a private sponsor reference registry for presentation only.

This registry is not a model input, a training update, or a jury-result override.
The workbook has binary labels/timestamps and supplies no event categories.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from train_baseline import read_source


def prepare(data_dir: Path, output: Path) -> dict:
    groups = read_source(data_dir.resolve())
    registry = {
        "schema_version": 1,
        "labels": {
            group["sha256"]: {
                "verdict": "violation" if group["positive"] else "no_violation",
                "type": None,
                "source": "supplied sponsor workbook",
                "timestamps_sec": sorted(group["timestamps"]),
            }
            for group in groups
        },
    }
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    try:
        temporary.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {"prepared": True, "unique_reference_entries": len(registry["labels"]),
            "positive_entries": sum(group["positive"] for group in groups),
            "negative_entries": sum(not group["positive"] for group in groups),
            "reference_categories_available": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True, help="Private open/ directory containing workbook and videos/")
    parser.add_argument("--output", type=Path, required=True, help="Explicit private ignored reference JSON destination")
    args = parser.parse_args()
    print(json.dumps(prepare(args.data_dir, args.output)))
