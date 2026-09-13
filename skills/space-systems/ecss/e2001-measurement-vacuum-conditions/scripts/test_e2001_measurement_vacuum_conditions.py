#!/usr/bin/env python3
"""Gate 3 contract test for e2001-measurement-vacuum-conditions.

stdlib unittest, offline, deterministic. Run: python3 test_e2001_measurement_vacuum_conditions.py
"""

import math
import unittest

from e2001_measurement_vacuum_conditions_logic import (
    ACCEPTABLE_REGIMES,
    BAKEOUT_MIN_DURATION_H,
    BAKEOUT_MIN_TEMPERATURE_K,
    CONTINUUM_FLOW_KNUDSEN,
    DEFAULT_TEMPERATURE_K,
    MOLECULAR_FLOW_KNUDSEN,
    assess_vacuum_conditions,
    audit_partial_pressures,
    bakeout_is_adequate,
    categorize_vacuum_regime,
    dominant_species,
    flow_regime,
    impingement_rate_per_m2_s,
    knudsen_number,
    mean_free_path_m,
    monolayer_formation_time_s,
    regime_is_acceptable,
    screen_pressure_log,
    species_molar_mass,
)


def near(test, got, want, rel=1e-9):
    test.assertAlmostEqual(got, want, delta=abs(want) * rel + 1e-300)


def good_facility(**over):
    facility = {
        "id": "SEY-UHV-BENCH-2",
        "pressure_log_pa": [6.0e-9, 8.0e-9, 1.0e-8, 7.0e-9],
        "pressure_limit_pa": 2.0e-8,
        "temperature_k": 295.0,
        "chamber_length_m": 0.8,
        "measurement_duration_s": 1800.0,
        "monolayer_margin": 3.0,
        "sticking_coefficient": 1.0,
        "residual_gas_partial_pa": {
            "hydrogen": 6.0e-9,
            "water": 2.0e-9,
            "carbon-monoxide": 1.5e-9,
            "methane": 2.0e-10,
        },
        "bakeout": {"temperature_k": 423.15, "duration_h": 24.0},
    }
    facility.update(over)
    return facility


class TestRegimeLadder(unittest.TestCase):
    def test_ladder_names(self):
        self.assertEqual(categorize_vacuum_regime(2.0e5), "ambient")
        self.assertEqual(categorize_vacuum_regime(5.0e3), "low-vacuum")
        self.assertEqual(categorize_vacuum_regime(1.0), "medium-vacuum")
        self.assertEqual(categorize_vacuum_regime(1.0e-3), "high-vacuum")
        self.assertEqual(categorize_vacuum_regime(1.0e-8), "ultra-high-vacuum")
        self.assertEqual(categorize_vacuum_regime(1.0e-12), "extreme-high-vacuum")

    def test_bound_belongs_to_the_cleaner_regime(self):
        self.assertEqual(categorize_vacuum_regime(1.0e-1), "high-vacuum")
        self.assertEqual(categorize_vacuum_regime(1.0e2), "medium-vacuum")
        self.assertEqual(categorize_vacuum_regime(1.0e-6), "ultra-high-vacuum")

    def test_bound_reached_by_arithmetic_is_not_demoted(self):
        drifted = math.fsum([1.0e-1 / 3.0] * 3)
        self.assertEqual(categorize_vacuum_regime(drifted), "high-vacuum")

    def test_zero_pressure_raises(self):
        with self.assertRaises(ValueError):
            categorize_vacuum_regime(0.0)

    def test_negative_pressure_raises(self):
        with self.assertRaises(ValueError):
            categorize_vacuum_regime(-1.0e-6)

    def test_non_finite_pressure_raises(self):
        with self.assertRaises(ValueError):
            categorize_vacuum_regime(math.inf)

    def test_non_numeric_pressure_raises(self):
        with self.assertRaises(ValueError):
            categorize_vacuum_regime("1e-6")

    def test_clause_floor_is_high_vacuum(self):
        for regime in ACCEPTABLE_REGIMES:
            self.assertTrue(regime_is_acceptable(regime))
        for regime in ("ambient", "low-vacuum", "medium-vacuum"):
            self.assertFalse(regime_is_acceptable(regime))

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            regime_is_acceptable("soft-vacuum")

    def test_non_string_regime_raises(self):
        with self.assertRaises(ValueError):
            regime_is_acceptable(7)


class TestKineticQuantities(unittest.TestCase):
    def test_mean_free_path_is_inverse_in_pressure(self):
        a = mean_free_path_m(1.0e-4)
        b = mean_free_path_m(1.0e-5)
        near(self, b, 10.0 * a)

    def test_mean_free_path_magnitude_at_reference_pressure(self):
        self.assertAlmostEqual(mean_free_path_m(1.0e-4), 66.5, delta=2.0)

    def test_mean_free_path_grows_with_temperature(self):
        cold = mean_free_path_m(1.0e-4, 100.0)
        hot = mean_free_path_m(1.0e-4, 400.0)
        self.assertGreater(hot, cold)
        near(self, hot / cold, 4.0)

    def test_mean_free_path_rejects_bad_pressure(self):
        with self.assertRaises(ValueError):
            mean_free_path_m(0.0)

    def test_mean_free_path_rejects_bad_temperature(self):
        with self.assertRaises(ValueError):
            mean_free_path_m(1.0e-6, -5.0)

    def test_mean_free_path_rejects_bad_diameter(self):
        with self.assertRaises(ValueError):
            mean_free_path_m(1.0e-6, DEFAULT_TEMPERATURE_K, 0.0)

    def test_knudsen_number_is_a_ratio(self):
        near(self, knudsen_number(8.0, 0.4), 20.0)

    def test_knudsen_rejects_zero_length(self):
        with self.assertRaises(ValueError):
            knudsen_number(8.0, 0.0)

    def test_flow_regime_bands(self):
        self.assertEqual(flow_regime(1.0e3), "free-molecular")
        self.assertEqual(flow_regime(1.0), "transitional")
        self.assertEqual(flow_regime(1.0e-4), "continuum")

    def test_flow_regime_boundaries_are_inclusive(self):
        self.assertEqual(flow_regime(MOLECULAR_FLOW_KNUDSEN), "free-molecular")
        self.assertEqual(flow_regime(CONTINUUM_FLOW_KNUDSEN), "continuum")

    def test_flow_regime_rejects_zero(self):
        with self.assertRaises(ValueError):
            flow_regime(0.0)


class TestSurfaceKinetics(unittest.TestCase):
    def test_known_species_molar_mass(self):
        near(self, species_molar_mass("water"), 18.015e-3)

    def test_unknown_species_raises(self):
        with self.assertRaises(ValueError):
            species_molar_mass("xenon")

    def test_impingement_rate_is_linear_in_pressure(self):
        a = impingement_rate_per_m2_s(1.0e-6, 295.0, "water")
        b = impingement_rate_per_m2_s(2.0e-6, 295.0, "water")
        near(self, b, 2.0 * a)

    def test_lighter_species_impinges_faster(self):
        light = impingement_rate_per_m2_s(1.0e-6, 295.0, "hydrogen")
        heavy = impingement_rate_per_m2_s(1.0e-6, 295.0, "water")
        self.assertGreater(light, heavy)
        near(self, light / heavy, math.sqrt(18.015e-3 / 2.016e-3))

    def test_impingement_rejects_unknown_species(self):
        with self.assertRaises(ValueError):
            impingement_rate_per_m2_s(1.0e-6, 295.0, "krypton")

    def test_monolayer_time_is_inverse_in_pressure(self):
        a = monolayer_formation_time_s(1.0e-6)
        b = monolayer_formation_time_s(1.0e-8)
        near(self, b, 100.0 * a)

    def test_monolayer_time_magnitude_at_reference_pressure(self):
        self.assertAlmostEqual(monolayer_formation_time_s(1.0e-4), 2.76, delta=0.3)

    def test_partial_sticking_lengthens_monolayer_time(self):
        full = monolayer_formation_time_s(1.0e-6, 295.0, "water", 1.0)
        half = monolayer_formation_time_s(1.0e-6, 295.0, "water", 0.5)
        near(self, half, 2.0 * full)

    def test_zero_sticking_raises(self):
        with self.assertRaises(ValueError):
            monolayer_formation_time_s(1.0e-6, 295.0, "water", 0.0)

    def test_sticking_above_unity_raises(self):
        with self.assertRaises(ValueError):
            monolayer_formation_time_s(1.0e-6, 295.0, "water", 1.5)

    def test_non_numeric_sticking_raises(self):
        with self.assertRaises(ValueError):
            monolayer_formation_time_s(1.0e-6, 295.0, "water", "unity")

    def test_zero_site_density_raises(self):
        with self.assertRaises(ValueError):
            monolayer_formation_time_s(1.0e-6, 295.0, "water", 1.0, 0.0)


class TestResidualGasInventory(unittest.TestCase):
    def test_dominant_species_is_the_largest_partial(self):
        partials = {"hydrogen": 6.0e-9, "water": 2.0e-9, "methane": 1.0e-10}
        self.assertEqual(dominant_species(partials), "hydrogen")

    def test_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            dominant_species({})

    def test_negative_partial_raises(self):
        with self.assertRaises(ValueError):
            dominant_species({"water": -1.0e-9})

    def test_non_numeric_partial_raises(self):
        with self.assertRaises(ValueError):
            dominant_species({"water": "2e-9"})

    def test_unknown_species_in_inventory_raises(self):
        with self.assertRaises(ValueError):
            dominant_species({"helium": 1.0e-9})

    def test_audit_reports_unaccounted_pressure(self):
        partials = {"hydrogen": 4.0e-9, "water": 2.0e-9}
        report = audit_partial_pressures(partials, 1.0e-8)
        near(self, report["listed_total_pa"], 6.0e-9)
        near(self, report["unaccounted_pa"], 4.0e-9)
        self.assertFalse(report["inventory_exceeds_total"])

    def test_audit_flags_inventory_above_total(self):
        partials = {"hydrogen": 9.0e-9, "water": 4.0e-9}
        report = audit_partial_pressures(partials, 1.0e-8)
        self.assertTrue(report["inventory_exceeds_total"])

    def test_inventory_equal_to_total_is_not_flagged(self):
        partials = {"hydrogen": 5.0e-9, "water": 3.0e-9, "carbon-monoxide": 2.0e-9}
        report = audit_partial_pressures(partials, 1.0e-8)
        self.assertFalse(report["inventory_exceeds_total"])
        near(self, report["listed_total_pa"], 1.0e-8)

    def test_hydrocarbon_fraction_counts_only_hydrocarbons(self):
        partials = {
            "hydrogen": 7.0e-9,
            "methane": 2.0e-10,
            "pump-oil-hydrocarbon": 3.0e-10,
        }
        report = audit_partial_pressures(partials, 1.0e-8)
        near(self, report["hydrocarbon_pa"], 5.0e-10)
        near(self, report["hydrocarbon_fraction"], 0.05)

    def test_audit_rejects_zero_total(self):
        with self.assertRaises(ValueError):
            audit_partial_pressures({"water": 1.0e-9}, 0.0)


class TestPressureLog(unittest.TestCase):
    def test_log_statistics(self):
        report = screen_pressure_log([1.0e-8, 2.0e-8, 4.0e-9], 5.0e-8)
        near(self, report["peak_pa"], 2.0e-8)
        near(self, report["floor_pa"], 4.0e-9)
        self.assertEqual(report["samples"], 3)
        self.assertTrue(report["within_limit"])

    def test_excursions_are_counted(self):
        report = screen_pressure_log([1.0e-8, 9.0e-8, 1.2e-7], 5.0e-8)
        self.assertEqual(report["excursion_count"], 2)
        self.assertFalse(report["within_limit"])

    def test_reading_exactly_at_the_limit_is_not_an_excursion(self):
        limit = 5.0e-8
        drifted = math.fsum([limit / 3.0] * 3)
        report = screen_pressure_log([1.0e-8, drifted], limit)
        self.assertEqual(report["excursion_count"], 0)
        self.assertTrue(report["within_limit"])

    def test_swing_is_reported_in_decades(self):
        report = screen_pressure_log([1.0e-9, 1.0e-7], 1.0e-6)
        near(self, report["swing_decades"], 2.0)

    def test_empty_log_raises(self):
        with self.assertRaises(ValueError):
            screen_pressure_log([], 1.0e-6)

    def test_non_sequence_log_raises(self):
        with self.assertRaises(ValueError):
            screen_pressure_log({"p": 1.0e-8}, 1.0e-6)

    def test_non_positive_reading_raises(self):
        with self.assertRaises(ValueError):
            screen_pressure_log([1.0e-8, 0.0], 1.0e-6)


class TestBakeout(unittest.TestCase):
    def test_absent_record_is_not_adequate(self):
        self.assertFalse(bakeout_is_adequate(None))

    def test_cold_bakeout_is_not_adequate(self):
        self.assertFalse(
            bakeout_is_adequate({"temperature_k": 330.0, "duration_h": 48.0})
        )

    def test_short_bakeout_is_not_adequate(self):
        self.assertFalse(
            bakeout_is_adequate({"temperature_k": 423.15, "duration_h": 2.0})
        )

    def test_exact_floor_is_adequate(self):
        record = {
            "temperature_k": BAKEOUT_MIN_TEMPERATURE_K,
            "duration_h": BAKEOUT_MIN_DURATION_H,
        }
        self.assertTrue(bakeout_is_adequate(record))

    def test_generous_bakeout_is_adequate(self):
        self.assertTrue(
            bakeout_is_adequate({"temperature_k": 473.15, "duration_h": 36.0})
        )

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            bakeout_is_adequate("24h at 150C")

    def test_missing_duration_raises(self):
        with self.assertRaises(ValueError):
            bakeout_is_adequate({"temperature_k": 423.15})


class TestAssessment(unittest.TestCase):
    def test_good_facility_is_compliant(self):
        report = assess_vacuum_conditions(good_facility())
        self.assertTrue(report["compliant"], report["findings"])
        self.assertEqual(report["regime"], "ultra-high-vacuum")
        self.assertEqual(report["flow_regime"], "free-molecular")
        self.assertEqual(report["dominant_species"], "hydrogen")

    def test_working_pressure_is_the_log_peak(self):
        report = assess_vacuum_conditions(good_facility())
        near(self, report["working_pressure_pa"], 1.0e-8)

    def test_medium_vacuum_run_is_flagged(self):
        facility = good_facility(
            pressure_log_pa=[1.0, 2.0], pressure_limit_pa=5.0, chamber_length_m=0.8
        )
        report = assess_vacuum_conditions(facility)
        self.assertIn("regime-above-high-vacuum", report["finding_codes"])
        self.assertIn("beam-path-not-collisionless", report["finding_codes"])

    def test_pressure_excursion_is_flagged(self):
        facility = good_facility(pressure_limit_pa=7.0e-9)
        report = assess_vacuum_conditions(facility)
        self.assertIn("pressure-excursion", report["finding_codes"])

    def test_recontamination_risk_is_flagged_for_a_long_run(self):
        facility = good_facility(measurement_duration_s=1.0e5)
        report = assess_vacuum_conditions(facility)
        self.assertIn("surface-recontamination-risk", report["finding_codes"])

    def test_monolayer_time_exactly_covering_the_run_is_compliant(self):
        facility = good_facility()
        monolayer = monolayer_formation_time_s(
            1.0e-8, facility["temperature_k"], "hydrogen", 1.0
        )
        facility["measurement_duration_s"] = monolayer / 3.0
        facility["monolayer_margin"] = 3.0
        report = assess_vacuum_conditions(facility)
        self.assertNotIn("surface-recontamination-risk", report["finding_codes"])
        near(self, report["monolayer_formation_time_s"], monolayer)

    def test_inconsistent_inventory_is_flagged(self):
        facility = good_facility(
            residual_gas_partial_pa={"hydrogen": 9.0e-9, "water": 5.0e-9}
        )
        report = assess_vacuum_conditions(facility)
        self.assertIn("partial-pressure-inventory-inconsistent", report["finding_codes"])

    def test_hydrocarbon_excess_is_flagged(self):
        facility = good_facility(
            residual_gas_partial_pa={
                "hydrogen": 5.0e-9,
                "pump-oil-hydrocarbon": 2.0e-9,
            }
        )
        report = assess_vacuum_conditions(facility)
        self.assertIn("hydrocarbon-partial-pressure-excess", report["finding_codes"])

    def test_hydrocarbon_fraction_exactly_at_the_limit_is_compliant(self):
        facility = good_facility(
            residual_gas_partial_pa={
                "hydrogen": 6.0e-9,
                "water": 2.0e-9,
                "methane": 5.0e-10,
            },
            hydrocarbon_fraction_limit=0.05,
        )
        report = assess_vacuum_conditions(facility)
        self.assertNotIn(
            "hydrocarbon-partial-pressure-excess", report["finding_codes"]
        )
        near(self, report["hydrocarbon_fraction"], 0.05)

    def test_missing_bakeout_is_flagged(self):
        report = assess_vacuum_conditions(good_facility(bakeout=None))
        self.assertIn("bakeout-not-substantiated", report["finding_codes"])
        self.assertFalse(report["compliant"])

    def test_missing_chamber_length_raises(self):
        facility = good_facility()
        del facility["chamber_length_m"]
        with self.assertRaises(ValueError):
            assess_vacuum_conditions(facility)

    def test_missing_duration_raises(self):
        facility = good_facility()
        del facility["measurement_duration_s"]
        with self.assertRaises(ValueError):
            assess_vacuum_conditions(facility)

    def test_missing_pressure_limit_raises(self):
        facility = good_facility()
        del facility["pressure_limit_pa"]
        with self.assertRaises(ValueError):
            assess_vacuum_conditions(facility)

    def test_non_mapping_facility_raises(self):
        with self.assertRaises(ValueError):
            assess_vacuum_conditions(["SEY-UHV-BENCH-2"])

    def test_report_carries_the_derived_quantities(self):
        report = assess_vacuum_conditions(good_facility())
        for key in (
            "facility",
            "working_pressure_pa",
            "regime",
            "mean_free_path_m",
            "knudsen_number",
            "flow_regime",
            "dominant_species",
            "monolayer_formation_time_s",
            "required_monolayer_time_s",
            "hydrocarbon_fraction",
            "pressure_log",
            "findings",
            "finding_codes",
            "compliant",
        ):
            self.assertIn(key, report)


if __name__ == "__main__":
    unittest.main()
