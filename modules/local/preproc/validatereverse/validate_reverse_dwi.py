#!/usr/bin/env python3
"""Validate a reverse acquisition and prepare its b-vectors for scilpy."""

import sys
from pathlib import Path

import nibabel as nib
import numpy as np


def main():
    image_path, bval_path, bvec_path, threshold, output_path = sys.argv[1:]
    if bool(bval_path) != bool(bvec_path):
        raise ValueError(f"{image_path}: b-values and b-vectors must both be provided or both be absent")
    shape = nib.load(image_path).shape
    if len(shape) not in (3, 4) or (len(shape) == 4 and shape[3] < 1):
        raise ValueError(f"{image_path}: expected a nonempty 3D or 4D image, got {shape}")
    if not bval_path:
        Path(output_path).write_text("")
        return
    volumes = shape[3] if len(shape) == 4 else 1
    bvals = np.loadtxt(bval_path, ndmin=1)
    bvecs = np.loadtxt(bvec_path, ndmin=2)
    if bvals.ndim != 1 or bvals.size != volumes or bvecs.shape != (3, volumes):
        raise ValueError(
            f"{image_path}: {volumes} volumes require {volumes} b-values and "
            f"a 3 x {volumes} b-vector matrix; got {bvals.shape} and {bvecs.shape}"
        )
    if not np.isfinite(bvals).all() or not np.isfinite(bvecs).all() or (bvals < 0).any():
        raise ValueError(f"{image_path}: gradients contain non-finite values or negative b-values")
    if not (bvals <= float(threshold)).any():
        raise ValueError(f"{image_path}: no b0 volume found at threshold {threshold}")
    # DIPY interprets a 3x3 b-vector file as one direction per row.
    if volumes == 3:
        np.savetxt(output_path, bvecs.T, fmt="%.17g")
    else:
        Path(output_path).write_bytes(Path(bvec_path).read_bytes())


if __name__ == "__main__":
    main()
