#!/usr/bin/env python3
"""Acceptance principles and allowed modifications for two-phase hardware.

Anchor: ECSS-E-ST-31-02 clause 4.5 and its table of design modifications
permitted on acceptance hardware (table 4-1). The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Acceptance hardware is not qualification hardware. It is built to a
design that has already been qualified, it is tested at levels that sit
inside the qualified envelope, and it is allowed to differ from the
qualified article only in ways the standard names. A change outside that
set is not an acceptance matter at all: it sends the article back to
qualification.

Every proposed change is graded to one of three dispositions, ordered by
how much it costs:

    accept-as-is       the change is inside what acceptance permits
    delta-acceptance   permitted, but it adds an acceptance test
    requalification    outside acceptance; the qualified basis is broken

Where a change is graded against a qualified span, the grade depends on
whether the new value sits inside that span. Where it is not, the grade
is fixed by the kind of change alone: a wick or a fluid change breaks
the qualified basis whatever the numbers say.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCEPT_AS_IS = "accept-as-is"
DELTA_ACCEPTANCE = "delta-acceptance"
REQUALIFICATION = "requalification"

DISPOSITION_ORDER = (ACCEPT_AS_IS, DELTA_ACCEPTANCE, REQUALIFICATION)

BASELINE_ACCEPTANCE_TESTS = (
    "proof-pressure-test",
    "leak-test",
    "thermal-performance-test",
    "workmanship-vibration-test",
)

# Table 4-1, paraphrased to a policy per kind of change. range_relevant
# says whether a qualified span decides the grade; added_tests are the
# acceptance tests the change brings with it when it is permitted.
MODIFICATION_POLICY = {
    "adiabatic-length-change": {
        "range_relevant": True,
        "within": ACCEPT_AS_IS,
        "outside": REQUALIFICATION,
        "added_tests": (),
    },
    "evaporator-length-change": {
        "range_relevant": True,
        "within": DELTA_ACCEPTANCE,
        "outside": REQUALIFICATION,
        "added_tests": ("transport-capability-test",),
    },
    "bend-radius-change": {
        "range_relevant": True,
        "within": DELTA_ACCEPTANCE,
        "outside": REQUALIFICATION,
        "added_tests": ("transport-capability-test",),
    },
    "envelope-wall-thickness-change": {
        "range_relevant": True,
        "within": DELTA_ACCEPTANCE,
        "outside": REQUALIFICATION,
        "added_tests": ("proof-pressure-test",),
    },
    "fluid-charge-change": {
        "range_relevant": True,
        "within": DELTA_ACCEPTANCE,
        "outside": REQUALIFICATION,
        "added_tests": ("thermal-performance-test", "transport-capability-test"),
    },
    "mounting-interface-change": {
        "range_relevant": False,
        "fixed": DELTA_ACCEPTANCE,
        "added_tests": ("interface-conductance-test",),
    },
    "external-finish-change": {
        "range_relevant": False,
        "fixed": ACCEPT_AS_IS,
        "added_tests": (),
    },
    "identification-marking-change": {
        "range_relevant": False,
        "fixed": ACCEPT_AS_IS,
        "added_tests": (),
    },
    "wick-structure-change": {
        "range_relevant": False,
        "fixed": REQUALIFICATION,
        "added_tests": (),
    },
    "working-fluid-change": {
        "range_relevant": False,
        "fixed": REQUALIFICATION,
        "added_tests": (),
    },
    "envelope-material-change": {
        "range_relevant": False,
        "fixed": REQUALIFICATION,
        "added_tests": (),
    },
}

MODIFICATION_TYPES = tuple(sorted(MODIFICATION_POLICY))

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (name, value))
    return tuple(value)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_modification(modification):
    """Check one proposed change on acceptance hardware is gradeable."""
    if not isinstance(modification, dict):
        raise ValueError("modification must be a mapping, got %r" % (modification,))
    kind = _require_text("modification type", modification.get("type"))
    if kind not in MODIFICATION_POLICY:
        raise ValueError(
            "unknown modification type %r; it is not in the permitted-change "
            "table and cannot be graded as an acceptance matter" % kind
        )
    policy = MODIFICATION_POLICY[kind]
    if policy["range_relevant"]:
        value = _require_number("%s value" % kind, modification.get("value"))
        low = _require_number("%s qualified_min" % kind, modification.get("qualified_min"))
        high = _require_number(
            "%s qualified_max" % kind, modification.get("qualified_max")
        )
        if high < low:
            raise ValueError(
                "%s declares a qualified span from %g to %g, which is inverted"
                % (kind, low, high)
            )
        del value
    return modification


def within_qualified_span(modification):
    """Say whether a range-graded change sits inside its qualified span."""
    validate_modification(modification)
    kind = modification["type"]
    if not MODIFICATION_POLICY[kind]["range_relevant"]:
        raise ValueError("%s is not graded against a qualified span" % kind)
    value = float(modification["value"])
    return _at_least(value, float(modification["qualified_min"])) and _at_most(
        value, float(modification["qualified_max"])
    )


def disposition_for(modification):
    """Grade one proposed change to a disposition, with its added tests."""
    validate_modification(modification)
    kind = modification["type"]
    policy = MODIFICATION_POLICY[kind]
    if policy["range_relevant"]:
        inside = within_qualified_span(modification)
        disposition = policy["within"] if inside else policy["outside"]
    else:
        inside = None
        disposition = policy["fixed"]
    added = tuple(policy["added_tests"]) if disposition == DELTA_ACCEPTANCE else ()
    return {
        "type": kind,
        "within_span": inside,
        "disposition": disposition,
        "added_tests": added,
    }


def most_onerous(dispositions):
    """Reduce a set of dispositions to the one that governs the article."""
    values = _require_sequence("dispositions", dispositions)
    if not values:
        return ACCEPT_AS_IS
    worst = ACCEPT_AS_IS
    for value in values:
        if value not in DISPOSITION_ORDER:
            raise ValueError("unknown disposition %r" % (value,))
        if DISPOSITION_ORDER.index(value) > DISPOSITION_ORDER.index(worst):
            worst = value
    return worst


def acceptance_test_set(graded, baseline=BASELINE_ACCEPTANCE_TESTS):
    """Baseline acceptance tests plus whatever the permitted changes add."""
    tests = set(_require_sequence("baseline", baseline))
    if not tests:
        raise ValueError("the baseline acceptance test set is empty")
    for item in _require_sequence("graded modifications", graded):
        if not isinstance(item, dict):
            raise ValueError("graded modification must be a mapping, got %r" % (item,))
        tests.update(_require_sequence("added_tests", item.get("added_tests", ())))
    return tuple(sorted(tests))


def audit_acceptance_levels(acceptance, qualification):
    """Check the acceptance levels sit inside the qualified envelope."""
    for name, block in (("acceptance", acceptance), ("qualification", qualification)):
        if not isinstance(block, dict):
            raise ValueError("%s levels must be a mapping, got %r" % (name, block))
    acc_min = _require_positive("acceptance min_k", acceptance.get("min_k"))
    acc_max = _require_positive("acceptance max_k", acceptance.get("max_k"))
    qual_min = _require_positive("qualification min_k", qualification.get("min_k"))
    qual_max = _require_positive("qualification max_k", qualification.get("max_k"))
    acc_asd = _require_positive(
        "acceptance asd_g2_per_hz", acceptance.get("asd_g2_per_hz")
    )
    qual_asd = _require_positive(
        "qualification asd_g2_per_hz", qualification.get("asd_g2_per_hz")
    )
    findings = []
    if not _at_least(acc_min, qual_min):
        findings.append(
            "the acceptance cold limit %g K is colder than the qualified %g K"
            % (acc_min, qual_min)
        )
    if not _at_most(acc_max, qual_max):
        findings.append(
            "the acceptance hot limit %g K is hotter than the qualified %g K"
            % (acc_max, qual_max)
        )
    if not _at_most(acc_asd, qual_asd):
        findings.append(
            "the acceptance density %g g2/Hz is above the qualified %g g2/Hz"
            % (acc_asd, qual_asd)
        )
    return {"inside_qualified_envelope": not findings, "findings": findings}


def apply_acceptance_principles(case):
    """Full clause 4.5 acceptance grading with a delivery disposition."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    _require_text("article", case.get("article"))
    modifications = _require_sequence("modifications", case.get("modifications", ()))
    graded = [disposition_for(item) for item in modifications]
    overall = most_onerous([item["disposition"] for item in graded])
    findings = []
    for item in graded:
        if item["disposition"] == REQUALIFICATION:
            findings.append(
                "%s is outside what acceptance permits and returns the article "
                "to qualification" % item["type"]
            )
    acceptance = case.get("acceptance_levels")
    qualification = case.get("qualification_levels")
    if acceptance is not None and qualification is not None:
        level_audit = audit_acceptance_levels(acceptance, qualification)
        findings.extend(level_audit["findings"])
    tests = acceptance_test_set(
        graded, case.get("baseline_tests", BASELINE_ACCEPTANCE_TESTS)
    )
    return {
        "article": case["article"].strip(),
        "graded": graded,
        "disposition": overall,
        "acceptance_tests": tests,
        "deliverable_as_acceptance_hardware": overall != REQUALIFICATION
        and not findings,
        "findings": findings,
    }
