"""General tribology: providing a lubrication function and choosing a lubricant.

Anchor: ECSS-E-ST-33-01C clause 4.7.3.1 (tribology, general -- a lubrication
function is provided between surfaces moving relative to each other, and it
holds for the specified life; the lubricant chosen is a qualified one suited to
the load, speed, cycle count and temperature of the duty). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Reduce the duty of a moving interface to the four quantities a lubricant is
   chosen on: peak Hertzian contact pressure, sliding speed, required life in
   cycles after the life factor, and the temperature range to be covered.
2. Walk the candidate list and keep only lubricants that are qualified, that
   cover the whole duty temperature range, and that carry a rated pressure,
   speed and cycle capability at or above what the duty asks for.
3. Report, for every candidate, the governing margin -- the smallest of the
   pressure, speed and cycle ratios -- because that is the one that decides
   whether the lubrication function survives the specified life.
4. Order the survivors by governing margin and break ties by name so the
   selection is reproducible across runs and machines.
5. Raise an explicit finding when no candidate survives, naming the duty
   quantity that eliminated each one, rather than returning the least bad.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "DEFAULT_LIFE_FACTOR",
    "validate_positive",
    "validate_non_negative",
    "at_least",
    "sliding_speed_m_s",
    "dn_value",
    "hertz_point_contact_pressure_mpa",
    "required_life_cycles",
    "duty_from_interface",
    "temperature_gap",
    "screen_candidate",
    "rank_candidates",
    "assess_lubricant_selection",
]

# Capability ratios are quotients of declared numbers; a capability physically
# exactly equal to the duty can land a few ULPs below unity.
MARGIN_TOLERANCE = 1e-9

# Cycle life is demonstrated with a factor on the duty count, not against the
# duty count itself.
DEFAULT_LIFE_FACTOR = 2.0


def validate_positive(label, value):
    """Return value as a strictly positive finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def at_least(capability, requirement):
    """Return True when capability meets requirement within the tolerance."""
    capability = float(capability)
    requirement = float(requirement)
    if capability >= requirement:
        return True
    return math.isclose(capability, requirement, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0)


def sliding_speed_m_s(radius_mm, speed_rpm):
    """Return the surface sliding speed at a radius, in m/s."""
    radius = validate_positive("radius_mm", radius_mm)
    rpm = validate_non_negative("speed_rpm", speed_rpm)
    return 2.0 * math.pi * (radius / 1000.0) * (rpm / 60.0)


def dn_value(bore_mm, speed_rpm):
    """Return the bearing DN value (bore in mm times speed in rpm)."""
    bore = validate_positive("bore_mm", bore_mm)
    rpm = validate_non_negative("speed_rpm", speed_rpm)
    return bore * rpm


def hertz_point_contact_pressure_mpa(load_n, radius_mm, effective_modulus_mpa):
    """Return the peak Hertzian pressure of a ball on a flat race, in MPa."""
    load = validate_positive("load_n", load_n)
    radius = validate_positive("radius_mm", radius_mm)
    modulus = validate_positive("effective_modulus_mpa", effective_modulus_mpa)
    radius_m = radius / 1000.0
    modulus_pa = modulus * 1.0e6
    contact_radius_m = (3.0 * load * radius_m / (4.0 * modulus_pa)) ** (1.0 / 3.0)
    pressure_pa = 3.0 * load / (2.0 * math.pi * contact_radius_m * contact_radius_m)
    return pressure_pa / 1.0e6


def required_life_cycles(duty_cycles, life_factor=DEFAULT_LIFE_FACTOR):
    """Return the cycle count the lubrication function is demonstrated to."""
    cycles = validate_non_negative("duty_cycles", duty_cycles)
    factor = validate_positive("life_factor", life_factor)
    if factor < 1.0:
        raise ValueError("life_factor must be at least 1.0, got %r" % (life_factor,))
    return cycles * factor


def duty_from_interface(spec):
    """Reduce a moving-interface description to the four selection quantities.

    spec keys: load_n, contact_radius_mm, effective_modulus_mpa, radius_mm,
    speed_rpm, duty_cycles, temperature_c (pair), optional life_factor and
    bore_mm.
    """
    if not isinstance(spec, dict):
        raise ValueError("interface spec must be a mapping")
    required = (
        "load_n",
        "contact_radius_mm",
        "effective_modulus_mpa",
        "radius_mm",
        "speed_rpm",
        "duty_cycles",
        "temperature_c",
    )
    for key in required:
        if key not in spec:
            raise ValueError("interface spec missing required key '%s'" % key)
    temperature = spec["temperature_c"]
    if not isinstance(temperature, (list, tuple)) or len(temperature) != 2:
        raise ValueError("interface spec 'temperature_c' must be a (low, high) pair")
    t_low = float(temperature[0])
    t_high = float(temperature[1])
    for label, value in (("temperature_c low", t_low), ("temperature_c high", t_high)):
        if not math.isfinite(value):
            raise ValueError("%s must be finite" % label)
    if t_low > t_high:
        raise ValueError("temperature_c is inverted: %g exceeds %g" % (t_low, t_high))
    duty = {
        "contact_pressure_mpa": hertz_point_contact_pressure_mpa(
            spec["load_n"], spec["contact_radius_mm"], spec["effective_modulus_mpa"]
        ),
        "sliding_speed_m_s": sliding_speed_m_s(spec["radius_mm"], spec["speed_rpm"]),
        "required_cycles": required_life_cycles(
            spec["duty_cycles"], spec.get("life_factor", DEFAULT_LIFE_FACTOR)
        ),
        "temperature_c": (t_low, t_high),
    }
    if "bore_mm" in spec:
        duty["dn_value"] = dn_value(spec["bore_mm"], spec["speed_rpm"])
    return duty


def temperature_gap(duty_range, candidate_range):
    """Return the cold and hot shortfalls in K; zero means covered."""
    duty_low, duty_high = float(duty_range[0]), float(duty_range[1])
    cand_low, cand_high = float(candidate_range[0]), float(candidate_range[1])
    if cand_low > cand_high:
        raise ValueError("candidate temperature range is inverted")
    cold = max(0.0, cand_low - duty_low)
    hot = max(0.0, duty_high - cand_high)
    return (cold, hot)


def screen_candidate(candidate, duty):
    """Evaluate one candidate lubricant against the reduced duty."""
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a mapping")
    if not isinstance(duty, dict):
        raise ValueError("duty must be a mapping")
    for key in ("contact_pressure_mpa", "sliding_speed_m_s", "required_cycles", "temperature_c"):
        if key not in duty:
            raise ValueError("duty missing required key '%s'" % key)
    required = (
        "name",
        "qualified",
        "max_contact_pressure_mpa",
        "max_sliding_speed_m_s",
        "qualified_cycles",
        "temperature_c",
    )
    for key in required:
        if key not in candidate:
            raise ValueError("candidate missing required key '%s'" % key)
    name = candidate["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("candidate name must be a non-empty string")
    if not isinstance(candidate["qualified"], bool):
        raise ValueError("candidate '%s' key 'qualified' must be a boolean" % name)
    cand_range = candidate["temperature_c"]
    if not isinstance(cand_range, (list, tuple)) or len(cand_range) != 2:
        raise ValueError("candidate '%s' temperature_c must be a (low, high) pair" % name)
    pressure_capability = validate_positive(
        "candidate '%s' max_contact_pressure_mpa" % name, candidate["max_contact_pressure_mpa"]
    )
    speed_capability = validate_positive(
        "candidate '%s' max_sliding_speed_m_s" % name, candidate["max_sliding_speed_m_s"]
    )
    cycle_capability = validate_positive(
        "candidate '%s' qualified_cycles" % name, candidate["qualified_cycles"]
    )
    reasons = []
    if not candidate["qualified"]:
        reasons.append("lubricant is not qualified for space use")
    pressure_margin = pressure_capability / duty["contact_pressure_mpa"]
    if not at_least(pressure_capability, duty["contact_pressure_mpa"]):
        reasons.append(
            "rated contact pressure %g MPa is below the duty %g MPa"
            % (pressure_capability, duty["contact_pressure_mpa"])
        )
    if duty["sliding_speed_m_s"] > 0.0:
        speed_margin = speed_capability / duty["sliding_speed_m_s"]
        if not at_least(speed_capability, duty["sliding_speed_m_s"]):
            reasons.append(
                "rated sliding speed %g m/s is below the duty %g m/s"
                % (speed_capability, duty["sliding_speed_m_s"])
            )
    else:
        speed_margin = float("inf")
    if duty["required_cycles"] > 0.0:
        cycle_margin = cycle_capability / duty["required_cycles"]
        if not at_least(cycle_capability, duty["required_cycles"]):
            reasons.append(
                "qualified life %g cycles is below the required %g cycles"
                % (cycle_capability, duty["required_cycles"])
            )
    else:
        cycle_margin = float("inf")
    cold, hot = temperature_gap(duty["temperature_c"], cand_range)
    if cold > 0.0:
        reasons.append("does not reach %g K below its rated cold limit" % cold)
    if hot > 0.0:
        reasons.append("falls %g K short of the duty hot limit" % hot)
    finite_margins = [
        margin for margin in (pressure_margin, speed_margin, cycle_margin) if math.isfinite(margin)
    ]
    governing = min(finite_margins) if finite_margins else float("inf")
    return {
        "name": name,
        "suitable": not reasons,
        "pressure_margin": pressure_margin,
        "speed_margin": speed_margin,
        "cycle_margin": cycle_margin,
        "governing_margin": governing,
        "temperature_shortfall_k": (cold, hot),
        "reasons": reasons,
    }


def rank_candidates(candidates, duty):
    """Return every screened candidate, survivors first by governing margin."""
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("candidates must be a non-empty sequence")
    screened = [screen_candidate(candidate, duty) for candidate in candidates]
    names = [record["name"] for record in screened]
    if len(set(names)) != len(names):
        raise ValueError("candidate names must be unique for a reproducible ranking")
    return sorted(
        screened,
        key=lambda record: (not record["suitable"], -record["governing_margin"], record["name"]),
    )


def assess_lubricant_selection(spec):
    """Run the full clause 4.7.3.1 lubricant selection assessment.

    spec keys: interface (see duty_from_interface) and candidates (sequence).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("interface", "candidates"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    duty = duty_from_interface(spec["interface"])
    ranked = rank_candidates(spec["candidates"], duty)
    survivors = [record for record in ranked if record["suitable"]]
    findings = []
    selected = None
    if survivors:
        selected = survivors[0]
    else:
        findings.append(
            "no candidate provides the lubrication function for the specified life; "
            + "; ".join(
                "%s: %s" % (record["name"], ", ".join(record["reasons"])) for record in ranked
            )
        )
    return {
        "duty": duty,
        "ranked": ranked,
        "survivors": survivors,
        "selected": selected,
        "compliant": bool(survivors),
        "findings": findings,
    }
