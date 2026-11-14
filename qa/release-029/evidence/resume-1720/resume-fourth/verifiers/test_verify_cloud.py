#!/usr/bin/env python3
"""Host-only self-evidence; fixtures never overwrite the source artifact."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'qa/diag_emulator_smoke.py').is_file())
OLD = ROOT / 'qa/release-029/evidence/resume-1720'
SHA = '44df9d0fd36aecaa22613e9aa73c5c7d4ed94416'
OUT: Path = HERE


class CloudTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = {}

    def run_cli(self, suite, run, name):
        command = [sys.executable, '-B', str(HERE / 'verify_cloud.py'), '--source', SHA,
                   '--run', run, '--suite', suite, '--incoming',
                   str(OLD / (('diag' if suite == 'diagnostics' else 'full') + '-44df9d0-evidence'))]
        command += ['--out', str(OUT / name)]
        result = subprocess.run(command, capture_output=True)
        (OUT / (name + '.stdout.bin')).write_bytes(result.stdout)
        (OUT / (name + '.stderr.bin')).write_bytes(result.stderr)
        (OUT / (name + '.execution.json')).write_text(json.dumps(
            {'command': command, 'exit_code': result.returncode}) + '\n')
        return result

    def test_01_real_diag_green(self):
        self.assertTrue((HERE / 'verify_cloud.py').is_file(), 'Missing independent verifier implementation')
        result = self.run_cli('diagnostics', '43590599162', 'old-diag')
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIs(json.loads((OUT / 'old-diag/receipt.json').read_text())['passed'], True)

    def test_02_real_full_red_preserved(self):
        self.assertTrue((HERE / 'verify_cloud.py').is_file(), 'Missing independent verifier implementation')
        result = self.run_cli('full', '43590641863', 'old-full-red')
        self.assertEqual(result.returncode, 1, result.stderr.decode())
        receipt = json.loads((OUT / 'old-full-red/receipt.json').read_text())
        self.assertIs(receipt['passed'], False)
        raw = json.loads((OUT / 'old-full-red/raw/artifact/report.json').read_text())
        self.assertIs(raw['harvested'], False)
        self.assertTrue(receipt['errors'])

    def test_03_minimal_negatives(self):
        self.assertTrue((HERE / 'verify_cloud.py').is_file(), 'Missing independent verifier implementation')
        spec = importlib.util.spec_from_file_location('cloud', HERE / 'verify_cloud.py')
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        art = OLD / 'diag-44df9d0-evidence/artifact'
        host = json.loads((art / 'diag-host-report.json').read_text())
        run = json.loads((art.parent / 'run.json').read_text())
        bad = dict(run, headSha='0' * 40)
        with self.assertRaises(AssertionError): module.check_run(bad, SHA, '43590599162')
        with self.assertRaises(AssertionError): module.check_host(dict(host, passed=False), SHA)
        diag = module.load_original('diag_emulator_smoke')
        keep = json.loads((art / 'diag-product/keepalive-report.json').read_text())
        keep['defaultOn'] = False
        with self.assertRaises(AssertionError):
            diag.verify_keepalive_report(keep, SHA, host['qaRun'], int(host['sdk']))
        actual = host['independentPngChecks']
        module.compare(actual, json.loads(json.dumps(actual)), 'serialization')
        from PIL import Image
        from typing import cast
        source = art / 'diag-product/settings-version.png'
        im = Image.open(source).convert('RGB')
        x, y = actual[0]['bounds'][:2]; old = cast(tuple[int, int, int], im.getpixel((x, y)))
        changed = ((old[0] + 1) % 256, old[1], old[2]); im.putpixel((x, y), changed)
        with tempfile.TemporaryDirectory(dir=OUT) as directory:
            mutated = Path(directory) / source.name; im.save(mutated)
            image = Image.open(mutated).convert('RGB')
            full = diag.pixel_stats(image, [0, 0, image.width, image.height], 3)
            local = diag.pixel_stats(image, actual[0]['bounds'], 1)
            # This 1px still passes original thresholds; full-report equality must not.
            diag.verify_pixels(full, local)
            row = dict(actual[0], fullPixels=full, targetPixels=local)
            with self.assertRaises(AssertionError): module.compare([row] + actual[1:], actual, '1px')
        (OUT / 'negative-receipt.json').write_text(json.dumps({
            'passed': True, 'source_mutation_rejected': True, 'passed_false_rejected': True,
            'keepalive_false_rejected': True, 'one_pixel_complete_compare_rejected': True,
            'one_pixel_original_thresholds_passed': True, 'pixel': [x, y],
            'before_rgb': old, 'after_rgb': changed,
            'scope': 'in-memory/temp host fixtures, not universal 1px threshold rejection'}) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); OUT = args.out.resolve(); OUT.mkdir(parents=True, exist_ok=False)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CloudTests)
    with (OUT / 'tests.log').open('x') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    print(json.dumps({'successful': result.wasSuccessful(), 'tests': result.testsRun,
                      'failures': len(result.failures), 'errors': len(result.errors), 'out': str(OUT)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
