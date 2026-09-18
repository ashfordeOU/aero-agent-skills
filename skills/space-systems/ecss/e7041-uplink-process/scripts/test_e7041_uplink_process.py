"""Contract tests for the clause 6.13.4.3 uplink process logic."""

import unittest

from e7041_uplink_process_logic import (
    ABORT_BUFFER_OVERFLOW,
    ABORT_DUPLICATE_FIRST_PART,
    ABORT_DUPLICATE_PART,
    ABORT_INCOMPLETE_AT_END_OF_STREAM,
    ABORT_INTER_PART_TIMEOUT,
    ABORT_OVERSIZED_PART,
    ABORT_SEQUENCE_GAP,
    ABORT_SHORT_PART,
    ABORT_UNEXPECTED_PART,
    FIRST_PART,
    INTERMEDIATE_PART,
    LAST_PART,
    assess_uplink_process,
    reassemble,
    validate_part_stream,
    validate_receiver,
)

PART = 1000
RECEIVER = {
    "part_octets": PART,
    "reception_buffer_octets": 10000,
    "inter_part_timeout_s": 5.0,
}


def part(tid, role, sequence, octets, time_s):
    return {
        "transaction_id": tid,
        "part_type": role,
        "sequence": sequence,
        "octets": octets,
        "time_s": time_s,
    }


def nominal_stream(tid=1, start=0.0):
    return [
        part(tid, FIRST_PART, 1, PART, start),
        part(tid, INTERMEDIATE_PART, 2, PART, start + 1.0),
        part(tid, LAST_PART, 3, 400, start + 2.0),
    ]


class ReceiverValidationTests(unittest.TestCase):
    def test_valid_receiver_is_returned_as_a_triple(self):
        self.assertEqual(validate_receiver(RECEIVER), (PART, 10000, 5.0))

    def test_timeout_is_optional(self):
        config = {"part_octets": PART, "reception_buffer_octets": 10000}
        self.assertIsNone(validate_receiver(config)[2])

    def test_zero_part_size_is_refused(self):
        with self.assertRaises(ValueError):
            validate_receiver({"part_octets": 0, "reception_buffer_octets": 10000})

    def test_negative_timeout_is_refused(self):
        config = dict(RECEIVER, inter_part_timeout_s=-1.0)
        with self.assertRaises(ValueError):
            validate_receiver(config)

    def test_missing_buffer_is_refused(self):
        with self.assertRaises(ValueError):
            validate_receiver({"part_octets": PART})


class StreamValidationTests(unittest.TestCase):
    def test_nominal_stream_validates(self):
        self.assertEqual(len(validate_part_stream(nominal_stream())), 3)

    def test_unknown_part_role_is_refused(self):
        stream = nominal_stream()
        stream[1]["part_type"] = "middle"
        with self.assertRaises(ValueError):
            validate_part_stream(stream)

    def test_backwards_timestamp_is_refused(self):
        stream = nominal_stream()
        stream[2]["time_s"] = -1.0
        with self.assertRaises(ValueError):
            validate_part_stream(stream)

    def test_zero_octet_part_is_refused(self):
        stream = nominal_stream()
        stream[1]["octets"] = 0
        with self.assertRaises(ValueError):
            validate_part_stream(stream)

    def test_missing_key_is_refused(self):
        with self.assertRaises(ValueError):
            validate_part_stream([{"transaction_id": 1, "part_type": FIRST_PART}])

    def test_non_sequence_stream_is_refused(self):
        with self.assertRaises(ValueError):
            validate_part_stream({"transaction_id": 1})


class ReassemblyTests(unittest.TestCase):
    def test_nominal_stream_completes(self):
        outcomes = reassemble(nominal_stream(), RECEIVER)
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["status"], "complete")
        self.assertEqual(outcomes[0]["octets"], 2400)
        self.assertEqual(outcomes[0]["parts_accepted"], 3)

    def test_two_part_transfer_completes(self):
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(1, LAST_PART, 2, 100, 1.0),
        ]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["octets"], 1100)

    def test_intermediate_part_with_nothing_open_is_refused(self):
        stream = [part(1, INTERMEDIATE_PART, 2, PART, 0.0)]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["reason"], ABORT_UNEXPECTED_PART)

    def test_last_part_with_nothing_open_is_refused(self):
        stream = [part(1, LAST_PART, 4, 200, 0.0)]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["reason"], ABORT_UNEXPECTED_PART)

    def test_second_first_part_aborts_the_open_reception(self):
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(1, FIRST_PART, 1, PART, 1.0),
        ]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["reason"], ABORT_DUPLICATE_FIRST_PART)

    def test_repeated_part_number_aborts(self):
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(1, INTERMEDIATE_PART, 2, PART, 1.0),
            part(1, INTERMEDIATE_PART, 2, PART, 2.0),
        ]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["reason"], ABORT_DUPLICATE_PART)
        self.assertEqual(outcomes[0]["parts_accepted"], 2)

    def test_skipped_part_number_aborts(self):
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(1, INTERMEDIATE_PART, 3, PART, 1.0),
        ]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["reason"], ABORT_SEQUENCE_GAP)

    def test_first_part_numbered_other_than_one_aborts(self):
        stream = [part(1, FIRST_PART, 2, PART, 0.0)]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["reason"], ABORT_SEQUENCE_GAP)

    def test_short_intermediate_part_aborts(self):
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(1, INTERMEDIATE_PART, 2, 400, 1.0),
        ]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["reason"], ABORT_SHORT_PART)

    def test_short_first_part_aborts(self):
        stream = [part(1, FIRST_PART, 1, 400, 0.0)]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["reason"], ABORT_SHORT_PART)

    def test_oversized_part_aborts(self):
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(1, INTERMEDIATE_PART, 2, 1400, 1.0),
        ]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["reason"], ABORT_OVERSIZED_PART)

    def test_buffer_overflow_aborts(self):
        small = dict(RECEIVER, reception_buffer_octets=1500)
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(1, INTERMEDIATE_PART, 2, PART, 1.0),
        ]
        outcomes = reassemble(stream, small)
        self.assertEqual(outcomes[0]["reason"], ABORT_BUFFER_OVERFLOW)

    def test_gap_past_the_timeout_aborts(self):
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(1, INTERMEDIATE_PART, 2, PART, 20.0),
        ]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["reason"], ABORT_INTER_PART_TIMEOUT)

    def test_gap_exactly_at_the_timeout_is_accepted(self):
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(1, LAST_PART, 2, 200, 5.0),
        ]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["status"], "complete")

    def test_no_timeout_configured_accepts_any_gap(self):
        config = {"part_octets": PART, "reception_buffer_octets": 10000}
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(1, LAST_PART, 2, 200, 9000.0),
        ]
        outcomes = reassemble(stream, config)
        self.assertEqual(outcomes[0]["status"], "complete")

    def test_stream_ending_mid_transfer_is_incomplete(self):
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(1, INTERMEDIATE_PART, 2, PART, 1.0),
        ]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["reason"], ABORT_INCOMPLETE_AT_END_OF_STREAM)
        self.assertEqual(outcomes[0]["parts_accepted"], 2)

    def test_two_transactions_interleave_independently(self):
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(2, FIRST_PART, 1, PART, 0.5),
            part(1, LAST_PART, 2, 100, 1.0),
            part(2, LAST_PART, 2, 300, 1.5),
        ]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(len(outcomes), 2)
        self.assertTrue(all(o["status"] == "complete" for o in outcomes))
        self.assertEqual(outcomes[0]["octets"], 1100)
        self.assertEqual(outcomes[1]["octets"], 1300)

    def test_a_transaction_can_be_reused_after_it_completes(self):
        stream = nominal_stream(1, 0.0) + nominal_stream(1, 10.0)
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(len(outcomes), 2)
        self.assertTrue(all(o["status"] == "complete" for o in outcomes))

    def test_aborted_reception_reports_no_octets(self):
        stream = [
            part(1, FIRST_PART, 1, PART, 0.0),
            part(1, INTERMEDIATE_PART, 4, PART, 1.0),
        ]
        outcomes = reassemble(stream, RECEIVER)
        self.assertEqual(outcomes[0]["octets"], 0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = dict(RECEIVER)
        spec["parts"] = nominal_stream()
        spec.update(overrides)
        return spec

    def test_clean_stream_reports_no_findings(self):
        result = assess_uplink_process(self._spec())
        self.assertTrue(result["clean"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["octets_reassembled"], 2400)

    def test_aborted_stream_is_flagged(self):
        stream = [part(1, LAST_PART, 4, 200, 0.0)]
        result = assess_uplink_process(self._spec(parts=stream))
        self.assertFalse(result["clean"])
        self.assertEqual(len(result["findings"]), 1)

    def test_empty_stream_is_not_clean(self):
        result = assess_uplink_process(self._spec(parts=[]))
        self.assertFalse(result["clean"])
        self.assertEqual(result["outcomes"], [])

    def test_missing_parts_key_is_refused(self):
        spec = self._spec()
        del spec["parts"]
        with self.assertRaises(ValueError):
            assess_uplink_process(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_uplink_process(["parts"])


if __name__ == "__main__":
    unittest.main()
