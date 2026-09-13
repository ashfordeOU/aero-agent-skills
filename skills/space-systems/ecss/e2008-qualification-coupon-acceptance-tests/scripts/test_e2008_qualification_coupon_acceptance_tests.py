"""Contract tests for the clause 5.5.2 qualification-coupon acceptance logic."""

import unittest

from e2008_qualification_coupon_acceptance_tests_logic import (
    SEVERITY_GRADES,
    assess_coupon_lot,
    evaluate_check,
    evaluate_coupon,
    group_imperfections,
    margin_fraction,
    required_sample_size,
)

CRITERIA = [
    {"name": "interconnect_peel_strength_n_per_cm", "limit": 2.0, "direction": "min"},
    {"name": "joint_resistance_mohm", "limit": 5.0, "direction": "max"},
    {"name": "illuminated_power_w", "limit": 1.6, "direction": "min"},
]

GOOD_MEASUREMENTS = {
    "interconnect_peel_strength_n_per_cm": 3.0,
    "joint_resistance_mohm": 3.0,
    "illuminated_power_w": 1.8,
}


def _coupon(coupon_id, measurements=None, imperfections=None):
    coupon = {"id": coupon_id, "measurements": dict(measurements or GOOD_MEASUREMENTS)}
    if imperfections is not None:
        coupon["imperfections"] = imperfections
    return coupon


def _spec(**overrides):
    spec = {
        "lot_size": 30,
        "coupons": [_coupon("c1"), _coupon("c2"), _coupon("c3")],
        "criteria": CRITERIA,
        "allowances": {"critical": 0, "major": 1, "minor": 6},
    }
    spec.update(overrides)
    return spec


class SampleSizeTests(unittest.TestCase):
    def test_proportional_sample_of_a_large_lot(self):
        self.assertEqual(required_sample_size(200, 0.10, 3), 20)

    def test_float_product_does_not_round_up_a_whole_coupon(self):
        self.assertEqual(required_sample_size(30, 0.10, 3), 3)

    def test_floor_applies_to_a_small_lot(self):
        self.assertEqual(required_sample_size(10, 0.10, 3), 3)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(required_sample_size(2, 0.10, 3), 2)

    def test_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size(30, 1.5, 3)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size(0, 0.10, 3)

    def test_non_integer_lot_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size(30.0, 0.10, 3)


class MarginTests(unittest.TestCase):
    def test_min_direction_rewards_exceeding_the_limit(self):
        self.assertAlmostEqual(margin_fraction(3.0, 2.0, "min"), 0.5, places=9)

    def test_max_direction_rewards_staying_under_the_limit(self):
        self.assertAlmostEqual(margin_fraction(4.0, 5.0, "max"), 0.2, places=9)

    def test_measurement_on_the_limit_gives_zero_margin(self):
        self.assertAlmostEqual(margin_fraction(2.0, 2.0, "min"), 0.0, places=9)

    def test_min_direction_shortfall_is_negative(self):
        self.assertAlmostEqual(margin_fraction(1.0, 2.0, "min"), -0.5, places=9)

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            margin_fraction(3.0, 2.0, "either")

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            margin_fraction(3.0, 0.0, "min")


class CheckTests(unittest.TestCase):
    def test_conforming_check(self):
        record = evaluate_check(
            {"name": "peel", "measured": 3.0, "limit": 2.0, "direction": "min"}
        )
        self.assertTrue(record["conforms"])

    def test_check_exactly_on_the_limit_conforms(self):
        record = evaluate_check(
            {"name": "peel", "measured": 2.0, "limit": 2.0, "direction": "min"}
        )
        self.assertTrue(record["conforms"])
        self.assertAlmostEqual(record["margin_fraction"], 0.0, places=9)

    def test_failing_check(self):
        record = evaluate_check(
            {"name": "resistance", "measured": 9.0, "limit": 5.0, "direction": "max"}
        )
        self.assertFalse(record["conforms"])

    def test_check_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_check({"name": "peel", "measured": 3.0, "limit": 2.0})

    def test_blank_check_name_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_check(
                {"name": "   ", "measured": 3.0, "limit": 2.0, "direction": "min"}
            )


class CouponTests(unittest.TestCase):
    def test_conforming_coupon_lists_no_failures(self):
        record = evaluate_coupon(_coupon("c1"), CRITERIA)
        self.assertTrue(record["conforms"])
        self.assertEqual(record["failed_checks"], [])

    def test_one_record_per_criterion(self):
        record = evaluate_coupon(_coupon("c1"), CRITERIA)
        self.assertEqual(len(record["checks"]), len(CRITERIA))

    def test_failed_check_is_named(self):
        weak = dict(GOOD_MEASUREMENTS)
        weak["interconnect_peel_strength_n_per_cm"] = 0.5
        record = evaluate_coupon(_coupon("c1", weak), CRITERIA)
        self.assertFalse(record["conforms"])
        self.assertEqual(record["failed_checks"], ["interconnect_peel_strength_n_per_cm"])

    def test_absent_imperfection_map_is_zero_filled(self):
        record = evaluate_coupon(_coupon("c1"), CRITERIA)
        self.assertEqual(record["imperfections"], {g: 0 for g in SEVERITY_GRADES})

    def test_missing_measurement_rejected(self):
        partial = dict(GOOD_MEASUREMENTS)
        del partial["joint_resistance_mohm"]
        with self.assertRaises(ValueError):
            evaluate_coupon(_coupon("c1", partial), CRITERIA)

    def test_unknown_severity_grade_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_coupon(_coupon("c1", None, {"cosmetic": 1}), CRITERIA)

    def test_negative_imperfection_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_coupon(_coupon("c1", None, {"minor": -1}), CRITERIA)

    def test_duplicate_criterion_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_coupon(_coupon("c1"), CRITERIA + [CRITERIA[0]])

    def test_empty_criteria_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_coupon(_coupon("c1"), [])

    def test_blank_coupon_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_coupon(_coupon("  "), CRITERIA)


class GroupingTests(unittest.TestCase):
    def test_totals_sum_across_coupons(self):
        records = [
            evaluate_coupon(_coupon("c1", None, {"minor": 2}), CRITERIA),
            evaluate_coupon(_coupon("c2", None, {"minor": 3, "major": 1}), CRITERIA),
        ]
        totals = group_imperfections(records)
        self.assertEqual(totals["minor"], 5)
        self.assertEqual(totals["major"], 1)
        self.assertEqual(totals["critical"], 0)

    def test_empty_set_gives_zero_totals(self):
        self.assertEqual(group_imperfections([]), {g: 0 for g in SEVERITY_GRADES})

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            group_imperfections([{"id": "c1"}])


class LotAssessmentTests(unittest.TestCase):
    def test_clean_lot_is_accepted(self):
        result = assess_coupon_lot(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_required_sample_size_is_reported(self):
        result = assess_coupon_lot(_spec())
        self.assertEqual(result["required_sample_size"], 3)
        self.assertEqual(result["sample_size"], 3)

    def test_undersized_sample_is_flagged(self):
        result = assess_coupon_lot(_spec(lot_size=200))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("below the 20" in f for f in result["findings"]))

    def test_failing_coupon_blocks_acceptance(self):
        bad = dict(GOOD_MEASUREMENTS)
        bad["joint_resistance_mohm"] = 12.0
        spec = _spec(coupons=[_coupon("c1"), _coupon("c2"), _coupon("c3", bad)])
        result = assess_coupon_lot(spec)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("coupon 'c3' fails" in f for f in result["findings"]))

    def test_workmanship_conformance_is_the_passing_fraction(self):
        bad = dict(GOOD_MEASUREMENTS)
        bad["joint_resistance_mohm"] = 12.0
        spec = _spec(coupons=[_coupon("c1"), _coupon("c2"), _coupon("c3", bad)])
        result = assess_coupon_lot(spec)
        self.assertAlmostEqual(result["workmanship_conformance"], 2.0 / 3.0, places=9)

    def test_critical_imperfection_blocks_acceptance(self):
        spec = _spec(
            coupons=[_coupon("c1", None, {"critical": 1}), _coupon("c2"), _coupon("c3")]
        )
        result = assess_coupon_lot(spec)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("critical workmanship" in f for f in result["findings"]))

    def test_grade_total_exactly_on_the_allowance_is_accepted(self):
        spec = _spec(
            coupons=[_coupon("c1", None, {"major": 1}), _coupon("c2"), _coupon("c3")]
        )
        result = assess_coupon_lot(spec)
        self.assertEqual(result["imperfection_totals"]["major"], 1)
        self.assertTrue(result["accepted"])

    def test_grade_total_one_over_the_allowance_is_flagged(self):
        spec = _spec(
            coupons=[
                _coupon("c1", None, {"major": 1}),
                _coupon("c2", None, {"major": 1}),
                _coupon("c3"),
            ]
        )
        result = assess_coupon_lot(spec)
        self.assertFalse(result["accepted"])

    def test_more_coupons_than_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_coupon_lot(_spec(lot_size=2))

    def test_duplicate_coupon_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_coupon_lot(
                _spec(coupons=[_coupon("c1"), _coupon("c1"), _coupon("c3")])
            )

    def test_empty_coupon_sample_rejected(self):
        with self.assertRaises(ValueError):
            assess_coupon_lot(_spec(coupons=[]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["allowances"]
        with self.assertRaises(ValueError):
            assess_coupon_lot(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_coupon_lot(["lot_size"])

    def test_unknown_allowance_grade_rejected(self):
        with self.assertRaises(ValueError):
            assess_coupon_lot(_spec(allowances={"cosmetic": 2}))


if __name__ == "__main__":
    unittest.main()
