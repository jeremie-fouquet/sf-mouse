import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import nibabel as nib
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "modules" / "local" / "preproc" / "validatereverse" / "validate_reverse_dwi.py"


class ReverseValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.image = self.root / "reverse.nii.gz"
        self.bval = self.root / "reverse.bval"
        self.bvec = self.root / "reverse.bvec"
        nib.save(nib.Nifti1Image(np.zeros((2, 2, 2, 3)), np.eye(4)), self.image)
        self.bval.write_text("0 1000 0\n")
        self.bvec.write_text("0 1 0\n0 0 0\n0 0 0\n")

    def run_validator(self, bval=None, bvec=None):
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(self.image), str(bval or ""), str(bvec or ""), "100",
             str(self.root / "validated.bvec")],
            capture_output=True,
            text=True,
        )

    def test_reverse_b0_without_gradients(self):
        self.assertEqual(self.run_validator().returncode, 0)
        self.assertEqual((self.root / "validated.bvec").read_text(), "")

    def test_reverse_dwi_with_gradients(self):
        self.assertEqual(self.run_validator(self.bval, self.bvec).returncode, 0)
        np.testing.assert_array_equal(
            np.loadtxt(self.root / "validated.bvec"), np.loadtxt(self.bvec).T
        )

    def test_incomplete_gradient_pair(self):
        for bval, bvec in ((self.bval, None), (None, self.bvec)):
            with self.subTest(bval=bval, bvec=bvec):
                result = self.run_validator(bval, bvec)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("b-values and b-vectors must both be provided", result.stderr)

    def test_four_volumes_keep_fsl_orientation(self):
        nib.save(nib.Nifti1Image(np.zeros((2, 2, 2, 4)), np.eye(4)), self.image)
        self.bval.write_text("0 1000 0 1000\n")
        self.bvec.write_text("0 1 0 0\n0 0 0 1\n0 0 0 0\n")
        self.assertEqual(self.run_validator(self.bval, self.bvec).returncode, 0)
        self.assertEqual((self.root / "validated.bvec").read_text(), self.bvec.read_text())

    def test_wrong_gradient_count(self):
        self.bval.write_text("0 1000\n")
        result = self.run_validator(self.bval, self.bvec)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("3 volumes require 3 b-values", result.stderr)

    def test_no_b0(self):
        self.bval.write_text("1000 1000 1000\n")
        result = self.run_validator(self.bval, self.bvec)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no b0 volume", result.stderr)

    def test_wrong_bvector_shape(self):
        self.bvec.write_text("0 1 0\n0 0 0\n")
        result = self.run_validator(self.bval, self.bvec)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("b-vector matrix", result.stderr)

    def test_invalid_image_dimensions(self):
        nib.save(nib.Nifti1Image(np.zeros((2, 2)), np.eye(4)), self.image)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected a nonempty 3D or 4D", result.stderr)


if __name__ == "__main__":
    unittest.main()
