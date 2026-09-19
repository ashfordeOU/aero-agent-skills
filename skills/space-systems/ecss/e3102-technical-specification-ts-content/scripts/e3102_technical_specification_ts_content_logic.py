#!/usr/bin/env python3
"""Technical specification content for two-phase heat transport equipment.

Anchor: ECSS-E-ST-31-02 clause 5.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The technical specification is the document the equipment is bought,
built and verified against, so the clause asks two separate questions of
it. Does it cover the ground it has to cover, and is each thing it says
actually verifiable?

Coverage runs over four families of content:

    performance     what the equipment has to transport and how well
    environmental   what it has to survive while doing it
    interface       how it attaches, conducts and fits
    test-data       what evidence comes back with the hardware

Verifiability is a property of the individual requirement. A statement
with no number, no unit, no tolerance or no verification method cannot
be closed at a review, however well written it reads. A tolerance of
zero is the specific trap: it is unachievable by measurement and turns
into a waiver every time.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONTENT_CATEGORIES = ("performance", "environmental", "interface", "test-data")

VERIFICATION_METHODS = ("test", "analysis", "review-of-design", "inspection")

REQUIRED_TOPICS = {
    "performance": (
        "transported-power",
        "thermal-conductance",
        "maximum-adverse-tilt",
        "start-up-capability",
    ),
    "environmental": (
        "operating-temperature-range",
        "non-operating-temperature-range",
        "random-vibration-level",
        "radiation-environment",
    ),
    "interface": (
        "mechanical-mounting-interface",
        "thermal-contact-interface",
        "dimensional-envelope-and-mass",
        "electrical-bonding-interface",
    ),
    "test-data": (
        "acceptance-data-package-content",
        "qualification-test-report-content",
        "measurement-uncertainty-statement",
        "test-tolerance-and-conditions",
    ),
}

TS_COMPLETE = "ts-complete"
TS_INCOMPLETE = "ts-incomplete"


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (name, value))
    return tuple(value)


def all_required_topics():
    """Every mandatory topic across the four content families."""
    topics = []
    for category in CONTENT_CATEGORIES:
        for topic in REQUIRED_TOPICS[category]:
            topics.append((category, topic))
    return tuple(topics)


def validate_requirement(record):
    """Check one specification entry is a requirement at all."""
    if not isinstance(record, dict):
        raise ValueError("requirement must be a mapping, got %r" % (record,))
    _require_text("requirement id", record.get("id"))
    _require_choice("category", record.get("category"), CONTENT_CATEGORIES)
    _require_text("topic", record.get("topic"))
    return record


def assess_verifiability(record):
    """Say whether a requirement could actually be closed at a review."""
    validate_requirement(record)
    reasons = []
    value = record.get("value")
    if not _is_finite_number(value):
        reasons.append("carries no finite numeric value")
    unit = record.get("unit")
    if not isinstance(unit, str) or not unit.strip():
        reasons.append("carries no unit")
    tolerance = record.get("tolerance")
    if not _is_finite_number(tolerance):
        reasons.append("carries no numeric tolerance")
    elif tolerance < 0.0:
        reasons.append("carries a negative tolerance")
    elif tolerance == 0.0:
        reasons.append("carries a zero tolerance, which no measurement can meet")
    method = record.get("verification_method")
    if method not in VERIFICATION_METHODS:
        reasons.append(
            "names no verification method from %s" % ", ".join(VERIFICATION_METHODS)
        )
    return {
        "id": record["id"].strip(),
        "verifiable": not reasons,
        "reasons": reasons,
    }


def index_requirements(requirements):
    """Group the supplied requirements by category and topic, rejecting reuse."""
    records = _require_sequence("requirements", requirements)
    by_category = {category: {} for category in CONTENT_CATEGORIES}
    seen_ids = set()
    supplementary = []
    for record in records:
        validate_requirement(record)
        req_id = record["id"].strip()
        if req_id in seen_ids:
            raise ValueError("duplicate requirement id %r in the specification" % req_id)
        seen_ids.add(req_id)
        category = record["category"]
        topic = record["topic"].strip()
        by_category[category].setdefault(topic, []).append(record)
        if topic not in REQUIRED_TOPICS[category]:
            supplementary.append((category, topic))
    return {"by_category": by_category, "supplementary": tuple(supplementary)}


def category_coverage(requirements, category):
    """Coverage of one content family against its mandatory topics."""
    _require_choice("category", category, CONTENT_CATEGORIES)
    index = index_requirements(requirements)["by_category"][category]
    required = REQUIRED_TOPICS[category]
    covered = [topic for topic in required if topic in index]
    missing = [topic for topic in required if topic not in index]
    return {
        "category": category,
        "required": len(required),
        "covered": len(covered),
        "missing": missing,
        "complete": not missing,
        "fraction": len(covered) / float(len(required)),
    }


def coverage_report(requirements):
    """Coverage across all four families, with an overall count."""
    report = {}
    total_required = 0
    total_covered = 0
    for category in CONTENT_CATEGORIES:
        block = category_coverage(requirements, category)
        report[category] = block
        total_required += block["required"]
        total_covered += block["covered"]
    return {
        "by_category": report,
        "required": total_required,
        "covered": total_covered,
        "complete": total_covered == total_required,
        "fraction": total_covered / float(total_required),
    }


def specify_ts_content(case):
    """Full clause 5.1 content assessment with a completeness verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    _require_text("specification reference", case.get("specification"))
    requirements = _require_sequence("requirements", case.get("requirements", ()))
    if not requirements:
        raise ValueError(
            "the specification carries no requirements; there is nothing to assess"
        )
    index = index_requirements(requirements)
    coverage = coverage_report(requirements)
    findings = []
    for category in CONTENT_CATEGORIES:
        for topic in coverage["by_category"][category]["missing"]:
            findings.append("%s content is missing the topic %s" % (category, topic))
    unverifiable = []
    for record in requirements:
        verdict = assess_verifiability(record)
        if not verdict["verifiable"]:
            unverifiable.append(verdict)
            findings.append(
                "%s cannot be verified: %s"
                % (verdict["id"], "; ".join(verdict["reasons"]))
            )
    complete = coverage["complete"] and not unverifiable
    return {
        "specification": case["specification"].strip(),
        "coverage": coverage,
        "supplementary_topics": index["supplementary"],
        "unverifiable": unverifiable,
        "findings": findings,
        "verdict": TS_COMPLETE if complete else TS_INCOMPLETE,
    }
