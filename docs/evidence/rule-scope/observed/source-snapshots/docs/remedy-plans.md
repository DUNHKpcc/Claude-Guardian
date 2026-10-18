# ENV-06 offline remedy-plan compiler

## Delivered scope and evidence

`skills/claude-guardian/scripts/remedy_plans.py` provides the standard-library-only
`compile_plan(request)` function. This is an offline **semantic proposal compiler**,
not a native Clash configuration compiler or transaction executor. It performs no
file access, process execution, DNS lookup, network access, installation, secret
extraction, or configuration mutation. There is deliberately no apply entry point,
CLI command output, YAML patch, raw-config input, or built-in production allowlist.

The source basis is ENV-SPEC v0.3 §§5.1–5.8, 20.9, ENG-03/04 and main SPEC
v0.1.10 PC0. The four directions from §20.9 have concrete proposal logic rather
than a shared unsupported-template stub:

| Template ID | Semantic proposal | Mandatory preservation / limitations |
| --- | --- | --- |
| `keep-existing` | Bind only selected rule references to the selected group; temporary neutral rules carry removal requirements | Existing subscription, unrelated routes, organization priorities, local/rescue paths and global MATCH stay outside the proposal |
| `explicit-rule` | Selected application binding to an explicitly projected HTTP/mixed entry plus selected rules and DNS responsibility | Existing necessary TUN/VPN remains; SOCKS-only is not silently treated as HTTP; adoption is per application, not every process |
| `tun-rule` | Scoped TUN routing intent, selected rules, node bootstrap and DNS responsibility | Control/proxy channels, VPN/VM and local services; unknown scope/compatibility and simultaneous explicit adoption are blockers |
| `scoped-compatibility` | Selected `ipv4-only`, `restrict-webrtc`, or `manual-egress` intent | Only the named workflow/application scope; preserve certificate verification, actual region and proxy outer transport; IPv4-only needs the outer-node IPv6 dependency resolved |

These are minimal **requested intents**, not a claim of byte-level minimality or
an idempotent native patch. The compiler neither replaces global MATCH nor builds
a fresh full configuration. It cannot prove that a proposed rule is absent from
current configuration; a future native adapter must compute the actual delta.

All structurally valid plans remain `status: blocked`, `apply_supported: false`.
They carry `NATIVE_SCHEMA_ADAPTER_NOT_IMPLEMENTED` and
`NATIVE_ACCEPTANCE_NOT_RUN`. Known-looking version strings add
`VERSION_CAPABILITY_UNVERIFIED`; missing/unknown version facts add
`VERSION_UNKNOWN`. Parsing a version string never registers native support.
These blockers do not suppress useful semantic proposals except on cancellation,
target mismatch or stale revision bindings, which return no proposals.

Evidence currently consists of synthetic Linux tests only. This does not close
ENV-06, ENG-03/04 or VAL-02/04/07, and does not demonstrate a Mac/Windows target,
real GUI write-back, real resolver behavior or actual rollback.

## Input contract

Input is an explicit dictionary with schema
`guardian-remedy-plan-input/0.1`. Unknown fields, invalid enums/types, unregistered
DNS nodes, duplicate reference lists and raw paths/URLs in reference fields raise
`InvalidProjection`. Error messages do not echo rejected values. Fields are not
silently ignored. The function does not validate whether a caller has told the
truth: supplied observations remain labeled `offline_projected_facts`.

Required envelope fields:

- `target_ref`, `observed_target_ref`: opaque references, equal before planning
- `revisions`, `current_revisions`: private trusted-host snapshot-binding inputs,
  identical nonempty layer-reference-to-SHA256 maps. Both sides must contain
  exactly the same layers and revisions. These digests are never returned
- `revision_refs`: public opaque snapshot aliases, keyed by exactly the same
  layer references as `revisions`; only these aliases appear in plan output.
  Hash-shaped aliases (including uppercase hex) and aliases equal to any private
  digest from either snapshot map are rejected, including cross-layer collisions
- `template`: one of the four IDs above
- `route_ref`: caller-selected route reference; no inferred route choice
- `scope_refs`: nonempty list of explicit workflow/application references
- `facts`, `intent`: objects using the allowed fields below
- Optional `cancelled`: boolean; cancellation produces no proposal

References use ASCII letters followed by at most 63 letters, digits, hyphens or
underscores. Reference lists are unique and bounded at 256; revision maps at 32;
DNS dependency edges at 1,024. References must be opaque aliases, never secret
values encoded as aliases. This is schema validation, not a secret detector.
Production callers must project and redact at the source before calling this
API. Names, ports, addresses, raw rule strings and subscription contents are
intentionally not accepted.

### Facts

Every facts section is optional to represent incomplete observation. Missing
relevant facts generate explicit unknown blockers rather than invented defaults.
`yes` / `no` / `unknown` are strings, not booleans.

- `versions`: `product` (`clash-verge-rev`, `clash-verge`, `mihomo`, `unknown`),
  `gui`, `core` (semantic-version-shaped string or `unknown`)
- `mode`: `rule`, `global`, `direct`, `unknown`
- `explicit`: required `kind` (`http`, `mixed`, `socks`, `unknown`) and `adoption`
  (tri-state), optional opaque `entry_ref`
- `tun`: tri-state `enabled`, `scope_known`, `vpn_vm_compatible`
- `control`: tri-state `dependency_known`, `preserved`, `rescue_available`, plus
  `scope_refs` for protected control scopes
- `rules`: tri-state `first_match_verified`, `protected_priority_preserved`,
  `complete`. These claims refer to the selected rules only, never a production
  domain allowlist
- `ownership`: tri-state `known`, `persistent_extension_available`,
  `gui_readback_available`
- `groups`: reference-to-object map; each object has tri-state `complete` and
  `members` references. Optional `kind` is `group`, `proxy`, `direct`, `reject`
  or `unknown`; missing types remain unknown. Terminal kinds require empty
  members. Empty groups are unresolved, not safe terminals. Proxy terminals
  also need a declared `protocol` (`http`, `socks5`, `shadowsocks`, `vmess`,
  `vless`, `trojan`, `hysteria2`, `tuic`, `wireguard`, `unknown`); unknown
  protocol remains blocked. Direct routing is detected from the typed node,
  never an alias spelling. Protocol recognition is not native transport proof.
  Unknown provider/rule-set expansion must not be represented as complete
- `ipv6`, `udp`: `verified`, `unknown`, `unsupported`. Verification remains a
  caller-projected statement and does not become native evidence
- `compatibility`: tri-state `scope_supported`, `ipv6_outer_node_required`
- `dns`: required `nodes` and `edges` if the section is present. Edges contain
  `from`, `to`, and `path` (`normal`, `failure`, `both`). Additional tri-state
  fields are `complete`, `local_preserved`, `browser_doh_known`,
  `bootstrap_known`, `policy_merge_known`. `responsibility` is `system`,
  `mihomo`, `application`, `mixed`, or `unknown`

A DNS edge means the source **depends on** the destination. Represent node-name
bootstrap, resolver transport, proxy reachability, application DoH and local
resolution as separate aliases when relevant. Cycles are checked independently
for normal and failure graphs with iterative topological traversal. Acyclic
output says `acyclic_projected`, not working DNS. An empty graph remains unknown,
even if a caller marks it complete. Absence of dependencies or failure edges
cannot be proved by this compiler; the caller's completeness claim and future
native evidence must establish terminal/bootstrap facts and fallback coverage.

### Intent

All fields optional, but applicable missing choices produce blockers:

- `rule_refs`, `diagnostic_rule_refs`: selected opaque registry references;
  diagnostic rules are explicitly temporary and require removal
- `egress_group_ref`: approved group reference, required for selected rules
- `no_direct`: tri-state; `yes` makes recursively reachable DIRECT a hard blocker
- `ipv6_goal`, `udp_goal`: `preserve`, `proxy`, `block`, `unknown`; proxy/block
  produces a scoped intent with `system_wide_guarantee: false`
- `compatibility_action`: `ipv4-only`, `restrict-webrtc`, `manual-egress`

No inference of all-program coverage is permitted from HTTP environment
variables, TUN enablement, DNS `ipv6: false`, timeout, or an empty observation.
Nested group cycles and unresolved group expansion are reported separately.

## Output and safety boundaries

The result contains the input bindings, `proposed_changes`, structured
`blockers` with `unknown` or `blocked` state, `dns_checks`,
`protected_control_path`, and backup/rollback/acceptance requirements. Output
objects are detached from the input; repeated calls are deterministic.

- Protected control scope overlap is a hard blocker even if another field claims
  the control path is preserved. Missing/empty explicit control scope references
  prevent a preserved status. Missing dependency/rescue facts remain unknown
- Existing global/direct mode is a conflict for rule templates and for any
  compatibility template that also proposes workflow or diagnostic rules, never
  a silent mode change. A compatibility-only proposal may omit rule intents. Explicit+TUN adoption requires loop/exclusion evidence
- Local/corporate DNS and fake-IP filters are retained. Full effective
  `dns.nameserver-policy` semantics must be preserved; no blind deep merge is
  offered. Version-specific full-table replacement remains future adapter work
- DNS suppliers are not selected by the compiler; use an existing verified or
  separately user-selected provider. No free/public resolver is silently chosen
- Backup requirements specify private, hash-verified snapshots of affected owned
  layers and their permissions, not copies in plans/reports. Rollback requires
  conflict checks, restoration of only owned changes, control connectivity and
  effective-state readback
- Native parsing, core validation (including possible provider-download side
  effects), GUI ownership/readback, refresh persistence and real traffic evidence
  are explicitly pending. Plans grant no execution authorization

## Integration and remaining work

The existing inventory adapters expose opaque per-call revision aliases, not
these private SHA256 snapshot-binding inputs. The compiler cannot be wired
directly to the inventory CLI: a private trusted-host snapshot binding adapter
would be required, and private digests must never be promoted to public fields.

The existing inventory adapters expose a limited projected subset. They do not
currently supply enough facts to infer all rule first matches, DNS bootstrap and
failure dependencies, GUI ownership, control-channel dependencies or complete
nested groups. Do not feed raw inventory/configuration into this contract or
invent the missing facts. A future explicit projection adapter must bind each
fact to source, target and revision evidence and preserve unknowns.

The revision comparison is a pure consistency gate: it does not read current
files or lock a target. Reusing the same caller-supplied revision twice cannot
prove freshness. A native executor would need a fresh observation/commit lock,
permission checks, precise semantic delta and action-time authorization.

Rule references must eventually resolve through a separately validated,
versioned registry. This module neither expands references nor certifies official
endpoint coverage. The documents' representative domain seeds are not a complete
production allowlist.

Future ENG-03 work must register actual product/version capabilities and layer
ownership, produce supported GUI/manual steps or persistent extension deltas,
handle whole-table DNS merge semantics, and stage/read back/restore them safely.
ENG-04 must supply native resolver/route evidence for each actual template,
including local DNS and normal/failure resolution. No claims are made that the
current module completes these native requirements.

## Reproduction

Run the synthetic unit suite:

```sh
python -m unittest discover -s tests -p test_remedy_plans.py -v
```

The fixture in `tests/test_remedy_plans.py` is the executable contract example.
It uses aliases and private synthetic SHA256-shaped inputs, not a real machine
record. Regression tests verify that digests never enter public plan output.
Tests cover all four directions, rejection of raw/unknown input, deterministic
non-mutating/no-I/O behavior, stale revisions and wrong targets, cancellation,
control-path protection, normal/failure DNS cycles, local DNS preservation,
nested DIRECT/cycles/unknown leaves, mode conflicts, incompatible proxy entry,
combined modes, IPv6/UDP unknowns, scoped downgrade and rollback requirements.
