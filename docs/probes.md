# 探测模块说明（DNS / STUN / 证据投影）

合并自 dns-probe、os-dns-probe、windows-dns-probe、mihomo-dns-probe、stun-probe、probe-evidence 六份说明（2026-10-21，内容未改写，仅下调标题层级）。原文件可从 git 历史找回。

## DNS protocol groundwork (ENV-04, partial)

`skills/claude-guardian/scripts/dns_probe.py` is a standard-library, pure A/AAAA
message codec. It has **no socket, OS resolver, HTTP client, CLI, provider,
automatic trigger, or persistent state**. Importing it does no I/O. Creating query
bytes grants no permission to transmit them. No Claude hostname is supplied as a
default. PC0 contact restrictions continue to apply to every future adapter.

### Actual coverage

This increment supplies bounded protocol groundwork for ENV-04 / D-ENV §20.4.
It does **not** implement §20.4.2's Windows/macOS system resolution or Mihomo
`/dns/query` call, nor browser DoH, authoritative correlation, DNS configuration
inventory, Fake-IP classification, or leak detection. ENV-04 and VAL-04 remain
incomplete. No transport was added because arbitrary UDP DNS would introduce a
new independent path rather than complete those specified adapters.

The wire parser is useful for a future explicitly authorized DNS wire capture or
query adapter. Mihomo returns JSON, not these wire bytes: it needs a separate
strict JSON projection, sharing the evidence distinctions below, rather than
pretending to feed JSON into this codec.

### API and bounded behavior

- `make_query(name, query_type, transaction_id=None)` returns immutable `Query`
  metadata and a single-question IN packet, with recursion desired. Type is
  exactly `A` or `AAAA`; there are no search domains or implicit names. A caller
  can supply a deterministic 16-bit transaction ID for tests; production default
  uses the standard-library cryptographic random source
- ASCII hostname labels only, at most 63 bytes each and 255 expanded wire bytes;
  a final dot is accepted. IDNA conversion is explicitly outside this subset
- `parse_response(packet, query)` binds the ID, one exact case-insensitive
  question, type, and class. A matching ID alone is insufficient
- Inputs are at most 4,096 bytes, 128 total records, and 4,096 name decoding steps
  per name (bounded by unique offsets in the packet). Compression accepts only backward references to known previously
  parsed name-label boundaries, rejecting header/interior pointers and cycles
- Full non-truncated envelopes, RR lengths, A/AAAA sizes and parsed name RDATA
  are checked. Unknown RR data remains bounded opaque bytes; it is not claimed
  to be semantically validated. Compression into opaque RDATA is unsupported
- Only matching answer-section IN addresses and an unambiguous local CNAME
  chain contribute answers. No alias follow-up, authority/additional glue,
  unrelated owner, or alternative address type becomes an answer
- Truncated responses expose no addresses and request no TCP fallback. The
  correlated header/question are checked, but a TC response's partial RR tail
  is intentionally not treated as a complete message
- Negative responses and server errors expose their numeric RCODE, never answer
  addresses. An empty positive response is `no_matching_address`, not proof of
  NODATA/nonexistence. EDNS and extended response codes are unsupported
- Fixed `DnsError` strings do not echo names, packet bodies, or private errors.
  Successful addresses are untrusted caller-visible data, not automatically
  logged, published, or approved as new connection destinations

`Observation` always retains `path_association='unknown'`,
`leak_assessment='unknown'`, `cache_possible=True`, and `authenticated=False`.
AD/AA flags, a successful answer, resolver-country differences, and a valid
transaction ID do not authenticate a packet or prove route coverage. A future
transport must independently verify source IP/port and outstanding transaction,
then retain the distinction between its own sample and the user's application.
The codec has bounded synchronous CPU work, so no transport deadlines,
cancellation callbacks, permissions, or cleanup hooks are applicable yet.

### Mihomo adapter integration checklist (implemented separately in this batch)

The separately gated `mihomo_dns_probe.py` implements the bounded library portion of the checklist below; see [its contract and remaining host limitations](mihomo-dns-probe.md). This does not widen audit permissions or complete native ownership/approval integration:

1. Bind one already-discovered controller instance to an exact numeric endpoint,
   target/environment alias, approved neutral query name, and one type. Existing
   controller identity and runtime freshness must be checked. Do not select a
   public resolver or discover a controller by scanning
2. Require the trusted host's fresh approval of that exact scope before one
   `GET /dns/query?name=<encoded-approved-name>&type=A` (or separately approved
   AAAA). Audit remains unable to call this path. Authorization must explain that
   the controller may perform an external query despite the HTTP method being GET
3. Reuse the bounded controller HTTP primitive only if its current architecture
   permits a distinct probe-only gate; otherwise build a separate narrow adapter.
   No redirects, environment proxy adoption, automatic alternative hosts, retries,
   implicit hostname resolution, or secret echoing. The existing credential
   boundary must be retained rather than embedding credentials in this module
4. Enforce a monotonic whole-operation deadline, short cancel polls, exact request
   count/body budget, and fresh target/approval checks before I/O and before
   releasing the result. Permission errors, timeout, cancellation, stale binding,
   malformed/truncated/oversize JSON and cleanup failure remain fixed-code unknowns
5. Validate response `Status`, bounded `Answer` records, numeric record type and
   data against the requested name/type and supported alias semantics. Project
   only an opaque domain alias, type, RCODE, answer categories/address family,
   cache possibility and evidence origin `mihomo_query`; do not leak controller
   secrets or infer browser/system adoption. Use configuration-bound Fake-IP
   ranges only when separately available; unknown range remains unknown
6. Test all cases against a self-owned numeric loopback fake controller, including
   target changes during callbacks, denial before network, mismatched name/type,
   and bounded resource cleanup. Then wire the opt-in result into the report.
   No real controller or external query runs without exact runtime authorization

That is a finite functional increment: one authorized kernel query plus a
bounded report, with its tests. Next, implement platform-specific system adapters
separately: Windows `Resolve-DnsName -DnsOnly` without a server override/cache
flush; macOS `getaddrinfo` in an owned cancellable subprocess (a bare blocking
resolver call cannot promise a whole-operation deadline). Native platform tests
must verify process termination, namespace binding and cache caveats. Neither
adapter proves browser DoH, recursive authority source, or a complete DNS path.

### Evidence and sources

Run `python -m unittest discover -s tests -p test_dns_probe.py -v`.
The 31 tests cover known wire bytes, IPv4/IPv6, query validation, correlation,
compression and cycles, malformed lengths, CNAME binding, sections/classes,
negative and truncated replies, budgets, fixed errors, a no-socket/no-resolver
check, and 1,000 deterministic mutated synthetic packets. Tests use synthetic
bytes only; no loopback transport exists or is claimed tested in this increment.
Linux execution is not macOS/Windows acceptance. No public DNS lookup or
user-device inspection was performed.

Protocol references, consulted 2026-10-15:

- [RFC 1035, §§2.3.4, 4.1.1–4.1.4](https://www.rfc-editor.org/rfc/rfc1035.html):
  name/message limits, questions, records, compression
- [RFC 3596, §2](https://www.rfc-editor.org/rfc/rfc3596.html): AAAA record encoding
- [RFC 5452, §9.1](https://www.rfc-editor.org/rfc/rfc5452.html): response matching
  includes transport endpoints as well as query identity

Rollback is removal of this module, its test file and this document before host
integration. No configuration restoration is needed. The integrated package includes both DNS modules via its explicit allowlist; package tests, capability maps, and release notes cover this batch.

## macOS system-resolution sample (ENV-04A)

Implements the macOS `getaddrinfo` portion of D-ENV v0.3 §20.4.2 as an
opt-in library, `scripts/os_dns_probe.py`. Importing performs no I/O. There is
no CLI, discovery, installation, public-resolver fallback, cache flush,
configuration write or Claude/Anthropic request. This is a partial implementation,
not completion of ENV-04 or native platform acceptance.

### Why a macOS-only process adapter

The specification selects `socket.getaddrinfo` on macOS, but
`Resolve-DnsName -Name <approved-name> -Type A/AAAA -DnsOnly` on Windows.
Using Windows `getaddrinfo` instead would change the specified resolution path.
The public entry point therefore rejects Windows and Linux, even with affirmative
callbacks. Windows uses the separate `windows_dns_probe.py` library adapter;
this module does not invoke PowerShell or label a Linux sample as macOS evidence.

A resolver thread cannot interrupt a blocked system resolver. Instead a fixed
helper runs in a separate existing Python process. `multiprocessing` would add
spawn/import semantics and ambient-environment concerns without providing a
stronger termination guarantee. A narrowly scoped `subprocess.Popen` runner is
used here, with explicit executable, `-I -S`, `shell=False`, `close_fds=True`, an
empty environment and a host-verified working directory. No `PATH` search, user
code interpolation, application imports, credentials or inherited secret
environment variables. The exact name/type travels via a bounded stdin message,
not a command argument. The helper never starts descendants.

This is process separation, not an OS sandbox. The trusted host must verify the
absolute interpreter, its standard library, extension modules, loader dependencies,
and working directory, and prevent untrusted replacement during launch. `-I -S`
reduces Python startup injection; it does not establish executable provenance or
supply an atomic executable-by-handle launch. If the host cannot establish these
conditions it must reject `verify_runtime`; a JSON claim is insufficient.

### Authority and request semantics

`probe_os_dns` requires three trusted callbacks, with no permissive defaults:

- `verify_binding(binding)` checks the current device, desktop user, namespace and
  effective execution context; aliases alone do not establish identity
- `verify_runtime(binding)` establishes the runtime and launch trust above
- `approve_query(scope, budget)` obtains fresh consent for this exact target,
  neutral PC0 hostname, A or AAAA type, budget, and possible upstream disclosure

Binding/runtime are checked before approval, again after approval immediately
before the launch, and after the result before accepting any fact. Callbacks
must bound their own work. The library cannot enforce deadlines inside arbitrary
host callbacks or prove their implementation is trustworthy.

Each invocation makes one resolver API call, separately for A or AAAA. Input is
an explicit lowercase ASCII multi-label hostname (IDNA conversion is the host's
responsibility); URLs, IP literals and service/search names are rejected. The
helper adds exactly one trailing dot, making the approved name absolute and
avoiding implicit search-suffix queries. The approval contract explicitly covers
that absolute query. The resolver receives `None` as service, AF_INET or AF_INET6,
SOCK_STREAM, protocol 0 and flags 0. There is no second family query or retry in
this code; the operating system may perform its own internal resolver operations.
The host must establish endpoint neutrality, beyond the additional defensive
Claude/Anthropic substring rejection. Query consent is separate from inventory
consent and does not open the PC0 contact gate.

### Timeouts, cancellation and output bounds

After process creation, a monotonic total deadline (0.05–15 seconds) and a
20 ms polling interval bound observation of the blocking resolver. POSIX pipes
are read nonblocking with selectors; the parent retains at most 4097 bytes and
rejects output above 4096. Stderr is discarded. The helper permits at most 128
rows and the parent revalidates the entire address list, family and uniqueness.
Private addresses are converted to counts, never persisted or returned publicly.
The native resolver's internal memory allocation is not sandboxed or memory-capped.

On success, failure, timeout, callback exception or interruption, the owned child
is killed if still running, waited on, and its pipes closed. Cleanup has a
separate one-second wait; failed termination/reaping becomes `CLEANUP_FAILED`,
never a claim that cancellation stopped every effect. EOF without process exit
still observes the deadline. No resolver thread or reader thread is left behind.

Python documents that process creation itself cannot be interrupted on many
platforms. Consequently this is not an absolute wall-clock bound on `Popen`,
callbacks, kernel termination or abnormal OS failure. A child killed after a
query has started cannot retract traffic or cancel work already handed to a
system resolver service. Native host supervision is required for stronger launch,
process-tree or kernel-level guarantees. No OS-global resolver service is killed.

### Separate provenance and deliberately limited claims

The output uses `guardian-os-dns-probe/0.1`, not the Mihomo DNS schema.
A successful result reports `macos_getaddrinfo` final-resolution address counts,
query type and family, UTC observation time and elapsed duration. It never
invents a DNS RCODE, TTL, CNAME chain, actual resolver server, route, new DNS packet,
DoH state or DNS leak conclusion. Cache/hosts origin remains possible and unknown.
An empty address list does not prove NXDOMAIN or IPv6 blocking. A non-global
address does not prove pollution; Fake-IP analysis remains unevaluated.

Reports omit raw hostname, addresses, device/user/namespace aliases, executable
paths and exception text. Error codes are fixed. `requests_attempted` counts entry
into the child launch attempt, not proof of an upstream DNS packet. All failures
discard facts; gate stays closed and changes stay empty. Imported JSON remains
unverified data; the offline dashboard can display the whitelisted sample via `--probes`, but no workflow evidence or authorization is produced.

### Evidence and remaining work

`python -m unittest discover -s tests -p test_os_dns_probe.py -v`

Tests run only synthetic resolver replacements and test-owned helpers that sleep,
write bytes or exit. The actual helper body is tested with `socket.getaddrinfo`
patched; no hostname, including localhost, is resolved. POSIX lifecycle tests run
on Linux/macOS and explicitly skip Windows. Linux execution proves only owned
POSIX helper lifecycle behavior. macOS CI synthetic tests, when run, still do not
constitute real target-user DNS acceptance. Real macOS DNS, Windows resolution,
live identity/runtime trust integration, authoritative correlation, actual server
or path attribution and browser DNS remain not run or not implemented.

Rollback: remove this opt-in module, its focused tests and this document. It has
no configuration changes, background service, registration or persisted state.

### Official references

- [Python socket.getaddrinfo](https://docs.python.org/3/library/socket.html#socket.getaddrinfo): system-dependent resolution and explicit family/type filters
- [Apple getaddrinfo manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/getaddrinfo.3.html): native API and address-family semantics (archived reference, not current-device acceptance)
- [Python subprocess](https://docs.python.org/3/library/subprocess.html): explicit environment, process timeout limitations, kill and wait semantics
- [Python isolated/startup options](https://docs.python.org/3/using/cmdline.html): `-I` and `-S` behavior
- [Python multiprocessing](https://docs.python.org/3/library/multiprocessing.html): process start methods and spawn/import responsibilities
- [Microsoft Resolve-DnsName](https://learn.microsoft.com/en-us/powershell/module/dnsclient/resolve-dnsname?view=windowsserver2025-ps): the distinct Windows API required by this specification

## Windows system DNS sample

Implements the Windows portion of D-ENV v0.3 §20.4.2 / ENV-04A as an
opt-in library, `windows_dns_probe.py`. This batch does not enable a CLI,
audit-mode query, automatic runtime installation, or real-device acceptance.
macOS uses its independent adapter; Windows never falls back to getaddrinfo,
nslookup, another resolver, a new DNS server, or a browser.

### Contract and authority

`probe_windows_dns(QueryScope(...), verify_binding=..., verify_runtime=...,
approve_query=..., cancelled=..., budget=Budget(...))` requires trusted host
callbacks, with literal `True` results. Binding and runtime are checked before
approval, again immediately before execution, and after the child exits. A stale
binding discards observations. Callbacks are not implemented by this library and
must bound their own work. Serialized data or a boolean in a saved configuration
is not actual user consent.

The host must freshly establish the exact target device, desktop user, namespace,
effective Windows context, trusted local-drive absolute Windows PowerShell
executable, DnsClient module file, working directory and system root. Runtime
verification includes module/utility dependencies, loaders, effective execution
policy, filesystem ownership and replacement races. Passing a path-shaped string
does not verify any of these properties. UNC/device paths and parent traversal
are rejected, but local-drive paths can still refer to mapped drives or reparse
points: the host must reject those or prove their trust. No environment cleanup
claim substitutes for dependency or DLL-search verification.

Approval covers the exact normalized neutral hostname, its trailing-dot absolute
native query, one A or AAAA type, time budget and possible disclosure to configured
resolvers and upstream infrastructure. The host establishes neutrality; a
conservative Claude/Anthropic substring exclusion is an additional PC0 safeguard.
Approval of one type does not approve both. Nothing opens the contact gate.

### Native execution and bounds

A fixed UTF-16LE encoded command starts the explicitly bound Windows PowerShell
with `-NoLogo -NoProfile -NonInteractive`; no execution-policy bypass is used.
The query and bound module path travel as a bounded JSON document on stdin,
never interpolated into code or placed in process arguments. Automatic module
loading is disabled. The script imports the built-in Utility module under PSHOME
and the exact approved DnsClient module, then invokes the module-qualified
`Resolve-DnsName -Name ... -Type A/AAAA -DnsOnly`. It does not set `-Server`, flush
caches, supply credentials, alter configuration or retry via another protocol.
The native resolver may itself perform normal recursion/retries/CNAME resolution;
one library attempt is not a claim of exactly one network packet or upstream name.

Request input is limited to 4096 ASCII bytes, output and stderr independently to
8192 bytes, native rows and projected unique addresses to 128. Stderr is counted
and discarded. The child emits only address strings; the public report retains
counts/classes, never names, addresses, paths or raw diagnostics. The wall budget
is 0.05–15 seconds, default 5, plus up to one second for cleanup. Unbuffered pipe
reader/writer threads avoid POSIX selectors-on-pipes assumptions. Timeout,
cancellation and overflow kill and reap the owned child, join its pipe workers,
and close handles; failure to establish cleanup returns `CLEANUP_FAILED`.
Trusted code must not spawn descendants or transfer pipe handles. OS process
creation/termination and host callbacks cannot be hard-real-time bounded in
Python. A failed cleanup is never reported as completed or safely cancelled.

### Evidence and error interpretation

Reports use `guardian-windows-dns-probe/0.1`, source `windows-system-dns`, coverage
`windows_system_dns_sample_only`, and resolver API
`windows_Resolve-DnsName_DnsOnly`. A successful empty answer is recorded as zero
addresses, not an invented NXDOMAIN. Cmdlet failure maps conservatively to
`RESOLUTION_FAILED`; initialization/module failure to `DEPENDENCY_MISSING`;
raw PowerShell messages never become public errors. There is no inferred DNS
packet RCODE, server identity, routing, browser DNS or leak-absence result.
Cache and hosts origin remain possible/unknown. Non-global addresses are not
called pollution; Fake-IP requires separate configured-range evidence.

### Tests and remaining acceptance

Run `python -m unittest discover -s tests -p test_windows_dns_probe.py -v`.
The Linux run covers validation, exact consent, fresh/revoked identity, privacy,
fixed PowerShell command construction, result schemas, synthetic subprocess
stdout/stderr floods, cancellation, timeout and reaping. A Windows-only test runs
the fixed script against an owned temporary **mock** DnsClient function, checking
zero/one/multiple answers and exact A/DnsOnly arguments without any DNS query.
It is skipped on Linux and is not evidence of native Resolve-DnsName execution.

Actual Windows PowerShell/DnsClient versions, module trust, execution policies,
managed-device restrictions, native errors, IPv6, cancellation and target user /
namespace behavior remain `not_run`. A separately authorized real Windows test
must close those gaps. No real DNS request was made during development.

### Primary references

- [Microsoft Resolve-DnsName](https://learn.microsoft.com/en-us/powershell/module/dnsclient/resolve-dnsname?view=windowsserver2025-ps): DnsOnly excludes LLMNR/NetBIOS; omitting Server uses configured interface DNS; A and AAAA are explicit record types
- [Microsoft about_PowerShell_exe](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_powershell_exe?view=powershell-5.1): NoProfile, NonInteractive and EncodedCommand invocation

### Rollback

Remove this isolated module, its test and this guide (and any separately approved
packaging/report registration). There are no network settings, services, cached
credentials or installed dependencies to undo.

## ENV-04A: bounded Mihomo DNS sample

Implementation of the Mihomo portion of D-ENV v0.3 §20.4.2. This is an opt-in
library integration, not a CLI, native ownership adapter, or completed ENV-04.
Importing the module causes no I/O. Inventory audit permissions remain unchanged.

### Private host boundary

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

### Transport and response boundary

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

### Public evidence and limitations

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

### Primary sources checked 2026-10-15

- [Official Mihomo API reference, Domain Query](https://wiki.metacubex.one/en/api/#dnsquery)
  specifies GET and the name/type parameters and DNS response fields
- [Official Mihomo route implementation](https://github.com/MetaCubeX/mihomo/blob/Meta/hub/route/dns.go)
  confirms Question is the DNS Question struct and answer keys are lowercase
- [Upstream DNS Question struct](https://github.com/miekg/dns/blob/master/types.go)
  establishes Name/Qtype/Qclass field names (no JSON rename tags)

These are mutable upstream references, not a claim of compatibility with every
Mihomo version. Unsupported response schemas remain blocked.

### Evidence and rollback

`python -m unittest discover -s tests -p test_mihomo_dns_probe.py -v`

Tests use injected data and test-owned loopback HTTP listeners only. The real
transport fixture forbids getaddrinfo, checks the exact request and absence of
credentials, and exercises framing/auth/redirect/cancellation handling. There
are no real-controller or public-DNS tests, no OS/user-device acceptance, no
configuration writes and no standing network authorization. Remove the three
new adapter/test/document files to roll back; there is no persistent state or
configuration to restore. Publishing requires approval for the eventual batch.

## ENV-04 bounded STUN transaction

### Delivered scope

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

### Host approval contract

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

### Bounds and lifecycle

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

### Evidence and privacy

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

### Protocol references and intentional limits

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

### Validation and rollback

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

## 离线探测证据投影：Mihomo DNS 增量

对应 ENV-04A / D-ENV-v0.3 §20.4.2，延续
[环境状态面板](environment-dashboard.md) 的 `--probes` 离线附件。
这一步只将已有 `guardian-mihomo-dns-probe/0.1` 结果接入 DNS 配置 / 查询行。
不调用控制器、不解析域名、不读取系统、不产生运行授权。

### 附件中的单条样本

```json
{
  "schema_version": "guardian-probe-evidence/0.1",
  "target_ref": "local-target-alias",
  "samples": [
    {
      "expected_path_kind": "mihomo_dns_query",
      "context": {
        "target_ref": "local-target-alias",
        "path_kind": "mihomo_dns_query"
      },
      "captured_at": "2026-10-15T12:00:00+00:00",
      "result": {"schema_version": "...replace with complete Mihomo result..."}
    }
  ]
}
```

`result` 是结构占位，须换成现有探测器的完整返回字典，不是可执行查询请求。
整个附件最多 64 条；沿用输入文件大小限制和重复 JSON 键拒绝。

Mihomo 的公开结果有意不包含设备、用户、命名空间或控制器绑定标识。
`context` 是宿主保存附件时可附加的声明，不是可从结果中恢复的真实身份。
目标别名只与附件的 `target_ref` 作一致性比较，路径只与固定类别和
`expected_path_kind` 比较；未与主盘点报告、当前设备或控制器做独立绑定。
缺少上下文显示未知；不匹配单独显示。JSON 布尔、来源字段、question_matches
或 gate_state 均不能建立可信宿主来源、操作授权或就绪通过。

成功返回读取 fact 的 `observed_at`，失败无 fact 时可读取附件的 `captured_at`。
两者都是未核验的时间声明；渲染时间从不填补缺失的采集时间。
缺失、未来、非法、超过 24 小时的时间保持相应缺口；取消/失败可同时显示时间无效或过期。

### 展示与严格边界

- 只显示 A/AAAA、地址族、rcode（0—4095）、截断标志、答案/地址/CNAME 数量、全局单播/非全局地址分类计数
- 计数必须是 0—256 的整数，布尔不算整数；分类数量与地址数量、答案分项必须一致
- completed 仅称“已记录响应声明”；rcode 非零和截断回复仍完整保留，不称 DNS 成功
- 失败报告不得夹带响应 facts；取消、超时、授权/权限缺口、绑定/响应上下文不匹配、其他失败均单独显示，不用普通未知吞掉
- 缺少/非法格式或自相矛盾的报告拒绝生成；不回显任意错误文本
- 多个样本保持原顺序，包括成功、负响应、取消和过期记录，不用最后一条覆盖旧记录
- 既有报告错误或授权缺口及其说明继续保留；样本响应不能掩盖它们
- 缓存/hosts 来源、Fake-IP、上游链路与真实请求均未核验，地址分类不能推断可达性、污染或泄露
- DNS 泄露、浏览器、IPv4/IPv6 HTTPS、STUN、一般 UDP、TUN 和失效保护均不取得新的检测证据
- 不显示域名、IP、端口、设备/用户/实例别名、响应自由文本、凭据或调用指令

主表仍为原来的三列。响应细节在 DNS 行折叠证据内；行验证状态不因样本而通过。
本接口不构造 workflow_guard.Evidence、不打开接触门禁，也不触发后续操作。

### 回归与限制

```sh
python -m unittest discover -s tests -p test_mihomo_dashboard.py -v
python -m unittest discover -s tests -p test_probe_evidence.py -v
python -m unittest discover -s tests -p test_status_dashboard.py -v
```

Mihomo 兼容性测试调用实际探测函数并注入字节响应；禁止 socket、系统 DNS、
subprocess 与渲染期间的 probe 调用。覆盖两族、负响应/截断、失败无事实、上下文、
非法计数、时间、混合样本和秘密哨兵。没有实际控制器、公网 DNS、真实设备或浏览器渲染验收。
回滚本次投影分支、状态标签和新增测试/文档即可；没有持久配置或运行状态变更。

### macOS / Windows 系统解析样本

还可在同一附件中导入两个分别定义的结果，全部只进入 DNS 配置 / 查询行：

| 输入 schema | coverage | fact source_ref | value resolver_api / 附件路径类别 |
| --- | --- | --- | --- |
| guardian-os-dns-probe/0.1 | macos_system_resolution_sample_only | os-system-resolution | macos_getaddrinfo |
| guardian-windows-dns-probe/0.1 | windows_system_dns_sample_only | windows-system-dns | windows_Resolve-DnsName_DnsOnly |

`context.path_kind` 与 `expected_path_kind` 使用上表最后一列的精确值，
`context.target_ref` 仍只与附件目标声明比较。schema、coverage、来源和 API 必须配套，
不能把 macOS getaddrinfo 改个标签当作 Windows Resolve-DnsName，更不能当作 Mihomo 查询。
任意未来 OS schema 均不自动接纳。来源名称是固定枚举，不显示输入的自由文本来源。

系统结果只提供最终地址数和分类数，不像 Mihomo 响应有 DNS rcode、截断、答案/CNAME 字段。
面板不会制造这些字段，也不会把空地址列表解释为 NXDOMAIN、IPv6 阻断或无泄露。
数量必须为 0—128 的整数（拒绝布尔），两类地址之和必须等于总地址数。
所有成功或空列表结果仅标“已记录响应声明”，保留独立的系统 API 来源标签。
DNS 报文、服务器、缓存/hosts 来源、Fake-IP 和上游实际路径仍未知。

失败无事实时保留固定错误码及取消、超时、授权/权限、目标不匹配等状态。
`UNSUPPORTED_PLATFORM`、`RUNTIME_NOT_TRUSTED`、`CLEANUP_FAILED` 等不是普通成功或未知；
Windows 的 `DEPENDENCY_MISSING` 也单独保留，不能静默安装依赖或尝试替代 API。
失败报告不得夹带 facts；未识别或矛盾的数据拒绝生成。错误码白名单不从附件扩展。
时间、上下文、既有报告错误/授权缺口、字段隐私和操作门禁沿用上述限制。

回归：`python -m unittest discover -s tests -p test_os_dns_dashboard.py -v`。
测试通过注入子进程 runner 取得实际 macOS/Windows 函数输出，并禁止原生解析与进程启动；
因此只能证明跨 schema 的离线投影，不代表 macOS、Windows 或用户设备的真实 DNS 验收。
