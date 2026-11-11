# Owner(s): ["module: ci"]

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from torch.testing._internal.common_utils import (
    instantiate_parametrized_tests,
    parametrize,
    run_tests,
    TestCase,
)


ROOT = Path(__file__).resolve().parents[1]


@instantiate_parametrized_tests
class TestJetsonBuild(TestCase):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.out = Path(self.tempdir.name)
        self.log = self.out / "docker.jsonl"
        self.env = os.environ.copy()
        self.env.pop("JETSON_PYTHON_VERSION", None)
        self.env.update(
            PATH=f"{self.out}:{self.env['PATH']}",
            JETSON_GPU_LOCK=str(self.out / "gpu.lock"),
            JETSON_DOCKER_LOG=str(self.log),
            JETSON_CCACHE_DIR=str(self.out / "ccache"),
        )
        docker = self.out / "docker"
        docker.write_text(
            textwrap.dedent("""\
            #!/usr/bin/env python3
            import json
            import os
            import sys
            with open(os.environ["JETSON_DOCKER_LOG"], "a") as log:
                log.write(json.dumps(sys.argv[1:]) + "\\n")
            sys.exit(int(os.environ.get("JETSON_DOCKER_EXIT", "0")))
        """)
        )
        docker.chmod(0o755)
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; printf "%s\\n" "${python_versions[@]}" "$PYTORCH_BUILD_VERSION"',
                "bash",
                str(ROOT / "jetson/versions.env"),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        *self.versions, self.torch_version = result.stdout.splitlines()
        for version in self.versions:
            tag = "cp" + "".join(version.split(".")[:2])
            (self.out / f"vision-src-{tag}" / ".git").mkdir(parents=True)

    @parametrize("mode", ["build", "vision", "test", "all"])
    def test_default_matrix(self, mode):
        subprocess.run(
            ["bash", str(ROOT / "jetson/run.sh"), mode, str(self.out)],
            env=self.env,
            check=True,
        )
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        builds = [call for call in calls if call[0] == "build"]
        runs = [call for call in calls if call[0] == "run"]
        self.assertEqual(len(builds), 4 if mode in ("build", "all") else 0)
        self.assertEqual(len(runs), 12 if mode == "all" else 4)
        self.assertEqual(
            [v.rsplit(".", 1)[0] for v in self.versions],
            ["3.11", "3.12", "3.13", "3.14"],
        )
        for version in self.versions:
            tag = "cp" + "".join(version.split(".")[:2])
            selected = [
                call for call in runs if f"JETSON_PYTHON_VERSION={version}" in call
            ]
            self.assertEqual(len(selected), 3 if mode == "all" else 1)
            for call in selected:
                mounts = [call[i + 1] for i, arg in enumerate(call) if arg == "-v"]
                self.assertTrue(
                    any(mount.startswith(f"{self.out / tag}:") for mount in mounts)
                )
                if "jetson/build.sh" in call or "jetson/vision.sh" in call:
                    self.assertIn(f"{self.out / 'ccache'}:/ccache", mounts)
            if builds:
                self.assertTrue(
                    any(f"PYTHON_VERSION={version}" in call for call in builds)
                )

    @parametrize("minor", ["3.11", "3.12", "3.13", "3.14"])
    def test_select_one_version(self, minor):
        self.env["JETSON_PYTHON_VERSION"] = minor
        subprocess.run(
            ["bash", str(ROOT / "jetson/run.sh"), "build", str(self.out)],
            env=self.env,
            check=True,
        )
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(len(calls), 2)
        version = next(v for v in self.versions if v.startswith(minor + "."))
        self.assertIn(f"PYTHON_VERSION={version}", calls[0])
        self.assertIn(f"JETSON_PYTHON_VERSION={version}", calls[1])

    @parametrize("version", ["3.10", "3.15", "3.1", "3.14t"])
    def test_reject_unsupported_version(self, version):
        self.env["JETSON_PYTHON_VERSION"] = version
        result = subprocess.run(
            ["bash", str(ROOT / "jetson/run.sh"), "build", str(self.out)],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unsupported Python version", result.stderr)
        self.assertFalse(self.log.exists())

    def test_failed_build_stops_packaging(self):
        self.env["JETSON_DOCKER_EXIT"] = "3"
        result = subprocess.run(
            ["bash", str(ROOT / "jetson/run.sh"), "build", str(self.out)],
            env=self.env,
        )
        self.assertEqual(result.returncode, 3)
        self.assertEqual(len(self.log.read_text().splitlines()), 1)

    def test_codeowners_checks_staged_paths(self):
        subprocess.run(["git", "init", "-q", str(self.out)], check=True)
        (self.out / "CODEOWNERS").write_text(
            "# Review-surface hierarchy:\n# - infra: build\n"
            "# Grouped review-surface definitions:\n# [build]\n/* @iMMIQ\n"
        )
        (self.out / "removed.txt").touch()
        subprocess.run(
            ["git", "add", "CODEOWNERS", "removed.txt"], cwd=self.out, check=True
        )
        subprocess.run(
            ["git", "update-index", "--force-remove", "removed.txt"],
            cwd=self.out,
            check=True,
        )
        (self.out / "added.txt").touch()
        subprocess.run(["git", "add", "added.txt"], cwd=self.out, check=True)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/codeowners/check_taxonomy.py")],
            cwd=self.out,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Tracked paths: 2 (Git index checked)", result.stdout)

    @parametrize("invalid", [None, "abi", "platform", "version", "duplicate"])
    def test_manifest_wheel_identity(self, invalid):
        tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
        abi = "cp310" if invalid == "abi" else tag
        platform = "linux_x86_64" if invalid == "platform" else "linux_aarch64"
        version = "2.0.0" if invalid == "version" else self.torch_version
        wheel = self.out / f"torch-{version}-{tag}-{abi}-{platform}.whl"
        wheel.write_bytes(b"wheel")
        (self.out / "source-commit.txt").write_text("a" * 40 + "\n")
        if invalid == "duplicate":
            (self.out / f"torch-{version}-cp310-cp310-linux_aarch64.whl").touch()
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; "$2" "$3" "$4"',
                "bash",
                str(ROOT / "jetson/versions.env"),
                sys.executable,
                str(ROOT / "jetson/manifest.py"),
                str(self.out),
            ],
            env=self.env,
            capture_output=True,
            text=True,
        )
        if invalid is not None:
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((self.out / "build.json").exists())
        else:
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((self.out / "build.json").read_text())
            self.assertEqual(manifest["version"], self.torch_version)
            actual_python = ".".join(map(str, sys.version_info[:3]))
            self.assertEqual(manifest["target"]["python"], actual_python)
            self.assertIn(wheel.name, manifest["files"])


if __name__ == "__main__":
    run_tests()
