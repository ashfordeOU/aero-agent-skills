#!/usr/bin/env python3
"""Gate 3 contract test for e2001-level-two-material-criteria.

stdlib unittest, offline, deterministic.  Run: python3 test_...py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e2001_level_two_material_criteria_logic as L  # noqa: E402


def silver_air(**over):
    """Air-exposed silver: the conservative flight-representative record."""
    ds = {
        "dataset_id": "SEY-AG-AIR",
        "material": "silver",
        "surface_condition": "air-exposed",
        "sigma_max": 2.22,
        "e_max_ev": 165.0,
        "e1_ev": 28.0,
        "e2_ev": 2100.0,
        "temperature_c": 20.0,
        "energy_range_ev": (5.0, 3000.0),
        "threshold_energy_ev": 12.5,
    }
    ds.update(over)
    return ds


def silver_baked(**over):
    ds = silver_air(
        dataset_id="SEY-AG-BAKED",
        surface_condition="vacuum-baked",
        sigma_max=1.7,
        e_max_ev=200.0,
        e1_ev=44.0,
        e2_ev=1200.0,
    )
    ds.update(over)
    return ds


def alodine(**over):
    ds = {
        "dataset_id": "SEY-ALODINE",
        "material": "alodine-coated-aluminium",
        "surface_condition": "as-received",
        "sigma_max": 1.9,
        "e_max_ev": 300.0,
        "e1_ev": 57.0,
        "e2_ev": 2450.0,
        "temperature_c": 20.0,
        "energy_range_ev": (5.0, 3000.0),
        "threshold_energy_ev": 20.0,
    }
    ds.update(over)
    return ds


def target(**over):
    goal = {
        "material": "silver",
        "surface_condition": "air-exposed",
        "temperature_c": 20.0,
        "impact_energy_range_ev": (10.0, 2500.0),
    }
    goal.update(over)
    return goal


class TestNormalizeMaterial(unittest.TestCase):
    def test_known_material(self):
        self.assertEqual(L.normalize_material("silver"), "silver")

    def test_spelling_alias(self):
        self.assertEqual(L.normalize_material("Aluminum"), "aluminium")

    def test_symbol_alias_and_whitespace(self):
        self.assertEqual(L.normalize_material("  Ag "), "silver")

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            L.normalize_material("kapton")

    def test_blank_material_raises(self):
        with self.assertRaises(ValueError):
            L.normalize_material("  ")

    def test_non_string_material_raises(self):
        with self.assertRaises(ValueError):
            L.normalize_material(47)


class TestNormalizeSurfaceCondition(unittest.TestCase):
    def test_known_condition(self):
        self.assertEqual(L.normalize_surface_condition("vacuum-baked"), "vacuum-baked")

    def test_alias_is_folded(self):
        self.assertEqual(L.normalize_surface_condition("baked"), "vacuum-baked")

    def test_underscore_form(self):
        self.assertEqual(L.normalize_surface_condition("air_exposed"), "air-exposed")

    def test_unknown_condition_raises(self):
        with self.assertRaises(ValueError):
            L.normalize_surface_condition("polished")


class TestValidateYieldDataset(unittest.TestCase):
    def test_valid_record_is_normalized(self):
        record = L.validate_yield_dataset(silver_air(material="Ag"))
        self.assertEqual(record["material"], "silver")
        self.assertEqual(record["surface_condition"], "air-exposed")
        self.assertAlmostEqual(record["sigma_max"], 2.22, places=9)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            L.validate_yield_dataset(["SEY-AG-AIR"])

    def test_missing_key_raises(self):
        ds = silver_air()
        del ds["e_max_ev"]
        with self.assertRaises(ValueError):
            L.validate_yield_dataset(ds)

    def test_blank_dataset_id_raises(self):
        with self.assertRaises(ValueError):
            L.validate_yield_dataset(silver_air(dataset_id="   "))

    def test_peak_yield_at_or_below_unity_raises(self):
        with self.assertRaises(ValueError):
            L.validate_yield_dataset(silver_air(sigma_max=1.0))

    def test_first_crossover_above_peak_energy_raises(self):
        with self.assertRaises(ValueError):
            L.validate_yield_dataset(silver_air(e1_ev=400.0))

    def test_second_crossover_below_peak_energy_raises(self):
        with self.assertRaises(ValueError):
            L.validate_yield_dataset(silver_air(e2_ev=100.0))

    def test_negative_energy_raises(self):
        with self.assertRaises(ValueError):
            L.validate_yield_dataset(silver_air(e1_ev=-5.0))

    def test_energy_span_must_be_a_pair(self):
        with self.assertRaises(ValueError):
            L.validate_yield_dataset(silver_air(energy_range_ev=(5.0,)))

    def test_energy_span_must_increase(self):
        with self.assertRaises(ValueError):
            L.validate_yield_dataset(silver_air(energy_range_ev=(3000.0, 5.0)))

    def test_negative_energy_span_lower_bound_raises(self):
        with self.assertRaises(ValueError):
            L.validate_yield_dataset(silver_air(energy_range_ev=(-1.0, 3000.0)))

    def test_threshold_at_or_above_peak_energy_raises(self):
        with self.assertRaises(ValueError):
            L.validate_yield_dataset(silver_air(threshold_energy_ev=165.0))


class TestSecondaryYieldCurve(unittest.TestCase):
    def test_peak_value_is_reached_at_peak_energy(self):
        self.assertAlmostEqual(
            L.secondary_yield_at(silver_air(), 165.0), 2.22, places=9
        )

    def test_below_threshold_the_yield_vanishes(self):
        self.assertAlmostEqual(L.secondary_yield_at(silver_air(), 8.0), 0.0, places=12)

    def test_yield_exceeds_unity_above_the_declared_first_crossover(self):
        self.assertGreater(L.secondary_yield_at(silver_air(), 28.0), 1.0)

    def test_far_tail_falls_below_unity(self):
        self.assertLess(L.secondary_yield_at(silver_air(), 5000.0), 1.0)

    def test_negative_impact_energy_raises(self):
        with self.assertRaises(ValueError):
            L.secondary_yield_at(silver_air(), -1.0)

    def test_non_numeric_impact_energy_raises(self):
        with self.assertRaises(ValueError):
            L.secondary_yield_at(silver_air(), "30 eV")


class TestCrossoverEnergies(unittest.TestCase):
    def test_model_first_crossover_matches_the_published_record(self):
        e1, _ = L.unity_crossover_energies(silver_air())
        self.assertAlmostEqual(e1, 27.39, delta=0.05)

    def test_model_second_crossover_matches_the_published_record(self):
        _, e2 = L.unity_crossover_energies(silver_air())
        self.assertAlmostEqual(e2, 2096.99, delta=1.0)

    def test_yield_is_unity_at_both_model_crossovers(self):
        e1, e2 = L.unity_crossover_energies(silver_air())
        self.assertAlmostEqual(L.secondary_yield_at(silver_air(), e1), 1.0, places=6)
        self.assertAlmostEqual(L.secondary_yield_at(silver_air(), e2), 1.0, places=6)

    def test_crossovers_bracket_the_peak_energy(self):
        e1, e2 = L.unity_crossover_energies(silver_air())
        self.assertLess(e1, 165.0)
        self.assertGreater(e2, 165.0)


class TestCrossoverConsistency(unittest.TestCase):
    def test_published_record_is_consistent(self):
        report = L.check_crossover_consistency(silver_air())
        self.assertTrue(report["consistent"])
        self.assertLess(report["relative_deviation_e1"], 0.10)

    def test_alodine_record_is_consistent(self):
        self.assertTrue(L.check_crossover_consistency(alodine())["consistent"])

    def test_wrong_first_crossover_is_caught(self):
        report = L.check_crossover_consistency(silver_air(e1_ev=120.0))
        self.assertFalse(report["consistent"])
        self.assertGreater(report["relative_deviation_e1"], 0.10)

    def test_tolerance_boundary_is_inclusive(self):
        report = L.check_crossover_consistency(silver_air())
        tight = max(report["relative_deviation_e1"], report["relative_deviation_e2"])
        self.assertTrue(
            L.check_crossover_consistency(silver_air(), tolerance=tight)["consistent"]
        )

    def test_non_positive_tolerance_raises(self):
        with self.assertRaises(ValueError):
            L.check_crossover_consistency(silver_air(), tolerance=0.0)


class TestConditionRepresentativeness(unittest.TestCase):
    def test_same_condition_is_representative(self):
        self.assertTrue(L.condition_is_representative("air-exposed", "air-exposed"))

    def test_dirtier_dataset_is_representative(self):
        self.assertTrue(L.condition_is_representative("as-received", "vacuum-baked"))

    def test_cleaner_dataset_is_not_representative(self):
        self.assertFalse(L.condition_is_representative("atomically-clean", "air-exposed"))

    def test_unknown_condition_raises(self):
        with self.assertRaises(ValueError):
            L.condition_is_representative("air-exposed", "sandblasted")


class TestEnergyCoverage(unittest.TestCase):
    def test_covered_range(self):
        self.assertTrue(L.covers_energy_range(silver_air(), 10.0, 2500.0))

    def test_uncovered_upper_end(self):
        self.assertFalse(L.covers_energy_range(silver_air(), 10.0, 4000.0))

    def test_uncovered_lower_end(self):
        self.assertFalse(L.covers_energy_range(silver_air(), 1.0, 2500.0))

    def test_exact_bounds_are_inclusive(self):
        self.assertTrue(L.covers_energy_range(silver_air(), 5.0, 3000.0))

    def test_one_ulp_outside_the_upper_bound_is_absorbed(self):
        high = math.nextafter(3000.0, 4000.0)
        self.assertGreater(high, 3000.0)
        self.assertTrue(L.covers_energy_range(silver_air(), 5.0, high))

    def test_negative_lower_bound_raises(self):
        with self.assertRaises(ValueError):
            L.covers_energy_range(silver_air(), -1.0, 2500.0)

    def test_non_increasing_range_raises(self):
        with self.assertRaises(ValueError):
            L.covers_energy_range(silver_air(), 2500.0, 10.0)


class TestTemperatureRepresentativeness(unittest.TestCase):
    def test_inside_the_window(self):
        self.assertTrue(L.temperature_is_representative(silver_air(), 30.0))

    def test_outside_the_window(self):
        self.assertFalse(L.temperature_is_representative(silver_air(), 120.0))

    def test_exact_window_edge_is_accepted(self):
        self.assertTrue(L.temperature_is_representative(silver_air(temperature_c=60.0), 20.0))

    def test_one_ulp_outside_the_window_is_absorbed(self):
        hot = math.nextafter(60.0, 61.0)
        self.assertGreater(abs(hot - 20.0), 40.0)
        self.assertTrue(L.temperature_is_representative(silver_air(temperature_c=hot), 20.0))

    def test_non_positive_window_raises(self):
        with self.assertRaises(ValueError):
            L.temperature_is_representative(silver_air(), 20.0, window_c=-5.0)


class TestScreenYieldDatasets(unittest.TestCase):
    def test_matching_dataset_is_accepted(self):
        report = L.screen_yield_datasets([silver_air()], target())
        self.assertEqual([r["dataset_id"] for r in report["accepted"]], ["SEY-AG-AIR"])
        self.assertEqual(report["rejected"], [])

    def test_material_mismatch_is_rejected(self):
        report = L.screen_yield_datasets([alodine()], target())
        self.assertIn("electrode-material-mismatch", report["rejected"][0]["reasons"])

    def test_cleaner_surface_is_rejected(self):
        report = L.screen_yield_datasets([silver_baked()], target())
        self.assertIn(
            "surface-condition-cleaner-than-flight", report["rejected"][0]["reasons"]
        )

    def test_uncovered_energy_range_is_rejected(self):
        report = L.screen_yield_datasets(
            [silver_air(energy_range_ev=(50.0, 400.0))], target()
        )
        self.assertIn("impact-energy-range-not-covered", report["rejected"][0]["reasons"])

    def test_temperature_outside_window_is_rejected(self):
        report = L.screen_yield_datasets([silver_air(temperature_c=150.0)], target())
        self.assertIn("temperature-outside-window", report["rejected"][0]["reasons"])

    def test_several_reasons_are_reported_together(self):
        candidate = silver_air(
            material="gold", surface_condition="atomically-clean", temperature_c=200.0
        )
        report = L.screen_yield_datasets([candidate], target())
        self.assertEqual(len(report["rejected"][0]["reasons"]), 3)

    def test_widened_temperature_window_admits_a_warm_dataset(self):
        report = L.screen_yield_datasets(
            [silver_air(temperature_c=90.0)], target(temperature_window_c=100.0)
        )
        self.assertEqual(len(report["accepted"]), 1)

    def test_empty_candidate_list_raises(self):
        with self.assertRaises(ValueError):
            L.screen_yield_datasets([], target())

    def test_non_list_candidates_raise(self):
        with self.assertRaises(ValueError):
            L.screen_yield_datasets(silver_air(), target())

    def test_duplicate_dataset_id_raises(self):
        with self.assertRaises(ValueError):
            L.screen_yield_datasets([silver_air(), silver_air()], target())

    def test_non_mapping_target_raises(self):
        with self.assertRaises(ValueError):
            L.screen_yield_datasets([silver_air()], "silver")

    def test_target_missing_key_raises(self):
        goal = target()
        del goal["temperature_c"]
        with self.assertRaises(ValueError):
            L.screen_yield_datasets([silver_air()], goal)

    def test_target_range_must_be_a_pair(self):
        with self.assertRaises(ValueError):
            L.screen_yield_datasets([silver_air()], target(impact_energy_range_ev=(10.0,)))


class TestSelectYieldDataset(unittest.TestCase):
    def test_lowest_first_crossover_wins(self):
        low = silver_air(dataset_id="SEY-AG-LOW", e1_ev=22.0)
        report = L.select_yield_dataset([silver_air(), low], target())
        self.assertEqual(report["selected"]["dataset_id"], "SEY-AG-LOW")
        self.assertEqual(report["ranked"], ["SEY-AG-LOW", "SEY-AG-AIR"])

    def test_equal_first_crossover_breaks_on_peak_yield(self):
        hot = silver_air(dataset_id="SEY-AG-HOT", sigma_max=2.9)
        report = L.select_yield_dataset([silver_air(), hot], target())
        self.assertEqual(report["selected"]["dataset_id"], "SEY-AG-HOT")

    def test_full_tie_breaks_alphabetically(self):
        twin = silver_air(dataset_id="SEY-AG-AAA")
        report = L.select_yield_dataset([silver_air(), twin], target())
        self.assertEqual(report["selected"]["dataset_id"], "SEY-AG-AAA")

    def test_no_qualifying_dataset_requires_a_fallback(self):
        report = L.select_yield_dataset([alodine()], target())
        self.assertIsNone(report["selected"])
        self.assertTrue(report["fallback_required"])
        self.assertIn("no-representative-yield-dataset", report["findings"])


class TestAssessMaterialCriteria(unittest.TestCase):
    def test_clean_selection_is_compliant(self):
        report = L.assess_material_criteria([silver_air(), silver_baked()], target())
        self.assertEqual(report["selected_dataset_id"], "SEY-AG-AIR")
        self.assertTrue(report["compliant"])
        self.assertTrue(report["crossover_consistency"]["consistent"])
        self.assertEqual(len(report["rejected"]), 1)

    def test_inconsistent_crossover_is_a_finding(self):
        report = L.assess_material_criteria([silver_air(e1_ev=120.0)], target())
        self.assertIn(
            "declared-crossover-energies-inconsistent-with-curve", report["findings"]
        )
        self.assertFalse(report["compliant"])

    def test_fallback_path_reports_no_selection(self):
        report = L.assess_material_criteria([alodine()], target())
        self.assertIsNone(report["selected_dataset_id"])
        self.assertTrue(report["fallback_required"])
        self.assertIsNone(report["crossover_consistency"])
        self.assertFalse(report["compliant"])

    def test_alodine_surface_selects_its_own_dataset(self):
        goal = target(material="alodine-coated-aluminium", surface_condition="as-received")
        report = L.assess_material_criteria([silver_air(), alodine()], goal)
        self.assertEqual(report["selected_dataset_id"], "SEY-ALODINE")
        self.assertTrue(report["compliant"])


if __name__ == "__main__":
    unittest.main()
