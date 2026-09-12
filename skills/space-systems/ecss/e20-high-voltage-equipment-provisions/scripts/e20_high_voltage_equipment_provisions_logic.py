#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.10 high voltage equipment provisions
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires high voltage hardware that is
neither encapsulated nor held in a sealed pressurised enclosure to be
kept out of the ambient pressure band in which a gas discharge starts
most easily, or to be designed so operation inside that band is
survivable. This module implements the checkable part of that
provision: categorization of the operating state by ambient regime, a
Paschen gas-breakdown model for a uniform gap, the analytic minimum of
that model, the pressure window in which a given applied voltage can
strike a discharge across a given gap, an exponential
depressurisation profile with the time needed to fall clear of that
window, and the energisation-inhibit and breakdown-margin checks that
follow. It does not model surface flashover, multipactor, or the
effect of outgassing on local pressure.
"""

import math

# Paschen coefficients for air in SI form, with the secondary-emission
# coefficient of the cathode. They are model parameters, overridable
# per gas and per electrode material at every call site.
PASCHEN_A_PER_PA_M = 112.5
PASCHEN_B_V_PER_PA_M = 2737.5
SECONDARY_EMISSION_COEFFICIENT = 0.01

SEA_LEVEL_PRESSURE_PA = 101325.0

# Boundary comparisons absorb floating-point representation error only;
# the engineering limit itself is never widened.
COMPARISON_REL_TOL = 1e-9
COMPARISON_ABS_TOL = 1e-12

_BISECTION_STEPS = 200
_BRACKET_DOUBLINGS = 200

OPERATING_STATE_REGIMES = {
    "ground_ambient": "dense_gas",
    "sealed_pressurised_enclosure": "dense_gas",
    "launch_ascent_depressurisation": "transitional_pressure",
    "early_orbit_outgassing": "transitional_pressure",
    "planetary_low_pressure_atmosphere": "transitional_pressure",
    "on_orbit_vacuum": "vacuum",
    "deep_space_vacuum": "vacuum",
}

RECOGNIZED_HV_PRECAUTIONS = frozenset(
    {
        "encapsulation_potting",
        "sealed_pressurised_enclosure",
        "energisation_inhibit_below_critical_range",
        "corona_free_clearance_margin",
        "vented_enclosure_with_conductive_screen",
    }
)

_ITEM_REQUIRED_KEYS = (
    "item_id",
    "operating_state",
    "applied_voltage_v",
    "gap_m",
    "potted",
    "pressurised",
    "operating_pressure_pa",
    "energisation_inhibit_pressure_pa",
    "required_voltage_margin",
)

_PROFILE_REQUIRED_KEYS = (
    "initial_pressure_pa",
    "time_constant_s",
    "inhibit_release_time_s",
)


def _within(value, limit):
    """True when value does not exceed limit. An exact-boundary case is
    accepted even when the computed value sits a few units in the last
    place above the limit through the arithmetic that produced it."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=COMPARISON_REL_TOL, abs_tol=COMPARISON_ABS_TOL
    )


def _at_least(value, floor):
    """True when value reaches floor, absorbing representation error at
    an exact-boundary case in the same way as _within."""
    return value >= floor or math.isclose(
        value, floor, rel_tol=COMPARISON_REL_TOL, abs_tol=COMPARISON_ABS_TOL
    )


def _require_keys(record, keys, what):
    missing = [k for k in keys if k not in record]
    if missing:
        raise ValueError(
            "%s record is missing required key(s): %s"
            % (what, ", ".join(sorted(missing)))
        )


def _check_coefficients(coefficient_a, coefficient_b, secondary_emission):
    if coefficient_a <= 0:
        raise ValueError("coefficient_a must be > 0")
    if coefficient_b <= 0:
        raise ValueError("coefficient_b must be > 0")
    if secondary_emission <= 0:
        raise ValueError("secondary_emission must be > 0")


def categorize_hv_operating_state(operating_state):
    """Ambient regime for a declared high voltage operating state:
    dense_gas, transitional_pressure or vacuum. Raises ValueError for a
    state that is not a recognized clause 5.10 operating state."""
    try:
        return OPERATING_STATE_REGIMES[operating_state]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized high voltage operating state %r under "
            "E-ST-20C clause 5.10" % (operating_state,)
        )


def clause_applies(potted, pressurised):
    """True when the clause 5.10 pressure-range provision bites: the
    hardware is neither encapsulated nor held in a sealed pressurised
    enclosure, so its gas gaps see the ambient pressure directly."""
    return not potted and not pressurised


def paschen_breakdown_voltage(
    pressure_pa,
    gap_m,
    coefficient_a=PASCHEN_A_PER_PA_M,
    coefficient_b=PASCHEN_B_V_PER_PA_M,
    secondary_emission=SECONDARY_EMISSION_COEFFICIENT,
):
    """Breakdown voltage in volts across a uniform gap at a given
    ambient pressure, from the Paschen similarity model in the
    pressure-times-gap product. Returns positive infinity on the
    low-pressure side of the curve, where too few collisions occur for
    an avalanche to be sustained at any voltage the model covers.
    Raises ValueError for a non-positive pressure, gap or model
    coefficient."""
    if pressure_pa <= 0:
        raise ValueError("pressure_pa must be > 0")
    if gap_m <= 0:
        raise ValueError("gap_m must be > 0")
    _check_coefficients(coefficient_a, coefficient_b, secondary_emission)
    product = pressure_pa * gap_m
    denominator = math.log(coefficient_a * product) - math.log(
        math.log(1.0 + 1.0 / secondary_emission)
    )
    if denominator <= 0:
        return math.inf
    return coefficient_b * product / denominator


def paschen_minimum(
    coefficient_a=PASCHEN_A_PER_PA_M,
    coefficient_b=PASCHEN_B_V_PER_PA_M,
    secondary_emission=SECONDARY_EMISSION_COEFFICIENT,
):
    """Analytic minimum of the Paschen model as a pair: the
    pressure-times-gap product in pascal metres at which breakdown is
    easiest, and the breakdown voltage there. Raises ValueError for a
    non-positive model coefficient."""
    _check_coefficients(coefficient_a, coefficient_b, secondary_emission)
    product_min = (
        math.e * math.log(1.0 + 1.0 / secondary_emission) / coefficient_a
    )
    return product_min, coefficient_b * product_min


def _breakdown_from_product(
    product, coefficient_a, coefficient_b, secondary_emission
):
    denominator = math.log(coefficient_a * product) - math.log(
        math.log(1.0 + 1.0 / secondary_emission)
    )
    if denominator <= 0:
        return math.inf
    return coefficient_b * product / denominator


def _bisect_product(
    target_v, low, high, coefficient_a, coefficient_b, secondary_emission
):
    """Bisect the pressure-gap product between low and high for the
    value whose breakdown voltage equals target_v. The bracket must
    straddle the target; the caller guarantees monotonicity on the
    branch it passes in."""
    f_low = _breakdown_from_product(
        low, coefficient_a, coefficient_b, secondary_emission
    ) - target_v
    for _ in range(_BISECTION_STEPS):
        middle = 0.5 * (low + high)
        f_middle = _breakdown_from_product(
            middle, coefficient_a, coefficient_b, secondary_emission
        ) - target_v
        if f_middle == 0.0:
            return middle
        if (f_middle > 0) == (f_low > 0):
            low = middle
            f_low = f_middle
        else:
            high = middle
    return 0.5 * (low + high)


def critical_pressure_window(
    gap_m,
    applied_voltage_v,
    coefficient_a=PASCHEN_A_PER_PA_M,
    coefficient_b=PASCHEN_B_V_PER_PA_M,
    secondary_emission=SECONDARY_EMISSION_COEFFICIENT,
):
    """Ambient pressure band, as a (low, high) pair in pascal, inside
    which the applied voltage is at or above the breakdown voltage of
    the gap. Returns None when the applied voltage never reaches the
    minimum of the curve, so no pressure can strike a discharge.
    Raises ValueError for a non-positive gap or applied voltage, for a
    bad model coefficient, or for an applied voltage so far above the
    model's low-pressure branch that the window cannot be bracketed."""
    if gap_m <= 0:
        raise ValueError("gap_m must be > 0")
    if applied_voltage_v <= 0:
        raise ValueError("applied_voltage_v must be > 0")
    _check_coefficients(coefficient_a, coefficient_b, secondary_emission)
    product_min, voltage_min = paschen_minimum(
        coefficient_a, coefficient_b, secondary_emission
    )
    if applied_voltage_v < voltage_min:
        return None
    asymptote = math.log(1.0 + 1.0 / secondary_emission) / coefficient_a
    low_bracket = asymptote * (1.0 + 1.0e-6)
    if (
        _breakdown_from_product(
            low_bracket, coefficient_a, coefficient_b, secondary_emission
        )
        <= applied_voltage_v
    ):
        raise ValueError(
            "applied voltage %.3g V sits above the low-pressure branch of "
            "the model; the critical window cannot be bracketed"
            % applied_voltage_v
        )
    product_low = _bisect_product(
        applied_voltage_v,
        low_bracket,
        product_min,
        coefficient_a,
        coefficient_b,
        secondary_emission,
    )
    high_bracket = product_min
    for _ in range(_BRACKET_DOUBLINGS):
        high_bracket *= 2.0
        if (
            _breakdown_from_product(
                high_bracket, coefficient_a, coefficient_b, secondary_emission
            )
            > applied_voltage_v
        ):
            break
    else:  # pragma: no cover - unreachable for any physical voltage
        raise ValueError(
            "could not bracket the high-pressure side of the critical window"
        )
    product_high = _bisect_product(
        applied_voltage_v,
        high_bracket,
        product_min,
        coefficient_a,
        coefficient_b,
        secondary_emission,
    )
    return product_low / gap_m, product_high / gap_m


def is_within_critical_pressure_range(pressure_pa, window):
    """True when an ambient pressure sits inside the critical window,
    endpoints included -- at an endpoint the breakdown voltage equals
    the applied voltage, which is not a passing condition. A window
    that has collapsed to a point at the minimum of the curve is still
    a window. A window of None is never entered. Raises ValueError for
    a non-positive pressure or a malformed window."""
    if pressure_pa <= 0:
        raise ValueError("pressure_pa must be > 0")
    if window is None:
        return False
    low, high = window
    if low <= 0 or high < low:
        raise ValueError("window must be an ordered pair of positive pressures")
    return _at_least(pressure_pa, low) and _within(pressure_pa, high)


def depressurisation_pressure(initial_pressure_pa, time_constant_s, elapsed_s):
    """Ambient pressure in an unsealed enclosure after elapsed_s
    seconds of exponential venting. Raises ValueError for a
    non-positive initial pressure or time constant, or a negative
    elapsed time."""
    if initial_pressure_pa <= 0:
        raise ValueError("initial_pressure_pa must be > 0")
    if time_constant_s <= 0:
        raise ValueError("time_constant_s must be > 0")
    if elapsed_s < 0:
        raise ValueError("elapsed_s must be >= 0")
    return initial_pressure_pa * math.exp(-elapsed_s / time_constant_s)


def time_to_pressure(initial_pressure_pa, target_pressure_pa, time_constant_s):
    """Seconds of exponential venting needed to reach a target
    pressure, zero when the enclosure is already at or below it. Raises
    ValueError for a non-positive pressure or time constant."""
    if initial_pressure_pa <= 0:
        raise ValueError("initial_pressure_pa must be > 0")
    if target_pressure_pa <= 0:
        raise ValueError("target_pressure_pa must be > 0")
    if time_constant_s <= 0:
        raise ValueError("time_constant_s must be > 0")
    if initial_pressure_pa <= target_pressure_pa:
        return 0.0
    return time_constant_s * math.log(
        initial_pressure_pa / target_pressure_pa
    )


def depressurisation_findings(item_id, profile, window):
    """Findings (empty list when the venting profile is acceptable) for
    an item that is energised on a timer during depressurisation.
    profile keys: initial_pressure_pa, time_constant_s,
    inhibit_release_time_s. A window of None means no critical band
    exists, so the profile cannot be wrong. Raises ValueError for a
    missing key or an out-of-range value."""
    _require_keys(profile, _PROFILE_REQUIRED_KEYS, "depressurisation profile")
    if window is None:
        return []
    if profile["inhibit_release_time_s"] < 0:
        raise ValueError("inhibit_release_time_s must be >= 0")
    low, _high = window
    clear_s = time_to_pressure(
        profile["initial_pressure_pa"], low, profile["time_constant_s"]
    )
    release_s = profile["inhibit_release_time_s"]
    findings = []
    if not _at_least(release_s, clear_s):
        findings.append(
            "item %s: energisation released at %.1f s, before the %.1f s the "
            "enclosure needs to fall clear of the critical pressure range"
            % (item_id, release_s, clear_s)
        )
    pressure_at_release = depressurisation_pressure(
        profile["initial_pressure_pa"],
        profile["time_constant_s"],
        release_s,
    )
    if not _within(pressure_at_release, low):
        findings.append(
            "item %s: %.4g Pa at release, still above the %.4g Pa lower edge "
            "of the critical pressure range" % (item_id, pressure_at_release, low)
        )
    return findings


def hv_item_findings(item):
    """Findings (empty list when compliant) for one high voltage item
    under clause 5.10. Required keys: item_id, operating_state,
    applied_voltage_v, gap_m, potted, pressurised, operating_pressure_pa,
    energisation_inhibit_pressure_pa (None when no inhibit is fitted),
    required_voltage_margin. Optional key depressurisation_profile.
    Returns an empty list for potted or pressurised hardware, which
    meets the provision by construction. Raises ValueError for a
    missing key, an unrecognized operating state, or an out-of-range
    value."""
    _require_keys(item, _ITEM_REQUIRED_KEYS, "high voltage item")
    item_id = item["item_id"]
    categorize_hv_operating_state(item["operating_state"])
    if not clause_applies(item["potted"], item["pressurised"]):
        return []
    if item["required_voltage_margin"] < 1.0:
        raise ValueError("required_voltage_margin must be >= 1.0")
    window = critical_pressure_window(item["gap_m"], item["applied_voltage_v"])
    findings = []
    if is_within_critical_pressure_range(item["operating_pressure_pa"], window):
        findings.append(
            "item %s: operates at %.4g Pa, inside the %.4g-%.4g Pa critical "
            "range for a %.4g m gap at %.4g V"
            % (
                item_id,
                item["operating_pressure_pa"],
                window[0],
                window[1],
                item["gap_m"],
                item["applied_voltage_v"],
            )
        )
    inhibit_pa = item["energisation_inhibit_pressure_pa"]
    if window is not None:
        if inhibit_pa is None:
            findings.append(
                "item %s: no energisation inhibit on record, so nothing keeps "
                "the item unpowered through the critical pressure range"
                % item_id
            )
        else:
            if inhibit_pa <= 0:
                raise ValueError(
                    "energisation_inhibit_pressure_pa must be > 0 or None"
                )
            if not _within(inhibit_pa, window[0]):
                findings.append(
                    "item %s: energisation inhibit releases at %.4g Pa, above "
                    "the %.4g Pa lower edge of the critical range"
                    % (item_id, inhibit_pa, window[0])
                )
    breakdown_v = paschen_breakdown_voltage(
        item["operating_pressure_pa"], item["gap_m"]
    )
    margin = breakdown_v / item["applied_voltage_v"]
    if not _at_least(margin, item["required_voltage_margin"]):
        findings.append(
            "item %s: breakdown margin %.3f at the operating pressure, below "
            "the required %.3f" % (item_id, margin, item["required_voltage_margin"])
        )
    if "depressurisation_profile" in item:
        findings.extend(
            depressurisation_findings(
                item_id, item["depressurisation_profile"], window
            )
        )
    return findings


def declared_precaution_findings(item_id, precautions):
    """Findings (empty list when acceptable) for the declared design
    precautions of one item: at least one precaution has to be on
    record. Raises ValueError for a precaution outside the recognized
    set."""
    listed = list(precautions)
    for precaution in listed:
        if precaution not in RECOGNIZED_HV_PRECAUTIONS:
            raise ValueError(
                "unrecognized high voltage precaution %r for item %s"
                % (precaution, item_id)
            )
    if not listed:
        return [
            "item %s: no high voltage design precaution declared" % item_id
        ]
    return []


def aggregate_hv_provisions_review(equipment):
    """Clause 5.10 review of a set of high voltage items. equipment
    keys: equipment_id, plus an optional items list. Each item may also
    carry a precautions list. Returns a mapping of the per-item finding
    lists, the flat finding list and a compliant flag that is true only
    when no item carries a finding. Raises ValueError for a missing
    equipment_id or through the per-item checks."""
    if "equipment_id" not in equipment:
        raise ValueError(
            "equipment record is missing required key: equipment_id"
        )
    per_item = {}
    findings = []
    for item in equipment.get("items", []):
        item_findings = hv_item_findings(item)
        item_findings.extend(
            declared_precaution_findings(
                item["item_id"], item.get("precautions", [])
            )
        )
        per_item[item["item_id"]] = item_findings
        findings.extend(item_findings)
    return {
        "equipment_id": equipment["equipment_id"],
        "item_findings": per_item,
        "findings": findings,
        "compliant": not findings,
    }
