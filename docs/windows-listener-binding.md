# Windows selected-listener binding (ENV §19.2, §19.7–19.8)

## Actual capability and evidence

`skills/claude-guardian/scripts/windows_listener_binding.py` implements an opt-in,
read-only Win32 adapter. It has no CLI, automatic invocation, controller transport,
process launch/termination, configuration change, privilege adjustment, credential
read, command-line/environment inspection, file-path lookup, or discovery export.

Linux mocked tests cover scope/approval rejection, cancellation, invalid budgets,
PID/start mismatch, conflicting and wildcard binds, user/host-context mismatch,
revocation, stale samples, sanitized exceptions, and IPv4/IPv6 binary row layouts.
Native Windows acceptance is **not_run** until the separate opt-in Windows CI job
passes. A synthetic runner pass is not approval to inspect a user's computer and
is not acceptance of all Windows editions, sandbox configurations or controllers.
No user process audit is part of the test suite.

## Host contract: authorization is external

The host supplies a private `Selection`: task device/user/namespace aliases,
canonical numeric loopback IP, exact port, expected PID, expected process creation
FILETIME integer (100-nanosecond intervals since 1601). This module deliberately provides no discovery helper to
obtain the PID or expected identity. Do not derive identity from a process name,
port convention or controller response. IPv4 127/8 and canonical `::1` are accepted;
controller_inventory currently supports only `127.0.0.1` and `::1`, so its stricter
transport restrictions still apply.

Call `verify_listener` with trusted host callbacks:

- `approve_read(selection, budget)` consults current user approval for that exact
  endpoint, PID/start, executing context, and bounded local reads. It is rechecked
  before both samples and before returning success. A saved boolean, model input,
  an environment flag or this module's input validation cannot replace approval
- `verify_context(selection)` independently confirms the requested device, desktop
  user and namespace actually correspond to this execution context. A Windows OS
  string, same user SID is insufficient to prove
  ownership of the user's desktop. Unknown/sandbox/remote/WSL mappings must stop
- `run_native(operation, deadline, cancelled)` runs the callable with a host-enforced
  blocking-call timeout and cancellation/lifetime management, preserving verified
  native user and network context. The module checks time cooperatively; Python
  cannot preempt blocked Win32 calls. A thread join timeout that leaves native work
  running is insufficient. An already approved bounded host worker/watchdog is a
  possible integration; this module never creates a process. If the host lacks
  that facility, do not enable native reads

Callbacks themselves must be bounded by the host as well. `_reader` is strictly a
private offline-test seam; do not expose it through a request/configuration API.
The library does not validate that arbitrary supplied Python host code is honest.

## Native evidence and privacy

The adapter uses `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE)`,
`GetProcessTimes`, `OpenProcessToken(TOKEN_QUERY)`, `GetTokenInformation(TokenUser)`
and `EqualSid`. It compares selected process and executing process users without
serializing SID values. Impersonating threads are rejected rather than silently
using the wrong effective user. Missing rights fail closed; no elevation, token
mutation or fallback to other users is attempted. Creation times and zero-time `WaitForSingleObject` liveness results are checked
while holding a process handle and again in a second independent observation.
Exit FILETIME is undefined for a running process and is not interpreted. Missing
SYNCHRONIZE rights fail closed, without falling back to an ambiguous liveness test.

`GetCurrentThreadCompartmentId` is not used: Microsoft documents it as reserved
and says not to use it. Namespace/device mapping is exclusively explicit trusted
host callback evidence, never a native claim by this adapter. The result labels
this limitation as `host_callback_only_not_native_verified`. The host must block
unknown or changed network context; this adapter cannot independently establish
compartment equivalence, physical machine, desktop, WSL or container identity.

`GetExtendedTcpTable(TCP_TABLE_OWNER_PID_LISTENER)` is called for AF_INET and
AF_INET6. Microsoft offers a table API, not an exact-endpoint query: the bounded
OS table necessarily enters private collector memory. Only rows at the selected
port survive parsing; no global inventory is returned, logged or persisted. Each
buffer is limited to 1 MiB and 16,384 rows by default; allocation growth fails
closed without an unbounded retry. Production approval must disclose this API
scope. Process queries are only for the selected PID and the executing process.

The conservative binding rule requires exactly one selected-port row across both
families, matching the exact selected IP and PID. Wildcard, public, scoped,
duplicate and even legitimate other-family listeners at the same port block.
This deliberately trades availability for unambiguous evidence. No wildcard
conversion or cross-family inference is performed. Two independent observations
must match. A change fails closed; no automatic resampling or alternate PID.

Results include only a stable error code, same/unknown user relationship and a
binding verdict. All exceptions are sanitized. Private metadata and native error
text are absent. Success remains a non-atomic, momentary observation: a listener
can change after the last read. Recheck immediately around any separately
approved controller request. Same-user adversaries, socket handoff and races are
not strong authentication. This adapter alone does not verify product metadata,
selected data root, configuration ownership, routing or the full ENV instance
identity, and does not authorize controller requests. Keep readiness gates closed.

## Test execution and rollback

Offline: `python -m unittest discover -s tests -p test_windows_listener_binding.py -v`.

Native synthetic tests require Windows plus `GUARDIAN_WINDOWS_LISTENER_CI=1`,
set only by the dedicated synthetic-test step on a disposable Windows CI runner
with a hard job timeout. The parent CI integration owns this opt-in; production
code never reads this environment variable.
The test creates temporary IPv4/IPv6 listeners in its own test process, validates
its own PID/creation identity, closes each socket, and verifies the binding fails.
There are no accepted client connections and no application HTTP requests.
The opt-in is fixture authorization only; never treat it as production read approval.

Rollback: remove this unintegrated module, tests, documentation and the corresponding CI test step. There are no runtime integration changes or system state to restore.

## Primary Microsoft references

- [GetExtendedTcpTable](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-getextendedtcptable)
- [IPv4 owner-PID row](https://learn.microsoft.com/en-us/windows/win32/api/tcpmib/ns-tcpmib-mib_tcprow_owner_pid)
- [IPv6 owner-PID row](https://learn.microsoft.com/en-us/windows/win32/api/tcpmib/ns-tcpmib-mib_tcp6row_owner_pid)
- [GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes)
- [OpenProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess)
- [OpenThreadToken](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openthreadtoken)
- [GetTokenInformation](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation)
- [GetCurrentThreadCompartmentId](https://learn.microsoft.com/en-us/windows/win32/api/netioapi/nf-netioapi-getcurrentthreadcompartmentid)

- [WaitForSingleObject](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject)
