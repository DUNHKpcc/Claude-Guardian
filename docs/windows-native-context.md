# Windows owned-process context observation

Implements a narrow ENV-01 / D-ENV v0.3 §18.2, §19.2–3 observation library:
`windows_native_context.py`. It does not implement target binding, desktop-user
configuration collection, DNS permission, a launcher, or a production host adapter.
No I/O occurs on import. Only an already trusted host with scoped permission may
invoke it. No real Windows observations were collected during development.

## Bounded native reads

The adapter loads only fixed `kernel32.dll`, `advapi32.dll`, and `wtsapi32.dll`
with `LOAD_LIBRARY_SEARCH_SYSTEM32`; there is no PATH/current-directory search
fallback. Unsupported loading/platform/API failures stop with sanitized codes.
The intended baseline is Windows 8+ and a Python with WinDLL winmode support;
Windows 10/11 native acceptance remains not_run.

It reads the current process ID, current thread ID, process session, and active
physical-console session ID. It opens only the current process token, with
TOKEN_QUERY, and reads TokenUser, TokenStatistics, TokenSessionId, TokenElevation,
TokenIsAppContainer, TokenHasRestrictions, and TokenUIAccess. TokenUser's binary
SID and token/authentication/modification LUIDs remain private in memory. It
neither looks up an account name nor emits a SID. Token buffers are bounded and
pointer/length checked before copying SID data. All opened token handles close.

Before and after each native observation, OpenThreadToken tests the current
thread. A token causes conservative rejection and is closed; only ERROR_NO_TOKEN
allows use of process-token effective-user observations. Access denied, anonymous
impersonation, and other errors do not fall back to process identity.
OpenAsSelf affects the access check only; no impersonation is performed.

Before WTS queries, session 0, an unavailable console, and a session different
from the active console are rejected. WTSQuerySessionInformationW then reads only
WTSConnectState and WTSClientProtocolType on WTS_CURRENT_SERVER_HANDLE and
WTS_CURRENT_SESSION. It never queries another user's session. Only WTSActive and
console protocol 0 are retained; buffers are freed even on malformed results.
Elevation, AppContainer, restricted tokens, UIAccess, the three well-known service
account SIDs, and token/process session mismatch are conservatively rejected.
These exclusions do not establish that all remaining identities are desktop users.

No process/session/account enumeration, remote WTS server, domain-controller
lookup, environment dump, credential/token creation, privilege change, registry,
user directory, DNS query, or system setting change occurs.

## Crucial incomplete relation and supported next step

Being in the console session is not proof that the process account is the logged-on
console account. RunAs can place another user's process in the same session.
SID continuity, token authentication LUID continuity, and hostname equality cannot
prove the selected target, console-user equality, or execution namespaces.

WTSQueryUserToken requires LocalSystem and SE_TCB_NAME. This library intentionally
does not call it, request those rights, install a service, or resolve WTS account
names with LookupAccountName/LookupAccountSid (which can require network lookup).
Consequently even a successful observation returns:

- desktop_user_relation: unknown
- binding_state: blocked
- blocking_reason: CONSOLE_ACCOUNT_EQUALITY_UNPROVEN
- gate_state: closed

A supported future integration may use an **existing trusted host's** freshly
established desktop-account relation, selected target association, and execution
namespace attestation. The host must bind that attestation to this exact owned
process/effective-user/session observation, retain the comparison privately,
recheck both immediately around the requested operation, and invalidate it on
context changes. An unsupported host must leave the relation unknown and offer
its supported native-target route or narrowly scoped manual collection. No new
persistent privileged helper is the default or a prerequisite imposed by this
observer. Designing and validating that trusted-host integration is outstanding;
this library accepts no caller boolean or serialized document as that attestation.

In particular, `recheck_context` must not be wrapped as an always-True
`windows_dns_probe.verify_binding` callback. The DNS adapter's independent
selected target, desktop-user, namespace, runtime/dependency, and exact live
query-approval obligations remain unchanged.

## Private lifecycle and runtime limits

`capture_current_context(max_age_seconds=30, cancelled=...)` returns an ephemeral
private ContextHandle. `recheck_context(handle, cancelled=...)` compares a fresh
double observation and returns sanitized facts. The validity interval is 0.1–60
seconds; capture and recheck detect cancellation, elapsed budgets, clock reversal,
and differing process/thread/token/session/runtime observations. A handle cannot
be rechecked on a different thread. Native synchronous API calls cannot be
forcibly interrupted by this Python deadline. Observations are not atomic;
changes after the final read or changes that revert between reads remain possible.

`describe_context` is a historical snapshot, not a freshness check. The handle
has a redacted repr and refuses pickle. Python code in the same interpreter can
inspect private fields or forge objects: this is an API convention, not a security
boundary against hostile code. Do not serialize, introspect, or log its fields.
No operating-system handles survive capture or recheck.

The four runtime strings (sys.executable, cwd, sys.prefix, sys.base_prefix) receive
**syntax-only** local-drive absolute path screening. No path is opened or stat'ed.
Mapped drives, junctions, reparse points, ACLs, signatures, DLL/module dependencies,
execution policy, and replacement races remain unverified. An acceptable path
string is not local-storage proof or runtime trust. Reports explicitly say
runtime_path_screen=local_drive_syntax_only and runtime_integrity=not_verified.

## Evidence and rollback

`python -m unittest discover -s tests -p test_windows_native_context.py -v`
runs synthetic fixtures only on every platform. It checks foreign/service/remote
contexts, impersonation errors, private data, native buffer lengths/pointers,
cleanup, cancellation, expiry, mutation, path syntax, and closed binding. It does
not invoke Windows native APIs, even in Windows CI. The separate owned-CI smoke was run with explicit scope; after the class-21
compatibility fix, commit78535f69 run38772721879 reached CONTEXT_FOREIGN and
was explicitly blocked. This does not establish complete ABI or desktop
acceptance. Actual user-device checks still require their own authorization.

Remove this module, its test, and this guide to roll back, plus any separately
approved package registration. There are no installed dependencies, services,
credentials, or device settings to undo.

## Primary Microsoft references

- [GetTokenInformation](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation): query access, structures and lengths
- [Token information classes](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_information_class) and [TOKEN_STATISTICS](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_statistics): token/session/change metadata
- [OpenThreadToken](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openthreadtoken): current-thread access and impersonation failures
- [WTSQuerySessionInformationW](https://learn.microsoft.com/en-us/windows/win32/api/wtsapi32/nf-wtsapi32-wtsquerysessioninformationw) and [WTS_INFO_CLASS](https://learn.microsoft.com/en-us/windows/win32/api/wtsapi32/ne-wtsapi32-wts_info_class): local current-session state and protocol
- [WTSGetActiveConsoleSessionId](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-wtsgetactiveconsolesessionid): physical-console session and transition sentinel
- [WTSQueryUserToken](https://learn.microsoft.com/en-us/windows/win32/api/wtsapi32/nf-wtsapi32-wtsqueryusertoken): privileged service requirements; deliberately not used
- [LoadLibraryExW](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-loadlibraryexw): constrained system32 DLL search

### Native CI failure localization

Windows ContextError may carry fixed `stage` and `reason` diagnostic enums in
addition to the unchanged public error code. These locate an existing failure
boundary (DLL initialization, owned token/session read, SID bounds, WTS state or
protocol, identity validation, runtime syntax, or cleanup). They contain no API
return values, PID, SID, path, account name, or raw native error. The smoke harness
must independently allowlist them before output. They do not authorize extra
reads, weaken validation, or turn CONTEXT_UNKNOWN into an accepted headless
outcome. Diagnostics remain observations; Windows CI evidence must be recorded
separately from user-device acceptance.

### TokenHasRestrictions compatibility boundary

Microsoft's [TOKEN_INFORMATION_CLASS reference](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_information_class)
documents a DWORD for TokenHasRestrictions (class 21). A [first-hand reproduction
on Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/6000453/gettokeninformation-tokenhasrestrictions-21-return)
reports successful calls returning one byte and modifying only that byte; the
answer explicitly does not establish an official cross-version contract.

The dedicated class-21 reader therefore supplies a zero-initialized four-byte
buffer and accepts returned lengths exactly 1 or 4. A one-byte result with any
nonzero trailing byte is rejected, as are every other length and API failure.
Every nonzero restriction value still fails context validation. The generic
fixed-size reader, other token classes, elevation/user/session checks, and closed
binding are unchanged. This is a narrow compatibility provision, not a general
rule for accepting short native structures.

CI run 38771591206, Windows job 116548509922, localized the pre-fix failure to
`token_restrictions / return_size_mismatch`. That observation proves a size
mismatch, **not its exact returned length**. Whether this compatibility change
addresses the observed runner failure must be established by the subsequent
native CI run; synthetic coverage alone cannot establish that result. No
user-device compatibility is claimed.
