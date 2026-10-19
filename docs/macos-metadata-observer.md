# macOS metadata observer: one approved descriptor

`scripts/macos_metadata_observer.py` adds a bounded, read-only observation of one
already-open, effective-user-owned regular file or directory on Darwin. It does
not open paths, scan directories, read file contents or attribute values, change
metadata, change security settings, or invoke a repair/cleanup host adapter.
The installed release explicitly includes this script; this guide and audit
artifacts stay repository-side.

## Agent invocation

The trusted caller must first bind the device, user, filesystem namespace and
exact selected object, obtain the required read approval, and open that object
through its verified no-follow path workflow. Opening and permission are the
caller's responsibility; an fd number is not authorization. Keep the descriptor
open and prevent its concurrent close/reuse until the child finishes.

The CLI accepts only `--fd INTEGER`, once. Pass the actual already-open descriptor
with `pass_fds`; typing an fd number into an unrelated terminal does not transfer
it. `observer_script` below is the host's fixed, reviewed installed script, not an
arbitrary executable supplied by a report. This macOS caller example performs no
opening or discovery:

```python
import json
import subprocess
import sys


def observe_selected_fd(observer_script, approved_fd):
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(observer_script),
         "--fd", str(approved_fd)],
        pass_fds=(approved_fd,),
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
    )
    return completed.returncode, json.loads(completed.stdout)
```

The caller retains ownership of the descriptor. Timeout, cancellation, malformed
output or a nonzero result does not establish an observation. Do not automatically
retry, select another object or widen the approved scope. JSON goes to stdout;
there are no output-path flags or automatic report files. Optional retention is
the caller's separate, approved private-output step. `--help` works off Darwin
without opening a descriptor or loading the native library.

## Reading the result

Schema: `guardian-macos-metadata-observation/1`. Exit status is 0 for `observed`,
1 for blocked/unsupported/invalid input, and 2 for cancellation. The fixed `code`
distinguishes platform/binding limits from denied, malformed, changing or failed
observations. Failure is never an empty-metadata result; counts remain null.
`native_name_listing: available` means the symbol was bound, not that a listing
succeeded; always check `observation_state` and `code` together.

Python lacking `os.listxattr` does not mean macOS lacks xattrs. On Darwin the
observer binds only the read-only `flistxattr` symbol in the fixed
`/usr/lib/libSystem.B.dylib`; no setter or copy API is used. It bounds the name
list to 65,536 bytes, 32 names and 127 bytes per name, repeats the listing and
checks descriptor state. A matching repeat does not prove an atomic snapshot,
writer exclusion, or that metadata stayed unchanged between reads.

Public output contains fixed categories/counts and `flags: unknown|zero|nonzero`.
Categories are `provenance`, `compression`, `resource_fork`, `finder_info`,
`quarantine`, `synthetic_marker` and `unknown`; recognizing one does not make it
harmless. No arbitrary attribute names, values, hashes, UID, inode or selected
path are emitted. `xattr_visibility: accessible_names_only` is an explicit limit:
an observed zero count is not proof of complete metadata absence.

`attribute_values` and `acl` remain `not_inspected`; `atomic_snapshot`,
`writer_exclusion`, `preservation` and `write_admission` remain `not_established`,
including on exit 0. Use the report to explain a limited observation, never to
approve replacement, receipt access, C5 moves or recovery. Existing production
admission gates remain unchanged.

## Verification boundary

New-module native macOS execution is pending. Synthetic/offline tests and
installed `--help` checks do not validate the Darwin ABI on a device or establish
preservation. Earlier Mac copy/probe evidence concerns a different tool and
cannot validate this module. No real-device operation is authorized by this
guide. Current integration results belong in [validation](validation.md);
broader unresolved native requirements remain in
[macOS adaptation](macos-native-adaptation.md).
