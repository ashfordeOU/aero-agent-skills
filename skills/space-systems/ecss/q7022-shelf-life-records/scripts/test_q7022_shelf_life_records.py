"""Contract tests for the per-lot shelf-life record audit logic."""

import datetime
import unittest

from q7022_shelf_life_records_logic import (
    MANDATORY_RECORD_FIELDS,
    RETENTION_YEARS,
    audit_shelf_life_record,
    chronology_findings,
    completeness,
    deviation_findings,
    extension_backing_findings,
    normalise_events,
    parse_date,
    quantity_balance,
    retention_findings,
)

AUDIT_DAY = "2026-09-18"


def base_events():
    return [
        {"type": "receipt", "date": "2026-02-10", "quantity": 5.0},
        {"type": "storage-move", "date": "2026-02-11"},
        {"type": "inspection", "date": "2026-03-01"},
        {"type": "issue", "date": "2026-04-02", "quantity": 1.5},
        {"type": "return", "date": "2026-04-09", "quantity": 0.5},
    ]


def base_record(**overrides):
    """A complete, balanced record for a 5 kg adhesive lot."""
    record = {
        "lot_id": "SL-2026-0031",
        "material_designation": "structural epoxy paste",
        "manufacturer": "Adhesive supplier",
        "batch_identifier": "LOT-4471",
        "manufacture_date": "2026-01-01",
        "expiry_date": "2027-02-05",
        "receipt_date": "2026-02-10",
        "storage_location": "cold store B, shelf 3",
        "quantity_received": 5.0,
        "quantity_remaining": 4.0,
        "events": base_events(),
    }
    record.update(overrides)
    return record


class ParseDateTests(unittest.TestCase):
    def test_iso_string_parsed(self):
        self.assertEqual(parse_date("2026-02-10"), datetime.date(2026, 2, 10))

    def test_non_iso_text_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("10 Feb 2026")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date(None)


class EventNormalisationTests(unittest.TestCase):
    def test_events_are_ordered_by_date(self):
        events = normalise_events(
            [
                {"type": "issue", "date": "2026-04-02"},
                {"type": "receipt", "date": "2026-02-10"},
            ]
        )
        self.assertEqual(events[0]["type"], "receipt")

    def test_dates_are_parsed_to_date_objects(self):
        events = normalise_events([{"type": "receipt", "date": "2026-02-10"}])
        self.assertEqual(events[0]["date"], datetime.date(2026, 2, 10))

    def test_same_day_events_keep_their_input_order(self):
        events = normalise_events(
            [
                {"type": "receipt", "date": "2026-02-10"},
                {"type": "storage-move", "date": "2026-02-10"},
            ]
        )
        self.assertEqual([e["type"] for e in events], ["receipt", "storage-move"])

    def test_unknown_event_type_rejected(self):
        with self.assertRaises(ValueError):
            normalise_events([{"type": "borrowed", "date": "2026-02-10"}])

    def test_event_without_a_date_rejected(self):
        with self.assertRaises(ValueError):
            normalise_events([{"type": "receipt"}])

    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValueError):
            normalise_events([{"type": "issue", "date": "2026-04-02", "quantity": -1.0}])

    def test_non_sequence_event_log_rejected(self):
        with self.assertRaises(ValueError):
            normalise_events({"type": "receipt", "date": "2026-02-10"})


class CompletenessTests(unittest.TestCase):
    def test_full_header_is_one_hundred_percent(self):
        self.assertAlmostEqual(completeness(base_record())["percent"], 100.0, places=9)

    def test_missing_field_is_named(self):
        record = base_record()
        del record["storage_location"]
        self.assertEqual(completeness(record)["missing"], ["storage_location"])

    def test_blank_field_counts_as_missing(self):
        self.assertIn("batch_identifier", completeness(base_record(batch_identifier="  "))["missing"])

    def test_empty_record_scores_zero(self):
        result = completeness({})
        self.assertAlmostEqual(result["percent"], 0.0, places=9)
        self.assertEqual(len(result["missing"]), len(MANDATORY_RECORD_FIELDS))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            completeness(["lot_id"])


class ChronologyTests(unittest.TestCase):
    def test_clean_log_has_no_chronology_findings(self):
        record = base_record()
        self.assertEqual(chronology_findings(record, normalise_events(record["events"])), [])

    def test_event_before_manufacture_is_flagged(self):
        events = base_events() + [{"type": "inspection", "date": "2025-12-01"}]
        record = base_record(events=events)
        findings = chronology_findings(record, normalise_events(events))
        self.assertTrue(any("precedes the manufacture date" in f for f in findings))

    def test_missing_receipt_event_is_flagged(self):
        events = [e for e in base_events() if e["type"] != "receipt"]
        record = base_record(events=events)
        findings = chronology_findings(record, normalise_events(events))
        self.assertTrue(any("no receipt event" in f for f in findings))

    def test_issue_before_receipt_is_flagged(self):
        events = base_events() + [{"type": "issue", "date": "2026-01-15", "quantity": 0.1}]
        record = base_record(events=events)
        findings = chronology_findings(record, normalise_events(events))
        self.assertTrue(any("precedes the first receipt" in f for f in findings))

    def test_activity_after_disposal_is_flagged(self):
        events = base_events() + [
            {"type": "disposal", "date": "2026-05-01", "quantity": 3.0},
            {"type": "issue", "date": "2026-06-01", "quantity": 0.2},
        ]
        record = base_record(events=events)
        findings = chronology_findings(record, normalise_events(events))
        self.assertTrue(any("follows the disposal" in f for f in findings))


class DeviationTests(unittest.TestCase):
    def test_closed_deviation_with_full_entry_is_clean(self):
        events = base_events() + [
            {
                "type": "deviation",
                "date": "2026-03-15",
                "reference": "NCR-118",
                "disposition": "use as is",
                "closed": True,
            }
        ]
        result = deviation_findings(normalise_events(events))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["open"], 0)

    def test_deviation_without_a_reference_is_flagged(self):
        events = base_events() + [
            {"type": "deviation", "date": "2026-03-15", "disposition": "use as is", "closed": True}
        ]
        result = deviation_findings(normalise_events(events))
        self.assertTrue(any("no reference recorded" in f for f in result["findings"]))

    def test_deviation_with_an_empty_disposition_is_flagged(self):
        events = base_events() + [
            {
                "type": "deviation",
                "date": "2026-03-15",
                "reference": "NCR-118",
                "disposition": "   ",
                "closed": True,
            }
        ]
        result = deviation_findings(normalise_events(events))
        self.assertTrue(any("empty disposition" in f for f in result["findings"]))

    def test_open_deviation_is_counted(self):
        events = base_events() + [
            {
                "type": "deviation",
                "date": "2026-03-15",
                "reference": "NCR-118",
                "disposition": "under review",
                "closed": False,
            }
        ]
        self.assertEqual(deviation_findings(normalise_events(events))["open"], 1)

    def test_log_without_deviations_reports_none_open(self):
        self.assertEqual(deviation_findings(normalise_events(base_events()))["open"], 0)


class ExtensionBackingTests(unittest.TestCase):
    def test_extension_after_a_retest_is_clean(self):
        events = base_events() + [
            {"type": "re-test", "date": "2027-02-01"},
            {"type": "extension", "date": "2027-02-06"},
        ]
        self.assertEqual(extension_backing_findings(normalise_events(events)), [])

    def test_extension_with_no_retest_is_flagged(self):
        events = base_events() + [{"type": "extension", "date": "2027-02-06"}]
        findings = extension_backing_findings(normalise_events(events))
        self.assertTrue(any("no re-test event" in f for f in findings))

    def test_retest_after_the_extension_does_not_back_it(self):
        events = base_events() + [
            {"type": "extension", "date": "2027-02-06"},
            {"type": "re-test", "date": "2027-03-01"},
        ]
        findings = extension_backing_findings(normalise_events(events))
        self.assertEqual(len(findings), 1)


class QuantityBalanceTests(unittest.TestCase):
    def test_balanced_account_reports_no_findings(self):
        record = base_record()
        balance = quantity_balance(record, normalise_events(record["events"]))
        self.assertTrue(balance["balanced"])
        self.assertEqual(balance["findings"], [])

    def test_net_issued_is_issue_minus_return(self):
        record = base_record()
        balance = quantity_balance(record, normalise_events(record["events"]))
        self.assertAlmostEqual(balance["issued"] - balance["returned"], 1.0, places=9)

    def test_unexplained_residual_is_flagged(self):
        record = base_record(quantity_remaining=2.0)
        balance = quantity_balance(record, normalise_events(record["events"]))
        self.assertFalse(balance["balanced"])
        self.assertAlmostEqual(balance["residual"], 2.0, places=9)

    def test_scrapped_quantity_closes_the_account(self):
        events = base_events() + [{"type": "disposal", "date": "2026-05-01", "quantity": 2.0}]
        record = base_record(events=events, quantity_remaining=2.0)
        balance = quantity_balance(record, normalise_events(events))
        self.assertTrue(balance["balanced"])

    def test_missing_received_quantity_rejected(self):
        record = base_record()
        del record["quantity_received"]
        with self.assertRaises(ValueError):
            quantity_balance(record, normalise_events(record["events"]))

    def test_non_numeric_remaining_quantity_rejected(self):
        record = base_record(quantity_remaining="four")
        with self.assertRaises(ValueError):
            quantity_balance(record, normalise_events(record["events"]))


class RetentionTests(unittest.TestCase):
    def test_live_record_has_no_retention_finding(self):
        events = normalise_events(base_events())
        self.assertEqual(retention_findings(events, AUDIT_DAY, retired=False), [])

    def test_record_retired_too_early_is_flagged(self):
        events = normalise_events(
            base_events() + [{"type": "disposal", "date": "2026-05-01", "quantity": 3.5}]
        )
        findings = retention_findings(events, AUDIT_DAY, retired=True)
        self.assertTrue(any("short of the" in f for f in findings))

    def test_record_retired_after_the_period_is_clean(self):
        events = normalise_events(
            base_events() + [{"type": "disposal", "date": "2026-05-01", "quantity": 3.5}]
        )
        late = "20%d-05-01" % (26 + RETENTION_YEARS)
        self.assertEqual(retention_findings(events, late, retired=True), [])

    def test_retired_record_without_a_disposal_event_is_flagged(self):
        events = normalise_events(base_events())
        findings = retention_findings(events, AUDIT_DAY, retired=True)
        self.assertTrue(any("no disposal event" in f for f in findings))


class AuditTests(unittest.TestCase):
    def test_clean_record_is_compliant(self):
        result = audit_shelf_life_record(base_record(), AUDIT_DAY)
        self.assertEqual(result["verdict"], "compliant")
        self.assertEqual(result["findings"], [])

    def test_audit_reports_completeness_and_event_count(self):
        result = audit_shelf_life_record(base_record(), AUDIT_DAY)
        self.assertAlmostEqual(result["completeness_percent"], 100.0, places=9)
        self.assertEqual(result["event_count"], len(base_events()))

    def test_missing_header_field_makes_the_record_deficient(self):
        record = base_record()
        del record["manufacturer"]
        result = audit_shelf_life_record(record, AUDIT_DAY)
        self.assertEqual(result["verdict"], "deficient")
        self.assertIn("manufacturer", result["missing_fields"])

    def test_open_deviation_makes_the_record_deficient(self):
        events = base_events() + [
            {
                "type": "deviation",
                "date": "2026-03-15",
                "reference": "NCR-118",
                "disposition": "under review",
                "closed": False,
            }
        ]
        result = audit_shelf_life_record(base_record(events=events), AUDIT_DAY)
        self.assertEqual(result["open_deviations"], 1)
        self.assertEqual(result["verdict"], "deficient")

    def test_unbacked_extension_makes_the_record_deficient(self):
        events = base_events() + [{"type": "extension", "date": "2026-05-01"}]
        result = audit_shelf_life_record(base_record(events=events), AUDIT_DAY)
        self.assertTrue(any("no re-test event" in f for f in result["findings"]))

    def test_unbalanced_quantities_make_the_record_deficient(self):
        result = audit_shelf_life_record(base_record(quantity_remaining=1.0), AUDIT_DAY)
        self.assertEqual(result["verdict"], "deficient")

    def test_record_with_no_events_is_deficient(self):
        result = audit_shelf_life_record(base_record(events=[], quantity_remaining=5.0), AUDIT_DAY)
        self.assertEqual(result["event_count"], 0)
        self.assertEqual(result["verdict"], "deficient")

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            audit_shelf_life_record("SL-2026-0031", AUDIT_DAY)

    def test_bad_audit_date_rejected(self):
        with self.assertRaises(ValueError):
            audit_shelf_life_record(base_record(retired=True), "18 September 2026")


if __name__ == "__main__":
    unittest.main()
