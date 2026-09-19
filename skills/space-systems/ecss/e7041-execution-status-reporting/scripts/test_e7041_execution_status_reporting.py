"""Contract test for the OBCP status reporting leaf (stdlib unittest)."""

import unittest

from e7041_execution_status_reporting_logic import (
    SCOPE_ALL,
    SCOPE_CHANGED,
    SCOPE_REQUESTED,
    STATUS_ACTIVE_RUNNING,
    STATUS_ACTIVE_SUSPENDED,
    STATUS_LOADED_INACTIVE,
    STATUS_TERMINATED_ABORTED,
    STATUS_TERMINATED_COMPLETED,
    assess_reporting_cadence,
    build_status_report,
    entries_per_packet,
    packet_octets,
    partition_report,
    select_all,
    select_changed,
    select_entries,
    select_requested,
    validate_entry,
    validate_packet_spec,
    validate_population,
    validate_status,
)


def entry(proc_id, status=STATUS_LOADED_INACTIVE, version=1):
    return {"id": proc_id, "version": version, "status": status}


def population():
    return [
        entry("OBCP-A", STATUS_ACTIVE_RUNNING),
        entry("OBCP-B", STATUS_LOADED_INACTIVE),
        entry("OBCP-C", STATUS_ACTIVE_SUSPENDED),
        entry("OBCP-D", STATUS_TERMINATED_ABORTED),
    ]


def spec(max_packet_octets=100, header_octets=12, entry_octets=8):
    return {
        "max_packet_octets": max_packet_octets,
        "header_octets": header_octets,
        "entry_octets": entry_octets,
    }


class TestEntryValidation(unittest.TestCase):
    def test_entry_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_entry(["OBCP-A", STATUS_ACTIVE_RUNNING])

    def test_an_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(entry(""))

    def test_an_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            validate_status("paused")

    def test_version_zero_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(entry("OBCP-A", version=0))

    def test_an_empty_population_raises(self):
        with self.assertRaises(ValueError):
            validate_population([])

    def test_a_duplicate_id_in_the_population_raises(self):
        with self.assertRaises(ValueError):
            validate_population([entry("OBCP-A"), entry("OBCP-A")])


class TestScopeSelection(unittest.TestCase):
    def test_all_keeps_the_store_order(self):
        self.assertEqual(
            [e["id"] for e in select_all(population())],
            ["OBCP-A", "OBCP-B", "OBCP-C", "OBCP-D"],
        )

    def test_a_requested_subset_keeps_the_requested_order(self):
        chosen = select_requested(population(), ["OBCP-C", "OBCP-A"])
        self.assertEqual([e["id"] for e in chosen], ["OBCP-C", "OBCP-A"])

    def test_requesting_a_procedure_not_aboard_raises(self):
        with self.assertRaises(ValueError):
            select_requested(population(), ["OBCP-Z"])

    def test_requesting_the_same_procedure_twice_raises(self):
        with self.assertRaises(ValueError):
            select_requested(population(), ["OBCP-A", "OBCP-A"])

    def test_an_empty_request_list_raises(self):
        with self.assertRaises(ValueError):
            select_requested(population(), [])

    def test_changed_reports_only_what_moved(self):
        previous = {
            "OBCP-A": STATUS_ACTIVE_RUNNING,
            "OBCP-B": STATUS_LOADED_INACTIVE,
            "OBCP-C": STATUS_ACTIVE_RUNNING,
            "OBCP-D": STATUS_TERMINATED_ABORTED,
        }
        self.assertEqual(
            [e["id"] for e in select_changed(population(), previous)],
            ["OBCP-C"],
        )

    def test_a_procedure_absent_from_the_previous_report_counts_as_changed(self):
        self.assertEqual(len(select_changed(population(), {})), 4)

    def test_a_changed_scope_without_a_previous_report_raises(self):
        with self.assertRaises(ValueError):
            select_entries(population(), SCOPE_CHANGED)

    def test_a_requested_scope_without_ids_raises(self):
        with self.assertRaises(ValueError):
            select_entries(population(), SCOPE_REQUESTED)

    def test_an_unknown_scope_raises(self):
        with self.assertRaises(ValueError):
            select_entries(population(), "everything-interesting")


class TestPacketGeometry(unittest.TestCase):
    def test_a_packet_too_small_for_one_entry_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_spec(spec(max_packet_octets=16, header_octets=12,
                                      entry_octets=8))

    def test_zero_entry_size_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_spec(spec(entry_octets=0))

    def test_a_negative_header_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_spec(spec(header_octets=-1))

    def test_capacity_is_the_space_left_after_the_header(self):
        self.assertEqual(entries_per_packet(spec()), 11)

    def test_a_packet_carrying_its_full_load_is_sized_exactly(self):
        self.assertEqual(packet_octets(spec(), 11), 100)

    def test_overfilling_a_packet_raises(self):
        with self.assertRaises(ValueError):
            packet_octets(spec(), 12)


class TestPartitioning(unittest.TestCase):
    def test_a_short_report_is_one_packet(self):
        packets = partition_report(population(), spec())
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0]["sequence_count"], 1)

    def test_a_long_report_becomes_a_counted_sequence(self):
        many = [entry("OBCP-%03d" % n) for n in range(25)]
        packets = partition_report(many, spec())
        self.assertEqual(len(packets), 3)
        self.assertEqual([p["sequence_number"] for p in packets], [1, 2, 3])
        self.assertTrue(all(p["sequence_count"] == 3 for p in packets))

    def test_no_entry_is_lost_across_the_split(self):
        many = [entry("OBCP-%03d" % n) for n in range(25)]
        packets = partition_report(many, spec())
        recovered = [e["id"] for p in packets for e in p["entries"]]
        self.assertEqual(recovered, [e["id"] for e in many])

    def test_the_last_packet_is_shorter_than_a_full_one(self):
        many = [entry("OBCP-%03d" % n) for n in range(25)]
        packets = partition_report(many, spec())
        self.assertEqual(packets[-1]["octets"], packet_octets(spec(), 3))

    def test_an_empty_report_is_still_one_packet(self):
        packets = partition_report([], spec())
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0]["entries"], [])


class TestReport(unittest.TestCase):
    def test_a_full_report_covers_every_procedure(self):
        report = build_status_report(population(), spec())
        self.assertEqual(report["entry_count"], 4)
        self.assertTrue(report["fits_one_packet"])

    def test_statuses_are_grouped_and_counted(self):
        report = build_status_report(population(), spec())
        self.assertEqual(report["grouped_by_status"][STATUS_ACTIVE_RUNNING],
                         ["OBCP-A"])
        self.assertEqual(
            report["counts_by_status"][STATUS_TERMINATED_COMPLETED], 0
        )

    def test_the_scope_is_carried_in_the_report(self):
        report = build_status_report(population(), spec(),
                                     scope=SCOPE_REQUESTED,
                                     requested_ids=["OBCP-B"])
        self.assertEqual(report["scope"], SCOPE_REQUESTED)
        self.assertEqual(report["covered_ids"], ["OBCP-B"])

    def test_total_octets_are_the_sum_over_the_packets(self):
        many = [entry("OBCP-%03d" % n) for n in range(25)]
        report = build_status_report(many, spec())
        self.assertEqual(report["total_octets"],
                         sum(p["octets"] for p in report["packets"]))

    def test_a_changed_scope_report_can_be_empty_and_still_ship(self):
        previous = {e["id"]: e["status"] for e in population()}
        report = build_status_report(population(), spec(),
                                     scope=SCOPE_CHANGED,
                                     previous_statuses=previous)
        self.assertEqual(report["entry_count"], 0)
        self.assertEqual(report["packet_count"], 1)


class TestCadence(unittest.TestCase):
    def test_a_cadence_within_budget_is_accepted(self):
        report = build_status_report(population(), spec())
        result = assess_reporting_cadence(report, 4, 10000)
        self.assertTrue(result["within_budget"])

    def test_a_cadence_exactly_on_budget_still_fits(self):
        report = build_status_report(population(), spec())
        budget = report["total_octets"] * 4
        result = assess_reporting_cadence(report, 4, budget)
        self.assertTrue(result["within_budget"])
        self.assertAlmostEqual(result["margin_octets_per_hour"], 0.0, places=9)

    def test_an_unaffordable_cadence_is_flagged(self):
        report = build_status_report(population(), spec())
        result = assess_reporting_cadence(report, 600, 1000)
        self.assertFalse(result["within_budget"])

    def test_the_affordable_rate_is_reported(self):
        report = build_status_report(population(), spec())
        result = assess_reporting_cadence(report, 1, 440)
        self.assertAlmostEqual(result["max_affordable_reports_per_hour"],
                               10.0, places=9)

    def test_a_zero_report_rate_raises(self):
        report = build_status_report(population(), spec())
        with self.assertRaises(ValueError):
            assess_reporting_cadence(report, 0, 1000)

    def test_cadence_needs_a_built_report(self):
        with self.assertRaises(ValueError):
            assess_reporting_cadence({"entries": []}, 1, 1000)


if __name__ == "__main__":
    unittest.main()
