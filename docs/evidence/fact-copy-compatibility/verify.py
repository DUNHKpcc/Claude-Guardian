"""One exact fact-snapshot transition; historical bytes and live execution are separate."""
from contextlib import contextmanager
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile

REL = 'docs/evidence/fact-copy-compatibility'
RUNTIME = 'skills/claude-guardian/scripts/interview_flow.py'
BEFORE = '691aa0b634ba7ff1d26d3d13a3a9c58a6e43924047c63338b41b832529e3ffa9'
AFTER = '9f5237846756759a90e907eebe096f9263c0d938e78aecf4173fafb3912ede25'
OLD_LINE = '    fact = {"value": value, "state": state_name, "source": source,\n'
NEW_LINE = '    fact = {"value": deepcopy(value), "state": state_name, "source": source,\n'
RESUME_SUITE = 'tests/test_acceptance_resume_completion.py'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(root, relative):
    p = PurePosixPath(relative)
    require(isinstance(relative, str) and relative and not p.is_absolute()
            and '..' not in p.parts and '\\' not in relative and ':' not in relative
            and p.as_posix() == relative, 'Unsafe relative path')
    path = Path(root)
    for part in p.parts:
        path = path / part
        require(not path.is_symlink(), 'Symlink is not source evidence: ' + relative)
    return path


def digest(path):
    require(path.is_file() and not path.is_symlink(), 'Missing or unsafe source: ' + str(path))
    return sha(path.read_bytes())


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def inventory(root):
    require(root.is_dir() and not root.is_symlink(), 'Missing or unsafe packet')
    values = {}
    for path in root.rglob('*'):
        relative = path.relative_to(root).as_posix()
        require(not path.is_symlink(), 'Packet symlink: ' + relative)
        if '__pycache__' not in path.parts and path.is_file():
            values[relative] = digest(path)
    return {'files': len(values), 'canonical_inventory_sha256': sha(canonical(values))}


def reconstruct_historical_runtime(raw):
    """Return real old bytes only after proving the exact new whole-file identity."""
    require(sha(raw) == AFTER, 'Unreviewed current runtime')
    require(raw.count(NEW_LINE.encode()) == 1 and OLD_LINE.encode() not in raw,
            'Unexpected fact-copy transition')
    historical = raw.replace(NEW_LINE.encode(), OLD_LINE.encode(), 1)
    require(sha(historical) == BEFORE, 'Incorrect reconstructed historical runtime')
    return historical


def verify_current(root, expected_manifest):
    root = Path(root)
    directory = safe_path(root, REL)
    require(digest(directory / 'manifest.json') == expected_manifest, 'Unreviewed compatibility manifest')
    manifest = read_json(directory / 'manifest.json')
    require(manifest['schema'] == 'guardian-fact-copy-compatibility/1'
            and manifest['historical_records_unchanged'] is True
            and manifest['new_model_generation'] is False, 'Compatibility boundary changed')
    require(manifest['transition'] == {'path': RUNTIME, 'before_sha256': BEFORE,
            'after_sha256': AFTER, 'old_line': OLD_LINE, 'new_line': NEW_LINE}, 'Transition identity changed')
    actual = {p.name for p in directory.iterdir() if p.name != '__pycache__'}
    require(actual == set(manifest['files']) | {'manifest.json'}, 'Compatibility inventory changed')
    for relative, expected in manifest['files'].items():
        require(digest(safe_path(directory, relative)) == expected, 'Compatibility payload changed: ' + relative)
    reconstruct_historical_runtime(safe_path(root, RUNTIME).read_bytes())
    for relative, expected in manifest['unchanged_source_pins'].items():
        require(digest(safe_path(root, relative)) == expected, 'Unchanged prerequisite drift: ' + relative)
    for relative, expected in manifest['historical_packet_inventories'].items():
        require(inventory(safe_path(root, relative)) == expected, 'Historical packet changed: ' + relative)
    return manifest


@contextmanager
def historical_source_view(root, expected_manifest):
    """A disposable historical review fixture, never represented as the live tree.

    No hashes are substituted. The old verifier reads actual reconstructed old
    runtime bytes and byte-identical prerequisite copies. Live replays use root.
    """
    root = Path(root)
    manifest = verify_current(root, expected_manifest)
    old_bytes = reconstruct_historical_runtime((root / RUNTIME).read_bytes())
    with tempfile.TemporaryDirectory(prefix='guardian-historical-source-view-') as temporary:
        historical = Path(temporary)
        for relative in set(manifest['unchanged_source_pins']) | {'docs/acceptance-rebuild-ledger.json'}:
            source = safe_path(root, relative)
            target = historical / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        target = historical / RUNTIME
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(old_bytes)
        for relative in manifest['historical_packet_inventories']:
            shutil.copytree(root / relative, historical / relative, copy_function=shutil.copyfile,
                            ignore=shutil.ignore_patterns('__pycache__'))
        require(digest(target) == BEFORE, 'Historical view reconstruction changed')
        yield historical


def verify_historical_pin_on_current(root, relative, historical_digest, expected_manifest):
    """Explicitly distinguish unchanged bytes from the one reviewed transition."""
    manifest = verify_current(root, expected_manifest)
    if relative == RUNTIME:
        require(historical_digest == BEFORE, 'Unknown historical runtime')
        require(sha(reconstruct_historical_runtime((Path(root) / relative).read_bytes())) == historical_digest,
                'Historical runtime reconstruction mismatch')
    else:
        require(manifest['unchanged_source_pins'].get(relative) == historical_digest,
                'Source is outside this exact compatibility review')
        require(digest(safe_path(root, relative)) == historical_digest, 'Historical source drift')


def module(name, path):
    if path.suffix == '.txt':
        loader = importlib.machinery.SourceFileLoader(name, str(path))
        spec = importlib.util.spec_from_loader(name, loader)
    else:
        spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def replay_output(root, suite, *, expected=None):
    root = Path(root)
    env = dict(os.environ, GUARDIAN_AUDIT_ROOT=str(root), PYTHONDONTWRITEBYTECODE='1',
               PYTHONIOENCODING='utf-8')
    result = subprocess.run([sys.executable, '-B', str(root / suite), '--replay'],
                            cwd=root, env=env, capture_output=True, check=False)
    require(result.returncode == 0, 'Semantic replay failed: ' + suite + '\n' + result.stderr.decode('utf-8'))
    if suite == RESUME_SUITE:
        require(expected is not None, 'Resume replay requires its explicit platform receipt')
        verify_replay_execution(result.stderr.decode('utf-8'), expected)
    return json.loads(result.stdout.decode('utf-8'))


def execution_profile(expected, execution_os_name=None):
    """Select a complete recorded result; never drop or synthesize trace fields."""
    profiles = expected.get('execution_profiles')
    if profiles is None:
        return expected
    require(expected['command'] == 'python -B ' + RESUME_SUITE + ' --replay'
            and set(profiles) == {'posix', 'nt'}, 'Unexpected platform-specific replay')
    require(profiles['posix']['canonical_sha256'] == expected['canonical_sha256'],
            'Original complete POSIX replay hash changed')
    platform = os.name if execution_os_name is None else execution_os_name
    require(platform in profiles, 'Unreviewed replay execution platform')
    return profiles[platform]


def verify_replay_execution(stderr, expected, execution_os_name=None):
    """The original suite's exact skip remains visible, never counted as passed."""
    profile = execution_profile(expected, execution_os_name)
    require('unittest' in profile, 'Missing platform execution evidence')
    # Captured unittest logs use platform line endings; trace JSON is untouched.
    stderr = '\n'.join(stderr.splitlines())
    runs = re.findall(r'^Ran ([0-9]+) tests? in ', stderr, re.MULTILINE)
    skips = [list(row) for row in re.findall(
        r"^(test_[A-Za-z0-9_]+) .* \.\.\. skipped '([^']*)'$", stderr, re.MULTILINE)]
    require(runs == [str(profile['unittest']['tests'])], 'Replay test inventory changed')
    require(skips == profile['unittest']['skipped'], 'Replay platform skip inventory changed')


def verify_replay_value(value, expected, execution_os_name=None):
    profile = execution_profile(expected, execution_os_name)
    if 'trace_keys' in profile:
        require(isinstance(value, dict) and sorted(value) == profile['trace_keys'],
                'Replay platform trace inventory changed')
    require(sha(canonical(value)) == profile['canonical_sha256'], 'Semantic replay result mismatch')


def replay_subscription(root):
    directory = Path(root) / 'docs/evidence/batch33-subscription-preservation'
    adapter = module('fact_copy_live_subscription_adapter', directory / 'live-helper-replay-runner.py.txt')
    actual = adapter.run_replay(root, Path(root) / 'docs/evidence/subscription-boundaries')
    old = read_json(Path(root) / 'docs/evidence/subscription-boundaries/reviewer-controls/actual-control-report.json')
    # The pinned adapter compares complete calls and outputs, including no-I/O
    # sentinels. Only interpreter/platform execution labels are not semantic.
    observed = {k: v for k, v in actual['result'].items() if k not in {'python_version', 'execution_platform'}}
    expected = {k: v for k, v in old.items() if k not in {'python_version', 'execution_platform'}}
    require(observed == expected, 'Subscription replay differs from historical control')
    return {'call_count': actual['result']['call_count'], 'blocked_io_attempts': actual['result']['blocked_io_attempts'],
            'semantic_sha256': sha(canonical(observed))}


def replay_upgrade(root):
    root = Path(root)
    packet = root / 'docs/evidence/subscription-upgrade-conflict'
    saved = {key: os.environ.get(key) for key in ('GUARDIAN_AUDIT_ROOT', 'GUARDIAN_UPGRADE_EXPECTED_MANIFEST')}
    try:
        os.environ['GUARDIAN_AUDIT_ROOT'] = str(root)
        os.environ['GUARDIAN_UPGRADE_EXPECTED_MANIFEST'] = 'cc7d25b302de2ebfa1d265fafb689a3b90768c9f8db4feb25ee68a199dea2fa2'
        retained = module('fact_copy_live_upgrade_replay', packet / 'tests/test_upgrade_conflict_evidence.py')
        rows = retained.replay_current_calls()
        require(rows == retained.EVIDENCE['current_replay']['calls'], 'Upgrade replay differs from historical calls')
        return {'call_count': len(rows), 'same_recorded_errors': sum(row['status'] == 'same_recorded_error' for row in rows),
                'semantic_sha256': sha(canonical(rows))}
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
