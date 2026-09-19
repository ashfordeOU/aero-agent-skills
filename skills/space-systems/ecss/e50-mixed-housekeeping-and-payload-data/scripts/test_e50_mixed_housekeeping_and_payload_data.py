"""Contract tests for the clause 5.6.10 housekeeping and payload sharing logic."""

import unittest

from e50_mixed_housekeeping_and_payload_data_logic import (
    BOTH_SERVED,
    CADENCE_LATE,
    PAYLOAD_SHORTFALL,
    assess_mixed_downlink,
    housekeeping_latency_s,
    housekeeping_rate_bps,
    housekeeping_share,
    max_payload_unit_bits,
    payload_capacity_bps,
    payload_unit_blocking_s,
    payload_volume_bits,
    required_link_rate_bps,
    validate_bits,
    validate_period,
    validate_positive_rate,
    validate_rate,
)

HK_FRAME = 4000.0
HK_PERIOD = 1.0
LINK = 1000000.0
UNIT = 16000.0
BUDGET = 0.05


class ValidationTests(unittest.TestCase):
    def test_zero_rate_accepted(self):
        self.assertAlmostEqual(validate_rate(0), 0.0, places=9)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(-1.0)

    def test_boolean_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits(True)

    def test_text_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits("4000")

    def test_nan_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(float("nan"))

    def test_zero_link_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive_rate(0.0)

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_period(0.0)

    def test_negative_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_period(-1.0)


class ReservationTests(unittest.TestCase):
    def test_housekeeping_rate_is_frame_over_cadence(self):
        self.assertAlmostEqual(housekeeping_rate_bps(HK_FRAME, HK_PERIOD), 4000.0, places=9)

    def test_faster_cadence_costs_proportionally_more(self):
        self.assertAlmostEqual(housekeeping_rate_bps(HK_FRAME, 0.25), 16000.0, places=9)

    def test_housekeeping_share_of_the_link(self):
        self.assertAlmostEqual(housekeeping_share(HK_FRAME, HK_PERIOD, LINK), 0.004, places=9)

    def test_payload_capacity_is_the_remainder(self):
        self.assertAlmostEqual(
            payload_capacity_bps(HK_FRAME, HK_PERIOD, LINK), 996000.0, places=9
        )

    def test_oversubscribed_cadence_leaves_no_payload_capacity(self):
        self.assertAlmostEqual(payload_capacity_bps(HK_FRAME, 0.001, LINK), 0.0, places=9)

    def test_payload_volume_over_a_contact(self):
        self.assertAlmostEqual(
            payload_volume_bits(HK_FRAME, HK_PERIOD, LINK, 600.0), 597600000.0, places=9
        )

    def test_zero_contact_length_rejected(self):
        with self.assertRaises(ValueError):
            payload_volume_bits(HK_FRAME, HK_PERIOD, LINK, 0.0)


class LatencyTests(unittest.TestCase):
    def test_non_preemptible_payload_unit_blocks_fully(self):
        self.assertAlmostEqual(payload_unit_blocking_s(UNIT, LINK), 0.016, places=9)

    def test_preemptible_link_blocks_for_nothing(self):
        self.assertAlmostEqual(payload_unit_blocking_s(UNIT, LINK, preemptible=True), 0.0, places=9)

    def test_latency_adds_the_housekeeping_serialisation(self):
        self.assertAlmostEqual(housekeeping_latency_s(HK_FRAME, UNIT, LINK), 0.020, places=9)

    def test_preemption_leaves_only_the_housekeeping_serialisation(self):
        self.assertAlmostEqual(
            housekeeping_latency_s(HK_FRAME, UNIT, LINK, preemptible=True), 0.004, places=9
        )

    def test_largest_payload_unit_the_budget_allows(self):
        self.assertAlmostEqual(max_payload_unit_bits(HK_FRAME, LINK, BUDGET), 46000.0, places=9)

    def test_the_largest_allowed_unit_lands_exactly_on_the_budget(self):
        unit = max_payload_unit_bits(HK_FRAME, LINK, BUDGET)
        self.assertAlmostEqual(housekeeping_latency_s(HK_FRAME, unit, LINK), BUDGET, places=9)

    def test_frame_longer_than_the_budget_allows_no_unit(self):
        self.assertAlmostEqual(max_payload_unit_bits(HK_FRAME, LINK, 0.001), 0.0, places=9)


class RequiredRateTests(unittest.TestCase):
    def test_required_rate_covers_both_loads(self):
        self.assertAlmostEqual(
            required_link_rate_bps(HK_FRAME, HK_PERIOD, 500000.0), 504000.0, places=9
        )

    def test_required_rate_respects_the_latency_budget(self):
        self.assertAlmostEqual(
            required_link_rate_bps(HK_FRAME, HK_PERIOD, 100000.0, 16000.0, 0.002),
            10000000.0,
            places=9,
        )


class AssessTests(unittest.TestCase):
    def test_downlink_serving_both_passes(self):
        result = assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 500000.0, UNIT, BUDGET)
        self.assertEqual(result["verdict"], BOTH_SERVED)
        self.assertTrue(result["cadence_ok"])
        self.assertTrue(result["payload_ok"])

    def test_oversized_payload_unit_makes_housekeeping_late(self):
        result = assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 100000.0, 200000.0, BUDGET)
        self.assertEqual(result["verdict"], CADENCE_LATE)
        self.assertFalse(result["cadence_ok"])

    def test_preemption_restores_the_cadence(self):
        result = assess_mixed_downlink(
            HK_FRAME, HK_PERIOD, LINK, 100000.0, 200000.0, BUDGET, preemptible=True
        )
        self.assertEqual(result["verdict"], BOTH_SERVED)

    def test_unit_exactly_on_the_latency_budget_is_accepted(self):
        unit = max_payload_unit_bits(HK_FRAME, LINK, BUDGET)
        result = assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 100000.0, unit, BUDGET)
        self.assertAlmostEqual(result["hk_latency_s"], BUDGET, places=9)
        self.assertTrue(result["cadence_ok"])

    def test_payload_beyond_the_remaining_capacity_is_short(self):
        result = assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 999000.0, UNIT, BUDGET)
        self.assertEqual(result["verdict"], PAYLOAD_SHORTFALL)
        self.assertFalse(result["payload_ok"])

    def test_payload_exactly_on_the_remaining_capacity_is_served(self):
        result = assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 996000.0, UNIT, BUDGET)
        self.assertAlmostEqual(
            result["payload_offered_bps"], result["payload_capacity_bps"], places=9
        )
        self.assertEqual(result["verdict"], BOTH_SERVED)

    def test_cadence_that_does_not_fit_the_link_is_reported(self):
        result = assess_mixed_downlink(HK_FRAME, 0.001, LINK, 1000.0, 100.0, BUDGET)
        self.assertEqual(result["verdict"], CADENCE_LATE)
        self.assertTrue(any("does not fit" in f for f in result["findings"]))

    def test_late_cadence_names_the_unit_cap(self):
        result = assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 100000.0, 200000.0, BUDGET)
        self.assertTrue(any("cap the payload" in f for f in result["findings"]))

    def test_frame_alone_past_the_budget_says_segmenting_cannot_help(self):
        result = assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 1000.0, 100.0, 0.001)
        self.assertTrue(any("cannot recover it" in f for f in result["findings"]))

    def test_payload_shortfall_is_reported_with_both_numbers(self):
        result = assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 999000.0, UNIT, BUDGET)
        self.assertTrue(any("bit/s left after the cadence" in f for f in result["findings"]))

    def test_healthy_downlink_reports_no_findings(self):
        result = assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 500000.0, UNIT, BUDGET)
        self.assertEqual(result["findings"], [])

    def test_housekeeping_share_is_carried_in_the_result(self):
        result = assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 500000.0, UNIT, BUDGET)
        self.assertAlmostEqual(result["hk_share"], 0.004, places=9)

    def test_stated_unit_cap_actually_meets_the_cadence(self):
        result = assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 100000.0, 200000.0, BUDGET)
        fixed = assess_mixed_downlink(
            HK_FRAME, HK_PERIOD, LINK, 100000.0, result["max_payload_unit_bits"], BUDGET
        )
        self.assertTrue(fixed["cadence_ok"])

    def test_stated_required_rate_actually_serves_both(self):
        result = assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 999000.0, UNIT, BUDGET)
        fixed = assess_mixed_downlink(
            HK_FRAME, HK_PERIOD, result["required_link_bps"], 999000.0, UNIT, BUDGET
        )
        self.assertEqual(fixed["verdict"], BOTH_SERVED)

    def test_zero_cadence_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_mixed_downlink(HK_FRAME, 0.0, LINK, 1000.0, UNIT, BUDGET)

    def test_negative_payload_unit_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_mixed_downlink(HK_FRAME, HK_PERIOD, LINK, 1000.0, -1.0, BUDGET)


if __name__ == "__main__":
    unittest.main()
