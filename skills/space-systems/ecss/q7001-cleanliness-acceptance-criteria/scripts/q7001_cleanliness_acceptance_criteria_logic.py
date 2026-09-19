"""Acceptance decisions and nonconformance handling for cleanliness results.

Anchor: ECSS-Q-ST-70-01C, verification clause -- applying the acceptance
criterion to a measured cleanliness value and routing the nonconformance that
an exceedance creates. Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide the result against the limit under the declared decision rule.
   Under a guard-banded rule the measurement uncertainty is spent by the
   party making the claim, so a value plus its expanded uncertainty has to
   stay inside the limit to be accepted and minus its uncertainty has to sit
   outside to be rejected; between the two the result is indeterminate and
   the measurement, not the hardware, is what has to be repeated.
   Under a shared-risk rule the value alone is compared.
2. Size the exceedance as a ratio of the measured value to the limit.
3. Group the nonconformance by that ratio together with the criticality of
   the surface and whether the exceedance repeats after a cleaning attempt.
4. Route the disposition: re-clean and re-verify where the surface can still
   be reached and cleaned, escalate to a review board where it repeats, is
   major, or where the surface can no longer be cleaned, and allow a
   use-as-is only where an accepted impact analysis backs it.
5. Summarise a set of results into counts, dispositions and findings.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "MINOR_RATIO_CEILING",
    "DECISION_RULES",
    "VERDICTS",
    "validate_result",
    "expanded_uncertainty",
    "decide_against_limit",
    "exceedance_ratio",
    "categorize_nonconformance",
    "disposition_for",
    "handle_result",
    "summarise_acceptance",
]

# An exact equality with the limit is a representation question, not an
# engineering one; absorb it here rather than by moving the limit.
LIMIT_TOLERANCE = 1e-9

# An exceedance up to this multiple of the limit on a non-critical surface is
# handled as a minor nonconformance; beyond it, or on a critical surface, it
# is major.
MINOR_RATIO_CEILING = 1.25

DECISION_RULES = ("guard-banded", "shared-risk")

VERDICTS = ("accept", "reject", "indeterminate")


def _finite(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _positive(label, value):
    """Return value as a strictly positive finite float or raise."""
    number = _finite(label, value)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_result(result):
    """Return a normalised cleanliness measurement result record."""
    if not isinstance(result, dict):
        raise ValueError("result must be a mapping")
    for key in ("id", "value", "limit"):
        if key not in result:
            raise ValueError("result missing required key '%s'" % key)
    identifier = result["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("result['id'] must be a non-empty string")
    value = _finite("result['value']", result["value"])
    if value < 0.0:
        raise ValueError("result['value'] must not be negative")
    rule = result.get("decision_rule", "guard-banded")
    if rule not in DECISION_RULES:
        raise ValueError(
            "decision_rule must be one of %s, got %r" % (DECISION_RULES, rule)
        )
    uncertainty = _finite(
        "result['standard_uncertainty']", result.get("standard_uncertainty", 0.0)
    )
    if uncertainty < 0.0:
        raise ValueError("standard_uncertainty must not be negative")
    coverage = _positive("result['coverage_factor']", result.get("coverage_factor", 2.0))
    return {
        "id": identifier.strip(),
        "value": value,
        "limit": _positive("result['limit']", result["limit"]),
        "standard_uncertainty": uncertainty,
        "coverage_factor": coverage,
        "decision_rule": rule,
        "critical": bool(result.get("critical", False)),
        "recleanable": bool(result.get("recleanable", True)),
        "repeat_exceedance": bool(result.get("repeat_exceedance", False)),
        "impact_analysis_accepted": bool(result.get("impact_analysis_accepted", False)),
    }


def expanded_uncertainty(standard_uncertainty, coverage_factor=2.0):
    """Return the expanded uncertainty at the declared coverage factor."""
    standard = _finite("standard_uncertainty", standard_uncertainty)
    if standard < 0.0:
        raise ValueError("standard_uncertainty must not be negative")
    return standard * _positive("coverage_factor", coverage_factor)


def decide_against_limit(value, limit, expanded=0.0, rule="guard-banded"):
    """Return 'accept', 'reject' or 'indeterminate' for one measured value."""
    measured = _finite("value", value)
    if measured < 0.0:
        raise ValueError("value must not be negative")
    bound = _positive("limit", limit)
    spread = _finite("expanded", expanded)
    if spread < 0.0:
        raise ValueError("expanded uncertainty must not be negative")
    if rule not in DECISION_RULES:
        raise ValueError(
            "rule must be one of %s, got %r" % (DECISION_RULES, rule)
        )
    if rule == "shared-risk":
        spread = 0.0
    upper = measured + spread
    lower = measured - spread
    if upper < bound or math.isclose(upper, bound, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0):
        return "accept"
    if lower > bound and not math.isclose(
        lower, bound, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0
    ):
        return "reject"
    return "indeterminate"


def exceedance_ratio(value, limit):
    """Return the measured value as a multiple of the limit."""
    measured = _finite("value", value)
    if measured < 0.0:
        raise ValueError("value must not be negative")
    return measured / _positive("limit", limit)


def categorize_nonconformance(ratio, critical=False, repeat=False):
    """Return 'minor' or 'major' for an exceedance of this size and context."""
    value = _finite("ratio", ratio)
    if value <= 1.0 and not math.isclose(
        value, 1.0, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0
    ):
        raise ValueError(
            "ratio %g is not an exceedance; nothing to categorize" % value
        )
    if not isinstance(critical, bool):
        raise ValueError("critical must be a boolean")
    if not isinstance(repeat, bool):
        raise ValueError("repeat must be a boolean")
    if critical or repeat:
        return "major"
    if value < MINOR_RATIO_CEILING or math.isclose(
        value, MINOR_RATIO_CEILING, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0
    ):
        return "minor"
    return "major"


def disposition_for(category, recleanable=True, impact_analysis_accepted=False,
                    repeat=False):
    """Return the route an exceedance of this category has to take."""
    if category not in ("minor", "major"):
        raise ValueError("category must be 'minor' or 'major', got %r" % (category,))
    for label, flag in (
        ("recleanable", recleanable),
        ("impact_analysis_accepted", impact_analysis_accepted),
        ("repeat", repeat),
    ):
        if not isinstance(flag, bool):
            raise ValueError("%s must be a boolean" % label)
    if category == "minor" and recleanable and not repeat:
        return "reclean-and-reverify"
    if impact_analysis_accepted:
        return "use-as-is-with-impact-analysis"
    if recleanable and not repeat:
        return "reclean-and-reverify"
    return "escalate-to-review-board"


def handle_result(result):
    """Return the acceptance decision and nonconformance route for one result."""
    record = validate_result(result)
    expanded = expanded_uncertainty(
        record["standard_uncertainty"], record["coverage_factor"]
    )
    verdict = decide_against_limit(
        record["value"], record["limit"], expanded, record["decision_rule"]
    )
    ratio = exceedance_ratio(record["value"], record["limit"])
    entry = {
        "id": record["id"],
        "verdict": verdict,
        "exceedance_ratio": ratio,
        "expanded_uncertainty": expanded,
        "category": None,
        "disposition": None,
        "findings": [],
    }
    if verdict == "accept":
        entry["disposition"] = "accept"
        return entry
    if verdict == "indeterminate":
        entry["disposition"] = "repeat-the-measurement"
        entry["findings"].append(
            "value %.6g with expanded uncertainty %.6g straddles the limit %.6g; "
            "the measurement, not the hardware, is what repeats"
            % (record["value"], expanded, record["limit"])
        )
        return entry
    category = categorize_nonconformance(
        ratio, record["critical"], record["repeat_exceedance"]
    )
    entry["category"] = category
    entry["disposition"] = disposition_for(
        category,
        record["recleanable"],
        record["impact_analysis_accepted"],
        record["repeat_exceedance"],
    )
    entry["findings"].append(
        "%s nonconformance: %.6g is %.4gx the limit %.6g"
        % (category, record["value"], ratio, record["limit"])
    )
    if record["critical"] and category == "major":
        entry["findings"].append(
            "surface %s is criticality-driven; the exceedance is major whatever "
            "its size" % record["id"]
        )
    if entry["disposition"] == "use-as-is-with-impact-analysis":
        entry["findings"].append(
            "use-as-is rests on the accepted impact analysis, which has to bound "
            "the effect of %.6g on the function the limit protects" % record["value"]
        )
    return entry


def summarise_acceptance(results):
    """Return the acceptance summary for a set of cleanliness results."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    entries = [handle_result(item) for item in results]
    seen = []
    for entry in entries:
        if entry["id"] in seen:
            raise ValueError("duplicate result id %r" % entry["id"])
        seen.append(entry["id"])
    counts = {name: 0 for name in VERDICTS}
    for entry in entries:
        counts[entry["verdict"]] += 1
    findings = []
    for entry in entries:
        findings.extend(entry["findings"])
    escalated = [
        entry["id"] for entry in entries
        if entry["disposition"] == "escalate-to-review-board"
    ]
    return {
        "entries": entries,
        "counts": counts,
        "escalated": escalated,
        "accepted_fraction": counts["accept"] / float(len(entries)),
        "findings": findings,
        "all_accepted": counts["accept"] == len(entries),
    }
