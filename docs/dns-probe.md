# DNS protocol groundwork (ENV-04, partial)

`skills/claude-guardian/scripts/dns_probe.py` is a standard-library, pure A/AAAA
message codec. It has **no socket, OS resolver, HTTP client, CLI, provider,
automatic trigger, or persistent state**. Importing it does no I/O. Creating query
bytes grants no permission to transmit them. No Claude hostname is supplied as a
default. PC0 contact restrictions continue to apply to every future adapter.

## Actual coverage

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

## API and bounded behavior

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

## Mihomo adapter integration checklist (implemented separately in this batch)

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

## Evidence and sources

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
