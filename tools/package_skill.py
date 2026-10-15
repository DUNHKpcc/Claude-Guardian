#!/usr/bin/env python3
"""Build a reproducible Skill archive, with GPL license, without user reports."""
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    skill = ROOT / 'skills' / 'claude-guardian'
    release_paths = [
        "SKILL.md", "scripts/guardian.py",
        "references/intake.md", "references/contact-and-safety.md",
        "references/routes-and-platforms.md", "references/network-and-remedies.md",
        "references/accounts-and-payments.md", "references/incidents-and-integrations.md",
        "references/evidence-policy.md",
    ]
    candidates = [skill / relative for relative in release_paths]
    # Explicit manifest: unrelated files and user reports cannot enter releases.
    if any(not p.is_file() or p.is_symlink() for p in candidates):
        parser.error("Release manifest is incomplete or contains symlinks")
    files = [(p, Path('claude-guardian') / p.relative_to(skill)) for p in candidates
             if p.is_file() and not p.is_symlink()]
    files.append((ROOT / 'LICENSE', Path('claude-guardian/LICENSE')))
    if args.output.exists():
        parser.error('Output exists; choose a new filename to preserve previous releases')
    with zipfile.ZipFile(args.output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for source, target in sorted(files, key=lambda pair: str(pair[1])):
            info = zipfile.ZipInfo(target.as_posix(), date_time=(2026, 10, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
    print(hashlib.sha256(args.output.read_bytes()).hexdigest(), args.output.name)

if __name__ == '__main__':
    main()
