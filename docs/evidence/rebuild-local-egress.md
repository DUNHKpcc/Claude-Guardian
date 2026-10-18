# Original T23: local Code with a VPS proxy exit

## Exact case and scope

Original D-SPEC-v0.1.10 §11 T23: **本机 Code 使用 VPS 代理出口 — 主流程仍为本机；记录网络出口，不能自动安装远端工作区**. The original tracker layer is **L+C**. This is a candidate for independent whole-clause review, not a ledger update or native acceptance claim.

D-SPEC §3 route distinction says client runtime and network egress are separate: a VPS proxy does not turn a local client into a remote workspace, and a local editor window does not prove local execution. This candidate supplies a concrete normalized local-Code/exit-only scenario. The trusted Agent must first determine actual execution location and intent; the pure interview API is not an NLP classifier. Do not manufacture local classification for an explicitly remote runtime.

## Logic replay

`tests/test_acceptance_local_egress.py` provides four inspectable scenarios against current nineteenth:

1. A complete existing-subscriber environment task explicitly selects local execution. Q-N01 records proxy kind, VPS-exit-only role and opaque exit alias; Q-N02 separately records local Code/proxy runtime, exit alias and no remote workspace. The facts retain their exact reported state, source and timestamp. Local questions are exactly Q-L01/Q-L04; no VM, VPS or payment branch is applicable. G2 planning passes, G3 stays blocked, contact stays PC0, payment intent stays none and save/export consent stays false. No question remains.
2. Before an explicit route answer, these same exit facts do not silently select a workspace. Q-C05 is the next question, selection basis stays default_proposal and G2 is blocked. This is a focused negative control, not whole T26 acceptance.
3. Saving requires separate opt-in; loading preserves the exact local state without permissions. A real interruption blocks planning. A reported exit change marks only Q-N01/N02 stale, preserves all unrelated facts and local route, asks Q-N01 and does not create a remote-workspace branch.
4. Missing local installation metadata asks the exact Q-L01 prompt and blocks G2. The system does not substitute remote setup for the missing local information.

All scenario execution occurs behind file-open, socket and subprocess sentinels after module loading. No installation, networking, payment or real-device inspection occurs. Literal assertions define expected route, branch IDs, gate/permission state and reported facts independently of runtime results. `--replay` retains full state, full assessment, next question and applicable-question objects. Input values are synthetic categories/aliases; there are no proxy URLs, credentials or private device facts.

## Actual operative guidance review (C)

- `references/routes-and-platforms.md`, Common concepts: “VPS ownership or using a VPS proxy does not make a local client a remote workspace.” It explicitly distinguishes execution host, target and egress, including locally displayed remote editors. This is the classification instruction for the host, not an assertion that the questionnaire automatically parses prose.
- Same file, R-LOCAL: identify only the chosen local client and relevant proxy boundaries; perform only necessary scoped steps. Its L1 card checks actual target/user and required client, preserves local projects/configuration and does not install to fill an inventory gap.
- Same file, R-VPS: “First confirm workspace versus exit-only role.” Existing/new server, SSH/rescue and remote development steps apply to a workspace choice. It says not to purchase, reimage or assume an empty server. Execution-card rules expand only the selected route.
- `references/intake.md`, Scheduling: route must be explicit_choice/task_context/accepted_default, never inferred from expertise or owned equipment. Pure technical diagnosis does not activate payment questions. Q-N01/N02 cover network type and runtime/proxy locations; Q-S01 distinguishes workspace from exit-only when that branch is relevant.
- Same file, Interruption and resume: retain selected route and provenance, inspect scoped changes, invalidate only related facts, never treat review/save as action authorization. This matches the changed-egress replay.
- `SKILL.md`: default CLI does not automatically network, pay, clean or modify configuration; specific host actions remain separately scoped/authorized. Its default local proposal is not permission and optional VPS guidance is not an instruction to install a workspace.

These sentences and the public replay jointly cover all three original obligations. They do not certify model behavior on arbitrary wording, a real proxy route, remote setup capabilities or native-device enforcement. No new N layer is invented; no missing native evidence is relabeled as pass.

## Reproduction

```sh
GUARDIAN_AUDIT_ROOT=/path/to/Claude-Guardian-nineteenth PYTHONDONTWRITEBYTECODE=1 python -B tests/test_acceptance_local_egress.py --replay
```

The candidate adds only this page and one test file. Review receipts, queue, logs and replay live beside the candidate outside the repository. Runtime, original sources, ledger and existing tests are unchanged. Independent review and final integrated validation are required before acceptance. Rollback removes candidate files and any future corresponding acceptance entry together.

## Evidence pins

| Path | SHA-256 |
|---|---|
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `skills/claude-guardian/scripts/interview_flow.py` | `0eb24c5fc9b356f145b35b792a13444392f23ea634f618df6886b16aa91beaac` |
| `skills/claude-guardian/SKILL.md` | `e34047180a0259a6a14e606f583ef0897c2057f5477e7c16f2aefde7af2fd276` |
| `skills/claude-guardian/references/intake.md` | `24fb26e81ec534f3678a5d081cf126ab1526fffb53df84a96c44f1eb928e9d47` |
| `skills/claude-guardian/references/routes-and-platforms.md` | `dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `tests/test_acceptance_local_egress.py` | `f191e857eec5c8b6221ba2a2f8a9c97bf8b632a3f2e09a018d8f7d08655c3959` |

Minimum-Python CI found that TestCase.enterContext requires Python 3.11. The equivalent ExitStack plus addCleanup(close) supports 3.10 while preserving the same patch lifetime and assertions.
