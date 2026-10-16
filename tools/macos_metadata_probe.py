#!/usr/bin/env python3
"""Opt-in Darwin metadata experiment; every write targets owned temp fixtures.

Optional runtime arguments authorize no reads by themselves: the calling host
must already approve those exact runtime metadata sources. Only the bounded
com.apple.provenance attribute is read from them. No source bytes, attributes,
identities or paths are exported. This is not a production file adapter.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

MAX_ATTRIBUTE = 65536
PROVENANCE = b'com.apple.provenance'
MARKER = b'user.guardian.synthetic'


class MetadataError(Exception):
    """Fixed diagnostic codes only; native exception messages stay private."""


class DarwinMetadata:
    def __init__(self):
        if sys.platform != 'darwin':
            raise MetadataError('UNSUPPORTED_PLATFORM')
        lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
        def bind(name, result, *args):
            fn = getattr(lib, name)
            fn.restype, fn.argtypes = result, list(args)
            return fn
        void, size, integer = ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int
        self.list = bind('flistxattr', ctypes.c_ssize_t, integer, void, size, integer)
        signature = (integer, ctypes.c_char_p, void, size, ctypes.c_uint32, integer)
        self.get = bind('fgetxattr', ctypes.c_ssize_t, *signature)
        self.put = bind('fsetxattr', integer, *signature)
        self.copy = bind('fcopyfile', integer, integer, integer, void, ctypes.c_uint32)
        self.acl_get = bind('acl_get_fd_np', void, integer, integer)
        self.acl_text = bind('acl_to_text', void, void, ctypes.POINTER(ctypes.c_ssize_t))
        self.acl_free = bind('acl_free', integer, void)
        self.uid_uuid = bind('mbr_uid_to_uuid', integer, ctypes.c_uint32, void)
        self.acl_init = bind('acl_init', void, integer)
        self.acl_create = bind('acl_create_entry', integer, ctypes.POINTER(void), ctypes.POINTER(void))
        self.acl_tag = bind('acl_set_tag_type', integer, void, integer)
        self.acl_qualifier = bind('acl_set_qualifier', integer, void, void)
        self.acl_get_perms = bind('acl_get_permset', integer, void, ctypes.POINTER(void))
        self.acl_clear_perms = bind('acl_clear_perms', integer, void)
        self.acl_add_perm = bind('acl_add_perm', integer, void, integer)
        self.acl_set_perms = bind('acl_set_permset', integer, void, void)
        self.acl_set_fd = bind('acl_set_fd_np', integer, integer, void, integer)

    def attribute(self, fd, name):
        length = self.get(fd, name, None, 0, 0, 0)
        if type(length) is not int or not 0 <= length <= MAX_ATTRIBUTE:
            raise MetadataError('ATTRIBUTE_UNAVAILABLE_OR_OVERSIZED')
        value = ctypes.create_string_buffer(max(length, 1))
        if self.get(fd, name, value, length, 0, 0) != length:
            raise MetadataError('ATTRIBUTE_CHANGED')
        return value.raw[:length]

    def attributes(self, fd):
        length = self.list(fd, None, 0, 0x0020)  # XATTR_SHOWCOMPRESSION
        if type(length) is not int or not 0 <= length <= MAX_ATTRIBUTE:
            raise MetadataError('ATTRIBUTE_LIST_BOUNDS')
        buffer = ctypes.create_string_buffer(max(length, 1))
        if self.list(fd, buffer, length, 0x0020) != length:
            raise MetadataError('ATTRIBUTE_LIST_CHANGED')
        names = list(filter(None, buffer.raw[:length].split(b'\0')))
        if len(names) > 32 or len(set(names)) != len(names):
            raise MetadataError('ATTRIBUTE_LIST_BOUNDS')
        return {name: self.attribute(fd, name) for name in names}

    def set_attribute(self, fd, name, value):
        buffer = ctypes.create_string_buffer(value)
        if self.put(fd, name, buffer, len(value), 0, 0):
            raise MetadataError('TEMP_ATTRIBUTE_SET_FAILED')

    def acl(self, fd):
        acl = self.acl_get(fd, 0x100)  # ACL_TYPE_EXTENDED, installed sys/acl.h
        if not acl:
            raise MetadataError('ACL_READ_FAILED')
        text = None
        try:
            length = ctypes.c_ssize_t()
            text = self.acl_text(acl, ctypes.byref(length))
            if not text or not 0 <= length.value <= MAX_ATTRIBUTE:
                raise MetadataError('ACL_TEXT_FAILED')
            return ctypes.string_at(text, length.value)
        finally:
            # Attempt both releases even if the first fails.
            text_ok = not text or self.acl_free(text) == 0
            acl_ok = self.acl_free(acl) == 0
            if not text_ok or not acl_ok:
                raise MetadataError('ACL_RELEASE_FAILED')

    def fixture_acl(self, fd, *, writable):
        """Set a fixed self-user ACL, only on our already-open temp fixture."""
        qualifier = (ctypes.c_ubyte * 16)()
        if self.uid_uuid(os.getuid(), ctypes.byref(qualifier)):
            raise MetadataError('TEMP_ACL_IDENTITY_FAILED')
        acl = ctypes.c_void_p(self.acl_init(1))
        if not acl.value:
            raise MetadataError('TEMP_ACL_SET_FAILED')
        try:
            entry, permissions = ctypes.c_void_p(), ctypes.c_void_p()
            if (self.acl_create(ctypes.byref(acl), ctypes.byref(entry)) or
                    self.acl_tag(entry, 1) or  # ACL_EXTENDED_ALLOW
                    self.acl_qualifier(entry, ctypes.byref(qualifier)) or
                    self.acl_get_perms(entry, ctypes.byref(permissions)) or
                    self.acl_clear_perms(permissions) or
                    self.acl_add_perm(permissions, 1 << 1) or  # ACL_READ_DATA
                    (writable and self.acl_add_perm(permissions, 1 << 2)) or
                    self.acl_set_perms(entry, permissions) or
                    self.acl_set_fd(fd, acl, 0x100)):
                raise MetadataError('TEMP_ACL_SET_FAILED')
        finally:
            if self.acl_free(acl):
                raise MetadataError('ACL_RELEASE_FAILED')


def snapshot(api, fd):
    """Private, bounded fixture data; never serialize the returned object."""
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_size > 4096:
        raise MetadataError('FIXTURE_BOUNDS')
    return {'contents': os.pread(fd, 4097, 0), 'mode': stat.S_IMODE(info.st_mode),
            'owner': info.st_uid, 'group': info.st_gid,
            'xattrs': api.attributes(fd), 'acl': api.acl(fd)}


def equality(expected, actual):
    result = {field: expected[field] == actual[field]
              for field in ('contents', 'mode', 'owner', 'group', 'xattrs', 'acl')}
    result['provenance'] = (PROVENANCE in expected['xattrs'] and
                            actual['xattrs'].get(PROVENANCE) == expected['xattrs'][PROVENANCE])
    return result


def differences(expected, actual):
    result = {field: expected[field] != actual[field]
              for field in ('contents', 'mode', 'owner', 'group', 'xattrs', 'acl')}
    result['provenance'] = expected['xattrs'].get(PROVENANCE) != actual['xattrs'].get(PROVENANCE)
    return result


def provenance_result(distinct_sources, assignments, initially_different, restored):
    if not assignments:
        return 'not_run_no_runtime_sources'
    if (distinct_sources is not True or len(assignments) != 3 or
            any(value is not True for value in assignments) or initially_different is not True):
        return 'blocked_fixture_values_not_distinct_or_setter_not_effective'
    return 'observed_different_value_restore' if restored is True else 'failed_copy_readback'


def copy_fixture(api, source, target, *, reset_offsets):
    if reset_offsets:
        os.lseek(source, 0, os.SEEK_SET)
        os.lseek(target, 0, os.SEEK_SET)
    if api.copy(source, target, None, 15):  # COPYFILE_ALL, installed copyfile.h
        raise MetadataError('TEMP_COPY_FAILED')


def reset_restore_fixture(api, fd, group, provenance=None):
    """Re-establish divergence after the negative copy, using only our fixture."""
    contents = b'different fixture'
    if os.pwrite(fd, contents, 0) != len(contents):
        raise MetadataError('TEMP_FIXTURE_SHORT_WRITE')
    os.ftruncate(fd, len(contents))
    os.fchmod(fd, 0o600)
    os.fchown(fd, -1, group)
    api.fixture_acl(fd, writable=True)
    api.set_attribute(fd, MARKER, b'different-marker')
    if provenance is not None:
        api.set_attribute(fd, PROVENANCE, provenance)
        return api.attribute(fd, PROVENANCE) == provenance
    return None


def _runtime_provenance(api, path):
    # This follows only the already approved runtime's path, never any output
    # from a configuration. It does not change the strict native-context screen.
    fd = os.open(os.path.realpath(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise MetadataError('RUNTIME_METADATA_SOURCE_INVALID')
        return api.attribute(fd, PROVENANCE)
    finally:
        os.close(fd)


def run(runtime_sources=()):
    if sys.platform != 'darwin':
        raise MetadataError('UNSUPPORTED_PLATFORM')
    if os.geteuid() == 0 or os.getuid() != os.geteuid():
        raise MetadataError('ORDINARY_USER_REQUIRED')
    if len(runtime_sources) not in (0, 2):
        raise MetadataError('TWO_APPROVED_RUNTIME_SOURCES_REQUIRED')
    api = DarwinMetadata()
    provenance = [_runtime_provenance(api, path) for path in runtime_sources]
    out = {'schema_version': 'guardian-macos-metadata-experiment/0.1',
           'write_scope': 'three_owned_disposable_files_only',
           'source_values_exported': False, 'production_apply_supported': False,
           'gate_state': 'closed'}
    with tempfile.TemporaryDirectory(prefix='guardian-metadata-') as temporary:
        root = Path(temporary).resolve()
        paths = [root / name for name in ('original', 'backup', 'restore')]
        handles = []
        try:
            for index, path in enumerate(paths):
                path.write_bytes(b'original fixture' if index == 0 else b'different fixture')
                path.chmod(0o640 if index == 0 else 0o600)
                handles.append(os.open(path, os.O_RDWR | os.O_NOFOLLOW))
                api.fixture_acl(handles[-1], writable=index != 0)
            source, saved, restored = handles
            primary = os.getegid()
            alternate = next((g for g in sorted(os.getgroups()) if g != primary), None)
            provenance_assignments = []
            for index, fd in enumerate(handles):
                os.fchown(fd, -1, primary if index == 0 or alternate is None else alternate)
                api.set_attribute(fd, MARKER, b'original-marker' if index == 0 else b'different-marker')
                if provenance:
                    selected = provenance[0 if index == 0 else 1]
                    api.set_attribute(fd, PROVENANCE, selected)
                    provenance_assignments.append(api.attribute(fd, PROVENANCE) == selected)
            original = snapshot(api, source)
            before = snapshot(api, restored)
            out['different_before_restore'] = differences(original, before)
            out['distinct_runtime_provenance_sources'] = len(provenance) == 2 and provenance[0] != provenance[1]
            out['provenance_fixture_assignment_readback'] = provenance_assignments
            out['source_visible_xattr_count'] = len(original['xattrs'])
            for label, left, right, reset in (('backup', source, saved, True),
                    ('restore_without_reset_offsets', saved, restored, False),
                    ('restore_with_reset_offsets', saved, restored, True)):
                if label == 'restore_with_reset_offsets':
                    assignment = reset_restore_fixture(api, restored,
                        primary if alternate is None else alternate,
                        provenance[1] if provenance else None)
                    out['reset_restore_provenance_assignment_readback'] = assignment
                    out['different_before_reset_restore'] = differences(original, snapshot(api, restored))
                copy_fixture(api, left, right, reset_offsets=reset)
                out[label] = equality(original, snapshot(api, right))
            out['different_provenance_restore'] = provenance_result(
                out['distinct_runtime_provenance_sources'], provenance_assignments,
                (out['different_before_reset_restore']['provenance'] and
                 out['reset_restore_provenance_assignment_readback'] is True),
                out['backup']['provenance'] and out['restore_with_reset_offsets']['provenance'])
            out['original_unchanged'] = snapshot(api, source) == original
            out['different_owner_restore'] = 'blocked_no_distinct_user_or_privilege_authorization'
            out['complete_application_recovery'] = 'not_run'
            out['compression_resource_forks_flags_timestamps'] = 'not_exercised'
            out['observation_state'] = 'partial'
            return out
        finally:
            for fd in handles:
                os.close(fd)


def main(argv=None):
    class Parser(argparse.ArgumentParser):
        def error(self, message):
            raise MetadataError('INPUT_INVALID')
    parser = Parser(description=__doc__)
    parser.add_argument('--runtime-metadata-source', action='append', default=[],
                        help='already approved interpreter metadata source; either zero or two')
    try:
        args = parser.parse_args(argv)
        result = run(tuple(args.runtime_metadata_source))
    except KeyboardInterrupt:
        result = {'observation_state': 'cancelled', 'code': 'CANCELLED', 'gate_state': 'closed'}
    except MetadataError as error:
        result = {'observation_state': 'blocked', 'code': str(error), 'gate_state': 'closed'}
    except Exception:
        result = {'observation_state': 'blocked', 'code': 'NATIVE_EXPERIMENT_FAILED', 'gate_state': 'closed'}
    print(json.dumps(result, sort_keys=True))
    return 2 if result.get('observation_state') == 'cancelled' else 1 if result.get('observation_state') == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
