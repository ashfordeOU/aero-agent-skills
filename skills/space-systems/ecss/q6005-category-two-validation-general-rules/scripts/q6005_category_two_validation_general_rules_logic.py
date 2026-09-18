"""General rules governing a category two validation of a hybrid supplier.

Anchor: ECSS-Q-ST-60-05 clause 6.3.1 (the overarching conditions and the scope
that apply when a supplier holding no approved production line is put through a
validation).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* A category two validation is the route for a supplier whose line carries no
  standing approval. Because nothing about the line has been accepted in
  advance, the entry conditions are the whole of the admissibility argument:
  each one is graded on its own and the ones the route exists to check cannot
  be traded against the rest.
* The line has to have been stable for a declared window before the validation
  starts. A line changed inside that window is a different line from the one
  the evidence would describe, so the validation is not admissible yet rather
  than admissible with a caveat.
* The result is bounded by what was actually examined. A technology family or
  a package type the supplier declared but the validation never looked at sits
  outside the envelope, and the envelope is reported with the verdict so no
  later procurement reads the result as covering the whole catalogue.
* Three elements have to be planned together -- the teardown construction
  analysis of sample units, the on-site quality and technical audit, and the
  evaluation testing. An element nobody planned makes the validation
  incomplete, at any readiness index.
* The readiness index is weighted credit over total weight. It ranks what is
  outstanding; an unmet mandatory condition, an unstable line or a missing
  element decides the outcome on its own.
* The validity period starts from the full term and is cut by reservations
  carried forward, because a reservation is evidence the line moved once and
  may move again.
"""

from __future__ import annotations

import math

# Entry conditions and the share of the admissibility argument each supplies.
ENTRY_CONDITION_WEIGHTS = {
    "supplier-quality-system-certified": 1.0,
    "production-line-identified-and-frozen": 1.0,
    "declared-technology-family-in-scope": 0.9,
    "validation-authority-nominated": 0.8,
    "customer-agreement-recorded": 0.7,
    "product-range-declared": 0.6,
    "process-documentation-released": 0.6,
    "previous-validation-history-disclosed": 0.4,
}

# The conditions this route exists to check; unmet, the route is not open.
MANDATORY_ENTRY_CONDITIONS = (
    "supplier-quality-system-certified",
    "production-line-identified-and-frozen",
    "declared-technology-family-in-scope",
    "validation-authority-nominated",
)

CONDITION_STATE_CREDIT = {
    "met": 1.0,
    "met-with-reservation": 0.6,
    "not-met": 0.0,
    "not-assessed": 0.0,
}

# The three elements a category two validation is made of.
VALIDATION_ELEMENTS = (
    "construction-analysis-of-sample-units",
    "supplier-quality-and-technical-audit",
    "evaluation-testing-of-sample-units",
)

# Technology families a category two validation envelope can be drawn around.
TECHNOLOGY_FAMILIES = (
    "thick-film-hybrid",
    "thin-film-hybrid",
    "multichip-module",
    "mixed-technology-hybrid",
    "power-hybrid",
)

# Months the line must have run unchanged before the validation may start.
LINE_STABILITY_WINDOW_MONTHS = 6.0

# Full validity term of a category two validation result.
BASE_VALIDITY_MONTHS = 24.0

# Months struck off the term for each condition carried with a reservation.
VALIDITY_PENALTY_PER_RESERVATION_MONTHS = 3.0

# Shortest term a validation result is still worth issuing for.
MINIMUM_VALIDITY_MONTHS = 6.0

# Readiness index an admissible validation has to reach.
ADMISSIBILITY_INDEX = 0.85

# Indices are ratios of sums of weights and terms are sums of months; a case
# meant to sit on a bound can land a few units in the last place away from it.
VALIDATION_TOLERANCE = 1e-9

VERDICTS = (
    "category-two-validation-admissible",
    "category-two-validation-admissible-with-reservations",
    "category-two-validation-not-admissible",
    "category-two-validation-preconditions-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _text(value, label):
    """Return ``value`` as a non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _names(value, label):
    """Return a list/tuple of non-empty strings with no repeat, or raise."""
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (label, type(value).__name__))
    seen = set()
    out = []
    for item in value:
        name = _text(item, "%s entry" % (label,))
        if name in seen:
            raise ValueError("duplicate %s entry %r" % (label, name))
        seen.add(name)
        out.append(name)
    return out


def technology_family_in_scope(family):
    """True when a declared technology family can carry this validation route."""
    name = _text(family, "technology_family")
    return name in TECHNOLOGY_FAMILIES


def condition_weight(name):
    """Weight of one entry condition; unknown condition names are rejected."""
    if name not in ENTRY_CONDITION_WEIGHTS:
        raise ValueError(
            "unknown entry condition %r (known: %s)"
            % (name, ", ".join(sorted(ENTRY_CONDITION_WEIGHTS)))
        )
    return ENTRY_CONDITION_WEIGHTS[name]


def state_credit(state):
    """Credit an entry-condition state earns."""
    if state not in CONDITION_STATE_CREDIT:
        raise ValueError(
            "unknown condition state %r (known: %s)"
            % (state, ", ".join(sorted(CONDITION_STATE_CREDIT)))
        )
    return CONDITION_STATE_CREDIT[state]


def normalize_condition(raw):
    """Validate one entry-condition record and fill its default state."""
    if not isinstance(raw, dict):
        raise ValueError("condition must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("condition")
    condition_weight(name)  # validation only
    state = raw.get("state", "not-assessed")
    state_credit(state)  # validation only
    return {"condition": name, "state": state}


def assess_condition(raw):
    """Grade one entry condition into a credit and its findings."""
    record = normalize_condition(raw)
    name = record["condition"]
    state = record["state"]
    weight = condition_weight(name)
    credit = state_credit(state)
    findings = []
    if state == "met-with-reservation":
        findings.append("condition-met-with-reservation")
    elif state == "not-met":
        findings.append("entry-condition-not-met")
    elif state == "not-assessed":
        findings.append("entry-condition-not-assessed")
    mandatory_unmet = name in MANDATORY_ENTRY_CONDITIONS and state in (
        "not-met",
        "not-assessed",
    )
    if mandatory_unmet:
        findings.append("mandatory-entry-condition-unmet")
    return {
        "condition": name,
        "state": state,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory_unmet": mandatory_unmet,
        "findings": findings,
    }


def readiness_index(records):
    """Weighted credit of a set of graded entry conditions over total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("a validation must carry at least one entry condition")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total entry-condition weight must be positive")
    return earned / total_weight


def line_is_stable(months_since_last_line_change):
    """True when the line has run unchanged for the declared stability window."""
    months = _real(months_since_last_line_change, "months_since_last_line_change")
    if months < 0.0:
        raise ValueError("months_since_last_line_change must not be negative, got %r" % (months,))
    return months >= LINE_STABILITY_WINDOW_MONTHS - VALIDATION_TOLERANCE


def scope_envelope(declared_scope, examined_scope):
    """Split a declared product range into what the result covers and what it does not.

    Only what the validation actually examined sits inside the envelope. An
    examined item nobody declared is reported as well, because the result then
    covers material the procurement never asked about.
    """
    declared = _names(declared_scope, "declared_scope")
    examined = _names(examined_scope, "examined_scope")
    if len(declared) == 0:
        raise ValueError("a validation must declare at least one product-range item")
    if len(examined) == 0:
        raise ValueError("a validation must examine at least one product-range item")
    declared_set = set(declared)
    examined_set = set(examined)
    return {
        "inside_envelope": sorted(declared_set & examined_set),
        "declared_not_examined": sorted(declared_set - examined_set),
        "examined_not_declared": sorted(examined_set - declared_set),
    }


def element_coverage(planned_elements):
    """Mandatory validation elements the plan never named."""
    planned = set(_names(planned_elements, "planned_elements"))
    unknown = sorted(planned - set(VALIDATION_ELEMENTS))
    if unknown:
        raise ValueError(
            "unknown validation element(s) %s (known: %s)"
            % (", ".join(unknown), ", ".join(VALIDATION_ELEMENTS))
        )
    return [name for name in VALIDATION_ELEMENTS if name not in planned]


def validity_months(reservation_count):
    """Validity term left once reservations carried forward are struck off."""
    if isinstance(reservation_count, bool) or not isinstance(reservation_count, int):
        raise ValueError("reservation_count must be a whole number, got %r" % (reservation_count,))
    if reservation_count < 0:
        raise ValueError("reservation_count must not be negative, got %r" % (reservation_count,))
    term = BASE_VALIDITY_MONTHS - (
        float(reservation_count) * VALIDITY_PENALTY_PER_RESERVATION_MONTHS
    )
    if term < MINIMUM_VALIDITY_MONTHS:
        return 0.0
    return term


def assess_category_two_validation(
    supplier_id,
    technology_family,
    declared_scope,
    examined_scope,
    conditions,
    planned_elements,
    months_since_last_line_change,
):
    """Decide whether a category two validation may proceed and what it covers."""
    _text(supplier_id, "supplier_id")
    family = _text(technology_family, "technology_family")
    if not isinstance(conditions, (list, tuple)):
        raise ValueError("conditions must be a list or tuple, got %r" % (type(conditions).__name__,))

    envelope = scope_envelope(declared_scope, examined_scope)
    missing_elements = element_coverage(planned_elements)
    stable = line_is_stable(months_since_last_line_change)

    declared_conditions = {}
    for raw in conditions:
        record = normalize_condition(raw)
        if record["condition"] in declared_conditions:
            raise ValueError("duplicate entry condition %r" % (record["condition"],))
        declared_conditions[record["condition"]] = record
    condition_records = []
    for name in sorted(ENTRY_CONDITION_WEIGHTS):
        condition_records.append(
            assess_condition(declared_conditions.get(name, {"condition": name}))
        )
    index = readiness_index(condition_records)

    reservations = sum(1 for r in condition_records if r["state"] == "met-with-reservation")
    term = validity_months(reservations)

    findings = []
    if not technology_family_in_scope(family):
        findings.append(
            {
                "item": family,
                "finding": "technology-family-outside-route",
                "detail": "category two validation does not cover this family",
            }
        )
    if not stable:
        findings.append(
            {
                "item": "production-line",
                "finding": "line-changed-inside-stability-window",
                "detail": "%.1f of %.1f months"
                % (
                    _real(months_since_last_line_change, "months_since_last_line_change"),
                    LINE_STABILITY_WINDOW_MONTHS,
                ),
            }
        )
    for name in missing_elements:
        findings.append(
            {"item": name, "finding": "validation-element-not-planned", "detail": name}
        )
    for item in envelope["declared_not_examined"]:
        findings.append(
            {"item": item, "finding": "declared-range-outside-envelope", "detail": item}
        )
    for item in envelope["examined_not_declared"]:
        findings.append(
            {"item": item, "finding": "examined-range-not-declared", "detail": item}
        )
    for record in condition_records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["condition"], "finding": finding, "detail": record["state"]}
            )

    incomplete = bool(missing_elements) or any(r["mandatory_unmet"] for r in condition_records)
    blocked = (
        not stable
        or not technology_family_in_scope(family)
        or index < ADMISSIBILITY_INDEX - VALIDATION_TOLERANCE
        or term <= 0.0
    )
    if incomplete:
        verdict = "category-two-validation-preconditions-incomplete"
    elif blocked:
        verdict = "category-two-validation-not-admissible"
    elif findings:
        verdict = "category-two-validation-admissible-with-reservations"
    else:
        verdict = "category-two-validation-admissible"
    return {
        "supplier_id": supplier_id,
        "technology_family": family,
        "condition_records": condition_records,
        "readiness_index": index,
        "reservation_count": reservations,
        "line_stable": stable,
        "missing_elements": missing_elements,
        "envelope": envelope,
        "validity_months": term,
        "findings": findings,
        "verdict": verdict,
        "may_proceed": verdict
        in (
            "category-two-validation-admissible",
            "category-two-validation-admissible-with-reservations",
        ),
    }
