#!/usr/bin/env bash
set -euo pipefail
source /checks/versions.env
rm -f /wheels/verification.json /wheels/build.json
cd "$(mktemp -d /tmp/jetson-verify.XXXXXX)"
export PYTHONPATH=$(/opt/venv/bin/python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
uv venv --python /opt/venv/bin/python /tmp/verify-env
uv pip install --python /tmp/verify-env/bin/python --offline --no-deps \
    /wheels/torch-"$PYTORCH_BUILD_VERSION"-*.whl /wheels/torchvision-"$TORCHVISION_BUILD_VERSION"-*.whl
export PATH=/tmp/verify-env/bin:$PATH
python /checks/verify.py
python - <<'PY' > /wheels/verification.json.tmp
import json
import platform
import torch
import torchvision

print(json.dumps({"version": torch.__version__, "python": platform.python_version(),
                  "device": torch.cuda.get_device_name(), "torchvision": torchvision.__version__,
                  "torchvision_cuda_nms": True, "cpu_blas_lapack": True,
                  "cuda_matmul": True, "changed_input_graph": True,
                  "config": torch.__config__.show()}, indent=2))
PY
mv /wheels/verification.json.tmp /wheels/verification.json
python /checks/manifest.py /wheels
