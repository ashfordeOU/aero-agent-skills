"""Manufacturer data deliveries accompanying Class 2 EEE shipments.

Anchor: ECSS-Q-ST-60C clause 5.3.11 (certificates of conformity and the
supporting manufacturer records delivered with Class 2 shipments). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive the record set the shipment owes from the part category and from
   what happened to the lot: screening, radiation lot acceptance, a delta
   qualification, an approved deviation, a rework.
2. Grade every delivered record against the box it arrived with: an authorised
   signature, a lot code that agrees with the shipment, an issue day at or
   before dispatch, and a quantity that covers what was actually delivered.
3. Credit each graded record by its status. A summary that stands in for the
   underlying data is worth less than the data, and a record that names
   another lot is worth nothing at all.
4. Weight the credits into a completeness fraction, so a missing screening
   record and a missing packing note do not move the number equally.
5. Name the mandatory gaps separately. A shipment missing its certificate of
   conformity is held whatever the completeness fraction says.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "RECORD_STATUSES",
    "STATUS_CREDIT",
    "RECORD_WEIGHTS",
    "MANDATORY_RECORDS",
    "CATEGORY_RECORDS",
    "CONDITIONAL_RECORDS",
    "ACCEPT_THRESHOLD",
    "ACTIONS_THRESHOLD",
    "owed_records",
    "record_weight",
    "grade_record",
    "grade_package",
    "completeness_fraction",
    "mandatory_gaps",
    "assess_data_package",
]

# Completeness is a quotient of weighted credits; a package meant to land
# exactly on a threshold can sit a few ULP either side of it. Absorb the
# representation error here, never by moving the threshold.
BOUND_TOLERANCE = 1e-9

RECORD_STATUSES = (
    "delivered",
    "summary",
    "late",
    "unsigned",
    "short-quantity",
    "lot-mismatch",
    "absent",
)

# What each status is worth against the record it was owed for.
STATUS_CREDIT = {
    "delivered": 1.0,
    "summary": 0.6,
    "late": 0.5,
    "unsigned": 0.3,
    "short-quantity": 0.0,
    "lot-mismatch": 0.0,
    "absent": 0.0,
}

# Weights say which gap matters. A missing screening record and a missing
# packing note are both gaps and are not the same gap.
RECORD_WEIGHTS = {
    "certificate-of-conformity": 5.0,
    "lot-traceability-record": 4.0,
    "screening-test-data": 4.0,
    "lot-acceptance-test-data": 3.0,
    "radiation-lot-acceptance-report": 3.0,
    "delta-qualification-report": 3.0,
    "approved-deviation-record": 3.0,
    "rework-and-repair-record": 2.0,
    "date-code-and-quantity-list": 2.0,
    "packing-and-handling-note": 1.0,
}

# A gap in one of these holds the shipment whatever the completeness says.
MANDATORY_RECORDS = ("certificate-of-conformity", "lot-traceability-record")

# The records a part category always owes.
CATEGORY_RECORDS = {
    "microcircuit": (
        "certificate-of-conformity",
        "lot-traceability-record",
        "lot-acceptance-test-data",
        "date-code-and-quantity-list",
        "packing-and-handling-note",
    ),
    "discrete-semiconductor": (
        "certificate-of-conformity",
        "lot-traceability-record",
        "lot-acceptance-test-data",
        "date-code-and-quantity-list",
    ),
    "hybrid": (
        "certificate-of-conformity",
        "lot-traceability-record",
        "lot-acceptance-test-data",
        "date-code-and-quantity-list",
        "packing-and-handling-note",
    ),
    "passive": (
        "certificate-of-conformity",
        "lot-traceability-record",
        "date-code-and-quantity-list",
    ),
}

# Records owed because of what happened to this particular lot.
CONDITIONAL_RECORDS = {
    "screened_lot": "screening-test-data",
    "radiation_lot_acceptance": "radiation-lot-acceptance-report",
    "delta_qualification": "delta-qualification-report",
    "approved_deviation": "approved-deviation-record",
    "rework_performed": "rework-and-repair-record",
}

ACCEPT_THRESHOLD = 0.95
ACTIONS_THRESHOLD = 0.80


def _positive_int(value, label):
    """Return value as a positive integer, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _any_int(value, label):
    """Return value as an integer day number, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer day number, got %r" % (label, value))
    return value


def _positive_real(value, label):
    """Return value as a finite positive float, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _clean_token(value, label):
    """Return a stripped lower-cased non-empty token, refusing anything else."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def _at_least(value, bound):
    """Return True when value sits at or above bound, tolerant of float noise."""
    return value > bound or math.isclose(
        value, bound, rel_tol=BOUND_TOLERANCE, abs_tol=BOUND_TOLERANCE
    )


def owed_records(part_category, options=None):
    """Return the record set this shipment owes.

    options carries what happened to the lot: screened_lot,
    radiation_lot_acceptance, delta_qualification, approved_deviation and
    rework_performed. An option the register does not carry is refused rather
    than ignored, because a silently dropped option is a silently dropped
    record.
    """
    category = _clean_token(part_category, "part_category")
    if category not in CATEGORY_RECORDS:
        raise ValueError(
            "part category '%s' is not in the data delivery register" % category
        )
    if options is None:
        options = {}
    if not isinstance(options, dict):
        raise ValueError("options must be a mapping of lot history flags")
    owed = list(CATEGORY_RECORDS[category])
    for name, value in options.items():
        key = str(name).strip().lower()
        if key not in CONDITIONAL_RECORDS:
            raise ValueError(
                "lot history flag '%s' is not a recognised data delivery trigger" % key
            )
        if bool(value):
            record = CONDITIONAL_RECORDS[key]
            if record not in owed:
                owed.append(record)
    return tuple(owed)


def record_weight(record_name, table=None):
    """Return the weight a record carries in the completeness fraction."""
    if table is None:
        table = RECORD_WEIGHTS
    if not isinstance(table, dict) or not table:
        raise ValueError("table must be a non-empty mapping of record to weight")
    name = _clean_token(record_name, "record_name")
    if name not in table:
        raise ValueError(
            "record '%s' carries no weight in the register; an unweighted record "
            "cannot be counted for or against the package" % name
        )
    return _positive_real(table[name], "weight for '%s'" % name)


def grade_record(record, lot_code, dispatch_day, delivered_quantity):
    """Grade one delivered record against the shipment it arrived with.

    record keys: lot_code, issue_day, quantity_covered, signed (bool) and an
    optional summary_only flag. The grades are ordered by how far the record is
    from being usable: a record naming another lot is not a signature problem,
    and a record covering fewer parts than arrived is not a late one.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    shipment_lot = _clean_token(lot_code, "lot_code")
    dispatch_day = _any_int(dispatch_day, "dispatch_day")
    delivered_quantity = _positive_int(delivered_quantity, "delivered_quantity")
    for key in ("lot_code", "issue_day", "quantity_covered", "signed"):
        if key not in record:
            raise ValueError("record missing key '%s'" % key)
    if _clean_token(record["lot_code"], "record lot_code") != shipment_lot:
        return "lot-mismatch"
    if not bool(record["signed"]):
        return "unsigned"
    covered = _positive_int(record["quantity_covered"], "quantity_covered")
    if covered < delivered_quantity:
        return "short-quantity"
    if _any_int(record["issue_day"], "issue_day") > dispatch_day:
        return "late"
    if bool(record.get("summary_only", False)):
        return "summary"
    return "delivered"


def grade_package(owed, delivered, lot_code, dispatch_day, delivered_quantity,
                  weights=None):
    """Grade every owed record, marking the ones that never arrived as absent."""
    if not isinstance(owed, (list, tuple)) or not owed:
        raise ValueError("owed must be a non-empty sequence of record names")
    if delivered is None:
        delivered = {}
    if not isinstance(delivered, dict):
        raise ValueError("delivered must be a mapping of record name to a record")
    owed_names = [_clean_token(name, "owed record name") for name in owed]
    supplied = {
        _clean_token(name, "delivered record name"): record
        for name, record in delivered.items()
    }
    for name in supplied:
        if name not in owed_names:
            raise ValueError(
                "record '%s' was delivered but this shipment does not owe it; check "
                "it names the right lot before it is filed" % name
            )
    graded = {}
    for name in owed_names:
        if name in supplied:
            status = grade_record(
                supplied[name], lot_code, dispatch_day, delivered_quantity
            )
        else:
            status = "absent"
        graded[name] = {
            "status": status,
            "credit": STATUS_CREDIT[status],
            "weight": record_weight(name, weights),
        }
    return graded


def completeness_fraction(graded):
    """Return the weighted share of the owed record set that actually arrived."""
    if not isinstance(graded, dict) or not graded:
        raise ValueError("graded must be a non-empty mapping of record to a grade")
    owed_weight = 0.0
    credited_weight = 0.0
    for name, entry in graded.items():
        if not isinstance(entry, dict) or "weight" not in entry or "credit" not in entry:
            raise ValueError("grade for '%s' must carry a weight and a credit" % name)
        weight = _positive_real(entry["weight"], "weight for '%s'" % name)
        credit = float(entry["credit"])
        if not math.isfinite(credit) or credit < 0.0 or credit > 1.0:
            raise ValueError("credit for '%s' must lie in [0, 1]" % name)
        owed_weight += weight
        credited_weight += weight * credit
    return credited_weight / owed_weight


def mandatory_gaps(graded, mandatory=MANDATORY_RECORDS):
    """Return the mandatory records that did not arrive in full."""
    if not isinstance(graded, dict) or not graded:
        raise ValueError("graded must be a non-empty mapping of record to a grade")
    gaps = []
    for name in mandatory:
        key = _clean_token(name, "mandatory record name")
        if key not in graded:
            continue
        if graded[key]["status"] != "delivered":
            gaps.append(key)
    return tuple(gaps)


def assess_data_package(spec):
    """Run the clause 5.3.11 data delivery assessment for one Class 2 shipment.

    Required spec keys: part_category, lot_code, dispatch_day,
    delivered_quantity, delivered_records. Optional: lot_history,
    accept_threshold, actions_threshold, weights, mandatory_records.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "part_category",
        "lot_code",
        "dispatch_day",
        "delivered_quantity",
        "delivered_records",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    owed = owed_records(spec["part_category"], spec.get("lot_history"))
    graded = grade_package(
        owed,
        spec["delivered_records"],
        spec["lot_code"],
        spec["dispatch_day"],
        spec["delivered_quantity"],
        spec.get("weights"),
    )
    fraction = completeness_fraction(graded)
    gaps = mandatory_gaps(graded, spec.get("mandatory_records", MANDATORY_RECORDS))
    accept = _positive_real(
        spec.get("accept_threshold", ACCEPT_THRESHOLD), "accept_threshold"
    )
    actions = _positive_real(
        spec.get("actions_threshold", ACTIONS_THRESHOLD), "actions_threshold"
    )
    if actions > accept:
        raise ValueError(
            "the actions threshold %r sits above the accept threshold %r"
            % (actions, accept)
        )

    shortfalls = tuple(
        sorted(name for name, entry in graded.items() if entry["status"] != "delivered")
    )
    result = {
        "owed_records": owed,
        "graded_records": graded,
        "completeness_fraction": fraction,
        "mandatory_gaps": gaps,
        "shortfalls": shortfalls,
        "accept_threshold": accept,
        "actions_threshold": actions,
    }

    if gaps:
        result["disposition"] = "hold-shipment"
        result["reasons"] = [
            "mandatory record '%s' did not arrive in full" % name for name in gaps
        ]
        return result
    if _at_least(fraction, accept):
        result["disposition"] = "accept-into-stores"
        result["reasons"] = [
            "data package is %.3f complete by weight against a threshold of %.3f"
            % (fraction, accept)
        ]
        return result
    if _at_least(fraction, actions):
        result["disposition"] = "accept-with-actions"
        result["reasons"] = [
            "data package is %.3f complete by weight; %d record(s) owe follow-up"
            % (fraction, len(shortfalls))
        ]
        return result
    result["disposition"] = "hold-shipment"
    result["reasons"] = [
        "data package is %.3f complete by weight, under the %.3f floor"
        % (fraction, actions)
    ]
    return result
