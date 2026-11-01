"""Fetch the pinned, unmodified HRA Mouth Male research candidate.

This does not adopt the asset in the production model. Python standard library only.
"""
import argparse
import hashlib
from pathlib import Path
import tempfile
import urllib.request

COMMIT = "29888dcc5f32dae28c7a07c41171c822275360c3"
URL = (f"https://raw.githubusercontent.com/hubmapconsortium/hra-kg/{COMMIT}/"
       "digital-objects/ref-organ/mouth-male/v1.0/raw/3d-vh-m-mouth.glb")
SHA256 = "aa5bf5f40c45c4679f05d31e7708df3e89b9897c2ff95aa89dbfaf3c501578be"
SIZE = 53487620


def verify(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if path.stat().st_size != SIZE or digest.hexdigest() != SHA256:
        raise ValueError(f"Source identity mismatch: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] /
                        "work/research/nih-hra/3d-vh-m-mouth.glb")
    args = parser.parse_args()
    dest = args.output.resolve()
    if dest.exists():
        verify(dest)
        print(f"Verified existing original: {dest}\nSHA256 {SHA256}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as output:
            temporary = Path(output.name)
            with urllib.request.urlopen(URL, timeout=60) as response:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    output.write(chunk)
        verify(temporary)
        temporary.replace(dest)
        print(f"Downloaded verified original: {dest}\nSHA256 {SHA256}")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
