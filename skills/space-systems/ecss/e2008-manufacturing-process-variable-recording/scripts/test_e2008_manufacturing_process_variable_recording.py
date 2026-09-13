#!/usr/bin/env python3
"""Contract test for pre-production process-variable recording (offline)."""

import copy
import math
import unittest

from e2008_manufacturing_process_variable_recording_logic import (
    GOVERNING_SHARE,
    IDENTIFICATION_LATE,
    RECORDING_GAP,
    RECORDING_METHODS,
    RECORDING_READY,
    SAMPLED_SHARE,
    VERDICT_RANK,
    assess_variable,
    combined_swing,
    control_band_width,
    influence_share,
    plan_process_variable_recording,
    potential_performance_swing,
    rank_variables,
    recording_is_adequate,
    required_recording_method,
)

TOLERANCE = 0.03

REFLOW = {
    "name": "solder-reflow-peak-temperature",
    "units": "degC",
    "sensitivity_per_unit": 0.0015,
    "band_min": 225.0,
    "band_max": 245.0,
    "recording_method": "continuous-logged",
    "identified_before_production": True,
}

CURE_DWELL = {
    "name": "laminate-cure-dwell-time",
    "units": "minutes",
    "sensitivity_per_unit": 0.0005,
    "band_min": 20.0,
    "band_max": 40.0,
    "recording_method": "per-lot-sampled",
    "identified_before_production": True,
}

HUMIDITY = {
    "name": "bonding-cell-relative-humidity",
    "units": "percent-rh",
    "sensitivity_per_unit": 0.0001,
    "band_min": 35.0,
    "band_max": 55.0,
    "recording_method": "witness-coupon-only",
    "identified_before_production": True,
}

READY_CASE = {
    "performance_tolerance": TOLERANCE,
    "variables": [REFLOW, CURE_DWELL, HUMIDITY],
}


def _variable(base, **overrides):
    item = copy.deepcopy(base)
    item.update(overrides)
    return item


class BandTests(unittest.TestCase):
    def test_band_width_is_the_span_of_the_control_band(self):
        self.assertAlmostEqual(control_band_width(225.0, 245.0), 20.0, places=9)

    def test_a_band_crossing_zero_is_still_a_span(self):
        self.assertAlmostEqual(control_band_width(-5.0, 15.0), 20.0, places=9)

    def test_zero_width_band_rejected(self):
        with self.assertRaises(ValueError):
            control_band_width(230.0, 230.0)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            control_band_width(245.0, 225.0)

    def test_non_numeric_band_rejected(self):
        with self.assertRaises(ValueError):
            control_band_width("225 C", 245.0)


class SwingTests(unittest.TestCase):
    def test_swing_is_sensitivity_across_the_whole_band(self):
        self.assertAlmostEqual(
            potential_performance_swing(0.0015, 225.0, 245.0), 0.03, places=12
        )

    def test_a_negative_sensitivity_swings_just_as_far(self):
        self.assertAlmostEqual(
            potential_performance_swing(-0.0015, 225.0, 245.0), 0.03, places=12
        )

    def test_share_is_the_swing_against_the_tolerance(self):
        self.assertAlmostEqual(influence_share(0.01, TOLERANCE), 1.0 / 3.0, places=9)

    def test_a_variable_filling_the_tolerance_has_a_share_of_one(self):
        self.assertAlmostEqual(
            influence_share(potential_performance_swing(0.0015, 225.0, 245.0), TOLERANCE),
            GOVERNING_SHARE,
            places=9,
        )

    def test_zero_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            influence_share(0.01, 0.0)

    def test_negative_swing_rejected(self):
        with self.assertRaises(ValueError):
            influence_share(-0.01, TOLERANCE)


class RequiredMethodTests(unittest.TestCase):
    def test_a_tolerance_filling_variable_is_logged_continuously(self):
        self.assertEqual(required_recording_method(1.4), "continuous-logged")

    def test_a_quarter_tolerance_variable_is_sampled_per_lot(self):
        self.assertEqual(required_recording_method(0.4), "per-lot-sampled")

    def test_a_small_variable_still_earns_a_witness_record(self):
        self.assertEqual(required_recording_method(0.05), "witness-coupon-only")

    def test_a_share_a_hair_below_the_governing_bound_still_governs(self):
        just_under = math.nextafter(GOVERNING_SHARE, 0.0)
        self.assertAlmostEqual(just_under, GOVERNING_SHARE, places=9)
        self.assertEqual(required_recording_method(just_under), "continuous-logged")

    def test_a_share_a_hair_below_the_sampling_bound_still_samples(self):
        just_under = math.nextafter(SAMPLED_SHARE, 0.0)
        self.assertAlmostEqual(just_under, SAMPLED_SHARE, places=9)
        self.assertEqual(required_recording_method(just_under), "per-lot-sampled")

    def test_negative_share_rejected(self):
        with self.assertRaises(ValueError):
            required_recording_method(-0.1)

    def test_no_required_method_is_ever_no_record(self):
        for share in (0.0, 0.1, 0.25, 0.9, 1.0, 5.0):
            self.assertNotEqual(required_recording_method(share), "not-recorded")


class AdequacyTests(unittest.TestCase):
    def test_matching_the_required_method_is_adequate(self):
        self.assertTrue(
            recording_is_adequate("per-lot-sampled", "per-lot-sampled")
        )

    def test_exceeding_the_required_method_is_adequate(self):
        self.assertTrue(
            recording_is_adequate("continuous-logged", "witness-coupon-only")
        )

    def test_falling_short_of_the_required_method_is_not(self):
        self.assertFalse(
            recording_is_adequate("witness-coupon-only", "continuous-logged")
        )

    def test_not_recorded_never_satisfies_anything(self):
        for required in RECORDING_METHODS[:-1]:
            self.assertFalse(recording_is_adequate("not-recorded", required))

    def test_unknown_declared_method_rejected(self):
        with self.assertRaises(ValueError):
            recording_is_adequate("written-on-a-board", "per-lot-sampled")


class CombinationTests(unittest.TestCase):
    def test_root_sum_square_of_one_swing_is_that_swing(self):
        self.assertAlmostEqual(combined_swing([0.03]), 0.03, places=12)

    def test_root_sum_square_combines_independent_swings(self):
        self.assertAlmostEqual(
            combined_swing([0.03, 0.04]), 0.05, places=12
        )

    def test_linear_combination_is_the_worst_case_stack(self):
        self.assertAlmostEqual(
            combined_swing([0.03, 0.04], method="linear"), 0.07, places=12
        )

    def test_empty_swing_list_combines_to_zero(self):
        self.assertAlmostEqual(combined_swing([]), 0.0, places=12)

    def test_unknown_combination_method_rejected(self):
        with self.assertRaises(ValueError):
            combined_swing([0.03], method="average")

    def test_negative_swing_in_the_list_rejected(self):
        with self.assertRaises(ValueError):
            combined_swing([0.03, -0.01])


class VariableAssessmentTests(unittest.TestCase):
    def test_a_continuously_logged_governing_variable_is_ready(self):
        result = assess_variable(REFLOW, TOLERANCE)
        self.assertEqual(result["verdict"], RECORDING_READY)
        self.assertEqual(result["required_recording_method"], "continuous-logged")
        self.assertAlmostEqual(result["influence_share"], 1.0, places=9)

    def test_a_mid_influence_variable_needs_per_lot_sampling(self):
        result = assess_variable(CURE_DWELL, TOLERANCE)
        self.assertEqual(result["required_recording_method"], "per-lot-sampled")
        self.assertTrue(result["recording_adequate"])

    def test_under_recording_opens_a_gap(self):
        result = assess_variable(
            _variable(CURE_DWELL, recording_method="witness-coupon-only"), TOLERANCE
        )
        self.assertEqual(result["verdict"], RECORDING_GAP)
        self.assertFalse(result["recording_adequate"])
        self.assertTrue(any("per-lot-sampled is required" in f for f in result["findings"]))

    def test_a_variable_named_after_production_started_is_late(self):
        result = assess_variable(
            _variable(REFLOW, identified_before_production=False), TOLERANCE
        )
        self.assertEqual(result["verdict"], IDENTIFICATION_LATE)
        self.assertTrue(any("after production started" in f for f in result["findings"]))

    def test_a_small_variable_with_a_witness_record_is_ready(self):
        self.assertEqual(assess_variable(HUMIDITY, TOLERANCE)["verdict"], RECORDING_READY)

    def test_an_unrecorded_variable_is_never_ready(self):
        result = assess_variable(
            _variable(HUMIDITY, recording_method="not-recorded"), TOLERANCE
        )
        self.assertEqual(result["verdict"], RECORDING_GAP)

    def test_missing_units_rejected(self):
        broken = copy.deepcopy(REFLOW)
        del broken["units"]
        with self.assertRaises(ValueError):
            assess_variable(broken, TOLERANCE)

    def test_non_boolean_identification_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_variable(
                _variable(REFLOW, identified_before_production="yes"), TOLERANCE
            )

    def test_unknown_recording_method_rejected(self):
        with self.assertRaises(ValueError):
            assess_variable(_variable(REFLOW, recording_method="logged-somewhere"), TOLERANCE)

    def test_non_mapping_variable_rejected(self):
        with self.assertRaises(ValueError):
            assess_variable("solder-reflow-peak-temperature", TOLERANCE)


class RankingTests(unittest.TestCase):
    def test_the_largest_swing_ranks_first(self):
        assessments = [assess_variable(v, TOLERANCE) for v in (HUMIDITY, REFLOW, CURE_DWELL)]
        self.assertEqual(
            rank_variables(assessments)[0]["name"], "solder-reflow-peak-temperature"
        )

    def test_the_smallest_swing_ranks_last(self):
        assessments = [assess_variable(v, TOLERANCE) for v in (HUMIDITY, REFLOW, CURE_DWELL)]
        self.assertEqual(
            rank_variables(assessments)[-1]["name"], "bonding-cell-relative-humidity"
        )

    def test_empty_assessment_list_rejected(self):
        with self.assertRaises(ValueError):
            rank_variables([])


class PlanTests(unittest.TestCase):
    def test_a_fully_planned_variable_list_is_ready(self):
        result = plan_process_variable_recording(READY_CASE)
        self.assertEqual(result["verdict"], RECORDING_READY)
        self.assertEqual(result["governing_variable"], "solder-reflow-peak-temperature")
        self.assertAlmostEqual(result["unlogged_swing"], 0.0, places=12)

    def test_combined_swing_is_the_root_sum_square_of_the_list(self):
        result = plan_process_variable_recording(READY_CASE)
        self.assertAlmostEqual(result["combined_swing"], math.sqrt(0.001004), places=12)

    def test_linear_stack_is_reported_alongside_the_root_sum_square(self):
        result = plan_process_variable_recording(READY_CASE)
        self.assertAlmostEqual(result["combined_swing_linear"], 0.042, places=12)

    def test_an_under_recorded_variable_drags_the_plan_to_a_gap(self):
        case = {
            "performance_tolerance": TOLERANCE,
            "variables": [
                REFLOW,
                _variable(CURE_DWELL, recording_method="not-recorded"),
                HUMIDITY,
            ],
        }
        result = plan_process_variable_recording(case)
        self.assertEqual(result["verdict"], RECORDING_GAP)
        self.assertAlmostEqual(result["unlogged_swing"], 0.01, places=12)

    def test_unlogged_share_is_reported_against_the_whole_swing(self):
        case = {
            "performance_tolerance": TOLERANCE,
            "variables": [
                REFLOW,
                _variable(CURE_DWELL, recording_method="not-recorded"),
                HUMIDITY,
            ],
        }
        result = plan_process_variable_recording(case)
        self.assertAlmostEqual(
            result["unlogged_share_of_swing"], 0.01 / math.sqrt(0.001004), places=9
        )

    def test_a_late_identification_outranks_a_recording_gap(self):
        case = {
            "performance_tolerance": TOLERANCE,
            "variables": [
                _variable(REFLOW, identified_before_production=False),
                _variable(CURE_DWELL, recording_method="not-recorded"),
            ],
        }
        result = plan_process_variable_recording(case)
        self.assertEqual(result["verdict"], IDENTIFICATION_LATE)

    def test_tolerance_consumed_reports_the_whole_variable_set(self):
        result = plan_process_variable_recording(READY_CASE)
        self.assertAlmostEqual(
            result["tolerance_consumed"], math.sqrt(0.001004) / TOLERANCE, places=9
        )

    def test_every_plan_verdict_is_ranked(self):
        result = plan_process_variable_recording(READY_CASE)
        self.assertIn(result["verdict"], VERDICT_RANK)

    def test_duplicate_variable_rejected(self):
        case = {
            "performance_tolerance": TOLERANCE,
            "variables": [REFLOW, copy.deepcopy(REFLOW)],
        }
        with self.assertRaises(ValueError):
            plan_process_variable_recording(case)

    def test_empty_variable_list_rejected(self):
        with self.assertRaises(ValueError):
            plan_process_variable_recording(
                {"performance_tolerance": TOLERANCE, "variables": []}
            )

    def test_missing_performance_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            plan_process_variable_recording({"variables": [REFLOW]})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            plan_process_variable_recording("solder-reflow-peak-temperature")


if __name__ == "__main__":
    unittest.main()
