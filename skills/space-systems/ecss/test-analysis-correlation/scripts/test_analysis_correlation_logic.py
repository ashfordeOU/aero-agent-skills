#!/usr/bin/env python3
"""ECSS-E-ST-32C / ECSS-E-ST-32-11 test-analysis correlation assessment
(paraphrase, not verbatim ECSS text).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
structural general requirements (E-ST-32C) and modal survey assessment
standard (E-ST-32-11) require that measured natural frequencies and mode
shapes from a structural modal survey be paired with FE model predictions
and checked against two acceptance criteria — a relative frequency-deviation
tolerance (typically ±5 %) and a Modal Assurance Criterion (MAC) threshold
for mode-shape similarity (typically ≥ 0.90 for primary structural modes).
A test mode for which no analysis mode reaches the MAC threshold is unpaired
and constitutes a TAC discrepancy. All discrepancies must be dispositioned
before the FE model is approved for structural load analysis. This module
implements frequency-deviation computation, MAC calculation, one-to-one
mode pairing, per-criterion violation checking, and the aggregated TAC
review; it does not define project-specific acceptance thresholds or the
engineering disposition process.
"""

DEFAULT_FREQUENCY_TOLERANCE = 0.05   # ±5 % relative deviation
DEFAULT_MAC_THRESHOLD = 0.90         # MAC ≥ 0.90 for primary modes
NO_PAIR = "no_pair"


def frequency_deviation(f_test, f_analysis):
    """Relative frequency deviation (f_test - f_analysis) / f_analysis.
    Raises ValueError for a negative f_test or a non-positive f_analysis."""
    if f_test < 0:
        raise ValueError("f_test must be >= 0, got %r" % (f_test,))
    if f_analysis <= 0:
        raise ValueError("f_analysis must be > 0, got %r" % (f_analysis,))
    return (f_test - f_analysis) / f_analysis


def frequency_within_tolerance(f_test, f_analysis, tolerance):
    """True when abs(frequency_deviation(f_test, f_analysis)) <= tolerance.
    Raises ValueError for a non-positive tolerance."""
    if tolerance <= 0:
        raise ValueError("tolerance must be > 0, got %r" % (tolerance,))
    return abs(frequency_deviation(f_test, f_analysis)) <= tolerance


def _dot(v1, v2):
    """Inner product of two equal-length sequences."""
    if len(v1) != len(v2):
        raise ValueError(
            "mode-shape vectors must have the same length (%d vs %d)"
            % (len(v1), len(v2))
        )
    return sum(a * b for a, b in zip(v1, v2))


def mac_value(phi_test, phi_analysis):
    """Modal Assurance Criterion in [0, 1] for two real mode-shape vectors.
    MAC = (phi_t . phi_a)^2 / ((phi_t . phi_t)(phi_a . phi_a)).
    Raises ValueError when either vector has zero norm or lengths differ."""
    phi_test = list(phi_test)
    phi_analysis = list(phi_analysis)
    cross = _dot(phi_test, phi_analysis)
    norm_t = _dot(phi_test, phi_test)
    norm_a = _dot(phi_analysis, phi_analysis)
    if norm_t == 0.0:
        raise ValueError("test mode-shape vector has zero norm")
    if norm_a == 0.0:
        raise ValueError("analysis mode-shape vector has zero norm")
    return (cross ** 2) / (norm_t * norm_a)


def pair_modes(test_modes, analysis_modes, mac_threshold=DEFAULT_MAC_THRESHOLD):
    """One-to-one pairing of test modes to analysis modes by highest MAC.

    test_modes and analysis_modes: lists of dicts with keys
      "mode_id"      — unique string identifier
      "frequency_hz" — natural frequency in Hz (float > 0)
      "shape"        — list of floats (normalised mode-shape components)

    Each test mode is paired to the analysis mode with the highest MAC
    that meets mac_threshold; an analysis mode already paired is not
    reused (greedy one-to-one). A test mode with no candidate at or
    above mac_threshold is paired with NO_PAIR.

    Returns a list of dicts:
      "test_mode_id"     — from test_modes
      "analysis_mode_id" — from analysis_modes, or NO_PAIR
      "mac"              — best MAC found (0.0 when no candidate)
      "f_test_hz"        — from test_modes
      "f_analysis_hz"    — from analysis_modes, or None when NO_PAIR

    Does not mutate inputs.
    """
    used_analysis_ids = set()
    pairs = []
    for tm in test_modes:
        best_mac = -1.0
        best_am = None
        for am in analysis_modes:
            if am["mode_id"] in used_analysis_ids:
                continue
            try:
                m = mac_value(tm["shape"], am["shape"])
            except ValueError:
                m = 0.0
            if m > best_mac:
                best_mac = m
                best_am = am
        if best_am is not None and best_mac >= mac_threshold:
            used_analysis_ids.add(best_am["mode_id"])
            pairs.append(
                {
                    "test_mode_id": tm["mode_id"],
                    "analysis_mode_id": best_am["mode_id"],
                    "mac": best_mac,
                    "f_test_hz": tm["frequency_hz"],
                    "f_analysis_hz": best_am["frequency_hz"],
                }
            )
        else:
            pairs.append(
                {
                    "test_mode_id": tm["mode_id"],
                    "analysis_mode_id": NO_PAIR,
                    "mac": max(best_mac, 0.0),
                    "f_test_hz": tm["frequency_hz"],
                    "f_analysis_hz": None,
                }
            )
    return pairs


def frequency_correlation_violations(
    pairs, freq_tolerance=DEFAULT_FREQUENCY_TOLERANCE
):
    """Violation list for frequency correlation across mode pairs.
    Unpaired test modes are reported as "unmatched_test_mode" violations.
    Paired modes whose frequency deviation exceeds freq_tolerance are
    reported as "frequency_deviation_exceeded" violations.
    Returns list of dicts; empty list means no frequency violations."""
    violations = []
    for p in pairs:
        if p["analysis_mode_id"] == NO_PAIR:
            violations.append(
                {
                    "issue": "unmatched_test_mode",
                    "test_mode_id": p["test_mode_id"],
                    "mac": p["mac"],
                }
            )
            continue
        if not frequency_within_tolerance(
            p["f_test_hz"], p["f_analysis_hz"], freq_tolerance
        ):
            dev = frequency_deviation(p["f_test_hz"], p["f_analysis_hz"])
            violations.append(
                {
                    "issue": "frequency_deviation_exceeded",
                    "test_mode_id": p["test_mode_id"],
                    "analysis_mode_id": p["analysis_mode_id"],
                    "deviation": dev,
                    "tolerance": freq_tolerance,
                }
            )
    return violations


def mac_correlation_violations(pairs, mac_threshold=DEFAULT_MAC_THRESHOLD):
    """Violation list for MAC criterion across paired modes.
    Unpaired test modes are excluded (already captured by
    frequency_correlation_violations as unmatched_test_mode).
    Returns list of dicts; empty list means no MAC violations."""
    violations = []
    for p in pairs:
        if p["analysis_mode_id"] == NO_PAIR:
            continue
        if p["mac"] < mac_threshold:
            violations.append(
                {
                    "issue": "mac_below_threshold",
                    "test_mode_id": p["test_mode_id"],
                    "analysis_mode_id": p["analysis_mode_id"],
                    "mac": p["mac"],
                    "mac_threshold": mac_threshold,
                }
            )
    return violations


def correlation_review(
    test_modes,
    analysis_modes,
    freq_tolerance=DEFAULT_FREQUENCY_TOLERANCE,
    mac_threshold=DEFAULT_MAC_THRESHOLD,
):
    """Full TAC review per ECSS-E-ST-32C / ECSS-E-ST-32-11.

    Returns:
      {"pairs": [...], "frequency_violations": [...], "mac_violations": [...]}

    The review is compliant when both violation lists are empty.
    Does not mutate inputs.
    """
    pairs = pair_modes(test_modes, analysis_modes, mac_threshold)
    return {
        "pairs": pairs,
        "frequency_violations": frequency_correlation_violations(
            pairs, freq_tolerance
        ),
        "mac_violations": mac_correlation_violations(pairs, mac_threshold),
    }


def is_correlation_compliant(review):
    """True when both violation lists in a correlation_review result are
    empty — the TAC satisfies ECSS-E-ST-32C / E-ST-32-11 acceptance
    criteria for this mode set."""
    return (
        len(review["frequency_violations"]) == 0
        and len(review["mac_violations"]) == 0
    )
