"""Contract tests for the clause 8.7.14 coverglass proton irradiation test."""

import copy
import unittest

from e2008_coverglass_proton_irradiation_test_logic import (
    BANDS,
    DENSITY_NOISE_ALLOWANCE,
    MAX_FLUX_P_PER_CM2_S,
    RANGE_COEFFICIENT_UM,
    RANGE_EXPONENT,
    REQUIRED_ZONES,
    TOLERANCE,
    ZONES,
    assess_coverglass_proton_irradiation,
    beam_flux,
    brightening_findings,
    combined_density,
    coverage_findings,
    deposition_zone,
    flux_findings,
    line_densities,
    optical_density,
    proton_range_um,
    transmittance_after,
    validate_energy_lines,
    zone_coverage,
)

REFERENCE = {"ultraviolet": 0.90, "visible": 0.95, "near-infrared": 0.93}
COATING_UM = 0.5
GLASS_UM = 150.0
ENERGIES = [0.10, 1.0, 3.0]
FLUENCES = [1.0e12, 5.0e11, 2.0e11]
DURATIONS = [1.0e4, 1.0e4, 1.0e4]
LINE_DENSITY = {
    "ultraviolet": [0.006, 0.010, 0.008],
    "visible": [0.003, 0.005, 0.004],
    "near-infrared": [0.001, 0.002, 0.0015],
}


def scan_for(index):
    return {
        band: REFERENCE[band] * 10.0 ** (-LINE_DENSITY[band][index])
        for band in BANDS
    }


def line_at(index):
    return {
        "label": "line-%d" % (index + 1),
        "energy_mev": ENERGIES[index],
        "fluence_p_per_cm2": FLUENCES[index],
        "duration_s": DURATIONS[index],
        "scan": scan_for(index),
    }


def spec(**overrides):
    base = {
        "reference_scan": dict(REFERENCE),
        "lines": [line_at(0), line_at(1), line_at(2)],
        "coating_thickness_um": COATING_UM,
        "glass_thickness_um": GLASS_UM,
        "required_transmittance": {"visible": 0.90},
    }
    base.update(overrides)
    return base


class RangeTests(unittest.TestCase):
    def test_range_at_one_megaelectronvolt_is_the_coefficient(self):
        self.assertAlmostEqual(
            proton_range_um(1.0), RANGE_COEFFICIENT_UM, places=9
        )

    def test_range_rises_steeply_with_energy(self):
        self.assertGreater(proton_range_um(3.0), proton_range_um(1.0) + 50.0)

    def test_range_follows_the_declared_power(self):
        doubled = proton_range_um(2.0) / proton_range_um(1.0)
        self.assertAlmostEqual(doubled, 2.0 ** RANGE_EXPONENT, places=9)

    def test_zero_energy_rejected(self):
        with self.assertRaises(ValueError):
            proton_range_um(0.0)

    def test_boolean_energy_rejected(self):
        with self.assertRaises(ValueError):
            proton_range_um(True)

    def test_zero_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            proton_range_um(1.0, coefficient_um=0.0)

    def test_default_range_law(self):
        self.assertAlmostEqual(RANGE_COEFFICIENT_UM, 11.0, places=9)
        self.assertAlmostEqual(RANGE_EXPONENT, 1.72, places=9)


class ZoneTests(unittest.TestCase):
    def test_soft_line_stops_in_the_coating(self):
        self.assertEqual(
            deposition_zone(0.10, COATING_UM, GLASS_UM), "coating"
        )

    def test_megaelectronvolt_line_stops_in_the_substrate(self):
        self.assertEqual(
            deposition_zone(1.0, COATING_UM, GLASS_UM), "substrate"
        )

    def test_hard_line_crosses_the_coverglass(self):
        self.assertEqual(
            deposition_zone(10.0, COATING_UM, GLASS_UM), "beyond"
        )

    def test_three_zones_are_named(self):
        self.assertEqual(len(ZONES), 3)
        self.assertEqual(sorted(REQUIRED_ZONES), ["coating", "substrate"])

    def test_zero_coating_thickness_rejected(self):
        with self.assertRaises(ValueError):
            deposition_zone(1.0, 0.0, GLASS_UM)

    def test_a_thicker_coating_takes_the_line_that_was_in_the_glass(self):
        self.assertEqual(deposition_zone(1.0, 20.0, GLASS_UM), "coating")


class EnergyLineTests(unittest.TestCase):
    def test_rising_lines_are_returned_as_floats(self):
        self.assertEqual(validate_energy_lines([1, 2, 3]), [1.0, 2.0, 3.0])

    def test_repeated_line_rejected(self):
        with self.assertRaises(ValueError):
            validate_energy_lines([1.0, 1.0])

    def test_falling_line_rejected(self):
        with self.assertRaises(ValueError):
            validate_energy_lines([3.0, 1.0])

    def test_single_line_rejected(self):
        with self.assertRaises(ValueError):
            validate_energy_lines([1.0])

    def test_negative_line_rejected(self):
        with self.assertRaises(ValueError):
            validate_energy_lines([-1.0, 1.0])


class CoverageTests(unittest.TestCase):
    def test_matrix_reaches_both_layers(self):
        coverage = zone_coverage(ENERGIES, COATING_UM, GLASS_UM)
        self.assertEqual(coverage["coating"], [0.10])
        self.assertEqual(coverage["substrate"], [1.0, 3.0])
        self.assertEqual(coverage["beyond"], [])

    def test_covered_matrix_gives_no_finding(self):
        coverage = zone_coverage(ENERGIES, COATING_UM, GLASS_UM)
        self.assertEqual(coverage_findings(coverage), [])

    def test_matrix_without_a_coating_line_is_a_finding(self):
        coverage = zone_coverage([1.0, 3.0], COATING_UM, GLASS_UM)
        findings = coverage_findings(coverage)
        self.assertEqual(len(findings), 1)
        self.assertIn("coating", findings[0])

    def test_matrix_without_a_substrate_line_is_a_finding(self):
        coverage = zone_coverage([0.05, 0.10], COATING_UM, GLASS_UM)
        findings = coverage_findings(coverage)
        self.assertEqual(len(findings), 1)
        self.assertIn("substrate", findings[0])

    def test_line_past_the_glass_is_a_finding(self):
        coverage = zone_coverage([0.10, 1.0, 10.0], COATING_UM, GLASS_UM)
        findings = coverage_findings(coverage)
        self.assertEqual(len(findings), 1)
        self.assertIn("crosses the whole coverglass", findings[0])

    def test_matrix_missing_both_layers_gives_two_findings(self):
        coverage = zone_coverage([10.0, 20.0], COATING_UM, GLASS_UM)
        self.assertEqual(len(coverage_findings(coverage)), 4)

    def test_coverage_with_an_unknown_zone_rejected(self):
        coverage = zone_coverage(ENERGIES, COATING_UM, GLASS_UM)
        coverage["cell"] = [1.0]
        with self.assertRaises(ValueError):
            coverage_findings(coverage)

    def test_coverage_missing_a_zone_rejected(self):
        coverage = zone_coverage(ENERGIES, COATING_UM, GLASS_UM)
        del coverage["beyond"]
        with self.assertRaises(ValueError):
            coverage_findings(coverage)

    def test_non_mapping_coverage_rejected(self):
        with self.assertRaises(ValueError):
            coverage_findings(["coating"])


class FluxTests(unittest.TestCase):
    def test_flux_is_fluence_over_time(self):
        self.assertAlmostEqual(beam_flux(1.0e12, 1.0e4), 1.0e8, places=3)

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            beam_flux(1.0e12, 0.0)

    def test_slow_line_gives_no_finding(self):
        self.assertEqual(flux_findings("line-1", 1.0e12, 1.0e4), [])

    def test_flux_exactly_on_the_cap_is_accepted(self):
        self.assertEqual(flux_findings("line-1", MAX_FLUX_P_PER_CM2_S, 1.0), [])

    def test_fast_line_is_a_finding(self):
        findings = flux_findings("line-1", 1.0e12, 1.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("heat and charge", findings[0])

    def test_empty_label_rejected(self):
        with self.assertRaises(ValueError):
            flux_findings("  ", 1.0e12, 1.0e4)

    def test_default_flux_cap(self):
        self.assertAlmostEqual(MAX_FLUX_P_PER_CM2_S, 1.0e9, places=3)


class DensityTests(unittest.TestCase):
    def test_unchanged_reading_gives_zero_density(self):
        self.assertAlmostEqual(optical_density(0.95, 0.95), 0.0, places=9)

    def test_a_tenth_of_the_light_gives_one_density(self):
        self.assertAlmostEqual(optical_density(0.095, 0.95), 1.0, places=9)

    def test_line_densities_recover_the_fixture(self):
        series = line_densities(REFERENCE, [scan_for(i) for i in range(3)])
        for band in BANDS:
            for measured, expected in zip(series[band], LINE_DENSITY[band]):
                self.assertAlmostEqual(measured, expected, places=9)

    def test_line_densities_cover_every_band(self):
        series = line_densities(REFERENCE, [scan_for(0)])
        self.assertEqual(sorted(series), sorted(BANDS))

    def test_zero_transmittance_rejected(self):
        with self.assertRaises(ValueError):
            optical_density(0.0, 0.95)

    def test_transmittance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            optical_density(1.2, 0.95)

    def test_scan_missing_a_band_rejected(self):
        with self.assertRaises(ValueError):
            line_densities(REFERENCE, [{"visible": 0.9}])

    def test_scan_with_an_unknown_band_rejected(self):
        scan = dict(scan_for(0))
        scan["x-ray"] = 0.5
        with self.assertRaises(ValueError):
            line_densities(REFERENCE, [scan])

    def test_empty_line_scan_list_rejected(self):
        with self.assertRaises(ValueError):
            line_densities(REFERENCE, [])

    def test_tolerance_is_small(self):
        self.assertAlmostEqual(TOLERANCE, 1e-9, places=12)


class CombinationTests(unittest.TestCase):
    def test_densities_add_across_the_matrix(self):
        self.assertAlmostEqual(
            combined_density(LINE_DENSITY["visible"]), 0.012, places=9
        )

    def test_a_single_line_combines_to_itself(self):
        self.assertAlmostEqual(combined_density([0.004]), 0.004, places=9)

    def test_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            combined_density([])

    def test_non_numeric_density_rejected(self):
        with self.assertRaises(ValueError):
            combined_density([0.004, "0.005"])

    def test_transmittance_after_is_the_inverse_of_the_density(self):
        left = transmittance_after(REFERENCE["visible"], 0.012)
        self.assertAlmostEqual(
            optical_density(left, REFERENCE["visible"]), 0.012, places=9
        )

    def test_zero_density_leaves_the_reading_alone(self):
        self.assertAlmostEqual(
            transmittance_after(REFERENCE["visible"], 0.0), 0.95, places=9
        )

    def test_transmittance_after_rejects_a_bad_reference(self):
        with self.assertRaises(ValueError):
            transmittance_after(0.0, 0.012)


class BrighteningTests(unittest.TestCase):
    def test_darkening_lines_give_no_finding(self):
        self.assertEqual(
            brightening_findings("visible", ENERGIES, LINE_DENSITY["visible"]),
            [],
        )

    def test_brightened_line_is_a_finding(self):
        findings = brightening_findings(
            "visible", ENERGIES, [0.003, -0.05, 0.004]
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("does not do", findings[0])

    def test_dip_inside_the_noise_allowance_is_accepted(self):
        densities = [0.003, -DENSITY_NOISE_ALLOWANCE / 2.0, 0.004]
        self.assertEqual(
            brightening_findings("visible", ENERGIES, densities), []
        )

    def test_unknown_band_rejected(self):
        with self.assertRaises(ValueError):
            brightening_findings("x-ray", ENERGIES, LINE_DENSITY["visible"])

    def test_density_count_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            brightening_findings("visible", ENERGIES, [0.003, 0.005])

    def test_default_noise_allowance(self):
        self.assertAlmostEqual(DENSITY_NOISE_ALLOWANCE, 0.0005, places=9)


class AssessmentTests(unittest.TestCase):
    def test_conformant_matrix_has_no_finding(self):
        result = assess_coverglass_proton_irradiation(spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["run_conformant"])

    def test_every_band_is_reported(self):
        result = assess_coverglass_proton_irradiation(spec())
        self.assertEqual(sorted(result["bands"]), sorted(BANDS))
        self.assertEqual(result["line_count"], 3)

    def test_stopping_depths_are_reported(self):
        result = assess_coverglass_proton_irradiation(spec())
        self.assertAlmostEqual(
            result["stopping_depths_um"][1], proton_range_um(1.0), places=9
        )

    def test_zone_coverage_is_reported(self):
        result = assess_coverglass_proton_irradiation(spec())
        self.assertEqual(result["zone_coverage"]["coating"], [0.10])
        self.assertEqual(result["zone_coverage"]["beyond"], [])

    def test_combined_density_and_transmittance_are_reported(self):
        result = assess_coverglass_proton_irradiation(spec())
        band = result["bands"]["visible"]
        self.assertAlmostEqual(band["combined_density"], 0.012, places=9)
        self.assertAlmostEqual(
            band["transmittance_after"],
            transmittance_after(REFERENCE["visible"], 0.012),
            places=9,
        )

    def test_transmittance_shortfall_fails_the_matrix(self):
        result = assess_coverglass_proton_irradiation(
            spec(required_transmittance={"visible": 0.94})
        )
        self.assertFalse(result["run_conformant"])
        self.assertTrue(
            any("budget asks for" in item for item in result["findings"])
        )

    def test_matrix_that_misses_the_coating_fails(self):
        state = copy.deepcopy(spec())
        state["lines"][0]["energy_mev"] = 0.5
        result = assess_coverglass_proton_irradiation(state)
        self.assertFalse(result["run_conformant"])
        self.assertTrue(
            any("never aged" in item for item in result["findings"])
        )

    def test_line_crossing_the_glass_fails_the_matrix(self):
        state = copy.deepcopy(spec())
        state["lines"][2]["energy_mev"] = 12.0
        result = assess_coverglass_proton_irradiation(state)
        self.assertFalse(result["run_conformant"])

    def test_fast_line_fails_the_matrix(self):
        state = copy.deepcopy(spec())
        state["lines"][1]["duration_s"] = 1.0
        result = assess_coverglass_proton_irradiation(state)
        self.assertFalse(result["run_conformant"])

    def test_brightened_specimen_fails_the_matrix(self):
        state = copy.deepcopy(spec())
        state["lines"][1]["scan"]["visible"] = 1.0
        result = assess_coverglass_proton_irradiation(state)
        self.assertFalse(result["run_conformant"])

    def test_thicker_coating_moves_the_lines_and_fails(self):
        result = assess_coverglass_proton_irradiation(
            spec(coating_thickness_um=100.0)
        )
        self.assertFalse(result["run_conformant"])

    def test_single_line_matrix_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_proton_irradiation(spec(lines=[line_at(0)]))

    def test_missing_spec_key_rejected(self):
        state = spec()
        del state["glass_thickness_um"]
        with self.assertRaises(ValueError):
            assess_coverglass_proton_irradiation(state)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_proton_irradiation(["lines"])

    def test_empty_transmittance_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_proton_irradiation(
                spec(required_transmittance={})
            )

    def test_unknown_required_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_proton_irradiation(
                spec(required_transmittance={"x-ray": 0.9})
            )

    def test_line_without_a_scan_rejected(self):
        state = copy.deepcopy(spec())
        del state["lines"][0]["scan"]
        with self.assertRaises(ValueError):
            assess_coverglass_proton_irradiation(state)


if __name__ == "__main__":
    unittest.main()
