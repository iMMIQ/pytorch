# Torch for Jetson AGX Orin

This fork maintains the native Torch build used by [orinfer](https://github.com/iMMIQ/orinfer). The first profile targets Jetson AGX Orin 64GB, L4T R36.4, CUDA 12.6, SM87 and CPython 3.12.15. It builds all Torch native libraries and Python bindings from source. It does not repackage a prebuilt Torch wheel.

Upstream base: PyTorch v2.14.1, commit `5c4886908584029761b579af026dcfb627c84070`. Our package version is `2.14.1+orinfer1`. Upstream licenses and third-party notices are retained in the wheel.

## Build

```bash
git clone --branch jetson-r36.4-cu126-py312-v2.14 https://github.com/iMMIQ/pytorch.git pytorch-jetson
cd pytorch-jetson
git submodule update --init --recursive --depth 1 --jobs 4
MAX_JOBS=6 bash jetson/run.sh build
MAX_JOBS=6 bash jetson/run.sh vision
JETSON_GPU_LOCK=/path/to/orinfer/artifacts/gpu-experiment.lock bash jetson/run.sh test
```

Build on native aarch64 with Docker and sufficient disk and RAM. GPU testing also needs NVIDIA Container Runtime. The build uses the CPU and CUDA compiler; it does not acquire the GPU or change power, clock or cache settings. Tests acquire the supplied shared lock and fail immediately if it is busy. The output directory defaults to `jetson/artifacts` and can be passed as a second argument to either command. Keep the build log alongside the output when running interactively.

`Dockerfile` pins NVIDIA's public CUDA development image by digest, CPython, uv, and the complete Python build dependency closure with hashes. The NVIDIA image supplies CUDA, cuDNN, NCCL, OpenBLAS and Clang 20. `profile.env` declares the complete supported feature profile: C++11 ABI, SM87, OpenBLAS/LAPACK, CUDA/cuDNN, Gloo/NCCL, and memory-efficient attention. MPI, TensorPipe, cuSPARSELt, cuDSS, cuFile, flash attention, Kineto and the optional CPU inference accelerators are disabled. The CPU BLAS/LAPACK path remains enabled for offline mathematical references.

The build uses the upstream PEP 517 backend without build isolation or network access. Resume with the same checkout, profile and builder image to reuse Ninja objects. Keep each changed toolchain or feature profile in a separate source checkout to avoid mixing cached objects.

`build.json` records the fork commit, upstream base, profile and all output hashes. Additional records pin every submodule and list system and Python dependencies. A successful build does not establish GPU acceptance: `verification.json` must contain a successful CPU triangular solve and SVD, native CUDA execution, cuBLAS, and changed-input CUDA Graph replay. Run orinfer's `make check-offline`, compiler smoke, integer-projection and frontend reference checks before adopting an artifact in its compiler image.

## NVIDIA recipe basis

The reference is NVIDIA Jetson maintainer's [jetson-containers PyTorch build](https://github.com/dusty-nv/jetson-containers/tree/467ca0bf6ee8c6e51c71fd113830b4b010deed84/packages/ml/pytorch). Its recipe explicitly selects OpenBLAS and target CUDA architectures, builds from source, and uses CUDA 12.6 fatbin compression and ARM prioritized linking. This profile preserves those essentials, pins the source instead of falling back to a moving branch, and separates compilation from acceptance and publication. Only the supported SM87 target is emitted. The profile explicitly disables SVE capability builds and SLEEF SVE on Orin; NEON remains available.

## Updates and releases

Advance the upstream base and local package revision together, refresh the locked build dependencies, build with a clean profile-specific checkout, then run both wheel and orinfer acceptance checks. Publish the wheel, `build.json`, dependency records, build log and acceptance result together as a versioned GitHub release. Existing release assets are immutable inputs for orinfer: pin a release URL and SHA256, rather than a moving image tag or an unverified wheel.

The manual `Jetson Torch wheel` workflow uses a native self-hosted runner with labels `linux`, `ARM64`, `jetson-orin` and repository variable `JETSON_GPU_LOCK`. It retains outputs on the runner and does not publish them automatically.

Torchvision 0.29.1 is built from upstream commit `1f1a920d685d46dfbe187934b785b7ecb7a182f2` with our newly built Torch. Its version is `0.29.1+orinfer1`; the acceptance check runs its CUDA NMS operator. Other compiled extensions must be built against the matching Torch ABI. General aarch64 CUDA wheels are not assumed to support SM87.

## Local compiler compatibility patch

`cmake/public/cuda.cmake` selects the Clang ABI compatibility flag from NVCC's actual host compiler identity, rather than the independent C++ compiler. This profile uses Clang 20 for C++ and GCC 11 for CUDA host compilation. Passing `-fclang-abi-compat=17` to GCC fails before any CUDA kernel compiles. CMake 4.4 records the host compiler identity used by this patch; the native CUDA build exercises the corrected flags.
