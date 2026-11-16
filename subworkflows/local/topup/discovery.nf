def forwardInputs(String subject, List files) {
    def findOne = { suffix ->
        def matches = files.findAll { it.fileName.toString().endsWith(suffix) }
        if (matches.size() != 1) {
            throw new IllegalArgumentException("${subject}: expected exactly one forward ${suffix} file, found ${matches.size()}")
        }
        matches[0]
    }
    def image = findOne.call('dwi.nii.gz')
    def bval = findOne.call('dwi.bval')
    def bvec = findOne.call('dwi.bvec')
    def prefix = image.fileName.toString().replaceFirst(/\.nii\.gz$/, '')
    if (bval.fileName.toString() != "${prefix}.bval" || bvec.fileName.toString() != "${prefix}.bvec") {
        throw new IllegalArgumentException("${subject}: forward DWI and gradient filenames must have the same prefix")
    }
    [[id: subject], image, bval, bvec]
}

def discoverReverse(Map meta, dwi) {
    def base = dwi.fileName.toString().replaceFirst(/\.nii\.gz$/, '')
    def reverse = dwi.resolveSibling("${base}_reverse.nii.gz")
    def reverseBval = dwi.resolveSibling("${base}_reverse.bval")
    def reverseBvec = dwi.resolveSibling("${base}_reverse.bvec")
    if (!java.nio.file.Files.isRegularFile(reverse)) {
        throw new IllegalArgumentException("${meta.id}: missing reverse image ${reverse}")
    }
    def hasBval = java.nio.file.Files.isRegularFile(reverseBval)
    def hasBvec = java.nio.file.Files.isRegularFile(reverseBvec)
    if (hasBval != hasBvec) {
        throw new IllegalArgumentException("${meta.id}: reverse bval and bvec must either both be present or both be absent")
    }
    [reverse, hasBval ? reverseBval : [], hasBvec ? reverseBvec : []]
}
