#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.6.1 verification
tool classification and qualification-status assignment.

Exercises scripts/e1002_tools_general_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - category
assignment follows fixed precedence (no evidence -> D; safety-critical
-> A/B; mission-critical -> B/C; standard -> C; negligible -> D); the
tool register covers every tool id with no duplicates; manual overrides
that weaken a category below what criticality/corroboration requires
are flagged.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_tools_general_logic as tg  # noqa: E402


class ClassifyToolTypeTest(unittest.TestCase):
    def test_known_type_returned(self):
        self.assertEqual(tg.classify_tool_type("gse"), "gse")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            tg.classify_tool_type("gadget")


class DetermineQualificationCategoryTest(unittest.TestCase):
    def test_no_evidence_is_category_d_regardless_of_criticality(self):
        self.assertEqual(
            tg.determine_qualification_category(False, "safety_critical", independent_corroboration=False),
            "D",
        )

    def test_safety_critical_no_corroboration_is_a(self):
        self.assertEqual(
            tg.determine_qualification_category(True, "safety_critical", independent_corroboration=False),
            "A",
        )

    def test_safety_critical_with_corroboration_is_b(self):
        self.assertEqual(
            tg.determine_qualification_category(True, "safety_critical", independent_corroboration=True),
            "B",
        )

    def test_mission_critical_no_corroboration_is_b(self):
        self.assertEqual(
            tg.determine_qualification_category(True, "mission_critical", independent_corroboration=False),
            "B",
        )

    def test_mission_critical_with_corroboration_is_c(self):
        self.assertEqual(
            tg.determine_qualification_category(True, "mission_critical", independent_corroboration=True),
            "C",
        )

    def test_standard_criticality_is_c(self):
        self.assertEqual(
            tg.determine_qualification_category(True, "standard"),
            "C",
        )

    def test_negligible_criticality_is_d(self):
        self.assertEqual(
            tg.determine_qualification_category(True, "negligible"),
            "D",
        )

    def test_unknown_criticality_raises(self):
        with self.assertRaises(ValueError):
            tg.determine_qualification_category(True, "cosmetic")


class QualificationActionsTest(unittest.TestCase):
    def test_known_category_returns_actions(self):
        self.assertIn("configuration control", tg.qualification_actions("A"))

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            tg.qualification_actions("E")


class ClassifyAndQualifyToolTest(unittest.TestCase):
    def test_full_assignment(self):
        tool = {
            "id": "TOOL-001",
            "tool_type": "software_tool",
            "generates_verification_evidence": True,
            "criticality": "mission_critical",
            "independent_corroboration": False,
        }
        result = tg.classify_and_qualify_tool(tool)
        self.assertEqual(result["id"], "TOOL-001")
        self.assertEqual(result["tool_type"], "software_tool")
        self.assertEqual(result["category"], "B")
        self.assertIn("calibration traceability", result["actions"])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            tg.classify_and_qualify_tool({
                "tool_type": "gse",
                "generates_verification_evidence": True,
                "criticality": "standard",
            })


class BuildToolRegisterTest(unittest.TestCase):
    TOOLS = [
        {
            "id": "TOOL-001",
            "tool_type": "test_equipment",
            "generates_verification_evidence": True,
            "criticality": "safety_critical",
            "independent_corroboration": False,
        },
        {
            "id": "TOOL-002",
            "tool_type": "facility",
            "generates_verification_evidence": False,
            "criticality": "negligible",
        },
    ]

    def test_register_order_and_content(self):
        register = tg.build_tool_register(self.TOOLS)
        self.assertEqual(
            [(entry["id"], entry["category"]) for entry in register],
            [("TOOL-001", "A"), ("TOOL-002", "D")],
        )

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            tg.build_tool_register(self.TOOLS + [self.TOOLS[0]])

    def test_does_not_mutate_input(self):
        before = [dict(t) for t in self.TOOLS]
        tg.build_tool_register(self.TOOLS)
        self.assertEqual(self.TOOLS, before)


class MissingToolClassificationsTest(unittest.TestCase):
    def test_detects_gap(self):
        register = [{"id": "TOOL-001", "tool_type": "gse", "category": "C", "actions": "x"}]
        self.assertEqual(
            tg.missing_tool_classifications(["TOOL-001", "TOOL-002", "TOOL-003"], register),
            ["TOOL-002", "TOOL-003"],
        )

    def test_no_gap(self):
        register = [{"id": "TOOL-001", "tool_type": "gse", "category": "C", "actions": "x"}]
        self.assertEqual(tg.missing_tool_classifications(["TOOL-001"], register), [])


class ManualCategoryOverrideTest(unittest.TestCase):
    REGISTER = [
        {"id": "TOOL-001", "tool_type": "test_equipment", "category": "A", "actions": "x"},
        {"id": "TOOL-002", "tool_type": "software_tool", "category": "C", "actions": "y"},
    ]
    TOOLS_BY_ID = {
        "TOOL-001": {
            "generates_verification_evidence": True,
            "criticality": "safety_critical",
            "independent_corroboration": False,
        },
        "TOOL-002": {
            "generates_verification_evidence": True,
            "criticality": "standard",
        },
    }

    def test_apply_override_does_not_mutate_input(self):
        before = [dict(e) for e in self.REGISTER]
        tg.apply_manual_category_override(self.REGISTER, {"TOOL-001": "D"})
        self.assertEqual(self.REGISTER, before)

    def test_apply_override_changes_only_targeted_entry(self):
        overridden = tg.apply_manual_category_override(self.REGISTER, {"TOOL-001": "D"})
        self.assertEqual(overridden[0]["category"], "D")
        self.assertEqual(overridden[1]["category"], "C")

    def test_unknown_override_category_raises(self):
        with self.assertRaises(ValueError):
            tg.apply_manual_category_override(self.REGISTER, {"TOOL-001": "E"})

    def test_find_understated_categories_flags_weakened_safety_critical(self):
        overridden = tg.apply_manual_category_override(self.REGISTER, {"TOOL-001": "D"})
        self.assertEqual(
            tg.find_understated_categories(overridden, self.TOOLS_BY_ID),
            ["TOOL-001"],
        )

    def test_find_understated_categories_clean_register(self):
        self.assertEqual(
            tg.find_understated_categories(self.REGISTER, self.TOOLS_BY_ID),
            [],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
