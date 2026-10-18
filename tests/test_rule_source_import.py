"""Synthetic, bounded source conversion; no real configuration or native claims."""
from copy import deepcopy
import hashlib
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
SKILL = ROOT / 'skills/claude-guardian'
sys.path.insert(0, str(SKILL / 'scripts'))
import rule_source_import as source
import rules_extension_plan as rules
from test_rules_extension_plan import BASE, RAW, inputs as plan_inputs

PLAIN = 'exact-domain-lines/0.1'
FRAGMENT = 'mihomo-domain-rules-fragment/0.1'
DOMAIN_BYTES = b'Example.test\n'


def declared_source(raw):
    return {'schema_version': 'guardian-rule-source-binding/0.1',
            'source_ref': 'source-a', 'expected_sha256': hashlib.sha256(raw).hexdigest(),
            'evidence_kind': 'official_documentation', 'verified_at': '2026-10-18',
            'version_scope': 'mihomo-1_19_0', 'purpose': 'workflow-repair',
            'client_scope': ['client-a'], 'feature_gate': 'feature-a',
            'shared_service': False, 'activation_state': 'candidate'}


def action():
    return {'kind': 'user_selected_egress', 'group_name': 'approved-group'}


class TextSubclass(str):
    pass


class BytesSubclass(bytes):
    pass


class DictSubclass(dict):
    pass


class ListSubclass(list):
    pass


class RuleSourceImportTests(unittest.TestCase):
    def convert(self, raw=DOMAIN_BYTES, format_id=PLAIN, refs=None, binding=None,
                intent=None, **kwargs):
        return source.import_rule_bindings(
            raw, format_id, ['rule-a'] if refs is None else refs,
            declared_source(raw) if binding is None else binding,
            action() if intent is None else intent, **kwargs)

    def reject(self, raw=DOMAIN_BYTES, format_id=PLAIN, refs=None, binding=None,
               intent=None, code=None, **kwargs):
        with self.assertRaises(source.SourceImportError) as caught:
            self.convert(raw, format_id, refs, binding, intent, **kwargs)
        message = str(caught.exception)
        self.assertRegex(message, r'^[A-Z][A-Z0-9_]*$')
        if code is not None:
            self.assertEqual(message, code)
        for private in ('Example.test', 'approved-group', 'source-a', 'private-SENTINEL'):
            self.assertNotIn(private, message + repr(caught.exception))
        return message

    def downstream(self, imported, raw=RAW, base=BASE):
        request, binding = plan_inputs(raw, base)
        components = imported.binding_components()
        binding.update(components)
        request['intent']['rule_refs'] = components['rule_order'][:]
        request['intent']['egress_group_ref'] = components['group_name']
        return request, binding

    def test_plain_preserves_order_case_and_source_bytes(self):
        raw = b'Zulu.test\r\nAlpha.test\r\nMiddle.test'
        refs = ['rule-z', 'rule-a', 'rule-m']
        result = self.convert(raw, refs=refs)
        self.assertEqual(result.binding_components(), {
            'rules': {'rule-z': {'kind': 'DOMAIN', 'domain': 'Zulu.test'},
                      'rule-a': {'kind': 'DOMAIN', 'domain': 'Alpha.test'},
                      'rule-m': {'kind': 'DOMAIN', 'domain': 'Middle.test'}},
            'rule_order': refs, 'group_name': 'approved-group'})
        material = result.private_material()
        self.assertEqual(material['source_bytes'], raw)
        self.assertEqual(material['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(material['source_format'], PLAIN)
        records = material['records']
        self.assertIs(type(records), tuple)
        self.assertEqual([record.rule_ref for record in records], refs)
        self.assertEqual([record.source_index for record in records], [0, 1, 2])
        self.assertEqual([record.source_line for record in records], [1, 2, 3])
        self.assertEqual([record.original_record for record in records],
                         [b'Zulu.test', b'Alpha.test', b'Middle.test'])
        for record in records:
            self.assertEqual(raw[record.start:record.end], record.original_record)
            self.assertIsNone(record.source_action)
            self.assertEqual(record.action, 'approved-group')

    def test_plain_optional_bom_and_lf_crlf_final_newline_are_lossless(self):
        for bom in (b'', b'\xef\xbb\xbf'):
            for ending in (b'\n', b'\r\n'):
                for final in (b'', ending):
                    raw = bom + b'Example.test' + ending + b'Other.test' + final
                    with self.subTest(bom=bool(bom), ending=ending, final=bool(final)):
                        result = self.convert(raw, refs=['rule-a', 'rule-b'])
                        material = result.private_material()
                        self.assertEqual(material['source_bytes'], raw)
                        self.assertEqual(material['records'][0].start, len(bom))
                        self.assertEqual(material['records'][1].source_line, 2)
                        for record in material['records']:
                            self.assertEqual(raw[record.start:record.end], record.original_record)
                        self.assertEqual(result.preview()['record_count'], 2)

    def test_fragment_preserves_exact_suffix_distinction_case_and_order(self):
        raw = (b'rules:\n  - DOMAIN-SUFFIX,Example.test,approved-group\n'
               b'  - DOMAIN,Example.test,approved-group\n')
        result = self.convert(raw, FRAGMENT, ['rule-z', 'rule-a'])
        self.assertEqual(result.binding_components(), {
            'rules': {'rule-z': {'kind': 'DOMAIN-SUFFIX', 'domain': 'Example.test'},
                      'rule-a': {'kind': 'DOMAIN', 'domain': 'Example.test'}},
            'rule_order': ['rule-z', 'rule-a'], 'group_name': 'approved-group'})
        self.assertEqual(result.preview()['exact_count'], 1)
        self.assertEqual(result.preview()['suffix_count'], 1)
        for record in result.private_material()['records']:
            self.assertEqual(record.source_action, 'approved-group')
            self.assertEqual(record.action, 'approved-group')

    def test_fragment_utf8_comment_bom_crlf_offsets_are_byte_offsets(self):
        raw = (b'\xef\xbb\xbf' + '# 中文🙂 private-SENTINEL\r\n'.encode('utf-8')
               + b'rules:\r\n  - DOMAIN,Example.test,approved-group # retained\r\n'
               b'  - DOMAIN-SUFFIX,Other.test,approved-group\r\n')
        result = self.convert(raw, FRAGMENT, ['rule-a', 'rule-b'])
        material = result.private_material()
        self.assertEqual(material['source_bytes'], raw)
        self.assertEqual([record.source_line for record in material['records']], [3, 4])
        expected = [b'DOMAIN,Example.test,approved-group',
                    b'DOMAIN-SUFFIX,Other.test,approved-group']
        for record, original in zip(material['records'], expected):
            self.assertEqual(record.original_record, original)
            self.assertEqual(record.start, raw.index(original))
            self.assertEqual(raw[record.start:record.end], original)
        self.assertNotIn('private-SENTINEL', json.dumps(result.preview()) + repr(result))

    def test_public_preview_declares_limits_without_source_or_action_details(self):
        result = self.convert()
        report = result.preview()
        self.assertEqual(report['status'], 'imported_candidate_only')
        self.assertEqual((report['record_count'], report['exact_count'], report['suffix_count']),
                         (1, 1, 0))
        self.assertIs(report['apply_supported'], False)
        for field in ('source_authenticity', 'source_freshness', 'independent_sources'):
            self.assertEqual(report[field], 'not_established')
        self.assertEqual(report['native_acceptance'], 'not_run')
        public = json.dumps(report) + repr(result)
        for private in ('Example.test', 'rule-a', 'source-a', 'approved-group',
                        'workflow-repair', 'client-a', 'feature-a', '2026-10-18',
                        hashlib.sha256(DOMAIN_BYTES).hexdigest()):
            self.assertNotIn(private, public)

    def test_every_evidence_kind_stays_a_declaration(self):
        for kind in ('official_documentation', 'user_supplied', 'reference_material'):
            binding = declared_source(DOMAIN_BYTES)
            binding['evidence_kind'] = kind
            with self.subTest(kind=kind):
                result = self.convert(binding=binding)
                self.assertEqual(dict(result.private_material()['declared_source'])['evidence_kind'], kind)
                self.assertEqual(result.preview()['source_authenticity'], 'not_established')
                self.assertEqual(result.preview()['source_freshness'], 'not_established')
                self.assertFalse(result.preview()['apply_supported'])

    def test_explicit_user_action_required_for_both_formats(self):
        inputs = [(DOMAIN_BYTES, PLAIN),
                  (b'rules:\n  - DOMAIN,Example.test,approved-group\n', FRAGMENT)]
        for raw, format_id in inputs:
            for intent in (None, {}, {'group_name': 'approved-group'},
                           {'kind': 'official_recommendation', 'group_name': 'approved-group'},
                           {'kind': 'user_selected_egress', 'group_name': 'DIRECT'},
                           {'kind': 'user_selected_egress', 'group_name': 'REJECT'},
                           {'kind': 'user_selected_egress', 'group_name': 'approved-group', 'approved': True}):
                with self.subTest(format_id=format_id, intent=intent):
                    with self.assertRaises(source.SourceImportError) as caught:
                        source.import_rule_bindings(raw, format_id, ['rule-a'], declared_source(raw), intent)
                    self.assertRegex(str(caught.exception), r'^[A-Z][A-Z0-9_]*$')

    def test_source_actions_never_silently_overridden(self):
        for policy in ('Other', 'DIRECT', 'REJECT', 'approved-Group'):
            raw = ('rules:\n  - DOMAIN,Example.test,' + policy + '\n').encode('ascii')
            with self.subTest(policy=policy):
                self.reject(raw, FRAGMENT, code='SOURCE_ACTION_CONFLICT')

    def test_mixed_source_actions_fail_whole_import_in_every_position(self):
        valid = b'  - DOMAIN,Example.test,approved-group\n'
        conflict = b'  - DOMAIN,Other.test,Other\n'
        for lines in (valid + conflict, conflict + valid):
            raw = b'rules:\n' + lines
            refs, binding, intent = ['rule-a', 'rule-b'], declared_source(raw), action()
            before = deepcopy((refs, binding, intent))
            with self.subTest(conflict_first=lines.startswith(conflict)):
                self.reject(raw, FRAGMENT, refs, binding, intent, 'SOURCE_ACTION_CONFLICT')
                self.assertEqual((refs, binding, intent), before)

    def test_unsupported_records_anywhere_are_not_filtered(self):
        good = b'  - DOMAIN,Example.test,approved-group\n'
        unsupported = [b'MATCH,approved-group', b'IP-CIDR,192.0.2.0/24,approved-group',
                       b'IP-CIDR6,2001:db8::/32,approved-group', b'GEOIP,US,approved-group',
                       b'DOMAIN-KEYWORD,example,approved-group', b'RULE-SET,provider,approved-group',
                       b'DOMAIN,Other.test,approved-group,no-resolve', b'DOMAIN,Other.test',
                       b'PROCESS-NAME,example,approved-group', b'SRC-IP-CIDR,192.0.2.0/24,approved-group']
        for record in unsupported:
            bad = b'  - ' + record + b'\n'
            for lines in (bad + good, good + bad):
                with self.subTest(record=record, first=lines.startswith(bad)):
                    self.reject(b'rules:\n' + lines, FRAGMENT, ['rule-a', 'rule-b'])

    def test_plain_blank_comments_whitespace_and_other_line_endings_reject(self):
        invalid = [b'', b'\n', b'\xef\xbb\xbf', b'Example.test\n\n', b'\nExample.test',
                   b'# Example.test\n', b'Example.test # comment\n', b' Example.test\n',
                   b'Example.test \n', b'\tExample.test\n', b'Example.test\r',
                   b'Example.test\rOther.test', b'Example.test\vOther.test',
                   b'Example.test\fOther.test', b'Example.test\x00',
                   b'Example.test\n# private-SENTINEL\n', b'Example.test\n\xef\xbb\xbfOther.test']
        for raw in invalid:
            with self.subTest(raw=raw):
                self.reject(raw)

    def test_domains_reject_unicode_idna_wildcards_root_dots_and_ambiguity(self):
        domains = ['é.test', 'ｅxample.test', 'xn--bcher-kva.test', 'XN--bcher-kva.test',
                   '*.test', '.test', 'example.test.', 'bad..test', '-bad.test', 'bad-.test',
                   'bad.test-', '_srv.test', 'https://example.test', 'example.test:443',
                   'example.test/path', 'example.test?query', 'person@example.test',
                   '192.0.2.1', '127.0.0.1', '2001:db8::1', '[2001:db8::1]',
                   '127.1', '192.000.2.1', '999.999.999.999', '2130706433',
                   'a' * 64 + '.test', 'a.' * 126 + 'aa', 'private-SENTINEL\u200b.test']
        for domain in domains:
            for format_id in (PLAIN, FRAGMENT):
                raw = ((domain + '\n') if format_id == PLAIN else
                       'rules:\n  - DOMAIN,' + domain + ',approved-group\n').encode('utf-8')
                with self.subTest(domain=domain, format_id=format_id):
                    self.reject(raw, format_id)

    def test_ordinary_numeric_domain_labels_are_not_treated_as_addresses(self):
        for domain in ('123.example.invalid', 'service.123.example.invalid', '1a.example.invalid'):
            for format_id in (PLAIN, FRAGMENT):
                raw = ((domain + '\n') if format_id == PLAIN else
                       'rules:\n  - DOMAIN,' + domain + ',approved-group\n').encode('ascii')
                with self.subTest(domain=domain, format_id=format_id):
                    result = self.convert(raw, format_id)
                    self.assertEqual(result.binding_components()['rules']['rule-a'],
                                     {'kind': 'DOMAIN', 'domain': domain})

    def test_malformed_utf8_never_escapes_as_a_decode_error(self):
        for raw, format_id in ((b'\xffExample.test', PLAIN),
                               (b'rules:\n  - DOMAIN,\xff.test,approved-group\n', FRAGMENT)):
            with self.subTest(format_id=format_id):
                self.reject(raw, format_id)

    def test_fragment_is_only_a_rules_mapping_not_a_provider_or_full_config(self):
        cases = [b'payload:\n  - Example.test\n', b'rules: []\n', b'{}\n', b'[]\n',
                 b'rules:\n', b'rules: scalar\n', b'rules:\n  - true\n',
                 b'rules:\n  - 42\n', b'rules:\n  - {domain: Example.test}\n',
                 b'rules:\n  - [DOMAIN, Example.test, approved-group]\n',
                 b'rules:\n  - DOMAIN,Example.test,approved-group\nmode: rule\n',
                 b'mode: rule\nrules:\n  - DOMAIN,Example.test,approved-group\n',
                 b'proxies: []\nrules:\n  - DOMAIN,Example.test,approved-group\n']
        for raw in cases:
            with self.subTest(raw=raw):
                self.reject(raw, FRAGMENT)

    def test_fragment_rejects_quotes_flow_multiline_and_whitespace_normalization(self):
        scalars = [b'"DOMAIN,Example.test,approved-group"',
                   b"'DOMAIN,Example.test,approved-group'", b'"DOMAIN,Example\\u002etest,approved-group"',
                   b'|\n      DOMAIN,Example.test,approved-group',
                   b'>\n      DOMAIN,Example.test,approved-group',
                   b'domain,Example.test,approved-group', b'DOMAIN, Example.test,approved-group',
                   b'DOMAIN,Example.test, approved-group', b'DOMAIN ,Example.test,approved-group']
        for scalar in scalars:
            with self.subTest(scalar=scalar):
                self.reject(b'rules:\n  - ' + scalar + b'\n', FRAGMENT)
        self.reject(b'rules: ["DOMAIN,Example.test,approved-group"]\n', FRAGMENT,
                    code='UNSUPPORTED_RULE_FRAGMENT')

    def test_fragment_yaml_ambiguity_tags_anchors_and_multiple_documents_reject(self):
        good = b'rules:\n  - DOMAIN,Example.test,approved-group\n'
        cases = [good + good, good + b'---\n' + good,
                 b'rules: &r\n  - DOMAIN,Example.test,approved-group\n',
                 b'rules:\n  - &r DOMAIN,Example.test,approved-group\n',
                 b'rules:\n  - !!str DOMAIN,Example.test,approved-group\n',
                 b'rules:\n  - *r\n', b'rules: [\n',
                 b'<<: {}\n' + good, b'%YAML 1.1\n---\n' + good,
                 b'rules: !!seq\n  - DOMAIN,Example.test,approved-group\n']
        for raw in cases:
            with self.subTest(raw=raw):
                self.reject(raw, FRAGMENT)

    def test_format_must_be_exact_and_never_auto_detected(self):
        for format_id in ('exact-domain-lines', 'exact-domain-lines/0.2', 'mihomo', '', None,
                          'EXACT-DOMAIN-LINES/0.1', TextSubclass(PLAIN), 1):
            with self.subTest(format_id=format_id):
                self.reject(format_id=format_id)
        self.reject(b'rules:\n  - DOMAIN,Example.test,approved-group\n', PLAIN)
        self.reject(DOMAIN_BYTES, FRAGMENT)

    def test_hash_is_verified_against_exact_supplied_bytes(self):
        binding = declared_source(DOMAIN_BYTES)
        binding['expected_sha256'] = hashlib.sha256(b'example.test\n').hexdigest()
        self.reject(binding=binding)
        for raw in (b'Example.test\r\n', b'\xef\xbb\xbfExample.test\n', b'Example.test'):
            with self.subTest(raw=raw):
                self.reject(raw, binding=declared_source(DOMAIN_BYTES))

    def test_duplicate_refs_and_ref_count_mismatch_reject_instead_of_overwriting(self):
        raw = b'Example.test\nOther.test\n'
        for refs in (['rule-a', 'rule-a'], ['rule-a'], ['rule-a', 'rule-b', 'rule-c'], []):
            with self.subTest(refs=refs):
                self.reject(raw, refs=refs)

    def test_duplicate_selectors_and_ascii_case_collisions_reject(self):
        for second in ('Example.test', 'EXAMPLE.TEST', 'example.test'):
            with self.subTest(second=second):
                self.reject(('Example.test\n' + second + '\n').encode('ascii'),
                            refs=['rule-a', 'rule-b'])
                for kind in ('DOMAIN', 'DOMAIN-SUFFIX'):
                    raw = ('rules:\n  - ' + kind + ',Example.test,approved-group\n  - '
                           + kind + ',' + second + ',approved-group\n').encode('ascii')
                    self.reject(raw, FRAGMENT, ['rule-a', 'rule-b'])

    def test_binding_keys_are_exact_and_candidate_state_cannot_be_promoted(self):
        for key in declared_source(DOMAIN_BYTES):
            binding = declared_source(DOMAIN_BYTES)
            del binding[key]
            with self.subTest(missing=key):
                self.reject(binding=binding)
        for key, value in [('approved', True), ('source_url', 'https://example.invalid'),
                           ('source_authenticity', 'verified')]:
            binding = declared_source(DOMAIN_BYTES)
            binding[key] = value
            with self.subTest(extra=key):
                self.reject(binding=binding)
        for key, value in [('schema_version', 'guardian-rule-source-binding/0.2'),
                           ('activation_state', 'active'), ('activation_state', 'approved'),
                           ('evidence_kind', 'verified')]:
            binding = declared_source(DOMAIN_BYTES)
            binding[key] = value
            with self.subTest(key=key, value=value):
                self.reject(binding=binding)
        binding = declared_source(DOMAIN_BYTES)
        binding['shared_service'] = True
        result = self.convert(binding=binding)
        self.assertIs(dict(result.private_material()['declared_source'])['shared_service'], True)
        self.assertEqual(result.binding_components()['rules'],
                         {'rule-a': {'kind': 'DOMAIN', 'domain': 'Example.test'}})
        self.assertFalse(result.preview()['apply_supported'])

    def test_invalid_metadata_dates_hashes_scopes_and_strict_types_reject(self):
        cases = [('verified_at', '2026-02-30'), ('verified_at', '2026-10-18T00:00:00Z'),
                 ('verified_at', '18-10-2026'), ('verified_at', ''),
                 ('expected_sha256', 'a' * 63), ('expected_sha256', 'g' * 64),
                 ('expected_sha256', b'a' * 64), ('client_scope', []),
                 ('client_scope', ['client-a', 'client-a']), ('client_scope', 'client-a'),
                 ('client_scope', ['client-a', 1]), ('shared_service', 0),
                 ('evidence_kind', TextSubclass('user_supplied')),
                 ('schema_version', TextSubclass('guardian-rule-source-binding/0.1')),
                 ('activation_state', TextSubclass('candidate')),
                 ('verified_at', TextSubclass('2026-10-18'))]
        for key, value in cases:
            binding = declared_source(DOMAIN_BYTES)
            binding[key] = value
            with self.subTest(key=key, value=value):
                self.reject(binding=binding)

    def test_aliases_are_opaque_ascii_not_urls_paths_email_or_free_text(self):
        invalid = ['', 'a' * 65, '1source', '-source', 'source/a', '../source',
                   'person@example.test', 'https://example.test', 'source a', 'sourcé',
                   'source\n', TextSubclass('source-a'), None, 1]
        for value in invalid:
            for key in ('source_ref', 'version_scope', 'purpose', 'feature_gate'):
                binding = declared_source(DOMAIN_BYTES)
                binding[key] = value
                with self.subTest(key=key, value=value):
                    self.reject(binding=binding)
            with self.subTest(location='client_scope', value=value):
                binding = declared_source(DOMAIN_BYTES)
                binding['client_scope'] = [value]
                self.reject(binding=binding)
            with self.subTest(location='rule_ref', value=value):
                self.reject(refs=[value])
            with self.subTest(location='group', value=value):
                self.reject(intent={'kind': 'user_selected_egress', 'group_name': value})

    def test_recognized_credential_shapes_rejected_without_echo(self):
        credentials = ['ghp_' + 'x' * 36, 'github_pat_' + 'x' * 40,
                       'source-gho_' + 'x' * 36, 'sk-' + 'x' * 32,
                       'sk-ant-' + 'x' * 32, 'xoxb-' + 'x' * 24]
        for credential in credentials:
            for key in ('source_ref', 'version_scope', 'purpose', 'feature_gate'):
                binding = declared_source(DOMAIN_BYTES)
                binding[key] = credential
                with self.subTest(prefix=credential[:5], key=key):
                    self.assertNotIn(credential, self.reject(binding=binding))
            binding = declared_source(DOMAIN_BYTES)
            binding['client_scope'] = [credential]
            self.assertNotIn(credential, self.reject(binding=binding))
            self.assertNotIn(credential, self.reject(refs=[credential]))
            self.assertNotIn(credential, self.reject(
                intent={'kind': 'user_selected_egress', 'group_name': credential}))

    def test_security_words_and_short_prefixes_remain_valid_aliases(self):
        aliases = ['source-token-guide', 'secret-case', 'credential-example', 'sk-guide',
                   'ghp_example', 'github_pat_note', 'xoxb_example', 'A' * 64]
        for alias in aliases:
            binding = declared_source(DOMAIN_BYTES)
            for key in ('source_ref', 'version_scope', 'purpose', 'feature_gate'):
                binding[key] = alias
            binding['client_scope'] = [alias]
            with self.subTest(alias=alias):
                result = self.convert(refs=[alias], binding=binding,
                                      intent={'kind': 'user_selected_egress', 'group_name': alias})
                self.assertEqual(result.binding_components()['rule_order'], [alias])
                self.assertEqual(result.binding_components()['group_name'], alias)

    def test_builtin_only_sources_and_containers_reject_subclasses(self):
        binding = declared_source(DOMAIN_BYTES)
        for raw in (bytearray(DOMAIN_BYTES), memoryview(DOMAIN_BYTES),
                    BytesSubclass(DOMAIN_BYTES), DOMAIN_BYTES.decode('ascii'), None):
            with self.subTest(source_type=type(raw).__name__):
                self.reject(raw, binding=binding)
        for refs in (ListSubclass(['rule-a']), iter(['rule-a']), {'rule-a'}, 'rule-a'):
            with self.subTest(ref_type=type(refs).__name__):
                self.reject(refs=refs)
        self.reject(binding=DictSubclass(binding))
        self.reject(intent=DictSubclass(action()))
        nested = declared_source(DOMAIN_BYTES)
        nested['client_scope'] = ListSubclass(['client-a'])
        self.reject(binding=nested)

    def test_record_limit_accepts_256_and_rejects_257_without_partial_result(self):
        for count in (256, 257):
            raw = ''.join(f'host{i}.test\n' for i in range(count)).encode('ascii')
            refs = [f'rule-{i}' for i in range(count)]
            with self.subTest(count=count):
                if count == 256:
                    result = self.convert(raw, refs=refs)
                    self.assertEqual(result.preview()['record_count'], count)
                    self.assertEqual(result.binding_components()['rule_order'], refs)
                else:
                    self.reject(raw, refs=refs)

    def test_source_byte_limit_is_one_mebibyte(self):
        prefix = b'#'
        tail = b'\nrules:\n  - DOMAIN,Example.test,approved-group\n'
        raw = prefix + b'x' * (1024 * 1024 - len(prefix) - len(tail)) + tail
        self.assertEqual(len(raw), 1024 * 1024)
        self.assertEqual(self.convert(raw, FRAGMENT).preview()['record_count'], 1)
        self.reject(raw + b'\n', FRAGMENT)

    def test_deadline_arguments_and_initial_deadline_are_bounded(self):
        for value in (True, False, 0, -1, 61, float('nan'), float('inf'), '5', None):
            with self.subTest(value=value):
                self.reject(max_seconds=value, code='INVALID_DEADLINE')
        with patch.object(source.time, 'monotonic', side_effect=[0, 6]):
            self.reject(code='DEADLINE_EXCEEDED')

    def test_cancellation_before_and_during_import_is_atomic(self):
        self.reject(cancelled=lambda: True, code='CANCELLED')
        def failed_callback():
            raise RuntimeError('private-SENTINEL')
        self.reject(cancelled=failed_callback, code='CANCELLED')
        calls = []
        def stop_during_work():
            calls.append(True)
            return len(calls) >= 2
        raw = b'Example.test\nOther.test\n'
        binding, refs, intent = declared_source(raw), ['rule-a', 'rule-b'], action()
        before = deepcopy((binding, refs, intent))
        self.reject(raw, refs=refs, binding=binding, intent=intent,
                    cancelled=stop_during_work, code='CANCELLED')
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual((binding, refs, intent), before)

    def test_final_boundary_cancellation_cannot_return_a_built_candidate(self):
        samples = [(DOMAIN_BYTES, PLAIN),
                   (b'rules:\n  - DOMAIN,Example.test,approved-group\n', FRAGMENT)]
        for raw, format_id in samples:
            with self.subTest(format_id=format_id), patch.object(
                    source, 'RuleRecord', wraps=source.RuleRecord) as built:
                self.reject(raw, format_id, cancelled=lambda: built.call_count > 0,
                            code='CANCELLED')
                self.assertEqual(built.call_count, 1)

    def test_final_boundary_deadline_cannot_return_a_built_candidate(self):
        samples = [(DOMAIN_BYTES, PLAIN),
                   (b'rules:\n  - DOMAIN,Example.test,approved-group\n', FRAGMENT)]
        for raw, format_id in samples:
            with self.subTest(format_id=format_id), patch.object(
                    source, 'RuleRecord', wraps=source.RuleRecord) as built:
                with patch.object(source.time, 'monotonic',
                                  side_effect=lambda: 6 if built.call_count else 0):
                    self.reject(raw, format_id, code='DEADLINE_EXCEEDED')
                self.assertEqual(built.call_count, 1)

    def test_tuple_refs_and_client_scope_are_copied_with_a_sixteen_client_limit(self):
        binding = declared_source(DOMAIN_BYTES)
        clients = tuple(f'client-{index}' for index in range(16))
        binding['client_scope'] = clients
        result = self.convert(refs=('rule-a',), binding=binding)
        self.assertEqual(result.binding_components()['rule_order'], ['rule-a'])
        self.assertEqual(dict(result.private_material()['declared_source'])['client_scope'], clients)
        binding['client_scope'] = clients + ('client-16',)
        self.reject(binding=binding, code='INVALID_SOURCE_BINDING')

    def test_public_rejection_codes_are_stable_for_the_declared_boundaries(self):
        mismatched = declared_source(DOMAIN_BYTES)
        mismatched['expected_sha256'] = '0' * 64
        self.reject(binding=mismatched, code='SOURCE_DIGEST_MISMATCH')
        self.reject(format_id='unknown-format', code='UNSUPPORTED_SOURCE_FORMAT')
        self.reject(intent={}, code='EXPLICIT_ACTION_REQUIRED')
        self.reject(binding={}, code='INVALID_SOURCE_BINDING')
        self.reject(b'Example.test\nOther.test\n', refs=['rule-a', 'rule-a'],
                    code='DUPLICATE_RULE_REFERENCE')
        self.reject(b'Example.test\nOther.test\n', code='RULE_REFERENCE_COUNT_MISMATCH')
        self.reject(b'Example.test\nEXAMPLE.TEST\n', refs=['rule-a', 'rule-b'],
                    code='DUPLICATE_RULE_SELECTOR')
        self.reject(b'\xffExample.test\n', code='INVALID_SOURCE_ENCODING')
        self.reject(b'example.test.\n', code='UNSUPPORTED_DOMAIN')
        self.reject(b'rules:\n  - MATCH,approved-group\n', FRAGMENT,
                    code='UNSUPPORTED_RULE_RECORD')
        self.reject(b'x' * (1024 * 1024 + 1), code='INVALID_OR_OVERSIZED_SOURCE')
        # Keep refs within their own budget so this reaches the source-record gate.
        refs = [f'rule-{index}' for index in range(256)]
        domains = [f'host{index}.test' for index in range(257)]
        self.reject(('\n'.join(domains) + '\n').encode('ascii'), refs=refs,
                    code='TOO_MANY_SOURCE_RECORDS')
        fragment = ('rules:\n' + ''.join(
            '  - DOMAIN,' + domain + ',approved-group\n' for domain in domains)).encode('ascii')
        self.reject(fragment, FRAGMENT, refs, code='TOO_MANY_SOURCE_RECORDS')

    def test_missing_optional_parser_only_blocks_yaml_fragment(self):
        with patch.object(source.config, 'yaml', None):
            self.assertEqual(self.convert().preview()['record_count'], 1)
            self.reject(b'rules:\n  - DOMAIN,Example.test,approved-group\n', FRAGMENT,
                        code='PARSER_UNAVAILABLE')

    def test_extracted_package_plain_import_without_site_yaml_and_current_guidance(self):
        fragment = b'rules:\n  - DOMAIN,Example.test,approved-group\n'
        payload = {'plain_binding': declared_source(DOMAIN_BYTES),
                   'fragment_binding': declared_source(fragment), 'action': action()}
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / 'skill.zip'
            subprocess.run([sys.executable, str(ROOT / 'tools/package_skill.py'),
                            '--output', str(archive_path)], check=True, capture_output=True,
                           timeout=30)
            with zipfile.ZipFile(archive_path) as archive:
                for relative in ('scripts/rule_source_import.py', 'references/agent-remediation.md'):
                    self.assertEqual(archive.read('claude-guardian/' + relative),
                                     (SKILL / relative).read_bytes())
                guidance = archive.read('claude-guardian/references/agent-remediation.md').decode('utf-8')
                self.assertIn(PLAIN, guidance)
                self.assertIn(FRAGMENT, guidance)
                self.assertIn('PARSER_UNAVAILABLE', guidance)
                # The archive is produced by the repository's explicit allowlist,
                # and this temporary destination has no installed user skill.
                archive.extractall(temporary)
            scripts = Path(temporary) / 'claude-guardian/scripts'
            snippet = '''
import json, pathlib, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import rule_source_import as source
assert pathlib.Path(source.__file__).parent == pathlib.Path(sys.argv[1])
assert source.config.yaml is None, 'Unexpected optional parser under -I -S'
fixture = json.loads(sys.argv[2])
raw = b'Example.test\\n'
result = source.import_rule_bindings(raw, 'exact-domain-lines/0.1', ['rule-a'],
                                    fixture['plain_binding'], fixture['action'])
assert result.binding_components() == {
    'rules': {'rule-a': {'kind': 'DOMAIN', 'domain': 'Example.test'}},
    'rule_order': ['rule-a'], 'group_name': 'approved-group'}
assert result.private_material()['source_bytes'] == raw
try:
    source.import_rule_bindings(b'rules:\\n  - DOMAIN,Example.test,approved-group\\n',
        'mihomo-domain-rules-fragment/0.1', ['rule-a'],
        fixture['fragment_binding'], fixture['action'])
except source.SourceImportError as error:
    assert str(error) == 'PARSER_UNAVAILABLE'
else:
    raise AssertionError('Missing YAML parser was silently bypassed')
print(json.dumps(result.preview()))
'''
            completed = subprocess.run(
                [sys.executable, '-I', '-S', '-c', snippet, str(scripts), json.dumps(payload)],
                cwd=temporary, check=True, capture_output=True, text=True, encoding='utf-8', timeout=30)
        report = json.loads(completed.stdout)
        self.assertEqual(report['status'], 'imported_candidate_only')
        self.assertEqual(report['record_count'], 1)
        self.assertFalse(report['apply_supported'])
        self.assertEqual(report['native_acceptance'], 'not_run')
        self.assertEqual(report['source_authenticity'], 'not_established')
        self.assertEqual(report['source_freshness'], 'not_established')
        self.assertEqual(report['independent_sources'], 'not_established')
        self.assertNotIn('Example.test', completed.stdout + completed.stderr)
        self.assertNotIn('approved-group', completed.stdout + completed.stderr)

    def test_result_records_and_declared_metadata_are_frozen(self):
        result = self.convert()
        material = result.private_material()
        self.assertIs(type(material['declared_source']), tuple)
        self.assertIs(type(dict(material['declared_source'])['client_scope']), tuple)
        record = material['records'][0]
        with self.assertRaises((AttributeError, TypeError)):
            record.domain = 'other.test'
        with self.assertRaises((AttributeError, TypeError)):
            record.source_index = 99
        slots = set()
        for cls in type(result).__mro__:
            slots.update(getattr(cls, '__slots__', ()))
        for field in slots - {'__weakref__', '__dict__'}:
            with self.subTest(field=field), self.assertRaises((AttributeError, TypeError)):
                setattr(result, field, getattr(result, field))
        with self.assertRaises((AttributeError, TypeError)):
            result.extra = 'mutable'

    def test_returned_copies_and_caller_changes_cannot_modify_private_result(self):
        binding, refs, intent = declared_source(DOMAIN_BYTES), ['rule-a'], action()
        result = self.convert(binding=binding, refs=refs, intent=intent)
        expected = result.binding_components()
        components = result.binding_components()
        components['rules']['rule-a']['domain'] = 'other.test'
        components['rules']['rule-b'] = {'kind': 'DOMAIN', 'domain': 'new.test'}
        components['rule_order'].append('rule-b')
        components['group_name'] = 'changed'
        binding['client_scope'].append('client-b')
        binding['purpose'] = 'changed'
        refs.append('rule-b')
        intent['group_name'] = 'changed'
        material = result.private_material()
        material['records'] = ()
        material['declared_source'] = ()
        material['source_bytes'] = b'changed'
        report = result.preview()
        report['record_count'] = 100
        report['apply_supported'] = True
        self.assertEqual(result.binding_components(), expected)
        self.assertEqual(result.private_material()['source_bytes'], DOMAIN_BYTES)
        self.assertEqual(len(result.private_material()['records']), 1)
        self.assertEqual(dict(result.private_material()['declared_source'])['client_scope'], ('client-a',))
        self.assertEqual(dict(result.private_material()['declared_source'])['purpose'], 'workflow-repair')
        self.assertEqual(result.preview()['record_count'], 1)
        self.assertFalse(result.preview()['apply_supported'])

    def test_private_result_and_records_do_not_leak_through_repr_json_or_pickle(self):
        result = self.convert()
        record = result.private_material()['records'][0]
        for item in (result, record):
            for private in ('Example.test', 'approved-group', 'rule-a', 'source-a',
                            hashlib.sha256(DOMAIN_BYTES).hexdigest()):
                self.assertNotIn(private, repr(item))
            with self.assertRaises(TypeError):
                json.dumps(item)
            with self.assertRaises(TypeError):
                pickle.dumps(item)

    def test_conversion_is_pure_and_input_objects_are_unchanged(self):
        samples = [(DOMAIN_BYTES, PLAIN),
                   (b'rules:\n  - DOMAIN,Example.test,approved-group\n', FRAGMENT)]
        for raw, format_id in samples:
            binding, refs, intent = declared_source(raw), ['rule-a'], action()
            before = deepcopy((binding, refs, intent))
            with (self.subTest(format_id=format_id),
                  patch('builtins.open', side_effect=AssertionError('file')),
                  patch('pathlib.Path.open', side_effect=AssertionError('path')),
                  patch('socket.socket', side_effect=AssertionError('network')),
                  patch('socket.getaddrinfo', side_effect=AssertionError('DNS')),
                  patch('subprocess.Popen', side_effect=AssertionError('process')),
                  patch('os.system', side_effect=AssertionError('shell'))):
                result = self.convert(raw, format_id, binding=binding, refs=refs, intent=intent)
            self.assertEqual((binding, refs, intent), before)
            self.assertEqual(result.preview()['record_count'], 1)

    def test_downstream_conversion_uses_actual_plan_and_keeps_native_apply_blocked(self):
        imported = self.convert()
        request, binding = self.downstream(imported)
        candidate = rules.compile_rules_extension(RAW, BASE, request, binding)
        self.assertEqual(candidate.private_material()['candidate_bytes'],
                         RAW.replace(b'prepend: []', b"prepend: ['DOMAIN,Example.test,approved-group']"))
        self.assertEqual(candidate.preview()['status'], 'candidate_only_blocked')
        self.assertFalse(candidate.preview()['apply_supported'])
        self.assertEqual(candidate.preview()['native_acceptance'], 'not_run')
        for blocker in rules.NATIVE_BLOCKERS + ('ACTION_AUTHORIZATION_PENDING',):
            self.assertIn(blocker, candidate.preview()['blockers'])

    def test_downstream_preserves_order_and_keeps_overlap_check_authority(self):
        raw = (b'rules:\n  - DOMAIN-SUFFIX,Other.example,approved-group\n'
               b'  - DOMAIN,Example.test,approved-group\n')
        imported = self.convert(raw, FRAGMENT, ['rule-z', 'rule-a'])
        request, binding = self.downstream(imported)
        candidate = rules.compile_rules_extension(RAW, BASE, request, binding)
        self.assertEqual(candidate.private_material()['ordered_additions'], (
            ('rule-z', 'DOMAIN-SUFFIX,Other.example,approved-group'),
            ('rule-a', 'DOMAIN,Example.test,approved-group')))
        raw = raw.replace(b'Other.example', b'Example.test')
        imported = self.convert(raw, FRAGMENT, ['rule-z', 'rule-a'])
        self.assertEqual(imported.preview()['record_count'], 2)
        request, binding = self.downstream(imported)
        with self.assertRaisesRegex(rules.RulesPlanError, '^OVERLAPPING_SELECTED_RULES$'):
            rules.compile_rules_extension(RAW, BASE, request, binding)

    def test_downstream_protected_group_and_duplicate_guards_are_not_bypassed(self):
        imported = self.convert()
        cases = [(BASE, [1], 'PROTECTED_RULE_PRIORITY_CONFLICT'),
                 (BASE, [2], 'PROTECTED_RULE_PRIORITY_CONFLICT'),
                 (BASE.replace(b'name: approved-group', b'name: other-group'), [0],
                  'EGRESS_GROUP_MISSING_OR_AMBIGUOUS'),
                 (BASE.replace(b'    type: select', b'  - name: approved-group\n    type: select'), [0],
                  'EGRESS_GROUP_MISSING_OR_AMBIGUOUS'),
                 (BASE.replace(b'DOMAIN,local.test,Local', b'DOMAIN,EXAMPLE.TEST,Other'), [],
                  'RULE_SELECTOR_ALREADY_PRESENT'),
                 (BASE.replace(b'DOMAIN,local.test,Local', b'RULE-SET,organization,Local'), [0],
                  'PROTECTED_RULE_TYPE_UNSUPPORTED')]
        for base, protected, code in cases:
            request, binding = self.downstream(imported, base=base)
            binding['protected_rule_indexes'] = protected
            with self.subTest(code=code), self.assertRaisesRegex(rules.RulesPlanError, '^' + code + '$'):
                rules.compile_rules_extension(RAW, base, request, binding)

    def test_downstream_stale_snapshots_versions_and_semantic_gates_still_block(self):
        imported = self.convert()
        for change in ('extension', 'effective', 'stale', 'version', 'protected', 'cancelled'):
            request, binding = self.downstream(imported)
            if change in ('extension', 'effective'):
                request['revisions'][change] = '0' * 64
                request['current_revisions'] = deepcopy(request['revisions'])
            elif change == 'stale':
                request['current_revisions']['extension'] = '0' * 64
            elif change == 'version':
                request['facts']['versions']['gui'] = '2.5.7'
            elif change == 'protected':
                request['facts']['rules']['protected_priority_preserved'] = 'unknown'
            else:
                request['cancelled'] = True
            with self.subTest(change=change), self.assertRaises(rules.RulesPlanError):
                rules.compile_rules_extension(RAW, BASE, request, binding)


if __name__ == '__main__':
    unittest.main()
