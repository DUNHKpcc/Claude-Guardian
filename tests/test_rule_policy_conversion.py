"""Offline ordered-label selection evidence, not native engine acceptance."""
import importlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/claude-guardian/scripts'))

class PolicyAPI(unittest.TestCase):
    def test_separate_api_exists(self):
        self.assertTrue(callable(importlib.import_module('rule_policy_conversion').convert_policy_rules))


from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import itertools
import json
import pickle
import random
import re
from unittest.mock import patch

import rule_policy_conversion as policy
import rule_format_conversion as predicates
import rule_source_import as importer

M = policy.MIHOMO
S = policy.SING_BOX
RAW = b"rules:\n  - DOMAIN-SUFFIX,example.invalid,egress-a\n  - DOMAIN,api.example.invalid,egress-b\n"


def binding(raw):
    return {'schema_version': 'guardian-rule-source-binding/0.1',
            'source_ref': 'source-a', 'expected_sha256': hashlib.sha256(raw).hexdigest(),
            'evidence_kind': 'official_documentation', 'verified_at': '2026-10-18',
            'version_scope': 'pinned-fixture', 'purpose': 'workflow-repair',
            'client_scope': ['client-a'], 'feature_gate': 'feature-a',
            'shared_service': False, 'activation_state': 'candidate'}


def outbound(a='egress-a', b='route-a'):
    return {'source_label': a, 'target_label': b,
            'source_kind': 'ordinary_outbound', 'target_kind': 'ordinary_outbound',
            'source_finality': 'terminal_for_tcp_udp', 'target_finality': 'terminal_for_tcp_udp'}


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, separators=(',', ':')) + '\n').encode('ascii')


def yaml_rules(rows):
    return ('rules:\n' + ''.join("  - '" + ','.join(row) + "'\n" for row in rows)).encode('ascii')


def convert(raw=RAW, src=M, mappings=None, refs=None, **kw):
    if mappings is None:
        mappings = [outbound(), outbound('egress-b', 'route-b')]
    if refs is None:
        count = len(json.loads(raw)) if src == S else len(raw.splitlines()) - 1
        refs = ['rule-' + str(i) for i in range(count)]
    return policy.convert_policy_rules(raw, src, S if src == M else M, refs,
                                       binding(raw), mappings, **kw)


def canonical_candidate(host):
    # Separate test-model validator, not the production converter helper.
    labels = host.split('.')
    return (0 < len(host) <= 253 and all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',
                                                   label) for label in labels)
            and not all(label.isdigit() for label in labels))


def source_oracle(rows, host):
    # Independent source-format oracle, with fixed out-of-profile cases tested below.
    if not canonical_candidate(host):
        return 'outside_profile'
    for kind, domain, action in rows:
        if host == domain or (kind == 'DOMAIN-SUFFIX' and host.endswith('.' + domain)):
            return action
    return policy.DEFER


def target_oracle(raw, host):
    # Independent parsed target oracle; does not use converter IR or match helpers.
    if not canonical_candidate(host):
        return 'outside_profile'
    for rule in json.loads(raw):
        if host in rule.get('domain', []):
            return rule['outbound']
        for domain in rule.get('domain_suffix', []):
            candidate_labels, pattern_labels = host.split('.'), domain.split('.')
            if candidate_labels[-len(pattern_labels):] == pattern_labels:
                return rule['outbound']
    return policy.DEFER


class OrderedPolicyTests(unittest.TestCase):
    def reject(self, raw, src=M, code=None, mappings=None, refs=None, **kw):
        with self.assertRaises(policy.PolicyConversionError) as caught:
            convert(raw, src, mappings, refs, **kw)
        if code:
            self.assertEqual(str(caught.exception), code)
        self.assertRegex(str(caught.exception), r'^[A-Z_]+$')
        self.assertFalse(hasattr(caught.exception, 'output_bytes'))
        return caught.exception

    def test_exact_frozen_output_and_provenance(self):
        result = convert()
        material = result.private_material()
        expected = (b'[{"domain_suffix":["example.invalid"],"action":"route","outbound":"route-a"},'
                    b'{"domain":["api.example.invalid"],"action":"route","outbound":"route-b"}]\n')
        self.assertEqual(material['output_bytes'], expected)
        self.assertEqual(material['source_bytes'], RAW)
        self.assertEqual(material['source_sha256'], hashlib.sha256(RAW).hexdigest())
        self.assertEqual(material['output_sha256'], hashlib.sha256(expected).hexdigest())
        self.assertEqual(material['output_occurrence_map'], ((0, 0, 0), (1, 1, 0)))
        first, second = material['records']
        self.assertEqual(first.source_rule_ref, 'rule-0')
        self.assertEqual(first.source_line, 2)
        self.assertEqual(second.source_path, ('rules', 1))
        self.assertEqual(first.original_value, 'DOMAIN-SUFFIX,example.invalid,egress-a')
        self.assertEqual(first.source_action, ('route_to_named_outbound', 'egress-a'))
        self.assertEqual(first.target_action, ('route_to_named_outbound', 'route-a'))
        self.assertEqual(material, convert().private_material())

    def test_order_duplicates_and_shadowed_occurrences_preserved(self):
        broad = ('DOMAIN-SUFFIX', 'example.invalid', 'egress-a')
        exact = ('DOMAIN', 'api.example.invalid', 'egress-b')
        for rows, expected in [([broad, exact], 'route-a'), ([exact, broad], 'route-b'),
                               ([exact, exact, broad], 'route-b'),
                               ([broad, exact, broad], 'route-a'),
                               ([('DOMAIN', 'api.example.invalid', 'egress-a'), exact], 'route-a')]:
            with self.subTest(rows=rows):
                material = convert(yaml_rules(rows)).private_material()
                self.assertEqual(len(material['records']), len(rows))
                self.assertEqual(target_oracle(material['output_bytes'], 'api.example.invalid'), expected)

    def test_sing_or_expansion_field_list_order_and_inverse_roundtrip(self):
        raw = encoded([{'domain_suffix': ['example.invalid', 'example.invalid'],
                        'outbound': 'route-a', 'domain': ['api.example.invalid'], 'action': 'route'},
                       {'domain': ['other.invalid'], 'action': 'route', 'outbound': 'route-b'}])
        inverse = [outbound('route-a', 'egress-a'), outbound('route-b', 'egress-b')]
        material = convert(raw, S, inverse).private_material()
        rows = [('DOMAIN-SUFFIX', 'example.invalid', 'egress-a'),
                ('DOMAIN-SUFFIX', 'example.invalid', 'egress-a'),
                ('DOMAIN', 'api.example.invalid', 'egress-a'),
                ('DOMAIN', 'other.invalid', 'egress-b')]
        self.assertEqual(material['output_bytes'], yaml_rules(rows))
        self.assertEqual(material['output_occurrence_map'], ((0, 0, 0), (1, 0, 1), (2, 0, 2), (3, 1, 0)))
        self.assertEqual(material['records'][2].source_path, (0, 'domain', 0))
        self.assertTrue(all(row.source_line is None for row in material['records']))
        self.assertEqual([row.source_rule_ref for row in material['records']], ['rule-0'] * 3 + ['rule-1'])
        forward = convert(material['output_bytes']).private_material()['output_bytes']
        self.assertEqual(json.loads(forward), [
            {'domain_suffix': ['example.invalid'], 'action': 'route', 'outbound': 'route-a'},
            {'domain_suffix': ['example.invalid'], 'action': 'route', 'outbound': 'route-a'},
            {'domain': ['api.example.invalid'], 'action': 'route', 'outbound': 'route-a'},
            {'domain': ['other.invalid'], 'action': 'route', 'outbound': 'route-b'}])

    def test_canonical_apex_boundary_matrix_and_no_match(self):
        raw = yaml_rules([('DOMAIN-SUFFIX', 'example.invalid', 'egress-a')])
        output = convert(raw, mappings=[outbound()]).private_material()['output_bytes']
        for host in ['example.invalid', 'a.example.invalid', 'a.b.example.invalid']:
            self.assertEqual(target_oracle(output, host), 'route-a')
        for host in ['badexample.invalid', 'bad-example.invalid', 'example.invalid.evil', 'other.invalid']:
            self.assertEqual(target_oracle(output, host), policy.DEFER)
        exact = convert(yaml_rules([('DOMAIN', 'example.invalid', 'egress-a')]),
                        mappings=[outbound()]).private_material()['output_bytes']
        self.assertEqual(target_oracle(exact, 'a.example.invalid'), policy.DEFER)
        self.assertEqual(target_oracle(exact, 'example.invalid'), 'route-a')

    def test_deterministic_generated_policy_semantics_and_roundtrips(self):
        rng = random.Random(40)
        hosts = ['example.invalid', 'a.example.invalid', 'a.b.example.invalid',
                 'api.example.invalid', 'bad-example.invalid', 'example.invalid.evil', 'other.invalid']
        for _ in range(80):
            rows = [(rng.choice(['DOMAIN', 'DOMAIN-SUFFIX']), rng.choice(hosts[:4]),
                     rng.choice(['egress-a', 'egress-b'])) for _ in range(rng.randint(1, 12))]
            used = sorted({row[2] for row in rows})
            maps = [outbound(label, label.replace('egress', 'route')) for label in used]
            raw = yaml_rules(rows)
            output = convert(raw, mappings=maps).private_material()['output_bytes']
            self.assertEqual(output, convert(raw, mappings=maps).private_material()['output_bytes'])
            for host in hosts:
                expected = source_oracle(rows, host)
                if expected != policy.DEFER:
                    expected = expected.replace('egress', 'route')
                self.assertEqual(target_oracle(output, host), expected)
            inverse = [outbound(m['target_label'], m['source_label']) for m in maps]
            self.assertEqual(convert(output, S, inverse).private_material()['output_bytes'], raw)

    def test_identity_and_case_sensitive_nonreserved_labels(self):
        for label in ['reject', 'direct', 'REJECT-backup', 'PASS-through', 'COMPATIBLE-edge',
                      'my-GLOBAL', 'DNS', 'REMATCH', 'MATCH', 'Route-A']:
            with self.subTest(label=label):
                raw = yaml_rules([('DOMAIN', 'example.invalid', label)])
                result = convert(raw, mappings=[outbound(label, label)]).private_material()
                self.assertEqual(json.loads(result['output_bytes'])[0]['outbound'], label)

    def test_all_reserved_labels_source_and_both_mapping_sides(self):
        for label in sorted(policy.RESERVED_POLICY_LABELS):
            for side in ['source_label', 'target_label']:
                mapping = outbound()
                mapping[side] = label
                self.reject(RAW, mappings=[mapping], code='RESERVED_ACTION_COLLISION')
            raw = yaml_rules([('DOMAIN', 'example.invalid', label)])
            self.reject(raw, mappings=[outbound()], code='RESERVED_ACTION_COLLISION')
            raw = encoded([{'domain': ['example.invalid'], 'action': 'route', 'outbound': label}])
            self.reject(raw, S, mappings=[outbound()], code='RESERVED_ACTION_COLLISION')

    def test_mapping_bijection_exact_coverage_and_shape(self):
        cases = [([], 'INVALID_OUTBOUND_BINDINGS'),
                 ([outbound()], 'INCOMPLETE_OUTBOUND_BINDINGS'),
                 ([outbound(), outbound('egress-b', 'route-a')], 'AMBIGUOUS_OUTBOUND_BINDINGS'),
                 ([outbound(), outbound('egress-a', 'route-b')], 'AMBIGUOUS_OUTBOUND_BINDINGS'),
                 ([outbound(), outbound('egress-b', 'route-b'), outbound('unused', 'route-c')],
                  'UNUSED_OUTBOUND_BINDINGS')]
        for maps, code in cases:
            self.reject(RAW, mappings=maps, code=code)
        for change in [{'native_pass': True}, {'source_kind': True}, {'source_kind': 'direct'},
                       {'target_kind': 'reject'}, {'target_kind': 'group_unknown'}]:
            maps = [outbound(), outbound('egress-b', 'route-b')]
            maps[0].update(change)
            self.reject(RAW, mappings=maps)
        for label in ['', ' edge', 'edge ', 'route.a', 'route,a', '\u00e9', 'sk-ant-api03-secret',
                      'x' * 65, None, 7]:
            maps = [outbound(), outbound('egress-b', 'route-b')]
            maps[0]['target_label'] = label
            self.reject(RAW, mappings=maps, code='INVALID_OUTBOUND_LABEL')

    def test_finality_unknown_or_one_protocol_and_false_claims_reject(self):
        for key, value in itertools.product(['source_finality', 'target_finality'],
                ['unknown', 'terminal_for_tcp', 'conditional_fallthrough', 'rematch', 'continuing', True, None]):
            maps = [outbound(), outbound('egress-b', 'route-b')]
            maps[0][key] = value
            self.reject(RAW, mappings=maps, code='UNKNOWN_OUTBOUND_FINALITY')

    def test_noncanonical_hosts_reject_in_both_profiles(self):
        for host in ['EXAMPLE.invalid', '\u4f8b.invalid', 'example.invalid.', '.example.invalid',
                     '*.example.invalid', '+.example.invalid', '-a.invalid', 'a-.invalid',
                     'a..invalid', 'a invalid', ' example.invalid', '127.0.0.1', '123',
                     'a' * 64 + '.invalid', '.'.join(['a' * 63] * 4)]:
            for key in ['domain', 'domain_suffix']:
                raw = encoded([{key: [host], 'action': 'route', 'outbound': 'egress-a'}])
                self.reject(raw, S, mappings=[outbound()], code='NONCANONICAL_DOMAIN')
            if host.isascii():
                self.reject(yaml_rules([('DOMAIN', host, 'egress-a')]),
                            mappings=[outbound()], code='NONCANONICAL_DOMAIN')
        result = convert(yaml_rules([('DOMAIN', 'xn--bcher-kva.invalid', 'egress-a')]), mappings=[outbound()])
        self.assertIn(b'xn--bcher-kva.invalid', result.private_material()['output_bytes'])
        # Noncanonical candidates are explicitly outside the advertised model.
        for host in ['EXAMPLE.INVALID', 'example.invalid.', '\u4f8b.invalid']:
            self.assertFalse(predicates._canonical_domain(host))
            self.assertEqual(target_oracle(result.private_material()['output_bytes'], host), 'outside_profile')
            self.assertEqual(source_oracle([], host), 'outside_profile')

    def test_unsupported_mihomo_rules_and_late_failure_atomicity(self):
        for entry in ['IP-ASN,12345,egress-a', 'IP-CIDR,192.0.2.0/24,egress-a',
                      'DOMAIN-KEYWORD,example,egress-a', 'DOMAIN-REGEX,example,egress-a',
                      'RULE-SET,provider-a,egress-a', 'MATCH,egress-a',
                      'DOMAIN,example.invalid,egress-a,no-resolve',
                      'DOMAIN,example.invalid', 'AND,example.invalid,egress-a']:
            raw = b'rules:\n  - DOMAIN,good.invalid,egress-a\n  - ' + entry.encode() + b'\n'
            self.reject(raw, mappings=[outbound()])

    def test_sing_unknown_default_fields_and_combined_conditions_reject(self):
        for key, value in [('port', [443]), ('network', 'tcp'), ('invert', False),
                           ('type', 'default'), ('rule_set', []), ('domain_keyword', ['example']),
                           ('domain_regex', ['.*']), ('ip_cidr', ['192.0.2.0/24']),
                           ('source_ip_is_private', False), ('unknown', None)]:
            good = {'domain': ['example.invalid'], 'action': 'route', 'outbound': 'egress-a'}
            for bad in [dict(good, **{key: value}), {key: value, **good}]:
                self.reject(encoded([good, bad]), S, mappings=[outbound()], code='UNHANDLED_CONDITION')
        for action in ['reject', 'reject-drop', 'sniff', 'resolve', '', None, True]:
            self.reject(encoded([{'domain': ['example.invalid'], 'action': action, 'outbound': 'egress-a'}]),
                        S, mappings=[outbound()], code='UNREPRESENTABLE_ACTION')
        self.reject(encoded([{'domain': ['example.invalid'], 'outbound': 'egress-a'}]),
                    S, mappings=[outbound()], code='UNREPRESENTABLE_ACTION')
        self.reject(encoded([{'domain': ['example.invalid'], 'action': 'reject', 'method': 'drop',
                              'no_drop': True}]), S, mappings=[outbound()], code='UNREPRESENTABLE_ACTION')

    def test_json_duplicate_keys_and_invalid_types(self):
        for raw in [b'[{"domain":["example.invalid"],"domain":["other.invalid"],"action":"route","outbound":"egress-a"}]',
                    b'[{"domain":["example.invalid"],"\\u0064omain":["other.invalid"],"action":"route","outbound":"egress-a"}]']:
            self.reject(raw, S, mappings=[outbound()], code='DUPLICATE_JSON_KEY', refs=['rule-a'])
        for value in [None, {}, {'rules': []}, [], [None], [7],
                      [{'domain': [], 'action': 'route', 'outbound': 'egress-a'}],
                      [{'domain': 'example.invalid', 'action': 'route', 'outbound': 'egress-a'}],
                      [{'domain': [7], 'action': 'route', 'outbound': 'egress-a'}],
                      [{'action': 'route', 'outbound': 'egress-a'}]]:
            self.reject(encoded(value), S, mappings=[outbound()], refs=['rule-a'])
        for raw in [b'[NaN]', b'[Infinity]', b'[{', b'[] trailing']:
            self.reject(raw, S, mappings=[outbound()], refs=['rule-a'])

    def test_yaml_unsupported_features_and_wrong_artifacts(self):
        for raw in [b'rules: [DOMAIN,x.invalid,egress-a]\n',
                    b'{rules: []}\n', b'rules: []\nrules: []\n',
                    b'rules:\n  - &a DOMAIN,x.invalid,egress-a\n  - *a\n',
                    b'rules:\n  - !!str DOMAIN,x.invalid,egress-a\n',
                    b'rules:\n  - >\n    DOMAIN,x.invalid,egress-a\n',
                    b'rules:\n  - "DOMAIN,x.invalid,\n    egress-a"\n',
                    b'rules:\n  - 42\n', b'rules:\n  - {domain: x.invalid}\n',
                    b'rules: []\n---\nrules: []\n', b'payload:\n  - x.invalid\n',
                    b'rules:\n  - DOMAIN,x.invalid,egress-a\nextra: 1\n']:
            self.reject(raw, mappings=[outbound()], refs=['rule-a'])
        for quote in ['', "'", '"']:
            raw = ('rules:\n  - ' + quote + 'DOMAIN,example.invalid,egress-a' + quote + '\n').encode()
            convert(raw, mappings=[outbound()])

    def test_explicit_profiles_only_and_fragment_no_match_contract(self):
        for src, target in [(M, M), (S, S), ('mihomo/latest/main-rules-yaml', S),
                            (M, predicates.MIHOMO_DOMAIN), (predicates.SING_BOX, M), (None, M)]:
            with self.assertRaisesRegex(policy.PolicyConversionError, '^UNSUPPORTED_PROFILE$'):
                policy.convert_policy_rules(RAW, src, target, ['r-a', 'r-b'], binding(RAW), [outbound()])
        for key, value in itertools.product(['source_no_match', 'target_no_match'], ['DIRECT', None, True, 'final']):
            self.reject(RAW, code='INCOMPATIBLE_NO_MATCH_SEMANTICS', **{key: value})
        preview = convert().preview()
        self.assertEqual(preview['no_match_contract'], policy.DEFER)
        self.assertEqual(preview['enclosing_fallback'], 'not_established')
        self.assertEqual(preview['native_acceptance'], 'not_run')
        self.assertFalse(preview['apply_supported'])

    def test_strict_binding_references_and_digest(self):
        for refs, code in [(['r-a'], 'RULE_REFERENCE_COUNT_MISMATCH'),
                           (['r-a', 'r-a'], 'DUPLICATE_RULE_REFERENCE'),
                           (['r-a', 'x' * 65], 'INVALID_RULE_REFERENCES')]:
            self.reject(RAW, refs=refs, code=code)
        for change, code in [({'expected_sha256': '0' * 64}, 'SOURCE_DIGEST_MISMATCH'),
                             ({'native_pass': True}, 'INVALID_SOURCE_BINDING'),
                             ({'verified_at': '2026-02-30'}, 'INVALID_SOURCE_BINDING'),
                             ({'client_scope': ['client-' + str(i) for i in range(17)]}, 'INVALID_SOURCE_BINDING')]:
            declared = binding(RAW)
            declared.update(change)
            with self.assertRaisesRegex(policy.PolicyConversionError, '^' + code + '$'):
                policy.convert_policy_rules(RAW, M, S, ['r-a', 'r-b'], declared,
                                            [outbound(), outbound('egress-b', 'route-b')])

    def test_private_frozen_result_and_public_redaction(self):
        result = convert()
        private = result.private_material()
        for value in [result, private['records'][0]]:
            self.assertNotIn('example.invalid', repr(value))
            self.assertNotIn('egress-a', repr(value))
            with self.assertRaises(TypeError):
                pickle.dumps(value)
            with self.assertRaises(TypeError):
                json.dumps(value)
        with self.assertRaises(FrozenInstanceError):
            result._source = b'changed'
        with self.assertRaises(FrozenInstanceError):
            private['records'][0].domain = 'changed.invalid'
        private['output_bytes'] = b'changed'
        self.assertNotEqual(result.private_material()['output_bytes'], b'changed')
        public = json.dumps(result.preview())
        for value in ['example.invalid', 'egress-a', 'route-a', 'source-a', private['source_sha256']]:
            self.assertNotIn(value, public)

    def test_caller_mutation_and_callback_snapshot_isolation(self):
        refs, declared = ['r-a', 'r-b'], binding(RAW)
        maps = [outbound(), outbound('egress-b', 'route-b')]
        originals = deepcopy((refs, declared, maps))
        def mutate():
            refs[:] = ['changed']
            declared['client_scope'][:] = ['changed']
            maps[0]['target_label'] = 'changed'
            return False
        result = policy.convert_policy_rules(RAW, M, S, refs, declared, maps, cancelled=mutate)
        material = result.private_material()
        self.assertEqual(material['ordered_rule_refs'], tuple(originals[0]))
        self.assertEqual(dict(material['declared_source'])['client_scope'], ('client-a',))
        self.assertEqual(dict(material['outbound_bindings'][0])['target_label'], 'route-a')
        self.assertNotIn(b'changed', material['output_bytes'])
        unchanged = deepcopy(originals)
        policy.convert_policy_rules(RAW, M, S, *unchanged)
        self.assertEqual(unchanged, originals)

    def test_resource_bounds_source_rules_predicates_mappings_and_output(self):
        self.reject(b'x' * (policy.MAX_BYTES + 1), refs=['r-a'], code='INVALID_OR_OVERSIZED_SOURCE')
        self.reject(b'', refs=['r-a'], code='INVALID_OR_OVERSIZED_SOURCE')
        raw = encoded([{'domain': ['example.invalid'] * 257, 'action': 'route', 'outbound': 'egress-a'}])
        self.reject(raw, S, mappings=[outbound()], code='TOO_MANY_PREDICATES')
        raw = encoded([{'domain': ['example.invalid'], 'action': 'route', 'outbound': 'egress-a'}] * 257)
        self.reject(raw, S, mappings=[outbound()], refs=['r-a'], code='TOO_MANY_SOURCE_RULES')
        self.reject(yaml_rules([('DOMAIN', 'example.invalid', 'egress-a')] * 257),
                    mappings=[outbound()], refs=['r-a'], code='TOO_MANY_SOURCE_RULES')
        self.reject(RAW, mappings=[outbound('source-' + str(i), 'target-' + str(i)) for i in range(257)],
                    code='INVALID_OUTBOUND_BINDINGS')
        # Output expansion is checked against actual bytes, not input estimates.
        raw = b'rules:\n  - DOMAIN,x.invalid,a\n'
        with patch.object(policy, 'MAX_BYTES', 70):
            self.reject(raw, mappings=[outbound('a', 'b' * 64)], code='OUTPUT_BUDGET_EXCEEDED')
        exact256 = yaml_rules([('DOMAIN', 'example.invalid', 'egress-a')] * 256)
        self.assertEqual(len(convert(exact256, mappings=[outbound()]).private_material()['records']), 256)

    def test_json_yaml_structural_budgets(self):
        self.reject(b'[' * 49 + b']' * 49, S, refs=['r-a'], code='JSON_BUDGET_EXCEEDED')
        self.reject(b'[' + b'0,' * 20001 + b'0]', S, refs=['r-a'], code='JSON_BUDGET_EXCEEDED')
        raw = b'rules:\n  - DOMAIN,example.invalid,egress-a\n'
        with patch.object(policy.config, 'MAX_NODES', 2):
            self.reject(raw, mappings=[outbound()], code='YAML_BUDGET_EXCEEDED')
        self.reject(b'rules: ' + b'[' * 49 + b']' * 49, refs=['r-a'], code='YAML_BUDGET_EXCEEDED')

    def test_deadline_finite_positive_bounded_and_elapsed(self):
        for value in [0, -1, True, '5', None, float('nan'), float('inf'), 61]:
            self.reject(RAW, max_seconds=value, code='INVALID_DEADLINE')
        with patch.object(policy.time, 'monotonic', side_effect=[0, 6]):
            self.reject(RAW, code='DEADLINE_EXCEEDED')

    def test_cancellation_errors_nonboolean_during_parse_and_last_boundary(self):
        for callback in [lambda: True, lambda: None, lambda: 0, lambda: (_ for _ in ()).throw(ValueError('private'))]:
            self.reject(RAW, cancelled=callback, code='CANCELLED')
        calls = []
        convert(cancelled=lambda: calls.append(1) or False)
        total = len(calls)
        self.assertGreater(total, 10)
        for boundary in [1, 4, total - 1, total]:
            count = 0
            def callback():
                nonlocal count
                count += 1
                return count == boundary
            self.reject(RAW, cancelled=callback, code='CANCELLED')
            self.assertEqual(count, boundary)

    def test_missing_yaml_dependency_leaves_json_conversion_available(self):
        with patch.object(policy.config, 'yaml', None):
            self.reject(RAW, code='PARSER_UNAVAILABLE')
            raw = encoded([{'domain': ['example.invalid'], 'action': 'route', 'outbound': 'egress-a'}])
            result = convert(raw, S, mappings=[outbound()])
            self.assertEqual(result.private_material()['output_bytes'],
                             b"rules:\n  - 'DOMAIN,example.invalid,route-a'\n")

    def test_conversion_no_filesystem_process_or_network_effects(self):
        with patch('builtins.open', side_effect=AssertionError('unexpected file access')), \
             patch('socket.socket', side_effect=AssertionError('unexpected network')), \
             patch('subprocess.Popen', side_effect=AssertionError('unexpected process')):
            result = convert()
            self.assertEqual(result.preview()['predicate_count'], 2)

    def test_existing_actionless_converter_remains_actionless(self):
        with self.assertRaisesRegex(predicates.ConversionError, '^UNREPRESENTABLE_ACTION$'):
            predicates.convert_rule_format(RAW, predicates.MIHOMO_CLASSICAL, predicates.SING_BOX,
                                           ['r-a', 'r-b'], binding(RAW))
        raw = encoded({'version': 1, 'rules': [{'domain': ['example.invalid'],
                                              'action': 'route', 'outbound': 'egress-a'}]})
        with self.assertRaisesRegex(predicates.ConversionError, '^UNREPRESENTABLE_ACTION$'):
            predicates.convert_rule_format(raw, predicates.SING_BOX, predicates.MIHOMO_DOMAIN,
                                           ['r-a'], binding(raw))


if __name__ == '__main__':
    unittest.main()
