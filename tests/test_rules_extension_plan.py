"""Synthetic pinned-format candidates; no native or real-configuration access."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import rules_extension_plan as r
from test_remedy_plans import fixture

RAW = b'# synthetic-only\nprepend: [] # retain comment\nappend: []\ndelete: []\nunknown: keep-SENTINEL\n'
BASE = (b'proxy-groups:\n  - name: approved-group\n    type: select\n    proxies: [node-a]\n'
        b'rules:\n  - DOMAIN,local.test,Local\n  - DOMAIN-SUFFIX,test,Old\n  - MATCH,DIRECT\n')


def inputs(raw=RAW, base=BASE):
    request = fixture()
    request['facts']['versions']['gui'] = '2.5.8'
    request['revisions'] = {'extension': hashlib.sha256(raw).hexdigest(),
                            'effective': hashlib.sha256(base).hexdigest()}
    request['current_revisions'] = deepcopy(request['revisions'])
    binding = {'schema_version': r.SCHEMA, 'operation': 'insert_selected_prepend_rules',
               'target_ref': 'mac-a', 'scope_refs': ['workflow-a'],
               'layer_ref': 'extension', 'base_layer_ref': 'effective',
               'layer_kind': 'owned-profile-rules-extension', 'placement': 'prepend',
               'group_name': 'approved-group',
               'rules': {'rule-a': {'kind': 'DOMAIN', 'domain': 'example.test'}},
               'rule_order': ['rule-a'], 'protected_rule_indexes': [0]}
    return request, binding


class RulesExtensionPlan(unittest.TestCase):
    def compile(self, raw=RAW, base=BASE, **kwargs):
        return r.compile_rules_extension(raw, base, *inputs(raw, base), **kwargs)

    def reject(self, request, binding, code, raw=RAW, base=BASE):
        with self.assertRaisesRegex(r.RulesPlanError, '^' + code + '$'):
            r.compile_rules_extension(raw, base, request, binding)

    def test_exact_insert_and_whole_file_preservation(self):
        material = self.compile().private_material()
        insertion = b"'DOMAIN,example.test,approved-group'"
        expected = RAW.replace(b'prepend: []', b'prepend: [' + insertion + b']')
        self.assertEqual(material['candidate_bytes'], expected)
        offset, before, after = material['byte_insertion']
        self.assertEqual(before, b'')
        self.assertEqual(after, insertion)
        self.assertEqual(RAW[:offset] + after + RAW[offset:], expected)
        self.assertEqual(material['ordered_additions'], (('rule-a', 'DOMAIN,example.test,approved-group'),))
        self.assertEqual([x[2] for x in material['known_priority_overlaps']], [1, 2])
        self.assertEqual(material['candidate_sha256'], hashlib.sha256(expected).hexdigest())
        self.assertEqual(material['matched_rule_refs'], ())
        self.assertEqual(self.compile().preview()['matched_rules'], 0)

    def test_exact_repeat_preserves_bytes_hashes_blockers_and_private_matches(self):
        raw = b'\xef\xbb\xbf' + '# 中文🙂\n'.encode() + RAW.replace(b'[] #', b'[  ] #').replace(b'\n', b'\r\n')
        request, binding = inputs(raw)
        request['intent']['rule_refs'] = ['rule-b', 'rule-a']
        binding['rule_order'] = ['rule-b', 'rule-a']
        binding['rules']['rule-b'] = {'kind': 'DOMAIN-SUFFIX', 'domain': 'other.example'}
        first = r.compile_rules_extension(raw, BASE, request, binding)
        repeated_raw = first.private_material()['candidate_bytes']
        self.reject(request, binding, 'SNAPSHOT_REVISION_MISMATCH', raw=repeated_raw)
        request['revisions']['extension'] = hashlib.sha256(repeated_raw).hexdigest()
        request['current_revisions'] = deepcopy(request['revisions'])
        before = deepcopy((request, binding, repeated_raw, BASE))
        with patch('builtins.open', side_effect=AssertionError('file')), \
                patch('socket.socket', side_effect=AssertionError('network')), \
                patch('subprocess.Popen', side_effect=AssertionError('process')):
            repeated = r.compile_rules_extension(repeated_raw, BASE, request, binding)
        self.assertEqual((request, binding, repeated_raw, BASE), before)
        material, report = repeated.private_material(), repeated.preview()
        self.assertEqual(material['candidate_bytes'], repeated_raw)
        self.assertEqual(material['original_bytes'], repeated_raw)
        self.assertEqual(material['candidate_sha256'], material['original_sha256'])
        self.assertEqual(material['candidate_sha256'], hashlib.sha256(repeated_raw).hexdigest())
        self.assertEqual(material['ordered_additions'], ())
        self.assertIsNone(material['byte_insertion'])
        self.assertEqual(material['matched_rule_refs'], ('rule-b', 'rule-a'))
        self.assertEqual(material['known_priority_overlaps'], first.private_material()['known_priority_overlaps'])
        self.assertEqual(report['status'], 'no_change_in_supplied_snapshot')
        self.assertEqual(report['added_rules'], 0)
        self.assertEqual(report['matched_rules'], 2)
        self.assertFalse(report['apply_supported'])
        self.assertEqual(report['native_acceptance'], 'not_run')
        self.assertEqual(report['authorization'], 'not_required_for_snapshot_observation')
        self.assertEqual(report['blockers'], [code for code in first.preview()['blockers']
                                             if code != 'ACTION_AUTHORIZATION_PENDING'])
        self.assertNotIn('ACTION_AUTHORIZATION_PENDING', report['blockers'])
        for code in r.NATIVE_BLOCKERS:
            self.assertIn(code, report['blockers'])
        self.assertEqual(report['known_base_overlap_count'], first.preview()['known_base_overlap_count'])
        material['matched_rule_refs'] = ()
        self.assertEqual(repeated.private_material()['matched_rule_refs'], ('rule-b', 'rule-a'))
        for private in ('rule-a', 'rule-b', 'example.test', 'approved-group', 'keep-SENTINEL',
                        hashlib.sha256(repeated_raw).hexdigest()):
            self.assertNotIn(private, json.dumps(report) + repr(repeated))
        with self.assertRaises(TypeError):
            pickle.dumps(repeated)
        with self.assertRaises(TypeError):
            json.dumps(repeated)

    def test_exact_single_line_repeat_keeps_original_literal_formatting(self):
        for value in (b"[ 'DOMAIN,example.test,approved-group' ]",
                      b'["DOMAIN,example.test,approved-group"]'):
            raw = RAW.replace(b'prepend: []', b'prepend: ' + value)
            with self.subTest(value=value):
                result = self.compile(raw=raw)
                self.assertEqual(result.private_material()['candidate_bytes'], raw)
                self.assertEqual(result.preview()['status'], 'no_change_in_supplied_snapshot')
                self.assertEqual(result.preview()['matched_rules'], 1)

    def test_nonempty_prepend_does_not_become_a_general_merge(self):
        first = b"'DOMAIN,example.test,approved-group'"
        second = b"'DOMAIN-SUFFIX,other.example,approved-group'"
        for value in (b'[' + first + b']', b'[' + second + b', ' + first + b']',
                      b'[' + first + b', ' + second + b', ' + first + b']',
                      b"['DOMAIN,unrelated.test,approved-group']",
                      b"['DOMAIN,example.test,Other', " + second + b']',
                      b"['DOMAIN,EXAMPLE.TEST,approved-group', " + second + b']',
                      b"['DOMAIN, example.test,approved-group', " + second + b']',
                      b'[\n' + first + b', ' + second + b'\n]',
                      b'\n  - ' + first + b'\n  - ' + second):
            raw = RAW.replace(b'prepend: []', b'prepend: ' + value)
            request, binding = inputs(raw)
            request['intent']['rule_refs'].append('rule-b')
            binding['rule_order'].append('rule-b')
            binding['rules']['rule-b'] = {'kind': 'DOMAIN-SUFFIX', 'domain': 'other.example'}
            with self.subTest(value=value):
                self.reject(request, binding, 'NONEMPTY_PREPEND_UNSUPPORTED', raw=raw)

    def test_exact_repeat_retains_base_group_protected_and_duplicate_guards(self):
        repeated = self.compile().private_material()['candidate_bytes']
        cases = [
            (BASE.replace(b'name: approved-group', b'name: missing-group'), [0],
             'EGRESS_GROUP_MISSING_OR_AMBIGUOUS'),
            (BASE.replace(b'    type: select', b'  - name: approved-group\n    type: select'), [0],
             'EGRESS_GROUP_MISSING_OR_AMBIGUOUS'),
            (BASE, [1], 'PROTECTED_RULE_PRIORITY_CONFLICT'),
            (BASE, [2], 'PROTECTED_RULE_PRIORITY_CONFLICT'),
            (BASE, [True], 'INVALID_PROTECTED_RULE_INDEXES'),
            (BASE.replace(b'DOMAIN,local.test,Local', b'RULE-SET,organization,Local'), [0],
             'PROTECTED_RULE_TYPE_UNSUPPORTED'),
            (BASE.replace(b'DOMAIN,local.test,Local', b'DOMAIN,EXAMPLE.TEST.,Other'), [],
             'RULE_SELECTOR_ALREADY_PRESENT'),
            (BASE + b'rules: []\n', [0], 'AMBIGUOUS_MAPPING'),
        ]
        for base, protected, code in cases:
            request, binding = inputs(repeated, base)
            binding['protected_rule_indexes'] = protected
            with self.subTest(code=code, protected=protected):
                self.reject(request, binding, code, raw=repeated, base=base)
        raw = repeated.replace(b'append: []', b"append: ['domain, EXAMPLE.TEST. ,Other']")
        request, binding = inputs(raw)
        self.reject(request, binding, 'RULE_SELECTOR_ALREADY_PRESENT', raw=raw)
        raw = repeated.replace(b'delete: []', b"delete: ['MATCH,DIRECT']")
        request, binding = inputs(raw)
        self.reject(request, binding, 'DELETE_SEQUENCE_UNSUPPORTED', raw=raw)

    def test_repeat_match_cannot_skip_other_invalid_or_overlapping_selection(self):
        raw = self.compile().private_material()['candidate_bytes']
        for other, code in [({'kind': 'DOMAIN', 'domain': 'bad..test'}, 'INVALID_SELECTED_RULE'),
                            ({'kind': 'DOMAIN-SUFFIX', 'domain': 'example.test'}, 'OVERLAPPING_SELECTED_RULES')]:
            for order in (['rule-a', 'rule-b'], ['rule-b', 'rule-a']):
                request, binding = inputs(raw)
                request['intent']['rule_refs'] = order
                binding['rule_order'] = order[:]
                binding['rules']['rule-b'] = other
                before = deepcopy((request, binding))
                with self.subTest(code=code, order=order):
                    self.reject(request, binding, code, raw=raw)
                self.assertEqual((request, binding), before)

    def test_exact_repeat_retains_revisions_semantics_cancellation_and_deadline(self):
        raw = self.compile().private_material()['candidate_bytes']
        for change in ('extension', 'effective', 'stale', 'version', 'protected', 'cancel'):
            request, binding = inputs(raw)
            if change in ('extension', 'effective'):
                request['revisions'][change] = '0' * 64
                request['current_revisions'] = deepcopy(request['revisions'])
            if change == 'stale': request['current_revisions']['extension'] = '0' * 64
            if change == 'version': request['facts']['versions']['gui'] = '2.5.7'
            if change == 'protected': request['facts']['rules']['protected_priority_preserved'] = 'unknown'
            if change == 'cancel': request['cancelled'] = True
            with self.subTest(change=change), self.assertRaises(r.RulesPlanError):
                r.compile_rules_extension(raw, BASE, request, binding)
        with self.assertRaisesRegex(r.RulesPlanError, '^CANCELLED$'):
            self.compile(raw=raw, cancelled=lambda: True)
        with patch.object(r.time, 'monotonic', side_effect=[0, 6]):
            with self.assertRaisesRegex(r.RulesPlanError, '^DEADLINE_EXCEEDED$'):
                self.compile(raw=raw)

    def test_private_public_and_no_authority(self):
        result = self.compile()
        report = result.preview()
        self.assertFalse(report['apply_supported'])
        self.assertEqual(report['operation'], 'insert_selected_prepend_rules')
        self.assertEqual(report['known_base_overlap_count'], 2)
        self.assertEqual(report['protected_index_coverage'], 'caller_declared_unverified')
        self.assertEqual(report['authorization'], 'pending')
        self.assertEqual(report['blockers'], list(r.NATIVE_BLOCKERS) + [
            'EFFECTIVE_RULE_PRIORITY_UNVERIFIED', 'BASE_RULE_GRAPH_UNVERIFIED',
            'GROUP_GRAPH_UNVERIFIED', 'PROTECTED_RULE_COVERAGE_UNVERIFIED',
            'LATER_MERGE_SCRIPT_EFFECTS_UNVERIFIED', 'ACTION_AUTHORIZATION_PENDING'])
        for blocker in ('BASE_RULE_GRAPH_UNVERIFIED', 'EFFECTIVE_RULE_PRIORITY_UNVERIFIED',
                        'NATIVE_ACCEPTANCE_NOT_RUN', 'ACTION_AUTHORIZATION_PENDING'):
            self.assertIn(blocker, report['blockers'])
        for private in ('example.test', 'approved-group', 'keep-SENTINEL', hashlib.sha256(RAW).hexdigest()):
            self.assertNotIn(private, json.dumps(report) + repr(result))
        with self.assertRaises(TypeError):
            pickle.dumps(result)
        with self.assertRaises(TypeError):
            json.dumps(result)

    def test_utf8_bom_crlf_comments_and_empty_whitespace(self):
        raw = b'\xef\xbb\xbf' + '# 中文🙂\n'.encode() + RAW.replace(b'[] #', b'[  ] #').replace(b'\n', b'\r\n')
        candidate = self.compile(raw=raw).private_material()['candidate_bytes']
        self.assertEqual(candidate, raw.replace(b'prepend: [', b"prepend: ['DOMAIN,example.test,approved-group'"))

    def test_explicit_multiple_rule_order(self):
        request, binding = inputs()
        request['intent']['rule_refs'] = ['rule-b', 'rule-a']
        binding['rule_order'] = ['rule-b', 'rule-a']
        binding['rules']['rule-b'] = {'kind': 'DOMAIN-SUFFIX', 'domain': 'other.example'}
        result = r.compile_rules_extension(RAW, BASE, request, binding)
        self.assertIn(b"['DOMAIN-SUFFIX,other.example,approved-group', 'DOMAIN,example.test,approved-group']",
                      result.private_material()['candidate_bytes'])
        self.assertEqual(result.preview()['added_rules'], 2)
        binding['rule_order'].reverse()
        self.reject(request, binding, 'INVALID_RULE_SELECTION')

    def test_prepend_placement_operation_and_exact_binding_required(self):
        for key, value in [('placement', 'append'), ('operation', 'replace_existing_rule'),
                           ('layer_kind', 'owned-profile-extension')]:
            request, binding = inputs()
            binding[key] = value
            self.reject(request, binding, 'EXPLICIT_PREPEND_OPERATION_REQUIRED')
        request, binding = inputs()
        del binding['protected_rule_indexes']
        self.reject(request, binding, 'INVALID_BINDING')
        request, binding = inputs()
        binding['approved'] = True
        self.reject(request, binding, 'INVALID_BINDING')

    def test_revision_target_version_and_semantic_gates(self):
        request, binding = inputs()
        binding['target_ref'] = 'other'
        self.reject(request, binding, 'TARGET_OR_SCOPE_MISMATCH')
        request, binding = inputs()
        request['revisions']['effective'] = '0' * 64
        request['current_revisions'] = deepcopy(request['revisions'])
        self.reject(request, binding, 'SNAPSHOT_REVISION_MISMATCH')
        request, binding = inputs()
        request['facts']['versions']['gui'] = '2.5.7'
        self.reject(request, binding, 'UNSUPPORTED_PRODUCT_OR_VERSION')
        request, binding = inputs()
        request['facts']['rules']['protected_priority_preserved'] = 'unknown'
        self.reject(request, binding, 'SEMANTIC_PLAN_BLOCKED')
        request, binding = inputs()
        request['facts']['groups']['node-a']['kind'] = 'direct'
        self.reject(request, binding, 'SEMANTIC_PLAN_BLOCKED')

    def test_nonempty_prepend_delete_and_nonliteral_empty_rejected(self):
        for raw, code in [(RAW.replace(b'prepend: []', b"prepend: ['DOMAIN,x.test,Old']"), 'NONEMPTY_PREPEND_UNSUPPORTED'),
                          (RAW.replace(b'delete: []', b"delete: ['MATCH,DIRECT']"), 'DELETE_SEQUENCE_UNSUPPORTED'),
                          (RAW.replace(b'prepend: []', b'prepend: [\n]'), 'EMPTY_INLINE_PREPEND_REQUIRED')]:
            request, binding = inputs(raw)
            self.reject(request, binding, code, raw=raw)

    def test_preserves_nonempty_append_and_unknown_fields(self):
        raw = RAW.replace(b'append: []', b"append: ['DOMAIN,other.example,Other', 'IP-CIDR,192.0.2.0/24,Other']")
        candidate = self.compile(raw=raw)
        self.assertIn(b"append: ['DOMAIN,other.example,Other', 'IP-CIDR,192.0.2.0/24,Other']",
                      candidate.private_material()['candidate_bytes'])
        self.assertEqual(candidate.preview()['unknown_base_or_append_rule_count'], 1)

    def test_known_append_overlap_has_explicit_layer_and_index(self):
        raw = RAW.replace(b'append: []', b"append: ['DOMAIN-SUFFIX,test,Other']")
        result = self.compile(raw=raw)
        self.assertEqual(result.preview()['known_append_overlap_count'], 1)
        self.assertIn(('rule-a', 'append', 0, 'DOMAIN-SUFFIX,test,Other'),
                      result.private_material()['known_priority_overlaps'])

    def test_duplicate_selectors_in_base_or_append(self):
        for value in ('DOMAIN,example.test,Other', 'domain, EXAMPLE.TEST. ,Other',
                      'DOMAIN,example.test,Other,no-resolve'):
            base = BASE.replace(b'DOMAIN,local.test,Local', value.encode())
            request, binding = inputs(base=base)
            binding['protected_rule_indexes'] = []
            self.reject(request, binding, 'RULE_SELECTOR_ALREADY_PRESENT', base=base)
            raw = RAW.replace(b'append: []', ('append: [' + json.dumps(value) + ']').encode())
            request, binding = inputs(raw=raw)
            self.reject(request, binding, 'RULE_SELECTOR_ALREADY_PRESENT', raw=raw)

    def test_selected_overlap_and_invalid_domains(self):
        request, binding = inputs()
        request['intent']['rule_refs'].append('rule-b')
        binding['rule_order'].append('rule-b')
        binding['rules']['rule-b'] = {'kind': 'DOMAIN-SUFFIX', 'domain': 'test'}
        self.reject(request, binding, 'OVERLAPPING_SELECTED_RULES')
        for domain in ('bad..test', 'a' * 64 + '.test', '-bad.test', 'bad.test-',
                       'x.test,Other', 'x.test\nsecret', 'é.test', '*.test'):
            request, binding = inputs()
            binding['rules']['rule-a']['domain'] = domain
            self.reject(request, binding, 'INVALID_SELECTED_RULE')

    def test_protected_scope_overlap_match_and_unknown_fail_closed(self):
        for index in (1, 2):
            request, binding = inputs()
            binding['protected_rule_indexes'] = [index]
            self.reject(request, binding, 'PROTECTED_RULE_PRIORITY_CONFLICT')
        base = BASE.replace(b'DOMAIN,local.test,Local', b'RULE-SET,organization,Local')
        request, binding = inputs(base=base)
        self.reject(request, binding, 'PROTECTED_RULE_TYPE_UNSUPPORTED', base=base)
        request, binding = inputs()
        binding['rules']['rule-a'] = {'kind': 'DOMAIN-SUFFIX', 'domain': 'local.test'}
        self.reject(request, binding, 'PROTECTED_RULE_PRIORITY_CONFLICT')

    def test_empty_declared_protected_list_does_not_prove_absence(self):
        request, binding = inputs()
        binding['protected_rule_indexes'] = []
        result = r.compile_rules_extension(RAW, BASE, request, binding)
        self.assertIn('PROTECTED_RULE_COVERAGE_UNVERIFIED', result.preview()['blockers'])

    def test_group_binding_missing_or_ambiguous(self):
        for base in (BASE.replace(b'name: approved-group', b'name: other-group'),
                     BASE.replace(b'    type: select', b'  - name: approved-group\n    type: select')):
            request, binding = inputs(base=base)
            self.reject(request, binding, 'EGRESS_GROUP_MISSING_OR_AMBIGUOUS', base=base)

    def test_unsupported_yaml_and_missing_parser(self):
        for raw in (RAW + b'prepend: []\n', RAW.replace(b'prepend: []', b'prepend: &rules []'),
                    RAW.replace(b'prepend: []', b'prepend: !!seq []')):
            with self.assertRaises(r.RulesPlanError):
                self.compile(raw=raw)
        with patch.object(r.config, 'yaml', None):
            with self.assertRaisesRegex(r.RulesPlanError, '^PARSER_UNAVAILABLE$'):
                self.compile()

    def test_no_io_no_input_mutation_and_atomic_rejection(self):
        request, binding = inputs()
        original = deepcopy((request, binding, RAW, BASE))
        with patch('builtins.open', side_effect=AssertionError('file')), \
                patch('socket.socket', side_effect=AssertionError('network')), \
                patch('subprocess.Popen', side_effect=AssertionError('process')):
            r.compile_rules_extension(RAW, BASE, request, binding)
        self.assertEqual((request, binding, RAW, BASE), original)
        request['intent']['rule_refs'].append('rule-b')
        binding['rule_order'].append('rule-b')
        binding['rules']['rule-b'] = {'kind': 'DOMAIN', 'domain': 'bad..test'}
        before = deepcopy((request, binding))
        self.reject(request, binding, 'INVALID_SELECTED_RULE')
        self.assertEqual((request, binding), before)

    def test_cancellation_deadlines_and_budgets(self):
        with patch.object(r, 'compile_plan', side_effect=AssertionError('compile')):
            with self.assertRaisesRegex(r.RulesPlanError, '^CANCELLED$'):
                self.compile(cancelled=lambda: True)
            with patch.object(r.time, 'monotonic', side_effect=[0, 6]):
                with self.assertRaisesRegex(r.RulesPlanError, '^DEADLINE_EXCEEDED$'):
                    self.compile()
        for value in (True, float('nan'), 0, 61):
            with self.assertRaisesRegex(r.RulesPlanError, '^INVALID_DEADLINE$'):
                self.compile(max_seconds=value)
        base = BASE.split(b'rules:')[0] + b'rules:\n' + b'  - MATCH,DIRECT\n' * 2049
        request, binding = inputs(base=base)
        binding['protected_rule_indexes'] = []
        self.reject(request, binding, 'PRIORITY_ANALYSIS_BUDGET_EXCEEDED', base=base)


if __name__ == '__main__':
    unittest.main()
