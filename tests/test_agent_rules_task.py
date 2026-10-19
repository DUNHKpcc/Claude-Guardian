"""Synthetic Agent task/comparison tests, never native/app execution evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pickle
import plistlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import agent_rules_task as a
from environment_entry_fixture import local_entry
from test_clash_verge_258 import INFO
from test_rules_extension_plan import BASE, inputs

RAW = b'prepend: []\nappend: []\ndelete: []\n'
COMMENTED_RAW = ('# private-comment-SENTINEL 中文🙂\n'
                 'prepend: [] # keep prepend\n'
                 'append: [] # keep append\n'
                 'delete: [] # keep delete\n'
                 '# keep tail\n').encode('utf-8')
INDEX = b'''current: profile-private
items:
  - uid: profile-private
    type: remote
    file: source-private.yaml
    option:
      rules: rules-private
  - uid: rules-private
    type: rules
    file: extension-private.yaml
'''


def arguments(raw=RAW, base=BASE):
    request, binding = inputs(raw, base)
    return (request, binding), {
        'app_plist': plistlib.dumps(INFO), 'profile_index': INDEX,
        'extension': raw, 'base': base, 'selected_uid': 'rules-private',
        'selected_basename': 'extension-private.yaml', 'base_basename': 'source-private.yaml',
        'entry_request': local_entry('mac-a'),
        'refs': {'task_ref': 'task-a', 'host_scope_ref': 'host-a', 'app_ref': 'app-a',
                 'profile_ref': 'profile-a', 'backup_ref': 'backup-a', 'recovery_ref': 'rescue-a'},
        'source_kinds': dict.fromkeys(('app_plist', 'profile_index', 'extension', 'base'), 'file_bytes'),
    }


class AgentRulesTaskTests(unittest.TestCase):
    def prepare(self, raw=RAW, base=BASE, **changes):
        args, kw = arguments(raw, base)
        kw.update(changes)
        return a.prepare_rules_task(*args, **kw)

    def compare(self, task, raw=None, **changes):
        _, kw = arguments()
        kw.pop('refs')
        if raw is None:
            raw = task.private_material()['candidate_bytes']
        kw['extension'] = raw
        kw.update(changes)
        return a.assess_supplied_readback(task, **kw)

    def reject(self, code, args=None, kw=None):
        if args is None:
            args, kw = arguments()
        with self.assertRaisesRegex(a.TaskError, '^' + code + '$') as caught:
            a.prepare_rules_task(*args, **kw)
        self.assertEqual(caught.exception.code, code)

    def test_callable_task_has_private_exact_candidate_and_fixed_actionable_steps(self):
        task = self.prepare()
        report, review, material = task.public_report(), task.private_review(), task.private_material()
        expected = RAW.replace(b'prepend: []', b"prepend: ['DOMAIN,example.test,approved-group']")
        self.assertEqual(material['original_bytes'], RAW)
        self.assertEqual(material['candidate_bytes'], expected)
        self.assertEqual(material['candidate_sha256'], hashlib.sha256(expected).hexdigest())
        self.assertEqual(review['selected_additions'], [('rule-a', 'DOMAIN,example.test,approved-group')])
        self.assertEqual(review['selection']['extension_uid'], 'rules-private')
        self.assertEqual(report['status'], 'needs_host_review')
        self.assertEqual(report['executor'], 'agent_supported_application')
        self.assertEqual([step['id'] for step in report['steps']], [key for key, _ in a._STEPS])
        self.assertIn('current_configuration_entry', report['required_host_checks'])
        recheck = next(step for step in report['steps'] if step['id'] == 'fresh_editor_recheck')
        self.assertIn('current configuration entry', recheck['instruction'])
        self.assertIn('before Save', recheck['instruction'])
        self.assertEqual(report['authority'], 'none')
        self.assertFalse(report['builtin_apply_supported'])
        self.assertIn('NATIVE_SCHEMA_ADAPTER_NOT_IMPLEMENTED', report['compiler_blockers'])
        self.assertIn('NATIVE_CONTEXT_NOT_BOUND', report['linkage_blockers'])
        self.assertEqual(review['format_scope'], 'comment_free_three_sequence_yaml_formatting_only')

    def test_legal_comments_preserve_exact_original_and_candidate_bytes(self):
        snapshots = (b'# head\n' + RAW, RAW + b'# tail\n',
                     RAW.replace(b'prepend: []', b'prepend: [] # inline'),
                     COMMENTED_RAW,
                     b'\xef\xbb\xbf' + COMMENTED_RAW.replace(b'\n', b'\r\n'),
                     COMMENTED_RAW.replace(b'prepend: []', b'prepend: [  ]'))
        for raw in snapshots:
            with self.subTest(raw=raw):
                task = self.prepare(raw=raw)
                material = task.private_material()
                expected = raw.replace(b'prepend: [', b"prepend: ['DOMAIN,example.test,approved-group'")
                self.assertEqual(material['original_bytes'], raw)
                self.assertEqual(material['candidate_bytes'], expected)
                self.assertEqual(material['original_sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(material['candidate_sha256'], hashlib.sha256(expected).hexdigest())
                self.assertEqual(task.private_review()['format_scope'],
                                 'comment_preserving_three_sequence_yaml_exact_bytes_required')
                candidate_result = self.compare(task, expected)
                original_result = self.compare(task, raw)
                self.assertEqual(candidate_result['comparison'], 'exact_match')
                self.assertEqual(candidate_result['recovery_relation'], 'candidate_matches_supplied_snapshot')
                self.assertEqual(original_result['comparison'], 'unchanged')
                self.assertEqual(original_result['recovery_relation'], 'original_matches_supplied_snapshot')
                for result in (candidate_result, original_result):
                    self.assertEqual(result['authority'], 'none')
                    self.assertEqual(result['app_save'], 'not_run')
                    self.assertEqual(result['recovery'], 'not_run')
                    self.assertNotIn('private-comment-SENTINEL', json.dumps(result))
                self.assertNotIn('private-comment-SENTINEL', json.dumps(task.public_report()))

    def test_commented_exact_repeat_is_no_change_without_action_steps(self):
        original = b'\xef\xbb\xbf' + COMMENTED_RAW.replace(b'\n', b'\r\n')
        raw = self.prepare(raw=original).private_material()['candidate_bytes']
        task = self.prepare(raw=raw)
        self.assertEqual(task.private_material()['original_bytes'], raw)
        self.assertEqual(task.private_material()['candidate_bytes'], raw)
        report = task.public_report()
        self.assertEqual(report['status'], 'no_change')
        self.assertEqual(report['operation'], 'none')
        self.assertEqual(report['changed_rules'], 0)
        self.assertEqual(report['matched_rules'], 1)
        self.assertEqual(report['steps'], [])
        self.assertEqual(report['required_host_checks'], [])
        for key in ('backup_ref', 'recovery_ref', 'receipt', 'action_id', 'native_session'):
            self.assertNotIn(key, report)
        result = self.compare(task, raw)
        self.assertEqual(result['comparison'], 'exact_match')
        self.assertEqual(result['recovery_relation'], 'no_change_task')

    def test_exact_repeat_only_is_no_change_without_action_or_backup_steps(self):
        raw = self.prepare().private_material()['candidate_bytes']
        task = self.prepare(raw=raw)
        report = task.public_report()
        self.assertEqual(report['status'], 'no_change')
        self.assertEqual(report['operation'], 'none')
        self.assertEqual(report['changed_rules'], 0)
        self.assertEqual(report['matched_rules'], 1)
        self.assertEqual(report['steps'], [])
        self.assertEqual(report['required_host_checks'], [])
        for key in ('backup_ref', 'recovery_ref', 'receipt', 'action_id', 'native_session'):
            self.assertNotIn(key, report)
        result = self.compare(task, raw=raw)
        self.assertEqual(result['comparison'], 'exact_match')
        self.assertEqual(result['recovery_relation'], 'no_change_task')

    def test_nonempty_other_rules_reordered_or_block_style_not_arbitrary_growth(self):
        for raw in (RAW.replace(b'prepend: []', b"prepend: ['DOMAIN,other.test,approved-group']"),
                    RAW.replace(b'prepend: []', b'prepend:\n  - DOMAIN,example.test,approved-group')):
            args, kw = arguments(raw)
            self.reject('NONEMPTY_PREPEND_UNSUPPORTED', args, kw)

    def test_extra_keys_append_and_delete_not_supported_with_or_without_comments(self):
        for original in (RAW, COMMENTED_RAW):
            for raw in (original + b'other: keep-private\n',
                        original.replace(b'append: []', b"append: ['DOMAIN,other.test,approved-group']")):
                with self.subTest(raw=raw):
                    args, kw = arguments(raw)
                    self.reject('UNSUPPORTED_AGENT_EXTENSION_FORMAT', args, kw)
            args, kw = arguments(original.replace(b'delete: []', b"delete: ['MATCH,DIRECT']"))
            self.reject('DELETE_SEQUENCE_UNSUPPORTED', args, kw)

    def test_comments_do_not_expand_empty_inline_prepend_support(self):
        raw = COMMENTED_RAW.replace(b'prepend: []', b'prepend: [\n  ]')
        args, kw = arguments(raw)
        self.reject('EMPTY_INLINE_PREPEND_REQUIRED', args, kw)

    def test_only_one_exact_domain_not_suffix_or_multiple(self):
        args, kw = arguments()
        args[1]['rules']['rule-a']['kind'] = 'DOMAIN-SUFFIX'
        self.reject('UNSUPPORTED_AGENT_RULE_SCOPE', args, kw)
        args, kw = arguments()
        args[0]['intent']['rule_refs'].append('rule-b')
        args[1]['rule_order'].append('rule-b')
        args[1]['rules']['rule-b'] = {'kind': 'DOMAIN', 'domain': 'other.example'}
        self.reject('UNSUPPORTED_AGENT_RULE_SCOPE', args, kw)

    def test_version_shared_global_and_base_linkage_checks_reused(self):
        cases = [
            ({'app_plist': plistlib.dumps(dict(INFO, CFBundleVersion='2.5.9'))}, 'UNSUPPORTED_PRODUCT_OR_VERSION'),
            ({'selected_uid': 'Rules'}, 'GLOBAL_OR_DEFAULT_EXTENSION_SCOPE_UNSUPPORTED'),
            ({'selected_basename': 'different.yaml'}, 'EXTENSION_FILE_MISMATCH'),
            ({'base_basename': 'different.yaml'}, 'BASE_PROFILE_FILE_MISMATCH'),
            ({'profile_index': INDEX + b'  - uid: other\n    type: local\n    option:\n      rules: rules-private\n'}, 'SHARED_EXTENSION_SCOPE_UNSUPPORTED'),
        ]
        for changes, code in cases:
            with self.subTest(code=code):
                args, kw = arguments()
                kw.update(changes)
                self.reject(code, args, kw)

    def test_semantic_revision_protected_and_group_checks_not_forged(self):
        for raw in (RAW, COMMENTED_RAW):
            with self.subTest(comments=b'#' in raw):
                args, kw = arguments(raw)
                args[0]['facts']['rules']['complete'] = 'unknown'
                self.reject('SEMANTIC_PLAN_BLOCKED', args, kw)
                args, kw = arguments(raw)
                args[0]['revisions']['extension'] = '0' * 64
                args[0]['current_revisions'] = deepcopy(args[0]['revisions'])
                self.reject('SNAPSHOT_REVISION_MISMATCH', args, kw)
                args, kw = arguments(raw)
                args[1]['protected_rule_indexes'] = [1]
                self.reject('PROTECTED_RULE_PRIORITY_CONFLICT', args, kw)
                args, kw = arguments(raw, base=BASE.replace(b'approved-group', b'absent-group'))
                self.reject('EGRESS_GROUP_MISSING_OR_AMBIGUOUS', args, kw)

    def test_entry_required_before_compiler_and_target_must_match(self):
        for value in (None, local_entry('different-target')):
            args, kw = arguments()
            kw['entry_request'] = value
            with patch.object(a.rules, 'compile_rules_extension', side_effect=AssertionError('compiler')):
                self.reject('ENVIRONMENT_ENTRY_REQUIRED', args, kw)

    def test_local_vm_vps_reuse_identical_task_schema(self):
        from test_environment_entry import fixture
        schemas = []
        for route, role in (('local', 'local'), ('vm', 'vm_guest'), ('vps', 'vps')):
            args, kw = arguments()
            projected = fixture(route)
            next(target for target in projected['targets'] if target['role'] == role)['target_ref'] = 'mac-a'
            kw['entry_request'] = projected
            report = a.prepare_rules_task(*args, **kw).public_report()
            schemas.append(set(report))
            self.assertEqual(report['target_ref'], 'mac-a')
        self.assertTrue(all(shape == schemas[0] for shape in schemas))

    def test_changed_entry_remains_inspectable_without_action_steps(self):
        args, kw = arguments()
        task = a.prepare_rules_task(*args, **kw)
        kw['entry_request']['route']['state'] = 'withdrawn'
        self.assertEqual(task.public_report()['status'], 'entry_changed_needs_review')
        self.assertEqual(task.public_report()['steps'], [])
        self.assertEqual(task.public_report()['authority'], 'none')
        self.assertEqual(task.private_review()['review_state'], 'entry_changed')
        self.assertEqual(task.private_material()['original_bytes'], RAW)
        result = self.compare(task, raw=RAW)
        self.assertEqual(result['review_state'], 'entry_changed')
        self.assertEqual(result['comparison'], 'binding_changed')
        kw['entry_request']['route']['state'] = 'selected'
        self.assertEqual(task.public_report()['review_state'], 'entry_changed')

    def test_fresh_but_different_entry_does_not_rebind_task(self):
        task = self.prepare()
        changed = local_entry('mac-a')
        changed['network']['resource_ref'] = 'different-resource'
        result = self.compare(task, entry_request=changed)
        self.assertEqual(result['comparison'], 'binding_changed')
        self.assertEqual(result['review_state'], 'entry_changed')

    def test_cancel_and_expiry_never_produce_task_authority(self):
        args, kw = arguments()
        kw['cancelled'] = lambda: True
        self.reject('CANCELLED', args, kw)
        for invalid in (None, 1, 'secret-private'):
            args, kw = arguments()
            kw['cancelled'] = invalid
            self.reject('INVALID_CANCELLATION_CALLBACK', args, kw)
        with patch.object(a.time, 'monotonic', return_value=100):
            task = self.prepare(ttl_seconds=1)
        with patch.object(a.time, 'monotonic', return_value=101):
            self.assertEqual(task.private_review()['task_freshness'], 'expired')
            self.assertEqual(task.private_material()['original_bytes'], RAW)
            self.assertEqual(task.public_report()['status'], 'expired_needs_review')
            self.assertEqual(task.public_report()['steps'], [])
            result = self.compare(task)
            self.assertEqual(result['comparison'], 'exact_match')
            self.assertEqual(result['task_freshness'], 'expired')
            self.assertEqual(result['application_load'], 'not_run')
        for field in ('max_seconds', 'ttl_seconds'):
            for value in (True, 0, -1, float('nan'), float('inf'), 10**1000, 'secret'):
                args, kw = arguments()
                kw[field] = value
                self.reject('INVALID_DEADLINE' if field == 'max_seconds' else 'INVALID_EXPIRY', args, kw)

    def test_invalid_backwards_and_unrepresentable_clocks_fail_safely(self):
        for value in (None, True, float('nan'), float('inf'), 10**1000, 1e308):
            with patch.object(a.time, 'monotonic', return_value=value):
                self.reject('INVALID_CLOCK')
        with patch.object(a.time, 'monotonic', side_effect=[100, 99]):
            self.reject('INVALID_CLOCK')

    def test_callback_entry_change_is_not_folded_into_cancel_or_content_conflict(self):
        args, kw = arguments()
        count = [0]
        def change_during_compile():
            count[0] += 1
            if count[0] == 2:
                kw['entry_request']['route']['state'] = 'withdrawn'
            return False
        kw['cancelled'] = change_during_compile
        self.reject('ENVIRONMENT_ENTRY_CHANGED', args, kw)
        args, kw = arguments()
        armed = [False]
        count = [0]
        def change_during_compare():
            if armed[0]:
                count[0] += 1
                if count[0] == 2:
                    kw['entry_request']['route']['state'] = 'withdrawn'
            return False
        kw['cancelled'] = change_during_compare
        task = a.prepare_rules_task(*args, **kw)
        raw = task.private_material()['candidate_bytes']
        armed[0] = True
        result = self.compare(task, raw=raw, entry_request=kw['entry_request'])
        self.assertEqual(result['comparison'], 'binding_changed')
        self.assertEqual(result['review_state'], 'entry_changed')

    def test_transient_cancel_during_comparison_is_not_content_conflict(self):
        args, kw = arguments()
        armed = [False]
        count = [0]
        def cancelled():
            if armed[0]:
                count[0] += 1
            return armed[0] and count[0] == 2
        kw['cancelled'] = cancelled
        task = a.prepare_rules_task(*args, **kw)
        raw = task.private_material()['candidate_bytes']
        armed[0] = True
        result = self.compare(task, raw=raw)
        self.assertEqual(result['comparison'], 'not_compared')
        self.assertEqual(result['review_state'], 'cancelled')
        self.assertEqual(task.public_report()['status'], 'cancelled')

    def test_request_or_binding_changed_during_compile_requires_new_task(self):
        for field in ('request', 'binding'):
            args, kw = arguments()
            count = [0]
            def mutate():
                count[0] += 1
                if count[0] == 2:
                    if field == 'request':
                        args[0]['facts']['rules']['complete'] = 'unknown'
                    else:
                        args[1]['group_name'] = 'different-group'
                return False
            kw['cancelled'] = mutate
            self.reject('TASK_INPUT_CHANGED', args, kw)

    def test_cancelled_retained_task_keeps_original_material_and_safe_status(self):
        stopped = [False]
        task = self.prepare(cancelled=lambda: stopped[0])
        stopped[0] = True
        self.assertEqual(task.private_material()['original_bytes'], RAW)
        self.assertEqual(task.private_review()['review_state'], 'cancelled')
        self.assertEqual(task.public_report()['status'], 'cancelled')
        self.assertEqual(task.public_report()['steps'], [])
        self.assertEqual(task.public_report()['authority'], 'none')
        result = self.compare(task, raw=RAW)
        self.assertEqual(result['comparison'], 'not_compared')
        self.assertEqual(result['review_state'], 'cancelled')
        self.assertEqual(result['authority'], 'none')

    def test_invalid_clock_does_not_hide_retained_original(self):
        task = self.prepare()
        with patch.object(a.time, 'monotonic', return_value=float('nan')):
            self.assertEqual(task.private_material()['original_bytes'], RAW)
            self.assertEqual(task.public_report()['steps'], [])
            self.assertEqual(task.public_report()['review_state'], 'invalid_clock')

    def test_source_kinds_are_explicit_and_registry_objects_are_not_file_bytes(self):
        for kinds in (None, {}, {'approved': True},
                      dict.fromkeys(a._ROLES, 'app_text'),
                      dict.fromkeys(a._ROLES, 'native_verified')):
            args, kw = arguments()
            kw['source_kinds'] = kinds
            self.reject('INVALID_SOURCE_KINDS', args, kw)
        args, kw = arguments()
        kw['profile_index'] = {'current': 'profile-private'}
        self.reject('INVALID_OR_OVERSIZED_SNAPSHOT', args, kw)
        for role in ('extension', 'base'):
            args, kw = arguments()
            kw['source_kinds'][role] = 'app_text'
            task = a.prepare_rules_task(*args, **kw)
            self.assertEqual(task.public_report()['source_kinds'][role], 'app_text')
            self.assertEqual(task.public_report()['file_content'], 'not_observed')

    def test_exact_candidate_comparison_cannot_assert_actual_file_save_load_or_effect(self):
        result = self.compare(self.prepare())
        self.assertEqual(result['comparison'], 'exact_match')
        self.assertEqual(result['evidence_level'], 'supplied_snapshot_comparison')
        for field in ('file_content', 'file_metadata'):
            self.assertEqual(result[field], 'not_observed')
        for field in ('app_save', 'application_load', 'effective_rules', 'effective_routing', 'recovery'):
            self.assertEqual(result[field], 'not_run')
        self.assertEqual(result['authority'], 'none')

    def test_app_text_comparison_is_not_observed_file_evidence(self):
        kinds = dict.fromkeys(a._ROLES, 'file_bytes')
        kinds['extension'] = 'app_text'
        result = self.compare(self.prepare(), source_kinds=kinds)
        self.assertEqual(result['comparison'], 'exact_match')
        self.assertEqual(result['content_basis'], 'app_text')
        self.assertEqual(result['file_content'], 'not_observed')
        with self.assertRaisesRegex(a.TaskError, '^INVALID_OR_OVERSIZED_SNAPSHOT$'):
            self.compare(self.prepare(), raw=b'', source_kinds=kinds)

    def test_normalization_reports_semantic_match_without_approval(self):
        raw = b'delete: []\nprepend:\n  - DOMAIN,example.test,approved-group\nappend: []\n'
        result = self.compare(self.prepare(), raw)
        self.assertEqual(result['comparison'], 'semantic_match_bytes_differ')
        self.assertNotIn('approved', json.dumps(result))
        self.assertEqual(result['recovery'], 'not_run')

    def test_commented_semantic_matches_with_any_byte_change_require_new_review(self):
        task = self.prepare(raw=COMMENTED_RAW)
        candidate = task.private_material()['candidate_bytes']
        head, body = candidate.split(b'\n', 1)
        uncommented = RAW.replace(b'prepend: []', b"prepend: ['DOMAIN,example.test,approved-group']")
        variants = {
            'remove_all_comments': uncommented,
            'remove_tail': candidate.replace(b'# keep tail\n', b''),
            'add_comment': candidate + b'# additional-private-SENTINEL\n',
            'change_comment': candidate.replace(b'# keep prepend', b'# edited-private-SENTINEL'),
            'move_comment': body + head + b'\n',
            'reorder_keys': candidate.replace(b'append: [] # keep append\ndelete: [] # keep delete',
                                              b'delete: [] # keep delete\nappend: [] # keep append'),
            'block_style': candidate.replace(b"prepend: ['DOMAIN,example.test,approved-group']",
                                              b'prepend:\n  - DOMAIN,example.test,approved-group'),
            'newline_normalization': candidate.replace(b'\n', b'\r\n'),
            'add_bom': b'\xef\xbb\xbf' + candidate,
            'trailing_whitespace': candidate + b'\n',
        }
        for change, raw in variants.items():
            with self.subTest(change=change):
                self.assertNotEqual(raw, candidate)
                self.assertEqual(a._seqmap(raw), a._seqmap(candidate))
                result = self.compare(task, raw)
                self.assertEqual(result['comparison'], 'unexpected_delta')
                self.assertEqual(result['recovery_relation'], 'conflict_requires_new_review')
                self.assertEqual(result['authority'], 'none')
                self.assertEqual(result['recovery'], 'not_run')
                self.assertNotIn('SENTINEL', json.dumps(result))
                self.assertEqual(task.private_material()['original_bytes'], COMMENTED_RAW)

    def test_comments_added_to_comment_free_candidate_are_not_formatting(self):
        task = self.prepare()
        candidate = task.private_material()['candidate_bytes']
        for raw in (b'# new private-SENTINEL\n' + candidate,
                    candidate.replace(b'append: []', b'append: [] # new private-SENTINEL')):
            result = self.compare(task, raw)
            self.assertEqual(a._seqmap(raw), a._seqmap(candidate))
            self.assertEqual(result['comparison'], 'unexpected_delta')
            self.assertEqual(result['recovery_relation'], 'conflict_requires_new_review')
            self.assertNotIn('SENTINEL', json.dumps(result))

    def test_commented_tasks_keep_cancellation_expiry_and_binding_guards(self):
        stopped = [False]
        task = self.prepare(raw=COMMENTED_RAW, cancelled=lambda: stopped[0])
        stopped[0] = True
        self.assertEqual(task.private_material()['original_bytes'], COMMENTED_RAW)
        self.assertEqual(task.public_report()['steps'], [])
        cancelled = self.compare(task)
        self.assertEqual(cancelled['comparison'], 'not_compared')
        self.assertEqual(cancelled['review_state'], 'cancelled')
        self.assertEqual(cancelled['recovery_relation'], 'conflict_requires_new_review')
        with patch.object(a.time, 'monotonic', return_value=100):
            task = self.prepare(raw=COMMENTED_RAW, ttl_seconds=1)
        with patch.object(a.time, 'monotonic', return_value=101):
            self.assertEqual(task.private_material()['original_bytes'], COMMENTED_RAW)
            self.assertEqual(task.public_report()['steps'], [])
            expired = self.compare(task)
            self.assertEqual(expired['comparison'], 'exact_match')
            self.assertEqual(expired['review_state'], 'expired')
            self.assertEqual(expired['authority'], 'none')
        for changes in ({'selected_uid': 'different'}, {'base': BASE + b'\n'},
                        {'entry_request': local_entry('different-target')}):
            with self.subTest(changes=changes):
                task = self.prepare(raw=COMMENTED_RAW)
                result = self.compare(task, **changes)
                self.assertEqual(result['comparison'], 'binding_changed')
                self.assertEqual(result['recovery_relation'], 'conflict_requires_new_review')
                self.assertEqual(task.private_material()['original_bytes'], COMMENTED_RAW)

    def test_unchanged_original_is_not_inferred_save_failure_or_restoration(self):
        result = self.compare(self.prepare(), RAW)
        self.assertEqual(result['comparison'], 'unchanged')
        self.assertEqual(result['recovery_relation'], 'original_matches_supplied_snapshot')
        self.assertEqual(result['app_save'], 'not_run')
        self.assertEqual(result['recovery'], 'not_run')
        normalized_original = b'delete: []\nappend: []\nprepend: []\n'
        conservative = self.compare(self.prepare(), normalized_original)
        self.assertEqual(conservative['comparison'], 'unexpected_delta')
        self.assertEqual(conservative['recovery_relation'], 'conflict_requires_new_review')

    def test_unexpected_content_or_comments_is_recovery_conflict_not_overwrite(self):
        for raw in (RAW.replace(b'prepend: []', b"prepend: ['DOMAIN,other.test,approved-group']"),
                    RAW + b'unrelated: private-SENTINEL\n',
                    b'# private-SENTINEL\n' + RAW,
                    b'prepend: [invalid\n',
                    RAW.replace(b'append: []', b"append: ['DOMAIN,other.test,approved-group']")):
            with self.subTest(raw=raw):
                result = self.compare(self.prepare(), raw)
                self.assertEqual(result['comparison'], 'unexpected_delta')
                self.assertEqual(result['recovery_relation'], 'conflict_requires_new_review')
                self.assertNotIn('private-SENTINEL', json.dumps(result))

    def test_changed_sources_selection_and_basis_are_not_accepted(self):
        changes = [{'app_plist': plistlib.dumps(dict(INFO, extra='changed'))},
                   {'profile_index': INDEX.replace(b'current: profile-private', b'current: different')},
                   {'base': BASE + b'\n'}, {'selected_uid': 'different'},
                   {'selected_basename': 'different.yaml'}, {'base_basename': 'different.yaml'},
                   {'source_kinds': dict(dict.fromkeys(a._ROLES, 'file_bytes'), base='app_text')}]
        for change in changes:
            with self.subTest(change=list(change)):
                result = self.compare(self.prepare(), **change)
                self.assertEqual(result['comparison'], 'binding_changed')
                self.assertEqual(result['recovery_relation'], 'conflict_requires_new_review')

    def test_no_authorization_flags_or_arbitrary_references(self):
        for refs in ({}, {'approved': True}, dict(arguments()[1]['refs'], task_ref='/private/path'),
                     dict.fromkeys(a._REFS, 'same-alias')):
            args, kw = arguments()
            kw['refs'] = refs
            self.reject('INVALID_TASK_REFERENCES', args, kw)
        args, kw = arguments()
        args[1]['approved'] = True
        self.reject('INVALID_BINDING', args, kw)
        with self.assertRaisesRegex(a.TaskError, '^INVALID_AGENT_TASK$'):
            self.compare({'approved': True}, raw=RAW)

    def test_public_output_and_repr_omit_private_material_and_return_defensive_copies(self):
        task = self.prepare()
        report = task.public_report()
        for secret in ('rules-private', 'profile-private', 'extension-private.yaml',
                       'source-private.yaml', 'example.test', 'approved-group',
                       hashlib.sha256(RAW).hexdigest()):
            self.assertNotIn(secret, json.dumps(report) + repr(task))
        report['steps'].clear()
        report['compiler_blockers'].clear()
        task.private_review()['selection'].clear()
        self.assertTrue(task.public_report()['steps'])
        self.assertTrue(task.public_report()['compiler_blockers'])
        self.assertEqual(task.private_review()['selection']['extension_uid'], 'rules-private')
        with self.assertRaises(TypeError):
            pickle.dumps(task)
        with self.assertRaises(TypeError):
            json.dumps(task)

    def test_pure_prepare_and_compare_do_not_io_or_mutate_supplied_data(self):
        args, kw = arguments()
        original = deepcopy((args, kw))
        with patch('builtins.open', side_effect=AssertionError('file')), \
                patch('socket.socket', side_effect=AssertionError('network')), \
                patch('subprocess.Popen', side_effect=AssertionError('process')):
            task = a.prepare_rules_task(*args, **kw)
            self.compare(task)
            task.public_report()
        self.assertEqual((args, kw), original)

    def test_missing_parser_and_oversized_snapshots_remain_explicit(self):
        args, kw = arguments()
        with patch.object(a.config, 'yaml', None):
            self.reject('PARSER_UNAVAILABLE', args, kw)
        for role in a._ROLES:
            args, kw = arguments()
            kw[role] = b'x' * (a.config.MAX_BYTES + 1)
            self.reject('INVALID_OR_OVERSIZED_SNAPSHOT', args, kw)

    def test_final_inspection_clears_positive_recovery_relation_on_interruption(self):
        for stop in ('cancel', 'entry_change'):
            for content in ('candidate', 'original', 'formatted'):
                with self.subTest(stop=stop, content=content):
                    args, kw = arguments()
                    armed, calls = [False], [0]
                    def interrupted():
                        if not armed[0]:
                            return False
                        calls[0] += 1
                        if calls[0] == 10:
                            if stop == 'cancel':
                                return True
                            kw['entry_request']['route']['state'] = 'withdrawn'
                        return False
                    kw['cancelled'] = interrupted
                    task = a.prepare_rules_task(*args, **kw)
                    raw = task.private_material()['candidate_bytes']
                    if content == 'original':
                        raw = RAW
                    elif content == 'formatted':
                        raw = b'prepend:\n  - DOMAIN,example.test,approved-group\nappend: []\ndelete: []\n'
                    armed[0] = True
                    result = self.compare(task, raw=raw, entry_request=kw['entry_request'])
                    self.assertEqual(calls[0], 10)
                    self.assertEqual(result['comparison'], 'not_compared' if stop == 'cancel' else 'binding_changed')
                    self.assertEqual(result['review_state'], 'cancelled' if stop == 'cancel' else 'entry_changed')
                    self.assertEqual(result['recovery_relation'], 'conflict_requires_new_review')
                    self.assertEqual(result['authority'], 'none')
                    self.assertEqual(result['recovery'], 'not_run')

    def test_parser_disappearance_is_not_a_content_or_recovery_conflict_claim(self):
        task = self.prepare()
        raw = task.private_material()['candidate_bytes']
        with patch.object(a.config, 'yaml', None):
            result = self.compare(task, raw=raw)
        self.assertEqual(result['comparison'], 'not_compared')
        self.assertEqual(result['error_code'], 'PARSER_UNAVAILABLE')
        self.assertEqual(result['recovery_relation'], 'conflict_requires_new_review')
        self.assertEqual(result['authority'], 'none')
        self.assertEqual(result['recovery'], 'not_run')

    def test_validator_deadline_is_not_an_unexpected_content_delta(self):
        task = self.prepare()
        raw = task.private_material()['candidate_bytes']
        with patch.object(a.linkage, 'inspect_linkage',
                          side_effect=a.linkage.OwnershipError('DEADLINE_EXCEEDED')):
            result = self.compare(task, raw=raw)
        self.assertEqual(result['comparison'], 'not_compared')
        self.assertEqual(result['error_code'], 'DEADLINE_EXCEEDED')
        self.assertEqual(result['recovery_relation'], 'conflict_requires_new_review')
        self.assertEqual(result['application_load'], 'not_run')


if __name__ == '__main__':
    unittest.main()
