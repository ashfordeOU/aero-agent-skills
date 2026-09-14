#!/usr/bin/env python3
"""Testing overview for planar blocking diodes: the two test sets.

Anchor: ECSS-E-ST-20-08C clause 12.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A planar blocking diode carries two test sets, not one. The
qualification set is owed once against the design and demonstrates the
part can survive the mission it is bought for. The procurement set is
owed again on every delivered lot and demonstrates the lot in front of
you was built to the design that was qualified. They are answered by
different hardware at different times, and reading them as one
programme is the defect this leaf exists to catch.

Some tests appear in both sets. A visual inspection and an electrical
characterisation are run in the qualification campaign and again on each
procured lot. Because the sets speak for different populations, a shared
test run once in the qualification campaign does not discharge the lot
obligation -- the qualification parts were consumed, and the lot was
not in the chamber. Counting one run twice is how a lot ships with no
acceptance evidence of its own while the matrix reads complete.

    qualification   owed once per design, on parts consumed by the
                    campaign; demonstrates the design
    procurement     owed per delivered lot, on parts representative of
                    that lot; demonstrates the build

Four record states are kept apart because different people disposition
them: no record at all, recorded as not yet run, recorded as failed,
recorded as passed. Absence is the worst because nobody can tell whether
the work was skipped, lost or never scheduled.

A qualification claimed by similarity to an already qualified part is a
legitimate route and a common one, but it is evidence-bearing: it rests
on a named heritage part and a delta justification, and without both it
is an assertion rather than a qualification.

The test sets, the coverage minimum and the failure policy below are
declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TEST_SETS = ("qualification", "procurement")

QUALIFICATION_TESTS = (
    "planar-blocking-diode-visual-inspection",
    "planar-blocking-diode-electrical-characterization",
    "planar-blocking-diode-thermal-vacuum",
    "planar-blocking-diode-thermal-cycling",
    "planar-blocking-diode-humidity",
    "planar-blocking-diode-mechanical-shock",
    "planar-blocking-diode-life-test",
    "planar-blocking-diode-contact-adherence",
)

PROCUREMENT_TESTS = (
    "planar-blocking-diode-visual-inspection",
    "planar-blocking-diode-electrical-characterization",
    "planar-blocking-diode-burn-in",
    "planar-blocking-diode-seal-integrity",
)

SET_MEMBERSHIP = {
    "qualification": QUALIFICATION_TESTS,
    "procurement": PROCUREMENT_TESTS,
}

SHARED_TESTS = tuple(t for t in QUALIFICATION_TESTS if t in PROCUREMENT_TESTS)

ALL_TESTS = tuple(
    sorted(set(QUALIFICATION_TESTS) | set(PROCUREMENT_TESTS))
)

OUTCOME_PASSED = "passed"
OUTCOME_FAILED = "failed"
OUTCOME_NOT_RUN = "not-run"
OUTCOMES = (OUTCOME_PASSED, OUTCOME_FAILED, OUTCOME_NOT_RUN)

QUAL_BY_TEST = "qualified-by-test"
QUAL_IN_PROGRESS = "qualification-in-progress"
QUAL_BY_SIMILARITY = "qualification-claimed-by-similarity"
QUAL_NONE = "not-qualified"
QUALIFICATION_STATES = (
    QUAL_BY_TEST,
    QUAL_IN_PROGRESS,
    QUAL_BY_SIMILARITY,
    QUAL_NONE,
)

SET_COMPLETE = "test-set-complete"
SET_FAILED = "test-set-failed"
SET_NOT_RUN = "test-set-not-run"
SET_NO_RECORD = "test-set-not-recorded"

SET_RANK = {
    SET_NO_RECORD: 0,
    SET_NOT_RUN: 1,
    SET_FAILED: 2,
    SET_COMPLETE: 3,
}

PROGRAMME_CLEAR = "blocking-diode-test-programme-clear"
PROGRAMME_OPEN = "blocking-diode-test-programme-open"

DEFAULT_PROGRAMME_POLICY = {
    "min_set_coverage": 1.0,
    "accept_similarity_claim": False,
    "carry_dispositioned_failure": False,
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


def _require_fraction(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if not 0.0 < value <= 1.0:
        raise ValueError(
            "%s must sit above zero and at or below one, got %r" % (name, value)
        )
    return float(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A set coverage figure is a quotient of two test counts, so a campaign
    that ran exactly the owed number can evaluate a unit in the last
    place below its declared minimum. The comparison absorbs that; the
    declared minimum is untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def test_sets_for(test_name):
    """Name the set or sets that own one test."""
    name = _require_choice("test", test_name, ALL_TESTS)
    return tuple(s for s in TEST_SETS if name in SET_MEMBERSHIP[s])


def is_shared_test(test_name):
    """True when a test is owed by both sets and so runs twice."""
    return len(test_sets_for(test_name)) == len(TEST_SETS)


def resolve_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_PROGRAMME_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    _require_fraction("min_set_coverage", settings.get("min_set_coverage"))
    _require_flag("accept_similarity_claim", settings.get("accept_similarity_claim"))
    _require_flag(
        "carry_dispositioned_failure", settings.get("carry_dispositioned_failure")
    )
    return settings


def validate_records(records, test_set):
    """Check a record book names only tests the given set owes."""
    owner = _require_choice("test_set", test_set, TEST_SETS)
    book = _require_mapping("records", records if records is not None else {})
    cleaned = {}
    for test_name, outcome in book.items():
        name = _require_choice("test", test_name, ALL_TESTS)
        if owner not in test_sets_for(name):
            raise ValueError(
                "%s is not owed by the %s set; booking it there is a misfiled "
                "record, not coverage" % (name, owner)
            )
        cleaned[name] = _require_choice("outcome for %s" % name, outcome, OUTCOMES)
    return cleaned


def assess_test_set(records, test_set, policy=None):
    """Grade one test set on the owed tests it actually reached."""
    settings = resolve_policy(policy)
    owner = _require_choice("test_set", test_set, TEST_SETS)
    book = validate_records(records, owner)
    owed = SET_MEMBERSHIP[owner]

    missing = [t for t in owed if t not in book]
    not_run = [t for t in owed if book.get(t) == OUTCOME_NOT_RUN]
    failed = [t for t in owed if book.get(t) == OUTCOME_FAILED]
    passed = [t for t in owed if book.get(t) == OUTCOME_PASSED]

    coverage = len(passed) / len(owed)
    meets_coverage = _at_least(coverage, settings["min_set_coverage"])

    findings = []
    for test_name in missing:
        findings.append(
            "%s set: no record at all for %s; nobody can tell whether the work "
            "was skipped, lost or never scheduled" % (owner, test_name)
        )
    for test_name in not_run:
        findings.append(
            "%s set: %s is recorded as not yet run" % (owner, test_name)
        )
    for test_name in failed:
        findings.append(
            "%s set: %s is recorded as failed and needs a disposition"
            % (owner, test_name)
        )
    if not meets_coverage and not (missing or not_run or failed):
        findings.append(
            "%s set: coverage %.4g sits below the declared %.4g"
            % (owner, coverage, settings["min_set_coverage"])
        )

    if missing:
        verdict = SET_NO_RECORD
    elif not_run:
        verdict = SET_NOT_RUN
    elif failed:
        verdict = SET_FAILED
    else:
        verdict = SET_COMPLETE

    return {
        "test_set": owner,
        "owed": list(owed),
        "missing": missing,
        "not_run": not_run,
        "failed": failed,
        "passed": passed,
        "coverage": coverage,
        "meets_coverage": meets_coverage,
        "verdict": verdict,
        "findings": findings,
    }


def shared_test_double_count(qualification_records, lot_records):
    """Name the shared tests a lot is leaning on the design campaign for.

    A shared test that has a qualification record and no lot record has
    been counted twice: the run it points at was made on parts the
    campaign consumed, and it says nothing about this lot.
    """
    qual = validate_records(qualification_records, "qualification")
    lot = validate_records(lot_records, "procurement")
    return [t for t in SHARED_TESTS if t in qual and t not in lot]


def assess_qualification(qualification, policy=None):
    """Grade the design campaign, including a similarity claim."""
    settings = resolve_policy(policy)
    block = _require_mapping("qualification", qualification)
    status = _require_choice(
        "qualification status", block.get("status"), QUALIFICATION_STATES
    )
    graded = assess_test_set(
        block.get("records") or {}, "qualification", settings
    )
    findings = list(graded["findings"])
    heritage = block.get("heritage_part")
    delta = block.get("delta_justification")

    similarity_supported = False
    if status == QUAL_BY_SIMILARITY:
        has_heritage = isinstance(heritage, str) and heritage.strip()
        has_delta = isinstance(delta, str) and delta.strip()
        similarity_supported = bool(has_heritage and has_delta)
        if not has_heritage:
            findings.append(
                "a similarity claim names no heritage part, so there is "
                "nothing for the design to be similar to"
            )
        if not has_delta:
            findings.append(
                "a similarity claim carries no delta justification, so the "
                "differences from the heritage part are undispositioned"
            )
        if similarity_supported and not settings["accept_similarity_claim"]:
            findings.append(
                "the similarity claim is supported but project policy does "
                "not accept similarity in place of the qualification set"
            )
    elif status == QUAL_NONE:
        findings.append(
            "the design carries no qualification at all, so the procurement "
            "set has no qualified build to be compared against"
        )
    elif status == QUAL_IN_PROGRESS:
        findings.append(
            "the qualification campaign is still open, so delivered lots are "
            "being procured against an unfinished design demonstration"
        )

    accepted = False
    if status == QUAL_BY_TEST:
        accepted = graded["verdict"] == SET_COMPLETE and graded["meets_coverage"]
    elif status == QUAL_BY_SIMILARITY:
        accepted = similarity_supported and settings["accept_similarity_claim"]

    return {
        "status": status,
        "set": graded,
        "heritage_part": heritage if isinstance(heritage, str) else None,
        "similarity_supported": similarity_supported,
        "accepted": accepted,
        "findings": findings,
    }


def assess_procurement_lot(lot, qualification_records=None, policy=None):
    """Grade one delivered lot against the procurement set."""
    settings = resolve_policy(policy)
    entry = _require_mapping("lot", lot)
    lot_id = _require_label("lot_id", entry.get("lot_id"))
    graded = assess_test_set(entry.get("records") or {}, "procurement", settings)
    findings = ["%s: %s" % (lot_id, f) for f in graded["findings"]]

    leaned_on = []
    if qualification_records is not None:
        leaned_on = shared_test_double_count(
            qualification_records, entry.get("records") or {}
        )
        for test_name in leaned_on:
            findings.append(
                "%s: %s has a qualification record and no lot record; the "
                "campaign parts were consumed, so that run cannot stand for "
                "this lot" % (lot_id, test_name)
            )
    return {
        "lot_id": lot_id,
        "set": graded,
        "leaning_on_qualification": leaned_on,
        "verdict": graded["verdict"],
        "findings": findings,
    }


def assess_blocking_diode_test_programme(case):
    """Full clause 12.2.1 roll-up over both test sets."""
    _require_mapping("case", case)
    part_id = _require_label("part_id", case.get("part_id"))
    settings = resolve_policy(case.get("policy"))
    qualification = assess_qualification(case.get("qualification"), settings)

    lots = case.get("lots")
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("case must carry a non-empty lots sequence")

    qual_records = (case.get("qualification") or {}).get("records") or {}
    seen = set()
    graded_lots = []
    for lot in lots:
        result = assess_procurement_lot(lot, qual_records, settings)
        if result["lot_id"] in seen:
            raise ValueError("lot %r appears twice in one programme" % result["lot_id"])
        seen.add(result["lot_id"])
        graded_lots.append(result)

    findings = list(qualification["findings"])
    for result in graded_lots:
        findings.extend(result["findings"])

    grouped = {}
    for result in graded_lots:
        grouped.setdefault(result["verdict"], []).append(result["lot_id"])
    for names in grouped.values():
        names.sort()

    blocking = set(grouped) - {SET_COMPLETE}
    if settings["carry_dispositioned_failure"]:
        blocking -= {SET_FAILED}

    coverage_short = any(not r["set"]["meets_coverage"] for r in graded_lots)
    leaning = any(r["leaning_on_qualification"] for r in graded_lots)

    if (
        qualification["accepted"]
        and not blocking
        and not coverage_short
        and not leaning
    ):
        verdict = PROGRAMME_CLEAR
    else:
        verdict = PROGRAMME_OPEN

    weakest = min(
        graded_lots, key=lambda r: (SET_RANK[r["verdict"]], r["lot_id"])
    )
    return {
        "part_id": part_id,
        "qualification": qualification,
        "lots": graded_lots,
        "grouped_lots": grouped,
        "shared_tests": list(SHARED_TESTS),
        "weakest_lot": weakest["lot_id"],
        "verdict": verdict,
        "findings": findings,
    }
