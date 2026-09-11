#!/usr/bin/env python3
"""Gate 3 behavior contract for e1002-execution (stdlib unittest, offline)."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1002_execution_logic import (  # noqa: E402
    ACTIVITY_STATES, NC_DISPOSITIONS, READINESS_CONDITIONS, activity_state,
    as_run_violations, deviation_violations, execution_review,
    is_execution_valid, may_start, open_nonconformances, unmet_readiness,
    validate_disposition, validate_state,
)


def ready(**over):
    r = {c: True for c in READINESS_CONDITIONS}
    r.update(over)
    return r


def activity(**over):
    a = {"activity_id": "VA-01", "readiness": ready(),
         "nonconformances": [], "deviations": [],
         "planned_steps": ["S1", "S2"], "as_run_steps": ["S1", "S2"]}
    a.update(over)
    return a


class VocabularyTest(unittest.TestCase):
    def test_every_state_validates(self):
        for s in ACTIVITY_STATES:
            self.assertEqual(validate_state(s), s)

    def test_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            validate_state("paused")

    def test_every_disposition_validates(self):
        for d in NC_DISPOSITIONS:
            self.assertEqual(validate_disposition(d), d)

    def test_unknown_disposition_raises(self):
        with self.assertRaises(ValueError):
            validate_disposition("ignore")


class ReadinessTest(unittest.TestCase):
    def test_all_conditions_met_reports_nothing(self):
        self.assertEqual(unmet_readiness(activity()), [])

    def test_unmet_condition_is_reported(self):
        a = activity(readiness=ready(facility_available=False))
        self.assertEqual(unmet_readiness(a), ["facility_available"])

    def test_conditions_are_conjunctive_not_a_score(self):
        a = activity(readiness=ready(procedure_approved=False,
                                     personnel_qualified=False))
        self.assertEqual(len(unmet_readiness(a)), 2)
        self.assertFalse(may_start(a))

    def test_ready_activity_may_start(self):
        self.assertTrue(may_start(activity(as_run_steps=[])))

    def test_open_nonconformance_blocks_start(self):
        a = activity(nonconformances=[{"nc_id": "NC-1", "disposition": "open"}])
        self.assertFalse(may_start(a))


class NonconformanceTest(unittest.TestCase):
    def test_no_nonconformances_reports_nothing(self):
        self.assertEqual(open_nonconformances(activity()), [])

    def test_open_nonconformance_is_listed(self):
        a = activity(nonconformances=[{"nc_id": "NC-1", "disposition": "open"}])
        self.assertEqual(open_nonconformances(a), ["NC-1"])

    def test_dispositioned_nonconformance_is_not_open(self):
        a = activity(nonconformances=[{"nc_id": "NC-1", "disposition": "repair"}])
        self.assertEqual(open_nonconformances(a), [])

    def test_missing_disposition_defaults_to_open(self):
        a = activity(nonconformances=[{"nc_id": "NC-2"}])
        self.assertEqual(open_nonconformances(a), ["NC-2"])

    def test_nonconformance_without_id_raises(self):
        with self.assertRaises(ValueError):
            open_nonconformances(activity(nonconformances=[{"disposition": "open"}]))


class DeviationTest(unittest.TestCase):
    def test_pre_approved_deviation_is_clean(self):
        a = activity(deviations=[{"deviation_id": "D1", "covers_step": "S3",
                                  "approved_before_execution": True}])
        self.assertEqual(deviation_violations(a), [])

    def test_retrospective_approval_is_the_finding(self):
        a = activity(deviations=[{"deviation_id": "D1", "covers_step": "S3",
                                  "approved_before_execution": False}])
        self.assertEqual(deviation_violations(a)[0]["issue"],
                         "deviation_not_approved_before_execution")

    def test_deviation_without_id_raises(self):
        with self.assertRaises(ValueError):
            deviation_violations(activity(deviations=[{"covers_step": "S1"}]))


class AsRunTest(unittest.TestCase):
    def test_as_run_matching_plan_is_clean(self):
        self.assertEqual(as_run_violations(activity()), [])

    def test_absent_as_run_record_is_reported(self):
        a = activity(as_run_steps=[])
        self.assertEqual(as_run_violations(a)[0]["issue"], "no_as_run_record")

    def test_planned_step_not_run_is_reported(self):
        a = activity(as_run_steps=["S1"])
        self.assertIn("planned_step_not_run",
                      [f["issue"] for f in as_run_violations(a)])

    def test_unplanned_step_run_is_reported(self):
        a = activity(as_run_steps=["S1", "S2", "S9"])
        self.assertIn("unplanned_step_run",
                      [f["issue"] for f in as_run_violations(a)])

    def test_a_covered_departure_is_not_a_finding(self):
        a = activity(as_run_steps=["S1", "S2", "S9"],
                     deviations=[{"deviation_id": "D1", "covers_step": "S9",
                                  "approved_before_execution": True}])
        self.assertEqual(as_run_violations(a), [])


class StateTest(unittest.TestCase):
    def test_open_nonconformance_suspends(self):
        a = activity(nonconformances=[{"nc_id": "N", "disposition": "open"}])
        self.assertEqual(activity_state(a), "suspended")

    def test_unmet_readiness_stays_planned(self):
        a = activity(readiness=ready(facility_available=False), as_run_steps=[])
        self.assertEqual(activity_state(a), "planned")

    def test_ready_but_not_started_is_ready(self):
        self.assertEqual(activity_state(activity(as_run_steps=[])), "ready")

    def test_clean_as_run_completes(self):
        self.assertEqual(activity_state(activity()), "complete")

    def test_as_run_gap_leaves_it_executing(self):
        self.assertEqual(activity_state(activity(as_run_steps=["S1"])), "executing")

    def test_nonconformance_dominates_readiness(self):
        a = activity(readiness=ready(facility_available=False),
                     nonconformances=[{"nc_id": "N", "disposition": "open"}])
        self.assertEqual(activity_state(a), "suspended")


class ReviewTest(unittest.TestCase):
    def test_clean_activity_is_valid(self):
        r = execution_review(activity())
        self.assertEqual(r["state"], "complete")
        self.assertTrue(is_execution_valid(r))

    def test_findings_carry_the_activity_id(self):
        a = activity(deviations=[{"deviation_id": "D1", "covers_step": "S1",
                                  "approved_before_execution": False}])
        r = execution_review(a)
        self.assertEqual(r["findings"][0]["activity_id"], "VA-01")
        self.assertFalse(is_execution_valid(r))

    def test_activity_without_id_raises(self):
        a = activity()
        del a["activity_id"]
        with self.assertRaises(ValueError):
            execution_review(a)

    def test_review_does_not_mutate_input(self):
        a = activity()
        before = copy.deepcopy(a)
        execution_review(a)
        self.assertEqual(a, before)


if __name__ == "__main__":
    unittest.main()
