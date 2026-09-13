#!/usr/bin/env python3
"""Contract test for the cycling environment preference leaf (offline)."""

import copy
import unittest

from e2008_thermal_cycle_acceptance_general_logic import (
    AMBIENT_JUSTIFIED,
    AMBIENT_NOT_JUSTIFIED,
    CHAMBER_ENVIRONMENTS,
    CONDUCTION_REGIMES,
    CONTINUUM_KNUDSEN,
    ENVIRONMENT_ATMOSPHERIC,
    ENVIRONMENT_RAREFIED,
    ENVIRONMENT_VACUUM,
    FREE_MOLECULAR_KNUDSEN,
    MAX_OXYGEN_VOLUME_FRACTION,
    MIN_FROST_POINT_MARGIN_K,
    OXIDATION_ONSET_K,
    RAREFIED_CEILING_PA,
    STANDARD_ATMOSPHERE_PA,
    VACUUM_CEILING_PA,
    VACUUM_PREFERENCE_MET,
    assess_cycling_environment,
    chamber_environment,
    frost_margin_adequate,
    frost_point_margin_k,
    gas_conduction_is_negligible,
    gas_conduction_regime,
    is_preferred_environment,
    knudsen_number,
    missing_gas_evidence,
    molecular_mean_free_path_m,
    oxidation_exposure,
    requires_justification,
    validate_pressure_pa,
)

VACUUM_CASE = {
    "chamber_pressure_pa": 5.0e-4,
    "cold_dwell_k": 173.15,
    "hot_dwell_k": 373.15,
    "characteristic_gap_m": 0.01,
}

PURGE_CASE = {
    "chamber_pressure_pa": 1000.0,
    "cold_dwell_k": 173.15,
    "hot_dwell_k": 373.15,
    "characteristic_gap_m": 0.01,
    "gas_frost_point_k": 150.0,
    "oxygen_volume_fraction": 1.0e-4,
    "justification_recorded": True,
    "profile_compensated_for_gas_conduction": True,
}

AIR_CASE = {
    "chamber_pressure_pa": STANDARD_ATMOSPHERE_PA,
    "cold_dwell_k": 173.15,
    "hot_dwell_k": 373.15,
    "characteristic_gap_m": 0.01,
    "gas_frost_point_k": 273.15,
    "oxygen_volume_fraction": 0.21,
    "justification_recorded": False,
    "profile_compensated_for_gas_conduction": False,
}


def _vacuum(**overrides):
    case = copy.deepcopy(VACUUM_CASE)
    case.update(overrides)
    return case


def _purge(**overrides):
    case = copy.deepcopy(PURGE_CASE)
    case.update(overrides)
    return case


class EnvironmentNamingTests(unittest.TestCase):
    def test_a_hard_vacuum_is_the_preferred_environment(self):
        self.assertEqual(chamber_environment(1.0e-5), ENVIRONMENT_VACUUM)
        self.assertTrue(is_preferred_environment(1.0e-5))

    def test_the_vacuum_ceiling_itself_still_counts_as_vacuum(self):
        self.assertEqual(chamber_environment(VACUUM_CEILING_PA), ENVIRONMENT_VACUUM)

    def test_a_thin_gas_fill_is_rarefied_not_vacuum(self):
        self.assertEqual(chamber_environment(1.0), ENVIRONMENT_RAREFIED)
        self.assertFalse(is_preferred_environment(1.0))

    def test_the_rarefied_ceiling_itself_is_still_rarefied(self):
        self.assertEqual(chamber_environment(RAREFIED_CEILING_PA), ENVIRONMENT_RAREFIED)

    def test_room_air_is_the_ambient_atmosphere_case(self):
        self.assertEqual(
            chamber_environment(STANDARD_ATMOSPHERE_PA), ENVIRONMENT_ATMOSPHERIC
        )

    def test_every_named_environment_is_reachable_from_a_pressure(self):
        reached = {
            chamber_environment(1.0e-6),
            chamber_environment(10.0),
            chamber_environment(STANDARD_ATMOSPHERE_PA),
        }
        self.assertEqual(reached, set(CHAMBER_ENVIRONMENTS))

    def test_only_a_departure_from_vacuum_has_to_be_argued(self):
        self.assertFalse(requires_justification(1.0e-5))
        self.assertTrue(requires_justification(STANDARD_ATMOSPHERE_PA))

    def test_a_zero_pressure_reading_is_refused(self):
        with self.assertRaises(ValueError):
            validate_pressure_pa(0.0)

    def test_a_negative_pressure_reading_is_refused(self):
        with self.assertRaises(ValueError):
            chamber_environment(-1.0)

    def test_a_non_numeric_pressure_reading_is_refused(self):
        with self.assertRaises(ValueError):
            validate_pressure_pa("1e-5 mbar")


class MeanFreePathTests(unittest.TestCase):
    def test_room_air_has_a_mean_free_path_of_tens_of_nanometres(self):
        path = molecular_mean_free_path_m(STANDARD_ATMOSPHERE_PA, 293.15)
        self.assertGreater(path, 1.0e-8)
        self.assertLess(path, 1.0e-6)

    def test_halving_the_pressure_doubles_the_mean_free_path(self):
        dense = molecular_mean_free_path_m(2000.0, 293.15)
        thin = molecular_mean_free_path_m(1000.0, 293.15)
        self.assertAlmostEqual(thin / dense, 2.0, places=9)

    def test_the_path_grows_in_proportion_to_temperature(self):
        cold = molecular_mean_free_path_m(1000.0, 150.0)
        hot = molecular_mean_free_path_m(1000.0, 300.0)
        self.assertAlmostEqual(hot / cold, 2.0, places=9)

    def test_a_larger_molecule_shortens_the_path(self):
        small = molecular_mean_free_path_m(1000.0, 293.15, 3.0e-10)
        large = molecular_mean_free_path_m(1000.0, 293.15, 6.0e-10)
        self.assertAlmostEqual(small / large, 4.0, places=9)

    def test_a_vacuum_chamber_has_a_path_of_metres(self):
        path = molecular_mean_free_path_m(5.0e-4, 173.15)
        self.assertGreater(path, 1.0)

    def test_a_zero_molecule_diameter_is_refused(self):
        with self.assertRaises(ValueError):
            molecular_mean_free_path_m(1000.0, 293.15, 0.0)


class ConductionRegimeTests(unittest.TestCase):
    def test_the_knudsen_number_is_the_path_over_the_gap(self):
        self.assertAlmostEqual(knudsen_number(0.02, 0.01), 2.0, places=12)

    def test_a_zero_gap_cannot_carry_a_knudsen_number(self):
        with self.assertRaises(ValueError):
            knudsen_number(0.02, 0.0)

    def test_a_dense_gas_conducts_in_the_continuum_regime(self):
        self.assertEqual(gas_conduction_regime(1.0e-5), "continuum")

    def test_the_continuum_boundary_itself_is_continuum(self):
        self.assertEqual(gas_conduction_regime(CONTINUUM_KNUDSEN), "continuum")

    def test_the_free_molecular_boundary_itself_is_free_molecular(self):
        self.assertEqual(
            gas_conduction_regime(FREE_MOLECULAR_KNUDSEN), "free-molecular"
        )

    def test_a_middling_knudsen_number_is_transitional(self):
        self.assertEqual(gas_conduction_regime(1.0), "transitional")

    def test_only_the_free_molecular_regime_lets_the_gas_be_ignored(self):
        self.assertTrue(gas_conduction_is_negligible("free-molecular"))
        self.assertFalse(gas_conduction_is_negligible("continuum"))
        self.assertFalse(gas_conduction_is_negligible("transitional"))

    def test_every_regime_name_is_declared(self):
        for regime in CONDUCTION_REGIMES:
            self.assertIsInstance(gas_conduction_is_negligible(regime), bool)

    def test_an_unknown_regime_name_is_refused(self):
        with self.assertRaises(ValueError):
            gas_conduction_is_negligible("slip-flow")


class FrostAndOxidationTests(unittest.TestCase):
    def test_a_dry_purge_leaves_a_wide_frost_margin(self):
        self.assertAlmostEqual(frost_point_margin_k(173.15, 150.0), 23.15, places=9)
        self.assertTrue(frost_margin_adequate(173.15, 150.0))

    def test_a_margin_exactly_on_the_floor_is_adequate(self):
        cold = 173.15
        frost = cold - MIN_FROST_POINT_MARGIN_K
        self.assertAlmostEqual(
            frost_point_margin_k(cold, frost), MIN_FROST_POINT_MARGIN_K, places=9
        )
        self.assertTrue(frost_margin_adequate(cold, frost))

    def test_a_cold_dwell_below_the_frost_point_has_a_negative_margin(self):
        self.assertLess(frost_point_margin_k(173.15, 273.15), 0.0)
        self.assertFalse(frost_margin_adequate(173.15, 273.15))

    def test_a_zero_frost_point_is_refused(self):
        with self.assertRaises(ValueError):
            frost_point_margin_k(173.15, 0.0)

    def test_air_at_the_hot_dwell_tarnishes_metallisation(self):
        exposure = oxidation_exposure(373.15, 0.21)
        self.assertTrue(exposure["at_risk"])
        self.assertTrue(exposure["above_oxidation_onset"])
        self.assertTrue(exposure["oxygen_above_ceiling"])

    def test_an_inert_purge_at_the_hot_dwell_is_not_at_risk(self):
        exposure = oxidation_exposure(373.15, 1.0e-5)
        self.assertFalse(exposure["at_risk"])
        self.assertFalse(exposure["oxygen_above_ceiling"])

    def test_oxygen_exactly_on_the_ceiling_is_not_above_it(self):
        exposure = oxidation_exposure(373.15, MAX_OXYGEN_VOLUME_FRACTION)
        self.assertFalse(exposure["oxygen_above_ceiling"])
        self.assertFalse(exposure["at_risk"])

    def test_air_below_the_oxidation_onset_is_not_at_risk(self):
        exposure = oxidation_exposure(OXIDATION_ONSET_K - 40.0, 0.21)
        self.assertFalse(exposure["above_oxidation_onset"])
        self.assertFalse(exposure["at_risk"])

    def test_an_oxygen_fraction_above_unity_is_refused(self):
        with self.assertRaises(ValueError):
            oxidation_exposure(373.15, 1.4)


class EvidenceTests(unittest.TestCase):
    def test_a_purge_case_brings_its_gas_evidence(self):
        self.assertEqual(missing_gas_evidence(PURGE_CASE), ())

    def test_a_vacuum_case_carries_no_gas_evidence(self):
        self.assertEqual(len(missing_gas_evidence(VACUUM_CASE)), 2)

    def test_a_gas_run_without_a_frost_point_stops_the_judgement(self):
        case = _purge()
        del case["gas_frost_point_k"]
        with self.assertRaises(ValueError):
            assess_cycling_environment(case)

    def test_a_gas_run_without_an_oxygen_fraction_stops_the_judgement(self):
        case = _purge()
        del case["oxygen_volume_fraction"]
        with self.assertRaises(ValueError):
            assess_cycling_environment(case)


class AssessmentTests(unittest.TestCase):
    def test_a_vacuum_run_meets_the_preference_outright(self):
        result = assess_cycling_environment(VACUUM_CASE)
        self.assertEqual(result["verdict"], VACUUM_PREFERENCE_MET)
        self.assertTrue(result["acceptable"])
        self.assertFalse(result["justification_required"])
        self.assertEqual(result["conduction_regime"], "free-molecular")
        self.assertEqual(result["findings"], [])

    def test_a_vacuum_run_needs_no_frost_or_oxidation_evidence(self):
        result = assess_cycling_environment(VACUUM_CASE)
        self.assertIsNone(result["frost_point_margin_k"])
        self.assertIsNone(result["oxidation_exposure"])

    def test_a_dry_compensated_inert_purge_can_be_justified(self):
        result = assess_cycling_environment(PURGE_CASE)
        self.assertEqual(result["verdict"], AMBIENT_JUSTIFIED)
        self.assertTrue(result["acceptable"])
        self.assertTrue(result["justification_required"])
        self.assertEqual(result["conduction_regime"], "continuum")

    def test_an_unargued_departure_from_vacuum_is_refused(self):
        result = assess_cycling_environment(_purge(justification_recorded=False))
        self.assertEqual(result["verdict"], AMBIENT_NOT_JUSTIFIED)
        self.assertTrue(
            any("no recorded justification" in f for f in result["findings"])
        )

    def test_an_uncompensated_profile_in_gas_is_refused(self):
        result = assess_cycling_environment(
            _purge(profile_compensated_for_gas_conduction=False)
        )
        self.assertEqual(result["verdict"], AMBIENT_NOT_JUSTIFIED)
        self.assertTrue(any("gas conduction" in f for f in result["findings"]))
        self.assertFalse(result["gas_conduction_negligible"])

    def test_a_moist_gas_ices_the_cold_dwell(self):
        result = assess_cycling_environment(_purge(gas_frost_point_k=200.0))
        self.assertEqual(result["verdict"], AMBIENT_NOT_JUSTIFIED)
        self.assertTrue(any("frost point" in f for f in result["findings"]))
        self.assertFalse(result["frost_margin_adequate"])

    def test_an_oxygen_rich_purge_tarnishes_the_joints(self):
        result = assess_cycling_environment(_purge(oxygen_volume_fraction=0.21))
        self.assertEqual(result["verdict"], AMBIENT_NOT_JUSTIFIED)
        self.assertTrue(any("tarnish" in f for f in result["findings"]))

    def test_a_room_air_run_collects_every_finding_at_once(self):
        result = assess_cycling_environment(AIR_CASE)
        self.assertEqual(result["verdict"], AMBIENT_NOT_JUSTIFIED)
        self.assertEqual(result["environment"], ENVIRONMENT_ATMOSPHERIC)
        self.assertEqual(len(result["findings"]), 4)
        self.assertLess(result["frost_point_margin_k"], 0.0)

    def test_a_rarefied_fill_still_asks_for_a_justification(self):
        result = assess_cycling_environment(_purge(chamber_pressure_pa=50.0))
        self.assertEqual(result["environment"], ENVIRONMENT_RAREFIED)
        self.assertTrue(result["justification_required"])

    def test_the_knudsen_number_rises_as_the_chamber_is_pumped_down(self):
        dense = assess_cycling_environment(PURGE_CASE)
        thin = assess_cycling_environment(_purge(chamber_pressure_pa=1.0))
        self.assertGreater(thin["knudsen_number"], dense["knudsen_number"])

    def test_an_inverted_dwell_pair_is_refused(self):
        with self.assertRaises(ValueError):
            assess_cycling_environment(_vacuum(cold_dwell_k=400.0))

    def test_a_justification_flag_that_is_not_a_boolean_is_refused(self):
        with self.assertRaises(ValueError):
            assess_cycling_environment(_purge(justification_recorded="yes"))

    def test_a_case_without_a_gap_is_refused(self):
        case = _vacuum()
        del case["characteristic_gap_m"]
        with self.assertRaises(ValueError):
            assess_cycling_environment(case)

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_cycling_environment("vacuum")


if __name__ == "__main__":
    unittest.main()
