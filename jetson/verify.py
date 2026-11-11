"""Acceptance checks for the native Jetson wheels; run outside the source tree."""

import os
import platform

import torch
import torchvision
from torch.testing._internal.common_device_type import instantiate_device_type_tests
from torch.testing._internal.common_utils import parametrize, run_tests, TestCase


class TestJetsonProfile(TestCase):
    def test_profile(self):
        self.assertEqual(platform.python_version(), os.environ["JETSON_PYTHON_VERSION"])
        self.assertEqual(torch.__version__, os.environ["PYTORCH_BUILD_VERSION"])
        self.assertEqual(
            torchvision.__version__, os.environ["TORCHVISION_BUILD_VERSION"]
        )
        self.assertEqual(torch.version.cuda, "12.6")
        config = torch.__config__.show()
        self.assertIn("BLAS_INFO=open", config)
        self.assertIn("LAPACK_INFO=open", config)
        self.assertTrue(torch._C._GLIBCXX_USE_CXX11_ABI)
        self.assertIn("sm_87", torch._C._cuda_getArchFlags())
        self.assertEqual(torch.cuda.get_device_capability(), (8, 7))

    def test_cpu_blas_lapack(self):
        torch.manual_seed(20261002)
        a = torch.randn(19, 19, dtype=torch.float64).tril()
        a.diagonal().add_(20)
        b = torch.randn(19, 7, dtype=torch.float64)
        x = torch.linalg.solve_triangular(a, b, upper=False)
        self.assertEqual(a @ x, b, atol=1e-12, rtol=1e-12)
        u, s, vh = torch.linalg.svd(a)
        self.assertEqual((u * s) @ vh, a, atol=1e-11, rtol=1e-11)


class TestJetsonCUDA(TestCase):
    @parametrize("value", [2, -3, 7])
    def test_graph_replay(self, device, value):
        x = torch.arange(17 * 33, device=device, dtype=torch.float16).reshape(17, 33)
        identity = torch.eye(33, device=device, dtype=torch.float16)
        stream = torch.cuda.Stream()
        stream.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(stream):
            for _ in range(3):
                y = x @ identity
        stream.synchronize()
        graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph, stream=stream):
            y = x @ identity
        x.fill_(value)
        graph.replay()
        torch.cuda.synchronize()
        self.assertEqual(y, x, rtol=0, atol=0)
        x.neg_()
        graph.replay()
        torch.cuda.synchronize()
        self.assertEqual(y, x, rtol=0, atol=0)

    def test_torchvision_nms(self, device):
        boxes = torch.tensor(
            [[0, 0, 2, 2], [0, 0, 2, 2], [5, 5, 6, 6]],
            device=device,
            dtype=torch.float32,
        )
        scores = torch.tensor([0.9, 0.8, 0.7], device=device)
        expected = torch.tensor([0, 2], device=device)
        self.assertEqual(torchvision.ops.nms(boxes, scores, 0.5), expected)


instantiate_device_type_tests(TestJetsonCUDA, globals(), only_for="cuda")

if __name__ == "__main__":
    run_tests()
