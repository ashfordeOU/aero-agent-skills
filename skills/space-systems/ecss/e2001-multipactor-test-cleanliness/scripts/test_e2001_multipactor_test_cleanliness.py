"""Contract test for the clause 6.1 airborne cleanliness logic (stdlib only)."""

import math
import unittest

import e2001_multipactor_test_cleanliness_logic as L


def _good_programme():
    return {
        "required_class": 8.0,
        "monitored_size_um": 0.5,
        "phase_classes": {
            "assembly": 7.0,
            "testing": 8.0,
            "delivery": 8.0,
            "handling": 8.0,
        },
        "measurements": {
            "assembly": 1000.0,
            "testing": 2000.0,
            "delivery": 5000.0,
            "handling": 5000.0,
        },
        "controls": {
            "assembly": ["garment-discipline", "filtered-air-supply", "particle-monitoring"],
            "testing": ["filtered-air-supply", "particle-monitoring", "chamber-purge"],
            "delivery": ["double-bagging", "purge-gas-fill", "shock-and-seal-record"],
            "handling": ["garment-discipline", "double-bagging", "tool-cleanliness-record"],
        },
        "fall_out": {
            "airborne_per_m3": 100.0,
            "exposure_hours": 4.0,
            "mean_particle_diameter_um": 5.0,
            "allowable_obscuration_percent": 0.1,
        },
    }


class ConcentrationLimitTests(unittest.TestCase):
    def test_class_five_at_half_micrometre_matches_reference_value(self):
        self.assertAlmostEqual(L.iso_concentration_limit(5, 0.5), 3517.6, delta=2.0)

    def test_limit_at_the_reference_size_is_a_power_of_ten(self):
        self.assertAlmostEqual(L.iso_concentration_limit(6, 0.1), 1.0e6, places=3)

    def test_limit_falls_as_particle_size_grows(self):
        small = L.iso_concentration_limit(7, 0.5)
        large = L.iso_concentration_limit(7, 5.0)
        self.assertGreater(small, large)

    def test_limit_scales_by_ten_per_class_step(self):
        ratio = L.iso_concentration_limit(8, 0.5) / L.iso_concentration_limit(7, 0.5)
        self.assertAlmostEqual(ratio, 10.0, places=9)

    def test_class_below_range_is_rejected(self):
        with self.assertRaises(ValueError):
            L.iso_concentration_limit(0.5, 0.5)

    def test_class_above_range_is_rejected(self):
        with self.assertRaises(ValueError):
            L.iso_concentration_limit(9.5, 0.5)

    def test_non_numeric_class_is_rejected(self):
        with self.assertRaises(ValueError):
            L.iso_concentration_limit("clean", 0.5)

    def test_particle_size_below_range_is_rejected(self):
        with self.assertRaises(ValueError):
            L.iso_concentration_limit(7, 0.05)

    def test_particle_size_above_range_is_rejected(self):
        with self.assertRaises(ValueError):
            L.iso_concentration_limit(7, 7.5)

    def test_zero_particle_size_is_rejected(self):
        with self.assertRaises(ValueError):
            L.iso_concentration_limit(7, 0.0)


class MeasurementGradingTests(unittest.TestCase):
    def test_count_well_below_limit_is_compliant(self):
        graded = L.evaluate_airborne_measurement(8, 0.5, 1000.0)
        self.assertTrue(graded["compliant"])
        self.assertLess(graded["utilisation"], 1.0)

    def test_count_exactly_at_limit_is_compliant(self):
        limit = L.iso_concentration_limit(8, 0.5)
        graded = L.evaluate_airborne_measurement(8, 0.5, limit)
        self.assertTrue(graded["compliant"])
        self.assertTrue(graded["at_limit"])

    def test_count_reassembled_from_thirds_is_still_compliant(self):
        limit = L.iso_concentration_limit(8, 0.5)
        third = limit / 3.0
        graded = L.evaluate_airborne_measurement(8, 0.5, third + third + third)
        self.assertTrue(graded["compliant"])

    def test_count_above_limit_is_not_compliant(self):
        limit = L.iso_concentration_limit(8, 0.5)
        graded = L.evaluate_airborne_measurement(8, 0.5, limit * 1.01)
        self.assertFalse(graded["compliant"])
        self.assertAlmostEqual(graded["utilisation"], 1.01, places=9)

    def test_zero_count_is_compliant(self):
        graded = L.evaluate_airborne_measurement(8, 0.5, 0.0)
        self.assertTrue(graded["compliant"])

    def test_negative_count_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_airborne_measurement(8, 0.5, -1.0)

    def test_non_finite_count_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_airborne_measurement(8, 0.5, float("inf"))


class PhaseNormalisationTests(unittest.TestCase):
    def test_alias_maps_onto_canonical_phase(self):
        self.assertEqual(L.normalize_phase("Integration"), "assembly")

    def test_underscores_and_spacing_are_tolerated(self):
        self.assertEqual(L.normalize_phase(" multipactor testing "), "testing")

    def test_storage_maps_onto_handling(self):
        self.assertEqual(L.normalize_phase("storage"), "handling")

    def test_uncategorized_phase_is_rejected(self):
        with self.assertRaises(ValueError):
            L.normalize_phase("launch-campaign")

    def test_empty_phase_is_rejected(self):
        with self.assertRaises(ValueError):
            L.normalize_phase("   ")

    def test_non_string_phase_is_rejected(self):
        with self.assertRaises(ValueError):
            L.normalize_phase(7)


class ProgrammeProfileTests(unittest.TestCase):
    def test_all_phases_at_or_better_than_requirement_is_compliant(self):
        profile = L.programme_class_profile(
            {"assembly": 7, "testing": 8, "delivery": 8, "handling": 8}, 8
        )
        self.assertTrue(profile["compliant"])
        self.assertEqual(profile["coarser_than_required"], [])

    def test_phase_equal_to_the_requirement_is_adequate(self):
        profile = L.programme_class_profile(
            {"assembly": 8, "testing": 8, "delivery": 8, "handling": 8}, 8
        )
        self.assertTrue(profile["compliant"])

    def test_coarser_phase_is_reported(self):
        profile = L.programme_class_profile(
            {"assembly": 7, "testing": 8, "delivery": 9, "handling": 8}, 8
        )
        self.assertIn("delivery", profile["coarser_than_required"])
        self.assertFalse(profile["compliant"])

    def test_undeclared_phase_is_reported(self):
        profile = L.programme_class_profile({"assembly": 7, "testing": 7}, 8)
        self.assertEqual(sorted(profile["undeclared_phases"]), ["delivery", "handling"])
        self.assertFalse(profile["compliant"])

    def test_duplicate_phase_via_alias_is_rejected(self):
        with self.assertRaises(ValueError):
            L.programme_class_profile({"assembly": 7, "integration": 7}, 8)

    def test_empty_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            L.programme_class_profile({}, 8)

    def test_out_of_range_phase_class_is_rejected(self):
        with self.assertRaises(ValueError):
            L.programme_class_profile({"assembly": 12}, 8)

    def test_out_of_range_requirement_is_rejected(self):
        with self.assertRaises(ValueError):
            L.programme_class_profile({"assembly": 7}, 0)


class FallOutTests(unittest.TestCase):
    def test_obscuration_matches_the_hand_computation(self):
        value = L.settled_obscuration_percent(1000.0, 1.0, 5.0)
        expected = 1000.0 * 0.0035 * 3600.0 * math.pi * (2.5e-6 ** 2) * 100.0
        self.assertAlmostEqual(value, expected, places=12)

    def test_obscuration_is_linear_in_dwell(self):
        one = L.settled_obscuration_percent(500.0, 1.0, 5.0)
        four = L.settled_obscuration_percent(500.0, 4.0, 5.0)
        self.assertAlmostEqual(four, 4.0 * one, places=12)

    def test_zero_dwell_deposits_nothing(self):
        self.assertAlmostEqual(L.settled_obscuration_percent(1e6, 0.0, 5.0), 0.0, places=15)

    def test_fall_out_exactly_at_allowance_is_compliant(self):
        obscuration = L.settled_obscuration_percent(2.0e5, 6.0, 10.0)
        graded = L.evaluate_surface_fall_out(2.0e5, 6.0, 10.0, obscuration)
        self.assertTrue(graded["compliant"])
        self.assertTrue(graded["at_limit"])

    def test_fall_out_above_allowance_is_reported(self):
        graded = L.evaluate_surface_fall_out(1.0e8, 24.0, 10.0, 0.01)
        self.assertFalse(graded["compliant"])

    def test_negative_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            L.settled_obscuration_percent(1000.0, -1.0, 5.0)

    def test_zero_particle_diameter_is_rejected(self):
        with self.assertRaises(ValueError):
            L.settled_obscuration_percent(1000.0, 1.0, 0.0)

    def test_zero_settling_velocity_is_rejected(self):
        with self.assertRaises(ValueError):
            L.settled_obscuration_percent(1000.0, 1.0, 5.0, settling_velocity_m_s=0.0)

    def test_zero_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_surface_fall_out(1000.0, 1.0, 5.0, 0.0)


class ControlTests(unittest.TestCase):
    def test_complete_control_set_leaves_no_gap(self):
        self.assertEqual(
            L.missing_controls(
                "delivery", ["double-bagging", "purge-gas-fill", "shock-and-seal-record"]
            ),
            [],
        )

    def test_missing_control_is_reported(self):
        gaps = L.missing_controls("testing", ["filtered-air-supply"])
        self.assertEqual(gaps, ["chamber-purge", "particle-monitoring"])

    def test_control_names_are_normalised_before_comparison(self):
        gaps = L.missing_controls("handling", ["Garment Discipline", "double_bagging",
                                               "tool-cleanliness-record"])
        self.assertEqual(gaps, [])

    def test_string_instead_of_list_is_rejected(self):
        with self.assertRaises(ValueError):
            L.missing_controls("handling", "double-bagging")

    def test_none_control_list_is_rejected(self):
        with self.assertRaises(ValueError):
            L.missing_controls("handling", None)

    def test_blank_control_name_is_rejected(self):
        with self.assertRaises(ValueError):
            L.missing_controls("handling", ["double-bagging", "  "])


class ProgrammeAssessmentTests(unittest.TestCase):
    def test_clean_programme_reports_no_findings(self):
        result = L.assess_cleanliness_programme(_good_programme())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["compliant"])

    def test_coarse_delivery_regime_is_a_finding(self):
        programme = _good_programme()
        programme["phase_classes"]["delivery"] = 9.0
        result = L.assess_cleanliness_programme(programme)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("delivery" in f for f in result["findings"]))

    def test_excess_count_is_a_finding(self):
        programme = _good_programme()
        programme["measurements"]["testing"] = 1.0e9
        result = L.assess_cleanliness_programme(programme)
        self.assertTrue(any("exceeds its class limit" in f for f in result["findings"]))

    def test_missing_control_is_a_finding(self):
        programme = _good_programme()
        programme["controls"]["assembly"] = ["garment-discipline"]
        result = L.assess_cleanliness_programme(programme)
        self.assertTrue(any("containment control" in f for f in result["findings"]))

    def test_absent_fall_out_estimate_is_a_finding(self):
        programme = _good_programme()
        programme.pop("fall_out")
        result = L.assess_cleanliness_programme(programme)
        self.assertIn("no critical-gap fall-out estimate on record", result["findings"])

    def test_phase_without_controls_is_a_finding(self):
        programme = _good_programme()
        programme["controls"].pop("handling")
        result = L.assess_cleanliness_programme(programme)
        self.assertTrue(any("declares no containment controls" in f for f in result["findings"]))

    def test_missing_required_key_is_rejected(self):
        programme = _good_programme()
        programme.pop("monitored_size_um")
        with self.assertRaises(ValueError):
            L.assess_cleanliness_programme(programme)

    def test_non_mapping_programme_is_rejected(self):
        with self.assertRaises(ValueError):
            L.assess_cleanliness_programme(["required_class", 8])

    def test_measurements_must_be_a_mapping(self):
        programme = _good_programme()
        programme["measurements"] = [1000.0]
        with self.assertRaises(ValueError):
            L.assess_cleanliness_programme(programme)

    def test_findings_are_sorted_and_stable(self):
        programme = _good_programme()
        programme["controls"]["assembly"] = []
        first = L.assess_cleanliness_programme(programme)["findings"]
        second = L.assess_cleanliness_programme(programme)["findings"]
        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first))


if __name__ == "__main__":
    unittest.main()
