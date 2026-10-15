# ENV-04A: bounded Mihomo DNS sample

Implementation of the Mihomo portion of D-ENV v0.3 §20.4.2. This is an opt-in
library integration, not a CLI, native ownership adapter, or completed ENV-04.
Importing the module causes no I/O. Inventory audit permissions remain unchanged.

## Private host boundary

Call `probe_mihomo_dns(QueryScope(binding, name, query_type), verify_binding=...,
approve_query=...)` with trusted host callbacks. There are deliberately no
permissive callback defaults and no default domain. `query_type` is A or AAAA;
use separate, separately approved calls for the two families. The name must be a
canonical lowercase ASCII multi-label hostname without a trailing dot; labels
are limited to letters, digits and interior hyphens. URL syntax, address
literals, wildcards and query injection are rejected. The exact path is built
with URL encoding. Names containing Claude/Anthropic labels are rejected in
this PC0-only adapter; this conservative filter does not replace host verification
of a neutral, registered, user-approved endpoint.

The host must establish and recheck device, desktop user, network namespace,
process ID and start identity, selected instance, listener ownership and Mihomo
product identity. `ControllerBinding` contains private host-issued references;
syntactic validation alone does not verify ownership. Checks happen before
approval, immediately after approval and after receiving the response. A changed
binding fails closed and yields no facts. A native host must still account for
process/listener races between checks; this module does not claim atomic OS
ownership or cryptographic server identity.

`approve_query(scope, budget)` must consult fresh, explicit network-probe consent
covering the exact binding, name, type, generated path and one-request budget.
The scope exposes `network_effect`: the controller can contact its configured
upstream resolvers and disclose the query name. Read-only configuration consent,
a model-supplied boolean, a previous audit or general coding permission does not
authorize this query. Consent must identify this disclosure and configured
resolver path to the user; if that scope cannot be established, remain blocked.
Callbacks and injected transports are trusted code, not user-selectable plugins.
The successful return value must be exactly True, not a truthy token.

## Transport and response boundary

The real default transport sends one credential-free GET to exactly 127.0.0.1
or ::1 in the executing namespace and the approved port. It does not call
getaddrinfo, inherit proxy settings, scan ports, discover endpoints, use cookies
or credentials, redirect, retry, fall back, flush caches, or change configuration.
HTTP 401/403 reports `AUTHENTICATION_HANDOFF_REQUIRED`; no credential API exists.
A caller must not work around that result by disabling controller authentication.

The adapter reuses `controller_inventory` binding/budget validation, its bounded
cancellation-aware socket reader and strict JSON parser. Its inventory transport
cannot accept DNS paths and is deliberately not widened. The small DNS transport
therefore has its own exact GET and strict HTTP framing checks. Shared-private-
helper changes require running both test suites. Response headers and body share
the byte cap; defaults are 262144 bytes, five seconds, depth 24, 10000 JSON nodes,
one request. The absolute cap follows inventory (1 MiB, 15 seconds, depth 32,
20000 nodes); answer records have an additional cap of 256. Duplicate JSON keys,
invalid constants, bad framing/encoding and context mismatches fail closed.

Cancellation is checked around callbacks/socket operations and polled every
50 ms while reading. Connect/send have remaining-deadline socket timeouts;
cancellation does not forcibly interrupt arbitrary trusted callback code or a
blocking connect/send. Host callbacks/transports must bound their own work.
Cancelling a client request cannot undo a query already sent or guarantee that
Mihomo stops its upstream work. `requests_attempted` records attempted transport
invocation, not a claim that a DNS packet was sent.

Mihomo's current JSON Question entries use `Name`, `Qtype`, `Qclass`; these must
match the requested name, numeric A/AAAA type and IN class. The implementation
accepts a single matching question, Status, TC and bounded A/AAAA/CNAME answers.
It checks answer ownership through a non-cyclic CNAME chain and the requested
address family. Unsupported answer types fail closed rather than being interpreted
speculatively. Authority/Additional/unknown fields are bounded but not projected.

## Public evidence and limitations

Public facts contain a generated query alias, matching-question flag, query type,
rcode, truncation, answer/address/CNAME counts, coarse global/non-global address
classification, family and observation/elapsed time. The global category excludes
multicast, loopback, link-local, unspecified and reserved addresses; it classifies
address space and does not establish reachability. They contain no raw query
name, IP, CNAME, binding, URL/path, response text, credentials or exception text.
The observation clock is explicitly unverified. Negative DNS results and
truncated replies remain samples with their status visible; successful execution
is not a passing readiness gate. The gate stays closed.

Addresses are not classified as Fake-IP without current configured-range
provenance. Private/reserved addresses do not establish pollution or a leak.
Cache/hosts origin remains possible/unknown. This sample does not establish
system/browser routing through Mihomo, actual upstream packets, resolver route,
authoritative correlation, global DNS leak absence or native-platform acceptance.
No endpoint registry or native UI approval adapter is supplied in this change.

## Primary sources checked 2026-10-15

- [Official Mihomo API reference, Domain Query](https://wiki.metacubex.one/en/api/#dnsquery)
  specifies GET and the name/type parameters and DNS response fields
- [Official Mihomo route implementation](https://github.com/MetaCubeX/mihomo/blob/Meta/hub/route/dns.go)
  confirms Question is the DNS Question struct and answer keys are lowercase
- [Upstream DNS Question struct](https://github.com/miekg/dns/blob/master/types.go)
  establishes Name/Qtype/Qclass field names (no JSON rename tags)

These are mutable upstream references, not a claim of compatibility with every
Mihomo version. Unsupported response schemas remain blocked.

## Evidence and rollback

`python -m unittest discover -s tests -p test_mihomo_dns_probe.py -v`

Tests use injected data and test-owned loopback HTTP listeners only. The real
transport fixture forbids getaddrinfo, checks the exact request and absence of
credentials, and exercises framing/auth/redirect/cancellation handling. There
are no real-controller or public-DNS tests, no OS/user-device acceptance, no
configuration writes and no standing network authorization. Remove the three
new adapter/test/document files to roll back; there is no persistent state or
configuration to restore. Publishing requires approval for the eventual batch.
