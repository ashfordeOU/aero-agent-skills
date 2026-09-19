#!/usr/bin/env python3
"""Regression tests for the sync commit-message generator.

Two defects, both found on 2026-09-19 when a sync finally carried enough
leaves to expose them, and both of a kind that only appears AT SCALE:

  1. `| head -N` SIGPIPEs its producer under `set -o pipefail`, killing the
     publish at exit 141. Harmless while a sync added tens of leaves;
     deterministic once one added hundreds.
  2. The subject line counted the TRUNCATED list, so a 672-leaf sync would
     have been committed, permanently, as "add 40 leaf skill(s)".

The publish script already carried a comment about (1) from an earlier
occurrence in a different file. A comment did not stop it recurring. These
tests do.

Every case builds a real git repo and runs the real script over it.

Run: python3 ops/automation/test_gen_sync_commit_msg.py
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEN = HERE / "gen_sync_commit_msg.sh"
REPO_ROOT = HERE.parent.parent


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo)] + list(args),
                          capture_output=True, text=True, timeout=60)


def build_repo(directory, new_leaves, family="space-systems", pack="ecss"):
    """A repo with one committed baseline and `new_leaves` staged additions."""
    git(directory, "init", "--quiet")
    git(directory, "config", "user.email", "t@example.invalid")
    git(directory, "config", "user.name", "t")

    docs = directory / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "metrics.json").write_text(
        '{"leaves": %d, "live_packs": 86, "families": 12}' % (100 + new_leaves),
        encoding="utf-8")
    (directory / "README.md").write_text("baseline\n", encoding="utf-8")
    git(directory, "add", "-A")
    git(directory, "commit", "--quiet", "-m", "baseline")

    for i in range(new_leaves):
        leaf = directory / "skills" / family / pack / ("leaf-%04d" % i)
        leaf.mkdir(parents=True, exist_ok=True)
        (leaf / "SKILL.md").write_text("# leaf %d\n" % i, encoding="utf-8")
    git(directory, "add", "-A")          # the script diffs --cached
    return directory


def run_gen(directory):
    return subprocess.run(["bash", str(GEN), str(directory)],
                          capture_output=True, text=True, timeout=120)


class DoesNotSigpipe(unittest.TestCase):
    """Exit 141 is 128+13. It must never appear, at any size."""

    def _check(self, n):
        with tempfile.TemporaryDirectory() as d:
            build_repo(Path(d), n)
            r = run_gen(Path(d))
        self.assertNotEqual(r.returncode, 141,
                            "SIGPIPE at %d leaves: a pipeline closed early "
                            "and pipefail killed the script" % n)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_a_small_sync(self):
        self._check(5)

    def test_exactly_at_the_display_cap(self):
        self._check(40)

    def test_one_past_the_display_cap(self):
        # The first size at which `head -40` closes the pipe early.
        self._check(41)

    def test_a_large_sync(self):
        # The 2026-09-19 shape: hundreds of leaves in one sync.
        self._check(250)


class CountsTheWholeChange(unittest.TestCase):

    def _subject(self, n):
        with tempfile.TemporaryDirectory() as d:
            build_repo(Path(d), n)
            r = run_gen(Path(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.splitlines()[0], r.stdout

    def test_a_small_sync_counts_exactly(self):
        subject, _ = self._subject(7)
        self.assertIn("add 7 leaf skill(s)", subject)

    def test_a_large_sync_reports_the_real_number_not_the_cap(self):
        # The defect: the subject counted the truncated list, so any sync
        # over the cap was reported AS the cap, in the permanent record.
        subject, _ = self._subject(250)
        self.assertIn("add 250 leaf skill(s)", subject)
        self.assertNotIn("add 40 leaf skill(s)", subject)

    def test_a_truncated_list_says_that_it_is_truncated(self):
        # A capped list that does not declare the cap reads as complete.
        _, out = self._subject(250)
        self.assertIn("more not listed here", out)
        self.assertIn("210 more", out)     # 250 - 40 shown

    def test_an_untruncated_list_makes_no_such_claim(self):
        _, out = self._subject(10)
        self.assertNotIn("more not listed here", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
