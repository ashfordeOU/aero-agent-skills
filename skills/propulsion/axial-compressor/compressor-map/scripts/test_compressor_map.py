#!/usr/bin/env python3
"""Gate 3 contract test: axial compressor operating map logic.

stdlib unittest, offline, deterministic. Exercises
scripts/compressor_map_logic.py against hand-computed analytic
values (SI units, standard-day correction with T_ref = 288.15 K,
P_ref = 101325 Pa):

  corrected_flow(50, 1.0, 1.0)  = 50*sqrt(1)/1        = 50.0 kg/s
  corrected_flow(60, 1.21, 0.9) = 60*sqrt(1.21)/0.9   = 73.3333 kg/s
  corrected_speed(15000, 1.0)   = 15000/sqrt(1)       = 15000.0 rpm
  corrected_speed(15000, 1.21)  = 15000/sqrt(1.21)    = 13636.3636 rpm
  surge_margin_flow(45, 50)     = (50-45)/50*100      = 10.0 %
  surge_margin_flow(48, 60)     = (60-48)/60*100      = 20.0 %
  operating_line_clearance(1.8, 2.0) = 0.2/1.8*100    = 11.1111 %
  operating_line_clearance(2.5, 2.8) = 0.3/2.5*100    = 12.0 %
  map_verdict(2.05, 30, 2.0)  -> pr >= surge_pr       = "on-surge-line"
  map_verdict(2.0, 30, 2.0)   -> pr >= surge_pr       = "on-surge-line"
  map_verdict(1.91, 30, 2.0)  -> gap 0.045 <= 0.05    = "approaching-surge"
  map_verdict(1.8, 30, 2.0)   -> gap 0.10 > 0.05      = "on-map"
  map_verdict(1.82, 30, 2.0, threshold=0.10)
                              -> gap 0.09 <= 0.10     = "approaching-surge"

Run: python3 scripts/test_compressor_map.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compressor_map_logic import (  # noqa: E402
    corrected_flow,
    corrected_speed,
    surge_margin_flow,
    operating_line_clearance,
    map_verdict,
    map_point,
)


class TestCompressorMap(unittest.TestCase):
    def test_corrected_flow_standard_day(self):
        """theta = delta = 1 means no correction: flow unchanged."""
        self.assertAlmostEqual(corrected_flow(50.0, 1.0, 1.0), 50.0, places=4)

    def test_corrected_flow_off_design(self):
        # 60*sqrt(1.21)/0.9 = 60*1.1/0.9 = 73.3333
        self.assertAlmostEqual(corrected_flow(60.0, 1.21, 0.9), 73.3333,
                               places=4)

    def test_corrected_speed_standard_day(self):
        self.assertAlmostEqual(corrected_speed(15000.0, 1.0), 15000.0,
                               places=4)

    def test_corrected_speed_off_design(self):
        # 15000/sqrt(1.21) = 15000/1.1 = 13636.3636
        self.assertAlmostEqual(corrected_speed(15000.0, 1.21), 13636.3636,
                               places=4)

    def test_surge_margin_flow_analytic(self):
        self.assertAlmostEqual(surge_margin_flow(45.0, 50.0), 10.0, places=4)
        self.assertAlmostEqual(surge_margin_flow(48.0, 60.0), 20.0, places=4)

    def test_operating_line_clearance_analytic(self):
        # (2.0-1.8)/1.8*100 = 11.1111; (2.8-2.5)/2.5*100 = 12.0
        self.assertAlmostEqual(operating_line_clearance(1.8, 2.0), 11.1111,
                               places=4)
        self.assertAlmostEqual(operating_line_clearance(2.5, 2.8), 12.0,
                               places=4)

    def test_map_verdict_on_surge_line(self):
        self.assertEqual(map_verdict(2.05, 30.0, 2.0), "on-surge-line")
        self.assertEqual(map_verdict(2.0, 30.0, 2.0), "on-surge-line")

    def test_map_verdict_approaching_surge(self):
        # gap (2.0-1.91)/2.0 = 0.045 is within the default 5% threshold
        self.assertEqual(map_verdict(1.91, 30.0, 2.0), "approaching-surge")

    def test_map_verdict_on_map(self):
        # gap (2.0-1.8)/2.0 = 0.10 exceeds the default 5% threshold
        self.assertEqual(map_verdict(1.8, 30.0, 2.0), "on-map")

    def test_map_verdict_custom_threshold(self):
        # gap (2.0-1.82)/2.0 = 0.09 is within the 10% threshold
        self.assertEqual(
            map_verdict(1.82, 30.0, 2.0, threshold=0.10),
            "approaching-surge",
        )

    def test_map_point_identification(self):
        pt = map_point(13636.3636, 73.3333)
        self.assertEqual(
            set(pt.keys()), {"corrected_speed", "corrected_flow"})
        self.assertAlmostEqual(pt["corrected_speed"], 13636.3636, places=4)
        self.assertAlmostEqual(pt["corrected_flow"], 73.3333, places=4)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            corrected_flow(0.0, 1.0, 1.0)
        with self.assertRaises(ValueError):
            corrected_flow(10.0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            corrected_flow(10.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            corrected_speed(0.0, 1.0)
        with self.assertRaises(ValueError):
            corrected_speed(15000.0, 0.0)
        with self.assertRaises(ValueError):
            surge_margin_flow(0.0, 50.0)
        with self.assertRaises(ValueError):
            surge_margin_flow(45.0, 0.0)
        with self.assertRaises(ValueError):
            operating_line_clearance(0.0, 2.0)
        with self.assertRaises(ValueError):
            operating_line_clearance(1.8, 0.0)
        with self.assertRaises(ValueError):
            map_verdict(1.0, 30.0, 1.0)
        with self.assertRaises(ValueError):
            map_verdict(1.8, 0.0, 2.0)
        with self.assertRaises(ValueError):
            map_verdict(1.8, 30.0, 2.0, threshold=0.0)
        with self.assertRaises(ValueError):
            map_verdict(1.8, 30.0, 2.0, threshold=1.0)
        with self.assertRaises(ValueError):
            map_point(0.0, 30.0)
        with self.assertRaises(ValueError):
            map_point(15000.0, 0.0)


if __name__ == "__main__":
    unittest.main()
