"""Acceptance checks for the native Jetson wheel; run outside the source tree."""
import json
import sys
import torch
import torchvision

assert sys.version_info[:2] == (3, 12)
assert torch.__version__ == "2.14.1+orinfer1", torch.__version__
assert torch.version.cuda == "12.6", torch.version.cuda
config = torch.__config__.show()
assert "BLAS_INFO=open" in config, config
assert "LAPACK_INFO=open" in config, config
assert torch._C._GLIBCXX_USE_CXX11_ABI
assert "sm_87" in torch._C._cuda_getArchFlags()
torch.manual_seed(20261002)
a = torch.randn(19, 19, dtype=torch.float64).tril()
a.diagonal().add_(20)
b = torch.randn(19, 7, dtype=torch.float64)
x = torch.linalg.solve_triangular(a, b, upper=False)
torch.testing.assert_close(a @ x, b, atol=1e-12, rtol=1e-12)
u, s, vh = torch.linalg.svd(a)
torch.testing.assert_close((u * s) @ vh, a, atol=1e-11, rtol=1e-11)
assert torchvision.__version__ == "0.29.1+orinfer1"
assert torch.cuda.get_device_capability() == (8, 7)
# Force a real ATen CUDA kernel and cuBLAS call before capture.
x = torch.arange(17 * 33, device="cuda", dtype=torch.float32).reshape(17, 33).half()
identity = torch.eye(33, device="cuda", dtype=torch.float16)
stream = torch.cuda.Stream()
stream.wait_stream(torch.cuda.current_stream())
with torch.cuda.stream(stream):
    for _ in range(3):
        y = x @ identity
stream.synchronize()
graph = torch.cuda.CUDAGraph()
with torch.cuda.graph(graph, stream=stream):
    y = x @ identity
for value in (2, -3, 7):
    x.fill_(value)
    graph.replay()
    torch.cuda.synchronize()
    torch.testing.assert_close(y, x, rtol=0, atol=0)
boxes = torch.tensor([[0, 0, 2, 2], [0, 0, 2, 2], [5, 5, 6, 6]], device="cuda", dtype=torch.float32)
scores = torch.tensor([0.9, 0.8, 0.7], device="cuda")
assert torchvision.ops.nms(boxes, scores, 0.5).tolist() == [0, 2]
print(json.dumps({"version": torch.__version__, "device": torch.cuda.get_device_name(),
                  "torchvision": torchvision.__version__, "torchvision_cuda_nms": True,
                  "cpu_blas_lapack": True, "cuda_matmul": True,
                  "changed_input_graph": True, "config": config}, indent=2))
