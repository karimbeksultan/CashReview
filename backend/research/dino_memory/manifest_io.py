"""Strict local manifest/model handling; metadata validation never decodes media."""
from __future__ import annotations
import hashlib
import contextlib
import json
import math
import re
import os
from pathlib import Path, PureWindowsPath

MODEL = 'facebook/dinov2-small'
REVISION = 'ed25f3a31f01632728cabb09d1542f84ab7b0056'
EXPECTED = {
    'config.json': '1809f83e3bdb1609a501a610ad4a742f4fd8ae44d72ca4aa0df52d1f2ac8628d',
    'preprocessor_config.json': '14e780d86fa1861f8751f868d7f45425b5feb55c38ca26f152ca5097ab30f828',
    'README.md': '4c20dca454a8e5c670e8de5c7e6040f512aeca5438516f7623eedc4e3b00599c',
    'model.safetensors': 'ae1e99fcefd534ed978cdeb8326f08030c96e28b7a81ffcbc98a857c84d14be1',
}
LICENSE = {
    'LICENSE-DINOV2-APACHE-2.0.txt': '600cc67cc4cb2f5ea317dcfc687ad1c74dc4bec8782bbe9db0afd83513b935b7',
    'upstream-README.md': 'd1bc2e9686522bbd66ed6123dc81eb36b3a98e8ea9a2ca97778f54a1c641c9e1',
    'upstream-MODEL_CARD.md': '70ca59606bee0a5fbb1baec80e7e29a93cd7cfbe26ca1910c52a852c4aab09d0',
}


@contextlib.contextmanager
def quiet_dependency_stderr():
    """Keep decoder/model-library diagnostics from echoing private local paths."""
    saved = os.dup(2)
    try:
        with open(os.devnull, 'w') as sink, contextlib.redirect_stderr(sink):
            os.dup2(sink.fileno(), 2)
            try:
                yield
            finally:
                os.dup2(saved, 2)
    finally:
        os.close(saved)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def groups(split_path, data_dir, phase):
    if phase not in ('train', 'validation'):
        raise ValueError('Test processing prohibited')
    source = read(split_path)
    rows, assignments = source['source'], source['assignments']
    if not isinstance(rows, list) or not rows or not isinstance(assignments, dict):
        raise ValueError('Invalid split schema')
    seen, leaves, clean = set(), set(), []
    media_root = (Path(data_dir) / 'videos').resolve()
    for row in rows:
        identifier = row['sha256']
        if not isinstance(identifier, str) or not re.fullmatch('[0-9a-f]{64}', identifier) or identifier in seen:
            raise ValueError('Invalid or duplicate content group')
        seen.add(identifier)
        if assignments.get(identifier) not in ('train', 'validation', 'test'):
            raise ValueError('Invalid split membership')
        if type(row['positive']) is not bool:
            raise ValueError('Binary labels must be JSON booleans')
        timestamps = row['timestamps']
        if not isinstance(timestamps, list) or any(type(t) not in (int, float) or not math.isfinite(t) or t < 0 for t in timestamps):
            raise ValueError('Invalid sparse annotations')
        if row['positive'] and not timestamps:
            raise ValueError('Positive content group needs a sparse annotation')
        raw_path = row['path']
        if not isinstance(raw_path, str) or not raw_path or '\x00' in raw_path:
            raise ValueError('Missing local media filename')
        # Relocate legacy paths by exact Unicode leaf; never read their old location.
        leaf = PureWindowsPath(raw_path).name
        if leaf in ('', '.', '..') or leaf.casefold() in leaves:
            raise ValueError('Ambiguous local filename')
        leaves.add(leaf.casefold())
        candidate = (media_root / leaf).resolve()
        if candidate.parent != media_root:
            raise ValueError('Media must remain inside the explicit data directory')
        clean.append({**row, 'path': str(candidate)})
    if set(assignments) != seen:
        raise ValueError('Split membership and content groups differ')
    selected = [row for row in clean if assignments[row['sha256']] == phase]
    counts = [sum(row['positive'] == label for row in selected) for label in (False, True)]
    if min(counts) < (4 if phase == 'train' else 1):
        raise ValueError('Insufficient per-class content groups for the fixed evaluation')
    return selected


def verify_model(model_dir):
    root = Path(model_dir).resolve()
    provenance = read(root / 'provenance.json')
    if provenance.get('model') != MODEL or provenance.get('revision') != REVISION or provenance.get('license') != 'Apache-2.0':
        raise ValueError('Official model provenance differs')
    files = provenance.get('files', {})
    if set(files) != set(EXPECTED):
        raise ValueError('Official asset inventory differs')
    for name, expected in EXPECTED.items():
        record = files[name]
        actual = record if isinstance(record, str) else record['sha256']
        target = (root / name).resolve()
        if target.parent != root or actual != expected or digest(target) != expected:
            raise ValueError('Official asset integrity differs')
    for name, expected in LICENSE.items():
        target = (root / name).resolve()
        if target.parent != root or digest(target) != expected:
            raise ValueError('Official licence/context integrity differs')
    return provenance
