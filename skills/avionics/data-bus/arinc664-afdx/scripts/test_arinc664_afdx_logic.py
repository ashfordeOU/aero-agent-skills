#!/usr/bin/env python3
"""Gate 3 contract test: ARINC 664 Part 7 AFDX network sizing and timing.

Exercises scripts/arinc664_afdx_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the VL bandwidth anchor
(1518 bytes at BAG 4 ms -> 3.036 Mbps), the link utilization check
(30 VLs -> 0.9108, 33 VLs oversubscribed), the frame transmission time
anchors, the jitter slack verdicts, the end-to-end latency anchor, the
largest-BAG selection, and invalid inputs (illegal BAG, out-of-range
frame, oversubscribed set, non-positive budgets) all raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import arinc664_afdx_logic as afdx  # noqa: E402

LINK_RATE = 100_000_000.0


class BagAndFrameValidationTest(unittest.TestCase):
    def test_illegal_bag_raises(self):
        for bad in (0, 3, 5, 6, 256, -1, 1000):
            with self.assertRaises(ValueError):
                afdx.vl_bandwidth(bad, 1518)

    def test_non_integer_bag_raises(self):
        with self.assertRaises(ValueError):
            afdx.vl_bandwidth(4.0, 1518)
        with self.assertRaises(ValueError):
            afdx.vl_bandwidth("4", 1518)

    def test_frame_below_minimum_raises(self):
        for bad in (0, 1, 63, -64):
            with self.assertRaises(ValueError):
                afdx.vl_bandwidth(4, bad)

    def test_frame_above_maximum_raises(self):
        for bad in (1519, 2000, 9000):
            with self.assertRaises(ValueError):
                afdx.vl_bandwidth(4, bad)

    def test_non_integer_frame_raises(self):
        with self.assertRaises(ValueError):
            afdx.vl_bandwidth(4, 1518.0)
        with self.assertRaises(ValueError):
            afdx.vl_bandwidth(4, "1518")


class VlBandwidthTest(unittest.TestCase):
    def test_anchor_4ms_1518_bytes(self):
        self.assertEqual(afdx.vl_bandwidth(4, 1518), 3036000.0)

    def test_anchor_128ms_1518_bytes(self):
        self.assertEqual(afdx.vl_bandwidth(128, 1518), 94875.0)

    def test_1ms_bag_capacity(self):
        self.assertEqual(afdx.vl_bandwidth(1, 1518), 12144000.0)

    def test_8ms_bag(self):
        self.assertEqual(afdx.vl_bandwidth(8, 1518), 1518000.0)

    def test_64_byte_minimum_frame(self):
        self.assertEqual(afdx.vl_bandwidth(4, 64), 128000.0)

    def test_bag_boundaries(self):
        for bag in (1, 2, 4, 8, 16, 32, 64, 128):
            self.assertAlmostEqual(
                afdx.vl_bandwidth(bag, 1518),
                12144.0 / (bag / 1000.0),
                places=6,
            )


class LinkUtilizationTest(unittest.TestCase):
    def test_anchor_30_virtual_links(self):
        specs = [(4, 1518)] * 30
        self.assertAlmostEqual(afdx.link_utilization(specs), 0.9108, places=6)

    def test_oversubscribed_33_virtual_links_raises(self):
        specs = [(4, 1518)] * 33
        with self.assertRaises(ValueError):
            afdx.link_utilization(specs)

    def test_empty_set_zero_utilization(self):
        self.assertEqual(afdx.link_utilization([]), 0.0)

    def test_single_virtual_link(self):
        self.assertAlmostEqual(afdx.link_utilization([(128, 1518)]), 0.00094875, places=9)

    def test_mixed_bags_fit(self):
        specs = [(4, 1518)] * 10 + [(128, 1518)] * 10 + [(1, 64)] * 10
        total = 10 * 3036000.0 + 10 * 94875.0 + 10 * 512000.0
        self.assertAlmostEqual(afdx.link_utilization(specs), total / LINK_RATE, places=6)

    def test_non_positive_link_rate_raises(self):
        with self.assertRaises(ValueError):
            afdx.link_utilization([(4, 1518)], 0.0)
        with self.assertRaises(ValueError):
            afdx.link_utilization([(4, 1518)], -100.0)

    def test_malformed_spec_entry_raises(self):
        with self.assertRaises(ValueError):
            afdx.link_utilization([(4, 1518), 1518])

    def test_string_link_rate_raises(self):
        with self.assertRaises(ValueError):
            afdx.link_utilization([(4, 1518)], "100000000")


class TransmissionTimeTest(unittest.TestCase):
    def test_anchor_1518_bytes(self):
        self.assertAlmostEqual(afdx.transmission_time(1518), 1.2144e-4, places=10)

    def test_anchor_64_bytes(self):
        self.assertAlmostEqual(afdx.transmission_time(64), 5.12e-6, places=12)

    def test_128_bytes(self):
        self.assertAlmostEqual(afdx.transmission_time(128), 1.024e-5, places=12)

    def test_zero_link_rate_raises(self):
        with self.assertRaises(ValueError):
            afdx.transmission_time(1518, 0.0)

    def test_out_of_range_frame_raises(self):
        with self.assertRaises(ValueError):
            afdx.transmission_time(2000)


class JitterSlackTest(unittest.TestCase):
    def test_anchor_compliant(self):
        self.assertEqual(afdx.jitter_slack(420.0, 500.0), 80.0)

    def test_anchor_violation(self):
        self.assertEqual(afdx.jitter_slack(620.0, 500.0), -120.0)

    def test_at_budget_zero_slack(self):
        self.assertEqual(afdx.jitter_slack(500.0, 500.0), 0.0)

    def test_zero_measured_jitter(self):
        self.assertEqual(afdx.jitter_slack(0.0, 500.0), 500.0)

    def test_negative_measured_jitter_raises(self):
        with self.assertRaises(ValueError):
            afdx.jitter_slack(-1.0, 500.0)

    def test_non_positive_budget_raises(self):
        with self.assertRaises(ValueError):
            afdx.jitter_slack(100.0, 0.0)
        with self.assertRaises(ValueError):
            afdx.jitter_slack(100.0, -50.0)

    def test_non_numeric_inputs_raise(self):
        with self.assertRaises(ValueError):
            afdx.jitter_slack("420", 500.0)
        with self.assertRaises(ValueError):
            afdx.jitter_slack(420.0, "500")


class EndToEndLatencyTest(unittest.TestCase):
    def test_anchor_two_switches(self):
        self.assertAlmostEqual(
            afdx.end_to_end_latency_us(1518, 2, 150.0), 542.88, places=6
        )

    def test_single_switch_64_byte_frame(self):
        self.assertAlmostEqual(
            afdx.end_to_end_latency_us(64, 1, 100.0), 110.24, places=6
        )

    def test_no_switch_direct(self):
        self.assertAlmostEqual(
            afdx.end_to_end_latency_us(1518, 0, 0.0), 242.88, places=6
        )

    def test_latency_grows_with_switch_count(self):
        base = afdx.end_to_end_latency_us(1518, 1, 150.0)
        two = afdx.end_to_end_latency_us(1518, 2, 150.0)
        self.assertAlmostEqual(two - base, 150.0, places=6)

    def test_negative_switch_count_raises(self):
        with self.assertRaises(ValueError):
            afdx.end_to_end_latency_us(1518, -1, 150.0)

    def test_negative_switch_delay_raises(self):
        with self.assertRaises(ValueError):
            afdx.end_to_end_latency_us(1518, 2, -10.0)

    def test_out_of_range_frame_raises(self):
        with self.assertRaises(ValueError):
            afdx.end_to_end_latency_us(60, 2, 150.0)


class LargestBagTest(unittest.TestCase):
    def test_anchor_1_mbps(self):
        self.assertEqual(afdx.largest_bag_for_bandwidth(1000000.0, 1518), 8)

    def test_anchor_12_mbps(self):
        self.assertEqual(afdx.largest_bag_for_bandwidth(12000000.0, 1518), 1)

    def test_anchor_90_kbps(self):
        self.assertEqual(afdx.largest_bag_for_bandwidth(90000.0, 1518), 128)

    def test_exact_capacity_bag(self):
        # 1518 bytes at BAG 8 -> 1.518 Mbps exactly meets 1.518 Mbps.
        self.assertEqual(afdx.largest_bag_for_bandwidth(1518000.0, 1518), 8)

    def test_beyond_1ms_capacity_raises(self):
        with self.assertRaises(ValueError):
            afdx.largest_bag_for_bandwidth(13000000.0, 1518)

    def test_non_positive_bandwidth_raises(self):
        with self.assertRaises(ValueError):
            afdx.largest_bag_for_bandwidth(0.0, 1518)
        with self.assertRaises(ValueError):
            afdx.largest_bag_for_bandwidth(-500.0, 1518)

    def test_invalid_frame_raises(self):
        with self.assertRaises(ValueError):
            afdx.largest_bag_for_bandwidth(1000000.0, 60)

    def test_selected_bag_meets_requirement(self):
        for needed in (1000.0, 50000.0, 200000.0, 3000000.0, 12000000.0):
            bag = afdx.largest_bag_for_bandwidth(needed, 1518)
            self.assertGreaterEqual(afdx.vl_bandwidth(bag, 1518), needed)


class ConsistencyTest(unittest.TestCase):
    def test_bandwidth_scales_inversely_with_bag(self):
        rates = [afdx.vl_bandwidth(b, 1518) for b in (1, 2, 4, 8, 16, 32, 64, 128)]
        for hi, lo in zip(rates, rates[1:]):
            self.assertGreater(hi, lo)
            self.assertAlmostEqual(hi / 2.0, lo, places=6)

    def test_utilization_matches_sum_of_bandwidths(self):
        specs = [(4, 1518)] * 5 + [(128, 1518)] * 5
        total = 5 * afdx.vl_bandwidth(4, 1518) + 5 * afdx.vl_bandwidth(128, 1518)
        self.assertAlmostEqual(afdx.link_utilization(specs), total / LINK_RATE, places=9)

    def test_boolean_inputs_raise(self):
        with self.assertRaises(ValueError):
            afdx.vl_bandwidth(True, 1518)
        with self.assertRaises(ValueError):
            afdx.transmission_time(False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
