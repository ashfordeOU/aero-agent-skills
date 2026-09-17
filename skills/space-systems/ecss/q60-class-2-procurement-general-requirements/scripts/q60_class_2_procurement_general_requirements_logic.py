"""Class 2 EEE parts procurement conformance against the agreed baseline.

Anchor: ECSS-Q-ST-60C clause 5.3.1 — the overall duty to ensure that the
Class 2 parts actually purchased meet the technical baseline agreed for the
project. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Index the agreed baseline by part type and reject a baseline that names
   the same part type twice: the duty is meaningless if two entries disagree
   about what the same type owes.
2. Match every ordered part type to a baseline entry, in both directions. An
   ordered type with no baseline entry was bought against nothing; a baseline
   entry nobody ordered is the gap that shows up at board build.
3. Compare the offered procurement grade with the grade the baseline demands,
   on an ordered ladder, so a higher grade satisfies a lower demand and a
   lower grade never does.
4. Confirm the part operating temperature range contains the mission range
   with the margin the baseline requires, at both ends independently.
5. Judge the supply route. The manufacturer and its franchised distributors
   carry their own traceability; a broker route is admitted only where
   traceability and counterfeit-avoidance evidence travel with the lot.
6. Admit a departure from the baseline only against a deviation carrying a
   reference, an approval authority and a validity that still covers the
   order date.
7. Report the per-type records, the compliant fraction and a verdict that
   carries every finding rather than the first.
"""

import datetime

__all__ = [
    "PROCUREMENT_GRADE_LADDER",
    "SELF_TRACEABLE_ROUTES",
    "EVIDENCE_BEARING_ROUTES",
    "REQUIRED_BROKER_EVIDENCE",
    "MARGIN_TOLERANCE",
    "normalize_token",
    "parse_iso_date",
    "grade_rank",
    "index_baseline",
    "grade_findings",
    "temperature_margins",
    "temperature_findings",
    "supply_route_findings",
    "deviation_findings",
    "assess_part_type",
    "assess_procurement_order",
]

# Procurement grades in increasing order of the evidence they carry. A part
# offered at a higher grade satisfies a demand for a lower one.
PROCUREMENT_GRADE_LADDER = (
    "commercial",
    "industrial",
    "automotive",
    "military",
    "space",
)

# Routes that carry the manufacturer's own traceability with the lot.
SELF_TRACEABLE_ROUTES = ("manufacturer", "franchised-distributor")

# Routes admitted only where the traceability evidence travels separately.
EVIDENCE_BEARING_ROUTES = ("broker", "open-market-distributor")

# The evidence an evidence-bearing route owes before a lot may be used.
REQUIRED_BROKER_EVIDENCE = (
    "traceability-chain",
    "counterfeit-avoidance-test-report",
)

# Temperature margins are differences of decimal values parsed from a file;
# a margin that lands on the requirement must not be failed on representation.
MARGIN_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_real(value, label):
    """Return a real number, raising on a boolean or a non-number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    return float(value)


def _require_mapping(value, label):
    """Return a mapping, raising on anything else."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def normalize_token(value, label):
    """Return a lower-case hyphenated token from a free-text field."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def parse_iso_date(value, label):
    """Return a date parsed from an ISO calendar string."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _require_text(value, label)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO calendar date, got '%s'" % (label, text))


def grade_rank(value, label="procurement grade"):
    """Return the ladder position of a procurement grade."""
    token = normalize_token(value, label)
    if token not in PROCUREMENT_GRADE_LADDER:
        raise ValueError(
            "%s '%s' is not on the procurement ladder %s"
            % (label, token, ", ".join(PROCUREMENT_GRADE_LADDER))
        )
    return PROCUREMENT_GRADE_LADDER.index(token)


def index_baseline(baseline):
    """Return the agreed baseline indexed by part type, rejecting a duplicate."""
    if not isinstance(baseline, (list, tuple)) or not baseline:
        raise ValueError("baseline must be a non-empty sequence of entries")
    index = {}
    for position, entry in enumerate(baseline):
        _require_mapping(entry, "baseline[%d]" % position)
        for key in (
            "part_type",
            "required_grade",
            "mission_low_c",
            "mission_high_c",
            "required_margin_c",
        ):
            if key not in entry:
                raise ValueError("baseline[%d] missing required key '%s'" % (position, key))
        part_type = normalize_token(entry["part_type"], "baseline[%d].part_type" % position)
        if part_type in index:
            raise ValueError("part type '%s' appears twice in the baseline" % part_type)
        low = _require_real(entry["mission_low_c"], "mission_low_c")
        high = _require_real(entry["mission_high_c"], "mission_high_c")
        if high <= low:
            raise ValueError(
                "part type '%s' has a mission range that does not rise: %g to %g"
                % (part_type, low, high)
            )
        margin = _require_real(entry["required_margin_c"], "required_margin_c")
        if margin < 0.0:
            raise ValueError("required_margin_c must not be negative for '%s'" % part_type)
        index[part_type] = {
            "part_type": part_type,
            "required_grade": normalize_token(entry["required_grade"], "required_grade"),
            "required_grade_rank": grade_rank(entry["required_grade"], "required_grade"),
            "mission_low_c": low,
            "mission_high_c": high,
            "required_margin_c": margin,
        }
    return index


def grade_findings(offered_grade, entry):
    """Return the findings raised by the grade actually bought."""
    offered = grade_rank(offered_grade, "offered grade")
    if offered < entry["required_grade_rank"]:
        return [
            "part type '%s' was bought at grade '%s', below the '%s' the baseline demands"
            % (
                entry["part_type"],
                normalize_token(offered_grade, "offered grade"),
                entry["required_grade"],
            )
        ]
    return []


def temperature_margins(part_low_c, part_high_c, entry):
    """Return the cold and hot margins the offered part holds over the mission."""
    low = _require_real(part_low_c, "part_low_c")
    high = _require_real(part_high_c, "part_high_c")
    if high <= low:
        raise ValueError("part operating range does not rise: %g to %g" % (low, high))
    return {
        "cold_margin_c": entry["mission_low_c"] - low,
        "hot_margin_c": high - entry["mission_high_c"],
    }


def temperature_findings(part_low_c, part_high_c, entry):
    """Return the margins and any shortfall at either end of the range."""
    margins = temperature_margins(part_low_c, part_high_c, entry)
    required = entry["required_margin_c"]
    findings = []
    if margins["cold_margin_c"] < required - MARGIN_TOLERANCE:
        findings.append(
            "part type '%s' holds %.3f C of cold margin, short of the %.3f required"
            % (entry["part_type"], margins["cold_margin_c"], required)
        )
    if margins["hot_margin_c"] < required - MARGIN_TOLERANCE:
        findings.append(
            "part type '%s' holds %.3f C of hot margin, short of the %.3f required"
            % (entry["part_type"], margins["hot_margin_c"], required)
        )
    margins["findings"] = findings
    return margins


def supply_route_findings(supply):
    """Return the findings raised by the route the parts were bought through."""
    _require_mapping(supply, "supply")
    if "route" not in supply:
        raise ValueError("supply missing required key 'route'")
    route = normalize_token(supply["route"], "supply route")
    known = SELF_TRACEABLE_ROUTES + EVIDENCE_BEARING_ROUTES
    if route not in known:
        raise ValueError("supply route '%s' is not a recognised route" % route)
    if route in SELF_TRACEABLE_ROUTES:
        return []
    evidence = supply.get("evidence", ())
    if not isinstance(evidence, (list, tuple, set, frozenset)):
        raise ValueError("supply evidence must be a collection of evidence tokens")
    held = set(normalize_token(item, "evidence entry") for item in evidence)
    findings = []
    for owed in REQUIRED_BROKER_EVIDENCE:
        if owed not in held:
            findings.append(
                "route '%s' carries no '%s', so the lot traceability stops at the seller"
                % (route, owed)
            )
    return findings


def deviation_findings(deviation, order_date):
    """Return the findings raised by a departure from the agreed baseline."""
    on = parse_iso_date(order_date, "order_date")
    if deviation is None:
        return ["a departure from the baseline is claimed with no deviation record"]
    _require_mapping(deviation, "deviation")
    findings = []
    reference = deviation.get("reference")
    if not isinstance(reference, str) or not reference.strip():
        findings.append("the deviation carries no reference")
    authority = deviation.get("approval_authority")
    if not isinstance(authority, str) or not authority.strip():
        findings.append("the deviation names no approval authority")
    valid_until = deviation.get("valid_until")
    if valid_until is not None:
        expiry = parse_iso_date(valid_until, "deviation valid_until")
        if expiry < on:
            findings.append(
                "the deviation expired on %s, before the order date %s"
                % (expiry.isoformat(), on.isoformat())
            )
    return findings


def assess_part_type(purchase, index, order_date):
    """Return one purchased-part-type record carrying its findings."""
    _require_mapping(purchase, "purchase")
    for key in ("part_type", "offered_grade", "part_low_c", "part_high_c", "supply"):
        if key not in purchase:
            raise ValueError("purchase missing required key '%s'" % key)
    part_type = normalize_token(purchase["part_type"], "purchase part_type")
    if part_type not in index:
        return {
            "part_type": part_type,
            "in_baseline": False,
            "margins": None,
            "findings": [
                "part type '%s' was ordered with no entry in the agreed baseline" % part_type
            ],
            "compliant": False,
        }
    entry = index[part_type]

    findings = []
    findings.extend(grade_findings(purchase["offered_grade"], entry))
    margins = temperature_findings(purchase["part_low_c"], purchase["part_high_c"], entry)
    findings.extend(margins["findings"])
    findings.extend(supply_route_findings(purchase["supply"]))
    if purchase.get("departs_from_baseline", False):
        findings.extend(deviation_findings(purchase.get("deviation"), order_date))

    return {
        "part_type": part_type,
        "in_baseline": True,
        "margins": {
            "cold_margin_c": margins["cold_margin_c"],
            "hot_margin_c": margins["hot_margin_c"],
        },
        "findings": findings,
        "compliant": not findings,
    }


def assess_procurement_order(order):
    """Run the full clause 5.3.1 procurement conformance assessment.

    order keys: order_reference, order_date, baseline, purchases.
    """
    _require_mapping(order, "order")
    for key in ("order_reference", "order_date", "baseline", "purchases"):
        if key not in order:
            raise ValueError("order missing required key '%s'" % key)
    reference = _require_text(order["order_reference"], "order_reference")
    order_date = parse_iso_date(order["order_date"], "order_date")
    index = index_baseline(order["baseline"])

    purchases = order["purchases"]
    if not isinstance(purchases, (list, tuple)) or not purchases:
        raise ValueError("purchases must be a non-empty sequence")

    records = []
    seen = []
    for purchase in purchases:
        record = assess_part_type(purchase, index, order_date)
        if record["part_type"] in seen:
            raise ValueError("part type '%s' is purchased twice on one order" % record["part_type"])
        seen.append(record["part_type"])
        records.append(record)

    findings = []
    unordered = [t for t in sorted(index) if t not in seen]
    for part_type in unordered:
        findings.append(
            "baseline part type '%s' appears on no line of the order" % part_type
        )
    for record in records:
        findings.extend(record["findings"])

    compliant = [r for r in records if r["compliant"]]
    return {
        "order_reference": reference,
        "order_date": order_date.isoformat(),
        "part_types": records,
        "unordered_baseline_types": unordered,
        "compliant_fraction": len(compliant) / float(len(records)),
        "baseline_met": not findings,
        "findings": findings,
    }
