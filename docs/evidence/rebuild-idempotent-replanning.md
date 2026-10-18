# Bounded idempotent replanning evidence

Date: 2026-10-18. Scope: offline supplied snapshots and synthetic POSIX files.
This is an ENV-T60 configuration-replanning subgap, not full original acceptance.
No real proxy configuration, native app, account, network endpoint or Claude
contact was used. Earlier reconstruction trees were read only.

## Original requirement and clause review

D-ENV v0.3 §5.8 requires idempotency checks for duplicate rules, duplicate group
names, repeated application and references after subscription refresh. It also
preserves global MATCH, company DNS, subscription tokens and original nodes.
This increment preserves unrelated bytes and existing guards within the two
already-supported grammars. It does not implement GUI application or
subscription-refresh validation.

Original ENV-T60 is: **同样任务再次运行且无环境变化** → **复用有效事实；变更幂等，已知问项不重复，未测结果不升级为通过**.
The implementation tracker assigns **L + R**. Clause-by-clause:

- **复用有效事实**: the full request is rebound to fresh supplied revisions and
  revalidated. This is not evidence that the Agent reuses every valid environment
  fact. Full fact-cache/session behavior is outside this change.
- **变更幂等**: exact supported repeats now produce unchanged candidate bytes and
  no action plan; mixed merge edits change only incorrect selected tokens.
  This establishes bounded compiler/CLI behavior. Actual native repeat application,
  GUI writeback and subscription refresh remain untested here.
- **已知问项不重复**: this increment does not change interview/question behavior
  and supplies no new evidence for this clause.
- **未测结果不升级为通过**: both repeat and mixed output retain native blockers,
  `apply_supported=false`, and unrun reload/routing/native results. A snapshot
  match is never labeled applied, verified or an unchanged live environment.

Therefore original ENV-T60 **L + R remains incomplete**. No acceptance ledger or
accepted-case source pins are changed by this increment.

Related constraints retained: ENV-T59 (L + N + R), covering organizational or
rescue-path conflicts; ENV-T61 (L + C), allowing conditional planning without
current-device write approval; ENV-T67 (L + N + R), invalidating old plans when
configuration, version or protected scope changes. The offline regressions below
are supporting evidence only for their exercised guards. ENV-T40's broader format
conversion requirement is not implemented or accepted by this change.

## Exact old counterexamples and fresh results

The same standalone reproducer below was run against the frozen fifth tree and
the sixth tree. It imports synthetic fixtures, creates no repository/configuration
files and performs no I/O through either compiler. The prepend example first
compiles an empty list, then supplies its exact candidate with freshly rebound
revisions. The mixed example supplies one already-correct rule and one rule still
using the old policy, with current expected rule values and hashes.

Frozen fifth output:

```json
{"case": "exact_repeat_prepend", "error": "NONEMPTY_PREPEND_UNSUPPORTED"}
{"case": "mixed_merge_policy", "error": "NO_CHANGE"}
```

Sixth output:

```json
{"apply_supported": false, "case": "exact_repeat_prepend", "changed_rules": 0, "matched_rules": 1, "native_acceptance": "not_run", "same_bytes": true, "status": "no_change_in_supplied_snapshot"}
{"apply_supported": false, "case": "mixed_merge_policy", "changed_rules": 1, "matched_rules": 1, "native_acceptance": "not_run", "same_bytes": false, "status": "candidate_only_blocked"}
```

Save this as a temporary script and pass the repository root as its one argument
with `PYTHONDONTWRITEBYTECODE=1 python -B /tmp/reproduce.py /path/to/repository`:

```python
from copy import deepcopy
import hashlib
import json
import sys
from pathlib import Path
repo = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(repo / 'tests'), str(repo / 'skills/claude-guardian/scripts')]
import config_edit_plan as merge
import rules_extension_plan as prepend
from test_config_edit_plan import RAW as MERGE_RAW, inputs as merge_inputs
from test_rules_extension_plan import RAW, BASE, inputs

def result(label, compile):
    try:
        candidate = compile()
        public = candidate.preview()
        private = candidate.private_material()
        print(json.dumps({'case': label, 'status': public['status'],
              'changed_rules': public.get('changed_rules', public.get('added_rules')),
              'matched_rules': public.get('matched_rules'),
              'same_bytes': private['candidate_bytes'] == private['original_bytes'],
              'apply_supported': public['apply_supported'],
              'native_acceptance': public['native_acceptance']}, sort_keys=True))
    except (merge.EditPlanError, prepend.RulesPlanError) as error:
        print(json.dumps({'case': label, 'error': str(error)}, sort_keys=True))

request, binding = inputs()
current = prepend.compile_rules_extension(RAW, BASE, request, binding).private_material()['candidate_bytes']
request['revisions']['extension'] = hashlib.sha256(current).hexdigest()
request['current_revisions'] = deepcopy(request['revisions'])
result('exact_repeat_prepend', lambda: prepend.compile_rules_extension(current, BASE, request, binding))

current = MERGE_RAW.replace(b'DOMAIN,example.test,Old', b'DOMAIN,example.test,approved-group')
request, binding = merge_inputs(current)
request['intent']['rule_refs'].append('rule-b')
binding['rules']['rule-a']['expected'] = 'DOMAIN,example.test,approved-group'
binding['rules']['rule-b'] = {'index': 1, 'expected': 'DOMAIN-SUFFIX,example.org,Old'}
result('mixed_merge_policy', lambda: merge.compile_edit_plan(current, request, binding))
```

These outputs establish actual old/new compiler behavior. They do not claim that
an earlier Agent double-applied a real configuration or that a native repair ran.

## API and execution boundaries

`config_edit_plan.compile_edit_plan(raw, request, binding)` validates every selected
rule before returning. Already-correct selections add immutable `matched_rule_refs`
and no span; incorrect selections add `changed_rule_refs` and exact policy-token
spans. Both tuples follow semantic request order. Invalid selections in either
order still reject the entire request without mutating input objects.

`rules_extension_plan.compile_rules_extension(raw, base, request, binding)` accepts
an exact ordered repeat only within the existing literal single-line prepend-list
grammar. The whole list must equal all requested rule strings. Original literal
formatting is retained. Partial, reordered, duplicated or unrelated nonempty lists
remain unsupported; no broad list merger or converter was added. Base/group,
protected overlap and duplicate-selector checks run even for the repeat.

An unchanged private candidate contains identical before/after bytes and hashes,
empty edit/addition tuples and (for prepend) `byte_insertion=None`. Public previews
omit private values and report `no_change_in_supplied_snapshot`, matching counts,
`authorization=not_required_for_snapshot_observation`, and no
`ACTION_AUTHORIZATION_PENDING`. Native/priority blockers remain. Changed candidates
retain their existing pending-action authorization contract.

`repair_cli.preflight(...)` branches before `transactions.plan` for identical
bytes. Its `PrivatePreflight._plan` is `None`, not an executable empty action.
Before return, every public/private no-change presentation and the final CLI
print, it rechecks the full request digest, target snapshot and parent identity,
all explicitly supplied base/metadata snapshots, original cancellation callback
and original monotonic deadline. It does not discover paths or reset the budget.
These bounded reads are observations, not atomic writer exclusion.

No-change `plan`, `diff` and `preflight` output cannot carry an action ID, plan or
retained-artifact digest, recovery receipt or applied status. Even supplied
`--plan-file` and `--backup-directory` arguments cause no destination access/write
on this branch. `repair_execution.retain(...)` directly rejects a no-change
object with `NO_CHANGE_TO_RETAIN` before validating/opening either destination.
No existing artifact is removed or refreshed.

Mixed private review lists only real changes, while retention continues binding
the full original request digest and all source/target identities. Dynamic checks
for changed plans remain in force. A retained no-op document is rejected with
`NO_CHANGE_TO_EXECUTE` before native admission; an execute-time recompile returning
`_plan=None` fails explicitly with `STALE_FILE`, rather than indexing None or
fabricating an applied receipt. `transactions.py` was not changed.

The two new no-change refusal codes are explicitly classified by
`agent_remediation.select`. They stop the current repair with a `no-change`
action and no alternate mutation fallback; they are not missing-adapter errors.
Independent `INCIDENT_PRIORITY` triage remains visible in either code order.
Cancellation still wins, and actual permission/stale/recovery failures retain
prerequisite resolution. Imported findings still cannot establish native success,
write permission or an environment pass. The emitted-code coverage test was
preserved unchanged and caught the initial missing classification during review.

## Fresh regression matrix

All tests use supplied synthetic bytes or dedicated private temporary directories.
The synthetic adapter exists only in tests; it is not production native admission.

| Boundary | Specific regression | Verified outcome |
| --- | --- | --- |
| Merge repeat | `test_fresh_replanning_is_byte_identical_private_and_io_free` | Fresh bindings yield identical bytes/hash and empty spans; old request stays stale; no I/O/private export |
| Mixed order | `test_mixed_matches_and_edits_preserve_order_and_exact_spans` | Both selection orders retain matches and edit only the incorrect token |
| Invalid beside match | `test_matching_selection_cannot_hide_later_or_earlier_invalid_selection` | Duplicate index, stale expected value, invalid domain and shadowed rule reject in both orders |
| Match guards | `test_matching_rules_retain_duplicate_shadow_group_and_syntax_guards` | Duplicate selectors/groups, missing group, shadowing and unsupported syntax still fail |
| Prepend exact repeat | `test_exact_repeat_preserves_bytes_hashes_blockers_and_private_matches`, `test_exact_single_line_repeat_keeps_original_literal_formatting` | Identical bytes including BOM/Unicode/CRLF/comments, no addition or insertion, blockers retained |
| No broad merger | `test_nonempty_prepend_does_not_become_a_general_merge` | Partial/reordered/unrelated/duplicate/multiline prepend remains unsupported |
| Prepend validation | `test_exact_repeat_retains_base_group_protected_and_duplicate_guards`, `test_repeat_match_cannot_skip_other_invalid_or_overlapping_selection` | Base/group/protected/duplicate/invalid conditions reject, including both selection orders |
| No transaction/artifact | `test_matching_snapshot_has_no_transaction_plan_or_receipt`, `test_matching_cli_plan_does_not_access_or_create_artifact_destinations`, `test_exact_repeat_cli_is_an_observation_without_artifact_or_receipt` | No tx.plan/apply, action ID, retained digest, receipt or destination creation |
| Fresh presentation | `test_matching_report_rechecks_changed_request_and_target`, `test_exact_repeat_review_rechecks_every_supporting_source_identity` | Changed request, bytes, inode, parent, base, app metadata or profile index reject cached output |
| Mid-work change/budget | `test_matching_preflight_rechecks_target_after_compilation`, `test_exact_repeat_source_change_during_compilation_still_blocks`, `test_matching_report_keeps_original_cancel_and_deadline`, `test_no_change_cli_rechecks_before_printing_cached_report` | No stale no-change result after compilation/presentation changes, cancellation or expiry |
| Direct retain | `test_no_change_retention_rejected_before_any_destination_access`, `test_exact_repeat_retention_is_rejected_without_destination_access` | Fixed refusal before destination path validation/open/write |
| Mixed retention | `test_mixed_plan_retains_full_request_and_only_changed_rule` | Full request digest retained; only real edit reviewed/written by synthetic transport; route stays not_run |
| Execute no-op | `test_old_retained_plan_cannot_become_no_change_success`, `test_noop_retained_document_rejected_before_native_admission` | Explicit stale/no-op refusal, no TypeError, native admission or fabricated receipt |
| Agent integration | `test_no_change_transport_codes_stop_without_fallback_or_native_claims`, `test_no_change_does_not_hide_cancellation_or_genuine_prerequisite_failure`, `test_no_change_preserves_independent_incident_triage_in_both_orders` | Both codes stop repair without alternate mutation; structured diagnostics, independent incident triage and genuine guard precedence are preserved |
| Existing changed-plan invariants | Existing retention expiry/cancel, same-byte source identity, conflict recovery, final-commit and post-write recovery tests | Original assertions remain green |

Focused command:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests:skills/claude-guardian/scripts \
python -B -m unittest test_config_edit_plan test_rules_extension_plan \
  test_repair_cli test_rules_repair_cli test_repair_execution test_agent_remediation -v
```

Result: **148 tests passed**: 28 merge compiler, 23 prepend compiler, 21 merge
CLI, 16 rules CLI, 28 execution and 32 Agent selector. The frozen fifth versions
contain 90 tests in the first five suites; 26 regressions were added there, plus
three selector integration regressions. The prior assertion that a selected
no-op must reject was replaced with stronger unchanged-byte/no-action and guard
assertions; unrelated negative assertions were retained. This is a Linux/POSIX
synthetic result, not macOS/Windows or live-app acceptance.

## Aggregate and package verification

After the selector/incident integration fix, the full command
`PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -v`
discovered **1,207 tests: 1,199 passed, 8 platform-specific skips**. Skips are not
native passes. `python -m compileall -q skills/claude-guardian/scripts`,
`node tests/webrtc-lifecycle.cjs` (8 synthetic cases),
`node tests/dashboard-interaction-protocol.cjs` and `git diff --check` passed.
No browser was executed by either Node suite.

Two fresh `python tools/package_skill.py --output <temporary-zip>` builds were
byte-identical, SHA-256
`ac389186fc8a45b99e5d35da090441bbb15c04f52d49e6329543ea1360813f57`.
An extracted-package synthetic selector smoke confirmed that
`NO_CHANGE_TO_EXECUTE` plus `INCIDENT_PRIORITY` keeps both no-change and incident
actions, stops repair, disables mutation fallback and grants no environment pass.
The frozen fifth targeted baseline independently reran **90/90 passed**, alongside
the two old counterexamples above; no earlier-tree source files were changed.

## Scope, risk and rollback

Owned implementation files are the two candidate compilers, `repair_cli.py` and
`repair_execution.py`, plus the Agent selector integration in
`agent_remediation.py`; tests are their six existing targeted suites. API docs are
`docs/config-edit-plan.md` and `docs/rules-extension-plan.md`. No new CLI/service,
engine rewrite, accepted source pin or broader grammar was introduced.

Risk: consumers must handle the new no-change state and nullable private action
plan/insertion. The shared CLI and execution entry points now do so explicitly.
Fresh reads remain subject to later external changes; output is deliberately
limited to supplied snapshots and does not claim live configuration stability.
For unsupported nonempty prepend, the Agent should preserve the file and explain
the exact limitation instead of merging or deleting unrelated entries.

Rollback only this increment's code/test/doc patch to restore the fifth behavior.
The increment itself performs no user-device mutation. Synthetic transport tests
write only their temporary fixtures and clean them through the test harness.
