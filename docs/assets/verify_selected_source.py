"""Verify distributable source snapshot without the candidate checkout or network."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[2]
snapshot=root/'assets/source/artiSynth'
manifest=json.loads((snapshot/'manifest.json').read_text())
assert manifest['upstream_commit']=='e37be3f1b4831f347c055cbf7124b6bd57414f98'
total=0
for record in manifest['files']:
 p=(snapshot/record['path']).resolve()
 assert p.is_relative_to(snapshot.resolve()),f'Escaping path: {record["path"]}'
 data=p.read_bytes()
 assert len(data)==record['bytes'],f'Length mismatch: {record["path"]}'
 assert hashlib.sha256(data).hexdigest()==record['sha256'],f'SHA256 mismatch: {record["path"]}'
 total+=len(data)
assert total==manifest['total_source_bytes']
assert not list(snapshot.rglob('.git')),'Nested Git metadata is not distributable source'
print(f'PASS: {len(manifest["files"])} unchanged source files, {total} bytes; no nested Git or network/candidate dependency.')
