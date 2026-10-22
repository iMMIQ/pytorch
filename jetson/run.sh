#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
mode=${1:-build}
out=${2:-$root/jetson/artifacts}
mkdir -p "$out"
out=$(realpath "$out")
image=orinfer-torch-builder:2.14.1-cu126-py312-v1
case "$mode" in
    build)
        docker build -t "$image" "$root/jetson"
        docker run --rm --runtime runc --network none --user "$(id -u):$(id -g)" \
            -e HOME=/tmp -e MAX_JOBS="${MAX_JOBS:-6}" \
            -v "$root:/src" -v "$out:/output" "$image" jetson/build.sh /output
        ;;
    vision)
        vision_src="$root/jetson/artifacts/vision-src"
        if [[ ! -d "$vision_src/.git" ]]; then
            git clone --depth 1 --branch v0.29.1 https://github.com/pytorch/vision.git "$vision_src"
        fi
        docker run --rm --runtime runc --network none --user "$(id -u):$(id -g)" \
            -e HOME=/tmp -e UV_CACHE_DIR=/tmp/uv -e MAX_JOBS="${MAX_JOBS:-6}" \
            -v "$root:/src" -v "$out:/output" "$image" \
            jetson/vision.sh /src/jetson/artifacts/vision-src /output
        ;;
    test)
        : "${JETSON_GPU_LOCK:?Set JETSON_GPU_LOCK to the shared GPU experiment lock}"
        exec 9>"$JETSON_GPU_LOCK"
        flock -n 9 || { echo 'GPU experiment lock is busy' >&2; exit 1; }
        group_args=()
        for group in $(id -G); do group_args+=(--group-add "$group"); done
        docker run --rm --runtime nvidia "${group_args[@]}" --network none --user "$(id -u):$(id -g)" \
            -e HOME=/tmp -e UV_CACHE_DIR=/tmp/uv \
            -e LD_PRELOAD=/usr/lib/aarch64-linux-gnu/nvidia/libcuda.so.1 \
            -v "$root/jetson/verify.py:/verify.py:ro" -v "$out:/wheels:ro" \
            -w /tmp "$image" -c \
            'export PYTHONPATH=$(/opt/venv/bin/python -c "import sysconfig; print(sysconfig.get_path(\"purelib\"))"); uv venv --python /opt/venv/bin/python /tmp/verify-env && uv pip install --python /tmp/verify-env/bin/python --no-deps /wheels/torch-*.whl /wheels/torchvision-*.whl && /tmp/verify-env/bin/python /verify.py' \
            > "$out/verification.json"
        ;;
    *) echo 'Usage: jetson/run.sh {build|vision|test} [output-directory]' >&2; exit 2 ;;
esac
