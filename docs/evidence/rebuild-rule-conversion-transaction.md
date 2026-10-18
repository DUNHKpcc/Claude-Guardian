# Rule conversion: controlled temporary-artifact transaction evidence

Date: 2026-10-18. Scope: actual POSIX file operations on dedicated synthetic
cloud temporary targets, composed with the public pure-conversion API. This is
supporting evidence for original ENV-T40, not acceptance of its full scenario.

## Original condition and limits

The original D-ENV v0.3 §12.1 row is unchanged:

| ID | Scenario | Required behavior | Validation layers |
|---|---|---|---|
| ENV-T40 | 纯域名/规则提供方/主规则/JSON 格式转换 | 不可表达的 ASN/匹配/动作语义明确报错，不静默丢失 | L + R |

The tracker defines L as pure logic/dialogue/fixtures and R as controlled write
and restoration. Both are required. Test counts do not replace a clause review.
This page does not change the original-case ledger or claim full-project completion.

The converter supplies predicate-only artifacts. This increment verifies an
existing standalone output artifact being wholly replaced and then restored.
It does not merge a fragment into a real mixed configuration or claim unrelated
bytes inside such a configuration were preserved. Separate synthetic source and
neighbor files are protected and compared after each operation.

No engine is installed or executed. No real host configuration, GUI, application,
network setting, account, controller or service endpoint is used. Existing
production repair admission remains closed. Windows transaction writes remain
unsupported; the new integration class is explicitly skipped on non-POSIX
platforms, and a skip is not a pass. Linux results do not certify macOS or Windows.

## Exact APIs composed, without a new writer

The test file is `tests/test_rule_conversion_transaction.py`. It invokes:

1. `rule_format_conversion.convert_rule_format(source_bytes, source_profile,
   target_profile, ordered_rule_refs, source_binding)`
2. The returned object's `private_material()['output_bytes']`
3. `transactions.plan(existing_path, output_bytes, target_ref)`
4. `transactions.apply(plan, target_ref=..., backup_directory=...,
   authorize=..., exclusive_access=True)`
5. `transactions.verify(applied_receipt)`
6. `transactions.rollback(applied_receipt, target_ref=..., authorize=...,
   exclusive_access=True)` with a distinct receipt-bound authorizer

The plan API is read-only. Conversion rejection occurs before it is called.
The fixture creates an existing single-link regular target, owned by the current
effective user/group, mode 0640, and a separate private backup directory, mode
0700. All paths are inside its own canonical temporary root. Source and neighbor
files have mode 0600. The fixture excludes other writers except explicit conflict
injections. It does not claim that a boolean itself establishes exclusion or consent.

Apply authorization checks the exact digest of `{plan, backup_directory}` and
the target reference. Rollback checks the independently computed receipt digest
and target. Each succeeds only for its corresponding operation, including the
second precommit check. Apply approval cannot authorize rollback.

Transactions preserve the supported bytes/mode/owner/group boundary; replacement
does not promise preservation of inode or timestamps. Unsupported file types,
ownership, xattrs and other metadata remain rejected by the existing primitive.
There is no new file-creation API, general output writer, or automatic recovery
adapter. Synthetic fixture setup/cleanup is test infrastructure, not production
transaction behavior; the transaction itself retains its backup and journals.

`repair_execution._native_session` still raises
`NATIVE_REPAIR_ADAPTER_UNAVAILABLE`. `windows_transactions.apply`, `verify` and
`rollback` remain unsupported. These gates are not patched or bypassed by this
composition; the lower-level POSIX primitive is exercised in its declared scope.

## Fixed source and exact expected outputs

The binding uses `guardian-rule-source-binding/0.1`, an exact SHA-256 of the
supplied bytes, synthetic aliases, `evidence_kind=user_supplied`, date 2026-10-18,
and `activation_state=candidate`. A matching digest establishes byte identity,
not source authenticity, freshness, platform permission or engine compatibility.

The exact original target bytes are:

```text
{"version":1,"rules":[{"domain":["old.example.invalid"]}]}
```

Each text block below includes one final LF. The test freezes the complete byte
strings, not selected phrases or a count of generated records.

### Plain exact output

Source and target profile: `exact-domain-lines/0.1`. One record, `rule-a`.

```text
example.invalid
```

### Mihomo domain-provider output

Source profile: `mihomo/1.19.32/provider-classical-yaml`. Target profile:
`mihomo/1.19.32/provider-domain-yaml`. Two records, `rule-a`, then `rule-b`.

```yaml
payload:
  - 'api.example.invalid'
  - '+.example.invalid'
```

### Mihomo classical-provider output

Source profile: `mihomo/1.19.32/provider-domain-yaml`. Target profile:
`mihomo/1.19.32/provider-classical-yaml`. Same two record references and order.

```yaml
payload:
  - 'DOMAIN,api.example.invalid'
  - 'DOMAIN-SUFFIX,example.invalid'
```

The preceding two YAML blocks are each the other's source fixture.

### sing-box source-rule-set JSON output

Source: the classical-provider block above. Target profile:
`sing-box/1.12.0/source-rule-set-json-v1`. Same two record references and order.

```json
{"version":1,"rules":[{"domain":["api.example.invalid"]},{"domain_suffix":["example.invalid"]}]}
```

Schema version 1 is this converter's chosen compatibility subset. The audited
sing-box v1.12.0 source accepts versions 1, 2 and 3; the engine is not described
as supporting only version 1. An input declaring version 5 is rejected by this
profile with `UNSUPPORTED_SCHEMA_VERSION`. That is a statement about this fixed
profile, not the newest sing-box version or all future schemas. Primary evidence:
[v1.12.0 rule-set parser](https://raw.githubusercontent.com/SagerNet/sing-box/v1.12.0/option/rule_set.go),
retrieved 2026-10-18. No current/latest release claim is made.

## Expected and observed integration behavior

All following expectations were observed in the recorded cloud run.

| Test / trajectory | Exact expectation and observed outcome |
|---|---|
| `test_all_output_profiles_exact_readback_and_independent_restoration` | For each of the four outputs above, conversion bytes equal the frozen complete output. Planning leaves the old target unchanged. Apply invokes the scoped authorizer twice and writes exactly the expected bytes. Backup `original.bin` equals the complete original; `applied.json` equals the returned receipt. Independently approved rollback restores the complete original bytes and mode/owner/group, produces a restored receipt/journal and retains the original backup. Source and neighbor bytes/modes remain identical. |
| `test_conversion_rejections_never_reach_transaction_plan` | Suffix-to-exact and a supported-plus-ASN mixture fail with `UNREPRESENTABLE_MATCH`; schema 5 fails with `UNSUPPORTED_SCHEMA_VERSION`; a classical entry carrying a third action token fails with `UNREPRESENTABLE_ACTION`; domain plus port fails with `UNHANDLED_CONDITION`. In every case the transaction planner is never called, the original target remains unchanged, and the backup directory stays empty. |
| `test_changed_source_digest_rejects_before_output_plan` | The synthetic source changes from api.example.invalid to new.example.invalid while the declared digest remains the original digest. Conversion fails with `SOURCE_DIGEST_MISMATCH`; no plan or backup is created, the target stays original, and the deliberately changed source is not overwritten. |
| `test_missing_or_wrong_apply_authorization_preserves_target` | Missing authorizer produces `AUTHORIZATION_REQUIRED`; a wrong digest produces `AUTHORIZATION_DENIED`. Neither changes the target nor creates a backup batch. |
| `test_target_and_backup_scope_cannot_reuse_conversion_approval` | A different target reference produces `TARGET_MISMATCH`; changing the backup destination invalidates the digest and produces `AUTHORIZATION_DENIED`. Both backup directories and the target remain unchanged. |
| `test_cancel_at_precommit_preserves_target_and_retains_backup` | The first approval succeeds and the second is denied. This is precommit authorization cancellation, not the converter cancellation callback. The target stays original, `original.bin` and `prepared.json` remain, `applied.json` is absent, and no staging file remains. |
| `test_stale_content_or_identity_blocks_converted_write` | A later content edit, or replacing the target with a new inode containing the same original bytes/mode, produces `STALE_FILE`. The newer target remains untouched and no backup batch is created. |
| `test_rollback_requires_a_distinct_receipt_bound_authorization` | Reusing the apply authorizer for rollback produces `AUTHORIZATION_DENIED` and leaves the converted bytes intact. A separate receipt-bound rollback then restores the exact original. |
| `test_rollback_conflict_preserves_later_edit_and_original_backup` | After apply, a later edit makes verify return fail. Rollback produces `ROLLBACK_CONFLICT`, preserves that edit and retains the original backup. |
| `test_postreplace_journal_failure_requires_reconciliation_not_fake_rollback` | A fault injected specifically while writing `applied.json` raises `IO_FAILURE` with a recovery ID after the converted bytes have already replaced the target. Original bytes and the actual prepared record remain. Rollback of that unmodified prepared record fails with `RECOVERY_REQUIRES_RECONCILIATION`; no fake applied receipt or successful restoration is asserted. |

Successful `transactions.verify` returns the complete expected object:

```json
{"check_status":"pass","verification_scope":"exact_file_bytes_only","application_effect":"not_tested","network_effect":"not_tested"}
```

The source-change test establishes a mismatch before conversion. It does not
claim continuous freshness of an external mutable source file after the caller
supplies immutable bytes. The normal conversion API has no source-file path or
file-watching responsibility.

## Concrete remaining recovery gap

Post-replace journal failure is not equivalent to a precommit failure. The target
can contain new output even though apply raises. The original backup and a
prepared-only journal are retained, but there is currently no public operation
that reconciles that state into a safely restorable applied receipt.

`transactions.rollback` validates the receipt through `_recovery`, which rejects
state `prepared`. `recovery_cli.bind_receipt` also invokes that validation and
requires the scoped `applied.json` path. A caller must not manufacture an applied
snapshot, relabel a prepared record, or blindly restore over a later edit.

This is a future bounded recovery design/implementation obligation. No transaction
runtime was changed in this increment. The demonstrated successful applied-receipt
restore path is useful R sub-evidence; it does not close the complete R layer or
all failure recovery for ENV-T40.

## Next action-preserving main-rule slice

The existing `rule_source_import` accepts one selected group, rejects conflicting
source actions, and rejects duplicate selectors. Its `binding_components` returns
one group plus predicate records, not an ordered mixed-policy intermediate form.
It should not be repurposed to silently collapse different actions.

A separate bounded main-rule profile would need per-record typed actions, source
order and duplicate/overlap preservation, explicit outbound mapping and reserved
name-collision checks. Predicate-only exports cannot discard those actions.
Reject/drop/continue behavior, additional conditions and unknown modifiers must
remain explicit errors until supported. No-match means defer to the enclosing
configuration. Main-policy priority and actual outbound execution would need
their own evidence; they are not proved by the artifact transaction tests here.

## Reproduction and snapshot pins

Recorded environment: Linux 6.18.55, x86_64, Python 3.12.14. These commands were
run in the ninth source tree with bytecode cache writing disabled:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_rule_conversion_transaction.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests python -m unittest test_rule_conversion_transaction test_transactions -v
```

Results: the new integration file passed 10 tests in 0.017 seconds; the composed
run with unchanged transaction tests passed 52 tests in 0.042 seconds, no skips
in that Linux run. Other-platform results and full aggregate results are separate
receipts. Existing transaction tests include mocked platform behavior and a
synthetic temporary-file xattr refusal check; these are not user-device acceptance.

| Reviewed file | SHA-256 |
|---|---|
| `skills/claude-guardian/scripts/rule_format_conversion.py` | `879b392f2228b6eb582af45c22b56b3aef088b087686f2ef3b189242476a02b1` |
| `skills/claude-guardian/scripts/rule_source_import.py` | `d6c48b54721001516435f7b9b990ade8d53eb2d1a828a4900a6828ff6291d6e7` |
| `skills/claude-guardian/scripts/transactions.py` | `71fe13787e953f91b727d127eacc04e095d02cf1cab8c71dc0f6964dc278ebf3` |
| `skills/claude-guardian/scripts/recovery_cli.py` | `06fcd1cf994e8dfa374740a561190748ff9f6257fd9107634e5cdf061d8964e2` |
| `tests/test_rule_conversion_transaction.py` | `8cd9695c76a5aa99a8ddc951ad66275d6cda95bc31c94c03a09b65f06cc59a00` |
| `tests/test_transactions.py` | `2f8dc38138319f65627ad2e54863cdddeaaba67e28c0280e589b2e1da9edb51c` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |

If an underlying pinned file changes, replay and refresh this receipt before
using it as evidence. No original acceptance condition or ledger status is
changed by this page.
