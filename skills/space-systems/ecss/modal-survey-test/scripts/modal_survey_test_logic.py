#!/usr/bin/env python3
"""ECSS-E-ST-32-11C clause 4.6.3.8 modal survey test logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): a modal survey
test excites a spacecraft structural assembly with a controlled input force,
measures frequency response functions at a sufficient number of points to spatially
resolve all target modes, and extracts modal parameters (natural frequency, viscous
damping ratio, mode shape). Finite element model correlation uses the Modal
Assurance Criterion (MAC) to compare measured and predicted mode shapes; a value
at or above the acceptance threshold combined with a measured frequency within the
allowable tolerance of the FEM prediction constitutes a passing mode pair. Every
target mode must be identified; any gap is a coverage finding. Damping estimates
outside the physically plausible structural range (0.1 % to 10 %) flag a
measurement or processing anomaly. This module implements excitation method
validation, MAC computation, frequency correlation, damping plausibility,
measurement adequacy, mode coverage, and the aggregated compliance verdict; it
does not implement FRF curve-fitting or sensor placement optimisation.
"""

VALID_EXCITATION_METHODS = frozenset(
    {"sine_sweep", "stepped_sine", "broadband_random", "impact"}
)

DAMPING_RATIO_MIN = 0.001
DAMPING_RATIO_MAX = 0.10

DEFAULT_MAC_THRESHOLD = 0.90
DEFAULT_FREQ_TOLERANCE = 0.05


def validate_excitation_method(method):
    """Confirm the excitation method is one of the four recognised types.
    Raises ValueError for any method not in VALID_EXCITATION_METHODS."""
    if method not in VALID_EXCITATION_METHODS:
        raise ValueError(
            "unrecognised excitation method %r; must be one of %s"
            % (method, sorted(VALID_EXCITATION_METHODS))
        )


def compute_mac(test_shape, fem_shape):
    """Modal Assurance Criterion between two real-valued mode shape vectors.

    MAC = (sum_i(a_i * b_i))^2 / ((sum_i(a_i^2)) * (sum_i(b_i^2)))

    Returns a float in [0.0, 1.0]. Raises ValueError for mismatched lengths,
    empty vectors, or a zero-norm vector (physically degenerate)."""
    if len(test_shape) != len(fem_shape):
        raise ValueError(
            "test_shape length %d != fem_shape length %d"
            % (len(test_shape), len(fem_shape))
        )
    if len(test_shape) == 0:
        raise ValueError("mode shape vectors must be non-empty")
    dot = sum(a * b for a, b in zip(test_shape, fem_shape))
    norm_a = sum(a * a for a in test_shape)
    norm_b = sum(b * b for b in fem_shape)
    if norm_a == 0.0:
        raise ValueError("test_shape is a zero vector — cannot compute MAC")
    if norm_b == 0.0:
        raise ValueError("fem_shape is a zero vector — cannot compute MAC")
    return (dot * dot) / (norm_a * norm_b)


def check_frequency_correlation(test_freq_hz, fem_freq_hz, tolerance_fraction=DEFAULT_FREQ_TOLERANCE):
    """True when the relative frequency deviation is within the allowable tolerance.

    Deviation = |test_freq_hz - fem_freq_hz| / fem_freq_hz. Raises ValueError
    for a non-positive fem_freq_hz or a negative test_freq_hz."""
    if fem_freq_hz <= 0.0:
        raise ValueError("fem_freq_hz must be positive, got %r" % (fem_freq_hz,))
    if test_freq_hz < 0.0:
        raise ValueError("test_freq_hz must be non-negative, got %r" % (test_freq_hz,))
    if tolerance_fraction < 0.0:
        raise ValueError("tolerance_fraction must be non-negative")
    deviation = abs(test_freq_hz - fem_freq_hz) / fem_freq_hz
    return deviation <= tolerance_fraction


def check_damping_plausible(damping_ratio):
    """True when the viscous damping ratio is within the physically plausible
    range [DAMPING_RATIO_MIN, DAMPING_RATIO_MAX] for spacecraft structures."""
    return DAMPING_RATIO_MIN <= damping_ratio <= DAMPING_RATIO_MAX


def check_mode_coverage(identified_mode_ids, target_mode_ids):
    """List of target mode identifiers that have no corresponding identified mode.
    Returns an empty list when every target mode is covered. Does not mutate
    either argument."""
    identified = set(identified_mode_ids)
    return [m for m in target_mode_ids if m not in identified]


def check_measurement_adequacy(num_measurement_points, min_required):
    """Adequacy verdict for the measurement point configuration.

    Returns {"adequate": True} when num_measurement_points >= min_required,
    otherwise {"adequate": False, "shortfall": min_required - num_measurement_points}.
    Raises ValueError for negative arguments."""
    if num_measurement_points < 0:
        raise ValueError("num_measurement_points must be non-negative")
    if min_required < 0:
        raise ValueError("min_required must be non-negative")
    if num_measurement_points >= min_required:
        return {"adequate": True}
    return {
        "adequate": False,
        "shortfall": min_required - num_measurement_points,
    }


def modal_mode_verdict(
    mode_id,
    test_freq_hz,
    fem_freq_hz,
    test_shape,
    fem_shape,
    damping_ratio,
    mac_threshold=DEFAULT_MAC_THRESHOLD,
    freq_tolerance=DEFAULT_FREQ_TOLERANCE,
):
    """Per-mode finding list for one test-prediction mode pair.

    Returns a list of finding dicts (empty when the mode passes all checks).
    Findings issued: mac_below_threshold, frequency_outside_tolerance,
    damping_outside_plausible_range."""
    findings = []
    mac = compute_mac(test_shape, fem_shape)
    if mac < mac_threshold:
        findings.append(
            {
                "issue": "mac_below_threshold",
                "mode_id": mode_id,
                "mac": mac,
                "threshold": mac_threshold,
            }
        )
    if not check_frequency_correlation(test_freq_hz, fem_freq_hz, freq_tolerance):
        deviation = abs(test_freq_hz - fem_freq_hz) / fem_freq_hz
        findings.append(
            {
                "issue": "frequency_outside_tolerance",
                "mode_id": mode_id,
                "test_freq_hz": test_freq_hz,
                "fem_freq_hz": fem_freq_hz,
                "deviation_fraction": deviation,
                "tolerance_fraction": freq_tolerance,
            }
        )
    if not check_damping_plausible(damping_ratio):
        findings.append(
            {
                "issue": "damping_outside_plausible_range",
                "mode_id": mode_id,
                "damping_ratio": damping_ratio,
                "min": DAMPING_RATIO_MIN,
                "max": DAMPING_RATIO_MAX,
            }
        )
    return findings


def modal_survey_compliance(survey):
    """Full compliance verdict for a modal survey test.

    survey keys:
      excitation_method: str
      num_measurement_points: int
      min_measurement_points: int
      target_mode_ids: list[str]
      modes: list of dicts, each with:
        mode_id: str
        test_freq_hz: float
        fem_freq_hz: float
        test_shape: list[float]
        fem_shape: list[float]
        damping_ratio: float
      mac_threshold: float  (optional, default DEFAULT_MAC_THRESHOLD)
      freq_tolerance: float (optional, default DEFAULT_FREQ_TOLERANCE)

    Returns:
      excitation_finding: None or error str
      measurement_finding: None or {"adequate": False, "shortfall": int}
      coverage_finding: list of missing target mode ids
      mode_findings: {mode_id: [finding dicts]}
      compliant: bool (True only when all finding containers are empty/None)

    Does not mutate survey."""
    mac_threshold = survey.get("mac_threshold", DEFAULT_MAC_THRESHOLD)
    freq_tolerance = survey.get("freq_tolerance", DEFAULT_FREQ_TOLERANCE)

    excitation_finding = None
    try:
        validate_excitation_method(survey["excitation_method"])
    except ValueError as exc:
        excitation_finding = str(exc)

    meas = check_measurement_adequacy(
        survey["num_measurement_points"],
        survey["min_measurement_points"],
    )
    measurement_finding = None if meas["adequate"] else meas

    identified_ids = [m["mode_id"] for m in survey.get("modes", [])]
    coverage_finding = check_mode_coverage(identified_ids, survey.get("target_mode_ids", []))

    mode_findings = {}
    for mode in survey.get("modes", []):
        findings = modal_mode_verdict(
            mode["mode_id"],
            mode["test_freq_hz"],
            mode["fem_freq_hz"],
            mode["test_shape"],
            mode["fem_shape"],
            mode["damping_ratio"],
            mac_threshold=mac_threshold,
            freq_tolerance=freq_tolerance,
        )
        if findings:
            mode_findings[mode["mode_id"]] = findings

    compliant = (
        excitation_finding is None
        and measurement_finding is None
        and len(coverage_finding) == 0
        and len(mode_findings) == 0
    )

    return {
        "excitation_finding": excitation_finding,
        "measurement_finding": measurement_finding,
        "coverage_finding": coverage_finding,
        "mode_findings": mode_findings,
        "compliant": compliant,
    }
