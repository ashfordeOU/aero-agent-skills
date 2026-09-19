#!/usr/bin/env python3
"""Detector tests for stale-number-guard.

The guard holds a list of retired count claims -- "330 SKILL.md", "650
tasks", "12 skills" -- and refuses a live document that still states one.
It passed every run it had ever had, which tells you nothing on its own.

It is a shell script that takes a root directory, so each case here builds a
throwaway root, plants one document in it, and runs the real script. No
mock: the thing under test is the thing that ships.

The exemption case matters as much as the failures. The guard has to let a
document say "330 SKILL.md" when the line is marked a planning target,
otherwise the roadmap is unwritable -- and an exemption nobody tests is an
exemption that silently widens.

Run: python3 ops/automation/test_stale_number_guard.py
(unittest writes OK on stderr; capture both streams.)
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
GUARD = _HERE / "stale-number-guard.sh"
EXEMPT = "planning target, not a shipped count"


def run_against(filename, text):
    """Build a one-document root and run the real guard over it."""
    with tempfile.TemporaryDirectory() as root:
        path = os.path.join(root, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        r = subprocess.run(["bash", str(GUARD), root],
                           capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout + r.stderr


class RetiredCounts(unittest.TestCase):

    def test_a_retired_skill_count_is_caught(self):
        rc, out = run_against("README.md", "We ship 12 skills today.\n")
        self.assertNotEqual(rc, 0, out)

    def test_a_retired_skill_md_count_is_caught(self):
        rc, out = run_against("docs/x.md", "The tree holds 330 SKILL.md files.\n")
        self.assertNotEqual(rc, 0, out)

    def test_a_retired_task_ratio_is_caught(self):
        rc, out = run_against("docs/x.md", "Gate 5 runs 650/650 tasks.\n")
        self.assertNotEqual(rc, 0, out)

    def test_a_current_count_is_not_a_finding(self):
        # 3,189 is what the tree actually holds. The guard lists RETIRED
        # numbers; a live one must pass or every accurate doc fails.
        rc, out = run_against("docs/x.md", "The tree holds 3,189 leaf skills.\n")
        self.assertEqual(rc, 0, out)

    def test_a_document_with_no_counts_passes(self):
        rc, out = run_against("docs/x.md", "This paragraph states no counts.\n")
        self.assertEqual(rc, 0, out)


class TheExemption(unittest.TestCase):
    """An untested exemption is how a guard quietly stops guarding."""

    def test_a_marked_planning_target_is_allowed(self):
        rc, out = run_against(
            "README.md",
            "Roadmap: 650 tasks (%s).\n" % EXEMPT)
        self.assertEqual(rc, 0, out)

    def test_the_exemption_does_not_leak_to_the_next_line(self):
        # The marker must exempt ITS line only. If it exempted the file, one
        # roadmap line would silence every stale count in the document.
        rc, out = run_against(
            "README.md",
            "Roadmap: 650 tasks (%s).\nWe ship 12 skills today.\n" % EXEMPT)
        self.assertNotEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
