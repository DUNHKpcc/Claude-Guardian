# Focused inventory and export boundary rebuild

Date: 2026-10-18. Candidate: isolated thirteenth tree, based on frozen eleventh source. This is scoped logic evidence, not full original-case acceptance or native validation.

## Original requirements

- T11 (`D-SPEC-v0.1.10.md:1070`, tracker row T11), L+C: credential-bearing logs must not carry secrets into reports, templates or public repositories.
- ENV-T34 (`D-ENV-v0.3.md:794`), L: proxy passwords/subscription tokens must fail export privacy checks and not be exported.
- ENV-T121 (`D-ENV-v0.3.md:916`, §§19.2/19.8), L: arbitrary commands/URLs and unknown secret fields require input/output schema and local filtering rejection, not display-only masking.
- ENV-T124 (`D-ENV-v0.3.md:919`), L+C per original tracker: synthetic contract evidence cannot establish platform or whole-machine testing. This batch addresses one provenance-loss subcase only; it does not change the original layers.

Original rows remain pending. The audit describes remaining public surfaces and content review; this patch does not close them by inference.

## Proven defects and changes

1. Inventory import previously projected unknown root/fact fields away before validation. `validate_inventory_envelope` now checks the complete current-release envelope and nested keys before projection. All source_refs are checked, including later references that the compact downstream model cannot retain. Unknown command/script/url/url_to_test/secret fields at root, binding, contact, privacy, snapshot, limits, findings or facts are rejected. Nonempty unsupported evidence is rejected.
2. Ordinary argparse invalid-choice/unknown-option errors echoed input before report redaction. `PrivateArgumentParser.error` retains static usage and fixed INPUT_OR_RESPONSE_INVALID with exit 2, omitting argparse's untrusted message. Fixed `prog=guardian` prevents a caller-controlled executable name from entering usage. Normal help remains available. CLI errors do not start collectors or exporters.
3. Static inventory aliases previously checked syntax only, then copied target_ref into even blocked reports. They now also use the same narrowly scoped known-credential detector as guardian aliases. Both target and file-source aliases reject generated known-token forms before collection; normal task aliases and short Slovak-like aliases remain accepted. This is not arbitrary-secret recognition.
4. Synthetic inventory reports were relabeled user_supplied_observation. Supported synthetic envelopes now retain synthetic_example through analyze, plan and dashboard projection. Imported device_observation/legacy offline_analysis remain unverified user-supplied observations, never authenticated device evidence. The change does not create executable plans or an environment-pass claim.

5. The compact interview report wrapper now validates complete current-producer root and nested metadata/question shapes before extracting state. Static inventory rejects unknown keys in target_binding, authorization and application before invoking cancellation callbacks or reading files. Original-case closure still requires the other public surfaces. The additional failing-first wrapper/nested regression run produced 19 failures before repair.

## Explicit supported schema and compatibility

The audited producer is `guardian.native_check`, based on `guardian.base`. This is the reconstructed current-release format, not the unavailable historical contract ZIP.

- Complete base envelope keys are required; schema_version is env-inventory/0.2. The converter still requires operation=audit, completed status, closed precontact gate and changes=[].
- Base metadata structures have closed keys and bounded typed values. Metadata is discarded where the compact model cannot represent it; it is not treated as proof of host identity or authenticity. This validator is not a complete normative value-enum validator for all historical report contracts.
- Binding supports the four required offline-binding fields plus native_check's binding_state=bound_by_explicit_operator_attestation, requested_role=local_desktop and network_namespace=not_verified. Required binding values retain downstream validation.
- Facts require id/value/state/context_ref/observed_at/layer/source_refs, optionally known reason_code/coverage. One to 64 source references must each satisfy the alias contract. The compact model keeps the first; all are checked before projection. Native macOS version reports with two sources remain accepted.
- Privacy and snapshot match base shapes. Limits match base plus exact optional command timeout/stdout budgets emitted by native_check. Facts retain existing typed-value validation, including no-value states and legitimate Slovak locale/language tags.
- synthetic_example, device_observation, offline_analysis and user_supplied_observation are recognized provenance kinds. Unknown or wrong-typed kinds are rejected.
- Hand-constructed abbreviated envelopes formerly accepted by the permissive converter are now rejected, including the independent audit's minimal ENV-T124 reproducer. That original reproducer is not reported as an after-pass. The new full-envelope regression tests the provenance repair without bypassing the schema boundary.

Wrong-typed fact IDs/states/layers, provenance, declared OS and snapshot state are rejected with fixed schema errors before hash-set membership; direct APIs no longer expose TypeError for those malformed inputs. The additional failing-first malformed-input test produced 18 errors before this repair.

Existing guardian producer/import tests pass unchanged. Future producer additions require an explicit schema update and positive/negative tests; do not restore permissive projection for compatibility.

## Reproducible tests

Run from repository root:

    python -B -m unittest discover -s tests -p test_inventory_export_boundaries_rebuild.py
    python -B -m unittest discover -s tests -p 'test_guardian*.py'
    python -B -m unittest discover -s tests -v

Failing-first receipt: initial 10 focused tests produced 46 failing assertions/subtests on the unchanged candidate. Expected failures covered unknown nested fields, ignored later source references, unknown provenance, synthetic-label loss, argument stderr echo, saved-report rejection and blocked alias echo. Positive controls already passed.

After implementation, the final focused suite contains 21 tests and passes. Added safety checks cover malformed provenance types, unknown finding/evidence fields, credential-shaped file-source aliases and isolated module import. Independent review caught a sibling-import dependency masked by the full suite; the collector now keeps an aligned local alias regex and the isolated subprocess regression passes without sys.path setup. Existing guardian suite: 71 tests passed. Standalone clash inventory: 35 tests passed, independently of discovery order. A complete fresh suite result is recorded in the external delivery receipt; skips remain skips.

All markers are synthetic. Test subprocesses exercise argument parsing or offline analyze/plan only. Test exports use temporary directories. A mocked platform string tests validation dispatch, not native compatibility. Static inventory regressions assert zero collector reads. There are no endpoint requests, Claude contact, credential reads or host setting changes in this work.

## Remaining scope and proposed guidance

No package manifest, source pin, ledger or prior evidence is changed here. Integration must refresh packaging/source receipts through the parent-owned process.

Separate guidance proposal: document the complete current inventory envelope requirement and the rejection of abbreviated hand-built reports; state that every imported result remains unverified and that synthetic labels survive transformations. Do not present this as the full historical ENV schema.

Remaining original-case work includes the other public import/CLI/export boundaries, arbitrary collector exception pipelines, complete report/template/archive sentinel checks and T11 content review. Known credential screening is defense in depth; closed field semantics and trusted non-identifying aliases remain essential. No test result here authenticates real native evidence, restores the historical 56-case attachment or closes full ENV-T124.
