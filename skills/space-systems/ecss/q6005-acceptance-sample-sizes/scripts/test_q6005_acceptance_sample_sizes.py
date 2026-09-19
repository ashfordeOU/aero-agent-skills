#!/usr/bin/env python3
"""Gate 3 contract test for q6005-acceptance-sample-sizes.

Offline, stdlib unittest. Exercises the batch validation, the schedule
validation, the band lookup, the full-inspection collapse, the cap of the
sample at the batch, the sampling fraction, the destructive-shortfall check
and the accept/reject disposition of ECSS-Q-ST-60-05C clause 12.1.2 as
paraphrased in the logic module. Sampling fractions land exactly on simple
quotients, so those are asserted with assertAlmostEqual rather than a strict
inequality that libm could round either way between build host and CI runner.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_acceptance_sample_sizes_logic import (  # noqa: E402
    DEFAULT_SAMPLE_SCHEDULE,
    FULL_INSPECTION_THRESHOLD,
    acceptance_number_for,
    assess_acceptance_sampling,
    batch_disposition,
    destructive_sample_shortfall,
    sampling_fraction,
    schedule_band,
    select_sample_plan,
    validate_batch_size,
    validate_schedule,
)


class BatchValidationTests(unittest.TestCase):
    def test_positive_batch_size_is_returned(self):
        self.assertEqual(validate_batch_size(250), 250)

    def test_zero_and_negative_batches_are_refused(self):
        for bad in (0, -1, -400):
            with self.assertRaises(ValueError):
                validate_batch_size(bad)

    def test_boolean_batch_size_is_refused(self):
        with self.assertRaises(ValueError):
            validate_batch_size(True)

    def test_non_integer_batch_size_is_refused(self):
        for bad in (12.5, "40", None):
            with self.assertRaises(ValueError):
                validate_batch_size(bad)


class ScheduleValidationTests(unittest.TestCase):
    def test_default_schedule_validates(self):
        self.assertEqual(len(validate_schedule(DEFAULT_SAMPLE_SCHEDULE)), 10)

    def test_empty_schedule_is_refused(self):
        with self.assertRaises(ValueError):
            validate_schedule([])

    def test_schedule_with_a_gap_is_refused(self):
        with self.assertRaises(ValueError):
            validate_schedule([(1, 10, 5, 0), (12, None, 8, 0)])

    def test_overlapping_bands_are_refused(self):
        with self.assertRaises(ValueError):
            validate_schedule([(1, 10, 5, 0), (8, None, 8, 0)])

    def test_open_ended_band_in_the_middle_is_refused(self):
        with self.assertRaises(ValueError):
            validate_schedule([(1, None, 5, 0), (20, 40, 8, 0)])

    def test_acceptance_number_at_or_above_the_sample_is_refused(self):
        with self.assertRaises(ValueError):
            validate_schedule([(1, None, 5, 5)])

    def test_malformed_band_tuple_is_refused(self):
        with self.assertRaises(ValueError):
            validate_schedule([(1, 10, 5)])

    def test_band_ending_below_its_start_is_refused(self):
        with self.assertRaises(ValueError):
            validate_schedule([(1, 10, 5, 0), (11, 10, 5, 0)])


class BandLookupTests(unittest.TestCase):
    def test_batch_lands_in_the_band_that_contains_it(self):
        self.assertEqual(schedule_band(100), (91, 150, 50, 1))

    def test_band_boundaries_are_inclusive_at_both_ends(self):
        self.assertEqual(schedule_band(91)[0], 91)
        self.assertEqual(schedule_band(150)[1], 150)

    def test_very_large_batch_falls_in_the_open_ended_band(self):
        self.assertEqual(schedule_band(50000)[1], None)


class SamplePlanTests(unittest.TestCase):
    def test_small_batch_collapses_to_full_inspection(self):
        plan = select_sample_plan(6)
        self.assertTrue(plan["full_inspection"])
        self.assertEqual(plan["sample_size"], 6)
        self.assertEqual(plan["acceptance_number"], 0)

    def test_threshold_batch_is_still_full_inspection(self):
        self.assertTrue(select_sample_plan(FULL_INSPECTION_THRESHOLD)["full_inspection"])

    def test_sample_is_capped_at_the_batch_inside_a_band(self):
        # Band 9..15 asks for 8 units, which a batch of 9 can supply; a band
        # whose sample exceeds its own low end is what the cap exists for.
        plan = select_sample_plan(20, schedule=[(1, None, 40, 1)], full_inspection_threshold=2)
        self.assertEqual(plan["sample_size"], 20)
        self.assertTrue(plan["capped_to_batch"])
        self.assertTrue(plan["full_inspection"])

    def test_large_batch_takes_the_scheduled_sample_not_the_whole_batch(self):
        plan = select_sample_plan(800)
        self.assertEqual(plan["sample_size"], 200)
        self.assertFalse(plan["full_inspection"])
        self.assertEqual(plan["acceptance_number"], 3)

    def test_sample_size_never_exceeds_the_batch_across_the_schedule(self):
        for size in (1, 5, 9, 16, 26, 51, 91, 151, 281, 501, 1201, 9000):
            plan = select_sample_plan(size)
            self.assertLessEqual(plan["sample_size"], plan["batch_size"])

    def test_acceptance_number_helper_agrees_with_the_plan(self):
        self.assertEqual(acceptance_number_for(400), 2)
        self.assertEqual(acceptance_number_for(4), 0)


class SamplingFractionTests(unittest.TestCase):
    def test_full_inspection_samples_the_whole_batch(self):
        self.assertAlmostEqual(sampling_fraction(5), 1.0, places=9)

    def test_fraction_is_the_sample_over_the_batch(self):
        self.assertAlmostEqual(sampling_fraction(1000), 0.2, places=9)

    def test_fraction_falls_as_the_batch_grows_within_a_band(self):
        self.assertAlmostEqual(sampling_fraction(100), 0.5, places=9)
        self.assertAlmostEqual(sampling_fraction(150), 50 / 150.0, places=9)


class DestructiveSampleTests(unittest.TestCase):
    def test_batch_carrying_sample_and_order_has_no_shortfall(self):
        self.assertEqual(destructive_sample_shortfall(1000, 800), 0)

    def test_order_taking_the_whole_batch_leaves_the_sample_short(self):
        self.assertEqual(destructive_sample_shortfall(1000, 1000), 200)

    def test_shortfall_is_exactly_the_missing_units(self):
        self.assertEqual(destructive_sample_shortfall(1000, 850), 50)

    def test_non_positive_deliverable_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            destructive_sample_shortfall(1000, 0)


class DispositionTests(unittest.TestCase):
    def test_clean_sample_accepts_the_batch(self):
        result = batch_disposition(800, 0)
        self.assertEqual(result["disposition"], "accept")
        self.assertEqual(result["margin"], 3)

    def test_failures_at_the_acceptance_number_still_accept(self):
        self.assertTrue(batch_disposition(800, 3)["accepted"])

    def test_one_failure_past_the_acceptance_number_rejects(self):
        self.assertEqual(batch_disposition(800, 4)["disposition"], "reject")

    def test_any_failure_rejects_a_zero_acceptance_band(self):
        self.assertEqual(batch_disposition(30, 1)["disposition"], "reject")

    def test_more_failures_than_units_sampled_is_refused(self):
        with self.assertRaises(ValueError):
            batch_disposition(30, 21)

    def test_negative_failure_count_is_refused(self):
        with self.assertRaises(ValueError):
            batch_disposition(30, -1)


class AssessmentTests(unittest.TestCase):
    def test_workable_plan_reports_no_findings(self):
        result = assess_acceptance_sampling({"batch_size": 800, "nonconforming_found": 1})
        self.assertTrue(result["plan_is_workable"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["disposition"], "accept")
        self.assertAlmostEqual(result["sampling_fraction"], 0.25, places=9)

    def test_plan_landing_exactly_on_the_minimum_fraction_meets_it(self):
        result = assess_acceptance_sampling({"batch_size": 1000, "minimum_fraction": 0.2})
        self.assertTrue(result["meets_minimum_fraction"])
        self.assertAlmostEqual(result["sampling_fraction"], 0.2, places=9)

    def test_plan_below_the_minimum_fraction_is_flagged(self):
        result = assess_acceptance_sampling({"batch_size": 5000, "minimum_fraction": 0.2})
        self.assertFalse(result["meets_minimum_fraction"])
        self.assertFalse(result["plan_is_workable"])

    def test_destructive_plan_without_a_deliverable_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            assess_acceptance_sampling({"batch_size": 800, "destructive": True})

    def test_destructive_plan_short_of_the_order_is_flagged(self):
        result = assess_acceptance_sampling(
            {"batch_size": 1000, "destructive": True, "deliverable_quantity": 900}
        )
        self.assertEqual(result["destructive_shortfall"], 100)
        self.assertFalse(result["plan_is_workable"])

    def test_destructive_full_inspection_leaves_nothing_to_ship(self):
        result = assess_acceptance_sampling(
            {"batch_size": 5, "destructive": True, "deliverable_quantity": 1}
        )
        self.assertTrue(any("no unit" in f for f in result["findings"]))

    def test_rejecting_sample_result_appears_in_the_findings(self):
        result = assess_acceptance_sampling({"batch_size": 800, "nonconforming_found": 9})
        self.assertEqual(result["disposition"], "reject")
        self.assertFalse(result["plan_is_workable"])

    def test_missing_batch_size_is_refused(self):
        with self.assertRaises(ValueError):
            assess_acceptance_sampling({"nonconforming_found": 0})

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_acceptance_sampling([("batch_size", 100)])

    def test_out_of_range_minimum_fraction_is_refused(self):
        for bad in (0.0, 1.5, -0.2):
            with self.assertRaises(ValueError):
                assess_acceptance_sampling({"batch_size": 800, "minimum_fraction": bad})

    def test_non_boolean_destructive_flag_is_refused(self):
        with self.assertRaises(ValueError):
            assess_acceptance_sampling({"batch_size": 800, "destructive": "yes"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
