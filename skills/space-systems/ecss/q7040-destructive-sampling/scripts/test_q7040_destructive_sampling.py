#!/usr/bin/env python3
"""Contract test for destructive sampling of brazements (offline)."""

import copy
import unittest

from q7040_destructive_sampling_logic import (
    COUPON_SWITCH_FRACTION,
    GEOMETRY_BUTT,
    GEOMETRY_FILLET,
    GEOMETRY_LAP,
    LOT_ACCEPTED,
    LOT_REJECTED,
    LOT_RESAMPLE,
    STRATEGY_COUPONS,
    STRATEGY_SAMPLE_LOT,
    TEST_METALLOGRAPHIC,
    TEST_PEEL,
    TEST_TENSILE_SHEAR,
    applicable_tests,
    assess_lot,
    evaluate_section,
    sample_size,
    sampling_plan,
)


def _sample(sample_id, coverage=92.0, voids=4.0, longest=2.0):
    return {
        "sample_id": sample_id,
        "coverage_pct": coverage,
        "void_pct": voids,
        "longest_continuous_void_pct": longest,
    }


GOOD_CASE = {
    "lot_id": "LOT-9001",
    "lot_size": 200,
    "criticality": "major",
    "geometry": GEOMETRY_BUTT,
    "samples": [_sample("S%d" % i) for i in range(1, 7)],
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class ApplicableTestTests(unittest.TestCase):
    def test_a_lap_joint_can_be_peeled(self):
        self.assertIn(TEST_PEEL, applicable_tests(GEOMETRY_LAP))

    def test_a_butt_joint_cannot_be_peeled(self):
        self.assertNotIn(TEST_PEEL, applicable_tests(GEOMETRY_BUTT))
        self.assertIn(TEST_TENSILE_SHEAR, applicable_tests(GEOMETRY_BUTT))

    def test_every_geometry_can_at_least_be_sectioned(self):
        for geometry in (GEOMETRY_LAP, GEOMETRY_BUTT, GEOMETRY_FILLET):
            self.assertIn(TEST_METALLOGRAPHIC, applicable_tests(geometry))

    def test_an_unknown_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            applicable_tests("glued-joint")


class SampleSizeTests(unittest.TestCase):
    def test_a_critical_lot_is_sampled_harder_than_a_minor_one(self):
        self.assertGreater(sample_size(200, "critical"), sample_size(200, "minor"))

    def test_a_small_critical_lot_still_hits_the_floor(self):
        self.assertEqual(sample_size(3, "critical"), 2)

    def test_a_very_large_lot_is_held_at_the_ceiling(self):
        self.assertEqual(sample_size(100000, "critical"), 10)
        self.assertEqual(sample_size(100000, "minor"), 3)

    def test_the_plan_never_asks_for_more_joints_than_the_lot_has(self):
        self.assertLessEqual(sample_size(1, "critical"), 1)

    def test_a_zero_lot_size_is_rejected(self):
        with self.assertRaises(ValueError):
            sample_size(0, "major")

    def test_a_non_integer_lot_size_is_rejected(self):
        with self.assertRaises(ValueError):
            sample_size(12.5, "major")


class SamplingPlanTests(unittest.TestCase):
    def test_a_large_lot_is_sampled_from_the_lot_itself(self):
        plan = sampling_plan(400, "critical", GEOMETRY_LAP)
        self.assertEqual(plan["strategy"], STRATEGY_SAMPLE_LOT)
        self.assertFalse(plan["coupons_required"])

    def test_a_tiny_lot_switches_to_representative_coupons(self):
        plan = sampling_plan(4, "critical", GEOMETRY_LAP)
        self.assertEqual(plan["strategy"], STRATEGY_COUPONS)
        self.assertTrue(plan["coupon_rationale"])

    def test_a_plan_exactly_on_the_switch_fraction_still_samples_the_lot(self):
        plan = sampling_plan(8, "critical", GEOMETRY_LAP)
        self.assertAlmostEqual(
            plan["sampled_fraction"], COUPON_SWITCH_FRACTION, places=9
        )
        self.assertEqual(plan["strategy"], STRATEGY_SAMPLE_LOT)

    def test_the_plan_carries_the_tests_the_geometry_allows(self):
        plan = sampling_plan(400, "major", GEOMETRY_FILLET)
        self.assertEqual(plan["applicable_tests"], [TEST_METALLOGRAPHIC])


class SectionReadingTests(unittest.TestCase):
    def test_a_sound_section_is_acceptable(self):
        result = evaluate_section(_sample("S1"), "major")
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_short_coverage_fails_the_section(self):
        result = evaluate_section(_sample("S1", coverage=50.0), "major")
        self.assertFalse(result["acceptable"])

    def test_coverage_exactly_on_the_limit_passes(self):
        result = evaluate_section(_sample("S1", coverage=75.0), "major")
        self.assertAlmostEqual(
            result["coverage_pct"], result["minimum_coverage_pct"], places=9
        )
        self.assertTrue(result["acceptable"])

    def test_the_same_section_can_pass_as_minor_and_fail_as_critical(self):
        sample = _sample("S1", coverage=70.0, voids=12.0, longest=6.0)
        self.assertTrue(evaluate_section(sample, "minor")["acceptable"])
        self.assertFalse(evaluate_section(sample, "critical")["acceptable"])

    def test_scattered_voids_pass_where_the_same_area_joined_up_fails(self):
        scattered = _sample("S1", coverage=88.0, voids=9.0, longest=2.0)
        joined = _sample("S2", coverage=88.0, voids=9.0, longest=9.0)
        self.assertTrue(evaluate_section(scattered, "critical")["acceptable"])
        self.assertFalse(evaluate_section(joined, "critical")["acceptable"])

    def test_a_continuous_void_larger_than_the_total_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_section(_sample("S1", voids=3.0, longest=8.0), "major")

    def test_coverage_plus_voids_over_the_faying_area_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_section(_sample("S1", coverage=98.0, voids=9.0), "major")

    def test_a_percentage_outside_zero_to_one_hundred_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_section(_sample("S1", coverage=140.0), "major")

    def test_a_section_without_an_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_section(_sample(""), "major")


class LotDispositionTests(unittest.TestCase):
    def test_a_fully_sampled_sound_lot_is_accepted(self):
        result = assess_lot(_case())
        self.assertEqual(result["disposition"], LOT_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_one_failure_on_a_major_lot_goes_to_double_sampling(self):
        samples = [_sample("S%d" % i) for i in range(1, 6)]
        samples.append(_sample("S6", coverage=40.0))
        result = assess_lot(_case(samples=samples))
        self.assertEqual(result["disposition"], LOT_RESAMPLE)
        self.assertEqual(result["failed_samples"], ["S6"])

    def test_a_failure_after_a_resample_rejects_the_lot(self):
        samples = [_sample("S%d" % i) for i in range(1, 6)]
        samples.append(_sample("S6", coverage=40.0))
        result = assess_lot(_case(samples=samples, already_resampled=True))
        self.assertEqual(result["disposition"], LOT_REJECTED)

    def test_one_failure_on_a_critical_lot_rejects_it_outright(self):
        samples = [_sample("S%d" % i) for i in range(1, 10)]
        samples.append(_sample("S10", coverage=40.0))
        result = assess_lot(
            _case(criticality="critical", samples=samples, lot_size=200)
        )
        self.assertEqual(result["disposition"], LOT_REJECTED)

    def test_two_failures_reject_a_major_lot_without_a_resample(self):
        samples = [_sample("S%d" % i) for i in range(1, 5)]
        samples.append(_sample("S5", coverage=40.0))
        samples.append(_sample("S6", coverage=41.0))
        result = assess_lot(_case(samples=samples))
        self.assertEqual(result["disposition"], LOT_REJECTED)

    def test_an_under_sampled_lot_is_held_rather_than_accepted(self):
        result = assess_lot(_case(samples=[_sample("S1")]))
        self.assertNotEqual(result["disposition"], LOT_ACCEPTED)

    def test_a_lot_without_an_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot(_case(lot_id=""))

    def test_samples_that_are_not_a_sequence_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot(_case(samples="four of them"))

    def test_a_non_boolean_resample_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot(_case(already_resampled="once"))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot("we cut two of them open")


if __name__ == "__main__":
    unittest.main()
