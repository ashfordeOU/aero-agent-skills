#!/usr/bin/env python3
"""Gate 3 contract tests for the clause 6.4.4 pulsed-substitution logic."""

import math
import unittest

import e2001_pulsed_test_application_logic as logic


BASE_CASE = {
    "frequency_hz": 12.0e9,
    "pulse_width_s": 9.0e-6,
    "prf_hz": 1.0e5,
    "continuous_wave_power_w": 120.0,
    "peak_power_w": 600.0,
    "observation_s": 10.0,
}


def assess(**overrides):
    kwargs = dict(BASE_CASE)
    kwargs.update(overrides)
    return logic.assess_pulsed_substitution(**kwargs)


class TestModeAndCompensationTokens(unittest.TestCase):
    def test_continuous_wave_mode_accepted(self):
        self.assertEqual(
            logic.validate_operational_mode("continuous-wave"), "continuous-wave"
        )

    def test_pulsed_mode_accepted_by_the_validator(self):
        self.assertEqual(logic.validate_operational_mode(" pulsed "), "pulsed")

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_operational_mode("burst")

    def test_non_string_mode_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_operational_mode(1)

    def test_known_compensations_accepted(self):
        for token in logic.THERMAL_COMPENSATIONS:
            self.assertEqual(logic.validate_thermal_compensation(token), token)

    def test_unknown_compensation_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_thermal_compensation("hope")

    def test_non_string_compensation_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_thermal_compensation(None)


class TestPulseProfile(unittest.TestCase):
    def test_repetition_period(self):
        self.assertAlmostEqual(logic.pulse_repetition_period_s(1.0e5), 1.0e-5)

    def test_duty_cycle(self):
        self.assertAlmostEqual(logic.duty_cycle(2.0e-6, 1.0e5), 0.2)

    def test_profile_fields(self):
        profile = logic.validate_pulse_profile(5.0e-6, 1.0e5)
        self.assertAlmostEqual(profile["duty_cycle"], 0.5)
        self.assertAlmostEqual(profile["period_s"], 1.0e-5)
        self.assertAlmostEqual(profile["pulse_width_s"], 5.0e-6)

    def test_pulse_longer_than_period_rejected(self):
        with self.assertRaises(ValueError):
            logic.duty_cycle(2.0e-5, 1.0e5)

    def test_pulse_equal_to_period_rejected(self):
        with self.assertRaises(ValueError):
            logic.duty_cycle(1.0e-5, 1.0e5)

    def test_zero_pulse_width_rejected(self):
        with self.assertRaises(ValueError):
            logic.duty_cycle(0.0, 1.0e5)

    def test_negative_pulse_width_rejected(self):
        with self.assertRaises(ValueError):
            logic.duty_cycle(-1.0e-6, 1.0e5)

    def test_zero_prf_rejected(self):
        with self.assertRaises(ValueError):
            logic.pulse_repetition_period_s(0.0)

    def test_non_finite_prf_rejected(self):
        with self.assertRaises(ValueError):
            logic.pulse_repetition_period_s(float("inf"))

    def test_boolean_pulse_width_rejected(self):
        with self.assertRaises(ValueError):
            logic.duty_cycle(True, 1.0e5)


class TestTransitAndGrowth(unittest.TestCase):
    def test_first_order_transit(self):
        self.assertAlmostEqual(logic.electron_transit_time_s(10.0e9), 5.0e-11)

    def test_third_order_transit(self):
        self.assertAlmostEqual(
            logic.electron_transit_time_s(10.0e9, resonant_order=3), 1.5e-10
        )

    def test_even_order_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(10.0e9, resonant_order=6)

    def test_zero_order_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(10.0e9, resonant_order=0)

    def test_float_order_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(10.0e9, resonant_order=1.0)

    def test_order_above_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(10.0e9, resonant_order=25)

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(0.0)

    def test_crossings_per_pulse(self):
        self.assertAlmostEqual(
            logic.gap_crossings_per_pulse(1.0e-9, 10.0e9), 20.0
        )

    def test_crossings_scale_with_pulse_width(self):
        short = logic.gap_crossings_per_pulse(1.0e-9, 10.0e9)
        long = logic.gap_crossings_per_pulse(4.0e-9, 10.0e9)
        self.assertAlmostEqual(long, 4.0 * short)

    def test_higher_order_gives_fewer_crossings(self):
        first = logic.gap_crossings_per_pulse(1.0e-9, 10.0e9, resonant_order=1)
        fifth = logic.gap_crossings_per_pulse(1.0e-9, 10.0e9, resonant_order=5)
        self.assertAlmostEqual(fifth, first / 5.0)

    def test_zero_pulse_width_rejected_for_crossings(self):
        with self.assertRaises(ValueError):
            logic.gap_crossings_per_pulse(0.0, 10.0e9)

    def test_rf_cycles_per_pulse(self):
        self.assertAlmostEqual(logic.rf_cycles_per_pulse(1.0e-9, 10.0e9), 10.0)

    def test_rf_cycles_rejects_bad_frequency(self):
        with self.assertRaises(ValueError):
            logic.rf_cycles_per_pulse(1.0e-9, -1.0)

    def test_rf_cycles_rejects_bad_width(self):
        with self.assertRaises(ValueError):
            logic.rf_cycles_per_pulse(-1.0e-9, 10.0e9)

    def test_minimum_pulse_width_holds_the_growth_transits(self):
        width = logic.minimum_pulse_width_s(12.0e9)
        self.assertAlmostEqual(
            logic.gap_crossings_per_pulse(width, 12.0e9), float(logic.MIN_GAP_CROSSINGS)
        )

    def test_minimum_pulse_width_scales_with_order(self):
        first = logic.minimum_pulse_width_s(12.0e9, resonant_order=1)
        third = logic.minimum_pulse_width_s(12.0e9, resonant_order=3)
        self.assertAlmostEqual(third, 3.0 * first)

    def test_minimum_pulse_width_rejects_non_positive_count(self):
        with self.assertRaises(ValueError):
            logic.minimum_pulse_width_s(12.0e9, min_crossings=0.0)


class TestWindowAccounting(unittest.TestCase):
    def test_whole_pulses_in_window(self):
        self.assertEqual(logic.pulses_in_window(1.0e3, 2.5), 2500)

    def test_partial_pulse_is_not_counted(self):
        self.assertEqual(logic.pulses_in_window(1.0e3, 2.5005), 2500)

    def test_exact_whole_window_is_not_short_counted(self):
        # 0.1 s at 3 kHz is exactly 300 pulses but evaluates a shade under.
        self.assertEqual(logic.pulses_in_window(3.0e3, 0.1), 300)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            logic.pulses_in_window(1.0e3, 0.0)

    def test_zero_prf_rejected_for_window(self):
        with self.assertRaises(ValueError):
            logic.pulses_in_window(0.0, 1.0)

    def test_accumulated_on_time(self):
        self.assertAlmostEqual(
            logic.accumulated_on_time_s(1.0e-6, 1.0e4, 1.0), 1.0e-2
        )

    def test_accumulated_on_time_rejects_over_unity_duty(self):
        with self.assertRaises(ValueError):
            logic.accumulated_on_time_s(1.0e-3, 1.0e4, 1.0)


class TestPowerRelations(unittest.TestCase):
    def test_pulsed_average_power(self):
        self.assertAlmostEqual(logic.pulsed_average_power_w(500.0, 0.2), 100.0)

    def test_pulsed_average_rejects_unity_duty(self):
        with self.assertRaises(ValueError):
            logic.pulsed_average_power_w(500.0, 1.0)

    def test_pulsed_average_rejects_zero_duty(self):
        with self.assertRaises(ValueError):
            logic.pulsed_average_power_w(500.0, 0.0)

    def test_pulsed_average_rejects_zero_peak(self):
        with self.assertRaises(ValueError):
            logic.pulsed_average_power_w(0.0, 0.5)

    def test_required_peak_with_six_db_margin(self):
        self.assertAlmostEqual(
            logic.required_peak_drive_w(100.0, 6.0), 100.0 * 10.0 ** 0.6
        )

    def test_required_peak_with_zero_margin(self):
        self.assertAlmostEqual(logic.required_peak_drive_w(137.0, 0.0), 137.0)

    def test_required_peak_rejects_negative_margin(self):
        with self.assertRaises(ValueError):
            logic.required_peak_drive_w(100.0, -1.0)

    def test_required_peak_rejects_zero_power(self):
        with self.assertRaises(ValueError):
            logic.required_peak_drive_w(0.0, 6.0)


class TestFullAssessment(unittest.TestCase):
    def setUp(self):
        self.report = assess(min_accumulated_on_time_s=1.0)

    def test_base_case_is_compliant(self):
        self.assertTrue(self.report["compliant"])

    def test_base_case_verdict(self):
        self.assertEqual(
            self.report["verdict"], "pulsed-drive-substitution-acceptable"
        )

    def test_duty_cycle_in_report(self):
        self.assertAlmostEqual(self.report["duty_cycle"], 0.9)

    def test_crossings_far_exceed_the_minimum(self):
        self.assertGreater(
            self.report["gap_crossings_per_pulse"], float(logic.MIN_GAP_CROSSINGS)
        )

    def test_shortest_admissible_pulse_in_report(self):
        self.assertAlmostEqual(
            self.report["shortest_admissible_pulse_s"],
            logic.minimum_pulse_width_s(12.0e9),
        )

    def test_accumulated_on_time_in_report(self):
        self.assertAlmostEqual(self.report["accumulated_on_time_s"], 9.0)

    def test_average_power_follows_duty(self):
        self.assertAlmostEqual(self.report["pulsed_average_power_w"], 540.0)

    def test_thermally_representative_at_high_duty(self):
        self.assertTrue(self.report["thermally_representative"])

    def test_short_pulse_is_flagged(self):
        report = assess(pulse_width_s=1.0e-11)
        codes = [item["code"] for item in report["findings"]]
        self.assertIn("pulse-too-short-for-avalanche-growth", codes)
        self.assertEqual(
            report["verdict"], "pulsed-drive-substitution-not-acceptable"
        )

    def test_exact_growth_boundary_is_not_flagged(self):
        # At 1 GHz and seventh order the shortest admissible pulse divides
        # back to 19.999999999999996 crossings; that is representation
        # error, not a physical shortfall.
        width = logic.minimum_pulse_width_s(1.0e9, resonant_order=7)
        self.assertLess(logic.gap_crossings_per_pulse(width, 1.0e9, 7), 20.0)
        report = assess(
            frequency_hz=1.0e9,
            resonant_order=7,
            pulse_width_s=width,
            prf_hz=1.0e5,
            thermal_compensation="separate-thermal-vacuum-run",
        )
        codes = [item["code"] for item in report["findings"]]
        self.assertNotIn("pulse-too-short-for-avalanche-growth", codes)

    def test_peak_below_margined_level_is_flagged(self):
        report = assess(peak_power_w=200.0)
        codes = [item["code"] for item in report["findings"]]
        self.assertIn("pulse-peak-below-required-drive-level", codes)

    def test_peak_exactly_at_the_margined_level_is_accepted(self):
        required = logic.required_peak_drive_w(120.0, 6.0)
        report = assess(peak_power_w=required)
        codes = [item["code"] for item in report["findings"]]
        self.assertNotIn("pulse-peak-below-required-drive-level", codes)

    def test_short_on_time_is_flagged(self):
        report = assess(min_accumulated_on_time_s=100.0)
        codes = [item["code"] for item in report["findings"]]
        self.assertIn("accumulated-on-time-below-detection-threshold", codes)

    def test_on_time_threshold_exactly_met_is_accepted(self):
        report = assess(min_accumulated_on_time_s=9.0)
        codes = [item["code"] for item in report["findings"]]
        self.assertNotIn("accumulated-on-time-below-detection-threshold", codes)

    def test_low_duty_without_compensation_is_flagged(self):
        report = assess(pulse_width_s=1.0e-6)
        codes = [item["code"] for item in report["findings"]]
        self.assertIn("continuous-wave-thermal-state-not-reproduced", codes)

    def test_low_duty_with_compensation_is_accepted(self):
        report = assess(
            pulse_width_s=1.0e-6, thermal_compensation="baseplate-preheat"
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(
            report["verdict"],
            "pulsed-drive-substitution-acceptable-with-compensation",
        )

    def test_low_duty_is_not_thermally_representative(self):
        report = assess(
            pulse_width_s=1.0e-6, thermal_compensation="baseplate-preheat"
        )
        self.assertFalse(report["thermally_representative"])

    def test_pulsed_equipment_is_out_of_scope(self):
        report = assess(operational_mode="pulsed")
        self.assertEqual(
            report["verdict"], "pulsed-drive-substitution-out-of-scope"
        )

    def test_several_findings_accumulate(self):
        report = assess(pulse_width_s=1.0e-11, peak_power_w=10.0)
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("pulse-too-short-for-avalanche-growth", codes)
        self.assertIn("pulse-peak-below-required-drive-level", codes)
        self.assertIn("continuous-wave-thermal-state-not-reproduced", codes)

    def test_custom_thermal_duty_threshold(self):
        report = assess(pulse_width_s=5.0e-6, min_thermal_duty=0.4)
        self.assertTrue(report["thermally_representative"])

    def test_thermal_duty_threshold_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess(min_thermal_duty=1.5)

    def test_thermal_duty_threshold_at_zero_rejected(self):
        with self.assertRaises(ValueError):
            assess(min_thermal_duty=0.0)

    def test_non_positive_on_time_threshold_rejected(self):
        with self.assertRaises(ValueError):
            assess(min_accumulated_on_time_s=0.0)

    def test_unknown_mode_rejected_by_assessment(self):
        with self.assertRaises(ValueError):
            assess(operational_mode="swept")

    def test_unknown_compensation_rejected_by_assessment(self):
        with self.assertRaises(ValueError):
            assess(thermal_compensation="wishful")

    def test_over_unity_duty_rejected_by_assessment(self):
        with self.assertRaises(ValueError):
            assess(pulse_width_s=2.0e-5)

    def test_negative_margin_rejected_by_assessment(self):
        with self.assertRaises(ValueError):
            assess(margin_db=-3.0)

    def test_bad_frequency_rejected_by_assessment(self):
        with self.assertRaises(ValueError):
            assess(frequency_hz=0.0)

    def test_bad_observation_window_rejected_by_assessment(self):
        with self.assertRaises(ValueError):
            assess(observation_s=-1.0)


class TestCategorizationAndSummary(unittest.TestCase):
    def test_categorize_rejects_non_report(self):
        with self.assertRaises(ValueError):
            logic.categorize_pulsed_substitution({"verdict": "x"})

    def test_summary_mentions_verdict(self):
        self.assertIn(
            "verdict: pulsed-drive-substitution-acceptable",
            logic.summarize_report(assess()),
        )

    def test_summary_lists_findings(self):
        report = assess(pulse_width_s=1.0e-11)
        self.assertIn(
            "finding: pulse-too-short-for-avalanche-growth",
            logic.summarize_report(report),
        )

    def test_summary_reports_compensation(self):
        report = assess(thermal_compensation="auxiliary-continuous-wave-soak")
        self.assertIn(
            "thermal compensation: auxiliary-continuous-wave-soak",
            logic.summarize_report(report),
        )

    def test_summary_rejects_non_report(self):
        with self.assertRaises(ValueError):
            logic.summarize_report({"findings": []})

    def test_growth_minimum_is_twenty(self):
        self.assertEqual(logic.MIN_GAP_CROSSINGS, 20)

    def test_default_thermal_duty_is_in_range(self):
        self.assertTrue(0.0 < logic.DEFAULT_MIN_THERMAL_DUTY <= 1.0)

    def test_operational_mode_tokens_are_a_closed_set(self):
        self.assertEqual(len(logic.OPERATIONAL_MODES), 2)


if __name__ == "__main__":
    unittest.main()
