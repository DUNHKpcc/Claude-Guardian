# Narrow native context observation

Implementation: `scripts/native_context.py`. Requirement scope: D-ENV §18.2,
§19.1–19.3, §19.6 / ENV-01–02 / ENG-01. This is an internal, opt-in native
collector, not a CLI, permissions source, OS sandbox, full target verifier, or
replacement for the existing DNS adapters' host trust boundary.

## Implemented native reads

On macOS only, the collector uses fixed absolute Apple framework paths through
`ctypes`, with explicit ABI signatures:

- Security `SessionGetInfo(callerSecuritySession)` observes the calling security
  session. Root/remote sessions and sessions without graphic access are rejected
- SystemConfiguration `SCDynamicStoreCopyConsoleUser` observes the primary console
  UID; the returned name is released immediately without converting or exporting it
- CoreGraphics `CGSessionCopyCurrentDictionary` reads only the current graphical
  session's UID, on-console flag, and login-done flag, with CoreFoundation type
  checks and checked integer conversion. SDK CFSTR key macros are represented by
  three fixed UTF-8 literals using `CFStringCreateWithCString`, including the SDK
  `kCGSSession` spelling for UID/on-console keys. Owned keys and copied objects
  are released on success and failure
- Current-process PID, UID/EUID, GID/EGID, supplementary groups, and POSIX session
  come from the corresponding OS functions. Effective/real credential changes,
  root execution, a different console user, inactive or unknown sessions fail closed
- Runtime observations cover only the current Python executable, current working
  directory, `sys.prefix`, and `sys.base_prefix`, including their bounded ancestor
  chains. No directory listings, user-directory discovery, process enumeration,
  secret configuration reads, shell commands, subprocesses or network requests occur

The context is sampled before and after path collection. Handles can only be
rechecked within the same process and a monotonic lifetime of at most 60 seconds.
A changed PID, credentials/groups, session, runtime path, or observed inode/stat
identity is rejected. The handle is immutable, has a redacted repr, and rejects
pickling. Its private fields must never be serialized, logged, attached or sent
to the model. These conventions do not defend against malicious code inside the
same trusted Python process.

Windows and Linux/WSL return `UNSUPPORTED_PLATFORM` before loading native
libraries. The separate `windows_native_context.py` adds narrow current-token/session observation, but leaves console-account equality and runtime ACL validation unproven; neither that observer nor the Windows DNS adapter supplies full target binding.

## Host integration contract

1. The trusted host establishes its own approved runtime and the scope of local
   metadata reads before importing/calling this collector. A Python program cannot
   retroactively establish the integrity of the interpreter executing it
2. Call `capture_current_context(max_age_seconds=30, cancelled=...)` and retain the
   returned `ContextHandle` privately
3. Obtain the device selection/association from the real host environment and
   user-selected target. Label it a trusted-host assertion. Neither hostname,
   platform string, this observation, nor a JSON field proves device ownership
4. Call `recheck_context(handle, cancelled=...)` immediately before and after any
   separately authorized operation. Errors are stable `ContextError` codes and
   contain no native paths, usernames, UIDs or session IDs
5. Apply independent host checks for the exact execution namespace, runtime and
   dependencies, and live operation-specific approval. Existing probe callbacks
   remain responsible for those checks. A host with established approval may
   integrate this observation; the adapter does not permanently prohibit such a
   future flow, nor does it implement that host's approval mechanism

`describe_context(handle)` returns only a sanitized snapshot summary; it does
not recheck or claim freshness. `recheck_context` returns that same shape after a
fresh comparison. Neither function returns an authorization boolean. Reports
always retain `gate_state: closed`, namespace `unknown`, and runtime integrity
`not_verified`. Persisted reports cannot restore the private observation or grant
permission. No target-association or approval JSON parser is provided.

## Partial metadata without an execution handle

`observe_context_metadata(max_seconds=5, cancelled=...)` is a separate read-only
API, bounded to 0.1–60 seconds. It returns only a redacted dictionary, never a
`ContextHandle`. Its exact local reads still require prior host authorization.
It samples and validates identity before and after runtime screening and rejects
changed/inactive/foreign identity, cancellation, expiry and permission/unknown
errors. Only the restrictive `RUNTIME_PATH_INVALID` screen failure may produce
partial metadata. The report then explicitly contains:

- `observation_state: partial`
- `observation_kind: metadata_only_no_handle`
- `runtime_path_screen: blocked_path_invalid`
- `runtime_path_error: RUNTIME_PATH_INVALID`
- `runtime_path_continuity: not_established`
- `runtime_integrity: not_verified` and `gate_state: closed`

A normal metadata result also has no handle and makes no runtime-continuity
claim. This API cannot provide DNS bindings or approvals, and its dictionary is
rejected by `recheck_context`. The strict capture/recheck API retains its existing
path-failure behavior. An interactive host may deliberately use the metadata-only
API within its separately approved scope and remaining overall deadline; there
is no automatic retry, fallback, CI smoke reinterpretation, or gate change here.

The macOS job in [CI run 38767766447](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38767766447)
reported `RUNTIME_PATH_INVALID` during strict capture on macos-26-arm64. Its
privacy-preserving log does not identify the offending path or condition. A
symlink is one possible rejected condition, not an established cause. That run's
blocked smoke remains blocked; synthetic partial-metadata tests do not replace
native validation of this new API.

## Runtime path screening is deliberately incomplete

Symlinks, non-normalized paths, non-regular executable nodes, non-directory
ancestors, unreadable nodes and excessively deep paths reject strict collection. For
otherwise inspectable paths, non-root ownership or group/other-write mode bits
produce `rejected_writable_or_nonroot`. The native identity observation may still
be returned, but the path screen must not be used to approve that runtime.

The positive value is explicitly `root_owned_mode_screen_only`, never "trusted".
It does not check macOS ACL grants, signatures, stdlib/extension contents, dyld
loaded images or dependency closure, modified-in-place code, mount replacement,
or race-free execution. User-owned Homebrew/venv installs and user-writable
project working directories fail this restrictive screen. This is a diagnostic
subset, not a mandate to chown, chmod, reinstall, elevate, or move the user's
files. No such changes are performed or authorized.

Path metadata and session reads are not atomic. The before/after comparisons do
not detect an ABA change, prevent a later change, or lock the active user session.
Graphical console membership does not prove absence of a sandbox, VM, altered
filesystem view or different network context; these remain separate host checks.
Security sessions and graphical sessions are not interchangeable identifiers.

Native synchronous API calls and `lstat` cannot be forcibly interrupted by this
in-process implementation. Cancellation/expiry is checked between calls; a hung
OS service can exceed the requested lifetime before control returns. The result
then fails expiry. There is no retry, privilege escalation, installation or
background watcher.

## Evidence and rollback

`python -m unittest discover -s tests -p test_native_context.py -v` exercises
synthetic native function fixtures and synthetic file metadata only. Tests cover
ABI setup, resource release, typed CF values, unsupported platforms, inactive/
foreign/changed sessions, stale handles, cancellation, privacy and path-screen
limits. No real native desktop/session APIs or user-device reads were run.
Native macOS compatibility remains `not_run`; the separate Windows observer also has synthetic-only evidence.
This increment does not close any full ENV or VAL acceptance scenario.

Rollback: remove this standalone module, its test and this document; it has no
CLI integration and changes no existing collector behavior or system settings.

## Primary references

- [Apple: SessionGetInfo](https://developer.apple.com/documentation/security/sessiongetinfo(_:_:_:))
- [Apple: AuthSession API declarations and flag values](https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_authorization/lib/AuthSession.h)
- [Apple: primary console user API](https://developer.apple.com/documentation/systemconfiguration/scdynamicstorecopyconsoleuser(_:_:_:))
- [Apple: supporting Fast User Switching, security versus graphics sessions and active-console checks](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPMultipleUsers/Concepts/FastUserSwitching.html)
- [Apple-authored CGSession.h in the archived macOS SDK mirror: CFSTR key values](https://github.com/phracker/MacOSX-SDKs/blob/master/MacOSX10.8.sdk/System/Library/Frameworks/CoreGraphics.framework/Versions/A/Headers/CGSession.h)
- [Apple: CoreFoundation number conversion](https://developer.apple.com/documentation/corefoundation/cfnumber)

Consulted 2026-10-15. Source documentation supports the narrow call semantics,
not a claim of native execution, namespace isolation, or complete runtime trust.
