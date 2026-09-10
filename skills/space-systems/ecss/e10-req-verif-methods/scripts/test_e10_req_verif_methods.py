#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.2.3.4 verification
method/level assignment.

Exercises scripts/e10_req_verif_methods_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - method selection
follows fixed precedence (physical -> inspection; safety-critical ->
test/analysis; heritage -> review_of_design; else test/analysis);
level assignment defaults to the allocation level and bumps one step
for emergent interaction, capping at system; the verification matrix
covers every requirement id with no duplicates; manual overrides that
leave a safety-critical requirement on review_of_design are flagged.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_req_verif_methods_logic as vm  # noqa: E402


class SelectMethodTest(unittest.TestCase):
    def test_physical_is_inspection_regardless_of_other_flags(self):
        self.assertEqual(
            vm.select_method("physical", test_feasible=False, heritage_evidence=False, safety_critical=True),
            "inspection",
        )

    def test_safety_critical_test_feasible_is_test(self):
        self.assertEqual(
            vm.select_method("performance", test_feasible=True, heritage_evidence=True, safety_critical=True),
            "test",
        )

    def test_safety_critical_test_infeasible_is_analysis(self):
        self.assertEqual(
            vm.select_method("performance", test_feasible=False, heritage_evidence=True, safety_critical=True),
            "analysis",
        )

    def test_heritage_non_safety_critical_is_review_of_design(self):
        self.assertEqual(
            vm.select_method("design", test_feasible=True, heritage_evidence=True, safety_critical=False),
            "review_of_design",
        )

    def test_test_feasible_fallback(self):
        self.assertEqual(
            vm.select_method("functional", test_feasible=True, heritage_evidence=False, safety_critical=False),
            "test",
        )

    def test_analysis_fallback(self):
        self.assertEqual(
            vm.select_method("functional", test_feasible=False, heritage_evidence=False, safety_critical=False),
            "analysis",
        )

    def test_unknown_characteristic_raises(self):
        with self.assertRaises(ValueError):
            vm.select_method("cosmetic", test_feasible=True, heritage_evidence=False, safety_critical=False)


class AssignLevelTest(unittest.TestCase):
    def test_default_stays_at_allocation_level(self):
        self.assertEqual(vm.assign_level("subsystem"), "subsystem")

    def test_emergent_interaction_bumps_one_level(self):
        self.assertEqual(vm.assign_level("subsystem", emergent_interaction=True), "element")

    def test_emergent_interaction_at_system_stays_system(self):
        self.assertEqual(vm.assign_level("system", emergent_interaction=True), "system")

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            vm.assign_level("assembly")


class VerifyRequirementTest(unittest.TestCase):
    def test_full_assignment(self):
        requirement = {
            "id": "REQ-001",
            "characteristic": "functional",
            "test_feasible": True,
            "heritage_evidence": False,
            "safety_critical": False,
            "allocation_level": "equipment",
            "emergent_interaction": True,
        }
        self.assertEqual(
            vm.verify_requirement(requirement),
            {"id": "REQ-001", "method": "test", "level": "subsystem"},
        )

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            vm.verify_requirement({
                "characteristic": "physical",
                "test_feasible": True,
                "heritage_evidence": False,
                "safety_critical": False,
                "allocation_level": "equipment",
            })


class BuildVerificationMatrixTest(unittest.TestCase):
    REQUIREMENTS = [
        {
            "id": "REQ-001",
            "characteristic": "physical",
            "test_feasible": False,
            "heritage_evidence": False,
            "safety_critical": False,
            "allocation_level": "equipment",
        },
        {
            "id": "REQ-002",
            "characteristic": "performance",
            "test_feasible": True,
            "heritage_evidence": False,
            "safety_critical": True,
            "allocation_level": "system",
        },
    ]

    def test_matrix_order_and_content(self):
        matrix = vm.build_verification_matrix(self.REQUIREMENTS)
        self.assertEqual(
            matrix,
            [
                {"id": "REQ-001", "method": "inspection", "level": "equipment"},
                {"id": "REQ-002", "method": "test", "level": "system"},
            ],
        )

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            vm.build_verification_matrix(self.REQUIREMENTS + [self.REQUIREMENTS[0]])

    def test_does_not_mutate_input(self):
        before = [dict(r) for r in self.REQUIREMENTS]
        vm.build_verification_matrix(self.REQUIREMENTS)
        self.assertEqual(self.REQUIREMENTS, before)


class MissingAssignmentsTest(unittest.TestCase):
    def test_detects_gap(self):
        matrix = [{"id": "REQ-001", "method": "test", "level": "system"}]
        self.assertEqual(
            vm.missing_assignments(["REQ-001", "REQ-002", "REQ-003"], matrix),
            ["REQ-002", "REQ-003"],
        )

    def test_no_gap(self):
        matrix = [{"id": "REQ-001", "method": "test", "level": "system"}]
        self.assertEqual(vm.missing_assignments(["REQ-001"], matrix), [])


class ManualOverrideTest(unittest.TestCase):
    MATRIX = [
        {"id": "REQ-001", "method": "test", "level": "system"},
        {"id": "REQ-002", "method": "analysis", "level": "subsystem"},
    ]
    REQUIREMENTS_BY_ID = {
        "REQ-001": {"safety_critical": True},
        "REQ-002": {"safety_critical": False},
    }

    def test_apply_override_does_not_mutate_input(self):
        before = [dict(e) for e in self.MATRIX]
        vm.apply_manual_override(self.MATRIX, {"REQ-001": "review_of_design"})
        self.assertEqual(self.MATRIX, before)

    def test_apply_override_changes_only_targeted_entry(self):
        overridden = vm.apply_manual_override(self.MATRIX, {"REQ-001": "review_of_design"})
        self.assertEqual(overridden[0]["method"], "review_of_design")
        self.assertEqual(overridden[1]["method"], "analysis")

    def test_unknown_override_method_raises(self):
        with self.assertRaises(ValueError):
            vm.apply_manual_override(self.MATRIX, {"REQ-001": "demonstration"})

    def test_find_unsafe_overrides_flags_safety_critical_rod(self):
        overridden = vm.apply_manual_override(self.MATRIX, {"REQ-001": "review_of_design"})
        self.assertEqual(
            vm.find_unsafe_overrides(overridden, self.REQUIREMENTS_BY_ID),
            ["REQ-001"],
        )

    def test_find_unsafe_overrides_clean_matrix(self):
        self.assertEqual(
            vm.find_unsafe_overrides(self.MATRIX, self.REQUIREMENTS_BY_ID),
            [],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
