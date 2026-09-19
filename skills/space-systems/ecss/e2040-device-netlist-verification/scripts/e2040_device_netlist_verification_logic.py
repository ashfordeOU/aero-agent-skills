#!/usr/bin/env python3
"""Netlist verification (ECSS-E-ST-20-40C clause 5.5.3).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The clause checks that the netlist synthesis produced still carries the
design intent it was made from, and records what the check found. Two
kinds of evidence close it, and neither is sufficient alone:

* an equivalence comparison relating points in the source description
  to points in the netlist. A point has four states -- equivalent,
  not-equivalent, unmapped and waived -- and folding the unmapped in
  with the equivalent produces a clean report over an unexamined
  region;
* a re-run of the source-level tests on the netlist, exercising what
  the comparison abstracts away. A test not re-run is not a test that
  passed, and a test that passed before and fails now isolates the
  synthesis, so it stays separate from one already failing.

The outcome is derived from the evidence rather than declared: a
verified outcome the evidence does not carry stops anybody looking
again.
"""

import math

EQUIVALENT = "equivalent"
NOT_EQUIVALENT = "not-equivalent"
UNMAPPED = "unmapped"
WAIVED = "waived"
POINT_STATES = (EQUIVALENT, NOT_EQUIVALENT, UNMAPPED, WAIVED)
_POINT_ALIASES = {
    "equivalent": EQUIVALENT,
    "match": EQUIVALENT,
    "matched": EQUIVALENT,
    "proven": EQUIVALENT,
    "not-equivalent": NOT_EQUIVALENT,
    "not equivalent": NOT_EQUIVALENT,
    "mismatch": NOT_EQUIVALENT,
    "failed": NOT_EQUIVALENT,
    "unmapped": UNMAPPED,
    "unmatched": UNMAPPED,
    "no mapping": UNMAPPED,
    "abandoned": UNMAPPED,
    "waived": WAIVED,
    "waiver": WAIVED,
    "accepted": WAIVED,
}

PASS = "pass"
FAIL = "fail"
NOT_RUN = "not-run"
TEST_RESULTS = (PASS, FAIL, NOT_RUN)
_RESULT_ALIASES = {
    "pass": PASS,
    "passed": PASS,
    "ok": PASS,
    "fail": FAIL,
    "failed": FAIL,
    "error": FAIL,
    "not-run": NOT_RUN,
    "not run": NOT_RUN,
    "skipped": NOT_RUN,
    "pending": NOT_RUN,
}

VERIFIED = "verified"
VERIFIED_WITH_WAIVERS = "verified-with-waivers"
NOT_VERIFIED = "not-verified"
OUTCOMES = (VERIFIED, VERIFIED_WITH_WAIVERS, NOT_VERIFIED)

REL_TOL = 1e-12
ABS_TOL = 1e-18

_POINT_KEYS = ("id", "state", "justification", "region")
_TEST_KEYS = ("id", "source_result", "netlist_result", "subject")
_CHECK_REQUIRED_KEYS = ("points", "tests")
_CHECK_OPTIONAL_KEYS = ("equivalence_goal", "outcome_record")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def meets_equivalence_goal(achieved, goal):
    """True when the equivalence reached meets the goal, exact landings included."""
    achieved = _fraction("achieved", achieved)
    goal = _fraction("goal", goal)
    return achieved > goal or math.isclose(
        achieved, goal, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def normalize_point_state(value):
    """Fold a comparison point state onto one of the four recognised states."""
    key = " ".join(_text("point state", value).lower().replace("_", " ").split())
    if key in _POINT_ALIASES:
        return _POINT_ALIASES[key]
    hyphenated = key.replace(" ", "-")
    if hyphenated in _POINT_ALIASES:
        return _POINT_ALIASES[hyphenated]
    raise ValueError(
        "unknown comparison point state %r; use one of %s"
        % (value, ", ".join(POINT_STATES))
    )


def normalize_test_result(value):
    """Fold a test result spelling onto pass, fail or not-run."""
    key = " ".join(_text("test result", value).lower().replace("_", " ").split())
    if key in _RESULT_ALIASES:
        return _RESULT_ALIASES[key]
    hyphenated = key.replace(" ", "-")
    if hyphenated in _RESULT_ALIASES:
        return _RESULT_ALIASES[hyphenated]
    raise ValueError(
        "unknown test result %r; use one of %s" % (value, ", ".join(TEST_RESULTS))
    )


def validate_points(records):
    """Check the comparison points and return them resolved in declared order."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("points must be a list")
    resolved = []
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("points[%d] must be a mapping" % index)
        unknown = sorted(set(record) - set(_POINT_KEYS))
        if unknown:
            raise ValueError(
                "points[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "state"):
            if key not in record:
                raise ValueError("points[%d] missing key: %s" % (index, key))
        point_id = _text("points[%d].id" % index, record["id"])
        if point_id in seen:
            raise ValueError("duplicate comparison point id %r" % point_id)
        seen.add(point_id)
        resolved.append(
            {
                "id": point_id,
                "state": normalize_point_state(record["state"]),
                "justification": _text(
                    "points[%d].justification" % index,
                    record.get("justification", ""),
                    allow_empty=True,
                ),
                "region": _text(
                    "points[%d].region" % index,
                    record.get("region", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def validate_tests(records):
    """Check the test list and return it resolved in declared order."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("tests must be a list")
    resolved = []
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("tests[%d] must be a mapping" % index)
        unknown = sorted(set(record) - set(_TEST_KEYS))
        if unknown:
            raise ValueError(
                "tests[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "id" not in record:
            raise ValueError("tests[%d] missing key: id" % index)
        test_id = _text("tests[%d].id" % index, record["id"])
        if test_id in seen:
            raise ValueError("duplicate test id %r" % test_id)
        seen.add(test_id)
        resolved.append(
            {
                "id": test_id,
                "source_result": normalize_test_result(
                    record.get("source_result", NOT_RUN)
                ),
                "netlist_result": normalize_test_result(
                    record.get("netlist_result", NOT_RUN)
                ),
                "subject": _text(
                    "tests[%d].subject" % index,
                    record.get("subject", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def points_in_state(points, state):
    """Comparison point ids in one state."""
    return sorted(p["id"] for p in points if p["state"] == state)


def unjustified_waivers(points):
    """Waived comparison point ids carrying no justification."""
    return sorted(
        p["id"] for p in points if p["state"] == WAIVED and not p["justification"]
    )


def equivalence_fraction(points):
    """Fraction of comparison points the check proved equivalent.

    Unmapped and waived points stay in the denominator: they are exactly
    what the figure is meant to surface.
    """
    if not points:
        raise ValueError("equivalence_fraction needs at least one comparison point")
    return sum(1 for p in points if p["state"] == EQUIVALENT) / len(points)


def tests_not_rerun(tests):
    """Tests that passed against the source and were not run on the netlist."""
    return sorted(
        t["id"]
        for t in tests
        if t["source_result"] == PASS and t["netlist_result"] == NOT_RUN
    )


def tests_broken_by_synthesis(tests):
    """Tests that passed against the source and fail on the netlist."""
    return sorted(
        t["id"]
        for t in tests
        if t["source_result"] == PASS and t["netlist_result"] == FAIL
    )


def tests_already_failing(tests):
    """Tests that were already failing against the source description."""
    return sorted(t["id"] for t in tests if t["source_result"] == FAIL)


def rerun_completeness(tests):
    """Fraction of source-level passes that were re-run on the netlist."""
    candidates = [t for t in tests if t["source_result"] == PASS]
    if not candidates:
        raise ValueError("rerun_completeness needs at least one source-level pass")
    return sum(1 for t in candidates if t["netlist_result"] != NOT_RUN) / len(candidates)


def netlist_verification_outcome(points, tests):
    """Derive the outcome the evidence actually carries."""
    if points_in_state(points, NOT_EQUIVALENT):
        return NOT_VERIFIED
    if points_in_state(points, UNMAPPED):
        return NOT_VERIFIED
    if unjustified_waivers(points):
        return NOT_VERIFIED
    if tests_not_rerun(tests) or tests_broken_by_synthesis(tests):
        return NOT_VERIFIED
    if points_in_state(points, WAIVED):
        return VERIFIED_WITH_WAIVERS
    return VERIFIED


def evaluate_netlist_verification(check):
    """Full clause 5.5.3 assessment of one netlist verification and its record.

    Returns the equivalence reached, the test findings, the derived outcome
    and the verdict.
    """
    if not isinstance(check, dict):
        raise ValueError("check must be a mapping of points, tests and a record")
    known = set(_CHECK_REQUIRED_KEYS) | set(_CHECK_OPTIONAL_KEYS)
    unknown = sorted(set(check) - known)
    if unknown:
        raise ValueError("unknown check keys: %s" % ", ".join(unknown))
    absent = [key for key in _CHECK_REQUIRED_KEYS if key not in check]
    if absent:
        raise ValueError("check missing required keys: %s" % ", ".join(absent))

    points = validate_points(check["points"])
    if not points:
        raise ValueError("check must carry at least one comparison point")
    tests = validate_tests(check["tests"])
    if not tests:
        raise ValueError("check must carry at least one test")
    record = _text("outcome_record", check.get("outcome_record", ""), allow_empty=True)

    findings = []
    for point_id in points_in_state(points, NOT_EQUIVALENT):
        findings.append(
            {
                "code": "comparison-point-not-equivalent",
                "point": point_id,
                "detail": "comparison point %s does not match between the source "
                "description and the netlist" % point_id,
            }
        )
    for point_id in points_in_state(points, UNMAPPED):
        findings.append(
            {
                "code": "comparison-point-unmapped",
                "point": point_id,
                "detail": "comparison point %s could not be related at all, so the "
                "region behind it was never examined" % point_id,
            }
        )
    for point_id in unjustified_waivers(points):
        findings.append(
            {
                "code": "waiver-without-justification",
                "point": point_id,
                "detail": "comparison point %s is waived with nothing written "
                "against it" % point_id,
            }
        )

    for test_id in tests_not_rerun(tests):
        findings.append(
            {
                "code": "source-pass-not-rerun-on-netlist",
                "test": test_id,
                "detail": "test %s passed against the source description and was "
                "not run on the netlist, so that evidence does not exist" % test_id,
            }
        )
    for test_id in tests_broken_by_synthesis(tests):
        findings.append(
            {
                "code": "test-broken-by-synthesis",
                "test": test_id,
                "detail": "test %s passed against the source description and fails "
                "on the netlist, which isolates the synthesis" % test_id,
            }
        )
    for test_id in tests_already_failing(tests):
        findings.append(
            {
                "code": "test-already-failing-before-synthesis",
                "test": test_id,
                "detail": "test %s was already failing against the source "
                "description, so it proves nothing about the netlist" % test_id,
            }
        )

    equivalence = equivalence_fraction(points)
    goal = check.get("equivalence_goal")
    if goal is not None:
        goal_value = _fraction("equivalence_goal", goal)
        if not meets_equivalence_goal(equivalence, goal_value):
            findings.append(
                {
                    "code": "equivalence-below-goal",
                    "achieved": equivalence,
                    "goal": goal_value,
                    "detail": "equivalence reaches %.1f %% against a %.1f %% goal"
                    % (100.0 * equivalence, 100.0 * goal_value),
                }
            )

    if not record:
        findings.append(
            {
                "code": "outcome-not-recorded",
                "detail": "the check names no outcome record, so as far as the next "
                "phase is concerned the work did not happen",
            }
        )

    outcome = netlist_verification_outcome(points, tests)
    return {
        "outcome": outcome,
        "point_count": len(points),
        "not_equivalent_points": points_in_state(points, NOT_EQUIVALENT),
        "unmapped_points": points_in_state(points, UNMAPPED),
        "unjustified_waivers": unjustified_waivers(points),
        "equivalence": equivalence,
        "tests_not_rerun": tests_not_rerun(tests),
        "tests_broken_by_synthesis": tests_broken_by_synthesis(tests),
        "tests_already_failing": tests_already_failing(tests),
        "outcome_record": record,
        "findings": findings,
        "detailed_design_may_continue": outcome != NOT_VERIFIED and bool(record),
    }
