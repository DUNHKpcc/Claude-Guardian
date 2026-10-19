"""Integrity checks only: these do not accept the 218 behavioral cases."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

# Explicit cases and original layer spellings; scheduling does not imply acceptance.
HISTORICALLY_ACCEPTED = {
    **{case: ('docs/evidence/rebuild-asset-route-cases.md', 'L+C', ['L', 'C'])
       for case in ('T26', 'T33')},
    **{case: ('docs/evidence/rebuild-local-incident-cases.md', 'L+C', ['L', 'C'])
       for case in ('T22', 'T25')},
    **{case: ('docs/evidence/rebuild-upgrade-conflict-cases.md', 'L+C', ['L', 'C'])
       for case in ('T77', 'T80')},
    **{case: ('docs/evidence/subscription-boundaries/CURRENT-REVIEW.md', 'L+C', ['L', 'C'])
       for case in ('T36', 'T38', 'T46', 'T54')},
    **{case: ('docs/evidence/rebuild-rule-scope-guided-responses.md', 'L + C', ['L', 'C'])
       for case in ('ENV-T38', 'ENV-T39', 'ENV-T41', 'ENV-T42', 'ENV-T58')},
    **{case: ('docs/evidence/rebuild-subscription-original-cases.md', 'L+C', ['L', 'C'])
       for case in ('T76', 'T84')},
    **{case: ('docs/evidence/rebuild-t11-t12-safe-inputs.md', 'L+C', ['L', 'C'])
       for case in ('T11', 'T12')},
    **{case: ('docs/evidence/rebuild-experience-and-subscription.md', 'L+C', ['L', 'C'])
       for case in ('T75', 'T79')},
    **{case: ('docs/evidence/rebuild-entry-order.md', 'L+C', ['L', 'C'])
       for case in ('T29', 'T57')},
    **{case: ('docs/evidence/rebuild-mobile-route.md', 'L+C', ['L', 'C'])
       for case in ('T49', 'T83')},
    **{case: ('docs/evidence/rebuild-history-and-pause.md', 'L+C', ['L', 'C'])
       for case in ('T31', 'T47')},
    'T82': ('docs/evidence/rebuild-legacy-retirement.md', 'L+C', ['L', 'C']),
    **{case: ('docs/evidence/rebuild-t03-t05-guided-responses.md', 'L+C', ['L', 'C'])
       for case in ('T03', 'T05')},
    'T16': ('docs/evidence/rebuild-resume-completion.md', 'L+C', ['L', 'C']),
    'T23': ('docs/evidence/rebuild-local-egress.md', 'L+C', ['L', 'C']),
    **{case: ('docs/evidence/rebuild-intake-basics.md', 'L+C', ['L', 'C'])
       for case in ('T01', 'T02')},
    'T18': ('docs/evidence/rebuild-t18-appeal-facts.md', 'L+C', ['L', 'C']),
    'T09': ('docs/evidence/rebuild-source-dedup.md', 'L+C', ['L', 'C']),
    **{case: ('docs/evidence/rebuild-route-cases.md', 'L+C', ['L', 'C'])
       for case in ('T19', 'T20', 'T21', 'T24')},
    **{case: ('docs/evidence/rebuild-intake-cases.md', 'L+C', ['L', 'C'])
       for case in ('T53', 'T74', 'T81')},
    **{case: ('docs/evidence/rebuild-task-scope-cases.md', 'L+C', ['L', 'C'])
       for case in ('T34', 'T43', 'T48', 'T78')},
    'ENV-T40': ('docs/evidence/rebuild-env40-composition.md', 'L + R', ['L', 'R']),
    'ENV-T79': ('docs/evidence/rebuild-enforcement-cases.md', 'L', ['L']),
    'ENV-T81': ('docs/evidence/rebuild-required-controls-case.md', 'L + C', ['L', 'C']),
    'ENV-T90': ('docs/evidence/rebuild-enforcement-cases.md', 'L + C', ['L', 'C']),
}


# This checkpoint's current decisions are explicit, never inferred from test totals.
CURRENTLY_ACCEPTED = frozenset({'T03', 'T05', 'T09', 'T18'})
LIMITED_CURRENT_REVIEW = 'docs/evidence/entry-order-limited-revalidation.md'
LIMITED_CURRENT_REVIEW_SHA256 = 'b94395b4d52c7d3a1f54954d3661a66af9e94de0faad435b9fdde49313eacd8d'
REVALIDATION_GROUPS = {'route_transition': ('T16',
                      'T19',
                      'T20',
                      'T21',
                      'T22',
                      'T23',
                      'T24',
                      'T25',
                      'T26',
                      'T33',
                      'T34',
                      'T53'),
 'entry_and_environment_intake': ('T01', 'T02', 'T29', 'T43', 'T57', 'T81', 'T84'),
 'workflow_enforcement': ('ENV-T79', 'ENV-T81', 'ENV-T90'),
 'subscription_and_interview_compatibility': ('T31',
                                              'T36',
                                              'T38',
                                              'T46',
                                              'T47',
                                              'T48',
                                              'T49',
                                              'T54',
                                              'T74',
                                              'T75',
                                              'T76',
                                              'T77',
                                              'T78',
                                              'T79',
                                              'T80',
                                              'T82',
                                              'T83'),
 'safe_input_compatibility': ('T11', 'T12'),
 'rule_scope_compatibility': ('ENV-T38', 'ENV-T39', 'ENV-T41', 'ENV-T42', 'ENV-T58'),
 'conversion_recovery_compatibility': ('ENV-T40',)}
HISTORICAL_EVIDENCE_RECORDS_SHA256 = 'baab12271fa16955f7d695a5616a972235a6ea593bb0136c65dba124722d958e'
# Independent fixed hashes prevent coordinated edits of a ledger and its page
# from silently rewriting the previous complete-case review.
HISTORICAL_PAGE_SHA256 = {'docs/evidence/rebuild-intake-basics.md': 'c8aca9fc6acaef50deb2d1704d73cf7c9f742d1598bb17c1df0b10533710c22d',
 'docs/evidence/rebuild-t03-t05-guided-responses.md': 'c329f75788acc702ecfb400e79731e4c9ca8be43dcc19a880dd1d86ff5bcc39c',
 'docs/evidence/rebuild-source-dedup.md': '0b81ae3758c50584f040610500effe4cc7760d00a94c7c578dbbce24c1310d32',
 'docs/evidence/rebuild-t11-t12-safe-inputs.md': '68d81acfe44558024c420e5b5f2328ea0d713f4dcd28b6b9e27745928ce3a3ea',
 'docs/evidence/rebuild-resume-completion.md': 'd7fba982e8b5933e6160332ffc60c637577ddde79db2d8397ae1978e77bd52f5',
 'docs/evidence/rebuild-t18-appeal-facts.md': '54bb6b7c0eca1119115b6b8569ebc6058e35643bb5cf066b5824d9a7d589adbb',
 'docs/evidence/rebuild-route-cases.md': '1a611f4c646835469a42f6df5e0e91b2aeca1f26e0a7e33a462c407f2995aa1f',
 'docs/evidence/rebuild-local-incident-cases.md': '57c0be1d6fd953f01ad0de69f08bfc92527c1939ea3fa1341bec0d662d170561',
 'docs/evidence/rebuild-local-egress.md': '46b31dbdd4cd61b35d53d65940167c9dc43baa18ee1bdb624ea4b368fc3991db',
 'docs/evidence/rebuild-asset-route-cases.md': '8e31a9f34aaa5ed191a2eee6721a7633d9754724da156304a23c75f9dd485459',
 'docs/evidence/rebuild-entry-order.md': 'ac003c14e6a9d2ad17d2a7d57803b57666a15c6ac2c85d7a40c49003ca61b5e8',
 'docs/evidence/rebuild-history-and-pause.md': '0777b57ce8189a47cb5c1565108c979f5f8afd4d93ae0058b4f405a2f119031b',
 'docs/evidence/rebuild-task-scope-cases.md': '37e0478c50e382f206f6f5214ec9bb9291b8ccddd0bab6724752b3defef137c5',
 'docs/evidence/subscription-boundaries/CURRENT-REVIEW.md': '8f3801b4d6b402779a7d9fb488fc895255c5142220622f8d90afd9c85f4701aa',
 'docs/evidence/rebuild-mobile-route.md': '95c564477a08a269f15fc94d5e419ecc67d0d1e087867c64c06f6441962097ea',
 'docs/evidence/rebuild-intake-cases.md': '74979d1eab88d6c2ec73772246ffd06cd14ce4643e9cca8638a0737a9cb5df5e',
 'docs/evidence/rebuild-experience-and-subscription.md': '8b7052ec894f37df13c54000b056489942bfcc394735e1918980c83511138b0a',
 'docs/evidence/rebuild-subscription-original-cases.md': '84fa95b46e3183b58f5ba1b7ea9c07a69aa85a4c57497df4ac2a9e52e488fdcf',
 'docs/evidence/rebuild-upgrade-conflict-cases.md': '0a8b8a724d76bba6e5c4a7a80c1846ce8e6b9608f8a374c784bea5a12925563b',
 'docs/evidence/rebuild-legacy-retirement.md': 'f48f1af5369396e9095e411706f6baeb4fd8be77a4c850f1adb47a7523aa3479',
 'docs/evidence/rebuild-rule-scope-guided-responses.md': '910fc7dca9cc10989545839ce2585452736b565b2ca91f249e950f3b92a17d1a',
 'docs/evidence/rebuild-env40-composition.md': 'bfa5ba5babd96fe93f2d42602b01c2c5eee42c5595a6243430b5221c88d65d1c',
 'docs/evidence/rebuild-enforcement-cases.md': 'deb11002f6a89bdae077388bca4666b2f44b384e069c5531cc9de9c1e326d97e',
 'docs/evidence/rebuild-required-controls-case.md': 'afc1f1a5425b40e4a8f0fdbb49c6a315b70483e86f9eff88bf8bcf45a20eff23'}

# Current pin checks use the separately reviewed current page; old pages keep
# their original source hashes and cannot be repinned in place.
LIMITED_INVENTORIES = {
    'skills/claude-guardian/sources': (11, '9c59f9170d22bd4a610a30bf2fd7efeedcc1551a3f184a43d0e86cf4bc243558'),
    'docs/evidence/t03-t05-guided-response-v1': (10, '57abb8921cfbbc92d4514d20977d7084819e0ac4efb7a525a4627507552819ae'),
    'docs/evidence/t18-guided-response-v1': (8, '1a1288236f46594f019faeda2c8fde6ddfef57b3607c2ab5ceb44b821372ec94'),
}


class AcceptanceRebuildLedgerTests(unittest.TestCase):
    def test_all_original_conditions_and_layers_are_preserved(self):
        ledger = json.loads((ROOT / 'docs/acceptance-rebuild-ledger.json').read_text(encoding='utf-8'))
        original = [line for line in (ROOT / 'docs/implementation-tracker.md').read_text(encoding='utf-8').splitlines()
                    if re.match(r'^\| (?:T\d+|ENV-T\d+) \|', line)]
        self.assertEqual(len(original), 218)
        self.assertEqual(ledger['original_rows_sha256'], hashlib.sha256(('\n'.join(original) + '\n').encode()).hexdigest())
        cases = ledger['cases']
        self.assertEqual(len(cases), 218)
        self.assertEqual(len({case['id'] for case in cases}), 218)
        for case, line in zip(cases, original):
            expected = [value.strip() for value in line.split('|')[1:-1]]
            self.assertEqual([case['id'], case['scenario'], case['requirement'], case['verification_layer']], expected[:4])

    def test_historical_pin_tables_and_current_accepted_source_pins(self):
        # Hashes are invalidation signals, not substitutes for L+C review.
        expected_counts = {
            'docs/evidence/rebuild-rule-scope-guided-responses.md': 21,
            'docs/evidence/rebuild-subscription-original-cases.md': 13,
            'docs/evidence/rebuild-experience-and-subscription.md': 11,
            'docs/evidence/rebuild-entry-order.md': 11,
            'docs/evidence/rebuild-mobile-route.md': 11,
            'docs/evidence/rebuild-history-and-pause.md': 12,
            'docs/evidence/rebuild-legacy-retirement.md': 14,
            'docs/evidence/rebuild-resume-completion.md': 15,
            'docs/evidence/rebuild-local-egress.md': 7,
            # T18 retained artifact and guide hashes have their own evidence suite.
            'docs/evidence/rebuild-intake-basics.md': 18,
            'docs/evidence/rebuild-env40-composition.md': 17,
            'docs/evidence/rebuild-route-cases.md': 15,
            'docs/evidence/rebuild-source-dedup.md': 4,
            'docs/evidence/rebuild-enforcement-cases.md': 16,
            'docs/evidence/rebuild-intake-cases.md': 15,
            'docs/evidence/rebuild-required-controls-case.md': 13,
            'docs/evidence/rebuild-task-scope-cases.md': 17,
        }
        ledger = json.loads((ROOT / 'docs/acceptance-rebuild-ledger.json').read_text(encoding='utf-8'))
        current_pages = {case['evidence']['path'] for case in ledger['cases']
                         if case['id'] in CURRENTLY_ACCEPTED}
        for path, count in expected_counts.items():
            page = (ROOT / path).read_text(encoding='utf-8')
            pins = re.findall(r'^\| `([^`]+)` \| `([0-9a-f]{64})` \|$', page, re.MULTILINE)
            self.assertEqual(len(pins), count)
            self.assertEqual(len({name for name, _ in pins}), count)
            for name, digest in pins:
                if path not in current_pages:
                    continue  # Historical table shape/bytes are checked, not live compatibility.
                with self.subTest(evidence=path, reviewed_file=name):
                    self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest,
                                     'Relevant bytes changed: rerun and re-review L+C before refreshing pins')

    def test_limited_current_review_has_strict_current_source_pins(self):
        page = ROOT / LIMITED_CURRENT_REVIEW
        self.assertFalse(page.is_symlink())
        self.assertEqual(hashlib.sha256(page.read_bytes()).hexdigest(), LIMITED_CURRENT_REVIEW_SHA256)
        pins = re.findall(r'^\| `([^`]+)` \| `([0-9a-f]{64})` \|$',
                          page.read_text(encoding='utf-8'), re.MULTILINE)
        self.assertEqual(len(pins), 15)
        self.assertEqual(len({name for name, _ in pins}), 15)
        for name, digest in pins:
            with self.subTest(current_reviewed_source=name):
                path = ROOT / name
                self.assertFalse(path.is_symlink())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest,
                                 'Current acceptance requires renewed scoped review after source drift')

    def test_limited_review_exact_additions_reconstruct_prior_whole_files(self):
        skill = (ROOT / 'skills/claude-guardian/SKILL.md').read_text(encoding='utf-8')
        first = '## 环境入口顺序（2026-10-19 用户确认更新）\n'
        last = '## Claude 目标流量默认仅允许 IPv4\n'
        self.assertEqual(skill.count(first), 1)
        start, end = skill.index(first), skill.index(last)
        self.assertLess(start, end)
        historical = (skill[:start] + skill[end:]).encode('utf-8')
        self.assertEqual(hashlib.sha256(historical).hexdigest(),
                         'f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3')
        intake = (ROOT / 'skills/claude-guardian/references/intake.md').read_text(encoding='utf-8')
        first, last = '当前环境动作顺序补充（2026-10-19）：', '中文执行摘要：'
        self.assertEqual(intake.count(first), 1)
        start, end = intake.index(first), intake.index(last)
        self.assertLess(start, end)
        historical = (intake[:start] + intake[end:]).encode('utf-8')
        self.assertEqual(hashlib.sha256(historical).hexdigest(),
                         '3eb0c795948d916804addfed31e8bcbb19502ec2447c8db2b0551f8d931e5742')
        package = (ROOT / 'tools/package_skill.py').read_bytes()
        member = b', "scripts/environment_entry.py"'
        self.assertEqual(package.count(member), 1)
        historical = package.replace(member, b'', 1)
        self.assertEqual(hashlib.sha256(historical).hexdigest(),
                         '1ea4db679625908ca0a9ad103aa79309421725e0cc4d17f7c8d046291572f37b')

    def test_limited_review_preserves_complete_source_and_response_inventories(self):
        for relative, (count, expected) in LIMITED_INVENTORIES.items():
            directory = ROOT / relative
            inventory = {}
            self.assertFalse(directory.is_symlink())
            for path in directory.rglob('*'):
                self.assertFalse(path.is_symlink())
                if path.is_file() and '__pycache__' not in path.parts:
                    inventory[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(len(inventory), count)
            canonical = json.dumps(inventory, ensure_ascii=True, sort_keys=True,
                                   separators=(',', ':')).encode('utf-8')
            self.assertEqual(hashlib.sha256(canonical).hexdigest(), expected)

    def test_historical_evidence_records_and_pages_are_immutable(self):
        ledger = json.loads((ROOT / 'docs/acceptance-rebuild-ledger.json').read_text(encoding='utf-8'))
        retained = {}
        for case in ledger['cases']:
            case_id = case['id']
            if case_id not in HISTORICALLY_ACCEPTED:
                self.assertNotIn('historical_evidence', case)
                continue
            expected_path, original_layer, reviewed_layers = HISTORICALLY_ACCEPTED[case_id]
            evidence = case.get('historical_evidence', case.get('evidence'))
            self.assertIsInstance(evidence, dict)
            self.assertEqual(case['verification_layer'], original_layer)
            self.assertEqual(evidence['path'], expected_path)
            self.assertEqual(evidence['layers'], reviewed_layers)
            self.assertEqual(evidence['sha256'], HISTORICAL_PAGE_SHA256[expected_path])
            self.assertTrue(evidence['boundary'])
            retained[case_id] = evidence
        self.assertEqual(set(retained), set(HISTORICALLY_ACCEPTED))
        self.assertEqual(len(retained), 51)
        canonical = json.dumps(retained, ensure_ascii=True, sort_keys=True,
                               separators=(',', ':')).encode('utf-8')
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), HISTORICAL_EVIDENCE_RECORDS_SHA256)
        self.assertEqual(set(HISTORICAL_PAGE_SHA256),
                         {entry[0] for entry in HISTORICALLY_ACCEPTED.values()})
        for relative, expected in HISTORICAL_PAGE_SHA256.items():
            with self.subTest(historical_page=relative):
                path = ROOT / relative
                self.assertFalse(path.is_symlink())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected,
                                 'Preserve historical evidence; add a separate current review')

    def test_scheduling_is_not_current_or_historical_acceptance(self):
        ledger = json.loads((ROOT / 'docs/acceptance-rebuild-ledger.json').read_text(encoding='utf-8'))
        groups = {case: group for group, cases in REVALIDATION_GROUPS.items() for case in cases}
        self.assertEqual(len(groups), 47)
        self.assertEqual(sum(map(len, REVALIDATION_GROUPS.values())), 47)
        self.assertEqual(set(groups), set(HISTORICALLY_ACCEPTED) - CURRENTLY_ACCEPTED)
        self.assertEqual(len(CURRENTLY_ACCEPTED), 4)
        counts, statuses = {}, {}
        for case in ledger['cases']:
            case_id = case['id']
            accepted = case_id in CURRENTLY_ACCEPTED
            self.assertEqual(case['rebuild_acceptance'],
                             'accepted_revalidated' if accepted else 'pending_revalidation')
            if accepted:
                self.assertNotIn('revalidation', case)
                expected_path, original_layer, reviewed_layers = HISTORICALLY_ACCEPTED[case_id]
                evidence = case['evidence']
                self.assertEqual(case['verification_layer'], original_layer)
                self.assertEqual(evidence['path'], LIMITED_CURRENT_REVIEW)
                self.assertEqual(evidence['layers'], reviewed_layers)
                self.assertEqual(evidence['review_date'], '2026-10-19')
                self.assertTrue(evidence['boundary'])
                self.assertEqual(evidence['sha256'], LIMITED_CURRENT_REVIEW_SHA256)
                self.assertEqual(evidence['sha256'],
                                 hashlib.sha256((ROOT / LIMITED_CURRENT_REVIEW).read_bytes()).hexdigest())
            else:
                self.assertNotIn('evidence', case)
                if case_id in groups:
                    self.assertIn('historical_evidence', case)
                    review = case['revalidation']
                    self.assertEqual(set(review), {'requirement_id', 'date', 'group', 'reason', 'tracking'})
                    self.assertEqual(review['requirement_id'], 'PRODUCT-ENTRY-20261019')
                    self.assertEqual(review['date'], '2026-10-19')
                    self.assertEqual(review['group'], groups[case_id])
                    self.assertTrue(review['reason'])
                    self.assertEqual(review['tracking'], 'docs/entry-revalidation-status.md')
                    self.assertTrue((ROOT / review['tracking']).is_file())
                else:
                    self.assertNotIn('historical_evidence', case)
                    self.assertNotIn('revalidation', case)
            self.assertTrue(case['next_steps'])
            self.assertTrue(case['dependencies'])
            counts[case['scheduling']] = counts.get(case['scheduling'], 0) + 1
            statuses[case['rebuild_acceptance']] = statuses.get(case['rebuild_acceptance'], 0) + 1
            if 'N' in case['verification_layer']:
                self.assertIn(case['scheduling'], ('deferred_native', 'conditional_native'))
        self.assertEqual(counts, {'cloud_only': 75, 'deferred_native': 113, 'conditional_native': 30})
        self.assertEqual(statuses, {'accepted_revalidated': 4, 'pending_revalidation': 214})


if __name__ == '__main__':
    unittest.main()
