"""Baseline selection rule for a hybrid microcircuit manufacturer.

Anchor: ECSS-Q-ST-60-05 clause 5.1 (general requirement on manufacturer
selection: whichever maker is chosen has to pass the validation route the
standard defines for it further on). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the candidate's category and derive the validation route that the
   baseline rule binds it to. A maker whose production line already carries
   an approval owes the shorter route; a maker whose line does not owes the
   route that starts with the line evaluation.
2. Validate every piece of validation evidence offered: a kind the route
   recognises, a well-formed issue and expiry date, and a declared standing.
3. Decide, at the assessment date, whether each required kind is held, held
   but lapsed, or held but suspended or withdrawn.
4. Check the evidence also covers the procurement, not only the moment of
   selection: evidence that expires before the lot is due leaves the buy
   uncovered where it matters.
5. Refuse heritage, flight history or a standing commercial relationship as
   a substitute for a missing route element, and report it as its own
   finding rather than letting it silently close the gap.
"""

import datetime

__all__ = [
    "CATEGORY_APPROVED_LINE",
    "CATEGORY_NO_APPROVED_LINE",
    "CATEGORIES",
    "ROUTE_APPROVED_LINE",
    "ROUTE_FULL_VALIDATION",
    "ROUTES",
    "REQUIRED_EVIDENCE",
    "EVIDENCE_KINDS",
    "ACCEPTABLE_STANDINGS",
    "normalize_category",
    "route_for_category",
    "required_evidence",
    "normalize_evidence_kind",
    "normalize_standing",
    "parse_date",
    "validate_evidence",
    "evidence_state",
    "days_of_cover",
    "evidence_by_kind",
    "missing_evidence",
    "assess_manufacturer_selection",
]

CATEGORY_APPROVED_LINE = "approved-line"
CATEGORY_NO_APPROVED_LINE = "no-approved-line"
CATEGORIES = (CATEGORY_APPROVED_LINE, CATEGORY_NO_APPROVED_LINE)

_CATEGORY_ALIASES = {
    "approved-line": CATEGORY_APPROVED_LINE,
    "approved_line": CATEGORY_APPROVED_LINE,
    "approved line": CATEGORY_APPROVED_LINE,
    "category-1": CATEGORY_APPROVED_LINE,
    "no-approved-line": CATEGORY_NO_APPROVED_LINE,
    "no_approved_line": CATEGORY_NO_APPROVED_LINE,
    "non-approved-line": CATEGORY_NO_APPROVED_LINE,
    "unapproved-line": CATEGORY_NO_APPROVED_LINE,
    "category-2": CATEGORY_NO_APPROVED_LINE,
}

ROUTE_APPROVED_LINE = "approved-line-validation"
ROUTE_FULL_VALIDATION = "full-validation"
ROUTES = (ROUTE_APPROVED_LINE, ROUTE_FULL_VALIDATION)

_ROUTE_FOR_CATEGORY = {
    CATEGORY_APPROVED_LINE: ROUTE_APPROVED_LINE,
    CATEGORY_NO_APPROVED_LINE: ROUTE_FULL_VALIDATION,
}

# What each route has to show before a maker can be selected under the
# baseline rule. The longer route adds the two line elements on top.
REQUIRED_EVIDENCE = {
    ROUTE_APPROVED_LINE: (
        "production-line-approval-certificate",
        "quality-management-certification",
        "process-identification-document",
    ),
    ROUTE_FULL_VALIDATION: (
        "manufacturer-audit-report",
        "production-line-evaluation-record",
        "production-line-approval-certificate",
        "quality-management-certification",
        "process-identification-document",
    ),
}

EVIDENCE_KINDS = tuple(sorted(set(
    kind for kinds in REQUIRED_EVIDENCE.values() for kind in kinds
)))

# Standings a document can carry. Only the first one supports a selection.
ACCEPTABLE_STANDINGS = ("valid",)
_STANDINGS = ("valid", "suspended", "withdrawn")

# Claims that are sometimes offered instead of a route element.
_SUBSTITUTE_CLAIMS = (
    "flight-heritage",
    "long-standing-supply",
    "sister-site-approval",
    "customer-preference",
)


def normalize_category(category):
    """Return the canonical manufacturer category name."""
    if not isinstance(category, str):
        raise ValueError("category must be a string, got %r" % (category,))
    key = category.strip().lower().replace(" ", "-")
    if not key:
        raise ValueError("category must not be empty")
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    raise ValueError("unknown manufacturer category %r" % (category,))


def route_for_category(category):
    """Return the validation route the baseline rule binds the category to."""
    return _ROUTE_FOR_CATEGORY[normalize_category(category)]


def required_evidence(route):
    """Return the evidence kinds the given validation route has to show."""
    if not isinstance(route, str):
        raise ValueError("route must be a string, got %r" % (route,))
    key = route.strip().lower()
    if key not in REQUIRED_EVIDENCE:
        raise ValueError("unknown validation route %r" % (route,))
    return REQUIRED_EVIDENCE[key]


def normalize_evidence_kind(kind):
    """Return the canonical name of a piece of validation evidence."""
    if not isinstance(kind, str):
        raise ValueError("evidence kind must be a string, got %r" % (kind,))
    key = kind.strip().lower().replace("_", "-").replace(" ", "-")
    if key not in EVIDENCE_KINDS:
        raise ValueError("unknown validation evidence kind %r" % (kind,))
    return key


def normalize_standing(standing):
    """Return the canonical standing a validation document carries."""
    if not isinstance(standing, str):
        raise ValueError("standing must be a string, got %r" % (standing,))
    key = standing.strip().lower()
    if key not in _STANDINGS:
        raise ValueError("unknown document standing %r" % (standing,))
    return key


def parse_date(value):
    """Return a date from an ISO yyyy-mm-dd string or a date object."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("date must be an ISO string or a date, got %r" % (value,))
    text = value.strip()
    parts = text.split("-")
    if len(parts) != 3 or len(parts[0]) != 4:
        raise ValueError("date %r must be formatted yyyy-mm-dd" % (value,))
    try:
        year, month, day = (int(p) for p in parts)
        return datetime.date(year, month, day)
    except ValueError:
        raise ValueError("date %r is not a real calendar date" % (value,))


def validate_evidence(record):
    """Return a canonical validation-evidence record."""
    if not isinstance(record, dict):
        raise ValueError("evidence record must be a mapping")
    for key in ("kind", "issued", "valid_until"):
        if key not in record:
            raise ValueError("evidence record missing required key '%s'" % key)
    kind = normalize_evidence_kind(record["kind"])
    issued = parse_date(record["issued"])
    valid_until = parse_date(record["valid_until"])
    if valid_until < issued:
        raise ValueError(
            "evidence %s expires %s before it was issued %s" % (kind, valid_until, issued)
        )
    standing = normalize_standing(record.get("standing", "valid"))
    reference = record.get("reference")
    if reference is not None and not isinstance(reference, str):
        raise ValueError("evidence reference must be a string when given")
    return {
        "kind": kind,
        "issued": issued,
        "valid_until": valid_until,
        "standing": standing,
        "reference": reference,
    }


def evidence_state(record, on_date):
    """Return 'valid', 'lapsed', 'suspended' or 'withdrawn' at a date."""
    canonical = validate_evidence(record)
    when = parse_date(on_date)
    if when < canonical["issued"]:
        raise ValueError(
            "assessment date %s precedes the issue date %s of %s"
            % (when, canonical["issued"], canonical["kind"])
        )
    if canonical["standing"] != "valid":
        return canonical["standing"]
    if when > canonical["valid_until"]:
        return "lapsed"
    return "valid"


def days_of_cover(record, from_date):
    """Return whole days of remaining cover; zero on the expiry date itself."""
    canonical = validate_evidence(record)
    start = parse_date(from_date)
    return (canonical["valid_until"] - start).days


def evidence_by_kind(records, on_date):
    """Group evidence by kind, keeping the entry with the longest cover."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("evidence must be a list or tuple of records")
    grouped = {}
    for record in records:
        canonical = validate_evidence(record)
        state = evidence_state(record, on_date)
        kind = canonical["kind"]
        candidate = dict(canonical)
        candidate["state"] = state
        held = grouped.get(kind)
        if held is None:
            grouped[kind] = candidate
            continue
        better_standing = held["state"] != "valid" and state == "valid"
        longer_cover = (
            held["state"] == state and candidate["valid_until"] > held["valid_until"]
        )
        if better_standing or longer_cover:
            grouped[kind] = candidate
    return grouped


def missing_evidence(route, records, on_date):
    """Return the required kinds with no usable evidence at the given date."""
    grouped = evidence_by_kind(records, on_date)
    missing = []
    for kind in required_evidence(route):
        entry = grouped.get(kind)
        if entry is None or entry["state"] != "valid":
            missing.append(kind)
    return missing


def assess_manufacturer_selection(spec):
    """Grade a candidate hybrid manufacturer against the baseline rule.

    spec keys: category, evidence (list of records), assessment_date, optional
    cover_until naming the date the procurement has to stay covered to, and
    optional substitute_claims listing arguments offered in place of evidence.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("category", "evidence", "assessment_date"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    category = normalize_category(spec["category"])
    route = route_for_category(category)
    when = parse_date(spec["assessment_date"])
    grouped = evidence_by_kind(spec["evidence"], when)
    required = required_evidence(route)
    cover_until = None
    if spec.get("cover_until") is not None:
        cover_until = parse_date(spec["cover_until"])
        if cover_until < when:
            raise ValueError("cover_until %s precedes the assessment date %s" % (cover_until, when))
    findings = []
    missing = []
    lapsed = []
    unusable = []
    short_cover = []
    for kind in required:
        entry = grouped.get(kind)
        if entry is None:
            missing.append(kind)
            findings.append("%s route has no %s on file" % (route, kind))
            continue
        state = entry["state"]
        if state == "lapsed":
            lapsed.append(kind)
            findings.append("%s lapsed on %s" % (kind, entry["valid_until"]))
            continue
        if state != "valid":
            unusable.append(kind)
            findings.append("%s is recorded as %s" % (kind, state))
            continue
        if cover_until is not None and entry["valid_until"] < cover_until:
            short_cover.append(kind)
            findings.append(
                "%s expires %s, before the procurement is covered to %s"
                % (kind, entry["valid_until"], cover_until)
            )
    claims = spec.get("substitute_claims") or []
    if not isinstance(claims, (list, tuple)):
        raise ValueError("substitute_claims must be a list or tuple when given")
    offered = []
    for claim in claims:
        if not isinstance(claim, str):
            raise ValueError("a substitute claim must be a string, got %r" % (claim,))
        key = claim.strip().lower().replace("_", "-").replace(" ", "-")
        if key not in _SUBSTITUTE_CLAIMS:
            raise ValueError("unknown substitute claim %r" % (claim,))
        offered.append(key)
    if offered and (missing or lapsed or unusable):
        findings.append(
            "claim %s is offered where the route is open; heritage does not "
            "stand in for a route element" % ", ".join(sorted(set(offered)))
        )
    extra = tuple(sorted(k for k in grouped if k not in required))
    return {
        "category": category,
        "route": route,
        "required_evidence": required,
        "missing_evidence": tuple(missing),
        "lapsed_evidence": tuple(lapsed),
        "unusable_evidence": tuple(unusable),
        "short_cover_evidence": tuple(short_cover),
        "surplus_evidence": extra,
        "substitute_claims": tuple(sorted(set(offered))),
        "assessment_date": when,
        "cover_until": cover_until,
        "selectable": not findings,
        "findings": findings,
    }
