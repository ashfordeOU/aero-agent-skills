#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 10.2.6 debris/meteoroid margin policy logic
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
debris/meteoroid flux prediction and the damage (penetration) prediction
built on it must both carry a margin before being used to demonstrate
compliance with a mission's probability-of-no-penetration (PNP)
requirement -- a flux margin factor scales up the predicted
expected-impact rate, and a diameter margin factor derates the
ballistic-limit critical diameter so smaller particles are
conservatively counted as damaging. This module implements the margin
application and the Poisson-model PNP derivation from a margined
impact rate; it does not implement flux model selection (see the
sibling e1004-debris / e1004-meteoroid leaves) or the ballistic-limit
critical-diameter calculation itself (see e1004-impact-risk).
"""

import math

MIN_FLUX_MARGIN_FACTOR = 1.0
MAX_DIAMETER_MARGIN_FACTOR = 1.0


def apply_flux_margin(baseline_expected_impacts, flux_margin_factor):
    """Scale a baseline expected-impact rate by a flux margin factor.
    baseline_expected_impacts must be >= 0; flux_margin_factor must be
    >= 1.0 (a margin must not relax the prediction). Raises ValueError
    otherwise."""
    if baseline_expected_impacts < 0:
        raise ValueError(
            "baseline expected impacts must be non-negative: %r" % (baseline_expected_impacts,)
        )
    if flux_margin_factor < MIN_FLUX_MARGIN_FACTOR:
        raise ValueError(
            "flux margin factor must be >= %r: %r" % (MIN_FLUX_MARGIN_FACTOR, flux_margin_factor)
        )
    return baseline_expected_impacts * flux_margin_factor


def apply_diameter_margin(baseline_critical_diameter, diameter_margin_factor):
    """Derate a baseline critical (ballistic-limit) diameter by a
    diameter margin factor. baseline_critical_diameter must be > 0;
    diameter_margin_factor must be in (0, 1.0] (a margin must shrink or
    hold the diameter, never grow it). Raises ValueError otherwise."""
    if baseline_critical_diameter <= 0:
        raise ValueError(
            "baseline critical diameter must be positive: %r" % (baseline_critical_diameter,)
        )
    if not (0 < diameter_margin_factor <= MAX_DIAMETER_MARGIN_FACTOR):
        raise ValueError(
            "diameter margin factor must be in (0, %r]: %r"
            % (MAX_DIAMETER_MARGIN_FACTOR, diameter_margin_factor)
        )
    return baseline_critical_diameter * diameter_margin_factor


def expected_impacts_for_margined_diameter(
    flux_margined_expected_impacts,
    baseline_critical_diameter,
    margined_critical_diameter,
    power_law_exponent,
):
    """Rescale a flux-margined expected-impact rate from the baseline
    critical diameter to a (smaller or equal) margined critical
    diameter, using the local cumulative-flux power-law exponent
    (flux ~ diameter^-power_law_exponent). Requires
    0 < margined_critical_diameter <= baseline_critical_diameter and
    power_law_exponent > 0; raises ValueError otherwise."""
    if flux_margined_expected_impacts < 0:
        raise ValueError(
            "flux-margined expected impacts must be non-negative: %r"
            % (flux_margined_expected_impacts,)
        )
    if baseline_critical_diameter <= 0:
        raise ValueError(
            "baseline critical diameter must be positive: %r" % (baseline_critical_diameter,)
        )
    if not (0 < margined_critical_diameter <= baseline_critical_diameter):
        raise ValueError(
            "margined critical diameter must be in (0, baseline]: %r (baseline %r)"
            % (margined_critical_diameter, baseline_critical_diameter)
        )
    if power_law_exponent <= 0:
        raise ValueError("power law exponent must be positive: %r" % (power_law_exponent,))
    ratio = (baseline_critical_diameter / margined_critical_diameter) ** power_law_exponent
    return flux_margined_expected_impacts * ratio


def probability_of_no_penetration(expected_impacts):
    """Poisson no-impact-in-service probability for an expected-impact
    rate. expected_impacts must be >= 0; raises ValueError otherwise."""
    if expected_impacts < 0:
        raise ValueError("expected impacts must be non-negative: %r" % (expected_impacts,))
    return math.exp(-expected_impacts)


def build_margined_damage_prediction(
    baseline_expected_impacts,
    baseline_critical_diameter,
    flux_margin_factor,
    diameter_margin_factor,
    power_law_exponent,
):
    """Full clause 10.2.6 margin application: flux-margin the baseline
    expected-impact rate, diameter-margin the baseline critical
    diameter, rescale the flux-margined rate onto the margined
    diameter, and derive both the baseline and margined PNP. Returns a
    new dict; raises ValueError via the underlying calls for any input
    outside its valid range."""
    margined_expected_impacts_from_flux = apply_flux_margin(
        baseline_expected_impacts, flux_margin_factor
    )
    margined_critical_diameter = apply_diameter_margin(
        baseline_critical_diameter, diameter_margin_factor
    )
    margined_expected_impacts = expected_impacts_for_margined_diameter(
        margined_expected_impacts_from_flux,
        baseline_critical_diameter,
        margined_critical_diameter,
        power_law_exponent,
    )
    return {
        "baseline_expected_impacts": baseline_expected_impacts,
        "baseline_critical_diameter": baseline_critical_diameter,
        "baseline_pnp": probability_of_no_penetration(baseline_expected_impacts),
        "flux_margin_factor": flux_margin_factor,
        "diameter_margin_factor": diameter_margin_factor,
        "power_law_exponent": power_law_exponent,
        "margined_critical_diameter": margined_critical_diameter,
        "margined_expected_impacts": margined_expected_impacts,
        "margined_pnp": probability_of_no_penetration(margined_expected_impacts),
    }


def meets_pnp_requirement(margined_pnp, required_pnp):
    """True if a margined PNP meets or exceeds the mission's PNP
    requirement."""
    return margined_pnp >= required_pnp


def margin_factors_are_conservative(
    flux_margin_factor,
    diameter_margin_factor,
    min_flux_margin_factor,
    max_diameter_margin_factor,
):
    """True if the flux margin factor used is not weaker than the
    project's minimum required flux margin, and the diameter margin
    factor used is not weaker (i.e. not larger) than the project's
    maximum allowed diameter margin."""
    return (
        flux_margin_factor >= min_flux_margin_factor
        and diameter_margin_factor <= max_diameter_margin_factor
    )
