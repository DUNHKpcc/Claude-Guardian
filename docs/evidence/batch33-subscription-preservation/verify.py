"""Exact, offline historical/current bridge checks; never a source allowlist.

The installed consumer pins manifest.json before importing this pinned module.
The old packet is a generation record and must remain byte-identical.
"""
import hashlib
import importlib.machinery
import importlib.util
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

BRIDGE_REL = 'docs/evidence/batch33-subscription-preservation'
PACKET_REL = 'docs/evidence/subscription-boundaries'
CASES = {'T36', 'T38', 'T46', 'T54'}
ROOT = None  # Supplied by the installed, hash-pinning consumer.
PINNED_MANIFEST_SHA256 = None
PINNED_LOADER = None


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(path):
    require(path.is_file() and not path.is_symlink(), 'Missing/unsafe file: ' + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def file_hashes(directory, excluded=()):
    require(directory.is_dir() and not directory.is_symlink(), 'Missing/unsafe evidence directory')
    result = {}
    for path in directory.rglob('*'):
        if '__pycache__' in path.relative_to(directory).parts:
            continue
        require(not path.is_symlink(), 'Symlink is not retained evidence: ' + str(path))
        if path.is_file() and path.relative_to(directory).as_posix() not in excluded:
            result[path.relative_to(directory).as_posix()] = digest(path)
    return result


def verify_bridge(root, expected_manifest_sha256):
    """Validate the one reviewed final tuple and all immutable prerequisites."""
    root = Path(root)
    evidence, packet = root / BRIDGE_REL, root / PACKET_REL
    manifest_path = evidence / 'manifest.json'
    require(digest(manifest_path) == expected_manifest_sha256, 'Unreviewed bridge manifest')
    manifest = read_json(manifest_path)
    require(manifest['schema'] == 'guardian-batch33-subscription-current-compatibility-public-projection/1', 'Bridge schema')
    require(manifest['status'] == 'exact_source_preservation_projection', 'Unreviewed bridge projection')
    require(manifest['evidence_form'] == 'sanitized_public_projection', 'Projection boundary missing')
    require(manifest['historical_packet_file_count'] == len(manifest['historical_packet_files']) == 173,
            'Original 173-file packet scope')
    require(manifest['historical_manifests_unchanged'] is True and manifest['model_generation_performed'] is False,
            'Historical generation boundary')
    require(manifest['bridge_only'] is True and set(manifest['cases']) == CASES, 'Original four-case scope')
    require(file_hashes(evidence, ('manifest.json',)) == manifest['files'], 'Bridge payload drift')
    require(file_hashes(packet) == manifest['historical_packet_files'], 'Historical packet drift')
    for name, key in [('integration-manifest.json', 'historical_integration_manifest_sha256'),
                      ('original-stage-manifest.json', 'historical_original_stage_manifest_sha256'),
                      ('current-guidance-source-pins.json', 'historical_current_pin_record_sha256')]:
        require(digest(packet / name) == manifest[key], 'Historical manifest changed: ' + name)
    old_pins = read_json(packet / 'current-guidance-source-pins.json')['pins']
    historical = {p['relative_path']: p['current_sha256'] for p in old_pins}
    require(len(old_pins) == len(historical) == 9 and historical == manifest['historical_source_tuple'],
            'Historical source tuple changed')
    for pin in old_pins:
        consumed = pin.get('consumed_sha256', pin.get('original_control_or_spec_sha256'))
        require(pin['equal'] is True and consumed == pin['current_sha256'], 'Historical equality falsified')
    current = manifest['approved_live_source_tuple']
    require(set(current) == set(historical), 'Incomplete or expanded live tuple')
    changed = {p for p in current if current[p] != historical[p]}
    require(changed == {'skills/claude-guardian/references/intake.md',
                        'skills/claude-guardian/scripts/interview_flow.py'}, 'Unreviewed source scope')
    for path, expected in {**current, **manifest['supporting_live_source_tuple']}.items():
        require(digest(root / path) == expected, 'Live source drift: ' + path)
    require(digest(evidence / 'prebridge-source-freeze.json') == manifest['review_freeze_sha256'], 'Review freeze')
    freeze = read_json(evidence / 'prebridge-source-freeze.json')
    for path, expected in {**current, **manifest['supporting_live_source_tuple']}.items():
        require(freeze['files'][path] == expected, 'Source not in reviewed freeze')
    require(freeze['evidence_form'] == 'sanitized_public_projection'
            and freeze['files'] == {**current, **manifest['supporting_live_source_tuple']},
            'Source projection is not the exact minimal tuple')
    approval = read_json(evidence / 'approved-preservation-review.json')
    require(digest(evidence / 'approved-preservation-review.json') == manifest['approval_record_sha256'], 'Sanitized review identity')
    require(approval['status'] == 'HISTORICAL_REVIEW_PROJECTION'
            and approval['historical_status'] == 'APPROVED_EXACT_SOURCE_PRESERVATION_ONLY'
            and approval['evidence_form'] == 'sanitized_public_projection', 'Unreviewed preservation projection')
    require(approval['accepted_live_hashes'] == current and approval['source_freeze_sha256'] == manifest['review_freeze_sha256'],
            'Review does not bind current tuple')
    require(digest(evidence / approval['semantic_review']['path']) == approval['semantic_review']['sha256'],
            'Semantic review projection drift')
    require(approval['whole_original_clauses_reviewed'] is True
            and approval['all_retained_selected_response_text_and_context_reviewed'] is True,
            'Whole-clause/context historical review absent')
    require(approval['covered_cases'] == {case: 'L+C' for case in CASES}, 'Review layer drift')
    require(approval['historical_exact_source_tuple'] == historical, 'Review historical identity')
    require(approval['runtime_clearance']['status'] == 'CLEAR', 'Runtime clearance absent')
    require(digest(evidence / 'verified-runtime-clearance.json') == approval['runtime_clearance']['sha256'], 'Runtime review identity')
    clearance = read_json(evidence / 'verified-runtime-clearance.json')
    require(clearance['status'] == 'CLEAR' and clearance['before_after_equal'] is True, 'Runtime review not clear')
    for path, expected in clearance['source_hashes'].items():
        require(digest(root / path) == expected, 'Runtime review source drift')
    for receipt in clearance['receipts']:
        require(digest(evidence / receipt['path']) == receipt['sha256'], 'Runtime receipt drift')
    require(digest(evidence / 'reviewed-guidance-intake.md') == current['skills/claude-guardian/references/intake.md'],
            'Semantic review used a different guide')
    verdicts = read_json(packet / 'current-verdicts.json')['case_verdicts']
    ledger = read_json(root / 'docs/acceptance-rebuild-ledger.json')['cases']
    for case, reviewed in manifest['cases'].items():
        old = verdicts[case]
        require(reviewed['new_case_acceptance'] is False, 'New acceptance is outside bridge')
        require(reviewed['selected_response_files'] == old['response_files'], 'Selected response scope drift')
        require(reviewed['generation_intake_sha256'] == old['generation_intake_sha256'], 'Generation source rewritten')
        expected_row = {key: old['original']['ledger_row_verbatim_object'][key]
                        for key in ('id', 'scenario', 'requirement', 'verification_layer')}
        require(reviewed['original'] == expected_row, 'Original clause or layer changed')
        actual_rows = [row for row in ledger if row['id'] == case]
        require(len(actual_rows) == 1 and all(actual_rows[0][key] == value for key, value in expected_row.items()),
                'Live original clause or layer changed: ' + case)
        for path, expected in reviewed['selected_response_files'].items():
            require(digest(packet / path) == expected, 'Historical response changed')
    replay = read_json(evidence / 'live-helper-replay.json')
    require(digest(evidence / 'live-helper-replay.json') == manifest['live_helper_replay_sha256']
            == approval['live_helper_receipt']['sha256'], 'Current helper receipt identity')
    old_control = read_json(packet / 'reviewer-controls/actual-control-report.json')
    expected_replay_sources = {
        PACKET_REL + '/' + path: manifest['historical_packet_files'][path]
        for path in (
            'reviewer-controls/replay.py',
            'retained/candidate/generator-inputs/runtime/interview_flow.py',
            'retained/candidate/generator-inputs/helper-inputs/prior-pure-api-inputs.json',
            'retained/candidate/review-only/prior-observations/outputs.json',
            'reviewer-controls/actual-control-report.json',
            'integration-manifest.json',
        )
    }
    expected_replay_sources.update({path: current[path] for path in (
        'skills/claude-guardian/scripts/interview_flow.py',
        'skills/claude-guardian/scripts/traffic_policy.py',
    )})
    verify_replay(replay, old_control, expected_replay_sources)
    return manifest


def verify_replay(replay, old_control, expected_sources):
    """Check complete observed arguments/states/returns, not success labels alone."""
    require(replay['evidence_form'] == 'sanitized_public_projection'
            and 'source_root' not in replay and 'packet_root' not in replay,
            'Replay must omit machine identity')
    require(replay['source_sha256'] == expected_sources, 'Replay source tuple drift')
    require(replay['kind'] == 'current_frozen_helper_preservation_replay'
            and replay['complete_calls_equal_historical_controls'] is True
            and replay['historical_runner_is_unchanged'] is True
            and replay['live_helper_loader_override_only'] is True
            and replay['model_prose_generated'] is False and replay['respondent_helper_calls'] is False,
            'Current replay provenance boundary')
    result = replay['result']
    require(result['call_count'] == len(result['calls']) == 15 and result['blocked_io_attempts'] == []
            and result['model_prose_generated'] is False, 'Current helper call/no-I/O boundary')
    require(set(result) == set(old_control), 'Incomplete replay fields')
    # Interpreter/platform are execution context only; all behavioral data and
    # guard definitions must exactly equal the unchanged original control.
    for key in set(old_control) - {'python_version', 'execution_platform'}:
        require(result[key] == old_control[key], 'Incomplete current helper preservation: ' + key)


def execute_live_replay(root):
    """Execute only the manifest-pinned portable adapter after bridge validation."""
    root = Path(root)
    verify_bridge(root, PINNED_MANIFEST_SHA256)
    path = root / BRIDGE_REL / 'live-helper-replay-runner.py.txt'
    loader = importlib.machinery.SourceFileLoader('subscription_preservation_public_replay', str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module.run_replay(root, root / PACKET_REL)


class SubscriptionPreservationBridgeControls(unittest.TestCase):
    """Negative controls change only newly created disposable copies."""
    @staticmethod
    def copy_disposable_tree(source, target):
        # Preserve evidence bytes, not source read-only attributes, in this
        # newly created throwaway fixture used for negative mutation controls.
        shutil.copytree(source, target, copy_function=shutil.copyfile,
                        ignore=shutil.ignore_patterns('__pycache__'))

    def test_disposable_copy_of_readonly_source_is_mutable(self):
        with tempfile.TemporaryDirectory(prefix='guardian-readonly-fixture-') as tmp:
            source = Path(tmp) / 'source'
            source.mkdir()
            original = source / 'evidence.json'
            original.write_bytes(b'original')
            original.chmod(0o444)
            target = Path(tmp) / 'copy'
            try:
                self.copy_disposable_tree(source, target)
                self.assertEqual((target / original.name).read_bytes(), b'original')
                (target / original.name).write_bytes(b'modified')
                self.assertEqual(original.read_bytes(), b'original')
            finally:
                original.chmod(0o600)

    def copy_inputs(self, root):
        manifest = read_json(ROOT / BRIDGE_REL / 'manifest.json')
        for rel in (BRIDGE_REL, PACKET_REL):
            self.copy_disposable_tree(ROOT / rel, root / rel)
        paths = set(manifest['approved_live_source_tuple']) | set(manifest['supporting_live_source_tuple'])
        paths.add('docs/acceptance-rebuild-ledger.json')
        for rel in paths:
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, target)

    def rejects(self, mutations):
        for name, mutate in mutations:
            with self.subTest(mutation=name), tempfile.TemporaryDirectory(prefix='guardian-subscription-bridge-') as tmp:
                root = Path(tmp)
                self.copy_inputs(root)
                mutate(root)
                with self.assertRaises(AssertionError):
                    verify_bridge(root, PINNED_MANIFEST_SHA256)

    def test_exact_approved_complete_bridge(self):
        verify_bridge(ROOT, PINNED_MANIFEST_SHA256)

    def test_live_runtime_replays_all_fifteen_guarded_calls_deterministically(self):
        retained = read_json(ROOT / BRIDGE_REL / 'live-helper-replay.json')
        original = read_json(ROOT / PACKET_REL / 'reviewer-controls/actual-control-report.json')
        first, second = execute_live_replay(ROOT), execute_live_replay(ROOT)
        verify_replay(first, original, retained['source_sha256'])
        verify_replay(second, original, retained['source_sha256'])
        self.assertEqual(first, second)
        self.assertEqual(first['result']['calls'], retained['result']['calls'])
        self.assertEqual(first['result']['outputs'], retained['result']['outputs'])

    def test_replay_semantic_tampering_rejected_independently_of_digest(self):
        retained = read_json(ROOT / BRIDGE_REL / 'live-helper-replay.json')
        original = read_json(ROOT / PACKET_REL / 'reviewer-controls/actual-control-report.json')
        mutations = [
            ('missing-call', lambda value: value['result']['calls'].pop()),
            ('changed-return', lambda value: value['result']['calls'][0].update({'return': {}})),
            ('changed-input', lambda value: value['result']['calls'][0].update({'arguments': {}})),
            ('changed-output', lambda value: value['result'].update({'outputs': {}})),
            ('io-attempt', lambda value: value['result']['blocked_io_attempts'].append('socket.socket')),
            ('missing-sentinel', lambda value: value['result']['guard_targets'].pop()),
            ('respondent-call', lambda value: value.update({'respondent_helper_calls': True})),
            ('machine-root', lambda value: value.update({'source_root': 'disallowed-machine-location'})),
            ('unbound-runtime', lambda value: value['source_sha256'].update({
                'skills/claude-guardian/scripts/interview_flow.py': '0' * 64})),
        ]
        for name, mutate in mutations:
            with self.subTest(mutation=name):
                value = deepcopy(retained)
                mutate(value)
                with self.assertRaises(AssertionError):
                    verify_replay(value, original, retained['source_sha256'])

    def test_missing_unapproved_or_extra_bridge_fails_closed(self):
        def unapprove(root):
            path = root / BRIDGE_REL / 'manifest.json'
            value = read_json(path)
            value['status'] = 'pending'
            path.write_text(json.dumps(value), encoding='utf-8')
        self.rejects([
            ('missing-manifest', lambda root: (root / BRIDGE_REL / 'manifest.json').unlink()),
            ('unapproved-manifest', unapprove),
            ('extra-unreviewed-payload', lambda root: (root / BRIDGE_REL / 'extra.txt').write_text('unreviewed', encoding='utf-8')),
        ])

    def test_all_live_source_drift_and_mixed_tuple_fail_closed(self):
        manifest = read_json(ROOT / BRIDGE_REL / 'manifest.json')
        mutations = []
        for rel in {**manifest['approved_live_source_tuple'], **manifest['supporting_live_source_tuple']}:
            def drift(root, rel=rel):
                path = root / rel
                path.write_bytes(path.read_bytes() + b'\n# unreviewed drift\n')
            mutations.append((rel, drift))
        def mixed(root):
            shutil.copyfile(root / PACKET_REL / 'proposed-guidance/intake-after.md',
                            root / 'skills/claude-guardian/references/intake.md')
        mutations.append(('mixed-old-intake-new-runtime', mixed))
        self.rejects(mutations)

    def test_historical_packet_drift_missing_and_extra_fail_closed(self):
        def change(root, rel):
            path = root / PACKET_REL / rel
            path.write_bytes(path.read_bytes() + b'\n')
        self.rejects([
            ('historical-current-pin', lambda root: change(root, 'current-guidance-source-pins.json')),
            ('historical-integration', lambda root: change(root, 'integration-manifest.json')),
            ('historical-response', lambda root: change(root, 'retained/v2-responses/T38/response-03.md')),
            ('missing-original-manifest', lambda root: (root / PACKET_REL / 'original-stage-manifest.json').unlink()),
            ('extra-historical-file', lambda root: (root / PACKET_REL / 'extra.txt').write_text('unreviewed', encoding='utf-8')),
        ])

    def test_current_review_receipt_and_guide_drift_fail_closed(self):
        mutations = []
        for rel in ['approved-preservation-review.json', 'live-helper-replay.json', 'runtime-review.md',
                    'reviewed-guidance-intake.md', 'REVIEW.md', 'preservation-review.md',
                    'projection-origins.json', 'PROJECTION.md', 'live-helper-replay-runner.py.txt']:
            def drift(root, rel=rel):
                path = root / BRIDGE_REL / rel
                path.write_bytes(path.read_bytes() + b'\n')
            mutations.append((rel, drift))
        self.rejects(mutations)

    def test_original_clause_and_layer_drift_fail_closed(self):
        mutations = []
        for key in ['requirement', 'verification_layer']:
            def drift(root, key=key):
                path = root / 'docs/acceptance-rebuild-ledger.json'
                value = read_json(path)
                next(row for row in value['cases'] if row['id'] == 'T38')[key] = 'changed'
                path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
            mutations.append((key, drift))
        self.rejects(mutations)

    def test_verifier_is_pinned_before_execution(self):
        with tempfile.TemporaryDirectory(prefix='guardian-subscription-bridge-') as tmp:
            root = Path(tmp)
            self.copy_inputs(root)
            (root / BRIDGE_REL / 'verify.py').write_text("raise RuntimeError('must never execute')\n", encoding='utf-8')
            with self.assertRaises(AssertionError):
                PINNED_LOADER(root)
