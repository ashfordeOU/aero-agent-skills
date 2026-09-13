#!/usr/bin/env python3
"""Gate 3 contract tests for the clause 6.4.3.3 reduced-carrier logic."""

import math
import unittest

import e2001_reduced_carrier_equivalent_power_test_logic as logic


def carrier(cid, power_w, frequency_hz):
    return {"id": cid, "power_w": power_w, "frequency_hz": frequency_hz}


def uniform_set(count, power_w, first_hz, spacing_hz):
    return [
        carrier("c%02d" % index, power_w, first_hz + index * spacing_hz)
        for index in range(count)
    ]


EIGHT_AT_20W = uniform_set(8, 20.0, 12.00e9, 40.0e6)
FOUR_AT_25W = uniform_set(4, 25.0, 11.70e9, 50.0e6)
THIRTY_TWO_TIGHT = uniform_set(32, 5.0, 2.00e9, 200.0e6)


class TestCarrierSetValidation(unittest.TestCase):
    def test_valid_set_sorted_by_frequency(self):
        result = logic.validate_carrier_set(
            [carrier("hi", 4.0, 2.0e9), carrier("lo", 9.0, 1.0e9)]
        )
        self.assertEqual([item["id"] for item in result], ["lo", "hi"])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set("c1")

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([])

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([["c1", 1.0, 1.0e9]])

    def test_missing_id_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([{"power_w": 1.0, "frequency_hz": 1.0e9}])

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set(
                [carrier("same", 1.0, 1.0e9), carrier("same", 2.0, 2.0e9)]
            )

    def test_non_positive_power_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("c", 0.0, 1.0e9)])

    def test_boolean_power_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("c", False, 1.0e9)])

    def test_non_finite_frequency_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("c", 1.0, float("inf"))])

    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("c", 1.0, -2.0e9)])


class TestReductionCount(unittest.TestCase):
    def test_valid_reduction_returns_operational_count(self):
        self.assertEqual(logic.validate_reduction_count(EIGHT_AT_20W, 3), 8)

    def test_reduction_to_one_is_allowed_by_the_validator(self):
        self.assertEqual(logic.validate_reduction_count(FOUR_AT_25W, 1), 4)

    def test_equal_count_is_not_a_reduction(self):
        with self.assertRaises(ValueError):
            logic.validate_reduction_count(FOUR_AT_25W, 4)

    def test_larger_count_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_reduction_count(FOUR_AT_25W, 5)

    def test_zero_count_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_reduction_count(FOUR_AT_25W, 0)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_reduction_count(FOUR_AT_25W, -2)

    def test_float_count_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_reduction_count(FOUR_AT_25W, 2.0)

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_reduction_count(FOUR_AT_25W, True)


class TestEquivalentDrive(unittest.TestCase):
    def test_voltage_sum_of_four_equal_carriers(self):
        self.assertAlmostEqual(logic.envelope_voltage_sum(FOUR_AT_25W), 20.0)

    def test_total_average_power(self):
        self.assertAlmostEqual(logic.total_average_power_w(FOUR_AT_25W), 100.0)

    def test_reduced_carrier_power_two_from_four(self):
        # (20/2)**2 = 100 W per retained carrier
        self.assertAlmostEqual(logic.reduced_carrier_power_w(FOUR_AT_25W, 2), 100.0)

    def test_reduced_set_average_power_two_from_four(self):
        self.assertAlmostEqual(
            logic.reduced_set_average_power_w(FOUR_AT_25W, 2), 200.0
        )

    def test_reduced_set_average_is_equivalent_over_count(self):
        equivalent = logic.envelope_voltage_sum(EIGHT_AT_20W) ** 2
        self.assertAlmostEqual(
            logic.reduced_set_average_power_w(EIGHT_AT_20W, 4), equivalent / 4.0
        )

    def test_reduced_set_draws_less_than_single_carrier_equivalent(self):
        equivalent = logic.envelope_voltage_sum(EIGHT_AT_20W) ** 2
        self.assertLess(
            logic.reduced_set_average_power_w(EIGHT_AT_20W, 3), equivalent
        )

    def test_peak_voltage_is_preserved_by_the_reduction(self):
        per_carrier = logic.reduced_carrier_power_w(EIGHT_AT_20W, 5)
        self.assertAlmostEqual(
            5.0 * math.sqrt(per_carrier), logic.envelope_voltage_sum(EIGHT_AT_20W)
        )

    def test_reduced_power_propagates_count_error(self):
        with self.assertRaises(ValueError):
            logic.reduced_carrier_power_w(FOUR_AT_25W, 9)


class TestSpacing(unittest.TestCase):
    def test_uniform_spacing(self):
        self.assertAlmostEqual(
            logic.carrier_spacing_hz(EIGHT_AT_20W), 40.0e6, places=1
        )

    def test_single_carrier_has_no_spacing(self):
        with self.assertRaises(ValueError):
            logic.carrier_spacing_hz([carrier("solo", 1.0, 1.0e9)])

    def test_non_uniform_spacing_rejected(self):
        with self.assertRaises(ValueError):
            logic.carrier_spacing_hz(
                [
                    carrier("a", 1.0, 1.000e9),
                    carrier("b", 1.0, 1.010e9),
                    carrier("c", 1.0, 1.050e9),
                ]
            )

    def test_repeated_frequency_rejected(self):
        with self.assertRaises(ValueError):
            logic.carrier_spacing_hz(
                [carrier("a", 1.0, 1.0e9), carrier("b", 1.0, 1.0e9)]
            )

    def test_bad_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            logic.carrier_spacing_hz(EIGHT_AT_20W, rel_tol=-1e-6)


class TestOnsetRatio(unittest.TestCase):
    def test_zero_margin_puts_onset_at_the_peak(self):
        self.assertAlmostEqual(logic.onset_voltage_ratio(0.0), 1.0)

    def test_six_db_margin_halves_the_voltage(self):
        self.assertAlmostEqual(logic.onset_voltage_ratio(6.0), 0.5011872336)

    def test_twenty_db_margin_is_one_tenth(self):
        self.assertAlmostEqual(logic.onset_voltage_ratio(20.0), 0.1)

    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            logic.onset_voltage_ratio(-3.0)

    def test_non_numeric_margin_rejected(self):
        with self.assertRaises(ValueError):
            logic.onset_voltage_ratio("6 dB")


class TestEnvelopeShape(unittest.TestCase):
    def test_peak_is_unity_at_zero_offset(self):
        self.assertAlmostEqual(logic.envelope_amplitude_ratio(8, 0.0), 1.0)

    def test_peak_is_unity_at_a_full_period(self):
        self.assertAlmostEqual(logic.envelope_amplitude_ratio(8, 1.0), 1.0)

    def test_first_null_is_zero(self):
        self.assertAlmostEqual(logic.envelope_amplitude_ratio(8, 0.125), 0.0)

    def test_single_carrier_envelope_is_flat(self):
        self.assertAlmostEqual(logic.envelope_amplitude_ratio(1, 0.31), 1.0)

    def test_two_carrier_envelope_matches_closed_form(self):
        # For two equal carriers the kernel reduces exactly to cos(pi*x).
        for offset in (0.05, 0.17, 0.33, 0.49):
            self.assertAlmostEqual(
                logic.envelope_amplitude_ratio(2, offset),
                abs(math.cos(math.pi * offset)),
            )

    def test_envelope_decreases_across_the_main_lobe(self):
        previous = 1.0
        for step in range(1, 12):
            value = logic.envelope_amplitude_ratio(6, step * (1.0 / 6.0) / 12.0)
            self.assertLess(value, previous)
            previous = value

    def test_zero_carrier_count_rejected(self):
        with self.assertRaises(ValueError):
            logic.envelope_amplitude_ratio(0, 0.1)

    def test_float_carrier_count_rejected(self):
        with self.assertRaises(ValueError):
            logic.envelope_amplitude_ratio(4.0, 0.1)

    def test_non_finite_offset_rejected(self):
        with self.assertRaises(ValueError):
            logic.envelope_amplitude_ratio(4, float("nan"))


class TestEnvelopeDwell(unittest.TestCase):
    def test_two_carrier_dwell_matches_closed_form(self):
        # Independent oracle: cos(pi*x) = ratio solves in closed form, while
        # the module bisects the Dirichlet kernel.
        for ratio in (0.2, 0.5, 0.75, 0.9):
            analytic = 2.0 * (math.acos(ratio) / math.pi) / 1.0e6
            self.assertAlmostEqual(
                logic.envelope_dwell_above_ratio_s(2, 1.0e6, ratio), analytic
            )

    def test_single_carrier_dwell_is_unbounded(self):
        self.assertEqual(
            logic.envelope_dwell_above_ratio_s(1, 1.0e6, 0.5), math.inf
        )

    def test_fewer_carriers_widen_the_main_lobe(self):
        wide = logic.envelope_dwell_above_ratio_s(3, 40.0e6, 0.5)
        narrow = logic.envelope_dwell_above_ratio_s(8, 40.0e6, 0.5)
        self.assertGreater(wide, narrow)

    def test_dwell_scales_inversely_with_spacing(self):
        tight = logic.envelope_dwell_above_ratio_s(4, 10.0e6, 0.5)
        wide = logic.envelope_dwell_above_ratio_s(4, 20.0e6, 0.5)
        self.assertAlmostEqual(tight, 2.0 * wide)

    def test_lower_onset_ratio_gives_longer_dwell(self):
        self.assertGreater(
            logic.envelope_dwell_above_ratio_s(6, 25.0e6, 0.2),
            logic.envelope_dwell_above_ratio_s(6, 25.0e6, 0.8),
        )

    def test_dwell_never_exceeds_the_main_lobe_width(self):
        dwell = logic.envelope_dwell_above_ratio_s(8, 40.0e6, 0.01)
        self.assertLess(dwell, 2.0 / (8.0 * 40.0e6))

    def test_ratio_at_one_rejected(self):
        with self.assertRaises(ValueError):
            logic.envelope_dwell_above_ratio_s(4, 1.0e6, 1.0)

    def test_ratio_at_zero_rejected(self):
        with self.assertRaises(ValueError):
            logic.envelope_dwell_above_ratio_s(4, 1.0e6, 0.0)

    def test_negative_spacing_rejected(self):
        with self.assertRaises(ValueError):
            logic.envelope_dwell_above_ratio_s(4, -1.0e6, 0.5)

    def test_zero_carrier_count_rejected(self):
        with self.assertRaises(ValueError):
            logic.envelope_dwell_above_ratio_s(0, 1.0e6, 0.5)


class TestTransitAndCrossings(unittest.TestCase):
    def test_first_order_transit(self):
        self.assertAlmostEqual(logic.electron_transit_time_s(12.0e9), 1.0 / 24.0e9)

    def test_fifth_order_transit(self):
        self.assertAlmostEqual(
            logic.electron_transit_time_s(1.0e9, resonant_order=5), 2.5e-9
        )

    def test_even_order_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(1.0e9, resonant_order=4)

    def test_order_above_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(1.0e9, resonant_order=23)

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(0.0)

    def test_crossings_from_dwell(self):
        self.assertAlmostEqual(
            logic.gap_crossings_in_dwell(2.0e-9, 10.0e9), 40.0
        )

    def test_unbounded_dwell_gives_unbounded_crossings(self):
        self.assertEqual(
            logic.gap_crossings_in_dwell(math.inf, 10.0e9), math.inf
        )

    def test_negative_dwell_rejected(self):
        with self.assertRaises(ValueError):
            logic.gap_crossings_in_dwell(-1.0e-9, 10.0e9)


class TestPowerRatio(unittest.TestCase):
    def test_three_times_is_about_four_point_eight_db(self):
        self.assertAlmostEqual(logic.power_ratio_db(300.0, 100.0), 4.7712125472)

    def test_zero_denominator_rejected(self):
        with self.assertRaises(ValueError):
            logic.power_ratio_db(100.0, 0.0)

    def test_negative_numerator_rejected(self):
        with self.assertRaises(ValueError):
            logic.power_ratio_db(-100.0, 10.0)


class TestFullAssessment(unittest.TestCase):
    def setUp(self):
        self.report = logic.assess_reduced_carrier_equivalent_power_test(
            EIGHT_AT_20W, 3, source_max_power_per_carrier_w=300.0
        )

    def test_reduction_is_acceptable(self):
        self.assertTrue(self.report["compliant"])
        self.assertEqual(
            self.report["verdict"], "reduced-carrier-equivalent-drive-acceptable"
        )

    def test_per_carrier_drive(self):
        self.assertAlmostEqual(
            self.report["reduced_carrier_power_w"], (8.0 * math.sqrt(20.0) / 3.0) ** 2
        )

    def test_retained_set_average_power(self):
        self.assertAlmostEqual(
            self.report["reduced_set_average_power_w"], 1280.0 / 3.0
        )

    def test_drive_saving_equals_retained_count_in_db(self):
        self.assertAlmostEqual(
            self.report["drive_saving_db"], 10.0 * math.log10(3.0)
        )

    def test_reduced_dwell_exceeds_operational_dwell(self):
        self.assertGreater(
            self.report["reduced_dwell_s"], self.report["operational_dwell_s"]
        )

    def test_reduced_crossings_clear_the_growth_criterion(self):
        self.assertGreater(
            self.report["reduced_gap_crossings"], float(logic.MIN_GAP_CROSSINGS)
        )

    def test_spacing_defaults_to_the_operational_spacing(self):
        self.assertAlmostEqual(
            self.report["reduced_spacing_hz"], self.report["operational_spacing_hz"]
        )

    def test_onset_ratio_follows_the_default_margin(self):
        self.assertAlmostEqual(self.report["onset_voltage_ratio"], 0.5011872336)

    def test_widened_spacing_makes_the_reduction_less_severe(self):
        report = logic.assess_reduced_carrier_equivalent_power_test(
            EIGHT_AT_20W, 3, reduced_spacing_hz=400.0e6
        )
        codes = [item["code"] for item in report["findings"]]
        self.assertIn("reduced-dwell-less-severe-than-operational", codes)
        self.assertEqual(
            report["verdict"], "reduced-carrier-equivalent-drive-not-acceptable"
        )

    def test_short_dwell_spectrum_fails_the_growth_criterion(self):
        report = logic.assess_reduced_carrier_equivalent_power_test(
            THIRTY_TWO_TIGHT, 24
        )
        codes = [item["code"] for item in report["findings"]]
        self.assertIn("insufficient-electron-gap-crossings", codes)

    def test_bench_shortfall_is_reported(self):
        report = logic.assess_reduced_carrier_equivalent_power_test(
            EIGHT_AT_20W, 3, source_max_power_per_carrier_w=50.0
        )
        codes = [item["code"] for item in report["findings"]]
        self.assertIn("reduced-carrier-drive-exceeds-source-capability", codes)

    def test_bench_limit_exactly_met_is_compliant(self):
        exact = logic.reduced_carrier_power_w(FOUR_AT_25W, 2)
        report = logic.assess_reduced_carrier_equivalent_power_test(
            FOUR_AT_25W, 2, source_max_power_per_carrier_w=exact
        )
        codes = [item["code"] for item in report["findings"]]
        self.assertNotIn("reduced-carrier-drive-exceeds-source-capability", codes)

    def test_single_retained_carrier_is_out_of_scope(self):
        report = logic.assess_reduced_carrier_equivalent_power_test(FOUR_AT_25W, 1)
        self.assertEqual(
            report["verdict"], "reduced-carrier-equivalent-drive-out-of-scope"
        )
        self.assertEqual(report["reduced_gap_crossings"], math.inf)

    def test_non_positive_bench_limit_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_reduced_carrier_equivalent_power_test(
                EIGHT_AT_20W, 3, source_max_power_per_carrier_w=0.0
            )

    def test_non_positive_reduced_spacing_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_reduced_carrier_equivalent_power_test(
                EIGHT_AT_20W, 3, reduced_spacing_hz=-1.0
            )

    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_reduced_carrier_equivalent_power_test(
                EIGHT_AT_20W, 3, margin_db=-1.0
            )

    def test_non_uniform_operational_set_rejected(self):
        ragged = [
            carrier("a", 10.0, 1.000e9),
            carrier("b", 10.0, 1.010e9),
            carrier("c", 10.0, 1.100e9),
        ]
        with self.assertRaises(ValueError):
            logic.assess_reduced_carrier_equivalent_power_test(ragged, 2)

    def test_over_reduction_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_reduced_carrier_equivalent_power_test(FOUR_AT_25W, 4)


class TestCategorizationAndSummary(unittest.TestCase):
    def test_categorize_rejects_non_report(self):
        with self.assertRaises(ValueError):
            logic.categorize_reduction({"codes": []})

    def test_summary_mentions_verdict(self):
        report = logic.assess_reduced_carrier_equivalent_power_test(EIGHT_AT_20W, 4)
        self.assertIn(
            "verdict: reduced-carrier-equivalent-drive-acceptable",
            logic.summarize_report(report),
        )

    def test_summary_lists_findings(self):
        report = logic.assess_reduced_carrier_equivalent_power_test(
            EIGHT_AT_20W, 3, reduced_spacing_hz=400.0e6
        )
        self.assertIn(
            "finding: reduced-dwell-less-severe-than-operational",
            logic.summarize_report(report),
        )

    def test_summary_rejects_non_report(self):
        with self.assertRaises(ValueError):
            logic.summarize_report({"findings": []})


if __name__ == "__main__":
    unittest.main()
