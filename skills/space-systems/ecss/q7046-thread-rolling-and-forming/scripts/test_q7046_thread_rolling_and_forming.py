"""Contract test for the fastener thread-forming leaf (stdlib unittest)."""

import unittest

from q7046_thread_rolling_and_forming_logic import (
    ACCEPTED,
    ACCEPTED_WITH_CONTROLS,
    CUT,
    NOT_APPLICABLE,
    REJECTED,
    ROLL_AFTER_HEAT_TREATMENT,
    ROLL_BEFORE_HEAT_TREATMENT,
    ROLLED,
    ROOT_RADIUS_FLOOR_FRACTION,
    assess_forming_schedule,
    assess_thread_forming,
    class_rank,
    fatigue_allowable_n,
    fatigue_benefit_factor,
    minimum_root_radius_mm,
    minor_diameter_mm,
    pitch_diameter_mm,
    required_forming_method,
    required_forming_sequence,
    rolling_blank_diameter_mm,
    root_radius_admissible,
    validate_thread_record,
)


def thread(**kw):
    record = {
        "part_number": "fs-4001",
        "property_class": "8.8",
        "declared_method": ROLLED,
        "declared_sequence": ROLL_BEFORE_HEAT_TREATMENT,
        "nominal_diameter_mm": 10.0,
        "pitch_mm": 1.5,
        "root_radius_mm": ROOT_RADIUS_FLOOR_FRACTION * 1.5,
        "fatigue_critical": False,
        "heat_treated": True,
        "base_fatigue_allowable_n": 10000.0,
        "duty_load_n": 0.0,
    }
    record.update(kw)
    return record


class TestPropertyClasses(unittest.TestCase):
    def test_the_classes_rank_by_strength(self):
        self.assertLess(class_rank("4.6"), class_rank("8.8"))
        self.assertLess(class_rank("8.8"), class_rank("12.9"))

    def test_an_unknown_class_raises(self):
        with self.assertRaises(ValueError):
            class_rank("11.4")

    def test_a_non_string_class_raises(self):
        with self.assertRaises(ValueError):
            class_rank(10.9)


class TestThreadGeometry(unittest.TestCase):
    def test_the_pitch_diameter_follows_from_diameter_and_pitch(self):
        self.assertAlmostEqual(pitch_diameter_mm(10.0, 1.5), 9.025721420742506,
                               places=9)

    def test_the_minor_diameter_sits_below_the_pitch_diameter(self):
        self.assertLess(minor_diameter_mm(10.0, 1.5), pitch_diameter_mm(10.0, 1.5))

    def test_a_finer_pitch_moves_both_diameters_up(self):
        self.assertGreater(pitch_diameter_mm(10.0, 1.0), pitch_diameter_mm(10.0, 1.5))
        self.assertGreater(minor_diameter_mm(10.0, 1.0), minor_diameter_mm(10.0, 1.5))

    def test_the_root_radius_floor_is_a_fraction_of_the_pitch(self):
        self.assertAlmostEqual(minimum_root_radius_mm(1.5), 0.1875, places=9)

    def test_a_radius_exactly_on_the_floor_is_admissible(self):
        self.assertTrue(root_radius_admissible(minimum_root_radius_mm(1.5), 1.5))

    def test_a_sharper_root_is_not_admissible(self):
        self.assertFalse(root_radius_admissible(0.10, 1.5))

    def test_a_zero_pitch_raises(self):
        with self.assertRaises(ValueError):
            pitch_diameter_mm(10.0, 0.0)

    def test_a_pitch_above_the_diameter_raises(self):
        with self.assertRaises(ValueError):
            minor_diameter_mm(1.0, 1.5)

    def test_a_negative_diameter_raises(self):
        with self.assertRaises(ValueError):
            pitch_diameter_mm(-10.0, 1.5)


class TestRollingBlank(unittest.TestCase):
    def test_the_blank_sits_just_above_the_pitch_diameter(self):
        blank = rolling_blank_diameter_mm(10.0, 1.5)
        self.assertGreater(blank, pitch_diameter_mm(10.0, 1.5))
        self.assertLess(blank, 10.0)

    def test_the_blank_stays_above_the_minor_diameter(self):
        self.assertGreater(
            rolling_blank_diameter_mm(10.0, 1.5), minor_diameter_mm(10.0, 1.5)
        )

    def test_a_zero_fill_allowance_lands_on_the_pitch_diameter(self):
        self.assertAlmostEqual(
            rolling_blank_diameter_mm(10.0, 1.5, 0.0),
            pitch_diameter_mm(10.0, 1.5),
            places=9,
        )

    def test_the_fill_allowance_scales_with_the_pitch(self):
        blank = rolling_blank_diameter_mm(10.0, 1.5, 0.10)
        self.assertAlmostEqual(blank - pitch_diameter_mm(10.0, 1.5), 0.15, places=9)

    def test_an_excessive_fill_allowance_raises(self):
        with self.assertRaises(ValueError):
            rolling_blank_diameter_mm(10.0, 1.5, 0.40)


class TestRequiredMethod(unittest.TestCase):
    def test_a_high_class_must_be_rolled(self):
        self.assertEqual(required_forming_method("10.9"), ROLLED)

    def test_the_class_floor_itself_must_be_rolled(self):
        self.assertEqual(required_forming_method("8.8"), ROLLED)

    def test_a_low_class_may_be_cut(self):
        self.assertEqual(required_forming_method("4.6"), CUT)

    def test_a_fatigue_duty_overrides_a_low_class(self):
        self.assertEqual(
            required_forming_method("4.6", fatigue_critical=True), ROLLED
        )

    def test_an_unhardened_part_has_no_sequence(self):
        self.assertEqual(
            required_forming_sequence("10.9", heat_treated=False), NOT_APPLICABLE
        )

    def test_a_high_class_rolls_after_heat_treatment(self):
        self.assertEqual(
            required_forming_sequence("12.9"), ROLL_AFTER_HEAT_TREATMENT
        )

    def test_a_middle_class_may_roll_before_it(self):
        self.assertEqual(
            required_forming_sequence("8.8"), ROLL_BEFORE_HEAT_TREATMENT
        )

    def test_a_fatigue_duty_forces_rolling_after_heat_treatment(self):
        self.assertEqual(
            required_forming_sequence("8.8", fatigue_critical=True),
            ROLL_AFTER_HEAT_TREATMENT,
        )


class TestFatigueBenefit(unittest.TestCase):
    def test_rolling_after_heat_treatment_earns_the_most(self):
        self.assertGreater(
            fatigue_benefit_factor(ROLLED, ROLL_AFTER_HEAT_TREATMENT),
            fatigue_benefit_factor(ROLLED, ROLL_BEFORE_HEAT_TREATMENT),
        )

    def test_a_cut_thread_earns_nothing(self):
        self.assertAlmostEqual(
            fatigue_benefit_factor(CUT, NOT_APPLICABLE), 1.0, places=9
        )

    def test_a_cut_thread_earns_nothing_whatever_the_sequence(self):
        self.assertAlmostEqual(
            fatigue_benefit_factor(CUT, ROLL_AFTER_HEAT_TREATMENT), 1.0, places=9
        )

    def test_the_allowable_scales_by_the_factor(self):
        allowable = fatigue_allowable_n(10000.0, ROLLED, ROLL_AFTER_HEAT_TREATMENT)
        self.assertAlmostEqual(allowable, 13000.0, places=9)

    def test_an_unknown_pair_raises(self):
        with self.assertRaises(ValueError):
            fatigue_benefit_factor("forged-by-wishing", NOT_APPLICABLE)

    def test_a_zero_base_allowable_raises(self):
        with self.assertRaises(ValueError):
            fatigue_allowable_n(0.0, ROLLED, NOT_APPLICABLE)


class TestValidateThreadRecord(unittest.TestCase):
    def test_a_well_formed_record_normalizes(self):
        norm = validate_thread_record(thread())
        self.assertEqual(norm["part_number"], "fs-4001")
        self.assertAlmostEqual(norm["pitch_mm"], 1.5, places=9)

    def test_a_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_thread_record("rolled")

    def test_an_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_thread_record(thread(declared_method="ground"))

    def test_an_unknown_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_thread_record(thread(declared_sequence="whenever"))

    def test_a_missing_part_number_raises(self):
        with self.assertRaises(ValueError):
            validate_thread_record(thread(part_number=""))


class TestAssessThreadForming(unittest.TestCase):
    def test_a_compliant_declaration_is_accepted(self):
        result = assess_thread_forming(thread())
        self.assertEqual(result["disposition"], ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_cut_thread_on_a_rolled_class_is_rejected(self):
        result = assess_thread_forming(
            thread(declared_method=CUT, declared_sequence=NOT_APPLICABLE)
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn(
            "cut-thread-where-a-rolled-thread-is-required", result["findings"]
        )

    def test_rolling_before_a_heat_treatment_that_relaxes_it_is_rejected(self):
        result = assess_thread_forming(
            thread(property_class="12.9",
                   declared_sequence=ROLL_BEFORE_HEAT_TREATMENT)
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn(
            "thread-rolled-before-the-heat-treatment-that-relaxes-it",
            result["findings"],
        )

    def test_rolling_after_heat_treatment_carries_a_machine_control(self):
        result = assess_thread_forming(
            thread(property_class="12.9",
                   declared_sequence=ROLL_AFTER_HEAT_TREATMENT)
        )
        self.assertEqual(result["disposition"], ACCEPTED_WITH_CONTROLS)
        self.assertIn(
            "confirm-the-rolling-machine-capability-on-hardened-stock",
            result["controls"],
        )

    def test_a_low_class_unhardened_cut_thread_is_accepted(self):
        result = assess_thread_forming(
            thread(property_class="4.6", declared_method=CUT,
                   declared_sequence=NOT_APPLICABLE, heat_treated=False)
        )
        self.assertEqual(result["disposition"], ACCEPTED)

    def test_a_fatigue_duty_rejects_that_same_cut_thread(self):
        result = assess_thread_forming(
            thread(property_class="4.6", declared_method=CUT,
                   declared_sequence=NOT_APPLICABLE, heat_treated=False,
                   fatigue_critical=True)
        )
        self.assertEqual(result["disposition"], REJECTED)

    def test_a_notch_sharp_root_is_rejected(self):
        result = assess_thread_forming(thread(root_radius_mm=0.05))
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn("root-radius-below-the-notch-floor", result["findings"])

    def test_a_duty_exactly_on_the_allowable_is_met(self):
        result = assess_thread_forming(
            thread(base_fatigue_allowable_n=10000.0,
                   declared_sequence=ROLL_AFTER_HEAT_TREATMENT,
                   property_class="10.9", duty_load_n=13000.0)
        )
        self.assertTrue(result["duty_met"])

    def test_a_duty_above_the_allowable_is_rejected(self):
        result = assess_thread_forming(
            thread(base_fatigue_allowable_n=10000.0, duty_load_n=12000.0)
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn(
            "duty-load-above-the-fatigue-allowable-earned", result["findings"]
        )

    def test_a_rolled_declaration_reports_its_blank_diameter(self):
        result = assess_thread_forming(thread())
        self.assertIn("rolling_blank_diameter_mm", result["geometry"])

    def test_a_cut_declaration_reports_no_blank_diameter(self):
        result = assess_thread_forming(
            thread(property_class="4.6", declared_method=CUT,
                   declared_sequence=NOT_APPLICABLE, heat_treated=False)
        )
        self.assertNotIn("rolling_blank_diameter_mm", result["geometry"])


class TestAssessFormingSchedule(unittest.TestCase):
    def test_a_clean_schedule_is_accepted(self):
        report = assess_forming_schedule(
            [thread(), thread(part_number="fs-4002")]
        )
        self.assertEqual(report["build_disposition"], ACCEPTED)
        self.assertEqual(report["rejected_parts"], [])

    def test_the_worst_thread_sets_the_build_disposition(self):
        report = assess_forming_schedule(
            [
                thread(),
                thread(part_number="fs-4003", declared_method=CUT,
                       declared_sequence=NOT_APPLICABLE),
            ]
        )
        self.assertEqual(report["build_disposition"], REJECTED)
        self.assertEqual(report["rejected_parts"], ["fs-4003"])

    def test_parts_rolled_after_heat_treatment_are_listed(self):
        report = assess_forming_schedule(
            [
                thread(part_number="fs-4004", property_class="12.9",
                       declared_sequence=ROLL_AFTER_HEAT_TREATMENT),
            ]
        )
        self.assertEqual(report["parts_rolled_after_heat_treatment"], ["fs-4004"])

    def test_a_duplicate_part_raises(self):
        with self.assertRaises(ValueError):
            assess_forming_schedule([thread(), thread()])

    def test_an_empty_schedule_raises(self):
        with self.assertRaises(ValueError):
            assess_forming_schedule([])


if __name__ == "__main__":
    unittest.main()
