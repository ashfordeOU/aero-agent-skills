"""Contract tests for the clause 6.13.3.2 downlink resource logic."""

import unittest

from e7041_resources_logic import (
    admit_in_arrival_order,
    assess_downlink_resources,
    peak_simultaneous,
    reserved_octets,
    validate_demand,
    validate_resources,
)

PART = 1000


def txn(tid, octets, start, end):
    return {"transaction_id": tid, "message_octets": octets, "start": start, "end": end}


class ReservedOctetsTests(unittest.TestCase):
    def test_exact_multiple_reserves_the_message(self):
        self.assertEqual(reserved_octets(4000, PART), 4000)

    def test_partial_final_part_is_reserved_whole(self):
        self.assertEqual(reserved_octets(4001, PART), 5000)

    def test_message_below_one_part_reserves_a_whole_part(self):
        self.assertEqual(reserved_octets(1, PART), 1000)

    def test_zero_length_message_is_refused(self):
        with self.assertRaises(ValueError):
            reserved_octets(0, PART)

    def test_non_integer_message_is_refused(self):
        with self.assertRaises(ValueError):
            reserved_octets(4000.0, PART)


class ResourceValidationTests(unittest.TestCase):
    def test_valid_declaration_is_returned_as_a_triple(self):
        spec = {"transaction_slots": 4, "buffer_pool_octets": 40000, "part_octets": PART}
        self.assertEqual(validate_resources(spec), (4, 40000, PART))

    def test_zero_slots_is_refused(self):
        spec = {"transaction_slots": 0, "buffer_pool_octets": 40000, "part_octets": PART}
        with self.assertRaises(ValueError):
            validate_resources(spec)

    def test_missing_pool_is_refused(self):
        with self.assertRaises(ValueError):
            validate_resources({"transaction_slots": 4, "part_octets": PART})

    def test_non_mapping_declaration_is_refused(self):
        with self.assertRaises(ValueError):
            validate_resources([4, 40000, PART])


class DemandValidationTests(unittest.TestCase):
    def test_footprint_is_attached_to_every_record(self):
        records = validate_demand([txn("a", 2500, 0.0, 10.0)], PART)
        self.assertEqual(records[0]["reserved_octets"], 3000)

    def test_window_ending_before_it_starts_is_refused(self):
        with self.assertRaises(ValueError):
            validate_demand([txn("a", 2500, 10.0, 4.0)], PART)

    def test_instantaneous_window_is_accepted(self):
        records = validate_demand([txn("a", 2500, 5.0, 5.0)], PART)
        self.assertAlmostEqual(records[0]["end"], 5.0, places=9)

    def test_missing_key_is_refused(self):
        with self.assertRaises(ValueError):
            validate_demand([{"transaction_id": "a", "start": 0.0, "end": 1.0}], PART)

    def test_non_numeric_instant_is_refused(self):
        with self.assertRaises(ValueError):
            validate_demand([txn("a", 2500, "0", 10.0)], PART)

    def test_non_sequence_demand_is_refused(self):
        with self.assertRaises(ValueError):
            validate_demand({"transaction_id": "a"}, PART)


class PeakTests(unittest.TestCase):
    def test_overlapping_transactions_raise_the_peak(self):
        records = validate_demand(
            [txn("a", 2000, 0.0, 10.0), txn("b", 3000, 5.0, 15.0)], PART
        )
        peaks = peak_simultaneous(records)
        self.assertEqual(peaks["peak_transactions"], 2)
        self.assertEqual(peaks["peak_reserved_octets"], 5000)

    def test_back_to_back_transactions_never_coexist(self):
        records = validate_demand(
            [txn("a", 2000, 0.0, 10.0), txn("b", 3000, 10.0, 20.0)], PART
        )
        peaks = peak_simultaneous(records)
        self.assertEqual(peaks["peak_transactions"], 1)
        self.assertEqual(peaks["peak_reserved_octets"], 3000)

    def test_peak_octets_can_occur_after_the_peak_count(self):
        records = validate_demand(
            [
                txn("a", 1000, 0.0, 4.0),
                txn("b", 1000, 1.0, 4.0),
                txn("c", 9000, 6.0, 9.0),
            ],
            PART,
        )
        peaks = peak_simultaneous(records)
        self.assertEqual(peaks["peak_transactions"], 2)
        self.assertEqual(peaks["peak_reserved_octets"], 9000)
        self.assertAlmostEqual(peaks["peak_reserved_octets_at"], 6.0, places=9)

    def test_empty_demand_gives_a_zero_peak(self):
        peaks = peak_simultaneous([])
        self.assertEqual(peaks["peak_transactions"], 0)
        self.assertEqual(peaks["peak_reserved_octets"], 0)


class AdmissionTests(unittest.TestCase):
    def test_slot_exhaustion_refuses_the_third_arrival(self):
        records = validate_demand(
            [
                txn("a", 1000, 0.0, 10.0),
                txn("b", 1000, 1.0, 10.0),
                txn("c", 1000, 2.0, 10.0),
            ],
            PART,
        )
        decisions = admit_in_arrival_order(records, 2, 100000)
        self.assertTrue(decisions[0]["admitted"])
        self.assertTrue(decisions[1]["admitted"])
        self.assertFalse(decisions[2]["admitted"])
        self.assertEqual(decisions[2]["refused_because"], "no free transaction slot")

    def test_buffer_exhaustion_names_the_pool(self):
        records = validate_demand(
            [txn("a", 6000, 0.0, 10.0), txn("b", 6000, 1.0, 10.0)], PART
        )
        decisions = admit_in_arrival_order(records, 8, 10000)
        self.assertTrue(decisions[0]["admitted"])
        self.assertFalse(decisions[1]["admitted"])
        self.assertEqual(decisions[1]["refused_because"], "buffer pool exhausted")

    def test_released_slot_is_reused_by_a_later_arrival(self):
        records = validate_demand(
            [txn("a", 1000, 0.0, 5.0), txn("b", 1000, 5.0, 10.0)], PART
        )
        decisions = admit_in_arrival_order(records, 1, 100000)
        self.assertTrue(all(d["admitted"] for d in decisions))

    def test_refused_transaction_does_not_consume_the_pool(self):
        records = validate_demand(
            [
                txn("a", 6000, 0.0, 10.0),
                txn("b", 6000, 1.0, 10.0),
                txn("c", 3000, 2.0, 10.0),
            ],
            PART,
        )
        decisions = admit_in_arrival_order(records, 8, 10000)
        self.assertFalse(decisions[1]["admitted"])
        self.assertTrue(decisions[2]["admitted"])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "transaction_slots": 3,
            "buffer_pool_octets": 20000,
            "part_octets": PART,
            "demand": [
                txn("a", 4500, 0.0, 10.0),
                txn("b", 3200, 2.0, 8.0),
                txn("c", 1500, 12.0, 20.0),
            ],
        }
        spec.update(overrides)
        return spec

    def test_sufficient_declaration_reports_no_findings(self):
        result = assess_downlink_resources(self._spec())
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["findings"], [])

    def test_peaks_are_reported(self):
        result = assess_downlink_resources(self._spec())
        self.assertEqual(result["peak_transactions"], 2)
        self.assertEqual(result["peak_reserved_octets"], 9000)

    def test_slot_shortfall_is_flagged(self):
        result = assess_downlink_resources(self._spec(transaction_slots=1))
        self.assertFalse(result["sufficient"])
        self.assertTrue(any("declared slots" in f for f in result["findings"]))

    def test_pool_shortfall_is_flagged(self):
        result = assess_downlink_resources(self._spec(buffer_pool_octets=5000))
        self.assertFalse(result["sufficient"])
        self.assertTrue(any("buffer pool" in f for f in result["findings"]))

    def test_message_larger_than_the_whole_pool_is_flagged(self):
        result = assess_downlink_resources(
            self._spec(buffer_pool_octets=4000, demand=[txn("a", 9000, 0.0, 5.0)])
        )
        self.assertTrue(any("whole" in f for f in result["findings"]))

    def test_refused_transactions_are_listed(self):
        result = assess_downlink_resources(self._spec(transaction_slots=1))
        self.assertEqual(result["refused"], ["b"])

    def test_missing_demand_is_refused(self):
        spec = self._spec()
        del spec["demand"]
        with self.assertRaises(ValueError):
            assess_downlink_resources(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_downlink_resources(["demand"])


if __name__ == "__main__":
    unittest.main()
