"""Contract test for the clean-area class requirement leaf (stdlib unittest)."""

import unittest

from q7001_cleanroom_class_requirements_logic import (
    MAX_CLASS,
    MAX_THRESHOLD_UM,
    MIN_CLASS,
    MIN_THRESHOLD_UM,
    STATE_AT_REST,
    STATE_OPERATIONAL,
    assess_facility_plan,
    assess_operation,
    class_ceiling_per_m3,
    required_class,
    round_to_significant,
    validate_class_number,
    validate_operation,
    validate_threshold_um,
)


def operation(oid="OPTICS-BONDING", **kw):
    record = {
        "id": oid,
        "threshold_um": 0.5,
        "tolerable_per_m3": 4000.0,
        "assigned_class": 5,
        "demonstrated_state": STATE_OPERATIONAL,
    }
    record.update(kw)
    return record


class TestThresholdAndClassValidation(unittest.TestCase):
    def test_a_half_micron_threshold_is_accepted(self):
        self.assertAlmostEqual(validate_threshold_um(0.5), 0.5, places=12)

    def test_the_lower_bound_of_the_range_is_accepted(self):
        self.assertAlmostEqual(
            validate_threshold_um(MIN_THRESHOLD_UM), MIN_THRESHOLD_UM, places=12
        )

    def test_the_upper_bound_of_the_range_is_accepted(self):
        self.assertAlmostEqual(
            validate_threshold_um(MAX_THRESHOLD_UM), MAX_THRESHOLD_UM, places=12
        )

    def test_a_threshold_below_the_range_raises(self):
        with self.assertRaises(ValueError):
            validate_threshold_um(0.02)

    def test_a_threshold_above_the_range_raises(self):
        with self.assertRaises(ValueError):
            validate_threshold_um(25.0)

    def test_a_non_numeric_threshold_raises(self):
        with self.assertRaises(ValueError):
            validate_threshold_um("half a micron")

    def test_a_class_outside_the_scheme_raises(self):
        with self.assertRaises(ValueError):
            validate_class_number(MAX_CLASS + 1)

    def test_a_class_below_the_scheme_raises(self):
        with self.assertRaises(ValueError):
            validate_class_number(MIN_CLASS - 1)


class TestCeiling(unittest.TestCase):
    def test_the_ceiling_at_the_reference_size_is_a_power_of_ten(self):
        self.assertAlmostEqual(class_ceiling_per_m3(5, 0.1), 1.0e5, places=3)

    def test_a_dirtier_class_has_a_ten_times_larger_ceiling(self):
        five = class_ceiling_per_m3(5, 0.5)
        six = class_ceiling_per_m3(6, 0.5)
        self.assertAlmostEqual(six, 10.0 * five, places=6)

    def test_a_larger_threshold_gives_a_smaller_ceiling(self):
        self.assertLess(
            class_ceiling_per_m3(7, 5.0), class_ceiling_per_m3(7, 0.5)
        )

    def test_the_half_micron_ceiling_matches_the_reporting_precision(self):
        self.assertAlmostEqual(
            round_to_significant(class_ceiling_per_m3(5, 0.5)), 3520.0, places=3
        )

    def test_rounding_keeps_the_leading_digits(self):
        self.assertAlmostEqual(round_to_significant(123456.0), 123000.0, places=3)

    def test_rounding_zero_gives_zero(self):
        self.assertAlmostEqual(round_to_significant(0.0), 0.0, places=12)

    def test_a_non_integer_digit_count_raises(self):
        with self.assertRaises(ValueError):
            round_to_significant(1234.0, 0)


class TestRequiredClass(unittest.TestCase):
    def test_a_tolerance_just_over_a_ceiling_picks_that_class(self):
        self.assertEqual(required_class(4000.0, 0.5), 5)

    def test_a_tolerance_exactly_on_a_ceiling_still_picks_that_class(self):
        ceiling = class_ceiling_per_m3(6, 0.5)
        self.assertEqual(required_class(ceiling, 0.5), 6)

    def test_a_tolerance_just_under_a_ceiling_picks_the_cleaner_class(self):
        ceiling = class_ceiling_per_m3(6, 0.5)
        self.assertEqual(required_class(ceiling * 0.5, 0.5), 5)

    def test_a_generous_tolerance_picks_the_loosest_class(self):
        self.assertEqual(required_class(1.0e12, 0.5), MAX_CLASS)

    def test_a_tolerance_no_room_class_can_hold_raises(self):
        with self.assertRaises(ValueError):
            required_class(1.0e-6, 0.5)

    def test_a_zero_tolerance_raises(self):
        with self.assertRaises(ValueError):
            required_class(0.0, 0.5)


class TestAssessOperation(unittest.TestCase):
    def test_an_adequately_assigned_operation_is_acceptable(self):
        row = assess_operation(operation())
        self.assertTrue(row["acceptable"])
        self.assertEqual(row["required_class"], 5)
        self.assertEqual(row["findings"], [])

    def test_a_looser_area_than_needed_is_rejected(self):
        row = assess_operation(operation(assigned_class=7))
        self.assertFalse(row["acceptable"])
        self.assertIn("assigned-area-looser-than-the-operation-needs", row["findings"])

    def test_an_area_two_classes_cleaner_is_reported_as_overspend(self):
        row = assess_operation(operation(assigned_class=3))
        self.assertIn(
            "assigned-area-far-cleaner-than-the-operation-needs", row["findings"]
        )
        self.assertTrue(row["acceptable"])

    def test_an_area_one_class_cleaner_is_not_reported_as_overspend(self):
        row = assess_operation(operation(assigned_class=4))
        self.assertEqual(row["findings"], [])

    def test_an_at_rest_demonstration_does_not_cover_exposed_hardware(self):
        row = assess_operation(operation(demonstrated_state=STATE_AT_REST))
        self.assertFalse(row["acceptable"])
        self.assertIn(
            "class-demonstrated-only-with-the-room-unoccupied", row["findings"]
        )

    def test_an_at_rest_demonstration_is_fine_with_nothing_exposed(self):
        row = assess_operation(
            operation(demonstrated_state=STATE_AT_REST, hardware_exposed=False)
        )
        self.assertEqual(row["findings"], [])

    def test_the_headroom_fraction_is_the_ceiling_over_the_tolerance(self):
        row = assess_operation(operation())
        self.assertAlmostEqual(
            row["headroom_fraction"],
            class_ceiling_per_m3(5, 0.5) / 4000.0,
            places=9,
        )

    def test_a_decimal_assigned_class_raises(self):
        with self.assertRaises(ValueError):
            validate_operation(operation(assigned_class=4.5))

    def test_a_missing_assigned_class_raises(self):
        record = operation()
        del record["assigned_class"]
        with self.assertRaises(ValueError):
            validate_operation(record)

    def test_an_unknown_demonstrated_state_raises(self):
        with self.assertRaises(ValueError):
            validate_operation(operation(demonstrated_state="probably-fine"))

    def test_a_non_mapping_operation_raises(self):
        with self.assertRaises(ValueError):
            validate_operation("OPTICS-BONDING")


class TestFacilityPlan(unittest.TestCase):
    def test_a_plan_of_adequate_assignments_is_clear(self):
        report = assess_facility_plan([operation("A"), operation("B")])
        self.assertTrue(report["clear"])
        self.assertEqual(report["verdict"], "clean-area-plan-acceptable")

    def test_the_cleanest_class_required_is_reported(self):
        report = assess_facility_plan(
            [
                operation("COARSE", tolerable_per_m3=1.0e6, assigned_class=7),
                operation("FINE"),
            ]
        )
        self.assertEqual(report["cleanest_class_required"], 5)

    def test_one_bad_assignment_rejects_the_plan(self):
        report = assess_facility_plan([operation("A"), operation("B", assigned_class=8)])
        self.assertEqual(report["verdict"], "clean-area-plan-rejected")
        self.assertEqual(report["unacceptable_operation_ids"], ["B"])

    def test_duplicate_operation_ids_raise(self):
        with self.assertRaises(ValueError):
            assess_facility_plan([operation("A"), operation("A")])

    def test_an_empty_plan_raises(self):
        with self.assertRaises(ValueError):
            assess_facility_plan([])


if __name__ == "__main__":
    unittest.main()
