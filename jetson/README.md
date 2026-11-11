# Torch for Jetson AGX Orin

This fork maintains the native Torch build used by [orinfer](https://github.com/iMMIQ/orinfer). The profile targets Jetson AGX Orin 64GB, L4T R36.4, CUDA 12.6 and SM87. Every default build produces separate wheels for CPython 3.11, 3.12, 3.13 and 3.14. It builds all Torch native libraries and Python bindings from source. It does not repackage a prebuilt Torch wheel.

Upstream base: PyTorch v2.15.0, commit `31a77fc9c0a7c6fff15a1ff58c743f53b1a9d457`. Our package version is `2.15.0+orinfer1`. `versions.env` pins CPython 3.11.18, 3.12.16, 3.13.18 and 3.14.10. Upstream licenses and third-party notices are retained in the wheel.

## Build

```bash
cd pytorch
git submodule update --init --recursive --depth 1 --jobs 4
MAX_JOBS=6 bash jetson/run.sh build
MAX_JOBS=6 bash jetson/run.sh vision
JETSON_GPU_LOCK=/path/to/orinfer/artifacts/gpu-experiment.lock bash jetson/run.sh test
```

Build on native aarch64 with Docker and sufficient disk and RAM. Local dependency management requires uv 0.13.7 or later so all pinned Python patch releases are available; Docker pins uv 0.13.7. GPU testing also needs NVIDIA Container Runtime. The build uses the CPU and CUDA compiler; it does not acquire the GPU or change power, clock or cache settings. Tests acquire the supplied shared lock and fail immediately if it is busy. The output directory defaults to `jetson/artifacts/2.15.0+orinfer1` and can be passed as a second argument. Each interpreter gets a `cp311`, `cp312`, `cp313` or `cp314` subdirectory containing its Torch and torchvision wheels, manifest and acceptance result. `bash jetson/run.sh all` runs build, vision and test in order for each interpreter; set `JETSON_GPU_LOCK` as above. To work on one version, set `JETSON_PYTHON_VERSION=3.11` (or 3.12, 3.13, 3.14). Keep the build log alongside the output when running interactively.

`Dockerfile` pins NVIDIA's public CUDA development image by digest and uv. `versions.env` pins the interpreter patch releases; `pyproject.toml` and `uv.lock` manage the complete Python build dependency closure with hashes. The universal lock selects Python 3.11-compatible NumPy and NetworkX releases where needed. Images are prepared with `uv sync --locked --no-dev`. The NVIDIA image supplies CUDA, cuDNN, NCCL, OpenBLAS and Clang 20. `profile.env` declares the complete supported feature profile: C++11 ABI, SM87, OpenBLAS/LAPACK, CUDA/cuDNN, Gloo/NCCL, and memory-efficient attention. MPI, TensorPipe, cuSPARSELt, cuDSS, cuFile, flash attention, Kineto and the optional CPU inference accelerators are disabled. The CPU BLAS/LAPACK path remains enabled for offline mathematical references.

The build uses `uv build --wheel --no-build-isolation --offline` with the upstream PEP 517 backend. Torch uses independent Ninja caches under `build/jetson/cp311` through `build/jetson/cp314`; torchvision also uses separate source checkouts for each interpreter. Builds run sequentially to avoid sharing generated source files or oversubscribing Orin memory. Resume with the same checkout, profile and builder images to reuse Ninja objects. Keep each changed toolchain or feature profile in a separate source checkout.

Builder images pin ccache 4.5.1. All four interpreters share `build/jetson/ccache`, mounted at `/ccache`, with a 20 GB limit and compiler content checks. Set `JETSON_CCACHE_DIR` to use another persistent host directory. Torch enables its CMake C/C++/CUDA launchers; torchvision uses Torch's automatic compiler wrappers. Compiler flags, source files and headers remain part of the cache identity. The first build after enabling ccache populates it; existing Ninja objects are not imported. Future builds record `ccache-config.txt` and cumulative `ccache-stats.txt` alongside their artifacts.

`build.json` records the fork commit, upstream base, actual Python version and all output hashes, and rejects a Torch wheel with the wrong interpreter ABI. `source.patch` records tracked changes relative to the fork commit, including a pending upstream merge. Add new source files to Git before building so they are included in this record. Publish only reviewed, committed sources. Additional records pin every submodule and list system and Python dependencies. A successful build does not establish GPU acceptance: `verification.json` must contain a successful CPU triangular solve and SVD, native CUDA execution, cuBLAS, and changed-input CUDA Graph replay. Run orinfer's `make check-offline`, compiler smoke, integer-projection and frontend reference checks before adopting an artifact in its compiler image.

For local tooling, prepare the repository environment without building Torch:

```bash
UV_PROJECT_ENVIRONMENT="$PWD/.venv" uv sync --project jetson --locked --python 3.12.16
.venv/bin/spin help
```

Refresh dependencies with `uv lock --project jetson --python 3.12.16` and validate all four interpreters before adopting the updated lock. Editable Torch development uses `uv pip install --python .venv/bin/python -e . -v --no-build-isolation` with the appropriate native toolchain.

## NVIDIA recipe basis

The reference is NVIDIA Jetson maintainer's [jetson-containers PyTorch build](https://github.com/dusty-nv/jetson-containers/tree/467ca0bf6ee8c6e51c71fd113830b4b010deed84/packages/ml/pytorch). Its recipe explicitly selects OpenBLAS and target CUDA architectures, builds from source, and uses CUDA 12.6 fatbin compression and ARM prioritized linking. This profile preserves those essentials, pins the source instead of falling back to a moving branch, and separates compilation from acceptance and publication. Only the supported SM87 target is emitted. The profile explicitly disables SVE capability builds and SLEEF SVE on Orin; NEON remains available.

## Updates and releases

Advance the upstream base and local package revision together, refresh the locked build dependencies, build with a clean profile-specific checkout, then run both wheel and orinfer acceptance checks. Publish the wheel, `build.json`, dependency records, build log and acceptance result together as a versioned GitHub release. Existing release assets are immutable inputs for orinfer: pin a release URL and SHA256, rather than a moving image tag or an unverified wheel.

The manual `Jetson Torch wheel` workflow has a four-version Python matrix, with sequential jobs on a native self-hosted runner with labels `linux`, `ARM64`, `jetson-orin` and repository variable `JETSON_GPU_LOCK`. It keeps the shared compiler cache and commit-specific artifacts under `RUNNER_TOOL_CACHE`, outside the checkout so subsequent matrix jobs do not delete them. It does not publish outputs automatically.

Torchvision 0.29.2 is built from upstream commit `f12281517f1b2f6255904639b027c9436f3e5008` with our newly built Torch. Its version is `0.29.2+orinfer1`; the acceptance check runs its CUDA NMS operator. Other compiled extensions must be built against the matching Torch ABI. General aarch64 CUDA wheels are not assumed to support SM87.

## Local compiler compatibility patch

`cmake/public/cuda.cmake` selects the Clang ABI compatibility flag from NVCC's actual host compiler identity, rather than the independent C++ compiler. This profile uses Clang 20 for C++ and GCC 11 for CUDA host compilation. Passing `-fclang-abi-compat=17` to GCC fails before any CUDA kernel compiles. CMake 4.4 records the host compiler identity used by this patch; the native CUDA build exercises the corrected flags.

The CUDA warning path also filters Clang-only warning options before forwarding them to GCC through NVCC. A standalone CUDA compile reproduces GCC rejecting `-Wmove`; the resumed native operator build validates the filtered command. The C++ compiler retains its own supported warnings.
