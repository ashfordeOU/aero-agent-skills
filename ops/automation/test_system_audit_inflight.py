#!/usr/bin/env python3
"""Fail-first unittest: in-flight CCD lane builds and in-cycle publish lag
must not FAIL the daily system audit.

Same false-red class as the paused-cron fix in check_crons()
(test_system_audit_paused_crons.py): a daily fixed-minute audit catches
legitimately-in-progress work and reports it as broken, desensitising the
founder to real breaks.

Covers:
  - check_dev_tree(): a dirty/unpushed dev tree is expected while a CCD lane
    build is in flight. "In flight" (VEDA-0066) is `claude -p` running (same
    signal aero-lane-harvest.py's claude_running() uses: `pgrep -f
    "claude -p"`) OR an open lane worktree under LANE_ROOT (same discovery
    as aero-lane-harvest.py's main(): a directory directly under LANE_ROOT
    containing a .git entry) — the pgrep signal alone reads FALSE between
    two claude invocations while a lane is genuinely still open. An IDLE
    dirty or unpushed tree with no lane open and no claude running must
    still FAIL exactly as before.
  - check_public_and_site(): the public mirror lagging dev is only a break
    if the mirror's newest commit is older than one publish cycle (hourly
    launchd publish, PUBLISH_CYCLE_TOLERANCE_MINUTES = 120).

Offline, stdlib only, python3.9-compatible. All git/pgrep/GitHub-API reads
are stubbed — no subprocess or network calls actually run. LANE_ROOT is
patched per-test to a scratch tmp directory — no real lane repos are read.
"""
import base64
import datetime
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import system_audit  # noqa: E402


def cp(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class CheckDevTreeInFlightTest(unittest.TestCase):
    def setUp(self):
        system_audit.failures = []
        system_audit.notes = []
        self._orig_run = system_audit.run
        self._orig_lane_root = system_audit.LANE_ROOT
        self._tmp = tempfile.TemporaryDirectory()
        # default: LANE_ROOT points at a path that does not exist -> no
        # real filesystem is ever consulted unless a test opts in below.
        system_audit.LANE_ROOT = Path(self._tmp.name) / "no-such-lane-root"

    def tearDown(self):
        system_audit.run = self._orig_run
        system_audit.LANE_ROOT = self._orig_lane_root
        self._tmp.cleanup()

    def _lane_root(self):
        root = Path(self._tmp.name) / "lanes"
        root.mkdir(parents=True, exist_ok=True)
        system_audit.LANE_ROOT = root
        return root

    def _make_open_lane(self, name):
        """A directory under LANE_ROOT with a .git entry — a genuine open
        lane per aero-lane-harvest.py's discovery."""
        lane = self._lane_root() / name
        lane.mkdir(parents=True, exist_ok=True)
        (lane / ".git").mkdir()
        return lane

    def _make_lane_dir_without_git(self, name):
        lane = self._lane_root() / name
        lane.mkdir(parents=True, exist_ok=True)
        return lane

    def _make_plain_file(self, name):
        f = self._lane_root() / name
        f.write_text("not a lane")
        return f

    def _stub_run(self, dirty_lines, unpushed, claude_running):
        def fake_run(cmd, cwd=None, timeout=120):
            if cmd[:2] == ["git", "status"]:
                stdout = "\n".join(" M file%d.py" % i for i in range(dirty_lines))
                return cp(0, stdout)
            if cmd[:2] == ["git", "fetch"]:
                return cp(0, "")
            if cmd[:3] == ["git", "rev-list", "--count"]:
                return cp(0, str(unpushed))
            if cmd[:2] == ["pgrep", "-f"]:
                return cp(0, "12345\n") if claude_running else cp(1, "")
            raise AssertionError("unexpected cmd %r" % (cmd,))
        system_audit.run = fake_run

    # (a) dirty + unpushed WITH a build in flight -> no failure
    def test_dirty_and_unpushed_with_build_in_flight_does_not_fail(self):
        self._stub_run(dirty_lines=2, unpushed=7, claude_running=True)
        system_audit.check_dev_tree()
        self.assertEqual(
            [f for f in system_audit.failures if f.startswith("dev-tree:")], [])
        self.assertTrue(any(
            "in flight" in n or "in-flight" in n for n in system_audit.notes))

    # (b) idle dirty -> failure
    def test_idle_dirty_fails(self):
        self._stub_run(dirty_lines=2, unpushed=0, claude_running=False)
        system_audit.check_dev_tree()
        self.assertTrue(any(
            f.startswith("dev-tree:") and "uncommitted" in f
            for f in system_audit.failures))

    # (c) idle unpushed -> failure
    def test_idle_unpushed_fails(self):
        self._stub_run(dirty_lines=0, unpushed=7, claude_running=False)
        system_audit.check_dev_tree()
        self.assertTrue(any(
            f.startswith("dev-tree:") and "unpushed" in f
            for f in system_audit.failures))

    # clean + no build in flight -> no failure, no note (unchanged behaviour)
    def test_clean_tree_no_build_is_silent(self):
        self._stub_run(dirty_lines=0, unpushed=0, claude_running=False)
        system_audit.check_dev_tree()
        self.assertEqual(system_audit.failures, [])

    # (1) lane open + claude not running + dirty/unpushed tree -> NOTE, zero failures
    def test_open_lane_no_claude_dirty_unpushed_tree_notes_not_fails(self):
        self._make_open_lane("e-abc-1")
        self._stub_run(dirty_lines=2, unpushed=3, claude_running=False)
        system_audit.check_dev_tree()
        self.assertEqual(
            [f for f in system_audit.failures if f.startswith("dev-tree:")], [])
        self.assertTrue(any(
            "in flight" in n and "e-abc-1" in n for n in system_audit.notes))

    # (2) no lane + claude not running + dirty tree -> still a FAIL (unchanged)
    def test_no_lane_no_claude_dirty_tree_still_fails(self):
        self._stub_run(dirty_lines=2, unpushed=0, claude_running=False)
        system_audit.check_dev_tree()
        self.assertTrue(any(
            f.startswith("dev-tree:") and "uncommitted" in f
            for f in system_audit.failures))

    # (3) claude running, no lane -> in flight (unchanged)
    def test_claude_running_no_lane_in_flight_unchanged(self):
        self._stub_run(dirty_lines=1, unpushed=1, claude_running=True)
        system_audit.check_dev_tree()
        self.assertEqual(
            [f for f in system_audit.failures if f.startswith("dev-tree:")], [])
        self.assertTrue(any(
            "in flight" in n and "claude -p running" in n
            for n in system_audit.notes))

    # (4a) a plain file directly under LANE_ROOT is NOT an open lane
    def test_plain_file_under_lane_root_is_not_an_open_lane(self):
        self._make_plain_file("scratch.txt")
        self.assertEqual(system_audit.open_lanes(system_audit.LANE_ROOT), [])
        self._stub_run(dirty_lines=1, unpushed=1, claude_running=False)
        system_audit.check_dev_tree()
        self.assertTrue(any(
            f.startswith("dev-tree:") for f in system_audit.failures))

    # (4b) a directory under LANE_ROOT without a .git entry is NOT an open lane
    def test_lane_dir_without_git_is_not_an_open_lane(self):
        self._make_lane_dir_without_git("e-half-cloned")
        self.assertEqual(system_audit.open_lanes(system_audit.LANE_ROOT), [])
        self._stub_run(dirty_lines=1, unpushed=1, claude_running=False)
        system_audit.check_dev_tree()
        self.assertTrue(any(
            f.startswith("dev-tree:") for f in system_audit.failures))

    def test_open_lanes_names_every_genuine_lane(self):
        self._make_open_lane("e-open-1")
        self._make_open_lane("e-open-2")
        self._make_plain_file("README.txt")
        self._make_lane_dir_without_git("e-not-a-lane")
        self.assertEqual(
            system_audit.open_lanes(system_audit.LANE_ROOT),
            ["e-open-1", "e-open-2"])


class CheckPublicPublishCycleTest(unittest.TestCase):
    def setUp(self):
        system_audit.failures = []
        system_audit.notes = []
        self._orig_api = system_audit.api
        self._orig_urlopen = system_audit.urllib.request.urlopen

    def tearDown(self):
        system_audit.api = self._orig_api
        system_audit.urllib.request.urlopen = self._orig_urlopen

    def _stub(self, pub_leaves, commit_minutes_ago, failed_workflows=0):
        commit_dt = (datetime.datetime.now(datetime.timezone.utc)
                     - datetime.timedelta(minutes=commit_minutes_ago))
        commit_date_str = commit_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        def fake_api(path, token):
            if path.startswith(
                    "/repos/%s/contents/docs/metrics.json" % system_audit.PUBLIC_REPO):
                content = base64.b64encode(
                    ('{"leaves": %d}' % pub_leaves).encode()).decode()
                return {"content": content}
            if path.startswith("/repos/%s/actions/runs" % system_audit.PUBLIC_REPO):
                return {"total_count": failed_workflows}
            if path.startswith("/repos/%s/commits" % system_audit.PUBLIC_REPO):
                return [{"commit": {"committer": {"date": commit_date_str}}}]
            raise AssertionError("unexpected api path %r" % path)
        system_audit.api = fake_api

        class FakeResp(object):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b"999 verified"

        system_audit.urllib.request.urlopen = (
            lambda req, timeout=30: FakeResp())

    # (d) public behind with a fresh mirror commit -> no failure
    def test_public_behind_with_fresh_commit_does_not_fail(self):
        self._stub(pub_leaves=806, commit_minutes_ago=5)
        system_audit.check_public_and_site(830, None)
        self.assertEqual(
            [f for f in system_audit.failures if f.startswith("public:")], [])
        self.assertTrue(any(n.startswith("public:") for n in system_audit.notes))

    # (e) public behind with a stale mirror commit (>120 min) -> failure
    def test_public_behind_with_stale_commit_fails(self):
        self._stub(pub_leaves=806, commit_minutes_ago=200)
        system_audit.check_public_and_site(830, None)
        self.assertTrue(any(
            f.startswith("public:") and "lags dev" in f
            for f in system_audit.failures))

    # public not behind -> unaffected (unchanged behaviour)
    def test_public_not_behind_does_not_fail(self):
        self._stub(pub_leaves=830, commit_minutes_ago=5)
        system_audit.check_public_and_site(830, None)
        self.assertEqual(
            [f for f in system_audit.failures if f.startswith("public:")], [])


if __name__ == "__main__":
    unittest.main()
