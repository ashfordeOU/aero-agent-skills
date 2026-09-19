#!/usr/bin/env python3
"""Qualification test programme for a threaded fastener type.

Anchor: ECSS-Q-ST-70-46 testing clause on threaded fasteners. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

A fastener type is qualified by mechanical-property evidence drawn from
real production lots. What it owes depends on the criticality it is
used at:

fracture-critical  the full mechanical set plus microstructure and
                   stress-rupture evidence, with the largest specimen
                   counts, because a failure has no redundancy behind
                   it.
structural         the load-carrying subset with moderate counts.
non-structural     tensile, proof and hardness only.

Tests split by what they are sensitive to. Lot-sensitive tests move
with the heat treatment and plating of the individual lot, so they are
drawn from every lot of every size variant. Variant-driven tests are
geometry- and process-driven, so one set per size variant answers for
every lot of that variant.

A change to the type does not reopen the whole programme: the
re-qualification scope is the intersection of the tests the change can
move with the tests the category already owed.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

CRITICALITY_CATEGORIES = ("fracture-critical", "structural", "non-structural")

TEST_TENSILE = "tensile-strength"
TEST_PROOF = "proof-load"
TEST_HARDNESS = "hardness"
TEST_MICROSTRUCTURE = "microstructure-and-decarburization"
TEST_COATING = "coating-thickness-and-adhesion"
TEST_SHEAR = "shear-strength"
TEST_FATIGUE = "axial-fatigue"
TEST_TORQUE_TENSION = "torque-tension"
TEST_CORROSION = "corrosion-resistance"
TEST_STRESS_RUPTURE = "stress-rupture-embrittlement"

#: Tests whose result belongs to the production lot it was drawn from.
LOT_SENSITIVE_TESTS = (
    TEST_TENSILE,
    TEST_PROOF,
    TEST_HARDNESS,
    TEST_MICROSTRUCTURE,
    TEST_COATING,
)

VERDICT_COMPLETE = "qualification-complete"
VERDICT_INCOMPLETE = "qualification-incomplete"
VERDICT_REQUALIFICATION_OPEN = "requalification-outstanding"

_CATEGORY_RULES = {
    "fracture-critical": {
        "specimens": {
            TEST_TENSILE: 6,
            TEST_PROOF: 6,
            TEST_HARDNESS: 5,
            TEST_MICROSTRUCTURE: 3,
            TEST_COATING: 5,
            TEST_SHEAR: 5,
            TEST_FATIGUE: 8,
            TEST_TORQUE_TENSION: 5,
            TEST_CORROSION: 3,
            TEST_STRESS_RUPTURE: 4,
        },
        "min_lots": 3,
        "min_variants": 1,
    },
    "structural": {
        "specimens": {
            TEST_TENSILE: 5,
            TEST_PROOF: 5,
            TEST_HARDNESS: 3,
            TEST_COATING: 3,
            TEST_SHEAR: 3,
            TEST_TORQUE_TENSION: 3,
            TEST_CORROSION: 3,
        },
        "min_lots": 2,
        "min_variants": 1,
    },
    "non-structural": {
        "specimens": {
            TEST_TENSILE: 3,
            TEST_PROOF: 3,
            TEST_HARDNESS: 3,
        },
        "min_lots": 1,
        "min_variants": 1,
    },
}

#: Tests a declared change can move, before intersecting with the set
#: the criticality category actually owes.
_CHANGE_IMPACT = {
    "material-batch": (TEST_TENSILE, TEST_HARDNESS, TEST_MICROSTRUCTURE),
    "material-grade": tuple(_CATEGORY_RULES["fracture-critical"]["specimens"]),
    "heat-treatment": (
        TEST_TENSILE,
        TEST_PROOF,
        TEST_HARDNESS,
        TEST_MICROSTRUCTURE,
        TEST_STRESS_RUPTURE,
    ),
    "coating-process": (
        TEST_COATING,
        TEST_CORROSION,
        TEST_TORQUE_TENSION,
        TEST_STRESS_RUPTURE,
    ),
    "thread-forming-method": (
        TEST_TENSILE,
        TEST_FATIGUE,
        TEST_MICROSTRUCTURE,
    ),
    "manufacturing-source": tuple(_CATEGORY_RULES["fracture-critical"]["specimens"]),
    "size-within-family": (TEST_TENSILE, TEST_PROOF, TEST_SHEAR),
}

CHANGE_TYPES = tuple(sorted(_CHANGE_IMPACT))


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def criticality_rules(category):
    """Specimen counts and lot/variant minima owed by one category."""
    _require_choice("category", category, CRITICALITY_CATEGORIES)
    rules = _CATEGORY_RULES[category]
    return {
        "category": category,
        "specimens": dict(rules["specimens"]),
        "min_lots": rules["min_lots"],
        "min_variants": rules["min_variants"],
    }


def required_tests(category):
    """Qualification tests the category owes, in a stable order."""
    return list(criticality_rules(category)["specimens"])


def specimens_per_test(category, test):
    """Specimens one test takes, per lot or per variant as it applies."""
    counts = criticality_rules(category)["specimens"]
    if test not in counts:
        raise ValueError(
            "%s is not a qualification test of the %s category" % (test, category)
        )
    return counts[test]


def is_lot_sensitive(test):
    """True when the result belongs to the lot the specimen came from."""
    if not isinstance(test, str) or not test:
        raise ValueError("test must be a non-empty name, got %r" % (test,))
    return test in LOT_SENSITIVE_TESTS


def allocate_specimens(category, lot_count, variant_count):
    """Specimens owed per test across the lots and variants on offer.

    A lot-sensitive test is drawn from every lot of every variant; a
    variant-driven test is drawn once per variant.
    """
    lots = _require_count("lot_count", lot_count, minimum=1)
    variants = _require_count("variant_count", variant_count, minimum=1)
    rules = criticality_rules(category)
    allocation = {}
    for test, per_draw in rules["specimens"].items():
        multiplier = lots * variants if is_lot_sensitive(test) else variants
        allocation[test] = per_draw * multiplier
    return allocation


def programme_total(category, lot_count, variant_count):
    """Total specimen count the whole programme consumes."""
    return sum(allocate_specimens(category, lot_count, variant_count).values())


def coverage_findings(category, lot_count, variant_count):
    """Findings on a lot or variant spread too thin for the category."""
    rules = criticality_rules(category)
    lots = _require_count("lot_count", lot_count, minimum=1)
    variants = _require_count("variant_count", variant_count, minimum=1)
    findings = []
    if lots < rules["min_lots"]:
        findings.append(
            "%d production lot(s) offered; the %s category needs %d so that "
            "lot-to-lot spread in heat treatment is bounded"
            % (lots, category, rules["min_lots"])
        )
    if variants < rules["min_variants"]:
        findings.append(
            "%d size variant(s) offered; the %s category needs %d"
            % (variants, category, rules["min_variants"])
        )
    return findings


def requalification_scope(category, change):
    """Tests a declared change reopens, within what the category owes."""
    _require_choice("change", change, CHANGE_TYPES)
    owed = set(required_tests(category))
    moved = _CHANGE_IMPACT[change]
    return [test for test in required_tests(category) if test in owed and test in moved]


def shortfall(category, lot_count, variant_count, specimens_tested):
    """Specimens still outstanding per test, and unexpected records."""
    if not isinstance(specimens_tested, dict):
        raise ValueError(
            "specimens_tested must be a mapping of test name to count, got %r"
            % (specimens_tested,)
        )
    allocation = allocate_specimens(category, lot_count, variant_count)
    outstanding = {}
    for test, owed in allocation.items():
        done = specimens_tested.get(test, 0)
        _require_count("specimens_tested[%s]" % test, done)
        if done < owed:
            outstanding[test] = owed - done
    unexpected = sorted(set(specimens_tested) - set(allocation))
    return {"outstanding": outstanding, "unexpected_tests": unexpected}


def plan_qualification(case):
    """Full qualification programme and verdict for one fastener type."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    category = _require_choice(
        "category", case.get("category"), CRITICALITY_CATEGORIES
    )
    lots = _require_count("lot_count", case.get("lot_count"), minimum=1)
    variants = _require_count("variant_count", case.get("variant_count", 1), minimum=1)
    tested = case.get("specimens_tested", {})
    allocation = allocate_specimens(category, lots, variants)
    gaps = shortfall(category, lots, variants, tested)
    findings = coverage_findings(category, lots, variants)

    changes = case.get("changes", ())
    if isinstance(changes, str):
        raise ValueError("changes must be a sequence of change types, got a string")
    if not isinstance(changes, (list, tuple, set)):
        raise ValueError("changes must be a sequence of change types, got %r" % (changes,))
    reopened = {}
    for change in sorted(changes):
        scope = requalification_scope(category, change)
        if scope:
            reopened[change] = scope

    for test in sorted(gaps["outstanding"]):
        findings.append(
            "%s is short %d specimen(s) of the %d owed"
            % (test, gaps["outstanding"][test], allocation[test])
        )
    if gaps["unexpected_tests"]:
        findings.append(
            "specimens recorded against test(s) the %s category does not ask "
            "for: %s" % (category, ", ".join(gaps["unexpected_tests"]))
        )
    for change, scope in sorted(reopened.items()):
        findings.append(
            "declared change '%s' reopens %d test(s): %s"
            % (change, len(scope), ", ".join(scope))
        )

    if gaps["outstanding"]:
        verdict = VERDICT_INCOMPLETE
    elif reopened:
        verdict = VERDICT_REQUALIFICATION_OPEN
    else:
        verdict = VERDICT_COMPLETE

    return {
        "category": category,
        "lot_count": lots,
        "variant_count": variants,
        "required_tests": required_tests(category),
        "allocation": allocation,
        "programme_total": sum(allocation.values()),
        "outstanding": dict(gaps["outstanding"]),
        "unexpected_tests": gaps["unexpected_tests"],
        "requalification": reopened,
        "findings": findings,
        "verdict": verdict,
    }
