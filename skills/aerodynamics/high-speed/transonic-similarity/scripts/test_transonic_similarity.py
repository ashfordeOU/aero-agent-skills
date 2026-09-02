#!/usr/bin/env python3
"""Gate 3 contract test: transonic similarity (compressibility corrections).

Exercises scripts/transonic_similarity_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - Prandtl-Glauert
factor 1 / sqrt(1 - M^2) with exact values at M = 0.6 (1.25) and
M = 0.8 (5/3), Karman-Tsien pressure coefficient correction with the
known value -2/3 for C_p0 = -0.5 at M = 0.6, corrected section lift
slope, transonic similarity parameter K = (1 - M^2) / tau^(2/3),
critical pressure coefficient C_p* at M = 0.7 (-0.7792), and critical
Mach number root-finding validated against the defining equation, with
ValueError on out-of-range inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import transonic_similarity_logic as ts  # noqa: E402


class PrandtlGlauertTest(unittest.TestCase):
    def test_factor_at_reference_mach(self):
        # 1 / sqrt(1 - 0.36) = 1 / 0.8 = 1.25
        self.assertAlmostEqual(ts.prandtl_glauert_factor(0.6), 1.25, delta=1e-9)
        # 1 / sqrt(1 - 0.64) = 1 / 0.6 = 5/3
        self.assertAlmostEqual(ts.prandtl_glauert_factor(0.8), 5.0 / 3.0, delta=1e-9)

    def test_factor_at_zero_and_low_mach(self):
        self.assertAlmostEqual(ts.prandtl_glauert_factor(0.0), 1.0, delta=1e-12)
        # small-M expansion: 1 + M^2 / 2
        self.assertAlmostEqual(ts.prandtl_glauert_factor(0.1), 1.0 + 0.005, delta=1e-4)

    def test_factor_grows_with_mach(self):
        self.assertLess(ts.prandtl_glauert_factor(0.3), ts.prandtl_glauert_factor(0.6))

    def test_pressure_coefficient_correction(self):
        self.assertAlmostEqual(
            ts.prandtl_glauert_correction(-0.5, 0.6), -0.625, delta=1e-9
        )
        self.assertAlmostEqual(
            ts.prandtl_glauert_correction(0.3, 0.0), 0.3, delta=1e-12
        )

    def test_lift_slope_correction(self):
        # a0 = 2 pi at M = 0.6 -> 2 pi / 0.8
        self.assertAlmostEqual(
            ts.corrected_lift_slope(2.0 * math.pi, 0.6),
            2.0 * math.pi / 0.8,
            delta=1e-9,
        )

    def test_supersonic_and_negative_mach_raise(self):
        with self.assertRaises(ValueError):
            ts.prandtl_glauert_factor(1.0)
        with self.assertRaises(ValueError):
            ts.prandtl_glauert_factor(1.5)
        with self.assertRaises(ValueError):
            ts.prandtl_glauert_correction(-0.5, -0.1)


class KarmanTsienTest(unittest.TestCase):
    def test_reference_value(self):
        # C_p0 = -0.5, M = 0.6: denom = 0.8 + 0.2 * (-0.25) = 0.75
        self.assertAlmostEqual(
            ts.karman_tsien_correction(-0.5, 0.6), -0.5 / 0.75, delta=1e-9
        )

    def test_zero_mach_reduces_to_incompressible(self):
        self.assertAlmostEqual(
            ts.karman_tsien_correction(0.3, 0.0), 0.3, delta=1e-12
        )

    def test_karman_tsien_more_severe_than_prandtl_glauert(self):
        # suction strengthens faster under Karman-Tsien than Prandtl-Glauert
        kt = ts.karman_tsien_correction(-0.5, 0.6)
        pg = ts.prandtl_glauert_correction(-0.5, 0.6)
        self.assertLess(kt, pg)

    def test_supersonic_mach_raises(self):
        with self.assertRaises(ValueError):
            ts.karman_tsien_correction(-0.5, 1.0)


class TransonicSimilarityParameterTest(unittest.TestCase):
    def test_reference_value(self):
        # K = (1 - 0.81) / 0.12^(2/3) = 0.19 / 0.24329 = 0.78098
        self.assertAlmostEqual(
            ts.transonic_similarity_parameter(0.9, 0.12), 0.78098, delta=1e-3
        )

    def test_incompressible_limit(self):
        # M = 0: K = 1 / tau^(2/3) = 4.1103 for tau = 0.12
        self.assertAlmostEqual(
            ts.transonic_similarity_parameter(0.0, 0.12), 4.1103, delta=1e-3
        )

    def test_similarity_at_mach_one(self):
        self.assertAlmostEqual(
            ts.transonic_similarity_parameter(1.0, 0.12), 0.0, delta=1e-12
        )

    def test_thicker_section_lowers_parameter(self):
        self.assertGreater(
            ts.transonic_similarity_parameter(0.85, 0.08),
            ts.transonic_similarity_parameter(0.85, 0.15),
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ts.transonic_similarity_parameter(0.5, 0.0)
        with self.assertRaises(ValueError):
            ts.transonic_similarity_parameter(0.5, 1.2)
        with self.assertRaises(ValueError):
            ts.transonic_similarity_parameter(1.5, 0.12)


class CriticalPressureCoefficientTest(unittest.TestCase):
    def test_reference_value(self):
        # C_p* at M = 0.7, gamma = 1.4: -0.77917
        self.assertAlmostEqual(
            ts.critical_pressure_coefficient(0.7), -0.77917, delta=1e-3
        )

    def test_sonic_limit_is_zero_at_mach_one(self):
        self.assertAlmostEqual(
            ts.critical_pressure_coefficient(1.0), 0.0, delta=1e-9
        )

    def test_sonic_limit_is_negative(self):
        self.assertLess(ts.critical_pressure_coefficient(0.5), 0.0)

    def test_gamma_variation(self):
        # C_p* at M = 0.6, gamma = 1.3: -1.34402 (gamma shifts the limit)
        self.assertAlmostEqual(
            ts.critical_pressure_coefficient(0.6, 1.3), -1.34402, delta=1e-3
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ts.critical_pressure_coefficient(0.0)
        with self.assertRaises(ValueError):
            ts.critical_pressure_coefficient(1.5)
        with self.assertRaises(ValueError):
            ts.critical_pressure_coefficient(0.6, 1.0)


class CriticalMachNumberTest(unittest.TestCase):
    def test_reference_value(self):
        # C_p0 = -0.5 gives M_cr near 0.714 (typical transport section)
        m = ts.critical_mach_number(-0.5)
        self.assertGreater(m, 0.70)
        self.assertLess(m, 0.73)

    def test_root_satisfies_defining_equation(self):
        m = ts.critical_mach_number(-0.5)
        lhs = -0.5 / math.sqrt(1.0 - m * m)
        rhs = ts.critical_pressure_coefficient(m)
        self.assertAlmostEqual(lhs, rhs, delta=1e-6)

    def test_weaker_suction_raises_critical_mach(self):
        self.assertGreater(
            ts.critical_mach_number(-0.2), ts.critical_mach_number(-0.8)
        )

    def test_thin_section_reference(self):
        # C_p0 = -0.3: M_cr near 0.80
        m = ts.critical_mach_number(-0.3)
        self.assertGreater(m, 0.78)
        self.assertLess(m, 0.82)

    def test_nonnegative_suction_raises(self):
        with self.assertRaises(ValueError):
            ts.critical_mach_number(0.0)
        with self.assertRaises(ValueError):
            ts.critical_mach_number(0.4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
