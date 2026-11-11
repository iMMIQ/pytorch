# NVIDIA Jetson CUDA/cuDNN/NCCL/OpenBLAS development toolchain, fixed by content.
FROM ghcr.io/nvidia-ai-iot/vllm@sha256:2a90817f4d760094a25c546126a48aa8e8ae4fae1ae41bf72445fbc2c8bc2a7f
ENV UV_PYTHON_INSTALL_DIR=/opt/python UV_DEFAULT_INDEX=https://pypi.org/simple
ENV UV_CONSTRAINT=/dev/null UV_BUILD_CONSTRAINT=/dev/null PIP_CONSTRAINT=/dev/null
ARG PYTHON_VERSION=3.12.16
RUN python3 -m pip install --no-cache-dir --index-url https://pypi.org/simple --no-deps --target /tmp/bootstrap uv==0.13.7 \
 && cp /tmp/bootstrap/bin/uv /usr/local/bin/uv && rm -rf /tmp/bootstrap
COPY pyproject.toml uv.lock /opt/build-tools/
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_HTTP_TIMEOUT=300 UV_CONCURRENT_DOWNLOADS=4 UV_LINK_MODE=copy
ENV UV_PYTHON_INSTALL_MIRROR=https://github.com/astral-sh/python-build-standalone/releases/download
RUN /usr/local/bin/uv python install ${PYTHON_VERSION}
RUN --mount=type=cache,target=/root/.cache/uv \
    /usr/local/bin/uv sync --project /opt/build-tools --locked --no-dev --python ${PYTHON_VERSION} \
 && /usr/local/bin/uv pip check --python /opt/venv/bin/python
RUN apt-get update -o Dir::Etc::sourceparts=- \
 && apt-get install -y --no-install-recommends ccache=4.5.1-1 \
 && rm -rf /var/lib/apt/lists/*
ENV CCACHE_DIR=/ccache CCACHE_BASEDIR=/src
ENV CCACHE_COMPILERCHECK=content CCACHE_MAXSIZE=20G
ENV PATH=/opt/venv/bin:/usr/local/cuda/bin:${PATH} PYTHONPATH=""
ENV TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=0
ENV OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
WORKDIR /src
ENTRYPOINT ["/bin/bash"]
