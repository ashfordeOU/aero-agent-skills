"""
Behavior-contract tests for e1003_el_thermal_logic.py.
Runs with: python3 test_e1003_el_thermal.py
stdlib unittest only, offline, deterministic.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1003_el_thermal_logic import (
    categorize_test,
    validate_tvac,
    validate_tbal,
    validate_mission_pressure,
    validate_iss,
    assess_campaign,
    QUAL_MARGIN_K,
    ACCEPT_MARGIN_K,
    TVAC_MIN_CYCLES_QUAL,
    TVAC_MIN_CYCLES_ACCEPT,
    TVAC_MIN_SOAK_HOT_H,
    TVAC_MIN_SOAK_COLD_H,
    TVAC_MAX_PRESSURE_PA,
    TBAL_MAX_DELTA_K,
    MISSION_PRESS_MIN_PA,
    MISSION_PRESS_MAX_PA,
    ISS_EXT_HOT_C,
    ISS_EXT_COLD_C,
)


# --------------------------------------------------------------------------- #
# categorize_test
# --------------------------------------------------------------------------- #

class TestCategorizeTest(unittest.TestCase):

    def test_thermal_vacuum_is_environmental(self):
        self.assertEqual(categorize_test("thermal_vacuum"), "environmental")

    def test_thermal_balance_is_model_correlation(self):
        self.assertEqual(categorize_test("thermal_balance"), "model_correlation")

    def test_mission_pressure_is_environmental(self):
        self.assertEqual(categorize_test("mission_pressure"), "environmental")

    def test_iss_specific_is_environmental(self):
        self.assertEqual(categorize_test("iss_specific"), "environmental")

    def test_unknown_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_test("ambient_soak")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_test("")


# --------------------------------------------------------------------------- #
# validate_tvac
# --------------------------------------------------------------------------- #

class TestValidateTvac(unittest.TestCase):

    def _good_qual(self, **overrides):
        defaults = dict(
            hot_temp_c=85.0,
            cold_temp_c=-50.0,
            soak_hot_h=4.0,
            soak_cold_h=4.0,
            cycles=4,
            chamber_pressure_pa=1e-4,
            level="qualification",
            design_hot_c=70.0,
            design_cold_c=-35.0,
        )
        defaults.update(overrides)
        return defaults

    def test_valid_qualification_no_findings(self):
        findings = validate_tvac(**self._good_qual())
        self.assertEqual(findings, [])

    def test_valid_acceptance_no_findings(self):
        params = self._good_qual(
            hot_temp_c=75.0,
            cold_temp_c=-40.0,
            cycles=2,
            level="acceptance",
        )
        findings = validate_tvac(**params)
        self.assertEqual(findings, [])

    def test_valid_protoflight_no_findings(self):
        findings = validate_tvac(**self._good_qual(level="protoflight"))
        self.assertEqual(findings, [])

    def test_hot_soak_below_minimum_flagged(self):
        findings = validate_tvac(**self._good_qual(soak_hot_h=TVAC_MIN_SOAK_HOT_H - 0.5))
        self.assertTrue(any("hot soak" in f.lower() for f in findings))

    def test_cold_soak_below_minimum_flagged(self):
        findings = validate_tvac(**self._good_qual(soak_cold_h=TVAC_MIN_SOAK_COLD_H - 0.5))
        self.assertTrue(any("cold soak" in f.lower() for f in findings))

    def test_cycle_count_too_low_for_qualification(self):
        findings = validate_tvac(**self._good_qual(cycles=TVAC_MIN_CYCLES_QUAL - 1))
        self.assertTrue(any("cycle" in f.lower() for f in findings))

    def test_cycle_count_too_low_for_acceptance(self):
        findings = validate_tvac(**self._good_qual(cycles=1, level="acceptance"))
        self.assertTrue(any("cycle" in f.lower() for f in findings))

    def test_chamber_pressure_above_limit_flagged(self):
        findings = validate_tvac(**self._good_qual(chamber_pressure_pa=TVAC_MAX_PRESSURE_PA * 10))
        self.assertTrue(any("pressure" in f.lower() for f in findings))

    def test_hot_margin_insufficient_flagged(self):
        # design_hot_c = 70, hot_temp_c = 75 → margin 5 K < QUAL_MARGIN_K (10)
        findings = validate_tvac(**self._good_qual(hot_temp_c=75.0, design_hot_c=70.0))
        self.assertTrue(any("hot margin" in f.lower() for f in findings))

    def test_cold_margin_insufficient_flagged(self):
        # design_cold_c = -35, cold_temp_c = -40 → cold margin 5 K < QUAL_MARGIN_K (10)
        findings = validate_tvac(**self._good_qual(cold_temp_c=-40.0, design_cold_c=-35.0))
        self.assertTrue(any("cold margin" in f.lower() for f in findings))

    def test_hot_below_cold_flagged(self):
        findings = validate_tvac(**self._good_qual(hot_temp_c=-60.0, cold_temp_c=10.0))
        self.assertTrue(any("above" in f.lower() or "strictly" in f.lower() for f in findings))

    def test_unknown_level_returns_finding(self):
        findings = validate_tvac(**self._good_qual(level="flight"))
        self.assertTrue(len(findings) == 1)
        self.assertIn("Unknown", findings[0])


# --------------------------------------------------------------------------- #
# validate_tbal
# --------------------------------------------------------------------------- #

class TestValidateTbal(unittest.TestCase):

    def test_all_nodes_within_tolerance_no_findings(self):
        measured = [20.0, -10.0, 55.3]
        model = [20.5, -10.1, 55.0]
        findings = validate_tbal(measured, model)
        self.assertEqual(findings, [])

    def test_node_exceeding_tolerance_flagged(self):
        measured = [20.0, -10.0, 55.0]
        model = [20.0, -10.0, 55.0 + TBAL_MAX_DELTA_K + 0.1]
        findings = validate_tbal(measured, model)
        self.assertEqual(len(findings), 1)
        self.assertIn("Node 2", findings[0])

    def test_multiple_nodes_flagged(self):
        measured = [0.0, 0.0, 0.0]
        model = [5.0, 5.0, 5.0]
        findings = validate_tbal(measured, model)
        self.assertEqual(len(findings), 3)

    def test_exactly_at_threshold_not_flagged(self):
        measured = [0.0]
        model = [TBAL_MAX_DELTA_K]
        findings = validate_tbal(measured, model)
        self.assertEqual(findings, [])

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            validate_tbal([10.0, 20.0], [10.0])

    def test_empty_lists_no_findings(self):
        findings = validate_tbal([], [])
        self.assertEqual(findings, [])


# --------------------------------------------------------------------------- #
# validate_mission_pressure
# --------------------------------------------------------------------------- #

class TestValidateMissionPressure(unittest.TestCase):

    def _good(self, **overrides):
        defaults = dict(
            test_pressure_pa=1.013e5,
            hot_temp_c=60.0,
            cold_temp_c=-20.0,
            level="qualification",
            design_hot_c=45.0,
            design_cold_c=-5.0,
        )
        defaults.update(overrides)
        return defaults

    def test_valid_mission_pressure_no_findings(self):
        findings = validate_mission_pressure(**self._good())
        self.assertEqual(findings, [])

    def test_pressure_below_band_flagged(self):
        findings = validate_mission_pressure(**self._good(test_pressure_pa=MISSION_PRESS_MIN_PA / 10))
        self.assertTrue(any("below" in f.lower() for f in findings))

    def test_pressure_above_band_flagged(self):
        findings = validate_mission_pressure(**self._good(test_pressure_pa=MISSION_PRESS_MAX_PA * 2))
        self.assertTrue(any("exceed" in f.lower() for f in findings))

    def test_hot_margin_insufficient_flagged(self):
        # design_hot_c = 45, hot_temp_c = 50 → 5 K < QUAL_MARGIN_K (10)
        findings = validate_mission_pressure(**self._good(hot_temp_c=50.0, design_hot_c=45.0))
        self.assertTrue(any("hot margin" in f.lower() for f in findings))


# --------------------------------------------------------------------------- #
# validate_iss
# --------------------------------------------------------------------------- #

class TestValidateIss(unittest.TestCase):

    def _good(self, **overrides):
        defaults = dict(
            hot_temp_c=ISS_EXT_HOT_C + QUAL_MARGIN_K,
            cold_temp_c=ISS_EXT_COLD_C - QUAL_MARGIN_K,
            soak_hot_h=4.0,
            soak_cold_h=4.0,
            cycles=4,
            chamber_pressure_pa=1e-4,
            level="qualification",
            design_hot_c=ISS_EXT_HOT_C,
            design_cold_c=ISS_EXT_COLD_C,
        )
        defaults.update(overrides)
        return defaults

    def test_valid_iss_no_findings(self):
        findings = validate_iss(**self._good())
        self.assertEqual(findings, [])

    def test_hot_setpoint_below_iss_limit_flagged(self):
        findings = validate_iss(**self._good(hot_temp_c=ISS_EXT_HOT_C - 5.0))
        self.assertTrue(any("iss" in f.lower() and "hot" in f.lower() for f in findings))

    def test_cold_setpoint_above_iss_limit_flagged(self):
        findings = validate_iss(**self._good(cold_temp_c=ISS_EXT_COLD_C + 5.0))
        self.assertTrue(any("iss" in f.lower() and "cold" in f.lower() for f in findings))

    def test_iss_inherits_tvac_cycle_check(self):
        findings = validate_iss(**self._good(cycles=1))
        self.assertTrue(any("cycle" in f.lower() for f in findings))


# --------------------------------------------------------------------------- #
# assess_campaign
# --------------------------------------------------------------------------- #

class TestAssessCampaign(unittest.TestCase):

    def test_complete_campaign_no_missing(self):
        missing = assess_campaign(["thermal_vacuum", "thermal_balance"])
        self.assertEqual(missing, [])

    def test_complete_campaign_with_extras_no_missing(self):
        missing = assess_campaign(
            ["thermal_vacuum", "thermal_balance", "mission_pressure", "iss_specific"]
        )
        self.assertEqual(missing, [])

    def test_missing_thermal_balance_reported(self):
        missing = assess_campaign(["thermal_vacuum"])
        self.assertIn("thermal_balance", missing)

    def test_missing_thermal_vacuum_reported(self):
        missing = assess_campaign(["thermal_balance"])
        self.assertIn("thermal_vacuum", missing)

    def test_empty_campaign_both_mandatory_missing(self):
        missing = assess_campaign([])
        self.assertIn("thermal_vacuum", missing)
        self.assertIn("thermal_balance", missing)

    def test_result_is_sorted(self):
        missing = assess_campaign([])
        self.assertEqual(missing, sorted(missing))


if __name__ == "__main__":
    unittest.main()
