# macOS system-resolution sample (ENV-04A)

Implements the macOS `getaddrinfo` portion of D-ENV v0.3 §20.4.2 as an
opt-in library, `scripts/os_dns_probe.py`. Importing performs no I/O. There is
no CLI, discovery, installation, public-resolver fallback, cache flush,
configuration write or Claude/Anthropic request. This is a partial implementation,
not completion of ENV-04 or native platform acceptance.

## Why a macOS-only process adapter

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

## Authority and request semantics

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

## Timeouts, cancellation and output bounds

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

## Separate provenance and deliberately limited claims

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

## Evidence and remaining work

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

## Official references

- [Python socket.getaddrinfo](https://docs.python.org/3/library/socket.html#socket.getaddrinfo): system-dependent resolution and explicit family/type filters
- [Apple getaddrinfo manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/getaddrinfo.3.html): native API and address-family semantics (archived reference, not current-device acceptance)
- [Python subprocess](https://docs.python.org/3/library/subprocess.html): explicit environment, process timeout limitations, kill and wait semantics
- [Python isolated/startup options](https://docs.python.org/3/using/cmdline.html): `-I` and `-S` behavior
- [Python multiprocessing](https://docs.python.org/3/library/multiprocessing.html): process start methods and spawn/import responsibilities
- [Microsoft Resolve-DnsName](https://learn.microsoft.com/en-us/powershell/module/dnsclient/resolve-dnsname?view=windowsserver2025-ps): the distinct Windows API required by this specification
