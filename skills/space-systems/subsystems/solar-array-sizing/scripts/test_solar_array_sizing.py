#!/usr/bin/env python3
"""Gate 3 contract test for space-systems/subsystems/solar-array-sizing.

Stdlib unittest, offline. Verifies the worked anchors in SKILL.md, the
trend properties (area grows with demand, eclipse fraction, and
degradation; shrinks with efficiency), the round-trip inverse, and the
input validation (ValueError) cases.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import solar_array_sizing_logic as sas  # noqa: E402


class SolarArraySizingAnchorTests(unittest.TestCase):
    """Worked anchors from the SKILL.md domain quick reference."""

    def test_daylight_power_anchor(self):
        # 500 W demand, 35% eclipse -> 500 / 0.65 = 769.23 W.
        self.assertAlmostEqual(sas.daylight_power(500, 0.35), 769.2308, places=3)

    def test_daylight_power_margin_anchor(self):
        # With a 0.20 sizing margin -> 769.23 * 1.20 = 923.08 W.
        self.assertAlmostEqual(sas.daylight_power(500, 0.35, 0.20), 923.0769, places=3)

    def test_degradation_factor_anchor(self):
        # 0.02 per year over 10 years -> 0.98 ** 10 = 0.8171.
        self.assertAlmostEqual(sas.degradation_factor(0.02, 10), 0.8170728068875467, places=10)

    def test_eol_specific_power_anchor(self):
        # 1367 * 0.30 * 0.85 * 0.8171 = 284.82 W/m2.
        self.assertAlmostEqual(
            sas.eol_specific_power(1367, 0.30, 0.85, 0.02, 10), 284.8193, places=3
        )

    def test_required_array_area_anchor(self):
        # 923.08 / 284.82 = 3.24 m2.
        self.assertAlmostEqual(
            sas.required_array_area(500, 0.35, 1367, 0.30, 0.85, 0.02, 10, 0.20),
            3.2409,
            places=3,
        )

    def test_required_array_area_no_margin_anchor(self):
        # 300 W, 40% eclipse, eta 0.28, PF 0.90, 3%/yr, 5 yr -> 1.69 m2.
        self.assertAlmostEqual(
            sas.required_array_area(300, 0.40, 1367, 0.28, 0.90, 0.03, 5, 0.0),
            1.6902,
            places=3,
        )


class SolarArraySizingTrendTests(unittest.TestCase):
    """Monotonic trend properties of the sizing model."""

    def test_area_increases_with_power_demand(self):
        low = sas.required_array_area(400, 0.35, 1367, 0.30, 0.85, 0.02, 10, 0.0)
        high = sas.required_array_area(600, 0.35, 1367, 0.30, 0.85, 0.02, 10, 0.0)
        self.assertGreater(high, low)

    def test_area_increases_with_eclipse_fraction(self):
        low = sas.required_array_area(500, 0.25, 1367, 0.30, 0.85, 0.02, 10, 0.0)
        high = sas.required_array_area(500, 0.45, 1367, 0.30, 0.85, 0.02, 10, 0.0)
        self.assertGreater(high, low)

    def test_area_decreases_with_cell_efficiency(self):
        low = sas.required_array_area(500, 0.35, 1367, 0.32, 0.85, 0.02, 10, 0.0)
        high = sas.required_array_area(500, 0.35, 1367, 0.26, 0.85, 0.02, 10, 0.0)
        self.assertGreater(high, low)

    def test_area_increases_with_annual_degradation(self):
        low = sas.required_array_area(500, 0.35, 1367, 0.30, 0.85, 0.01, 10, 0.0)
        high = sas.required_array_area(500, 0.35, 1367, 0.30, 0.85, 0.04, 10, 0.0)
        self.assertGreater(high, low)

    def test_area_increases_with_mission_years(self):
        low = sas.required_array_area(500, 0.35, 1367, 0.30, 0.85, 0.02, 5, 0.0)
        high = sas.required_array_area(500, 0.35, 1367, 0.30, 0.85, 0.02, 15, 0.0)
        self.assertGreater(high, low)

    def test_degradation_factor_monotone_decreasing(self):
        self.assertGreater(sas.degradation_factor(0.02, 5), sas.degradation_factor(0.02, 15))


class SolarArraySizingRoundTripTests(unittest.TestCase):
    """Inverse consistency between area and available power."""

    def test_array_power_available_roundtrip(self):
        area = sas.required_array_area(500, 0.35, 1367, 0.30, 0.85, 0.02, 10, 0.20)
        available = sas.array_power_available(area, 1367, 0.30, 0.85, 0.02, 10)
        self.assertAlmostEqual(available, 923.0769, places=3)

    def test_power_margin_matches_sizing_margin(self):
        area = sas.required_array_area(500, 0.35, 1367, 0.30, 0.85, 0.02, 10, 0.20)
        margin = sas.power_margin(area, 500, 0.35, 1367, 0.30, 0.85, 0.02, 10)
        self.assertAlmostEqual(margin, 0.20, places=6)

    def test_zero_margin_gives_zero_margin(self):
        area = sas.required_array_area(500, 0.35, 1367, 0.30, 0.85, 0.02, 10, 0.0)
        margin = sas.power_margin(area, 500, 0.35, 1367, 0.30, 0.85, 0.02, 10)
        self.assertAlmostEqual(margin, 0.0, places=6)

    def test_margin_negative_when_undersized(self):
        # An area sized for 400 W cannot cover a 600 W demand.
        area = sas.required_array_area(400, 0.35, 1367, 0.30, 0.85, 0.02, 10, 0.0)
        margin = sas.power_margin(area, 600, 0.35, 1367, 0.30, 0.85, 0.02, 10)
        self.assertLess(margin, 0.0)


class SolarArraySizingValidationTests(unittest.TestCase):
    """Input validation: invalid values must raise ValueError."""

    def test_negative_power_demand_raises(self):
        with self.assertRaises(ValueError):
            sas.daylight_power(-10, 0.35)

    def test_zero_power_demand_raises(self):
        with self.assertRaises(ValueError):
            sas.required_array_area(0, 0.35, 1367, 0.30, 0.85, 0.02, 10, 0.0)

    def test_eclipse_fraction_of_one_raises(self):
        with self.assertRaises(ValueError):
            sas.daylight_power(500, 1.0)

    def test_negative_eclipse_fraction_raises(self):
        with self.assertRaises(ValueError):
            sas.daylight_power(500, -0.1)

    def test_nonpositive_cell_efficiency_raises(self):
        with self.assertRaises(ValueError):
            sas.eol_specific_power(1367, 0.0, 0.85, 0.02, 10)
        with self.assertRaises(ValueError):
            sas.eol_specific_power(1367, 1.5, 0.85, 0.02, 10)

    def test_nonpositive_packing_factor_raises(self):
        with self.assertRaises(ValueError):
            sas.eol_specific_power(1367, 0.30, 0.0, 0.02, 10)

    def test_invalid_annual_degradation_raises(self):
        with self.assertRaises(ValueError):
            sas.degradation_factor(1.0, 10)
        with self.assertRaises(ValueError):
            sas.degradation_factor(-0.02, 10)

    def test_negative_mission_years_raises(self):
        with self.assertRaises(ValueError):
            sas.degradation_factor(0.02, -1)

    def test_nonpositive_irradiance_raises(self):
        with self.assertRaises(ValueError):
            sas.eol_specific_power(0, 0.30, 0.85, 0.02, 10)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            sas.daylight_power(500, 0.35, -0.1)

    def test_nonpositive_array_area_raises(self):
        with self.assertRaises(ValueError):
            sas.array_power_available(0, 1367, 0.30, 0.85, 0.02, 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
