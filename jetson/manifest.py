"""Record the source, build profile and immutable wheel identities."""
import hashlib
import json
from pathlib import Path
import sys

out = Path(sys.argv[1])
manifest = {
    "schema": 1,
    "upstream": "pytorch/pytorch",
    "upstream_commit": "5c4886908584029761b579af026dcfb627c84070",
    "fork": "https://github.com/iMMIQ/pytorch",
    "commit": (out / "source-commit.txt").read_text().strip(),
    "version": "2.14.1+orinfer1",
    "target": {"arch": "aarch64", "sm": 87, "cuda": "12.6", "python": "3.12.15"},
    "files": {},
}
vision_commit = out / "torchvision-source-commit.txt"
if vision_commit.exists():
    manifest["torchvision"] = {"upstream_commit": vision_commit.read_text().strip(),
                             "version": "0.29.1+orinfer1"}
for path in sorted(out.iterdir()):
    if path.is_file() and path.name != "build.json":
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        manifest["files"][path.name] = {
            "sha256": digest,
            "bytes": path.stat().st_size,
        }
(out / "build.json").write_text(json.dumps(manifest, indent=2) + "\n")
