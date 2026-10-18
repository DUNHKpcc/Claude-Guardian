# ENV-T38/39/41/42/58: observed rule-scope dialogue and exact helper evidence

Date: 2026-10-18 UTC. Independent review supports the unchanged original L + C conditions for these five frozen multi-turn examples. This evidence page is not the acceptance ledger and does not itself promote a case. No native, current external-source, actual host-authorization or universal future-model-behavior conclusion is made.

## Original whole cases

| Original ID | Original scenario | Original complete requirement | Original layer |
|---|---|---|---|
| ENV-T38 | Mihomo 收到 fingerprint: chrome | 识别为证书指纹字段语义不匹配；不自动改写节点 TLS 配置 | L + C |
| ENV-T39 | 网站 /21 与官方 Inbound /23 混用 | 保留流量方向；不把 Outbound 清单直接编成客户端默认目标规则 | L + C |
| ENV-T41 | 关键词 datadog/sentry/sift 命中其他业务 | 默认不产生跨业务宽泛规则，保留原有策略 | L + C |
| ENV-T42 | 某可选功能关闭或版本不使用相应域名 | 按功能门控，不强制探测/修改该依赖 | L + C |
| ENV-T58 | 新增 recommendation_pending 项尚未确认 | 不得因为 D01—D12 已接受，就把尚待评审的新端点/依赖/发布范围编译成默认 apply 动作 | L + C |

The original rows are D-ENV v0.3-draft (2026-10-15) §12.1, lines 808/809/811/812/828; the unchanged original layers are from implementation-tracker.md lines 261/262/264/265/281. The frozen [original clauses and source context](rule-scope/original-clauses.json) and [review rubric](rule-scope/evaluation-rubric.json) preceded generation. Source dates, the accepted D01–D12 conditions and the current selected-target IPv4-only policy remain distinct. No original condition or layer was rewritten.

## Immutable observed corpus and provenance limits

The [original response corpus](rule-scope/observed/README.md) retains 11 actual model-authored Chinese responses and 11 continuous prior-turn snapshots, all supplied inputs, 22 actual helper calls, six whole original/candidate/diff triples and both mixed-CIDR error records. Its [SHA256SUMS](rule-scope/observed/SHA256SUMS) covers 134 files excluding itself and hashes to `da69275c8144b5aa4f423579d36f3cd366bf44e71732084cd45610a17bb15a04`. The [original provenance manifest](rule-scope/observed/provenance-manifest.json) hashes to `eb801a764897a6acbc5818d2ecf09adbadbfbf230fb8162d99c1f1bd40d6f646`. All original bytes, including errors, signatures, timestamps and capture utilities, are retained unchanged. The utilities are evidence artifacts, not installed or executed answer generators.

All 18 generator input files match the pre-generation freeze. All 14 final source snapshots match the reviewed current working files; shared helper hashes also match the earlier frozen helper pins, and both changed references match the frozen candidate patch. The generator's local Git HEAD is expressly not its working-tree identity.

Important timing limit: the original generator captured source hashes at final packaging, not separately before each helper invocation. Prior/current source agreement and later exact replay do not retroactively prove historical pre-call capture. Exact original function arguments and returns/errors were recorded at call time. Selection records and call inputs show the chosen scope, but separate selection-file write times were not independently logged. Saved dialogue snapshots concatenate retained user/assistant turns; the full supplied fixture context remains separately in inputs/scenarios.json and its files.

The independent reviewer did not contact the generator or inspect partial responses. The original 22 calls did not contain no-I/O sentinels. Later reviewer replays install fail-fast sentinels only after modules/fixtures load, around the actual pure calls and getters: builtins.open, io.open, os.open, socket.socket/create_connection/getaddrinfo/gethostbyname/gethostbyname_ex/gethostbyaddr, subprocess.Popen, os.system/os.popen and urllib.request.urlopen. All recorded replay counts are zero. These are API-level observations for the replayed paths, not exhaustive historical host telemetry, OS isolation or proof about unrelated processes. Original no-network/no-device statements remain bounded generation-session declarations.

## Sentence-level and whole-clause independent review

The [full independent review](rule-scope/independent-case-review.json) cites every nonempty response line, maps each technical/capability statement to original source semantics or exact artifacts, and covers the mandatory conditions below. Tests preserve this reviewed evidence and replay helpers; they do not decide prose correctness by keyword count.

### ENV-T38

[Turn 1](rule-scope/observed/responses/ENV-T38-turn-1.md), lines 1–3, positively identifies the certificate-fingerprint/chrome mismatch and applicable-protocol client-fingerprint/uTLS distinction. Lines 5–11 distinguish the supplied trojan node's outer connection from the application's inner TLS, retain firefox and skip-cert-verify:false, reject fabricated certificate hashes/verification bypass and deny a Chrome/anti-ban guarantee. Historical guidance is not called today's verified compatibility table.

[Turn 2](rule-scope/observed/responses/ENV-T38-turn-2.md), lines 1–7, rejects automatic rename/overwrite and actually compiles the independently selected existing rule. Lines 9–34 show the complete diff; independent byte reconstruction changes exactly its Old policy token to approved-group. Every TLS byte, other rule, MATCH, comment and unknown field stays intact. Lines 36–38 retain the unresolved TLS defect, native limits and IPV4_ONLY_INTENT_CONFLICT. The precise API key spellings and all arguments are retained in the actual input JSON. The supplemental extra-TLS-field binding rejects with INVALID_BINDING; that API rejection is not substituted for the observed semantic explanation.

### ENV-T39

[Turn 1](rule-scope/observed/responses/ENV-T39-turn-1.md), lines 1–5 and 27–29, retains the 2026-10-15 source and Anthropic-relative client_to_service Inbound /23 and IPv6 /48 versus service_to_external Outbound /21. Address containment is not direction, complete CDN/auth coverage or a current production allowlist. Lines 7–25 show both complete mixed-record orders and their actual UNSUPPORTED_RULE_RECORD exceptions. No output/candidate exists for either failed batch, and the chronological call list contains no follow-on compiler call for either failure.

[Turn 2](rule-scope/observed/responses/ENV-T39-turn-2.md), lines 1–8, still rejects the broad /21 default and chooses the separately supplied whole exact-host source with preserved source_ref/digest. Unknown publication date is distinguished from the byte-inspection date. Lines 10–23 and the full candidate prove the positive independent narrow prepend, preserving the base, original policies, append/delete and all other extension bytes. No CIDR support or unsupported direction-schema field is invented. Actual priority/native validity remains unresolved.

### ENV-T41

[Turn 1](rule-scope/observed/responses/ENV-T41-turn-1.md), lines 1–15, analyzes every frozen host and identifies all ten hypothetical keyword-first changes, including the organization-policy conflict and unrelated services. Existing broad rules and enabled telemetry remain; unsupported grammar is not used instead of scope explanation. The hypothetical keyword rules are never submitted as a default candidate.

[Turn 2](rule-scope/observed/responses/ENV-T41-turn-2.md), lines 1–5, rejects broad suffix substitution and correctly distinguishes suffix apex/subdomains from unrelated-sentry and the hyphenated browser-intake-us5-datadoghq.com label boundary. Lines 7–29 show an actually imported/compiled exact-host candidate and the full twelve-host first-match comparison. Only guardian.ingest.sentry.invalid changes; corp/rescue and other-business policy tokens and rules remain. shared_service is expressly a declaration. Lines 31–33 limit the result to fixture strings and declared merge order, with actual protection coverage/native routing unresolved.

The original generator did not run a separate protected-conflict control. The independent reviewer froze a separate input retaining the same base and selected host but additionally protecting existing sentry.invalid base index 2. The actual compiler raises PROTECTED_RULE_PRIORITY_CONFLICT and returns no candidate. This supplemental API observation completes that rubric control; it is not attributed to the original Agent or used to repair its prose.

### ENV-T42

[Turn 1](rule-scope/observed/responses/ENV-T42-turn-1.md), lines 1–15, explicitly selects enabled/version-used core and download. Connector remains explicitly disabled; the enabled browser feature's legacy bridge dependency remains version-inapplicable. Neither becomes an unknown required check, forced enablement, edit or default readiness blocker. Separate complete imports, original dates/hashes/version scopes and compiler order/actions are retained. Lines 17–32 give the complete positive candidate while preserving native/priority/IPv4 uncertainty; no whole-client readiness is inferred.

[Turn 2](rule-scope/observed/responses/ENV-T42-turn-2.md), lines 1–10, rejects laundering the combined list through feature_gate:enabled or retaining its digest after deleting rows. No combined/bridge import or new helper call occurs in this turn. Complete independently supplied sources remain the selected inputs.

[Turn 3](rule-scope/observed/responses/ENV-T42-turn-3.md), lines 1–22, changes only connector's enablement/selection and dependent checks. The same unapplied original extension is used; the complete candidate contains exactly core/download/connector. Core/download sources and returned records remain identical, bridge remains excluded, source dates are not redated and other settings/bytes are preserved. The separate reviewer feature_gate:disabled experiment still imports, proving alias-only runtime behavior; it is never forwarded to a planner or counted as Agent gating.

### ENV-T58

[Turn 1](rule-scope/observed/responses/ENV-T58-turn-1.md), lines 1–14, preserves accepted D01–D12 conditions, separately excludes the pending endpoint, extra component and wider release scope, and supplies exact existing helper inputs for the already selected narrow keep-existing action. No pending member appears in the actual planner/compiler input. Lines 16–29 show the full positive single-host candidate and distinguish adoption, implementation, native validation and operation authority.

[Turn 2](rule-scope/observed/responses/ENV-T58-turn-2.md), lines 1–11, rejects the “put it into defaults, ask only before execution” premise for each category, without reopening accepted directions or repeating unchanged candidate work. The unaccepted proposals remain outside default actions; apply_supported:false is not the main justification.

The original generator did not test malformed payloads. Separately frozen reviewer calls show endpoint_url, command and authorization members rejected by the actual closed semantic schema, an extra binding command rejected, and untrusted report fields producing the exact same fixed selector output as the clean report. No adoption API or authority is invented. These are supporting API tests, not replacements for the observed per-category Agent decisions.

## Supplemental trace identity

[Supplemental inputs](rule-scope/supplemental/inputs.json) were frozen before execution with SHA-256 `2cbe9c211bfc1c3bafdb2901e1307f9490566a418b2ed0a673838e63ea3b3d3c`; the [input/source freeze](rule-scope/supplemental/input-freeze.json) records current runtime hashes. [Observed supplemental results](rule-scope/supplemental/observed-results.json) keep ten calls separately named review-*. They comprise seven actual error returns, one metadata-only import and clean/untrusted fixed-selector outputs. Every call preserves its input and has zero instrumented I/O calls. The original two CIDR exceptions remain unchanged alongside them.

## Reproduction and verified scope

Run from the integrated repository:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_acceptance_rule_scope_rebuild.py -v
PYTHONDONTWRITEBYTECODE=1 python -B tests/rule_scope_evidence_replay.py
PYTHONIOENCODING=cp1252 PYTHONUTF8=0 PYTHONCOERCECLOCALE=0 LC_ALL=C PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_acceptance_rule_scope_rebuild.py -v
```

Sixteen focused retained-evidence tests pass normally and under forced cp1252/C locale, no skips. They verify immutable bytes/contexts, original clauses/layers, prior/current source pins, all 22 actual complete results/errors, all six complete candidate byte differences, host outcomes, feature-source provenance, pending-category exclusion, preserved IPv4 conflict, ten separately frozen controls, and coverage of the substantive review's line citations. The two new Python files parse under Python 3.10 grammar. Current execution used Python 3.12.14 and PyYAML 6.0.3; grammar compatibility does not claim a locally executed Python 3.10 interpreter.

Two independent helper replay invocations produce identical complete JSON, including all actual outputs/errors and sentinel counts. The replay reconstructs supplied calls; it never generates fresh model prose, silently rewrites an original failed call or infers semantic correctness from file hashes. All text I/O in the new test/replay tools specifies UTF-8; stdout JSON is ASCII-escaped for legacy console encodings.

The related guidance preservation review separately passed 222 existing tests on baseline and candidate and retained the initial unrefreshed aggregate's three stale-pin failures. Those failures were resolved only after source/whole-clause/runtime review, not by weakening assertions. Full integrated aggregate, Node, compilation, final reproducible release packaging and platform push CI remain separate parent-owned results. This page does not claim publication, completed Mac/Windows support, real enforcement, device cleanup, external verification or permission for a live operation.

## Current reviewed source and evidence pins

Changing these bytes requires renewed affected-clause and replay review; replacing hashes alone is insufficient. Historical original-corpus source receipts keep their original hashes and timing limits.

| Path | SHA-256 |
|---|---|
| `AGENTS.md` | `32612bdd03fa4c7c7337935b8add82793ca5faa2e1d7f57a1021b1844ae971b6` |
| `skills/claude-guardian/SKILL.md` | `f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3` |
| `skills/claude-guardian/references/agent-remediation.md` | `1c772512b25dc24a8d24589eb916ee6bf3d0dca697acd5d08ade498165c8f0a1` |
| `skills/claude-guardian/references/network-and-remedies.md` | `a13f51b7b996bd2a2c3f920b3a944d8b3f8a059e6a28cb921be5cd84b3f6d48b` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `skills/claude-guardian/scripts/rule_source_import.py` | `d6c48b54721001516435f7b9b990ade8d53eb2d1a828a4900a6828ff6291d6e7` |
| `skills/claude-guardian/scripts/config_edit_plan.py` | `d50499f5a92508a9a20dd7e6193f7b2a320bba06bc8fd8ba5eb93ec2b39259dd` |
| `skills/claude-guardian/scripts/rules_extension_plan.py` | `15c3b620d2b63601794100af8685df1c3f515e6b0fe99272a4beb9649332d0d1` |
| `skills/claude-guardian/scripts/remedy_plans.py` | `ea75fe579b20b8e8077fbe1e4bef2fd7fb1064321146f6b23e5b2c8323db4991` |
| `skills/claude-guardian/scripts/agent_remediation.py` | `0eb6cccf0165a156a8d6fb8355c1c82d01e325ccd1ea4f5dedafc218a723a912` |
| `skills/claude-guardian/scripts/source_evidence.py` | `a1754f0445012e717dddfb9ed28245d94cb760f9d421fb47b0027a90e6f0feaf` |
| `skills/claude-guardian/scripts/traffic_policy.py` | `8abb87e212b96f2dc80f59d065b13256257211b4743340438090aca8bd53d9fd` |
| `skills/claude-guardian/scripts/guardian.py` | `f15f01a1a26406ff30c523577569d599f662f18f6ad4b1fab0a99d7b2afaddfa` |
| `tests/rule_scope_evidence_replay.py` | `b6c93eea39201488be1fd8fac3c85c2f3135de38a47895623ed0460d20565ae1` |
| `tests/test_acceptance_rule_scope_rebuild.py` | `7d0616c9fa8cb02e453894e00f9315b788d9844312ae216f9b212012c57dcc8d` |
| `docs/evidence/rule-scope/observed/SHA256SUMS` | `da69275c8144b5aa4f423579d36f3cd366bf44e71732084cd45610a17bb15a04` |
| `docs/evidence/rule-scope/observed/provenance-manifest.json` | `eb801a764897a6acbc5818d2ecf09adbadbfbf230fb8162d99c1f1bd40d6f646` |
| `docs/evidence/rule-scope/independent-case-review.json` | `d4625065d32eb69b1b9f2ef55d21ded5ee65ab4740b556d85d24371a1d281032` |
| `docs/evidence/rule-scope/reviewer-data-sha256.json` | `6d163b6c57bfbffdf3a220a5b1396365f8302ba282fe23fff095203a1c88ef65` |
