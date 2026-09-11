#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C §4.6.4 hardware ergonomics
requirements check.

Exercises scripts/e1011_hw_ergonomics_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 -- an item type is
assigned to exactly one hardware ergonomics family and an unrecognized
type raises; a control's operating force is checked against its type
limit and an exceedance is flagged; a display's character visual angle
must lie within the 20-80 arcmin band and its contrast ratio must meet
the 3:1 minimum; a handle's payload must not exceed the grip-mode
limit and its grip clearance must meet the 38 mm minimum; a
maintenance access opening must meet the task-type minimum diameter;
and the aggregated review is conformant only when the findings list is
empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_hw_ergonomics_logic as hw  # noqa: E402


class CategorizeHardwareItemTest(unittest.TestCase):
    def test_control_family_accepted(self):
        self.assertEqual(hw.categorize_hardware_item("control"), "control")

    def test_display_family_accepted(self):
        self.assertEqual(hw.categorize_hardware_item("display"), "display")

    def test_handle_family_accepted(self):
        self.assertEqual(hw.categorize_hardware_item("handle"), "handle")

    def test_access_point_family_accepted(self):
        self.assertEqual(
            hw.categorize_hardware_item("access_point"), "access_point"
        )

    def test_unknown_item_type_raises(self):
        with self.assertRaises(ValueError):
            hw.categorize_hardware_item("actuator_valve")


class ControlForceLimitTest(unittest.TestCase):
    def test_push_button_within_limit_no_violation(self):
        self.assertEqual(
            hw.check_control_force_limit("push_button", 20.0), []
        )

    def test_push_button_at_limit_no_violation(self):
        self.assertEqual(
            hw.check_control_force_limit("push_button", 22.2), []
        )

    def test_push_button_exceeds_limit_flagged(self):
        violations = hw.check_control_force_limit("push_button", 30.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "control_force_limit_exceeded")
        self.assertEqual(violations[0]["control_type"], "push_button")
        self.assertAlmostEqual(violations[0]["operating_force"], 30.0)
        self.assertAlmostEqual(violations[0]["limit"], 22.2)

    def test_rotary_knob_within_torque_limit_no_violation(self):
        self.assertEqual(
            hw.check_control_force_limit("rotary_knob", 0.5), []
        )

    def test_rotary_knob_exceeds_torque_limit_flagged(self):
        violations = hw.check_control_force_limit("rotary_knob", 1.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "control_force_limit_exceeded")

    def test_keyboard_key_within_limit_no_violation(self):
        self.assertEqual(
            hw.check_control_force_limit("keyboard_key", 2.5), []
        )

    def test_negative_force_raises(self):
        with self.assertRaises(ValueError):
            hw.check_control_force_limit("push_button", -1.0)

    def test_unknown_control_type_raises(self):
        with self.assertRaises(ValueError):
            hw.check_control_force_limit("dial_gauge", 5.0)


class DisplayVisualAngleTest(unittest.TestCase):
    def test_angle_within_band_no_violation(self):
        self.assertEqual(hw.check_display_visual_angle(40.0), [])

    def test_angle_at_minimum_no_violation(self):
        self.assertEqual(
            hw.check_display_visual_angle(
                hw.DISPLAY_MIN_CHAR_VISUAL_ANGLE_ARCMIN
            ),
            [],
        )

    def test_angle_at_maximum_no_violation(self):
        self.assertEqual(
            hw.check_display_visual_angle(
                hw.DISPLAY_MAX_CHAR_VISUAL_ANGLE_ARCMIN
            ),
            [],
        )

    def test_angle_below_minimum_flagged(self):
        violations = hw.check_display_visual_angle(15.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(
            violations[0]["issue"],
            "display_char_visual_angle_below_minimum",
        )
        self.assertAlmostEqual(violations[0]["value_arcmin"], 15.0)

    def test_angle_above_maximum_flagged(self):
        violations = hw.check_display_visual_angle(90.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(
            violations[0]["issue"],
            "display_char_visual_angle_above_maximum",
        )
        self.assertAlmostEqual(violations[0]["value_arcmin"], 90.0)

    def test_negative_angle_raises(self):
        with self.assertRaises(ValueError):
            hw.check_display_visual_angle(-5.0)


class DisplayContrastTest(unittest.TestCase):
    def test_contrast_above_minimum_no_violation(self):
        self.assertEqual(hw.check_display_contrast(5.0), [])

    def test_contrast_at_minimum_no_violation(self):
        self.assertEqual(
            hw.check_display_contrast(hw.DISPLAY_MIN_CONTRAST_RATIO), []
        )

    def test_contrast_below_minimum_flagged(self):
        violations = hw.check_display_contrast(2.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "display_contrast_below_minimum")
        self.assertAlmostEqual(violations[0]["value"], 2.0)

    def test_negative_contrast_raises(self):
        with self.assertRaises(ValueError):
            hw.check_display_contrast(-1.0)


class HandleRequirementsTest(unittest.TestCase):
    def test_one_hand_within_payload_limit_no_violation(self):
        self.assertEqual(
            hw.check_handle_requirements(100.0, "one_hand", 50.0), []
        )

    def test_one_hand_exceeds_payload_limit_flagged(self):
        violations = hw.check_handle_requirements(120.0, "one_hand", 50.0)
        issues = [v["issue"] for v in violations]
        self.assertIn("handle_payload_limit_exceeded", issues)

    def test_two_hand_within_payload_limit_no_violation(self):
        self.assertEqual(
            hw.check_handle_requirements(200.0, "two_hand", 50.0), []
        )

    def test_two_hand_exceeds_payload_limit_flagged(self):
        violations = hw.check_handle_requirements(250.0, "two_hand", 50.0)
        issues = [v["issue"] for v in violations]
        self.assertIn("handle_payload_limit_exceeded", issues)

    def test_grip_clearance_below_minimum_flagged(self):
        violations = hw.check_handle_requirements(50.0, "one_hand", 30.0)
        issues = [v["issue"] for v in violations]
        self.assertIn("handle_grip_clearance_below_minimum", issues)
        found = next(v for v in violations if v["issue"] == "handle_grip_clearance_below_minimum")
        self.assertAlmostEqual(found["minimum_mm"], hw.HANDLE_MIN_GRIP_CLEARANCE_MM)

    def test_grip_clearance_at_minimum_no_violation(self):
        self.assertEqual(
            hw.check_handle_requirements(50.0, "one_hand", 38.0), []
        )

    def test_both_payload_and_clearance_violations_returned(self):
        violations = hw.check_handle_requirements(200.0, "one_hand", 20.0)
        issues = [v["issue"] for v in violations]
        self.assertIn("handle_payload_limit_exceeded", issues)
        self.assertIn("handle_grip_clearance_below_minimum", issues)

    def test_unknown_grip_mode_raises(self):
        with self.assertRaises(ValueError):
            hw.check_handle_requirements(50.0, "three_hand", 50.0)

    def test_negative_payload_raises(self):
        with self.assertRaises(ValueError):
            hw.check_handle_requirements(-1.0, "one_hand", 50.0)

    def test_negative_clearance_raises(self):
        with self.assertRaises(ValueError):
            hw.check_handle_requirements(50.0, "one_hand", -1.0)


class MaintenanceAccessTest(unittest.TestCase):
    def test_one_hand_access_sufficient_no_violation(self):
        self.assertEqual(
            hw.check_maintenance_access("one_hand", 110.0), []
        )

    def test_one_hand_access_at_minimum_no_violation(self):
        self.assertEqual(
            hw.check_maintenance_access("one_hand", 102.0), []
        )

    def test_one_hand_access_below_minimum_flagged(self):
        violations = hw.check_maintenance_access("one_hand", 90.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(
            violations[0]["issue"],
            "maintenance_access_opening_below_minimum",
        )
        self.assertAlmostEqual(violations[0]["minimum_mm"], 102.0)

    def test_finger_access_sufficient_no_violation(self):
        self.assertEqual(
            hw.check_maintenance_access("finger", 40.0), []
        )

    def test_head_and_shoulders_access_below_minimum_flagged(self):
        violations = hw.check_maintenance_access("head_and_shoulders", 300.0)
        self.assertEqual(len(violations), 1)
        self.assertAlmostEqual(violations[0]["minimum_mm"], 455.0)

    def test_unknown_task_type_raises(self):
        with self.assertRaises(ValueError):
            hw.check_maintenance_access("elbow_deep", 200.0)

    def test_negative_diameter_raises(self):
        with self.assertRaises(ValueError):
            hw.check_maintenance_access("one_hand", -5.0)


class HwErgonomicsReviewTest(unittest.TestCase):
    def test_compliant_control_review(self):
        item = {
            "item_id": "btn-001",
            "item_type": "control",
            "control_type": "push_button",
            "operating_force": 10.0,
        }
        review = hw.hw_ergonomics_review(item)
        self.assertEqual(review["item_id"], "btn-001")
        self.assertEqual(review["findings"], [])
        self.assertTrue(hw.is_hw_ergonomics_compliant(review))

    def test_noncompliant_control_review(self):
        item = {
            "item_id": "btn-002",
            "item_type": "control",
            "control_type": "push_button",
            "operating_force": 50.0,
        }
        review = hw.hw_ergonomics_review(item)
        self.assertTrue(len(review["findings"]) > 0)
        self.assertFalse(hw.is_hw_ergonomics_compliant(review))

    def test_compliant_display_review(self):
        item = {
            "item_id": "disp-001",
            "item_type": "display",
            "char_visual_angle_arcmin": 35.0,
            "contrast_ratio": 5.0,
        }
        review = hw.hw_ergonomics_review(item)
        self.assertEqual(review["findings"], [])
        self.assertTrue(hw.is_hw_ergonomics_compliant(review))

    def test_display_two_violations_both_reported(self):
        item = {
            "item_id": "disp-002",
            "item_type": "display",
            "char_visual_angle_arcmin": 10.0,
            "contrast_ratio": 1.5,
        }
        review = hw.hw_ergonomics_review(item)
        issues = [f["issue"] for f in review["findings"]]
        self.assertIn("display_char_visual_angle_below_minimum", issues)
        self.assertIn("display_contrast_below_minimum", issues)
        self.assertFalse(hw.is_hw_ergonomics_compliant(review))

    def test_compliant_handle_review(self):
        item = {
            "item_id": "hdl-001",
            "item_type": "handle",
            "payload_n": 80.0,
            "grip_mode": "one_hand",
            "grip_clearance_mm": 45.0,
        }
        review = hw.hw_ergonomics_review(item)
        self.assertEqual(review["findings"], [])
        self.assertTrue(hw.is_hw_ergonomics_compliant(review))

    def test_compliant_access_point_review(self):
        item = {
            "item_id": "acc-001",
            "item_type": "access_point",
            "task_type": "two_hand",
            "opening_diameter_mm": 160.0,
        }
        review = hw.hw_ergonomics_review(item)
        self.assertEqual(review["findings"], [])
        self.assertTrue(hw.is_hw_ergonomics_compliant(review))

    def test_noncompliant_access_point_review(self):
        item = {
            "item_id": "acc-002",
            "item_type": "access_point",
            "task_type": "two_hand",
            "opening_diameter_mm": 100.0,
        }
        review = hw.hw_ergonomics_review(item)
        self.assertFalse(hw.is_hw_ergonomics_compliant(review))

    def test_unknown_item_type_raises_in_review(self):
        item = {
            "item_id": "unk-001",
            "item_type": "sensor_head",
            "operating_force": 5.0,
        }
        with self.assertRaises(ValueError):
            hw.hw_ergonomics_review(item)


if __name__ == "__main__":
    unittest.main(verbosity=2)
