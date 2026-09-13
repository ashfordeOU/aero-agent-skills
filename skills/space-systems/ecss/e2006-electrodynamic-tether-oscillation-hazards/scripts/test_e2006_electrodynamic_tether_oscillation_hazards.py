#!/usr/bin/env python3
"""Contract test for the clause 10.2.6 tether oscillation-hazard logic."""

import math
import unittest

from e2006_electrodynamic_tether_oscillation_hazards_logic import (
    DEFAULT_DETUNE_FRACTION,
    IN_PLANE_LIBRATION,
    OFF_RESONANCE,
    OUT_OF_PLANE_LIBRATION,
    TUMBLE_SEPARATRIX_DEG,
    assess_oscillation_hazards,
    build_mode_table,
    categorize_resonance,
    center_of_mass_offset,
    forcing_spectrum,
    libration_inertia,
    libration_mode_frequencies,
    libration_response_deg,
    longitudinal_mode_frequencies,
    lorentz_force_per_length,
    lorentz_libration_torque,
    orbital_mean_motion,
    resonant_amplification,
    transverse_mode_frequencies,
    transverse_sag_ratio,
)


def base_case(**overrides):
    """A deployed electrodynamic tether trailed from a heavy host spacecraft."""
    case = {
        "altitude_km": 400.0,
        "length_m": 5000.0,
        "linear_density_kg_m": 2.0e-4,
        "tension_n": 1.5,
        "axial_stiffness_n": 1.2e5,
        "current_a": 1.0,
        "magnetic_flux_density_t": 3.0e-5,
        "field_incidence_deg": 90.0,
        "end_mass_a_kg": 200.0,
        "end_mass_b_kg": 20.0,
        "damping_ratio": 0.01,
        "orbital_harmonics": 1,
        "allowable_libration_deg": 15.0,
    }
    case.update(overrides)
    return case


class TestOrbitalMeanMotion(unittest.TestCase):
    def test_surface_orbit_period_is_the_schuler_period(self):
        n = orbital_mean_motion(0.001)
        period_min = 2.0 * math.pi / n / 60.0
        self.assertAlmostEqual(period_min, 84.5, delta=0.2)

    def test_four_hundred_km_orbit_period(self):
        n = orbital_mean_motion(400.0)
        period_min = 2.0 * math.pi / n / 60.0
        self.assertAlmostEqual(period_min, 92.56, delta=0.1)

    def test_mean_motion_decreases_with_altitude(self):
        self.assertLess(orbital_mean_motion(800.0), orbital_mean_motion(400.0))

    def test_zero_altitude_rejected(self):
        with self.assertRaises(ValueError):
            orbital_mean_motion(0.0)

    def test_negative_altitude_rejected(self):
        with self.assertRaises(ValueError):
            orbital_mean_motion(-10.0)

    def test_altitude_beyond_regime_rejected(self):
        with self.assertRaises(ValueError):
            orbital_mean_motion(120000.0)

    def test_non_numeric_altitude_rejected(self):
        with self.assertRaises(ValueError):
            orbital_mean_motion("400")

    def test_boolean_altitude_rejected(self):
        with self.assertRaises(ValueError):
            orbital_mean_motion(True)

    def test_nan_altitude_rejected(self):
        with self.assertRaises(ValueError):
            orbital_mean_motion(float("nan"))

    def test_infinite_altitude_rejected(self):
        with self.assertRaises(ValueError):
            orbital_mean_motion(float("inf"))


class TestModeTable(unittest.TestCase):
    def test_libration_frequency_ratio(self):
        modes = libration_mode_frequencies(1.0e-3)
        ratio = modes[IN_PLANE_LIBRATION] / modes[OUT_OF_PLANE_LIBRATION]
        self.assertAlmostEqual(ratio, math.sqrt(3.0) / 2.0, places=12)

    def test_out_of_plane_libration_is_twice_mean_motion(self):
        modes = libration_mode_frequencies(2.5e-3)
        self.assertAlmostEqual(modes[OUT_OF_PLANE_LIBRATION], 5.0e-3, places=12)

    def test_libration_rejects_zero_mean_motion(self):
        with self.assertRaises(ValueError):
            libration_mode_frequencies(0.0)

    def test_transverse_first_mode_from_wave_speed(self):
        # tension/density chosen so the wave speed is exactly 100 m/s
        modes = transverse_mode_frequencies(1000.0, 1.0, 1.0e-4, mode_count=1)
        self.assertAlmostEqual(modes["transverse-mode-1"], math.pi * 100.0 / 1000.0,
                               places=10)

    def test_transverse_modes_are_integer_multiples(self):
        modes = transverse_mode_frequencies(2000.0, 4.0, 1.0e-3, mode_count=3)
        self.assertAlmostEqual(modes["transverse-mode-3"] / modes["transverse-mode-1"],
                               3.0, places=10)

    def test_transverse_frequency_scales_with_root_tension(self):
        low = transverse_mode_frequencies(1000.0, 2.0, 1.0e-3, mode_count=1)
        high = transverse_mode_frequencies(1000.0, 8.0, 1.0e-3, mode_count=1)
        self.assertAlmostEqual(
            high["transverse-mode-1"] / low["transverse-mode-1"], 2.0, places=10
        )

    def test_transverse_rejects_slack_tether(self):
        with self.assertRaises(ValueError):
            transverse_mode_frequencies(1000.0, 0.0, 1.0e-3)

    def test_transverse_rejects_zero_mode_count(self):
        with self.assertRaises(ValueError):
            transverse_mode_frequencies(1000.0, 1.0, 1.0e-3, mode_count=0)

    def test_transverse_rejects_excessive_mode_count(self):
        with self.assertRaises(ValueError):
            transverse_mode_frequencies(1000.0, 1.0, 1.0e-3, mode_count=99)

    def test_transverse_rejects_float_mode_count(self):
        with self.assertRaises(ValueError):
            transverse_mode_frequencies(1000.0, 1.0, 1.0e-3, mode_count=2.0)

    def test_longitudinal_is_far_stiffer_than_transverse(self):
        axial = longitudinal_mode_frequencies(5000.0, 1.2e5, 2.0e-4, mode_count=1)
        lateral = transverse_mode_frequencies(5000.0, 1.5, 2.0e-4, mode_count=1)
        self.assertGreater(axial["longitudinal-mode-1"], lateral["transverse-mode-1"])

    def test_longitudinal_rejects_zero_stiffness(self):
        with self.assertRaises(ValueError):
            longitudinal_mode_frequencies(5000.0, 0.0, 2.0e-4)

    def test_mode_table_carries_every_family(self):
        table = build_mode_table(base_case())
        self.assertIn(IN_PLANE_LIBRATION, table)
        self.assertIn("transverse-mode-1", table)
        self.assertIn("longitudinal-mode-1", table)


class TestLorentzForcing(unittest.TestCase):
    def test_perpendicular_field_gives_full_load(self):
        self.assertAlmostEqual(
            lorentz_force_per_length(2.0, 1.0e-4, 90.0), 2.0e-4, places=12
        )

    def test_thirty_degree_incidence_halves_the_load(self):
        self.assertAlmostEqual(
            lorentz_force_per_length(2.0, 1.0e-4, 30.0), 1.0e-4, places=12
        )

    def test_aligned_field_gives_no_load(self):
        self.assertAlmostEqual(
            lorentz_force_per_length(2.0, 1.0e-4, 0.0), 0.0, places=12
        )

    def test_antiparallel_field_gives_no_load(self):
        self.assertAlmostEqual(
            lorentz_force_per_length(2.0, 1.0e-4, 180.0), 0.0, places=12
        )

    def test_zero_current_rejected(self):
        with self.assertRaises(ValueError):
            lorentz_force_per_length(0.0, 1.0e-4, 90.0)

    def test_negative_flux_density_rejected(self):
        with self.assertRaises(ValueError):
            lorentz_force_per_length(1.0, -1.0e-4, 90.0)

    def test_incidence_beyond_half_turn_rejected(self):
        with self.assertRaises(ValueError):
            lorentz_force_per_length(1.0, 1.0e-4, 200.0)

    def test_negative_incidence_rejected(self):
        with self.assertRaises(ValueError):
            lorentz_force_per_length(1.0, 1.0e-4, -5.0)

    def test_spectrum_has_one_line_per_orbital_harmonic(self):
        lines = forcing_spectrum(1.0e-3, orbital_harmonics=3)
        self.assertEqual(len(lines), 3)

    def test_second_orbital_harmonic_is_twice_mean_motion(self):
        lines = forcing_spectrum(1.0e-3, orbital_harmonics=2)
        self.assertAlmostEqual(lines[1]["omega_rad_s"], 2.0e-3, places=12)

    def test_current_modulation_adds_two_lines(self):
        plain = forcing_spectrum(1.0e-3, orbital_harmonics=2)
        switched = forcing_spectrum(1.0e-3, current_modulation_hz=0.05,
                                    orbital_harmonics=2)
        self.assertEqual(len(switched) - len(plain), 2)

    def test_current_modulation_fundamental_is_angular(self):
        lines = forcing_spectrum(1.0e-3, current_modulation_hz=0.5, orbital_harmonics=1)
        self.assertAlmostEqual(lines[1]["omega_rad_s"], math.pi, places=10)

    def test_zero_modulation_rate_rejected(self):
        with self.assertRaises(ValueError):
            forcing_spectrum(1.0e-3, current_modulation_hz=0.0)

    def test_zero_orbital_harmonics_rejected(self):
        with self.assertRaises(ValueError):
            forcing_spectrum(1.0e-3, orbital_harmonics=0)

    def test_boolean_orbital_harmonics_rejected(self):
        with self.assertRaises(ValueError):
            forcing_spectrum(1.0e-3, orbital_harmonics=True)


class TestResonanceCategorization(unittest.TestCase):
    def setUp(self):
        self.table = {
            IN_PLANE_LIBRATION: 1.0e-3,
            OUT_OF_PLANE_LIBRATION: 2.0e-3,
            "transverse-mode-1": 5.0e-2,
            "longitudinal-mode-1": 1.5e1,
        }

    def test_exact_hit_is_categorized_as_libration_resonance(self):
        verdict = categorize_resonance(2.0e-3, self.table, 0.05)
        self.assertEqual(verdict["category"], "libration-resonance")
        self.assertEqual(verdict["mode"], OUT_OF_PLANE_LIBRATION)

    def test_exact_hit_has_zero_detuning(self):
        verdict = categorize_resonance(1.0e-3, self.table, 0.05)
        self.assertAlmostEqual(verdict["detuning_fraction"], 0.0, places=12)

    def test_transverse_family_is_categorized(self):
        verdict = categorize_resonance(5.0e-2, self.table, 0.05)
        self.assertEqual(verdict["category"], "transverse-string-resonance")

    def test_longitudinal_family_is_categorized(self):
        verdict = categorize_resonance(1.5e1, self.table, 0.05)
        self.assertEqual(verdict["category"], "longitudinal-resonance")

    def test_band_edge_counts_as_resonant(self):
        # Exactly on the detuning band edge: a sum of floats that can round a
        # few units in the last place high must still read as resonant.
        edge = 2.0e-3 * (1.0 + 0.05)
        verdict = categorize_resonance(edge, self.table, 0.05)
        self.assertTrue(verdict["resonant"])

    def test_just_outside_band_is_off_resonance(self):
        verdict = categorize_resonance(2.0e-3 * 1.2, self.table, 0.05)
        self.assertEqual(verdict["category"], OFF_RESONANCE)

    def test_off_resonance_names_no_mode(self):
        verdict = categorize_resonance(2.0e-3 * 1.2, self.table, 0.05)
        self.assertIsNone(verdict["mode"])

    def test_off_resonance_still_reports_the_nearest_mode(self):
        verdict = categorize_resonance(2.0e-3 * 1.2, self.table, 0.05)
        self.assertEqual(verdict["nearest_mode"], OUT_OF_PLANE_LIBRATION)

    def test_wider_band_captures_a_previously_detuned_line(self):
        verdict = categorize_resonance(2.0e-3 * 1.2, self.table, 0.3)
        self.assertTrue(verdict["resonant"])

    def test_empty_mode_table_rejected(self):
        with self.assertRaises(ValueError):
            categorize_resonance(1.0e-3, {}, 0.05)

    def test_non_mapping_mode_table_rejected(self):
        with self.assertRaises(ValueError):
            categorize_resonance(1.0e-3, [1.0e-3], 0.05)

    def test_non_positive_mode_frequency_rejected(self):
        with self.assertRaises(ValueError):
            categorize_resonance(1.0e-3, {IN_PLANE_LIBRATION: 0.0}, 0.05)

    def test_unrecognised_mode_family_rejected(self):
        with self.assertRaises(ValueError):
            categorize_resonance(1.0, {"mystery-mode": 1.0}, 0.05)

    def test_detune_fraction_at_unity_rejected(self):
        with self.assertRaises(ValueError):
            categorize_resonance(1.0e-3, self.table, 1.0)

    def test_zero_detune_fraction_rejected(self):
        with self.assertRaises(ValueError):
            categorize_resonance(1.0e-3, self.table, 0.0)

    def test_zero_forcing_frequency_rejected(self):
        with self.assertRaises(ValueError):
            categorize_resonance(0.0, self.table, 0.05)


class TestAmplification(unittest.TestCase):
    def test_one_percent_damping_gives_fifty_fold_gain(self):
        self.assertAlmostEqual(resonant_amplification(0.01), 50.0, places=10)

    def test_gain_falls_as_damping_rises(self):
        self.assertLess(resonant_amplification(0.1), resonant_amplification(0.01))

    def test_zero_damping_rejected(self):
        with self.assertRaises(ValueError):
            resonant_amplification(0.0)

    def test_negative_damping_rejected(self):
        with self.assertRaises(ValueError):
            resonant_amplification(-0.01)

    def test_supercritical_damping_rejected(self):
        with self.assertRaises(ValueError):
            resonant_amplification(1.5)


class TestGeometryAndResponse(unittest.TestCase):
    def test_symmetric_dumbbell_balances_at_midspan(self):
        offset = center_of_mass_offset(1000.0, 1.0e-4, 50.0, 50.0)
        self.assertAlmostEqual(offset, 500.0, places=6)

    def test_heavy_host_pulls_the_balance_point_towards_it(self):
        offset = center_of_mass_offset(1000.0, 1.0e-4, 500.0, 5.0)
        self.assertLess(offset, 100.0)

    def test_offset_never_leaves_the_span(self):
        offset = center_of_mass_offset(1000.0, 1.0e-4, 0.0, 500.0)
        self.assertLessEqual(offset, 1000.0)

    def test_offset_rejects_zero_length(self):
        with self.assertRaises(ValueError):
            center_of_mass_offset(0.0, 1.0e-4, 10.0, 10.0)

    def test_offset_rejects_negative_end_mass(self):
        with self.assertRaises(ValueError):
            center_of_mass_offset(1000.0, 1.0e-4, -1.0, 10.0)

    def test_symmetric_dumbbell_inertia_matches_hand_value(self):
        # Two 50 kg tips on a near-massless 1000 m strand: 2 * m * (L/2)^2.
        inertia = libration_inertia(1000.0, 1.0e-9, 50.0, 50.0)
        self.assertAlmostEqual(inertia, 2.0 * 50.0 * 500.0 ** 2, delta=1.0)

    def test_inertia_grows_with_length(self):
        short = libration_inertia(1000.0, 2.0e-4, 100.0, 10.0)
        long_ = libration_inertia(4000.0, 2.0e-4, 100.0, 10.0)
        self.assertGreater(long_, short)

    def test_symmetric_tether_takes_no_net_lorentz_torque(self):
        torque = lorentz_libration_torque(1.0e-4, 1000.0, 500.0)
        self.assertAlmostEqual(torque, 0.0, places=10)

    def test_offset_balance_point_takes_a_net_torque(self):
        torque = lorentz_libration_torque(1.0e-4, 1000.0, 100.0)
        self.assertGreater(torque, 0.0)

    def test_torque_rejects_offset_outside_the_span(self):
        with self.assertRaises(ValueError):
            lorentz_libration_torque(1.0e-4, 1000.0, 1500.0)

    def test_torque_rejects_negative_load(self):
        with self.assertRaises(ValueError):
            lorentz_libration_torque(-1.0e-4, 1000.0, 100.0)

    def test_resonant_response_is_the_quasi_static_times_gain(self):
        static = libration_response_deg(100.0, 1.0e6, 1.0e-3, 0.01, False)
        peak = libration_response_deg(100.0, 1.0e6, 1.0e-3, 0.01, True)
        self.assertAlmostEqual(peak / static, 50.0, places=8)

    def test_quasi_static_response_matches_hand_value(self):
        # torque / (I * omega^2) = 0.1 / (1e6 * 1e-6) = 0.1 rad
        response = libration_response_deg(0.1, 1.0e6, 1.0e-3, 0.05, False)
        self.assertAlmostEqual(response, math.degrees(0.1), places=8)

    def test_response_rejects_non_boolean_resonance_flag(self):
        with self.assertRaises(ValueError):
            libration_response_deg(100.0, 1.0e6, 1.0e-3, 0.01, "yes")

    def test_response_validates_damping_even_when_off_resonance(self):
        with self.assertRaises(ValueError):
            libration_response_deg(100.0, 1.0e6, 1.0e-3, 0.0, False)

    def test_response_rejects_zero_inertia(self):
        with self.assertRaises(ValueError):
            libration_response_deg(100.0, 0.0, 1.0e-3, 0.01, False)

    def test_sag_ratio_matches_hand_value(self):
        self.assertAlmostEqual(transverse_sag_ratio(1.0e-3, 1000.0, 10.0),
                               0.0125, places=10)

    def test_sag_ratio_falls_as_tension_rises(self):
        self.assertLess(transverse_sag_ratio(1.0e-3, 1000.0, 20.0),
                        transverse_sag_ratio(1.0e-3, 1000.0, 10.0))

    def test_sag_ratio_rejects_slack_tether(self):
        with self.assertRaises(ValueError):
            transverse_sag_ratio(1.0e-3, 1000.0, 0.0)


class TestAssessment(unittest.TestCase):
    def test_baseline_case_is_compliant(self):
        result = assess_oscillation_hazards(base_case())
        self.assertTrue(result["compliant"])

    def test_compliant_case_carries_no_findings(self):
        result = assess_oscillation_hazards(base_case())
        self.assertEqual(result["findings"], [])

    def test_first_orbital_harmonic_alone_is_off_resonance(self):
        result = assess_oscillation_hazards(base_case())
        self.assertEqual(result["resonances"][0]["category"], OFF_RESONANCE)

    def test_second_orbital_harmonic_pumps_out_of_plane_libration(self):
        result = assess_oscillation_hazards(base_case(orbital_harmonics=2))
        hits = [r for r in result["resonances"] if r["mode"] == OUT_OF_PLANE_LIBRATION]
        self.assertEqual(len(hits), 1)

    def test_resonant_case_is_not_compliant(self):
        result = assess_oscillation_hazards(base_case(orbital_harmonics=2))
        self.assertFalse(result["compliant"])

    def test_resonance_amplifies_the_libration_amplitude(self):
        quiet = assess_oscillation_hazards(base_case())
        pumped = assess_oscillation_hazards(base_case(orbital_harmonics=2))
        self.assertGreater(pumped["libration_amplitude_deg"],
                           quiet["libration_amplitude_deg"])

    def test_pumped_case_crosses_the_tumbling_separatrix(self):
        result = assess_oscillation_hazards(base_case(orbital_harmonics=2))
        self.assertGreater(result["libration_amplitude_deg"], TUMBLE_SEPARATRIX_DEG)
        self.assertTrue(any("separatrix" in f for f in result["findings"]))

    def test_amplitude_exactly_on_the_allowable_stays_compliant(self):
        first = assess_oscillation_hazards(base_case())
        exact = assess_oscillation_hazards(
            base_case(allowable_libration_deg=first["libration_amplitude_deg"])
        )
        self.assertTrue(exact["compliant"])

    def test_amplitude_over_the_allowable_is_flagged(self):
        result = assess_oscillation_hazards(base_case(allowable_libration_deg=1.0))
        self.assertTrue(any("allowable" in f for f in result["findings"]))

    def test_low_tension_trips_the_slack_onset_limit(self):
        result = assess_oscillation_hazards(base_case(tension_n=0.2))
        self.assertTrue(any("slack-onset" in f for f in result["findings"]))

    def test_sag_ratio_exactly_on_the_limit_stays_compliant(self):
        first = assess_oscillation_hazards(base_case())
        exact = assess_oscillation_hazards(
            base_case(sag_ratio_limit=first["sag_ratio"])
        )
        self.assertTrue(exact["compliant"])

    def test_symmetric_tether_librates_negligibly(self):
        result = assess_oscillation_hazards(
            base_case(end_mass_a_kg=100.0, end_mass_b_kg=100.0)
        )
        self.assertAlmostEqual(result["libration_amplitude_deg"], 0.0, places=6)

    def test_switched_current_adds_forcing_lines(self):
        plain = assess_oscillation_hazards(base_case())
        switched = assess_oscillation_hazards(base_case(current_modulation_hz=0.01))
        self.assertGreater(len(switched["forcing_lines"]), len(plain["forcing_lines"]))

    def test_switched_current_can_strike_a_transverse_mode(self):
        # The first transverse mode of the baseline strand sits near 0.0544 rad/s.
        table = build_mode_table(base_case())
        rate = table["transverse-mode-1"] / (2.0 * math.pi)
        result = assess_oscillation_hazards(base_case(current_modulation_hz=rate))
        self.assertTrue(
            any(r["category"] == "transverse-string-resonance"
                for r in result["resonances"])
        )

    def test_aligned_field_removes_the_lorentz_load(self):
        result = assess_oscillation_hazards(base_case(field_incidence_deg=0.0))
        self.assertAlmostEqual(result["lorentz_load_n_m"], 0.0, places=12)

    def test_default_detuning_fraction_is_applied(self):
        result = assess_oscillation_hazards(base_case())
        edge = result["resonances"][0]["detuning_fraction"]
        self.assertGreater(edge, DEFAULT_DETUNE_FRACTION)

    def test_missing_required_key_rejected(self):
        case = base_case()
        del case["tension_n"]
        with self.assertRaises(ValueError):
            assess_oscillation_hazards(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_oscillation_hazards(["altitude_km", 400.0])

    def test_bad_damping_ratio_rejected_by_assessment(self):
        with self.assertRaises(ValueError):
            assess_oscillation_hazards(base_case(damping_ratio=0.0))

    def test_bad_sag_limit_rejected_by_assessment(self):
        with self.assertRaises(ValueError):
            assess_oscillation_hazards(base_case(sag_ratio_limit=-0.1))

    def test_bad_allowable_libration_rejected_by_assessment(self):
        with self.assertRaises(ValueError):
            assess_oscillation_hazards(base_case(allowable_libration_deg=0.0))

    def test_assessment_reports_every_mode_family(self):
        result = assess_oscillation_hazards(base_case())
        self.assertIn("longitudinal-mode-1", result["modes"])


if __name__ == "__main__":
    unittest.main()
