"""Run with Blender: validate failure before scene changes using a missing-input fixture.

blender -b -t 2 --python scripts/test_scene_guard.py -- --output work/scene-guard.json
No production input or model is modified.
"""
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import bpy

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
root = Path(__file__).resolve().parents[1]
sentinel = bpy.data.objects.new("PRESERVE_EXISTING_SCENE", None)
bpy.context.scene.collection.objects.link(sentinel)
before = set(bpy.data.objects)
result = {"method": "Blender background execution of the actual build script in a missing-input fixture",
          "blender_version": bpy.app.version_string}
with tempfile.TemporaryDirectory() as directory:
    fixture = Path(directory)
    (fixture / "scripts").mkdir()
    (fixture / "docs").mkdir()
    (fixture / "scripts/preflight.py").write_bytes((root / "scripts/preflight.py").read_bytes())
    build_path = fixture / "scripts/build_model.py"
    build_path.write_bytes((root / "scripts/build_model.py").read_bytes())
    (fixture / "docs/source-lock.json").write_text(json.dumps({"files": {"model/source/missing.glb": hashlib.sha256(b"fixture").hexdigest()}}))
    try:
        exec(compile(build_path.read_text(), str(build_path), "exec"), {"__name__": "__main__", "__file__": str(build_path)})
        result["blocked"] = False
    except RuntimeError as exc:
        result.update(blocked=True, error=str(exc))
    result["existing_objects_preserved"] = set(bpy.data.objects) == before
    result["output_asset_written"] = (fixture / "public/models/makharij-rest.glb").exists()
result["passed"] = result["blocked"] and result["existing_objects_preserved"] and not result["output_asset_written"]
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
if not result["passed"]:
    raise RuntimeError("Scene preservation test failed")
