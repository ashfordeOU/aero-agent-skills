#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.4.4 pre-launch
readiness verification.

Exercises scripts/e1002_pre_launch_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - transport readiness flags
out-of-limit events; storage readiness flags expired or out-of-limit
items; launch-site readiness requires every required check present and
passed; launch-configuration readiness requires as-built to match the
baseline and no open critical non-conformance; the combined assessment
is a go only if all four categories are ready.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_pre_launch_logic as pl  # noqa: E402


class CheckTransportReadinessTest(unittest.TestCase):
    def test_all_within_limits_is_ready(self):
        events = [{"id": "T-1", "within_limits": True}, {"id": "T-2", "within_limits": True}]
        result = pl.check_transport_readiness(events)
        self.assertEqual(result, {"category": "transport", "ready": True, "blocking_reasons": []})

    def test_out_of_limit_event_blocks(self):
        events = [{"id": "T-1", "within_limits": True}, {"id": "T-2", "within_limits": False}]
        result = pl.check_transport_readiness(events)
        self.assertFalse(result["ready"])
        self.assertEqual(result["blocking_reasons"], ["T-2"])

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            pl.check_transport_readiness([{"id": "T-1"}])


class CheckStorageReadinessTest(unittest.TestCase):
    def test_not_expired_within_limits_is_ready(self):
        items = [{"id": "S-1", "shelf_life_expiry": "2026-12-01", "within_limits": True}]
        result = pl.check_storage_readiness(items, as_of_date="2026-09-09")
        self.assertEqual(result, {"category": "storage", "ready": True, "blocking_reasons": []})

    def test_expired_item_blocks(self):
        items = [{"id": "S-1", "shelf_life_expiry": "2026-01-01", "within_limits": True}]
        result = pl.check_storage_readiness(items, as_of_date="2026-09-09")
        self.assertEqual(result["blocking_reasons"], ["S-1"])

    def test_no_expiry_is_not_life_limited(self):
        items = [{"id": "S-1", "shelf_life_expiry": None, "within_limits": True}]
        result = pl.check_storage_readiness(items, as_of_date="2026-09-09")
        self.assertTrue(result["ready"])

    def test_out_of_limit_environment_blocks(self):
        items = [{"id": "S-1", "shelf_life_expiry": None, "within_limits": False}]
        result = pl.check_storage_readiness(items, as_of_date="2026-09-09")
        self.assertEqual(result["blocking_reasons"], ["S-1"])

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            pl.check_storage_readiness([{"id": "S-1", "within_limits": True}], as_of_date="2026-09-09")


class CheckLaunchSiteActivitiesTest(unittest.TestCase):
    def test_all_completed_and_passed_is_ready(self):
        result = pl.check_launch_site_activities(
            ["LS-1", "LS-2"], {"LS-1": True, "LS-2": True},
        )
        self.assertEqual(result, {"category": "launch_site", "ready": True, "blocking_reasons": []})

    def test_missing_check_blocks(self):
        result = pl.check_launch_site_activities(["LS-1", "LS-2"], {"LS-1": True})
        self.assertEqual(result["blocking_reasons"], ["LS-2"])

    def test_failed_check_blocks(self):
        result = pl.check_launch_site_activities(
            ["LS-1", "LS-2"], {"LS-1": True, "LS-2": False},
        )
        self.assertEqual(result["blocking_reasons"], ["LS-2"])

    def test_does_not_mutate_inputs(self):
        required = ["LS-1"]
        completed = {"LS-1": True}
        pl.check_launch_site_activities(required, completed)
        self.assertEqual(required, ["LS-1"])
        self.assertEqual(completed, {"LS-1": True})


class CheckLaunchConfigurationTest(unittest.TestCase):
    def test_matching_baseline_no_open_nc_is_ready(self):
        result = pl.check_launch_configuration(
            as_built={"comp-a": "rev3"},
            baseline={"comp-a": "rev3"},
            open_nonconformances=[],
        )
        self.assertEqual(
            result,
            {"category": "launch_configuration", "ready": True, "blocking_reasons": []},
        )

    def test_mismatched_component_blocks(self):
        result = pl.check_launch_configuration(
            as_built={"comp-a": "rev2"},
            baseline={"comp-a": "rev3"},
            open_nonconformances=[],
        )
        self.assertEqual(result["blocking_reasons"], ["comp-a"])

    def test_undispositioned_critical_nc_blocks(self):
        result = pl.check_launch_configuration(
            as_built={"comp-a": "rev3"},
            baseline={"comp-a": "rev3"},
            open_nonconformances=[{"id": "NC-1", "severity": "critical", "dispositioned": False}],
        )
        self.assertEqual(result["blocking_reasons"], ["NC-1"])

    def test_dispositioned_critical_nc_does_not_block(self):
        result = pl.check_launch_configuration(
            as_built={"comp-a": "rev3"},
            baseline={"comp-a": "rev3"},
            open_nonconformances=[{"id": "NC-1", "severity": "critical", "dispositioned": True}],
        )
        self.assertTrue(result["ready"])

    def test_minor_nc_does_not_block(self):
        result = pl.check_launch_configuration(
            as_built={"comp-a": "rev3"},
            baseline={"comp-a": "rev3"},
            open_nonconformances=[{"id": "NC-1", "severity": "minor", "dispositioned": False}],
        )
        self.assertTrue(result["ready"])

    def test_does_not_mutate_inputs(self):
        as_built = {"comp-a": "rev3"}
        baseline = {"comp-a": "rev3"}
        ncs = [{"id": "NC-1", "severity": "critical", "dispositioned": False}]
        pl.check_launch_configuration(as_built, baseline, ncs)
        self.assertEqual(as_built, {"comp-a": "rev3"})
        self.assertEqual(baseline, {"comp-a": "rev3"})
        self.assertEqual(ncs, [{"id": "NC-1", "severity": "critical", "dispositioned": False}])


class AssessPreLaunchReadinessTest(unittest.TestCase):
    READY_KWARGS = dict(
        transport_events=[{"id": "T-1", "within_limits": True}],
        storage_items=[{"id": "S-1", "shelf_life_expiry": None, "within_limits": True}],
        as_of_date="2026-09-09",
        required_checks=["LS-1"],
        completed_checks={"LS-1": True},
        as_built={"comp-a": "rev3"},
        baseline={"comp-a": "rev3"},
        open_nonconformances=[],
    )

    def test_all_ready_is_go(self):
        result = pl.assess_pre_launch_readiness(**self.READY_KWARGS)
        self.assertTrue(result["go"])
        self.assertEqual(len(result["categories"]), 4)
        self.assertEqual(
            [c["category"] for c in result["categories"]],
            list(pl.CATEGORIES),
        )

    def test_single_category_failure_is_no_go(self):
        kwargs = dict(self.READY_KWARGS)
        kwargs["completed_checks"] = {"LS-1": False}
        result = pl.assess_pre_launch_readiness(**kwargs)
        self.assertFalse(result["go"])
        launch_site = next(c for c in result["categories"] if c["category"] == "launch_site")
        self.assertEqual(launch_site["blocking_reasons"], ["LS-1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
