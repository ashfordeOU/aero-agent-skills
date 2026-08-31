#!/usr/bin/env python3
"""Multi-stage axial compressor design and matching logic.

Design relations for a multi-stage axial compressor (SI units
throughout, stdlib only):

- overall_pressure_ratio(stage_pressure_ratios): product of the stage
  pressure ratios, dimensionless.
- stage_count(total_pressure_ratio, stage_pressure_ratio):
  ceil(ln(PR_total) / ln(PR_stage)), the number of identical design
  stages needed to reach the target overall pressure ratio.
- reheat_factor(actual_work, ideal_work_sum): W_actual / W_ideal_sum.
  The actual total work exceeds the sum of the ideal (isentropic)
  stage works because each stage re-compresses flow that was reheated
  by the losses of the previous stage; the factor is >= 1.0 and grows
  with the stage count (typical 1.01 to 1.06).
- annulus_area(mass_flow, axial_velocity, density):
  A = m_dot / (rho * V_ax) in m^2. Density rises through the
  compressor, so the annulus area shrinks toward the rear for a
  constant axial velocity.
- stage_work_distribution(total_work, n_stages, scheme): the stage
  work split. Equal scheme: w_k = W_total / n for every stage. Rising
  scheme: w_k = W_total * 2*k / (n*(n+1)) for k = 1..n (1-indexed),
  a linearly increasing loading that puts about twice the first-stage
  work on the last stage, matching the rising back-pressure along the
  flow path.
- corrected_speed(physical_speed, t_ref, t):
  N_corr = N * sqrt(t_ref / t) in rpm, the rotor speed referred to the
  reference temperature (standard day t_ref = 288.15 K) for
  off-design matching on a compressor map.

FAR-33 is referenced, not reproduced; the matching relations are
common turbomachinery methodology summarized per standards-map.yaml.

Functions raise ValueError on non-physical inputs (pressure ratios
<= 1, non-positive flows, speeds, temperatures, densities, work
values, or a reheat factor below 1) instead of returning nonsense or
dividing by zero.
"""

import math


def overall_pressure_ratio(stage_pressure_ratios):
    """Product of the stage pressure ratios, dimensionless.

    Each stage pressure ratio must be > 1.0 (a compressing stage); the
    list must be non-empty. Returns the overall pressure ratio.
    """
    if not stage_pressure_ratios:
        raise ValueError("stage_pressure_ratios must be non-empty")
    pr = 1.0
    for pi in stage_pressure_ratios:
        if pi <= 1.0:
            raise ValueError("each stage pressure ratio must be > 1, got %r" % (pi,))
        pr *= pi
    return pr


def stage_count(total_pressure_ratio, stage_pressure_ratio):
    """Number of identical stages: ceil(ln(PR_total) / ln(PR_stage)).

    Both pressure ratios must be > 1.0. The result is >= 1: a target
    already met by one stage returns 1, never 0.
    """
    if total_pressure_ratio <= 1.0:
        raise ValueError(
            "total_pressure_ratio must be > 1, got %r" % (total_pressure_ratio,)
        )
    if stage_pressure_ratio <= 1.0:
        raise ValueError(
            "stage_pressure_ratio must be > 1, got %r" % (stage_pressure_ratio,)
        )
    # The log ratio is mathematically exact at integer boundaries (for
    # example 1.44 with 1.2 per stage); floating point lands a hair
    # above the integer, so shave 1e-9 before the ceiling to keep the
    # count at the true value instead of rounding one stage too high.
    ratio = math.log(total_pressure_ratio) / math.log(stage_pressure_ratio)
    return math.ceil(ratio - 1e-9)


def reheat_factor(actual_work, ideal_work_sum):
    """Reheat factor = W_actual / W_ideal_sum, dimensionless, >= 1.0.

    actual_work is the total shaft work absorbed by all stages in J/kg
    (or J); ideal_work_sum is the sum of the ideal (isentropic) stage
    works. The factor is physically >= 1.0 because each stage
    re-compresses the reheat losses of the previous stage; a value
    below 1.0 signals a data error and raises ValueError.
    """
    if actual_work <= 0:
        raise ValueError("actual_work must be > 0, got %r" % (actual_work,))
    if ideal_work_sum <= 0:
        raise ValueError("ideal_work_sum must be > 0, got %r" % (ideal_work_sum,))
    if actual_work < ideal_work_sum:
        raise ValueError(
            "actual_work %r below ideal_work_sum %r: reheat factor < 1 "
            "is non-physical" % (actual_work, ideal_work_sum)
        )
    return actual_work / ideal_work_sum


def annulus_area(mass_flow, axial_velocity, density):
    """Annulus flow area A = m_dot / (rho * V_ax) in m^2.

    mass_flow in kg/s, axial_velocity in m/s, density in kg/m^3. All
    inputs must be > 0.
    """
    if mass_flow <= 0:
        raise ValueError("mass_flow must be > 0, got %r" % (mass_flow,))
    if axial_velocity <= 0:
        raise ValueError("axial_velocity must be > 0, got %r" % (axial_velocity,))
    if density <= 0:
        raise ValueError("density must be > 0, got %r" % (density,))
    return mass_flow / (density * axial_velocity)


def stage_work_distribution(total_work, n_stages, scheme):
    """Stage work split as a list of n_stages work values summing to total_work.

    scheme 'equal': w_k = total_work / n_stages for every stage.
    scheme 'rising': w_k = total_work * 2*k / (n_stages*(n_stages+1))
    for k = 1..n_stages (1-indexed), a linear ramp that loads the rear
    stages about twice the first stage. total_work in J/kg (or J),
    n_stages an int >= 1, scheme one of the two names.
    """
    if total_work <= 0:
        raise ValueError("total_work must be > 0, got %r" % (total_work,))
    if not isinstance(n_stages, int) or n_stages < 1:
        raise ValueError("n_stages must be an int >= 1, got %r" % (n_stages,))
    if scheme == "equal":
        w = total_work / n_stages
        return [w] * n_stages
    if scheme == "rising":
        denom = n_stages * (n_stages + 1)
        return [
            total_work * 2.0 * k / denom for k in range(1, n_stages + 1)
        ]
    raise ValueError("scheme must be 'equal' or 'rising', got %r" % (scheme,))


def corrected_speed(physical_speed, t_ref, t):
    """Corrected rotor speed N_corr = N * sqrt(t_ref / t) in rpm.

    physical_speed in rpm, t_ref and t in K. At t == t_ref the
    corrected speed equals the physical speed. All inputs must be > 0.
    """
    if physical_speed <= 0:
        raise ValueError(
            "physical_speed must be > 0, got %r" % (physical_speed,)
        )
    if t_ref <= 0:
        raise ValueError("t_ref must be > 0, got %r" % (t_ref,))
    if t <= 0:
        raise ValueError("t must be > 0, got %r" % (t,))
    return physical_speed * math.sqrt(t_ref / t)
