"""Repetitive-overload endurance of a latching current limiter (LCL).

Anchor: ECSS-E-ST-20-20C clause 5.2.10.1.1 -- a latching current limiter has to
survive repeated overload cycles while every rating and derating limit it is
built against still holds. Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the bus, the limiter setting, the overload and the pass-element
   thermal and rating data. A missing or non-physical value is refused rather
   than defaulted, because the endurance verdict is only as good as its inputs.
2. Decide whether the declared overload actually drives the limiter into
   current limitation. The prospective load current at full bus voltage is
   compared with the low end of the limiting-current band; a load that never
   reaches it is not an overload cycle at all and is reported as such instead
   of being run through the thermal model. A load that lands inside the band
   but below the nominal setting is equally refused a thermal run, because
   whether it limits at all depends on where in the band the unit sits.
3. Resolve the pass-element dissipation of one limitation interval. While the
   limiter regulates, the output sits at the product of the limiting current
   and the load resistance, so the pass element carries the limiting current
   across the remaining bus voltage.
4. Propagate a single-pole junction thermal model through the train of
   commanded re-closures: the junction heats for the trip delay and cools for
   the recovery interval, and the train settles on a repeating peak that is
   higher than the first pulse whenever the recovery interval is short
   relative to the thermal time constant.
5. Compare the settled peak junction temperature, the limiting current, the
   average dissipation and the applied trip count against the derating policy
   and the rated repetitive-trip capability, and report the endurance verdict
   with the margin on each check.
"""

import math

__all__ = [
    "DEFAULT_DERATING_POLICY",
    "TEMPERATURE_TOLERANCE_C",
    "RELATIVE_TOLERANCE",
    "average_dissipation_w",
    "assess_lcl_repetitive_overload",
    "cycle_margin",
    "enters_limitation",
    "limiting_output_voltage_v",
    "pass_element_dissipation_w",
    "prospective_current_a",
    "settled_junction_rise_c",
    "thermal_impedance_k_per_w",
    "trip_energy_j",
    "validate_derating_policy",
]

# Derating is declared project policy, not a physical constant, so the numbers
# travel with the result instead of being hidden inside the comparison.
DEFAULT_DERATING_POLICY = {
    "max_junction_temperature_c": 110.0,
    "max_current_fraction": 0.80,
    "max_average_power_fraction": 0.70,
    "min_cycle_margin": 1.0,
}

# A limit comparison can land exactly on its bound in exact arithmetic and a
# few units in the last place off it in floating point. Absorb the
# representation error here rather than by relaxing the engineering limit.
TEMPERATURE_TOLERANCE_C = 1e-9
RELATIVE_TOLERANCE = 1e-12

_POLICY_FRACTION_KEYS = ("max_current_fraction", "max_average_power_fraction")


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


def _non_negative(label, value):
    """Return value as a non-negative finite float."""
    number = _real(label, value)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, number))
    return number


def _fraction(label, value):
    """Return value as a fraction in the half-open interval (0, 1]."""
    number = _real(label, value)
    if number <= 0.0 or number > 1.0:
        raise ValueError("%s must lie in (0, 1], got %g" % (label, number))
    return number


def _count(label, value):
    """Return value as a strictly positive integer count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _at_or_below(value, limit, tolerance):
    """True when value is below limit or on it to within tolerance."""
    return value < limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=tolerance)


def validate_derating_policy(policy):
    """Return the policy after checking every key it has to carry."""
    if not isinstance(policy, dict):
        raise ValueError("derating policy must be a mapping")
    for key in ("max_junction_temperature_c", "min_cycle_margin") + _POLICY_FRACTION_KEYS:
        if key not in policy:
            raise ValueError("derating policy missing required key '%s'" % key)
    _real("max_junction_temperature_c", policy["max_junction_temperature_c"])
    for key in _POLICY_FRACTION_KEYS:
        _fraction(key, policy[key])
    if _real("min_cycle_margin", policy["min_cycle_margin"]) < 1.0:
        raise ValueError("min_cycle_margin below 1.0 would accept more trips than are rated")
    return policy


def prospective_current_a(bus_voltage_v, load_resistance_ohm):
    """Return the current the faulted load would draw with no limiting action."""
    bus = _positive("bus_voltage_v", bus_voltage_v)
    resistance = _positive("load_resistance_ohm", load_resistance_ohm)
    return bus / resistance


def enters_limitation(prospective_current, limiting_current_min_a):
    """True when the overload reaches the low end of the limiting-current band."""
    drawn = _positive("prospective_current", prospective_current)
    threshold = _positive("limiting_current_min_a", limiting_current_min_a)
    return drawn > threshold or math.isclose(
        drawn, threshold, rel_tol=RELATIVE_TOLERANCE, abs_tol=0.0
    )


def limiting_output_voltage_v(limiting_current_a, load_resistance_ohm, bus_voltage_v):
    """Return the regulated output voltage held across the faulted load."""
    current = _positive("limiting_current_a", limiting_current_a)
    resistance = _positive("load_resistance_ohm", load_resistance_ohm)
    bus = _positive("bus_voltage_v", bus_voltage_v)
    output = current * resistance
    if output > bus or math.isclose(output, bus, rel_tol=RELATIVE_TOLERANCE, abs_tol=0.0):
        raise ValueError(
            "load resistance %g ohm draws no more than the limiting current %g A at "
            "%g V, so no limitation interval exists" % (resistance, current, bus)
        )
    return output


def pass_element_dissipation_w(bus_voltage_v, limiting_current_a, load_resistance_ohm):
    """Return the pass-element dissipation while the limiter regulates."""
    output = limiting_output_voltage_v(limiting_current_a, load_resistance_ohm, bus_voltage_v)
    return (float(bus_voltage_v) - output) * float(limiting_current_a)


def trip_energy_j(power_w, trip_delay_s):
    """Return the energy one limitation interval puts into the pass element."""
    power = _positive("power_w", power_w)
    delay = _positive("trip_delay_s", trip_delay_s)
    return power * delay


def thermal_impedance_k_per_w(rth_jc_k_per_w, thermal_tau_s, duration_s):
    """Return the single-pole transient thermal impedance over a duration."""
    rth = _positive("rth_jc_k_per_w", rth_jc_k_per_w)
    tau = _positive("thermal_tau_s", thermal_tau_s)
    duration = _non_negative("duration_s", duration_s)
    return rth * (1.0 - math.exp(-duration / tau))


def settled_junction_rise_c(power_w, rth_jc_k_per_w, thermal_tau_s, on_time_s, off_time_s):
    """Return the first-pulse, settled-peak and settled-valley junction rises.

    The junction heats towards power * rth during the limitation interval and
    cools towards the case during the recovery interval, both with the same
    time constant. Over a repeating train the two exponentials close on a fixed
    point, which is the peak the endurance case has to be judged on.
    """
    power = _positive("power_w", power_w)
    rth = _positive("rth_jc_k_per_w", rth_jc_k_per_w)
    tau = _positive("thermal_tau_s", thermal_tau_s)
    on_time = _positive("on_time_s", on_time_s)
    off_time = _non_negative("off_time_s", off_time_s)
    heat = math.exp(-on_time / tau)
    cool = math.exp(-off_time / tau)
    denominator = 1.0 - heat * cool
    if denominator <= 0.0:
        raise ValueError("degenerate thermal train: the duty cycle leaves no cooling interval")
    first = power * rth * (1.0 - heat)
    peak = first / denominator
    return {
        "first_pulse_rise_c": first,
        "settled_peak_rise_c": peak,
        "settled_valley_rise_c": peak * cool,
        "steady_state_rise_c": power * rth,
    }


def average_dissipation_w(power_w, on_time_s, off_time_s):
    """Return the dissipation averaged over one overload-and-recovery cycle."""
    power = _positive("power_w", power_w)
    on_time = _positive("on_time_s", on_time_s)
    off_time = _non_negative("off_time_s", off_time_s)
    return power * on_time / (on_time + off_time)


def cycle_margin(applied_cycles, rated_cycles):
    """Return the ratio of rated repetitive trips to the trips actually applied."""
    applied = _count("applied_cycles", applied_cycles)
    rated = _count("rated_cycles", rated_cycles)
    return float(rated) / float(applied)


def assess_lcl_repetitive_overload(spec):
    """Run the clause 5.2.10.1.1 repetitive-overload endurance assessment.

    spec keys: bus_voltage_v, limiting_current_a, load_resistance_ohm,
    trip_delay_s, recovery_interval_s, applied_cycles, rated_cycles,
    rth_jc_k_per_w, thermal_tau_s, case_temperature_c,
    pass_element_rated_current_a, pass_element_rated_power_w, and optionally
    limiting_current_tolerance and derating_policy.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "bus_voltage_v",
        "limiting_current_a",
        "load_resistance_ohm",
        "trip_delay_s",
        "recovery_interval_s",
        "applied_cycles",
        "rated_cycles",
        "rth_jc_k_per_w",
        "thermal_tau_s",
        "case_temperature_c",
        "pass_element_rated_current_a",
        "pass_element_rated_power_w",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    policy = validate_derating_policy(spec.get("derating_policy", DEFAULT_DERATING_POLICY))
    bus = _positive("bus_voltage_v", spec["bus_voltage_v"])
    limiting = _positive("limiting_current_a", spec["limiting_current_a"])
    resistance = _positive("load_resistance_ohm", spec["load_resistance_ohm"])
    trip_delay = _positive("trip_delay_s", spec["trip_delay_s"])
    recovery = _non_negative("recovery_interval_s", spec["recovery_interval_s"])
    applied = _count("applied_cycles", spec["applied_cycles"])
    rated_cycles = _count("rated_cycles", spec["rated_cycles"])
    rth = _positive("rth_jc_k_per_w", spec["rth_jc_k_per_w"])
    tau = _positive("thermal_tau_s", spec["thermal_tau_s"])
    case_temperature = _real("case_temperature_c", spec["case_temperature_c"])
    rated_current = _positive("pass_element_rated_current_a", spec["pass_element_rated_current_a"])
    rated_power = _positive("pass_element_rated_power_w", spec["pass_element_rated_power_w"])

    tolerance = spec.get("limiting_current_tolerance", 0.0)
    tolerance = _non_negative("limiting_current_tolerance", tolerance)
    if tolerance >= 1.0:
        raise ValueError("limiting_current_tolerance must be below 1.0, got %g" % tolerance)
    limiting_min = limiting * (1.0 - tolerance)

    findings = []
    drawn = prospective_current_a(bus, resistance)
    if not enters_limitation(drawn, limiting_min):
        findings.append(
            "the declared load draws %.4f A at full bus, below the low end of the "
            "limiting band %.4f A, so no limitation interval occurs and the case is "
            "not a repetitive-overload cycle" % (drawn, limiting_min)
        )
        return {
            "verdict": "overload-below-limitation",
            "compliant": None,
            "prospective_current_a": drawn,
            "limiting_current_min_a": limiting_min,
            "findings": findings,
            "checks": [],
        }

    if limiting * resistance >= bus:
        findings.append(
            "the declared load draws %.4f A, inside the limiting band but below the "
            "nominal setting %.4f A: whether a limitation interval occurs depends on "
            "where in the band the unit actually sits, so the endurance case has to be "
            "re-declared against the band edge that is being demonstrated"
            % (drawn, limiting)
        )
        return {
            "verdict": "overload-inside-limiting-band",
            "compliant": None,
            "prospective_current_a": drawn,
            "limiting_current_min_a": limiting_min,
            "findings": findings,
            "checks": [],
        }

    output_voltage = limiting_output_voltage_v(limiting, resistance, bus)
    power = (bus - output_voltage) * limiting
    energy = trip_energy_j(power, trip_delay)
    rises = settled_junction_rise_c(power, rth, tau, trip_delay, recovery)
    peak_junction = case_temperature + rises["settled_peak_rise_c"]
    first_junction = case_temperature + rises["first_pulse_rise_c"]
    average_power = average_dissipation_w(power, trip_delay, recovery)
    margin = cycle_margin(applied, rated_cycles)

    junction_limit = float(policy["max_junction_temperature_c"])
    current_limit = rated_current * float(policy["max_current_fraction"])
    power_limit = rated_power * float(policy["max_average_power_fraction"])
    cycle_limit = float(policy["min_cycle_margin"])

    checks = [
        {
            "name": "settled-junction-temperature",
            "value": peak_junction,
            "limit": junction_limit,
            "unit": "degC",
            "passed": _at_or_below(peak_junction, junction_limit, TEMPERATURE_TOLERANCE_C),
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
            "name": "repetitive-trip-capability",
            "value": margin,
            "limit": cycle_limit,
            "unit": "ratio",
            "passed": margin > cycle_limit
            or math.isclose(margin, cycle_limit, rel_tol=RELATIVE_TOLERANCE, abs_tol=0.0),
        },
    ]

    for check in checks:
        if not check["passed"]:
            findings.append(
                "%s is %.4f %s against a limit of %.4f %s"
                % (check["name"], check["value"], check["unit"], check["limit"], check["unit"])
            )
    if rises["settled_peak_rise_c"] > rises["first_pulse_rise_c"] * 1.10:
        findings.append(
            "the recovery interval is short against the thermal time constant: the "
            "settled peak rise %.2f K exceeds the first-pulse rise %.2f K by more "
            "than a tenth, so a single-pulse check would understate the case"
            % (rises["settled_peak_rise_c"], rises["first_pulse_rise_c"])
        )

    compliant = all(check["passed"] for check in checks)
    return {
        "verdict": "endurance-demonstrated" if compliant else "endurance-not-demonstrated",
        "compliant": compliant,
        "prospective_current_a": drawn,
        "limiting_current_min_a": limiting_min,
        "limited_output_voltage_v": output_voltage,
        "pass_element_dissipation_w": power,
        "trip_energy_j": energy,
        "average_dissipation_w": average_power,
        "first_pulse_junction_temperature_c": first_junction,
        "settled_peak_junction_temperature_c": peak_junction,
        "junction_rises_c": rises,
        "cycle_margin": margin,
        "checks": checks,
        "findings": findings,
    }
