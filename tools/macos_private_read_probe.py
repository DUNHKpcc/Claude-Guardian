#!/usr/bin/env python3
"""Opt-in Darwin read-guard experiment on disposable, owned fixtures only.

No path arguments, existing file reads, metadata values, ACL principals, network
or application operations. This experiment does not enable production writers.
The host authorizes running these synthetic fixture mutations on its device.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import macos_private_read as reader
_fixture_spec = importlib.util.spec_from_file_location(
    "guardian_private_read_fixture_support", Path(__file__).with_name("macos_metadata_probe.py"))
_fixture = importlib.util.module_from_spec(_fixture_spec)
_fixture_spec.loader.exec_module(_fixture)
DarwinMetadata, MetadataError, MARKER = _fixture.DarwinMetadata, _fixture.MetadataError, _fixture.MARKER


def set_empty_acl(api, fd):
    acl = api.acl_init(0)
    if not acl:
        raise MetadataError('TEMP_ACL_INIT_FAILED')
    try:
        if api.acl_set_fd(fd, acl, 0x100):
            raise MetadataError('TEMP_EMPTY_ACL_SET_FAILED')
    finally:
        if api.acl_free(acl):
            raise MetadataError('TEMP_ACL_RELEASE_FAILED')


def assess(file_fd, parent_fd):
    report = {}
    for role, fd in (('file', file_fd), ('parent', parent_fd)):
        try:
            report[role + '_acl'] = reader.observe_acl_fd(fd)
        except reader.PrivateReadError as error:
            report[role + '_acl'] = error.code
    try:
        with reader.private_document_read(file_fd, parent_fd):
            # The helper reads metadata, not content. This caller's bounded
            # data-fork read is solely the synthetic JSON written below.
            report['fixture_bytes_match'] = os.pread(file_fd, 3, 0) == b'{}'
        report['read_guard'] = 'accepted'
    except reader.PrivateReadError as error:
        report['read_guard'] = error.code
    return report


def run():
    if sys.platform != 'darwin':
        raise MetadataError('UNSUPPORTED_PLATFORM')
    if os.geteuid() == 0 or os.getuid() != os.geteuid():
        raise MetadataError('ORDINARY_USER_REQUIRED')
    api = DarwinMetadata()
    results = {}
    cases = ('natural', 'explicit_empty', 'file_acl', 'parent_acl',
             'file_marker', 'parent_marker')
    with tempfile.TemporaryDirectory(prefix='guardian-read-fixture-') as root:
        for case in cases:
            directory = Path(root) / case
            directory.mkdir(mode=0o700)
            parent = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            file_fd = None
            try:
                file_fd = os.open('receipt.json', os.O_CREAT | os.O_EXCL | os.O_RDWR |
                                  os.O_NOFOLLOW, 0o600, dir_fd=parent)
                if os.write(file_fd, b'{}') != 2:
                    raise MetadataError('TEMP_SHORT_WRITE')
                if case == 'explicit_empty':
                    set_empty_acl(api, file_fd)
                    set_empty_acl(api, parent)
                elif case in ('file_acl', 'parent_acl'):
                    api.fixture_acl(file_fd if case == 'file_acl' else parent, writable=False)
                elif case in ('file_marker', 'parent_marker'):
                    api.set_attribute(file_fd if case == 'file_marker' else parent,
                                      MARKER, b'fixed-synthetic-marker')
                results[case] = assess(file_fd, parent)
            finally:
                if file_fd is not None:
                    os.close(file_fd)
                os.close(parent)
    accepted = ('natural', 'explicit_empty')
    expected = all(results[name]['read_guard'] == 'accepted' and
                   results[name].get('fixture_bytes_match') is True for name in accepted)
    for name in ('file_acl', 'parent_acl'):
        role = 'file' if name == 'file_acl' else 'parent'
        expected = expected and results[name]['read_guard'] == 'ACL_ENTRIES_PRESENT'
        expected = expected and results[name][role + '_acl'] == 'entries_present'
    for name in ('file_marker', 'parent_marker'):
        expected = expected and results[name]['read_guard'] == 'UNSUPPORTED_XATTR_NAMES'
    return {'schema_version': 'guardian-private-read-fixture/1',
            'scope': 'owned_disposable_fixtures_only',
            'cases': results, 'all_expected': expected,
            'production_cli_admission': 'unchanged',
            'write_admission': 'unchanged',
            'limitations': ['No inherited ACL, nonzero flags or namespace certification',
                            'No metadata values or ownership changes inspected',
                            'No atomic snapshot or writer exclusion established',
                            'No transaction, cleanup or application recovery exercised']}


def main(argv=None):
    class Parser(argparse.ArgumentParser):
        def error(self, message):
            raise MetadataError('INPUT_INVALID')
    try:
        Parser(allow_abbrev=False, description=__doc__).parse_args(argv)
        report = run()
        print(json.dumps(report, sort_keys=True))
        return 0 if report['all_expected'] else 1
    except KeyboardInterrupt:
        print(json.dumps({'status': 'cancelled', 'code': 'CANCELLED'}))
        return 2
    except MetadataError as error:
        print(json.dumps({'status': 'blocked', 'code': str(error)}))
        return 1
    except Exception:
        print(json.dumps({'status': 'blocked', 'code': 'FIXTURE_FAILED'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
