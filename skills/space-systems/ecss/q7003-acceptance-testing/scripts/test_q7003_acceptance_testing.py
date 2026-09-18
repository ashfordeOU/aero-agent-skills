#!/usr/bin/env python3
"""Contract test for the anodize batch acceptance programme (offline)."""

import copy
import unittest

from q7003_acceptance_testing_logic import (
    BATCH_ACCEPT,
    BATCH_REJECT,
    BATCH_SCREEN,
    DESTRUCTIVE_TESTS,
    PART_CATEGORIES,
    TEST_ADHESION,
    TEST_CORROSION,
    TEST_THICKNESS,
    acceptance_number,
    category_rules,
    destructive_tests,
    judge_batch,
    plan_acceptance,
    required_tests,
    sample_size,
    witness_coupons_required,
)

GOOD_CASE = {
    "category": "flight-standard",
    "lot_size": 100,
    "rack_count": 2,
    "tests_performed": required_tests("flight-standard"),
    "defective_count": 0,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class CategoryRuleTests(unittest.TestCase):
    def test_every_category_has_rules(self):
        for category in PART_CATEGORIES:
            rules = category_rules(category)
            self.assertTrue(rules["tests"])
            self.assertGreaterEqual(rules["sample_floor"], 1)

    def test_critical_category_demands_the_most_tests(self):
        critical = required_tests("flight-critical")
        standard = required_tests("flight-standard")
        support = required_tests("ground-support")
        self.assertGreater(len(critical), len(standard))
        self.assertGreater(len(standard), len(support))

    def test_critical_category_forbids_screening(self):
        self.assertFalse(category_rules("flight-critical")["screening_allowed"])

    def test_corrosion_test_is_only_owed_by_the_critical_category(self):
        self.assertIn(TEST_CORROSION, required_tests("flight-critical"))
        self.assertNotIn(TEST_CORROSION, required_tests("flight-standard"))

    def test_thickness_is_owed_by_every_category(self):
        for category in PART_CATEGORIES:
            self.assertIn(TEST_THICKNESS, required_tests(category))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            category_rules("prototype")


class SamplingTests(unittest.TestCase):
    def test_sample_follows_the_square_root_of_the_lot(self):
        self.assertEqual(sample_size(100, "ground-support"), 10)

    def test_perfect_square_lot_takes_its_exact_root(self):
        self.assertEqual(sample_size(400, "ground-support"), 20)

    def test_sample_rounds_up_off_a_perfect_square(self):
        self.assertEqual(sample_size(101, "ground-support"), 11)

    def test_sample_never_falls_below_the_category_floor(self):
        self.assertEqual(sample_size(4, "flight-standard"), 4)
        self.assertEqual(sample_size(9, "flight-standard"), 5)

    def test_sample_never_exceeds_the_lot(self):
        for lot in range(1, 30):
            for category in PART_CATEGORIES:
                self.assertLessEqual(sample_size(lot, category), lot)

    def test_sample_is_monotone_in_the_lot(self):
        previous = 0
        for lot in range(1, 500):
            current = sample_size(lot, "ground-support")
            self.assertGreaterEqual(current, previous)
            previous = current

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            sample_size(0, "ground-support")

    def test_non_integer_lot_rejected(self):
        with self.assertRaises(ValueError):
            sample_size(100.0, "ground-support")


class AcceptanceNumberTests(unittest.TestCase):
    def test_critical_category_allows_no_defective(self):
        self.assertEqual(acceptance_number(1000, "flight-critical"), 0)

    def test_support_category_allows_more_than_the_standard_one(self):
        self.assertGreaterEqual(
            acceptance_number(10000, "ground-support"),
            acceptance_number(10000, "flight-standard"),
        )

    def test_allowance_is_never_negative(self):
        for lot in (1, 10, 100, 1000):
            for category in PART_CATEGORIES:
                self.assertGreaterEqual(acceptance_number(lot, category), 0)

    def test_allowance_never_exceeds_the_sample(self):
        for lot in (1, 25, 250, 2500):
            for category in PART_CATEGORIES:
                self.assertLessEqual(
                    acceptance_number(lot, category), sample_size(lot, category)
                )


class WitnessCouponTests(unittest.TestCase):
    def test_coupons_scale_with_the_rack_count(self):
        one = witness_coupons_required("flight-critical", 1)["coupons"]
        three = witness_coupons_required("flight-critical", 3)["coupons"]
        self.assertEqual(three, 3 * one)

    def test_coupons_cover_every_destructive_test(self):
        result = witness_coupons_required("flight-critical", 1)
        self.assertEqual(
            sorted(result["destructive_tests"]), sorted(DESTRUCTIVE_TESTS)
        )

    def test_a_category_with_one_destructive_test_needs_one_per_rack(self):
        result = witness_coupons_required("ground-support", 4)
        self.assertEqual(result["destructive_tests"], [TEST_ADHESION])
        self.assertEqual(result["coupons"], 4)

    def test_zero_racks_rejected(self):
        with self.assertRaises(ValueError):
            witness_coupons_required("flight-standard", 0)

    def test_destructive_tests_are_a_subset_of_the_required_tests(self):
        for category in PART_CATEGORIES:
            self.assertTrue(
                set(destructive_tests(category)) <= set(required_tests(category))
            )


class JudgeBatchTests(unittest.TestCase):
    def test_clean_sample_accepts(self):
        result = judge_batch(100, "flight-standard", 0)
        self.assertEqual(result["disposition"], BATCH_ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_defective_within_the_allowance_accepts(self):
        allowance = acceptance_number(10000, "ground-support")
        result = judge_batch(10000, "ground-support", allowance)
        self.assertEqual(result["disposition"], BATCH_ACCEPT)

    def test_one_defective_rejects_a_critical_batch(self):
        result = judge_batch(1000, "flight-critical", 1)
        self.assertEqual(result["disposition"], BATCH_REJECT)
        self.assertTrue(any("screening is not a route" in f for f in result["findings"]))

    def test_overrun_on_a_screenable_category_calls_for_screening(self):
        result = judge_batch(100, "flight-standard", 5)
        self.assertEqual(result["disposition"], BATCH_SCREEN)

    def test_a_completed_screen_recovers_the_lot(self):
        result = judge_batch(100, "flight-standard", 5, screening_completed=True)
        self.assertEqual(result["disposition"], BATCH_ACCEPT)
        self.assertTrue(any("screened part by part" in f for f in result["findings"]))

    def test_a_completed_screen_does_not_recover_a_critical_lot(self):
        result = judge_batch(1000, "flight-critical", 1, screening_completed=True)
        self.assertEqual(result["disposition"], BATCH_REJECT)

    def test_more_defectives_than_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            judge_batch(100, "flight-standard", 99)

    def test_negative_defective_count_rejected(self):
        with self.assertRaises(ValueError):
            judge_batch(100, "flight-standard", -1)


class PlanAcceptanceTests(unittest.TestCase):
    def test_complete_programme_accepts(self):
        result = plan_acceptance(GOOD_CASE)
        self.assertEqual(result["verdict"], "acceptance-complete")
        self.assertEqual(result["disposition"], BATCH_ACCEPT)
        self.assertEqual(result["missing_tests"], [])

    def test_missing_test_blocks_any_disposition(self):
        case = _case(tests_performed=[TEST_THICKNESS])
        result = plan_acceptance(case)
        self.assertEqual(result["verdict"], "acceptance-incomplete")
        self.assertIsNone(result["disposition"])
        self.assertIn(TEST_ADHESION, result["missing_tests"])

    def test_no_tests_recorded_leaves_every_test_missing(self):
        case = _case()
        del case["tests_performed"]
        result = plan_acceptance(case)
        self.assertEqual(
            result["missing_tests"], required_tests("flight-standard")
        )

    def test_an_unexpected_test_is_reported_but_not_fatal(self):
        case = _case(
            tests_performed=required_tests("flight-standard") + [TEST_CORROSION]
        )
        result = plan_acceptance(case)
        self.assertEqual(result["verdict"], "acceptance-complete")
        self.assertTrue(any("does not call for" in f for f in result["findings"]))

    def test_coupon_count_is_carried_into_the_plan(self):
        result = plan_acceptance(_case(rack_count=3))
        self.assertEqual(result["witness_coupons"]["coupons"], 3)

    def test_a_critical_batch_with_a_defective_rejects(self):
        case = _case(
            category="flight-critical",
            tests_performed=required_tests("flight-critical"),
            defective_count=1,
        )
        self.assertEqual(plan_acceptance(case)["disposition"], BATCH_REJECT)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            plan_acceptance("one batch, all good")

    def test_non_sequence_test_record_rejected(self):
        with self.assertRaises(ValueError):
            plan_acceptance(_case(tests_performed="everything"))

    def test_missing_lot_size_rejected(self):
        case = _case()
        del case["lot_size"]
        with self.assertRaises(ValueError):
            plan_acceptance(case)


if __name__ == "__main__":
    unittest.main()
