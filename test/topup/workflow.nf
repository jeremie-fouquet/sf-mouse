include { TOPUP_EDDY } from '../../subworkflows/local/topup/main.nf'
include { forwardInputs } from '../../subworkflows/local/topup/discovery.nf'

workflow {
    ch_dwi = Channel.fromPath("${params.input}/**/*dwi.{nii.gz,bval,bvec}")
        .map { path -> [path.parent.name, path] }
        .groupTuple()
        .map { sid, files -> forwardInputs(sid, files) }
    ch_processed = params.drop_processed_subject
        ? ch_dwi.filter { meta, dwi, bval, bvec -> meta.id != params.drop_processed_subject }
        : ch_dwi
    TOPUP_EDDY(ch_dwi, ch_processed, file("${projectDir}/../../modules/local/preproc/validatereverse/validate_reverse_dwi.py"))
    TOPUP_EDDY.out.dwi.view { meta, dwi, bval, bvec ->
        "CORRECTED ${meta.id} ${dwi} ${bval} ${bvec}"
    }
    TOPUP_EDDY.out.reverse_b0_mean.view { meta, image -> "REVERSE_MEAN ${meta.id} ${image}" }
}
