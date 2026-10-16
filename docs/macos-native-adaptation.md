# macOS native adaptation investigation

Scope: ENV-01/02/06/09, ENG-01/08, VAL-02/07. Project baseline:
`2921e4f72ba0c0bcd2d37bdfb6d5410248f045e6`. No production repair adapter is admitted.
The old working directory and its uncommitted changes were retained; this work
uses a separate clean clone. No real configuration writes, GUI/core shutdown,
reload, proxy/DNS/TUN/firewall changes or external diagnostics were performed.

## Reproducible temporary metadata experiment

`tools/macos_metadata_probe.py` creates exactly three disposable files. Every
write is to these files; its optional two runtime arguments read only the bounded
`com.apple.provenance` attribute of already approved interpreter files. The host
must authorize these exact metadata sources before invoking the tool. The CLI
does not establish approval. It never prints values, file paths or identities.

The experiment sets different contents, mode, current-user group membership,
ordinary synthetic xattr and explicit self-user ACL. Darwin ACL objects are
created through `mbr_uid_to_uuid`, `acl_create_entry` and `acl_set_fd_np` using
the installed Apple SDK ABI; private UUID/text values are released and omitted.
`fcopyfile(COPYFILE_ALL)` is compared against exact content, mode, owner/group,
accessible xattr bytes and ACL text. Both descriptor offsets are reset before
the positive copy case. The unreset-offset counterexample remains in the result.

Observed on the scoped Mac:

- Different data, mode, group, ordinary xattr and explicit ACL were actually
  present before the backup copy, which compared equal. The original recovery
  sequence reused the destination after the negative copy had already restored
  metadata; reset-offset equality therefore proves content recovery and equal
  metadata preservation, not restoration of different metadata
- Ownership was preserved, but changing ownership to a different user requires
  an independently authorized identity/privilege boundary and was not attempted
- The two runtime sources had distinct real provenance values. The first
  fixture's setter returned success, but immediate readback did not match the
  selected value; readback flags were false/true/true. The fixtures retained equal
  provenance, so different-value provenance restoration remains **blocked**
- Preserving an already equal provenance value is a separate limited observation
- Without resetting offsets, the API returned success while restored contents
  differed. Apple `copyfile(3)` explicitly documents that offsets are not reset
- The original fixture remained unchanged; no attributes were deleted/ignored
- Compression/resource forks/file flags/timestamps and full application recovery
  were not exercised. The overall observation remains partial, gate closed

The initial numeric-name `chmod +a` fixture setup failed. It was replaced by the
documented current-user UUID ACL API; that failure is retained in the handoff.
No production transaction, recovery reader or native-admission gate was changed.
The earlier equal-value setter experiment cannot establish the missing case.

## Cloud review correction (native evidence transfer pending)

Review of the exported result found that the negative copy had already restored
mode/group/xattrs/ACL before the positive recovery. The corrected probe reseeds
the restore fixture with different content, mode, group, ordinary xattr and ACL,
and retries the second approved provenance value when provided. It snapshots
`different_before_reset_restore` immediately before the positive copy and records
`reset_restore_provenance_assignment_readback` independently. A different-value
provenance result now requires this fresh assignment and immediate difference.
The original `different_before_restore` describes the pre-counterexample state.

Two additional synthetic regressions check reseeding and exact operation order.
These are cloud tests only. The previous native result remains historical and
does not establish corrected native recovery. A scoped Mac run must show
true immediate differences for each claimed dimension, true backup/recovery
comparisons and `original_unchanged`; absent/differing ownership, provenance,
compression, resource forks, flags, timestamps and full application recovery
remain separately limited or blocked. Production admission stays closed.

## Runtime path result

Strict capture using the normal interpreter spelling still encounters a symlink.
A fresh child launched using each existing interpreter's actual canonical
executable, `-I -S -B`, sanitized environment and a fixed root-owned working
directory completed capture/recheck. No `sys.executable`, prefix or native
identity was mocked or reassigned; the strict collector was unchanged.

Both the Homebrew and managed runtime still returned
`rejected_writable_or_nonroot`, `runtime_integrity: not_verified`, unknown
filesystem/network namespaces, and a closed gate. This establishes a supported
way to avoid the lexical symlink obstacle in a real launch, not trusted-runtime
admission. The existing root-owned Apple CLT Python was 3.9.6, below the project's
3.10 minimum; it is not a supported replacement runtime.

An admitted host must separately establish interpreter/dependency integrity and
namespace binding. A root-owned supported interpreter installation or changing
the ownership of user files is not authorized here. Canonical paths alone do
not solve dependency replacement, signatures, ACLs, mounts or execution races.

## Clash Verge Rev 2.5.8 writers and application acceptance

The approved installed metadata still reports product/build 2.5.8. The current
index and linked merge/rules files were re-read privately: references were
unique and stable; merge remained comments/whitespace only; rules had empty
prepend/append/delete lists. No subscription payload, UID, actual extension
filename or private configuration hash was exported. Stability over a bounded
read is not writer exclusion. Additional script/merge/proxy/group-chain blockers
reported by the supplied-metadata validator remain unresolved.

The official source tag resolves to
`4337bd85758d54d7b9044b2da3c9ac1176eae1f3`. It was read without building/running it.

- [`save_profile_file`](https://github.com/clash-verge-rev/clash-verge-rev/blob/4337bd85758d54d7b9044b2da3c9ac1176eae1f3/src-tauri/src/cmd/save_profile.rs)
  reads the selected file, writes it with `fs::write`, validates and may restore
  the old contents. Active linked extensions trigger `update_config_forced`.
  No external compare-and-swap or third-party writer lease is exposed there
- [`rules-editor-viewer`](https://github.com/clash-verge-rev/clash-verge-rev/blob/4337bd85758d54d7b9044b2da3c9ac1176eae1f3/src/components/profile/rules-editor-viewer.tsx)
  saves its in-memory `currData`. An already open stale editor can overwrite an
  external edit; the frontend's own lock does not exclude a Python writer
- [`Timer`](https://github.com/clash-verge-rev/clash-verge-rev/blob/4337bd85758d54d7b9044b2da3c9ac1176eae1f3/src-tauri/src/core/timer.rs)
  and [`update_profile`](https://github.com/clash-verge-rev/clash-verge-rev/blob/4337bd85758d54d7b9044b2da3c9ac1176eae1f3/src-tauri/src/feat/profile.rs)
  can update the subscription and regenerate the active runtime independently
- [`reload_or_restart` and service application](https://github.com/clash-verge-rev/clash-verge-rev/blob/4337bd85758d54d7b9044b2da3c9ac1176eae1f3/src-tauri/src/core/manager/config.rs)
  can restart/replace the core after a failed reload. Saving an active extension
  can also synchronize the DNS override. Approval limited to a harmless file
  save would not cover those effects
- [`quit`](https://github.com/clash-verge-rev/clash-verge-rev/blob/4337bd85758d54d7b9044b2da3c9ac1176eae1f3/src-tauri/src/feat/window.rs)
  coordinates configuration saves and core cleanup; treating GUI exit as a
  network-neutral writer pause is unsupported

These are source observations, not proof of the installed binary's runtime
behavior. No supported external writer-suspension protocol was established in
the inspected paths. An advisory filesystem lock or unchanged hash cannot fill
that gap.

## Smallest next operation plan for owner review

1. Keep CLI production apply blocked. Independently bind the existing app/core
   instance, runtime integrity and private output/recovery locations. Obtain
   additional precise read permission for the minimum base-rule/group/chain
   projection needed by the candidate compiler; current index/extension scope
   does not authorize reading the subscription payload
2. For an initial supported application exercise, use the app-owned rules editor
   under host supervision, after reviewing the exact requested rule diff and
   closing stale editors. Approval must name the chosen current extension and
   include save/validation, possible runtime reload **and core restart/replace**,
   DNS-override synchronization and connectivity impact. No such operation or
   approval is claimed here; no concrete rule selector was supplied this round
3. Verify file bytes/metadata and index/current linkage separately from app
   validation and active rules. Any API verification requires separately approved
   exact read-only `/version`, `/configs` or `/rules` requests to an independently
   bound existing local core. Authenticated transport needs its own approved
   private credential scope; do not request secrets in chat. No healthcheck,
   DNS query, subscription refresh or `/connections` is implied
4. A production CLI file writer needs actual cooperative writer exclusion from
   the application, or an explicitly approved maintenance window that stops the
   relevant writers and accounts for core/network effects. Neither has been
   implemented or authorized. Different provenance restoration and the other
   metadata/trust gaps must close before admitting that adapter

No terminal confirmation code or serialized `native_pass` is introduced. The
existing conversational review/host-approval design remains in force.


## Corrected native callback (evidence file not transferred)

The Mac task callback reports 14 targeted tests passed and two corrected runs
with immediate differences for contents, mode, group, ordinary xattrs and ACL,
matching values after positive recovery, and an unchanged original. Provenance
still lacked an immediate difference. The upload handshake failed: the cloud
review has read the callback only and has not downloaded or independently
verified the corrected result JSON. This does not close the remaining metadata,
runtime, writer-exclusion or application recovery acceptance. The earlier 91
full-suite Mac failures/errors remain recorded; no combined full Mac suite is
claimed. See validation.md for the final cloud batch and evidence distinction.
