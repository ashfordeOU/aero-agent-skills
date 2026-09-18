"""Contract tests for the clause 5.6.4 test-surveillance logic."""

import unittest
from datetime import datetime

from q20_test_monitoring_logic import (
    CRITICALITIES,
    CUSTOMER_ROLE,
    SURVEILLANCE_ROLE,
    anomaly_findings,
    assess_test_monitoring,
    attendance_covers,
    hold_point_findings,
    normalise_identifier,
    parse_timestamp,
    surveillance_coverage,
    surveillance_demand,
    validate_attendance,
    validate_timeline,
)

STEPS = [
    {
        "id": "setup",
        "sequence": 10,
        "criticality": "routine",
        "start": "2026-05-04T08:00",
        "end": "2026-05-04T09:00",
    },
    {
        "id": "pyro-firing",
        "sequence": 20,
        "criticality": "critical",
        "start": "2026-05-04T10:00",
        "end": "2026-05-04T11:00",
        "customer_witnessed": True,
    },
    {
        "id": "functional-check",
        "sequence": 30,
        "criticality": "critical",
        "start": "2026-05-04T13:00",
        "end": "2026-05-04T14:00",
    },
]

ATTENDANCE = [
    {"role": "product-assurance", "from": "2026-05-04T09:30", "to": "2026-05-04T15:00"},
    {"role": "customer", "from": "2026-05-04T09:45", "to": "2026-05-04T11:30"},
]

HOLD_POINTS = [
    {
        "id": "hp-01",
        "after_step": "pyro-firing",
        "authority": "product-assurance",
        "released": True,
        "released_by": "product-assurance",
        "release_time": "2026-05-04T11:30",
    }
]

PLAN = {
    "steps": STEPS,
    "attendance": ATTENDANCE,
    "hold_points": HOLD_POINTS,
    "anomalies": [],
}


def plan(**overrides):
    """Return a copy of the clean plan with overrides applied."""
    item = dict(PLAN)
    item.update(overrides)
    return item


class HelperTests(unittest.TestCase):
    def test_identifier_normalised(self):
        self.assertEqual(normalise_identifier(" Pyro-Firing ", "id"), "pyro-firing")

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier("  ", "id")

    def test_timestamp_parsed(self):
        self.assertEqual(
            parse_timestamp("2026-05-04T10:00", "t"), datetime(2026, 5, 4, 10, 0)
        )

    def test_date_only_stamp_rejected(self):
        with self.assertRaises(ValueError):
            parse_timestamp("2026-05-04", "t")

    def test_non_string_stamp_rejected(self):
        with self.assertRaises(ValueError):
            parse_timestamp(20260504, "t")


class TimelineTests(unittest.TestCase):
    def test_timeline_is_ordered_by_sequence(self):
        timeline = validate_timeline(list(reversed(STEPS)))
        self.assertEqual([s["id"] for s in timeline], ["setup", "pyro-firing", "functional-check"])

    def test_criticality_vocabulary(self):
        self.assertEqual(CRITICALITIES, ("routine", "critical"))

    def test_unknown_criticality_rejected(self):
        bad = [dict(STEPS[0], criticality="urgent")]
        with self.assertRaises(ValueError):
            validate_timeline(bad)

    def test_duplicate_step_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline([dict(STEPS[0]), dict(STEPS[0], sequence=11)])

    def test_duplicate_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline([dict(STEPS[0]), dict(STEPS[1], sequence=10)])

    def test_step_ending_before_it_starts_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline([dict(STEPS[0], end="2026-05-04T07:00")])

    def test_empty_timeline_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline([])

    def test_non_integer_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline([dict(STEPS[0], sequence="10")])


class AttendanceTests(unittest.TestCase):
    def test_attendance_normalises(self):
        entries = validate_attendance(ATTENDANCE)
        self.assertEqual(entries[0]["role"], SURVEILLANCE_ROLE)

    def test_attendance_leaving_before_arriving_rejected(self):
        with self.assertRaises(ValueError):
            validate_attendance(
                [{"role": "product-assurance", "from": "2026-05-04T12:00", "to": "2026-05-04T09:00"}]
            )

    def test_missing_attendance_is_allowed(self):
        self.assertEqual(validate_attendance(None), [])

    def test_covering_entry_spans_the_step(self):
        timeline = validate_timeline(STEPS)
        entries = validate_attendance(ATTENDANCE)
        self.assertTrue(attendance_covers(timeline[1], SURVEILLANCE_ROLE, entries))

    def test_partial_entry_does_not_cover_the_step(self):
        timeline = validate_timeline(STEPS)
        entries = validate_attendance(
            [{"role": "product-assurance", "from": "2026-05-04T10:30", "to": "2026-05-04T11:00"}]
        )
        self.assertFalse(attendance_covers(timeline[1], SURVEILLANCE_ROLE, entries))


class DemandTests(unittest.TestCase):
    def test_routine_step_demands_nobody(self):
        demand = surveillance_demand(validate_timeline(STEPS))
        self.assertNotIn("setup", demand)

    def test_critical_step_demands_product_assurance(self):
        demand = surveillance_demand(validate_timeline(STEPS))
        self.assertEqual(demand["functional-check"], [SURVEILLANCE_ROLE])

    def test_customer_witnessed_step_demands_both_roles(self):
        demand = surveillance_demand(validate_timeline(STEPS))
        self.assertEqual(demand["pyro-firing"], [SURVEILLANCE_ROLE, CUSTOMER_ROLE])

    def test_customer_witnessed_routine_step_still_demands_surveillance(self):
        steps = [dict(STEPS[0], customer_witnessed=True)]
        demand = surveillance_demand(validate_timeline(steps))
        self.assertEqual(demand["setup"], [SURVEILLANCE_ROLE, CUSTOMER_ROLE])


class CoverageTests(unittest.TestCase):
    def test_full_coverage_ratio_is_one(self):
        result = surveillance_coverage(validate_timeline(STEPS), validate_attendance(ATTENDANCE))
        self.assertEqual(result["demanded_pairs"], 3)
        self.assertAlmostEqual(result["coverage_ratio"], 1.0, places=9)

    def test_missing_customer_leaves_a_gap(self):
        entries = validate_attendance([ATTENDANCE[0]])
        result = surveillance_coverage(validate_timeline(STEPS), entries)
        self.assertAlmostEqual(result["coverage_ratio"], 2.0 / 3.0, places=9)
        self.assertEqual(result["gaps"], ["pyro-firing uncovered by customer"])

    def test_no_demand_gives_full_coverage(self):
        steps = [dict(STEPS[0])]
        result = surveillance_coverage(validate_timeline(steps), [])
        self.assertEqual(result["demanded_pairs"], 0)
        self.assertAlmostEqual(result["coverage_ratio"], 1.0, places=9)


class HoldPointTests(unittest.TestCase):
    def test_clean_hold_point_gives_no_finding(self):
        timeline = validate_timeline(STEPS)
        self.assertEqual(hold_point_findings(timeline, HOLD_POINTS), [])

    def test_unreleased_hold_point_is_a_finding(self):
        timeline = validate_timeline(STEPS)
        points = [dict(HOLD_POINTS[0], released=False)]
        self.assertEqual(hold_point_findings(timeline, points), ["hold point hp-01 was never released"])

    def test_release_by_the_wrong_role_is_a_finding(self):
        timeline = validate_timeline(STEPS)
        points = [dict(HOLD_POINTS[0], released_by="test-conductor")]
        self.assertIn("not by the product-assurance", hold_point_findings(timeline, points)[0])

    def test_next_step_starting_before_release_is_a_finding(self):
        timeline = validate_timeline(STEPS)
        points = [dict(HOLD_POINTS[0], release_time="2026-05-04T13:30")]
        findings = hold_point_findings(timeline, points)
        self.assertTrue(any("started before hold point" in f for f in findings))

    def test_release_before_the_held_step_finished_is_a_finding(self):
        timeline = validate_timeline(STEPS)
        points = [dict(HOLD_POINTS[0], release_time="2026-05-04T10:30")]
        self.assertIn("before step pyro-firing finished", hold_point_findings(timeline, points)[0])

    def test_hold_point_on_an_unknown_step_rejected(self):
        timeline = validate_timeline(STEPS)
        with self.assertRaises(ValueError):
            hold_point_findings(timeline, [dict(HOLD_POINTS[0], after_step="burn-in")])

    def test_duplicate_hold_point_id_rejected(self):
        timeline = validate_timeline(STEPS)
        with self.assertRaises(ValueError):
            hold_point_findings(timeline, [dict(HOLD_POINTS[0]), dict(HOLD_POINTS[0])])


class AnomalyTests(unittest.TestCase):
    def test_no_anomalies_gives_no_finding(self):
        timeline = validate_timeline(STEPS)
        self.assertEqual(anomaly_findings(timeline, [], validate_attendance(ATTENDANCE)), [])

    def test_unlogged_anomaly_is_a_finding(self):
        timeline = validate_timeline(STEPS)
        anomalies = [
            {
                "id": "an-01",
                "time": "2026-05-04T10:20",
                "logged": False,
                "witnessed_by": ["product-assurance", "customer"],
            }
        ]
        findings = anomaly_findings(timeline, anomalies, validate_attendance(ATTENDANCE))
        self.assertEqual(findings, ["anomaly an-01 was not entered in the run log"])

    def test_anomaly_missing_a_demanded_witness_is_a_finding(self):
        timeline = validate_timeline(STEPS)
        anomalies = [
            {
                "id": "an-02",
                "time": "2026-05-04T10:20",
                "logged": True,
                "witnessed_by": ["product-assurance"],
            }
        ]
        findings = anomaly_findings(timeline, anomalies, validate_attendance(ATTENDANCE))
        self.assertIn("not witnessed by customer", findings[0])

    def test_anomaly_outside_every_step_window_is_a_finding(self):
        timeline = validate_timeline(STEPS)
        anomalies = [
            {"id": "an-03", "time": "2026-05-04T12:00", "logged": True, "witnessed_by": []}
        ]
        findings = anomaly_findings(timeline, anomalies, validate_attendance(ATTENDANCE))
        self.assertIn("cannot be attributed", findings[0])

    def test_witness_claim_without_attendance_is_a_finding(self):
        timeline = validate_timeline(STEPS)
        anomalies = [
            {
                "id": "an-04",
                "time": "2026-05-04T13:30",
                "logged": True,
                "witnessed_by": ["product-assurance"],
            }
        ]
        findings = anomaly_findings(timeline, anomalies, [])
        self.assertTrue(any("no attendance covering" in f for f in findings))

    def test_duplicate_anomaly_id_rejected(self):
        timeline = validate_timeline(STEPS)
        entry = {"id": "an-05", "time": "2026-05-04T10:20", "logged": True, "witnessed_by": []}
        with self.assertRaises(ValueError):
            anomaly_findings(timeline, [entry, dict(entry)], [])


class AssessmentTests(unittest.TestCase):
    def test_clean_run_is_surveillance_complete(self):
        result = assess_test_monitoring(plan())
        self.assertEqual(result["verdict"], "surveillance-complete")
        self.assertAlmostEqual(result["coverage_ratio"], 1.0, places=9)

    def test_uncovered_step_gives_a_surveillance_gap(self):
        result = assess_test_monitoring(plan(attendance=[ATTENDANCE[0]]))
        self.assertEqual(result["verdict"], "surveillance-gap")
        self.assertTrue(any("surveillance gap" in f for f in result["findings"]))

    def test_steps_running_out_of_sequence_order_are_reported(self):
        steps = [dict(STEPS[0]), dict(STEPS[1]), dict(STEPS[2], start="2026-05-04T09:10", end="2026-05-04T09:50")]
        result = assess_test_monitoring(plan(steps=steps))
        self.assertTrue(any("out of their sequence order" in f for f in result["findings"]))

    def test_step_count_is_reported(self):
        self.assertEqual(assess_test_monitoring(plan())["step_count"], 3)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_monitoring(["setup"])


if __name__ == "__main__":
    unittest.main()
