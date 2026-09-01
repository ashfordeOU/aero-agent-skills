"""Eddy current inspection (ET) math for aerospace NDT.

Deterministic, offline, stdlib-only helpers for eddy current inspection:
standard depth of penetration from test frequency, electrical
conductivity, and magnetic permeability; frequency selection that places
a surface or subsurface flaw within the usable penetration band; percent
IACS to siemens per meter conversion; eddy current density ratio and
phase lag at the flaw depth. All units are SI: frequency in Hz,
conductivity in S/m, permeability in H/m, depth in meters.

Contract exercised by scripts/test_eddy_current_inspection.py.
"""

import math

MU0 = 4.0 * math.pi * 1e-7  # vacuum permeability, H/m
COPPER_100_IACS = 5.8e7  # S/m, annealed copper 100 percent IACS reference


def standard_depth_of_penetration(frequency, conductivity, relative_permeability=1.0):
    """Return the standard depth of penetration delta in meters.

    delta = 1 / sqrt(pi * f * mu * sigma), with mu = MU0 * mu_r. At one
    standard depth of penetration the eddy current density falls to 1/e
    (about 37 percent) of its surface value. Higher frequency, higher
    conductivity, and higher permeability all shrink delta.

    Raises ValueError for a non-positive frequency, conductivity, or
    relative permeability.
    """
    if frequency <= 0:
        raise ValueError("frequency must be > 0, got %r" % (frequency,))
    if conductivity <= 0:
        raise ValueError("conductivity must be > 0, got %r" % (conductivity,))
    if relative_permeability <= 0:
        raise ValueError(
            "relative permeability must be > 0, got %r" % (relative_permeability,)
        )
    mu = MU0 * relative_permeability
    return 1.0 / math.sqrt(math.pi * frequency * mu * conductivity)


def frequency_for_depth(depth, conductivity, relative_permeability=1.0):
    """Return the frequency in Hz whose standard depth of penetration
    equals the given depth.

    Solving delta = depth for f gives f = 1 / (pi * mu * sigma * depth^2).
    This is the frequency that places a flaw at exactly one standard
    depth of penetration below the surface.

    Raises ValueError for a non-positive depth, conductivity, or
    relative permeability.
    """
    if depth <= 0:
        raise ValueError("depth must be > 0, got %r" % (depth,))
    if conductivity <= 0:
        raise ValueError("conductivity must be > 0, got %r" % (conductivity,))
    if relative_permeability <= 0:
        raise ValueError(
            "relative permeability must be > 0, got %r" % (relative_permeability,)
        )
    mu = MU0 * relative_permeability
    return 1.0 / (math.pi * mu * conductivity * depth * depth)


def select_frequency_for_flaw(
    flaw_depth, conductivity, relative_permeability=1.0, penetration_factor=2.0
):
    """Return the test frequency in Hz for a flaw at the given depth.

    The frequency sets the standard depth of penetration to
    penetration_factor times the flaw depth, so delta = factor * depth.
    For subsurface flaws use a factor of 2.0 or more, keeping the flaw
    within one delta where the current density stays above 37 percent.
    For surface flaws use a factor below 1.0, concentrating the current
    near the surface for sharp crack response.

    Raises ValueError for a non-positive flaw depth, conductivity,
    relative permeability, or penetration factor.
    """
    if flaw_depth <= 0:
        raise ValueError("flaw depth must be > 0, got %r" % (flaw_depth,))
    if conductivity <= 0:
        raise ValueError("conductivity must be > 0, got %r" % (conductivity,))
    if relative_permeability <= 0:
        raise ValueError(
            "relative permeability must be > 0, got %r" % (relative_permeability,)
        )
    if penetration_factor <= 0:
        raise ValueError(
            "penetration factor must be > 0, got %r" % (penetration_factor,)
        )
    return frequency_for_depth(
        penetration_factor * flaw_depth, conductivity, relative_permeability
    )


def eddy_current_density_ratio(depth, delta):
    """Return the eddy current density at depth as a fraction of the
    surface value: exp(-depth / delta).

    At one standard depth of penetration the ratio is 1/e, about 0.368;
    at two deltas it is about 0.135.

    Raises ValueError for a negative depth or a non-positive delta.
    """
    if depth < 0:
        raise ValueError("depth must be >= 0, got %r" % (depth,))
    if delta <= 0:
        raise ValueError("delta must be > 0, got %r" % (delta,))
    return math.exp(-depth / delta)


def phase_lag_degrees(depth, delta):
    """Return the eddy current phase lag at depth in degrees.

    The phase lag in radians is depth / delta, so in degrees it is
    (depth / delta) * 180 / pi. At one standard depth of penetration
    the lag is one radian, about 57.3 degrees.

    Raises ValueError for a negative depth or a non-positive delta.
    """
    if depth < 0:
        raise ValueError("depth must be >= 0, got %r" % (depth,))
    if delta <= 0:
        raise ValueError("delta must be > 0, got %r" % (delta,))
    return (depth / delta) * 180.0 / math.pi


def conductivity_from_iacs(percent_iacs):
    """Return the electrical conductivity in S/m for a percent IACS value.

    sigma = (percent / 100) * 5.8e7, with 100 percent IACS equal to the
    annealed copper reference of 5.8e7 S/m. Aluminum alloys sit near 30
    percent IACS and titanium alloys near 5 percent IACS.

    Raises ValueError for a non-positive percent IACS.
    """
    if percent_iacs <= 0:
        raise ValueError("percent IACS must be > 0, got %r" % (percent_iacs,))
    return (percent_iacs / 100.0) * COPPER_100_IACS
