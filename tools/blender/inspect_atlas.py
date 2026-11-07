"""Read atlas datablock names without installing its application template."""
import argparse
import json
from pathlib import Path
import re
import sys
import bpy

parser = argparse.ArgumentParser()
parser.add_argument('--source', required=True)
parser.add_argument('--out', required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
with bpy.data.libraries.load(args.source, link=False) as (available, selected):
    names = list(available.objects)
    collections = list(available.collections)
pattern = re.compile(r'tongue|lingu|gloss|palat|uvul|mandib|maxill|pharyn|laryn|epiglot|nasal|teeth|tooth|gingiv|oral|lip|mucos|digastr|genio|mylo|skin|face', re.I)
matched = sorted(name for name in names if pattern.search(name))
record = {'source': str(Path(args.source)), 'objectCount': len(names), 'objects': names, 'collections': collections,
          'candidateHeadNeckNames': matched, 'applicationScriptsExecuted': False}
Path(args.out).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'objectCount': len(names), 'candidateNameCount': len(matched), 'inventoryPath': args.out}, indent=2))
