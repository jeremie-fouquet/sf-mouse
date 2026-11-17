import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ConfigurationTests(unittest.TestCase):
    def test_topup_parameter_defaults(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                ["nextflow", "-log", str(Path(temporary) / "nextflow.log"),
                 "config", "-flat", str(ROOT)],
                cwd=temporary, env={**os.environ, "NXF_ANSI_LOG": "false"},
                capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for expected in (
            "params.run_topup = false",
            "params.topup_forward_phase_encoding = null",
            "params.topup_forward_readout = null",
            "params.topup_reverse_phase_encoding = null",
            "params.topup_reverse_readout = null",
            "params.topup_config = 'b02b0.cnf'",
            "params.topup_config_file = null",
            "params.topup_run_qc = true",
        ):
            self.assertIn(expected, result.stdout)

    def test_topup_schema_group(self):
        schema = json.loads((ROOT / "nextflow_schema.json").read_text())
        run_topup = schema["$defs"]["skip_steps_options"]["properties"]["run_topup"]
        self.assertIs(run_topup["default"], False)
        self.assertIn({"$ref": "#/$defs/topup_options"}, schema["allOf"])
        properties = schema["$defs"]["topup_options"]["properties"]
        self.assertEqual(properties["topup_forward_phase_encoding"]["enum"], ["i", "j", "k"])
        self.assertEqual(properties["topup_reverse_phase_encoding"]["enum"], ["i-", "j-", "k-"])
        for direction in ("forward", "reverse"):
            self.assertEqual(properties[f"topup_{direction}_readout"]["minimum"], 0.00005)
        self.assertEqual(properties["topup_config"]["default"], "b02b0.cnf")
        self.assertTrue(properties["topup_config_file"]["exists"])
        self.assertIs(properties["topup_run_qc"]["default"], True)

    def test_candidate_configurations(self):
        schedules = []
        for species in ("mouse", "rat"):
            config = ROOT / "assets" / "topup" / f"{species}-candidate.cnf"
            options = {}
            for line in config.read_text().splitlines():
                if line.startswith("--"):
                    key, value = line.split("=", 1)
                    options[key] = value
            for key in ("--warpres", "--subsamp", "--fwhm", "--miter", "--lambda", "--estmov", "--minmet"):
                self.assertEqual(len(options[key].split(",")), 9, f"{species}: {key}")
            self.assertEqual(options["--subsamp"], "1,1,1,1,1,1,1,1,1")
            self.assertEqual(options["--warpres"], "2,1.6,1.4,1.2,1,0.6,0.4,0.4,0.4")
            self.assertEqual(options["--fwhm"], "0.8,0.6,0.4,0.3,0.3,0.2,0.1,0,0")
            schedules.append(options)
        self.assertEqual(*schedules)


if __name__ == "__main__":
    unittest.main()
