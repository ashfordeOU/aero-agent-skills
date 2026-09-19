"""Contract tests for the solder joint rework permission and grading logic."""

import unittest

from q7028_solder_joint_rework_logic import (
    DOUBLING_INTERVAL_C,
    REFERENCE_TIP_C,
    assess_solder_joint_rework,
    cumulative_exposure_units,
    grade_fillet_coverage,
    grade_lead_protrusion,
    grade_reworked_joint,
    grade_wetting,
    require_band,
    require_count,
    require_real,
    rework_cycle_state,
    thermal_exposure_units,
    tip_within_window,
)

WINDOW = (280.0, 340.0)


class InputValidationTests(unittest.TestCase):
    def test_require_real_accepts_int(self):
        self.assertAlmostEqual(require_real("x", 5), 5.0, places=9)

    def test_require_real_rejects_bool(self):
        with self.assertRaises(ValueError):
            require_real("x", False)

    def test_require_real_rejects_infinity(self):
        with self.assertRaises(ValueError):
            require_real("x", float("inf"))

    def test_require_count_rejects_bool(self):
        with self.assertRaises(ValueError):
            require_count("n", True)

    def test_require_band_rejects_inverted_pair(self):
        with self.assertRaises(ValueError):
            require_band("w", (340.0, 280.0))

    def test_require_band_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            require_band("w", (280.0,))


class CycleStateTests(unittest.TestCase):
    def test_fresh_joint_has_cycles_left(self):
        state = rework_cycle_state(0, 3)
        self.assertFalse(state["exhausted"])
        self.assertEqual(state["remaining_after_this_cycle"], 2)

    def test_last_cycle_is_flagged(self):
        self.assertTrue(rework_cycle_state(2, 3)["last_allowed"])

    def test_exhausted_joint(self):
        self.assertTrue(rework_cycle_state(3, 3)["exhausted"])

    def test_zero_maximum_rejected(self):
        with self.assertRaises(ValueError):
            rework_cycle_state(0, 0)


class TipWindowTests(unittest.TestCase):
    def test_setting_inside_the_window(self):
        self.assertTrue(tip_within_window(320.0, WINDOW)["within_window"])

    def test_setting_on_the_lower_edge_is_inside(self):
        self.assertTrue(tip_within_window(280.0, WINDOW)["within_window"])

    def test_setting_on_the_upper_edge_is_inside(self):
        self.assertTrue(tip_within_window(340.0, WINDOW)["within_window"])

    def test_cold_iron_is_below_the_window(self):
        result = tip_within_window(250.0, WINDOW)
        self.assertTrue(result["below_window"])
        self.assertFalse(result["within_window"])

    def test_hot_iron_is_above_the_window(self):
        self.assertTrue(tip_within_window(400.0, WINDOW)["above_window"])

    def test_zero_tip_temperature_rejected(self):
        with self.assertRaises(ValueError):
            tip_within_window(0.0, WINDOW)


class ExposureTests(unittest.TestCase):
    def test_dwell_at_the_reference_counts_once(self):
        self.assertAlmostEqual(
            thermal_exposure_units(4.0, REFERENCE_TIP_C), 4.0, places=9
        )

    def test_one_doubling_interval_above_counts_double(self):
        value = thermal_exposure_units(4.0, REFERENCE_TIP_C + DOUBLING_INTERVAL_C)
        self.assertAlmostEqual(value, 8.0, places=9)

    def test_one_doubling_interval_below_counts_half(self):
        value = thermal_exposure_units(4.0, REFERENCE_TIP_C - DOUBLING_INTERVAL_C)
        self.assertAlmostEqual(value, 2.0, places=9)

    def test_a_short_hot_touch_can_match_a_long_warm_one(self):
        hot = thermal_exposure_units(2.0, REFERENCE_TIP_C + DOUBLING_INTERVAL_C)
        warm = thermal_exposure_units(4.0, REFERENCE_TIP_C)
        self.assertAlmostEqual(hot, warm, places=9)

    def test_zero_dwell_is_zero_exposure(self):
        self.assertAlmostEqual(thermal_exposure_units(0.0, 340.0), 0.0, places=9)

    def test_negative_dwell_rejected(self):
        with self.assertRaises(ValueError):
            thermal_exposure_units(-1.0, 320.0)

    def test_cumulative_adds_the_events(self):
        total = cumulative_exposure_units(
            [(4.0, REFERENCE_TIP_C), (2.0, REFERENCE_TIP_C + DOUBLING_INTERVAL_C)]
        )
        self.assertAlmostEqual(total, 8.0, places=9)

    def test_malformed_event_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_exposure_units([(4.0,)])

    def test_non_sequence_events_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_exposure_units(4.0)


class JointGradingTests(unittest.TestCase):
    def test_low_angle_is_wetted(self):
        self.assertEqual(grade_wetting(20.0, 75.0)["outcome"], "wetted")

    def test_angle_just_under_the_limit_is_marginal(self):
        self.assertEqual(grade_wetting(73.0, 75.0)["outcome"], "marginal")

    def test_angle_exactly_on_the_limit_is_still_acceptable(self):
        result = grade_wetting(75.0, 75.0)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["outcome"], "marginal")

    def test_angle_over_the_limit_is_dewetted(self):
        result = grade_wetting(95.0, 75.0)
        self.assertEqual(result["outcome"], "dewetted")
        self.assertFalse(result["acceptable"])

    def test_angle_beyond_180_rejected(self):
        with self.assertRaises(ValueError):
            grade_wetting(200.0, 75.0)

    def test_full_fillet_is_acceptable(self):
        self.assertTrue(grade_fillet_coverage(0.9, 0.75)["acceptable"])

    def test_coverage_exactly_on_the_minimum_is_acceptable(self):
        result = grade_fillet_coverage(0.75, 0.75)
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(result["coverage_fraction"], 0.75, places=9)

    def test_short_fillet_is_rejected(self):
        self.assertEqual(grade_fillet_coverage(0.5, 0.75)["outcome"], "short-fillet")

    def test_coverage_above_one_rejected(self):
        with self.assertRaises(ValueError):
            grade_fillet_coverage(1.4, 0.75)

    def test_protrusion_in_band(self):
        self.assertTrue(grade_lead_protrusion(1.0, (0.5, 2.0))["acceptable"])

    def test_protrusion_under_band(self):
        self.assertEqual(grade_lead_protrusion(0.2, (0.5, 2.0))["outcome"],
                         "under-protrusion")

    def test_protrusion_over_band(self):
        self.assertEqual(grade_lead_protrusion(3.0, (0.5, 2.0))["outcome"],
                         "over-protrusion")

    def test_worst_characteristic_drives_the_verdict(self):
        result = grade_reworked_joint({
            "contact_angle_deg": 20.0,
            "max_contact_angle_deg": 75.0,
            "fillet_coverage": 0.4,
            "min_fillet_coverage": 0.75,
        })
        self.assertEqual(result["verdict"], "reject")
        self.assertEqual(result["driving"], ["fillet"])

    def test_two_bad_characteristics_are_both_named(self):
        result = grade_reworked_joint({
            "contact_angle_deg": 120.0,
            "max_contact_angle_deg": 75.0,
            "fillet_coverage": 0.4,
            "min_fillet_coverage": 0.75,
        })
        self.assertEqual(result["driving"], ["fillet", "wetting"])

    def test_sound_joint_is_accepted(self):
        result = grade_reworked_joint({
            "contact_angle_deg": 20.0,
            "max_contact_angle_deg": 75.0,
            "fillet_coverage": 0.95,
            "min_fillet_coverage": 0.75,
            "lead_protrusion_mm": 1.0,
            "protrusion_band_mm": (0.5, 2.0),
        })
        self.assertEqual(result["verdict"], "accept")
        self.assertEqual(result["driving"], [])

    def test_protrusion_reading_without_a_band_rejected(self):
        with self.assertRaises(ValueError):
            grade_reworked_joint({
                "contact_angle_deg": 20.0,
                "max_contact_angle_deg": 75.0,
                "fillet_coverage": 0.95,
                "min_fillet_coverage": 0.75,
                "lead_protrusion_mm": 1.0,
            })

    def test_missing_measurement_key_rejected(self):
        with self.assertRaises(ValueError):
            grade_reworked_joint({"contact_angle_deg": 20.0})


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "pad_condition": "sound",
            "cycles_used": 0,
            "max_cycles": 3,
            "tip_temperature_c": 320.0,
            "temperature_window_c": WINDOW,
            "dwell_s": 3.0,
            "prior_exposure_units": 2.0,
            "max_exposure_units": 40.0,
        }
        spec.update(overrides)
        return spec

    def test_clean_case_is_permitted(self):
        result = assess_solder_joint_rework(self._spec())
        self.assertEqual(result["permission"], "rework-permitted")
        self.assertEqual(result["findings"], [])

    def test_lifted_pad_refuses_the_rework(self):
        result = assess_solder_joint_rework(self._spec(pad_condition="lifted"))
        self.assertEqual(result["permission"], "rework-refused")

    def test_damaged_bonded_pad_needs_approval(self):
        result = assess_solder_joint_rework(self._spec(pad_condition="damaged-bonded"))
        self.assertEqual(result["permission"], "rework-with-approval")

    def test_exhausted_cycles_refuse_the_rework(self):
        result = assess_solder_joint_rework(self._spec(cycles_used=3))
        self.assertEqual(result["permission"], "rework-refused")

    def test_last_cycle_needs_approval(self):
        result = assess_solder_joint_rework(self._spec(cycles_used=2))
        self.assertEqual(result["permission"], "rework-with-approval")

    def test_iron_outside_the_window_refuses_the_rework(self):
        result = assess_solder_joint_rework(self._spec(tip_temperature_c=420.0))
        self.assertEqual(result["permission"], "rework-refused")

    def test_exposure_over_budget_refuses_the_rework(self):
        result = assess_solder_joint_rework(
            self._spec(prior_exposure_units=39.0, dwell_s=30.0)
        )
        self.assertTrue(result["over_exposure_budget"])
        self.assertEqual(result["permission"], "rework-refused")

    def test_cumulative_exposure_is_prior_plus_event(self):
        result = assess_solder_joint_rework(
            self._spec(tip_temperature_c=REFERENCE_TIP_C, dwell_s=4.0,
                       prior_exposure_units=2.0)
        )
        self.assertAlmostEqual(result["event_exposure_units"], 4.0, places=9)
        self.assertAlmostEqual(result["cumulative_exposure_units"], 6.0, places=9)

    def test_post_rework_rejection_is_reported(self):
        result = assess_solder_joint_rework(self._spec(post_rework={
            "contact_angle_deg": 110.0,
            "max_contact_angle_deg": 75.0,
            "fillet_coverage": 0.9,
            "min_fillet_coverage": 0.75,
        }))
        self.assertEqual(result["post_rework"]["verdict"], "reject")
        self.assertTrue(any("finished joint" in f for f in result["findings"]))

    def test_post_rework_absent_by_default(self):
        self.assertIsNone(assess_solder_joint_rework(self._spec())["post_rework"])

    def test_unknown_pad_condition_rejected(self):
        with self.assertRaises(ValueError):
            assess_solder_joint_rework(self._spec(pad_condition="slightly-tired"))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["dwell_s"]
        with self.assertRaises(ValueError):
            assess_solder_joint_rework(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_solder_joint_rework("sound")


if __name__ == "__main__":
    unittest.main()
