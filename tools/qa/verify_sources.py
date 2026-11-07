"""Offline verification of original asset snapshots, not anatomical approval."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
summaries = []
for directory in ['artiSynth', 'makehuman', 'vkh-upper-airway', 'z-anatomy']:
    source = ROOT / 'assets/source' / directory
    manifest = json.loads((source / 'manifest.json').read_text())
    total = 0
    for record in manifest['files']:
        path = (source / record['path']).resolve()
        if not path.is_relative_to(source.resolve()):
            raise ValueError('Source manifest path escapes its snapshot')
        blob = path.read_bytes()
        assert len(blob) == record['bytes'], path
        assert hashlib.sha256(blob).hexdigest() == record['sha256'], path
        total += len(blob)
    assert not list(source.rglob('.git')), 'Nested Git repository in distributable snapshot'
    summaries.append({'snapshot': directory, 'files': len(manifest['files']), 'bytes': total,
                      'kind': manifest.get('snapshotKind', 'unchanged original files')})
registry = json.loads((ROOT / 'assets/licenses/registry.json').read_text())
for entry in registry['entries']:
    assert (ROOT / entry['noticePath']).is_file(), entry['id']
print(json.dumps({'verified': summaries, 'licenseNoticesPresent': len(registry['entries']), 'scope': 'Source byte identity and audited notice availability only'}, indent=2))
