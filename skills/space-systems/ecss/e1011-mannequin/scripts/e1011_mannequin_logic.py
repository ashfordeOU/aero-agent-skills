"""
Electronic mannequin / digital human model (DHM) verification logic.
Implements fit, reach, and visibility checks for crewed spacecraft
workstations per ECSS-E-ST-10-11C §4.5.2.

Stdlib only — no third-party dependencies.
All functions are deterministic and offline.
"""

# Anthropometric bounding table: stature and functional reach (mm)
# by (sex, percentile).  Values represent representative population bounds
# used for design verification — NOT verbatim ECSS text.
_ANTHROPOMETRY = {
    ("male",   5):  {"stature_mm": 1630, "functional_reach_mm": 640},
    ("male",  50):  {"stature_mm": 1755, "functional_reach_mm": 730},
    ("male",  95):  {"stature_mm": 1880, "functional_reach_mm": 820},
    ("female", 5):  {"stature_mm": 1505, "functional_reach_mm": 585},
    ("female", 50): {"stature_mm": 1620, "functional_reach_mm": 665},
    ("female", 95): {"stature_mm": 1735, "functional_reach_mm": 750},
}

_VALID_SEXES = frozenset({"male", "female"})
_VALID_PERCENTILES = frozenset({5, 50, 95})
_VALID_CHECK_TYPES = frozenset({"fit", "reach", "visibility"})


def get_anthropometry(sex: str, percentile: int) -> dict:
    """Return a copy of the anthropometric data for the given sex/percentile."""
    if sex not in _VALID_SEXES:
        raise ValueError(
            f"sex must be one of {sorted(_VALID_SEXES)!r}, got {sex!r}"
        )
    if percentile not in _VALID_PERCENTILES:
        raise ValueError(
            f"percentile must be one of {sorted(_VALID_PERCENTILES)}, got {percentile}"
        )
    return dict(_ANTHROPOMETRY[(sex, percentile)])


def check_fit(
    clearance_mm: float,
    stature_mm: float,
    margin_mm: float = 50.0,
) -> dict:
    """
    Verify that the available clearance exceeds mannequin stature by at least
    the required margin.

    Returns a dict:
        pass           – True when margin_mm >= required
        margin_mm      – actual clearance minus stature
        required_margin_mm – the threshold supplied
    """
    if clearance_mm <= 0:
        raise ValueError(
            f"clearance_mm must be positive, got {clearance_mm}"
        )
    if stature_mm <= 0:
        raise ValueError(
            f"stature_mm must be positive, got {stature_mm}"
        )
    if margin_mm < 0:
        raise ValueError(
            f"margin_mm must be non-negative, got {margin_mm}"
        )

    actual_margin = clearance_mm - stature_mm
    return {
        "pass": actual_margin >= margin_mm,
        "margin_mm": actual_margin,
        "required_margin_mm": margin_mm,
    }


def check_reach(
    target_distance_mm: float,
    functional_reach_mm: float,
) -> dict:
    """
    Verify that the target is within the mannequin's functional reach envelope.

    target_distance_mm   – distance from shoulder reference point to target
    functional_reach_mm  – population-specific functional reach (not full arm length)

    Returns a dict:
        pass          – True when target_distance <= functional_reach
        shortfall_mm  – amount by which target exceeds reach (0 when passing)
    """
    if target_distance_mm <= 0:
        raise ValueError(
            f"target_distance_mm must be positive, got {target_distance_mm}"
        )
    if functional_reach_mm <= 0:
        raise ValueError(
            f"functional_reach_mm must be positive, got {functional_reach_mm}"
        )

    shortfall = target_distance_mm - functional_reach_mm
    return {
        "pass": shortfall <= 0,
        "shortfall_mm": max(0.0, shortfall),
    }


def check_visibility(
    line_of_sight_angle_deg: float,
    obstruction_present: bool,
    max_eye_rotation_deg: float = 55.0,
) -> dict:
    """
    Verify that a display/indicator is within the comfortable visibility cone
    AND has an unobstructed sightline.

    line_of_sight_angle_deg – angle from the forward eye axis to the target
    obstruction_present     – True if a structural element blocks the sightline
    max_eye_rotation_deg    – cone half-angle limit (default 55 deg)

    Returns a dict:
        pass               – True only when within cone AND no obstruction
        within_cone        – angle check result
        obstruction        – obstruction flag
        angle_deg          – the supplied angle
        max_eye_rotation_deg – the limit used
    """
    if line_of_sight_angle_deg < 0:
        raise ValueError(
            f"line_of_sight_angle_deg must be non-negative, got {line_of_sight_angle_deg}"
        )
    if max_eye_rotation_deg <= 0:
        raise ValueError(
            f"max_eye_rotation_deg must be positive, got {max_eye_rotation_deg}"
        )

    within_cone = line_of_sight_angle_deg <= max_eye_rotation_deg
    return {
        "pass": within_cone and not obstruction_present,
        "within_cone": within_cone,
        "obstruction": obstruction_present,
        "angle_deg": line_of_sight_angle_deg,
        "max_eye_rotation_deg": max_eye_rotation_deg,
    }


def select_bounding_cases(checks: list) -> list:
    """
    Return the (sex, percentile) pairs that must be verified for the given
    set of check types.

    Mapping (per §4.5.2 bounding logic):
        fit        → [('male', 95)]           largest body
        reach      → [('female', 5)]          smallest reach
        visibility → [('male', 95), ('female', 5)]  both eye-point extremes

    Returns a sorted list of unique (sex, percentile) tuples.
    """
    for c in checks:
        if c not in _VALID_CHECK_TYPES:
            raise ValueError(
                f"Unknown check type {c!r}; valid: {sorted(_VALID_CHECK_TYPES)}"
            )

    populations: set = set()
    if "fit" in checks:
        populations.add(("male", 95))
    if "reach" in checks:
        populations.add(("female", 5))
    if "visibility" in checks:
        populations.add(("male", 95))
        populations.add(("female", 5))

    return sorted(populations)


def run_mannequin_verification(
    clearance_mm: float,
    target_distance_mm: float,
    line_of_sight_angle_deg: float,
    obstruction_present: bool,
    sex: str = "male",
    percentile: int = 95,
    fit_margin_mm: float = 50.0,
    max_eye_rotation_deg: float = 55.0,
) -> dict:
    """
    Run a complete workstation verification (fit + reach + visibility) for
    a single anthropometric bounding case.

    Returns a dict with per-check detail sub-dicts and an overall 'pass' flag.
    """
    anthro = get_anthropometry(sex, percentile)

    fit_result = check_fit(clearance_mm, anthro["stature_mm"], fit_margin_mm)
    reach_result = check_reach(target_distance_mm, anthro["functional_reach_mm"])
    vis_result = check_visibility(
        line_of_sight_angle_deg, obstruction_present, max_eye_rotation_deg
    )

    overall_pass = (
        fit_result["pass"]
        and reach_result["pass"]
        and vis_result["pass"]
    )

    return {
        "sex": sex,
        "percentile": percentile,
        "stature_mm": anthro["stature_mm"],
        "functional_reach_mm": anthro["functional_reach_mm"],
        "fit": fit_result,
        "reach": reach_result,
        "visibility": vis_result,
        "pass": overall_pass,
    }
