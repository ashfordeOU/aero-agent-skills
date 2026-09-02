"""Low-thrust spiral orbit transfer math (Edelbaum approximation).

Deterministic, offline, stdlib-only helpers for sizing a continuous-
thrust (spiral) orbit transfer between two circular orbits: circular
orbit velocity at a radius, the Edelbaum delta-v budget for a transfer
with a total inclination change, the delta-v for the no-plane-change
spiral case, the rocket-equation propellant mass, final mass, and
transfer time for a constant-thrust, constant-specific-impulse
thruster, the impulsive Hohmann comparison budget, and a packed
summary for one transfer leg. All units are SI: radii in meters, mu in
m^3/s^2, velocities and delta-v in m/s, thrust in N, mass in kg,
specific impulse in seconds, time in seconds, angles in degrees.

Contract exercised by scripts/test_low_thrust_spiral.py.
"""

import math

MU_EARTH = 3.986004418e14  # Earth gravitational parameter, m^3/s^2
G0 = 9.80665               # standard gravity, m/s^2


def _require_radius(radius):
    if radius <= 0:
        raise ValueError("radius must be > 0, got %r" % (radius,))


def circular_velocity(radius, mu=MU_EARTH):
    """Return the circular orbit velocity in m/s at the given radius.

    v = sqrt(mu / r). A low earth orbit near 6878 km radius flies at
    about 7613 m/s and a geostationary orbit at 42164 km radius flies
    at about 3075 m/s.

    Raises ValueError for a non-positive radius or mu.
    """
    _require_radius(radius)
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    return math.sqrt(mu / radius)


def edelbaum_delta_v(r_i, r_f, di_deg, mu=MU_EARTH):
    """Return the Edelbaum delta-v in m/s for a low-thrust transfer.

    Edelbaum's approximation sizes the delta-v of a continuous-thrust
    transfer between two circular orbits at radii r_i and r_f with a
    total inclination change di_deg:

        dv = sqrt(v_i^2 + v_f^2 - 2 * v_i * v_f *
                  cos(pi * di_rad / 2)),  di_rad = di_deg * pi / 180

    with v_i and v_f the circular velocities at the two radii. The
    inclination change is assumed split evenly across the spiral. With
    di_deg = 0 the expression reduces to |v_i - v_f|, the pure spiral
    without a plane change, matching spiral_no_plane_change_delta_v.

    Raises ValueError for non-positive radii or mu, or an inclination
    outside [0, 180] degrees.
    """
    _require_radius(r_i)
    _require_radius(r_f)
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    if di_deg < 0 or di_deg > 180.0:
        raise ValueError(
            "di_deg must be within [0, 180], got %r" % (di_deg,)
        )
    v_i = circular_velocity(r_i, mu)
    v_f = circular_velocity(r_f, mu)
    di_rad = di_deg * math.pi / 180.0
    return math.sqrt(
        v_i * v_i + v_f * v_f
        - 2.0 * v_i * v_f * math.cos(math.pi * di_rad / 2.0)
    )


def spiral_no_plane_change_delta_v(r_i, r_f, mu=MU_EARTH):
    """Return the spiral delta-v in m/s with no inclination change.

    A continuous-thrust spiral between two circular orbits without a
    plane change costs |v_i - v_f|, the magnitude of the circular
    velocity difference, because the thrust only changes the speed on
    the slowly expanding (or contracting) spiral.

    Raises ValueError for non-positive radii or mu.
    """
    _require_radius(r_i)
    _require_radius(r_f)
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    return abs(circular_velocity(r_i, mu) - circular_velocity(r_f, mu))


def transfer_mass_and_time(delta_v, m0, thrust, isp):
    """Return (m_prop, m_final, t_transfer) for a constant-thrust leg.

    With exhaust velocity c = g0 * isp, the rocket equation gives
    m_final = m0 * exp(-delta_v / c), propellant mass m_prop = m0 -
    m_final, and the burn time for constant thrust
    t_transfer = m_prop * c / thrust. Units: kg, kg, s.

    Raises ValueError for a negative delta-v, or non-positive initial
    mass, thrust, or specific impulse.
    """
    if delta_v < 0:
        raise ValueError("delta_v must be >= 0, got %r" % (delta_v,))
    if m0 <= 0:
        raise ValueError("m0 must be > 0, got %r" % (m0,))
    if thrust <= 0:
        raise ValueError("thrust must be > 0, got %r" % (thrust,))
    if isp <= 0:
        raise ValueError("isp must be > 0, got %r" % (isp,))
    c = G0 * isp
    m_final = m0 * math.exp(-delta_v / c)
    m_prop = m0 - m_final
    t_transfer = m_prop * c / thrust
    return m_prop, m_final, t_transfer


def hohmann_delta_v(r_i, r_f, mu=MU_EARTH):
    """Return the impulsive Hohmann delta-v magnitude in m/s.

    dv = |v_i * (sqrt(2 * r_f / (r_i + r_f)) - 1)
          + v_f * (1 - sqrt(2 * r_i / (r_i + r_f)))|

    the sum of the two Hohmann impulses between circular orbits at r_i
    and r_f (the absolute value keeps the budget positive for inward
    and outward transfers alike), used as the impulsive benchmark
    against the continuous low-thrust spiral budget for the same end
    orbits with no plane change.

    Raises ValueError for non-positive radii or mu, or equal radii.
    """
    _require_radius(r_i)
    _require_radius(r_f)
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    if r_i == r_f:
        raise ValueError("r_i and r_f must differ, got equal radii %r" % (r_i,))
    v_i = circular_velocity(r_i, mu)
    v_f = circular_velocity(r_f, mu)
    return abs(
        v_i * (math.sqrt(2.0 * r_f / (r_i + r_f)) - 1.0)
        + v_f * (1.0 - math.sqrt(2.0 * r_i / (r_i + r_f)))
    )


def low_thrust_transfer_summary(r_i, r_f, di_deg, thrust, isp, m0, mu=MU_EARTH):
    """Return a dict sizing one low-thrust transfer leg.

    Keys: v_i and v_f (circular velocities at the inner and outer
    radii, m/s), delta_v (Edelbaum budget including the inclination
    change, m/s), m_prop (propellant mass, kg), mf (final mass, kg),
    and t_transfer (transfer time, s) for a constant-thrust,
    constant-specific-impulse ion propulsion trajectory from radius r_i
    to radius r_f with total inclination change di_deg.

    Raises ValueError for non-positive radii, thrust, initial mass, or
    specific impulse, or an inclination outside [0, 180] degrees.
    """
    v_i = circular_velocity(r_i, mu)
    v_f = circular_velocity(r_f, mu)
    delta_v = edelbaum_delta_v(r_i, r_f, di_deg, mu)
    m_prop, m_final, t_transfer = transfer_mass_and_time(delta_v, m0, thrust, isp)
    return {
        "v_i": v_i,
        "v_f": v_f,
        "delta_v": delta_v,
        "m_prop": m_prop,
        "mf": m_final,
        "t_transfer": t_transfer,
    }
