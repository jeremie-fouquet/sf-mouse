import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ReverseInputTests(unittest.TestCase):
    def test_reverse_input_discovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            env = os.environ.copy()
            env["NXF_ANSI_LOG"] = "false"
            result = subprocess.run(
                [
                    "nextflow", "-log", str(root / "nextflow.log"),
                    "run", str(ROOT / "test/topup/reverse_inputs.nf"),
                    "-work-dir", str(root / "work"),
                    "--test_dir", str(root / "input"),
                ],
                cwd=root, env=env, capture_output=True, text=True, timeout=180,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("REVERSE_INPUT_TESTS_PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
