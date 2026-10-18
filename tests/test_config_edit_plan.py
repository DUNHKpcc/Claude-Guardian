"""Synthetic private snapshots only; no actual configuration or native checks."""
import builtins
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pickle
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import config_edit_plan as c
from test_remedy_plans import fixture

RAW = (b'# synthetic secret-SENTINEL\nsecret: secret-SENTINEL\n'
       b'proxy-groups:\n  - name: approved-group\n    type: select\n    proxies: [node-a]\n'
       b'rules:\n  - DOMAIN,example.test,Old # keep comment\n'
       b'  - DOMAIN-SUFFIX,example.org,Old\n  - MATCH,DIRECT\n'
       b'unknown-field: {nested: [true, 12, untouched]}\n')


def inputs(raw=RAW):
    request = fixture()
    request['revisions']['extension'] = hashlib.sha256(raw).hexdigest()
    request['current_revisions'] = deepcopy(request['revisions'])
    binding = {'schema_version': 'guardian-config-edit-binding/0.1',
               'target_ref': 'mac-a', 'scope_refs': ['workflow-a'],
               'layer_ref': 'extension', 'layer_kind': 'owned-profile-extension',
               'group_name': 'approved-group',
               'rules': {'rule-a': {'index': 0, 'expected': 'DOMAIN,example.test,Old'}}}
    return request, binding


class ConfigEditTests(unittest.TestCase):
    def compile(self, raw=RAW):
        return c.compile_edit_plan(raw, *inputs(raw))

    def rejects(self, raw, code=None):
        with self.assertRaises(c.EditPlanError) as caught:
            self.compile(raw)
        if code:
            self.assertEqual(str(caught.exception), code)
        self.assertNotIn('secret-SENTINEL', str(caught.exception))

    def test_exact_bytes_and_hashes(self):
        result = self.compile()
        material = result.private_material()
        expected = RAW.replace(b'DOMAIN,example.test,Old', b'DOMAIN,example.test,approved-group')
        self.assertEqual(material['candidate_bytes'], expected)
        self.assertEqual(material['original_bytes'], RAW)
        self.assertEqual(material['candidate_sha256'], hashlib.sha256(expected).hexdigest())
        self.assertEqual(material['declared_binding'][0], 'mac-a')
        self.assertFalse(result.preview()['apply_supported'])
        self.assertEqual(len(result.preview()['blockers']), 4)
        self.assertEqual(result.preview()['authorization'], 'pending')
        self.assertEqual(result.preview()['blockers'],
                         sorted(c._ALLOWED_BLOCKERS) + ['ACTION_AUTHORIZATION_PENDING'])

    def test_unicode_bom_crlf_offsets_and_trailing_comment(self):
        raw = b'\xef\xbb\xbf' + '# 非英文🙂\n'.encode() + RAW.replace(b'\n', b'\r\n')
        result = self.compile(raw).private_material()['candidate_bytes']
        self.assertEqual(result, raw.replace(b'DOMAIN,example.test,Old', b'DOMAIN,example.test,approved-group'))

    def test_multiple_nonoverlapping_edits(self):
        request, binding = inputs()
        request['intent']['rule_refs'].append('rule-b')
        binding['rules']['rule-b'] = {'index': 1, 'expected': 'DOMAIN-SUFFIX,example.org,Old'}
        result = c.compile_edit_plan(RAW, request, binding)
        self.assertEqual(result.preview()['changed_rules'], 2)
        self.assertEqual(result.private_material()['candidate_bytes'], RAW.replace(b',Old', b',approved-group'))

    def test_public_privacy_and_serialization(self):
        result = self.compile()
        public = json.dumps(result.preview()) + repr(result)
        for private in ('secret-SENTINEL', 'example.test', 'approved-group', hashlib.sha256(RAW).hexdigest()):
            self.assertNotIn(private, public)
        with self.assertRaises(TypeError):
            json.dumps(result)
        with self.assertRaises(TypeError):
            pickle.dumps(result)

    def test_no_io_and_no_mutation(self):
        request, binding = inputs()
        before = deepcopy((request, binding))
        with patch.object(builtins, 'open', side_effect=AssertionError('file')), \
                patch.object(socket, 'socket', side_effect=AssertionError('network')), \
                patch.object(subprocess, 'Popen', side_effect=AssertionError('process')):
            c.compile_edit_plan(RAW, request, binding)
        self.assertEqual((request, binding), before)

    def test_private_diff_reconstructs_candidate_using_original_byte_offsets(self):
        raw = b'\xef\xbb\xbf' + '# 中文🙂\n'.encode() + RAW.replace(b'\n', b'\r\n')
        request, binding = inputs(raw)
        request['intent']['rule_refs'].append('rule-b')
        binding['rules']['rule-b'] = {'index': 1, 'expected': 'DOMAIN-SUFFIX,example.org,Old'}
        result = c.compile_edit_plan(raw, request, binding)
        material = result.private_material()
        edits = material['policy_token_edits']
        self.assertIsInstance(edits, tuple)
        self.assertEqual(len(edits), 2)
        self.assertEqual(edits, tuple(sorted(edits)))
        rebuilt = raw
        for start, end, before, after in reversed(edits):
            self.assertEqual(raw[start:end], before)
            self.assertEqual(before, b'Old')
            self.assertEqual(after, b'approved-group')
            rebuilt = rebuilt[:start] + after + rebuilt[end:]
        self.assertEqual(rebuilt, material['candidate_bytes'])
        material['policy_token_edits'] = ()
        self.assertEqual(result.private_material()['policy_token_edits'], edits)
        self.assertNotIn('policy_token_edits', result.preview())

    def test_invalid_selected_domain_labels_are_rejected(self):
        for domain in ('example..test', 'example.-test', 'example.test-', 'example-.test',
                       'a' * 64 + '.test', 'a.' * 126 + 'aa'):
            raw = RAW.replace(b'example.test', domain.encode())
            request, binding = inputs(raw)
            binding['rules']['rule-a']['expected'] = 'DOMAIN,' + domain + ',Old'
            with self.subTest(domain=domain), self.assertRaisesRegex(
                    c.EditPlanError, '^AMBIGUOUS_OR_UNSUPPORTED_RULE$'):
                c.compile_edit_plan(raw, request, binding)

    def test_earlier_covering_rules_conflict_with_selected_rule(self):
        for earlier in ('MATCH,DIRECT', 'DOMAIN-SUFFIX,test,Other',
                        'DOMAIN-SUFFIX,EXAMPLE.TEST.,Other',
                        ' DOMAIN-SUFFIX , test. , Other '):
            raw = RAW.replace(b'rules:\n', b'rules:\n  - "' + earlier.encode() + b'"\n')
            request, binding = inputs(raw)
            binding['rules']['rule-a']['index'] = 1
            with self.subTest(earlier=earlier), self.assertRaisesRegex(
                    c.EditPlanError, '^SELECTED_RULE_SHADOWED$'):
                c.compile_edit_plan(raw, request, binding)

    def test_suffix_shadowing_checks_label_boundaries_and_order(self):
        for earlier in ('DOMAIN-SUFFIX,ample.test,Other',
                        'DOMAIN,other.test,Other', 'DOMAIN,child.example.test,Other'):
            raw = RAW.replace(b'rules:\n', b'rules:\n  - ' + earlier.encode() + b'\n')
            request, binding = inputs(raw)
            binding['rules']['rule-a']['index'] = 1
            result = c.compile_edit_plan(raw, request, binding)
            self.assertFalse(result.preview()['apply_supported'])
        # A later covering rule does not shadow the selected earlier rule.
        self.compile(RAW.replace(b'MATCH,DIRECT', b'DOMAIN-SUFFIX,test,Other'))

    def test_unresolved_earlier_rules_do_not_certify_first_match(self):
        for earlier in ('RULE-SET,external-rules,Other',
                        'DOMAIN-KEYWORD,example,Other',
                        'DOMAIN-SUFFIX,test,Other,unsupported-modifier'):
            raw = RAW.replace(b'rules:\n', b'rules:\n  - ' + earlier.encode() + b'\n')
            request, binding = inputs(raw)
            binding['rules']['rule-a']['index'] = 1
            preview = c.compile_edit_plan(raw, request, binding).preview()
            self.assertEqual(preview['native_compatibility'], 'unknown')
            self.assertEqual(preview['native_acceptance'], 'not_run')
            self.assertFalse(preview['apply_supported'])
            self.assertIn('NATIVE_ACCEPTANCE_NOT_RUN', preview['blockers'])

    def test_later_edit_rejection_leaves_all_inputs_unchanged(self):
        raw = RAW.replace(b'  - DOMAIN-SUFFIX,example.org,Old',
                          b'  - DOMAIN-SUFFIX,org,Other\n  - DOMAIN-SUFFIX,example.org,Old')
        request, binding = inputs(raw)
        request['intent']['rule_refs'].append('rule-b')
        binding['rules']['rule-b'] = {'index': 2, 'expected': 'DOMAIN-SUFFIX,example.org,Old'}
        original = deepcopy((raw, request, binding))
        with self.assertRaisesRegex(c.EditPlanError, '^SELECTED_RULE_SHADOWED$'):
            c.compile_edit_plan(raw, request, binding)
        self.assertEqual((raw, request, binding), original)

    def test_valid_domain_label_and_name_limits(self):
        for domain in ('a' * 63 + '.test', '.'.join(['a' * 63] * 3 + ['b' * 61]),
                       'example-test.test', 'localhost'):
            raw = RAW.replace(b'example.test', domain.encode())
            request, binding = inputs(raw)
            binding['rules']['rule-a']['expected'] = 'DOMAIN,' + domain + ',Old'
            result = c.compile_edit_plan(raw, request, binding)
            self.assertEqual(result.preview()['changed_rules'], 1)

    def test_suffix_selection_is_shadowed_by_parent_suffix(self):
        raw = RAW.replace(b'rules:\n', b'rules:\n  - DOMAIN-SUFFIX,org,Other\n')
        request, binding = inputs(raw)
        binding['rules']['rule-a'] = {'index': 2, 'expected': 'DOMAIN-SUFFIX,example.org,Old'}
        with self.assertRaisesRegex(c.EditPlanError, '^SELECTED_RULE_SHADOWED$'):
            c.compile_edit_plan(raw, request, binding)

    def test_binding_guards(self):
        for field, value in [('target_ref', 'other'), ('scope_refs', ['other']),
                             ('layer_ref', 'unknown'), ('layer_kind', 'generated_config'),
                             ('group_name', 'injected,#\n'), ('group_name', 'Other')]:
            request, binding = inputs()
            binding[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(c.EditPlanError):
                c.compile_edit_plan(RAW, request, binding)
        request, binding = inputs()
        binding['authorized'] = True
        with self.assertRaises(c.EditPlanError):
            c.compile_edit_plan(RAW, request, binding)

    def test_stale_cancelled_unknown_version_and_semantic_blockers(self):
        for change in ('stale', 'cancel', 'version', 'control', 'template', 'revision'):
            request, binding = inputs()
            if change == 'stale': request['current_revisions']['extension'] = 'a' * 64
            if change == 'cancel': request['cancelled'] = True
            if change == 'version': request['facts']['versions']['core'] = 'unknown'
            if change == 'control': request['facts']['control']['preserved'] = 'no'
            if change == 'template': request['template'] = 'tun-rule'
            if change == 'revision': request['revisions']['extension'] = 'a' * 64
            with self.subTest(change=change), self.assertRaises(c.EditPlanError):
                c.compile_edit_plan(RAW, request, binding)

    def test_parser_rejections(self):
        for extra in (b'x: 1\nx: 2\n', b'x: {nested: 1, nested: 2}\n',
                      b'x: &a secret-SENTINEL\ny: *a\n', b'x: !!str secret-SENTINEL\n',
                      b'x: {<<: value}\n', b'---\nx: 2\n', b'x: [\n'):
            with self.subTest(extra=extra): self.rejects(RAW + extra)
        self.rejects(b'%YAML 1.2\n---\n' + RAW)
        self.rejects(b'\xff' + RAW)

    def test_missing_parser_and_size_budget(self):
        with patch.object(c, 'yaml', None):
            self.rejects(RAW, 'PARSER_UNAVAILABLE')
        with patch.object(c, 'MAX_BYTES', 10):
            self.rejects(RAW, 'INVALID_OR_OVERSIZED_SNAPSHOT')

    def test_quoted_and_multiline_rule_rejected(self):
        for value in (b'"DOMAIN,example.test,Old"', b"'DOMAIN,example.test,Old'", b'>\n      DOMAIN,example.test,Old'):
            self.rejects(RAW.replace(b'DOMAIN,example.test,Old', value))

    def test_duplicate_rules_and_groups_rejected(self):
        self.rejects(RAW.replace(b'  - MATCH,DIRECT', b'  - DOMAIN,example.test,Old'))
        self.rejects(RAW.replace(b'rules:\n', b'  - name: approved-group\nrules:\n'))

    def test_duplicate_selector_with_other_policy_rejected(self):
        self.rejects(RAW.replace(b'  - MATCH,DIRECT', b'  - DOMAIN,example.test,Other'))

    def test_equivalent_selector_spellings_rejected(self):
        for alternate in (b'DOMAIN,EXAMPLE.TEST,Other', b'DOMAIN, example.test, Other',
                          b'DOMAIN,example.test.,Other', b'DOMAIN , Example.Test. , Other',
                          b'"DOMAIN, EXAMPLE.TEST., Other"'):
            with self.subTest(alternate=alternate):
                self.rejects(RAW.replace(b'MATCH,DIRECT', alternate),
                             'AMBIGUOUS_OR_UNSUPPORTED_RULE')

    def test_flow_and_resource_limits(self):
        self.rejects(RAW.replace(b'rules:\n  - DOMAIN,example.test,Old # keep comment\n'
                                b'  - DOMAIN-SUFFIX,example.org,Old\n  - MATCH,DIRECT',
                                b'rules: ["DOMAIN,example.test,Old"]'))
        self.rejects(RAW + b'deep: ' + b'[' * 49 + b'0' + b']' * 49 + b'\n',
                     'YAML_BUDGET_EXCEEDED')
        with patch.object(c, 'MAX_NODES', 5):
            self.rejects(RAW, 'YAML_BUDGET_EXCEEDED')

    def test_changed_index_noop_and_unsupported_rule(self):
        for index, expected in [(1, 'DOMAIN,example.test,Old'), (True, 'DOMAIN,example.test,Old'),
                                (2, 'MATCH,DIRECT')]:
            request, binding = inputs()
            binding['rules']['rule-a'] = {'index': index, 'expected': expected}
            with self.assertRaises(c.EditPlanError): c.compile_edit_plan(RAW, request, binding)
        raw = RAW.replace(b',Old', b',approved-group')
        request, binding = inputs(raw)
        binding['rules']['rule-a']['expected'] = 'DOMAIN,example.test,approved-group'
        result = c.compile_edit_plan(raw, request, binding)
        material, report = result.private_material(), result.preview()
        self.assertEqual(material['candidate_bytes'], raw)
        self.assertEqual(material['original_bytes'], raw)
        self.assertEqual(material['original_sha256'], material['candidate_sha256'])
        self.assertEqual(material['policy_token_edits'], ())
        self.assertEqual(material['changed_rule_refs'], ())
        self.assertEqual(material['matched_rule_refs'], ('rule-a',))
        self.assertEqual(report['status'], 'no_change_in_supplied_snapshot')
        self.assertEqual(report['changed_rules'], 0)
        self.assertEqual(report['matched_rules'], 1)
        self.assertFalse(report['apply_supported'])
        self.assertEqual(report['native_acceptance'], 'not_run')
        self.assertEqual(report['authorization'], 'not_required_for_snapshot_observation')
        self.assertEqual(report['blockers'], sorted(c._ALLOWED_BLOCKERS))
        self.assertNotIn('ACTION_AUTHORIZATION_PENDING', report['blockers'])

    def test_fresh_replanning_is_byte_identical_private_and_io_free(self):
        raw = b'\xef\xbb\xbf' + '# 中文🙂\n'.encode() + RAW.replace(b'\n', b'\r\n')
        request, binding = inputs(raw)
        request['intent']['rule_refs'].append('rule-b')
        binding['rules']['rule-b'] = {'index': 1, 'expected': 'DOMAIN-SUFFIX,example.org,Old'}
        first = c.compile_edit_plan(raw, request, binding)
        repeated_raw = first.private_material()['candidate_bytes']
        with self.assertRaisesRegex(c.EditPlanError, '^SNAPSHOT_REVISION_MISMATCH$'):
            c.compile_edit_plan(repeated_raw, request, binding)
        request['revisions']['extension'] = hashlib.sha256(repeated_raw).hexdigest()
        request['current_revisions'] = deepcopy(request['revisions'])
        for item in binding['rules'].values():
            item['expected'] = item['expected'].replace(',Old', ',approved-group')
        before = deepcopy((request, binding))
        with patch.object(builtins, 'open', side_effect=AssertionError('file')), \
                patch.object(socket, 'socket', side_effect=AssertionError('network')), \
                patch.object(subprocess, 'Popen', side_effect=AssertionError('process')):
            repeated = c.compile_edit_plan(repeated_raw, request, binding)
        self.assertEqual((request, binding), before)
        material, report = repeated.private_material(), repeated.preview()
        self.assertEqual(material['candidate_bytes'], repeated_raw)
        self.assertEqual(material['original_sha256'], material['candidate_sha256'])
        self.assertEqual(material['policy_token_edits'], ())
        self.assertEqual(material['matched_rule_refs'], ('rule-a', 'rule-b'))
        self.assertEqual(material['changed_rule_refs'], ())
        self.assertEqual(report['matched_rules'], 2)
        self.assertEqual(report['changed_rules'], 0)
        self.assertEqual(report['status'], 'no_change_in_supplied_snapshot')
        self.assertFalse(report['apply_supported'])
        self.assertEqual(report['native_acceptance'], 'not_run')
        self.assertEqual(report['authorization'], 'not_required_for_snapshot_observation')
        self.assertEqual(report['blockers'], [code for code in first.preview()['blockers']
                                             if code != 'ACTION_AUTHORIZATION_PENDING'])
        self.assertNotIn('ACTION_AUTHORIZATION_PENDING', report['blockers'])
        material['matched_rule_refs'] = ()
        self.assertEqual(repeated.private_material()['matched_rule_refs'], ('rule-a', 'rule-b'))
        for private in ('rule-a', 'rule-b', 'example.test', 'approved-group', 'secret-SENTINEL',
                        hashlib.sha256(repeated_raw).hexdigest()):
            self.assertNotIn(private, json.dumps(report) + repr(repeated))
        with self.assertRaises(TypeError):
            pickle.dumps(repeated)
        with self.assertRaises(TypeError):
            json.dumps(repeated)

    def test_mixed_matches_and_edits_preserve_order_and_exact_spans(self):
        raw = RAW.replace(b'DOMAIN,example.test,Old', b'DOMAIN,example.test,approved-group')
        for order in (['rule-a', 'rule-b'], ['rule-b', 'rule-a']):
            request, binding = inputs(raw)
            request['intent']['rule_refs'] = order
            binding['rules']['rule-a']['expected'] = 'DOMAIN,example.test,approved-group'
            binding['rules']['rule-b'] = {'index': 1, 'expected': 'DOMAIN-SUFFIX,example.org,Old'}
            with self.subTest(order=order):
                result = c.compile_edit_plan(raw, request, binding)
                report, material = result.preview(), result.private_material()
                self.assertEqual(report['status'], 'candidate_only_blocked')
                self.assertEqual(report['matched_rules'], 1)
                self.assertEqual(report['changed_rules'], 1)
                self.assertEqual(material['matched_rule_refs'], ('rule-a',))
                self.assertEqual(material['changed_rule_refs'], ('rule-b',))
                self.assertEqual(material['candidate_bytes'], raw.replace(b',Old', b',approved-group'))
                self.assertEqual(len(material['policy_token_edits']), 1)
                start, end, before, after = material['policy_token_edits'][0]
                self.assertEqual(raw[start:end], before)
                self.assertEqual(before, b'Old')
                self.assertEqual(after, b'approved-group')
                self.assertEqual(raw[:start] + after + raw[end:], material['candidate_bytes'])
                self.assertFalse(report['apply_supported'])
                self.assertEqual(report['native_acceptance'], 'not_run')
                self.assertEqual(report['authorization'], 'pending')
                self.assertEqual(report['blockers'],
                                 sorted(c._ALLOWED_BLOCKERS) + ['ACTION_AUTHORIZATION_PENDING'])

    def test_matching_selection_cannot_hide_later_or_earlier_invalid_selection(self):
        correct = RAW.replace(b'DOMAIN,example.test,Old', b'DOMAIN,example.test,approved-group')
        cases = [
            (correct, {'index': 0, 'expected': 'DOMAIN,example.test,approved-group'},
             'AMBIGUOUS_RULE_SELECTION'),
            (correct, {'index': 1, 'expected': 'DOMAIN-SUFFIX,example.org,changed'},
             'UNSUPPORTED_OR_CHANGED_RULE'),
            (correct.replace(b'example.org', b'bad..org'),
             {'index': 1, 'expected': 'DOMAIN-SUFFIX,bad..org,Old'},
             'AMBIGUOUS_OR_UNSUPPORTED_RULE'),
            (correct.replace(b'  - DOMAIN-SUFFIX,example.org,Old',
                             b'  - DOMAIN-SUFFIX,org,Other\n  - DOMAIN-SUFFIX,example.org,Old'),
             {'index': 2, 'expected': 'DOMAIN-SUFFIX,example.org,Old'},
             'SELECTED_RULE_SHADOWED'),
        ]
        for raw, other, code in cases:
            for order in (['rule-a', 'rule-b'], ['rule-b', 'rule-a']):
                request, binding = inputs(raw)
                request['intent']['rule_refs'] = order
                binding['rules']['rule-a']['expected'] = 'DOMAIN,example.test,approved-group'
                binding['rules']['rule-b'] = other
                before = deepcopy((request, binding))
                with self.subTest(code=code, order=order), self.assertRaisesRegex(c.EditPlanError, '^' + code + '$'):
                    c.compile_edit_plan(raw, request, binding)
                self.assertEqual((request, binding), before)

    def test_matching_rules_retain_duplicate_shadow_group_and_syntax_guards(self):
        correct = RAW.replace(b',Old', b',approved-group')
        cases = [
            (correct.replace(b'MATCH,DIRECT', b'DOMAIN,EXAMPLE.TEST.,Other'), 0,
             'AMBIGUOUS_OR_UNSUPPORTED_RULE'),
            (correct.replace(b'rules:\n', b'rules:\n  - MATCH,DIRECT\n'), 1,
             'SELECTED_RULE_SHADOWED'),
            (correct.replace(b'rules:\n', b'rules:\n  - DOMAIN-SUFFIX,test,Other\n'), 1,
             'SELECTED_RULE_SHADOWED'),
            (correct.replace(b'name: approved-group', b'name: missing-group'), 0,
             'EGRESS_GROUP_MISSING_OR_AMBIGUOUS'),
            (correct.replace(b'rules:\n', b'  - name: approved-group\nrules:\n'), 0,
             'EGRESS_GROUP_MISSING_OR_AMBIGUOUS'),
            (correct.replace(b'DOMAIN,example.test,approved-group', b'"DOMAIN,example.test,approved-group"'), 0,
             'UNSUPPORTED_OR_CHANGED_RULE'),
            (correct + b'unknown-field: duplicate\n', 0, 'AMBIGUOUS_MAPPING'),
        ]
        for raw, index, code in cases:
            request, binding = inputs(raw)
            binding['rules']['rule-a'] = {'index': index, 'expected': 'DOMAIN,example.test,approved-group'}
            with self.subTest(code=code, raw=raw), self.assertRaisesRegex(c.EditPlanError, '^' + code + '$'):
                c.compile_edit_plan(raw, request, binding)

    def test_matching_rules_retain_revision_and_semantic_guards(self):
        raw = RAW.replace(b',Old', b',approved-group')
        for change in ('stale', 'cancel', 'version', 'control', 'protected', 'revision'):
            request, binding = inputs(raw)
            binding['rules']['rule-a']['expected'] = 'DOMAIN,example.test,approved-group'
            if change == 'stale': request['current_revisions']['extension'] = 'a' * 64
            if change == 'cancel': request['cancelled'] = True
            if change == 'version': request['facts']['versions']['core'] = 'unknown'
            if change == 'control': request['facts']['control']['preserved'] = 'no'
            if change == 'protected': request['facts']['rules']['protected_priority_preserved'] = 'unknown'
            if change == 'revision': request['revisions']['extension'] = 'a' * 64
            with self.subTest(change=change), self.assertRaises(c.EditPlanError):
                c.compile_edit_plan(raw, request, binding)


if __name__ == '__main__':
    unittest.main()
