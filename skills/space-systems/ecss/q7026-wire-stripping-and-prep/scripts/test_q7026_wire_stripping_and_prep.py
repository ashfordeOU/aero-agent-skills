#!/usr/bin/env python3
"""Contract test for stripped wire end preparation (offline)."""

import copy
import unittest

from q7026_wire_stripping_and_prep_logic import (
    DISPOSITION_ACCEPT,
    DISPOSITION_REJECT,
    DISPOSITION_REWORK,
    assess_lot,
    assess_wire_end,
    evaluate_conductor_condition,
    evaluate_process,
    evaluate_strand_damage,
    evaluate_strip_length,
    lookup_gauge,
    validate_gauge_table,
)

TABLE = {
    "22": {
        "strip_min_mm": 4.0,
        "strip_max_mm": 5.0,
        "strand_count": 19,
        "max_nicked_strands": 1,
        "max_severed_strands": 0,
    },
    "20": {
        "strip_min_mm": 4.5,
        "strip_max_mm": 5.5,
        "strand_count": 19,
        "max_nicked_strands": 1,
        "max_severed_strands": 1,
    },
}

GOOD_END = {
    "identifier": "W-001-A",
    "gauge": "22",
    "strip_length_mm": 4.5,
    "wire_margin_mm": 40.0,
    "min_rework_margin_mm": 12.0,
    "strands_in_bundle": 19,
    "nicked": 0,
    "severed": 0,
    "birdcaged": False,
    "insulation_damaged": False,
    "contaminated": False,
    "tinned": False,
    "method": "thermal",
    "qualified_methods": ["thermal", "mechanical-die"],
    "calibration_days_remaining": 30.0,
}


def _end(**overrides):
    end = copy.deepcopy(GOOD_END)
    end.update(overrides)
    return end


def _entry(gauge="22"):
    return lookup_gauge(validate_gauge_table(TABLE), gauge)


class GaugeTableTests(unittest.TestCase):
    def test_valid_table_normalises_every_gauge(self):
        table = validate_gauge_table(TABLE)
        self.assertEqual(sorted(table), ["20", "22"])
        self.assertAlmostEqual(table["22"]["strip_min_mm"], 4.0, places=9)

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_gauge_table({})

    def test_inverted_strip_band_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["22"]["strip_max_mm"] = 3.0
        with self.assertRaises(ValueError):
            validate_gauge_table(bad)

    def test_allowance_reaching_strand_count_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["22"]["max_nicked_strands"] = 19
        with self.assertRaises(ValueError):
            validate_gauge_table(bad)

    def test_untabulated_gauge_is_not_interpolated(self):
        table = validate_gauge_table(TABLE)
        with self.assertRaises(ValueError):
            lookup_gauge(table, "21")


class StripLengthTests(unittest.TestCase):
    def test_length_inside_band_accepts(self):
        result = evaluate_strip_length(4.5, _entry(), 40.0, 12.0)
        self.assertEqual(result["disposition"], DISPOSITION_ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_length_exactly_on_the_minimum_is_in_band(self):
        # 0.1 + 0.2 lands one unit in the last place above 0.3, and the same
        # representation error reaches a converted strip length.
        edge = 4.0 + (0.1 + 0.2 - 0.3)
        result = evaluate_strip_length(edge, _entry(), 40.0, 12.0)
        self.assertFalse(result["below_minimum"])
        self.assertEqual(result["disposition"], DISPOSITION_ACCEPT)

    def test_length_exactly_on_the_maximum_is_in_band(self):
        result = evaluate_strip_length(5.0, _entry(), 40.0, 12.0)
        self.assertFalse(result["above_maximum"])
        self.assertEqual(result["disposition"], DISPOSITION_ACCEPT)

    def test_short_strip_with_margin_is_rework(self):
        result = evaluate_strip_length(3.0, _entry(), 40.0, 12.0)
        self.assertEqual(result["disposition"], DISPOSITION_REWORK)
        self.assertTrue(result["below_minimum"])

    def test_long_strip_without_margin_is_reject(self):
        result = evaluate_strip_length(7.0, _entry(), 2.0, 12.0)
        self.assertEqual(result["disposition"], DISPOSITION_REJECT)
        self.assertTrue(any("margin" in f for f in result["findings"]))

    def test_band_position_is_reported(self):
        result = evaluate_strip_length(4.5, _entry(), 40.0, 12.0)
        self.assertAlmostEqual(result["band_position"], 0.5, places=9)

    def test_negative_length_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_strip_length(-1.0, _entry(), 40.0, 12.0)

    def test_non_numeric_length_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_strip_length("4.5 mm", _entry(), 40.0, 12.0)


class StrandDamageTests(unittest.TestCase):
    def test_undamaged_bundle_accepts(self):
        result = evaluate_strand_damage(_entry(), 19, nicked=0, severed=0)
        self.assertEqual(result["disposition"], DISPOSITION_ACCEPT)
        self.assertEqual(result["intact"], 19)

    def test_nicked_within_allowance_accepts(self):
        result = evaluate_strand_damage(_entry(), 19, nicked=1)
        self.assertEqual(result["disposition"], DISPOSITION_ACCEPT)

    def test_nicked_above_allowance_rejects(self):
        result = evaluate_strand_damage(_entry(), 19, nicked=2)
        self.assertEqual(result["disposition"], DISPOSITION_REJECT)
        self.assertTrue(any("nicked" in f for f in result["findings"]))

    def test_severed_strand_rejects_when_allowance_is_zero(self):
        result = evaluate_strand_damage(_entry(), 19, severed=1)
        self.assertEqual(result["disposition"], DISPOSITION_REJECT)

    def test_severed_within_allowance_accepts_on_the_wider_gauge(self):
        result = evaluate_strand_damage(_entry("20"), 19, severed=1)
        self.assertEqual(result["disposition"], DISPOSITION_ACCEPT)

    def test_intact_fraction_is_reported(self):
        result = evaluate_strand_damage(_entry("20"), 19, nicked=1, severed=1)
        self.assertAlmostEqual(result["intact_fraction"], 17.0 / 19.0, places=9)

    def test_bundle_count_disagreeing_with_the_gauge_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_strand_damage(_entry(), 18)

    def test_damage_exceeding_the_bundle_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_strand_damage(_entry("20"), 19, nicked=12, severed=12)

    def test_non_integer_nick_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_strand_damage(_entry(), 19, nicked=1.5)


class ConductorConditionTests(unittest.TestCase):
    def test_clean_conductor_accepts(self):
        result = evaluate_conductor_condition()
        self.assertEqual(result["disposition"], DISPOSITION_ACCEPT)

    def test_tinned_conductor_is_never_crimped(self):
        result = evaluate_conductor_condition(tinned=True)
        self.assertEqual(result["disposition"], DISPOSITION_REJECT)
        self.assertTrue(any("tinned" in f for f in result["findings"]))

    def test_birdcaged_conductor_is_rework(self):
        result = evaluate_conductor_condition(birdcaged=True)
        self.assertEqual(result["disposition"], DISPOSITION_REWORK)

    def test_contaminated_conductor_is_rework(self):
        result = evaluate_conductor_condition(contaminated=True)
        self.assertEqual(result["disposition"], DISPOSITION_REWORK)

    def test_insulation_damage_rejects(self):
        result = evaluate_conductor_condition(insulation_damaged=True)
        self.assertEqual(result["disposition"], DISPOSITION_REJECT)

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_conductor_condition(birdcaged="yes")


class ProcessTests(unittest.TestCase):
    def test_qualified_method_in_calibration_accepts(self):
        result = evaluate_process("thermal", ["thermal"], 10.0)
        self.assertEqual(result["disposition"], DISPOSITION_ACCEPT)
        self.assertTrue(result["calibration_current"])

    def test_unqualified_method_rejects(self):
        result = evaluate_process("abrasive", ["thermal"], 10.0)
        self.assertEqual(result["disposition"], DISPOSITION_REJECT)
        self.assertFalse(result["method_qualified"])

    def test_calibration_due_today_is_still_current(self):
        result = evaluate_process("thermal", ["thermal"], 0.1 + 0.2 - 0.3)
        self.assertTrue(result["calibration_current"])
        self.assertEqual(result["disposition"], DISPOSITION_ACCEPT)

    def test_lapsed_calibration_rejects(self):
        result = evaluate_process("thermal", ["thermal"], -1.0)
        self.assertEqual(result["disposition"], DISPOSITION_REJECT)

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_process("gnaw", ["thermal"], 10.0)

    def test_empty_qualified_set_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_process("thermal", [], 10.0)


class WireEndTests(unittest.TestCase):
    def test_good_end_accepts(self):
        result = assess_wire_end(_end(), TABLE)
        self.assertEqual(result["disposition"], DISPOSITION_ACCEPT)
        self.assertEqual(result["driving_checks"], [])

    def test_worst_check_drives_the_disposition(self):
        result = assess_wire_end(_end(tinned=True, birdcaged=True), TABLE)
        self.assertEqual(result["disposition"], DISPOSITION_REJECT)
        self.assertEqual(result["driving_checks"], ["conductor_condition"])

    def test_two_checks_at_the_worst_level_are_both_named(self):
        result = assess_wire_end(_end(nicked=5, insulation_damaged=True), TABLE)
        self.assertEqual(
            result["driving_checks"], ["conductor_condition", "strand_damage"]
        )

    def test_findings_are_prefixed_by_check(self):
        result = assess_wire_end(_end(nicked=5), TABLE)
        self.assertTrue(any(f.startswith("strand_damage:") for f in result["findings"]))

    def test_non_mapping_end_rejected(self):
        with self.assertRaises(ValueError):
            assess_wire_end("a stripped wire", TABLE)


class LotTests(unittest.TestCase):
    def test_complete_lot_rolls_up(self):
        lot = {"gauge_table": TABLE, "ends": [_end(), _end(identifier="W-002-A")]}
        result = assess_lot(lot)
        self.assertEqual(result["worst_disposition"], DISPOSITION_ACCEPT)
        self.assertEqual(result["accepted"], 2)
        self.assertTrue(result["record_complete"])

    def test_unrecorded_ends_flag_the_record(self):
        lot = {
            "gauge_table": TABLE,
            "ends": [_end()],
            "declared_end_count": 4,
        }
        result = assess_lot(lot)
        self.assertEqual(result["unrecorded_end_count"], 3)
        self.assertFalse(result["record_complete"])

    def test_not_accepted_ends_are_named(self):
        lot = {
            "gauge_table": TABLE,
            "ends": [_end(), _end(identifier="W-009-B", tinned=True)],
        }
        result = assess_lot(lot)
        self.assertEqual(result["not_accepted"], ["W-009-B"])
        self.assertEqual(result["rejected"], 1)

    def test_more_records_than_declared_rejected(self):
        lot = {
            "gauge_table": TABLE,
            "ends": [_end(), _end()],
            "declared_end_count": 1,
        }
        with self.assertRaises(ValueError):
            assess_lot(lot)

    def test_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot({"gauge_table": TABLE, "ends": []})


if __name__ == "__main__":
    unittest.main()
