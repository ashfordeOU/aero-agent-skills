#!/usr/bin/env python3
"""Test conditions and methods for a solar cell assembly, against its drawing.

Anchor: ECSS-E-ST-20-08C clause 6.1.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A solar cell assembly is bought and accepted against a cell assembly
source control drawing. The drawing, not the laboratory, decides which
tests are run, by which method, and at which conditions. A result only
stands as evidence when the method the drawing allows was used and the
condition the drawing specifies was demonstrated -- demonstrated, not
merely declared, because the instrument that recorded the condition has
an uncertainty of its own and that uncertainty eats the tolerance
window from the inside.

Method source, strongest to weakest
    drawing-named              the drawing names the method outright
    drawing-invoked-standard   the drawing invokes a standard that names it
    approved-equivalent        a substitute standing on a written approval
    supplier-internal          a house procedure the drawing never saw

Condition verdicts
    demonstrated               setpoint plus instrument uncertainty fits
    within-window-undemonstrated   setpoint fits, the uncertainty does not
    outside-window             the setpoint itself misses the window

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

METHOD_SOURCES = (
    "drawing-named",
    "drawing-invoked-standard",
    "approved-equivalent",
    "supplier-internal",
)

ALIGNED = "aligned"
ALIGNED_UNDER_APPROVAL = "aligned-under-approval"
MISALIGNED = "misaligned"

ALIGNMENT_RANK = {MISALIGNED: 0, ALIGNED_UNDER_APPROVAL: 1, ALIGNED: 2}

DEMONSTRATED = "demonstrated"
UNDEMONSTRATED = "within-window-undemonstrated"
OUTSIDE_WINDOW = "outside-window"

CONDITION_RANK = {OUTSIDE_WINDOW: 0, UNDEMONSTRATED: 1, DEMONSTRATED: 2}

TEST_ALIGNED = "test-aligned"
TEST_ALIGNED_UNDER_APPROVAL = "test-aligned-under-approval"
TEST_NOT_ALIGNED = "test-not-aligned"

TEST_RANK = {
    TEST_NOT_ALIGNED: 0,
    TEST_ALIGNED_UNDER_APPROVAL: 1,
    TEST_ALIGNED: 2,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A margin is a difference of declared decimal quantities, so a
    condition that sits exactly on its bound can evaluate a unit in the
    last place below zero on one platform and on it on another. The
    comparison absorbs that; the declared values are untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def method_alignment(method_source, approval_reference=None):
    """Decide whether the declared test method is one the drawing allows."""
    source = _require_choice("method_source", method_source, METHOD_SOURCES)
    if approval_reference is not None:
        approval_reference = _require_label("approval_reference", approval_reference)
    findings = []

    if source == "approved-equivalent":
        if approval_reference is None:
            raise ValueError(
                "a method declared as an approved equivalent must cite the "
                "approval that authorises it; the name alone is not the approval"
            )
        findings.append(
            "an equivalent method stands in for the drawing method under "
            "approval %s; the substitution travels with the result" % approval_reference
        )
        return {
            "alignment": ALIGNED_UNDER_APPROVAL,
            "approval_reference": approval_reference,
            "findings": findings,
        }

    if source == "supplier-internal":
        findings.append(
            "the method is a house procedure the drawing neither names nor "
            "invokes, so the result is not a result against the drawing"
        )
        return {
            "alignment": MISALIGNED,
            "approval_reference": None,
            "findings": findings,
        }

    if approval_reference is not None:
        findings.append(
            "an approval is cited for a method the drawing already allows; "
            "the approval is redundant and can be dropped from the record"
        )
    return {
        "alignment": ALIGNED,
        "approval_reference": approval_reference,
        "findings": findings,
    }


def condition_margin(condition):
    """Guard-band one declared condition by the uncertainty that recorded it."""
    if not isinstance(condition, dict):
        raise ValueError("condition must be a mapping, got %r" % (condition,))
    kind = _require_label("condition kind", condition.get("kind"))
    specified = _require_number("specified_value", condition.get("specified_value"))
    declared = _require_number("declared_value", condition.get("declared_value"))
    half_window = _require_non_negative("half_window", condition.get("half_window"))
    uncertainty = _require_non_negative("uncertainty", condition.get("uncertainty"))
    deviation = declared - specified
    offset = abs(deviation)
    findings = []

    if half_window == 0.0:
        if uncertainty > 0.0:
            raise ValueError(
                "condition %r declares an exact value with no tolerance but an "
                "instrument uncertainty of %r; an exact value cannot be "
                "demonstrated by an instrument that cannot resolve it"
                % (kind, uncertainty)
            )
        matched = math.isclose(
            declared, specified, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        )
        if not matched:
            findings.append(
                "%s: the drawing fixes this value exactly and the test "
                "declared a different one" % kind
            )
        return {
            "kind": kind,
            "deviation": deviation,
            "margin": 0.0 if matched else -offset,
            "window_usage": 0.0 if matched else 1.0,
            "verdict": DEMONSTRATED if matched else OUTSIDE_WINDOW,
            "findings": findings,
        }

    margin = half_window - offset - uncertainty
    usage = (offset + uncertainty) / half_window

    if not _at_least(half_window - offset, 0.0):
        verdict = OUTSIDE_WINDOW
        findings.append(
            "%s: the declared setpoint is outside the drawing window before "
            "any measurement uncertainty is applied" % kind
        )
    elif _at_least(margin, 0.0):
        verdict = DEMONSTRATED
    else:
        verdict = UNDEMONSTRATED
        findings.append(
            "%s: the setpoint fits the drawing window but the recording "
            "uncertainty pushes the interval past it, so the condition is "
            "declared rather than demonstrated" % kind
        )
    return {
        "kind": kind,
        "deviation": deviation,
        "margin": margin,
        "window_usage": usage,
        "verdict": verdict,
        "findings": findings,
    }


def matrix_coverage(declared_ids, required_ids):
    """Compare the tests the matrix declares against the tests the drawing calls."""
    if not isinstance(declared_ids, (list, tuple)):
        raise ValueError("declared_ids must be a sequence")
    if not isinstance(required_ids, (list, tuple)) or not required_ids:
        raise ValueError(
            "required_ids must be a non-empty sequence; a drawing that calls "
            "no test gives the matrix nothing to be graded against"
        )
    declared = [_require_label("declared test id", item) for item in declared_ids]
    required = [_require_label("required test id", item) for item in required_ids]
    if len(set(declared)) != len(declared):
        raise ValueError("a test identifier is declared twice in the matrix")
    if len(set(required)) != len(required):
        raise ValueError("a test identifier is required twice by the drawing")
    missing = sorted(set(required) - set(declared))
    extra = sorted(set(declared) - set(required))
    covered = len(set(required) & set(declared))
    return {
        "required": sorted(required),
        "declared": sorted(declared),
        "missing": missing,
        "undeclared_by_drawing": extra,
        "coverage": covered / len(required),
    }


def assess_test(test):
    """Grade one declared test: method first, then every condition."""
    if not isinstance(test, dict):
        raise ValueError("test must be a mapping, got %r" % (test,))
    test_id = _require_label("test id", test.get("test_id"))
    method = method_alignment(
        test.get("method_source"), test.get("approval_reference")
    )
    conditions = test.get("conditions")
    if not isinstance(conditions, (list, tuple)) or not conditions:
        raise ValueError(
            "test %r declares no conditions; an empty condition list is an "
            "unspecified test, not a compliant one" % test_id
        )
    findings = ["%s: %s" % (test_id, f) for f in method["findings"]]
    evaluated = []
    kinds = set()
    for condition in conditions:
        result = condition_margin(condition)
        if result["kind"] in kinds:
            raise ValueError(
                "test %r declares condition %r twice" % (test_id, result["kind"])
            )
        kinds.add(result["kind"])
        evaluated.append(result)
        findings.extend("%s: %s" % (test_id, f) for f in result["findings"])

    worst_condition = min(CONDITION_RANK[c["verdict"]] for c in evaluated)
    governing = max(evaluated, key=lambda c: (c["window_usage"], c["kind"]))

    if method["alignment"] == MISALIGNED:
        verdict = TEST_NOT_ALIGNED
    elif worst_condition == CONDITION_RANK[OUTSIDE_WINDOW]:
        verdict = TEST_NOT_ALIGNED
    elif worst_condition == CONDITION_RANK[UNDEMONSTRATED]:
        verdict = TEST_ALIGNED_UNDER_APPROVAL
    elif method["alignment"] == ALIGNED_UNDER_APPROVAL:
        verdict = TEST_ALIGNED_UNDER_APPROVAL
    else:
        verdict = TEST_ALIGNED

    return {
        "test_id": test_id,
        "method_alignment": method["alignment"],
        "approval_reference": method["approval_reference"],
        "conditions": evaluated,
        "governing_condition": governing["kind"],
        "worst_margin": min(c["margin"] for c in evaluated),
        "verdict": verdict,
        "findings": findings,
    }


def assess_test_matrix(case):
    """Full clause 6.1.2 roll-up of a cell assembly test matrix."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    drawing = _require_label("drawing_reference", case.get("drawing_reference"))
    tests = case.get("tests")
    if not isinstance(tests, (list, tuple)) or not tests:
        raise ValueError("case must carry a non-empty tests sequence")
    assessments = []
    findings = []
    seen = set()
    for test in tests:
        assessment = assess_test(test)
        if assessment["test_id"] in seen:
            raise ValueError(
                "test %r appears twice in the matrix" % assessment["test_id"]
            )
        seen.add(assessment["test_id"])
        assessments.append(assessment)
        findings.extend(assessment["findings"])

    coverage = matrix_coverage(
        [a["test_id"] for a in assessments], case.get("required_test_ids")
    )
    for item in coverage["missing"]:
        findings.append(
            "the drawing calls test %s and the matrix never declares it; an "
            "absent test raises no deviation and passes every band" % item
        )

    worst = min(TEST_RANK[a["verdict"]] for a in assessments)
    verdict = next(k for k, v in TEST_RANK.items() if v == worst)
    if coverage["missing"] and verdict == TEST_ALIGNED:
        verdict = TEST_ALIGNED_UNDER_APPROVAL
    weakest = min(
        assessments,
        key=lambda a: (TEST_RANK[a["verdict"]], a["worst_margin"], a["test_id"]),
    )
    not_aligned = [a["test_id"] for a in assessments if a["verdict"] == TEST_NOT_ALIGNED]
    return {
        "drawing_reference": drawing,
        "assessments": assessments,
        "coverage": coverage,
        "verdict": verdict,
        "weakest_test": weakest["test_id"],
        "not_aligned_tests": not_aligned,
        "aligned_share": (len(assessments) - len(not_aligned)) / len(assessments),
        "findings": findings,
    }
