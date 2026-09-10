#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 10.2.5 -- meteoroid/debris impact risk
assessment (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): once
a cumulative damaging flux (impacts/m^2/year of particles at or above
the ballistic-limit critical diameter) is available for each
contributing population, the impact-risk assessment combines those
fluxes with the exposed area and mission duration into an expected
impact count, then applies Poisson zero-hit statistics (the Annex J
method) to get a probability of no penetration (PNP) and its
complement, the probability of damage. That probability is checked
against the mission's PNP acceptance requirement. This module does not
select or evaluate the flux models themselves (that is the sibling
e1004-debris and e1004-meteoroid leaves) and does not apply design
margins to the flux or the result (that is the sibling e1004-mm-margins
leaf); it only runs the flux-to-probability assessment and the
system-level combination of element results.
"""

import math


def combine_cumulative_fluxes(fluxes):
    """Total damaging cumulative flux (impacts/m^2/year) from an
    iterable of non-negative per-population fluxes (e.g. debris,
    meteoroid background, meteoroid streams) evaluated at the same
    critical diameter. Independent particle populations sum linearly.
    Raises ValueError if fluxes is empty or any value is negative."""
    flux_list = list(fluxes)
    if not flux_list:
        raise ValueError("fluxes must be a non-empty iterable")
    for flux in flux_list:
        if flux < 0:
            raise ValueError("flux must be non-negative: %r" % (flux,))
    return sum(flux_list)


def expected_impact_count(total_flux, exposed_area_m2, duration_years):
    """Expected number of damaging impacts N = total_flux * area *
    duration, the Poisson rate parameter for the Annex J method.
    total_flux must be non-negative; exposed_area_m2 and duration_years
    must be positive. Raises ValueError otherwise."""
    if total_flux < 0:
        raise ValueError("total_flux must be non-negative: %r" % (total_flux,))
    if exposed_area_m2 <= 0:
        raise ValueError("exposed_area_m2 must be positive: %r" % (exposed_area_m2,))
    if duration_years <= 0:
        raise ValueError("duration_years must be positive: %r" % (duration_years,))
    return total_flux * exposed_area_m2 * duration_years


def probability_no_penetration(expected_impacts):
    """Probability of no penetration (PNP), Po = exp(-N), the Poisson
    zero-hit probability per Annex J. expected_impacts (N) must be
    non-negative. Raises ValueError otherwise."""
    if expected_impacts < 0:
        raise ValueError("expected_impacts must be non-negative: %r" % (expected_impacts,))
    return math.exp(-expected_impacts)


def probability_of_damage(expected_impacts):
    """Probability of one or more damaging impacts, Pd = 1 - Po. Raises
    ValueError if expected_impacts is negative (delegates to
    probability_no_penetration for the check)."""
    return 1.0 - probability_no_penetration(expected_impacts)


def assess_impact_risk(component_fluxes, exposed_area_m2, duration_years, pnp_requirement):
    """Run the full flux-to-probability assessment for one element.
    component_fluxes is a name -> cumulative-flux mapping (e.g.
    {'debris': ..., 'meteoroid_background': ..., 'meteoroid_stream':
    ...}), all evaluated at the same critical diameter. pnp_requirement
    is the mission's minimum acceptable probability of no penetration
    (0 < pnp_requirement <= 1). Returns a dict with the per-component
    and total expected impacts, Po, Pd, and whether the element meets
    its PNP requirement (with the shortfall when it does not). Raises
    ValueError if component_fluxes is empty or pnp_requirement is out
    of (0, 1]."""
    if not component_fluxes:
        raise ValueError("component_fluxes must be a non-empty mapping")
    if not (0 < pnp_requirement <= 1):
        raise ValueError("pnp_requirement must be in (0, 1]: %r" % (pnp_requirement,))
    per_component_impacts = {
        name: expected_impact_count(flux, exposed_area_m2, duration_years)
        for name, flux in component_fluxes.items()
    }
    total_flux = combine_cumulative_fluxes(component_fluxes.values())
    total_impacts = expected_impact_count(total_flux, exposed_area_m2, duration_years)
    pnp = probability_no_penetration(total_impacts)
    pd = probability_of_damage(total_impacts)
    meets_requirement = pnp >= pnp_requirement
    return {
        "per_component_impacts": per_component_impacts,
        "total_expected_impacts": total_impacts,
        "probability_no_penetration": pnp,
        "probability_of_damage": pd,
        "pnp_requirement": pnp_requirement,
        "meets_requirement": meets_requirement,
        "shortfall": 0.0 if meets_requirement else pnp_requirement - pnp,
    }


def combine_system_pnp(element_pnps):
    """System-level probability of no penetration from an iterable of
    independently-assessed element PNPs (e.g. separate spacecraft
    panels or subsystems), combined multiplicatively under the
    independence assumption used by the Annex J method. Raises
    ValueError if element_pnps is empty or any value is out of
    (0, 1]."""
    pnp_list = list(element_pnps)
    if not pnp_list:
        raise ValueError("element_pnps must be a non-empty iterable")
    for pnp in pnp_list:
        if not (0 < pnp <= 1):
            raise ValueError("each element PNP must be in (0, 1]: %r" % (pnp,))
    system_pnp = 1.0
    for pnp in pnp_list:
        system_pnp *= pnp
    return system_pnp
