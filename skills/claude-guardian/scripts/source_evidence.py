"""Bounded, offline byte identity for already-read public source material.

This module does not read files, accept caller hashes, interpret instructions,
or establish independent corroboration. The host owns authorized reads and
non-identifying aliases. A content group is not a truth or provenance verdict.
"""
import hashlib
import re

MAX_INPUTS = 64
MAX_ITEM_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
_SOURCE_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
# Defense in depth for recognized token-shaped aliases, not a generic secret
# detector. Ordinary words such as 'token' and short examples stay valid.
_CREDENTIAL_ALIAS = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:gh[oprsu]_|github_pat_|sk-(?:ant-)?|xox[baprs]-)"
    r"[A-Za-z0-9_-]{12,}")


class SourceEvidenceError(ValueError):
    """Fixed error code; never includes source text, paths, or caller values."""


def group_source_bytes(sources):
    """Group a list/tuple of (opaque source ID, bytes) by computed SHA-256.

    Only exact built-in containers, IDs and immutable bytes are accepted.
    Validate the entire bounded batch before hashing; invalid input produces
    no partial result. Distinct bytes, including derivatives, remain distinct
    content groups while independent_sources always stays not_established.
    """
    if type(sources) not in (list, tuple):
        raise SourceEvidenceError('INVALID_SOURCE_BATCH')
    if len(sources) > MAX_INPUTS:
        raise SourceEvidenceError('TOO_MANY_SOURCES')
    seen = set()
    total = 0
    checked = []
    for item in sources:
        if type(item) not in (list, tuple) or len(item) != 2:
            raise SourceEvidenceError('INVALID_SOURCE_ENTRY')
        source_id, content = item
        if (type(source_id) is not str or not _SOURCE_ID.fullmatch(source_id)
                or _CREDENTIAL_ALIAS.search(source_id)):
            raise SourceEvidenceError('INVALID_SOURCE_ID')
        if source_id in seen:
            raise SourceEvidenceError('DUPLICATE_SOURCE_ID')
        if type(content) is not bytes:
            raise SourceEvidenceError('INVALID_SOURCE_BYTES')
        if not content:
            raise SourceEvidenceError('EMPTY_SOURCE_BYTES')
        if len(content) > MAX_ITEM_BYTES:
            raise SourceEvidenceError('SOURCE_TOO_LARGE')
        total += len(content)
        if total > MAX_TOTAL_BYTES:
            raise SourceEvidenceError('SOURCE_BATCH_TOO_LARGE')
        seen.add(source_id)
        checked.append((source_id, content))

    grouped = {}
    for source_id, content in sorted(checked):
        digest = hashlib.sha256(content).hexdigest()
        if digest in grouped:
            # Never conflate unequal bytes even if a digest collision occurs.
            if grouped[digest][0] != content:
                raise SourceEvidenceError('SOURCE_DIGEST_COLLISION')
            grouped[digest][1].append(source_id)
        else:
            grouped[digest] = (content, [source_id])
    return {
        'groups': [{'sha256': digest, 'source_ids': source_ids}
                   for digest, (_, source_ids) in grouped.items()],
        'independent_sources': 'not_established',
    }
