# ENV-04 bounded STUN transaction

## Delivered scope

`skills/claude-guardian/scripts/stun_probe.py` implements an isolated, opt-in
Binding codec and independent UDP transaction. It has no CLI, import-time I/O,
automatic trigger, DNS resolver, persistent worker, configuration reader, or
integration into the global workflow. ADR-004's Cloudflare choice is a service
candidate, never permission to probe it. ENV §20.6 remains the design baseline.

Production scope permits only `stun:stun.cloudflare.com:3478` with a canonical,
global numeric address, UDP port 3478, one address family, an exact local target
alias, and `direct_socket_os_route_tun_unknown`. The separately labelled
`owned-loopback-fixture` scope permits only numeric loopback addresses and an
explicit port for tests. It is not an arbitrary endpoint override.

## Host approval contract

`probe_stun(scope, approve=..., current_target=..., cancelled=...)` requires
all three live callbacks. `Scope` is immutable and contains endpoint, pinned
numeric peer, port, family, target alias, and path. `approve(scope)` must return
an equal `Scope` from current, exact-scope host approval; `True` or a scope covering another target/path/address is insufficient.
Freshness of an otherwise identical approval must be enforced by the host. The host must
verify the approved hostname-to-address binding before approving that scope.
This module does not resolve or authenticate that binding. DNS resolution needs
its own approved path and bounded implementation; there is no implicit fallback.
No shipped host consent integration is claimed by this milestone.

Before a public run the host must identify the operator, exact service and peer,
local target/device/user/namespace, path, family, disclosure, and budgets, obtain
the user's current approval, and ensure cancellation/revocation can reach these
callbacks. A hardcoded echo callback is a test stub, not user consent. A callback
must not automatically create permission because the scope is allowlisted.

The target callback returns the live local target alias. Cancellation is checked
before socket creation, around approval, before sends, during bounded receive
polls, after received packets, before accepting evidence, and after socket cleanup. Scope/target/path
are not sent in the datagram. Callback exceptions return fixed codes, never raw
exception text. No callback or transport injection is an untrusted-plugin sandbox.

## Bounds and lifecycle

- One cryptographically random 96-bit transaction ID, reused for retransmissions
- At most three send attempts, with 0.5 s then 1 s retransmission intervals
- Default 3.5 s total window; caller may shorten it, maximum 5 s
- 50 ms maximum socket wait slices for cancellation responsiveness
- At most 64 received datagrams and 256 receive attempts (including timeouts);
  bounded 4097-byte receive detects oversize
- Clock samples must be finite numeric values, never booleans, and nondecreasing;
  the independent receive-attempt ceiling also bounds a stalled clock
- Each request is 20 bytes: at most 60 request payload bytes, excluding IP/UDP
  overhead; at most 262208 received bytes processed by this transaction
- Numeric pinned peer only: no DNS, redirect/alternate server, family fallback,
  proxy discovery, alternate port, new transaction retry, or packet logging
- Socket closes in `finally`; cleanup failure invalidates successful evidence

Invalid packets are discarded within the same budgets. Source address/port,
transaction ID, response type, cookie, length, attribute boundaries, and mapped
address family must match. Optional unknown attributes are skipped; unknown
mandatory/authentication attributes are rejected. If present, the FINGERPRINT
is checked and must be last. A fully framed, matching Binding error response with a valid ERROR-CODE, or a
matching success with an unsupported mandatory attribute, terminates the
transaction as unknown with a fixed error code. No later queued success is
accepted. Framing and any fingerprint are validated first, so an early unknown
attribute cannot hide corruption. There is no redirect, reason-text disclosure
or retry after these terminal failures. Source/transaction correlation is not
cryptographic authentication.

The budgets are cooperative: synchronous authorization, target, cancellation,
clock, socket-factory and injected socket methods must be trusted and bounded.
Python cannot forcibly interrupt a stuck callback or `close()` with this API.
The production socket uses OS timeout support, but OS scheduling can add latency.
Hard wall-clock guarantees against hostile/stalled adapters would require a
separate supervised process, which is not implemented. Revocation cannot undo a
previously sent datagram; simultaneous external changes need host coordination.
The host must also serialize/rate-limit separate invocations; this function's
per-call budgets do not authorize repeated probes.

## Evidence and privacy

The service and intervening network can observe source IP/port, destination,
timing, and the bare STUN request. There are no usernames, credentials, device
identifiers, or business payloads. Raw mapped IP/port are returned only to the
local caller for comparison and must be aliased/redacted before ordinary sharing.
No provider retention or availability guarantee is made.

An `observed` response is unauthenticated address evidence for this transaction.
`path_association` always remains `unknown`; browser and target application paths
remain `not_observed`. Native UDP follows current OS routing, which may include
a TUN. It does not prove ISP-direct routing, proxy adoption, browser behavior,
kill-switch protection, all-UDP reachability, account eligibility, or safe access
to any service. A timeout, rejection budget, permission error, cancellation or
revocation leaves the result unknown. No system/proxy changes follow automatically.

## Protocol references and intentional limits

Verified against [RFC 8489](https://www.rfc-editor.org/rfc/rfc8489.html), sections
5, 6.2.1, 6.3 (including terminal responses in 6.3.3–6.3.4), 14 and 14.2: 20-byte headers, cookie `0x2112A442`, 96-bit IDs,
Binding request/success types, padded TLVs, and IPv4/IPv6 XOR mappings. The
IPv4 mask is the cookie; IPv6 also uses the transaction ID. Receiver padding and
the reserved mapping byte are ignored; the first mapping takes precedence.

The three-send diagnostic cap intentionally shortens the RFC's ordinary retry
window, so exhaustion is no conclusion about general reachability. The parser
supports unauthenticated XOR mapping, not a complete STUN client, TURN, ICE,
SOCKS5 UDP ASSOCIATE, MESSAGE-INTEGRITY, or NAT-behavior classification.

Independent IPv4/IPv6 mapping vectors come from
[RFC 5769 §§2.2–2.3](https://www.rfc-editor.org/rfc/rfc5769.html#section-2.2).
Optional CRC fingerprints detect corruption, not server authenticity.

## Validation and rollback

Run `python -m unittest discover -s tests -p test_stun_probe.py -v`.
Tests use injected sockets/clocks and owned IPv4/IPv6 loopback responders only.
They cover framing, truncations, mappings, fingerprint corruption, wrong
source/ID/family, flooding, three-send/deadline limits, live revocation and target
changes, cancellation, invalid/stalled clocks, terminal server/attribute errors,
error redaction and post-cleanup revalidation. Loopback IPv6 skips
explicitly when unavailable; skipping is not acceptance.

No public STUN traffic or public DNS lookup was performed for this change.
Owned Linux loopback is not Mac/Windows native acceptance, real Cloudflare
compatibility, proxy/TUN association, or ENV-04/VAL04 completion. The remaining
host/DNS consent integration and real authorized path validation remain open.
Rollback removes this module, its tests and this document; there are no network,
account, configuration or installed-service changes to undo.
