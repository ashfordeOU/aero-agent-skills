#!/usr/bin/env python3
"""Fail-first unittest: paused crons must not FAIL the daily system audit.

Covers ops/automation/system_audit.py check_crons() against an explicit
pause registry (ops/automation/state/paused-crons.json). A cron that is
DISABLED but recorded in the registry is an intentional pause (note, not
fail). A cron that is DISABLED and NOT in the registry is a real break
(fail, as before). Offline, stdlib only, python3.9-compatible.
"""
import json
import os
import sys
import tempfile
import shutil
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import system_audit  # noqa: E402


def write_jobs(cron_dir, jobs):
    os.makedirs(cron_dir, exist_ok=True)
    with open(os.path.join(cron_dir, "jobs.json"), "w", encoding="utf-8") as fh:
        json.dump({"jobs": jobs}, fh)


def all_required_jobs(overrides):
    """All REQUIRED_CRONS enabled, except names in `overrides` (name -> enabled)."""
    jobs = []
    for name in system_audit.REQUIRED_CRONS:
        jobs.append({"name": name, "enabled": overrides.get(name, True)})
    return jobs


def write_registry(path, pauses):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"pauses": pauses}, fh)


class CheckCronsPauseRegistryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="system-audit-test-")
        self.cron_dir = os.path.join(self.tmp, "cron")
        self.registry_path = os.path.join(self.tmp, "state", "paused-crons.json")

        self._orig_cron_dirs = system_audit.CRON_DIRS
        # getattr: on the pre-fix audit the constant does not exist yet, so the
        # suite must still run and fail BEHAVIOURALLY (disabled cron -> FAIL),
        # not error out on a missing attribute.
        self._orig_pause_registry = getattr(system_audit, "PAUSE_REGISTRY", None)
        system_audit.CRON_DIRS = [self.cron_dir]
        if self._orig_pause_registry is not None:
            system_audit.PAUSE_REGISTRY = self.registry_path

        system_audit.failures = []
        system_audit.notes = []

    def tearDown(self):
        system_audit.CRON_DIRS = self._orig_cron_dirs
        if self._orig_pause_registry is not None:
            system_audit.PAUSE_REGISTRY = self._orig_pause_registry
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _crons_failures(self):
        return [f for f in system_audit.failures if f.startswith("crons:")]

    # (a) registered + DISABLED -> no crons failure
    def test_registered_disabled_cron_does_not_fail(self):
        write_jobs(self.cron_dir, all_required_jobs(
            {"Aero night CCD lane dispatch": False}))
        write_registry(self.registry_path, [
            {
                "name": "Aero night CCD lane dispatch",
                "since": "2026-09-11",
                "by": "founder",
                "reason": "manual handover mode - the founder drives the CCD lane builds by hand",
                "ref": "ops/ecss-program/HANDOVER-MANUAL-RUN.md",
            }
        ])
        system_audit.check_crons()
        self.assertEqual(self._crons_failures(), [])

    # (b) unregistered + DISABLED -> crons failure present
    def test_unregistered_disabled_cron_fails(self):
        write_jobs(self.cron_dir, [
            {"name": "Aero night CCD lane dispatch", "enabled": False},
        ])
        write_registry(self.registry_path, [])
        system_audit.check_crons()
        self.assertTrue(any(
            "is DISABLED" in f and "Aero night CCD lane dispatch" in f
            for f in self._crons_failures()))

    # (c) ENABLED cron -> no failure
    def test_enabled_cron_does_not_fail(self):
        write_jobs(self.cron_dir, [
            {"name": "Aero night CCD lane dispatch", "enabled": True},
        ])
        write_registry(self.registry_path, [])
        system_audit.check_crons()
        self.assertEqual(
            [f for f in self._crons_failures()
             if "Aero night CCD lane dispatch" in f],
            [],
        )

    # (d) registry file MISSING + DISABLED -> failure present
    def test_missing_registry_file_does_not_silence_failure(self):
        write_jobs(self.cron_dir, [
            {"name": "Aero night CCD lane dispatch", "enabled": False},
        ])
        self.assertFalse(os.path.exists(self.registry_path))
        system_audit.check_crons()
        self.assertTrue(any(
            "is DISABLED" in f and "Aero night CCD lane dispatch" in f
            for f in self._crons_failures()))

    # (e) ENABLED + still registered -> no failure, pause-lifted note emitted
    def test_enabled_but_still_registered_notes_pause_lifted(self):
        write_jobs(self.cron_dir, [
            {"name": "Aero night CCD lane dispatch", "enabled": True},
        ])
        write_registry(self.registry_path, [
            {
                "name": "Aero night CCD lane dispatch",
                "since": "2026-09-11",
                "by": "founder",
                "reason": "manual handover mode - the founder drives the CCD lane builds by hand",
                "ref": "ops/ecss-program/HANDOVER-MANUAL-RUN.md",
            }
        ])
        system_audit.check_crons()
        self.assertEqual(
            [f for f in self._crons_failures()
             if "Aero night CCD lane dispatch" in f],
            [],
        )
        self.assertTrue(
            any("lifted" in n.lower() and "Aero night CCD lane dispatch" in n
                for n in system_audit.notes)
        )

    # (f) registry reason text reaches the emitted note
    def test_pause_reason_reaches_note(self):
        write_jobs(self.cron_dir, [
            {"name": "Aero night CCD lane dispatch", "enabled": False},
        ])
        write_registry(self.registry_path, [
            {
                "name": "Aero night CCD lane dispatch",
                "since": "2026-09-11",
                "by": "founder",
                "reason": "manual handover mode - the founder drives the CCD lane builds by hand",
                "ref": "ops/ecss-program/HANDOVER-MANUAL-RUN.md",
            }
        ])
        system_audit.check_crons()
        self.assertTrue(
            any("manual handover mode - the founder drives the CCD lane builds by hand" in n
                for n in system_audit.notes)
        )


if __name__ == "__main__":
    unittest.main()
