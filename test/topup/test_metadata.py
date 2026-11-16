import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class MetadataTests(unittest.TestCase):
    def test_subject_metadata_and_defaults(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            env = os.environ.copy()
            env["NXF_ANSI_LOG"] = "false"
            result = subprocess.run(
                [
                    "nextflow", "-log", str(root / "nextflow.log"),
                    "run", str(ROOT / "test/topup/metadata.nf"),
                    "-work-dir", str(root / "work"),
                    "--test_dir", str(root / "input"),
                ],
                cwd=root, env=env, capture_output=True, text=True, timeout=180,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("TOPUP_METADATA_TESTS_PASSED", output)
            self.assertIn("using configured forward acquisition defaults", output)
            self.assertIn("using configured reverse acquisition defaults", output)
            self.assertIn("will be rounded", output)


if __name__ == "__main__":
    unittest.main()
