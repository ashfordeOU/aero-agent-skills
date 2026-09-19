"""Contract tests for the clause 5.6.9 mixed isochronous and asynchronous logic."""

import unittest

from e50_mixed_isochronous_and_asynchronous_traffic_logic import (
    ASYNC_STARVED,
    BOTH_SERVED,
    CADENCE_LOST,
    assess_mixed_traffic,
    async_wait_s,
    blocking_delay_s,
    isochronous_load_bps,
    max_async_unit_bits,
    normalize_flows,
    required_link_rate_bps,
    reserved_slot_fraction,
    spare_capacity_bps,
    validate_bits,
    validate_period,
    validate_positive_rate,
    validate_rate,
    worst_case_jitter_s,
)

FLOWS = [
    ("attitude-cadence", 0.1, 8000.0),
    ("star-tracker-cadence", 0.5, 20000.0),
]
LINK = 1000000.0
UNIT = 8000.0
BUDGET = 0.02


class ValidationTests(unittest.TestCase):
    def test_zero_rate_accepted(self):
        self.assertAlmostEqual(validate_rate(0), 0.0, places=9)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(-1.0)

    def test_boolean_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(True)

    def test_zero_link_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive_rate(0.0)

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_period(0.0)

    def test_infinite_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_period(float("inf"))

    def test_negative_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits(-8.0)

    def test_empty_flow_list_rejected(self):
        with self.assertRaises(ValueError):
            normalize_flows([])

    def test_duplicate_flow_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_flows([("a", 1.0, 10.0), ("a", 2.0, 10.0)])

    def test_mapping_flow_entries_accepted(self):
        mapped = [{"name": "hk", "period_s": 1.0, "frame_bits": 1000.0}]
        self.assertAlmostEqual(isochronous_load_bps(mapped), 1000.0, places=9)

    def test_short_tuple_flow_rejected(self):
        with self.assertRaises(ValueError):
            normalize_flows([("a", 1.0)])


class ReservationTests(unittest.TestCase):
    def test_periodic_load_is_the_sum_of_rates(self):
        self.assertAlmostEqual(isochronous_load_bps(FLOWS), 120000.0, places=9)

    def test_reserved_fraction_is_load_over_link(self):
        self.assertAlmostEqual(reserved_slot_fraction(FLOWS, LINK), 0.12, places=9)

    def test_spare_capacity_is_what_is_left(self):
        self.assertAlmostEqual(spare_capacity_bps(FLOWS, LINK), 880000.0, places=9)

    def test_oversubscribed_reservation_leaves_nothing(self):
        self.assertAlmostEqual(spare_capacity_bps(FLOWS, 100000.0), 0.0, places=9)


class BlockingTests(unittest.TestCase):
    def test_non_preemptible_unit_blocks_for_its_serialisation_time(self):
        self.assertAlmostEqual(blocking_delay_s(UNIT, LINK), 0.008, places=9)

    def test_preemptible_link_blocks_for_nothing(self):
        self.assertAlmostEqual(blocking_delay_s(UNIT, LINK, preemptible=True), 0.0, places=9)

    def test_jitter_equals_the_blocking_interval(self):
        self.assertAlmostEqual(
            worst_case_jitter_s(UNIT, LINK), blocking_delay_s(UNIT, LINK), places=9
        )

    def test_largest_unit_the_budget_allows(self):
        self.assertAlmostEqual(max_async_unit_bits(LINK, BUDGET), 20000.0, places=9)

    def test_the_largest_allowed_unit_exactly_meets_the_budget(self):
        unit = max_async_unit_bits(LINK, BUDGET)
        self.assertAlmostEqual(blocking_delay_s(unit, LINK), BUDGET, places=9)


class AsyncServiceTests(unittest.TestCase):
    def test_best_effort_unit_waits_on_the_spare_capacity(self):
        self.assertAlmostEqual(async_wait_s(880000.0, FLOWS, LINK), 1.0, places=9)

    def test_no_spare_capacity_never_completes(self):
        self.assertIsNone(async_wait_s(1000.0, FLOWS, 120000.0))

    def test_empty_unit_waits_no_time(self):
        self.assertAlmostEqual(async_wait_s(0.0, FLOWS, LINK), 0.0, places=9)

    def test_required_rate_covers_both_loads(self):
        self.assertAlmostEqual(required_link_rate_bps(FLOWS, 300000.0), 420000.0, places=9)

    def test_required_rate_respects_the_jitter_budget(self):
        self.assertAlmostEqual(
            required_link_rate_bps(FLOWS, 100000.0, 0.002, 8000.0), 4000000.0, places=9
        )


class AssessTests(unittest.TestCase):
    def test_link_serving_both_passes(self):
        result = assess_mixed_traffic(FLOWS, LINK, 300000.0, UNIT, BUDGET)
        self.assertEqual(result["verdict"], BOTH_SERVED)
        self.assertTrue(result["cadence_held"])
        self.assertTrue(result["async_served"])

    def test_oversized_unit_loses_the_cadence(self):
        result = assess_mixed_traffic(FLOWS, LINK, 100000.0, 40000.0, BUDGET)
        self.assertEqual(result["verdict"], CADENCE_LOST)
        self.assertFalse(result["cadence_held"])

    def test_preemption_restores_the_cadence(self):
        result = assess_mixed_traffic(FLOWS, LINK, 100000.0, 40000.0, BUDGET, preemptible=True)
        self.assertEqual(result["verdict"], BOTH_SERVED)

    def test_unit_exactly_on_the_jitter_budget_holds_the_cadence(self):
        unit = max_async_unit_bits(LINK, BUDGET)
        result = assess_mixed_traffic(FLOWS, LINK, 100000.0, unit, BUDGET)
        self.assertAlmostEqual(result["worst_case_jitter_s"], BUDGET, places=9)
        self.assertTrue(result["cadence_held"])

    def test_best_effort_load_beyond_the_spare_is_starved(self):
        result = assess_mixed_traffic(FLOWS, LINK, 950000.0, UNIT, BUDGET)
        self.assertEqual(result["verdict"], ASYNC_STARVED)
        self.assertFalse(result["async_served"])

    def test_best_effort_load_exactly_on_the_spare_is_served(self):
        result = assess_mixed_traffic(FLOWS, LINK, 880000.0, UNIT, BUDGET)
        self.assertAlmostEqual(result["async_offered_bps"], result["spare_bps"], places=9)
        self.assertEqual(result["verdict"], BOTH_SERVED)

    def test_reservation_beyond_the_link_is_reported(self):
        result = assess_mixed_traffic(FLOWS, 100000.0, 1000.0, 100.0, BUDGET)
        self.assertEqual(result["verdict"], CADENCE_LOST)
        self.assertTrue(any("cannot be met at all" in f for f in result["findings"]))

    def test_cadence_loss_names_the_segment_size(self):
        result = assess_mixed_traffic(FLOWS, LINK, 100000.0, 40000.0, BUDGET)
        self.assertTrue(any("segment it below" in f for f in result["findings"]))

    def test_starvation_is_reported_with_both_numbers(self):
        result = assess_mixed_traffic(FLOWS, LINK, 950000.0, UNIT, BUDGET)
        self.assertTrue(any("exceeds the" in f for f in result["findings"]))

    def test_healthy_link_reports_no_findings(self):
        self.assertEqual(assess_mixed_traffic(FLOWS, LINK, 300000.0, UNIT, BUDGET)["findings"], [])

    def test_per_flow_rates_are_carried_in_the_result(self):
        result = assess_mixed_traffic(FLOWS, LINK, 300000.0, UNIT, BUDGET)
        self.assertAlmostEqual(result["flows"][0]["rate_bps"], 80000.0, places=9)

    def test_stated_required_rate_actually_serves_both(self):
        result = assess_mixed_traffic(FLOWS, LINK, 950000.0, UNIT, BUDGET)
        fixed = assess_mixed_traffic(
            FLOWS, result["required_link_bps"], 950000.0, UNIT, BUDGET
        )
        self.assertEqual(fixed["verdict"], BOTH_SERVED)

    def test_stated_max_unit_actually_holds_the_cadence(self):
        result = assess_mixed_traffic(FLOWS, LINK, 100000.0, 40000.0, BUDGET)
        fixed = assess_mixed_traffic(
            FLOWS, LINK, 100000.0, result["max_async_unit_bits"], BUDGET
        )
        self.assertTrue(fixed["cadence_held"])

    def test_zero_link_rate_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_mixed_traffic(FLOWS, 0.0, 100.0, UNIT, BUDGET)

    def test_zero_jitter_budget_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_mixed_traffic(FLOWS, LINK, 100.0, UNIT, 0.0)


if __name__ == "__main__":
    unittest.main()
