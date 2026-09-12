"""
Dynamic sine-sweep, random-vibration, and shock test logic.
Implements deterministic, checkable engineering rules for
ECSS-E-ST-32C section 4.6.3.9 dynamic test planning and execution.
stdlib only — no third-party dependencies.
"""

import math

_VALID_LEVELS = {"qualification", "acceptance", "proto_flight"}
_VALID_TYPES = {"sine_sweep", "random_vibration", "shock"}


def _normalize(raw, sep="_"):
    return raw.lower().replace("-", sep).replace(" ", sep)


def categorize_test_level(level_str):
    """
    Return the normalized test level string for the given input.
    Accepted inputs (case-insensitive, hyphens/spaces treated as underscores):
    qualification, acceptance, proto_flight / proto-flight.
    Raises ValueError for unrecognized inputs.
    """
    normalized = _normalize(level_str)
    if normalized not in _VALID_LEVELS:
        raise ValueError(
            f"Unrecognized test level {level_str!r}. "
            f"Expected one of: {sorted(_VALID_LEVELS)}"
        )
    return normalized


def categorize_test_type(type_str):
    """
    Return the normalized test type string for the given input.
    Accepted inputs: sine_sweep, random_vibration, shock (and hyphen/space variants).
    Raises ValueError for unrecognized inputs.
    """
    normalized = _normalize(type_str)
    if normalized not in _VALID_TYPES:
        raise ValueError(
            f"Unrecognized test type {type_str!r}. "
            f"Expected one of: {sorted(_VALID_TYPES)}"
        )
    return normalized


def compute_sweep_rate(freq_start_hz, freq_end_hz, duration_min):
    """
    Compute the sine-sweep rate in octaves per minute for a log sweep.
    freq_start_hz, freq_end_hz: sweep band endpoints (Hz), both must be > 0.
    duration_min: elapsed time for one sweep pass (minutes), must be > 0.
    Returns sweep rate in oct/min.
    """
    if freq_start_hz <= 0 or freq_end_hz <= 0:
        raise ValueError("Both frequencies must be positive (Hz)")
    if freq_start_hz == freq_end_hz:
        raise ValueError("freq_start_hz and freq_end_hz must differ")
    if duration_min <= 0:
        raise ValueError("duration_min must be positive")
    octaves = abs(math.log2(freq_end_hz / freq_start_hz))
    return octaves / duration_min


def apply_notching(input_level_g, response_limit_g, predicted_response_g):
    """
    Compute the notched input level needed to keep the structural response
    within its prescribed limit.

    If predicted_response_g <= response_limit_g the input is unchanged.
    Otherwise the input is scaled down linearly so that the predicted response
    equals the limit (assuming linear response-to-input relationship).

    Returns (notched_level_g: float, was_notched: bool).
    All arguments must be positive.
    """
    if input_level_g <= 0:
        raise ValueError("input_level_g must be positive")
    if response_limit_g <= 0:
        raise ValueError("response_limit_g must be positive")
    if predicted_response_g <= 0:
        raise ValueError("predicted_response_g must be positive")

    if predicted_response_g <= response_limit_g:
        return input_level_g, False

    notch_factor = response_limit_g / predicted_response_g
    return input_level_g * notch_factor, True


def compute_grms(psd_segments):
    """
    Compute overall Grms from a list of constant-PSD breakpoint segments.

    psd_segments: list of (f_low_hz, f_high_hz, psd_g2_per_hz) tuples.
    Each tuple describes a frequency band with a flat PSD level.
    Bands must not overlap and each f_low < f_high.

    Returns Grms (g-rms) as float.
    Raises ValueError for an empty list or invalid segment values.
    """
    if not psd_segments:
        raise ValueError("psd_segments must not be empty")

    total_mean_square = 0.0
    for i, seg in enumerate(psd_segments):
        f_low, f_high, psd_val = seg
        if f_low <= 0 or f_high <= 0:
            raise ValueError(f"Segment {i}: frequencies must be positive")
        if f_low >= f_high:
            raise ValueError(f"Segment {i}: f_low must be less than f_high")
        if psd_val < 0:
            raise ValueError(f"Segment {i}: PSD value must be non-negative")
        total_mean_square += psd_val * (f_high - f_low)

    return math.sqrt(total_mean_square)


def check_srs_compliance(response_g, spec_limit_g):
    """
    Check whether a shock response spectrum (SRS) response value at a
    single frequency point meets the specified SRS envelope limit.

    response_g: computed or measured SRS value at the frequency (g).
    spec_limit_g: specification limit at the same frequency (g), must be > 0.

    Returns (compliant: bool, ratio: float).
    ratio = response_g / spec_limit_g; ratio <= 1.0 means compliant.
    """
    if response_g < 0:
        raise ValueError("response_g must be non-negative")
    if spec_limit_g <= 0:
        raise ValueError("spec_limit_g must be positive")

    ratio = response_g / spec_limit_g
    return ratio <= 1.0, ratio


def check_qualification_margin(qual_level_g, accept_level_g, min_margin_db):
    """
    Verify that the qualification test level exceeds the acceptance level
    by at least min_margin_db (decibels, 20*log10 scale for acceleration).

    Returns (passes: bool, actual_margin_db: float).
    """
    if qual_level_g <= 0 or accept_level_g <= 0:
        raise ValueError("Test levels must be positive")
    if min_margin_db < 0:
        raise ValueError("min_margin_db must be non-negative")

    actual_db = 20.0 * math.log10(qual_level_g / accept_level_g)
    return actual_db >= min_margin_db, actual_db


def get_random_test_duration_seconds(test_level):
    """
    Return the standard random-vibration test duration per axis (seconds).
    Qualification: 120 s/axis.  Acceptance / proto-flight: 60 s/axis.
    Raises ValueError for unrecognized test levels.
    """
    level = categorize_test_level(test_level)
    durations = {
        "qualification": 120,
        "acceptance": 60,
        "proto_flight": 60,
    }
    return durations[level]


def get_shock_pulse_count(test_level):
    """
    Return the number of shock pulses per axis for the given test level.
    Qualification / proto-flight: 3 pulses.  Acceptance: 2 pulses.
    Raises ValueError for unrecognized test levels.
    """
    level = categorize_test_level(test_level)
    counts = {
        "qualification": 3,
        "proto_flight": 3,
        "acceptance": 2,
    }
    return counts[level]


def check_notching_justification(notch_applied, justification):
    """
    Verify that if notching was applied a written justification is on record.
    justification: a non-empty string, or None / empty string if absent.

    Returns (compliant: bool, finding: str or None).
    A finding of None means no issue.
    """
    if notch_applied and not justification:
        return False, "Notching applied but no written justification on record"
    return True, None


def build_test_summary(test_type, test_level, axes, notching_applied):
    """
    Build an immutable summary dict for a dynamic test plan entry.
    Raises ValueError if test_type or test_level are unrecognized.
    """
    normalized_type = categorize_test_type(test_type)
    normalized_level = categorize_test_level(test_level)
    if not axes or not isinstance(axes, (list, tuple)):
        raise ValueError("axes must be a non-empty list or tuple")
    return {
        "test_type": normalized_type,
        "test_level": normalized_level,
        "axes": tuple(axes),
        "notching_applied": bool(notching_applied),
    }
