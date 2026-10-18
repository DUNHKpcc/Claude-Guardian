# ENV-T79 / ENV-T90: offline rule and enforcement boundary revalidation

Date: 2026-10-18 (UTC). Scope: the eleventh isolated working tree assembled from
the baseline and tenth checkpoint26 patch, plus the explicitly listed changes
below. Local Git HEAD is not the identity of these current bytes. The source
hash table fixes the reviewed implementation, original conditions and active
content. Original acceptance statuses remain the parent's ledger decision.

## Original full conditions and verdict scope

| Original ID | Original scenario | Original complete requirement | Original layers | Candidate conclusion |
|---|---|---|---|---|
| ENV-T79 | 预置规则含 Claude 域名 | 只做离线语法/匹配模拟，不为验证规则主动查询目标域名；实际命中仍标后验 | L | All clauses have the exact offline replay below |
| ENV-T90 | Skill 的网络控制仅为指令或脚本检查 | 声明真实 enforcement 层级；搜索/MCP/浏览器等未覆盖范围不冒充 OS 级隔离 | L + C | Complete public-output replay and the sentence/clause review below support the original scope |

Sources: D-ENV v0.3 §12.3 rows ENV-T79/ENV-T90 and §18.5–18.8; the
`implementation-tracker.md` §8.2 rows supply the unchanged original layers.
D-SPEC v0.1.10 §6.13 distinguishes G1/G2/G3 from PC-G1/PC-G2. The original
historical statement that cases were unimplemented is not current runtime
verification, and has not been rewritten.

L is pure logic/dialogue/fixtures; C is content/source review. These rows do not
require N or X. No network, native device, actual approval UI, model response,
OS isolation, live domain hit, engine execution or current external-source
verification was performed. The findings do not accept ENV-T40, any native VAL
row, or the full project. The broader full-spec work continues after this
priority checkpoint.

This boundary-review subset changes no production runtime. It adds one exact
replay test module and this evidence page; other coordinated eleventh-batch
subsets may change their separately reviewed runtime files. A coordinated content correction changes only the
first capability paragraph of `contact-and-safety.md`: the generic preview and
independent released POSIX recovery interface are now explicitly separated;
read-only reconciliation does not inherit recovery-write exclusion conditions.
The parent separately refreshes affected accepted route evidence after review.

## Reproducer and fixed input

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_acceptance_boundary_rebuild.py -v
PYTHONDONTWRITEBYTECODE=1 python -B tests/test_acceptance_boundary_rebuild.py --replay
```

The test module holds complete literal inputs and independently handwritten
expected outputs. It does not copy expected results from runtime constants or
assert that a few keywords establish acceptance. `--replay` prints both complete
case projections. Tests compare entire converter/compiler previews, every public
workflow Decision field, complete State and snapshot outputs, complete
inventory CLI JSON, and the exact approval requests used by the fixture.

All modules and literal fixture definitions load before the no-I/O scope. Within
conversion, parsing, matching, compilation, workflow evaluation and the in-process
`workflow-status` call, fail-fast sentinels replace these APIs:

- `builtins.open`, `io.open` (including Path.open) and `os.open`
- `socket.socket`, `socket.create_connection`, `socket.getaddrinfo`,
  `socket.gethostbyname`, `socket.gethostbyname_ex`, `socket.gethostbyaddr`
- `subprocess.Popen`, `os.system`, `os.popen`

Every successful replay additionally asserts each sentinel was never called.
These are test-level traps for the reviewed pure paths, not an OS network filter,
a universal detector of arbitrary native extensions, or an assertion that other
processes are isolated. Output redirection for retaining the replay is test
infrastructure outside the pure runtime scope.

## ENV-T79: syntax, matches and deferred actual traffic

### Literal source and complete output

The provider input is exactly:

```yaml
payload:
  - 'DOMAIN,claude.ai'
  - 'DOMAIN-SUFFIX,anthropic.com'
```

It has a final LF. These are literal domain strings read as data, not resolved
names or an asserted complete production allowlist. The synthetic binding
computes SHA-256 over the complete bytes and labels the input user-supplied,
fixture-only and candidate. Dates and metadata do not prove source freshness.

`convert_rule_format` uses explicit
`mihomo/1.19.32/provider-classical-yaml` and
`sing-box/1.12.0/source-rule-set-json-v1` profiles. The exact output, also with
one final LF, is:

```json
{"version":1,"rules":[{"domain":["claude.ai"]},{"domain_suffix":["anthropic.com"]}]}
```

The complete converter preview remains `converted_predicates_only`, two records,
one exact and one suffix, `apply_supported=false`,
`authorization=not_required_for_offline_conversion`, `native_acceptance=not_run`,
`effective_priority=not_established`. Authenticity/freshness/independent-source
status remains not established. Canonical lowercase ASCII predicate scope is
explicit; no general engine-ingress normalization is inferred.

### Separate production matching calculation

The replay calls the existing compiler's `_overlap` helper with each candidate
represented as an exact-host selector. This is a production selector-intersection
calculation, not an independently invented matching engine and not actual client
traffic. The private helper is explicitly identified rather than represented as
a new public API.

| Candidate host | Exact `claude.ai` intersects | Suffix `anthropic.com` intersects |
|---|---|---|
| claude.ai | true | false |
| www.claude.ai | false | false |
| notclaude.ai | false | false |
| claude.ai.invalid | false | false |
| anthropic.com | false | true |
| api.anthropic.com | false | true |
| deep.api.anthropic.com | false | true |
| notanthropic.com | false | false |
| anthropic.com.invalid | false | false |

The reverse-operand test separately verifies suffix apex/subdomain positives and
textual-lookalike negatives. No hostname query is part of either calculation.

### Public compiler path and preserved uncertainty

The public `compile_rules_extension` receives complete literal base and extension
bytes from the test. The selected rules are `DOMAIN,claude.ai,approved-group` and
`DOMAIN-SUFFIX,anthropic.com,approved-group`. The sole change is the empty
prepend list becoming:

```yaml
prepend: ['DOMAIN,claude.ai,approved-group', 'DOMAIN-SUFFIX,anthropic.com,approved-group']
```

The rest of the extension bytes, including its comment and empty append/delete,
are compared exactly. The protected `rescue.invalid` base rule remains separate.
The complete known overlap list is asserted:

1. rule-a with base index 1, `DOMAIN-SUFFIX,claude.ai,old-group`
2. rule-a with base index 3, `MATCH,DIRECT`
3. rule-b with base index 2, `DOMAIN,api.anthropic.com,old-group`
4. rule-b with base index 3, `MATCH,DIRECT`

The synthetic semantic request deliberately contains optimistic declarations so
that this narrow compiler can be exercised. They do not become observations:
public output still says `candidate_only_blocked`, `native_acceptance=not_run`,
`apply_supported=false`, and caller-declared protected coverage. The complete
blocker list retains effective priority, base/group graphs, protected coverage,
later merge/script effects, native adapter, version, native acceptance and
pending action authorization.

Changing `facts.rules.first_match_verified` to `unknown` produces
`RULES_FIRST_MATCH_VERIFIED` in the semantic plan and
`SEMANTIC_PLAN_BLOCKED` from the candidate compiler. This is an **unknown declared
first-match/priority prerequisite**, not evidence about a client connection.
The replay keys are `unknown_declared_priority_*` to preserve that distinction.

### Actual hits are explicitly later checks

The host fixture supplies `claude-domain-actual-hit` as its applicable
PC-G2-unauthenticated requirement. It is **not automatically inferred from the
domain syntax**. This illustrates the actual host contract documented in the
phase guidance: the host must identify applicable real-client checks.

A wholly synthetic fixture supplies a target-manual preparation declaration,
synthetic adapter support declaration, and a fixture-only approval callback to
exercise a scheduling-allowed PC1 branch. The resulting complete Decision has
`pending_checks=['claude-domain-actual-hit']`, `enforcement_level=workflow_guard`
and `executes=false`. It executes no handoff or client check. Its approval
request is compared exactly. This fixture does not establish actual PC-G1,
human consent, native support, or permission to make a real request.

Supplying a synthetic pass for that pending hit cannot satisfy PC-G2: the next
transition returns `allowed=false` with
`EVIDENCE_REQUIRED:claude-domain-actual-hit`. Thus local syntax/intersection and
candidate success do not become an observed hit. Runtime match/route evidence
must be collected later under its real scope; this replay has none.

### Clause-by-clause L conclusion

- “只做离线语法/匹配模拟”: actual existing conversion/parsing, compiler intersections,
  positive/negative host cases and full candidate construction run in memory
- “不为验证规则主动查询目标域名”: literal Claude-domain inputs traverse those paths
  with all listed file/DNS/socket/process sentinels unused
- “实际命中仍标后验”: the applicable host-declared actual-hit check remains pending
  after permitted scheduling, and a synthetic hit is rejected as completion

Supplementary failures preserve the same offline boundary: unsupported ASN both
before and after valid source members fails atomically with
`UNREPRESENTABLE_MATCH`; cancellation returns `CANCELLED`; protecting an
intersecting base rule returns `PROTECTED_RULE_PRIORITY_CONFLICT`. These are
boundary controls, not additional original-case acceptance counts.

## ENV-T90: complete exposed scope

### L output and behavior

The fixture contains two explicitly synthetic adapter declarations so an allowed
local planning branch can be tested. `supported_scopes` is the exact supplied
fixture list, not a discovered or real capability inventory. Full Decision
comparison includes that list, allowed/gaps, pending checks, enforcement level
and executes. The tests never replace production execution gates.

| Stage | Complete state/decision meaning asserted |
|---|---|
| New guard | precontact/closed, no authorized scopes, observed contact not measured; runtime permissions not restorable |
| Allowed local plan | scheduling permitted even with interview gaps; `workflow_guard`, `executes=false`; exactly one scoped fixture action approval |
| Browser/search/MCP/shell/Computer Use/connector contact proposals | each explicitly host-classified as Claude contact; unsupported scope + closed/out-of-scope gate + missing preparation evidence; no approval callback or I/O |
| After all denials | complete initial snapshot remains unchanged |
| Observed prior contact | gate revoked and history observed, without claiming prevention or erased history |
| Resume from saved open/authenticated state | fresh precontact/closed gate; history is previous_contact_reported; saved permissions do not reopen it |
| inventory CLI workflow-status | status partial, default-new-process-only scope, transition unavailable, no changes and closed PC0; complete boundary text rejects authenticated-consent, host/OS-approval, saved-grant, OS-isolation, controller and readiness inferences |

The surface names are fixture labels, not implemented browser/search/MCP hooks.
The host must classify and mediate its own actions. These tests show the declared
workflow path cannot authorize those inputs in PC0; they do not prove that an
unmediated tool, restored tab, unrelated app or malicious caller is intercepted.
Denial, cancellation, timeout, boolean True and absent replies all fail exact
approval; missing host/OS permission also blocks. Every such Decision continues
to report workflow-level scheduling without execution.

### C: active instruction and source-context review

The Skill entry actively links the contact policy before each tool operation;
network and repair references are linked from the same live entry. The following
review assesses the actual sentences and their effect, not keyword presence.
The file hashes below identify their full context.

| Active location | Sentence/clause meaning reviewed | Relationship to the complete original condition |
|---|---|---|
| SKILL opening capability paragraph | Default CLI is limited; optional libraries/transactions require their own trusted host, scope and live authorization | Does not imply an isolation layer merely because a capability is packaged |
| SKILL start step 1 | Actual execution host and target are separate; cloud-shell facts cannot certify a user's Mac | Prevents host capability substitution |
| SKILL start step 5, first two clauses | Contact policy applies before each tool action; PC0 forbids target contact/client startup/login/subscription pages | Instruction-level scheduling rule is active, not an unused reference |
| SKILL step 5, remaining clauses | Public docs, DNS, HEAD, version commands and delegated Claude tools are not exceptions; current facts remain pending | Alternative tool names and supposedly harmless requests do not silently expand contact scope |
| SKILL step 6 | Only scoped available checks; missing capability is unknown; independent repair cannot bypass permissions or PC0 | No permission bypass is created by an unsupported built-in |
| SKILL step 7 | Check results are scoped; inventory completion is not PC-G1; offline tests do not prove isolation | Explicitly rejects the overclaim targeted by ENV-T90 |
| Contact policy summary | Names workflow constraints and explicitly denies whole-machine isolation | Correct declared enforcement level |
| Contact policy capability paragraph, generic-preview sentence | Generic preview does not execute probe, production apply or online verify | Describes that entry-point scope, not all separately released libraries |
| Same paragraph, recovery sentences | Independent POSIX reconcile is read-only; rollback/restore-prepared have their own checks; exclusion/operation approval are required for writes, not read-only reconciliation | Corrects the older overly broad recovery wording without making offline investigation depend on a write gate |
| Same paragraph, limits sentence | Recovery does not open native repair or contact gates or prove Windows/app/routing behavior | File restoration is not network isolation or native effect evidence |
| Same paragraph, remaining sentences | Authorization alone cannot invent an adapter; independent Agent repair remains scoped, reviewed and separately permitted; no callback/native/denial bypass | Allows practical authorized repair while retaining the actual boundary |
| Contact policy workflow paragraph, sentence 1 | Controls are workflow controls, not a firewall | Directly establishes the level the runtime also exposes |
| Same paragraph, sentence 2 | Unrelated apps, restored tabs and user actions are not stopped; prior contact cannot be erased | Explicit uncovered-browser/process/history scope |
| Same paragraph, sentences 3–4 | Record known history; strict no-egress remains blocked without a tested technical boundary | Unknown coverage is not silently upgraded to hard isolation |
| Contact PC0 bullet | Lists target web/API/auth/download/status/telemetry/docs plus DNS, search-mediated fetch, HEAD, ping, client commands/extensions/delegation; installed metadata may be read without execution | Search and indirect tool access are workflow obligations; no claim these tools are technically filtered |
| Contact PC-G1 bullet | Actual target/profile/path evidence and missing controls are required; imported assertions/synthetic tests cannot close the gate | Explains why synthetic declarations in these tests are not real preparation evidence |
| Contact PC1 bullet | Exact first-contact handoff and host policy remain required; built-in preview does not execute the handoff; installation can contact services | Allowed scheduling is not execution or OS enforcement |
| Contact PC-G2/PC2 bullets | Real-client evidence is separate; authenticated checks may be deferred; login/payment remain separate | Supports the later actual-hit requirement and prevents inferred completion |
| Contact target paragraph | Phones, host, guest, remote server, browser profile and client evidence stay separate | No cross-target isolation/capability inference |
| Contact permissions paragraph | Answers/plan acceptance/host authority/OS privilege/contact/payment differ; silence/default/cancellation do not confer any; user approval cannot override host policy | Names the external host boundary instead of pretending the Skill replaces it |
| Contact read/probe paragraphs | Bind minimal authorized reads; no scans/arbitrary scripts; local GET may cause work; neutral probes need precise endpoints and cannot expand via redirects/subresources | Does not treat indirect network effects as offline or universally controlled |
| Contact reporting paragraph | Proposed/applied/verified differ; independent action does not upgrade built-in/native status; withdrawn requests cannot be undone | Honest effect and enforcement reporting |
| Contact persistence/resume paragraphs | Saved records are not renewed permission; relevant target/history retained; dependent actions stop at actual missing prerequisites | State history and current authority stay distinct; workflow resume reset is not a claim historical contact vanished |
| Accounts/payments operational preamble | PC0 explicitly covers browser, search, MCP and shell access to target docs/status/auth/payment pages; historical links are not permission | Confirms MCP/search/browser are included in Agent obligations, not implied OS coverage |
| Network layered-interpretation child-process sentence | Variable inheritance does not prove adoption; MCP/interpreters/plugins/background/update paths need their own later evidence | Explicitly rejects process-tree coverage by assumption |
| Agent remediation loop, steps 2, 4–7 | Static configuration is not actual traffic; action lists are recommendations; exact changes/authority and later same-path retesting are separate | Prevents tool output/candidates from becoming effective-network proof |
| Agent remediation converter paragraphs | Conversion stays in memory, does not fetch providers/run engines; semantics are canonical and source order is not policy priority; subsequent scope/approval/readback are separate | Accurate offline interpretation boundary for ENV-T79 and no hidden execution claim |
| workflow_guard module contract and Decision | Host assertions and callbacks are not signatures/consent/sandboxing; decisions schedule only; enforcement field stays workflow_guard and executes stays false | Implementation agrees with active guidance and public output |
| inventory_cli boundary contract | Terminal responses and caller identities are not authenticated consent or OS authority; no isolation or readiness claim | Public CLI presentation exposes its actual limits |

Original D-ENV §18.7 separately defines workflow_guard, script_guard and a
verified_execution_boundary, with E35 as its historical source pointer. This
review compares that supplied design to this implementation; it does not fetch
E35 or claim to have verified current host-product networking. A script guard
cannot stand in for an OS boundary, and even a separately tested native boundary
would apply only to its tested platform/protocol/process scope. The original
request here is to state the real level, not to build or demonstrate isolation.

Conclusion: the complete ENV-T90 statement has matching L output and active C
content support. The scope of any eventual ledger acceptance is that truthful
workflow-boundary behavior, not arbitrary Agent compliance or OS isolation.

## Results and reproducibility

- Eight exact boundary test methods passed, zero skipped
- 183 combined boundary/workflow/contact-epoch/converter/compiler/inventory tests
  passed, zero skipped
- Two independent `--replay` runs are compared byte-for-byte before freezing;
  final digest and complete command logs are retained with the owned receipt
- Initial fixture-authoring run failed because of a mistaken request-schema
  literal, mistaken existing error-code expectation, and an incomplete expected
  CLI object. They were corrected against the existing contracts; no production
  behavior was changed or existing assertion weakened. That log is retained and
  is not represented as a preexisting runtime regression
- Parent performs full aggregate, synthetic Node, compilation and reproducible
  package checks on the integrated final batch. Those results must be recorded
  separately; this page does not infer them from the focused tests

## Reviewed source hashes

The evidence page's own hash is recorded externally to avoid a self-reference.
When a pinned file changes, re-review the affected clauses and replay outputs;
updating hashes alone does not renew acceptance.

| File | SHA-256 |
|---|---|
| `tests/test_acceptance_boundary_rebuild.py` | `b5604c118e9c11fea9d03c19e75efdae4acb53f7bb0df3bd2ac4db38842621fd` |
| `skills/claude-guardian/scripts/rule_format_conversion.py` | `879b392f2228b6eb582af45c22b56b3aef088b087686f2ef3b189242476a02b1` |
| `skills/claude-guardian/scripts/rules_extension_plan.py` | `15c3b620d2b63601794100af8685df1c3f515e6b0fe99272a4beb9649332d0d1` |
| `skills/claude-guardian/scripts/config_edit_plan.py` | `d50499f5a92508a9a20dd7e6193f7b2a320bba06bc8fd8ba5eb93ec2b39259dd` |
| `skills/claude-guardian/scripts/remedy_plans.py` | `d9f1faa146681adb74c47a549b7efec1734d5c78d266a7a4c4285c7973712b09` |
| `skills/claude-guardian/scripts/workflow_guard.py` | `68aa99db78a70d0387a3901d4f3ba25a9c4dcee19fa2ff3a584706419ccfeed0` |
| `skills/claude-guardian/scripts/inventory_cli.py` | `e0c5fc46800e5838e9d40bc8271c8ca1e1da093c85055ed85256ddd57a1cb3b1` |
| `skills/claude-guardian/SKILL.md` | `8cdec703516570679f497c3b5f417dfcbc60ca8bcf14fbbde093afc506694490` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `skills/claude-guardian/references/network-and-remedies.md` | `3b2eb1ea88b16656558e9327f42470dd371114401995d688994783f686085120` |
| `skills/claude-guardian/references/accounts-and-payments.md` | `cf16e85bfbe2a9ea6a2cc51d88b9f82c85eab29248f289c3ae3990c15cda6cb9` |
| `skills/claude-guardian/references/agent-remediation.md` | `363fdee6fa226545f0b03ebd14e6c311ac7582211800e78f94ffd6f3ad173fb1` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `docs/implementation-tracker.md` | `8056f8d999a73a66dcdb7960dd724cd9e0c7404d769b00650e6936f21703fd50` |


### Twelfth-batch grant-invalidation preservation review

The workflow-only grant invalidation and review-epoch change was independently
rechecked against the complete original ENV-T79/ENV-T90 conditions. All eight
unchanged exact fixtures pass and their full replay remains
`b014fc2e16015a9ecd07b2f95460ab5fead21b625fd882eb01d8031042325581`.
The 98 combined checks passed. Only the reviewed workflow implementation pin is
refreshed; offline-domain semantics, executes=false, workflow_guard enforcement
and absence of native/OS isolation proof are unchanged.


### Fourteenth-batch preservation review

The explicit package addition and bounded pure policy-conversion guidance were
independently reviewed against the original conditions on this page. All 23
source/package checks, nine installed-package checks, eight ENV-T79/90 exact
fixtures and 26 conversion tests passed. The guide example also ran from the
extracted ZIP with exact expected output and unused I/O sentinels. Existing
source evidence code and fixtures are unchanged; the ENV-T79/90 replay remains
`b014fc2e16015a9ecd07b2f95460ab5fead21b625fd882eb01d8031042325581`.
Only the reviewed file pin is refreshed; no native or automatic execution claim
is introduced, and full ENV-T40 remains pending.


### Fifteenth derived-reference preservation review

On 2026-10-18 the sanitized case reference and its two active links were
independently reviewed against this page's full original conditions. Existing
case replays remain unchanged. The host-library/CLI clarification grants no new
capability or authorization; historical single-device observations do not become
current native evidence. Only reviewed affected file pins above were refreshed.
The review reran 182 relevant offline tests and 145 interview tests with no skips,
and compared five complete case replay outputs and both release archives.
