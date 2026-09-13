#!/usr/bin/env python3
"""Contract test for the clause 10.3 tether end-to-end voltage logic."""

import math
import unittest

from e2006_tether_voltage_validation_logic import (
    EXTREME_VOLTAGE,
    HIGH_VOLTAGE,
    LOW_VOLTAGE,
    categorize_voltage_regime,
    circuit_drop,
    corotation_velocity,
    declared_voltage_covers_bound,
    dipole_flux_density,
    end_to_end_emf,
    end_to_end_potential,
    induced_field_v_per_m,
    orbital_radius_m,
    orbital_velocity,
    relative_plasma_velocity,
    sweep_grid,
    validate_tether_voltage,
    withstand_margin,
    worst_case_end_to_end_potential,
)


def base_case(**overrides):
    """A 5 km conducting tether on a 400 km, 51.6 degree orbit."""
    case = {
        "altitude_km": 400.0,
        "inclination_deg": 51.6,
        "length_m": 5000.0,
        "alignment_deg": 0.0,
        "attitude_deviation_deg": 15.0,
        "circuit_resistance_ohm": 200.0,
        "operating_current_a": 0.5,
        "anode_contact_drop_v": 20.0,
        "cathode_contact_drop_v": 30.0,
        "applied_bias_v": 0.0,
        "declared_design_voltage_v": 2000.0,
        "insulation_withstand_v": 3000.0,
        "high_voltage_provisions": True,
    }
    case.update(overrides)
    return case


def short_case(**overrides):
    """A 100 m tether whose bounding potential stays in the low-voltage regime."""
    return base_case(length_m=100.0, high_voltage_provisions=False, **overrides)


class TestOrbitEnvironment(unittest.TestCase):
    def test_orbital_radius_matches_hand_value(self):
        self.assertAlmostEqual(orbital_radius_m(400.0), 6778137.0, places=3)

    def test_orbital_radius_rejects_zero_altitude(self):
        with self.assertRaises(ValueError):
            orbital_radius_m(0.0)

    def test_orbital_radius_rejects_negative_altitude(self):
        with self.assertRaises(ValueError):
            orbital_radius_m(-100.0)

    def test_orbital_radius_rejects_altitude_beyond_the_model(self):
        with self.assertRaises(ValueError):
            orbital_radius_m(100000.0)

    def test_orbital_radius_rejects_text(self):
        with self.assertRaises(ValueError):
            orbital_radius_m("400")

    def test_orbital_radius_rejects_boolean(self):
        with self.assertRaises(ValueError):
            orbital_radius_m(True)

    def test_low_orbit_speed_is_about_seven_point_seven(self):
        self.assertAlmostEqual(orbital_velocity(400.0), 7669.0, delta=5.0)

    def test_orbital_speed_falls_with_altitude(self):
        self.assertLess(orbital_velocity(800.0), orbital_velocity(400.0))

    def test_equatorial_corotation_speed(self):
        self.assertAlmostEqual(corotation_velocity(400.0, 0.0), 494.3, delta=2.0)

    def test_corotation_vanishes_over_the_pole(self):
        self.assertAlmostEqual(corotation_velocity(400.0, 90.0), 0.0, places=6)

    def test_corotation_rejects_impossible_latitude(self):
        with self.assertRaises(ValueError):
            corotation_velocity(400.0, 95.0)

    def test_prograde_equatorial_orbit_loses_the_corotation_speed(self):
        speed = relative_plasma_velocity(400.0, 0.0, 0.0)
        self.assertAlmostEqual(speed, 7669.0 - 494.3, delta=6.0)

    def test_retrograde_orbit_gains_on_the_plasma(self):
        self.assertGreater(relative_plasma_velocity(400.0, 180.0, 0.0),
                           relative_plasma_velocity(400.0, 0.0, 0.0))

    def test_polar_orbit_keeps_the_full_orbital_speed(self):
        self.assertAlmostEqual(relative_plasma_velocity(400.0, 90.0, 0.0),
                               orbital_velocity(400.0), places=6)

    def test_relative_velocity_rejects_impossible_inclination(self):
        with self.assertRaises(ValueError):
            relative_plasma_velocity(400.0, 200.0, 0.0)


class TestFieldModel(unittest.TestCase):
    def test_surface_equatorial_field_matches_the_dipole_anchor(self):
        self.assertAlmostEqual(dipole_flux_density(0.001, 0.0), 3.12e-5, places=9)

    def test_polar_field_is_twice_the_equatorial_field(self):
        polar = dipole_flux_density(400.0, 90.0)
        equatorial = dipole_flux_density(400.0, 0.0)
        self.assertAlmostEqual(polar / equatorial, 2.0, places=10)

    def test_field_is_symmetric_about_the_equator(self):
        self.assertAlmostEqual(dipole_flux_density(400.0, -45.0),
                               dipole_flux_density(400.0, 45.0), places=12)

    def test_field_falls_with_the_cube_of_radius(self):
        # Doubling the radius must cut the field to one eighth.
        far = dipole_flux_density(6378.137, 0.0)
        near = dipole_flux_density(0.001, 0.0)
        self.assertAlmostEqual(far / near, 0.125, places=6)

    def test_field_rejects_impossible_latitude(self):
        with self.assertRaises(ValueError):
            dipole_flux_density(400.0, 91.0)


class TestInducedField(unittest.TestCase):
    def test_perpendicular_crossing_matches_hand_value(self):
        self.assertAlmostEqual(induced_field_v_per_m(7500.0, 3.0e-5, 90.0),
                               0.225, places=12)

    def test_thirty_degree_crossing_halves_the_field(self):
        self.assertAlmostEqual(induced_field_v_per_m(7500.0, 3.0e-5, 30.0),
                               0.1125, places=12)

    def test_parallel_crossing_induces_nothing(self):
        self.assertAlmostEqual(induced_field_v_per_m(7500.0, 3.0e-5, 0.0),
                               0.0, places=12)

    def test_low_orbit_field_is_the_familiar_hundreds_of_volts_per_km(self):
        per_km = induced_field_v_per_m(7174.0, 2.6e-5) * 1000.0
        self.assertGreater(per_km, 100.0)
        self.assertLess(per_km, 250.0)

    def test_induced_field_rejects_zero_speed(self):
        with self.assertRaises(ValueError):
            induced_field_v_per_m(0.0, 3.0e-5, 90.0)

    def test_induced_field_rejects_zero_flux_density(self):
        with self.assertRaises(ValueError):
            induced_field_v_per_m(7500.0, 0.0, 90.0)

    def test_induced_field_rejects_impossible_angle(self):
        with self.assertRaises(ValueError):
            induced_field_v_per_m(7500.0, 3.0e-5, 200.0)

    def test_emf_matches_hand_value_when_aligned(self):
        self.assertAlmostEqual(end_to_end_emf(0.2, 5000.0, 0.0), 1000.0, places=9)

    def test_emf_halves_at_sixty_degrees(self):
        self.assertAlmostEqual(end_to_end_emf(0.2, 5000.0, 60.0), 500.0, places=9)

    def test_emf_vanishes_across_the_field(self):
        self.assertAlmostEqual(end_to_end_emf(0.2, 5000.0, 90.0), 0.0, places=9)

    def test_reversed_line_has_the_same_magnitude(self):
        self.assertAlmostEqual(end_to_end_emf(0.2, 5000.0, 180.0), 1000.0, places=9)

    def test_emf_rejects_negative_field(self):
        with self.assertRaises(ValueError):
            end_to_end_emf(-0.2, 5000.0, 0.0)

    def test_emf_rejects_zero_length(self):
        with self.assertRaises(ValueError):
            end_to_end_emf(0.2, 0.0, 0.0)

    def test_emf_rejects_impossible_alignment(self):
        with self.assertRaises(ValueError):
            end_to_end_emf(0.2, 5000.0, 270.0)


class TestCircuitTerms(unittest.TestCase):
    def test_circuit_drop_matches_hand_value(self):
        self.assertAlmostEqual(circuit_drop(0.5, 200.0, 20.0, 30.0), 150.0, places=9)

    def test_open_circuit_leaves_only_the_contact_drops(self):
        self.assertAlmostEqual(circuit_drop(0.0, 200.0, 20.0, 30.0), 50.0, places=9)

    def test_circuit_drop_rejects_negative_resistance(self):
        with self.assertRaises(ValueError):
            circuit_drop(0.5, -200.0, 20.0, 30.0)

    def test_circuit_drop_rejects_negative_current(self):
        with self.assertRaises(ValueError):
            circuit_drop(-0.5, 200.0, 20.0, 30.0)

    def test_circuit_drop_rejects_negative_contact_drop(self):
        with self.assertRaises(ValueError):
            circuit_drop(0.5, 200.0, -20.0, 30.0)

    def test_open_circuit_bounds_the_loaded_value(self):
        potentials = end_to_end_potential(1000.0, 0.0, 150.0)
        self.assertAlmostEqual(potentials["open_circuit_v"], 1000.0, places=9)
        self.assertAlmostEqual(potentials["loaded_v"], 850.0, places=9)
        self.assertAlmostEqual(potentials["bounding_v"], 1000.0, places=9)

    def test_supply_bias_adds_to_the_open_circuit_value(self):
        potentials = end_to_end_potential(1000.0, 200.0, 150.0)
        self.assertAlmostEqual(potentials["open_circuit_v"], 1200.0, places=9)

    def test_opposing_bias_reverses_the_sense_but_not_the_bound(self):
        potentials = end_to_end_potential(1000.0, -1500.0, 150.0)
        self.assertAlmostEqual(potentials["open_circuit_v"], 500.0, places=9)
        self.assertAlmostEqual(potentials["loaded_v"], 350.0, places=9)

    def test_drops_larger_than_the_drive_leave_no_current(self):
        potentials = end_to_end_potential(100.0, 0.0, 150.0)
        self.assertFalse(potentials["current_flows"])
        self.assertAlmostEqual(potentials["loaded_v"],
                               potentials["open_circuit_v"], places=12)

    def test_driven_circuit_reports_current_flow(self):
        potentials = end_to_end_potential(1000.0, 0.0, 150.0)
        self.assertTrue(potentials["current_flows"])

    def test_potential_rejects_negative_emf(self):
        with self.assertRaises(ValueError):
            end_to_end_potential(-1000.0, 0.0, 150.0)

    def test_potential_rejects_negative_drop(self):
        with self.assertRaises(ValueError):
            end_to_end_potential(1000.0, 0.0, -150.0)


class TestSweepGrid(unittest.TestCase):
    def test_grid_covers_every_latitude_and_attitude_pair(self):
        grid = sweep_grid(51.6, 0.0, 15.0, sample_count=7)
        self.assertEqual(len(grid), 14)

    def test_fixed_attitude_gives_one_alignment_per_latitude(self):
        grid = sweep_grid(51.6, 0.0, 0.0, sample_count=7)
        self.assertEqual(len(grid), 7)

    def test_latitude_reach_follows_the_inclination(self):
        grid = sweep_grid(51.6, 0.0, 0.0, sample_count=7)
        self.assertAlmostEqual(max(s["magnetic_latitude_deg"] for s in grid),
                               51.6, places=9)

    def test_retrograde_inclination_folds_onto_its_supplement(self):
        grid = sweep_grid(150.0, 0.0, 0.0, sample_count=7)
        self.assertAlmostEqual(max(s["magnetic_latitude_deg"] for s in grid),
                               30.0, places=9)

    def test_polar_reach_is_capped_at_the_pole(self):
        grid = sweep_grid(90.0, 0.0, 0.0, sample_count=5)
        self.assertAlmostEqual(max(s["magnetic_latitude_deg"] for s in grid),
                               90.0, places=9)

    def test_grid_starts_at_the_magnetic_equator(self):
        grid = sweep_grid(51.6, 0.0, 0.0, sample_count=7)
        self.assertAlmostEqual(min(s["magnetic_latitude_deg"] for s in grid),
                               0.0, places=12)

    def test_attitude_envelope_is_clipped_at_zero(self):
        grid = sweep_grid(51.6, 5.0, 15.0, sample_count=2)
        self.assertAlmostEqual(min(s["alignment_deg"] for s in grid), 0.0, places=12)

    def test_single_sample_rejected(self):
        with self.assertRaises(ValueError):
            sweep_grid(51.6, 0.0, 15.0, sample_count=1)

    def test_excessive_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            sweep_grid(51.6, 0.0, 15.0, sample_count=500)

    def test_float_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            sweep_grid(51.6, 0.0, 15.0, sample_count=7.0)

    def test_boolean_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            sweep_grid(51.6, 0.0, 15.0, sample_count=True)

    def test_excessive_attitude_deviation_rejected(self):
        with self.assertRaises(ValueError):
            sweep_grid(51.6, 0.0, 120.0)

    def test_negative_attitude_deviation_rejected(self):
        with self.assertRaises(ValueError):
            sweep_grid(51.6, 0.0, -5.0)


class TestWorstCaseSweep(unittest.TestCase):
    def test_baseline_bound_is_in_the_kilovolt_range(self):
        worst = worst_case_end_to_end_potential(base_case())
        self.assertGreater(worst["bounding_v"], 1400.0)
        self.assertLess(worst["bounding_v"], 1800.0)

    def test_worst_sample_sits_at_the_highest_reached_latitude(self):
        worst = worst_case_end_to_end_potential(base_case())
        self.assertAlmostEqual(worst["magnetic_latitude_deg"], 51.6, places=9)

    def test_worst_sample_sits_at_the_best_aligned_attitude(self):
        worst = worst_case_end_to_end_potential(base_case())
        self.assertAlmostEqual(worst["alignment_deg"], 0.0, places=12)

    def test_bound_is_linear_in_deployed_length(self):
        single = worst_case_end_to_end_potential(base_case())
        double = worst_case_end_to_end_potential(base_case(length_m=10000.0))
        self.assertAlmostEqual(double["bounding_v"] / single["bounding_v"],
                               2.0, places=9)

    def test_polar_orbit_bounds_higher_than_an_equatorial_one(self):
        polar = worst_case_end_to_end_potential(base_case(inclination_deg=90.0))
        equatorial = worst_case_end_to_end_potential(base_case(inclination_deg=0.0))
        self.assertGreater(polar["bounding_v"], equatorial["bounding_v"])

    def test_open_circuit_sets_the_bound_without_an_opposing_bias(self):
        worst = worst_case_end_to_end_potential(base_case())
        self.assertAlmostEqual(worst["bounding_v"], worst["open_circuit_v"], places=9)

    def test_supply_bias_raises_the_bound(self):
        plain = worst_case_end_to_end_potential(base_case())
        biased = worst_case_end_to_end_potential(base_case(applied_bias_v=400.0))
        self.assertAlmostEqual(biased["bounding_v"] - plain["bounding_v"],
                               400.0, places=6)

    def test_circuit_drop_is_reported_with_the_worst_sample(self):
        worst = worst_case_end_to_end_potential(base_case())
        self.assertAlmostEqual(worst["circuit_drop_v"], 150.0, places=9)

    def test_sample_count_is_reported(self):
        worst = worst_case_end_to_end_potential(base_case())
        self.assertEqual(worst["sample_count"], 14)

    def test_denser_sweep_does_not_lower_the_bound(self):
        coarse = worst_case_end_to_end_potential(base_case(sample_count=2))
        fine = worst_case_end_to_end_potential(base_case(sample_count=31))
        self.assertGreaterEqual(fine["bounding_v"], coarse["bounding_v"] - 1.0e-9)

    def test_worst_case_rejects_a_missing_key(self):
        case = base_case()
        del case["length_m"]
        with self.assertRaises(ValueError):
            worst_case_end_to_end_potential(case)


class TestRegimeAndMargin(unittest.TestCase):
    def test_small_potential_is_categorized_low_voltage(self):
        self.assertEqual(categorize_voltage_regime(50.0), LOW_VOLTAGE)

    def test_threshold_potential_is_categorized_high_voltage(self):
        # Exactly on the threshold, which a product of floats can land either
        # side of, must read as the higher regime.
        self.assertEqual(categorize_voltage_regime(100.0), HIGH_VOLTAGE)

    def test_just_below_the_threshold_stays_low_voltage(self):
        self.assertEqual(categorize_voltage_regime(99.0), LOW_VOLTAGE)

    def test_kilovolt_potential_is_categorized_extreme(self):
        self.assertEqual(categorize_voltage_regime(1000.0), EXTREME_VOLTAGE)

    def test_just_below_a_kilovolt_stays_high_voltage(self):
        self.assertEqual(categorize_voltage_regime(999.0), HIGH_VOLTAGE)

    def test_zero_potential_is_low_voltage(self):
        self.assertEqual(categorize_voltage_regime(0.0), LOW_VOLTAGE)

    def test_negative_potential_rejected(self):
        with self.assertRaises(ValueError):
            categorize_voltage_regime(-10.0)

    def test_withstand_margin_matches_hand_value(self):
        self.assertAlmostEqual(withstand_margin(3000.0, 1500.0), 2.0, places=12)

    def test_withstand_margin_rejects_zero_bound(self):
        with self.assertRaises(ValueError):
            withstand_margin(3000.0, 0.0)

    def test_withstand_margin_rejects_zero_rating(self):
        with self.assertRaises(ValueError):
            withstand_margin(0.0, 1500.0)

    def test_declared_voltage_above_the_bound_covers_it(self):
        self.assertTrue(declared_voltage_covers_bound(2000.0, 1638.0))

    def test_declared_voltage_equal_to_the_bound_covers_it(self):
        self.assertTrue(declared_voltage_covers_bound(1638.0, 1638.0))

    def test_declared_voltage_below_the_bound_does_not_cover_it(self):
        self.assertFalse(declared_voltage_covers_bound(1000.0, 1638.0))

    def test_declared_voltage_rejects_zero(self):
        with self.assertRaises(ValueError):
            declared_voltage_covers_bound(0.0, 1638.0)


class TestValidation(unittest.TestCase):
    def test_baseline_case_is_compliant(self):
        result = validate_tether_voltage(base_case())
        self.assertTrue(result["compliant"])

    def test_compliant_case_carries_no_findings(self):
        result = validate_tether_voltage(base_case())
        self.assertEqual(result["findings"], [])

    def test_baseline_lands_in_the_extreme_regime(self):
        result = validate_tether_voltage(base_case())
        self.assertEqual(result["regime"], EXTREME_VOLTAGE)

    def test_short_tether_stays_in_the_low_voltage_regime(self):
        result = validate_tether_voltage(short_case())
        self.assertEqual(result["regime"], LOW_VOLTAGE)

    def test_short_tether_needs_no_high_voltage_provisions(self):
        result = validate_tether_voltage(short_case())
        self.assertTrue(result["compliant"])

    def test_understated_design_voltage_is_flagged(self):
        result = validate_tether_voltage(base_case(declared_design_voltage_v=500.0))
        self.assertTrue(any("does not cover" in f for f in result["findings"]))

    def test_design_voltage_exactly_at_the_bound_stays_compliant(self):
        first = validate_tether_voltage(base_case())
        exact = validate_tether_voltage(
            base_case(declared_design_voltage_v=first["bounding_voltage_v"])
        )
        self.assertTrue(exact["compliant"])

    def test_thin_insulation_margin_is_flagged(self):
        result = validate_tether_voltage(base_case(insulation_withstand_v=1700.0))
        self.assertTrue(any("withstand margin" in f for f in result["findings"]))

    def test_margin_exactly_at_the_requirement_stays_compliant(self):
        first = validate_tether_voltage(base_case())
        rating = 1.25 * first["bounding_voltage_v"]
        exact = validate_tether_voltage(
            base_case(insulation_withstand_v=rating,
                      declared_design_voltage_v=rating)
        )
        self.assertTrue(exact["compliant"])

    def test_missing_high_voltage_provisions_are_flagged(self):
        result = validate_tether_voltage(base_case(high_voltage_provisions=False))
        self.assertTrue(any("high-voltage provisions" in f for f in result["findings"]))

    def test_non_boolean_provisions_rejected(self):
        with self.assertRaises(ValueError):
            validate_tether_voltage(base_case(high_voltage_provisions="yes"))

    def test_reported_margin_matches_the_rating_over_the_bound(self):
        result = validate_tether_voltage(base_case())
        expected = 3000.0 / result["bounding_voltage_v"]
        self.assertAlmostEqual(result["withstand_margin"], expected, places=9)

    def test_loaded_value_is_below_the_open_circuit_value(self):
        result = validate_tether_voltage(base_case())
        self.assertLess(result["loaded_voltage_v"], result["open_circuit_voltage_v"])

    def test_tighter_margin_requirement_can_fail_an_otherwise_sound_case(self):
        result = validate_tether_voltage(base_case(required_withstand_margin=3.0))
        self.assertFalse(result["compliant"])

    def test_zero_margin_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_tether_voltage(base_case(required_withstand_margin=0.0))

    def test_missing_required_key_rejected(self):
        case = base_case()
        del case["insulation_withstand_v"]
        with self.assertRaises(ValueError):
            validate_tether_voltage(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            validate_tether_voltage(["altitude_km", 400.0])

    def test_worst_sample_is_returned_with_the_verdict(self):
        result = validate_tether_voltage(base_case())
        self.assertIn("magnetic_latitude_deg", result["worst_sample"])

    def test_retrograde_orbit_raises_the_bound(self):
        prograde = validate_tether_voltage(base_case(inclination_deg=20.0))
        retrograde = validate_tether_voltage(base_case(inclination_deg=160.0))
        self.assertGreater(retrograde["bounding_voltage_v"],
                           prograde["bounding_voltage_v"])

    def test_cross_field_attitude_lowers_the_bound(self):
        aligned = validate_tether_voltage(base_case())
        crossed = validate_tether_voltage(
            base_case(alignment_deg=80.0, attitude_deviation_deg=0.0)
        )
        self.assertLess(crossed["bounding_voltage_v"], aligned["bounding_voltage_v"])

    def test_cross_field_bound_follows_the_cosine_projection(self):
        aligned = validate_tether_voltage(
            base_case(alignment_deg=0.0, attitude_deviation_deg=0.0)
        )
        crossed = validate_tether_voltage(
            base_case(alignment_deg=60.0, attitude_deviation_deg=0.0)
        )
        self.assertAlmostEqual(
            crossed["bounding_voltage_v"] / aligned["bounding_voltage_v"],
            math.cos(math.radians(60.0)), places=9
        )


if __name__ == "__main__":
    unittest.main()
