#!/usr/bin/env python3
"""Contract test for the electromagnetic effects verification plan leaf."""

import unittest
from datetime import date

from e2007_electromagnetic_effects_verification_plan_logic import (
    ADMISSIBLE_METHODS,
    MANDATORY_PLAN_SECTIONS,
    MILESTONE_ORDER,
    VERIFICATION_METHODS,
    assess_verification_plan,
    check_schedule_feasibility,
    check_schedule_ordering,
    compute_requirement_coverage,
    method_admissible,
    missing_plan_sections,
    normalize_method,
    normalize_milestone,
    normalize_requirement_family,
    parse_plan_date,
    validate_activity,
)


def good_activity(**overrides):
    activity = {
        "id": "ACT-010",
        "requirement_id": "EMC-R-010",
        "family": "radiated-emission",
        "method": "test",
        "planned_start": "2027-01-11",
        "duration_days": 4.0,
        "closure_milestone": "QR",
        "facility": "anechoic-chamber-1",
        "configuration": "flight-model-stack",
    }
    activity.update(overrides)
    return activity


def good_plan(**overrides):
    plan = {
        "baseline_date": "2027-01-04",
        "sections": list(MANDATORY_PLAN_SECTIONS),
        "requirements": [
            {"id": "EMC-R-010", "family": "radiated-emission"},
            {"id": "EMC-R-020", "family": "magnetic-moment"},
        ],
        "activities": [
            good_activity(),
            good_activity(
                id="ACT-020",
                requirement_id="EMC-R-020",
                family="magnetic-moment",
                method="analysis",
                planned_start="2027-01-18",
                duration_days=2.0,
                facility="",
                configuration="",
            ),
        ],
        "milestone_dates": {"QR": "2027-03-01"},
        "window_days": 30.0,
        "contingency_fraction": 0.2,
    }
    plan.update(overrides)
    return plan


class TestNormalizers(unittest.TestCase):
    def test_method_canonical_token(self):
        self.assertEqual(normalize_method("Test"), "test")

    def test_method_synonym_review_of_design(self):
        self.assertEqual(normalize_method("  Review Of Design "), "review-of-design")

    def test_method_synonym_single_letter(self):
        self.assertEqual(normalize_method("A"), "analysis")

    def test_method_underscore_is_hyphenated(self):
        self.assertEqual(normalize_method("review_of_design"), "review-of-design")

    def test_every_method_constant_round_trips(self):
        for method in VERIFICATION_METHODS:
            self.assertEqual(normalize_method(method), method)

    def test_method_unknown_raises(self):
        with self.assertRaises(ValueError):
            normalize_method("vibration")

    def test_method_blank_raises(self):
        with self.assertRaises(ValueError):
            normalize_method("   ")

    def test_method_non_string_raises(self):
        with self.assertRaises(ValueError):
            normalize_method(7)

    def test_family_canonical_token(self):
        self.assertEqual(
            normalize_requirement_family("Radiated_Emission"), "radiated-emission"
        )

    def test_family_unknown_raises(self):
        with self.assertRaises(ValueError):
            normalize_requirement_family("thermal-balance")

    def test_milestone_canonical_token(self):
        self.assertEqual(normalize_milestone("CDR"), "cdr")

    def test_milestone_unknown_raises(self):
        with self.assertRaises(ValueError):
            normalize_milestone("lrr")

    def test_milestone_order_is_monotonic(self):
        order = [MILESTONE_ORDER[key] for key in ("srr", "pdr", "cdr", "qr", "ar")]
        self.assertEqual(order, sorted(order))

    def test_parse_plan_date_accepts_iso_string(self):
        self.assertEqual(parse_plan_date("2027-02-03"), date(2027, 2, 3))

    def test_parse_plan_date_accepts_date_object(self):
        self.assertEqual(parse_plan_date(date(2027, 2, 3)), date(2027, 2, 3))

    def test_parse_plan_date_rejects_malformed_string(self):
        with self.assertRaises(ValueError):
            parse_plan_date("03/02/2027")

    def test_parse_plan_date_rejects_non_string(self):
        with self.assertRaises(ValueError):
            parse_plan_date(20270203)


class TestMethodAdmissibility(unittest.TestCase):
    def test_measured_family_accepts_test(self):
        self.assertTrue(method_admissible("radiated-emission", "test"))

    def test_measured_family_rejects_review_of_design(self):
        self.assertFalse(method_admissible("radiated-emission", "review-of-design"))

    def test_tailoring_justification_admits_substitution(self):
        self.assertTrue(
            method_admissible(
                "radiated-emission", "similarity", tailoring_justified=True
            )
        )

    def test_magnetic_moment_accepts_analysis(self):
        self.assertTrue(method_admissible("magnetic-moment", "analysis"))

    def test_bonding_family_accepts_inspection(self):
        self.assertTrue(method_admissible("bonding-and-grounding", "inspection"))

    def test_every_family_declares_at_least_one_method(self):
        for family, methods in ADMISSIBLE_METHODS.items():
            self.assertTrue(methods, family)
            self.assertTrue(methods <= VERIFICATION_METHODS, family)

    def test_admissibility_rejects_unknown_family(self):
        with self.assertRaises(ValueError):
            method_admissible("acoustic-emission", "test")


class TestPlanSections(unittest.TestCase):
    def test_complete_outline_has_no_gap(self):
        self.assertEqual(missing_plan_sections(MANDATORY_PLAN_SECTIONS), [])

    def test_absent_section_is_reported(self):
        outline = [s for s in MANDATORY_PLAN_SECTIONS if s != "nonconformance-handling"]
        self.assertEqual(missing_plan_sections(outline), ["nonconformance-handling"])

    def test_extra_section_is_tolerated(self):
        outline = list(MANDATORY_PLAN_SECTIONS) + ["annex-a-facility-survey"]
        self.assertEqual(missing_plan_sections(outline), [])

    def test_duplicate_section_raises(self):
        outline = list(MANDATORY_PLAN_SECTIONS) + ["requirement-list"]
        with self.assertRaises(ValueError):
            missing_plan_sections(outline)

    def test_string_instead_of_list_raises(self):
        with self.assertRaises(ValueError):
            missing_plan_sections("requirement-list")

    def test_blank_section_name_raises(self):
        with self.assertRaises(ValueError):
            missing_plan_sections(["scope-and-applicability", ""])


class TestActivityValidation(unittest.TestCase):
    def test_valid_activity_is_normalized(self):
        record = validate_activity(good_activity())
        self.assertEqual(record["id"], "act-010")
        self.assertEqual(record["closure_milestone"], "qr")
        self.assertAlmostEqual(record["duration_days"], 4.0)

    def test_validation_is_idempotent(self):
        once = validate_activity(good_activity())
        twice = validate_activity(once)
        self.assertEqual(once, twice)

    def test_missing_key_raises(self):
        activity = good_activity()
        del activity["method"]
        with self.assertRaises(ValueError):
            validate_activity(activity)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_activity(["ACT-010"])

    def test_zero_duration_raises(self):
        with self.assertRaises(ValueError):
            validate_activity(good_activity(duration_days=0.0))

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            validate_activity(good_activity(duration_days=-1.0))

    def test_boolean_duration_raises(self):
        with self.assertRaises(ValueError):
            validate_activity(good_activity(duration_days=True))

    def test_infinite_duration_raises(self):
        with self.assertRaises(ValueError):
            validate_activity(good_activity(duration_days=float("inf")))

    def test_non_string_facility_raises(self):
        with self.assertRaises(ValueError):
            validate_activity(good_activity(facility=3))

    def test_absent_facility_defaults_to_empty(self):
        activity = good_activity()
        del activity["facility"]
        self.assertEqual(validate_activity(activity)["facility"], "")


class TestScheduleOrdering(unittest.TestCase):
    def test_well_ordered_schedule_is_silent(self):
        plan = good_plan()
        findings = check_schedule_ordering(
            plan["baseline_date"], plan["activities"], plan["milestone_dates"]
        )
        self.assertEqual(findings, [])

    def test_activity_before_baseline_is_flagged(self):
        plan = good_plan()
        plan["activities"][0]["planned_start"] = "2026-12-20"
        findings = check_schedule_ordering(
            plan["baseline_date"], plan["activities"], plan["milestone_dates"]
        )
        codes = [f["code"] for f in findings]
        self.assertIn("activity-precedes-plan-baseline", codes)

    def test_activity_overrunning_milestone_is_flagged(self):
        plan = good_plan()
        plan["activities"][0]["planned_start"] = "2027-02-27"
        findings = check_schedule_ordering(
            plan["baseline_date"], plan["activities"], plan["milestone_dates"]
        )
        codes = [f["code"] for f in findings]
        self.assertIn("activity-overruns-closure-milestone", codes)

    def test_activity_ending_on_milestone_day_is_accepted(self):
        plan = good_plan()
        plan["activities"][0]["planned_start"] = "2027-02-25"
        plan["activities"][0]["duration_days"] = 4.0
        findings = check_schedule_ordering(
            plan["baseline_date"], [plan["activities"][0]], plan["milestone_dates"]
        )
        self.assertEqual(findings, [])

    def test_undated_milestone_is_flagged(self):
        plan = good_plan(milestone_dates={"CDR": "2027-02-01"})
        findings = check_schedule_ordering(
            plan["baseline_date"], plan["activities"], plan["milestone_dates"]
        )
        codes = [f["code"] for f in findings]
        self.assertIn("closure-milestone-undated", codes)

    def test_milestone_dates_must_be_a_mapping(self):
        plan = good_plan()
        with self.assertRaises(ValueError):
            check_schedule_ordering(
                plan["baseline_date"], plan["activities"], ["2027-03-01"]
            )


class TestScheduleFeasibility(unittest.TestCase):
    def test_comfortable_window_is_feasible(self):
        result = check_schedule_feasibility(
            [good_activity()], window_days=30.0, contingency_fraction=0.2
        )
        self.assertTrue(result["feasible"])
        self.assertAlmostEqual(result["required_days"], 4.8)

    def test_exhausted_window_is_infeasible(self):
        result = check_schedule_feasibility(
            [good_activity(duration_days=40.0)], window_days=30.0
        )
        self.assertFalse(result["feasible"])
        self.assertAlmostEqual(result["slack_days"], -10.0)

    def test_exact_boundary_survives_float_representation(self):
        activities = [
            good_activity(id="ACT-A", duration_days=1.1),
            good_activity(id="ACT-B", duration_days=2.2),
        ]
        result = check_schedule_feasibility(activities, window_days=3.3)
        self.assertTrue(result["feasible"])
        self.assertAlmostEqual(result["activity_days"], 3.3)

    def test_contingency_above_one_raises(self):
        with self.assertRaises(ValueError):
            check_schedule_feasibility(
                [good_activity()], window_days=30.0, contingency_fraction=1.5
            )

    def test_negative_contingency_raises(self):
        with self.assertRaises(ValueError):
            check_schedule_feasibility(
                [good_activity()], window_days=30.0, contingency_fraction=-0.1
            )

    def test_non_numeric_contingency_raises(self):
        with self.assertRaises(ValueError):
            check_schedule_feasibility(
                [good_activity()], window_days=30.0, contingency_fraction="20%"
            )

    def test_zero_window_raises(self):
        with self.assertRaises(ValueError):
            check_schedule_feasibility([good_activity()], window_days=0.0)

    def test_empty_activity_list_raises(self):
        with self.assertRaises(ValueError):
            check_schedule_feasibility([], window_days=10.0)


class TestRequirementCoverage(unittest.TestCase):
    def test_full_coverage_reports_unity(self):
        plan = good_plan()
        coverage = compute_requirement_coverage(
            plan["requirements"], plan["activities"]
        )
        self.assertAlmostEqual(coverage["coverage_fraction"], 1.0)
        self.assertEqual(coverage["uncovered"], [])

    def test_uncovered_requirement_is_listed(self):
        plan = good_plan()
        coverage = compute_requirement_coverage(
            plan["requirements"], [plan["activities"][0]]
        )
        self.assertEqual(coverage["uncovered"], ["emc-r-020"])
        self.assertAlmostEqual(coverage["coverage_fraction"], 0.5)

    def test_orphan_activity_is_listed(self):
        plan = good_plan()
        extra = good_activity(id="ACT-900", requirement_id="EMC-R-900")
        coverage = compute_requirement_coverage(
            plan["requirements"], plan["activities"] + [extra]
        )
        self.assertEqual(coverage["orphan_activities"], ["act-900"])

    def test_family_mismatch_is_listed_and_not_counted_as_coverage(self):
        plan = good_plan()
        activity = good_activity(family="conducted-emission")
        coverage = compute_requirement_coverage(
            plan["requirements"], [activity, plan["activities"][1]]
        )
        self.assertEqual(coverage["family_mismatch_activities"], ["act-010"])
        self.assertIn("emc-r-010", coverage["uncovered"])

    def test_two_activities_may_cover_one_requirement(self):
        plan = good_plan()
        second = good_activity(id="ACT-011")
        coverage = compute_requirement_coverage(
            plan["requirements"], [plan["activities"][0], second, plan["activities"][1]]
        )
        self.assertEqual(coverage["covered"]["emc-r-010"], ["act-010", "act-011"])

    def test_duplicate_requirement_id_raises(self):
        requirements = [
            {"id": "EMC-R-010", "family": "radiated-emission"},
            {"id": "emc-r-010", "family": "conducted-emission"},
        ]
        with self.assertRaises(ValueError):
            compute_requirement_coverage(requirements, [good_activity()])

    def test_empty_requirement_list_raises(self):
        with self.assertRaises(ValueError):
            compute_requirement_coverage([], [good_activity()])

    def test_requirement_without_family_raises(self):
        with self.assertRaises(ValueError):
            compute_requirement_coverage([{"id": "EMC-R-010"}], [good_activity()])


class TestPlanAssessment(unittest.TestCase):
    def test_sound_plan_is_release_ready(self):
        result = assess_verification_plan(good_plan())
        self.assertEqual(result["verdict"], "compliant")
        self.assertTrue(result["release_ready"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["activity_count"], 2)

    def test_missing_section_drives_non_compliance(self):
        sections = [s for s in MANDATORY_PLAN_SECTIONS if s != "tailoring-justification"]
        result = assess_verification_plan(good_plan(sections=sections))
        codes = [f["code"] for f in result["findings"]]
        self.assertIn("plan-section-missing", codes)
        self.assertEqual(result["verdict"], "non-compliant")

    def test_inadmissible_method_without_tailoring_is_flagged(self):
        plan = good_plan()
        plan["activities"][0]["method"] = "similarity"
        codes = [f["code"] for f in assess_verification_plan(plan)["findings"]]
        self.assertIn("method-not-admissible", codes)

    def test_inadmissible_method_with_tailoring_is_accepted(self):
        plan = good_plan()
        plan["activities"][0]["method"] = "similarity"
        plan["activities"][0]["tailoring_justification"] = True
        codes = [f["code"] for f in assess_verification_plan(plan)["findings"]]
        self.assertNotIn("method-not-admissible", codes)

    def test_measured_activity_without_facility_is_flagged(self):
        plan = good_plan()
        plan["activities"][0]["facility"] = "  "
        codes = [f["code"] for f in assess_verification_plan(plan)["findings"]]
        self.assertIn("test-facility-unnamed", codes)

    def test_measured_activity_without_configuration_is_flagged(self):
        plan = good_plan()
        plan["activities"][0]["configuration"] = ""
        codes = [f["code"] for f in assess_verification_plan(plan)["findings"]]
        self.assertIn("eut-configuration-unnamed", codes)

    def test_modelled_activity_needs_no_facility(self):
        plan = good_plan()
        codes = [f["code"] for f in assess_verification_plan(plan)["findings"]]
        self.assertNotIn("test-facility-unnamed", codes)

    def test_uncovered_requirement_is_a_finding(self):
        plan = good_plan()
        plan["activities"] = [plan["activities"][0]]
        codes = [f["code"] for f in assess_verification_plan(plan)["findings"]]
        self.assertIn("requirement-uncovered", codes)

    def test_infeasible_window_is_a_finding(self):
        plan = good_plan(window_days=3.0)
        codes = [f["code"] for f in assess_verification_plan(plan)["findings"]]
        self.assertIn("schedule-infeasible", codes)

    def test_absent_window_skips_the_schedule_check(self):
        plan = good_plan()
        del plan["window_days"]
        result = assess_verification_plan(plan)
        self.assertIsNone(result["schedule"])
        self.assertTrue(result["release_ready"])

    def test_duplicate_activity_id_raises(self):
        plan = good_plan()
        plan["activities"].append(good_activity())
        with self.assertRaises(ValueError):
            assess_verification_plan(plan)

    def test_plan_missing_key_raises(self):
        plan = good_plan()
        del plan["milestone_dates"]
        with self.assertRaises(ValueError):
            assess_verification_plan(plan)

    def test_plan_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_verification_plan([good_plan()])

    def test_plan_without_activities_raises(self):
        with self.assertRaises(ValueError):
            assess_verification_plan(good_plan(activities=[]))

    def test_findings_carry_code_subject_and_detail(self):
        plan = good_plan(window_days=1.0)
        for finding in assess_verification_plan(plan)["findings"]:
            self.assertEqual(
                sorted(finding.keys()), ["code", "detail", "subject"]
            )


if __name__ == "__main__":
    unittest.main()
