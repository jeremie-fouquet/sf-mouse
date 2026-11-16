include { discoverReverse } from './discovery.nf'

def topupAcquisition(image, String directionDefault, readoutDefault, String subject, String label, logger) {
    def name = image.fileName.toString().replaceFirst(/\.nii\.gz$/, '')
    def sidecar = image.resolveSibling("${name}.json")
    def direction
    def readout
    if (java.nio.file.Files.exists(sidecar)) {
        def metadata
        try {
            metadata = new groovy.json.JsonSlurper().parseText(sidecar.text)
        } catch (IOException | groovy.json.JsonException | IllegalArgumentException e) {
            throw new IllegalArgumentException("${subject}: cannot read ${label} sidecar ${sidecar}: ${e.message}", e)
        }
        if (!(metadata instanceof Map) || !metadata.containsKey('PhaseEncodingDirection') || !metadata.containsKey('TotalReadoutTime')) {
            throw new IllegalArgumentException("${subject}: ${sidecar} must contain PhaseEncodingDirection and TotalReadoutTime")
        }
        direction = metadata.PhaseEncodingDirection
        readout = metadata.TotalReadoutTime
        if (!(readout instanceof Number)) {
            throw new IllegalArgumentException("${subject}: TotalReadoutTime in ${sidecar} must be a number in seconds")
        }
    } else {
        direction = directionDefault
        readout = readoutDefault
        if (direction == null || readout == null) {
            throw new IllegalArgumentException("${subject}: missing ${label} sidecar ${sidecar} and acquisition defaults")
        }
        logger.warn("${subject}: using configured ${label} acquisition defaults; no sidecar at ${sidecar}")
    }
    if (!(direction instanceof String) || !(direction in ['i', 'i-', 'j', 'j-', 'k', 'k-'])) {
        throw new IllegalArgumentException("${subject}: invalid ${label} PhaseEncodingDirection '${direction}'")
    }
    double seconds
    try {
        seconds = Double.parseDouble(readout.toString())
    } catch (NumberFormatException e) {
        throw new IllegalArgumentException("${subject}: invalid ${label} TotalReadoutTime '${readout}'", e)
    }
    if (!Double.isFinite(seconds) || seconds <= 0 || seconds < 0.00005) {
        throw new IllegalArgumentException("${subject}: ${label} TotalReadoutTime must be finite and at least 0.00005 seconds")
    }
    [direction: direction, readout: seconds]
}

def prepareTopupInputs(Map meta, dwi, settings, logger) {
    def (reverse, reverseBval, reverseBvec) = discoverReverse(meta, dwi)
    def forward = topupAcquisition(dwi, settings.topup_forward_phase_encoding, settings.topup_forward_readout, meta.id, 'forward', logger)
    def backward = topupAcquisition(reverse, settings.topup_reverse_phase_encoding, settings.topup_reverse_readout, meta.id, 'reverse', logger)
    if (!(forward.direction in ['i', 'j', 'k'])) {
        throw new IllegalArgumentException("${meta.id}: nf-neuro topup requires a positive forward PhaseEncodingDirection (i, j or k), got ${forward.direction}")
    }
    if (backward.direction != "${forward.direction}-") {
        throw new IllegalArgumentException("${meta.id}: reverse PhaseEncodingDirection must be opposite to the forward direction")
    }
    if (forward.readout != backward.readout) {
        throw new IllegalArgumentException("${meta.id}: nf-neuro topup requires equal forward and reverse TotalReadoutTime")
    }
    if (Math.abs(forward.readout * 10000 - Math.rint(forward.readout * 10000)) > 1e-8) {
        logger.warn("${meta.id}: scilpy writes TotalReadoutTime to four decimal places; ${forward.readout} seconds will be rounded")
    }
    def axes = [i: 'x', j: 'y', k: 'z']
    [meta, reverse, reverseBval, reverseBvec, axes[forward.direction], forward.readout]
}
