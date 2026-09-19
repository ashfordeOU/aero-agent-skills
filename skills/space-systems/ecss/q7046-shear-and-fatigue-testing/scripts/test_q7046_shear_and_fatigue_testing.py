#!/usr/bin/env python3
"""Contract test for fastener shear and fatigue testing (offline)."""

import copy
import math
import unittest

from q7046_shear_and_fatigue_testing_logic import (
    CYCLIC_THRESHOLD,
    FATIGUE_FAILED,
    FATIGUE_PASSED,
    FATIGUE_RUNOUT,
    LOAD_MODE_COMBINED,
    LOAD_MODE_SHEAR,
    LOAD_MODE_TENSION,
    MINOR_DIAMETER_PITCH_FACTOR,
    MIN_FATIGUE_SPECIMENS,
    PLANE_SHANK,
    PLANE_THREAD,
    PROPERTY_CLASSES,
    RESULT_FAIL,
    RESULT_PASS,
    TEST_FATIGUE,
    TEST_SHEAR,
    VERDICT_ACCEPT,
    VERDICT_NOT_REQUIRED,
    VERDICT_REJECT,
    VERDICT_SET_TOO_SMALL,
    assess_fatigue_set,
    assess_shear_and_fatigue,
    evaluate_fatigue_result,
    evaluate_shear_test,
    shear_allowable_n,
    shear_plane_area_mm2,
    shear_strength_mpa,
    testing_required,
)

M8_ALLOWABLE = shear_allowable_n(8.0, 1.25, PLANE_SHANK, "10.9", 1)

GOOD_CASE = {
    "application": {
        "load_mode": LOAD_MODE_SHEAR,
        "criticality": "structural",
        "cyclic_loading": False,
        "expected_cycles": 0,
    },
    "nominal_diameter_mm": 8.0,
    "pitch_mm": 1.25,
    "shear_plane": PLANE_SHANK,
    "property_class": "10.9",
    "shear_planes": 1,
    "measured_shear_loads_n": [M8_ALLOWABLE * 1.05, M8_ALLOWABLE * 1.10],
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class RequirementTests(unittest.TestCase):
    def test_shear_loaded_joint_owes_shear(self):
        owed = testing_required(
            {"load_mode": LOAD_MODE_SHEAR, "criticality": "structural"}
        )["tests_owed"]
        self.assertIn(TEST_SHEAR, owed)

    def test_combined_loading_owes_shear(self):
        owed = testing_required(
            {"load_mode": LOAD_MODE_COMBINED, "criticality": "structural"}
        )["tests_owed"]
        self.assertIn(TEST_SHEAR, owed)

    def test_static_tension_joint_on_minor_hardware_owes_nothing(self):
        owed = testing_required(
            {"load_mode": LOAD_MODE_TENSION, "criticality": "non-structural"}
        )["tests_owed"]
        self.assertEqual(owed, [])

    def test_fracture_critical_owes_shear_even_in_tension(self):
        owed = testing_required(
            {"load_mode": LOAD_MODE_TENSION, "criticality": "fracture-critical"}
        )["tests_owed"]
        self.assertIn(TEST_SHEAR, owed)

    def test_cyclic_structural_duty_above_the_threshold_owes_fatigue(self):
        owed = testing_required(
            {
                "load_mode": LOAD_MODE_TENSION,
                "criticality": "structural",
                "cyclic_loading": True,
                "expected_cycles": CYCLIC_THRESHOLD,
            }
        )["tests_owed"]
        self.assertIn(TEST_FATIGUE, owed)

    def test_a_handful_of_cycles_is_not_cyclic_duty(self):
        owed = testing_required(
            {
                "load_mode": LOAD_MODE_TENSION,
                "criticality": "structural",
                "cyclic_loading": True,
                "expected_cycles": 10,
            }
        )["tests_owed"]
        self.assertNotIn(TEST_FATIGUE, owed)

    def test_fracture_critical_cyclic_duty_owes_fatigue_at_any_amplitude(self):
        owed = testing_required(
            {
                "load_mode": LOAD_MODE_TENSION,
                "criticality": "fracture-critical",
                "cyclic_loading": True,
                "expected_cycles": 5,
            }
        )["tests_owed"]
        self.assertIn(TEST_FATIGUE, owed)

    def test_each_owed_test_carries_its_reason(self):
        requirement = testing_required(
            {"load_mode": LOAD_MODE_SHEAR, "criticality": "structural"}
        )
        for test in requirement["tests_owed"]:
            self.assertTrue(requirement["reasons"][test])

    def test_unknown_load_mode_rejected(self):
        with self.assertRaises(ValueError):
            testing_required({"load_mode": "wiggly", "criticality": "structural"})

    def test_negative_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            testing_required(
                {
                    "load_mode": LOAD_MODE_TENSION,
                    "criticality": "structural",
                    "expected_cycles": -5,
                }
            )


class ShearAreaTests(unittest.TestCase):
    def test_shank_plane_uses_the_full_nominal_section(self):
        expected = math.pi / 4.0 * 8.0 ** 2
        self.assertAlmostEqual(
            shear_plane_area_mm2(8.0, 1.25, PLANE_SHANK), expected, places=9
        )

    def test_thread_plane_uses_the_minor_diameter_section(self):
        minor = 8.0 - MINOR_DIAMETER_PITCH_FACTOR * 1.25
        expected = math.pi / 4.0 * minor ** 2
        self.assertAlmostEqual(
            shear_plane_area_mm2(8.0, 1.25, PLANE_THREAD), expected, places=9
        )

    def test_thread_plane_is_smaller_than_the_shank_plane(self):
        self.assertLess(
            shear_plane_area_mm2(8.0, 1.25, PLANE_THREAD),
            shear_plane_area_mm2(8.0, 1.25, PLANE_SHANK),
        )

    def test_pitch_that_leaves_no_minor_diameter_rejected(self):
        with self.assertRaises(ValueError):
            shear_plane_area_mm2(2.0, 4.0, PLANE_THREAD)

    def test_unknown_plane_rejected(self):
        with self.assertRaises(ValueError):
            shear_plane_area_mm2(8.0, 1.25, "somewhere-near-the-head")

    def test_zero_diameter_rejected(self):
        with self.assertRaises(ValueError):
            shear_plane_area_mm2(0.0, 1.25, PLANE_SHANK)


class AllowableTests(unittest.TestCase):
    def test_shear_strength_is_a_fraction_of_the_ultimate(self):
        for name in PROPERTY_CLASSES:
            self.assertGreater(shear_strength_mpa(name), 0.0)

    def test_stainless_family_has_a_lower_shear_fraction(self):
        self.assertLess(
            shear_strength_mpa("A4-80") / 800.0,
            shear_strength_mpa("8.8") / 800.0,
        )

    def test_double_shear_doubles_the_allowable_load(self):
        single = shear_allowable_n(8.0, 1.25, PLANE_SHANK, "10.9", 1)
        double = shear_allowable_n(8.0, 1.25, PLANE_SHANK, "10.9", 2)
        self.assertAlmostEqual(double, 2.0 * single, places=9)

    def test_thread_plane_allowable_is_lower_than_the_shank_one(self):
        self.assertLess(
            shear_allowable_n(8.0, 1.25, PLANE_THREAD, "10.9"),
            shear_allowable_n(8.0, 1.25, PLANE_SHANK, "10.9"),
        )

    def test_three_shear_planes_rejected(self):
        with self.assertRaises(ValueError):
            shear_allowable_n(8.0, 1.25, PLANE_SHANK, "10.9", 3)

    def test_unlisted_property_class_rejected(self):
        with self.assertRaises(ValueError):
            shear_strength_mpa("14.9")


class ShearResultTests(unittest.TestCase):
    def test_load_above_the_allowable_passes(self):
        outcome = evaluate_shear_test(M8_ALLOWABLE * 1.1, M8_ALLOWABLE)
        self.assertEqual(outcome["result"], RESULT_PASS)

    def test_load_landing_exactly_on_the_allowable_passes(self):
        outcome = evaluate_shear_test(M8_ALLOWABLE, M8_ALLOWABLE)
        self.assertEqual(outcome["result"], RESULT_PASS)
        self.assertAlmostEqual(
            outcome["measured_load_n"], outcome["allowable_load_n"], places=9
        )

    def test_load_below_the_allowable_fails_with_a_finding(self):
        outcome = evaluate_shear_test(M8_ALLOWABLE * 0.8, M8_ALLOWABLE)
        self.assertEqual(outcome["result"], RESULT_FAIL)
        self.assertTrue(outcome["findings"])

    def test_zero_measured_load_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_shear_test(0.0, M8_ALLOWABLE)


class FatigueSpecimenTests(unittest.TestCase):
    def test_life_below_the_requirement_is_a_failure(self):
        outcome = evaluate_fatigue_result(50000, 100000, 1000000)
        self.assertEqual(outcome["outcome"], FATIGUE_FAILED)
        self.assertFalse(outcome["passed"])

    def test_life_above_the_requirement_passes_on_cycles(self):
        outcome = evaluate_fatigue_result(400000, 100000, 1000000)
        self.assertEqual(outcome["outcome"], FATIGUE_PASSED)

    def test_life_reaching_the_runout_limit_is_a_runout(self):
        outcome = evaluate_fatigue_result(1000000, 100000, 1000000)
        self.assertEqual(outcome["outcome"], FATIGUE_RUNOUT)
        self.assertTrue(outcome["passed"])

    def test_life_landing_exactly_on_the_requirement_passes(self):
        outcome = evaluate_fatigue_result(100000, 100000, 1000000)
        self.assertEqual(outcome["outcome"], FATIGUE_PASSED)

    def test_runout_below_the_required_life_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_fatigue_result(500, 100000, 1000)

    def test_non_integer_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_fatigue_result(1.5e5, 100000, 1000000)


class FatigueSetTests(unittest.TestCase):
    def test_a_full_healthy_set_has_no_findings(self):
        report = assess_fatigue_set([400000] * MIN_FATIGUE_SPECIMENS, 100000, 1000000)
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["set_large_enough"])

    def test_a_short_set_is_flagged_however_good_the_numbers(self):
        report = assess_fatigue_set([1000000, 1000000], 100000, 1000000)
        self.assertFalse(report["set_large_enough"])
        self.assertTrue(any("scatter" in f for f in report["findings"]))

    def test_runouts_are_counted_separately_from_passes(self):
        report = assess_fatigue_set(
            [1000000, 1000000, 400000, 500000, 600000], 100000, 1000000
        )
        self.assertEqual(report["runouts"], 2)
        self.assertEqual(report["passed_on_cycles"], 3)

    def test_worst_life_ignores_the_runouts(self):
        report = assess_fatigue_set(
            [1000000, 1000000, 300000, 250000, 900000], 100000, 1000000
        )
        self.assertEqual(report["worst_life_cycles"], 250000)

    def test_one_failure_is_reported_by_its_cycle_count(self):
        report = assess_fatigue_set(
            [400000, 500000, 60000, 700000, 800000], 100000, 1000000
        )
        self.assertEqual(report["failures"], 1)
        self.assertTrue(any("60000" in f for f in report["findings"]))

    def test_cycles_given_as_a_string_rejected(self):
        with self.assertRaises(ValueError):
            assess_fatigue_set("400000", 100000, 1000000)


class AssessmentTests(unittest.TestCase):
    def test_clean_shear_only_case_is_accepted(self):
        self.assertEqual(
            assess_shear_and_fatigue(_case())["verdict"], VERDICT_ACCEPT
        )

    def test_a_weak_shear_specimen_rejects(self):
        case = _case(measured_shear_loads_n=[M8_ALLOWABLE * 0.7])
        self.assertEqual(assess_shear_and_fatigue(case)["verdict"], VERDICT_REJECT)

    def test_owed_shear_with_no_specimen_recorded_rejects(self):
        case = _case(measured_shear_loads_n=[])
        self.assertEqual(assess_shear_and_fatigue(case)["verdict"], VERDICT_REJECT)

    def test_an_application_owing_nothing_says_so(self):
        case = _case(
            application={
                "load_mode": LOAD_MODE_TENSION,
                "criticality": "non-structural",
            }
        )
        result = assess_shear_and_fatigue(case)
        self.assertEqual(result["verdict"], VERDICT_NOT_REQUIRED)
        self.assertIsNone(result["shear"])

    def test_short_fatigue_set_blocks_the_verdict(self):
        case = _case(
            application={
                "load_mode": LOAD_MODE_SHEAR,
                "criticality": "structural",
                "cyclic_loading": True,
                "expected_cycles": 500000,
            },
            fatigue_cycles=[1000000, 1000000],
            required_cycles=100000,
            runout_cycles=1000000,
        )
        self.assertEqual(
            assess_shear_and_fatigue(case)["verdict"], VERDICT_SET_TOO_SMALL
        )

    def test_full_shear_and_fatigue_case_is_accepted(self):
        case = _case(
            application={
                "load_mode": LOAD_MODE_SHEAR,
                "criticality": "structural",
                "cyclic_loading": True,
                "expected_cycles": 500000,
            },
            fatigue_cycles=[400000, 500000, 600000, 700000, 1000000],
            required_cycles=100000,
            runout_cycles=1000000,
        )
        result = assess_shear_and_fatigue(case)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["fatigue"]["runouts"], 1)

    def test_double_shear_case_is_judged_against_the_doubled_allowable(self):
        case = _case(
            shear_planes=2,
            measured_shear_loads_n=[M8_ALLOWABLE * 1.5],
        )
        self.assertEqual(assess_shear_and_fatigue(case)["verdict"], VERDICT_REJECT)

    def test_missing_shear_plane_rejected(self):
        case = _case()
        del case["shear_plane"]
        with self.assertRaises(ValueError):
            assess_shear_and_fatigue(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_shear_and_fatigue("shear the bolts twice")


if __name__ == "__main__":
    unittest.main()
