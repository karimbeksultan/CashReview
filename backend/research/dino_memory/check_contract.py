"""Media-free DINO port checks. Never imports Torch/Transformers or opens video."""
from __future__ import annotations
import argparse
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import types
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import manifest_io
import workflow as port


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path)
    args = parser.parse_args()
    checks = 0

    def check(condition):
        nonlocal checks
        if not condition:
            raise AssertionError('Synthetic contract assertion failed')
        checks += 1

    def rejected(function):
        try:
            function()
        except (ValueError, KeyError):
            check(True)
        else:
            check(False)

    receipt = json.loads((HERE / 'source_receipt.json').read_text())
    tree = ast.parse((HERE / 'workflow.py').read_text(encoding='utf-8'))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    for name, expected in receipt['algorithm_ast_sha256'].items():
        actual = hashlib.sha256(ast.dump(functions[name], include_attributes=False).encode()).hexdigest()
        check(actual == expected)
    check(hashlib.sha256((HERE / 'policy.json').read_bytes()).hexdigest() == receipt['original_policy_sha256'])
    if args.original:
        original_bytes = args.original.read_bytes()
        check(hashlib.sha256(original_bytes).hexdigest() == receipt['original_code_sha256'])
        source_nodes = {node.name: node for node in ast.parse(original_bytes).body if isinstance(node, ast.FunctionDef)}
        for name in receipt['algorithm_ast_sha256']:
            check(ast.dump(source_nodes[name], include_attributes=False) == ast.dump(functions[name], include_attributes=False))

    # Independent cosine/neighbour/top-cell calculation for both actual cell layouts.
    rng = np.random.default_rng(27017)
    for cells in (2, 32):
        query = port.unit(rng.normal(size=(5, cells, 7))).astype(np.float32)
        normal = port.unit(rng.normal(size=(8, cells, 7))).astype(np.float32)
        positive = port.unit(rng.normal(size=(4, cells, 7))).astype(np.float32)
        for kind in ('normal_novelty', 'positive_normal_margin'):
            expected = []
            for row in query:
                scores = []
                for cell in range(cells):
                    nearest = max(float(np.dot(row[cell], item[cell])) for item in normal)
                    scores.append(1 - nearest if kind == 'normal_novelty' else max(float(np.dot(row[cell], item[cell])) for item in positive) - nearest)
                expected.append(np.mean(sorted(scores)[-min(4, cells):]))
            np.testing.assert_allclose(port.frame_scores(query, (normal, positive), kind), expected, rtol=2e-6, atol=2e-6)
            check(True)
        zeros = np.zeros_like(query)
        np.testing.assert_array_equal(port.frame_scores(zeros, (normal, positive), 'normal_novelty'), np.zeros(5))
        check(True)
        np.testing.assert_array_equal(port.frame_scores(zeros, (normal, positive), 'positive_normal_margin'), np.full(5, -2.))
        check(True)
    check(np.isclose(port.aggregate(np.array([0., 1., 0.]), 'quantile90'), .8))
    check(port.aggregate(np.array([0., 1., 0.]), 'adjacent2_mean_maximum') == .5)
    check(port.aggregate(np.array([.2]), 'adjacent2_mean_maximum') == .2)
    check(port.choose_threshold([0, 0, 1, 1], [0., 0., 0., 0.]) is None)
    check(port.choose_threshold([0, 0, 1, 1], [1., 1., 0., 0.]) is None)
    chosen = port.choose_threshold([0] * 5 + [1] * 5, [.1, .2, .3, .4, .6, .5, .7, .8, .9, 1.])
    check(chosen is not None and chosen[1]['specificity'] >= .8 and chosen[1]['recall'] >= .5)

    # Odd-height crop rounding and tile order, without any neural network.
    old_tile = port.single_tile
    seen = []
    pixels = np.zeros((101, 51, 3), np.uint8)
    pixels[:, :, 0] = np.arange(101, dtype=np.uint8)[:, None]
    def fake_tile(image, torch, model):
        seen.append((image.size, np.asarray(image)[0, 0, 0], np.asarray(image)[-1, 0, 0]))
        marker = len(seen)
        return np.full((1, 384), marker, np.float32), np.full((16, 384), marker, np.float32)
    port.single_tile = fake_tile
    cls, patch = port.embedding(Image.fromarray(pixels), None, None)
    port.single_tile = old_tile
    check(seen == [((51, 61), 0, 60), ((51, 61), 40, 100)])
    check(cls.shape == (2, 384) and patch.shape == (32, 384))
    check(np.all(cls[0] == 1) and np.all(cls[1] == 2) and np.all(patch[:16] == 1) and np.all(patch[16:] == 2))

    old_load = port.load
    port.load = lambda group, view: (np.arange(42, dtype=np.float32).reshape(21, 1, 2), np.arange(21.))
    normal, positive = port.memory([{'positive': False}, {'positive': True, 'timestamps': [4.]}], 'global')
    port.load = old_load
    check(len(normal) == 16 and len(positive) == 5)
    check(set(positive[:, 0, 0]) == {4., 6., 8., 10., 12.})
    check(port.public_summary({'bindings': {'private': 'hidden'}, 'count': 2}) == {'count': 2})
    capture = io.StringIO()
    with contextlib.redirect_stderr(capture):
        with manifest_io.quiet_dependency_stderr():
            print('synthetic dependency diagnostic', file=sys.stderr)
    check(capture.getvalue() == '')

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        data = root / 'data'
        data.mkdir()
        model = root / 'model'
        model.mkdir()
        rows, assignments = [], {}
        for phase, count in (('train', 8), ('validation', 2), ('test', 2)):
            for i in range(count):
                content = f'synthetic-{phase}-{i}'.encode()
                identifier = hashlib.sha256(content).hexdigest()
                positive = bool(i % 2)
                rows.append({'sha256': identifier, 'path': f'Z:/unavailable/synthetic-{phase}-{i}.mov', 'positive': positive, 'timestamps': [2.] if positive else []})
                assignments[identifier] = phase
        split = root / 'synthetic-split.json'
        def write_split(value):
            split.write_text(json.dumps(value), encoding='utf-8')
        original = {'source': rows, 'assignments': assignments}
        write_split(original)
        relocated = manifest_io.groups(split, data, 'train')
        check(len(relocated) == 8 and all(Path(row['path']).parent == (data / 'videos').resolve() for row in relocated))
        check(all(not Path(row['path']).exists() for row in relocated))
        rejected(lambda: manifest_io.groups(root / 'absent.json', data, 'test'))
        invalid = json.loads(json.dumps(original))
        invalid['source'][0]['positive'] = 0
        write_split(invalid)
        rejected(lambda: manifest_io.groups(split, data, 'train'))
        invalid = json.loads(json.dumps(original))
        invalid['source'][1]['timestamps'] = [True]
        write_split(invalid)
        rejected(lambda: manifest_io.groups(split, data, 'train'))
        invalid = json.loads(json.dumps(original))
        invalid['source'][1]['sha256'] = invalid['source'][0]['sha256']
        write_split(invalid)
        rejected(lambda: manifest_io.groups(split, data, 'train'))
        invalid = json.loads(json.dumps(original))
        invalid['source'][1]['path'] = invalid['source'][0]['path']
        write_split(invalid)
        rejected(lambda: manifest_io.groups(split, data, 'train'))
        write_split(original)

        # Configure/audit does not create outputs or read any synthetic media bytes.
        run = root / 'run'
        port.configure(types.SimpleNamespace(run_dir=run, model_dir=model, split=split, data_dir=data, mode='audit'))
        check(not run.exists())
        rejected(lambda: port.configure(types.SimpleNamespace(run_dir=data / 'run', model_dir=model, split=split, data_dir=data, mode='freeze')))
        port.ROOT = run
        run.mkdir()
        feature_dir = run / 'features'
        feature_dir.mkdir()
        group = rows[0]
        cache = feature_dir / (group['sha256'] + '.npz')
        saved_binding = port.binding
        port.binding = lambda: {'synthetic': True}
        vector = np.full((2, 2, 384), 1 / np.sqrt(384), np.float32)
        np.savez_compressed(cache, global_features=vector, patch_features=np.repeat(vector[:, :1], 32, axis=1), times=np.array([0., 2.]), raw_pts_sec=np.array([5., 7.]), pts_origin_sec=5., fps=30., duration_sec=4., last_relative_pts=3.9667, source_sha256=group['sha256'], seconds=1., binding=json.dumps(port.binding(), sort_keys=True))
        port.save(run / 'cache_manifest.json', {group['sha256']: port.sha(cache)})
        loaded, times = port.load(group, 'global')
        check(loaded.shape == (2, 2, 384) and list(times) == [0., 2.])
        with cache.open('ab') as stream:
            stream.write(b'corrupt')
        rejected(lambda: port.load(group, 'global'))

        # Failures/active attempts cannot be silently retried; no decoder/model imported.
        old_assets, old_groups, old_freeze, old_model = port.verify_assets, port.groups, port.require_freeze, port.load_model
        port.verify_assets = lambda: None
        port.groups = lambda phase: [{}]
        port.require_freeze = lambda: None
        port.load_model = lambda: (_ for _ in ()).throw(AssertionError('Unexpected neural load'))
        old_cv2 = sys.modules.get('cv2')
        sys.modules['cv2'] = types.SimpleNamespace()
        probe = {'estimated74_frames_seconds': 1., 'cold_import_and_model_load_seconds': 1., 'bindings': port.binding(), 'synthetic_only': True, 'case_inputs': 0, 'frames': 12, 'encoder_calls': 24}
        port.save(run / 'probe.json', probe)
        for outcome in ({'state': 'failed'}, {'state': 'started'}):
            port.save(run / 'train_extraction.json', {'expected': 1, 'attempted': 1, 'outcomes': [outcome], 'bindings': port.binding()})
            rejected(lambda: port.extract('train'))
        probe['bindings'] = {'stale': True}
        port.save(run / 'probe.json', probe)
        rejected(lambda: port.extract('train'))
        if old_cv2 is None:
            del sys.modules['cv2']
        else:
            sys.modules['cv2'] = old_cv2
        port.verify_assets, port.groups, port.require_freeze, port.load_model = old_assets, old_groups, old_freeze, old_model
        port.binding = saved_binding

    check('torch' not in sys.modules and 'transformers' not in sys.modules)
    result = {'synthetic_contract_checks': checks, 'passed': checks, 'source_inputs': 0, 'neural_loads': 0, 'original_ast_comparison': bool(args.original)}
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    main()
