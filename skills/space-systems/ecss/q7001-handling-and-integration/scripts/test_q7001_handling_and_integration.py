"""Contract test for the clean handling and integration leaf (stdlib unittest)."""

import unittest

from q7001_handling_and_integration_logic import (
    DEPOSITION_COEFFICIENT_PCT_PER_HOUR,
    accumulated_obscuration_pct,
    affordable_exposure_hours,
    area_concentration_per_m3,
    assess_handling_operation,
    assess_tooling,
    fallout_rate_pct_per_hour,
    orientation_factor,
    required_glove_pairs,
)


def tool(tid="TORQUE-DRIVER-7", **kw):
    record = {"id": tid, "cleaning_record": "CLN-4410", "lubricant": "space-grade-pfpe"}
    record.update(kw)
    return record


def operation(**kw):
    record = {
        "id": "FPA-TO-BENCH-MATE",
        "orientation": "vertical",
        "obscuration_allocation_pct": 0.5,
        "planned_exposure_hours": 6.0,
        "cover_open_hours": 6.0,
        "contacts": 40,
        "planned_glove_pairs": 2,
        "tools": [tool()],
        "approved_lubricants": ["space-grade-pfpe"],
        "required_area_class": 7,
    }
    record.update(kw)
    return record


def area(**kw):
    record = {"iso_class": 7, "threshold_um": 0.5}
    record.update(kw)
    return record


class TestOrientation(unittest.TestCase):
    def test_an_upward_face_collects_the_full_fallout(self):
        self.assertAlmostEqual(orientation_factor("facing-up"), 1.0, places=12)

    def test_turning_a_surface_down_cuts_the_fallout_sharply(self):
        self.assertLess(orientation_factor("facing-down"), orientation_factor("vertical"))

    def test_an_unknown_orientation_raises(self):
        with self.assertRaises(ValueError):
            orientation_factor("roughly-sideways")


class TestFalloutRate(unittest.TestCase):
    def test_the_rate_is_the_coefficient_times_concentration_times_facing(self):
        rate = fallout_rate_pct_per_hour(100000.0, "vertical")
        self.assertAlmostEqual(
            rate, DEPOSITION_COEFFICIENT_PCT_PER_HOUR * 100000.0 * 0.30, places=12
        )

    def test_a_dirtier_area_deposits_faster(self):
        clean = fallout_rate_pct_per_hour(1000.0, "facing-up")
        dirty = fallout_rate_pct_per_hour(100000.0, "facing-up")
        self.assertLess(clean, dirty)

    def test_still_air_with_no_particles_deposits_nothing(self):
        self.assertAlmostEqual(
            fallout_rate_pct_per_hour(0.0, "facing-up"), 0.0, places=12
        )

    def test_a_negative_concentration_raises(self):
        with self.assertRaises(ValueError):
            fallout_rate_pct_per_hour(-10.0, "facing-up")

    def test_accumulation_is_linear_in_the_exposure(self):
        rate = fallout_rate_pct_per_hour(100000.0, "vertical")
        self.assertAlmostEqual(
            accumulated_obscuration_pct(rate, 4.0),
            4.0 * accumulated_obscuration_pct(rate, 1.0),
            places=12,
        )

    def test_a_class_outside_the_scheme_raises(self):
        with self.assertRaises(ValueError):
            area_concentration_per_m3(11)


class TestAffordableExposure(unittest.TestCase):
    def test_the_affordable_exposure_is_the_allocation_over_the_rate(self):
        self.assertAlmostEqual(affordable_exposure_hours(0.5, 0.01), 50.0, places=9)

    def test_a_larger_allocation_buys_more_exposure(self):
        self.assertLess(
            affordable_exposure_hours(0.2, 0.01), affordable_exposure_hours(0.5, 0.01)
        )

    def test_a_perfectly_still_area_buys_unbounded_exposure(self):
        self.assertEqual(affordable_exposure_hours(0.5, 0.0), float("inf"))

    def test_a_zero_allocation_raises(self):
        with self.assertRaises(ValueError):
            affordable_exposure_hours(0.0, 0.01)


class TestGlovePairs(unittest.TestCase):
    def test_a_short_task_needs_one_pair(self):
        self.assertEqual(required_glove_pairs(10, 25), 1)

    def test_a_contact_count_over_the_pair_life_needs_another_pair(self):
        self.assertEqual(required_glove_pairs(40, 25), 2)

    def test_a_contact_count_exactly_on_the_pair_life_needs_one_pair(self):
        self.assertEqual(required_glove_pairs(25, 25), 1)

    def test_a_task_with_no_contacts_still_needs_a_pair(self):
        self.assertEqual(required_glove_pairs(0, 25), 1)

    def test_each_non_clean_contact_ends_a_pair(self):
        self.assertEqual(required_glove_pairs(40, 25, non_clean_contacts=2), 4)

    def test_more_spoiled_contacts_than_contacts_raises(self):
        with self.assertRaises(ValueError):
            required_glove_pairs(3, 25, non_clean_contacts=5)

    def test_a_zero_pair_life_raises(self):
        with self.assertRaises(ValueError):
            required_glove_pairs(40, 0)


class TestTooling(unittest.TestCase):
    def test_recorded_tooling_with_approved_lubricant_is_clean(self):
        row = assess_tooling([tool()], ["space-grade-pfpe"])
        self.assertEqual(row["tools_without_a_cleaning_record"], [])
        self.assertEqual(row["unapproved_lubricants"], [])

    def test_a_tool_with_no_cleaning_record_is_named(self):
        row = assess_tooling([tool(cleaning_record=None)], ["space-grade-pfpe"])
        self.assertEqual(row["tools_without_a_cleaning_record"], ["TORQUE-DRIVER-7"])

    def test_an_unapproved_lubricant_is_named_with_its_tool(self):
        row = assess_tooling([tool(lubricant="workshop-grease")], ["space-grade-pfpe"])
        self.assertEqual(
            row["unapproved_lubricants"],
            [{"tool_id": "TORQUE-DRIVER-7", "lubricant": "workshop-grease"}],
        )

    def test_a_dry_tool_needs_no_lubricant_approval(self):
        row = assess_tooling([tool(lubricant=None)], [])
        self.assertEqual(row["unapproved_lubricants"], [])

    def test_duplicate_tool_ids_raise(self):
        with self.assertRaises(ValueError):
            assess_tooling([tool(), tool()], ["space-grade-pfpe"])


class TestHandlingOperation(unittest.TestCase):
    def test_a_sound_handling_plan_is_clear(self):
        report = assess_handling_operation(operation(), area())
        self.assertTrue(report["clear"])
        self.assertEqual(report["verdict"], "handling-plan-acceptable")

    def test_the_accumulated_obscuration_sits_inside_the_allocation(self):
        report = assess_handling_operation(operation(), area())
        self.assertLess(report["allocation_utilization_fraction"], 1.0)

    def test_an_over_long_exposure_is_reported(self):
        report = assess_handling_operation(
            operation(planned_exposure_hours=400.0, cover_open_hours=400.0),
            area(),
        )
        self.assertIn(
            "uncovered-time-longer-than-the-fallout-allocation-pays-for",
            report["findings"],
        )

    def test_an_aperture_open_beyond_the_task_is_reported(self):
        report = assess_handling_operation(
            operation(planned_exposure_hours=1.0, cover_open_hours=6.0), area()
        )
        self.assertIn(
            "aperture-left-open-outside-the-task-that-needed-it", report["findings"]
        )

    def test_an_upward_facing_uncovered_surface_is_reported(self):
        report = assess_handling_operation(operation(orientation="facing-up"), area())
        self.assertIn(
            "sensitive-surface-left-facing-up-while-uncovered", report["findings"]
        )

    def test_turning_the_surface_down_cuts_the_accumulation(self):
        up = assess_handling_operation(operation(orientation="facing-up"), area())
        down = assess_handling_operation(operation(orientation="facing-down"), area())
        self.assertLess(
            down["accumulated_obscuration_pct"], up["accumulated_obscuration_pct"]
        )

    def test_too_few_glove_pairs_is_reported(self):
        report = assess_handling_operation(operation(planned_glove_pairs=1), area())
        self.assertIn(
            "fewer-glove-pairs-planned-than-the-contact-count-needs",
            report["findings"],
        )
        self.assertEqual(report["glove_pairs_needed"], 2)

    def test_an_unrecorded_tool_is_reported(self):
        report = assess_handling_operation(
            operation(tools=[tool(cleaning_record=None)]), area()
        )
        self.assertIn("tool-used-with-no-cleaning-record", report["findings"])

    def test_an_unapproved_lubricant_is_reported(self):
        report = assess_handling_operation(
            operation(tools=[tool(lubricant="workshop-grease")]), area()
        )
        self.assertIn(
            "unapproved-lubricant-on-a-tool-near-a-sensitive-surface",
            report["findings"],
        )

    def test_a_dirtier_area_than_the_operation_needs_is_reported(self):
        report = assess_handling_operation(operation(), area(iso_class=8))
        self.assertIn(
            "handling-in-an-area-dirtier-than-the-operation-needs", report["findings"]
        )

    def test_a_cleaner_area_than_needed_is_accepted(self):
        report = assess_handling_operation(operation(), area(iso_class=6))
        self.assertTrue(report["clear"])

    def test_a_directly_declared_concentration_overrides_the_class(self):
        report = assess_handling_operation(
            operation(required_area_class=None),
            {"particle_concentration_per_m3": 100000.0},
        )
        self.assertAlmostEqual(report["concentration_per_m3"], 100000.0, places=6)

    def test_a_negative_exposure_raises(self):
        with self.assertRaises(ValueError):
            assess_handling_operation(
                operation(planned_exposure_hours=-1.0, cover_open_hours=0.0), area()
            )

    def test_a_non_mapping_area_raises(self):
        with self.assertRaises(ValueError):
            assess_handling_operation(operation(), "the integration hall")

    def test_a_non_integer_area_class_raises(self):
        with self.assertRaises(ValueError):
            assess_handling_operation(operation(), area(iso_class=7.5))


if __name__ == "__main__":
    unittest.main()
