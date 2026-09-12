#!/usr/bin/env python3
"""Gate test: a release's notes must describe the tree the release TAGS.

Measured 2026-09-11 — v1.8.0 was cut from the dev tree's live count but
tagged on the public mirror's HEAD, which lagged a publish cycle behind.
The shipped artifact holds 830 leaves; the notes it shipped with claimed
"926 verified leaves" under an "Aero Agent Skills — 1.9.0" heading, one
whole band ahead of the tag on the release. Both numbers were read from
this working copy instead of from the tree being tagged.

These tests pin the repaired contract:
  1. the heading names the TAG's version, never the dev tree's band;
  2. the leaf/pack/task line comes from the TAGGED tree's metrics;
  3. cut_release refuses to cut while the public mirror is short of the
     milestone, instead of cutting a release that overstates itself;
  4. cut_release pins the tag to the sha it measured (--target).
"""
import importlib.util
import os
import shutil
import unittest
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANAGER = os.path.join(REPO_ROOT, "scripts", "release-manager.py")


def load_manager():
    """Import release-manager.py with gh resolvable, as the cut path needs."""
    real_which = shutil.which
    with mock.patch.object(shutil, "which",
                           lambda c, *a, **k: "/usr/bin/gh" if c == "gh"
                           else real_which(c, *a, **k)):
        spec = importlib.util.spec_from_file_location("release_manager_notes", MANAGER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


RM = load_manager()

# A tagged tree a full band behind this working copy — the v1.8.0 shape.
TAGGED = {"leaves": 830, "live_packs": 86, "families": 12, "corpus_tasks": 1646}


class ChangelogDescribesTaggedTree(unittest.TestCase):
    def test_heading_names_the_tag_not_the_dev_band(self):
        body = RM.changelog_body(830, TAGGED, "1.8.0", log="")
        self.assertIn("## Aero Agent Skills — 1.8.0", body)
        self.assertNotIn("1.9.0", body)

    def test_counts_come_from_the_tagged_tree(self):
        body = RM.changelog_body(830, TAGGED, "1.8.0", log="")
        self.assertIn("830 verified leaves", body)
        self.assertIn("1646 router tasks", body)

    def test_dev_tree_count_never_leaks_into_the_notes(self):
        dev_leaves, _ = RM.leaf_count()
        body = RM.changelog_body(830, TAGGED, "1.8.0", log="")
        if dev_leaves != 830:
            self.assertNotIn(f"{dev_leaves} verified leaves", body)

    def test_supplied_log_is_used_verbatim(self):
        body = RM.changelog_body(830, TAGGED, "1.8.0", log="abc1234 mirror commit")
        self.assertIn("abc1234 mirror commit", body)
        self.assertIn("### Changes since last release", body)

    def test_empty_log_omits_the_changes_section(self):
        body = RM.changelog_body(830, TAGGED, "1.8.0", log="")
        self.assertNotIn("### Changes since last release", body)

    def test_defaults_still_describe_this_working_copy(self):
        leaves, m = RM.leaf_count()
        body = RM.changelog_body()
        self.assertIn(f"## Aero Agent Skills — {RM.band_version(leaves)}", body)
        self.assertIn(f"{leaves} verified leaves", body)

    def test_packages_section_survives(self):
        body = RM.changelog_body(830, TAGGED, "1.8.0", log="")
        self.assertIn("### Packages", body)
        self.assertIn("aero-agent-skills", body)


class PreviousReleasedTag(unittest.TestCase):
    def test_walks_back_one_minor(self):
        self.assertEqual(RM.previous_released_tag("v1.9.0"), "v1.8.0")
        self.assertEqual(RM.previous_released_tag("v1.1.0"), "v1.0.0")

    def test_rejects_a_non_milestone_tag(self):
        self.assertIsNone(RM.previous_released_tag("v1.8.1"))
        self.assertIsNone(RM.previous_released_tag("jb-v1.3.0"))
        self.assertIsNone(RM.previous_released_tag(None))


class CutRefusesToOverstate(unittest.TestCase):
    def _run_cut(self, public_leaves, dev_leaves=938):
        """cut_release with the milestone due and the mirror at N leaves."""
        calls = []

        def fake_run(cmd, *a, **k):
            calls.append(cmd)
            # `gh release view <tag>` -> not released yet
            if "release" in cmd and "view" in cmd:
                return mock.Mock(returncode=1, stdout="", stderr="not found")
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(RM, "leaf_count",
                               lambda: (dev_leaves, {"leaves": dev_leaves})), \
             mock.patch.object(RM, "public_tree_state",
                               lambda: ("deadbeef", dict(TAGGED, leaves=public_leaves))), \
             mock.patch.object(RM.subprocess, "run", fake_run), \
             mock.patch.object(RM.os.path, "exists", lambda p: False):
            rc = RM.cut_release(dry=False, auto=True)
        return rc, calls

    def test_mirror_short_of_the_milestone_is_not_cut(self):
        rc, calls = self._run_cut(public_leaves=830)   # v1.8.0 needs 900
        self.assertEqual(rc, 0, "a mirror that has not caught up is a wait, not a failure")
        created = [c for c in calls if "release" in c and "create" in c]
        self.assertEqual(created, [], "cut a release the mirror could not back")

    def test_mirror_at_the_milestone_is_cut_and_pinned(self):
        rc, calls = self._run_cut(public_leaves=900)
        created = [c for c in calls if "release" in c and "create" in c]
        self.assertEqual(len(created), 1, "milestone reached but no release created")
        self.assertIn("--target", created[0])
        self.assertIn("deadbeef", created[0],
                      "release must pin the sha whose metrics it just read")

    def test_unreadable_mirror_is_a_loud_failure(self):
        with mock.patch.object(RM, "leaf_count", lambda: (938, {"leaves": 938})), \
             mock.patch.object(RM, "public_tree_state", lambda: (None, None)), \
             mock.patch.object(RM.subprocess, "run",
                               lambda *a, **k: mock.Mock(returncode=1, stdout="", stderr="")), \
             mock.patch.object(RM.os.path, "exists", lambda p: False):
            self.assertEqual(RM.cut_release(dry=False, auto=True), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
