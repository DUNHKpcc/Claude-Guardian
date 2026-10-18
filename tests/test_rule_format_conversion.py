"""Bounded offline predicate conversion; no engine, routing, or R acceptance.

The initial API test was run before rule_format_conversion existed and failed
with ModuleNotFoundError. Fixtures are reserved/synthetic names only. Matching
oracles below cover canonical lowercase ASCII host strings, never engine ingress.
"""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'claude-guardian'
sys.path.insert(0, str(SKILL / 'scripts'))

EXACT = 'exact-domain-lines/0.1'
MIHOMO_DOMAIN = 'mihomo/1.19.32/provider-domain-yaml'
MIHOMO_CLASSICAL = 'mihomo/1.19.32/provider-classical-yaml'
SING_BOX = 'sing-box/1.12.0/source-rule-set-json-v1'
PROFILES = (EXACT, MIHOMO_DOMAIN, MIHOMO_CLASSICAL, SING_BOX)
RAW = b'api.example.invalid\n'
EXACT_KIND = 'exact_domain'
SUFFIX_KIND = 'suffix_including_apex'


def declared_source(raw):
    return {'schema_version': 'guardian-rule-source-binding/0.1',
            'source_ref': 'source-a', 'expected_sha256': hashlib.sha256(raw).hexdigest(),
            'evidence_kind': 'official_documentation', 'verified_at': '2026-10-18',
            'version_scope': 'pinned-converter-fixture', 'purpose': 'workflow-repair',
            'client_scope': ['client-a'], 'feature_gate': 'feature-a',
            'shared_service': False, 'activation_state': 'candidate'}


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=True, separators=(',', ':')) + '\n').encode('utf-8')


def fixture(profile, records):
    """Independent, fixed expected serialization of the supported grammar."""
    if profile == EXACT:
        if any(kind != EXACT_KIND for kind, _ in records):
            raise AssertionError('Exact fixture cannot encode suffixes')
        return ''.join(domain + '\n' for _, domain in records).encode('utf-8')
    if profile in (MIHOMO_DOMAIN, MIHOMO_CLASSICAL):
        values = []
        for kind, domain in records:
            if profile == MIHOMO_DOMAIN:
                values.append(('' if kind == EXACT_KIND else '+.') + domain)
            else:
                values.append(('DOMAIN,' if kind == EXACT_KIND else 'DOMAIN-SUFFIX,') + domain)
        return ('payload:\n' + ''.join("  - '" + value + "'\n" for value in values)).encode('utf-8')
    return json_bytes({'version': 1, 'rules': [
        {'domain' if kind == EXACT_KIND else 'domain_suffix': [domain]}
        for kind, domain in records]})


def canonical_match(records, host):
    """Canonical-host predicate oracle, not native-engine execution."""
    return any(host == domain or (kind == SUFFIX_KIND and host.endswith('.' + domain))
               for kind, domain in records)


class TextSubclass(str):
    pass


class BytesSubclass(bytes):
    pass


class DictSubclass(dict):
    pass


class ListSubclass(list):
    pass


class RuleFormatConversionApiTests(unittest.TestCase):
    def test_predicate_only_converter_api_exists(self):
        converter = importlib.import_module('rule_format_conversion')
        self.assertTrue(callable(converter.convert_rule_format))
        self.assertEqual(converter.PROFILES, PROFILES)
        for name in ('EXACT', 'MIHOMO_DOMAIN', 'MIHOMO_CLASSICAL', 'SING_BOX'):
            self.assertEqual(getattr(converter, name), globals()[name])
        self.assertEqual(converter.MAX_BYTES, 1024 * 1024)
        self.assertEqual(converter.MAX_RECORDS, 256)


class RuleFormatConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.converter = importlib.import_module('rule_format_conversion')

    def convert(self, raw=RAW, source_profile=EXACT, target_profile=SING_BOX,
                refs=None, binding=None, **kwargs):
        return self.converter.convert_rule_format(
            raw, source_profile, target_profile, ['rule-a'] if refs is None else refs,
            declared_source(raw) if binding is None else binding, **kwargs)

    def reject(self, raw=RAW, source_profile=EXACT, target_profile=SING_BOX,
               refs=None, binding=None, code=None, **kwargs):
        with self.assertRaises(self.converter.ConversionError) as caught:
            self.convert(raw, source_profile, target_profile, refs, binding, **kwargs)
        message = str(caught.exception)
        self.assertRegex(message, r'^[A-Z][A-Z0-9_]*$')
        if code is not None:
            self.assertEqual(message, code)
        public = message + repr(caught.exception)
        for private in ('api.example.invalid', 'private-sentinel', 'source-a', 'rule-a'):
            self.assertNotIn(private, public)
        self.assertFalse(hasattr(caught.exception, 'output_bytes'))
        return message

    def test_exact_bytes_are_frozen_across_all_sixteen_profile_pairs(self):
        records = [(EXACT_KIND, 'z.example.invalid'), (EXACT_KIND, 'a.example.invalid')]
        refs = ['rule-z', 'rule-a']
        for source_profile in PROFILES:
            raw = fixture(source_profile, records)
            for target_profile in PROFILES:
                with self.subTest(source=source_profile, target=target_profile):
                    result = self.convert(raw, source_profile, target_profile, refs)
                    material = result.private_material()
                    self.assertEqual(material['output_bytes'], fixture(target_profile, records))
                    self.assertEqual(material['source_bytes'], raw)
                    self.assertEqual(material['source_sha256'], hashlib.sha256(raw).hexdigest())
                    self.assertEqual(material['output_sha256'],
                                     hashlib.sha256(material['output_bytes']).hexdigest())
                    self.assertEqual(material['source_profile'], source_profile)
                    self.assertEqual(material['target_profile'], target_profile)
                    self.assertEqual([(r.kind, r.domain) for r in material['records']], records)
                    self.assertEqual([r.rule_ref for r in material['records']], refs)

    def test_suffix_bytes_are_frozen_and_plain_target_fails_atomically(self):
        records = [(SUFFIX_KIND, 'example.invalid'), (EXACT_KIND, 'api.example.invalid')]
        for source_profile in PROFILES[1:]:
            raw = fixture(source_profile, records)
            for target_profile in PROFILES[1:]:
                with self.subTest(source=source_profile, target=target_profile):
                    result = self.convert(raw, source_profile, target_profile, ['rule-z', 'rule-a'])
                    self.assertEqual(result.private_material()['output_bytes'],
                                     fixture(target_profile, records))
            self.reject(raw, source_profile, EXACT, ['rule-z', 'rule-a'])

    def test_canonical_exact_and_apex_suffix_match_matrix(self):
        host_expectations = [
            ('example.invalid', True, True),
            ('a.example.invalid', False, True),
            ('a.b.example.invalid', False, True),
            ('badexample.invalid', False, False),
            ('bad-example.invalid', False, False),
            ('example.invalid.evil', False, False),
            ('other.invalid', False, False)]
        for kind in (EXACT_KIND, SUFFIX_KIND):
            records = [(kind, 'example.invalid')]
            profiles = PROFILES if kind == EXACT_KIND else PROFILES[1:]
            for source_profile in profiles:
                for target_profile in profiles:
                    result = self.convert(fixture(source_profile, records),
                                          source_profile, target_profile)
                    emitted = result.private_material()['output_bytes']
                    # Exact serialized bytes establish each target's pinned predicate
                    # representation. The oracle deliberately does not invoke engines.
                    self.assertEqual(emitted, fixture(target_profile, records))
                    actual_records = [(r.kind, r.domain)
                                      for r in result.private_material()['records']]
                    for host, exact, suffix in host_expectations:
                        with self.subTest(kind=kind, source=source_profile,
                                          target=target_profile, host=host):
                            self.assertIs(canonical_match(actual_records, host),
                                          exact if kind == EXACT_KIND else suffix)
        records = [(SUFFIX_KIND, 'datadoghq.com')]
        for host, expected in [('datadoghq.com', True), ('a.datadoghq.com', True),
                               ('browser-intake-us5-datadoghq.com', False)]:
            self.assertIs(canonical_match(records, host), expected)

    def test_exact_and_suffix_overlap_keeps_order_without_coalescing(self):
        for records in (
                [(SUFFIX_KIND, 'example.invalid'), (EXACT_KIND, 'example.invalid')],
                [(EXACT_KIND, 'example.invalid'), (SUFFIX_KIND, 'example.invalid')]):
            for source_profile in PROFILES[1:]:
                raw = fixture(source_profile, records)
                result = self.convert(raw, source_profile, SING_BOX, ['rule-z', 'rule-a'])
                self.assertEqual(result.private_material()['output_bytes'], fixture(SING_BOX, records))
                self.assertEqual([(r.kind, r.domain) for r in result.private_material()['records']], records)
                self.assertEqual(result.preview()['record_count'], 2)

    def test_json_flattening_preserves_object_key_and_list_order_with_paths(self):
        raw = json_bytes({'version': 1, 'rules': [
            {'domain_suffix': ['z.example.invalid', 'a.example.invalid'],
             'domain': ['api.example.invalid', 'web.example.invalid']},
            {'domain': ['other.invalid']}]})
        refs = ['rule-z', 'rule-a', 'rule-api', 'rule-web', 'rule-other']
        result = self.convert(raw, SING_BOX, MIHOMO_CLASSICAL, refs)
        records = result.private_material()['records']
        expected = [(SUFFIX_KIND, 'z.example.invalid'), (SUFFIX_KIND, 'a.example.invalid'),
                    (EXACT_KIND, 'api.example.invalid'), (EXACT_KIND, 'web.example.invalid'),
                    (EXACT_KIND, 'other.invalid')]
        self.assertEqual([(r.kind, r.domain) for r in records], expected)
        self.assertEqual([r.source_index for r in records], list(range(5)))
        self.assertEqual([r.rule_ref for r in records], refs)
        self.assertEqual([r.source_path for r in records], [
            ('rules', 0, 'domain_suffix', 0), ('rules', 0, 'domain_suffix', 1),
            ('rules', 0, 'domain', 0), ('rules', 0, 'domain', 1), ('rules', 1, 'domain', 0)])
        self.assertEqual([r.original_value for r in records], [domain for _, domain in expected])
        self.assertEqual(result.private_material()['output_bytes'], fixture(MIHOMO_CLASSICAL, expected))

    def test_plain_provenance_retains_original_bytes_line_endings_and_final_newline(self):
        for ending in (b'\n', b'\r\n'):
            for final in (b'', ending):
                raw = b'z.example.invalid' + ending + b'a.example.invalid' + final
                result = self.convert(raw, refs=['rule-z', 'rule-a'])
                material = result.private_material()
                self.assertEqual(material['source_bytes'], raw)
                records = material['records']
                self.assertEqual([r.source_line for r in records], [1, 2])
                self.assertEqual([r.source_path for r in records], [('lines', 0), ('lines', 1)])
                self.assertEqual([r.source_index for r in records], [0, 1])
                self.assertEqual([r.original_value for r in records],
                                 ['z.example.invalid', 'a.example.invalid'])

    def test_yaml_plain_single_double_quotes_and_comment_provenance(self):
        for quote in ('', "'", '"'):
            raw = ('# synthetic 中文 comment\r\npayload:\r\n  - ' + quote +
                   'api.example.invalid' + quote + ' # private-sentinel\r\n').encode('utf-8')
            result = self.convert(raw, MIHOMO_DOMAIN)
            record = result.private_material()['records'][0]
            self.assertEqual(result.private_material()['source_bytes'], raw)
            self.assertEqual(record.source_path, ('payload', 0))
            self.assertEqual(record.source_line, 3)
            self.assertEqual(record.original_value, 'api.example.invalid')
            self.assertEqual(result.private_material()['output_bytes'], fixture(SING_BOX, [
                (EXACT_KIND, 'api.example.invalid')]))
            self.assertNotIn('private-sentinel', repr(result) + json.dumps(result.preview()))

    def test_duplicate_selectors_reject_instead_of_deduplicating(self):
        for profile in PROFILES:
            kinds = (EXACT_KIND,) if profile == EXACT else (EXACT_KIND, SUFFIX_KIND)
            for kind in kinds:
                records = [(kind, 'example.invalid'), (EXACT_KIND, 'other.invalid'),
                           (kind, 'example.invalid')]
                self.reject(fixture(profile, records), profile, SING_BOX,
                            ['rule-a', 'rule-b', 'rule-c'])
        raw = json_bytes({'version': 1, 'rules': [
            {'domain': ['example.invalid', 'example.invalid']}]})
        self.reject(raw, SING_BOX, refs=['rule-a', 'rule-b'])

    def test_json_duplicate_keys_reject_at_each_object_depth(self):
        cases = [
            b'{"version":1,"version":1,"rules":[{"domain":["example.invalid"]}]}',
            b'{"version":1,"rules":[{"domain":["example.invalid"]}],"rules":[]}',
            b'{"version":1,"rules":[{"domain":["example.invalid"],"domain":["other.invalid"]}]}',
            b'{"version":1,"rules":[{"domain_suffix":["example.invalid"],"domain_suffix":["other.invalid"]}]}']
        for raw in cases:
            with self.subTest(raw=raw):
                self.reject(raw, SING_BOX, refs=['rule-a', 'rule-b'])

    def test_profiles_are_exact_pins_and_never_autodetected(self):
        invalid = [None, '', 1, TextSubclass(EXACT), 'exact-domain-lines/0.2',
                   'mihomo/1.19.31/provider-domain-yaml',
                   'mihomo/1.19.32/main-rules-yaml', 'mihomo/1.19.32/provider-domain-mrs',
                   'sing-box/1.12.0/route-rules-json', 'sing-box/1.12.0/source-rule-set-json-v2',
                   'sing-box/1.13.0/source-rule-set-json-v1', 'sing-box/1.12.0/compiled-rule-set-srs']
        for profile in invalid:
            with self.subTest(source=profile):
                self.reject(source_profile=profile)
            with self.subTest(target=profile):
                self.reject(target_profile=profile)
        for profile in PROFILES:
            wrong = b'{"version":1,"rules":[{"domain":["example.invalid"]}]}' if profile != SING_BOX else RAW
            self.reject(wrong, profile)

    def test_noncanonical_domains_reject_without_normalizing(self):
        bad = ['EXAMPLE.invalid', 'example.INVALID', 'Example.invalid', 'example.invalid.',
               'éxample.invalid', 'ｅxample.invalid', '.example.invalid', '*.example.invalid',
               'bad..invalid', '-bad.invalid', 'bad-.invalid', '_service.invalid',
               ' example.invalid', 'example.invalid ', 'example.invalid\t',
               'example.invalid/path', 'https://example.invalid', 'example.invalid:443',
               'person@example.invalid', '192.0.2.1', '127.1', '2130706433',
               '2001:db8::1', '[2001:db8::1]', '999.999.999.999',
               'a' * 64 + '.invalid', 'a.' * 126 + 'aa', 'example\u200b.invalid']
        for domain in bad:
            for profile in PROFILES:
                with self.subTest(domain=domain, profile=profile):
                    self.reject(fixture(profile, [(EXACT_KIND, domain)]), profile)

    def test_ascii_alabels_remain_opaque_and_numeric_labels_are_preserved(self):
        for domain in ('xn--bcher-kva.invalid', '123.example.invalid', 'a1.example.invalid'):
            for profile in PROFILES:
                result = self.convert(fixture(profile, [(EXACT_KIND, domain)]), profile)
                self.assertEqual(result.private_material()['records'][0].domain, domain)
                self.assertEqual(result.private_material()['output_bytes'], fixture(SING_BOX, [
                    (EXACT_KIND, domain)]))
        self.reject('bücher.invalid\n'.encode('utf-8'))
        self.reject(b'XN--bcher-kva.invalid\n')

    def test_wildcard_descendants_and_apex_distinctions_are_never_collapsed(self):
        for value in ('.example.invalid', '*.example.invalid', '+example.invalid',
                      '*example.invalid', '+.*.example.invalid', '+.example.invalid.'):
            raw = ('payload:\n  - ' + value + '\n').encode('utf-8')
            self.reject(raw, MIHOMO_DOMAIN)
        for value in ('.example.invalid', '*.example.invalid', '+.example.invalid'):
            raw = json_bytes({'version': 1, 'rules': [{'domain_suffix': [value]}]})
            self.reject(raw, SING_BOX)
        positive = self.convert(b"payload:\n  - '+.example.invalid'\n", MIHOMO_DOMAIN)
        self.assertEqual(positive.private_material()['records'][0].kind, SUFFIX_KIND)

    def test_plain_blank_comments_whitespace_and_unhandled_lines_reject(self):
        invalid = [b'', b'\n', b'# example.invalid\n', b'example.invalid\n\n',
                   b'\nexample.invalid\n', b'example.invalid # comment\n',
                   b'example.invalid\r', b'example.invalid\rother.invalid',
                   b'example.invalid\vother.invalid', b'example.invalid\x00',
                   b'example.invalid\n# private-sentinel\n',
                   b'example.invalid\n\xef\xbb\xbfother.invalid\n']
        for raw in invalid:
            self.reject(raw)

    def test_malformed_utf8_and_json_are_bounded_conversion_errors(self):
        for profile in PROFILES:
            self.reject(b'\xffprivate-sentinel', profile)
        for raw in (b'{', b'[]', b'null', b'1', b'true', b'{}',
                    b'{"version":1,"rules":[', b'{"version":1,"rules":[]} trailing',
                    b'{"version":NaN,"rules":[]}', b'{"version":Infinity,"rules":[]}'):
            self.reject(raw, SING_BOX)

    def test_json_root_schema_and_version_are_strict(self):
        valid_rule = {'domain': ['example.invalid']}
        for version in (True, False, None, '1', 1.0, 0, 2, 3):
            self.reject(json_bytes({'version': version, 'rules': [valid_rule]}), SING_BOX)
        for obj in ({'rules': [valid_rule]}, {'version': 1},
                    {'version': 1, 'rules': [valid_rule], 'extra': 'private-sentinel'},
                    {'version': 1, 'rules': [valid_rule], 'route': {}},
                    {'version': 1, 'rules': valid_rule}, {'version': 1, 'rules': []},
                    {'version': 1, 'rules': None}):
            self.reject(json_bytes(obj), SING_BOX)

    def test_json_wrong_rule_and_selector_types_reject(self):
        for rule in (None, True, 'example.invalid', [], {}, {'domain': []},
                     {'domain': 'example.invalid'}, {'domain': None}, {'domain': [None]},
                     {'domain': [1]}, {'domain': [True]}, {'domain': [['example.invalid']]},
                     {'domain': ['example.invalid'], 'domain_suffix': []}):
            self.reject(json_bytes({'version': 1, 'rules': [rule]}), SING_BOX)

    def test_json_unknown_conditions_and_actions_reject_whole_batch_in_both_orders(self):
        extras = [('port', [443]), ('network', 'tcp'), ('ip_cidr', ['192.0.2.0/24']),
                  ('ip_version', 4), ('domain_keyword', ['example']), ('domain_regex', ['.*']),
                  ('geosite', ['example']), ('geoip', ['example']), ('rule_set', ['provider-a']),
                  ('invert', True), ('type', 'logical'), ('mode', 'and'), ('rules', []),
                  ('action', 'route'), ('action', 'reject'), ('outbound', 'REJECT'),
                  ('method', 'drop'), ('no_drop', True), ('no_resolve', True),
                  ('unknown', 'private-sentinel')]
        good = {'domain': ['good.invalid']}
        for key, value in extras:
            bad = {'domain': ['bad.invalid'], key: value}
            for rules in ([good, bad], [bad, good]):
                with self.subTest(key=key, value=value, bad_first=rules[0] == bad):
                    self.reject(json_bytes({'version': 1, 'rules': rules}), SING_BOX,
                                refs=['rule-a', 'rule-b'])

    def test_classical_unsupported_match_or_action_tokens_reject_whole_batch(self):
        invalid = ['IP-ASN,64512', 'IP-CIDR,192.0.2.0/24', 'IP-CIDR6,2001:db8::/32',
                   'DOMAIN-KEYWORD,example', 'DOMAIN-REGEX,.*', 'GEOIP,US',
                   'RULE-SET,provider-a', 'MATCH', 'DOMAIN-WILDCARD,*.example.invalid',
                   'DOMAIN,example.invalid,REJECT', 'DOMAIN,example.invalid,REJECT-DROP',
                   'DOMAIN,example.invalid,DIRECT', 'DOMAIN,example.invalid,egress-a',
                   'DOMAIN,example.invalid,no-resolve', 'DOMAIN-SUFFIX,example.invalid,no-resolve',
                   'DOMAIN,example.invalid,', 'DOMAIN, example.invalid', 'DOMAIN ,example.invalid']
        for item in invalid:
            for values in (['DOMAIN,good.invalid', item], [item, 'DOMAIN,good.invalid']):
                raw = ('payload:\n' + ''.join("  - '" + value + "'\n" for value in values)).encode('utf-8')
                with self.subTest(item=item, first=values[0] == item):
                    self.reject(raw, MIHOMO_CLASSICAL, refs=['rule-a', 'rule-b'])

    def test_yaml_schema_ambiguity_and_unsupported_features_reject(self):
        good = b"payload:\n  - 'example.invalid'\n"
        invalid = [good + good, good + b'unknown: private-sentinel\n',
                   b'rules:\n  - DOMAIN,example.invalid,egress-a\n',
                   b'payload: []\n', b'payload: example.invalid\n', b'payload: {}\n',
                   b'payload: [example.invalid]\n', b'payload:\n  - 1\n',
                   b'payload:\n  - true\n', b'payload:\n  - null\n',
                   b'payload:\n  - {domain: example.invalid}\n',
                   b'payload: &r\n  - example.invalid\n',
                   b'payload:\n  - &r example.invalid\n  - *r\n',
                   b'payload:\n  - !!str example.invalid\n', b'payload:\n  - *r\n',
                   b'payload:\n  - |\n    example.invalid\n',
                   b'payload:\n  - >\n    example.invalid\n',
                   b'payload:\n  - "example.\n      invalid"\n',
                   good + b'---\n' + good, b'%YAML 1.1\n---\n' + good,
                   b'<<: {}\n' + good, b'payload: !!seq\n  - example.invalid\n']
        for raw in invalid:
            with self.subTest(raw=raw):
                self.reject(raw, MIHOMO_DOMAIN)

    def test_action_bearing_artifacts_cannot_be_reinterpreted_as_predicates(self):
        sources = [b'rules:\n  - DOMAIN,example.invalid,DIRECT\n',
                   b'rules:\n  - DOMAIN-SUFFIX,example.invalid,egress-a\n  - DOMAIN,api.example.invalid,egress-b\n',
                   b'{"route":{"rules":[{"domain":["example.invalid"],"action":"route","outbound":"egress-a"}]}}',
                   b'[{"domain":["example.invalid"],"action":"reject","method":"drop","no_drop":true}]']
        for raw in sources:
            for profile in PROFILES:
                self.reject(raw, profile)

    def test_source_digest_binds_exact_input_bytes(self):
        binding = declared_source(RAW)
        for raw in (RAW.replace(b'\n', b'\r\n'), RAW.rstrip(b'\n'), b'other.invalid\n'):
            self.reject(raw, binding=binding, code='SOURCE_DIGEST_MISMATCH')

    def test_source_binding_exact_fields_and_unpromoted_declarations(self):
        for key in declared_source(RAW):
            binding = declared_source(RAW)
            del binding[key]
            self.reject(binding=binding)
        for key, value in [('unknown', True), ('source_url', 'https://example.invalid'),
                           ('source_authenticity', 'verified'), ('approved', True)]:
            binding = declared_source(RAW)
            binding[key] = value
            self.reject(binding=binding)
        for key, value in [('schema_version', 'guardian-rule-source-binding/0.2'),
                           ('activation_state', 'active'), ('evidence_kind', 'verified'),
                           ('verified_at', '2026-02-30'), ('expected_sha256', 'a' * 63),
                           ('shared_service', 1), ('client_scope', []),
                           ('client_scope', ['client-a', 'client-a'])]:
            binding = declared_source(RAW)
            binding[key] = value
            self.reject(binding=binding)
        for kind in ('official_documentation', 'user_supplied', 'reference_material'):
            binding = declared_source(RAW)
            binding['evidence_kind'] = kind
            binding['shared_service'] = True
            result = self.convert(binding=binding)
            saved = dict(result.private_material()['declared_source'])
            self.assertEqual(saved['evidence_kind'], kind)
            self.assertIs(saved['shared_service'], True)
            self.assertEqual(result.preview()['source_authenticity'], 'not_established')

    def test_reference_identity_count_and_client_bounds_reject_ambiguity(self):
        raw = b'one.invalid\ntwo.invalid\n'
        for refs in ([], ['rule-a'], ['rule-a', 'rule-a'], ['rule-a', 'rule-b', 'rule-c'],
                     ['https://example.invalid', 'rule-b'], ['rule a', 'rule-b']):
            self.reject(raw, refs=refs)
        binding = declared_source(RAW)
        binding['client_scope'] = tuple('client-' + str(i) for i in range(16))
        result = self.convert(binding=binding, refs=('rule-a',))
        self.assertEqual(dict(result.private_material()['declared_source'])['client_scope'],
                         binding['client_scope'])
        binding['client_scope'] += ('client-16',)
        self.reject(binding=binding)

    def test_builtin_only_containers_and_source_bytes_are_required(self):
        binding = declared_source(RAW)
        for raw in (BytesSubclass(RAW), bytearray(RAW), memoryview(RAW),
                    RAW.decode('utf-8'), None):
            self.reject(raw, binding=binding)
        for refs in (ListSubclass(['rule-a']), iter(['rule-a']), {'rule-a'}, 'rule-a'):
            self.reject(refs=refs)
        self.reject(binding=DictSubclass(binding))
        binding['client_scope'] = ListSubclass(['client-a'])
        self.reject(binding=binding)

    def test_sensitive_alias_shapes_are_rejected_without_echo(self):
        values = ['ghp_' + 'x' * 36, 'github_pat_' + 'x' * 40, 'sk-ant-' + 'x' * 32,
                  'xoxb-' + 'x' * 24, 'https://example.invalid/private-sentinel',
                  'person@example.invalid', '../private-sentinel']
        for value in values:
            for key in ('source_ref', 'purpose', 'version_scope', 'feature_gate'):
                binding = declared_source(RAW)
                binding[key] = value
                self.assertNotIn(value, self.reject(binding=binding))
            self.assertNotIn(value, self.reject(refs=[value]))

    def test_public_preview_reports_only_bounded_evidence_scope_and_counts(self):
        result = self.convert()
        report = result.preview()
        expected = {'status': 'converted_predicates_only', 'record_count': 1,
                    'exact_count': 1, 'suffix_count': 0, 'apply_supported': False,
                    'native_acceptance': 'not_run',
                    'equivalence_scope': 'canonical_lowercase_ascii_predicates_only',
                    'source_authenticity': 'not_established',
                    'source_freshness': 'not_established', 'independent_sources': 'not_established'}
        for key, value in expected.items():
            self.assertEqual(report[key], value)
        public = repr(result) + json.dumps(report)
        for private in ('api.example.invalid', 'rule-a', 'source-a', 'workflow-repair',
                        'feature-a', 'client-a', '2026-10-18', 'pinned-converter-fixture',
                        hashlib.sha256(RAW).hexdigest(),
                        result.private_material()['output_sha256']):
            self.assertNotIn(private, public)
        for key in ('output_bytes', 'source_bytes', 'source_sha256', 'output_sha256',
                    'records', 'declared_source'):
            self.assertNotIn(key, report)
        # Uppercase/trailing-dot/Unicode candidate ingress is intentionally not
        # passed through this oracle or represented as runtime-equivalence proof.
        self.assertNotIn('runtime_verified', report)

    def test_private_result_records_are_frozen_redacted_and_not_default_serializable(self):
        result = self.convert()
        material = result.private_material()
        self.assertIs(type(material['records']), tuple)
        self.assertIs(type(material['declared_source']), tuple)
        self.assertIs(type(dict(material['declared_source'])['client_scope']), tuple)
        record = material['records'][0]
        for item in (result, record):
            self.assertFalse(hasattr(item, '__dict__'))
            for private in ('api.example.invalid', 'rule-a', 'source-a',
                            hashlib.sha256(RAW).hexdigest()):
                self.assertNotIn(private, repr(item))
            with self.assertRaises(TypeError):
                json.dumps(item)
            with self.assertRaises(TypeError):
                pickle.dumps(item)
            with self.assertRaises((AttributeError, TypeError)):
                item.extra = 'mutable'
            slots = set()
            for cls in type(item).__mro__:
                slots.update(getattr(cls, '__slots__', ()))
            for field in slots - {'__weakref__', '__dict__'}:
                with self.subTest(field=field), self.assertRaises((AttributeError, TypeError)):
                    setattr(item, field, getattr(item, field))

    def test_result_copies_and_caller_mutations_cannot_change_conversion(self):
        binding, refs = declared_source(RAW), ['rule-a']
        result = self.convert(binding=binding, refs=refs)
        before = result.private_material()
        binding['client_scope'].append('client-b')
        binding['purpose'] = 'changed'
        refs.append('rule-b')
        changed = result.private_material()
        changed['records'] = ()
        changed['source_bytes'] = b'changed'
        changed['output_bytes'] = b'changed'
        changed['declared_source'] = ()
        preview = result.preview()
        preview['apply_supported'] = True
        preview['record_count'] = 999
        self.assertEqual(result.private_material(), before)
        self.assertFalse(result.preview()['apply_supported'])
        self.assertEqual(result.preview()['record_count'], 1)

    def test_conversion_is_deterministic_pure_and_does_not_mutate_callers(self):
        records = [(EXACT_KIND, 'example.invalid'), (EXACT_KIND, 'other.invalid')]
        for profile in PROFILES:
            raw = fixture(profile, records)
            binding, refs = declared_source(raw), ['rule-a', 'rule-b']
            before = deepcopy((binding, refs))
            with (self.subTest(profile=profile),
                  patch('builtins.open', side_effect=AssertionError('file')),
                  patch('pathlib.Path.open', side_effect=AssertionError('path')),
                  patch('socket.socket', side_effect=AssertionError('network')),
                  patch('socket.getaddrinfo', side_effect=AssertionError('DNS')),
                  patch('subprocess.Popen', side_effect=AssertionError('process')),
                  patch('os.system', side_effect=AssertionError('shell'))):
                first = self.convert(raw, profile, SING_BOX, refs, binding)
                second = self.convert(raw, profile, SING_BOX, refs, binding)
            self.assertEqual(first.private_material(), second.private_material())
            self.assertEqual((binding, refs), before)

    def test_supported_plus_invalid_batches_preserve_inputs_and_return_no_partial_result(self):
        for profile in PROFILES:
            bad = [(EXACT_KIND, 'good.invalid'), (EXACT_KIND, 'BAD.invalid')]
            for records in (bad, list(reversed(bad))):
                raw = fixture(profile, records)
                refs, binding = ['rule-a', 'rule-b'], declared_source(raw)
                before = deepcopy((refs, binding))
                self.reject(raw, profile, refs=refs, binding=binding)
                self.assertEqual((refs, binding), before)

    def test_record_limit_accepts_256_and_rejects_257(self):
        for profile in PROFILES:
            for count in (256, 257):
                records = [(EXACT_KIND, 'host' + str(i) + '.invalid') for i in range(count)]
                raw = fixture(profile, records)
                # Keep reference count inside its own limit to reach parser bound.
                refs = ['rule-' + str(i) for i in range(min(count, 256))]
                with self.subTest(profile=profile, count=count):
                    if count == 256:
                        result = self.convert(raw, profile, SING_BOX, refs)
                        self.assertEqual(result.preview()['record_count'], 256)
                        self.assertEqual(result.private_material()['output_bytes'], fixture(SING_BOX, records))
                    else:
                        self.reject(raw, profile, refs=refs)

    def test_source_byte_limit_is_exactly_one_mebibyte(self):
        tail = b'\npayload:\n  - example.invalid\n'
        raw = b'#' + b'x' * (1024 * 1024 - 1 - len(tail)) + tail
        self.assertEqual(len(raw), 1024 * 1024)
        self.assertEqual(self.convert(raw, MIHOMO_DOMAIN).preview()['record_count'], 1)
        self.reject(raw + b'\n', MIHOMO_DOMAIN)
        self.reject(b'x' * (1024 * 1024 + 1))

    def test_serialized_output_is_bounded_before_return(self):
        raw = b'a.invalid\n'
        self.assertLess(len(raw), 16)
        self.assertGreater(len(fixture(SING_BOX, [(EXACT_KIND, 'a.invalid')])), 16)
        with patch.object(self.converter, 'MAX_BYTES', 16):
            self.reject(raw)

    def test_deadline_argument_and_initial_deadline_validation(self):
        for seconds in (True, False, 0, -1, 61, float('nan'), float('inf'), '5', None):
            self.reject(max_seconds=seconds, code='INVALID_DEADLINE')
        with patch.object(self.converter.time, 'monotonic', side_effect=[0, 6]):
            self.reject(code='DEADLINE_EXCEEDED')

    def test_cancellation_invalid_callback_and_callback_failure_are_private(self):
        def failed():
            raise RuntimeError('private-sentinel')
        for cancelled in (lambda: True, lambda: None, lambda: 1, failed, None):
            self.reject(cancelled=cancelled, code='CANCELLED')

    def test_cancellation_at_every_observed_guard_is_atomic(self):
        for profile in PROFILES:
            raw = fixture(profile, [(EXACT_KIND, 'one.invalid'), (EXACT_KIND, 'two.invalid')])
            refs, binding = ['rule-a', 'rule-b'], declared_source(raw)
            calls = []
            def record_guard():
                calls.append(True)
                return False
            self.convert(raw, profile, refs=refs, binding=binding, cancelled=record_guard)
            self.assertGreater(len(calls), 2)
            before = deepcopy((refs, binding))
            for stop_at in range(1, len(calls) + 1):
                visited = []
                def cancel():
                    visited.append(True)
                    return len(visited) >= stop_at
                with self.subTest(profile=profile, guard=stop_at):
                    self.reject(raw, profile, refs=refs, binding=binding,
                                cancelled=cancel, code='CANCELLED')
                    self.assertEqual((refs, binding), before)

    def test_deadline_at_final_observed_guard_cannot_return_output(self):
        calls = []
        def clock():
            calls.append(True)
            return 0
        with patch.object(self.converter.time, 'monotonic', side_effect=clock):
            self.convert()
        count = len(calls)
        self.assertGreater(count, 2)
        seen = []
        def expires():
            seen.append(True)
            return 6 if len(seen) >= count else 0
        with patch.object(self.converter.time, 'monotonic', side_effect=expires):
            self.reject(code='DEADLINE_EXCEEDED')

    def test_json_escaped_keys_still_detect_decoded_duplicate_members(self):
        cases = [
            b'{"version":1,"\\u0076ersion":1,"rules":[{"domain":["example.invalid"]}]}',
            b'{"version":1,"rules":[{"domain":["example.invalid"]}],"\\u0072ules":[]}',
            b'{"version":1,"rules":[{"domain":["example.invalid"],"\\u0064omain":["other.invalid"]}]}',
            b'{"version":1,"rules":[{"domain_suffix":["example.invalid"],"\\u0064omain_suffix":["other.invalid"]}]}']
        for raw in cases:
            with self.subTest(raw=raw):
                self.reject(raw, SING_BOX, code='DUPLICATE_JSON_KEY')

    def test_sing_box_source_schema_v5_is_explicitly_unsupported(self):
        raw = b'{"version":5,"rules":[{"domain":["example.invalid"]}]}\n'
        self.reject(raw, SING_BOX, code='UNSUPPORTED_SCHEMA_VERSION')

    def test_json_depth_budget_precedes_decode_and_bounds_nested_input(self):
        depth = self.converter.MAX_JSON_DEPTH
        self.assertEqual(depth, 48)
        allowed_depth = b'[' * depth + b'0' + b']' * depth
        self.reject(allowed_depth, SING_BOX, code='UNSUPPORTED_SOURCE_STRUCTURE')
        denied_depth = b'[' * (depth + 1) + b'0' + b']' * (depth + 1)
        with patch.object(self.converter.json, 'loads', side_effect=AssertionError('decode')):
            self.reject(denied_depth, SING_BOX, code='JSON_BUDGET_EXCEEDED')

    def test_json_token_budget_has_exact_boundary_and_ignores_string_contents(self):
        raw = fixture(SING_BOX, [(EXACT_KIND, 'api.example.invalid')])
        self.assertEqual(sum(char in '{}[],:' for char in raw.decode('utf-8')), 12)
        with patch.object(self.converter, 'MAX_JSON_TOKENS', 12):
            self.assertEqual(self.convert(raw, SING_BOX).private_material()['output_bytes'], raw)
        with (patch.object(self.converter, 'MAX_JSON_TOKENS', 11),
              patch.object(self.converter.json, 'loads', side_effect=AssertionError('decode'))):
            self.reject(raw, SING_BOX, code='JSON_BUDGET_EXCEEDED')
        self.assertEqual(self.converter.MAX_JSON_TOKENS, 20000)
        many_tokens = b'[' + b'0,' * 20000 + b'0]'
        self.reject(many_tokens, SING_BOX, code='JSON_BUDGET_EXCEEDED')
        # Escaped quotes/backslashes and punctuation inside a scalar do not
        # consume structural-token quota; they fail canonical domain validation.
        scalar = ('{}[],:' * 100) + '\\"private-sentinel'
        string_punctuation = json_bytes({'version': 1, 'rules': [{'domain': [scalar]}]})
        with patch.object(self.converter, 'MAX_JSON_TOKENS', 12):
            self.reject(string_punctuation, SING_BOX, code='NONCANONICAL_DOMAIN')

    def test_json_budget_scan_can_cancel_before_decoding(self):
        raw = b' ' * 8192 + fixture(SING_BOX, [(EXACT_KIND, 'example.invalid')])
        calls = []
        def stop_during_scan():
            calls.append(True)
            return len(calls) >= 4
        with patch.object(self.converter.json, 'loads', side_effect=AssertionError('decode')):
            self.reject(raw, SING_BOX, cancelled=stop_during_scan, code='CANCELLED')
        self.assertEqual(len(calls), 4)

    def test_decoded_ascii_escape_provenance_is_distinct_from_exact_source_bytes(self):
        sources = [
            (SING_BOX, b'{"version":1,"rules":[{"domain":["\\u0061pi.example.invalid"]}]}\n'),
            (MIHOMO_DOMAIN, b'payload:\n  - "\\u0061pi.example.invalid"\n')]
        for profile, raw in sources:
            result = self.convert(raw, profile)
            material = result.private_material()
            self.assertEqual(material['source_bytes'], raw)
            self.assertEqual(material['source_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(material['records'][0].original_value, 'api.example.invalid')
            self.assertEqual(material['records'][0].domain, 'api.example.invalid')
            self.assertEqual(material['output_bytes'], fixture(SING_BOX, [
                (EXACT_KIND, 'api.example.invalid')]))

    def test_fixed_diagnostics_distinguish_semantics_without_partial_artifacts(self):
        cases = [
            (b'EXAMPLE.invalid\n', EXACT, SING_BOX, ['rule-a'], 'NONCANONICAL_DOMAIN'),
            (b'example.invalid\nexample.invalid\n', EXACT, SING_BOX,
             ['rule-a', 'rule-b'], 'DUPLICATE_PREDICATE'),
            (b"payload:\n  - '+.example.invalid'\n", MIHOMO_DOMAIN, EXACT,
             ['rule-a'], 'UNREPRESENTABLE_MATCH'),
            (b"payload:\n  - '*.example.invalid'\n", MIHOMO_DOMAIN, SING_BOX,
             ['rule-a'], 'UNREPRESENTABLE_MATCH'),
            (b"payload:\n  - 'DOMAIN,example.invalid,REJECT'\n", MIHOMO_CLASSICAL,
             SING_BOX, ['rule-a'], 'UNREPRESENTABLE_ACTION'),
            (b'rules:\n  - DOMAIN,example.invalid,DIRECT\n', MIHOMO_DOMAIN,
             SING_BOX, ['rule-a'], 'UNREPRESENTABLE_ACTION'),
            (json_bytes({'version': 1, 'rules': [{'domain': ['example.invalid'],
                                                'action': 'route', 'outbound': 'REJECT'}]}),
             SING_BOX, EXACT, ['rule-a'], 'UNREPRESENTABLE_ACTION'),
            (json_bytes({'version': 1, 'rules': [{'domain': ['example.invalid'], 'port': [443]}]}),
             SING_BOX, EXACT, ['rule-a'], 'UNHANDLED_CONDITION'),
            (b'{"version":3,"rules":[{"domain":["example.invalid"]}]}',
             SING_BOX, EXACT, ['rule-a'], 'UNSUPPORTED_SCHEMA_VERSION'),
            (b'{"version":1,"rules":[{"domain":["example.invalid"]}],"unknown":true}',
             SING_BOX, EXACT, ['rule-a'], 'UNSUPPORTED_SOURCE_STRUCTURE'),
            (b'{"version":1,"rules":[', SING_BOX, EXACT, ['rule-a'], 'INVALID_RULE_SET_JSON'),
            (b'payload: [example.invalid]\n', MIHOMO_DOMAIN, SING_BOX,
             ['rule-a'], 'UNSUPPORTED_PROVIDER_SYNTAX'),
            (b'payload:\n  - &private example.invalid\n', MIHOMO_DOMAIN, SING_BOX,
             ['rule-a'], 'INVALID_PROVIDER_YAML'),
            (b'payload:\n  - example.invalid\nother: private-sentinel\n', MIHOMO_DOMAIN,
             SING_BOX, ['rule-a'], 'UNSUPPORTED_SOURCE_STRUCTURE'),
            (b'\xffprivate-sentinel', EXACT, SING_BOX, ['rule-a'], 'INVALID_SOURCE_ENCODING'),
            (b'example.invalid\n\n', EXACT, SING_BOX, ['rule-a'], 'EMPTY_SOURCE_RECORD')]
        for raw, source_profile, target_profile, refs, code in cases:
            with self.subTest(code=code, source=source_profile), patch.object(
                    self.converter, 'PrivateConversion', side_effect=AssertionError('partial result')):
                self.reject(raw, source_profile, target_profile, refs, code=code)
        self.reject(source_profile='unknown', code='UNSUPPORTED_PROFILE')
        self.reject(target_profile='unknown', code='UNSUPPORTED_PROFILE')
        self.reject(refs=['rule-a', 'rule-b'], code='RULE_REFERENCE_COUNT_MISMATCH')
        self.reject(refs=['rule-a', 'rule-a'], code='DUPLICATE_RULE_REFERENCE')
        self.reject(refs=[], code='INVALID_RULE_REFERENCES')
        self.reject(binding={}, code='INVALID_SOURCE_BINDING')
        with patch.object(self.converter, 'MAX_BYTES', 16):
            self.reject(b'a.invalid\n', code='OUTPUT_BUDGET_EXCEEDED')
        with patch.object(self.converter.config, 'yaml', None):
            self.reject(b'payload:\n  - example.invalid\n', MIHOMO_DOMAIN,
                        code='PARSER_UNAVAILABLE')

    def test_extracted_package_smoke_isolated_without_site_packages(self):
        with tempfile.TemporaryDirectory(prefix='guardian-converter-') as temporary:
            root = Path(temporary)
            archive_path = root / 'skill.zip'
            subprocess.run([sys.executable, '-B', str(ROOT / 'tools/package_skill.py'),
                            '--output', str(archive_path)], check=True, capture_output=True,
                           encoding='utf-8', timeout=30)
            with zipfile.ZipFile(archive_path) as archive:
                relative = 'claude-guardian/scripts/rule_format_conversion.py'
                self.assertEqual(archive.read(relative),
                                 (SKILL / 'scripts/rule_format_conversion.py').read_bytes())
                for member in archive.namelist():
                    self.assertTrue(member.startswith('claude-guardian/'))
                    self.assertNotIn('..', Path(member).parts)
                archive.extractall(root / 'detached')
            scripts = root / 'detached/claude-guardian/scripts'
            cwd = root / 'unrelated'
            cwd.mkdir()
            snippet = r"""
import hashlib, json, pathlib, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import rule_format_conversion as conversion
assert pathlib.Path(conversion.__file__).parent == pathlib.Path(sys.argv[1])
raw = b'api.example.invalid\n'
binding = json.loads(sys.argv[2])
result = conversion.convert_rule_format(raw, conversion.EXACT, conversion.SING_BOX,
                                        ['rule-a'], binding)
assert result.private_material()['output_bytes'] == (
    b'{"version":1,"rules":[{"domain":["api.example.invalid"]}]}\n')
assert result.private_material()['source_bytes'] == raw
assert result.preview()['equivalence_scope'] == 'canonical_lowercase_ascii_predicates_only'
for target in (conversion.MIHOMO_DOMAIN, conversion.MIHOMO_CLASSICAL):
    converted = conversion.convert_rule_format(raw, conversion.EXACT, target,
                                               ['rule-a'], binding)
    assert converted.private_material()['output_bytes'].startswith(b'payload:\n')
for source_profile in (conversion.MIHOMO_DOMAIN, conversion.MIHOMO_CLASSICAL):
    value = ('example.invalid' if source_profile == conversion.MIHOMO_DOMAIN
             else 'DOMAIN,example.invalid')
    source = ('payload:\n  - ' + value + '\n').encode('utf-8')
    declared = dict(binding)
    declared['expected_sha256'] = hashlib.sha256(source).hexdigest()
    try:
        conversion.convert_rule_format(source, source_profile, conversion.SING_BOX,
                                       ['rule-a'], declared)
    except conversion.ConversionError as error:
        assert str(error) == 'PARSER_UNAVAILABLE', str(error)
    else:
        raise AssertionError('Optional parser absence was bypassed')
print(json.dumps(result.preview()))
"""
            completed = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', snippet,
                                        str(scripts), json.dumps(declared_source(RAW))],
                                       cwd=cwd, check=True, capture_output=True,
                                       encoding='utf-8', timeout=30)
            self.assertEqual(list(cwd.iterdir()), [])
            self.assertFalse(list((root / 'detached').rglob('*.pyc')))
        report = json.loads(completed.stdout)
        self.assertEqual(report['status'], 'converted_predicates_only')
        self.assertFalse(report['apply_supported'])
        self.assertEqual(report['native_acceptance'], 'not_run')
        self.assertNotIn('api.example.invalid', completed.stdout + completed.stderr)
        self.assertNotIn('source-a', completed.stdout + completed.stderr)


if __name__ == '__main__':
    unittest.main()
