#!/usr/bin/env python3
"""Gate 3 contract test for e2001-electromagnetic-field-analysis.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2001_electromagnetic_field_analysis.py
"""

import math
import unittest

from e2001_electromagnetic_field_analysis_logic import (
    CONVERGENCE_TOLERANCE_PCT,
    GOVERNING_CLOSENESS_DB,
    MIN_BAND_SAMPLES,
    SOLVER_TYPES,
    assess_field_analysis,
    assess_region,
    ceil_with_tolerance,
    equivalent_gap_voltage,
    frequency_gap_product,
    frequency_sampling_findings,
    mesh_convergence,
    required_band_samples,
    resolve_solver,
    scale_field_to_power,
    select_governing_regions,
)

FEM = "finite-element-frequency-domain"


def region(region_id="iris-1", gap_mm=0.8, frequency_ghz=22.0,
           field=1.36e6, uniformity=0.9, dielectric=None):
    out = {
        "region_id": region_id,
        "gap_mm": gap_mm,
        "frequency_ghz": frequency_ghz,
        "reference_peak_field_v_per_m": field,
        "uniformity_factor": uniformity,
    }
    if dielectric is not None:
        out["dielectric_loaded"] = dielectric
    return out


def model(model_id="omux-filter-fem", solver=FEM,
          levels=(1.20e6, 1.35e6, 1.36e6), band=(21.45, 22.55), q=400.0,
          samples=100, p_ref=1.0, p_op=200.0, regions=None):
    return {
        "model_id": model_id,
        "solver": solver,
        "mesh_peak_fields_v_per_m": list(levels),
        "band_start_ghz": band[0],
        "band_stop_ghz": band[1],
        "loaded_q": q,
        "frequency_samples": samples,
        "reference_power_w": p_ref,
        "operating_power_w": p_op,
        "regions": list(regions) if regions is not None else [
            region("iris-1"),
            region("step-2", gap_mm=1.2, field=0.9e6, uniformity=1.0),
        ],
    }


class TestToleranceAwareCeiling(unittest.TestCase):
    def test_a_whole_number_reached_through_rounding_does_not_round_up(self):
        self.assertEqual(ceil_with_tolerance(100.00000000000013), 100)

    def test_a_genuine_fraction_still_rounds_up(self):
        self.assertEqual(ceil_with_tolerance(99.5), 100)

    def test_an_exact_whole_number_is_unchanged(self):
        self.assertEqual(ceil_with_tolerance(64.0), 64)

    def test_non_numeric_value_is_refused(self):
        with self.assertRaises(ValueError):
            ceil_with_tolerance("100")


class TestSolverResolution(unittest.TestCase):
    def test_recognized_solver_carries_its_specification(self):
        spec = resolve_solver(FEM)
        self.assertEqual(spec["solver"], FEM)
        self.assertTrue(spec["carries_dielectric"])
        self.assertEqual(spec["min_refinement_levels"], 3)

    def test_solver_name_is_matched_case_and_whitespace_insensitively(self):
        self.assertEqual(resolve_solver("  Mode-Matching ")["solver"], "mode-matching")

    def test_every_recognized_solver_declares_its_refinement_requirement(self):
        for name in SOLVER_TYPES:
            with self.subTest(solver=name):
                spec = resolve_solver(name)
                self.assertGreaterEqual(spec["min_refinement_levels"], 2)

    def test_uncategorized_solver_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_solver("ray-tracing")

    def test_non_string_solver_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_solver(None)


class TestFieldScaling(unittest.TestCase):
    def test_field_goes_as_the_square_root_of_power(self):
        self.assertAlmostEqual(
            scale_field_to_power(1.0e6, 1.0, 4.0), 2.0e6, places=3
        )

    def test_field_at_the_reference_power_is_unchanged(self):
        self.assertAlmostEqual(scale_field_to_power(1.36e6, 50.0, 50.0), 1.36e6)

    def test_doubling_the_power_raises_the_field_by_root_two(self):
        self.assertAlmostEqual(
            scale_field_to_power(1.0e6, 100.0, 200.0), 1.0e6 * math.sqrt(2.0),
            places=3,
        )

    def test_zero_reference_power_is_refused(self):
        with self.assertRaises(ValueError):
            scale_field_to_power(1.0e6, 0.0, 200.0)

    def test_negative_field_is_refused(self):
        with self.assertRaises(ValueError):
            scale_field_to_power(-1.0e6, 1.0, 200.0)

    def test_non_numeric_operating_power_is_refused(self):
        with self.assertRaises(ValueError):
            scale_field_to_power(1.0e6, 1.0, "200")


class TestEquivalentGapVoltage(unittest.TestCase):
    def test_uniform_gap_integrates_the_field_over_the_separation(self):
        self.assertAlmostEqual(equivalent_gap_voltage(1.0e6, 1.0, 1.0), 1000.0)

    def test_uniformity_factor_reduces_the_equivalent_voltage(self):
        self.assertAlmostEqual(equivalent_gap_voltage(1.0e6, 1.0, 0.75), 750.0)

    def test_wider_gap_carries_more_voltage_at_the_same_field(self):
        narrow = equivalent_gap_voltage(1.0e6, 0.8, 1.0)
        wide = equivalent_gap_voltage(1.0e6, 1.2, 1.0)
        self.assertGreater(wide, narrow)

    def test_uniformity_factor_above_unity_is_refused(self):
        with self.assertRaises(ValueError):
            equivalent_gap_voltage(1.0e6, 1.0, 1.2)

    def test_zero_uniformity_factor_is_refused(self):
        with self.assertRaises(ValueError):
            equivalent_gap_voltage(1.0e6, 1.0, 0.0)

    def test_zero_gap_is_refused(self):
        with self.assertRaises(ValueError):
            equivalent_gap_voltage(1.0e6, 0.0, 1.0)


class TestFrequencyGapProduct(unittest.TestCase):
    def test_product_multiplies_frequency_by_separation(self):
        self.assertAlmostEqual(frequency_gap_product(22.0, 0.8), 17.6)

    def test_negative_gap_is_refused(self):
        with self.assertRaises(ValueError):
            frequency_gap_product(22.0, -0.8)

    def test_zero_frequency_is_refused(self):
        with self.assertRaises(ValueError):
            frequency_gap_product(0.0, 0.8)


class TestMeshConvergence(unittest.TestCase):
    def test_settled_peak_field_is_converged(self):
        result = mesh_convergence([1.20e6, 1.35e6, 1.36e6], 3)
        self.assertTrue(result["converged"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["finest_peak_field_v_per_m"], 1.36e6)

    def test_still_moving_peak_field_is_not_converged(self):
        result = mesh_convergence([1.0e6, 1.2e6, 1.5e6], 3)
        self.assertFalse(result["converged"])
        self.assertTrue(any("still moving" in f for f in result["findings"]))

    def test_change_landing_exactly_on_the_tolerance_is_converged(self):
        # 100005.0 and 102005.1 differ by exactly two percent in decimal, but
        # the binary quotient lands a few units in the last place above the
        # tolerance. The tolerance must not move to accommodate that.
        result = mesh_convergence([102005.1, 100005.0], 2)
        self.assertGreater(result["relative_change_pct"], CONVERGENCE_TOLERANCE_PCT)
        self.assertAlmostEqual(
            result["relative_change_pct"], CONVERGENCE_TOLERANCE_PCT, places=9
        )
        self.assertTrue(result["converged"])

    def test_too_few_refinement_levels_is_a_finding(self):
        result = mesh_convergence([1.35e6, 1.36e6], 3)
        self.assertFalse(result["converged"])
        self.assertTrue(any("refinement levels" in f for f in result["findings"]))

    def test_a_single_refinement_level_cannot_show_convergence(self):
        with self.assertRaises(ValueError):
            mesh_convergence([1.36e6], 3)

    def test_non_sequence_level_list_is_refused(self):
        with self.assertRaises(ValueError):
            mesh_convergence("1.36e6", 3)

    def test_non_positive_peak_field_is_refused(self):
        with self.assertRaises(ValueError):
            mesh_convergence([1.35e6, 0.0], 2)

    def test_non_integer_level_requirement_is_refused(self):
        with self.assertRaises(ValueError):
            mesh_convergence([1.35e6, 1.36e6], 2.5)


class TestFrequencySampling(unittest.TestCase):
    def test_sample_count_reached_through_rounding_is_not_inflated(self):
        # 1.1 GHz of band at a loaded quality-factor of 400 about 22 GHz is
        # exactly twenty resonance widths, so exactly one hundred samples are
        # owed; a bare ceiling would demand a hundred and one.
        self.assertEqual(required_band_samples(21.45, 22.55, 400.0), 100)

    def test_a_wide_low_quality_band_falls_back_to_the_sample_floor(self):
        self.assertEqual(required_band_samples(10.0, 10.2, 5.0), MIN_BAND_SAMPLES)

    def test_higher_quality_factor_demands_more_samples(self):
        coarse = required_band_samples(21.45, 22.55, 400.0)
        fine = required_band_samples(21.45, 22.55, 800.0)
        self.assertGreater(fine, coarse)

    def test_inverted_band_is_refused(self):
        with self.assertRaises(ValueError):
            required_band_samples(22.55, 21.45, 400.0)

    def test_zero_quality_factor_is_refused(self):
        with self.assertRaises(ValueError):
            required_band_samples(21.45, 22.55, 0.0)

    def test_adequate_sampling_reports_no_finding(self):
        result = frequency_sampling_findings(21.45, 22.55, 100, 400.0)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["required_samples"], 100)

    def test_under_sampled_band_is_a_finding(self):
        result = frequency_sampling_findings(21.45, 22.55, 40, 400.0)
        self.assertFalse(result["adequate"])
        self.assertTrue(any("resolve the loaded" in f for f in result["findings"]))

    def test_a_single_sample_is_refused(self):
        with self.assertRaises(ValueError):
            frequency_sampling_findings(21.45, 22.55, 1, 400.0)

    def test_non_integer_sample_count_is_refused(self):
        with self.assertRaises(ValueError):
            frequency_sampling_findings(21.45, 22.55, 100.5, 400.0)


class TestRegionAssessment(unittest.TestCase):
    def setUp(self):
        self.fem = resolve_solver(FEM)
        self.mode = resolve_solver("mode-matching")

    def test_region_voltage_follows_the_scaled_field(self):
        result = assess_region(region(), 1.0, 4.0, self.fem)
        expected_field = 1.36e6 * 2.0
        self.assertAlmostEqual(result["peak_field_v_per_m"], expected_field, places=3)
        self.assertAlmostEqual(
            result["equivalent_gap_voltage_v"],
            expected_field * 0.0008 * 0.9,
            places=6,
        )

    def test_region_records_its_frequency_gap_product(self):
        result = assess_region(region(), 1.0, 1.0, self.fem)
        self.assertAlmostEqual(result["frequency_gap_product_ghz_mm"], 17.6)

    def test_uniformity_factor_defaults_to_a_uniform_gap(self):
        bare = {
            "region_id": "iris-1",
            "gap_mm": 1.0,
            "frequency_ghz": 22.0,
            "reference_peak_field_v_per_m": 1.0e6,
        }
        result = assess_region(bare, 1.0, 1.0, self.fem)
        self.assertAlmostEqual(result["equivalent_gap_voltage_v"], 1000.0)

    def test_dielectric_region_with_a_metal_only_solver_is_a_finding(self):
        result = assess_region(region(dielectric=True), 1.0, 1.0, self.mode)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("dielectric-loaded", result["findings"][0])

    def test_dielectric_region_with_a_dielectric_solver_is_clean(self):
        result = assess_region(region(dielectric=True), 1.0, 1.0, self.fem)
        self.assertEqual(result["findings"], [])

    def test_region_without_an_identifier_is_refused(self):
        bad = region()
        bad["region_id"] = "  "
        with self.assertRaises(ValueError):
            assess_region(bad, 1.0, 1.0, self.fem)

    def test_non_mapping_region_is_refused(self):
        with self.assertRaises(ValueError):
            assess_region(["iris-1"], 1.0, 1.0, self.fem)

    def test_non_boolean_dielectric_flag_is_refused(self):
        bad = region()
        bad["dielectric_loaded"] = "yes"
        with self.assertRaises(ValueError):
            assess_region(bad, 1.0, 1.0, self.fem)


class TestGoverningRegionSelection(unittest.TestCase):
    def setUp(self):
        self.fem = resolve_solver(FEM)

    def assessed(self, *regions):
        return [assess_region(r, 1.0, 1.0, self.fem) for r in regions]

    def test_single_region_governs_alone(self):
        result = select_governing_regions(self.assessed(region()))
        self.assertEqual(result["governing_region_ids"], ["iris-1"])
        self.assertFalse(result["co_governing"])

    def test_the_highest_gap_voltage_governs(self):
        regions = self.assessed(
            region("iris-1", gap_mm=0.8, field=1.0e6, uniformity=1.0),
            region("step-2", gap_mm=1.6, field=1.0e6, uniformity=1.0),
        )
        result = select_governing_regions(regions)
        self.assertEqual(result["governing_region_ids"], ["step-2"])
        self.assertAlmostEqual(result["highest_gap_voltage_v"], 1600.0)

    def test_equal_regions_both_govern(self):
        regions = self.assessed(
            region("iris-1", gap_mm=1.0, field=1.0e6, uniformity=1.0),
            region("iris-2", gap_mm=1.0, field=1.0e6, uniformity=1.0),
        )
        result = select_governing_regions(regions)
        self.assertEqual(result["governing_region_ids"], ["iris-1", "iris-2"])
        self.assertTrue(result["co_governing"])

    def test_region_exactly_at_the_closeness_band_still_governs(self):
        lower = 1.0e6 / (10.0 ** (GOVERNING_CLOSENESS_DB / 20.0))
        regions = self.assessed(
            region("iris-1", gap_mm=1.0, field=1.0e6, uniformity=1.0),
            region("iris-2", gap_mm=1.0, field=lower, uniformity=1.0),
        )
        result = select_governing_regions(regions)
        self.assertIn("iris-2", result["governing_region_ids"])
        self.assertTrue(result["co_governing"])

    def test_region_outside_the_closeness_band_does_not_govern(self):
        regions = self.assessed(
            region("iris-1", gap_mm=1.0, field=1.0e6, uniformity=1.0),
            region("iris-2", gap_mm=1.0, field=0.5e6, uniformity=1.0),
        )
        result = select_governing_regions(regions)
        self.assertEqual(result["governing_region_ids"], ["iris-1"])

    def test_empty_region_set_is_refused(self):
        with self.assertRaises(ValueError):
            select_governing_regions([])

    def test_non_sequence_region_set_is_refused(self):
        with self.assertRaises(ValueError):
            select_governing_regions("iris-1")


class TestFieldAnalysisAssessment(unittest.TestCase):
    def test_sound_model_permits_threshold_establishment(self):
        result = assess_field_analysis(model())
        self.assertTrue(result["threshold_establishment_permitted"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["region_count"], 2)
        self.assertEqual(result["governing_region_ids"], ["step-2"])

    def test_unconverged_model_blocks_threshold_establishment(self):
        result = assess_field_analysis(model(levels=(1.0e6, 1.2e6, 1.5e6)))
        self.assertFalse(result["threshold_establishment_permitted"])
        self.assertFalse(result["convergence"]["converged"])

    def test_too_few_refinement_levels_block_threshold_establishment(self):
        result = assess_field_analysis(model(levels=(1.35e6, 1.36e6)))
        self.assertFalse(result["threshold_establishment_permitted"])

    def test_under_sampled_band_blocks_threshold_establishment(self):
        result = assess_field_analysis(model(samples=40))
        self.assertFalse(result["threshold_establishment_permitted"])
        self.assertFalse(result["sampling"]["adequate"])

    def test_dielectric_region_on_a_metal_only_solver_blocks_the_model(self):
        result = assess_field_analysis(
            model(
                solver="mode-matching",
                levels=(1.35e6, 1.36e6),
                regions=[region("iris-1", dielectric=True)],
            )
        )
        self.assertFalse(result["threshold_establishment_permitted"])
        self.assertTrue(any("dielectric-loaded" in f for f in result["findings"]))

    def test_operating_power_raises_every_region_voltage(self):
        low = assess_field_analysis(model(p_op=50.0))
        high = assess_field_analysis(model(p_op=200.0))
        self.assertGreater(
            high["highest_gap_voltage_v"], low["highest_gap_voltage_v"]
        )

    def test_duplicate_region_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            assess_field_analysis(
                model(regions=[region("iris-1"), region("iris-1", gap_mm=1.2)])
            )

    def test_model_without_regions_is_refused(self):
        with self.assertRaises(ValueError):
            assess_field_analysis(model(regions=[]))

    def test_model_without_an_identifier_is_refused(self):
        bad = model()
        bad["model_id"] = ""
        with self.assertRaises(ValueError):
            assess_field_analysis(bad)

    def test_uncategorized_solver_is_refused(self):
        with self.assertRaises(ValueError):
            assess_field_analysis(model(solver="ray-tracing"))

    def test_non_mapping_model_is_refused(self):
        with self.assertRaises(ValueError):
            assess_field_analysis(["omux-filter-fem"])

    def test_zero_operating_power_is_refused(self):
        with self.assertRaises(ValueError):
            assess_field_analysis(model(p_op=0.0))


if __name__ == "__main__":
    unittest.main()
