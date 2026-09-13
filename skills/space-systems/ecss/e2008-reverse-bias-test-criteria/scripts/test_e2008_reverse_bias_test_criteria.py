"""Contract tests for the clause 6.4.3.14.3 reverse-bias setting criteria logic."""

import unittest

from e2008_reverse_bias_test_criteria_logic import (
    COMPARISONS,
    CRITERIA_NOT_SPECIFIED,
    REQUIRED_SETTINGS,
    SETTINGS_AS_DRAWN,
    SETTINGS_NOT_RECORDED,
    SETTINGS_OFF_DRAWING,
    SETTING_RULES,
    assess_reverse_bias_criteria,
    assess_setting,
    assess_settings,
    missing_settings,
    normalize_setting,
    setting_is_met,
    validate_drawing,
    validate_drawn_setting,
)

# A drawing that holds the assembly at 25 C within two degrees, for at least
# sixty seconds, with the supply allowed no more than 1.5 A into it.
DRAWING = {
    "temperature_c": {"value": 25.0, "tolerance": 2.0},
    "hold_time_s": {"value": 60.0, "tolerance": 1.0},
    "current_limit_a": {"value": 1.5, "tolerance": 0.05},
}

APPLIED = {"temperature_c": 24.4, "hold_time_s": 62.0, "current_limit_a": 1.45}


def _spec(**overrides):
    spec = {
        "drawing": {k: dict(v) for k, v in DRAWING.items()},
        "applied": dict(APPLIED),
    }
    spec.update(overrides)
    return spec


class SettingNameTests(unittest.TestCase):
    def test_case_and_space_are_absorbed(self):
        self.assertEqual(normalize_setting("  Hold_Time_S "), "hold_time_s")

    def test_unknown_setting_rejected(self):
        with self.assertRaises(ValueError):
            normalize_setting("illumination_w_m2")

    def test_non_string_setting_rejected(self):
        with self.assertRaises(ValueError):
            normalize_setting(3)

    def test_three_settings_are_required(self):
        self.assertEqual(len(REQUIRED_SETTINGS), 3)

    def test_every_rule_names_a_recognized_comparison(self):
        for comparison in SETTING_RULES.values():
            self.assertIn(comparison, COMPARISONS)


class DrawnSettingTests(unittest.TestCase):
    def test_valid_entry_carries_its_comparison(self):
        record = validate_drawn_setting("current_limit_a", DRAWING["current_limit_a"])
        self.assertEqual(record["comparison"], "at-most")

    def test_temperature_may_be_negative(self):
        record = validate_drawn_setting(
            "temperature_c", {"value": -40.0, "tolerance": 3.0}
        )
        self.assertAlmostEqual(record["value"], -40.0, places=9)

    def test_hold_time_may_not_be_zero(self):
        with self.assertRaises(ValueError):
            validate_drawn_setting("hold_time_s", {"value": 0.0, "tolerance": 1.0})

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawn_setting(
                "current_limit_a", {"value": 1.5, "tolerance": -0.1}
            )

    def test_missing_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawn_setting("hold_time_s", {"value": 60.0})

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawn_setting("hold_time_s", 60.0)

    def test_drawing_returns_every_setting(self):
        validated = validate_drawing(DRAWING)
        self.assertEqual(sorted(validated), sorted(REQUIRED_SETTINGS))

    def test_setting_drawn_twice_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing({
                "hold_time_s": {"value": 60.0, "tolerance": 1.0},
                " HOLD_TIME_S ": {"value": 90.0, "tolerance": 1.0},
            })

    def test_incomplete_drawing_is_reported(self):
        partial = {k: dict(v) for k, v in DRAWING.items()}
        del partial["temperature_c"]
        self.assertEqual(missing_settings(partial), ("temperature_c",))

    def test_complete_drawing_misses_nothing(self):
        self.assertEqual(missing_settings(DRAWING), ())


class DirectionTests(unittest.TestCase):
    def setUp(self):
        self.drawn = validate_drawing(DRAWING)

    def test_temperature_below_the_band_fails(self):
        self.assertFalse(setting_is_met(22.0, self.drawn["temperature_c"]))

    def test_temperature_above_the_band_fails(self):
        self.assertFalse(setting_is_met(28.0, self.drawn["temperature_c"]))

    def test_temperature_on_the_band_edge_is_met(self):
        self.assertTrue(setting_is_met(27.0, self.drawn["temperature_c"]))

    def test_longer_hold_than_drawn_is_met(self):
        self.assertTrue(setting_is_met(600.0, self.drawn["hold_time_s"]))

    def test_short_hold_fails(self):
        self.assertFalse(setting_is_met(40.0, self.drawn["hold_time_s"]))

    def test_hold_on_the_floor_is_met(self):
        self.assertTrue(setting_is_met(59.0, self.drawn["hold_time_s"]))

    def test_lower_current_limit_than_drawn_is_met(self):
        self.assertTrue(setting_is_met(0.5, self.drawn["current_limit_a"]))

    def test_higher_current_limit_fails(self):
        self.assertFalse(setting_is_met(2.0, self.drawn["current_limit_a"]))

    def test_current_limit_on_the_ceiling_is_met(self):
        self.assertTrue(setting_is_met(1.55, self.drawn["current_limit_a"]))

    def test_unrecognized_comparison_rejected(self):
        drawn = dict(self.drawn["hold_time_s"])
        drawn["comparison"] = "roughly-equal"
        with self.assertRaises(ValueError):
            setting_is_met(60.0, drawn)


class SettingAssessmentTests(unittest.TestCase):
    def test_record_carries_the_signed_deviation(self):
        record = assess_setting("temperature_c", 24.4, DRAWING)
        self.assertAlmostEqual(record["deviation"], -0.6, places=9)
        self.assertTrue(record["met"])

    def test_setting_absent_from_the_drawing_rejected(self):
        partial = {k: dict(v) for k, v in DRAWING.items()}
        del partial["hold_time_s"]
        with self.assertRaises(ValueError):
            assess_setting("hold_time_s", 60.0, partial)

    def test_negative_applied_hold_time_rejected(self):
        with self.assertRaises(ValueError):
            assess_setting("hold_time_s", -5.0, DRAWING)

    def test_records_come_back_in_setting_order(self):
        records = assess_settings(APPLIED, DRAWING)
        self.assertEqual([r["setting"] for r in records], list(REQUIRED_SETTINGS))

    def test_applied_setting_the_drawing_lacks_rejected(self):
        partial = {k: dict(v) for k, v in DRAWING.items()}
        del partial["current_limit_a"]
        with self.assertRaises(ValueError):
            assess_settings(APPLIED, partial)

    def test_non_mapping_applied_rejected(self):
        with self.assertRaises(ValueError):
            assess_settings([24.4], DRAWING)


class CriteriaOutcomeTests(unittest.TestCase):
    def test_run_as_drawn_passes(self):
        result = assess_reverse_bias_criteria(_spec())
        self.assertEqual(result["outcome"], SETTINGS_AS_DRAWN)
        self.assertTrue(result["passed"])
        self.assertEqual(result["findings"], [])

    def test_hot_hold_is_off_drawing(self):
        result = assess_reverse_bias_criteria(
            _spec(applied=dict(APPLIED, temperature_c=40.0))
        )
        self.assertEqual(result["outcome"], SETTINGS_OFF_DRAWING)
        self.assertEqual(result["breached_settings"], ("temperature_c",))

    def test_raised_current_limit_is_off_drawing(self):
        result = assess_reverse_bias_criteria(
            _spec(applied=dict(APPLIED, current_limit_a=3.0))
        )
        self.assertEqual(result["breached_settings"], ("current_limit_a",))

    def test_undrawn_setting_leaves_no_criterion(self):
        drawing = {k: dict(v) for k, v in DRAWING.items()}
        del drawing["hold_time_s"]
        applied = dict(APPLIED)
        del applied["hold_time_s"]
        result = assess_reverse_bias_criteria(
            _spec(drawing=drawing, applied=applied)
        )
        self.assertEqual(result["outcome"], CRITERIA_NOT_SPECIFIED)
        self.assertEqual(result["undrawn_settings"], ("hold_time_s",))

    def test_unrecorded_setting_is_its_own_outcome(self):
        applied = dict(APPLIED)
        del applied["current_limit_a"]
        result = assess_reverse_bias_criteria(_spec(applied=applied))
        self.assertEqual(result["outcome"], SETTINGS_NOT_RECORDED)
        self.assertEqual(result["unrecorded_settings"], ("current_limit_a",))

    def test_a_breach_outranks_an_undrawn_setting(self):
        drawing = {k: dict(v) for k, v in DRAWING.items()}
        del drawing["hold_time_s"]
        applied = dict(APPLIED, temperature_c=40.0)
        del applied["hold_time_s"]
        result = assess_reverse_bias_criteria(
            _spec(drawing=drawing, applied=applied)
        )
        self.assertEqual(result["outcome"], SETTINGS_OFF_DRAWING)
        self.assertEqual(len(result["findings"]), 2)

    def test_reaching_the_limit_fails_an_otherwise_clean_run(self):
        result = assess_reverse_bias_criteria(_spec(current_limit_reached=True))
        self.assertEqual(result["outcome"], SETTINGS_OFF_DRAWING)
        self.assertFalse(result["passed"])

    def test_non_boolean_limit_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_bias_criteria(_spec(current_limit_reached="yes"))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["applied"]
        with self.assertRaises(ValueError):
            assess_reverse_bias_criteria(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_bias_criteria(["drawing"])

    def test_empty_drawing_specifies_nothing(self):
        result = assess_reverse_bias_criteria(_spec(drawing={}, applied={}))
        self.assertEqual(result["outcome"], CRITERIA_NOT_SPECIFIED)
        self.assertEqual(len(result["findings"]), 3)


if __name__ == "__main__":
    unittest.main()
