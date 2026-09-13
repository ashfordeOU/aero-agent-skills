"""Contract tests for the clause 5.3.2.2.1 first-analysis-level logic."""

import math
import unittest

from e2001_analysis_level_one_requirements_logic import (
    CANONICAL_GEOMETRIES,
    CHARTED_MATERIALS,
    DEFAULT_MAX_FIELD_RATIO,
    LEVEL_ONE_CRITERIA,
    LEVEL_ONE_EVIDENCE,
    MARGIN_TOLERANCE_DB,
    assess_level_one,
    chart_span,
    charted_threshold_v,
    evaluate_criteria,
    field_homogeneous,
    gap_extremes_mm,
    level_one_margin_db,
    missing_evidence,
    normalize_geometry,
    normalize_material,
    select_analysis_level,
    worst_case_gap_product,
)

# Rising branch: threshold grows with the frequency-gap product.
CHART = [(0.5, 60.0), (1.0, 100.0), (2.0, 200.0), (4.0, 480.0), (10.0, 1600.0), (40.0, 9000.0)]

# Charted shape with an interior minimum, so the larger gap can be the worse one.
U_CHART = [(0.5, 300.0), (1.0, 150.0), (2.0, 100.0), (4.0, 200.0), (10.0, 900.0)]

# Symmetric shape used for the deterministic tie-break.
TIE_CHART = [(1.0, 150.0), (2.0, 100.0), (4.0, 150.0)]


def spec(**overrides):
    base = {
        "geometry": "parallel-plate",
        "surface_material": "silver",
        "peak_field": 1.0,
        "mean_field": 1.0,
        "dielectric_in_gap": False,
        "propagating_modes": 1,
        "chart": CHART,
        "frequency_ghz": 12.0,
        "nominal_gap_mm": 0.15,
        "minus_tolerance_mm": 0.05,
        "plus_tolerance_mm": 0.05,
        "impedance_ohm": 50.0,
        "operating_power_w": 1.0,
        "required_margin_db": 6.0,
        "declared_evidence": list(LEVEL_ONE_EVIDENCE),
    }
    base.update(overrides)
    return base


class NormalisationTests(unittest.TestCase):
    def test_geometry_case_folded(self):
        self.assertEqual(normalize_geometry(" Parallel-Plate "), "parallel-plate")

    def test_material_case_folded(self):
        self.assertEqual(normalize_material("Silver"), "silver")

    def test_empty_geometry_rejected(self):
        with self.assertRaises(ValueError):
            normalize_geometry("  ")

    def test_non_string_material_rejected(self):
        with self.assertRaises(ValueError):
            normalize_material(42)

    def test_canonical_sets_are_non_empty(self):
        self.assertIn("coaxial-line", CANONICAL_GEOMETRIES)
        self.assertIn("alodine-treated-aluminium", CHARTED_MATERIALS)


class GapStackTests(unittest.TestCase):
    def test_extremes_from_the_stack(self):
        low, high = gap_extremes_mm(0.15, 0.05, 0.05)
        self.assertAlmostEqual(low, 0.10)
        self.assertAlmostEqual(high, 0.20)

    def test_asymmetric_tolerance(self):
        low, high = gap_extremes_mm(1.0, 0.1, 0.3)
        self.assertAlmostEqual(low, 0.9)
        self.assertAlmostEqual(high, 1.3)

    def test_zero_tolerance_collapses_to_nominal(self):
        self.assertEqual(gap_extremes_mm(2.0, 0.0, 0.0), (2.0, 2.0))

    def test_tolerance_closing_the_gap_rejected(self):
        with self.assertRaises(ValueError):
            gap_extremes_mm(0.1, 0.1, 0.05)

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            gap_extremes_mm(1.0, -0.1, 0.1)

    def test_non_positive_nominal_rejected(self):
        with self.assertRaises(ValueError):
            gap_extremes_mm(0.0, 0.0, 0.0)


class FieldHomogeneityTests(unittest.TestCase):
    def test_uniform_field_passes(self):
        self.assertTrue(field_homogeneous(1.0, 1.0))

    def test_mild_non_uniformity_passes(self):
        self.assertTrue(field_homogeneous(1.05, 1.0))

    def test_strong_non_uniformity_fails(self):
        self.assertFalse(field_homogeneous(1.5, 1.0))

    def test_exact_limit_ratio_passes(self):
        self.assertTrue(field_homogeneous(DEFAULT_MAX_FIELD_RATIO, 1.0))

    def test_representation_error_at_the_limit_is_absorbed(self):
        just_over = math.nextafter(DEFAULT_MAX_FIELD_RATIO, 2.0)
        self.assertGreater(just_over, DEFAULT_MAX_FIELD_RATIO)
        self.assertTrue(field_homogeneous(just_over, 1.0))

    def test_limit_is_not_widened(self):
        self.assertFalse(field_homogeneous(DEFAULT_MAX_FIELD_RATIO * 1.001, 1.0))

    def test_custom_limit_honoured(self):
        self.assertTrue(field_homogeneous(1.4, 1.0, 1.5))

    def test_peak_below_mean_rejected(self):
        with self.assertRaises(ValueError):
            field_homogeneous(0.9, 1.0)

    def test_zero_mean_field_rejected(self):
        with self.assertRaises(ValueError):
            field_homogeneous(1.0, 0.0)


class ChartTests(unittest.TestCase):
    def test_span_is_the_tabulated_range(self):
        self.assertEqual(chart_span(CHART), (0.5, 40.0))

    def test_threshold_at_a_tabulated_point(self):
        self.assertAlmostEqual(charted_threshold_v(CHART, 2.0), 200.0)

    def test_threshold_interpolated_on_a_unit_slope_segment(self):
        self.assertAlmostEqual(charted_threshold_v(CHART, 1.2), 120.0)

    def test_threshold_at_the_upper_edge(self):
        self.assertAlmostEqual(charted_threshold_v(CHART, 40.0), 9000.0)

    def test_below_span_refused(self):
        with self.assertRaises(ValueError):
            charted_threshold_v(CHART, 0.2)

    def test_above_span_refused(self):
        with self.assertRaises(ValueError):
            charted_threshold_v(CHART, 60.0)

    def test_short_chart_rejected(self):
        with self.assertRaises(ValueError):
            chart_span([(1.0, 100.0)])

    def test_non_monotone_chart_rejected(self):
        with self.assertRaises(ValueError):
            chart_span([(2.0, 100.0), (1.0, 200.0)])

    def test_malformed_chart_entry_rejected(self):
        with self.assertRaises(ValueError):
            chart_span([(1.0, 100.0), (2.0, 200.0, 3.0)])

    def test_non_positive_threshold_rejected(self):
        with self.assertRaises(ValueError):
            chart_span([(1.0, -100.0), (2.0, 200.0)])


class WorstCaseGapTests(unittest.TestCase):
    def test_rising_chart_makes_the_smallest_gap_worst(self):
        worst = worst_case_gap_product(12.0, 0.10, 0.20, CHART)
        self.assertAlmostEqual(worst["gap_mm"], 0.10)
        self.assertAlmostEqual(worst["fd_ghz_mm"], 1.2)
        self.assertAlmostEqual(worst["threshold_voltage_v"], 120.0)

    def test_interior_minimum_can_make_the_largest_gap_worst(self):
        worst = worst_case_gap_product(1.0, 0.5, 2.0, U_CHART)
        self.assertAlmostEqual(worst["gap_mm"], 2.0)
        self.assertAlmostEqual(worst["threshold_voltage_v"], 100.0)

    def test_tie_is_broken_by_the_smaller_gap(self):
        worst = worst_case_gap_product(1.0, 1.0, 4.0, TIE_CHART)
        self.assertAlmostEqual(worst["gap_mm"], 1.0)

    def test_inverted_gap_range_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_gap_product(12.0, 0.30, 0.10, CHART)

    def test_gap_leaving_the_charted_span_refused(self):
        with self.assertRaises(ValueError):
            worst_case_gap_product(12.0, 0.001, 0.20, CHART)


class CriteriaTests(unittest.TestCase):
    def _inputs(self, **overrides):
        base = {
            "geometry": "parallel-plate",
            "surface_material": "silver",
            "peak_field": 1.0,
            "mean_field": 1.0,
            "dielectric_in_gap": False,
            "propagating_modes": 1,
            "worst_case_fd_ghz_mm": 1.2,
            "chart": CHART,
        }
        base.update(overrides)
        return base

    def test_all_criteria_met(self):
        verdicts = evaluate_criteria(self._inputs())
        self.assertTrue(all(verdicts[name] for name in LEVEL_ONE_CRITERIA))

    def test_arbitrary_geometry_fails_its_criterion(self):
        verdicts = evaluate_criteria(self._inputs(geometry="arbitrary-three-dimensional"))
        self.assertFalse(verdicts["canonical-geometry"])

    def test_uncharted_material_fails_its_criterion(self):
        verdicts = evaluate_criteria(self._inputs(surface_material="titanium"))
        self.assertFalse(verdicts["charted-surface-material"])

    def test_dielectric_in_gap_fails_its_criterion(self):
        verdicts = evaluate_criteria(self._inputs(dielectric_in_gap=True))
        self.assertFalse(verdicts["no-dielectric-in-gap"])

    def test_multimode_region_fails_its_criterion(self):
        verdicts = evaluate_criteria(self._inputs(propagating_modes=3))
        self.assertFalse(verdicts["single-dominant-mode"])

    def test_product_outside_the_chart_fails_its_criterion(self):
        verdicts = evaluate_criteria(self._inputs(worst_case_fd_ghz_mm=45.0))
        self.assertFalse(verdicts["charted-frequency-gap-product"])

    def test_non_uniform_field_fails_its_criterion(self):
        verdicts = evaluate_criteria(self._inputs(peak_field=2.0))
        self.assertFalse(verdicts["homogeneous-gap-field"])

    def test_missing_input_rejected(self):
        bad = self._inputs()
        del bad["chart"]
        with self.assertRaises(ValueError):
            evaluate_criteria(bad)

    def test_non_boolean_dielectric_flag_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_criteria(self._inputs(dielectric_in_gap="no"))

    def test_zero_mode_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_criteria(self._inputs(propagating_modes=0))

    def test_non_integer_mode_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_criteria(self._inputs(propagating_modes=1.0))

    def test_non_mapping_inputs_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_criteria(["geometry"])


class LevelSelectionTests(unittest.TestCase):
    def _verdicts(self, **overrides):
        base = {name: True for name in LEVEL_ONE_CRITERIA}
        base.update(overrides)
        return base

    def test_all_true_selects_the_first_level(self):
        level, failed = select_analysis_level(self._verdicts())
        self.assertEqual(level, "level-one")
        self.assertEqual(failed, [])

    def test_one_failure_escalates(self):
        level, failed = select_analysis_level(self._verdicts(**{"no-dielectric-in-gap": False}))
        self.assertEqual(level, "level-two")
        self.assertEqual(failed, ["no-dielectric-in-gap"])

    def test_failures_reported_in_criterion_order(self):
        _, failed = select_analysis_level(
            self._verdicts(**{"single-dominant-mode": False, "canonical-geometry": False})
        )
        self.assertEqual(failed, ["canonical-geometry", "single-dominant-mode"])

    def test_missing_criterion_rejected(self):
        verdicts = self._verdicts()
        del verdicts["canonical-geometry"]
        with self.assertRaises(ValueError):
            select_analysis_level(verdicts)

    def test_non_boolean_verdict_rejected(self):
        with self.assertRaises(ValueError):
            select_analysis_level(self._verdicts(**{"canonical-geometry": 1}))

    def test_empty_verdicts_rejected(self):
        with self.assertRaises(ValueError):
            select_analysis_level({})


class EvidenceTests(unittest.TestCase):
    def test_complete_record_has_no_gap(self):
        self.assertEqual(missing_evidence(list(LEVEL_ONE_EVIDENCE)), [])

    def test_absent_record_lists_everything(self):
        self.assertEqual(missing_evidence(None), list(LEVEL_ONE_EVIDENCE))

    def test_partial_record_lists_the_remainder(self):
        absent = missing_evidence(["worst-case-in-band-frequency"])
        self.assertNotIn("worst-case-in-band-frequency", absent)
        self.assertEqual(len(absent), len(LEVEL_ONE_EVIDENCE) - 1)

    def test_unknown_evidence_item_rejected(self):
        with self.assertRaises(ValueError):
            missing_evidence(["particle-tracking-run"])

    def test_non_sequence_record_rejected(self):
        with self.assertRaises(ValueError):
            missing_evidence("worst-case-in-band-frequency")


class MarginTests(unittest.TestCase):
    def test_closed_form_margin(self):
        self.assertAlmostEqual(level_one_margin_db(200.0, 50.0, 100.0), 6.020599913, places=6)

    def test_magnification_lowers_the_margin(self):
        plain = level_one_margin_db(200.0, 50.0, 100.0)
        magnified = level_one_margin_db(200.0, 50.0, 100.0, 2.0)
        self.assertAlmostEqual(plain - magnified, 10.0 * math.log10(4.0), places=9)

    def test_zero_operating_power_rejected(self):
        with self.assertRaises(ValueError):
            level_one_margin_db(200.0, 50.0, 0.0)

    def test_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            level_one_margin_db(-200.0, 50.0, 100.0)


class AssessmentTests(unittest.TestCase):
    def test_compliant_component_stays_at_the_first_level(self):
        result = assess_level_one(spec())
        self.assertEqual(result["analysis_level"], "level-one")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_worst_case_gap_is_the_minimum_of_the_stack(self):
        result = assess_level_one(spec())
        self.assertAlmostEqual(result["gap_min_mm"], 0.10)
        self.assertAlmostEqual(result["worst_case"]["gap_mm"], 0.10)
        self.assertAlmostEqual(result["worst_case"]["threshold_voltage_v"], 120.0)

    def test_dielectric_loading_escalates_and_is_reported(self):
        result = assess_level_one(spec(dielectric_in_gap=True))
        self.assertEqual(result["analysis_level"], "level-two")
        self.assertFalse(result["compliant"])
        self.assertIn("no-dielectric-in-gap", result["findings"][0])

    def test_arbitrary_geometry_escalates(self):
        result = assess_level_one(spec(geometry="arbitrary-three-dimensional"))
        self.assertEqual(result["failed_criteria"], ["canonical-geometry"])

    def test_margin_shortfall_is_flagged(self):
        result = assess_level_one(spec(operating_power_w=1000.0))
        self.assertFalse(result["margin_ok"])
        self.assertFalse(result["compliant"])

    def test_exact_boundary_margin_is_compliant(self):
        base = spec()
        achieved = level_one_margin_db(120.0, 50.0, base["operating_power_w"])
        result = assess_level_one(spec(required_margin_db=achieved))
        self.assertTrue(result["margin_ok"])
        self.assertLessEqual(
            abs(result["achieved_margin_db"] - achieved), MARGIN_TOLERANCE_DB
        )

    def test_missing_evidence_is_reported(self):
        result = assess_level_one(spec(declared_evidence=["achieved-margin-statement"]))
        self.assertEqual(len(result["missing_evidence"]), 3)
        self.assertFalse(result["compliant"])

    def test_required_keys_enforced(self):
        bad = spec()
        del bad["impedance_ohm"]
        with self.assertRaises(ValueError):
            assess_level_one(bad)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_level_one("parallel-plate")

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            assess_level_one(spec(required_margin_db=-1.0))

    def test_gap_stack_error_propagates(self):
        with self.assertRaises(ValueError):
            assess_level_one(spec(minus_tolerance_mm=0.20))


if __name__ == "__main__":
    unittest.main()
