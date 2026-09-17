"""Content adequacy review of a pure tin whisker risk analysis.

Anchor: ECSS-Q-ST-60C clause 9.2 (what a risk analysis covering whisker
growth from pure tin finishes has to contain before it can be accepted).
Paraphrased into an implementable review procedure; no standard text is
reproduced.

What this module decides
------------------------
This is a review of the DELIVERABLE, not a computation of the whisker risk
itself. The question it answers is whether a submitted analysis carries the
content a reviewer needs to believe its conclusion.

1. Every pure tin item on the declared list has to be addressed. An analysis
   that reasons beautifully about nine of eleven pure tin items is not a
   complete analysis, and the shortfall is reported as a coverage fraction.
2. Each required section is graded by its state, not by its presence. A
   section that asserts a conclusion earns partial credit; one that
   substantiates it with cited evidence earns full credit; one that is
   missing earns none.
3. A section declared substantiated while citing nothing is demoted to
   asserted. The declaration is the author's, the credit is the reviewer's.
4. Mandatory sections fail the analysis outright however high the weighted
   total climbs, so a thick discussion of growth mechanism cannot buy its way
   past a missing mitigation justification.
5. The weighted total is graded against two floors, each judged at the
   boundary under a named tolerance so an analysis sitting exactly on a floor
   is not failed by float representation alone.
"""

import math

__all__ = [
    "REQUIRED_SECTIONS",
    "SECTION_STATES",
    "STATE_CREDIT",
    "MIN_EVIDENCE_REFS_FOR_SUBSTANTIATION",
    "COMPLIANT_SCORE_FLOOR",
    "ACTIONS_SCORE_FLOOR",
    "SCORE_TOLERANCE",
    "REQUIRED_ITEM_COVERAGE",
    "VERDICTS",
    "normalize_token",
    "mandatory_sections",
    "total_section_weight",
    "effective_state",
    "section_credit",
    "validate_section",
    "validate_sections",
    "item_coverage",
    "content_score",
    "missing_mandatory_sections",
    "content_verdict",
    "assess_whisker_risk_analysis",
]

# The content a clause 9.2 whisker risk analysis is expected to carry, with
# the weight each part of the argument holds and whether its absence is fatal.
REQUIRED_SECTIONS = {
    "part-and-finish-identification": {"weight": 2.0, "mandatory": True},
    "finish-composition-evidence": {"weight": 3.0, "mandatory": True},
    "whisker-growth-driver-discussion": {"weight": 2.0, "mandatory": False},
    "mission-duration-and-environment-basis": {"weight": 3.0, "mandatory": True},
    "whisker-length-bounding-basis": {"weight": 3.0, "mandatory": True},
    "bridging-geometry-and-spacing-assessment": {"weight": 3.0, "mandatory": True},
    "circuit-consequence-and-arc-evaluation": {"weight": 2.0, "mandatory": False},
    "mitigation-selection-and-justification": {"weight": 3.0, "mandatory": True},
    "residual-risk-acceptance-statement": {"weight": 2.0, "mandatory": True},
    "verification-and-surveillance-provisions": {"weight": 2.0, "mandatory": False},
}

# How far a section got, in the reviewer's vocabulary.
SECTION_STATES = ("absent", "asserted", "substantiated")

# What each state is worth against the section's weight.
STATE_CREDIT = {"absent": 0.0, "asserted": 0.5, "substantiated": 1.0}

# A substantiated section citing fewer references than this is demoted.
MIN_EVIDENCE_REFS_FOR_SUBSTANTIATION = 1

# Weighted content floors.
COMPLIANT_SCORE_FLOOR = 0.90
ACTIONS_SCORE_FLOOR = 0.60

# The score is a quotient of floats; an analysis sitting exactly on a floor
# must not be failed on representation alone.
SCORE_TOLERANCE = 1e-9

# Every pure tin item on the declared list has to be addressed.
REQUIRED_ITEM_COVERAGE = 1.0

VERDICTS = ("compliant", "compliant-with-actions", "not-compliant")


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _non_negative_int(value, label):
    """Return a whole count that may be zero but never negative."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _positive_int(value, label):
    """Return a strictly positive whole count."""
    count = _non_negative_int(value, label)
    if count == 0:
        raise ValueError("%s must be greater than zero" % label)
    return count


def _fraction(value, label):
    """Return a real value in the closed range zero to one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (label, value))
    return number


def normalize_token(value, label="token"):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def mandatory_sections():
    """Return the sections whose absence fails the analysis, sorted."""
    return sorted(k for k, v in REQUIRED_SECTIONS.items() if v["mandatory"])


def total_section_weight():
    """Return the weight every required section contributes in total."""
    return sum(v["weight"] for v in REQUIRED_SECTIONS.values())


def effective_state(state, evidence_refs):
    """Return the state the reviewer credits, not the one the author declared.

    A section declared substantiated while citing nothing is demoted to
    asserted: the claim may well be true, but the analysis does not show it.
    """
    token = normalize_token(state, "state")
    if token not in SECTION_STATES:
        raise ValueError(
            "state '%s' is not recognized; expected one of %s"
            % (token, ", ".join(SECTION_STATES))
        )
    refs = _non_negative_int(evidence_refs, "evidence_refs")
    if token == "substantiated" and refs < MIN_EVIDENCE_REFS_FOR_SUBSTANTIATION:
        return "asserted"
    return token


def section_credit(state, evidence_refs):
    """Return the credit fraction a section earns, after any demotion."""
    return STATE_CREDIT[effective_state(state, evidence_refs)]


def validate_section(section):
    """Return one validated section entry of the submitted analysis."""
    if not isinstance(section, dict):
        raise ValueError("section must be a mapping")
    for key in ("section", "state"):
        if key not in section:
            raise ValueError("section missing required key '%s'" % key)
    token = normalize_token(section["section"], "section")
    if token not in REQUIRED_SECTIONS:
        raise ValueError(
            "section '%s' is not a required clause 9.2 content item; expected "
            "one of %s" % (token, ", ".join(sorted(REQUIRED_SECTIONS)))
        )
    refs = _non_negative_int(section.get("evidence_refs", 0), "evidence_refs")
    declared = normalize_token(section["state"], "state")
    credited = effective_state(declared, refs)
    return {
        "section": token,
        "declared_state": declared,
        "state": credited,
        "demoted": credited != declared,
        "evidence_refs": refs,
        "weight": REQUIRED_SECTIONS[token]["weight"],
        "mandatory": REQUIRED_SECTIONS[token]["mandatory"],
        "credit": STATE_CREDIT[credited],
    }


def validate_sections(sections):
    """Return every required section, with anything unsubmitted marked absent.

    A section submitted twice is a defect in the submission, not something to
    silently resolve, so a duplicate raises.
    """
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a list")
    validated = {}
    for entry in sections:
        item = validate_section(entry)
        if item["section"] in validated:
            raise ValueError(
                "section '%s' submitted more than once" % item["section"]
            )
        validated[item["section"]] = item
    for token, spec in REQUIRED_SECTIONS.items():
        if token not in validated:
            validated[token] = {
                "section": token,
                "declared_state": "absent",
                "state": "absent",
                "demoted": False,
                "evidence_refs": 0,
                "weight": spec["weight"],
                "mandatory": spec["mandatory"],
                "credit": 0.0,
            }
    return validated


def item_coverage(pure_tin_item_count, items_addressed):
    """Return the fraction of declared pure tin items the analysis addresses."""
    declared = _positive_int(pure_tin_item_count, "pure_tin_item_count")
    addressed = _non_negative_int(items_addressed, "items_addressed")
    if addressed > declared:
        raise ValueError(
            "items_addressed (%d) exceeds the declared pure tin item count (%d)"
            % (addressed, declared)
        )
    return addressed / declared


def content_score(validated):
    """Return the weighted content score of a validated section mapping."""
    if not isinstance(validated, dict) or not validated:
        raise ValueError("validated sections must be a non-empty mapping")
    earned = 0.0
    available = 0.0
    for item in validated.values():
        earned += item["weight"] * item["credit"]
        available += item["weight"]
    if available <= 0.0:
        raise ValueError("required sections carry no weight")
    return earned / available


def missing_mandatory_sections(validated):
    """Return the mandatory sections that are absent, sorted."""
    if not isinstance(validated, dict):
        raise ValueError("validated sections must be a mapping")
    return sorted(
        token
        for token, item in validated.items()
        if item["mandatory"] and item["state"] == "absent"
    )


def _at_or_above(value, floor):
    """Return whether a value meets a floor, tolerant at the boundary."""
    return value > floor or math.isclose(
        value, floor, rel_tol=0.0, abs_tol=SCORE_TOLERANCE
    )


def content_verdict(score, missing, coverage):
    """Return the verdict a score, a mandatory shortfall and a coverage earn."""
    value = _fraction(score, "score")
    covered = _fraction(coverage, "coverage")
    if not isinstance(missing, (list, tuple)):
        raise ValueError("missing must be a list")
    complete = _at_or_above(covered, REQUIRED_ITEM_COVERAGE)
    if missing or not complete:
        if _at_or_above(value, ACTIONS_SCORE_FLOOR):
            return "compliant-with-actions"
        return "not-compliant"
    if _at_or_above(value, COMPLIANT_SCORE_FLOOR):
        return "compliant"
    if _at_or_above(value, ACTIONS_SCORE_FLOOR):
        return "compliant-with-actions"
    return "not-compliant"


def assess_whisker_risk_analysis(analysis):
    """Review one submitted pure tin whisker risk analysis for content.

    analysis keys: document_id, pure_tin_item_count, items_addressed and
    sections (a list of {section, state, evidence_refs} entries).
    """
    if not isinstance(analysis, dict):
        raise ValueError("analysis must be a mapping")
    for key in ("document_id", "pure_tin_item_count", "items_addressed", "sections"):
        if key not in analysis:
            raise ValueError("analysis missing required key '%s'" % key)

    document_id = _require_text(analysis["document_id"], "document_id")
    validated = validate_sections(analysis["sections"])
    coverage = item_coverage(
        analysis["pure_tin_item_count"], analysis["items_addressed"]
    )
    score = content_score(validated)
    missing = missing_mandatory_sections(validated)
    verdict = content_verdict(score, missing, coverage)

    demoted = sorted(t for t, i in validated.items() if i["demoted"])
    asserted_only = sorted(
        t for t, i in validated.items() if i["state"] == "asserted"
    )

    findings = []
    for token in missing:
        findings.append(
            "analysis '%s' omits the mandatory section '%s'" % (document_id, token)
        )
    if not _at_or_above(coverage, REQUIRED_ITEM_COVERAGE):
        findings.append(
            "analysis '%s' addresses %d of %d declared pure tin items"
            % (
                document_id,
                analysis["items_addressed"],
                analysis["pure_tin_item_count"],
            )
        )
    for token in demoted:
        findings.append(
            "section '%s' of analysis '%s' is declared substantiated but cites "
            "no evidence, so it is credited as asserted" % (token, document_id)
        )
    if verdict == "not-compliant":
        findings.append(
            "analysis '%s' scores %.3f against the %.2f floor and cannot be "
            "accepted as it stands" % (document_id, score, ACTIONS_SCORE_FLOOR)
        )

    actions = []
    for token in missing:
        actions.append("write-the-missing-section-%s" % token)
    if not _at_or_above(coverage, REQUIRED_ITEM_COVERAGE):
        actions.append("extend-the-analysis-to-every-declared-pure-tin-item")
    for token in demoted:
        actions.append("cite-evidence-for-section-%s" % token)
    if verdict != "compliant":
        for token in asserted_only:
            action = "cite-evidence-for-section-%s" % token
            if action not in actions:
                actions.append(action)

    return {
        "document_id": document_id,
        "sections": validated,
        "pure_tin_item_count": analysis["pure_tin_item_count"],
        "items_addressed": analysis["items_addressed"],
        "item_coverage": coverage,
        "content_score": score,
        "missing_mandatory": missing,
        "demoted_sections": demoted,
        "asserted_only_sections": asserted_only,
        "verdict": verdict,
        "acceptable_as_submitted": verdict == "compliant",
        "findings": findings,
        "actions": actions,
    }
