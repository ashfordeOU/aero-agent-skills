#!/usr/bin/env python3
"""Electromagnetic effects verification plan logic (ECSS-E-ST-20C Annex B).

Deterministic, offline, stdlib-only. Paraphrased procedure -- no standard
text is reproduced. The module answers, for the verification plan that
covers the electromagnetic effects requirements: does every requirement
carry an approach, is the method assigned to it admissible for that
requirement kind and supported by the evidence that method needs, is the
integration level of each activity high enough, and do the declared shares
of a requirement add up to full coverage?
"""

import math

__all__ = [
    "PLAN_SECTIONS",
    "METHODS",
    "REQUIREMENT_KINDS",
    "LEVELS",
    "ADMISSIBLE_METHODS",
    "METHOD_EVIDENCE",
    "normalize_method",
    "normalize_requirement_kind",
    "normalize_level",
    "level_rank",
    "check_plan_sections",
    "validate_activity",
    "check_method_admissibility",
    "check_level_adequacy",
    "compute_requirement_coverage",
    "summarize_method_mix",
    "assess_verification_plan",
]

# Absorbs float representation error when declared coverage shares sum to a
# full requirement (ten shares of 0.1 do not sum to exactly 1.0 in binary
# floating point). The coverage requirement itself is never reduced.
_COVERAGE_REL_TOL = 1e-9
_COVERAGE_ABS_TOL = 1e-12

PLAN_SECTIONS = (
    "verification-approach-narrative",
    "requirement-to-activity-matrix",
    "method-justification-record",
    "facility-and-configuration-declaration",
)

_SECTION_SYNONYMS = {
    "approach": "verification-approach-narrative",
    "verification-approach": "verification-approach-narrative",
    "matrix": "requirement-to-activity-matrix",
    "traceability-matrix": "requirement-to-activity-matrix",
    "method-justification": "method-justification-record",
    "facilities": "facility-and-configuration-declaration",
    "facility-declaration": "facility-and-configuration-declaration",
}

METHODS = (
    "verification-by-test",
    "verification-by-analysis",
    "verification-by-review-of-design",
    "verification-by-similarity",
    "verification-by-inspection",
)

_METHOD_SYNONYMS = {
    "test": "verification-by-test",
    "t": "verification-by-test",
    "analysis": "verification-by-analysis",
    "a": "verification-by-analysis",
    "review-of-design": "verification-by-review-of-design",
    "rod": "verification-by-review-of-design",
    "similarity": "verification-by-similarity",
    "s": "verification-by-similarity",
    "inspection": "verification-by-inspection",
    "i": "verification-by-inspection",
}

REQUIREMENT_KINDS = (
    "radiated-emission",
    "radiated-susceptibility",
    "conducted-emission",
    "conducted-susceptibility",
    "electrostatic-discharge",
    "lightning-induced-transient",
    "electrical-bonding-resistance",
    "grounding-architecture",
    "magnetic-moment-limit",
)

_KIND_SYNONYMS = {
    "re": "radiated-emission",
    "rs": "radiated-susceptibility",
    "ce": "conducted-emission",
    "cs": "conducted-susceptibility",
    "esd": "electrostatic-discharge",
    "lightning": "lightning-induced-transient",
    "bonding": "electrical-bonding-resistance",
    "grounding": "grounding-architecture",
    "magnetic-moment": "magnetic-moment-limit",
}

# Which method can close which requirement kind. A field quantity that only
# exists once the item is powered and radiating cannot be closed by reading
# a drawing; a resistance across a bonding strap can.
ADMISSIBLE_METHODS = {
    "radiated-emission": ("verification-by-test", "verification-by-analysis",
                          "verification-by-similarity"),
    "radiated-susceptibility": ("verification-by-test", "verification-by-analysis",
                                "verification-by-similarity"),
    "conducted-emission": ("verification-by-test", "verification-by-analysis",
                           "verification-by-similarity"),
    "conducted-susceptibility": ("verification-by-test", "verification-by-analysis",
                                 "verification-by-similarity"),
    "electrostatic-discharge": ("verification-by-test", "verification-by-analysis",
                                "verification-by-review-of-design"),
    "lightning-induced-transient": ("verification-by-test",
                                    "verification-by-analysis",
                                    "verification-by-similarity"),
    "electrical-bonding-resistance": ("verification-by-test",
                                      "verification-by-inspection"),
    "grounding-architecture": ("verification-by-review-of-design",
                               "verification-by-inspection",
                               "verification-by-test"),
    "magnetic-moment-limit": ("verification-by-test", "verification-by-analysis"),
}

# Evidence each method has to name before an activity counts as planned.
METHOD_EVIDENCE = {
    "verification-by-test": ("facility", "configuration"),
    "verification-by-analysis": ("model_reference",),
    "verification-by-review-of-design": ("design_document_reference",),
    "verification-by-similarity": ("heritage_reference", "delta_justification"),
    "verification-by-inspection": ("acceptance_criterion",),
}

# An analysis closing a field-quantity requirement needs a model correlated
# against measured data, not a bare model reference.
_CORRELATION_REQUIRED_KINDS = (
    "radiated-emission",
    "radiated-susceptibility",
    "lightning-induced-transient",
)

LEVELS = ("equipment-level", "subsystem-level", "system-level")
_LEVEL_RANK = {"equipment-level": 0, "subsystem-level": 1, "system-level": 2}

_LEVEL_SYNONYMS = {
    "equipment": "equipment-level",
    "unit": "equipment-level",
    "unit-level": "equipment-level",
    "subsystem": "subsystem-level",
    "system": "system-level",
    "spacecraft": "system-level",
    "spacecraft-level": "system-level",
}


def _canonical(raw, what):
    if not isinstance(raw, str):
        raise ValueError("%s must be a string, got %r" % (what, type(raw).__name__))
    token = "-".join(raw.strip().lower().split())
    if not token:
        raise ValueError("%s must not be empty" % what)
    return token


def _resolve(raw, what, synonyms, allowed):
    token = _canonical(raw, what)
    token = synonyms.get(token, token)
    if token not in allowed:
        raise ValueError(
            "unknown %s %r; expected one of %s" % (what, raw, ", ".join(allowed))
        )
    return token


def _covers(total, required):
    """True when declared shares reach the required coverage, absorbing float
    representation error at an exactly met requirement."""
    if total >= required:
        return True
    return math.isclose(total, required, rel_tol=_COVERAGE_REL_TOL,
                        abs_tol=_COVERAGE_ABS_TOL)


def _named(value):
    return isinstance(value, str) and bool(value.strip())


def normalize_method(raw):
    """Resolve a declared verification method to its canonical token."""
    return _resolve(raw, "verification method", _METHOD_SYNONYMS, METHODS)


def normalize_requirement_kind(raw):
    """Resolve a declared requirement kind to its canonical token."""
    return _resolve(raw, "requirement kind", _KIND_SYNONYMS, REQUIREMENT_KINDS)


def normalize_level(raw):
    """Resolve a declared integration level to its canonical token."""
    return _resolve(raw, "integration level", _LEVEL_SYNONYMS, LEVELS)


def level_rank(raw):
    """Rank an integration level: equipment 0, subsystem 1, system 2."""
    return _LEVEL_RANK[normalize_level(raw)]


def check_plan_sections(plan):
    """Report the Annex B plan sections that are absent or empty."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping of section name to content")
    declared = set()
    for key, value in plan.items():
        token = _resolve(key, "plan section", _SECTION_SYNONYMS, PLAN_SECTIONS)
        if value in (None, "", [], {}):
            continue
        declared.add(token)
    missing = [s for s in PLAN_SECTIONS if s not in declared]
    return {"declared": sorted(declared), "missing": missing,
            "complete": not missing}


def validate_activity(activity):
    """Normalise one planned verification activity, rejecting bad input."""
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping")
    activity_id = activity.get("id")
    if not _named(activity_id):
        raise ValueError("activity needs a non-empty 'id'")
    method = normalize_method(activity.get("method"))
    level = normalize_level(activity.get("level"))
    share = activity.get("coverage_share", 1.0)
    if isinstance(share, bool) or not isinstance(share, (int, float)):
        raise ValueError("activity %r needs a numeric 'coverage_share'"
                         % activity_id)
    share = float(share)
    if math.isnan(share) or math.isinf(share):
        raise ValueError("activity %r coverage_share must be finite" % activity_id)
    if not 0.0 < share <= 1.0:
        raise ValueError("activity %r coverage_share must lie in (0, 1]"
                         % activity_id)
    record = dict(activity)
    record["id"] = activity_id.strip()
    record["method"] = method
    record["level"] = level
    record["coverage_share"] = share
    return record


def check_method_admissibility(kind, activity):
    """Check the method can close this requirement kind and is supported.

    Returns a findings list: an inadmissible method, missing evidence for
    the method, or an analysis of a field quantity whose model was never
    correlated against measured data.
    """
    kind = normalize_requirement_kind(kind)
    record = validate_activity(activity)
    method = record["method"]
    findings = []
    if method not in ADMISSIBLE_METHODS[kind]:
        findings.append({"activity": record["id"], "kind": kind,
                         "method": method,
                         "finding": "method-not-admissible-for-kind"})
        return findings
    for field in METHOD_EVIDENCE[method]:
        if not _named(record.get(field)):
            findings.append({"activity": record["id"], "kind": kind,
                             "method": method, "field": field,
                             "finding": "method-evidence-undeclared"})
    if method == "verification-by-analysis" and kind in _CORRELATION_REQUIRED_KINDS:
        if not _named(record.get("correlation_evidence")):
            findings.append({"activity": record["id"], "kind": kind,
                             "method": method,
                             "finding": "analysis-model-uncorrelated"})
    return findings


def check_level_adequacy(requirement_level, activity_level):
    """True when the activity runs at or above the requirement's level."""
    return level_rank(activity_level) >= level_rank(requirement_level)


def compute_requirement_coverage(requirement):
    """Sum the declared shares of one requirement and judge completeness."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping")
    req_id = requirement.get("id")
    if not _named(req_id):
        raise ValueError("requirement needs a non-empty 'id'")
    kind = normalize_requirement_kind(requirement.get("kind"))
    level = normalize_level(requirement.get("level"))
    activities = requirement.get("activities")
    if activities is None or isinstance(activities, (str, dict)):
        raise ValueError("requirement %r needs a sequence of activities" % req_id)
    activities = [validate_activity(a) for a in activities]
    if not activities:
        raise ValueError("requirement %r declares no activity" % req_id)
    seen = set()
    total = 0.0
    for record in activities:
        if record["id"] in seen:
            raise ValueError("requirement %r repeats activity id %r"
                             % (req_id, record["id"]))
        seen.add(record["id"])
        total += record["coverage_share"]
    complete = _covers(total, 1.0)
    over = total > 1.0 and not math.isclose(
        total, 1.0, rel_tol=_COVERAGE_REL_TOL, abs_tol=_COVERAGE_ABS_TOL)
    return {
        "id": req_id.strip(),
        "kind": kind,
        "level": level,
        "activities": activities,
        "declared_share": total,
        "deficit": 0.0 if complete else 1.0 - total,
        "complete": complete,
        "over_declared": over,
    }


def summarize_method_mix(requirements):
    """Count planned activities per method across the whole plan."""
    if requirements is None or isinstance(requirements, (str, dict)):
        raise ValueError("requirements must be a sequence of mappings")
    requirements = list(requirements)
    if not requirements:
        raise ValueError("plan must cover at least one requirement")
    counts = {method: 0 for method in METHODS}
    for requirement in requirements:
        coverage = compute_requirement_coverage(requirement)
        for record in coverage["activities"]:
            counts[record["method"]] += 1
    total = sum(counts.values())
    return {
        "counts": counts,
        "activities": total,
        "measured_share": (counts["verification-by-test"] / total) if total else 0.0,
    }


def assess_verification_plan(requirements, min_coverage_index=1.0,
                             plan_sections=None):
    """Run the full Annex B check over the planned requirement set.

    Each requirement is judged on method admissibility, method evidence,
    integration level and declared coverage. The plan passes when no
    requirement carries a finding, the share of fully covered requirements
    reaches min_coverage_index, and any declared section set is complete.
    """
    if isinstance(min_coverage_index, bool) or not isinstance(
            min_coverage_index, (int, float)):
        raise ValueError("min_coverage_index must be a number")
    min_coverage_index = float(min_coverage_index)
    if not 0.0 <= min_coverage_index <= 1.0:
        raise ValueError("min_coverage_index must lie in [0, 1]")
    if requirements is None or isinstance(requirements, (str, dict)):
        raise ValueError("requirements must be a sequence of mappings")
    requirements = list(requirements)
    if not requirements:
        raise ValueError("plan must cover at least one requirement")
    findings = []
    rows = []
    seen = set()
    for requirement in requirements:
        coverage = compute_requirement_coverage(requirement)
        if coverage["id"] in seen:
            raise ValueError("duplicate requirement id %r" % coverage["id"])
        seen.add(coverage["id"])
        for record in coverage["activities"]:
            findings.extend(check_method_admissibility(coverage["kind"], record))
            if not check_level_adequacy(coverage["level"], record["level"]):
                findings.append({"requirement": coverage["id"],
                                 "activity": record["id"],
                                 "finding": "verification-level-too-low",
                                 "detail": "%s below %s" % (record["level"],
                                                            coverage["level"])})
        if not coverage["complete"]:
            findings.append({"requirement": coverage["id"],
                             "finding": "coverage-incomplete",
                             "deficit": coverage["deficit"]})
        if coverage["over_declared"]:
            findings.append({"requirement": coverage["id"],
                             "finding": "coverage-over-declared",
                             "declared_share": coverage["declared_share"]})
        rows.append(coverage)
    covered = sum(1 for r in rows if r["complete"])
    coverage_index = covered / len(rows)
    if not _covers(coverage_index, min_coverage_index):
        findings.append({"finding": "coverage-index-below-floor",
                         "detail": "%.6f < %.6f" % (coverage_index,
                                                    min_coverage_index)})
    sections = None
    if plan_sections is not None:
        sections = check_plan_sections(plan_sections)
        findings.extend({"section": s, "finding": "plan-section-undeclared"}
                        for s in sections["missing"])
    rows.sort(key=lambda r: r["id"])
    return {
        "requirements": rows,
        "coverage_index": coverage_index,
        "method_mix": summarize_method_mix(requirements),
        "sections": sections,
        "findings": findings,
        "acceptable": not findings,
    }
