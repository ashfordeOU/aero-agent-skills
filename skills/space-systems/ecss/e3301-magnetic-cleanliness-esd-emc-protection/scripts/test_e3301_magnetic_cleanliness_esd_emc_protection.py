"""Contract tests for the clause 4.7.7.8 magnetic, ESD and EMC protection logic."""

import math
import unittest

from e3301_magnetic_cleanliness_esd_emc_protection_logic import (
    MAX_BLEED_RESISTANCE_OHM,
    MIN_BLEED_RESISTANCE_OHM,
    VACUUM_PERMEABILITY,
    assess_magnetic_esd_emc,
    axial_dipole_field_t,
    band_conflicts,
    combined_moment_a_m2,
    emc_findings,
    esd_findings,
    grade_magnetic_budget,
    harmonic_frequencies_hz,
    validate_source,
    validate_surface,
)

SOURCES = [
    {"id": "STEPPER", "moment_a_m2": 0.030, "orientation_known": True},
    {"id": "LATCH-MAGNET", "moment_a_m2": 0.040, "orientation_known": True},
]

SURFACES = [
    {"id": "YOKE", "area_m2": 0.05, "bleed_resistance_ohm": 1.0e6},
    {"id": "SUNSHIELD", "area_m2": 0.40, "bleed_resistance_ohm": 5.0e7},
]

BANDS = [
    {"id": "S-BAND-RX", "low_hz": 2.02e9, "high_hz": 2.12e9},
    {"id": "GNSS-L1", "low_hz": 1.56e9, "high_hz": 1.60e9},
]

DRIVES = [
    {"id": "SADM-DRIVE", "switching_hz": 40000.0, "filter_declared": True,
     "screen_terminated": True},
]


class ValidateSourceTests(unittest.TestCase):
    def test_defaults_orientation_to_unknown(self):
        self.assertFalse(validate_source({"id": "M", "moment_a_m2": 0.01})["orientation_known"])

    def test_zero_moment_is_allowed(self):
        self.assertAlmostEqual(
            validate_source({"id": "M", "moment_a_m2": 0.0})["moment_a_m2"], 0.0, places=12
        )

    def test_negative_moment_rejected(self):
        with self.assertRaises(ValueError):
            validate_source({"id": "M", "moment_a_m2": -0.01})

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_source({"id": "M"})

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_source("M")

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_source({"id": "  ", "moment_a_m2": 0.01})


class CombinationTests(unittest.TestCase):
    def test_root_sum_square_of_three_and_four_is_five(self):
        sources = [{"id": "A", "moment_a_m2": 0.03}, {"id": "B", "moment_a_m2": 0.04}]
        self.assertAlmostEqual(combined_moment_a_m2(sources), 0.05, places=12)

    def test_aligned_sum_is_the_arithmetic_total(self):
        sources = [{"id": "A", "moment_a_m2": 0.03}, {"id": "B", "moment_a_m2": 0.04}]
        self.assertAlmostEqual(combined_moment_a_m2(sources, aligned=True), 0.07, places=12)

    def test_single_source_is_identical_either_way(self):
        sources = [{"id": "A", "moment_a_m2": 0.02}]
        self.assertAlmostEqual(combined_moment_a_m2(sources),
                               combined_moment_a_m2(sources, aligned=True), places=12)

    def test_empty_source_set_rejected(self):
        with self.assertRaises(ValueError):
            combined_moment_a_m2([])

    def test_non_boolean_aligned_rejected(self):
        with self.assertRaises(ValueError):
            combined_moment_a_m2([{"id": "A", "moment_a_m2": 0.02}], aligned=1)


class DipoleFieldTests(unittest.TestCase):
    def test_field_matches_the_closed_form(self):
        expected = VACUUM_PERMEABILITY * 0.05 / (2.0 * math.pi * 8.0)
        self.assertAlmostEqual(axial_dipole_field_t(0.05, 2.0), expected, places=18)

    def test_field_falls_as_the_cube_of_distance(self):
        near = axial_dipole_field_t(0.05, 1.0)
        far = axial_dipole_field_t(0.05, 2.0)
        self.assertAlmostEqual(far * 8.0, near, places=15)

    def test_zero_distance_rejected(self):
        with self.assertRaises(ValueError):
            axial_dipole_field_t(0.05, 0.0)

    def test_zero_moment_gives_zero_field(self):
        self.assertAlmostEqual(axial_dipole_field_t(0.0, 2.0), 0.0, places=18)


class MagneticBudgetTests(unittest.TestCase):
    def test_known_orientations_use_the_root_sum_square(self):
        graded = grade_magnetic_budget(SOURCES, 0.10, 2.0, 1.0e-6)
        self.assertAlmostEqual(graded["governing_moment_a_m2"], 0.05, places=12)
        self.assertEqual(graded["orientations_unknown"], [])

    def test_unknown_orientation_forces_the_aligned_sum(self):
        sources = [dict(SOURCES[0]), dict(SOURCES[1], orientation_known=False)]
        graded = grade_magnetic_budget(sources, 0.10, 2.0, 1.0e-6)
        self.assertAlmostEqual(graded["governing_moment_a_m2"], 0.07, places=12)
        self.assertEqual(graded["orientations_unknown"], ["LATCH-MAGNET"])

    def test_moment_over_allocation_is_flagged(self):
        graded = grade_magnetic_budget(SOURCES, 0.01, 2.0, 1.0e-6)
        self.assertFalse(graded["moment_ok"])

    def test_moment_exactly_on_the_allocation_is_accepted(self):
        graded = grade_magnetic_budget(SOURCES, 0.05, 2.0, 1.0e-6)
        self.assertAlmostEqual(graded["governing_moment_a_m2"], 0.05, places=12)
        self.assertTrue(graded["moment_ok"])

    def test_field_over_the_sensor_limit_is_flagged(self):
        graded = grade_magnetic_budget(SOURCES, 0.10, 0.20, 1.0e-9)
        self.assertFalse(graded["field_ok"])
        self.assertTrue(any("stray field" in f for f in graded["findings"]))

    def test_healthy_budget_is_compliant(self):
        graded = grade_magnetic_budget(SOURCES, 0.10, 2.0, 1.0e-6)
        self.assertTrue(graded["compliant"])
        self.assertEqual(graded["findings"], [])

    def test_zero_allocation_rejected(self):
        with self.assertRaises(ValueError):
            grade_magnetic_budget(SOURCES, 0.0, 2.0, 1.0e-6)


class EsdTests(unittest.TestCase):
    def test_window_constants_are_the_documented_ones(self):
        self.assertAlmostEqual(MIN_BLEED_RESISTANCE_OHM, 1.0e5, places=3)
        self.assertAlmostEqual(MAX_BLEED_RESISTANCE_OHM, 1.0e9, places=3)

    def test_surfaces_inside_the_window_are_clean(self):
        result = esd_findings(SURFACES)
        self.assertEqual(result["findings"], [])
        self.assertTrue(all(r["compliant"] for r in result["records"]))

    def test_isolated_surface_is_flagged(self):
        result = esd_findings([{"id": "FLOATER", "area_m2": 0.2}])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("no bleed path", result["findings"][0])

    def test_resistance_below_the_floor_is_flagged(self):
        result = esd_findings([{"id": "HARD", "area_m2": 0.2, "bleed_resistance_ohm": 1.0}])
        self.assertIn("fault-current route", result["findings"][0])

    def test_resistance_above_the_ceiling_is_flagged(self):
        result = esd_findings([{"id": "SOFT", "area_m2": 0.2, "bleed_resistance_ohm": 1.0e12}])
        self.assertIn("floats long enough", result["findings"][0])

    def test_resistance_exactly_on_the_floor_is_accepted(self):
        result = esd_findings(
            [{"id": "EDGE", "area_m2": 0.2, "bleed_resistance_ohm": MIN_BLEED_RESISTANCE_OHM}]
        )
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["records"][0]["compliant"])

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface({"id": "X", "area_m2": 0.0})

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            esd_findings(SURFACES, min_ohm=1.0e9, max_ohm=1.0e5)

    def test_empty_surface_set_rejected(self):
        with self.assertRaises(ValueError):
            esd_findings([])


class HarmonicTests(unittest.TestCase):
    def test_first_harmonic_is_the_fundamental(self):
        self.assertAlmostEqual(harmonic_frequencies_hz(40000.0, 3)[0], 40000.0, places=6)

    def test_harmonics_are_integer_multiples(self):
        values = harmonic_frequencies_hz(40000.0, 3)
        self.assertAlmostEqual(values[2], 120000.0, places=6)

    def test_zero_count_rejected(self):
        with self.assertRaises(ValueError):
            harmonic_frequencies_hz(40000.0, 0)

    def test_fractional_count_rejected(self):
        with self.assertRaises(ValueError):
            harmonic_frequencies_hz(40000.0, 2.5)

    def test_zero_fundamental_rejected(self):
        with self.assertRaises(ValueError):
            harmonic_frequencies_hz(0.0, 3)

    def test_no_conflict_outside_the_bands(self):
        self.assertEqual(band_conflicts([1.0e6], BANDS), [])

    def test_frequency_inside_a_band_conflicts(self):
        conflicts = band_conflicts([1.57e9], BANDS)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["band"], "GNSS-L1")

    def test_band_edge_counts_as_inside(self):
        conflicts = band_conflicts([1.56e9], BANDS)
        self.assertEqual(len(conflicts), 1)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            band_conflicts([1.0e6], [{"id": "BAD", "low_hz": 2.0e9, "high_hz": 1.0e9}])

    def test_malformed_band_rejected(self):
        with self.assertRaises(ValueError):
            band_conflicts([1.0e6], [{"id": "BAD", "low_hz": 2.0e9}])


class EmcTests(unittest.TestCase):
    def test_filtered_screened_drive_clear_of_bands_is_clean(self):
        result = emc_findings(DRIVES, BANDS)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["records"][0]["compliant"])

    def test_missing_filter_is_flagged(self):
        drives = [dict(DRIVES[0], filter_declared=False)]
        result = emc_findings(drives, BANDS)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("filter declared", result["findings"][0])

    def test_unterminated_screen_is_flagged(self):
        drives = [dict(DRIVES[0], screen_terminated=False)]
        result = emc_findings(drives, BANDS)
        self.assertIn("screen", result["findings"][0])

    def test_harmonic_landing_in_a_band_is_flagged(self):
        drives = [dict(DRIVES[0], switching_hz=3.9e8)]
        result = emc_findings(drives, BANDS, harmonic_count=4)
        self.assertEqual(len(result["records"][0]["conflicts"]), 1)
        self.assertEqual(result["records"][0]["conflicts"][0]["band"], "GNSS-L1")
        self.assertEqual(len(result["findings"]), 1)

    def test_every_conflicting_harmonic_raises_its_own_finding(self):
        drives = [dict(DRIVES[0], switching_hz=5.2e8)]
        result = emc_findings(drives, BANDS, harmonic_count=4)
        self.assertEqual(len(result["records"][0]["conflicts"]), 2)
        self.assertEqual(len(result["findings"]), 2)

    def test_harmonic_count_reaches_the_record(self):
        result = emc_findings(DRIVES, BANDS, harmonic_count=7)
        self.assertEqual(len(result["records"][0]["harmonics_hz"]), 7)

    def test_empty_drive_set_rejected(self):
        with self.assertRaises(ValueError):
            emc_findings([], BANDS)

    def test_missing_drive_key_rejected(self):
        with self.assertRaises(ValueError):
            emc_findings([{"id": "X"}], BANDS)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "sources": SOURCES,
            "allocation_a_m2": 0.10,
            "sensor_distance_m": 2.0,
            "sensor_limit_t": 1.0e-6,
            "surfaces": SURFACES,
            "drives": DRIVES,
            "protected_bands": BANDS,
        }
        spec.update(overrides)
        return spec

    def test_healthy_design_reports_no_findings(self):
        result = assess_magnetic_esd_emc(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_records_cover_all_three_domains(self):
        result = assess_magnetic_esd_emc(self._spec())
        self.assertEqual(len(result["esd"]), 2)
        self.assertEqual(len(result["emc"]), 1)
        self.assertIn("governing_moment_a_m2", result["magnetic"])

    def test_tight_allocation_fails_the_design(self):
        result = assess_magnetic_esd_emc(self._spec(allocation_a_m2=0.001))
        self.assertFalse(result["compliant"])

    def test_isolated_surface_fails_the_design(self):
        result = assess_magnetic_esd_emc(self._spec(surfaces=[{"id": "F", "area_m2": 0.1}]))
        self.assertFalse(result["compliant"])

    def test_findings_from_every_domain_aggregate(self):
        result = assess_magnetic_esd_emc(self._spec(
            allocation_a_m2=0.001,
            surfaces=[{"id": "F", "area_m2": 0.1}],
            drives=[dict(DRIVES[0], filter_declared=False)],
        ))
        self.assertEqual(len(result["findings"]), 3)

    def test_empty_source_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_magnetic_esd_emc(self._spec(sources=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["protected_bands"]
        with self.assertRaises(ValueError):
            assess_magnetic_esd_emc(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_magnetic_esd_emc(["sources"])

    def test_bleed_window_override_reaches_the_report(self):
        result = assess_magnetic_esd_emc(self._spec(min_bleed_ohm=1.0e7, max_bleed_ohm=1.0e8))
        self.assertFalse(result["compliant"])
        self.assertFalse(result["esd"][0]["compliant"])


if __name__ == "__main__":
    unittest.main()
