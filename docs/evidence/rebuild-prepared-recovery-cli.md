# Selected prepared recovery: CLI and active-guidance evidence

Date: 2026-10-18. Execution boundary: cloud Linux, synthetic private temporary
files, independent Python subprocesses and real POSIX pseudo-terminals. This page
records the callable CLI integration of the separately reviewed recovery core.
It does not change any original acceptance status or claim full-project completion.

## Original conditions and exact boundary

The original rows and their tracker layers are unchanged:

| Original ID | Full scenario | Full required behavior | Layers |
|---|---|---|---|
| ENV-T68 | 清理/故障演练后 Agent 不可连接且需要恢复 | 独立终端能读取离线恢复清单；敏感备份不公开，凭据撤销等不可逆动作不得承诺自动恢复 | L + N + R |
| ENV-T87 | 故障演练会同时切断 Codex 服务连接 | 预先准备独立恢复并核实本地执行能力；不要求用户回到已断网 Agent 取得恢复指令 | L + N + X + R |
| ENV-T40 | 纯域名/规则提供方/主规则/JSON 格式转换 | 不可表达的 ASN/匹配/动作语义明确报错，不静默丢失 | L + R |

L is pure logic/dialogue/fixtures; C is content/source review; R is controlled
write/restoration; N is target-native/real-host interaction; X is authorized
network/current external facts. These layers need their own evidence. The exact-file CLI provides limited L/R
support for T68/T87 and addresses the missing prepared-restoration subpath found
in the ninth conversion transaction exercise. It does not establish native
device recovery, a disconnected Agent scenario, a complete format converter, or
full satisfaction of any row above. The original ledger remains authoritative.

No real user configuration, application, proxy, browser policy, network setting,
credential, deletion, account or Claude service is exercised. No production
native admission is opened: `repair_execution._native_session` still fails with
`NATIVE_REPAIR_ADAPTER_UNAVAILABLE`. Windows restoration remains unsupported; the
new CLI class is skipped outside POSIX. A skip is not a pass. Linux temporary-file
evidence does not certify macOS or Windows. These are exact-byte/mode operations,
not verified application-effective or network-effective recovery.

## Before and after, without rewriting historical evidence

The ninth CLI at SHA-256
`06fcd1cf994e8dfa374740a561190748ff9f6257fd9107634e5cdf061d8964e2`
offered `inspect`, `preview` and `rollback`. After a target replacement followed
by an `applied.json` journal failure, `prepared.json` and `original.bin` remained.
Inspect could read the selected receipt; preview/rollback returned
`RECOVERY_REQUIRES_RECONCILIATION`. There was no separately callable restoration
path from the retained prepared evidence. The ninth historical evidence is kept
unchanged; its failure statement describes that snapshot.

The new core records a version-2 staged-file witness. The CLI now offers a
read-only `reconcile` and a separately authorized `restore-prepared` command.
The old preview/rollback rejection of prepared receipts is deliberately retained.
Only a version-2 `prepared_candidate_observed` result can enter the new restore
path. The change does not retroactively turn legacy version-1 prepared records
into recoverable evidence, manufacture a historical applied receipt, replay apply,
or solve the converter's unsupported action/match/schema cases.

Initial witness recognition tolerates rename's ctime change while matching the
recorded staged identity and supported metadata/content. It does not prove an
uninterrupted history or rule out inode reuse under arbitrary interference.
Actual writer exclusion is still required; the complete observed current
snapshot is bound without relaxation throughout the later restoration approvals.

## Callable contract and compatibility

- `inspect --receipt PATH`: opens only the selected private receipt; output is an
  unverified candidate digest. It does not follow embedded target/backup paths
- `preview` / `rollback`: existing applied-receipt scope and approval contract
  remains; neither admits a prepared record
- `reconcile`: requires `--receipt`, `--receipt-digest`, `--target-ref`,
  `--target-path`, `--backup-batch`. The CLI validates the selected digest; core
  checks caller scope before target/backup reads. It writes nothing and emits a
  curated private observation, never original/proposed bytes or base64
- `restore-prepared`: additionally requires `--reconciliation-digest`. The value
  is exactly `digest({'recovery_digest': digest(receipt), 'observation': observation})`,
  including complete receipt/backup/target snapshots and batch identity. It is
  the same digest checked by both `restore_prepared` authorization callbacks
- Changed scope or observation blocks before prompting. Noncandidate, applied,
  restore-attempt and legacy records remain read-only through the new path. An
  observation exit code 0 means the read completed, including a conflict result;
  it does not mean restoration or readiness
- Actual restoration requires a real terminal with three fresh random challenges:
  `EXCLUSIVE ACCESS ESTABLISHED`, then twice `RESTORE_PREPARED <bound digest>`.
  The original receipt and entire observation are rechecked before and after
  each approval. The core also rechecks immediately before replacement
- Pipes, `--yes`, saved grants, an apply/rollback phrase, queued future responses,
  cancellation and prompt expiry cannot authorize this operation. The timeout
  bounds terminal input only, not filesystem I/O
- Result/error output is content-free but private. Safe recovery/attempt IDs and
  the three fixed cleanup codes are preserved; arbitrary exception attributes
  are not printed. A failure may follow actual restoration and must not be
  described as proof the target was unchanged

Trusted Agent hosts can call the same public `reconcile` and `restore_prepared`
APIs after establishing actual current scope/permission/writer exclusion. The
active guidance forbids arbitrary true callbacks, saved JSON authorization, and
terminal automation as substitutes for consent. This is a callable integration
contract, not evidence that a particular Agent UI or native adapter performed it.
The ordinary terminal remains usable independently once the two scripts and
private records have been prepared locally before disruption.

## Fixed inputs and exact observed results

Every fixture creates an existing single-link file owned by the effective
user/group, mode 0600, under its own canonical `TemporaryDirectory`, with a
separate 0700 backup directory. The original bytes are exactly
`b'original synthetic data'`; proposed bytes are exactly `b'new synthetic data'`.
Neither includes a final newline. The target reference is `synthetic-device`.
The producer process really exits with code 74 immediately before writing
`applied.json`, after replacement. No real host file is used.

| Reproducible case | Expected and actual result |
|---|---|
| Read-only observe after producer exit 74 | Target is exactly proposed bytes; only prepared state is retained. Classification `prepared_candidate_observed`; returned reconciliation digest equals the independent canonical operation digest; repeated observation is identical and the full private file tree is unchanged |
| Restore without observed digest | Exit 2, `EXPECTED_RECONCILIATION_REQUIRED`, no terminal prompt, target/batch unchanged |
| Wrong valid-format digest / malformed digest | Exit 2, respectively `RECONCILIATION_STALE` / `INVALID_EXPECTED_DIGEST`; no prompt or write |
| Three current terminal challenges | Exit 0, exactly three prompts; target equals original bytes with mode 0600; original prepared receipt and original.bin remain; one restore witness and one rollback result exist; no applied.json is manufactured |
| Each cancelled prompt, queued future input, timeout, pipe, old rollback phrase | Exit 2; no target replacement or new durable batch record; staging cleaned unless the separate cleanup fault is injected |
| Wrong target path/ref, batch or receipt digest | Stable mismatch code before embedded reads; full file tree unchanged |
| Target changed after observation | `RECONCILIATION_STALE` before prompting; new read-only classification is `conflict`; later bytes preserved |
| Same-content replacement of target, receipt or backup inode | Old reconciliation digest is rejected; no prompt or write; identity changes are not treated as unchanged content |
| Target edited at each of three prompts | Exit 2; exact later bytes remain; no rollback result or leftover staging |
| Receipt or original backup edited at final prompt | `AUTHORIZATION_CANCELLED`; changed private material remains; proposed target bytes remain |
| Version-1 prepared conversion fixture | `legacy_identity_unproven` is observable; `LEGACY_RECOVERY_IDENTITY_UNPROVEN` blocks restore without prompts or writes |
| Producer exits before replace / completed applied receipt | `original_observed` / `applied_observed`; both rejected by new restore path without prompts or writes |
| Successful restoration witness selected | `restored_candidate_observed`; attempted replay returns `PREPARED_RECOVERY_REQUIRED`, no prompt or write |
| Restore-witness write fault after final actual approval | `IO_FAILURE`, all three prompts occurred; target remains proposed bytes and full prior tree is unchanged; new read-only reconcile still recognizes the candidate |
| Result-journal fault after restoration | `IO_FAILURE`, all three prompts occurred; target is original bytes despite failure, original prepared and restore witness remain, no rollback result. Opaque error IDs identify the exact witness; selected reconcile yields `restored_candidate_observed` and no subsequent write occurs |
| Final cancellation plus staging unlink fault | Primary `AUTHORIZATION_CANCELLED` plus `STAGING_CLEANUP_FAILED`; target remains proposed bytes; one retained stage contains exact original bytes; private backup remains |
| Error-projection fault only | Three allowlisted cleanup codes survive; arbitrary cleanup text and non-hex recovery/attempt IDs are omitted; no TTY bypass, approval or write is involved |

The fault tests wrap only synthetic-process filesystem calls. New restoration
tests never patch `confirm`, `isatty`, terminal input validation, or production
native admission. The inherited PTY helper was extended only with a command
argument; its old default remains `rollback`. The separate original suite still
tests old behavior, including expiry, unsafe receipt types, selected-only inspect,
and existing rollback failures.

## Active guidance review, sentence by sentence

The review covers the changed SKILL recovery paragraph, the complete new
`agent-remediation.md#prepared-recovery` section and the changed offline guide.

1. Preparation sentences require trusted local scripts, original private backup,
   steps and verified local execution before an outage. They do not promise to
   recover by returning to an unavailable online Agent
2. Scope sentences restrict reads to an independently established selected
   receipt, target and batch; inspect's candidate digest is explicitly unverified
3. Classification sentences distinguish observed candidate, original, legacy,
   applied, restore-attempt and conflict states. They never equate observation
   with a historical successful apply or permission
4. Version/admission sentences limit the new write path to witnessed version-2
   candidates and keep old prepared/conflicting states blocked. No receipt editing
   or fabricated historical applied state is permitted
5. Difference/approval sentences require exact bytes/mode impact, trusted semantic
   review, actual permission and writer exclusion. Library callback and ordinary
   terminal workflows are described separately and cannot forge each other's consent
6. Revalidation sentences bind the complete observation, require both new approval
   checks, stop on changes and forbid silently replacing a stale digest to retry
7. Result/failure sentences say restoration covers current exact bytes/mode only;
   a late error can follow mutation. Safe IDs locate one selected witness, but
   neither IDs nor missing result files prove what committed. Restoration-attempt
   reconciliation stays read-only
8. Cleanup sentences preserve the fixed secondary failure codes and warn that
   retained staging may contain private bytes. They do not silently delete it
9. Privacy and exclusions keep original/proposed content and sensitive hashes out
   of public reports; revoked credentials, deletion, OS settings, Windows and
   application/network recovery are not represented as supported
10. Native-gate/test-limit sentences retain the closed production repair gate and
    distinguish Linux synthetic subprocess/PTY evidence from actual device and
    disconnected-control-channel validation

These are content/source-review findings, not model-integration or native evidence.

## Reproduction and retained receipts

```sh
python -B -m unittest discover -s tests -p 'test*recovery_cli.py' -v
PYTHONPATH=tests python -B -m unittest test_transactions test_prepared_recovery \
  test_recovery_cli test_prepared_recovery_cli test_rule_conversion_transaction -v
```

Observed locally: 38 CLI tests passed (18 new and 20 existing); the combined
exact-file/core/CLI/conversion-transaction run passed 129 tests in 10.321 seconds.
Counts summarize the runs; the concrete assertions above establish their scope.

The final core delta was separately reviewed against the previously frozen
`ee59d886…` source: persisted journals now use the same bounded compact encoding
as their canonical digests, and future applied/restore envelopes are reserved
before authorization. A legal long Unicode path with a near-limit proposal now
fails `INVALID_DOCUMENT` before any approval or batch creation; original bytes
remain. The public API and document limit are unchanged. The final 38 CLI checks
passed again in 8.326 seconds, and the 129-test composition includes the new
failing-first budget regression. The normal/failure byte trace was rerun on this
final core; its current hash is recorded below. Other reviewed CLI/guidance code
and findings are unchanged.

The user-owned verification bundle is
`/tmp/guardian-prepared-recovery-cli-tenth/`: `cli-tests-budget-fix.log`, `combined-tests-budget-fix.log`,
`trace-reproducer.py` and `trace.json`. The trace captures complete actual CLI
output and exact byte results for normal restoration, post-restoration journal
failure, and cleanup failure; all paths/data are dedicated synthetic fixtures.
The reproducer takes the repository root as its sole argument. Nonces, inode
numbers, paths and operation digests naturally differ on rerun; the exact
operation digest is recomputed from each concrete observation, never hardcoded.

Reproducer SHA-256: `1b9a2532fff0da9a4d5157b55022df5b47b0759de7cdf9b9dcf42836824ce203`.
Captured trace SHA-256: `dfaddecdf258fb38ac15110e4af5bd7637df571cfb8480243acc95de257f5cbe`.

## Reviewed file pins

The following hashes identify the reviewed current snapshot. This page does not
pin itself; its own digest is recorded in the delivery receipt.

| File | SHA-256 |
|---|---|
| `skills/claude-guardian/scripts/transactions.py` | `53c1fa7a3f2e2fff2737ba3dbe96d0dbe748bfdbbed73b2a7d15f05c723190cd` |
| `skills/claude-guardian/scripts/recovery_cli.py` | `0355e39cd8375f5044431d98f9949dddce05b2f07b30334f92fed3225621b732` |
| `tests/test_transactions.py` | `2f8dc38138319f65627ad2e54863cdddeaaba67e28c0280e589b2e1da9edb51c` |
| `tests/test_prepared_recovery.py` | `b5bdb007d70cd3fa8de8d629ac3b67f448244a2217661f61e0f18fcdd447ccef` |
| `tests/test_recovery_cli.py` | `13474ad92b04adb1ef974d7cdfa2490b15e2f41053e00021f808a87c91ef2371` |
| `tests/test_prepared_recovery_cli.py` | `15f81b93bad9442417602691e4db9b69d34b562e3e888d739d9bebd4e2945e1d` |
| `docs/offline-recovery.md` | `cdfda0163a1b3405ab93be8ade5f8a1806c5e36ee7eed87c37291d4776ddec3c` |
| `skills/claude-guardian/SKILL.md` | `958c27324e41d46dc2977d60db285b26994bcd5aa6691ae61263be7469765d6e` |
| `skills/claude-guardian/references/agent-remediation.md` | `e9cf0aad0908ad98d4864d884a6f0a4301c06eb057a8f89738d0a98f338d84eb` |
| `skills/claude-guardian/scripts/repair_execution.py` | `ca7540482cc3059f47f365b80b1cac27dae9ab32e30269537a744582c2cb6554` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |

## Rollback and remaining work

Code rollback is removal of the two new CLI verbs/tests and restoration of the
prior guidance from the retained ninth snapshot. Existing old commands remain
available. Reverting CLI/core code does not undo a file operation or delete any
private evidence; retain a compatible trusted tool to inspect records already
created. No user-device configuration was changed by this batch.

Native/environment admission, actual writer exclusion on a real host, application
effect, disconnected-Agent end-to-end testing, Windows recovery and all remaining
original conversion conditions still require their own evidence. The scope of
this page ends at the reviewed callable exact-file path and active guidance.
