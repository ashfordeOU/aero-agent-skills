#!/usr/bin/env python3
"""ECSS-E-ST-10C §8.2.9 / ECSS-E-ST-10-02C requirement verifiability check
(paraphrase, not copy).

Common-knowledge summary: the ECSS systems engineering standard requires each
requirement to be verifiable -- meaning at least one verification method
(Test, Analysis, Inspection, Review of Design -- T/A/I/D) and at least one
verification level (system, subsystem, equipment, component) must be assignable
and documented, forming a traceable entry in the project's verification
requirements database (VRDB). A requirement whose text bundles multiple
independently verifiable conditions (detectable by more than one "shall" clause)
may be non-verifiable because each condition cannot be individually confirmed
as met. This module implements method and level validation, compound-requirement
detection, per-requirement verifiability assessment, set-level assessment, and
findings aggregation.
"""

VERIFICATION_METHODS = frozenset({"T", "A", "I", "D"})
# T = Test, A = Analysis, I = Inspection, D = Review of Design
# per ECSS-E-ST-10-02C §4.5

VERIFICATION_LEVELS = frozenset({"system", "subsystem", "equipment", "component"})
# per ECSS-E-ST-10C §8.2.9 system hierarchy tiers


def validate_method(method):
    """Return method when it is a recognized ECSS verification method code.
    Raises ValueError for any code outside the recognized set."""
    if method not in VERIFICATION_METHODS:
        raise ValueError(
            "unrecognized verification method %r; expected one of %s "
            "(ECSS-E-ST-10-02C §4.5)" % (method, sorted(VERIFICATION_METHODS))
        )
    return method


def validate_level(level):
    """Return level when it is a recognized ECSS verification level.
    Raises ValueError for any identifier outside the recognized set."""
    if level not in VERIFICATION_LEVELS:
        raise ValueError(
            "unrecognized verification level %r; expected one of %s "
            "(ECSS-E-ST-10C §8.2.9)" % (level, sorted(VERIFICATION_LEVELS))
        )
    return level


def is_compound_requirement(text):
    """Return True when text contains more than one occurrence of the word
    'shall' (case-insensitive), indicating the requirement likely bundles
    multiple independently verifiable conditions into a single statement.
    Returns False for empty text (handled separately as missing_text)."""
    if not text:
        return False
    return text.lower().split().count("shall") > 1


def assess_verifiability(req):
    """Verifiability assessment for one requirement under ECSS-E-ST-10C §8.2.9.

    req: dict with keys --
      req_id  -- str, the requirement identifier
      text    -- str, the requirement statement
      methods -- list[str], assigned verification method codes
      levels  -- list[str], assigned verification levels

    Returns a new dict (req is never mutated):
      req_id     -- str
      verifiable -- bool (True only when findings is empty)
      findings   -- list[dict], each with at least an "issue" key
    """
    req_id = req.get("req_id", "")
    text = req.get("text", "")
    methods = list(req.get("methods") or [])
    levels = list(req.get("levels") or [])
    findings = []

    if not text or not text.strip():
        findings.append({"issue": "missing_text", "req_id": req_id})

    if not methods:
        findings.append({"issue": "no_method_assigned", "req_id": req_id})
    else:
        invalid = [m for m in methods if m not in VERIFICATION_METHODS]
        if invalid:
            findings.append({
                "issue": "invalid_method",
                "req_id": req_id,
                "invalid": invalid,
            })

    if not levels:
        findings.append({"issue": "no_level_assigned", "req_id": req_id})
    else:
        invalid = [lv for lv in levels if lv not in VERIFICATION_LEVELS]
        if invalid:
            findings.append({
                "issue": "invalid_level",
                "req_id": req_id,
                "invalid": invalid,
            })

    if is_compound_requirement(text):
        findings.append({
            "issue": "compound_requirement",
            "req_id": req_id,
            "detail": (
                "text contains multiple 'shall' clauses; split into "
                "separate requirements before assigning method-level"
            ),
        })

    return {
        "req_id": req_id,
        "verifiable": len(findings) == 0,
        "findings": findings,
    }


def assess_set(requirements):
    """Assess a list of requirement dicts; return a list of verifiability
    result dicts in the same order as the input. Input is not mutated."""
    return [assess_verifiability(req) for req in requirements]


def is_verifiable(result):
    """True when a verifiability result dict has no findings."""
    return result["verifiable"]


def summarize_results(results):
    """Aggregate verifiability counts and findings-by-type from a list of
    verifiability result dicts. Returns a new dict:
      total              -- int, number of requirements assessed
      verifiable_count   -- int, requirements with no findings
      unverifiable_count -- int, requirements with one or more findings
      findings_by_type   -- {issue_code: count, ...}, across all results
    Input list and result dicts are not mutated."""
    total = len(results)
    verifiable_count = sum(1 for r in results if r["verifiable"])
    findings_by_type = {}
    for result in results:
        for finding in result["findings"]:
            issue = finding["issue"]
            findings_by_type[issue] = findings_by_type.get(issue, 0) + 1
    return {
        "total": total,
        "verifiable_count": verifiable_count,
        "unverifiable_count": total - verifiable_count,
        "findings_by_type": findings_by_type,
    }
