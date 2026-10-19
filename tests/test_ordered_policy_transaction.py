"""ENV-T40 composition on owned POSIX temporary artifacts, never live configs.

The fixture excludes other writers except deliberate conflict injections. Its
callbacks assert synthetic authorization; they do not authenticate a user or
establish exclusion on another host. Engine/application effects remain untested.
"""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from environment_entry_fixture import local_entry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/claude-guardian/scripts'))
import rule_policy_conversion as policy
import rule_format_conversion as predicates
import repair_cli
import repair_execution
import transactions as tx

M, S = policy.MIHOMO, policy.SING_BOX
REF = 'synthetic-ordered-artifact'
ORIGINAL = b'original standalone synthetic artifact\n'
NEIGHBOR = b'protected synthetic neighbor\x00\xff'
MIHOMO = (b'rules:\n  - DOMAIN-SUFFIX,example.invalid,egress-a\n'
          b'  - DOMAIN,api.example.invalid,egress-b\n'
          b'  - DOMAIN,api.example.invalid,egress-b\n')
JSON_EXPECTED = (b'[{"domain_suffix":["example.invalid"],"action":"route","outbound":"route-a"},'
                 b'{"domain":["api.example.invalid"],"action":"route","outbound":"route-b"},'
                 b'{"domain":["api.example.invalid"],"action":"route","outbound":"route-b"}]\n')
SING = (b'[{"domain":["api.example.invalid","api.example.invalid"],'
        b'"domain_suffix":["example.invalid"],"action":"route","outbound":"route-a"},'
        b'{"domain":["other.invalid"],"action":"route","outbound":"route-b"}]\n')
YAML_EXPECTED = (b"rules:\n  - 'DOMAIN,api.example.invalid,egress-a'\n"
                 b"  - 'DOMAIN,api.example.invalid,egress-a'\n"
                 b"  - 'DOMAIN-SUFFIX,example.invalid,egress-a'\n"
                 b"  - 'DOMAIN,other.invalid,egress-b'\n")
CASES = ((MIHOMO, M, S, JSON_EXPECTED, 3), (SING, S, M, YAML_EXPECTED, 2))
VERIFY = {'check_status': 'pass', 'verification_scope': 'exact_file_bytes_only',
          'application_effect': 'not_tested', 'network_effect': 'not_tested'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_binding(raw):
    return {'schema_version': 'guardian-rule-source-binding/0.1',
            'source_ref': 'synthetic-source', 'expected_sha256': sha(raw),
            'evidence_kind': 'user_supplied', 'verified_at': '2026-10-18',
            'version_scope': 'pinned-fixture', 'purpose': 'offline-composition',
            'client_scope': ['synthetic-client'], 'feature_gate': 'synthetic-feature',
            'shared_service': False, 'activation_state': 'candidate'}


def maps(profile):
    pairs = [('egress-a', 'route-a'), ('egress-b', 'route-b')]
    if profile == S:
        pairs = [(b, a) for a, b in pairs]
    return [{'source_label': a, 'target_label': b,
             'source_kind': 'ordinary_outbound', 'target_kind': 'ordinary_outbound',
             'source_finality': 'terminal_for_tcp_udp',
             'target_finality': 'terminal_for_tcp_udp'} for a, b in pairs]


def selection(raw, profile, host):
    """Independent test oracle on canonical candidates; no production matcher."""
    if profile == M:
        rows = [item.split(',') for item in policy.config.yaml.safe_load(raw)['rules']]
        for kind, domain, label in rows:
            exact = host == domain
            suffix = host.split('.')[-len(domain.split('.')):] == domain.split('.')
            if exact or kind == 'DOMAIN-SUFFIX' and suffix:
                return label
    else:
        for rule in json.loads(raw):
            if (host in rule.get('domain', []) or any(
                    host == domain or host.endswith('.' + domain)
                    for domain in rule.get('domain_suffix', []))):
                return rule['outbound']
    return policy.DEFER


@unittest.skipUnless(os.name == 'posix', 'POSIX temporary-artifact R only; Windows unsupported')
class OrderedPolicyTransactions(unittest.TestCase):
    def setUp(self):
        self.guards = ExitStack()
        self.addCleanup(self.guards.close)
        self.io_guards = [self.guards.enter_context(patch(name, side_effect=AssertionError('unexpected external effect')))
                          for name in ('socket.socket', 'socket.create_connection', 'socket.getaddrinfo',
                                       'socket.gethostbyname', 'subprocess.Popen', 'os.system')]

    def tearDown(self):
        for guard in self.io_guards:
            guard.assert_not_called()

    def fixture(self, raw=MIHOMO):
        temp = tempfile.TemporaryDirectory(prefix='guardian-ordered-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        parent = root / 'owned'
        parent.mkdir()
        target = parent / 'standalone-artifact'
        target.write_bytes(ORIGINAL)
        target.chmod(0o640)
        source = root / 'source'
        source.write_bytes(raw)
        source.chmod(0o600)
        neighbor = root / 'neighbor'
        neighbor.write_bytes(NEIGHBOR)
        neighbor.chmod(0o600)
        backups = root / 'private-backups'
        backups.mkdir(mode=0o700)
        return SimpleNamespace(root=root, parent=parent, target=target, source=source,
                               neighbor=neighbor, backups=backups, raw=raw,
                               owner=(target.stat().st_uid, target.stat().st_gid))

    def protected(self, f, source=None):
        self.assertEqual(f.source.read_bytes(), f.raw if source is None else source)
        self.assertEqual(f.neighbor.read_bytes(), NEIGHBOR)
        self.assertEqual(stat.S_IMODE(f.source.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(f.neighbor.stat().st_mode), 0o600)

    def prepare(self, f, profile=M, *, raw=None, refs=None, binding=None, mappings=None, **kwargs):
        raw = f.raw if raw is None else raw
        if refs is None:
            count = len(policy.config.yaml.safe_load(raw)['rules']) if profile == M else len(json.loads(raw))
            refs = ['rule-' + str(i) for i in range(count)]
        converted = policy.convert_policy_rules(
            raw, profile, S if profile == M else M, refs,
            source_binding(raw) if binding is None else binding,
            maps(profile) if mappings is None else mappings, **kwargs)
        material = converted.private_material()
        self.assertEqual(material['source_bytes'], raw)
        self.assertEqual(material['source_sha256'], sha(raw))
        plan = tx.plan(str(f.target), material['output_bytes'], REF)
        self.assertEqual(plan['after_sha256'], material['output_sha256'])
        return converted, material, plan

    def authorizer(self, operation, document, calls=None, mutate=None):
        expected = (operation, tx.digest(document), REF)
        def approve(*actual):
            if calls is not None:
                calls.append(actual)
            if mutate is not None:
                mutate()
            return actual == expected
        return approve

    def apply(self, f, plan, authorize=None):
        if authorize is None:
            authorize = self.authorizer('apply', {'plan': plan, 'backup_directory': str(f.backups)})
        return tx.apply(plan, target_ref=REF, backup_directory=str(f.backups),
                        authorize=authorize, exclusive_access=True)

    def rollback(self, receipt, authorize=None):
        return tx.rollback(receipt, target_ref=REF, exclusive_access=True,
                           authorize=self.authorizer('rollback', receipt) if authorize is None else authorize)

    def crash_after_replace(self, f, plan):
        write = tx._write
        def fail(fd, name, data, mode=0o600):
            if name == 'applied.json':
                raise OSError('synthetic completion-journal failure')
            return write(fd, name, data, mode)
        with patch.object(tx, '_write', side_effect=fail):
            with self.assertRaisesRegex(tx.TransactionError, '^IO_FAILURE$') as caught:
                self.apply(f, plan)
        batch = f.backups / caught.exception.recovery_id
        path = batch / 'prepared.json'
        receipt = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(receipt['schema_version'], 'exact-file-recovery/2')
        self.assertEqual(receipt['state'], 'prepared')
        self.assertIsNone(receipt['applied_snapshot'])
        self.assertFalse((batch / 'applied.json').exists())
        self.assertEqual((batch / 'original.bin').read_bytes(), ORIGINAL)
        observation = tx.reconcile(receipt, receipt_path=str(path), target_ref=REF,
                                   target_path=str(f.target), backup_batch=str(batch))
        self.assertEqual(observation['classification'], 'prepared_candidate_observed')
        return receipt, observation, batch

    def restore(self, receipt, observation, authorize=None):
        scope = {'recovery_digest': tx.digest(receipt), 'observation': observation}
        return tx.restore_prepared(receipt, observation, target_ref=REF, exclusive_access=True,
                                   authorize=self.authorizer('restore_prepared', scope) if authorize is None else authorize)

    def semantic_readback(self, raw, profile, readback, target_profile):
        mapping = {row['source_label']: row['target_label'] for row in maps(profile)}
        for host in ('example.invalid', 'api.example.invalid', 'deep.api.example.invalid',
                     'other.invalid', 'badexample.invalid', 'bad-example.invalid',
                     'example.invalid.other', 'unmatched.invalid'):
            before = selection(raw, profile, host)
            self.assertEqual(selection(readback, target_profile, host), mapping.get(before, policy.DEFER))

    def restored(self, f, result):
        self.assertEqual(result['state'], 'restored')
        self.assertEqual(result['verification_scope'], 'exact_file_bytes_only')
        self.assertEqual(result['application_effect'], 'not_tested')
        self.assertEqual(result['network_effect'], 'not_tested')
        self.assertEqual(f.target.read_bytes(), ORIGINAL)
        actual = f.target.stat()
        self.assertEqual((stat.S_IMODE(actual.st_mode), actual.st_uid, actual.st_gid), (0o640, *f.owner))
        self.protected(f)

    def test_both_directions_exact_readback_semantics_and_independent_rollback(self):
        for raw, src, dst, expected, count in CASES:
            with self.subTest(profile=src):
                f = self.fixture(raw)
                converted, material, plan = self.prepare(f, src)
                self.assertEqual(material['output_bytes'], expected)
                self.assertEqual(material['output_sha256'], sha(expected))
                self.assertEqual(len(material['ordered_rule_refs']), count)
                self.assertEqual(dict(material['declared_source']), {**source_binding(raw), 'client_scope': ('synthetic-client',)})
                self.assertEqual(f.target.read_bytes(), ORIGINAL)
                calls = []
                scope = {'plan': plan, 'backup_directory': str(f.backups)}
                receipt = self.apply(f, plan, self.authorizer('apply', scope, calls))
                self.assertEqual(calls, [('apply', tx.digest(scope), REF)] * 2)
                self.assertEqual(f.target.read_bytes(), expected)
                self.assertEqual(tx.verify(receipt), VERIFY)
                self.semantic_readback(raw, src, f.target.read_bytes(), dst)
                batch = f.backups / receipt['batch']
                self.assertEqual((batch / 'original.bin').read_bytes(), ORIGINAL)
                self.assertEqual(json.loads((batch / 'applied.json').read_text(encoding='utf-8')), receipt)
                self.assertEqual(stat.S_IMODE(batch.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE((batch / 'original.bin').stat().st_mode), 0o600)
                with self.assertRaisesRegex(tx.TransactionError, '^AUTHORIZATION_DENIED$'):
                    self.rollback(receipt, self.authorizer('apply', scope))
                self.assertEqual(f.target.read_bytes(), expected)
                calls = []
                result = self.rollback(receipt, self.authorizer('rollback', receipt, calls))
                self.assertEqual(calls, [('rollback', tx.digest(receipt), REF)] * 2)
                self.restored(f, result)
                self.assertEqual(len(list(batch.glob('rollback-*.json'))), 1)
                self.assertTrue((batch / 'prepared.json').exists())
                self.assertFalse(list(f.parent.glob('.guardian-stage-*')))

    def rejected_before_plan(self, raw, profile, code, **kwargs):
        f = self.fixture(raw)
        kwargs.setdefault('refs', ['rule-a', 'rule-b'])
        with patch.object(tx, 'plan', wraps=tx.plan) as planner, \
                patch.object(tx, 'apply', wraps=tx.apply) as writer, \
                patch.object(tx, '_authorize', wraps=tx._authorize) as authorizer:
            with self.assertRaises(policy.PolicyConversionError) as caught:
                self.apply(f, self.prepare(f, profile, **kwargs)[2])
            self.assertEqual(str(caught.exception), code)
            planner.assert_not_called()
            writer.assert_not_called()
            authorizer.assert_not_called()
        self.assertNotIn('example.invalid', str(caught.exception))
        self.assertNotIn('egress-a', repr(caught.exception))
        self.assertEqual(f.target.read_bytes(), ORIGINAL)
        self.assertEqual(list(f.backups.iterdir()), [])
        self.protected(f)

    def test_asn_match_and_action_refusals_are_atomic_in_both_positions(self):
        good = 'DOMAIN,good.invalid,egress-a'
        for bad, code in [
                ('IP-ASN,64512,egress-a', 'UNREPRESENTABLE_MATCH'),
                ('IP-CIDR,192.0.2.0/24,egress-a', 'UNREPRESENTABLE_MATCH'),
                ('DOMAIN-KEYWORD,example,egress-a', 'UNREPRESENTABLE_MATCH'),
                ('MATCH,egress-a', 'UNREPRESENTABLE_ACTION'),
                ('DOMAIN,example.invalid,egress-a,no-resolve', 'UNREPRESENTABLE_ACTION'),
                ('DOMAIN,example.invalid,REJECT', 'RESERVED_ACTION_COLLISION')]:
            for entries in ([good, bad], [bad, good]):
                with self.subTest(bad=bad, position=entries.index(bad)):
                    raw = ('rules:\n' + ''.join('  - ' + item + '\n' for item in entries)).encode('ascii')
                    self.rejected_before_plan(raw, M, code)
        good = {'domain': ['good.invalid'], 'action': 'route', 'outbound': 'route-a'}
        for bad, code in [
                ({**good, 'ip_cidr': ['192.0.2.0/24']}, 'UNHANDLED_CONDITION'),
                ({**good, 'domain_keyword': ['example']}, 'UNHANDLED_CONDITION'),
                ({**good, 'port': [443]}, 'UNHANDLED_CONDITION'),
                ({**good, 'network': 'tcp'}, 'UNHANDLED_CONDITION'),
                ({**good, 'invert': False}, 'UNHANDLED_CONDITION'),
                ({**good, 'rule_set': []}, 'UNHANDLED_CONDITION'),
                ({**good, 'type': 'logical'}, 'UNHANDLED_CONDITION'),
                ({**good, 'action': 'reject', 'method': 'drop'}, 'UNREPRESENTABLE_ACTION')]:
            for entries in ([good, bad], [bad, good]):
                with self.subTest(bad=bad, position=entries.index(bad)):
                    self.rejected_before_plan(json.dumps(entries).encode('ascii'), S, code)

    def test_mapping_finality_and_reserved_labels_cannot_be_silently_repaired(self):
        for label in ('DIRECT', 'REJECT', 'REJECT-DROP', 'COMPATIBLE', 'PASS', 'PASS-RULE', 'GLOBAL'):
            for field in ('source_label', 'target_label'):
                bindings = maps(M)
                bindings[0][field] = label
                with self.subTest(label=label, field=field):
                    self.rejected_before_plan(MIHOMO, M, 'RESERVED_ACTION_COLLISION', mappings=bindings)
        for field, value, code in [
                ('source_finality', 'unknown', 'UNKNOWN_OUTBOUND_FINALITY'),
                ('target_finality', 'terminal_for_tcp', 'UNKNOWN_OUTBOUND_FINALITY'),
                ('source_kind', 'reject', 'UNREPRESENTABLE_ACTION')]:
            bindings = maps(M)
            bindings[0][field] = value
            self.rejected_before_plan(MIHOMO, M, code, mappings=bindings)
        duplicate = maps(M)
        duplicate[1]['target_label'] = duplicate[0]['target_label']
        self.rejected_before_plan(MIHOMO, M, 'AMBIGUOUS_OUTBOUND_BINDINGS', mappings=duplicate)
        self.rejected_before_plan(MIHOMO, M, 'INCOMPLETE_OUTBOUND_BINDINGS', mappings=maps(M)[:1],
                                  refs=['rule-a', 'rule-b', 'rule-c'])

    def test_malformed_and_noncanonical_batches_do_not_reach_any_write_stage(self):
        cases = [
            (b'[{"domain":["example.invalid"],"action":"route","\\u0061ction":"route","outbound":"route-a"}]',
             S, 'DUPLICATE_JSON_KEY'),
            (b'[{"domain":["Example.invalid"],"action":"route","outbound":"route-a"}]', S, 'NONCANONICAL_DOMAIN'),
            (b'[{"domain_suffix":[".example.invalid"],"action":"route","outbound":"route-a"}]', S, 'NONCANONICAL_DOMAIN'),
            (b'[{"domain":["example.invalid."],"action":"route","outbound":"route-a"}]', S, 'NONCANONICAL_DOMAIN'),
            (b'[{"domain":["*.example.invalid"],"action":"route","outbound":"route-a"}]', S, 'NONCANONICAL_DOMAIN'),
            (b'[{', S, 'INVALID_ROUTE_JSON'), (b'\xff', M, 'INVALID_SOURCE_ENCODING'),
            (b'rules:\n  - &private DOMAIN,example.invalid,egress-a\n', M, 'UNSUPPORTED_YAML')]
        for raw, profile, code in cases:
            with self.subTest(code=code, raw=raw):
                self.rejected_before_plan(raw, profile, code, refs=['rule-a'])

    def test_actions_never_cross_into_actionless_output_or_write(self):
        inputs = [(MIHOMO, predicates.MIHOMO_CLASSICAL),
                  (b'{"version":1,"rules":[{"domain":["example.invalid"],"action":"route","outbound":"route-a"}]}',
                   predicates.SING_BOX)]
        for raw, profile in inputs:
            with self.subTest(profile=profile):
                f = self.fixture(raw)
                with patch.object(tx, 'plan', wraps=tx.plan) as planner, \
                        patch.object(tx, 'apply', wraps=tx.apply) as writer:
                    with self.assertRaisesRegex(predicates.ConversionError, '^UNREPRESENTABLE_ACTION$'):
                        converted = predicates.convert_rule_format(raw, profile, predicates.EXACT,
                                                                  ['rule-a'], source_binding(raw))
                        self.apply(f, tx.plan(str(f.target), converted.private_material()['output_bytes'], REF))
                    planner.assert_not_called()
                    writer.assert_not_called()
                self.assertEqual(f.target.read_bytes(), ORIGINAL)
                self.assertEqual(list(f.backups.iterdir()), [])
                self.protected(f)

    def test_source_digest_references_cancel_and_deadline_refuse_before_planning(self):
        changed = MIHOMO.replace(b'api.example.invalid', b'new.example.invalid')
        self.rejected_before_plan(changed, M, 'SOURCE_DIGEST_MISMATCH', binding=source_binding(MIHOMO))
        self.rejected_before_plan(MIHOMO, M, 'DUPLICATE_RULE_REFERENCE', refs=['same', 'same'])
        self.rejected_before_plan(MIHOMO, M, 'CANCELLED', cancelled=lambda: True)
        self.rejected_before_plan(MIHOMO, M, 'CANCELLED', cancelled=lambda: None)
        with patch.object(policy.time, 'monotonic', side_effect=[0, 6]):
            self.rejected_before_plan(MIHOMO, M, 'DEADLINE_EXCEEDED')

    def test_changed_target_bytes_mode_inode_or_parent_cannot_reuse_plan(self):
        for kind in ('bytes', 'mode', 'inode', 'parent'):
            with self.subTest(change=kind):
                f = self.fixture()
                _, _, plan = self.prepare(f)
                expected = ORIGINAL
                if kind == 'bytes':
                    expected = b'later user edit\n'
                    f.target.write_bytes(expected)
                elif kind == 'mode':
                    f.target.chmod(0o600)
                elif kind == 'inode':
                    other = f.parent / 'replacement'
                    other.write_bytes(ORIGINAL)
                    other.chmod(0o640)
                    other.replace(f.target)
                else:
                    f.parent.rename(f.root / 'old-owned')
                    f.parent.mkdir()
                    f.target.write_bytes(ORIGINAL)
                    f.target.chmod(0o640)
                with self.assertRaisesRegex(tx.TransactionError, '^' + ('PARENT_CHANGED' if kind == 'parent' else 'STALE_FILE') + '$'):
                    self.apply(f, plan)
                self.assertEqual(f.target.read_bytes(), expected)
                self.assertEqual(list(f.backups.iterdir()), [])
                self.protected(f)

    def test_apply_scope_expiry_and_missing_authority_preserve_original(self):
        f = self.fixture()
        _, _, plan = self.prepare(f)
        scope = {'plan': plan, 'backup_directory': str(f.backups)}
        for authorizer, code in [(None, 'AUTHORIZATION_REQUIRED'), (lambda *args: 1, 'AUTHORIZATION_DENIED'),
                                 (lambda *args: False, 'AUTHORIZATION_DENIED')]:
            with self.subTest(code=code), self.assertRaisesRegex(tx.TransactionError, '^' + code + '$'):
                tx.apply(plan, target_ref=REF, backup_directory=str(f.backups),
                         authorize=authorizer, exclusive_access=True)
        with self.assertRaisesRegex(tx.TransactionError, '^TARGET_MISMATCH$'):
            tx.apply(plan, target_ref='other-target', backup_directory=str(f.backups),
                     authorize=self.authorizer('apply', scope), exclusive_access=True)
        other = f.root / 'other-backups'
        other.mkdir(mode=0o700)
        with self.assertRaisesRegex(tx.TransactionError, '^AUTHORIZATION_DENIED$'):
            tx.apply(plan, target_ref=REF, backup_directory=str(other),
                     authorize=self.authorizer('apply', scope), exclusive_access=True)
        with patch.object(tx.time, 'time', return_value=plan['expires_at']):
            with self.assertRaisesRegex(tx.TransactionError, '^INVALID_OR_EXPIRED_PLAN$'):
                self.apply(f, plan)
        self.assertEqual(f.target.read_bytes(), ORIGINAL)
        self.assertEqual(list(f.backups.iterdir()), [])
        self.assertEqual(list(other.iterdir()), [])
        self.protected(f)

    def test_cancel_at_second_apply_approval_retains_prepared_but_never_writes(self):
        f = self.fixture()
        _, _, plan = self.prepare(f)
        calls = []
        bound = self.authorizer('apply', {'plan': plan, 'backup_directory': str(f.backups)}, calls)
        with self.assertRaisesRegex(tx.TransactionError, '^AUTHORIZATION_DENIED$') as caught:
            self.apply(f, plan, lambda *args: bound(*args) and len(calls) == 1)
        self.assertEqual(len(calls), 2)
        batch = f.backups / caught.exception.recovery_id
        self.assertEqual(f.target.read_bytes(), ORIGINAL)
        self.assertEqual((batch / 'original.bin').read_bytes(), ORIGINAL)
        self.assertTrue((batch / 'prepared.json').exists())
        self.assertFalse((batch / 'applied.json').exists())
        self.assertFalse(list(f.parent.glob('.guardian-stage-*')))
        self.protected(f)

    def test_later_edit_after_applied_receipt_blocks_rollback(self):
        f = self.fixture()
        _, _, plan = self.prepare(f)
        receipt = self.apply(f, plan)
        f.target.write_bytes(b'later independent edit\n')
        self.assertEqual(tx.verify(receipt), {**VERIFY, 'check_status': 'fail'})
        with self.assertRaisesRegex(tx.TransactionError, '^ROLLBACK_CONFLICT$'):
            self.rollback(receipt)
        self.assertEqual(f.target.read_bytes(), b'later independent edit\n')
        self.assertEqual((f.backups / receipt['batch'] / 'original.bin').read_bytes(), ORIGINAL)
        self.protected(f)

    def test_changed_prepared_target_or_identity_rejects_stale_observation(self):
        for same_bytes in (False, True):
            with self.subTest(same_bytes=same_bytes):
                f = self.fixture()
                _, _, plan = self.prepare(f)
                receipt, observation, batch = self.crash_after_replace(f, plan)
                expected = JSON_EXPECTED if same_bytes else b'later edit after observation\n'
                replacement = f.parent / 'new-target'
                replacement.write_bytes(expected)
                replacement.chmod(0o640)
                replacement.replace(f.target)
                calls = []
                scope = {'recovery_digest': tx.digest(receipt), 'observation': observation}
                with self.assertRaisesRegex(tx.TransactionError, '^RECONCILIATION_STALE$'):
                    self.restore(receipt, observation, self.authorizer('restore_prepared', scope, calls))
                self.assertEqual(calls, [])
                self.assertEqual(f.target.read_bytes(), expected)
                self.assertEqual((batch / 'original.bin').read_bytes(), ORIGINAL)
                self.protected(f)

    def test_prepared_target_receipt_and_backup_changes_during_last_approval_block(self):
        for changed in ('target', 'receipt', 'backup', 'batch'):
            with self.subTest(changed=changed):
                f = self.fixture()
                _, _, plan = self.prepare(f)
                receipt, observation, batch = self.crash_after_replace(f, plan)
                calls = []
                scope = {'recovery_digest': tx.digest(receipt), 'observation': observation}
                def mutate():
                    if len(calls) != 2:
                        return
                    if changed == 'target':
                        f.target.write_bytes(b'later edit during restoration approval\n')
                    elif changed == 'receipt':
                        path = batch / 'prepared.json'
                        raw = path.read_bytes()
                        path.write_bytes(raw + b'\n')
                    elif changed == 'backup':
                        (batch / 'original.bin').write_bytes(b'corrupted synthetic original\n')
                    else:
                        batch.chmod(0o750)
                with self.assertRaises(tx.TransactionError) as caught:
                    self.restore(receipt, observation, self.authorizer('restore_prepared', scope, calls, mutate))
                self.assertEqual(str(caught.exception), {'target': 'RECONCILIATION_STALE',
                    'receipt': 'RECONCILIATION_STALE', 'backup': 'BACKUP_CORRUPT',
                    'batch': 'BACKUP_DIRECTORY_NOT_PRIVATE'}[changed])
                self.assertEqual(len(calls), 2)
                self.assertEqual(f.target.read_bytes(), b'later edit during restoration approval\n'
                                 if changed == 'target' else JSON_EXPECTED)
                self.assertFalse(list(batch.glob('rollback-*.json')))
                self.protected(f)

    def test_cancel_at_each_prepared_restore_approval_does_not_restore(self):
        for denied_at in (1, 2):
            with self.subTest(denied_at=denied_at):
                f = self.fixture()
                _, _, plan = self.prepare(f)
                receipt, observation, batch = self.crash_after_replace(f, plan)
                calls = []
                scope = {'recovery_digest': tx.digest(receipt), 'observation': observation}
                bound = self.authorizer('restore_prepared', scope, calls)
                with self.assertRaisesRegex(tx.TransactionError, '^AUTHORIZATION_DENIED$'):
                    self.restore(receipt, observation, lambda *args: bound(*args) and len(calls) != denied_at)
                self.assertEqual(len(calls), denied_at)
                self.assertEqual(f.target.read_bytes(), JSON_EXPECTED)
                self.assertEqual((batch / 'original.bin').read_bytes(), ORIGINAL)
                self.assertFalse(list(batch.glob('restore-*')))
                self.protected(f)

    def test_restoration_journal_failure_retains_truthful_readonly_witness(self):
        f = self.fixture()
        _, _, plan = self.prepare(f)
        receipt, observation, batch = self.crash_after_replace(f, plan)
        write = tx._write
        def fail(fd, name, data, mode=0o600):
            if name.startswith('rollback-'):
                raise OSError('synthetic restoration journal failure')
            return write(fd, name, data, mode)
        with patch.object(tx, '_write', side_effect=fail):
            with self.assertRaisesRegex(tx.TransactionError, '^IO_FAILURE$') as caught:
                self.restore(receipt, observation)
        self.assertEqual(f.target.read_bytes(), ORIGINAL)
        witness_path = batch / ('restore-' + caught.exception.attempt_id + '.prepared.json')
        witness = json.loads(witness_path.read_text(encoding='utf-8'))
        observed = tx.reconcile(witness, receipt_path=str(witness_path), target_ref=REF,
                                target_path=str(f.target), backup_batch=str(batch))
        self.assertEqual(observed['classification'], 'restored_candidate_observed')
        self.assertEqual(observed['application_effect'], 'not_tested')
        self.assertFalse(list(batch.glob('rollback-*.json')))
        with self.assertRaisesRegex(tx.TransactionError, '^RECONCILIATION_STALE$'):
            self.restore(receipt, observation)
        self.assertEqual(f.target.read_bytes(), ORIGINAL)
        self.protected(f)

    def test_complete_public_preview_and_production_admission_are_truthful(self):
        f = self.fixture()
        converted, _, plan = self.prepare(f)
        self.assertEqual(converted.preview(), {
            'schema_version': 'guardian-policy-conversion-preview/0.1',
            'status': 'converted_ordered_labels_under_declared_preconditions',
            'source_rule_count': 3, 'predicate_count': 3, 'outbound_count': 2,
            'equivalence_scope': 'canonical_lowercase_ascii_tcp_udp_label_selection',
            'outbound_finality_evidence': 'declared_unverified',
            'no_match_contract': policy.DEFER, 'enclosing_fallback': 'not_established',
            'runtime_behavior': 'not_established', 'effective_priority': 'not_established',
            'actual_egress': 'not_established', 'source_authenticity': 'not_established',
            'source_freshness': 'not_established', 'independent_sources': 'not_established',
            'native_acceptance': 'not_run', 'apply_supported': False,
            'authorization': 'not_required_for_offline_conversion'})
        self.assertEqual(tx.preview(plan), {'plan_digest': tx.digest(plan),
            'before_sha256': sha(ORIGINAL), 'after_sha256': sha(JSON_EXPECTED),
            'before_size': len(ORIGINAL), 'after_size': len(JSON_EXPECTED),
            'changed': True, 'verification_scope': 'exact_file_bytes_only'})
        with patch.object(repair_cli, '_load_request', side_effect=AssertionError('unexpected read')) as read:
            with self.assertRaisesRegex(repair_cli.RepairError, '^UNSUPPORTED_CANDIDATE_KIND$'):
                repair_cli.preflight('not-read', 'not-read', REF, candidate_kind='policy-conversion',
                                     entry_request=local_entry(REF))
            read.assert_not_called()
        with self.assertRaisesRegex(tx.TransactionError, '^NATIVE_REPAIR_ADAPTER_UNAVAILABLE$'):
            with repair_execution._native_session({}):
                self.fail('native session unexpectedly admitted')
        self.assertEqual(f.target.read_bytes(), ORIGINAL)
        self.assertEqual(list(f.backups.iterdir()), [])

    def test_ordered_occurrence_provenance_is_not_lost_at_write_boundary(self):
        for raw, src, dst, expected, count in CASES:
            with self.subTest(profile=src):
                f = self.fixture(raw)
                _, m, p = self.prepare(f, src)
                expected_map = ((0, 0, 0), (1, 1, 0), (2, 2, 0)) if src == M else ((0, 0, 0), (1, 0, 1), (2, 0, 2), (3, 1, 0))
                self.assertEqual(m['output_occurrence_map'], expected_map)
                self.assertEqual([r.source_rule_ref for r in m['records']],
                                 ['rule-' + str(i) for _, i, _ in expected_map])
                self.assertEqual([r.source_path for r in m['records']],
                    [('rules', 0), ('rules', 1), ('rules', 2)] if src == M else
                    [(0, 'domain', 0), (0, 'domain', 1), (0, 'domain_suffix', 0), (1, 'domain', 0)])
                self.assertEqual([r.source_line for r in m['records']], [2, 3, 4] if src == M else [None] * 4)
                receipt = self.apply(f, p)
                self.assertEqual(f.target.read_bytes(), expected)
                self.assertEqual(m['source_bytes'], f.source.read_bytes())
                self.restored(f, self.rollback(receipt))

    def test_actual_output_priority_reversal_changes_only_expected_label_choice(self):
        cases = [(MIHOMO, 'route-a'),
                 (b'rules:\n  - DOMAIN,api.example.invalid,egress-b\n'
                  b'  - DOMAIN-SUFFIX,example.invalid,egress-a\n', 'route-b')]
        for raw, expected in cases:
            with self.subTest(first=expected):
                f = self.fixture(raw)
                _, _, plan = self.prepare(f)
                receipt = self.apply(f, plan)
                self.assertEqual(selection(f.target.read_bytes(), S, 'api.example.invalid'), expected)
                self.assertEqual(selection(f.target.read_bytes(), S, 'example.invalid'), 'route-a')
                self.assertEqual(selection(f.target.read_bytes(), S, 'notexample.invalid'), policy.DEFER)
                self.restored(f, self.rollback(receipt))

    def test_both_directions_prepared_v2_reconciliation_and_separate_restoration(self):
        for raw, src, dst, expected, _ in CASES:
            with self.subTest(profile=src):
                f = self.fixture(raw)
                _, _, plan = self.prepare(f, src)
                receipt, observation, batch = self.crash_after_replace(f, plan)
                self.assertEqual(f.target.read_bytes(), expected)
                self.semantic_readback(raw, src, f.target.read_bytes(), dst)
                self.assertEqual(observation['replace_sha256'], sha(expected))
                self.assertEqual(observation['restore_sha256'], sha(ORIGINAL))
                self.assertEqual(observation['application_effect'], 'not_tested')
                self.assertEqual(observation['network_effect'], 'not_tested')
                with self.assertRaisesRegex(tx.TransactionError, '^RECOVERY_REQUIRES_RECONCILIATION$'):
                    self.rollback(receipt)
                with self.assertRaisesRegex(tx.TransactionError, '^AUTHORIZATION_DENIED$'):
                    self.restore(receipt, observation, self.authorizer('apply', {'plan': plan, 'backup_directory': str(f.backups)}))
                calls = []
                scope = {'recovery_digest': tx.digest(receipt), 'observation': observation}
                result = self.restore(receipt, observation, self.authorizer('restore_prepared', scope, calls))
                self.assertEqual(calls, [('restore_prepared', tx.digest(scope), REF)] * 2)
                self.restored(f, result)
                self.assertTrue((batch / 'prepared.json').exists())
                self.assertFalse((batch / 'applied.json').exists())
                self.assertEqual((batch / 'original.bin').read_bytes(), ORIGINAL)


if __name__ == '__main__':
    unittest.main()
