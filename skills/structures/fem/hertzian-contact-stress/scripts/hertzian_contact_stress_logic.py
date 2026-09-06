"""Hertzian contact stress between curved elastic bodies (closed form).

Computes the analytic Hertz contact solution used to validate FEA contact
runs: the equivalent elastic modulus E* and equivalent radius of curvature
Re of the contacting pair, the circular patch radius a or strip half-width
b, the maximum (elliptic pressure peak) contact pressure p0, the
subsurface maximum shear and von Mises state of the elastic half-space
under the patch (fixed at nu = 0.3 in both solids), and the standard Hertz
yield-limit check against the material yield strength: p0_yield = 3.3
sigma_y for point contact, 1.6 sigma_y for line contact, the yield-limit
load P_yield that drives p0 to p0_yield by inverting the load-pressure
closed form, and the margin with the pass/fail verdict.

Geometry classes (sign convention of the equivalent radius):
- point contact: sphere pair, sphere on flat, ball in concave socket,
  crossed equal cylinders (the per-plane curvature sum A + B = (1/r1 +
  1/r2)/2 equals 1/r only for equal crossed radii r, giving exactly the
  sphere-on-flat patch with Re = r);
- line contact: cylinder on flat, parallel cylinder pair (wheel-rail
  like), cylinder in concave bore, roller in concave race, all with an
  axial strip length L.

A flat partner is an infinite radius, a concave socket/bore/race is a
negative radius whose magnitude exceeds the convex body it surrounds, so
1/Re = 1/r1 + 1/r2 stays positive. Material properties enter only through
E* and sigma_y. SI units throughout (m, N, Pa).

Pure stdlib (math only), deterministic, no network. Out of scope: FEA
penalty or Lagrange contact enforcement, penetration, friction or
stick-slip (contact-analysis); the nominal P/(Dt) lug pin bearing stress
(lug-joint-analysis); interference-fit Lame contact pressure
(shrink-fit-analysis); generic von Mises or Tresca margins of an
arbitrary stress state (multiaxial-yield-criteria); general elliptical
patches of unequal crossed radii, which need the Hertz elliptic
integrals.

Assumptions recorded: subsurface ratios use nu = 0.3 in both solids
(module constants, anchor-verified against the exact elastic fields);
line-contact yield limit 1.6 sigma_y follows from the subsurface Tresca
condition tau_max = 0.30 p0 = sigma_y/2, so first subsurface yield and
the yield-limit pressure coincide for strips; the point-contact
yield-limit pressure 3.3 sigma_y is the standard spherical static-check
relation, above the 1.6 sigma_y of first subsurface yield where bounded
permanent deformation sets the load limit. Adhesive contact, tangential
traction, rolling or sliding contact with surface shear, wear and fatigue
are out of scope.
"""

import math

# Subsurface characteristics of the elastic half-space under the patch,
# nu = 0.3 in both solids (anchor-verified against the exact elastic
# field scans: z/a = 0.4810 vs 0.48, tau/p0 = 0.3100 vs 0.31, vm/p0 =
# 0.6200 vs 0.62 point; z/b = 0.7862 vs 0.78, tau/p0 = 0.3003 vs 0.30,
# z/b = 0.7042 vs 0.70, vm/p0 = 0.5575 vs 0.557 line).
POINT_Z_TAU = 0.48
POINT_TAU_P0 = 0.31
POINT_Z_VM = 0.48
POINT_VM_P0 = 0.62
LINE_Z_TAU = 0.78
LINE_TAU_P0 = 0.30
LINE_Z_VM = 0.70
LINE_VM_P0 = 0.557

# Standard Hertz yield-limit relations: the circular-patch (point)
# spherical static check allows p0 = 3.3 sigma_y before bounded permanent
# deformation; the strip (line) check allows p0 = 1.6 sigma_y, where the
# subsurface Tresca condition tau_max = 0.30 p0 = sigma_y/2 gives
# p0 = sigma_y/0.60 = 1.67 sigma_y, the 1.6 of the standard relation.
YLD_FACTOR_POINT = 3.3
YLD_FACTOR_LINE = 1.6


def equivalent_modulus(e1, nu1, e2, nu2):
    """Return the equivalent elastic modulus E* in Pa.

    From 1/E* = (1-nu1**2)/E1 + (1-nu2**2)/E2. For identical materials
    this reduces to E* = E/(2*(1-nu**2)) to float noise. ValueError for
    non-positive Young moduli or Poisson ratios outside [0, 0.5).
    """
    if e1 <= 0 or e2 <= 0:
        raise ValueError("Young moduli must be positive")
    if not (0.0 <= nu1 < 0.5) or not (0.0 <= nu2 < 0.5):
        raise ValueError("Poisson ratios must lie in [0, 0.5)")
    return 1.0 / ((1.0 - nu1 * nu1) / e1 + (1.0 - nu2 * nu2) / e2)


def equivalent_radius(r1, r2):
    """Return the equivalent radius of curvature Re in m.

    From 1/Re = 1/r1 + 1/r2, where r1 is always the convex (positive)
    radius of the first body and r2 is positive for a convex partner,
    negative for a concave internal partner (socket, bore, race,
    magnitude = concave radius) and +inf for a flat. The curvature sum
    1/Re must stay positive, so a concave partner must be larger than the
    convex body it surrounds. ValueError if r1 <= 0, r2 == 0,
    r2 == -inf, or the curvature sum is not positive.
    """
    if r1 <= 0:
        raise ValueError("convex radius r1 must be positive")
    if r2 == 0:
        raise ValueError("partner radius r2 must be non-zero (flat is +inf)")
    if r2 == float("-inf"):
        raise ValueError("a concave partner of infinite radius is unphysical")
    if r2 == float("inf"):
        return float(r1)
    curvature = 1.0 / r1 + 1.0 / r2
    if curvature <= 0:
        raise ValueError(
            "curvature sum 1/r1 + 1/r2 must be positive (concave partner "
            "must be larger than the convex body it surrounds)"
        )
    return 1.0 / curvature


def point_patch(load, e_star, re):
    """Return (a, p0) for circular point contact.

    a = (3*load*re/(4*e_star))**(1/3) and p0 = 3*load/(2*pi*a**2), the
    sphere-pair, sphere-on-flat, ball-in-socket and crossed-equal-cylinder
    closed forms. ValueError if load <= 0, e_star <= 0 or re <= 0.
    """
    if load <= 0 or e_star <= 0 or re <= 0:
        raise ValueError("load, E* and Re must all be positive")
    a = (3.0 * load * re / (4.0 * e_star)) ** (1.0 / 3.0)
    p0 = 3.0 * load / (2.0 * math.pi * a * a)
    return a, p0


def line_patch(load, e_star, re, length):
    """Return (b, p0) for line contact of a cylinder along axial length L.

    b = (4*load*re/(pi*length*e_star))**(1/2) and
    p0 = 2*load/(pi*b*length), the cylinder-on-flat, parallel-cylinder,
    cylinder-in-bore and roller-in-race strip forms. ValueError if any
    argument is not positive.
    """
    if load <= 0 or e_star <= 0 or re <= 0 or length <= 0:
        raise ValueError("load, E*, Re and length must all be positive")
    b = math.sqrt(4.0 * load * re / (math.pi * length * e_star))
    p0 = 2.0 * load / (math.pi * b * length)
    return b, p0


def point_subsurface(p0, a):
    """Return the point-contact subsurface state dict under the patch.

    {"z_tau": 0.48*a, "tau_max": 0.31*p0, "z_vm": 0.48*a,
    "vm_max": 0.62*p0} at nu = 0.3: the max shear and the von Mises
    stress both peak on the axis of symmetry at depth 0.48*a, where the
    von Mises stress equals exactly twice the max shear (axisymmetric
    field). ValueError if p0 <= 0 or a <= 0.
    """
    if p0 <= 0 or a <= 0:
        raise ValueError("p0 and patch radius a must be positive")
    return {
        "z_tau": POINT_Z_TAU * a,
        "tau_max": POINT_TAU_P0 * p0,
        "z_vm": POINT_Z_VM * a,
        "vm_max": POINT_VM_P0 * p0,
    }


def line_subsurface(p0, b):
    """Return the line-contact subsurface state dict under the strip.

    {"z_tau": 0.78*b, "tau_max": 0.30*p0, "z_vm": 0.70*b,
    "vm_max": 0.557*p0} at nu = 0.3: max shear at 0.78*b and max von
    Mises at 0.70*b, the plane-strain intermediate principal stress
    separating the two depths. ValueError if p0 <= 0 or b <= 0.
    """
    if p0 <= 0 or b <= 0:
        raise ValueError("p0 and strip half-width b must be positive")
    return {
        "z_tau": LINE_Z_TAU * b,
        "tau_max": LINE_TAU_P0 * p0,
        "z_vm": LINE_Z_VM * b,
        "vm_max": LINE_VM_P0 * p0,
    }


def yield_limit_pressure(sigma_y, point_contact=True):
    """Return the Hertz yield-limit pressure p0_yield in Pa.

    3.3*sigma_y for point contact (spherical static check) or
    1.6*sigma_y for line contact (strip). ValueError if sigma_y <= 0.
    """
    if sigma_y <= 0:
        raise ValueError("yield strength must be positive")
    factor = YLD_FACTOR_POINT if point_contact else YLD_FACTOR_LINE
    return factor * sigma_y


def yield_limit_load(sigma_y, e_star, re, point_contact=True, length=None):
    """Return the yield-limit load P_yield in N.

    Inverts the p0(load) closed form at p0 = p0_yield: point contact
    P_y = pi**3*Re**2*p0_y**3/(6*E*^2) (from p0 = 3P/(2 pi a^2) with
    a^3 = 3P Re/(4 E*)); line contact P_y = pi*Re*L*p0_y**2/E* (from
    p0 = 2P/(pi b L) with b^2 = 4P Re/(pi L E*)); length is required for
    line contact. ValueError if sigma_y <= 0 or the line length is
    missing or not positive.
    """
    if sigma_y <= 0:
        raise ValueError("yield strength must be positive")
    if e_star <= 0 or re <= 0:
        raise ValueError("E* and Re must be positive")
    p0_yield = yield_limit_pressure(sigma_y, point_contact=point_contact)
    if point_contact:
        return math.pi ** 3 * re * re * p0_yield ** 3 / (6.0 * e_star * e_star)
    if length is None or length <= 0:
        raise ValueError("line contact requires a positive axial length L")
    return math.pi * re * length * p0_yield * p0_yield / e_star


def check_yield_margin(p0, sigma_y, point_contact=True):
    """Return the yield-limit load check verdict dict.

    {"p0_yield": p0_yield, "margin": p0_yield/p0,
    "below_yield_limit": p0 <= p0_yield}. ValueError if p0 <= 0 or
    sigma_y <= 0.
    """
    if p0 <= 0:
        raise ValueError("contact pressure p0 must be positive")
    if sigma_y <= 0:
        raise ValueError("yield strength must be positive")
    p0_yield = yield_limit_pressure(sigma_y, point_contact=point_contact)
    return {
        "p0_yield": p0_yield,
        "margin": p0_yield / p0,
        "below_yield_limit": p0 <= p0_yield,
    }
