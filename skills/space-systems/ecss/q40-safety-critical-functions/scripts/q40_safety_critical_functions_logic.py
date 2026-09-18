"""Identification and control of safety-critical functions.

Anchor: ECSS-Q-ST-40C clause 6.5 (safety-critical functions and the controls
they carry). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Decide which declared functions are safety-critical, from the worst
   credible consequence of their loss or inadvertent operation.
2. Derive the failure tolerance the severity demands and the number of
   inhibits that tolerance needs.
3. Count only independent inhibits toward the tolerance achieved: inhibits
   sharing a common-cause group are one inhibit between them.
4. Work out which of the clause's control areas each function owes --
   inadvertent-operation prevention, status information to the operator, safe
   shutdown, EEE component selection where the function is in hardware, and
   safety-critical software control where it is in software.
5. Report per function the tolerance shortfall and the control areas still
   open, and roll the whole set up into a verdict.
"""

__all__ = [
    "SEVERITY_ORDER",
    "CRITICAL_SEVERITIES",
    "CONTROL_AREAS",
    "UNIVERSAL_CONTROL_AREAS",
    "REQUIRED_TOLERANCE",
    "FUNCTION_FIELDS",
    "validate_severity",
    "validate_function",
    "is_safety_critical",
    "required_failure_tolerance",
    "required_inhibit_count",
    "independent_inhibit_count",
    "achieved_failure_tolerance",
    "required_controls",
    "missing_controls",
    "assess_function",
    "assess_safety_critical_functions",
]

# Severity of the worst credible consequence, most severe first.
SEVERITY_ORDER = ("catastrophic", "critical", "major", "minor")

# Severities that make a function safety-critical on their own.
CRITICAL_SEVERITIES = ("catastrophic", "critical")

# The control areas the clause puts on a safety-critical function.
CONTROL_AREAS = (
    "inadvertent-operation-prevention",
    "status-information",
    "safe-shutdown",
    "eee-component-selection",
    "software-safety-control",
)

# Areas every safety-critical function owes, whatever it is built from.
UNIVERSAL_CONTROL_AREAS = (
    "inadvertent-operation-prevention",
    "status-information",
    "safe-shutdown",
)

# Failure tolerance demanded by the severity of the consequence.
REQUIRED_TOLERANCE = {
    "catastrophic": 2,
    "critical": 1,
    "major": 0,
    "minor": 0,
}

# The record the assessment accepts for one function.
FUNCTION_FIELDS = (
    "id",
    "severity",
    "controls",
    "inhibits",
    "uses_software",
    "uses_eee",
    "safety_critical",
)


def validate_severity(value):
    """Return a known severity; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("severity must be a string, got %r" % (value,))
    severity = value.strip().lower()
    if severity not in SEVERITY_ORDER:
        raise ValueError(
            "severity must be one of %s, got %r" % (", ".join(SEVERITY_ORDER), value)
        )
    return severity


def _flag(value, label):
    """Return a boolean flag; raise on anything else."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _validate_inhibits(inhibits, label):
    """Return the normalised inhibit list for one function."""
    if inhibits is None:
        return []
    if not isinstance(inhibits, (list, tuple)):
        raise ValueError("%s must be a sequence of inhibit records" % label)
    seen = set()
    result = []
    for index, inhibit in enumerate(inhibits):
        if not isinstance(inhibit, dict):
            raise ValueError("%s[%d] must be a mapping" % (label, index))
        unknown = sorted(key for key in inhibit if key not in ("id", "common_cause_group"))
        if unknown:
            raise ValueError("%s[%d] carries unknown keys: %s" % (label, index, ", ".join(unknown)))
        identifier = inhibit.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("%s[%d].id must be a non-empty string" % (label, index))
        identifier = identifier.strip().lower()
        if identifier in seen:
            raise ValueError("%s lists inhibit %r twice" % (label, identifier))
        seen.add(identifier)
        group = inhibit.get("common_cause_group")
        if group is not None:
            if not isinstance(group, str) or not group.strip():
                raise ValueError(
                    "%s[%d].common_cause_group must be a non-empty string when given"
                    % (label, index)
                )
            group = group.strip().lower()
        result.append({"id": identifier, "common_cause_group": group})
    return result


def validate_function(function, position=0):
    """Return one normalised function record; raise on a malformed one."""
    if not isinstance(function, dict):
        raise ValueError("functions[%d] must be a mapping" % position)
    unknown = sorted(key for key in function if key not in FUNCTION_FIELDS)
    if unknown:
        raise ValueError(
            "functions[%d] carries unknown keys: %s" % (position, ", ".join(unknown))
        )
    identifier = function.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("functions[%d].id must be a non-empty string" % position)
    controls = function.get("controls", {})
    if not isinstance(controls, dict):
        raise ValueError("functions[%d].controls must be a mapping" % position)
    normalised_controls = {}
    for key, value in controls.items():
        if not isinstance(key, str):
            raise ValueError("functions[%d].controls keys must be strings" % position)
        area = key.strip().lower()
        if area not in CONTROL_AREAS:
            raise ValueError(
                "functions[%d].controls names an unknown control area %r" % (position, key)
            )
        normalised_controls[area] = _flag(value, "functions[%d].controls[%r]" % (position, key))
    declared = function.get("safety_critical")
    if declared is not None:
        declared = _flag(declared, "functions[%d].safety_critical" % position)
    return {
        "id": identifier.strip(),
        "severity": validate_severity(function.get("severity")),
        "controls": normalised_controls,
        "inhibits": _validate_inhibits(function.get("inhibits"), "functions[%d].inhibits" % position),
        "uses_software": _flag(function.get("uses_software", False),
                               "functions[%d].uses_software" % position),
        "uses_eee": _flag(function.get("uses_eee", False),
                          "functions[%d].uses_eee" % position),
        "safety_critical": declared,
    }


def is_safety_critical(record):
    """Return True when a normalised function record is safety-critical."""
    if not isinstance(record, dict) or "severity" not in record:
        raise ValueError("record must be a normalised function record")
    if record.get("safety_critical") is not None:
        return bool(record["safety_critical"])
    return record["severity"] in CRITICAL_SEVERITIES


def required_failure_tolerance(severity):
    """Return the failure tolerance the severity demands."""
    return REQUIRED_TOLERANCE[validate_severity(severity)]


def required_inhibit_count(severity):
    """Return the inhibits the demanded tolerance needs."""
    return required_failure_tolerance(severity) + 1


def independent_inhibit_count(inhibits):
    """Return the inhibits that count independently of each other."""
    if not isinstance(inhibits, (list, tuple)):
        raise ValueError("inhibits must be a sequence of normalised inhibit records")
    groups = set()
    loose = 0
    for index, inhibit in enumerate(inhibits):
        if not isinstance(inhibit, dict) or "id" not in inhibit:
            raise ValueError("inhibits[%d] must be a normalised inhibit record" % index)
        group = inhibit.get("common_cause_group")
        if group is None:
            loose += 1
        else:
            groups.add(group)
    return loose + len(groups)


def achieved_failure_tolerance(inhibits):
    """Return the failure tolerance the independent inhibits actually give."""
    independent = independent_inhibit_count(inhibits)
    return independent - 1 if independent > 0 else 0


def required_controls(record):
    """Return the control areas a function owes, in declaration order."""
    if not is_safety_critical(record):
        return ()
    areas = list(UNIVERSAL_CONTROL_AREAS)
    if record.get("uses_eee"):
        areas.append("eee-component-selection")
    if record.get("uses_software"):
        areas.append("software-safety-control")
    return tuple(area for area in CONTROL_AREAS if area in areas)


def missing_controls(record):
    """Return the owed control areas the function does not provide."""
    controls = record.get("controls", {})
    return tuple(area for area in required_controls(record) if not controls.get(area, False))


def assess_function(function, position=0):
    """Grade one function against the clause's criticality and control rules."""
    record = validate_function(function, position)
    critical = is_safety_critical(record)
    required_tolerance = required_failure_tolerance(record["severity"]) if critical else 0
    achieved = achieved_failure_tolerance(record["inhibits"])
    open_areas = missing_controls(record)
    findings = []
    if critical and achieved < required_tolerance:
        findings.append(
            "%s is %s and needs %d-failure tolerance (%d inhibits); %d independent "
            "inhibit(s) give %d"
            % (
                record["id"],
                record["severity"],
                required_tolerance,
                required_tolerance + 1,
                independent_inhibit_count(record["inhibits"]),
                achieved,
            )
        )
    for area in open_areas:
        findings.append("%s has no %s control" % (record["id"], area))
    return {
        "id": record["id"],
        "severity": record["severity"],
        "safety_critical": critical,
        "required_failure_tolerance": required_tolerance,
        "required_inhibits": required_tolerance + 1 if critical else 0,
        "independent_inhibits": independent_inhibit_count(record["inhibits"]),
        "achieved_failure_tolerance": achieved,
        "required_controls": required_controls(record),
        "missing_controls": open_areas,
        "findings": findings,
    }


def assess_safety_critical_functions(functions):
    """Grade a whole function list and roll the findings up."""
    if not isinstance(functions, (list, tuple)) or not functions:
        raise ValueError("functions must be a non-empty sequence of function records")
    graded = []
    seen = set()
    for position, function in enumerate(functions):
        row = assess_function(function, position)
        key = row["id"].lower()
        if key in seen:
            raise ValueError("function id %r appears twice" % row["id"])
        seen.add(key)
        graded.append(row)
    findings = []
    for row in graded:
        findings.extend(row["findings"])
    critical_rows = [row for row in graded if row["safety_critical"]]
    return {
        "functions": graded,
        "function_count": len(graded),
        "safety_critical_count": len(critical_rows),
        "open_control_areas": sorted(
            {area for row in graded for area in row["missing_controls"]}
        ),
        "findings": findings,
        "verdict": "controls-complete" if not findings else "controls-incomplete",
    }
