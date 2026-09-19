"""Contract tests for the clause 6.22.9.1 schedule summary report logic."""

import unittest

from e7041_position_based_schedule_summary_report_logic import (
    POSITION_TOLERANCE_DEG,
    REVOLUTION_DEG,
    SUMMARY_ENTRY_FIELDS,
    build_summary_report,
    order_summary_entries,
    position_window_contains,
    select_activities,
    summary_entry,
    summary_report_octets,
    validate_identification,
    validate_position_deg,
)


def activity(source_id=1, apid=10, sequence_count=1, position=30.0, group=1, request=None):
    entry = {
        "source_id": source_id,
        "apid": apid,
        "sequence_count": sequence_count,
        "position_deg": position,
        "group": group,
    }
    if request is not None:
        entry["request"] = request
    return entry


class PositionTests(unittest.TestCase):
    def test_origin_is_a_valid_position(self):
        self.assertAlmostEqual(validate_position_deg(0), 0.0, places=9)

    def test_integer_position_is_taken_as_degrees(self):
        self.assertAlmostEqual(validate_position_deg(90), 90.0, places=9)

    def test_a_full_revolution_is_the_origin_and_is_refused(self):
        with self.assertRaises(ValueError):
            validate_position_deg(REVOLUTION_DEG)

    def test_negative_position_is_refused(self):
        with self.assertRaises(ValueError):
            validate_position_deg(-0.5)

    def test_non_numeric_position_is_refused(self):
        with self.assertRaises(ValueError):
            validate_position_deg("90 deg")

    def test_boolean_position_is_refused(self):
        with self.assertRaises(ValueError):
            validate_position_deg(True)


class IdentificationTests(unittest.TestCase):
    def test_identification_is_the_three_packet_fields(self):
        self.assertEqual(validate_identification(activity()), (1, 10, 1))

    def test_application_process_past_its_field_is_refused(self):
        with self.assertRaises(ValueError):
            validate_identification(activity(apid=2048))

    def test_widest_sequence_count_is_accepted(self):
        self.assertEqual(validate_identification(activity(sequence_count=16383))[2], 16383)

    def test_negative_source_is_refused(self):
        with self.assertRaises(ValueError):
            validate_identification(activity(source_id=-1))

    def test_missing_identification_key_is_refused(self):
        broken = activity()
        del broken["apid"]
        with self.assertRaises(ValueError):
            validate_identification(broken)


class SummaryEntryTests(unittest.TestCase):
    def test_entry_carries_only_the_summary_fields(self):
        entry = summary_entry(activity(request={"opcode": "TC"}))
        self.assertEqual(tuple(sorted(entry)), tuple(sorted(SUMMARY_ENTRY_FIELDS)))

    def test_request_content_is_dropped_from_the_entry(self):
        entry = summary_entry(activity(request={"opcode": "TC"}))
        self.assertNotIn("request", entry)

    def test_entry_keeps_the_scheduling_group(self):
        self.assertEqual(summary_entry(activity(group=4))["group"], 4)

    def test_missing_position_is_refused(self):
        broken = activity()
        del broken["position_deg"]
        with self.assertRaises(ValueError):
            summary_entry(broken)

    def test_zero_group_is_refused(self):
        with self.assertRaises(ValueError):
            summary_entry(activity(group=0))


class WindowTests(unittest.TestCase):
    def test_position_inside_a_plain_window_is_kept(self):
        self.assertTrue(position_window_contains(10.0, 50.0, 30.0))

    def test_position_outside_a_plain_window_is_dropped(self):
        self.assertFalse(position_window_contains(10.0, 50.0, 60.0))

    def test_a_position_on_the_lower_bound_is_inside(self):
        self.assertTrue(position_window_contains(10.0, 50.0, 10.0))

    def test_a_position_on_the_upper_bound_is_inside(self):
        self.assertTrue(position_window_contains(10.0, 50.0, 50.0))

    def test_a_wrapping_window_keeps_both_arcs(self):
        self.assertTrue(position_window_contains(350.0, 10.0, 355.0))
        self.assertTrue(position_window_contains(350.0, 10.0, 5.0))

    def test_a_wrapping_window_drops_the_far_side(self):
        self.assertFalse(position_window_contains(350.0, 10.0, 180.0))

    def test_the_edge_tolerance_is_small_enough_to_be_an_edge(self):
        self.assertLess(POSITION_TOLERANCE_DEG, 1e-6)


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.schedule = [
            activity(sequence_count=1, position=300.0, group=1),
            activity(sequence_count=2, position=20.0, group=2),
            activity(sequence_count=3, position=120.0, group=1),
        ]

    def test_no_selection_keeps_every_activity(self):
        self.assertEqual(len(select_activities(self.schedule)), 3)

    def test_group_selection_keeps_only_that_group(self):
        kept = select_activities(self.schedule, groups=[2])
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["sequence_count"], 2)

    def test_window_selection_keeps_the_positions_inside_it(self):
        kept = select_activities(self.schedule, window=(100.0, 200.0))
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["sequence_count"], 3)

    def test_a_wrapping_window_selects_across_the_origin(self):
        kept = select_activities(self.schedule, window=(290.0, 30.0))
        self.assertEqual(len(kept), 2)

    def test_empty_group_selection_is_refused(self):
        with self.assertRaises(ValueError):
            select_activities(self.schedule, groups=[])

    def test_malformed_window_is_refused(self):
        with self.assertRaises(ValueError):
            select_activities(self.schedule, window=(10.0,))


class OrderingTests(unittest.TestCase):
    def test_entries_come_out_by_increasing_position(self):
        entries = select_activities(
            [
                activity(sequence_count=1, position=300.0),
                activity(sequence_count=2, position=20.0),
            ]
        )
        ordered = order_summary_entries(entries)
        self.assertAlmostEqual(ordered[0]["position_deg"], 20.0, places=9)
        self.assertAlmostEqual(ordered[1]["position_deg"], 300.0, places=9)

    def test_a_shared_position_is_broken_on_the_identification(self):
        entries = select_activities(
            [
                activity(sequence_count=9, position=45.0),
                activity(sequence_count=2, position=45.0),
            ]
        )
        ordered = order_summary_entries(entries)
        self.assertEqual(
            [e["sequence_count"] for e in ordered],
            [2, 9],
        )

    def test_ordering_a_non_sequence_is_refused(self):
        with self.assertRaises(ValueError):
            order_summary_entries("entries")


class SizingTests(unittest.TestCase):
    def test_report_size_is_header_plus_the_entries(self):
        self.assertEqual(summary_report_octets(4, 12, 8), 44)

    def test_an_empty_report_is_just_its_header(self):
        self.assertEqual(summary_report_octets(0, 12, 8), 12)

    def test_negative_entry_count_is_refused(self):
        with self.assertRaises(ValueError):
            summary_report_octets(-1, 12, 8)

    def test_zero_entry_size_is_refused(self):
        with self.assertRaises(ValueError):
            summary_report_octets(4, 12, 0)


class ReportTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "activities": [
                activity(sequence_count=1, position=300.0, group=1, request={"a": 1}),
                activity(sequence_count=2, position=20.0, group=2, request={"a": 2}),
                activity(sequence_count=3, position=120.0, group=1, request={"a": 3}),
            ]
        }
        spec.update(over)
        return spec

    def test_report_is_ordered_and_complete(self):
        report = build_summary_report(self._spec())
        self.assertEqual(report["entry_count"], 3)
        self.assertAlmostEqual(report["first_position_deg"], 20.0, places=9)
        self.assertAlmostEqual(report["last_position_deg"], 300.0, places=9)

    def test_report_never_carries_request_content(self):
        report = build_summary_report(self._spec())
        self.assertFalse(report["carries_request_content"])
        for entry in report["entries"]:
            self.assertNotIn("request", entry)

    def test_group_selection_is_reported_against_the_whole_schedule(self):
        report = build_summary_report(self._spec(groups=[1]))
        self.assertEqual(report["entry_count"], 2)
        self.assertEqual(report["scheduled_count"], 3)

    def test_an_empty_selection_is_a_finding_not_an_error(self):
        report = build_summary_report(self._spec(groups=[7]))
        self.assertEqual(report["entry_count"], 0)
        self.assertFalse(report["clean"])

    def test_a_wrapping_window_is_recorded_as_a_finding(self):
        report = build_summary_report(self._spec(window=(290.0, 30.0)))
        self.assertTrue(any("wraps" in f for f in report["findings"]))

    def test_report_octets_are_sized_when_the_layout_is_given(self):
        report = build_summary_report(self._spec(header_octets=12, entry_octets=8))
        self.assertEqual(report["report_octets"], 36)

    def test_duplicate_identification_in_the_schedule_is_refused(self):
        spec = self._spec(
            activities=[
                activity(sequence_count=5, position=10.0),
                activity(sequence_count=5, position=200.0),
            ]
        )
        with self.assertRaises(ValueError):
            build_summary_report(spec)

    def test_missing_activities_key_is_refused(self):
        with self.assertRaises(ValueError):
            build_summary_report({})

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            build_summary_report(["activities"])


if __name__ == "__main__":
    unittest.main()
