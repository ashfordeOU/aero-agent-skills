"""Contract test for the ECSS-E-ST-20-01C clause 9.1 yield definition."""

import math
import unittest

from e2001_secondary_emission_yield_definition_logic import (
    DEFAULT_E0_EV,
    angle_corrected_parameters,
    categorize_surface_yield,
    evaluate_yield_definition,
    first_crossover_energy,
    is_in_growth_band,
    second_crossover_energy,
    susceptible_energy_band,
    total_emission_yield,
    vaughan_yield,
    yield_from_currents,
)

PEAK_YIELD = 2.0
PEAK_ENERGY = 300.0


class TotalYieldTests(unittest.TestCase):
    def test_total_yield_sums_both_emitted_populations(self):
        self.assertAlmostEqual(total_emission_yield(1.6, 0.25), 1.85, places=12)

    def test_pure_backscatter_still_counts(self):
        self.assertAlmostEqual(total_emission_yield(0.0, 0.4), 0.4, places=12)

    def test_no_emission_gives_zero_yield(self):
        self.assertAlmostEqual(total_emission_yield(0.0, 0.0), 0.0, places=12)

    def test_negative_true_secondary_yield_raises(self):
        with self.assertRaises(ValueError):
            total_emission_yield(-0.1, 0.2)

    def test_negative_backscattered_yield_raises(self):
        with self.assertRaises(ValueError):
            total_emission_yield(1.0, -0.2)

    def test_non_numeric_component_raises(self):
        with self.assertRaises(ValueError):
            total_emission_yield("1.6", 0.2)


class CurrentRatioTests(unittest.TestCase):
    def test_yield_is_the_current_ratio(self):
        self.assertAlmostEqual(yield_from_currents(2.0e-9, 3.4e-9), 1.7, places=12)

    def test_equal_currents_give_unity_yield(self):
        self.assertAlmostEqual(yield_from_currents(5.0e-9, 5.0e-9), 1.0, places=12)

    def test_zero_emitted_current_gives_zero_yield(self):
        self.assertAlmostEqual(yield_from_currents(5.0e-9, 0.0), 0.0, places=12)

    def test_zero_incident_current_raises(self):
        with self.assertRaises(ValueError):
            yield_from_currents(0.0, 1.0e-9)

    def test_negative_incident_current_raises(self):
        with self.assertRaises(ValueError):
            yield_from_currents(-1.0e-9, 1.0e-9)

    def test_negative_emitted_current_raises(self):
        with self.assertRaises(ValueError):
            yield_from_currents(1.0e-9, -1.0e-9)

    def test_boolean_current_raises(self):
        with self.assertRaises(ValueError):
            yield_from_currents(True, 1.0e-9)


class AngleCorrectionTests(unittest.TestCase):
    def test_normal_incidence_leaves_parameters_untouched(self):
        peak, energy = angle_corrected_parameters(PEAK_YIELD, PEAK_ENERGY, 0.0)
        self.assertAlmostEqual(peak, PEAK_YIELD, places=12)
        self.assertAlmostEqual(energy, PEAK_ENERGY, places=12)

    def test_grazing_incidence_raises_the_peak_yield(self):
        peak, _ = angle_corrected_parameters(PEAK_YIELD, PEAK_ENERGY, 60.0)
        self.assertGreater(peak, PEAK_YIELD)

    def test_grazing_incidence_raises_the_peak_energy(self):
        _, energy = angle_corrected_parameters(PEAK_YIELD, PEAK_ENERGY, 60.0)
        self.assertGreater(energy, PEAK_ENERGY)

    def test_energy_shift_is_twice_the_yield_shift(self):
        peak, energy = angle_corrected_parameters(PEAK_YIELD, PEAK_ENERGY, 45.0)
        self.assertAlmostEqual(
            (energy / PEAK_ENERGY) - 1.0, 2.0 * ((peak / PEAK_YIELD) - 1.0), places=12
        )

    def test_zero_smoothness_makes_a_rough_surface_angle_blind(self):
        peak, energy = angle_corrected_parameters(PEAK_YIELD, PEAK_ENERGY, 80.0, 0.0)
        self.assertAlmostEqual(peak, PEAK_YIELD, places=12)
        self.assertAlmostEqual(energy, PEAK_ENERGY, places=12)

    def test_angle_of_ninety_degrees_raises(self):
        with self.assertRaises(ValueError):
            angle_corrected_parameters(PEAK_YIELD, PEAK_ENERGY, 90.0)

    def test_negative_angle_raises(self):
        with self.assertRaises(ValueError):
            angle_corrected_parameters(PEAK_YIELD, PEAK_ENERGY, -5.0)

    def test_smoothness_above_two_raises(self):
        with self.assertRaises(ValueError):
            angle_corrected_parameters(PEAK_YIELD, PEAK_ENERGY, 30.0, 2.5)

    def test_zero_peak_yield_raises(self):
        with self.assertRaises(ValueError):
            angle_corrected_parameters(0.0, PEAK_ENERGY, 0.0)

    def test_zero_peak_energy_raises(self):
        with self.assertRaises(ValueError):
            angle_corrected_parameters(PEAK_YIELD, 0.0, 0.0)


class VaughanCurveTests(unittest.TestCase):
    def test_yield_peaks_at_the_peak_energy(self):
        self.assertAlmostEqual(
            vaughan_yield(PEAK_ENERGY, PEAK_YIELD, PEAK_ENERGY), PEAK_YIELD, places=12
        )

    def test_yield_below_the_threshold_energy_is_zero(self):
        self.assertAlmostEqual(vaughan_yield(5.0, PEAK_YIELD, PEAK_ENERGY), 0.0, places=12)

    def test_yield_at_the_threshold_energy_is_zero(self):
        self.assertAlmostEqual(
            vaughan_yield(DEFAULT_E0_EV, PEAK_YIELD, PEAK_ENERGY), 0.0, places=12
        )

    def test_yield_at_zero_energy_is_zero(self):
        self.assertAlmostEqual(vaughan_yield(0.0, PEAK_YIELD, PEAK_ENERGY), 0.0, places=12)

    def test_curve_rises_below_the_peak(self):
        low = vaughan_yield(100.0, PEAK_YIELD, PEAK_ENERGY)
        high = vaughan_yield(200.0, PEAK_YIELD, PEAK_ENERGY)
        self.assertLess(low, high)
        self.assertLess(high, PEAK_YIELD)

    def test_curve_decays_above_the_peak(self):
        near = vaughan_yield(600.0, PEAK_YIELD, PEAK_ENERGY)
        far = vaughan_yield(3000.0, PEAK_YIELD, PEAK_ENERGY)
        self.assertLess(far, near)
        self.assertLess(near, PEAK_YIELD)

    def test_far_tail_stays_positive(self):
        self.assertGreater(vaughan_yield(50000.0, PEAK_YIELD, PEAK_ENERGY), 0.0)

    def test_tail_branch_is_continuous_at_the_break(self):
        break_energy = DEFAULT_E0_EV + 3.6 * (PEAK_ENERGY - DEFAULT_E0_EV)
        below = vaughan_yield(break_energy, PEAK_YIELD, PEAK_ENERGY)
        above = vaughan_yield(break_energy * 1.0000001, PEAK_YIELD, PEAK_ENERGY)
        self.assertAlmostEqual(below, above, places=2)

    def test_grazing_incidence_raises_the_yield_at_the_peak(self):
        normal = vaughan_yield(PEAK_ENERGY, PEAK_YIELD, PEAK_ENERGY, DEFAULT_E0_EV, 0.0)
        grazing = vaughan_yield(PEAK_ENERGY, PEAK_YIELD, PEAK_ENERGY, DEFAULT_E0_EV, 70.0)
        self.assertGreater(grazing, normal)

    def test_negative_impact_energy_raises(self):
        with self.assertRaises(ValueError):
            vaughan_yield(-1.0, PEAK_YIELD, PEAK_ENERGY)

    def test_threshold_above_the_peak_energy_raises(self):
        with self.assertRaises(ValueError):
            vaughan_yield(100.0, PEAK_YIELD, 50.0, 80.0)

    def test_negative_threshold_energy_raises(self):
        with self.assertRaises(ValueError):
            vaughan_yield(100.0, PEAK_YIELD, PEAK_ENERGY, -1.0)

    def test_non_numeric_impact_energy_raises(self):
        with self.assertRaises(ValueError):
            vaughan_yield("100", PEAK_YIELD, PEAK_ENERGY)


class CrossoverTests(unittest.TestCase):
    def test_lower_crossover_sits_between_threshold_and_peak(self):
        lower = first_crossover_energy(PEAK_YIELD, PEAK_ENERGY)
        self.assertGreater(lower, DEFAULT_E0_EV)
        self.assertLess(lower, PEAK_ENERGY)

    def test_yield_at_the_lower_crossover_is_unity(self):
        lower = first_crossover_energy(PEAK_YIELD, PEAK_ENERGY)
        self.assertAlmostEqual(vaughan_yield(lower, PEAK_YIELD, PEAK_ENERGY), 1.0, places=9)

    def test_upper_crossover_sits_above_the_peak(self):
        upper = second_crossover_energy(PEAK_YIELD, PEAK_ENERGY)
        self.assertGreater(upper, PEAK_ENERGY)

    def test_yield_at_the_upper_crossover_is_unity(self):
        upper = second_crossover_energy(PEAK_YIELD, PEAK_ENERGY)
        self.assertAlmostEqual(vaughan_yield(upper, PEAK_YIELD, PEAK_ENERGY), 1.0, places=9)

    def test_a_higher_peak_yield_widens_the_band(self):
        narrow = susceptible_energy_band(1.3, PEAK_ENERGY)["band_width_ev"]
        wide = susceptible_energy_band(2.5, PEAK_ENERGY)["band_width_ev"]
        self.assertGreater(wide, narrow)

    def test_surface_below_unity_has_no_lower_crossover(self):
        self.assertIsNone(first_crossover_energy(0.85, PEAK_ENERGY))

    def test_surface_below_unity_has_no_upper_crossover(self):
        self.assertIsNone(second_crossover_energy(0.85, PEAK_ENERGY))

    def test_peak_yield_exactly_at_unity_has_no_crossover(self):
        self.assertIsNone(first_crossover_energy(1.0, PEAK_ENERGY))

    def test_peak_yield_one_ulp_above_unity_is_absorbed_as_unity(self):
        just_over = math.nextafter(1.0, 2.0)
        self.assertGreater(just_over, 1.0)
        self.assertIsNone(first_crossover_energy(just_over, PEAK_ENERGY))

    def test_peak_yield_genuinely_above_unity_still_crosses(self):
        self.assertIsNotNone(first_crossover_energy(1.000001, PEAK_ENERGY))

    def test_crossover_with_threshold_above_the_peak_raises(self):
        with self.assertRaises(ValueError):
            first_crossover_energy(PEAK_YIELD, 50.0, 80.0)

    def test_upper_crossover_with_threshold_above_the_peak_raises(self):
        with self.assertRaises(ValueError):
            second_crossover_energy(PEAK_YIELD, 50.0, 80.0)


class SusceptibleBandTests(unittest.TestCase):
    def test_band_of_a_high_yield_surface_permits_growth(self):
        band = susceptible_energy_band(PEAK_YIELD, PEAK_ENERGY)
        self.assertTrue(band["growth_possible"])
        self.assertGreater(band["band_width_ev"], 0.0)

    def test_band_width_matches_the_two_crossovers(self):
        band = susceptible_energy_band(PEAK_YIELD, PEAK_ENERGY)
        self.assertAlmostEqual(
            band["band_width_ev"],
            band["upper_crossover_ev"] - band["lower_crossover_ev"],
            places=9,
        )

    def test_low_yield_surface_has_no_band(self):
        band = susceptible_energy_band(0.9, PEAK_ENERGY)
        self.assertFalse(band["growth_possible"])
        self.assertIsNone(band["band_width_ev"])
        self.assertTrue(band["degenerate"])

    def test_unity_peak_yield_gives_a_degenerate_band(self):
        band = susceptible_energy_band(1.0, PEAK_ENERGY)
        self.assertFalse(band["growth_possible"])

    def test_grazing_incidence_widens_the_band(self):
        normal = susceptible_energy_band(PEAK_YIELD, PEAK_ENERGY, DEFAULT_E0_EV, 0.0)
        grazing = susceptible_energy_band(PEAK_YIELD, PEAK_ENERGY, DEFAULT_E0_EV, 70.0)
        self.assertGreater(grazing["band_width_ev"], normal["band_width_ev"])


class GrowthBandMembershipTests(unittest.TestCase):
    def test_peak_energy_is_inside_the_growth_band(self):
        self.assertTrue(is_in_growth_band(PEAK_ENERGY, PEAK_YIELD, PEAK_ENERGY))

    def test_energy_below_the_lower_crossover_is_outside(self):
        lower = first_crossover_energy(PEAK_YIELD, PEAK_ENERGY)
        self.assertFalse(is_in_growth_band(lower * 0.9, PEAK_YIELD, PEAK_ENERGY))

    def test_energy_above_the_upper_crossover_is_outside(self):
        upper = second_crossover_energy(PEAK_YIELD, PEAK_ENERGY)
        self.assertFalse(is_in_growth_band(upper * 1.1, PEAK_YIELD, PEAK_ENERGY))

    def test_the_lower_crossover_itself_is_replacement_not_growth(self):
        lower = first_crossover_energy(PEAK_YIELD, PEAK_ENERGY)
        self.assertFalse(is_in_growth_band(lower, PEAK_YIELD, PEAK_ENERGY))

    def test_the_upper_crossover_itself_is_replacement_not_growth(self):
        upper = second_crossover_energy(PEAK_YIELD, PEAK_ENERGY)
        self.assertFalse(is_in_growth_band(upper, PEAK_YIELD, PEAK_ENERGY))

    def test_energy_just_inside_the_lower_crossover_is_growth(self):
        lower = first_crossover_energy(PEAK_YIELD, PEAK_ENERGY)
        self.assertTrue(is_in_growth_band(lower * 1.05, PEAK_YIELD, PEAK_ENERGY))

    def test_energy_below_the_threshold_is_outside(self):
        self.assertFalse(is_in_growth_band(1.0, PEAK_YIELD, PEAK_ENERGY))


class SurfaceCategorizationTests(unittest.TestCase):
    def test_yield_below_unity_is_low(self):
        self.assertEqual(categorize_surface_yield(0.7), "low-yield")

    def test_yield_exactly_at_unity_is_low(self):
        self.assertEqual(categorize_surface_yield(1.0), "low-yield")

    def test_unity_with_representation_error_is_still_low(self):
        just_over = math.nextafter(1.0, 2.0)
        self.assertGreater(just_over, 1.0)
        self.assertEqual(categorize_surface_yield(just_over), "low-yield")

    def test_yield_just_above_unity_is_moderate(self):
        self.assertEqual(categorize_surface_yield(1.2), "moderate-yield")

    def test_yield_at_the_moderate_ceiling_is_moderate(self):
        self.assertEqual(categorize_surface_yield(1.5), "moderate-yield")

    def test_yield_above_the_moderate_ceiling_is_elevated(self):
        self.assertEqual(categorize_surface_yield(2.0), "elevated-yield")

    def test_yield_at_the_elevated_ceiling_is_elevated(self):
        self.assertEqual(categorize_surface_yield(2.5), "elevated-yield")

    def test_yield_above_the_elevated_ceiling_is_high(self):
        self.assertEqual(categorize_surface_yield(3.1), "high-yield")

    def test_zero_yield_raises(self):
        with self.assertRaises(ValueError):
            categorize_surface_yield(0.0)

    def test_negative_yield_raises(self):
        with self.assertRaises(ValueError):
            categorize_surface_yield(-1.0)

    def test_non_numeric_yield_raises(self):
        with self.assertRaises(ValueError):
            categorize_surface_yield(None)


class DefinitionEvaluationTests(unittest.TestCase):
    def test_full_evaluation_of_a_susceptible_surface(self):
        result = evaluate_yield_definition(
            {
                "peak_yield": PEAK_YIELD,
                "peak_energy_ev": PEAK_ENERGY,
                "impact_energies_ev": [10.0, 50.0, 300.0, 5000.0],
            }
        )
        self.assertTrue(result["growth_possible"])
        self.assertEqual(result["category"], "elevated-yield")
        self.assertEqual(len(result["samples"]), 4)

    def test_sample_below_the_threshold_has_zero_yield(self):
        result = evaluate_yield_definition(
            {"peak_yield": PEAK_YIELD, "peak_energy_ev": PEAK_ENERGY, "impact_energies_ev": [10.0]}
        )
        self.assertAlmostEqual(result["samples"][0]["yield"], 0.0, places=12)
        self.assertFalse(result["samples"][0]["in_growth_band"])

    def test_sample_at_the_peak_is_inside_the_band(self):
        result = evaluate_yield_definition(
            {
                "peak_yield": PEAK_YIELD,
                "peak_energy_ev": PEAK_ENERGY,
                "impact_energies_ev": [PEAK_ENERGY],
            }
        )
        self.assertTrue(result["samples"][0]["in_growth_band"])

    def test_treated_surface_reports_no_growth(self):
        result = evaluate_yield_definition({"peak_yield": 0.9, "peak_energy_ev": PEAK_ENERGY})
        self.assertFalse(result["growth_possible"])
        self.assertEqual(result["category"], "low-yield")

    def test_angle_raises_the_effective_peak_yield(self):
        result = evaluate_yield_definition(
            {
                "peak_yield": PEAK_YIELD,
                "peak_energy_ev": PEAK_ENERGY,
                "incidence_angle_deg": 70.0,
            }
        )
        self.assertGreater(result["effective_peak_yield"], PEAK_YIELD)
        self.assertGreater(result["effective_peak_energy_ev"], PEAK_ENERGY)

    def test_angle_can_push_a_moderate_surface_into_the_next_band(self):
        flat = evaluate_yield_definition({"peak_yield": 1.45, "peak_energy_ev": PEAK_ENERGY})
        grazing = evaluate_yield_definition(
            {"peak_yield": 1.45, "peak_energy_ev": PEAK_ENERGY, "incidence_angle_deg": 75.0}
        )
        self.assertEqual(flat["category"], "moderate-yield")
        self.assertEqual(grazing["category"], "elevated-yield")

    def test_missing_peak_energy_raises(self):
        with self.assertRaises(ValueError):
            evaluate_yield_definition({"peak_yield": PEAK_YIELD})

    def test_non_mapping_specification_raises(self):
        with self.assertRaises(ValueError):
            evaluate_yield_definition(["peak_yield"])

    def test_non_list_impact_energies_raises(self):
        with self.assertRaises(ValueError):
            evaluate_yield_definition(
                {
                    "peak_yield": PEAK_YIELD,
                    "peak_energy_ev": PEAK_ENERGY,
                    "impact_energies_ev": 300.0,
                }
            )

    def test_invalid_angle_in_the_specification_raises(self):
        with self.assertRaises(ValueError):
            evaluate_yield_definition(
                {
                    "peak_yield": PEAK_YIELD,
                    "peak_energy_ev": PEAK_ENERGY,
                    "incidence_angle_deg": 95.0,
                }
            )


if __name__ == "__main__":
    unittest.main()
