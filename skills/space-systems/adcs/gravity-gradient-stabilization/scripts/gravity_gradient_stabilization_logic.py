"""Passive gravity-gradient stabilization analysis for nadir-pointing spacecraft.

Pure standard-library module. Implements the inertia-ratio stability
criterion (I_y > I_x > I_z, y along the orbit normal), the pitch libration
frequency omega_p = sqrt(3 * n^2 * (I_x - I_z) / I_y) and its period, the
gravity-gradient restoring torque (3/2) * n^2 * (I_x - I_z) * sin(2 * theta)
at a pitch offset, and gravity boom tip-mass sizing for a target libration
stiffness. Conventions: circular orbit with mean motion n = sqrt(mu / r^3),
x along the velocity direction, y along the orbit normal, z nadir.

The restoring torque and libration relations here are the passive-stiffness
design view; full gravity torque modeling and rigid-body propagation belong
to the attitude-dynamics leaf. All quantities are SI (kg m^2, s, N m).
"""

import math

# Gravitational parameter of Earth, m^3 s^-2.
MU_EARTH = 3.986004418e14
SECONDS_PER_MINUTE = 60.0
DEG_TO_RAD = math.pi / 180.0


def _require_positive_inertias(ix, iy, iz):
    """Raise ValueError unless every principal moment is positive."""
    if ix <= 0.0 or iy <= 0.0 or iz <= 0.0:
        raise ValueError("moments of inertia must all be positive")


def mean_motion(mu, radius):
    """Mean motion n = sqrt(mu / r^3) of a circular orbit, in rad/s."""
    if mu <= 0.0:
        raise ValueError("mu must be positive")
    if radius <= 0.0:
        raise ValueError("radius must be positive")
    return math.sqrt(mu / radius ** 3.0)


def stability_verdict(ix, iy, iz):
    """True when the inertia-ratio criterion I_y > I_x > I_z holds.

    I_y is the moment about the orbit normal; it must be the largest
    principal moment for a passively stable nadir equilibrium.
    """
    _require_positive_inertias(ix, iy, iz)
    return iy > ix > iz


def moment_ordering(ix, iy, iz):
    """Principal axes sorted by descending moment, e.g. 'y > x > z'."""
    _require_positive_inertias(ix, iy, iz)
    axes = [(iy, "y"), (ix, "x"), (iz, "z")]
    axes.sort(reverse=True)
    return " > ".join(label for _, label in axes)


def pitch_libration_frequency(ix, iy, iz, mu, radius):
    """Pitch libration frequency sqrt(3 * n^2 * (I_x - I_z) / I_y), rad/s."""
    _require_positive_inertias(ix, iy, iz)
    if ix - iz <= 0.0:
        raise ValueError(
            "pitch libration requires I_x > I_z (positive inertia spread)")
    n = mean_motion(mu, radius)
    return n * math.sqrt(3.0 * (ix - iz) / iy)


def libration_period(ix, iy, iz, mu, radius):
    """Pitch libration period 2 * pi / omega_p, in seconds."""
    omega_p = pitch_libration_frequency(ix, iy, iz, mu, radius)
    return 2.0 * math.pi / omega_p


def restoring_torque(ix, iy, iz, mu, radius, pitch_offset_deg):
    """Gravity-gradient restoring torque at a pitch offset, in N m.

    T = (3/2) * n^2 * (I_x - I_z) * sin(2 * theta). The torque vanishes at
    theta = 0 and 90 degrees and reaches its largest magnitude at 45
    degrees. Offsets from -90 to 90 degrees inclusive are accepted; the
    endpoints are the unstable equilibria where the torque is exactly
    zero. An offset magnitude above 90 degrees is rejected as
    non-physical for a nadir-pointing body.
    """
    _require_positive_inertias(ix, iy, iz)
    if ix - iz <= 0.0:
        raise ValueError(
            "restoring torque requires I_x > I_z (positive inertia spread)")
    if abs(pitch_offset_deg) > 90.0:
        raise ValueError(
            "pitch offset must lie within -90 to 90 degrees inclusive")
    n = mean_motion(mu, radius)
    theta = pitch_offset_deg * DEG_TO_RAD
    return 1.5 * n * n * (ix - iz) * math.sin(2.0 * theta)


def boom_tip_mass_for_stiffness(ix_other, target_ix_minus_iz, boom_length):
    """Tip mass m = target / L^2 for a gravity boom of length L, in kg.

    Point-mass approximation: a tip mass at the boom end contributes
    m * L^2 to the inertia spread I_x - I_z. ix_other is the spacecraft
    moment carried before the boom is added; it is validated as positive
    bookkeeping context, and the approximation credits the full target
    spread to the tip mass.
    """
    if ix_other <= 0.0:
        raise ValueError("ix_other must be positive")
    if target_ix_minus_iz <= 0.0:
        raise ValueError("target inertia spread must be positive")
    if boom_length <= 0.0:
        raise ValueError("boom length must be positive")
    return target_ix_minus_iz / (boom_length * boom_length)


def gg_report(ix, iy, iz, mu, radius, pitch_offset_deg=45.0):
    """Design report dict for a passive gravity-gradient stabilized body.

    Keys: stable (inertia-ratio verdict), ordering (axis order string),
    omega_p (pitch libration frequency), period_s (libration period),
    period_min (period in minutes), torque (restoring torque at the given
    offset, default 45 degrees, the maximum-torque worst case). When the
    inertia-ratio criterion fails the quantity keys are None and the
    verdict keys carry the diagnosis. Raises ValueError on non-positive
    inertias, non-positive mu or radius, or an offset magnitude above 90.
    """
    _require_positive_inertias(ix, iy, iz)
    if abs(pitch_offset_deg) > 90.0:
        raise ValueError(
            "pitch offset must lie within -90 to 90 degrees inclusive")
    mean_motion(mu, radius)  # validates mu and radius
    stable = stability_verdict(ix, iy, iz)
    ordering = moment_ordering(ix, iy, iz)
    if stable:
        omega_p = pitch_libration_frequency(ix, iy, iz, mu, radius)
        period_s = libration_period(ix, iy, iz, mu, radius)
        torque = restoring_torque(ix, iy, iz, mu, radius, pitch_offset_deg)
    else:
        omega_p = None
        period_s = None
        torque = None
    return {
        "stable": stable,
        "ordering": ordering,
        "omega_p": omega_p,
        "period_s": period_s,
        "period_min": None if period_s is None
        else period_s / SECONDS_PER_MINUTE,
        "torque": torque,
    }
