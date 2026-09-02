#!/usr/bin/env python3
"""Gate 3 contract test: eddy current inspection.

Exercises scripts/eddy_current_inspection_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (standard depth of
penetration from frequency, conductivity, and permeability; frequency
selection placing a flaw within the penetration band; percent IACS to
S/m conversion; eddy current density ratio and phase lag at depth;
invalid inputs raise ValueError.

Anchors:
- standard_depth_of_penetration(1e5, 5.8e7) = 2.0898e-4 m (copper
  100 kHz, about 0.21 mm)
- standard_depth_of_penetration(60, 5.8e7) = 8.5316e-3 m (copper 60 Hz)
- standard_depth_of_penetration(2e5, 1.74e7) = 2.6979e-4 m (aluminum
  30 pct IACS at 200 kHz)
- frequency_for_depth(1e-3, 1.74e7) = 14557.6 Hz (one delta at 1 mm)
- select_frequency_for_flaw(1e-3, 1.74e7, penetration_factor=2.0) =
  3639.4 Hz (delta = 2 mm for a 1 mm subsurface flaw)
- eddy_current_density_ratio(delta, delta) = 0.3679 (1/e)
- phase_lag_degrees(delta, delta) = 57.2958 (one radian at one delta)
- conductivity_from_iacs(100) = 5.8e7 S/m; (30) = 1.74e7 S/m
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import eddy_current_inspection_logic as ec  # noqa: E402


class StandardDepthOfPenetrationTest(unittest.TestCase):
    def test_anchor_copper_100khz(self):
        self.assertAlmostEqual(ec.standard_depth_of_penetration(1e5, 5.8e7), 2.0898e-4)

    def test_anchor_copper_60hz(self):
        self.assertAlmostEqual(ec.standard_depth_of_penetration(60, 5.8e7), 8.5316e-3)

    def test_anchor_aluminum_200khz(self):
        self.assertAlmostEqual(
            ec.standard_depth_of_penetration(2e5, 1.74e7), 2.6979e-4
        )

    def test_higher_frequency_shrinks_delta(self):
        high = ec.standard_depth_of_penetration(1e6, 5.8e7)
        low = ec.standard_depth_of_penetration(1e5, 5.8e7)
        self.assertLess(high, low)

    def test_ferromagnetic_permeability_shrinks_delta(self):
        plain = ec.standard_depth_of_penetration(1e5, 5.8e7, relative_permeability=1.0)
        ferrous = ec.standard_depth_of_penetration(
            1e5, 5.8e7, relative_permeability=100.0
        )
        self.assertAlmostEqual(ferrous, plain / 10.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ec.standard_depth_of_penetration(0, 5.8e7)
        with self.assertRaises(ValueError):
            ec.standard_depth_of_penetration(-1e5, 5.8e7)
        with self.assertRaises(ValueError):
            ec.standard_depth_of_penetration(1e5, 0)
        with self.assertRaises(ValueError):
            ec.standard_depth_of_penetration(1e5, -5.8e7)
        with self.assertRaises(ValueError):
            ec.standard_depth_of_penetration(1e5, 5.8e7, relative_permeability=0)


class FrequencyForDepthTest(unittest.TestCase):
    def test_anchor_aluminum_1mm(self):
        self.assertAlmostEqual(
            ec.frequency_for_depth(1e-3, 1.74e7), 14557.6413, places=2
        )

    def test_roundtrip_with_delta(self):
        delta = ec.standard_depth_of_penetration(1e5, 5.8e7)
        f = ec.frequency_for_depth(delta, 5.8e7)
        self.assertAlmostEqual(f, 1e5, places=1)

    def test_deeper_flaw_needs_lower_frequency(self):
        deep = ec.frequency_for_depth(2e-3, 1.74e7)
        shallow = ec.frequency_for_depth(1e-3, 1.74e7)
        self.assertLess(deep, shallow)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ec.frequency_for_depth(0, 1.74e7)
        with self.assertRaises(ValueError):
            ec.frequency_for_depth(-1e-3, 1.74e7)
        with self.assertRaises(ValueError):
            ec.frequency_for_depth(1e-3, 0)
        with self.assertRaises(ValueError):
            ec.frequency_for_depth(1e-3, 1.74e7, relative_permeability=-1)


class SelectFrequencyForFlawTest(unittest.TestCase):
    def test_anchor_subsurface_factor_two(self):
        self.assertAlmostEqual(
            ec.select_frequency_for_flaw(1e-3, 1.74e7, penetration_factor=2.0),
            3639.4103,
            places=2,
        )

    def test_anchor_surface_factor_half(self):
        self.assertAlmostEqual(
            ec.select_frequency_for_flaw(1e-3, 1.74e7, penetration_factor=0.5),
            58230.5653,
            places=1,
        )

    def test_subsurface_lower_than_surface_frequency(self):
        sub = ec.select_frequency_for_flaw(1e-3, 1.74e7, penetration_factor=2.0)
        surf = ec.select_frequency_for_flaw(1e-3, 1.74e7, penetration_factor=0.5)
        self.assertLess(sub, surf)

    def test_default_factor_keeps_flaw_within_one_delta(self):
        f = ec.select_frequency_for_flaw(1e-3, 1.74e7)
        delta = ec.standard_depth_of_penetration(f, 1.74e7)
        self.assertAlmostEqual(delta, 2e-3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ec.select_frequency_for_flaw(0, 1.74e7)
        with self.assertRaises(ValueError):
            ec.select_frequency_for_flaw(1e-3, 0)
        with self.assertRaises(ValueError):
            ec.select_frequency_for_flaw(1e-3, 1.74e7, penetration_factor=0)
        with self.assertRaises(ValueError):
            ec.select_frequency_for_flaw(1e-3, 1.74e7, penetration_factor=-1.0)


class DensityRatioTest(unittest.TestCase):
    def test_anchor_one_delta(self):
        self.assertAlmostEqual(
            ec.eddy_current_density_ratio(1e-3, 1e-3), 0.3679, places=4
        )

    def test_anchor_surface(self):
        self.assertAlmostEqual(ec.eddy_current_density_ratio(0.0, 1e-3), 1.0)

    def test_anchor_two_delta(self):
        self.assertAlmostEqual(
            ec.eddy_current_density_ratio(2e-3, 1e-3), 0.1353, places=4
        )

    def test_deeper_depth_lower_density(self):
        deep = ec.eddy_current_density_ratio(2e-3, 1e-3)
        shallow = ec.eddy_current_density_ratio(1e-3, 1e-3)
        self.assertLess(deep, shallow)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ec.eddy_current_density_ratio(-1e-3, 1e-3)
        with self.assertRaises(ValueError):
            ec.eddy_current_density_ratio(1e-3, 0)
        with self.assertRaises(ValueError):
            ec.eddy_current_density_ratio(1e-3, -1e-3)


class PhaseLagTest(unittest.TestCase):
    def test_anchor_one_delta(self):
        self.assertAlmostEqual(ec.phase_lag_degrees(1e-3, 1e-3), 57.2958, places=4)

    def test_anchor_two_delta(self):
        self.assertAlmostEqual(ec.phase_lag_degrees(2e-3, 1e-3), 114.5916, places=4)

    def test_anchor_surface(self):
        self.assertAlmostEqual(ec.phase_lag_degrees(0.0, 1e-3), 0.0)

    def test_linear_in_depth(self):
        one = ec.phase_lag_degrees(1e-3, 1e-3)
        half = ec.phase_lag_degrees(0.5e-3, 1e-3)
        self.assertAlmostEqual(half, one / 2.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ec.phase_lag_degrees(-1e-3, 1e-3)
        with self.assertRaises(ValueError):
            ec.phase_lag_degrees(1e-3, 0)


class ConductivityIacsTest(unittest.TestCase):
    def test_anchor_copper_100(self):
        self.assertAlmostEqual(ec.conductivity_from_iacs(100), 5.8e7)

    def test_anchor_aluminum_30(self):
        self.assertAlmostEqual(ec.conductivity_from_iacs(30), 1.74e7)

    def test_anchor_titanium_5(self):
        self.assertAlmostEqual(ec.conductivity_from_iacs(5), 2.9e6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ec.conductivity_from_iacs(0)
        with self.assertRaises(ValueError):
            ec.conductivity_from_iacs(-10)


class SubsurfaceFlawScenarioTest(unittest.TestCase):
    def test_subsurface_flaw_within_one_delta(self):
        # 1 mm subsurface flaw in aluminum 30 pct IACS. Frequency chosen
        # with a factor of 2.0 puts delta at 2 mm, so the flaw sits at
        # half a delta where the density ratio is exp(-0.5) = 0.6065.
        f = ec.select_frequency_for_flaw(1e-3, 1.74e7, penetration_factor=2.0)
        delta = ec.standard_depth_of_penetration(f, 1.74e7)
        ratio = ec.eddy_current_density_ratio(1e-3, delta)
        lag = ec.phase_lag_degrees(1e-3, delta)
        self.assertAlmostEqual(delta, 2e-3)
        self.assertAlmostEqual(ratio, 0.6065, places=4)
        self.assertAlmostEqual(lag, 28.6479, places=4)

    def test_surface_crack_sharp_sensitivity(self):
        # A surface crack needs a small delta: factor 0.5 at a 1 mm
        # crack depth gives a shallow 0.5 mm delta and a high frequency,
        # higher than the subsurface-flaw frequency for the same depth.
        f = ec.select_frequency_for_flaw(1e-3, 1.74e7, penetration_factor=0.5)
        sub = ec.select_frequency_for_flaw(1e-3, 1.74e7, penetration_factor=2.0)
        self.assertAlmostEqual(ec.standard_depth_of_penetration(f, 1.74e7), 5e-4)
        self.assertGreater(f, sub)
        self.assertGreater(f, 5e4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
