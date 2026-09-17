"""Contract tests for the Annex A component control plan content audit."""

import unittest

from q60_component_control_plan_drd_logic import (
    ACTIONS_FLOOR,
    COMPLETENESS_TOLERANCE,
    DRD_SECTIONS,
    GROUPS,
    GROUP_FLOOR,
    OVERALL_FLOOR,
    REQUIRED_MILESTONE_ORDER,
    SECTION_STATES,
    STATE_CREDIT,
    VERDICTS,
    assess_component_control_plan,
    group_completeness,
    group_weight,
    mandatory_sections,
    milestone_order_findings,
    missing_mandatory_sections,
    normalize_token,
    overall_completeness,
    plan_verdict,
    sections_in_group,
    validate_milestones,
    validate_section,
    validate_sections,
)

OPTIONAL_TRIM = (
    "definitions-and-abbreviations",
    "supplier-and-subcontractor-flowdown",
    "derating-and-worst-case-policy",
    "traceability-storage-and-handling-control",
)


def _sections(states=None, drop=()):
    """Every required section complete, before the overrides are applied."""
    states = states or {}
    entries = []
    for token in sorted(DRD_SECTIONS):
        if token in drop:
            continue
        entries.append({"section": token, "state": states.get(token, "complete")})
    return entries


def _milestones(**overrides):
    days = {
        "preliminary-declared-list-submission": 30,
        "component-selection-freeze": 90,
        "long-lead-procurement-release": 120,
        "final-declared-list-submission": 200,
        "component-delivery-complete": 400,
    }
    days.update(overrides)
    return [{"milestone": k, "day": v} for k, v in sorted(days.items())]


def _plan(**overrides):
    plan = {
        "document_id": "CCP-A-0007",
        "sections": _sections(),
        "milestones": _milestones(),
    }
    plan.update(overrides)
    return plan


class CatalogueTests(unittest.TestCase):
    def test_token_normalization_is_hyphenated_lower_case(self):
        self.assertEqual(
            normalize_token("Purpose_And Scope"), "purpose-and-scope"
        )

    def test_every_section_belongs_to_a_known_group(self):
        for token, spec in DRD_SECTIONS.items():
            self.assertIn(spec["group"], GROUPS, token)

    def test_every_group_holds_at_least_two_sections(self):
        for group in GROUPS:
            self.assertGreaterEqual(len(sections_in_group(group)), 2, group)

    def test_group_weights_sum_to_the_catalogue_weight(self):
        self.assertAlmostEqual(
            sum(group_weight(g) for g in GROUPS),
            sum(v["weight"] for v in DRD_SECTIONS.values()),
            places=9,
        )

    def test_every_group_carries_a_mandatory_section(self):
        for group in GROUPS:
            self.assertTrue(
                any(t in mandatory_sections() for t in sections_in_group(group)),
                group,
            )

    def test_unknown_group_rejected(self):
        with self.assertRaises(ValueError):
            sections_in_group("finance")

    def test_every_state_carries_a_credit(self):
        for state in SECTION_STATES:
            self.assertIn(state, STATE_CREDIT)

    def test_verdict_vocabulary_is_fixed(self):
        self.assertEqual(
            VERDICTS, ("submittable", "submittable-with-actions", "not-submittable")
        )


class SectionValidationTests(unittest.TestCase):
    def test_a_validated_section_carries_its_group_and_weight(self):
        item = validate_section(
            {"section": "declared-component-list-management", "state": "complete"}
        )
        self.assertEqual(item["group"], "controls")
        self.assertAlmostEqual(item["weight"], 3.0, places=9)
        self.assertTrue(item["mandatory"])

    def test_an_outlined_section_earns_half_credit(self):
        item = validate_section(
            {"section": "pure-tin-and-finish-control", "state": "outline"}
        )
        self.assertAlmostEqual(item["credit"], 0.5, places=9)

    def test_unknown_section_rejected(self):
        with self.assertRaises(ValueError):
            validate_section({"section": "marketing-annex", "state": "complete"})

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_section({"section": "purpose-and-scope", "state": "nearly"})

    def test_non_mapping_section_rejected(self):
        with self.assertRaises(ValueError):
            validate_section(["purpose-and-scope", "complete"])

    def test_unsubmitted_sections_come_back_absent(self):
        validated = validate_sections([])
        self.assertEqual(len(validated), len(DRD_SECTIONS))
        for item in validated.values():
            self.assertEqual(item["state"], "absent")

    def test_duplicate_section_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections(
                [
                    {"section": "purpose-and-scope", "state": "complete"},
                    {"section": "purpose-and-scope", "state": "outline"},
                ]
            )

    def test_non_list_sections_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections({"section": "purpose-and-scope"})


class CompletenessTests(unittest.TestCase):
    def test_a_complete_plan_scores_one_everywhere(self):
        validated = validate_sections(_sections())
        self.assertAlmostEqual(overall_completeness(validated), 1.0, places=9)
        for group, value in group_completeness(validated).items():
            self.assertAlmostEqual(value, 1.0, places=9, msg=group)

    def test_an_empty_plan_scores_zero_everywhere(self):
        validated = validate_sections([])
        self.assertAlmostEqual(overall_completeness(validated), 0.0, places=9)
        for group, value in group_completeness(validated).items():
            self.assertAlmostEqual(value, 0.0, places=9, msg=group)

    def test_group_completeness_covers_every_group(self):
        validated = validate_sections(_sections())
        self.assertEqual(set(group_completeness(validated)), set(GROUPS))

    def test_trimming_the_optional_sections_lands_on_both_floors(self):
        validated = validate_sections(_sections(drop=OPTIONAL_TRIM))
        groups = group_completeness(validated)
        self.assertAlmostEqual(groups["general"], GROUP_FLOOR, places=9)
        self.assertAlmostEqual(overall_completeness(validated), OVERALL_FLOOR, places=9)

    def test_a_weak_group_is_not_hidden_by_a_strong_one(self):
        states = {t: "absent" for t in sections_in_group("schedules")}
        validated = validate_sections(_sections(states=states))
        groups = group_completeness(validated)
        self.assertAlmostEqual(groups["schedules"], 0.0, places=9)
        self.assertAlmostEqual(groups["controls"], 1.0, places=9)
        self.assertGreater(overall_completeness(validated), GROUP_FLOOR)

    def test_empty_mapping_rejected(self):
        with self.assertRaises(ValueError):
            group_completeness({})

    def test_missing_mandatory_listed_when_absent(self):
        validated = validate_sections(_sections(drop=("pure-tin-and-finish-control",)))
        self.assertEqual(
            missing_mandatory_sections(validated), ["pure-tin-and-finish-control"]
        )

    def test_absent_optional_section_is_not_a_mandatory_shortfall(self):
        validated = validate_sections(_sections(drop=OPTIONAL_TRIM))
        self.assertEqual(missing_mandatory_sections(validated), [])


class MilestoneTests(unittest.TestCase):
    def test_a_sensible_schedule_raises_nothing(self):
        self.assertEqual(milestone_order_findings(_milestones()), [])

    def test_every_required_milestone_is_validated(self):
        schedule = validate_milestones(_milestones())
        self.assertEqual(set(schedule), set(REQUIRED_MILESTONE_ORDER))

    def test_a_missing_milestone_is_a_finding(self):
        milestones = [
            m
            for m in _milestones()
            if m["milestone"] != "component-selection-freeze"
        ]
        findings = milestone_order_findings(milestones)
        self.assertIn(
            "milestone-not-committed-component-selection-freeze", findings
        )

    def test_a_backwards_pair_is_a_finding_against_the_later_milestone(self):
        findings = milestone_order_findings(
            _milestones(**{"long-lead-procurement-release": 10})
        )
        self.assertIn(
            "milestone-out-of-sequence-long-lead-procurement-release", findings
        )

    def test_milestones_on_the_same_day_are_allowed(self):
        self.assertEqual(
            milestone_order_findings(_milestones(**{"component-selection-freeze": 30})),
            [],
        )

    def test_findings_come_back_sorted(self):
        findings = milestone_order_findings(
            _milestones(
                **{
                    "component-selection-freeze": 500,
                    "final-declared-list-submission": 10,
                }
            )
        )
        self.assertEqual(findings, sorted(findings))
        self.assertGreater(len(findings), 1)

    def test_unknown_milestone_rejected(self):
        with self.assertRaises(ValueError):
            validate_milestones([{"milestone": "launch-campaign", "day": 5}])

    def test_duplicate_milestone_rejected(self):
        with self.assertRaises(ValueError):
            validate_milestones(
                [
                    {"milestone": "component-selection-freeze", "day": 5},
                    {"milestone": "component-selection-freeze", "day": 6},
                ]
            )

    def test_negative_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_milestones(
                [{"milestone": "component-selection-freeze", "day": -1}]
            )

    def test_non_integer_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_milestones(
                [{"milestone": "component-selection-freeze", "day": 5.5}]
            )

    def test_non_list_milestones_rejected(self):
        with self.assertRaises(ValueError):
            validate_milestones({"milestone": "component-selection-freeze"})


class VerdictTests(unittest.TestCase):
    def test_every_floor_met_with_no_defect_is_submittable(self):
        groups = {g: 1.0 for g in GROUPS}
        self.assertEqual(plan_verdict(groups, 1.0, [], []), "submittable")

    def test_a_group_exactly_on_its_floor_still_clears_it(self):
        groups = {g: 1.0 for g in GROUPS}
        groups["general"] = GROUP_FLOOR
        self.assertEqual(plan_verdict(groups, OVERALL_FLOOR, [], []), "submittable")

    def test_a_group_just_under_its_floor_falls_to_actions(self):
        groups = {g: 1.0 for g in GROUPS}
        groups["organization"] = GROUP_FLOOR - 0.01
        self.assertEqual(
            plan_verdict(groups, 0.95, [], []), "submittable-with-actions"
        )

    def test_every_group_clearing_its_floor_does_not_carry_the_overall_floor(self):
        groups = {g: GROUP_FLOOR for g in GROUPS}
        self.assertEqual(
            plan_verdict(groups, GROUP_FLOOR, [], []), "submittable-with-actions"
        )

    def test_a_mandatory_shortfall_blocks_submittable(self):
        groups = {g: 1.0 for g in GROUPS}
        self.assertEqual(
            plan_verdict(groups, 1.0, ["purpose-and-scope"], []),
            "submittable-with-actions",
        )

    def test_a_schedule_defect_blocks_submittable(self):
        groups = {g: 1.0 for g in GROUPS}
        self.assertEqual(
            plan_verdict(groups, 1.0, [], ["milestone-out-of-sequence-x"]),
            "submittable-with-actions",
        )

    def test_a_plan_under_the_actions_floor_is_not_submittable(self):
        groups = {g: 0.2 for g in GROUPS}
        self.assertEqual(
            plan_verdict(groups, ACTIONS_FLOOR - 0.05, [], []), "not-submittable"
        )

    def test_a_plan_exactly_on_the_actions_floor_still_earns_actions(self):
        groups = {g: 0.6 for g in GROUPS}
        self.assertEqual(
            plan_verdict(groups, ACTIONS_FLOOR, [], []), "submittable-with-actions"
        )

    def test_incomplete_group_mapping_rejected(self):
        with self.assertRaises(ValueError):
            plan_verdict({"controls": 1.0}, 1.0, [], [])

    def test_overall_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            plan_verdict({g: 1.0 for g in GROUPS}, 1.4, [], [])

    def test_the_boundary_tolerance_is_far_below_a_percentage_point(self):
        self.assertLess(COMPLETENESS_TOLERANCE, 1e-6)


class PlanAuditTests(unittest.TestCase):
    def test_a_complete_plan_is_submittable(self):
        result = assess_component_control_plan(_plan())
        self.assertEqual(result["verdict"], "submittable")
        self.assertTrue(result["submittable_as_drafted"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["actions"], [])

    def test_the_optional_trim_is_still_submittable(self):
        result = assess_component_control_plan(
            _plan(sections=_sections(drop=OPTIONAL_TRIM))
        )
        self.assertAlmostEqual(
            result["overall_completeness"], OVERALL_FLOOR, places=9
        )
        self.assertEqual(result["weak_groups"], [])
        self.assertEqual(result["verdict"], "submittable")

    def test_a_hollow_organization_group_is_named(self):
        states = {t: "absent" for t in sections_in_group("organization")}
        result = assess_component_control_plan(_plan(sections=_sections(states=states)))
        self.assertIn("organization", result["weak_groups"])
        self.assertIn("deepen-the-organization-group-to-its-floor", result["actions"])
        self.assertNotEqual(result["verdict"], "submittable")

    def test_a_missing_mandatory_section_raises_an_action(self):
        result = assess_component_control_plan(
            _plan(sections=_sections(drop=("electrostatic-discharge-control",)))
        )
        self.assertIn("electrostatic-discharge-control", result["missing_mandatory"])
        self.assertIn(
            "write-the-missing-section-electrostatic-discharge-control",
            result["actions"],
        )

    def test_a_backwards_schedule_blocks_a_complete_plan(self):
        result = assess_component_control_plan(
            _plan(milestones=_milestones(**{"final-declared-list-submission": 5}))
        )
        self.assertEqual(result["verdict"], "submittable-with-actions")
        self.assertTrue(result["schedule_findings"])
        self.assertAlmostEqual(result["overall_completeness"], 1.0, places=9)

    def test_an_outline_only_plan_is_not_submittable(self):
        states = {t: "outline" for t in DRD_SECTIONS}
        result = assess_component_control_plan(_plan(sections=_sections(states=states)))
        self.assertAlmostEqual(result["overall_completeness"], 0.5, places=9)
        self.assertEqual(result["verdict"], "not-submittable")

    def test_an_empty_plan_is_not_submittable(self):
        result = assess_component_control_plan(_plan(sections=[]))
        self.assertEqual(result["verdict"], "not-submittable")
        self.assertEqual(
            sorted(result["missing_mandatory"]), sorted(mandatory_sections())
        )

    def test_blank_document_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_component_control_plan(_plan(document_id="  "))

    def test_missing_key_rejected(self):
        plan = _plan()
        del plan["milestones"]
        with self.assertRaises(ValueError):
            assess_component_control_plan(plan)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_component_control_plan(["CCP-A-0007"])

    def test_every_required_section_appears_in_the_result(self):
        result = assess_component_control_plan(_plan(sections=[]))
        self.assertEqual(set(result["sections"]), set(DRD_SECTIONS))

    def test_verdict_is_always_from_the_fixed_vocabulary(self):
        for state in SECTION_STATES:
            states = {t: state for t in DRD_SECTIONS}
            result = assess_component_control_plan(
                _plan(sections=_sections(states=states))
            )
            self.assertIn(result["verdict"], VERDICTS)


if __name__ == "__main__":
    unittest.main()
