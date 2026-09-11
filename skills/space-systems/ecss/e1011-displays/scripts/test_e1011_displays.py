"""
Gate 3 contract tests — ECSS-E-ST-10-11C §4.9.4 display design logic.
stdlib unittest, deterministic, offline. Run: python3 test_e1011_displays.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_displays_logic import (
    validate_display_format,
    validate_display_density,
    validate_alarm_entry,
    assess_display,
)


class TestValidateDisplayFormat(unittest.TestCase):

    def _make_display(self, **kwargs):
        base = {
            "display_id": "DSP-001",
            "layout_type": "graphical",
            "font_size_pt": 12,
            "contrast_ratio": 5.0,
        }
        base.update(kwargs)
        return base

    def test_valid_display_passes(self):
        result = validate_display_format(self._make_display())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_unknown_layout_type_fails(self):
        result = validate_display_format(self._make_display(layout_type="freeform"))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("approved set" in f for f in result["findings"]))

    def test_font_size_below_minimum_fails(self):
        result = validate_display_format(self._make_display(font_size_pt=8))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("below the HFE minimum" in f for f in result["findings"]))

    def test_font_size_at_minimum_passes(self):
        result = validate_display_format(self._make_display(font_size_pt=10))
        self.assertTrue(result["compliant"])

    def test_contrast_ratio_below_minimum_fails(self):
        result = validate_display_format(self._make_display(contrast_ratio=3.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("contrast_ratio" in f for f in result["findings"]))

    def test_contrast_ratio_at_minimum_passes(self):
        result = validate_display_format(self._make_display(contrast_ratio=4.5))
        self.assertTrue(result["compliant"])

    def test_empty_display_id_fails(self):
        result = validate_display_format(self._make_display(display_id=""))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("display_id is empty" in f for f in result["findings"]))

    def test_all_approved_layout_types_pass(self):
        for lt in ("list", "graphical", "schematic", "alphanumeric", "combined"):
            result = validate_display_format(self._make_display(layout_type=lt))
            self.assertTrue(result["compliant"], msg=f"layout_type '{lt}' should pass")

    def test_non_str_layout_type_raises(self):
        with self.assertRaises(TypeError):
            validate_display_format(self._make_display(layout_type=42))

    def test_non_numeric_font_size_raises(self):
        with self.assertRaises(TypeError):
            validate_display_format(self._make_display(font_size_pt="large"))

    def test_non_numeric_contrast_ratio_raises(self):
        with self.assertRaises(TypeError):
            validate_display_format(self._make_display(contrast_ratio="high"))

    def test_missing_required_key_raises(self):
        with self.assertRaises(ValueError):
            validate_display_format({"display_id": "X", "layout_type": "list"})

    def test_result_contains_required_keys(self):
        result = validate_display_format(self._make_display())
        for key in ("display_id", "layout_type", "compliant", "findings"):
            self.assertIn(key, result)

    def test_float_font_size_accepted(self):
        result = validate_display_format(self._make_display(font_size_pt=10.5))
        self.assertTrue(result["compliant"])


class TestValidateDisplayDensity(unittest.TestCase):

    def test_valid_density_passes(self):
        result = validate_display_density("DSP-001", 10, 5)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_parameter_count_exceeds_default_limit_fails(self):
        result = validate_display_density("DSP-002", 16, 5)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("parameter_count" in f for f in result["findings"]))

    def test_visible_alarm_count_exceeds_default_limit_fails(self):
        result = validate_display_density("DSP-003", 5, 13)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("alarm_count_visible" in f for f in result["findings"]))

    def test_counts_at_exact_default_limits_pass(self):
        result = validate_display_density("DSP-004", 15, 12)
        self.assertTrue(result["compliant"])

    def test_custom_max_parameters_tighter(self):
        result = validate_display_density("DSP-005", 10, 5, max_parameters=8)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("parameter_count" in f for f in result["findings"]))

    def test_zero_counts_pass(self):
        result = validate_display_density("DSP-006", 0, 0)
        self.assertTrue(result["compliant"])

    def test_negative_parameter_count_raises(self):
        with self.assertRaises(ValueError):
            validate_display_density("DSP-007", -1, 0)

    def test_negative_alarm_count_raises(self):
        with self.assertRaises(ValueError):
            validate_display_density("DSP-008", 0, -1)

    def test_non_int_parameter_count_raises(self):
        with self.assertRaises(TypeError):
            validate_display_density("DSP-009", 10.5, 0)

    def test_invalid_max_parameters_raises(self):
        with self.assertRaises(ValueError):
            validate_display_density("DSP-010", 5, 5, max_parameters=0)

    def test_result_contains_required_keys(self):
        result = validate_display_density("DSP-011", 3, 2)
        for key in ("display_id", "parameter_count", "alarm_count_visible",
                    "compliant", "findings"):
            self.assertIn(key, result)


class TestValidateAlarmEntry(unittest.TestCase):

    def _make_alarm(self, **kwargs):
        base = {
            "alarm_id": "ALM-001",
            "priority": "advisory",
            "state": "normal",
            "visual_distinct": True,
            "auditory_distinct": False,
            "suppression_visible": False,
        }
        base.update(kwargs)
        return base

    def test_normal_advisory_alarm_passes(self):
        result = validate_alarm_entry(self._make_alarm())
        self.assertTrue(result["compliant"])

    def test_active_warning_requires_visual_and_auditory(self):
        alarm = self._make_alarm(
            priority="warning", state="active",
            visual_distinct=True, auditory_distinct=True,
        )
        result = validate_alarm_entry(alarm)
        self.assertTrue(result["compliant"])

    def test_active_warning_missing_visual_fails(self):
        alarm = self._make_alarm(
            priority="warning", state="active",
            visual_distinct=False, auditory_distinct=True,
        )
        result = validate_alarm_entry(alarm)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("visual_distinct" in f for f in result["findings"]))

    def test_active_warning_missing_auditory_fails(self):
        alarm = self._make_alarm(
            priority="warning", state="active",
            visual_distinct=True, auditory_distinct=False,
        )
        result = validate_alarm_entry(alarm)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("auditory_distinct" in f for f in result["findings"]))

    def test_active_emergency_requires_both_cues(self):
        alarm = self._make_alarm(
            priority="emergency", state="active",
            visual_distinct=False, auditory_distinct=False,
        )
        result = validate_alarm_entry(alarm)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)

    def test_emergency_suppressed_fails(self):
        alarm = self._make_alarm(
            priority="emergency", state="suppressed",
            suppression_visible=True,
        )
        result = validate_alarm_entry(alarm)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("emergency" in f and "suppressed" in f for f in result["findings"]))

    def test_suppressed_caution_requires_suppression_visible(self):
        alarm = self._make_alarm(
            priority="caution", state="suppressed",
            suppression_visible=False,
        )
        result = validate_alarm_entry(alarm)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("suppression_visible" in f for f in result["findings"]))

    def test_suppressed_caution_with_visible_indicator_passes(self):
        alarm = self._make_alarm(
            priority="caution", state="suppressed",
            suppression_visible=True,
        )
        result = validate_alarm_entry(alarm)
        self.assertTrue(result["compliant"])

    def test_active_caution_no_auditory_required(self):
        alarm = self._make_alarm(
            priority="caution", state="active",
            visual_distinct=True, auditory_distinct=False,
        )
        result = validate_alarm_entry(alarm)
        self.assertTrue(result["compliant"])

    def test_invalid_priority_raises(self):
        with self.assertRaises(ValueError):
            validate_alarm_entry(self._make_alarm(priority="critical"))

    def test_invalid_state_raises(self):
        with self.assertRaises(ValueError):
            validate_alarm_entry(self._make_alarm(state="silenced"))

    def test_missing_required_key_raises(self):
        with self.assertRaises(ValueError):
            validate_alarm_entry({"alarm_id": "X", "priority": "caution"})

    def test_non_bool_visual_distinct_raises(self):
        with self.assertRaises(TypeError):
            validate_alarm_entry(self._make_alarm(visual_distinct="yes"))

    def test_non_bool_auditory_distinct_raises(self):
        with self.assertRaises(TypeError):
            validate_alarm_entry(self._make_alarm(auditory_distinct=1))

    def test_result_contains_required_keys(self):
        result = validate_alarm_entry(self._make_alarm())
        for key in ("alarm_id", "priority", "state", "compliant", "findings"):
            self.assertIn(key, result)

    def test_acknowledged_emergency_passes_without_auditory(self):
        alarm = self._make_alarm(
            priority="emergency", state="acknowledged",
            visual_distinct=True, auditory_distinct=False,
        )
        result = validate_alarm_entry(alarm)
        self.assertTrue(result["compliant"])


class TestAssessDisplay(unittest.TestCase):

    def _valid_format(self):
        return {
            "display_id": "DSP-001",
            "layout_type": "graphical",
            "font_size_pt": 12,
            "contrast_ratio": 5.0,
        }

    def _valid_density(self):
        return {
            "display_id": "DSP-001",
            "parameter_count": 8,
            "alarm_count_visible": 4,
        }

    def _valid_alarm(self):
        return {
            "alarm_id": "ALM-001",
            "priority": "advisory",
            "state": "normal",
            "visual_distinct": True,
            "auditory_distinct": False,
            "suppression_visible": False,
        }

    def test_all_valid_inputs_pass(self):
        result = assess_display(
            self._valid_format(), self._valid_density(), [self._valid_alarm()]
        )
        self.assertTrue(result["overall_compliant"])
        self.assertEqual(result["total_findings"], 0)

    def test_format_failure_propagates(self):
        bad_format = self._valid_format()
        bad_format["font_size_pt"] = 6
        result = assess_display(bad_format, self._valid_density(), [])
        self.assertFalse(result["overall_compliant"])
        self.assertGreater(result["total_findings"], 0)

    def test_density_failure_propagates(self):
        bad_density = self._valid_density()
        bad_density["parameter_count"] = 20
        result = assess_display(self._valid_format(), bad_density, [])
        self.assertFalse(result["overall_compliant"])
        self.assertGreater(result["total_findings"], 0)

    def test_alarm_failure_propagates(self):
        bad_alarm = {
            "alarm_id": "ALM-002",
            "priority": "emergency",
            "state": "active",
            "visual_distinct": False,
            "auditory_distinct": False,
            "suppression_visible": False,
        }
        result = assess_display(self._valid_format(), self._valid_density(), [bad_alarm])
        self.assertFalse(result["overall_compliant"])
        self.assertGreater(result["total_findings"], 0)

    def test_empty_alarm_list_passes(self):
        result = assess_display(self._valid_format(), self._valid_density(), [])
        self.assertTrue(result["overall_compliant"])

    def test_result_has_all_required_keys(self):
        result = assess_display(self._valid_format(), self._valid_density(), [])
        for key in ("format_result", "density_result", "alarm_results",
                    "overall_compliant", "total_findings"):
            self.assertIn(key, result)

    def test_non_list_alarms_raises(self):
        with self.assertRaises(TypeError):
            assess_display(self._valid_format(), self._valid_density(), "not-a-list")

    def test_non_dict_format_raises(self):
        with self.assertRaises(TypeError):
            assess_display("not-a-dict", self._valid_density(), [])

    def test_multiple_alarms_total_findings_summed(self):
        alarms = [
            {
                "alarm_id": "ALM-A",
                "priority": "warning",
                "state": "active",
                "visual_distinct": False,
                "auditory_distinct": False,
                "suppression_visible": False,
            },
            {
                "alarm_id": "ALM-B",
                "priority": "caution",
                "state": "suppressed",
                "visual_distinct": True,
                "auditory_distinct": False,
                "suppression_visible": False,
            },
        ]
        result = assess_display(self._valid_format(), self._valid_density(), alarms)
        self.assertFalse(result["overall_compliant"])
        self.assertGreaterEqual(result["total_findings"], 3)

    def test_density_custom_limits_via_spec(self):
        density = self._valid_density()
        density["max_parameters"] = 5
        density["parameter_count"] = 6
        result = assess_display(self._valid_format(), density, [])
        self.assertFalse(result["overall_compliant"])


if __name__ == "__main__":
    unittest.main()
