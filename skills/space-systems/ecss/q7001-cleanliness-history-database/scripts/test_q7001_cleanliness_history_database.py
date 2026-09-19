#!/usr/bin/env python3
"""Contract test for the per-unit contamination history (offline, stdlib)."""

import copy
import datetime
import unittest

from q7001_cleanliness_history_database_logic import (
    ENTRY_KINDS,
    KIND_CLEANING,
    KIND_EXPOSURE,
    KIND_MEASUREMENT,
    MOLECULAR,
    PARTICULATE,
    STATE_INCOMPLETE,
    STATE_TRACEABLE,
    build_ledger,
    cleaning_closed_by_reading,
    exposure_since_cleaning,
    last_cleaning,
    latest_measurement,
    monitoring_gaps,
    normalise_entry,
    parse_date,
    record_contamination_history,
)

UNIT = "OPT-SN-0042"

ENTRIES = [
    {"unit_id": UNIT, "kind": KIND_MEASUREMENT, "date": "2026-01-05",
     "contaminant": MOLECULAR, "value": 1.4, "note": "incoming survey"},
    {"unit_id": UNIT, "kind": KIND_CLEANING, "date": "2026-01-10",
     "note": "solvent wipe"},
    {"unit_id": UNIT, "kind": KIND_MEASUREMENT, "date": "2026-01-11",
     "contaminant": MOLECULAR, "value": 0.4, "note": "post-clean verification"},
    {"unit_id": UNIT, "kind": KIND_MEASUREMENT, "date": "2026-01-11",
     "contaminant": PARTICULATE, "value": 0.03, "note": "post-clean tape lift"},
    {"unit_id": UNIT, "kind": KIND_EXPOSURE, "date": "2026-01-20",
     "contaminant": MOLECULAR, "value": 0.25, "note": "unbagged for fit check"},
    {"unit_id": UNIT, "kind": KIND_EXPOSURE, "date": "2026-02-02",
     "contaminant": PARTICULATE, "value": 0.01, "note": "transport"},
    {"unit_id": UNIT, "kind": KIND_MEASUREMENT, "date": "2026-02-04",
     "contaminant": MOLECULAR, "value": 0.7, "note": "pre-test survey"},
    {"unit_id": "OPT-SN-0043", "kind": KIND_EXPOSURE, "date": "2026-01-20",
     "contaminant": MOLECULAR, "value": 9.0, "note": "sister unit"},
]

CASE = {
    "unit_id": UNIT,
    "entries": ENTRIES,
    "max_interval_days": 30,
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


def _entries(extra=None, drop=None):
    rows = [copy.deepcopy(e) for e in ENTRIES]
    if drop is not None:
        rows = [e for e in rows if not drop(e)]
    if extra:
        rows.extend(copy.deepcopy(extra))
    return rows


class EntryValidationTests(unittest.TestCase):
    def test_iso_date_parses(self):
        self.assertEqual(parse_date("date", "2026-01-10"), datetime.date(2026, 1, 10))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("date", "10 January 2026")

    def test_every_declared_kind_is_accepted(self):
        for kind in ENTRY_KINDS:
            entry = {"unit_id": UNIT, "kind": kind, "date": "2026-01-10"}
            if kind != KIND_CLEANING:
                entry.update({"contaminant": MOLECULAR, "value": 0.1})
            self.assertEqual(normalise_entry(entry)["kind"], kind)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalise_entry({"unit_id": UNIT, "kind": "inspection", "date": "2026-01-10"})

    def test_quantified_entry_without_a_contaminant_rejected(self):
        with self.assertRaises(ValueError):
            normalise_entry(
                {"unit_id": UNIT, "kind": KIND_MEASUREMENT, "date": "2026-01-10",
                 "value": 0.4}
            )

    def test_negative_measurement_rejected(self):
        with self.assertRaises(ValueError):
            normalise_entry(
                {"unit_id": UNIT, "kind": KIND_MEASUREMENT, "date": "2026-01-10",
                 "contaminant": MOLECULAR, "value": -0.4}
            )

    def test_entry_without_a_unit_rejected(self):
        with self.assertRaises(ValueError):
            normalise_entry({"kind": KIND_CLEANING, "date": "2026-01-10"})

    def test_cleaning_carries_no_contaminant_value(self):
        row = normalise_entry({"unit_id": UNIT, "kind": KIND_CLEANING, "date": "2026-01-10"})
        self.assertIsNone(row["value"])


class LedgerTests(unittest.TestCase):
    def test_ledger_keys_on_the_serial_number(self):
        ledger = build_ledger(ENTRIES, UNIT)
        self.assertTrue(all(row["unit_id"] == UNIT for row in ledger))
        self.assertEqual(len(ledger), 7)

    def test_a_sister_unit_does_not_contaminate_the_ledger(self):
        ledger = build_ledger(ENTRIES, "OPT-SN-0043")
        self.assertEqual(len(ledger), 1)
        self.assertAlmostEqual(ledger[0]["value"], 9.0, places=9)

    def test_ledger_is_ordered_by_date(self):
        dates = [row["date"] for row in build_ledger(ENTRIES, UNIT)]
        self.assertEqual(dates, sorted(dates))

    def test_two_entries_on_one_day_keep_their_supplied_order(self):
        ledger = build_ledger(ENTRIES, UNIT)
        same_day = [r for r in ledger if r["date"] == datetime.date(2026, 1, 11)]
        self.assertEqual(
            [r["contaminant"] for r in same_day], [MOLECULAR, PARTICULATE]
        )

    def test_shuffled_input_produces_the_same_ledger(self):
        shuffled = list(reversed(_entries()))
        self.assertEqual(
            [r["date"] for r in build_ledger(shuffled, UNIT)],
            [r["date"] for r in build_ledger(ENTRIES, UNIT)],
        )

    def test_duplicate_entry_refused_at_entry(self):
        rows = _entries(extra=[ENTRIES[2]])
        with self.assertRaises(ValueError):
            build_ledger(rows, UNIT)

    def test_entries_must_be_a_list(self):
        with self.assertRaises(ValueError):
            build_ledger("2026-01-10", UNIT)

    def test_empty_unit_id_rejected(self):
        with self.assertRaises(ValueError):
            build_ledger(ENTRIES, "  ")


class AccumulationTests(unittest.TestCase):
    def test_accumulation_starts_at_the_last_cleaning(self):
        result = exposure_since_cleaning(build_ledger(ENTRIES, UNIT))
        self.assertEqual(result["since"], "2026-01-10")

    def test_pre_cleaning_exposure_is_not_carried_forward(self):
        rows = _entries(
            extra=[{"unit_id": UNIT, "kind": KIND_EXPOSURE, "date": "2026-01-02",
                    "contaminant": MOLECULAR, "value": 5.0, "note": "before cleaning"}]
        )
        result = exposure_since_cleaning(build_ledger(rows, UNIT))
        self.assertAlmostEqual(result["molecular"], 0.25, places=9)

    def test_the_two_ledgers_accumulate_separately(self):
        result = exposure_since_cleaning(build_ledger(ENTRIES, UNIT))
        self.assertAlmostEqual(result["molecular"], 0.25, places=9)
        self.assertAlmostEqual(result["particulate"], 0.01, places=9)

    def test_a_second_cleaning_resets_the_accumulation(self):
        rows = _entries(
            extra=[
                {"unit_id": UNIT, "kind": KIND_CLEANING, "date": "2026-02-10",
                 "note": "re-clean"},
                {"unit_id": UNIT, "kind": KIND_MEASUREMENT, "date": "2026-02-11",
                 "contaminant": MOLECULAR, "value": 0.3, "note": "verification"},
            ]
        )
        result = exposure_since_cleaning(build_ledger(rows, UNIT))
        self.assertEqual(result["since"], "2026-02-10")
        self.assertAlmostEqual(result["molecular"], 0.0, places=9)

    def test_a_unit_never_cleaned_accumulates_everything(self):
        rows = _entries(drop=lambda e: e["kind"] == KIND_CLEANING)
        result = exposure_since_cleaning(build_ledger(rows, UNIT))
        self.assertIsNone(result["since"])
        self.assertAlmostEqual(result["molecular"], 0.25, places=9)

    def test_latest_reading_is_what_the_unit_is_known_at(self):
        ledger = build_ledger(ENTRIES, UNIT)
        self.assertAlmostEqual(
            latest_measurement(ledger, MOLECULAR)["value"], 0.7, places=9
        )

    def test_unknown_contaminant_ledger_rejected(self):
        with self.assertRaises(ValueError):
            latest_measurement(build_ledger(ENTRIES, UNIT), "biological")

    def test_last_cleaning_is_the_most_recent_one(self):
        rows = _entries(
            extra=[{"unit_id": UNIT, "kind": KIND_CLEANING, "date": "2026-02-10",
                    "note": "re-clean"}]
        )
        self.assertEqual(
            last_cleaning(build_ledger(rows, UNIT))["date"], datetime.date(2026, 2, 10)
        )


class GapTests(unittest.TestCase):
    def test_a_monitored_record_has_no_gaps(self):
        self.assertEqual(monitoring_gaps(build_ledger(ENTRIES, UNIT), 30), ())

    def test_an_unmonitored_interval_is_reported(self):
        rows = _entries(
            extra=[{"unit_id": UNIT, "kind": KIND_MEASUREMENT, "date": "2026-06-01",
                    "contaminant": MOLECULAR, "value": 1.1, "note": "after storage"}]
        )
        gaps = monitoring_gaps(build_ledger(rows, UNIT), 30)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["days"], 117)
        self.assertEqual(gaps[0]["over_by_days"], 87)

    def test_an_interval_exactly_on_the_maximum_is_not_a_gap(self):
        rows = _entries(
            extra=[{"unit_id": UNIT, "kind": KIND_MEASUREMENT, "date": "2026-03-06",
                    "contaminant": MOLECULAR, "value": 0.8, "note": "monthly"}]
        )
        self.assertEqual(monitoring_gaps(build_ledger(rows, UNIT), 30), ())

    def test_silence_since_the_last_reading_counts_as_a_gap(self):
        gaps = monitoring_gaps(build_ledger(ENTRIES, UNIT), 30, as_of="2026-05-01")
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["to"], "2026-05-01")

    def test_zero_maximum_interval_rejected(self):
        with self.assertRaises(ValueError):
            monitoring_gaps(build_ledger(ENTRIES, UNIT), 0)

    def test_boolean_maximum_interval_rejected(self):
        with self.assertRaises(ValueError):
            monitoring_gaps(build_ledger(ENTRIES, UNIT), True)


class HistoryStateTests(unittest.TestCase):
    def test_a_complete_history_is_traceable(self):
        result = record_contamination_history(CASE)
        self.assertEqual(result["state"], STATE_TRACEABLE)
        self.assertTrue(result["traceable"])
        self.assertEqual(result["missing"], ())

    def test_entry_count_excludes_other_units(self):
        self.assertEqual(record_contamination_history(CASE)["entry_count"], 7)

    def test_a_cleaning_with_no_reading_after_it_is_incomplete(self):
        rows = _entries(
            extra=[{"unit_id": UNIT, "kind": KIND_CLEANING, "date": "2026-03-01",
                    "note": "re-clean, unverified"}]
        )
        result = record_contamination_history(_case(entries=rows))
        self.assertEqual(result["state"], STATE_INCOMPLETE)
        self.assertTrue(any("never closed" in m for m in result["missing"]))

    def test_a_unit_never_cleaned_is_incomplete(self):
        rows = _entries(drop=lambda e: e["kind"] == KIND_CLEANING)
        result = record_contamination_history(_case(entries=rows))
        self.assertTrue(any("no cleaning" in m for m in result["missing"]))

    def test_a_missing_ledger_is_named(self):
        rows = _entries(
            drop=lambda e: e.get("contaminant") == PARTICULATE
            and e["kind"] == KIND_MEASUREMENT
        )
        result = record_contamination_history(_case(entries=rows))
        self.assertTrue(any("particulate measurement" in m for m in result["missing"]))

    def test_an_empty_history_is_incomplete_rather_than_clean(self):
        result = record_contamination_history(_case(entries=[]))
        self.assertFalse(result["traceable"])
        self.assertIsNone(result["first_entry"])

    def test_the_gap_is_carried_into_the_state(self):
        result = record_contamination_history(_case(as_of="2026-05-01"))
        self.assertEqual(result["state"], STATE_INCOMPLETE)
        self.assertTrue(any("monitoring gap" in m for m in result["missing"]))

    def test_closing_reading_detected_on_the_cleaning_day_itself(self):
        rows = [
            {"unit_id": UNIT, "kind": KIND_CLEANING, "date": "2026-01-10"},
            {"unit_id": UNIT, "kind": KIND_MEASUREMENT, "date": "2026-01-10",
             "contaminant": MOLECULAR, "value": 0.2},
        ]
        self.assertTrue(cleaning_closed_by_reading(build_ledger(rows, UNIT)))

    def test_a_reading_before_the_cleaning_does_not_close_it(self):
        rows = [
            {"unit_id": UNIT, "kind": KIND_MEASUREMENT, "date": "2026-01-09",
             "contaminant": MOLECULAR, "value": 0.2},
            {"unit_id": UNIT, "kind": KIND_CLEANING, "date": "2026-01-10"},
        ]
        self.assertFalse(cleaning_closed_by_reading(build_ledger(rows, UNIT)))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            record_contamination_history(UNIT)

    def test_missing_unit_id_rejected(self):
        case = _case()
        del case["unit_id"]
        with self.assertRaises(ValueError):
            record_contamination_history(case)


if __name__ == "__main__":
    unittest.main()
