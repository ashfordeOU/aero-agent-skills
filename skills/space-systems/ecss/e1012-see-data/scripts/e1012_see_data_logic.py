#!/usr/bin/env python3
"""ECSS-E-ST-10C §9.4.2 — SEE experimental data: Weibull cross-section
fits and in-orbit rate prediction (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
accelerator tests yield measured single-event-effect cross-sections
(cm² per device or per bit) at discrete ion LET values (MeV·cm²/mg).
These points are parameterised with a four-parameter Weibull sigmoid:
saturation cross-section σ_sat, threshold LET L₀, width W, and shape
exponent s. The in-orbit SEE rate is the integral of the fitted
cross-section against the mission differential LET spectrum, evaluated
numerically using the trapezoidal rule. The predicted rate is then
compared against the component hardness limit to give a compliance
verdict. This module implements Weibull parameter validation,
cross-section evaluation, LET spectrum integration, and hardness-limit
comparison; it does not define the LET spectrum itself or the Weibull
fitting procedure.
"""

import math

WEIBULL_PARAM_KEYS = frozenset(
    {"sigma_sat_cm2", "let_threshold_mev_cm2_mg", "width_mev_cm2_mg", "shape_exponent"}
)


def validate_weibull_params(params):
    """Check the four Weibull parameters satisfy physical constraints.

    Raises ValueError for any missing key or out-of-range value:
    sigma_sat_cm2 > 0, let_threshold_mev_cm2_mg >= 0,
    width_mev_cm2_mg > 0, shape_exponent > 0.
    """
    missing = WEIBULL_PARAM_KEYS - set(params)
    if missing:
        raise ValueError(
            "missing Weibull parameter(s): %s" % sorted(missing)
        )
    if params["sigma_sat_cm2"] <= 0:
        raise ValueError("sigma_sat_cm2 must be > 0")
    if params["let_threshold_mev_cm2_mg"] < 0:
        raise ValueError("let_threshold_mev_cm2_mg must be >= 0")
    if params["width_mev_cm2_mg"] <= 0:
        raise ValueError("width_mev_cm2_mg must be > 0")
    if params["shape_exponent"] <= 0:
        raise ValueError("shape_exponent must be > 0")


def weibull_cross_section(let_mev_cm2_mg, params):
    """Weibull SEE cross-section (cm²) at a given LET (MeV·cm²/mg).

    Returns 0.0 for LET at or below the threshold. Raises ValueError
    for a negative LET or an invalid parameter set.
    """
    if let_mev_cm2_mg < 0:
        raise ValueError("let_mev_cm2_mg must be >= 0")
    validate_weibull_params(params)
    l0 = params["let_threshold_mev_cm2_mg"]
    if let_mev_cm2_mg <= l0:
        return 0.0
    sigma_sat = params["sigma_sat_cm2"]
    w = params["width_mev_cm2_mg"]
    s = params["shape_exponent"]
    ratio = (let_mev_cm2_mg - l0) / w
    return sigma_sat * (1.0 - math.exp(-(ratio ** s)))


def integrate_see_rate(weibull_params, let_spectrum):
    """Predicted in-orbit SEE rate (events/s) from a Weibull-fitted
    cross-section and a discrete differential LET spectrum.

    let_spectrum: list of (let_mev_cm2_mg, flux_cm2_s_per_let_unit) tuples
    sorted in strictly ascending LET order. The flux value is the
    differential LET spectrum (events per cm² per second per unit LET).

    Uses the trapezoidal rule. Raises ValueError for an invalid parameter
    set, an empty spectrum, a single-point spectrum (no integrable
    interval), or a spectrum not in strictly ascending LET order.
    Does not mutate let_spectrum.
    """
    validate_weibull_params(weibull_params)
    if not let_spectrum:
        raise ValueError("let_spectrum must not be empty")
    if len(let_spectrum) < 2:
        raise ValueError(
            "let_spectrum must contain at least two points to integrate"
        )
    lets = [pair[0] for pair in let_spectrum]
    for i in range(len(lets) - 1):
        if lets[i] >= lets[i + 1]:
            raise ValueError(
                "let_spectrum must be sorted in strictly ascending LET order; "
                "found %.6g >= %.6g at positions %d and %d"
                % (lets[i], lets[i + 1], i, i + 1)
            )
    integrand = [
        weibull_cross_section(let, weibull_params) * flux
        for let, flux in let_spectrum
    ]
    rate = 0.0
    for i in range(len(let_spectrum) - 1):
        d_let = let_spectrum[i + 1][0] - let_spectrum[i][0]
        rate += 0.5 * (integrand[i] + integrand[i + 1]) * d_let
    return rate


def check_see_rate_against_limit(see_rate, rate_limit_events_per_s):
    """Compare a predicted SEE rate against a component hardness limit.

    see_rate: predicted rate (events/s), must be >= 0.
    rate_limit_events_per_s: allowable rate (events/s), must be > 0.

    Returns a dict:
      "compliant": True when see_rate <= rate_limit_events_per_s.
      "margin": rate_limit_events_per_s / see_rate, or None when see_rate is 0.

    Raises ValueError for a negative see_rate or a non-positive limit.
    """
    if see_rate < 0:
        raise ValueError("see_rate must be >= 0")
    if rate_limit_events_per_s <= 0:
        raise ValueError("rate_limit_events_per_s must be > 0")
    if see_rate == 0.0:
        return {"compliant": True, "margin": None}
    margin = rate_limit_events_per_s / see_rate
    return {
        "compliant": see_rate <= rate_limit_events_per_s,
        "margin": margin,
    }
