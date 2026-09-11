#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §4.4.1 test conditions definition
and validation.

Exercises scripts/e1003_test_conditions_logic.py (stdlib unittest,
offline).  Contract: an ambient environment parameter is categorized as
compliant when its value is within the defined low/high limit band and
non-compliant otherwise; invalid limit ranges or empty parameter names
raise; a cleanliness area is compliant when its actual ISO class is
equal to or stricter than the required class, non-compliant otherwise,
and an unrecognized class label raises; ESD controls pass when all
required controls are present for ESD-sensitive items, and pass
unconditionally for non-sensitive items; configuration completeness
passes when every required field appears in the documented-field set;
monitoring coverage passes when every required channel is defined with a
positive recording rate and a non-None limits set; and the aggregate
validate_test_conditions result is compliant exactly when the findings
list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_test_conditions_logic as tc  # noqa: E402


class EnvironmentConditionTest(unittest.TestCase):
    def test_value_within_range_is_compliant(self):
        self.assertEqual(
            tc.categorize_environment_condition("temperature_C", 20.0, 15.0, 25.0),
            tc.CONDITION_COMPLIANT,
        )

    def test_value_at_low_limit_is_compliant(self):
        self.assertEqual(
            tc.categorize_environment_condition("humidity_pct", 40.0, 40.0, 60.0),
            tc.CONDITION_COMPLIANT,
        )

    def test_value_at_high_limit_is_compliant(self):
        self.assertEqual(
            tc.categorize_environment_condition("pressure_Pa", 101325.0, 90000.0, 101325.0),
            tc.CONDITION_COMPLIANT,
        )

    def test_value_below_low_limit_is_non_compliant(self):
        self.assertEqual(
            tc.categorize_environment_condition("temperature_C", 10.0, 15.0, 25.0),
            tc.CONDITION_NON_COMPLIANT,
        )

    def test_value_above_high_limit_is_non_compliant(self):
        self.assertEqual(
            tc.categorize_environment_condition("temperature_C", 30.0, 15.0, 25.0),
            tc.CONDITION_NON_COMPLIANT,
        )

    def test_empty_param_name_raises(self):
        with self.assertRaises(ValueError):
            tc.categorize_environment_condition("", 20.0, 15.0, 25.0)

    def test_inverted_limits_raises(self):
        with self.assertRaises(ValueError):
            tc.categorize_environment_condition("temperature_C", 20.0, 25.0, 15.0)


class CleanlinessClassTest(unittest.TestCase):
    def test_actual_equals_required_is_compliant(self):
        self.assertEqual(
            tc.check_cleanliness_class("area-1", "ISO5", "ISO5"), []
        )

    def test_actual_stricter_than_required_is_compliant(self):
        # ISO3 is stricter than ISO5 (lower number = stricter)
        self.assertEqual(
            tc.check_cleanliness_class("area-2", "ISO5", "ISO3"), []
        )

    def test_actual_less_strict_than_required_is_flagged(self):
        violations = tc.check_cleanliness_class("area-3", "ISO5", "ISO7")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "cleanliness_class_insufficient")
        self.assertEqual(violations[0]["area"], "area-3")

    def test_unknown_required_class_raises(self):
        with self.assertRaises(ValueError):
            tc.check_cleanliness_class("area-4", "ISO0", "ISO5")

    def test_unknown_actual_class_raises(self):
        with self.assertRaises(ValueError):
            tc.check_cleanliness_class("area-5", "ISO5", "CLEAN")


class EsdControlTest(unittest.TestCase):
    def test_esd_not_required_no_violation(self):
        self.assertEqual(
            tc.check_esd_controls("item-1", False, []), []
        )

    def test_esd_not_required_ignores_controls_present(self):
        self.assertEqual(
            tc.check_esd_controls("item-2", False, ["esd_wrist_strap"]), []
        )

    def test_esd_required_all_controls_present_no_violation(self):
        all_controls = list(tc.REQUIRED_ESD_CONTROLS)
        self.assertEqual(
            tc.check_esd_controls("item-3", True, all_controls), []
        )

    def test_esd_required_missing_one_control_flagged(self):
        # Provide all except esd_mat
        partial = [c for c in tc.REQUIRED_ESD_CONTROLS if c != "esd_mat"]
        violations = tc.check_esd_controls("item-4", True, partial)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "esd_control_missing")
        self.assertIn("esd_mat", violations[0]["missing_controls"])

    def test_esd_required_no_controls_present_flagged(self):
        violations = tc.check_esd_controls("item-5", True, [])
        self.assertEqual(len(violations), 1)
        self.assertEqual(len(violations[0]["missing_controls"]), len(tc.REQUIRED_ESD_CONTROLS))


class ConfigurationCompletenessTest(unittest.TestCase):
    def test_all_fields_documented_no_violation(self):
        self.assertEqual(
            tc.check_configuration_completeness(
                "cfg-1",
                ["sw_build_id", "hw_config_state"],
                ["sw_build_id", "hw_config_state", "extra_field"],
            ),
            [],
        )

    def test_missing_field_flagged(self):
        violations = tc.check_configuration_completeness(
            "cfg-2",
            ["sw_build_id", "hw_config_state", "gse_connections"],
            ["sw_build_id"],
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "configuration_fields_missing")
        self.assertIn("hw_config_state", violations[0]["missing_fields"])
        self.assertIn("gse_connections", violations[0]["missing_fields"])

    def test_no_required_fields_is_compliant(self):
        self.assertEqual(
            tc.check_configuration_completeness("cfg-3", [], []), []
        )

    def test_extra_documented_fields_are_allowed(self):
        self.assertEqual(
            tc.check_configuration_completeness(
                "cfg-4", ["sw_build_id"], ["sw_build_id", "notes", "revision"]
            ),
            [],
        )


class MonitoringChannelTest(unittest.TestCase):
    def test_valid_channel_no_violation(self):
        self.assertEqual(
            tc.check_monitoring_channel("CH_TEMP", 10.0, {"low": -10, "high": 50}), []
        )

    def test_zero_rate_flagged(self):
        violations = tc.check_monitoring_channel("CH_PRES", 0, {"low": 0, "high": 200})
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "monitoring_channel_rate_zero")

    def test_undefined_limits_flagged(self):
        violations = tc.check_monitoring_channel("CH_HUM", 1.0, None)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "monitoring_channel_limits_undefined")

    def test_zero_rate_and_undefined_limits_both_flagged(self):
        violations = tc.check_monitoring_channel("CH_EMI", 0, None)
        self.assertEqual(len(violations), 2)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            tc.check_monitoring_channel("CH_BAD", -1.0, {"low": 0, "high": 1})


class MonitoringCoverageTest(unittest.TestCase):
    def test_all_channels_defined_no_violation(self):
        defined = {
            "CH_TEMP": {"recording_rate_hz": 1.0, "limits": {"low": 15, "high": 25}},
            "CH_HUM": {"recording_rate_hz": 0.5, "limits": {"low": 30, "high": 70}},
        }
        self.assertEqual(
            tc.check_monitoring_coverage("mon-1", ["CH_TEMP", "CH_HUM"], defined), []
        )

    def test_missing_channel_flagged(self):
        defined = {
            "CH_TEMP": {"recording_rate_hz": 1.0, "limits": {"low": 15, "high": 25}},
        }
        violations = tc.check_monitoring_coverage(
            "mon-2", ["CH_TEMP", "CH_PRES"], defined
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "monitoring_channel_not_defined")
        self.assertEqual(violations[0]["channel"], "CH_PRES")

    def test_defined_channel_with_zero_rate_flagged(self):
        defined = {
            "CH_TEMP": {"recording_rate_hz": 0, "limits": {"low": 15, "high": 25}},
        }
        violations = tc.check_monitoring_coverage("mon-3", ["CH_TEMP"], defined)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "monitoring_channel_rate_zero")


class ValidateTestConditionsTest(unittest.TestCase):
    def _compliant_conditions(self):
        return {
            "environment": [
                {"param": "temperature_C", "value": 20.0, "low_limit": 15.0, "high_limit": 25.0}
            ],
            "cleanliness_areas": [
                {"area_id": "clean-room-1", "required_class": "ISO6", "actual_class": "ISO5"}
            ],
            "esd_items": [
                {
                    "item_id": "pcb-1",
                    "esd_required": True,
                    "controls_present": list(tc.REQUIRED_ESD_CONTROLS),
                }
            ],
            "configurations": [
                {
                    "config_id": "cfg-alpha",
                    "required_fields": ["sw_build_id", "hw_config_state"],
                    "documented_fields": ["sw_build_id", "hw_config_state"],
                }
            ],
            "monitoring": [
                {
                    "monitor_id": "mon-alpha",
                    "required_channels": ["CH_TEMP"],
                    "defined_channels": {
                        "CH_TEMP": {"recording_rate_hz": 1.0, "limits": {"low": 15, "high": 25}}
                    },
                }
            ],
        }

    def test_fully_compliant_conditions_no_findings(self):
        result = tc.validate_test_conditions(self._compliant_conditions())
        self.assertEqual(result["findings"], [])
        self.assertTrue(tc.is_test_conditions_compliant(result))

    def test_environment_violation_surfaces_in_findings(self):
        cond = self._compliant_conditions()
        cond["environment"][0]["value"] = 35.0  # above high limit of 25
        result = tc.validate_test_conditions(cond)
        categories = [f["category"] for f in result["findings"]]
        self.assertIn("environment", categories)

    def test_cleanliness_violation_surfaces_in_findings(self):
        cond = self._compliant_conditions()
        cond["cleanliness_areas"][0]["actual_class"] = "ISO9"  # too dirty for ISO6
        result = tc.validate_test_conditions(cond)
        categories = [f["category"] for f in result["findings"]]
        self.assertIn("cleanliness", categories)

    def test_esd_violation_surfaces_in_findings(self):
        cond = self._compliant_conditions()
        cond["esd_items"][0]["controls_present"] = []  # all controls missing
        result = tc.validate_test_conditions(cond)
        categories = [f["category"] for f in result["findings"]]
        self.assertIn("esd", categories)

    def test_configuration_violation_surfaces_in_findings(self):
        cond = self._compliant_conditions()
        cond["configurations"][0]["documented_fields"] = []  # required fields missing
        result = tc.validate_test_conditions(cond)
        categories = [f["category"] for f in result["findings"]]
        self.assertIn("configuration", categories)

    def test_monitoring_violation_surfaces_in_findings(self):
        cond = self._compliant_conditions()
        cond["monitoring"][0]["required_channels"].append("CH_MISSING")
        result = tc.validate_test_conditions(cond)
        categories = [f["category"] for f in result["findings"]]
        self.assertIn("monitoring", categories)

    def test_multiple_violations_all_reported(self):
        cond = self._compliant_conditions()
        cond["environment"][0]["value"] = 99.0
        cond["esd_items"][0]["controls_present"] = []
        result = tc.validate_test_conditions(cond)
        categories = {f["category"] for f in result["findings"]}
        self.assertIn("environment", categories)
        self.assertIn("esd", categories)
        self.assertFalse(tc.is_test_conditions_compliant(result))

    def test_empty_conditions_is_compliant(self):
        result = tc.validate_test_conditions({})
        self.assertEqual(result["findings"], [])
        self.assertTrue(tc.is_test_conditions_compliant(result))

    def test_is_compliant_false_for_nonempty_findings(self):
        result = {"findings": [{"category": "environment", "issue": "out_of_range"}]}
        self.assertFalse(tc.is_test_conditions_compliant(result))


if __name__ == "__main__":
    unittest.main()
