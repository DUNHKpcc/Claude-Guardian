# Workflow enforcement review: ENV-T79, ENV-T81 and ENV-T90

Date: 2026-10-21 UTC. Verification layers: **ENV-T79 L**, **ENV-T81 L + C**, **ENV-T90 L + C**. Dependency **A**
(cloud, deterministic, no user machine, no real account, no external request). Source baseline: the tree at
`9a44ff9` (parent of the commit that adds this page).

This page re-registers the three cases that the 2026-10-19 entry-gate change moved to "pending revalidation". An
unchanged replay hash is not revalidation by itself, so each clause below was re-read against the current
behavior and the current guidance text. The C part is a **guidance-text review by the author**, not a fresh
model dialogue and not an independent reviewer (see "Not claimed").

## Original requirements

Quoted from `skills/claude-guardian/sources/design/D-ENV-v0.3.md` (§12.3 rows, lines 865, 867 and 876):

- **ENV-T79**, scenario "预置规则含 Claude 域名": 只做离线语法/匹配模拟，不为验证规则主动查询目标域名；实际命中仍标后验。
- **ENV-T81**, scenario "接触前必需项目未知或有真实误直连": 门禁保持 closed；不是标成可选限制后自动登录/购卡。
- **ENV-T90**, scenario "Skill 的网络控制仅为指令或脚本检查": 声明真实 enforcement 层级；搜索/MCP/浏览器等未覆盖范围不冒充 OS 级隔离。

ID, scenario, requirement and layer in the ledger are unchanged. The historical pages
`docs/evidence/rebuild-enforcement-cases.md` and `docs/evidence/rebuild-required-controls-case.md` stay in the
ledger as `historical_evidence`, byte for byte.

## What was run

    PYTHONPATH=tests python3 -B tests/test_acceptance_boundary_rebuild.py        # 8 tests, OK
    PYTHONPATH=tests python3 -B tests/test_acceptance_required_controls_rebuild.py  # 23 tests, OK
    PYTHONPATH=tests python3 -B tests/test_acceptance_boundary_rebuild.py --replay
    PYTHONPATH=tests python3 -B tests/test_acceptance_required_controls_rebuild.py --replay

Two complete `--replay` invocations per script give identical stdout. Boundary replay: 18789 bytes, SHA-256
`b014fc2e16015a9ecd07b2f95460ab5fead21b625fd882eb01d8031042325581`. Required-controls replay: 743185 bytes, SHA-256
`097e5442157d2942152f0a2c99035af7f9ead6b800967696d1165818f9a6840b`. Both equal the values recorded in the
historical pages. That equality only says the public decision output did not change; the clause-by-clause reading
below is what supports the registration.

The replays and tests install fail-fast sentinels on `builtins.open`, `io.open`, `os.open`, `socket.socket`,
`socket.create_connection`, `socket.getaddrinfo`, `socket.gethostbyname(_ex)`, `socket.gethostbyaddr`,
`subprocess.Popen`, `os.system` and `os.popen`, and assert none was called. These are test instrumentation, not host
telemetry and not OS isolation.

Changes since the historical review that could touch these paths: commit `75dc6fb` added the shared
`reject_unknown_report_members` check used by the dashboard, the Agent remediation selector and probe evidence.
None of `workflow_guard.py`, `rule_format_conversion.py`, `rules_extension_plan.py` or `inventory_cli.py` differs
from the `29f9d39` baseline, and the full suite (including these 31 tests) passes on the tree that carries this page.

## ENV-T79 (L): offline matching only, actual hit stays post-contact

Observed in the boundary replay (`case_id: ENV-T79`), synthetic prepend rules `DOMAIN,claude.ai` and
`DOMAIN-SUFFIX,anthropic.com`:

- **Offline syntax and matching.** Exact-host intersections are computed from the literal rules and declared hosts
  only: `claude.ai` matches the exact rule; `anthropic.com`, `api.anthropic.com` and `deep.api.anthropic.com` match
  the suffix rule; `www.claude.ai`, `notclaude.ai`, `claude.ai.invalid`, `notanthropic.com` and
  `anthropic.com.invalid` match nothing. The converted output is the 85-byte candidate
  `{"version":1,"rules":[{"domain":["claude.ai"]},{"domain_suffix":["anthropic.com"]}]}`, scope
  `canonical_lowercase_ascii_predicates_only`, `effective_priority: not_established`.
- **No domain is queried to validate the rules.** The replay runs under the I/O sentinels; none fired. Additional
  tests: an invalid mixed source is rejected atomically offline, cancellation and a protected rule fail without I/O,
  and a same-source request with a suffix does not touch DNS.
- **Priority and apply are not claimed.** The rules-extension compiler returns `status: candidate_only_blocked`,
  `apply_supported: false`, `native_acceptance: not_run`, `protected_index_coverage: caller_declared_unverified`,
  with nine named blockers (adapter not implemented, version capability unverified, effective priority unverified,
  and so on). Four known base-rule overlaps are reported; the replay does not call them effective routing. Unknown
  declared priority yields `SEMANTIC_PLAN_BLOCKED`.
- **Actual hit remains a later check.** The post-contact schedule is allowed with
  `pending_checks: ["claude-domain-actual-hit"]` and `executes: false`. A synthetic hit supplied as evidence does not
  satisfy it: that decision is `allowed: false` with `EVIDENCE_REQUIRED:claude-domain-actual-hit`.

Assessment: all three clauses (offline simulation only, no active query, actual hit marked after the fact) hold in
the current output. Pass.

## ENV-T81 (L + C): required controls keep the gate closed

L part, from the 23 required-control tests and the 23 replayed records (all decisions carry
`enforcement_level: workflow_guard` and `executes: false`):

- Unknown, skipped, not-applicable, blocked, failed or absent mandatory control: every contact handoff is denied
  (`EVIDENCE_REQUIRED:required-fault-blocking`), the state stays `closed`, and no approval callback is invoked.
- A mandatory readiness gap in G2 is not downgraded to an optional limit (`G2_INCOMPLETE` blocks).
- A scoped real direct-path conflict denies even when older passing evidence exists (`KNOWN_CONFLICT`), and a current
  epoch review does not clear an unresolved conflict.
- A new required unknown after PC1, or a real-path incident after PC2, blocks login and payment immediately and
  without an approval callback. Recorded contact revokes; old passes, new timestamps, a same-binding reset or a saved
  open gate cannot reopen it.
- Payment needs its own current review and its own approval; a missing purchase review does not by itself revoke an
  otherwise valid login grant. A required manifest is neither a saved permission nor an optional flag.
- Unknown controls allow only an independent offline plan, never automatic contact.

C part, active guidance read on 2026-10-21:

- `references/contact-and-safety.md` PC-G1: "List every unavailable or unmeasured requirement ... do not silently
  waive a strict user requirement"; PC2: "Login is not payment authorization. A real-path failure pauses payment and
  returns to diagnosis"; the section that keeps answers, plan acceptance, host permission, OS privilege,
  first-contact authorization and payment authorization distinct.
- `SKILL.md` step 7: inventory completion is not PC-G1.

Assessment: the gate stays closed, required items are never relabeled optional, and no path in the replay logs in
or buys a card automatically. Pass for L; the C clause is supported by the guidance text above, with the limits
below.

## ENV-T90 (L + C): declared enforcement level

L part (boundary replay `case_id: ENV-T90`):

- Every public workflow decision carries `enforcement_level: "workflow_guard"` and `executes: false`.
- The six surfaces the clause names or implies (`browser`, `hosted-search`, `mcp`, `shell`, `computer-use`,
  `connector`) are denied while the gate is closed with `UNSUPPORTED_OPERATION_SCOPE`,
  `CONTACT_GATE_CLOSED_OR_OUT_OF_SCOPE` and `EVIDENCE_REQUIRED:preparation`: they are not treated as covered.
- Denials do not open the gate. An observed contact moves the gate to `revoked` with
  `observed_contact: observed`, and a resumed session reports `previous_contact_reported`; the gate is `closed`
  and `runtime_permission_restorable` stays `false`.
- The inventory workflow CLI states its own limit: "Caller-asserted target/user/namespace and local hydrated storage;
  terminal response is not authenticated consent or host/OS approval. No saved grants, OS isolation, controller
  access, or readiness claim." It exits 0 with `transition_available: false`.
- Host denial, cancellation and a missing permission remain workflow-only in the dedicated test.

C part, active guidance:

- `SKILL.md` line 66: "workflow_guard提供即时资格判定，不是进程隔离或可持久化执行授权。"
- `references/contact-and-safety.md` line 9: "These are workflow controls, not a firewall. The preview does not stop
  unrelated apps, restored browser tabs, or user activity, and cannot erase prior contact ... Strict no-egress
  requirements remain blocked without a tested technical boundary."
- `SKILL.md` step 7: "离线测试不证明平台支持或网络隔离。"

Assessment: the real level (`workflow_guard`) is declared in output and guidance, and the uncovered paths are named
as uncovered rather than as isolated. Pass.

## Not claimed

- **C layer is author-side only.** No new model dialogue was run, and no independent reviewer re-read the guidance.
  The C assessment is a clause-by-clause reading of the shipped text against the output. A later model-dialogue
  replay or an independent review could still find wording problems.
- No real device, OS isolation, firewall, TUN, real proxy or effective-routing evidence. `workflow_guard` is a
  qualification check, not an enforcement boundary; the I/O sentinels are test instrumentation.
- No claim that a real client hit a Claude domain, matched a rule, or was blocked. The actual-hit check remains
  post-contact work.
- No native Mac or Windows detection of required controls; the inputs are synthetic host assertions.
- Rule priority, base rule graph, protected rule coverage and later merge-script effects stay unverified in the
  compiler output.
- Other cases in the workflow area, and every pending case, are unaffected.

## Reproduce

From the repository root:

    PYTHONPATH=tests python3 -B tests/test_acceptance_boundary_rebuild.py
    PYTHONPATH=tests python3 -B tests/test_acceptance_required_controls_rebuild.py
    PYTHONPATH=tests python3 -B tests/test_acceptance_boundary_rebuild.py --replay | sha256sum
    PYTHONPATH=tests python3 -B tests/test_acceptance_required_controls_rebuild.py --replay | sha256sum
    python3 -B -m unittest discover -s tests -v
