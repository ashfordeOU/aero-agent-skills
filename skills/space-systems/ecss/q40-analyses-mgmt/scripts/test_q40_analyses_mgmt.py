"""Contract tests for the clause 7.2-7.4 analysis suite selection logic."""

import unittest

from q40_analyses_mgmt_logic import (
    ANALYSES,
    APPLICABILITY,
    PHASE_REVIEWS,
    PROJECT_PHASES,
    SEVERITY_FLOOR,
    SEVERITY_ORDER,
    applicability,
    assess_analyses_management,
    coverage_ratio,
    effective_applicability,
    late_analyses,
    phase_index,
    plan_gaps,
    recommended_analyses,
    required_analyses,
    severity_rank,
    validate_analysis,
    validate_phase,
    validate_plan,
    validate_severity,
)


def plan(*pairs):
    """Build a plan from (analysis, due_phase) pairs."""
    return [{"analysis": name, "due_phase": phase} for name, phase in pairs]


def full_plan(phase, severity):
    """Build a plan covering everything the phase owes, due in that phase."""
    return plan(*[(name, phase) for name in required_analyses(phase, severity)])


class MatrixShapeTests(unittest.TestCase):
    def test_every_analysis_has_a_row(self):
        self.assertEqual(sorted(APPLICABILITY), sorted(ANALYSES))

    def test_every_row_covers_every_phase(self):
        for name in ANALYSES:
            self.assertEqual(sorted(APPLICABILITY[name]), sorted(PROJECT_PHASES))

    def test_every_entry_is_a_known_status(self):
        allowed = {"mandatory", "recommended", "not-applicable"}
        for name in ANALYSES:
            for phase in PROJECT_PHASES:
                self.assertIn(APPLICABILITY[name][phase], allowed)

    def test_every_analysis_has_a_severity_floor(self):
        self.assertEqual(sorted(SEVERITY_FLOOR), sorted(ANALYSES))

    def test_every_phase_has_a_closing_review(self):
        self.assertEqual(sorted(PHASE_REVIEWS), sorted(PROJECT_PHASES))


class TokenTests(unittest.TestCase):
    def test_phase_is_trimmed_and_lowered(self):
        self.assertEqual(validate_phase(" Phase-C "), "phase-c")

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase("phase-f")

    def test_unknown_analysis_rejected(self):
        with self.assertRaises(ValueError):
            validate_analysis("vibration-analysis")

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_severity("severe")

    def test_phase_index_follows_the_lifecycle(self):
        self.assertLess(phase_index("phase-b"), phase_index("phase-d"))

    def test_severity_rank_puts_catastrophic_first(self):
        self.assertEqual(severity_rank("catastrophic"), 0)
        self.assertEqual(severity_rank(SEVERITY_ORDER[-1]), len(SEVERITY_ORDER) - 1)


class ApplicabilityTests(unittest.TestCase):
    def test_raw_entry_is_read_from_the_matrix(self):
        self.assertEqual(applicability("hazard-analysis", "phase-b"), "mandatory")

    def test_not_applicable_entry_is_untouched_by_severity(self):
        self.assertEqual(
            effective_applicability("sneak-analysis", "phase-a", "catastrophic"),
            "not-applicable",
        )

    def test_mandatory_survives_when_severity_reaches_the_floor(self):
        self.assertEqual(
            effective_applicability("fault-tree-analysis", "phase-b", "critical"), "mandatory"
        )

    def test_mandatory_degrades_when_severity_is_below_the_floor(self):
        self.assertEqual(
            effective_applicability("fault-tree-analysis", "phase-b", "major"), "recommended"
        )

    def test_hazard_analysis_never_degrades(self):
        self.assertEqual(
            effective_applicability("hazard-analysis", "phase-b", "minor"), "mandatory"
        )

    def test_sneak_analysis_only_survives_at_catastrophic(self):
        self.assertEqual(
            effective_applicability("sneak-analysis", "phase-c", "critical"), "recommended"
        )
        self.assertEqual(
            effective_applicability("sneak-analysis", "phase-c", "catastrophic"), "mandatory"
        )


class SuiteSelectionTests(unittest.TestCase):
    def test_mandatory_set_is_in_declaration_order(self):
        suite = required_analyses("phase-c", "catastrophic")
        self.assertEqual(list(suite), [name for name in ANALYSES if name in suite])

    def test_a_benign_project_owes_less(self):
        severe = required_analyses("phase-c", "catastrophic")
        benign = required_analyses("phase-c", "minor")
        self.assertLess(len(benign), len(severe))

    def test_mandatory_and_recommended_do_not_overlap(self):
        phase, severity = "phase-c", "critical"
        self.assertEqual(
            set(required_analyses(phase, severity)) & set(recommended_analyses(phase, severity)),
            set(),
        )

    def test_early_phase_owes_fewer_analyses_than_a_design_phase(self):
        self.assertLess(
            len(required_analyses("phase-0", "catastrophic")),
            len(required_analyses("phase-c", "catastrophic")),
        )

    def test_hazard_analysis_is_owed_from_phase_a_onward(self):
        for phase in ("phase-a", "phase-b", "phase-c", "phase-d"):
            self.assertIn("hazard-analysis", required_analyses(phase, "minor"))


class PlanValidationTests(unittest.TestCase):
    def test_valid_plan_normalises_tokens(self):
        entries = validate_plan(plan((" Hazard-Analysis ", " PHASE-B ")))
        self.assertEqual(entries[0]["analysis"], "hazard-analysis")
        self.assertEqual(entries[0]["due_phase"], "phase-b")

    def test_duplicate_analysis_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(plan(("hazard-analysis", "phase-b"), ("hazard-analysis", "phase-c")))

    def test_unknown_plan_key_rejected(self):
        entries = plan(("hazard-analysis", "phase-b"))
        entries[0]["owner"] = "safety"
        with self.assertRaises(ValueError):
            validate_plan(entries)

    def test_non_sequence_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan({"analysis": "hazard-analysis"})

    def test_empty_plan_is_valid_but_empty(self):
        self.assertEqual(validate_plan([]), [])


class GapTests(unittest.TestCase):
    def test_complete_plan_has_no_missing_mandatory(self):
        gaps = plan_gaps(full_plan("phase-c", "catastrophic"), "phase-c", "catastrophic")
        self.assertEqual(gaps["missing_mandatory"], ())

    def test_missing_mandatory_is_reported(self):
        gaps = plan_gaps(plan(("hazard-analysis", "phase-c")), "phase-c", "catastrophic")
        self.assertIn("fault-tree-analysis", gaps["missing_mandatory"])

    def test_recommended_not_taken_up_is_reported_separately(self):
        gaps = plan_gaps(plan(("hazard-analysis", "phase-a")), "phase-a", "catastrophic")
        self.assertIn("fault-tree-analysis", gaps["recommended_not_planned"])
        self.assertNotIn("fault-tree-analysis", gaps["missing_mandatory"])

    def test_analysis_the_phase_has_no_use_for_is_reported(self):
        gaps = plan_gaps(plan(("sneak-analysis", "phase-0")), "phase-0", "catastrophic")
        self.assertEqual(gaps["planned_without_use"], ("sneak-analysis",))


class LatenessTests(unittest.TestCase):
    def test_analysis_due_in_the_phase_is_not_late(self):
        self.assertEqual(late_analyses(plan(("hazard-analysis", "phase-c")),
                                       "phase-c", "catastrophic"), ())

    def test_analysis_due_earlier_is_not_late(self):
        self.assertEqual(late_analyses(plan(("hazard-analysis", "phase-a")),
                                       "phase-c", "catastrophic"), ())

    def test_analysis_due_later_is_late(self):
        self.assertEqual(
            late_analyses(plan(("hazard-analysis", "phase-e")), "phase-c", "catastrophic"),
            ("hazard-analysis",),
        )

    def test_a_merely_recommended_analysis_is_never_late(self):
        self.assertEqual(
            late_analyses(plan(("sneak-analysis", "phase-e")), "phase-c", "critical"), ()
        )


class CoverageTests(unittest.TestCase):
    def test_complete_plan_covers_everything(self):
        ratio = coverage_ratio(full_plan("phase-c", "catastrophic"), "phase-c", "catastrophic")
        self.assertAlmostEqual(ratio, 1.0, places=9)

    def test_empty_plan_covers_nothing(self):
        ratio = coverage_ratio([], "phase-c", "catastrophic")
        self.assertAlmostEqual(ratio, 0.0, places=9)

    def test_single_analysis_suite_is_fully_covered_by_one_entry(self):
        mandatory = required_analyses("phase-a", "catastrophic")
        self.assertEqual(len(mandatory), 1)
        ratio = coverage_ratio(plan((mandatory[0], "phase-a")), "phase-a", "catastrophic")
        self.assertAlmostEqual(ratio, 1.0, places=9)

    def test_partial_plan_is_between_zero_and_one(self):
        ratio = coverage_ratio(plan(("hazard-analysis", "phase-c")), "phase-c", "catastrophic")
        self.assertGreater(ratio, 0.0)
        self.assertLess(ratio, 1.0)

    def test_phase_with_no_mandatory_set_reads_covered(self):
        ratio = coverage_ratio([], "phase-0", "minor")
        self.assertAlmostEqual(ratio, 1.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_complete_suite_reports_suite_complete(self):
        result = assess_analyses_management(
            {
                "phase": "phase-c",
                "worst_severity": "catastrophic",
                "planned": full_plan("phase-c", "catastrophic"),
            }
        )
        self.assertEqual(result["verdict"], "suite-complete")
        self.assertEqual(result["findings"], [])

    def test_missing_mandatory_analysis_is_a_finding(self):
        result = assess_analyses_management(
            {
                "phase": "phase-c",
                "worst_severity": "catastrophic",
                "planned": plan(("hazard-analysis", "phase-c")),
            }
        )
        self.assertEqual(result["verdict"], "suite-incomplete")
        self.assertTrue(any("is owed at phase-c" in f for f in result["findings"]))

    def test_late_analysis_names_the_closing_review(self):
        entries = [
            {"analysis": name, "due_phase": "phase-e"}
            for name in required_analyses("phase-c", "catastrophic")
        ]
        result = assess_analyses_management(
            {"phase": "phase-c", "worst_severity": "catastrophic", "planned": entries}
        )
        self.assertTrue(any("critical-design-review" in f for f in result["findings"]))

    def test_useless_analysis_is_a_finding(self):
        result = assess_analyses_management(
            {
                "phase": "phase-0",
                "worst_severity": "minor",
                "planned": plan(("sneak-analysis", "phase-0")),
            }
        )
        self.assertTrue(any("no use for it" in f for f in result["findings"]))

    def test_result_carries_the_closing_review(self):
        result = assess_analyses_management(
            {"phase": "phase-d", "worst_severity": "critical", "planned": []}
        )
        self.assertEqual(result["closing_review"], "qualification-and-acceptance-review")

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_analyses_management({"phase": "phase-c", "worst_severity": "critical"})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_analyses_management(["phase-c"])


if __name__ == "__main__":
    unittest.main()
