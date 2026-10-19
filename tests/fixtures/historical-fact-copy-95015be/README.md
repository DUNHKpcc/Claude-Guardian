# Historical fact-copy compatibility fixture

This sparse fixture preserves public source bytes from release
`95015be0fc70d2a1b143b43aab09e7a7ab7a7565` (Git tree
`0fbe23a5fe52dd28706f933e4c9df94c077ae688`). It is not the current runtime,
not a new acceptance decision, and not a new model-response generation.

12 changed source files are retained verbatim (562,019 bytes). Every other
required source has one explicit repository origin and must still match the
recorded whole-file hash and size. There is no fallback, hash substitution, or
symlink to current code. A repository-origin source change requires an explicit
historical-source preservation update; it must never refresh the old pin.

The loader checks the exact sparse inventory and copies only pinned source
members (64 source members in all) and four unmodified historical evidence packets into a disposable
root. The original fact-copy bridge and receipts remain byte-identical and
verify this historical root. Its before/after labels refer only to the old
one-line fact-copy transition. Historical test success does not accept the
current code, current guidance, or native behavior.

The normal acceptance and runtime suites keep using the current repository.
Current replay comparisons are labeled separately. All thirteen complete normal-scenario traces retain their original exact
expectations; current intake basics explicitly supplies the new entry fixture.
A separate current missing-entry case uses three independently specified gap
lists from the requirement. Its entire boundary trace is compared to the
pinned old boundary trace with only those explicit lists replaced. No field
is dropped, and no expectation is generated from current output.

The historical package builder describes 64 installed members; the current
67-member package is tested independently. This fixture is test-only and is
excluded from the explicit Skill release list. It contains no private logs,
authentication material, machine records, or coordination records.

The additional stored source is the original 10,004-byte
`docs/rules-extension-plan.md`, SHA-256
`bc851c13dffd4670ab6e6f471eabd38f3087a22f146dc2ad67cc8913aa12f057`.
The current document clarifies retained schema 0.3; this historical source keeps
schema 0.2 exactly. Only its explicit origin changes from repository to snapshot;
its old hash and size, all other source records, and historical receipts stay fixed.
