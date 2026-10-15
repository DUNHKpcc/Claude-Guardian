"""Synthetic static inventories; no real user configuration or app is touched."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/clash_inventory.py'
spec = importlib.util.spec_from_file_location('clash_inventory', SCRIPT)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class InventoryFixture:
    def setUp(self):
        platform = patch.object(c.sys, 'platform', 'darwin')
        platform.start()
        self.addCleanup(platform.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / 'config.yaml'
        self.path.write_text('mode: rule\nmixed-port: 8123\n', encoding='utf-8')
        self.req = {'schema_version': 'guardian-clash-inventory/0.1', 'operation': 'audit',
                    'target_ref': 'device-1', 'contact_phase': 'precontact', 'gate_state': 'closed',
                    'target_binding': {'target_ref': 'device-1', 'binding_state': 'bound',
                                       'declared_os': 'macos', 'execution_location': 'native_local',
                                       'desktop_user_relation': 'same', 'filesystem_namespace': 'host_desktop'},
                    'authorization': {'approved_paths': [str(self.path)], 'local_hydrated_files': True},
                    'application': {'product': 'clash-verge-rev', 'gui_version': '2.5.5', 'core_version': '1.19.0'},
                    'files': [{'source_ref': 'path-1', 'kind': 'profile', 'path': str(self.path)}]}

    def run_audit(self):
        return c.audit_inventory(self.req, 'device-1')

    def codes(self):
        return [e['code'] for e in self.run_audit()['errors']]


class ContractTests(InventoryFixture, unittest.TestCase):
    def test_missing_dependency_structured(self):
        with patch.object(c, 'yaml', None), patch.object(c, '_read') as read:
            self.assertEqual(self.codes(), ['RUNTIME_OR_PARSER_UNAVAILABLE'])
            read.assert_not_called()

    def test_os_binding_mismatch_before_read(self):
        with patch.object(c.sys, 'platform', 'linux'), patch.object(c, '_read') as read:
            self.assertIn('TARGET_USER_CONTEXT_MISMATCH', self.codes())
            read.assert_not_called()

    def test_target_mismatch_before_read(self):
        with patch.object(c, '_read') as read:
            result = c.audit_inventory(self.req, 'other-device')
            self.assertEqual(result['errors'][0]['code'], 'TARGET_NOT_BOUND')
            read.assert_not_called()

    def test_invalid_targets(self):
        for key, value in [('execution_location', 'cloud'), ('desktop_user_relation', 'different'),
                           ('filesystem_namespace', 'guest')]:
            with self.subTest(key=key):
                original = self.req['target_binding'][key]
                self.req['target_binding'][key] = value
                self.assertIn('TARGET_USER_CONTEXT_MISMATCH', self.codes())
                self.req['target_binding'][key] = original

    def test_unapproved_path_entire_request_rejected(self):
        self.req['files'].append({'source_ref': 'path-2', 'kind': 'profile', 'path': str(self.root / 'other.yaml')})
        with patch.object(c, '_read') as read:
            self.assertIn('AUTHORIZATION_MISSING', self.codes())
            read.assert_not_called()

    def test_unsupported_versions(self):
        for field, value in [('product', 'clash-verge'), ('gui_version', '99.1.0'), ('core_version', 'unknown')]:
            original = self.req['application'][field]
            self.req['application'][field] = value
            with patch.object(c, '_read') as read:
                self.assertIn('UNSUPPORTED_PRODUCT_OR_VERSION', self.codes())
                read.assert_not_called()
            self.req['application'][field] = original

    def test_cancellation_prevents_reads(self):
        with patch.object(c, '_read') as read:
            result = c.audit_inventory(self.req, 'device-1', cancel_check=lambda: True)
            self.assertEqual(result['errors'][0]['code'], 'USER_CANCELLED')
            read.assert_not_called()

    def test_callback_errors_never_escape_or_echo(self):
        for error in (RuntimeError('SECRET-SENTINEL'), c.InventoryError('SECRET-SENTINEL')):
            def callback():
                raise error
            result = c.audit_inventory(self.req, 'device-1', cancel_check=callback)
            self.assertEqual(result['errors'], [{'code': 'INVENTORY_CALLBACK_FAILED'}])
            self.assertNotIn('SECRET-SENTINEL', json.dumps(result))
            self.assertEqual(result['snapshot']['state'], 'unknown')

    def test_public_error_codes_are_allowlisted(self):
        self.assertEqual(c.InventoryError('SECRET-SENTINEL').code, 'INPUT_OR_RESPONSE_INVALID')
        self.assertEqual(c.InventoryError(['SECRET-SENTINEL']).code, 'INPUT_OR_RESPONSE_INVALID')

    def test_expired_budget_prevents_reads(self):
        with patch.object(c, 'MAX_SECONDS', 0), patch.object(c, '_read') as read:
            self.assertIn('BUDGET_EXCEEDED', self.codes())
            read.assert_not_called()

    def test_injected_actions_refused(self):
        for key, value in [('command', 'secret-sentinel'), ('url_to_test', 'secret-sentinel')]:
            self.req[key] = value
            self.assertIn('INPUT_OR_RESPONSE_INVALID', self.codes())
            del self.req[key]
        self.req['operation'] = 'apply'
        self.assertIn('PRECONTACT_ACTION_REJECTED', self.codes())

    def test_nonlocal_material_requires_authorization(self):
        self.req['authorization']['local_hydrated_files'] = False
        self.assertIn('AUTHORIZATION_MISSING', self.codes())

    def test_bad_paths(self):
        for path in ['//server/config.yaml', '../config.yaml', '/tmp/../config.yaml']:
            self.req['files'][0]['path'] = path
            self.assertIn('UNSAFE_OR_OFFLINE_PATH', self.codes())

    def test_malformed_input_never_echoes(self):
        for request in [None, [], {'SECRET-SENTINEL': 'PASSWORD'}, dict(self.req, application={'product': []})]:
            result = c.audit_inventory(request, 'device-1')
            self.assertTrue(result['errors'])
            self.assertNotIn('SECRET-SENTINEL', json.dumps(result))


@unittest.skipIf(c.yaml is None, 'Optional PyYAML unavailable; missing dependency is separately tested')
class MockedReadTests(InventoryFixture, unittest.TestCase):
    """Platform-independent parser/control tests; all target reads are synthetic."""
    def test_cancellation_after_reads_and_before_return(self):
        for stage in (3, 6, 8):
            with self.subTest(check=stage):
                count = 0
                def callback():
                    nonlocal count
                    count += 1
                    return count >= stage
                with patch.object(c, '_read', return_value=(b'mode: rule', ('fixture', b'revision'))):
                    result = c.audit_inventory(self.req, 'device-1', cancel_check=callback)
                self.assertEqual(result['errors'][-1]['code'], 'USER_CANCELLED')
                self.assertEqual(result['snapshot']['state'], 'unknown')

    def test_budget_after_reads_and_before_return(self):
        for stage in (3, 6, 8):
            with self.subTest(check=stage):
                clock = [0]
                count = 0
                def callback():
                    nonlocal count
                    count += 1
                    if count >= stage:
                        clock[0] = c.MAX_SECONDS + 1
                    return False
                with patch.object(c, '_read', return_value=(b'mode: rule', ('fixture', b'revision'))):
                    with patch.object(c.time, 'monotonic', side_effect=lambda: clock[0]):
                        result = c.audit_inventory(self.req, 'device-1', cancel_check=callback)
                self.assertEqual(result['errors'][-1]['code'], 'BUDGET_EXCEEDED')
                self.assertEqual(result['snapshot']['state'], 'unknown')

    def test_callback_exception_after_final_read_is_sanitized(self):
        for error in (RuntimeError('SECRET-SENTINEL'), c.InventoryError('SECRET-SENTINEL')):
            count = 0
            def callback():
                nonlocal count
                count += 1
                if count >= 6:
                    raise error
                return False
            with patch.object(c, '_read', return_value=(b'mode: rule', ('fixture', b'revision'))):
                result = c.audit_inventory(self.req, 'device-1', cancel_check=callback)
            self.assertEqual(result['errors'][-1]['code'], 'INVENTORY_CALLBACK_FAILED')
            self.assertNotIn('SECRET-SENTINEL', json.dumps(result))
            self.assertEqual(result['snapshot']['state'], 'unknown')

    def test_schema_fixture_labels_not_compatibility_claim(self):
        with patch.object(c, '_read', return_value=(b'mode: rule', ('fixture', b'revision'))):
            result = self.run_audit()
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['application']['version_scope'], 'synthetic_schema_fixture_only')
        self.assertEqual(result['application']['native_compatibility'], 'not_validated')
        self.assertEqual(result['files'][0]['values']['mode']['value'], 'rule')


@unittest.skipIf(c.yaml is None, 'Optional PyYAML unavailable; missing dependency is separately tested')
@unittest.skipUnless(os.name == 'posix', 'Secure POSIX read tests; Windows is explicitly unsupported')
class ParsingTests(InventoryFixture, unittest.TestCase):
    def write(self, text):
        self.path.write_text(text, encoding='utf-8')

    def test_minimal_static_result_missing_is_unknown(self):
        result = self.run_audit()
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['snapshot']['state'], 'stable_observed_subset')
        self.assertEqual(result['runtime']['state'], 'unknown')
        entry = result['files'][0]
        self.assertEqual(entry['layer'], 'file_declared')
        self.assertEqual(entry['values']['mode']['value'], 'rule')
        self.assertEqual(entry['values']['tun']['enable'], {'state': 'unknown', 'value': None})
        self.assertEqual(result['changes'], [])
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertNotIn('sha256', json.dumps(result))

    def test_secrets_addresses_and_names_never_output(self):
        self.write('''mode: rule
secret: SECRET-SENTINEL
subscription: https://SECRET-SENTINEL.invalid/token
bind-address: 203.0.113.77
proxy-groups:
 - name: SECRET-SENTINEL
   type: select
   proxies: [DIRECT, SECRET-SENTINEL]
proxies:
 - name: SECRET-SENTINEL
   password: SECRET-SENTINEL
   server: 203.0.113.77
rules:
 - DOMAIN,SECRET-SENTINEL.invalid,SECRET-SENTINEL
unknown: SECRET-SENTINEL
''')
        result = self.run_audit()
        self.assertEqual(result['errors'], [])
        encoded = json.dumps(result)
        self.assertNotIn('SECRET-SENTINEL', encoded)
        self.assertNotIn('203.0.113.77', encoded)
        group = result['files'][0]['values']['groups']['value'][0]
        self.assertEqual(group['group_ref'], 'group-1')
        self.assertTrue(group['direct_candidate']['value'])
        self.assertIsNone(group['runtime_selection']['value'])

    def test_duplicate_documents_aliases_tags_rejected(self):
        for text in ['mode: rule\nmode: global', 'dns: {enable: true, enable: false}',
                     'mode: rule\n---\nmode: global', 'x: &a [1]\ny: *a',
                     'x: &a [*a]', 'x: !!python/object/apply:os.system [evil]',
                     'x: !!str secret', '<<: {mode: rule}', '[1,2]', 'mode: [unclosed']:
            with self.subTest(text=text):
                self.write(text)
                result = self.run_audit()
                self.assertEqual(result['files'], [])
                self.assertIn('INPUT_OR_RESPONSE_INVALID', [e['code'] for e in result['errors']])

    def test_bounds(self):
        for text, limits in [('x: ' + '[' * 10 + '0' + ']' * 10, {'MAX_DEPTH': 5}),
                             ('x: [1,2,3,4,5]', {'MAX_NODES': 4}),
                             ('x: ' + 'a' * 100, {'MAX_BYTES': 50})]:
            self.write(text)
            with patch.multiple(c, **limits):
                self.assertIn('BUDGET_EXCEEDED', self.codes())
        self.req['files'] *= 33
        self.assertIn('BUDGET_EXCEEDED', self.codes())

    def test_invalid_utf8(self):
        self.path.write_bytes(b'mode: \xffSECRET-SENTINEL')
        result = self.run_audit()
        self.assertIn('INPUT_OR_RESPONSE_INVALID', [e['code'] for e in result['errors']])
        self.assertNotIn('SECRET-SENTINEL', json.dumps(result))

    def test_typed_values_not_coerced(self):
        self.write('mixed-port: true\nallow-lan: "false"\nmode: SECRET-SENTINEL\ntun: {enable: true}\ndns: {ipv6: false}')
        values = self.run_audit()['files'][0]['values']
        self.assertEqual(values['mixed-port']['state'], 'unknown')
        self.assertEqual(values['allow-lan']['state'], 'unknown')
        self.assertEqual(values['mode']['state'], 'unknown')
        self.assertTrue(values['tun']['enable']['value'])
        self.assertFalse(values['dns']['ipv6']['value'])

    def test_gui_settings_separate_layer(self):
        self.write('enable_system_proxy: true\nenable_tun_mode: false\nmode: global')
        self.req['files'][0]['kind'] = 'gui_settings'
        entry = self.run_audit()['files'][0]
        self.assertEqual(entry['layer'], 'gui_declared')
        self.assertTrue(entry['values']['enable_system_proxy']['value'])
        self.assertNotIn('mode', entry['values'])

    def test_conflicts_preserve_layers(self):
        second = self.root / 'generated.yaml'
        second.write_text('mode: global\nmixed-port: 9234')
        self.req['authorization']['approved_paths'].append(str(second))
        self.req['files'].append({'source_ref': 'path-2', 'kind': 'generated_config', 'path': str(second)})
        result = self.run_audit()
        self.assertEqual({c['field'] for c in result['conflicts']}, {'mode', 'mixed-port'})
        self.assertTrue(all(f['layer'] == 'file_declared' for f in result['files']))
        self.assertEqual(result['runtime']['state'], 'unknown')

    def test_snapshot_change_discards_freshness(self):
        original = c._read
        reads = 0
        def changed(path):
            nonlocal reads
            reads += 1
            if reads == 2:
                self.write('mode: global')
            return original(path)
        with patch.object(c, '_read', changed):
            result = self.run_audit()
        self.assertEqual(result['snapshot']['state'], 'changed')
        self.assertEqual(result['files'][0]['state'], 'stale')
        self.assertIn('SNAPSHOT_CHANGED_DURING_AUDIT', [e['code'] for e in result['errors']])

    def test_replacement_with_identical_bytes_is_change(self):
        original = c._read
        reads = 0
        def replaced(path):
            nonlocal reads
            reads += 1
            if reads == 2:
                replacement = self.root / 'replacement.yaml'
                replacement.write_bytes(self.path.read_bytes())
                replacement.replace(self.path)
            return original(path)
        with patch.object(c, '_read', replaced):
            result = self.run_audit()
        self.assertEqual(result['snapshot']['state'], 'changed')
        self.assertEqual(result['files'][0]['state'], 'stale')

    def test_audit_does_not_modify_config(self):
        before = self.path.read_bytes()
        before_stat = self.path.stat()
        self.run_audit()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.path.stat().st_mtime_ns, before_stat.st_mtime_ns)

    def test_parser_cooperative_cancellation(self):
        self.write('values: [' + ','.join('0' for _ in range(100)) + ']')
        count = 0
        def cancel():
            nonlocal count
            count += 1
            return count >= 3
        result = c.audit_inventory(self.req, 'device-1', cancel_check=cancel)
        self.assertIn('USER_CANCELLED', [e['code'] for e in result['errors']])
        self.assertEqual(result['snapshot']['state'], 'unknown')

    def test_revisions_opaque_and_session_local(self):
        first, second = self.run_audit(), self.run_audit()
        self.assertNotEqual(first['files'][0]['source_revision'], second['files'][0]['source_revision'])
        self.assertEqual(first['files'][0]['source_ref'], second['files'][0]['source_ref'])

    def test_symlink_file_and_parent_rejected(self):
        actual = self.root / 'actual.yaml'
        self.path.rename(actual)
        self.path.symlink_to(actual)
        self.assertIn('UNSAFE_OR_OFFLINE_PATH', self.codes())
        self.path.unlink()
        folder = self.root / 'folder'
        folder.mkdir()
        actual.rename(folder / 'config.yaml')
        link = self.root / 'link'
        link.symlink_to(folder, target_is_directory=True)
        linked = str(link / 'config.yaml')
        self.req['files'][0]['path'] = linked
        self.req['authorization']['approved_paths'] = [linked]
        self.assertIn('UNSAFE_OR_OFFLINE_PATH', self.codes())

    def test_hardlink_directory_and_missing_rejected(self):
        other = self.root / 'hardlink'
        os.link(self.path, other)
        self.assertIn('UNSAFE_OR_OFFLINE_PATH', self.codes())
        other.unlink()
        self.path.unlink()
        self.assertIn('FILE_NOT_FOUND_IN_APPROVED_SCOPE', self.codes())
        self.path.mkdir()
        self.assertIn('UNSAFE_OR_OFFLINE_PATH', self.codes())

    def test_permission_denied_no_exception_echo(self):
        with patch.object(c.os, 'open', side_effect=PermissionError('SECRET-SENTINEL')) as opened:
            with patch.object(c.os, 'supports_dir_fd', {opened}):
                result = self.run_audit()
        self.assertIn('PERMISSION_DENIED', [e['code'] for e in result['errors']])
        self.assertNotIn('SECRET-SENTINEL', json.dumps(result))

    def test_windows_read_is_explicitly_unsupported(self):
        with patch.object(c.os, 'name', 'nt'):
            with self.assertRaisesRegex(c.InventoryError, 'HOST_CAPABILITY_UNAVAILABLE'):
                c._read(self.path)


if __name__ == '__main__':
    unittest.main()
