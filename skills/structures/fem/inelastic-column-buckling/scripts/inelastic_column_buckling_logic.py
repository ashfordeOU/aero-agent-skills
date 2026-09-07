"""Inelastic column buckling logic: yield-anchored Euler-Johnson tangent
column strength curve.

Whole solid, round, tube or extruded compression member in the
intermediate slenderness band. The column strength curve is the Johnson
parabola arm F_col = F_cy*(1 - F_cy*lambda**2/(4*pi**2*E)) at or below the
euler-johnson-tangent transition lambda_t = sqrt(2*pi**2*E/F_cy), and the
Euler arm F_col = pi**2*E/lambda**2 above it. Both arms return exactly
F_cy/2 at lambda_t and the parabola is tangent to the Euler hyperbola
there, the standard Johnson form of the published Euler-Johnson tangent
column strength curve. Pure Python stdlib, math only, deterministic, no
RNG, no external processes. All functions take plain SI floats (E and
F_cy in Pa, lengths in m, area in m^2, forces in N); the end-condition
effective length factor K is a plain given number (the K resolution
table belongs to the elastic buckling-analysis sibling).

Scope: whole solid sections, round or extruded tubes and extruded or
machined members whose local wall stability does not govern; linear
elastic isotropic material characterized by E and F_cy; ideally straight,
concentrically loaded column; compression only; SI units.
"""

import math

# Material registry values (Pa), shared with the crippling-analysis
# sibling of the same pack; used by the worked examples only. Every
# function takes E and f_cy as plain float arguments.
E_2024_T3 = 72.4e9      # Pa, Young modulus 2024-T3
F_CY_2024_T3 = 290.0e6  # Pa, compressive yield 2024-T3
E_7075_T6 = 71.7e9      # Pa, Young modulus 7075-T6
F_CY_7075_T6 = 462.0e6  # Pa, compressive yield 7075-T6


def effective_slenderness(k_factor, length, radius_gyration):
    """lambda = K*L/r, dimensionless, of the compression member.

    K is the effective length factor (a plain given number), L the
    physical length in m, r the radius of gyration in m. ValueError:
    any argument <= 0.
    """
    if k_factor <= 0.0 or length <= 0.0 or radius_gyration <= 0.0:
        raise ValueError("k_factor, length and radius_gyration must be positive")
    return k_factor * length / radius_gyration


def johnson_transition_slenderness(e, f_cy):
    """lambda_t = sqrt(2*pi**2*E/F_cy), dimensionless.

    The euler-johnson-tangent transition of the column strength curve:
    at lambda_t both arms return F_cy/2 and the parabola is tangent to
    the Euler hyperbola. ValueError: e <= 0 or f_cy <= 0.
    """
    if e <= 0.0 or f_cy <= 0.0:
        raise ValueError("e and f_cy must be positive")
    return math.sqrt(2.0 * math.pi**2 * e / f_cy)


def johnson_parabola_stress(e, f_cy, lam):
    """Johnson arm F_col = F_cy*(1 - F_cy*lam**2/(4*pi**2*E)) in Pa.

    The quadratic between the yield anchor F_col = F_cy at lam = 0 and
    the tangent point F_col = F_cy/2 at lambda_t, valid lam <= lambda_t.
    ValueError: e, f_cy or lam <= 0.
    """
    if e <= 0.0 or f_cy <= 0.0 or lam <= 0.0:
        raise ValueError("e, f_cy and lam must be positive")
    return f_cy * (1.0 - f_cy * lam**2 / (4.0 * math.pi**2 * e))


def euler_arm_stress(e, lam):
    """Euler arm F_col = pi**2*E/lam**2 in Pa, valid lam > lambda_t.

    The elastic hyperbola of the same column strength curve, coincident
    with the Euler stress of the slender column in the elastic band.
    ValueError: e or lam <= 0.
    """
    if e <= 0.0 or lam <= 0.0:
        raise ValueError("e and lam must be positive")
    return math.pi**2 * e / lam**2


def column_regime(e, f_cy, lam):
    """Regime classification of the column strength curve.

    "johnson" at or below lambda_t, "euler" above. At the exact float
    equality the arms agree to roundoff, so the tie classification is
    inert. ValueError: e or f_cy <= 0, or lam <= 0.
    """
    lam_t = johnson_transition_slenderness(e, f_cy)
    if lam <= 0.0:
        raise ValueError("lam must be positive")
    return "johnson" if lam <= lam_t else "euler"


def column_strength_allowable(e, f_cy, lam):
    """Inelastic column allowable stress F_col in Pa by regime.

    Johnson parabola arm at or below lambda_t, Euler arm above: the
    F_col of the yield-anchored column strength curve. ValueError as
    the two arms.
    """
    if column_regime(e, f_cy, lam) == "johnson":
        return johnson_parabola_stress(e, f_cy, lam)
    return euler_arm_stress(e, lam)


def column_capacity(e, f_cy, lam, area):
    """Column capacity P_col = F_col*A in N of the gross section area A.

    ValueError: area <= 0, plus the curve ValueErrors.
    """
    if area <= 0.0:
        raise ValueError("area must be positive")
    return column_strength_allowable(e, f_cy, lam) * area


def margin_of_safety(allowable, applied):
    """MS = allowable/applied - 1, pass when MS >= 0.

    Against the applied axial compression applied in N. ValueError:
    allowable <= 0 or applied <= 0.
    """
    if allowable <= 0.0 or applied <= 0.0:
        raise ValueError("allowable and applied must be positive")
    return allowable / applied - 1.0


def column_check(e, f_cy, lam, area, applied_load):
    """Full inelastic column check in one call.

    Returns a dict with keys "lambda_t" (float), "regime" ("johnson" or
    "euler"), "F_col" (Pa), "P_col" (N), "margin" (float) and "verdict"
    ("pass" when margin >= 0, else "fail"). ValueErrors of all component
    functions.
    """
    lam_t = johnson_transition_slenderness(e, f_cy)
    regime = column_regime(e, f_cy, lam)
    f_col = column_strength_allowable(e, f_cy, lam)
    p_col = column_capacity(e, f_cy, lam, area)
    margin = margin_of_safety(p_col, applied_load)
    return {"lambda_t": lam_t, "regime": regime, "F_col": f_col,
            "P_col": p_col, "margin": margin,
            "verdict": "pass" if margin >= 0.0 else "fail"}


def johnson_slope(e, f_cy, lam):
    """Closed-form d/dlam of the Johnson arm: -F_cy**2*lam/(2*pi**2*E).

    Used by the slope-tangency identity at lambda_t. Pa per unit
    slenderness. ValueError: e, f_cy or lam <= 0.
    """
    if e <= 0.0 or f_cy <= 0.0 or lam <= 0.0:
        raise ValueError("e, f_cy and lam must be positive")
    return -f_cy**2 * lam / (2.0 * math.pi**2 * e)


def euler_slope(e, lam):
    """Closed-form d/dlam of the Euler arm: -2*pi**2*E/lam**3.

    Used by the slope-tangency identity at lambda_t. ValueError: e or
    lam <= 0.
    """
    if e <= 0.0 or lam <= 0.0:
        raise ValueError("e and lam must be positive")
    return -2.0 * math.pi**2 * e / lam**3
