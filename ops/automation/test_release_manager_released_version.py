#!/usr/bin/env python3
"""The version files name a version that has shipped, never one in progress.

Regression for the first-principles review finding FP-17 (2026-09-26): the
files tracked the band the leaf count sat in, so at 3,150 leaves every file
said 1.31.0 while no v1.31.0 tag, Release or npm version existed. The rule
under test: the files carry the last COMPLETED band, which is exactly the
tag release-on-milestone cuts at that count, so the files change only in the
push that completes a band.
"""
import importlib.util
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location(
    "release_manager", os.path.join(REPO, "scripts", "release-manager.py"))
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)

WORKFLOW = os.path.join(REPO, ".github", "workflows",
                        "release-on-milestone.yml")


def tag_the_workflow_cuts(leaves):
    """Highest milestone tag release-on-milestone would have cut by this
    count: v1.m.0 once leaves >= (m + 1) * 100, for m >= 1."""
    cut = [m for m in range(1, (leaves - 1) // 100 + 1)
           if leaves >= (m + 1) * 100]
    return f"1.{cut[-1]}.0" if cut else "1.0.0"


class ReleasedVersion(unittest.TestCase):
    def test_mid_band_names_the_last_release_not_the_band_in_progress(self):
        self.assertEqual(rm.released_version(3150), "1.30.0")
        self.assertNotEqual(rm.released_version(3150), rm.band_version(3150))

    def test_completing_a_band_moves_the_files_to_its_tag(self):
        self.assertEqual(rm.released_version(3199), "1.30.0")
        self.assertEqual(rm.released_version(3200), "1.31.0")
        self.assertEqual(rm.released_version(3299), "1.31.0")
        self.assertEqual(rm.released_version(3300), "1.32.0")

    def test_below_the_first_milestone_is_the_launch_version(self):
        for n in (1, 99, 100, 199):
            self.assertEqual(rm.released_version(n), "1.0.0", n)

    def test_agrees_with_the_tag_the_workflow_cuts_at_every_count(self):
        for n in range(1, 5001):
            self.assertEqual(rm.released_version(n), tag_the_workflow_cuts(n), n)

    def test_the_workflow_still_uses_the_boundary_this_test_models(self):
        text = open(WORKFLOW, encoding="utf-8").read()
        self.assertIn('TAG="v1.${m}.0"', text)
        self.assertIn("BOUNDARY=$(( (m + 1) * 100 ))", text)
        self.assertIn('[ "$LEAVES" -ge "$BOUNDARY" ] || continue', text)

    def test_version_changes_only_at_a_band_boundary(self):
        changes = [n for n in range(2, 5001)
                   if rm.released_version(n) != rm.released_version(n - 1)]
        self.assertTrue(changes)
        self.assertTrue(all(n % 100 == 0 for n in changes), changes[:5])

    def test_the_repo_version_files_name_the_released_version(self):
        leaves, want, pkg = rm.current_version()
        self.assertEqual(pkg, want)
        self.assertEqual(rm.sync_versions(dry=True), [])
        g = open(rm.PLUGIN_GRADLE, encoding="utf-8").read()
        self.assertEqual(re.search(r'version\s*=\s*"([^"]+)"', g).group(1), want)


if __name__ == "__main__":
    unittest.main()
