#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/jetson
exec 8>build/jetson/build.lock
flock 8
source jetson/profile.env
[[ $(uname -m) == aarch64 ]] || { echo 'Native aarch64 builder required' >&2; exit 1; }
python - <<'PY'
import os
import platform

expected = os.environ["JETSON_PYTHON_VERSION"]
actual = platform.python_version()
if actual != expected:
    raise RuntimeError(f"Expected Python {expected}, got {actual}")
PY
if ! git merge-base --is-ancestor "$JETSON_UPSTREAM_COMMIT" HEAD; then
    git merge-base --is-ancestor "$JETSON_UPSTREAM_COMMIT" MERGE_HEAD
fi
[[ -z $(git ls-files -u) ]] || { echo 'Resolve merge conflicts before building' >&2; exit 1; }
if git submodule status --recursive | grep -E '^[-+U]'; then
    echo 'Initialize the pinned submodules before building' >&2; exit 1
fi
out=${1:-jetson/artifacts}
mkdir -p "$out"
out=$(realpath "$out")
rm -f "$out/verification.json" "$out/build.json"
git rev-parse HEAD > "$out/source-commit.txt"
git diff --binary HEAD > "$out/source.patch"
git submodule status --recursive > "$out/source-submodules.txt"
cp jetson/profile.env jetson/versions.env jetson/pyproject.toml jetson/uv.lock "$out/"
dpkg-query -W -f='${Package}\t${Version}\n' > "$out/system-packages.tsv"
uv pip freeze --python /opt/venv/bin/python > "$out/python-packages.txt"
ccache --show-config > "$out/ccache-config.txt"
python_tag=$(python -c 'import sys; print(f"cp{sys.version_info.major}{sys.version_info.minor}")')
uv build --wheel --no-build-isolation --offline --python /opt/venv/bin/python --out-dir "$out" \
    --config-setting="build-dir=build/jetson/$python_tag" \
    --config-setting=cmake.define.USE_CCACHE=ON \
    --config-setting=cmake.define.CXX_SVE256_FOUND=OFF \
    --config-setting=cmake.define.CXX_SVE_FOUND=OFF \
    --config-setting=cmake.define.SLEEF_DISABLE_SVE=ON
ccache --show-stats > "$out/ccache-stats.txt"
python jetson/manifest.py "$out"
