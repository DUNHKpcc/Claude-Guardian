"""Strict old bridge loader and an explicitly historical, byte-real source view.

``load(root)`` still rejects any source outside the old exact compatibility
review. ``historical_baseline(root)`` never grants current-source acceptance.
"""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile

REL = 'docs/evidence/fact-copy-compatibility'
EXPECTED_MANIFEST = '95c7bdeaa430a735f1f154d2748f600ccafc6312e5e11f941aa47ada8b599d5e'
SNAPSHOT_REL = 'tests/fixtures/historical-fact-copy-95015be'
EXPECTED_SNAPSHOT_MANIFEST = '17ce86957d19f476247ca35203c9d8153316d2d95c453a91c19bd75494ef291b'


def _safe_path(root, relative):
    if not isinstance(relative, str):
        raise AssertionError('Unsafe historical relative path')
    part = PurePosixPath(relative)
    if (not relative or relative == '.' or part.is_absolute() or '..' in part.parts
            or '\\' in relative or ':' in relative or part.as_posix() != relative):
        raise AssertionError('Unsafe historical relative path')
    path = Path(root)
    if path.is_symlink():
        raise AssertionError('Historical source root is a symlink')
    for component in part.parts:
        path = path / component
        if path.is_symlink():
            raise AssertionError('Historical source symlink: ' + relative)
    return path


def _bytes(path):
    if path.is_symlink() or not path.is_file():
        raise AssertionError('Missing or unsafe historical source: ' + str(path))
    return path.read_bytes()


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _load_pinned_verifier(root):
    directory = _safe_path(root, REL)
    path = directory / 'manifest.json'
    raw = _bytes(path)
    if _digest(raw) != EXPECTED_MANIFEST:
        raise AssertionError('Missing or unreviewed fact-copy compatibility manifest')
    manifest = json.loads(raw)
    verifier = directory / 'verify.py'
    if _digest(_bytes(verifier)) != manifest['files']['verify.py']:
        raise AssertionError('Unreviewed fact-copy verifier must not execute')
    spec = importlib.util.spec_from_file_location('guardian_fact_copy_compatibility', verifier)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(root):
    """Verify the original exact tuple; never reinterpret changed current code."""
    module = _load_pinned_verifier(root)
    module.verify_current(root, EXPECTED_MANIFEST)
    return module


def verify_historical_sources(root):
    """Validate one explicit origin for every member before copying/executing."""
    directory = _safe_path(root, SNAPSHOT_REL)
    manifest_path = directory / 'manifest.json'
    raw = _bytes(manifest_path)
    if _digest(raw) != EXPECTED_SNAPSHOT_MANIFEST:
        raise AssertionError('Unreviewed historical source manifest')
    manifest = json.loads(raw)
    if (manifest['schema'] != 'guardian-historical-fact-copy-source/1'
            or manifest['purpose'] != 'historical_only_not_current_acceptance'
            or manifest['fact_copy_manifest_sha256'] != EXPECTED_MANIFEST):
        raise AssertionError('Historical source boundary changed')
    if _digest(_bytes(directory / 'README.md')) != manifest['readme_sha256']:
        raise AssertionError('Historical source explanation changed')
    snapshots = {relative for relative, entry in manifest['sources'].items()
                 if entry['origin'] == 'snapshot'}
    expected_files = {'manifest.json', 'README.md'} | {'source/' + p for p in snapshots}
    actual_files = set()
    expected_directories = {parent.as_posix() for relative in expected_files
                            for parent in PurePosixPath(relative).parents
                            if parent.as_posix() != '.'}
    actual_directories = set()
    for path in directory.rglob('*'):
        relative = path.relative_to(directory).as_posix()
        if path.is_symlink():
            raise AssertionError('Historical snapshot symlink: ' + relative)
        if path.is_file():
            actual_files.add(relative)
        elif path.is_dir():
            actual_directories.add(relative)
        else:
            raise AssertionError('Unsupported historical snapshot member')
    if actual_files != expected_files or actual_directories != expected_directories:
        raise AssertionError('Historical snapshot inventory changed')
    if (len(snapshots) != manifest['snapshot_files']
            or sum(manifest['sources'][p]['size_bytes'] for p in snapshots) != manifest['snapshot_bytes']):
        raise AssertionError('Historical snapshot totals changed')
    for relative, entry in manifest['sources'].items():
        if entry['origin'] == 'snapshot':
            path = _safe_path(directory / 'source', relative)
        elif entry['origin'] == 'repository':
            path = _safe_path(root, relative)
        else:
            raise AssertionError('Unknown historical source origin')
        raw = _bytes(path)
        if len(raw) != entry['size_bytes'] or _digest(raw) != entry['sha256']:
            raise AssertionError('Historical ' + entry['origin'] + ' source drift: ' + relative)
    return manifest


@contextmanager
def historical_baseline(root):
    """Yield release 95015be's necessary public bytes, never a live-tree alias."""
    root = Path(root)
    manifest = verify_historical_sources(root)
    verifier = _load_pinned_verifier(root)
    old_manifest = json.loads(_bytes(_safe_path(root, REL + '/manifest.json')))
    if manifest['historical_packet_inventories'] != old_manifest['historical_packet_inventories']:
        raise AssertionError('Historical packet scope changed')
    for relative, expected in manifest['historical_packet_inventories'].items():
        if verifier.inventory(_safe_path(root, relative)) != expected:
            raise AssertionError('Historical packet changed: ' + relative)
    expected_bridge = {'manifest.json'} | set(old_manifest['files'])
    directory = _safe_path(root, REL)
    if {p.name for p in directory.iterdir() if p.name != '__pycache__'} != expected_bridge:
        raise AssertionError('Compatibility inventory changed')
    for relative, expected in old_manifest['files'].items():
        if _digest(_bytes(_safe_path(directory, relative))) != expected:
            raise AssertionError('Compatibility payload changed: ' + relative)
    with tempfile.TemporaryDirectory(prefix='guardian-explicit-historical-baseline-') as temporary:
        historical = Path(temporary)
        for relative, entry in manifest['sources'].items():
            origin = root / SNAPSHOT_REL / 'source' if entry['origin'] == 'snapshot' else root
            target = historical / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = _bytes(_safe_path(origin, relative))
            if len(raw) != entry['size_bytes'] or _digest(raw) != entry['sha256']:
                raise AssertionError('Historical source changed during copy: ' + relative)
            target.write_bytes(raw)
        for relative in [REL, *manifest['historical_packet_inventories']]:
            shutil.copytree(_safe_path(root, relative), historical / relative,
                            copy_function=shutil.copyfile,
                            ignore=shutil.ignore_patterns('__pycache__'))
        # The unchanged verifier performs its original complete tuple checks on
        # these real bytes. Its old "current" means only the fact-copy baseline.
        load(historical)
        yield historical
