"""
Gate-3 contract tests for e1024_ticd_logic.py.
stdlib unittest only — deterministic, offline.
Run: python3 test_e1024_ticd.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1024_ticd_logic import (
    validate_signal_record,
    check_pin_conflicts,
    check_signal_name_duplicates,
    check_ground_reference,
    check_category_coverage,
    check_direction_conflicts,
    assess_ticd,
    VALID_SIGNAL_TYPES,
    VALID_DIRECTIONS,
)


def _make_signal(name="SIG_A", sig_type="electrical", direction="source",
                 connector="J1", pin="1"):
    return {
        "signal_name": name,
        "signal_type": sig_type,
        "direction": direction,
        "connector": connector,
        "pin": pin,
    }


def _minimal_ticd(extra_signals=None, required_categories=None):
    signals = [
        _make_signal("PWR_28V", "power", "source", "J1", "1"),
        _make_signal("GND_REF", "ground", "sink", "J1", "2"),
        _make_signal("CMD_TX", "data", "source", "J2", "1"),
        _make_signal("TLM_RX", "data", "sink", "J2", "2"),
    ]
    if extra_signals:
        signals.extend(extra_signals)
    return {
        "ticd_id": "TICD-001",
        "test_item": "UUT-FM-01",
        "signals": signals,
        "required_categories": required_categories or [],
    }


class TestValidateSignalRecord(unittest.TestCase):

    def test_valid_record_passes(self):
        ok, msg = validate_signal_record(_make_signal())
        self.assertTrue(ok)
        self.assertEqual(msg, "ok")

    def test_missing_signal_type_rejected(self):
        rec = _make_signal()
        del rec["signal_type"]
        ok, msg = validate_signal_record(rec)
        self.assertFalse(ok)
        self.assertIn("missing fields", msg)
        self.assertIn("signal_type", msg)

    def test_missing_multiple_fields_rejected(self):
        rec = {"signal_name": "X"}
        ok, msg = validate_signal_record(rec)
        self.assertFalse(ok)
        self.assertIn("missing fields", msg)

    def test_blank_signal_name_rejected(self):
        ok, msg = validate_signal_record(_make_signal(name="   "))
        self.assertFalse(ok)
        self.assertIn("signal_name", msg)

    def test_unrecognized_signal_type_rejected(self):
        ok, msg = validate_signal_record(_make_signal(sig_type="quantum"))
        self.assertFalse(ok)
        self.assertIn("unrecognized signal_type", msg)

    def test_unrecognized_direction_rejected(self):
        ok, msg = validate_signal_record(_make_signal(direction="upstream"))
        self.assertFalse(ok)
        self.assertIn("unrecognized direction", msg)

    def test_all_valid_signal_types_accepted(self):
        for st in VALID_SIGNAL_TYPES:
            ok, _ = validate_signal_record(_make_signal(sig_type=st))
            self.assertTrue(ok, "Expected valid for signal_type={}".format(st))

    def test_all_valid_directions_accepted(self):
        for d in VALID_DIRECTIONS:
            ok, _ = validate_signal_record(_make_signal(direction=d))
            self.assertTrue(ok, "Expected valid for direction={}".format(d))


class TestPinConflicts(unittest.TestCase):

    def test_no_conflict_when_pins_unique(self):
        signals = [
            _make_signal("A", connector="J1", pin="1"),
            _make_signal("B", connector="J1", pin="2"),
            _make_signal("C", connector="J2", pin="1"),
        ]
        self.assertEqual(check_pin_conflicts(signals), [])

    def test_conflict_detected_on_same_connector_pin(self):
        signals = [
            _make_signal("A", connector="J1", pin="1"),
            _make_signal("B", connector="J1", pin="1"),
        ]
        conflicts = check_pin_conflicts(signals)
        self.assertEqual(len(conflicts), 1)
        self.assertIn(("J1", "1"), conflicts)

    def test_same_pin_different_connector_is_not_conflict(self):
        signals = [
            _make_signal("A", connector="J1", pin="1"),
            _make_signal("B", connector="J2", pin="1"),
        ]
        self.assertEqual(check_pin_conflicts(signals), [])

    def test_conflict_reported_once_for_triple_assignment(self):
        signals = [
            _make_signal("A", connector="J1", pin="5"),
            _make_signal("B", connector="J1", pin="5"),
            _make_signal("C", connector="J1", pin="5"),
        ]
        conflicts = check_pin_conflicts(signals)
        self.assertEqual(conflicts.count(("J1", "5")), 1)


class TestSignalNameDuplicates(unittest.TestCase):

    def test_no_duplicate_when_names_unique(self):
        signals = [_make_signal("A"), _make_signal("B"), _make_signal("C")]
        self.assertEqual(check_signal_name_duplicates(signals), [])

    def test_duplicate_detected(self):
        signals = [_make_signal("A"), _make_signal("A"), _make_signal("B")]
        dupes = check_signal_name_duplicates(signals)
        self.assertIn("A", dupes)
        self.assertNotIn("B", dupes)

    def test_duplicate_reported_once(self):
        signals = [_make_signal("X"), _make_signal("X"), _make_signal("X")]
        dupes = check_signal_name_duplicates(signals)
        self.assertEqual(dupes.count("X"), 1)


class TestGroundReference(unittest.TestCase):

    def test_ground_signal_present(self):
        signals = [
            _make_signal("PWR", "power", "source"),
            _make_signal("GND", "ground", "sink"),
        ]
        self.assertTrue(check_ground_reference(signals))

    def test_no_ground_signal_absent(self):
        signals = [
            _make_signal("PWR", "power", "source"),
            _make_signal("DATA", "data", "bidirectional"),
        ]
        self.assertFalse(check_ground_reference(signals))

    def test_empty_signal_list_no_ground(self):
        self.assertFalse(check_ground_reference([]))


class TestCategoryCoverage(unittest.TestCase):

    def test_all_required_categories_present(self):
        signals = [
            _make_signal("A", "power"),
            _make_signal("B", "data"),
            _make_signal("C", "ground"),
        ]
        missing = check_category_coverage(signals, ["power", "data"])
        self.assertEqual(missing, [])

    def test_missing_required_category_flagged(self):
        signals = [_make_signal("A", "data")]
        missing = check_category_coverage(signals, ["power", "data"])
        self.assertIn("power", missing)
        self.assertNotIn("data", missing)

    def test_empty_required_list_always_passes(self):
        signals = [_make_signal("A", "electrical")]
        self.assertEqual(check_category_coverage(signals, []), [])


class TestDirectionConflicts(unittest.TestCase):

    def test_no_conflict_when_directions_consistent(self):
        signals = [
            _make_signal("CMD", direction="source"),
            _make_signal("TLM", direction="sink"),
        ]
        self.assertEqual(check_direction_conflicts(signals), [])

    def test_conflict_detected_same_name_source_and_sink(self):
        signals = [
            _make_signal("BUS_A", direction="source"),
            _make_signal("BUS_A", direction="sink"),
        ]
        conflicts = check_direction_conflicts(signals)
        self.assertIn("BUS_A", conflicts)

    def test_bidirectional_alone_is_not_a_conflict(self):
        signals = [_make_signal("BUS_B", direction="bidirectional")]
        self.assertEqual(check_direction_conflicts(signals), [])

    def test_source_and_bidirectional_not_flagged(self):
        signals = [
            _make_signal("BUS_C", direction="source"),
            _make_signal("BUS_C", direction="bidirectional"),
        ]
        self.assertEqual(check_direction_conflicts(signals), [])


class TestAssessTicd(unittest.TestCase):

    def test_valid_ticd_passes(self):
        result = assess_ticd(_minimal_ticd())
        self.assertTrue(result["valid"])
        self.assertEqual(result["findings"], [])

    def test_blank_ticd_id_is_finding(self):
        rec = _minimal_ticd()
        rec["ticd_id"] = "  "
        result = assess_ticd(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("ticd_id" in f for f in result["findings"]))

    def test_blank_test_item_is_finding(self):
        rec = _minimal_ticd()
        rec["test_item"] = ""
        result = assess_ticd(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("test_item" in f for f in result["findings"]))

    def test_no_signals_is_finding(self):
        rec = _minimal_ticd()
        rec["signals"] = []
        result = assess_ticd(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("no signals" in f for f in result["findings"]))

    def test_invalid_signal_record_is_finding(self):
        rec = _minimal_ticd(extra_signals=[{"signal_name": "BAD"}])
        result = assess_ticd(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("signal[" in f for f in result["findings"]))

    def test_pin_conflict_is_finding(self):
        extra = [_make_signal("CLASH", "electrical", "source", "J1", "1")]
        rec = _minimal_ticd(extra_signals=extra)
        result = assess_ticd(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("pin conflict" in f for f in result["findings"]))

    def test_duplicate_signal_name_is_finding(self):
        extra = [_make_signal("TLM_RX", "data", "sink", "J3", "1")]
        rec = _minimal_ticd(extra_signals=extra)
        result = assess_ticd(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("duplicate signal name" in f for f in result["findings"]))

    def test_no_ground_reference_is_finding(self):
        rec = {
            "ticd_id": "TICD-002",
            "test_item": "UUT-EM-01",
            "signals": [
                _make_signal("PWR", "power", "source", "J1", "1"),
                _make_signal("DATA", "data", "sink", "J1", "2"),
            ],
            "required_categories": [],
        }
        result = assess_ticd(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("ground" in f for f in result["findings"]))

    def test_missing_required_category_is_finding(self):
        rec = _minimal_ticd(required_categories=["rf"])
        result = assess_ticd(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("rf" in f for f in result["findings"]))

    def test_direction_conflict_is_finding(self):
        extra = [_make_signal("CMD_TX", "data", "sink", "J3", "1")]
        rec = _minimal_ticd(extra_signals=extra)
        result = assess_ticd(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("direction conflict" in f for f in result["findings"]))

    def test_multiple_findings_accumulate(self):
        rec = {
            "ticd_id": "",
            "test_item": "",
            "signals": [],
        }
        result = assess_ticd(rec)
        self.assertFalse(result["valid"])
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_valid_ticd_with_required_category_covered(self):
        extra = [_make_signal("HGA_RF", "rf", "bidirectional", "J3", "1")]
        rec = _minimal_ticd(extra_signals=extra, required_categories=["power", "rf"])
        result = assess_ticd(rec)
        self.assertTrue(result["valid"])
        self.assertEqual(result["findings"], [])


if __name__ == "__main__":
    unittest.main()
