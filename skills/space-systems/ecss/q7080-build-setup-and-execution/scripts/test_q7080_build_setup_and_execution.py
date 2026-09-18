"""Contract tests for the build set-up and execution logic."""

import copy
import unittest

from q7080_build_setup_and_execution_logic import (
    DEFAULT_ABORT_AFTER_LAYERS,
    check_value,
    evaluate_channel,
    evaluate_event_counts,
    evaluate_startup_checks,
    execute_build,
    layer_excursions,
    longest_consecutive_layers,
    monitoring_coverage,
    start_permitted,
    validate_limits,
)

REQUIREMENTS = {
    "platform_flatness_mm": {"max": 0.05},
    "platform_preheat_c": {"min": 150.0, "max": 200.0},
    "chamber_oxygen_ppm": {"max": 1000.0},
    "powder_lot_moisture_pct": {"max": 0.05},
}

RECORDED = {
    "platform_flatness_mm": 0.03,
    "platform_preheat_c": 170.0,
    "chamber_oxygen_ppm": 400.0,
    "powder_lot_moisture_pct": 0.02,
}

TOTAL_LAYERS = 10


def samples(value, layers=None, overrides=None):
    layers = range(1, TOTAL_LAYERS + 1) if layers is None else layers
    overrides = overrides or {}
    return [(layer, overrides.get(layer, value)) for layer in layers]


def channels():
    return {
        "chamber_oxygen_ppm": {"limits": {"max": 1000.0}, "samples": samples(400.0)},
        "beam_power_deviation_pct": {
            "limits": {"min": -3.0, "max": 3.0},
            "samples": samples(0.5),
        },
    }


def spec(startup=None, chans=None, **extra):
    base = {
        "startup_records": dict(RECORDED) if startup is None else startup,
        "startup_requirements": copy.deepcopy(REQUIREMENTS),
        "total_layers": TOTAL_LAYERS,
        "channels": channels() if chans is None else chans,
        "event_counts": {"recoater_interruptions": 1},
        "event_limits": {"recoater_interruptions": 2},
    }
    base.update(extra)
    return base


class LimitTests(unittest.TestCase):
    def test_limits_returned_as_a_pair(self):
        self.assertEqual(validate_limits("x", {"min": 1.0, "max": 2.0}), (1.0, 2.0))

    def test_single_sided_limit_allowed(self):
        self.assertEqual(validate_limits("x", {"max": 2.0}), (None, 2.0))

    def test_empty_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits("x", {})

    def test_inverted_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits("x", {"min": 5.0, "max": 1.0})

    def test_value_inside_limits_is_ok(self):
        self.assertEqual(check_value(400.0, {"max": 1000.0}), "ok")

    def test_value_above_maximum_named(self):
        self.assertEqual(check_value(1500.0, {"max": 1000.0}), "above-maximum")

    def test_value_below_minimum_named(self):
        self.assertEqual(check_value(-4.0, {"min": -3.0, "max": 3.0}), "below-minimum")

    def test_value_exactly_on_the_limit_is_ok(self):
        self.assertEqual(check_value(1000.0, {"max": 1000.0}), "ok")

    def test_non_finite_reading_rejected(self):
        with self.assertRaises(ValueError):
            check_value(float("nan"), {"max": 1000.0})


class StartupTests(unittest.TestCase):
    def test_complete_checklist_is_all_ok(self):
        records = evaluate_startup_checks(RECORDED, REQUIREMENTS)
        self.assertEqual(len(records), 4)
        self.assertTrue(start_permitted(records))

    def test_unrecorded_check_blocks_the_start(self):
        recorded = dict(RECORDED)
        del recorded["platform_flatness_mm"]
        records = evaluate_startup_checks(recorded, REQUIREMENTS)
        self.assertFalse(start_permitted(records))
        status = {r["check"]: r["status"] for r in records}
        self.assertEqual(status["platform_flatness_mm"], "unrecorded")

    def test_null_value_counts_as_unrecorded(self):
        recorded = dict(RECORDED, chamber_oxygen_ppm=None)
        records = evaluate_startup_checks(recorded, REQUIREMENTS)
        self.assertFalse(start_permitted(records))

    def test_out_of_limit_check_blocks_the_start(self):
        recorded = dict(RECORDED, platform_preheat_c=120.0)
        records = evaluate_startup_checks(recorded, REQUIREMENTS)
        self.assertFalse(start_permitted(records))

    def test_undeclared_record_rejected(self):
        recorded = dict(RECORDED, hopper_colour="green")
        with self.assertRaises(ValueError):
            evaluate_startup_checks(recorded, REQUIREMENTS)

    def test_empty_requirements_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_startup_checks(RECORDED, {})

    def test_empty_record_list_rejected(self):
        with self.assertRaises(ValueError):
            start_permitted([])


class MonitoringTests(unittest.TestCase):
    def test_in_band_channel_has_no_excursions(self):
        self.assertEqual(layer_excursions(samples(400.0), {"max": 1000.0}), [])

    def test_excursion_carries_its_layer(self):
        found = layer_excursions(samples(400.0, overrides={5: 1500.0}), {"max": 1000.0})
        self.assertEqual(found[0]["layer"], 5)
        self.assertEqual(found[0]["status"], "above-maximum")

    def test_duplicate_layer_sample_rejected(self):
        with self.assertRaises(ValueError):
            layer_excursions([(1, 400.0), (1, 500.0)], {"max": 1000.0})

    def test_zero_layer_index_rejected(self):
        with self.assertRaises(ValueError):
            layer_excursions([(0, 400.0)], {"max": 1000.0})

    def test_malformed_sample_rejected(self):
        with self.assertRaises(ValueError):
            layer_excursions([(1,)], {"max": 1000.0})

    def test_consecutive_run_counted(self):
        self.assertEqual(longest_consecutive_layers([4, 5, 6, 9]), 3)

    def test_isolated_excursions_run_of_one(self):
        self.assertEqual(longest_consecutive_layers([2, 7]), 1)

    def test_no_excursions_run_of_zero(self):
        self.assertEqual(longest_consecutive_layers([]), 0)

    def test_coverage_is_a_fraction_of_the_build(self):
        self.assertAlmostEqual(monitoring_coverage(range(1, 9), 10), 0.8, places=9)

    def test_full_coverage_is_one(self):
        self.assertAlmostEqual(monitoring_coverage(range(1, 11), 10), 1.0, places=9)

    def test_sample_above_the_build_height_rejected(self):
        with self.assertRaises(ValueError):
            monitoring_coverage([1, 2, 40], 10)

    def test_zero_total_layers_rejected(self):
        with self.assertRaises(ValueError):
            monitoring_coverage([1], 0)

    def test_channel_record_reports_run_and_coverage(self):
        record = evaluate_channel(
            "chamber_oxygen_ppm",
            {"limits": {"max": 1000.0}, "samples": samples(400.0, overrides={4: 1500.0, 5: 1500.0})},
            TOTAL_LAYERS,
        )
        self.assertEqual(record["longest_excursion_run"], 2)
        self.assertAlmostEqual(record["coverage"], 1.0, places=9)
        self.assertFalse(record["abort"])

    def test_channel_run_at_the_abort_threshold_aborts(self):
        record = evaluate_channel(
            "chamber_oxygen_ppm",
            {"limits": {"max": 1000.0},
             "samples": samples(400.0, overrides={4: 1500.0, 5: 1500.0, 6: 1500.0})},
            TOTAL_LAYERS,
            DEFAULT_ABORT_AFTER_LAYERS,
        )
        self.assertTrue(record["abort"])

    def test_channel_without_limits_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_channel("x", {"samples": samples(1.0)}, TOTAL_LAYERS)

    def test_zero_abort_threshold_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_channel(
                "x", {"limits": {"max": 1.0}, "samples": samples(0.5)}, TOTAL_LAYERS, 0
            )


class EventCountTests(unittest.TestCase):
    def test_counts_within_allowance_pass(self):
        self.assertEqual(
            evaluate_event_counts({"recoater_interruptions": 1},
                                  {"recoater_interruptions": 2}), []
        )

    def test_count_over_allowance_reported(self):
        finding = evaluate_event_counts({"recoater_interruptions": 4},
                                        {"recoater_interruptions": 2})[0]
        self.assertEqual(finding["count"], 4)

    def test_event_without_allowance_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_event_counts({"restarts": 1}, {"recoater_interruptions": 2})

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_event_counts({"recoater_interruptions": -1},
                                  {"recoater_interruptions": 2})


class DispositionTests(unittest.TestCase):
    def test_clean_build_completes(self):
        result = execute_build(spec())
        self.assertEqual(result["disposition"], "complete")
        self.assertEqual(result["findings"], [])

    def test_blocked_start_is_not_dispositioned_on_monitoring(self):
        recorded = dict(RECORDED, platform_flatness_mm=0.20)
        result = execute_build(spec(startup=recorded))
        self.assertEqual(result["disposition"], "start-blocked")
        self.assertEqual(result["channels"], [])

    def test_isolated_excursion_is_a_concession(self):
        chans = channels()
        chans["chamber_oxygen_ppm"]["samples"] = samples(400.0, overrides={5: 1500.0})
        result = execute_build(spec(chans=chans))
        self.assertEqual(result["disposition"], "complete-with-concession")

    def test_sustained_excursion_aborts_the_build(self):
        chans = channels()
        chans["chamber_oxygen_ppm"]["samples"] = samples(
            400.0, overrides={4: 1500.0, 5: 1500.0, 6: 1500.0}
        )
        result = execute_build(spec(chans=chans))
        self.assertEqual(result["disposition"], "aborted")
        self.assertTrue(any("consecutive layers" in b for b in result["blocking"]))

    def test_sparse_monitoring_is_a_concession(self):
        chans = channels()
        chans["beam_power_deviation_pct"]["samples"] = samples(0.5, layers=range(1, 9))
        result = execute_build(spec(chans=chans))
        self.assertEqual(result["disposition"], "complete-with-concession")
        self.assertTrue(any("of the layers" in f for f in result["findings"]))

    def test_coverage_exactly_at_the_minimum_passes(self):
        chans = channels()
        chans["beam_power_deviation_pct"]["samples"] = samples(0.5, layers=range(1, 10))
        result = execute_build(spec(chans=chans, min_coverage=0.9))
        self.assertEqual(result["disposition"], "complete")

    def test_event_over_allowance_is_a_concession(self):
        result = execute_build(spec(event_counts={"recoater_interruptions": 5}))
        self.assertEqual(result["disposition"], "complete-with-concession")

    def test_empty_channel_map_rejected(self):
        with self.assertRaises(ValueError):
            execute_build(spec(chans={}))

    def test_missing_spec_key_rejected(self):
        broken = spec()
        del broken["total_layers"]
        with self.assertRaises(ValueError):
            execute_build(broken)

    def test_out_of_range_min_coverage_rejected(self):
        with self.assertRaises(ValueError):
            execute_build(spec(min_coverage=1.5))


if __name__ == "__main__":
    unittest.main(verbosity=1)
