"""Package a clean committed checkout, excluding nested delivery archives.

The manifest records SHA-256 for every included file. This is a development
package, not evidence of anatomical acceptance. No credentials or caches are
discovered or added: only Git-tracked files and the optional Vite dist are used.
"""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--include-browser", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    def git(*words):
        return subprocess.check_output(["git", *words], cwd=root)
    if git("status", "--porcelain", "--untracked-files=no").strip():
        raise SystemExit("Commit tracked changes before packaging a recoverable snapshot.")
    commit = git("rev-parse", "HEAD").decode().strip()
    paths = [Path(p.decode()) for p in git("ls-files", "-z").split(b"\0") if p]
    excluded = [str(p) for p in paths if p.parts[0] == "delivery" and p.suffix == ".zip"]
    entries = [(root / p, str(p)) for p in paths if str(p) not in excluded]
    if args.include_browser:
        if not (root / "dist/index.html").is_file():
            raise SystemExit("Run npm run build before including the browser build.")
        entries += [(p, "browser/" + str(p.relative_to(root / "dist")))
                    for p in sorted((root / "dist").rglob("*")) if p.is_file()]
    manifest = {
        "kind": "development recovery milestone; anatomical gate not passed",
        "source_commit": commit,
        "excluded_nested_archives": excluded,
        "browser_build_included": args.include_browser,
        "files": {},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, name in entries:
            if path.is_symlink() or not path.is_file():
                raise SystemExit("Missing or unsupported tracked source: " + str(path))
            data = path.read_bytes()
            manifest["files"][name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            archive.writestr("makharij/" + name, data)
        archive.writestr("makharij/package-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    with zipfile.ZipFile(args.output) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit("ZIP integrity failure: " + bad)
    print(json.dumps({"archive": str(args.output), "source_commit": commit,
                      "files": len(entries), "bytes": args.output.stat().st_size,
                      "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
