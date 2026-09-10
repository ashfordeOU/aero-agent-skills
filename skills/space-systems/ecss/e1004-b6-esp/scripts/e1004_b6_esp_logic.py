#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex B.6 Emission of Solar Protons (ESP) worst-case
fluence spectra (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): Annex
B.6 documents a probabilistic solar-proton worst-case model (the JPL
"ESP" family) that, unlike a single deterministic event spectrum,
returns a design fluence-above-energy spectrum keyed by two inputs: the
mission exposure duration (longer exposure raises the chance of
encountering a large event) and a design confidence level (the
probability that the true mission fluence will not exceed the returned
value -- a higher confidence level pushes further into the rare, large-
event tail and so returns a larger fluence). This module implements the
duration and confidence-level scaling of a reference annual fluence
spectrum, spectrum assembly across the model's supported energy
thresholds, and the worst-case confidence-level compliance check; it
does not implement a specific published ESP coefficient table (see the
data-provenance note in SKILL.md) or peak (non-integrated) flux
estimation.
"""

import math

REFERENCE_ENERGIES_MEV = (1.0, 4.0, 10.0, 30.0, 60.0, 100.0)

# Reference 1-year, 50%-confidence integral fluence (protons/cm^2, fluence
# above the given threshold energy). Representative engineering
# placeholders calibrated to the correct decreasing-with-energy shape of
# a solar-proton worst-case spectrum -- see SKILL.md data-provenance note.
BASELINE_ANNUAL_FLUENCE_CM2 = {
    1.0: 5.0e10,
    4.0: 1.5e10,
    10.0: 5.0e9,
    30.0: 1.0e9,
    60.0: 3.0e8,
    100.0: 1.0e8,
}

MIN_CONFIDENCE_PCT = 50.0
MAX_CONFIDENCE_PCT = 99.0
BASELINE_CONFIDENCE_PCT = 50.0

# Confidence level most guidance treats as the floor for a worst-case
# solar-proton design fluence.
RECOMMENDED_MIN_CONFIDENCE_PCT = 90.0

# Sub-linear exponent for the mission-duration scaling: longer exposure
# raises the design fluence, but not in direct proportion to duration.
DURATION_EXPONENT = 0.6


def confidence_scale_factor(confidence_pct):
    """Multiplier applied to the baseline fluence for a design confidence
    level (percent). 1.0 at BASELINE_CONFIDENCE_PCT (50%); grows without
    bound as confidence_pct approaches 100, reflecting that bounding a
    larger fraction of the event-size probability distribution requires
    reaching further into the rare, large-event tail. Raises ValueError
    outside [MIN_CONFIDENCE_PCT, MAX_CONFIDENCE_PCT]."""
    if not (MIN_CONFIDENCE_PCT <= confidence_pct <= MAX_CONFIDENCE_PCT):
        raise ValueError(
            "confidence_pct must be within [%s, %s] under E-ST-10-04C "
            "Annex B.6; got %r" % (MIN_CONFIDENCE_PCT, MAX_CONFIDENCE_PCT, confidence_pct)
        )
    p = confidence_pct / 100.0
    baseline_p = BASELINE_CONFIDENCE_PCT / 100.0
    return math.log(1.0 - p) / math.log(1.0 - baseline_p)


def duration_scale_factor(mission_duration_years):
    """Multiplier applied to the baseline fluence for a mission exposure
    duration (years). 1.0 at 1 year; increases sub-linearly with
    duration. Raises ValueError for a non-positive duration."""
    if mission_duration_years <= 0:
        raise ValueError("mission_duration_years must be > 0")
    return mission_duration_years ** DURATION_EXPONENT


def integral_fluence_above(threshold_mev, mission_duration_years, confidence_pct):
    """Design integral fluence (protons/cm^2, fluence above
    threshold_mev) for one energy threshold, scaled from the reference
    1-year/50%-confidence spectrum by duration_scale_factor and
    confidence_scale_factor. threshold_mev must be one of
    REFERENCE_ENERGIES_MEV (the model's supported thresholds); raises
    ValueError otherwise."""
    if threshold_mev not in BASELINE_ANNUAL_FLUENCE_CM2:
        raise ValueError(
            "unsupported ESP threshold energy %r MeV; supported "
            "thresholds are %r" % (threshold_mev, REFERENCE_ENERGIES_MEV)
        )
    baseline = BASELINE_ANNUAL_FLUENCE_CM2[threshold_mev]
    return (
        baseline
        * duration_scale_factor(mission_duration_years)
        * confidence_scale_factor(confidence_pct)
    )


def fluence_spectrum(mission_duration_years, confidence_pct):
    """Full ESP integral fluence spectrum for a mission duration and
    confidence level: an ordered dict of threshold energy (MeV) to
    design fluence (protons/cm^2) across every REFERENCE_ENERGIES_MEV
    threshold, ascending by energy."""
    return {
        energy: integral_fluence_above(energy, mission_duration_years, confidence_pct)
        for energy in REFERENCE_ENERGIES_MEV
    }


def is_spectrum_monotonic_decreasing(spectrum):
    """True when a fluence_spectrum result strictly decreases as energy
    increases -- the expected shape of an integral fluence-above-energy
    spectrum (fewer protons exceed a higher energy threshold)."""
    energies = list(spectrum.keys())
    fluences = [spectrum[energy] for energy in energies]
    return all(fluences[i] > fluences[i + 1] for i in range(len(fluences) - 1))


def meets_worst_case_confidence(confidence_pct, required_confidence_pct=RECOMMENDED_MIN_CONFIDENCE_PCT):
    """True when a case's design confidence level meets or exceeds the
    required worst-case confidence-level threshold."""
    return confidence_pct >= required_confidence_pct


def assess_esp_case(case):
    """Full Annex B.6 ESP assessment for one radiation-design case.

    case: {"case_id": str, "mission_duration_years": float,
    "confidence_pct": float, "required_confidence_pct": float
    (optional, defaults to RECOMMENDED_MIN_CONFIDENCE_PCT)}. Returns
    {"case_id": str, "spectrum": {energy: fluence, ...}, "compliant":
    bool, "findings": [...]}. Raises ValueError for an invalid
    mission_duration_years or confidence_pct (see duration_scale_factor,
    confidence_scale_factor)."""
    case_id = case["case_id"]
    mission_duration_years = case["mission_duration_years"]
    confidence_pct = case["confidence_pct"]
    required_confidence_pct = case.get(
        "required_confidence_pct", RECOMMENDED_MIN_CONFIDENCE_PCT
    )
    spectrum = fluence_spectrum(mission_duration_years, confidence_pct)
    findings = []
    spectrum_ok = is_spectrum_monotonic_decreasing(spectrum)
    if not spectrum_ok:
        findings.append(
            {"issue": "non_monotonic_fluence_spectrum", "case": case_id}
        )
    confidence_ok = meets_worst_case_confidence(confidence_pct, required_confidence_pct)
    if not confidence_ok:
        findings.append(
            {
                "issue": "confidence_level_below_worst_case_threshold",
                "case": case_id,
                "confidence_pct": confidence_pct,
                "required_confidence_pct": required_confidence_pct,
            }
        )
    return {
        "case_id": case_id,
        "spectrum": spectrum,
        "compliant": spectrum_ok and confidence_ok,
        "findings": findings,
    }
