#!/usr/bin/env python3
"""Contract test for the multicarrier multipactor analysis-level leaf."""

import math
import unittest

import e2001_multicarrier_analysis_levels_logic as m


def carrier(freq_hz, power_w):
    return {"frequency_hz": freq_hz, "power_w": power_w}


# Two equal carriers one megahertz apart: envelope period 1 us, peak 100 W.
CLOSE_PAIR = [carrier(11.000e9, 25.0), carrier(11.001e9, 25.0)]
# Two equal carriers half a gigahertz apart: envelope period 2 ns, peak 100 W.
WIDE_PAIR = [carrier(11.0e9, 25.0), carrier(11.5e9, 25.0)]
# Irregular plan: offsets of 1 MHz and 3 MHz beat at 1 MHz.
IRREGULAR_TRIPLE = [
    carrier(11.000e9, 10.0),
    carrier(11.001e9, 10.0),
    carrier(11.003e9, 10.0),
]


class TestCarrierPlanValidation(unittest.TestCase):
    def test_mappings_are_accepted_and_sorted(self):
        plan = m.validate_carriers([carrier(11.5e9, 4.0), carrier(11.0e9, 9.0)])
        self.assertEqual(plan[0][0], 11.0e9)
        self.assertAlmostEqual(plan[0][1], 9.0)

    def test_normalized_pairs_are_accepted(self):
        plan = m.validate_carriers(CLOSE_PAIR)
        self.assertEqual(m.validate_carriers(plan), plan)

    def test_single_carrier_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carriers([carrier(11.0e9, 25.0)])

    def test_non_list_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carriers(carrier(11.0e9, 25.0))

    def test_bad_record_type_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carriers([carrier(11.0e9, 25.0), "11.001 GHz"])

    def test_missing_frequency_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carriers([carrier(11.0e9, 25.0), {"power_w": 25.0}])

    def test_missing_power_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carriers([carrier(11.0e9, 25.0), {"frequency_hz": 11.001e9}])

    def test_non_positive_frequency_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carriers([carrier(0.0, 25.0), carrier(11.0e9, 25.0)])

    def test_non_positive_power_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carriers([carrier(11.0e9, -1.0), carrier(11.001e9, 25.0)])

    def test_non_finite_power_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carriers([carrier(11.0e9, float("inf")), carrier(11.001e9, 1.0)])

    def test_duplicate_frequency_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carriers([carrier(11.0e9, 25.0), carrier(11.0e9, 25.0)])

    def test_boolean_power_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carriers([carrier(11.0e9, True), carrier(11.001e9, 25.0)])


class TestPowerAggregates(unittest.TestCase):
    def test_peak_envelope_of_equal_pair(self):
        self.assertAlmostEqual(m.peak_envelope_power_w(CLOSE_PAIR), 100.0)

    def test_average_power_of_equal_pair(self):
        self.assertAlmostEqual(m.average_power_w(CLOSE_PAIR), 50.0)

    def test_peak_is_twice_the_average_for_a_pair(self):
        self.assertAlmostEqual(
            m.peak_envelope_power_w(CLOSE_PAIR) / m.average_power_w(CLOSE_PAIR), 2.0
        )

    def test_peak_envelope_of_triple(self):
        self.assertAlmostEqual(m.peak_envelope_power_w(IRREGULAR_TRIPLE), 90.0)

    def test_peak_envelope_of_unequal_pair(self):
        self.assertAlmostEqual(
            m.peak_envelope_power_w([carrier(11.0e9, 100.0), carrier(11.001e9, 1.0)]),
            121.0,
        )


class TestBeatAndPeriod(unittest.TestCase):
    def test_even_spacing_beat_is_the_spacing(self):
        self.assertAlmostEqual(m.fundamental_beat_hz(CLOSE_PAIR), 1.0e6)

    def test_irregular_spacing_beat_is_the_common_divisor(self):
        self.assertAlmostEqual(m.fundamental_beat_hz(IRREGULAR_TRIPLE), 1.0e6)

    def test_coprime_offsets_beat_at_their_divisor(self):
        plan = [carrier(11.0e9, 5.0), carrier(11.0e9 + 2e6, 5.0), carrier(11.0e9 + 3e6, 5.0)]
        self.assertAlmostEqual(m.fundamental_beat_hz(plan), 1.0e6)

    def test_wide_pair_beat(self):
        self.assertAlmostEqual(m.fundamental_beat_hz(WIDE_PAIR), 0.5e9)

    def test_sub_hertz_offset_rejected(self):
        with self.assertRaises(ValueError):
            m.fundamental_beat_hz([carrier(11.0e9, 5.0), carrier(11.0e9 + 0.4, 5.0)])

    def test_envelope_period_is_the_beat_reciprocal(self):
        self.assertAlmostEqual(m.envelope_period_s(CLOSE_PAIR), 1.0e-6)

    def test_wide_pair_period_is_shorter(self):
        self.assertLess(m.envelope_period_s(WIDE_PAIR), m.envelope_period_s(CLOSE_PAIR))


class TestGapCrossingTiming(unittest.TestCase):
    def test_first_order_crossing_is_half_an_rf_period(self):
        self.assertAlmostEqual(m.gap_crossing_time_s(10.0e9), 5.0e-11)

    def test_third_order_crossing_is_three_times_longer(self):
        self.assertAlmostEqual(
            m.gap_crossing_time_s(10.0e9, order=3), 3 * m.gap_crossing_time_s(10.0e9)
        )

    def test_even_order_rejected(self):
        with self.assertRaises(ValueError):
            m.gap_crossing_time_s(10.0e9, order=2)

    def test_zero_order_rejected(self):
        with self.assertRaises(ValueError):
            m.gap_crossing_time_s(10.0e9, order=0)

    def test_non_integer_order_rejected(self):
        with self.assertRaises(ValueError):
            m.gap_crossing_time_s(10.0e9, order=1.0)

    def test_non_positive_frequency_rejected(self):
        with self.assertRaises(ValueError):
            m.gap_crossing_time_s(0.0)

    def test_window_is_crossings_times_crossing_time(self):
        self.assertAlmostEqual(
            m.gap_crossing_window_s(10.0e9, crossings=20), 20 * 5.0e-11
        )

    def test_default_window_uses_twenty_crossings(self):
        self.assertEqual(m.DEFAULT_GAP_CROSSINGS, 20)
        self.assertAlmostEqual(
            m.gap_crossing_window_s(10.0e9),
            m.DEFAULT_GAP_CROSSINGS * m.gap_crossing_time_s(10.0e9),
        )

    def test_window_scales_with_crossings(self):
        self.assertAlmostEqual(
            m.gap_crossing_window_s(10.0e9, crossings=40)
            / m.gap_crossing_window_s(10.0e9, crossings=20),
            2.0,
        )

    def test_zero_crossings_rejected(self):
        with self.assertRaises(ValueError):
            m.gap_crossing_window_s(10.0e9, crossings=0)

    def test_non_integer_crossings_rejected(self):
        with self.assertRaises(ValueError):
            m.gap_crossing_window_s(10.0e9, crossings=20.5)


class TestMarginedThreshold(unittest.TestCase):
    def test_six_decibel_margin_derates_the_threshold(self):
        self.assertAlmostEqual(m.margined_threshold_w(400.0, 6.0), 400.0 / 10 ** 0.6)

    def test_zero_margin_is_identity(self):
        self.assertAlmostEqual(m.margined_threshold_w(400.0, 0.0), 400.0)

    def test_larger_margin_lowers_the_allowance(self):
        self.assertLess(
            m.margined_threshold_w(400.0, 8.0), m.margined_threshold_w(400.0, 6.0)
        )

    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            m.margined_threshold_w(400.0, -1.0)

    def test_non_finite_margin_rejected(self):
        with self.assertRaises(ValueError):
            m.margined_threshold_w(400.0, float("nan"))

    def test_non_numeric_margin_rejected(self):
        with self.assertRaises(ValueError):
            m.margined_threshold_w(400.0, "6")

    def test_non_positive_threshold_rejected(self):
        with self.assertRaises(ValueError):
            m.margined_threshold_w(0.0, 6.0)


class TestEnvelopeSampling(unittest.TestCase):
    def test_sample_count_matches_request(self):
        self.assertEqual(len(m.envelope_power_samples(CLOSE_PAIR, samples=256)), 256)

    def test_first_sample_is_the_coherent_peak(self):
        samples = m.envelope_power_samples(CLOSE_PAIR, samples=256)
        self.assertAlmostEqual(samples[0], 100.0)

    def test_no_sample_exceeds_the_peak(self):
        peak = m.peak_envelope_power_w(IRREGULAR_TRIPLE)
        for value in m.envelope_power_samples(IRREGULAR_TRIPLE, samples=512):
            self.assertLessEqual(value, peak + 1e-9)

    def test_equal_pair_reaches_a_null(self):
        samples = m.envelope_power_samples(CLOSE_PAIR, samples=512)
        self.assertAlmostEqual(min(samples), 0.0, places=6)

    def test_too_few_samples_rejected(self):
        with self.assertRaises(ValueError):
            m.envelope_power_samples(CLOSE_PAIR, samples=4)

    def test_non_integer_samples_rejected(self):
        with self.assertRaises(ValueError):
            m.envelope_power_samples(CLOSE_PAIR, samples=256.0)

    def test_sampling_too_coarse_for_the_plan_rejected(self):
        with self.assertRaises(ValueError):
            m.envelope_power_samples(IRREGULAR_TRIPLE, samples=16)


class TestDwellAboveLevel(unittest.TestCase):
    def test_equal_pair_half_period_above_half_peak(self):
        dwell = m.longest_dwell_above_s(CLOSE_PAIR, 50.0)
        step = m.envelope_period_s(CLOSE_PAIR) / m.DEFAULT_ENVELOPE_SAMPLES
        self.assertAlmostEqual(dwell, 0.5e-6, delta=3 * step)

    def test_dwell_matches_the_closed_form_near_the_peak(self):
        level = 95.0
        expected = 2 * math.acos(math.sqrt(level / 100.0)) / (math.pi * 0.5e9)
        dwell = m.longest_dwell_above_s(WIDE_PAIR, level)
        step = m.envelope_period_s(WIDE_PAIR) / m.DEFAULT_ENVELOPE_SAMPLES
        self.assertAlmostEqual(dwell, expected, delta=3 * step)

    def test_level_above_the_peak_gives_no_dwell(self):
        self.assertAlmostEqual(m.longest_dwell_above_s(CLOSE_PAIR, 200.0), 0.0)

    def test_level_below_the_envelope_floor_gives_the_whole_period(self):
        plan = [carrier(11.0e9, 100.0), carrier(11.001e9, 1.0)]
        self.assertAlmostEqual(
            m.longest_dwell_above_s(plan, 50.0), m.envelope_period_s(plan)
        )

    def test_higher_level_shortens_the_dwell(self):
        self.assertLess(
            m.longest_dwell_above_s(CLOSE_PAIR, 90.0),
            m.longest_dwell_above_s(CLOSE_PAIR, 40.0),
        )

    def test_non_positive_level_rejected(self):
        with self.assertRaises(ValueError):
            m.longest_dwell_above_s(CLOSE_PAIR, 0.0)

    def test_dwell_never_exceeds_the_period(self):
        period = m.envelope_period_s(CLOSE_PAIR)
        self.assertLessEqual(m.longest_dwell_above_s(CLOSE_PAIR, 1e-6), period)


class TestLevelOneCheck(unittest.TestCase):
    def test_comfortable_case_is_within_allowance(self):
        check = m.level_one_check(CLOSE_PAIR, 1000.0, 6.0)
        self.assertTrue(check["within_allowance"])
        self.assertAlmostEqual(check["exceedance_w"], 0.0)

    def test_peak_envelope_is_reported(self):
        check = m.level_one_check(CLOSE_PAIR, 1000.0, 6.0)
        self.assertAlmostEqual(check["peak_envelope_power_w"], 100.0)

    def test_exceeding_case_reports_the_overshoot(self):
        check = m.level_one_check(CLOSE_PAIR, 200.0, 6.0)
        self.assertFalse(check["within_allowance"])
        self.assertGreater(check["exceedance_w"], 0.0)

    def test_exact_boundary_is_within_allowance(self):
        threshold = 100.0 * 10 ** 0.6
        check = m.level_one_check(CLOSE_PAIR, threshold, 6.0)
        self.assertTrue(check["within_allowance"])

    def test_margin_moves_the_allowance(self):
        loose = m.level_one_check(CLOSE_PAIR, 500.0, 3.0)
        tight = m.level_one_check(CLOSE_PAIR, 500.0, 9.0)
        self.assertLess(tight["allowed_power_w"], loose["allowed_power_w"])


class TestLevelSelection(unittest.TestCase):
    def test_worst_case_closure_selects_the_first_level(self):
        selection = m.select_analysis_level(CLOSE_PAIR, 1000.0, 6.0)
        self.assertEqual(selection["level"], m.LEVEL_ONE)
        self.assertIn("worst-case", selection["reason"])

    def test_worst_case_failure_selects_the_second_level(self):
        selection = m.select_analysis_level(CLOSE_PAIR, 200.0, 6.0)
        self.assertEqual(selection["level"], m.LEVEL_TWO)
        self.assertIn("time-resolved", selection["reason"])

    def test_selection_carries_the_first_level_numbers(self):
        selection = m.select_analysis_level(CLOSE_PAIR, 200.0, 6.0)
        self.assertIn("peak_envelope_power_w", selection["level_one"])

    def test_level_names_are_stable(self):
        self.assertEqual(m.LEVEL_ONE, "level-1")
        self.assertEqual(m.LEVEL_TWO, "level-2")

    def test_selection_rejects_a_single_carrier_plan(self):
        with self.assertRaises(ValueError):
            m.select_analysis_level([carrier(11.0e9, 25.0)], 1000.0, 6.0)


class TestLevelTwoCheck(unittest.TestCase):
    def test_short_excursion_passes(self):
        detail = m.level_two_check(WIDE_PAIR, 95.0 * 10 ** 0.6, 6.0)
        self.assertTrue(detail["within_allowance"])
        self.assertLess(detail["longest_dwell_s"], detail["gap_crossing_window_s"])

    def test_long_excursion_fails(self):
        detail = m.level_two_check(CLOSE_PAIR, 50.0 * 10 ** 0.6, 6.0)
        self.assertFalse(detail["within_allowance"])

    def test_window_is_taken_at_the_highest_carrier(self):
        detail = m.level_two_check(WIDE_PAIR, 95.0 * 10 ** 0.6, 6.0)
        self.assertAlmostEqual(detail["reference_frequency_hz"], 11.5e9)

    def test_envelope_period_is_reported(self):
        detail = m.level_two_check(WIDE_PAIR, 95.0 * 10 ** 0.6, 6.0)
        self.assertAlmostEqual(detail["envelope_period_s"], 2.0e-9)

    def test_more_credited_crossings_widen_the_window(self):
        few = m.level_two_check(CLOSE_PAIR, 50.0 * 10 ** 0.6, 6.0, crossings=20)
        many = m.level_two_check(CLOSE_PAIR, 50.0 * 10 ** 0.6, 6.0, crossings=40)
        self.assertAlmostEqual(
            many["gap_crossing_window_s"] / few["gap_crossing_window_s"], 2.0
        )

    def test_enough_credited_crossings_flip_the_verdict(self):
        detail = m.level_two_check(CLOSE_PAIR, 50.0 * 10 ** 0.6, 6.0, crossings=20000)
        self.assertTrue(detail["within_allowance"])

    def test_higher_resonance_order_widens_the_window(self):
        first = m.level_two_check(WIDE_PAIR, 95.0 * 10 ** 0.6, 6.0, order=1)
        third = m.level_two_check(WIDE_PAIR, 95.0 * 10 ** 0.6, 6.0, order=3)
        self.assertGreater(
            third["gap_crossing_window_s"], first["gap_crossing_window_s"]
        )

    def test_even_order_rejected(self):
        with self.assertRaises(ValueError):
            m.level_two_check(WIDE_PAIR, 95.0 * 10 ** 0.6, 6.0, order=4)

    def test_allowed_power_matches_the_margined_threshold(self):
        detail = m.level_two_check(WIDE_PAIR, 95.0 * 10 ** 0.6, 6.0)
        self.assertAlmostEqual(detail["allowed_power_w"], 95.0)


class TestCaseAssessment(unittest.TestCase):
    def case(self, **over):
        payload = {
            "id": "output-multiplexer",
            "carriers": WIDE_PAIR,
            "single_carrier_threshold_w": 95.0 * 10 ** 0.6,
            "margin_db": 6.0,
        }
        payload.update(over)
        return payload

    def test_first_level_case_closes_without_the_second(self):
        result = m.assess_multicarrier_case(
            self.case(single_carrier_threshold_w=1000.0)
        )
        self.assertEqual(result["level"], m.LEVEL_ONE)
        self.assertIsNone(result["level_two"])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_second_level_case_passes_on_dwell(self):
        result = m.assess_multicarrier_case(self.case())
        self.assertEqual(result["level"], m.LEVEL_TWO)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_second_level_case_can_fail(self):
        result = m.assess_multicarrier_case(
            self.case(carriers=CLOSE_PAIR, single_carrier_threshold_w=50.0 * 10 ** 0.6)
        )
        self.assertEqual(result["level"], m.LEVEL_TWO)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_credited_crossings_are_honoured(self):
        result = m.assess_multicarrier_case(
            self.case(
                carriers=CLOSE_PAIR,
                single_carrier_threshold_w=50.0 * 10 ** 0.6,
                gap_crossings=20000,
            )
        )
        self.assertTrue(result["compliant"])

    def test_identifier_is_stripped(self):
        result = m.assess_multicarrier_case(self.case(id="  input-filter "))
        self.assertEqual(result["id"], "input-filter")

    def test_missing_key_rejected(self):
        payload = self.case()
        del payload["margin_db"]
        with self.assertRaises(ValueError):
            m.assess_multicarrier_case(payload)

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            m.assess_multicarrier_case(self.case(id="   "))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            m.assess_multicarrier_case(["output-multiplexer"])

    def test_bad_margin_rejected(self):
        with self.assertRaises(ValueError):
            m.assess_multicarrier_case(self.case(margin_db=-3.0))

    def test_bad_threshold_rejected(self):
        with self.assertRaises(ValueError):
            m.assess_multicarrier_case(self.case(single_carrier_threshold_w=0.0))


class TestSummary(unittest.TestCase):
    def cases(self):
        return [
            {
                "id": "easy-chain",
                "carriers": WIDE_PAIR,
                "single_carrier_threshold_w": 1000.0,
                "margin_db": 6.0,
            },
            {
                "id": "tight-chain",
                "carriers": CLOSE_PAIR,
                "single_carrier_threshold_w": 50.0 * 10 ** 0.6,
                "margin_db": 6.0,
            },
        ]

    def test_summary_counts_cases(self):
        summary = m.summarize_cases(self.cases())
        self.assertEqual(summary["cases"], 2)

    def test_summary_splits_by_level(self):
        summary = m.summarize_cases(self.cases())
        self.assertEqual(summary["level_one_ids"], ["easy-chain"])
        self.assertEqual(summary["level_two_ids"], ["tight-chain"])

    def test_summary_lists_open_cases(self):
        summary = m.summarize_cases(self.cases())
        self.assertEqual(summary["open_ids"], ["tight-chain"])
        self.assertFalse(summary["all_compliant"])

    def test_summary_all_compliant(self):
        summary = m.summarize_cases(self.cases()[:1])
        self.assertTrue(summary["all_compliant"])
        self.assertEqual(summary["open_ids"], [])

    def test_duplicate_identifier_rejected(self):
        cases = self.cases()
        cases[1]["id"] = "easy-chain"
        with self.assertRaises(ValueError):
            m.summarize_cases(cases)

    def test_empty_input_rejected(self):
        with self.assertRaises(ValueError):
            m.summarize_cases([])

    def test_non_list_input_rejected(self):
        with self.assertRaises(ValueError):
            m.summarize_cases("easy-chain")

    def test_tolerances_are_representation_scale(self):
        self.assertLess(m.POWER_REL_TOLERANCE, 1e-9)
        self.assertLess(m.TIME_REL_TOLERANCE, 1e-9)

    def test_module_is_offline_and_deterministic(self):
        first = m.summarize_cases(self.cases())
        second = m.summarize_cases(self.cases())
        self.assertEqual(first["open_ids"], second["open_ids"])
        self.assertFalse(hasattr(m, "requests"))


if __name__ == "__main__":
    unittest.main()
