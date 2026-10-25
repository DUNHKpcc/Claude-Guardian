"""Detached ZIP acceptance using synthetic files only; no native/live probes."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'claude-guardian'
CLI_NAMES = ('guardian', 'interview_cli', 'inventory_cli', 'status_dashboard',
             'network_check', 'egress_verifier', 'recovery_cli', 'serve_webrtc')
REQUIRED_LIBRARIES = ('config_edit_plan', 'remedy_plans', 'stun_probe', 'probe_evidence')


class InstalledSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='guardian-installed-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name).resolve()
        staging = cls.root / 'build checkout'
        shutil.copytree(SKILL, staging / 'skills/claude-guardian',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (staging / 'tools').mkdir()
        shutil.copyfile(ROOT / 'tools/package_skill.py', staging / 'tools/package_skill.py')
        shutil.copyfile(ROOT / 'LICENSE', staging / 'LICENSE')
        cls.sentinel = 'SYNTHETIC_PRIVATE_FILE_MUST_NOT_SHIP_7381'
        for relative in ('private-report.json', '.env', 'scripts/private-helper.txt',
                         'references/private-notes.md', 'sources/raw-private.txt'):
            (staging / 'skills/claude-guardian' / relative).write_text(cls.sentinel, encoding='utf-8')
        cls.archive = cls.root / 'release.zip'
        subprocess.run([sys.executable, '-B', str(staging / 'tools/package_skill.py'),
                        '--output', str(cls.archive)], check=True, capture_output=True, timeout=30)
        with zipfile.ZipFile(cls.archive) as archive:
            for name in archive.namelist():
                if not name.startswith('claude-guardian/') or '..' in Path(name).parts:
                    raise AssertionError('Unsafe archive member')
            archive.extractall(cls.root / 'detached installation')
        cls.installed = cls.root / 'detached installation/claude-guardian'
        cls.scripts = cls.installed / 'scripts'
        shutil.rmtree(staging)  # Running code cannot fall back to its build tree.
        cls.cwd = cls.root / 'unrelated working directory'
        cls.cwd.mkdir()

    def invoke(self, module, *args, expected=0):
        # -E/-s ignore inherited Python paths and user packages; -S removes optional
        # site dependencies, while retaining normal script sibling imports.
        result = subprocess.run([sys.executable, '-E', '-s', '-S', '-B',
                                 str(self.scripts / (module + '.py')), *map(str, args)],
                                cwd=self.cwd, capture_output=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def snippet(self, code):
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c',
                                 'import sys; sys.path.insert(0, ' + repr(str(self.scripts)) + ')\n' + code],
                                cwd=self.cwd, capture_output=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_cli_help_without_repository_or_optional_packages(self):
        for module in CLI_NAMES:
            with self.subTest(module=module):
                self.assertIn('usage:', self.invoke(module, '--help').stdout)
        self.assertEqual(list(self.cwd.iterdir()), [])
        self.assertFalse(list(self.installed.rglob('*.pyc')))

    def test_capabilities_and_workflow_are_offline_and_closed(self):
        caps = json.loads(self.invoke('inventory_cli', 'capabilities').stdout)
        self.assertEqual(caps['cli']['mutations'], 'unavailable')
        self.assertEqual(caps['windows']['native_transaction_acceptance'], 'not_run')
        status = json.loads(self.invoke('inventory_cli', 'workflow-status').stdout)
        self.assertEqual(status['workflow']['gate_state'], 'closed')
        self.assertFalse(status['workflow']['transition_available'])

    def test_offline_interview_save_and_resume(self):
        with tempfile.TemporaryDirectory(dir=self.root) as tmp:
            root = Path(tmp)
            first = json.loads(self.invoke('interview_cli').stdout)
            self.assertEqual(first['question']['id'], 'Q-J01')
            self.assertFalse(first['action_executed'])
            self.assertFalse(first['saved'])
            answer, state = root / 'answer.json', root / 'state.json'
            answer.write_text(json.dumps({'question_id': 'Q-J01', 'value': 'first_subscription'}), encoding='utf-8')
            saved = json.loads(self.invoke('interview_cli', '--answer-file', answer,
                                          '--output', state).stdout)
            resumed = json.loads(self.invoke('interview_cli', '--input', state).stdout)
            self.assertEqual(saved['question']['id'], 'Q-C02')
            self.assertEqual(resumed['question']['id'], 'Q-C02')
            self.assertFalse(resumed['action_executed'])

    def test_offline_analysis_plan_and_dashboard_from_synthetic_input(self):
        with tempfile.TemporaryDirectory(dir=self.root) as tmp:
            root = Path(tmp)
            source = root / 'synthetic.json'
            report = root / 'report.json'
            output = root / 'dashboard.html'
            # Empty observations intentionally stay unknown; no host metadata query.
            source.write_text(json.dumps({'schema_version': 'guardian-offline/0.1',
                'record_kind': 'synthetic_example', 'target_ref': 'fixture-device',
                'target_binding': {'declared_os': 'macos', 'desktop_user_relation': 'same',
                    'filesystem_namespace': 'host_desktop', 'execution_location': 'native_local'},
                'contact_phase': 'precontact', 'gate_state': 'closed',
                'snapshot_state': 'stable', 'facts': []}), encoding='utf-8')
            for command in ('analyze', 'plan'):
                args = ['--input', source, '--target-ref', 'fixture-device']
                if command == 'plan':
                    args += ['--output', report]
                result = json.loads(self.invoke('guardian', command, *args).stdout)
                self.assertEqual(result['contact_control']['gate_state'], 'closed')
                self.assertEqual(result['check_status'], 'unknown')
                self.assertEqual(result['changes'], [])
                if command == 'plan':
                    self.assertFalse(result['plan']['executable'])
            self.invoke('status_dashboard', '--input', report, '--output', output)
            html = output.read_text(encoding='utf-8')
            self.assertIn('<html', html)
            self.assertNotIn('<script', html)
            self.assertNotIn('<iframe', html)

    def test_required_modules_and_sibling_dependencies_are_bundled(self):
        modules = {p.stem for p in self.scripts.glob('*.py')}
        self.assertTrue(set(CLI_NAMES + REQUIRED_LIBRARIES) <= modules,
                        sorted(set(CLI_NAMES + REQUIRED_LIBRARIES) - modules))
        repository_modules = {p.stem for p in (SKILL / 'scripts').glob('*.py')}
        for path in self.scripts.glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                imports = ([a.name.split('.')[0] for a in node.names] if isinstance(node, ast.Import)
                           else [node.module.split('.')[0]] if isinstance(node, ast.ImportFrom) and node.module else [])
                for name in imports:
                    if name in repository_modules:
                        self.assertIn(name, modules, str(path.name) + ' requires ' + name)

    def test_imports_have_no_application_io_and_yaml_absence_is_explicit(self):
        modules = sorted(p.stem for p in self.scripts.glob('*.py'))
        self.snippet('''
import ast, ctypes, importlib, json, os, pathlib, socket, subprocess
# Preload standard-library dependencies before forbidding application operations.
for name in ('argparse', 'base64', 'dataclasses', 'datetime', 'hashlib', 'http.client',
             'http.server', 'ipaddress', 'secrets', 'select', 'selectors', 'threading',
             'urllib.parse', 'uuid', 'typing', 'zlib', 'html', 'email.utils'):
    importlib.import_module(name)
def deny(*args, **kwargs):
    raise AssertionError('Import attempted application I/O')
def audit(event, args):
    if event.startswith(('socket.', 'subprocess.')) or event in ('os.system', 'os.spawn', 'ctypes.dlopen'):
        deny()
    if event == 'open':
        path, mode, flags = args
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            deny()
        if not isinstance(path, str) or not path.endswith(('.py', '.pyc', '.so', '.pyd', '.dll')):
            deny()
sys.addaudithook(audit)
for name in ('getuid', 'geteuid', 'getgid', 'getegid', 'getlogin', 'uname'):
    if hasattr(os, name):
        setattr(os, name, deny)
for name in ''' + repr(modules) + ''':
    module = importlib.import_module(name)
    assert pathlib.Path(module.__file__).parent == pathlib.Path(sys.path[0])
import clash_inventory
assert clash_inventory.yaml is None, 'Site packages unexpectedly available'
try:
    clash_inventory._parse(b'mode: rule\\n')
except clash_inventory.InventoryError as error:
    assert error.code == 'RUNTIME_OR_PARSER_UNAVAILABLE'
else:
    raise AssertionError('Missing YAML parser did not fail closed')
print('Detached imports and missing-parser boundary passed')
''')

    def test_skill_and_source_index_links_resolve_inside_bundle(self):
        for relative in ('SKILL.md', 'references/source-library.md'):
            document = self.installed / relative
            for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = (document.parent / unquote(parsed.path)).resolve()
                self.assertTrue(target.is_relative_to(self.installed), link)
                self.assertTrue(target.is_file(), link)
        self.assertTrue((self.installed / 'assets/webrtc-probe.html').is_file())
        self.snippet('import serve_webrtc\nassert serve_webrtc.ASSET.is_file()\n')

    def test_only_allowlisted_public_files_and_verified_sources_ship(self):
        with zipfile.ZipFile(self.archive) as archive:
            names = archive.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertIn('claude-guardian/LICENSE', names)
            for name in names:
                self.assertNotIn('__pycache__', name)
                self.assertNotIn(self.sentinel.encode(), archive.read(name))
            self.assertFalse(any(name.endswith(('.env', '.pyc', 'private-report.json',
                                               'private-helper.txt', 'private-notes.md', 'raw-private.txt')) for name in names))
        manifest = json.loads((self.installed / 'sources/manifest.json').read_text(encoding='utf-8'))
        for source in manifest['sources']:
            entries = [(source['path'], source['distributed_sha256'])]
            entries += [(item['path'], item['sha256']) for item in source.get('companions', [])]
            for relative, digest in entries:
                self.assertEqual(hashlib.sha256((self.installed / relative).read_bytes()).hexdigest(), digest)

    def test_python_310_syntax_baseline_only(self):
        # Parsing is intentionally not advertised as Python 3.10 runtime evidence.
        for path in self.scripts.glob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'), filename=path.name, feature_version=(3, 10))


if __name__ == '__main__':
    unittest.main()
