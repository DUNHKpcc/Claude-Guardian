# CI-owned native context smoke

Requirement scope: ENV-01/02, ENG-01, D-ENV §18.2 and §19.1–19.3/19.6.
This adds runner-process ABI evidence, not VAL-01 desktop acceptance or a
trusted-host authorization implementation. Runtime collectors are unchanged.

## Activation and bounded child

The three-platform `tests.yml` workflow has a separate step setting
`GUARDIAN_NATIVE_CONTEXT_CI=1`. Both that exact value and
`GITHUB_ACTIONS=true` are required. Normal test discovery runs only synthetic
boundary checks and skips the native smoke. Linux records an explicit n/a skip.
These flags scope a test harness, not a permission mechanism for product code.
Do not enable them on a user's desktop without separate scoped authorization.

The Mac/Windows test launches only the current CI Python interpreter in isolated
mode with the fixed test file and `--native-child`. No arbitrary command, module,
URL, endpoint, or executable argument is accepted. The owned child imports its
platform's existing collector, captures once with a five-second internal budget,
and rechecks the private handle in that same process/thread. The parent imposes
a separate 15-second wait, kills a timed-out child, and waits at most two seconds
for reap and two seconds for the reader. Native synchronous calls cannot evade
the parent timeout by ignoring the collector's cooperative budget.
Kill, wait/reap, reader-start/join, and pipe-close failures produce a fixed
cleanup failure without raw exception details. A timed-out or failed initial
wait still triggers a bounded reap attempt when killing fails.

The reader retains at most 2,049 bytes, kills on overflow, and accepts at most
2,048 bytes. Stdin and stderr are discarded. Python diagnostics inside native
collection are suppressed. The parent never prints unexpected stdout, exception
text, handles, usernames, identifiers, token/SID values, or runtime paths. Only
allowlisted state/code/phase values are emitted. No native data artifact is saved.

## Exact read scope and compatibility

- macOS: fixed absolute Apple framework calls already declared in
  `native_context.py`, caller security session, primary-console UID (returned
  name released without conversion), current graphical-session fields, own POSIX
  process identity, and bounded lstat ancestor chains for the interpreter, cwd,
  prefix, and base prefix. No directory listings or file-content reads
- Windows: system32-only kernel32/advapi32/wtsapi32, current process/thread handles,
  query-only own token metadata, active-console session number, and current-session
  WTS state/protocol only after session equality. Runtime paths are syntax checked
  only. No other-user/session enumeration, account-name resolution,
  WTSQueryUserToken, elevation, privilege enabling, or persistent helper
- Neither path makes an external request, uses DNS, changes a proxy/browser,
  touches Claude, creates credentials, or reuses a real user's context

The current native modules are the source-compatibility contract: fixed
`capture_current_context(max_age_seconds=5)` then `recheck_context(handle)`;
private handles never cross the child boundary. Explicit ctypes signatures and
System32/absolute-framework selection remain covered by the separate synthetic
module suites. The smoke validates the closed gate, empty changes, unknown
namespaces, unverified runtime integrity, and unchanged `native_platform_validation`
field; Windows additionally retains unknown desktop-user relation and blocked
binding. It intentionally does not rewrite collector reports as certified.

## Interpreting results

- `observed / CONTINUITY_OBSERVED / recheck`: capture and recheck completed on that
  particular runner. Still no device association, user desktop acceptance,
  namespace proof, runtime/dependency trust, or permission for later operations
- `blocked`: unittest records a skip with the exact allowlisted code and phase.
  Headless, foreign, remote/inactive, mismatched-user, permission-denied, and
  rejected runtime-path conditions are legitimate fail-closed outcomes. Later
  ABI paths may never have been reached; a blocked smoke is not ABI success
- Unknown context errors (including possible ABI problems), unexpected exceptions,
  cleanup/expiry errors, crashes/nonzero exits, timeout, overflow, invalid output,
  or weakened report contracts fail the test. They are never relabeled as blocked
  Strictly validated failure code/phase enums and a bounded integer process exit
  status are included in the failure message, even when the child exits nonzero.
  Unknown/malformed output stays suppressed; a valid failure envelope or a
  nonzero exit can never become an observed/blocked success.
- Linux n/a and disabled smoke are explicit skips, never native passes

Before publication only the synthetic tests have been executed in this Linux
workspace. Record each exact post-publication CI run and platform result
separately; do not infer native execution from an overall green workflow.
The older general metadata smoke remains a distinct check and does not substitute
for this context collector's result. Roll back by removing this test, workflow
step, and guide; there are no installed services or configuration changes to undo.

## First native-run diagnosis

Run 38767766447, Windows job 116535339412, failed the native-context step while
its ordinary unit suite passed. The original parent decoder discarded nonzero
child envelopes, so that log did not establish an ABI root cause. The diagnostic
change preserves failing semantics and exposes only reviewed error enums and
capture/recheck stage plus exit status. Native success is still unestablished.
The macOS step on that run was explicitly blocked with RUNTIME_PATH_INVALID
at capture; this does not establish full ABI or desktop acceptance.

Run 38769891354, Windows job 116542628031, subsequently returned the sanitized
failure `exit=1; code=CONTEXT_UNKNOWN; phase=capture`. This establishes a native
capture failure, not its root cause. Windows native-context failures may now add
exact `stage` and `reason` fields drawn from fixed code vocabularies, including
literal `unknown`. Missing or unrecognized attributes become `unknown` inside
the child; the parent independently rejects unrecognized enum values, partial
fields, extra fields, and diagnostic fields on observed/blocked envelopes.
These fields are diagnostics only and every such envelope still fails. No native
return values, last-error numbers, paths, identifiers, or exception text are
included. The next CI run is needed to identify the failing branch.

## Verified follow-up outcome

Commit `78535f69b523287a0304c1be017dd60e491554f0`, run
[38772721879](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38772721879),
completed successfully on all three platforms. After the class-21 return-width
fix, Windows capture reported the existing `CONTEXT_FOREIGN` blocked condition;
macOS capture still reported `RUNTIME_PATH_INVALID`. Both actual native tests
were explicit skips, not observed contexts or complete ABI/desktop acceptance.
No additional blocked codes were introduced. The earlier failures remain part
of the diagnostic history. The new Mac metadata-only fallback was not exercised
by this strict context smoke.
