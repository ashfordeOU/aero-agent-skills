"""Repetitive-overload endurance of a retriggerable latching current limiter.

Anchor: ECSS-E-ST-20-20C clause 5.2.10.2.1 -- a retriggerable limiter has to
survive repeated overload cycles while its derating limits still hold.
Paraphrased into an implementable procedure; no standard text is reproduced.

What makes the retriggerable case different
-------------------------------------------
A plain latching limiter stops after one trip and waits for a command, so the
recovery interval between overloads is set by an operator. A retriggerable
limiter re-arms itself after a fixed off time, so a fault that does not clear
produces an unattended train of limitation intervals at a duty cycle the design
fixed in advance. The endurance question is therefore a design question: is the
declared off time long enough, and how many retriggers does a persistent fault
accumulate before something else clears it.

Procedure implemented here
--------------------------
1. Validate the bus, the limiter setting, the faulted load, the limitation and
   off intervals, the fault-persistence window and the pass-element thermal and
   rating data.
2. Form the retrigger period and duty cycle, and the dissipation of a single
   limitation interval at the regulated output voltage.
3. Settle a single-pole junction model over the repeating train and take the
   settled peak rise, which is what the junction derating limit applies to.
4. Count the complete retrigger cycles a persistent fault produces inside the
   declared window and compare that with the rated retrigger capability.
5. Solve, from the thermal headroom the case temperature leaves, the shortest
   off time and the highest duty cycle that still hold the junction limit, so
   a failing design is handed the number it has to change.
6. Grade junction temperature, duty cycle, limiting current, average
   dissipation and retrigger count, and report the verdict with each margin.
"""

import math

__all__ = [
    "DEFAULT_RLCL_DERATING_POLICY",
    "RELATIVE_TOLERANCE",
    "TEMPERATURE_TOLERANCE_C",
    "assess_rlcl_repetitive_overload",
    "average_dissipation_w",
    "limitation_dissipation_w",
    "maximum_duty_cycle",
    "minimum_off_time_s",
    "regulated_output_voltage_v",
    "retrigger_count",
    "retrigger_duty_cycle",
    "retrigger_period_s",
    "settled_junction_rise_c",
    "validate_rlcl_policy",
]

# Declared project derating policy, carried with the result rather than buried
# inside the comparisons.
DEFAULT_RLCL_DERATING_POLICY = {
    "max_junction_temperature_c": 110.0,
    "max_duty_cycle": 0.50,
    "max_current_fraction": 0.80,
    "max_average_power_fraction": 0.70,
    "min_retrigger_margin": 1.0,
}

# A limit comparison can land exactly on its bound in exact arithmetic and a
# few units in the last place off it in floating point.
TEMPERATURE_TOLERANCE_C = 1e-9
RELATIVE_TOLERANCE = 1e-12

_POLICY_FRACTION_KEYS = ("max_duty_cycle", "max_current_fraction", "max_average_power_fraction")


def _real(label, value):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(label, value):
    """Return value as a strictly positive finite float."""
    number = _real(label, value)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _count(label, value):
    """Return value as a strictly positive integer count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _fraction(label, value):
    """Return value as a fraction in the half-open interval (0, 1]."""
    number = _real(label, value)
    if number <= 0.0 or number > 1.0:
        raise ValueError("%s must lie in (0, 1], got %g" % (label, number))
    return number


def _at_or_below(value, limit, tolerance):
    """True when value is below limit or on it to within tolerance."""
    return value < limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=tolerance)


def validate_rlcl_policy(policy):
    """Return the derating policy after checking every key it has to carry."""
    if not isinstance(policy, dict):
        raise ValueError("derating policy must be a mapping")
    for key in ("max_junction_temperature_c", "min_retrigger_margin") + _POLICY_FRACTION_KEYS:
        if key not in policy:
            raise ValueError("derating policy missing required key '%s'" % key)
    _real("max_junction_temperature_c", policy["max_junction_temperature_c"])
    for key in _POLICY_FRACTION_KEYS:
        _fraction(key, policy[key])
    if _real("min_retrigger_margin", policy["min_retrigger_margin"]) < 1.0:
        raise ValueError("min_retrigger_margin below 1.0 would accept more retriggers than rated")
    return policy


def retrigger_period_s(limitation_time_s, off_time_s):
    """Return the period of one limitation-plus-off retrigger cycle."""
    on_time = _positive("limitation_time_s", limitation_time_s)
    off_time = _positive("off_time_s", off_time_s)
    return on_time + off_time


def retrigger_duty_cycle(limitation_time_s, off_time_s):
    """Return the fraction of the retrigger period spent in current limitation."""
    on_time = _positive("limitation_time_s", limitation_time_s)
    return on_time / retrigger_period_s(limitation_time_s, off_time_s)


def retrigger_count(window_s, limitation_time_s, off_time_s):
    """Return the complete retrigger cycles a persistent fault produces in a window."""
    window = _positive("window_s", window_s)
    period = retrigger_period_s(limitation_time_s, off_time_s)
    # Guard the floor against a window that is an exact multiple of the period
    # but lands a fraction of a unit in the last place low in binary.
    ratio = window / period
    whole = math.floor(ratio)
    if math.isclose(ratio, whole + 1.0, rel_tol=RELATIVE_TOLERANCE, abs_tol=0.0):
        whole += 1
    return int(whole)


def regulated_output_voltage_v(limiting_current_a, load_resistance_ohm, bus_voltage_v):
    """Return the output voltage held across the faulted load during limitation."""
    current = _positive("limiting_current_a", limiting_current_a)
    resistance = _positive("load_resistance_ohm", load_resistance_ohm)
    bus = _positive("bus_voltage_v", bus_voltage_v)
    output = current * resistance
    if output > bus or math.isclose(output, bus, rel_tol=RELATIVE_TOLERANCE, abs_tol=0.0):
        raise ValueError(
            "a load of %g ohm cannot draw the limiting current %g A from %g V, so the "
            "limiter never enters limitation and never retriggers"
            % (resistance, current, bus)
        )
    return output


def limitation_dissipation_w(bus_voltage_v, limiting_current_a, load_resistance_ohm):
    """Return the pass-element dissipation during one limitation interval."""
    output = regulated_output_voltage_v(limiting_current_a, load_resistance_ohm, bus_voltage_v)
    return (float(bus_voltage_v) - output) * float(limiting_current_a)


def settled_junction_rise_c(power_w, rth_jc_k_per_w, thermal_tau_s, on_time_s, off_time_s):
    """Return the first-pulse and settled junction rises over a retrigger train."""
    power = _positive("power_w", power_w)
    rth = _positive("rth_jc_k_per_w", rth_jc_k_per_w)
    tau = _positive("thermal_tau_s", thermal_tau_s)
    on_time = _positive("on_time_s", on_time_s)
    off_time = _positive("off_time_s", off_time_s)
    heat = math.exp(-on_time / tau)
    cool = math.exp(-off_time / tau)
    denominator = 1.0 - heat * cool
    if denominator <= 0.0:
        raise ValueError("degenerate retrigger train: no cooling interval remains")
    first = power * rth * (1.0 - heat)
    peak = first / denominator
    return {
        "first_pulse_rise_c": first,
        "settled_peak_rise_c": peak,
        "settled_valley_rise_c": peak * cool,
        "steady_state_rise_c": power * rth,
    }


def average_dissipation_w(power_w, limitation_time_s, off_time_s):
    """Return the dissipation averaged over one retrigger period."""
    power = _positive("power_w", power_w)
    return power * retrigger_duty_cycle(limitation_time_s, off_time_s)


def minimum_off_time_s(power_w, rth_jc_k_per_w, thermal_tau_s, on_time_s, max_rise_c):
    """Return the shortest off time whose settled peak still holds the rise limit.

    Inverts the settled-train expression for the off time. Zero is returned when
    even a continuously limiting element stays under the limit; a rise limit the
    first limitation interval already breaks cannot be bought by any off time at
    all, and is refused rather than returned as a very large number.
    """
    power = _positive("power_w", power_w)
    rth = _positive("rth_jc_k_per_w", rth_jc_k_per_w)
    tau = _positive("thermal_tau_s", thermal_tau_s)
    on_time = _positive("on_time_s", on_time_s)
    max_rise = _positive("max_rise_c", max_rise_c)
    heat = math.exp(-on_time / tau)
    first = power * rth * (1.0 - heat)
    residue = 1.0 - first / max_rise
    if residue <= 0.0:
        raise ValueError(
            "one limitation interval alone raises the junction by %.4f K against a "
            "headroom of %.4f K; no off time can hold the limit and the limitation "
            "time or the thermal path has to change" % (first, max_rise)
        )
    ratio = residue / heat
    if ratio >= 1.0:
        return 0.0
    return -tau * math.log(ratio)


def maximum_duty_cycle(power_w, rth_jc_k_per_w, thermal_tau_s, on_time_s, max_rise_c):
    """Return the highest retrigger duty cycle that still holds the rise limit."""
    off_time = minimum_off_time_s(power_w, rth_jc_k_per_w, thermal_tau_s, on_time_s, max_rise_c)
    on_time = float(on_time_s)
    if off_time == 0.0:
        return 1.0
    return on_time / (on_time + off_time)


def assess_rlcl_repetitive_overload(spec):
    """Run the clause 5.2.10.2.1 retriggerable-limiter endurance assessment.

    spec keys: bus_voltage_v, limiting_current_a, load_resistance_ohm,
    limitation_time_s, retrigger_off_time_s, fault_window_s, rth_jc_k_per_w,
    thermal_tau_s, case_temperature_c, rated_current_a, rated_power_w,
    rated_retrigger_cycles, and optionally derating_policy.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "bus_voltage_v",
        "limiting_current_a",
        "load_resistance_ohm",
        "limitation_time_s",
        "retrigger_off_time_s",
        "fault_window_s",
        "rth_jc_k_per_w",
        "thermal_tau_s",
        "case_temperature_c",
        "rated_current_a",
        "rated_power_w",
        "rated_retrigger_cycles",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    policy = validate_rlcl_policy(spec.get("derating_policy", DEFAULT_RLCL_DERATING_POLICY))
    bus = _positive("bus_voltage_v", spec["bus_voltage_v"])
    limiting = _positive("limiting_current_a", spec["limiting_current_a"])
    resistance = _positive("load_resistance_ohm", spec["load_resistance_ohm"])
    on_time = _positive("limitation_time_s", spec["limitation_time_s"])
    off_time = _positive("retrigger_off_time_s", spec["retrigger_off_time_s"])
    window = _positive("fault_window_s", spec["fault_window_s"])
    rth = _positive("rth_jc_k_per_w", spec["rth_jc_k_per_w"])
    tau = _positive("thermal_tau_s", spec["thermal_tau_s"])
    case_temperature = _real("case_temperature_c", spec["case_temperature_c"])
    rated_current = _positive("rated_current_a", spec["rated_current_a"])
    rated_power = _positive("rated_power_w", spec["rated_power_w"])
    rated_retriggers = _count("rated_retrigger_cycles", spec["rated_retrigger_cycles"])

    findings = []
    power = limitation_dissipation_w(bus, limiting, resistance)
    duty = retrigger_duty_cycle(on_time, off_time)
    period = retrigger_period_s(on_time, off_time)
    cycles = retrigger_count(window, on_time, off_time)
    rises = settled_junction_rise_c(power, rth, tau, on_time, off_time)
    peak_junction = case_temperature + rises["settled_peak_rise_c"]
    average_power = average_dissipation_w(power, on_time, off_time)

    junction_limit = float(policy["max_junction_temperature_c"])
    headroom = junction_limit - case_temperature
    required_off_time = None
    highest_duty = None
    if headroom <= 0.0:
        findings.append(
            "the declared case temperature %.2f degC already sits at or above the "
            "derated junction limit %.2f degC, so no retrigger design holds"
            % (case_temperature, junction_limit)
        )
    else:
        try:
            required_off_time = minimum_off_time_s(power, rth, tau, on_time, headroom)
            highest_duty = maximum_duty_cycle(power, rth, tau, on_time, headroom)
        except ValueError as exc:
            findings.append(str(exc))

    if cycles == 0:
        findings.append(
            "the declared fault window %.4f s is shorter than one retrigger period "
            "%.4f s, so the window contains no complete retrigger cycle" % (window, period)
        )

    current_limit = rated_current * float(policy["max_current_fraction"])
    power_limit = rated_power * float(policy["max_average_power_fraction"])
    duty_limit = float(policy["max_duty_cycle"])
    retrigger_margin = float(rated_retriggers) / float(cycles) if cycles else float("inf")
    margin_limit = float(policy["min_retrigger_margin"])

    checks = [
        {
            "name": "settled-junction-temperature",
            "value": peak_junction,
            "limit": junction_limit,
            "unit": "degC",
            "passed": _at_or_below(peak_junction, junction_limit, TEMPERATURE_TOLERANCE_C),
        },
        {
            "name": "retrigger-duty-cycle",
            "value": duty,
            "limit": duty_limit,
            "unit": "fraction",
            "passed": _at_or_below(duty, duty_limit, abs(duty_limit) * RELATIVE_TOLERANCE),
        },
        {
            "name": "limiting-current-derating",
            "value": limiting,
            "limit": current_limit,
            "unit": "A",
            "passed": _at_or_below(
                limiting, current_limit, abs(current_limit) * RELATIVE_TOLERANCE
            ),
        },
        {
            "name": "average-dissipation-derating",
            "value": average_power,
            "limit": power_limit,
            "unit": "W",
            "passed": _at_or_below(
                average_power, power_limit, abs(power_limit) * RELATIVE_TOLERANCE
            ),
        },
        {
            "name": "retrigger-capability",
            "value": retrigger_margin,
            "limit": margin_limit,
            "unit": "ratio",
            "passed": retrigger_margin > margin_limit
            or math.isclose(retrigger_margin, margin_limit, rel_tol=RELATIVE_TOLERANCE, abs_tol=0.0),
        },
    ]

    for check in checks:
        if not check["passed"]:
            findings.append(
                "%s is %.4f %s against a limit of %.4f %s"
                % (check["name"], check["value"], check["unit"], check["limit"], check["unit"])
            )
    if required_off_time is not None and off_time < required_off_time:
        findings.append(
            "the declared retrigger off time %.5f s is shorter than the %.5f s the "
            "junction limit needs at this limitation time"
            % (off_time, required_off_time)
        )

    compliant = all(check["passed"] for check in checks) and headroom > 0.0
    return {
        "verdict": "endurance-demonstrated" if compliant else "endurance-not-demonstrated",
        "compliant": compliant,
        "limitation_dissipation_w": power,
        "regulated_output_voltage_v": regulated_output_voltage_v(limiting, resistance, bus),
        "retrigger_period_s": period,
        "retrigger_duty_cycle": duty,
        "retrigger_count": cycles,
        "retrigger_margin": retrigger_margin,
        "average_dissipation_w": average_power,
        "settled_peak_junction_temperature_c": peak_junction,
        "junction_rises_c": rises,
        "junction_headroom_c": headroom,
        "required_off_time_s": required_off_time,
        "off_time_shortfall_s": (
            max(0.0, required_off_time - off_time) if required_off_time is not None else None
        ),
        "highest_permissible_duty_cycle": highest_duty,
        "checks": checks,
        "findings": findings,
    }
