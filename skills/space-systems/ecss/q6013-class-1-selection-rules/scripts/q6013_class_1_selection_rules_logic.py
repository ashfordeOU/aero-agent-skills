#!/usr/bin/env python3
"""Baseline rules admitting a commercial EEE part into a Class 1 design.

Anchor: ECSS-Q-ST-60-13C clause 4.2.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The framing clause says what a Class 1 selection owes. This one is the
rule set that a real candidate part is put through, and the whole point
of a rule set is that the rules are not interchangeable. Six baseline
rules are applied:

    manufacturer-quality-system      the maker holds a certified quality
                                     system, not a self-declaration
    franchised-distribution-path     the part is bought from the maker or
                                     a franchised distributor, never an
                                     open-market broker or unknown source
    flight-lot-homogeneity           the flight build draws from one
                                     wafer lot and one assembly lot
    temperature-range-envelope       the rated range envelopes the
                                     mission range with declared margin
    change-notification-agreement    the maker owes notice of a process,
                                     die or material change
    qualification-heritage-or-plan   either relevant qualification
                                     heritage exists, or an evaluation
                                     plan covers its absence

Two rules carry the decisions most often got wrong.

The distribution path is a hard rule, not a preference. A part from an
open-market broker has no chain of custody back to the maker, so every
other rule below it is being applied to a claim rather than a part; the
correct response is to refuse the part, not to write a finding and
proceed.

The heritage rule is the only one that is genuinely conditional. A part
with no qualification heritage is not barred; it is admitted subject to
the evaluation that replaces the heritage, which is a different verdict
from a clean admission and has to be reported as one. A tool that
returns a plain pass there loses the evaluation the project has just
committed to.

The temperature rule is arithmetic, and the arithmetic sits on a
boundary more often than it looks: a commercial part rated to the same
industrial range the mission declares gives a margin of exactly zero,
which is a pass against a zero declared margin and must not be turned
into a failure by the last bit of a subtraction.

The rule set, the accepted distribution paths, the margin and the
lot-count limit below are declared project policy, not physical
constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SELECTION_RULES = (
    "manufacturer-quality-system",
    "franchised-distribution-path",
    "flight-lot-homogeneity",
    "temperature-range-envelope",
    "change-notification-agreement",
    "qualification-heritage-or-plan",
)

HARD_RULES = (
    "manufacturer-quality-system",
    "franchised-distribution-path",
    "flight-lot-homogeneity",
    "temperature-range-envelope",
    "change-notification-agreement",
)

CONDITIONAL_RULES = ("qualification-heritage-or-plan",)

QUALITY_SYSTEM_STATES = ("certified", "self-declared", "none")
ACCEPTED_QUALITY_SYSTEMS = ("certified",)

DISTRIBUTION_PATHS = (
    "manufacturer-direct",
    "franchised-distributor",
    "open-market-broker",
    "unknown-source",
)
ACCEPTED_DISTRIBUTION_PATHS = ("manufacturer-direct", "franchised-distributor")

PART_ADMISSIBLE = "part-admissible"
PART_ADMISSIBLE_WITH_EVALUATION = "part-admissible-with-evaluation"
PART_NOT_ADMISSIBLE = "part-not-admissible"

PART_RANK = {
    PART_NOT_ADMISSIBLE: 0,
    PART_ADMISSIBLE_WITH_EVALUATION: 1,
    PART_ADMISSIBLE: 2,
}

DESIGN_ADMISSIBLE = "design-part-set-admissible"
DESIGN_NOT_ADMISSIBLE = "design-part-set-not-admissible"

DEFAULT_RULE_POLICY = {
    "min_temperature_margin_k": 0.0,
    "max_flight_lots": 1,
    "accept_evaluation_for_heritage": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_number(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_count(name, value, minimum=1):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A temperature margin is a difference of two declared limits, so a
    part rated exactly to the mission range can evaluate a unit in the
    last place below a zero declared margin. The comparison absorbs
    that; the declared margin is untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_RULE_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    margin = _require_number(
        "min_temperature_margin_k", settings.get("min_temperature_margin_k")
    )
    if margin < 0.0:
        raise ValueError(
            "min_temperature_margin_k must not be negative, got %r" % (margin,)
        )
    settings["min_temperature_margin_k"] = margin
    settings["max_flight_lots"] = _require_count(
        "max_flight_lots", settings.get("max_flight_lots")
    )
    _require_flag(
        "accept_evaluation_for_heritage",
        settings.get("accept_evaluation_for_heritage"),
    )
    return settings


def validate_range(name, span):
    """Check a temperature span is an ordered pair of finite limits."""
    if not isinstance(span, (list, tuple)) or len(span) != 2:
        raise ValueError("%s must be a two-element (min, max) span, got %r" % (name, span))
    low = _require_number("%s minimum" % name, span[0])
    high = _require_number("%s maximum" % name, span[1])
    if not high > low:
        raise ValueError(
            "%s maximum must sit above its minimum, got %r" % (name, span)
        )
    return (low, high)


def temperature_envelope(rated_range, mission_range, min_margin_k=0.0):
    """Measure how far a rated range envelopes a mission range, in kelvin."""
    rated = validate_range("rated_temperature_range", rated_range)
    mission = validate_range("mission_temperature_range", mission_range)
    margin = _require_number("min_margin_k", min_margin_k)
    if margin < 0.0:
        raise ValueError("min_margin_k must not be negative, got %r" % (margin,))

    cold_margin = mission[0] - rated[0]
    hot_margin = rated[1] - mission[1]
    worst = min(cold_margin, hot_margin)
    envelopes = _at_least(cold_margin, margin) and _at_least(hot_margin, margin)

    findings = []
    if not _at_least(cold_margin, margin):
        findings.append(
            "cold end short by %.4g K against a declared %.4g K margin"
            % (margin - cold_margin, margin)
        )
    if not _at_least(hot_margin, margin):
        findings.append(
            "hot end short by %.4g K against a declared %.4g K margin"
            % (margin - hot_margin, margin)
        )
    return {
        "rated_range": rated,
        "mission_range": mission,
        "cold_margin_k": cold_margin,
        "hot_margin_k": hot_margin,
        "worst_margin_k": worst,
        "envelopes": envelopes,
        "findings": findings,
    }


def validate_part(part):
    """Check one candidate part declares every input the rules read."""
    _require_mapping("part", part)
    cleaned = {
        "part_id": _require_label("part_id", part.get("part_id")),
        "quality_system": _require_choice(
            "quality_system", part.get("quality_system"), QUALITY_SYSTEM_STATES
        ),
        "distribution_path": _require_choice(
            "distribution_path", part.get("distribution_path"), DISTRIBUTION_PATHS
        ),
        "wafer_lots": _require_count("wafer_lots", part.get("wafer_lots")),
        "assembly_lots": _require_count("assembly_lots", part.get("assembly_lots")),
        "rated_temperature_range": validate_range(
            "rated_temperature_range", part.get("rated_temperature_range")
        ),
        "mission_temperature_range": validate_range(
            "mission_temperature_range", part.get("mission_temperature_range")
        ),
        "change_notification_agreement": _require_flag(
            "change_notification_agreement",
            part.get("change_notification_agreement"),
        ),
        "qualification_heritage": _require_flag(
            "qualification_heritage", part.get("qualification_heritage")
        ),
        "evaluation_plan": _require_flag(
            "evaluation_plan", part.get("evaluation_plan")
        ),
    }
    return cleaned


def apply_selection_rules(part, policy=None):
    """Apply the six baseline rules to one candidate part."""
    settings = resolve_policy(policy)
    record = validate_part(part)
    envelope = temperature_envelope(
        record["rated_temperature_range"],
        record["mission_temperature_range"],
        settings["min_temperature_margin_k"],
    )

    results = []

    quality_ok = record["quality_system"] in ACCEPTED_QUALITY_SYSTEMS
    results.append(
        {
            "rule": "manufacturer-quality-system",
            "satisfied": quality_ok,
            "hard": True,
            "finding": ""
            if quality_ok
            else "the maker offers a %s quality system, not a certified one"
            % record["quality_system"],
        }
    )

    path_ok = record["distribution_path"] in ACCEPTED_DISTRIBUTION_PATHS
    results.append(
        {
            "rule": "franchised-distribution-path",
            "satisfied": path_ok,
            "hard": True,
            "finding": ""
            if path_ok
            else "bought through %s, so nothing below this rule is being "
            "applied to a part with a chain of custody"
            % record["distribution_path"],
        }
    )

    lots_ok = (
        record["wafer_lots"] <= settings["max_flight_lots"]
        and record["assembly_lots"] <= settings["max_flight_lots"]
    )
    results.append(
        {
            "rule": "flight-lot-homogeneity",
            "satisfied": lots_ok,
            "hard": True,
            "finding": ""
            if lots_ok
            else "the flight build draws %d wafer lot(s) and %d assembly lot(s) "
            "against a declared limit of %d"
            % (
                record["wafer_lots"],
                record["assembly_lots"],
                settings["max_flight_lots"],
            ),
        }
    )

    results.append(
        {
            "rule": "temperature-range-envelope",
            "satisfied": envelope["envelopes"],
            "hard": True,
            "finding": "; ".join(envelope["findings"]),
        }
    )

    pcn_ok = record["change_notification_agreement"]
    results.append(
        {
            "rule": "change-notification-agreement",
            "satisfied": pcn_ok,
            "hard": True,
            "finding": ""
            if pcn_ok
            else "no change-notification agreement, so a die, process or "
            "material change reaches the build unannounced",
        }
    )

    heritage_ok = record["qualification_heritage"]
    covered_by_plan = (
        record["evaluation_plan"] and settings["accept_evaluation_for_heritage"]
    )
    results.append(
        {
            "rule": "qualification-heritage-or-plan",
            "satisfied": heritage_ok or covered_by_plan,
            "hard": False,
            "finding": ""
            if heritage_ok or covered_by_plan
            else "no qualification heritage and no evaluation plan to replace it",
        }
    )

    failed_hard = [r["rule"] for r in results if r["hard"] and not r["satisfied"]]
    failed_soft = [
        r["rule"] for r in results if not r["hard"] and not r["satisfied"]
    ]
    if failed_hard or failed_soft:
        verdict = PART_NOT_ADMISSIBLE
    elif not heritage_ok and covered_by_plan:
        verdict = PART_ADMISSIBLE_WITH_EVALUATION
    else:
        verdict = PART_ADMISSIBLE

    findings = [
        "%s: %s" % (record["part_id"], r["finding"]) for r in results if r["finding"]
    ]
    if verdict == PART_ADMISSIBLE_WITH_EVALUATION:
        findings.append(
            "%s: admitted on an evaluation plan rather than heritage; the "
            "evaluation is now a committed activity" % record["part_id"]
        )
    return {
        "part_id": record["part_id"],
        "rules": results,
        "failed_rules": failed_hard + failed_soft,
        "temperature": envelope,
        "verdict": verdict,
        "findings": findings,
    }


def assess_design_part_set(case):
    """Full clause 4.2.2.1 roll-up over every candidate in one design."""
    _require_mapping("case", case)
    design_id = _require_label("design_id", case.get("design_id"))
    parts = case.get("parts")
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("case must carry a non-empty parts sequence")
    settings = resolve_policy(case.get("policy"))

    seen = set()
    for part in parts:
        part_id = validate_part(part)["part_id"]
        if part_id in seen:
            raise ValueError("part %r appears twice in one design" % part_id)
        seen.add(part_id)

    assessments = [apply_selection_rules(p, settings) for p in parts]
    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])

    grouped = {}
    for assessment in assessments:
        grouped.setdefault(assessment["verdict"], []).append(assessment["part_id"])
    for names in grouped.values():
        names.sort()

    evaluations_owed = sorted(grouped.get(PART_ADMISSIBLE_WITH_EVALUATION, []))
    weakest = min(
        assessments, key=lambda a: (PART_RANK[a["verdict"]], a["part_id"])
    )
    verdict = (
        DESIGN_NOT_ADMISSIBLE
        if PART_NOT_ADMISSIBLE in grouped
        else DESIGN_ADMISSIBLE
    )
    return {
        "design_id": design_id,
        "parts": assessments,
        "grouped_parts": grouped,
        "evaluations_owed": evaluations_owed,
        "weakest_part": weakest["part_id"],
        "verdict": verdict,
        "findings": findings,
    }
