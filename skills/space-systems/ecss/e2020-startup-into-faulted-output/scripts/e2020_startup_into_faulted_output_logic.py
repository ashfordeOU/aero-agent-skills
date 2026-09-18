"""Limiter start up into an output that is already faulted.

Anchor: ECSS-E-ST-20C clause 5.2.7.5.1 (a current limiter has to start up
correctly, and stay inside its own ratings while doing so, when the overload
or the short circuit is already sitting on its output before it is turned
on). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the limiter ratings, the bus condition and each declared fault.
2. Solve the start-up operating point for each fault: the prospective current
   the fault would draw unlimited, whether that pulls the limiter into
   limiting, and the current, output voltage and pass-element voltage that
   result. The worst case of the current-limit accuracy band is used, because
   a limiter that limits high dissipates more.
3. Convert the pass-element voltage and the current into the dissipation the
   element carries for the hold time, which is the trip delay unless the
   declared fault clears sooner.
4. Carry the dissipation into a junction temperature through the declared
   thermal resistance and baseplate temperature, and into a pulse energy
   through the hold time.
5. Hold dissipation, junction temperature and pulse energy against their
   ratings, each through a named tolerance so a case cut exactly to a rating
   is not decided by representation error.
6. Group the fault set and report a set that never reaches limiting, or that
   carries no hard short, as a coverage finding rather than a pass.
"""

import math

__all__ = [
    "POWER_TOLERANCE_W",
    "TEMPERATURE_TOLERANCE_C",
    "ENERGY_TOLERANCE_J",
    "ABSOLUTE_ZERO_C",
    "FAULT_KINDS",
    "validate_limiter",
    "validate_bus",
    "validate_fault",
    "prospective_current_a",
    "worst_case_limit_current_a",
    "operating_point",
    "categorize_fault",
    "junction_temperature_c",
    "pulse_energy_j",
    "assess_fault_case",
    "assess_startup_into_fault",
]

# Dissipation, junction temperature and pulse energy are all products and
# differences of measured quantities, so a case cut exactly to a rating can
# land a unit in the last place on either side. Absorb that here instead of
# relaxing the rating.
POWER_TOLERANCE_W = 1e-9
TEMPERATURE_TOLERANCE_C = 1e-9
ENERGY_TOLERANCE_J = 1e-12

ABSOLUTE_ZERO_C = -273.15

FAULT_KINDS = ("short", "overload", "within-rating")


def _real_number(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    number = _real_number(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(value, label):
    number = _real_number(value, label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def _temperature(value, label):
    number = _real_number(value, label)
    if number <= ABSOLUTE_ZERO_C:
        raise ValueError(
            "%s must sit above absolute zero (%g C), got %r"
            % (label, ABSOLUTE_ZERO_C, value)
        )
    return number


def validate_limiter(limiter):
    """Return the validated limiter rating set."""
    if not isinstance(limiter, dict):
        raise ValueError("limiter must be a mapping")
    for key in (
        "limit_current_a",
        "trip_delay_s",
        "max_dissipation_w",
        "max_junction_temperature_c",
        "thermal_resistance_c_per_w",
    ):
        if key not in limiter:
            raise ValueError("limiter missing required key '%s'" % key)
    tolerance = _non_negative(
        limiter.get("current_limit_tolerance", 0.0), "current_limit_tolerance"
    )
    if tolerance >= 1.0:
        raise ValueError(
            "current_limit_tolerance is a fraction below one, got %r" % (tolerance,)
        )
    record = {
        "limit_current_a": _positive(limiter["limit_current_a"], "limit_current_a"),
        "trip_delay_s": _positive(limiter["trip_delay_s"], "trip_delay_s"),
        "max_dissipation_w": _positive(
            limiter["max_dissipation_w"], "max_dissipation_w"
        ),
        "max_junction_temperature_c": _temperature(
            limiter["max_junction_temperature_c"], "max_junction_temperature_c"
        ),
        "thermal_resistance_c_per_w": _non_negative(
            limiter["thermal_resistance_c_per_w"], "thermal_resistance_c_per_w"
        ),
        "current_limit_tolerance": tolerance,
        "on_state_drop_v": _non_negative(
            limiter.get("on_state_drop_v", 0.0), "on_state_drop_v"
        ),
        "max_pulse_energy_j": (
            None
            if limiter.get("max_pulse_energy_j") is None
            else _positive(limiter["max_pulse_energy_j"], "max_pulse_energy_j")
        ),
    }
    return record


def validate_bus(bus):
    """Return the validated bus and baseplate condition."""
    if not isinstance(bus, dict):
        raise ValueError("bus must be a mapping")
    if "bus_voltage_v" not in bus:
        raise ValueError("bus missing required key 'bus_voltage_v'")
    return {
        "bus_voltage_v": _positive(bus["bus_voltage_v"], "bus_voltage_v"),
        "baseplate_temperature_c": _temperature(
            bus.get("baseplate_temperature_c", 20.0), "baseplate_temperature_c"
        ),
    }


def validate_fault(fault, index=0):
    """Return one validated downstream fault record."""
    if not isinstance(fault, dict):
        raise ValueError("fault[%d] must be a mapping" % index)
    if "fault_resistance_ohm" not in fault:
        raise ValueError("fault[%d] missing required key 'fault_resistance_ohm'" % index)
    duration = fault.get("fault_duration_s")
    record = {
        "id": str(fault.get("id", "fault-%d" % index)),
        "fault_resistance_ohm": _non_negative(
            fault["fault_resistance_ohm"], "fault[%d].fault_resistance_ohm" % index
        ),
        "harness_resistance_ohm": _non_negative(
            fault.get("harness_resistance_ohm", 0.0),
            "fault[%d].harness_resistance_ohm" % index,
        ),
        "fault_duration_s": (
            None
            if duration is None
            else _positive(duration, "fault[%d].fault_duration_s" % index)
        ),
    }
    record["total_resistance_ohm"] = (
        record["fault_resistance_ohm"] + record["harness_resistance_ohm"]
    )
    return record


def prospective_current_a(bus_voltage_v, total_resistance_ohm):
    """Return the current the fault would draw with no limiting at all."""
    voltage = _positive(bus_voltage_v, "bus_voltage_v")
    resistance = _non_negative(total_resistance_ohm, "total_resistance_ohm")
    if resistance == 0.0:
        return math.inf
    return voltage / resistance


def worst_case_limit_current_a(limiter):
    """Return the top of the current-limit accuracy band."""
    if not isinstance(limiter, dict):
        raise ValueError("limiter must be a mapping")
    record = limiter if "current_limit_tolerance" in limiter else validate_limiter(limiter)
    return record["limit_current_a"] * (1.0 + record["current_limit_tolerance"])


def categorize_fault(prospective_a, limit_a, short_multiple=10.0):
    """Group a fault as a short, an overload, or a load inside the rating."""
    limit = _positive(limit_a, "limit_a")
    multiple = _positive(short_multiple, "short_multiple")
    if multiple <= 1.0:
        raise ValueError("short_multiple must exceed one, got %r" % (short_multiple,))
    if not isinstance(prospective_a, (int, float)) or isinstance(prospective_a, bool):
        raise ValueError("prospective_a must be a real number, got %r" % (prospective_a,))
    value = float(prospective_a)
    if math.isnan(value):
        raise ValueError("prospective_a must not be a NaN")
    if value <= limit:
        return "within-rating"
    if value >= limit * multiple:
        return "short"
    return "overload"


def operating_point(limiter, bus, fault):
    """Return the start-up operating point of the limiter against one fault."""
    lim = validate_limiter(limiter)
    condition = validate_bus(bus)
    if not isinstance(fault, dict):
        raise ValueError("fault must be a mapping")
    flt = fault if "total_resistance_ohm" in fault else validate_fault(fault)
    prospective = prospective_current_a(
        condition["bus_voltage_v"], flt["total_resistance_ohm"]
    )
    band_top = worst_case_limit_current_a(lim)
    limiting = prospective > band_top
    if limiting:
        current = band_top
        output_voltage = current * flt["total_resistance_ohm"]
        element_voltage = condition["bus_voltage_v"] - output_voltage
        if element_voltage < 0.0:
            element_voltage = 0.0
    else:
        current = prospective
        element_voltage = min(lim["on_state_drop_v"], condition["bus_voltage_v"])
        output_voltage = condition["bus_voltage_v"] - element_voltage
    return {
        "fault_id": flt["id"],
        "prospective_current_a": prospective,
        "limiting": limiting,
        "output_current_a": current,
        "output_voltage_v": output_voltage,
        "element_voltage_v": element_voltage,
        "dissipation_w": element_voltage * current,
        "total_resistance_ohm": flt["total_resistance_ohm"],
    }


def junction_temperature_c(dissipation_w, thermal_resistance_c_per_w, baseplate_c):
    """Return the steady junction temperature reached by that dissipation."""
    power = _non_negative(dissipation_w, "dissipation_w")
    resistance = _non_negative(thermal_resistance_c_per_w, "thermal_resistance_c_per_w")
    base = _temperature(baseplate_c, "baseplate_c")
    return base + power * resistance


def pulse_energy_j(dissipation_w, hold_time_s):
    """Return the energy the pass element carries over the hold time."""
    power = _non_negative(dissipation_w, "dissipation_w")
    hold = _non_negative(hold_time_s, "hold_time_s")
    return power * hold


def assess_fault_case(limiter, bus, fault, short_multiple=10.0):
    """Return the full start-up verdict for one downstream fault."""
    lim = validate_limiter(limiter)
    condition = validate_bus(bus)
    flt = validate_fault(fault)
    point = operating_point(lim, condition, flt)
    hold = lim["trip_delay_s"]
    if flt["fault_duration_s"] is not None and flt["fault_duration_s"] < hold:
        hold = flt["fault_duration_s"]
    junction = junction_temperature_c(
        point["dissipation_w"],
        lim["thermal_resistance_c_per_w"],
        condition["baseplate_temperature_c"],
    )
    energy = pulse_energy_j(point["dissipation_w"], hold)
    kind = categorize_fault(
        point["prospective_current_a"], lim["limit_current_a"], short_multiple
    )

    findings = []
    dissipation_margin = lim["max_dissipation_w"] - point["dissipation_w"]
    if dissipation_margin < -POWER_TOLERANCE_W:
        findings.append(
            "%s: pass element dissipates %.3f W against a %.3f W rating"
            % (flt["id"], point["dissipation_w"], lim["max_dissipation_w"])
        )
    thermal_margin = lim["max_junction_temperature_c"] - junction
    if thermal_margin < -TEMPERATURE_TOLERANCE_C:
        findings.append(
            "%s: junction reaches %.2f C against a %.2f C rating"
            % (flt["id"], junction, lim["max_junction_temperature_c"])
        )
    energy_margin = None
    if lim["max_pulse_energy_j"] is not None:
        energy_margin = lim["max_pulse_energy_j"] - energy
        if energy_margin < -ENERGY_TOLERANCE_J:
            findings.append(
                "%s: %.4f J carried over the %.4f s hold against a %.4f J rating"
                % (flt["id"], energy, hold, lim["max_pulse_energy_j"])
            )
    if not point["limiting"]:
        findings.append(
            "%s: the declared load draws %.3f A, inside the limit, so the case does "
            "not start the unit into a faulted output"
            % (flt["id"], point["prospective_current_a"])
        )
    return {
        "fault_id": flt["id"],
        "fault_kind": kind,
        "operating_point": point,
        "hold_time_s": hold,
        "junction_temperature_c": junction,
        "pulse_energy_j": energy,
        "dissipation_margin_w": dissipation_margin,
        "thermal_margin_c": thermal_margin,
        "energy_margin_j": energy_margin,
        "findings": findings,
        "within_rating": not findings,
    }


def assess_startup_into_fault(spec):
    """Run the full clause 5.2.7.5.1 faulted start-up assessment.

    spec keys: limiter, bus, faults (a non-empty sequence), optional
    short_multiple.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("limiter", "bus", "faults"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    faults = spec["faults"]
    if not isinstance(faults, (list, tuple)) or not faults:
        raise ValueError("spec['faults'] must be a non-empty sequence")
    multiple = spec.get("short_multiple", 10.0)
    cases = [
        assess_fault_case(spec["limiter"], spec["bus"], fault, multiple)
        for fault in faults
    ]
    ids = [case["fault_id"] for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("fault ids must be unique, got %r" % (ids,))

    worst = cases[0]
    for case in cases[1:]:
        if case["junction_temperature_c"] > worst["junction_temperature_c"]:
            worst = case
        elif math.isclose(
            case["junction_temperature_c"],
            worst["junction_temperature_c"],
            rel_tol=1e-12,
            abs_tol=TEMPERATURE_TOLERANCE_C,
        ) and case["operating_point"]["dissipation_w"] > worst["operating_point"][
            "dissipation_w"
        ]:
            worst = case

    findings = []
    for case in cases:
        findings.extend(case["findings"])
    kinds = set(case["fault_kind"] for case in cases)
    if "short" not in kinds:
        findings.append(
            "the fault set carries no hard short; the clause covers a short already "
            "present on the output as well as an overload"
        )
    if "overload" not in kinds:
        findings.append(
            "the fault set carries no overload short of a hard short; the partial "
            "fault is the case that keeps the element in limiting the longest"
        )
    return {
        "cases": cases,
        "worst_case": worst,
        "fault_kinds": sorted(kinds),
        "findings": findings,
        "compliant": not findings,
    }
