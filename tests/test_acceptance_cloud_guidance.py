"""Cloud acceptance replays for T65, T71 and ENV-T124 (no earlier dialogue evidence).

Normalized synthetic inputs only. Not a model evaluation, not a native observation, not a claim about any real
ban mechanism. Expectations are authored from the original requirement text. Run with --replay to print the
actual observations.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / 'skills/claude-guardian'
sys.path.insert(0, str(SK / 'scripts'))
import agent_remediation as ar  # noqa: E402
import status_dashboard as dash  # noqa: E402

TEXT = {name: (SK / name).read_text(encoding='utf-8')
        for name in ('SKILL.md', 'references/agent-remediation.md', 'references/evidence-policy.md',
                     'references/incidents-and-integrations.md')}


def select(*codes):
    return ar.select({'schema_version': ar.INPUT_SCHEMA, 'target_ref': 'device-1',
                      'findings': [{'code': c} for c in codes]}, 'device-1')


def analyze_fixture():
    run = subprocess.run([sys.executable, '-B', str(SK / 'scripts/guardian.py'), 'analyze', '--target-ref', 'device-1',
                          '--input', str(ROOT / 'tests/fixtures/proxy-port-conflict.json')],
                         capture_output=True, text=True, encoding='utf-8', timeout=30,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return run.returncode, json.loads(run.stdout)


def observe():
    code, report = analyze_fixture()
    with tempfile.TemporaryDirectory() as d:
        src, out = Path(d) / 'r.json', Path(d) / 'o.html'
        src.write_text(json.dumps(report), encoding='utf-8')
        run = subprocess.run([sys.executable, '-B', str(SK / 'scripts/status_dashboard.py'), '--input', str(src),
                              '--output', str(out)], capture_output=True, text=True, encoding='utf-8', timeout=30,
                             env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        html = out.read_text(encoding='utf-8') if run.returncode == 0 else ''
    return {'tz_only': select('EGRESS_TIMEZONE_DIFFERENCE'), 'goal': select('TIMEZONE_LANGUAGE_GOAL'),
            'analyze_exit': code, 'report': report, 'dashboard_exit': run.returncode,
            'dashboard_marks_synthetic': '合成示例，不是你的设备检测结果' in html}


class CloudGuidanceAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = observe()

    def test_t65_t71_egress_timezone_difference_creates_no_change_target(self):
        r = self.o['tz_only']
        self.assertEqual([a['action_id'] for a in r['actions']], ['keep'])
        action = r['actions'][0]
        self.assertEqual(action['kind'], 'no_change')
        self.assertFalse(action['target_mutation_supported'])
        self.assertEqual(action['agent_fallback'], 'none')
        self.assertEqual((r['changes'], r['authority'], r['completion']), ([], 'none', 'no_repair_performed'))
        self.assertNotIn('clock', [a['action_id'] for a in r['actions']])

    def test_t65_explicit_timezone_goal_never_follows_egress_region(self):
        r = self.o['goal']
        action = r['actions'][0]
        self.assertEqual(action['action_id'], 'clock')
        self.assertIn('不按出口地区改时区', ' '.join(action['steps']))
        self.assertIn('用户确认后', ' '.join(action['steps']))
        self.assertEqual(r['changes'], [])
        self.assertFalse(r['environment_pass'])

    def test_t65_t71_guidance_has_no_ban_probability_or_timezone_benefit_claim(self):
        skill = TEXT['SKILL.md']
        self.assertIn('不编造免封概率', skill)
        self.assertIn('时区伪装收益', skill)
        self.assertIn('出口位置不代表服务资格', skill)
        ev = TEXT['references/evidence-policy.md']
        self.assertIn('C03 语言/时区因果', ev)
        self.assertIn('社区案例不证明总体概率', ev)
        self.assertIn('仅作经验，不用作许可/概率/平台验证', ev)
        self.assertIn('证据冲突时并列，不删除反例', TEXT['references/incidents-and-integrations.md'])
        rem = TEXT['references/agent-remediation.md']
        self.assertRegex(rem, r'ENV-04.*时区仅与出口不同.*no_change.*不制造修改目标')
        self.assertIn('不按出口地区改时区', rem)

    def test_t71_no_community_post_is_registered_as_adopted_cause(self):
        ev = TEXT['references/evidence-policy.md']
        self.assertIn('官方政策只能支持其产品/时间/范围内的公开规则', ev)
        self.assertIn('技术文档描述指定版本能力', ev)
        self.assertIn('推广资料只是待查线索', ev)

    def test_env_t124_synthetic_fixture_reports_only_fixture_scope(self):
        report = self.o['report']
        self.assertEqual(self.o['analyze_exit'], 0)
        self.assertEqual(report['record_kind'], 'synthetic_example')
        self.assertEqual(report['limits']['native_platform_validation'], 'not_run')
        self.assertIs(report['limits']['environment_pass_claim'], False)
        self.assertIs(report['limits']['account_safety_guarantee'], False)
        self.assertEqual(self.o['dashboard_exit'], 0)
        self.assertTrue(self.o['dashboard_marks_synthetic'])

    def test_env_t124_selection_never_closes_platform_validation(self):
        for r in (self.o['tz_only'], self.o['goal']):
            self.assertEqual(r['native_acceptance'], 'not_established')
            self.assertIs(r['environment_pass'], False)


if __name__ == '__main__':
    if '--replay' in sys.argv:
        o = observe()
        print(json.dumps({'tz_only_actions': [a['action_id'] for a in o['tz_only']['actions']],
                          'tz_only_kind': o['tz_only']['actions'][0]['kind'],
                          'goal_steps': o['goal']['actions'][0]['steps'],
                          'limits': o['report']['limits'], 'record_kind': o['report']['record_kind'],
                          'dashboard_marks_synthetic': o['dashboard_marks_synthetic']},
                         ensure_ascii=False, indent=2, sort_keys=True))
    else:
        unittest.main()
