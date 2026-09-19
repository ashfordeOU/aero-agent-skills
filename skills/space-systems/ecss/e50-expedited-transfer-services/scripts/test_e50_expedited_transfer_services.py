"""Contract tests for the clause 5.7.2.3 expedited transfer service logic."""

import unittest

from e50_expedited_transfer_services_logic import (
    MET,
    MISSED,
    NOT_EXPEDITED,
    ahead_bits,
    assess_expedited_transfer,
    interference_bits,
    max_non_preemptable_bits,
    required_link_rate,
    transmission_time,
    validate_bits,
    validate_deadline,
    validate_rate,
    worst_case_latency,
)

MESSAGE = 1000.0
BLOCKING = 2000.0
RATE = 1000000.0
DEADLINE = 0.01
PEERS = [500.0, 500.0]
BACKLOG = 100000.0


class ValidationTests(unittest.TestCase):
    def test_zero_bits_accepted(self):
        self.assertAlmostEqual(validate_bits(0), 0.0, places=9)

    def test_negative_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits(-1.0)

    def test_boolean_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits(True)

    def test_text_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits("1000")

    def test_nan_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits(float("nan"))

    def test_zero_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(0.0)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(-1.0)

    def test_zero_deadline_rejected(self):
        with self.assertRaises(ValueError):
            validate_deadline(0.0)

    def test_infinite_deadline_rejected(self):
        with self.assertRaises(ValueError):
            validate_deadline(float("inf"))

    def test_non_list_peers_rejected(self):
        with self.assertRaises(ValueError):
            interference_bits(500.0)

    def test_negative_peer_rejected(self):
        with self.assertRaises(ValueError):
            interference_bits([500.0, -1.0])

    def test_absent_peers_contribute_nothing(self):
        self.assertAlmostEqual(interference_bits(None), 0.0, places=9)

    def test_non_boolean_precedence_rejected(self):
        with self.assertRaises(ValueError):
            ahead_bits(MESSAGE, BLOCKING, PEERS, BACKLOG, precedence="yes")


class QueueTests(unittest.TestCase):
    def test_peers_sum(self):
        self.assertAlmostEqual(interference_bits(PEERS), 1000.0, places=9)

    def test_transmission_time_is_bits_over_rate(self):
        self.assertAlmostEqual(transmission_time(2000.0, RATE), 0.002, places=9)

    def test_precedence_keeps_the_backlog_out_of_the_queue(self):
        self.assertAlmostEqual(
            ahead_bits(MESSAGE, BLOCKING, PEERS, BACKLOG, True), 4000.0, places=9
        )

    def test_no_precedence_puts_the_backlog_in_front(self):
        self.assertAlmostEqual(
            ahead_bits(MESSAGE, BLOCKING, PEERS, BACKLOG, False), 104000.0, places=9
        )

    def test_worst_case_is_the_queue_over_the_rate(self):
        self.assertAlmostEqual(
            worst_case_latency(MESSAGE, BLOCKING, RATE, PEERS, BACKLOG), 0.004, places=9
        )

    def test_a_faster_link_shortens_the_worst_case_proportionally(self):
        slow = worst_case_latency(MESSAGE, BLOCKING, RATE, PEERS, BACKLOG)
        fast = worst_case_latency(MESSAGE, BLOCKING, 2.0 * RATE, PEERS, BACKLOG)
        self.assertAlmostEqual(fast, slow / 2.0, places=9)

    def test_blocking_dominates_a_small_message(self):
        result = assess_expedited_transfer(10.0, BLOCKING, RATE, DEADLINE)
        self.assertGreater(result["blocking_time_s"], 100.0 * result["own_time_s"])


class InverseTests(unittest.TestCase):
    def test_tolerable_unit_size_from_the_deadline(self):
        self.assertAlmostEqual(
            max_non_preemptable_bits(MESSAGE, RATE, DEADLINE, PEERS, BACKLOG),
            8000.0,
            places=9,
        )

    def test_unreachable_deadline_tolerates_no_blocking(self):
        self.assertAlmostEqual(
            max_non_preemptable_bits(MESSAGE, RATE, 0.0005, PEERS, BACKLOG), 0.0, places=9
        )

    def test_required_rate_from_the_deadline(self):
        self.assertAlmostEqual(
            required_link_rate(MESSAGE, BLOCKING, DEADLINE, PEERS, BACKLOG),
            400000.0,
            places=9,
        )

    def test_losing_precedence_raises_the_required_rate(self):
        with_pre = required_link_rate(MESSAGE, BLOCKING, DEADLINE, PEERS, BACKLOG, True)
        without = required_link_rate(MESSAGE, BLOCKING, DEADLINE, PEERS, BACKLOG, False)
        self.assertGreater(without, 10.0 * with_pre)

    def test_the_stated_required_rate_meets_the_deadline(self):
        rate = required_link_rate(MESSAGE, BLOCKING, DEADLINE, PEERS, BACKLOG)
        result = assess_expedited_transfer(MESSAGE, BLOCKING, rate, DEADLINE, PEERS, BACKLOG)
        self.assertTrue(result["on_time"])

    def test_the_stated_unit_size_meets_the_deadline(self):
        unit = max_non_preemptable_bits(MESSAGE, RATE, DEADLINE, PEERS, BACKLOG)
        result = assess_expedited_transfer(MESSAGE, unit, RATE, DEADLINE, PEERS, BACKLOG)
        self.assertTrue(result["on_time"])


class AssessmentTests(unittest.TestCase):
    def test_a_sound_expedited_path_meets_the_deadline(self):
        result = assess_expedited_transfer(MESSAGE, BLOCKING, RATE, DEADLINE, PEERS, BACKLOG)
        self.assertEqual(result["verdict"], MET)
        self.assertEqual(result["findings"], [])

    def test_a_tight_deadline_is_missed(self):
        result = assess_expedited_transfer(MESSAGE, BLOCKING, RATE, 0.001, PEERS, BACKLOG)
        self.assertEqual(result["verdict"], MISSED)
        self.assertFalse(result["on_time"])

    def test_a_worst_case_exactly_on_the_deadline_is_met(self):
        result = assess_expedited_transfer(MESSAGE, BLOCKING, RATE, 0.004, PEERS, BACKLOG)
        self.assertAlmostEqual(result["worst_case_latency_s"], result["deadline_s"], places=9)
        self.assertEqual(result["verdict"], MET)

    def test_without_precedence_there_is_no_expedited_service(self):
        result = assess_expedited_transfer(
            MESSAGE, BLOCKING, RATE, 1.0, PEERS, BACKLOG, precedence=False
        )
        self.assertEqual(result["verdict"], NOT_EXPEDITED)

    def test_a_met_deadline_does_not_excuse_missing_precedence(self):
        result = assess_expedited_transfer(
            MESSAGE, BLOCKING, RATE, 1.0, PEERS, BACKLOG, precedence=False
        )
        self.assertTrue(result["on_time"])
        self.assertNotEqual(result["verdict"], MET)

    def test_missing_precedence_is_named_in_the_findings(self):
        result = assess_expedited_transfer(
            MESSAGE, BLOCKING, RATE, 1.0, PEERS, BACKLOG, precedence=False
        )
        self.assertTrue(any("not stood aside" in f for f in result["findings"]))

    def test_a_missed_deadline_reports_both_remedies(self):
        result = assess_expedited_transfer(MESSAGE, BLOCKING, RATE, 0.001, PEERS, BACKLOG)
        self.assertTrue(any("link rate of at least" in f for f in result["findings"]))

    def test_margin_is_reported(self):
        result = assess_expedited_transfer(MESSAGE, BLOCKING, RATE, DEADLINE, PEERS, BACKLOG)
        self.assertAlmostEqual(result["margin_s"], 0.006, places=9)

    def test_the_three_time_components_add_to_the_worst_case(self):
        result = assess_expedited_transfer(MESSAGE, BLOCKING, RATE, DEADLINE, PEERS, BACKLOG)
        total = (
            result["blocking_time_s"] + result["interference_time_s"] + result["own_time_s"]
        )
        self.assertAlmostEqual(total, result["worst_case_latency_s"], places=9)

    def test_peer_traffic_is_carried_in_the_result(self):
        result = assess_expedited_transfer(MESSAGE, BLOCKING, RATE, DEADLINE, PEERS, BACKLOG)
        self.assertAlmostEqual(result["peer_bits"], 1000.0, places=9)

    def test_no_peers_and_no_blocking_leaves_only_the_message(self):
        result = assess_expedited_transfer(MESSAGE, 0.0, RATE, DEADLINE)
        self.assertAlmostEqual(result["worst_case_latency_s"], 0.001, places=9)

    def test_bad_rate_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_expedited_transfer(MESSAGE, BLOCKING, 0.0, DEADLINE)

    def test_bad_deadline_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_expedited_transfer(MESSAGE, BLOCKING, RATE, -1.0)

    def test_bad_peer_list_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_expedited_transfer(MESSAGE, BLOCKING, RATE, DEADLINE, ["500"])


if __name__ == "__main__":
    unittest.main()
