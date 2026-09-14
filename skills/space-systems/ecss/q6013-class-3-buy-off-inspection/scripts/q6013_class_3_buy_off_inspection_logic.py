"""Final customer buy-off of a commercial EEE part lot at class 3.

Anchor: ECSS-Q-ST-60-13C clause 6.3.6 (the final customer inspection that
releases a lot of commercial parts at the lowest assurance class).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. At this class the buy-off is normally a documentary release taken on the
   delivery pack rather than a witnessed source inspection, and it may also be
   delegated to the supplier. The three routes are all admissible, but each
   one has to name the thing that makes it auditable: the witnessed route
   needs an independent inspector and the organisation behind them, the desk
   route needs the review record, and the delegated route needs the delegation
   reference and its issue.
2. The required document set is a list of items, not a score. A pack at three
   of four is a hold on the fourth, never a pass at seventy-five percent.
3. The quantity is reconciled rather than accepted. Delivered less the pieces
   rejected on receipt is what the project actually has; a shortfall releases
   what arrived and keeps the rest open, while an overage beyond the declared
   tolerance is a hold because nobody ordered it.
4. Moisture-sensitive parts are released against their packaging. A breached
   barrier bag or a humidity indicator past its limit sends the lot to a bake
   before it goes to the line; a non-sensitive part is untouched by either.
5. Nonconformances are grouped by severity and by the way they were closed.
   Each closure route carries its own requirement: a use-as-is decision needs
   a named authority and a decision day that is not earlier than the delivery,
   a repair needs its verification reference, and a scrapping needs neither
   because the pieces are gone. A closure missing its requirement is an open
   nonconformance wearing a different word.
"""

__all__ = [
    "RELEASE_MODES",
    "REQUIRED_DOCUMENTS",
    "OPTIONAL_DOCUMENTS",
    "NONCONFORMANCE_STATES",
    "SEVERITIES",
    "MOISTURE_SENSITIVE_FROM_LEVEL",
    "INDICATOR_TOLERANCE",
    "parse_day",
    "release_mode_record",
    "document_record",
    "quantity_record",
    "moisture_record",
    "nonconformance_record",
    "assess_buy_off",
]

# How the release may be taken at the lowest assurance class.
RELEASE_MODES = ("source-witness", "documentary-desk-review", "delegated-supplier-release")

# The short document set this class requires before a lot is released.
REQUIRED_DOCUMENTS = (
    "certificate-of-conformity",
    "date-code-traceability-record",
    "packaging-and-esd-evidence",
    "quantity-reconciliation",
)

# Offered rather than required: reported, never blocking.
OPTIONAL_DOCUMENTS = ("test-data-summary", "handling-photographs", "supplier-inspection-report")

# Nonconformance severities and the states a nonconformance can be in.
SEVERITIES = ("major", "minor")
NONCONFORMANCE_STATES = ("open", "use-as-is", "repaired-and-verified", "scrapped")

# Parts at or above this moisture sensitivity level are released on packaging.
MOISTURE_SENSITIVE_FROM_LEVEL = 2

# Absorbs binary representation error when an indicator lands on its limit.
INDICATOR_TOLERANCE = 1e-9


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _rate(label, value):
    """Return value as a percentage in 0..100."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a percentage number, got %r" % (label, value))
    number = float(value)
    if number < 0.0 or number > 100.0:
        raise ValueError("%s must lie in 0..100 percent, got %r" % (label, value))
    return number


def _flag(label, value):
    """Return value as a real boolean; an absent declaration is not a false."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _token(label, value):
    """Return a lowercase hyphenated token for a non-empty string field."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return "-".join(value.strip().lower().replace("_", "-").split())


def _named(mapping, key):
    """Return a stripped non-empty string field, or None where it is absent."""
    value = mapping.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def parse_day(label, value):
    """Return the (year, month, day) triple parsed from a YYYY-MM-DD string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a YYYY-MM-DD string, got %r" % (label, value))
    parts = value.strip().split("-")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("%s must be YYYY-MM-DD, got %r" % (label, value))
    if len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
        raise ValueError("%s must be YYYY-MM-DD, got %r" % (label, value))
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    if month < 1 or month > 12:
        raise ValueError("%s month must lie in 01..12, got %r" % (label, value))
    length = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    if day < 1 or day > length:
        raise ValueError("%s day is out of range for its month, got %r" % (label, value))
    return (year, month, day)


def _ordinal(day):
    """Return a whole-day count for a (year, month, day) triple."""
    year, month, dom = day
    cumulative = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334][month - 1]
    leaps = (year - 1) // 4 - (year - 1) // 100 + (year - 1) // 400
    leap_this_year = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    extra = 1 if (leap_this_year and month > 2) else 0
    return 365 * (year - 1) + leaps + cumulative + extra + dom


def release_mode_record(release):
    """Return the admissibility record for the route the release was taken by.

    release keys: mode, record_reference, and for the witnessed route
    inspector_organisation and inspector_independent, for the delegated route
    delegation_reference and delegation_issue.
    """
    if not isinstance(release, dict):
        raise ValueError("release must be a mapping")
    if "mode" not in release:
        raise ValueError("release missing required key 'mode'")
    mode = _token("mode", release["mode"])
    if mode not in RELEASE_MODES:
        raise ValueError(
            "unknown release mode %r; known modes are %s"
            % (release["mode"], ", ".join(sorted(RELEASE_MODES)))
        )
    missing = []
    if _named(release, "record_reference") is None:
        missing.append("record_reference")
    independent = None
    if mode == "source-witness":
        if _named(release, "inspector_organisation") is None:
            missing.append("inspector_organisation")
        if "inspector_independent" not in release:
            missing.append("inspector_independent")
        else:
            independent = _flag("inspector_independent", release["inspector_independent"])
            if not independent:
                missing.append("an inspector independent of the organisation that built the lot")
    if mode == "delegated-supplier-release":
        if _named(release, "delegation_reference") is None:
            missing.append("delegation_reference")
        if _named(release, "delegation_issue") is None:
            missing.append("delegation_issue")
    return {
        "mode": mode,
        "delegated": mode == "delegated-supplier-release",
        "record_reference": _named(release, "record_reference"),
        "inspector_independent": independent,
        "missing": missing,
        "admissible": not missing,
    }


def document_record(documents_seen):
    """Return the item-by-item walk of the delivery pack.

    documents_seen is a list of document names actually present. The share is
    reported beside the missing list, never instead of it.
    """
    if documents_seen is None:
        documents_seen = []
    if not isinstance(documents_seen, (list, tuple)):
        raise ValueError("documents_seen must be a list of document names")
    known = set(REQUIRED_DOCUMENTS) | set(OPTIONAL_DOCUMENTS)
    seen = []
    for index, name in enumerate(documents_seen):
        key = _token("documents_seen[%d]" % index, name)
        if key not in known:
            raise ValueError(
                "unknown document %r; known documents are %s"
                % (name, ", ".join(sorted(known)))
            )
        if key in seen:
            raise ValueError("document %r is listed twice in the delivery pack" % (key,))
        seen.append(key)
    present = [name for name in REQUIRED_DOCUMENTS if name in seen]
    missing = [name for name in REQUIRED_DOCUMENTS if name not in seen]
    optional_seen = [name for name in OPTIONAL_DOCUMENTS if name in seen]
    return {
        "required_present": present,
        "missing": missing,
        "optional_present": optional_seen,
        "required_share_percent": 100.0 * len(present) / len(REQUIRED_DOCUMENTS),
        "complete": not missing,
        "optional_thin": not optional_seen,
    }


def quantity_record(ordered, delivered, rejected_on_receipt, overage_tolerance_percent=0):
    """Return the reconciliation of what was ordered against what is usable."""
    wanted = _count("ordered", ordered)
    if wanted < 1:
        raise ValueError("ordered must be at least 1, got %d" % wanted)
    arrived = _count("delivered", delivered)
    rejected = _count("rejected_on_receipt", rejected_on_receipt)
    if rejected > arrived:
        raise ValueError(
            "rejected_on_receipt %d exceeds the %d delivered" % (rejected, arrived)
        )
    tolerance = _count("overage_tolerance_percent", overage_tolerance_percent)
    if tolerance > 100:
        raise ValueError("overage_tolerance_percent must lie in 0..100, got %d" % tolerance)
    accepted = arrived - rejected
    ceiling = wanted + wanted * tolerance // 100
    shortfall = max(0, wanted - accepted)
    overage = max(0, arrived - ceiling)
    return {
        "ordered": wanted,
        "delivered": arrived,
        "rejected_on_receipt": rejected,
        "accepted_quantity": accepted,
        "delivery_ceiling": ceiling,
        "shortfall": shortfall,
        "overage": overage,
        "fill_percent": 100.0 * accepted / wanted,
        "reconciled": shortfall == 0 and overage == 0,
    }


def moisture_record(
    moisture_sensitivity_level,
    barrier_bag_intact,
    humidity_indicator_percent=0.0,
    indicator_limit_percent=10.0,
):
    """Return whether the lot has to be baked before it reaches the line."""
    level = _count("moisture_sensitivity_level", moisture_sensitivity_level)
    if level < 1 or level > 6:
        raise ValueError("moisture_sensitivity_level must lie in 1..6, got %d" % level)
    intact = _flag("barrier_bag_intact", barrier_bag_intact)
    indicator = _rate("humidity_indicator_percent", humidity_indicator_percent)
    limit = _rate("indicator_limit_percent", indicator_limit_percent)
    sensitive = level >= MOISTURE_SENSITIVE_FROM_LEVEL
    indicator_exceeded = indicator > limit + INDICATOR_TOLERANCE
    breached = (not intact) or indicator_exceeded
    reasons = []
    if sensitive and not intact:
        reasons.append("the moisture barrier bag arrived breached")
    if sensitive and indicator_exceeded:
        reasons.append(
            "the humidity indicator reads %.3f percent against a limit of %.3f"
            % (indicator, limit)
        )
    return {
        "moisture_sensitivity_level": level,
        "moisture_sensitive": sensitive,
        "barrier_breached": breached,
        "indicator_exceeded": indicator_exceeded,
        "bake_required": sensitive and breached,
        "reasons": reasons,
    }


def nonconformance_record(items, delivery_date, minor_allowance=0):
    """Group the nonconformances by severity and by how they were closed.

    Each item is a mapping of identifier, severity and state, plus whatever
    that closure route requires: authority and decision_date for a use-as-is,
    verification_reference for a repair.
    """
    delivered_on = _ordinal(parse_day("delivery_date", delivery_date))
    allowance = _count("minor_allowance", minor_allowance)
    if items is None:
        items = []
    if not isinstance(items, (list, tuple)):
        raise ValueError("nonconformances must be a list of mappings")
    seen_ids = set()
    open_major, open_minor, closed, refused = [], [], [], []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("nonconformances[%d] must be a mapping" % index)
        for key in ("identifier", "severity", "state"):
            if key not in item:
                raise ValueError("nonconformances[%d] missing required key '%s'" % (index, key))
        identifier = _named(item, "identifier")
        if identifier is None:
            raise ValueError("nonconformances[%d]['identifier'] must be a non-empty string" % index)
        if identifier in seen_ids:
            raise ValueError(
                "nonconformance %r is listed twice; one finding cannot be counted twice"
                % (identifier,)
            )
        seen_ids.add(identifier)
        severity = _token("nonconformances[%d]['severity']" % index, item["severity"])
        if severity not in SEVERITIES:
            raise ValueError(
                "unknown severity %r; known severities are %s"
                % (item["severity"], ", ".join(SEVERITIES))
            )
        state = _token("nonconformances[%d]['state']" % index, item["state"])
        if state not in NONCONFORMANCE_STATES:
            raise ValueError(
                "unknown state %r; known states are %s"
                % (item["state"], ", ".join(NONCONFORMANCE_STATES))
            )
        still_open = state == "open"
        reason = None
        if state == "use-as-is":
            authority = _named(item, "authority")
            decided = item.get("decision_date")
            if authority is None:
                still_open, reason = True, "no authority is named behind the use-as-is decision"
            elif decided is None:
                still_open, reason = True, "the use-as-is decision carries no decision day"
            elif _ordinal(parse_day("decision_date", decided)) < delivered_on:
                still_open, reason = (
                    True,
                    "the use-as-is decision predates the delivery it was meant to disposition",
                )
        elif state == "repaired-and-verified":
            if _named(item, "verification_reference") is None:
                still_open, reason = True, "the repair cites no verification reference"
        entry = {
            "identifier": identifier,
            "severity": severity,
            "state": state,
            "open": still_open,
            "reason": reason,
        }
        if reason is not None:
            refused.append(entry)
        if still_open:
            (open_major if severity == "major" else open_minor).append(entry)
        else:
            closed.append(entry)
    blocking = bool(open_major) or len(open_minor) > allowance
    return {
        "open_majors": open_major,
        "open_minors": open_minor,
        "closed": closed,
        "refused_closures": refused,
        "minor_allowance": allowance,
        "blocking": blocking,
    }


def assess_buy_off(spec):
    """Run the full clause 6.3.6 buy-off assessment for one class 3 lot.

    spec keys: lot_reference, delivery_date, release, documents_seen, ordered,
    delivered, rejected_on_receipt, moisture_sensitivity_level,
    barrier_bag_intact, optional overage_tolerance_percent,
    humidity_indicator_percent, indicator_limit_percent, nonconformances and
    minor_allowance.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "lot_reference",
        "delivery_date",
        "release",
        "ordered",
        "delivered",
        "rejected_on_receipt",
        "moisture_sensitivity_level",
        "barrier_bag_intact",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lot_reference = _named(spec, "lot_reference")
    if lot_reference is None:
        raise ValueError("lot_reference must be a non-empty string")
    release = release_mode_record(spec["release"])
    documents = document_record(spec.get("documents_seen"))
    quantity = quantity_record(
        spec["ordered"],
        spec["delivered"],
        spec["rejected_on_receipt"],
        spec.get("overage_tolerance_percent", 0),
    )
    moisture = moisture_record(
        spec["moisture_sensitivity_level"],
        spec["barrier_bag_intact"],
        spec.get("humidity_indicator_percent", 0.0),
        spec.get("indicator_limit_percent", 10.0),
    )
    nonconformances = nonconformance_record(
        spec.get("nonconformances"), spec["delivery_date"], spec.get("minor_allowance", 0)
    )

    findings = []
    if not release["admissible"]:
        findings.append(
            "the '%s' release route is missing %s"
            % (release["mode"], ", ".join(release["missing"]))
        )
    for name in documents["missing"]:
        findings.append("the delivery pack has no %s" % name)
    if quantity["overage"] > 0:
        findings.append(
            "%d piece(s) arrived beyond the delivery ceiling of %d; nobody ordered them"
            % (quantity["overage"], quantity["delivery_ceiling"])
        )
    if quantity["accepted_quantity"] == 0:
        findings.append("no usable pieces remain after the receipt rejections")
    if moisture["bake_required"]:
        findings.append(
            "level %d parts need a bake before the line: %s"
            % (moisture["moisture_sensitivity_level"], "; ".join(moisture["reasons"]))
        )
    for entry in nonconformances["open_majors"]:
        findings.append(
            "major nonconformance %s is open%s"
            % (entry["identifier"], "" if entry["reason"] is None else ": " + entry["reason"])
        )
    if len(nonconformances["open_minors"]) > nonconformances["minor_allowance"]:
        findings.append(
            "%d open minor nonconformance(s) against a declared allowance of %d"
            % (len(nonconformances["open_minors"]), nonconformances["minor_allowance"])
        )

    advisories = []
    if documents["optional_thin"]:
        advisories.append(
            "no optional evidence was offered with this delivery; the receiving side is "
            "taking the lot on the required pack alone"
        )
    if quantity["shortfall"] > 0 and quantity["accepted_quantity"] > 0:
        advisories.append(
            "%d piece(s) short of the order; the balance stays open against the supplier"
            % quantity["shortfall"]
        )

    blocking = bool(findings)
    if blocking:
        disposition = "hold-on-receipt"
    elif quantity["shortfall"] > 0:
        disposition = "partial-release"
    else:
        disposition = "release-lot"
    return {
        "lot_reference": lot_reference,
        "release": release,
        "documents": documents,
        "quantity": quantity,
        "moisture": moisture,
        "nonconformances": nonconformances,
        "accepted": not blocking,
        "disposition": disposition,
        "findings": findings,
        "advisories": advisories,
    }
