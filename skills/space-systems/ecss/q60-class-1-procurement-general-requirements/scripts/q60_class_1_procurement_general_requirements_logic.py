"""Procurement conformity assessment for purchased class 1 EEE parts.

Anchor: ECSS-Q-ST-60C clause 4.3.1 — the general duty to ensure that
electrical, electronic and electromechanical parts actually purchased for
class 1 use meet the technical baseline agreed for them. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the agreed technical baseline: which part, from which
   manufacturer, at which assurance level, over which temperature range, to
   which total-ionising-dose capability, and which baseline requirements have
   to be flowed into the purchase.
2. Validate the purchase order placed against that baseline, and validate the
   lot actually delivered against it.
3. Test the order for an undeclared substitution: a part number or a
   manufacturer that is neither the baseline one nor a declared alternate.
4. Rank the ordered assurance level on the assurance ladder and refuse an
   order placed below the baseline rank.
5. Name every baseline requirement the purchase order failed to flow down; an
   unflowed requirement is a requirement the supplier never saw.
6. Test the delivered lot: quantity against the order, temperature range
   against the baseline range it has to contain, dose capability against the
   baseline figure, and the traceability records the lot has to carry.
7. Return the per-check records and a conformity verdict carrying every
   finding rather than only the first.

Boundary equalities are representation questions and are absorbed by a named
tolerance; the agreed baseline figures themselves are never relaxed.
"""

import math

__all__ = [
    "ASSURANCE_LADDER",
    "MANDATORY_TRACEABILITY",
    "BASELINE_TOLERANCE",
    "normalize_token",
    "assurance_rank",
    "meets_assurance",
    "validate_baseline",
    "validate_purchase_order",
    "validate_delivered_lot",
    "is_declared_substitution",
    "missing_flowdown",
    "temperature_range_covered",
    "missing_traceability",
    "assess_purchase",
]

# Assurance levels ordered from the weakest to the strongest. A purchase may
# be placed at or above the baseline rank, never below it.
ASSURANCE_LADDER = (
    "commercial",
    "industrial",
    "class-3",
    "class-2",
    "class-1",
)

# Records a delivered lot has to carry before the purchase can be shown to
# have met the baseline.
MANDATORY_TRACEABILITY = (
    "manufacturer-lot-identity",
    "screening-records",
    "certificate-of-conformity",
)

# Temperature limits and dose figures pass through unit conversions, so a
# value that should sit exactly on the baseline can land a few units in the
# last place away from it. Absorb that here, never by moving the baseline.
BASELINE_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_count(value, label, minimum=0):
    """Return a validated non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def _require_real(value, label):
    """Return a validated finite real quantity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _require_non_negative_real(value, label):
    """Return a validated finite real quantity that is not negative."""
    number = _require_real(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _require_range(value, label):
    """Return a validated ordered temperature range as a pair of reals."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("%s must be a pair of temperatures" % label)
    low = _require_real(value[0], "%s lower limit" % label)
    high = _require_real(value[1], "%s upper limit" % label)
    if low >= high:
        raise ValueError("%s is inverted or degenerate" % label)
    return (low, high)


def _require_token_list(value, label):
    """Return a validated list of normalized tokens with no repeats."""
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence" % label)
    tokens = []
    for index, item in enumerate(value):
        token = normalize_token(item, "%s[%d]" % (label, index))
        if token in tokens:
            raise ValueError("%s lists '%s' twice" % (label, token))
        tokens.append(token)
    return tokens


def normalize_token(value, label="token"):
    """Return a token in the normalized lower-case hyphenated form."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def assurance_rank(level, label="assurance level"):
    """Return the ladder position of an assurance level."""
    token = normalize_token(level, label)
    if token not in ASSURANCE_LADDER:
        raise ValueError(
            "%s must be one of %s, got '%s'" % (label, list(ASSURANCE_LADDER), token)
        )
    return ASSURANCE_LADDER.index(token)


def meets_assurance(ordered_level, baseline_level):
    """Return whether an ordered assurance level reaches the baseline rank."""
    return assurance_rank(ordered_level, "ordered assurance level") >= assurance_rank(
        baseline_level, "baseline assurance level"
    )


def validate_baseline(baseline):
    """Return the validated technical baseline agreed for the part."""
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be a mapping")
    for key in ("part_number", "manufacturer", "assurance_level", "temperature_range_c",
                "required_tid_krad", "required_flowdown"):
        if key not in baseline:
            raise ValueError("baseline missing required key '%s'" % key)
    return {
        "part_number": _require_text(baseline["part_number"], "baseline part_number"),
        "manufacturer": normalize_token(baseline["manufacturer"], "baseline manufacturer"),
        "assurance_level": normalize_token(baseline["assurance_level"],
                                           "baseline assurance_level"),
        "temperature_range_c": _require_range(baseline["temperature_range_c"],
                                              "baseline temperature_range_c"),
        "required_tid_krad": _require_non_negative_real(baseline["required_tid_krad"],
                                                        "required_tid_krad"),
        "required_flowdown": _require_token_list(baseline["required_flowdown"],
                                                 "required_flowdown"),
        "approved_alternates": _require_token_list(
            baseline.get("approved_alternates", []), "approved_alternates"),
    }


def validate_purchase_order(order):
    """Return the validated purchase order placed against the baseline."""
    if not isinstance(order, dict):
        raise ValueError("purchase_order must be a mapping")
    for key in ("part_number", "manufacturer", "assurance_level", "quantity",
                "flowed_clauses"):
        if key not in order:
            raise ValueError("purchase_order missing required key '%s'" % key)
    return {
        "part_number": _require_text(order["part_number"], "order part_number"),
        "manufacturer": normalize_token(order["manufacturer"], "order manufacturer"),
        "assurance_level": normalize_token(order["assurance_level"],
                                           "order assurance_level"),
        "quantity": _require_count(order["quantity"], "order quantity", minimum=1),
        "flowed_clauses": _require_token_list(order["flowed_clauses"], "flowed_clauses"),
    }


def validate_delivered_lot(lot):
    """Return the validated lot actually delivered against the order."""
    if not isinstance(lot, dict):
        raise ValueError("delivered_lot must be a mapping")
    for key in ("lot_code", "quantity", "temperature_range_c", "tid_krad", "records"):
        if key not in lot:
            raise ValueError("delivered_lot missing required key '%s'" % key)
    return {
        "lot_code": _require_text(lot["lot_code"], "lot_code"),
        "quantity": _require_count(lot["quantity"], "delivered quantity", minimum=1),
        "temperature_range_c": _require_range(lot["temperature_range_c"],
                                              "delivered temperature_range_c"),
        "tid_krad": _require_non_negative_real(lot["tid_krad"], "tid_krad"),
        "records": _require_token_list(lot["records"], "delivered records"),
    }


def is_declared_substitution(order, baseline):
    """Return whether an ordered part is the baseline part or a declared alternate."""
    agreed = validate_baseline(baseline)
    placed = validate_purchase_order(order)
    if placed["part_number"] == agreed["part_number"]:
        return placed["manufacturer"] == agreed["manufacturer"]
    return normalize_token(placed["part_number"], "order part_number") in agreed[
        "approved_alternates"
    ]


def missing_flowdown(order, baseline):
    """Return the baseline requirements the purchase order never flowed down."""
    agreed = validate_baseline(baseline)
    placed = validate_purchase_order(order)
    return [ref for ref in agreed["required_flowdown"] if ref not in placed["flowed_clauses"]]


def temperature_range_covered(delivered_range, baseline_range):
    """Return whether a delivered range contains the baseline range end to end."""
    delivered = _require_range(delivered_range, "delivered temperature range")
    baseline = _require_range(baseline_range, "baseline temperature range")
    low_ok = delivered[0] < baseline[0] or math.isclose(
        delivered[0], baseline[0], rel_tol=0.0, abs_tol=BASELINE_TOLERANCE
    )
    high_ok = delivered[1] > baseline[1] or math.isclose(
        delivered[1], baseline[1], rel_tol=0.0, abs_tol=BASELINE_TOLERANCE
    )
    return low_ok and high_ok


def missing_traceability(lot):
    """Return the mandatory traceability records a delivered lot does not carry."""
    delivered = validate_delivered_lot(lot)
    return [name for name in MANDATORY_TRACEABILITY if name not in delivered["records"]]


def assess_purchase(spec):
    """Run the full clause 4.3.1 procurement conformity assessment.

    spec keys: baseline, purchase_order, delivered_lot.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("baseline", "purchase_order", "delivered_lot"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    agreed = validate_baseline(spec["baseline"])
    placed = validate_purchase_order(spec["purchase_order"])
    delivered = validate_delivered_lot(spec["delivered_lot"])

    findings = []

    substitution_declared = is_declared_substitution(spec["purchase_order"],
                                                     spec["baseline"])
    if not substitution_declared:
        findings.append(
            "order for '%s' from '%s' is neither the baseline part nor a declared alternate"
            % (placed["part_number"], placed["manufacturer"])
        )

    assurance_ok = meets_assurance(placed["assurance_level"], agreed["assurance_level"])
    if not assurance_ok:
        findings.append(
            "order placed at '%s' against a baseline of '%s'"
            % (placed["assurance_level"], agreed["assurance_level"])
        )

    unflowed = [ref for ref in agreed["required_flowdown"]
                if ref not in placed["flowed_clauses"]]
    for ref in unflowed:
        findings.append("baseline requirement '%s' was never flowed into the order" % ref)

    quantity_ok = delivered["quantity"] >= placed["quantity"]
    if not quantity_ok:
        findings.append(
            "lot '%s' delivered %d against %d ordered"
            % (delivered["lot_code"], delivered["quantity"], placed["quantity"])
        )

    range_ok = temperature_range_covered(delivered["temperature_range_c"],
                                         agreed["temperature_range_c"])
    if not range_ok:
        findings.append(
            "lot '%s' is rated %g to %g degC, inside the baseline %g to %g degC"
            % (delivered["lot_code"], delivered["temperature_range_c"][0],
               delivered["temperature_range_c"][1], agreed["temperature_range_c"][0],
               agreed["temperature_range_c"][1])
        )

    dose_ok = delivered["tid_krad"] > agreed["required_tid_krad"] or math.isclose(
        delivered["tid_krad"], agreed["required_tid_krad"], rel_tol=0.0,
        abs_tol=BASELINE_TOLERANCE
    )
    if not dose_ok:
        findings.append(
            "lot '%s' carries %g krad against a baseline %g krad"
            % (delivered["lot_code"], delivered["tid_krad"], agreed["required_tid_krad"])
        )

    absent_records = [name for name in MANDATORY_TRACEABILITY
                      if name not in delivered["records"]]
    for name in absent_records:
        findings.append("lot '%s' carries no %s" % (delivered["lot_code"], name))

    return {
        "baseline": agreed,
        "purchase_order": placed,
        "delivered_lot": delivered,
        "substitution_declared": substitution_declared,
        "assurance_level_met": assurance_ok,
        "unflowed_requirements": unflowed,
        "quantity_met": quantity_ok,
        "temperature_range_met": range_ok,
        "dose_capability_met": dose_ok,
        "missing_records": absent_records,
        "conformant": not findings,
        "findings": findings,
    }
