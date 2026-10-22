# Narrow PC0 diagnostic session

`diagnostic_session.py` connects a live consent boundary, the actual-platform current-context
observer, the existing system DNS probe, and the existing sanitized dashboard.
This is a first callable vertical slice of ENV-01 / ENV-04 and UI-I01–I06, not the
full ENV-01/02 inventory, Codex-native UI, full interview, environment acceptance,
or permission to enter PC1. The contact gate remains closed in every outcome.

## Standalone terminal fallback

First establish the current task, explicitly select local / VM / VPS, declare
the necessary network resources and configuration state, and obtain approval for
the exact check. A trusted host must assemble the current sanitized
`guardian-environment-entry-input/0.1` declaration from those actual choices;
saved interview answers are not an execution grant. See
[environment entry order](environment-entry-decision.md).

This session's native adapters observe the current local desktop only. Eligible
VM/VPS declarations do not create an adapter or prove host/guest identity. Unknown,
withdrawn or otherwise ineligible routes block target reads; route/target changes
invalidate dependent bindings and plans without discarding recovery obligations.

On the intended Mac, inside an already trusted local host, supply the independently
prepared declaration through a private, local, hydrated JSON file:

```sh
python3 skills/claude-guardian/scripts/diagnostic_session.py --target-ref my-mac \
  --entry-file /approved-private-directory/entry.json
```

The path is a placeholder, not a bundled file or permission record. The declaration
must satisfy `environment_entry.require_entry(entry_request, 'offline_precheck',
'my-mac')`; it establishes entry eligibility only. The current `--entry-file` safe
reader is POSIX-only. On Windows, a reviewed trusted host must instead pass the
dictionary explicitly through `run(..., entry_request=...)` or
`execute(..., entry_request=...)`, retaining all target binding and live consent
requirements. Do not pass both a file and an in-process declaration. This does not
claim Windows command-line file support.

The declaration names the intended target; it does not independently identify the
hardware or prove the process is outside a remote/container namespace. Before
any context collection, the terminal displays the exact narrow read scope and
requires `APPROVE` followed by a newly generated random nonce. It rejects piped
input and nonterminal prompts, clears type-ahead, rejects reused responses, and
expires approval after 30 seconds. Windows uses bounded `msvcrt` console polling
(no blocking stdin readline), rejects redirected/nonstandard input, limits the
initial type-ahead drain to 80 characters and 250 ms, and cancels on control or
extended-key input. Nonfinite, invalid or reversed monotonic clocks fail closed. EOF, any other answer, or Ctrl-C cancels.
There is no `--yes`, approval import, environment-variable approval, saved grant,
DNS option, client launch, configuration mutation, dependency installation, or
browser opening. A pseudo-terminal can be automated: this is fresh user-intent
interaction, not authenticated human identity or host/OS permission.

On macOS the scope is only current process identity, primary console/session
metadata, and metadata for fixed interpreter/current-directory/prefix path chains.
On Windows it is the owned process token, current-thread impersonation check,
current-session/console state, and syntax-only inspection of four runtime paths.
The backend is selected from the actual process platform, never an input flag. It does not
scan applications, inspect proxy configuration, read credentials, or call the
broader `guardian.native_check` under fabricated namespace assertions. The latter
remains a separate host-integrated collector. See `native-context.md` for native
API, continuity, path-screen and platform limitations; Windows details are in
`windows-native-context.md`. Linux fails closed;
a cloud result must never represent the user's Mac. Missing permission, inactive
console, unsupported context, symlinked runtime paths, and expiry remain visible.

If strict macOS context capture fails specifically with `RUNTIME_PATH_INVALID`,
the session may recover a useful partial observation using
`observe_context_metadata` within the remaining original 60-second budget
(capped at five seconds for this retry). This repeats only the already approved
metadata scope. It never resets the deadline and returns no context handle.
The original path-screen failure remains visible; runtime and namespace trust
remain unknown. Even when a DNS host and queries were supplied, this partial
path does not invoke host verifiers, request DNS consent, or launch a query.
Identity, permission, cancellation, expiry, and other failures do not trigger
this fallback. A later failure or late result discards the partial observation.

JSON goes to stdout. The callable API also returns HTML in memory. To explicitly
save a dashboard to a new private, local, already-hydrated file:

```sh
python3 skills/claude-guardian/scripts/diagnostic_session.py --target-ref my-mac \
  --entry-file /approved-private-directory/entry.json \
  --dashboard-output /approved-local-directory/session.html
```

There is no implicit save or overwrite. Parent storage must be independently
verified local/hydrated; path screening does not prove mount locality or eliminate
all filesystem races. Existing files are refused; new POSIX files use mode 0600. The shared `guardian.save_new` boundary and this session’s early validation
reject Windows output paths containing UNC/device namespaces, alternate streams, reserved device names in any
component, and trailing-dot/space aliases before collection or opening a file.
This is syntax screening only, not a mapped-drive/reparse-point or ACL proof.
Windows permissions inherit the parent directory ACL; mode 0600 does not establish
Windows privacy. Choose an already verified private local directory.
Review before sharing even sanitized machine metadata. A dashboard can show a
blocked session; saving a page does not mean collection succeeded. A cancelled or
declined session never creates the requested dashboard file (ENV-T123).
Exit codes: 0 partial usable metadata (never environment pass), 2 blocked/input/
save failure, 3 cancellation. Help is JSON and performs no collection.

## Trusted-host DNS integration

`execute(target_ref, consent=..., entry_request=..., dns_host=..., queries=...,
interview=...)` is the callable entry point. Metadata requires the current
`offline_precheck` entry; every DNS query also requires `active_probe` eligibility
and its separate live target/endpoint authorization. Declarations are rechecked
around callbacks; changes block the session. `DNSHost` requires a typed `os_dns_probe.Binding` plus all
three actual host implementations:

- `verify_binding(binding)`: current selected device, desktop user, filesystem
  and network namespaces, and effective execution context
- `verify_runtime(binding)`: interpreter, standard library, extension/loader
  dependencies, working directory, and replacement/launch-race protection
- `verify_neutral(scope)`: approval of this exact endpoint as neutral in PC0,
  beyond the probe's defensive rejection of Claude/Anthropic names

No production implementation of those host prerequisites is provided by this
session. Do not substitute always-true callbacks, caller-provided JSON booleans,
root-owned path modes, or a positive native-context observation. The standalone
CLI therefore stays metadata-only and explicitly reports DNS host integration
missing. Windows observations explicitly preserve `desktop_user_relation=unknown`,
`binding_state=blocked`, and `CONSOLE_ACCOUNT_EQUALITY_UNPROVEN`: same console
session is not proof of console-account equality. This session does not integrate
Windows DNS even if a caller supplies a host object; requested queries stop with
`WINDOWS_SESSION_DNS_UNAVAILABLE` without calling macOS DNS or host verifiers.
A usable Windows metadata report does not unlock DNS or target authority.

Python callbacks are trusted integration code, not an adversarial-code
sandbox. Each callback must bound its own execution and enforce its host policy.

The `consent` callable receives one exact structured scope at a time and must
obtain genuine fresh operation-specific user intent through the actual host UI.
`TerminalConsent` is the provided terminal fallback. Returning true because a
saved interview/report says “approved” violates the integration contract. An
optional interview is used only for `interview_flow.assessment` coverage and
unresolved counts; it can never satisfy the action gate.

For the macOS callable integration, at most eight explicit `(hostname, A-or-AAAA)`
pairs may be supplied. For each:

1. Recheck the private current-context handle and host binding/runtime/neutrality
2. Show partial metadata findings, exact trailing-dot hostname, query type, target,
   one API-call budget, and potential disclosure to configured resolvers and
   upstream providers; the user may decline independently of local reading
3. Recheck continuity, consume one in-memory approval for the exact immutable
   query/budget, and run the existing bounded `probe_os_dns` operation
4. Recheck again before retaining a sanitized result; preserve both successful
   and failed samples in the dashboard instead of hiding earlier failures

The context lifetime is 60 seconds across the session. The session also checks
its original monotonic deadline before and after each strict-context recheck,
so delayed capture/recheck cannot silently refresh the original budget. A slow consent cannot
silently refresh the handle or inherit approval for a new context; restart the
session instead. The DNS operation retains its separate five-second budget and
existing process cleanup limitations. Callback execution and synchronous native
APIs are not forcibly interruptible. Cancellation cannot retract already-sent
traffic. A terminal read observes its own deadline; a trusted UI callback must
implement equivalent expiration and cancellation.

Cancellation, consent timeout, context expiry/change, binding failure, runtime
failure, probe timeout, or cleanup failure stop further queries. Negative host-verifier verdicts and
unexpected host-verifier, context-recheck or cancellation-poll exceptions are
latched as stable trust failures, including
when the DNS library sanitizes callback errors; later successful rechecks cannot
restore that session. Previously
collected metadata becomes historical (`stale`), retained sample context is
invalidated, and no new facts are accepted after context change. Ordinary
resolution failures remain visible and permit a separately approved next query.
DNS results are counts, not addresses; raw hostname, local paths and device/user
aliases are absent from returned reports and HTML. The per-operation private
prompt necessarily displays the exact selected hostname and target alias.

The dashboard intentionally treats stored samples as unverified declarations.
Successful system resolution does not establish DNS packets, actual servers,
upstream routes, absence of leaks, runtime trust, complete environment readiness,
or platform permission. No output is a resumable capability.

## Evidence and rollback

```sh
python -m unittest discover -s tests -p test_diagnostic_session.py -v
```

54 synthetic session tests exercise the actual session plus existing DNS library and
existing dashboard using injected context and resolver responses. Tests cover
separate consent, nonce replay, bounded partial terminal input, decline/cancel,
delayed approval, target rebind, context change after query, missing runtime or
neutrality, saved/imported authority rejection, mixed failures, closed gates,
sanitization, explicit new-file saves, Windows metadata routing/unknown binding,
Windows native-error/cancel paths, bounded fake-console input, type-ahead rejection,
clock anomalies, and oversized timeout rejection. Socket resolution and subprocess
creation are forbidden in these integration tests. They are not native Mac,
Windows, Codex UI, or real resolver acceptance evidence. No actual user-device
read or query was performed to build or test this flow.

Rollback removes this module, its focused tests, and this document. No persistent
service, system configuration, scheduled work, permission record, or grant is
created. The integrated package explicitly includes the session and context modules; package tests check their presence. The shared
Windows output-path regression is additionally covered by four tests in
`tests/test_save_paths.py`, including retained POSIX no-overwrite/symlink behavior.

2026-10-16 boundary increment: 15 additional synthetic regressions in
`tests/test_diagnostic_session_boundaries.py` plus the 54 existing session tests
pass. They cover original-deadline enforcement, transient adapter failure latching,
historical evidence invalidation, unchanged healthy two-query projection, cancelled
no-save and explicitly requested blocked-report saves. Baseline-failure and full
batch results are in git 历史中的 `docs/validation.md`（已移出，见 ADR-024）; no real host or DNS acceptance is implied.
