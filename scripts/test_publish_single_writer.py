#!/usr/bin/env python3
"""Gate test: the PUBLIC publish mutates ONE shared mirror under a lock.

VEDA-0037: publish-public.sh rewrites a single persistent mirror clone
(reset --hard -> find -delete -> cp -a <export> -> commit -> push) and nothing
serialised its callers. The launchd plist's StartInterval only stops the TIMER
from overlapping itself, so on 2026-09-10 a gateway run (20:04:41Z) raced the
hourly launchd job (20:08:53Z) on that one worktree. The damage was contained
by luck (a leaf-count guard, a non-fast-forward refusal); the real symptom is
the SILENT FALSE no-op of VEDA-0033 — two runs interleave, both log "nothing to
push", and the public repo stays behind the dev tree while every gate is green.

These tests pin the lock on both sides:
  * runtime: with the lock held by another process, a run CANNOT enter the
    mirror phase — it exits 75 and says which lock/path blocked it; once the
    holder is gone the same run proceeds past the lock;
  * contract: the lock is taken before the first mirror mutation, lives
    outside the repo, aborts non-zero when busy, and has no escape hatch that
    would skip it silently;
  * the audit check that guards this wiring can actually FAIL (negative
    fixtures — an untested gate is a claim, not a check).

Hermetic: the publish script is exercised from a temp sandbox repo, with temp
lock/GO paths and a short wait; no network, no real mirror, no push, and the
real publish-public.sh is never executed.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTOMATION = os.path.join(REPO_ROOT, "ops", "automation")
PUBLISH = os.path.join(AUTOMATION, "publish-public.sh")
HOLD = os.path.join(AUTOMATION, "public-publish-hold.sh")

LOCK_BUSY_RC = 75          # publish-public.sh: another publish owns the lock
LOCK_WAIT_SECONDS = "2"    # short bounded wait, keeps the tests fast
HOLDER_READY = "LOCKED"
GO_TEXT = "GO aero-agent-skills public release 2026-09-10\n"
LOCK_MARKER = "# --- 0b. SINGLE-WRITER LOCK (VEDA-0037) ---"
LOCK_ACQUIRED = "log \"single-writer lock acquired ($PUBLISH_LOCK_FILE).\""
# A process that owns the lock the same way publish-public.sh does: bash holds
# fd 9, python takes the flock on that inherited descriptor. It prints LOCKED
# only after the kernel granted it, so the test never races a slow start.
HOLDER_CODE = (
    "import fcntl, sys, time\n"
    "fd = int(sys.argv[1])\n"
    "fcntl.flock(fd, fcntl.LOCK_EX)\n"
    "print('LOCKED', flush=True)\n"
    "time.sleep(float(sys.argv[2]))\n"
)
HOLDER_SH = (
    "#!/usr/bin/env bash\n"
    "exec 9>\"$1\"\n"
    "python3 -c \"$2\" 9 \"$3\"\n"
)


def sandbox(d):
    """Copy the publish scripts into a throwaway repo so the real one is never run.

    The sandbox is a clean git repo, so publish-public.sh gets past its
    dev-tree check and stops at the next step (no Makefile) — far enough to
    prove it left the lock phase, with no export, no gates, no push.
    """
    repo = os.path.join(d, "repo")
    auto = os.path.join(repo, "ops", "automation")
    os.makedirs(auto)
    shutil.copy(PUBLISH, os.path.join(auto, "publish-public.sh"))
    shutil.copy(HOLD, os.path.join(auto, "public-publish-hold.sh"))
    subprocess.run(["git", "init", "--quiet", repo], check=True, timeout=60)
    subprocess.run(["git", "-C", repo, "-c", "user.email=t@example.invalid",
                    "-c", "user.name=t", "commit", "--quiet", "--allow-empty",
                    "-m", "sandbox"], check=True, timeout=60)
    go_file = os.path.join(d, "GO")
    with open(go_file, "w") as fh:
        fh.write(GO_TEXT)
    return os.path.join(auto, "publish-public.sh"), go_file, os.path.join(d, "publish.lock")


def run_publish(script, go_file, lock_file, timeout=60):
    env = dict(os.environ,
               AERO_PUBLISH_LOCK_FILE=lock_file,
               AERO_PUBLISH_LOCK_TIMEOUT=LOCK_WAIT_SECONDS,
               AERO_PUBLISH_GO_FILE=go_file,
               TMPDIR=os.path.dirname(lock_file))
    return subprocess.run(["bash", script], capture_output=True, text=True,
                          env=env, timeout=timeout)


class SecondWriterBlocked(unittest.TestCase):
    """(a) A run that cannot own the mirror must not touch it, and must say so."""

    def test_blocked_while_lock_held(self):
        with tempfile.TemporaryDirectory() as d:
            script, go_file, lock = sandbox(d)
            holder = subprocess.Popen(
                ["bash", "-c", HOLDER_SH, "bash", lock, HOLDER_CODE, "30"],
                stdout=subprocess.PIPE, text=True)
            try:
                ready = holder.stdout.readline().strip()
                self.assertEqual(ready, HOLDER_READY, "holder never took the lock")
                r = run_publish(script, go_file, lock)
            finally:
                holder.stdout.close()
                holder.kill()
                holder.wait()
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, LOCK_BUSY_RC, out)
        self.assertIn("held by another publish", out)
        self.assertIn(lock, out, "the block message must name the lock it could not take")
        # Nothing of the mirror phase ran: no export, no commit, no push.
        self.assertNotIn("single-writer lock acquired", out)
        self.assertNotIn("exporting the full tree", out)
        self.assertNotIn("pushing (normal fast-forward", out)

    def test_proceeds_once_released(self):
        with tempfile.TemporaryDirectory() as d:
            script, go_file, lock = sandbox(d)
            r = run_publish(script, go_file, lock)
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, LOCK_BUSY_RC, out)
        self.assertIn("single-writer lock acquired", out)
        # It moved on into the publish flow (sandbox has no Makefile: it stops
        # at the dev-tree battery, well past the lock).
        self.assertIn("checking dev tree has no uncommitted changes", out)
        self.assertNotIn("held by another publish", out)


class LockContract(unittest.TestCase):
    """(c) No path may reach the mirror without taking the lock."""

    @classmethod
    def setUpClass(cls):
        with open(PUBLISH, encoding="utf-8") as fh:
            cls.body = fh.read()

    def test_lock_precedes_the_first_mirror_mutation(self):
        # Anchor on the real commands: the file's prose says "reset --hard" as
        # well, and matching a comment hides whether the lock is early enough.
        for mutation in ('git -C "$MIRROR" reset --hard',
                         'find "$MIRROR" -mindepth 1',
                         'cp -a "$EXPORT/." "$MIRROR/"'):
            self.assertIn(mutation, self.body)
            self.assertLess(self.body.index("exec 9>"), self.body.index(mutation),
                            f"lock is taken after the mirror mutation {mutation!r}")

    def test_lock_is_taken_unconditionally(self):
        # A top-level `exec 9>` cannot be turned off by a flag or env var, so
        # no run (dry-run included) can skip it and reach the mirror unlocked.
        self.assertIn("\nexec 9>", self.body)
        self.assertNotIn("\n  exec 9>", self.body)

    def test_busy_lock_aborts_nonzero_and_names_the_decision(self):
        self.assertIn('exit "$LOCK_BUSY_EXIT"', self.body)
        self.assertIn("LOCK_BUSY_EXIT=75", self.body)

    def test_host_without_lock_primitive_aborts(self):
        # macOS ships no flock(1); the python fcntl fallback is a real lock.
        # A host with neither must ABORT, never publish unlocked.
        self.assertIn("command -v flock", self.body)
        self.assertIn("command -v python3", self.body)
        self.assertIn("refusing to publish WITHOUT mutual exclusion", self.body)

    def test_no_escape_hatch_skips_the_lock(self):
        for off_switch in ("AERO_PUBLISH_LOCK_OFF", "SKIP_LOCK", "NO_LOCK",
                           "AERO_PUBLISH_LOCK_ONLY", "AERO_PUBLISH_LOCK_DISABLE"):
            self.assertNotIn(off_switch, self.body)

    def test_lock_file_is_host_local_and_outside_the_repo(self):
        default = os.path.expanduser("~/.hermes/state/aero-public-publish.lock")
        self.assertIn("AERO_PUBLISH_LOCK_FILE:-$HOME/.hermes/state/", self.body)
        self.assertFalse(default.startswith(REPO_ROOT + os.sep))
        self.assertNotIn(REPO_ROOT, default)


class AuditCheckCatchesDrift(unittest.TestCase):
    """(c) The system_audit check must fail on each violation class.

    Negative fixtures: an untested gate is a claim, not a check.
    """

    def _audit(self, root):
        if AUTOMATION not in sys.path:
            sys.path.insert(0, AUTOMATION)
        import system_audit as sa
        old_root, old_failures = sa.ROOT, list(sa.failures)
        sa.ROOT, sa.failures = root, []
        try:
            sa.check_publish_single_writer()
            return list(sa.failures)
        finally:
            sa.ROOT = old_root
            sa.failures.clear()
            sa.failures.extend(old_failures)

    def _fake_root(self, d, body):
        auto = os.path.join(d, "ops", "automation")
        os.makedirs(auto)
        path = os.path.join(auto, "publish-public.sh")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return d

    def test_real_script_passes(self):
        self.assertEqual([f for f in self._audit(REPO_ROOT)
                          if f.startswith("publish-lock:")], [],
                         "the audit rejects the real publish-public.sh")

    def test_missing_lock_fails(self):
        with open(PUBLISH, encoding="utf-8") as fh:
            body = fh.read()
        start = body.index(LOCK_MARKER)
        end = body.index(LOCK_ACQUIRED) + len(LOCK_ACQUIRED)
        with tempfile.TemporaryDirectory() as d:
            fails = self._audit(self._fake_root(d, body[:start] + body[end:]))
        self.assertTrue(any(f.startswith("publish-lock:") for f in fails),
                        f"a lockless publish-public.sh audited clean: {fails}")

    def test_lock_after_mirror_fails(self):
        with open(PUBLISH, encoding="utf-8") as fh:
            body = fh.read()
        start = body.index(LOCK_MARKER)
        end = body.index(LOCK_ACQUIRED) + len(LOCK_ACQUIRED)
        moved = body[:start] + body[end:] + "\n" + body[start:end]
        with tempfile.TemporaryDirectory() as d:
            fails = self._audit(self._fake_root(d, moved))
        self.assertTrue(any("AFTER the first mirror mutation" in f for f in fails),
                        f"lock ordering drift audited clean: {fails}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
