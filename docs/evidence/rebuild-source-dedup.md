# T09: exact-source reconstruction evidence

Date: 2026-10-18 (UTC). Published baseline:
`584064fc9c210e684ba4a0e11b79db74f1946155`.
This review covers the current local implementation, not an unpublished historical
patch, native device acceptance, or all of M14. The acceptance ledger is not edited
by this report; integration/review owns its eventual decision.

## Unchanged original requirement

- ID: **T09**
- Scenario: **两份完全相同教程**
- Required behavior: **只算一个来源，不当交叉证据**
- Required layers: **L+C**, both required
- Authority: [D-SPEC §11](../../skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md)
  and [original tracker §8.1](../implementation-tracker.md)
- Related source interpretation: D-SPEC §2.1 explicitly gives the S07 alias the
  same SHA-256 and one evidence weight; §8.1 separates source type from claim
  status. M14 does not turn byte identity into truth, independence, current
  validity, permission, or licensing evidence.

## Before: what was and was not established

The active evidence policy already said that duplicate S07 copies add no evidence
weight. The source library already described S03's extracted text as a derivative,
not an independent source. Those are correct statements. Neither supplied a general
two-input procedure or a callable source-identity path. Existing source tests
checked inventory IDs, hashes, links and reproducible packaging; they did not
submit two identical tutorials to such a path.

An isolated temporary copy of the repository received an extra `S07-COPY` manifest
entry at a different path, holding the exact S07 bytes. The existing packager:

- returned exit 0 and created the archive
- retained both byte-identical records without an identity-group field
- contained eight reading records but only seven distinct reading-content hashes
- continued to pass all nine pre-existing source tests

This is evidence that packaging did not enforce evidence identity. It is **not** an
observed Agent double-count, nor a reason to prohibit legitimate duplicate aliases
in a distribution. The packager still permits aliases; the new evidence helper
handles their interpretation. No original tutorial bytes or source hashes changed.

## After: active workflow and exact replay (L)

Active entry: [SKILL.md → M14 evidence policy](../../skills/claude-guardian/SKILL.md)
→ [two-tutorial procedure](../../skills/claude-guardian/references/evidence-policy.md#两份教程与来源去重t09)
→ [`group_source_bytes`](../../skills/claude-guardian/scripts/source_evidence.py).
The host reads only already-authorized selected public source files, assigns fresh
opaque aliases, then passes immutable bytes to the function. No source content is
interpreted as instructions. The function has no CLI, file reader, network client,
scanner, subprocess, persistence, evidence score, or automatic independence verdict.

Run from the repository root:

```sh
python -m unittest discover -s tests -p 'test_source_evidence.py' -v
python -m unittest discover -s tests -p 'test_source*.py' -v
```

The exact original-scenario test is
`SourceEvidenceTests.test_T09_two_renamed_byte_identical_s07_tutorials_are_one_group`.
It copies the actual packaged S07 bytes into two differently named files in a
temporary directory, reads each independently, and submits both with distinct
aliases. The complete result, not a keyword or group-count-only assertion, is:

```json
{
  "groups": [
    {
      "sha256": "ba1c1f4b4a7c6f9737436c9b488bcb6d34f69c8e9687fdfcbb75b66eeb3767a3",
      "source_ids": ["input-A", "input-B"]
    }
  ],
  "independent_sources": "not_established"
}
```

Each file is 11,030 bytes. Both aliases survive in one content group. The active
procedure explicitly interprets that group as one source, forbids cross-evidence
between its aliases, and supplies this corresponding user response:

> 这两份教程内容完全相同，只算一个来源，不能互相作为交叉证据。

This response is the reviewed procedure's worked output, not a claimed transcript
from an independently sampled model. The executed evidence is the real helper
result plus its exact fixture and extracted-package invocation. Helper correctness
does not mechanically control arbitrary Agent prose outside this workflow.

Supporting cases exercise the boundaries needed to interpret the exact result:

| Executed test | Actual assertion and its limit |
|---|---|
| `test_content_not_alias_or_order_controls_identity` | Renaming/reordering does not change content membership; a third different input stays separate |
| `test_different_bytes_and_changed_line_endings_do_not_prove_independence` | Different text and LF/CRLF variants produce two byte groups while independence stays unestablished |
| `test_s03_pdf_and_derived_text_remain_two_byte_groups_not_two_independent_sources` | The real S03 PDF and its real companion have their recorded different hashes; the reviewed manifest supplies the derivative relationship, not the algorithm |
| `test_caller_hashes_paths_and_text_are_not_an_input_format` | Caller hashes, paths, mutable buffers, non-byte content and unsupported input shapes are rejected |
| `test_duplicate_ids_are_rejected_instead_of_overwriting_content` | Same alias cannot silently overwrite identical or different input |
| `test_recognized_credential_aliases_rejected_without_echo` | Synthetic GitHub/API/Slack-shaped aliases are rejected with a fixed error, never echoed; this is not arbitrary-secret detection |
| `test_ordinary_aliases_not_rejected_for_security_words_or_short_prefixes` | Ordinary token/secret words and short prefix examples remain usable |
| `test_bounds_reject_whole_batch_before_hashing` / `test_exact_boundaries_are_supported` | More than 64 inputs, an empty item, more than 2 MiB/item, or more than 16 MiB total fail before hashing; exact limits work |
| `test_empty_batch_does_not_establish_independent_sources` | No input yields no groups and no independence assertion |
| `test_digest_collision_cannot_merge_unequal_bytes` | A simulated equal digest with unequal bytes fails rather than conflating sources |
| `test_source_instructions_are_opaque_data_and_result_contains_no_content` | Instruction-shaped source bytes are hashed without file/network/DNS/subprocess access; output fields are restricted to IDs, hashes, groups and the negative independence status |
| `test_distributed_package_has_callable_helper_and_current_guidance` | The generated archive contains exact current helper/guidance bytes; the extracted helper executes from an isolated interpreter outside the checkout |

## Sentence-by-sentence content review (C)

This is a semantic review of the entire new active procedure. Automated tests do
not substitute keyword presence for this review. References below identify the
five numbered paragraphs in `references/evidence-policy.md`.

| Sentence reviewed | Review finding |
|---|---|
| 1.1: “用户提供多份教程时，先在已有读取权限内取得选定文件的实际完整字节，为每份输入分配无个人信息的任务内别名（如 `input-A`、`input-B`）。” | Establishes the actual two-file input rather than trusting filenames; scopes reads to existing authority and avoids private identifiers |
| 1.2: “文件名、标题、上传次数或调用方提供的哈希都不能证明它们是不同来源；不扫描目录、不联网下载，不读取配置、凭据或个人日志来做来源比较。” | Blocks the most direct duplicate-counting shortcuts and unauthorized acquisition; it does not suggest running S07's commands |
| 2.1: “宿主将已读取的字节传给随包 `scripts/source_evidence.py` 的 `group_source_bytes([('input-A', first_bytes), ('input-B', second_bytes)])`。” | Gives a concrete callable interface; `first_bytes` and `second_bytes` come from the preceding authorized read, not fabricated digest strings |
| 2.2: “这是纯内存标准库函数，没有 CLI、文件读取、网络或执行入口。” | Matches the inspected implementation's imports and operations; “执行入口” here means executing source instructions or external actions, not forbidding this pure function call |
| 2.3: “每批最多 64 份、每份非空且不超过 2 MiB、总计不超过 16 MiB；重复别名、缺字节、类型或大小错误整批停止，不输出部分计数。” | Supplies explicit operational limits and a complete failure exit; tests cover limits and whole-batch prevalidation |
| 2.4: “别名只允许 1–64 位 ASCII 字母、数字、下划线或连字符，以字母开头；已识别的凭据形态会被拒绝，但不能识别任意秘密，宿主仍须使用新建的无个人信息别名。” | Matches syntactic validation and recognized-token screening; correctly leaves privacy responsibility with the host rather than claiming universal detection |
| 3.1: “函数计算实际 SHA-256 并比较同摘要内容，返回 `groups` 中的 `sha256` 和 `source_ids`。” | Accurately describes actual-byte hashing plus collision protection and the narrow output schema |
| 3.2: “两份字节完全相同的教程只形成一组：保留两个输入别名与原始定位，但仅算一个来源，不当作两个来源交叉印证，不因改名或重复上传增加证据权重。” | Directly and fully implements both original T09 clauses in the host interpretation; the helper preserves aliases, while the host retains input locations privately |
| 3.3: “分组内的输入别名不是重新分配既有 S 编号。” | Keeps the original stable-source namespace intact; grouping is not renumbering source records |
| 4.1: “返回值 `independent_sources` 始终为 `not_established`。” | Literal output matches every successful function branch, including empty input and different bytes |
| 4.2: “字节不同只表示内容不同，不能据此认定作者、观察或事实依据独立；换行差异、翻译、节选、转载和格式转换都可能仍属同一来源。” | Explicitly prevents the converse error: distinct hashes do not prove independent corroboration |
| 4.3: “对 S03 PDF 与其文字辅助版，结合清单中的 `companions` 关系保留为同一来源的两种材料，不能把两个字节分组算成两个独立证据。” | Uses real manifest provenance to handle the derivative case outside byte equality, without pretending the helper can discover semantic derivation |
| 4.4: “来源去重也不核实内容真伪、当前有效性、安全性或许可。” | Preserves D-SPEC §8 and M14's separate evidence and rights decisions; no current external fact is claimed |
| 5.1: “向用户说明实际结果与边界。” | Requires reporting the actual helper result, including its limits |
| 5.2: “例如读取同一份 S07 教程的两个副本后：‘这两份教程内容完全相同，只算一个来源，不能互相作为交叉证据。’” | Supplies an exact-scenario answer which says one source and no cross-evidence; it is conditioned on having read the actual copies |
| 5.3: “无法读取完整输入或超出边界时说明去重尚未完成，不接受自报摘要替代实际字节，也不作多来源已印证的结论。” | Unreadable/oversized cases remain unknown, with no fallback that trusts caller hashes or silently closes acceptance |
| 5.4: “仅在确有不同、独立且相关的来源证据经逐项审阅后，才另行说明交叉证据；这个函数从不作该决定。” | Keeps a future independent-evidence conclusion outside the helper and dependent on actual reviewed provenance |

Context review: the unchanged preceding S07 sentence already forbids increased
weight; the new procedure generalizes rather than contradicts it. The existing
source-library paragraph keeps the S03 derivative under its original source.
The policy's source-type/claim-status paragraphs remain restrictive, and its
release paragraph still separates licensing from public-source identity. The
existing statement that one URL may support different scopes preserves IDs; it
does not imply that duplicate content is independent. No current external-source
verification or additional platform access is needed for the original L+C row.

## Verification receipt and limits

On this local change set:

- `python -m unittest discover -s tests -p 'test_source*.py' -v`: **23 passed**
  (14 new helper cases plus nine pre-existing source/inventory/package cases)
- `python -m py_compile skills/claude-guardian/scripts/source_evidence.py`: passed
- `git diff --check`: passed
- Full repository, Node, compilation and repeatable-package checks remain the
  integrating parent's aggregate responsibility; this scoped report does not
  claim to have run those full checks

Reviewed file SHA-256 values:

| File | SHA-256 |
|---|---|
| `skills/claude-guardian/scripts/source_evidence.py` | `a1754f0445012e717dddfb9ed28245d94cb760f9d421fb47b0027a90e6f0feaf` |
| `skills/claude-guardian/references/evidence-policy.md` | `8afb262a1d85050a897c6c9a89f54afbc96a653874b7308472dbeec4c3ea1838` |
| `tests/test_source_evidence.py` | `cd9804d062f0226dcd25f7efc204c2fb4d43005be828b79dbeeb6df0ded8b86d` |
| `tools/package_skill.py` | `e4db77058bfce6e9451cc893ec48b8e7cf7fd57977eb5f541d3781714813e7c2` |

Disposition: the exact original two-identical-tutorial scenario now has executable
L evidence and a full active-guidance C review, ready for independent integration
review. This does not establish independence of differing content, universal Agent
compliance, semantic duplicate detection, truth of S07, third-party permission,
or completeness of the rest of M14. No native settings, network/Claude contact,
installation, credentials, commit, or push was involved. Rollback is limited to
removing this helper/test/evidence page, its package-list entry and the new M14
procedure; original source files remain untouched.


## Package allowlist re-review (eighth batch)

The explicit package list now includes the pure rule-source importer. The source
identity helper, its original T09 tests and active evidence policy are unchanged.
Independent review reran all 23 source/inventory/package tests and checked that
this is the only packager delta; T09 retains its exact L+C boundary. The reviewed
package-file pin above is refreshed for that addition, not a new provenance or
independence claim. ENV-T40 remains pending in the original-case ledger.
