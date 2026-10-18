# Claude-target IPv4-only policy: bounded implementation evidence

Date: 2026-10-18 UTC. New requirement: **PRODUCT-IPV4-20261018**.
Evidence layer: offline logic, fixtures and presentation only. No host network
change, active probe, engine execution or native IPv6-blocking pass is claimed.

## Product decision and precedence

The user explicitly chose “改为仅允许ipv4” when asked whether Claude-related
traffic should default to IPv4-only as the Skill recommendation. The current
policy is **IPv4_ONLY**, with **IPv6 fallback forbidden** for the selected Claude
target/application flow. IPv4 failure remains unavailable under that policy;
it does not authorize IPv6 fallback.

This supersedes only the older dual-stack-first recommendation for that selected
flow. Original source specifications and the 218 historical acceptance conditions,
IDs and evidence layers are unchanged. It is not a host-operation authorization.

Selected application scope includes related subprocesses only when actually bound
to the workflow; target-leg scope includes proxy-to-target family choice. Proxy
outer transport may remain IPv6. Codex/recovery controls, other applications,
organization policies, private DNS and unselected system IPv6 remain protected.
Unknown/unsupported application scoping is reported honestly; it does not silently
change the default to dual stack or expand enforcement to the whole machine.

## Implemented pure APIs

`traffic_policy.policy_projection()` returns fresh fixed values derived from a
frozen typed `TrafficPolicy`. Constructor fields cannot be overridden:

- schema: guardian-traffic-policy/0.1
- requirement/date: PRODUCT-IPV4-20261018 / 2026-10-18
- policy: IPv4_ONLY; applies_to: claude_target_application_traffic
- ipv6_fallback: forbidden
- proxy_outer_transport: preserve_existing_independently
- control_channels: preserve; other_applications: unchanged
- enforcement_status: unknown; compliance: not_established
- environment_pass: false; apply_supported: false; authorization: none

`traffic_policy.plan_ipv4_only(scope=None, *, max_seconds=5, cancelled=...)` and
`remedy_plans.compile_ipv4_policy_plan(...)` return a frozen private conditional
plan. `preview()` exposes only bounded fixed enums/reasons, not scope aliases;
`private_material()` explicitly exposes immutable declared scope. Repr/default
JSON/pickle do not disclose private scope. Constructor validation rejects arbitrary
status/reason labels, so ordinary direct constructor misuse cannot forge passed
or verified output. This is not a claim of hostile in-process Python isolation.

The strict scope schema guardian-ipv4-policy-scope/0.1 separates application,
target leg, proxy outer, control and other-application refs. It also requires
explicit support, separation, fallback and preservation declarations plus a
configuration-state declaration. None is trusted native evidence. Missing scope
is unresolved; unsupported scope remains unsupported; preserved-scope overlap,
present IPv6 fallback or stale configuration block planning. Complete declarations
can yield conditional_plan, but enforcement remains unknown and compliance is
always not_established. There is no success/pass path or mutation command.

Limits: 64 refs per scope family, 256 total, 64-character bounded ASCII aliases,
recognized credential-shape rejection, strict builtin containers and enums;
finite positive deadline up to 60 seconds, default 5. All caller data is copied
before callbacks. Cancellation/error/non-boolean callback results stop atomically;
checks include the final return boundary. Planning performs no file/process/network
I/O. Existing scopes cannot be altered through returned copies.

## Runtime integration and independent work

- `interview_flow.assessment` exposes the fixed current policy for fresh and legacy
  interview states without rewriting answers or creating consent. G1 coverage,
  G2 planning readiness and G3 action authorization retain their meanings
- `agent_remediation.select` exposes policy separately and maps explicit policy
  gaps to fixed `ipv4-only-policy`, a candidate_only action. It requires exact
  target/scope/diff/impact/backup/recovery and separate approval/verification;
  it never emits a network-changing command. Existing cancellation, prerequisite,
  no-change and incident handling retain priority
- `remedy_plans.compile_plan` adds a separate traffic_policy member. Legacy
  preserve/proxy IPv6 intent is explicitly marked conflicting/ambiguous against
  the new target policy. Existing executable-candidate proposal and blocker sets
  are unchanged; an independent rule edit cannot certify IPv4-only enforcement
- The old coarse compatibility path's outer-IPv6 protection is retained. The new
  separate conditional planner can describe preserving an IPv6 outer connection
  while constraining a distinct target leg; declarations still cannot prove this
- `interview_migration` accepts legacy omission or the exact current fixed policy
  member, rejects malformed/extra/forged values, and preserves cancelled state
- `guardian.base` emits the fixed policy. Strict report validators accept either
  legacy omission or the exact fixed member (including types); arbitrary extra
  fields, modified policy and forged pass/authorization values reject
- Guardian redaction reconstructs only the exact safe fixed policy object so its
  literal authorization=none survives report round trips. Changed/extra arbitrary
  authorization/token content keeps normal redaction; no general exemption exists
- `status_dashboard` projects the current fixed policy independently of imported
  claims and shows unknown enforcement/no acceptance. Existing sample-card
  meanings do not change. Fake imported compliance, AAAA-empty, curl-4 success,
  one HTTPS sample, IPv6 timeout or no ICE candidate cannot establish compliance

The original standalone file-path import behavior is preserved for guardian,
interview_flow and remedy_plans: when the sibling module is not on sys.path, an
explicit sibling-file fallback loads the stdlib-only policy module. It does not
change sys.path or depend on prior test order. Packaged normal imports remain
available. Runtime input schemas were not generally relaxed.

## Observed tests and corrections

The initial API test was captured before module creation and failed with
ModuleNotFoundError. Later focused integration found a real round-trip regression:
generic redaction replaced the new fixed authorization=none with [redacted]. A
new test failed before the narrow fix, and the same test and original compact
interview save/load regression pass afterward. Neither failure was hidden.

Independent review also found that direct PrivatePolicyPlan construction could
remove known conflict reasons and replace blocked with conditional_plan (without
forging compliance or authority). A new failing-first regression reproduced it.
The constructor now bounds exact tuple/pair/key structure before dict conversion,
validates the immutable snapshot, and requires statuses/reasons to equal the
canonical derivation used by the planner. That fix passed 26 tests. Later aggregate consumer review found two additional
integration issues: the existing static-HTML allowlist rejected the new section
tag, and compact interview migration rejected the new policy member. Both were
captured before repair. The renderer now uses existing allowed paragraph tags;
no HTML/resource/CSS allowlist was widened. Migration accepts only legacy absence
or the exact fixed typed policy, preserves prior screening/unknown-key checks and
cancellation, and never treats policy as observed evidence. Current, redacted and
legacy wrappers migrate to identical states; interrupted wrappers stay paused.
The current policy suite has 27 tests and migration has 17 tests.

Observed focused runs:

| Suite | Passed |
|---|---:|
| New policy/runtime integration | 27 |
| Interview flow | 75 |
| Interview resume | 33 |
| Interview CLI | 22 |
| Compact interview migration | 17 |
| Agent remediation | 33 |
| Semantic remedy plans | 22 |
| Guardian | 44 |
| Typed report boundaries | 19 |
| Inventory | 15 |
| Status dashboard | 26 |
| Static dashboard preview | 16 |
| Dashboard interactions | 11 |
| Existing config-edit candidates | 28 |
| Existing rules-extension candidates | 23 |
| Source/package bundle | 3 |
| Exact route replay cases | 6 |
| Exact intake replay cases | 15 |
| Exact task-scope replay cases | 15 |

Commands are `python -m unittest discover -s tests -p test_<suite>.py -v`;
exact accepted-case replays also ran directly with `--replay`. Logs are in the
project recovery records under the ipv4-sixteenth prefix. The new suite includes
independent exact policy literals, every observed cancellation boundary, initial
and final deadlines, constructor misuse, mutation isolation, no-I/O checks,
unknown/unsupported/conflict outcomes, actual report round trips, unchanged
candidate admission sets, and subprocess imports using `python -I -S` from a
fresh temporary directory without PYTHONPATH.

Three accepted-case expectation files were updated only with independently
authored exact policy literals. Complete before/after replays recursively compare
all old members unchanged: route 20, intake 67, task-scope 84 added traffic_policy
members; **zero existing-member value differences**. Before-failure and after-pass
logs plus complete replay/diff receipts are retained. No scenario, field assertion
or original condition was removed. These edits require independent re-review and
explicit accepted-evidence pin refresh; old evidence pins are not automatically
valid merely because tests pass.

## Remaining obligations and rollback

This batch implements the chosen default, bounded planning and truthful reporting;
it does not implement a native app-scoped enforcement adapter. Actual use still
requires bound current device/app/profile/target/configuration, supported scope and
fallback control, preservation review, a precise approved change and independent
same-scope readback/verification. Evidence must address target leg, related
subprocesses and relevant failure/lifecycle behavior, not just resolver output or
one successful request. Any drift invalidates old-condition conclusions.

Parent integration owns independent review, complete aggregate/Node/syntax/package
validation, reviewed evidence pins, persistent backup and publication. Rollback is
the reviewed scoped patch reversal to the fifteenth baseline; preserve unrelated
concurrent edits. No real host setting or routing state needs restoration because
none was changed by this batch.
