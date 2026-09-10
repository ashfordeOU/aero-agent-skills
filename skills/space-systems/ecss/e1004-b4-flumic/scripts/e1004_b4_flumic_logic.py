#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex B.4 FLUMIC worst-case trapped electron model
logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
FLUMIC bounds the trapped electron energy spectrum in the outer
radiation belt (including geostationary altitudes) and the inner belt
as a worst case, parametrized by a confidence (percentile) level and
an exposure-duration class, rather than as a long-term average. A
short (worst-day) duration class bounds transient peak flux for
peak-risk internal-charging assessments; a long (mission-life)
duration class gives the cumulative-fluence bound. Internal
(deep-dielectric) charging risk depends on the integral flux above a
shielding-relevant threshold energy, summed over every belt region an
orbit crosses. This module implements the region-parameter lookup,
confidence/duration scaling, differential-spectrum evaluation,
threshold integration, and duration-class compliance logic; it does
not implement the NASA worst-case GEO spectrum (see the sibling
e1004-b5-geo-wc leaf) or the combined internal-charging assessment
roll-up (see the sibling e1004-internal-charging leaf).
"""

import math

REGION_PARAMS = {
    "inner_belt": {"flux0": 5.0e9, "e0_mev": 0.3},
    "outer_belt": {"flux0": 2.0e10, "e0_mev": 0.6},
}

CONFIDENCE_SCALE = {
    90: 1.0,
    95: 1.3,
    99: 1.8,
}

DURATION_SCALE = {
    "worst_day": 1.0,
    "worst_week": 0.6,
    "mission": 0.25,
}

REQUIRED_DURATION_CLASS = {
    "peak_risk": "worst_day",
    "cumulative_fluence": "mission",
}


def region_params(region):
    """Copy of the reference flux0 (per unit area, time, energy) and
    characteristic rolloff energy e0_mev for one belt region ("inner_belt"
    or "outer_belt"). Raises ValueError for an unknown region."""
    if region not in REGION_PARAMS:
        raise ValueError("unknown belt region: %r" % (region,))
    return dict(REGION_PARAMS[region])


def confidence_scale_factor(percentile):
    """Scale factor applied to the reference spectrum for one
    confidence (percentile) level. Raises ValueError for an unsupported
    percentile."""
    if percentile not in CONFIDENCE_SCALE:
        raise ValueError("unsupported confidence percentile: %r" % (percentile,))
    return CONFIDENCE_SCALE[percentile]


def duration_scale_factor(duration_class):
    """Scale factor applied to the reference spectrum for one
    exposure-duration class. Raises ValueError for an unknown duration
    class."""
    if duration_class not in DURATION_SCALE:
        raise ValueError("unknown duration class: %r" % (duration_class,))
    return DURATION_SCALE[duration_class]


def required_duration_class(analysis_purpose):
    """Exposure-duration class one analysis purpose requires:
    worst_day for peak transient risk, mission for cumulative fluence.
    Raises ValueError for an unknown analysis purpose."""
    if analysis_purpose not in REQUIRED_DURATION_CLASS:
        raise ValueError("unknown analysis purpose: %r" % (analysis_purpose,))
    return REQUIRED_DURATION_CLASS[analysis_purpose]


def differential_flux(region, energy_mev, percentile, duration_class):
    """FLUMIC differential electron flux at energy_mev for one belt
    region, confidence percentile, and duration class: an exponential
    reference spectrum scaled by the confidence and duration factors.
    Raises ValueError when energy_mev is negative."""
    if energy_mev < 0:
        raise ValueError("energy_mev must not be negative")
    params = region_params(region)
    scale = confidence_scale_factor(percentile) * duration_scale_factor(duration_class)
    return params["flux0"] * scale * math.exp(-energy_mev / params["e0_mev"])


def integral_flux_above(region, threshold_energy_mev, percentile, duration_class):
    """Integral of differential_flux() from threshold_energy_mev to
    infinity for one belt region, evaluated analytically for the
    exponential reference spectrum. Raises ValueError when
    threshold_energy_mev is negative."""
    if threshold_energy_mev < 0:
        raise ValueError("threshold_energy_mev must not be negative")
    params = region_params(region)
    scale = confidence_scale_factor(percentile) * duration_scale_factor(duration_class)
    return (
        params["flux0"]
        * scale
        * params["e0_mev"]
        * math.exp(-threshold_energy_mev / params["e0_mev"])
    )


def combined_integral_flux_above(regions, threshold_energy_mev, percentile, duration_class):
    """Sum of integral_flux_above() over every region in regions (a
    belt-crossing orbit's full set of belt regions). Raises ValueError
    when regions is empty."""
    if not regions:
        raise ValueError("regions must not be empty")
    return sum(
        integral_flux_above(region, threshold_energy_mev, percentile, duration_class)
        for region in regions
    )


def assess_case(case):
    """Full FLUMIC evaluation and duration-class compliance assessment
    for one case dict. Required keys: id, regions, analysis_purpose,
    duration_class, percentile, threshold_energy_mev. Returns a new
    dict; does not mutate the input. Raises ValueError when 'id' is
    missing or analysis_purpose is unknown."""
    if "id" not in case:
        raise ValueError("FLUMIC case is missing an id")
    analysis_purpose = case["analysis_purpose"]
    duration_class = case["duration_class"]
    needed_duration_class = required_duration_class(analysis_purpose)
    duration_class_ok = duration_class == needed_duration_class
    flux_above_threshold = combined_integral_flux_above(
        case["regions"],
        case["threshold_energy_mev"],
        case["percentile"],
        duration_class,
    )
    return {
        "id": case["id"],
        "regions": list(case["regions"]),
        "analysis_purpose": analysis_purpose,
        "duration_class": duration_class,
        "required_duration_class": needed_duration_class,
        "duration_class_ok": duration_class_ok,
        "percentile": case["percentile"],
        "threshold_energy_mev": case["threshold_energy_mev"],
        "flux_above_threshold": flux_above_threshold,
        "compliant": duration_class_ok,
    }


def build_assessment(cases):
    """Assessment record: one assess_case() result per case, in input
    order. Raises ValueError on a duplicate case id."""
    record = []
    seen_ids = set()
    for case in cases:
        assessment = assess_case(case)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate FLUMIC case id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        record.append(assessment)
    return record


def noncompliant_items(record):
    """Case ids in the record that are not compliant, in record
    order -- these cannot feed the internal-charging assessment
    as-is."""
    return [entry["id"] for entry in record if not entry["compliant"]]


def all_compliant(record):
    """True when every entry in the assessment record is compliant."""
    return len(noncompliant_items(record)) == 0
