#!/usr/bin/env python3
"""Contract test for the planar blocking diode testing overview (offline).

Walks the clause workflow step by step: the two test sets and which one
owns each test, the misfiled record, the four record states kept apart,
the shared tests a lot leans on the design campaign for, the coverage
figure against the declared minimum, the similarity route and the
evidence it rests on, the failure policy, and the roll-up into one
programme verdict. This is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_blocking_diode_testing_overview_logic import (
    ALL_TESTS,
    PROCUREMENT_TESTS,
    PROGRAMME_CLEAR,
    PROGRAMME_OPEN,
    QUALIFICATION_TESTS,
    QUAL_BY_SIMILARITY,
    QUAL_BY_TEST,
    QUAL_IN_PROGRESS,
    QUAL_NONE,
    OUTCOME_FAILED,
    OUTCOME_NOT_RUN,
    OUTCOME_PASSED,
    SET_COMPLETE,
    SET_FAILED,
    SET_NOT_RUN,
    SET_NO_RECORD,
    SHARED_TESTS,
    assess_blocking_diode_test_programme,
    assess_procurement_lot,
    assess_qualification,
    assess_test_set,
    is_shared_test,
    resolve_policy,
    shared_test_double_count,
    test_sets_for,
    validate_records,
)


def _full(tests):
    return {name: OUTCOME_PASSED for name in tests}


def _qualification(**overrides):
    block = {"status": QUAL_BY_TEST, "records": _full(QUALIFICATION_TESTS)}
    block.update(copy.deepcopy(overrides))
    return block


def _lot(lot_id="LOT-01", **overrides):
    entry = {"lot_id": lot_id, "records": _full(PROCUREMENT_TESTS)}
    entry.update(copy.deepcopy(overrides))
    return entry


def _case(**overrides):
    case = {
        "part_id": "BD-PLANAR-12",
        "qualification": _qualification(),
        "lots": [_lot("LOT-01"), _lot("LOT-02")],
    }
    case.update(copy.deepcopy(overrides))
    return case


class TestSetMembershipTests(unittest.TestCase):
    def test_a_qualification_only_test_names_one_set(self):
        self.assertEqual(
            test_sets_for("planar-blocking-diode-life-test"), ("qualification",)
        )

    def test_a_procurement_only_test_names_one_set(self):
        self.assertEqual(
            test_sets_for("planar-blocking-diode-burn-in"), ("procurement",)
        )

    def test_a_shared_test_names_both_sets(self):
        self.assertTrue(is_shared_test("planar-blocking-diode-visual-inspection"))
        self.assertEqual(
            test_sets_for("planar-blocking-diode-visual-inspection"),
            ("qualification", "procurement"),
        )

    def test_the_shared_tests_are_the_intersection_of_the_two_sets(self):
        for name in SHARED_TESTS:
            self.assertIn(name, QUALIFICATION_TESTS)
            self.assertIn(name, PROCUREMENT_TESTS)
        self.assertTrue(set(SHARED_TESTS).issubset(set(ALL_TESTS)))

    def test_an_unknown_test_is_rejected(self):
        with self.assertRaises(ValueError):
            test_sets_for("planar-blocking-diode-launch-rehearsal")


class RecordValidationTests(unittest.TestCase):
    def test_a_sound_record_book_validates(self):
        book = validate_records(_full(PROCUREMENT_TESTS), "procurement")
        self.assertEqual(len(book), len(PROCUREMENT_TESTS))

    def test_a_test_booked_to_the_set_that_does_not_owe_it_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_records(
                {"planar-blocking-diode-life-test": OUTCOME_PASSED}, "procurement"
            )

    def test_an_unknown_outcome_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_records(
                {"planar-blocking-diode-burn-in": "probably-fine"}, "procurement"
            )

    def test_an_unknown_test_set_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_records({}, "flight-acceptance")


class TestSetGradingTests(unittest.TestCase):
    def test_a_complete_set_is_complete_and_finding_free(self):
        graded = assess_test_set(_full(PROCUREMENT_TESTS), "procurement")
        self.assertEqual(graded["verdict"], SET_COMPLETE)
        self.assertEqual(graded["findings"], [])
        self.assertAlmostEqual(graded["coverage"], 1.0, places=9)
        self.assertTrue(graded["meets_coverage"])

    def test_a_missing_record_ranks_worst(self):
        book = _full(PROCUREMENT_TESTS)
        del book["planar-blocking-diode-burn-in"]
        graded = assess_test_set(book, "procurement")
        self.assertEqual(graded["verdict"], SET_NO_RECORD)
        self.assertEqual(graded["missing"], ["planar-blocking-diode-burn-in"])

    def test_an_unrun_test_is_kept_apart_from_absence(self):
        book = _full(PROCUREMENT_TESTS)
        book["planar-blocking-diode-burn-in"] = OUTCOME_NOT_RUN
        graded = assess_test_set(book, "procurement")
        self.assertEqual(graded["verdict"], SET_NOT_RUN)
        self.assertEqual(graded["missing"], [])

    def test_a_recorded_failure_is_kept_apart_from_absence(self):
        book = _full(PROCUREMENT_TESTS)
        book["planar-blocking-diode-seal-integrity"] = OUTCOME_FAILED
        graded = assess_test_set(book, "procurement")
        self.assertEqual(graded["verdict"], SET_FAILED)
        self.assertTrue(graded["findings"])

    def test_coverage_lands_on_the_owed_count_not_the_recorded_count(self):
        book = _full(PROCUREMENT_TESTS)
        book["planar-blocking-diode-burn-in"] = OUTCOME_NOT_RUN
        graded = assess_test_set(book, "procurement")
        expected = (len(PROCUREMENT_TESTS) - 1) / len(PROCUREMENT_TESTS)
        self.assertAlmostEqual(graded["coverage"], expected, places=9)

    def test_a_coverage_landing_exactly_on_the_minimum_is_accepted(self):
        book = _full(PROCUREMENT_TESTS)
        book["planar-blocking-diode-burn-in"] = OUTCOME_NOT_RUN
        minimum = (len(PROCUREMENT_TESTS) - 1) / len(PROCUREMENT_TESTS)
        graded = assess_test_set(
            book, "procurement", {"min_set_coverage": minimum}
        )
        self.assertTrue(graded["meets_coverage"])


class SharedTestTests(unittest.TestCase):
    def test_a_lot_with_its_own_shared_records_leans_on_nothing(self):
        self.assertEqual(
            shared_test_double_count(
                _full(QUALIFICATION_TESTS), _full(PROCUREMENT_TESTS)
            ),
            [],
        )

    def test_a_lot_missing_a_shared_record_is_leaning_on_the_campaign(self):
        book = _full(PROCUREMENT_TESTS)
        del book["planar-blocking-diode-visual-inspection"]
        leaned = shared_test_double_count(_full(QUALIFICATION_TESTS), book)
        self.assertEqual(leaned, ["planar-blocking-diode-visual-inspection"])

    def test_the_lot_report_names_the_double_counted_test(self):
        book = _full(PROCUREMENT_TESTS)
        del book["planar-blocking-diode-electrical-characterization"]
        result = assess_procurement_lot(
            _lot("LOT-09", records=book), _full(QUALIFICATION_TESTS)
        )
        self.assertEqual(
            result["leaning_on_qualification"],
            ["planar-blocking-diode-electrical-characterization"],
        )
        self.assertTrue(any("consumed" in f for f in result["findings"]))


class QualificationRouteTests(unittest.TestCase):
    def test_a_fully_tested_design_is_accepted(self):
        result = assess_qualification(_qualification())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_an_open_campaign_is_reported_and_not_accepted(self):
        result = assess_qualification(
            _qualification(status=QUAL_IN_PROGRESS, records={})
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(any("still open" in f for f in result["findings"]))

    def test_a_design_with_no_qualification_is_reported(self):
        result = assess_qualification(_qualification(status=QUAL_NONE, records={}))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("no qualification at all" in f for f in result["findings"]))

    def test_a_similarity_claim_without_a_heritage_part_is_unsupported(self):
        result = assess_qualification(
            _qualification(
                status=QUAL_BY_SIMILARITY,
                records={},
                delta_justification="same die, new package",
            ),
            {"accept_similarity_claim": True},
        )
        self.assertFalse(result["similarity_supported"])
        self.assertFalse(result["accepted"])

    def test_a_similarity_claim_without_a_delta_justification_is_unsupported(self):
        result = assess_qualification(
            _qualification(
                status=QUAL_BY_SIMILARITY, records={}, heritage_part="BD-PLANAR-09"
            ),
            {"accept_similarity_claim": True},
        )
        self.assertFalse(result["similarity_supported"])

    def test_a_supported_similarity_claim_still_needs_policy_to_accept_it(self):
        block = _qualification(
            status=QUAL_BY_SIMILARITY,
            records={},
            heritage_part="BD-PLANAR-09",
            delta_justification="same die, same package, new lot date",
        )
        refused = assess_qualification(block)
        accepted = assess_qualification(block, {"accept_similarity_claim": True})
        self.assertTrue(refused["similarity_supported"])
        self.assertFalse(refused["accepted"])
        self.assertTrue(accepted["accepted"])


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve(self):
        settings = resolve_policy()
        self.assertAlmostEqual(settings["min_set_coverage"], 1.0, places=9)
        self.assertFalse(settings["accept_similarity_claim"])

    def test_a_coverage_minimum_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"min_set_coverage": 1.4})

    def test_a_non_boolean_failure_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"carry_dispositioned_failure": "yes"})


class ProgrammeRollUpTests(unittest.TestCase):
    def test_a_sound_programme_is_clear(self):
        result = assess_blocking_diode_test_programme(_case())
        self.assertEqual(result["verdict"], PROGRAMME_CLEAR)
        self.assertEqual(result["findings"], [])
        self.assertEqual(sorted(result["grouped_lots"]), [SET_COMPLETE])

    def test_one_thin_lot_opens_the_programme(self):
        book = _full(PROCUREMENT_TESTS)
        del book["planar-blocking-diode-seal-integrity"]
        case = _case(lots=[_lot("LOT-01"), _lot("LOT-02", records=book)])
        result = assess_blocking_diode_test_programme(case)
        self.assertEqual(result["verdict"], PROGRAMME_OPEN)
        self.assertEqual(result["weakest_lot"], "LOT-02")

    def test_an_unqualified_design_opens_the_programme_with_clean_lots(self):
        case = _case(qualification=_qualification(status=QUAL_NONE, records={}))
        result = assess_blocking_diode_test_programme(case)
        self.assertEqual(result["verdict"], PROGRAMME_OPEN)
        self.assertEqual(sorted(result["grouped_lots"]), [SET_COMPLETE])

    def test_a_dispositioned_failure_can_be_carried_by_policy(self):
        book = _full(PROCUREMENT_TESTS)
        book["planar-blocking-diode-burn-in"] = OUTCOME_FAILED
        case = _case(
            lots=[_lot("LOT-01", records=book)],
            policy={"carry_dispositioned_failure": True, "min_set_coverage": 0.75},
        )
        result = assess_blocking_diode_test_programme(case)
        self.assertEqual(result["verdict"], PROGRAMME_CLEAR)

    def test_a_duplicate_lot_identifier_is_rejected(self):
        case = _case(lots=[_lot("LOT-01"), _lot("LOT-01")])
        with self.assertRaises(ValueError):
            assess_blocking_diode_test_programme(case)

    def test_a_programme_with_no_lots_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_test_programme(_case(lots=[]))

    def test_an_empty_part_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_test_programme(_case(part_id="   "))


if __name__ == "__main__":
    unittest.main(verbosity=1)
