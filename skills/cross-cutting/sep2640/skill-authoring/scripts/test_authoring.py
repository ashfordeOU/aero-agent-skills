#!/usr/bin/env python3
"""Gate 3 contract test: SEP-2640 skill authoring logic.

Exercises scripts/authoring_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the pre-publish
conformance check for a new SKILL.md candidate: required top-level
fields, kebab-case name matching the folder, description discipline
(action + use-when + trigger), license Apache-2.0, compliance values,
non-empty standards, boolean gated, metadata version and author.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import authoring_logic as al  # noqa: E402

GOOD_FRONTMATTER = """---
name: demo-leaf
description: "Determine the demo value for the system: compute the result with the action clause, apply the use when clause for the trigger routing, and list trigger keywords for retrieval. Use when the task is a demo determination with the action and use when and trigger clauses. Trigger: demo, determination, action clause, use when, trigger routing."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: sep-2640
    reference-only: true
gated: false
metadata:
  domain: cross-cutting
  subdomain: sep2640
  tags: [demo]
  version: 0.1.0
  author: Aero Agent Skills
---
Body text.
"""


class KebabCaseTest(unittest.TestCase):
    def test_valid_kebab(self):
        self.assertTrue(al.is_kebab_case("skill-authoring"))
        self.assertTrue(al.is_kebab_case("sep2640-leaf-2"))
        self.assertTrue(al.is_kebab_case("x"))

    def test_invalid_shapes(self):
        self.assertFalse(al.is_kebab_case("Skill-Authoring"))
        self.assertFalse(al.is_kebab_case("skill_authoring"))
        self.assertFalse(al.is_kebab_case("skill  authoring"))
        self.assertFalse(al.is_kebab_case("skill--authoring"))
        self.assertFalse(al.is_kebab_case(""))
        self.assertFalse(al.is_kebab_case("-skill"))


class ParseTest(unittest.TestCase):
    def test_parse_good_frontmatter(self):
        fields, body = al.parse_frontmatter(GOOD_FRONTMATTER)
        self.assertEqual(fields["name"], "demo-leaf")
        self.assertEqual(fields["license"], "Apache-2.0")
        self.assertEqual(fields["compliance"], "STANDARDS-REF")
        self.assertIs(fields["gated"], False)
        self.assertEqual(fields["metadata"]["version"], "0.1.0")
        self.assertIn("Body text.", body)

    def test_missing_delimiter_raises(self):
        with self.assertRaises(ValueError):
            al.parse_frontmatter("no frontmatter here")

    def test_unclosed_frontmatter_raises(self):
        with self.assertRaises(ValueError):
            al.parse_frontmatter("---\nname: x\n")


class RequiredFieldsTest(unittest.TestCase):
    def test_good_candidate_has_no_missing(self):
        fields, _ = al.parse_frontmatter(GOOD_FRONTMATTER)
        self.assertEqual(al.missing_required_fields(fields), [])

    def test_missing_each_required_field(self):
        fields, _ = al.parse_frontmatter(GOOD_FRONTMATTER)
        for key in al.REQUIRED_TOP_LEVEL:
            missing = dict(fields)
            del missing[key]
            self.assertIn(key, al.missing_required_fields(missing))


class CheckFunctionsTest(unittest.TestCase):
    def test_check_name_kebab_and_folder(self):
        fields, _ = al.parse_frontmatter(GOOD_FRONTMATTER)
        self.assertEqual(al.check_name(fields, folder_name="demo-leaf"), [])
        problems = al.check_name(fields, folder_name="other-folder")
        self.assertEqual(len(problems), 1)
        self.assertIn("does not match folder", problems[0])

    def test_check_description_passes_and_fails(self):
        fields, _ = al.parse_frontmatter(GOOD_FRONTMATTER)
        self.assertEqual(al.check_description(fields), [])
        bad = dict(fields)
        bad["description"] = "short"
        problems = al.check_description(bad)
        self.assertTrue(any("Use when" in p for p in problems))
        self.assertTrue(any("Trigger" in p for p in problems))

    def test_check_license(self):
        fields, _ = al.parse_frontmatter(GOOD_FRONTMATTER)
        self.assertEqual(al.check_license(fields), [])
        bad = dict(fields)
        bad["license"] = "MIT"
        self.assertEqual(len(al.check_license(bad)), 1)

    def test_check_compliance_values(self):
        fields, _ = al.parse_frontmatter(GOOD_FRONTMATTER)
        self.assertEqual(al.check_compliance(fields), [])
        for value in ("none", "ITAR-GATED", "EAR-GATED"):
            bad = dict(fields)
            bad["compliance"] = value
            self.assertEqual(al.check_compliance(bad), [], value)
        bad = dict(fields)
        bad["compliance"] = "NOT-A-VALUE"
        self.assertEqual(len(al.check_compliance(bad)), 1)

    def test_check_standards(self):
        fields, _ = al.parse_frontmatter(GOOD_FRONTMATTER)
        self.assertEqual(al.check_standards(fields, GOOD_FRONTMATTER), [])
        bad = dict(fields)
        bad["standards"] = []
        self.assertEqual(len(al.check_standards(bad, GOOD_FRONTMATTER)), 1)

    def test_check_gated_boolean(self):
        fields, _ = al.parse_frontmatter(GOOD_FRONTMATTER)
        self.assertEqual(al.check_gated(fields), [])
        bad = dict(fields)
        bad["gated"] = "yes"
        self.assertEqual(len(al.check_gated(bad)), 1)

    def test_check_metadata(self):
        fields, _ = al.parse_frontmatter(GOOD_FRONTMATTER)
        self.assertEqual(al.check_metadata(fields), [])
        bad = dict(fields)
        bad["metadata"] = {"domain": "cross-cutting"}
        self.assertEqual(len(al.check_metadata(bad)), 2)


class ValidateCandidateTest(unittest.TestCase):
    def test_good_candidate_valid(self):
        problems, valid = al.validate_skill_candidate(GOOD_FRONTMATTER, folder_name="demo-leaf")
        self.assertEqual(problems, [])
        self.assertTrue(valid)

    def test_bad_name_makes_invalid(self):
        text = GOOD_FRONTMATTER.replace("name: demo-leaf", "name: Demo_Leaf")
        problems, valid = al.validate_skill_candidate(text, folder_name="demo-leaf")
        self.assertFalse(valid)
        self.assertTrue(any("kebab" in p for p in problems))

    def test_missing_field_makes_invalid(self):
        text = GOOD_FRONTMATTER.replace("gated: false\n", "")
        problems, valid = al.validate_skill_candidate(text, folder_name="demo-leaf")
        self.assertFalse(valid)
        self.assertTrue(any("gated" in p for p in problems))

    def test_template_builds_valid_candidate(self):
        template = al.build_frontmatter_template(
            "demo-leaf",
            "Determine the demo value for the system with the action clause and the "
            "use when clause and the trigger routing: compute the demo result from the "
            "inputs, apply the use when condition for the routing decision, and list the "
            "trigger keywords for retrieval. Use when the task is a demo determination "
            "with the action and use when and trigger clauses for the routing. Trigger: "
            "demo, determination, action clause, use when, trigger routing.",
        )
        text = template + "\n---\nBody.\n"
        problems, valid = al.validate_skill_candidate(text, folder_name="demo-leaf")
        self.assertEqual(problems, [])
        self.assertTrue(valid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
