"""Input-integrity regressions; no Blender installation or network required."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from preflight import inspect_inputs, require_model_inputs


class InputIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        (self.root / "asset.obj").write_bytes(b"v 0 0 0\n")
        self.digest = hashlib.sha256(b"v 0 0 0\n").hexdigest()
        self.lock({"asset.obj": self.digest})

    def lock(self, mapping):
        (self.root / "docs/source-lock.json").write_text(json.dumps({"files": mapping}))

    def test_exact_bytes_are_required(self):
        self.assertEqual(require_model_inputs(self.root)[0]["status"], "ok")
        (self.root / "asset.obj").write_bytes(b"v 0 0 0\n\n")
        self.assertEqual(inspect_inputs(self.root)[0]["status"], "mismatch")
        with self.assertRaisesRegex(RuntimeError, "before scene changes"):
            require_model_inputs(self.root)

    def test_missing_and_empty_downloads_are_rejected(self):
        (self.root / "asset.obj").unlink()
        self.assertEqual(inspect_inputs(self.root)[0]["status"], "missing")
        (self.root / "asset.obj").touch()
        self.assertEqual(inspect_inputs(self.root)[0]["status"], "mismatch")

    def test_path_traversal_and_symlink_escape_are_rejected(self):
        self.lock({"../asset.obj": self.digest})
        self.assertEqual(inspect_inputs(self.root)[0]["status"], "unsafe_path")
        (self.root / "outside").symlink_to(self.root.parent, target_is_directory=True)
        self.lock({"outside/asset.obj": self.digest})
        self.assertEqual(inspect_inputs(self.root)[0]["status"], "unsafe_path")

    def test_bad_lock_fails_closed(self):
        self.lock({})
        self.assertEqual(inspect_inputs(self.root)[0]["status"], "invalid_lock")
        self.lock({"asset.obj": "not-a-hash"})
        self.assertEqual(inspect_inputs(self.root)[0]["status"], "invalid_digest")
        (self.root / "docs/source-lock.json").write_text("{")
        with self.assertRaises(RuntimeError):
            require_model_inputs(self.root)
        (self.root / "docs/source-lock.json").write_text("[]")
        self.assertEqual(inspect_inputs(self.root)[0]["status"], "invalid_lock")


if __name__ == "__main__":
    unittest.main()
