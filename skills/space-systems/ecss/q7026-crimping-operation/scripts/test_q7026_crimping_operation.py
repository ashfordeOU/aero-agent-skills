#!/usr/bin/env python3
"""Contract test for the crimp cycle: setup, completion, compression (offline)."""

import copy
import unittest

from q7026_crimping_operation_logic import (
    COMPRESSION_IN_BAND,
    COMPRESSION_OVER,
    COMPRESSION_UNDER,
    CRIMP_ACCEPT,
    CRIMP_REJECT,
    CRIMP_REMAKE,
    authorize_cycle,
    evaluate_calibration,
    evaluate_compression,
    evaluate_cycle_completion,
    evaluate_selector,
    evaluate_tooling,
    lookup_setup,
    perform_crimp,
    summarize_run,
    validate_setup_table,
)

TABLE = {
    "M39029-22": {
        "die_part": "M22520-1-01",
        "positioner": "K13-1",
        "gauges": {
            "22": {
                "selector": 4,
                "height_target_mm": 1.30,
                "height_tolerance_mm": 0.06,
            },
            "24": {
                "selector": 3,
                "height_target_mm": 1.18,
                "height_tolerance_mm": 0.06,
            },
        },
    },
    "M39029-20": {
        "die_part": "M22520-1-02",
        "positioner": "K42",
        "gauges": {
            "20": {
                "selector": 6,
                "height_target_mm": 1.55,
                "height_tolerance_mm": 0.07,
            }
        },
    },
}

GOOD = {
    "identifier": "C-001",
    "contact": "M39029-22",
    "gauge": "22",
    "die_part": "M22520-1-01",
    "positioner": "K13-1",
    "selector_setting": 4,
    "calibration_days_remaining": 45.0,
    "cycles_since_calibration": 1200,
    "cycle_interval": 10000,
    "cycle_completed": True,
    "crimps_on_barrel": 1,
    "ratchet_fitted": True,
    "crimp_height_mm": 1.30,
    "wire_margin_mm": 60.0,
    "remake_margin_mm": 20.0,
}


def _job(**overrides):
    job = copy.deepcopy(GOOD)
    job.update(overrides)
    return job


def _entries(contact="M39029-22", gauge="22"):
    return lookup_setup(validate_setup_table(TABLE), contact, gauge)


class SetupTableTests(unittest.TestCase):
    def test_valid_table_normalises_bands(self):
        table = validate_setup_table(TABLE)
        spec = table["M39029-22"]["gauges"]["22"]
        self.assertAlmostEqual(spec["height_min_mm"], 1.24, places=9)
        self.assertAlmostEqual(spec["height_max_mm"], 1.36, places=9)

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_setup_table({})

    def test_contact_with_no_gauges_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["gauges"] = {}
        with self.assertRaises(ValueError):
            validate_setup_table(bad)

    def test_tolerance_swallowing_the_target_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["gauges"]["22"]["height_tolerance_mm"] = 1.5
        with self.assertRaises(ValueError):
            validate_setup_table(bad)

    def test_non_integer_selector_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["gauges"]["22"]["selector"] = "four"
        with self.assertRaises(ValueError):
            validate_setup_table(bad)

    def test_untabulated_contact_rejected(self):
        with self.assertRaises(ValueError):
            lookup_setup(validate_setup_table(TABLE), "M39029-16", "16")

    def test_gauge_the_contact_does_not_accept_rejected(self):
        with self.assertRaises(ValueError):
            lookup_setup(validate_setup_table(TABLE), "M39029-22", "20")


class ToolingTests(unittest.TestCase):
    def test_correct_die_and_positioner_pass(self):
        entry, _ = _entries()
        result = evaluate_tooling(entry, "M22520-1-01", "K13-1")
        self.assertTrue(result["correct"])
        self.assertEqual(result["findings"], [])

    def test_wrong_die_is_reported(self):
        entry, _ = _entries()
        result = evaluate_tooling(entry, "M22520-1-02", "K13-1")
        self.assertFalse(result["die_correct"])
        self.assertTrue(any("die" in f for f in result["findings"]))

    def test_wrong_positioner_is_reported(self):
        entry, _ = _entries()
        result = evaluate_tooling(entry, "M22520-1-01", "K42")
        self.assertFalse(result["positioner_correct"])

    def test_empty_die_name_rejected(self):
        entry, _ = _entries()
        with self.assertRaises(ValueError):
            evaluate_tooling(entry, "", "K13-1")


class SelectorTests(unittest.TestCase):
    def test_correct_selector_passes(self):
        _, gauge_entry = _entries()
        self.assertTrue(evaluate_selector(4, gauge_entry)["correct"])

    def test_wrong_selector_is_reported(self):
        _, gauge_entry = _entries()
        result = evaluate_selector(6, gauge_entry)
        self.assertFalse(result["correct"])
        self.assertEqual(result["expected"], 4)

    def test_selector_for_the_other_gauge_is_still_wrong(self):
        _, gauge_entry = _entries(gauge="24")
        self.assertFalse(evaluate_selector(4, gauge_entry)["correct"])

    def test_non_integer_selector_rejected(self):
        _, gauge_entry = _entries()
        with self.assertRaises(ValueError):
            evaluate_selector(4.0, gauge_entry)


class CalibrationTests(unittest.TestCase):
    def test_tool_in_date_and_under_interval_is_current(self):
        result = evaluate_calibration(30.0, 100, 10000)
        self.assertTrue(result["current"])

    def test_tool_due_today_is_still_current(self):
        result = evaluate_calibration(0.1 + 0.2 - 0.3, 100, 10000)
        self.assertTrue(result["date_current"])

    def test_tool_exactly_on_its_cycle_interval_is_still_current(self):
        result = evaluate_calibration(30.0, 10000, 10000)
        self.assertTrue(result["cycles_current"])
        self.assertEqual(result["cycles_remaining"], 0)

    def test_lapsed_date_is_reported(self):
        result = evaluate_calibration(-2.0, 100, 10000)
        self.assertFalse(result["current"])
        self.assertTrue(any("lapsed" in f for f in result["findings"]))

    def test_cycle_count_past_the_interval_is_reported(self):
        result = evaluate_calibration(30.0, 10001, 10000)
        self.assertFalse(result["cycles_current"])

    def test_zero_cycle_interval_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_calibration(30.0, 100, 0)


class CycleCompletionTests(unittest.TestCase):
    def test_one_full_ratcheted_cycle_accepts(self):
        result = evaluate_cycle_completion(True, 1, True)
        self.assertEqual(result["disposition"], CRIMP_ACCEPT)

    def test_interrupted_cycle_is_a_remake(self):
        result = evaluate_cycle_completion(False, 1, True)
        self.assertEqual(result["disposition"], CRIMP_REMAKE)

    def test_second_cycle_on_one_barrel_is_a_remake(self):
        result = evaluate_cycle_completion(True, 2, True)
        self.assertEqual(result["disposition"], CRIMP_REMAKE)
        self.assertTrue(any("work-harden" in f for f in result["findings"]))

    def test_no_ratchet_is_a_remake(self):
        result = evaluate_cycle_completion(True, 1, False)
        self.assertEqual(result["disposition"], CRIMP_REMAKE)

    def test_barrel_with_no_crimp_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cycle_completion(True, 0, True)

    def test_non_boolean_completion_flag_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cycle_completion("yes", 1, True)


class CompressionTests(unittest.TestCase):
    def test_height_on_target_is_in_band(self):
        _, gauge_entry = _entries()
        result = evaluate_compression(1.30, gauge_entry)
        self.assertEqual(result["state"], COMPRESSION_IN_BAND)
        self.assertEqual(result["disposition"], CRIMP_ACCEPT)

    def test_height_exactly_on_the_floor_is_in_band(self):
        _, gauge_entry = _entries()
        result = evaluate_compression(gauge_entry["height_min_mm"], gauge_entry)
        self.assertEqual(result["state"], COMPRESSION_IN_BAND)

    def test_height_exactly_on_the_ceiling_is_in_band(self):
        _, gauge_entry = _entries()
        result = evaluate_compression(gauge_entry["height_max_mm"], gauge_entry)
        self.assertEqual(result["state"], COMPRESSION_IN_BAND)

    def test_height_below_the_floor_is_an_over_crimp(self):
        _, gauge_entry = _entries()
        result = evaluate_compression(1.10, gauge_entry)
        self.assertEqual(result["state"], COMPRESSION_OVER)
        self.assertEqual(result["disposition"], CRIMP_REMAKE)

    def test_height_above_the_ceiling_is_an_under_crimp(self):
        _, gauge_entry = _entries()
        result = evaluate_compression(1.50, gauge_entry)
        self.assertEqual(result["state"], COMPRESSION_UNDER)

    def test_deviation_from_target_is_reported(self):
        _, gauge_entry = _entries()
        result = evaluate_compression(1.36, gauge_entry)
        self.assertAlmostEqual(result["deviation_mm"], 0.06, places=9)

    def test_zero_height_rejected(self):
        _, gauge_entry = _entries()
        with self.assertRaises(ValueError):
            evaluate_compression(0.0, gauge_entry)


class AuthorizationTests(unittest.TestCase):
    def test_correct_setup_authorizes(self):
        entry, gauge_entry = _entries()
        result = authorize_cycle(entry, gauge_entry, _job())
        self.assertTrue(result["authorized"])
        self.assertEqual(result["blockers"], [])

    def test_wrong_die_blocks_the_cycle(self):
        entry, gauge_entry = _entries()
        result = authorize_cycle(entry, gauge_entry, _job(die_part="M22520-1-02"))
        self.assertFalse(result["authorized"])
        self.assertTrue(any(b.startswith("tooling:") for b in result["blockers"]))

    def test_lapsed_calibration_blocks_the_cycle(self):
        entry, gauge_entry = _entries()
        result = authorize_cycle(
            entry, gauge_entry, _job(calibration_days_remaining=-1.0)
        )
        self.assertFalse(result["authorized"])
        self.assertTrue(any(b.startswith("calibration:") for b in result["blockers"]))

    def test_non_mapping_setup_rejected(self):
        entry, gauge_entry = _entries()
        with self.assertRaises(ValueError):
            authorize_cycle(entry, gauge_entry, "a set tool")


class PerformCrimpTests(unittest.TestCase):
    def test_good_crimp_accepts(self):
        result = perform_crimp(_job(), TABLE)
        self.assertEqual(result["disposition"], CRIMP_ACCEPT)
        self.assertTrue(result["authorized"])

    def test_over_crimp_with_wire_left_is_a_remake(self):
        result = perform_crimp(_job(crimp_height_mm=1.05), TABLE)
        self.assertEqual(result["disposition"], CRIMP_REMAKE)

    def test_over_crimp_without_wire_left_is_a_reject(self):
        result = perform_crimp(_job(crimp_height_mm=1.05, wire_margin_mm=2.0), TABLE)
        self.assertEqual(result["disposition"], CRIMP_REJECT)
        self.assertTrue(any(f.startswith("remake:") for f in result["findings"]))

    def test_unauthorized_setup_shows_in_the_findings(self):
        result = perform_crimp(_job(selector_setting=6), TABLE)
        self.assertFalse(result["authorized"])
        self.assertTrue(any(f.startswith("authorization:") for f in result["findings"]))

    def test_findings_are_prefixed_by_stage(self):
        result = perform_crimp(_job(cycle_completed=False), TABLE)
        self.assertTrue(any(f.startswith("cycle:") for f in result["findings"]))

    def test_non_mapping_job_rejected(self):
        with self.assertRaises(ValueError):
            perform_crimp("a crimp", TABLE)


class RunSummaryTests(unittest.TestCase):
    def test_clean_run_reports_full_yield(self):
        run = {"setup_table": TABLE, "crimps": [_job(), _job(identifier="C-002")]}
        result = summarize_run(run)
        self.assertAlmostEqual(result["first_pass_yield"], 1.0, places=9)
        self.assertEqual(result["worst_disposition"], CRIMP_ACCEPT)

    def test_yield_counts_only_accepted_crimps(self):
        run = {
            "setup_table": TABLE,
            "crimps": [_job(), _job(identifier="C-002", crimp_height_mm=1.05)],
        }
        result = summarize_run(run)
        self.assertAlmostEqual(result["first_pass_yield"], 0.5, places=9)
        self.assertEqual(result["not_accepted"], ["C-002"])

    def test_unauthorized_cycles_are_counted(self):
        run = {
            "setup_table": TABLE,
            "crimps": [_job(), _job(identifier="C-003", die_part="M22520-1-02")],
        }
        result = summarize_run(run)
        self.assertEqual(result["unauthorized_cycles"], 1)

    def test_unrecorded_crimps_flag_the_record(self):
        run = {"setup_table": TABLE, "crimps": [_job()], "declared_crimp_count": 5}
        result = summarize_run(run)
        self.assertEqual(result["unrecorded_crimp_count"], 4)
        self.assertFalse(result["record_complete"])

    def test_more_records_than_declared_rejected(self):
        run = {"setup_table": TABLE, "crimps": [_job(), _job()], "declared_crimp_count": 1}
        with self.assertRaises(ValueError):
            summarize_run(run)

    def test_empty_run_rejected(self):
        with self.assertRaises(ValueError):
            summarize_run({"setup_table": TABLE, "crimps": []})


if __name__ == "__main__":
    unittest.main()
