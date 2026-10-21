# Conversion and recovery compatibility review: ENV-T40

Date: 2026-10-21 UTC. Verification layers **L + R**, dependency **A, P**. This is the compatibility review that the
`conversion_recovery_compatibility` group requires after the repair CLI and execution entry changed. No C layer is
involved. Source baseline: the tree at `2b268bb` plus the review files of this batch.

## Original requirement

ENV-T40, 纯域名/规则提供方/主规则/JSON 格式转换: 不可表达的 ASN/匹配/动作语义明确报错，不静默丢失 (D-ENV v0.3 §12.1).
The ledger row, scenario and layers are unchanged. Supported grammars are deliberate subsets; an unsupported feature
is an explicit error, not a promise of every engine feature.

## What stays historical

`docs/evidence/rebuild-env40-composition.md` and its clause-by-clause table (plain domains, rule providers, main rules,
JSON, ASN, match semantics, action semantics, explicit errors, L + R) stay as `historical_evidence`.

Of the 17 pins on that page three differ today: `scripts/repair_cli.py`, `scripts/repair_execution.py` (the entry
changes this review exists for) and `tests/test_ordered_policy_transaction.py` (it now also asserts the current repair
entry behavior, below). The converters, `rule_source_import.py`, `config_edit_plan.py`, `transactions.py`,
`recovery_cli.py` and the other test files are byte-identical. The pinned bytes of the three changed files cannot be
diffed (squashed history), so they are assessed by rerunning behavior.

## Rerun on the current tree

    PYTHONPATH=tests python3 -B -m unittest test_rule_format_conversion test_rule_policy_conversion \
      test_rule_conversion_transaction test_ordered_policy_transaction test_transactions \
      test_prepared_recovery test_prepared_recovery_cli

200 tests, OK, 0 skipped: the same total the historical page recorded (its breakdown: 47 predicate, 26 ordered, 10
existing predicate transaction, 18 new ordered transaction, 42 transaction, 39 prepared recovery and 18
prepared-recovery CLI; counts overlap and are not additive). The ordered-policy transaction file alone is 18 tests, OK. They cover, on dedicated synthetic temporary artifacts: exact and suffix match semantics, ASN rejection
(`UNREPRESENTABLE_MATCH`), action-bearing material refused by the actionless converter (`UNREPRESENTABLE_ACTION`),
atomic failure of mixed supported/unsupported batches with the planner, writer and authorizer never called, ordered
occurrence provenance, actual write, readback, independent rollback, and prepared-v2 reconciliation and restore after
a post-replace journal failure, with neighbor contents and modes unchanged.

Current entry behavior (the reason for revalidation): `test_ordered_policy_transaction` asserts that
`repair_cli.preflight(... candidate_kind='policy-conversion', entry_request=local_entry(...))` is refused with
`UNSUPPORTED_CANDIDATE_KIND` without reading the request file, that `repair_execution._native_session` refuses with
`NATIVE_REPAIR_ADAPTER_UNAVAILABLE`, and that the target bytes are unchanged with no backup created. So the converted
output cannot reach a real configuration through the repair entry; recovery is exercised only on the dedicated
temporary artifacts of the tests. The cross-path matrix of `docs/evidence/input-boundary-revalidation.md` shows the
same repair entry rejecting unknown request members (6 cases x 3 commands) with no stray file.

## Assessment

Each unsupported ASN, match or action case still fails with a fixed code and without silent loss, supported
conversions keep exact bytes and provenance, and actual write and restoration on temporary artifacts still compose
with them (L + R). The repair entry does not widen what a conversion can do. Pass.

## Not claimed

- No real configuration, live Mihomo or sing-box engine, installed-version check or effective-routing claim; versions
  are the fixed compatibility targets from the historical page.
- Restoration is proven on POSIX temporary files only; no Windows, native admission, user device or production
  recovery.
- No new external-source fetch; the historical semantic pins are reused.

## Reproduce

    PYTHONPATH=tests python3 -B -m unittest test_rule_format_conversion test_rule_policy_conversion test_rule_conversion_transaction test_ordered_policy_transaction test_transactions test_prepared_recovery test_prepared_recovery_cli
    python3 -B -m unittest discover -s tests -p test_ordered_policy_transaction.py -v
