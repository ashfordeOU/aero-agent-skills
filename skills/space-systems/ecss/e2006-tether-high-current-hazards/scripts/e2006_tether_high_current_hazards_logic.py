#!/usr/bin/env python3
"""High-current hazards on a tether current loop (ECSS-E-ST-20-06C, 10.2.3).

Offline, deterministic, stdlib-only. The module traces the current a
tethered system drives out along its tether conductor and back through the
structural return path, and grades every segment of that loop for ohmic
dissipation, temperature rise, bonding-joint quality and fault withstand.

Anchor: ECSS-E-ST-20-06C clause 10.2.3 (paraphrased into an implementable
procedure; no verbatim standard text).
"""

import math

# --- segment taxonomy -------------------------------------------------------

SEGMENT_FAMILY = {
    "tether-conductor": "tether",
    "tether-shield": "tether",
    "structural-return-path": "return",
    "bonding-strap": "return",
    "chassis-bond-joint": "return",
    "deployer-slip-ring": "interface",
    "plasma-contactor-lead": "interface",
    "deployment-mechanism-lead": "interface",
}

# Adiabatic material constants k (A*sqrt(s)/mm^2) for the withstand law
# I^2 * t <= (k * A)^2.
MATERIAL_K = {
    "copper": 226.0,
    "aluminium": 148.0,
    "aluminum": 148.0,
    "stainless-steel": 78.0,
    "titanium": 52.0,
}

# Comparison tolerance. A limit check must not fail on the few ULPs a sum or
# difference of floats introduces, so the comparison absorbs representation
# error; the engineering limit itself is never widened.
REL_TOL = 1e-9
ABS_TOL = 1e-12


def _positive(name, value):
    """Return value as a float, raising ValueError unless strictly positive."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return out


def _non_negative(name, value):
    """Return value as a float, raising ValueError if negative or non-finite."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    return out


def within_limit(value, limit):
    """True when value does not exceed limit, absorbing float representation
    error at the exact boundary (the limit is not widened)."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def categorize_segment(kind):
    """Map a loop segment type onto its family: tether, return or interface."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("segment kind must be a non-empty string, got %r" % (kind,))
    key = kind.strip().lower()
    if key not in SEGMENT_FAMILY:
        raise ValueError(
            "uncategorized segment kind %r; known kinds: %s"
            % (kind, ", ".join(sorted(SEGMENT_FAMILY)))
        )
    return SEGMENT_FAMILY[key]


# --- per-segment electrical quantities --------------------------------------


def voltage_drop_v(current_a, resistance_ohm):
    """Ohmic voltage drop I * R across one loop segment, in volts."""
    i = _non_negative("current_a", current_a)
    r = _non_negative("resistance_ohm", resistance_ohm)
    return i * r


def dissipation_w(current_a, resistance_ohm):
    """Ohmic dissipation I^2 * R in one loop segment, in watts."""
    i = _non_negative("current_a", current_a)
    r = _non_negative("resistance_ohm", resistance_ohm)
    return i * i * r


def temperature_rise_k(power_w, thermal_conductance_w_per_k):
    """Steady temperature rise P / G of a segment above its local sink."""
    p = _non_negative("power_w", power_w)
    g = _positive("thermal_conductance_w_per_k", thermal_conductance_w_per_k)
    return p / g


def conductor_temperature_c(sink_temperature_c, rise_k):
    """Segment conductor temperature = local sink temperature + rise."""
    try:
        sink = float(sink_temperature_c)
    except (TypeError, ValueError):
        raise ValueError(
            "sink_temperature_c must be a real number, got %r" % (sink_temperature_c,)
        )
    if math.isnan(sink) or math.isinf(sink):
        raise ValueError("sink_temperature_c must be finite, got %r" % (sink_temperature_c,))
    if sink < -273.15:
        raise ValueError("sink_temperature_c below absolute zero: %r" % (sink_temperature_c,))
    return sink + _non_negative("rise_k", rise_k)


# --- fault behaviour --------------------------------------------------------


def let_through_energy_a2s(fault_current_a, clearing_time_s):
    """Let-through energy I^2 * t deposited by a fault before it is cleared."""
    i = _non_negative("fault_current_a", fault_current_a)
    t = _non_negative("clearing_time_s", clearing_time_s)
    return i * i * t


def adiabatic_withstand_a2s(material, cross_section_mm2):
    """Adiabatic conductor withstand (k * A)^2, in A^2*s."""
    if not isinstance(material, str) or not material.strip():
        raise ValueError("material must be a non-empty string, got %r" % (material,))
    key = material.strip().lower()
    if key not in MATERIAL_K:
        raise ValueError(
            "uncategorized conductor material %r; known: %s"
            % (material, ", ".join(sorted(MATERIAL_K)))
        )
    area = _positive("cross_section_mm2", cross_section_mm2)
    k_a = MATERIAL_K[key] * area
    return k_a * k_a


# --- segment and loop evaluation --------------------------------------------


def evaluate_segment(segment, operating_current_a):
    """Grade one loop segment at the declared operating current.

    segment keys: kind, resistance_ohm, thermal_conductance_w_per_k,
    sink_temperature_c, insulation_rating_c, and optionally rated_current_a,
    allowable_drop_v, joint_resistance_ohm, max_joint_resistance_ohm,
    material, cross_section_mm2, protection_clearing_time_s,
    fault_current_a. Returns a report mapping with a findings list.
    """
    if not isinstance(segment, dict):
        raise ValueError("segment must be a mapping, got %r" % (type(segment).__name__,))
    name = segment.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("segment needs a non-empty 'name', got %r" % (name,))
    family = categorize_segment(segment.get("kind"))
    current = _non_negative("operating_current_a", operating_current_a)
    resistance = _non_negative("resistance_ohm", segment.get("resistance_ohm"))

    drop = voltage_drop_v(current, resistance)
    power = dissipation_w(current, resistance)
    rise = temperature_rise_k(power, segment.get("thermal_conductance_w_per_k"))
    temperature = conductor_temperature_c(segment.get("sink_temperature_c", 20.0), rise)
    rating = _positive("insulation_rating_c", segment.get("insulation_rating_c"))

    findings = []
    if not within_limit(temperature, rating):
        findings.append(
            "conductor-temperature %.2f C exceeds insulation rating %.2f C" % (temperature, rating)
        )

    rated_current = segment.get("rated_current_a")
    if rated_current is None:
        findings.append("no rated-current on record for this segment")
    else:
        rated = _positive("rated_current_a", rated_current)
        if not within_limit(current, rated):
            findings.append(
                "operating current %.3f A exceeds rated current %.3f A" % (current, rated)
            )

    allowable_drop = segment.get("allowable_drop_v")
    if allowable_drop is not None:
        allowed = _positive("allowable_drop_v", allowable_drop)
        if not within_limit(drop, allowed):
            findings.append(
                "voltage-drop %.4f V exceeds allocation %.4f V" % (drop, allowed)
            )

    if family == "return":
        findings.extend(evaluate_bonding_joint(segment))

    return {
        "name": name.strip(),
        "family": family,
        "voltage_drop_v": drop,
        "dissipation_w": power,
        "temperature_rise_k": rise,
        "conductor_temperature_c": temperature,
        "findings": findings,
        "compliant": not findings,
    }


def evaluate_bonding_joint(segment):
    """Return bonding-joint findings for a return-family segment."""
    joint = segment.get("joint_resistance_ohm")
    maximum = segment.get("max_joint_resistance_ohm")
    if joint is None:
        return ["no bonding-joint resistance on record for the structural return"]
    measured = _non_negative("joint_resistance_ohm", joint)
    if maximum is None:
        return ["no maximum bonding-joint resistance on record"]
    limit = _positive("max_joint_resistance_ohm", maximum)
    if not within_limit(measured, limit):
        return [
            "bonding-joint resistance %.6f ohm exceeds maximum %.6f ohm" % (measured, limit)
        ]
    return []


def evaluate_fault_protection(segment, fault_current_a=None):
    """Grade one segment against its fault let-through energy."""
    if not isinstance(segment, dict):
        raise ValueError("segment must be a mapping, got %r" % (type(segment).__name__,))
    clearing = segment.get("protection_clearing_time_s")
    if clearing is None:
        return {
            "name": segment.get("name"),
            "let_through_a2s": None,
            "withstand_a2s": None,
            "findings": ["no protection device on record for this segment"],
            "compliant": False,
        }
    current = fault_current_a
    if current is None:
        current = segment.get("fault_current_a")
    if current is None:
        raise ValueError("fault current not given for segment %r" % (segment.get("name"),))
    energy = let_through_energy_a2s(current, clearing)
    withstand = adiabatic_withstand_a2s(
        segment.get("material"), segment.get("cross_section_mm2")
    )
    findings = []
    if not within_limit(energy, withstand):
        findings.append(
            "let-through-energy %.4g A^2*s exceeds adiabatic withstand %.4g A^2*s"
            % (energy, withstand)
        )
    return {
        "name": segment.get("name"),
        "let_through_a2s": energy,
        "withstand_a2s": withstand,
        "findings": findings,
        "compliant": not findings,
    }


def assess_high_current_hazards(config):
    """Assess a whole tether current loop against clause 10.2.3.

    config keys: operating_current_a, segments (non-empty list), optionally
    fault_current_a and loop_drop_budget_v.
    """
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping, got %r" % (type(config).__name__,))
    segments = config.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("config['segments'] must be a non-empty list")
    current = _non_negative("operating_current_a", config.get("operating_current_a"))
    fault_current = config.get("fault_current_a")

    segment_reports = [evaluate_segment(seg, current) for seg in segments]
    fault_reports = [evaluate_fault_protection(seg, fault_current) for seg in segments]

    families = sorted({rep["family"] for rep in segment_reports})
    loop_drop = sum(rep["voltage_drop_v"] for rep in segment_reports)
    loop_power = sum(rep["dissipation_w"] for rep in segment_reports)

    loop_findings = []
    if "return" not in families:
        loop_findings.append("no return-family segment: the current loop does not close")
    budget = config.get("loop_drop_budget_v")
    if budget is not None:
        allowed = _positive("loop_drop_budget_v", budget)
        if not within_limit(loop_drop, allowed):
            loop_findings.append(
                "loop voltage-drop %.4f V exceeds budget %.4f V" % (loop_drop, allowed)
            )

    segment_findings = [
        "%s: %s" % (rep["name"], f) for rep in segment_reports for f in rep["findings"]
    ]
    fault_findings = [
        "%s: %s" % (rep["name"], f) for rep in fault_reports for f in rep["findings"]
    ]
    all_findings = segment_findings + fault_findings + loop_findings
    return {
        "segments": segment_reports,
        "fault": fault_reports,
        "families": families,
        "loop_voltage_drop_v": loop_drop,
        "loop_dissipation_w": loop_power,
        "findings": all_findings,
        "compliant": not all_findings,
    }
