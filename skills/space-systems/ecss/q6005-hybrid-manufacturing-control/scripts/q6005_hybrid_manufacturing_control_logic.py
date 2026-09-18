"""In-process controls applied while hybrid microcircuits are assembled and sealed.

Anchor: ECSS-Q-ST-60-05 clause 10.1 (the controls a manufacturer keeps over the
production environment and over the assembly and sealing operations carried out
in it, so that what leaves the line is the article the design describes).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* A hybrid is open to the room for most of its build. Every assembly operation
  therefore carries the dirtiest air it may be worked in, and an operation run
  in a dirtier area than its own limit is uncontrolled however well the step
  itself was performed. Sealing is the strictest of them, because whatever is
  in the room at that moment is inside the package for the rest of its life.
* The pre-seal bakeout is a dwell, not a temperature. A hotter bake drives the
  same moisture out in less time, so the required dwell falls as the plateau
  rises, down to a floor below which the mechanism has no time to work at all.
  A bake too hot for the attach materials is a finding, not extra credit.
* Moisture inside the package is decided twice: by the atmosphere the unit is
  sealed in, and by how long the unit stood between the bakeout and the seal.
  A dry gas cannot rescue a unit left open on the bench for an afternoon.
* Bond-strength monitoring is read from the spread of the pull sample, not from
  its mean. A sample whose average is comfortable and whose spread is wide will
  put bonds under the minimum strength on the lots nobody pulled.
* Each control element carries a weight. A few of them are the reason the line
  is controllable at all -- environment monitoring, electrostatic protection,
  bond-strength monitoring, pre-seal inspection, the bakeout and the sealing
  atmosphere -- and a line missing one of those is not graded, it is incomplete.
* The manufacturing-control index is weighted credit over total weight. It
  ranks what is outstanding; a mandatory element out of control, an operation
  in the wrong environment or a failed seal condition decides the outcome on
  its own, at any index.
"""

from __future__ import annotations

import math
import statistics

# Cleanliness grade of an assembly area; the smaller number is the cleaner air.
ENVIRONMENT_GRADES = {
    "grade-5": 5,
    "grade-6": 6,
    "grade-7": 7,
    "grade-8": 8,
    "uncontrolled-shop-floor": 9,
}

# Dirtiest environment each assembly operation may be carried out in.
OPERATION_ENVIRONMENT_LIMIT = {
    "substrate-preparation": 8,
    "die-attach": 6,
    "wire-bonding": 6,
    "pre-seal-visual-inspection": 6,
    "pre-seal-bakeout": 6,
    "package-sealing": 5,
    "external-lead-attach": 8,
    "marking-and-packing": 8,
}

# Operations without which an assembly flow cannot be graded at all.
MANDATORY_OPERATIONS = (
    "die-attach",
    "wire-bonding",
    "pre-seal-visual-inspection",
    "package-sealing",
)

# Relative humidity band an assembly area is held in: dry enough for the
# materials, damp enough for electrostatic charge to bleed away.
MINIMUM_RELATIVE_HUMIDITY_PERCENT = 30.0
MAXIMUM_RELATIVE_HUMIDITY_PERCENT = 60.0

# Pre-seal bakeout plateau and the dwell it has to be held for.
MINIMUM_BAKEOUT_TEMPERATURE_C = 125.0
MAXIMUM_BAKEOUT_TEMPERATURE_C = 200.0
BAKEOUT_DWELL_AT_MINIMUM_HOURS = 4.0
BAKEOUT_DWELL_FLOOR_HOURS = 2.0
# Hours of dwell recovered per degree of plateau above the minimum.
BAKEOUT_DWELL_RECOVERED_PER_DEGREE = 0.04

# Sealing atmosphere and the stand time allowed between bakeout and seal.
SEALING_MOISTURE_LIMIT_PPMV = 5000.0
MAXIMUM_SEAL_DELAY_HOURS = 2.0

# Bond-strength monitoring: the sample the pull test has to be read from and
# the spread the process needs to keep bonds off the minimum strength.
MINIMUM_BOND_PULL_SAMPLE = 4
REQUIRED_BOND_CAPABILITY = 1.0

# Control elements and the share of the line's controllability each supplies.
CONTROL_ELEMENT_WEIGHTS = {
    "assembly-environment-monitoring": 1.0,
    "electrostatic-discharge-control": 1.0,
    "wire-bond-strength-monitoring": 1.0,
    "pre-seal-visual-inspection": 1.0,
    "pre-seal-bakeout-control": 1.0,
    "sealing-atmosphere-control": 1.0,
    "die-attach-process-monitoring": 0.9,
    "operator-certification-currency": 0.8,
    "equipment-calibration-currency": 0.8,
    "traveller-and-process-record": 0.7,
    "material-storage-and-shelf-life-control": 0.6,
    "rework-authorization-and-record": 0.5,
}

# The elements the line's control rests on; without one it is not graded.
MANDATORY_CONTROL_ELEMENTS = (
    "assembly-environment-monitoring",
    "electrostatic-discharge-control",
    "wire-bond-strength-monitoring",
    "pre-seal-visual-inspection",
    "pre-seal-bakeout-control",
    "sealing-atmosphere-control",
)

CONTROL_STATE_CREDIT = {
    "in-control": 1.0,
    "in-control-with-observation": 0.7,
    "out-of-control": 0.0,
    "not-implemented": 0.0,
}

# Manufacturing-control index a controlled line has to reach.
ACCEPTANCE_INDEX = 0.90

# Indices are ratios of sums of weights, and the dwell and moisture bounds are
# meant to be met exactly; a case sitting on a bound can land a few units in
# the last place away from it.
CONTROL_TOLERANCE = 1e-9

VERDICTS = (
    "assembly-process-under-control",
    "assembly-process-under-control-with-open-actions",
    "assembly-process-not-under-control",
    "manufacturing-control-assessment-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _non_negative(value, label):
    """Return ``value`` as a finite float that is not negative, or raise."""
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _text(value, label):
    """Return ``value`` as a non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def environment_grade_value(name):
    """Rank of an assembly-area cleanliness grade; unknown grades are rejected."""
    if name not in ENVIRONMENT_GRADES:
        raise ValueError(
            "unknown environment grade %r (known: %s)"
            % (name, ", ".join(sorted(ENVIRONMENT_GRADES)))
        )
    return ENVIRONMENT_GRADES[name]


def operation_environment_limit(operation):
    """Dirtiest environment one assembly operation may be worked in."""
    if operation not in OPERATION_ENVIRONMENT_LIMIT:
        raise ValueError(
            "unknown assembly operation %r (known: %s)"
            % (operation, ", ".join(sorted(OPERATION_ENVIRONMENT_LIMIT)))
        )
    return OPERATION_ENVIRONMENT_LIMIT[operation]


def operation_environment_is_adequate(operation, grade_name):
    """True when an operation is worked in air at least as clean as it needs."""
    return environment_grade_value(grade_name) <= operation_environment_limit(operation)


def normalize_operations(operations):
    """Validate the declared assembly operations and reject a repeated one."""
    if not isinstance(operations, (list, tuple)):
        raise ValueError(
            "operations must be a list or tuple, got %r" % (type(operations).__name__,)
        )
    if len(operations) == 0:
        raise ValueError("an assembly flow must declare at least one operation")
    seen = set()
    normalized = []
    for raw in operations:
        if not isinstance(raw, dict):
            raise ValueError("operation must be a mapping, got %r" % (type(raw).__name__,))
        name = raw.get("operation")
        operation_environment_limit(name)  # validation only
        if name in seen:
            raise ValueError("duplicate assembly operation %r" % (name,))
        seen.add(name)
        grade = raw.get("environment_grade")
        environment_grade_value(grade)  # validation only
        normalized.append({"operation": name, "environment_grade": grade})
    return normalized


def operations_in_wrong_environment(operations):
    """Operations worked in air dirtier than the operation itself allows."""
    return sorted(
        record["operation"]
        for record in normalize_operations(operations)
        if not operation_environment_is_adequate(
            record["operation"], record["environment_grade"]
        )
    )


def missing_operations(operations):
    """Mandatory assembly operations the declared flow never names."""
    declared = {record["operation"] for record in normalize_operations(operations)}
    return sorted(name for name in MANDATORY_OPERATIONS if name not in declared)


def humidity_within_band(percent):
    """True when the area humidity sits inside the assembly band."""
    value = _real(percent, "relative_humidity_percent")
    if value < 0.0 or value > 100.0:
        raise ValueError("relative_humidity_percent must lie in 0..100, got %r" % (percent,))
    return (
        value >= MINIMUM_RELATIVE_HUMIDITY_PERCENT - CONTROL_TOLERANCE
        and value <= MAXIMUM_RELATIVE_HUMIDITY_PERCENT + CONTROL_TOLERANCE
    )


def required_bakeout_dwell_hours(temperature_c):
    """Dwell a pre-seal bakeout needs at a given plateau temperature."""
    plateau = _real(temperature_c, "bakeout_temperature_c")
    if plateau < MINIMUM_BAKEOUT_TEMPERATURE_C - CONTROL_TOLERANCE:
        raise ValueError(
            "bakeout plateau %r is below the minimum %r degC"
            % (temperature_c, MINIMUM_BAKEOUT_TEMPERATURE_C)
        )
    above = plateau - MINIMUM_BAKEOUT_TEMPERATURE_C
    dwell = BAKEOUT_DWELL_AT_MINIMUM_HOURS - above * BAKEOUT_DWELL_RECOVERED_PER_DEGREE
    return max(dwell, BAKEOUT_DWELL_FLOOR_HOURS)


def assess_bakeout(bakeout):
    """Grade the pre-seal bakeout against the dwell its plateau calls for."""
    if not isinstance(bakeout, dict):
        raise ValueError("bakeout must be a mapping, got %r" % (type(bakeout).__name__,))
    plateau = _real(bakeout.get("temperature_c"), "bakeout_temperature_c")
    dwell = _non_negative(bakeout.get("dwell_hours"), "bakeout_dwell_hours")
    findings = []
    if plateau < MINIMUM_BAKEOUT_TEMPERATURE_C - CONTROL_TOLERANCE:
        findings.append("bakeout-plateau-below-minimum")
        required = BAKEOUT_DWELL_AT_MINIMUM_HOURS
    else:
        required = required_bakeout_dwell_hours(plateau)
    if plateau > MAXIMUM_BAKEOUT_TEMPERATURE_C + CONTROL_TOLERANCE:
        findings.append("bakeout-plateau-above-material-limit")
    if dwell < required - CONTROL_TOLERANCE:
        findings.append("bakeout-dwell-below-required")
    return {
        "temperature_c": plateau,
        "dwell_hours": dwell,
        "required_dwell_hours": required,
        "adequate": len(findings) == 0,
        "findings": findings,
    }


def assess_seal_atmosphere(seal):
    """Grade the sealing atmosphere and the stand time before the seal."""
    if not isinstance(seal, dict):
        raise ValueError("seal atmosphere must be a mapping, got %r" % (type(seal).__name__,))
    moisture = _non_negative(seal.get("moisture_ppmv"), "sealing_moisture_ppmv")
    delay = _non_negative(seal.get("delay_after_bakeout_hours"), "delay_after_bakeout_hours")
    findings = []
    if moisture > SEALING_MOISTURE_LIMIT_PPMV + CONTROL_TOLERANCE:
        findings.append("sealing-atmosphere-moisture-above-limit")
    if delay > MAXIMUM_SEAL_DELAY_HOURS + CONTROL_TOLERANCE:
        findings.append("seal-delayed-beyond-allowed-stand-time")
    return {
        "moisture_ppmv": moisture,
        "delay_after_bakeout_hours": delay,
        "moisture_margin_ppmv": SEALING_MOISTURE_LIMIT_PPMV - moisture,
        "acceptable": len(findings) == 0,
        "findings": findings,
    }


def bond_strength_capability(samples, minimum_strength_gf):
    """Read bond-strength monitoring from the spread of a pull sample."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples must be a list or tuple, got %r" % (type(samples).__name__,))
    if len(samples) < MINIMUM_BOND_PULL_SAMPLE:
        raise ValueError(
            "a pull sample needs at least %d readings, got %d"
            % (MINIMUM_BOND_PULL_SAMPLE, len(samples))
        )
    values = [_real(value, "pull_strength_gf") for value in samples]
    for value in values:
        if value < 0.0:
            raise ValueError("pull strength must not be negative, got %r" % (value,))
    floor = _real(minimum_strength_gf, "minimum_strength_gf")
    if floor <= 0.0:
        raise ValueError("minimum_strength_gf must be positive, got %r" % (minimum_strength_gf,))
    mean = statistics.fmean(values)
    spread = statistics.pstdev(values)
    below = [value for value in values if value < floor - CONTROL_TOLERANCE]
    if spread <= CONTROL_TOLERANCE:
        capability = math.inf if mean > floor + CONTROL_TOLERANCE else 0.0
    else:
        capability = (mean - floor) / (3.0 * spread)
    findings = []
    if below:
        findings.append("pull-reading-below-minimum-strength")
    if capability < REQUIRED_BOND_CAPABILITY - CONTROL_TOLERANCE:
        findings.append("bond-strength-spread-too-wide")
    return {
        "sample_size": len(values),
        "mean_strength_gf": mean,
        "spread_gf": spread,
        "minimum_observed_gf": min(values),
        "capability": capability,
        "readings_below_minimum": len(below),
        "capable": len(findings) == 0,
        "findings": findings,
    }


def control_element_weight(name):
    """Weight of one control element; unknown element names are rejected."""
    if name not in CONTROL_ELEMENT_WEIGHTS:
        raise ValueError(
            "unknown control element %r (known: %s)"
            % (name, ", ".join(sorted(CONTROL_ELEMENT_WEIGHTS)))
        )
    return CONTROL_ELEMENT_WEIGHTS[name]


def control_state_credit(state):
    """Credit a control-element state earns."""
    if state not in CONTROL_STATE_CREDIT:
        raise ValueError(
            "unknown control state %r (known: %s)"
            % (state, ", ".join(sorted(CONTROL_STATE_CREDIT)))
        )
    return CONTROL_STATE_CREDIT[state]


def normalize_control_element(raw):
    """Validate one control-element record and fill its default state."""
    if not isinstance(raw, dict):
        raise ValueError("control element must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("element")
    control_element_weight(name)  # validation only
    state = raw.get("state", "not-implemented")
    control_state_credit(state)  # validation only
    return {"element": name, "state": state}


def assess_control_element(raw):
    """Grade one control element into a credit and its findings."""
    record = normalize_control_element(raw)
    name = record["element"]
    state = record["state"]
    weight = control_element_weight(name)
    credit = control_state_credit(state)
    findings = []
    if state == "in-control-with-observation":
        findings.append("control-element-observation-open")
    elif state == "out-of-control":
        findings.append("control-element-out-of-control")
    elif state == "not-implemented":
        findings.append("control-element-not-implemented")
    mandatory = name in MANDATORY_CONTROL_ELEMENTS
    return {
        "element": name,
        "state": state,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory": mandatory,
        "mandatory_missing": mandatory and state == "not-implemented",
        "mandatory_out_of_control": mandatory and state == "out-of-control",
        "findings": findings,
    }


def manufacturing_control_index(records):
    """Weighted credit of a set of graded control elements over total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("a control assessment must carry at least one element")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total control weight must be positive")
    return earned / total_weight


def assess_manufacturing_control(
    line_id,
    operations,
    elements,
    bakeout,
    seal_atmosphere,
    bond_pull=None,
    relative_humidity_percent=None,
):
    """Grade the in-process control of one hybrid assembly line, with a verdict."""
    _text(line_id, "line_id")
    if not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a list or tuple, got %r" % (type(elements).__name__,))

    normalized_operations = normalize_operations(operations)
    wrong_environment = operations_in_wrong_environment(normalized_operations)
    absent_operations = missing_operations(normalized_operations)

    declared_elements = {}
    for raw in elements:
        record = normalize_control_element(raw)
        if record["element"] in declared_elements:
            raise ValueError("duplicate control element %r" % (record["element"],))
        declared_elements[record["element"]] = record
    element_records = []
    for name in sorted(CONTROL_ELEMENT_WEIGHTS):
        element_records.append(assess_control_element(declared_elements.get(name, {"element": name})))
    index = manufacturing_control_index(element_records)

    bakeout_record = assess_bakeout(bakeout)
    seal_record = assess_seal_atmosphere(seal_atmosphere)

    bond_record = None
    if bond_pull is not None:
        if not isinstance(bond_pull, dict):
            raise ValueError("bond_pull must be a mapping, got %r" % (type(bond_pull).__name__,))
        bond_record = bond_strength_capability(
            bond_pull.get("samples_gf"), bond_pull.get("minimum_strength_gf")
        )

    humidity_ok = None
    if relative_humidity_percent is not None:
        humidity_ok = humidity_within_band(relative_humidity_percent)

    findings = []
    for name in absent_operations:
        findings.append(
            {
                "item": name,
                "finding": "mandatory-operation-not-declared",
                "detail": "the flow never names this operation",
            }
        )
    for name in wrong_environment:
        findings.append(
            {
                "item": name,
                "finding": "operation-in-environment-dirtier-than-allowed",
                "detail": "grade limit %d" % (operation_environment_limit(name),),
            }
        )
    for record in element_records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["element"], "finding": finding, "detail": record["state"]}
            )
    for finding in bakeout_record["findings"]:
        findings.append(
            {
                "item": "pre-seal-bakeout",
                "finding": finding,
                "detail": "%.2f h at %.1f degC, %.2f h required"
                % (
                    bakeout_record["dwell_hours"],
                    bakeout_record["temperature_c"],
                    bakeout_record["required_dwell_hours"],
                ),
            }
        )
    for finding in seal_record["findings"]:
        findings.append(
            {
                "item": "package-sealing",
                "finding": finding,
                "detail": "%.1f ppmv, %.2f h after bakeout"
                % (seal_record["moisture_ppmv"], seal_record["delay_after_bakeout_hours"]),
            }
        )
    if bond_record is not None:
        for finding in bond_record["findings"]:
            findings.append(
                {
                    "item": "wire-bond-strength-monitoring",
                    "finding": finding,
                    "detail": "%d readings, capability %.3f"
                    % (bond_record["sample_size"], bond_record["capability"]),
                }
            )
    if humidity_ok is False:
        findings.append(
            {
                "item": "assembly-area-humidity",
                "finding": "area-humidity-outside-assembly-band",
                "detail": "%.1f %%rh" % (float(relative_humidity_percent),),
            }
        )

    incomplete = bool(absent_operations) or any(r["mandatory_missing"] for r in element_records)
    uncontrolled = (
        bool(wrong_environment)
        or any(r["mandatory_out_of_control"] for r in element_records)
        or not bakeout_record["adequate"]
        or not seal_record["acceptable"]
        or (bond_record is not None and not bond_record["capable"])
        or index < ACCEPTANCE_INDEX - CONTROL_TOLERANCE
    )
    if incomplete:
        verdict = "manufacturing-control-assessment-incomplete"
    elif uncontrolled:
        verdict = "assembly-process-not-under-control"
    elif findings:
        verdict = "assembly-process-under-control-with-open-actions"
    else:
        verdict = "assembly-process-under-control"
    return {
        "line_id": line_id,
        "operations": normalized_operations,
        "operations_in_wrong_environment": wrong_environment,
        "missing_operations": absent_operations,
        "element_records": element_records,
        "manufacturing_control_index": index,
        "bakeout": bakeout_record,
        "seal_atmosphere": seal_record,
        "bond_strength": bond_record,
        "humidity_within_band": humidity_ok,
        "findings": findings,
        "verdict": verdict,
        "line_under_control": verdict
        in (
            "assembly-process-under-control",
            "assembly-process-under-control-with-open-actions",
        ),
    }
