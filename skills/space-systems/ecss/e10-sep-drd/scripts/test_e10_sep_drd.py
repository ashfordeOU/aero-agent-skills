#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C Annex D SEP DRD check.

Exercises scripts/e10_sep_drd_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - required SEP content
sections, organisation-interface coverage, task ownership, DRD document
linkage, overall compliance verdict, and ValueError on invalid input.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_sep_drd_logic as sepdrd  # noqa: E402


FULL_DOCUMENT = {
    "introduction": "Purpose and scope of this SEP.",
    "applicable-and-reference-documents": "AD/RD list.",
    "se-organisation": "SE team structure and interfaces.",
    "se-processes": "SE process per lifecycle phase.",
    "se-tasks": "SE task list tied to the WBS.",
    "drd-linkage": "Documents this SEP plans and controls.",
}

FULL_ORG_ROLES = [
    {"role": "lead-se", "interfaces": ["product-assurance", "aiv"]},
    {
        "role": "se-support",
        "interfaces": [
            "risk-management",
            "configuration-management",
            "software-engineering",
        ],
    },
]


class MissingSectionsTest(unittest.TestCase):
    def test_complete_document_has_no_missing_sections(self):
        self.assertEqual(sepdrd.missing_sections(FULL_DOCUMENT), [])

    def test_absent_section_flagged(self):
        doc = dict(FULL_DOCUMENT)
        del doc["se-tasks"]
        self.assertEqual(sepdrd.missing_sections(doc), ["se-tasks"])

    def test_blank_section_flagged(self):
        doc = dict(FULL_DOCUMENT)
        doc["se-processes"] = "   "
        self.assertIn("se-processes", sepdrd.missing_sections(doc))

    def test_order_matches_required_sections(self):
        doc = {}
        self.assertEqual(
            sepdrd.missing_sections(doc), sepdrd.REQUIRED_SEP_SECTIONS
        )

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            sepdrd.missing_sections(["introduction"])


class MissingOrganisationInterfacesTest(unittest.TestCase):
    def test_full_coverage_has_no_missing_interfaces(self):
        self.assertEqual(
            sepdrd.missing_organisation_interfaces(FULL_ORG_ROLES), []
        )

    def test_uncovered_interface_flagged(self):
        roles = [{"role": "lead-se", "interfaces": ["product-assurance"]}]
        missing = sepdrd.missing_organisation_interfaces(roles)
        self.assertIn("aiv", missing)
        self.assertIn("risk-management", missing)

    def test_case_insensitive_interface_tag(self):
        roles = [{"role": "lead-se", "interfaces": ["AIV"]}]
        self.assertNotIn("aiv", sepdrd.missing_organisation_interfaces(roles))

    def test_empty_org_roles_raises(self):
        with self.assertRaises(ValueError):
            sepdrd.missing_organisation_interfaces([])

    def test_malformed_entry_raises(self):
        with self.assertRaises(ValueError):
            sepdrd.missing_organisation_interfaces([{"role": "lead-se"}])

    def test_unknown_interface_tag_raises(self):
        with self.assertRaises(ValueError):
            sepdrd.missing_organisation_interfaces(
                [{"role": "lead-se", "interfaces": ["marketing"]}]
            )


class UnownedTasksTest(unittest.TestCase):
    def test_known_owner_not_flagged(self):
        tasks = [{"task_id": "T1", "owner_role": "lead-se"}]
        self.assertEqual(sepdrd.unowned_tasks(tasks, ["lead-se"]), [])

    def test_unknown_owner_flagged(self):
        tasks = [{"task_id": "T1", "owner_role": "ghost-role"}]
        self.assertEqual(sepdrd.unowned_tasks(tasks, ["lead-se"]), ["T1"])

    def test_empty_tasks_raises(self):
        with self.assertRaises(ValueError):
            sepdrd.unowned_tasks([], ["lead-se"])

    def test_malformed_task_raises(self):
        with self.assertRaises(ValueError):
            sepdrd.unowned_tasks([{"task_id": "T1"}], ["lead-se"])


class DanglingDrdLinksTest(unittest.TestCase):
    def test_known_links_not_flagged(self):
        self.assertEqual(
            sepdrd.dangling_drd_links(["MDD", "SCR"], ["MDD", "SCR", "TP"]), []
        )

    def test_unknown_link_flagged(self):
        self.assertEqual(
            sepdrd.dangling_drd_links(["MDD", "GHOST"], ["MDD", "SCR"]),
            ["GHOST"],
        )

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            sepdrd.dangling_drd_links("MDD", ["MDD"])
        with self.assertRaises(ValueError):
            sepdrd.dangling_drd_links(["MDD"], "MDD")


class SepDrdComplianceTest(unittest.TestCase):
    def test_fully_compliant_document(self):
        verdict = sepdrd.sep_drd_compliance(
            FULL_DOCUMENT,
            FULL_ORG_ROLES,
            [{"task_id": "T1", "owner_role": "lead-se"}],
            ["MDD"],
            ["MDD", "SCR"],
        )
        self.assertEqual(verdict["status"], "sep-drd-compliant")
        self.assertEqual(verdict["missing_sections"], [])
        self.assertEqual(verdict["missing_organisation_interfaces"], [])
        self.assertEqual(verdict["unowned_tasks"], [])
        self.assertEqual(verdict["dangling_drd_links"], [])

    def test_known_textbook_case_multiple_violations(self):
        doc = dict(FULL_DOCUMENT)
        del doc["se-tasks"]
        verdict = sepdrd.sep_drd_compliance(
            doc,
            [{"role": "lead-se", "interfaces": ["product-assurance"]}],
            [{"task_id": "T1", "owner_role": "ghost-role"}],
            ["GHOST-DOC"],
            ["MDD", "SCR"],
        )
        self.assertEqual(verdict["status"], "sep-drd-non-compliant")
        self.assertIn("se-tasks", verdict["missing_sections"])
        self.assertIn("aiv", verdict["missing_organisation_interfaces"])
        self.assertEqual(verdict["unowned_tasks"], ["T1"])
        self.assertEqual(verdict["dangling_drd_links"], ["GHOST-DOC"])

    def test_single_violation_still_non_compliant(self):
        verdict = sepdrd.sep_drd_compliance(
            FULL_DOCUMENT,
            FULL_ORG_ROLES,
            [{"task_id": "T1", "owner_role": "lead-se"}],
            ["GHOST-DOC"],
            ["MDD", "SCR"],
        )
        self.assertEqual(verdict["status"], "sep-drd-non-compliant")
        self.assertEqual(verdict["dangling_drd_links"], ["GHOST-DOC"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
