# Input and export boundary review: ENV-T34 and ENV-T121

Date: 2026-10-21 UTC. Verification layer **L**, dependency **A** (cloud, deterministic, no user machine, no real
account, no external request). This review is bounded sentinel coverage of the listed public paths. It is not
universal secret detection, native evidence, or a model-dialogue review.

## Original requirements

Quoted from `skills/claude-guardian/sources/design/D-ENV-v0.3.md`:

- **ENV-T34** (line 794), scenario "exported report contains a proxy password or subscription token":
  the privacy check fails and the secret is not exported.
- **ENV-T121** (line 916), scenario "input carries an arbitrary command or URL, or a report carries an unknown
  secret field": input and output schema and local filtering reject it; display-layer masking is not a remedy.

The original ID, scenario, requirement and layer in the ledger are unchanged.

## Design decision

Before this review the status dashboard, the Agent remediation selector and the probe-evidence reader dropped
unknown members while projecting. That hides the secret but does not reject it, which is what ENV-T121 asks for.
The project owner confirmed on 2026-10-21 that these paths should reject. Unknown members are now refused at the
input boundary with a fixed error code; the member name and value are never echoed.

Source baseline for the change: `29f9d39e0cd4438ff4cd5eac1835ec42fdccd0bb`. Source changes landed in `08896fe`
(dashboard) and `75dc6fb` (shared check, selector, probe evidence). The commit that adds this page adds the
regression matrix and registration.

## Covered paths and observed outcomes

All markers are the synthetic string `SYNTHSECRETQ7Z9K2` or a URL/command embedding it. Each case checks stdout,
stderr and every file the command created. An unmodified control is accepted in every group.

| Path | Injected | Expected | Observed |
|---|---|---|---|
| `guardian.py analyze` / `plan` on an offline fixture | unknown root members: password, command, url_to_test | rejected (exit 2 or 3), marker absent | as expected |
| `status_dashboard.py --input` | 10 placements: root (3), snapshot, target_binding, privacy, limits, contact_control, fact, finding | `DASHBOARD_REPORT_INVALID`, no HTML written | as expected, both report schemas |
| `agent_remediation.py select --input` | the same 10 placements | exit 2, marker absent | as expected |
| `status_dashboard.py --probes` bundle | unknown members at bundle, sample item, context, HTTPS, STUN and DNS result level; forged `authorized`/`verified`/`provenance` | `DASHBOARD_PROBE_REPORT_INVALID`, no HTML | as expected; real HTTPS and STUN producer output still accepted |
| `interview_cli.py --answer-file` | secret as value, source URL, unknown keys, id and state; batched form | rejected with `INVALID_OR_UNAUTHORIZED_INTERVIEW_IO` | as expected (7 cases) |
| `interview_cli.py --context-file` | unknown password, URL and command members | rejected | as expected (3 cases) |
| `repair_cli.py preflight` / `plan` / `diff` (POSIX) | unknown members in the request document, remedy request, binding, intent and entry file | exit 2, marker absent, no stray file | as expected (6 cases x 3 commands) |
| Hostile **values** under known members (fact value, next actions, missing fields, target alias) through the dashboard and the selector | marker inside the value | marker never reaches any output | as expected |

Tests that carry this evidence:

- `tests/test_secret_boundary_matrix.py` (six tests, the deterministic cross-path matrix);
- `UnknownFieldRejectionTests` in `tests/test_status_dashboard.py`;
- `UnknownMemberRejectionTests` in `tests/test_agent_remediation.py` and `tests/test_probe_evidence.py`.

Existing tests that continue to run in the full suite and are relied on, not newly probed here:
`tests/test_inventory_export_boundaries_rebuild.py` (inventory import and static request), `tests/test_inventory_cli.py`,
`tests/test_installed_skill.py` (allowlist and private sentinels in the package), and the sentinel tests listed for
T11, ENV-T34 and ENV-T121 in `docs/test-coverage-map.md`.

## Failing-first receipts

- Matrix test against the pre-change tree `29f9d39`: 20 failures (dashboard 10, selector 10), all on the
  unknown-member cases; controls and hostile-value cases passed.
- Dashboard unit tests on the unchanged dashboard: 28 failing subtests. Selector tests: 21. Probe evidence: 8.

## Existing tests that changed, and why

Seven existing tests asserted that unknown members were silently ignored. The owner decision above replaces that
contract, so they now assert refusal and keep every other assertion. None was deleted or weakened:

- `test_status_dashboard.test_no_arbitrary_text_or_secrets_survive`: only the unknown `secrets` root member was
  removed from the injected input.
- `test_traffic_policy`: the four forged success flags are asserted rejected; the forged `traffic_policy`
  assertions are unchanged.
- `test_probe_evidence.test_success_is_only_imported_declaration` and the Mihomo and OS DNS dashboard tests
  (three sites): forged `authorized`/`verified`/`provenance` members are asserted rejected, then the unforged
  projection is asserted to remain `unverified_import`.
- `test_probe_evidence.test_no_secret_address_identity_or_markup_survives` and
  `test_mihomo_dashboard.test_unexpected_strings_html_secrets_never_echoed`: the unknown `extra` member is now
  asserted rejected without echo. Forged values under known members, including `path_association='verified'`,
  stay in the projection checks.

## Not claimed

- Arbitrary-secret recognition. Credential-shaped screening of aliases is a narrow defense in depth. A secret placed
  in a free-text value of a known member is not recognized by content; the covered paths either project that value
  through a whitelist or reject it, and the matrix asserts it never reaches an output.
- Closed vocabularies for DNS probe fact values. They are checked by the existing strict required-key validation.
- Paths not re-probed: cleanup plan and receipt files, recovery receipts, the diagnostic-session entry file (closed
  schema through `environment_entry.require_entry`, covered by existing tests), `serve_webrtc.py` output, and a
  content scan of the packaged archive beyond the existing installed-skill test.
- Any real device, real host stdout/stderr pipeline, real proxy configuration, browser or network path. Native and
  user-device acceptance for other cases is unaffected and remains pending.
- A fresh model dialogue. This review is code and file level only.

## Reproduce

From the repository root:

    python3 -B -m unittest discover -s tests -p test_secret_boundary_matrix.py -v
    python3 -B -m unittest discover -s tests -v
