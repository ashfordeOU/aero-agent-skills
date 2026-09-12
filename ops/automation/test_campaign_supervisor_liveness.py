#!/usr/bin/env python3
"""Fail-first pins for aero-campaign-supervisor.sh liveness detection (VEDA-0076).

Run:
    python3 ops/automation/test_campaign_supervisor_liveness.py
Env:
    AERO_SUPERVISOR=<path>   default: the repo copy beside this test file

WHY THESE CASES
The supervisor must read a runner as alive in BOTH argv forms:
  * WAITING at the doer gate -> `/bin/zsh <tracked>/aero-campaign.sh`
  * RUNNING the campaign     -> the wrapper `exec`s the driver, so argv becomes
    `python3 ~/.hermes/scripts/aero-day-driver.py` and the wrapper name is gone
    from the process table.
Matching only the wrapper name reported "no runner" for a live driver, spawned
a duplicate, read the flock refusal as a failure and alarmed the ops topic
every 10 minutes for a healthy campaign. Case 1 fails on that pre-fix file.

SAFETY: every case overrides AERO_CAMPAIGN_SCRIPT onto a throwaway stub, so the
real campaign is never started, stopped, or signalled by this test.
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SUPERVISOR = os.environ.get("AERO_SUPERVISOR", os.path.join(HERE, "aero-campaign-supervisor.sh"))
RUNNING_FORM = "aero-day-driver.py"

FAILURES = []


def report(name, ok, detail=""):
    print("%-46s %s %s" % (name, "OK" if ok else "FAIL", detail))
    if not ok:
        FAILURES.append(name)


def run(env, timeout=60):
    full = dict(os.environ)
    full.update(env)
    return subprocess.run(["/bin/bash", SUPERVISOR], env=full, capture_output=True,
                          text=True, timeout=timeout)


def write(path, text, mode=0o755):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, mode)
    return path


def main():
    tmp = tempfile.mkdtemp(prefix="aero-sup-test-")
    marker = os.path.join(tmp, "started.marker")
    log = os.path.join(tmp, "campaign.log")
    token = "aerosup-test-%d" % os.getpid()
    probes = []

    try:
        # --- case 0: the default pattern set covers the RUNNING form ---------
        text = open(SUPERVISOR, encoding="utf-8").read()
        default_line = [ln for ln in text.splitlines() if "AERO_CAMPAIGN_PATTERN:-" in ln]
        ok = bool(default_line) and RUNNING_FORM in default_line[0]
        report("default patterns cover the running form", ok,
               "" if ok else "(no aero-day-driver.py in the default set)")

        # --- case 1: a runner in the RUNNING form is seen (pre-fix FAILS) ----
        probe = write(os.path.join(tmp, RUNNING_FORM),
                      "import time\ntime.sleep(30)\n")
        p1 = subprocess.Popen([sys.executable, probe], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        probes.append(p1)
        time.sleep(1)
        alive_stub = write(os.path.join(tmp, "%s.sh" % token),
                           "#!/bin/zsh\ntouch \"$MARKER\"\nsleep 30\n")
        r = run({"AERO_CAMPAIGN_SCRIPT": alive_stub, "AERO_CAMPAIGN_LOG": log,
                 "MARKER": marker, "AERO_CAMPAIGN_STOP": os.path.join(tmp, "no-stop")})
        ok = r.returncode == 0 and "RESTART" not in r.stdout and not os.path.exists(marker)
        report("running-form runner is a silent no-op", ok,
               "rc=%d out=%r" % (r.returncode, r.stdout.strip()[:70]))

        # --- case 2: no runner -> starts the tracked script, reports it ------
        unique = "%s-c2.sh" % token
        if os.path.exists(marker):
            os.remove(marker)
        alive2 = write(os.path.join(tmp, "c2", unique),
                       "#!/bin/zsh\ntouch \"$MARKER\"\nsleep 30\n")
        r = run({"AERO_CAMPAIGN_SCRIPT": alive2, "AERO_CAMPAIGN_LOG": log,
                 "MARKER": marker, "AERO_CAMPAIGN_PATTERN": unique,
                 "AERO_CAMPAIGN_STOP": os.path.join(tmp, "no-stop")})
        ok = (r.returncode == 0 and "restarted from tracked path" in r.stdout
              and os.path.exists(marker))
        report("no runner -> starts tracked, rc 0", ok,
               "rc=%d out=%r marker=%s" % (r.returncode, r.stdout.strip()[:60],
                                           os.path.exists(marker)))
        subprocess.run(["pkill", "-f", unique], capture_output=True)

        # --- case 3: a start that dies is still reported loudly --------------
        unique3 = "%s-c3.sh" % token
        dead = write(os.path.join(tmp, "c3", unique3), "#!/bin/zsh\nexit 1\n")
        r = run({"AERO_CAMPAIGN_SCRIPT": dead, "AERO_CAMPAIGN_LOG": log,
                 "AERO_CAMPAIGN_PATTERN": unique3,
                 "AERO_CAMPAIGN_STOP": os.path.join(tmp, "no-stop")})
        ok = r.returncode == 1 and "RESTART FAILED" in r.stdout
        report("dead start is still a loud failure", ok,
               "rc=%d out=%r" % (r.returncode, r.stdout.strip()[:60]))
    finally:
        for p in probes:
            try:
                p.send_signal(signal.SIGTERM)
            except OSError:
                pass
        subprocess.run(["pkill", "-f", token], capture_output=True)
        subprocess.run(["pkill", "-f", os.path.join(tmp, RUNNING_FORM)],
                       capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n%s: %d failure(s)" % ("RED" if FAILURES else "GREEN", len(FAILURES)))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
