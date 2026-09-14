#!/usr/bin/env python3
"""Contract test for the blocking diode qualification plan, clause 12.5.2 (offline)."""

import copy
import unittest

from e2008_blocking_diode_qualification_plan_logic import (
    DEFAULT_PLAN_POLICY,
    PLAN_COMPLETE,
    PLAN_INCOMPLETE,
    PLAN_SOURCES,
    TEST_GROUPS,
    TEST_NOT_IN_TABLE,
    TEST_OMITTED,
    TEST_PLANNED,
    TEST_PREREQUISITE_ABSENT,
    TEST_PREREQUISITE_PLANNED_LATER,
    TEST_SAMPLE_COUNT_SHORT,
    TEST_SIMILARITY_NOT_ADMITTED,
    TEST_SIMILARITY_UNJUSTIFIED,
    assemble_blocking_diode_qualification_plan,
    assess_planned_test,
    mandatory_tests,
    normalise_plan,
    normalise_test_table,
    omitted_mandatory_tests,
    prerequisite_order,
    similarity_argument,
    specimen_demand,
    validate_plan_policy,
    worst_plan_verdict,
)

TABLE = [
    {
        "test_id": "visual-inspection",
        "test_group": "construction-analysis",
        "mandatory": True,
        "min_sample_count": 10,
    },
    {
        "test_id": "forward-voltage",
        "test_group": "electrical-characterisation",
        "mandatory": True,
        "min_sample_count": 10,
    },
    {
        "test_id": "thermal-cycling",
        "test_group": "environmental",
        "mandatory": True,
        "min_sample_count": 6,
        "prerequisite_tests": ["visual-inspection"],
    },
    {
        "test_id": "reverse-bias-life",
        "test_group": "endurance",
        "mandatory": True,
        "min_sample_count": 4,
        "prerequisite_tests": ["forward-voltage"],
    },
    {
        "test_id": "solderability",
        "test_group": "construction-analysis",
        "mandatory": False,
        "min_sample_count": 3,
    },
]

PLAN = [
    {"test_id": "visual-inspection", "sequence_position": 1, "source": "run",
     "planned_sample_count": 12},
    {"test_id": "forward-voltage", "sequence_position": 2, "source": "run",
     "planned_sample_count": 12},
    {"test_id": "thermal-cycling", "sequence_position": 3, "source": "run",
     "planned_sample_count": 6},
    {"test_id": "reverse-bias-life", "sequence_position": 4, "source": "run",
     "planned_sample_count": 4},
]


def _table(extra=None, drop=None):
    rows = [copy.deepcopy(row) for row in TABLE if row["test_id"] != drop]
    if extra:
        rows.append(copy.deepcopy(extra))
    return rows


def _plan(entries=None, extra=None, drop=None, **overrides):
    rows = [
        copy.deepcopy(row)
        for row in (entries if entries is not None else PLAN)
        if row["test_id"] != drop
    ]
    if extra:
        rows.append(copy.deepcopy(extra))
    for row in rows:
        if row["test_id"] in overrides:
            row.update(overrides[row["test_id"]])
    return rows


def _case(table=None, plan=None, **overrides):
    case = {
        "plan_id": "qp-bd-alpha",
        "diode_type": "bd-type-alpha",
        "test_table": table if table is not None else _table(),
        "plan": plan if plan is not None else _plan(),
    }
    case.update(overrides)
    return case


def _positions(plan):
    return {row["test_id"]: row["sequence_position"] for row in normalise_plan(plan)}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_plan_policy(DEFAULT_PLAN_POLICY), DEFAULT_PLAN_POLICY)

    def test_default_policy_requires_every_owed_test(self):
        self.assertTrue(DEFAULT_PLAN_POLICY["require_every_mandatory_test"])

    def test_default_policy_refuses_a_test_outside_the_table(self):
        self.assertFalse(DEFAULT_PLAN_POLICY["admit_test_outside_table"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan_policy("assemble from the table")

    def test_non_boolean_order_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_PLAN_POLICY)
        broken["enforce_prerequisite_order"] = 1
        with self.assertRaises(ValueError):
            validate_plan_policy(broken)

    def test_out_of_range_coverage_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_PLAN_POLICY)
        broken["min_mandatory_coverage_fraction"] = -0.2
        with self.assertRaises(ValueError):
            validate_plan_policy(broken)


class TableTests(unittest.TestCase):
    def test_the_table_indexes_every_listed_test(self):
        index = normalise_test_table(_table())
        self.assertEqual(len(index), 5)

    def test_the_owed_tests_are_the_mandatory_rows(self):
        self.assertEqual(
            mandatory_tests(normalise_test_table(_table())),
            [
                "forward-voltage",
                "reverse-bias-life",
                "thermal-cycling",
                "visual-inspection",
            ],
        )

    def test_a_repeated_table_row_rejected(self):
        with self.assertRaises(ValueError):
            normalise_test_table(_table(extra=copy.deepcopy(TABLE[0])))

    def test_an_unknown_test_group_rejected(self):
        row = copy.deepcopy(TABLE[0])
        row["test_id"] = "acoustic-noise"
        row["test_group"] = "acoustic"
        with self.assertRaises(ValueError):
            normalise_test_table(_table(extra=row))

    def test_a_zero_sample_count_in_the_table_rejected(self):
        row = copy.deepcopy(TABLE[0])
        row["test_id"] = "x-ray"
        row["min_sample_count"] = 0
        with self.assertRaises(ValueError):
            normalise_test_table(_table(extra=row))

    def test_a_prerequisite_the_table_never_lists_rejected(self):
        row = copy.deepcopy(TABLE[0])
        row["test_id"] = "burn-in"
        row["prerequisite_tests"] = ["radiography"]
        with self.assertRaises(ValueError):
            normalise_test_table(_table(extra=row))

    def test_a_self_referencing_prerequisite_rejected(self):
        row = copy.deepcopy(TABLE[0])
        row["test_id"] = "burn-in"
        row["prerequisite_tests"] = ["burn-in"]
        with self.assertRaises(ValueError):
            normalise_test_table(_table(extra=row))

    def test_an_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            normalise_test_table([])

    def test_every_declared_group_is_a_recognised_group(self):
        index = normalise_test_table(_table())
        for row in index.values():
            self.assertIn(row["test_group"], TEST_GROUPS)


class PlanShapeTests(unittest.TestCase):
    def test_the_plan_reads_back_in_sequence_order(self):
        shuffled = list(reversed(_plan()))
        self.assertEqual(
            [row["test_id"] for row in normalise_plan(shuffled)],
            [
                "visual-inspection",
                "forward-voltage",
                "thermal-cycling",
                "reverse-bias-life",
            ],
        )

    def test_a_test_booked_twice_rejected(self):
        with self.assertRaises(ValueError):
            normalise_plan(
                _plan(
                    extra={
                        "test_id": "visual-inspection",
                        "sequence_position": 9,
                        "source": "run",
                        "planned_sample_count": 10,
                    }
                )
            )

    def test_a_sequence_position_booked_twice_rejected(self):
        with self.assertRaises(ValueError):
            normalise_plan(
                _plan(
                    extra={
                        "test_id": "solderability",
                        "sequence_position": 1,
                        "source": "run",
                        "planned_sample_count": 3,
                    }
                )
            )

    def test_a_zero_sequence_position_rejected(self):
        with self.assertRaises(ValueError):
            normalise_plan(
                _plan(**{"visual-inspection": {"sequence_position": 0}})
            )

    def test_an_unknown_plan_source_rejected(self):
        with self.assertRaises(ValueError):
            normalise_plan(_plan(**{"forward-voltage": {"source": "assumed"}}))

    def test_an_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            normalise_plan([])

    def test_run_and_similarity_are_the_two_plan_sources(self):
        self.assertEqual(sorted(PLAN_SOURCES), ["run", "similarity"])


class SimilarityTests(unittest.TestCase):
    def test_a_run_entry_claims_no_similarity(self):
        read = similarity_argument(PLAN[0])
        self.assertFalse(read["claimed"])
        self.assertTrue(read["justified"])

    def test_a_bare_similarity_claim_is_unjustified(self):
        read = similarity_argument(
            {"test_id": "solderability", "sequence_position": 5, "source": "similarity"}
        )
        self.assertTrue(read["claimed"])
        self.assertFalse(read["justified"])
        self.assertEqual(read["missing"], ["delta_justification", "heritage_part"])

    def test_a_similarity_claim_with_heritage_and_delta_is_justified(self):
        read = similarity_argument(
            {
                "test_id": "solderability",
                "sequence_position": 5,
                "source": "similarity",
                "heritage_part": "bd-type-legacy",
                "delta_justification": "same lead finish and package",
            }
        )
        self.assertTrue(read["justified"])

    def test_a_relaxed_policy_accepts_a_bare_similarity_claim(self):
        relaxed = copy.deepcopy(DEFAULT_PLAN_POLICY)
        relaxed["require_similarity_justification"] = False
        read = similarity_argument(
            {"test_id": "solderability", "sequence_position": 5, "source": "similarity"},
            relaxed,
        )
        self.assertTrue(read["justified"])

    def test_an_unknown_source_rejected_by_the_similarity_read(self):
        with self.assertRaises(ValueError):
            similarity_argument({"test_id": "x", "source": "guessed"})


class PrerequisiteTests(unittest.TestCase):
    def test_a_correctly_ordered_test_is_ordered(self):
        index = normalise_test_table(_table())
        positions = _positions(_plan())
        read = prerequisite_order(PLAN[2], index, positions)
        self.assertTrue(read["ordered"])

    def test_a_prerequisite_the_plan_never_books_is_absent(self):
        index = normalise_test_table(_table())
        plan = _plan(drop="visual-inspection")
        read = prerequisite_order(plan[1], index, _positions(plan))
        self.assertEqual(read["absent"], ["visual-inspection"])

    def test_a_prerequisite_booked_later_is_late(self):
        index = normalise_test_table(_table())
        plan = _plan(
            **{
                "visual-inspection": {"sequence_position": 8},
            }
        )
        read = prerequisite_order(plan[2], index, _positions(plan))
        self.assertEqual(read["late"], ["visual-inspection"])

    def test_a_relaxed_policy_lets_a_late_prerequisite_through(self):
        relaxed = copy.deepcopy(DEFAULT_PLAN_POLICY)
        relaxed["enforce_prerequisite_order"] = False
        index = normalise_test_table(_table())
        plan = _plan(**{"visual-inspection": {"sequence_position": 8}})
        read = prerequisite_order(plan[2], index, _positions(plan), relaxed)
        self.assertTrue(read["ordered"])

    def test_a_test_outside_the_table_has_no_prerequisites_to_check(self):
        index = normalise_test_table(_table())
        entry = {"test_id": "acoustic", "sequence_position": 9, "source": "run"}
        self.assertTrue(prerequisite_order(entry, index, {})["ordered"])


class PlannedTestTests(unittest.TestCase):
    def setUp(self):
        self.index = normalise_test_table(_table())

    def test_a_clean_entry_is_planned(self):
        result = assess_planned_test(PLAN[0], self.index, _positions(_plan()))
        self.assertEqual(result["verdict"], TEST_PLANNED)
        self.assertTrue(result["discharged"])

    def test_a_test_outside_the_table_is_caught(self):
        entry = {
            "test_id": "acoustic-noise",
            "sequence_position": 9,
            "source": "run",
            "planned_sample_count": 5,
        }
        plan = _plan(extra=entry)
        result = assess_planned_test(entry, self.index, _positions(plan))
        self.assertEqual(result["verdict"], TEST_NOT_IN_TABLE)

    def test_an_undersized_test_is_caught_with_its_shortfall(self):
        plan = _plan(**{"thermal-cycling": {"planned_sample_count": 2}})
        result = assess_planned_test(plan[2], self.index, _positions(plan))
        self.assertEqual(result["verdict"], TEST_SAMPLE_COUNT_SHORT)
        self.assertEqual(result["sample_shortfall"], 4)

    def test_a_test_planned_on_exactly_the_table_count_is_planned(self):
        plan = _plan(**{"thermal-cycling": {"planned_sample_count": 6}})
        result = assess_planned_test(plan[2], self.index, _positions(plan))
        self.assertEqual(result["verdict"], TEST_PLANNED)

    def test_an_absent_prerequisite_outranks_an_undersized_count(self):
        plan = _plan(
            drop="visual-inspection",
            **{"thermal-cycling": {"planned_sample_count": 1}},
        )
        result = assess_planned_test(plan[1], self.index, _positions(plan))
        self.assertEqual(result["verdict"], TEST_PREREQUISITE_ABSENT)

    def test_a_late_prerequisite_is_caught(self):
        plan = _plan(**{"visual-inspection": {"sequence_position": 8}})
        result = assess_planned_test(plan[2], self.index, _positions(plan))
        self.assertEqual(result["verdict"], TEST_PREREQUISITE_PLANNED_LATER)

    def test_a_bare_similarity_claim_is_caught(self):
        plan = _plan(**{"solderability": {}})
        entry = {
            "test_id": "solderability",
            "sequence_position": 5,
            "source": "similarity",
        }
        plan = _plan(extra=entry)
        result = assess_planned_test(entry, self.index, _positions(plan))
        self.assertEqual(result["verdict"], TEST_SIMILARITY_UNJUSTIFIED)

    def test_a_justified_similarity_claim_is_planned(self):
        entry = {
            "test_id": "solderability",
            "sequence_position": 5,
            "source": "similarity",
            "heritage_part": "bd-type-legacy",
            "delta_justification": "identical package and lead finish",
        }
        plan = _plan(extra=entry)
        result = assess_planned_test(entry, self.index, _positions(plan))
        self.assertEqual(result["verdict"], TEST_PLANNED)

    def test_a_similarity_claim_on_an_owed_test_can_be_refused(self):
        strict = copy.deepcopy(DEFAULT_PLAN_POLICY)
        strict["admit_similarity_for_mandatory_test"] = False
        plan = _plan(
            **{
                "thermal-cycling": {
                    "source": "similarity",
                    "heritage_part": "bd-type-legacy",
                    "delta_justification": "same die",
                }
            }
        )
        result = assess_planned_test(plan[2], self.index, _positions(plan), strict)
        self.assertEqual(result["verdict"], TEST_SIMILARITY_NOT_ADMITTED)

    def test_a_similarity_entry_is_not_measured_against_the_sample_count(self):
        entry = {
            "test_id": "solderability",
            "sequence_position": 5,
            "source": "similarity",
            "heritage_part": "bd-type-legacy",
            "delta_justification": "identical package",
            "planned_sample_count": 0,
        }
        plan = _plan(extra=entry)
        result = assess_planned_test(entry, self.index, _positions(plan))
        self.assertTrue(result["discharged"])

    def test_an_entry_without_a_test_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_planned_test(
                {"sequence_position": 1, "source": "run"}, self.index, {}
            )


class OmissionAndDemandTests(unittest.TestCase):
    def test_a_complete_plan_omits_nothing(self):
        index = normalise_test_table(_table())
        self.assertEqual(omitted_mandatory_tests(index, _positions(_plan())), [])

    def test_a_dropped_owed_test_is_named(self):
        index = normalise_test_table(_table())
        plan = _plan(drop="reverse-bias-life")
        self.assertEqual(
            omitted_mandatory_tests(index, _positions(plan)), ["reverse-bias-life"]
        )

    def test_an_optional_test_may_be_left_out(self):
        index = normalise_test_table(_table())
        self.assertNotIn("solderability", omitted_mandatory_tests(index, _positions(_plan())))

    def test_the_specimen_demand_totals_the_run_entries(self):
        result = assemble_blocking_diode_qualification_plan(_case())
        self.assertEqual(result["specimen_demand"]["total"], 34)

    def test_the_specimen_demand_splits_by_group(self):
        result = assemble_blocking_diode_qualification_plan(_case())
        self.assertEqual(
            result["specimen_demand"]["per_group"]["environmental"], 6
        )

    def test_a_similarity_entry_draws_no_specimens(self):
        entry = {
            "test_id": "solderability",
            "sequence_position": 5,
            "source": "similarity",
            "heritage_part": "bd-type-legacy",
            "delta_justification": "identical package",
            "planned_sample_count": 7,
        }
        result = assemble_blocking_diode_qualification_plan(
            _case(plan=_plan(extra=entry))
        )
        self.assertEqual(result["specimen_demand"]["total"], 34)

    def test_a_non_sequence_assessment_list_rejected(self):
        with self.assertRaises(ValueError):
            specimen_demand("thirty-four")


class RankTests(unittest.TestCase):
    def test_an_omission_outranks_every_other_arm(self):
        self.assertEqual(
            worst_plan_verdict([TEST_PLANNED, TEST_SAMPLE_COUNT_SHORT, TEST_OMITTED]),
            TEST_OMITTED,
        )

    def test_a_test_outside_the_table_outranks_an_undersized_count(self):
        self.assertEqual(
            worst_plan_verdict([TEST_SAMPLE_COUNT_SHORT, TEST_NOT_IN_TABLE]),
            TEST_NOT_IN_TABLE,
        )

    def test_a_clean_plan_ranks_as_planned(self):
        self.assertEqual(worst_plan_verdict([TEST_PLANNED]), TEST_PLANNED)

    def test_an_unknown_verdict_rejected(self):
        with self.assertRaises(ValueError):
            worst_plan_verdict(["test-looks-fine"])

    def test_an_empty_verdict_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_plan_verdict([])


class AssemblyTests(unittest.TestCase):
    def test_a_clean_plan_is_complete(self):
        result = assemble_blocking_diode_qualification_plan(_case())
        self.assertEqual(result["verdict"], PLAN_COMPLETE)
        self.assertTrue(result["every_owed_test_discharged"])
        self.assertEqual(result["findings"], [])

    def test_a_clean_plan_covers_every_owed_test(self):
        result = assemble_blocking_diode_qualification_plan(_case())
        self.assertAlmostEqual(result["mandatory_coverage_fraction"], 1.0, places=9)

    def test_one_dropped_owed_test_in_four_scores_three_quarters(self):
        result = assemble_blocking_diode_qualification_plan(
            _case(plan=_plan(drop="reverse-bias-life"))
        )
        self.assertAlmostEqual(result["mandatory_coverage_fraction"], 0.75, places=9)
        self.assertEqual(result["verdict"], PLAN_INCOMPLETE)

    def test_the_omitted_test_is_named_in_the_roll_up(self):
        result = assemble_blocking_diode_qualification_plan(
            _case(plan=_plan(drop="thermal-cycling"))
        )
        self.assertEqual(result["omitted_mandatory_tests"], ["thermal-cycling"])
        self.assertEqual(result["worst_verdict"], TEST_OMITTED)

    def test_the_roll_up_reports_the_planned_sequence(self):
        result = assemble_blocking_diode_qualification_plan(_case())
        self.assertEqual(result["planned_sequence"][0], "visual-inspection")

    def test_the_roll_up_groups_the_tests_by_verdict(self):
        result = assemble_blocking_diode_qualification_plan(
            _case(plan=_plan(**{"thermal-cycling": {"planned_sample_count": 1}}))
        )
        self.assertEqual(
            result["grouped_by_verdict"][TEST_SAMPLE_COUNT_SHORT], ["thermal-cycling"]
        )

    def test_the_roll_up_names_the_open_tests(self):
        result = assemble_blocking_diode_qualification_plan(
            _case(plan=_plan(**{"forward-voltage": {"planned_sample_count": 2}}))
        )
        self.assertEqual(result["open_test_ids"], ["forward-voltage"])

    def test_a_relaxed_coverage_share_accepts_a_partial_plan(self):
        relaxed = copy.deepcopy(DEFAULT_PLAN_POLICY)
        relaxed["min_mandatory_coverage_fraction"] = 0.5
        result = assemble_blocking_diode_qualification_plan(
            _case(plan=_plan(**{"forward-voltage": {"planned_sample_count": 1}})),
            relaxed,
        )
        self.assertAlmostEqual(result["mandatory_coverage_fraction"], 0.75, places=9)
        self.assertEqual(result["required_coverage_fraction"], 0.5)

    def test_a_case_without_a_plan_identifier_rejected(self):
        case = _case()
        del case["plan_id"]
        with self.assertRaises(ValueError):
            assemble_blocking_diode_qualification_plan(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assemble_blocking_diode_qualification_plan([_case()])

    def test_the_roll_up_carries_every_test_finding(self):
        result = assemble_blocking_diode_qualification_plan(
            _case(plan=_plan(**{"reverse-bias-life": {"planned_sample_count": 1}}))
        )
        self.assertTrue(any("reverse-bias-life" in f for f in result["findings"]))

    def test_the_roll_up_lists_the_owed_tests_from_the_table(self):
        result = assemble_blocking_diode_qualification_plan(_case())
        self.assertEqual(len(result["owed_test_ids"]), 4)


if __name__ == "__main__":
    unittest.main()
