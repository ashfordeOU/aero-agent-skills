#!/usr/bin/env python3
"""Gate 3 contract test for e2001-multipactor-free-declaration.

Offline, deterministic, stdlib unittest. Run:
python3 test_e2001_multipactor_free_declaration.py
"""

import sys
import unittest

import e2001_multipactor_free_declaration_logic as L


def base_record(**over):
    rec = {
        "max_operating_power_w": 100.0,
        "margin_db": 3.0,
        "run_log": [
            {"level_w": 100.0, "multipactor_observed": False},
            {"level_w": 250.0, "multipactor_observed": False},
        ],
        "detection_methods": [
            {
                "name": "forward-reflected-comparison",
                "sensitivity_verified": True,
                "calibration_in_date": True,
            },
            {
                "name": "electron-probe",
                "sensitivity_verified": True,
                "calibration_in_date": True,
            },
        ],
        "seeding": {
            "source": "electron-gun",
            "active": True,
            "effectiveness_verified": True,
        },
        "environment": {
            "pressure_pa": 1.0e-5,
            "run_temp_min_c": -20.0,
            "run_temp_max_c": 70.0,
            "operating_temp_min_c": -10.0,
            "operating_temp_max_c": 60.0,
        },
    }
    rec.update(over)
    return rec


class DecibelTests(unittest.TestCase):
    def test_zero_decibel_margin_is_unity(self):
        self.assertAlmostEqual(L.db_to_ratio(0.0), 1.0, places=12)

    def test_three_decibel_margin_is_about_two(self):
        self.assertAlmostEqual(L.db_to_ratio(3.0), 1.9952623149688795, places=12)

    def test_ten_decibel_margin_is_ten(self):
        self.assertAlmostEqual(L.db_to_ratio(10.0), 10.0, places=9)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            L.db_to_ratio(-1.0)

    def test_non_finite_margin_raises(self):
        with self.assertRaises(ValueError):
            L.db_to_ratio(float("nan"))

    def test_boolean_margin_raises(self):
        with self.assertRaises(ValueError):
            L.db_to_ratio(True)

    def test_ratio_to_db_of_ten_is_ten(self):
        self.assertAlmostEqual(L.ratio_to_db(10.0), 10.0, places=9)

    def test_decibel_roundtrip(self):
        self.assertAlmostEqual(L.ratio_to_db(L.db_to_ratio(6.5)), 6.5, places=9)

    def test_zero_ratio_raises(self):
        with self.assertRaises(ValueError):
            L.ratio_to_db(0.0)

    def test_negative_ratio_raises(self):
        with self.assertRaises(ValueError):
            L.ratio_to_db(-2.0)


class RequiredLevelTests(unittest.TestCase):
    def test_required_level_applies_the_margin(self):
        self.assertAlmostEqual(
            L.required_drive_level_w(100.0, 3.0), 199.52623149688795, places=9
        )

    def test_zero_margin_leaves_the_operating_level(self):
        self.assertAlmostEqual(L.required_drive_level_w(80.0, 0.0), 80.0, places=12)

    def test_zero_operating_power_raises(self):
        with self.assertRaises(ValueError):
            L.required_drive_level_w(0.0, 3.0)

    def test_negative_margin_in_required_level_raises(self):
        with self.assertRaises(ValueError):
            L.required_drive_level_w(100.0, -3.0)

    def test_qualified_level_releases_the_margin(self):
        declared = 250.0
        qualified = L.qualified_operating_level_w(declared, 3.0)
        self.assertAlmostEqual(qualified * L.db_to_ratio(3.0), declared, places=9)

    def test_zero_declared_level_raises(self):
        with self.assertRaises(ValueError):
            L.qualified_operating_level_w(0.0, 3.0)


class RunLogTests(unittest.TestCase):
    def test_highest_quiet_level_is_taken(self):
        scan = L.scan_run_log(base_record()["run_log"])
        self.assertAlmostEqual(scan["highest_quiet_level_w"], 250.0, places=9)
        self.assertIsNone(scan["lowest_onset_level_w"])

    def test_lowest_onset_is_taken(self):
        scan = L.scan_run_log(
            [
                {"level_w": 100.0, "multipactor_observed": False},
                {"level_w": 300.0, "multipactor_observed": True},
                {"level_w": 260.0, "multipactor_observed": True},
            ]
        )
        self.assertAlmostEqual(scan["lowest_onset_level_w"], 260.0, places=9)
        self.assertAlmostEqual(scan["highest_quiet_level_w"], 100.0, places=9)

    def test_all_onset_log_has_no_quiet_level(self):
        scan = L.scan_run_log([{"level_w": 90.0, "multipactor_observed": True}])
        self.assertIsNone(scan["highest_quiet_level_w"])

    def test_empty_run_log_raises(self):
        with self.assertRaises(ValueError):
            L.scan_run_log([])

    def test_non_list_run_log_raises(self):
        with self.assertRaises(ValueError):
            L.scan_run_log({"level_w": 100.0})

    def test_entry_not_mapping_raises(self):
        with self.assertRaises(ValueError):
            L.scan_run_log([100.0])

    def test_non_boolean_observation_flag_raises(self):
        with self.assertRaises(ValueError):
            L.scan_run_log([{"level_w": 100.0, "multipactor_observed": "no"}])

    def test_non_positive_level_raises(self):
        with self.assertRaises(ValueError):
            L.scan_run_log([{"level_w": 0.0, "multipactor_observed": False}])


class DetectionCapabilityTests(unittest.TestCase):
    def test_one_of_each_family_passes(self):
        self.assertEqual(
            L.check_detection_capability(base_record()["detection_methods"]), []
        )

    def test_single_method_is_flagged(self):
        findings = L.check_detection_capability(
            [
                {
                    "name": "harmonic-detection",
                    "sensitivity_verified": True,
                    "calibration_in_date": True,
                }
            ]
        )
        self.assertTrue(any("at least" in f for f in findings), findings)
        self.assertTrue(any("local-detection-method" in f for f in findings), findings)

    def test_two_global_methods_miss_the_local_family(self):
        findings = L.check_detection_capability(
            [
                {
                    "name": "harmonic-detection",
                    "sensitivity_verified": True,
                    "calibration_in_date": True,
                },
                {
                    "name": "nulling-detection",
                    "sensitivity_verified": True,
                    "calibration_in_date": True,
                },
            ]
        )
        self.assertEqual(
            findings, ["no local-detection-method in the detection-capability"]
        )

    def test_unverified_sensitivity_is_flagged(self):
        methods = base_record()["detection_methods"]
        methods[1]["sensitivity_verified"] = False
        findings = L.check_detection_capability(methods)
        self.assertTrue(any("sensitivity_verified" in f for f in findings), findings)

    def test_expired_calibration_is_flagged(self):
        methods = base_record()["detection_methods"]
        methods[0]["calibration_in_date"] = False
        findings = L.check_detection_capability(methods)
        self.assertTrue(any("calibration_in_date" in f for f in findings), findings)

    def test_unknown_method_name_raises(self):
        with self.assertRaises(ValueError):
            L.check_detection_capability(
                [
                    {
                        "name": "thermal-camera",
                        "sensitivity_verified": True,
                        "calibration_in_date": True,
                    }
                ]
            )

    def test_method_not_mapping_raises(self):
        with self.assertRaises(ValueError):
            L.check_detection_capability(["electron-probe"])

    def test_non_list_methods_raises(self):
        with self.assertRaises(ValueError):
            L.check_detection_capability("electron-probe")

    def test_non_boolean_method_flag_raises(self):
        with self.assertRaises(ValueError):
            L.check_detection_capability(
                [
                    {
                        "name": "electron-probe",
                        "sensitivity_verified": 1,
                        "calibration_in_date": True,
                    }
                ]
            )


class SeedingTests(unittest.TestCase):
    def test_active_verified_seeding_passes(self):
        self.assertEqual(L.check_seeding(base_record()["seeding"]), [])

    def test_inactive_seeding_is_flagged(self):
        seeding = base_record()["seeding"]
        seeding["active"] = False
        self.assertEqual(
            L.check_seeding(seeding), ["electron-seeding: active is not satisfied"]
        )

    def test_unverified_effectiveness_is_flagged(self):
        seeding = base_record()["seeding"]
        seeding["effectiveness_verified"] = False
        findings = L.check_seeding(seeding)
        self.assertTrue(any("effectiveness_verified" in f for f in findings), findings)

    def test_unknown_seeding_source_raises(self):
        with self.assertRaises(ValueError):
            L.check_seeding(
                {"source": "candle", "active": True, "effectiveness_verified": True}
            )

    def test_non_mapping_seeding_raises(self):
        with self.assertRaises(ValueError):
            L.check_seeding("electron-gun")

    def test_non_boolean_seeding_flag_raises(self):
        with self.assertRaises(ValueError):
            L.check_seeding(
                {
                    "source": "electron-gun",
                    "active": "yes",
                    "effectiveness_verified": True,
                }
            )


class EnvironmentTests(unittest.TestCase):
    def test_enveloping_environment_passes(self):
        self.assertEqual(L.check_environment(base_record()["environment"]), [])

    def test_pressure_at_the_declared_limit_passes(self):
        env = base_record()["environment"]
        env["pressure_pa"] = L.VACUUM_LIMIT_PA
        self.assertEqual(L.check_environment(env), [])

    def test_pressure_above_the_limit_is_flagged(self):
        env = base_record()["environment"]
        env["pressure_pa"] = 5.0e-3
        findings = L.check_environment(env)
        self.assertTrue(any("vacuum-condition" in f for f in findings), findings)

    def test_cold_corner_short_is_flagged(self):
        env = base_record()["environment"]
        env["run_temp_min_c"] = 0.0
        findings = L.check_environment(env)
        self.assertTrue(any("cold corner" in f for f in findings), findings)

    def test_hot_corner_short_is_flagged(self):
        env = base_record()["environment"]
        env["run_temp_max_c"] = 50.0
        findings = L.check_environment(env)
        self.assertTrue(any("hot corner" in f for f in findings), findings)

    def test_envelope_exactly_matching_the_operating_range_passes(self):
        env = base_record()["environment"]
        env["run_temp_min_c"] = env["operating_temp_min_c"]
        env["run_temp_max_c"] = env["operating_temp_max_c"]
        self.assertEqual(L.check_environment(env), [])

    def test_inverted_run_envelope_raises(self):
        env = base_record()["environment"]
        env["run_temp_min_c"] = 80.0
        with self.assertRaises(ValueError):
            L.check_environment(env)

    def test_inverted_operating_envelope_raises(self):
        env = base_record()["environment"]
        env["operating_temp_min_c"] = 90.0
        with self.assertRaises(ValueError):
            L.check_environment(env)

    def test_missing_pressure_raises(self):
        env = base_record()["environment"]
        del env["pressure_pa"]
        with self.assertRaises(ValueError):
            L.check_environment(env)

    def test_non_mapping_environment_raises(self):
        with self.assertRaises(ValueError):
            L.check_environment(None)


class DeclaredLevelTests(unittest.TestCase):
    def test_no_onset_declares_the_highest_quiet_level(self):
        scan = {"highest_quiet_level_w": 250.0, "lowest_onset_level_w": None}
        self.assertAlmostEqual(L.declared_free_level_w(scan), 250.0, places=9)

    def test_onset_above_the_quiet_level_does_not_lower_it(self):
        scan = {"highest_quiet_level_w": 250.0, "lowest_onset_level_w": 400.0}
        self.assertAlmostEqual(L.declared_free_level_w(scan), 250.0, places=9)

    def test_onset_below_the_quiet_level_caps_the_declaration(self):
        scan = {"highest_quiet_level_w": 250.0, "lowest_onset_level_w": 200.0}
        declared = L.declared_free_level_w(scan)
        self.assertAlmostEqual(declared, 200.0 * L.ONSET_STEP_BACK, places=9)
        self.assertLess(declared, 200.0)

    def test_no_quiet_level_declares_nothing(self):
        scan = {"highest_quiet_level_w": None, "lowest_onset_level_w": 90.0}
        self.assertIsNone(L.declared_free_level_w(scan))

    def test_non_mapping_scan_raises(self):
        with self.assertRaises(ValueError):
            L.declared_free_level_w([250.0])


class DeclarationTests(unittest.TestCase):
    def test_complete_evidence_supports_the_declaration(self):
        out = L.evaluate_declaration(base_record())
        self.assertTrue(out["declarable"], out["findings"])
        self.assertEqual(out["findings"], [])
        self.assertAlmostEqual(out["declared_free_level_w"], 250.0, places=9)
        self.assertAlmostEqual(
            out["qualified_operating_level_w"] * L.db_to_ratio(3.0), 250.0, places=9
        )

    def test_run_short_of_the_required_level_is_not_declarable(self):
        out = L.evaluate_declaration(
            base_record(
                run_log=[{"level_w": 150.0, "multipactor_observed": False}]
            )
        )
        self.assertFalse(out["declarable"])
        self.assertTrue(any("does not reach" in f for f in out["findings"]))

    def test_level_short_by_representation_error_is_still_declarable(self):
        # The bench level was built up from two contributions, so it lands a
        # few units in the last place under the level reached by one
        # multiplication. That is representation error, not a shortfall.
        required = L.required_drive_level_w(100.0, 3.0)
        quiet = required - 8.0 * sys.float_info.epsilon * required
        self.assertLess(quiet, required)
        out = L.evaluate_declaration(
            base_record(run_log=[{"level_w": quiet, "multipactor_observed": False}])
        )
        self.assertTrue(out["declarable"], out["findings"])

    def test_level_short_by_one_percent_is_not_declarable(self):
        required = L.required_drive_level_w(100.0, 3.0)
        out = L.evaluate_declaration(
            base_record(
                run_log=[{"level_w": required * 0.99, "multipactor_observed": False}]
            )
        )
        self.assertFalse(out["declarable"])

    def test_recorded_onset_blocks_the_declaration_and_caps_the_level(self):
        out = L.evaluate_declaration(
            base_record(
                run_log=[
                    {"level_w": 250.0, "multipactor_observed": False},
                    {"level_w": 240.0, "multipactor_observed": True},
                ]
            )
        )
        self.assertFalse(out["declarable"])
        self.assertAlmostEqual(out["lowest_onset_level_w"], 240.0, places=9)
        self.assertLess(out["declared_free_level_w"], 240.0)

    def test_missing_seeding_evidence_blocks_the_declaration(self):
        out = L.evaluate_declaration(
            base_record(
                seeding={
                    "source": "radioactive-source",
                    "active": True,
                    "effectiveness_verified": False,
                }
            )
        )
        self.assertFalse(out["declarable"])

    def test_single_detection_family_blocks_the_declaration(self):
        out = L.evaluate_declaration(
            base_record(
                detection_methods=[
                    {
                        "name": "electron-probe",
                        "sensitivity_verified": True,
                        "calibration_in_date": True,
                    },
                    {
                        "name": "optical-detection",
                        "sensitivity_verified": True,
                        "calibration_in_date": True,
                    },
                ]
            )
        )
        self.assertFalse(out["declarable"])

    def test_all_onset_run_declares_nothing(self):
        out = L.evaluate_declaration(
            base_record(run_log=[{"level_w": 120.0, "multipactor_observed": True}])
        )
        self.assertFalse(out["declarable"])
        self.assertIsNone(out["declared_free_level_w"])
        self.assertIsNone(out["qualified_operating_level_w"])

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            L.evaluate_declaration(["record"])

    def test_missing_margin_raises(self):
        rec = base_record()
        del rec["margin_db"]
        with self.assertRaises(ValueError):
            L.evaluate_declaration(rec)


if __name__ == "__main__":
    unittest.main()
