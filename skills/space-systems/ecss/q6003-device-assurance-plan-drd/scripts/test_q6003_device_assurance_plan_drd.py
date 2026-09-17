#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-Q-ST-60-03C Annex A device assurance plan DRD.

Exercises scripts/q6003_device_assurance_plan_drd_logic.py (stdlib
unittest, offline). Contract: section coverage, assurance-function
ownership, milestone activity coverage, activity owner resolution,
deliverable linkage, the aggregate verdict, and ValueError on invalid
input.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import q6003_device_assurance_plan_drd_logic as plandrd  # noqa: E402


FULL_PLAN = {key: "content for %s" % key for key in plandrd.REQUIRED_PLAN_SECTIONS}

FULL_ROLES = [
    {"role": "device-design-lead", "functions": ["design-authority", "verification-and-validation"]},
    {
        "role": "device-pa-manager",
        "functions": [
            "product-assurance",
            "configuration-management",
            "procurement-and-supplier-control",
            "customer-interface",
        ],
    },
]

MILESTONES = ["device-srr", "device-pdr", "device-cdr"]

FULL_ACTIVITIES = [
    {"activity_id": "A1", "milestone": "device-srr", "owner_role": "device-pa-manager"},
    {"activity_id": "A2", "milestone": "device-pdr", "owner_role": "device-design-lead"},
    {"activity_id": "A3", "milestone": "device-cdr", "owner_role": "device-pa-manager"},
]

FULL_DELIVERABLES = [
    {"item": item, "issued_at_milestone": "device-cdr"}
    for item in plandrd.REQUIRED_DELIVERABLES
]


def full_spec(**overrides):
    spec = {
        "plan": dict(FULL_PLAN),
        "roles": [dict(r) for r in FULL_ROLES],
        "milestones": list(MILESTONES),
        "activities": [dict(a) for a in FULL_ACTIVITIES],
        "deliverables": [dict(d) for d in FULL_DELIVERABLES],
    }
    spec.update(overrides)
    return spec


class MissingPlanSectionsTest(unittest.TestCase):
    def test_complete_plan_has_no_missing_sections(self):
        self.assertEqual(plandrd.missing_plan_sections(FULL_PLAN), [])

    def test_absent_section_reported(self):
        plan = dict(FULL_PLAN)
        del plan["part-and-material-selection"]
        self.assertEqual(
            plandrd.missing_plan_sections(plan), ["part-and-material-selection"]
        )

    def test_blank_heading_counts_as_absent(self):
        plan = dict(FULL_PLAN)
        plan["reuse-and-heritage-policy"] = "   \n\t"
        self.assertIn("reuse-and-heritage-policy", plandrd.missing_plan_sections(plan))

    def test_empty_plan_returns_every_section_in_drd_order(self):
        self.assertEqual(
            plandrd.missing_plan_sections({}), list(plandrd.REQUIRED_PLAN_SECTIONS)
        )

    def test_non_mapping_plan_raises(self):
        with self.assertRaises(ValueError):
            plandrd.missing_plan_sections(["introduction"])


class UnownedAssuranceFunctionsTest(unittest.TestCase):
    def test_full_coverage_leaves_nothing_unowned(self):
        self.assertEqual(plandrd.unowned_assurance_functions(FULL_ROLES), [])

    def test_uncovered_function_reported(self):
        roles = [{"role": "device-pa-manager", "functions": ["product-assurance"]}]
        unowned = plandrd.unowned_assurance_functions(roles)
        self.assertIn("design-authority", unowned)
        self.assertIn("customer-interface", unowned)
        self.assertNotIn("product-assurance", unowned)

    def test_function_name_matched_without_case_or_space(self):
        roles = [{"role": "device-pa-manager", "functions": ["  Product-Assurance "]}]
        self.assertNotIn("product-assurance", plandrd.unowned_assurance_functions(roles))

    def test_empty_roles_raises(self):
        with self.assertRaises(ValueError):
            plandrd.unowned_assurance_functions([])

    def test_role_without_functions_key_raises(self):
        with self.assertRaises(ValueError):
            plandrd.unowned_assurance_functions([{"role": "device-pa-manager"}])

    def test_unknown_function_name_raises(self):
        with self.assertRaises(ValueError):
            plandrd.unowned_assurance_functions(
                [{"role": "device-pa-manager", "functions": ["marketing"]}]
            )

    def test_blank_role_name_raises(self):
        with self.assertRaises(ValueError):
            plandrd.unowned_assurance_functions(
                [{"role": "  ", "functions": ["product-assurance"]}]
            )


class MilestoneCoverageTest(unittest.TestCase):
    def test_every_milestone_covered(self):
        self.assertEqual(
            plandrd.milestones_without_activities(MILESTONES, FULL_ACTIVITIES), []
        )

    def test_uncovered_milestone_reported_in_declared_order(self):
        activities = [FULL_ACTIVITIES[0]]
        self.assertEqual(
            plandrd.milestones_without_activities(MILESTONES, activities),
            ["device-pdr", "device-cdr"],
        )

    def test_duplicate_milestone_declaration_raises(self):
        with self.assertRaises(ValueError):
            plandrd.milestones_without_activities(
                ["device-srr", "device-srr"], FULL_ACTIVITIES[:1]
            )

    def test_activity_on_undeclared_milestone_raises(self):
        with self.assertRaises(ValueError):
            plandrd.milestones_without_activities(
                MILESTONES,
                [{"activity_id": "A9", "milestone": "device-far", "owner_role": "device-pa-manager"}],
            )

    def test_empty_milestone_list_raises(self):
        with self.assertRaises(ValueError):
            plandrd.milestones_without_activities([], [])


class ActivityOwnerTest(unittest.TestCase):
    def test_known_owners_not_reported(self):
        self.assertEqual(
            plandrd.activities_with_unknown_owner(FULL_ACTIVITIES, FULL_ROLES), []
        )

    def test_unknown_owner_reported(self):
        activities = [
            {"activity_id": "A7", "milestone": "device-srr", "owner_role": "ghost-role"}
        ]
        self.assertEqual(
            plandrd.activities_with_unknown_owner(activities, FULL_ROLES), ["A7"]
        )

    def test_malformed_activity_raises(self):
        with self.assertRaises(ValueError):
            plandrd.activities_with_unknown_owner([{"activity_id": "A7"}], FULL_ROLES)

    def test_non_sequence_activities_raises(self):
        with self.assertRaises(ValueError):
            plandrd.activities_with_unknown_owner("A7", FULL_ROLES)


class DeliverableLinkageTest(unittest.TestCase):
    def test_complete_deliverable_list_is_clean(self):
        record = plandrd.dangling_deliverables(FULL_DELIVERABLES, MILESTONES)
        self.assertEqual(record["missing"], [])
        self.assertEqual(record["duplicated"], [])
        self.assertEqual(record["unknown_milestone"], [])

    def test_missing_deliverable_reported(self):
        record = plandrd.dangling_deliverables(FULL_DELIVERABLES[:-1], MILESTONES)
        self.assertEqual(record["missing"], [plandrd.REQUIRED_DELIVERABLES[-1]])

    def test_duplicated_deliverable_reported_once(self):
        deliverables = FULL_DELIVERABLES + [
            {"item": "device-reuse-file", "issued_at_milestone": "device-pdr"}
        ]
        record = plandrd.dangling_deliverables(deliverables, MILESTONES)
        self.assertEqual(record["duplicated"], ["device-reuse-file"])

    def test_undeclared_issue_milestone_reported(self):
        deliverables = [dict(d) for d in FULL_DELIVERABLES]
        deliverables[0]["issued_at_milestone"] = "device-far"
        record = plandrd.dangling_deliverables(deliverables, MILESTONES)
        self.assertEqual(record["unknown_milestone"], [deliverables[0]["item"]])

    def test_malformed_deliverable_raises(self):
        with self.assertRaises(ValueError):
            plandrd.dangling_deliverables([{"item": "device-reuse-file"}], MILESTONES)


class AggregateVerdictTest(unittest.TestCase):
    def test_complete_plan_is_compliant(self):
        verdict = plandrd.assess_device_assurance_plan_drd(full_spec())
        self.assertTrue(verdict["compliant"])
        self.assertEqual(verdict["disposition"], "plan-drd-compliant")
        self.assertEqual(verdict["findings"], [])

    def test_known_textbook_case_names_every_gap_not_the_first(self):
        plan = dict(FULL_PLAN)
        del plan["nonconformance-and-alert-handling"]
        spec = full_spec(
            plan=plan,
            roles=[{"role": "device-pa-manager", "functions": ["product-assurance"]}],
            activities=[
                {"activity_id": "A1", "milestone": "device-srr", "owner_role": "ghost-role"}
            ],
            deliverables=FULL_DELIVERABLES[:2],
        )
        verdict = plandrd.assess_device_assurance_plan_drd(spec)
        self.assertEqual(verdict["disposition"], "plan-drd-rework")
        self.assertIn("nonconformance-and-alert-handling", verdict["missing_sections"])
        self.assertIn("design-authority", verdict["unowned_functions"])
        self.assertEqual(
            verdict["milestones_without_activities"], ["device-pdr", "device-cdr"]
        )
        self.assertEqual(verdict["activities_with_unknown_owner"], ["A1"])
        self.assertGreater(len(verdict["findings"]), 5)

    def test_single_gap_still_forces_rework(self):
        plan = dict(FULL_PLAN)
        plan["introduction"] = ""
        verdict = plandrd.assess_device_assurance_plan_drd(full_spec(plan=plan))
        self.assertFalse(verdict["compliant"])
        self.assertEqual(verdict["missing_sections"], ["introduction"])
        self.assertEqual(len(verdict["findings"]), 1)

    def test_spec_missing_key_raises(self):
        spec = full_spec()
        del spec["deliverables"]
        with self.assertRaises(ValueError):
            plandrd.assess_device_assurance_plan_drd(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            plandrd.assess_device_assurance_plan_drd(["plan"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
