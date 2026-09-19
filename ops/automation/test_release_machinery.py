#!/usr/bin/env python3
"""Detector suite for the release-machinery gate.

This is the gate's negative control. Every other gate proves red-capability by
having the fixture mutated under it; release-machinery cannot, because it runs
test suites rather than reading the corpus -- a pruned four-leaf fixture makes
its suites fail for reasons that have nothing to do with the mutation, so every
mutation would be VOID.

So the proof is direct instead: synthesize directories of passing and failing
suites and assert the gate's verdict on each. The cases below are named in
SELFTEST_PROOFS in tools/negative_controls/run_negative_controls.py; renaming
one without updating that entry reports NOT PROVED, which is the intent.

Offline, stdlib only.
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "ops" / "automation" / "release_machinery.sh"

PASSING_SUITE = (
    "import unittest\n"
    "class T(unittest.TestCase):\n"
    "    def test_ok(self):\n"
    "        self.assertTrue(True)\n"
    "if __name__ == '__main__':\n"
    "    unittest.main()\n"
)

FAILING_SUITE = (
    "import unittest\n"
    "class T(unittest.TestCase):\n"
    "    def test_no(self):\n"
    "        self.assertTrue(False)\n"
    "if __name__ == '__main__':\n"
    "    unittest.main()\n"
)


def run_gate(directory, minimum):
    """Run the gate against a directory. Returns (returncode, stdout, stderr)."""
    r = subprocess.run(
        ["bash", str(GATE), "--dir", str(directory), "--min", str(minimum)],
        cwd=str(REPO), capture_output=True, text=True, timeout=300,
    )
    return r.returncode, r.stdout, r.stderr


def write_suites(directory, passing=0, failing=0):
    for i in range(passing):
        (Path(directory) / ("test_pass_%d.py" % i)).write_text(PASSING_SUITE)
    for i in range(failing):
        (Path(directory) / ("test_fail_%d.py" % i)).write_text(FAILING_SUITE)


class GateGoesRed(unittest.TestCase):
    """The half that matters: the gate must be able to fail."""

    def test_a_failing_suite_turns_the_gate_red(self):
        with tempfile.TemporaryDirectory() as d:
            write_suites(d, passing=2, failing=1)
            rc, out, err = run_gate(d, 3)
            self.assertEqual(rc, 1, "a failing suite must fail the gate")
            self.assertIn("test_fail_0.py", err)
            self.assertNotIn("PASS", out)

    def test_an_empty_directory_is_refused_not_passed(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out, err = run_gate(d, 9)
            self.assertEqual(rc, 2, "an empty set must not read as all-green")
            self.assertNotIn("PASS", out)
            self.assertIn("found 0 suite(s)", err)

    def test_a_shrunken_set_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            write_suites(d, passing=4)
            rc, out, err = run_gate(d, 9)
            self.assertEqual(rc, 2, "fewer suites than the floor must fail")
            self.assertIn("expected at least 9", err)

    def test_the_shrink_verdict_is_distinct_from_the_failure_verdict(self):
        # Distinct exit codes, so a shrunken set is never misread as a red
        # suite (or vice versa) by anything parsing the result.
        with tempfile.TemporaryDirectory() as d:
            write_suites(d, passing=1, failing=1)
            red, _, _ = run_gate(d, 2)
        with tempfile.TemporaryDirectory() as d:
            write_suites(d, passing=1)
            shrunk, _, _ = run_gate(d, 9)
        self.assertEqual(red, 1)
        self.assertEqual(shrunk, 2)
        self.assertNotEqual(red, shrunk)


class GateGoesGreen(unittest.TestCase):
    """A control that cannot pass is as useless as one that cannot fail."""

    def test_all_green_suites_pass(self):
        with tempfile.TemporaryDirectory() as d:
            write_suites(d, passing=9)
            rc, out, err = run_gate(d, 9)
            self.assertEqual(rc, 0, err)
            self.assertIn("PASS release-machinery: 9 suite(s) green", out)

    def test_a_suite_above_the_floor_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            write_suites(d, passing=11)
            rc, out, _ = run_gate(d, 9)
            self.assertEqual(rc, 0)
            self.assertIn("11 suite(s) green", out)

    def test_a_suite_printing_ok_on_stderr_is_not_a_failure(self):
        # unittest writes "OK" to STDERR. A gate reading stdout for a verdict
        # would score every passing suite as silent-and-suspect; this one reads
        # the exit code.
        with tempfile.TemporaryDirectory() as d:
            suite = Path(d) / "test_talks_on_stderr.py"
            suite.write_text(
                "import sys, unittest\n"
                "sys.stderr.write('chatter on stderr\\n')\n"
                "class T(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n"
                "if __name__ == '__main__':\n"
                "    unittest.main()\n"
            )
            rc, out, _ = run_gate(d, 1)
            self.assertEqual(rc, 0)
            self.assertIn("1 suite(s) green", out)


class WiredIn(unittest.TestCase):
    """The gate is only a gate while the Makefile actually calls it."""

    def test_the_makefile_target_calls_this_script(self):
        text = (REPO / "Makefile").read_text(encoding="utf-8")
        self.assertIn("release_machinery.sh", text,
                      "the release-machinery target no longer calls the script")

    def test_the_script_exists_and_is_executable(self):
        self.assertTrue(GATE.is_file(), "%s is missing" % GATE)
        self.assertTrue(os.access(str(GATE), os.X_OK),
                        "%s is not executable" % GATE)

    def test_the_real_suite_set_meets_the_floor(self):
        # Guards the floor against the set it describes: if suites are retired
        # without lowering --min, this fails here rather than in CI.
        real = sorted((REPO / "ops" / "automation").glob("test_*.py"))
        self.assertGreaterEqual(
            len(real), 10,
            "ops/automation has %d suites, below the floor of 10" % len(real))

    def test_the_floor_in_the_script_matches_the_real_set(self):
        # The floor is only protection while it tracks the set. If a suite is
        # added and the floor is not raised, a later deletion goes unnoticed.
        text = GATE.read_text(encoding="utf-8")
        declared = int(re.search(r"^MIN=(\d+)$", text, re.M).group(1))
        real = len(sorted((REPO / "ops" / "automation").glob("test_*.py")))
        self.assertEqual(
            declared, real,
            "script floor is %d but ops/automation holds %d suites -- raise "
            "MIN in release_machinery.sh in the commit that adds a suite"
            % (declared, real))


if __name__ == "__main__":
    unittest.main(verbosity=2)
