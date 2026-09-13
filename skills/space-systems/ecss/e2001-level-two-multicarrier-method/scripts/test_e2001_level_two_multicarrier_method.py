#!/usr/bin/env python3
"""Contract test for the level-two multicarrier envelope sweep (offline)."""

import math
import unittest

from e2001_level_two_multicarrier_method_logic import (
    DEFAULT_SUSTAINING_CROSSINGS,
    assess_level_two_multicarrier,
    carrier_spacing_hz,
    envelope_power_ratio_for_pulse_width,
    envelope_voltage_ratio,
    gap_crossing_time_s,
    main_lobe_base_width_s,
    multipaction_margin_db,
    normalise_susceptibility_table,
    peak_envelope_power_w,
    sustaining_pulse_width_s,
    sweep_envelope_pulse_widths,
    worst_case_envelope_point,
)

FREQS = [11.70e9, 11.71e9, 11.72e9, 11.73e9]
POWERS = [20.0, 20.0, 20.0, 20.0]
CENTRE = sum(FREQS) / len(FREQS)


def _table(rows):
    return [
        {"pulse_width_s": w, "breakdown_power_w": p} for w, p in rows
    ]


class GapCrossingTimeTests(unittest.TestCase):
    def test_crossing_time_is_half_an_rf_period(self):
        self.assertAlmostEqual(gap_crossing_time_s(1.0e9), 5.0e-10, places=18)

    def test_crossing_time_scales_inversely_with_frequency(self):
        self.assertAlmostEqual(
            gap_crossing_time_s(2.0e9), gap_crossing_time_s(1.0e9) / 2.0, places=18
        )

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            gap_crossing_time_s(0.0)

    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            gap_crossing_time_s(-1.0e9)

    def test_non_numeric_frequency_rejected(self):
        with self.assertRaises(ValueError):
            gap_crossing_time_s("11.7 GHz")


class SustainingPulseWidthTests(unittest.TestCase):
    def test_default_crossings_is_twenty(self):
        self.assertEqual(DEFAULT_SUSTAINING_CROSSINGS, 20)

    def test_sustaining_width_is_crossings_times_transit(self):
        self.assertAlmostEqual(
            sustaining_pulse_width_s(1.0e9), 20 * 5.0e-10, places=18
        )

    def test_custom_crossing_count_applied(self):
        self.assertAlmostEqual(
            sustaining_pulse_width_s(1.0e9, crossings=10), 10 * 5.0e-10, places=18
        )

    def test_zero_crossings_rejected(self):
        with self.assertRaises(ValueError):
            sustaining_pulse_width_s(1.0e9, crossings=0)

    def test_fractional_crossings_rejected(self):
        with self.assertRaises(ValueError):
            sustaining_pulse_width_s(1.0e9, crossings=2.5)

    def test_boolean_crossings_rejected(self):
        with self.assertRaises(ValueError):
            sustaining_pulse_width_s(1.0e9, crossings=True)


class CarrierCombTests(unittest.TestCase):
    def test_uniform_spacing_recovered(self):
        self.assertAlmostEqual(carrier_spacing_hz(FREQS), 1.0e7, places=3)

    def test_unordered_input_is_sorted_first(self):
        self.assertAlmostEqual(
            carrier_spacing_hz(list(reversed(FREQS))), 1.0e7, places=3
        )

    def test_single_carrier_rejected(self):
        with self.assertRaises(ValueError):
            carrier_spacing_hz([11.7e9])

    def test_non_uniform_comb_rejected(self):
        with self.assertRaises(ValueError):
            carrier_spacing_hz([11.70e9, 11.71e9, 11.75e9])

    def test_duplicate_carrier_rejected(self):
        with self.assertRaises(ValueError):
            carrier_spacing_hz([11.7e9, 11.7e9])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            carrier_spacing_hz("11.7e9,11.71e9")


class PeakEnvelopePowerTests(unittest.TestCase):
    def test_equal_carriers_give_n_squared_peak(self):
        self.assertAlmostEqual(peak_envelope_power_w(POWERS), 320.0, places=9)

    def test_unequal_carriers_root_sum_of_voltages(self):
        expected = (math.sqrt(9.0) + math.sqrt(16.0)) ** 2
        self.assertAlmostEqual(peak_envelope_power_w([9.0, 16.0]), expected, places=9)

    def test_single_carrier_rejected(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([20.0])

    def test_zero_carrier_power_rejected(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([20.0, 0.0])


class EnvelopeShapeTests(unittest.TestCase):
    def test_peak_ratio_is_unity_at_beat_peak(self):
        self.assertAlmostEqual(envelope_voltage_ratio(4, 1.0e7, 0.0), 1.0, places=12)

    def test_peak_recurs_once_per_beat_period(self):
        self.assertAlmostEqual(
            envelope_voltage_ratio(4, 1.0e7, 1.0e-7), 1.0, places=12
        )

    def test_first_null_of_main_lobe(self):
        null = 1.0 / (4 * 1.0e7)
        self.assertAlmostEqual(envelope_voltage_ratio(4, 1.0e7, null), 0.0, places=9)

    def test_envelope_decays_away_from_the_peak(self):
        near = envelope_voltage_ratio(4, 1.0e7, 2.0e-9)
        far = envelope_voltage_ratio(4, 1.0e7, 8.0e-9)
        self.assertGreater(near, far)

    def test_main_lobe_base_width(self):
        self.assertAlmostEqual(main_lobe_base_width_s(4, 1.0e7), 5.0e-8, places=15)

    def test_single_carrier_lobe_rejected(self):
        with self.assertRaises(ValueError):
            main_lobe_base_width_s(1, 1.0e7)

    def test_non_finite_time_rejected(self):
        with self.assertRaises(ValueError):
            envelope_voltage_ratio(4, 1.0e7, float("inf"))


class EnvelopePulseWidthTests(unittest.TestCase):
    def test_zero_width_sits_at_the_peak(self):
        self.assertAlmostEqual(
            envelope_power_ratio_for_pulse_width(4, 1.0e7, 0.0), 1.0, places=12
        )

    def test_narrow_pulse_is_just_below_the_peak(self):
        ratio = envelope_power_ratio_for_pulse_width(4, 1.0e7, 1.0e-9)
        self.assertAlmostEqual(ratio, 0.9987669, places=6)

    def test_ratio_falls_as_the_pulse_widens(self):
        wide = envelope_power_ratio_for_pulse_width(4, 1.0e7, 2.0e-8)
        narrow = envelope_power_ratio_for_pulse_width(4, 1.0e7, 2.0e-9)
        self.assertGreater(narrow, wide)

    def test_pulse_at_the_lobe_base_width_is_unreachable(self):
        lobe = main_lobe_base_width_s(4, 1.0e7)
        self.assertAlmostEqual(
            envelope_power_ratio_for_pulse_width(4, 1.0e7, lobe), 0.0, places=15
        )

    def test_pulse_wider_than_the_lobe_is_unreachable(self):
        self.assertAlmostEqual(
            envelope_power_ratio_for_pulse_width(4, 1.0e7, 1.0e-7), 0.0, places=15
        )

    def test_negative_pulse_width_rejected(self):
        with self.assertRaises(ValueError):
            envelope_power_ratio_for_pulse_width(4, 1.0e7, -1.0e-9)


class SusceptibilityTableTests(unittest.TestCase):
    def test_table_is_sorted_by_pulse_width(self):
        rows = normalise_susceptibility_table(
            _table([(3.0e-9, 500.0), (1.0e-9, 700.0)])
        )
        self.assertAlmostEqual(rows[0]["pulse_width_s"], 1.0e-9, places=15)
        self.assertAlmostEqual(rows[1]["pulse_width_s"], 3.0e-9, places=15)

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            normalise_susceptibility_table([])

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            normalise_susceptibility_table([(1.0e-9, 500.0)])

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            normalise_susceptibility_table([{"pulse_width_s": 1.0e-9}])

    def test_zero_breakdown_power_rejected(self):
        with self.assertRaises(ValueError):
            normalise_susceptibility_table(_table([(1.0e-9, 0.0)]))

    def test_duplicate_pulse_width_rejected(self):
        with self.assertRaises(ValueError):
            normalise_susceptibility_table(_table([(1.0e-9, 500.0), (1.0e-9, 600.0)]))


class SweepTests(unittest.TestCase):
    def test_sweep_reports_comb_geometry(self):
        sweep = sweep_envelope_pulse_widths(
            FREQS, POWERS, _table([(1.0e-9, 500.0)])
        )
        self.assertEqual(sweep["n_carriers"], 4)
        self.assertAlmostEqual(sweep["spacing_hz"], 1.0e7, places=3)
        self.assertAlmostEqual(sweep["peak_envelope_power_w"], 320.0, places=9)
        self.assertAlmostEqual(sweep["beat_period_s"], 1.0e-7, places=15)

    def test_short_row_is_not_governing(self):
        short = sustaining_pulse_width_s(CENTRE) * 0.5
        sweep = sweep_envelope_pulse_widths(FREQS, POWERS, _table([(short, 500.0)]))
        point = sweep["points"][0]
        self.assertFalse(point["sustains"])
        self.assertTrue(point["reachable"])
        self.assertFalse(point["governing"])

    def test_row_exactly_at_the_sustaining_width_governs(self):
        exact = sustaining_pulse_width_s(CENTRE)
        sweep = sweep_envelope_pulse_widths(FREQS, POWERS, _table([(exact, 500.0)]))
        self.assertTrue(sweep["points"][0]["sustains"])
        self.assertTrue(sweep["points"][0]["governing"])

    def test_row_beyond_the_lobe_is_unreachable(self):
        sweep = sweep_envelope_pulse_widths(FREQS, POWERS, _table([(2.0e-7, 500.0)]))
        point = sweep["points"][0]
        self.assertFalse(point["reachable"])
        self.assertFalse(point["governing"])
        self.assertEqual(point["headroom_ratio"], float("inf"))

    def test_mismatched_carrier_lists_rejected(self):
        with self.assertRaises(ValueError):
            sweep_envelope_pulse_widths(FREQS, POWERS[:3], _table([(1.0e-9, 500.0)]))

    def test_non_sequence_carrier_powers_rejected(self):
        with self.assertRaises(ValueError):
            sweep_envelope_pulse_widths(FREQS, "20,20,20,20", _table([(1.0e-9, 500.0)]))


class WorstCasePointTests(unittest.TestCase):
    def test_least_headroom_point_wins(self):
        sweep = sweep_envelope_pulse_widths(
            FREQS,
            POWERS,
            _table([(1.0e-9, 900.0), (5.0e-9, 400.0), (2.0e-8, 600.0)]),
        )
        worst = worst_case_envelope_point(sweep["points"])
        self.assertAlmostEqual(worst["pulse_width_s"], 5.0e-9, places=15)

    def test_no_governing_point_returns_none(self):
        short = sustaining_pulse_width_s(CENTRE) * 0.1
        sweep = sweep_envelope_pulse_widths(FREQS, POWERS, _table([(short, 500.0)]))
        self.assertIsNone(worst_case_envelope_point(sweep["points"]))

    def test_empty_point_list_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_envelope_point([])


class MarginTests(unittest.TestCase):
    def test_margin_of_a_factor_of_two(self):
        self.assertAlmostEqual(multipaction_margin_db(200.0, 100.0), 3.0103, places=4)

    def test_margin_is_zero_at_equality(self):
        self.assertAlmostEqual(multipaction_margin_db(100.0, 100.0), 0.0, places=12)

    def test_negative_margin_when_operating_above_breakdown(self):
        self.assertLess(multipaction_margin_db(50.0, 100.0), 0.0)

    def test_zero_operating_power_rejected(self):
        with self.assertRaises(ValueError):
            multipaction_margin_db(100.0, 0.0)

    def test_negative_breakdown_power_rejected(self):
        with self.assertRaises(ValueError):
            multipaction_margin_db(-100.0, 10.0)


class AssessmentTests(unittest.TestCase):
    def test_compliant_case_reports_margin_met(self):
        result = assess_level_two_multicarrier(
            FREQS, POWERS, _table([(5.0e-9, 2000.0)]), 6.0
        )
        self.assertEqual(result["verdict"], "margin-met")
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_db"], 8.0932187, places=6)

    def test_non_compliant_case_reports_margin_not_met(self):
        result = assess_level_two_multicarrier(
            FREQS, POWERS, _table([(5.0e-9, 400.0)]), 6.0
        )
        self.assertEqual(result["verdict"], "margin-not-met")
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])

    def test_exact_six_decibel_boundary_is_compliant(self):
        width = 5.0e-9
        spacing = carrier_spacing_hz(FREQS)
        ratio = envelope_power_ratio_for_pulse_width(len(FREQS), spacing, width)
        envelope_power = peak_envelope_power_w(POWERS) * ratio
        breakdown = envelope_power * (10.0 ** 0.6)
        result = assess_level_two_multicarrier(
            FREQS, POWERS, _table([(width, breakdown)]), 6.0
        )
        self.assertAlmostEqual(result["margin_db"], 6.0, places=9)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "margin-met")

    def test_worst_case_width_and_minimum_level_reported(self):
        result = assess_level_two_multicarrier(
            FREQS,
            POWERS,
            _table([(2.0e-9, 5000.0), (1.0e-8, 800.0), (3.0e-8, 4000.0)]),
            3.0,
        )
        self.assertAlmostEqual(result["worst_case_pulse_width_s"], 1.0e-8, places=15)
        self.assertAlmostEqual(result["governing_breakdown_power_w"], 800.0, places=9)
        self.assertGreater(result["minimum_breakdown_peak_power_w"], 800.0)

    def test_only_short_rows_give_no_sustaining_pulse(self):
        short = sustaining_pulse_width_s(CENTRE) * 0.2
        result = assess_level_two_multicarrier(
            FREQS, POWERS, _table([(short, 100.0)]), 6.0
        )
        self.assertEqual(result["verdict"], "no-sustaining-envelope-pulse")
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["margin_db"])
        self.assertTrue(
            any("sustaining pulse width" in f for f in result["findings"])
        )

    def test_row_beyond_the_lobe_is_flagged(self):
        result = assess_level_two_multicarrier(
            FREQS, POWERS, _table([(2.0e-7, 100.0)]), 6.0
        )
        self.assertEqual(result["verdict"], "no-sustaining-envelope-pulse")
        self.assertTrue(any("main lobe" in f for f in result["findings"]))

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            assess_level_two_multicarrier(
                FREQS, POWERS, _table([(5.0e-9, 400.0)]), -1.0
            )

    def test_fewer_crossings_relax_the_sustaining_width(self):
        width = sustaining_pulse_width_s(CENTRE, crossings=10)
        strict = assess_level_two_multicarrier(
            FREQS, POWERS, _table([(width, 2000.0)]), 3.0
        )
        relaxed = assess_level_two_multicarrier(
            FREQS, POWERS, _table([(width, 2000.0)]), 3.0, crossings=10
        )
        self.assertEqual(strict["verdict"], "no-sustaining-envelope-pulse")
        self.assertEqual(relaxed["verdict"], "margin-met")


if __name__ == "__main__":
    unittest.main()
