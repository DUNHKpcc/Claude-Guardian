"""Synthetic neutral-probe contracts, never native acceptance or live consent."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import environment_entry as entry
import network_probes as probes
from test_environment_entry import fixture
import test_workflow_environment_entry as workflow_fixtures
w = workflow_fixtures.w

PATH = 'direct_socket_os_route_tun_unknown'


def neutral_request(target='target-local'):
    request = fixture()
    request['schema_version'] = 'guardian-environment-entry-input/0.2'
    request['targets'][0]['target_ref'] = target
    request['network'] = dict(possession='unknown', selection='unknown',
                              configuration='unknown', path='unknown')
    request['local_entry'] = {'kind': 'unknown'}
    request['final_egress'] = {'kind': 'unknown', 'protocol': 'unknown'}
    request['client'] = 'unknown'
    request['probe_context'] = {
        'schema_version': 'guardian-probe-context/0.1',
        'executor': 'shell', 'transport_path': PATH,
        'binding': {'target_ref': target, 'user_ref': 'user', 'namespace_ref': 'native',
                    'source': 'current_host_observation'},
        'resource': {'selection': 'unknown', 'source': 'current_user_declaration'},
    }
    return request


def explicit_request():
    request = neutral_request()
    request['network'] = dict(possession='present', selection='selected', configuration='imported',
                              path='explicit', resource_ref='resource')
    request['local_entry'] = {'kind': 'http', 'entry_ref': 'listener'}
    context = request['probe_context']
    context.update(transport_path='explicit_proxy', entry_ref='listener')
    context['resource'].update(selection='selected', resource_ref='resource')
    return request


class ControlledTransport:
    path_kind = PATH
    def __init__(self, context):
        self.context = deepcopy(context)
        self.calls = []
    def current_probe_context(self):
        return deepcopy(self.context)
    def request(self, url, **limits):
        self.calls.append((url, limits))
        return probes.Response(200, b'{"ip":"8.8.8.8"}')


class NeutralProbeContextTests(unittest.TestCase):
    def run_probe(self, request, transport, **changes):
        arguments = dict(approved_endpoints=[probes.ENDPOINTS['ipify_v4'][0]],
                         approved_paths=[PATH], target_ref=request['targets'][0]['target_ref'],
                         entry_request=request, transport=transport)
        arguments.update(changes)
        return probes.probe_https_ip('ipify_v4', **arguments)

    def test_unknown_protocol_system_sample_once_configuration_still_blocked(self):
        request = neutral_request()
        original = deepcopy(request)
        transport = ControlledTransport(request['probe_context'])
        result = self.run_probe(request, transport)
        self.assertEqual(result['status'], 'observed')
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(result['final_egress_declaration'], {'kind': 'unknown', 'protocol': 'unknown'})
        self.assertEqual(result['probe_context']['executor'], 'shell')
        self.assertEqual(result['coverage'], 'single_context_sample_not_whole_machine')
        self.assertEqual(result['path_association'], 'unknown')
        self.assertEqual(result['browser_path'], 'not_observed')
        self.assertEqual(request, original)
        with self.assertRaises(entry.EntryBlocked):
            entry.require_entry(request, 'configuration', 'target-local')

    def test_unknown_unselected_resources_and_absent_configuration_are_measurable(self):
        for selection in ('unknown', 'unselected'):
            for state in ('unknown', 'absent', 'imported', 'effective'):
                request = neutral_request()
                request['network'].update(selection=selection, configuration=state)
                request['probe_context']['resource']['selection'] = selection
                transport = ControlledTransport(request['probe_context'])
                self.assertEqual(self.run_probe(request, transport)['status'], 'observed')
                self.assertEqual(len(transport.calls), 1)

    def test_existing_schema_is_not_silently_upgraded(self):
        request = neutral_request()
        request['schema_version'] = entry.SCHEMA
        del request['probe_context']
        with self.assertRaises(entry.EntryBlocked):
            entry.require_entry(request, 'active_probe', 'target-local')
        request['probe_context'] = neutral_request()['probe_context']
        with self.assertRaises(entry.InvalidProjection):
            entry.assess_entry(request)

    def test_no_permission_wrong_path_wrong_target_zero_requests(self):
        for change in ({'approved_endpoints': []}, {'approved_paths': []},
                       {'target_ref': 'other-target'}, {'path_kind': 'explicit_proxy',
                                                      'approved_paths': ['explicit_proxy']}):
            request = neutral_request()
            transport = ControlledTransport(request['probe_context'])
            with self.assertRaises(probes.ProbeError):
                self.run_probe(request, transport, **change)
            self.assertEqual(transport.calls, [])

    def test_withdrawn_stale_conflicting_context_zero_requests(self):
        for location, key, values in (
            ('route', 'state', ('withdrawn', 'stale', 'conflict', 'unknown')),
            ('network', 'selection', ('withdrawn', 'stale', 'conflict', 'declined')),
            ('network', 'configuration', ('stale', 'conflict'))):
            for value in values:
                request = neutral_request()
                request[location][key] = value
                if key == 'selection':
                    request['probe_context']['resource']['selection'] = value
                transport = ControlledTransport(request['probe_context'])
                with self.assertRaises(probes.ProbeError):
                    self.run_probe(request, transport)
                self.assertEqual(transport.calls, [])

    def test_runtime_target_user_namespace_or_resource_cannot_be_swapped(self):
        for part, field, value in (('binding', 'target_ref', 'other-target'),
                                   ('binding', 'user_ref', 'other-user'),
                                   ('binding', 'namespace_ref', 'vm-guest'),
                                   ('resource', 'selection', 'unselected')):
            request = neutral_request()
            transport = ControlledTransport(request['probe_context'])
            transport.context[part][field] = value
            with self.assertRaisesRegex(probes.ProbeError, 'probe_context_mismatch'):
                self.run_probe(request, transport)
            self.assertEqual(transport.calls, [])

    def test_vm_host_cannot_stand_in_for_guest(self):
        request = neutral_request('host')
        request['route']['choice'] = 'vm'
        request['targets'] = [{'role': 'vm_host', 'target_ref': 'host'},
                              {'role': 'vm_guest', 'target_ref': 'guest'}]
        request['probe_context']['binding']['target_ref'] = 'guest'
        transport = ControlledTransport(request['probe_context'])
        with self.assertRaises(probes.ProbeError):
            self.run_probe(request, transport)
        self.assertEqual(transport.calls, [])

    def test_callback_context_change_before_send_is_rechecked(self):
        for mutation in ('withdraw', 'namespace', 'resource'):
            request = neutral_request()
            class CallbackTransport(ControlledTransport):
                @property
                def request(self):
                    if mutation == 'withdraw':
                        request['route']['state'] = 'withdrawn'
                    elif mutation == 'namespace':
                        self.context['binding']['namespace_ref'] = 'changed'
                    else:
                        request['network']['selection'] = 'unselected'
                        request['probe_context']['resource']['selection'] = 'unselected'
                        self.context = deepcopy(request['probe_context'])
                    return super().request
            transport = CallbackTransport(request['probe_context'])
            with self.assertRaises(probes.ProbeError):
                self.run_probe(request, transport)
            self.assertEqual(transport.calls, [])

    def test_runtime_provider_is_required_and_boolean_is_not_authorization(self):
        request = neutral_request()
        transport = ControlledTransport(request['probe_context'])
        transport.current_probe_context = lambda: True
        with self.assertRaises(probes.ProbeError):
            self.run_probe(request, transport)
        with patch.object(probes.subprocess, 'Popen', side_effect=AssertionError('must not run')):
            with self.assertRaisesRegex(probes.ProbeError, 'probe_context_binding_required'):
                self.run_probe(request, None)
        self.assertEqual(transport.calls, [])

    def test_shell_cannot_be_labeled_browser_even_with_browser_declarations(self):
        request = neutral_request()
        request['probe_context']['executor'] = 'browser'
        request['probe_context']['browser'] = {'profile_ref': 'profile', 'origin_ref': 'origin'}
        transport = ControlledTransport(request['probe_context'])
        with self.assertRaisesRegex(probes.ProbeError, 'unsupported_probe_executor'):
            self.run_probe(request, transport)
        self.assertEqual(transport.calls, [])

    def test_strict_nested_schema_rejects_authorization_and_secret_fields(self):
        for location in ('root', 'binding', 'resource'):
            for field in ('approved', 'effective', 'password', 'url'):
                request = neutral_request()
                context = request['probe_context']
                node = context if location == 'root' else context[location]
                node[field] = True
                with self.assertRaises(entry.InvalidProjection):
                    entry.assess_entry(request)

    def test_explicit_proxy_needs_entry_adapter_and_original_resource_gates(self):
        request = neutral_request()
        context = request['probe_context']
        context['transport_path'] = 'explicit_proxy'
        transport = ControlledTransport(context)
        transport.path_kind = 'explicit_proxy'
        with self.assertRaises(probes.ProbeError):
            self.run_probe(request, transport, path_kind='explicit_proxy', approved_paths=['explicit_proxy'])
        request['network'] = dict(possession='present', selection='selected', configuration='imported',
                                  path='explicit', resource_ref='resource')
        request['local_entry'] = {'kind': 'http', 'entry_ref': 'listener'}
        context['resource'].update(selection='selected', resource_ref='resource')
        context['entry_ref'] = 'listener'
        transport = ControlledTransport(context)
        transport.path_kind = 'explicit_proxy'
        transport.proxy_endpoint = 'http://proxy.invalid:8080'
        with self.assertRaisesRegex(probes.ProbeError, 'exact_proxy_endpoint_consent_required'):
            self.run_probe(request, transport, path_kind='explicit_proxy', approved_paths=['explicit_proxy'])
        self.assertEqual(transport.calls, [])
        result = self.run_probe(request, transport, path_kind='explicit_proxy', approved_paths=['explicit_proxy'],
                                approved_proxy_endpoints=['http://proxy.invalid:8080'])
        self.assertEqual(result['status'], 'observed')
        self.assertEqual(len(transport.calls), 1)
        transport.context['entry_ref'] = 'other-listener'
        with self.assertRaises(probes.ProbeError):
            self.run_probe(request, transport, path_kind='explicit_proxy', approved_paths=['explicit_proxy'])
        self.assertEqual(len(transport.calls), 1)

    def test_unadapted_probe_consumer_cannot_use_new_context(self):
        request = neutral_request()
        with self.assertRaises(entry.EntryBlocked) as error:
            entry.require_entry(request, 'active_probe', 'target-local')
        self.assertIn('EXACT_PROBE_ADAPTER_CONTEXT_REQUIRED', error.exception.gaps)
        result = entry.require_entry(request, 'active_probe', 'target-local',
                                     probe_executor='shell', probe_path=PATH)
        self.assertEqual(result['authorization_status'], 'not_evaluated_use_existing_action_gates')

    def test_resource_selection_and_source_must_match_current_declaration(self):
        for key, value in (('selection', 'unselected'), ('source', 'unknown')):
            request = neutral_request()
            request['probe_context']['resource'][key] = value
            transport = ControlledTransport(request['probe_context'])
            with self.assertRaises(probes.ProbeError):
                self.run_probe(request, transport)
            self.assertEqual(transport.calls, [])

    def test_builtin_explicit_proxy_is_not_implemented(self):
        request = neutral_request()
        request['network'] = dict(possession='present', selection='selected', configuration='imported',
                                  path='explicit', resource_ref='resource')
        request['local_entry'] = {'kind': 'http', 'entry_ref': 'listener'}
        context = request['probe_context']
        context.update(transport_path='explicit_proxy', entry_ref='listener')
        context['resource'].update(selection='selected', resource_ref='resource')
        with patch.object(probes.subprocess, 'Popen', side_effect=AssertionError('must not run')):
            with self.assertRaisesRegex(probes.ProbeError, 'transport_path_mismatch'):
                self.run_probe(request, None, path_kind='explicit_proxy', approved_paths=['explicit_proxy'])

    def test_endpoint_and_path_withdrawal_in_adapter_callback_prevents_send(self):
        for permission in ('endpoint', 'path'):
            request = neutral_request()
            endpoints, paths = [probes.ENDPOINTS['ipify_v4'][0]], [PATH]
            class WithdrawingTransport(ControlledTransport):
                @property
                def request(self):
                    (endpoints if permission == 'endpoint' else paths).clear()
                    return super().request
            transport = WithdrawingTransport(request['probe_context'])
            with self.assertRaises(probes.ProbeError):
                self.run_probe(request, transport, approved_endpoints=endpoints, approved_paths=paths)
            self.assertEqual(transport.calls, [])

    def test_context_provider_withdrawal_is_rechecked_after_callback(self):
        request = neutral_request()
        class WithdrawingTransport(ControlledTransport):
            def current_probe_context(self):
                request['route']['state'] = 'withdrawn'
                return super().current_probe_context()
        transport = WithdrawingTransport(request['probe_context'])
        with self.assertRaises(probes.ProbeError):
            self.run_probe(request, transport)
        self.assertEqual(transport.calls, [])

    def test_selected_unknown_upstream_keeps_resource_and_configuration_unknown(self):
        request = neutral_request()
        request['network'].update(selection='selected', possession='present', path='tun',
                                  configuration='imported', resource_ref='resource')
        request['probe_context']['resource'].update(selection='selected', resource_ref='resource')
        transport = ControlledTransport(request['probe_context'])
        self.assertEqual(self.run_probe(request, transport)['status'], 'observed')
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(entry.assess_entry(request)['gates']['configuration']['status'], 'blocked')


    def test_proxy_endpoint_is_concrete_credential_free_and_never_echoed(self):
        bad_endpoints = ('listener', 'http://proxy.invalid', 'file://proxy.invalid:8080',
                         'http://user:secret@proxy.invalid:8080', 'http://proxy.invalid:8080/',
                         'http://proxy.invalid:8080/private', 'http://proxy.invalid:8080?token=secret',
                         'http://proxy.invalid:8080#secret', 'http://proxy.invalid:8080?',
                         'http://proxy.invalid:8080#', 'http://proxy.invalid:99999',
                         'http://proxy.invalid:8080\n', True)
        for endpoint in bad_endpoints:
            request = explicit_request()
            transport = ControlledTransport(request['probe_context'])
            transport.path_kind = 'explicit_proxy'
            transport.proxy_endpoint = endpoint
            with self.assertRaisesRegex(probes.ProbeError, '^concrete_proxy_endpoint_binding_required$') as error:
                self.run_probe(request, transport, path_kind='explicit_proxy',
                               approved_paths=['explicit_proxy'], approved_proxy_endpoints=[endpoint])
            self.assertNotIn('secret', str(error.exception))
            self.assertEqual(transport.calls, [])

    def test_proxy_endpoint_or_proxy_permission_change_in_callback_prevents_send(self):
        for mutation in ('endpoint', 'permission'):
            request = explicit_request()
            approved = ['http://proxy.invalid:8080']
            class ChangingProxy(ControlledTransport):
                path_kind = 'explicit_proxy'
                proxy_endpoint = 'http://proxy.invalid:8080'
                @property
                def request(self):
                    if mutation == 'endpoint':
                        self.proxy_endpoint = 'http://other.invalid:8080'
                    else:
                        approved.clear()
                    return super().request
            transport = ChangingProxy(request['probe_context'])
            with self.assertRaises(probes.ProbeError):
                self.run_probe(request, transport, path_kind='explicit_proxy',
                               approved_paths=['explicit_proxy'], approved_proxy_endpoints=approved)
            self.assertEqual(transport.calls, [])

    def test_browser_requires_profile_and_origin_and_shell_rejects_browser_metadata(self):
        request = neutral_request()
        request['probe_context']['executor'] = 'browser'
        with self.assertRaises(entry.InvalidProjection):
            entry.assess_entry(request)
        request['probe_context']['browser'] = {'profile_ref': 'profile'}
        with self.assertRaises(entry.InvalidProjection):
            entry.assess_entry(request)
        request['probe_context']['browser']['origin_ref'] = 'origin'
        self.assertEqual(entry.assess_entry(request)['gates']['active_probe']['status'],
                         'eligible_for_existing_gate')
        request['probe_context']['executor'] = 'shell'
        with self.assertRaises(entry.InvalidProjection):
            entry.assess_entry(request)

    def test_unknown_binding_source_cannot_be_upgraded_by_matching_json(self):
        request = neutral_request()
        request['probe_context']['binding']['source'] = 'unknown'
        transport = ControlledTransport(request['probe_context'])
        with self.assertRaises(probes.ProbeError):
            self.run_probe(request, transport)
        self.assertEqual(transport.calls, [])

    def test_postsend_callback_change_is_not_reported_as_current_evidence(self):
        request = neutral_request()
        transport = ControlledTransport(request['probe_context'])
        def clock():
            request['route']['state'] = 'withdrawn'
            return None, False
        result = self.run_probe(request, transport, response_clock=clock)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['error'], 'probe_context_changed_after_send')
        self.assertIsNone(result['observed_ip'])


    def test_existing_dns_session_rejects_unadapted_context_before_any_query(self):
        import test_native_environment_entry as native_fixtures
        fixture = native_fixtures.SessionEntryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        request = neutral_request('target')
        result = native_fixtures.session.execute(
            'target', consent=fixture.consent, queries=[('reserved.test', 'A')],
            entry_request=request)
        self.assertEqual(result['errors'], ['E_ENTRY_BLOCKED'])
        fixture.child.assert_not_called()


    def test_final_proxy_getter_namespace_refresh_blocks_before_send(self):
        request = explicit_request()
        class RefreshProxy(ControlledTransport):
            path_kind = 'explicit_proxy'
            def __init__(self, context):
                super().__init__(context)
                self.reads = 0
            @property
            def proxy_endpoint(self):
                self.reads += 1
                if self.reads == 2:
                    self.context['binding']['namespace_ref'] = 'new-namespace'
                return 'http://proxy.invalid:8080'
        transport = RefreshProxy(request['probe_context'])
        with self.assertRaises(probes.ProbeError):
            self.run_probe(request, transport, path_kind='explicit_proxy',
                           approved_paths=['explicit_proxy'],
                           approved_proxy_endpoints=['http://proxy.invalid:8080'])
        self.assertEqual(transport.calls, [])

    def test_final_context_reader_path_refresh_blocks_before_send(self):
        request = neutral_request()
        class RefreshPath(ControlledTransport):
            def __init__(self, context):
                super().__init__(context)
                self.reads = 0
            def current_probe_context(self):
                self.reads += 1
                if self.reads == 2:
                    self.path_kind = 'explicit_proxy'
                return super().current_probe_context()
        transport = RefreshPath(request['probe_context'])
        with self.assertRaises(probes.ProbeError):
            self.run_probe(request, transport)
        self.assertEqual(transport.calls, [])


    def test_postsend_permission_withdrawal_keeps_one_request_and_invalidates_current_scope(self):
        for withdrawn in ('endpoint', 'path', 'proxy'):
            request = explicit_request()
            transport = ControlledTransport(request['probe_context'])
            transport.path_kind = 'explicit_proxy'
            transport.proxy_endpoint = 'http://proxy.invalid:8080'
            endpoints = [probes.ENDPOINTS['ipify_v4'][0]]
            paths = ['explicit_proxy']
            proxies = ['http://proxy.invalid:8080']
            def clock():
                {'endpoint': endpoints, 'path': paths, 'proxy': proxies}[withdrawn].clear()
                return None, False
            result = self.run_probe(request, transport, path_kind='explicit_proxy',
                                    approved_endpoints=endpoints, approved_paths=paths,
                                    approved_proxy_endpoints=proxies, response_clock=clock)
            self.assertEqual(len(transport.calls), 1)
            self.assertEqual(result['request_count'], 1)
            self.assertEqual(result['status'], 'unknown')
            self.assertEqual(result['error'], 'probe_context_changed_after_send')
            self.assertIsNone(result['observed_ip'])



class NeutralWorkflowTests(unittest.TestCase):
    def test_neutral_exception_never_opens_claude_contact_or_configuration(self):
        fixture = workflow_fixtures.WorkflowEnvironmentEntryTests()
        fixture.setUp()
        request = neutral_request('device')
        ready = replace(fixture.ready, entry_request=request)
        decision = fixture.evaluate(fixture.probe, readiness=ready)
        self.assertTrue(decision.allowed, decision.gaps)
        transport = ControlledTransport(request['probe_context'])
        NeutralProbeContextTests().run_probe(request, transport)
        self.assertEqual(len(transport.calls), 1)
        self.assertFalse(fixture.handoff(ready).allowed)
        self.assertFalse(fixture.evaluate(fixture.client, readiness=ready).allowed)
        self.assertFalse(fixture.evaluate(fixture.apply, readiness=ready).allowed)
        self.assertIs(fixture.guard.state.phase, w.Phase.PC0)

    def test_neutral_approval_callback_change_invalidates_before_transport(self):
        fixture = workflow_fixtures.WorkflowEnvironmentEntryTests()
        fixture.setUp()
        request = neutral_request('device')
        ready = replace(fixture.ready, entry_request=request)
        def approve(action):
            request['probe_context']['binding']['namespace_ref'] = 'changed'
            return w.Reply.APPROVED
        fixture.guard.authorize = approve
        transport = ControlledTransport(request['probe_context'])
        decision = fixture.evaluate(fixture.probe, readiness=ready)
        self.assertFalse(decision.allowed)
        self.assertEqual(transport.calls, [])

    def test_relabeling_claude_scope_neutral_has_no_supported_adapter(self):
        fixture = workflow_fixtures.WorkflowEnvironmentEntryTests()
        fixture.setUp()
        request = neutral_request('device')
        ready = replace(fixture.ready, entry_request=request)
        relabeled = replace(fixture.client, contact=w.Contact.NEUTRAL, endpoint_refs=('claude-endpoint',))
        result = fixture.evaluate(relabeled, readiness=ready)
        self.assertFalse(result.allowed)
        self.assertIn('UNSUPPORTED_OPERATION_SCOPE', result.gaps)
        self.assertEqual(fixture.requests, [])


if __name__ == '__main__':
    unittest.main()
