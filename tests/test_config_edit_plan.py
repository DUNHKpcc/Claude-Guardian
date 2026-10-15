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
        with self.assertRaisesRegex(c.EditPlanError, 'NO_CHANGE'):
            c.compile_edit_plan(raw, request, binding)


if __name__ == '__main__':
    unittest.main()
