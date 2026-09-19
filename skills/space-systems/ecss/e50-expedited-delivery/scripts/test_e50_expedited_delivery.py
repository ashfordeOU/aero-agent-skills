"""Contract tests for the clause 5.6.14.3 expedited delivery logic."""

import unittest

from e50_expedited_delivery_logic import (
    MEETS_DEADLINE,
    MISSES_DEADLINE,
    POLICY_NONE,
    POLICY_NON_PREEMPTIVE,
    POLICY_PREEMPTIVE,
    assess_expedited_delivery,
    expedited_latency_s,
    expedited_share,
    latency_by_policy,
    least_policy_meeting_deadline,
    queued_bits,
    required_service_rate_bps,
    validate_bits,
    validate_count,
    validate_nonnegative_bits,
    validate_policy,
    validate_positive_time,
    validate_rate,
    validate_time,
)

RATE = 100000.0
URGENT = 1000.0
QUEUED = 20
QUEUED_UNIT = 4000.0
RESIDUAL = 3000.0


def design(**overrides):
    base = dict(
        policy=POLICY_NON_PREEMPTIVE,
        service_rate_bps=RATE,
        urgent_unit_bits=URGENT,
        queued_units=QUEUED,
        queued_unit_bits=QUEUED_UNIT,
        in_service_remaining_bits=RESIDUAL,
        deadline_s=0.1,
        expedited_load_bps=10000.0,
        normal_share_floor=0.1,
        preemption_switch_s=0.0,
    )
    base.update(overrides)
    return base


class ValidationTests(unittest.TestCase):
    def test_known_policy_accepted(self):
        self.assertEqual(validate_policy(POLICY_PREEMPTIVE), POLICY_PREEMPTIVE)

    def test_unknown_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy("round-robin")

    def test_zero_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(0.0)

    def test_zero_unit_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits(0.0)

    def test_zero_residual_accepted(self):
        self.assertAlmostEqual(validate_nonnegative_bits(0.0), 0.0, places=9)

    def test_negative_residual_rejected(self):
        with self.assertRaises(ValueError):
            validate_nonnegative_bits(-1.0)

    def test_empty_queue_accepted(self):
        self.assertEqual(validate_count(0, "queued_units"), 0)

    def test_negative_queue_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(-1, "queued_units")

    def test_float_queue_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(20.0, "queued_units")

    def test_negative_switch_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(-0.001)

    def test_zero_deadline_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive_time(0.0, "deadline_s")

    def test_boolean_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(True)


class QueueTests(unittest.TestCase):
    def test_queued_bits_is_the_count_times_the_size(self):
        self.assertAlmostEqual(queued_bits(20, 4000.0), 80000.0, places=9)

    def test_empty_queue_holds_nothing(self):
        self.assertAlmostEqual(queued_bits(0, 4000.0), 0.0, places=9)


class LatencyTests(unittest.TestCase):
    def test_no_class_waits_for_the_whole_queue(self):
        value = expedited_latency_s(POLICY_NONE, RATE, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL)
        self.assertAlmostEqual(value, (3000.0 + 80000.0 + 1000.0) / RATE, places=9)

    def test_non_preemptive_waits_only_for_the_unit_in_service(self):
        value = expedited_latency_s(
            POLICY_NON_PREEMPTIVE, RATE, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL
        )
        self.assertAlmostEqual(value, (3000.0 + 1000.0) / RATE, places=9)

    def test_preemptive_waits_only_for_its_own_unit(self):
        value = expedited_latency_s(
            POLICY_PREEMPTIVE, RATE, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL
        )
        self.assertAlmostEqual(value, URGENT / RATE, places=9)

    def test_preemption_switch_is_paid(self):
        with_switch = expedited_latency_s(
            POLICY_PREEMPTIVE, RATE, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL, 0.005
        )
        without = expedited_latency_s(
            POLICY_PREEMPTIVE, RATE, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL
        )
        self.assertAlmostEqual(with_switch - without, 0.005, places=9)

    def test_idle_link_makes_the_policies_agree(self):
        latencies = latency_by_policy(RATE, URGENT, 0, QUEUED_UNIT, 0.0)
        self.assertAlmostEqual(latencies[POLICY_NONE], latencies[POLICY_PREEMPTIVE], places=9)

    def test_policies_are_ordered_on_a_busy_link(self):
        latencies = latency_by_policy(RATE, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL)
        self.assertGreater(latencies[POLICY_NONE], latencies[POLICY_NON_PREEMPTIVE])
        self.assertGreater(latencies[POLICY_NON_PREEMPTIVE], latencies[POLICY_PREEMPTIVE])


class RemedyTests(unittest.TestCase):
    def test_required_rate_meets_the_deadline_under_the_same_policy(self):
        deadline = 0.02
        rate = required_service_rate_bps(
            POLICY_NON_PREEMPTIVE, deadline, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL
        )
        achieved = expedited_latency_s(
            POLICY_NON_PREEMPTIVE, rate, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL
        )
        self.assertAlmostEqual(achieved, deadline, places=9)

    def test_required_rate_is_higher_without_an_expedited_class(self):
        deadline = 0.05
        self.assertGreater(
            required_service_rate_bps(
                POLICY_NONE, deadline, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL
            ),
            required_service_rate_bps(
                POLICY_NON_PREEMPTIVE, deadline, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL
            ),
        )

    def test_switch_cost_past_the_deadline_admits_no_rate(self):
        self.assertIsNone(
            required_service_rate_bps(
                POLICY_PREEMPTIVE, 0.001, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL, 0.005
            )
        )

    def test_least_policy_prefers_the_least_intrusive(self):
        self.assertEqual(
            least_policy_meeting_deadline(1.0, RATE, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL),
            POLICY_NONE,
        )

    def test_least_policy_escalates_when_the_queue_is_too_long(self):
        self.assertEqual(
            least_policy_meeting_deadline(0.05, RATE, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL),
            POLICY_NON_PREEMPTIVE,
        )

    def test_least_policy_returns_none_when_no_policy_works(self):
        self.assertIsNone(
            least_policy_meeting_deadline(
                0.001, RATE, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL
            )
        )

    def test_share_is_the_load_over_the_rate(self):
        self.assertAlmostEqual(expedited_share(25000.0, RATE), 0.25, places=9)


class AssessTests(unittest.TestCase):
    def test_sound_design_meets_the_deadline(self):
        result = assess_expedited_delivery(**design())
        self.assertEqual(result["verdict"], MEETS_DEADLINE)
        self.assertEqual(result["findings"], [])

    def test_missed_deadline_is_reported(self):
        result = assess_expedited_delivery(**design(deadline_s=0.01))
        self.assertFalse(result["meets_deadline"])
        self.assertEqual(result["verdict"], MISSES_DEADLINE)

    def test_latency_exactly_at_the_deadline_is_accepted(self):
        exact = expedited_latency_s(
            POLICY_NON_PREEMPTIVE, RATE, URGENT, QUEUED, QUEUED_UNIT, RESIDUAL
        )
        result = assess_expedited_delivery(**design(deadline_s=exact))
        self.assertAlmostEqual(result["latency_s"], result["deadline_s"], places=12)
        self.assertTrue(result["meets_deadline"])

    def test_missing_expedited_class_is_a_finding_on_its_own(self):
        result = assess_expedited_delivery(**design(policy=POLICY_NONE, deadline_s=5.0))
        self.assertTrue(result["meets_deadline"])
        self.assertEqual(result["verdict"], MISSES_DEADLINE)
        self.assertTrue(any("no expedited class" in f for f in result["findings"]))

    def test_recommended_rate_clears_the_deadline_finding(self):
        result = assess_expedited_delivery(**design(deadline_s=0.01))
        fixed = assess_expedited_delivery(
            **design(deadline_s=0.01, service_rate_bps=result["required_service_rate_bps"])
        )
        self.assertTrue(fixed["meets_deadline"])

    def test_recommended_policy_clears_the_deadline_finding(self):
        result = assess_expedited_delivery(
            **design(policy=POLICY_NONE, deadline_s=0.05)
        )
        fixed = assess_expedited_delivery(
            **design(policy=result["least_policy_meeting_deadline"], deadline_s=0.05)
        )
        self.assertTrue(fixed["meets_deadline"])

    def test_both_remedies_are_named_in_the_finding(self):
        result = assess_expedited_delivery(**design(deadline_s=0.01))
        self.assertTrue(any("meets it at this rate" in f for f in result["findings"]))
        self.assertTrue(any("bit/s meets it under" in f for f in result["findings"]))

    def test_starving_the_normal_queue_is_reported(self):
        result = assess_expedited_delivery(**design(expedited_load_bps=99000.0))
        self.assertTrue(result["starves_normal_traffic"])
        self.assertTrue(any("grows without bound" in f for f in result["findings"]))

    def test_starvation_fails_the_verdict_even_on_a_met_deadline(self):
        result = assess_expedited_delivery(**design(expedited_load_bps=99000.0))
        self.assertTrue(result["meets_deadline"])
        self.assertEqual(result["verdict"], MISSES_DEADLINE)

    def test_normal_share_exactly_at_the_floor_is_accepted(self):
        result = assess_expedited_delivery(**design(expedited_load_bps=0.9 * RATE))
        self.assertAlmostEqual(result["normal_share"], result["normal_share_floor"], places=12)
        self.assertFalse(result["starves_normal_traffic"])

    def test_every_policy_latency_is_carried(self):
        result = assess_expedited_delivery(**design())
        self.assertEqual(
            sorted(result["latency_by_policy"]),
            sorted([POLICY_NONE, POLICY_NON_PREEMPTIVE, POLICY_PREEMPTIVE]),
        )

    def test_bad_floor_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_expedited_delivery(**design(normal_share_floor=1.0))

    def test_bad_policy_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_expedited_delivery(**design(policy="round-robin"))

    def test_bad_deadline_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_expedited_delivery(**design(deadline_s=0.0))


if __name__ == "__main__":
    unittest.main()
