"""Read the source scene's stored unit settings without activating its scene."""
import argparse
import json
from pathlib import Path
import sys
import bpy

p = argparse.ArgumentParser()
p.add_argument('--source', required=True)
p.add_argument('--out', required=True)
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
with bpy.data.libraries.load(args.source, link=True) as (available, selected):
    selected.scenes = available.scenes[:1]
scene = selected.scenes[0]
units = scene.unit_settings
result = {'scene': scene.name, 'system': units.system, 'scaleLength': units.scale_length,
          'lengthUnit': units.length_unit, 'sourceSceneActivated': False, 'templateInstalled': False}
Path(args.out).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
