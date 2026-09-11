"""
Offline deterministic unit tests for e1003_eq_mission_logic.
Run: python3 test_e1003_eq_mission.py
Must print OK with no network access.
"""
import unittest
from e1003_eq_mission_logic import (
    MISSION_TEST_TYPES,
    LEVEL_ACCEPTANCE,
    LEVEL_QUALIFICATION,
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_ERROR,
    STATUS_INCOMPLETE,
    MissionTestError,
    validate_test_record,
    compute_margin,
    evaluate_test_record,
    check_test_completeness,
    categorize_test,
    evaluate_sound_pressure,
    compile_results,
)


def _record(**overrides):
    base = {
        "test_id":   "T-001",
        "test_type": "acoustic",
        "level":     LEVEL_ACCEPTANCE,
        "measured":  120.0,
        "limit":     125.0,
    }
    base.update(overrides)
    return base


class TestMissionTestTypeRegistry(unittest.TestCase):
    def test_acoustic_present(self):
        self.assertIn("acoustic", MISSION_TEST_TYPES)

    def test_vibration_present(self):
        self.assertIn("vibration", MISSION_TEST_TYPES)

    def test_emc_present(self):
        self.assertIn("emc", MISSION_TEST_TYPES)

    def test_thermal_present(self):
        self.assertIn("thermal", MISSION_TEST_TYPES)

    def test_functional_present(self):
        self.assertIn("functional", MISSION_TEST_TYPES)

    def test_exactly_five_types(self):
        self.assertEqual(len(MISSION_TEST_TYPES), 5)


class TestValidateTestRecord(unittest.TestCase):
    def test_valid_record_does_not_raise(self):
        validate_test_record(_record())

    def test_missing_measured_raises(self):
        rec = _record()
        del rec["measured"]
        with self.assertRaises(MissionTestError):
            validate_test_record(rec)

    def test_missing_limit_raises(self):
        rec = _record()
        del rec["limit"]
        with self.assertRaises(MissionTestError):
            validate_test_record(rec)

    def test_missing_test_id_raises(self):
        rec = _record()
        del rec["test_id"]
        with self.assertRaises(MissionTestError):
            validate_test_record(rec)

    def test_unrecognized_test_type_raises(self):
        with self.assertRaises(MissionTestError):
            validate_test_record(_record(test_type="pyrotechnic"))

    def test_invalid_level_raises(self):
        with self.assertRaises(MissionTestError):
            validate_test_record(_record(level="protoflight"))

    def test_non_numeric_measured_raises(self):
        with self.assertRaises(MissionTestError):
            validate_test_record(_record(measured="high"))

    def test_non_numeric_limit_raises(self):
        with self.assertRaises(MissionTestError):
            validate_test_record(_record(limit=None))

    def test_zero_limit_raises(self):
        with self.assertRaises(MissionTestError):
            validate_test_record(_record(limit=0))

    def test_negative_limit_raises(self):
        with self.assertRaises(MissionTestError):
            validate_test_record(_record(limit=-5.0))

    def test_qualification_level_accepted(self):
        validate_test_record(_record(level=LEVEL_QUALIFICATION))

    def test_all_five_test_types_accepted(self):
        for t in MISSION_TEST_TYPES:
            validate_test_record(_record(test_type=t))


class TestComputeMargin(unittest.TestCase):
    def test_positive_margin_higher_is_worse(self):
        self.assertAlmostEqual(compute_margin(120.0, 130.0, True), 10.0)

    def test_negative_margin_higher_is_worse(self):
        self.assertAlmostEqual(compute_margin(135.0, 130.0, True), -5.0)

    def test_zero_margin_higher_is_worse(self):
        self.assertAlmostEqual(compute_margin(130.0, 130.0, True), 0.0)

    def test_positive_margin_lower_is_worse(self):
        self.assertAlmostEqual(compute_margin(55.0, 40.0, False), 15.0)

    def test_negative_margin_lower_is_worse(self):
        self.assertAlmostEqual(compute_margin(30.0, 40.0, False), -10.0)


class TestEvaluateTestRecord(unittest.TestCase):
    def test_pass_when_below_limit(self):
        result = evaluate_test_record(_record(measured=110.0, limit=125.0))
        self.assertEqual(result["status"], STATUS_PASS)
        self.assertGreater(result["margin"], 0)

    def test_fail_when_above_limit(self):
        result = evaluate_test_record(_record(measured=130.0, limit=125.0))
        self.assertEqual(result["status"], STATUS_FAIL)
        self.assertLess(result["margin"], 0)

    def test_pass_at_exact_limit(self):
        result = evaluate_test_record(_record(measured=125.0, limit=125.0))
        self.assertEqual(result["status"], STATUS_PASS)
        self.assertAlmostEqual(result["margin"], 0.0)

    def test_result_contains_required_keys(self):
        result = evaluate_test_record(_record())
        for key in ("test_id", "test_type", "level", "status", "margin", "note"):
            self.assertIn(key, result)

    def test_vibration_pass(self):
        rec = _record(test_type="vibration", measured=4.5, limit=6.0)
        result = evaluate_test_record(rec)
        self.assertEqual(result["status"], STATUS_PASS)
        self.assertAlmostEqual(result["margin"], 1.5)

    def test_emc_qualification_fail(self):
        rec = _record(test_type="emc", level=LEVEL_QUALIFICATION, measured=55.0, limit=50.0)
        result = evaluate_test_record(rec)
        self.assertEqual(result["status"], STATUS_FAIL)

    def test_invalid_record_raises(self):
        with self.assertRaises(MissionTestError):
            evaluate_test_record(_record(test_type="unknown"))


class TestCheckTestCompleteness(unittest.TestCase):
    def test_complete_campaign(self):
        required = ["acoustic", "vibration", "emc"]
        submitted = ["acoustic", "vibration", "emc", "thermal"]
        ok, missing = check_test_completeness(submitted, required)
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_incomplete_campaign_reports_missing(self):
        required = ["acoustic", "vibration", "emc"]
        submitted = ["acoustic"]
        ok, missing = check_test_completeness(submitted, required)
        self.assertFalse(ok)
        self.assertIn("vibration", missing)
        self.assertIn("emc", missing)

    def test_empty_required_is_complete(self):
        ok, missing = check_test_completeness([], [])
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_missing_list_is_sorted(self):
        required = ["vibration", "acoustic", "emc"]
        submitted = []
        _, missing = check_test_completeness(submitted, required)
        self.assertEqual(missing, sorted(missing))

    def test_duplicate_submitted_types_handled(self):
        required = ["acoustic", "vibration"]
        submitted = ["acoustic", "acoustic", "vibration"]
        ok, missing = check_test_completeness(submitted, required)
        self.assertTrue(ok)


class TestCategorizeTest(unittest.TestCase):
    def test_acoustic_label_contains_acoustic(self):
        self.assertIn("Acoustic", categorize_test("acoustic"))

    def test_vibration_label_contains_vibration(self):
        self.assertIn("Vibration", categorize_test("vibration"))

    def test_emc_label_contains_electromagnetic(self):
        self.assertIn("Electromagnetic", categorize_test("emc"))

    def test_thermal_label_contains_thermal(self):
        self.assertIn("Thermal", categorize_test("thermal"))

    def test_functional_label_contains_functional(self):
        self.assertIn("Functional", categorize_test("functional"))

    def test_unknown_type_raises(self):
        with self.assertRaises(MissionTestError):
            categorize_test("shock")


class TestEvaluateSoundPressure(unittest.TestCase):
    def test_below_limit_passes(self):
        status, margin = evaluate_sound_pressure(118.0, 125.0)
        self.assertEqual(status, STATUS_PASS)
        self.assertAlmostEqual(margin, 7.0)

    def test_above_limit_fails(self):
        status, margin = evaluate_sound_pressure(130.0, 125.0)
        self.assertEqual(status, STATUS_FAIL)
        self.assertAlmostEqual(margin, -5.0)

    def test_at_limit_passes(self):
        status, margin = evaluate_sound_pressure(125.0, 125.0)
        self.assertEqual(status, STATUS_PASS)
        self.assertAlmostEqual(margin, 0.0)

    def test_qualification_level_accepted(self):
        status, _ = evaluate_sound_pressure(110.0, 131.0, test_level=LEVEL_QUALIFICATION)
        self.assertEqual(status, STATUS_PASS)

    def test_non_numeric_measured_raises(self):
        with self.assertRaises(MissionTestError):
            evaluate_sound_pressure("loud", 125.0)

    def test_non_numeric_limit_raises(self):
        with self.assertRaises(MissionTestError):
            evaluate_sound_pressure(120.0, "high")

    def test_invalid_level_raises(self):
        with self.assertRaises(MissionTestError):
            evaluate_sound_pressure(120.0, 125.0, test_level="dev")


class TestCompileResults(unittest.TestCase):
    def test_all_pass_status(self):
        records = [
            _record(test_id="R1", test_type="acoustic",  measured=110.0, limit=130.0),
            _record(test_id="R2", test_type="vibration", measured=3.0,   limit=5.0),
        ]
        summary = compile_results(records)
        self.assertEqual(summary["overall_status"], STATUS_PASS)
        self.assertEqual(summary["passed"], 2)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["errors"], [])

    def test_one_fail_yields_fail_status(self):
        records = [
            _record(test_id="R3", test_type="emc", measured=60.0, limit=50.0),
        ]
        summary = compile_results(records)
        self.assertEqual(summary["overall_status"], STATUS_FAIL)
        self.assertEqual(summary["failed"], 1)

    def test_invalid_record_goes_to_errors(self):
        records = [
            _record(test_id="R4", test_type="nonexistent"),
        ]
        summary = compile_results(records)
        self.assertEqual(summary["overall_status"], STATUS_ERROR)
        self.assertEqual(len(summary["errors"]), 1)
        self.assertEqual(summary["errors"][0]["test_id"], "R4")

    def test_empty_campaign_is_incomplete(self):
        summary = compile_results([])
        self.assertEqual(summary["overall_status"], STATUS_INCOMPLETE)
        self.assertEqual(summary["total"], 0)

    def test_summary_total_matches_input_count(self):
        records = [
            _record(test_id=f"X{i}", measured=float(i * 10), limit=200.0)
            for i in range(5)
        ]
        summary = compile_results(records)
        self.assertEqual(summary["total"], 5)

    def test_mixed_pass_fail_is_fail(self):
        records = [
            _record(test_id="M1", measured=100.0, limit=130.0),
            _record(test_id="M2", measured=140.0, limit=130.0),
        ]
        summary = compile_results(records)
        self.assertEqual(summary["overall_status"], STATUS_FAIL)
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["failed"], 1)


if __name__ == "__main__":
    unittest.main()
