#!/usr/bin/env python3
"""Contract test for the ECSS-E-ST-20-01C clause 6.4.3.1 overview leaf."""

import math
import unittest

from e2001_multi_frequency_test_overview_logic import (
    BASIS_AVERAGE_FLOOR,
    BASIS_PEAK_ENVELOPE,
    BASIS_SUSTAINED_ENVELOPE,
    CROSSINGS_PER_RF_PERIOD,
    DEFAULT_GAP_CROSSINGS,
    assess_test_feasibility,
    carrier_spacing_hz,
    carriers_are_equal_power,
    dwell_above_level_s,
    envelope_power_w,
    equivalent_single_carrier_power_w,
    first_envelope_null_s,
    multi_frequency_test_overview,
    multipactor_onset_time_s,
    peak_envelope_power_w,
    summarize_overview,
    sustained_envelope_level_w,
    total_average_power_w,
    validate_carrier_set,
)


def comb(count, spacing_hz, power_w, start_hz=11.9e9):
    return [
        {"frequency_hz": start_hz + index * spacing_hz, "power_w": power_w}
        for index in range(count)
    ]


NARROW = comb(4, 1.0e5, 120.0)
MODERATE = comb(4, 4.0e7, 120.0)
WIDE = comb(4, 4.0e9, 120.0)
F_TEST = 12.0e9


class TestCarrierSetValidation(unittest.TestCase):
    def test_valid_set_is_returned_sorted(self):
        unsorted_set = [
            {"frequency_hz": 12.1e9, "power_w": 50.0},
            {"frequency_hz": 11.9e9, "power_w": 50.0},
        ]
        cleaned = validate_carrier_set(unsorted_set)
        self.assertAlmostEqual(cleaned[0]["frequency_hz"], 11.9e9)

    def test_single_carrier_rejected(self):
        with self.assertRaises(ValueError):
            validate_carrier_set([{"frequency_hz": 12.0e9, "power_w": 50.0}])

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_carrier_set([])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_carrier_set({"frequency_hz": 12.0e9, "power_w": 50.0})

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_carrier_set(["12.0e9", "12.1e9"])

    def test_duplicate_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_carrier_set(
                [
                    {"frequency_hz": 12.0e9, "power_w": 50.0},
                    {"frequency_hz": 12.0e9, "power_w": 60.0},
                ]
            )

    def test_zero_power_rejected(self):
        with self.assertRaises(ValueError):
            validate_carrier_set(
                [
                    {"frequency_hz": 12.0e9, "power_w": 0.0},
                    {"frequency_hz": 12.1e9, "power_w": 60.0},
                ]
            )

    def test_missing_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_carrier_set([{"power_w": 50.0}, {"frequency_hz": 12.1e9, "power_w": 60.0}])


class TestCarrierSetDescriptors(unittest.TestCase):
    def test_equal_carriers_give_the_square_law_peak(self):
        self.assertAlmostEqual(peak_envelope_power_w(MODERATE), 16.0 * 120.0)

    def test_unequal_carriers_use_the_root_sum(self):
        carriers = [
            {"frequency_hz": 12.0e9, "power_w": 100.0},
            {"frequency_hz": 12.1e9, "power_w": 400.0},
        ]
        self.assertAlmostEqual(peak_envelope_power_w(carriers), 900.0)

    def test_average_power_is_the_plain_sum(self):
        self.assertAlmostEqual(total_average_power_w(MODERATE), 480.0)

    def test_peak_exceeds_average_for_more_than_one_carrier(self):
        self.assertGreater(peak_envelope_power_w(MODERATE), total_average_power_w(MODERATE))

    def test_spacing_reports_the_comb_step(self):
        self.assertAlmostEqual(carrier_spacing_hz(MODERATE)["spacing_hz"], 4.0e7)

    def test_spacing_reports_the_carrier_count(self):
        self.assertEqual(carrier_spacing_hz(MODERATE)["count"], 4)

    def test_uniform_comb_is_recognized(self):
        self.assertTrue(carrier_spacing_hz(MODERATE)["uniform"])

    def test_non_uniform_comb_is_recognized(self):
        ragged = [
            {"frequency_hz": 12.00e9, "power_w": 120.0},
            {"frequency_hz": 12.04e9, "power_w": 120.0},
            {"frequency_hz": 12.30e9, "power_w": 120.0},
        ]
        self.assertFalse(carrier_spacing_hz(ragged)["uniform"])

    def test_smallest_spacing_is_reported_for_a_ragged_comb(self):
        ragged = [
            {"frequency_hz": 12.00e9, "power_w": 120.0},
            {"frequency_hz": 12.04e9, "power_w": 120.0},
            {"frequency_hz": 12.30e9, "power_w": 120.0},
        ]
        self.assertAlmostEqual(carrier_spacing_hz(ragged)["spacing_hz"], 4.0e7, delta=1.0)

    def test_equal_power_comb_is_recognized(self):
        self.assertTrue(carriers_are_equal_power(MODERATE))

    def test_unequal_power_comb_is_recognized(self):
        mixed = [
            {"frequency_hz": 12.0e9, "power_w": 120.0},
            {"frequency_hz": 12.04e9, "power_w": 60.0},
        ]
        self.assertFalse(carriers_are_equal_power(mixed))


class TestEnvelopeModel(unittest.TestCase):
    def test_envelope_peaks_at_the_origin(self):
        self.assertAlmostEqual(envelope_power_w(4, 120.0, 4.0e7, 0.0), 1920.0)

    def test_envelope_repeats_after_one_period(self):
        period = 1.0 / 4.0e7
        self.assertAlmostEqual(envelope_power_w(4, 120.0, 4.0e7, period), 1920.0)

    def test_envelope_vanishes_at_the_first_null(self):
        null = first_envelope_null_s(4, 4.0e7)
        self.assertAlmostEqual(envelope_power_w(4, 120.0, 4.0e7, null), 0.0, places=6)

    def test_envelope_decreases_across_the_main_lobe(self):
        null = first_envelope_null_s(4, 4.0e7)
        samples = [
            envelope_power_w(4, 120.0, 4.0e7, fraction * null / 10.0)
            for fraction in range(11)
        ]
        for earlier, later in zip(samples, samples[1:]):
            self.assertGreaterEqual(earlier + 1e-9, later)

    def test_null_moves_in_with_more_carriers(self):
        self.assertLess(first_envelope_null_s(8, 4.0e7), first_envelope_null_s(4, 4.0e7))

    def test_null_moves_in_with_wider_spacing(self):
        self.assertLess(first_envelope_null_s(4, 8.0e7), first_envelope_null_s(4, 4.0e7))

    def test_single_carrier_envelope_rejected(self):
        with self.assertRaises(ValueError):
            envelope_power_w(1, 120.0, 4.0e7, 0.0)

    def test_negative_time_rejected(self):
        with self.assertRaises(ValueError):
            envelope_power_w(4, 120.0, 4.0e7, -1.0e-9)

    def test_zero_spacing_rejected(self):
        with self.assertRaises(ValueError):
            envelope_power_w(4, 120.0, 0.0, 1.0e-9)

    def test_non_integer_count_rejected(self):
        with self.assertRaises(ValueError):
            envelope_power_w(4.0, 120.0, 4.0e7, 0.0)

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):
            first_envelope_null_s(True, 4.0e7)


class TestDwell(unittest.TestCase):
    def test_dwell_at_the_peak_level_is_zero(self):
        self.assertAlmostEqual(dwell_above_level_s(4, 120.0, 4.0e7, 1920.0), 0.0)

    def test_dwell_above_the_peak_level_is_zero(self):
        self.assertAlmostEqual(dwell_above_level_s(4, 120.0, 4.0e7, 5000.0), 0.0)

    def test_dwell_widens_as_the_level_falls(self):
        high = dwell_above_level_s(4, 120.0, 4.0e7, 1800.0)
        low = dwell_above_level_s(4, 120.0, 4.0e7, 600.0)
        self.assertGreater(low, high)

    def test_dwell_approaches_the_main_lobe_width_at_a_low_level(self):
        widest = 2.0 * first_envelope_null_s(4, 4.0e7)
        self.assertAlmostEqual(
            dwell_above_level_s(4, 120.0, 4.0e7, 1.0e-6) / widest, 1.0, places=4
        )

    def test_dwell_is_consistent_with_the_envelope_it_measures(self):
        level = 1000.0
        half = 0.5 * dwell_above_level_s(4, 120.0, 4.0e7, level)
        self.assertAlmostEqual(envelope_power_w(4, 120.0, 4.0e7, half), level, places=3)

    def test_zero_level_rejected(self):
        with self.assertRaises(ValueError):
            dwell_above_level_s(4, 120.0, 4.0e7, 0.0)

    def test_negative_level_rejected(self):
        with self.assertRaises(ValueError):
            dwell_above_level_s(4, 120.0, 4.0e7, -10.0)


class TestOnsetTime(unittest.TestCase):
    def test_onset_time_follows_the_half_period_rule(self):
        expected = DEFAULT_GAP_CROSSINGS / (CROSSINGS_PER_RF_PERIOD * F_TEST)
        self.assertAlmostEqual(multipactor_onset_time_s(F_TEST), expected)

    def test_onset_time_falls_with_frequency(self):
        self.assertLess(multipactor_onset_time_s(24.0e9), multipactor_onset_time_s(12.0e9))

    def test_fewer_crossings_shorten_the_onset(self):
        self.assertLess(
            multipactor_onset_time_s(F_TEST, crossings=5),
            multipactor_onset_time_s(F_TEST, crossings=20),
        )

    def test_zero_crossings_rejected(self):
        with self.assertRaises(ValueError):
            multipactor_onset_time_s(F_TEST, crossings=0)

    def test_non_integer_crossings_rejected(self):
        with self.assertRaises(ValueError):
            multipactor_onset_time_s(F_TEST, crossings=20.0)

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            multipactor_onset_time_s(0.0)


class TestSustainedLevel(unittest.TestCase):
    def test_level_sits_between_average_and_peak(self):
        onset = multipactor_onset_time_s(F_TEST)
        level = sustained_envelope_level_w(4, 120.0, 4.0e7, onset)
        self.assertGreater(level, 480.0)
        self.assertLess(level, 1920.0)

    def test_level_dwell_matches_the_onset_time(self):
        onset = multipactor_onset_time_s(F_TEST)
        level = sustained_envelope_level_w(4, 120.0, 4.0e7, onset)
        self.assertAlmostEqual(
            dwell_above_level_s(4, 120.0, 4.0e7, level) / onset, 1.0, places=4
        )

    def test_very_wide_spacing_falls_back_to_the_average(self):
        onset = multipactor_onset_time_s(F_TEST)
        self.assertAlmostEqual(
            sustained_envelope_level_w(4, 120.0, 4.0e9, onset), 480.0
        )

    def test_very_narrow_spacing_approaches_the_peak(self):
        onset = multipactor_onset_time_s(F_TEST)
        level = sustained_envelope_level_w(4, 120.0, 1.0e5, onset)
        self.assertAlmostEqual(level / 1920.0, 1.0, places=5)

    def test_level_is_never_below_the_average(self):
        onset = multipactor_onset_time_s(1.0e9)
        self.assertGreaterEqual(
            sustained_envelope_level_w(4, 120.0, 1.0e9, onset), 480.0
        )

    def test_zero_onset_time_rejected(self):
        with self.assertRaises(ValueError):
            sustained_envelope_level_w(4, 120.0, 4.0e7, 0.0)


class TestEquivalentDrive(unittest.TestCase):
    def test_moderate_spacing_uses_the_sustained_level(self):
        result = equivalent_single_carrier_power_w(MODERATE, F_TEST)
        self.assertEqual(result["basis"], BASIS_SUSTAINED_ENVELOPE)

    def test_narrow_spacing_uses_the_peak_envelope(self):
        result = equivalent_single_carrier_power_w(NARROW, F_TEST)
        self.assertEqual(result["basis"], BASIS_PEAK_ENVELOPE)

    def test_wide_spacing_falls_back_to_the_average_floor(self):
        result = equivalent_single_carrier_power_w(WIDE, F_TEST)
        self.assertEqual(result["basis"], BASIS_AVERAGE_FLOOR)

    def test_average_floor_case_carries_a_note(self):
        result = equivalent_single_carrier_power_w(WIDE, F_TEST)
        self.assertTrue(any("average power" in note for note in result["notes"]))

    def test_margin_scales_the_drive(self):
        plain = equivalent_single_carrier_power_w(MODERATE, F_TEST)
        raised = equivalent_single_carrier_power_w(MODERATE, F_TEST, margin_db=3.0)
        self.assertAlmostEqual(
            raised["equivalent_drive_w"] / plain["equivalent_drive_w"],
            10.0 ** 0.3,
            places=9,
        )

    def test_zero_margin_leaves_the_level_untouched(self):
        result = equivalent_single_carrier_power_w(MODERATE, F_TEST)
        self.assertAlmostEqual(
            result["equivalent_drive_w"], result["representative_level_w"]
        )

    def test_unequal_carriers_use_the_peak_envelope_with_a_note(self):
        mixed = [
            {"frequency_hz": 11.90e9, "power_w": 120.0},
            {"frequency_hz": 11.94e9, "power_w": 60.0},
        ]
        result = equivalent_single_carrier_power_w(mixed, F_TEST)
        self.assertEqual(result["basis"], BASIS_PEAK_ENVELOPE)
        self.assertTrue(any("closed-form" in note for note in result["notes"]))

    def test_ragged_comb_uses_the_peak_envelope_with_a_note(self):
        ragged = [
            {"frequency_hz": 11.90e9, "power_w": 120.0},
            {"frequency_hz": 11.94e9, "power_w": 120.0},
            {"frequency_hz": 12.30e9, "power_w": 120.0},
        ]
        result = equivalent_single_carrier_power_w(ragged, F_TEST)
        self.assertEqual(result["basis"], BASIS_PEAK_ENVELOPE)
        self.assertTrue(result["notes"])

    def test_result_reports_the_onset_time_used(self):
        result = equivalent_single_carrier_power_w(MODERATE, F_TEST)
        self.assertAlmostEqual(result["onset_time_s"], multipactor_onset_time_s(F_TEST))

    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_single_carrier_power_w(MODERATE, F_TEST, margin_db=-3.0)

    def test_non_numeric_margin_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_single_carrier_power_w(MODERATE, F_TEST, margin_db="3 dB")

    def test_zero_test_frequency_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_single_carrier_power_w(MODERATE, 0.0)

    def test_single_carrier_input_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_single_carrier_power_w(
                [{"frequency_hz": 12.0e9, "power_w": 120.0}], F_TEST
            )


class TestFeasibility(unittest.TestCase):
    def test_comfortable_case_is_feasible(self):
        self.assertTrue(assess_test_feasibility(1000.0, 2000.0, 2000.0)["feasible"])

    def test_facility_shortfall_is_reported(self):
        result = assess_test_feasibility(3000.0, 2000.0, 5000.0)
        self.assertFalse(result["feasible"])
        self.assertTrue(any("facility" in f for f in result["findings"]))

    def test_thermal_shortfall_is_reported(self):
        result = assess_test_feasibility(3000.0, 5000.0, 2000.0)
        self.assertFalse(result["feasible"])
        self.assertTrue(any("thermal rating" in f for f in result["findings"]))

    def test_both_shortfalls_are_reported_together(self):
        result = assess_test_feasibility(9000.0, 2000.0, 2000.0)
        self.assertEqual(len(result["findings"]), 2)

    def test_drive_exactly_at_the_limit_is_feasible(self):
        self.assertTrue(assess_test_feasibility(2000.0, 2000.0, 2000.0)["feasible"])

    def test_limit_reached_through_a_different_expression_is_still_feasible(self):
        powers = [100.0, 200.0, 300.0]
        carriers = [
            {"frequency_hz": 11.90e9 + index * 1.0e5, "power_w": value}
            for index, value in enumerate(powers)
        ]
        drive = peak_envelope_power_w(carriers)
        cross_terms = 2.0 * (
            math.sqrt(powers[0] * powers[1])
            + math.sqrt(powers[0] * powers[2])
            + math.sqrt(powers[1] * powers[2])
        )
        limit = sum(powers) + cross_terms
        self.assertNotEqual(drive, limit)
        self.assertTrue(assess_test_feasibility(drive, limit, limit)["feasible"])

    def test_zero_facility_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_feasibility(1000.0, 0.0, 2000.0)

    def test_negative_thermal_rating_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_feasibility(1000.0, 2000.0, -1.0)


class TestOverviewRecord(unittest.TestCase):
    def test_clean_record_is_valid(self):
        record = multi_frequency_test_overview(
            {
                "carriers": MODERATE,
                "f_test_hz": F_TEST,
                "margin_db": 3.0,
                "facility_max_w": 8000.0,
                "thermal_rating_w": 8000.0,
            }
        )
        self.assertTrue(record["single_carrier_substitution_valid"])

    def test_over_test_ratio_is_the_drive_over_the_average(self):
        record = multi_frequency_test_overview(
            {"carriers": MODERATE, "f_test_hz": F_TEST}
        )
        self.assertAlmostEqual(
            record["over_test_ratio"],
            record["equivalent"]["equivalent_drive_w"] / 480.0,
        )

    def test_over_test_ratio_exceeds_one_for_a_carrier_comb(self):
        record = multi_frequency_test_overview(
            {"carriers": MODERATE, "f_test_hz": F_TEST}
        )
        self.assertGreater(record["over_test_ratio"], 1.0)

    def test_record_without_limits_has_no_feasibility_block(self):
        record = multi_frequency_test_overview(
            {"carriers": MODERATE, "f_test_hz": F_TEST}
        )
        self.assertIsNone(record["feasibility"])

    def test_thermal_shortfall_invalidates_the_record(self):
        record = multi_frequency_test_overview(
            {
                "carriers": MODERATE,
                "f_test_hz": F_TEST,
                "facility_max_w": 8000.0,
                "thermal_rating_w": 500.0,
            }
        )
        self.assertFalse(record["single_carrier_substitution_valid"])

    def test_one_limit_alone_rejected(self):
        with self.assertRaises(ValueError):
            multi_frequency_test_overview(
                {"carriers": MODERATE, "f_test_hz": F_TEST, "facility_max_w": 8000.0}
            )

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            multi_frequency_test_overview([MODERATE, F_TEST])

    def test_missing_carriers_rejected(self):
        with self.assertRaises(ValueError):
            multi_frequency_test_overview({"f_test_hz": F_TEST})

    def test_findings_accumulate_from_both_stages(self):
        record = multi_frequency_test_overview(
            {
                "carriers": WIDE,
                "f_test_hz": F_TEST,
                "facility_max_w": 100.0,
                "thermal_rating_w": 100.0,
            }
        )
        self.assertGreaterEqual(len(record["findings"]), 3)


class TestSummary(unittest.TestCase):
    def test_summary_reports_a_valid_verdict(self):
        record = multi_frequency_test_overview(
            {"carriers": MODERATE, "f_test_hz": F_TEST}
        )
        lines = summarize_overview(record)
        self.assertTrue(
            any("verdict: single-carrier substitution valid" in line for line in lines)
        )

    def test_summary_reports_the_basis(self):
        record = multi_frequency_test_overview(
            {"carriers": MODERATE, "f_test_hz": F_TEST}
        )
        lines = summarize_overview(record)
        self.assertTrue(any(BASIS_SUSTAINED_ENVELOPE in line for line in lines))

    def test_summary_lists_every_finding(self):
        record = multi_frequency_test_overview(
            {
                "carriers": WIDE,
                "f_test_hz": F_TEST,
                "facility_max_w": 100.0,
                "thermal_rating_w": 100.0,
            }
        )
        lines = summarize_overview(record)
        emitted = [line for line in lines if line.startswith("finding: ")]
        self.assertEqual(len(emitted), len(record["findings"]))

    def test_summary_rejects_a_foreign_mapping(self):
        with self.assertRaises(ValueError):
            summarize_overview({"over_test_ratio": 4.0})


class TestDeterminism(unittest.TestCase):
    def test_repeated_derivation_is_bit_identical(self):
        first = equivalent_single_carrier_power_w(MODERATE, F_TEST, margin_db=3.0)
        second = equivalent_single_carrier_power_w(MODERATE, F_TEST, margin_db=3.0)
        self.assertEqual(
            first["equivalent_drive_w"], second["equivalent_drive_w"]
        )

    def test_drive_never_exceeds_the_margined_peak_envelope(self):
        for carriers in (NARROW, MODERATE, WIDE):
            result = equivalent_single_carrier_power_w(carriers, F_TEST, margin_db=6.0)
            ceiling = result["peak_envelope_power_w"] * 10.0 ** 0.6
            self.assertTrue(
                result["equivalent_drive_w"] <= ceiling
                or math.isclose(result["equivalent_drive_w"], ceiling, rel_tol=1e-9)
            )


if __name__ == "__main__":
    unittest.main()
