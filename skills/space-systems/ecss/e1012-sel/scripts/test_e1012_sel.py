"""
Gate 3 contract tests for e1012_sel_logic.py.
stdlib unittest only; offline; deterministic. Run: python3 test_e1012_sel.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_sel_logic import (
    SEL_RATE_ACCEPTABLE,
    SEL_RATE_MONITOR,
    SELAssessment,
    assess_sel,
    bendel_proton_cross_section,
    categorize_sel_rate,
    heavy_ion_sel_rate,
    proton_sel_rate,
    weibull_cross_section,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _let_spectrum(let_min, let_max, n, flux):
    step = (let_max - let_min) / (n - 1)
    return [(let_min + i * step, flux) for i in range(n)]


def _energy_spectrum(e_min, e_max, n, flux):
    step = (e_max - e_min) / (n - 1)
    return [(e_min + i * step, flux) for i in range(n)]


# ── Weibull cross-section tests ───────────────────────────────────────────────

class TestWeibullCrossSection(unittest.TestCase):

    def test_below_threshold_returns_zero(self):
        self.assertEqual(weibull_cross_section(3.0, 10.0, 1e-6, 5.0, 1.2), 0.0)

    def test_at_threshold_returns_zero(self):
        self.assertEqual(weibull_cross_section(10.0, 10.0, 1e-6, 5.0, 1.2), 0.0)

    def test_well_above_threshold_approaches_saturation(self):
        sigma = weibull_cross_section(1000.0, 1.0, 1e-6, 5.0, 1.0)
        self.assertAlmostEqual(sigma, 1e-6, places=10)

    def test_monotonically_increasing_with_let(self):
        lets = [2.0, 5.0, 10.0, 20.0, 50.0]
        sigmas = [weibull_cross_section(l, 1.0, 1e-6, 5.0, 1.0) for l in lets]
        for i in range(len(sigmas) - 1):
            self.assertLess(sigmas[i], sigmas[i + 1])

    def test_never_exceeds_sigma_sat(self):
        sigma_sat = 1e-6
        sigma = weibull_cross_section(500.0, 1.0, sigma_sat, 5.0, 1.5)
        self.assertLessEqual(sigma, sigma_sat)

    def test_invalid_width_raises(self):
        with self.assertRaises(ValueError):
            weibull_cross_section(10.0, 1.0, 1e-6, 0.0, 1.0)

    def test_negative_width_raises(self):
        with self.assertRaises(ValueError):
            weibull_cross_section(10.0, 1.0, 1e-6, -2.0, 1.0)

    def test_invalid_shape_raises(self):
        with self.assertRaises(ValueError):
            weibull_cross_section(10.0, 1.0, 1e-6, 5.0, 0.0)

    def test_invalid_sigma_sat_raises(self):
        with self.assertRaises(ValueError):
            weibull_cross_section(10.0, 1.0, 0.0, 5.0, 1.0)


# ── Heavy-ion rate integration tests ─────────────────────────────────────────

class TestHeavyIonSELRate(unittest.TestCase):

    def test_zero_rate_when_spectrum_below_threshold(self):
        spec = _let_spectrum(0.1, 0.9, 5, 1e4)
        rate = heavy_ion_sel_rate(spec, 1.0, 1e-6, 5.0, 1.0)
        self.assertAlmostEqual(rate, 0.0, places=20)

    def test_positive_rate_when_spectrum_above_threshold(self):
        spec = _let_spectrum(10.0, 100.0, 20, 1e3)
        rate = heavy_ion_sel_rate(spec, 1.0, 1e-6, 5.0, 1.0)
        self.assertGreater(rate, 0.0)

    def test_higher_flux_gives_higher_rate(self):
        spec_lo = _let_spectrum(5.0, 50.0, 20, 1e2)
        spec_hi = _let_spectrum(5.0, 50.0, 20, 1e4)
        rate_lo = heavy_ion_sel_rate(spec_lo, 2.0, 1e-6, 3.0, 1.0)
        rate_hi = heavy_ion_sel_rate(spec_hi, 2.0, 1e-6, 3.0, 1.0)
        self.assertGreater(rate_hi, rate_lo)

    def test_larger_sigma_sat_gives_larger_rate(self):
        spec = _let_spectrum(5.0, 50.0, 20, 1e3)
        rate_sm = heavy_ion_sel_rate(spec, 2.0, 1e-8, 3.0, 1.0)
        rate_lg = heavy_ion_sel_rate(spec, 2.0, 1e-4, 3.0, 1.0)
        self.assertGreater(rate_lg, rate_sm)

    def test_empty_spectrum_raises(self):
        with self.assertRaises(ValueError):
            heavy_ion_sel_rate([], 1.0, 1e-6, 5.0, 1.0)

    def test_invalid_sigma_sat_raises(self):
        spec = _let_spectrum(5.0, 50.0, 5, 1e3)
        with self.assertRaises(ValueError):
            heavy_ion_sel_rate(spec, 1.0, 0.0, 5.0, 1.0)

    def test_unsorted_spectrum_same_result_as_sorted(self):
        pairs_sorted   = _let_spectrum(2.0, 40.0, 10, 1e3)
        pairs_reversed = list(reversed(pairs_sorted))
        r1 = heavy_ion_sel_rate(pairs_sorted,   1.0, 1e-6, 5.0, 1.0)
        r2 = heavy_ion_sel_rate(pairs_reversed, 1.0, 1e-6, 5.0, 1.0)
        self.assertAlmostEqual(r1, r2, places=15)


# ── Bendel proton cross-section tests ────────────────────────────────────────

class TestBendelProtonCrossSection(unittest.TestCase):

    def test_below_threshold_returns_zero(self):
        self.assertEqual(bendel_proton_cross_section(10.0, 50.0, 1e-8), 0.0)

    def test_at_threshold_returns_zero(self):
        self.assertEqual(bendel_proton_cross_section(50.0, 50.0, 1e-8), 0.0)

    def test_above_threshold_returns_positive(self):
        sigma = bendel_proton_cross_section(200.0, 20.0, 1e-8)
        self.assertGreater(sigma, 0.0)

    def test_monotonically_increasing_with_energy(self):
        energies = [25.0, 50.0, 100.0, 200.0, 500.0]
        A, B = 20.0, 1e-8
        sigmas = [bendel_proton_cross_section(e, A, B) for e in energies]
        for i in range(len(sigmas) - 1):
            self.assertLess(sigmas[i], sigmas[i + 1])

    def test_never_exceeds_B(self):
        B = 1e-8
        sigma = bendel_proton_cross_section(1e6, 20.0, B)
        self.assertLessEqual(sigma, B)

    def test_invalid_A_raises(self):
        with self.assertRaises(ValueError):
            bendel_proton_cross_section(100.0, 0.0, 1e-8)

    def test_invalid_B_raises(self):
        with self.assertRaises(ValueError):
            bendel_proton_cross_section(100.0, 20.0, 0.0)

    def test_negative_A_raises(self):
        with self.assertRaises(ValueError):
            bendel_proton_cross_section(100.0, -5.0, 1e-8)


# ── Proton rate integration tests ─────────────────────────────────────────────

class TestProtonSELRate(unittest.TestCase):

    def test_zero_rate_when_spectrum_below_threshold(self):
        spec = _energy_spectrum(5.0, 15.0, 5, 1e5)
        rate = proton_sel_rate(spec, 20.0, 1e-8)
        self.assertAlmostEqual(rate, 0.0, places=20)

    def test_positive_rate_when_spectrum_above_threshold(self):
        spec = _energy_spectrum(50.0, 500.0, 20, 1e5)
        rate = proton_sel_rate(spec, 20.0, 1e-8)
        self.assertGreater(rate, 0.0)

    def test_empty_spectrum_raises(self):
        with self.assertRaises(ValueError):
            proton_sel_rate([], 20.0, 1e-8)

    def test_invalid_A_raises(self):
        spec = _energy_spectrum(50.0, 200.0, 5, 1e5)
        with self.assertRaises(ValueError):
            proton_sel_rate(spec, 0.0, 1e-8)

    def test_invalid_B_raises(self):
        spec = _energy_spectrum(50.0, 200.0, 5, 1e5)
        with self.assertRaises(ValueError):
            proton_sel_rate(spec, 20.0, -1.0)


# ── Severity categorization tests ────────────────────────────────────────────

class TestCategorize(unittest.TestCase):

    def test_zero_rate_is_acceptable(self):
        self.assertEqual(categorize_sel_rate(0.0), "acceptable")

    def test_just_below_acceptable_threshold(self):
        self.assertEqual(categorize_sel_rate(SEL_RATE_ACCEPTABLE * 0.5), "acceptable")

    def test_at_acceptable_threshold_is_monitor(self):
        self.assertEqual(categorize_sel_rate(SEL_RATE_ACCEPTABLE), "monitor")

    def test_midpoint_is_monitor(self):
        mid = (SEL_RATE_ACCEPTABLE + SEL_RATE_MONITOR) / 2.0
        self.assertEqual(categorize_sel_rate(mid), "monitor")

    def test_at_monitor_threshold_is_critical(self):
        self.assertEqual(categorize_sel_rate(SEL_RATE_MONITOR), "critical")

    def test_above_monitor_threshold_is_critical(self):
        self.assertEqual(categorize_sel_rate(SEL_RATE_MONITOR * 100.0), "critical")

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            categorize_sel_rate(-1.0e-6)


# ── Full assessment tests ─────────────────────────────────────────────────────

class TestAssessSEL(unittest.TestCase):

    def _hi(self):
        return _let_spectrum(1.0, 100.0, 50, 5e3)

    def _pr(self):
        return _energy_spectrum(20.0, 500.0, 50, 1e5)

    def test_returns_assessment_dataclass(self):
        result = assess_sel("DEV-A", self._hi(), 5.0, 1e-6, 10.0, 1.5,
                            self._pr(), 30.0, 1e-9)
        self.assertIsInstance(result, SELAssessment)
        self.assertEqual(result.device_id, "DEV-A")

    def test_combined_rate_equals_sum_of_parts(self):
        result = assess_sel("DEV-B", self._hi(), 5.0, 1e-6, 10.0, 1.5,
                            self._pr(), 30.0, 1e-9)
        self.assertAlmostEqual(
            result.combined_rate,
            result.heavy_ion_rate + result.proton_rate,
            places=15,
        )

    def test_severity_is_valid_string(self):
        result = assess_sel("DEV-C", self._hi(), 5.0, 1e-6, 10.0, 1.5,
                            self._pr(), 30.0, 1e-9)
        self.assertIn(result.severity, ("acceptable", "monitor", "critical"))

    def test_critical_device_carries_critical_flag(self):
        hi_heavy = _let_spectrum(0.1, 100.0, 50, 1e10)
        pr_heavy = _energy_spectrum(10.0, 500.0, 50, 1e10)
        result = assess_sel("DEV-CRIT", hi_heavy, 0.05, 1e-3, 1.0, 1.0,
                            pr_heavy, 5.0, 1e-5)
        self.assertEqual(result.severity, "critical")
        self.assertTrue(any("CRITICAL" in f for f in result.flags))

    def test_empty_device_id_raises(self):
        with self.assertRaises(ValueError):
            assess_sel("", self._hi(), 5.0, 1e-6, 10.0, 1.5,
                       self._pr(), 30.0, 1e-9)

    def test_whitespace_only_device_id_raises(self):
        with self.assertRaises(ValueError):
            assess_sel("   ", self._hi(), 5.0, 1e-6, 10.0, 1.5,
                       self._pr(), 30.0, 1e-9)

    def test_zero_rate_produces_zero_combined_rate(self):
        hi_lo = _let_spectrum(0.1, 0.5, 5, 1e3)
        pr_lo = _energy_spectrum(1.0, 9.0, 5, 1e5)
        result = assess_sel("DEV-ZERO", hi_lo, 1.0, 1e-6, 5.0, 1.0,
                            pr_lo, 10.0, 1e-9)
        self.assertAlmostEqual(result.combined_rate, 0.0, places=20)
        self.assertEqual(result.severity, "acceptable")

    def test_zero_rate_triggers_zero_rate_flag(self):
        hi_lo = _let_spectrum(0.1, 0.5, 5, 1e3)
        pr_lo = _energy_spectrum(1.0, 9.0, 5, 1e5)
        result = assess_sel("DEV-ZERO2", hi_lo, 1.0, 1e-6, 5.0, 1.0,
                            pr_lo, 10.0, 1e-9)
        self.assertTrue(any("zero" in f for f in result.flags))

    def test_heavy_ion_dominance_flag_raised(self):
        hi_dom = _let_spectrum(1.0, 100.0, 50, 1e8)
        pr_min = _energy_spectrum(20.0, 500.0, 5, 1e-3)
        result = assess_sel("DEV-HI-DOM", hi_dom, 0.5, 1e-5, 2.0, 1.0,
                            pr_min, 200.0, 1e-12)
        if result.heavy_ion_rate > 0.0 and result.proton_rate > 0.0:
            if result.heavy_ion_rate > result.proton_rate * 10.0:
                self.assertTrue(any("heavy-ion dominated" in f for f in result.flags))

    def test_flags_is_list(self):
        result = assess_sel("DEV-D", self._hi(), 5.0, 1e-6, 10.0, 1.5,
                            self._pr(), 30.0, 1e-9)
        self.assertIsInstance(result.flags, list)


if __name__ == "__main__":
    unittest.main()
