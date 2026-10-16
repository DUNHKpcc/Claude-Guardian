# Agent-driven repair: authority and implementation boundary

Requirements: D-ENV §3.4, §18–20; ENV-02/06/10; ENG-08; VAL-02/07.

## Confirmed interaction design

On 2026-10-16 the owner approved this interaction: the Agent presents the exact
change in the conversation, receives confirmation there, and invokes the internal
repair script. The user is not required to type a second confirmation code in a
terminal. Start with the user's actual installed Clash Verge/Mihomo version and
owned configuration layer, so file modification is not confused with effective
application configuration.

This approves the product design and development, not any actual device read,
configuration write, application shutdown/reload, network probe, or credential
operation. Each actual operation still needs the relevant scope and permission.

## Practical trust boundary

The trusted Agent host's ordinary action-execution approval boundary checks the
user's current conversational approval against the exact intended command. The
Python script does not authenticate chat messages. No `approved` JSON field,
terminal response, plan digest, saved receipt or caller-supplied `native_pass`
value can establish that approval or certify a native adapter.

The intended execution contract is:

1. Bind the selected device, desktop user and filesystem namespace in the host;
   obtain permission for the exact necessary local reads
2. Read only explicitly selected files, establish product/version/installation
   and authoritative active-profile/owned-extension provenance, and compile a
   bounded candidate; reject generated runtime files and subscription originals
3. Show the exact selected-rule differences, target, impact, private backup
   destination, conflict conditions and independent recovery path; keep unrelated
   configuration and secrets out of the review
4. Obtain conversational approval of that exact scope, then invoke the fixed
   audited script through the host action boundary. Do not accept arbitrary
   shell fragments, executable callback paths or serialized grants
5. Revalidate the approved scope, deadline, original snapshot, candidate,
   product/version ownership and actual writer exclusion immediately before
   commit. A changed scope needs a new plan and approval. Rechecking the same
   unchanged approval does not require repeated human questions
6. Back up, stage, verify and atomically replace the single file using the
   transaction engine; read back the exact bytes and preserve the recovery batch
7. Report file verification separately from application acceptance and routing.
   Application reloads or network probes are separate actions with their own
   supported adapters and authorization

A future cross-process approval binding must include the exact original file
snapshot (including identity, not only bytes), candidate, target, request,
operation, adapter/version, backup destination, action identity and expiry.
`transactions.plan()` deliberately generates fresh IDs and times: its digest
cannot be reproduced by independently rebuilding a new plan. Retain the trusted
private plan or define a stable review binding; do not compare unrelated fresh
transaction digests or treat matching bytes as reusable consent.

The host is a trust boundary, not a general-purpose attestation service. The
script need not invent a token server or claim that Python can prove the
integrity of its own interpreter. Running the interface outside the established
host does not inherit conversational approval.

## Native admission remains separate

The current candidate compiler retains these blockers:

- `NATIVE_SCHEMA_ADAPTER_NOT_IMPLEMENTED`
- `VERSION_CAPABILITY_UNVERIFIED`
- `NATIVE_ACCEPTANCE_NOT_RUN`

A supported adapter must establish the reviewed product/version/installation,
owned extension and active profile from authoritative product evidence, group
resolution and effective rule ordering under that version's merge behavior.
Declarations in a request are not that evidence. Synthetic fixtures and Linux
tests do not establish acceptance on the user's Mac.

### Pinned 2.5.8 supplied-metadata validator

`clash_verge_258.inspect_linkage()` is a separate read-only library. It accepts
explicitly supplied `Info.plist`, `profiles.yaml` and extension bytes plus a
selected UID and basename; it does not discover or open files. It checks the
declared bundle identifier and version, resolves `current` to one local/remote
profile, follows the explicitly selected `option.merge` or `option.rules` to
one entry of the matching type, and requires its literal basename to match the
selection. Rules mode also binds the current profile's source basename. Duplicate
profile IDs, duplicate file ownership, traversal, unsupported types and missing
links fail closed. XML and binary plist duplicate keys are rejected; parser size,
node/depth and elapsed-time checks are bounded, without claiming hard preemption
of synchronous parsers.

The source baseline is official v2.5.8 commit
`4337bd85758d54d7b9044b2da3c9ac1176eae1f3`. A merge mapping's `rules` sequence
replaces the base sequence; a rules extension instead uses `prepend`, `append`
and `delete`. Merge mode accepts only an existing merge mapping containing `rules` and
`proxy-groups`, never synthesizing a one-rule replacement for a full base.
Rules mode separately validates the three SeqMap sequences; it does not treat
them as a merge mapping. Script and
other sequence-chain references remain explicit unsupported-chain blockers.

The private linkage binds all three supplied snapshot hashes. The public result
always says `supplied_metadata_only`, `apply_supported: false`,
`native_ownership: not_verified` and `native_acceptance: not_run`. Forged or stale
metadata can still have internally consistent links; this module does not prove
installed application identity, effective runtime, core version, writer exclusion
or consent and is not connected to production execution admission.

Do not relabel an unsupported Clash repair as a generic exact-file edit merely
to bypass these gates. The existing transaction library remains a lower-level
exact-file transport, not an application adapter. `workflow_guard` support and
native-evidence requirements are not relaxed by this design.

## Concurrency, failure and recovery

Writer exclusion means actually preventing all relevant GUI, service, refresh
and sync writers for the operation. A Boolean, advisory lock, terminal phrase or
conversational statement alone is not an OS enforcement mechanism. POSIX rename
is atomic replacement, not compare-and-swap; stale-file checks cannot eliminate
the final race against an uncontrolled writer.

Only a verified applied receipt can enter ordinary rollback. A prepared-only
record, or a failure after possible replacement, requires reconciliation rather
than blind retry. Later edits or a replaced inode block rollback; do not overwrite
them or regenerate snapshots to force recovery. Recovery has fresh authorization
and retains its private backup and result. See [offline recovery](offline-recovery.md)
for the independent terminal route when the Agent is unavailable.

## Current delivery status

`repair_cli.py` adds executable offline preflight and private review around
`config_edit_plan` and the exact-file snapshot checks. An explicitly requested
plan artifact can be retained privately; this writes the new artifact, not the
target configuration. `repair_execution.py` connects retained-plan validation,
transactional apply and byte readback behind a fixed native-adapter gate.
Production execution remains blocked while no native write adapter has been
admitted. There is no actual-device modification, application reload, network
contact or effective-routing acceptance in this increment.

The separate [rules-extension route](rules-extension-plan.md) handles explicit
additions into an existing empty prepend list, with mandatory registry, app-info
and base-source inputs. It is selected explicitly and retains all native gates.
Retained artifacts now use schema 0.2; old schema 0.1 plans require fresh planning
and review, not in-place migration or restored permission.

### Internal invocation

The host first authorizes reading the explicitly selected request and target.
The request has exactly `schema_version: guardian-repair-request/0.1`,
`remedy_request` and `binding`; the latter two follow
[the candidate compiler contract](config-edit-plan.md). It is a private,
single-link file in an existing private directory, subject to the recovery
reader's ownership, path and size checks. File paths are explicit command
arguments, never executable content from that JSON.

For read-only preflight:

```sh
python3 -B skills/claude-guardian/scripts/repair_cli.py preflight \
  --request /private/review/request.json \
  --target-path /private/config/owned-extension.yaml --target-ref selected-device
```

When the host has permission to create the exact new private plan file and use
the existing private backup directory, retain and review the same artifact:

```sh
python3 -B skills/claude-guardian/scripts/repair_cli.py plan \
  --request /private/review/request.json \
  --target-path /private/config/owned-extension.yaml --target-ref selected-device \
  --plan-file /private/review/plan.json --backup-directory /private/recovery \
  --private-review
```

These are illustrative paths, not discovery defaults. `--private-review` enables
noninteractive private host output containing the exact selected selectors and
before/after policies, target and hashes. For a retained plan it also includes
the retained artifact digest, action identity, expiry and backup destination.
The private review JSON is followed by the ordinary redacted result JSON.
Do not send this private output to public logs, repository artifacts or unrelated
services. Unrelated configuration values are not included.

The future admitted execution command uses those same exact arguments with
`execute`, omits `--private-review`, and supplies
`--plan-digest FULL_RETAINED_PLAN_DIGEST`. Use `retained_plan_digest`, not the
inner transaction's separate `plan_digest`. The digest is an integrity binding,
not permission. Today this command fails with
`NATIVE_REPAIR_ADAPTER_UNAVAILABLE`; no terminal phrase or request flag removes
that blocker. Rebuilding a plan after expiry or a changed target requires review
and approval of the new scope, not reuse of the old decision.

The current development tests use private temporary synthetic files only.
Final CLI invocation details and verified regression evidence are recorded with
the implementation delivery; no full ENV or VAL acceptance is claimed here.

The later [Mac native adaptation investigation](macos-native-adaptation.md)
records real temporary-file ACL/xattr experiments, canonical runtime launches,
and pinned 2.5.8 writer/reload source observations. Different-value provenance
restoration and actual writer exclusion remain blocked; no production gate was
opened and no existing transaction metadata restriction was weakened.
