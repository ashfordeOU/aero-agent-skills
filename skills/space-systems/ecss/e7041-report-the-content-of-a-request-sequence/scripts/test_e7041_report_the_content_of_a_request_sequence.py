"""Contract tests for the clause 6.21.8 request sequence content report logic."""

import unittest

from e7041_report_the_content_of_a_request_sequence_logic import (
    REPORTABLE_STATUSES,
    STATUS_AVAILABLE,
    STATUS_UNDER_CONSTRUCTION,
    assess_sequence_content_report,
    entry_cost_octets,
    normalise_entry,
    order_entries,
    oversized_entries,
    pack_entries,
)


def entry(name, offset, octets):
    return {"name": name, "offset_seconds": offset, "request_octets": octets}


class EntryValidationTests(unittest.TestCase):
    def test_valid_entry_is_normalised_with_its_load_order(self):
        result = normalise_entry(entry("a", 5, 40), 3)
        self.assertEqual(result["name"], "a")
        self.assertEqual(result["offset_seconds"], 5)
        self.assertEqual(result["load_order"], 3)

    def test_zero_offset_is_accepted(self):
        self.assertEqual(normalise_entry(entry("a", 0, 40), 0)["offset_seconds"], 0)

    def test_negative_offset_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_entry(entry("a", -1, 40), 0)

    def test_zero_length_request_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_entry(entry("a", 0, 0), 0)

    def test_boolean_offset_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_entry(entry("a", True, 40), 0)

    def test_blank_entry_name_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_entry(entry("   ", 0, 40), 0)

    def test_missing_key_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_entry({"name": "a", "offset_seconds": 0}, 0)

    def test_non_mapping_entry_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_entry(["a", 0, 40], 0)


class OrderingTests(unittest.TestCase):
    def test_entries_are_ordered_by_release_offset(self):
        ordered = order_entries([entry("b", 20, 10), entry("a", 5, 10)])
        self.assertEqual([e["name"] for e in ordered], ["a", "b"])

    def test_equal_offsets_keep_the_load_order(self):
        ordered = order_entries([entry("b", 5, 10), entry("a", 5, 10)])
        self.assertEqual([e["name"] for e in ordered], ["b", "a"])

    def test_duplicate_entry_name_is_refused(self):
        with self.assertRaises(ValueError):
            order_entries([entry("a", 5, 10), entry("a", 9, 10)])

    def test_empty_sequence_orders_to_nothing(self):
        self.assertEqual(order_entries([]), ())

    def test_non_sequence_input_is_refused(self):
        with self.assertRaises(ValueError):
            order_entries("ab")


class PackingTests(unittest.TestCase):
    def test_entry_cost_adds_the_per_entry_overhead(self):
        self.assertEqual(entry_cost_octets({"request_octets": 40}, 8), 48)

    def test_entries_that_fit_share_one_report(self):
        ordered = order_entries([entry("a", 1, 40), entry("b", 2, 40)])
        self.assertEqual(pack_entries(ordered, 200, 8), (("a", "b"),))

    def test_packing_opens_a_new_report_when_the_field_is_full(self):
        ordered = order_entries([entry("a", 1, 40), entry("b", 2, 40)])
        self.assertEqual(pack_entries(ordered, 60, 8), (("a",), ("b",)))

    def test_packing_preserves_the_release_order_across_reports(self):
        ordered = order_entries(
            [entry("c", 30, 40), entry("a", 10, 40), entry("b", 20, 40)]
        )
        self.assertEqual(pack_entries(ordered, 100, 8), (("a", "b"), ("c",)))

    def test_oversized_entry_is_named(self):
        ordered = order_entries([entry("a", 1, 40), entry("big", 2, 500)])
        self.assertEqual(oversized_entries(ordered, 100, 8), ("big",))

    def test_packing_refuses_an_entry_no_report_can_carry(self):
        ordered = order_entries([entry("big", 1, 500)])
        with self.assertRaises(ValueError):
            pack_entries(ordered, 100, 8)

    def test_zero_capacity_is_refused(self):
        with self.assertRaises(ValueError):
            pack_entries(order_entries([entry("a", 1, 10)]), 0, 0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "sequence_store": {
                7: {
                    "status": STATUS_AVAILABLE,
                    "entries": [
                        entry("open-valve", 0, 40),
                        entry("start-pump", 30, 40),
                        entry("close-valve", 90, 40),
                    ],
                }
            },
            "requested_identifier": 7,
            "report_data_octets": 200,
            "entry_overhead_octets": 8,
        }
        spec.update(overrides)
        return spec

    def test_available_sequence_is_reportable(self):
        result = assess_sequence_content_report(self._spec())
        self.assertTrue(result["reportable"])
        self.assertEqual(result["findings"], [])

    def test_report_lists_the_entries_in_release_order(self):
        result = assess_sequence_content_report(self._spec())
        self.assertEqual(
            result["ordered_entries"], ("open-valve", "start-pump", "close-valve")
        )

    def test_small_data_field_splits_the_content_over_reports(self):
        result = assess_sequence_content_report(self._spec(report_data_octets=100))
        self.assertEqual(result["report_count"], 2)

    def test_total_octets_counts_every_entry_with_its_overhead(self):
        result = assess_sequence_content_report(self._spec())
        self.assertEqual(result["total_octets"], 144)

    def test_unknown_identifier_is_refused_as_a_finding(self):
        result = assess_sequence_content_report(self._spec(requested_identifier=9))
        self.assertFalse(result["reportable"])
        self.assertEqual(result["status"], "unknown")
        self.assertTrue(any("not held" in f for f in result["findings"]))

    def test_sequence_still_being_built_is_flagged(self):
        store = {
            7: {
                "status": STATUS_UNDER_CONSTRUCTION,
                "entries": [entry("open-valve", 0, 40)],
            }
        }
        result = assess_sequence_content_report(self._spec(sequence_store=store))
        self.assertFalse(result["reportable"])
        self.assertTrue(any("not settled" in f for f in result["findings"]))

    def test_empty_sequence_is_flagged(self):
        store = {7: {"status": STATUS_AVAILABLE, "entries": []}}
        result = assess_sequence_content_report(self._spec(sequence_store=store))
        self.assertEqual(result["entry_count"], 0)
        self.assertTrue(any("no entries" in f for f in result["findings"]))

    def test_entry_larger_than_a_report_is_flagged_and_stops_packing(self):
        store = {
            7: {
                "status": STATUS_AVAILABLE,
                "entries": [entry("open-valve", 0, 40), entry("bulk-load", 5, 900)],
            }
        }
        result = assess_sequence_content_report(self._spec(sequence_store=store))
        self.assertEqual(result["reports"], ())
        self.assertTrue(any("bulk-load" in f for f in result["findings"]))

    def test_overhead_filling_the_data_field_is_refused(self):
        with self.assertRaises(ValueError):
            assess_sequence_content_report(
                self._spec(report_data_octets=8, entry_overhead_octets=8)
            )

    def test_missing_spec_key_is_refused(self):
        spec = self._spec()
        del spec["report_data_octets"]
        with self.assertRaises(ValueError):
            assess_sequence_content_report(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_sequence_content_report(["sequence_store"])

    def test_available_is_the_reportable_status(self):
        self.assertIn(STATUS_AVAILABLE, REPORTABLE_STATUSES)
        self.assertNotIn(STATUS_UNDER_CONSTRUCTION, REPORTABLE_STATUSES)


if __name__ == "__main__":
    unittest.main()
