"""Contract tests for the clause 5.4.8 telecommand-acknowledgement logic."""

import unittest

from e50_telecommand_acknowledgement_logic import (
    DEADLINE_TOLERANCE_S,
    STAGE_LADDER,
    STATUS_COVERED,
    STATUS_FAILED,
    STATUS_LATE,
    STATUS_MISSING,
    STATUS_OUT_OF_ORDER,
    assess_acknowledgement_coverage,
    evaluate_command,
    match_reports,
    stage_deadline_s,
    validate_stage,
    validate_subscription,
)

RTLT = 120.0

COMMAND = {
    "name": "TC_MODE_SET",
    "uplink_epoch_s": 0.0,
    "stages": ["acceptance", "completion"],
    "stage_timeouts_s": {"acceptance": 30.0, "completion": 600.0},
}


def reports(**overrides):
    base = {
        "acceptance": {"command": "TC_MODE_SET", "stage": "acceptance", "received_at_s": 130.0, "success": True},
        "completion": {"command": "TC_MODE_SET", "stage": "completion", "received_at_s": 400.0, "success": True},
    }
    base.update(overrides)
    return [value for value in base.values() if value is not None]


class StageTests(unittest.TestCase):
    def test_stage_name_is_canonicalised(self):
        self.assertEqual(validate_stage("  Acceptance "), "acceptance")

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage("almost-done")

    def test_non_string_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage(2)

    def test_ladder_is_ordered_acceptance_first(self):
        self.assertEqual(STAGE_LADDER[0], "acceptance")
        self.assertEqual(STAGE_LADDER[-1], "completion")


class SubscriptionTests(unittest.TestCase):
    def test_subscription_is_returned_in_ladder_order(self):
        self.assertEqual(
            validate_subscription(["completion", "acceptance"]), ["acceptance", "completion"]
        )

    def test_start_is_optional(self):
        self.assertEqual(
            validate_subscription(["acceptance", "completion"]), ["acceptance", "completion"]
        )

    def test_completion_without_acceptance_rejected(self):
        with self.assertRaises(ValueError):
            validate_subscription(["completion"])

    def test_progress_without_start_rejected(self):
        with self.assertRaises(ValueError):
            validate_subscription(["acceptance", "progress"])

    def test_progress_with_start_accepted(self):
        self.assertEqual(
            validate_subscription(["acceptance", "start", "progress"]),
            ["acceptance", "start", "progress"],
        )

    def test_duplicate_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_subscription(["acceptance", "acceptance"])

    def test_empty_subscription_rejected(self):
        with self.assertRaises(ValueError):
            validate_subscription([])


class DeadlineTests(unittest.TestCase):
    def test_deadline_carries_the_round_trip_light_time(self):
        self.assertAlmostEqual(stage_deadline_s(0.0, 120.0, 30.0), 150.0)

    def test_near_earth_deadline_is_dominated_by_the_timeout(self):
        self.assertAlmostEqual(stage_deadline_s(100.0, 0.5, 30.0), 130.5)

    def test_zero_timeout_rejected(self):
        with self.assertRaises(ValueError):
            stage_deadline_s(0.0, 120.0, 0.0)

    def test_negative_light_time_rejected(self):
        with self.assertRaises(ValueError):
            stage_deadline_s(0.0, -120.0, 30.0)


class MatchReportTests(unittest.TestCase):
    def test_reports_are_matched_to_their_stage(self):
        matched = match_reports("TC_MODE_SET", ["acceptance", "completion"], reports())
        self.assertEqual(sorted(matched), ["acceptance", "completion"])

    def test_reports_for_another_command_are_ignored(self):
        stray = reports() + [
            {"command": "TC_OTHER", "stage": "acceptance", "received_at_s": 10.0, "success": True}
        ]
        matched = match_reports("TC_MODE_SET", ["acceptance", "completion"], stray)
        self.assertEqual(len(matched), 2)

    def test_report_for_an_unsubscribed_stage_rejected(self):
        stray = reports() + [
            {"command": "TC_MODE_SET", "stage": "start", "received_at_s": 200.0, "success": True}
        ]
        with self.assertRaises(ValueError):
            match_reports("TC_MODE_SET", ["acceptance", "completion"], stray)

    def test_duplicate_stage_report_rejected(self):
        doubled = reports() + [
            {"command": "TC_MODE_SET", "stage": "acceptance", "received_at_s": 140.0, "success": True}
        ]
        with self.assertRaises(ValueError):
            match_reports("TC_MODE_SET", ["acceptance", "completion"], doubled)

    def test_non_boolean_success_rejected(self):
        bad = [{"command": "TC_MODE_SET", "stage": "acceptance", "received_at_s": 130.0, "success": 1}]
        with self.assertRaises(ValueError):
            match_reports("TC_MODE_SET", ["acceptance"], bad)

    def test_report_missing_a_field_rejected(self):
        bad = [{"command": "TC_MODE_SET", "stage": "acceptance", "received_at_s": 130.0}]
        with self.assertRaises(ValueError):
            match_reports("TC_MODE_SET", ["acceptance"], bad)


class EvaluateCommandTests(unittest.TestCase):
    def test_fully_reported_command_is_covered(self):
        record = evaluate_command(COMMAND, reports(), RTLT)
        self.assertEqual(record["status"], STATUS_COVERED)
        self.assertTrue(record["covered"])

    def test_absent_completion_is_missing(self):
        record = evaluate_command(COMMAND, reports(completion=None), RTLT)
        self.assertEqual(record["status"], STATUS_MISSING)
        self.assertEqual(record["stages"]["completion"]["status"], STATUS_MISSING)

    def test_report_after_the_deadline_is_late(self):
        late = reports(
            acceptance={"command": "TC_MODE_SET", "stage": "acceptance", "received_at_s": 200.0, "success": True}
        )
        record = evaluate_command(COMMAND, late, RTLT)
        self.assertEqual(record["stages"]["acceptance"]["status"], STATUS_LATE)

    def test_report_exactly_on_the_deadline_is_on_time(self):
        deadline = stage_deadline_s(0.0, RTLT, 30.0)
        onedge = reports(
            acceptance={"command": "TC_MODE_SET", "stage": "acceptance", "received_at_s": deadline, "success": True}
        )
        record = evaluate_command(COMMAND, onedge, RTLT)
        self.assertEqual(record["stages"]["acceptance"]["status"], STATUS_COVERED)
        self.assertLessEqual(
            abs(record["stages"]["acceptance"]["received_at_s"]
                - record["stages"]["acceptance"]["deadline_s"]),
            DEADLINE_TOLERANCE_S,
        )

    def test_rejection_report_is_a_failure_not_a_gap(self):
        rejected = reports(
            acceptance={"command": "TC_MODE_SET", "stage": "acceptance", "received_at_s": 130.0, "success": False}
        )
        record = evaluate_command(COMMAND, rejected, RTLT)
        self.assertEqual(record["status"], STATUS_FAILED)

    def test_completion_before_acceptance_is_out_of_order(self):
        scrambled = reports(
            completion={"command": "TC_MODE_SET", "stage": "completion", "received_at_s": 125.0, "success": True}
        )
        record = evaluate_command(COMMAND, scrambled, RTLT)
        self.assertEqual(record["stages"]["completion"]["status"], STATUS_OUT_OF_ORDER)

    def test_latency_is_measured_from_the_uplink_epoch(self):
        record = evaluate_command(COMMAND, reports(), RTLT)
        self.assertAlmostEqual(record["stages"]["completion"]["latency_s"], 400.0)

    def test_missing_timeout_for_a_subscribed_stage_rejected(self):
        command = dict(COMMAND, stage_timeouts_s={"acceptance": 30.0})
        with self.assertRaises(ValueError):
            evaluate_command(command, reports(), RTLT)

    def test_command_missing_a_field_rejected(self):
        command = dict(COMMAND)
        del command["uplink_epoch_s"]
        with self.assertRaises(ValueError):
            evaluate_command(command, reports(), RTLT)


class BatchTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {"commands": [COMMAND], "reports": reports(), "round_trip_light_time_s": RTLT}
        spec.update(overrides)
        return spec

    def test_fully_acknowledged_batch_is_compliant(self):
        result = assess_acknowledgement_coverage(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_coverage_ratio_counts_covered_commands(self):
        second = dict(COMMAND, name="TC_TWO")
        spec = self._spec(commands=[COMMAND, second])
        result = assess_acknowledgement_coverage(spec)
        self.assertAlmostEqual(result["coverage_ratio"], 0.5)

    def test_uncovered_command_produces_a_named_finding(self):
        result = assess_acknowledgement_coverage(self._spec(reports=reports(completion=None)))
        self.assertFalse(result["compliant"])
        self.assertIn("TC_MODE_SET", result["findings"][0])

    def test_duplicate_command_in_the_batch_rejected(self):
        with self.assertRaises(ValueError):
            assess_acknowledgement_coverage(self._spec(commands=[COMMAND, dict(COMMAND)]))

    def test_empty_batch_rejected(self):
        with self.assertRaises(ValueError):
            assess_acknowledgement_coverage(self._spec(commands=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["round_trip_light_time_s"]
        with self.assertRaises(ValueError):
            assess_acknowledgement_coverage(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_acknowledgement_coverage(["commands"])


if __name__ == "__main__":
    unittest.main()
