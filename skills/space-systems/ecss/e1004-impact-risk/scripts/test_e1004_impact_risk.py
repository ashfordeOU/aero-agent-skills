#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 10.2.5 impact risk
assessment.

Exercises scripts/e1004_impact_risk_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - cumulative
per-population fluxes at a shared critical diameter sum linearly;
expected impacts N = flux * area * duration requires a non-negative
flux and positive area/duration; probability of no penetration is
exp(-N) and probability of damage is its complement; an element meets
its PNP requirement only when Po >= pnp_requirement; system-level PNP
combines independent element PNPs multiplicatively; empty inputs and
out-of-range values raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_impact_risk_logic as ir  # noqa: E402


class CombineCumulativeFluxesTest(unittest.TestCase):
    def test_sums_linearly(self):
        self.assertAlmostEqual(ir.combine_cumulative_fluxes([1e-6, 2e-6, 3e-7]), 3.3e-6)

    def test_single_value(self):
        self.assertEqual(ir.combine_cumulative_fluxes([5e-5]), 5e-5)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            ir.combine_cumulative_fluxes([])

    def test_negative_flux_raises(self):
        with self.assertRaises(ValueError):
            ir.combine_cumulative_fluxes([1e-6, -1e-7])


class ExpectedImpactCountTest(unittest.TestCase):
    def test_basic_product(self):
        self.assertAlmostEqual(ir.expected_impact_count(1e-4, 10.0, 5.0), 5e-3)

    def test_zero_flux_gives_zero_impacts(self):
        self.assertEqual(ir.expected_impact_count(0.0, 10.0, 5.0), 0.0)

    def test_negative_flux_raises(self):
        with self.assertRaises(ValueError):
            ir.expected_impact_count(-1e-6, 10.0, 5.0)

    def test_non_positive_area_raises(self):
        with self.assertRaises(ValueError):
            ir.expected_impact_count(1e-4, 0.0, 5.0)
        with self.assertRaises(ValueError):
            ir.expected_impact_count(1e-4, -1.0, 5.0)

    def test_non_positive_duration_raises(self):
        with self.assertRaises(ValueError):
            ir.expected_impact_count(1e-4, 10.0, 0.0)
        with self.assertRaises(ValueError):
            ir.expected_impact_count(1e-4, 10.0, -5.0)


class ProbabilityTest(unittest.TestCase):
    def test_zero_impacts_gives_certain_no_penetration(self):
        self.assertEqual(ir.probability_no_penetration(0.0), 1.0)
        self.assertEqual(ir.probability_of_damage(0.0), 0.0)

    def test_known_rate(self):
        self.assertAlmostEqual(ir.probability_no_penetration(1.0), math.exp(-1.0))
        self.assertAlmostEqual(ir.probability_of_damage(1.0), 1.0 - math.exp(-1.0))

    def test_complementary(self):
        n = 0.02
        self.assertAlmostEqual(
            ir.probability_no_penetration(n) + ir.probability_of_damage(n), 1.0
        )

    def test_negative_impacts_raises(self):
        with self.assertRaises(ValueError):
            ir.probability_no_penetration(-0.1)
        with self.assertRaises(ValueError):
            ir.probability_of_damage(-0.1)


class AssessImpactRiskTest(unittest.TestCase):
    def test_meets_requirement(self):
        result = ir.assess_impact_risk(
            {"debris": 1e-7, "meteoroid_background": 2e-8},
            exposed_area_m2=2.0,
            duration_years=5.0,
            pnp_requirement=0.999,
        )
        total_flux = 1e-7 + 2e-8
        expected_n = total_flux * 2.0 * 5.0
        self.assertAlmostEqual(result["total_expected_impacts"], expected_n)
        self.assertAlmostEqual(result["probability_no_penetration"], math.exp(-expected_n))
        self.assertTrue(result["meets_requirement"])
        self.assertEqual(result["shortfall"], 0.0)
        self.assertAlmostEqual(
            result["per_component_impacts"]["debris"], 1e-7 * 2.0 * 5.0
        )

    def test_fails_requirement_reports_shortfall(self):
        result = ir.assess_impact_risk(
            {"debris": 1e-3},
            exposed_area_m2=50.0,
            duration_years=10.0,
            pnp_requirement=0.999,
        )
        self.assertFalse(result["meets_requirement"])
        self.assertGreater(result["shortfall"], 0.0)
        self.assertAlmostEqual(
            result["shortfall"],
            0.999 - result["probability_no_penetration"],
        )

    def test_empty_component_fluxes_raises(self):
        with self.assertRaises(ValueError):
            ir.assess_impact_risk({}, 1.0, 1.0, 0.999)

    def test_pnp_requirement_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            ir.assess_impact_risk({"debris": 1e-6}, 1.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            ir.assess_impact_risk({"debris": 1e-6}, 1.0, 1.0, 1.5)


class CombineSystemPnpTest(unittest.TestCase):
    def test_combines_multiplicatively(self):
        self.assertAlmostEqual(ir.combine_system_pnp([0.99, 0.98, 0.995]), 0.99 * 0.98 * 0.995)

    def test_single_element_passthrough(self):
        self.assertEqual(ir.combine_system_pnp([0.97]), 0.97)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            ir.combine_system_pnp([])

    def test_out_of_range_pnp_raises(self):
        with self.assertRaises(ValueError):
            ir.combine_system_pnp([0.99, 0.0])
        with self.assertRaises(ValueError):
            ir.combine_system_pnp([0.99, 1.2])


if __name__ == "__main__":
    unittest.main(verbosity=2)
