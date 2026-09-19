#!/usr/bin/env python3
"""Gate 3 contract test for q2007-process-design.

stdlib unittest, offline, deterministic. Run:
    python3 test_q2007_process_design.py
"""

import unittest

from q2007_process_design_logic import (
    VERDICT_APPROVED,
    VERDICT_REWORK,
    design_test_process,
    guard_banded_limits,
    instrument_covers_band,
    ramp_findings,
    ramp_rates,
    sequence_duration_s,
    test_accuracy_ratio,
    validate_load_steps,
    validate_parameter,
)


def good_parameter(**over):
    record = {
        "name": "axial-load-kn",
        "nominal": 100.0,
        "tolerance": 4.0,
        "uncertainty": 0.5,
        "instrument_range": (0.0, 150.0),
    }
    record.update(over)
    return record


def good_steps():
    return [
        {"level": 25.0, "dwell_s": 60.0, "transition_s": 25.0},
        {"level": 50.0, "dwell_s": 60.0, "transition_s": 25.0},
        {"level": 100.0, "dwell_s": 120.0, "transition_s": 50.0},
    ]


def good_design(**over):
    record = {
        "parameters": [good_parameter()],
        "load_steps": good_steps(),
        "max_ramp_rate": 2.0,
    }
    record.update(over)
    return record


class TestParameterValidation(unittest.TestCase):
    def test_good_parameter_normalizes(self):
        param = validate_parameter(good_parameter())
        self.assertEqual(param["name"], "axial-load-kn")
        self.assertAlmostEqual(param["tolerance"], 4.0, places=9)

    def test_blank_name_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(good_parameter(name="  "))

    def test_zero_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(good_parameter(tolerance=0.0))

    def test_negative_uncertainty_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(good_parameter(uncertainty=-0.1))

    def test_inverted_instrument_range_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(good_parameter(instrument_range=(150.0, 0.0)))

    def test_non_pair_instrument_range_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(good_parameter(instrument_range=(0.0, 50.0, 150.0)))


class TestAccuracyRatio(unittest.TestCase):
    def test_ratio_is_band_over_uncertainty(self):
        self.assertAlmostEqual(test_accuracy_ratio(4.0, 0.5), 8.0, places=9)

    def test_zero_uncertainty_has_no_ratio(self):
        with self.assertRaises(ValueError):
            test_accuracy_ratio(4.0, 0.0)

    def test_zero_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            test_accuracy_ratio(0.0, 0.5)


class TestGuardBand(unittest.TestCase):
    def test_limits_pull_inward_by_the_uncertainty(self):
        limits = guard_banded_limits(100.0, 4.0, 0.5)
        self.assertAlmostEqual(limits["accept_upper"], 103.5, places=9)
        self.assertAlmostEqual(limits["accept_lower"], 96.5, places=9)

    def test_specified_limits_are_left_where_the_customer_put_them(self):
        limits = guard_banded_limits(100.0, 4.0, 0.5)
        self.assertAlmostEqual(limits["specified_upper"], 104.0, places=9)
        self.assertAlmostEqual(limits["specified_lower"], 96.0, places=9)

    def test_zero_uncertainty_leaves_the_band_untouched(self):
        limits = guard_banded_limits(100.0, 4.0, 0.0)
        self.assertAlmostEqual(limits["accept_upper"], limits["specified_upper"], places=9)

    def test_uncertainty_equal_to_the_band_is_refused(self):
        with self.assertRaises(ValueError):
            guard_banded_limits(100.0, 4.0, 4.0)

    def test_uncertainty_wider_than_the_band_is_refused(self):
        with self.assertRaises(ValueError):
            guard_banded_limits(100.0, 4.0, 5.0)


class TestInstrumentCoverage(unittest.TestCase):
    def test_range_bracketing_the_band_covers_it(self):
        self.assertTrue(instrument_covers_band(good_parameter()))

    def test_range_ending_exactly_on_the_band_edge_covers_it(self):
        self.assertTrue(instrument_covers_band(good_parameter(instrument_range=(96.0, 104.0))))

    def test_range_clipping_the_top_of_the_band_does_not_cover_it(self):
        self.assertFalse(
            instrument_covers_band(good_parameter(instrument_range=(0.0, 103.0)))
        )

    def test_range_sized_on_the_nominal_alone_does_not_cover_the_band(self):
        self.assertFalse(
            instrument_covers_band(good_parameter(instrument_range=(0.0, 100.0)))
        )


class TestLoadSteps(unittest.TestCase):
    def test_good_sequence_normalizes_in_order(self):
        steps = validate_load_steps(good_steps())
        self.assertEqual([s["order"] for s in steps], [1, 2, 3])

    def test_single_step_is_not_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_load_steps(good_steps()[:1])

    def test_repeated_level_is_rejected(self):
        steps = good_steps()
        steps[2]["level"] = steps[1]["level"]
        with self.assertRaises(ValueError):
            validate_load_steps(steps)

    def test_descending_level_is_rejected(self):
        steps = good_steps()
        steps[2]["level"] = 10.0
        with self.assertRaises(ValueError):
            validate_load_steps(steps)

    def test_zero_dwell_is_rejected(self):
        steps = good_steps()
        steps[0]["dwell_s"] = 0.0
        with self.assertRaises(ValueError):
            validate_load_steps(steps)

    def test_zero_transition_is_rejected(self):
        steps = good_steps()
        steps[0]["transition_s"] = 0.0
        with self.assertRaises(ValueError):
            validate_load_steps(steps)

    def test_sequence_duration_sums_dwell_and_transition(self):
        self.assertAlmostEqual(sequence_duration_s(good_steps()), 340.0, places=9)


class TestRamps(unittest.TestCase):
    def test_ramp_rate_of_the_first_step_runs_from_the_start_level(self):
        self.assertAlmostEqual(ramp_rates(good_steps())[0], 1.0, places=9)

    def test_ramp_rate_of_a_later_step_runs_from_the_previous_level(self):
        self.assertAlmostEqual(ramp_rates(good_steps())[2], 1.0, places=9)

    def test_a_ramp_exactly_on_the_facility_limit_is_not_a_finding(self):
        rates = ramp_rates(good_steps())
        self.assertAlmostEqual(max(rates), 1.0, places=9)
        self.assertEqual(ramp_findings(good_steps(), 1.0), [])

    def test_a_ramp_over_the_facility_limit_is_a_finding(self):
        steps = good_steps()
        steps[2]["transition_s"] = 5.0
        self.assertEqual(len(ramp_findings(steps, 1.0)), 1)

    def test_zero_ramp_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            ramp_findings(good_steps(), 0.0)


class TestFullDesign(unittest.TestCase):
    def test_clean_design_is_approved(self):
        report = design_test_process(good_design())
        self.assertEqual(report["verdict"], VERDICT_APPROVED)
        self.assertEqual(report["findings"], [])

    def test_report_carries_the_guard_banded_limits(self):
        report = design_test_process(good_design())
        self.assertAlmostEqual(
            report["parameters"][0]["limits"]["accept_upper"], 103.5, places=9
        )

    def test_accuracy_ratio_exactly_on_the_floor_is_not_a_finding(self):
        design = good_design(parameters=[good_parameter(uncertainty=1.0)])
        report = design_test_process(design)
        self.assertAlmostEqual(report["parameters"][0]["accuracy_ratio"], 4.0, places=9)
        self.assertEqual(report["findings"], [])

    def test_accuracy_ratio_under_the_floor_is_a_finding(self):
        design = good_design(parameters=[good_parameter(uncertainty=2.0)])
        report = design_test_process(design)
        self.assertEqual(report["verdict"], VERDICT_REWORK)
        self.assertEqual(len(report["findings"]), 1)

    def test_a_clipping_instrument_is_a_finding(self):
        design = good_design(
            parameters=[good_parameter(instrument_range=(0.0, 102.0))]
        )
        report = design_test_process(design)
        self.assertEqual(report["verdict"], VERDICT_REWORK)
        self.assertEqual(len(report["findings"]), 1)

    def test_a_zero_uncertainty_parameter_reports_no_ratio(self):
        design = good_design(parameters=[good_parameter(uncertainty=0.0)])
        report = design_test_process(design)
        self.assertIsNone(report["parameters"][0]["accuracy_ratio"])
        self.assertEqual(report["findings"], [])

    def test_missing_ramp_limit_is_rejected(self):
        design = good_design()
        del design["max_ramp_rate"]
        with self.assertRaises(ValueError):
            design_test_process(design)

    def test_empty_parameter_list_is_rejected(self):
        with self.assertRaises(ValueError):
            design_test_process(good_design(parameters=[]))

    def test_design_propagates_a_load_step_error(self):
        steps = good_steps()
        steps[1]["dwell_s"] = -1.0
        with self.assertRaises(ValueError):
            design_test_process(good_design(load_steps=steps))


if __name__ == "__main__":
    unittest.main()
