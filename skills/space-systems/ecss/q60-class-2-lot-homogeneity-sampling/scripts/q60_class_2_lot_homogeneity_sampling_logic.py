#!/usr/bin/env python3
"""Composing the class 2 radiation test sample set.

Anchor: ECSS-Q-ST-60C clause 5.5.5 (the set of class 2 parts offered for
radiation verification testing is composed in line with the radiation
standard). Paraphrased into an implementable procedure; no standard text is
reproduced.

A radiation result is a statement about parts that were never irradiated. It
carries to the flight hardware only through two things: the specimens came out
of material the flight parts also came out of, and there were enough of them,
in the right roles, for the test method being run.

Procedure implemented here
--------------------------
1. Validate the flight lot record and every offered specimen: identifier,
   role in the set, and the traceability values the basis will be tested on.
2. Read the axis set the declared traceability basis rests on, and measure
   each specimen against the flight lot on exactly those axes.
3. Size the set the test method demands, in integer arithmetic, from the
   per-condition specimen count, the number of bias conditions, and whether
   the method runs its conditions on one specimen or on fresh ones.
4. Count the roles actually offered against that size.
5. Check the scope the result is going to be written against is one the basis
   can carry, and return one verdict in precedence order.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "RADIATION_TEST_METHODS",
    "SPECIMEN_ROLES",
    "TRACEABILITY_AXES",
    "TRACEABILITY_BASES",
    "BASIS_SUPPORTED_SCOPE",
    "RESULT_SCOPES",
    "SCOPE_STRENGTH",
    "DEFAULT_SAMPLE_PLAN",
    "SAMPLE_SET_COMPOSED",
    "SPECIMEN_OUTSIDE_BASIS",
    "SCOPE_EXCEEDS_BASIS",
    "IRRADIATED_COUNT_SHORT",
    "CONTROL_COUNT_SHORT",
    "SPARE_COUNT_SHORT",
    "validate_sample_plan",
    "required_axes",
    "validate_flight_lot",
    "validate_specimen",
    "validate_specimens",
    "specimen_mismatches",
    "partition_specimens",
    "required_sample_size",
    "role_counts",
    "coverage_fraction",
    "supported_scope",
    "scope_is_supported",
    "assess_radiation_sample_set",
]

# The radiation test methods a class 2 part set is offered against.
RADIATION_TEST_METHODS = (
    "total-ionising-dose",
    "displacement-damage-dose",
    "single-event-effects",
    "single-event-latch-up",
)

# What a specimen is in the set for.
SPECIMEN_ROLES = ("irradiated", "control", "spare")

# Every traceability value a specimen can be measured on.
TRACEABILITY_AXES = (
    "part_number",
    "manufacturer",
    "die_revision",
    "wafer_diffusion_lot",
    "assembly_date_code",
    "package_style",
)

# The axes each declared basis actually rests on. A narrower basis tests more
# axes and therefore supports a stronger claim about the flight lot.
TRACEABILITY_BASES = {
    "same-wafer-diffusion-lot": TRACEABILITY_AXES,
    "same-assembly-date-code": (
        "part_number",
        "manufacturer",
        "die_revision",
        "assembly_date_code",
        "package_style",
    ),
    "same-part-type-heritage": ("part_number", "manufacturer", "die_revision"),
}

# How far a result resting on each basis reaches.
BASIS_SUPPORTED_SCOPE = {
    "same-wafer-diffusion-lot": "lot-specific",
    "same-assembly-date-code": "date-code-family",
    "same-part-type-heritage": "generic-part-type",
}

RESULT_SCOPES = ("lot-specific", "date-code-family", "generic-part-type")

# Higher is a stronger claim. A claim may never sit above what the basis holds.
SCOPE_STRENGTH = {
    "generic-part-type": 1,
    "date-code-family": 2,
    "lot-specific": 3,
}

# Per method: specimens per bias condition, control specimens, spares, and
# whether the conditions consume fresh specimens. A dose method retires a
# specimen once it has been irradiated, so its conditions multiply; an event
# method sweeps its conditions on the same specimen and does not.
DEFAULT_SAMPLE_PLAN = {
    "total-ionising-dose": {
        "irradiated_per_condition": 5,
        "control": 2,
        "spare": 2,
        "conditions_consume_specimens": True,
    },
    "displacement-damage-dose": {
        "irradiated_per_condition": 4,
        "control": 2,
        "spare": 2,
        "conditions_consume_specimens": True,
    },
    "single-event-effects": {
        "irradiated_per_condition": 3,
        "control": 0,
        "spare": 1,
        "conditions_consume_specimens": False,
    },
    "single-event-latch-up": {
        "irradiated_per_condition": 2,
        "control": 0,
        "spare": 1,
        "conditions_consume_specimens": False,
    },
}

SAMPLE_SET_COMPOSED = "radiation-sample-set-composed"
SPECIMEN_OUTSIDE_BASIS = "specimen-outside-traceability-basis"
SCOPE_EXCEEDS_BASIS = "declared-scope-exceeds-traceability-basis"
IRRADIATED_COUNT_SHORT = "irradiated-specimen-count-short"
CONTROL_COUNT_SHORT = "control-specimen-count-short"
SPARE_COUNT_SHORT = "spare-specimen-count-short"

_PLAN_KEYS = (
    "irradiated_per_condition",
    "control",
    "spare",
    "conditions_consume_specimens",
)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _require_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def validate_sample_plan(plan=None):
    """Validate a per-method sample plan, returning the default when omitted."""
    if plan is None:
        return {name: dict(entry) for name, entry in DEFAULT_SAMPLE_PLAN.items()}
    if not isinstance(plan, dict):
        raise ValueError("sample plan must be a mapping, got %r" % (type(plan).__name__,))
    validated = {}
    for name in RADIATION_TEST_METHODS:
        if name not in plan:
            raise ValueError("sample plan has no entry for method %r" % (name,))
        entry = plan[name]
        if not isinstance(entry, dict):
            raise ValueError("sample plan entry %r must be a mapping" % (name,))
        for key in _PLAN_KEYS:
            if key not in entry:
                raise ValueError("sample plan entry %r has no %r" % (name, key))
        consume = entry["conditions_consume_specimens"]
        if not isinstance(consume, bool):
            raise ValueError(
                "conditions_consume_specimens of %r must be a boolean, got %r"
                % (name, consume)
            )
        for key in ("irradiated_per_condition", "control", "spare"):
            value = entry[key]
            if not _is_int(value) or value < 0:
                raise ValueError(
                    "%s of %r must be a non-negative integer, got %r"
                    % (key, name, value)
                )
        if entry["irradiated_per_condition"] < 1:
            raise ValueError(
                "irradiated_per_condition of %r must be at least one" % (name,)
            )
        validated[name] = {key: entry[key] for key in _PLAN_KEYS}
    return validated


def required_axes(basis):
    """The traceability axes a declared basis is measured on."""
    if basis not in TRACEABILITY_BASES:
        raise ValueError(
            "unknown traceability basis %r (known: %s)"
            % (basis, ", ".join(sorted(TRACEABILITY_BASES)))
        )
    return TRACEABILITY_BASES[basis]


def validate_flight_lot(lot):
    """Validate the flight lot record every specimen is measured against."""
    if not isinstance(lot, dict):
        raise ValueError("flight lot must be a mapping, got %r" % (type(lot).__name__,))
    _require_text("flight lot id", lot.get("lot_id"))
    record = {"lot_id": lot["lot_id"]}
    for axis in TRACEABILITY_AXES:
        _require_text("flight lot %s" % (axis,), lot.get(axis))
        record[axis] = lot[axis]
    return record


def validate_specimen(raw):
    """Validate one offered specimen and fill in its traceability record."""
    if not isinstance(raw, dict):
        raise ValueError("specimen must be a mapping, got %r" % (type(raw).__name__,))
    _require_text("specimen id", raw.get("specimen_id"))
    role = raw.get("role")
    if role not in SPECIMEN_ROLES:
        raise ValueError(
            "role of %r must be one of %s, got %r"
            % (raw["specimen_id"], ", ".join(SPECIMEN_ROLES), role)
        )
    record = {"specimen_id": raw["specimen_id"], "role": role}
    for axis in TRACEABILITY_AXES:
        _require_text("%s %s" % (raw["specimen_id"], axis), raw.get(axis))
        record[axis] = raw[axis]
    return record


def validate_specimens(specimens):
    """Validate an offered set and reject a repeated specimen identifier."""
    if not isinstance(specimens, (list, tuple)):
        raise ValueError(
            "specimens must be a list or tuple, got %r" % (type(specimens).__name__,)
        )
    if len(specimens) == 0:
        raise ValueError("at least one specimen must be offered")
    records = [validate_specimen(raw) for raw in specimens]
    seen = set()
    for record in records:
        if record["specimen_id"] in seen:
            raise ValueError("duplicate specimen id %r" % (record["specimen_id"],))
        seen.add(record["specimen_id"])
    return records


def specimen_mismatches(flight_lot, specimen, basis):
    """Axes on which one specimen departs from the flight lot under a basis."""
    lot = validate_flight_lot(flight_lot)
    record = validate_specimen(specimen)
    return tuple(
        axis for axis in required_axes(basis) if record[axis] != lot[axis]
    )


def partition_specimens(flight_lot, specimens, basis):
    """Split an offered set into the specimens the basis holds and the rest."""
    lot = validate_flight_lot(flight_lot)
    records = validate_specimens(specimens)
    axes = required_axes(basis)
    inside = []
    outside = []
    for record in records:
        mismatched = tuple(axis for axis in axes if record[axis] != lot[axis])
        if mismatched:
            outside.append(
                {"specimen_id": record["specimen_id"], "mismatched_axes": mismatched}
            )
        else:
            inside.append(record)
    return {"within_basis": inside, "outside_basis": outside}


def required_sample_size(method, bias_conditions, plan=None):
    """Specimen counts the method demands for the declared bias conditions."""
    if method not in RADIATION_TEST_METHODS:
        raise ValueError(
            "unknown radiation test method %r (known: %s)"
            % (method, ", ".join(RADIATION_TEST_METHODS))
        )
    if not _is_int(bias_conditions) or bias_conditions < 1:
        raise ValueError(
            "bias_conditions must be an integer of at least one, got %r"
            % (bias_conditions,)
        )
    entry = validate_sample_plan(plan)[method]
    per_condition = entry["irradiated_per_condition"]
    if entry["conditions_consume_specimens"]:
        irradiated = per_condition * bias_conditions
    else:
        irradiated = per_condition
    control = entry["control"]
    spare = entry["spare"]
    return {
        "irradiated": irradiated,
        "control": control,
        "spare": spare,
        "total": irradiated + control + spare,
    }


def role_counts(specimens):
    """How many offered specimens sit in each role."""
    records = validate_specimens(specimens)
    counts = {role: 0 for role in SPECIMEN_ROLES}
    for record in records:
        counts[record["role"]] += 1
    return counts


def coverage_fraction(available, required):
    """Share of a required count that an available count reaches, capped at one."""
    for label, value in (("available", available), ("required", required)):
        if not _is_int(value) or value < 0:
            raise ValueError(
                "%s must be a non-negative integer, got %r" % (label, value)
            )
    if required == 0:
        return 1.0
    if available >= required:
        return 1.0
    return available / required


def supported_scope(basis):
    """The scope a result resting on the declared basis can be written to."""
    if basis not in BASIS_SUPPORTED_SCOPE:
        raise ValueError(
            "unknown traceability basis %r (known: %s)"
            % (basis, ", ".join(sorted(BASIS_SUPPORTED_SCOPE)))
        )
    return BASIS_SUPPORTED_SCOPE[basis]


def scope_is_supported(declared_scope, basis):
    """True when the declared scope sits no higher than the basis can hold."""
    if declared_scope not in SCOPE_STRENGTH:
        raise ValueError(
            "unknown result scope %r (known: %s)"
            % (declared_scope, ", ".join(RESULT_SCOPES))
        )
    return SCOPE_STRENGTH[declared_scope] <= SCOPE_STRENGTH[supported_scope(basis)]


def assess_radiation_sample_set(case, plan=None):
    """Compose and grade a whole class 2 radiation test sample set."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (type(case).__name__,))
    for key in ("flight_lot", "specimens", "basis", "method", "bias_conditions"):
        if key not in case:
            raise ValueError("case has no %r" % (key,))
    basis = case["basis"]
    method = case["method"]
    declared_scope = case.get("declared_result_scope", supported_scope(basis))
    split = partition_specimens(case["flight_lot"], case["specimens"], basis)
    required = required_sample_size(method, case["bias_conditions"], plan)
    counts = role_counts(split["within_basis"]) if split["within_basis"] else {
        role: 0 for role in SPECIMEN_ROLES
    }
    findings = []
    for entry in split["outside_basis"]:
        findings.append(
            {
                "specimen_id": entry["specimen_id"],
                "finding": SPECIMEN_OUTSIDE_BASIS,
                "mismatched_axes": entry["mismatched_axes"],
            }
        )
    if not scope_is_supported(declared_scope, basis):
        findings.append(
            {
                "specimen_id": None,
                "finding": SCOPE_EXCEEDS_BASIS,
                "mismatched_axes": (),
            }
        )
    shortfalls = {
        "irradiated": max(0, required["irradiated"] - counts["irradiated"]),
        "control": max(0, required["control"] - counts["control"]),
        "spare": max(0, required["spare"] - counts["spare"]),
    }
    for role, finding in (
        ("irradiated", IRRADIATED_COUNT_SHORT),
        ("control", CONTROL_COUNT_SHORT),
        ("spare", SPARE_COUNT_SHORT),
    ):
        if shortfalls[role] > 0:
            findings.append(
                {"specimen_id": None, "finding": finding, "mismatched_axes": ()}
            )
    order = (
        SPECIMEN_OUTSIDE_BASIS,
        SCOPE_EXCEEDS_BASIS,
        IRRADIATED_COUNT_SHORT,
        CONTROL_COUNT_SHORT,
        SPARE_COUNT_SHORT,
    )
    verdict = SAMPLE_SET_COMPOSED
    for name in order:
        if any(item["finding"] == name for item in findings):
            verdict = name
            break
    return {
        "verdict": verdict,
        "method": method,
        "basis": basis,
        "declared_result_scope": declared_scope,
        "supported_result_scope": supported_scope(basis),
        "required": required,
        "offered_within_basis": counts,
        "outside_basis": split["outside_basis"],
        "shortfalls": shortfalls,
        "irradiated_coverage": coverage_fraction(
            counts["irradiated"], required["irradiated"]
        ),
        "findings": findings,
        "composed": verdict == SAMPLE_SET_COMPOSED,
    }
