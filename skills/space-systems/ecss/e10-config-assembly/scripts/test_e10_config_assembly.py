#!/usr/bin/env python3
"""Offline unittest contract for e10_config_assembly_logic (stdlib only)."""

import unittest

from e10_config_assembly_logic import (
    EMI_CONFLICT,
    HAZARD_SEPARATION_REQUIRED,
    MASS_BUDGET_EXCEEDED,
    MISSING_MASS_BUDGET,
    MOUNTING_ZONE_MISMATCH,
    assembly_compliance_report,
    assembly_mass_finding,
    assembly_pairwise_findings,
    functional_grouping_conflict,
    integration_sequence,
    physical_compatibility,
)


def make_ci(id_, mounting_zone="zone_a", hazard_class="none", emi_role="neutral",
            mass_kg=1.0, function_group=None):
    return {
        "id": id_,
        "mounting_zone": mounting_zone,
        "hazard_class": hazard_class,
        "emi_role": emi_role,
        "mass_kg": mass_kg,
        "function_group": function_group,
    }


class PhysicalCompatibilityTests(unittest.TestCase):
    def test_same_zone_neutral_items_are_compatible(self):
        a = make_ci("a")
        b = make_ci("b")
        self.assertEqual(physical_compatibility(a, b), [])

    def test_mismatched_mounting_zone_is_flagged(self):
        a = make_ci("a", mounting_zone="zone_a")
        b = make_ci("b", mounting_zone="zone_b")
        self.assertEqual(physical_compatibility(a, b), [MOUNTING_ZONE_MISMATCH])

    def test_energetic_paired_with_non_energetic_requires_separation(self):
        a = make_ci("a", hazard_class="energetic")
        b = make_ci("b", hazard_class="none")
        self.assertIn(HAZARD_SEPARATION_REQUIRED, physical_compatibility(a, b))

    def test_two_energetic_items_do_not_trigger_hazard_separation(self):
        a = make_ci("a", hazard_class="energetic")
        b = make_ci("b", hazard_class="energetic")
        self.assertNotIn(HAZARD_SEPARATION_REQUIRED, physical_compatibility(a, b))

    def test_sensitive_and_emitter_pair_is_an_emi_conflict(self):
        a = make_ci("a", emi_role="sensitive")
        b = make_ci("b", emi_role="emitter")
        self.assertIn(EMI_CONFLICT, physical_compatibility(a, b))

    def test_two_neutral_items_have_no_emi_conflict(self):
        a = make_ci("a", emi_role="neutral")
        b = make_ci("b", emi_role="neutral")
        self.assertNotIn(EMI_CONFLICT, physical_compatibility(a, b))

    def test_multiple_incompatibility_reasons_all_reported(self):
        a = make_ci("a", mounting_zone="zone_a", hazard_class="energetic", emi_role="sensitive")
        b = make_ci("b", mounting_zone="zone_b", hazard_class="none", emi_role="emitter")
        reasons = physical_compatibility(a, b)
        self.assertEqual(
            set(reasons), {MOUNTING_ZONE_MISMATCH, HAZARD_SEPARATION_REQUIRED, EMI_CONFLICT}
        )

    def test_missing_required_key_raises(self):
        a = {"id": "a"}
        b = make_ci("b")
        with self.assertRaises(ValueError):
            physical_compatibility(a, b)

    def test_unrecognized_hazard_class_raises(self):
        a = make_ci("a", hazard_class="unknown")
        b = make_ci("b")
        with self.assertRaises(ValueError):
            physical_compatibility(a, b)

    def test_negative_mass_raises(self):
        a = make_ci("a", mass_kg=-1.0)
        b = make_ci("b")
        with self.assertRaises(ValueError):
            physical_compatibility(a, b)


class FunctionalGroupingConflictTests(unittest.TestCase):
    def test_same_function_group_and_physically_compatible_is_no_conflict(self):
        a = make_ci("a", function_group="fg1")
        b = make_ci("b", function_group="fg1")
        self.assertFalse(functional_grouping_conflict(a, b))

    def test_same_function_group_but_physically_incompatible_is_a_conflict(self):
        a = make_ci("a", function_group="fg1", mounting_zone="zone_a")
        b = make_ci("b", function_group="fg1", mounting_zone="zone_b")
        self.assertTrue(functional_grouping_conflict(a, b))

    def test_different_function_groups_never_conflict(self):
        a = make_ci("a", function_group="fg1", mounting_zone="zone_a")
        b = make_ci("b", function_group="fg2", mounting_zone="zone_b")
        self.assertFalse(functional_grouping_conflict(a, b))

    def test_unset_function_group_never_conflicts(self):
        a = make_ci("a", function_group=None, mounting_zone="zone_a")
        b = make_ci("b", function_group=None, mounting_zone="zone_b")
        self.assertFalse(functional_grouping_conflict(a, b))


class AssemblyPairwiseFindingsTests(unittest.TestCase):
    def test_fully_compatible_assembly_has_no_findings(self):
        cis = [make_ci("a"), make_ci("b"), make_ci("c")]
        self.assertEqual(assembly_pairwise_findings(cis), [])

    def test_incompatible_pair_is_reported(self):
        cis = [make_ci("a", mounting_zone="zone_a"), make_ci("b", mounting_zone="zone_b")]
        findings = assembly_pairwise_findings(cis)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["finding"], "physical_incompatibility")

    def test_functional_conflict_is_reported_alongside_physical_finding(self):
        cis = [
            make_ci("a", function_group="fg1", mounting_zone="zone_a"),
            make_ci("b", function_group="fg1", mounting_zone="zone_b"),
        ]
        findings = assembly_pairwise_findings(cis)
        kinds = {f["finding"] for f in findings}
        self.assertEqual(kinds, {"physical_incompatibility", "functional_grouping_conflict"})

    def test_duplicate_ci_id_raises(self):
        cis = [make_ci("a"), make_ci("a")]
        with self.assertRaises(ValueError):
            assembly_pairwise_findings(cis)


class AssemblyMassFindingTests(unittest.TestCase):
    def test_within_budget_has_no_finding(self):
        cis = [make_ci("a", mass_kg=2.0), make_ci("b", mass_kg=2.0)]
        self.assertIsNone(assembly_mass_finding("asm1", cis, mass_budget_kg=5.0))

    def test_over_budget_is_flagged(self):
        cis = [make_ci("a", mass_kg=3.0), make_ci("b", mass_kg=3.0)]
        finding = assembly_mass_finding("asm1", cis, mass_budget_kg=5.0)
        self.assertEqual(finding["finding"], MASS_BUDGET_EXCEEDED)
        self.assertEqual(finding["total_mass_kg"], 6.0)

    def test_missing_budget_is_itself_a_finding(self):
        cis = [make_ci("a", mass_kg=1.0)]
        finding = assembly_mass_finding("asm1", cis, mass_budget_kg=None)
        self.assertEqual(finding["finding"], MISSING_MASS_BUDGET)


class IntegrationSequenceTests(unittest.TestCase):
    def test_linear_precedence_orders_correctly(self):
        order = integration_sequence(["asm_c", "asm_a", "asm_b"], [("asm_a", "asm_b"), ("asm_b", "asm_c")])
        self.assertEqual(order, ["asm_a", "asm_b", "asm_c"])

    def test_independent_assemblies_are_ordered_deterministically(self):
        order = integration_sequence(["asm_b", "asm_a"], [])
        self.assertEqual(order, ["asm_a", "asm_b"])

    def test_cycle_raises(self):
        with self.assertRaises(ValueError):
            integration_sequence(["asm_a", "asm_b"], [("asm_a", "asm_b"), ("asm_b", "asm_a")])

    def test_unknown_assembly_in_precedence_raises(self):
        with self.assertRaises(ValueError):
            integration_sequence(["asm_a"], [("asm_a", "asm_z")])


class AssemblyComplianceReportTests(unittest.TestCase):
    def test_compliant_assembly_report(self):
        cis = [make_ci("a", mass_kg=1.0), make_ci("b", mass_kg=1.0)]
        report = assembly_compliance_report("asm1", cis, mass_budget_kg=5.0)
        self.assertEqual(report["pairwise_findings"], [])
        self.assertIsNone(report["mass_finding"])

    def test_noncompliant_assembly_report_carries_both_finding_kinds(self):
        cis = [
            make_ci("a", mounting_zone="zone_a", mass_kg=4.0),
            make_ci("b", mounting_zone="zone_b", mass_kg=4.0),
        ]
        report = assembly_compliance_report("asm1", cis, mass_budget_kg=5.0)
        self.assertTrue(report["pairwise_findings"])
        self.assertEqual(report["mass_finding"]["finding"], MASS_BUDGET_EXCEEDED)


if __name__ == "__main__":
    unittest.main()
