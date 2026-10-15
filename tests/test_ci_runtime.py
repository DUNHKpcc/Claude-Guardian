"""Workflow wiring contracts; never a substitute for a Python 3.10 CI receipt."""
from pathlib import Path
import unittest

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
SETUP_PYTHON = 'actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1'


@unittest.skipIf(yaml is None, 'Optional pinned test YAML parser unavailable')
class MinimumRuntimeWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.load((ROOT / '.github/workflows/tests.yml').read_text(
            encoding='utf-8'), Loader=yaml.BaseLoader)
        cls.job = cls.workflow['jobs']['minimum-python']
        cls.steps = cls.job['steps']

    def test_minimum_runtime_is_additive_linux_job(self):
        self.assertEqual(self.job['runs-on'], 'ubuntu-latest')
        self.assertEqual(self.job['timeout-minutes'], '10')
        self.assertEqual(self.workflow['jobs']['test']['strategy']['matrix']['os'],
                         ['ubuntu-latest', 'macos-latest', 'windows-latest'])
        self.assertEqual(self.workflow['permissions'], {'contents': 'read'})

    def test_official_immutable_setup_precedes_version_assertion_and_tests(self):
        setup = next(i for i, step in enumerate(self.steps) if step.get('uses') == SETUP_PYTHON)
        self.assertEqual(self.steps[setup]['with'], {'python-version': '3.10', 'architecture': 'x64'})
        version = next(i for i, step in enumerate(self.steps)
                       if 'assert sys.version_info[:2] == (3, 10)' in step.get('run', ''))
        suite = next(i for i, step in enumerate(self.steps)
                     if step.get('run') == 'python -m unittest discover -s tests -v')
        self.assertLess(setup, version)
        self.assertLess(version, suite)

    def test_detached_package_and_reproducibility_are_executed(self):
        commands = '\n'.join(step.get('run', '') for step in self.steps)
        for command in ('python -m pip install -r requirements-dev.txt',
                        'python -m unittest discover -s tests -p test_installed_skill.py -v',
                        'python -m compileall -q skills/claude-guardian/scripts',
                        'python tools/package_skill.py --output "$RUNNER_TEMP/minimum-a.zip"',
                        'python tools/package_skill.py --output "$RUNNER_TEMP/minimum-b.zip"',
                        "assert (p/'minimum-a.zip').read_bytes() == (p/'minimum-b.zip').read_bytes()"):
            self.assertIn(command, commands)

    def test_failures_are_not_masked_and_native_smoke_is_not_enabled(self):
        for item in (self.job, *self.steps):
            self.assertNotIn('continue-on-error', item)
            self.assertNotIn('if', item)
            self.assertNotIn('env', item)
        commands = '\n'.join(step.get('run', '') for step in self.steps)
        self.assertNotIn('||', commands)
        self.assertNotIn('GUARDIAN_NATIVE_CONTEXT_CI', commands)


if __name__ == '__main__':
    unittest.main()
