#!/usr/bin/env python3
"""ECSS-E-ST-10-12C §9.4.1.8 SEHE rate prediction (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
radiation effects specification's SEHE clause requires predicting the rate
of single event housekeeping and functional interrupts in a device by
fitting a Weibull curve to the device's measured heavy-ion threshold
cross-section data (LET threshold, width, shape exponent, saturation
cross-section), integrating that curve against the mission heavy-ion LET
spectrum at the shielded device location to obtain the unshielded rate,
applying a shielding attenuation factor, and comparing the result against
the mission SEHE rate requirement under the applicable design margin. A
device with a nonzero computed rate and no captured requirement is itself
a finding; a device whose rate scaled by the design margin exceeds the
allowable rate fails the margin check even if it passes the raw threshold.
"""

import math

NO_RATE_REQUIREMENT = None


def weibull_cross_section(
    let_mev_cm2_mg,
    sigma_sat_cm2,
    let_threshold_mev_cm2_mg,
    weibull_width,
    weibull_exponent,
):
    """Weibull SEHE cross-section (cm^2/device) at a given LET value.

    Returns 0.0 for LET at or below the threshold.
    Raises ValueError for non-positive sigma_sat, negative threshold,
    non-positive width, or non-positive exponent.
    """
    if sigma_sat_cm2 <= 0:
        raise ValueError("sigma_sat_cm2 must be > 0, got %r" % sigma_sat_cm2)
    if let_threshold_mev_cm2_mg < 0:
        raise ValueError(
            "let_threshold_mev_cm2_mg must be >= 0, got %r" % let_threshold_mev_cm2_mg
        )
    if weibull_width <= 0:
        raise ValueError("weibull_width must be > 0, got %r" % weibull_width)
    if weibull_exponent <= 0:
        raise ValueError("weibull_exponent must be > 0, got %r" % weibull_exponent)
    if let_mev_cm2_mg <= let_threshold_mev_cm2_mg:
        return 0.0
    excess = (let_mev_cm2_mg - let_threshold_mev_cm2_mg) / weibull_width
    return sigma_sat_cm2 * (1.0 - math.exp(-(excess ** weibull_exponent)))


def integrate_sehe_rate(
    sigma_sat_cm2,
    let_threshold_mev_cm2_mg,
    weibull_width,
    weibull_exponent,
    let_flux_pairs,
):
    """Compute the SEHE rate (events/device/day) by trapezoidal integration
    of the Weibull cross-section against the differential heavy-ion LET spectrum.

    let_flux_pairs: iterable of (let_mev_cm2_mg, differential_flux) tuples
    in strictly ascending LET order, where differential_flux is the ion flux
    per unit LET interval (ions/cm^2/day per MeV·cm^2/mg).

    Requires at least 2 LET-flux points. Raises ValueError for fewer points
    or non-strictly-ascending LET values.
    """
    pairs = list(let_flux_pairs)
    if len(pairs) < 2:
        raise ValueError(
            "at least 2 LET-flux pairs required for integration, got %d" % len(pairs)
        )
    for i in range(1, len(pairs)):
        if pairs[i][0] <= pairs[i - 1][0]:
            raise ValueError(
                "LET values must be strictly ascending; index %d: %r <= %r"
                % (i, pairs[i][0], pairs[i - 1][0])
            )
    rate = 0.0
    for i in range(1, len(pairs)):
        let_a, flux_a = pairs[i - 1]
        let_b, flux_b = pairs[i]
        sigma_a = weibull_cross_section(
            let_a, sigma_sat_cm2, let_threshold_mev_cm2_mg, weibull_width, weibull_exponent
        )
        sigma_b = weibull_cross_section(
            let_b, sigma_sat_cm2, let_threshold_mev_cm2_mg, weibull_width, weibull_exponent
        )
        delta_let = let_b - let_a
        rate += 0.5 * (sigma_a * flux_a + sigma_b * flux_b) * delta_let
    return rate


def apply_shielding_reduction(base_rate, shielding_factor):
    """Apply a shielding attenuation factor to a base SEHE rate.

    shielding_factor in [0.0, 1.0]: 1.0 means no attenuation (worst case),
    0.0 means total attenuation. Raises ValueError for a negative base rate
    or an out-of-range factor.
    """
    if base_rate < 0:
        raise ValueError("base_rate must be >= 0, got %r" % base_rate)
    if not (0.0 <= shielding_factor <= 1.0):
        raise ValueError(
            "shielding_factor must be in [0.0, 1.0], got %r" % shielding_factor
        )
    return base_rate * shielding_factor


def check_sehe_rate(computed_rate_per_day, allowable_rate_per_day, design_margin_factor=10.0):
    """Check the computed SEHE rate against the mission requirement and margin.

    The rate is compliant when computed_rate_per_day * design_margin_factor
    <= allowable_rate_per_day (i.e. the predicted rate is at most
    1/design_margin_factor of the allowable rate).

    A None allowable_rate_per_day with nonzero computed rate returns
    issue "missing_sehe_rate_requirement". A nonzero rate that passes the
    raw threshold but fails the margin check returns
    "sehe_margin_not_met". An exceedance of the raw threshold returns
    "sehe_rate_exceeds_requirement".

    Raises ValueError for a negative computed rate or a non-positive margin.
    """
    if computed_rate_per_day < 0:
        raise ValueError(
            "computed_rate_per_day must be >= 0, got %r" % computed_rate_per_day
        )
    if design_margin_factor <= 0:
        raise ValueError(
            "design_margin_factor must be > 0, got %r" % design_margin_factor
        )

    if allowable_rate_per_day is None:
        if computed_rate_per_day > 0:
            return {
                "compliant": False,
                "issue": "missing_sehe_rate_requirement",
                "computed_rate_per_day": computed_rate_per_day,
                "allowable_rate_per_day": None,
                "design_margin_factor": design_margin_factor,
            }
        return {
            "compliant": True,
            "issue": None,
            "computed_rate_per_day": computed_rate_per_day,
            "allowable_rate_per_day": None,
            "design_margin_factor": design_margin_factor,
        }

    if allowable_rate_per_day < 0:
        raise ValueError(
            "allowable_rate_per_day must be >= 0, got %r" % allowable_rate_per_day
        )

    if computed_rate_per_day > allowable_rate_per_day:
        return {
            "compliant": False,
            "issue": "sehe_rate_exceeds_requirement",
            "computed_rate_per_day": computed_rate_per_day,
            "allowable_rate_per_day": allowable_rate_per_day,
            "design_margin_factor": design_margin_factor,
        }

    if computed_rate_per_day * design_margin_factor > allowable_rate_per_day:
        return {
            "compliant": False,
            "issue": "sehe_margin_not_met",
            "computed_rate_per_day": computed_rate_per_day,
            "allowable_rate_per_day": allowable_rate_per_day,
            "design_margin_factor": design_margin_factor,
        }

    return {
        "compliant": True,
        "issue": None,
        "computed_rate_per_day": computed_rate_per_day,
        "allowable_rate_per_day": allowable_rate_per_day,
        "design_margin_factor": design_margin_factor,
    }


def sehe_assessment(device):
    """Full SEHE rate assessment for one device under ECSS-E-ST-10-12C §9.4.1.8.

    device: {
        "device_id": str,
        "sigma_sat_cm2": float,             -- Weibull saturation cross-section
        "let_threshold_mev_cm2_mg": float,  -- Weibull LET threshold
        "weibull_width": float,             -- Weibull width parameter W
        "weibull_exponent": float,          -- Weibull shape exponent s
        "let_flux_pairs": list of (let, flux) tuples,
        "shielding_factor": float,          -- 1.0 = no shielding
        "allowable_rate_per_day": float | None,
        "design_margin_factor": float,      -- default 10.0
    }

    Returns {
        "device_id": str,
        "unshielded_rate_per_day": float,
        "shielded_rate_per_day": float,
        "rate_check": dict from check_sehe_rate,
    }. Does not mutate the device dict.
    """
    unshielded = integrate_sehe_rate(
        device["sigma_sat_cm2"],
        device["let_threshold_mev_cm2_mg"],
        device["weibull_width"],
        device["weibull_exponent"],
        device["let_flux_pairs"],
    )
    shielded = apply_shielding_reduction(unshielded, device["shielding_factor"])
    rate_check = check_sehe_rate(
        shielded,
        device.get("allowable_rate_per_day"),
        device.get("design_margin_factor", 10.0),
    )
    return {
        "device_id": device["device_id"],
        "unshielded_rate_per_day": unshielded,
        "shielded_rate_per_day": shielded,
        "rate_check": rate_check,
    }


def is_sehe_compliant(assessment):
    """True when the SEHE rate check in an assessment result is compliant."""
    return assessment["rate_check"]["compliant"]
