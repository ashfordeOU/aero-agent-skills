#!/usr/bin/env python3
"""Qualification test programme for an ECSS thermal test.

Anchor: ECSS-Q-ST-70-04C, the method variant that qualifies rather than
screens. The procedure below is a paraphrase into implementable steps; no
standard text is reproduced.

A qualification programme is a ladder of test article levels, not a single
run. Coupons answer the material question, subassemblies answer the joint
and interface question, and equipment answers the question the coupons
cannot: whether the thing that flies survives. A ladder with a rung
missing looks complete on paper and has a gap exactly where the failures
live.

Two numbers compete for the cycle count at each level. The level table
carries a floor, and the acceptance programme carries a multiple of its
own cycles; the qualification count is whichever is larger, and which one
governed is a reportable fact. A level governed by the acceptance
multiple moves whenever the acceptance programme moves.

A level may be waived only where the policy allows a waiver and only
against a named heritage reference. A waiver without a reference is a
skipped rung.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

COUPON = "coupon"
SUBASSEMBLY = "subassembly"
EQUIPMENT = "equipment"
TEST_ARTICLE_LEVELS = (COUPON, SUBASSEMBLY, EQUIPMENT)

LEVEL_TABLE = "level-table"
ACCEPTANCE_MULTIPLE = "acceptance-multiple"

DEFAULT_QUALIFICATION_POLICY = {
    "level_cycles": {COUPON: 200, SUBASSEMBLY: 100, EQUIPMENT: 50},
    "level_articles": {COUPON: 6, SUBASSEMBLY: 3, EQUIPMENT: 2},
    "qualification_factor": 2,
    "min_cycles": 25,
    "min_articles": 1,
    "max_articles_per_run": 4,
    "waivable_levels": (COUPON,),
}

def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_positive_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(
            "%s must be an integer of at least 1, got %r" % (name, value)
        )
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _ceil_div(numerator, denominator):
    """Integer ceiling division; no float rounding anywhere near it."""
    return -(-numerator // denominator)


def validate_qualification_policy(policy):
    """Check the level tables are complete and the factor is a whole multiple."""
    _require_mapping("policy", policy)
    cycles = _require_mapping("policy level_cycles", policy.get("level_cycles"))
    articles = _require_mapping("policy level_articles", policy.get("level_articles"))
    for table_name, table in (("level_cycles", cycles), ("level_articles", articles)):
        missing = set(TEST_ARTICLE_LEVELS) - set(table)
        if missing:
            raise ValueError(
                "policy %s is missing: %s" % (table_name, ", ".join(sorted(missing)))
            )
        for level in TEST_ARTICLE_LEVELS:
            _require_positive_int("%s[%s]" % (table_name, level), table[level])
    factor = _require_positive_int(
        "qualification_factor", policy.get("qualification_factor")
    )
    if factor < 2:
        raise ValueError(
            "qualification_factor %d does not exceed the acceptance programme; a "
            "qualification run has to demand more than acceptance does" % factor
        )
    min_cycles = _require_positive_int("min_cycles", policy.get("min_cycles"))
    _require_positive_int("min_articles", policy.get("min_articles"))
    _require_positive_int("max_articles_per_run", policy.get("max_articles_per_run"))
    for level in TEST_ARTICLE_LEVELS:
        if cycles[level] < min_cycles:
            raise ValueError(
                "level_cycles[%s] is %d, below the qualification floor of %d"
                % (level, cycles[level], min_cycles)
            )
    waivable = policy.get("waivable_levels")
    if not isinstance(waivable, (list, tuple)):
        raise ValueError("waivable_levels must be a sequence, got %r" % (waivable,))
    for level in waivable:
        _require_choice("waivable level", level, TEST_ARTICLE_LEVELS)
    if EQUIPMENT in waivable:
        raise ValueError(
            "the equipment level cannot be waivable; nothing below it answers "
            "whether the flight configuration survives"
        )
    return policy


def level_ladder(highest_level, policy=DEFAULT_QUALIFICATION_POLICY):
    """Every level from the coupon up to the highest article being qualified."""
    validate_qualification_policy(policy)
    _require_choice("highest_level", highest_level, TEST_ARTICLE_LEVELS)
    top = TEST_ARTICLE_LEVELS.index(highest_level)
    return TEST_ARTICLE_LEVELS[: top + 1]


def resolve_waivers(ladder, waivers, policy=DEFAULT_QUALIFICATION_POLICY):
    """Drop waived levels from the ladder, refusing an unsupported waiver."""
    validate_qualification_policy(policy)
    if not isinstance(waivers, dict):
        raise ValueError("waivers must be a mapping of level to reference")
    kept = []
    dropped = []
    for level in ladder:
        if level not in waivers:
            kept.append(level)
            continue
        if level not in tuple(policy["waivable_levels"]):
            raise ValueError(
                "the %s level is not waivable; a ladder cannot skip it" % level
            )
        reference = waivers[level]
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError(
                "the %s waiver needs a named heritage reference, got %r"
                % (level, reference)
            )
        dropped.append({"level": level, "reference": reference.strip()})
    if not kept:
        raise ValueError("every level was waived; there is no programme left to run")
    return {"levels": tuple(kept), "waived": dropped}


def qualification_cycles(level, acceptance_cycles, policy=DEFAULT_QUALIFICATION_POLICY):
    """Cycles a level qualifies on: the larger of its floor and the multiple."""
    validate_qualification_policy(policy)
    _require_choice("level", level, TEST_ARTICLE_LEVELS)
    acceptance = _require_positive_int("acceptance_cycles", acceptance_cycles)
    derived = acceptance * policy["qualification_factor"]
    floor = policy["level_cycles"][level]
    if derived > floor:
        return {"cycles": derived, "governed_by": ACCEPTANCE_MULTIPLE}
    return {"cycles": floor, "governed_by": LEVEL_TABLE}


def level_article_count(level, policy=DEFAULT_QUALIFICATION_POLICY):
    """Articles the level is qualified on."""
    validate_qualification_policy(policy)
    _require_choice("level", level, TEST_ARTICLE_LEVELS)
    return policy["level_articles"][level]


def level_run_count(article_count, policy=DEFAULT_QUALIFICATION_POLICY):
    """Chamber loads needed for the articles at one level."""
    validate_qualification_policy(policy)
    count = _require_positive_int("article_count", article_count)
    return _ceil_div(count, policy["max_articles_per_run"])


def level_duration_s(cycle_count, cycle_duration_s, run_count):
    """Chamber time for one level."""
    cycles = _require_positive_int("cycle_count", cycle_count)
    duration = _require_positive("cycle_duration_s", cycle_duration_s)
    runs = _require_positive_int("run_count", run_count)
    return cycles * duration * runs


def plan_qualification_programme(case, policy=DEFAULT_QUALIFICATION_POLICY):
    """Full qualification programme across the surviving test article levels."""
    validate_qualification_policy(policy)
    _require_mapping("case", case)
    item = case.get("item_id")
    if not isinstance(item, str) or not item.strip():
        raise ValueError("case item_id must be a non-empty string")
    ladder = level_ladder(case.get("highest_level"), policy)
    resolution = resolve_waivers(ladder, case.get("waivers", {}), policy)
    acceptance = _require_positive_int(
        "acceptance_cycles", case.get("acceptance_cycles")
    )
    cycle_duration = _require_positive(
        "cycle_duration_s", case.get("cycle_duration_s")
    )
    declared_articles = case.get("articles", {})
    if not isinstance(declared_articles, dict):
        raise ValueError("case articles must be a mapping of level to count")
    for level in declared_articles:
        _require_choice("declared article level", level, TEST_ARTICLE_LEVELS)

    levels = []
    findings = []
    duties = []
    total_duration = 0.0
    total_articles = 0
    for level in resolution["levels"]:
        cycles = qualification_cycles(level, acceptance, policy)
        policy_articles = level_article_count(level, policy)
        if level in declared_articles:
            articles = _require_positive_int(
                "articles[%s]" % level, declared_articles[level]
            )
            source = "declared"
        else:
            articles = policy_articles
            source = "policy"
        runs = level_run_count(articles, policy)
        duration = level_duration_s(cycles["cycles"], cycle_duration, runs)
        total_duration += duration
        total_articles += articles
        levels.append(
            {
                "level": level,
                "cycle_count": cycles["cycles"],
                "governed_by": cycles["governed_by"],
                "article_count": articles,
                "article_source": source,
                "run_count": runs,
                "duration_s": duration,
            }
        )
        if cycles["governed_by"] == ACCEPTANCE_MULTIPLE:
            findings.append(
                "%s qualifies on %d cycles because the acceptance programme times "
                "%d exceeds the level floor of %d; this count moves whenever "
                "acceptance moves"
                % (
                    level,
                    cycles["cycles"],
                    policy["qualification_factor"],
                    policy["level_cycles"][level],
                )
            )
        if source == "declared" and articles < policy_articles:
            findings.append(
                "%s runs %d articles where the policy calls for %d; the level is "
                "thinner than the programme it is written as"
                % (level, articles, policy_articles)
            )

    for waiver in resolution["waived"]:
        findings.append(
            "the %s level is waived against %s; the waiver, not a test, carries "
            "that rung" % (waiver["level"], waiver["reference"])
        )
    if EQUIPMENT not in resolution["levels"]:
        findings.append(
            "no equipment-level article is qualified, so nothing in this programme "
            "demonstrates the flight configuration itself"
        )
    duties.append(
        "keep the qualification articles out of the flight build; they have spent "
        "their life in the chamber"
    )
    duties.append(
        "re-derive every level governed by the acceptance multiple whenever the "
        "acceptance programme changes"
    )

    return {
        "item_id": item,
        "ladder": ladder,
        "levels": levels,
        "level_count": len(levels),
        "waived": resolution["waived"],
        "acceptance_cycles": acceptance,
        "total_article_count": total_articles,
        "programme_duration_s": total_duration,
        "findings": findings,
        "duties": duties,
    }
