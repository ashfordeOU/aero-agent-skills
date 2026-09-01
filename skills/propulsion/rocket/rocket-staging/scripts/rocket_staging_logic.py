#!/usr/bin/env python3
"""Rocket staging logic: per-stage ideal delta-v, mass ratio and payload
fraction allocation, structural index, and stage optimization for a
target total delta-v (common propulsion methodology).

Common-knowledge summary (standards-map.yaml, ecss: free ESA download,
reference-only): ECSS space-systems standards frame launch-vehicle
engineering context. The rocket equation and the equal-mass-ratio
optimum split of identical stages are standard propulsion methodology.

Worked anchors (all verified by running this module):
- delta-v = g0 * Isp * ln(m0 / mf): Isp = 300 s, m0/mf = 2 gives
  delta-v = 9.80665 * 300 * ln(2) = 2039.24 m/s.
- mass ratio from a delta-v: exp(2039.24 / (9.80665 * 300)) = 2.0.
- structural index eps = 0.1 and payload fraction lam = 0.05 give stage
  mass ratio r = 1 / (lam + eps * (1 - lam)) = 6.8966.
- optimal two-stage split for 9000 m/s at Isp = 300 s, eps = 0.1 gives
  per-stage ratio r* = 4.6162 and total payload fraction 0.01679.
"""

import math


def stage_delta_v(isp_s, m0_kg, mf_kg, g0=9.80665):
    """Ideal delta-v of one stage from the rocket equation, g0 * Isp * ln(m0/mf).

    Worked anchor: stage_delta_v(300, 100000, 50000) = 2039.24 m/s
    (m0/mf = 2).

    Raises ValueError when Isp is not positive, when the initial or
    final mass is not positive, or when the final mass is not below
    the initial mass.
    """
    if isp_s <= 0:
        raise ValueError("specific impulse must be > 0, got %r" % (isp_s,))
    if m0_kg <= 0:
        raise ValueError("initial mass must be > 0, got %r" % (m0_kg,))
    if mf_kg <= 0:
        raise ValueError("final mass must be > 0, got %r" % (mf_kg,))
    if mf_kg >= m0_kg:
        raise ValueError(
            "final mass must be < initial mass, got %r >= %r" % (mf_kg, m0_kg)
        )
    return g0 * isp_s * math.log(m0_kg / mf_kg)


def mass_ratio_from_delta_v(delta_v, isp_s, g0=9.80665):
    """Stage mass ratio m0/mf required for a stage delta-v at a given Isp.

    Worked anchor: mass_ratio_from_delta_v(2039.24, 300) = 2.0.

    Raises ValueError for a negative delta-v or a non-positive Isp.
    """
    if delta_v < 0:
        raise ValueError("delta-v must be >= 0, got %r" % (delta_v,))
    if isp_s <= 0:
        raise ValueError("specific impulse must be > 0, got %r" % (isp_s,))
    return math.exp(delta_v / (g0 * isp_s))


def payload_fraction(payload_kg, m0_kg):
    """Payload fraction of a stage, payload mass over initial stage mass.

    Worked anchor: payload_fraction(5000, 100000) = 0.05.

    Raises ValueError when the payload or the initial mass is not
    positive, or when the payload is not below the initial mass.
    """
    if payload_kg <= 0:
        raise ValueError("payload mass must be > 0, got %r" % (payload_kg,))
    if m0_kg <= 0:
        raise ValueError("initial mass must be > 0, got %r" % (m0_kg,))
    if payload_kg >= m0_kg:
        raise ValueError(
            "payload must be < initial mass, got %r >= %r" % (payload_kg, m0_kg)
        )
    return payload_kg / m0_kg


def structural_index(structure_kg, propellant_kg):
    """Structural index of a stage, structure over structure plus propellant.

    Worked anchor: structural_index(10000, 90000) = 0.1.

    Raises ValueError when the structure or the propellant mass is not
    positive.
    """
    if structure_kg <= 0:
        raise ValueError("structure mass must be > 0, got %r" % (structure_kg,))
    if propellant_kg <= 0:
        raise ValueError("propellant mass must be > 0, got %r" % (propellant_kg,))
    return structure_kg / (structure_kg + propellant_kg)


def mass_ratio_from_indices(eps, lam):
    """Stage mass ratio from the structural index and the payload fraction.

    Burnout mass is payload plus structure: mf = (lam + eps * (1 - lam))
    * m0, so r = m0 / mf = 1 / (lam + eps * (1 - lam)).

    Worked anchor: mass_ratio_from_indices(0.1, 0.05) = 6.8966.

    Raises ValueError when eps or lam is not in the open interval (0, 1),
    or when the combination gives a non-positive burnout fraction.
    """
    if not 0 < eps < 1:
        raise ValueError("structural index must be in (0, 1), got %r" % (eps,))
    if not 0 < lam < 1:
        raise ValueError("payload fraction must be in (0, 1), got %r" % (lam,))
    burnout_frac = lam + eps * (1 - lam)
    if burnout_frac <= 0:
        raise ValueError(
            "payload fraction %r and structural index %r leave no burnout mass"
            % (lam, eps)
        )
    return 1.0 / burnout_frac


def payload_fraction_from_mass_ratio(eps, r):
    """Payload fraction implied by a stage mass ratio and structural index.

    Inverse of mass_ratio_from_indices: lam = (1 / r - eps) / (1 - eps).

    Worked anchor: payload_fraction_from_mass_ratio(0.1, 6.8966) = 0.05.

    Raises ValueError when eps is not in (0, 1), when the mass ratio is
    not above 1, or when the implied payload fraction is not positive
    (the stage cannot deliver the ratio with that structural index).
    """
    if not 0 < eps < 1:
        raise ValueError("structural index must be in (0, 1), got %r" % (eps,))
    if r <= 1:
        raise ValueError("mass ratio must be > 1, got %r" % (r,))
    lam = (1.0 / r - eps) / (1.0 - eps)
    if lam <= 0:
        raise ValueError(
            "mass ratio %r is unreachable at structural index %r" % (r, eps)
        )
    return lam


def stage_delta_v_from_indices(isp_s, eps, lam, g0=9.80665):
    """Ideal delta-v of one stage from Isp, structural index, and payload
    fraction: g0 * Isp * ln(1 / (lam + eps * (1 - lam))).

    Worked anchor: stage_delta_v_from_indices(300, 0.1, 0.05) =
    5681.06 m/s (mass ratio 6.8966).

    Raises ValueError when Isp is not positive or when eps or lam is not
    in (0, 1).
    """
    if isp_s <= 0:
        raise ValueError("specific impulse must be > 0, got %r" % (isp_s,))
    r = mass_ratio_from_indices(eps, lam)
    return g0 * isp_s * math.log(r)


def optimal_equal_stage_split(total_delta_v, n_stages, isp_s, eps, g0=9.80665):
    """Optimal split of identical stages for a target total delta-v.

    For n equal stages with equal structural index and Isp, the
    per-stage mass ratio that maximizes the payload fraction is the
    equal ratio r* = exp(total_delta_v / (n * g0 * Isp)); every stage
    then has the same payload fraction lam = (1 / r* - eps) / (1 - eps)
    and the total payload fraction is lam ** n.

    Returns (r_star, lam_stage, lam_total).

    Worked anchor: optimal_equal_stage_split(9000, 2, 300, 0.1) =
    (4.6162, 0.12959, 0.01679).

    Raises ValueError for a negative total delta-v, fewer than one
    stage, a non-positive Isp, an eps outside (0, 1), or a split that
    implies a non-positive stage payload fraction (the target is
    unreachable with that structural index).
    """
    if total_delta_v <= 0:
        raise ValueError("total delta-v must be > 0, got %r" % (total_delta_v,))
    if n_stages < 1:
        raise ValueError("stage count must be >= 1, got %r" % (n_stages,))
    if isp_s <= 0:
        raise ValueError("specific impulse must be > 0, got %r" % (isp_s,))
    if not 0 < eps < 1:
        raise ValueError("structural index must be in (0, 1), got %r" % (eps,))
    r_star = math.exp(total_delta_v / (n_stages * g0 * isp_s))
    lam_stage = payload_fraction_from_mass_ratio(eps, r_star)
    return r_star, lam_stage, lam_stage ** n_stages


def stage_count_for_delta_v(total_delta_v, isp_s, eps, target_payload_fraction,
                            g0=9.80665):
    """Minimum number of identical stages that deliver the total delta-v
    with at least the target total payload fraction.

    Returns (n_stages, lam_total_achieved). The achievable total payload
    fraction is bounded above by the asymptotic limit
    exp(-total_delta_v / (g0 * Isp * (1 - eps))) as the stage count
    grows; a target above that limit is infeasible and raises
    ValueError.

    Worked anchor: stage_count_for_delta_v(9000, 300, 0.1, 0.02) = (3, 0.0243)
    (two stages give only 0.01679).

    Raises ValueError for invalid delta-v, Isp, eps, or target, and for
    an unreachable target payload fraction.
    """
    if total_delta_v <= 0:
        raise ValueError("total delta-v must be > 0, got %r" % (total_delta_v,))
    if isp_s <= 0:
        raise ValueError("specific impulse must be > 0, got %r" % (isp_s,))
    if not 0 < eps < 1:
        raise ValueError("structural index must be in (0, 1), got %r" % (eps,))
    if not 0 < target_payload_fraction < 1:
        raise ValueError(
            "target payload fraction must be in (0, 1), got %r"
            % (target_payload_fraction,)
        )
    limit = math.exp(-total_delta_v / (g0 * isp_s * (1.0 - eps)))
    if target_payload_fraction > limit:
        raise ValueError(
            "target payload fraction %r exceeds the asymptotic staging "
            "limit %r at Isp %r and structural index %r"
            % (target_payload_fraction, limit, isp_s, eps)
        )
    n = 1
    while True:
        try:
            r_star, lam_stage, lam_total = optimal_equal_stage_split(
                total_delta_v, n, isp_s, eps, g0
            )
        except ValueError:
            # The stage ratio for this stage count is unreachable at the
            # structural index (payload fraction would be negative); try
            # the next stage count.
            n += 1
            continue
        if lam_total >= target_payload_fraction:
            return n, lam_total
        n += 1


def total_staged_delta_v(stage_delta_vs):
    """Total delta-v across the stages of a multistage vehicle.

    Worked anchor: total_staged_delta_v([2000.0, 1500.0]) = 3500.0.

    Raises ValueError for an empty stage list or a negative stage
    delta-v.
    """
    if not stage_delta_vs:
        raise ValueError("stage delta-v list must not be empty")
    total = 0.0
    for dv in stage_delta_vs:
        if dv < 0:
            raise ValueError("stage delta-v must be >= 0, got %r" % (dv,))
        total += dv
    return total
