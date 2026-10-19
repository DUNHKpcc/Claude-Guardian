# Darwin private control-document read capability

Status: internal implementation and synthetic validation, pending native evidence.
Existing recovery, repair and cleanup CLI behavior is unchanged. This capability
is not yet included in the installable Skill package or production admission.

## One shared capability, bounded scope

Local, VM and VPS routes share the same detection core and result contracts.
Route selection binds the actual target, supported capabilities and inspection
depth. VM host and guest are separate scopes; VPS uses the basic profile. This
Darwin implementation is selected by the bound operating environment, not by
copying three route-specific probes or treating a route declaration as evidence.

`macos_private_read.private_document_read(file_fd, parent_fd)` brackets a caller's
bounded data-fork read. It opens no path, reads no file content or xattr values,
and does not mutate metadata. The context yields `None`, not an admission token.
The caller retains descriptor ownership and must discard its read result if
exit validation fails. The caller separately binds the selected filename to its
file descriptor and the original no-follow parent path to the parent descriptor.

The initial subset is current effective-user/group ownership, exact 0600 regular
file with one link, exact 0700 directory, bounded file size, zero flags, no ACL
entries, and accessible attribute names empty or only `com.apple.provenance`.
Unknown, compression, resource-fork, FinderInfo, quarantine and synthetic marker
attributes are rejected. Naming a recognized attribute does not establish its
safety for copying or deleting. This narrow mode policy does not alter the old
reader's supported modes.

Selected stat snapshots and effective identity are compared around metadata reads
and the caller's body. They detect some changes, but provide neither an atomic
snapshot nor writer exclusion, and cannot defeat descriptor reuse or arbitrary
same-user interference. ACL reads are bounded to one entry query. Native calls
may block in the kernel; no hard I/O deadline is promised.

## Native ABI distinction

`observe_acl_fd(fd)` returns one fixed label: `no_acl_reported`, `empty_acl` or
`entries_present`. It does not expose ACL principals, text, UUIDs or attribute
names/values. Apple descriptor retrieval can report an absent ACL as null with
ENOENT. For a validated ACL, Darwin `acl_get_entry` returns 0 with an entry;
-1/EINVAL with no entry is the source-derived empty case. The two absence forms
remain distinct and are rechecked rather than silently conflated.

Sources checked on 2026-10-19:

- [Apple ACL declarations](https://github.com/apple-oss-distributions/Libc/blob/main/include/sys/acl.h)
- [Apple descriptor ACL retrieval](https://github.com/apple-oss-distributions/Libc/blob/main/posix1e/acl_file.c)
- [Apple entry iteration](https://github.com/apple-oss-distributions/Libc/blob/main/posix1e/acl_entry.c)
- [Apple FILESEC_ACL handling](https://github.com/apple-oss-distributions/Libc/blob/main/gen/filesec.c)
- [Apple attribute-list visibility](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/listxattr.2.html)

These moving source references explain the implementation; they are not a claim
about the installed OS or filesystem. Every returned ACL object is released.
Permission failures, unsupported APIs, unexpected returns and release failures
block the capability rather than being reported as empty metadata.

## Disposable native experiment

After the host authorizes synthetic temporary fixtures on its Darwin environment:

```sh
python -B tools/macos_private_read_probe.py
```

The command accepts no file paths. It creates six fresh private fixture pairs:
natural metadata, explicit empty ACLs, a file ACL entry, a parent ACL entry, a file
marker and a parent marker. It reads only the synthetic JSON it wrote. Existing
metadata values, identity strings, user paths, network and applications are not
read or contacted. Fixture mutation code reuses the existing bounded test helper;
no production writer is invoked.

A completed experiment is not necessarily a pass. `all_expected` requires both
positive cases to read exact synthetic bytes and each negative case to fail with
the expected ACL/attribute code. Unrelated failures remain failures. Results from
hosted Mac CI and a user's actual Mac must be recorded separately. Inherited
ACLs, nonzero flags, namespaces, real control documents and application effects
are not covered by these six fixtures.

## Next integration boundary

Only after applicable native validation, connect this narrow reader to the
selected-receipt `inspect` command. Do not globally relax `load_receipt`: repair
requests and retained plans also use it. Preview, reconcile, rollback, target
replacement, cleanup, app activation and restoration have separate safeguards
and remain pending. Readability of an existing data fork does not establish
metadata-preserving writes or recoverability.
