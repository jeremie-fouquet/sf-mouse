import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import nibabel as nib
import numpy as np


ROOT = Path(__file__).resolve().parents[2]


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = os.environ.copy()
        self.env["NXF_ANSI_LOG"] = "false"

    def invoke_nextflow(self, script, *args):
        return subprocess.run(
            ["nextflow", "-log", str(self.root / "nextflow.log"), "run", str(ROOT / script),
             "-work-dir", str(self.root / "work"), *args],
            cwd=self.root, env=self.env, capture_output=True, text=True, timeout=900,
        )

    def run_nextflow(self, script, *args):
        result = self.invoke_nextflow(script, *args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_topup_requires_eddy(self):
        params = self.root / "params.json"
        params.write_text(json.dumps({"run_topup": True, "run_eddy": False}))
        result = subprocess.run(
            ["nextflow", "-log", str(self.root / "nextflow.log"), "run", str(ROOT / "main.nf"),
             "-params-file", str(params), "--outdir", str(self.root / "out")],
            cwd=self.root, env=self.env, capture_output=True, text=True, timeout=180,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run_topup requires run_eddy", result.stdout + result.stderr)

    def test_cli_topup_requires_eddy(self):
        result = subprocess.run(
            ["nextflow", "-log", str(self.root / "nextflow.log"), "run", str(ROOT / "main.nf"),
             "--run_topup", "--run_eddy", "false", "--outdir", str(self.root / "out")],
            cwd=self.root, env=self.env, capture_output=True, text=True, timeout=180,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run_topup requires run_eddy", result.stdout + result.stderr)

    def test_invalid_topup_switch(self):
        result = subprocess.run(
            ["nextflow", "-log", str(self.root / "nextflow.log"), "run", str(ROOT / "main.nf"),
             "--run_topup", "invalid", "--outdir", str(self.root / "out")],
            cwd=self.root, env=self.env, capture_output=True, text=True, timeout=180,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run_topup must be true or false", result.stdout + result.stderr)

    def create_stub_inputs(self):
        for subject in ("one", "two"):
            directory = self.root / "input" / subject
            directory.mkdir(parents=True)
            for name in ("sample_dwi.nii.gz", "sample_dwi.bval", "sample_dwi.bvec", "sample_dwi_reverse.nii.gz"):
                (directory / name).touch()
        for extension in ("bval", "bvec"):
            (self.root / "input" / "two" / f"sample_dwi_reverse.{extension}").touch()
        mocks = self.root / "mocks"
        mocks.mkdir()
        for name in (
            "scil_volume_math", "scil_dwi_extract_b0", "antsRegistrationSyNQuick.sh",
            "scil_dwi_prepare_topup_command", "maskfilter", "bet",
            "scil_gradients_validate_correct_eddy", "scil_dwi_concatenate", "mrconvert",
            "scil_dwi_prepare_eddy_command", "scil_header_print_info",
            "scil_viz_volume_screenshot", "convert", "uv", "antsRegistration", "flirt",
            "mrinfo", "dwidenoise",
        ):
            (mocks / name).symlink_to("/bin/true")
        self.env["PATH"] = str(mocks) + os.pathsep + self.env["PATH"]

    def test_stub_workflow_pairs_subjects(self):
        self.create_stub_inputs()
        output = self.run_nextflow(
            "test/topup/workflow.nf", "-c", str(ROOT / "test/topup/nextflow.config"),
            "-stub-run", "--input", str(self.root / "input"),
        )
        self.assertIn("CORRECTED one ", output)
        self.assertIn("CORRECTED two ", output)
        self.assertEqual(output.count("CORRECTED "), 2)

    def test_custom_config_staged_for_each_subject(self):
        self.create_stub_inputs()
        config = self.root / "custom config.cnf"
        config.write_text("# custom topup configuration\n--subsamp=1\n")
        self.run_nextflow(
            "test/topup/workflow.nf", "-c", str(ROOT / "test/topup/nextflow.config"),
            "-stub-run", "--input", str(self.root / "input"),
            "--topup_config", "b02b0_4.cnf", "--topup_config_file", str(config),
        )
        staged = list((self.root / "work").glob("*/*/sfmouse_topup_custom.cnf"))
        self.assertEqual(len(staged), 2)
        for path in staged:
            self.assertEqual(path.read_text(), config.read_text())

    def test_missing_custom_config_fails(self):
        self.create_stub_inputs()
        result = self.invoke_nextflow(
            "test/topup/workflow.nf", "-c", str(ROOT / "test/topup/nextflow.config"),
            "-stub-run", "--input", str(self.root / "input"),
            "--topup_config_file", str(self.root / "missing.cnf"),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing.cnf", result.stdout + result.stderr)

    def test_changing_custom_config_invalidates_cached_topup(self):
        self.create_stub_inputs()
        config = self.root / "custom.cnf"
        config.write_text("# first configuration\n")
        args = (
            "-c", str(ROOT / "test/topup/nextflow.config"), "-stub-run",
            "--input", str(self.root / "input"), "--topup_config_file", str(config),
        )
        self.run_nextflow("test/topup/workflow.nf", *args)
        self.assertEqual(len(list((self.root / "work").glob("*/*/sfmouse_topup_custom.cnf"))), 2)
        config.write_text("# changed configuration with a different size\n")
        self.run_nextflow("test/topup/workflow.nf", "-resume", *args)
        self.assertEqual(len(list((self.root / "work").glob("*/*/sfmouse_topup_custom.cnf"))), 4)

    def test_directory_custom_config_fails(self):
        self.create_stub_inputs()
        result = self.invoke_nextflow(
            "test/topup/workflow.nf", "-c", str(ROOT / "test/topup/nextflow.config"),
            "-stub-run", "--input", str(self.root / "input"),
            "--topup_config_file", str(self.root),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("topup_config_file must be a regular file", result.stdout + result.stderr)

    def test_missing_reverse_image_fails(self):
        self.create_stub_inputs()
        (self.root / "input" / "two" / "sample_dwi_reverse.nii.gz").unlink()
        result = self.invoke_nextflow(
            "test/topup/workflow.nf", "-c", str(ROOT / "test/topup/nextflow.config"),
            "-stub-run", "--input", str(self.root / "input"),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("two: missing reverse image", result.stdout + result.stderr)

    def test_invalid_metadata_reports_subject(self):
        self.create_stub_inputs()
        (self.root / "input" / "two" / "sample_dwi.json").write_text("{}")
        result = self.invoke_nextflow(
            "test/topup/workflow.nf", "-c", str(ROOT / "test/topup/nextflow.config"),
            "-stub-run", "--input", str(self.root / "input"),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("two:", result.stdout + result.stderr)
        self.assertIn("must contain PhaseEncodingDirection", result.stdout + result.stderr)

    def test_unmatched_processed_subject_fails(self):
        self.create_stub_inputs()
        result = self.invoke_nextflow(
            "test/topup/workflow.nf", "-c", str(ROOT / "test/topup/nextflow.config"),
            "-stub-run", "--input", str(self.root / "input"), "--drop_processed_subject", "two",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Join mismatch", result.stdout + result.stderr)
        self.assertIn("id:two", result.stdout + result.stderr)

    def run_real_synthetic(self, with_reverse_gradients, custom_config=False, candidate=None, voxel_size=1):
        directory = self.root / "input" / "subject"
        directory.mkdir(parents=True)
        grid = np.indices((16, 16, 15) if candidate else (16, 16, 16))
        radius = sum((axis - 7.5) ** 2 for axis in grid)
        b0 = (1000 * np.exp(-radius / 25)).astype(np.float32)
        dwi = np.stack([b0] + [b0 * (0.65 + 0.02 * i) for i in range(8)], axis=-1)
        reverse_b0 = np.roll(b0, 1, axis=1)
        reverse_volumes = [reverse_b0, 3 * reverse_b0]
        if with_reverse_gradients:
            reverse_volumes.append(9 * reverse_b0)
        reverse = np.stack(reverse_volumes, axis=-1)
        affine = np.diag([voxel_size, voxel_size, voxel_size, 1])
        nib.save(nib.Nifti1Image(dwi, affine), directory / "sample_dwi.nii.gz")
        nib.save(nib.Nifti1Image(reverse, affine), directory / "sample_dwi_reverse.nii.gz")
        (directory / "sample_dwi.bval").write_text("0 " + " ".join(["1000"] * 8) + "\n")
        directions = np.array([
            [0, 1, 0, 0, 1, 1, 0, 1, -1],
            [0, 0, 1, 0, 1, 0, 1, -1, 0],
            [0, 0, 0, 1, 0, 1, 1, 0, 1],
        ], dtype=float)
        directions[:, 1:] /= np.linalg.norm(directions[:, 1:], axis=0)
        np.savetxt(directory / "sample_dwi.bvec", directions)
        if with_reverse_gradients:
            (directory / "sample_dwi_reverse.bval").write_text("0 0 1000\n")
            (directory / "sample_dwi_reverse.bvec").write_text("0 0 1\n0 0 0\n0 0 0\n")
        preset_name = "b02b0.cnf" if with_reverse_gradients else "b02b0_1.cnf"
        config_args = ["--topup_config", preset_name]
        if custom_config:
            preset = subprocess.run(
                ["docker", "run", "--rm", "--entrypoint", "cat", "scilus/scilus:2.2.2",
                 "/fsl/etc/flirtsch/b02b0_1.cnf"],
                capture_output=True, text=True, check=True, timeout=60,
            ).stdout
            config = self.root / "custom config.cnf"
            config.write_text(preset.replace(
                "--miter=5,5,5,5,5,10,10,20,20", "--miter=1,1,1,1,1,1,1,1,1"
            ))
            config_args += ["--topup_config_file", str(config)]
        elif candidate:
            config = ROOT / "assets" / "topup" / candidate
            config_args += ["--topup_config_file", str(config)]
        output = self.run_nextflow(
            "test/topup/workflow.nf", "-c", str(ROOT / "test/topup/nextflow.config"),
            "-with-docker", "scilus/scilus:2.2.2", "--input", str(self.root / "input"),
            *config_args,
        )
        topup_scripts = list((self.root / "work").glob("*/*/topup.sh"))
        self.assertEqual(len(topup_scripts), 1)
        expected_config = "sfmouse_topup_custom.cnf" if custom_config or candidate else preset_name
        self.assertIn(expected_config, topup_scripts[0].read_text())
        if custom_config or candidate:
            self.assertEqual((topup_scripts[0].parent / expected_config).read_text(), config.read_text())
        corrected = next(line.split() for line in output.splitlines() if line.startswith("CORRECTED "))
        reverse_mean = next(line.split() for line in output.splitlines() if line.startswith("REVERSE_MEAN "))
        self.assertEqual(nib.load(corrected[2]).shape, dwi.shape)
        self.assertEqual(np.loadtxt(corrected[3]).size, dwi.shape[-1])
        self.assertEqual(np.loadtxt(corrected[4]).shape, (3, dwi.shape[-1]))
        np.testing.assert_allclose(nib.load(reverse_mean[2]).get_fdata(), reverse[..., :2].mean(axis=-1), atol=1e-4)

    @unittest.skipUnless(os.environ.get("SFMOUSE_REAL_TOPUP_TEST") == "1", "requires Docker imaging container")
    def test_real_synthetic_reverse_b0(self):
        self.run_real_synthetic(False)

    @unittest.skipUnless(os.environ.get("SFMOUSE_REAL_TOPUP_TEST") == "1", "requires Docker imaging container")
    def test_real_synthetic_reverse_dwi(self):
        self.run_real_synthetic(True)

    @unittest.skipUnless(os.environ.get("SFMOUSE_REAL_TOPUP_TEST") == "1", "requires Docker imaging container")
    def test_real_synthetic_custom_config(self):
        self.run_real_synthetic(False, custom_config=True)

    @unittest.skipUnless(os.environ.get("SFMOUSE_REAL_TOPUP_TEST") == "1", "requires Docker imaging container")
    def test_real_synthetic_mouse_candidate(self):
        self.run_real_synthetic(False, candidate="mouse-candidate.cnf", voxel_size=0.2)

    @unittest.skipUnless(os.environ.get("SFMOUSE_REAL_TOPUP_TEST") == "1", "requires Docker imaging container")
    def test_real_synthetic_rat_candidate(self):
        self.run_real_synthetic(False, candidate="rat-candidate.cnf", voxel_size=0.5)


if __name__ == "__main__":
    unittest.main()
