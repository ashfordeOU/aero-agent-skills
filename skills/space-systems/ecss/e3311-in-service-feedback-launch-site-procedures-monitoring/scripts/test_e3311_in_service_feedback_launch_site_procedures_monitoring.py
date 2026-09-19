"""Contract tests for the clause 4.16 in-service, launch-site and monitoring logic."""

import unittest

from e3311_in_service_feedback_launch_site_procedures_monitoring_logic import (
    HAZARDOUS_ACTIONS,
    KNOWN_ACTIONS,
    assess_in_service,
    excursion_summary,
    impacted_items,
    life_disposition,
    remaining_shelf_life_days,
    requalification_decision,
    surveillance_status,
    validate_day,
    validate_launch_sequence,
    validate_non_negative,
)

LIMITS = {"temperature_min_c": -10.0, "temperature_max_c": 35.0}


def sequence(**overrides):
    steps = [
        {"step_id": "S1", "action": "area-clear", "personnel": 3},
        {"step_id": "S2", "action": "measure-bridge-resistance", "personnel": 2},
        {"step_id": "S3", "action": "connect-initiation-circuit", "personnel": 2},
        {"step_id": "S4", "action": "remove-safing-device", "personnel": 2},
        {"step_id": "S5", "action": "arm", "personnel": 2},
        {"step_id": "S6", "action": "fire", "personnel": 2},
    ]
    if "steps" in overrides:
        return overrides["steps"]
    return steps


def good_spec(**overrides):
    spec = {
        "item": {
            "manufacture_day": 0,
            "shelf_life_days": 1825,
            "last_surveillance_day": 700,
            "surveillance_interval_days": 365,
        },
        "today_day": 900,
        "anomaly": {
            "item_id": "SN-501",
            "explosive_batch": "B-771",
            "build_standard": "rev-C",
            "design_rooted": False,
        },
        "inventory": [
            {"item_id": "SN-502", "explosive_batch": "B-772", "build_standard": "rev-C"},
        ],
        "launch_sequence": sequence(),
        "monitoring": {
            "records": [
                {"day": 100, "temperature_c": 20.0, "duration_h": 24.0},
                {"day": 200, "temperature_c": 30.0, "duration_h": 12.0},
            ],
            "limits": LIMITS,
            "allowance_h": 50.0,
        },
    }
    spec.update(overrides)
    return spec


class DayGuardTests(unittest.TestCase):
    def test_day_must_be_an_integer(self):
        with self.assertRaises(ValueError):
            validate_day("d", 3.5)

    def test_boolean_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_day("d", True)

    def test_non_negative_accepts_zero(self):
        self.assertEqual(validate_non_negative("h", 0), 0.0)

    def test_negative_hours_rejected(self):
        with self.assertRaises(ValueError):
            validate_non_negative("h", -1.0)


class ShelfLifeTests(unittest.TestCase):
    def test_remaining_life_counts_down(self):
        self.assertEqual(remaining_shelf_life_days(0, 900, 1825), 925)

    def test_remaining_life_goes_negative_once_spent(self):
        self.assertEqual(remaining_shelf_life_days(0, 2000, 1825), -175)

    def test_day_before_manufacture_rejected(self):
        with self.assertRaises(ValueError):
            remaining_shelf_life_days(100, 50, 1825)

    def test_zero_shelf_life_rejected(self):
        with self.assertRaises(ValueError):
            remaining_shelf_life_days(0, 10, 0)

    def test_surveillance_counts_down_to_due(self):
        status = surveillance_status(700, 900, 365)
        self.assertEqual(status["days_to_next_surveillance"], 165)
        self.assertFalse(status["due"])

    def test_surveillance_becomes_due(self):
        status = surveillance_status(300, 900, 365)
        self.assertTrue(status["due"])

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            surveillance_status(300, 900, 0)


class DispositionTests(unittest.TestCase):
    def test_fresh_item_is_serviceable(self):
        result = life_disposition(925, 165)
        self.assertEqual(result["state"], "serviceable")
        self.assertTrue(result["usable"])

    def test_overdue_surveillance_blocks_use(self):
        result = life_disposition(925, -20)
        self.assertEqual(result["state"], "surveillance-due")
        self.assertFalse(result["usable"])

    def test_spent_life_without_extension_is_expired(self):
        result = life_disposition(-5, 100)
        self.assertEqual(result["state"], "expired")
        self.assertFalse(result["usable"])

    def test_spent_life_with_approved_extension_is_usable(self):
        result = life_disposition(-5, 100, True)
        self.assertEqual(result["state"], "life-extended")
        self.assertTrue(result["usable"])

    def test_non_integer_remaining_days_rejected(self):
        with self.assertRaises(ValueError):
            life_disposition(5.0, 100)


class FeedbackTests(unittest.TestCase):
    def test_same_batch_items_are_reached(self):
        result = impacted_items(
            {
                "item_id": "SN-1",
                "explosive_batch": "B-1",
                "build_standard": "rev-A",
                "design_rooted": False,
            },
            [
                {"item_id": "SN-2", "explosive_batch": "B-1", "build_standard": "rev-B"},
                {"item_id": "SN-3", "explosive_batch": "B-9", "build_standard": "rev-A"},
            ],
        )
        self.assertEqual(result["impacted_count"], 1)
        self.assertEqual(result["impacted"][0]["item_id"], "SN-2")

    def test_design_rooted_anomaly_also_reaches_the_build_standard(self):
        result = impacted_items(
            {
                "item_id": "SN-1",
                "explosive_batch": "B-1",
                "build_standard": "rev-A",
                "design_rooted": True,
            },
            [
                {"item_id": "SN-2", "explosive_batch": "B-1", "build_standard": "rev-B"},
                {"item_id": "SN-3", "explosive_batch": "B-9", "build_standard": "rev-A"},
            ],
        )
        self.assertEqual(result["impacted_count"], 2)

    def test_unrelated_inventory_needs_no_quarantine(self):
        result = impacted_items(
            {
                "item_id": "SN-1",
                "explosive_batch": "B-1",
                "build_standard": "rev-A",
                "design_rooted": False,
            },
            [{"item_id": "SN-3", "explosive_batch": "B-9", "build_standard": "rev-B"}],
        )
        self.assertFalse(result["quarantine_required"])

    def test_non_boolean_design_flag_rejected(self):
        with self.assertRaises(ValueError):
            impacted_items(
                {
                    "item_id": "SN-1",
                    "explosive_batch": "B-1",
                    "build_standard": "rev-A",
                    "design_rooted": "yes",
                },
                [],
            )


class SequenceTests(unittest.TestCase):
    def test_known_actions_include_every_hazardous_action(self):
        for action in HAZARDOUS_ACTIONS:
            self.assertIn(action, KNOWN_ACTIONS)

    def test_correct_sequence_is_valid(self):
        result = validate_launch_sequence(sequence())
        self.assertTrue(result["valid"])
        self.assertEqual(result["findings"], [])

    def test_arming_before_the_area_is_clear_is_a_finding(self):
        steps = [
            {"step_id": "S1", "action": "connect-initiation-circuit", "personnel": 2},
            {"step_id": "S2", "action": "measure-bridge-resistance", "personnel": 2},
            {"step_id": "S3", "action": "remove-safing-device", "personnel": 2},
            {"step_id": "S4", "action": "area-clear", "personnel": 3},
            {"step_id": "S5", "action": "arm", "personnel": 2},
            {"step_id": "S6", "action": "fire", "personnel": 2},
        ]
        result = validate_launch_sequence(steps)
        self.assertFalse(result["valid"])
        self.assertTrue(any("area-clear" in f for f in result["findings"]))

    def test_resistance_measurement_after_safing_removal_is_a_finding(self):
        steps = [
            {"step_id": "S1", "action": "area-clear", "personnel": 3},
            {"step_id": "S2", "action": "connect-initiation-circuit", "personnel": 2},
            {"step_id": "S3", "action": "remove-safing-device", "personnel": 2},
            {"step_id": "S4", "action": "measure-bridge-resistance", "personnel": 2},
            {"step_id": "S5", "action": "arm", "personnel": 2},
            {"step_id": "S6", "action": "fire", "personnel": 2},
        ]
        result = validate_launch_sequence(steps)
        self.assertFalse(result["valid"])

    def test_firing_that_is_not_last_is_a_finding(self):
        steps = sequence()[:6]
        steps = steps[:5] + [
            {"step_id": "S6", "action": "fire", "personnel": 2},
            {"step_id": "S7", "action": "area-clear", "personnel": 3},
        ]
        result = validate_launch_sequence(steps)
        self.assertFalse(result["valid"])
        self.assertTrue(any("last step" in f for f in result["findings"]))

    def test_single_person_on_a_hazardous_step_is_a_finding(self):
        steps = sequence()
        steps[4] = {"step_id": "S5", "action": "arm", "personnel": 1}
        result = validate_launch_sequence(steps)
        self.assertFalse(result["valid"])
        self.assertTrue(any("two" in f for f in result["findings"]))

    def test_arming_without_removing_the_safing_device_is_a_finding(self):
        steps = [
            {"step_id": "S1", "action": "area-clear", "personnel": 3},
            {"step_id": "S2", "action": "arm", "personnel": 2},
            {"step_id": "S3", "action": "fire", "personnel": 2},
        ]
        result = validate_launch_sequence(steps)
        self.assertFalse(result["valid"])

    def test_duplicate_step_id_rejected(self):
        steps = sequence()
        steps[1] = dict(steps[1], step_id="S1")
        with self.assertRaises(ValueError):
            validate_launch_sequence(steps)

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            validate_launch_sequence(
                [{"step_id": "S1", "action": "paint-the-fairing", "personnel": 2}]
            )

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_launch_sequence([])


class MonitoringTests(unittest.TestCase):
    def test_records_inside_the_envelope_give_no_excursion(self):
        summary = excursion_summary(
            [{"day": 1, "temperature_c": 20.0, "duration_h": 10.0}], LIMITS
        )
        self.assertEqual(summary["excursion_count"], 0)
        self.assertAlmostEqual(summary["accumulated_hours"], 0.0, places=9)

    def test_hot_and_cold_excursions_both_accumulate(self):
        summary = excursion_summary(
            [
                {"day": 1, "temperature_c": 48.0, "duration_h": 6.0},
                {"day": 2, "temperature_c": -30.0, "duration_h": 4.0},
                {"day": 3, "temperature_c": 20.0, "duration_h": 8.0},
            ],
            LIMITS,
        )
        self.assertEqual(summary["excursion_count"], 2)
        self.assertAlmostEqual(summary["accumulated_hours"], 10.0, places=9)

    def test_a_record_exactly_on_the_limit_is_not_an_excursion(self):
        summary = excursion_summary(
            [{"day": 1, "temperature_c": 35.0, "duration_h": 6.0}], LIMITS
        )
        self.assertEqual(summary["excursion_count"], 0)

    def test_inverted_limits_rejected(self):
        with self.assertRaises(ValueError):
            excursion_summary([], {"temperature_min_c": 40.0, "temperature_max_c": 0.0})

    def test_missing_record_field_rejected(self):
        with self.assertRaises(ValueError):
            excursion_summary([{"day": 1, "temperature_c": 20.0}], LIMITS)

    def test_exposure_inside_the_allowance_needs_no_requalification(self):
        summary = excursion_summary(
            [{"day": 1, "temperature_c": 48.0, "duration_h": 6.0}], LIMITS
        )
        decision = requalification_decision(summary, 50.0)
        self.assertFalse(decision["requalification_required"])

    def test_exposure_exactly_on_the_allowance_needs_no_requalification(self):
        summary = excursion_summary(
            [{"day": 1, "temperature_c": 48.0, "duration_h": 50.0}], LIMITS
        )
        decision = requalification_decision(summary, 50.0)
        self.assertFalse(decision["requalification_required"])
        self.assertAlmostEqual(decision["accumulated_hours"], 50.0, places=9)

    def test_exposure_past_the_allowance_forces_requalification(self):
        summary = excursion_summary(
            [{"day": 1, "temperature_c": 48.0, "duration_h": 80.0}], LIMITS
        )
        decision = requalification_decision(summary, 50.0)
        self.assertTrue(decision["requalification_required"])

    def test_summary_must_carry_accumulated_hours(self):
        with self.assertRaises(ValueError):
            requalification_decision({"excursion_count": 2}, 50.0)


class AssessmentTests(unittest.TestCase):
    def test_clean_case_is_clear_to_use(self):
        result = assess_in_service(good_spec())
        self.assertTrue(result["clear_to_use"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["disposition"]["state"], "serviceable")

    def test_expired_item_is_not_clear_to_use(self):
        spec = good_spec(today_day=2000)
        spec["item"] = dict(spec["item"], last_surveillance_day=1900)
        result = assess_in_service(spec)
        self.assertFalse(result["clear_to_use"])
        self.assertEqual(result["disposition"]["state"], "expired")

    def test_matching_batch_anomaly_raises_a_quarantine_finding(self):
        spec = good_spec()
        spec["inventory"] = [
            {"item_id": "SN-502", "explosive_batch": "B-771", "build_standard": "rev-C"}
        ]
        result = assess_in_service(spec)
        self.assertFalse(result["clear_to_use"])
        self.assertTrue(any("quarantine" in f for f in result["findings"]))

    def test_bad_sequence_sinks_the_assessment(self):
        spec = good_spec()
        steps = sequence()
        steps[4] = {"step_id": "S5", "action": "arm", "personnel": 1}
        spec["launch_sequence"] = steps
        self.assertFalse(assess_in_service(spec)["clear_to_use"])

    def test_excess_monitoring_exposure_sinks_the_assessment(self):
        spec = good_spec()
        spec["monitoring"] = dict(
            spec["monitoring"],
            records=[{"day": 5, "temperature_c": 60.0, "duration_h": 90.0}],
        )
        self.assertFalse(assess_in_service(spec)["clear_to_use"])

    def test_missing_item_key_rejected(self):
        spec = good_spec()
        del spec["item"]["shelf_life_days"]
        with self.assertRaises(ValueError):
            assess_in_service(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_in_service(["item"])


if __name__ == "__main__":
    unittest.main()
