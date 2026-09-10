#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 10.2.6 debris/meteoroid
margin policy.

Exercises scripts/e1004_mm_margins_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a flux margin factor below
1.0 or a diameter margin factor above 1.0 is rejected (margins must not
relax the prediction); the diameter-margin rescale requires the
margined diameter to stay in (0, baseline] and a positive power-law
exponent; the margined expected-impact rate is always >= the baseline
rate for factor=1.0 diameter margin and strictly greater once either
margin engages; PNP is a strictly decreasing function of expected
impacts; and margin_factors_are_conservative flags a project-supplied
factor weaker than the stated floor/ceiling.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_mm_margins_logic as mm  # noqa: E402


class ApplyFluxMarginTest(unittest.TestCase):
    def test_scales_by_factor(self):
        self.assertAlmostEqual(mm.apply_flux_margin(2.0, 3.0), 6.0)

    def test_factor_of_one_is_identity(self):
        self.assertAlmostEqual(mm.apply_flux_margin(5.0, 1.0), 5.0)

    def test_negative_baseline_raises(self):
        with self.assertRaises(ValueError):
            mm.apply_flux_margin(-1.0, 1.5)

    def test_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            mm.apply_flux_margin(2.0, 0.9)


class ApplyDiameterMarginTest(unittest.TestCase):
    def test_scales_by_factor(self):
        self.assertAlmostEqual(mm.apply_diameter_margin(10.0, 0.8), 8.0)

    def test_factor_of_one_is_identity(self):
        self.assertAlmostEqual(mm.apply_diameter_margin(10.0, 1.0), 10.0)

    def test_non_positive_baseline_raises(self):
        with self.assertRaises(ValueError):
            mm.apply_diameter_margin(0.0, 0.8)

    def test_factor_above_one_raises(self):
        with self.assertRaises(ValueError):
            mm.apply_diameter_margin(10.0, 1.1)

    def test_factor_of_zero_raises(self):
        with self.assertRaises(ValueError):
            mm.apply_diameter_margin(10.0, 0.0)


class ExpectedImpactsForMarginedDiameterTest(unittest.TestCase):
    def test_smaller_diameter_raises_impact_rate(self):
        result = mm.expected_impacts_for_margined_diameter(1.0, 10.0, 5.0, power_law_exponent=2.0)
        self.assertAlmostEqual(result, 4.0)

    def test_equal_diameter_is_identity(self):
        result = mm.expected_impacts_for_margined_diameter(3.0, 10.0, 10.0, power_law_exponent=2.0)
        self.assertAlmostEqual(result, 3.0)

    def test_margined_diameter_above_baseline_raises(self):
        with self.assertRaises(ValueError):
            mm.expected_impacts_for_margined_diameter(1.0, 10.0, 11.0, power_law_exponent=2.0)

    def test_non_positive_margined_diameter_raises(self):
        with self.assertRaises(ValueError):
            mm.expected_impacts_for_margined_diameter(1.0, 10.0, 0.0, power_law_exponent=2.0)

    def test_non_positive_power_law_exponent_raises(self):
        with self.assertRaises(ValueError):
            mm.expected_impacts_for_margined_diameter(1.0, 10.0, 5.0, power_law_exponent=0.0)

    def test_negative_flux_margined_impacts_raises(self):
        with self.assertRaises(ValueError):
            mm.expected_impacts_for_margined_diameter(-1.0, 10.0, 5.0, power_law_exponent=2.0)


class ProbabilityOfNoPenetrationTest(unittest.TestCase):
    def test_zero_impacts_gives_certainty(self):
        self.assertAlmostEqual(mm.probability_of_no_penetration(0.0), 1.0)

    def test_matches_poisson_formula(self):
        self.assertAlmostEqual(mm.probability_of_no_penetration(2.0), math.exp(-2.0))

    def test_strictly_decreasing_in_expected_impacts(self):
        self.assertGreater(
            mm.probability_of_no_penetration(1.0), mm.probability_of_no_penetration(2.0)
        )

    def test_negative_expected_impacts_raises(self):
        with self.assertRaises(ValueError):
            mm.probability_of_no_penetration(-0.1)


class BuildMarginedDamagePredictionTest(unittest.TestCase):
    def test_fields_and_relationships(self):
        result = mm.build_margined_damage_prediction(
            baseline_expected_impacts=1.0,
            baseline_critical_diameter=10.0,
            flux_margin_factor=2.0,
            diameter_margin_factor=0.5,
            power_law_exponent=2.0,
        )
        self.assertAlmostEqual(result["margined_critical_diameter"], 5.0)
        # flux margin (x2) then diameter rescale ((10/5)^2 = x4) => x8 baseline.
        self.assertAlmostEqual(result["margined_expected_impacts"], 8.0)
        self.assertAlmostEqual(result["margined_pnp"], math.exp(-8.0))
        self.assertAlmostEqual(result["baseline_pnp"], math.exp(-1.0))
        self.assertGreater(result["baseline_pnp"], result["margined_pnp"])

    def test_no_margin_leaves_prediction_unchanged(self):
        result = mm.build_margined_damage_prediction(
            baseline_expected_impacts=1.5,
            baseline_critical_diameter=10.0,
            flux_margin_factor=1.0,
            diameter_margin_factor=1.0,
            power_law_exponent=2.0,
        )
        self.assertAlmostEqual(result["margined_expected_impacts"], 1.5)
        self.assertAlmostEqual(result["margined_pnp"], result["baseline_pnp"])

    def test_invalid_input_propagates(self):
        with self.assertRaises(ValueError):
            mm.build_margined_damage_prediction(
                baseline_expected_impacts=1.0,
                baseline_critical_diameter=10.0,
                flux_margin_factor=0.5,
                diameter_margin_factor=1.0,
                power_law_exponent=2.0,
            )


class MeetsPnpRequirementTest(unittest.TestCase):
    def test_meets_when_equal_or_above(self):
        self.assertTrue(mm.meets_pnp_requirement(0.999, 0.999))
        self.assertTrue(mm.meets_pnp_requirement(0.9995, 0.999))

    def test_fails_when_below(self):
        self.assertFalse(mm.meets_pnp_requirement(0.9985, 0.999))


class MarginFactorsAreConservativeTest(unittest.TestCase):
    def test_true_when_at_or_beyond_floor_and_ceiling(self):
        self.assertTrue(
            mm.margin_factors_are_conservative(
                flux_margin_factor=2.0,
                diameter_margin_factor=0.8,
                min_flux_margin_factor=1.5,
                max_diameter_margin_factor=0.9,
            )
        )

    def test_false_when_flux_margin_weaker_than_floor(self):
        self.assertFalse(
            mm.margin_factors_are_conservative(
                flux_margin_factor=1.2,
                diameter_margin_factor=0.8,
                min_flux_margin_factor=1.5,
                max_diameter_margin_factor=0.9,
            )
        )

    def test_false_when_diameter_margin_weaker_than_ceiling(self):
        self.assertFalse(
            mm.margin_factors_are_conservative(
                flux_margin_factor=2.0,
                diameter_margin_factor=0.95,
                min_flux_margin_factor=1.5,
                max_diameter_margin_factor=0.9,
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
