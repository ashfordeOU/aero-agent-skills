"""
e1012_dd_unc_logic.py

Displacement damage (DD) assessment uncertainty budget logic per
ECSS-E-ST-10-12C §8.7.

The module implements the deterministic, checkable part of the procedure:

  1. every mandatory uncertainty source is identified and its factor
     validated (a factor is a bounding multiplier >= 1.0);
  2. the source factors are combined into a single overall multiplier by
     either the multiplicative or the root-sum-square (RSS) method;
  3. the combined multiplier is applied to the nominal proton-equivalent
     fluence to obtain the design fluence;
  4. the design fluence is checked against the device withstand fluence
     with the required design margin.

Units: fluences are proton-equivalent particles/cm^2 (p_eq/cm^2); the
uncertainty factors and the margin factor are dimensionless.

Stdlib only, offline, deterministic.
"""

import math

# The four uncertainty sources that §8.7 requires the budget to address.
MANDATORY_SOURCES = (
    "environment_model",
    "niel_scaling",
    "shielding_transport",
    "device_response",
)

COMBINATION_METHODS = ("multiplicative", "rss")

# Default design margin required of a qualified part by the radiation
# hardness assurance programme.
DEFAULT_REQUIRED_MARGIN = 2.0


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_factor(value, source):
    """
    Validate a single uncertainty factor.

    A factor is a bounding multiplier on the nominal estimate, so it must
    be a finite number >= 1.0.  A value below 1.0 would imply that the
    nominal estimate overstates the true value, which is not a
    conservative assumption for a margin check.

    Raises TypeError if value is not a number, ValueError if it is below
    1.0 or not finite.
    """
    if not _is_number(value):
        raise TypeError(
            f"uncertainty factor for '{source}' must be a number, "
            f"got {type(value).__name__}"
        )
    if math.isnan(value):
        raise ValueError(f"uncertainty factor for '{source}' must not be NaN")
    if math.isinf(value):
        raise ValueError(f"uncertainty factor for '{source}' must be finite")
    if value < 1.0:
        raise ValueError(
            f"uncertainty factor for '{source}' must be >= 1.0, got {value}"
        )
    return float(value)


def normalize_source_factors(source_factors):
    """
    Validate a {source: factor} mapping and return a normalized copy.

    Every key must be one of MANDATORY_SOURCES; an unrecognized source
    label is rejected before any factor is used, so a mislabelled source
    cannot silently enter the budget.
    """
    if not isinstance(source_factors, dict):
        raise TypeError(
            "source_factors must be a dict, "
            f"got {type(source_factors).__name__}"
        )
    if not source_factors:
        raise ValueError("source_factors must not be empty")
    normalized = {}
    for source, value in source_factors.items():
        if not isinstance(source, str):
            raise TypeError(f"source label must be a string, got {source!r}")
        if source not in MANDATORY_SOURCES:
            raise ValueError(
                f"unknown uncertainty source '{source}'; expected one of "
                f"{list(MANDATORY_SOURCES)}"
            )
        normalized[source] = validate_factor(value, source)
    return normalized


def check_required_sources(source_factors):
    """
    Return the sorted list of mandatory sources absent from the budget.

    An empty list means every required source was addressed.
    """
    if isinstance(source_factors, dict):
        present = set(source_factors)
    else:
        raise TypeError(
            "source_factors must be a dict, "
            f"got {type(source_factors).__name__}"
        )
    return sorted(set(MANDATORY_SOURCES) - present)


def compute_multiplicative_factor(source_factors):
    """
    Combine factors as their product.

    The multiplicative method is the conservative default and is used
    whenever the independence of the source pairs cannot be demonstrated.
    The result is >= every individual factor.
    """
    normalized = normalize_source_factors(source_factors)
    combined = 1.0
    for value in normalized.values():
        combined *= value
    return combined


def compute_rss_factor(source_factors):
    """
    Combine factors by root-sum-square of their excess over unity.

    combined = 1 + sqrt( sum_i (f_i - 1)^2 )

    Used only when statistical independence of the sources is documented.
    A single source reproduces its own factor; for two or more factors
    >= 1.0 the result is smaller than the multiplicative product but is
    still >= each individual factor.
    """
    normalized = normalize_source_factors(source_factors)
    excess_squares = sum((value - 1.0) ** 2 for value in normalized.values())
    return 1.0 + math.sqrt(excess_squares)


def combine_factors(source_factors, method="multiplicative"):
    """
    Combine validated source factors by the named method.

    method must be 'multiplicative' or 'rss'; anything else is rejected.
    """
    if method not in COMBINATION_METHODS:
        raise ValueError(
            f"unknown combination method '{method}'; expected one of "
            f"{list(COMBINATION_METHODS)}"
        )
    if method == "multiplicative":
        return compute_multiplicative_factor(source_factors)
    return compute_rss_factor(source_factors)


def compute_design_fluence(nominal_fluence, combined_factor):
    """
    Apply the combined uncertainty factor to the nominal equivalent
    fluence to obtain the design fluence.

    nominal_fluence must be strictly positive (p_eq/cm^2); combined_factor
    must be a valid factor >= 1.0.
    """
    if not _is_number(nominal_fluence):
        raise TypeError(
            f"nominal_fluence must be a number, got "
            f"{type(nominal_fluence).__name__}"
        )
    if nominal_fluence <= 0:
        raise ValueError(f"nominal_fluence must be positive, got {nominal_fluence}")
    factor = validate_factor(combined_factor, "combined_factor")
    return nominal_fluence * factor


def check_margin(withstand_fluence, design_fluence, required_margin=DEFAULT_REQUIRED_MARGIN):
    """
    Compare the device DD withstand fluence against the design fluence.

    margin_factor = withstand_fluence / design_fluence.

    The part passes only when the margin factor is at least
    required_margin; a margin of 1.5 when 2.0 is required is a margin
    non-compliance, not a pass.

    Returns a dict:
        status          : 'pass' | 'fail'
        margin_factor   : withstand_fluence / design_fluence
        required_margin : required_margin
        shortfall       : True when margin_factor < required_margin
    """
    if not _is_number(withstand_fluence):
        raise TypeError(
            f"withstand_fluence must be a number, got "
            f"{type(withstand_fluence).__name__}"
        )
    if not _is_number(design_fluence):
        raise TypeError(
            f"design_fluence must be a number, got "
            f"{type(design_fluence).__name__}"
        )
    if withstand_fluence <= 0:
        raise ValueError(
            f"withstand_fluence must be positive, got {withstand_fluence}"
        )
    if design_fluence <= 0:
        raise ValueError(f"design_fluence must be positive, got {design_fluence}")
    validate_factor(required_margin, "required_margin")

    margin_factor = withstand_fluence / design_fluence
    shortfall = margin_factor < required_margin
    return {
        "status": "fail" if shortfall else "pass",
        "margin_factor": margin_factor,
        "required_margin": float(required_margin),
        "shortfall": shortfall,
    }


def assemble_uncertainty_budget(
    nominal_fluence,
    source_factors,
    method,
    withstand_fluence,
    required_margin=DEFAULT_REQUIRED_MARGIN,
):
    """
    Assemble the full §8.7 uncertainty budget and its pass/fail verdict.

    Raises ValueError if any mandatory source is missing from
    source_factors, so an incomplete budget cannot be reported as a
    result.

    Returns a dict:
        sources          : normalized {source: factor}
        missing_sources  : [] on success
        method           : combination method used
        combined_factor  : overall uncertainty multiplier
        nominal_fluence  : input nominal p_eq/cm^2
        design_fluence   : nominal * combined_factor
        withstand_fluence: device DD withstand p_eq/cm^2
        required_margin  : required design margin
        margin_factor    : withstand / design
        status           : 'pass' | 'fail'
        shortfall        : True when margin_factor < required_margin
    """
    if not isinstance(source_factors, dict):
        raise TypeError(
            "source_factors must be a dict, "
            f"got {type(source_factors).__name__}"
        )
    missing = check_required_sources(source_factors)
    if missing:
        raise ValueError(
            "uncertainty budget is incomplete; missing mandatory source(s): "
            f"{missing}"
        )
    normalized = normalize_source_factors(source_factors)
    combined = combine_factors(normalized, method)
    design_fluence = compute_design_fluence(nominal_fluence, combined)
    margin = check_margin(withstand_fluence, design_fluence, required_margin)

    return {
        "sources": normalized,
        "missing_sources": missing,
        "method": method,
        "combined_factor": combined,
        "nominal_fluence": nominal_fluence,
        "design_fluence": design_fluence,
        "withstand_fluence": withstand_fluence,
        "required_margin": float(required_margin),
        "margin_factor": margin["margin_factor"],
        "status": margin["status"],
        "shortfall": margin["shortfall"],
    }
