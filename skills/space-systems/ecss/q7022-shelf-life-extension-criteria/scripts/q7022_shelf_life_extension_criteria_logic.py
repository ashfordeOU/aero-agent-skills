"""Eligibility criteria for extending the shelf life of a stored material.

Anchor: ECSS-Q-ST-70-22 life-extension clause -- the conditions under which the
declared shelf life of a limited-shelf-life material may be extended, and on
what evidence. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Separate the criteria that BLOCK an extension from the caps that merely
   SHORTEN it. A missing evidence base is a refusal; a request longer than the
   per-step cap is a reduced grant.
2. Run the blocking criteria: the family has to be extendable at all, the
   storage record has to be complete and within its exposure allowance, the
   evidence base has to be either a manufacturer statement covering the period
   or a passed re-test, and the item must not have used up its extension count.
3. Apply the caps: a per-step increment as a fraction of the original shelf
   life, and a ceiling on the total life the item may ever accumulate.
4. Grant the smallest of what was asked for and what the caps permit, and say
   plainly which cap did the cutting.
5. Close with granted / granted-reduced / refused and the reasons for each.
"""

import math

__all__ = [
    "DAY_TOLERANCE",
    "MAX_EXTENSION_COUNT",
    "MAX_INCREMENT_FRACTION",
    "MAX_TOTAL_LIFE_FRACTION",
    "NON_EXTENDABLE_FAMILIES",
    "EVIDENCE_SOURCES",
    "validate_request",
    "evidence_basis",
    "blocking_criteria",
    "increment_cap_days",
    "total_life_cap_days",
    "granted_extension_days",
    "assess_shelf_life_extension",
]

# Caps are fractions of an integer day count; take the whole day only when it
# is really there, not when the product lands a few ULPs below an integer.
DAY_TOLERANCE = 1e-9

# An item may be extended at most this many times in its life.
MAX_EXTENSION_COUNT = 2

# One extension step may not exceed this fraction of the ORIGINAL shelf life.
MAX_INCREMENT_FRACTION = 0.5

# Original plus every extension may not exceed this multiple of the original.
MAX_TOTAL_LIFE_FRACTION = 2.0

# Families whose degradation is not evidenced by the available property tests,
# so no amount of re-testing supports an extension.
NON_EXTENDABLE_FAMILIES = ("pyrotechnic-composition", "catalysed-premix", "activated-adhesive")

EVIDENCE_SOURCES = ("manufacturer-statement", "qualification-data", "re-test-report")


def _int(value, label, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def validate_request(request):
    """Return a normalised extension request."""
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping")
    ident = request.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("request needs a non-empty 'id'")
    family = request.get("family")
    if not isinstance(family, str) or not family.strip():
        raise ValueError("request needs a non-empty 'family'")
    original = _int(request.get("original_shelf_life_days"), "original_shelf_life_days", 1)
    requested = _int(request.get("requested_days"), "requested_days", 1)
    granted_before = _int(request.get("previously_granted_days", 0), "previously_granted_days")
    count = _int(request.get("prior_extension_count", 0), "prior_extension_count")
    sources = request.get("evidence_sources", [])
    if not isinstance(sources, (list, tuple)):
        raise ValueError("evidence_sources must be a sequence")
    normalised_sources = []
    for source in sources:
        if not isinstance(source, str) or source.strip() not in EVIDENCE_SOURCES:
            raise ValueError(
                "unknown evidence source %r; known sources: %s"
                % (source, ", ".join(EVIDENCE_SOURCES))
            )
        normalised_sources.append(source.strip())
    for key in ("storage_record_complete", "exposure_within_allowance", "re_test_passed"):
        if not isinstance(request.get(key, False), bool):
            raise ValueError("%s must be true or false, got %r" % (key, request.get(key)))
    covers = request.get("manufacturer_statement_covers_days", 0)
    covers = _int(covers, "manufacturer_statement_covers_days")
    return {
        "id": ident.strip(),
        "family": family.strip().lower(),
        "original_shelf_life_days": original,
        "requested_days": requested,
        "previously_granted_days": granted_before,
        "prior_extension_count": count,
        "evidence_sources": normalised_sources,
        "storage_record_complete": bool(request.get("storage_record_complete", False)),
        "exposure_within_allowance": bool(request.get("exposure_within_allowance", False)),
        "re_test_passed": bool(request.get("re_test_passed", False)),
        "manufacturer_statement_covers_days": covers,
    }


def evidence_basis(request):
    """Return the evidence basis the request can stand on, or None."""
    norm = validate_request(request)
    has_statement = "manufacturer-statement" in norm["evidence_sources"]
    covers = norm["manufacturer_statement_covers_days"] >= norm["requested_days"]
    if has_statement and covers:
        return "manufacturer-statement"
    if "re-test-report" in norm["evidence_sources"] and norm["re_test_passed"]:
        return "passed-re-test"
    return None


def blocking_criteria(request):
    """Return one record per blocking criterion, met or not."""
    norm = validate_request(request)
    basis = evidence_basis(norm)
    criteria = [
        {
            "name": "family-extendable",
            "met": norm["family"] not in NON_EXTENDABLE_FAMILIES,
            "detail": "family %s is outside the non-extendable set" % norm["family"]
                      if norm["family"] not in NON_EXTENDABLE_FAMILIES
                      else "family %s is not extendable on any evidence" % norm["family"],
        },
        {
            "name": "storage-record-complete",
            "met": norm["storage_record_complete"],
            "detail": "storage record complete" if norm["storage_record_complete"]
                      else "storage record is incomplete, so the item's history is unknown",
        },
        {
            "name": "exposure-within-allowance",
            "met": norm["exposure_within_allowance"],
            "detail": "recorded exposure is within allowance"
                      if norm["exposure_within_allowance"]
                      else "recorded exposure exceeded its allowance",
        },
        {
            "name": "evidence-basis",
            "met": basis is not None,
            "detail": "extension rests on %s" % basis if basis
                      else "no manufacturer statement covering the period and no passed re-test",
        },
        {
            "name": "extension-count",
            "met": norm["prior_extension_count"] < MAX_EXTENSION_COUNT,
            "detail": "%d of %d extensions used"
                      % (norm["prior_extension_count"], MAX_EXTENSION_COUNT),
        },
    ]
    return criteria


def increment_cap_days(request):
    """Return the largest single extension step the original shelf life permits."""
    norm = validate_request(request)
    cap = MAX_INCREMENT_FRACTION * norm["original_shelf_life_days"]
    return int(math.floor(cap + DAY_TOLERANCE))


def total_life_cap_days(request):
    """Return the extension days still available under the total-life ceiling."""
    norm = validate_request(request)
    ceiling = MAX_TOTAL_LIFE_FRACTION * norm["original_shelf_life_days"]
    total_allowed = int(math.floor(ceiling + DAY_TOLERANCE))
    headroom = total_allowed - norm["original_shelf_life_days"] - norm["previously_granted_days"]
    return headroom if headroom > 0 else 0


def granted_extension_days(request):
    """Return the days actually grantable and which cap, if any, cut the request."""
    norm = validate_request(request)
    step_cap = increment_cap_days(norm)
    life_cap = total_life_cap_days(norm)
    granted = norm["requested_days"]
    limited_by = None
    if step_cap < granted:
        granted = step_cap
        limited_by = "per-step-increment-cap"
    if life_cap < granted:
        granted = life_cap
        limited_by = "total-life-cap"
    if granted < 0:
        granted = 0
    return {
        "requested_days": norm["requested_days"],
        "increment_cap_days": step_cap,
        "total_life_cap_days": life_cap,
        "granted_days": granted,
        "limited_by": limited_by,
    }


def assess_shelf_life_extension(request):
    """Decide whether a shelf-life extension is supportable and for how long."""
    norm = validate_request(request)
    criteria = blocking_criteria(norm)
    unmet = [item["name"] for item in criteria if not item["met"]]
    grant = granted_extension_days(norm)
    findings = [item["detail"] for item in criteria if not item["met"]]
    if not unmet and grant["limited_by"] is not None and grant["granted_days"] > 0:
        findings.append(
            "requested %d day(s) reduced to %d by the %s"
            % (grant["requested_days"], grant["granted_days"], grant["limited_by"])
        )
    if unmet:
        disposition = "extension-refused"
        granted = 0
    elif grant["granted_days"] <= 0:
        disposition = "extension-refused"
        granted = 0
        findings.append("no extension days remain under the total-life ceiling")
    elif grant["granted_days"] < grant["requested_days"]:
        disposition = "extension-granted-reduced"
        granted = grant["granted_days"]
    else:
        disposition = "extension-granted"
        granted = grant["granted_days"]
    return {
        "id": norm["id"],
        "criteria": criteria,
        "unmet_criteria": unmet,
        "evidence_basis": evidence_basis(norm),
        "caps": grant,
        "granted_days": granted,
        "eligible": disposition != "extension-refused",
        "disposition": disposition,
        "findings": findings,
    }
