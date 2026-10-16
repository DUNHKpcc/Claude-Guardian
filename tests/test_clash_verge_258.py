"""Synthetic supplied snapshots; no installed-product/native acceptance."""
import hashlib
import json
from pathlib import Path
import pickle
import plistlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import clash_verge_258 as a
from test_config_edit_plan import RAW

INDEX = b'''current: profile-a
items:
  - uid: profile-a
    type: remote
    file: source.yaml
    url: synthetic-private-SENTINEL
    option:
      merge: merge-a
  - uid: merge-a
    type: merge
    file: extension.yaml
'''
INFO = {'CFBundleIdentifier': 'io.github.clash-verge-rev.clash-verge-rev',
        'CFBundleShortVersionString': '2.5.8', 'CFBundleVersion': '2.5.8'}


class Clash258(unittest.TestCase):
    def inspect(self, index=INDEX, extension=RAW, info=None, **selection):
        return a.inspect_linkage(plistlib.dumps(info or INFO), index, extension,
                                 selected_uid=selection.get('selected_uid', 'merge-a'),
                                 selected_basename=selection.get('selected_basename', 'extension.yaml'))

    def test_exact_linkage_private_binding_not_authority(self):
        result = self.inspect()
        material = result.private_material()
        self.assertEqual(material['current_uid'], 'profile-a')
        self.assertEqual(material['extension_uid'], 'merge-a')
        self.assertEqual(material['extension_sha256'], hashlib.sha256(RAW).hexdigest())
        report = result.public_report()
        self.assertEqual(report['status'], 'supplied_metadata_only')
        self.assertFalse(report['apply_supported'])
        self.assertEqual(report['rule_merge_semantics'], 'replaces_base_rules_sequence')
        self.assertIn('EFFECTIVE_MERGE_CHAIN_UNVERIFIED', report['blockers'])
        for value in ('synthetic-private-SENTINEL', 'profile-a', 'merge-a', 'extension.yaml',
                      'secret-SENTINEL', hashlib.sha256(RAW).hexdigest()):
            self.assertNotIn(value, json.dumps(report) + repr(result))
        with self.assertRaises(TypeError):
            pickle.dumps(result)

    def test_version_product_and_field_type_exact(self):
        for field, value in [('CFBundleIdentifier', 'unrelated'),
                             ('CFBundleShortVersionString', '2.5.9'),
                             ('CFBundleVersion', '2.5.7'),
                             ('CFBundleVersion', ['2.5.8'])]:
            with self.assertRaisesRegex(a.OwnershipError, '^UNSUPPORTED_PRODUCT_OR_VERSION$'):
                self.inspect(info=dict(INFO, **{field: value}))

    def test_explicit_rules_linkage_and_format(self):
        index = INDEX.replace(b'merge: merge-a', b'rules: merge-a').replace(b'type: merge', b'type: rules')
        result = a.inspect_linkage(plistlib.dumps(INFO), index,
                                   b'prepend: []\nappend: []\ndelete: []\n',
                                   selected_uid='merge-a', selected_basename='extension.yaml',
                                   extension_kind='rules')
        self.assertEqual(result.public_report()['format'], 'rules_seqmap')
        self.assertEqual(result.private_material()['base_basename'], 'source.yaml')
        self.assertFalse(result.public_report()['apply_supported'])
        with self.assertRaisesRegex(a.OwnershipError, '^UNSUPPORTED_RULES_SEQMAP_FORMAT$'):
            a.inspect_linkage(plistlib.dumps(INFO), index, RAW,
                              selected_uid='merge-a', selected_basename='extension.yaml',
                              extension_kind='rules')
        with self.assertRaisesRegex(a.OwnershipError, '^INVALID_PROFILE_INDEX$'):
            a.inspect_linkage(plistlib.dumps(INFO), INDEX, b'prepend: []\nappend: []\ndelete: []\n',
                              selected_uid='merge-a', selected_basename='extension.yaml',
                              extension_kind='rules')

    def test_case_alias_and_path_bearing_references_rejected(self):
        alias = INDEX + b'  - uid: alias\n    type: merge\n    file: EXTENSION.yaml\n'
        with self.assertRaisesRegex(a.OwnershipError, '^AMBIGUOUS_EXTENSION_FILE_OWNER$'):
            self.inspect(index=alias)
        for filename in ('../extension.yaml', 'nested/extension.yaml', 'x\\extension.yaml'):
            index = INDEX + ('  - uid: alias\n    type: merge\n    file: ' + filename + '\n').encode()
            with self.assertRaisesRegex(a.OwnershipError, '^UNSAFE_PROFILE_FILE_REFERENCE$'):
                self.inspect(index=index)

    def test_shared_or_global_extension_scope_rejected(self):
        index = INDEX + b'  - uid: other-profile\n    type: local\n    option:\n      merge: merge-a\n'
        with self.assertRaisesRegex(a.OwnershipError, '^SHARED_EXTENSION_SCOPE_UNSUPPORTED$'):
            self.inspect(index=index)
        for uid in ('Merge', 'Script', 'Rules', 'Proxies', 'Groups'):
            with self.assertRaisesRegex(a.OwnershipError, '^GLOBAL_OR_DEFAULT_EXTENSION_SCOPE_UNSUPPORTED$'):
                self.inspect(index=INDEX.replace(b'merge-a', uid.encode()), selected_uid=uid)

    def test_duplicate_uids_anywhere_rejected(self):
        for uid in ('profile-a', 'merge-a'):
            index = INDEX + ('  - uid: ' + uid + '\n    type: local\n').encode()
            with self.assertRaisesRegex(a.OwnershipError, '^DUPLICATE_OR_INVALID_PROFILE_UID$'):
                self.inspect(index=index)

    def test_duplicate_file_owner_rejected(self):
        index = INDEX + b'  - uid: alias\n    type: merge\n    file: extension.yaml\n'
        with self.assertRaisesRegex(a.OwnershipError, '^AMBIGUOUS_EXTENSION_FILE_OWNER$'):
            self.inspect(index=index)

    def test_wrong_current_or_link(self):
        for old, new, code in [(b'current: profile-a', b'current: missing', 'PROFILE_LINK_MISSING'),
                               (b'merge: merge-a', b'merge: other', 'SELECTED_EXTENSION_NOT_ACTIVE_MERGE'),
                               (b'type: remote', b'type: merge', 'UNSUPPORTED_ACTIVE_PROFILE_TYPE')]:
            with self.assertRaisesRegex(a.OwnershipError, '^' + code + '$'):
                self.inspect(index=INDEX.replace(old, new))

    def test_rules_script_and_subscription_not_merge_targets(self):
        for kind in (b'rules', b'script', b'remote', b'local'):
            with self.assertRaisesRegex(a.OwnershipError, '^UNSUPPORTED_EXTENSION_TYPE$'):
                self.inspect(index=INDEX.replace(b'type: merge', b'type: ' + kind))

    def test_no_traversal_or_ambiguous_basenames(self):
        for value in ('../extension.yaml', '/extension.yaml', 'x/extension.yaml',
                      'x\\extension.yaml', '.', '..', 'extension.yaml\n',
                      'extension..yaml', 'ｅxtension.yaml'):
            with self.assertRaisesRegex(a.OwnershipError, '^INVALID_EXTENSION_SELECTION$'):
                self.inspect(selected_basename=value)
        with self.assertRaisesRegex(a.OwnershipError, '^EXTENSION_FILE_MISMATCH$'):
            self.inspect(index=INDEX.replace(b'file: extension.yaml', b'file: other.yaml'))

    def test_no_synthesis_from_missing_rules_or_seqmap(self):
        for raw in (b'other: true\n', b'prepend: []\nappend: []\ndelete: []\n',
                    b'rules: []\n', b'proxy-groups: []\n'):
            with self.assertRaisesRegex(a.OwnershipError, '^UNSUPPORTED_EXISTING_MERGE_FORMAT$'):
                self.inspect(extension=raw)
        with self.assertRaisesRegex(a.OwnershipError, '^RULES_EXTENSION_FORMAT_NOT_MERGE$'):
            self.inspect(extension=RAW + b'prepend: []\n')

    def test_script_and_sequence_chains_explicitly_blocked(self):
        index = INDEX.replace(b'      merge: merge-a',
                              b'      merge: merge-a\n      script: script-a\n      rules: rules-a')
        index += b'  - uid: Script\n    type: script\n    file: global.js\n'
        blockers = self.inspect(index=index).public_report()['blockers']
        for code in ('PROFILE_SCRIPT_CHAIN_UNSUPPORTED', 'PROFILE_RULES_CHAIN_UNSUPPORTED',
                     'GLOBAL_SCRIPT_CHAIN_UNSUPPORTED'):
            self.assertIn(code, blockers)

    def test_no_io_and_missing_parser(self):
        with patch('builtins.open', side_effect=AssertionError('file')), \
                patch('socket.socket', side_effect=AssertionError('network')), \
                patch('subprocess.Popen', side_effect=AssertionError('process')):
            self.inspect()
        with patch.object(a.compiler, 'yaml', None):
            with self.assertRaisesRegex(a.OwnershipError, '^PARSER_UNAVAILABLE$'):
                self.inspect()

    def test_malformed_and_bounded_plist_errors_private(self):
        for raw in (b'private-SENTINEL', b'<plist><dict>private-SENTINEL',
                    b'x' * (a.MAX_PLIST_BYTES + 1)):
            with self.assertRaises(a.OwnershipError) as caught:
                a.inspect_linkage(raw, INDEX, RAW, selected_uid='merge-a', selected_basename='extension.yaml')
            self.assertNotIn('private-SENTINEL', str(caught.exception))
        nested = 'x'
        for _ in range(34):
            nested = [nested]
        with self.assertRaisesRegex(a.OwnershipError, '^APP_METADATA_BUDGET_EXCEEDED$'):
            self.inspect(info=dict(INFO, extra=nested))

    def test_duplicate_plist_keys_rejected_xml_and_binary(self):
        xml = plistlib.dumps(INFO).replace(b'</dict>',
                b'<key>CFBundleIdentifier</key><string>other-product</string></dict>')
        binary = plistlib.dumps(dict(INFO, CFBundleVersioX='wrong'), fmt=plistlib.FMT_BINARY)
        binary = binary.replace(b'CFBundleVersioX', b'CFBundleVersion')
        for raw, code in ((xml, 'DUPLICATE_OR_INVALID_APP_METADATA_KEY'),
                          (binary, 'INVALID_APP_METADATA')):
            # plistlib wraps binary-parser ValueErrors as InvalidFileException.
            with self.assertRaisesRegex(a.OwnershipError, '^' + code + '$'):
                a.inspect_linkage(raw, INDEX, RAW, selected_uid='merge-a',
                                  selected_basename='extension.yaml')

    def test_cancellation_and_deadline(self):
        args = (plistlib.dumps(INFO), INDEX, RAW)
        selection = dict(selected_uid='merge-a', selected_basename='extension.yaml')
        with patch.object(a, '_plist', side_effect=AssertionError('parse')):
            with self.assertRaisesRegex(a.OwnershipError, '^CANCELLED$'):
                a.inspect_linkage(*args, **selection, cancelled=lambda: True)
            with patch.object(a.time, 'monotonic', side_effect=[0, 6]):
                with self.assertRaisesRegex(a.OwnershipError, '^DEADLINE_EXCEEDED$'):
                    a.inspect_linkage(*args, **selection)
        for invalid in (True, float('nan'), 0, 61):
            with self.assertRaisesRegex(a.OwnershipError, '^INVALID_DEADLINE$'):
                a.inspect_linkage(*args, **selection, max_seconds=invalid)

    def test_yaml_duplicates_and_aliases_refused(self):
        for index in (INDEX + b'current: profile-b\n',
                      INDEX.replace(b'option:', b'option: &alias'),
                      INDEX.replace(b'items:', b'items: !!seq')):
            with self.assertRaisesRegex(a.OwnershipError, '^INVALID_OR_UNSUPPORTED_YAML$'):
                self.inspect(index=index)


if __name__ == '__main__':
    unittest.main()
