#!/usr/bin/env python3
"""Rebuild the current text handoff and hashes without including private art drafts."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sections = ['CONTRACT.json', 'docs/00_PRODUCT_AND_DECISIONS.md', 'docs/01_GAMEPLAY.md',
            'docs/02_STYLE_AND_UX.md', 'docs/07_ACCEPTANCE_AND_RECOVERY.md',
            'docs/09_TUTORIAL_AND_PLAYTEST.md', 'docs/18_ROSTER_AND_GROWTH.md',
            'docs/19_SYNERGY_AND_SERVICES.md', 'docs/20_POINTER_AND_MODES.md',
            'docs/21_NFC_TAP_TO_PLAY.md', 'WEB_IMPLEMENTATION_HANDOFF.md',
            'content/clash_balance.json', 'content/clash_tactics.json', 'content/capabilities.json']
contract = json.loads((ROOT / 'CONTRACT.json').read_text())
reference = contract['reference']
reference['sha256'] = hashlib.sha256((ROOT / reference['path']).read_bytes()).hexdigest()
(ROOT / 'CONTRACT.json').write_text(json.dumps(contract, ensure_ascii=False, indent=2) + '\n')
(ROOT / 'UNIVERSAL_PROMPT_FULL.txt').write_text(
    'PULSE IMPLEMENTATION CONTRACT — tactical-v1\n当前主线；旧规则从归档分支读取。\n\n' +
    '\n\n'.join('===== ' + name + ' =====\n' + (ROOT / name).read_text() for name in sections))
# Tracked assets remain in the manifest; untracked art and review_tables never enter it.
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
files = {ROOT / name for name in tracked if name}
for directory in ['content', 'docs', 'reference', 'tests', 'tools']:
    files.update(path for path in (ROOT / directory).rglob('*')
                 if path.suffix in {'.md', '.json', '.js', '.cjs', '.py'} and '__pycache__' not in path.parts)
files.add(ROOT / 'START_HERE.md')
entries = []
for path in sorted(files):
    if not path.is_file() or path.name == 'RELEASE_MANIFEST.json':
        continue
    data = path.read_bytes()
    entries.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
                    'sha256': hashlib.sha256(data).hexdigest()})
manifest = {'release': '2.0.0', 'balance_version': 'tactical-v1', 'status': 'local_build', 'files': entries}
(ROOT / 'RELEASE_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(f'Built current handoff and manifest: {len(entries)} files')
