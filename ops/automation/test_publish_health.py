#!/usr/bin/env python3
"""Detector tests for the publish-health check.

Every verdict gets a case that fires and a neighbouring case that does not.
The point of this check is that a broken publish pipe cannot hide behind a
green tree, so the cases that matter most are the ones asserting it goes RED
-- and the one asserting that "could not check" is not "fine".

Run: python3 ops/automation/test_ph.py
(unittest writes OK on stderr; capture both streams.)
"""

import importlib.util
import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "publish_health", _HERE / "publish-health.py")
ph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ph)


class Drift(unittest.TestCase):
    """The band is the unit: minutes of lag is normal, a band is a defect."""

    def test_identical_counts_are_current(self):
        self.assertEqual(ph.decide(3189, 3189)[0], ph.OK)

    def test_small_lag_inside_the_band_is_tolerated(self):
        # A wave lands on dev and publishes an hour later. Not a defect.
        self.assertEqual(ph.decide(3189, 3150)[0], ph.OK)

    def test_exactly_the_tolerance_is_still_tolerated(self):
        self.assertEqual(ph.decide(3189, 3089, tolerance=100)[0], ph.OK)

    def test_one_past_the_tolerance_is_stale(self):
        self.assertEqual(ph.decide(3190, 3089, tolerance=100)[0], ph.STALE)

    def test_the_real_2026_09_19_outage_is_caught(self):
        # The case this check was written for: 18 hours, three aborts,
        # every dev gate green, nothing reported.
        verdict, drift = ph.decide(3189, 2517)
        self.assertEqual(verdict, ph.STALE)
        self.assertEqual(drift, 672)

    def test_public_ahead_of_dev_is_its_own_verdict(self):
        # Not stale -- something else is wrong (out-of-band push, dev reset).
        # Reporting it as "stale" would send someone to the wrong log.
        verdict, drift = ph.decide(3000, 3100)
        self.assertEqual(verdict, ph.AHEAD)
        self.assertEqual(drift, -100)

    def test_a_missing_count_is_refused_not_defaulted(self):
        # Defaulting an unknown to 0 would read as a catastrophic drift, or
        # worse, as agreement. Neither is honest.
        with self.assertRaises(ValueError):
            ph.decide(3189, None)
        with self.assertRaises(ValueError):
            ph.decide(None, 3189)

    def test_tolerance_is_configurable(self):
        self.assertEqual(ph.decide(3189, 3150, tolerance=10)[0], ph.STALE)


class ExitContract(unittest.TestCase):
    """2 is not a pass."""

    def test_unverifiable_is_not_zero(self):
        # gh absent -> exit 2. The whole point: a check that cannot run must
        # not report success.
        real = ph.gh_bin
        try:
            ph.gh_bin = lambda: None
            self.assertEqual(ph.main([]), 2)
        finally:
            ph.gh_bin = real



class CompareTrees(unittest.TestCase):
    """The comparison that replaced a population count.

    A leaf count said "public is current" through three failed publishes,
    because the change added six FILES and zero LEAVES.
    """

    def test_identical_trees_show_no_drift(self):
        tree = {"a": "1", "b": "2"}
        out = ph.compare_trees(dict(tree), dict(tree))
        self.assertEqual((out["missing"], out["differing"], out["extra"]),
                         ([], [], []))

    def test_a_file_absent_from_public_is_missing(self):
        out = ph.compare_trees({"a": "1", "new": "9"}, {"a": "1"})
        self.assertEqual(out["missing"], ["new"])

    def test_same_path_different_content_is_differing(self):
        out = ph.compare_trees({"a": "1"}, {"a": "2"})
        self.assertEqual(out["differing"], ["a"])

    def test_a_file_only_public_is_extra(self):
        out = ph.compare_trees({}, {"stale": "1"})
        self.assertEqual(out["extra"], ["stale"])

    def test_export_generated_files_are_never_drift(self):
        # .ci-native is tracked in dev AND rewritten at export, so comparing
        # it would report a difference on every run forever.
        out = ph.compare_trees({".ci-native": "1"},
                                           {".ci-native": "2",
                                            ".release-hold": "3"})
        self.assertEqual((out["missing"], out["differing"], out["extra"]),
                         ([], [], []))

    def test_zero_leaves_changed_still_reports_file_drift(self):
        # The exact 2026-09-20 shape: same corpus, new contract files.
        out = ph.compare_trees(
            {"skills/a/b/c/SKILL.md": "1", "ops/contracts/x.json": "2"},
            {"skills/a/b/c/SKILL.md": "1"})
        self.assertEqual(out["missing"], ["ops/contracts/x.json"])


class DecideContent(unittest.TestCase):
    NONE = {"missing": [], "differing": [], "extra": []}
    SOME = {"missing": ["ops/contracts/x.json"], "differing": [], "extra": []}

    def test_no_drift_is_ok(self):
        v, _ = ph.decide_content(
            self.NONE, {"outcome": "ok", "dev_head": "abc"}, "abc")
        self.assertEqual(v, "ok")

    def test_a_failed_attempt_is_broken_even_with_no_drift(self):
        # The publish aborting is a fault whether or not it happens to have
        # left the trees equal.
        v, why = ph.decide_content(
            self.NONE, {"outcome": "failed", "exit_status": 1,
                        "stage": "public-ci-parity"}, "abc")
        self.assertEqual(v, "broken")
        self.assertIn("public-ci-parity", why)

    def test_success_over_this_commit_with_drift_is_broken(self):
        v, why = ph.decide_content(
            self.SOME, {"outcome": "ok", "dev_head": "abc"}, "abc")
        self.assertEqual(v, "broken")
        self.assertIn("reported success", why)

    def test_a_commit_since_the_last_attempt_is_in_flight(self):
        v, _ = ph.decide_content(
            self.SOME, {"outcome": "ok", "dev_head": "older"}, "abc")
        self.assertEqual(v, "in-flight")

    def test_a_held_publish_is_not_a_failure(self):
        # Founder GO absent (78) and lock busy (75) are documented as
        # SKIPPED, not failed.
        for outcome in ("held", "skipped-lock"):
            v, _ = ph.decide_content(
                self.SOME, {"outcome": outcome, "dev_head": "abc"}, "abc")
            self.assertEqual(v, "in-flight", outcome)

    def test_drift_with_no_record_is_unexplained_not_ok(self):
        v, _ = ph.decide_content(self.SOME, None, "abc")
        self.assertEqual(v, "unexplained")

    def test_unexplained_and_broken_both_fail_the_check(self):
        for verdict in ("unexplained", "broken"):
            self.assertIn(verdict, ("unexplained", "broken"))


class ExportExcludes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "export-excludes.txt")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, text):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return self.path

    def test_comments_and_blanks_are_not_pathspecs(self):
        self.assertEqual(
            ph.export_excludes(
                self.write("# why\n\nops/x\n  docs/y.md  # trailing\n")),
            ["ops/x", "docs/y.md"])

    def test_a_missing_file_yields_nothing(self):
        self.assertEqual(
            ph.export_excludes(os.path.join(self.tmp, "absent")),
            [])

    def test_the_shipped_list_is_not_empty(self):
        # An empty list would put the internal ops record into the
        # comparison set and make every publish look broken.
        self.assertTrue(ph.export_excludes())

    def test_the_shipped_list_matches_what_publish_public_reads(self):
        script = os.path.join(os.path.dirname(ph.EXCLUDES_FILE),
                              "publish-public.sh")
        with open(script, encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("export-excludes.txt", body,
                      "publish-public.sh no longer reads the shared list, so "
                      "the two sides can drift again")
        self.assertNotIn("':(exclude)ops/ecss-program'", body,
                         "the hardcoded pathspec list came back alongside "
                         "the shared file")



class StateFileIsPerRepo(unittest.TestCase):
    """Four copies of publish-public.sh live on a dev machine: skills dev,
    roles dev, and the two public mirrors, which are clones of the exports.
    A shared state filename means whichever ran last owns the record, and
    publish-health for one corpus reads an outcome written by the other.
    That shipped once and was caught by a record whose dev_head was not a
    commit in this repository at all."""

    def test_the_name_carries_the_repo(self):
        self.assertIn(os.path.basename(ph.REPO),
                      os.path.basename(ph.STATE_FILE))

    def test_it_is_not_the_old_shared_name(self):
        self.assertNotEqual(os.path.basename(ph.STATE_FILE),
                            "aero-publish-last.json")

    def test_publish_public_derives_the_same_shape(self):
        script = os.path.join(os.path.dirname(ph.EXCLUDES_FILE),
                              "publish-public.sh")
        with open(script, encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("aero-publish-last-", body,
                      "publish-public.sh writes a shared record again")
        self.assertIn("basename", body)

    def test_it_lives_outside_the_repository(self):
        self.assertFalse(
            os.path.abspath(ph.STATE_FILE).startswith(
                os.path.abspath(ph.REPO) + os.sep),
            "host-local state must never be committed or exported")


if __name__ == "__main__":
    unittest.main(verbosity=2)
