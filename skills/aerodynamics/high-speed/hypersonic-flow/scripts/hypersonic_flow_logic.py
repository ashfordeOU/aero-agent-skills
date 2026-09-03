#!/usr/bin/env python3
"""Hypersonic flow force estimation with modified Newtonian theory.

Estimates the aerodynamic force coefficients on a body in hypersonic
continuum flow (Mach well above 5) with the classical modified
Newtonian impact theory of hypersonic aerodynamics: the stagnation
pressure behind the normal shock follows from the Rayleigh pitot
relation, the finite-Mach stagnation pressure coefficient Cp_max(M)
scales the local pressure coefficient of any surface from its
inclination to the freestream through the sine-squared law, shadowed
surfaces carry zero pressure (Newtonian shadow) or the hypersonic
vacuum limit Cp_vacuum, and integration over a sphere, a sharp cone
and an inclined flat plate gives the drag, axial-force and lift
coefficients. Pure stdlib, no numpy. All angles in degrees, all Mach
numbers freestream. gamma defaults to 1.4 (air).

The method is the classical engineering estimate for hypersonic
continuum flow, not a CFD replacement. For gamma 1.4 the modified
Newtonian stagnation pressure coefficient approaches 1.839 from below
as M grows (cp_max at infinite Mach, the "Newtonian limit"); use it to
sanity-check finite-Mach values. NACA TR-824 is the classic
compressible-flow data source referenced for the relations.

Textbook anchors at gamma 1.4 (verified by the contract test):
rayleigh_pitot_ratio(2.0) = 5.640, rayleigh_pitot_ratio(5.0) = 32.65,
cp_stagnation(8.0) = 1.8275, sphere_drag_coefficient(8.0) = 0.9137,
cone_axial_force_coefficient(20.0, 8.0) = 0.2138.
"""

import math

GAMMA = 1.4
D2R = 0.017453292519943295  # degrees to radians
CP_MAX_INF = 1.839  # modified Newtonian limit of Cp_max at M -> inf, gamma 1.4


def _check_supersonic(M, gamma):
    """Reject nonphysical inputs: M must exceed 1, gamma must exceed 1."""
    if M <= 1.0:
        raise ValueError("Mach number must be supersonic (M > 1)")
    if gamma <= 1.0:
        raise ValueError("specific heat ratio gamma must be > 1")


def _check_angle_deg(angle_deg, lo, hi, name):
    """Reject an angle outside its closed physical range, in degrees."""
    if not lo <= angle_deg <= hi:
        raise ValueError("%s must lie in [%g, %g] degrees" % (name, lo, hi))


def rayleigh_pitot_ratio(M, gamma=GAMMA):
    """Stagnation pressure behind a normal shock over upstream static.

    p02/p1 from the Rayleigh pitot formula at freestream Mach M:
    ((gamma+1)^2*M^2/(4*gamma*M^2 - 2*(gamma-1)))^(gamma/(gamma-1)) *
    (2*gamma*M^2 - gamma + 1)/(gamma+1). Requires M > 1, gamma > 1.
    """
    _check_supersonic(M, gamma)
    first = ((gamma + 1.0) ** 2) * M * M
    first /= 4.0 * gamma * M * M - 2.0 * (gamma - 1.0)
    first = first ** (gamma / (gamma - 1.0))
    second = (2.0 * gamma * M * M - gamma + 1.0) / (gamma + 1.0)
    return first * second


def cp_stagnation(M, gamma=GAMMA):
    """Finite-Mach stagnation pressure coefficient Cp_max(M).

    Cp_max = 2/(gamma*M^2) * (p02/p1 - 1) with p02/p1 the Rayleigh
    pitot ratio. Tends to CP_MAX_INF (1.839 for gamma 1.4) from below
    as M grows without bound.
    """
    _check_supersonic(M, gamma)
    return 2.0 / (gamma * M * M) * (rayleigh_pitot_ratio(M, gamma) - 1.0)


def cp_vacuum(M, gamma=GAMMA):
    """Hypersonic vacuum limit for a shadowed surface.

    Surface pressure tending to zero gives Cp -> -2/(gamma*M^2), the
    most negative pressure coefficient reachable at finite Mach.
    """
    _check_supersonic(M, gamma)
    return -2.0 / (gamma * M * M)


def newtonian_cp(theta_deg, M, gamma=GAMMA):
    """Local pressure coefficient on a surface at angle theta to flow.

    Modified Newtonian sine-squared law: Cp = Cp_max * sin(theta)^2
    for a surface inclined theta (0 to 90 degrees) to the freestream.
    """
    _check_angle_deg(theta_deg, 0.0, 90.0, "theta")
    return cp_stagnation(M, gamma) * math.sin(theta_deg * D2R) ** 2


def sphere_drag_coefficient(M, gamma=GAMMA):
    """Drag coefficient of a sphere at hypersonic Mach.

    Modified Newtonian pressure integrated over the windward hemisphere
    with the frontal area reference gives Cd = Cp_max/2, the classic
    blunt-body drag estimate.
    """
    return cp_stagnation(M, gamma) / 2.0


def cone_axial_force_coefficient(half_angle_deg, M, gamma=GAMMA):
    """Axial force coefficient of a sharp cone at zero incidence.

    Newtonian pressure on the conical surface projected on the base
    area gives CA = Cp_max * sin(half_angle)^2. Half angle in degrees,
    open interval (0, 90).
    """
    if not 0.0 < half_angle_deg < 90.0:
        raise ValueError("cone half angle must lie in (0, 90) degrees")
    return cp_stagnation(M, gamma) * math.sin(half_angle_deg * D2R) ** 2


def flat_plate_coefficients(alpha_deg, M, gamma=GAMMA):
    """Force coefficients of an inclined flat plate, unit planform area.

    Windward side carries Cp = Cp_max * sin(alpha)^2, the leeward side
    is in the Newtonian shadow (Cp = 0). Normal-force coefficient
    CN = Cp_windward - Cp_leeward, then CL = CN*cos(alpha) and
    CD = CN*sin(alpha). ld_ratio is CL/CD, None at zero incidence
    where the division is undefined. Alpha in [0, 45] degrees.
    """
    _check_angle_deg(alpha_deg, 0.0, 45.0, "alpha")
    cp_windward = newtonian_cp(alpha_deg, M, gamma)
    cp_leeward = 0.0
    cn = cp_windward - cp_leeward
    cl = cn * math.cos(alpha_deg * D2R)
    cd = cn * math.sin(alpha_deg * D2R)
    if cd > 0.0:
        ld_ratio = cl / cd
    else:
        ld_ratio = None
    return {
        "cp_windward": cp_windward,
        "cp_leeward": cp_leeward,
        "cn": cn,
        "cl": cl,
        "cd": cd,
        "ld_ratio": ld_ratio,
    }


def analyze_body(body_type, params, M, gamma=GAMMA):
    """Dispatch to the body force model and add the stagnation state.

    body_type is 'sphere' (params unused), 'cone' (params
    {'half_angle_deg': ...}) or 'flat_plate' (params
    {'alpha_deg': ...}). Returns the body coefficient set plus the
    stagnation pressure coefficient and the Rayleigh pitot ratio that
    drive it. Rejects M <= 1, gamma <= 1, negative geometry and
    unknown body types with ValueError.
    """
    _check_supersonic(M, gamma)
    pitot = rayleigh_pitot_ratio(M, gamma)
    cp_stag = cp_stagnation(M, gamma)
    if body_type == "sphere":
        return {
            "body_type": body_type,
            "drag_coefficient": sphere_drag_coefficient(M, gamma),
            "cp_stagnation": cp_stag,
            "pitot_ratio": pitot,
        }
    if body_type == "cone":
        half_angle_deg = params.get("half_angle_deg")
        if half_angle_deg is None or half_angle_deg <= 0.0:
            raise ValueError("cone requires a positive half_angle_deg")
        return {
            "body_type": body_type,
            "half_angle_deg": half_angle_deg,
            "axial_force_coefficient": cone_axial_force_coefficient(
                half_angle_deg, M, gamma
            ),
            "cp_stagnation": cp_stag,
            "pitot_ratio": pitot,
        }
    if body_type == "flat_plate":
        alpha_deg = params.get("alpha_deg")
        if alpha_deg is None:
            raise ValueError("flat_plate requires an alpha_deg")
        result = flat_plate_coefficients(alpha_deg, M, gamma)
        result["body_type"] = body_type
        result["alpha_deg"] = alpha_deg
        result["cp_stagnation"] = cp_stag
        result["pitot_ratio"] = pitot
        return result
    raise ValueError("unknown body_type: expected sphere, cone or flat_plate")
