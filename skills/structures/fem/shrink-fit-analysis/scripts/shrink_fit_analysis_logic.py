"""Two-cylinder Lame radial-interference (shrink or press) fit analysis.

Computes the closed-form stress state of a bushing or sleeve pressed or
shrunk into a lug, hub or race. The total radial interference delta is
converted into the interface contact pressure p from the Lame thick
cylinder radial compliance of both members: the inner member (bore r_i,
interface radius r_c) carries only the external pressure p, so its
interface hoop is -p (r_c**2 + r_i**2) / (r_c**2 - r_i**2) and its inward
interface displacement is

    u_inner = -(p r_c / E_i) * ((r_c**2 + r_i**2) / (r_c**2 - r_i**2) - nu_i),

while the outer member (bore r_c, outer radius r_o) carries only the
internal pressure p, so its bore hoop is +p (r_o**2 + r_c**2) /
(r_o**2 - r_c**2) and its outward bore displacement is

    u_outer = +(p r_c / E_o) * ((r_o**2 + r_c**2) / (r_o**2 - r_c**2) + nu_o).

Compatibility delta = u_outer - u_inner gives the contact pressure

    p = delta / [ (r_c / E_i) * ((r_c**2 + r_i**2) / (r_c**2 - r_i**2) - nu_i)
                + (r_c / E_o) * ((r_o**2 + r_c**2) / (r_o**2 - r_c**2) + nu_o) ],

the standard Shigley/Juvinall class press-fit relation. Sign convention:
the COMPRESSED inner member carries the -nu_i term and the EXPANDED outer
member the +nu_o term; swapping the two signs (a common transcription
error) shifts p by several percent. The critical bore planes follow from
the exact Lame extreme-fiber values: the inner member bore (r = r_i) is a
free surface with sigma_r = 0 and the most compressive hoop in the
assembly, sigma_theta = -2 p r_c**2 / (r_c**2 - r_i**2); the outer member
bore (r = r_c) carries sigma_r = -p and the maximum tensile hoop
sigma_theta = p (r_o**2 + r_c**2) / (r_o**2 - r_c**2). The von-Mises
equivalent of each bore plane uses the plane stress (sigma_z = 0)
distortion-energy form, and, because every stress is linear in p (elastic,
small strain), the assembly scales linearly to the yield point of the
governing (least-margin) bore.

Assumptions recorded: plane stress at the bore surfaces (sigma_z = 0) for
the von-Mises equivalent; elastic small-strain linearity for the yield
scaling; all radii share one length unit, all stresses one stress unit and
all moduli and pressures the same stress unit (the worked example uses mm
and MPa, with E in MPa and delta in mm). Pure stdlib (math only),
deterministic, closed form only: no FEA, no iteration, no plasticity.
"""

import math


def _require(name, condition):
    """Raise ValueError when a physical-input condition is violated."""
    if not condition:
        raise ValueError("non-physical input for %s" % name)


def contact_pressure(delta, r_i, r_c, r_o, E_i, nu_i, E_o, nu_o):
    """Interface contact pressure of a two-cylinder radial-interference fit.

    p = delta / [ (r_c / E_i) * ((r_c**2 + r_i**2) / (r_c**2 - r_i**2) -
    nu_i) + (r_c / E_o) * ((r_o**2 + r_c**2) / (r_o**2 - r_c**2) + nu_o) ],
    the exact two-cylinder Lame form. delta is the total RADIAL
    interference, delta > 0. ValueError on delta <= 0, r_i <= 0, r_c <=
    r_i, r_o <= r_c, E_i <= 0, E_o <= 0, or any Poisson ratio outside
    (0, 0.5).
    """
    _require("delta", delta > 0.0)
    _require("r_i", r_i > 0.0)
    _require("r_c", r_c > r_i)
    _require("r_o", r_o > r_c)
    _require("E_i", E_i > 0.0)
    _require("E_o", E_o > 0.0)
    _require("nu_i", 0.0 < nu_i < 0.5)
    _require("nu_o", 0.0 < nu_o < 0.5)
    inner_compliance = (r_c / E_i) * (
        (r_c ** 2 + r_i ** 2) / (r_c ** 2 - r_i ** 2) - nu_i
    )
    outer_compliance = (r_c / E_o) * (
        (r_o ** 2 + r_c ** 2) / (r_o ** 2 - r_c ** 2) + nu_o
    )
    return delta / (inner_compliance + outer_compliance)


def stress_distributions(p, r_i, r_c, r_o):
    """Critical bore plane stresses of both members at interface pressure p.

    Returns a dict with exactly the keys {"inner_bore_sigma_r",
    "inner_bore_sigma_theta", "outer_bore_sigma_r",
    "outer_bore_sigma_theta"}: the inner member bore (r = r_i) is a free
    surface with sigma_r = 0.0 and the most compressive hoop in the
    assembly, sigma_theta = -2.0 * p * r_c**2 / (r_c**2 - r_i**2); the
    outer member bore (r = r_c) carries sigma_r = -p and the maximum
    tensile hoop sigma_theta = p * (r_o**2 + r_c**2) / (r_o**2 - r_c**2).
    ValueError if p <= 0 or the radii violate 0 < r_i < r_c < r_o.
    """
    _require("p", p > 0.0)
    _require("r_i", r_i > 0.0)
    _require("r_c", r_c > r_i)
    _require("r_o", r_o > r_c)
    inner_bore_sigma_theta = -2.0 * p * r_c ** 2 / (r_c ** 2 - r_i ** 2)
    outer_bore_sigma_theta = p * (r_o ** 2 + r_c ** 2) / (r_o ** 2 - r_c ** 2)
    return {
        "inner_bore_sigma_r": 0.0,
        "inner_bore_sigma_theta": inner_bore_sigma_theta,
        "outer_bore_sigma_r": -p,
        "outer_bore_sigma_theta": outer_bore_sigma_theta,
    }


def von_mises_margin(sy, sigma_r, sigma_theta):
    """Von-Mises equivalent and yield margin of a bore plane stress state.

    sigma_vm = sqrt(sigma_theta**2 - sigma_theta*sigma_r + sigma_r**2),
    the plane stress (sigma_z = 0) distortion-energy equivalent, and
    margin = sy - sigma_vm, positive below yield. ValueError if sy <= 0.
    """
    _require("sy", sy > 0.0)
    sigma_vm = math.sqrt(
        sigma_theta ** 2 - sigma_theta * sigma_r + sigma_r ** 2
    )
    return {"sigma_vm": sigma_vm, "margin": sy - sigma_vm}


def allowable_interference(
    delta, r_i, r_c, r_o, E_i, nu_i, E_o, nu_o, sy_i, sy_o
):
    """Governing member and allowable interference before the fit yields.

    Evaluates contact_pressure and stress_distributions, forms
    von_mises_margin at both bores with sy_i (inner member) and sy_o
    (outer member), and, because every stress is linear in p (elastic,
    small strain), scales linearly to the yield point of the governing
    (least-margin) bore: governing_contact_pressure = p * sy_gov /
    sigma_vm_gov and allowable_interference = delta * sy_gov /
    sigma_vm_gov. Returns a dict with exactly the keys
    {"governing_member", "governing_contact_pressure",
    "allowable_interference"}; governing_member is the string "inner" or
    "outer". ValueErrors as in contact_pressure, plus sy_i <= 0 or
    sy_o <= 0.
    """
    p = contact_pressure(delta, r_i, r_c, r_o, E_i, nu_i, E_o, nu_o)
    _require("sy_i", sy_i > 0.0)
    _require("sy_o", sy_o > 0.0)
    stresses = stress_distributions(p, r_i, r_c, r_o)
    inner_vm = von_mises_margin(
        sy_i, stresses["inner_bore_sigma_r"], stresses["inner_bore_sigma_theta"]
    )["sigma_vm"]
    outer_vm = von_mises_margin(
        sy_o, stresses["outer_bore_sigma_r"], stresses["outer_bore_sigma_theta"]
    )["sigma_vm"]
    if inner_vm / sy_i >= outer_vm / sy_o:
        governing_member = "inner"
        sy_gov = sy_i
        vm_gov = inner_vm
    else:
        governing_member = "outer"
        sy_gov = sy_o
        vm_gov = outer_vm
    return {
        "governing_member": governing_member,
        "governing_contact_pressure": p * sy_gov / vm_gov,
        "allowable_interference": delta * sy_gov / vm_gov,
    }
