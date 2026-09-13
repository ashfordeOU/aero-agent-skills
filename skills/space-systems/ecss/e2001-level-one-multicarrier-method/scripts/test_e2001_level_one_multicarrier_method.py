#!/usr/bin/env python3
"""Contract test for the level-one multicarrier multipactor method.

Offline, deterministic, stdlib unittest.
Run: python3 test_e2001_level_one_multicarrier_method.py
"""

import math
import unittest

import e2001_level_one_multicarrier_method_logic as logic

GHZ = 1.0e9


def carriers(*pairs):
    return [{"frequency_hz": f, "power_w": p} for f, p in pairs]


TWO_EQUAL = carriers((10.0 * GHZ, 50.0), (10.0 * GHZ + 1.0e6, 50.0))


class TestCarrierSet(unittest.TestCase):
    def test_set_is_sorted_by_frequency(self):
        normalized = logic.validate_carrier_set(
            carriers((12.0 * GHZ, 10.0), (11.0 * GHZ, 20.0))
        )
        self.assertAlmostEqual(normalized[0][0], 11.0 * GHZ, places=3)
        self.assertAlmostEqual(normalized[1][1], 10.0, places=9)

    def test_single_carrier_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set(carriers((10.0 * GHZ, 50.0)))

    def test_duplicate_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set(
                carriers((10.0 * GHZ, 50.0), (10.0 * GHZ, 20.0))
            )

    def test_non_positive_carrier_power_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set(
                carriers((10.0 * GHZ, 50.0), (11.0 * GHZ, 0.0))
            )

    def test_non_mapping_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([{"frequency_hz": 1.0e9, "power_w": 1.0}, 7])

    def test_missing_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([{"power_w": 1.0}, {"power_w": 2.0}])

    def test_total_average_power_is_the_sum(self):
        self.assertAlmostEqual(logic.total_average_power_w(TWO_EQUAL), 100.0, places=9)


class TestCarrierVoltages(unittest.TestCase):
    def test_matched_carrier_voltage(self):
        amplitudes = logic.carrier_peak_voltages(TWO_EQUAL)
        self.assertAlmostEqual(amplitudes[0], math.sqrt(2.0 * 50.0 * 50.0), places=9)
        self.assertEqual(len(amplitudes), 2)

    def test_standing_wave_and_concentration_scale_every_carrier(self):
        amplitudes = logic.carrier_peak_voltages(
            TWO_EQUAL, vswr=2.0, field_concentration=1.5
        )
        expected = math.sqrt(2.0 * 50.0 * 50.0) * (1.0 + 1.0 / 3.0) * 1.5
        self.assertAlmostEqual(amplitudes[0], expected, places=9)

    def test_standing_wave_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.carrier_peak_voltages(TWO_EQUAL, vswr=0.5)

    def test_peak_envelope_is_the_sum_of_crests(self):
        self.assertAlmostEqual(
            logic.peak_envelope_voltage([70.0, 30.0, 12.5]), 112.5, places=9
        )

    def test_empty_amplitude_set_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.peak_envelope_voltage([])

    def test_negative_amplitude_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.peak_envelope_voltage([70.0, -30.0])

    def test_equivalent_single_carrier_power_round_trips(self):
        amplitudes = logic.carrier_peak_voltages(TWO_EQUAL)
        envelope = logic.peak_envelope_voltage(amplitudes)
        power = logic.equivalent_single_carrier_power_w(envelope)
        # Two 50 W carriers crest together like one carrier of four times the
        # single-carrier power, not twice it.
        self.assertAlmostEqual(power, 200.0, places=6)

    def test_equivalent_power_rejects_a_zero_envelope(self):
        with self.assertRaises(ValueError):
            logic.equivalent_single_carrier_power_w(0.0)


class TestEnvelopePeriod(unittest.TestCase):
    def test_period_is_the_reciprocal_of_the_spacing_divisor(self):
        frequencies = [10.0 * GHZ, 10.0 * GHZ + 2.0e6, 10.0 * GHZ + 5.0e6]
        self.assertAlmostEqual(
            logic.envelope_repetition_period_s(frequencies), 1.0e-6, places=15
        )

    def test_uniform_spacing_gives_the_spacing_reciprocal(self):
        frequencies = [4.0 * GHZ, 4.0 * GHZ + 4.0e6, 4.0 * GHZ + 8.0e6]
        self.assertAlmostEqual(
            logic.envelope_repetition_period_s(frequencies), 2.5e-7, places=15
        )

    def test_identical_frequencies_have_no_envelope(self):
        with self.assertRaises(ValueError):
            logic.envelope_repetition_period_s([1.0 * GHZ, 1.0 * GHZ])

    def test_off_grid_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.envelope_repetition_period_s([1.0 * GHZ, 1.0 * GHZ + 1.5])

    def test_one_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.envelope_repetition_period_s([1.0 * GHZ])


class TestEnvelopeShape(unittest.TestCase):
    def setUp(self):
        self.amplitudes = [100.0, 100.0]
        self.frequencies = [10.0 * GHZ, 10.0 * GHZ + 1.0e6]
        self.spacing = 1.0e6

    def test_crest_is_the_sum_of_amplitudes(self):
        self.assertAlmostEqual(
            logic.envelope_voltage_at(self.amplitudes, self.frequencies, 0.0),
            200.0,
            places=9,
        )

    def test_quarter_period_is_the_quadrature_sum(self):
        t_s = 0.25 / self.spacing
        self.assertAlmostEqual(
            logic.envelope_voltage_at(self.amplitudes, self.frequencies, t_s),
            100.0 * math.sqrt(2.0),
            places=6,
        )

    def test_half_period_cancels_two_equal_carriers(self):
        t_s = 0.5 / self.spacing
        self.assertAlmostEqual(
            logic.envelope_voltage_at(self.amplitudes, self.frequencies, t_s),
            0.0,
            places=6,
        )

    def test_envelope_is_even_about_the_crest(self):
        t_s = 0.13 / self.spacing
        self.assertAlmostEqual(
            logic.envelope_voltage_at(self.amplitudes, self.frequencies, t_s),
            logic.envelope_voltage_at(self.amplitudes, self.frequencies, -t_s),
            places=9,
        )

    def test_length_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.envelope_voltage_at([100.0], self.frequencies, 0.0)


class TestDwellAboveThreshold(unittest.TestCase):
    def setUp(self):
        self.amplitudes = [100.0, 100.0]
        self.spacing = 1.0e6
        self.frequencies = [10.0 * GHZ, 10.0 * GHZ + self.spacing]

    def test_dwell_matches_the_closed_form_for_two_equal_carriers(self):
        threshold = 150.0
        expected = 2.0 * math.acos(threshold / 200.0) / (math.pi * self.spacing)
        dwell = logic.longest_dwell_above_threshold_s(
            self.amplitudes, self.frequencies, threshold
        )
        self.assertAlmostEqual(dwell, expected, delta=expected * 1e-9)

    def test_lower_threshold_lengthens_the_dwell(self):
        low = logic.longest_dwell_above_threshold_s(
            self.amplitudes, self.frequencies, 60.0
        )
        high = logic.longest_dwell_above_threshold_s(
            self.amplitudes, self.frequencies, 180.0
        )
        self.assertGreater(low, high)

    def test_wider_spacing_shortens_the_dwell(self):
        wide = logic.longest_dwell_above_threshold_s(
            self.amplitudes, [10.0 * GHZ, 10.0 * GHZ + 1.0e8], 150.0
        )
        narrow = logic.longest_dwell_above_threshold_s(
            self.amplitudes, self.frequencies, 150.0
        )
        self.assertAlmostEqual(wide * 100.0, narrow, delta=narrow * 1e-6)

    def test_crest_under_the_threshold_dwells_zero(self):
        self.assertAlmostEqual(
            logic.longest_dwell_above_threshold_s(
                self.amplitudes, self.frequencies, 250.0
            ),
            0.0,
            places=15,
        )

    def test_envelope_never_dropping_below_dwells_the_whole_period(self):
        dwell = logic.longest_dwell_above_threshold_s(
            [100.0, 20.0], self.frequencies, 50.0
        )
        self.assertAlmostEqual(dwell, 1.0 / self.spacing, places=15)

    def test_non_positive_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.longest_dwell_above_threshold_s(
                self.amplitudes, self.frequencies, 0.0
            )


class TestBuildUpCriterion(unittest.TestCase):
    def test_gap_crossing_is_half_a_carrier_period(self):
        self.assertAlmostEqual(logic.gap_crossing_time_s(10.0 * GHZ), 5.0e-11, places=18)

    def test_required_dwell_uses_the_fastest_carrier(self):
        frequencies = [4.0 * GHZ, 12.0 * GHZ]
        self.assertAlmostEqual(
            logic.required_dwell_time_s(frequencies, 20),
            20.0 / (2.0 * 12.0 * GHZ),
            places=18,
        )

    def test_crossing_count_scales_the_required_dwell(self):
        frequencies = [10.0 * GHZ, 11.0 * GHZ]
        self.assertAlmostEqual(
            logic.required_dwell_time_s(frequencies, 40),
            2.0 * logic.required_dwell_time_s(frequencies, 20),
            places=18,
        )

    def test_zero_crossings_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_dwell_time_s([10.0 * GHZ], 0)

    def test_fractional_crossings_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_dwell_time_s([10.0 * GHZ], 20.5)

    def test_empty_frequency_set_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_dwell_time_s([], 20)


class TestMarginRoutes(unittest.TestCase):
    def test_factor_of_two_is_six_decibels(self):
        self.assertAlmostEqual(
            logic.margin_db(300.0, 150.0), 20.0 * math.log10(2.0), places=12
        )

    def test_zero_applied_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.margin_db(300.0, 0.0)

    def test_routes_owe_different_margins(self):
        self.assertAlmostEqual(logic.required_margin_db("analysis-only"), 6.0, places=12)
        self.assertAlmostEqual(
            logic.required_margin_db("Test-Supported"), 3.0, places=12
        )

    def test_unknown_route_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_margin_db("heritage")


class TestAssessment(unittest.TestCase):
    def test_wide_margin_passes_on_the_peak_envelope(self):
        record = logic.assess_multicarrier(TWO_EQUAL, 500.0, region_id="filter-gap")
        self.assertEqual(record["verdict"], logic.VERDICT_PEAK_ENVELOPE)
        self.assertEqual(record["carrier_count"], 2)
        self.assertEqual(record["actions"], [])
        self.assertAlmostEqual(record["total_average_power_w"], 100.0, places=9)
        self.assertAlmostEqual(
            record["peak_envelope_voltage_v"],
            2.0 * math.sqrt(2.0 * 50.0 * 50.0),
            places=9,
        )
        self.assertAlmostEqual(record["dwell_above_threshold_s"], 0.0, places=15)

    def test_margin_exactly_at_the_owed_value_passes_on_the_peak_envelope(self):
        amplitudes = logic.carrier_peak_voltages(TWO_EQUAL)
        envelope = logic.peak_envelope_voltage(amplitudes)
        boundary = envelope * 10.0 ** (6.0 / 20.0)
        record = logic.assess_multicarrier(TWO_EQUAL, boundary)
        # The decibel round trip can land a few units in the last place under
        # 6 dB; a compliant carrier plan must not be failed by it.
        self.assertAlmostEqual(record["achieved_margin_db"], 6.0, places=9)
        self.assertEqual(record["verdict"], logic.VERDICT_PEAK_ENVELOPE)

    def test_short_margin_with_a_brief_crest_passes_on_the_build_up_criterion(self):
        wide = carriers((10.0 * GHZ, 50.0), (12.0 * GHZ, 50.0))
        record = logic.assess_multicarrier(wide, 200.0)
        self.assertEqual(record["verdict"], logic.VERDICT_CROSSING_RULE)
        self.assertLess(record["achieved_margin_db"], 6.0)
        self.assertLess(
            record["dwell_above_threshold_s"], record["required_dwell_s"]
        )
        self.assertEqual(len(record["actions"]), 1)

    def test_short_margin_with_a_long_crest_predicts_a_discharge(self):
        close = carriers((10.0 * GHZ, 50.0), (10.0 * GHZ + 2.0e6, 50.0))
        record = logic.assess_multicarrier(close, 200.0)
        self.assertEqual(record["verdict"], logic.VERDICT_PREDICTED)
        self.assertGreater(
            record["dwell_above_threshold_s"], record["required_dwell_s"]
        )
        self.assertEqual(len(record["actions"]), 1)

    def test_derated_boundary_carries_the_route_margin(self):
        record = logic.assess_multicarrier(TWO_EQUAL, 200.0)
        self.assertAlmostEqual(
            record["derated_threshold_v"], 200.0 / (10.0 ** 0.3), places=9
        )

    def test_test_supported_route_derates_less(self):
        analysis = logic.assess_multicarrier(TWO_EQUAL, 200.0)
        tested = logic.assess_multicarrier(TWO_EQUAL, 200.0, route="test-supported")
        self.assertGreater(
            tested["derated_threshold_v"], analysis["derated_threshold_v"]
        )

    def test_more_carriers_raise_the_envelope_and_cut_the_margin(self):
        two = logic.assess_multicarrier(TWO_EQUAL, 500.0)
        four = logic.assess_multicarrier(
            carriers(
                (10.0 * GHZ, 50.0),
                (10.0 * GHZ + 1.0e6, 50.0),
                (10.0 * GHZ + 2.0e6, 50.0),
                (10.0 * GHZ + 3.0e6, 50.0),
            ),
            500.0,
        )
        self.assertGreater(
            four["peak_envelope_voltage_v"], two["peak_envelope_voltage_v"]
        )
        self.assertLess(four["achieved_margin_db"], two["achieved_margin_db"])

    def test_non_positive_boundary_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_multicarrier(TWO_EQUAL, 0.0)

    def test_unknown_route_stops_the_assessment(self):
        with self.assertRaises(ValueError):
            logic.assess_multicarrier(TWO_EQUAL, 500.0, route="engineering-judgement")

    def test_single_carrier_stops_the_assessment(self):
        with self.assertRaises(ValueError):
            logic.assess_multicarrier(carriers((10.0 * GHZ, 50.0)), 500.0)


if __name__ == "__main__":
    unittest.main()
