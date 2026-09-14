#!/usr/bin/env python3
"""Order of coverglass acceptance testing, on both populations.

Anchor: ECSS-E-ST-20-08C clause 8.5.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Acceptance testing of coverglasses is run in a fixed order, and that
order is applied to two populations rather than one: the coverglasses
being delivered, and the coverglasses the qualification campaign
consumes. The second population is the one that gets dropped, because
qualification hardware is not being shipped and the acceptance sequence
looks like somebody else's obligation. It is the reverse -- a
qualification result only carries meaning if the pieces it was produced
on went through the same acceptance order the delivered pieces did.

Order is not decoration. A coverglass acceptance run mixes observations
that leave the piece as it was with steps that can mark, load or coat
it, so a step taken out of order silently changes what the later steps
are measuring. Two different deviations are therefore graded apart:

    inversion       two activities that appear in the opposite order to
                    the baseline; graded in aggregate as a conformance
                    fraction, because a sequence can drift a little
    precedence      a declared pair that must hold whatever else moves,
                    such as an observation that has to be taken before
                    any step that can alter the piece; a single one is
                    a defect on its own

Coverage is kept apart from order. A sequence missing an activity has
not merely been reordered, and an invented activity is refused rather
than counted as coverage, because an extra step in an acceptance run is
a change to the article's history that nobody agreed to.

The baseline order, the precedence pairs and the conformance floor
below are declared project policy, not physical constants; a project
may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

POPULATIONS = ("delivery", "qualification")

BASELINE_SEQUENCE = (
    "coverglass-lot-sample-draw",
    "coverglass-dimensional-measurement",
    "coverglass-visual-inspection",
    "coverglass-optical-transmission-measurement",
    "coverglass-surface-conductivity-measurement",
    "coverglass-environmental-exposure",
    "coverglass-post-exposure-visual-inspection",
)

BASELINE_INDEX = {name: index for index, name in enumerate(BASELINE_SEQUENCE)}

PRECEDENCE_PAIRS = (
    ("coverglass-lot-sample-draw", "coverglass-dimensional-measurement"),
    ("coverglass-visual-inspection", "coverglass-environmental-exposure"),
    (
        "coverglass-optical-transmission-measurement",
        "coverglass-environmental-exposure",
    ),
    (
        "coverglass-environmental-exposure",
        "coverglass-post-exposure-visual-inspection",
    ),
)

SEQUENCE_ABSENT = "coverglass-sequence-absent"
SEQUENCE_INCOMPLETE = "coverglass-sequence-incomplete"
SEQUENCE_PRECEDENCE_BROKEN = "coverglass-sequence-precedence-broken"
SEQUENCE_REORDERED = "coverglass-sequence-reordered"
SEQUENCE_CONFORMING = "coverglass-sequence-conforming"

SEQUENCE_RANK = {
    SEQUENCE_ABSENT: 0,
    SEQUENCE_INCOMPLETE: 1,
    SEQUENCE_PRECEDENCE_BROKEN: 2,
    SEQUENCE_REORDERED: 3,
    SEQUENCE_CONFORMING: 4,
}

CAMPAIGN_CONFORMING = "coverglass-acceptance-order-conforming"
CAMPAIGN_NOT_CONFORMING = "coverglass-acceptance-order-not-conforming"

DEFAULT_SEQUENCE_POLICY = {
    "min_order_conformance": 1.0,
    "min_activity_coverage": 1.0,
    "carry_precedence_break": False,
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


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if not 0.0 <= value <= 1.0:
        raise ValueError(
            "%s must sit between zero and one inclusive, got %r" % (name, value)
        )
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Conformance and coverage are both quotients of two activity counts,
    so a sequence sitting exactly on its declared floor can evaluate a
    unit in the last place below it. The comparison absorbs that; the
    declared floor is untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_sequence_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_SEQUENCE_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    _require_fraction("min_order_conformance", settings.get("min_order_conformance"))
    _require_fraction("min_activity_coverage", settings.get("min_activity_coverage"))
    _require_flag("carry_precedence_break", settings.get("carry_precedence_break"))
    return settings


def validate_sequence_record(entry):
    """Check one declared sequence names a population and known steps."""
    _require_mapping("sequence entry", entry)
    population = _require_choice("population", entry.get("population"), POPULATIONS)
    steps = entry.get("steps")
    if steps is None:
        steps = []
    if not isinstance(steps, (list, tuple)):
        raise ValueError("steps must be a sequence, got %r" % (steps,))

    seen = set()
    cleaned = []
    for step in steps:
        name = _require_label("step", step)
        if name not in BASELINE_INDEX:
            raise ValueError(
                "step %r is not an acceptance activity this clause orders; an "
                "invented step is a change to the article history, not coverage"
                % name
            )
        if name in seen:
            raise ValueError("step %r appears twice in one sequence" % name)
        seen.add(name)
        cleaned.append(name)
    return {"population": population, "steps": cleaned}


def activity_coverage(steps):
    """Split the baseline activity set into reached and missing."""
    present = [name for name in BASELINE_SEQUENCE if name in steps]
    missing = [name for name in BASELINE_SEQUENCE if name not in steps]
    coverage = len(present) / len(BASELINE_SEQUENCE)
    return {
        "present": present,
        "missing": missing,
        "coverage": coverage,
    }


def order_inversions(steps):
    """Count pairs of declared steps sitting in the reverse baseline order.

    The count is reduced to a conformance fraction against the number of
    pairs the sequence holds, so a long run that slipped one step apart
    is not scored the same as a run reversed end to end.
    """
    ordered = [BASELINE_INDEX[name] for name in steps]
    pairs = 0
    inversions = 0
    inverted = []
    for left in range(len(ordered)):
        for right in range(left + 1, len(ordered)):
            pairs += 1
            if ordered[left] > ordered[right]:
                inversions += 1
                inverted.append((steps[left], steps[right]))
    conformance = 1.0 if pairs == 0 else 1.0 - (inversions / pairs)
    return {
        "pairs": pairs,
        "inversions": inversions,
        "inverted_pairs": inverted,
        "conformance": conformance,
    }


def precedence_violations(steps):
    """Find declared pairs whose required order the sequence broke."""
    position = {name: index for index, name in enumerate(steps)}
    broken = []
    for before, after in PRECEDENCE_PAIRS:
        if before in position and after in position:
            if position[before] > position[after]:
                broken.append((before, after))
    return broken


def assess_population_sequence(entry, policy=None):
    """Grade one population's declared acceptance order."""
    settings = resolve_sequence_policy(policy)
    record = validate_sequence_record(entry)
    steps = record["steps"]
    population = record["population"]

    coverage = activity_coverage(steps)
    order = order_inversions(steps)
    broken = precedence_violations(steps)

    meets_coverage = _at_least(coverage["coverage"], settings["min_activity_coverage"])
    meets_order = _at_least(order["conformance"], settings["min_order_conformance"])

    findings = []
    if not steps:
        findings.append(
            "%s population: no acceptance order is declared at all, so the "
            "population has not been sequenced rather than sequenced badly"
            % population
        )
    else:
        if coverage["missing"] and not meets_coverage:
            findings.append(
                "%s population: the declared order omits %s"
                % (population, ", ".join(coverage["missing"]))
            )
        for before, after in broken:
            findings.append(
                "%s population: %s is run after %s, and that pair has to hold "
                "whatever else moves" % (population, before, after)
            )
        if not meets_order:
            findings.append(
                "%s population: %d of %d activity pairs sit in the reverse "
                "order, giving %.4g conformance against a declared floor of %.4g"
                % (
                    population,
                    order["inversions"],
                    order["pairs"],
                    order["conformance"],
                    settings["min_order_conformance"],
                )
            )

    if not steps:
        verdict = SEQUENCE_ABSENT
    elif not meets_coverage:
        verdict = SEQUENCE_INCOMPLETE
    elif broken and not settings["carry_precedence_break"]:
        verdict = SEQUENCE_PRECEDENCE_BROKEN
    elif not meets_order:
        verdict = SEQUENCE_REORDERED
    else:
        verdict = SEQUENCE_CONFORMING
    return {
        "population": population,
        "steps": steps,
        "coverage": coverage,
        "order": order,
        "precedence_broken": broken,
        "meets_coverage": meets_coverage,
        "meets_order": meets_order,
        "verdict": verdict,
        "findings": findings,
    }


def assess_acceptance_sequence(case):
    """Full clause 8.5.2 roll-up over both coverglass populations."""
    _require_mapping("case", case)
    campaign_id = _require_label("campaign_id", case.get("campaign_id"))
    sequences = case.get("sequences")
    if not isinstance(sequences, (list, tuple)) or not sequences:
        raise ValueError("case must carry a non-empty sequences list")
    settings = resolve_sequence_policy(case.get("policy"))

    assessed = {}
    for entry in sequences:
        assessment = assess_population_sequence(entry, settings)
        population = assessment["population"]
        if population in assessed:
            raise ValueError(
                "population %r declares two acceptance orders" % population
            )
        assessed[population] = assessment

    findings = []
    for population in POPULATIONS:
        if population in assessed:
            findings.extend(assessed[population]["findings"])

    missing_populations = [p for p in POPULATIONS if p not in assessed]
    for population in missing_populations:
        findings.append(
            "the campaign declares no acceptance order for the %s population, "
            "so the clause cannot be shown reached on it" % population
        )

    grouped = {}
    for population in POPULATIONS:
        if population in assessed:
            grouped.setdefault(assessed[population]["verdict"], []).append(population)
    for names in grouped.values():
        names.sort()

    if assessed:
        weakest = min(
            assessed.values(),
            key=lambda a: (SEQUENCE_RANK[a["verdict"]], a["population"]),
        )
        weakest_population = weakest["population"]
    else:
        weakest_population = None

    conforming = [
        a for a in assessed.values() if a["verdict"] == SEQUENCE_CONFORMING
    ]
    if missing_populations or len(conforming) != len(POPULATIONS):
        verdict = CAMPAIGN_NOT_CONFORMING
    else:
        verdict = CAMPAIGN_CONFORMING
    return {
        "campaign_id": campaign_id,
        "populations": assessed,
        "grouped_populations": grouped,
        "missing_populations": missing_populations,
        "weakest_population": weakest_population,
        "verdict": verdict,
        "findings": findings,
    }
