"""Contract test for the materials-data-entry leaf (stdlib unittest)."""

import datetime
import unittest

from q7002_data_entry_to_materials_data_logic import (
    CONFLICT,
    CONFIRMED,
    DUPLICATE_ENTRY,
    ENTRY_DECIMALS,
    KEY_FIELDS,
    NEW_ENTRY,
    STALE,
    SUPERSEDES,
    data_set_key,
    normalize_value,
    parse_test_date,
    reconcile,
    record_entries,
    validate_entry,
    values_match,
)


def entry(**kw):
    record = {
        "material_designation": "EPX-114 two-part epoxy",
        "manufacturer": "Beispiel Polymere",
        "product_form": "potting compound",
        "processing_state": "cured 24 h at 60 C",
        "test_report_reference": "OG-2026-0041",
        "test_date": "2026-05-12",
        "total_mass_loss_pct": 0.62,
        "cvcm_pct": 0.04,
    }
    record.update(kw)
    return record


class TestDataSetKey(unittest.TestCase):
    def test_the_key_is_built_from_every_key_field(self):
        self.assertEqual(len(data_set_key(entry())), len(KEY_FIELDS))

    def test_the_key_ignores_case_and_spacing(self):
        a = data_set_key(entry())
        b = data_set_key(entry(manufacturer="  BEISPIEL   POLYMERE "))
        self.assertEqual(a, b)

    def test_a_different_cure_is_a_different_entry(self):
        a = data_set_key(entry())
        b = data_set_key(entry(processing_state="cured 2 h at 120 C"))
        self.assertNotEqual(a, b)

    def test_a_blank_key_field_raises(self):
        with self.assertRaises(ValueError):
            data_set_key(entry(product_form="   "))

    def test_a_non_mapping_entry_raises(self):
        with self.assertRaises(ValueError):
            data_set_key("EPX-114")


class TestNormalization(unittest.TestCase):
    def test_a_value_is_rounded_to_the_record_resolution(self):
        self.assertAlmostEqual(normalize_value(0.6237), 0.62, places=9)

    def test_the_record_resolution_is_two_decimals(self):
        self.assertEqual(ENTRY_DECIMALS, 2)

    def test_non_numeric_normalization_input_raises(self):
        with self.assertRaises(ValueError):
            normalize_value("0.62")

    def test_an_iso_date_parses(self):
        self.assertEqual(parse_test_date("2026-05-12"), datetime.date(2026, 5, 12))

    def test_a_date_object_passes_through(self):
        day = datetime.date(2026, 5, 12)
        self.assertEqual(parse_test_date(day), day)

    def test_a_malformed_date_raises(self):
        with self.assertRaises(ValueError):
            parse_test_date("12.05.2026")


class TestValidateEntry(unittest.TestCase):
    def test_a_valid_entry_is_normalized(self):
        norm = validate_entry(entry(total_mass_loss_pct=0.6237))
        self.assertAlmostEqual(norm["total_mass_loss_pct"], 0.62, places=9)
        self.assertEqual(norm["test_date"], datetime.date(2026, 5, 12))

    def test_a_missing_report_reference_raises(self):
        record = entry()
        del record["test_report_reference"]
        with self.assertRaises(ValueError):
            validate_entry(record)

    def test_a_negative_value_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(entry(cvcm_pct=-0.01))

    def test_condensing_more_than_was_lost_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(entry(total_mass_loss_pct=0.03, cvcm_pct=0.20))

    def test_a_recovered_loss_above_the_total_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(entry(recovered_mass_loss_pct=1.50))

    def test_an_absent_recovered_loss_is_carried_as_none(self):
        self.assertIsNone(validate_entry(entry())["recovered_mass_loss_pct"])

    def test_a_non_boolean_reportable_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(entry(report_reportable="yes"))


class TestValuesMatch(unittest.TestCase):
    def test_identical_entries_match(self):
        self.assertTrue(values_match(validate_entry(entry()), validate_entry(entry())))

    def test_entries_differing_past_the_record_resolution_still_match(self):
        left = validate_entry(entry(total_mass_loss_pct=0.6201))
        right = validate_entry(entry(total_mass_loss_pct=0.6198))
        self.assertTrue(values_match(left, right))

    def test_entries_differing_at_the_record_resolution_do_not(self):
        left = validate_entry(entry(total_mass_loss_pct=0.62))
        right = validate_entry(entry(total_mass_loss_pct=0.71))
        self.assertFalse(values_match(left, right))

    def test_a_present_and_an_absent_optional_value_do_not_match(self):
        left = validate_entry(entry(recovered_mass_loss_pct=0.30))
        right = validate_entry(entry())
        self.assertFalse(values_match(left, right))


class TestReconcile(unittest.TestCase):
    def test_nothing_recorded_gives_a_new_entry(self):
        self.assertEqual(reconcile(None, entry()), NEW_ENTRY)

    def test_the_same_report_twice_is_a_duplicate(self):
        self.assertEqual(reconcile(entry(), entry()), DUPLICATE_ENTRY)

    def test_the_same_values_from_another_report_confirm(self):
        other = entry(test_report_reference="OG-2026-0099", test_date="2026-09-01")
        self.assertEqual(reconcile(entry(), other), CONFIRMED)

    def test_new_values_from_a_later_report_supersede(self):
        later = entry(
            test_report_reference="OG-2026-0099",
            test_date="2026-09-01",
            cvcm_pct=0.09,
        )
        self.assertEqual(reconcile(entry(), later), SUPERSEDES)

    def test_new_values_from_an_earlier_report_are_stale(self):
        earlier = entry(
            test_report_reference="OG-2023-0007",
            test_date="2023-02-02",
            cvcm_pct=0.09,
        )
        self.assertEqual(reconcile(entry(), earlier), STALE)

    def test_new_values_on_the_same_date_conflict(self):
        same_day = entry(test_report_reference="OG-2026-0042", cvcm_pct=0.09)
        self.assertEqual(reconcile(entry(), same_day), CONFLICT)

    def test_reconciling_across_keys_raises(self):
        other = entry(processing_state="cured 2 h at 120 C")
        with self.assertRaises(ValueError):
            reconcile(entry(), other)


class TestRecordEntries(unittest.TestCase):
    def test_a_first_entry_lands_in_the_data_set(self):
        report = record_entries([entry()])
        self.assertTrue(report["clean"])
        self.assertEqual(len(report["recorded_keys"]), 1)
        self.assertEqual(report["actions"][0]["action"], NEW_ENTRY)

    def test_two_cure_states_are_two_entries(self):
        report = record_entries(
            [entry(), entry(processing_state="cured 2 h at 120 C")]
        )
        self.assertEqual(len(report["recorded_keys"]), 2)

    def test_a_later_report_replaces_the_recorded_values(self):
        first = record_entries([entry()])
        second = record_entries(
            [
                entry(
                    test_report_reference="OG-2026-0099",
                    test_date="2026-09-01",
                    cvcm_pct=0.09,
                )
            ],
            recorded=first["data_set"],
        )
        key = second["recorded_keys"][0]
        self.assertAlmostEqual(
            second["data_set"][key]["cvcm_pct"], 0.09, places=9
        )

    def test_an_earlier_report_does_not_replace_them(self):
        first = record_entries([entry()])
        second = record_entries(
            [
                entry(
                    test_report_reference="OG-2023-0007",
                    test_date="2023-02-02",
                    cvcm_pct=0.09,
                )
            ],
            recorded=first["data_set"],
        )
        key = second["recorded_keys"][0]
        self.assertAlmostEqual(
            second["data_set"][key]["cvcm_pct"], 0.04, places=9
        )
        self.assertIn(
            "earlier-report-offered-against-a-newer-entry", second["findings"]
        )

    def test_a_same_day_disagreement_is_a_finding(self):
        report = record_entries(
            [entry(), entry(test_report_reference="OG-2026-0042", cvcm_pct=0.09)]
        )
        self.assertFalse(report["clean"])
        self.assertIn(
            "same-key-entries-disagree-on-the-same-date", report["findings"]
        )

    def test_an_unreportable_source_is_never_recorded(self):
        report = record_entries([entry(report_reportable=False)])
        self.assertEqual(report["recorded_keys"], [])
        self.assertEqual(report["actions"][0]["action"], "not-recorded")
        self.assertIn(
            "entry-offered-from-a-report-that-is-not-reportable", report["findings"]
        )

    def test_an_empty_submission_raises(self):
        with self.assertRaises(ValueError):
            record_entries([])

    def test_a_non_list_submission_raises(self):
        with self.assertRaises(ValueError):
            record_entries(entry())

    def test_a_non_mapping_recorded_set_raises(self):
        with self.assertRaises(ValueError):
            record_entries([entry()], recorded=[entry()])


if __name__ == "__main__":
    unittest.main()
