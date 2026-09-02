#!/usr/bin/env python3
"""Ground vibration testing logic module: GVT data quality checks.

Contract: docs/harness-contract.md gate 3 (flight-test-operations/
flutter/ground-vibration-testing leaf). All frequencies are in Hz,
damping is dimensionless, SI units throughout.

GVT measures the structural natural frequencies, mode shapes, and
damping of the aircraft on the ground before flight; the results
anchor the flutter clearance model. The half-power bandwidth and
peak-picking checks follow common modal test practice, summary-only
per standards-map.yaml (FAR-25, CS-25 referenced, not reproduced).
"""


def half_power_damping(f1, f2, fn):
    """Modal damping ratio from the half-power bandwidth method.

    zeta = (f2 - f1) / (2 * fn), with fn the natural frequency in Hz
    and f1, f2 the half-power points (where the FRF magnitude has
    fallen to 1/sqrt(2) of its peak value) bracketing fn, both in Hz.
    Output is dimensionless. Requires 0 < f1 < fn < f2; raises
    ValueError otherwise.
    """
    if f1 <= 0 or f2 <= 0 or fn <= 0:
        raise ValueError(
            "frequencies must be positive, got f1=%r f2=%r fn=%r"
            % (f1, f2, fn)
        )
    if not (f1 < fn < f2):
        raise ValueError(
            "half-power points must bracket the natural frequency, "
            "got f1=%r fn=%r f2=%r" % (f1, fn, f2)
        )
    return (f2 - f1) / (2.0 * fn)


def peak_pick_verdict(frf_peak, threshold):
    """Peak-picking verdict: does the FRF peak qualify as a mode.

    An FRF magnitude peak at or above the threshold is accepted as a
    mode candidate; below it the peak is treated as noise. Returns
    {'peak': frf_peak, 'threshold': threshold, 'pass': bool}. Raises
    ValueError when the threshold is non-positive or the peak
    magnitude is negative.
    """
    if threshold <= 0:
        raise ValueError("threshold must be positive, got %r" % (threshold,))
    if frf_peak < 0:
        raise ValueError(
            "FRF magnitude cannot be negative, got %r" % (frf_peak,)
        )
    return {
        "peak": frf_peak,
        "threshold": threshold,
        "pass": frf_peak >= threshold,
    }


def frequency_resolution(sample_rate, n_samples):
    """FFT frequency resolution for the GVT acquisition setup.

    df = sample_rate / n_samples in Hz, with sample_rate in samples
    per second and n_samples the FFT block size in samples. Raises
    ValueError when sample_rate is non-positive or n_samples is not
    an integer of at least 2.
    """
    if sample_rate <= 0:
        raise ValueError(
            "sample_rate must be positive, got %r" % (sample_rate,)
        )
    if isinstance(n_samples, bool) or not isinstance(n_samples, int):
        raise ValueError(
            "n_samples must be an integer, got %r" % (n_samples,)
        )
    if n_samples < 2:
        raise ValueError(
            "n_samples must be at least 2, got %r" % (n_samples,)
        )
    return sample_rate / float(n_samples)


def mode_count_verdict(peaks, expected):
    """Mode count verdict: detected peaks versus pre-test expectation.

    Compares the number of detected mode candidate peaks with the
    number of modes expected from the analysis model in the test
    band. Returns {'found': len(peaks), 'expected': expected,
    'pass': bool, 'verdict': str}. Raises ValueError when expected
    is negative or any peak frequency is negative.
    """
    if expected < 0:
        raise ValueError(
            "expected mode count cannot be negative, got %r" % (expected,)
        )
    if any(p < 0 for p in peaks):
        raise ValueError(
            "peak frequencies cannot be negative, got %r" % (peaks,)
        )
    found = len(peaks)
    ok = found == expected
    verdict = "mode count matches" if ok else "mode count mismatch"
    return {"found": found, "expected": expected, "pass": ok, "verdict": verdict}


def reciprocity_check(h12, h21, tolerance=0.05):
    """Reciprocity quality check between two transfer FRFs.

    For a linear time-invariant structure the FRF H_ij equals H_ji;
    the relative difference abs(h12 - h21) / max(abs(h12), abs(h21))
    must stay within the tolerance (default 0.05) for the data to
    pass. Both zero means no response at either location and passes
    trivially. Returns {'rel_diff': value, 'tolerance': tolerance,
    'pass': bool}. Raises ValueError when tolerance is non-positive.
    """
    if tolerance <= 0:
        raise ValueError("tolerance must be positive, got %r" % (tolerance,))
    denom = max(abs(h12), abs(h21))
    if denom == 0.0:
        rel_diff = 0.0
    else:
        rel_diff = abs(h12 - h21) / denom
    return {
        "rel_diff": rel_diff,
        "tolerance": tolerance,
        "pass": rel_diff <= tolerance,
    }


def coherence_verdict(coherence, min_coherence=0.9):
    """Coherence quality check for a measured FRF.

    Coherence gamma^2 in [0, 1] reports how much of the output power
    is linearly explained by the input; the FRF passes when
    coherence >= min_coherence (default 0.9). Low coherence flags
    noise, leakage, or nonlinearity. Returns {'coherence': value,
    'min_coherence': min_coherence, 'pass': bool}. Raises ValueError
    when coherence or min_coherence falls outside [0, 1].
    """
    if coherence < 0.0 or coherence > 1.0:
        raise ValueError(
            "coherence must be in [0, 1], got %r" % (coherence,)
        )
    if min_coherence <= 0.0 or min_coherence > 1.0:
        raise ValueError(
            "min_coherence must be in (0, 1], got %r" % (min_coherence,)
        )
    return {
        "coherence": coherence,
        "min_coherence": min_coherence,
        "pass": coherence >= min_coherence,
    }
