"""Contract tests for the clause 6.22.9.2 schedule detail report logic."""

import unittest

from e7041_position_based_schedule_detail_report_logic import (
    DETAIL_ENTRY_FIELDS,
    REVOLUTION_DEG,
    assess_detail_report,
    detail_entry_octets,
    minimum_packet_count,
    order_detail_entries,
    pack_detail_report,
    packet_payload_octets,
    position_window_contains,
    select_detail_entries,
    validate_detail_activity,
    validate_position_deg,
)


def activity(source_id=1, apid=10, sequence_count=1, position=30.0, group=1,
             request_octets=100):
    return {
        "source_id": source_id,
        "apid": apid,
        "sequence_count": sequence_count,
        "position_deg": position,
        "group": group,
        "request_octets": request_octets,
    }


class ActivityValidationTests(unittest.TestCase):
    def test_entry_carries_the_detail_fields(self):
        entry = validate_detail_activity(activity())
        self.assertEqual(tuple(sorted(entry)), tuple(sorted(DETAIL_ENTRY_FIELDS)))

    def test_request_size_is_kept_on_the_entry(self):
        self.assertEqual(validate_detail_activity(activity(request_octets=250))["request_octets"], 250)

    def test_zero_length_request_is_refused(self):
        with self.assertRaises(ValueError):
            validate_detail_activity(activity(request_octets=0))

    def test_missing_request_size_is_refused(self):
        broken = activity()
        del broken["request_octets"]
        with self.assertRaises(ValueError):
            validate_detail_activity(broken)

    def test_application_process_past_its_field_is_refused(self):
        with self.assertRaises(ValueError):
            validate_detail_activity(activity(apid=2048))

    def test_position_at_a_full_revolution_is_refused(self):
        with self.assertRaises(ValueError):
            validate_position_deg(REVOLUTION_DEG)

    def test_zero_group_is_refused(self):
        with self.assertRaises(ValueError):
            validate_detail_activity(activity(group=0))


class EntrySizingTests(unittest.TestCase):
    def test_entry_size_is_overhead_plus_request(self):
        self.assertEqual(detail_entry_octets(validate_detail_activity(activity()), 6), 106)

    def test_zero_overhead_leaves_the_request_alone(self):
        self.assertEqual(detail_entry_octets(validate_detail_activity(activity()), 0), 100)

    def test_negative_overhead_is_refused(self):
        with self.assertRaises(ValueError):
            detail_entry_octets(validate_detail_activity(activity()), -2)

    def test_entry_without_a_request_size_is_refused(self):
        with self.assertRaises(ValueError):
            detail_entry_octets({"apid": 1}, 6)


class PayloadTests(unittest.TestCase):
    def test_header_is_taken_off_the_packet_limit(self):
        self.assertEqual(packet_payload_octets(1024, 24), 1000)

    def test_header_filling_the_packet_is_refused(self):
        with self.assertRaises(ValueError):
            packet_payload_octets(24, 24)

    def test_lower_bound_is_a_ceiling_division(self):
        self.assertEqual(minimum_packet_count(2001, 1000), 3)

    def test_an_exact_multiple_needs_no_extra_packet(self):
        self.assertEqual(minimum_packet_count(2000, 1000), 2)

    def test_no_payload_needs_no_packet(self):
        self.assertEqual(minimum_packet_count(0, 1000), 0)


class WindowTests(unittest.TestCase):
    def test_plain_window_keeps_the_interior(self):
        self.assertTrue(position_window_contains(10.0, 50.0, 30.0))

    def test_plain_window_includes_both_bounds(self):
        self.assertTrue(position_window_contains(10.0, 50.0, 10.0))
        self.assertTrue(position_window_contains(10.0, 50.0, 50.0))

    def test_wrapping_window_keeps_both_arcs(self):
        self.assertTrue(position_window_contains(350.0, 10.0, 358.0))
        self.assertTrue(position_window_contains(350.0, 10.0, 2.0))

    def test_wrapping_window_drops_the_far_side(self):
        self.assertFalse(position_window_contains(350.0, 10.0, 200.0))


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.schedule = [
            activity(sequence_count=1, position=300.0, group=1),
            activity(sequence_count=2, position=20.0, group=2),
            activity(sequence_count=3, position=120.0, group=1),
        ]

    def test_identification_selection_picks_one_request(self):
        kept = select_detail_entries(self.schedule, identifications=[(1, 10, 2)])
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["sequence_count"], 2)

    def test_group_selection_picks_a_group(self):
        self.assertEqual(len(select_detail_entries(self.schedule, groups=[1])), 2)

    def test_window_selection_picks_an_arc(self):
        kept = select_detail_entries(self.schedule, window=(100.0, 200.0))
        self.assertEqual(len(kept), 1)

    def test_selections_combine_as_an_intersection(self):
        kept = select_detail_entries(self.schedule, groups=[1], window=(100.0, 200.0))
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["sequence_count"], 3)

    def test_malformed_identification_is_refused(self):
        with self.assertRaises(ValueError):
            select_detail_entries(self.schedule, identifications=[(1, 10)])

    def test_empty_identification_set_is_refused(self):
        with self.assertRaises(ValueError):
            select_detail_entries(self.schedule, identifications=[])

    def test_entries_come_out_by_increasing_position(self):
        ordered = order_detail_entries(select_detail_entries(self.schedule))
        self.assertEqual([e["sequence_count"] for e in ordered], [2, 3, 1])


class PackingTests(unittest.TestCase):
    def _entries(self, sizes):
        return [
            validate_detail_activity(
                activity(sequence_count=i + 1, position=float(i * 10), request_octets=s)
            )
            for i, s in enumerate(sizes)
        ]

    def test_entries_that_fit_share_one_packet(self):
        packets = pack_detail_report(self._entries([100, 100, 100]), 512, 12, 4)
        self.assertEqual(len(packets), 1)
        self.assertEqual(len(packets[0]), 3)

    def test_a_packet_is_closed_when_the_next_entry_no_longer_fits(self):
        packets = pack_detail_report(self._entries([200, 200, 200]), 512, 12, 0)
        self.assertEqual(len(packets), 2)
        self.assertEqual(len(packets[0]), 2)
        self.assertEqual(len(packets[1]), 1)

    def test_packing_preserves_the_entry_order(self):
        packets = pack_detail_report(self._entries([200, 200, 200]), 512, 12, 0)
        flat = [e["sequence_count"] for p in packets for e in p]
        self.assertEqual(flat, [1, 2, 3])

    def test_an_entry_that_fits_no_packet_is_refused(self):
        with self.assertRaises(ValueError):
            pack_detail_report(self._entries([5000]), 512, 12, 4)

    def test_an_entry_exactly_filling_the_payload_is_accepted(self):
        packets = pack_detail_report(self._entries([500]), 512, 12, 0)
        self.assertEqual(len(packets), 1)

    def test_an_empty_selection_produces_no_packet(self):
        self.assertEqual(pack_detail_report([], 512, 12, 4), ())

    def test_a_header_larger_than_the_packet_is_refused(self):
        with self.assertRaises(ValueError):
            pack_detail_report(self._entries([10]), 16, 32, 0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "activities": [
                activity(sequence_count=1, position=300.0, group=1, request_octets=200),
                activity(sequence_count=2, position=20.0, group=2, request_octets=200),
                activity(sequence_count=3, position=120.0, group=1, request_octets=200),
            ],
            "max_packet_octets": 512,
            "report_header_octets": 12,
            "entry_overhead_octets": 0,
        }
        spec.update(over)
        return spec

    def test_report_carries_the_request_content(self):
        result = assess_detail_report(self._spec())
        self.assertTrue(result["carries_request_content"])
        self.assertIn("request_octets", result["entry_fields"])

    def test_entries_are_ordered_by_position_before_packing(self):
        result = assess_detail_report(self._spec())
        flat = [e["sequence_count"] for p in result["packets"] for e in p]
        self.assertEqual(flat, [2, 3, 1])

    def test_packet_count_and_payload_are_reported(self):
        result = assess_detail_report(self._spec())
        self.assertEqual(result["packet_payload_octets"], 500)
        self.assertEqual(result["packet_count"], 2)
        self.assertEqual(result["total_entry_octets"], 600)

    def test_no_split_cost_is_reported_against_the_lower_bound(self):
        result = assess_detail_report(self._spec())
        self.assertEqual(result["minimum_packet_count"], 2)
        self.assertEqual(result["packet_count"], 2)

    def test_fill_ratios_are_reported_per_packet(self):
        result = assess_detail_report(self._spec())
        self.assertAlmostEqual(result["packet_fill_ratios"][0], 0.8, places=9)
        self.assertAlmostEqual(result["packet_fill_ratios"][1], 0.4, places=9)

    def test_an_oversized_activity_is_refused(self):
        spec = self._spec(
            activities=[activity(sequence_count=1, position=10.0, request_octets=9000)]
        )
        with self.assertRaises(ValueError):
            assess_detail_report(spec)

    def test_an_empty_selection_is_a_finding(self):
        result = assess_detail_report(self._spec(groups=[9]))
        self.assertEqual(result["entry_count"], 0)
        self.assertFalse(result["clean"])

    def test_a_wrapping_window_is_recorded(self):
        result = assess_detail_report(self._spec(window=(290.0, 30.0)))
        self.assertTrue(any("wraps" in f for f in result["findings"]))
        self.assertEqual(result["entry_count"], 2)

    def test_the_schedule_size_is_reported_beside_the_selection(self):
        result = assess_detail_report(self._spec(groups=[1]))
        self.assertEqual(result["entry_count"], 2)
        self.assertEqual(result["scheduled_count"], 3)

    def test_duplicate_identification_is_refused(self):
        spec = self._spec(
            activities=[
                activity(sequence_count=4, position=10.0),
                activity(sequence_count=4, position=200.0),
            ]
        )
        with self.assertRaises(ValueError):
            assess_detail_report(spec)

    def test_the_largest_entry_is_reported(self):
        result = assess_detail_report(self._spec())
        self.assertEqual(result["largest_entry_octets"], 200)

    def test_missing_spec_key_is_refused(self):
        spec = self._spec()
        del spec["max_packet_octets"]
        with self.assertRaises(ValueError):
            assess_detail_report(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_detail_report(["activities"])


if __name__ == "__main__":
    unittest.main()
