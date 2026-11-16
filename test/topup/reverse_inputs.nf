include { forwardInputs; discoverReverse } from '../../subworkflows/local/topup/discovery.nf'

workflow {
    def root = file(params.test_dir)
    def subjects = ['one', 'two'].collect { sid ->
        def dir = root.resolve(sid)
        java.nio.file.Files.createDirectories(dir)
        def forward = dir.resolve('sample_dwi.nii.gz')
        def bval = dir.resolve('sample_dwi.bval')
        def bvec = dir.resolve('sample_dwi.bvec')
        def reverse = dir.resolve('sample_dwi_reverse.nii.gz')
        [forward, bval, bvec, reverse].each { java.nio.file.Files.writeString(it, '') }
        [sid, forward, bval, bvec, reverse]
    }
    def fail = { text, Closure action ->
        try {
            action.call()
            throw new AssertionError("Expected failure containing ${text}")
        } catch (Exception e) {
            assert e.toString().contains(text) || e.cause?.toString()?.contains(text): e.toString()
        }
    }

    subjects.each { sid, forward, bval, bvec, reverse ->
        assert forwardInputs(sid, [bvec, forward, bval]) == [[id: sid], forward, bval, bvec]
        assert discoverReverse([id: sid], forward) == [reverse, [], []]
    }
    def (sid, forward, bval, bvec, reverse) = subjects[0]
    fail.call('exactly one', { forwardInputs(sid, [forward, bval]) })
    fail.call('exactly one', { forwardInputs(sid, [forward, forward, bval, bvec]) })
    def otherBval = forward.resolveSibling('other_dwi.bval')
    fail.call('same prefix', { forwardInputs(sid, [forward, otherBval, bvec]) })

    def revBval = forward.resolveSibling('sample_dwi_reverse.bval')
    def revBvec = forward.resolveSibling('sample_dwi_reverse.bvec')
    java.nio.file.Files.writeString(revBval, '')
    fail.call('both be present', { discoverReverse([id: sid], forward) })
    java.nio.file.Files.writeString(revBvec, '')
    assert discoverReverse([id: sid], forward) == [reverse, revBval, revBvec]
    java.nio.file.Files.delete(revBval)
    fail.call('both be present', { discoverReverse([id: sid], forward) })
    java.nio.file.Files.delete(reverse)
    fail.call('missing reverse image', { discoverReverse([id: sid], forward) })
    println 'REVERSE_INPUT_TESTS_PASSED'
}
