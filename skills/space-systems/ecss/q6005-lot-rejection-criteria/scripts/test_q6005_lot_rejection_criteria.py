#!/usr/bin/env python3
"""Gate 3 contract test for q6005-lot-rejection-criteria.

Offline, stdlib unittest. Exercises the stage-record validation, the
percentage defective, the accept-number path for a small lot, the
exactly-on-the-limit case, the cumulative criterion and the overall verdict of
ECSS-Q-ST-60-05C clause 10.4.2 as paraphrased in the logic module.

Percentages here are quotients that land exactly on a stated limit in the
cases that decide a lot, and 100*f/u is not correctly rounded to the same
float on every host. Every such bound is asserted with assertAlmostEqual, and
the accept or reject side of it is asserted through exceeds_limit, which
settles the equality with a named tolerance rather than a strict comparison.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_lot_rejection_criteria_logic import (  # noqa: E402
    CUMULATIVE_LIMIT_PERCENT,
    DEFAULT_STAGE_LIMITS,
    SMALL_LOT_THRESHOLD,
    accept_number,
    assess_lot_rejection_criteria,
    cumulative_percent_defective,
    evaluate_stage,
    exceeds_limit,
    percent_defective,
    resolve_limits,
    validate_stage_records,
)


def stage(name="burn-in", units=100, failures=0):
    return {"stage": name, "units_entering": units, "chargeable_failures": failures}


class PercentDefectiveTests(unittest.TestCase):
    def test_no_failures_is_zero_percent(self):
        self.assertAlmostEqual(percent_defective(0, 100), 0.0, places=9)

    def test_percentage_is_failures_over_units_entering(self):
        self.assertAlmostEqual(percent_defective(3, 120), 2.5, places=9)

    def test_every_unit_failing_is_one_hundred_percent(self):
        self.assertAlmostEqual(percent_defective(40, 40), 100.0, places=9)

    def test_failures_above_the_population_are_refused(self):
        with self.assertRaises(ValueError):
            percent_defective(41, 40)

    def test_zero_population_is_refused(self):
        with self.assertRaises(ValueError):
            percent_defective(0, 0)

    def test_non_integer_counts_are_refused(self):
        for bad in (2.5, "3", True, None):
            with self.assertRaises(ValueError):
                percent_defective(bad, 100)


class LimitComparisonTests(unittest.TestCase):
    def test_a_value_on_the_limit_is_inside_it(self):
        observed = percent_defective(5, 100)
        self.assertAlmostEqual(observed, 5.0, places=9)
        self.assertFalse(exceeds_limit(observed, 5.0))

    def test_a_recurring_quotient_landing_on_the_limit_is_inside_it(self):
        # 1/30 of the lot against a limit written as a third of ten percent:
        # the two sides are computed differently and need not be the same float.
        observed = percent_defective(1, 30)
        self.assertAlmostEqual(observed, 10.0 / 3.0, places=9)
        self.assertFalse(exceeds_limit(observed, 10.0 / 3.0))

    def test_one_more_failure_than_the_limit_allows_exceeds_it(self):
        self.assertTrue(exceeds_limit(percent_defective(6, 100), 5.0))

    def test_a_percentage_outside_zero_to_one_hundred_is_refused(self):
        with self.assertRaises(ValueError):
            exceeds_limit(5.0, 120.0)
        with self.assertRaises(ValueError):
            exceeds_limit(-1.0, 5.0)


class AcceptNumberTests(unittest.TestCase):
    def test_accept_number_truncates_the_percentage_of_the_population(self):
        self.assertEqual(accept_number(100, 5.0), 5)
        self.assertEqual(accept_number(150, 5.0), 7)

    def test_a_zero_limit_allows_no_failures_at_any_population(self):
        self.assertEqual(accept_number(1000, 0.0), 0)
        self.assertEqual(accept_number(5, 0.0), 0)

    def test_a_small_lot_falls_back_to_the_absolute_accept_number(self):
        self.assertEqual(accept_number(SMALL_LOT_THRESHOLD - 1, 5.0), 1)

    def test_the_threshold_population_itself_uses_the_percentage(self):
        self.assertEqual(accept_number(SMALL_LOT_THRESHOLD, 5.0), 1)
        self.assertEqual(accept_number(SMALL_LOT_THRESHOLD, 10.0), 2)


class StageRecordValidationTests(unittest.TestCase):
    def test_empty_record_set_is_refused(self):
        with self.assertRaises(ValueError):
            validate_stage_records([])

    def test_mapping_is_not_a_sequence_of_records(self):
        with self.assertRaises(ValueError):
            validate_stage_records(stage())

    def test_record_missing_a_key_is_refused(self):
        for key in ("stage", "units_entering", "chargeable_failures"):
            record = stage()
            del record[key]
            with self.assertRaises(ValueError):
                validate_stage_records([record])

    def test_a_stage_recorded_twice_is_refused(self):
        with self.assertRaises(ValueError):
            validate_stage_records([stage(), stage()])

    def test_a_stage_starting_with_more_units_than_survived_is_refused(self):
        records = [stage("burn-in", 100, 4), stage("final-electrical", 98, 0)]
        with self.assertRaises(ValueError):
            validate_stage_records(records)

    def test_a_consistent_flow_is_accepted(self):
        records = [stage("burn-in", 100, 4), stage("final-electrical", 96, 1)]
        self.assertEqual(len(validate_stage_records(records)), 2)


class StageEvaluationTests(unittest.TestCase):
    def test_a_stage_on_its_limit_is_not_exceeded(self):
        result = evaluate_stage(stage("burn-in", 100, 5))
        self.assertAlmostEqual(result["percent_defective"], 5.0, places=9)
        self.assertAlmostEqual(result["limit_percent"], DEFAULT_STAGE_LIMITS["burn-in"], places=9)
        self.assertFalse(result["exceeded"])
        self.assertEqual(result["criterion"], "percentage")

    def test_a_stage_past_its_limit_is_exceeded(self):
        self.assertTrue(evaluate_stage(stage("burn-in", 100, 6))["exceeded"])

    def test_a_zero_limit_stage_refuses_a_single_failure(self):
        self.assertFalse(evaluate_stage(stage("lot-acceptance-tests", 40, 0))["exceeded"])
        self.assertTrue(evaluate_stage(stage("lot-acceptance-tests", 40, 1))["exceeded"])

    def test_small_lot_is_graded_on_the_accept_number_not_the_percentage(self):
        result = evaluate_stage(stage("burn-in", 10, 1))
        self.assertEqual(result["criterion"], "accept-number")
        self.assertTrue(result["small_lot"])
        self.assertAlmostEqual(result["percent_defective"], 10.0, places=9)
        self.assertFalse(result["exceeded"])

    def test_small_lot_beyond_the_accept_number_is_exceeded(self):
        self.assertTrue(evaluate_stage(stage("burn-in", 10, 2))["exceeded"])

    def test_a_stage_with_no_stated_limit_is_refused(self):
        with self.assertRaises(ValueError):
            evaluate_stage(stage("lid-polishing", 100, 0))

    def test_a_procurement_override_replaces_the_stage_limit(self):
        limits = resolve_limits({"BURN IN": 2.0})
        self.assertAlmostEqual(limits["burn-in"], 2.0, places=9)
        self.assertTrue(evaluate_stage(stage("burn-in", 100, 3), limits)["exceeded"])

    def test_an_override_outside_zero_to_one_hundred_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_limits({"burn-in": 101.0})


class CumulativeTests(unittest.TestCase):
    def test_cumulative_is_measured_against_the_units_that_entered(self):
        records = [stage("burn-in", 200, 4), stage("final-electrical", 196, 6)]
        self.assertAlmostEqual(cumulative_percent_defective(records), 5.0, places=9)

    def test_stages_inside_their_limits_can_still_exceed_the_cumulative_limit(self):
        records = [
            stage("internal-visual", 100, 5),
            stage("burn-in", 95, 4),
            stage("final-electrical", 91, 3),
        ]
        result = assess_lot_rejection_criteria({"stage_records": records})
        self.assertFalse(any(item["exceeded"] for item in result["stages"]))
        self.assertTrue(result["cumulative_exceeded"])
        self.assertAlmostEqual(result["cumulative_percent_defective"], 12.0, places=9)
        self.assertEqual(result["verdict"], "reject")

    def test_cumulative_on_the_limit_is_inside_it(self):
        # Both stages carry a ten percent limit and stay inside it, so the only
        # criterion in play is the cumulative one, and it lands exactly on the
        # limit: ten failures out of the hundred units that entered.
        records = [stage("internal-visual", 100, 5), stage("final-electrical", 95, 5)]
        result = assess_lot_rejection_criteria({"stage_records": records})
        self.assertFalse(any(item["exceeded"] for item in result["stages"]))
        self.assertAlmostEqual(
            result["cumulative_percent_defective"], CUMULATIVE_LIMIT_PERCENT, places=9
        )
        self.assertFalse(result["cumulative_exceeded"])
        self.assertEqual(result["verdict"], "accept")


class AssessmentTests(unittest.TestCase):
    def test_a_clean_lot_is_accepted_with_nothing_exceeded(self):
        records = [stage("burn-in", 100, 0), stage("final-electrical", 100, 0)]
        result = assess_lot_rejection_criteria({"stage_records": records})
        self.assertEqual(result["verdict"], "accept")
        self.assertFalse(result["rejected"])
        self.assertEqual(result["exceeded_limits"], [])
        self.assertAlmostEqual(result["cumulative_percent_defective"], 0.0, places=9)

    def test_an_exceeded_stage_names_the_stage_and_both_numbers(self):
        result = assess_lot_rejection_criteria({"stage_records": [stage("burn-in", 100, 9)]})
        self.assertTrue(result["rejected"])
        self.assertEqual(len(result["exceeded_limits"]), 1)
        self.assertIn("burn-in", result["exceeded_limits"][0])

    def test_small_lot_grading_is_reported_as_a_finding(self):
        result = assess_lot_rejection_criteria({"stage_records": [stage("burn-in", 12, 1)]})
        self.assertTrue(any("accept-number criterion" in f for f in result["findings"]))
        self.assertEqual(result["verdict"], "accept")

    def test_the_total_charged_and_the_entering_population_are_reported(self):
        records = [stage("burn-in", 80, 2), stage("final-electrical", 78, 3)]
        result = assess_lot_rejection_criteria({"stage_records": records})
        self.assertEqual(result["units_entering_screening"], 80)
        self.assertEqual(result["total_chargeable_failures"], 5)

    def test_a_tightened_cumulative_limit_is_honoured(self):
        records = [stage("burn-in", 100, 4)]
        spec = {"stage_records": records, "cumulative_limit_percent": 3.0}
        self.assertEqual(assess_lot_rejection_criteria(spec)["verdict"], "reject")

    def test_missing_stage_records_key_is_refused(self):
        with self.assertRaises(ValueError):
            assess_lot_rejection_criteria({})

    def test_a_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_lot_rejection_criteria([stage()])


if __name__ == "__main__":
    unittest.main(verbosity=2)
