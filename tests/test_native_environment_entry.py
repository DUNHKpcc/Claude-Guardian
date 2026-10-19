"""Synthetic entry wiring. No native acceptance, real device or network I/O."""
from contextlib import ExitStack, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path, PureWindowsPath
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import diagnostic_session as session
import environment_entry as entry
import guardian
import inventory_cli as inventory
import network_probes as probes


def entry_request(target='target', route='local', *, available=True):
    roles = {'local': ['local'], 'vm': ['vm_host', 'vm_guest'], 'vps': ['vps']}[route]
    request = {
        'schema_version': entry.SCHEMA,
        'route': {'choice': route, 'state': 'selected'},
        'targets': [{'role': role, 'target_ref': target if i == 0 else 'guest'}
                    for i, role in enumerate(roles)],
        'network': {'possession': 'present', 'selection': 'selected',
                    'configuration': 'effective', 'path': 'explicit',
                    'resource_ref': 'resource-a'},
        'local_entry': {'kind': 'mixed', 'entry_ref': 'entry-a'},
        'final_egress': {'kind': 'proxy', 'protocol': 'socks5'},
        'client': 'claude_code',
    }
    if not available:
        request['network'] = {'possession': 'none', 'selection': 'unknown',
                              'configuration': 'absent', 'path': 'unknown'}
        request['local_entry'] = {'kind': 'unknown'}
        request['final_egress'] = {'kind': 'unknown', 'protocol': 'unknown'}
    return request


def denied_requests():
    withdrawn = entry_request()
    withdrawn['route']['state'] = 'withdrawn'
    unasked = entry_request()
    unasked['route']['state'] = 'unasked'
    return [None, withdrawn, unasked, entry_request('other-target')]


def args(**kwargs):
    return SimpleNamespace(**dict(dict(target_ref='target', target_os='macos',
        target_kind='local', namespace='desktop', execution_location='native_local',
        user_context='same', confirm_target=True, authorize_audit=True), **kwargs))


class NativeEntryTests(unittest.TestCase):
    def test_missing_withdrawn_unasked_and_mismatch_no_target_reads(self):
        for request in denied_requests():
            with self.subTest(request=request), patch.object(guardian.os, 'uname', create=True) as uname, \
                    patch.object(guardian, 'extended_inventory') as collect, \
                    patch.object(guardian.time, 'localtime') as localtime:
                with self.assertRaises(guardian.GuardianError) as caught:
                    guardian.native_check(args(), entry_request=request)
                self.assertIn(caught.exception.code, {'E_OBJECT_SHAPE', 'E_ENTRY_BLOCKED'})
                uname.assert_not_called()
                collect.assert_not_called()
                localtime.assert_not_called()

    def test_eligible_entry_never_grants_old_authorization(self):
        with patch.object(guardian, 'extended_inventory') as collect:
            with self.assertRaises(guardian.GuardianError) as caught:
                guardian.native_check(args(authorize_audit=False), entry_request=entry_request())
        self.assertEqual(caught.exception.code, 'AUTHORIZATION_MISSING')
        collect.assert_not_called()

    def test_eligible_entry_never_changes_native_context_support(self):
        for change in ({'confirm_target': False}, {'namespace': 'sandbox'},
                       {'execution_location': 'cloud'}, {'user_context': 'different'}):
            with self.subTest(change=change), patch.object(guardian.sys, 'platform', 'darwin'), \
                    patch.object(guardian, 'extended_inventory') as collect:
                with self.assertRaises(guardian.GuardianError):
                    guardian.native_check(args(**change), entry_request=entry_request())
                collect.assert_not_called()

    def test_missing_resources_allow_only_authorized_offline_metadata(self):
        with patch.object(guardian.sys, 'platform', 'darwin'), \
                patch.object(guardian.os, 'uname', return_value=SimpleNamespace(release='fixture-kernel'), create=True), \
                patch.object(guardian.time, 'localtime', return_value=SimpleNamespace(tm_gmtoff=0)), \
                patch.object(guardian, 'extended_inventory', return_value=([], [])) as collect:
            result = guardian.native_check(args(), entry_request=entry_request(available=False))
        self.assertEqual(result['record_kind'], 'device_observation')
        collect.assert_called_once_with('macos')

    def test_synthetic_native_checks_work_without_host_uname(self):
        # Replace only guardian's module reference; never remove a real OS API.
        host_without_uname = SimpleNamespace()
        with patch.object(guardian, 'os', host_without_uname):
            self.test_missing_withdrawn_unasked_and_mismatch_no_target_reads()
            self.test_missing_resources_allow_only_authorized_offline_metadata()
        self.assertFalse(hasattr(host_without_uname, 'uname'))

    def test_vm_vps_selection_does_not_create_native_adapter(self):
        for route in ('vm', 'vps'):
            with self.subTest(route=route), patch.object(guardian, 'extended_inventory') as collect:
                with self.assertRaises(guardian.GuardianError) as caught:
                    guardian.native_check(args(), entry_request=entry_request(route=route))
                self.assertEqual(caught.exception.code, 'TARGET_USER_CONTEXT_MISMATCH')
                collect.assert_not_called()

    def test_check_cli_missing_entry_is_fail_closed(self):
        with redirect_stdout(io.StringIO()) as out, patch.object(guardian, 'extended_inventory') as collect:
            code = guardian.main(['check', '--target-ref', 'target', '--target-os', 'macos',
                '--confirm-target', '--authorize-audit'])
        self.assertEqual(code, 3)
        self.assertIn('E_OBJECT_SHAPE', out.getvalue())
        collect.assert_not_called()

    def test_pure_help_and_interview_have_no_entry_gate(self):
        with patch.object(guardian.environment_entry, 'require_entry', side_effect=AssertionError) as gate:
            self.assertEqual(guardian.interview({})['operation'], 'interview')
            with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as done:
                guardian.main(['check', '--help'])
        self.assertEqual(done.exception.code, 0)
        gate.assert_not_called()


class SessionEntryTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(session.sys, 'platform', 'darwin'))
        self.capture = self.stack.enter_context(patch.object(session.native_context,
            'capture_current_context', return_value=object()))
        self.stack.enter_context(patch.object(session.native_context, 'recheck_context', return_value={}))
        self.stack.enter_context(patch.object(session.native_context, 'describe_context', return_value={}))
        self.child = self.stack.enter_context(patch.object(session.os_dns_probe,
            '_run_child', return_value=b'["192.0.2.1"]'))
        self.consent = Mock(return_value=True)

    def test_missing_withdrawn_unasked_mismatch_no_callback_or_target_io(self):
        for request in denied_requests():
            with self.subTest(request=request):
                result = session.execute('target', consent=self.consent, entry_request=request)
                self.assertEqual(result['status'], 'blocked')
                self.assertIn(result['errors'][0], {'E_OBJECT_SHAPE', 'E_ENTRY_BLOCKED'})
        self.consent.assert_not_called()
        self.capture.assert_not_called()
        self.child.assert_not_called()

    def test_eligible_entry_still_needs_consent(self):
        self.consent.return_value = False
        result = session.execute('target', consent=self.consent, entry_request=entry_request())
        self.assertEqual(result['errors'], ['DECLINED'])
        self.capture.assert_not_called()

    def test_resource_absence_allows_metadata_but_not_dns(self):
        result = session.execute('target', consent=self.consent,
            queries=[('reserved.test', 'A')], entry_request=entry_request(available=False))
        self.assertEqual(result['errors'], ['E_ENTRY_BLOCKED'])
        self.assertEqual(self.capture.call_count, 1)
        self.assertEqual(self.consent.call_count, 1)
        self.child.assert_not_called()

    def test_same_eligibility_resource_alias_mutation_during_consent_is_rejected(self):
        request = entry_request()
        def approve(scope):
            request['network']['resource_ref'] = 'resource-b'
            return True
        result = session.execute('target', consent=approve, entry_request=request)
        self.assertEqual(result['errors'], ['ENTRY_CHANGED'])
        self.capture.assert_not_called()
        self.child.assert_not_called()

    def test_withdrawal_during_consent_is_rejected_before_capture(self):
        request = entry_request()
        def approve(scope):
            request['route']['state'] = 'withdrawn'
            return True
        result = session.execute('target', consent=approve, entry_request=request)
        self.assertEqual(result['errors'], ['E_ENTRY_BLOCKED'])
        self.capture.assert_not_called()

    def test_dns_approval_cannot_change_resource_before_transport(self):
        request = entry_request()
        binding = session.os_dns_probe.Binding('target', 'user', 'namespace', 'darwin',
                                               '/trusted/python', '/trusted')
        host = session.DNSHost(binding, Mock(return_value=True), Mock(return_value=True), Mock(return_value=True))
        def approve(scope):
            if scope['operation'] == 'system_dns_query':
                request['network']['resource_ref'] = 'resource-b'
            return True
        result = session.execute('target', consent=approve, dns_host=host,
            queries=[('reserved.test', 'A')], entry_request=request)
        self.assertEqual(result['errors'], ['ENTRY_CHANGED'])
        self.assertEqual(result['report']['facts'][0]['state'], 'stale')
        self.child.assert_not_called()

    def test_cancellation_callback_cannot_replace_validated_resource(self):
        request = entry_request()
        def cancelled():
            request['network']['resource_ref'] = 'resource-b'
            return False
        result = session.execute('target', consent=self.consent, cancelled=cancelled,
                                 entry_request=request)
        self.assertEqual(result['errors'], ['ENTRY_CHANGED'])
        self.consent.assert_not_called()
        self.capture.assert_not_called()

    def test_windows_trusted_host_dict_remains_available_without_file_reader(self):
        with patch.object(session.sys, 'platform', 'win32'), \
                patch.object(session.windows_native_context, 'capture_current_context', return_value=object()) as capture, \
                patch.object(session.windows_native_context, 'recheck_context', return_value={}), \
                patch.object(session.windows_native_context, 'describe_context', return_value={}), \
                patch.object(inventory, 'read_request', side_effect=AssertionError):
            result = session.execute('target', consent=self.consent, entry_request=entry_request())
        self.assertEqual(result['status'], 'partial')
        capture.assert_called_once()
        self.capture.assert_not_called()
        self.child.assert_not_called()

    def test_cli_host_dict_does_not_read_file_or_reuse_stdin(self):
        out = io.StringIO()
        with patch.object(session, 'TerminalConsent', return_value=self.consent), \
                patch.object(inventory, 'read_request', side_effect=AssertionError):
            code = session.run(['--target-ref', 'target'], entry_request=entry_request(), outgoing=out)
        self.assertEqual(code, 0)
        self.assertEqual(self.capture.call_count, 1)

    def test_cli_help_does_not_read_entry_or_capture(self):
        out = io.StringIO()
        with patch.object(inventory, 'read_request', side_effect=AssertionError):
            self.assertEqual(session.run(['--help'], outgoing=out), 0)
        self.assertEqual(json.loads(out.getvalue())['status'], 'help')
        self.capture.assert_not_called()


class InventoryEntryTests(unittest.TestCase):
    def setUp(self):
        # Host-valid syntax only. read_request and audit_inventory remain mocked.
        self.fixture_root = (Path(tempfile.gettempdir()) / 'guardian-entry-fixture').resolve()

    def request(self):
        return {'schema_version': 'guardian-static-cli-request/2', 'target_ref': 'target',
                'entry_request': entry_request(),
                'target_binding': {'target_ref': 'target', 'binding_state': 'bound',
                    'declared_os': 'macos', 'execution_location': 'native_local',
                    'desktop_user_relation': 'same', 'filesystem_namespace': 'host_desktop'},
                'application': {'product': 'clash-verge-rev', 'gui_version': '2.5.5', 'core_version': '1.19.0'},
                'files': [{'source_ref': 'profile', 'kind': 'profile',
                           'path': str(self.fixture_root / 'config.yaml')}]}

    def invoke(self, request, *, confirm=None):
        out = io.StringIO()
        with patch.object(inventory.sys, 'platform', 'darwin'), \
                patch.object(inventory, 'read_request', return_value=request), \
                patch.object(inventory, 'confirm_scope', side_effect=confirm) as consent, \
                patch.object(inventory.clash_inventory, 'audit_inventory',
                             return_value={'errors': [], 'status': 'partial'}) as audit:
            code = inventory.run(['static-audit', '--request', str(self.fixture_root / 'request.json'),
                                  '--target-ref', 'target'], outgoing=out)
        return code, json.loads(out.getvalue()), consent, audit

    def test_missing_withdrawn_unasked_mismatch_before_consent_and_target_reads(self):
        for value in denied_requests():
            with self.subTest(value=value):
                request = self.request()
                request['entry_request'] = value
                code, result, consent, audit = self.invoke(request)
                self.assertEqual(code, 2)
                self.assertIn(result['error_code'], {'E_OBJECT_SHAPE', 'E_ENTRY_BLOCKED'})
                consent.assert_not_called()
                audit.assert_not_called()

    def test_legacy_envelope_is_not_silently_upgraded(self):
        request = self.request()
        request['schema_version'] = 'guardian-static-cli-request/1'
        del request['entry_request']
        code, result, consent, audit = self.invoke(request)
        self.assertEqual(result['error_code'], 'INPUT_OR_RESPONSE_INVALID')
        consent.assert_not_called()
        audit.assert_not_called()

    def test_valid_entry_is_removed_before_strict_library_schema(self):
        request = self.request()
        request['entry_request'] = entry_request(available=False)
        code, result, consent, audit = self.invoke(request)
        self.assertEqual(code, 0)
        consent.assert_called_once()
        forwarded = audit.call_args.args[0]
        self.assertNotIn('entry_request', forwarded)
        self.assertEqual(forwarded['schema_version'], 'guardian-clash-inventory/0.1')
        self.assertEqual(forwarded['authorization']['approved_paths'],
                         [str(self.fixture_root / 'config.yaml')])

    def test_entry_cannot_replace_original_context_gate(self):
        request = self.request()
        request['target_binding']['execution_location'] = 'cloud'
        code, result, consent, audit = self.invoke(request)
        self.assertEqual(result['error_code'], 'TARGET_USER_CONTEXT_MISMATCH')
        consent.assert_not_called()
        audit.assert_not_called()

    def test_confirmation_cannot_change_same_eligibility_resource_alias(self):
        request = self.request()
        def change(*_):
            request['entry_request']['network']['resource_ref'] = 'resource-b'
        code, result, consent, audit = self.invoke(request, confirm=change)
        self.assertEqual(result['error_code'], 'ENTRY_CHANGED')
        audit.assert_not_called()

    def test_original_terminal_consent_stays_required(self):
        out = io.StringIO()
        with patch.object(inventory.sys, 'platform', 'darwin'), \
                patch.object(inventory, 'read_request', return_value=self.request()), \
                patch.object(inventory.clash_inventory, 'audit_inventory') as audit:
            code = inventory.run(['static-audit', '--request', str(self.fixture_root / 'request.json'),
                                  '--target-ref', 'target'],
                incoming=io.StringIO('READ\n'), outgoing=out, prompt=io.StringIO())
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out.getvalue())['error_code'], 'LIVE_TERMINAL_REQUIRED')
        audit.assert_not_called()

    def test_synthetic_inventory_checks_keep_windows_path_rules(self):
        # Exercise the same assertions with Windows path grammar on any CI host.
        # The real _path validator stays active, including its rejection branch.
        self.fixture_root = PureWindowsPath('C:/guardian-entry-fixture')
        with patch.object(inventory, 'Path', PureWindowsPath):
            with self.assertRaises(inventory.InputError) as caught:
                inventory._path('/fixture/config.yaml')
            self.assertEqual(caught.exception.code, 'UNSAFE_OR_OFFLINE_PATH')
            self.test_valid_entry_is_removed_before_strict_library_schema()
            self.test_confirmation_cannot_change_same_eligibility_resource_alias()
            self.test_original_terminal_consent_stays_required()

    def test_pure_capabilities_and_help_need_no_entry(self):
        for argv in (['capabilities'], ['workflow-status'], ['--help']):
            with self.subTest(argv=argv), patch.object(inventory, 'read_request', side_effect=AssertionError):
                self.assertEqual(inventory.run(argv, outgoing=io.StringIO()), 0)


class ProbeEntryTests(unittest.TestCase):
    def probe(self, request, **overrides):
        options = dict(approved_endpoints=[probes.ENDPOINTS['ipify_v4'][0]],
            approved_paths=['explicit_proxy'], target_ref='target', path_kind='explicit_proxy',
            transport=self.transport, entry_request=request)
        options.update(overrides)
        return probes.probe_https_ip('ipify_v4', **options)

    def setUp(self):
        self.transport = Mock(path_kind='explicit_proxy')
        self.transport.request.return_value = probes.Response(200, b'{"ip":"8.8.8.8"}')

    def test_missing_withdrawn_unasked_mismatch_never_constructs_or_calls_transport(self):
        for request in denied_requests():
            with self.subTest(request=request), patch.object(probes, 'SystemRouteTransport') as constructor:
                with self.assertRaises(probes.ProbeError) as caught:
                    self.probe(request, transport=None)
                self.assertIn(str(caught.exception), {'E_OBJECT_SHAPE', 'E_ENTRY_BLOCKED'})
                constructor.assert_not_called()
        self.transport.request.assert_not_called()

    def test_network_resource_absence_blocks_even_with_route_and_endpoint_approval(self):
        with self.assertRaisesRegex(probes.ProbeError, '^E_ENTRY_BLOCKED$'):
            self.probe(entry_request(available=False))
        self.transport.request.assert_not_called()

    def test_entry_never_grants_endpoint_or_path_consent(self):
        for override, code in (({'approved_endpoints': []}, 'exact_endpoint_consent_required'),
                               ({'approved_paths': []}, 'explicit_path_consent_required')):
            with self.subTest(override=override), self.assertRaisesRegex(probes.ProbeError, '^' + code + '$'):
                self.probe(entry_request(), **override)
        self.transport.request.assert_not_called()

    def test_current_entry_and_old_gates_allow_one_mock_transport(self):
        result = self.probe(entry_request())
        self.assertEqual(result['status'], 'observed')
        self.transport.request.assert_called_once()

    def test_adapter_property_cannot_switch_resource_after_validation(self):
        request = entry_request()
        transport = self.transport
        class MutatingAdapter:
            @property
            def path_kind(self):
                request['network']['resource_ref'] = 'resource-b'
                return 'explicit_proxy'
            request = transport.request
        with self.assertRaisesRegex(probes.ProbeError, '^ENTRY_CHANGED$'):
            self.probe(request, transport=MutatingAdapter())
        self.transport.request.assert_not_called()


    def test_request_getter_cannot_withdraw_route_before_transport(self):
        request = entry_request()
        transport = self.transport
        lookups = []
        class MutatingRequestAdapter:
            path_kind = 'explicit_proxy'
            @property
            def request(self):
                lookups.append('request')
                request['route']['state'] = 'withdrawn'
                return transport.request
        with self.assertRaisesRegex(probes.ProbeError, '^E_ENTRY_BLOCKED$'):
            self.probe(request, transport=MutatingRequestAdapter())
        self.assertEqual(lookups, ['request'])
        self.transport.request.assert_not_called()

    def test_request_getter_cannot_replace_same_eligibility_resource_before_transport(self):
        request = entry_request()
        transport = self.transport
        lookups = []
        class MutatingRequestAdapter:
            path_kind = 'explicit_proxy'
            @property
            def request(self):
                lookups.append('request')
                request['network']['resource_ref'] = 'resource-b'
                return transport.request
        with self.assertRaisesRegex(probes.ProbeError, '^ENTRY_CHANGED$'):
            self.probe(request, transport=MutatingRequestAdapter())
        self.assertEqual(lookups, ['request'])
        self.transport.request.assert_not_called()

    def test_request_getter_is_bound_once_and_does_not_echo_errors(self):
        transport = self.transport
        lookups = []
        class StableRequestAdapter:
            path_kind = 'explicit_proxy'
            @property
            def request(self):
                lookups.append('request')
                if len(lookups) != 1:
                    raise RuntimeError('synthetic-private-getter-error')
                return transport.request
        self.assertEqual(self.probe(entry_request(), transport=StableRequestAdapter())['status'], 'observed')
        self.assertEqual(lookups, ['request'])
        transport.request.assert_called_once()

        class BrokenRequestAdapter:
            path_kind = 'explicit_proxy'
            @property
            def request(self):
                raise RuntimeError('synthetic-private-getter-error')
        class BrokenPathAdapter:
            @property
            def path_kind(self):
                raise RuntimeError('synthetic-private-getter-error')
            request = transport.request
        for adapter in (BrokenRequestAdapter(), BrokenPathAdapter()):
            with self.subTest(adapter=type(adapter).__name__):
                with self.assertRaisesRegex(probes.ProbeError, '^transport_error$'):
                    self.probe(entry_request(), transport=adapter)
        # No second request follows either malformed getter.
        transport.request.assert_called_once()


class EntryFileReaderTests(unittest.TestCase):
    def test_standalone_file_path_imports_do_not_need_scripts_on_sys_path(self):
        for filename in ('guardian.py', 'network_probes.py'):
            with self.subTest(filename=filename), patch.dict(sys.modules, {'environment_entry': None}):
                spec = importlib.util.spec_from_file_location('standalone_entry_test', SCRIPTS / filename)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                with self.assertRaises(module.environment_entry.InvalidProjection):
                    module.environment_entry.require_entry(None, 'offline_precheck', 'target')

    @unittest.skipUnless(os.name == 'posix', 'POSIX request-reader fixtures')
    def test_cli_entry_files_use_safe_reader_and_never_guardian_load_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            path = root / 'entry.json'
            path.write_text(json.dumps(entry_request()), encoding='utf-8')
            with patch.object(guardian, 'load_json', side_effect=AssertionError), \
                    patch.object(guardian, 'native_check', return_value=guardian.base('audit')) as native, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(guardian.main(['check', '--target-ref', 'target', '--target-os', 'macos',
                                                '--entry-file', str(path)]), 0)
            self.assertEqual(native.call_args.kwargs['entry_request'], entry_request())
            with patch.object(session, 'execute', return_value={'status': 'partial', 'dashboard_html': ''}) as execute:
                self.assertEqual(session.run(['--target-ref', 'target', '--entry-file', str(path)],
                                             outgoing=io.StringIO()), 0)
            self.assertEqual(execute.call_args.kwargs['entry_request'], entry_request())

    @unittest.skipUnless(os.name == 'posix', 'POSIX request-reader fixtures')
    def test_linked_or_oversize_entry_file_cannot_reach_native_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            path = root / 'entry.json'
            path.write_text(json.dumps(entry_request()), encoding='utf-8')
            link = root / 'link.json'
            link.symlink_to(path)
            huge = root / 'huge.json'
            huge.write_bytes(b' ' * (inventory.MAX_REQUEST_BYTES + 1))
            for filename in (link, huge):
                with self.subTest(filename=filename), patch.object(guardian, 'native_check') as native, \
                        redirect_stdout(io.StringIO()):
                    self.assertNotEqual(guardian.main(['check', '--target-ref', 'target', '--target-os', 'macos',
                                                       '--entry-file', str(filename)]), 0)
                native.assert_not_called()

    def test_windows_entry_file_reader_explicitly_unsupported(self):
        with patch.object(inventory.os, 'name', 'nt'), patch.object(inventory.os, 'open') as opened:
            with self.assertRaises(inventory.InputError) as caught:
                inventory.read_request('C:\\entry.json')
        self.assertEqual(caught.exception.code, 'HOST_CAPABILITY_UNAVAILABLE')
        opened.assert_not_called()


if __name__ == '__main__':
    unittest.main()
