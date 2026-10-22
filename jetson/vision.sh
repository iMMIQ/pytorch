#!/usr/bin/env bash
set -euo pipefail
source_dir=$(realpath "$1")
out=$(realpath "$2")
expected=1f1a920d685d46dfbe187934b785b7ecb7a182f2
[[ $(git -C "$source_dir" rev-parse HEAD) == "$expected" ]]
git -C "$source_dir" diff --exit-code --quiet
uv venv --python /opt/venv/bin/python /tmp/vision-env
# A venv's system-site-packages refers to CPython, not a parent venv.
export PYTHONPATH=$(/opt/venv/bin/python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
uv pip install --python /tmp/vision-env/bin/python --no-deps "$out"/torch-2.14.1+orinfer1-*.whl
export PATH=/tmp/vision-env/bin:$PATH
export CC=/usr/bin/gcc-11 CXX=/usr/bin/g++-11
export BUILD_VERSION=0.29.1+orinfer1 FORCE_CUDA=1 TORCH_CUDA_ARCH_LIST=8.7
export MAX_JOBS=${MAX_JOBS:-6}
export TORCHVISION_USE_FFMPEG=0 TORCHVISION_USE_VIDEO_CODEC=0
cd "$source_dir"
python -c 'import torch; assert torch.__version__ == "2.14.1+orinfer1"'
python -m build --wheel --no-isolation --outdir "$out"
printf '%s\n' "$expected" > "$out/torchvision-source-commit.txt"
python /src/jetson/manifest.py "$out"
