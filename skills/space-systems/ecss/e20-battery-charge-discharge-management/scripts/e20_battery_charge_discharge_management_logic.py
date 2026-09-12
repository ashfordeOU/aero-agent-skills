#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.7.3 battery charge and discharge management
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the battery charger to behave
so that a deeply discharged battery, including one taken all the way
down to zero volts, can be brought back into service. This module
implements the checkable part of that clause: categorization of a cell
terminal state from its measured voltage, the charge stage that state
permits, the current limit each stage derives from the rated capacity,
the time a recovery trickle needs to lift the pack back to the bulk
entry point, the charge-temperature window, and the depth-of-discharge
and end-of-discharge voltage limits that govern the discharge side.
Every threshold is a caller-supplied design figure; the defaults here
are ordinary lithium-ion placeholders, not values taken from the
standard. It does not model cell chemistry, does not estimate state of
health, and does not size the battery.
"""

DEFAULT_CELL_THRESHOLDS = {
    "zero_volt_ceiling_v": 0.5,
    "deep_discharge_ceiling_v": 2.5,
    "max_charge_voltage_v": 4.2,
}

DEFAULT_STAGE_C_RATES = {
    "recovery_trickle": 0.02,
    "precharge": 0.05,
    "bulk_constant_current": 0.5,
    "taper_constant_voltage": 0.5,
    "charge_inhibit": 0.0,
}

STATE_TO_STAGE = {
    "zero_volt": "recovery_trickle",
    "deep_discharge": "precharge",
    "operating": "bulk_constant_current",
    "overvoltage": "charge_inhibit",
}

RECOVERY_STATES = frozenset({"zero_volt", "deep_discharge"})

# Slack that absorbs floating-point representation error when a
# measured sum or ratio is compared against a design limit. It is a
# representation tolerance, not an engineering allowance.
COMPARISON_REL_TOL = 1e-9
COMPARISON_ABS_TOL = 1e-12


def _spread(limit):
    return abs(limit) * COMPARISON_REL_TOL + COMPARISON_ABS_TOL


def _at_most(value, limit):
    """True when value does not exceed limit, absorbing the
    representation error of a float sum or ratio at the boundary."""
    return value <= limit or (value - limit) <= _spread(limit)


def _at_least(value, limit):
    """True when value meets or exceeds limit, absorbing the
    representation error of a float sum or ratio at the boundary."""
    return value >= limit or (limit - value) <= _spread(limit)


def validate_cell_thresholds(thresholds=None):
    """Normalized cell voltage thresholds. Defaults are used when
    thresholds is None. Raises ValueError for a missing key, a
    non-positive threshold, or an ordering that is not strictly
    increasing from the zero-volt ceiling through the deep-discharge
    ceiling to the maximum charge voltage."""
    source = DEFAULT_CELL_THRESHOLDS if thresholds is None else thresholds
    normalized = {}
    for key in (
        "zero_volt_ceiling_v",
        "deep_discharge_ceiling_v",
        "max_charge_voltage_v",
    ):
        if key not in source:
            raise ValueError("cell thresholds missing required key %r" % (key,))
        value = float(source[key])
        if value <= 0:
            raise ValueError("%s must be > 0" % key)
        normalized[key] = value
    if not (
        normalized["zero_volt_ceiling_v"]
        < normalized["deep_discharge_ceiling_v"]
        < normalized["max_charge_voltage_v"]
    ):
        raise ValueError(
            "cell thresholds must increase: zero_volt_ceiling_v < "
            "deep_discharge_ceiling_v < max_charge_voltage_v"
        )
    return normalized


def categorize_cell_state(cell_voltage_v, thresholds=None):
    """Terminal state of a cell from its measured voltage:
    "zero_volt" (at or under the reanimation ceiling, the case the
    charger has to be able to come back from), "deep_discharge" (above
    that ceiling but under the normal operating floor), "operating"
    (inside the normal band) or "overvoltage" (above the maximum
    charge voltage). Raises ValueError for a negative voltage or
    through validate_cell_thresholds for an invalid threshold set."""
    if cell_voltage_v < 0:
        raise ValueError("cell_voltage_v must be >= 0")
    limits = validate_cell_thresholds(thresholds)
    if _at_most(cell_voltage_v, limits["zero_volt_ceiling_v"]):
        return "zero_volt"
    if cell_voltage_v < limits["deep_discharge_ceiling_v"]:
        return "deep_discharge"
    if _at_most(cell_voltage_v, limits["max_charge_voltage_v"]):
        return "operating"
    return "overvoltage"


def charge_stage_for_state(state):
    """Charge stage a cell state permits: a reduced recovery trickle
    from zero volts, a precharge from deep discharge, bulk constant
    current from the normal band, and charge inhibit above the maximum
    charge voltage. Raises ValueError for an unrecognized state."""
    try:
        return STATE_TO_STAGE[state]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized cell state %r under E-ST-20C clause 5.7.3"
            % (state,)
        )


def stage_current_limit_a(stage, capacity_ah, c_rates=None):
    """Current limit in amperes for a charge stage: the stage C-rate
    times the rated capacity. Raises ValueError for a non-positive
    capacity, an unrecognized stage, or a negative C-rate."""
    if capacity_ah <= 0:
        raise ValueError("capacity_ah must be > 0")
    rates = DEFAULT_STAGE_C_RATES if c_rates is None else c_rates
    if stage not in rates:
        raise ValueError("no C-rate declared for charge stage %r" % (stage,))
    rate = float(rates[stage])
    if rate < 0:
        raise ValueError("C-rate for stage %r must be >= 0" % (stage,))
    return rate * float(capacity_ah)


def recovery_charge_time_h(capacity_ah, recovery_fraction, charge_current_a):
    """Hours a constant recovery current needs to return the fraction
    of rated capacity that brings the pack back to the bulk entry
    point. Raises ValueError for a non-positive capacity or current, or
    a recovery fraction outside the half-open range above zero up to
    one."""
    if capacity_ah <= 0:
        raise ValueError("capacity_ah must be > 0")
    if charge_current_a <= 0:
        raise ValueError("charge_current_a must be > 0")
    if not 0 < recovery_fraction <= 1:
        raise ValueError("recovery_fraction must be within (0, 1]")
    return float(capacity_ah) * float(recovery_fraction) / float(charge_current_a)


def depth_of_discharge(discharged_ah, capacity_ah):
    """Depth of discharge as a fraction of rated capacity. Raises
    ValueError for a negative charge removed, a non-positive capacity,
    or a charge removed that exceeds the rated capacity by more than
    representation error."""
    if discharged_ah < 0:
        raise ValueError("discharged_ah must be >= 0")
    if capacity_ah <= 0:
        raise ValueError("capacity_ah must be > 0")
    if not _at_most(discharged_ah, capacity_ah):
        raise ValueError("discharged_ah must be <= capacity_ah")
    return float(discharged_ah) / float(capacity_ah)


def stage_selection_findings(battery_id, state, commanded_stage):
    """Findings (empty when consistent) for a commanded charge stage
    that is not the stage the measured cell state permits. Raises
    ValueError through charge_stage_for_state for an unrecognized
    state."""
    expected = charge_stage_for_state(state)
    if commanded_stage == expected:
        return []
    return [
        {
            "issue": "charge_stage_does_not_match_cell_state",
            "battery": battery_id,
            "cell_state": state,
            "commanded_stage": commanded_stage,
            "expected_stage": expected,
        }
    ]


def charge_temperature_findings(battery_id, cell_temperature_c, window_c):
    """Findings (empty when inside the window) for charging outside the
    permitted cell temperature band. Charging a cell colder than the
    lower bound is the plating case and is reported separately from an
    over-temperature charge. window_c: (minimum, maximum) in degrees
    Celsius. Raises ValueError when the window is inverted or not a
    pair."""
    try:
        minimum_c, maximum_c = window_c
    except (TypeError, ValueError):
        raise ValueError("window_c must be a (minimum, maximum) pair")
    if minimum_c >= maximum_c:
        raise ValueError("charge temperature window minimum must be < maximum")
    findings = []
    if not _at_least(cell_temperature_c, minimum_c):
        findings.append(
            {
                "issue": "charge_below_minimum_cell_temperature",
                "battery": battery_id,
                "temperature_c": cell_temperature_c,
                "limit_c": minimum_c,
            }
        )
    if not _at_most(cell_temperature_c, maximum_c):
        findings.append(
            {
                "issue": "charge_above_maximum_cell_temperature",
                "battery": battery_id,
                "temperature_c": cell_temperature_c,
                "limit_c": maximum_c,
            }
        )
    return findings


def charge_command_findings(
    battery_id, command, capacity_ah, thresholds=None, c_rates=None
):
    """Findings (empty when the command is inside every limit) for one
    commanded charge point.

    command: {"stage", "current_a", "cell_voltage_v"}. The commanded
    current is checked against the stage limit, an inhibit stage is
    checked for actually carrying no current, and the commanded cell
    voltage is checked against the maximum charge voltage. Raises
    ValueError for a missing key, a negative current or voltage, or
    through the helpers for an unrecognized stage or bad capacity."""
    for key in ("stage", "current_a", "cell_voltage_v"):
        if key not in command:
            raise ValueError("charge command missing required key %r" % (key,))
    current_a = float(command["current_a"])
    cell_voltage_v = float(command["cell_voltage_v"])
    if current_a < 0:
        raise ValueError("commanded current_a must be >= 0")
    if cell_voltage_v < 0:
        raise ValueError("commanded cell_voltage_v must be >= 0")
    limits = validate_cell_thresholds(thresholds)
    stage = command["stage"]
    limit_a = stage_current_limit_a(stage, capacity_ah, c_rates)
    findings = []
    if not _at_most(current_a, limit_a):
        findings.append(
            {
                "issue": "charge_current_above_stage_limit",
                "battery": battery_id,
                "stage": stage,
                "current_a": current_a,
                "limit_a": limit_a,
            }
        )
    if stage == "charge_inhibit" and not _at_most(current_a, 0.0):
        findings.append(
            {
                "issue": "charge_not_inhibited_at_overvoltage",
                "battery": battery_id,
                "current_a": current_a,
            }
        )
    if not _at_most(cell_voltage_v, limits["max_charge_voltage_v"]):
        findings.append(
            {
                "issue": "cell_voltage_above_maximum_charge_voltage",
                "battery": battery_id,
                "cell_voltage_v": cell_voltage_v,
                "limit_v": limits["max_charge_voltage_v"],
            }
        )
    return findings


def recovery_findings(battery_id, state, capacity_ah, charger, c_rates=None):
    """Findings (empty when the charger can bring the pack back) for a
    cell state that needs recovery.

    charger: {"supports_zero_volt_recovery": bool, "recovery_fraction":
    float, "maximum_recovery_time_h": float}. A state outside the
    recovery set yields no findings. A zero-volt pack needs a charger
    that declares it can restart from there; the recovery trickle is
    then timed against the budget. Raises ValueError for a missing
    charger key, a non-positive time budget, or through the helpers."""
    if state not in RECOVERY_STATES:
        charge_stage_for_state(state)  # rejects an unrecognized state
        return []
    for key in (
        "supports_zero_volt_recovery",
        "recovery_fraction",
        "maximum_recovery_time_h",
    ):
        if key not in charger:
            raise ValueError("charger definition missing required key %r" % (key,))
    budget_h = float(charger["maximum_recovery_time_h"])
    if budget_h <= 0:
        raise ValueError("maximum_recovery_time_h must be > 0")
    findings = []
    if state == "zero_volt" and not charger["supports_zero_volt_recovery"]:
        findings.append(
            {
                "issue": "charger_cannot_recover_zero_volt_battery",
                "battery": battery_id,
                "cell_state": state,
            }
        )
    stage = charge_stage_for_state(state)
    current_a = stage_current_limit_a(stage, capacity_ah, c_rates)
    if current_a <= 0:
        raise ValueError("recovery stage %r has a zero current limit" % (stage,))
    time_h = recovery_charge_time_h(
        capacity_ah, charger["recovery_fraction"], current_a
    )
    if not _at_most(time_h, budget_h):
        findings.append(
            {
                "issue": "recovery_time_exceeds_budget",
                "battery": battery_id,
                "stage": stage,
                "recovery_time_h": time_h,
                "budget_h": budget_h,
            }
        )
    return findings


def discharge_findings(battery_id, discharge, limits):
    """Findings (empty when inside the limits) for the discharge side.

    discharge: {"discharged_ah", "capacity_ah",
    "end_of_discharge_voltage_v"}. limits:
    {"maximum_depth_of_discharge", "end_of_discharge_voltage_floor_v"}.
    Raises ValueError for a missing key, a maximum depth outside the
    half-open range above zero up to one, a non-positive voltage floor,
    or through depth_of_discharge for an inconsistent charge figure."""
    for key in ("discharged_ah", "capacity_ah", "end_of_discharge_voltage_v"):
        if key not in discharge:
            raise ValueError("discharge record missing required key %r" % (key,))
    for key in ("maximum_depth_of_discharge", "end_of_discharge_voltage_floor_v"):
        if key not in limits:
            raise ValueError("discharge limits missing required key %r" % (key,))
    maximum_dod = float(limits["maximum_depth_of_discharge"])
    if not 0 < maximum_dod <= 1:
        raise ValueError("maximum_depth_of_discharge must be within (0, 1]")
    floor_v = float(limits["end_of_discharge_voltage_floor_v"])
    if floor_v <= 0:
        raise ValueError("end_of_discharge_voltage_floor_v must be > 0")
    findings = []
    dod = depth_of_discharge(
        discharge["discharged_ah"], discharge["capacity_ah"]
    )
    if not _at_most(dod, maximum_dod):
        findings.append(
            {
                "issue": "depth_of_discharge_above_limit",
                "battery": battery_id,
                "depth_of_discharge": dod,
                "limit": maximum_dod,
            }
        )
    end_voltage_v = float(discharge["end_of_discharge_voltage_v"])
    if not _at_least(end_voltage_v, floor_v):
        findings.append(
            {
                "issue": "end_of_discharge_voltage_below_floor",
                "battery": battery_id,
                "end_of_discharge_voltage_v": end_voltage_v,
                "floor_v": floor_v,
            }
        )
    return findings


def battery_management_review(battery):
    """Full clause 5.7.3 review for one battery.

    battery: {"battery_id", "capacity_ah", "cell_voltage_v",
    "cell_temperature_c", "charge_temperature_window_c": (min, max),
    "command": {...see charge_command_findings...}, "charger":
    {...see recovery_findings...}, "discharge": {...},
    "discharge_limits": {...}, "cell_thresholds" (optional),
    "stage_c_rates" (optional)}.

    Returns {"stage": [...], "charge": [...], "thermal": [...],
    "recovery": [...], "discharge": [...]}. Raises ValueError through
    the helpers for any invalid input. Does not mutate battery."""
    battery_id = battery["battery_id"]
    capacity_ah = battery["capacity_ah"]
    thresholds = battery.get("cell_thresholds")
    c_rates = battery.get("stage_c_rates")
    state = categorize_cell_state(battery["cell_voltage_v"], thresholds)
    return {
        "stage": stage_selection_findings(
            battery_id, state, battery["command"]["stage"]
        ),
        "charge": charge_command_findings(
            battery_id, battery["command"], capacity_ah, thresholds, c_rates
        ),
        "thermal": charge_temperature_findings(
            battery_id,
            battery["cell_temperature_c"],
            battery["charge_temperature_window_c"],
        ),
        "recovery": recovery_findings(
            battery_id, state, capacity_ah, battery["charger"], c_rates
        ),
        "discharge": discharge_findings(
            battery_id, battery["discharge"], battery["discharge_limits"]
        ),
    }


def is_charge_management_compliant(review):
    """True when every finding list in a battery_management_review
    result is empty -- the charger stage, current, temperature,
    recovery timing and discharge limits all hold."""
    return all(len(findings) == 0 for findings in review.values())
