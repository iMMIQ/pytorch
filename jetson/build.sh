#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source jetson/profile.env
[[ $(uname -m) == aarch64 ]] || { echo 'Native aarch64 builder required' >&2; exit 1; }
python -c 'import sys; assert sys.version_info[:3] == (3, 12, 15)'
git merge-base --is-ancestor 5c4886908584029761b579af026dcfb627c84070 HEAD
git diff --exit-code --quiet
git diff --cached --exit-code --quiet
if git submodule status --recursive | grep -E '^[-+U]'; then
    echo 'Initialize the pinned submodules before building' >&2; exit 1
fi
out=${1:-jetson/artifacts}
mkdir -p "$out"
out=$(realpath "$out")
git rev-parse HEAD > "$out/source-commit.txt"
git submodule status --recursive > "$out/source-submodules.txt"
cp jetson/profile.env "$out/profile.env"
dpkg-query -W -f='${Package}\t${Version}\n' > "$out/system-packages.tsv"
uv pip freeze --python /opt/venv/bin/python > "$out/python-packages.txt"
# The PEP 517 frontend uses the pinned environment, without dependency downloads.
python -m build --wheel --no-isolation --outdir "$out"
python jetson/manifest.py "$out"
