#!/usr/bin/env python3
"""Build a reproducible Skill archive, with GPL license, without user reports."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    skill = ROOT / 'skills' / 'claude-guardian'
    release_paths = [
        "SKILL.md", "scripts/guardian.py", "scripts/interview_flow.py", "scripts/interview_cli.py",
        "scripts/network_probes.py", "scripts/transactions.py", "scripts/serve_webrtc.py", "assets/webrtc-probe.html",
        "references/intake.md", "references/contact-and-safety.md",
        "references/routes-and-platforms.md", "references/network-and-remedies.md",
        "references/accounts-and-payments.md", "references/incidents-and-integrations.md",
        "references/evidence-policy.md", "references/source-library.md", "sources/manifest.json",
    ]
    manifest = json.loads((skill / 'sources/manifest.json').read_text(encoding='utf-8'))
    for source in manifest['sources']:
        records = [(source['path'], source['distributed_sha256'])]
        records.extend((item['path'], item['sha256']) for item in source.get('companions', []))
        for relative, digest in records:
            path = Path(relative)
            if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'sources':
                parser.error('Invalid source manifest path')
            candidate = skill / path
            if candidate.is_symlink() or not candidate.is_file() or candidate.resolve().is_relative_to(skill.resolve()) is False:
                parser.error('Invalid source manifest file')
            if hashlib.sha256(candidate.read_bytes()).hexdigest() != digest:
                parser.error('Source manifest hash mismatch')
            release_paths.append(relative)
    if len(release_paths) != len(set(release_paths)):
        parser.error('Duplicate release path')
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
            info.create_system = 3  # fixed Unix ZIP metadata on every build host
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
    print(hashlib.sha256(args.output.read_bytes()).hexdigest(), args.output.name)

if __name__ == '__main__':
    main()
