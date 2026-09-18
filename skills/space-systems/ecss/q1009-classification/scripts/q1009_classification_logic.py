"""Nonconformance severity categorization and cumulative assessment per item.

Anchor: ECSS-Q-ST-10-09 clause 5.2.2.2 (sorting a nonconformance into the
minor or the major category against the clause 3.2 criteria, and grouping the
several minor nonconformances raised on one item so their combined effect is
assessed rather than each one dismissed on its own). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each raised nonconformance: an identifier, the item it sits on,
   an explicit true/false answer to every severity criterion, and the share of
   a shared budget or margin the departure consumes.
2. Categorize it. Any single criterion answered true makes the departure
   major; the criteria are a disjunction, not a score, so one true answer is
   not traded against several false ones. Nothing true makes it minor.
3. Group the minor nonconformances by the item they sit on. The group is the
   unit of the cumulative assessment, because a budget is consumed by the item
   and not by any one departure against it.
4. Assess the group: sum the consumed shares and compare against the margin
   the item was allocated, and compare the group size against the count the
   item is permitted to carry. Either limit reached escalates the whole group
   to major and names which limit did it.
5. Report the per-departure category, the per-item cumulative verdict and the
   escalation reasons, so the item can be re-presented to the board correctly.
"""

import math

__all__ = [
    "CUMULATIVE_TOLERANCE",
    "DEFAULT_CUMULATIVE_LIMIT",
    "DEFAULT_MINOR_COUNT_LIMIT",
    "MAJOR_CRITERIA",
    "normalize_criterion",
    "validate_consumption",
    "validate_nonconformance",
    "triggered_criteria",
    "categorize_nonconformance",
    "group_by_item",
    "cumulative_consumption",
    "cumulative_assessment",
    "assess_categorization",
]

# A cumulative share is a sum of floats and lands a few ULPs either side of an
# exactly-consumed margin. Absorb that here rather than padding the margin.
CUMULATIVE_TOLERANCE = 1e-9

# A group that has consumed its whole allocated margin has no margin left for
# the next departure, so reaching the limit escalates, not exceeding it.
DEFAULT_CUMULATIVE_LIMIT = 1.0

# Beyond this many open minor departures an item is no longer a compliant item
# carrying an exception; the accumulation itself is the finding.
DEFAULT_MINOR_COUNT_LIMIT = 5

# The clause 3.2 severity criteria, in reporting order. Any one answered true
# makes the departure major.
MAJOR_CRITERIA = (
    "safety",
    "reliability-or-lifetime",
    "interchangeability",
    "performance-outside-specification",
    "interface",
    "budget-allocation-exceeded",
    "qualification-validity",
    "higher-level-or-contractual-requirement",
    "operational-use",
)

_CRITERION_SET = frozenset(MAJOR_CRITERIA)


def normalize_criterion(value):
    """Return a severity criterion name in canonical hyphen form."""
    if not isinstance(value, str):
        raise ValueError("criterion must be a string, got %r" % (value,))
    text = " ".join(value.strip().lower().split())
    if not text:
        raise ValueError("criterion must not be empty or whitespace only")
    name = text.replace(" ", "-").replace("_", "-")
    if name not in _CRITERION_SET:
        raise ValueError("unknown severity criterion '%s'" % name)
    return name


def _normalize_key(value, label):
    """Return a free identifier (nonconformance id, item id) in canonical form."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = " ".join(value.strip().lower().split())
    if not text:
        raise ValueError("%s must not be empty or whitespace only" % label)
    return text.replace(" ", "-").replace("_", "-")


def validate_consumption(value):
    """Return the validated share of the item's margin a departure consumes."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("consumption share must be a real number, got %r" % (value,))
    share = float(value)
    if not math.isfinite(share):
        raise ValueError("consumption share must be finite")
    if share < 0.0 or share > 1.0:
        raise ValueError("consumption share must lie in [0, 1], got %r" % (value,))
    return share


def validate_nonconformance(nc):
    """Return one validated nonconformance record."""
    if not isinstance(nc, dict):
        raise ValueError("nonconformance must be a mapping, got %r" % (nc,))
    for key in ("id", "item", "criteria"):
        if key not in nc:
            raise ValueError("nonconformance missing required key '%s'" % key)
    criteria = nc["criteria"]
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping of criterion name to true/false")
    answers = {}
    for raw_name, raw_value in criteria.items():
        name = normalize_criterion(raw_name)
        if not isinstance(raw_value, bool):
            raise ValueError(
                "criterion '%s' must be answered with a boolean, got %r" % (name, raw_value)
            )
        if name in answers:
            raise ValueError("criterion '%s' answered more than once" % name)
        answers[name] = raw_value
    unanswered = [c for c in MAJOR_CRITERIA if c not in answers]
    if unanswered:
        raise ValueError(
            "severity criteria left unanswered: %s" % ", ".join(unanswered)
        )
    return {
        "id": _normalize_key(nc["id"], "id"),
        "item": _normalize_key(nc["item"], "item"),
        "criteria": answers,
        "consumption": validate_consumption(nc.get("consumption", 0.0)),
    }


def triggered_criteria(nc):
    """Return the severity criteria answered true, in reporting order."""
    record = validate_nonconformance(nc)
    return tuple(c for c in MAJOR_CRITERIA if record["criteria"][c])


def categorize_nonconformance(nc):
    """Return the severity category of one departure and what drove it."""
    record = validate_nonconformance(nc)
    triggered = tuple(c for c in MAJOR_CRITERIA if record["criteria"][c])
    category = "major" if triggered else "minor"
    return {
        "id": record["id"],
        "item": record["item"],
        "category": category,
        "triggered": triggered,
        "consumption": record["consumption"],
    }


def group_by_item(nonconformances):
    """Return the categorized departures grouped by the item they sit on."""
    if not isinstance(nonconformances, (list, tuple)) or not nonconformances:
        raise ValueError("nonconformances must be a non-empty sequence")
    groups = {}
    order = []
    seen_ids = set()
    for nc in nonconformances:
        record = categorize_nonconformance(nc)
        if record["id"] in seen_ids:
            raise ValueError("nonconformance id '%s' raised more than once" % record["id"])
        seen_ids.add(record["id"])
        if record["item"] not in groups:
            groups[record["item"]] = []
            order.append(record["item"])
        groups[record["item"]].append(record)
    return [(item, groups[item]) for item in order]


def cumulative_consumption(records):
    """Return the share of the item's margin the minor departures consume together."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of categorized departures")
    total = 0.0
    for record in records:
        if not isinstance(record, dict) or "category" not in record:
            raise ValueError("each record must be a categorized departure mapping")
        if record["category"] == "minor":
            total += validate_consumption(record["consumption"])
    return total


def cumulative_assessment(records, limit=DEFAULT_CUMULATIVE_LIMIT,
                          count_limit=DEFAULT_MINOR_COUNT_LIMIT):
    """Assess one item's group of departures and return its cumulative verdict."""
    if not isinstance(limit, (int, float)) or isinstance(limit, bool):
        raise ValueError("limit must be a real number, got %r" % (limit,))
    cap = float(limit)
    if not math.isfinite(cap) or cap <= 0.0:
        raise ValueError("limit must be positive and finite, got %r" % (limit,))
    if not isinstance(count_limit, int) or isinstance(count_limit, bool):
        raise ValueError("count_limit must be an integer, got %r" % (count_limit,))
    if count_limit < 1:
        raise ValueError("count_limit must be at least 1, got %d" % count_limit)
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of departures")
    minors = [r for r in records if r["category"] == "minor"]
    majors = [r for r in records if r["category"] == "major"]
    total = cumulative_consumption(records)
    reasons = []
    budget_reached = total > cap or math.isclose(
        total, cap, rel_tol=0.0, abs_tol=CUMULATIVE_TOLERANCE
    )
    if budget_reached:
        reasons.append("cumulative-margin-consumed")
    if len(minors) > count_limit:
        reasons.append("minor-count-limit-exceeded")
    escalated = bool(reasons) and not majors
    effective = "major" if (majors or reasons) else "minor"
    return {
        "minor_count": len(minors),
        "major_count": len(majors),
        "cumulative_consumption": total,
        "limit": cap,
        "count_limit": count_limit,
        "escalation_reasons": tuple(reasons),
        "escalated": escalated,
        "effective_category": effective,
    }


def assess_categorization(spec):
    """Run the full clause 5.2.2.2 categorization and cumulative assessment.

    spec keys: nonconformances (sequence), optional cumulative_limit,
    optional minor_count_limit.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "nonconformances" not in spec:
        raise ValueError("spec missing required key 'nonconformances'")
    limit = spec.get("cumulative_limit", DEFAULT_CUMULATIVE_LIMIT)
    count_limit = spec.get("minor_count_limit", DEFAULT_MINOR_COUNT_LIMIT)
    grouped = group_by_item(spec["nonconformances"])
    departures = []
    items = []
    findings = []
    for item, records in grouped:
        departures.extend(records)
        verdict = cumulative_assessment(records, limit, count_limit)
        verdict["item"] = item
        items.append(verdict)
        for record in records:
            if record["category"] == "major":
                findings.append(
                    "%s on %s is major: %s"
                    % (record["id"], item, ", ".join(record["triggered"]))
                )
        if verdict["escalated"]:
            findings.append(
                "item %s escalates to major on the accumulation of %d minor departures (%s)"
                % (item, verdict["minor_count"], ", ".join(verdict["escalation_reasons"]))
            )
    return {
        "departures": departures,
        "items": items,
        "major_departures": sum(1 for d in departures if d["category"] == "major"),
        "minor_departures": sum(1 for d in departures if d["category"] == "minor"),
        "escalated_items": tuple(v["item"] for v in items if v["escalated"]),
        "findings": findings,
        "all_minor": all(v["effective_category"] == "minor" for v in items),
    }
