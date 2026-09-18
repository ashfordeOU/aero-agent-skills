"""Contract test for the q40-verification-planning leaf (stdlib unittest)."""

import unittest

from q40_verification_planning_logic import (
    METHODS,
    RATIO_TOLERANCE,
    admissible_methods,
    assess_requirement,
    build_verification_plan,
    coverage_ratio,
    latest_closure_milestone,
    method_mix,
    validate_requirement,
)


def requirement(rid="SR-1", severity="critical", method="test", **kw):
    record = {
        "id": rid,
        "severity": severity,
        "method": method,
        "planned_closure_milestone": "cdr",
        "report_planned": True,
    }
    record.update(kw)
    return record


class TestValidateRequirement(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_requirement(requirement())
        self.assertFalse(norm["analysis_correlated_by_test"])
        self.assertIsNone(norm["similarity_baseline"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(["SR-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement("   "))

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(severity="annoying"))

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(method="a-good-feeling"))

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(planned_closure_milestone="someday"))

    def test_non_boolean_report_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(report_planned="yes"))

    def test_severity_and_method_are_case_folded(self):
        norm = validate_requirement(requirement(severity="CRITICAL", method="Test"))
        self.assertEqual(norm["severity"], "critical")
        self.assertEqual(norm["method"], "test")


class TestAdmissibility(unittest.TestCase):
    def test_catastrophic_carries_only_test_and_analysis(self):
        self.assertEqual(admissible_methods("catastrophic"), ("test", "analysis"))

    def test_minor_carries_every_method(self):
        self.assertEqual(admissible_methods("minor"), METHODS)

    def test_the_admissible_set_shrinks_as_severity_rises(self):
        sizes = [len(admissible_methods(s))
                 for s in ("minor", "major", "critical", "catastrophic")]
        self.assertEqual(sizes, sorted(sizes, reverse=True))

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            admissible_methods("worrying")

    def test_similarity_is_withdrawn_above_minor(self):
        self.assertNotIn("similarity", admissible_methods("major"))


class TestClosureMilestone(unittest.TestCase):
    def test_catastrophic_must_close_by_qualification_review(self):
        self.assertEqual(latest_closure_milestone("catastrophic"), "qr")

    def test_minor_may_run_to_flight_readiness(self):
        self.assertEqual(latest_closure_milestone("minor"), "frr")

    def test_a_late_plan_is_a_finding(self):
        item = assess_requirement(requirement(severity="catastrophic", method="test",
                                              planned_closure_milestone="ar"))
        self.assertFalse(item["planned"])
        self.assertTrue(any("later than" in f for f in item["findings"]))

    def test_closing_exactly_on_the_latest_milestone_is_accepted(self):
        item = assess_requirement(requirement(severity="critical",
                                              planned_closure_milestone="qr"))
        self.assertTrue(item["planned"])


class TestAssessRequirement(unittest.TestCase):
    def test_a_sound_requirement_has_no_findings(self):
        item = assess_requirement(requirement())
        self.assertEqual(item["findings"], [])
        self.assertTrue(item["planned"])

    def test_an_inadmissible_method_is_a_finding(self):
        item = assess_requirement(requirement(severity="catastrophic", method="inspection"))
        self.assertFalse(item["planned"])
        self.assertTrue(any("not admissible" in f for f in item["findings"]))

    def test_uncorrelated_analysis_of_a_catastrophic_requirement_is_a_finding(self):
        item = assess_requirement(requirement(severity="catastrophic", method="analysis"))
        self.assertTrue(any("correlated test data" in f for f in item["findings"]))

    def test_correlated_analysis_of_a_catastrophic_requirement_is_accepted(self):
        item = assess_requirement(requirement(severity="catastrophic", method="analysis",
                                              analysis_correlated_by_test=True))
        self.assertTrue(item["planned"])

    def test_similarity_without_a_baseline_is_a_finding(self):
        item = assess_requirement(requirement(severity="minor", method="similarity"))
        self.assertTrue(any("no baseline" in f for f in item["findings"]))

    def test_similarity_with_a_baseline_is_accepted(self):
        item = assess_requirement(requirement(severity="minor", method="similarity",
                                              similarity_baseline="GSE-77"))
        self.assertTrue(item["planned"])

    def test_a_missing_report_is_a_finding_on_its_own(self):
        item = assess_requirement(requirement(report_planned=False))
        self.assertEqual(len(item["findings"]), 1)
        self.assertFalse(item["planned"])

    def test_several_defects_are_all_reported(self):
        item = assess_requirement(requirement(severity="catastrophic", method="similarity",
                                              planned_closure_milestone="frr",
                                              report_planned=False))
        self.assertGreaterEqual(len(item["findings"]), 4)


class TestPlanRollup(unittest.TestCase):
    def test_method_mix_counts_every_method(self):
        mix = method_mix([requirement("SR-1"), requirement("SR-2", method="inspection")])
        self.assertEqual(mix["test"], 1)
        self.assertEqual(mix["inspection"], 1)
        self.assertEqual(mix["similarity"], 0)

    def test_coverage_of_a_sound_plan_is_one(self):
        ratio = coverage_ratio([requirement("SR-1"), requirement("SR-2")])
        self.assertAlmostEqual(ratio, 1.0, places=9)

    def test_coverage_counts_only_soundly_planned_requirements(self):
        ratio = coverage_ratio([requirement("SR-1"),
                                requirement("SR-2", report_planned=False),
                                requirement("SR-3"),
                                requirement("SR-4", report_planned=False)])
        self.assertAlmostEqual(ratio, 0.5, places=9)

    def test_empty_requirement_set_raises(self):
        with self.assertRaises(ValueError):
            coverage_ratio([])

    def test_a_sound_plan_is_acceptable(self):
        plan = build_verification_plan([requirement("SR-1"), requirement("SR-2")])
        self.assertEqual(plan["disposition"], "plan-acceptable")
        self.assertTrue(plan["acceptable"])
        self.assertAlmostEqual(plan["coverage_ratio"], 1.0, places=9)

    def test_an_open_minor_requirement_only_raises_actions(self):
        plan = build_verification_plan([requirement("SR-1"),
                                        requirement("SR-2", severity="minor",
                                                    report_planned=False)])
        self.assertEqual(plan["disposition"], "plan-acceptable-with-actions")
        self.assertTrue(plan["acceptable"])
        self.assertEqual(plan["open_requirement_ids"], ["SR-2"])

    def test_an_open_catastrophic_requirement_rejects_the_plan(self):
        plan = build_verification_plan([requirement("SR-1"),
                                        requirement("SR-2", severity="catastrophic",
                                                    method="similarity")])
        self.assertEqual(plan["disposition"], "plan-rejected")
        self.assertFalse(plan["acceptable"])
        self.assertEqual(plan["severe_open_requirement_ids"], ["SR-2"])

    def test_duplicate_requirement_ids_raise(self):
        with self.assertRaises(ValueError):
            build_verification_plan([requirement("SR-1"), requirement("SR-1")])

    def test_ratio_tolerance_is_small_enough_to_be_slack_not_a_band(self):
        self.assertLess(RATIO_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
