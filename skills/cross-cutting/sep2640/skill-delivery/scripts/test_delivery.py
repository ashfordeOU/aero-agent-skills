#!/usr/bin/env python3
"""Gate 3 contract test: SEP-2640 skill delivery over MCP.

Exercises scripts/delivery_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a skill package is
deliverable when it carries a conformant SKILL.md (kebab-case name,
description present) at the package root; the SEP-2640 delivery model
serves skills as resources under skill:// URIs with resources/read and
directory listing behind the directoryRead capability; readiness
requires those capabilities. Unknown inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import delivery_logic as dl  # noqa: E402


class PackageCheckTest(unittest.TestCase):
    def test_complete_package_has_no_issues(self):
        issues = dl.check_package(
            ["SKILL.md", "scripts/tool.py"],
            name="analysis",
            description="Use when analyzing.",
        )
        self.assertEqual(issues, [])

    def test_missing_skill_md_is_flagged(self):
        issues = dl.check_package(
            ["scripts/tool.py"],
            name="analysis",
            description="Use when analyzing.",
        )
        self.assertTrue(any("SKILL.md" in i for i in issues))

    def test_bad_name_is_flagged(self):
        issues = dl.check_package(
            ["SKILL.md"],
            name="Analysis Tool",
            description="Use when analyzing.",
        )
        self.assertTrue(any("kebab" in i.lower() for i in issues))

    def test_missing_description_is_flagged(self):
        issues = dl.check_package(
            ["SKILL.md"],
            name="analysis",
            description="",
        )
        self.assertTrue(any("description" in i.lower() for i in issues))

    def test_conformance_helper(self):
        status, issues = dl.package_conformance(
            ["SKILL.md"], name="analysis", description="Use when analyzing."
        )
        self.assertEqual(status, "conformant")
        self.assertEqual(issues, [])


class UriTest(unittest.TestCase):
    def test_skill_uri_shape(self):
        self.assertEqual(
            dl.skill_uri("acme-skills", "avionics/analysis"),
            "skill://acme-skills/avionics/analysis",
        )

    def test_empty_namespace_raises(self):
        with self.assertRaises(ValueError):
            dl.skill_uri("", "avionics/analysis")


class ReadinessTest(unittest.TestCase):
    def test_full_capability_set_is_ready(self):
        ready, missing = dl.delivery_readiness(
            ["skill-uri", "resources-read", "directory-read"]
        )
        self.assertTrue(ready)
        self.assertEqual(missing, [])

    def test_missing_directory_read_blocks(self):
        ready, missing = dl.delivery_readiness(["skill-uri", "resources-read"])
        self.assertFalse(ready)
        self.assertIn("directory-read", missing)


if __name__ == "__main__":
    unittest.main(verbosity=2)
