#!/usr/bin/env python3
"""Contract test for the SCA qualification schedule, clause 6.4.2 (offline)."""

import copy
import unittest

from e2008_sca_qualification_schedule_logic import (
    DEFAULT_SCHEDULE_POLICY,
    REQUIRED_SCHEDULE_STEPS,
    SCHEDULE_NOT_RUNNABLE,
    SCHEDULE_RUNNABLE,
    STEP_COUPONS_EXHAUSTED,
    STEP_ORDERED,
    STEP_OUT_OF_ORDER,
    STEP_PREREQUISITE_ABSENT,
    assess_qualification_schedule,
    assess_schedule_step,
    coupon_flow,
    minimum_coupon_demand,
    ordering_status,
    required_schedule_steps,
    step_definition,
    step_prerequisites,
    validate_schedule_policy,
    validate_sequence,
)

NOMINAL_SEQUENCE = [
    "coupon-manufacture",
    "initial-visual-inspection",
    "initial-electrical-measurement",
    "thermal-cycling",
    "humidity-exposure",
    "electrostatic-discharge-test",
    "final-electrical-measurement",
    "final-visual-inspection",
    "qualification-report",
]

NOMINAL_COUPONS = 6


def _case(sequence=None, coupons=NOMINAL_COUPONS):
    return {
        "sequence": list(NOMINAL_SEQUENCE if sequence is None else sequence),
        "initial_coupons": coupons,
    }


def _records(case, policy=DEFAULT_SCHEDULE_POLICY):
    result = assess_qualification_schedule(case, policy)
    return {record["step"]: record for record in result["step_records"]}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_schedule_policy(DEFAULT_SCHEDULE_POLICY), DEFAULT_SCHEDULE_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule_policy("run the steps in order")

    def test_negative_coupon_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCHEDULE_POLICY)
        broken["coupon_margin"] = -1
        with self.assertRaises(ValueError):
            validate_schedule_policy(broken)

    def test_non_boolean_documentation_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCHEDULE_POLICY)
        broken["require_documentation_last"] = "always"
        with self.assertRaises(ValueError):
            validate_schedule_policy(broken)


class StepDefinitionTests(unittest.TestCase):
    def test_required_steps_are_returned_as_a_copy(self):
        first = required_schedule_steps()
        first["thermal-cycling"]["coupons_consumed"] = 99
        self.assertEqual(
            required_schedule_steps()["thermal-cycling"]["coupons_consumed"], 2
        )

    def test_manufacture_opens_the_schedule_with_no_prerequisites(self):
        self.assertEqual(step_prerequisites("coupon-manufacture"), ())

    def test_environmental_steps_follow_the_baseline_measurements(self):
        self.assertEqual(
            sorted(step_prerequisites("thermal-cycling")),
            ["initial-electrical-measurement", "initial-visual-inspection"],
        )

    def test_final_measurements_follow_the_environmental_exposures(self):
        self.assertEqual(
            sorted(step_prerequisites("final-electrical-measurement")),
            ["humidity-exposure", "thermal-cycling"],
        )

    def test_the_report_is_the_only_documentation_step(self):
        kinds = {
            name: body["kind"] for name, body in required_schedule_steps().items()
        }
        documentation = [n for n, k in kinds.items() if k == "documentation"]
        self.assertEqual(documentation, ["qualification-report"])

    def test_step_definition_carries_the_coupon_consumption(self):
        self.assertEqual(step_definition("humidity-exposure")["coupons_consumed"], 2)

    def test_unknown_step_rejected(self):
        with self.assertRaises(ValueError):
            step_definition("vibration-survey")

    def test_blank_step_name_rejected(self):
        with self.assertRaises(ValueError):
            step_definition("   ")


class SequenceTests(unittest.TestCase):
    def test_nominal_sequence_validates(self):
        self.assertEqual(len(validate_sequence(NOMINAL_SEQUENCE)), 9)

    def test_sequence_covers_every_required_step(self):
        self.assertEqual(set(NOMINAL_SEQUENCE), set(REQUIRED_SCHEDULE_STEPS))

    def test_repeated_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence(NOMINAL_SEQUENCE + ["thermal-cycling"])

    def test_unknown_step_in_a_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence(["coupon-manufacture", "acoustic-test"])

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([])


class OrderingTests(unittest.TestCase):
    def test_nominal_sequence_is_fully_ordered(self):
        report = ordering_status(NOMINAL_SEQUENCE)
        self.assertTrue(all(entry["ordered"] for entry in report.values()))

    def test_exposure_before_the_baseline_is_a_late_prerequisite(self):
        sequence = list(NOMINAL_SEQUENCE)
        sequence.remove("thermal-cycling")
        sequence.insert(1, "thermal-cycling")
        report = ordering_status(sequence)
        self.assertEqual(
            report["thermal-cycling"]["late_prerequisites"],
            ["initial-electrical-measurement", "initial-visual-inspection"],
        )
        self.assertFalse(report["thermal-cycling"]["ordered"])

    def test_a_dropped_baseline_is_an_absent_prerequisite(self):
        sequence = [s for s in NOMINAL_SEQUENCE if s != "initial-visual-inspection"]
        report = ordering_status(sequence)
        self.assertEqual(
            report["thermal-cycling"]["absent_prerequisites"],
            ["initial-visual-inspection"],
        )

    def test_ordering_reports_the_declared_position(self):
        report = ordering_status(NOMINAL_SEQUENCE)
        self.assertEqual(report["coupon-manufacture"]["position"], 0)
        self.assertEqual(report["qualification-report"]["position"], 8)


class CouponFlowTests(unittest.TestCase):
    def test_full_schedule_demands_the_consumed_coupons_plus_margin(self):
        self.assertEqual(minimum_coupon_demand(), 6)

    def test_a_policy_without_margin_demands_only_what_is_consumed(self):
        policy = copy.deepcopy(DEFAULT_SCHEDULE_POLICY)
        policy["coupon_margin"] = 0
        self.assertEqual(minimum_coupon_demand(policy), 5)

    def test_nominal_batch_survives_the_schedule(self):
        flow = coupon_flow(NOMINAL_SEQUENCE, NOMINAL_COUPONS)
        self.assertEqual(flow["exhausted_at"], [])
        self.assertTrue(flow["meets_demand"])
        self.assertEqual(flow["findings"], [])

    def test_balance_falls_as_the_consuming_steps_run(self):
        trace = {
            entry["step"]: entry
            for entry in coupon_flow(NOMINAL_SEQUENCE, NOMINAL_COUPONS)["trace"]
        }
        self.assertEqual(trace["thermal-cycling"]["closing_balance"], 4)
        self.assertEqual(trace["humidity-exposure"]["closing_balance"], 2)
        self.assertEqual(trace["electrostatic-discharge-test"]["closing_balance"], 1)

    def test_a_thin_batch_runs_out_at_the_last_consuming_step(self):
        flow = coupon_flow(NOMINAL_SEQUENCE, 4)
        self.assertEqual(flow["exhausted_at"], ["electrostatic-discharge-test"])
        self.assertFalse(flow["meets_demand"])

    def test_a_batch_exactly_on_the_demand_meets_it(self):
        flow = coupon_flow(NOMINAL_SEQUENCE, minimum_coupon_demand())
        self.assertEqual(flow["initial_coupons"], flow["required_coupons"])
        self.assertTrue(flow["meets_demand"])
        self.assertEqual(flow["surplus_coupons"], 0)

    def test_a_strict_policy_reports_a_surplus_batch(self):
        policy = copy.deepcopy(DEFAULT_SCHEDULE_POLICY)
        policy["allow_extra_coupons"] = False
        flow = coupon_flow(NOMINAL_SEQUENCE, 12, policy)
        self.assertEqual(flow["surplus_coupons"], 6)
        self.assertTrue(any("more than the demand" in f for f in flow["findings"]))

    def test_negative_starting_batch_rejected(self):
        with self.assertRaises(ValueError):
            coupon_flow(NOMINAL_SEQUENCE, -3)

    def test_fractional_starting_batch_rejected(self):
        with self.assertRaises(ValueError):
            coupon_flow(NOMINAL_SEQUENCE, 6.5)


class StepVerdictTests(unittest.TestCase):
    def test_nominal_step_is_ordered(self):
        record = _records(_case())["thermal-cycling"]
        self.assertEqual(record["verdict"], STEP_ORDERED)
        self.assertTrue(record["runnable"])
        self.assertEqual(record["findings"], [])

    def test_a_misplaced_step_is_out_of_order(self):
        sequence = list(NOMINAL_SEQUENCE)
        sequence.remove("humidity-exposure")
        sequence.insert(1, "humidity-exposure")
        record = _records(_case(sequence))["humidity-exposure"]
        self.assertEqual(record["verdict"], STEP_OUT_OF_ORDER)

    def test_a_step_whose_prerequisite_is_absent_outranks_a_misplacement(self):
        sequence = [s for s in NOMINAL_SEQUENCE if s != "initial-electrical-measurement"]
        record = _records(_case(sequence, coupons=0))["thermal-cycling"]
        self.assertEqual(record["verdict"], STEP_PREREQUISITE_ABSENT)

    def test_a_misplacement_outranks_a_coupon_shortfall(self):
        sequence = list(NOMINAL_SEQUENCE)
        sequence.remove("thermal-cycling")
        sequence.insert(1, "thermal-cycling")
        record = _records(_case(sequence, coupons=0))["thermal-cycling"]
        self.assertEqual(record["verdict"], STEP_OUT_OF_ORDER)

    def test_a_thin_batch_shows_as_a_coupon_verdict_on_the_right_step(self):
        records = _records(_case(coupons=4))
        self.assertEqual(
            records["electrostatic-discharge-test"]["verdict"], STEP_COUPONS_EXHAUSTED
        )
        self.assertEqual(records["thermal-cycling"]["verdict"], STEP_ORDERED)

    def test_step_outside_the_ordering_report_rejected(self):
        with self.assertRaises(ValueError):
            assess_schedule_step("thermal-cycling", {}, {})


class ScheduleTests(unittest.TestCase):
    def test_nominal_schedule_is_runnable(self):
        result = assess_qualification_schedule(_case())
        self.assertEqual(result["verdict"], SCHEDULE_RUNNABLE)
        self.assertEqual(result["open_steps"], [])
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["fully_declared"])

    def test_a_missing_step_stops_the_schedule(self):
        sequence = [s for s in NOMINAL_SEQUENCE if s != "humidity-exposure"]
        result = assess_qualification_schedule(_case(sequence))
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)
        self.assertEqual(result["missing_steps"], ["humidity-exposure"])
        self.assertAlmostEqual(result["completeness_fraction"], 8.0 / 9.0, places=9)

    def test_a_reordered_schedule_is_not_runnable(self):
        sequence = list(NOMINAL_SEQUENCE)
        sequence.remove("final-visual-inspection")
        sequence.insert(1, "final-visual-inspection")
        result = assess_qualification_schedule(_case(sequence))
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)
        self.assertIn("final-visual-inspection", result["open_steps"])

    def test_a_thin_coupon_batch_is_not_runnable(self):
        result = assess_qualification_schedule(_case(coupons=4))
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)
        self.assertEqual(
            result["coupons"]["exhausted_at"], ["electrostatic-discharge-test"]
        )
        self.assertTrue(any("runs out of coupons" in f for f in result["findings"]))

    def test_documentation_that_does_not_close_the_schedule_is_reported(self):
        sequence = list(NOMINAL_SEQUENCE)
        sequence.remove("qualification-report")
        sequence.insert(7, "qualification-report")
        result = assess_qualification_schedule(_case(sequence))
        self.assertFalse(result["documentation_closes_schedule"])
        self.assertTrue(
            any("does not close the schedule" in f for f in result["findings"])
        )

    def test_a_policy_may_drop_the_documentation_placement_rule(self):
        policy = copy.deepcopy(DEFAULT_SCHEDULE_POLICY)
        policy["require_documentation_last"] = False
        result = assess_qualification_schedule(_case(), policy)
        self.assertTrue(result["documentation_closes_schedule"])
        self.assertEqual(result["verdict"], SCHEDULE_RUNNABLE)

    def test_schedule_groups_steps_by_verdict(self):
        grouped = assess_qualification_schedule(_case(coupons=4))[
            "grouped_by_verdict"
        ]
        self.assertEqual(
            grouped[STEP_COUPONS_EXHAUSTED], ["electrostatic-discharge-test"]
        )
        self.assertEqual(len(grouped[STEP_ORDERED]), 8)

    def test_schedule_reports_the_declared_order_it_graded(self):
        result = assess_qualification_schedule(_case())
        self.assertEqual(result["declared_sequence"], NOMINAL_SEQUENCE)

    def test_case_without_a_coupon_count_rejected(self):
        case = _case()
        del case["initial_coupons"]
        with self.assertRaises(ValueError):
            assess_qualification_schedule(case)

    def test_case_without_a_sequence_rejected(self):
        with self.assertRaises(ValueError):
            assess_qualification_schedule({"initial_coupons": 6})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_qualification_schedule(NOMINAL_SEQUENCE)


if __name__ == "__main__":
    unittest.main()
