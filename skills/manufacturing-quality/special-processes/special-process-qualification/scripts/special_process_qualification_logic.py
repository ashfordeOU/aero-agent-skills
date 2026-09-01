"""Special process qualification for aerospace manufacturing.

A special process (welding, heat treatment, non-destructive testing,
surface finishing, composites processing) is qualified rather than
inspected: the product result cannot be fully verified by inspection
alone, so control moves to the process itself. The process
qualification record (PQR) pins the qualified envelope: parameters
with ranges, process variables, qualification date, and validity. Any
change outside that envelope is a requalification trigger.

This module implements the qualification decision model exercised by
scripts/test_special_process_qualification_logic.py (stdlib unittest,
offline): change classification (parameter, equipment, personnel,
time-interval), qualified-range checking, and the PQR checklist
builder and validator.

Status vocabulary: 'qualified', 'requalify-required', 'out-of-range'.
range_status() reports the fine-grained 'in-range'/'out-of-range'
verdict; assess_change() folds an out-of-range parameter into
'requalify-required' because any out-of-range change is a
requalification trigger.
"""

CHANGE_TYPES = ("parameter", "equipment", "personnel", "time-interval")

QUALIFIED = "qualified"
REQUALIFY = "requalify-required"
OUT_OF_RANGE = "out-of-range"

STATUSES = (QUALIFIED, REQUALIFY, OUT_OF_RANGE)

# The process qualification record (PQR) checklist fields.
REQUIRED_FIELDS = (
    "process_id",
    "parameters",
    "variables",
    "qualification_date",
    "validity",
)


def range_status(value, qualified_range):
    """Classify a value against the qualified (min, max) envelope.

    Returns 'in-range' when lo <= value <= hi, else 'out-of-range'.
    Raises ValueError when qualified_range is not a (min, max) pair,
    when min > max, or when value or a bound is not numeric.
    """
    if not isinstance(qualified_range, (tuple, list)) or len(qualified_range) != 2:
        raise ValueError("qualified_range must be a (min, max) pair")
    lo, hi = qualified_range
    try:
        lo = float(lo)
        hi = float(hi)
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("value and range bounds must be numeric")
    if lo > hi:
        raise ValueError("qualified_range min must be <= max")
    if value < lo or value > hi:
        return OUT_OF_RANGE
    return "in-range"


def assess_change(
    change_type,
    value=None,
    qualified_range=None,
    elapsed_days=None,
    validity_days=None,
):
    """Classify a proposed process change against the qualification.

    change_type in CHANGE_TYPES:
      - 'parameter': a parameter value change; in-range stays
        'qualified', out-of-range is 'requalify-required'.
      - 'equipment': any equipment change is 'requalify-required'.
      - 'personnel': any personnel change is 'requalify-required'.
      - 'time-interval': elapsed_days against validity_days; within
        validity stays 'qualified', expiry is 'requalify-required'.

    Returns one of 'qualified', 'requalify-required', 'out-of-range'.
    Raises ValueError for an unknown change type, a missing or invalid
    qualified_range for 'parameter', or missing or non-numeric days
    for 'time-interval'.
    """
    if change_type not in CHANGE_TYPES:
        raise ValueError("unknown change type: %r" % (change_type,))
    if change_type == "parameter":
        if qualified_range is None:
            raise ValueError("parameter change needs qualified_range")
        if range_status(value, qualified_range) == OUT_OF_RANGE:
            return REQUALIFY
        return QUALIFIED
    if change_type == "equipment":
        return REQUALIFY
    if change_type == "personnel":
        return REQUALIFY
    # time-interval
    if elapsed_days is None or validity_days is None:
        raise ValueError("time-interval change needs elapsed_days and validity_days")
    try:
        elapsed = float(elapsed_days)
        validity = float(validity_days)
    except (TypeError, ValueError):
        raise ValueError("elapsed_days and validity_days must be numeric")
    if validity < 0:
        raise ValueError("validity_days must be >= 0")
    if elapsed > validity:
        return REQUALIFY
    return QUALIFIED


def build_record_checklist(
    process_id, parameters, variables, qualification_date, validity
):
    """Build and validate the process qualification record checklist.

    parameters: non-empty list of {'name', 'min', 'max'} mappings with
      min <= max. variables: list of process variable names (may be
      empty). qualification_date: 'YYYY-MM-DD' string. validity: int
      number of days the qualification holds.

    Returns a dict carrying every REQUIRED_FIELDS key plus 'checklist'
    (one {'field', 'present', 'detail'} item per required field),
    'missing' (list of absent fields), and 'complete' (boolean).
    Raises ValueError when a field has the wrong type or a parameter
    mapping is malformed.
    """
    if not isinstance(process_id, str) or not process_id.strip():
        raise ValueError("process_id must be a non-empty string")
    if not isinstance(parameters, list) or not parameters:
        raise ValueError("parameters must be a non-empty list")
    checked = []
    for p in parameters:
        if not isinstance(p, dict):
            raise ValueError("each parameter must be a mapping")
        name = p.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("each parameter needs a non-empty 'name'")
        if "min" not in p or "max" not in p:
            raise ValueError("parameter %r needs 'min' and 'max'" % (name,))
        try:
            lo = float(p["min"])
            hi = float(p["max"])
        except (TypeError, ValueError):
            raise ValueError("parameter %r bounds must be numeric" % (name,))
        if lo > hi:
            raise ValueError("parameter %r min must be <= max" % (name,))
        checked.append({"name": name, "min": lo, "max": hi})
    if not isinstance(variables, list) or not all(
        isinstance(v, str) for v in variables
    ):
        raise ValueError("variables must be a list of strings")
    if not isinstance(qualification_date, str) or not qualification_date.strip():
        raise ValueError("qualification_date must be a non-empty string")
    if not isinstance(validity, int) or validity <= 0:
        raise ValueError("validity must be a positive int (days)")

    record = {
        "process_id": process_id,
        "parameters": checked,
        "variables": variables,
        "qualification_date": qualification_date,
        "validity": validity,
    }
    missing = validate_record(record)
    record["missing"] = missing
    record["complete"] = not missing
    record["checklist"] = [
        {
            "field": field,
            "present": field not in missing,
            "detail": record.get(field, ""),
        }
        for field in REQUIRED_FIELDS
    ]
    return record


def validate_record(record):
    """Return the list of missing REQUIRED_FIELDS in a record.

    Empty list means the record is complete. Raises ValueError when
    record is not a mapping.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    missing = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None or value == "":
            missing.append(field)
        elif field == "parameters" and not value:
            missing.append(field)
    return missing
