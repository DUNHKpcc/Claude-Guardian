# ENV-T40: complete bounded conversion and controlled restoration evidence

Date: 2026-10-18 UTC. This evidence joins the existing format/policy logic with
actual POSIX writes and restoration on dedicated synthetic temporary artifacts.
It requests independent whole-case review under the original **L + R** layers;
only the batch owner may integrate acceptance afterward. No production runtime,
CLI, native-admission gate or original requirement was changed by this subset.

## Unchanged original condition

| ID | Scenario | Required behavior | Layers |
|---|---|---|---|
| ENV-T40 | 纯域名/规则提供方/主规则/JSON 格式转换 | 不可表达的 ASN/匹配/动作语义明确报错，不静默丢失 | L + R |

D-ENV v0.3 §12.1 supplies the original scenario/requirement; tracker §8 defines
L as logic/dialogue/fixtures and R as controlled write and restoration. This row
has no N or X layer. Its cloud-only scheduling does not relax either original
layer, and test totals do not substitute for the clause review below.

The supported grammars are deliberate subsets. An unsupported feature is an
explicit error, including unsupported source/target profile combinations. The
requirement does not promise all features of every engine or every format pair.
This page does not promote conditional fragment semantics into live engine
compatibility, effective routing or user-device acceptance.

## Original-clause review

| Original clause | Executable evidence and observed result |
|---|---|
| 纯域名 | `test_rule_format_conversion` freezes exact-domain-lines/0.1 conversions and exact-host-only semantics; suffix-to-exact output rejects. Existing `test_rule_conversion_transaction.test_all_output_profiles_exact_readback_and_independent_restoration` writes and restores the exact plain output `example.invalid` plus LF. |
| 规则提供方 | Explicit Mihomo 1.19.32 domain-provider and classical-provider profiles preserve bare exact versus `+.` inclusive suffix, and DOMAIN versus DOMAIN-SUFFIX. Existing controlled transaction tests write/read back/restore both provider outputs. Unsupported `.`/`*.` forms, other match types and action tokens fail rather than being collapsed. |
| 主规则 | New `test_both_directions_exact_readback_semantics_and_independent_rollback` and `test_ordered_occurrence_provenance_is_not_lost_at_write_boundary` preserve main YAML output, mixed ordinary policy labels, duplicate and shadowed occurrences, complete output and per-occurrence provenance through write/readback/restoration. The output is a rules-only fragment, not a full deployed configuration. |
| JSON | Existing actionless source-rule-set JSON v1 has frozen output and R coverage. New action-bearing sing-box 1.12.0 route-array output has frozen output and R coverage in both directions. Source-key/list-order OR expansion is contiguous and retains the same action; it does not invent a policy-priority interpretation for actionless sets. |
| 不可表达的 ASN | Existing provider IP-ASN rejection and new main-rule IP-ASN rejection are explicit `UNREPRESENTABLE_MATCH`. The new mixed supported/unsupported matrix places the unsupported entry both before and after a valid record; planner, writer and authorizer are never called and target/backups remain unchanged. |
| 匹配语义 | Existing exact/suffix apex, child and label-boundary positives/negatives and loss rejection are retained. The new oracle parses actual written target bytes and compares canonical first-match label selection with the source. Broad-before-exact reversal changes the expected selected label; suffix apex survives and concatenated/hyphenated/appended-suffix lookalikes do not match. Extra port/network/logical/default-valued conditions reject rather than being extracted away. |
| 动作语义 | The actionless converter still refuses action-bearing material with `UNREPRESENTABLE_ACTION` before planning. The policy converter requires explicit bijective maps covering all used ordinary labels and declared terminal behavior for both TCP and UDP. Unknown finality, TCP-only finality, reject/drop, incomplete/ambiguous mappings and all seven exact reserved labels reject. There is no guessed DIRECT, deny, continue or fallback conversion. |
| 明确报错，不静默丢失 | Complete source and output bytes/hashes, source references/index/path/line, occurrence order and typed action maps survive privately. Unsupported batches fail atomically with asserted fixed codes. No silent filtering, sorting or deduplication is introduced. Public preview is asserted as a complete fixed object; raw domains/actions/metadata are not exported. |
| L + R | New ordered outputs pass actual temporary-file normal apply/readback/independent rollback and prepared-v2 reconciliation/restore after post-replace journal failure. Source and unrelated neighbor contents/modes remain unchanged; supported original target bytes/mode/owner/group are restored. Stale targets, bad scopes, cancellation, changed evidence and rollback conflicts stop at their actual stages. |

Supporting retained suites were freshly rerun on this tree, rather than accepted
solely because an older page contains a test count or source hash. The original
218 rows and their layers are untouched.

## Fixed versions, grammar and provenance

The pure APIs remain separate:

- `rule_format_conversion.convert_rule_format`: exact-domain-lines/0.1;
  Mihomo 1.19.32 provider-domain-yaml / provider-classical-yaml; sing-box 1.12.0
  source-rule-set-json-v1. These are actionless predicate collections
- `rule_policy_conversion.convert_policy_rules`: Mihomo 1.19.32 main-rules-yaml
  ↔ sing-box 1.12.0 route-rules-json, two cross directions only. JSON is an array
  intended for route.rules; YAML contains only rules. Neither is a full config

Fixed versions are compatibility targets, not latest or installed-version claims.
Both converters require canonical lowercase ASCII configured hosts; uppercase,
root-dot, Unicode, wildcard/leading-dot and ambiguous numeric-only inputs reject.
Lowercase A-labels remain opaque. The canonical oracle does not classify unknown
inbound normalization as equivalent or as a safe no-match.

Exact matches select one host; suffixes include apex plus dot-separated
descendants. Source bindings retain computed SHA-256, source/date/version/client/
feature/purpose declarations separately from action intent. Such declarations do
not prove authenticity, freshness, independence or native capabilities. Ordinary
outbound maps have explicit source/target kind and terminal-for-TCP-and-UDP
finality on both sides. Actual adapter/group/member behavior remains
`declared_unverified`. Exact reserved exclusions are DIRECT, REJECT, REJECT-DROP,
COMPATIBLE, PASS, PASS-RULE and GLOBAL; this is not a substring blacklist.

Both no-match contracts remain `defer_to_enclosing_configuration`; the converter
never inserts MATCH or a final action. It does not establish the enclosing
configuration's fallback. The current product's separately scoped address-family
policy cannot be inferred from this TCP/UDP label-selection model.

The existing pinned semantic review remains applicable: Mihomo v1.19.32 commit
`88dcbf7f1614a67c3b36b848ee3592dfa92ada36`, sing-box v1.12.0 and its pinned sing
domain matcher. Primary links and full model limits are in
[ordered-policy evidence](rebuild-policy-conversion.md) and
[predicate evidence](rebuild-rule-format-conversion.md). This test-only batch did
not re-fetch sources, install engines or execute native configuration checks.

## Concrete ordered fixtures and complete outputs

Both original target fixtures contain `original standalone synthetic artifact`
plus LF, mode 0640, owned by the executing effective user/group. The independent
source and neighbor files are mode 0600; private backup directories are mode 0700.
All lie in a dedicated temporary root. No real configuration is selected.

### Mihomo main rules → sing-box route array

Source bytes (final LF included):

```yaml
rules:
  - DOMAIN-SUFFIX,example.invalid,egress-a
  - DOMAIN,api.example.invalid,egress-b
  - DOMAIN,api.example.invalid,egress-b
```

Map egress-a → route-a and egress-b → route-b. Exact expected output, final LF:

```json
[{"domain_suffix":["example.invalid"],"action":"route","outbound":"route-a"},{"domain":["api.example.invalid"],"action":"route","outbound":"route-b"},{"domain":["api.example.invalid"],"action":"route","outbound":"route-b"}]
```

The broad first rule selects route-a for example.invalid, api.example.invalid
and deep.api.example.invalid under the model. The duplicate exact rules remain
present even though shadowed. Reversing the exact/broad order selects route-b for
api.example.invalid. No-match candidates defer; they are not rewritten to DIRECT.

### sing-box route array → Mihomo main rules

Source bytes, final LF:

```json
[{"domain":["api.example.invalid","api.example.invalid"],"domain_suffix":["example.invalid"],"action":"route","outbound":"route-a"},{"domain":["other.invalid"],"action":"route","outbound":"route-b"}]
```

Map route-a → egress-a and route-b → egress-b. Exact output, final LF:

```yaml
rules:
  - 'DOMAIN,api.example.invalid,egress-a'
  - 'DOMAIN,api.example.invalid,egress-a'
  - 'DOMAIN-SUFFIX,example.invalid,egress-a'
  - 'DOMAIN,other.invalid,egress-b'
```

Output occurrence mapping is `(0,0,0), (1,0,1), (2,0,2), (3,1,0)`, where each
triple is output index, source rule index, predicate index. Paths retain the JSON
source field/list position; no guessed JSON line is recorded. Both duplicate
exact predicates remain. An independently parsed source/target oracle checks
actual saved bytes, separately from the complete-byte expectation.

## APIs and actual authorization/recovery sequence

Each successful test calls `convert_policy_rules`, keeps its immutable private
material, checks source/output digests and complete expected output, and then
calls `transactions.plan(existing_path, output_bytes, target_ref)`. The transaction
plan's output hash equals the private conversion output hash. Transaction plans
bind actual destination/output bytes, not the truth of source declarations.
Private conversion provenance is retained alongside the plan; no new provenance
attestation or production envelope is claimed.

Normal apply uses `transactions.apply`, `verify` and independently authorized
`rollback`. Apply's two callbacks bind the exact operation, target reference and
`digest({'plan': plan, 'backup_directory': backup_directory})`. Rollback's two
callbacks bind `rollback`, target and `digest(receipt)`. Reusing apply authority
for rollback is denied and leaves converted bytes intact. Complete verify output:

```json
{"check_status":"pass","verification_scope":"exact_file_bytes_only","application_effect":"not_tested","network_effect":"not_tested"}
```

After injected `applied.json` failure, apply raises IO_FAILURE even though target
replacement occurred. Original.bin and the actual v2 prepared.json remain;
applied.json is absent. Ordinary rollback refuses the prepared record.
`reconcile` receives explicit receipt_path, target_ref, target_path and backup_batch
and observes `prepared_candidate_observed`. `restore_prepared` needs two fresh
callbacks bound to operation, target and
`digest({'recovery_digest': digest(recovery), 'observation': observation})`.
Prior apply authority cannot restore. No applied snapshot is fabricated.

After restoration, original bytes/mode/owner/group are checked. Backup/prepared/
restoration journals are retained. Reconciliation describes current observation,
not historical success. A restoration-journal failure is still IO_FAILURE even
when original bytes are now present; the retained restore witness reconciles as
`restored_candidate_observed` and the stale original restoration cannot replay.

The fixture controls its temporary directory and excludes writers except explicit
conflict injections. Its synthetic callbacks establish only that test boundary.
An actual host still needs genuine scope authorization and writer exclusion;
`exclusive_access=True` and an always-true callback cannot supply those facts.
There is no general writer or production repair adapter in this slice.

## Failure matrix actually exercised

- ASN, CIDR, keyword, MATCH and unsupported modifiers/actions appear before and
  after a valid source record: exact fixed error, zero planner/writer/approval,
  unchanged destination/source/neighbor, no backup creation
- JSON extra port/network/logical/default-valued fields, reject/drop, malformed or
  escaped duplicate keys and noncanonical hosts reject the entire batch
- All seven literal reserved labels on both mapping sides, unknown/TCP-only
  finality, nonordinary action kind, ambiguous and incomplete maps reject
- Action-bearing YAML/JSON cannot pass through the predicate exporter and lose
  actions on the way to a transaction
- Source SHA mismatch, duplicate source references, cancelled/nonboolean callback
  and expired converter budget fail before planning. This binds immutable supplied
  bytes; it does not watch an external source file for later changes
- Changed target bytes/mode/same-bytes inode or parent invalidate a plan. Missing,
  wrong or nonboolean authority, wrong target/backup destination and plan expiry
  preserve the destination and create no batch
- Cancellation at the second apply callback leaves original target bytes and the
  actual private prepared/original backup, without an applied receipt or stage
- Later edit after apply yields failed verify and ROLLBACK_CONFLICT; later content
  and original backup survive
- Target replacement after reconciliation rejects stale observation before any
  restore approval, even when replacement bytes are identical
- Target, prepared receipt, backup or batch-permission changes during the second
  restore approval stop restoration without overwriting the later state
- Cancellation at each restoration approval preserves candidate and original
  backup, with no restore witness/rollback completion created
- Post-restoration completion-journal failure retains a read-only usable witness,
  reports failure and cannot silently replay the old operation
- Complete conversion and exact-file preview objects are asserted; production
  preflight still rejects candidate_kind=policy-conversion before request reads,
  and `_native_session` remains NATIVE_REPAIR_ADAPTER_UNAVAILABLE

All new tests patch socket construction/connections, DNS getaddrinfo/gethostbyname,
subprocess creation and os.system to fail on use. Each sentinel is asserted
uncalled. File operations are intentionally real and limited to fixture-owned
artifacts; production code has no file-scan path introduced by these tests.

## Fresh runs and retained receipts

Linux cloud run, current Python. `PYTHONDONTWRITEBYTECODE=1` was used. Focused:

```sh
python -m unittest discover -s tests -p test_ordered_policy_transaction.py -v
```

18 tests passed in 0.130 seconds. Combined:

```sh
PYTHONPATH=tests python -m unittest test_rule_format_conversion test_rule_policy_conversion test_rule_conversion_transaction test_ordered_policy_transaction test_transactions test_prepared_recovery test_prepared_recovery_cli -v
```

200 tests passed, no skips, in 8.525 seconds: 47 predicate, 26 ordered, 10 existing
predicate transaction, 18 new ordered transaction, 42 transaction, 39 prepared
recovery and 18 prepared-recovery CLI. Counts overlap other focused runs and must
not be added twice. All assertions, including the original tests, remain intact.

A four-test early checkpoint passed before expanding the matrix. During test-file
assembly an indentation error caused the first matrix import to fail; that log
is retained. Fixing placement in the new test file yielded the 18-test passing
run without changing runtime code or weakening an assertion. This is new
composition evidence for existing behavior, not a fabricated failing-first
production regression.

The independently repeatable synthetic replay is retained as
`guardian-rebuild-backups/env40-seventeenth-replay.py`, invoked with the reviewed
source-tree path. It performs both normal and prepared recovery directions and
prints bounded synthetic observations. Output SHA-256:
`c1647c67598035d373dc6f9b92d89d34fc2338f3c89075f4a0c1a080931c0041`.
Focused/combined logs, immutable checkpoint copies, final owned patch/manifest
and receipt are retained under `env40-seventeenth-*`. Python 3.10 grammar and
current-interpreter byte compilation pass; this is not a Python 3.10 runtime run.
Full aggregate, package and CI results belong to the batch's separate final
validation receipt and are not invented here.

## Scope limits, eligibility and rollback

The complete original conversion/loss-refusal condition now has combined L and
controlled POSIX artifact R evidence for independent review. The parent alone
updates case acceptance after that review. Windows skips cannot establish Windows
R; Linux does not certify macOS, installed engines or user-device recovery.

D-ENV §3.4 exact target/digest/expiry/backup/conflict-safe recovery is exercised in
this temporary-artifact scope. §5.7 keeps source dependency facts separate from
selected outbound intent. §5.3, §5.6, §5.8 and D07 additionally require full actual
configuration context, protected organization/recovery/local rules, version and
GUI ownership, stable merge/persistence, native validation, live first-match and
egress evidence, and subscription-refresh verification for deployment. Those
remain unproved; no standalone fragment overwrites an enclosing config here.
They are not silently added as N/X layers to the unchanged ENV-T40 row, nor closed
by this evidence. Source/mapping claims remain caller declarations, and no-match
fallback outside the fragment remains unknown.

The ninth historical evidence's prepared-recovery limitation is superseded only
by current v2 recovery, as recorded in the tenth recovery evidence. Old prepared
receipts are not upgraded or made restorable. Process faults/journal failures are
not sudden-power-loss certification. Inode/timestamps are not restored; supported
bytes/mode/owner/group are. Unsupported metadata, unsafe paths, foreign ownership
and other primitive restrictions remain unchanged.

Rollback of this two-file increment removes the new test and this evidence page;
it does not edit runtime or any retained private recovery data. Any later parent
ledger acceptance is independently reversible if relevant source/pin review fails.

## Current underlying pins

Pins exclude this page, the ledger and other self-referential receipt cycles.
If a pinned implementation or test changes, rerun and review the affected clauses
rather than merely substituting hashes.

| File | SHA-256 |
|---|---|
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `docs/implementation-tracker.md` | `8056f8d999a73a66dcdb7960dd724cd9e0c7404d769b00650e6936f21703fd50` |
| `skills/claude-guardian/scripts/rule_format_conversion.py` | `879b392f2228b6eb582af45c22b56b3aef088b087686f2ef3b189242476a02b1` |
| `skills/claude-guardian/scripts/rule_policy_conversion.py` | `88cd726eb9d67586c40938835f52fe43f48dcf2174cc96e8cf04faddb3740cdb` |
| `skills/claude-guardian/scripts/rule_source_import.py` | `d6c48b54721001516435f7b9b990ade8d53eb2d1a828a4900a6828ff6291d6e7` |
| `skills/claude-guardian/scripts/config_edit_plan.py` | `d50499f5a92508a9a20dd7e6193f7b2a320bba06bc8fd8ba5eb93ec2b39259dd` |
| `skills/claude-guardian/scripts/repair_cli.py` | `36e54b3486c85692e6f86df30a7fdc90ee1233d178d4302202fbab8fd81d59bb` |
| `skills/claude-guardian/scripts/repair_execution.py` | `ca7540482cc3059f47f365b80b1cac27dae9ab32e30269537a744582c2cb6554` |
| `skills/claude-guardian/scripts/transactions.py` | `53c1fa7a3f2e2fff2737ba3dbe96d0dbe748bfdbbed73b2a7d15f05c723190cd` |
| `skills/claude-guardian/scripts/recovery_cli.py` | `0355e39cd8375f5044431d98f9949dddce05b2f07b30334f92fed3225621b732` |
| `tests/test_rule_format_conversion.py` | `449ea5764d8c1ae1e9cf28edfab0c0c151d3eef9b638a3db7239f13824bf83db` |
| `tests/test_rule_policy_conversion.py` | `0d763f0901c9229f2265eadf282fbe647faf537ec90621e4c8436b620b2f2723` |
| `tests/test_rule_conversion_transaction.py` | `8cd9695c76a5aa99a8ddc951ad66275d6cda95bc31c94c03a09b65f06cc59a00` |
| `tests/test_ordered_policy_transaction.py` | `de654e1d07bf92d9db277d8600a6badb5fcc7ea04bd26d6fc3505df155ca6ae8` |
| `tests/test_transactions.py` | `2f8dc38138319f65627ad2e54863cdddeaaba67e28c0280e589b2e1da9edb51c` |
| `tests/test_prepared_recovery.py` | `b5bdb007d70cd3fa8de8d629ac3b67f448244a2217661f61e0f18fcdd447ccef` |
| `tests/test_prepared_recovery_cli.py` | `15f81b93bad9442417602691e4db9b69d34b562e3e888d739d9bebd4e2945e1d` |
