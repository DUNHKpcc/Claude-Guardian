"""Only temporary request/config fixtures; no native app or real controller I/O."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from environment_entry_fixture import local_entry

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import inventory_cli as cli


class Terminal(io.StringIO):
    def isatty(self):
        return True


@unittest.skipUnless(os.name == 'posix', 'POSIX request-reader fixture coverage')
class InventoryCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = self.root / 'config.yaml'
        self.config.write_text('mode: rule\nsecret: RAW_SECRET_SENTINEL\n', encoding='utf-8')
        self.path = self.root / 'request.json'
        self.request = {'schema_version': 'guardian-static-cli-request/2', 'target_ref': 'device-1',
                        'entry_request': local_entry('device-1'),
                        'target_binding': {'target_ref': 'device-1', 'binding_state': 'bound',
                           'declared_os': 'macos', 'execution_location': 'native_local',
                           'desktop_user_relation': 'same', 'filesystem_namespace': 'host_desktop'},
                        'application': {'product': 'clash-verge-rev', 'gui_version': '2.5.5', 'core_version': '1.19.0'},
                        'files': [{'source_ref': 'profile-1', 'kind': 'profile', 'path': str(self.config)}]}
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.request), encoding='utf-8')

    def invoke(self, argv=None, response='READ\n', terminal=True):
        out = io.StringIO()
        incoming = Terminal(response) if terminal else io.StringIO(response)
        prompt = Terminal() if terminal else io.StringIO()
        args = argv or ['static-audit', '--request', str(self.path), '--target-ref', 'device-1']
        with patch.object(cli.sys, 'platform', 'darwin'):
            code = cli.run(args, incoming=incoming, outgoing=out, prompt=prompt)
        self.assertNotIn('RAW_SECRET_SENTINEL', out.getvalue() + prompt.getvalue())
        return code, json.loads(out.getvalue()), prompt.getvalue()

    def test_static_fixture_no_writes(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        code, result, prompt = self.invoke()
        if cli.clash_inventory.yaml is None:
            self.assertEqual(code, 2)
        else:
            self.assertEqual(code, 0)
            self.assertEqual(result['inventory']['files'][0]['values']['mode']['value'], 'rule')
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
        self.assertIn(str(self.config), prompt)
        self.assertIn('not authenticated consent', prompt)
        self.assertEqual(result['gate_state'], 'closed')
        self.assertFalse(result['permission_restorable'])
        self.assertNotIn(str(self.config), json.dumps(result))

    def test_nonterminal_does_not_read_config(self):
        with patch.object(cli.clash_inventory, 'audit_inventory') as audit:
            code, result, _ = self.invoke(terminal=False)
        audit.assert_not_called()
        self.assertEqual((code, result['error_code']), (3, 'LIVE_TERMINAL_REQUIRED'))

    def test_denied_and_eof_do_not_read(self):
        for response in ('', 'yes\n', 'READ', 'READ later\n', 'no\n'):
            with self.subTest(response=response), patch.object(cli.clash_inventory, 'audit_inventory') as audit:
                code, result, _ = self.invoke(response=response)
                audit.assert_not_called()
                self.assertEqual((code, result['error_code']), (3, 'USER_CANCELLED'))

    def test_saved_grants_rejected(self):
        for key, value in (('authorization', {'approved': True}), ('approved', True), ('gate_state', 'open_scoped')):
            with self.subTest(key=key):
                self.request[key] = value
                self.save()
                code, result, prompt = self.invoke()
                self.assertEqual(code, 2)
                self.assertEqual(prompt, '')
                del self.request[key]

    def test_mismatch_before_prompt(self):
        self.request['target_ref'] = 'another-device'
        self.save()
        code, result, prompt = self.invoke()
        self.assertEqual((code, result['error_code'], prompt), (2, 'TARGET_NOT_BOUND', ''))

    def test_cloud_binding_blocked(self):
        self.request['target_binding']['execution_location'] = 'cloud'
        self.save()
        self.assertEqual(self.invoke()[1]['error_code'], 'TARGET_USER_CONTEXT_MISMATCH')

    def test_linux_cannot_claim_mac(self):
        out = io.StringIO()
        with patch.object(cli.sys, 'platform', 'linux'):
            code = cli.run(['static-audit', '--request', str(self.path), '--target-ref', 'device-1'],
                           incoming=Terminal('READ\n'), outgoing=out, prompt=Terminal())
        self.assertEqual(code, 2)
        self.assertIn('TARGET_USER_CONTEXT_MISMATCH', out.getvalue())

    def test_unsupported_version(self):
        self.request['application']['core_version'] = 'future'
        self.save()
        self.assertEqual(self.invoke()[1]['error_code'], 'UNSUPPORTED_PRODUCT_OR_VERSION')

    def test_invalid_file_fields(self):
        for field, value in [('source_ref', 'RAW_SECRET_SENTINEL\n'), ('kind', []), ('path', 'relative')]:
            original = self.request['files'][0][field]
            self.request['files'][0][field] = value
            self.save()
            self.assertEqual(self.invoke()[0], 2)
            self.request['files'][0][field] = original

    def test_duplicate_targets(self):
        self.request['files'].append(dict(self.request['files'][0], source_ref='another'))
        self.save()
        self.assertEqual(self.invoke()[0], 2)

    def test_duplicate_json_keys(self):
        self.path.write_text('{"secret":0,"secret":"RAW_SECRET_SENTINEL"}')
        self.assertEqual(self.invoke()[1]['error_code'], 'INPUT_OR_RESPONSE_INVALID')

    def test_nonfinite_json(self):
        self.path.write_text('{"x":NaN}')
        self.assertEqual(self.invoke()[0], 2)

    def test_deep_json_is_sanitized(self):
        self.path.write_text('[' * 2000 + '0' + ']' * 2000)
        self.assertEqual(self.invoke()[0], 2)

    def test_oversize_request(self):
        self.path.write_bytes(b' ' * (cli.MAX_REQUEST_BYTES + 1))
        self.assertEqual(self.invoke()[1]['error_code'], 'BUDGET_EXCEEDED')

    @unittest.skipUnless(os.name == 'posix', 'POSIX links')
    def test_request_symlink_rejected(self):
        self.path.unlink()
        self.path.symlink_to(self.config)
        self.assertEqual(self.invoke()[0], 2)

    @unittest.skipUnless(os.name == 'posix', 'POSIX links')
    def test_request_ancestor_symlink_rejected(self):
        link = self.root / 'linked'
        link.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(self.invoke(['static-audit', '--request', str(link / self.path.name), '--target-ref', 'device-1'])[0], 2)

    @unittest.skipUnless(os.name == 'posix', 'POSIX fifo')
    def test_request_fifo_rejected_without_block(self):
        self.path.unlink()
        os.mkfifo(self.path)
        self.assertEqual(self.invoke()[0], 2)

    def test_argument_errors_do_not_echo(self):
        code, result, _ = self.invoke(['capabilities', '--secret=RAW_SECRET_SENTINEL'])
        self.assertEqual((code, result['error_code']), (2, 'INVALID_ARGUMENTS'))

    def test_unknown_command(self):
        self.assertEqual(self.invoke(['RAW_SECRET_SENTINEL'])[0], 2)

    def test_capabilities_no_config_read(self):
        with patch.object(cli, 'read_request', side_effect=AssertionError):
            code, result, _ = self.invoke(['capabilities'])
        self.assertEqual(code, 0)
        self.assertNotIn('windows', result)
        self.assertEqual(result['cli']['mutations'], 'unavailable')


    def test_noncanonical_request_paths(self):
        for path in (str(self.root) + '//request.json', str(self.path) + '/',
                     str(self.root) + '/./request.json'):
            with self.subTest(path=path):
                self.assertEqual(self.invoke(['static-audit', '--request', path,
                                             '--target-ref', 'device-1'])[1]['error_code'],
                                 'UNSAFE_OR_OFFLINE_PATH')

    def test_noncanonical_config_path_before_io(self):
        self.request['files'][0]['path'] = str(self.root) + '//config.yaml'
        self.save()
        with patch.object(cli.clash_inventory, 'audit_inventory') as audit:
            self.assertEqual(self.invoke()[1]['error_code'], 'UNSAFE_OR_OFFLINE_PATH')
        audit.assert_not_called()

    def test_invalid_second_file_zero_collector_io(self):
        self.request['files'].append({'source_ref': 'second', 'kind': 'profile', 'path': 'relative'})
        self.save()
        with patch.object(cli.clash_inventory, 'audit_inventory') as audit, \
                patch.object(cli.clash_inventory, '_read') as read:
            code, _, prompt = self.invoke()
        self.assertEqual(code, 2)
        self.assertEqual(prompt, '')
        audit.assert_not_called()
        read.assert_not_called()

    def test_request_hardlink_rejected(self):
        os.link(self.path, self.root / 'second-request.json')
        self.assertEqual(self.invoke()[1]['error_code'], 'UNSAFE_OR_OFFLINE_PATH')

    def test_request_changes_during_read(self):
        original = os.fstat
        calls = []
        def changed(fd):
            observed = original(fd)
            calls.append(fd)
            fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode', 'st_nlink')
            values = {field: getattr(observed, field) for field in fields}
            if len(calls) == 2:
                values['st_mtime_ns'] += 1
            return SimpleNamespace(**values)
        with patch.object(cli.os, 'fstat', side_effect=changed), \
                patch.object(cli.clash_inventory, 'audit_inventory') as audit:
            self.assertEqual(self.invoke()[1]['error_code'], 'SNAPSHOT_CHANGED_DURING_AUDIT')
        audit.assert_not_called()

    @unittest.skipIf(cli.clash_inventory.yaml is None, 'Optional YAML parser unavailable')
    def test_config_symlink_rejected(self):
        actual = self.root / 'actual.yaml'
        self.config.rename(actual)
        self.config.symlink_to(actual)
        code, result, _ = self.invoke()
        self.assertEqual(code, 2)
        self.assertEqual(result['inventory']['files'], [])
        self.assertEqual(result['inventory']['errors'][0]['code'], 'UNSAFE_OR_OFFLINE_PATH')

    @unittest.skipIf(cli.clash_inventory.yaml is None, 'Optional YAML parser unavailable')
    def test_config_fifo_rejected_without_block(self):
        self.config.unlink()
        os.mkfifo(self.config)
        code, result, _ = self.invoke()
        self.assertEqual(code, 2)
        self.assertEqual(result['inventory']['files'], [])
        self.assertEqual(result['inventory']['errors'][0]['code'], 'UNSAFE_OR_OFFLINE_PATH')

    def test_permission_error_sanitized(self):
        with patch.object(cli, 'read_request', side_effect=PermissionError('RAW_SECRET_SENTINEL')):
            self.assertEqual(self.invoke()[0], 3)

    def test_interrupt_cancels(self):
        with patch.object(cli, 'confirm_scope', side_effect=KeyboardInterrupt):
            code, result, _ = self.invoke()
        self.assertEqual((code, result['status']), (3, 'cancelled'))

    def test_internal_error_sanitized(self):
        with patch.object(cli, 'read_request', side_effect=RuntimeError('RAW_SECRET_SENTINEL')):
            self.assertEqual(self.invoke()[0], 4)

    def test_library_errors_propagate_as_failure(self):
        with patch.object(cli.clash_inventory, 'audit_inventory', return_value={
                'status': 'partial', 'errors': [{'code': 'PERMISSION_DENIED'}]}):
            self.assertEqual(self.invoke()[0], 3)


class CrossPlatformCliTests(unittest.TestCase):
    def test_capabilities_offline(self):
        out = io.StringIO()
        self.assertEqual(cli.run(['capabilities'], outgoing=out), 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result['cli']['mutations'], 'unavailable')
        self.assertNotIn('windows', result)


    def test_help_uses_json_and_injected_stream(self):
        for argv in (['--help'], ['static-audit', '--help'], ['capabilities', '--help']):
            with self.subTest(argv=argv), patch.object(cli.sys, 'stdout', new_callable=io.StringIO) as global_out:
                out = io.StringIO()
                self.assertEqual(cli.run(argv, outgoing=out), 0)
                result = json.loads(out.getvalue())
                self.assertEqual(result['status'], 'help')
                self.assertIn('usage:', result['help'])
                self.assertEqual(global_out.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
