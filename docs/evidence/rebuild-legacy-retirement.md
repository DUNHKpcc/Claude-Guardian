# Original T82 candidate: retired ownership fields

Status: independently cleared against the full original T82 L+C clause within the documented compact/report host contract. The reviewer determined that the original requirement is semantic retirement, not a promise of arbitrary historical wire-format import. This integration-ready evidence retains that boundary; ledger promotion remains a separate integration step.

## Exact original condition

- ID: T82
- Scenario: 续接旧画像含 Q-C07 或账号归属字段
- Requirement: 已停用问项不加载、不改名询问，不把缺少该字段当作就绪阻断
- Original layer: L+C

D-SPEC §6.11, §7.4 and D.11 require retirement from display, scheduling, required profile fields and readiness, with no ownership/control synonym and no reinterpretation of old Q-C08 entitlement as a desired plan. They describe conceptual profile content but do not specify a historical serialized wire format. The supported concrete compatibility API is explicitly described in active SKILL: versioned compact input, not automatic CLI migration.

## Supported boundary, without widening it

`interview_migration.migrate_legacy` accepts `guardian-interview/0.1` compact answers and the exact `guardian-report/0.1` interview wrapper emitted by the repository's producer. Compatibility keys Q-C07, account_ownership, account_control and old Q-C08 are accepted only inside answers, with bounded sanitized nonblank string values, solely for discarding. The producer itself is not claimed to have emitted those compatibility keys. The test adds them explicitly as synthetic historical compatibility input.

Allowed surviving named fields are retained as stale facts with source paths, unknown freshness and fresh caller-supplied target/account aliases. Those aliases label association, not account ownership or actual permission. Current facts must be reconfirmed by the host before becoming reported current evidence. Saved permissions never transfer.

Unversioned dictionaries, invented old full-state schemas, unknown synonyms, top-level ownership keys, malformed values and unsafe discarded values fail closed. Current `loads_state` rejects retired facts or asked IDs instead of automatically migrating them. No CLI fallback or generic private-profile importer exists. A real user-supplied historical format outside this contract remains blocked pending deliberate supported mapping; these tests cannot establish its compatibility.

## Actual candidate checks

`tests/test_acceptance_legacy_retirement.py` provides nine passing tests:

1. No tombstone, each individual tombstone and all tombstones produce identical current states; discarded values are not echoed and inputs remain unchanged
2. Every retained fact's exact stale envelope and field-path provenance is checked; subscription/binding/freshness remain unverified and no action/save consent is recovered
3. A complete independent 20-question refresh trace pins every full prompt object. Decorated and undecorated imports have identical traces and terminal states; none asks a renamed ownership question
4. Real producer-shaped wrappers, with and without the fixed policy member and synthetic old advisory prompt text, discard that prompt and retain named-field meanings
5. Old Q-C08 cannot become the new target plan; explicitly named target_plan remains a distinct stale fact
6. Clean loading and actual resume review preserve retirement while current same-target association remains separate from ownership/control
7. Current mutation/loading interfaces reject retired fact IDs and asked IDs without modifying the input
8. Unsupported shapes and unsafe/malformed values fail closed with sanitized errors and no partial state
9. Missing fresh binding or a genuine current network gap still blocks; absent retired fields never cause that block

The complete path is Q-J01, Q-C11, Q-C02, Q-C01, Q-OS03, Q-C03, Q-C04, Q-C05, Q-C06, Q-C09, Q-N01, Q-N02, Q-N03, Q-N04, Q-N06, Q-L01, Q-L04, Q-C12, Q-Z01, Q-C10, then no next question. Six stale imported fields are explicitly refreshed rather than silently trusted. Final G1 is complete, G2 planning passes, G3 remains blocked, PC0 remains unchanged and no persistence permission exists. No original native layer is claimed from the ledger's separate conditional-native follow-on.

## Active content review

- SKILL start instruction 4 expressly forbids renamed ownership/control questions, not merely the old ID. Its migration paragraph explicitly distinguishes supported compact migration from current CLI resume
- Intake's opening and stable-ID registry say Q-C07 is never active or a missing field; the whole registry is not a mandatory form
- Intake Q-C03/Q-C04/Q-C06 ask relevant history, reported registration/login and authentication category without credentials. They do not investigate who owns or generally controls the account
- Same-target device/account association on resume is not account ownership. Relevant changed environment facts can be reviewed without reintroducing Q-C07
- Specific project authority, billing confirmation and Apple/Google login/target correspondence remain legitimate scoped prerequisites; they cannot be repurposed into the prohibited ownership survey
- G1/G2 requirements derive from applicable active questions. The complete paired trace proves removal is not merely cosmetic: with and without discarded values it reaches the same planning state
- G3 and save/contact gates remain independent. Removing Q-C07 does not waive actual action-time authorization

The code/guidance reconnaissance author also prepared this T82 test file. A separate reviewer subsequently checked the completed artifact, all exact original clauses, active guides and supported-format scope. Its frozen review receipt SHA-256 is `eb62cf77b3e1b3f14e82b61bbcc6b67ffb73d84f024e1b231ce61c226971a411`. It reran 15 combined candidate tests, 172 existing interview tests and 68 independent assertions, including compact/report tombstone-versus-omission state and readiness parity. Both replay artifacts matched exactly.

## Documentation correction and scope judgment

No failure was found within the supported compact/wrapper contract. The accompanying narrow `docs/interview-migration.md` correction adds the already-supported optional fixed `traffic_policy` member alongside `question`, with exact key/type/value validation and no imported authority. Existing migration tests cover the accepted member and reject missing/extra keys, altered values and incorrect types. This is a documentation correction only; input scope and runtime do not change.

The independent reviewer concluded that supported compact/report migration plus strict current-schema rejection and the reviewed host guidance satisfy the full stated retirement clause. The original condition names no historical wire format and does not mandate a universal importer. This conclusion does not establish that all ordinary historical profiles resume automatically: a concrete outside-format input remains unsupported and requires a separately justified mapping. No broad compatibility claim follows from nine passing tests. Actual native import/presentation remains untested, and an integrated-tree rerun still binds the final delivered bytes.

## Reproduction and evidence

Run from the integrated repository root:

```sh
PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_acceptance_legacy_retirement.py -v
PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python -B tests/test_acceptance_legacy_retirement.py --replay > legacy-retirement-replay.json
PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_interview_migration.py -v
```

On PowerShell, set `$env:PYTHONIOENCODING='utf-8'` and `$env:PYTHONDONTWRITEBYTECODE='1'` before the same `python -B` commands; retain UTF-8 explicitly when the shell re-encodes redirected output. For an external candidate, set `GUARDIAN_AUDIT_ROOT` to the source checkout and invoke the candidate file. Artifact output destinations remain operator-selected.


Run the same file with `--replay` for actual states, prompts and assessments. Repeat-identical replay SHA-256: `3e55aa2a1e193fa7775447118a620933c3780e4cf0590cd0392b8a75df1a3e90`. Exact integration dependencies are pinned below; preparation logs/replays and their manifest remain retained with the delivery receipt. Proposed synthetic dialogue exercises are explicitly unrun; the tests neither generate model responses nor verify a native host import.


## Exact dependency pins

The corrected migration document is pinned at its candidate bytes; all runtime and original-spec dependencies remain unchanged. Aggregate acceptance ledgers and trackers are deliberately excluded.

| Dependency | SHA-256 |
|---|---|
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `skills/claude-guardian/scripts/interview_flow.py` | `304144309c2e918223777df5d0f2f9801ff1e862fad195d18f0f318b5b321f4e` |
| `skills/claude-guardian/scripts/traffic_policy.py` | `8abb87e212b96f2dc80f59d065b13256257211b4743340438090aca8bd53d9fd` |
| `skills/claude-guardian/SKILL.md` | `e34047180a0259a6a14e606f583ef0897c2057f5477e7c16f2aefde7af2fd276` |
| `skills/claude-guardian/references/intake.md` | `1d3d6f75788abafefe4a8ce8e9ca1c740b1f4b57656b350a4688c6629ac52dba` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `skills/claude-guardian/scripts/interview_migration.py` | `a52e4b7530fd99650579d418aac387231fd2e632ba8f3b407f5b94cfe1da86fd` |
| `skills/claude-guardian/scripts/guardian.py` | `f15f01a1a26406ff30c523577569d599f662f18f6ad4b1fab0a99d7b2afaddfa` |
| `docs/interview-migration.md` | `9c70baad590bfc6ccdf99c1c5d93c4f32b1062e840d3098599143197675087ea` |
| `tests/test_interview_migration.py` | `6c4e6bf32875b83ea179ffc836f140141f161240b478b359b62b304767063618` |
| `tests/test_interview_flow.py` | `7140e70b88e4cd3099d2fa725b3b20269de511be90d4dd020154d2db3e5e0965` |
| `tests/test_interview_resume.py` | `081036b33c3b9a97a476d1e7894b2876ffe0b07d3bdf148b36fe1f370b47d442` |
| `tests/test_acceptance_legacy_retirement.py` | `22e4a208acc0c768af0469e6cd864fdf927586531899a0703ec5d874b12192a8` |

Prior migration-document SHA-256 (only the optional-member statement changes): `1cb55357db07e7ce3ceaaec462cfe5ae6b23a79ad5bdffe0de81e67c753a119f`.


### Twentyninth subscription-repair preservation review (2026-10-18)

The earlier statement that runtime dependencies were unchanged describes the prior T82 migration-document-only batch. In this later repair, interview runtime/intake/supporting-test bytes change; the legacy migration implementation and original specification remain byte-identical. An independent reviewer re-read original T82, D-SPEC §6.4, §6.11, §7.4 and D.11, and the changed current-plan/receipt guidance for ownership or authority leakage.

All nine original tests pass on fresh published baseline and candidate, with zero skips. Full paired tombstone/omission, wrapper, stale-envelope, 20-question refresh, rejection and resume traces remain byte-identical across both trees and both runs: SHA-256 `3e55aa2a1e193fa7775447118a620933c3780e4cf0590cd0392b8a75df1a3e90` (277948 bytes), matching the historical replay. Independent tests confirm that retired Q-C07/account_ownership/account_control/old Q-C08 neither create Q-C13 or a completion receipt nor become missing readiness requirements. Explicitly named target_plan remains a separate stale target; imported subscription remains unknown. New current-plan and receipt account aliases are bounded association metadata, not a renamed ownership/control questionnaire or recovered permission.

The full original T82 L+C conclusion is preserved under the same explicitly supported compact/report migration contract and strict rejection of unsupported shapes. This remains semantic retirement, not a universal legacy-format importer. No generated response, native import, live account verification or new action authority is added. Historical generated-response packet provenance is untouched. Refresh only the reviewed current dependency table pins and the final page hash in its ledger entry after retaining this review.
