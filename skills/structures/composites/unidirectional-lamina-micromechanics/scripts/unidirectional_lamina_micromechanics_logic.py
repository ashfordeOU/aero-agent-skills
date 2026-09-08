"""Constituent-to-lamina micromechanics for a unidirectional composite ply.

Predicts the four lamina engineering constants E1, nu12, E2, G12 (plus
density) of a unidirectional lamina from the fiber and matrix constituent
properties and the fiber volume fraction, by the rule of mixtures (E1,
nu12, density) and the Halpin-Tsai closed form (E2, G12) with the standard
circular-fiber shape factors. Also produces the Voigt/Reuss and
Hashin-Shtrikman bound bands used to verify the closed-form predictions.
Pure stdlib, deterministic closed-form arithmetic only.
"""

import math

XI_E2 = 2.0
XI_G12 = 1.0


def _reject_bool(value, label):
    """Raise ValueError if value is a bool (bools pass isinstance int checks)."""
    if isinstance(value, bool):
        raise ValueError("{} must be a positive number, got {}".format(label, value))


def _require_positive_modulus(value, label):
    """Raise ValueError unless value is a positive real number."""
    _reject_bool(value, label)
    if not isinstance(value, (int, float)) or value <= 0.0:
        raise ValueError("{} must be a positive number, got {}".format(label, value))
    return float(value)


def _require_poisson(value, label):
    """Raise ValueError unless value is in [0, 0.5)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0.0 or value >= 0.5:
        raise ValueError("{} must be in [0, 0.5), got {}".format(label, value))
    return float(value)


def _require_fraction(value, label="fiber volume fraction"):
    """Raise ValueError unless value is in [0, 1] (and not a bool)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0.0 or value > 1.0:
        raise ValueError("{} must be in [0, 1], got {}".format(label, value))
    return float(value)


def shear_modulus_isotropic(e, nu):
    """Isotropic shear modulus G = e / (2 (1 + nu)) for a matrix material."""
    e = _require_positive_modulus(e, "modulus")
    nu = _require_poisson(nu, "poisson ratio")
    return e / (2.0 * (1.0 + nu))


def e1_longitudinal(e_f, e_m, v_f):
    """Longitudinal modulus E1 by the rule of mixtures (exact CCA value)."""
    e_f = _require_positive_modulus(e_f, "fiber modulus E_f")
    e_m = _require_positive_modulus(e_m, "matrix modulus E_m")
    v_f = _require_fraction(v_f)
    return v_f * e_f + (1.0 - v_f) * e_m


def nu12_major(nu_f, nu_m, v_f):
    """Major Poisson ratio nu12 by the rule of mixtures (exact CCA value)."""
    nu_f = _require_poisson(nu_f, "fiber major Poisson ratio nu_f")
    nu_m = _require_poisson(nu_m, "matrix Poisson ratio nu_m")
    v_f = _require_fraction(v_f)
    return v_f * nu_f + (1.0 - v_f) * nu_m


def _halpin_tsai(p_reinforcement, p_matrix, v_f, xi):
    """Shared Halpin-Tsai closed form: eta = (Mr - 1) / (Mr + xi)."""
    mr = p_reinforcement / p_matrix
    eta = (mr - 1.0) / (mr + xi)
    return p_matrix * (1.0 + xi * eta * v_f) / (1.0 - eta * v_f)


def e2_halpin_tsai(e_ft, e_m, v_f, xi=XI_E2):
    """Transverse modulus E2, Halpin-Tsai closed form on the fiber transverse modulus."""
    e_ft = _require_positive_modulus(e_ft, "fiber transverse modulus E_fT")
    e_m = _require_positive_modulus(e_m, "matrix modulus E_m")
    v_f = _require_fraction(v_f)
    xi = _require_positive_modulus(xi, "shape factor xi")
    return _halpin_tsai(e_ft, e_m, v_f, xi)


def g12_halpin_tsai(g_f, g_m, v_f, xi=XI_G12):
    """In-plane shear modulus G12, Halpin-Tsai closed form on the fiber shear modulus."""
    g_f = _require_positive_modulus(g_f, "fiber shear modulus G_f")
    g_m = _require_positive_modulus(g_m, "matrix shear modulus G_m")
    v_f = _require_fraction(v_f)
    xi = _require_positive_modulus(xi, "shape factor xi")
    return _halpin_tsai(g_f, g_m, v_f, xi)


def e2_reuss_lower(e_ft, e_m, v_f):
    """E2 Reuss (iso-stress) lower bound: inverse rule of mixtures."""
    e_ft = _require_positive_modulus(e_ft, "fiber transverse modulus E_fT")
    e_m = _require_positive_modulus(e_m, "matrix modulus E_m")
    v_f = _require_fraction(v_f)
    v_m = 1.0 - v_f
    return 1.0 / (v_f / e_ft + v_m / e_m)


def e2_voigt_upper(e_ft, e_m, v_f):
    """E2 Voigt (iso-strain) upper bound: rule of mixtures."""
    e_ft = _require_positive_modulus(e_ft, "fiber transverse modulus E_fT")
    e_m = _require_positive_modulus(e_m, "matrix modulus E_m")
    v_f = _require_fraction(v_f)
    return v_f * e_ft + (1.0 - v_f) * e_m


def g12_reuss_lower(g_f, g_m, v_f):
    """G12 Reuss (iso-stress) lower bound: inverse rule of mixtures."""
    g_f = _require_positive_modulus(g_f, "fiber shear modulus G_f")
    g_m = _require_positive_modulus(g_m, "matrix shear modulus G_m")
    v_f = _require_fraction(v_f)
    v_m = 1.0 - v_f
    return 1.0 / (v_f / g_f + v_m / g_m)


def g12_voigt_upper(g_f, g_m, v_f):
    """G12 Voigt (iso-strain) upper bound: rule of mixtures."""
    g_f = _require_positive_modulus(g_f, "fiber shear modulus G_f")
    g_m = _require_positive_modulus(g_m, "matrix shear modulus G_m")
    v_f = _require_fraction(v_f)
    return v_f * g_f + (1.0 - v_f) * g_m


def rho_composite(rho_f, rho_m, v_f):
    """Composite density by the rule of mixtures."""
    rho_f = _require_positive_modulus(rho_f, "fiber density rho_f")
    rho_m = _require_positive_modulus(rho_m, "matrix density rho_m")
    v_f = _require_fraction(v_f)
    return v_f * rho_f + (1.0 - v_f) * rho_m


def g12_hashin_shtrikman_bounds(g_f, g_m, v_f):
    """(lower, upper) G12 anti-plane Hashin-Shtrikman band."""
    g_f = _require_positive_modulus(g_f, "fiber shear modulus G_f")
    g_m = _require_positive_modulus(g_m, "matrix shear modulus G_m")
    v_f = _require_fraction(v_f)
    if g_f <= g_m:
        raise ValueError(
            "the fiber must be the stiffer shear phase, got G_f {} with G_m {}".format(g_f, g_m))
    v_m = 1.0 - v_f
    g_lo = g_m + v_f / (1.0 / (g_f - g_m) + v_m / (2.0 * g_m))
    g_hi = g_f + v_m / (1.0 / (g_m - g_f) + v_f / (2.0 * g_f))
    return g_lo, g_hi


def _plane_strain_pair(e, nu):
    """Isotropic-equivalent shear g and plane-strain bulk modulus k from (e, nu)."""
    g = e / (2.0 * (1.0 + nu))
    k = g / (1.0 - 2.0 * nu)
    return g, k


def _e2_from_km(k, m, e1, nu12):
    """Exact transverse-isotropy conversion E2 = 4 k m E1 / (E1 (k+m) + 4 k m nu12^2)."""
    return 4.0 * k * m * e1 / (e1 * (k + m) + 4.0 * k * m * nu12 * nu12)


def e2_hashin_shtrikman_bounds(e_f, nu_f, e_ft, e_m, nu_m, v_f):
    """(lower, upper) E2 in-plane Hashin-Shtrikman band via the k*/m* bounds."""
    e_f = _require_positive_modulus(e_f, "fiber modulus E_f")
    nu_f = _require_poisson(nu_f, "fiber major Poisson ratio nu_f")
    e_ft = _require_positive_modulus(e_ft, "fiber transverse modulus E_fT")
    e_m = _require_positive_modulus(e_m, "matrix modulus E_m")
    nu_m = _require_poisson(nu_m, "matrix Poisson ratio nu_m")
    v_f = _require_fraction(v_f)

    g_m, k_m = _plane_strain_pair(e_m, nu_m)
    g_fx, k_fx = _plane_strain_pair(e_ft, nu_f)
    if k_fx <= k_m or g_fx <= g_m:
        raise ValueError(
            "the fiber must be the stiffer cross-section phase, got k_f {} with k_m {}".format(k_fx, k_m))

    v_m = 1.0 - v_f
    k_lo = k_m + v_f / (1.0 / (k_fx - k_m) + v_m / (k_m + g_m))
    k_hi = k_fx + v_m / (1.0 / (k_m - k_fx) + v_f / (k_fx + g_fx))
    m_lo = g_m + v_f / (1.0 / (g_fx - g_m) + v_m * (k_m + 2.0 * g_m) / (2.0 * g_m * (k_m + g_m)))
    m_hi = g_fx + v_m / (1.0 / (g_m - g_fx) + v_f * (k_fx + 2.0 * g_fx) / (2.0 * g_fx * (k_fx + g_fx)))

    e1 = e1_longitudinal(e_f, e_m, v_f)
    nu12 = nu12_major(nu_f, nu_m, v_f)
    e2_lo = _e2_from_km(k_lo, m_lo, e1, nu12)
    e2_hi = _e2_from_km(k_hi, m_hi, e1, nu12)
    return e2_lo, e2_hi


def unidirectional_lamina_constants(e_f, nu_f, e_ft, g_f, e_m, nu_m, v_f,
                                     rho_f=None, rho_m=None):
    """One-shot report of the lamina engineering constants and verification bands."""
    e1 = e1_longitudinal(e_f, e_m, v_f)
    nu12 = nu12_major(nu_f, nu_m, v_f)
    g_m = shear_modulus_isotropic(e_m, nu_m)
    e2 = e2_halpin_tsai(e_ft, e_m, v_f)
    g12 = g12_halpin_tsai(g_f, g_m, v_f)

    e2_reuss = e2_reuss_lower(e_ft, e_m, v_f)
    e2_voigt = e2_voigt_upper(e_ft, e_m, v_f)
    e2_hs_low, e2_hs_up = e2_hashin_shtrikman_bounds(e_f, nu_f, e_ft, e_m, nu_m, v_f)

    g12_reuss = g12_reuss_lower(g_f, g_m, v_f)
    g12_voigt = g12_voigt_upper(g_f, g_m, v_f)
    g12_hs_low, g12_hs_up = g12_hashin_shtrikman_bounds(g_f, g_m, v_f)

    result = {
        "e1": e1,
        "nu12": nu12,
        "e2": e2,
        "g12": g12,
        "e2_reuss": e2_reuss,
        "e2_voigt": e2_voigt,
        "e2_hs_low": e2_hs_low,
        "e2_hs_up": e2_hs_up,
        "g12_reuss": g12_reuss,
        "g12_voigt": g12_voigt,
        "g12_hs_low": g12_hs_low,
        "g12_hs_up": g12_hs_up,
    }
    if rho_f is not None and rho_m is not None:
        result["rho"] = rho_composite(rho_f, rho_m, v_f)
    return result
