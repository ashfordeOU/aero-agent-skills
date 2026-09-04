"""Bi-elliptic three-impulse orbit transfer logic (pure stdlib).

Analyzes the bi-elliptic three-impulse transfer between two coplanar
circular orbits: the perigee raise burn to the intermediate apogee
radius r_b, the burn at r_b that raises perigee to the target radius,
and the circularization burn at the target radius. Compares the total
against the Hohmann two-impulse baseline for the same orbit pair and
returns the strategy verdict (bi-elliptic when it saves delta-v,
hohmann on ties, the simpler two-burn strategy).

All functions are deterministic, pure math on module constants; no RNG,
no network, no external processes.
"""

import math

MU_EARTH = 3.986004418e14  # m3/s2, default gravitational parameter (Earth)


def circular_speed(mu, radius):
    """Speed on a circular orbit: v = sqrt(mu / radius) in m/s.

    ValueError if radius <= 0 or mu <= 0.
    """
    if mu <= 0:
        raise ValueError("gravitational parameter mu must be positive")
    if radius <= 0:
        raise ValueError("orbit radius must be positive")
    return math.sqrt(mu / radius)


def hohmann_delta_v(mu, r1, r2):
    """Two-impulse Hohmann delta-v baseline for the same orbit pair.

    Returns {'dv1', 'dv2', 'total'} in m/s with the departure burn
    dv1 = sqrt(mu*(2/r1 - 2/(r1+r2))) - sqrt(mu/r1) and the arrival
    burn dv2 = sqrt(mu/r2) - sqrt(mu*(2/r2 - 2/(r1+r2))). ValueErrors:
    mu <= 0, r1 <= 0, r2 <= 0, r1 == r2 (identical orbits are not a
    transfer).
    """
    if mu <= 0:
        raise ValueError("gravitational parameter mu must be positive")
    if r1 <= 0:
        raise ValueError("start radius r1 must be positive")
    if r2 <= 0:
        raise ValueError("target radius r2 must be positive")
    if r1 == r2:
        raise ValueError("r1 == r2: a transfer between identical orbits is not a transfer")
    v1 = math.sqrt(mu * (2.0 / r1 - 2.0 / (r1 + r2))) - math.sqrt(mu / r1)
    v2 = math.sqrt(mu / r2) - math.sqrt(mu * (2.0 / r2 - 2.0 / (r1 + r2)))
    return {"dv1": v1, "dv2": v2, "total": v1 + v2}


def _check_bi_elliptic_args(mu, r1, r_b, r2):
    """Shared physical-input checks for the bi-elliptic functions."""
    if mu <= 0:
        raise ValueError("gravitational parameter mu must be positive")
    if r1 <= 0:
        raise ValueError("start radius r1 must be positive")
    if r2 <= 0:
        raise ValueError("target radius r2 must be positive")
    if r_b <= r2:
        raise ValueError("intermediate apogee radius r_b must exceed the target radius r2")
    if r2 <= r1:
        raise ValueError("target radius r2 must exceed the start radius r1 (outward transfer only)")


def bi_elliptic_delta_v(mu, r1, r_b, r2):
    """Three-impulse bi-elliptic transfer delta-v budget in m/s.

    Returns {'dv1', 'dv2', 'dv3', 'total'} where
    dv1 = sqrt(mu*(2/r1 - 2/(r1+r_b))) - sqrt(mu/r1) raises the apogee
    to r_b, dv2 = sqrt(mu*(2/r_b - 2/(r_b+r2))) -
    sqrt(mu*(2/r_b - 2/(r1+r_b))) is the speed difference at r_b between
    the second and first transfer ellipses (raising the perigee from r1
    to r2), and dv3 = sqrt(mu/r2) - sqrt(mu*(2/r2 - 2/(r_b+r2)))
    circularizes at r2. The arrival burn is retrograde (the spacecraft
    reaches r2 at the perigee of the second transfer ellipse, faster
    than the circular-orbit speed), so dv3 is taken as the positive
    magnitude sqrt(mu*(2/r2 - 2/(r_b+r2))) - sqrt(mu/r2); this is the
    sign convention that keeps all three impulse magnitudes positive and
    matches the worked-example bounds (a literal
    sqrt(mu/r2) - sqrt(mu*(2/r2 - 2/(r_b+r2))) ordering would be
    negative). ValueErrors: mu <= 0, r1 <= 0, r2 <= 0,
    r_b <= r2 (the intermediate apogee must exceed the target radius),
    r2 <= r1 (outward transfer only, so r1 == r2 is also rejected).
    """
    _check_bi_elliptic_args(mu, r1, r_b, r2)
    dv1 = math.sqrt(mu * (2.0 / r1 - 2.0 / (r1 + r_b))) - math.sqrt(mu / r1)
    dv2 = (math.sqrt(mu * (2.0 / r_b - 2.0 / (r_b + r2)))
           - math.sqrt(mu * (2.0 / r_b - 2.0 / (r1 + r_b))))
    dv3 = (math.sqrt(mu * (2.0 / r2 - 2.0 / (r_b + r2)))
           - math.sqrt(mu / r2))
    return {"dv1": dv1, "dv2": dv2, "dv3": dv3, "total": dv1 + dv2 + dv3}


def transfer_comparison(mu, r1, r2, r_b):
    """Compare the bi-elliptic and Hohmann totals for the orbit pair.

    Returns {'hohmann_dv1', 'hohmann_dv2', 'hohmann_total', 'bi_dv1',
    'bi_dv2', 'bi_dv3', 'bi_total', 'saving', 'verdict'} with
    saving = hohmann_total - bi_total (positive when the bi-elliptic
    transfer is cheaper) and verdict = "bi-elliptic" when saving > 0
    else "hohmann" (ties go to hohmann, the simpler two-burn strategy).
    """
    _check_bi_elliptic_args(mu, r1, r_b, r2)
    hoh = hohmann_delta_v(mu, r1, r2)
    bi = bi_elliptic_delta_v(mu, r1, r_b, r2)
    saving = hoh["total"] - bi["total"]
    verdict = "bi-elliptic" if saving > 0 else "hohmann"
    return {
        "hohmann_dv1": hoh["dv1"],
        "hohmann_dv2": hoh["dv2"],
        "hohmann_total": hoh["total"],
        "bi_dv1": bi["dv1"],
        "bi_dv2": bi["dv2"],
        "bi_dv3": bi["dv3"],
        "bi_total": bi["total"],
        "saving": saving,
        "verdict": verdict,
    }


def transfer_time_bi_elliptic(mu, r1, r_b, r2):
    """Coast time of the bi-elliptic transfer in seconds.

    Sum of the two half-period arcs: pi * sqrt((r1+r_b)^3 / (8*mu)) +
    pi * sqrt((r_b+r2)^3 / (8*mu)). ValueErrors as in
    bi_elliptic_delta_v.
    """
    _check_bi_elliptic_args(mu, r1, r_b, r2)
    t1 = math.pi * math.sqrt((r1 + r_b) ** 3 / (8.0 * mu))
    t2 = math.pi * math.sqrt((r_b + r2) ** 3 / (8.0 * mu))
    return t1 + t2
