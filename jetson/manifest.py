"""Record the source, build profile and immutable wheel identities."""

import hashlib
import json
import os
import platform
import sys
from pathlib import Path

from packaging.utils import parse_wheel_filename


out = Path(sys.argv[1])
python_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
torch_wheels = list(out.glob("torch-*.whl"))
if len(torch_wheels) != 1:
    raise RuntimeError(f"Expected one Torch wheel in {out}, got {torch_wheels}")
_, version, _, tags = parse_wheel_filename(torch_wheels[0].name)
if str(version) != os.environ["PYTORCH_BUILD_VERSION"]:
    raise RuntimeError(f"Unexpected Torch wheel version: {version}")
if not any(
    tag.interpreter == python_tag
    and tag.abi == python_tag
    and tag.platform.endswith("_aarch64")
    for tag in tags
):
    raise RuntimeError(f"Expected {python_tag} wheel, got {tags}")
manifest = {
    "schema": 1,
    "upstream": "pytorch/pytorch",
    "upstream_commit": os.environ["JETSON_UPSTREAM_COMMIT"],
    "fork": "https://github.com/iMMIQ/pytorch",
    "commit": (out / "source-commit.txt").read_text().strip(),
    "version": os.environ["PYTORCH_BUILD_VERSION"],
    "target": {
        "arch": "aarch64",
        "sm": 87,
        "cuda": "12.6",
        "python": platform.python_version(),
    },
    "files": {},
}
vision_commit = out / "torchvision-source-commit.txt"
if vision_commit.exists():
    manifest["torchvision"] = {
        "upstream_commit": vision_commit.read_text().strip(),
        "version": os.environ["TORCHVISION_BUILD_VERSION"],
    }
for path in sorted(out.iterdir()):
    if path.is_file() and path.name != "build.json":
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        manifest["files"][path.name] = {
            "sha256": digest,
            "bytes": path.stat().st_size,
        }
(out / "build.json").write_text(json.dumps(manifest, indent=2) + "\n")
