"""ENV-T34 / ENV-T121 deterministic sentinel matrix over the public input and export paths.

Every case injects a clearly synthetic marker, runs the shipped command, and asserts both the expected
outcome (accept for the unmodified control, fixed-code rejection for unknown members) and that the marker
never reaches stdout, stderr or any file the command created. No network, no real configuration, no
credentials. This is bounded sentinel coverage of the listed paths, not universal secret detection.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'
FIXTURE = ROOT / 'tests/fixtures/proxy-port-conflict.json'
sys.path.insert(0, str(SCRIPTS))
MARKER = 'SYNTHSECRETQ7Z9K2'


def run(args, cwd):
    return subprocess.run([sys.executable, '-B', *map(str, args)], capture_output=True, text=True,
                          cwd=str(cwd), timeout=120)


def made_files(root, before):
    names = {p.name for p in Path(root).iterdir()} - before
    return ''.join((Path(root) / n).read_text(errors='replace') for n in names if (Path(root) / n).is_file())


def unknown_member_mutations():
    """name -> mutation of a valid saved report; each adds a member outside the release vocabulary."""
    def root(key, value=MARKER):
        return lambda d: d.__setitem__(key, value)

    def nested(section, key):
        return lambda d: d[section].__setitem__(key, MARKER)

    def item(section, key):
        return lambda d: d[section][0].__setitem__(key, MARKER)
    return {
        'root proxy_password': root('proxy_password'),
        'root subscription_url': root('subscription_url', 'https://sub.example.invalid/?token=' + MARKER),
        'root command': root('command', 'curl ' + MARKER),
        'snapshot token': nested('snapshot', 'token'),
        'target_binding secret': nested('target_binding', 'secret'),
        'privacy token': nested('privacy', 'token'),
        'limits endpoint': nested('limits', 'endpoint'),
        'contact_control password': nested('contact_control', 'password'),
        'fact password': item('facts', 'password'),
        'finding detail': item('findings', 'detail'),
    }


class SavedReportPaths(unittest.TestCase):
    """analyze/plan on offline fixtures, then status_dashboard and agent_remediation on saved reports."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        saved = cls.root / 'clean.json'
        done = run([SCRIPTS / 'guardian.py', 'analyze', '--input', FIXTURE, '--target-ref', 'device-1',
                    '--output', saved], cls.root)
        assert done.returncode == 0, done.stderr
        cls.clean = json.loads(saved.read_text(encoding='utf-8'))

    def write(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def assert_clean_channels(self, result, before):
        self.assertNotIn(MARKER, result.stdout)
        self.assertNotIn(MARKER, result.stderr)
        self.assertNotIn(MARKER, made_files(self.root, before))

    def test_offline_fixture_analyze_and_plan_reject_unknown_members(self):
        base = json.loads(FIXTURE.read_text(encoding='utf-8'))
        mutations = {'root proxy_password': ('proxy_password', MARKER), 'root command': ('command', 'curl ' + MARKER),
                     'root url_to_test': ('url_to_test', 'https://p.example.invalid/?k=' + MARKER)}
        for command in ('analyze', 'plan'):
            for name, (key, value) in mutations.items():
                with self.subTest(command=command, case=name):
                    obj = deepcopy(base); obj[key] = value
                    src = self.write('in.json', obj)
                    out = self.root / ('out-%s-%s.json' % (command, key))
                    before = {p.name for p in self.root.iterdir()}
                    result = run([SCRIPTS / 'guardian.py', command, '--input', src, '--target-ref', 'device-1',
                                  '--output', out], self.root)
                    self.assertIn(result.returncode, (2, 3))
                    self.assert_clean_channels(result, before)

    def test_saved_report_consumers_accept_control_and_reject_unknown_members(self):
        consumers = {
            'status_dashboard': lambda src, out: [SCRIPTS / 'status_dashboard.py', '--input', src, '--output', out],
            'agent_remediation': lambda src, out: [SCRIPTS / 'agent_remediation.py', 'select', '--input', src,
                                                   '--target-ref', 'device-1'],
        }
        for tool, command in consumers.items():
            out = self.root / ('control-%s.html' % tool)
            control = run(command(self.write('control.json', self.clean), out), self.root)
            self.assertEqual(control.returncode, 0, (tool, control.stderr))
            for name, mutate in unknown_member_mutations().items():
                with self.subTest(tool=tool, case=name):
                    obj = deepcopy(self.clean)
                    mutate(obj)
                    out = self.root / ('reject-%s-%s.html' % (tool, abs(hash(name))))
                    args = command(self.write('mutated.json', obj), out)  # input written before the snapshot
                    before = {p.name for p in self.root.iterdir()}
                    result = run(args, self.root)
                    self.assertEqual(result.returncode, 2, (result.stdout, result.stderr))
                    self.assertFalse(out.exists())
                    self.assert_clean_channels(result, before)

    def test_hostile_values_under_known_members_never_surface(self):
        """Known members are projected through a whitelist; the marker must not reach any output."""
        mutations = {
            'fact value text': lambda d: d['facts'][0].__setitem__('value', 'password=' + MARKER),
            'next_actions text': lambda d: d.__setitem__('next_actions', ['curl ' + MARKER]),
            'missing_fields text': lambda d: d.__setitem__('missing_fields', [MARKER]),
            'target_ref secret': lambda d: d.__setitem__('target_ref', MARKER),
        }
        for name, mutate in mutations.items():
            obj = deepcopy(self.clean)
            mutate(obj)
            src = self.write('hostile.json', obj)
            for tool, command in (
                    ('status_dashboard', [SCRIPTS / 'status_dashboard.py', '--input', src, '--output', None]),
                    ('agent_remediation', [SCRIPTS / 'agent_remediation.py', 'select', '--input', src,
                                           '--target-ref', 'device-1'])):
                with self.subTest(tool=tool, case=name):
                    out = self.root / ('hostile-%s-%s.html' % (tool, abs(hash(name))))
                    args = [out if a is None else a for a in command]
                    before = {p.name for p in self.root.iterdir()}
                    result = run(args, self.root)
                    self.assert_clean_channels(result, before)


class InterviewPaths(unittest.TestCase):
    GOOD = {'question_id': 'Q-J01', 'value': 'first_subscription', 'state': 'reported', 'source': 'user:turn-1'}

    def run_answer(self, tmp, answer):
        (tmp / 'ans.json').write_text(json.dumps(answer), encoding='utf-8')
        out = tmp / 'state.json'
        if out.exists():
            out.unlink()
        before = {p.name for p in tmp.iterdir()}
        result = run([SCRIPTS / 'interview_cli.py', '--target-ref', 'laptop-a', '--account-ref', 'account-a',
                      '--answer-file', tmp / 'ans.json', '--output', out], tmp)
        return result, before

    def test_answer_file_control_accepted_and_hostile_answers_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            result, _ = self.run_answer(tmp, self.GOOD)
            self.assertEqual(result.returncode, 0, result.stderr)
            cases = {
                'value password text': dict(self.GOOD, value='proxy password=' + MARKER),
                'source url token': dict(self.GOOD, source='https://sub.example.invalid/?token=' + MARKER),
                'unknown key secret': dict(self.GOOD, secret=MARKER),
                'unknown key command': dict(self.GOOD, command='curl ' + MARKER),
                'question id secret': dict(self.GOOD, question_id=MARKER),
                'state secret': dict(self.GOOD, state=MARKER),
                'answers[] unknown key': {'answers': [dict(self.GOOD, proxy_password=MARKER)]},
            }
            for name, answer in cases.items():
                with self.subTest(case=name):
                    result, before = self.run_answer(tmp, answer)
                    self.assertEqual(result.returncode, 2, (result.stdout, result.stderr))
                    self.assertIn('INVALID_OR_UNAUTHORIZED_INTERVIEW_IO', result.stdout + result.stderr)
                    self.assertNotIn(MARKER, result.stdout + result.stderr)
                    self.assertNotIn(MARKER, made_files(tmp, before))

    def test_context_file_unknown_members_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            for name, ctx in {'password': {'proxy_password': MARKER},
                              'url': {'subscription_url': 'https://s.example.invalid/?t=' + MARKER},
                              'command': {'command': 'sh ' + MARKER}}.items():
                with self.subTest(case=name):
                    (tmp / 'ctx.json').write_text(json.dumps(ctx), encoding='utf-8')
                    out = tmp / ('state-%s.json' % name)
                    before = {p.name for p in tmp.iterdir()}
                    result = run([SCRIPTS / 'interview_cli.py', '--target-ref', 'laptop-a', '--account-ref',
                                  'account-a', '--context-file', tmp / 'ctx.json', '--output', out], tmp)
                    self.assertEqual(result.returncode, 2, (result.stdout, result.stderr))
                    self.assertNotIn(MARKER, result.stdout + result.stderr)
                    self.assertNotIn(MARKER, made_files(tmp, before))


@unittest.skipUnless(os.name == 'posix', 'POSIX exact-file repair preflight only')
class RepairPaths(unittest.TestCase):
    def setUp(self):
        from test_config_edit_plan import RAW, inputs
        from environment_entry_fixture import local_entry
        import repair_cli
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.target = self.root / 'extension.yaml'
        self.target.write_bytes(RAW)
        self.target.chmod(0o600)
        request, binding = inputs()
        self.doc = {'schema_version': repair_cli.SCHEMA, 'remedy_request': request, 'binding': binding}
        self.entry = local_entry('mac-a')

    def call(self, command, doc, entry):
        req, ef = self.root / 'request.json', self.root / 'entry.json'
        for path, data in ((req, doc), (ef, entry)):
            path.write_text(json.dumps(data), encoding='utf-8')
            path.chmod(0o600)
        before = {p.name for p in self.root.iterdir()}
        extra = ['--private-review'] if command == 'diff' else []
        result = run([SCRIPTS / 'repair_cli.py', command, '--request', req, '--target-path', self.target,
                      '--target-ref', 'mac-a', '--entry-file', ef, *extra], self.root)
        return result, before

    def test_request_and_entry_files_control_accepted_and_unknown_members_rejected(self):
        def mutate(name):
            doc, entry = deepcopy(self.doc), deepcopy(self.entry)
            if name == 'doc proxy_password':
                doc['proxy_password'] = MARKER
            elif name == 'doc command':
                doc['command'] = 'curl ' + MARKER
            elif name == 'remedy_request subscription_url':
                doc['remedy_request']['subscription_url'] = 'https://s.example.invalid/?t=' + MARKER
            elif name == 'binding secret':
                doc['binding']['secret'] = MARKER
            elif name == 'intent token':
                doc['remedy_request']['intent']['token'] = MARKER
            elif name == 'entry proxy_password':
                entry['proxy_password'] = MARKER
            return doc, entry
        for command in ('preflight', 'plan', 'diff'):
            result, _ = self.call(command, self.doc, self.entry)
            self.assertEqual(result.returncode, 0, (command, result.stderr))
            for name in ('doc proxy_password', 'doc command', 'remedy_request subscription_url',
                         'binding secret', 'intent token', 'entry proxy_password'):
                with self.subTest(command=command, case=name):
                    doc, entry = mutate(name)
                    result, before = self.call(command, doc, entry)
                    self.assertEqual(result.returncode, 2, (result.stdout, result.stderr))
                    self.assertNotIn(MARKER, result.stdout + result.stderr)
                    self.assertNotIn(MARKER, made_files(self.root, before))


if __name__ == '__main__':
    unittest.main()
