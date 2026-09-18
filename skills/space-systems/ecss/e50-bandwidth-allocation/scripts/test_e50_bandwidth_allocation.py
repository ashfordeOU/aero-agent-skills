"""Contract tests for the clause 5.3.1 bandwidth allocation logic."""

import unittest

from e50_bandwidth_allocation_logic import (
    MARGIN_SHORT,
    OVERSUBSCRIBED,
    WITHIN_CAPACITY,
    allocate_bandwidth,
    flow_allocation,
    normalize_flow,
    required_capacity,
    scale_to_capacity,
    validate_margin_fraction,
    validate_overhead_factor,
    validate_rate,
)

FLOWS = [
    {"name": "payload telemetry", "rate_bps": 400000.0, "overhead_factor": 1.1},
    {"name": "housekeeping", "rate_bps": 50000.0, "overhead_factor": 1.2},
    {"name": "file downlink", "rate_bps": 200000.0},
]


class RateValidationTests(unittest.TestCase):
    def test_positive_rate_accepted(self):
        self.assertAlmostEqual(validate_rate(1000), 1000.0, places=9)

    def test_zero_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(0)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(-1.0)

    def test_boolean_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(True)

    def test_text_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate("1000")

    def test_infinite_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(float("inf"))


class FactorValidationTests(unittest.TestCase):
    def test_unit_overhead_accepted(self):
        self.assertAlmostEqual(validate_overhead_factor(1.0), 1.0, places=9)

    def test_overhead_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_overhead_factor(0.95)

    def test_zero_margin_accepted(self):
        self.assertAlmostEqual(validate_margin_fraction(0.0), 0.0, places=9)

    def test_margin_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_margin_fraction(1.0)

    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_margin_fraction(-0.01)


class FlowAllocationTests(unittest.TestCase):
    def test_allocation_applies_the_overhead(self):
        self.assertAlmostEqual(flow_allocation(100000.0, 1.25), 125000.0, places=9)

    def test_unit_overhead_leaves_the_rate_alone(self):
        self.assertAlmostEqual(flow_allocation(100000.0), 100000.0, places=9)

    def test_flow_normalisation_defaults_the_overhead(self):
        self.assertAlmostEqual(normalize_flow(FLOWS[2])["overhead_factor"], 1.0, places=9)

    def test_flow_without_a_rate_rejected(self):
        with self.assertRaises(ValueError):
            normalize_flow({"name": "a"})

    def test_flow_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_flow({"rate_bps": 100.0})

    def test_non_mapping_flow_rejected(self):
        with self.assertRaises(ValueError):
            normalize_flow("payload telemetry")


class AllocateTests(unittest.TestCase):
    def test_total_is_the_sum_of_the_flow_allocations(self):
        result = allocate_bandwidth(FLOWS, 1000000.0)
        self.assertAlmostEqual(result["total_allocated_bps"], 700000.0, places=9)

    def test_each_flow_is_reported_with_its_allocation(self):
        result = allocate_bandwidth(FLOWS, 1000000.0)
        self.assertEqual(len(result["allocations"]), 3)
        self.assertAlmostEqual(result["allocations"][0]["allocated_bps"], 440000.0, places=9)

    def test_share_of_capacity_is_reported(self):
        result = allocate_bandwidth(FLOWS, 1000000.0)
        self.assertAlmostEqual(result["allocations"][1]["share_of_capacity"], 0.06, places=9)

    def test_comfortable_link_is_within_capacity(self):
        result = allocate_bandwidth(FLOWS, 1000000.0, margin_fraction=0.2)
        self.assertEqual(result["verdict"], WITHIN_CAPACITY)
        self.assertTrue(result["feasible"])

    def test_exactly_on_the_usable_bound_is_feasible(self):
        result = allocate_bandwidth(FLOWS, 875000.0, margin_fraction=0.2)
        self.assertAlmostEqual(result["usable_bps"], 700000.0, places=9)
        self.assertTrue(result["feasible"])
        self.assertEqual(result["verdict"], WITHIN_CAPACITY)

    def test_margin_eaten_but_link_fits(self):
        result = allocate_bandwidth(FLOWS, 800000.0, margin_fraction=0.2)
        self.assertEqual(result["verdict"], MARGIN_SHORT)
        self.assertFalse(result["feasible"])

    def test_margin_short_finding_names_the_missing_headroom(self):
        result = allocate_bandwidth(FLOWS, 800000.0, margin_fraction=0.2)
        self.assertTrue(any("headroom is missing" in f for f in result["findings"]))

    def test_oversubscribed_link_is_reported(self):
        result = allocate_bandwidth(FLOWS, 500000.0)
        self.assertEqual(result["verdict"], OVERSUBSCRIBED)
        self.assertTrue(any("oversubscribed" in f for f in result["findings"]))

    def test_shortfall_is_the_gap_to_usable_capacity(self):
        result = allocate_bandwidth(FLOWS, 800000.0, margin_fraction=0.2)
        self.assertAlmostEqual(result["shortfall_bps"], 60000.0, places=9)

    def test_feasible_link_reports_no_shortfall(self):
        result = allocate_bandwidth(FLOWS, 1000000.0)
        self.assertAlmostEqual(result["shortfall_bps"], 0.0, places=9)

    def test_achieved_margin_is_reported(self):
        result = allocate_bandwidth(FLOWS, 1000000.0)
        self.assertAlmostEqual(result["achieved_margin_fraction"], 0.3, places=9)

    def test_duplicate_flow_name_rejected(self):
        with self.assertRaises(ValueError):
            allocate_bandwidth(FLOWS + [FLOWS[0]], 1000000.0)

    def test_empty_flow_set_rejected(self):
        with self.assertRaises(ValueError):
            allocate_bandwidth([], 1000000.0)

    def test_non_list_flow_set_rejected(self):
        with self.assertRaises(ValueError):
            allocate_bandwidth({"name": "a", "rate_bps": 1.0}, 1000000.0)


class RequiredCapacityTests(unittest.TestCase):
    def test_without_margin_it_is_the_total(self):
        self.assertAlmostEqual(required_capacity(FLOWS), 700000.0, places=9)

    def test_margin_inflates_the_requirement(self):
        self.assertAlmostEqual(required_capacity(FLOWS, 0.2), 875000.0, places=9)

    def test_the_required_capacity_is_itself_feasible(self):
        needed = required_capacity(FLOWS, 0.2)
        self.assertTrue(allocate_bandwidth(FLOWS, needed, 0.2)["feasible"])


class ScaleTests(unittest.TestCase):
    def test_feasible_set_is_not_scaled(self):
        result = scale_to_capacity(FLOWS, 1000000.0)
        self.assertAlmostEqual(result["scale_factor"], 1.0, places=9)
        self.assertTrue(result["feasible_as_declared"])

    def test_oversubscribed_set_is_cut_proportionally(self):
        result = scale_to_capacity(FLOWS, 350000.0)
        self.assertAlmostEqual(result["scale_factor"], 0.5, places=9)
        self.assertAlmostEqual(result["allocations"][0]["allocated_bps"], 220000.0, places=9)

    def test_scaled_set_fits_the_usable_capacity(self):
        result = scale_to_capacity(FLOWS, 350000.0)
        total = sum(item["allocated_bps"] for item in result["allocations"])
        self.assertAlmostEqual(total, 350000.0, places=9)

    def test_scaling_preserves_the_relative_sizing(self):
        result = scale_to_capacity(FLOWS, 350000.0)
        ratio = result["allocations"][0]["allocated_bps"] / result["allocations"][1]["allocated_bps"]
        self.assertAlmostEqual(ratio, 440000.0 / 60000.0, places=9)


if __name__ == "__main__":
    unittest.main()
