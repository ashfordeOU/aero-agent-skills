"""Contract tests for the radiation environment definition logic."""

import unittest

from q7006_radiation_environment_definition_logic import (
    SECONDS_PER_YEAR,
    SOLAR_UV_IRRADIANCE_W_M2,
    coverage_findings,
    define_environment,
    differential_flux_at,
    energy_window,
    integral_flux,
    phase_particle_fluence,
    phase_uv_dose_esh,
    uv_dose_from_irradiance,
    validate_spectrum,
)

# A flat differential spectrum makes the trapezoidal integral exact and
# analytically checkable: 100 per cm^2/s/MeV between 0.1 and 10.1 MeV.
FLAT = [(0.1, 100.0), (10.1, 100.0)]

# A falling spectrum with an interior node, as a real trapped-electron
# differential spectrum would be tabulated.
FALLING = [(0.1, 1000.0), (1.0, 100.0), (5.0, 10.0), (10.0, 1.0)]


def base_spec(**overrides):
    spec = {
        "spectrum": list(FLAT),
        "phases": [
            {"name": "transfer", "years": 0.5, "sun_fraction": 1.0},
            {"name": "operations", "years": 5.0, "sun_fraction": 0.62, "duty_fraction": 1.0},
        ],
    }
    spec.update(overrides)
    return spec


class ValidateSpectrumTests(unittest.TestCase):
    def test_returns_float_pairs(self):
        self.assertEqual(validate_spectrum([(1, 2), (3, 4)]), [(1.0, 2.0), (3.0, 4.0)])

    def test_single_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(1.0, 2.0)])

    def test_repeated_energy_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(1.0, 2.0), (1.0, 3.0)])

    def test_descending_energy_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(3.0, 2.0), (1.0, 3.0)])

    def test_negative_flux_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(1.0, -2.0), (3.0, 4.0)])

    def test_zero_energy_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(0.0, 2.0), (3.0, 4.0)])

    def test_all_zero_flux_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(1.0, 0.0), (3.0, 0.0)])

    def test_malformed_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(1.0, 2.0), (3.0,)])

    def test_energy_window_is_the_tabulated_span(self):
        self.assertEqual(energy_window(FALLING), (0.1, 10.0))


class DifferentialFluxTests(unittest.TestCase):
    def test_tabulated_point_returned_exactly(self):
        self.assertAlmostEqual(differential_flux_at(FALLING, 1.0), 100.0, places=9)

    def test_interpolates_inside_a_bin(self):
        self.assertAlmostEqual(differential_flux_at(FALLING, 3.0), 55.0, places=9)

    def test_lower_edge_allowed(self):
        self.assertAlmostEqual(differential_flux_at(FALLING, 0.1), 1000.0, places=9)

    def test_upper_edge_allowed(self):
        self.assertAlmostEqual(differential_flux_at(FALLING, 10.0), 1.0, places=9)

    def test_below_window_refused(self):
        with self.assertRaises(ValueError):
            differential_flux_at(FALLING, 0.01)

    def test_above_window_refused(self):
        with self.assertRaises(ValueError):
            differential_flux_at(FALLING, 40.0)


class IntegralFluxTests(unittest.TestCase):
    def test_flat_spectrum_integral_is_exact(self):
        self.assertAlmostEqual(integral_flux(FLAT), 1000.0, places=9)

    def test_partial_window_of_a_flat_spectrum(self):
        self.assertAlmostEqual(integral_flux(FLAT, 1.1, 3.1), 200.0, places=9)

    def test_window_edges_interpolated_inside_a_bin(self):
        whole = integral_flux(FALLING)
        lower = integral_flux(FALLING, 0.1, 3.0)
        upper = integral_flux(FALLING, 3.0, 10.0)
        self.assertAlmostEqual(lower + upper, whole, places=9)

    def test_zero_width_window_gives_zero(self):
        self.assertAlmostEqual(integral_flux(FALLING, 2.0, 2.0), 0.0, places=9)

    def test_window_outside_the_table_refused(self):
        with self.assertRaises(ValueError):
            integral_flux(FALLING, 0.05, 10.0)

    def test_inverted_window_refused(self):
        with self.assertRaises(ValueError):
            integral_flux(FALLING, 5.0, 1.0)

    def test_soft_part_of_a_falling_spectrum_dominates(self):
        soft = integral_flux(FALLING, 0.1, 1.0)
        hard = integral_flux(FALLING, 1.0, 10.0)
        self.assertGreater(soft, hard)


class PhaseAccumulationTests(unittest.TestCase):
    def test_fluence_is_flux_times_exposed_seconds(self):
        value = phase_particle_fluence(FLAT, 1.0)
        self.assertAlmostEqual(value, 1000.0 * SECONDS_PER_YEAR, places=3)

    def test_duty_fraction_halves_the_fluence(self):
        full = phase_particle_fluence(FLAT, 2.0)
        half = phase_particle_fluence(FLAT, 2.0, duty_fraction=0.5)
        self.assertAlmostEqual(2.0 * half, full, places=3)

    def test_scaling_multiplies_the_spectrum(self):
        base = phase_particle_fluence(FLAT, 1.0)
        scaled = phase_particle_fluence(FLAT, 1.0, scaling=3.0)
        self.assertAlmostEqual(scaled, 3.0 * base, places=3)

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            phase_particle_fluence(FLAT, 0.0)

    def test_duty_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            phase_particle_fluence(FLAT, 1.0, duty_fraction=1.2)

    def test_full_sun_year_in_equivalent_sun_hours(self):
        self.assertAlmostEqual(
            phase_uv_dose_esh(1.0, 1.0), SECONDS_PER_YEAR / 3600.0, places=6
        )

    def test_eclipse_fraction_reduces_the_dose(self):
        self.assertAlmostEqual(
            phase_uv_dose_esh(0.5, 1.0) * 2.0, phase_uv_dose_esh(1.0, 1.0), places=6
        )

    def test_concentrated_intensity_multiplies_the_dose(self):
        self.assertAlmostEqual(
            phase_uv_dose_esh(1.0, 1.0, 4.0), 4.0 * phase_uv_dose_esh(1.0, 1.0), places=6
        )

    def test_one_solar_constant_for_one_hour_is_one_esh(self):
        self.assertAlmostEqual(
            uv_dose_from_irradiance(SOLAR_UV_IRRADIANCE_W_M2, 1.0), 1.0, places=9
        )

    def test_lamp_irradiance_scales_the_equivalent_hours(self):
        self.assertAlmostEqual(
            uv_dose_from_irradiance(3.0 * SOLAR_UV_IRRADIANCE_W_M2, 10.0), 30.0, places=9
        )

    def test_negative_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            uv_dose_from_irradiance(-1.0, 10.0)


class CoverageTests(unittest.TestCase):
    def test_enveloping_facility_has_no_findings(self):
        self.assertEqual(coverage_findings((0.05, 20.0), (0.1, 10.0)), [])

    def test_exactly_matching_window_has_no_findings(self):
        self.assertEqual(coverage_findings((0.1, 10.0), (0.1, 10.0)), [])

    def test_soft_end_shortfall_reported(self):
        notes = coverage_findings((1.0, 20.0), (0.1, 10.0))
        self.assertEqual(len(notes), 1)
        self.assertIn("starts at", notes[0])

    def test_hard_end_shortfall_reported(self):
        notes = coverage_findings((0.05, 4.0), (0.1, 10.0))
        self.assertEqual(len(notes), 1)
        self.assertIn("reaches", notes[0])

    def test_both_ends_short_gives_two_findings(self):
        self.assertEqual(len(coverage_findings((1.0, 4.0), (0.1, 10.0))), 2)

    def test_inverted_facility_window_rejected(self):
        with self.assertRaises(ValueError):
            coverage_findings((20.0, 1.0), (0.1, 10.0))

    def test_malformed_window_rejected(self):
        with self.assertRaises(ValueError):
            coverage_findings((1.0,), (0.1, 10.0))


class DefineEnvironmentTests(unittest.TestCase):
    def test_phase_fluences_sum_to_the_mission_fluence(self):
        result = define_environment(base_spec())
        total = sum(p["particle_fluence"] for p in result["phases"])
        self.assertAlmostEqual(total, result["particle_fluence"], places=3)

    def test_mission_years_are_summed(self):
        self.assertAlmostEqual(define_environment(base_spec())["mission_years"], 5.5, places=9)

    def test_energy_window_is_reported(self):
        self.assertEqual(define_environment(base_spec())["energy_window_mev"], (0.1, 10.1))

    def test_complete_definition_has_no_findings(self):
        result = define_environment(base_spec())
        self.assertTrue(result["definition_complete"])
        self.assertEqual(result["findings"], [])

    def test_dark_mission_is_flagged(self):
        spec = base_spec(phases=[{"years": 2.0, "sun_fraction": 0.0}])
        result = define_environment(spec)
        self.assertFalse(result["definition_complete"])
        self.assertTrue(any("ultraviolet" in note for note in result["findings"]))

    def test_facility_shortfall_becomes_a_finding(self):
        result = define_environment(base_spec(facility_window=(0.5, 5.0)))
        self.assertEqual(len(result["findings"]), 2)

    def test_energy_window_restricts_the_integral(self):
        wide = define_environment(base_spec())
        narrow = define_environment(base_spec(e_min=1.1, e_max=3.1))
        self.assertLess(narrow["particle_fluence"], wide["particle_fluence"])

    def test_empty_phase_list_rejected(self):
        with self.assertRaises(ValueError):
            define_environment(base_spec(phases=[]))

    def test_phase_without_duration_rejected(self):
        with self.assertRaises(ValueError):
            define_environment(base_spec(phases=[{"sun_fraction": 1.0}]))

    def test_missing_spectrum_rejected(self):
        spec = base_spec()
        del spec["spectrum"]
        with self.assertRaises(ValueError):
            define_environment(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            define_environment(["spectrum"])

    def test_unnamed_phases_get_positional_names(self):
        spec = base_spec(phases=[{"years": 1.0, "sun_fraction": 1.0}])
        self.assertEqual(define_environment(spec)["phases"][0]["name"], "phase-1")


if __name__ == "__main__":
    unittest.main()
