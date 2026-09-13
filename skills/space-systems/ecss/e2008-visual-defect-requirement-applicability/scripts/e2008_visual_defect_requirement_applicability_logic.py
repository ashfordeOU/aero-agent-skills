#!/usr/bin/env python3
"""Applicability envelope of the visible defect requirements for cell assemblies.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause does not say what a defect is. It says who the defect rules
reach: the cell assemblies that are being put forward when a
qualification approval is granted. That is an applicability question
and it is settled before any individual defect is dispositioned,
because a defect call made against an item the rules never governed is
not evidence of anything and a category nobody submitted leaves a hole
in the approval that no amount of inspection closes.

Four things move an item in or out of the envelope.

The purpose it was submitted under. The rules bite where an approval is
being granted or extended. An item circulated for information, or one
running against lot acceptance criteria after the approval already
exists, is outside -- not because it is good, but because this clause
is not the one that governs it.

Its category. An approval names the assembly categories it covers. An
item of a category outside that list is not reached, and crediting it
inflates the approved population.

Its build standard. An item built to something other than the qualified
build is inside the subject matter of the rules and outside the
approval envelope, so it points at a qualification extension rather
than at a pass or a fail.

Its representativeness. A sample that does not reproduce the flight
process cannot carry an approval however clean it inspects, so it goes
to review rather than quietly counting toward coverage.

The output is per item and rolled up: which categories ended up covered
by at least the required number of governed items, which did not, and
what fraction of the submitted samples the rules actually govern.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ASSEMBLY_CATEGORIES = (
    "bare-cell-assembly",
    "coverglassed-assembly",
    "interconnected-assembly",
    "diode-equipped-assembly",
    "assembly-on-substrate-coupon",
)

SUBMISSION_PURPOSES = (
    "qualification-approval",
    "qualification-extension",
    "lot-acceptance",
    "information-only",
)

GOVERNED = "requirements-apply"
EXTENSION = "requires-qualification-extension"
OUT_OF_SCOPE = "outside-applicability"
REFER = "refer-for-review"
APPLICABILITY_STATES = (GOVERNED, EXTENSION, OUT_OF_SCOPE, REFER)

ENVELOPE_ESTABLISHED = "applicability-established"
ENVELOPE_INCOMPLETE = "applicability-incomplete"

_STATE_ORDER = {GOVERNED: 0, OUT_OF_SCOPE: 1, EXTENSION: 2, REFER: 3}

DEFAULT_APPLICABILITY_POLICY = {
    "applicable_categories": (
        "coverglassed-assembly",
        "interconnected-assembly",
        "diode-equipped-assembly",
    ),
    "approval_purposes": ("qualification-approval", "qualification-extension"),
    "qualified_build_standard": "BS-QUAL-A",
    "min_process_representativeness": 0.90,
    "min_items_per_category": 1,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive integer, got %r" % (name, value))
    return value


def _at_least(value, floor):
    """value >= floor, absorbing floating-point representation error.

    A representativeness figure is a ratio of two measured or declared
    quantities, so a sample sitting exactly on the policy floor can
    evaluate a few units in the last place below it. The floor is never
    lowered; only the comparison tolerates the representation error.
    """
    return value >= floor or math.isclose(
        value, floor, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(states):
    worst = GOVERNED
    for state in states:
        if _STATE_ORDER[state] > _STATE_ORDER[worst]:
            worst = state
    return worst


def validate_applicability_policy(policy):
    """Check an applicability policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    categories = policy.get("applicable_categories")
    if not isinstance(categories, (list, tuple)) or not categories:
        raise ValueError(
            "policy applicable_categories must be a non-empty sequence, got %r"
            % (categories,)
        )
    for category in categories:
        _require_choice("policy applicable category", category, ASSEMBLY_CATEGORIES)
    if len(set(categories)) != len(categories):
        raise ValueError(
            "policy applicable_categories repeats a category: %r" % (categories,)
        )
    purposes = policy.get("approval_purposes")
    if not isinstance(purposes, (list, tuple)) or not purposes:
        raise ValueError(
            "policy approval_purposes must be a non-empty sequence, got %r"
            % (purposes,)
        )
    for purpose in purposes:
        _require_choice("policy approval purpose", purpose, SUBMISSION_PURPOSES)
    if "information-only" in purposes:
        raise ValueError(
            "an information-only submission never grants an approval, so it "
            "cannot be listed as an approval purpose"
        )
    _require_identifier(
        "policy qualified_build_standard", policy.get("qualified_build_standard")
    )
    _require_fraction(
        "policy min_process_representativeness",
        policy.get("min_process_representativeness"),
    )
    _require_count(
        "policy min_items_per_category", policy.get("min_items_per_category")
    )
    return policy


def assess_assembly_applicability(item, policy=DEFAULT_APPLICABILITY_POLICY):
    """Decide whether the visible defect rules reach one cell assembly item."""
    validate_applicability_policy(policy)
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (item,))
    assembly_id = _require_identifier("assembly_id", item.get("assembly_id"))
    category = _require_choice("category", item.get("category"), ASSEMBLY_CATEGORIES)
    purpose = _require_choice("purpose", item.get("purpose"), SUBMISSION_PURPOSES)
    build_standard = _require_identifier("build_standard", item.get("build_standard"))
    representativeness = _require_fraction(
        "process_representativeness", item.get("process_representativeness")
    )
    sample_count = _require_count("sample_count", item.get("sample_count"))

    reasons = []
    if purpose not in tuple(policy["approval_purposes"]):
        if purpose == "information-only":
            reasons.append(
                "submitted for information, so no approval turns on it and the "
                "visible defect rules do not reach it"
            )
        else:
            reasons.append(
                "submitted under %s rather than an approval grant; lot acceptance "
                "runs against its own criteria and inherits the approval instead "
                "of creating it" % (purpose,)
            )
        return {
            "assembly_id": assembly_id,
            "category": category,
            "purpose": purpose,
            "state": OUT_OF_SCOPE,
            "governed": False,
            "counts_toward_coverage": False,
            "sample_count": sample_count,
            "process_representativeness": representativeness,
            "reasons": reasons,
        }

    if category not in tuple(policy["applicable_categories"]):
        reasons.append(
            "category %s is not one the approval covers, so crediting it would "
            "widen the approved population past what was examined" % (category,)
        )
        return {
            "assembly_id": assembly_id,
            "category": category,
            "purpose": purpose,
            "state": OUT_OF_SCOPE,
            "governed": False,
            "counts_toward_coverage": False,
            "sample_count": sample_count,
            "process_representativeness": representativeness,
            "reasons": reasons,
        }

    if build_standard != policy["qualified_build_standard"]:
        reasons.append(
            "built to %s against the qualified %s; the rules are the right ones "
            "but the approval envelope has to be extended before this build sits "
            "inside it" % (build_standard, policy["qualified_build_standard"])
        )
        return {
            "assembly_id": assembly_id,
            "category": category,
            "purpose": purpose,
            "state": EXTENSION,
            "governed": True,
            "counts_toward_coverage": False,
            "sample_count": sample_count,
            "process_representativeness": representativeness,
            "reasons": reasons,
        }

    if not _at_least(representativeness, policy["min_process_representativeness"]):
        reasons.append(
            "reproduces %.4f of the flight process against a %.4f floor; a sample "
            "that is not representative cannot carry an approval however clean it "
            "inspects" % (representativeness, policy["min_process_representativeness"])
        )
        return {
            "assembly_id": assembly_id,
            "category": category,
            "purpose": purpose,
            "state": REFER,
            "governed": True,
            "counts_toward_coverage": False,
            "sample_count": sample_count,
            "process_representativeness": representativeness,
            "reasons": reasons,
        }

    if purpose == "qualification-extension":
        reasons.append(
            "governed as part of an extension to an existing approval rather than "
            "an initial grant"
        )
    return {
        "assembly_id": assembly_id,
        "category": category,
        "purpose": purpose,
        "state": GOVERNED,
        "governed": True,
        "counts_toward_coverage": True,
        "sample_count": sample_count,
        "process_representativeness": representativeness,
        "reasons": reasons,
    }


def map_qualification_applicability(submission, policy=DEFAULT_APPLICABILITY_POLICY):
    """Clause 6.4.3.1.1 applicability envelope over a whole submission."""
    validate_applicability_policy(policy)
    if not isinstance(submission, dict):
        raise ValueError("submission must be a mapping, got %r" % (submission,))
    submission_id = _require_identifier(
        "submission_id", submission.get("submission_id")
    )
    items = submission.get("assemblies")
    if not isinstance(items, (list, tuple)):
        raise ValueError("assemblies must be a list, got %r" % (items,))
    if not items:
        raise ValueError(
            "submission %s carries no assemblies; an empty population cannot "
            "establish an applicability envelope" % (submission_id,)
        )

    seen = set()
    assessed = []
    for item in items:
        result = assess_assembly_applicability(item, policy)
        marker = result["assembly_id"]
        if marker in seen:
            raise ValueError(
                "duplicate assembly id %r in submission %s" % (marker, submission_id)
            )
        seen.add(marker)
        assessed.append(result)

    findings = []
    counts = dict((state, 0) for state in APPLICABILITY_STATES)
    coverage = dict((category, 0) for category in policy["applicable_categories"])
    total_samples = 0
    governed_samples = 0
    for result in assessed:
        counts[result["state"]] += 1
        total_samples += result["sample_count"]
        if result["governed"]:
            governed_samples += result["sample_count"]
        if result["counts_toward_coverage"]:
            coverage[result["category"]] += 1
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["assembly_id"], reason))

    minimum = policy["min_items_per_category"]
    uncovered = [
        category
        for category in policy["applicable_categories"]
        if coverage[category] < minimum
    ]
    for category in uncovered:
        findings.append(
            "category %s is covered by %d governed item(s) against the %d "
            "required; the approval would reach a population nobody examined"
            % (category, coverage[category], minimum)
        )

    state = _worst([result["state"] for result in assessed])
    complete = not uncovered
    verdict = ENVELOPE_ESTABLISHED if complete and state != REFER else ENVELOPE_INCOMPLETE
    governed_sample_fraction = governed_samples / float(total_samples)
    return {
        "submission_id": submission_id,
        "verdict": verdict,
        "worst_state": state,
        "envelope_complete": complete,
        "state_counts": counts,
        "category_coverage": coverage,
        "uncovered_categories": uncovered,
        "extension_required_ids": [
            result["assembly_id"]
            for result in assessed
            if result["state"] == EXTENSION
        ],
        "out_of_scope_ids": [
            result["assembly_id"]
            for result in assessed
            if result["state"] == OUT_OF_SCOPE
        ],
        "review_ids": [
            result["assembly_id"] for result in assessed if result["state"] == REFER
        ],
        "total_sample_count": total_samples,
        "governed_sample_count": governed_samples,
        "governed_sample_fraction": governed_sample_fraction,
        "assemblies": assessed,
        "findings": findings,
    }
