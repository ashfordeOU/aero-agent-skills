"""Hohmann transfer math for coplanar circular-orbit transfers.

Deterministic, offline, stdlib-only helpers for a two-impulse Hohmann
transfer between two coplanar circular orbits: circular orbit velocity,
transfer-orbit semimajor axis, transfer period and transfer time,
vis-viva velocities on the transfer ellipse, the departure and arrival
burn impulses, the total delta-v budget, the orbit period of a circular
orbit, the specific orbital energy, and the rendezvous phase angle (the
lead angle at departure for a target in the outer circular orbit). All
units are SI: radii and semimajor axes in meters, mu in m^3/s^2,
velocities in m/s, delta-v in m/s, times in seconds, angles in degrees.

Contract exercised by scripts/test_hohmann_transfer.py.
"""

import math

MU_EARTH = 3.986004418e14  # Earth gravitational parameter, m^3/s^2
EARTH_RADIUS = 6378.137e3  # Earth equatorial radius, m


def circular_velocity(radius, mu=MU_EARTH):
    """Return the circular orbit velocity in m/s at the given radius.

    v = sqrt(mu / r). Applies to any circular orbit: a low earth orbit
    near 6878 km radius flies at about 7613 m/s and a geostationary
    orbit at 42164 km radius flies at about 3075 m/s.

    Raises ValueError for a non-positive radius or mu.
    """
    if radius <= 0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    return math.sqrt(mu / radius)


def transfer_semimajor_axis(r1, r2):
    """Return the transfer ellipse semimajor axis in meters.

    a = (r1 + r2) / 2: the Hohmann transfer ellipse is tangent to the
    inner circular orbit at periapsis and to the outer circular orbit
    at apoapsis, so its semimajor axis is the mean of the two radii.

    Raises ValueError for non-positive radii or equal radii (an equal
    radius pair is not a transfer).
    """
    if r1 <= 0:
        raise ValueError("r1 must be > 0, got %r" % (r1,))
    if r2 <= 0:
        raise ValueError("r2 must be > 0, got %r" % (r2,))
    if r1 == r2:
        raise ValueError("r1 and r2 must differ, got equal radii %r" % (r1,))
    return (r1 + r2) / 2.0


def orbit_period(radius, mu=MU_EARTH):
    """Return the period in seconds of a circular orbit at the radius.

    T = 2 * pi * sqrt(r^3 / mu), Kepler's third law for a circular
    orbit. A geostationary orbit at 42164 km has a period of about
    86164 s, one sidereal day.

    Raises ValueError for a non-positive radius or mu.
    """
    if radius <= 0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    return 2.0 * math.pi * math.sqrt(radius**3 / mu)


def transfer_period(semimajor_axis, mu=MU_EARTH):
    """Return the full transfer ellipse period in seconds.

    T = 2 * pi * sqrt(a^3 / mu) from the transfer semimajor axis.

    Raises ValueError for a non-positive semimajor axis or mu.
    """
    if semimajor_axis <= 0:
        raise ValueError("semimajor axis must be > 0, got %r" % (semimajor_axis,))
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    return 2.0 * math.pi * math.sqrt(semimajor_axis**3 / mu)


def transfer_time(r1, r2, mu=MU_EARTH):
    """Return the one-way Hohmann transfer time in seconds.

    The transfer covers half the ellipse, so the time is half the
    transfer period: t = pi * sqrt(a^3 / mu) with a = (r1 + r2) / 2.
    A low-earth to geostationary transfer takes about 19055 s, roughly
    5.3 hours.

    Raises ValueError for non-positive radii, equal radii, or non-
    positive mu.
    """
    a = transfer_semimajor_axis(r1, r2)
    return transfer_period(a, mu) / 2.0


def vis_viva_velocity(radius, semimajor_axis, mu=MU_EARTH):
    """Return the vis-viva speed in m/s at the given radius on the orbit.

    v = sqrt(mu * (2 / r - 1 / a)). On the transfer ellipse this gives
    the periapsis speed at r1 and the apoapsis speed at r2, both higher
    and lower than the circular speeds they replace.

    Raises ValueError for a non-positive radius, semimajor axis, or mu.
    """
    if radius <= 0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    if semimajor_axis <= 0:
        raise ValueError("semimajor axis must be > 0, got %r" % (semimajor_axis,))
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    return math.sqrt(mu * (2.0 / radius - 1.0 / semimajor_axis))


def departure_delta_v(r1, r2, mu=MU_EARTH):
    """Return the departure burn impulse in m/s at the inner radius.

    dv1 = |v_transfer(r1) - v_circular(r1)|: the first impulse raises
    the spacecraft from the inner circular orbit onto the transfer
    ellipse at periapsis. For an outward transfer the burn is
    prograde; for an inward transfer it is retrograde.

    Raises ValueError for non-positive radii, equal radii, or non-
    positive mu.
    """
    a = transfer_semimajor_axis(r1, r2)
    return abs(vis_viva_velocity(r1, a, mu) - circular_velocity(r1, mu))


def arrival_delta_v(r1, r2, mu=MU_EARTH):
    """Return the arrival burn impulse in m/s at the outer radius.

    dv2 = |v_circular(r2) - v_transfer(r2)|: the second impulse at
    apoapsis circularizes the transfer ellipse into the outer circular
    orbit. Together with the departure impulse it makes the Hohmann
    transfer the minimum-energy two-impulse coplanar transfer.

    Raises ValueError for non-positive radii, equal radii, or non-
    positive mu.
    """
    a = transfer_semimajor_axis(r1, r2)
    return abs(circular_velocity(r2, mu) - vis_viva_velocity(r2, a, mu))


def total_delta_v(r1, r2, mu=MU_EARTH):
    """Return the total Hohmann delta-v budget in m/s.

    dv_total = dv1 + dv2. A low-earth to geostationary coplanar
    transfer totals about 3816 m/s (about 3.9 km/s, the classic
    reference budget before plane changes).

    Raises ValueError for non-positive radii, equal radii, or non-
    positive mu.
    """
    return departure_delta_v(r1, r2, mu) + arrival_delta_v(r1, r2, mu)


def specific_orbital_energy(semimajor_axis, mu=MU_EARTH):
    """Return the specific orbital energy in J/kg of the transfer.

    epsilon = -mu / (2 * a). The transfer ellipse carries less energy
    than the outer circular orbit and more than the inner one, which
    is why the two impulses are both positive for an outward transfer.

    Raises ValueError for a non-positive semimajor axis or mu.
    """
    if semimajor_axis <= 0:
        raise ValueError("semimajor axis must be > 0, got %r" % (semimajor_axis,))
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    return -mu / (2.0 * semimajor_axis)


def rendezvous_phase_angle(r1, r2, mu=MU_EARTH):
    """Return the departure lead angle in degrees for a Hohmann rendezvous.

    The chaser covers 180 degrees of true anomaly during the transfer.
    The target in the outer circular orbit sweeps n2 * t_transfer in
    the same time, so the chaser must lead the target by
    lead = 180 - (t_transfer / T2) * 360 degrees at departure. The
    result is wrapped to [0, 360).

    Raises ValueError for non-positive radii, equal radii, or non-
    positive mu.
    """
    t = transfer_time(r1, r2, mu)
    t2 = orbit_period(r2, mu)
    lead = 180.0 - (t / t2) * 360.0
    return lead % 360.0
