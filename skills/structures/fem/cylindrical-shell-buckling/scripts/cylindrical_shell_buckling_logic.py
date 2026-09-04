"""Cylindrical shell buckling logic (NASA SP-8007 empirical knockdown method).

Pure stdlib, deterministic, no RNG. Computes the elastic buckling of
unstiffened circular cylindrical shells under axial compression and
bending with the SP-8007 empirical knockdown factors, the cross-section
ovalization collapse moment, and the plasticity correction factor.

The knockdown coefficients are pinned public-domain NASA SP-8007 values
("Buckling of Thin-Walled Circular Cylinders", 1968 original / 2023 NTRS
revision 20205011530). The stresses are elastic; the plasticity
correction eta is reported separately and applied by the caller when the
material is beyond the proportional limit.

All linear dimensions are meters, all stresses/elastic moduli are Pa,
moments are N*m. Standard-module usage:

    from cylindrical_shell_buckling_logic import shell_buckling_assessment
    out = shell_buckling_assessment(70e9, 0.005, 1.5)
"""

import math

# Module constants (NASA SP-8007 pinned values).
K_AXIAL_A = 0.901   # axial knockdown coefficient (imperfection sensitivity)
K_AXIAL_B = 0.605   # axial classical coefficient = 1/sqrt(3*(1-nu^2)) at nu=0.3
K_BEND_A = 0.731    # bending knockdown coefficient
K_OVAL = 0.987      # ovalization collapse coefficient
PHI_FACTOR = 1.0 / 16.0  # knockdown exponent factor phi = (1/16)*sqrt(r/t)
NU_DEFAULT = 0.3    # default Poisson ratio
R_T_LIMIT = 1500.0  # validity guard: SP-8007 knockdowns apply below r/t ~ 1500


def curvature_parameter(radius_m, thickness_m):
    """Return phi = (1/16)*sqrt(r/t), the SP-8007 curvature parameter.

    Raises ValueError when radius or thickness is non-positive or when
    r/t >= R_T_LIMIT (the empirical knockdown validity guard).
    """
    if radius_m <= 0 or thickness_m <= 0:
        raise ValueError("radius and thickness must be positive")
    r_t = radius_m / thickness_m
    if r_t >= R_T_LIMIT:
        raise ValueError(
            "r/t = %.1f exceeds the SP-8007 validity limit of %g"
            % (r_t, R_T_LIMIT)
        )
    return PHI_FACTOR * math.sqrt(r_t)


def knockdown_axial(radius_m, thickness_m):
    """Return gamma_a = 1 - 0.901*(1 - exp(-phi)), axial knockdown factor.

    Monotonic decreasing in r/t and bounded in (0, 1). ValueErrors of
    curvature_parameter propagate.
    """
    phi = curvature_parameter(radius_m, thickness_m)
    return 1.0 - K_AXIAL_A * (1.0 - math.exp(-phi))


def knockdown_bending(radius_m, thickness_m):
    """Return gamma_b = 1 - 0.731*(1 - exp(-phi)), bending knockdown factor.

    Monotonic decreasing in r/t and bounded in (0, 1). ValueErrors of
    curvature_parameter propagate.
    """
    phi = curvature_parameter(radius_m, thickness_m)
    return 1.0 - K_BEND_A * (1.0 - math.exp(-phi))


def _validate_stress_inputs(e_mod_pa, thickness_m, radius_m, gamma):
    """Shared guard for stress/moment functions; returns resolved gamma."""
    if e_mod_pa <= 0 or thickness_m <= 0 or radius_m <= 0:
        raise ValueError("modulus, thickness and radius must be positive")
    if radius_m / thickness_m >= R_T_LIMIT:
        raise ValueError(
            "r/t = %.1f exceeds the SP-8007 validity limit of %g"
            % (radius_m / thickness_m, R_T_LIMIT)
        )
    if gamma is None:
        return None
    if not (0.0 < gamma <= 1.0):
        raise ValueError("knockdown factor gamma must lie in (0, 1]")
    return gamma


def axial_critical_stress(e_mod_pa, thickness_m, radius_m, gamma=None):
    """Return sigma_cr = 0.605*gamma*E*t/r, axial critical buckling stress.

    When gamma is None the axial knockdown factor for the geometry is
    computed internally. ValueErrors on non-positive inputs and on
    r/t >= R_T_LIMIT.
    """
    resolved = _validate_stress_inputs(e_mod_pa, thickness_m, radius_m, gamma)
    if resolved is None:
        resolved = knockdown_axial(radius_m, thickness_m)
    return K_AXIAL_B * resolved * e_mod_pa * thickness_m / radius_m


def bending_critical_moment(e_mod_pa, thickness_m, radius_m, gamma=None):
    """Return M_cr = pi*0.605*gamma*E*t**2*r, bending bifurcation moment.

    Derivation: the axial critical stress sigma_cr = 0.605*gamma*E*t/r
    acting over the full wall section (area pi*r*t) at the extreme fiber
    arm r gives M = sigma_cr * (pi*r*t) * r. When gamma is None the
    bending knockdown factor is computed internally. ValueErrors on
    non-positive inputs and on r/t >= R_T_LIMIT.
    """
    resolved = _validate_stress_inputs(e_mod_pa, thickness_m, radius_m, gamma)
    if resolved is None:
        resolved = knockdown_bending(radius_m, thickness_m)
    return (
        math.pi
        * K_AXIAL_B
        * resolved
        * e_mod_pa
        * thickness_m**2
        * radius_m
    )


def ovalization_collapse_moment(e_mod_pa, thickness_m, radius_m, nu=NU_DEFAULT):
    """Return M_ov = 0.987*E*r*t**2/sqrt(1-nu**2), ovalization collapse.

    ValueErrors on non-positive inputs, nu outside (-1, 1), and on
    r/t >= R_T_LIMIT.
    """
    if e_mod_pa <= 0 or thickness_m <= 0 or radius_m <= 0:
        raise ValueError("modulus, thickness and radius must be positive")
    if not (-1.0 < nu < 1.0):
        raise ValueError("Poisson ratio nu must lie in (-1, 1)")
    if radius_m / thickness_m >= R_T_LIMIT:
        raise ValueError(
            "r/t = %.1f exceeds the SP-8007 validity limit of %g"
            % (radius_m / thickness_m, R_T_LIMIT)
        )
    return K_OVAL * e_mod_pa * radius_m * thickness_m**2 / math.sqrt(1.0 - nu**2)


def plasticity_correction(e_sec_pa, e_tan_pa, e_mod_pa):
    """Return eta = sqrt(E_sec*E_tan)/E, the plasticity correction factor.

    Values are the secant and tangent moduli at the acting stress over
    the elastic modulus. When all three are equal eta = 1.0. ValueErrors
    on non-positive inputs.
    """
    if e_sec_pa <= 0 or e_tan_pa <= 0 or e_mod_pa <= 0:
        raise ValueError("secant, tangent and elastic moduli must be positive")
    return math.sqrt(e_sec_pa * e_tan_pa) / e_mod_pa


def shell_buckling_assessment(
    e_mod_pa,
    thickness_m,
    radius_m,
    nu=NU_DEFAULT,
    e_sec_pa=None,
    e_tan_pa=None,
):
    """Return the full curved-shell stability dict for a cylinder geometry.

    Dict keys: radius_to_thickness, curvature_parameter, gamma_axial,
    gamma_bending, sigma_cr_axial_pa, m_cr_bending_Nm,
    m_cr_ovalization_Nm, governing, eta_plasticity. governing is
    "bifurcation" when m_cr_bending < m_cr_ovalization, else
    "ovalization". eta_plasticity is None when e_sec or e_tan is None.
    ValueErrors of the component functions propagate.
    """
    sigma_cr = axial_critical_stress(e_mod_pa, thickness_m, radius_m)
    m_cr_bend = bending_critical_moment(e_mod_pa, thickness_m, radius_m)
    m_ov = ovalization_collapse_moment(e_mod_pa, thickness_m, radius_m, nu)
    eta = None
    if e_sec_pa is not None and e_tan_pa is not None:
        eta = plasticity_correction(e_sec_pa, e_tan_pa, e_mod_pa)
    return {
        "radius_to_thickness": radius_m / thickness_m,
        "curvature_parameter": curvature_parameter(radius_m, thickness_m),
        "gamma_axial": knockdown_axial(radius_m, thickness_m),
        "gamma_bending": knockdown_bending(radius_m, thickness_m),
        "sigma_cr_axial_pa": sigma_cr,
        "m_cr_bending_Nm": m_cr_bend,
        "m_cr_ovalization_Nm": m_ov,
        "governing": "bifurcation" if m_cr_bend < m_ov else "ovalization",
        "eta_plasticity": eta,
    }
