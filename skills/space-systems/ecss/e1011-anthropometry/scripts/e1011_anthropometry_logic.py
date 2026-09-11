"""
ECSS-E-ST-10-11C §4.5.1 — Anthropometric and biomechanical design verification.

Implements deterministic, offline checks for:
  - Percentile interpolation (5th/95th linear model)
  - Physical-envelope accommodation (clearance and reach)
  - Reach-envelope compliance per direction
  - Operator-strength compliance
  - Microgravity body-dimension corrections
  - Population accommodation percentage estimation

stdlib only. No external dependencies.
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REACH_FORWARD = "forward"
REACH_SIDE = "side"
REACH_OVERHEAD = "overhead"

VALID_REACH_TYPES = frozenset([REACH_FORWARD, REACH_SIDE, REACH_OVERHEAD])

REGION_STATURE = "stature"
REGION_SEATED_HEIGHT = "seated_height"
REGION_ARM_LENGTH = "arm_length"
REGION_NONE = "none"

VALID_BODY_REGIONS = frozenset(
    [REGION_STATURE, REGION_SEATED_HEIGHT, REGION_ARM_LENGTH, REGION_NONE]
)

# Microgravity spinal-unloading corrections (fractional increase on ground value).
# Source: ECSS-E-ST-10-11C §4.5.1 paraphrase — stature and seated height
# increase ~3% due to intervertebral disc expansion in weightlessness.
_MICROGRAVITY_CORRECTIONS = {
    REGION_STATURE: 0.03,
    REGION_SEATED_HEIGHT: 0.03,
    REGION_ARM_LENGTH: 0.0,
    REGION_NONE: 0.0,
}

# Reference percentile anchors used in linear interpolation
_P_LOW = 5.0
_P_HIGH = 95.0


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class AnthropometryError(ValueError):
    """Raised when inputs violate anthropometric check preconditions."""


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def interpolate_percentile(p5, p95, target_percentile):
    """
    Return the linearly interpolated body-dimension value at *target_percentile*
    given reference values at the 5th (*p5*) and 95th (*p95*) percentile.

    Linear interpolation is the standard conservative estimate when the full
    distribution is not available (ECSS-E-ST-10-11C §4.5.1).

    Args:
        p5 (float): dimension at the 5th percentile (mm, N, or unitless).
        p95 (float): dimension at the 95th percentile.
        target_percentile (float): target percentile in the open interval (0, 100).

    Returns:
        float: interpolated dimension value.

    Raises:
        AnthropometryError: if p5 >= p95 or target_percentile is outside (0, 100).
    """
    if not (0.0 < target_percentile < 100.0):
        raise AnthropometryError(
            f"target_percentile must be in (0, 100), got {target_percentile}"
        )
    if p5 >= p95:
        raise AnthropometryError(
            f"p5 ({p5}) must be strictly less than p95 ({p95})"
        )
    fraction = (target_percentile - _P_LOW) / (_P_HIGH - _P_LOW)
    return p5 + fraction * (p95 - p5)


def check_dimension_accommodation(design_min, design_max, population_p5, population_p95):
    """
    Check whether the design envelope [*design_min*, *design_max*] accommodates
    the full target population range [*population_p5*, *population_p95*].

    For clearance-type checks the design must be at least as large as the 95th
    percentile body dimension; for minimum-opening checks it must be no larger
    than the 5th percentile. Both bounds are checked simultaneously.

    Args:
        design_min (float): smallest design dimension (mm or equivalent unit).
        design_max (float): largest design dimension.
        population_p5 (float): 5th-percentile body dimension.
        population_p95 (float): 95th-percentile body dimension.

    Returns:
        dict with keys:
            accommodated (bool): True when both shortfalls are zero.
            shortfall_low (float): amount by which design_min exceeds population_p5
                (the smallest users are too large for the minimum opening).
            shortfall_high (float): amount by which population_p95 exceeds
                design_max (the largest users exceed the maximum clearance).

    Raises:
        AnthropometryError: on invalid input ordering.
    """
    if design_min > design_max:
        raise AnthropometryError(
            f"design_min ({design_min}) must be <= design_max ({design_max})"
        )
    if population_p5 >= population_p95:
        raise AnthropometryError(
            f"population_p5 ({population_p5}) must be < population_p95 ({population_p95})"
        )

    shortfall_low = max(0.0, design_min - population_p5)
    shortfall_high = max(0.0, population_p95 - design_max)
    accommodated = shortfall_low == 0.0 and shortfall_high == 0.0

    return {
        "accommodated": accommodated,
        "shortfall_low": round(shortfall_low, 6),
        "shortfall_high": round(shortfall_high, 6),
    }


def check_reach_requirement(required_reach, reach_p5, reach_p95, reach_type):
    """
    Check whether a physical reach requirement is met by the design population.

    The 5th-percentile functional reach is the limiting value: if the smallest
    crew member cannot reach a control, the design fails. The 50th-percentile
    reach is also reported for information.

    Args:
        required_reach (float): distance from operator reference point to
            the control or object (mm).
        reach_p5 (float): 5th-percentile functional reach in the stated direction.
        reach_p95 (float): 95th-percentile functional reach.
        reach_type (str): one of REACH_FORWARD, REACH_SIDE, REACH_OVERHEAD.

    Returns:
        dict with keys:
            reach_type (str), required_reach (float), reach_p5 (float),
            reach_p50 (float), reach_p95 (float),
            reachable_by_p5 (bool), reachable_by_p50 (bool),
            shortfall_p5 (float).

    Raises:
        AnthropometryError: on invalid reach_type, non-positive required_reach,
            or invalid p5/p95 ordering.
    """
    if reach_type not in VALID_REACH_TYPES:
        raise AnthropometryError(
            f"Unknown reach_type '{reach_type}'. Valid: {sorted(VALID_REACH_TYPES)}"
        )
    if required_reach <= 0:
        raise AnthropometryError(
            f"required_reach must be positive, got {required_reach}"
        )
    if reach_p5 >= reach_p95:
        raise AnthropometryError(
            f"reach_p5 ({reach_p5}) must be < reach_p95 ({reach_p95})"
        )

    reach_p50 = interpolate_percentile(reach_p5, reach_p95, 50.0)
    reachable_by_p5 = reach_p5 >= required_reach
    reachable_by_p50 = reach_p50 >= required_reach
    shortfall_p5 = max(0.0, required_reach - reach_p5)

    return {
        "reach_type": reach_type,
        "required_reach": required_reach,
        "reach_p5": reach_p5,
        "reach_p50": round(reach_p50, 4),
        "reach_p95": reach_p95,
        "reachable_by_p5": reachable_by_p5,
        "reachable_by_p50": reachable_by_p50,
        "shortfall_p5": round(shortfall_p5, 4),
    }


def check_strength_requirement(required_force_n, strength_p5, strength_p95):
    """
    Check whether a required operator force does not exceed the 5th-percentile
    population strength capability.

    The 5th-percentile strength is the binding constraint: the design must be
    operable by the weakest expected crew member without exceeding that person's
    capability (ECSS-E-ST-10-11C §4.5.1).

    Args:
        required_force_n (float): maximum force or torque the operator must exert
            (Newtons or N·m).
        strength_p5 (float): 5th-percentile population strength capability.
        strength_p95 (float): 95th-percentile population strength capability.

    Returns:
        dict with keys:
            required_force_n, strength_p5, strength_p95,
            margin_n (float): strength_p5 - required_force_n (positive = pass),
            compliant (bool).

    Raises:
        AnthropometryError: on negative required force, non-positive strength_p5,
            or invalid p5/p95 ordering.
    """
    if required_force_n < 0:
        raise AnthropometryError(
            f"required_force_n must be non-negative, got {required_force_n}"
        )
    if strength_p5 <= 0:
        raise AnthropometryError(
            f"strength_p5 must be positive, got {strength_p5}"
        )
    if strength_p5 >= strength_p95:
        raise AnthropometryError(
            f"strength_p5 ({strength_p5}) must be < strength_p95 ({strength_p95})"
        )

    margin_n = strength_p5 - required_force_n
    compliant = margin_n >= 0.0

    return {
        "required_force_n": required_force_n,
        "strength_p5": strength_p5,
        "strength_p95": strength_p95,
        "margin_n": round(margin_n, 6),
        "compliant": compliant,
    }


def apply_microgravity_correction(ground_value_mm, body_region):
    """
    Apply a microgravity spinal-unloading correction to a ground-measured
    anthropometric dimension.

    Stature and seated height increase approximately 3% in weightlessness due
    to intervertebral disc expansion. Other dimensions are negligibly affected
    and are returned unchanged.

    Args:
        ground_value_mm (float): ground-measured dimension in mm.
        body_region (str): one of REGION_STATURE, REGION_SEATED_HEIGHT,
            REGION_ARM_LENGTH, REGION_NONE.

    Returns:
        dict with keys:
            ground_value_mm, body_region, correction_factor (float),
            corrected_value_mm (float).

    Raises:
        AnthropometryError: on unrecognised body_region or non-positive
            ground_value_mm.
    """
    if body_region not in VALID_BODY_REGIONS:
        raise AnthropometryError(
            f"Unknown body_region '{body_region}'. "
            f"Valid: {sorted(VALID_BODY_REGIONS)}"
        )
    if ground_value_mm <= 0:
        raise AnthropometryError(
            f"ground_value_mm must be positive, got {ground_value_mm}"
        )

    correction_factor = _MICROGRAVITY_CORRECTIONS[body_region]
    corrected_value_mm = ground_value_mm * (1.0 + correction_factor)

    return {
        "ground_value_mm": ground_value_mm,
        "body_region": body_region,
        "correction_factor": correction_factor,
        "corrected_value_mm": round(corrected_value_mm, 6),
    }


def compute_accommodation_percentage(design_min, design_max, population_p5, population_p95):
    """
    Estimate the fraction of the population (as a percentage) accommodated by
    a design envelope [*design_min*, *design_max*].

    Uses linear interpolation within the [p5, p95] reference band. Values
    outside that band are clipped to the 5th or 95th percentile for this
    estimate.

    Args:
        design_min (float): smallest design dimension.
        design_max (float): largest design dimension.
        population_p5 (float): 5th-percentile body dimension.
        population_p95 (float): 95th-percentile body dimension.

    Returns:
        float: estimated accommodation percentage in [0.0, 90.0].

    Raises:
        AnthropometryError: on invalid input ordering.
    """
    if design_min > design_max:
        raise AnthropometryError(
            f"design_min ({design_min}) must be <= design_max ({design_max})"
        )
    if population_p5 >= population_p95:
        raise AnthropometryError(
            f"population_p5 ({population_p5}) must be < population_p95 ({population_p95})"
        )

    span = population_p95 - population_p5

    # Effective lower bound of accommodated percentile range
    if design_min <= population_p5:
        low_pct = _P_LOW
    elif design_min >= population_p95:
        low_pct = _P_HIGH
    else:
        low_pct = _P_LOW + ((design_min - population_p5) / span) * (_P_HIGH - _P_LOW)

    # Effective upper bound of accommodated percentile range
    if design_max >= population_p95:
        high_pct = _P_HIGH
    elif design_max <= population_p5:
        high_pct = _P_LOW
    else:
        high_pct = _P_LOW + ((design_max - population_p5) / span) * (_P_HIGH - _P_LOW)

    accommodation_pct = max(0.0, high_pct - low_pct)
    return round(accommodation_pct, 4)
