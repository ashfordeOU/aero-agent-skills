"""Contract tests for the clause 4.1.2.2 component control plan scope.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused plan policy, a
plan with no reference or issue, a required subject missing outright, a
subject named with no procedure behind it, a subject below the depth
floor, an unapproved plan and a plan issued after the first procurement
commitment.
"""

import unittest

from q6013_class_1_component_control_plan_logic import (
    DEFAULT_PLAN_POLICY,
    DERATING_AND_APPLICATION_RULES,
    EVALUATION_AND_LOT_QUALIFICATION,
    NONCONFORMANCE_AND_ALERT_ROUTE,
    OBSOLESCENCE_AND_LIFETIME_BUY,
    PLAN_COVERS_CLASS_ONE_SCOPE,
    PLAN_ISSUED_AFTER_PROCUREMENT,
    PLAN_NOT_APPROVED,
    PLAN_NOT_ESTABLISHED,
    PLAN_SUBJECT_COVERAGE_SHORT,
    RADIATION_AND_ENVIRONMENT_SUITABILITY,
    REQUIRED_PLAN_SUBJECTS,
    SCREENING_AND_LOT_ACCEPTANCE,
    SELECTION_AND_APPROVAL_CRITERIA,
    SOURCE_AND_DISTRIBUTOR_CONTROL,
    TRACEABILITY_AND_LOT_RECORDS,
    assess_component_control_plan,
    depth_weighted_completeness,
    marginal_depth_advisories,
    missing_subjects,
    shallow_subjects,
    subject_coverage,
    subject_is_treated,
    validate_plan_identity,
    validate_plan_policy,
    validate_subject_record,
    validate_subjects,
    weakest_treated_subject,
)

DEPTHS = {
    SELECTION_AND_APPROVAL_CRITERIA: 0.90,
    SOURCE_AND_DISTRIBUTOR_CONTROL: 0.85,
    EVALUATION_AND_LOT_QUALIFICATION: 0.80,
    SCREENING_AND_LOT_ACCEPTANCE: 0.88,
    RADIATION_AND_ENVIRONMENT_SUITABILITY: 0.75,
    DERATING_AND_APPLICATION_RULES: 0.82,
    OBSOLESCENCE_AND_LIFETIME_BUY: 0.78,
    TRACEABILITY_AND_LOT_RECORDS: 0.84,
    NONCONFORMANCE_AND_ALERT_ROUTE: 0.86,
}


def _policy(**overrides):
    policy = dict(DEFAULT_PLAN_POLICY)
    policy.update(overrides)
    return policy


def _subjects(**overrides):
    depths = dict(DEPTHS)
    depths.update(overrides)
    return [
        {
            "subject": name,
            "depth": depths[name],
            "procedure_reference": "CCP-PROC-%02d" % (index + 1),
        }
        for index, name in enumerate(REQUIRED_PLAN_SUBJECTS)
        if name in depths
    ]


def _plan(**overrides):
    plan = {
        "plan_reference": "CCP-4471",
        "issue": "issue 3",
        "approved_by_customer": True,
        "issued_before_first_procurement": True,
        "subjects": _subjects(),
    }
    plan.update(overrides)
    return plan


def _case(**overrides):
    case = {"plan": _plan()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_plan_policy(DEFAULT_PLAN_POLICY), DEFAULT_PLAN_POLICY)

    def test_coverage_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(_policy(min_subject_coverage=1.2))

    def test_depth_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(_policy(min_subject_depth=1.5))

    def test_non_positive_depth_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(_policy(min_subject_depth=0.0))

    def test_marginal_band_wider_than_the_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(
                _policy(min_subject_depth=0.6, marginal_depth_band=0.8)
            )

    def test_non_boolean_approval_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(_policy(require_customer_approval="maybe"))


class IdentityAndSubjectTests(unittest.TestCase):
    def test_a_good_plan_identity_reads_back(self):
        identity = validate_plan_identity(_plan())
        self.assertEqual(identity["plan_reference"], "CCP-4471")
        self.assertTrue(identity["approved_by_customer"])

    def test_non_boolean_timing_declaration_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_identity(_plan(issued_before_first_procurement="later"))

    def test_unrecognised_subject_name_refused(self):
        with self.assertRaises(ValueError):
            validate_subject_record(
                {
                    "subject": "general-good-intentions",
                    "depth": 0.9,
                    "procedure_reference": "X",
                }
            )

    def test_depth_outside_the_unit_interval_refused(self):
        with self.assertRaises(ValueError):
            validate_subject_record(
                {
                    "subject": DERATING_AND_APPLICATION_RULES,
                    "depth": 1.4,
                    "procedure_reference": "X",
                }
            )

    def test_duplicate_subject_refused(self):
        subjects = _subjects()
        subjects.append(dict(subjects[0]))
        with self.assertRaises(ValueError):
            validate_subjects(subjects)

    def test_a_blank_procedure_reference_is_read_as_no_procedure(self):
        record = {
            "subject": DERATING_AND_APPLICATION_RULES,
            "depth": 0.99,
            "procedure_reference": "   ",
        }
        self.assertFalse(subject_is_treated(record))

    def test_a_subject_exactly_on_the_depth_floor_counts(self):
        record = {
            "subject": DERATING_AND_APPLICATION_RULES,
            "depth": 0.6,
            "procedure_reference": "CCP-PROC-06",
        }
        self.assertTrue(subject_is_treated(record, _policy(min_subject_depth=0.6)))


class CoverageTests(unittest.TestCase):
    def test_a_complete_plan_covers_every_subject(self):
        self.assertAlmostEqual(subject_coverage(_subjects()), 1.0, places=9)
        self.assertEqual(missing_subjects(_subjects()), ())
        self.assertEqual(shallow_subjects(_subjects()), ())

    def test_a_dropped_subject_is_named_and_lowers_the_coverage(self):
        subjects = [
            record
            for record in _subjects()
            if record["subject"] != RADIATION_AND_ENVIRONMENT_SUITABILITY
        ]
        self.assertEqual(
            missing_subjects(subjects), (RADIATION_AND_ENVIRONMENT_SUITABILITY,)
        )
        self.assertAlmostEqual(
            subject_coverage(subjects),
            (len(REQUIRED_PLAN_SUBJECTS) - 1) / len(REQUIRED_PLAN_SUBJECTS),
            places=9,
        )

    def test_a_heading_with_no_procedure_is_shallow_not_treated(self):
        subjects = _subjects()
        for record in subjects:
            if record["subject"] == OBSOLESCENCE_AND_LIFETIME_BUY:
                record["procedure_reference"] = ""
        self.assertEqual(shallow_subjects(subjects), (OBSOLESCENCE_AND_LIFETIME_BUY,))

    def test_deleting_a_weak_section_cannot_raise_the_completeness(self):
        subjects = _subjects()
        with_weak = depth_weighted_completeness(subjects)
        without = depth_weighted_completeness(
            [
                record
                for record in subjects
                if record["subject"] != RADIATION_AND_ENVIRONMENT_SUITABILITY
            ]
        )
        self.assertLess(without, with_weak)

    def test_completeness_is_the_mean_over_the_full_required_list(self):
        expected = sum(DEPTHS.values()) / len(REQUIRED_PLAN_SUBJECTS)
        self.assertAlmostEqual(
            depth_weighted_completeness(_subjects()), expected, places=9
        )

    def test_the_weakest_treated_subject_is_named(self):
        weakest = weakest_treated_subject(_subjects())
        self.assertEqual(weakest["subject"], RADIATION_AND_ENVIRONMENT_SUITABILITY)
        self.assertAlmostEqual(weakest["depth"], 0.75, places=9)

    def test_no_treated_subject_names_nobody(self):
        subjects = _subjects()
        for record in subjects:
            record["procedure_reference"] = ""
        self.assertIsNone(weakest_treated_subject(subjects))

    def test_a_subject_just_above_the_floor_raises_an_advisory(self):
        subjects = _subjects(
            **{RADIATION_AND_ENVIRONMENT_SUITABILITY: 0.65}
        )
        advisories = marginal_depth_advisories(
            subjects, _policy(min_subject_depth=0.6, marginal_depth_band=0.1)
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn(RADIATION_AND_ENVIRONMENT_SUITABILITY, advisories[0])

    def test_a_comfortable_plan_raises_no_advisory(self):
        self.assertEqual(
            marginal_depth_advisories(
                _subjects(), _policy(min_subject_depth=0.5, marginal_depth_band=0.1)
            ),
            (),
        )


class AssessmentTests(unittest.TestCase):
    def test_a_complete_plan_covers_the_class_scope(self):
        result = assess_component_control_plan(_case())
        self.assertEqual(result["verdict"], PLAN_COVERS_CLASS_ONE_SCOPE)
        self.assertAlmostEqual(result["subject_coverage"], 1.0, places=9)
        self.assertEqual(result["plan_reference"], "CCP-4471")

    def test_an_absent_plan_is_not_established(self):
        case = _case()
        del case["plan"]
        result = assess_component_control_plan(case)
        self.assertEqual(result["verdict"], PLAN_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_a_plan_with_no_reference_is_not_established(self):
        result = assess_component_control_plan(_case(plan=_plan(plan_reference="  ")))
        self.assertEqual(result["verdict"], PLAN_NOT_ESTABLISHED)

    def test_a_plan_with_no_issue_label_is_not_established(self):
        result = assess_component_control_plan(_case(plan=_plan(issue="")))
        self.assertEqual(result["verdict"], PLAN_NOT_ESTABLISHED)

    def test_every_missing_subject_is_named_not_only_the_first(self):
        subjects = [
            record
            for record in _subjects()
            if record["subject"]
            not in (
                RADIATION_AND_ENVIRONMENT_SUITABILITY,
                OBSOLESCENCE_AND_LIFETIME_BUY,
                TRACEABILITY_AND_LOT_RECORDS,
            )
        ]
        result = assess_component_control_plan(_case(plan=_plan(subjects=subjects)))
        self.assertEqual(result["verdict"], PLAN_SUBJECT_COVERAGE_SHORT)
        self.assertEqual(len(result["missing_subjects"]), 3)

    def test_a_shallow_subject_shortens_the_coverage(self):
        subjects = _subjects(**{SCREENING_AND_LOT_ACCEPTANCE: 0.2})
        result = assess_component_control_plan(_case(plan=_plan(subjects=subjects)))
        self.assertEqual(result["verdict"], PLAN_SUBJECT_COVERAGE_SHORT)
        self.assertEqual(result["shallow_subjects"], (SCREENING_AND_LOT_ACCEPTANCE,))

    def test_an_unapproved_plan_is_a_draft(self):
        result = assess_component_control_plan(
            _case(plan=_plan(approved_by_customer=False))
        )
        self.assertEqual(result["verdict"], PLAN_NOT_APPROVED)

    def test_approval_may_be_waived_by_policy(self):
        result = assess_component_control_plan(
            _case(plan=_plan(approved_by_customer=False)),
            _policy(require_customer_approval=False),
        )
        self.assertEqual(result["verdict"], PLAN_COVERS_CLASS_ONE_SCOPE)

    def test_a_late_plan_documents_purchases_already_made(self):
        result = assess_component_control_plan(
            _case(plan=_plan(issued_before_first_procurement=False))
        )
        self.assertEqual(result["verdict"], PLAN_ISSUED_AFTER_PROCUREMENT)

    def test_a_plan_with_no_subjects_sequence_refused(self):
        plan = _plan()
        del plan["subjects"]
        with self.assertRaises(ValueError):
            assess_component_control_plan(_case(plan=plan))

    def test_advisories_travel_with_a_passing_verdict(self):
        subjects = _subjects(**{OBSOLESCENCE_AND_LIFETIME_BUY: 0.62})
        result = assess_component_control_plan(
            _case(plan=_plan(subjects=subjects)),
            _policy(min_subject_depth=0.6, marginal_depth_band=0.05),
        )
        self.assertEqual(result["verdict"], PLAN_COVERS_CLASS_ONE_SCOPE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_component_control_plan(["plan"])


if __name__ == "__main__":
    unittest.main()
