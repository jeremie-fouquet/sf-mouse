include { PREPROC_VALIDATEREVERSE } from '../../../modules/local/preproc/validatereverse/main.nf'
include { PREPROC_TOPUP } from '../../../modules/nf-neuro/preproc/topup/main.nf'
include { PREPROC_EDDY } from '../../../modules/nf-neuro/preproc/eddy/main.nf'
include { prepareTopupInputs } from './metadata.nf'

workflow TOPUP_EDDY {
    take:
    original_dwi
    processed_dwi
    validator

    main:
    ch_reverse = original_dwi.map { meta, dwi, bval, bvec ->
        prepareTopupInputs(meta, dwi, params, log)
    }
    PREPROC_VALIDATEREVERSE(ch_reverse, validator)
    ch_topup_inputs = processed_dwi.join(PREPROC_VALIDATEREVERSE.out.validated, failOnMismatch: true, failOnDuplicate: true)
        .map { meta, dwi, bval, bvec, reverse, rev_bval, rev_bvec, direction, readout ->
            [meta + [dir: direction, readout: readout], dwi, bval, bvec, reverse, rev_bval, rev_bval ? rev_bvec : []]
        }
    config_file = params.topup_config_file ? file(params.topup_config_file, checkIfExists: true) : []
    if (config_file && !java.nio.file.Files.isRegularFile(config_file)) {
        error "topup_config_file must be a regular file: ${params.topup_config_file}"
    }
    PREPROC_TOPUP(
        ch_topup_inputs.map { meta, dwi, bval, bvec, reverse, rev_bval, rev_bvec ->
            [meta, dwi, bval, bvec, [], rev_bval ? reverse : [], rev_bval, rev_bvec, rev_bval ? [] : reverse]
        },
        [params.topup_config, config_file]
    )
    ch_eddy = ch_topup_inputs
        .map { meta, dwi, bval, bvec, reverse, rev_bval, rev_bvec -> [meta, dwi, bval, bvec] }
        .join(PREPROC_TOPUP.out.topup_corrected_b0s, failOnMismatch: true, failOnDuplicate: true)
        .join(PREPROC_TOPUP.out.topup_fieldcoef, failOnMismatch: true, failOnDuplicate: true)
        .join(PREPROC_TOPUP.out.topup_movpart, failOnMismatch: true, failOnDuplicate: true)
        .map { meta, dwi, bval, bvec, corrected_b0s, fieldcoef, movpart ->
            [meta, dwi, bval, bvec, [], [], [], corrected_b0s, fieldcoef, movpart]
        }
    PREPROC_EDDY(ch_eddy)
    ch_corrected = PREPROC_EDDY.out.dwi_corrected
        .join(PREPROC_EDDY.out.bval_corrected, failOnMismatch: true, failOnDuplicate: true)
        .join(PREPROC_EDDY.out.bvec_corrected, failOnMismatch: true, failOnDuplicate: true)
        .map { meta, dwi, bval, bvec -> [[id: meta.id], dwi, bval, bvec] }
    ch_qc = PREPROC_TOPUP.out.mqc.map { meta, qc -> [[id: meta.id], qc] }
        .mix(
            PREPROC_EDDY.out.dwi_eddy_mqc.map { meta, qc -> [[id: meta.id], qc] },
            PREPROC_EDDY.out.eddy_fd_mqc.map { meta, qc -> [[id: meta.id], qc] }
        )

    emit:
    dwi = ch_corrected
    qc = ch_qc
    reverse_b0_mean = PREPROC_TOPUP.out.rev_b0_mean.map { meta, image -> [[id: meta.id], image] }
}
