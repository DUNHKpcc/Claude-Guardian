"""ADR-018: route, egress-source and mobile questions. Offline state tests only."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('route_exit_flow', ROOT / 'skills/claude-guardian/scripts/interview_flow.py')
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)

NEW = ('Q-X01', 'Q-X02', 'Q-M01', 'Q-V07', 'Q-V08', 'Q-V09', 'Q-S08', 'Q-T01')


def base(route='local', basis='explicit_choice', **context):
    s = f.new_state('route-device', 'route-account', task_id='route-task')
    return f.set_context(s, route=route, route_selection_basis=basis, **context)


def ids(s):
    return [q['id'] for q in f.applicable_questions(s)]


def answer(s, qid, value, **kwargs):
    return f.record_fact(s, qid, value, source='synthetic:route-exit', **kwargs)


class RouteExitQuestionTests(unittest.TestCase):
    def test_registry_prompts_and_values(self):
        for qid in NEW:
            self.assertIn(qid, f.QUESTION_PROMPTS)
            self.assertTrue(f.QUESTION_PROMPTS[qid].strip())
            self.assertIn(qid, f.ROUTE_EXIT_VALUES)
        self.assertEqual(f.ROUTE_EXIT_VALUES['Q-X01'],
                         {'airport', 'self_built', 'residential_carpool', 'existing_stable_exit', 'undecided'})
        self.assertEqual(f.ROUTE_EXIT_VALUES['Q-V08'], {'lan_bridged', 'shared_nat', 'other'})

    def test_local_route_asks_egress_source_and_residential_only_for_self_built(self):
        s = base('local')
        self.assertIn('Q-X01', ids(s))
        self.assertNotIn('Q-X02', ids(s))
        s = answer(s, 'Q-X01', 'airport')
        self.assertNotIn('Q-X02', ids(s))
        self.assertNotIn('Q-T01', ids(s))
        s = answer(s, 'Q-X01', 'self_built', correction=True)
        self.assertIn('Q-X02', ids(s))
        self.assertIn('Q-T01', ids(s))
        for other in ('Q-V07', 'Q-V08', 'Q-S08', 'Q-M01'):
            self.assertNotIn(other, ids(s))

    def test_vm_route_asks_guest_os_nic_and_egress(self):
        s = base('vm')
        for qid in ('Q-V07', 'Q-V08', 'Q-X01'):
            self.assertIn(qid, ids(s))
        self.assertNotIn('Q-S08', ids(s))
        s = answer(s, 'Q-X01', 'self_built')
        self.assertIn('Q-X02', ids(s))

    def test_vps_route_asks_exit_kind_and_not_the_relay_source(self):
        s = base('vps')
        self.assertIn('Q-S08', ids(s))
        self.assertIn('Q-T01', ids(s))
        for qid in ('Q-X01', 'Q-X02', 'Q-V07', 'Q-V08'):
            self.assertNotIn(qid, ids(s))

    def test_unconfirmed_default_route_does_not_ask_route_specific_questions(self):
        s = base('local', basis='default_proposal')
        for qid in ('Q-X01', 'Q-X02', 'Q-V07', 'Q-V08', 'Q-S08'):
            self.assertNotIn(qid, ids(s))

    def test_mobile_question_follows_in_app_purchase_or_mobile_only(self):
        self.assertIn('Q-M01', ids(base('local', billing_channel='apple')))
        self.assertIn('Q-M01', ids(base('local', billing_channel='google')))
        self.assertNotIn('Q-M01', ids(base('local', billing_channel='web')))
        s = answer(base('local'), 'Q-C02', 'mobile_only')
        self.assertIn('Q-M01', ids(s))

    def test_invalid_values_are_rejected_and_unknown_is_a_state(self):
        for qid in NEW:
            for bad in ('sanitized answer', 5, ['x']):
                with self.subTest(qid=qid, bad=bad), self.assertRaisesRegex(f.InterviewError, 'Invalid route or exit category'):
                    answer(base('vm'), qid, bad)
            ok = answer(base('vm'), qid, sorted(f.ROUTE_EXIT_VALUES[qid])[0])
            self.assertEqual(ok['facts'][qid]['state'], 'reported')
        unknown = answer(base('vm'), 'Q-X01', None, state_name='unknown')
        self.assertEqual(unknown['facts']['Q-X01']['state'], 'unknown')
        asked = []
        walker = unknown
        for _ in range(80):
            question = f.next_question(walker)
            if question is None:
                break
            asked.append(question['id'])
            walker = f.mark_asked(walker, question['id'])
        self.assertNotIn('Q-X01', asked)  # a terminal unknown is not asked again

    def test_loaded_state_with_invalid_value_is_refused(self):
        s = answer(base('vm'), 'Q-V08', 'lan_bridged')
        raw = json.loads(f.dumps_state(s, host_opt_in=True))
        raw['facts']['Q-V08']['value'] = 'whatever'
        with self.assertRaises(f.InterviewError):
            f.loads_state(json.dumps(raw))

    def test_round_trip_keeps_new_facts(self):
        s = base('vm')
        for qid, value in (('Q-V07', 'omarchy'), ('Q-V08', 'lan_bridged'), ('Q-X01', 'self_built'), ('Q-X02', 'with_residential_exit')):
            s = answer(s, qid, value)
        self.assertEqual(f.loads_state(f.dumps_state(s, host_opt_in=True)), s)

    def test_schema_enumerates_the_values(self):
        props = f.STATE_SCHEMA['properties']['facts']['properties']
        for qid in NEW:
            self.assertEqual(set(props[qid]['properties']['value']['enum']) - {None}, set(f.ROUTE_EXIT_VALUES[qid]))

    def test_route_change_stales_route_bound_facts(self):
        s = base('vm')
        s = answer(s, 'Q-V07', 'omarchy')
        s = answer(s, 'Q-X01', 'self_built')
        s = f.set_context(s, route='vps', route_selection_basis='explicit_choice')
        self.assertEqual(s['facts']['Q-V07']['state'], 'stale')
        self.assertEqual(s['facts']['Q-X01']['state'], 'stale')


def refs(s):
    return [item['path'] for item in f.required_references(s)]


class RequiredReferenceTests(unittest.TestCase):
    def test_every_reference_path_ships_in_the_skill(self):
        root = ROOT / 'skills/claude-guardian'
        for key, path in f.REFERENCE_PATHS.items():
            self.assertTrue((root / path).is_file(), key)

    def test_payment_leads_with_s02(self):
        s = base('local', basis='default_proposal', billing_channel='web')
        self.assertEqual(refs(s)[0], 'sources/S02-ai-payments.md')
        self.assertEqual(f.assessment(s)['required_references'][0]['topic'], 'payment')

    def test_registration_and_mobile(self):
        s = answer(base('local', basis='default_proposal', billing_channel='apple'), 'Q-J01', 'first_subscription')
        paths = refs(s)
        for path in ('references/account-onboarding.md', 'sources/S03-claude-experience.pdf',
                     'sources/S04-claude-guide.md', 'references/mobile-guidance.md'):
            self.assertIn(path, paths)
        self.assertEqual(paths[0], 'sources/S02-ai-payments.md')
        self.assertEqual(paths.count('sources/S03-claude-experience.pdf'), 1)
        s03 = [item for item in f.required_references(s) if item['path'] == 'sources/S03-claude-experience.pdf'][0]
        self.assertEqual(s03.get('locator'), 'p.4')

    def test_local_self_built_with_residential_exit(self):
        s = answer(base('local'), 'Q-X01', 'self_built')
        s = answer(s, 'Q-X02', 'with_residential_exit')
        paths = refs(s)
        for path in ('references/egress-ip-options.md', 'sources/vps-recommendations/INDEX.md',
                     'sources/S07-vps-script-catalog.md', 'sources/R02-vps-line-optimization.md',
                     'references/line-optimization.md'):
            self.assertIn(path, paths)
        self.assertNotIn('references/vps-guidance.md', paths)

    def test_airport_gets_no_vps_material(self):
        s = answer(base('local'), 'Q-X01', 'airport')
        self.assertEqual(refs(s), ['sources/S02-ai-payments.md', 'references/authorization-tiers.md',
                                   'references/routes-and-platforms.md', 'references/egress-ip-options.md',
                                   'references/whole-machine-ipv4.md'])

    def test_vm_linux_guest_gets_firewall_script_macos_does_not(self):
        linux = answer(base('vm'), 'Q-V07', 'omarchy')
        self.assertIn('assets/vm-killswitch/install-flclash-killswitch.sh', refs(linux))
        self.assertIn('references/vm-guidance.md', refs(linux))
        mac = answer(base('vm'), 'Q-V07', 'macos')
        self.assertNotIn('assets/vm-killswitch/install-flclash-killswitch.sh', refs(mac))

    def test_unreachable_linux_vm_gets_advanced_route_before_firewall(self):
        direct = refs(answer(answer(base('vm'), 'Q-V07', 'omarchy'), 'Q-V09', 'direct'))
        for path in ('references/advanced-route.md', 'assets/remote-hardening/install-reverse-tunnel.sh',
                     'assets/remote-hardening/flclash-crash-heal.sh'):
            self.assertNotIn(path, direct)
        remote = refs(answer(answer(base('vm'), 'Q-V07', 'omarchy'), 'Q-V09', 'remote_unreachable'))
        order = [remote.index(p) for p in ('assets/vm-killswitch/install-flclash-tun.sh',
                                           'assets/remote-hardening/install-reverse-tunnel.sh',
                                           'assets/remote-hardening/flclash-crash-heal.sh',
                                           'assets/vm-killswitch/install-flclash-killswitch.sh')]
        self.assertEqual(order, sorted(order))
        self.assertIn('references/advanced-route.md', remote)
        mac = refs(answer(answer(base('vm'), 'Q-V07', 'macos'), 'Q-V09', 'remote_unreachable'))
        self.assertNotIn('references/advanced-route.md', mac)
        with self.assertRaises(f.InterviewError):
            answer(base('vm'), 'Q-V09', 'whatever')

    def test_vps_exit_kind_selects_firewall_and_relay_material(self):
        own = answer(base('vps'), 'Q-S08', 'vps_own_ip')
        for path in ('references/vps-guidance.md', 'sources/S08-vps-claude-tutorial.pdf',
                     'sources/vps-recommendations/INDEX.md', 'sources/S07-vps-script-catalog.md',
                     'assets/vps-firewall/vps-guard.sh'):
            self.assertIn(path, refs(own))
        self.assertNotIn('sources/R02-vps-line-optimization.md', refs(own))
        chain = answer(base('vps'), 'Q-S08', 'residential_chain')
        for path in ('sources/R02-vps-line-optimization.md', 'references/line-optimization.md',
                     'assets/vm-killswitch/install-flclash-killswitch.sh'):
            self.assertIn(path, refs(chain))
        self.assertNotIn('assets/vps-firewall/vps-guard.sh', refs(chain))

    def test_unconfirmed_route_attaches_no_route_material(self):
        s = base('vps', basis='default_proposal')
        self.assertNotIn('references/vps-guidance.md', refs(s))

    def test_macos_cleanup_attaches_s06(self):
        s = answer(base('local', basis='default_proposal', task='cleanup'), 'Q-C02', 'macos')
        self.assertIn('sources/S06-macos-cleanup-sanitized.md', refs(s))
        self.assertNotIn('references/account-onboarding.md', refs(s))

    def test_references_are_not_authorization(self):
        s = answer(base('vps'), 'Q-S08', 'vps_own_ip')
        a = f.assessment(s)
        self.assertIn('required_references', a)
        self.assertEqual(a['G3']['status'], 'blocked')


class LineAndWindowsReferenceTests(unittest.TestCase):
    def test_line_problem_attaches_line_optimization(self):
        none = answer(base('vps'), 'Q-T01', 'none')
        self.assertNotIn('references/line-optimization.md', refs(none))
        slow = answer(base('vps'), 'Q-T01', 'evening_slow')
        for path in ('references/line-optimization.md', 'sources/R02-vps-line-optimization.md',
                     'sources/vps-recommendations/INDEX.md'):
            self.assertIn(path, refs(slow))
        lag = answer(base('vps'), 'Q-T01', 'desktop_lag')
        self.assertIn('references/line-optimization.md', refs(lag))

    def test_line_question_for_self_built_on_local(self):
        s = answer(base('local'), 'Q-X01', 'self_built')
        s = answer(s, 'Q-X02', 'with_residential_exit')
        s = answer(s, 'Q-T01', 'drops')
        self.assertIn('references/line-optimization.md', refs(s))

    def test_windows_local_attaches_ipv6_hint_with_anchor(self):
        s = answer(base('local'), 'Q-C02', 'windows')
        item = [i for i in f.required_references(s) if i['path'] == 'references/agent-remediation.md'][0]
        self.assertEqual(item['locator'], '#windows-adapter-ipv6-hint')
        mac = answer(base('local'), 'Q-C02', 'macos')
        self.assertNotIn('references/agent-remediation.md', refs(mac))

    def test_vm_linux_guest_gets_setup_scripts_in_order(self):
        paths = refs(answer(base('vm'), 'Q-V07', 'omarchy'))
        order = [paths.index(p) for p in ('assets/vm-killswitch/enable-guest-ssh.sh',
                                          'assets/vm-killswitch/install-flclash-tun.sh',
                                          'assets/vm-killswitch/install-flclash-killswitch.sh')]
        self.assertEqual(order, sorted(order))
        mac = refs(answer(base('vm'), 'Q-V07', 'macos'))
        self.assertNotIn('assets/vm-killswitch/enable-guest-ssh.sh', mac)


class LocalFirewallReferenceTests(unittest.TestCase):
    def test_windows_local_gets_firewall_prompts_before_s05(self):
        paths = refs(answer(base('local'), 'Q-C02', 'windows'))
        self.assertIn('references/local-firewall-prompts.md', paths)
        self.assertLess(paths.index('references/local-firewall-prompts.md'), paths.index('sources/S05-local-protection.md'))
        item = [i for i in f.required_references(answer(base('local'), 'Q-C02', 'windows'))
                if i['path'] == 'references/local-firewall-prompts.md'][0]
        self.assertEqual(item['locator'], '#windows')

    def test_mac_local_gets_firewall_prompts_and_dns_lessons(self):
        paths = refs(answer(base('local'), 'Q-C02', 'macos'))
        for path in ('references/local-firewall-prompts.md', 'references/macos-dns-case-lessons.md'):
            self.assertIn(path, paths)
        self.assertNotIn('sources/S05-local-protection.md', paths)

    def test_vm_and_vps_do_not_get_local_firewall_prompts(self):
        self.assertNotIn('references/local-firewall-prompts.md', refs(answer(base('vm'), 'Q-C02', 'macos')))
        self.assertNotIn('references/local-firewall-prompts.md', refs(answer(base('vps'), 'Q-C02', 'windows')))


class AuthorizationTierReferenceTests(unittest.TestCase):
    def test_explicit_route_attaches_authorization_tiers(self):
        for route in ('local', 'vm', 'vps'):
            self.assertIn('references/authorization-tiers.md', refs(base(route)), route)
        self.assertNotIn('references/authorization-tiers.md', refs(base('local', basis='default_proposal')))

    def test_tiers_are_not_a_state_machine_authorization(self):
        a = f.assessment(answer(base('vps'), 'Q-S08', 'vps_own_ip'))
        self.assertEqual(a['G3']['status'], 'blocked')


class DiscoverabilityReferenceTests(unittest.TestCase):
    """Materials that exist but were never routed to the Agent (the A0b/KYC gap) must be attached."""

    def locator(self, s, path):
        return [item for item in f.required_references(s) if item['path'] == path][0].get('locator')

    def test_suspension_and_past_restriction_attach_ban_timeline_and_triage(self):
        for s in (f.set_context(base('local'), incident='suspension'),
                  answer(base('local'), 'Q-D01', 'past_restriction_on_target')):
            paths = refs(s)
            for path in ('references/account-onboarding.md', 'sources/S03-claude-experience.pdf',
                         'sources/S04-claude-guide.md', 'references/incidents-and-integrations.md'):
                self.assertIn(path, paths)
            self.assertEqual(self.locator(s, 'references/account-onboarding.md'), '#a0b')
            self.assertEqual(self.locator(s, 'sources/S03-claude-experience.pdf'), 'p.5')
            topics = {item['path']: item['topic'] for item in f.required_references(s)}
            self.assertEqual(topics['references/incidents-and-integrations.md'], 'incident_triage')
            self.assertNotIn('references/accounts-and-payments.md', paths)

    def test_identity_review_adds_kyc_triage_and_pages_accumulate_on_one_entry(self):
        s = f.set_context(base('local'), incident='identity_review')
        self.assertEqual(self.locator(s, 'references/accounts-and-payments.md'), '#a3-真实身份核验异常会话与凭据保护')
        mixed = f.set_context(base('local', billing_channel='apple'), incident='suspension')
        self.assertEqual(self.locator(mixed, 'sources/S03-claude-experience.pdf'), 'p.4, p.5')
        self.assertEqual(refs(mixed).count('sources/S03-claude-experience.pdf'), 1)

    def test_no_incident_means_no_ban_material(self):
        self.assertNotIn('references/incidents-and-integrations.md', refs(base('local')))

    def test_local_route_attaches_whole_machine_egress_guide(self):
        self.assertIn('references/whole-machine-ipv4.md', refs(base('local')))
        self.assertNotIn('references/whole-machine-ipv4.md', refs(base('vps')))

    def test_cleanup_attaches_platform_cleanup_guides(self):
        mac = answer(f.set_context(base('local'), task='cleanup'), 'Q-C02', 'macos')
        win = answer(f.set_context(base('local'), task='cleanup'), 'Q-C02', 'windows')
        unknown = f.set_context(base('local'), task='cleanup')
        self.assertTrue({'sources/S06-macos-cleanup-sanitized.md', 'references/cleanup-cli-usage.md'} <= set(refs(mac)))
        self.assertNotIn('references/windows-cleanup.md', refs(mac))
        self.assertIn('references/windows-cleanup.md', refs(win))
        self.assertNotIn('references/cleanup-cli-usage.md', refs(win))
        self.assertTrue({'references/windows-cleanup.md', 'references/cleanup-cli-usage.md'} <= set(refs(unknown)))


if __name__ == '__main__':
    unittest.main()

