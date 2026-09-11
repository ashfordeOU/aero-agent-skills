#!/usr/bin/env python3
"""test_release_hold_marker.py — the release HOLD must reach the public cut.

Regression for the 2026-09-11 gap: doctrine section 5 says the stop switch
~/.hermes/state/aero-release-HOLD "pauses all auto-cuts", but the PRIMARY cut
is release-on-milestone.yml on the public repo, which cannot read host-local
state. Without a carried marker a held milestone still auto-cut on the next
content push (measured: 800 leaves vs public 784, no v1.7.0 Release).

Offline, stdlib only, no network, no git. Creates its own temp trees and
points the helper at a temp HOLD path via AERO_RELEASE_HOLD_FILE, so it never
reads or writes the real switch.

Run: python3 ops/automation/test_release_hold_marker.py
"""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HELPER = os.path.join(HERE, "release-hold-marker.sh")
PUBLISH = os.path.join(HERE, "publish-public.sh")
WORKFLOW = os.path.join(REPO, ".github", "workflows", "release-on-milestone.yml")
MARKER = ".release-hold"
HOST_PATH_RE = re.compile(r"/Us" r"ers/|/ho" r"me/")


def run_helper(tree: str, hold_file: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, AERO_RELEASE_HOLD_FILE=hold_file)
    return subprocess.run(["bash", HELPER, tree], capture_output=True, text=True,
                          env=env, timeout=60)


def sha(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class ReleaseHoldMarkerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="aero-hold-test-")
        self.tree = os.path.join(self.tmp, "export")
        self.hold = os.path.join(self.tmp, "aero-release-HOLD")
        os.makedirs(self.tree)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def marker(self) -> str:
        return os.path.join(self.tree, MARKER)

    # (a) HOLD set -> marker written, publicly safe, no host path
    def test_hold_set_writes_safe_marker(self):
        with open(self.hold, "w") as fh:
            fh.write("HOLD set 2026-09-11: v1.7.0 cut waits for evidence\n")
        res = run_helper(self.tree, self.hold)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(os.path.isfile(self.marker()), "marker must exist")
        body = open(self.marker()).read()
        self.assertIn("HOLD active", body)
        self.assertIsNone(HOST_PATH_RE.search(body),
                          "marker must not carry a host-local path into public")
        self.assertNotIn("HOLD set 2026-09-11", body,
                         "the switch note must not be copied verbatim")

    # (b) HOLD clear + stale marker from an earlier publish -> marker removed
    def test_hold_cleared_removes_stale_marker(self):
        with open(self.marker(), "w") as fh:
            fh.write("stale\n")
        res = run_helper(self.tree, self.hold)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertFalse(os.path.exists(self.marker()),
                         "a cleared switch must not leave the cut suppressed")

    # (c) the helper never modifies the founder's switch file
    def test_helper_leaves_hold_file_untouched(self):
        with open(self.hold, "w") as fh:
            fh.write("HOLD set 2026-09-11: v1.7.0 cut waits for evidence\n")
        before_sha, before_mtime = sha(self.hold), os.path.getmtime(self.hold)
        run_helper(self.tree, self.hold)
        self.assertEqual(sha(self.hold), before_sha, "HOLD file content changed")
        self.assertEqual(os.path.getmtime(self.hold), before_mtime,
                         "HOLD file mtime changed")

    # (d) a missing HOLD path is the open state, not an error
    def test_missing_hold_is_not_an_error(self):
        res = run_helper(self.tree, os.path.join(self.tmp, "nope"))
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertFalse(os.path.exists(self.marker()))

    # (e) the publish path must actually call the helper
    def test_publish_path_carries_the_marker(self):
        body = open(PUBLISH).read()
        self.assertIn("release-hold-marker.sh", body,
                      "publish-public.sh must mirror the HOLD into the export")

    # (f) the workflow must refuse to cut while the marker is present
    def test_workflow_guards_on_marker(self):
        body = open(WORKFLOW).read()
        guard = body.index(MARKER)
        loop = body.index('for m in $(seq 1 "$MINOR")')
        self.assertLess(guard, loop,
                        "the HOLD guard must run before the milestone loop")
        self.assertIn("should_release=false", body[guard:loop])


if __name__ == "__main__":
    unittest.main(verbosity=2)
