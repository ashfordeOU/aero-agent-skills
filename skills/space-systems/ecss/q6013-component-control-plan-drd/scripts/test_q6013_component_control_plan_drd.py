#!/usr/bin/env python3
"""Contract tests for the Annex A component control plan data item.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused data-item
policy, a plan that was never submitted, a plan with no reference or
issue, a required section absent, a section drafted with no procedure
behind it, an ownership-bearing section naming no function, an issue that
has outlived its revision interval and an approval milestone the plan was
never taken through.
"""

import unittest

from q6013_component_control_plan_drd_logic import (
    APPROVAL_MILESTONE_OUTSTANDING,
    CRITICAL_DESIGN_REVIEW,
    DEFAULT_PLAN_DRD_POLICY,
    DERATING_AND_APPLICATION_RULES,
    OBSOLESCENCE_AND_ALERT_HANDLING,
    OWNERSHIP_BEARING_SECTIONS,
    PARTS_APPROVAL_BOARD,
    PART_SELECTION_AND_APPROVAL_ROUTE,
    PLAN_ISSUE_OVERDUE,
    PLAN_NOT_APPROVED,
    PLAN_NOT_SUBMITTED,
    PLAN_SUBMITTABLE,
    PRELIMINARY_DESIGN_REVIEW,
    RADIATION_AND_ENVIRONMENT_ASSESSMENT,
    REQUIRED_PLAN_SECTIONS,
    SECTION_COVERAGE_SHORT,
    SECTION_OWNERSHIP_MISSING,
    TRACEABILITY_AND_DOCUMENTATION,
    absent_sections,
    assess_component_control_plan_drd,
    issue_currency,
    issue_is_overdue,
    marginal_currency_advisory,
    outstanding_milestones,
    section_coverage,
    section_index,
    section_is_written,
    unowned_sections,
    unwritten_sections,
    validate_plan_drd_policy,
    validate_plan_identity,
    validate_section_record,
    validate_sections,
)


def _policy(**overrides):
    policy = dict(DEFAULT_PLAN_DRD_POLICY)
    policy.update(overrides)
    return policy


def _sections(drafted=None, procedures=None, functions=None, drop=()):
    drafted_map = drafted or {}
    procedure_map = procedures or {}
    function_map = functions or {}
    records = []
    for index, name in enumerate(REQUIRED_PLAN_SECTIONS):
        if name in drop:
            continue
        default_function = (
            "component-engineering" if name in OWNERSHIP_BEARING_SECTIONS else ""
        )
        records.append(
            {
                "section": name,
                "drafted": drafted_map.get(name, True),
                "procedure_reference": procedure_map.get(
                    name, "CCP-PROC-%02d" % (index + 1)
                ),
                "responsible_function": function_map.get(name, default_function),
            }
        )
    return records


def _plan(**overrides):
    plan = {
        "plan_reference": "CCP-COTS-4410",
        "issue": "issue 2",
        "issue_age_days": 180.0,
        "approved_by_customer": True,
        "sections": _sections(),
        "completed_milestones": [
            PRELIMINARY_DESIGN_REVIEW,
            CRITICAL_DESIGN_REVIEW,
            PARTS_APPROVAL_BOARD,
        ],
    }
    plan.update(overrides)
    return plan


def _case(**overrides):
    case = {"policy": _policy(), "plan": _plan()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_plan_drd_policy(DEFAULT_PLAN_DRD_POLICY),
            DEFAULT_PLAN_DRD_POLICY,
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_drd_policy(["min_section_coverage"])

    def test_coverage_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_drd_policy(_policy(min_section_coverage=1.4))

    def test_non_positive_revision_interval_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_drd_policy(_policy(max_issue_age_days=0.0))

    def test_full_width_marginal_band_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_drd_policy(_policy(marginal_currency_band=1.0))

    def test_unrecognised_milestone_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_drd_policy(_policy(required_milestones=["launch-review"]))

    def test_empty_milestone_list_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_drd_policy(_policy(required_milestones=[]))

    def test_non_boolean_ownership_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_drd_policy(_policy(require_named_ownership="yes"))


class IdentityValidationTests(unittest.TestCase):
    def test_identity_is_read_back(self):
        identity = validate_plan_identity(_plan())
        self.assertEqual(identity["plan_reference"], "CCP-COTS-4410")
        self.assertAlmostEqual(identity["issue_age_days"], 180.0, places=9)

    def test_negative_issue_age_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_identity(_plan(issue_age_days=-1.0))

    def test_non_string_issue_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_identity(_plan(issue=2))

    def test_non_boolean_approval_refused(self):
        with self.assertRaises(ValueError):
            validate_plan_identity(_plan(approved_by_customer="signed"))


class SectionValidationTests(unittest.TestCase):
    def test_unrecognised_section_refused(self):
        with self.assertRaises(ValueError):
            validate_section_record(
                {"section": "packaging-notes", "drafted": True}
            )

    def test_duplicate_section_refused(self):
        sections = _sections()
        sections.append(dict(sections[0]))
        with self.assertRaises(ValueError):
            validate_sections(sections)

    def test_non_boolean_drafted_refused(self):
        with self.assertRaises(ValueError):
            validate_section_record(
                {
                    "section": DERATING_AND_APPLICATION_RULES,
                    "drafted": "yes",
                    "procedure_reference": "P-1",
                }
            )

    def test_blank_procedure_reads_as_unwritten(self):
        record = validate_section_record(
            {
                "section": DERATING_AND_APPLICATION_RULES,
                "drafted": True,
                "procedure_reference": "   ",
            }
        )
        self.assertFalse(section_is_written(record))

    def test_section_index_maps_every_declared_section(self):
        index = section_index(_sections())
        self.assertEqual(len(index), len(REQUIRED_PLAN_SECTIONS))


class CoverageTests(unittest.TestCase):
    def test_full_plan_covers_every_section(self):
        self.assertAlmostEqual(section_coverage(_sections()), 1.0, places=9)

    def test_absent_section_is_named_and_lowers_coverage(self):
        sections = _sections(drop=(OBSOLESCENCE_AND_ALERT_HANDLING,))
        self.assertEqual(absent_sections(sections), (OBSOLESCENCE_AND_ALERT_HANDLING,))
        self.assertAlmostEqual(
            section_coverage(sections),
            (len(REQUIRED_PLAN_SECTIONS) - 1) / float(len(REQUIRED_PLAN_SECTIONS)),
            places=9,
        )

    def test_heading_with_no_procedure_is_unwritten(self):
        sections = _sections(procedures={RADIATION_AND_ENVIRONMENT_ASSESSMENT: ""})
        self.assertEqual(
            unwritten_sections(sections), (RADIATION_AND_ENVIRONMENT_ASSESSMENT,)
        )

    def test_section_missing_its_owner_is_named(self):
        sections = _sections(functions={PART_SELECTION_AND_APPROVAL_ROUTE: ""})
        self.assertEqual(
            unowned_sections(sections), (PART_SELECTION_AND_APPROVAL_ROUTE,)
        )


class CurrencyTests(unittest.TestCase):
    def test_currency_is_the_consumed_share(self):
        self.assertAlmostEqual(issue_currency(182.5, _policy()), 0.5, places=9)

    def test_issue_landing_on_the_interval_is_still_current(self):
        self.assertFalse(issue_is_overdue(365.0, _policy()))

    def test_issue_past_the_interval_is_overdue(self):
        self.assertTrue(issue_is_overdue(400.0, _policy()))

    def test_marginal_band_advises_before_the_date_passes(self):
        self.assertEqual(len(marginal_currency_advisory(340.0, _policy())), 1)

    def test_overdue_issue_carries_no_marginal_advisory(self):
        self.assertEqual(marginal_currency_advisory(400.0, _policy()), ())


class MilestoneTests(unittest.TestCase):
    def test_every_milestone_reached_leaves_nothing_outstanding(self):
        reached = [PRELIMINARY_DESIGN_REVIEW, CRITICAL_DESIGN_REVIEW, PARTS_APPROVAL_BOARD]
        self.assertEqual(outstanding_milestones(reached, _policy()), ())

    def test_missing_milestone_is_named(self):
        reached = [PRELIMINARY_DESIGN_REVIEW, CRITICAL_DESIGN_REVIEW]
        self.assertEqual(
            outstanding_milestones(reached, _policy()), (PARTS_APPROVAL_BOARD,)
        )

    def test_unrecognised_completed_milestone_refused(self):
        with self.assertRaises(ValueError):
            outstanding_milestones(["flight-readiness-review"], _policy())


class AssessmentTests(unittest.TestCase):
    def test_complete_plan_satisfies_the_data_item(self):
        result = assess_component_control_plan_drd(_case())
        self.assertEqual(result["verdict"], PLAN_SUBMITTABLE)
        self.assertEqual(result["findings"], [])

    def test_absent_plan_stops_the_assessment(self):
        result = assess_component_control_plan_drd(_case(plan=None))
        self.assertEqual(result["verdict"], PLAN_NOT_SUBMITTED)

    def test_blank_reference_stops_the_assessment(self):
        result = assess_component_control_plan_drd(_case(plan=_plan(plan_reference="  ")))
        self.assertEqual(result["verdict"], PLAN_NOT_SUBMITTED)

    def test_short_coverage_outranks_the_later_checks(self):
        plan = _plan(sections=_sections(drop=(TRACEABILITY_AND_DOCUMENTATION,)))
        result = assess_component_control_plan_drd(_case(plan=plan))
        self.assertEqual(result["verdict"], SECTION_COVERAGE_SHORT)

    def test_unowned_section_is_its_own_verdict(self):
        plan = _plan(sections=_sections(functions={OBSOLESCENCE_AND_ALERT_HANDLING: ""}))
        result = assess_component_control_plan_drd(_case(plan=plan))
        self.assertEqual(result["verdict"], SECTION_OWNERSHIP_MISSING)

    def test_unapproved_plan_is_reported(self):
        plan = _plan(approved_by_customer=False)
        result = assess_component_control_plan_drd(_case(plan=plan))
        self.assertEqual(result["verdict"], PLAN_NOT_APPROVED)

    def test_overdue_issue_is_reported(self):
        result = assess_component_control_plan_drd(_case(plan=_plan(issue_age_days=500.0)))
        self.assertEqual(result["verdict"], PLAN_ISSUE_OVERDUE)

    def test_outstanding_milestone_is_reported(self):
        plan = _plan(completed_milestones=[PRELIMINARY_DESIGN_REVIEW])
        result = assess_component_control_plan_drd(_case(plan=plan))
        self.assertEqual(result["verdict"], APPROVAL_MILESTONE_OUTSTANDING)

    def test_marginal_issue_still_passes_with_an_advisory(self):
        result = assess_component_control_plan_drd(_case(plan=_plan(issue_age_days=340.0)))
        self.assertEqual(result["verdict"], PLAN_SUBMITTABLE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_plan_with_no_sections_sequence_refused(self):
        plan = _plan()
        del plan["sections"]
        with self.assertRaises(ValueError):
            assess_component_control_plan_drd(_case(plan=plan))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_component_control_plan_drd(["plan"])


if __name__ == "__main__":
    unittest.main()
