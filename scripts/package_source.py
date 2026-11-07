"""Package the current project without caches, candidate checkouts or secrets."""
from pathlib import Path
import json, hashlib, zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'artifacts'; OUT.mkdir(exist_ok=True)
entries=[]
for folder in ['src','data','docs','scripts','tools','tests','public','.agents/skills','assets/source','assets/anatomy','assets/licenses','assets/calibration','artifacts/milestone-evidence','artifacts/method-evidence']:
 p=ROOT/folder
 if p.exists():
  for f in p.rglob('*'):
   if f.is_file() and not f.is_symlink() and '__pycache__' not in f.parts and not (f.suffix == '.pyc' or (f.suffix.startswith('.blend') and f.suffix != '.blend')):
    entries.append(f)
for name in ['package.json','package-lock.json','tsconfig.json','vite.config.ts','index.html','anatomy.html','README.md','.gitignore','.node-version']:
 if (ROOT/name).exists(): entries.append(ROOT/name)
manifest={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(entries))}
temporary=OUT/'makharij-source.zip.tmp'
with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(set(entries)):z.write(p,Path('makharij-3d')/p.relative_to(ROOT))
 z.writestr('makharij-3d/PACKAGE-MANIFEST.json',json.dumps(manifest,indent=2,ensure_ascii=False))
with zipfile.ZipFile(temporary) as z:
 assert z.testzip() is None, 'Corrupt source package'
 for name,record in manifest.items():
  assert hashlib.sha256(z.read('makharij-3d/'+name)).hexdigest()==record['sha256'],name
temporary.replace(OUT/'makharij-source.zip')
print(OUT/'makharij-source.zip',len(manifest),'files')
