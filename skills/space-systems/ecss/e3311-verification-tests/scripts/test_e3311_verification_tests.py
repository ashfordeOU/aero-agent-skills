"""Contract tests for the clause 4.14.3 explosive verification-test logic."""

import unittest

from e3311_verification_tests_logic import (
    LEVEL_TOLERANCE,
    REQUIRED_CATEGORIES,
    assess_verification_programme,
    at_least,
    at_most,
    category_coverage,
    environmental_verdict,
    esd_verdict,
    firing_demonstration_verdict,
    no_fire_verdict,
    normalize_category,
    qualification_level,
    unit_disposition,
    validate_positive,
)


def good_spec(**overrides):
    spec = {
        "no_fire": {
            "no_fire_current_a": 1.0,
            "applied_current_a": 1.0,
            "required_dwell_s": 300.0,
            "applied_dwell_s": 300.0,
            "functioned": False,
        },
        "firing": {
            "all_fire_current_a": 5.0,
            "applied_current_a": 5.0,
            "functioned": True,
            "measured_output": 12.0,
            "required_output": 10.0,
        },
        "esd": {
            "threshold_v": 25000.0,
            "applied_v": 25000.0,
            "paths": ("pin-to-pin", "pin-to-case"),
            "functioned": False,
            "degraded": False,
        },
        "environmental": {
            "mission_level": 20.0,
            "test_level": 30.0,
            "qualification_factor": 1.5,
            "functioned_after": True,
        },
        "units": [
            {
                "unit_id": "SN-014",
                "exposed_categories": ("no-fire",),
                "returned_to_flight": False,
            }
        ],
    }
    spec.update(overrides)
    return spec


class CategoryTests(unittest.TestCase):
    def test_aliases_fold_to_canonical_names(self):
        self.assertEqual(normalize_category("Electrostatic Discharge"), "esd")
        self.assertEqual(normalize_category("firing-demonstration"), "functional")
        self.assertEqual(normalize_category("NoFire"), "no-fire")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category("vibration-survey")

    def test_non_string_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category(7)

    def test_coverage_reports_every_missing_category(self):
        result = category_coverage(["functional", "esd"])
        self.assertEqual(result["missing"], ["environmental", "no-fire"])
        self.assertFalse(result["complete"])

    def test_full_coverage_is_complete(self):
        result = category_coverage(list(REQUIRED_CATEGORIES))
        self.assertEqual(result["missing"], [])
        self.assertTrue(result["complete"])

    def test_coverage_needs_a_sequence(self):
        with self.assertRaises(ValueError):
            category_coverage("functional")


class NumericGuardTests(unittest.TestCase):
    def test_validate_positive_returns_float(self):
        self.assertEqual(validate_positive("x", 3), 3.0)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("nan"))

    def test_at_least_absorbs_representation_error(self):
        self.assertTrue(at_least(1.0 - LEVEL_TOLERANCE / 10.0, 1.0))
        self.assertFalse(at_least(0.9, 1.0))

    def test_at_most_absorbs_representation_error(self):
        self.assertTrue(at_most(1.0 + LEVEL_TOLERANCE / 10.0, 1.0))
        self.assertFalse(at_most(1.1, 1.0))


class QualificationLevelTests(unittest.TestCase):
    def test_level_scales_by_the_factor(self):
        self.assertAlmostEqual(qualification_level(20.0, 1.5), 30.0, places=9)

    def test_unit_factor_leaves_the_mission_level(self):
        self.assertAlmostEqual(qualification_level(20.0, 1.0), 20.0, places=9)

    def test_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            qualification_level(20.0, 0.9)

    def test_negative_mission_level_rejected(self):
        with self.assertRaises(ValueError):
            qualification_level(-1.0, 1.5)


class NoFireTests(unittest.TestCase):
    def test_current_exactly_on_the_specified_level_passes(self):
        verdict = no_fire_verdict(1.0, 1.0, 300.0, 300.0, False)
        self.assertTrue(verdict["passed"])
        self.assertAlmostEqual(verdict["applied_current_a"], 1.0, places=9)

    def test_short_dwell_is_a_finding(self):
        verdict = no_fire_verdict(1.0, 1.0, 300.0, 120.0, False)
        self.assertFalse(verdict["passed"])
        self.assertIn("dwell", verdict["findings"][0])

    def test_under_current_is_a_finding(self):
        verdict = no_fire_verdict(1.0, 0.8, 300.0, 300.0, False)
        self.assertFalse(verdict["passed"])

    def test_a_unit_that_functions_fails_the_no_fire_test(self):
        verdict = no_fire_verdict(1.0, 1.0, 300.0, 300.0, True)
        self.assertFalse(verdict["passed"])
        self.assertIn("functioned", verdict["findings"][-1])

    def test_non_boolean_outcome_rejected(self):
        with self.assertRaises(ValueError):
            no_fire_verdict(1.0, 1.0, 300.0, 300.0, "no")


class FiringDemonstrationTests(unittest.TestCase):
    def test_firing_at_the_stated_all_fire_current_passes(self):
        verdict = firing_demonstration_verdict(5.0, 5.0, True, 12.0, 10.0)
        self.assertTrue(verdict["passed"])

    def test_over_driving_the_unit_is_a_finding(self):
        verdict = firing_demonstration_verdict(5.0, 9.0, True, 12.0, 10.0)
        self.assertFalse(verdict["passed"])
        self.assertIn("exceeds", verdict["findings"][0])

    def test_a_unit_that_does_not_function_fails(self):
        verdict = firing_demonstration_verdict(5.0, 5.0, False, 12.0, 10.0)
        self.assertFalse(verdict["passed"])

    def test_low_output_is_a_finding(self):
        verdict = firing_demonstration_verdict(5.0, 5.0, True, 8.0, 10.0)
        self.assertFalse(verdict["passed"])
        self.assertIn("output", verdict["findings"][-1])


class EsdTests(unittest.TestCase):
    def test_both_paths_at_threshold_pass(self):
        verdict = esd_verdict(25000.0, 25000.0, ("pin-to-pin", "pin-to-case"), False, False)
        self.assertTrue(verdict["passed"])

    def test_single_path_is_a_coverage_finding(self):
        verdict = esd_verdict(25000.0, 25000.0, ("pin-to-pin",), False, False)
        self.assertFalse(verdict["passed"])
        self.assertIn("pin-to-case", verdict["findings"][0])

    def test_degradation_after_discharge_fails(self):
        verdict = esd_verdict(25000.0, 25000.0, ("pin-to-pin", "pin-to-case"), False, True)
        self.assertFalse(verdict["passed"])

    def test_unknown_path_rejected(self):
        with self.assertRaises(ValueError):
            esd_verdict(25000.0, 25000.0, ("case-to-ground",), False, False)

    def test_paths_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            esd_verdict(25000.0, 25000.0, 2, False, False)


class EnvironmentalTests(unittest.TestCase):
    def test_level_exactly_on_the_requirement_passes(self):
        verdict = environmental_verdict(20.0, 30.0, 1.5, True)
        self.assertTrue(verdict["passed"])
        self.assertAlmostEqual(verdict["required_level"], 30.0, places=9)

    def test_mission_level_alone_is_not_a_qualification_level(self):
        verdict = environmental_verdict(20.0, 20.0, 1.5, True)
        self.assertFalse(verdict["passed"])

    def test_failure_after_exposure_is_a_finding(self):
        verdict = environmental_verdict(20.0, 30.0, 1.5, False)
        self.assertFalse(verdict["passed"])


class DispositionTests(unittest.TestCase):
    def test_exposed_unit_kept_as_flight_stock_is_a_finding(self):
        result = unit_disposition("SN-002", ("environmental",), True)
        self.assertFalse(result["acceptable"])
        self.assertIn("SN-002", result["findings"][0])

    def test_exposed_unit_withdrawn_is_acceptable(self):
        result = unit_disposition("SN-002", ("environmental",), False)
        self.assertTrue(result["acceptable"])

    def test_unexposed_unit_may_stay_in_flight_stock(self):
        result = unit_disposition("SN-003", (), True)
        self.assertTrue(result["acceptable"])

    def test_blank_unit_id_rejected(self):
        with self.assertRaises(ValueError):
            unit_disposition("   ", ("esd",), False)


class ProgrammeTests(unittest.TestCase):
    def test_clean_programme_is_compliant(self):
        result = assess_verification_programme(good_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["coverage"]["complete"])

    def test_one_bad_test_sinks_the_programme(self):
        spec = good_spec()
        spec["esd"] = dict(spec["esd"], paths=("pin-to-pin",))
        result = assess_verification_programme(spec)
        self.assertFalse(result["compliant"])

    def test_returned_exposed_unit_sinks_the_programme(self):
        spec = good_spec()
        spec["units"] = [
            {
                "unit_id": "SN-014",
                "exposed_categories": ("no-fire",),
                "returned_to_flight": True,
            }
        ]
        result = assess_verification_programme(spec)
        self.assertFalse(result["compliant"])

    def test_missing_block_rejected(self):
        spec = good_spec()
        del spec["environmental"]
        with self.assertRaises(ValueError):
            assess_verification_programme(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_programme(["no_fire"])

    def test_units_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_verification_programme(good_spec(units={"unit_id": "SN-1"}))


if __name__ == "__main__":
    unittest.main()
