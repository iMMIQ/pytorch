"""Record the source, build profile and immutable wheel identities."""
import hashlib
import json
from pathlib import Path
import sys

out = Path(sys.argv[1])
manifest = {
    "schema": 1,
    "upstream": "pytorch/pytorch",
    "upstream_commit": "70d99e998b4955e0049d13a98d77ae1b14db1f45",
    "fork": "https://github.com/iMMIQ/pytorch",
    "commit": (out / "source-commit.txt").read_text().strip(),
    "version": "2.11.0+orinfer1",
    "target": {"arch": "aarch64", "sm": 87, "cuda": "12.6", "python": "3.12.15"},
    "files": {},
}
for path in sorted(out.iterdir()):
    if path.is_file() and path.name != "build.json":
        manifest["files"][path.name] = {
            "sha256": hashlib.file_digest(path.open("rb"), "sha256").hexdigest(),
            "bytes": path.stat().st_size,
        }
(out / "build.json").write_text(json.dumps(manifest, indent=2) + "\n")
