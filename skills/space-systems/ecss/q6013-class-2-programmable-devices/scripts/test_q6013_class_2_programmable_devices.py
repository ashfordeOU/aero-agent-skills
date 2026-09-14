"""Contract tests for the clause 5.6.4 class 2 programmable device handling.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: an unknown device family, a
control named against the wrong category, a reprogrammable record with no
endurance or retention figures, endurance sitting exactly on the derated
allowance, retention sitting exactly on the scaled mission duration, and a one
time part reporting more than a single programming operation.
"""

import unittest

from q6013_class_2_programmable_devices_logic import (
    BASELINE_CONTROLS,
    CATEGORY_CONTROLS,
    DEFAULT_HANDLING_POLICY,
    DEVICE_FAMILIES,
    HANDLING_ACCEPTED,
    HANDLING_ACCEPTED_WITH_FINDINGS,
    HANDLING_REFUSED,
    ONE_TIME,
    REPROGRAMMABLE_NON_VOLATILE,
    REPROGRAMMABLE_VOLATILE,
    assess_programmable_handling,
    endurance_usage_ratio,
    endurance_within_allowance,
    open_controls,
    programmability_category,
    required_controls,
    required_retention_years,
    retention_adequate,
    validate_control_list,
    validate_handling_policy,
)


def _otp_case(**overrides):
    case = {
        "family": "antifuse-fpga",
        "declared_controls": list(required_controls(ONE_TIME)),
        "programming_cycles_used": 1,
    }
    case.update(overrides)
    return case


def _flash_case(**overrides):
    case = {
        "family": "flash-fpga",
        "declared_controls": list(required_controls(REPROGRAMMABLE_NON_VOLATILE)),
        "programming_cycles_used": 100,
        "rated_endurance_cycles": 1000,
        "retention_years": 20.0,
        "mission_years": 10.0,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_handling_policy(None)
        self.assertAlmostEqual(settings["endurance_derating_fraction"], 0.5, places=9)
        self.assertAlmostEqual(settings["retention_margin_factor"], 1.5, places=9)

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_handling_policy({"endurance_fraction": 0.5})

    def test_derating_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_handling_policy({"endurance_derating_fraction": 1.2})

    def test_retention_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_handling_policy({"retention_margin_factor": 0.5})

    def test_negative_open_control_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_handling_policy({"max_open_controls": -1})


class CategoryTests(unittest.TestCase):
    def test_every_declared_family_maps_to_a_known_category(self):
        for family in DEVICE_FAMILIES:
            self.assertIn(
                programmability_category(family),
                (ONE_TIME, REPROGRAMMABLE_NON_VOLATILE, REPROGRAMMABLE_VOLATILE),
            )

    def test_antifuse_part_is_one_time(self):
        self.assertEqual(programmability_category("antifuse-fpga"), ONE_TIME)

    def test_sram_part_is_reprogrammable_volatile(self):
        self.assertEqual(programmability_category("sram-fpga"), REPROGRAMMABLE_VOLATILE)

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            programmability_category("bubble-memory")

    def test_blank_family_rejected(self):
        with self.assertRaises(ValueError):
            programmability_category("   ")


class ControlSetTests(unittest.TestCase):
    def test_every_category_carries_the_baseline(self):
        for category in CATEGORY_CONTROLS:
            for name in BASELINE_CONTROLS:
                self.assertIn(name, required_controls(category))

    def test_one_time_carries_a_blank_verification_control(self):
        self.assertIn("pre-programming-blank-verification", required_controls(ONE_TIME))

    def test_volatile_part_carries_a_scrubbing_provision(self):
        self.assertIn(
            "configuration-scrubbing-provision",
            required_controls(REPROGRAMMABLE_VOLATILE),
        )

    def test_one_time_does_not_carry_a_reprogramming_cycle_log(self):
        self.assertNotIn("reprogramming-cycle-log", required_controls(ONE_TIME))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            required_controls("write-once-ish")

    def test_control_from_another_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_list(["reprogramming-cycle-log"], ONE_TIME, "declared")

    def test_repeated_control_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_list(
                ["configuration-identification", "configuration-identification"],
                ONE_TIME,
                "declared",
            )

    def test_bare_string_control_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_list("configuration-identification", ONE_TIME, "declared")

    def test_an_empty_record_leaves_every_control_open(self):
        self.assertEqual(open_controls(ONE_TIME, None), required_controls(ONE_TIME))


class EnduranceTests(unittest.TestCase):
    def test_usage_ratio_is_spent_over_rated(self):
        self.assertAlmostEqual(endurance_usage_ratio(250, 1000), 0.25, places=9)

    def test_zero_rated_endurance_rejected(self):
        with self.assertRaises(ValueError):
            endurance_usage_ratio(10, 0)

    def test_negative_cycles_rejected(self):
        with self.assertRaises(ValueError):
            endurance_usage_ratio(-1, 1000)

    def test_non_integer_cycles_rejected(self):
        with self.assertRaises(ValueError):
            endurance_usage_ratio(10.5, 1000)

    def test_usage_exactly_on_the_allowance_is_within_it(self):
        self.assertTrue(endurance_within_allowance(0.5, 0.5))

    def test_usage_past_the_allowance_is_not_within_it(self):
        self.assertFalse(endurance_within_allowance(0.75, 0.5))


class RetentionTests(unittest.TestCase):
    def test_required_retention_applies_the_factor(self):
        self.assertAlmostEqual(required_retention_years(10.0, 1.5), 15.0, places=9)

    def test_retention_exactly_on_the_scaled_duration_is_adequate(self):
        self.assertTrue(retention_adequate(15.0, 10.0, 1.5))

    def test_retention_below_the_scaled_duration_is_not_adequate(self):
        self.assertFalse(retention_adequate(12.0, 10.0, 1.5))

    def test_zero_mission_duration_rejected(self):
        with self.assertRaises(ValueError):
            required_retention_years(0.0, 1.5)

    def test_negative_retention_rejected(self):
        with self.assertRaises(ValueError):
            retention_adequate(-1.0, 10.0, 1.5)


class AssessmentTests(unittest.TestCase):
    def test_a_complete_one_time_record_is_accepted(self):
        result = assess_programmable_handling(_otp_case())
        self.assertEqual(result["verdict"], HANDLING_ACCEPTED)
        self.assertEqual(result["category"], ONE_TIME)
        self.assertEqual(result["open_controls"], ())

    def test_one_open_control_reads_as_findings_not_refusal(self):
        controls = list(required_controls(ONE_TIME))
        controls.remove("programming-yield-record")
        result = assess_programmable_handling(_otp_case(declared_controls=controls))
        self.assertEqual(result["verdict"], HANDLING_ACCEPTED_WITH_FINDINGS)
        self.assertEqual(result["open_controls"], ("programming-yield-record",))

    def test_open_controls_past_the_allowance_refuse_the_record(self):
        controls = list(required_controls(ONE_TIME))[:-2]
        result = assess_programmable_handling(_otp_case(declared_controls=controls))
        self.assertEqual(result["verdict"], HANDLING_REFUSED)

    def test_a_one_time_part_programmed_twice_is_refused(self):
        result = assess_programmable_handling(_otp_case(programming_cycles_used=2))
        self.assertEqual(result["verdict"], HANDLING_REFUSED)
        self.assertFalse(result["endurance_within_allowance"])

    def test_a_one_time_part_reports_no_endurance_ratio(self):
        result = assess_programmable_handling(_otp_case())
        self.assertIsNone(result["endurance_usage_ratio"])

    def test_a_complete_reprogrammable_record_is_accepted(self):
        result = assess_programmable_handling(_flash_case())
        self.assertEqual(result["verdict"], HANDLING_ACCEPTED)
        self.assertAlmostEqual(result["endurance_usage_ratio"], 0.1, places=9)

    def test_endurance_exactly_on_the_derated_allowance_is_accepted(self):
        result = assess_programmable_handling(
            _flash_case(programming_cycles_used=500, rated_endurance_cycles=1000)
        )
        self.assertAlmostEqual(
            result["endurance_usage_ratio"],
            DEFAULT_HANDLING_POLICY["endurance_derating_fraction"],
            places=9,
        )
        self.assertEqual(result["verdict"], HANDLING_ACCEPTED)

    def test_endurance_past_the_derated_allowance_refuses_the_record(self):
        result = assess_programmable_handling(
            _flash_case(programming_cycles_used=900, rated_endurance_cycles=1000)
        )
        self.assertEqual(result["verdict"], HANDLING_REFUSED)

    def test_retention_exactly_on_the_scaled_duration_is_accepted(self):
        result = assess_programmable_handling(
            _flash_case(retention_years=15.0, mission_years=10.0)
        )
        self.assertAlmostEqual(result["retention_margin"], 1.0, places=9)
        self.assertEqual(result["verdict"], HANDLING_ACCEPTED)

    def test_retention_short_of_the_scaled_duration_refuses_the_record(self):
        result = assess_programmable_handling(_flash_case(retention_years=11.0))
        self.assertEqual(result["verdict"], HANDLING_REFUSED)
        self.assertFalse(result["retention_adequate"])

    def test_a_volatile_part_needs_its_own_control_set(self):
        controls = list(required_controls(REPROGRAMMABLE_VOLATILE))
        result = assess_programmable_handling(
            _flash_case(family="sram-fpga", declared_controls=controls)
        )
        self.assertEqual(result["category"], REPROGRAMMABLE_VOLATILE)
        self.assertEqual(result["verdict"], HANDLING_ACCEPTED)

    def test_a_reprogrammable_record_without_endurance_figures_rejected(self):
        case = _flash_case()
        del case["rated_endurance_cycles"]
        with self.assertRaises(ValueError):
            assess_programmable_handling(case)

    def test_a_reprogrammable_record_without_retention_figures_rejected(self):
        case = _flash_case()
        del case["retention_years"]
        with self.assertRaises(ValueError):
            assess_programmable_handling(case)

    def test_missing_family_rejected(self):
        case = _flash_case()
        del case["family"]
        with self.assertRaises(ValueError):
            assess_programmable_handling(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_programmable_handling(["family"])

    def test_every_finding_is_a_string(self):
        result = assess_programmable_handling(_flash_case(retention_years=11.0))
        self.assertTrue(result["findings"])
        self.assertTrue(all(isinstance(line, str) for line in result["findings"]))


if __name__ == "__main__":
    unittest.main()
