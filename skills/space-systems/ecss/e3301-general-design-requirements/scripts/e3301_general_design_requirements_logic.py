"""General design requirements for a spacecraft mechanism.

Anchor: ECSS-E-ST-33-01C clause 4.7.2 (general design requirements -- the
mechanism is designed to operate in ground ambient and in thermal vacuum, and
to survive the handling, transport, test, storage, launch and orbit
environments of its own life cycle). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise each declared life-cycle phase environment and refuse a malformed
   or inverted range instead of clamping it.
2. Establish which of the mandatory life-cycle phases are declared at all; an
   absent phase is a coverage gap, never an implicitly benign one.
3. Bound the declared phases into a single enclosing environment, which is the
   envelope the mechanism design has to be shown against.
4. Compare each phase, and the envelope, with the declared design capability:
   temperature enclosure, pressure enclosure, humidity where the phase is at a
   pressure that can carry it, random vibration and shock level.
5. Accumulate the duty the life cycle imposes -- operating hours and actuation
   cycles, ground test cycles included -- and compare with the qualified life.
6. Confirm that both required operating demonstrations, ground ambient and
   thermal vacuum, are declared; a mechanism shown only in one of them is not
   shown.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "REQUIRED_PHASES",
    "REQUIRED_OPERATING_MODES",
    "AMBIENT_PRESSURE_PA",
    "HUMIDITY_RELEVANT_PRESSURE_PA",
    "validate_number",
    "validate_range",
    "encloses",
    "normalise_phase",
    "missing_phases",
    "environment_envelope",
    "cumulative_duty",
    "grade_phase",
    "operating_modes_gap",
    "assess_general_design",
]

# Enclosure comparisons are differences of declared numbers; a limit that is
# physically exactly on the capability bound can land a few ULPs outside it.
MARGIN_TOLERANCE = 1e-9

# The life-cycle phases a mechanism design is shown against.
REQUIRED_PHASES = ("handling", "transport", "test", "storage", "launch", "orbit")

# Both operating demonstrations are required; one alone is not a demonstration.
REQUIRED_OPERATING_MODES = ("ground-ambient", "thermal-vacuum")

AMBIENT_PRESSURE_PA = 101325.0

# Below this pressure there is not enough water vapour present for a relative
# humidity requirement to mean anything, so one declared there is an error.
HUMIDITY_RELEVANT_PRESSURE_PA = 1000.0


def validate_number(label, value, allow_negative=True):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def validate_range(label, low, high, allow_negative=True):
    """Return an ordered (low, high) pair or raise ValueError."""
    low_value = validate_number("%s low" % label, low, allow_negative)
    high_value = validate_number("%s high" % label, high, allow_negative)
    if low_value > high_value:
        raise ValueError(
            "%s is inverted: low %g exceeds high %g" % (label, low_value, high_value)
        )
    return (low_value, high_value)


def encloses(capability, requirement):
    """Return True when the capability range contains the requirement range."""
    cap_low, cap_high = capability
    req_low, req_high = requirement
    low_ok = cap_low <= req_low or math.isclose(
        cap_low, req_low, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    )
    high_ok = cap_high >= req_high or math.isclose(
        cap_high, req_high, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    )
    return low_ok and high_ok


def normalise_phase(name, environment):
    """Return a validated phase environment record.

    environment keys: temperature_c (pair), pressure_pa (pair), optional
    humidity_pct, random_vibration_grms, shock_g, duration_hours, cycles.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("phase name must be a non-empty string")
    if not isinstance(environment, dict):
        raise ValueError("phase '%s' environment must be a mapping" % name)
    for key in ("temperature_c", "pressure_pa"):
        if key not in environment:
            raise ValueError("phase '%s' missing required key '%s'" % (name, key))
        value = environment[key]
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError("phase '%s' key '%s' must be a (low, high) pair" % (name, key))
    temperature = validate_range("phase '%s' temperature_c" % name, *environment["temperature_c"])
    pressure = validate_range(
        "phase '%s' pressure_pa" % name, *environment["pressure_pa"], allow_negative=False
    )
    record = {
        "name": name,
        "temperature_c": temperature,
        "pressure_pa": pressure,
        "humidity_pct": None,
        "random_vibration_grms": validate_number(
            "phase '%s' random_vibration_grms" % name,
            environment.get("random_vibration_grms", 0.0),
            allow_negative=False,
        ),
        "shock_g": validate_number(
            "phase '%s' shock_g" % name,
            environment.get("shock_g", 0.0),
            allow_negative=False,
        ),
        "duration_hours": validate_number(
            "phase '%s' duration_hours" % name,
            environment.get("duration_hours", 0.0),
            allow_negative=False,
        ),
        "cycles": validate_number(
            "phase '%s' cycles" % name,
            environment.get("cycles", 0.0),
            allow_negative=False,
        ),
    }
    if environment.get("humidity_pct") is not None:
        humidity = validate_number(
            "phase '%s' humidity_pct" % name, environment["humidity_pct"], allow_negative=False
        )
        if humidity > 100.0:
            raise ValueError("phase '%s' humidity_pct must not exceed 100" % name)
        if pressure[1] < HUMIDITY_RELEVANT_PRESSURE_PA:
            raise ValueError(
                "phase '%s' declares a humidity requirement at a pressure of %g Pa, "
                "where relative humidity is not a meaningful quantity"
                % (name, pressure[1])
            )
        record["humidity_pct"] = humidity
    return record


def missing_phases(declared_names):
    """Return the mandatory life-cycle phases that were not declared."""
    if not isinstance(declared_names, (list, tuple, set, frozenset)):
        raise ValueError("declared_names must be a sequence of phase names")
    present = set()
    for name in declared_names:
        if not isinstance(name, str):
            raise ValueError("phase names must be strings, got %r" % (name,))
        present.add(name.strip().lower())
    return tuple(phase for phase in REQUIRED_PHASES if phase not in present)


def environment_envelope(phases):
    """Return the bounding environment across a sequence of phase records."""
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("phases must be a non-empty sequence of phase records")
    temp_low = None
    temp_high = None
    pressure_low = None
    pressure_high = None
    vibration = 0.0
    shock = 0.0
    humidity = None
    for phase in phases:
        if not isinstance(phase, dict) or "temperature_c" not in phase:
            raise ValueError("each phase must be a normalised phase record")
        t_low, t_high = phase["temperature_c"]
        p_low, p_high = phase["pressure_pa"]
        temp_low = t_low if temp_low is None else min(temp_low, t_low)
        temp_high = t_high if temp_high is None else max(temp_high, t_high)
        pressure_low = p_low if pressure_low is None else min(pressure_low, p_low)
        pressure_high = p_high if pressure_high is None else max(pressure_high, p_high)
        vibration = max(vibration, phase["random_vibration_grms"])
        shock = max(shock, phase["shock_g"])
        if phase["humidity_pct"] is not None:
            humidity = phase["humidity_pct"] if humidity is None else max(
                humidity, phase["humidity_pct"]
            )
    return {
        "temperature_c": (temp_low, temp_high),
        "pressure_pa": (pressure_low, pressure_high),
        "random_vibration_grms": vibration,
        "shock_g": shock,
        "humidity_pct": humidity,
    }


def cumulative_duty(phases):
    """Return the total operating hours and actuation cycles of the life cycle."""
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("phases must be a non-empty sequence of phase records")
    hours = 0.0
    cycles = 0.0
    for phase in phases:
        if not isinstance(phase, dict) or "duration_hours" not in phase:
            raise ValueError("each phase must be a normalised phase record")
        hours += phase["duration_hours"]
        cycles += phase["cycles"]
    return {"duration_hours": hours, "cycles": cycles}


def grade_phase(phase, capability):
    """Compare one phase environment with the declared design capability."""
    if not isinstance(phase, dict) or "temperature_c" not in phase:
        raise ValueError("phase must be a normalised phase record")
    if not isinstance(capability, dict):
        raise ValueError("capability must be a mapping")
    for key in ("temperature_c", "pressure_pa", "random_vibration_grms", "shock_g"):
        if key not in capability:
            raise ValueError("capability missing required key '%s'" % key)
    cap_temperature = validate_range("capability temperature_c", *capability["temperature_c"])
    cap_pressure = validate_range(
        "capability pressure_pa", *capability["pressure_pa"], allow_negative=False
    )
    cap_vibration = validate_number(
        "capability random_vibration_grms", capability["random_vibration_grms"], False
    )
    cap_shock = validate_number("capability shock_g", capability["shock_g"], False)
    findings = []
    if not encloses(cap_temperature, phase["temperature_c"]):
        findings.append(
            "phase %s temperature range %g..%g C is not enclosed by the design "
            "capability %g..%g C"
            % (
                phase["name"],
                phase["temperature_c"][0],
                phase["temperature_c"][1],
                cap_temperature[0],
                cap_temperature[1],
            )
        )
    if not encloses(cap_pressure, phase["pressure_pa"]):
        findings.append(
            "phase %s pressure range %g..%g Pa is not enclosed by the design "
            "capability %g..%g Pa"
            % (
                phase["name"],
                phase["pressure_pa"][0],
                phase["pressure_pa"][1],
                cap_pressure[0],
                cap_pressure[1],
            )
        )
    if phase["random_vibration_grms"] > cap_vibration and not math.isclose(
        phase["random_vibration_grms"], cap_vibration, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        findings.append(
            "phase %s random vibration %g grms exceeds the design capability %g grms"
            % (phase["name"], phase["random_vibration_grms"], cap_vibration)
        )
    if phase["shock_g"] > cap_shock and not math.isclose(
        phase["shock_g"], cap_shock, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        findings.append(
            "phase %s shock %g g exceeds the design capability %g g"
            % (phase["name"], phase["shock_g"], cap_shock)
        )
    if phase["humidity_pct"] is not None:
        cap_humidity = capability.get("humidity_max_pct")
        if cap_humidity is None:
            findings.append(
                "phase %s declares a humidity of %g %% but the design capability "
                "carries no humidity rating" % (phase["name"], phase["humidity_pct"])
            )
        else:
            cap_humidity = validate_number("capability humidity_max_pct", cap_humidity, False)
            if phase["humidity_pct"] > cap_humidity and not math.isclose(
                phase["humidity_pct"], cap_humidity, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
            ):
                findings.append(
                    "phase %s humidity %g %% exceeds the design capability %g %%"
                    % (phase["name"], phase["humidity_pct"], cap_humidity)
                )
    return {"name": phase["name"], "compliant": not findings, "findings": findings}


def operating_modes_gap(declared_modes):
    """Return the required operating demonstrations that were not declared."""
    if not isinstance(declared_modes, (list, tuple, set, frozenset)):
        raise ValueError("declared_modes must be a sequence of mode names")
    present = set()
    for mode in declared_modes:
        if not isinstance(mode, str):
            raise ValueError("operating mode names must be strings, got %r" % (mode,))
        present.add(mode.strip().lower())
    return tuple(mode for mode in REQUIRED_OPERATING_MODES if mode not in present)


def assess_general_design(spec):
    """Run the full clause 4.7.2 general design assessment.

    spec keys: phases (mapping of phase name to environment), capability
    (mapping), operating_modes (sequence), qualified_life_hours,
    qualified_life_cycles.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "phases",
        "capability",
        "operating_modes",
        "qualified_life_hours",
        "qualified_life_cycles",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    phases_spec = spec["phases"]
    if not isinstance(phases_spec, dict) or not phases_spec:
        raise ValueError("spec['phases'] must be a non-empty mapping")
    records = [normalise_phase(name, env) for name, env in sorted(phases_spec.items())]
    findings = []
    gaps = missing_phases([record["name"] for record in records])
    for gap in gaps:
        findings.append("life-cycle phase '%s' is not declared; coverage gap" % gap)
    graded = [grade_phase(record, spec["capability"]) for record in records]
    for result in graded:
        findings.extend(result["findings"])
    envelope = environment_envelope(records)
    duty = cumulative_duty(records)
    life_hours = validate_number("qualified_life_hours", spec["qualified_life_hours"], False)
    life_cycles = validate_number("qualified_life_cycles", spec["qualified_life_cycles"], False)
    if duty["duration_hours"] > life_hours and not math.isclose(
        duty["duration_hours"], life_hours, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        findings.append(
            "life-cycle operating time %g h exceeds the qualified life %g h"
            % (duty["duration_hours"], life_hours)
        )
    if duty["cycles"] > life_cycles and not math.isclose(
        duty["cycles"], life_cycles, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        findings.append(
            "life-cycle actuation count %g cycles exceeds the qualified life %g cycles"
            % (duty["cycles"], life_cycles)
        )
    mode_gaps = operating_modes_gap(spec["operating_modes"])
    for mode in mode_gaps:
        findings.append("required operating demonstration '%s' is not declared" % mode)
    return {
        "phases": graded,
        "envelope": envelope,
        "duty": duty,
        "missing_phases": gaps,
        "missing_operating_modes": mode_gaps,
        "compliant": not findings,
        "findings": findings,
    }
