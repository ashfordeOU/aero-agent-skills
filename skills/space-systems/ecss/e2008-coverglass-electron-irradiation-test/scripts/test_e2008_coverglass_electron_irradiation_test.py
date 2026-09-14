"""Contract tests for the clause 8.7.13 coverglass electron irradiation test."""

import copy
import unittest

from e2008_coverglass_electron_irradiation_test_logic import (
    BANDS,
    DENSITY_NOISE_ALLOWANCE,
    GRAY_PER_MEV_PER_GRAM,
    MAX_FLUX_E_PER_CM2_S,
    MAX_TRAVERSAL_RATIO,
    MIN_TRAVERSAL_RATIO,
    RANGE_DENSITY_G_PER_CM3,
    STOPPING_POWER_MEV_CM2_G,
    TOLERANCE,
    absorbed_dose_gy,
    assess_coverglass_electron_irradiation,
    beam_flux,
    density_monotonicity_findings,
    density_series,
    electron_range_um,
    energy_findings,
    fit_density_power_law,
    flux_findings,
    grounding_findings,
    optical_density,
    predict_density,
    traversal_ratio,
    transmittance_from_density,
)

REFERENCE = {"ultraviolet": 0.90, "visible": 0.95, "near-infrared": 0.93}
BASE_DENSITY = {
    "ultraviolet": 0.004,
    "visible": 0.002,
    "near-infrared": 0.001,
}
FLUENCES = [1.0e13, 1.0e14, 1.0e15]
DURATIONS = [1.0e4, 1.0e5, 1.0e6]
EXPONENT = 0.5
COATING_UM = 0.5
GLASS_UM = 150.0
BEAM_MEV = 1.0


def density_at(band, fluence):
    return BASE_DENSITY[band] * (fluence / FLUENCES[0]) ** EXPONENT


def scan_at(fluence):
    return {
        band: REFERENCE[band] * 10.0 ** (-density_at(band, fluence))
        for band in BANDS
    }


def step_at(index):
    return {
        "label": "step-%d" % (index + 1),
        "fluence_e_per_cm2": FLUENCES[index],
        "duration_s": DURATIONS[index],
        "scan": scan_at(FLUENCES[index]),
    }


def spec(**overrides):
    base = {
        "reference_scan": dict(REFERENCE),
        "steps": [step_at(0), step_at(1), step_at(2)],
        "beam_energy_mev": BEAM_MEV,
        "coating_thickness_um": COATING_UM,
        "glass_thickness_um": GLASS_UM,
        "eol_fluence_e_per_cm2": 1.0e16,
        "required_transmittance": {"visible": 0.80},
        "coating_is_conductive": True,
        "coating_is_grounded": True,
    }
    base.update(overrides)
    return base


class RangeTests(unittest.TestCase):
    def test_range_rises_with_energy(self):
        self.assertGreater(
            electron_range_um(1.0), electron_range_um(0.3) + 100.0
        )

    def test_megaelectronvolt_range_crosses_a_coverglass(self):
        self.assertGreater(electron_range_um(1.0), 1000.0)

    def test_denser_glass_stops_the_beam_sooner(self):
        dense = electron_range_um(1.0, 4.4)
        light = electron_range_um(1.0, 2.2)
        self.assertAlmostEqual(dense * 2.0, light, places=6)

    def test_zero_energy_rejected(self):
        with self.assertRaises(ValueError):
            electron_range_um(0.0)

    def test_boolean_energy_rejected(self):
        with self.assertRaises(ValueError):
            electron_range_um(True)

    def test_default_glass_density(self):
        self.assertAlmostEqual(RANGE_DENSITY_G_PER_CM3, 2.2, places=9)

    def test_traversal_ratio_is_range_over_thickness(self):
        ratio = traversal_ratio(BEAM_MEV, COATING_UM, GLASS_UM)
        expected = electron_range_um(BEAM_MEV) / (COATING_UM + GLASS_UM)
        self.assertAlmostEqual(ratio, expected, places=9)

    def test_zero_glass_thickness_rejected(self):
        with self.assertRaises(ValueError):
            traversal_ratio(BEAM_MEV, COATING_UM, 0.0)


class BeamEnergyTests(unittest.TestCase):
    def test_megaelectronvolt_beam_gives_no_finding(self):
        self.assertEqual(energy_findings(BEAM_MEV, COATING_UM, GLASS_UM), [])

    def test_soft_beam_front_loads_the_damage(self):
        findings = energy_findings(0.1, COATING_UM, GLASS_UM)
        self.assertEqual(len(findings), 1)
        self.assertIn("front-loaded", findings[0])

    def test_beam_far_past_the_ceiling_is_a_finding(self):
        findings = energy_findings(
            BEAM_MEV, COATING_UM, GLASS_UM, max_ratio=2.0
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("too little behind", findings[0])

    def test_ceiling_below_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            energy_findings(
                BEAM_MEV, COATING_UM, GLASS_UM, min_ratio=10.0, max_ratio=2.0
            )

    def test_default_traversal_window(self):
        self.assertAlmostEqual(MIN_TRAVERSAL_RATIO, 1.0, places=9)
        self.assertAlmostEqual(MAX_TRAVERSAL_RATIO, 100.0, places=9)


class DoseTests(unittest.TestCase):
    def test_dose_scales_with_fluence(self):
        self.assertAlmostEqual(
            absorbed_dose_gy(2.0e15), 2.0 * absorbed_dose_gy(1.0e15), places=6
        )

    def test_dose_of_a_known_fluence(self):
        expected = 1.0e15 * STOPPING_POWER_MEV_CM2_G * GRAY_PER_MEV_PER_GRAM
        self.assertAlmostEqual(absorbed_dose_gy(1.0e15), expected, places=6)

    def test_zero_fluence_rejected(self):
        with self.assertRaises(ValueError):
            absorbed_dose_gy(0.0)

    def test_zero_stopping_power_rejected(self):
        with self.assertRaises(ValueError):
            absorbed_dose_gy(1.0e15, 0.0)

    def test_default_stopping_power(self):
        self.assertAlmostEqual(STOPPING_POWER_MEV_CM2_G, 1.85, places=9)


class FluxTests(unittest.TestCase):
    def test_flux_is_fluence_over_time(self):
        self.assertAlmostEqual(beam_flux(1.0e13, 1.0e4), 1.0e9, places=3)

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            beam_flux(1.0e13, 0.0)

    def test_slow_step_gives_no_finding(self):
        self.assertEqual(flux_findings("step-1", 1.0e13, 1.0e4), [])

    def test_flux_exactly_on_the_cap_is_accepted(self):
        self.assertEqual(
            flux_findings("step-1", MAX_FLUX_E_PER_CM2_S, 1.0), []
        )

    def test_fast_step_is_a_finding(self):
        findings = flux_findings("step-1", 1.0e15, 1.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("charge and heat", findings[0])

    def test_empty_label_rejected(self):
        with self.assertRaises(ValueError):
            flux_findings("   ", 1.0e13, 1.0e4)

    def test_default_flux_cap(self):
        self.assertAlmostEqual(MAX_FLUX_E_PER_CM2_S, 1.0e10, places=3)


class GroundingTests(unittest.TestCase):
    def test_grounded_conductive_coating_gives_no_finding(self):
        self.assertEqual(grounding_findings(True, True), [])

    def test_ungrounded_conductive_coating_is_a_finding(self):
        findings = grounding_findings(True, False)
        self.assertEqual(len(findings), 1)
        self.assertIn("discharged", findings[0])

    def test_bare_coverglass_needs_no_ground(self):
        self.assertEqual(grounding_findings(False, False), [])

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            grounding_findings("yes", True)


class DensityTests(unittest.TestCase):
    def test_unchanged_reading_gives_zero_density(self):
        self.assertAlmostEqual(optical_density(0.90, 0.90), 0.0, places=9)

    def test_a_tenth_of_the_light_gives_one_density(self):
        self.assertAlmostEqual(optical_density(0.09, 0.90), 1.0, places=9)

    def test_density_matches_the_fixture(self):
        scan = scan_at(FLUENCES[1])
        for band in BANDS:
            self.assertAlmostEqual(
                optical_density(scan[band], REFERENCE[band]),
                density_at(band, FLUENCES[1]),
                places=9,
            )

    def test_zero_transmittance_rejected(self):
        with self.assertRaises(ValueError):
            optical_density(0.0, 0.90)

    def test_transmittance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            optical_density(1.5, 0.90)

    def test_series_covers_every_band_and_step(self):
        series = density_series(REFERENCE, [scan_at(f) for f in FLUENCES])
        self.assertEqual(sorted(series), sorted(BANDS))
        for values in series.values():
            self.assertEqual(len(values), 3)

    def test_scan_missing_a_band_rejected(self):
        with self.assertRaises(ValueError):
            density_series(REFERENCE, [{"visible": 0.9}])

    def test_scan_with_an_unknown_band_rejected(self):
        scan = dict(scan_at(FLUENCES[0]))
        scan["x-ray"] = 0.5
        with self.assertRaises(ValueError):
            density_series(REFERENCE, [scan])

    def test_empty_step_list_rejected(self):
        with self.assertRaises(ValueError):
            density_series(REFERENCE, [])

    def test_transmittance_from_density_is_the_inverse(self):
        density = density_at("visible", FLUENCES[2])
        left = transmittance_from_density(REFERENCE["visible"], density)
        self.assertAlmostEqual(
            optical_density(left, REFERENCE["visible"]), density, places=9
        )


class MonotonicityTests(unittest.TestCase):
    def test_rising_density_gives_no_finding(self):
        densities = [density_at("visible", f) for f in FLUENCES]
        self.assertEqual(
            density_monotonicity_findings("visible", FLUENCES, densities), []
        )

    def test_lightening_step_is_a_finding(self):
        findings = density_monotonicity_findings(
            "visible", FLUENCES, [0.02, 0.05, 0.01]
        )
        self.assertTrue(any("lightened" in item for item in findings))

    def test_density_below_the_unirradiated_scan_is_a_finding(self):
        findings = density_monotonicity_findings(
            "visible", FLUENCES, [-0.05, 0.02, 0.04]
        )
        self.assertTrue(any("brighter" in item for item in findings))

    def test_fall_inside_the_noise_allowance_is_accepted(self):
        densities = [0.02, 0.05, 0.05 - DENSITY_NOISE_ALLOWANCE / 2.0]
        self.assertEqual(
            density_monotonicity_findings("visible", FLUENCES, densities), []
        )

    def test_unknown_band_rejected(self):
        with self.assertRaises(ValueError):
            density_monotonicity_findings("x-ray", FLUENCES, [0.01, 0.02, 0.03])

    def test_density_count_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            density_monotonicity_findings("visible", FLUENCES, [0.01, 0.02])

    def test_falling_fluence_rejected(self):
        with self.assertRaises(ValueError):
            density_monotonicity_findings(
                "visible", [1.0e15, 1.0e13], [0.01, 0.02]
            )

    def test_default_noise_allowance(self):
        self.assertAlmostEqual(DENSITY_NOISE_ALLOWANCE, 0.0005, places=9)

    def test_tolerance_is_small(self):
        self.assertAlmostEqual(TOLERANCE, 1e-9, places=12)


class FitTests(unittest.TestCase):
    def setUp(self):
        self.densities = [density_at("ultraviolet", f) for f in FLUENCES]
        self.fit = fit_density_power_law(FLUENCES, self.densities)

    def test_exponent_recovers_the_fixture(self):
        self.assertAlmostEqual(self.fit["exponent"], EXPONENT, places=9)

    def test_point_count_is_reported(self):
        self.assertEqual(self.fit["point_count"], 3)

    def test_fit_reproduces_every_measured_step(self):
        for fluence, density in zip(FLUENCES, self.densities):
            self.assertAlmostEqual(
                predict_density(self.fit, fluence), density, places=9
            )

    def test_projection_follows_the_power_law(self):
        self.assertAlmostEqual(
            predict_density(self.fit, 1.0e16),
            density_at("ultraviolet", 1.0e16),
            places=9,
        )

    def test_zero_density_rejected_by_the_fit(self):
        with self.assertRaises(ValueError):
            fit_density_power_law(FLUENCES, [0.0, 0.02, 0.03])

    def test_density_count_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            fit_density_power_law(FLUENCES, [0.01, 0.02])

    def test_prediction_at_zero_fluence_rejected(self):
        with self.assertRaises(ValueError):
            predict_density(self.fit, 0.0)

    def test_fit_without_an_exponent_rejected(self):
        with self.assertRaises(ValueError):
            predict_density({"log_coefficient": 1.0}, 1.0e13)


class AssessmentTests(unittest.TestCase):
    def test_conformant_run_has_no_finding(self):
        result = assess_coverglass_electron_irradiation(spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["run_conformant"])

    def test_every_band_is_reported(self):
        result = assess_coverglass_electron_irradiation(spec())
        self.assertEqual(sorted(result["bands"]), sorted(BANDS))
        self.assertEqual(result["step_count"], 3)

    def test_projected_transmittance_is_reported(self):
        result = assess_coverglass_electron_irradiation(spec())
        band = result["bands"]["visible"]
        expected = transmittance_from_density(
            REFERENCE["visible"], density_at("visible", 1.0e16)
        )
        self.assertAlmostEqual(
            band["projected_transmittance"], expected, places=9
        )

    def test_fitted_exponent_is_reported_per_band(self):
        result = assess_coverglass_electron_irradiation(spec())
        for band in BANDS:
            self.assertAlmostEqual(
                result["bands"][band]["fit"]["exponent"], EXPONENT, places=9
            )

    def test_doses_are_reported(self):
        result = assess_coverglass_electron_irradiation(spec())
        self.assertAlmostEqual(
            result["eol_dose_gy"], absorbed_dose_gy(1.0e16), places=3
        )
        self.assertEqual(len(result["step_doses_gy"]), 3)

    def test_transmittance_shortfall_fails_the_run(self):
        result = assess_coverglass_electron_irradiation(
            spec(required_transmittance={"visible": 0.92})
        )
        self.assertFalse(result["run_conformant"])
        self.assertTrue(
            any("budget asks for" in item for item in result["findings"])
        )

    def test_soft_beam_fails_the_run(self):
        result = assess_coverglass_electron_irradiation(
            spec(beam_energy_mev=0.05)
        )
        self.assertFalse(result["run_conformant"])

    def test_ungrounded_conductive_coating_fails_the_run(self):
        result = assess_coverglass_electron_irradiation(
            spec(coating_is_grounded=False)
        )
        self.assertFalse(result["run_conformant"])

    def test_fast_step_fails_the_run(self):
        state = copy.deepcopy(spec())
        state["steps"][1]["duration_s"] = 1.0
        result = assess_coverglass_electron_irradiation(state)
        self.assertFalse(result["run_conformant"])

    def test_lightening_band_fails_the_run(self):
        state = copy.deepcopy(spec())
        state["steps"][2]["scan"]["visible"] = REFERENCE["visible"]
        result = assess_coverglass_electron_irradiation(state)
        self.assertFalse(result["run_conformant"])

    def test_unfittable_band_reports_no_fit_rather_than_zero(self):
        state = copy.deepcopy(spec())
        state["steps"][2]["scan"]["visible"] = REFERENCE["visible"]
        band = assess_coverglass_electron_irradiation(state)["bands"]["visible"]
        self.assertIsNone(band["fit"])
        self.assertIsNone(band["projected_transmittance"])
        self.assertTrue(any("no power law" in i for i in band["findings"]))

    def test_end_of_life_below_the_last_step_is_a_finding(self):
        result = assess_coverglass_electron_irradiation(
            spec(eol_fluence_e_per_cm2=1.0e14)
        )
        self.assertTrue(
            any("runs backwards" in item for item in result["findings"])
        )

    def test_single_step_run_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_electron_irradiation(spec(steps=[step_at(0)]))

    def test_missing_spec_key_rejected(self):
        state = spec()
        del state["eol_fluence_e_per_cm2"]
        with self.assertRaises(ValueError):
            assess_coverglass_electron_irradiation(state)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_electron_irradiation(["steps"])

    def test_empty_transmittance_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_electron_irradiation(
                spec(required_transmittance={})
            )

    def test_unknown_required_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_electron_irradiation(
                spec(required_transmittance={"x-ray": 0.8})
            )

    def test_step_without_a_duration_rejected(self):
        state = copy.deepcopy(spec())
        del state["steps"][0]["duration_s"]
        with self.assertRaises(ValueError):
            assess_coverglass_electron_irradiation(state)


if __name__ == "__main__":
    unittest.main()
