"""Contract test for the q40-02-requirements leaf (stdlib unittest)."""

import unittest

from q40_02_requirements_logic import (
    MAX_LOG_UPDATE_INTERVAL_DAYS,
    REQUIRED_REVIEW_TRIGGERS,
    assess_hazard_analysis_requirements,
    log_duty_findings,
    method_declaration_findings,
    missing_review_triggers,
    phase_coverage,
    required_phases,
    uncovered_operations,
    validate_profile,
    validate_programme,
)


def profile(**kw):
    record = {"segments": ["launch", "orbital"], "crewed": False}
    record.update(kw)
    return record


def programme(**kw):
    prof = kw.pop("profile", profile())
    record = {
        "profile": prof,
        "covered_phases": list(required_phases(prof)),
        "operations": [
            {"id": "OP-1", "phase": "launch-and-ascent"},
            {"id": "OP-2", "phase": "orbital-operations"},
        ],
        "hazard_log": {
            "maintained": True,
            "custodian": "product-assurance-lead",
            "update_interval_days": 90,
        },
        "report_severities": ["catastrophic", "critical"],
        "techniques": ["functional-hazard-review", "operations-walkthrough"],
        "tools": ["hazard-log-database"],
        "review_triggers": list(REQUIRED_REVIEW_TRIGGERS),
    }
    record.update(kw)
    return record


class TestValidateProfile(unittest.TestCase):
    def test_normalizes_defaults(self):
        norm = validate_profile({"segments": ["ground"]})
        self.assertFalse(norm["crewed"])
        self.assertEqual(norm["segments"], ["ground"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(["ground"])

    def test_empty_segments_raises(self):
        with self.assertRaises(ValueError):
            validate_profile({"segments": []})

    def test_unknown_segment_raises(self):
        with self.assertRaises(ValueError):
            validate_profile({"segments": ["lunar-surface"]})

    def test_crewed_without_orbital_raises(self):
        with self.assertRaises(ValueError):
            validate_profile({"segments": ["launch"], "crewed": True})

    def test_non_boolean_crewed_raises(self):
        with self.assertRaises(ValueError):
            validate_profile({"segments": ["orbital"], "crewed": "yes"})


class TestRequiredPhases(unittest.TestCase):
    def test_baseline_phases_always_present(self):
        phases = required_phases(profile(segments=["ground"]))
        self.assertIn("manufacturing", phases)
        self.assertIn("disposal", phases)

    def test_launch_segment_adds_ascent(self):
        self.assertIn("launch-and-ascent", required_phases(profile()))

    def test_reentry_segment_adds_landing(self):
        phases = required_phases(
            profile(segments=["launch", "orbital", "re-entry"])
        )
        self.assertIn("re-entry-and-descent", phases)
        self.assertIn("landing-and-recovery", phases)

    def test_crewed_adds_habitation_phase(self):
        phases = required_phases(profile(segments=["orbital"], crewed=True))
        self.assertIn("crewed-habitation-operations", phases)

    def test_uncrewed_has_no_habitation_phase(self):
        self.assertNotIn("crewed-habitation-operations", required_phases(profile()))

    def test_phases_are_unique(self):
        phases = required_phases(profile(segments=["ground", "launch"]))
        self.assertEqual(len(phases), len(set(phases)))


class TestValidateProgramme(unittest.TestCase):
    def test_accepts_a_well_formed_programme(self):
        norm = validate_programme(programme())
        self.assertEqual(len(norm["operations"]), 2)

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            validate_programme(programme(covered_phases=["deep-space-cruise"]))

    def test_duplicate_operation_id_raises(self):
        ops = [
            {"id": "OP-1", "phase": "launch-and-ascent"},
            {"id": "OP-1", "phase": "orbital-operations"},
        ]
        with self.assertRaises(ValueError):
            validate_programme(programme(operations=ops))

    def test_operation_with_unknown_phase_raises(self):
        ops = [{"id": "OP-9", "phase": "tea-break"}]
        with self.assertRaises(ValueError):
            validate_programme(programme(operations=ops))

    def test_missing_hazard_log_raises(self):
        rec = programme()
        del rec["hazard_log"]
        with self.assertRaises(ValueError):
            validate_programme(rec)

    def test_negative_update_interval_raises(self):
        with self.assertRaises(ValueError):
            validate_programme(
                programme(
                    hazard_log={
                        "maintained": True,
                        "custodian": "pa",
                        "update_interval_days": -3,
                    }
                )
            )

    def test_unknown_report_severity_raises(self):
        with self.assertRaises(ValueError):
            validate_programme(programme(report_severities=["annoying"]))


class TestPhaseCoverage(unittest.TestCase):
    def test_full_coverage_fraction_is_one(self):
        cov = phase_coverage(programme())
        self.assertAlmostEqual(cov["coverage_fraction"], 1.0, places=9)
        self.assertEqual(cov["missing"], [])

    def test_missing_phase_is_reported(self):
        prof = profile()
        phases = [p for p in required_phases(prof) if p != "disposal"]
        cov = phase_coverage(programme(profile=prof, covered_phases=phases))
        self.assertEqual(cov["missing"], ["disposal"])

    def test_coverage_fraction_is_the_quotient(self):
        prof = profile()
        req = required_phases(prof)
        phases = list(req[:2])
        cov = phase_coverage(programme(profile=prof, covered_phases=phases))
        self.assertAlmostEqual(
            cov["coverage_fraction"], 2.0 / float(len(req)), places=9
        )

    def test_phase_outside_scope_is_listed_not_counted(self):
        prof = profile()
        phases = list(required_phases(prof)) + ["landing-and-recovery"]
        cov = phase_coverage(programme(profile=prof, covered_phases=phases))
        self.assertEqual(cov["outside_scope"], ["landing-and-recovery"])
        self.assertAlmostEqual(cov["coverage_fraction"], 1.0, places=9)


class TestOperationsAndDuties(unittest.TestCase):
    def test_operation_inside_a_covered_phase_is_clean(self):
        self.assertEqual(uncovered_operations(programme()), [])

    def test_operation_outside_coverage_is_flagged(self):
        prof = profile()
        phases = [p for p in required_phases(prof) if p != "orbital-operations"]
        self.assertEqual(
            uncovered_operations(programme(profile=prof, covered_phases=phases)),
            ["OP-2"],
        )

    def test_unmaintained_log_is_a_finding(self):
        rec = programme(
            hazard_log={
                "maintained": False,
                "custodian": "pa",
                "update_interval_days": 30,
            }
        )
        self.assertIn("hazard-log-not-maintained", log_duty_findings(rec))

    def test_missing_custodian_is_a_finding(self):
        rec = programme(
            hazard_log={"maintained": True, "update_interval_days": 30}
        )
        self.assertIn("hazard-log-has-no-named-custodian", log_duty_findings(rec))

    def test_interval_on_the_limit_is_accepted(self):
        rec = programme(
            hazard_log={
                "maintained": True,
                "custodian": "pa",
                "update_interval_days": MAX_LOG_UPDATE_INTERVAL_DAYS,
            }
        )
        self.assertNotIn("hazard-log-update-interval-too-long", log_duty_findings(rec))

    def test_interval_past_the_limit_is_a_finding(self):
        rec = programme(
            hazard_log={
                "maintained": True,
                "custodian": "pa",
                "update_interval_days": MAX_LOG_UPDATE_INTERVAL_DAYS + 1,
            }
        )
        self.assertIn("hazard-log-update-interval-too-long", log_duty_findings(rec))

    def test_missing_catastrophic_report_duty_is_a_finding(self):
        rec = programme(report_severities=["critical"])
        self.assertIn(
            "no-hazard-report-duty-for-catastrophic-hazards", log_duty_findings(rec)
        )

    def test_no_technique_declared_is_a_finding(self):
        self.assertIn(
            "no-analysis-technique-declared",
            method_declaration_findings(programme(techniques=[])),
        )

    def test_no_tool_declared_is_a_finding(self):
        self.assertIn(
            "no-supporting-tool-declared",
            method_declaration_findings(programme(tools=[])),
        )


class TestReviewTriggersAndVerdict(unittest.TestCase):
    def test_all_triggers_declared_is_clean(self):
        self.assertEqual(missing_review_triggers(programme()), [])

    def test_dropped_trigger_is_listed(self):
        triggers = [t for t in REQUIRED_REVIEW_TRIGGERS if t != "design-change"]
        self.assertEqual(
            missing_review_triggers(programme(review_triggers=triggers)),
            ["design-change"],
        )

    def test_clean_programme_is_compliant(self):
        result = assess_hazard_analysis_requirements(programme())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_missing_phase_makes_it_non_compliant(self):
        prof = profile()
        phases = [p for p in required_phases(prof) if p != "manufacturing"]
        result = assess_hazard_analysis_requirements(
            programme(profile=prof, covered_phases=phases)
        )
        self.assertFalse(result["compliant"])
        self.assertIn("mission-phase-not-covered:manufacturing", result["findings"])

    def test_findings_accumulate_across_checks(self):
        result = assess_hazard_analysis_requirements(
            programme(techniques=[], tools=[], review_triggers=[])
        )
        self.assertGreaterEqual(len(result["findings"]), 7)

    def test_non_mapping_programme_raises(self):
        with self.assertRaises(ValueError):
            assess_hazard_analysis_requirements(["not", "a", "programme"])


if __name__ == "__main__":
    unittest.main()
