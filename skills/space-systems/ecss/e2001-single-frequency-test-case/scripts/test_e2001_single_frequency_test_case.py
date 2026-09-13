#!/usr/bin/env python3
"""Contract test for the ECSS-E-ST-20-01C clause 6.4.2 frequency-selection leaf."""

import math
import unittest

from e2001_single_frequency_test_case_logic import (
    DEFAULT_DRIFT_FRACTION,
    SUSCEPTIBILITY_MAP_HIGH_GHZ_MM,
    SUSCEPTIBILITY_MAP_LOW_GHZ_MM,
    categorize_field_response,
    critical_gap,
    drift_window_hz,
    frequency_gap_product_ghz_mm,
    frequency_selection_record,
    peak_magnification_frequency,
    select_test_frequency,
    single_frequency_sufficiency,
    summarize_selection,
    susceptibility_map_findings,
    validate_operating_band,
)

GAPS = [
    {"identifier": "iris-1", "gap_m": 1.2e-3},
    {"identifier": "iris-2", "gap_m": 0.8e-3},
]

RESONANT_SPEC = {
    "component_type": "cavity-filter",
    "f_low_hz": 11.7e9,
    "f_high_hz": 12.2e9,
    "gaps": GAPS,
    "response_map": [
        {"frequency_hz": 11.75e9, "voltage_magnification": 3.1},
        {"frequency_hz": 11.95e9, "voltage_magnification": 6.4},
        {"frequency_hz": 12.15e9, "voltage_magnification": 2.7},
    ],
    "drift_fraction": 0.002,
}

NON_RESONANT_SPEC = {
    "component_type": "waveguide-run",
    "f_low_hz": 11.7e9,
    "f_high_hz": 12.2e9,
    "gaps": GAPS,
    "drift_fraction": 0.002,
}


class TestBandValidation(unittest.TestCase):
    def test_valid_band_returns_float_pair(self):
        low, high = validate_operating_band(11.7e9, 12.2e9)
        self.assertAlmostEqual(low, 11.7e9)
        self.assertAlmostEqual(high, 12.2e9)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_band(12.2e9, 11.7e9)

    def test_zero_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_band(0.0, 12.2e9)

    def test_string_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_band("11.7e9", 12.2e9)

    def test_nan_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_band(float("nan"), 12.2e9)


class TestFieldResponseCategorization(unittest.TestCase):
    def test_cavity_filter_is_resonant(self):
        self.assertEqual(categorize_field_response("cavity-filter"), "resonant-field")

    def test_output_multiplexer_is_resonant(self):
        self.assertEqual(
            categorize_field_response("output-multiplexer"), "resonant-field"
        )

    def test_waveguide_run_is_non_resonant(self):
        self.assertEqual(
            categorize_field_response("waveguide-run"), "non-resonant-field"
        )

    def test_connector_is_non_resonant(self):
        self.assertEqual(categorize_field_response("connector"), "non-resonant-field")

    def test_lookup_is_case_and_space_insensitive(self):
        self.assertEqual(
            categorize_field_response("  Coaxial-Line "), "non-resonant-field"
        )

    def test_unknown_type_rejected(self):
        with self.assertRaises(ValueError):
            categorize_field_response("travelling-wave-tube")

    def test_non_string_type_rejected(self):
        with self.assertRaises(ValueError):
            categorize_field_response(None)


class TestCriticalGap(unittest.TestCase):
    def test_smallest_gap_is_selected(self):
        self.assertEqual(critical_gap(GAPS)["identifier"], "iris-2")

    def test_selected_gap_value_is_returned(self):
        self.assertAlmostEqual(critical_gap(GAPS)["gap_m"], 0.8e-3)

    def test_tie_is_broken_deterministically_by_identifier(self):
        tied = [
            {"identifier": "b-gap", "gap_m": 1.0e-3},
            {"identifier": "a-gap", "gap_m": 1.0e-3},
        ]
        self.assertEqual(critical_gap(tied)["identifier"], "a-gap")

    def test_empty_gap_list_rejected(self):
        with self.assertRaises(ValueError):
            critical_gap([])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            critical_gap({"identifier": "iris-1", "gap_m": 1.0e-3})

    def test_entry_without_identifier_rejected(self):
        with self.assertRaises(ValueError):
            critical_gap([{"gap_m": 1.0e-3}])

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            critical_gap([{"identifier": "   ", "gap_m": 1.0e-3}])

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            critical_gap(
                [
                    {"identifier": "iris-1", "gap_m": 1.0e-3},
                    {"identifier": "iris-1", "gap_m": 2.0e-3},
                ]
            )

    def test_negative_gap_rejected(self):
        with self.assertRaises(ValueError):
            critical_gap([{"identifier": "iris-1", "gap_m": -1.0e-3}])

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            critical_gap(["iris-1"])


class TestFrequencyGapProduct(unittest.TestCase):
    def test_product_is_expressed_in_ghz_millimetre(self):
        self.assertAlmostEqual(frequency_gap_product_ghz_mm(4.0e9, 1.0e-3), 4.0)

    def test_product_scales_with_frequency(self):
        self.assertAlmostEqual(frequency_gap_product_ghz_mm(8.0e9, 1.0e-3), 8.0)

    def test_product_scales_with_gap(self):
        self.assertAlmostEqual(frequency_gap_product_ghz_mm(4.0e9, 2.0e-3), 8.0)

    def test_zero_gap_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product_ghz_mm(4.0e9, 0.0)

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product_ghz_mm(0.0, 1.0e-3)


class TestSusceptibilityMapSpan(unittest.TestCase):
    def test_in_span_product_reports_nothing(self):
        self.assertEqual(susceptibility_map_findings(4.0), [])

    def test_product_below_span_is_reported(self):
        findings = susceptibility_map_findings(0.01)
        self.assertEqual(len(findings), 1)
        self.assertIn("below", findings[0])

    def test_product_above_span_is_reported(self):
        findings = susceptibility_map_findings(300.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("above", findings[0])

    def test_exact_low_span_edge_is_accepted(self):
        product = frequency_gap_product_ghz_mm(1.0e8, 1.0e-3)
        self.assertAlmostEqual(product, SUSCEPTIBILITY_MAP_LOW_GHZ_MM)
        self.assertEqual(susceptibility_map_findings(product), [])

    def test_exact_high_span_edge_is_accepted(self):
        product = frequency_gap_product_ghz_mm(1.0e11, 1.0e-3)
        self.assertAlmostEqual(product, SUSCEPTIBILITY_MAP_HIGH_GHZ_MM)
        self.assertEqual(susceptibility_map_findings(product), [])

    def test_inverted_span_rejected(self):
        with self.assertRaises(ValueError):
            susceptibility_map_findings(4.0, map_low_ghz_mm=10.0, map_high_ghz_mm=1.0)

    def test_zero_product_rejected(self):
        with self.assertRaises(ValueError):
            susceptibility_map_findings(0.0)


class TestPeakMagnificationFrequency(unittest.TestCase):
    def test_largest_magnification_wins(self):
        peak = peak_magnification_frequency(
            RESONANT_SPEC["response_map"], 11.7e9, 12.2e9
        )
        self.assertAlmostEqual(peak["frequency_hz"], 11.95e9)

    def test_magnification_value_is_returned(self):
        peak = peak_magnification_frequency(
            RESONANT_SPEC["response_map"], 11.7e9, 12.2e9
        )
        self.assertAlmostEqual(peak["voltage_magnification"], 6.4)

    def test_tie_is_broken_toward_the_lower_frequency(self):
        tied = [
            {"frequency_hz": 12.1e9, "voltage_magnification": 5.0},
            {"frequency_hz": 11.8e9, "voltage_magnification": 5.0},
        ]
        peak = peak_magnification_frequency(tied, 11.7e9, 12.2e9)
        self.assertAlmostEqual(peak["frequency_hz"], 11.8e9)

    def test_entry_exactly_on_the_band_edge_is_accepted(self):
        edge = [{"frequency_hz": 11.7e9, "voltage_magnification": 4.0}]
        peak = peak_magnification_frequency(edge, 11.7e9, 12.2e9)
        self.assertAlmostEqual(peak["frequency_hz"], 11.7e9)

    def test_entry_outside_the_band_rejected(self):
        with self.assertRaises(ValueError):
            peak_magnification_frequency(
                [{"frequency_hz": 13.0e9, "voltage_magnification": 4.0}],
                11.7e9,
                12.2e9,
            )

    def test_empty_map_rejected(self):
        with self.assertRaises(ValueError):
            peak_magnification_frequency([], 11.7e9, 12.2e9)

    def test_non_positive_magnification_rejected(self):
        with self.assertRaises(ValueError):
            peak_magnification_frequency(
                [{"frequency_hz": 11.8e9, "voltage_magnification": 0.0}],
                11.7e9,
                12.2e9,
            )

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            peak_magnification_frequency(["11.8e9"], 11.7e9, 12.2e9)


class TestDriftWindow(unittest.TestCase):
    def test_window_straddles_the_point(self):
        low, high = drift_window_hz(12.0e9, 0.01)
        self.assertAlmostEqual(low, 11.88e9)
        self.assertAlmostEqual(high, 12.12e9)

    def test_zero_drift_collapses_the_window(self):
        low, high = drift_window_hz(12.0e9, 0.0)
        self.assertAlmostEqual(low, high)

    def test_default_drift_is_small_and_positive(self):
        self.assertGreater(DEFAULT_DRIFT_FRACTION, 0.0)
        self.assertLess(DEFAULT_DRIFT_FRACTION, 0.1)

    def test_drift_of_one_rejected(self):
        with self.assertRaises(ValueError):
            drift_window_hz(12.0e9, 1.0)

    def test_negative_drift_rejected(self):
        with self.assertRaises(ValueError):
            drift_window_hz(12.0e9, -0.01)


class TestSelectTestFrequency(unittest.TestCase):
    def test_non_resonant_selection_sits_at_the_drifted_low_edge(self):
        selection = select_test_frequency(NON_RESONANT_SPEC)
        self.assertAlmostEqual(selection["frequency_hz"], 11.7e9 * (1.0 - 0.002))

    def test_non_resonant_basis_is_the_gap_product(self):
        self.assertEqual(
            select_test_frequency(NON_RESONANT_SPEC)["basis"],
            "lowest-frequency-gap-product",
        )

    def test_non_resonant_selection_reports_no_magnification(self):
        self.assertIsNone(select_test_frequency(NON_RESONANT_SPEC)["voltage_magnification"])

    def test_resonant_selection_sits_on_the_magnification_peak(self):
        selection = select_test_frequency(RESONANT_SPEC)
        self.assertAlmostEqual(selection["frequency_hz"], 11.95e9)

    def test_resonant_basis_is_the_magnification_peak(self):
        self.assertEqual(
            select_test_frequency(RESONANT_SPEC)["basis"], "peak-voltage-magnification"
        )

    def test_selection_carries_the_critical_gap(self):
        self.assertEqual(
            select_test_frequency(RESONANT_SPEC)["critical_gap"]["identifier"], "iris-2"
        )

    def test_selection_reports_the_frequency_gap_product(self):
        selection = select_test_frequency(RESONANT_SPEC)
        self.assertAlmostEqual(
            selection["frequency_gap_product_ghz_mm"], 11.95e9 * 0.8e-3 / 1.0e6
        )

    def test_clean_resonant_case_has_no_findings(self):
        self.assertEqual(select_test_frequency(RESONANT_SPEC)["findings"], [])

    def test_drift_reaching_below_the_band_is_reported(self):
        spec = dict(RESONANT_SPEC)
        spec["response_map"] = [
            {"frequency_hz": 11.7e9, "voltage_magnification": 6.4}
        ]
        spec["drift_fraction"] = 0.01
        findings = select_test_frequency(spec)["findings"]
        self.assertTrue(any("below the declared band edge" in f for f in findings))

    def test_drift_reaching_above_the_band_is_reported(self):
        spec = dict(RESONANT_SPEC)
        spec["response_map"] = [
            {"frequency_hz": 12.2e9, "voltage_magnification": 6.4}
        ]
        spec["drift_fraction"] = 0.01
        findings = select_test_frequency(spec)["findings"]
        self.assertTrue(any("above the declared band edge" in f for f in findings))

    def test_zero_drift_keeps_a_band_edge_peak_inside(self):
        spec = dict(RESONANT_SPEC)
        spec["response_map"] = [
            {"frequency_hz": 12.2e9, "voltage_magnification": 6.4}
        ]
        spec["drift_fraction"] = 0.0
        self.assertEqual(select_test_frequency(spec)["findings"], [])

    def test_unused_response_map_on_non_resonant_hardware_is_reported(self):
        spec = dict(NON_RESONANT_SPEC)
        spec["response_map"] = [
            {"frequency_hz": 11.9e9, "voltage_magnification": 2.0}
        ]
        findings = select_test_frequency(spec)["findings"]
        self.assertTrue(any("not used" in f for f in findings))

    def test_out_of_chart_gap_product_is_reported(self):
        spec = dict(NON_RESONANT_SPEC)
        spec["gaps"] = [{"identifier": "micro-gap", "gap_m": 1.0e-9}]
        findings = select_test_frequency(spec)["findings"]
        self.assertTrue(any("below the validated chart span" in f for f in findings))

    def test_resonant_hardware_without_a_response_map_rejected(self):
        spec = dict(RESONANT_SPEC)
        spec.pop("response_map")
        with self.assertRaises(ValueError):
            select_test_frequency(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            select_test_frequency("cavity-filter")

    def test_missing_gaps_rejected(self):
        spec = dict(NON_RESONANT_SPEC)
        spec.pop("gaps")
        with self.assertRaises(ValueError):
            select_test_frequency(spec)

    def test_invalid_drift_rejected(self):
        spec = dict(NON_RESONANT_SPEC)
        spec["drift_fraction"] = 1.5
        with self.assertRaises(ValueError):
            select_test_frequency(spec)


class TestSingleFrequencySufficiency(unittest.TestCase):
    def test_wide_coverage_is_sufficient(self):
        result = single_frequency_sufficiency(12.0e9, 11.7e9, 12.2e9, 0.9, 1.1)
        self.assertTrue(result["sufficient"])

    def test_low_edge_shortfall_is_reported(self):
        result = single_frequency_sufficiency(12.0e9, 11.7e9, 12.2e9, 0.999, 1.1)
        self.assertFalse(result["sufficient"])
        self.assertTrue(any("low band edge" in f for f in result["findings"]))

    def test_high_edge_shortfall_is_reported(self):
        result = single_frequency_sufficiency(12.0e9, 11.7e9, 12.2e9, 0.9, 1.001)
        self.assertFalse(result["sufficient"])
        self.assertTrue(any("high band edge" in f for f in result["findings"]))

    def test_exact_edge_coverage_is_sufficient(self):
        selected = 12.0e9
        ratio_low = 11.7e9 / selected
        ratio_high = 12.2e9 / selected
        result = single_frequency_sufficiency(
            selected, 11.7e9, 12.2e9, ratio_low, ratio_high
        )
        self.assertTrue(result["sufficient"])

    def test_covered_edges_are_reported(self):
        result = single_frequency_sufficiency(12.0e9, 11.7e9, 12.2e9, 0.9, 1.1)
        self.assertAlmostEqual(result["covered_low_hz"], 10.8e9, delta=1.0)
        self.assertAlmostEqual(result["covered_high_hz"], 13.2e9, delta=1.0)

    def test_inverted_ratios_rejected(self):
        with self.assertRaises(ValueError):
            single_frequency_sufficiency(12.0e9, 11.7e9, 12.2e9, 1.1, 0.9)

    def test_zero_ratio_rejected(self):
        with self.assertRaises(ValueError):
            single_frequency_sufficiency(12.0e9, 11.7e9, 12.2e9, 0.0, 1.1)


class TestSelectionRecord(unittest.TestCase):
    def test_clean_record_is_valid(self):
        record = frequency_selection_record(RESONANT_SPEC)
        self.assertTrue(record["single_frequency_test_case_valid"])

    def test_record_without_ratios_has_no_sufficiency_block(self):
        self.assertIsNone(frequency_selection_record(RESONANT_SPEC)["sufficiency"])

    def test_record_with_ratios_carries_sufficiency(self):
        record = frequency_selection_record(RESONANT_SPEC, 0.9, 1.1)
        self.assertTrue(record["sufficiency"]["sufficient"])

    def test_insufficient_coverage_invalidates_the_record(self):
        record = frequency_selection_record(RESONANT_SPEC, 0.9999, 1.0001)
        self.assertFalse(record["single_frequency_test_case_valid"])

    def test_one_ratio_alone_rejected(self):
        with self.assertRaises(ValueError):
            frequency_selection_record(RESONANT_SPEC, 0.9)

    def test_findings_accumulate_from_both_stages(self):
        spec = dict(NON_RESONANT_SPEC)
        spec["gaps"] = [{"identifier": "micro-gap", "gap_m": 1.0e-9}]
        record = frequency_selection_record(spec, 0.9999, 1.0001)
        self.assertGreaterEqual(len(record["findings"]), 2)


class TestSummary(unittest.TestCase):
    def test_summary_reports_a_valid_verdict(self):
        lines = summarize_selection(frequency_selection_record(RESONANT_SPEC))
        self.assertTrue(any("verdict: single-frequency test case valid" in l for l in lines))

    def test_summary_lists_every_finding(self):
        spec = dict(NON_RESONANT_SPEC)
        spec["gaps"] = [{"identifier": "micro-gap", "gap_m": 1.0e-9}]
        record = frequency_selection_record(spec)
        lines = summarize_selection(record)
        emitted = [line for line in lines if line.startswith("finding: ")]
        self.assertEqual(len(emitted), len(record["findings"]))

    def test_summary_rejects_a_foreign_mapping(self):
        with self.assertRaises(ValueError):
            summarize_selection({"selection_only": True})


class TestDeterminism(unittest.TestCase):
    def test_repeated_selection_is_bit_identical(self):
        first = select_test_frequency(RESONANT_SPEC)
        second = select_test_frequency(RESONANT_SPEC)
        self.assertEqual(first["frequency_hz"], second["frequency_hz"])

    def test_gap_product_and_selection_are_consistent(self):
        selection = select_test_frequency(NON_RESONANT_SPEC)
        expected = frequency_gap_product_ghz_mm(
            selection["frequency_hz"], selection["critical_gap"]["gap_m"]
        )
        self.assertTrue(
            math.isclose(
                selection["frequency_gap_product_ghz_mm"], expected, rel_tol=1e-12
            )
        )


if __name__ == "__main__":
    unittest.main()
