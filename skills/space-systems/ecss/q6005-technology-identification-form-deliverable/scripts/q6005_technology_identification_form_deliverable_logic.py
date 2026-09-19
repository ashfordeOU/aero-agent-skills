"""Technology identification form delivered as a data item: fields and structure.

Anchor: ECSS-Q-ST-60-05C Annex A -- the technology identification form that a
hybrid manufacturer supplies as a deliverable data item, and the entries and
arrangement that data item has to carry. Paraphrased into an implementable
acceptance procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise the delivered form into a field map, refusing a malformed or
   duplicated entry.
2. Report the mandated header and body fields that are absent, and the ones
   that are present as a heading with nothing written behind them.
3. Fire the conditional entry rules: a declared option (a hermetic seal, a
   polymer encapsulation, an RF hybrid type) pulls in the further entries that
   option owes, and those entries then count as mandated for this case.
4. Place every delivered entry that is outside the mandated set: an entry
   belonging to a rule that did not fire is out of scope, an entry belonging
   to no rule at all is unknown.
5. Measure how far the delivered arrangement departs from the mandated one
   through the longest run of fields already in sequence.
6. Combine the field completeness and the arrangement into an accept,
   accept-with-remarks or hold verdict with an ordered findings list.
"""

import math

__all__ = [
    "ORDER_TOLERANCE",
    "MANDATED_HEADER_FIELDS",
    "MANDATED_BODY_FIELDS",
    "MANDATED_ORDER",
    "CONDITIONAL_FIELD_RULES",
    "normalise_field_name",
    "normalise_submission",
    "activated_conditional_fields",
    "required_fields",
    "missing_fields",
    "blank_fields",
    "categorize_extra_fields",
    "longest_ordered_run",
    "structure_order_ratio",
    "completeness_ratio",
    "assess_identification_form",
]

# Ratios are counts divided by counts, so an exact 1.0 can still land a few
# ULPs low. Absorb the representation error here instead of loosening the
# acceptance rule itself.
ORDER_TOLERANCE = 1e-12

# The header block identifies the issue of the data item; the body block
# declares the construction technologies the form exists to record.
MANDATED_HEADER_FIELDS = (
    "form_reference",
    "issue",
    "issue_date",
    "manufacturer",
    "manufacturing_line",
    "prepared_by",
    "approved_by",
)

MANDATED_BODY_FIELDS = (
    "hybrid_type",
    "substrate_technology",
    "interconnection_technology",
    "die_attach_technology",
    "encapsulation_technology",
    "sealing_method",
    "process_control_documents",
    "qualification_status",
)

MANDATED_ORDER = MANDATED_HEADER_FIELDS + MANDATED_BODY_FIELDS

# (field, declared value) -> further entries that declaration owes.
CONDITIONAL_FIELD_RULES = {
    ("sealing_method", "hermetic"): (
        "seal_leak_test_method",
        "internal_gas_analysis_reference",
    ),
    ("sealing_method", "non_hermetic"): (
        "moisture_protection_coating",
        "humidity_exposure_evidence",
    ),
    ("encapsulation_technology", "polymer"): ("outgassing_screening_reference",),
    ("hybrid_type", "rf"): ("frequency_range_declaration",),
}

_ALL_CONDITIONAL_FIELDS = frozenset(
    field for owed in CONDITIONAL_FIELD_RULES.values() for field in owed
)


def normalise_field_name(name):
    """Return the canonical spelling of a delivered field label."""
    if not isinstance(name, str):
        raise ValueError("field name must be a string, got %r" % (name,))
    cleaned = name.strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    if not cleaned:
        raise ValueError("field name must not be blank")
    return cleaned


def _normalise_value(value, label):
    """Return the delivered value as a stripped string ('' when nothing given)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        raise ValueError("field '%s' must carry text, not a boolean" % label)
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise ValueError("field '%s' must carry a finite value" % label)
        return str(value)
    if isinstance(value, str):
        return value.strip()
    raise ValueError("field '%s' must carry text, got %r" % (label, type(value).__name__))


def normalise_submission(submission):
    """Return the delivered form as an ordered canonical field map."""
    if not isinstance(submission, dict):
        raise ValueError("submission must be a mapping of field name to value")
    if not submission:
        raise ValueError("submission must carry at least one field")
    fields = {}
    for raw_name, raw_value in submission.items():
        name = normalise_field_name(raw_name)
        if name in fields:
            raise ValueError("field '%s' is delivered more than once" % name)
        fields[name] = _normalise_value(raw_value, name)
    return fields


def activated_conditional_fields(fields):
    """Return the further entries the declared options pull in, sorted."""
    if not isinstance(fields, dict):
        raise ValueError("fields must be a mapping")
    owed = set()
    for (trigger_field, trigger_value), extras in CONDITIONAL_FIELD_RULES.items():
        declared = fields.get(trigger_field)
        if not declared:
            continue
        if normalise_field_name(declared) == trigger_value:
            owed.update(extras)
    return tuple(sorted(owed))


def required_fields(fields):
    """Return the mandated field set for this case, in mandated order."""
    owed = activated_conditional_fields(fields)
    return MANDATED_ORDER + tuple(owed)


def missing_fields(fields):
    """Return the required fields the form never delivered."""
    required = required_fields(fields)
    return tuple(name for name in required if name not in fields)


def blank_fields(fields):
    """Return the required fields delivered as a heading with no value."""
    required = required_fields(fields)
    return tuple(name for name in required if name in fields and fields[name] == "")


def categorize_extra_fields(fields):
    """Group the delivered entries that are outside the mandated set."""
    required = set(required_fields(fields))
    out_of_scope = []
    unknown = []
    for name in fields:
        if name in required:
            continue
        if name in _ALL_CONDITIONAL_FIELDS:
            out_of_scope.append(name)
        else:
            unknown.append(name)
    return {"out_of_scope": tuple(sorted(out_of_scope)), "unknown": tuple(sorted(unknown))}


def longest_ordered_run(delivered, expected):
    """Return the length of the longest delivered run already in mandated order."""
    if not isinstance(delivered, (list, tuple)):
        raise ValueError("delivered order must be a sequence of field names")
    if not isinstance(expected, (list, tuple)) or not expected:
        raise ValueError("expected order must be a non-empty sequence")
    rank = {}
    for position, name in enumerate(expected):
        if not isinstance(name, str):
            raise ValueError("expected order entries must be strings")
        rank[name] = position
    positions = []
    for name in delivered:
        if not isinstance(name, str):
            raise ValueError("delivered order entries must be strings")
        if name in rank:
            positions.append(rank[name])
    if not positions:
        return 0
    best = [1] * len(positions)
    for i in range(1, len(positions)):
        for j in range(i):
            if positions[j] < positions[i] and best[j] + 1 > best[i]:
                best[i] = best[j] + 1
    return max(best)


def structure_order_ratio(delivered, expected):
    """Return the fraction of the recognised delivered entries already in order."""
    run = longest_ordered_run(delivered, expected)
    recognised = sum(1 for name in delivered if name in set(expected))
    if recognised == 0:
        return 0.0
    return run / recognised


def completeness_ratio(fields):
    """Return the fraction of the required entries delivered with a value."""
    required = required_fields(fields)
    if not required:
        return 1.0
    satisfied = sum(
        1 for name in required if name in fields and fields[name] != ""
    )
    return satisfied / len(required)


def assess_identification_form(submission, delivered_order=None):
    """Judge a delivered technology identification form data item.

    Returns the required field set for the case, the absent and blank entries,
    the grouped extra entries, the completeness and arrangement ratios, an
    ordered findings list and an accept / accept-with-remarks / hold verdict.
    """
    fields = normalise_submission(submission)
    if delivered_order is None:
        order = list(fields.keys())
    else:
        if not isinstance(delivered_order, (list, tuple)):
            raise ValueError("delivered_order must be a sequence of field names")
        order = [normalise_field_name(name) for name in delivered_order]
        if sorted(order) != sorted(fields.keys()):
            raise ValueError("delivered_order must list exactly the delivered fields")
    required = required_fields(fields)
    absent = missing_fields(fields)
    blank = blank_fields(fields)
    extras = categorize_extra_fields(fields)
    completeness = completeness_ratio(fields)
    arrangement = structure_order_ratio(order, required)
    in_order = math.isclose(arrangement, 1.0, rel_tol=0.0, abs_tol=ORDER_TOLERANCE)

    findings = []
    for name in absent:
        findings.append("mandated entry '%s' is absent from the delivered form" % name)
    for name in blank:
        findings.append("entry '%s' is delivered as a heading with no value" % name)
    for name in extras["unknown"]:
        findings.append("entry '%s' belongs to no mandated or conditional rule" % name)
    for name in extras["out_of_scope"]:
        findings.append(
            "entry '%s' is only owed when its declaring option is selected" % name
        )
    if not in_order:
        findings.append(
            "delivered arrangement departs from the mandated order "
            "(longest run in sequence covers %.3f of the recognised entries)"
            % arrangement
        )

    blocking = bool(absent) or bool(blank) or bool(extras["unknown"]) or not in_order
    if blocking:
        verdict = "hold"
    elif extras["out_of_scope"]:
        verdict = "accept-with-remarks"
    else:
        verdict = "accept"

    return {
        "fields": fields,
        "required_fields": required,
        "conditional_fields": activated_conditional_fields(fields),
        "missing_fields": absent,
        "blank_fields": blank,
        "extra_fields": extras,
        "completeness_ratio": completeness,
        "structure_order_ratio": arrangement,
        "in_mandated_order": in_order,
        "findings": findings,
        "verdict": verdict,
    }
