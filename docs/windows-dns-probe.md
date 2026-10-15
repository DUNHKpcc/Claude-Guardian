# Windows system DNS sample

Implements the Windows portion of D-ENV v0.3 §20.4.2 / ENV-04A as an
opt-in library, `windows_dns_probe.py`. This batch does not enable a CLI,
audit-mode query, automatic runtime installation, or real-device acceptance.
macOS uses its independent adapter; Windows never falls back to getaddrinfo,
nslookup, another resolver, a new DNS server, or a browser.

## Contract and authority

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

## Native execution and bounds

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

## Evidence and error interpretation

Reports use `guardian-windows-dns-probe/0.1`, source `windows-system-dns`, coverage
`windows_system_dns_sample_only`, and resolver API
`windows_Resolve-DnsName_DnsOnly`. A successful empty answer is recorded as zero
addresses, not an invented NXDOMAIN. Cmdlet failure maps conservatively to
`RESOLUTION_FAILED`; initialization/module failure to `DEPENDENCY_MISSING`;
raw PowerShell messages never become public errors. There is no inferred DNS
packet RCODE, server identity, routing, browser DNS or leak-absence result.
Cache and hosts origin remain possible/unknown. Non-global addresses are not
called pollution; Fake-IP requires separate configured-range evidence.

## Tests and remaining acceptance

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

## Primary references

- [Microsoft Resolve-DnsName](https://learn.microsoft.com/en-us/powershell/module/dnsclient/resolve-dnsname?view=windowsserver2025-ps): DnsOnly excludes LLMNR/NetBIOS; omitting Server uses configured interface DNS; A and AAAA are explicit record types
- [Microsoft about_PowerShell_exe](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_powershell_exe?view=powershell-5.1): NoProfile, NonInteractive and EncodedCommand invocation

## Rollback

Remove this isolated module, its test and this guide (and any separately approved
packaging/report registration). There are no network settings, services, cached
credentials or installed dependencies to undo.
