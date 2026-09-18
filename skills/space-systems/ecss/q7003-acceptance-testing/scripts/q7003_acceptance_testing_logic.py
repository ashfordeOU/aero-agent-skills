#!/usr/bin/env python3
"""Acceptance test programme for a batch of anodized parts.

Anchor: ECSS-Q-ST-70-03 verification clause on anodizing. The procedure
below is a paraphrase into implementable steps; no standard text is
reproduced.

Acceptance runs per processed batch, and what the batch owes depends on
the category of part in it:

flight-critical    every characteristic is verified, no defective is
                   allowed in the sample, and screening the rest of the
                   lot is not a way back in. A defective means the batch
                   goes back through review, because the process, not
                   the part, is what failed.
flight-standard    the load-bearing characteristics are verified and a
                   small defective allowance applies. A sample that
                   overruns the allowance can still be recovered by
                   screening every part rather than rejecting the lot.
ground-support     the basic characteristics are verified with a wider
                   allowance and screening available.

Two of the tests destroy what they touch. They are run on witness
coupons carried through the tanks with the batch, one set per rack, so
that the coupon has seen the same bath chemistry, current density and
dwell as the parts it stands for.

Sampling is a square-root plan with a category floor: the sample grows
with the lot but never falls below the floor, and never exceeds the lot.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_CATEGORIES = ("flight-critical", "flight-standard", "ground-support")

TEST_THICKNESS = "coating-thickness"
TEST_ADHESION = "coating-adhesion"
TEST_SEAL = "seal-quality"
TEST_CORROSION = "corrosion-resistance"
TEST_DIMENSIONAL = "dimensional-growth"
TEST_APPEARANCE = "appearance-and-colour"

BATCH_ACCEPT = "accept"
BATCH_SCREEN = "screen-whole-lot"
BATCH_REJECT = "reject"

_CATEGORY_RULES = {
    "flight-critical": {
        "tests": (
            TEST_THICKNESS,
            TEST_ADHESION,
            TEST_SEAL,
            TEST_CORROSION,
            TEST_DIMENSIONAL,
            TEST_APPEARANCE,
        ),
        "sample_floor": 8,
        "acceptance_per_hundred": 0,
        "screening_allowed": False,
    },
    "flight-standard": {
        "tests": (TEST_THICKNESS, TEST_ADHESION, TEST_SEAL, TEST_APPEARANCE),
        "sample_floor": 5,
        "acceptance_per_hundred": 10,
        "screening_allowed": True,
    },
    "ground-support": {
        "tests": (TEST_THICKNESS, TEST_ADHESION),
        "sample_floor": 3,
        "acceptance_per_hundred": 25,
        "screening_allowed": True,
    },
}

DESTRUCTIVE_TESTS = (TEST_ADHESION, TEST_CORROSION)


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


def _ceil_sqrt(n):
    """Smallest integer whose square is at least n, computed in integers.

    math.sqrt would be rounded on the way out and a perfect square could
    land either side of its own root on a different platform. Integer
    arithmetic has no such freedom.
    """
    if n <= 0:
        return 0
    root = math.isqrt(n - 1) + 1
    return root


def category_rules(category):
    """Sampling and acceptance rules that apply to one part category."""
    _require_choice("category", category, PART_CATEGORIES)
    rules = _CATEGORY_RULES[category]
    return {
        "category": category,
        "tests": list(rules["tests"]),
        "sample_floor": rules["sample_floor"],
        "acceptance_per_hundred": rules["acceptance_per_hundred"],
        "screening_allowed": rules["screening_allowed"],
    }


def required_tests(category):
    """Acceptance tests the category owes on every processed batch."""
    return list(category_rules(category)["tests"])


def destructive_tests(category):
    """Subset of the required tests that consume what they are run on."""
    return [test for test in required_tests(category) if test in DESTRUCTIVE_TESTS]


def sample_size(lot_size, category):
    """Square-root sample with a category floor, never above the lot."""
    lot = _require_count("lot_size", lot_size, minimum=1)
    rules = category_rules(category)
    return min(lot, max(rules["sample_floor"], _ceil_sqrt(lot)))


def acceptance_number(lot_size, category):
    """Defectives the sample may carry and still be accepted as drawn."""
    sample = sample_size(lot_size, category)
    rules = category_rules(category)
    return (sample * rules["acceptance_per_hundred"]) // 100


def witness_coupons_required(category, rack_count):
    """Witness coupons owed: one set per rack, only where a test destroys.

    A coupon only stands for the parts it travelled with, so a batch
    split over several racks owes a set per rack rather than one set for
    the batch.
    """
    racks = _require_count("rack_count", rack_count, minimum=1)
    destructive = destructive_tests(category)
    if not destructive:
        return {"coupons": 0, "per_rack": 0, "destructive_tests": []}
    per_rack = len(destructive)
    return {
        "coupons": per_rack * racks,
        "per_rack": per_rack,
        "destructive_tests": destructive,
    }


def judge_batch(lot_size, category, defective_count, screening_completed=False):
    """Accept, screen or reject the batch on the defectives found."""
    sample = sample_size(lot_size, category)
    defects = _require_count("defective_count", defective_count)
    if defects > sample:
        raise ValueError(
            "defective_count %d exceeds the sample of %d parts" % (defects, sample)
        )
    rules = category_rules(category)
    allowance = acceptance_number(lot_size, category)
    findings = []
    if defects <= allowance:
        return {
            "disposition": BATCH_ACCEPT,
            "sample_size": sample,
            "acceptance_number": allowance,
            "defective_count": defects,
            "findings": findings,
        }
    if not rules["screening_allowed"]:
        findings.append(
            "%d defective of %d sampled on a %s batch; screening is not a route "
            "back in because the process, not the part, produced the defect"
            % (defects, sample, category)
        )
        return {
            "disposition": BATCH_REJECT,
            "sample_size": sample,
            "acceptance_number": allowance,
            "defective_count": defects,
            "findings": findings,
        }
    if screening_completed:
        findings.append(
            "%d defective of %d sampled; the lot was screened part by part and "
            "the defectives removed" % (defects, sample)
        )
        disposition = BATCH_ACCEPT
    else:
        findings.append(
            "%d defective of %d sampled exceeds the allowance of %d; screen every "
            "part of the lot or reject it" % (defects, sample, allowance)
        )
        disposition = BATCH_SCREEN
    return {
        "disposition": disposition,
        "sample_size": sample,
        "acceptance_number": allowance,
        "defective_count": defects,
        "findings": findings,
    }


def plan_acceptance(case):
    """Full acceptance programme and disposition for one processed batch."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    category = _require_choice(
        "category", case.get("category"), PART_CATEGORIES
    )
    lot = _require_count("lot_size", case.get("lot_size"), minimum=1)
    racks = _require_count("rack_count", case.get("rack_count", 1), minimum=1)
    sample = sample_size(lot, category)
    coupons = witness_coupons_required(category, racks)
    tests = required_tests(category)
    performed = case.get("tests_performed")
    findings = []
    if performed is None:
        missing = list(tests)
    else:
        if not isinstance(performed, (list, tuple, set)):
            raise ValueError("tests_performed must be a sequence of test names")
        missing = [test for test in tests if test not in set(performed)]
        unexpected = sorted(set(performed) - set(tests))
        if unexpected:
            findings.append(
                "tests recorded that this category does not call for: %s"
                % ", ".join(unexpected)
            )
    result = {
        "category": category,
        "lot_size": lot,
        "sample_size": sample,
        "required_tests": tests,
        "missing_tests": missing,
        "witness_coupons": coupons,
        "acceptance_number": acceptance_number(lot, category),
        "findings": findings,
    }
    if missing:
        findings.append(
            "acceptance is incomplete; %d required test(s) not recorded: %s"
            % (len(missing), ", ".join(missing))
        )
        result.update({"disposition": None, "verdict": "acceptance-incomplete"})
        return result
    judgement = judge_batch(
        lot,
        category,
        case.get("defective_count", 0),
        screening_completed=bool(case.get("screening_completed", False)),
    )
    findings.extend(judgement["findings"])
    result.update(
        {
            "disposition": judgement["disposition"],
            "defective_count": judgement["defective_count"],
            "verdict": "acceptance-complete",
        }
    )
    return result
