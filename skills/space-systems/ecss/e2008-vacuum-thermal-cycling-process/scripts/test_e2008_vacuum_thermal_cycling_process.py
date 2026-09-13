"""Contract tests for the clause 5.5.3.11.2 vacuum-cycling continuity monitoring logic."""

import unittest

from e2008_vacuum_thermal_cycling_process_logic import (
    CONDUCTING_ITEM_CLASSES,
    ITEM_CLASSES,
    LIMIT_TOLERANCE,
    NON_CONDUCTING_ITEM_CLASSES,
    assess_continuity_monitoring,
    at_or_above,
    at_or_below,
    build_channel_assignment,
    categorize_monitoring_scope,
    evaluate_monitoring_window,
    evaluate_sampling,
    merge_gaps,
    required_sample_interval_s,
)

# Three conducting items, each on its own channel, plus one item no continuity
# monitor can watch at all.
ITEMS = [
    {"item_id": "string-1", "item_class": "solar-cell-string", "monitor_channel": "ch-1"},
    {"item_id": "bus-joint-1", "item_class": "bus-bar-joint", "monitor_channel": "ch-2"},
    {"item_id": "diode-1", "item_class": "bypass-diode", "monitor_channel": "ch-3"},
    {"item_id": "bond-1", "item_class": "substrate-bondline"},
]

RUN = {"start_s": 0.0, "end_s": 36000.0}


def _monitor(**overrides):
    monitor = {
        "sample_interval_s": 0.0005,
        "min_event_duration_s": 0.001,
        "samples_per_event": 2,
        "start_s": 0.0,
        "end_s": 36000.0,
        "gaps": [],
        "max_unmonitored_time_s": 60.0,
        "max_single_gap_s": 30.0,
    }
    monitor.update(overrides)
    return monitor


def _spec(**overrides):
    spec = {
        "items": [dict(item) for item in ITEMS],
        "available_channels": 8,
        "monitor": _monitor(),
        "run": dict(RUN),
    }
    spec.update(overrides)
    return spec


class BoundHelperTests(unittest.TestCase):
    def test_value_below_upper_bound_passes(self):
        self.assertTrue(at_or_below(10.0, 60.0))

    def test_value_above_upper_bound_fails(self):
        self.assertFalse(at_or_below(90.0, 60.0))

    def test_exact_equality_respects_upper_bound(self):
        self.assertTrue(at_or_below(60.0, 60.0))

    def test_equality_within_tolerance_respects_upper_bound(self):
        self.assertTrue(at_or_below(60.0 + LIMIT_TOLERANCE / 2.0, 60.0))

    def test_exact_equality_respects_lower_bound(self):
        self.assertTrue(at_or_above(60.0, 60.0))

    def test_non_numeric_argument_rejected(self):
        with self.assertRaises(ValueError):
            at_or_below("60", 60.0)


class ScopeGroupingTests(unittest.TestCase):
    def test_conducting_and_non_conducting_are_separated(self):
        scope = categorize_monitoring_scope(ITEMS)
        self.assertEqual(len(scope["requires_monitoring"]), 3)
        self.assertEqual(len(scope["not_monitorable"]), 1)
        self.assertEqual(scope["declared_items"], 4)

    def test_the_two_class_groups_do_not_overlap(self):
        self.assertEqual(
            CONDUCTING_ITEM_CLASSES & NON_CONDUCTING_ITEM_CLASSES, frozenset()
        )
        self.assertEqual(
            ITEM_CLASSES, CONDUCTING_ITEM_CLASSES | NON_CONDUCTING_ITEM_CLASSES
        )

    def test_unrecognised_item_class_rejected(self):
        with self.assertRaises(ValueError):
            categorize_monitoring_scope([{"item_id": "x", "item_class": "sail"}])

    def test_duplicate_item_id_rejected(self):
        with self.assertRaises(ValueError):
            categorize_monitoring_scope([
                {"item_id": "dup", "item_class": "harness"},
                {"item_id": "dup", "item_class": "bus-bar-joint"},
            ])

    def test_empty_item_id_rejected(self):
        with self.assertRaises(ValueError):
            categorize_monitoring_scope([{"item_id": "  ", "item_class": "harness"}])

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            categorize_monitoring_scope([])


class ChannelAssignmentTests(unittest.TestCase):
    def test_a_complete_plan_reports_no_finding(self):
        plan = build_channel_assignment(categorize_monitoring_scope(ITEMS), 8)
        self.assertTrue(plan["complete"])
        self.assertEqual(plan["channels_used"], 3)
        self.assertAlmostEqual(plan["monitoring_coverage_fraction"], 1.0, places=12)

    def test_conducting_item_without_a_channel_is_named(self):
        items = [dict(item) for item in ITEMS]
        del items[1]["monitor_channel"]
        plan = build_channel_assignment(categorize_monitoring_scope(items), 8)
        self.assertEqual(plan["unmonitored_items"], ["bus-joint-1"])
        self.assertFalse(plan["complete"])
        self.assertAlmostEqual(
            plan["monitoring_coverage_fraction"], 2.0 / 3.0, places=12
        )

    def test_channel_on_a_non_conducting_item_is_a_finding(self):
        items = [dict(item) for item in ITEMS]
        items[3]["monitor_channel"] = "ch-4"
        plan = build_channel_assignment(categorize_monitoring_scope(items), 8)
        self.assertEqual(len(plan["findings"]), 1)
        self.assertIn("bond-1", plan["findings"][0])

    def test_too_few_channels_is_a_finding(self):
        plan = build_channel_assignment(categorize_monitoring_scope(ITEMS), 2)
        self.assertFalse(plan["complete"])
        self.assertIn("2", plan["findings"][0])

    def test_channel_claimed_twice_rejected(self):
        items = [dict(item) for item in ITEMS]
        items[1]["monitor_channel"] = "ch-1"
        with self.assertRaises(ValueError):
            build_channel_assignment(categorize_monitoring_scope(items), 8)

    def test_negative_channel_count_rejected(self):
        with self.assertRaises(ValueError):
            build_channel_assignment(categorize_monitoring_scope(ITEMS), -1)

    def test_non_scope_argument_rejected(self):
        with self.assertRaises(ValueError):
            build_channel_assignment({"items": []}, 8)


class SamplingTests(unittest.TestCase):
    def test_required_interval_splits_the_shortest_event(self):
        self.assertAlmostEqual(required_sample_interval_s(0.001, 2), 0.0005, places=12)

    def test_zero_samples_per_event_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_interval_s(0.001, 0)

    def test_non_integer_samples_per_event_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_interval_s(0.001, 2.5)

    def test_zero_event_duration_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_interval_s(0.0, 2)

    def test_interval_exactly_on_the_requirement_is_adequate(self):
        sampling = evaluate_sampling(_monitor(sample_interval_s=0.0005))
        self.assertTrue(sampling["adequate"])
        self.assertEqual(sampling["findings"], [])

    def test_too_slow_an_interval_is_a_finding(self):
        sampling = evaluate_sampling(_monitor(sample_interval_s=0.01))
        self.assertFalse(sampling["adequate"])
        self.assertEqual(len(sampling["findings"]), 1)

    def test_sample_rate_and_resolvable_event_are_reported(self):
        sampling = evaluate_sampling(_monitor(sample_interval_s=0.0005))
        self.assertAlmostEqual(sampling["sample_rate_hz"], 2000.0, places=6)
        self.assertAlmostEqual(
            sampling["shortest_resolvable_event_s"], 0.001, places=12
        )

    def test_missing_monitor_key_rejected(self):
        monitor = _monitor()
        del monitor["min_event_duration_s"]
        with self.assertRaises(ValueError):
            evaluate_sampling(monitor)


class GapMergingTests(unittest.TestCase):
    def test_overlapping_gaps_are_merged_once(self):
        merged = merge_gaps(
            [{"start_s": 100.0, "end_s": 200.0}, {"start_s": 150.0, "end_s": 250.0}],
            0.0,
            1000.0,
        )
        self.assertEqual(len(merged), 1)
        self.assertAlmostEqual(merged[0]["end_s"] - merged[0]["start_s"], 150.0, places=9)

    def test_disjoint_gaps_stay_separate(self):
        merged = merge_gaps(
            [{"start_s": 100.0, "end_s": 200.0}, {"start_s": 400.0, "end_s": 450.0}],
            0.0,
            1000.0,
        )
        self.assertEqual(len(merged), 2)

    def test_gap_outside_the_run_is_dropped(self):
        merged = merge_gaps([{"start_s": 2000.0, "end_s": 3000.0}], 0.0, 1000.0)
        self.assertEqual(merged, [])

    def test_gap_straddling_the_run_end_is_clipped(self):
        merged = merge_gaps([{"start_s": 900.0, "end_s": 3000.0}], 0.0, 1000.0)
        self.assertAlmostEqual(merged[0]["end_s"], 1000.0, places=9)

    def test_inverted_gap_rejected(self):
        with self.assertRaises(ValueError):
            merge_gaps([{"start_s": 300.0, "end_s": 100.0}], 0.0, 1000.0)

    def test_inverted_run_window_rejected(self):
        with self.assertRaises(ValueError):
            merge_gaps([], 1000.0, 0.0)


class MonitoringWindowTests(unittest.TestCase):
    def test_a_continuous_run_reports_full_coverage(self):
        window = evaluate_monitoring_window(RUN, _monitor())
        self.assertTrue(window["continuous"])
        self.assertAlmostEqual(window["monitored_fraction"], 1.0, places=12)
        self.assertAlmostEqual(window["unmonitored_time_s"], 0.0, places=9)

    def test_a_late_start_counts_as_unmonitored_time(self):
        window = evaluate_monitoring_window(RUN, _monitor(start_s=100.0))
        self.assertAlmostEqual(window["unmonitored_time_s"], 100.0, places=9)
        self.assertFalse(window["continuous"])

    def test_an_early_stop_counts_as_unmonitored_time(self):
        window = evaluate_monitoring_window(RUN, _monitor(end_s=35990.0))
        self.assertAlmostEqual(window["unmonitored_time_s"], 10.0, places=9)
        self.assertTrue(window["continuous"])

    def test_logged_gaps_accumulate_and_the_longest_is_reported(self):
        window = evaluate_monitoring_window(
            RUN,
            _monitor(gaps=[
                {"start_s": 1000.0, "end_s": 1010.0},
                {"start_s": 5000.0, "end_s": 5025.0},
            ]),
        )
        self.assertAlmostEqual(window["unmonitored_time_s"], 35.0, places=9)
        self.assertAlmostEqual(window["longest_gap_s"], 25.0, places=9)
        self.assertEqual(window["gap_count"], 2)

    def test_a_single_long_gap_breaks_its_own_limit(self):
        window = evaluate_monitoring_window(
            RUN, _monitor(gaps=[{"start_s": 1000.0, "end_s": 1040.0}])
        )
        self.assertFalse(window["continuous"])
        self.assertEqual(len(window["findings"]), 1)

    def test_unmonitored_time_exactly_on_its_limit_is_accepted(self):
        window = evaluate_monitoring_window(
            RUN,
            _monitor(
                gaps=[{"start_s": 1000.0, "end_s": 1030.0},
                      {"start_s": 5000.0, "end_s": 5030.0}],
            ),
        )
        self.assertAlmostEqual(window["unmonitored_time_s"], 60.0, places=9)
        self.assertTrue(window["continuous"])

    def test_inverted_monitor_window_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_monitoring_window(RUN, _monitor(start_s=500.0, end_s=100.0))

    def test_missing_run_key_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_monitoring_window({"start_s": 0.0}, _monitor())


class ContinuityMonitoringAssessmentTests(unittest.TestCase):
    def test_a_sound_plan_is_acceptable(self):
        result = assess_continuity_monitoring(_spec())
        self.assertTrue(result["plan_acceptable"])
        self.assertEqual(result["findings"], [])

    def test_findings_accumulate_across_the_three_checks(self):
        items = [dict(item) for item in ITEMS]
        del items[0]["monitor_channel"]
        result = assess_continuity_monitoring(
            _spec(
                items=items,
                monitor=_monitor(
                    sample_interval_s=0.01,
                    gaps=[{"start_s": 10.0, "end_s": 200.0}],
                ),
            )
        )
        self.assertFalse(result["plan_acceptable"])
        self.assertEqual(len(result["findings"]), 4)

    def test_the_non_monitorable_item_is_still_reported(self):
        result = assess_continuity_monitoring(_spec())
        self.assertEqual(len(result["scope"]["not_monitorable"]), 1)
        self.assertEqual(result["scope"]["not_monitorable"][0]["item_id"], "bond-1")

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["monitor"]
        with self.assertRaises(ValueError):
            assess_continuity_monitoring(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_continuity_monitoring(["items"])


if __name__ == "__main__":
    unittest.main()
