"""Contract tests for the clause 5.1.2.2 class 2 component control plan.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused plan policy, a
plan with no reference or no issue, a heading with nothing behind it, a
reference naming a document but no issue, a subject below the depth floor,
a covered share or weighted completeness under its floor, a plan the
customer was never told about, and a plan issued after the first
procurement commitment.
"""

import unittest

from q6013_class_2_component_control_plan_logic import (
    ABSENT,
    COVERED_BY_REFERENCE,
    COVERED_IN_PLAN,
    DEFAULT_PLAN_POLICY,
    DERATING_AND_APPLICATION_RULES,
    EVALUATION_AND_SCREENING_RULES,
    NONCONFORMANCE_AND_ALERT_HANDLING,
    OBSOLESCENCE_AND_REPLACEMENT_RULES,
    PART_SELECTION_RULES,
    PLAN_COVERS_CLASS_TWO_SCOPE,
    PLAN_ISSUED_AFTER_PROCUREMENT,
    PLAN_NOT_ESTABLISHED,
    PLAN_NOT_NOTIFIED,
    PLAN_SUBJECT_COVERAGE_SHORT,
    PROCUREMENT_SOURCE_RULES,
    REQUIRED_SUBJECTS,
    SHALLOW,
    STATED_ONLY,
    TRACEABILITY_AND_LOT_RECORDS,
    absent_subjects,
    assess_component_control_plan,
    covered_share,
    covered_subjects,
    depth_advisories,
    referenced_subjects,
    shallow_subjects,
    stated_only_subjects,
    subject_disposition,
    validate_plan_identity,
    validate_plan_policy,
    validate_subject_record,
    validate_subjects,
    weakest_covered_subject,
    weighted_completeness,
)


def _policy(**overrides):
    policy = dict(DEFAULT_PLAN_POLICY)
    policy.update(overrides)
    return policy


def _in_plan(subject, depth, procedure="CCP-4"):
    return {
        "subject": subject,
        "depth": depth,
        "covered_by_reference": False,
        "procedure_reference": procedure,
        "referenced_document": "",
        "referenced_issue": "",
    }


def _by_reference(subject, depth, document="PA-PLAN-01", issue="C"):
    return {
        "subject": subject,
        "depth": depth,
        "covered_by_reference": True,
        "procedure_reference": "",
        "referenced_document": document,
        "referenced_issue": issue,
    }


def _subjects():
    return [
        _in_plan(PART_SELECTION_RULES, 0.9, "CCP-4.1"),
        _in_plan(PROCUREMENT_SOURCE_RULES, 0.85, "CCP-4.2"),
        _in_plan(EVALUATION_AND_SCREENING_RULES, 0.8, "CCP-4.3"),
        _in_plan(DERATING_AND_APPLICATION_RULES, 0.75, "CCP-4.4"),
        _by_reference(TRACEABILITY_AND_LOT_RECORDS, 0.7),
        _in_plan(OBSOLESCENCE_AND_REPLACEMENT_RULES, 0.65, "CCP-4.6"),
        _in_plan(NONCONFORMANCE_AND_ALERT_HANDLING, 0.6, "CCP-4.7"),
    ]


def _expected_completeness():
    return (0.9 + 0.85 + 0.8 + 0.75 + 0.65 + 0.6 + 0.7 * 0.8) / len(REQUIRED_SUBJECTS)


def _case(**overrides):
    case = {
        "subjects": _subjects(),
        "plan_reference": "CCP-2026-014",
        "plan_issue": "2",
        "customer_notified": True,
        "issued_before_procurement_commitment": True,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_plan_policy(DEFAULT_PLAN_POLICY), DEFAULT_PLAN_POLICY)

    def test_completeness_floor_above_covered_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(
                _policy(min_covered_share=0.6, min_weighted_completeness=0.8)
            )

    def test_zero_depth_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(_policy(min_subject_depth=0.0))

    def test_zero_reference_credit_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(_policy(referenced_subject_credit=0.0))

    def test_reference_credit_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(_policy(referenced_subject_credit=1.2))

    def test_marginal_band_wider_than_depth_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(
                _policy(min_subject_depth=0.5, marginal_depth_band=0.6)
            )

    def test_non_boolean_notification_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(_policy(require_customer_notification="later"))

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(["min_subject_depth"])


class IdentityTests(unittest.TestCase):
    def test_a_good_identity_reads_back(self):
        identity = validate_plan_identity(_case())
        self.assertEqual(identity["plan_reference"], "CCP-2026-014")
        self.assertEqual(identity["plan_issue"], "2")

    def test_non_string_plan_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_identity(_case(plan_reference=14))

    def test_non_boolean_notification_declaration_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_identity(_case(customer_notified="verbally"))

    def test_non_mapping_identity_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_identity(["plan_reference"])


class SubjectValidationTests(unittest.TestCase):
    def test_a_good_subject_reads_back(self):
        record = validate_subject_record(_in_plan(PART_SELECTION_RULES, 0.8))
        self.assertEqual(record["subject"], PART_SELECTION_RULES)
        self.assertAlmostEqual(record["depth"], 0.8, places=9)

    def test_unrecognised_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_subject_record(_in_plan("parts-vibes-section", 0.8))

    def test_depth_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_subject_record(_in_plan(PART_SELECTION_RULES, 1.4))

    def test_negative_depth_refused(self):
        with self.assertRaises(ValueError):
            validate_subject_record(_in_plan(PART_SELECTION_RULES, -0.2))

    def test_a_subject_both_written_and_referenced_refused(self):
        entry = _by_reference(PART_SELECTION_RULES, 0.8)
        entry["procedure_reference"] = "CCP-4.1"
        with self.assertRaises(ValueError):
            validate_subject_record(entry)

    def test_duplicate_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_subjects(
                [
                    _in_plan(PART_SELECTION_RULES, 0.8),
                    _in_plan(PART_SELECTION_RULES, 0.7),
                ]
            )

    def test_empty_subject_list_refused(self):
        with self.assertRaises(ValueError):
            validate_subjects([])

    def test_non_sequence_subjects_refused(self):
        with self.assertRaises(ValueError):
            validate_subjects({"subject": PART_SELECTION_RULES})


class DispositionTests(unittest.TestCase):
    def test_every_required_subject_appears_in_the_disposition(self):
        self.assertEqual(set(subject_disposition(_subjects())), set(REQUIRED_SUBJECTS))

    def test_a_complete_plan_treats_every_subject(self):
        self.assertAlmostEqual(covered_share(_subjects()), 1.0, places=9)
        self.assertEqual(absent_subjects(_subjects()), ())
        self.assertEqual(stated_only_subjects(_subjects()), ())
        self.assertEqual(shallow_subjects(_subjects()), ())
        self.assertEqual(len(covered_subjects(_subjects())), len(REQUIRED_SUBJECTS))

    def test_a_referenced_subject_is_named_and_credited_below_one(self):
        self.assertEqual(referenced_subjects(_subjects()), (TRACEABILITY_AND_LOT_RECORDS,))
        self.assertEqual(
            subject_disposition(_subjects())[TRACEABILITY_AND_LOT_RECORDS]["state"],
            COVERED_BY_REFERENCE,
        )
        self.assertAlmostEqual(
            weighted_completeness(_subjects()), _expected_completeness(), places=9
        )

    def test_a_reference_with_no_issue_is_a_heading_only(self):
        subjects = _subjects()
        subjects[4] = _by_reference(TRACEABILITY_AND_LOT_RECORDS, 0.7, issue="")
        self.assertEqual(
            subject_disposition(subjects)[TRACEABILITY_AND_LOT_RECORDS]["state"],
            STATED_ONLY,
        )
        self.assertEqual(stated_only_subjects(subjects), (TRACEABILITY_AND_LOT_RECORDS,))

    def test_a_heading_with_no_procedure_is_stated_only(self):
        subjects = _subjects()
        subjects[0] = _in_plan(PART_SELECTION_RULES, 0.9, procedure="   ")
        self.assertEqual(stated_only_subjects(subjects), (PART_SELECTION_RULES,))
        self.assertAlmostEqual(
            covered_share(subjects),
            (len(REQUIRED_SUBJECTS) - 1) / len(REQUIRED_SUBJECTS),
            places=9,
        )

    def test_a_shallow_subject_does_not_count_as_treated(self):
        subjects = _subjects()
        subjects[6] = _in_plan(NONCONFORMANCE_AND_ALERT_HANDLING, 0.2, "CCP-4.7")
        self.assertEqual(shallow_subjects(subjects), (NONCONFORMANCE_AND_ALERT_HANDLING,))
        self.assertEqual(
            subject_disposition(subjects)[NONCONFORMANCE_AND_ALERT_HANDLING]["state"],
            SHALLOW,
        )

    def test_a_subject_exactly_on_the_depth_floor_is_treated(self):
        subjects = _subjects()
        subjects[0] = _in_plan(PART_SELECTION_RULES, 0.5, "CCP-4.1")
        self.assertEqual(
            subject_disposition(subjects)[PART_SELECTION_RULES]["state"],
            COVERED_IN_PLAN,
        )
        self.assertAlmostEqual(covered_share(subjects), 1.0, places=9)

    def test_deleting_a_weak_section_cannot_raise_the_completeness(self):
        base = weighted_completeness(_subjects())
        trimmed = _subjects()[:-1]
        self.assertEqual(absent_subjects(trimmed), (NONCONFORMANCE_AND_ALERT_HANDLING,))
        self.assertEqual(
            subject_disposition(trimmed)[NONCONFORMANCE_AND_ALERT_HANDLING]["state"],
            ABSENT,
        )
        self.assertLess(weighted_completeness(trimmed), base)

    def test_the_weakest_treated_subject_is_named_with_its_depth(self):
        weakest = weakest_covered_subject(_subjects())
        self.assertEqual(weakest[0], NONCONFORMANCE_AND_ALERT_HANDLING)
        self.assertAlmostEqual(weakest[1], 0.6, places=9)

    def test_a_subject_just_above_the_floor_raises_an_advisory(self):
        subjects = _subjects()
        subjects[6] = _in_plan(NONCONFORMANCE_AND_ALERT_HANDLING, 0.52, "CCP-4.7")
        advisories = depth_advisories(subjects)
        self.assertEqual(len(advisories), 1)
        self.assertIn(NONCONFORMANCE_AND_ALERT_HANDLING, advisories[0])

    def test_a_comfortable_plan_raises_no_advisory(self):
        self.assertEqual(depth_advisories(_subjects()), ())


class AssessmentTests(unittest.TestCase):
    def test_a_sound_plan_covers_the_class_scope(self):
        result = assess_component_control_plan(_case())
        self.assertEqual(result["verdict"], PLAN_COVERS_CLASS_TWO_SCOPE)
        self.assertAlmostEqual(result["covered_share"], 1.0, places=9)
        self.assertAlmostEqual(
            result["weighted_completeness"], _expected_completeness(), places=9
        )
        self.assertEqual(
            result["weakest_covered_subject"][0], NONCONFORMANCE_AND_ALERT_HANDLING
        )

    def test_an_absent_plan_is_not_established(self):
        case = _case()
        del case["subjects"]
        result = assess_component_control_plan(case)
        self.assertEqual(result["verdict"], PLAN_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_a_blank_plan_reference_is_not_established(self):
        result = assess_component_control_plan(_case(plan_reference="  "))
        self.assertEqual(result["verdict"], PLAN_NOT_ESTABLISHED)

    def test_a_blank_plan_issue_is_not_established(self):
        result = assess_component_control_plan(_case(plan_issue=""))
        self.assertEqual(result["verdict"], PLAN_NOT_ESTABLISHED)

    def test_every_missing_subject_is_named_not_only_the_first(self):
        result = assess_component_control_plan(_case(subjects=_subjects()[:4]))
        self.assertEqual(result["verdict"], PLAN_SUBJECT_COVERAGE_SHORT)
        self.assertEqual(len(result["absent_subjects"]), 3)

    def test_a_heading_without_a_procedure_shortens_the_coverage(self):
        subjects = _subjects()
        subjects[2] = _in_plan(EVALUATION_AND_SCREENING_RULES, 0.8, procedure="")
        result = assess_component_control_plan(_case(subjects=subjects))
        self.assertEqual(result["verdict"], PLAN_SUBJECT_COVERAGE_SHORT)
        self.assertEqual(
            result["stated_only_subjects"], (EVALUATION_AND_SCREENING_RULES,)
        )

    def test_a_shallow_subject_shortens_the_coverage(self):
        subjects = _subjects()
        subjects[5] = _in_plan(OBSOLESCENCE_AND_REPLACEMENT_RULES, 0.1, "CCP-4.6")
        result = assess_component_control_plan(_case(subjects=subjects))
        self.assertEqual(result["verdict"], PLAN_SUBJECT_COVERAGE_SHORT)
        self.assertEqual(
            result["shallow_subjects"], (OBSOLESCENCE_AND_REPLACEMENT_RULES,)
        )

    def test_a_plan_carried_entirely_by_reference_fails_the_weighted_floor(self):
        subjects = [_by_reference(subject, 0.8) for subject in REQUIRED_SUBJECTS]
        result = assess_component_control_plan(_case(subjects=subjects))
        self.assertEqual(result["verdict"], PLAN_SUBJECT_COVERAGE_SHORT)
        self.assertAlmostEqual(result["covered_share"], 1.0, places=9)
        self.assertAlmostEqual(result["weighted_completeness"], 0.8 * 0.8, places=9)

    def test_an_unnotified_plan_closes_the_assessment(self):
        result = assess_component_control_plan(_case(customer_notified=False))
        self.assertEqual(result["verdict"], PLAN_NOT_NOTIFIED)

    def test_the_notification_requirement_may_be_waived_by_policy(self):
        result = assess_component_control_plan(
            _case(customer_notified=False),
            _policy(require_customer_notification=False),
        )
        self.assertEqual(result["verdict"], PLAN_COVERS_CLASS_TWO_SCOPE)

    def test_a_plan_issued_after_the_commitment_closes_the_assessment(self):
        result = assess_component_control_plan(
            _case(issued_before_procurement_commitment=False)
        )
        self.assertEqual(result["verdict"], PLAN_ISSUED_AFTER_PROCUREMENT)

    def test_advisories_travel_with_a_passing_verdict(self):
        subjects = _subjects()
        subjects[6] = _in_plan(NONCONFORMANCE_AND_ALERT_HANDLING, 0.53, "CCP-4.7")
        result = assess_component_control_plan(_case(subjects=subjects))
        self.assertEqual(result["verdict"], PLAN_COVERS_CLASS_TWO_SCOPE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_component_control_plan(["subjects"])


if __name__ == "__main__":
    unittest.main()
