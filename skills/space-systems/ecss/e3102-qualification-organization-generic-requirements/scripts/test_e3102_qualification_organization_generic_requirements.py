#!/usr/bin/env python3
"""Contract test for the two-phase qualification organization (offline)."""

import copy
import unittest

from e3102_qualification_organization_generic_requirements_logic import (
    DEFAULT_REQUIREMENT_REGISTRY,
    ORGANIZATION_AGREED,
    ORGANIZATION_OPEN,
    PROCUREMENT_ROUTES,
    PRODUCT_CATEGORIES,
    ROLES,
    applicable_requirements,
    audit_assignments,
    audit_disapplications,
    group_by_owner,
    organize_qualification,
    requirement_applies,
    resolve_role,
    validate_registry,
    validate_requirement,
)


def _registry_entry(req_id):
    for record in DEFAULT_REQUIREMENT_REGISTRY:
        if record["id"] == req_id:
            return record
    raise AssertionError("no registry entry %r" % req_id)


def _owners_for(category, route):
    return {
        item["id"]: item["owner"]
        for item in applicable_requirements(category, route)
    }


DEV_CASE = {
    "customer": "prime contractor",
    "supplier": "two-phase equipment house",
    "product_category": "new-development",
    "procurement_route": "full-development-contract",
    "declared_assignments": _owners_for(
        "new-development", "full-development-contract"
    ),
}

CATALOGUE_CASE = {
    "customer": "prime contractor",
    "supplier": "catalogue vendor",
    "product_category": "off-the-shelf",
    "procurement_route": "catalogue-purchase",
    "declared_assignments": _owners_for("off-the-shelf", "catalogue-purchase"),
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class RegistryTests(unittest.TestCase):
    def test_default_registry_validates(self):
        self.assertEqual(
            len(validate_registry(DEFAULT_REQUIREMENT_REGISTRY)),
            len(DEFAULT_REQUIREMENT_REGISTRY),
        )

    def test_every_record_declares_a_known_role(self):
        for record in DEFAULT_REQUIREMENT_REGISTRY:
            self.assertIn(record["base_role"], ROLES)

    def test_empty_registry_rejected(self):
        with self.assertRaises(ValueError):
            validate_registry(())

    def test_duplicate_requirement_id_rejected(self):
        doubled = list(DEFAULT_REQUIREMENT_REGISTRY) + [
            copy.deepcopy(DEFAULT_REQUIREMENT_REGISTRY[0])
        ]
        with self.assertRaises(ValueError):
            validate_registry(doubled)

    def test_record_with_unknown_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_REQUIREMENT_REGISTRY[0])
        broken["categories"] = ("prototype",)
        with self.assertRaises(ValueError):
            validate_requirement(broken)

    def test_record_with_no_route_rejected(self):
        broken = copy.deepcopy(DEFAULT_REQUIREMENT_REGISTRY[0])
        broken["routes"] = ()
        with self.assertRaises(ValueError):
            validate_requirement(broken)

    def test_record_without_a_disapplicable_flag_rejected(self):
        broken = copy.deepcopy(DEFAULT_REQUIREMENT_REGISTRY[0])
        del broken["disapplicable"]
        with self.assertRaises(ValueError):
            validate_requirement(broken)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement("qualification-status-declaration")


class ApplicabilityTests(unittest.TestCase):
    def test_a_universal_duty_applies_everywhere(self):
        record = _registry_entry("qualification-status-declaration")
        for category in PRODUCT_CATEGORIES:
            for route in PROCUREMENT_ROUTES:
                self.assertTrue(requirement_applies(record, category, route))

    def test_development_reporting_does_not_reach_a_catalogue_item(self):
        record = _registry_entry("development-test-reporting")
        self.assertFalse(
            requirement_applies(record, "off-the-shelf", "catalogue-purchase")
        )

    def test_heritage_evidence_is_not_owed_on_a_new_design(self):
        record = _registry_entry("heritage-evidence-submission")
        self.assertFalse(
            requirement_applies(record, "new-development", "full-development-contract")
        )

    def test_a_catalogue_purchase_carries_fewer_duties_than_a_development(self):
        catalogue = applicable_requirements("off-the-shelf", "catalogue-purchase")
        development = applicable_requirements(
            "new-development", "full-development-contract"
        )
        self.assertLess(len(catalogue), len(development))

    def test_unknown_product_category_rejected(self):
        with self.assertRaises(ValueError):
            applicable_requirements("breadboard", "catalogue-purchase")

    def test_unknown_procurement_route_rejected(self):
        with self.assertRaises(ValueError):
            applicable_requirements("off-the-shelf", "handshake")


class RoleResolutionTests(unittest.TestCase):
    def test_a_named_role_is_unchanged_by_the_route(self):
        record = _registry_entry("acceptance-data-package-delivery")
        for route in PROCUREMENT_ROUTES:
            self.assertEqual(resolve_role(record, route), "supplier")

    def test_a_joint_duty_falls_to_the_supplier_on_a_development(self):
        record = _registry_entry("verification-matrix-maintenance")
        self.assertEqual(resolve_role(record, "full-development-contract"), "supplier")

    def test_a_joint_duty_falls_to_the_customer_on_a_catalogue_purchase(self):
        record = _registry_entry("verification-matrix-maintenance")
        self.assertEqual(resolve_role(record, "catalogue-purchase"), "customer")

    def test_a_joint_duty_stays_joint_on_a_recurring_build(self):
        record = _registry_entry("verification-matrix-maintenance")
        self.assertEqual(resolve_role(record, "recurring-build"), "joint")

    def test_grouping_covers_every_active_duty(self):
        resolved = applicable_requirements("new-development", "recurring-build")
        grouped = group_by_owner(resolved)
        total = sum(len(ids) for ids in grouped.values())
        self.assertEqual(total, len(resolved))

    def test_grouping_rejects_an_unknown_owner(self):
        with self.assertRaises(ValueError):
            group_by_owner([{"id": "x", "owner": "subcontractor"}])


class AssignmentAuditTests(unittest.TestCase):
    def test_a_matching_assignment_raises_no_finding(self):
        resolved = applicable_requirements("off-the-shelf", "catalogue-purchase")
        declared = {item["id"]: item["owner"] for item in resolved}
        self.assertEqual(audit_assignments(resolved, declared)["findings"], [])

    def test_a_missing_owner_is_reported_as_unowned(self):
        resolved = applicable_requirements("off-the-shelf", "catalogue-purchase")
        declared = {item["id"]: item["owner"] for item in resolved}
        declared.pop("acceptance-data-package-delivery")
        audit = audit_assignments(resolved, declared)
        self.assertIn("acceptance-data-package-delivery", audit["unowned"])
        self.assertTrue(any("no owner" in f for f in audit["findings"]))

    def test_a_wrong_owner_is_reported(self):
        resolved = applicable_requirements("off-the-shelf", "catalogue-purchase")
        declared = {item["id"]: item["owner"] for item in resolved}
        declared["nonconformance-disposition-authority"] = "supplier"
        audit = audit_assignments(resolved, declared)
        self.assertTrue(any("not the supplier" in f for f in audit["findings"]))

    def test_an_owner_on_an_inapplicable_duty_is_reported(self):
        resolved = applicable_requirements("off-the-shelf", "catalogue-purchase")
        declared = {item["id"]: item["owner"] for item in resolved}
        declared["development-test-reporting"] = "supplier"
        audit = audit_assignments(resolved, declared)
        self.assertTrue(
            any("does not apply to this context" in f for f in audit["findings"])
        )

    def test_non_mapping_assignments_rejected(self):
        resolved = applicable_requirements("off-the-shelf", "catalogue-purchase")
        with self.assertRaises(ValueError):
            audit_assignments(resolved, ["supplier"])


class DisapplicationTests(unittest.TestCase):
    def test_a_disapplicable_duty_drops_against_an_agreement(self):
        resolved = applicable_requirements(
            "new-development", "full-development-contract"
        )
        audit = audit_disapplications(
            resolved, ("development-test-reporting",), "TAILORING-0007"
        )
        self.assertEqual(audit["accepted"], ["development-test-reporting"])
        self.assertEqual(audit["findings"], [])

    def test_a_disapplicable_duty_without_an_agreement_is_a_finding(self):
        resolved = applicable_requirements(
            "new-development", "full-development-contract"
        )
        audit = audit_disapplications(resolved, ("development-test-reporting",))
        self.assertEqual(audit["accepted"], [])
        self.assertTrue(any("no tailoring agreement" in f for f in audit["findings"]))

    def test_a_non_disapplicable_duty_never_drops(self):
        resolved = applicable_requirements(
            "new-development", "full-development-contract"
        )
        audit = audit_disapplications(
            resolved, ("qualification-status-declaration",), "TAILORING-0007"
        )
        self.assertEqual(audit["accepted"], [])
        self.assertTrue(any("may not be dropped" in f for f in audit["findings"]))

    def test_dropping_an_inapplicable_duty_is_a_finding(self):
        resolved = applicable_requirements("off-the-shelf", "catalogue-purchase")
        audit = audit_disapplications(
            resolved, ("development-test-reporting",), "TAILORING-0007"
        )
        self.assertTrue(
            any("does not apply to this context" in f for f in audit["findings"])
        )

    def test_a_blank_disapplied_id_rejected(self):
        resolved = applicable_requirements("off-the-shelf", "catalogue-purchase")
        with self.assertRaises(ValueError):
            audit_disapplications(resolved, ("   ",), "TAILORING-0007")


class OrganizeTests(unittest.TestCase):
    def test_a_fully_assigned_development_is_agreed(self):
        result = organize_qualification(DEV_CASE)
        self.assertEqual(result["verdict"], ORGANIZATION_AGREED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["unowned"], [])

    def test_a_fully_assigned_catalogue_purchase_is_agreed(self):
        result = organize_qualification(CATALOGUE_CASE)
        self.assertEqual(result["verdict"], ORGANIZATION_AGREED)
        self.assertIn(
            "verification-matrix-maintenance", result["owners"]["customer"]
        )

    def test_an_unowned_duty_opens_the_organization(self):
        case = _case(DEV_CASE)
        case["declared_assignments"] = dict(case["declared_assignments"])
        case["declared_assignments"].pop("working-fluid-compatibility-declaration")
        result = organize_qualification(case)
        self.assertEqual(result["verdict"], ORGANIZATION_OPEN)
        self.assertIn(
            "working-fluid-compatibility-declaration", result["unowned"]
        )

    def test_an_agreed_drop_leaves_the_duty_out_of_the_active_set(self):
        case = _case(
            DEV_CASE,
            disapplied=("development-test-reporting",),
            tailoring_agreement="TAILORING-0012",
        )
        result = organize_qualification(case)
        self.assertIn("development-test-reporting", result["applicable"])
        self.assertNotIn("development-test-reporting", result["active"])
        self.assertEqual(result["dropped"], ["development-test-reporting"])

    def test_a_dropped_duty_is_no_longer_grouped_under_an_owner(self):
        case = _case(
            DEV_CASE,
            disapplied=("development-test-reporting",),
            tailoring_agreement="TAILORING-0012",
        )
        result = organize_qualification(case)
        for ids in result["owners"].values():
            self.assertNotIn("development-test-reporting", ids)

    def test_a_missing_customer_name_rejected(self):
        case = _case(DEV_CASE)
        del case["customer"]
        with self.assertRaises(ValueError):
            organize_qualification(case)

    def test_a_blank_supplier_name_rejected(self):
        with self.assertRaises(ValueError):
            organize_qualification(_case(DEV_CASE, supplier="  "))

    def test_an_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            organize_qualification(_case(DEV_CASE, procurement_route="barter"))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            organize_qualification("new-development")

    def test_a_registry_that_covers_nothing_is_rejected(self):
        narrow = (
            {
                "id": "development-test-reporting",
                "subject": "report the development tests that fed the design",
                "categories": ("new-development",),
                "routes": ("full-development-contract",),
                "base_role": "supplier",
                "disapplicable": True,
            },
        )
        with self.assertRaises(ValueError):
            organize_qualification(CATALOGUE_CASE, narrow)


if __name__ == "__main__":
    unittest.main()
