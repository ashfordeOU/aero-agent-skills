"""Contract tests for the clause 5.3.1 in-band frequency-selection logic."""

import math
import unittest

from e2001_analysis_frequency_selection_logic import (
    MARGIN_TOLERANCE_DB,
    assess_frequency_selection,
    breakdown_power_w,
    candidate_frequencies,
    evaluate_candidate,
    frequency_gap_product,
    interpolate_linear,
    interpolate_log_log,
    margin_db,
    select_worst_case,
    sweep_band,
    threshold_voltage,
    validate_band,
)

# Representative silver-surface susceptibility shape: threshold voltage rises
# with the frequency-gap product away from the low-fd minimum.
CURVE = [
    (0.5, 60.0),
    (1.0, 100.0),
    (2.0, 200.0),
    (4.0, 480.0),
    (10.0, 1600.0),
    (40.0, 9000.0),
]

FLAT_Z = [(1.0, 50.0), (20.0, 50.0)]


class ValidateBandTests(unittest.TestCase):
    def test_returns_float_pair(self):
        self.assertEqual(validate_band(4, 8), (4.0, 8.0))

    def test_equal_edges_allowed_for_single_frequency_component(self):
        self.assertEqual(validate_band(11.7, 11.7), (11.7, 11.7))

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band(12.0, 4.0)

    def test_zero_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_band(0.0, 4.0)

    def test_negative_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_band(4.0, -1.0)

    def test_non_numeric_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_band("4", 8.0)

    def test_non_finite_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_band(4.0, float("inf"))


class FrequencyGapProductTests(unittest.TestCase):
    def test_product_in_ghz_mm(self):
        self.assertAlmostEqual(frequency_gap_product(12.0, 0.5), 6.0)

    def test_small_gap_lowers_the_product(self):
        self.assertAlmostEqual(frequency_gap_product(30.0, 0.05), 1.5)

    def test_zero_gap_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product(12.0, 0.0)

    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product(-12.0, 0.5)

    def test_boolean_gap_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product(12.0, True)


class InterpolationTests(unittest.TestCase):
    def test_log_log_hits_tabulated_point(self):
        self.assertAlmostEqual(interpolate_log_log(CURVE, 2.0), 200.0)

    def test_log_log_midpoint_is_geometric(self):
        value = interpolate_log_log([(1.0, 100.0), (4.0, 400.0)], 2.0)
        self.assertAlmostEqual(value, 200.0)

    def test_log_log_lower_edge(self):
        self.assertAlmostEqual(interpolate_log_log(CURVE, 0.5), 60.0)

    def test_log_log_upper_edge(self):
        self.assertAlmostEqual(interpolate_log_log(CURVE, 40.0), 9000.0)

    def test_log_log_below_range_refused(self):
        with self.assertRaises(ValueError):
            interpolate_log_log(CURVE, 0.1)

    def test_log_log_above_range_refused(self):
        with self.assertRaises(ValueError):
            interpolate_log_log(CURVE, 400.0)

    def test_single_point_table_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_log_log([(1.0, 100.0)], 1.0)

    def test_non_monotone_table_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_log_log([(1.0, 100.0), (1.0, 200.0)], 1.0)

    def test_malformed_point_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_log_log([(1.0, 100.0), (2.0,)], 1.5)

    def test_non_positive_ordinate_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_log_log([(1.0, 0.0), (2.0, 200.0)], 1.5)

    def test_linear_midpoint(self):
        self.assertAlmostEqual(interpolate_linear([(1.0, 50.0), (3.0, 70.0)], 2.0), 60.0)

    def test_linear_outside_range_refused(self):
        with self.assertRaises(ValueError):
            interpolate_linear(FLAT_Z, 25.0)

    def test_abscissa_must_be_positive(self):
        with self.assertRaises(ValueError):
            interpolate_linear(FLAT_Z, -3.0)


class ThresholdAndPowerTests(unittest.TestCase):
    def test_threshold_voltage_uses_the_curve(self):
        self.assertAlmostEqual(threshold_voltage(CURVE, 4.0), 480.0)

    def test_breakdown_power_matches_closed_form(self):
        self.assertAlmostEqual(breakdown_power_w(200.0, 50.0), 400.0)

    def test_magnification_reduces_breakdown_power(self):
        plain = breakdown_power_w(200.0, 50.0, 1.0)
        magnified = breakdown_power_w(200.0, 50.0, 2.0)
        self.assertAlmostEqual(magnified, plain / 4.0)

    def test_zero_impedance_rejected(self):
        with self.assertRaises(ValueError):
            breakdown_power_w(200.0, 0.0)

    def test_negative_magnification_rejected(self):
        with self.assertRaises(ValueError):
            breakdown_power_w(200.0, 50.0, -1.0)


class CandidateFrequencyTests(unittest.TestCase):
    def test_sweep_includes_both_edges(self):
        values = candidate_frequencies(4.0, 8.0, 5)
        self.assertAlmostEqual(values[0], 4.0)
        self.assertAlmostEqual(values[-1], 8.0)

    def test_sweep_point_count(self):
        self.assertEqual(len(candidate_frequencies(4.0, 8.0, 5)), 5)

    def test_singular_frequency_is_inserted_in_order(self):
        values = candidate_frequencies(4.0, 8.0, 3, [6.5])
        self.assertEqual(len(values), 4)
        self.assertAlmostEqual(values[2], 6.5)

    def test_duplicate_singular_frequency_is_collapsed(self):
        values = candidate_frequencies(4.0, 8.0, 3, [6.0])
        self.assertEqual(len(values), 3)

    def test_degenerate_band_gives_one_candidate(self):
        self.assertEqual(candidate_frequencies(11.7, 11.7, 5), [11.7])

    def test_too_few_sweep_points_rejected(self):
        with self.assertRaises(ValueError):
            candidate_frequencies(4.0, 8.0, 2)

    def test_out_of_band_singular_frequency_rejected(self):
        with self.assertRaises(ValueError):
            candidate_frequencies(4.0, 8.0, 3, [9.0])

    def test_non_integer_sweep_points_rejected(self):
        with self.assertRaises(ValueError):
            candidate_frequencies(4.0, 8.0, 4.5)


class SweepAndSelectionTests(unittest.TestCase):
    def test_sweep_returns_one_record_per_candidate(self):
        records = sweep_band((4.0, 8.0), 0.5, CURVE, FLAT_Z, sweep_points=5)
        self.assertEqual(len(records), 5)

    def test_lowest_frequency_is_worst_case_on_a_rising_curve(self):
        records = sweep_band((4.0, 8.0), 0.5, CURVE, FLAT_Z, sweep_points=5)
        worst = select_worst_case(records)
        self.assertAlmostEqual(worst["frequency_ghz"], 4.0)

    def test_in_band_magnification_peak_moves_the_worst_case(self):
        magnification = [(4.0, 1.0), (6.0, 3.0), (8.0, 1.0)]
        records = sweep_band(
            (4.0, 8.0), 0.5, CURVE, FLAT_Z, magnification, sweep_points=3
        )
        worst = select_worst_case(records)
        self.assertAlmostEqual(worst["frequency_ghz"], 6.0)

    def test_record_carries_the_frequency_gap_product(self):
        record = evaluate_candidate(8.0, 0.25, CURVE, FLAT_Z)
        self.assertAlmostEqual(record["fd_ghz_mm"], 2.0)
        self.assertAlmostEqual(record["threshold_voltage_v"], 200.0)

    def test_tie_is_broken_by_the_lower_frequency(self):
        records = [
            {"frequency_ghz": 9.0, "breakdown_power_w": 100.0},
            {"frequency_ghz": 5.0, "breakdown_power_w": 100.0},
        ]
        self.assertAlmostEqual(select_worst_case(records)["frequency_ghz"], 5.0)

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            select_worst_case([])

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            select_worst_case([{"frequency_ghz": 5.0}])

    def test_gap_outside_the_tabulated_product_range_is_refused(self):
        with self.assertRaises(ValueError):
            sweep_band((4.0, 8.0), 0.01, CURVE, FLAT_Z, sweep_points=3)


class MarginTests(unittest.TestCase):
    def test_factor_of_four_is_about_six_db(self):
        self.assertAlmostEqual(margin_db(400.0, 100.0), 6.020599913, places=6)

    def test_equal_powers_give_zero_db(self):
        self.assertAlmostEqual(margin_db(100.0, 100.0), 0.0)

    def test_zero_operating_power_rejected(self):
        with self.assertRaises(ValueError):
            margin_db(400.0, 0.0)

    def test_negative_breakdown_power_rejected(self):
        with self.assertRaises(ValueError):
            margin_db(-400.0, 100.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "band": (4.0, 8.0),
            "gap_mm": 0.5,
            "susceptibility_curve": CURVE,
            "impedance_table": FLAT_Z,
            "sweep_points": 5,
            "operating_power_w": 100.0,
            "required_margin_db": 6.0,
        }
        spec.update(overrides)
        return spec

    def test_compliant_case_reports_no_findings(self):
        result = assess_frequency_selection(self._spec(operating_power_w=100.0))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_worst_case_record_is_reported(self):
        result = assess_frequency_selection(self._spec())
        self.assertAlmostEqual(result["worst_case"]["frequency_ghz"], 4.0)

    def test_underpowered_margin_is_flagged(self):
        result = assess_frequency_selection(self._spec(operating_power_w=4000.0))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_exact_boundary_margin_is_compliant(self):
        spec = self._spec(required_margin_db=0.0, operating_power_w=None)
        records = sweep_band((4.0, 8.0), 0.5, CURVE, FLAT_Z, sweep_points=5)
        worst = select_worst_case(records)
        spec["operating_power_w"] = worst["breakdown_power_w"]
        result = assess_frequency_selection(spec)
        self.assertTrue(result["compliant"])
        self.assertLessEqual(abs(result["achieved_margin_db"]), MARGIN_TOLERANCE_DB)

    def test_degenerate_band_is_flagged_as_edge_only(self):
        result = assess_frequency_selection(self._spec(band=(6.0, 6.0)))
        self.assertFalse(result["compliant"])
        self.assertIn("edges only", result["findings"][-1])

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["gap_mm"]
        with self.assertRaises(ValueError):
            assess_frequency_selection(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_frequency_selection(["band"])

    def test_malformed_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_frequency_selection(self._spec(band=(4.0,)))

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            assess_frequency_selection(self._spec(required_margin_db=-3.0))

    def test_margin_scales_with_operating_power(self):
        high = assess_frequency_selection(self._spec(operating_power_w=100.0))
        low = assess_frequency_selection(self._spec(operating_power_w=200.0))
        self.assertAlmostEqual(
            high["achieved_margin_db"] - low["achieved_margin_db"],
            10.0 * math.log10(2.0),
            places=9,
        )


if __name__ == "__main__":
    unittest.main()
