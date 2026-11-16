process PREPROC_VALIDATEREVERSE {
    tag "$meta.id"
    label 'process_single'
    container "scilus/scilus:2.2.2"

    input:
    tuple val(meta), path(reverse), path(bval), path(bvec), val(direction), val(readout)
    path validator

    output:
    tuple val(meta), path(reverse), path(bval), path('validated_reverse.bvec'), val(direction), val(readout), emit: validated

    script:
    def bvalArg = bval ? "'${bval}'" : "''"
    def bvecArg = bvec ? "'${bvec}'" : "''"
    """
    python '${validator}' '${reverse}' ${bvalArg} ${bvecArg} '${params.b0_threshold}' validated_reverse.bvec
    """

    stub:
    """
    touch validated_reverse.bvec
    """
}
