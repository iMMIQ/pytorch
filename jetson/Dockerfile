# NVIDIA Jetson CUDA/cuDNN/NCCL/OpenBLAS development toolchain, fixed by content.
FROM ghcr.io/nvidia-ai-iot/vllm@sha256:2a90817f4d760094a25c546126a48aa8e8ae4fae1ae41bf72445fbc2c8bc2a7f
ENV UV_PYTHON_INSTALL_DIR=/opt/python UV_DEFAULT_INDEX=https://pypi.org/simple
ENV UV_CONSTRAINT=/dev/null UV_BUILD_CONSTRAINT=/dev/null PIP_CONSTRAINT=/dev/null
RUN python3 -m pip install --no-cache-dir --index-url https://pypi.org/simple --no-deps --target /tmp/bootstrap uv==0.13.4 \
 && cp /tmp/bootstrap/bin/uv /usr/local/bin/uv && rm -rf /tmp/bootstrap
COPY requirements.lock /tmp/build-requirements.lock
RUN /usr/local/bin/uv python install 3.12.15 \
 && /usr/local/bin/uv venv --clear --python 3.12.15 /opt/venv \
 && /usr/local/bin/uv pip sync --python /opt/venv/bin/python --require-hashes /tmp/build-requirements.lock \
 && /usr/local/bin/uv pip check --python /opt/venv/bin/python \
 && rm /tmp/build-requirements.lock
ENV PATH=/opt/venv/bin:/usr/local/cuda/bin:${PATH} PYTHONPATH=""
ENV OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
WORKDIR /src
ENTRYPOINT ["/bin/bash"]
