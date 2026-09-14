"""Contract tests for the clause 6.1.2.2 lowest-class plan scope.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused plan policy, a
plan that names neither its own reference nor a host document, a core
subject missing or standing on no procedure, a core subject below the
depth floor, a tailorable subject dropped in silence, tailoring past the
agreement cap, and a plan issued after the first procurement commitment.
"""

import unittest

from q6013_class_3_component_control_plan_logic import (
    APPLICATION_AND_DERATING_RULES,
    CORE_PLAN_SUBJECTS,
    CORE_SUBJECT_COVERAGE_SHORT,
    DEFAULT_PLAN_POLICY,
    EVALUATION_AND_LOT_QUALIFICATION,
    NONCONFORMANCE_AND_DISPOSITION_ROUTE,
    OBSOLESCENCE_AND_LIFETIME_BUY,
    PART_SELECTION_AND_APPROVAL,
    PLAN_COVERS_CLASS_THREE_SCOPE,
    PLAN_ISSUED_AFTER_PROCUREMENT,
    PLAN_NOT_ESTABLISHED,
    PROCUREMENT_SOURCE_AND_AUTHENTICITY,
    RADIATION_AND_ENVIRONMENT_SUITABILITY,
    SCREENING_AND_LOT_ACCEPTANCE,
    TAILORABLE_PLAN_SUBJECTS,
    TAILORING_NOT_AGREED,
    TAILORING_NOT_JUSTIFIED,
    TRACEABILITY_AND_LOT_RECORDS,
    assess_component_control_plan,
    core_depth_weighted_completeness,
    core_subject_coverage,
    justified_tailorings,
    marginal_depth_advisories,
    subject_index,
    subject_is_treated,
    unjustified_tailorings,
    untreated_core_subjects,
    validate_plan_identity,
    validate_plan_policy,
    validate_subject_record,
    validate_subjects,
    weakest_treated_core_subject,
)

CORE_DEPTHS = {
    PART_SELECTION_AND_APPROVAL: 0.80,
    PROCUREMENT_SOURCE_AND_AUTHENTICITY: 0.75,
    APPLICATION_AND_DERATING_RULES: 0.70,
    TRACEABILITY_AND_LOT_RECORDS: 0.65,
    NONCONFORMANCE_AND_DISPOSITION_ROUTE: 0.72,
}


def _policy(**overrides):
    policy = dict(DEFAULT_PLAN_POLICY)
    policy.update(overrides)
    return policy


def _core(**overrides):
    depths = dict(CORE_DEPTHS)
    depths.update(overrides)
    return [
        {
            "subject": name,
            "depth": depths[name],
            "procedure_reference": "CCP3-PROC-%02d" % (index + 1),
            "omission_justification": "",
        }
        for index, name in enumerate(CORE_PLAN_SUBJECTS)
        if name in depths
    ]


def _dropped(name, reason="no flight environment drives this subject"):
    return {
        "subject": name,
        "depth": 0.0,
        "procedure_reference": "",
        "omission_justification": reason,
    }


def _subjects(core_overrides=None, tailorable=None):
    records = _core(**(core_overrides or {}))
    if tailorable is None:
        tailorable = [
            _dropped(EVALUATION_AND_LOT_QUALIFICATION),
            _dropped(SCREENING_AND_LOT_ACCEPTANCE),
            _dropped(RADIATION_AND_ENVIRONMENT_SUITABILITY),
            _dropped(OBSOLESCENCE_AND_LIFETIME_BUY),
        ]
    return records + list(tailorable)


def _plan(**overrides):
    plan = {
        "plan_reference": "CCP3-2210",
        "host_document": "",
        "issue": "issue 1",
        "customer_agreed_tailoring": True,
        "issued_before_first_procurement": True,
        "subjects": _subjects(),
    }
    plan.update(overrides)
    return plan


def _case(**overrides):
    case = {"plan": _plan()}
    case.update(overrides)
    return case


class PlanPolicyValidation(unittest.TestCase):
    def test_default_policy_accepted(self):
        self.assertIs(validate_plan_policy(DEFAULT_PLAN_POLICY), DEFAULT_PLAN_POLICY)

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(["min_core_subject_depth"])

    def test_depth_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(_policy(min_core_subject_depth=1.4))

    def test_zero_depth_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(_policy(min_core_subject_depth=0.0))

    def test_marginal_band_wider_than_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(
                _policy(min_core_subject_depth=0.5, marginal_depth_band=0.6)
            )

    def test_tailoring_cap_above_tailorable_count_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(
                _policy(max_unagreed_tailorings=len(TAILORABLE_PLAN_SUBJECTS) + 1)
            )

    def test_boolean_tailoring_cap_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_policy(_policy(max_unagreed_tailorings=True))


class PlanIdentityValidation(unittest.TestCase):
    def test_standalone_reference_is_the_carrier(self):
        identity = validate_plan_identity(_plan())
        self.assertEqual(identity["carrier"], "CCP3-2210")

    def test_host_document_carries_the_plan_when_no_reference(self):
        identity = validate_plan_identity(
            _plan(plan_reference="", host_document="PA-PLAN-88")
        )
        self.assertEqual(identity["carrier"], "section of PA-PLAN-88")

    def test_neither_reference_nor_host_leaves_no_carrier(self):
        identity = validate_plan_identity(_plan(plan_reference="", host_document=""))
        self.assertEqual(identity["carrier"], "")

    def test_non_boolean_agreement_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_identity(_plan(customer_agreed_tailoring="yes"))

    def test_missing_issue_label_refused(self):
        plan = _plan()
        del plan["issue"]
        with self.assertRaises(ValueError):
            validate_plan_identity(plan)


class SubjectValidation(unittest.TestCase):
    def test_unrecognised_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_subject_record(
                {"subject": "packaging-colour", "depth": 0.9, "procedure_reference": "P"}
            )

    def test_depth_outside_unit_interval_refused(self):
        with self.assertRaises(ValueError):
            validate_subject_record(
                {
                    "subject": PART_SELECTION_AND_APPROVAL,
                    "depth": 1.2,
                    "procedure_reference": "P",
                }
            )

    def test_core_subject_with_omission_justification_refused(self):
        with self.assertRaises(ValueError):
            validate_subject_record(
                {
                    "subject": TRACEABILITY_AND_LOT_RECORDS,
                    "depth": 0.0,
                    "procedure_reference": "",
                    "omission_justification": "not needed at this class",
                }
            )

    def test_duplicate_subject_refused(self):
        records = _core()
        with self.assertRaises(ValueError):
            validate_subjects(records + [records[0]])

    def test_subjects_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_subjects({"subject": PART_SELECTION_AND_APPROVAL})

    def test_subject_index_keys_every_declared_subject(self):
        index = subject_index(_subjects())
        self.assertEqual(len(index), len(CORE_PLAN_SUBJECTS) + len(TAILORABLE_PLAN_SUBJECTS))


class TreatmentDecisions(unittest.TestCase):
    def test_subject_on_a_procedure_above_the_floor_is_treated(self):
        record = _core()[0]
        self.assertTrue(subject_is_treated(record, _policy()))

    def test_subject_named_without_a_procedure_is_untreated(self):
        record = dict(_core()[0], procedure_reference="")
        self.assertFalse(subject_is_treated(record, _policy()))

    def test_subject_exactly_on_the_depth_floor_is_treated(self):
        record = dict(_core()[0], depth=0.5)
        self.assertTrue(subject_is_treated(record, _policy(min_core_subject_depth=0.5)))

    def test_untreated_core_names_every_short_subject(self):
        subjects = _subjects(
            core_overrides={
                APPLICATION_AND_DERATING_RULES: 0.2,
                TRACEABILITY_AND_LOT_RECORDS: 0.1,
            }
        )
        untreated = untreated_core_subjects(subjects, _policy())
        self.assertEqual(
            set(untreated),
            {APPLICATION_AND_DERATING_RULES, TRACEABILITY_AND_LOT_RECORDS},
        )


class CoverageArithmetic(unittest.TestCase):
    def test_full_core_treatment_scores_one(self):
        self.assertAlmostEqual(
            core_subject_coverage(_subjects(), _policy()), 1.0, places=9
        )

    def test_one_missing_core_subject_drops_the_share(self):
        subjects = [
            record
            for record in _subjects()
            if record["subject"] != NONCONFORMANCE_AND_DISPOSITION_ROUTE
        ]
        self.assertAlmostEqual(
            core_subject_coverage(subjects, _policy()), 0.8, places=9
        )

    def test_completeness_counts_a_missing_subject_as_zero(self):
        subjects = [
            record
            for record in _subjects()
            if record["subject"] != NONCONFORMANCE_AND_DISPOSITION_ROUTE
        ]
        expected = (0.80 + 0.75 + 0.70 + 0.65) / 5.0
        self.assertAlmostEqual(
            core_depth_weighted_completeness(subjects, _policy()), expected, places=9
        )

    def test_completeness_ignores_depth_behind_no_procedure(self):
        subjects = _subjects()
        for record in subjects:
            if record["subject"] == PART_SELECTION_AND_APPROVAL:
                record["procedure_reference"] = ""
        expected = (0.75 + 0.70 + 0.65 + 0.72) / 5.0
        self.assertAlmostEqual(
            core_depth_weighted_completeness(subjects, _policy()), expected, places=9
        )

    def test_weakest_treated_core_subject_is_named(self):
        weakest = weakest_treated_core_subject(_subjects(), _policy())
        self.assertEqual(weakest["subject"], TRACEABILITY_AND_LOT_RECORDS)

    def test_weakest_is_none_when_nothing_is_treated(self):
        subjects = _core()
        for record in subjects:
            record["procedure_reference"] = ""
        self.assertIsNone(weakest_treated_core_subject(subjects, _policy()))


class TailoringDecisions(unittest.TestCase):
    def test_every_drop_recorded_is_justified(self):
        self.assertEqual(len(justified_tailorings(_subjects(), _policy())), 4)
        self.assertEqual(unjustified_tailorings(_subjects(), _policy()), ())

    def test_undeclared_tailorable_subject_is_silent(self):
        subjects = _subjects(tailorable=[])
        self.assertEqual(
            set(unjustified_tailorings(subjects, _policy())),
            set(TAILORABLE_PLAN_SUBJECTS),
        )

    def test_declared_shallow_without_reason_is_silent(self):
        bare = {
            "subject": SCREENING_AND_LOT_ACCEPTANCE,
            "depth": 0.1,
            "procedure_reference": "",
            "omission_justification": "",
        }
        subjects = _subjects(tailorable=[bare])
        self.assertIn(SCREENING_AND_LOT_ACCEPTANCE, unjustified_tailorings(subjects, _policy()))

    def test_treated_tailorable_subject_is_neither_dropped_nor_silent(self):
        kept = {
            "subject": SCREENING_AND_LOT_ACCEPTANCE,
            "depth": 0.9,
            "procedure_reference": "CCP3-PROC-11",
            "omission_justification": "",
        }
        subjects = _subjects(tailorable=[kept])
        self.assertNotIn(SCREENING_AND_LOT_ACCEPTANCE, justified_tailorings(subjects, _policy()))
        self.assertNotIn(
            SCREENING_AND_LOT_ACCEPTANCE, unjustified_tailorings(subjects, _policy())
        )


class MarginalAdvisories(unittest.TestCase):
    def test_no_advisory_when_every_core_subject_clears_comfortably(self):
        self.assertEqual(marginal_depth_advisories(_subjects(), _policy()), ())

    def test_core_subject_just_above_the_floor_is_advised_on(self):
        subjects = _subjects(core_overrides={APPLICATION_AND_DERATING_RULES: 0.54})
        advisories = marginal_depth_advisories(
            subjects, _policy(min_core_subject_depth=0.5, marginal_depth_band=0.08)
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn(APPLICATION_AND_DERATING_RULES, advisories[0])


class PlanVerdicts(unittest.TestCase):
    def test_absent_plan_is_not_established(self):
        result = assess_component_control_plan(_case(plan=None))
        self.assertEqual(result["verdict"], PLAN_NOT_ESTABLISHED)

    def test_plan_with_no_carrier_is_not_established(self):
        result = assess_component_control_plan(
            _case(plan=_plan(plan_reference="", host_document=""))
        )
        self.assertEqual(result["verdict"], PLAN_NOT_ESTABLISHED)

    def test_untreated_core_subject_shortens_coverage(self):
        subjects = _subjects(core_overrides={TRACEABILITY_AND_LOT_RECORDS: 0.2})
        result = assess_component_control_plan(
            _case(plan=_plan(subjects=subjects)), _policy()
        )
        self.assertEqual(result["verdict"], CORE_SUBJECT_COVERAGE_SHORT)
        self.assertIn(TRACEABILITY_AND_LOT_RECORDS, result["untreated_core_subjects"])

    def test_silent_drop_is_unjustified_tailoring(self):
        subjects = _subjects(tailorable=[_dropped(EVALUATION_AND_LOT_QUALIFICATION)])
        result = assess_component_control_plan(
            _case(plan=_plan(subjects=subjects)), _policy()
        )
        self.assertEqual(result["verdict"], TAILORING_NOT_JUSTIFIED)
        self.assertEqual(len(result["unjustified_tailorings"]), 3)

    def test_tailoring_past_the_cap_needs_customer_agreement(self):
        result = assess_component_control_plan(
            _case(plan=_plan(customer_agreed_tailoring=False)),
            _policy(max_unagreed_tailorings=2),
        )
        self.assertEqual(result["verdict"], TAILORING_NOT_AGREED)

    def test_tailoring_inside_the_cap_needs_no_agreement(self):
        tailorable = [
            _dropped(EVALUATION_AND_LOT_QUALIFICATION),
            _dropped(SCREENING_AND_LOT_ACCEPTANCE),
            {
                "subject": RADIATION_AND_ENVIRONMENT_SUITABILITY,
                "depth": 0.9,
                "procedure_reference": "CCP3-PROC-12",
                "omission_justification": "",
            },
            {
                "subject": OBSOLESCENCE_AND_LIFETIME_BUY,
                "depth": 0.88,
                "procedure_reference": "CCP3-PROC-13",
                "omission_justification": "",
            },
        ]
        result = assess_component_control_plan(
            _case(
                plan=_plan(
                    customer_agreed_tailoring=False,
                    subjects=_subjects(tailorable=tailorable),
                )
            ),
            _policy(max_unagreed_tailorings=2),
        )
        self.assertEqual(result["verdict"], PLAN_COVERS_CLASS_THREE_SCOPE)

    def test_plan_issued_after_procurement_is_caught_last(self):
        result = assess_component_control_plan(
            _case(plan=_plan(issued_before_first_procurement=False)), _policy()
        )
        self.assertEqual(result["verdict"], PLAN_ISSUED_AFTER_PROCUREMENT)

    def test_compliant_light_plan_passes_with_its_numbers(self):
        result = assess_component_control_plan(_case(), _policy())
        self.assertEqual(result["verdict"], PLAN_COVERS_CLASS_THREE_SCOPE)
        self.assertAlmostEqual(result["core_subject_coverage"], 1.0, places=9)
        self.assertEqual(result["carrier"], "CCP3-2210")

    def test_plan_without_subjects_sequence_refused(self):
        plan = _plan()
        del plan["subjects"]
        with self.assertRaises(ValueError):
            assess_component_control_plan(_case(plan=plan))

    def test_advisories_travel_with_a_passing_verdict(self):
        subjects = _subjects(core_overrides={NONCONFORMANCE_AND_DISPOSITION_ROUTE: 0.53})
        result = assess_component_control_plan(
            _case(plan=_plan(subjects=subjects)),
            _policy(min_core_subject_depth=0.5, marginal_depth_band=0.05),
        )
        self.assertEqual(result["verdict"], PLAN_COVERS_CLASS_THREE_SCOPE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_component_control_plan(["plan"])


if __name__ == "__main__":
    unittest.main()
