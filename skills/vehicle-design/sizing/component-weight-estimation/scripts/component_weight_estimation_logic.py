"""Class-II statistical group-weight regressions for the airframe structure.

Predicts the wing, horizontal tail, vertical tail and fuselage group
masses from geometry and design loading using the published class-II
statistical regressions (Raymer-style, paraphrased in this module's own
notation). Pure stdlib, deterministic closed-form arithmetic only.
"""

import math

KG_TO_LB = 1.0 / 0.45359237
M_TO_FT = 1.0 / 0.3048
M2_TO_FT2 = M_TO_FT ** 2
M3_TO_FT3 = M_TO_FT ** 3
PA_TO_PSF = 1.0 / 47.88025898033584
PA_TO_PSI = 1.0 / 6894.757293168361

ULTIMATE_OVER_LIMIT = 1.5

WING_K = 0.036
WING_E_S = 0.758
WING_E_FW = 0.0035
WING_E_A = 0.6
WING_E_Q = 0.006
WING_E_LAM = 0.04
WING_E_TC = -0.3
WING_E_NW = 0.49

HT_K = 0.016
HT_E_NW = 0.414
HT_E_A = 0.168
HT_E_Q = 0.043
HT_E_S = 0.896
HT_E_TC = -0.12
HT_E_LAM = 0.02

VT_K = 0.073
VT_H_FACTOR = 0.2
VT_E_NW = 0.376
VT_E_Q = 0.122
VT_E_S = 0.873
VT_E_TC = -0.49
VT_E_A = 0.357
VT_E_LAM = 0.039

FUS_K = 0.052
FUS_E_SF = 1.086
FUS_E_NW = 0.177
FUS_E_LD = -0.072
FUS_E_Q = 0.241
FUS_PRESS_K = 11.9
FUS_E_PRESS = 0.271


def _require_positive(value, name):
    """Raise ValueError unless value is a positive number."""
    if not (isinstance(value, (int, float)) and value > 0.0):
        raise ValueError("{} must be positive, got {}".format(name, value))


def _require_below(value, bound, name, bound_text=None):
    """Raise ValueError unless value is strictly below bound."""
    if value >= bound:
        shown = bound_text if bound_text is not None else bound
        raise ValueError("{} must be below {}, got {}".format(name, shown, value))


def _check_common_geometry(nz_limit, q_pa, s_m2, ar, taper, tc, sweep_deg):
    """Shared ValueError checks for the wing and tail group regressions."""
    _require_positive(nz_limit, "design limit load factor")
    _require_positive(q_pa, "dynamic pressure")
    _require_positive(s_m2, "planform area")
    _require_positive(ar, "aspect ratio")
    _require_positive(taper, "taper ratio")
    _require_positive(tc, "thickness to chord")
    _require_below(tc, 1.0, "thickness to chord")
    _require_positive(sweep_deg, "sweep angle")
    _require_below(sweep_deg, 90.0, "sweep angle", bound_text="90 degrees")


def _ultimate_load_factor(nz_limit):
    """Ultimate load factor: the limit maneuvering factor times 1.5 (FAR-25.303)."""
    return ULTIMATE_OVER_LIMIT * nz_limit


def wing_group_weight(mtow_kg, nz_limit, q_pa, s_m2, ar, taper, tc,
                       sweep_deg, fuel_in_wing_kg):
    """Wing group mass in kg from the class-II statistical regression."""
    _require_positive(mtow_kg, "MTOW")
    _check_common_geometry(nz_limit, q_pa, s_m2, ar, taper, tc, sweep_deg)
    _require_positive(fuel_in_wing_kg, "fuel weight in the wing")

    w0_lb = mtow_kg * KG_TO_LB
    n_ult = _ultimate_load_factor(nz_limit)
    s_ft2 = s_m2 * M2_TO_FT2
    q_psf = q_pa * PA_TO_PSF
    fw_lb = fuel_in_wing_kg * KG_TO_LB
    sweep_rad = math.radians(sweep_deg)
    cos_l = math.cos(sweep_rad)

    w_lb = (WING_K * s_ft2 ** WING_E_S * fw_lb ** WING_E_FW
            * (ar / cos_l ** 2) ** WING_E_A * q_psf ** WING_E_Q
            * taper ** WING_E_LAM * (100.0 * tc / cos_l) ** WING_E_TC
            * (n_ult * w0_lb) ** WING_E_NW)
    return w_lb / KG_TO_LB


def horizontal_tail_group_weight(mtow_kg, nz_limit, q_pa, s_m2, ar, taper,
                                  tc, sweep_deg):
    """Horizontal tail group mass in kg from the class-II statistical regression."""
    _require_positive(mtow_kg, "MTOW")
    _check_common_geometry(nz_limit, q_pa, s_m2, ar, taper, tc, sweep_deg)

    w0_lb = mtow_kg * KG_TO_LB
    n_ult = _ultimate_load_factor(nz_limit)
    s_ft2 = s_m2 * M2_TO_FT2
    q_psf = q_pa * PA_TO_PSF
    sweep_rad = math.radians(sweep_deg)
    cos_l = math.cos(sweep_rad)

    w_lb = (HT_K * (n_ult * w0_lb) ** HT_E_NW
            * (ar / cos_l ** 2) ** HT_E_A * q_psf ** HT_E_Q
            * s_ft2 ** HT_E_S * (100.0 * tc / cos_l) ** HT_E_TC
            * taper ** HT_E_LAM)
    return w_lb / KG_TO_LB


def vertical_tail_group_weight(mtow_kg, nz_limit, q_pa, s_m2, ar, taper,
                                tc, sweep_deg, t_tail=0.0):
    """Vertical tail group mass in kg from the class-II statistical regression."""
    _require_positive(mtow_kg, "MTOW")
    _check_common_geometry(nz_limit, q_pa, s_m2, ar, taper, tc, sweep_deg)
    if t_tail < 0.0:
        raise ValueError("t_tail must be non-negative, got {}".format(t_tail))

    w0_lb = mtow_kg * KG_TO_LB
    n_ult = _ultimate_load_factor(nz_limit)
    s_ft2 = s_m2 * M2_TO_FT2
    q_psf = q_pa * PA_TO_PSF
    sweep_rad = math.radians(sweep_deg)
    cos_l = math.cos(sweep_rad)

    w_lb = (VT_K * (1.0 + VT_H_FACTOR * t_tail) * (n_ult * w0_lb) ** VT_E_NW
            * q_psf ** VT_E_Q * s_ft2 ** VT_E_S
            * (100.0 * tc / cos_l) ** VT_E_TC * ar ** VT_E_A
            * (taper / cos_l ** 2) ** VT_E_LAM)
    return w_lb / KG_TO_LB


def fuselage_group_weight(mtow_kg, nz_limit, q_pa, wetted_area_m2, length_m,
                           diameter_m, press_volume_m3=0.0, delta_p_pa=0.0):
    """Fuselage group mass in kg, with an additive pressurization penalty."""
    _require_positive(mtow_kg, "MTOW")
    _require_positive(nz_limit, "design limit load factor")
    _require_positive(q_pa, "dynamic pressure")
    _require_positive(wetted_area_m2, "wetted area")
    _require_positive(length_m, "fuselage length")
    _require_positive(diameter_m, "fuselage diameter")

    press_given = press_volume_m3 > 0.0
    dp_given = delta_p_pa > 0.0
    if press_given != dp_given:
        raise ValueError(
            "pressurization requires both the pressurized volume and the "
            "pressure differential, got volume {} m^3 and dp {} Pa".format(
                press_volume_m3, delta_p_pa))

    w0_lb = mtow_kg * KG_TO_LB
    n_ult = _ultimate_load_factor(nz_limit)
    sf_ft2 = wetted_area_m2 * M2_TO_FT2
    q_psf = q_pa * PA_TO_PSF
    l_over_d = length_m / diameter_m

    w_lb = (FUS_K * sf_ft2 ** FUS_E_SF * (n_ult * w0_lb) ** FUS_E_NW
            * l_over_d ** FUS_E_LD * q_psf ** FUS_E_Q)

    if press_given:
        vp_ft3 = press_volume_m3 * M3_TO_FT3
        dp_psi = delta_p_pa * PA_TO_PSI
        w_lb += FUS_PRESS_K * (vp_ft3 * dp_psi) ** FUS_E_PRESS

    return w_lb / KG_TO_LB


def airframe_group_total(w_wing, w_ht, w_vt, w_fus):
    """Sum of the four airframe structural group masses in kg."""
    for i, w in enumerate((w_wing, w_ht, w_vt, w_fus), start=1):
        if not isinstance(w, (int, float)) or w < 0.0:
            raise ValueError("group mass {} must be non-negative, got {}".format(i, w))
    return w_wing + w_ht + w_vt + w_fus
