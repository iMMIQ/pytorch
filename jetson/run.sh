#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
mode=${1:-build}
out=${2:-$root/jetson/artifacts}
mkdir -p "$out"
out=$(realpath "$out")
image=orinfer-torch-builder:2.11.0-cu126-py312-v1
case "$mode" in
    build)
        docker build -t "$image" "$root/jetson"
        docker run --rm --runtime runc --network none --user "$(id -u):$(id -g)" \
            -e HOME=/tmp -e MAX_JOBS="${MAX_JOBS:-6}" \
            -v "$root:/src" -v "$out:/output" "$image" jetson/build.sh /output
        ;;
    test)
        : "${JETSON_GPU_LOCK:?Set JETSON_GPU_LOCK to the shared GPU experiment lock}"
        exec 9>"$JETSON_GPU_LOCK"
        flock -n 9 || { echo 'GPU experiment lock is busy' >&2; exit 1; }
        docker run --rm --runtime nvidia --network none --user "$(id -u):$(id -g)" \
            -e HOME=/tmp -e UV_CACHE_DIR=/tmp/uv \
            -v "$root/jetson/verify.py:/verify.py:ro" -v "$out:/wheels:ro" \
            -w /tmp "$image" -c \
            'uv venv --python /opt/venv/bin/python --system-site-packages /tmp/verify-env && uv pip install --python /tmp/verify-env/bin/python --no-deps /wheels/torch-*.whl && /tmp/verify-env/bin/python /verify.py' \
            > "$out/verification.json"
        ;;
    *) echo 'Usage: jetson/run.sh {build|test} [output-directory]' >&2; exit 2 ;;
esac
