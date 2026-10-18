# Ordered policy conversion: bounded ENV-T40 logic evidence

Date: 2026-10-18 UTC. Evidence layer: **L only** in this page. No native engine
execution, installed-version check, real configuration write, network probe,
Claude contact, or ENV-T40 acceptance is claimed.

## Requirement and scope

Original D-ENV v0.3 §12.1 ENV-T40: 纯域名/规则提供方/主规则/JSON 格式转换;
不可表达的 ASN/匹配/动作语义明确报错，不静默丢失. The tracker requires **L + R**;
R means controlled write and restoration, not a regression-test count.
D-ENV §5.7, §5.8 and D07 remain binding: source/version/feature provenance,
label-boundary suffix matching, action and priority preservation, protected
surrounding configuration, conflict review, references, ownership/persistence,
native validation, actual rule hits and refresh verification.

`rule_policy_conversion.py` is a separate pure API. The existing
`rule_format_conversion.py` remains actionless; `rule_source_import.py` retains
its single-group/duplicate-selector restrictions. Neither was edited for this
slice. The API supports only the two cross-engine directions:

- `mihomo/1.19.32/main-rules-yaml`
- `sing-box/1.12.0/route-rules-json`

`convert_policy_rules(source_bytes, source_profile, target_profile,
ordered_rule_refs, source_binding, outbound_bindings, *,
source_no_match="defer_to_enclosing_configuration",
target_no_match="defer_to_enclosing_configuration", max_seconds=5,
cancelled=...)` returns a frozen private result or a fixed non-sensitive error.
The no-match keywords are fragment contracts, **not discovered enclosing fallback
properties**. Any other declaration fails. No MATCH or final rule is invented.

The source binding is the existing strict `guardian-rule-source-binding/0.1`
contract; the full actual source SHA-256 must match its declared hash. Metadata
is preserved as declared, not treated as proof of authenticity or freshness.
Explicit ordinary-outbound maps must be bijective, cover precisely all used
source labels and contain exactly these six fields: source_label, target_label,
source_kind, target_kind, source_finality, target_finality. Both kinds must be
ordinary_outbound and both finalities terminal_for_tcp_udp. These include the
caller-declared group/member behavior and remain **declared_unverified**.
Names do not prove adapter kind, UDP support or terminal behavior.

## Pinned semantic basis

The supplied 2026-10-18 ordered-policy design and pinned-rule-semantics research
were read in full. Links here identify their primary-source basis; this coding
slice did not newly fetch, install or execute the engines. Targets are audit
pins, not latest-release or installed-version claims:

- Mihomo v1.19.32, commit `88dcbf7f1614a67c3b36b848ee3592dfa92ada36`
- sing-box v1.12.0, resolved release commit
  `2dcb86941f5db01bbe296acae555a3b1f38c0441`; research retrieved tag-addressed
  source and resolved the commit separately, without claiming raw SHA URL reads
- sing domain matcher dependency v0.7.0-beta.2

[Exact match](https://raw.githubusercontent.com/MetaCubeX/mihomo/88dcbf7f1614a67c3b36b848ee3592dfa92ada36/rules/common/domain.go)
and [suffix match](https://raw.githubusercontent.com/MetaCubeX/mihomo/88dcbf7f1614a67c3b36b848ee3592dfa92ada36/rules/common/domain_suffix.go)
versus sing-box [DomainItem](https://raw.githubusercontent.com/SagerNet/sing-box/v1.12.0/route/rule/rule_item_domain.go)
and the [domain matcher](https://raw.githubusercontent.com/SagerNet/sing/v0.7.0-beta.2/common/domain/matcher.go)
support the restricted canonical-lowercase-ASCII predicate model. Exact matches
only equality; suffix matches the apex or dot-separated descendants. Uppercase,
Unicode, root dots, leading-dot suffixes and wildcard patterns are rejected;
existing lowercase ASCII A-labels remain opaque. Noncanonical candidate hosts
are outside-profile in the test oracle, not a successful no-match comparison.
This deliberately does not claim that actual inbound metadata is canonical.

The sing-box [constructor](https://raw.githubusercontent.com/SagerNet/sing-box/v1.12.0/route/rule/rule_default.go)
and [matching logic](https://raw.githubusercontent.com/SagerNet/sing-box/v1.12.0/route/rule/rule_abstract.go)
support OR expansion of pure domain/domain_suffix arrays. Expansion is contiguous
in object-key/list order with the same action. Extra conditions, including false,
empty or default-valued extra fields, reject rather than being dropped.

The exact exclusion table is DIRECT, REJECT, REJECT-DROP, COMPATIBLE, PASS,
PASS-RULE, GLOBAL. The [pinned configuration parser](https://raw.githubusercontent.com/MetaCubeX/mihomo/88dcbf7f1614a67c3b36b848ee3592dfa92ada36/config/config.go)
creates six predefined adapters and separately recognizes/creates GLOBAL;
these are not seven equivalent typed actions. The
[direct constructor](https://raw.githubusercontent.com/MetaCubeX/mihomo/88dcbf7f1614a67c3b36b848ee3592dfa92ada36/adapter/outbound/direct.go)
and [reject/pass constructors](https://raw.githubusercontent.com/MetaCubeX/mihomo/88dcbf7f1614a67c3b36b848ee3592dfa92ada36/adapter/outbound/reject.go)
justify rejecting them from this ordinary-label slice on both mapping sides.
Lowercase or containing strings such as reject, REJECT-backup and PASS-through
are not substring-blacklisted, but still require ordinary/finality declarations.
The [adapter parser](https://raw.githubusercontent.com/MetaCubeX/mihomo/88dcbf7f1614a67c3b36b848ee3592dfa92ada36/adapter/parser.go)
can assign special behavior to custom names, so spelling alone cannot establish
ordinary semantics.

The [Mihomo routing loop](https://raw.githubusercontent.com/MetaCubeX/mihomo/88dcbf7f1614a67c3b36b848ee3592dfa92ada36/tunnel/tunnel.go)
can skip UDP-incompatible outbounds or continue/rematch. sing-box's
[action schema](https://raw.githubusercontent.com/SagerNet/sing-box/v1.12.0/option/rule_action.go)
distinguishes a route to a named tag from a reject action. These facts require
explicit terminal-for-TCP-and-UDP declarations and forbid guessed DIRECT,
reject/drop, TCP-only compensation or implicit actions. The
[enclosing route documentation](https://raw.githubusercontent.com/SagerNet/sing-box/v1.12.0/docs/configuration/route/index.md)
describes fallback outside this fragment's proof scope.

## Preservation, privacy and bounded failures

Original source bytes, digest, complete target bytes/digest, immutable declarations,
unique top-level source references and normalized occurrences remain private.
Each occurrence retains source-rule index/reference, predicate index, path,
original decoded value, YAML line (JSON has no guessed line), exact/suffix kind,
domain and typed source/target actions. Output mapping is
(output_index, source_rule_index, predicate_index). Identical rules, selectors,
array members, overlaps and shadowed occurrences survive in order.

Public preview contains only bounded counts and fixed statements: ordered-label
selection under declared preconditions; canonical lowercase ASCII TCP/UDP scope;
finality declared_unverified; enclosing fallback/runtime behavior/effective
priority/actual egress not_established; native acceptance not_run; apply_supported
false. It contains no domains, labels, source metadata or digests. Default repr,
JSON and pickle do not expose private state. Explicit private_material returns
immutable private values in a fresh outer mapping.

Limits: input/output each 1 MiB; 256 original source rules, 256 total occurrences,
256 mapping records, 16 client aliases. Alias and canonical-domain lengths remain
bounded by existing validators. JSON depth/tokens and safe YAML event/depth limits
bound parsing. Unsupported YAML tags/anchors/flow forms/multiple documents,
duplicate JSON keys (including escape-equivalent keys), unsupported fields,
noncanonical hosts, missing/ambiguous mappings/finality, digest/reference mismatch,
parser absence, cancellation and deadline all fail without a returned artifact.
Cancellation checks occur during parser/record/render traversal and immediately
before return; callback exceptions/non-booleans cancel. Caller declarations are
validated and copied before the first callback. Deadline is finite, positive,
maximum 60 seconds, default 5; this is cooperative, not preemptive interruption
of the bounded parser's individual operation.

## Observed tests

Failing-first run before the module existed:
`python -m unittest discover -s tests -p test_rule_policy_conversion.py -v`
failed on test_separate_api_exists with ModuleNotFoundError for
rule_policy_conversion (one test, one error). The module was then implemented.

Observed after implementation on 2026-10-18:

- Focused ordered-policy suite: **26 tests passed**
- `python -m unittest discover -s tests -p 'test_rule*conversion.py'`: **73 passed**
  (47 retained predicate tests and 26 new ordered-policy tests)
- `python -m unittest discover -s tests -p test_rule_source_import.py -v`:
  **45 passed**
- `python -m compileall -q skills/claude-guardian/scripts/rule_policy_conversion.py`:
  passed
- `ast.parse(..., feature_version=(3,10))` for the new module and test: passed;
  this is minimum-version syntax checking, not running Python 3.10

The focused suite freezes complete JSON/YAML output, provenance and hashes;
checks broad-before-exact, reversal, duplicate policies and OR expansion; tests
apex/child/grandchild and concatenated/hyphenated/appended-suffix negatives;
uses 80 deterministic generated policies with independently parsed source/target
selection oracles and inverse round trips; checks both mapping sides of every
reserved label; exercises malformed structures, conditions, actions, metadata,
parser/byte/count limits, private output, mutation isolation, cancellation at
parse and final-return boundaries, and mocked no-file/process/network effects.
Existing predicate action rejection is retained. Generated round trips alone
are not the equivalence evidence: the independent selection oracle and frozen
expected bytes are separate assertions.

## Remaining conditions and rollback

This page does **not** grant full ENV-T40 acceptance. Separate evidence must cover:

1. Authorized controlled composition of successful private output through the
   actual reviewed transaction/recovery APIs: scoped target and backup, exact
   output readback, distinct rollback authority, exact restored bytes/metadata,
   source/unrelated-neighbor protection, and retained evidence on failure
2. Stale source/target identity, cancellation, changed backup scope/permissions,
   rollback conflict and post-replace journal failure at their actual stages;
   failed conversions must never reach planning or change a destination
3. Review against all original L + R obligations across the actionless and
   ordered-profile slices, without broadening unsupported semantic claims
4. Integrated package entry and package/source/pin/ledger refresh, full aggregate,
   Node synthetic checks and reproducible packaging in the parent batch

Even controlled transaction tests cannot establish complete configuration merging,
organization/recovery protection, GUI persistence, subscription refresh, actual
rule hits/egress, installed-engine acceptance, or user-device recovery. These
remain explicit host/native integration obligations from §5.8/D07; neither source
research nor this conditional model replaces them.

Rollback for this isolated logic slice is removal of the three new owned files
(module, tests, this evidence page), plus reversal of any separately integrated
package/procedure references. No real settings or live routing were changed.
