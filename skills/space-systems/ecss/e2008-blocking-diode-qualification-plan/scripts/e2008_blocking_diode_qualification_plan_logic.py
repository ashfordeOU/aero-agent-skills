#!/usr/bin/env python3
"""A blocking diode qualification programme is assembled from a fixed test table.

Anchor: ECSS-E-ST-20-08C clause 12.5.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The programme is not written from scratch. It is assembled: the applicable
table lists the tests a blocking diode qualification owes, and the plan is
the act of taking those tests, giving each one a specimen count and a place
in a sequence, and saying for each whether it will be run or carried by
similarity to a part already qualified. The plan is therefore graded before
a single specimen is drawn, and the gradeable content is entirely structural.

Four things can go wrong when a plan is assembled, and they need different
work:

    omission    a test the table lists as owed appears nowhere in the plan
    invention   a test appears in the plan that the table never listed, so
                specimens and schedule are being spent outside the programme
    undersizing a test is planned on fewer specimens than the table asks
                for, which reads as planned until the lot is drawn
    sequencing  a test is planned before the test it depends on, which is
                invisible in a list sorted by test identifier and fatal in
                a campaign where one specimen set walks the whole sequence

A similarity claim is the fifth. It is not a shortcut, it is an argument,
and an argument with no heritage part and no delta justification behind it
is an omission wearing a different label. That is why a bare similarity
entry does not count towards coverage here.

The specimen demand is totalled from the plan as a number, per group and
overall, because a plan whose arithmetic nobody did is a plan that fails at
the lot draw rather than at review.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TEST_TABLE_KEYS = ("test_id", "test_group", "mandatory", "min_sample_count")

TEST_GROUPS = (
    "electrical-characterisation",
    "construction-analysis",
    "environmental",
    "endurance",
)

PLAN_SOURCES = ("run", "similarity")

TEST_PLANNED = "test-planned"
TEST_NOT_IN_TABLE = "test-not-in-table"
TEST_SAMPLE_COUNT_SHORT = "test-sample-count-short"
TEST_PREREQUISITE_ABSENT = "test-prerequisite-absent"
TEST_PREREQUISITE_PLANNED_LATER = "test-prerequisite-planned-later"
TEST_SIMILARITY_UNJUSTIFIED = "test-similarity-claim-unjustified"
TEST_SIMILARITY_NOT_ADMITTED = "test-similarity-not-admitted"
TEST_OMITTED = "test-omitted-from-plan"

TEST_VERDICT_RANK = (
    TEST_OMITTED,
    TEST_NOT_IN_TABLE,
    TEST_SIMILARITY_NOT_ADMITTED,
    TEST_SIMILARITY_UNJUSTIFIED,
    TEST_PREREQUISITE_ABSENT,
    TEST_PREREQUISITE_PLANNED_LATER,
    TEST_SAMPLE_COUNT_SHORT,
    TEST_PLANNED,
)

PLAN_COMPLETE = "blocking-diode-qualification-plan-complete"
PLAN_INCOMPLETE = "blocking-diode-qualification-plan-incomplete"

DEFAULT_PLAN_POLICY = {
    "require_every_mandatory_test": True,
    "admit_test_outside_table": False,
    "admit_similarity_for_mandatory_test": True,
    "require_similarity_justification": True,
    "enforce_prerequisite_order": True,
    "min_mandatory_coverage_fraction": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def validate_plan_policy(policy):
    """Check a plan assembly policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "require_every_mandatory_test",
        "admit_test_outside_table",
        "admit_similarity_for_mandatory_test",
        "require_similarity_justification",
        "enforce_prerequisite_order",
    ):
        _require_flag(key, policy.get(key))
    _require_fraction(
        "min_mandatory_coverage_fraction",
        policy.get("min_mandatory_coverage_fraction"),
    )
    return policy


def normalise_test_table(table):
    """Read the owed test list into an index keyed on the test identifier."""
    if not isinstance(table, (list, tuple)) or not table:
        raise ValueError("test table must be a non-empty sequence of mappings")
    index = {}
    for row in table:
        if not isinstance(row, dict):
            raise ValueError("test table row must be a mapping, got %r" % (row,))
        missing = sorted(key for key in TEST_TABLE_KEYS if key not in row)
        if missing:
            raise ValueError("test table row is missing %s" % ", ".join(missing))
        test_id = _require_text("test_id", row["test_id"])
        if test_id in index:
            raise ValueError("test table lists %s twice" % test_id)
        group = _require_text("test_group", row["test_group"]).lower()
        if group not in TEST_GROUPS:
            raise ValueError(
                "test_group must be one of %s, got %r" % (", ".join(TEST_GROUPS), group)
            )
        prerequisites = row.get("prerequisite_tests", [])
        if not isinstance(prerequisites, (list, tuple)):
            raise ValueError(
                "prerequisite_tests must be a sequence, got %r" % (prerequisites,)
            )
        index[test_id] = {
            "test_id": test_id,
            "test_group": group,
            "mandatory": _require_flag("mandatory", row["mandatory"]),
            "min_sample_count": _require_count(
                "min_sample_count", row["min_sample_count"], minimum=1
            ),
            "prerequisite_tests": sorted(
                _require_text("prerequisite_test", p) for p in prerequisites
            ),
        }
    for test_id, row in index.items():
        for prerequisite in row["prerequisite_tests"]:
            if prerequisite not in index:
                raise ValueError(
                    "test %s depends on %s, which the table does not list"
                    % (test_id, prerequisite)
                )
            if prerequisite == test_id:
                raise ValueError("test %s depends on itself" % test_id)
    return index


def mandatory_tests(table_index):
    """The owed tests a plan cannot drop."""
    if not isinstance(table_index, dict) or not table_index:
        raise ValueError("table index must be a non-empty mapping")
    return sorted(
        test_id for test_id, row in table_index.items() if row["mandatory"]
    )


def normalise_plan(entries):
    """Read the planned programme into sequence order, refusing a broken plan."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("plan must be a non-empty sequence of mappings")
    normalised = []
    seen_tests = set()
    seen_positions = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("plan entry must be a mapping, got %r" % (entry,))
        test_id = _require_text("test_id", entry.get("test_id"))
        if test_id in seen_tests:
            raise ValueError("plan books test %s twice" % test_id)
        seen_tests.add(test_id)
        position = _require_count(
            "sequence_position", entry.get("sequence_position"), minimum=1
        )
        if position in seen_positions:
            raise ValueError("plan books sequence position %d twice" % position)
        seen_positions.add(position)
        source = _require_text("source", entry.get("source")).lower()
        if source not in PLAN_SOURCES:
            raise ValueError(
                "source must be one of %s, got %r" % (", ".join(PLAN_SOURCES), source)
            )
        sample_count = _require_count(
            "planned_sample_count", entry.get("planned_sample_count", 0), minimum=0
        )
        heritage = entry.get("heritage_part")
        justification = entry.get("delta_justification")
        normalised.append(
            {
                "test_id": test_id,
                "sequence_position": position,
                "source": source,
                "planned_sample_count": sample_count,
                "heritage_part": None
                if heritage is None
                else _require_text("heritage_part", heritage),
                "delta_justification": None
                if justification is None
                else _require_text("delta_justification", justification),
            }
        )
    normalised.sort(key=lambda item: item["sequence_position"])
    return normalised


def similarity_argument(entry, policy=DEFAULT_PLAN_POLICY):
    """Does a similarity claim carry the heritage part and delta behind it."""
    validate_plan_policy(policy)
    if not isinstance(entry, dict):
        raise ValueError("plan entry must be a mapping, got %r" % (entry,))
    source = _require_text("source", entry.get("source")).lower()
    if source not in PLAN_SOURCES:
        raise ValueError("unknown plan source %r" % (source,))
    if source != "similarity":
        return {"claimed": False, "justified": True, "missing": []}
    missing = []
    if not entry.get("heritage_part"):
        missing.append("heritage_part")
    if not entry.get("delta_justification"):
        missing.append("delta_justification")
    if not policy["require_similarity_justification"]:
        missing = []
    return {"claimed": True, "justified": not missing, "missing": sorted(missing)}


def prerequisite_order(entry, table_index, planned_positions, policy=DEFAULT_PLAN_POLICY):
    """Do the tests this one rests on sit earlier in the planned sequence."""
    validate_plan_policy(policy)
    test_id = _require_text("test_id", entry.get("test_id"))
    position = _require_count(
        "sequence_position", entry.get("sequence_position"), minimum=1
    )
    row = table_index.get(test_id)
    if row is None:
        return {"absent": [], "late": [], "ordered": True}
    absent = []
    late = []
    for prerequisite in row["prerequisite_tests"]:
        if prerequisite not in planned_positions:
            absent.append(prerequisite)
        elif planned_positions[prerequisite] >= position:
            late.append(prerequisite)
    if not policy["enforce_prerequisite_order"]:
        late = []
    return {
        "absent": sorted(absent),
        "late": sorted(late),
        "ordered": not absent and not late,
    }


def assess_planned_test(entry, table_index, planned_positions, policy=DEFAULT_PLAN_POLICY):
    """Grade one booked test against the table row it claims to discharge."""
    validate_plan_policy(policy)
    if not isinstance(table_index, dict):
        raise ValueError("table index must be a mapping, got %r" % (table_index,))
    if not isinstance(planned_positions, dict):
        raise ValueError("planned positions must be a mapping")
    test_id = _require_text("test_id", entry.get("test_id"))
    position = _require_count(
        "sequence_position", entry.get("sequence_position"), minimum=1
    )
    source = _require_text("source", entry.get("source")).lower()
    sample_count = _require_count(
        "planned_sample_count", entry.get("planned_sample_count", 0), minimum=0
    )
    row = table_index.get(test_id)
    similarity = similarity_argument(entry, policy)
    order = prerequisite_order(entry, table_index, planned_positions, policy)

    result = {
        "test_id": test_id,
        "sequence_position": position,
        "source": source,
        "test_group": None if row is None else row["test_group"],
        "mandatory": None if row is None else row["mandatory"],
        "planned_sample_count": sample_count,
        "required_sample_count": None if row is None else row["min_sample_count"],
        "sample_shortfall": 0,
        "similarity": similarity,
        "prerequisites": order,
    }

    findings = []
    if row is None and not policy["admit_test_outside_table"]:
        verdict = TEST_NOT_IN_TABLE
        findings.append(
            "the plan books %s at position %d, and the table does not list it"
            % (test_id, position)
        )
    elif row is None:
        verdict = TEST_PLANNED
    elif (
        similarity["claimed"]
        and row["mandatory"]
        and not policy["admit_similarity_for_mandatory_test"]
    ):
        verdict = TEST_SIMILARITY_NOT_ADMITTED
        findings.append(
            "test %s is owed and the plan carries it by similarity, which this "
            "programme does not admit" % test_id
        )
    elif similarity["claimed"] and not similarity["justified"]:
        verdict = TEST_SIMILARITY_UNJUSTIFIED
        findings.append(
            "test %s is carried by similarity with no %s"
            % (test_id, " and no ".join(similarity["missing"]))
        )
    elif order["absent"]:
        verdict = TEST_PREREQUISITE_ABSENT
        findings.append(
            "test %s rests on %s, which the plan never books"
            % (test_id, ", ".join(order["absent"]))
        )
    elif order["late"]:
        verdict = TEST_PREREQUISITE_PLANNED_LATER
        findings.append(
            "test %s sits at position %d, ahead of %s it rests on"
            % (test_id, position, ", ".join(order["late"]))
        )
    elif not similarity["claimed"] and sample_count < row["min_sample_count"]:
        verdict = TEST_SAMPLE_COUNT_SHORT
        result["sample_shortfall"] = row["min_sample_count"] - sample_count
        findings.append(
            "test %s is planned on %d specimens against the %d the table asks for"
            % (test_id, sample_count, row["min_sample_count"])
        )
    else:
        verdict = TEST_PLANNED

    result["verdict"] = verdict
    result["discharged"] = verdict == TEST_PLANNED
    result["findings"] = findings
    return result


def omitted_mandatory_tests(table_index, planned_positions, policy=DEFAULT_PLAN_POLICY):
    """The owed tests the plan never booked at all."""
    validate_plan_policy(policy)
    if not isinstance(planned_positions, dict):
        raise ValueError("planned positions must be a mapping")
    if not policy["require_every_mandatory_test"]:
        return []
    return sorted(
        test_id
        for test_id in mandatory_tests(table_index)
        if test_id not in planned_positions
    )


def specimen_demand(assessments):
    """Total and per-group specimen counts the plan commits to drawing."""
    if not isinstance(assessments, (list, tuple)):
        raise ValueError("assessments must be a sequence, got %r" % (assessments,))
    per_group = {}
    total = 0
    for entry in assessments:
        if not isinstance(entry, dict):
            raise ValueError("assessment must be a mapping, got %r" % (entry,))
        if entry.get("source") == "similarity":
            continue
        count = _require_count(
            "planned_sample_count", entry.get("planned_sample_count", 0), minimum=0
        )
        group = entry.get("test_group") or "outside-table"
        per_group[group] = per_group.get(group, 0) + count
        total += count
    return {"total": total, "per_group": dict(sorted(per_group.items()))}


def worst_plan_verdict(verdicts):
    """The plan finding that has to be closed first."""
    if not isinstance(verdicts, (list, tuple, set, frozenset)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    ranked = []
    for verdict in verdicts:
        verdict = _require_text("verdict", verdict)
        if verdict not in TEST_VERDICT_RANK:
            raise ValueError("unknown plan verdict %s" % verdict)
        ranked.append(TEST_VERDICT_RANK.index(verdict))
    return TEST_VERDICT_RANK[min(ranked)]


def assemble_blocking_diode_qualification_plan(case, policy=DEFAULT_PLAN_POLICY):
    """Full clause 12.5.2 assembly check of a blocking diode qualification plan."""
    validate_plan_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    plan_id = _require_text("plan_id", case.get("plan_id"))
    diode_type = _require_text("diode_type", case.get("diode_type"))
    table_index = normalise_test_table(case.get("test_table"))
    plan = normalise_plan(case.get("plan"))
    planned_positions = {
        entry["test_id"]: entry["sequence_position"] for entry in plan
    }

    assessments = [
        assess_planned_test(entry, table_index, planned_positions, policy)
        for entry in plan
    ]
    findings = []
    for entry in assessments:
        findings.extend(entry["findings"])

    omitted = omitted_mandatory_tests(table_index, planned_positions, policy)
    for test_id in omitted:
        findings.append(
            "the table lists %s as owed and the plan books it nowhere" % test_id
        )

    owed = mandatory_tests(table_index)
    discharged = sorted(
        entry["test_id"]
        for entry in assessments
        if entry["discharged"] and entry["mandatory"]
    )
    coverage = len(discharged) / float(len(owed)) if owed else 1.0
    minimum = float(policy["min_mandatory_coverage_fraction"])
    coverage_ok = _at_least(coverage, minimum)
    if not coverage_ok:
        findings.append(
            "the plan discharges %d of %d owed tests against a required share "
            "of %.3f" % (len(discharged), len(owed), minimum)
        )

    grouped = {}
    for entry in assessments:
        grouped.setdefault(entry["verdict"], []).append(entry["test_id"])
    for test_id in omitted:
        grouped.setdefault(TEST_OMITTED, []).append(test_id)

    open_tests = sorted(
        entry["test_id"] for entry in assessments if not entry["discharged"]
    )
    verdicts = [entry["verdict"] for entry in assessments]
    if omitted:
        verdicts.append(TEST_OMITTED)

    return {
        "verdict": PLAN_COMPLETE
        if coverage_ok and not open_tests and not omitted
        else PLAN_INCOMPLETE,
        "plan_id": plan_id,
        "diode_type": diode_type,
        "test_assessments": assessments,
        "grouped_by_verdict": {k: sorted(v) for k, v in grouped.items()},
        "omitted_mandatory_tests": omitted,
        "open_test_ids": open_tests,
        "owed_test_ids": owed,
        "discharged_mandatory_tests": discharged,
        "mandatory_coverage_fraction": coverage,
        "required_coverage_fraction": minimum,
        "specimen_demand": specimen_demand(assessments),
        "planned_sequence": [entry["test_id"] for entry in plan],
        "worst_verdict": worst_plan_verdict(verdicts),
        "every_owed_test_discharged": not open_tests and not omitted,
        "findings": findings,
    }
