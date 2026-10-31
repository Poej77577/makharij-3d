"""Package the current project without caches, candidate checkouts or secrets."""
from pathlib import Path
import json, hashlib, zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'artifacts'; OUT.mkdir(exist_ok=True)
entries=[]
for folder in ['src','data','docs','scripts','public','assets/source','assets/anatomy']:
 p=ROOT/folder
 if p.exists():
  for f in p.rglob('*'):
   if f.is_file() and not f.is_symlink() and '__pycache__' not in f.parts and not (f.suffix == '.pyc' or (f.suffix.startswith('.blend') and f.suffix != '.blend')):
    entries.append(f)
for name in ['package.json','package-lock.json','tsconfig.json','index.html','README.md','.gitignore']:
 if (ROOT/name).exists(): entries.append(ROOT/name)
manifest={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(entries))}
with zipfile.ZipFile(OUT/'makharij-source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(set(entries)):z.write(p,Path('makharij-3d')/p.relative_to(ROOT))
 z.writestr('makharij-3d/PACKAGE-MANIFEST.json',json.dumps(manifest,indent=2,ensure_ascii=False))
print(OUT/'makharij-source.zip',len(manifest),'files')
