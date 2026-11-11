#!/usr/bin/env bash
set -euo pipefail
source_dir=$(realpath "$1")
out=$(realpath "$2")
source /src/jetson/versions.env
[[ $(git -C "$source_dir" rev-parse HEAD) == "$TORCHVISION_COMMIT" ]]
git -C "$source_dir" diff --exit-code --quiet
rm -f "$out/verification.json" "$out/build.json"
uv venv --python /opt/venv/bin/python /tmp/vision-env
# A venv's system-site-packages refers to CPython, not a parent venv.
export PYTHONPATH=$(/opt/venv/bin/python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
uv pip install --python /tmp/vision-env/bin/python --offline --no-deps "$out"/torch-"$PYTORCH_BUILD_VERSION"-*.whl
export PATH=/tmp/vision-env/bin:$PATH
export CC=/usr/bin/gcc-11 CXX=/usr/bin/g++-11
export BUILD_VERSION=$TORCHVISION_BUILD_VERSION FORCE_CUDA=1 TORCH_CUDA_ARCH_LIST=8.7
export MAX_JOBS=${MAX_JOBS:-6}
export TORCHVISION_USE_FFMPEG=0 TORCHVISION_USE_VIDEO_CODEC=0
cd "$source_dir"
python -c 'import os, sys, torch; torch.__version__ == os.environ["PYTORCH_BUILD_VERSION"] or sys.exit(torch.__version__)'
uv build --wheel --no-build-isolation --offline --python /tmp/vision-env/bin/python --out-dir "$out"
ccache --show-stats > "$out/ccache-stats.txt"
printf '%s\n' "$TORCHVISION_COMMIT" > "$out/torchvision-source-commit.txt"
python /src/jetson/manifest.py "$out"
