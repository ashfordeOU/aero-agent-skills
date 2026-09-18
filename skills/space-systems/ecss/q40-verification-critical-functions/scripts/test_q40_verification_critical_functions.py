"""Contract test for the q40-verification-critical-functions leaf (unittest)."""

import unittest

from q40_verification_critical_functions_logic import (
    ACTIVITIES,
    REQUIRED_FAILURE_COVERAGE,
    activity_index,
    failure_coverage_met,
    failure_test_coverage,
    outstanding_activities,
    required_activities,
    supplementary_activities,
    validate_function,
    verify_critical_function,
    verify_function_set,
)

MODES = ["stuck-open", "stuck-closed", "late-response", "spurious-command", "no-output"]


def activity(name, status="passed", **kw):
    record = {"name": name, "status": status}
    if status == "passed":
        record["evidence_ref"] = "VR-%s" % name
    record.update(kw)
    return record


def function(fid="SCF-1", criticality="critical", modes=None, activities=None, **kw):
    modes = MODES if modes is None else modes
    if activities is None:
        activities = [activity(name) for name in required_activities(criticality)]
        for item in activities:
            if item["name"] == "failure-test":
                item["failure_modes_covered"] = list(modes)
    record = {
        "id": fid,
        "criticality": criticality,
        "failure_modes": list(modes),
        "activities": activities,
    }
    record.update(kw)
    return record


class TestValidateFunction(unittest.TestCase):
    def test_a_complete_record_normalises(self):
        norm = validate_function(function())
        self.assertEqual(norm["criticality"], "critical")
        self.assertEqual(len(norm["activities"]), 5)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_function("SCF-1")

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_function(function(""))

    def test_unknown_criticality_raises(self):
        with self.assertRaises(ValueError):
            validate_function(function(criticality="mild"))

    def test_unknown_activity_name_raises(self):
        with self.assertRaises(ValueError):
            validate_function(function(activities=[activity("a-chat-with-the-lead")]))

    def test_unknown_activity_status_raises(self):
        with self.assertRaises(ValueError):
            validate_function(function(activities=[activity("validation", "probably-fine")]))

    def test_a_repeated_activity_raises(self):
        with self.assertRaises(ValueError):
            validate_function(function(activities=[activity("validation"),
                                                   activity("validation")]))

    def test_covering_an_undeclared_failure_mode_raises(self):
        with self.assertRaises(ValueError):
            validate_function(function(activities=[activity(
                "failure-test", failure_modes_covered=["a-mode-nobody-listed"])]))

    def test_non_sequence_activities_raise(self):
        with self.assertRaises(ValueError):
            validate_function(function(activities="validation"))


class TestRequiredActivities(unittest.TestCase):
    def test_catastrophic_owes_every_activity(self):
        self.assertEqual(required_activities("catastrophic"), ACTIVITIES)

    def test_the_owed_set_grows_with_criticality(self):
        sizes = [len(required_activities(c)) for c in ("major", "critical", "catastrophic")]
        self.assertEqual(sizes, sorted(sizes))

    def test_major_does_not_owe_failure_testing(self):
        self.assertNotIn("failure-test", required_activities("major"))

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            required_activities("moderate")

    def test_activity_index_is_keyed_by_name(self):
        index = activity_index(function())
        self.assertIn("qualification", index)
        self.assertEqual(index["qualification"]["status"], "passed")


class TestOutstandingActivities(unittest.TestCase):
    def test_a_complete_function_has_nothing_outstanding(self):
        self.assertEqual(outstanding_activities(function()), [])

    def test_a_missing_owed_activity_is_outstanding(self):
        acts = [activity(n) for n in required_activities("critical") if n != "validation"]
        for item in acts:
            if item["name"] == "failure-test":
                item["failure_modes_covered"] = list(MODES)
        found = outstanding_activities(function(activities=acts))
        self.assertEqual([f["activity"] for f in found], ["validation"])

    def test_a_failed_activity_is_outstanding(self):
        acts = [activity(n) for n in required_activities("major")]
        acts[0]["status"] = "failed"
        found = outstanding_activities(function(criticality="major", activities=acts))
        self.assertEqual(found[0]["reason"], "activity record is a failure")

    def test_a_not_run_activity_is_outstanding(self):
        acts = [activity(n) for n in required_activities("major")]
        acts[1] = activity("qualification", "not-run")
        found = outstanding_activities(function(criticality="major", activities=acts))
        self.assertEqual(found[0]["activity"], "qualification")

    def test_a_referenced_waiver_discharges_a_major_activity(self):
        acts = [activity(n) for n in required_activities("major")]
        acts[1] = activity("qualification", "waived", waiver_ref="WVR-9")
        self.assertEqual(outstanding_activities(
            function(criticality="major", activities=acts)), [])

    def test_a_waiver_without_a_reference_stays_outstanding(self):
        acts = [activity(n) for n in required_activities("major")]
        acts[1] = activity("qualification", "waived")
        found = outstanding_activities(function(criticality="major", activities=acts))
        self.assertEqual(found[0]["reason"], "waived with no waiver reference")

    def test_a_waiver_cannot_discharge_a_catastrophic_activity(self):
        acts = [activity(n) for n in required_activities("catastrophic")]
        acts[0] = activity("validation", "waived", waiver_ref="WVR-9")
        for item in acts:
            if item["name"] == "failure-test":
                item["failure_modes_covered"] = list(MODES)
        found = outstanding_activities(function(criticality="catastrophic", activities=acts))
        self.assertIn("cannot discharge", found[0]["reason"])

    def test_a_pass_without_evidence_is_outstanding(self):
        acts = [activity(n) for n in required_activities("major")]
        acts[0].pop("evidence_ref")
        found = outstanding_activities(function(criticality="major", activities=acts))
        self.assertEqual(found[0]["reason"], "passed with no evidence reference")

    def test_extra_activities_are_reported_as_supplementary(self):
        acts = [activity(n) for n in required_activities("major")]
        acts.append(activity("safety-verification-test"))
        extra = supplementary_activities(function(criticality="major", activities=acts))
        self.assertEqual(extra, ["safety-verification-test"])


class TestFailureCoverage(unittest.TestCase):
    def test_full_coverage_is_one(self):
        self.assertAlmostEqual(failure_test_coverage(function()), 1.0, places=9)

    def test_partial_coverage_is_the_covered_fraction(self):
        acts = [activity(n) for n in required_activities("critical")]
        for item in acts:
            if item["name"] == "failure-test":
                item["failure_modes_covered"] = MODES[:2]
        self.assertAlmostEqual(
            failure_test_coverage(function(activities=acts)), 0.4, places=9)

    def test_a_failed_failure_test_covers_nothing(self):
        acts = [activity(n) for n in required_activities("critical")]
        for item in acts:
            if item["name"] == "failure-test":
                item["status"] = "failed"
                item["failure_modes_covered"] = list(MODES)
        self.assertAlmostEqual(
            failure_test_coverage(function(activities=acts)), 0.0, places=9)

    def test_a_function_with_no_declared_modes_raises(self):
        with self.assertRaises(ValueError):
            failure_test_coverage(function(modes=[], activities=[]))

    def test_coverage_sitting_exactly_on_the_critical_bound_is_met(self):
        acts = [activity(n) for n in required_activities("critical")]
        for item in acts:
            if item["name"] == "failure-test":
                item["failure_modes_covered"] = MODES[:4]
        record = function(activities=acts)
        self.assertAlmostEqual(failure_test_coverage(record),
                               REQUIRED_FAILURE_COVERAGE["critical"], places=9)
        self.assertTrue(failure_coverage_met(record))

    def test_coverage_below_the_bound_is_not_met(self):
        acts = [activity(n) for n in required_activities("critical")]
        for item in acts:
            if item["name"] == "failure-test":
                item["failure_modes_covered"] = MODES[:3]
        self.assertFalse(failure_coverage_met(function(activities=acts)))

    def test_a_category_that_owes_no_failure_test_is_trivially_met(self):
        self.assertTrue(failure_coverage_met(function(criticality="major")))


class TestVerifyFunction(unittest.TestCase):
    def test_a_complete_function_is_verified(self):
        report = verify_critical_function(function())
        self.assertEqual(report["disposition"], "function-verified")
        self.assertTrue(report["verified"])
        self.assertEqual(report["findings"], [])

    def test_a_missing_evidence_reference_only_opens_an_action(self):
        acts = [activity(n) for n in required_activities("major")]
        acts[0].pop("evidence_ref")
        report = verify_critical_function(function(criticality="major", activities=acts))
        self.assertEqual(report["disposition"], "function-verified-with-open-actions")

    def test_a_failed_activity_leaves_the_function_unverified(self):
        acts = [activity(n) for n in required_activities("major")]
        acts[0]["status"] = "failed"
        report = verify_critical_function(function(criticality="major", activities=acts))
        self.assertEqual(report["disposition"], "function-not-verified")
        self.assertFalse(report["verified"])

    def test_thin_failure_coverage_leaves_the_function_unverified(self):
        acts = [activity(n) for n in required_activities("critical")]
        for item in acts:
            if item["name"] == "failure-test":
                item["failure_modes_covered"] = MODES[:1]
        report = verify_critical_function(function(activities=acts))
        self.assertEqual(report["disposition"], "function-not-verified")
        self.assertTrue(any("declared failure modes" in f for f in report["findings"]))

    def test_the_required_coverage_is_reported_back(self):
        report = verify_critical_function(function())
        self.assertAlmostEqual(report["required_failure_coverage"], 0.8, places=9)


class TestFunctionSet(unittest.TestCase):
    def test_a_sound_set_is_verified(self):
        rollup = verify_function_set([function("SCF-1"), function("SCF-2")])
        self.assertEqual(rollup["disposition"], "set-verified")
        self.assertAlmostEqual(rollup["verified_ratio"], 1.0, places=9)

    def test_one_unverified_function_stops_the_set(self):
        acts = [activity(n) for n in required_activities("major")]
        acts[0]["status"] = "failed"
        rollup = verify_function_set([function("SCF-1"),
                                      function("SCF-2", criticality="major",
                                               activities=acts)])
        self.assertEqual(rollup["disposition"], "set-not-verified")
        self.assertEqual(rollup["unverified_ids"], ["SCF-2"])

    def test_open_actions_alone_are_reported_separately(self):
        acts = [activity(n) for n in required_activities("major")]
        acts[0].pop("evidence_ref")
        rollup = verify_function_set([function("SCF-1"),
                                      function("SCF-2", criticality="major",
                                               activities=acts)])
        self.assertEqual(rollup["disposition"], "set-verified-with-open-actions")
        self.assertEqual(rollup["open_action_ids"], ["SCF-2"])
        self.assertAlmostEqual(rollup["verified_ratio"], 0.5, places=9)

    def test_duplicate_function_ids_raise(self):
        with self.assertRaises(ValueError):
            verify_function_set([function("SCF-1"), function("SCF-1")])

    def test_an_empty_set_raises(self):
        with self.assertRaises(ValueError):
            verify_function_set([])


if __name__ == "__main__":
    unittest.main()
