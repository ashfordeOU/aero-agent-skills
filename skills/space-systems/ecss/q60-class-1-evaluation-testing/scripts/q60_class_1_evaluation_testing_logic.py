"""Evaluation test programme assessment for a candidate class 1 EEE part.

Anchor: ECSS-Q-ST-60C clause 4.2.3.4 — the test programme, the conditions it
is run at and the pass criteria applied while evaluating a part put forward as
a candidate for class 1 flight use. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the candidate part identity: manufacturer, part number and the
   assurance category the part is being evaluated against. A programme with no
   traceable identity evaluates nothing.
2. Validate each programme step: its normalized name, the conditions actually
   applied, the severity the step was required to reach, and the end-point
   measurements taken after it.
3. Compare every applied condition with its required severity in the sense the
   step declares. A hot life step owes an at-least sense, a cold step an
   at-most sense, so the sense travels with the required value rather than
   being assumed from the key.
4. Turn each end-point measurement into a drift fraction against its initial
   reading and hold it to its drift limit, then hold the final reading to the
   absolute limit band when one is declared.
5. Check the programme covers every mandatory step; an absent step is a
   coverage shortfall, not a step that ran with no drift.
6. Return the per-step records, the absent steps and a candidate verdict
   carrying every finding rather than only the first.

Boundary equalities are representation questions and are absorbed by named
tolerances; the declared severities and limits are never relaxed.
"""

import math

__all__ = [
    "MANDATORY_STEPS",
    "CONDITION_SENSES",
    "CONDITION_TOLERANCE",
    "DRIFT_TOLERANCE",
    "normalize_step_name",
    "validate_candidate_part",
    "validate_applied_conditions",
    "validate_required_condition",
    "condition_met",
    "assess_conditions",
    "parameter_drift_fraction",
    "assess_measurement",
    "assess_test_step",
    "missing_steps",
    "assess_evaluation_programme",
]

# Steps an evaluation test programme has to run before a candidate part may be
# put forward for class 1 use. Names are normalized (lower case, hyphenated).
MANDATORY_STEPS = (
    "visual-inspection",
    "electrical-measurement",
    "temperature-cycling",
    "life-test",
    "mechanical-robustness",
)

# A required severity is meaningless without the sense it is read in: a hot
# soak has to reach at least its value, a cold soak at most its value.
CONDITION_SENSES = ("at-least", "at-most")

# An applied condition that exactly meets its required severity can land a few
# units in the last place away from it once it has been through a unit
# conversion. Absorb that here, never by moving the severity.
CONDITION_TOLERANCE = 1e-9

# A drift fraction is a quotient, so an exactly-met drift limit carries the
# same representation question.
DRIFT_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_real(value, label):
    """Return a validated finite real quantity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _require_positive_real(value, label):
    """Return a validated strictly positive finite real quantity."""
    number = _require_real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def normalize_step_name(value, label="step name"):
    """Return a programme step name in normalized lower-case hyphenated form."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_candidate_part(part):
    """Return the validated identity of the candidate part under evaluation."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    for key in ("manufacturer", "part_number", "assurance_category"):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)
    category = normalize_step_name(part["assurance_category"], "assurance_category")
    if category != "class-1":
        raise ValueError(
            "this programme evaluates class 1 candidates, got '%s'" % category
        )
    return {
        "manufacturer": _require_text(part["manufacturer"], "manufacturer"),
        "part_number": _require_text(part["part_number"], "part_number"),
        "assurance_category": category,
    }


def validate_applied_conditions(conditions, label="conditions"):
    """Return the validated conditions a step was actually run at."""
    if not isinstance(conditions, dict) or not conditions:
        raise ValueError("%s must be a non-empty mapping" % label)
    applied = {}
    for key, value in conditions.items():
        name = _require_text(key, "%s key" % label)
        applied[name] = _require_real(value, "%s['%s']" % (label, name))
    return applied


def validate_required_condition(requirement, label="required condition"):
    """Return one validated required severity, value plus the sense it is read in."""
    if not isinstance(requirement, dict):
        raise ValueError("%s must be a mapping carrying 'value' and 'sense'" % label)
    if "value" not in requirement:
        raise ValueError("%s missing required key 'value'" % label)
    sense = requirement.get("sense", "at-least")
    sense = normalize_step_name(sense, "%s sense" % label)
    if sense not in CONDITION_SENSES:
        raise ValueError(
            "%s sense must be one of %s, got '%s'" % (label, list(CONDITION_SENSES), sense)
        )
    return {"value": _require_real(requirement["value"], "%s value" % label), "sense": sense}


def condition_met(applied, required_value, sense):
    """Return whether an applied condition reaches its required severity."""
    applied = _require_real(applied, "applied condition")
    required_value = _require_real(required_value, "required condition value")
    sense = normalize_step_name(sense, "sense")
    if sense not in CONDITION_SENSES:
        raise ValueError("sense must be one of %s, got '%s'" % (list(CONDITION_SENSES), sense))
    if math.isclose(applied, required_value, rel_tol=0.0, abs_tol=CONDITION_TOLERANCE):
        return True
    if sense == "at-least":
        return applied > required_value
    return applied < required_value


def assess_conditions(applied, required):
    """Return per-condition records and findings for one step's severities."""
    applied_map = validate_applied_conditions(applied)
    if not isinstance(required, dict):
        raise ValueError("required conditions must be a mapping")
    records = []
    findings = []
    for key in sorted(required):
        name = _require_text(key, "required condition key")
        spec = validate_required_condition(required[key], "required condition '%s'" % name)
        if name not in applied_map:
            findings.append("condition '%s' was required but never applied" % name)
            records.append({"condition": name, "applied": None, "required": spec["value"],
                            "sense": spec["sense"], "met": False})
            continue
        met = condition_met(applied_map[name], spec["value"], spec["sense"])
        if not met:
            findings.append(
                "condition '%s' applied %g against a required %s %g"
                % (name, applied_map[name], spec["sense"], spec["value"])
            )
        records.append({"condition": name, "applied": applied_map[name],
                        "required": spec["value"], "sense": spec["sense"], "met": met})
    return {"conditions": records, "findings": findings}


def parameter_drift_fraction(initial, final):
    """Return the magnitude of the end-point drift of one measured parameter."""
    start = _require_real(initial, "initial reading")
    end = _require_real(final, "final reading")
    if start == 0.0:
        raise ValueError("initial reading must not be zero; drift would be undefined")
    return abs(end - start) / abs(start)


def assess_measurement(measurement, default_drift_limit):
    """Return a measurement record with its drift and absolute-band verdicts."""
    if not isinstance(measurement, dict):
        raise ValueError("each measurement must be a mapping")
    for key in ("parameter", "initial", "final"):
        if key not in measurement:
            raise ValueError("measurement missing required key '%s'" % key)
    name = _require_text(measurement["parameter"], "parameter")
    drift = parameter_drift_fraction(measurement["initial"], measurement["final"])
    limit = measurement.get("drift_limit_fraction")
    if limit is None:
        limit = default_drift_limit
    limit = _require_positive_real(limit, "drift_limit_fraction for '%s'" % name)
    final = _require_real(measurement["final"], "final reading for '%s'" % name)
    findings = []
    within_drift = drift < limit or math.isclose(
        drift, limit, rel_tol=0.0, abs_tol=DRIFT_TOLERANCE
    )
    if not within_drift:
        findings.append(
            "parameter '%s' drifted %.6f against a limit of %.6f" % (name, drift, limit)
        )
    lower = measurement.get("lower_limit")
    upper = measurement.get("upper_limit")
    if lower is not None:
        lower = _require_real(lower, "lower_limit for '%s'" % name)
    if upper is not None:
        upper = _require_real(upper, "upper_limit for '%s'" % name)
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("limit band for '%s' is inverted" % name)
    within_band = True
    if lower is not None and not condition_met(final, lower, "at-least"):
        within_band = False
    if upper is not None and not condition_met(final, upper, "at-most"):
        within_band = False
    if not within_band:
        findings.append("parameter '%s' ended at %g, outside its limit band" % (name, final))
    return {
        "parameter": name,
        "drift_fraction": drift,
        "drift_limit_fraction": limit,
        "within_drift_limit": within_drift,
        "within_limit_band": within_band,
        "findings": findings,
        "passed": not findings,
    }


def assess_test_step(step, default_drift_limit):
    """Return one programme step record carrying its own verdict and findings."""
    if not isinstance(step, dict):
        raise ValueError("each programme step must be a mapping")
    for key in ("name", "conditions"):
        if key not in step:
            raise ValueError("programme step missing required key '%s'" % key)
    name = normalize_step_name(step["name"])
    condition_result = assess_conditions(step["conditions"], step.get("required_conditions", {}))
    measurements = step.get("measurements", [])
    if not isinstance(measurements, (list, tuple)):
        raise ValueError("measurements for step '%s' must be a sequence" % name)
    records = []
    seen = set()
    findings = list(condition_result["findings"])
    for measurement in measurements:
        record = assess_measurement(measurement, default_drift_limit)
        if record["parameter"] in seen:
            raise ValueError(
                "parameter '%s' is measured twice in step '%s'" % (record["parameter"], name)
            )
        seen.add(record["parameter"])
        records.append(record)
        findings.extend(record["findings"])
    return {
        "name": name,
        "conditions": condition_result["conditions"],
        "measurements": records,
        "findings": findings,
        "passed": not findings,
    }


def missing_steps(records):
    """Return the mandatory programme steps absent from the executed set."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of step records")
    executed = set()
    for record in records:
        if not isinstance(record, dict) or "name" not in record:
            raise ValueError("each record must be a mapping carrying 'name'")
        executed.add(record["name"])
    return [name for name in MANDATORY_STEPS if name not in executed]


def assess_evaluation_programme(spec):
    """Run the full clause 4.2.3.4 evaluation-programme assessment.

    spec keys: part, steps, default_drift_limit_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("part", "steps", "default_drift_limit_fraction"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    identity = validate_candidate_part(spec["part"])
    steps = spec["steps"]
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("spec['steps'] must be a non-empty sequence of programme steps")
    default_limit = _require_positive_real(
        spec["default_drift_limit_fraction"], "default_drift_limit_fraction"
    )

    records = []
    seen = set()
    for step in steps:
        record = assess_test_step(step, default_limit)
        if record["name"] in seen:
            raise ValueError("programme step '%s' is declared twice" % record["name"])
        seen.add(record["name"])
        records.append(record)

    absent = missing_steps(records)
    findings = ["mandatory programme step '%s' was not executed" % name for name in absent]
    for record in records:
        findings.extend(record["findings"])

    return {
        "part": identity,
        "steps": records,
        "missing_steps": absent,
        "default_drift_limit_fraction": default_limit,
        "evaluated": not findings,
        "findings": findings,
    }
