#!/usr/bin/env python3
"""Gate 3 contract test: ARINC 653 IMA partitioning logic.

Exercises scripts/ima_partitioning_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - partition schedule
feasibility within the major frame, the partition configuration table
record, and sampling and queuing port latency bounds.

Hand-computed analytic references:
- MAF 40 ms with windows 10 ms and 30 ms at period 40 ms each: frame
  load 10 + 30 = 40 ms exactly fills the frame, utilization 1.0, slack
  0, feasible.
- MAF 40 ms with windows 10, 20, and 15 ms at period 40 ms: load
  45 ms, utilization 1.125, over-subscribed, infeasible.
- MAF 40 ms with a 10 ms window at period 20 ms (runs twice per frame,
  load 20 ms) plus a 15 ms window at period 40 ms: load 35 ms,
  utilization 0.875, slack 5 ms, feasible.
- MAF 40 ms with a 30 ms window at period 20 ms: the duration exceeds
  the period slot, violation.
- MAF 40 ms with a 10 ms window at period 25 ms: 40 % 25 != 0, the
  period does not divide the major frame, violation.
- Wire transmission: 100 bytes at 100 Mbps serializes in
  800 / 1e8 s = 8e-6 s = 0.008 ms.
- Sampling port: period 10 ms, 100 bytes at 100 Mbps gives
  10 + 0.008 = 10.008 ms worst-case latency.
- Queuing port: depth 4, period 10 ms, 100 bytes at 100 Mbps gives
  4 x 10 + 0.008 = 40.008 ms; depth 1 gives 10.008 ms.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ima_partitioning_logic as ima  # noqa: E402

BPS = 100e6  # 100 Mbps backplane bit rate


class ScheduleFeasibilityTest(unittest.TestCase):
    def test_exact_fill_frame_is_feasible(self):
        # MAF 40 ms, windows 10 and 30 ms at period 40 ms: load 40 ms
        # exactly fills the frame, utilization 1.0, slack 0.
        r = ima.schedule_feasibility(40, [("nav", 10, 40), ("display", 30, 40)])
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(r["frame_load_ms"], 40.0, places=9)
        self.assertAlmostEqual(r["utilization"], 1.0, places=9)
        self.assertAlmostEqual(r["slack_ms"], 0.0, places=9)
        self.assertEqual(r["violations"], [])

    def test_over_subscribed_frame_is_infeasible(self):
        # 10 + 20 + 15 = 45 ms > MAF 40 ms; utilization 1.125.
        r = ima.schedule_feasibility(
            40, [("nav", 10, 40), ("guidance", 20, 40), ("display", 15, 40)]
        )
        self.assertFalse(r["ok"])
        self.assertAlmostEqual(r["frame_load_ms"], 45.0, places=9)
        self.assertAlmostEqual(r["utilization"], 1.125, places=9)
        self.assertTrue(any("exceeds the major frame" in v for v in r["violations"]))

    def test_sub_period_partition_runs_twice_per_frame(self):
        # 10 ms at period 20 ms runs 40 / 20 = 2 windows (20 ms) plus
        # 15 ms at period 40 ms: load 35 ms, utilization 0.875, slack 5.
        r = ima.schedule_feasibility(40, [("nav", 10, 20), ("display", 15, 40)])
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(r["frame_load_ms"], 35.0, places=9)
        self.assertAlmostEqual(r["utilization"], 0.875, places=9)
        self.assertAlmostEqual(r["slack_ms"], 5.0, places=9)

    def test_duration_exceeding_period_slot_is_violation(self):
        # 30 ms window at period 20 ms cannot finish before its next
        # slot starts.
        r = ima.schedule_feasibility(40, [("nav", 30, 20)])
        self.assertFalse(r["ok"])
        self.assertTrue(any("exceeds its period slot" in v for v in r["violations"]))

    def test_period_not_dividing_major_frame_is_violation(self):
        # 40 % 25 != 0: the cyclic schedule cannot repeat evenly.
        r = ima.schedule_feasibility(40, [("nav", 10, 25)])
        self.assertFalse(r["ok"])
        self.assertTrue(
            any("does not divide the major frame" in v for v in r["violations"])
        )

    def test_validation_raises(self):
        with self.assertRaises(ValueError):
            ima.schedule_feasibility(-1, [("nav", 10, 40)])
        with self.assertRaises(ValueError):
            ima.schedule_feasibility(40, [("nav", 10, 0)])
        with self.assertRaises(ValueError):
            ima.schedule_feasibility(40, [("nav", 0, 40)])
        with self.assertRaises(ValueError):
            ima.frame_load_ms(40, [("nav", 10, 0)])


class PartitionScheduleTest(unittest.TestCase):
    def test_class_record_matches_feasibility(self):
        s = ima.PartitionSchedule(40, [("nav", 10, 20), ("display", 15, 40)])
        self.assertTrue(s.feasible)
        self.assertAlmostEqual(s.frame_load_ms, 35.0, places=9)
        self.assertAlmostEqual(s.utilization, 0.875, places=9)
        self.assertAlmostEqual(s.slack_ms, 5.0, places=9)
        self.assertEqual(s.maf_ms, 40)
        self.assertEqual(s.partitions, [("nav", 10, 20), ("display", 15, 40)])
        self.assertEqual(s.violations, [])

    def test_as_dict_keys(self):
        s = ima.PartitionSchedule(40, [("nav", 10, 20), ("display", 15, 40)])
        d = s.as_dict()
        self.assertEqual(
            set(d),
            {"maf_ms", "utilization", "frame_load_ms", "slack_ms",
             "feasible", "violations"},
        )
        self.assertTrue(d["feasible"])


class SamplingPortLatencyTest(unittest.TestCase):
    def test_known_latency_value(self):
        # 100 bytes at 100 Mbps = 0.008 ms on the wire; period 10 ms
        # gives 10.008 ms worst-case latency.
        self.assertAlmostEqual(
            ima.sampling_port_latency_ms(10, 100, BPS), 10.008, places=6
        )

    def test_transmission_time_known_value(self):
        self.assertAlmostEqual(ima.transmission_time_ms(100, BPS), 0.008, places=9)
        # 1518 bytes at 100 Mbps serializes in 0.12144 ms.
        self.assertAlmostEqual(
            ima.transmission_time_ms(1518, BPS), 0.12144, places=9
        )

    def test_message_over_capacity_raises(self):
        with self.assertRaises(ValueError):
            ima.sampling_port_latency_ms(10, 200, BPS, port_message_size=100)
        # At exactly the capacity the port accepts the message.
        self.assertAlmostEqual(
            ima.sampling_port_latency_ms(10, 100, BPS, port_message_size=100),
            10.008,
            places=6,
        )

    def test_validation_raises(self):
        with self.assertRaises(ValueError):
            ima.sampling_port_latency_ms(0, 100, BPS)
        with self.assertRaises(ValueError):
            ima.sampling_port_latency_ms(10, -1, BPS)
        with self.assertRaises(ValueError):
            ima.sampling_port_latency_ms(10, 100, 0)


class QueuingPortLatencyTest(unittest.TestCase):
    def test_known_latency_values(self):
        # Depth 4 at period 10 ms: 4 x 10 + 0.008 = 40.008 ms; depth 1
        # matches the sampling bound 10.008 ms.
        self.assertAlmostEqual(
            ima.queuing_port_latency_ms(10, 100, BPS, 4), 40.008, places=6
        )
        self.assertAlmostEqual(
            ima.queuing_port_latency_ms(10, 100, BPS, 1), 10.008, places=6
        )

    def test_message_over_capacity_raises(self):
        with self.assertRaises(ValueError):
            ima.queuing_port_latency_ms(10, 200, BPS, 4, port_message_size=100)

    def test_validation_raises(self):
        with self.assertRaises(ValueError):
            ima.queuing_port_latency_ms(10, 100, BPS, 0)
        with self.assertRaises(ValueError):
            ima.queuing_port_latency_ms(0, 100, BPS, 4)


if __name__ == "__main__":
    unittest.main()
