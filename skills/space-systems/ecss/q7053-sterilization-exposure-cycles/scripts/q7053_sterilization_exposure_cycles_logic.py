"""Delivered exposure accounting for sterilization compatibility cycles.

Anchor: the procedure clause of ECSS-Q-ST-70-53, where specimens are exposed
to the defined sterilization cycles and the delivered exposure is recorded.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each cycle log: strictly increasing time samples with a
   temperature each.
2. Integrate the dwell at or above the set-point, interpolating the crossings
   linearly between the bracketing samples so a coarse log cannot buy dwell.
3. Form the thermal lethality equivalent at the reference temperature, using
   the declared thermal resistance parameter, so differently shaped cycles are
   additive.
4. Accumulate the delivered radiation dose as rate times duration.
5. Grade each cycle against its window (required dwell, material temperature
   limit) and sum the campaign totals.
"""

import math

__all__ = [
    "TIME_TOLERANCE_S",
    "TEMPERATURE_TOLERANCE_C",
    "DOSE_TOLERANCE_KGY",
    "validate_log",
    "peak_temperature",
    "dwell_time_at_or_above",
    "lethality_equivalent_s",
    "accumulated_dose_kgy",
    "grade_cycle",
    "assess_exposure_campaign",
]

# Dwell, temperature and dose comparisons all sit on sums of floats; absorb the
# representation error at the bound rather than relaxing the requirement.
TIME_TOLERANCE_S = 1e-9
TEMPERATURE_TOLERANCE_C = 1e-9
DOSE_TOLERANCE_KGY = 1e-9


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _non_negative(value, label):
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def validate_log(samples):
    """Return the log as [(time_s, temperature_c)] with strictly rising time."""
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError("a cycle log needs at least two (time_s, temperature_c) samples")
    cleaned = []
    for index, item in enumerate(samples):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("log[%d] must be a (time_s, temperature_c) pair" % index)
        time_s = _non_negative(item[0], "log[%d] time_s" % index)
        temperature = _real(item[1], "log[%d] temperature_c" % index)
        cleaned.append((time_s, temperature))
    for index in range(1, len(cleaned)):
        if cleaned[index][0] <= cleaned[index - 1][0]:
            raise ValueError("log times must strictly increase (sample %d)" % index)
    return cleaned


def peak_temperature(samples):
    """Return the highest logged temperature of the cycle."""
    return max(temperature for _time, temperature in validate_log(samples))


def _crossing_time(t0, y0, t1, y1, level):
    """Return the time at which the segment crosses the level."""
    if y1 == y0:
        return t0
    return t0 + (level - y0) * (t1 - t0) / (y1 - y0)


def dwell_time_at_or_above(samples, setpoint_c):
    """Return the seconds spent at or above the set-point, ramps excluded."""
    log = validate_log(samples)
    level = _real(setpoint_c, "setpoint_c")
    total = 0.0
    for index in range(1, len(log)):
        t0, y0 = log[index - 1]
        t1, y1 = log[index]
        above0 = y0 >= level
        above1 = y1 >= level
        if above0 and above1:
            total += t1 - t0
        elif above0 and not above1:
            total += _crossing_time(t0, y0, t1, y1, level) - t0
        elif not above0 and above1:
            total += t1 - _crossing_time(t0, y0, t1, y1, level)
    return total


def lethality_equivalent_s(samples, reference_c, z_value_c):
    """Return the equivalent time at the reference temperature, in seconds.

    The instantaneous rate is ten to the power of the temperature offset over
    the declared thermal resistance parameter; the rate is integrated over the
    log by the trapezium rule.
    """
    log = validate_log(samples)
    reference = _real(reference_c, "reference_c")
    z_value = _real(z_value_c, "z_value_c")
    if z_value <= 0.0:
        raise ValueError("z_value_c must be positive, got %r" % (z_value_c,))
    total = 0.0
    for index in range(1, len(log)):
        t0, y0 = log[index - 1]
        t1, y1 = log[index]
        rate0 = 10.0 ** ((y0 - reference) / z_value)
        rate1 = 10.0 ** ((y1 - reference) / z_value)
        total += 0.5 * (rate0 + rate1) * (t1 - t0)
    return total


def accumulated_dose_kgy(dose_rate_kgy_per_h, duration_s):
    """Return the dose delivered by a radiation cycle, in kilograys."""
    rate = _non_negative(dose_rate_kgy_per_h, "dose_rate_kgy_per_h")
    duration = _non_negative(duration_s, "duration_s")
    return rate * duration / 3600.0


def grade_cycle(cycle, material_limit_c, reference_c, z_value_c):
    """Return the delivered-exposure record for one cycle.

    cycle keys: id, log, setpoint_c, required_dwell_s; optional
    dose_rate_kgy_per_h and dose_duration_s.
    """
    if not isinstance(cycle, dict):
        raise ValueError("cycle must be a mapping")
    for key in ("id", "log", "setpoint_c", "required_dwell_s"):
        if key not in cycle:
            raise ValueError("cycle missing required key '%s'" % key)
    identifier = cycle["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("cycle id must be a non-empty string")
    log = validate_log(cycle["log"])
    setpoint = _real(cycle["setpoint_c"], "cycle %s setpoint_c" % identifier)
    required = _non_negative(
        cycle["required_dwell_s"], "cycle %s required_dwell_s" % identifier
    )
    limit = _real(material_limit_c, "material_limit_c")
    dwell = dwell_time_at_or_above(log, setpoint)
    lethality = lethality_equivalent_s(log, reference_c, z_value_c)
    peak = peak_temperature(log)
    dose = accumulated_dose_kgy(
        cycle.get("dose_rate_kgy_per_h", 0.0), cycle.get("dose_duration_s", 0.0)
    )
    dwell_ok = dwell >= required - TIME_TOLERANCE_S
    peak_ok = peak <= limit + TEMPERATURE_TOLERANCE_C
    return {
        "id": identifier.strip(),
        "dwell_s": dwell,
        "required_dwell_s": required,
        "dwell_met": dwell_ok,
        "peak_temperature_c": peak,
        "material_limit_c": limit,
        "within_material_limit": peak_ok,
        "lethality_equivalent_s": lethality,
        "dose_kgy": dose,
        "conforming": dwell_ok and peak_ok,
    }


def assess_exposure_campaign(spec):
    """Account for everything an exposure campaign delivered.

    spec keys: cycles, material_limit_c, reference_c, z_value_c,
    required_cycles, qualified_dose_kgy.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = ("cycles", "material_limit_c", "reference_c", "z_value_c",
                     "required_cycles", "qualified_dose_kgy")
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    cycles = spec["cycles"]
    if not isinstance(cycles, (list, tuple)) or not cycles:
        raise ValueError("cycles must be a non-empty sequence")
    required_cycles = spec["required_cycles"]
    if not isinstance(required_cycles, int) or isinstance(required_cycles, bool):
        raise ValueError("required_cycles must be an integer")
    if required_cycles < 1:
        raise ValueError("required_cycles must be at least 1, got %d" % required_cycles)
    qualified_dose = _non_negative(spec["qualified_dose_kgy"], "qualified_dose_kgy")
    records = [
        grade_cycle(cycle, spec["material_limit_c"], spec["reference_c"], spec["z_value_c"])
        for cycle in cycles
    ]
    seen = set()
    for record in records:
        if record["id"] in seen:
            raise ValueError("duplicated cycle id %r" % record["id"])
        seen.add(record["id"])
    conforming = [record for record in records if record["conforming"]]
    total_dwell = sum(record["dwell_s"] for record in records)
    total_lethality = sum(record["lethality_equivalent_s"] for record in records)
    total_dose = sum(record["dose_kgy"] for record in records)
    findings = []
    for record in records:
        if not record["dwell_met"]:
            findings.append(
                "cycle %s held %.3f s at the set-point against the required %.3f s"
                % (record["id"], record["dwell_s"], record["required_dwell_s"])
            )
        if not record["within_material_limit"]:
            findings.append(
                "cycle %s peaked at %.3f C, above the material limit %.3f C"
                % (record["id"], record["peak_temperature_c"], record["material_limit_c"])
            )
    if len(conforming) < required_cycles:
        findings.append(
            "campaign delivered %d conforming cycles against the %d required"
            % (len(conforming), required_cycles)
        )
    if total_dose > qualified_dose + DOSE_TOLERANCE_KGY:
        findings.append(
            "accumulated dose %.6f kGy exceeds the qualified %.6f kGy"
            % (total_dose, qualified_dose)
        )
    return {
        "cycles": records,
        "conforming_cycles": len(conforming),
        "required_cycles": required_cycles,
        "total_dwell_s": total_dwell,
        "total_lethality_equivalent_s": total_lethality,
        "total_dose_kgy": total_dose,
        "qualified_dose_kgy": qualified_dose,
        "credited": not findings,
        "findings": findings,
    }
