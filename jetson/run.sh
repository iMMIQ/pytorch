#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
mode=${1:-build}
source "$root/jetson/versions.env"
case "$mode" in
    build|vision|test|all) ;;
    *) echo 'Usage: jetson/run.sh {build|vision|test|all} [output-directory]' >&2; exit 2 ;;
esac
selected_versions=()
for version in "${python_versions[@]}"; do
    requested=${JETSON_PYTHON_VERSION:-${version%.*}}
    if [[ "$requested" == "$version" || "$requested" == "${version%.*}" ]]; then
        selected_versions+=("$version")
    fi
done
if [[ ${#selected_versions[@]} == 0 ]]; then
    echo "Unsupported Python version: $JETSON_PYTHON_VERSION" >&2; exit 2
fi
out=${2:-$root/jetson/artifacts/$PYTORCH_BUILD_VERSION}
mkdir -p "$out"
out=$(realpath "$out")
if [[ "$mode" != test ]]; then
    cache_dir=${JETSON_CCACHE_DIR:-$root/build/jetson/ccache}
    mkdir -p "$cache_dir"
    cache_dir=$(realpath "$cache_dir")
fi
if [[ "$mode" == test || "$mode" == all ]]; then
    : "${JETSON_GPU_LOCK:?Set JETSON_GPU_LOCK to the shared GPU experiment lock}"
fi
for version in "${selected_versions[@]}"; do
    python_tag=cp${version%.*}
    python_tag=${python_tag//./}
    wheel_out="$out/$python_tag"
    mkdir -p "$wheel_out"
    image="orinfer-torch-builder:${PYTORCH_BUILD_VERSION//+/-}-cu126-py${version}-uv1"
    if [[ "$mode" == build || "$mode" == all ]]; then
        docker build --build-arg "PYTHON_VERSION=$version" -t "$image" "$root/jetson"
        docker run --rm --runtime runc --network none --user "$(id -u):$(id -g)" \
            -e HOME=/tmp -e MAX_JOBS="${MAX_JOBS:-6}" \
            -e UV_CACHE_DIR=/tmp/uv -e JETSON_PYTHON_VERSION="$version" \
            -v "$root:/src" -v "$wheel_out:/output" -v "$cache_dir:/ccache" \
            "$image" jetson/build.sh /output
    fi
    if [[ "$mode" == vision || "$mode" == all ]]; then
        vision_src="$out/vision-src-$python_tag"
        if [[ ! -d "$vision_src/.git" ]]; then
            git clone --depth 1 --branch "$TORCHVISION_TAG" https://github.com/pytorch/vision.git "$vision_src"
        fi
        docker run --rm --runtime runc --network none --user "$(id -u):$(id -g)" \
            -e HOME=/tmp -e UV_CACHE_DIR=/tmp/uv -e MAX_JOBS="${MAX_JOBS:-6}" \
            -e JETSON_PYTHON_VERSION="$version" \
            -v "$root:/src" -v "$wheel_out:/output" -v "$vision_src:/vision-src" \
            -v "$cache_dir:/ccache" "$image" \
            jetson/vision.sh /vision-src /output
    fi
    if [[ "$mode" == test || "$mode" == all ]]; then
        (
            exec 9>"$JETSON_GPU_LOCK"
            flock -n 9 || { echo 'GPU experiment lock is busy' >&2; exit 1; }
            group_args=()
            for group in $(id -G); do group_args+=(--group-add "$group"); done
            docker run --rm --runtime nvidia "${group_args[@]}" --network none --user "$(id -u):$(id -g)" \
                -e HOME=/tmp -e UV_CACHE_DIR=/tmp/uv \
                -e JETSON_PYTHON_VERSION="$version" \
                -e LD_PRELOAD=/usr/lib/aarch64-linux-gnu/nvidia/libcuda.so.1 \
                -v "$root/jetson:/checks:ro" -v "$wheel_out:/wheels" \
                -w /tmp "$image" /checks/test.sh
        )
    fi
done
