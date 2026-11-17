![alt text](assets/sf-mouse-light-logo.png "sf-mouse")

# sf-mouse

sf-mouse pipeline is developed by the Neurofunctional Imaging Group (GIN-IMN) and Sherbrooke Connectivity Imaging Lab (SCIL) in order to process diffusion MRI dataset from the raw data to the tractography.

Using on diffusion data sf-mouse is a nextflow pipeline based on [nf-neuro](https://github.com/scilus/nf-neuro).

It incorporates essential steps: denoising, corrections of some artefacts, registration to a template (Allen Mouse Brain Atlas), the DTI and QBall reconstructions, extraction of some metrics, until constructing a whole brain tractogram of the mouse brain and extracting some bundles. It is capable of adapting the resolution of the atlas according to the native data, for better anatomical alignment.

## Optional topup and eddy correction

The existing single-direction eddy correction remains the default. To estimate
susceptibility distortion from a reverse-phase acquisition and apply it with
eddy, enable `--run_topup`; `run_eddy` must also be enabled.

For each subject, use the existing forward DWI and gradient filenames and add
the reverse image and, optionally, acquisition sidecars beside them. There
must be exactly one forward DWI and gradient pair per subject directory:

```text
input/
  subject1/
    sample_dwi.nii.gz
    sample_dwi.bval
    sample_dwi.bvec
    sample_dwi.json               # optional if forward defaults are provided
    sample_dwi_reverse.nii.gz
    sample_dwi_reverse.json       # optional if reverse defaults are provided
    sample_dwi_reverse.bval       # optional, with the corresponding bvec
    sample_dwi_reverse.bvec       # optional, with the corresponding bval
```

The reverse basename is the forward DWI basename followed by `_reverse`.
When both reverse gradient files are present, topup extracts and averages the
reverse b0 volumes using `b0_threshold`. Without either gradient file, the
reverse image must contain **only b0 volumes**, which topup averages. This
assumption cannot be checked without gradients. The forward b0 is extracted
and averaged using the same threshold. Reverse DWI volumes are used to estimate
the field, not concatenated into the DWI passed to eddy; the corrected DWI and
rotated gradients therefore correspond to the forward acquisition.

Each BIDS-like sidecar contains the phase-encoding direction in NIfTI image
coordinates and the total readout time in seconds, for example:

```json
{"PhaseEncodingDirection": "j", "TotalReadoutTime": 0.01536}
```

The reverse sidecar for this example uses `"j-"` and the same readout time.
The installed nf-neuro/scilpy implementation supports forward `i`, `j`, or
`k`, an exactly opposite reverse direction, and a single shared readout time.
Negative forward directions and unequal readout times are rejected. Scilpy
writes readout times to four decimal places; a warning is emitted if the
specified value will be rounded. Readout times below 0.00005 seconds are
rejected. These files are BIDS-like, not full BIDS
discovery.

When a sidecar is absent, its direction and readout time must both be provided
as defaults. A present but invalid or incomplete sidecar is an error, not a
reason to use defaults. For example:

```bash
nextflow run main.nf -profile docker --input /path/to/input --run_topup \
  --topup_forward_phase_encoding j --topup_forward_readout 0.01536 \
  --topup_reverse_phase_encoding j- --topup_reverse_readout 0.01536
```

Defaults are applied independently to missing forward and reverse sidecars,
and their use is logged by subject. `--topup_config` selects a configuration
available inside the topup container (default `b02b0.cnf`). To use a custom
FSL configuration, pass `--topup_config_file /path/to/rodent.cnf` instead; it
is staged into each topup task and takes precedence over `--topup_config`.
The default preset requires even image dimensions; for an odd dimension the
container also provides `b02b0_1.cnf`.
`--topup_run_qc false` disables the new QC visualizations. Topup intermediate
images are published when `lean_output` is disabled; corrected gradient files
follow the existing preprocessed-gradient naming convention. CPU/GPU selection
uses the existing `use_gpu` setting and profiles. Use representative acquisition
metadata rather than copying the example values above.

### Experimental rodent topup candidates

The repository includes [mouse-candidate.cnf](assets/topup/mouse-candidate.cnf)
and [rat-candidate.cnf](assets/topup/rat-candidate.cnf). Select one explicitly,
for example from a local checkout:

```bash
nextflow run main.nf -profile docker --input /path/to/input --run_topup \
  --topup_config_file "$PWD/assets/topup/mouse-candidate.cnf"
```

Provide acquisition sidecars or the required phase-encoding and readout
defaults as described above. These files are **experimental starting points**,
not validated mouse or rat brain presets and not enabled by default.
They currently contain the same settings: the FSL `b02b0_1.cnf` schedule,
with warp knot spacings (`warpres`) and image smoothing (`fwhm`) divided by 10.
This follows a scaling approach described for
[rat cervical spinal cord diffusion imaging](https://doi.org/10.3791/52390),
not a validated brain protocol. All other values, including regularisation
weights, remain from FSL's
[b02b0_1.cnf](https://fsl.fmrib.ox.ac.uk/fsl/docs/diffusion/topup/users_guide/config_files.html);
they have not been independently tuned for either species. Subsampling is 1
at every level, allowing odd image dimensions but potentially increasing runtime.

The candidates assume correctly specified image voxel sizes in millimetres.
Topup approximates knot spacing using the voxel grid, so actual spacing can
differ from the requested value. Before using results for analysis, assess
correction quality and sensitivity to the configuration using representative
paired acquisitions, anatomical references and suitable quality-control metrics.

The focused tests are run with `python -m unittest discover -s test/topup -v`
in an environment with Nextflow, NumPy and nibabel. Set
`SFMOUSE_REAL_TOPUP_TEST=1` to also run a synthetic topup/eddy integration test
with Docker and the pinned `scilus/scilus:2.2.2` image. A representative
paired acquisition remains necessary to assess correction quality.
The installed eddy module carries a small local patch so fractional NaN
percentages trigger its existing warning and cleanup.

Configuration and input-discovery regression tests can be run with
`python -m unittest discover -s test -v`. The resource tests exercise local
execution and simulate SLURM submission; they do not require a SLURM cluster.


### Documentation:
--------------
sf-mouse documentation is available [here](https://scilus.github.io/sf-mouse/)
This documentation presents how to install and launch sf-mouse.

### :warning: WARNING :warning:
--------------
This pipeline is currently in development. We highly encourage everyone to give it a try and give us feedback and raise issues if any.

### In development features (non exhaustive list)

- BIDS compliant
- Meta metric QC across mouses
