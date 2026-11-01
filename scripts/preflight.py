"""Fail before touching the Blender scene when a checkout is incomplete.

Uses only Python's standard library. It does not download or repair assets and
does not treat file integrity as anatomical acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def inspect_inputs(root: Path) -> list[dict]:
    root = root.resolve()
    lock = root / "docs/source-lock.json"
    try:
        files = json.loads(lock.read_text(encoding="utf-8"))["files"]
        if not isinstance(files, dict) or not files:
            raise ValueError("empty or invalid files mapping")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [{"path": "docs/source-lock.json", "status": "invalid_lock", "detail": str(exc)}]
    results = []
    for name, expected in sorted(files.items()):
        record = {"path": name, "expected_sha256": expected}
        path = root / name
        if Path(name).is_absolute() or root not in path.resolve().parents:
            record["status"] = "unsafe_path"
        elif not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            record["status"] = "invalid_digest"
        elif not path.is_file():
            record["status"] = "missing"
        else:
            digest = hashlib.sha256()
            try:
                with path.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
                record["actual_sha256"] = digest.hexdigest()
                record["status"] = "ok" if digest.hexdigest() == expected else "mismatch"
            except OSError as exc:
                record.update(status="unreadable", detail=str(exc))
        results.append(record)
    return results


def require_model_inputs(root: Path) -> list[dict]:
    results = inspect_inputs(root)
    errors = [r for r in results if r["status"] != "ok"]
    if errors:
        detail = "; ".join(f"{r['path']}: {r['status']}" for r in errors)
        raise RuntimeError("Model build blocked before scene changes. Restore the pinned source inputs: " + detail)
    return results


def command_result(args: list[str], root: Path, timeout: int = 20) -> dict:
    try:
        process = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=timeout)
        return {"command": args, "exit_code": process.returncode, "output": (process.stdout + process.stderr)[-4000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": args, "exit_code": None, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only environment and model-input preflight")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, help="Optional JSON report; no report is written by default")
    parser.add_argument("--network", action="store_true", help="Probe the two public source/package hosts through the inherited proxy")
    args = parser.parse_args()
    root = args.root.resolve()
    inputs = inspect_inputs(root)
    report = {
        "schema": 1,
        "scope": "environment and pinned input integrity only; no anatomical or motion validation",
        "model_inputs_complete": all(r["status"] == "ok" for r in inputs),
        "inputs": inputs,
        "runtime": {"python": platform.python_version(), "platform": platform.platform(),
                    "tools": {name: shutil.which(name) for name in ("blender", "node", "npm", "git", "ffmpeg")}},
        "git": command_result(["git", "status", "--short", "--branch"], root),
        "web_dependencies_present": (root / "node_modules/vite/bin/vite.js").is_file() and (root / "node_modules/three/package.json").is_file(),
        "network": "not_requested",
    }
    if args.network:
        report["network"] = [command_result(["curl", "--head", "--silent", "--show-error", "--connect-timeout", "5", "--max-time", "10", url], root)
                             for url in ("https://github.com", "https://registry.npmjs.org/vite")]
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if report["model_inputs_complete"] else 2


if __name__ == "__main__":
    sys.exit(main())
