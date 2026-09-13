#!/usr/bin/env python3
"""Contract test for acceptance thermal-cycle exposure (offline).

This is the gate 3 behaviour contract: every workflow step of the leaf
(policy validation, referenced-count resolution, declared-count
reconciliation, interruption crediting, coupon grading and the set
verdict) is exercised here, including the refusals that stop a lot being
accepted on an exposure it never took.
"""

import copy
import unittest

from e2008_thermal_cycle_acceptance_process_logic import (
    COUPON_CATEGORIES,
    COUPON_EXPOSED,
    COUPON_INVALID,
    COUPON_SHORT,
    DEFAULT_ACCEPTANCE_POLICY,
    EXPOSURE_COMPLETE,
    EXPOSURE_NOT_RUN,
    EXPOSURE_SHORT,
    assess_acceptance_cycling,
    credited_cycles,
    grade_coupon_exposure,
    reconcile_declared_count,
    referenced_cycle_count,
    validate_acceptance_policy,
)


def _coupon(coupon_id, cycles_run, interruptions=()):
    return {
        "coupon_id": coupon_id,
        "cycles_run": cycles_run,
        "interruptions": list(interruptions),
    }


BASE_CASE = {
    "standard_key": "coupon-cycling-baseline",
    "coupon_category": "cell-stack",
    "coupons": [_coupon("C1", 200), _coupon("C2", 200)],
}


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_acceptance_policy(DEFAULT_ACCEPTANCE_POLICY),
            DEFAULT_ACCEPTANCE_POLICY,
        )

    def test_every_catalogue_entry_covers_every_coupon_category(self):
        for counts in DEFAULT_ACCEPTANCE_POLICY["referenced_standard_cycles"].values():
            for category in COUPON_CATEGORIES:
                self.assertIn(category, counts)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy("baseline")

    def test_empty_reference_catalogue_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        broken["referenced_standard_cycles"] = {}
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_catalogue_missing_a_coupon_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        del broken["referenced_standard_cycles"]["coupon-cycling-baseline"]["interconnect"]
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_fractional_reference_count_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        broken["referenced_standard_cycles"]["coupon-cycling-baseline"]["cell-stack"] = 200.5
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_zero_minimum_coupon_count_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        broken["minimum_coupons_per_category"] = 0
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_negative_overtest_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        broken["overtest_finding_fraction"] = -0.1
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)


class ReferencedCountTests(unittest.TestCase):
    def test_count_comes_from_the_referenced_standard(self):
        self.assertEqual(
            referenced_cycle_count("coupon-cycling-baseline", "cell-stack"), 200
        )

    def test_extended_reference_demands_more_than_the_reduced_one(self):
        self.assertGreater(
            referenced_cycle_count("coupon-cycling-extended", "interconnect"),
            referenced_cycle_count("coupon-cycling-reduced", "interconnect"),
        )

    def test_category_changes_the_count_under_one_reference(self):
        self.assertNotEqual(
            referenced_cycle_count("coupon-cycling-baseline", "cell-stack"),
            referenced_cycle_count("coupon-cycling-baseline", "harness-termination"),
        )

    def test_unlisted_reference_rejected(self):
        with self.assertRaises(ValueError):
            referenced_cycle_count("a-standard-nobody-cites", "cell-stack")

    def test_unknown_coupon_category_rejected(self):
        with self.assertRaises(ValueError):
            referenced_cycle_count("coupon-cycling-baseline", "blanket")

    def test_blank_reference_key_rejected(self):
        with self.assertRaises(ValueError):
            referenced_cycle_count("   ", "cell-stack")


class DeclaredCountTests(unittest.TestCase):
    def test_matching_declaration_carries_no_finding(self):
        result = reconcile_declared_count("coupon-cycling-baseline", "cell-stack", 200)
        self.assertEqual(result["overtest_cycles"], 0)
        self.assertEqual(result["findings"], [])

    def test_declaration_below_the_reference_is_refused(self):
        with self.assertRaises(ValueError):
            reconcile_declared_count("coupon-cycling-baseline", "cell-stack", 150)

    def test_small_overtest_is_recorded_not_refused(self):
        result = reconcile_declared_count("coupon-cycling-baseline", "cell-stack", 210)
        self.assertEqual(result["overtest_cycles"], 10)
        self.assertEqual(len(result["findings"]), 1)

    def test_overtest_exactly_on_the_allowance_is_not_flagged_as_beyond_it(self):
        result = reconcile_declared_count("coupon-cycling-baseline", "cell-stack", 220)
        self.assertEqual(result["overtest_cycles"], 20)
        self.assertNotIn("beyond", result["findings"][0])

    def test_overtest_past_the_allowance_is_flagged(self):
        result = reconcile_declared_count("coupon-cycling-baseline", "cell-stack", 260)
        self.assertIn("beyond", result["findings"][0])

    def test_zero_declared_count_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_declared_count("coupon-cycling-baseline", "cell-stack", 0)

    def test_non_integer_declared_count_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_declared_count("coupon-cycling-baseline", "cell-stack", 200.0)


class CreditedCycleTests(unittest.TestCase):
    def test_uninterrupted_run_credits_every_cycle(self):
        tally = credited_cycles(_coupon("C1", 200))
        self.assertEqual(tally["cycles_credited"], 200)
        self.assertEqual(tally["cycles_invalidated"], 0)

    def test_interruption_takes_back_the_cycles_it_invalidated(self):
        tally = credited_cycles(
            _coupon("C1", 200, [{"at_cycle": 120, "cycles_invalidated": 15}])
        )
        self.assertEqual(tally["cycles_credited"], 185)

    def test_several_interruptions_accumulate(self):
        tally = credited_cycles(
            _coupon(
                "C1",
                200,
                [
                    {"at_cycle": 60, "cycles_invalidated": 10},
                    {"at_cycle": 150, "cycles_invalidated": 20},
                ],
            )
        )
        self.assertEqual(tally["cycles_credited"], 170)
        self.assertEqual(tally["interruption_count"], 2)

    def test_interruption_logged_past_the_run_rejected(self):
        with self.assertRaises(ValueError):
            credited_cycles(
                _coupon("C1", 100, [{"at_cycle": 140, "cycles_invalidated": 5}])
            )

    def test_interruption_invalidating_unrun_cycles_rejected(self):
        with self.assertRaises(ValueError):
            credited_cycles(
                _coupon("C1", 200, [{"at_cycle": 10, "cycles_invalidated": 40}])
            )

    def test_missing_coupon_identifier_rejected(self):
        with self.assertRaises(ValueError):
            credited_cycles({"cycles_run": 200, "interruptions": []})

    def test_negative_cycles_run_rejected(self):
        with self.assertRaises(ValueError):
            credited_cycles(_coupon("C1", -5))

    def test_non_mapping_interruption_rejected(self):
        with self.assertRaises(ValueError):
            credited_cycles(_coupon("C1", 200, ["power loss"]))


class CouponGradingTests(unittest.TestCase):
    def test_full_exposure_passes(self):
        graded = grade_coupon_exposure(_coupon("C1", 200), 200)
        self.assertEqual(graded["verdict"], COUPON_EXPOSED)
        self.assertAlmostEqual(graded["completion_fraction"], 1.0, places=9)

    def test_run_meeting_the_count_only_before_interruptions_is_short(self):
        graded = grade_coupon_exposure(
            _coupon("C1", 200, [{"at_cycle": 100, "cycles_invalidated": 30}]), 200
        )
        self.assertEqual(graded["verdict"], COUPON_SHORT)
        self.assertEqual(graded["cycles_credited"], 170)

    def test_half_an_exposure_reports_half_a_completion_fraction(self):
        graded = grade_coupon_exposure(_coupon("C1", 100), 200)
        self.assertAlmostEqual(graded["completion_fraction"], 0.5, places=9)

    def test_too_many_interruptions_invalidate_the_coupon(self):
        graded = grade_coupon_exposure(
            _coupon(
                "C1",
                260,
                [
                    {"at_cycle": 40, "cycles_invalidated": 0},
                    {"at_cycle": 90, "cycles_invalidated": 0},
                    {"at_cycle": 160, "cycles_invalidated": 0},
                ],
            ),
            200,
        )
        self.assertEqual(graded["verdict"], COUPON_INVALID)

    def test_extra_cycles_run_over_the_count_still_pass(self):
        graded = grade_coupon_exposure(
            _coupon("C1", 240, [{"at_cycle": 60, "cycles_invalidated": 20}]), 200
        )
        self.assertEqual(graded["verdict"], COUPON_EXPOSED)
        self.assertTrue(any("lost 20 cycles" in note for note in graded["findings"]))

    def test_zero_required_cycles_rejected(self):
        with self.assertRaises(ValueError):
            grade_coupon_exposure(_coupon("C1", 200), 0)


class SetAssessmentTests(unittest.TestCase):
    def test_fully_exposed_set_is_complete(self):
        result = assess_acceptance_cycling(_case())
        self.assertEqual(result["verdict"], EXPOSURE_COMPLETE)
        self.assertEqual(result["coupons_exposed"], 2)
        self.assertEqual(result["required_cycles"], 200)

    def test_one_short_coupon_holds_the_whole_set_short(self):
        result = assess_acceptance_cycling(
            _case(coupons=[_coupon("C1", 200), _coupon("C2", 180)])
        )
        self.assertEqual(result["verdict"], EXPOSURE_SHORT)
        self.assertEqual(result["coupons_exposed"], 1)

    def test_too_few_coupons_holds_the_set_short(self):
        result = assess_acceptance_cycling(_case(coupons=[_coupon("C1", 200)]))
        self.assertEqual(result["verdict"], EXPOSURE_SHORT)
        self.assertTrue(any("minimum" in note for note in result["findings"]))

    def test_no_records_leaves_the_set_not_run(self):
        case = _case()
        del case["coupons"]
        result = assess_acceptance_cycling(case)
        self.assertEqual(result["verdict"], EXPOSURE_NOT_RUN)
        self.assertEqual(result["referenced_cycles"], 200)

    def test_declared_overtest_raises_the_bar_every_coupon_must_clear(self):
        result = assess_acceptance_cycling(
            _case(declared_cycles=210, coupons=[_coupon("C1", 205), _coupon("C2", 205)])
        )
        self.assertEqual(result["required_cycles"], 210)
        self.assertEqual(result["verdict"], EXPOSURE_SHORT)

    def test_declared_count_below_the_reference_refuses_the_whole_set(self):
        with self.assertRaises(ValueError):
            assess_acceptance_cycling(_case(declared_cycles=120))

    def test_duplicate_coupon_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance_cycling(
                _case(coupons=[_coupon("C1", 200), _coupon("C1", 200)])
            )

    def test_unknown_category_rejected_before_any_grading(self):
        with self.assertRaises(ValueError):
            assess_acceptance_cycling(_case(coupon_category="blanket"))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance_cycling(["coupon-cycling-baseline"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
