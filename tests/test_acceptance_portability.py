"""Small pre-push guards for acceptance-test helpers, not native certification."""
import ast
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AcceptancePortabilityTests(unittest.TestCase):
    def test_acceptance_helpers_use_explicit_encoding_and_python310_apis(self):
        for path in sorted((ROOT / 'tests').glob('test_acceptance*.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'), feature_version=(3, 10))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                attr = node.func.attr if isinstance(node.func, ast.Attribute) else ''
                label = f'{path.name}:{node.lineno}'
                if attr in ('read_text', 'write_text'):
                    self.assertTrue(any(k.arg == 'encoding' for k in node.keywords), label)
                is_open = attr == 'open' or (isinstance(node.func, ast.Name) and node.func.id == 'open')
                if is_open:
                    module_open = isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id in ('io', 'builtins')
                    mode_index = 1 if isinstance(node.func, ast.Name) or module_open else 0
                    mode = next((k.value for k in node.keywords if k.arg == 'mode'),
                                node.args[mode_index] if len(node.args) > mode_index else ast.Constant('r'))
                    binary = isinstance(mode, ast.Constant) and isinstance(mode.value, str) and 'b' in mode.value
                    if not binary:
                        self.assertTrue(any(k.arg == 'encoding' for k in node.keywords), label)
                self.assertNotEqual(attr, 'enterContext', label + ': TestCase API requires Python 3.11')

    def test_relevant_acceptance_helpers_under_cp1252_default(self):
        code = r'''
import builtins, io, sys, unittest
from unittest.mock import patch
real_io_open, real_open = io.open, builtins.open
def wrap(original):
    def opened(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        if 'b' not in mode and encoding in (None, 'locale'):
            encoding = 'cp1252'
        return original(file, mode, buffering, encoding, errors, newline, closefd, opener)
    return opened
sys.path.insert(0, sys.argv[1])
with patch.object(io, 'open', wrap(real_io_open)), patch.object(builtins, 'open', wrap(real_open)):
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'test_acceptance_diagnostic_evidence',
        'test_acceptance_resume_completion',
        'test_acceptance_local_egress',
    ])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
'''
        env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT / 'tests')],
                                cwd=ROOT, env=env, capture_output=True, text=True,
                                encoding='utf-8', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Ran 14 tests', result.stderr)


if __name__ == '__main__':
    unittest.main()
