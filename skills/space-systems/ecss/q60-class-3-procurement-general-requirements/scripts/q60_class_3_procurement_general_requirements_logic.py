"""General duty on Class 3 parts actually purchased to meet the baseline.

Anchor: ECSS-Q-ST-60C clause 6.3.1 (the overall obligation to ensure that
the Class 3 parts a project buys meet the technical baseline agreed for them).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The baseline and the order are reconciled in both directions. A part type
  bought against no baseline entry and a baseline entry nobody ever bought are
  different defects and both are reported.
* Quality level is a ladder, and the Class 3 ladder reaches down into
  commercial grades. What matters is not which rung the part sits on but
  whether that rung is at or above the rung the baseline demands.
* The rated temperature envelope has to contain the mission envelope. Where it
  does not, the part is being uprated, and uprating is admissible only against
  a justification record naming a recognised method and the evidence behind
  it. Buying a commercial part and hoping is the defect this catches.
* An open-market or broker route carries no traceability of its own, so it is
  admitted only against the authenticity evidence set. A manufacturer or
  franchised route carries its own.
* A lot older than the agreed date-code limit is refused on age alone.
"""

from __future__ import annotations

import math

# Quality levels in ascending order; Class 3 admits the commercial rungs.
QUALITY_LEVEL_LADDER = (
    "commercial-catalogue",
    "industrial-grade",
    "automotive-qualified",
    "military-grade",
    "space-qualified",
)

QUALITY_RANK = {level: index for index, level in enumerate(QUALITY_LEVEL_LADDER)}

# Routes that carry their own traceability back to the manufacturer.
SELF_TRACEABLE_ROUTES = ("manufacturer", "franchised-distributor")

# Routes admitted only against evidence that the part is what it claims to be.
EVIDENCE_BEARING_ROUTES = ("open-market-distributor", "broker")

SUPPLY_ROUTES = SELF_TRACEABLE_ROUTES + EVIDENCE_BEARING_ROUTES

# What an evidence-bearing route has to produce before it is admitted.
REQUIRED_AUTHENTICITY_EVIDENCE = (
    "manufacturer-traceability-chain",
    "counterfeit-avoidance-inspection-report",
    "electrical-verification-on-the-delivered-lot",
)

# Recognised ways of justifying use outside the rated envelope.
UPRATING_METHODS = (
    "parameter-conformance",
    "parameter-re-characterization",
    "stress-balance",
)

# A lot older than this is refused on age alone.
DATE_CODE_AGE_LIMIT_MONTHS = 60.0

# Declared quantities; a case meant to sit on a bound can land a few units in
# the last place away from it.
MARGIN_TOLERANCE = 1e-9

TARGET_CATEGORY = "class-3"

PART_TYPE_STATUSES = (
    "class-3-part-type-conforms-to-baseline",
    "class-3-part-type-departs-from-baseline",
    "class-3-part-type-not-in-baseline",
)


def _require_real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _require_text(value, label):
    """Return a required non-empty string field or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_mapping(value, label):
    """Return a required mapping field or raise."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, type(value).__name__))
    return value


def _name_set(raw, allowed, label):
    """Validate a declared collection of names drawn from a closed set."""
    if isinstance(raw, str) or not isinstance(raw, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a list or tuple of names, got %r" % (label, raw))
    names = []
    for name in raw:
        if name not in allowed:
            raise ValueError(
                "unknown %s %r (known: %s)" % (label, name, ", ".join(allowed))
            )
        if name not in names:
            names.append(name)
    return tuple(names)


def quality_rank(level, label="quality level"):
    """Position of a quality level on the ascending ladder."""
    if level not in QUALITY_RANK:
        raise ValueError(
            "unknown %s %r (known: %s)"
            % (label, level, ", ".join(QUALITY_LEVEL_LADDER))
        )
    return QUALITY_RANK[level]


def quality_level_is_adequate(offered_level, minimum_level):
    """True when the offered rung is at or above the rung demanded."""
    return quality_rank(offered_level) >= quality_rank(
        minimum_level, "minimum quality level"
    )


def index_baseline(baseline):
    """Index the agreed baseline by part type, one entry per type."""
    if isinstance(baseline, str) or not isinstance(baseline, (list, tuple)):
        raise ValueError(
            "baseline must be a list or tuple of mappings, got %r" % (baseline,)
        )
    if not baseline:
        raise ValueError("at least one baseline entry is required")
    index = {}
    for raw in baseline:
        entry = _require_mapping(raw, "baseline entry")
        part_type = _require_text(entry.get("part_type"), "part_type")
        if part_type in index:
            raise ValueError("duplicate baseline part_type %r" % (part_type,))
        minimum_level = entry.get("minimum_quality_level")
        quality_rank(minimum_level, "minimum quality level")
        mission_low = _require_real(entry.get("mission_low_c"), "mission_low_c")
        mission_high = _require_real(entry.get("mission_high_c"), "mission_high_c")
        if not mission_high > mission_low:
            raise ValueError(
                "mission_high_c must exceed mission_low_c for %r" % (part_type,)
            )
        index[part_type] = {
            "part_type": part_type,
            "minimum_quality_level": minimum_level,
            "mission_low_c": mission_low,
            "mission_high_c": mission_high,
        }
    return index


def quality_findings(offered_level, entry):
    """Findings raised by the quality level offered against the baseline."""
    quality_rank(offered_level)
    if quality_level_is_adequate(offered_level, entry["minimum_quality_level"]):
        return ()
    return (
        {
            "finding": "offered-quality-level-below-the-baseline-minimum",
            "detail": "%s below %s" % (offered_level, entry["minimum_quality_level"]),
        },
    )


def temperature_margins(rated_low_c, rated_high_c, entry):
    """Cold and hot margins of the rated envelope over the mission envelope."""
    low = _require_real(rated_low_c, "rated_low_c")
    high = _require_real(rated_high_c, "rated_high_c")
    if not high > low:
        raise ValueError("rated_high_c must exceed rated_low_c")
    return {
        "cold_margin_c": entry["mission_low_c"] - low,
        "hot_margin_c": high - entry["mission_high_c"],
    }


def envelope_contains_mission(rated_low_c, rated_high_c, entry):
    """True when the rated envelope covers the mission envelope at both ends."""
    margins = temperature_margins(rated_low_c, rated_high_c, entry)
    return (
        margins["cold_margin_c"] >= -MARGIN_TOLERANCE
        and margins["hot_margin_c"] >= -MARGIN_TOLERANCE
    )


def normalize_uprating_record(record):
    """Validate an uprating justification record."""
    entry = _require_mapping(record, "uprating_record")
    method = entry.get("method")
    if method not in UPRATING_METHODS:
        raise ValueError(
            "unknown uprating method %r (known: %s)"
            % (method, ", ".join(UPRATING_METHODS))
        )
    return {
        "method": method,
        "evidence_reference": _require_text(
            entry.get("evidence_reference"), "evidence_reference"
        ),
    }


def uprating_findings(rated_low_c, rated_high_c, entry, uprating_record):
    """Findings raised where the mission runs outside the rated envelope."""
    margins = temperature_margins(rated_low_c, rated_high_c, entry)
    inside = envelope_contains_mission(rated_low_c, rated_high_c, entry)
    if inside:
        if uprating_record is not None:
            normalize_uprating_record(uprating_record)
        return ()
    ends = []
    if margins["cold_margin_c"] < -MARGIN_TOLERANCE:
        ends.append("cold end %.1f C short" % abs(margins["cold_margin_c"]))
    if margins["hot_margin_c"] < -MARGIN_TOLERANCE:
        ends.append("hot end %.1f C short" % abs(margins["hot_margin_c"]))
    if uprating_record is None:
        return (
            {
                "finding": "temperature-uprating-without-a-justification-record",
                "detail": "; ".join(ends),
            },
        )
    normalize_uprating_record(uprating_record)
    return ()


def authenticity_findings(supply):
    """Findings raised by the route the part was actually bought through."""
    entry = _require_mapping(supply, "supply")
    route = entry.get("route")
    if route not in SUPPLY_ROUTES:
        raise ValueError(
            "unknown supply route %r (known: %s)" % (route, ", ".join(SUPPLY_ROUTES))
        )
    declared = _name_set(
        entry.get("evidence", []),
        REQUIRED_AUTHENTICITY_EVIDENCE,
        "authenticity evidence",
    )
    if route in SELF_TRACEABLE_ROUTES:
        return ()
    return tuple(
        {
            "finding": "evidence-bearing-route-missing-authenticity-evidence",
            "detail": "%s: %s" % (route, item),
        }
        for item in REQUIRED_AUTHENTICITY_EVIDENCE
        if item not in declared
    )


def date_code_findings(age_months, limit_months=DATE_CODE_AGE_LIMIT_MONTHS):
    """Findings raised by the age of the delivered lot."""
    age = _require_real(age_months, "date_code_age_months")
    if age < 0.0:
        raise ValueError("date_code_age_months must not be negative, got %r" % (age,))
    limit = _require_real(limit_months, "date_code_age_limit_months")
    if limit <= 0.0:
        raise ValueError("date_code_age_limit_months must be positive, got %r" % (limit,))
    if age > limit + MARGIN_TOLERANCE:
        return (
            {
                "finding": "lot-date-code-older-than-the-agreed-limit",
                "detail": "%.1f months against %.1f" % (age, limit),
            },
        )
    return ()


def assess_purchased_type(purchase, index, limit_months=DATE_CODE_AGE_LIMIT_MONTHS):
    """Read one purchased part type against the baseline it was bought to."""
    entry_in = _require_mapping(purchase, "purchase")
    part_type = _require_text(entry_in.get("part_type"), "part_type")
    baseline_entry = index.get(part_type)
    if baseline_entry is None:
        return {
            "part_type": part_type,
            "status": "class-3-part-type-not-in-baseline",
            "findings": [
                {
                    "part_type": part_type,
                    "finding": "part-type-bought-against-no-baseline-entry",
                    "detail": part_type,
                }
            ],
            "margins": None,
            "conforms": False,
        }

    findings = []
    findings.extend(quality_findings(entry_in.get("offered_quality_level"), baseline_entry))
    findings.extend(
        uprating_findings(
            entry_in.get("rated_low_c"),
            entry_in.get("rated_high_c"),
            baseline_entry,
            entry_in.get("uprating_record"),
        )
    )
    findings.extend(authenticity_findings(entry_in.get("supply")))
    findings.extend(
        date_code_findings(entry_in.get("date_code_age_months"), limit_months)
    )
    for finding in findings:
        finding["part_type"] = part_type

    margins = temperature_margins(
        entry_in.get("rated_low_c"), entry_in.get("rated_high_c"), baseline_entry
    )
    conforms = not findings
    return {
        "part_type": part_type,
        "offered_quality_level": entry_in.get("offered_quality_level"),
        "minimum_quality_level": baseline_entry["minimum_quality_level"],
        "status": (
            "class-3-part-type-conforms-to-baseline"
            if conforms
            else "class-3-part-type-departs-from-baseline"
        ),
        "margins": margins,
        "findings": findings,
        "conforms": conforms,
    }


def assess_class_3_procurement(order):
    """Judge a Class 3 order against the technical baseline agreed for it."""
    entry = _require_mapping(order, "order")
    order_id = _require_text(entry.get("order_id"), "order_id")
    category = _require_text(entry.get("declared_category"), "declared_category")
    index = index_baseline(entry.get("baseline"))
    purchases = entry.get("purchases")
    if isinstance(purchases, str) or not isinstance(purchases, (list, tuple)):
        raise ValueError(
            "purchases must be a list or tuple of mappings, got %r" % (purchases,)
        )
    if not purchases:
        raise ValueError("at least one purchased part type is required")
    limit = _require_real(
        entry.get("date_code_age_limit_months", DATE_CODE_AGE_LIMIT_MONTHS),
        "date_code_age_limit_months",
    )

    findings = []
    if category != TARGET_CATEGORY:
        findings.append(
            {
                "part_type": "-",
                "finding": "declared-category-is-not-the-one-being-checked",
                "detail": category,
            }
        )

    records = []
    seen = set()
    for purchase in purchases:
        record = assess_purchased_type(purchase, index, limit)
        if record["part_type"] in seen:
            raise ValueError("duplicate purchased part_type %r" % (record["part_type"],))
        seen.add(record["part_type"])
        records.append(record)
        findings.extend(record["findings"])

    never_bought = tuple(
        part_type for part_type in sorted(index) if part_type not in seen
    )
    for part_type in never_bought:
        findings.append(
            {
                "part_type": part_type,
                "finding": "baseline-entry-nobody-ever-bought",
                "detail": part_type,
            }
        )

    conforming = [r["part_type"] for r in records if r["conforms"]]
    departing = [r["part_type"] for r in records if not r["conforms"]]
    return {
        "order_id": order_id,
        "part_type_records": records,
        "conforming_part_types": conforming,
        "departing_part_types": departing,
        "baseline_entries_never_bought": list(never_bought),
        "conforming_fraction": float(len(conforming)) / float(len(records)),
        "findings": findings,
        "order_conforms": not findings,
    }
