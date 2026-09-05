"""Curved-beam analysis with the Winkler correction (pure stdlib).

Stress-check a curved member (frame segment, torque link, clevis arc)
whose radial section bends about the center of curvature. The module
implements the classic Winkler curved-beam relations:

- neutral_axis_radius_rect: exact neutral-axis radius of a rectangular
  radial section, (r_o - r_i) / ln(r_o / r_i), the closed form of
  A / integral(dA / rho) with the out-of-plane width cancelling.
- neutral_axis_radius_circular_tube: exact closed form of
  A / integral(dA / rho) for a circular solid or tube whose material
  annulus is centered at distance r_c from the center of curvature,
  (sqrt(r_c**2 - a_i**2) + sqrt(r_c**2 - a_o**2)) / 2.
- eccentricity: inward shift of the neutral axis from the centroidal
  axis, e = r_c - r_n, positive for every physical curved beam.
- curved_beam_stress: Winkler bending stress at fiber radius r_fiber,
  sigma = M (r_n - r_fiber) / (A e r_fiber). The stress is hyperbolic
  across the depth, not linear as in the straight-beam law.
- straight_beam_stress_rect: straight Euler-Bernoulli extreme fiber
  stress 6 M / (A h) of the same rectangular section, the comparison
  baseline that exposes the curved-beam amplification.
- combined_axial_stress: adds the axial contribution P / A to a fiber
  bending stress, tension positive.
- stress_verdict: stress-to-allowable ratio with pass/fail verdict and
  margin.

Sign convention (documented per the leaf spec): a positive moment opens
the arc, tending to straighten the member. That puts the inner fiber
(r_fiber < r_n) in tension, sigma > 0, and the outer fiber in
compression, sigma < 0; a negative moment reverses both signs.

All radii share one length unit and all stresses one stress unit. In
the leaf worked example the units are mm and MPa, with moment in N mm
and area in mm^2, so N mm / mm^3 = N / mm^2 = MPa.

Deterministic closed-form core only: no FEA, no iteration, no
plasticity. Non-physical inputs raise ValueError.
"""

import math


def neutral_axis_radius_rect(r_i, r_o):
    """Neutral-axis radius of a curved bar with rectangular radial section.

    r_n = (r_o - r_i) / ln(r_o / r_i) is the exact closed form of
    A / integral(dA / rho); the width out of plane cancels, so the
    result depends only on the inner and outer radii of the section.

    Args:
        r_i: inner radius of the radial section (same length unit as r_o).
        r_o: outer radius of the radial section.

    Returns:
        Neutral-axis radius r_n, always strictly between r_i and r_o.

    Raises:
        ValueError: if r_i <= 0 or r_o <= r_i (non-physical radii).
    """
    if r_i <= 0.0:
        raise ValueError("inner radius r_i must be positive")
    if r_o <= r_i:
        raise ValueError("outer radius r_o must exceed inner radius r_i")
    return (r_o - r_i) / math.log(r_o / r_i)


def neutral_axis_radius_circular_tube(r_c, a_i, a_o):
    """Neutral-axis radius of a curved bar with a circular tube section.

    Closed form of A / integral(dA / rho) for a circular cross-section
    whose material annulus (inner radius a_i, outer radius a_o) is
    centered at distance r_c from the center of curvature:

        r_n = (sqrt(r_c**2 - a_i**2) + sqrt(r_c**2 - a_o**2)) / 2

    a_i = 0.0 reduces the tube to the solid circular section with
    r_n = (r_c + sqrt(r_c**2 - a_o**2)) / 2.

    Args:
        r_c: radius of the section center from the center of curvature.
        a_i: inner radius of the material annulus (0 for a solid round).
        a_o: outer radius of the material annulus.

    Returns:
        Neutral-axis radius r_n of the circular section.

    Raises:
        ValueError: if r_c <= 0, a_i < 0, a_o <= a_i or a_o >= r_c.
    """
    if r_c <= 0.0:
        raise ValueError("centerline radius r_c must be positive")
    if a_i < 0.0:
        raise ValueError("inner annulus radius a_i must not be negative")
    if a_o <= a_i:
        raise ValueError("outer annulus radius a_o must exceed a_i")
    if a_o >= r_c:
        raise ValueError("outer annulus radius a_o must stay below r_c")
    return (math.sqrt(r_c ** 2 - a_i ** 2) + math.sqrt(r_c ** 2 - a_o ** 2)) / 2.0


def eccentricity(r_centroid, r_n):
    """Inward shift of the neutral axis from the centroidal axis.

    e = r_centroid - r_n: the neutral axis of every physical curved
    beam sits inward of the centroid, toward the center of curvature,
    so the eccentricity is positive.

    Args:
        r_centroid: centroidal radius of the section, r_c.
        r_n: neutral-axis radius from the section closed form.

    Returns:
        Positive eccentricity e.

    Raises:
        ValueError: if r_centroid <= 0 or r_n <= 0.
    """
    if r_centroid <= 0.0:
        raise ValueError("centroidal radius must be positive")
    if r_n <= 0.0:
        raise ValueError("neutral-axis radius must be positive")
    return r_centroid - r_n


def curved_beam_stress(moment, area, e, r_n, r_fiber):
    """Winkler curved-beam bending stress at fiber radius r_fiber.

    sigma = moment * (r_n - r_fiber) / (area * e * r_fiber). The
    stress is hyperbolic across the depth. A positive moment opens the
    arc (tends to straighten the member): the inner fiber
    (r_fiber < r_n) is in tension, sigma > 0, and the outer fiber is
    in compression, sigma < 0; a negative moment reverses both signs.

    Args:
        moment: signed bending moment at the checked section.
        area: cross-section area (out of plane included).
        e: eccentricity r_centroid - r_n from eccentricity().
        r_n: neutral-axis radius from the section closed form.
        r_fiber: radius of the fiber being stressed (inner r_i or
            outer r_o of the section).

    Returns:
        Signed fiber bending stress (sigma > 0 tension).

    Raises:
        ValueError: if area <= 0, e <= 0, r_n <= 0 or r_fiber <= 0.
    """
    if area <= 0.0:
        raise ValueError("area must be positive")
    if e <= 0.0:
        raise ValueError("eccentricity must be positive")
    if r_n <= 0.0:
        raise ValueError("neutral-axis radius must be positive")
    if r_fiber <= 0.0:
        raise ValueError("fiber radius must be positive")
    return moment * (r_n - r_fiber) / (area * e * r_fiber)


def straight_beam_stress_rect(moment, area, depth):
    """Straight Euler-Bernoulli extreme fiber stress of a rectangle.

    sigma_straight = 6.0 * moment / (area * depth) is M c / I with
    c = depth / 2 and I = area * depth**2 / 12, the straight-beam
    world of the beam-frame-analysis leaf. Used only as the comparison
    baseline for the curved-beam amplification.

    Args:
        moment: signed bending moment at the checked section.
        area: cross-section area.
        depth: section depth in the radial direction, h = r_o - r_i.

    Returns:
        Extreme fiber stress of the straight-beam reading.

    Raises:
        ValueError: if area <= 0 or depth <= 0.
    """
    if area <= 0.0:
        raise ValueError("area must be positive")
    if depth <= 0.0:
        raise ValueError("section depth must be positive")
    return 6.0 * moment / (area * depth)


def combined_axial_stress(bending_stress, axial_force, area):
    """Add the axial contribution to a fiber bending stress.

    sigma_combined = bending_stress + axial_force / area, tension
    positive. Compression in the axial_force argument reads negative.

    Args:
        bending_stress: signed fiber bending stress from
            curved_beam_stress (or straight_beam_stress_rect).
        axial_force: signed axial load, tension positive.
        area: cross-section area.

    Returns:
        Combined fiber stress, tension positive.

    Raises:
        ValueError: if area <= 0.
    """
    if area <= 0.0:
        raise ValueError("area must be positive")
    return bending_stress + axial_force / area


def stress_verdict(sigma, allowable):
    """Rate a fiber stress against an allowable.

    Args:
        sigma: signed fiber stress (combined axial plus bending where
            the member carries axial load).
        allowable: allowable stress for the material and check.

    Returns:
        Dict with keys exactly {"abs_stress", "ratio", "verdict",
        "margin"}: abs_stress = abs(sigma), ratio = abs_stress /
        allowable, verdict "pass" when ratio <= 1.0 else "fail", and
        margin = allowable - abs_stress.

    Raises:
        ValueError: if allowable <= 0.
    """
    if allowable <= 0.0:
        raise ValueError("allowable stress must be positive")
    abs_stress = abs(sigma)
    ratio = abs_stress / allowable
    verdict = "pass" if ratio <= 1.0 else "fail"
    return {
        "abs_stress": abs_stress,
        "ratio": ratio,
        "verdict": verdict,
        "margin": allowable - abs_stress,
    }
