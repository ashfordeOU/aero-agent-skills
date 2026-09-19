"""Contract tests for the conformal coating repair and re-application logic."""

import unittest

from q7028_conformal_coating_repair_logic import (
    assess_conformal_coating_repair,
    assess_cure,
    assess_overlap,
    assess_removal_window,
    assess_thickness_readings,
    removal_margin_mm,
    require_band,
    require_real,
    required_cure_hours,
)

SCHEDULE = [(25.0, 72.0), (40.0, 24.0), (60.0, 6.0), (80.0, 2.0)]
BAND = (50.0, 200.0)


class InputValidationTests(unittest.TestCase):
    def test_require_real_returns_float(self):
        self.assertAlmostEqual(require_real("x", 7), 7.0, places=9)

    def test_require_real_rejects_text(self):
        with self.assertRaises(ValueError):
            require_real("x", "7")

    def test_require_real_rejects_bool(self):
        with self.assertRaises(ValueError):
            require_real("x", True)

    def test_require_real_rejects_nan(self):
        with self.assertRaises(ValueError):
            require_real("x", float("nan"))

    def test_require_band_rejects_inverted(self):
        with self.assertRaises(ValueError):
            require_band("b", (200.0, 50.0))

    def test_require_band_rejects_non_pair(self):
        with self.assertRaises(ValueError):
            require_band("b", 50.0)


class RemovalWindowTests(unittest.TestCase):
    def test_margin_is_per_side(self):
        self.assertAlmostEqual(removal_margin_mm(20.0, 10.0), 5.0, places=9)

    def test_removal_smaller_than_the_footprint_rejected(self):
        with self.assertRaises(ValueError):
            removal_margin_mm(8.0, 10.0)

    def test_removal_equal_to_the_footprint_gives_zero_margin(self):
        self.assertAlmostEqual(removal_margin_mm(10.0, 10.0), 0.0, places=9)

    def test_window_inside_both_limits_is_acceptable(self):
        result = assess_removal_window(10.0, 6.0, 14.0, 10.0, 1.0, 5.0)
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(result["margin_along_mm"], 2.0, places=9)

    def test_margin_below_the_minimum_is_flagged(self):
        result = assess_removal_window(10.0, 6.0, 10.4, 6.4, 1.0, 5.0)
        self.assertTrue(result["under_margin"])
        self.assertFalse(result["acceptable"])

    def test_margin_exactly_on_the_minimum_is_accepted(self):
        result = assess_removal_window(10.0, 6.0, 12.0, 8.0, 1.0, 5.0)
        self.assertAlmostEqual(result["margin_along_mm"], 1.0, places=9)
        self.assertFalse(result["under_margin"])

    def test_margin_above_the_maximum_is_flagged(self):
        result = assess_removal_window(10.0, 6.0, 30.0, 26.0, 1.0, 5.0)
        self.assertTrue(result["over_margin"])

    def test_the_short_side_drives_the_under_margin(self):
        result = assess_removal_window(10.0, 6.0, 18.0, 6.2, 1.0, 5.0)
        self.assertTrue(result["under_margin"])
        self.assertAlmostEqual(result["margin_across_mm"], 0.1, places=9)


class ThicknessTests(unittest.TestCase):
    def test_all_readings_in_band(self):
        result = assess_thickness_readings([80.0, 95.0, 110.0], BAND)
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(result["mean_um"], 95.0, places=9)

    def test_a_single_thin_point_fails_a_good_mean(self):
        result = assess_thickness_readings([20.0, 150.0, 150.0], BAND)
        self.assertEqual(result["thin_points"], [0])
        self.assertTrue(result["mean_in_band"])
        self.assertFalse(result["acceptable"])

    def test_a_thick_point_is_reported(self):
        result = assess_thickness_readings([100.0, 260.0], BAND)
        self.assertEqual(result["thick_points"], [1])

    def test_reading_exactly_on_the_lower_bound_is_accepted(self):
        result = assess_thickness_readings([50.0, 100.0], BAND)
        self.assertEqual(result["thin_points"], [])

    def test_reading_exactly_on_the_upper_bound_is_accepted(self):
        result = assess_thickness_readings([200.0, 100.0], BAND)
        self.assertEqual(result["thick_points"], [])

    def test_empty_reading_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_thickness_readings([], BAND)

    def test_non_numeric_reading_rejected(self):
        with self.assertRaises(ValueError):
            assess_thickness_readings([100.0, "thick"], BAND)


class OverlapTests(unittest.TestCase):
    def test_generous_lap_is_acceptable(self):
        self.assertTrue(assess_overlap(5.0, 2.0)["acceptable"])

    def test_lap_exactly_on_the_minimum_is_acceptable(self):
        self.assertTrue(assess_overlap(2.0, 2.0)["acceptable"])

    def test_short_lap_is_refused(self):
        self.assertFalse(assess_overlap(0.5, 2.0)["acceptable"])

    def test_zero_minimum_lap_rejected(self):
        with self.assertRaises(ValueError):
            assess_overlap(2.0, 0.0)


class CureTests(unittest.TestCase):
    def test_tabulated_temperature_returns_its_hours(self):
        self.assertAlmostEqual(required_cure_hours(SCHEDULE, 40.0), 24.0, places=9)

    def test_interpolation_between_points(self):
        self.assertAlmostEqual(required_cure_hours(SCHEDULE, 50.0), 15.0, places=9)

    def test_lower_edge_of_the_schedule(self):
        self.assertAlmostEqual(required_cure_hours(SCHEDULE, 25.0), 72.0, places=9)

    def test_upper_edge_of_the_schedule(self):
        self.assertAlmostEqual(required_cure_hours(SCHEDULE, 80.0), 2.0, places=9)

    def test_temperature_below_the_schedule_refused(self):
        with self.assertRaises(ValueError):
            required_cure_hours(SCHEDULE, 10.0)

    def test_temperature_above_the_schedule_refused(self):
        with self.assertRaises(ValueError):
            required_cure_hours(SCHEDULE, 120.0)

    def test_non_monotone_schedule_rejected(self):
        with self.assertRaises(ValueError):
            required_cure_hours([(40.0, 24.0), (40.0, 12.0)], 40.0)

    def test_single_point_schedule_rejected(self):
        with self.assertRaises(ValueError):
            required_cure_hours([(40.0, 24.0)], 40.0)

    def test_sufficient_cure_is_acceptable(self):
        result = assess_cure(SCHEDULE, 60.0, 8.0)
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(result["shortfall_hours"], 0.0, places=9)

    def test_cure_exactly_on_the_requirement_is_acceptable(self):
        result = assess_cure(SCHEDULE, 60.0, 6.0)
        self.assertTrue(result["acceptable"])

    def test_short_cure_reports_its_shortfall(self):
        result = assess_cure(SCHEDULE, 60.0, 4.0)
        self.assertFalse(result["acceptable"])
        self.assertAlmostEqual(result["shortfall_hours"], 2.0, places=9)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "footprint_length_mm": 10.0,
            "footprint_width_mm": 6.0,
            "removal_length_mm": 14.0,
            "removal_width_mm": 10.0,
            "min_margin_mm": 1.0,
            "max_margin_mm": 5.0,
            "thickness_readings_um": [90.0, 110.0, 130.0],
            "thickness_band_um": BAND,
            "overlap_mm": 4.0,
            "min_overlap_mm": 2.0,
            "cure_schedule": SCHEDULE,
            "cure_temperature_c": 60.0,
            "cure_held_hours": 8.0,
        }
        spec.update(overrides)
        return spec

    def test_clean_repair_is_accepted(self):
        result = assess_conformal_coating_repair(self._spec())
        self.assertEqual(result["verdict"], "accept")
        self.assertEqual(result["findings"], [])

    def test_thin_spot_sends_it_back_for_re_coat(self):
        result = assess_conformal_coating_repair(
            self._spec(thickness_readings_um=[20.0, 120.0, 130.0])
        )
        self.assertEqual(result["verdict"], "re-coat")

    def test_short_cure_sends_it_back_for_re_coat(self):
        result = assess_conformal_coating_repair(self._spec(cure_held_hours=1.0))
        self.assertEqual(result["verdict"], "re-coat")

    def test_short_lap_sends_it_back_for_re_coat(self):
        result = assess_conformal_coating_repair(self._spec(overlap_mm=0.2))
        self.assertEqual(result["verdict"], "re-coat")

    def test_under_margin_removal_sends_it_back_for_re_coat(self):
        result = assess_conformal_coating_repair(
            self._spec(removal_length_mm=10.4, removal_width_mm=6.4)
        )
        self.assertEqual(result["verdict"], "re-coat")

    def test_over_stripped_area_is_refused_not_re_coated(self):
        result = assess_conformal_coating_repair(
            self._spec(removal_length_mm=40.0, removal_width_mm=36.0)
        )
        self.assertEqual(result["verdict"], "refuse")

    def test_every_failing_characteristic_is_named(self):
        result = assess_conformal_coating_repair(
            self._spec(overlap_mm=0.2, cure_held_hours=1.0)
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["cure_schedule"]
        with self.assertRaises(ValueError):
            assess_conformal_coating_repair(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_conformal_coating_repair(["coating"])

    def test_cure_record_is_carried_in_the_result(self):
        result = assess_conformal_coating_repair(self._spec())
        self.assertAlmostEqual(result["cure"]["required_hours"], 6.0, places=9)


if __name__ == "__main__":
    unittest.main()
