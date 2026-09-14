#!/usr/bin/env python3
"""Testing of external protection diodes against their own drawing.

Anchor: ECSS-E-ST-20-08C clause 9.2.1.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An external protection diode is not tested to a generic diode routine. The
conditions and the methods are the ones its own dedicated source control
drawing defines, so the clause creates binding work rather than
measurement work:

    bind       every declared test names the document its method and its
               conditions came from, and only the part's OWN source
               control drawing governs. A house test specification, a
               supplier datasheet or nothing at all leaves the test
               ungoverned however carefully it was run
    stand      a drawing is read for its issue as well as its number. A
               test run to an issue the governing one has replaced was
               run to a definition nobody works to any more
    belong     a drawing raised for a different part number is somebody
               else's drawing. It reads as a citation, it passes every
               presence check, and it defines a different diode
    follow     with the drawing settled, the declared method has to be the
               drawing's method, and only then are the conditions worth
               comparing at all
    cover      a test the drawing defines and the programme never ran is
               a hole exactly where nobody is looking

Conditions are compared under their own sense, because the same numeric
gap means opposite things. A severity floor is weakened by a smaller
number, a permitted ceiling is weakened by a larger one, and a set point
with a tolerance is off its baseline in either direction. A relaxation
leaves the diode less tested than its drawing asks; an escalation
over-tests delivered parts and is reported as its own thing, since
whether it blocks is a project position rather than a default.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "CONDITION_ESCALATED",
    "CONDITION_OFF_BASELINE",
    "CONDITION_RELAXED",
    "CONDITION_REUSED",
    "CONDITION_SENSES",
    "DEFAULT_CARRY_POLICY",
    "DOCUMENT_SOURCES",
    "PROGRAMME_ACCEPTED",
    "PROGRAMME_OPEN",
    "TEST_CONDITION_ESCALATED",
    "TEST_CONDITION_INVENTED",
    "TEST_CONDITION_OFF_BASELINE",
    "TEST_CONDITION_OMITTED",
    "TEST_CONDITION_RELAXED",
    "TEST_CONFORMING",
    "TEST_DRAWING_SUPERSEDED",
    "TEST_DRAWING_UNRESOLVED",
    "TEST_FOREIGN_DRAWING",
    "TEST_METHOD_SUBSTITUTED",
    "VERDICT_RANK",
    "assess_declared_test",
    "compare_condition",
    "evaluate_diode_test_programme",
    "normalize_sense",
    "validate_carry_policy",
    "validate_declared_test",
    "validate_drawing",
    "validate_drawings",
]

DOCUMENT_SOURCES = (
    "source-control-drawing",
    "in-house-test-specification",
    "supplier-datasheet",
    "undeclared",
)

CONDITION_SENSES = ("floor", "ceiling", "nominal")

CONDITION_REUSED = "condition-reused"
CONDITION_RELAXED = "condition-relaxed"
CONDITION_ESCALATED = "condition-escalated"
CONDITION_OFF_BASELINE = "condition-off-baseline"

TEST_DRAWING_UNRESOLVED = "test-has-no-governing-drawing"
TEST_FOREIGN_DRAWING = "test-cites-another-parts-drawing"
TEST_DRAWING_SUPERSEDED = "test-cites-a-superseded-drawing-issue"
TEST_METHOD_SUBSTITUTED = "test-method-substituted"
TEST_CONDITION_OMITTED = "test-omits-a-drawing-condition"
TEST_CONDITION_INVENTED = "test-adds-a-condition-the-drawing-lacks"
TEST_CONDITION_RELAXED = "test-condition-relaxed"
TEST_CONDITION_OFF_BASELINE = "test-condition-off-baseline"
TEST_CONDITION_ESCALATED = "test-condition-escalated"
TEST_CONFORMING = "test-conforms-to-drawing"

# Worst first. A test is reported at its worst standing, because a
# substituted method makes every condition underneath it incomparable and
# an unresolved drawing makes the whole comparison meaningless.
VERDICT_RANK = (
    TEST_DRAWING_UNRESOLVED,
    TEST_FOREIGN_DRAWING,
    TEST_DRAWING_SUPERSEDED,
    TEST_METHOD_SUBSTITUTED,
    TEST_CONDITION_OMITTED,
    TEST_CONDITION_INVENTED,
    TEST_CONDITION_RELAXED,
    TEST_CONDITION_OFF_BASELINE,
    TEST_CONDITION_ESCALATED,
    TEST_CONFORMING,
)

PROGRAMME_ACCEPTED = "diode-test-programme-follows-its-drawing"
PROGRAMME_OPEN = "diode-test-programme-open"

# Whether an over-test blocks is a project position, not a default; a set
# point off its baseline band is a deviation either way and blocks unless
# the project says otherwise.
DEFAULT_CARRY_POLICY = {
    "escalation_blocks": False,
    "off_baseline_blocks": True,
}

# Declared condition values are routinely arrived at by arithmetic -- a
# step count multiplied out, a band summed up -- so a value meant to sit
# exactly on a drawing bound can land a unit in the last place either side
# of it. The comparisons absorb that while the drawing value stays as
# drawn.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _number(label, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (label, value))
    return float(value)


def _non_negative(label, value):
    number = _number(label, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _key(value, label):
    """Return a trimmed, lowercased key for matching."""
    return _text(label, value).lower()


def _issue(label, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer issue number, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %d" % (label, value))
    return value


def _flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _same(a, b):
    return math.isclose(a, b, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def normalize_sense(sense, label="sense"):
    """Return the sense a condition is read in."""
    if not isinstance(sense, str):
        raise ValueError("%s must be a string, got %r" % (label, sense))
    cleaned = sense.strip().lower()
    if cleaned not in CONDITION_SENSES:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, sense, ", ".join(CONDITION_SENSES))
        )
    return cleaned


def _normalize_source(source, label="governing_document"):
    if not isinstance(source, str):
        raise ValueError("%s must be a string, got %r" % (label, source))
    cleaned = source.strip().lower()
    if cleaned not in DOCUMENT_SOURCES:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, source, ", ".join(DOCUMENT_SOURCES))
        )
    return cleaned


def validate_carry_policy(policy=None):
    """Return the carry positions merged onto the defaults."""
    merged = dict(DEFAULT_CARRY_POLICY)
    if policy is None:
        return merged
    if not isinstance(policy, dict):
        raise ValueError("carry policy must be a mapping or None")
    unknown = set(policy) - set(merged)
    if unknown:
        raise ValueError("carry policy carries unknown key(s): %s"
                         % ", ".join(sorted(unknown)))
    for key in merged:
        if key in policy:
            merged[key] = _flag(key, policy[key])
    return merged


def _validate_reference_condition(condition, label):
    if not isinstance(condition, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("name", "sense", "value"):
        if key not in condition:
            raise ValueError("%s missing required key '%s'" % (label, key))
    sense = normalize_sense(condition["sense"], "%s sense" % label)
    tolerance = condition.get("tolerance", 0.0)
    tolerance = _non_negative("%s tolerance" % label, tolerance)
    if sense == "nominal" and tolerance <= 0.0:
        raise ValueError(
            "%s is a set point, so it must carry a positive tolerance" % label
        )
    return {
        "name": _key(condition["name"], "%s name" % label),
        "sense": sense,
        "value": _number("%s value" % label, condition["value"]),
        "tolerance": tolerance,
    }


def _validate_reference_test(test, label):
    if not isinstance(test, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("test_name", "method"):
        if key not in test:
            raise ValueError("%s missing required key '%s'" % (label, key))
    conditions = test.get("conditions", ())
    if isinstance(conditions, dict) or not isinstance(conditions, (list, tuple)):
        raise ValueError("%s conditions must be a sequence" % label)
    resolved = {}
    for index, condition in enumerate(conditions):
        entry = _validate_reference_condition(condition, "%s conditions[%d]"
                                              % (label, index))
        if entry["name"] in resolved:
            raise ValueError("%s names condition %s twice" % (label, entry["name"]))
        resolved[entry["name"]] = entry
    return {
        "test_name": _key(test["test_name"], "%s test_name" % label),
        "method": _key(test["method"], "%s method" % label),
        "conditions": resolved,
    }


def validate_drawing(drawing, label="drawing"):
    """Return one validated source control drawing."""
    if not isinstance(drawing, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("drawing_id", "part_number", "issue", "governing_issue", "tests"):
        if key not in drawing:
            raise ValueError("%s missing required key '%s'" % (label, key))
    tests_raw = drawing["tests"]
    if not isinstance(tests_raw, (list, tuple)) or not tests_raw:
        raise ValueError("%s must define at least one test" % label)
    tests = {}
    for index, test in enumerate(tests_raw):
        entry = _validate_reference_test(test, "%s tests[%d]" % (label, index))
        if entry["test_name"] in tests:
            raise ValueError("%s defines test %s twice" % (label, entry["test_name"]))
        tests[entry["test_name"]] = entry
    return {
        "drawing_id": _key(drawing["drawing_id"], "%s drawing_id" % label),
        "part_number": _key(drawing["part_number"], "%s part_number" % label),
        "issue": _issue("%s issue" % label, drawing["issue"]),
        "governing_issue": _issue("%s governing_issue" % label,
                                  drawing["governing_issue"]),
        "tests": tests,
    }


def validate_drawings(drawings):
    """Return every validated drawing, keyed by its identifier."""
    if not isinstance(drawings, (list, tuple)) or not drawings:
        raise ValueError("drawings must be a non-empty sequence")
    resolved = {}
    for index, drawing in enumerate(drawings):
        entry = validate_drawing(drawing, "drawings[%d]" % index)
        if entry["drawing_id"] in resolved:
            raise ValueError("drawing %s appears twice" % entry["drawing_id"])
        resolved[entry["drawing_id"]] = entry
    return resolved


def validate_declared_test(test, label="declared test"):
    """Return one validated declared test from the programme."""
    if not isinstance(test, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("test_name", "governing_document", "method"):
        if key not in test:
            raise ValueError("%s missing required key '%s'" % (label, key))
    source = _normalize_source(test["governing_document"],
                               "%s governing_document" % label)
    drawing_id = test.get("drawing_id")
    if source == "source-control-drawing":
        drawing_id = _key(drawing_id, "%s drawing_id" % label)
    elif drawing_id is not None:
        drawing_id = _key(drawing_id, "%s drawing_id" % label)
    conditions_raw = test.get("conditions", ())
    if isinstance(conditions_raw, dict) or not isinstance(conditions_raw,
                                                          (list, tuple)):
        raise ValueError("%s conditions must be a sequence" % label)
    conditions = {}
    for index, condition in enumerate(conditions_raw):
        if not isinstance(condition, dict):
            raise ValueError("%s conditions[%d] must be a mapping" % (label, index))
        for key in ("name", "value"):
            if key not in condition:
                raise ValueError(
                    "%s conditions[%d] missing required key '%s'" % (label, index, key)
                )
        name = _key(condition["name"], "%s conditions[%d] name" % (label, index))
        if name in conditions:
            raise ValueError("%s names condition %s twice" % (label, name))
        conditions[name] = _number(
            "%s conditions[%d] value" % (label, index), condition["value"]
        )
    return {
        "test_name": _key(test["test_name"], "%s test_name" % label),
        "governing_document": source,
        "drawing_id": drawing_id,
        "declared_issue": (
            _issue("%s declared_issue" % label, test["declared_issue"])
            if test.get("declared_issue") is not None
            else None
        ),
        "method": _key(test["method"], "%s method" % label),
        "conditions": conditions,
    }


def compare_condition(declared_value, reference):
    """Say how one declared condition stands against the drawing value.

    The sense decides the direction of weakening: a floor is weakened by a
    smaller number, a ceiling by a larger one, and a set point is off its
    baseline in either direction.
    """
    value = _number("declared condition value", declared_value)
    sense = reference["sense"]
    drawn = reference["value"]
    if sense == "nominal":
        if abs(value - drawn) <= reference["tolerance"] or _same(
            abs(value - drawn), reference["tolerance"]
        ):
            state = CONDITION_REUSED
        else:
            state = CONDITION_OFF_BASELINE
    elif sense == "floor":
        if _same(value, drawn):
            state = CONDITION_REUSED
        elif value < drawn:
            state = CONDITION_RELAXED
        else:
            state = CONDITION_ESCALATED
    else:
        if _same(value, drawn):
            state = CONDITION_REUSED
        elif value > drawn:
            state = CONDITION_RELAXED
        else:
            state = CONDITION_ESCALATED
    return {
        "name": reference["name"],
        "sense": sense,
        "declared_value": value,
        "drawing_value": drawn,
        "tolerance": reference["tolerance"],
        "state": state,
    }


def _rank(state):
    return VERDICT_RANK.index(state)


def assess_declared_test(declared, drawings, part_number, policy=None):
    """Grade one declared test against the drawing it claims to follow."""
    carry = validate_carry_policy(policy)
    test = validate_declared_test(declared)
    part_number = _key(part_number, "part_number")
    reasons = []
    conditions = ()
    omitted = ()
    invented = ()
    drawing = None

    if test["governing_document"] != "source-control-drawing":
        reasons.append(
            "test %s took its method and conditions from a %s rather than the "
            "part's own source control drawing"
            % (test["test_name"], test["governing_document"].replace("-", " "))
        )
        state = TEST_DRAWING_UNRESOLVED
    elif test["drawing_id"] not in drawings:
        reasons.append(
            "test %s cites drawing %s, which is not among the drawings supplied"
            % (test["test_name"], test["drawing_id"])
        )
        state = TEST_DRAWING_UNRESOLVED
    else:
        drawing = drawings[test["drawing_id"]]
        if drawing["part_number"] != part_number:
            reasons.append(
                "test %s cites drawing %s, raised for part %s and not for %s"
                % (test["test_name"], drawing["drawing_id"],
                   drawing["part_number"], part_number)
            )
            state = TEST_FOREIGN_DRAWING
        elif test["test_name"] not in drawing["tests"]:
            reasons.append(
                "test %s is not a test drawing %s defines"
                % (test["test_name"], drawing["drawing_id"])
            )
            state = TEST_DRAWING_UNRESOLVED
        else:
            cited_issue = (
                test["declared_issue"]
                if test["declared_issue"] is not None
                else drawing["issue"]
            )
            if cited_issue < drawing["governing_issue"]:
                reasons.append(
                    "test %s was run to drawing %s issue %d, superseded by issue %d"
                    % (test["test_name"], drawing["drawing_id"], cited_issue,
                       drawing["governing_issue"])
                )
                state = TEST_DRAWING_SUPERSEDED
            else:
                reference = drawing["tests"][test["test_name"]]
                if test["method"] != reference["method"]:
                    reasons.append(
                        "test %s ran method '%s' where drawing %s defines '%s', so "
                        "its conditions are not comparable"
                        % (test["test_name"], test["method"],
                           drawing["drawing_id"], reference["method"])
                    )
                    state = TEST_METHOD_SUBSTITUTED
                else:
                    omitted = tuple(
                        sorted(set(reference["conditions"]) - set(test["conditions"]))
                    )
                    invented = tuple(
                        sorted(set(test["conditions"]) - set(reference["conditions"]))
                    )
                    compared = []
                    for name in sorted(
                        set(reference["conditions"]) & set(test["conditions"])
                    ):
                        compared.append(
                            compare_condition(
                                test["conditions"][name], reference["conditions"][name]
                            )
                        )
                    conditions = tuple(compared)
                    for name in omitted:
                        reasons.append(
                            "test %s omits condition %s, which drawing %s defines"
                            % (test["test_name"], name, drawing["drawing_id"])
                        )
                    for name in invented:
                        reasons.append(
                            "test %s adds condition %s, which drawing %s does not "
                            "define" % (test["test_name"], name,
                                        drawing["drawing_id"])
                        )
                    for entry in conditions:
                        if entry["state"] == CONDITION_RELAXED:
                            reasons.append(
                                "test %s relaxes condition %s from %.6g to %.6g"
                                % (test["test_name"], entry["name"],
                                   entry["drawing_value"], entry["declared_value"])
                            )
                        elif entry["state"] == CONDITION_OFF_BASELINE:
                            reasons.append(
                                "test %s sets condition %s to %.6g, outside the "
                                "%.6g band around %.6g"
                                % (test["test_name"], entry["name"],
                                   entry["declared_value"], entry["tolerance"],
                                   entry["drawing_value"])
                            )
                        elif entry["state"] == CONDITION_ESCALATED:
                            reasons.append(
                                "test %s over-tests condition %s, %.6g against the "
                                "drawing's %.6g"
                                % (test["test_name"], entry["name"],
                                   entry["declared_value"], entry["drawing_value"])
                            )
                    states = [e["state"] for e in conditions]
                    if omitted:
                        state = TEST_CONDITION_OMITTED
                    elif invented:
                        state = TEST_CONDITION_INVENTED
                    elif CONDITION_RELAXED in states:
                        state = TEST_CONDITION_RELAXED
                    elif CONDITION_OFF_BASELINE in states:
                        state = TEST_CONDITION_OFF_BASELINE
                    elif CONDITION_ESCALATED in states:
                        state = TEST_CONDITION_ESCALATED
                    else:
                        state = TEST_CONFORMING

    if state == TEST_CONDITION_ESCALATED and not carry["escalation_blocks"]:
        blocking = False
    elif state == TEST_CONDITION_OFF_BASELINE and not carry["off_baseline_blocks"]:
        blocking = False
    else:
        blocking = state != TEST_CONFORMING

    return {
        "test_name": test["test_name"],
        "governing_document": test["governing_document"],
        "drawing_id": test["drawing_id"],
        "part_number": part_number,
        "method": test["method"],
        "state": state,
        "blocking": blocking,
        "conditions": conditions,
        "omitted_conditions": omitted,
        "invented_conditions": invented,
        "reasons": tuple(reasons),
    }


def evaluate_diode_test_programme(spec):
    """Run the clause 9.2.1.2.2 check over one declared test programme.

    spec keys: programme_id, part_number, drawings, declared_tests;
    optional carry_policy.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("programme_id", "part_number", "drawings", "declared_tests"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    programme_id = _text("programme_id", spec["programme_id"])
    part_number = _key(spec["part_number"], "part_number")
    drawings = validate_drawings(spec["drawings"])
    carry = validate_carry_policy(spec.get("carry_policy"))

    declared_raw = spec["declared_tests"]
    if not isinstance(declared_raw, (list, tuple)) or not declared_raw:
        raise ValueError("a programme must declare at least one test")

    assessed = []
    seen = set()
    for declared in declared_raw:
        entry = assess_declared_test(declared, drawings, part_number, carry)
        if entry["test_name"] in seen:
            raise ValueError("test %s is declared twice" % entry["test_name"])
        seen.add(entry["test_name"])
        assessed.append(entry)
    assessed.sort(key=lambda e: (_rank(e["state"]), e["test_name"]))

    own_drawings = [d for d in drawings.values() if d["part_number"] == part_number]
    required = set()
    for drawing in own_drawings:
        required.update(drawing["tests"])
    uncovered = tuple(sorted(required - seen))

    findings = []
    for entry in assessed:
        if entry["blocking"]:
            findings.extend(entry["reasons"])
    for test_name in uncovered:
        findings.append(
            "programme %s never ran test %s, which the drawing for part %s defines"
            % (programme_id, test_name, part_number)
        )
    if not own_drawings:
        findings.append(
            "programme %s supplies no source control drawing raised for part %s"
            % (programme_id, part_number)
        )

    conforming = sum(1 for e in assessed if e["state"] == TEST_CONFORMING)
    return {
        "programme_id": programme_id,
        "part_number": part_number,
        "tests": tuple(assessed),
        "uncovered_tests": uncovered,
        "conforming_count": conforming,
        "declared_count": len(assessed),
        "conformance_fraction": conforming / float(len(assessed)),
        "weakest_test": assessed[0]["test_name"] if assessed else None,
        "weakest_state": assessed[0]["state"] if assessed else None,
        "carry_policy": carry,
        "findings": tuple(findings),
        "verdict": PROGRAMME_ACCEPTED if not findings else PROGRAMME_OPEN,
        "accepted": not findings,
    }
