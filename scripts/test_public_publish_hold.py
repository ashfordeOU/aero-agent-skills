#!/usr/bin/env python3
"""Gate test: the PUBLIC publish is fail-closed on the founder GO (Ruling 3).

The 2026-09-10 relay tick found the public sync was held only BY ACCIDENT:
scripts/public-safety-audit.py aborted on a private_ips false positive, so
publish-public.sh never reached its push. Fixing that false positive would
have published 101 ECSS leaves to ashfordeOU/aero-agent-skills with no
founder GO — the hold existed in policy (products-state, relay log) but in
no code path.

These tests pin the guard on both sides:
  * helper unit: absent / empty GO => exit 78 (HELD), non-empty => exit 0
  * wiring: publish-public.sh must abort at the hold BEFORE it exports or
    touches the mirror/push, so a fix to any downstream gate can never
    release a publish on its own.

Hermetic: temp GO paths only, no network, no git, no push.
"""
import os
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOLD = os.path.join(REPO_ROOT, "ops", "automation", "public-publish-hold.sh")
PUBLISH = os.path.join(REPO_ROOT, "ops", "automation", "publish-public.sh")

HELD_RC = 78


def run(cmd, go_file):
    env = dict(os.environ, AERO_PUBLISH_GO_FILE=go_file)
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)


class HoldHelper(unittest.TestCase):
    def test_missing_go_file_is_held(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(["bash", HOLD], os.path.join(d, "absent-GO"))
        self.assertEqual(r.returncode, HELD_RC, r.stdout + r.stderr)
        self.assertIn("HELD", r.stdout)

    def test_empty_go_file_is_held(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "GO")
            open(path, "w").close()
            r = run(["bash", HOLD], path)
        self.assertEqual(r.returncode, HELD_RC, r.stdout + r.stderr)
        self.assertIn("EMPTY", r.stdout)

    def test_present_go_file_authorizes(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "GO")
            with open(path, "w") as fh:
                fh.write("GO aero-agent-skills public release 2026-09-10\n")
            r = run(["bash", HOLD], path)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("GO:", r.stdout)


class PublishWiring(unittest.TestCase):
    """The guard must sit BEFORE the export and before any push."""

    def test_publish_aborts_held_before_export(self):
        with tempfile.TemporaryDirectory() as d:
            scratch = os.path.join(d, "scratch")
            os.makedirs(scratch)
            go_file = os.path.join(d, "absent-GO")
            env = dict(os.environ, AERO_PUBLISH_GO_FILE=go_file, TMPDIR=scratch)
            r = subprocess.run(["bash", PUBLISH], capture_output=True, text=True,
                               env=env, timeout=300)
            leftovers = [n for n in os.listdir(scratch) if not n.endswith(".log")]
        self.assertEqual(r.returncode, HELD_RC, r.stdout + r.stderr)
        self.assertIn("HELD", r.stdout + r.stderr)
        # No export tree, no mirror work, no push happened.
        self.assertEqual(leftovers, [], f"hold ran after export: {leftovers}")
        self.assertNotIn("pushing (normal fast-forward", r.stdout)

    def test_hold_gate_is_wired_before_the_dev_tree_check(self):
        with open(PUBLISH) as fh:
            body = fh.read()
        self.assertIn("public-publish-hold.sh", body,
                      "publish-public.sh does not call the founder-GO hold")
        self.assertLess(body.index("public-publish-hold.sh"),
                        body.index("checking dev tree is itself clean"),
                        "hold must be checked before the dev-tree gate battery")


class WrapperReporting(unittest.TestCase):
    """The launchd entry point must report HELD, not a generic FAILED.

    Regression: `if ! cmd; then rc=$?` yields 0 inside the then-branch, so the
    first cut of this guard reported "FAILED (exit 0)" for a correctly held
    publish and would have misread every future hold as a failure.
    """

    def test_hourly_wrapper_reports_held(self):
        wrapper = os.path.join(REPO_ROOT, "ops", "automation", "hourly-publish.sh")
        with tempfile.TemporaryDirectory() as d:
            site = os.path.join(d, "site")
            for product in ("aeroagentskills", "aeroagentroles"):
                os.makedirs(os.path.join(site, product))
                stub = os.path.join(site, product, "sync-and-publish.sh")
                with open(stub, "w") as fh:
                    fh.write("#!/usr/bin/env bash\nexit 0\n")
                os.chmod(stub, 0o755)
            env = dict(os.environ,
                       ASHFORDE_SITE_REPO=site,
                       AERO_PUBLISH_GO_FILE=os.path.join(d, "absent-GO"))
            r = subprocess.run(["bash", wrapper], capture_output=True, text=True,
                               env=env, timeout=300)
        self.assertIn("HELD (exit 78)", r.stdout, r.stdout + r.stderr)
        self.assertNotIn("FAILED", r.stdout, r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
