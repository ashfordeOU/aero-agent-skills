#!/usr/bin/env python3
"""The stdlib front-matter reader, graded against PyYAML where available.

A parser tested only against its own expectations is graded by itself.  Where
PyYAML happens to be importable in the developer environment, these tests
compare this module's answer to PyYAML's answer over real corpus files, which
is an oracle that does not share the expression.  Where it is absent the
cross-check SKIPS rather than passing on nothing: a green that proves nothing
is worse than a skip that says so.
"""

import os
import sys
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from evidence import frontmatter, standards  # noqa: E402

# tests/ -> evidence/ -> tools/ -> the repository root.  Three dirnames lands
# on tools/, which is where the package is imported FROM; the corpus is one
# level above that, and getting it wrong turns every corpus test into a skip
# that still reports OK.
TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
SKILLS = os.path.join(REPO_ROOT, "skills")
STANDARDS_MAP = os.path.join(REPO_ROOT, "standards-map.yaml")

try:
    import yaml  # noqa: F401

    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


def sample_skill_files(limit=40):
    found = []
    if not os.path.isdir(SKILLS):
        return found
    for dirpath, dirnames, filenames in os.walk(SKILLS):
        dirnames[:] = sorted(dirnames)
        if "SKILL.md" in filenames:
            found.append(os.path.join(dirpath, "SKILL.md"))
        if len(found) >= limit:
            break
    return sorted(found)[:limit]


class ParserTest(unittest.TestCase):
    def test_scalars_lists_and_nested_mappings(self):
        text = (
            "---\n"
            "name: demo-leaf\n"
            'description: "Use when: a colon, a \'quote\', and commas."\n'
            "gated: false\n"
            "count: 7\n"
            "tags: [a, b, c]\n"
            "standards:\n"
            "  - id: demo-std\n"
            "    reference-only: true\n"
            "  - id: other-std\n"
            "metadata:\n"
            "  version: 0.1.0\n"
            "  author: Fixture\n"
            "---\n"
            "body line\n"
        )
        parsed, body = frontmatter.parse(text)
        self.assertEqual(parsed["name"], "demo-leaf")
        self.assertEqual(parsed["description"], "Use when: a colon, a 'quote', and commas.")
        self.assertIs(parsed["gated"], False)
        self.assertEqual(parsed["count"], 7)
        self.assertEqual(parsed["tags"], ["a", "b", "c"])
        self.assertEqual(
            parsed["standards"],
            [{"id": "demo-std", "reference-only": True}, {"id": "other-std"}],
        )
        self.assertEqual(parsed["metadata"]["author"], "Fixture")
        self.assertEqual(body.strip(), "body line")

    def test_unclosed_front_matter_is_an_error(self):
        with self.assertRaises(frontmatter.FrontmatterError):
            frontmatter.parse("---\nname: x\nno closing fence\n")

    def test_missing_front_matter_is_an_error(self):
        with self.assertRaises(frontmatter.FrontmatterError):
            frontmatter.parse("# just a heading\n")


@unittest.skipUnless(HAVE_YAML, "PyYAML is not importable; cross-check skipped")
@unittest.skipUnless(os.path.isdir(SKILLS), "the corpus is not present")
class CrossCheckTest(unittest.TestCase):
    def test_agrees_with_pyyaml_on_real_skill_files(self):
        import yaml

        files = sample_skill_files()
        self.assertTrue(files, "no SKILL.md sampled")
        for path in files:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            mine, _body = frontmatter.parse(text)
            head, _ = frontmatter.split(text)
            theirs = yaml.safe_load(head)
            for key in ("name", "description", "license", "compliance", "gated", "domain", "pack"):
                self.assertEqual(
                    mine.get(key),
                    theirs.get(key),
                    "%s disagreed on %s" % (os.path.relpath(path, REPO_ROOT), key),
                )
            self.assertEqual(
                [s.get("id") for s in (mine.get("standards") or [])],
                [s.get("id") for s in (theirs.get("standards") or [])],
                os.path.relpath(path, REPO_ROOT),
            )

    def test_agrees_with_pyyaml_on_the_standards_map(self):
        import yaml

        with open(STANDARDS_MAP, "r", encoding="utf-8") as fh:
            text = fh.read()
        theirs = yaml.safe_load(text)
        mine, _digest = standards.load_map(REPO_ROOT)
        self.assertEqual(
            sorted(mine), sorted(entry["id"] for entry in theirs["standards"])
        )
        for entry in theirs["standards"]:
            for key in ("name", "family", "publisher", "status", "gated"):
                self.assertEqual(
                    mine[entry["id"]].get(key), entry.get(key), "%s.%s" % (entry["id"], key)
                )


@unittest.skipUnless(os.path.isfile(STANDARDS_MAP), "the standards map is not present")
class EditionBindingTest(unittest.TestCase):
    def test_every_edition_is_explicitly_unbound_rather_than_blank(self):
        entries, _digest = standards.load_map(REPO_ROOT)
        block = standards.in_scope(REPO_ROOT, sorted(entries)[:5])
        self.assertEqual(len(block["in_scope"]), 5)
        for entry in block["in_scope"]:
            self.assertIn("issue", entry)
            self.assertIn("issue_date", entry)
            self.assertIsNone(entry["issue"])
            self.assertIsNone(entry["issue_date"])
            self.assertEqual(entry["edition_binding"], "unbound")
            self.assertTrue(entry["edition_source"])
        self.assertEqual(len(block["edition_gaps"]), 5)

    def test_an_unresolvable_id_is_reported_not_dropped(self):
        block = standards.in_scope(REPO_ROOT, ["no-such-standard"])
        self.assertEqual(block["in_scope"][0]["resolved"], False)
        self.assertEqual(block["in_scope"][0]["edition_binding"], "unresolved")

    def test_the_revision_token_comes_from_the_designation(self):
        self.assertEqual(standards.revision_token("ARP4754A"), "A")
        self.assertEqual(standards.revision_token("DO-178C"), "C")
        self.assertIsNone(standards.revision_token("CS-25"))
        self.assertEqual(standards.designation_of("DO-178C: a title"), "DO-178C")


if __name__ == "__main__":
    unittest.main(verbosity=2)
