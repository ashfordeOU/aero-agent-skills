"""Gibson and Ashby hexagonal honeycomb core micromechanics.

Predicts the equivalent mechanical properties of an aerospace hexagonal
honeycomb core from the cell geometry and the foil material properties.
Pure stdlib (math only), closed form, deterministic, no RNG, no tables.
"""

import math

_T_L_MSG = "wall thickness to edge-length ratio t/l must be in (0, 1), got {0}"
_H_L_MSG = "cell aspect ratio h/l must be a positive number, got {0}"
_THETA_MSG = "cell angle theta must be in (0, 90) degrees, got {0}"
_ES_MSG = "foil modulus E_s must be a positive number, got {0}"
_NU_MSG = "foil Poisson ratio nu_s must be in [0, 0.5), got {0}"
_RHOS_MSG = "foil density rho_s must be a positive number, got {0}"
_GS_MSG = "foil shear modulus G_s must be a positive number, got {0}"


def _check_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label.format(value))


def _validate_t_l(t_l):
    _check_number(t_l, _T_L_MSG)
    if not (0.0 < t_l < 1.0):
        raise ValueError(_T_L_MSG.format(t_l))


def _validate_h_l(h_l):
    _check_number(h_l, _H_L_MSG)
    if not (h_l > 0.0):
        raise ValueError(_H_L_MSG.format(h_l))


def _validate_theta_deg(theta_deg):
    _check_number(theta_deg, _THETA_MSG)
    if not (0.0 < theta_deg < 90.0):
        raise ValueError(_THETA_MSG.format(theta_deg))


def _validate_geometry(t_l, h_l, theta_deg):
    _validate_t_l(t_l)
    _validate_h_l(h_l)
    _validate_theta_deg(theta_deg)


def _validate_positive(value, label):
    _check_number(value, label)
    if not (value > 0.0):
        raise ValueError(label.format(value))


def shear_modulus_isotropic(e_s, nu_s):
    """Derive the isotropic foil shear modulus G_s = E_s / (2 (1 + nu_s))."""
    _validate_positive(e_s, _ES_MSG)
    _check_number(nu_s, _NU_MSG)
    if not (0.0 <= nu_s < 0.5):
        raise ValueError(_NU_MSG.format(nu_s))
    return e_s / (2.0 * (1.0 + nu_s))


def relative_density(t_l, h_l, theta_deg):
    """Relative density rho*/rho_s of the double-thickness-wall hex cell."""
    _validate_geometry(t_l, h_l, theta_deg)
    theta = math.radians(theta_deg)
    return (t_l * (h_l + 2.0)) / (2.0 * math.cos(theta) * (h_l + math.sin(theta)))


def core_density(rho_s, t_l, h_l, theta_deg):
    """Core density rho* = rho_s * (rho*/rho_s), kg/m^3."""
    _validate_positive(rho_s, _RHOS_MSG)
    return rho_s * relative_density(t_l, h_l, theta_deg)


def compressive_modulus_e3(e_s, t_l, h_l, theta_deg):
    """Stabilized out-of-plane compressive modulus E3 = E_s * (rho*/rho_s), Pa."""
    _validate_positive(e_s, _ES_MSG)
    return e_s * relative_density(t_l, h_l, theta_deg)


def shear_modulus_g13(g_s, t_l, h_l, theta_deg):
    """Out-of-plane shear modulus G13 in the ribbon plane, Pa."""
    _validate_positive(g_s, _GS_MSG)
    _validate_geometry(t_l, h_l, theta_deg)
    theta = math.radians(theta_deg)
    return g_s * (t_l * math.cos(theta)) / (h_l + math.sin(theta))


def shear_modulus_g23(g_s, t_l, h_l, theta_deg):
    """Out-of-plane shear modulus G23 in the transverse plane, Pa."""
    _validate_positive(g_s, _GS_MSG)
    _validate_geometry(t_l, h_l, theta_deg)
    theta = math.radians(theta_deg)
    numerator = t_l * (h_l + math.sin(theta))
    denominator = (h_l ** 2) * math.cos(theta) * (2.0 * h_l + 1.0)
    return g_s * numerator / denominator


def inplane_modulus_e1(e_s, t_l, h_l, theta_deg):
    """In-plane cell-wall-bending modulus E1*, Pa (scales with (t/l)^3)."""
    _validate_positive(e_s, _ES_MSG)
    _validate_geometry(t_l, h_l, theta_deg)
    theta = math.radians(theta_deg)
    numerator = (t_l ** 3) * math.cos(theta)
    denominator = (h_l + math.sin(theta)) * (math.sin(theta) ** 2)
    return e_s * numerator / denominator


def inplane_modulus_e2(e_s, t_l, h_l, theta_deg):
    """In-plane cell-wall-bending modulus E2*, Pa (scales with (t/l)^3)."""
    _validate_positive(e_s, _ES_MSG)
    _validate_geometry(t_l, h_l, theta_deg)
    theta = math.radians(theta_deg)
    numerator = (t_l ** 3) * (h_l + math.sin(theta))
    denominator = math.cos(theta) ** 3
    return e_s * numerator / denominator


def inplane_shear_modulus_g12(e_s, t_l, h_l, theta_deg):
    """In-plane cell-wall-bending shear modulus G12*, Pa (scales with (t/l)^3)."""
    _validate_positive(e_s, _ES_MSG)
    _validate_geometry(t_l, h_l, theta_deg)
    theta = math.radians(theta_deg)
    numerator = (t_l ** 3) * (h_l + math.sin(theta))
    denominator = (h_l ** 2) * (1.0 + 2.0 * h_l) * math.cos(theta)
    return e_s * numerator / denominator


def honeycomb_core_properties(e_s, nu_s, rho_s, t_l, h_l, theta_deg, g_s=None):
    """One-shot report of the equivalent honeycomb core properties.

    When g_s is None the foil shear modulus is derived with
    shear_modulus_isotropic(e_s, nu_s); an explicit g_s is validated and
    used as given.
    """
    _validate_positive(e_s, _ES_MSG)
    _validate_positive(rho_s, _RHOS_MSG)
    if g_s is None:
        g_s = shear_modulus_isotropic(e_s, nu_s)
    else:
        _validate_positive(g_s, _GS_MSG)

    rel_density = relative_density(t_l, h_l, theta_deg)
    e3 = e_s * rel_density
    g13 = shear_modulus_g13(g_s, t_l, h_l, theta_deg)
    g23 = shear_modulus_g23(g_s, t_l, h_l, theta_deg)
    e1 = inplane_modulus_e1(e_s, t_l, h_l, theta_deg)
    e2 = inplane_modulus_e2(e_s, t_l, h_l, theta_deg)
    g12 = inplane_shear_modulus_g12(e_s, t_l, h_l, theta_deg)

    return {
        "relative_density": rel_density,
        "core_density": rho_s * rel_density,
        "e3": e3,
        "g13": g13,
        "g23": g23,
        "e1": e1,
        "e2": e2,
        "g12": g12,
        "e3_over_es": e3 / e_s,
        "g13_over_gs": g13 / g_s,
        "g23_over_gs": g23 / g_s,
    }
