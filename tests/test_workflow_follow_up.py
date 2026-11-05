"""Offline regressions for Issues #19–#24; no target device operations."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/claude-guardian'
sys.path.insert(0, str(SKILL / 'scripts'))
import interview_flow as flow


class WorkflowFollowUpTests(unittest.TestCase):
    def setUp(self):
        self.state = flow.new_state('device-a', 'account-a')

    def item(self, **changes):
        item = dict(id='uninstall-client', target_ref='device-a', kind='manual_action',
                    status='pending', scope='selected-client', impact='client removed',
                    prerequisites=[{'check': 'inspect old exit traces', 'status': 'not_run'}],
                    return_evidence=['uninstall result'], reason='user handoff',
                    blocking_next_session=False)
        return dict(item, **changes)

    def test_topics_work_without_any_interview_answers(self):
        refs = flow.references_for_topics(['suspension', 'trace_cleanup', 'ip_quality'], os_name='windows')
        paths = {r['path']: r for r in refs}
        self.assertIn('references/account-onboarding.md', paths)
        self.assertEqual(paths['references/trace-cleanup.md']['type'], 'checklist')
        self.assertEqual(paths['sources/S07-vps-script-catalog.md']['type'], 'checklist')
        self.assertTrue(paths['sources/S07-vps-script-catalog.md']['execution_report_required'])
        self.assertIn('references/windows-cleanup.md', paths)
        self.assertNotIn('references/cleanup-cli-usage.md', paths)

    def test_payment_is_first_and_duplicate_topics_do_not_duplicate_paths(self):
        refs = flow.references_for_topics(['suspension', 'payment', 'payment', 'identity_review'])
        self.assertEqual(refs[0]['path'], 'sources/S02-ai-payments.md')
        self.assertEqual(len(refs), len({r['path'] for r in refs}))

    def test_mobile_and_ban_pdf_pages_merge(self):
        refs = flow.references_for_topics(['mobile', 'suspension'])
        pdf = next(r for r in refs if r['path'].endswith('.pdf'))
        self.assertEqual(pdf['locator'], 'p.4, p.5')

    def test_topic_facts_join_interview_routes_and_survive_private_save(self):
        s = flow.record_fact(self.state, 'Q-C02', 'windows', source='synthetic')
        s['reference_topics'] = ['trace_cleanup', 'payment']
        s = flow.loads_state(flow.dumps_state(s, host_opt_in=True))
        refs = flow.assessment(s)['required_references']
        self.assertEqual(refs[0]['path'], 'sources/S02-ai-payments.md')
        self.assertIn('references/trace-cleanup.md', {r['path'] for r in refs})

    def test_invalid_topic_or_os_rejected(self):
        for topics, os_name in [(['unknown-topic'], 'macos'), ('payment', 'macos'), (['payment'], 'other')]:
            with self.subTest(topics=topics, os_name=os_name), self.assertRaises(flow.InterviewError):
                flow.references_for_topics(topics, os_name=os_name)

    def test_existing_interview_output_marks_checklists(self):
        s = flow.record_fact(self.state, 'Q-C05', 'vps', source='synthetic')
        ref = next(r for r in flow.required_references(s) if r['path'].endswith('S07-vps-script-catalog.md'))
        self.assertEqual(ref['type'], 'checklist')

    def test_capabilities_are_target_bound_and_do_not_grant_permission(self):
        caps = dict(target_ref='device-a', platform='windows', python='missing',
                    network_check='unknown', egress_verifier='unknown', source='synthetic-observation')
        s = flow.record_capabilities(self.state, caps)
        self.assertNotIn('capabilities', self.state)
        self.assertEqual(flow.assessment(s)['capabilities']['python'], 'missing')
        self.assertEqual(flow.assessment(s)['G3']['status'], 'blocked')
        self.assertNotIn('source', flow.assessment(s)['capabilities'])
        with self.assertRaises(flow.InterviewError):
            flow.record_capabilities(s, dict(caps, target_ref='device-b'))

    def test_handoff_round_trip_retains_prerequisites_without_echoing_private_text(self):
        s = flow.record_work_item(self.state, self.item())
        loaded = flow.loads_state(flow.dumps_state(s, host_opt_in=True))
        self.assertEqual(loaded['work_items'][0]['prerequisites'], self.item()['prerequisites'])
        resumed = flow.resume_interview(loaded, resume_id='session-b')
        summary = flow.assessment(resumed)['follow_up']
        self.assertEqual(summary['items'][0]['id'], 'uninstall-client')
        self.assertNotIn('inspect old exit traces', json.dumps(summary))
        self.assertNotIn('work_items', self.state)

    def test_unfinished_acceptance_stays_blocking_until_completed(self):
        item = self.item(id='failure-drill', kind='acceptance', prerequisites=[])
        s = flow.record_work_item(self.state, item)
        self.assertTrue(s['work_items'][0]['blocking_next_session'])
        self.assertTrue(flow.assessment(s)['follow_up']['blocking_next_session'])
        s = flow.record_work_item(s, dict(item, status='completed'))
        self.assertFalse(flow.assessment(s)['follow_up']['blocking_next_session'])
        self.assertEqual(flow.assessment(s)['follow_up']['items'], [])

    def test_handoff_cannot_complete_with_unfinished_prerequisites(self):
        with self.assertRaises(flow.InterviewError):
            flow.record_work_item(self.state, self.item(status='completed'))
        with self.assertRaises(flow.InterviewError):
            flow.record_work_item(self.state, self.item(target_ref='device-b'))

    def test_saved_state_validation_cannot_bypass_acceptance_reminder(self):
        s = flow.record_work_item(self.state, self.item(kind='acceptance'))
        tampered = deepcopy(s)
        tampered['work_items'][0]['blocking_next_session'] = False
        with self.assertRaises(flow.InterviewError):
            flow.loads_state(json.dumps(tampered))

    def test_reference_cli_skips_questionnaire_and_never_saves(self):
        result = subprocess.run([sys.executable, str(SKILL/'scripts/interview_cli.py'),
                                 '--references-only', '--topics', 'ip_quality', 'trace_cleanup',
                                 '--reference-os', 'windows'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertNotIn('question', output)
        self.assertFalse(output['saved'])
        self.assertFalse(output['action_executed'])
        self.assertEqual(len([r for r in output['required_references'] if r.get('type') == 'checklist']), 2)

    def test_cli_rejects_invalid_or_mismatched_updates_without_saving(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            incoming, output = root/'input.json', root/'output.json'
            for args, value in [(['--work-item-file'], self.item(target_ref='device-b')),
                                (['--capabilities-file'], {'source': 'private-sentinel'})]:
                incoming.write_text(json.dumps(value), encoding='utf-8')
                result = subprocess.run([sys.executable, str(SKILL/'scripts/interview_cli.py'),
                                         '--target-ref', 'device-a', *args, str(incoming),
                                         '--output', str(output)], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertFalse(output.exists())
                self.assertNotIn('private-sentinel', result.stdout + result.stderr)
            result = subprocess.run([sys.executable, str(SKILL/'scripts/interview_cli.py'),
                                     '--references-only', '--topics', 'payment', '--output', str(output)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())

    def test_cli_persists_and_restores_follow_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            item_file, state_file = root/'item.json', root/'state.json'
            item_file.write_text(json.dumps(self.item(kind='acceptance')), encoding='utf-8')
            result = subprocess.run([sys.executable, str(SKILL/'scripts/interview_cli.py'),
                                     '--target-ref', 'device-a', '--work-item-file', str(item_file),
                                     '--output', str(state_file)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn('inspect old exit traces', result.stdout)
            result = subprocess.run([sys.executable, str(SKILL/'scripts/interview_cli.py'),
                                     '--input', str(state_file)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue(json.loads(result.stdout)['assessment']['follow_up']['blocking_next_session'])
            self.assertEqual(json.loads(result.stdout)['next_step'], 'review_follow_up')

    def test_guidance_covers_capabilities_handoff_and_session_start(self):
        skill = (SKILL/'SKILL.md').read_text(encoding='utf-8')
        entry = skill.split('## 环境入口顺序')[1].split('\n## ')[0]
        self.assertIn('能力核实', entry)
        self.assertIn('capabilities', entry)
        self.assertIn('blocking_next_session', skill)
        remote = (SKILL/'references/local-advanced-route.md').read_text(encoding='utf-8')
        self.assertIn('Python', remote)
        self.assertIn('egress_verifier.py', remote)
        self.assertIn('缺 Python 必须补齐', entry)
        self.assertIn('不以手写检查替代', entry)
        self.assertIn('Windows 无 Python **必须先补齐**', remote)
        guide = (SKILL/'references/agent-remediation.md').read_text(encoding='utf-8')
        self.assertIn('前置依赖', guide)
        self.assertIn('blocking_next_session', guide)
        self.assertIn('已执行项', (SKILL/'references/source-library.md').read_text(encoding='utf-8'))

    def test_source_manifest_marks_s07_without_changing_source_hash(self):
        manifest = json.loads((SKILL/'sources/manifest.json').read_text(encoding='utf-8'))
        source = next(s for s in manifest['sources'] if s['id'] == 'S07')
        self.assertEqual(source['type'], 'checklist')


if __name__ == '__main__':
    unittest.main()
