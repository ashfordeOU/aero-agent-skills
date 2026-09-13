#!/usr/bin/env python3
"""Contract test for the clause 10.2.7 tether breakage and debris logic."""

import math
import unittest

from e2006_tether_breakage_and_debris_effects_logic import (
    ARC_EROSION,
    DEFAULT_DISPOSAL_LIMIT_YEARS,
    MECHANICAL_OVERLOAD,
    OHMIC_BURNOUT,
    PARTICULATE_SEVERANCE,
    THERMAL_SOFTENING,
    UNCATEGORIZED,
    area_to_mass_ratio,
    assess_tether_breakage,
    categorize_failure_initiator,
    conductor_current_density,
    debris_segment_inventory,
    disposal_compliant,
    equilibrium_conductor_temperature,
    exposed_strand_area,
    ohmic_burnout_margin,
    orbital_decay_years,
    recoil_clears_standoff,
    recoil_reach,
    recoil_velocity,
    severance_probability,
    stored_strain_energy,
)


def base_case(**overrides):
    """A 5 km aluminium-conductor tether trailed from a host spacecraft."""
    case = {
        "length_m": 5000.0,
        "diameter_mm": 1.0,
        "linear_density_kg_m": 2.0e-4,
        "conductor_area_mm2": 0.5,
        "current_a": 1.0,
        "fusing_current_density_a_mm2": 80.0,
        "resistivity_ohm_m": 2.82e-8,
        "perimeter_mm": 3.1416,
        "emissivity": 0.8,
        "environment_temperature_k": 250.0,
        "softening_temperature_k": 700.0,
        "tension_n": 1.5,
        "breaking_strength_n": 60.0,
        "axial_stiffness_n": 1.2e5,
        "arc_energy_j": 0.2,
        "arc_erosion_threshold_j": 5.0,
        "particulate_flux_per_m2_s": 1.0e-9,
        "exposure_s": 2.592e6,
        "allowable_severance_probability": 0.05,
        "break_fraction": 0.5,
        "standoff_m": 20.0,
        "altitude_km": 400.0,
        "allowable_debris_objects": 1,
    }
    case.update(overrides)
    return case


def base_evidence(**overrides):
    evidence = {
        "current_density_a_mm2": 2.0,
        "fusing_current_density_a_mm2": 80.0,
        "conductor_temperature_k": 260.0,
        "softening_temperature_k": 700.0,
        "arc_energy_j": 0.2,
        "arc_erosion_threshold_j": 5.0,
        "tension_n": 1.5,
        "breaking_strength_n": 60.0,
        "severance_probability": 0.01,
        "allowable_severance_probability": 0.05,
    }
    evidence.update(overrides)
    return evidence


class TestConductorLoading(unittest.TestCase):
    def test_current_density_matches_hand_value(self):
        self.assertAlmostEqual(conductor_current_density(2.0, 0.5), 4.0, places=12)

    def test_current_density_rejects_zero_area(self):
        with self.assertRaises(ValueError):
            conductor_current_density(2.0, 0.0)

    def test_current_density_rejects_zero_current(self):
        with self.assertRaises(ValueError):
            conductor_current_density(0.0, 0.5)

    def test_current_density_rejects_text(self):
        with self.assertRaises(ValueError):
            conductor_current_density("2", 0.5)

    def test_current_density_rejects_boolean(self):
        with self.assertRaises(ValueError):
            conductor_current_density(True, 0.5)

    def test_current_density_rejects_nan(self):
        with self.assertRaises(ValueError):
            conductor_current_density(float("nan"), 0.5)

    def test_burnout_margin_matches_hand_value(self):
        self.assertAlmostEqual(ohmic_burnout_margin(4.0, 80.0), 20.0, places=12)

    def test_burnout_margin_falls_below_unity_when_overdriven(self):
        self.assertLess(ohmic_burnout_margin(100.0, 80.0), 1.0)

    def test_burnout_margin_rejects_negative_fusing_limit(self):
        with self.assertRaises(ValueError):
            ohmic_burnout_margin(4.0, -80.0)


class TestConductorTemperature(unittest.TestCase):
    def test_negligible_current_settles_at_the_environment(self):
        temperature = equilibrium_conductor_temperature(
            1.0e-9, 2.82e-8, 0.5, 3.1416, 0.8, 250.0
        )
        self.assertAlmostEqual(temperature, 250.0, places=6)

    def test_temperature_rises_with_current(self):
        cool = equilibrium_conductor_temperature(1.0, 2.82e-8, 0.5, 3.1416, 0.8, 250.0)
        hot = equilibrium_conductor_temperature(20.0, 2.82e-8, 0.5, 3.1416, 0.8, 250.0)
        self.assertGreater(hot, cool)

    def test_drive_dominated_temperature_scales_as_root_current(self):
        # Well above the environment the balance is T^4 proportional to I^2,
        # so doubling the current multiplies the temperature by sqrt(2).
        single = equilibrium_conductor_temperature(
            50.0, 2.82e-8, 0.5, 3.1416, 0.8, 1.0e-3
        )
        double = equilibrium_conductor_temperature(
            100.0, 2.82e-8, 0.5, 3.1416, 0.8, 1.0e-3
        )
        self.assertAlmostEqual(double / single, math.sqrt(2.0), places=6)

    def test_better_emitter_runs_cooler(self):
        dull = equilibrium_conductor_temperature(20.0, 2.82e-8, 0.5, 3.1416, 0.1, 250.0)
        black = equilibrium_conductor_temperature(20.0, 2.82e-8, 0.5, 3.1416, 0.9, 250.0)
        self.assertLess(black, dull)

    def test_zero_emissivity_rejected(self):
        with self.assertRaises(ValueError):
            equilibrium_conductor_temperature(1.0, 2.82e-8, 0.5, 3.1416, 0.0, 250.0)

    def test_emissivity_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            equilibrium_conductor_temperature(1.0, 2.82e-8, 0.5, 3.1416, 1.4, 250.0)

    def test_zero_perimeter_rejected(self):
        with self.assertRaises(ValueError):
            equilibrium_conductor_temperature(1.0, 2.82e-8, 0.5, 0.0, 0.8, 250.0)

    def test_negative_environment_temperature_rejected(self):
        with self.assertRaises(ValueError):
            equilibrium_conductor_temperature(1.0, 2.82e-8, 0.5, 3.1416, 0.8, -3.0)

    def test_zero_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            equilibrium_conductor_temperature(1.0, 0.0, 0.5, 3.1416, 0.8, 250.0)


class TestParticulateSeverance(unittest.TestCase):
    def test_exposed_area_matches_hand_value(self):
        self.assertAlmostEqual(exposed_strand_area(5000.0, 1.0), 5.0, places=12)

    def test_exposed_area_rejects_zero_diameter(self):
        with self.assertRaises(ValueError):
            exposed_strand_area(5000.0, 0.0)

    def test_one_expected_cut_of_ln_two_gives_even_odds(self):
        probability = severance_probability(math.log(2.0), 1.0, 1.0)
        self.assertAlmostEqual(probability, 0.5, places=12)

    def test_rare_strikes_approach_the_expected_count(self):
        probability = severance_probability(1.0e-9, 5.0, 1.0e6)
        self.assertAlmostEqual(probability, 5.0e-3, delta=2.0e-5)

    def test_no_flux_gives_no_severance(self):
        self.assertAlmostEqual(severance_probability(0.0, 5.0, 1.0e6), 0.0, places=12)

    def test_heavy_flux_saturates_towards_certainty(self):
        probability = severance_probability(1.0e-5, 100.0, 1.0e4)
        self.assertGreater(probability, 0.99)
        self.assertLessEqual(probability, 1.0)

    def test_negative_flux_rejected(self):
        with self.assertRaises(ValueError):
            severance_probability(-1.0e-9, 5.0, 1.0e6)

    def test_zero_exposure_rejected(self):
        with self.assertRaises(ValueError):
            severance_probability(1.0e-9, 5.0, 0.0)


class TestInitiatorCategorization(unittest.TestCase):
    def test_nominal_evidence_stays_uncategorized(self):
        verdict = categorize_failure_initiator(base_evidence())
        self.assertEqual(verdict["initiator"], UNCATEGORIZED)

    def test_uncategorized_verdict_reports_the_worst_ratio(self):
        verdict = categorize_failure_initiator(base_evidence())
        self.assertLess(verdict["ratio"], 1.0)

    def test_overdriven_conductor_is_categorized_as_ohmic_burnout(self):
        verdict = categorize_failure_initiator(
            base_evidence(current_density_a_mm2=200.0)
        )
        self.assertEqual(verdict["initiator"], OHMIC_BURNOUT)

    def test_hot_conductor_is_categorized_as_thermal_softening(self):
        verdict = categorize_failure_initiator(
            base_evidence(conductor_temperature_k=900.0)
        )
        self.assertEqual(verdict["initiator"], THERMAL_SOFTENING)

    def test_sustained_arc_is_categorized_as_arc_erosion(self):
        verdict = categorize_failure_initiator(base_evidence(arc_energy_j=12.0))
        self.assertEqual(verdict["initiator"], ARC_EROSION)

    def test_overloaded_strand_is_categorized_as_mechanical_overload(self):
        verdict = categorize_failure_initiator(base_evidence(tension_n=100.0))
        self.assertEqual(verdict["initiator"], MECHANICAL_OVERLOAD)

    def test_cut_risk_is_categorized_as_particulate_severance(self):
        verdict = categorize_failure_initiator(
            base_evidence(severance_probability=0.4)
        )
        self.assertEqual(verdict["initiator"], PARTICULATE_SEVERANCE)

    def test_ratio_exactly_at_the_limit_counts_as_reached(self):
        # A demand equal to its limit is a sum of floats that can round a few
        # units in the last place either way; it must still read as reached.
        verdict = categorize_failure_initiator(
            base_evidence(current_density_a_mm2=80.0)
        )
        self.assertEqual(verdict["initiator"], OHMIC_BURNOUT)

    def test_largest_exceedance_wins_over_a_smaller_one(self):
        verdict = categorize_failure_initiator(
            base_evidence(current_density_a_mm2=88.0, tension_n=600.0)
        )
        self.assertEqual(verdict["initiator"], MECHANICAL_OVERLOAD)

    def test_exact_tie_is_broken_by_priority(self):
        # ohmic ratio 2.0 and mechanical ratio 2.0 - the priority order decides.
        verdict = categorize_failure_initiator(
            base_evidence(current_density_a_mm2=160.0, tension_n=120.0)
        )
        self.assertEqual(verdict["initiator"], OHMIC_BURNOUT)

    def test_every_ratio_is_reported(self):
        verdict = categorize_failure_initiator(base_evidence())
        self.assertEqual(len(verdict["ratios"]), 5)

    def test_missing_evidence_key_rejected(self):
        evidence = base_evidence()
        del evidence["tension_n"]
        with self.assertRaises(ValueError):
            categorize_failure_initiator(evidence)

    def test_non_mapping_evidence_rejected(self):
        with self.assertRaises(ValueError):
            categorize_failure_initiator(["tension_n", 1.5])

    def test_probability_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            categorize_failure_initiator(base_evidence(severance_probability=1.4))

    def test_zero_allowable_probability_rejected(self):
        with self.assertRaises(ValueError):
            categorize_failure_initiator(
                base_evidence(allowable_severance_probability=0.0)
            )

    def test_negative_arc_energy_rejected(self):
        with self.assertRaises(ValueError):
            categorize_failure_initiator(base_evidence(arc_energy_j=-1.0))

    def test_zero_breaking_strength_rejected(self):
        with self.assertRaises(ValueError):
            categorize_failure_initiator(base_evidence(breaking_strength_n=0.0))


class TestRecoilMechanics(unittest.TestCase):
    def test_stored_energy_matches_hand_value(self):
        self.assertAlmostEqual(stored_strain_energy(1.5, 5000.0, 1.2e5),
                               0.046875, places=12)

    def test_stored_energy_grows_with_the_square_of_tension(self):
        single = stored_strain_energy(1.0, 5000.0, 1.2e5)
        double = stored_strain_energy(2.0, 5000.0, 1.2e5)
        self.assertAlmostEqual(double / single, 4.0, places=10)

    def test_stiffer_strand_stores_less_energy(self):
        self.assertLess(stored_strain_energy(1.5, 5000.0, 2.4e5),
                        stored_strain_energy(1.5, 5000.0, 1.2e5))

    def test_stored_energy_rejects_zero_stiffness(self):
        with self.assertRaises(ValueError):
            stored_strain_energy(1.5, 5000.0, 0.0)

    def test_recoil_velocity_matches_hand_value(self):
        # 2 * 0.046875 J released into 0.5 kg gives sqrt(0.1875) m/s.
        self.assertAlmostEqual(recoil_velocity(1.5, 5000.0, 1.2e5, 0.5),
                               math.sqrt(0.1875), places=10)

    def test_heavier_segment_recoils_more_slowly(self):
        self.assertLess(recoil_velocity(1.5, 5000.0, 1.2e5, 2.0),
                        recoil_velocity(1.5, 5000.0, 1.2e5, 0.5))

    def test_recoil_velocity_rejects_zero_mass(self):
        with self.assertRaises(ValueError):
            recoil_velocity(1.5, 5000.0, 1.2e5, 0.0)

    def test_recoil_reach_matches_hand_value(self):
        self.assertAlmostEqual(recoil_reach(1.5, 5000.0, 1.2e5), 0.0625, places=12)

    def test_recoil_reach_grows_with_tension(self):
        self.assertGreater(recoil_reach(3.0, 5000.0, 1.2e5),
                           recoil_reach(1.5, 5000.0, 1.2e5))

    def test_short_reach_clears_the_standoff(self):
        self.assertTrue(recoil_clears_standoff(0.0625, 20.0))

    def test_long_reach_breaches_the_standoff(self):
        self.assertFalse(recoil_clears_standoff(25.0, 20.0))

    def test_reach_exactly_at_the_standoff_still_clears(self):
        self.assertTrue(recoil_clears_standoff(20.0, 20.0))

    def test_standoff_rejects_zero(self):
        with self.assertRaises(ValueError):
            recoil_clears_standoff(1.0, 0.0)

    def test_negative_reach_rejected(self):
        with self.assertRaises(ValueError):
            recoil_clears_standoff(-1.0, 20.0)


class TestDebrisInventory(unittest.TestCase):
    def test_mid_span_sever_splits_the_length_evenly(self):
        inventory = debris_segment_inventory(5000.0, 0.5, 2.0e-4)
        self.assertAlmostEqual(inventory["attached_length_m"], 2500.0, places=9)
        self.assertAlmostEqual(inventory["free_length_m"], 2500.0, places=9)

    def test_free_mass_follows_the_linear_density(self):
        inventory = debris_segment_inventory(5000.0, 0.5, 2.0e-4)
        self.assertAlmostEqual(inventory["free_mass_kg"], 0.5, places=12)

    def test_sever_near_the_host_leaves_a_long_free_segment(self):
        inventory = debris_segment_inventory(5000.0, 0.1, 2.0e-4)
        self.assertGreater(inventory["free_length_m"], inventory["attached_length_m"])

    def test_released_end_body_adds_its_mass(self):
        inventory = debris_segment_inventory(5000.0, 0.5, 2.0e-4, 5.0)
        self.assertAlmostEqual(inventory["free_mass_kg"], 5.5, places=12)

    def test_released_end_body_adds_an_object(self):
        inventory = debris_segment_inventory(5000.0, 0.5, 2.0e-4, 5.0)
        self.assertEqual(inventory["released_object_count"], 2)

    def test_bare_strand_sever_releases_one_object(self):
        inventory = debris_segment_inventory(5000.0, 0.5, 2.0e-4)
        self.assertEqual(inventory["released_object_count"], 1)

    def test_break_fraction_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            debris_segment_inventory(5000.0, 0.0, 2.0e-4)

    def test_break_fraction_of_one_rejected(self):
        with self.assertRaises(ValueError):
            debris_segment_inventory(5000.0, 1.0, 2.0e-4)

    def test_break_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            debris_segment_inventory(5000.0, 1.5, 2.0e-4)

    def test_negative_released_mass_rejected(self):
        with self.assertRaises(ValueError):
            debris_segment_inventory(5000.0, 0.5, 2.0e-4, -1.0)

    def test_area_to_mass_matches_hand_value(self):
        self.assertAlmostEqual(area_to_mass_ratio(2500.0, 1.0, 0.5), 5.0, places=12)

    def test_area_to_mass_rejects_zero_mass(self):
        with self.assertRaises(ValueError):
            area_to_mass_ratio(2500.0, 1.0, 0.0)


class TestDecayLifetime(unittest.TestCase):
    def test_compact_fragment_at_four_hundred_km_decays_within_a_year(self):
        years = orbital_decay_years(400.0, 0.01)
        self.assertGreater(years, 0.1)
        self.assertLess(years, 10.0)

    def test_bare_strand_decays_far_faster_than_a_compact_fragment(self):
        self.assertLess(orbital_decay_years(400.0, 5.0),
                        orbital_decay_years(400.0, 0.01))

    def test_lifetime_is_inverse_in_area_to_mass(self):
        single = orbital_decay_years(400.0, 0.01)
        double = orbital_decay_years(400.0, 0.02)
        self.assertAlmostEqual(single / double, 2.0, places=8)

    def test_lifetime_grows_with_altitude(self):
        self.assertGreater(orbital_decay_years(800.0, 0.01),
                           orbital_decay_years(400.0, 0.01))

    def test_high_orbit_strand_outlives_the_disposal_limit(self):
        self.assertGreater(orbital_decay_years(1200.0, 5.0),
                           DEFAULT_DISPOSAL_LIMIT_YEARS)

    def test_altitude_above_the_drag_regime_rejected(self):
        with self.assertRaises(ValueError):
            orbital_decay_years(35786.0, 0.01)

    def test_zero_area_to_mass_rejected(self):
        with self.assertRaises(ValueError):
            orbital_decay_years(400.0, 0.0)

    def test_zero_drag_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            orbital_decay_years(400.0, 0.01, drag_coefficient=0.0)

    def test_lifetime_inside_the_limit_is_compliant(self):
        self.assertTrue(disposal_compliant(3.0, 25.0))

    def test_lifetime_exactly_on_the_limit_is_compliant(self):
        self.assertTrue(disposal_compliant(25.0, 25.0))

    def test_lifetime_past_the_limit_is_not_compliant(self):
        self.assertFalse(disposal_compliant(40.0, 25.0))

    def test_disposal_limit_rejects_zero(self):
        with self.assertRaises(ValueError):
            disposal_compliant(3.0, 0.0)


class TestAssessment(unittest.TestCase):
    def test_baseline_case_is_compliant(self):
        result = assess_tether_breakage(base_case())
        self.assertTrue(result["compliant"])

    def test_compliant_case_carries_no_findings(self):
        result = assess_tether_breakage(base_case())
        self.assertEqual(result["findings"], [])

    def test_baseline_initiator_is_uncategorized(self):
        result = assess_tether_breakage(base_case())
        self.assertEqual(result["initiator"], UNCATEGORIZED)

    def test_baseline_conductor_runs_near_the_environment(self):
        result = assess_tether_breakage(base_case())
        self.assertLess(result["conductor_temperature_k"], 300.0)

    def test_overdriven_conductor_is_flagged(self):
        result = assess_tether_breakage(base_case(current_a=100.0))
        self.assertFalse(result["compliant"])
        self.assertEqual(result["initiator"], OHMIC_BURNOUT)

    def test_overdriven_conductor_loses_its_burnout_margin(self):
        result = assess_tether_breakage(base_case(current_a=100.0))
        self.assertLess(result["ohmic_burnout_margin"], 1.0)
        self.assertTrue(any("burnout margin" in f for f in result["findings"]))

    def test_overdriven_conductor_runs_hot(self):
        result = assess_tether_breakage(base_case(current_a=100.0))
        self.assertGreater(result["conductor_temperature_k"], 700.0)

    def test_burnout_margin_exactly_at_unity_is_not_flagged_as_below(self):
        result = assess_tether_breakage(
            base_case(fusing_current_density_a_mm2=2.0)
        )
        self.assertFalse(any("burnout margin" in f for f in result["findings"]))

    def test_burnout_margin_exactly_at_unity_still_names_the_initiator(self):
        result = assess_tether_breakage(
            base_case(fusing_current_density_a_mm2=2.0)
        )
        self.assertEqual(result["initiator"], OHMIC_BURNOUT)

    def test_sustained_arc_site_is_flagged(self):
        result = assess_tether_breakage(base_case(arc_energy_j=12.0))
        self.assertEqual(result["initiator"], ARC_EROSION)

    def test_tension_overload_is_flagged(self):
        result = assess_tether_breakage(base_case(tension_n=100.0))
        self.assertEqual(result["initiator"], MECHANICAL_OVERLOAD)

    def test_tight_allowable_cut_risk_is_flagged(self):
        result = assess_tether_breakage(
            base_case(allowable_severance_probability=0.001)
        )
        self.assertEqual(result["initiator"], PARTICULATE_SEVERANCE)

    def test_recoil_breaching_the_standoff_is_flagged(self):
        result = assess_tether_breakage(base_case(standoff_m=0.01))
        self.assertTrue(any("keep-out standoff" in f for f in result["findings"]))

    def test_standoff_exactly_at_the_reach_stays_compliant(self):
        first = assess_tether_breakage(base_case())
        exact = assess_tether_breakage(base_case(standoff_m=first["recoil_reach_m"]))
        self.assertTrue(exact["compliant"])

    def test_free_segment_at_high_altitude_outlives_the_disposal_limit(self):
        result = assess_tether_breakage(base_case(altitude_km=1200.0))
        self.assertTrue(any("disposal limit" in f for f in result["findings"]))

    def test_disposal_limit_exactly_at_the_lifetime_stays_compliant(self):
        first = assess_tether_breakage(base_case(altitude_km=1200.0))
        exact = assess_tether_breakage(
            base_case(altitude_km=1200.0,
                      disposal_limit_years=first["decay_lifetime_years"])
        )
        self.assertTrue(exact["compliant"])

    def test_released_end_body_breaches_the_object_allowance(self):
        result = assess_tether_breakage(base_case(released_end_mass_kg=5.0))
        self.assertTrue(any("allowance" in f for f in result["findings"]))

    def test_released_end_body_within_allowance_is_compliant(self):
        result = assess_tether_breakage(
            base_case(released_end_mass_kg=5.0, allowable_debris_objects=2)
        )
        self.assertTrue(result["compliant"])

    def test_released_end_body_slows_the_recoil(self):
        bare = assess_tether_breakage(base_case())
        loaded = assess_tether_breakage(
            base_case(released_end_mass_kg=5.0, allowable_debris_objects=2)
        )
        self.assertLess(loaded["recoil_velocity_m_s"], bare["recoil_velocity_m_s"])

    def test_sever_near_the_host_leaves_a_longer_free_segment(self):
        result = assess_tether_breakage(base_case(break_fraction=0.1))
        self.assertGreater(result["inventory"]["free_length_m"], 4000.0)

    def test_free_segment_area_to_mass_is_reported(self):
        result = assess_tether_breakage(base_case())
        self.assertAlmostEqual(result["free_area_to_mass_m2_kg"], 5.0, places=9)

    def test_missing_required_key_rejected(self):
        case = base_case()
        del case["standoff_m"]
        with self.assertRaises(ValueError):
            assess_tether_breakage(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_tether_breakage(["length_m", 5000.0])

    def test_zero_object_allowance_rejected(self):
        with self.assertRaises(ValueError):
            assess_tether_breakage(base_case(allowable_debris_objects=0))

    def test_boolean_object_allowance_rejected(self):
        with self.assertRaises(ValueError):
            assess_tether_breakage(base_case(allowable_debris_objects=True))

    def test_float_object_allowance_rejected(self):
        with self.assertRaises(ValueError):
            assess_tether_breakage(base_case(allowable_debris_objects=1.5))

    def test_negative_disposal_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_tether_breakage(base_case(disposal_limit_years=-5.0))

    def test_bad_break_fraction_rejected_by_assessment(self):
        with self.assertRaises(ValueError):
            assess_tether_breakage(base_case(break_fraction=1.0))

    def test_bad_emissivity_rejected_by_assessment(self):
        with self.assertRaises(ValueError):
            assess_tether_breakage(base_case(emissivity=1.5))


if __name__ == "__main__":
    unittest.main()
