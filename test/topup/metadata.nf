include { prepareTopupInputs } from '../../subworkflows/local/topup/metadata.nf'

workflow {
    def root = file(params.test_dir)
    def subject = root.resolve('subject')
    java.nio.file.Files.createDirectories(subject)
    def image = subject.resolve('sample_dwi.nii.gz')
    def bval = subject.resolve('sample_dwi.bval')
    def bvec = subject.resolve('sample_dwi.bvec')
    def reverse = subject.resolve('sample_dwi_reverse.nii.gz')
    [image, bval, bvec, reverse].each { java.nio.file.Files.writeString(it, '') }
    def defaults = [
        topup_forward_phase_encoding: 'j',
        topup_forward_readout: 0.01536,
        topup_reverse_phase_encoding: 'j-',
        topup_reverse_readout: 0.01536
    ]
    def meta = [id: 'subject']
    def fail = { text, Closure action ->
        try {
            action.call()
            throw new AssertionError("Expected failure containing ${text}")
        } catch (Exception e) {
            def causes = [e, e.cause, e.cause?.cause, e.cause?.cause?.cause, e.cause?.cause?.cause?.cause]
            assert causes.any { it?.toString()?.contains(text) }: causes
        }
    }

    def result = prepareTopupInputs(meta, image, defaults, log)
    assert result == [meta, reverse, [], [], 'y', 0.01536d]
    fail.call('acquisition defaults', { prepareTopupInputs(meta, image, [:], log) })

    def reverseBval = subject.resolve('sample_dwi_reverse.bval')
    def reverseBvec = subject.resolve('sample_dwi_reverse.bvec')
    java.nio.file.Files.writeString(reverseBval, '')
    fail.call('both be present', { prepareTopupInputs(meta, image, defaults, log) })
    java.nio.file.Files.writeString(reverseBvec, '')
    assert prepareTopupInputs(meta, image, defaults, log)[2..3] == [reverseBval, reverseBvec]

    def forwardJson = subject.resolve('sample_dwi.json')
    def reverseJson = subject.resolve('sample_dwi_reverse.json')
    forwardJson.text = '{"PhaseEncodingDirection":"i","TotalReadoutTime":0.02}'
    reverseJson.text = '{"PhaseEncodingDirection":"i-","TotalReadoutTime":0.02}'
    result = prepareTopupInputs(meta, image, defaults, log)
    assert result[4..5] == ['x', 0.02d]
    forwardJson.text = '{"PhaseEncodingDirection":"k","TotalReadoutTime":0.02}'
    reverseJson.text = '{"PhaseEncodingDirection":"k-","TotalReadoutTime":0.02}'
    assert prepareTopupInputs(meta, image, defaults, log)[4..5] == ['z', 0.02d]
    forwardJson.text = '{"PhaseEncodingDirection":"i","TotalReadoutTime":0.02}'
    java.nio.file.Files.delete(reverseJson)
    result = prepareTopupInputs(meta, image, defaults + [
        topup_reverse_phase_encoding: 'i-', topup_reverse_readout: 0.02
    ], log)
    assert result[4..5] == ['x', 0.02d]
    reverseJson.text = '{"PhaseEncodingDirection":"i-","TotalReadoutTime":0.03}'
    fail.call('equal forward and reverse', { prepareTopupInputs(meta, image, defaults, log) })
    reverseJson.text = '{"PhaseEncodingDirection":"j-","TotalReadoutTime":0.02}'
    fail.call('must be opposite', { prepareTopupInputs(meta, image, defaults, log) })
    forwardJson.text = '{"PhaseEncodingDirection":"i-","TotalReadoutTime":0.02}'
    fail.call('requires a positive forward', { prepareTopupInputs(meta, image, defaults, log) })
    forwardJson.text = '{"PhaseEncodingDirection":"i","TotalReadoutTime":"0.02"}'
    fail.call('must be a number', { prepareTopupInputs(meta, image, defaults, log) })
    forwardJson.text = '{"PhaseEncodingDirection":"i","TotalReadoutTime":null}'
    fail.call('must be a number', { prepareTopupInputs(meta, image, defaults, log) })
    forwardJson.text = '{"PhaseEncodingDirection":"bad","TotalReadoutTime":0.02}'
    fail.call('invalid forward PhaseEncodingDirection', { prepareTopupInputs(meta, image, defaults, log) })
    forwardJson.text = '{"PhaseEncodingDirection":"i"}'
    fail.call('must contain', { prepareTopupInputs(meta, image, defaults, log) })
    forwardJson.text = '{broken'
    fail.call('cannot read', { prepareTopupInputs(meta, image, defaults, log) })
    forwardJson.text = ''
    fail.call('cannot read', { prepareTopupInputs(meta, image, defaults, log) })
    java.nio.file.Files.delete(forwardJson)
    java.nio.file.Files.delete(reverseJson)
    fail.call('finite and at least', { prepareTopupInputs(meta, image, defaults + [topup_forward_readout: 0], log) })
    fail.call('finite and at least', { prepareTopupInputs(meta, image, defaults + [topup_forward_readout: 'NaN'], log) })
    fail.call('invalid forward TotalReadoutTime', { prepareTopupInputs(meta, image, defaults + [topup_forward_readout: 'invalid'], log) })
    java.nio.file.Files.delete(reverse)
    fail.call('missing reverse image', { prepareTopupInputs(meta, image, defaults, log) })
    println 'TOPUP_METADATA_TESTS_PASSED'
}
