"""Electrical design specification content for a microwave monolithic circuit.

Anchor: ECSS-Q-ST-60-12 clause 7.2.1 (the performance parameters, interfaces
and operating conditions captured before circuit design work begins).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the operating envelope the specification declares: an ordered
   ambient temperature range and an ordered supply voltage range.
2. Validate every performance parameter: a name, a unit, at least one bound,
   bounds that are ordered, and the condition the bound is stated at.
3. Compare the declared parameters with the mandated set, so a parameter the
   specification omits is a gap and a parameter outside the mandated set is a
   project addition rather than a gap.
4. Grade each parameter for the unit its quantity is stated in, for a test
   condition without which the bound cannot be verified, and for a stated
   condition that sits outside the declared operating envelope.
5. Grade the interface definitions: an RF port owes a reference impedance, a
   DC port owes a bias voltage, and every mandated port owes a definition.
6. Return a completeness ratio and the release verdict for the draft.
"""

import math

__all__ = [
    "MANDATED_PARAMETERS",
    "MANDATED_INTERFACES",
    "RF_PORTS",
    "DC_PORTS",
    "RATIO_TOLERANCE",
    "validate_range",
    "validate_parameter",
    "build_parameter_set",
    "parameter_coverage",
    "unit_mismatches",
    "missing_test_conditions",
    "out_of_envelope_conditions",
    "validate_interface",
    "interface_gaps",
    "completeness_ratio",
    "assess_electrical_specification",
]

# The performance parameters a microwave circuit specification has to bound
# before circuit design starts, with the unit each quantity is stated in.
MANDATED_PARAMETERS = {
    "operating-frequency-band": "GHz",
    "small-signal-gain": "dB",
    "gain-flatness": "dB",
    "noise-figure": "dB",
    "output-power": "dBm",
    "input-return-loss": "dB",
    "output-return-loss": "dB",
    "supply-voltage": "V",
    "supply-current": "mA",
}

# Ports whose definition the specification has to carry.
RF_PORTS = ("rf-input", "rf-output")
DC_PORTS = ("dc-bias",)
MANDATED_INTERFACES = RF_PORTS + DC_PORTS + ("ground-reference",)

# Ratio and envelope comparisons are float divisions and differences; absorb
# representation error here instead of widening the declared envelope.
RATIO_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a stripped non-empty string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _canonical(value, label):
    """Return a canonical hyphenated lowercase name."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def _real(value, label):
    """Return a finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def validate_range(pair, label):
    """Return an ordered (low, high) operating range, or raise."""
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low = _real(pair[0], "%s low" % label)
    high = _real(pair[1], "%s high" % label)
    if low > high:
        raise ValueError("%s low %g exceeds high %g" % (label, low, high))
    return (low, high)


def validate_parameter(parameter):
    """Return one validated performance-parameter record, or raise."""
    if not isinstance(parameter, dict):
        raise ValueError("each parameter must be a mapping, got %r" % (parameter,))
    if "name" not in parameter:
        raise ValueError("parameter missing required key 'name'")
    name = _canonical(parameter["name"], "parameter name")
    unit = parameter.get("unit")
    unit = _require_text(unit, "parameter %s unit" % name) if unit is not None else None
    minimum = parameter.get("minimum")
    maximum = parameter.get("maximum")
    if minimum is None and maximum is None:
        raise ValueError("parameter %s states neither a minimum nor a maximum" % name)
    if minimum is not None:
        minimum = _real(minimum, "parameter %s minimum" % name)
    if maximum is not None:
        maximum = _real(maximum, "parameter %s maximum" % name)
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError(
            "parameter %s has minimum %g above maximum %g" % (name, minimum, maximum)
        )
    condition = parameter.get("test_condition")
    if condition is not None:
        condition = _require_text(condition, "parameter %s test_condition" % name)
    temperature = parameter.get("condition_temperature_c")
    if temperature is not None:
        temperature = _real(temperature, "parameter %s condition_temperature_c" % name)
    supply = parameter.get("condition_supply_v")
    if supply is not None:
        supply = _real(supply, "parameter %s condition_supply_v" % name)
    return {
        "name": name,
        "unit": unit,
        "minimum": minimum,
        "maximum": maximum,
        "test_condition": condition,
        "condition_temperature_c": temperature,
        "condition_supply_v": supply,
    }


def build_parameter_set(parameters):
    """Return the validated parameter set, refusing a repeated parameter name."""
    if not isinstance(parameters, (list, tuple)) or not parameters:
        raise ValueError("parameters must be a non-empty sequence of mappings")
    records = []
    seen = set()
    for parameter in parameters:
        record = validate_parameter(parameter)
        if record["name"] in seen:
            raise ValueError("parameter %s is stated twice" % record["name"])
        seen.add(record["name"])
        records.append(record)
    return records


def parameter_coverage(records):
    """Return the covered, missing and additional performance parameters."""
    declared = {record["name"] for record in records}
    mandated = sorted(MANDATED_PARAMETERS)
    covered = [name for name in mandated if name in declared]
    missing = [name for name in mandated if name not in declared]
    additional = sorted(name for name in declared if name not in MANDATED_PARAMETERS)
    return {"covered": covered, "missing": missing, "additional": additional}


def unit_mismatches(records):
    """Return (name, stated_unit, expected_unit) for every wrong or absent unit."""
    findings = []
    for record in records:
        expected = MANDATED_PARAMETERS.get(record["name"])
        if expected is None:
            continue
        if record["unit"] != expected:
            findings.append((record["name"], record["unit"], expected))
    return findings


def missing_test_conditions(records):
    """Return the names of bounded parameters stated without a test condition."""
    return [record["name"] for record in records if record["test_condition"] is None]


def _outside(value, low, high):
    """True when value sits outside [low, high] by more than the tolerance."""
    span = max(abs(low), abs(high), 1.0)
    slack = span * RATIO_TOLERANCE
    return value < low - slack or value > high + slack


def out_of_envelope_conditions(records, temperature_range_c, supply_range_v):
    """Return the parameters whose stated condition leaves the declared envelope."""
    t_low, t_high = validate_range(temperature_range_c, "temperature_range_c")
    v_low, v_high = validate_range(supply_range_v, "supply_range_v")
    findings = []
    for record in records:
        temperature = record["condition_temperature_c"]
        if temperature is not None and _outside(temperature, t_low, t_high):
            findings.append(
                (record["name"], "condition_temperature_c", temperature, (t_low, t_high))
            )
        supply = record["condition_supply_v"]
        if supply is not None and _outside(supply, v_low, v_high):
            findings.append(
                (record["name"], "condition_supply_v", supply, (v_low, v_high))
            )
    return findings


def validate_interface(interface):
    """Return one validated interface record, or raise."""
    if not isinstance(interface, dict):
        raise ValueError("each interface must be a mapping, got %r" % (interface,))
    if "name" not in interface:
        raise ValueError("interface missing required key 'name'")
    name = _canonical(interface["name"], "interface name")
    impedance = interface.get("impedance_ohm")
    if impedance is not None:
        impedance = _real(impedance, "interface %s impedance_ohm" % name)
        if impedance <= 0.0:
            raise ValueError(
                "interface %s impedance_ohm must be positive, got %g" % (name, impedance)
            )
    bias = interface.get("bias_voltage_v")
    if bias is not None:
        bias = _real(bias, "interface %s bias_voltage_v" % name)
    return {"name": name, "impedance_ohm": impedance, "bias_voltage_v": bias}


def interface_gaps(interfaces):
    """Return the interface definition gaps of the draft.

    Keys: 'absent' (a mandated port with no definition), 'no_impedance' (an RF
    port with no reference impedance) and 'no_bias' (a DC port with no bias
    voltage).
    """
    records = []
    seen = set()
    for interface in interfaces or []:
        record = validate_interface(interface)
        if record["name"] in seen:
            raise ValueError("interface %s is defined twice" % record["name"])
        seen.add(record["name"])
        records.append(record)
    by_name = {record["name"]: record for record in records}
    absent = [name for name in MANDATED_INTERFACES if name not in by_name]
    no_impedance = [
        name for name in RF_PORTS
        if name in by_name and by_name[name]["impedance_ohm"] is None
    ]
    no_bias = [
        name for name in DC_PORTS
        if name in by_name and by_name[name]["bias_voltage_v"] is None
    ]
    return {
        "records": records,
        "absent": absent,
        "no_impedance": no_impedance,
        "no_bias": no_bias,
    }


def completeness_ratio(records, gaps):
    """Return the share of mandated parameters and ports the draft carries."""
    coverage = parameter_coverage(records)
    total = len(MANDATED_PARAMETERS) + len(MANDATED_INTERFACES)
    present = len(coverage["covered"]) + (len(MANDATED_INTERFACES) - len(gaps["absent"]))
    return present / float(total)


def assess_electrical_specification(spec):
    """Run the full clause 7.2.1 electrical-specification content assessment.

    spec keys: parameters (sequence), interfaces (sequence),
    temperature_range_c (pair), supply_range_v (pair).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("parameters", "interfaces", "temperature_range_c", "supply_range_v"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    records = build_parameter_set(spec["parameters"])
    coverage = parameter_coverage(records)
    units = unit_mismatches(records)
    conditions = missing_test_conditions(records)
    envelope = out_of_envelope_conditions(
        records, spec["temperature_range_c"], spec["supply_range_v"]
    )
    gaps = interface_gaps(spec["interfaces"])
    ratio = completeness_ratio(records, gaps)

    findings = []
    if coverage["missing"]:
        findings.append(
            "%d mandated performance parameter(s) are not bounded: %s"
            % (len(coverage["missing"]), ", ".join(coverage["missing"]))
        )
    if units:
        findings.append(
            "%d parameter(s) are stated in the wrong unit: %s"
            % (len(units), ", ".join("%s (%r, expected %s)" % u for u in units))
        )
    if conditions:
        findings.append(
            "%d parameter(s) carry no test condition and cannot be verified: %s"
            % (len(conditions), ", ".join(conditions))
        )
    if envelope:
        findings.append(
            "%d stated condition(s) sit outside the declared operating envelope: %s"
            % (len(envelope), ", ".join("%s %s=%g" % (e[0], e[1], e[2]) for e in envelope))
        )
    if gaps["absent"]:
        findings.append(
            "%d mandated interface(s) are undefined: %s"
            % (len(gaps["absent"]), ", ".join(gaps["absent"]))
        )
    if gaps["no_impedance"]:
        findings.append(
            "%d RF port(s) carry no reference impedance: %s"
            % (len(gaps["no_impedance"]), ", ".join(gaps["no_impedance"]))
        )
    if gaps["no_bias"]:
        findings.append(
            "%d DC port(s) carry no bias voltage: %s"
            % (len(gaps["no_bias"]), ", ".join(gaps["no_bias"]))
        )

    return {
        "parameters": records,
        "covered_parameters": coverage["covered"],
        "missing_parameters": coverage["missing"],
        "additional_parameters": coverage["additional"],
        "unit_mismatches": units,
        "missing_test_conditions": conditions,
        "out_of_envelope": envelope,
        "interfaces": gaps["records"],
        "absent_interfaces": gaps["absent"],
        "rf_ports_without_impedance": gaps["no_impedance"],
        "dc_ports_without_bias": gaps["no_bias"],
        "completeness_ratio": ratio,
        "findings": findings,
        "released": not findings,
    }
