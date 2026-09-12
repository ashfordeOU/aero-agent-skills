#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-12C §9.4.1.8 SEHE rate prediction.

Exercises scripts/e1012_sehe_logic.py (stdlib unittest, offline). Contract:
the Weibull cross-section is zero at or below the LET threshold and positive
above it, approaching sigma_sat at very high LET, and raises for invalid
parameters; the trapezoidal integration produces a correct rate from a
LET-flux spectrum with at least two strictly ascending LET points, raising
for degenerate inputs; the shielding reduction scales the rate by the factor
and raises for out-of-range factors; the rate check flags exceedances of both
the raw requirement and the design-margin threshold, flags a missing
requirement when the computed rate is nonzero, and passes when all conditions
are met; the full assessment aggregates these steps and the compliance flag
is derived from the rate check result.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1012_sehe_logic as sehe  # noqa: E402


class WeibullCrossSectionTest(unittest.TestCase):
    def _params(self):
        return dict(sigma_sat_cm2=1e-6, let_threshold_mev_cm2_mg=5.0,
                    weibull_width=10.0, weibull_exponent=2.0)

    def test_zero_at_threshold(self):
        self.assertEqual(
            sehe.weibull_cross_section(5.0, **self._params()), 0.0
        )

    def test_zero_below_threshold(self):
        self.assertEqual(
            sehe.weibull_cross_section(3.0, **self._params()), 0.0
        )

    def test_positive_above_threshold(self):
        result = sehe.weibull_cross_section(15.0, **self._params())
        self.assertGreater(result, 0.0)

    def test_does_not_exceed_sigma_sat(self):
        result = sehe.weibull_cross_section(1000.0, **self._params())
        self.assertLessEqual(result, 1e-6)

    def test_approaches_saturation_at_high_let(self):
        result = sehe.weibull_cross_section(1000.0, **self._params())
        self.assertAlmostEqual(result, 1e-6, places=12)

    def test_raises_on_non_positive_sigma_sat(self):
        with self.assertRaises(ValueError):
            sehe.weibull_cross_section(10.0, sigma_sat_cm2=0.0,
                                       let_threshold_mev_cm2_mg=5.0,
                                       weibull_width=10.0, weibull_exponent=2.0)

    def test_raises_on_negative_threshold(self):
        with self.assertRaises(ValueError):
            sehe.weibull_cross_section(10.0, sigma_sat_cm2=1e-6,
                                       let_threshold_mev_cm2_mg=-1.0,
                                       weibull_width=10.0, weibull_exponent=2.0)

    def test_raises_on_zero_width(self):
        with self.assertRaises(ValueError):
            sehe.weibull_cross_section(10.0, sigma_sat_cm2=1e-6,
                                       let_threshold_mev_cm2_mg=5.0,
                                       weibull_width=0.0, weibull_exponent=2.0)

    def test_raises_on_zero_exponent(self):
        with self.assertRaises(ValueError):
            sehe.weibull_cross_section(10.0, sigma_sat_cm2=1e-6,
                                       let_threshold_mev_cm2_mg=5.0,
                                       weibull_width=10.0, weibull_exponent=0.0)

    def test_known_value_spot_check(self):
        # σ(15) = 1e-6 * (1 - exp(-((15-5)/10)^2)) = 1e-6 * (1 - exp(-1))
        expected = 1e-6 * (1.0 - math.exp(-1.0))
        result = sehe.weibull_cross_section(15.0, sigma_sat_cm2=1e-6,
                                            let_threshold_mev_cm2_mg=5.0,
                                            weibull_width=10.0, weibull_exponent=2.0)
        self.assertAlmostEqual(result, expected, places=18)


class IntegrateSEHERateTest(unittest.TestCase):
    def _params(self):
        return dict(sigma_sat_cm2=1e-6, let_threshold_mev_cm2_mg=5.0,
                    weibull_width=10.0, weibull_exponent=2.0)

    def test_all_let_below_threshold_gives_zero(self):
        pairs = [(1.0, 1e4), (2.0, 1e4), (3.0, 1e4)]
        result = sehe.integrate_sehe_rate(let_flux_pairs=pairs, **self._params())
        self.assertEqual(result, 0.0)

    def test_two_point_integration_basic(self):
        # Both points above threshold; result must be positive.
        pairs = [(10.0, 1e4), (20.0, 1e4)]
        result = sehe.integrate_sehe_rate(let_flux_pairs=pairs, **self._params())
        self.assertGreater(result, 0.0)

    def test_integration_scales_with_flux(self):
        pairs_low = [(10.0, 1e3), (20.0, 1e3)]
        pairs_high = [(10.0, 2e3), (20.0, 2e3)]
        rate_low = sehe.integrate_sehe_rate(let_flux_pairs=pairs_low, **self._params())
        rate_high = sehe.integrate_sehe_rate(let_flux_pairs=pairs_high, **self._params())
        self.assertAlmostEqual(rate_high / rate_low, 2.0, places=10)

    def test_raises_with_one_point(self):
        with self.assertRaises(ValueError):
            sehe.integrate_sehe_rate(let_flux_pairs=[(10.0, 1e4)], **self._params())

    def test_raises_with_no_points(self):
        with self.assertRaises(ValueError):
            sehe.integrate_sehe_rate(let_flux_pairs=[], **self._params())

    def test_raises_with_non_ascending_let(self):
        with self.assertRaises(ValueError):
            sehe.integrate_sehe_rate(let_flux_pairs=[(20.0, 1e4), (10.0, 1e4)],
                                     **self._params())

    def test_raises_with_duplicate_let(self):
        with self.assertRaises(ValueError):
            sehe.integrate_sehe_rate(let_flux_pairs=[(10.0, 1e4), (10.0, 1e4)],
                                     **self._params())


class ApplyShieldingReductionTest(unittest.TestCase):
    def test_factor_one_returns_base_rate(self):
        self.assertAlmostEqual(sehe.apply_shielding_reduction(5.0, 1.0), 5.0)

    def test_factor_zero_returns_zero(self):
        self.assertEqual(sehe.apply_shielding_reduction(5.0, 0.0), 0.0)

    def test_partial_factor(self):
        self.assertAlmostEqual(sehe.apply_shielding_reduction(4.0, 0.25), 1.0)

    def test_raises_on_negative_rate(self):
        with self.assertRaises(ValueError):
            sehe.apply_shielding_reduction(-1.0, 0.5)

    def test_raises_on_factor_above_one(self):
        with self.assertRaises(ValueError):
            sehe.apply_shielding_reduction(1.0, 1.1)

    def test_raises_on_negative_factor(self):
        with self.assertRaises(ValueError):
            sehe.apply_shielding_reduction(1.0, -0.1)


class CheckSEHERateTest(unittest.TestCase):
    def test_compliant_when_rate_and_margin_both_met(self):
        result = sehe.check_sehe_rate(0.05, 1.0, design_margin_factor=10.0)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["issue"])

    def test_rate_exceeds_raw_requirement(self):
        result = sehe.check_sehe_rate(2.0, 1.0, design_margin_factor=10.0)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["issue"], "sehe_rate_exceeds_requirement")

    def test_margin_not_met_when_rate_below_but_scaled_above(self):
        # rate=0.2, allowable=1.0, margin=10 → 0.2*10=2.0 > 1.0 → margin fails
        result = sehe.check_sehe_rate(0.2, 1.0, design_margin_factor=10.0)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["issue"], "sehe_margin_not_met")

    def test_missing_requirement_with_nonzero_rate_flagged(self):
        result = sehe.check_sehe_rate(0.5, None, design_margin_factor=10.0)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["issue"], "missing_sehe_rate_requirement")

    def test_missing_requirement_with_zero_rate_passes(self):
        result = sehe.check_sehe_rate(0.0, None, design_margin_factor=10.0)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["issue"])

    def test_raises_on_negative_computed_rate(self):
        with self.assertRaises(ValueError):
            sehe.check_sehe_rate(-0.1, 1.0)

    def test_raises_on_non_positive_margin(self):
        with self.assertRaises(ValueError):
            sehe.check_sehe_rate(0.1, 1.0, design_margin_factor=0.0)

    def test_result_carries_all_inputs(self):
        result = sehe.check_sehe_rate(0.05, 1.0, design_margin_factor=10.0)
        self.assertAlmostEqual(result["computed_rate_per_day"], 0.05)
        self.assertAlmostEqual(result["allowable_rate_per_day"], 1.0)
        self.assertEqual(result["design_margin_factor"], 10.0)


class SEHEAssessmentTest(unittest.TestCase):
    def _device(self, **overrides):
        base = {
            "device_id": "dev-A",
            "sigma_sat_cm2": 1e-6,
            "let_threshold_mev_cm2_mg": 5.0,
            "weibull_width": 10.0,
            "weibull_exponent": 2.0,
            "let_flux_pairs": [(1.0, 5e4), (10.0, 5e4), (50.0, 5e3), (100.0, 1e3)],
            "shielding_factor": 0.5,
            "allowable_rate_per_day": 100.0,
            "design_margin_factor": 10.0,
        }
        base.update(overrides)
        return base

    def test_assessment_returns_expected_keys(self):
        result = sehe.sehe_assessment(self._device())
        for key in ("device_id", "unshielded_rate_per_day",
                    "shielded_rate_per_day", "rate_check"):
            self.assertIn(key, result)

    def test_shielded_rate_equals_unshielded_times_factor(self):
        device = self._device(shielding_factor=0.3)
        result = sehe.sehe_assessment(device)
        self.assertAlmostEqual(
            result["shielded_rate_per_day"],
            result["unshielded_rate_per_day"] * 0.3,
            places=12,
        )

    def test_compliant_assessment_is_compliant(self):
        result = sehe.sehe_assessment(self._device(allowable_rate_per_day=1e10))
        self.assertTrue(sehe.is_sehe_compliant(result))

    def test_rate_exceedance_makes_assessment_noncompliant(self):
        result = sehe.sehe_assessment(self._device(allowable_rate_per_day=1e-20))
        self.assertFalse(sehe.is_sehe_compliant(result))

    def test_missing_requirement_makes_assessment_noncompliant(self):
        result = sehe.sehe_assessment(self._device(allowable_rate_per_day=None))
        self.assertFalse(sehe.is_sehe_compliant(result))

    def test_device_id_propagated(self):
        result = sehe.sehe_assessment(self._device(device_id="sensor-1"))
        self.assertEqual(result["device_id"], "sensor-1")


if __name__ == "__main__":
    unittest.main()
