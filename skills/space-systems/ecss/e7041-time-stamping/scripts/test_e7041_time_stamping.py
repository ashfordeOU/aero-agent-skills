"""Contract test for the storage time-stamping leaf (stdlib unittest)."""

import unittest

from e7041_time_stamping_logic import (
    COARSE_MAX,
    FINDING_STAMP_REPEATED,
    FINDING_STAMP_WENT_BACKWARDS,
    assess_storage_time_stamping,
    decode_storage_time,
    encode_storage_time,
    fine_units_per_second,
    quantisation_error_s,
    select_by_generation_window,
    select_by_storage_window,
    stamp_packet,
    stamp_packets,
    stamp_resolution_s,
    storage_latency_s,
)


def packet(packet_id="P-1", generation=None):
    record = {"id": packet_id}
    if generation is not None:
        record["generation_time_s"] = generation
    return record


class TestResolution(unittest.TestCase):
    def test_fine_units_are_a_power_of_two_per_octet(self):
        self.assertEqual(fine_units_per_second(1), 256)
        self.assertEqual(fine_units_per_second(2), 65536)

    def test_resolution_is_the_reciprocal_of_the_unit_count(self):
        self.assertAlmostEqual(stamp_resolution_s(1), 1.0 / 256.0, places=12)
        self.assertAlmostEqual(stamp_resolution_s(2), 1.0 / 65536.0, places=12)

    def test_zero_fine_octets_raises(self):
        with self.assertRaises(ValueError):
            stamp_resolution_s(0)

    def test_oversized_fine_field_raises(self):
        with self.assertRaises(ValueError):
            stamp_resolution_s(4)

    def test_boolean_fine_octets_raises(self):
        with self.assertRaises(ValueError):
            stamp_resolution_s(True)


class TestEncoding(unittest.TestCase):
    def test_a_whole_second_encodes_with_an_empty_fine_field(self):
        self.assertEqual(encode_storage_time(7.0, 1), (7, 0))

    def test_a_representable_fraction_round_trips_exactly(self):
        coarse, fine = encode_storage_time(7.5, 1)
        self.assertEqual((coarse, fine), (7, 128))
        self.assertAlmostEqual(decode_storage_time(coarse, fine, 1), 7.5, places=12)

    def test_the_stamp_never_reads_later_than_the_time_it_came_from(self):
        for seconds in (0.001, 1.9999, 12.3456789, 1000.5001):
            coarse, fine = encode_storage_time(seconds, 1)
            self.assertLessEqual(decode_storage_time(coarse, fine, 1), seconds)

    def test_quantisation_error_is_zero_on_a_representable_time(self):
        self.assertAlmostEqual(quantisation_error_s(7.5, 1), 0.0, places=12)

    def test_quantisation_error_stays_under_one_resolution_step(self):
        error = quantisation_error_s(0.001, 1)
        self.assertAlmostEqual(error, 0.001, places=12)
        self.assertLess(error, stamp_resolution_s(1))

    def test_a_wider_fine_field_carries_the_same_time_more_closely(self):
        self.assertLess(
            quantisation_error_s(12.3456789, 2), quantisation_error_s(12.3456789, 1)
        )

    def test_a_negative_time_raises(self):
        with self.assertRaises(ValueError):
            encode_storage_time(-1.0, 1)

    def test_a_time_past_the_coarse_field_raises(self):
        with self.assertRaises(ValueError):
            encode_storage_time(float(COARSE_MAX) + 2.0, 1)

    def test_a_fine_value_outside_its_field_raises(self):
        with self.assertRaises(ValueError):
            decode_storage_time(7, 256, 1)

    def test_a_boolean_coarse_value_raises(self):
        with self.assertRaises(ValueError):
            decode_storage_time(True, 0, 1)


class TestStampingOnePacket(unittest.TestCase):
    def test_a_stamped_packet_carries_its_storage_time(self):
        record = stamp_packet(packet(), 7.5, 1)
        self.assertAlmostEqual(record["storage_time_s"], 7.5, places=12)
        self.assertEqual(record["storage_time_coarse"], 7)
        self.assertEqual(record["storage_time_fine"], 128)

    def test_generation_time_is_kept_and_kept_separate(self):
        record = stamp_packet(packet(generation=2.0), 7.5, 1)
        self.assertAlmostEqual(record["generation_time_s"], 2.0, places=12)
        self.assertAlmostEqual(record["storage_time_s"], 7.5, places=12)

    def test_storage_latency_is_the_gap_between_the_two_times(self):
        record = stamp_packet(packet(generation=2.0), 7.5, 1)
        self.assertAlmostEqual(storage_latency_s(record), 5.5, places=12)

    def test_latency_without_a_generation_time_raises(self):
        with self.assertRaises(ValueError):
            storage_latency_s(stamp_packet(packet(), 7.5, 1))

    def test_a_stamp_before_generation_raises(self):
        with self.assertRaises(ValueError):
            storage_latency_s(stamp_packet(packet(generation=9.0), 7.5, 1))

    def test_a_packet_without_an_id_raises(self):
        with self.assertRaises(ValueError):
            stamp_packet({"generation_time_s": 1.0}, 7.5, 1)

    def test_a_packet_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            stamp_packet(["P-1"], 7.5, 1)


class TestStampingASequence(unittest.TestCase):
    def test_an_increasing_run_is_monotonic_and_clean(self):
        result = stamp_packets(
            [packet("P-1"), packet("P-2"), packet("P-3")], [1.0, 2.0, 3.0], 1
        )
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["stamped"]), 3)

    def test_two_packets_inside_one_resolution_step_share_a_stamp(self):
        result = stamp_packets([packet("P-1"), packet("P-2")], [1.0, 1.001], 1)
        self.assertEqual(result["findings"][0]["finding"], FINDING_STAMP_REPEATED)
        self.assertAlmostEqual(
            result["stamped"][0]["storage_time_s"],
            result["stamped"][1]["storage_time_s"],
            places=12,
        )

    def test_a_backwards_stamp_is_a_finding(self):
        result = stamp_packets([packet("P-1"), packet("P-2")], [5.0, 2.0], 1)
        self.assertEqual(result["findings"][0]["finding"], FINDING_STAMP_WENT_BACKWARDS)
        self.assertEqual(result["findings"][0]["previous_id"], "P-1")

    def test_mismatched_lengths_raise(self):
        with self.assertRaises(ValueError):
            stamp_packets([packet("P-1"), packet("P-2")], [1.0], 1)

    def test_an_empty_run_raises(self):
        with self.assertRaises(ValueError):
            stamp_packets([], [], 1)


class TestRetrievalWindow(unittest.TestCase):
    def setUp(self):
        self.stamped = stamp_packets(
            [
                packet("P-1", generation=1.0),
                packet("P-2", generation=2.0),
                packet("P-3", generation=3.0),
            ],
            [10.0, 11.0, 30.0],
            1,
        )["stamped"]

    def test_the_window_selects_on_storage_time(self):
        selected = select_by_storage_window(self.stamped, 9.0, 12.0)
        self.assertEqual([r["id"] for r in selected], ["P-1", "P-2"])

    def test_the_same_window_on_generation_time_answers_differently(self):
        selected = select_by_generation_window(self.stamped, 9.0, 12.0)
        self.assertEqual(selected, [])

    def test_the_window_is_closed_at_both_ends(self):
        selected = select_by_storage_window(self.stamped, 10.0, 11.0)
        self.assertEqual([r["id"] for r in selected], ["P-1", "P-2"])

    def test_an_inverted_window_raises(self):
        with self.assertRaises(ValueError):
            select_by_storage_window(self.stamped, 12.0, 9.0)

    def test_a_record_without_a_storage_time_raises(self):
        with self.assertRaises(ValueError):
            select_by_storage_window([{"id": "P-9"}], 0.0, 1.0)


class TestAssessment(unittest.TestCase):
    def test_a_clean_run_reports_monotonic_with_no_findings(self):
        report = assess_storage_time_stamping(
            [packet("P-1"), packet("P-2")], [1.0, 2.0], 1
        )
        self.assertTrue(report["monotonic"])
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["resolution_s"], 1.0 / 256.0, places=12)

    def test_a_time_correction_shows_up_as_a_non_monotonic_run(self):
        report = assess_storage_time_stamping(
            [packet("P-1"), packet("P-2")], [5.0, 2.0], 1
        )
        self.assertFalse(report["monotonic"])
        self.assertEqual(report["packet_count"], 2)

    def test_the_two_window_answers_are_reported_side_by_side(self):
        report = assess_storage_time_stamping(
            [packet("P-1", generation=1.0), packet("P-2", generation=2.0)],
            [10.0, 11.0],
            1,
            window=(9.0, 12.0),
        )
        self.assertEqual(report["window"]["storage_time_ids"], ["P-1", "P-2"])
        self.assertEqual(report["window"]["generation_time_ids"], [])
        self.assertFalse(report["window"]["answers_agree"])

    def test_the_answers_agree_when_storage_followed_generation_closely(self):
        report = assess_storage_time_stamping(
            [packet("P-1", generation=10.0), packet("P-2", generation=11.0)],
            [10.0, 11.0],
            1,
            window=(9.0, 12.0),
        )
        self.assertTrue(report["window"]["answers_agree"])

    def test_a_malformed_window_raises(self):
        with self.assertRaises(ValueError):
            assess_storage_time_stamping(
                [packet("P-1")], [1.0], 1, window=(1.0, 2.0, 3.0)
            )


if __name__ == "__main__":
    unittest.main()
