"""Class-II landing gear group weight regression (Raymer method, paraphrased).

Pure stdlib power-law arithmetic. Inputs are SI (kg, m, dimensionless
counts) with the stall speed kept in knots as published; the regressions
run in the published lb / in closed forms and convert at the boundary.
"""

KG_TO_LB = 1.0 / 0.45359237
M_TO_IN = 1.0 / 0.0254

ULTIMATE_OVER_LIMIT = 1.5

MAIN_LG_K = 0.0106
MAIN_LG_E_WL = 0.888
MAIN_LG_E_NL = 0.25
MAIN_LG_E_LM = 0.4
MAIN_LG_E_NMW = 0.321
MAIN_LG_E_NMSS = -0.5
MAIN_LG_E_VS = 0.1

NOSE_LG_K = 0.032
NOSE_LG_E_WL = 0.646
NOSE_LG_E_NL = 0.2
NOSE_LG_E_LN = 0.5
NOSE_LG_E_NNW = 0.45

SHOCK_STRUTS_DEFAULT = 2.0
STALL_SPEED_KTS_DEFAULT = 51.0


def _require_positive_number(value, label):
    """Raise ValueError unless value is a positive real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %s" % (label, value))


def _require_min_count(value, minimum, label):
    """Raise ValueError unless value is a number at least minimum."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if value < minimum:
        raise ValueError(
            "%s must be at least %s, got %s" % (label, minimum, value)
        )


def ultimate_landing_load_factor(n_land_limit):
    """Scale the limit landing load factor to the ultimate value (FAR-25.303)."""
    _require_positive_number(n_land_limit, "design limit landing load factor")
    return ULTIMATE_OVER_LIMIT * n_land_limit


def main_gear_group_weight(
    design_landing_weight_kg,
    n_land_limit,
    main_strut_length_m,
    main_wheels,
    main_shock_struts=SHOCK_STRUTS_DEFAULT,
    stall_speed_kts=STALL_SPEED_KTS_DEFAULT,
):
    """Main gear group mass in kg from the class-II statistical regression."""
    _require_positive_number(
        design_landing_weight_kg, "design landing weight"
    )
    _require_positive_number(
        main_strut_length_m, "main strut length"
    )
    _require_positive_number(stall_speed_kts, "stall speed")
    _require_min_count(main_wheels, 1, "number of main gear wheels")
    _require_min_count(main_shock_struts, 1, "number of main gear shock struts")
    n_ult = ultimate_landing_load_factor(n_land_limit)

    w_l_lb = design_landing_weight_kg * KG_TO_LB
    l_m_in = main_strut_length_m * M_TO_IN

    w_main_lb = (
        MAIN_LG_K
        * w_l_lb ** MAIN_LG_E_WL
        * n_ult ** MAIN_LG_E_NL
        * l_m_in ** MAIN_LG_E_LM
        * main_wheels ** MAIN_LG_E_NMW
        * main_shock_struts ** MAIN_LG_E_NMSS
        * stall_speed_kts ** MAIN_LG_E_VS
    )
    return w_main_lb / KG_TO_LB


def nose_gear_group_weight(
    design_landing_weight_kg,
    n_land_limit,
    nose_strut_length_m,
    nose_wheels,
):
    """Nose gear group mass in kg from the class-II statistical regression."""
    _require_positive_number(
        design_landing_weight_kg, "design landing weight"
    )
    _require_positive_number(
        nose_strut_length_m, "nose strut length"
    )
    _require_min_count(nose_wheels, 1, "number of nose gear wheels")
    n_ult = ultimate_landing_load_factor(n_land_limit)

    w_l_lb = design_landing_weight_kg * KG_TO_LB
    l_n_in = nose_strut_length_m * M_TO_IN

    w_nose_lb = (
        NOSE_LG_K
        * w_l_lb ** NOSE_LG_E_WL
        * n_ult ** NOSE_LG_E_NL
        * l_n_in ** NOSE_LG_E_LN
        * nose_wheels ** NOSE_LG_E_NNW
    )
    return w_nose_lb / KG_TO_LB


def landing_gear_group_total(w_main, w_nose):
    """Sum the main and nose gear group masses in kg."""
    for value, label in ((w_main, "group mass 1"), (w_nose, "group mass 2")):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a number, got %r" % (label, value))
        if value < 0:
            raise ValueError("%s must be non-negative, got %s" % (label, value))
    return w_main + w_nose


def gear_group_fraction(gear_group_total_kg, reference_weight_kg):
    """Gear group total as a fraction of a reference weight (landing weight or MTOW)."""
    _require_positive_number(reference_weight_kg, "reference weight")
    if isinstance(gear_group_total_kg, bool) or not isinstance(
        gear_group_total_kg, (int, float)
    ):
        raise ValueError(
            "gear group total must be a number, got %r" % (gear_group_total_kg,)
        )
    if gear_group_total_kg < 0:
        raise ValueError(
            "gear group total must be non-negative, got %s" % (gear_group_total_kg,)
        )
    return gear_group_total_kg / reference_weight_kg
