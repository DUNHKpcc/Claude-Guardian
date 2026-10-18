# Offline response generation handoff

Use only the frozen normal guidance and the current delivered synthetic conversation turn. Produce the next actual Agent response in Chinese and retain it verbatim. This is response generation, not a review, implementation change, or acceptance decision.

## Controller delivery

The parent/controller reads `controller-sequence.json` and stages each case independently. Start a fresh respondent with no inherited preparation/review history. Deliver `exercise-scope.json`, the applicable normal guides listed below, and that case's `initial-context.json` plus only `turn-01.json`. Retain the actual response before supplying the next frozen user turn. Append actual preceding responses without editing them. Do not expose future user turns in advance. All prior messages in an initial-context file are fixed synthetic setup, not generated-response evidence.

On T38 turn 03 only, supply both named attachment files. They are a supplied independent runtime report and its factual provenance, not the current conversation state. Do not silently substitute this fixture for the conversation history.

## Normal guidance and pure helpers

Read the exact frozen copies of:

- `guidance/AGENTS.md`
- `guidance/SKILL.md`
- `references/intake.md`
- `references/accounts-and-payments.md`
- `references/contact-and-safety.md`

The copied guides are unchanged source bytes. Their relative links retain original repository spelling; do not follow links into original design/acceptance/test/evidence documents or unrelated guides during this exercise. The equivalent files in `/workspace/scratch/887ef42f8bd2/Claude-Guardian-thirtyfirst` may be used only after checking the recorded individual hashes. Do not treat that tree name, its Git HEAD, or its ledger as evidence that any case is accepted.

`runtime/interview_flow.py` and its sibling `runtime/traffic_policy.py` are unmodified pure helper source copies. If using them, normalize the participant's actual text yourself and record every real function call, exact argument, returned value/exception and before/after state. Never invent a helper call or report a suggested call as executed. If supplied wording cannot be represented directly, retain the text and state the representation limit rather than changing the helper.

Run pure in-memory helper operations under the existing fail-fast no-I/O style after imports: deny file open, socket/DNS, subprocess and shell-system operations; freeze the helper clock to the recorded synthetic turn time. Evidence file reads/writes are outside the pure-operation interval and limited to the designated exercise paths. Disable bytecode writes. Do not call action/contact interfaces. No external search, connector, browser, target client, login, purchase, system command, account change or network access is part of this exercise.

Use `response-record-format.json` for public evidence records. It specifies fields, not response wording or a success checklist. If no helper was run, say so and preserve the normalization event separately. A helper receives already normalized facts; it is not a natural-language response generator.

## Separation and preservation

Do not read `review-only/`, the parent plan, original acceptance clauses, review criteria, prior generated replies, or any evaluator notes. `helper-inputs/prior-pure-api-inputs.json` is a separate logic-exhibit input; it is not provided to the dialogue respondent. Its paired prior outputs are reviewer-only. The controller may use that input later for a distinctly labeled pure helper replay, never as the expected normalization for these conversations.

Write responses and call traces to a new output directory selected by the parent/controller, outside this frozen input bundle. Preserve failed or incomplete responses. Do not edit guidance, tests, runtime, repository, ledger or frozen inputs. Return the complete requested response/draft artifact and concise execution limitations. Do not judge whether a case passes.
