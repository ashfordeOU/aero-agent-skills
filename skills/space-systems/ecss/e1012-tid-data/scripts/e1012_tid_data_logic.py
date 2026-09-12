"""
TID degradation prediction from experimental dose-response data.
ECSS-E-ST-10-12C §7.6-7.7 — component and material degradation analysis.
"""

VALID_DIRECTIONS = ("increasing", "decreasing")


def interpolate_degradation(test_data, dose_krad):
    """
    Interpolate a parameter value from measured dose-response test data.

    test_data : sequence of (dose_krad, parameter_value) pairs.
    dose_krad : query dose in krad(Si); must be >= 0 and within the tested range.

    Returns the linearly interpolated parameter value.
    Raises ValueError for negative dose, empty data, or dose exceeding test range.
    """
    if not test_data:
        raise ValueError("test_data is empty — no dose-response measurements provided")
    if dose_krad < 0:
        raise ValueError(
            f"dose_krad must be non-negative; got {dose_krad}"
        )

    sorted_data = sorted(test_data, key=lambda p: p[0])
    doses = [p[0] for p in sorted_data]
    values = [p[1] for p in sorted_data]

    max_dose = doses[-1]
    if dose_krad > max_dose:
        raise ValueError(
            f"dose_krad {dose_krad} exceeds the maximum measured test dose "
            f"{max_dose} krad — extrapolation beyond the tested range is not "
            "permitted; extend testing or obtain a formal engineering waiver"
        )

    if dose_krad in doses:
        return values[doses.index(dose_krad)]

    for i in range(len(doses) - 1):
        if doses[i] <= dose_krad <= doses[i + 1]:
            frac = (dose_krad - doses[i]) / (doses[i + 1] - doses[i])
            return values[i] + frac * (values[i + 1] - values[i])

    return values[-1]


def apply_eldrs_correction(base_value, eldrs_factor, direction):
    """
    Apply an enhanced low dose-rate sensitivity (ELDRS) correction factor.

    Bipolar devices can exhibit greater degradation at the low dose rates
    encountered on-orbit than at the high dose rates used in laboratory
    testing.  The ELDRS factor (>= 1.0) scales the interpolated lab value
    to the worst-case low-dose-rate response.

    base_value   : parameter value from dose-response interpolation.
    eldrs_factor : ratio of low- to high-dose-rate degradation (>= 1.0).
    direction    : "increasing" — parameter worsens by rising (e.g. leakage current);
                   "decreasing" — parameter worsens by falling (e.g. gain, output voltage).

    Returns the ELDRS-corrected worst-case parameter value.
    Raises ValueError for factor < 1.0 or unrecognised direction.
    """
    if direction not in VALID_DIRECTIONS:
        raise ValueError(
            f"direction must be one of {VALID_DIRECTIONS}; got {direction!r}"
        )
    if eldrs_factor < 1.0:
        raise ValueError(
            f"eldrs_factor must be >= 1.0 (it is a ratio >= 1 of low- to "
            f"high-dose-rate degradation); got {eldrs_factor}"
        )

    if direction == "increasing":
        return base_value * eldrs_factor
    else:
        return base_value / eldrs_factor


def apply_lot_margin(value, margin_fraction, direction):
    """
    Apply a lot-variability margin to bound worst-case performance across lots.

    value            : parameter value after ELDRS correction.
    margin_fraction  : fractional margin in [0, 1); e.g. 0.20 for a 20 % margin.
    direction        : "increasing" or "decreasing" — same convention as ELDRS.

    For an increasing parameter the worst-case value is higher, so the margin
    multiplies by (1 + fraction).  For a decreasing parameter the worst-case
    value is lower, so the margin multiplies by (1 - fraction).

    Returns the margin-adjusted worst-case parameter value.
    Raises ValueError for margin outside [0, 1) or unrecognised direction.
    """
    if direction not in VALID_DIRECTIONS:
        raise ValueError(
            f"direction must be one of {VALID_DIRECTIONS}; got {direction!r}"
        )
    if not (0.0 <= margin_fraction < 1.0):
        raise ValueError(
            f"margin_fraction must be in [0, 1); got {margin_fraction}"
        )

    if direction == "increasing":
        return value * (1.0 + margin_fraction)
    else:
        return value * (1.0 - margin_fraction)


def check_compliance(predicted_value, functional_limit, direction):
    """
    Determine whether the predicted worst-case value meets the functional limit.

    predicted_value  : worst-case value after ELDRS and lot-margin steps.
    functional_limit : maximum allowed (increasing) or minimum required (decreasing).
    direction        : "increasing" or "decreasing".

    Returns True if compliant, False if limit is violated.
    Raises ValueError for unrecognised direction.
    """
    if direction not in VALID_DIRECTIONS:
        raise ValueError(
            f"direction must be one of {VALID_DIRECTIONS}; got {direction!r}"
        )

    if direction == "increasing":
        return predicted_value <= functional_limit
    else:
        return predicted_value >= functional_limit


def compute_margin_percent(predicted_value, functional_limit, direction):
    """
    Compute the design margin as a percentage of the functional limit.

    Positive margin indicates headroom; negative margin indicates an exceedance.
    Increasing: margin = (limit - predicted) / |limit| * 100
    Decreasing: margin = (predicted - limit) / |limit| * 100

    Returns margin in percent.
    Raises ValueError for unrecognised direction or a zero functional limit.
    """
    if direction not in VALID_DIRECTIONS:
        raise ValueError(
            f"direction must be one of {VALID_DIRECTIONS}; got {direction!r}"
        )
    if functional_limit == 0.0:
        raise ValueError(
            "functional_limit must be non-zero to compute a meaningful margin percentage"
        )

    if direction == "increasing":
        return (functional_limit - predicted_value) / abs(functional_limit) * 100.0
    else:
        return (predicted_value - functional_limit) / abs(functional_limit) * 100.0


def predict_tid_degradation(
    test_data,
    design_dose_krad,
    eldrs_factor,
    lot_margin_fraction,
    functional_limit,
    direction,
):
    """
    Full TID degradation prediction pipeline per ECSS-E-ST-10-12C §7.6-7.7.

    Steps applied in order:
      1. Interpolate the dose-response curve at design_dose_krad.
      2. Apply the ELDRS correction factor.
      3. Apply the lot-variability margin.
      4. Check the result against the functional limit.
      5. Compute the design margin percentage.

    Returns a dict with keys:
      interpolated_value    - parameter value at design_dose_krad from test data
      eldrs_corrected_value - after ELDRS worst-case scaling
      lot_adjusted_value    - after lot-variability margin
      compliance            - bool; True if lot_adjusted_value meets functional_limit
      margin_percent        - float; positive = headroom, negative = exceedance
      status                - "PASS" or "FAIL"
    """
    interp = interpolate_degradation(test_data, design_dose_krad)
    eldrs_val = apply_eldrs_correction(interp, eldrs_factor, direction)
    lot_val = apply_lot_margin(eldrs_val, lot_margin_fraction, direction)
    compliant = check_compliance(lot_val, functional_limit, direction)
    margin = compute_margin_percent(lot_val, functional_limit, direction)

    return {
        "interpolated_value": interp,
        "eldrs_corrected_value": eldrs_val,
        "lot_adjusted_value": lot_val,
        "compliance": compliant,
        "margin_percent": margin,
        "status": "PASS" if compliant else "FAIL",
    }
