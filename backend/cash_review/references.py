"""Optional source-label display for an authenticated reviewer.

This module is deliberately independent of the engine and worker. A reference is
looked up only after model analysis completes, and never changes that analysis.
"""

import json
import math
from pathlib import Path
import re
from typing import Any


MAX_REGISTRY_BYTES = 2 * 1024 * 1024
MAX_LABELS = 10000
SOURCE = "supplied sponsor workbook"


def sponsor_reference(path: Path | None, digest: str) -> dict[str, Any]:
    unavailable = {"available": False, "verdict": None, "type": None, "source": None}
    if path is None or not re.fullmatch(r"[0-9a-f]{64}", digest):
        return unavailable
    try:
        with path.open("rb") as stream:
            content = stream.read(MAX_REGISTRY_BYTES + 1)
        if len(content) > MAX_REGISTRY_BYTES:
            return unavailable
        registry = json.loads(content.decode("utf-8-sig"))
        if not isinstance(registry, dict) or type(registry.get("schema_version")) is not int or registry["schema_version"] != 1:
            return unavailable
        labels = registry.get("labels")
        if not isinstance(labels, dict) or len(labels) > MAX_LABELS:
            return unavailable
        entry = labels.get(digest)
        if not isinstance(entry, dict) or entry.get("verdict") not in {"violation", "no_violation"}:
            return unavailable
        # The supplied original labels contain no event categories. Never invent one.
        if entry.get("type") is not None or entry.get("source") != SOURCE:
            return unavailable
        timestamps = entry.get("timestamps_sec", [])
        if not isinstance(timestamps, list) or len(timestamps) > 100:
            return unavailable
        if any(type(value) not in {int, float} or not math.isfinite(value) or not 0 <= value <= 86400
               for value in timestamps):
            return unavailable
        return {"available": True, "verdict": entry["verdict"], "type": None,
                "source": SOURCE, "timestamps_sec": list(timestamps)}
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
        # Optional or corrupt source data must never become an inferred verdict.
        return unavailable
