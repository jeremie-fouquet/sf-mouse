import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class EddyModuleTests(unittest.TestCase):
    def test_fractional_nan_percentage_is_detected(self):
        source = (ROOT / "modules/nf-neuro/preproc/eddy/main.nf").read_text()
        self.assertIn(
            """if awk -v percentage="\\${nan_percentage}" 'BEGIN { exit !(percentage > 0) }';""",
            source,
        )
        for percentage, expected in (("0", 1), ("0.01", 0), ("1", 0)):
            result = subprocess.run(
                ["awk", "-v", f"percentage={percentage}", "BEGIN { exit !(percentage > 0) }"],
                check=False,
            )
            self.assertEqual(result.returncode, expected)


if __name__ == "__main__":
    unittest.main()
