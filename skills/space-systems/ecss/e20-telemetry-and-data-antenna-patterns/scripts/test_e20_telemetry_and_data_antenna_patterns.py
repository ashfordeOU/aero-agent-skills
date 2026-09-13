#!/usr/bin/env python3
"""Contract test for e20-telemetry-and-data-antenna-patterns (stdlib unittest)."""

import math
import unittest

from e20_telemetry_and_data_antenna_patterns_logic import (
    MAX_BLOCKAGE_DB,
    MAX_RIPPLE_DB,
    apply_structure_effects,
    assess_pattern_compliance,
    categorize_structure_interaction,
    check_angular_sampling,
    coverage_fraction,
    derive_perturbation_db,
    frequency_to_wavelength,
    interpolate_gain,
    validate_pattern_cut,
    worst_case_gain_in_cone,
)

S_BAND_GHZ = 2.2
S_BAND_WAVELENGTH = frequency_to_wavelength(S_BAND_GHZ)
PEAK_DBI = 3.0
ROLL_OFF_DB_PER_DEG = 0.05


def free_space_cut(step_deg=5.0):
    """Monotonic low-gain cut: peak on boresight, linear roll-off with angle."""
    samples = []
    count = int(round(180.0 / step_deg))
    for k in range(-count, count + 1):
        theta = k * step_deg
        samples.append((theta, PEAK_DBI - ROLL_OFF_DB_PER_DEG * abs(theta)))
    return samples


def flat_cut(gain_dbi=0.0):
    return [(-180.0, gain_dbi), (0.0, gain_dbi), (180.0, gain_dbi)]


def structure(**overrides):
    item = {
        "id": "solar-array-wing",
        "size_m": 1.4,
        "distance_m": 2.0,
        "surface": "conductive",
        "obscures_boresight_path": False,
        "sector_deg": (60.0, 120.0),
    }
    item.update(overrides)
    return item


class TestWavelength(unittest.TestCase):
    def test_wavelength_matches_closed_form(self):
        self.assertAlmostEqual(
            frequency_to_wavelength(S_BAND_GHZ), 299792458.0 / 2.2e9, places=9
        )

    def test_higher_carrier_gives_a_shorter_wavelength(self):
        self.assertLess(frequency_to_wavelength(26.0), frequency_to_wavelength(2.2))

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            frequency_to_wavelength(0.0)

    def test_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            frequency_to_wavelength(-2.2)


class TestCutValidation(unittest.TestCase):
    def test_valid_cut_normalizes(self):
        cut = validate_pattern_cut(free_space_cut())
        self.assertEqual(len(cut), 73)
        self.assertAlmostEqual(cut[0][0], -180.0)

    def test_too_few_samples_raise(self):
        with self.assertRaises(ValueError):
            validate_pattern_cut([(-10.0, 1.0), (10.0, 1.0)])

    def test_unordered_angles_raise(self):
        with self.assertRaises(ValueError):
            validate_pattern_cut([(-10.0, 1.0), (10.0, 1.0), (0.0, 1.0)])

    def test_repeated_angle_raises(self):
        with self.assertRaises(ValueError):
            validate_pattern_cut([(-10.0, 1.0), (0.0, 1.0), (0.0, 2.0)])

    def test_angle_beyond_the_half_sphere_raises(self):
        with self.assertRaises(ValueError):
            validate_pattern_cut([(-190.0, 1.0), (0.0, 1.0), (10.0, 1.0)])

    def test_malformed_sample_raises(self):
        with self.assertRaises(ValueError):
            validate_pattern_cut([(-10.0, 1.0), (0.0,), (10.0, 1.0)])

    def test_non_numeric_gain_raises(self):
        with self.assertRaises(ValueError):
            validate_pattern_cut([(-10.0, "low"), (0.0, 1.0), (10.0, 1.0)])

    def test_non_sequence_cut_raises(self):
        with self.assertRaises(ValueError):
            validate_pattern_cut({"theta": 0.0})


class TestAngularSampling(unittest.TestCase):
    def test_five_degree_cut_meets_a_five_degree_step(self):
        self.assertEqual(check_angular_sampling(free_space_cut(5.0), 5.0), [])

    def test_coarse_cut_reports_every_oversized_step(self):
        coarse = [(-180.0, -6.0), (-90.0, 0.0), (0.0, 3.0), (90.0, 0.0),
                  (180.0, -6.0)]
        findings = check_angular_sampling(coarse, 5.0)
        self.assertEqual(len(findings), 4)

    def test_finer_cut_passes_a_coarser_requirement(self):
        self.assertEqual(check_angular_sampling(free_space_cut(2.0), 5.0), [])

    def test_zero_step_limit_raises(self):
        with self.assertRaises(ValueError):
            check_angular_sampling(free_space_cut(), 0.0)


class TestInterpolation(unittest.TestCase):
    def test_interpolation_at_a_sample_returns_that_sample(self):
        self.assertAlmostEqual(
            interpolate_gain(free_space_cut(), 30.0),
            PEAK_DBI - ROLL_OFF_DB_PER_DEG * 30.0,
        )

    def test_interpolation_between_samples_is_linear(self):
        value = interpolate_gain(free_space_cut(10.0), 5.0)
        self.assertAlmostEqual(value, PEAK_DBI - ROLL_OFF_DB_PER_DEG * 5.0)

    def test_interpolation_outside_the_cut_raises(self):
        with self.assertRaises(ValueError):
            interpolate_gain(free_space_cut(), 181.0)


class TestWorstCaseGain(unittest.TestCase):
    def test_worst_case_sits_at_the_cone_edge_for_a_monotonic_cut(self):
        self.assertAlmostEqual(
            worst_case_gain_in_cone(free_space_cut(), 30.0),
            PEAK_DBI - ROLL_OFF_DB_PER_DEG * 30.0,
        )

    def test_wider_cone_gives_a_lower_worst_case(self):
        self.assertLess(
            worst_case_gain_in_cone(free_space_cut(), 90.0),
            worst_case_gain_in_cone(free_space_cut(), 30.0),
        )

    def test_cone_wider_than_the_cut_raises(self):
        partial = [(-45.0, 0.0), (0.0, 3.0), (45.0, 0.0)]
        with self.assertRaises(ValueError):
            worst_case_gain_in_cone(partial, 90.0)

    def test_zero_cone_raises(self):
        with self.assertRaises(ValueError):
            worst_case_gain_in_cone(free_space_cut(), 0.0)


class TestStructureCategorization(unittest.TestCase):
    def test_electrically_small_structure_is_negligible(self):
        self.assertEqual(
            categorize_structure_interaction(
                structure(size_m=0.002), S_BAND_WAVELENGTH
            ),
            "negligible",
        )

    def test_large_obscuring_structure_blocks(self):
        self.assertEqual(
            categorize_structure_interaction(
                structure(obscures_boresight_path=True), S_BAND_WAVELENGTH
            ),
            "blockage",
        )

    def test_small_obscuring_structure_only_scatters(self):
        self.assertEqual(
            categorize_structure_interaction(
                structure(size_m=0.05, obscures_boresight_path=True),
                S_BAND_WAVELENGTH,
            ),
            "scattering",
        )

    def test_conductive_structure_off_the_path_scatters(self):
        self.assertEqual(
            categorize_structure_interaction(structure(), S_BAND_WAVELENGTH),
            "scattering",
        )

    def test_modest_dielectric_off_the_path_is_negligible(self):
        self.assertEqual(
            categorize_structure_interaction(
                structure(size_m=0.3, surface="dielectric"), S_BAND_WAVELENGTH
            ),
            "negligible",
        )

    def test_large_dielectric_off_the_path_scatters(self):
        self.assertEqual(
            categorize_structure_interaction(
                structure(size_m=2.0, surface="dielectric"), S_BAND_WAVELENGTH
            ),
            "scattering",
        )

    def test_unknown_surface_raises(self):
        with self.assertRaises(ValueError):
            categorize_structure_interaction(
                structure(surface="ceramic-tile"), S_BAND_WAVELENGTH
            )

    def test_zero_size_raises(self):
        with self.assertRaises(ValueError):
            categorize_structure_interaction(
                structure(size_m=0.0), S_BAND_WAVELENGTH
            )

    def test_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            categorize_structure_interaction(
                structure(distance_m=-1.0), S_BAND_WAVELENGTH
            )

    def test_reversed_sector_raises(self):
        with self.assertRaises(ValueError):
            categorize_structure_interaction(
                structure(sector_deg=(120.0, 60.0)), S_BAND_WAVELENGTH
            )

    def test_missing_identifier_raises(self):
        item = structure()
        del item["id"]
        with self.assertRaises(ValueError):
            categorize_structure_interaction(item, S_BAND_WAVELENGTH)

    def test_zero_wavelength_raises(self):
        with self.assertRaises(ValueError):
            categorize_structure_interaction(structure(), 0.0)


class TestDerivedPerturbation(unittest.TestCase):
    def test_blockage_grows_with_size_in_wavelengths(self):
        self.assertGreater(
            derive_perturbation_db("blockage", 20.0),
            derive_perturbation_db("blockage", 2.0),
        )

    def test_blockage_is_capped(self):
        self.assertAlmostEqual(
            derive_perturbation_db("blockage", 1e6), MAX_BLOCKAGE_DB
        )

    def test_scattering_is_capped_lower_than_blockage(self):
        self.assertAlmostEqual(
            derive_perturbation_db("scattering", 1e6), MAX_RIPPLE_DB
        )

    def test_negligible_interaction_perturbs_nothing(self):
        self.assertAlmostEqual(derive_perturbation_db("negligible", 3.0), 0.0)

    def test_unknown_interaction_raises(self):
        with self.assertRaises(ValueError):
            derive_perturbation_db("diffraction", 3.0)

    def test_zero_size_ratio_raises(self):
        with self.assertRaises(ValueError):
            derive_perturbation_db("blockage", 0.0)


class TestStructureEffects(unittest.TestCase):
    def test_sector_samples_take_the_full_perturbation(self):
        installed = apply_structure_effects(
            flat_cut(), [structure(sector_deg=(-180.0, 180.0),
                                   perturbation_db=2.0)],
            S_BAND_WAVELENGTH,
        )
        for _, gain in installed:
            self.assertAlmostEqual(gain, -2.0)

    def test_samples_well_outside_the_sector_are_untouched(self):
        installed = apply_structure_effects(
            flat_cut(), [structure(sector_deg=(60.0, 120.0),
                                   perturbation_db=2.0)],
            S_BAND_WAVELENGTH,
        )
        self.assertAlmostEqual(installed[0][1], 0.0)
        self.assertAlmostEqual(installed[1][1], 0.0)

    def test_guard_band_takes_half_the_perturbation(self):
        cut = [(-10.0, 0.0), (0.0, 0.0), (12.0, 0.0), (60.0, 0.0)]
        installed = apply_structure_effects(
            cut,
            [structure(sector_deg=(-5.0, 10.0), perturbation_db=4.0)],
            S_BAND_WAVELENGTH,
            guard_deg=5.0,
        )
        self.assertAlmostEqual(installed[0][1], -2.0)
        self.assertAlmostEqual(installed[1][1], -4.0)
        self.assertAlmostEqual(installed[2][1], -2.0)
        self.assertAlmostEqual(installed[3][1], 0.0)

    def test_negligible_structure_leaves_the_cut_alone(self):
        installed = apply_structure_effects(
            flat_cut(), [structure(size_m=0.001,
                                   sector_deg=(-180.0, 180.0))],
            S_BAND_WAVELENGTH,
        )
        for _, gain in installed:
            self.assertAlmostEqual(gain, 0.0)

    def test_derived_perturbation_is_used_when_none_is_given(self):
        installed = apply_structure_effects(
            flat_cut(),
            [structure(obscures_boresight_path=True,
                       sector_deg=(-180.0, 180.0))],
            S_BAND_WAVELENGTH,
        )
        ratio = 1.4 / S_BAND_WAVELENGTH
        self.assertAlmostEqual(
            installed[1][1], -derive_perturbation_db("blockage", ratio)
        )

    def test_several_structures_accumulate(self):
        installed = apply_structure_effects(
            flat_cut(),
            [
                structure(sector_deg=(-180.0, 180.0), perturbation_db=1.0),
                structure(id="thruster-bracket", sector_deg=(-180.0, 180.0),
                          perturbation_db=0.5),
            ],
            S_BAND_WAVELENGTH,
        )
        self.assertAlmostEqual(installed[1][1], -1.5)

    def test_negative_perturbation_raises(self):
        with self.assertRaises(ValueError):
            apply_structure_effects(
                flat_cut(),
                [structure(sector_deg=(-180.0, 180.0), perturbation_db=-1.0)],
                S_BAND_WAVELENGTH,
            )

    def test_non_sequence_structure_list_raises(self):
        with self.assertRaises(ValueError):
            apply_structure_effects(flat_cut(), structure(), S_BAND_WAVELENGTH)


class TestCoverageFraction(unittest.TestCase):
    def test_threshold_below_the_whole_cut_covers_everything(self):
        self.assertAlmostEqual(coverage_fraction(free_space_cut(), -20.0), 1.0)

    def test_threshold_above_the_peak_covers_nothing(self):
        self.assertAlmostEqual(coverage_fraction(free_space_cut(), 10.0), 0.0)

    def test_partial_coverage_matches_the_solid_angle_weighting(self):
        threshold = PEAK_DBI - ROLL_OFF_DB_PER_DEG * 30.0
        expected = (2.0 * (1.0 - math.cos(math.radians(30.0)))) / 4.0
        self.assertAlmostEqual(
            coverage_fraction(free_space_cut(), threshold), expected, places=9
        )

    def test_coverage_falls_as_the_threshold_rises(self):
        low = coverage_fraction(free_space_cut(), PEAK_DBI - 6.0)
        high = coverage_fraction(free_space_cut(), PEAK_DBI - 1.0)
        self.assertLess(high, low)

    def test_threshold_outside_the_gain_range_raises(self):
        with self.assertRaises(ValueError):
            coverage_fraction(free_space_cut(), 500.0)


class TestPatternComplianceRollUp(unittest.TestCase):
    def test_clean_installation_is_compliant(self):
        result = assess_pattern_compliance(
            free_space_cut(),
            {"cone_half_angle_deg": 30.0, "min_gain_dbi": 0.0,
             "min_coverage_fraction": 0.05},
            [structure(size_m=0.002)],
            S_BAND_WAVELENGTH,
        )
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["structure_degradation_db"], 0.0)
        self.assertEqual(result["interactions"]["solar-array-wing"], "negligible")

    def test_blockage_inside_the_cone_is_a_finding(self):
        result = assess_pattern_compliance(
            free_space_cut(),
            {"cone_half_angle_deg": 30.0, "min_gain_dbi": 0.0},
            [structure(obscures_boresight_path=True, sector_deg=(-20.0, 20.0))],
            S_BAND_WAVELENGTH,
        )
        self.assertFalse(result["compliant"])
        self.assertGreater(result["structure_degradation_db"], 0.0)
        self.assertEqual(result["interactions"]["solar-array-wing"], "blockage")

    def test_coarse_sampling_is_reported_alongside_the_gain_check(self):
        coarse = [(-180.0, -6.0), (-90.0, 0.0), (0.0, 3.0), (90.0, 0.0),
                  (180.0, -6.0)]
        result = assess_pattern_compliance(
            coarse,
            {"cone_half_angle_deg": 30.0, "min_gain_dbi": 0.0,
             "max_step_deg": 5.0},
            [],
            S_BAND_WAVELENGTH,
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("angular-sampling" in f for f in result["findings"])
        )

    def test_coverage_shortfall_is_a_finding(self):
        result = assess_pattern_compliance(
            free_space_cut(),
            {"cone_half_angle_deg": 30.0, "min_gain_dbi": 0.0,
             "min_coverage_fraction": 0.95},
            [],
            S_BAND_WAVELENGTH,
        )
        self.assertTrue(
            any("coverage-fraction" in f for f in result["findings"])
        )

    def test_gain_exactly_at_the_requirement_after_two_perturbations_passes(self):
        # 0.1 dB + 0.2 dB of accumulated structure perturbation lands a few
        # ULPs below -0.3 dBi in binary floating point; the physically
        # compliant installation must still read as compliant.
        result = assess_pattern_compliance(
            flat_cut(0.0),
            {"cone_half_angle_deg": 30.0, "min_gain_dbi": -0.3,
             "min_coverage_fraction": 1.0, "max_step_deg": 180.0},
            [
                structure(sector_deg=(-180.0, 180.0), perturbation_db=0.1),
                structure(id="thruster-bracket", sector_deg=(-180.0, 180.0),
                          perturbation_db=0.2),
            ],
            S_BAND_WAVELENGTH,
        )
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["installed_worst_gain_dbi"], -0.3, places=9)

    def test_missing_minimum_gain_raises(self):
        with self.assertRaises(ValueError):
            assess_pattern_compliance(
                free_space_cut(), {"cone_half_angle_deg": 30.0}, [],
                S_BAND_WAVELENGTH,
            )

    def test_non_mapping_requirement_raises(self):
        with self.assertRaises(ValueError):
            assess_pattern_compliance(
                free_space_cut(), [30.0, 0.0], [], S_BAND_WAVELENGTH
            )

    def test_coverage_requirement_above_unity_raises(self):
        with self.assertRaises(ValueError):
            assess_pattern_compliance(
                free_space_cut(),
                {"cone_half_angle_deg": 30.0, "min_gain_dbi": 0.0,
                 "min_coverage_fraction": 1.4},
                [],
                S_BAND_WAVELENGTH,
            )


if __name__ == "__main__":
    unittest.main()
