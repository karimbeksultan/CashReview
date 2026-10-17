import json
from pathlib import Path

import pytest

from cash_review.references import MAX_REGISTRY_BYTES, sponsor_reference


DIGEST = "a" * 64
UNAVAILABLE = {"available": False, "verdict": None, "type": None, "source": None}


@pytest.mark.parametrize("entry", [
    None,
    {"verdict": "unrecognized", "source": "supplied sponsor workbook"},
    {"verdict": "violation", "type": "invented category", "source": "supplied sponsor workbook"},
    {"verdict": "violation", "type": None, "source": "/private/labels.xlsx"},
    {"verdict": "violation", "type": None, "source": "supplied sponsor workbook", "timestamps_sec": [-1]},
    {"verdict": "violation", "type": None, "source": "supplied sponsor workbook", "timestamps_sec": [float("nan")]},
    {"verdict": "violation", "type": None, "source": "supplied sponsor workbook", "timestamps_sec": [True]},
])
def test_invalid_reference_is_unavailable(tmp_path: Path, entry):
    path = tmp_path / "labels.json"
    path.write_text(json.dumps({"schema_version": 1, "labels": {DIGEST: entry}}), encoding="utf-8")
    assert sponsor_reference(path, DIGEST) == UNAVAILABLE


def test_reference_preserves_original_timestamps_without_inventing_type(tmp_path: Path):
    path = tmp_path / "labels.json"
    path.write_text(json.dumps({"schema_version": 1, "labels": {DIGEST: {
        "verdict": "violation", "type": None, "source": "supplied sponsor workbook", "timestamps_sec": [57, 68]
    }}}), encoding="utf-8")
    assert sponsor_reference(path, DIGEST) == {"available": True, "verdict": "violation", "type": None,
                                              "source": "supplied sponsor workbook", "timestamps_sec": [57, 68]}


def test_missing_corrupt_or_oversized_reference_never_produces_a_verdict(tmp_path: Path):
    path = tmp_path / "labels.json"
    assert sponsor_reference(None, DIGEST) == UNAVAILABLE
    assert sponsor_reference(path, DIGEST) == UNAVAILABLE
    path.write_bytes(b"not JSON")
    assert sponsor_reference(path, DIGEST) == UNAVAILABLE
    path.write_bytes(b" " * (MAX_REGISTRY_BYTES + 1))
    assert sponsor_reference(path, DIGEST) == UNAVAILABLE
