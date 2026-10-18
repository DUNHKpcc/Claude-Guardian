"""Test-only authority for exclusively owned synthetic trees; never packaged."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile

class FixtureHost:
    def __init__(self):
        self._temporary = tempfile.TemporaryDirectory(prefix='guardian-cleanup-cli-')
        self.base = Path(self._temporary.name).resolve()
        self.base.chmod(0o700)
        for name in ('app', 'backup', 'protected', 'quarantine'):
            (self.base/name).mkdir(mode=0o700)
        for name in ('app', 'backup'):
            (self.base/name/'data').write_bytes(b'synthetic')
            (self.base/name/'data').chmod(0o600)
        (self.base/'protected/keep').write_bytes(b'protected')
        (self.base/'protected/keep').chmod(0o600)
        scope = {'schema_version':'guardian-cleanup-operator-scope/0.1',
            'target_ref':'fixture-target','mode':'C5-full-local-data',
            'roots':[{'root_ref':'app','path':str(self.base/'app'),'data_kind':'cli_app_data'}],
            'protected_paths':[str(self.base/'protected'),str(self.base/'backup')],
            'quarantine_directory':str(self.base/'quarantine'),
            'backup_ref':'fixture-backup','host_context_ref':'fixture-host'}
        self.scope = scope
        self.root_identity = self._identity(self.base/'app')
        self.data_identity = self._identity(self.base/'app/data')
        self.events = []
        self.denied = set()
        self.active = False
        self.scope_digest = hashlib.sha256(json.dumps({k: scope[k] for k in (
            'roots', 'protected_paths', 'quarantine_directory', 'target_ref', 'mode')},
            sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()
        self.identities = {str(p): (p.stat().st_dev, p.stat().st_ino) for p in
                           [self.base, self.base/'protected', self.base/'backup', self.base/'quarantine']}

    @staticmethod
    def _identity(path):
        st = path.stat(); return st.st_dev, st.st_ino, st.st_mode

    def close(self):
        self._temporary.cleanup()

    def verify(self, target, digest, bindings):
        self.events.append(('verify', target, digest))
        assert target == self.scope['target_ref'] and digest == self.scope_digest
        assert bindings == {k: self.scope[k] for k in ('backup_ref', 'host_context_ref')}
        for path, identity in self.identities.items():
            p = Path(path)
            assert not p.is_symlink() and (p.stat().st_dev, p.stat().st_ino) == identity
        assert (self.base/'protected/keep').read_bytes() == b'protected'
        assert (self.base/'backup/data').read_bytes() == b'synthetic'
        selected = self.base/'app'
        if not selected.exists():
            candidates = [p/'root-0000' for p in (self.base/'quarantine').iterdir()
                          if p.is_dir() and not p.is_symlink() and (p/'root-0000').exists()]
            assert len(candidates) == 1
            selected = candidates[0]
        assert not selected.is_symlink() and self._identity(selected) == self.root_identity
        assert {p.name for p in selected.iterdir()} == {'data'}
        assert not (selected/'data').is_symlink()
        assert self._identity(selected/'data') == self.data_identity
        assert (selected/'data').read_bytes() == (self.base/'backup/data').read_bytes() == b'synthetic'
        return 'active_host' if self.active else 'verified_inactive_claude_data'

    def approve(self, operation, digest, target, private_review):
        self.events.append(('approve', operation, digest, target))
        assert target == self.scope['target_ref']
        assert operation in {'read_hash_scope','save_plan','quarantine','read_reconcile','save_receipt','restore_cleanup'}
        assert hashlib.sha256(json.dumps(private_review, sort_keys=True,
            separators=(',', ':'), ensure_ascii=True).encode()).hexdigest() == digest
        review = private_review
        if operation in {'save_plan','save_receipt'}:
            output = Path(review['output_path'])
            assert output.parent == self.base and output.name in {'plan.json','receipt.json'}
            review = review['document']
        if operation == 'read_hash_scope':
            assert review == self.scope
        else:
            assert review['bindings'] == {k:self.scope[k] for k in ('backup_ref','host_context_ref')}
            material = review['material']
            plan = material if review['kind']=='plan' else material['plan']
            assert plan['scope_digest'] == self.scope_digest
            assert [{k:r[k] for k in ('root_ref','path','data_kind')} for r in plan['roots']] == self.scope['roots']
            assert plan['protected_paths'] == self.scope['protected_paths']
            assert plan['quarantine_directory'] == self.scope['quarantine_directory']
        return operation not in self.denied

    @contextmanager
    def exclusive(self, target, scope_digest, bindings):
        self.verify(target, scope_digest, bindings)
        self.events.append(('exclusive', 'entered'))
        # This fixture has no application or competing fixture writers.
        yield
        self.events.append(('exclusive', 'exited'))

    def cancelled(self):
        return False
