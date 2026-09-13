#!/usr/bin/env python3
"""Gate 3 contract test for e2006-differential-charging-reduction-purpose."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2006_differential_charging_reduction_purpose_logic import (  # noqa: E402
    EPSILON_0,
    SEVERITY_BANDS,
    differential_potential,
    evaluate_mission,
    evaluate_pair,
    maximum_area_for_budget,
    minimum_thickness_for_budget,
    pair_capacitance,
    reduction_factor,
    severity_band,
    stored_discharge_energy,
    within_level,
)

LEVELS = {"differential_potential_limit_v": 400.0, "energy_budget_j": 1.0e-3}


def good_pair(**over):
    pair = {
        "name": "kapton-blanket-over-grounded-panel",
        "potential_a_v": -120.0,
        "potential_b_v": 0.0,
        "coated_area_m2": 0.02,
        "dielectric_thickness_m": 5.0e-5,
        "relative_permittivity": 3.4,
    }
    pair.update(over)
    return pair


class TestDifferentialPotential(unittest.TestCase):
    def test_magnitude_of_the_difference(self):
        self.assertAlmostEqual(differential_potential(-1200.0, -300.0), 900.0, places=9)

    def test_sign_order_does_not_matter(self):
        self.assertAlmostEqual(
            differential_potential(-300.0, -1200.0),
            differential_potential(-1200.0, -300.0),
            places=9,
        )

    def test_equal_potentials_give_zero(self):
        self.assertAlmostEqual(differential_potential(-5000.0, -5000.0), 0.0, places=12)

    def test_uniform_absolute_potential_is_not_a_hazard(self):
        # Both faces far from the ambient plasma, but at the same potential.
        self.assertAlmostEqual(differential_potential(-8000.0, -8000.0), 0.0, places=12)

    def test_non_finite_potential_raises(self):
        with self.assertRaises(ValueError):
            differential_potential(float("nan"), 0.0)

    def test_non_numeric_potential_raises(self):
        with self.assertRaises(ValueError):
            differential_potential("negative", 0.0)


class TestPairCapacitance(unittest.TestCase):
    def test_parallel_plate_formula(self):
        cap = pair_capacitance(0.25, 5.0e-5, 3.4)
        self.assertAlmostEqual(cap, EPSILON_0 * 3.4 * 0.25 / 5.0e-5, places=15)

    def test_capacitance_scales_with_area(self):
        c1 = pair_capacitance(0.10, 5.0e-5, 3.4)
        c2 = pair_capacitance(0.20, 5.0e-5, 3.4)
        self.assertAlmostEqual(c2 / c1, 2.0, places=9)

    def test_capacitance_falls_with_thickness(self):
        c1 = pair_capacitance(0.10, 5.0e-5, 3.4)
        c2 = pair_capacitance(0.10, 1.0e-4, 3.4)
        self.assertAlmostEqual(c1 / c2, 2.0, places=9)

    def test_vacuum_permittivity_is_the_floor_case(self):
        self.assertAlmostEqual(
            pair_capacitance(1.0, 1.0e-3, 1.0), EPSILON_0 / 1.0e-3, places=15
        )

    def test_zero_area_raises(self):
        with self.assertRaises(ValueError):
            pair_capacitance(0.0, 5.0e-5, 3.4)

    def test_negative_thickness_raises(self):
        with self.assertRaises(ValueError):
            pair_capacitance(0.25, -5.0e-5, 3.4)

    def test_relative_permittivity_below_unity_raises(self):
        with self.assertRaises(ValueError):
            pair_capacitance(0.25, 5.0e-5, 0.5)

    def test_non_numeric_area_raises(self):
        with self.assertRaises(ValueError):
            pair_capacitance("quarter", 5.0e-5, 3.4)


class TestStoredEnergy(unittest.TestCase):
    def test_half_c_v_squared(self):
        self.assertAlmostEqual(stored_discharge_energy(2.0e-9, 1000.0), 1.0e-3, places=12)

    def test_energy_is_quadratic_in_potential(self):
        e1 = stored_discharge_energy(1.0e-9, 100.0)
        e2 = stored_discharge_energy(1.0e-9, 200.0)
        self.assertAlmostEqual(e2 / e1, 4.0, places=9)

    def test_zero_potential_stores_no_energy(self):
        self.assertAlmostEqual(stored_discharge_energy(1.0e-9, 0.0), 0.0, places=18)

    def test_negative_potential_input_raises(self):
        with self.assertRaises(ValueError):
            stored_discharge_energy(1.0e-9, -50.0)

    def test_zero_capacitance_raises(self):
        with self.assertRaises(ValueError):
            stored_discharge_energy(0.0, 100.0)


class TestDesignLevers(unittest.TestCase):
    def test_minimum_thickness_lands_exactly_on_budget(self):
        t_min = minimum_thickness_for_budget(0.5, 3.4, 900.0, 1.0e-3)
        energy = stored_discharge_energy(pair_capacitance(0.5, t_min, 3.4), 900.0)
        self.assertAlmostEqual(energy / 1.0e-3, 1.0, places=9)

    def test_minimum_thickness_result_reads_compliant_at_the_budget(self):
        # The round-trip can land a few ULPs over; the tolerance absorbs it
        # without widening the budget.
        t_min = minimum_thickness_for_budget(0.37, 3.1, 745.0, 1.0e-3)
        energy = stored_discharge_energy(pair_capacitance(0.37, t_min, 3.1), 745.0)
        self.assertTrue(within_level(energy, 1.0e-3))

    def test_maximum_area_lands_exactly_on_budget(self):
        a_max = maximum_area_for_budget(5.0e-5, 3.4, 600.0, 1.0e-3)
        energy = stored_discharge_energy(pair_capacitance(a_max, 5.0e-5, 3.4), 600.0)
        self.assertAlmostEqual(energy / 1.0e-3, 1.0, places=9)

    def test_maximum_area_result_reads_compliant_at_the_budget(self):
        a_max = maximum_area_for_budget(7.3e-5, 2.9, 512.0, 2.5e-4)
        energy = stored_discharge_energy(pair_capacitance(a_max, 7.3e-5, 2.9), 512.0)
        self.assertTrue(within_level(energy, 2.5e-4))

    def test_thickness_lever_is_linear_but_potential_lever_is_quadratic(self):
        t_at_v = minimum_thickness_for_budget(0.5, 3.4, 800.0, 1.0e-3)
        t_at_half_v = minimum_thickness_for_budget(0.5, 3.4, 400.0, 1.0e-3)
        self.assertAlmostEqual(t_at_v / t_at_half_v, 4.0, places=9)

    def test_zero_potential_has_no_constraining_thickness(self):
        with self.assertRaises(ValueError):
            minimum_thickness_for_budget(0.5, 3.4, 0.0, 1.0e-3)

    def test_zero_potential_has_no_constraining_area(self):
        with self.assertRaises(ValueError):
            maximum_area_for_budget(5.0e-5, 3.4, 0.0, 1.0e-3)

    def test_zero_budget_raises_for_thickness(self):
        with self.assertRaises(ValueError):
            minimum_thickness_for_budget(0.5, 3.4, 900.0, 0.0)

    def test_negative_budget_raises_for_area(self):
        with self.assertRaises(ValueError):
            maximum_area_for_budget(5.0e-5, 3.4, 900.0, -1.0e-3)


class TestReductionAndSeverity(unittest.TestCase):
    def test_reduction_factor_at_budget_is_one(self):
        self.assertAlmostEqual(reduction_factor(1.0e-3, 1.0e-3), 1.0, places=12)

    def test_reduction_factor_reports_how_far_over(self):
        self.assertAlmostEqual(reduction_factor(4.0e-3, 1.0e-3), 4.0, places=12)

    def test_reduction_factor_rejects_zero_budget(self):
        with self.assertRaises(ValueError):
            reduction_factor(1.0e-3, 0.0)

    def test_reduction_factor_rejects_negative_energy(self):
        with self.assertRaises(ValueError):
            reduction_factor(-1.0e-3, 1.0e-3)

    def test_small_energy_is_negligible(self):
        self.assertEqual(severity_band(1.0e-7), "negligible")

    def test_millijoule_class_energy_is_marginal(self):
        self.assertEqual(severity_band(5.0e-4), "marginal")

    def test_large_energy_is_hazardous(self):
        self.assertEqual(severity_band(2.0e-2), "hazardous")

    def test_band_edge_belongs_to_the_lower_band(self):
        for label, upper in SEVERITY_BANDS[:-1]:
            self.assertEqual(severity_band(upper), label)

    def test_negative_energy_band_raises(self):
        with self.assertRaises(ValueError):
            severity_band(-1.0e-6)


class TestWithinLevel(unittest.TestCase):
    def test_below_level_passes(self):
        self.assertTrue(within_level(390.0, 400.0))

    def test_exactly_at_level_passes(self):
        self.assertTrue(within_level(400.0, 400.0))

    def test_above_level_fails(self):
        self.assertFalse(within_level(401.0, 400.0))

    def test_level_is_not_widened_by_the_tolerance(self):
        self.assertFalse(within_level(400.0 * 1.0001, 400.0))

    def test_non_finite_value_raises(self):
        with self.assertRaises(ValueError):
            within_level(float("inf"), 400.0)


class TestEvaluatePair(unittest.TestCase):
    def test_benign_pair_is_compliant(self):
        result = evaluate_pair(good_pair(), 400.0, 1.0e-3)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["differential_potential_v"], 120.0, places=9)

    def test_over_potential_pair_raises_that_finding(self):
        result = evaluate_pair(good_pair(potential_a_v=-2500.0), 400.0, 1.0e-3)
        self.assertFalse(result["potential_ok"])
        self.assertTrue(any("differential-potential" in f for f in result["findings"]))

    def test_over_energy_pair_raises_that_finding(self):
        result = evaluate_pair(
            good_pair(coated_area_m2=4.0, potential_a_v=-1500.0), 4000.0, 1.0e-4
        )
        self.assertFalse(result["energy_ok"])
        self.assertTrue(any("stored-discharge-energy" in f for f in result["findings"]))

    def test_over_energy_pair_reports_both_design_levers(self):
        result = evaluate_pair(
            good_pair(coated_area_m2=4.0, potential_a_v=-1500.0), 4000.0, 1.0e-4
        )
        self.assertIn("minimum_thickness_m", result)
        self.assertIn("maximum_area_m2", result)
        self.assertGreater(result["minimum_thickness_m"], good_pair()["dielectric_thickness_m"])

    def test_compliant_pair_carries_no_design_levers(self):
        result = evaluate_pair(good_pair(), 400.0, 1.0e-3)
        self.assertNotIn("minimum_thickness_m", result)

    def test_large_area_stores_more_than_small_area_at_equal_potential(self):
        small = evaluate_pair(good_pair(coated_area_m2=0.01), 4000.0, 1.0)
        large = evaluate_pair(good_pair(name="big", coated_area_m2=1.0), 4000.0, 1.0)
        self.assertGreater(large["stored_energy_j"], small["stored_energy_j"])

    def test_reduction_factor_is_reported_for_every_pair(self):
        result = evaluate_pair(good_pair(), 400.0, 1.0e-3)
        self.assertGreaterEqual(result["reduction_factor"], 0.0)

    def test_pair_without_name_raises(self):
        pair = good_pair()
        del pair["name"]
        with self.assertRaises(ValueError):
            evaluate_pair(pair, 400.0, 1.0e-3)

    def test_pair_missing_thickness_raises(self):
        pair = good_pair()
        del pair["dielectric_thickness_m"]
        with self.assertRaises(ValueError):
            evaluate_pair(pair, 400.0, 1.0e-3)

    def test_non_mapping_pair_raises(self):
        with self.assertRaises(ValueError):
            evaluate_pair(["blanket"], 400.0, 1.0e-3)

    def test_non_positive_limit_raises(self):
        with self.assertRaises(ValueError):
            evaluate_pair(good_pair(), 0.0, 1.0e-3)


class TestEvaluateMission(unittest.TestCase):
    def test_all_benign_pairs_meet_the_objective(self):
        summary = evaluate_mission(
            [good_pair(), good_pair(name="second-blanket")], LEVELS
        )
        self.assertTrue(summary["objective_met"])
        self.assertEqual(summary["compliant_count"], 2)

    def test_one_bad_pair_fails_the_objective(self):
        summary = evaluate_mission(
            [good_pair(), good_pair(name="hot-blanket", potential_a_v=-3000.0)], LEVELS
        )
        self.assertFalse(summary["objective_met"])
        self.assertEqual(summary["compliant_count"], 1)

    def test_worst_pair_is_identified_by_stored_energy(self):
        summary = evaluate_mission(
            [good_pair(), good_pair(name="wide-sheet", coated_area_m2=2.0)], LEVELS
        )
        self.assertEqual(summary["worst_pair"], "wide-sheet")

    def test_undeclared_energy_budget_is_a_finding_not_a_pass(self):
        summary = evaluate_mission(
            [good_pair()], {"differential_potential_limit_v": 400.0}
        )
        self.assertFalse(summary["levels_declared"])
        self.assertFalse(summary["objective_met"])
        self.assertTrue(summary["open_findings"])

    def test_undeclared_potential_limit_is_a_finding(self):
        summary = evaluate_mission([good_pair()], {"energy_budget_j": 1.0e-3})
        self.assertFalse(summary["objective_met"])

    def test_both_levels_missing_gives_two_findings(self):
        summary = evaluate_mission([good_pair()], {})
        self.assertEqual(len(summary["open_findings"]), 2)

    def test_empty_pair_list_raises(self):
        with self.assertRaises(ValueError):
            evaluate_mission([], LEVELS)

    def test_duplicate_pair_name_raises(self):
        with self.assertRaises(ValueError):
            evaluate_mission([good_pair(), good_pair()], LEVELS)

    def test_non_mapping_levels_raises(self):
        with self.assertRaises(ValueError):
            evaluate_mission([good_pair()], ["400"])

    def test_worst_reduction_factor_tracks_the_worst_pair(self):
        summary = evaluate_mission(
            [good_pair(), good_pair(name="wide-sheet", coated_area_m2=2.0)], LEVELS
        )
        self.assertAlmostEqual(
            summary["worst_reduction_factor"],
            summary["worst_energy_j"] / LEVELS["energy_budget_j"],
            places=12,
        )


if __name__ == "__main__":
    unittest.main()
