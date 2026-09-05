"""Torsion and shear-flow analysis for closed and open structural sections.

Pure stdlib implementation of the torsion-shear-flow leaf contract
(structures/fem). Functions:

- polar_j_solid: polar second moment J of a solid circular shaft.
- polar_j_tube: polar second moment J of a circular tube.
- saint_venant_j_rectangle: Saint-Venant torsion constant of a thin
  rectangle.
- saint_venant_j_open: conservative open-section Saint-Venant J built
  from independent thin rectangles.
- bredt_shear_flow: Bredt-Batho closed-section shear flow q = T/(2 A_m).
- closed_twist_rate: twist rate of a closed single-cell section from the
  wall length/thickness integral.
- multi_cell_shear_flow: two-cell shear-flow distribution solved from
  equal twist-rate compatibility plus torque balance (Cramer's rule).
- torsion_margin: torsional stress margin tau_allow / tau - 1.

SI units throughout: N m torque, m dimensions, Pa modulus, rad/m twist.
No material is hard-coded; the shear modulus G and the allowable shear
stress are always inputs. Non-physical inputs raise ValueError.
"""

import math


def polar_j_solid(radius):
    """Polar second moment of area of a solid circular shaft, pi r^4 / 2.

    radius: shaft radius in m. Returns J in m^4.
    """
    if radius <= 0:
        raise ValueError("solid shaft radius must be > 0")
    return math.pi * radius ** 4 / 2.0


def polar_j_tube(radius_outer, radius_inner):
    """Polar second moment of area of a circular tube, pi (ro^4 - ri^4) / 2.

    radius_outer and radius_inner are the outer and inner radii in m.
    Returns J in m^4. An inner radius of 0 degenerates to the solid shaft.
    """
    if radius_outer <= 0:
        raise ValueError("outer tube radius must be > 0")
    if radius_inner < 0:
        raise ValueError("inner tube radius must be >= 0")
    if radius_inner >= radius_outer:
        raise ValueError("inner tube radius must be < outer radius")
    return math.pi * (radius_outer ** 4 - radius_inner ** 4) / 2.0


def saint_venant_j_rectangle(width, thickness):
    """Saint-Venant torsion constant of a thin rectangle, width t^3 / 3.

    width and thickness are in m (thickness is the short dimension).
    Returns J in m^4.
    """
    if width <= 0:
        raise ValueError("rectangle width must be > 0")
    if thickness <= 0:
        raise ValueError("rectangle thickness must be > 0")
    return width * thickness ** 3 / 3.0


def saint_venant_j_open(elements):
    """Conservative open-section Saint-Venant J, sum of width_i t_i^3 / 3.

    elements is a list of (width, thickness) pairs in m describing the
    independent thin rectangles of a built-up open section. Returns J in
    m^4. Treating the rectangles as independent is the standard
    conservative open-section model; it ignores the junction stiffening.
    """
    if not elements:
        raise ValueError("open section needs at least one rectangle")
    total = 0.0
    for width, thickness in elements:
        if width <= 0:
            raise ValueError("rectangle width must be > 0")
        if thickness <= 0:
            raise ValueError("rectangle thickness must be > 0")
        total += width * thickness ** 3 / 3.0
    return total


def bredt_shear_flow(T, A_m):
    """Bredt-Batho closed-section shear flow q = T / (2 A_m), in N/m.

    T is the applied torque in N m (0 allowed) and A_m is the area in m^2
    enclosed by the mid-line of the closed section.
    """
    if T < 0:
        raise ValueError("applied torque T must be >= 0")
    if A_m <= 0:
        raise ValueError("enclosed area A_m must be > 0")
    return T / (2.0 * A_m)


def closed_twist_rate(T, G, side_lengths, thicknesses, A_m=None):
    """Twist rate of a closed single-cell section, T / (4 A_m^2 G) sum s/t.

    T: applied torque in N m (0 allowed). G: shear modulus in Pa.
    side_lengths and thicknesses are parallel lists in m of the mid-line
    wall segments. A_m is the mid-line enclosed area in m^2; when A_m is
    None it is computed from a rectangular outline, four sides listed as
    (a, b, a, b), as A_m = a * b. Returns the twist rate in rad/m.
    """
    if T < 0:
        raise ValueError("applied torque T must be >= 0")
    if G <= 0:
        raise ValueError("shear modulus G must be > 0")
    if len(side_lengths) != len(thicknesses):
        raise ValueError("side_lengths and thicknesses must have equal length")
    if not side_lengths:
        raise ValueError("closed section needs at least one wall segment")
    if A_m is None:
        if (len(side_lengths) == 4 and side_lengths[0] == side_lengths[2]
                and side_lengths[1] == side_lengths[3]):
            A_m = side_lengths[0] * side_lengths[1]
        else:
            raise ValueError("pass A_m explicitly for a non-rectangular outline")
    if A_m <= 0:
        raise ValueError("enclosed area A_m must be > 0")
    wall_sum = 0.0
    for length, thickness in zip(side_lengths, thicknesses):
        if length <= 0:
            raise ValueError("side lengths must be > 0")
        if thickness <= 0:
            raise ValueError("wall thicknesses must be > 0")
        wall_sum += length / thickness
    return T / (4.0 * A_m ** 2 * G) * wall_sum


def multi_cell_shear_flow(T, cell_areas, wall_integrals, shared_integrals, G):
    """Two-cell shear-flow distribution from compatibility and torque balance.

    T: applied torque in N m (0 allowed). G: shear modulus in Pa.
    cell_areas: [A1, A2] mid-line enclosed areas in m^2.
    wall_integrals: [S1, S2] outer-wall length/thickness integrals of each
    cell, sum of outer segment length divided by segment thickness.
    shared_integrals: S12 of the shared wall, L12 / t12 (a number, or a
    length-1 list). Equal twist-rate compatibility
    (q1 (S1+S12) - q2 S12) / A1 == (q2 (S2+S12) - q1 S12) / A2 together
    with torque balance T = 2 A1 q1 + 2 A2 q2 is solved by Cramer's rule.
    Returns dict {q1, q2, twist_rate} with q in N/m and the twist rate in
    rad/m as the mean of the two cell values (identical by construction).
    """
    if T < 0:
        raise ValueError("applied torque T must be >= 0")
    if G <= 0:
        raise ValueError("shear modulus G must be > 0")
    a1, a2 = _two_positive(cell_areas, "cell_areas")
    s1, s2 = _two_positive(wall_integrals, "wall_integrals")
    s12 = _shared_integral(shared_integrals)
    # Torque balance row: 2 A1 q1 + 2 A2 q2 = T.
    a11 = 2.0 * a1
    a12 = 2.0 * a2
    b1 = T
    # Compatibility row: expanded equal-twist-rate condition, rhs 0.
    a21 = a2 * (s1 + s12) + a1 * s12
    a22 = -(a2 * s12 + a1 * (s2 + s12))
    b2 = 0.0
    det = a11 * a22 - a12 * a21
    if det == 0.0:
        raise ValueError("singular two-cell system")
    q1 = (b1 * a22 - a12 * b2) / det
    q2 = (a11 * b2 - b1 * a21) / det
    twist1 = (q1 * (s1 + s12) - q2 * s12) / (2.0 * a1 * G)
    twist2 = (q2 * (s2 + s12) - q1 * s12) / (2.0 * a2 * G)
    return {"q1": q1, "q2": q2, "twist_rate": 0.5 * (twist1 + twist2)}


def torsion_margin(tau, tau_allow):
    """Torsional stress margin, tau_allow / tau - 1.

    tau is the running shear stress in Pa and tau_allow the allowable
    shear stress in Pa. A margin of 0 means the section is exactly at the
    allowable; positive margins are below it and negative ones exceed it.
    """
    if tau <= 0:
        raise ValueError("running shear stress tau must be > 0")
    if tau_allow <= 0:
        raise ValueError("allowable shear stress must be > 0")
    return tau_allow / tau - 1.0


def _two_positive(values, label):
    """Return values as a length-2 list of positive floats."""
    if isinstance(values, (list, tuple)):
        items = list(values)
    else:
        raise ValueError(label + " must be a list of two positive values")
    if len(items) != 2:
        raise ValueError(label + " must contain exactly two values")
    for value in items:
        if value <= 0:
            raise ValueError(label + " entries must be > 0")
    return items


def _shared_integral(shared_integrals):
    """Return the single shared-wall integral S12 as a positive float."""
    if isinstance(shared_integrals, (list, tuple)):
        if len(shared_integrals) != 1:
            raise ValueError("shared_integrals must hold exactly one value")
        value = shared_integrals[0]
    else:
        value = shared_integrals
    if value <= 0:
        raise ValueError("shared wall integral S12 must be > 0")
    return value
