"""Contract test for the ECSS-E-ST-20-01C clause 8.6 procedure-content audit."""

import math
import unittest

from e2001_multipactor_test_procedure_logic import (
    DEFAULT_REQUIRED_MARGIN_DB,
    MAX_TEST_PRESSURE_MBAR,
    MIN_PUMP_DOWN_HOURS,
    REQUIRED_SECTIONS,
    achieved_margin_db,
    assess_test_procedure,
    audit_procedure_sections,
    categorize_detection_method,
    check_seeding_arrangement,
    check_vacuum_conditions,
    evaluate_detection_coverage,
    evaluate_power_schedule,
    required_test_power_w,
)


def ladder(start_w, step_db, n_steps):
    """Ascending drive schedule of n_steps rungs above start_w."""
    return [start_w * (10.0 ** (i * step_db / 10.0)) for i in range(n_steps + 1)]


def good_procedure(**overrides):
    proc = {
        "sections": list(REQUIRED_SECTIONS),
        "operating_power_w": 100.0,
        "drive_steps_w": ladder(100.0, 0.5, 6),
        "required_margin_db": 3.0,
        "chamber_pressure_mbar": 1.0e-6,
        "pump_down_hours": 48.0,
        "seeding_source": "beta-radioactive-source",
        "seeding_flux_per_cm2_s": 25.0,
        "detection_methods": ["third-harmonic-monitoring", "electron-probe"],
    }
    proc.update(overrides)
    return proc


class DetectionCategorizationTests(unittest.TestCase):
    def test_harmonic_monitoring_is_global(self):
        self.assertEqual(categorize_detection_method("third-harmonic-monitoring"), "global")

    def test_nulling_is_global(self):
        self.assertEqual(
            categorize_detection_method("forward-reflected-power-nulling"), "global"
        )

    def test_electron_probe_is_local(self):
        self.assertEqual(categorize_detection_method("electron-probe"), "local")

    def test_method_name_is_case_and_space_insensitive(self):
        self.assertEqual(categorize_detection_method("  Electron-Probe "), "local")

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            categorize_detection_method("listen-for-a-bang")

    def test_empty_method_raises(self):
        with self.assertRaises(ValueError):
            categorize_detection_method("   ")

    def test_non_string_method_raises(self):
        with self.assertRaises(ValueError):
            categorize_detection_method(7)


class DetectionCoverageTests(unittest.TestCase):
    def test_one_global_and_one_local_is_adequate(self):
        result = evaluate_detection_coverage(["close-to-carrier-noise", "electron-probe"])
        self.assertTrue(result["adequate"])
        self.assertEqual(result["distinct_methods"], 2)

    def test_two_global_methods_leave_no_local_coverage(self):
        result = evaluate_detection_coverage(
            ["close-to-carrier-noise", "third-harmonic-monitoring"]
        )
        self.assertFalse(result["adequate"])
        self.assertIn("no local detection technique declared", result["findings"])

    def test_two_local_methods_leave_no_global_coverage(self):
        result = evaluate_detection_coverage(["electron-probe", "local-pressure-rise"])
        self.assertFalse(result["adequate"])
        self.assertIn("no global detection technique declared", result["findings"])

    def test_single_method_is_not_independent_coverage(self):
        result = evaluate_detection_coverage(["electron-probe"])
        self.assertFalse(result["adequate"])
        self.assertIn(
            "fewer than two independent detection techniques declared", result["findings"]
        )

    def test_duplicate_method_is_counted_once(self):
        result = evaluate_detection_coverage(["electron-probe", "Electron-Probe"])
        self.assertEqual(result["distinct_methods"], 1)
        self.assertFalse(result["adequate"])

    def test_empty_method_list_raises(self):
        with self.assertRaises(ValueError):
            evaluate_detection_coverage([])

    def test_non_list_method_argument_raises(self):
        with self.assertRaises(ValueError):
            evaluate_detection_coverage("electron-probe")


class PowerMarginTests(unittest.TestCase):
    def test_three_db_margin_doubles_the_power(self):
        self.assertAlmostEqual(required_test_power_w(100.0, 3.0), 199.52623149688787, places=9)

    def test_zero_margin_returns_operating_power(self):
        self.assertAlmostEqual(required_test_power_w(45.0, 0.0), 45.0, places=12)

    def test_six_db_margin_quadruples_the_power(self):
        self.assertAlmostEqual(required_test_power_w(10.0, 6.0), 39.810717055349734, places=9)

    def test_achieved_margin_inverts_required_power(self):
        target = required_test_power_w(80.0, 4.5)
        self.assertAlmostEqual(achieved_margin_db(80.0, target), 4.5, places=9)

    def test_zero_operating_power_raises(self):
        with self.assertRaises(ValueError):
            required_test_power_w(0.0, 3.0)

    def test_negative_operating_power_raises(self):
        with self.assertRaises(ValueError):
            required_test_power_w(-10.0, 3.0)

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            required_test_power_w(100.0, -1.0)

    def test_non_numeric_operating_power_raises(self):
        with self.assertRaises(ValueError):
            required_test_power_w("100", 3.0)

    def test_boolean_margin_raises(self):
        with self.assertRaises(ValueError):
            required_test_power_w(100.0, True)

    def test_achieved_margin_rejects_zero_test_power(self):
        with self.assertRaises(ValueError):
            achieved_margin_db(100.0, 0.0)

    def test_achieved_margin_rejects_zero_operating_power(self):
        with self.assertRaises(ValueError):
            achieved_margin_db(0.0, 200.0)


class DriveScheduleTests(unittest.TestCase):
    def test_half_db_ladder_to_three_db_is_compliant(self):
        result = evaluate_power_schedule(100.0, ladder(100.0, 0.5, 6), 3.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["achieved_margin_db"], 3.0, places=9)

    def test_schedule_one_ulp_below_target_is_absorbed(self):
        target = required_test_power_w(100.0, 3.0)
        just_under = math.nextafter(target, 0.0)
        levels = ladder(100.0, 0.5, 5) + [just_under]
        result = evaluate_power_schedule(100.0, levels, 3.0)
        self.assertTrue(result["compliant"])

    def test_schedule_genuinely_short_of_target_fails(self):
        levels = ladder(100.0, 0.5, 4)
        result = evaluate_power_schedule(100.0, levels, 3.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("tops out" in f for f in result["findings"]))

    def test_coarse_step_is_flagged(self):
        result = evaluate_power_schedule(100.0, [100.0, 200.0], 3.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("coarser" in f for f in result["findings"]))

    def test_schedule_starting_above_operating_power_is_flagged(self):
        levels = ladder(150.0, 0.5, 6)
        result = evaluate_power_schedule(100.0, levels, 3.0)
        self.assertTrue(any("starts above" in f for f in result["findings"]))

    def test_target_power_matches_the_margin_formula(self):
        result = evaluate_power_schedule(64.0, ladder(64.0, 0.5, 12), 6.0)
        self.assertAlmostEqual(result["target_power_w"], 64.0 * 10.0 ** 0.6, places=9)

    def test_single_level_schedule_raises(self):
        with self.assertRaises(ValueError):
            evaluate_power_schedule(100.0, [100.0], 3.0)

    def test_non_ascending_schedule_raises(self):
        with self.assertRaises(ValueError):
            evaluate_power_schedule(100.0, [100.0, 120.0, 110.0, 200.0], 3.0)

    def test_flat_repeat_in_schedule_raises(self):
        with self.assertRaises(ValueError):
            evaluate_power_schedule(100.0, [100.0, 100.0, 200.0], 3.0)

    def test_negative_drive_level_raises(self):
        with self.assertRaises(ValueError):
            evaluate_power_schedule(100.0, [-5.0, 100.0, 200.0], 3.0)

    def test_non_numeric_drive_level_raises(self):
        with self.assertRaises(ValueError):
            evaluate_power_schedule(100.0, [100.0, "200"], 3.0)


class VacuumConditionTests(unittest.TestCase):
    def test_low_pressure_long_pump_down_is_acceptable(self):
        result = check_vacuum_conditions(1.0e-7, 72.0)
        self.assertTrue(result["acceptable"])

    def test_pressure_exactly_at_the_ceiling_is_acceptable(self):
        result = check_vacuum_conditions(MAX_TEST_PRESSURE_MBAR, MIN_PUMP_DOWN_HOURS)
        self.assertTrue(result["acceptable"])

    def test_pressure_above_the_ceiling_is_flagged(self):
        result = check_vacuum_conditions(5.0e-5, 48.0)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("gas discharge" in f for f in result["findings"]))

    def test_short_pump_down_is_flagged(self):
        result = check_vacuum_conditions(1.0e-7, 4.0)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("stabilisation" in f for f in result["findings"]))

    def test_zero_pressure_raises(self):
        with self.assertRaises(ValueError):
            check_vacuum_conditions(0.0, 48.0)

    def test_negative_pump_down_raises(self):
        with self.assertRaises(ValueError):
            check_vacuum_conditions(1.0e-7, -1.0)

    def test_non_numeric_pressure_raises(self):
        with self.assertRaises(ValueError):
            check_vacuum_conditions("1e-7", 48.0)


class SeedingArrangementTests(unittest.TestCase):
    def test_beta_source_with_ample_flux_is_adequate(self):
        result = check_seeding_arrangement("beta-radioactive-source", 50.0)
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["flux_per_cm2_s"], 50.0, places=12)

    def test_flux_exactly_at_the_floor_is_adequate(self):
        result = check_seeding_arrangement("ultraviolet-lamp", 1.0)
        self.assertTrue(result["adequate"])

    def test_flux_below_the_floor_is_flagged(self):
        result = check_seeding_arrangement("electron-gun", 0.2)
        self.assertFalse(result["adequate"])

    def test_unrecognized_source_raises(self):
        with self.assertRaises(ValueError):
            check_seeding_arrangement("cosmic-luck", 10.0)

    def test_empty_source_raises(self):
        with self.assertRaises(ValueError):
            check_seeding_arrangement("", 10.0)

    def test_negative_flux_raises(self):
        with self.assertRaises(ValueError):
            check_seeding_arrangement("electron-gun", -3.0)


class SectionAuditTests(unittest.TestCase):
    def test_full_section_list_is_complete(self):
        result = audit_procedure_sections(list(REQUIRED_SECTIONS))
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])

    def test_missing_pass_fail_criteria_is_reported(self):
        sections = [s for s in REQUIRED_SECTIONS if s != "pass-fail-criteria"]
        result = audit_procedure_sections(sections)
        self.assertFalse(result["complete"])
        self.assertIn("pass-fail-criteria", result["missing"])

    def test_extra_section_is_listed_but_not_a_failure(self):
        result = audit_procedure_sections(list(REQUIRED_SECTIONS) + ["annex-photographs"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["extra"], ["annex-photographs"])

    def test_empty_section_list_reports_every_item_missing(self):
        result = audit_procedure_sections([])
        self.assertEqual(len(result["missing"]), len(REQUIRED_SECTIONS))

    def test_blank_section_name_raises(self):
        with self.assertRaises(ValueError):
            audit_procedure_sections(["test-objectives", "  "])

    def test_non_list_sections_raises(self):
        with self.assertRaises(ValueError):
            audit_procedure_sections("test-objectives")


class ProcedureAssessmentTests(unittest.TestCase):
    def test_complete_procedure_is_approvable(self):
        result = assess_test_procedure(good_procedure())
        self.assertTrue(result["approvable"])
        self.assertEqual(result["findings"], [])

    def test_default_required_margin_is_three_db(self):
        self.assertAlmostEqual(DEFAULT_REQUIRED_MARGIN_DB, 3.0, places=12)

    def test_procedure_short_of_margin_is_not_approvable(self):
        result = assess_test_procedure(good_procedure(drive_steps_w=ladder(100.0, 0.5, 3)))
        self.assertFalse(result["approvable"])

    def test_procedure_with_only_global_detection_is_not_approvable(self):
        result = assess_test_procedure(
            good_procedure(detection_methods=["third-harmonic-monitoring", "close-to-carrier-noise"])
        )
        self.assertFalse(result["approvable"])

    def test_procedure_with_high_chamber_pressure_is_not_approvable(self):
        result = assess_test_procedure(good_procedure(chamber_pressure_mbar=2.0e-4))
        self.assertFalse(result["approvable"])

    def test_procedure_missing_a_section_is_not_approvable(self):
        sections = [s for s in REQUIRED_SECTIONS if s != "non-conformance-route"]
        result = assess_test_procedure(good_procedure(sections=sections))
        self.assertFalse(result["approvable"])
        self.assertTrue(any("missing procedure content" in f for f in result["findings"]))

    def test_several_defects_accumulate_findings(self):
        result = assess_test_procedure(
            good_procedure(
                chamber_pressure_mbar=1.0e-3,
                pump_down_hours=1.0,
                seeding_flux_per_cm2_s=0.0,
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_procedure_missing_a_required_key_raises(self):
        proc = good_procedure()
        del proc["detection_methods"]
        with self.assertRaises(ValueError):
            assess_test_procedure(proc)

    def test_non_mapping_procedure_raises(self):
        with self.assertRaises(ValueError):
            assess_test_procedure(["sections"])


if __name__ == "__main__":
    unittest.main()
