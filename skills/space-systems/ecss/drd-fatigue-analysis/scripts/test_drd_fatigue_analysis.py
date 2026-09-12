"""
Gate 3 contract tests for drd_fatigue_analysis_logic.py.
Stdlib unittest only. Deterministic, offline.
Run: python3 test_drd_fatigue_analysis.py
"""

import math
import os
import sys
import unittest

# Ensure the scripts directory is on the path regardless of working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from drd_fatigue_analysis_logic import (
    FatigueSpectrum,
    FatigueResult,
    LoadCycle,
    SNPoint,
    apply_scatter_factor,
    assess_fatigue_location,
    categorize_loading,
    compute_life_from_damage,
    compute_life_margin,
    compute_miner_damage,
    count_cycles_from_peaks,
    interpolate_sn_curve,
    validate_sn_curve,
    validate_spectrum,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _sn_two_point():
    """Simple two-point S-N curve: 200 MPa -> 1 000 cycles, 100 MPa -> 1 000 000 cycles."""
    return [
        SNPoint(stress_amplitude=200.0, allowable_cycles=1_000.0),
        SNPoint(stress_amplitude=100.0, allowable_cycles=1_000_000.0),
    ]


def _make_spectrum(name, *cycle_tuples):
    """Build a FatigueSpectrum from (amplitude, mean, count) tuples."""
    cycles = tuple(
        LoadCycle(stress_amplitude=a, mean_stress=m, count=n)
        for a, m, n in cycle_tuples
    )
    return FatigueSpectrum(name=name, cycles=cycles)


# ---------------------------------------------------------------------------
# validate_spectrum
# ---------------------------------------------------------------------------

class TestValidateSpectrum(unittest.TestCase):

    def test_empty_spectrum_is_valid(self):
        sp = FatigueSpectrum(name="empty", cycles=())
        validate_spectrum(sp)  # must not raise

    def test_valid_spectrum_passes(self):
        sp = _make_spectrum("ok", (100.0, 0.0, 500.0))
        validate_spectrum(sp)  # must not raise

    def test_negative_amplitude_raises(self):
        sp = _make_spectrum("bad", (-10.0, 0.0, 100.0))
        with self.assertRaises(ValueError):
            validate_spectrum(sp)

    def test_negative_count_raises(self):
        sp = _make_spectrum("bad", (50.0, 0.0, -1.0))
        with self.assertRaises(ValueError):
            validate_spectrum(sp)

    def test_zero_amplitude_and_zero_count_are_valid(self):
        sp = _make_spectrum("zeros", (0.0, 0.0, 0.0))
        validate_spectrum(sp)  # must not raise


# ---------------------------------------------------------------------------
# categorize_loading
# ---------------------------------------------------------------------------

class TestCategorizeLoading(unittest.TestCase):

    def test_empty_spectrum_is_constant_amplitude(self):
        sp = FatigueSpectrum(name="empty", cycles=())
        self.assertEqual(categorize_loading(sp), "constant_amplitude")

    def test_single_amplitude_level_is_constant(self):
        sp = _make_spectrum("ca", (150.0, 0.0, 1000.0), (150.0, 0.0, 500.0))
        self.assertEqual(categorize_loading(sp), "constant_amplitude")

    def test_multiple_non_zero_levels_is_variable_amplitude(self):
        sp = _make_spectrum("va", (200.0, 0.0, 100.0), (100.0, 0.0, 500.0))
        self.assertEqual(categorize_loading(sp), "variable_amplitude")

    def test_non_zero_plus_rest_block_is_combined(self):
        sp = _make_spectrum("comb", (150.0, 0.0, 300.0), (0.0, 0.0, 200.0))
        self.assertEqual(categorize_loading(sp), "combined")

    def test_all_zero_amplitude_blocks_is_constant(self):
        sp = _make_spectrum("zeros", (0.0, 0.0, 100.0), (0.0, 0.0, 50.0))
        self.assertEqual(categorize_loading(sp), "constant_amplitude")


# ---------------------------------------------------------------------------
# count_cycles_from_peaks
# ---------------------------------------------------------------------------

class TestCountCyclesFromPeaks(unittest.TestCase):

    def test_empty_peaks_returns_empty(self):
        self.assertEqual(count_cycles_from_peaks([]), [])

    def test_single_peak_returns_empty(self):
        self.assertEqual(count_cycles_from_peaks([100.0]), [])

    def test_two_peaks_produce_one_half_cycle(self):
        cycles = count_cycles_from_peaks([200.0, 0.0])
        self.assertEqual(len(cycles), 1)
        self.assertAlmostEqual(cycles[0].stress_amplitude, 100.0)
        self.assertAlmostEqual(cycles[0].mean_stress, 100.0)
        self.assertAlmostEqual(cycles[0].count, 0.5)

    def test_three_peaks_produce_two_half_cycles(self):
        cycles = count_cycles_from_peaks([0.0, 200.0, 0.0])
        self.assertEqual(len(cycles), 2)
        for c in cycles:
            self.assertAlmostEqual(c.stress_amplitude, 100.0)
            self.assertAlmostEqual(c.count, 0.5)

    def test_amplitude_is_half_range(self):
        cycles = count_cycles_from_peaks([300.0, 100.0])
        self.assertAlmostEqual(cycles[0].stress_amplitude, 100.0)   # |300-100|/2

    def test_mean_stress_is_midpoint(self):
        cycles = count_cycles_from_peaks([300.0, 100.0])
        self.assertAlmostEqual(cycles[0].mean_stress, 200.0)        # (300+100)/2


# ---------------------------------------------------------------------------
# validate_sn_curve / interpolate_sn_curve
# ---------------------------------------------------------------------------

class TestSNCurve(unittest.TestCase):

    def test_single_point_sn_raises_on_validate(self):
        with self.assertRaises(ValueError):
            validate_sn_curve([SNPoint(100.0, 1e6)])

    def test_zero_amplitude_point_raises(self):
        with self.assertRaises(ValueError):
            validate_sn_curve([
                SNPoint(0.0, 1e6),
                SNPoint(200.0, 1e3),
            ])

    def test_exact_match_lower_point(self):
        n = interpolate_sn_curve(100.0, _sn_two_point())
        self.assertAlmostEqual(n, 1_000_000.0, places=0)

    def test_exact_match_upper_point(self):
        n = interpolate_sn_curve(200.0, _sn_two_point())
        self.assertAlmostEqual(n, 1_000.0, places=0)

    def test_interpolation_midpoint_log_log(self):
        # Midpoint in log-log space between (200, 1e3) and (100, 1e6)
        # log10(150) ~= 2.176, slope in log-log from these two points:
        # d_log_n / d_log_s = (log10(1e3)-log10(1e6)) / (log10(200)-log10(100))
        #                    = (-3) / (0.301) = -9.966
        # At s=150: log_n = log10(1e6) + slope*(log10(150)-log10(100))
        sn = _sn_two_point()
        n = interpolate_sn_curve(150.0, sn)
        self.assertGreater(n, 1_000.0)
        self.assertLess(n, 1_000_000.0)

    def test_extrapolation_above_range_returns_lower_allowable(self):
        # 400 MPa is higher stress than 200 MPa -> fewer allowable cycles
        n_high = interpolate_sn_curve(400.0, _sn_two_point())
        n_ref = interpolate_sn_curve(200.0, _sn_two_point())
        self.assertLess(n_high, n_ref)

    def test_extrapolation_below_range_returns_higher_allowable(self):
        # 50 MPa is lower stress than 100 MPa -> more allowable cycles
        n_low = interpolate_sn_curve(50.0, _sn_two_point())
        n_ref = interpolate_sn_curve(100.0, _sn_two_point())
        self.assertGreater(n_low, n_ref)

    def test_non_positive_amplitude_raises(self):
        with self.assertRaises(ValueError):
            interpolate_sn_curve(0.0, _sn_two_point())


# ---------------------------------------------------------------------------
# compute_miner_damage
# ---------------------------------------------------------------------------

class TestComputeMinerDamage(unittest.TestCase):

    def test_empty_spectrum_returns_zero_damage(self):
        sp = FatigueSpectrum(name="empty", cycles=())
        d = compute_miner_damage(sp, _sn_two_point())
        self.assertAlmostEqual(d, 0.0)

    def test_single_block_damage_equals_n_over_N(self):
        # 500 cycles at 200 MPa; N(200) = 1 000 -> D = 500/1000 = 0.5
        sp = _make_spectrum("s1", (200.0, 0.0, 500.0))
        d = compute_miner_damage(sp, _sn_two_point())
        self.assertAlmostEqual(d, 0.5, places=6)

    def test_two_blocks_damage_sums_correctly(self):
        # 500 @ 200 MPa (D1=0.5) + 500_000 @ 100 MPa (D2=0.5) -> D=1.0
        sp = _make_spectrum("s2", (200.0, 0.0, 500.0), (100.0, 0.0, 500_000.0))
        d = compute_miner_damage(sp, _sn_two_point())
        self.assertAlmostEqual(d, 1.0, places=6)

    def test_zero_amplitude_cycle_contributes_no_damage(self):
        sp = _make_spectrum("zero_amp", (200.0, 0.0, 500.0), (0.0, 0.0, 999_999.0))
        d_with_rest = compute_miner_damage(sp, _sn_two_point())
        sp_no_rest = _make_spectrum("no_rest", (200.0, 0.0, 500.0))
        d_no_rest = compute_miner_damage(sp_no_rest, _sn_two_point())
        self.assertAlmostEqual(d_with_rest, d_no_rest, places=9)

    def test_zero_count_cycle_contributes_no_damage(self):
        sp = _make_spectrum("zc", (200.0, 0.0, 0.0))
        d = compute_miner_damage(sp, _sn_two_point())
        self.assertAlmostEqual(d, 0.0)


# ---------------------------------------------------------------------------
# apply_scatter_factor
# ---------------------------------------------------------------------------

class TestApplyScatterFactor(unittest.TestCase):

    def test_basic_division(self):
        result = apply_scatter_factor(40_000.0, 4.0)
        self.assertAlmostEqual(result, 10_000.0)

    def test_scatter_factor_one_returns_same_life(self):
        self.assertAlmostEqual(apply_scatter_factor(1_000.0, 1.0), 1_000.0)

    def test_zero_predicted_life_returns_zero(self):
        self.assertAlmostEqual(apply_scatter_factor(0.0, 4.0), 0.0)

    def test_negative_scatter_factor_raises(self):
        with self.assertRaises(ValueError):
            apply_scatter_factor(1_000.0, -1.0)

    def test_zero_scatter_factor_raises(self):
        with self.assertRaises(ValueError):
            apply_scatter_factor(1_000.0, 0.0)


# ---------------------------------------------------------------------------
# compute_life_from_damage
# ---------------------------------------------------------------------------

class TestComputeLifeFromDamage(unittest.TestCase):

    def test_zero_damage_returns_infinity(self):
        life = compute_life_from_damage(0.0, 1_000.0)
        self.assertTrue(math.isinf(life))

    def test_damage_one_equals_applied_cycles(self):
        life = compute_life_from_damage(1.0, 5_000.0)
        self.assertAlmostEqual(life, 5_000.0)

    def test_damage_half_doubles_life(self):
        life = compute_life_from_damage(0.5, 5_000.0)
        self.assertAlmostEqual(life, 10_000.0)

    def test_negative_damage_raises(self):
        with self.assertRaises(ValueError):
            compute_life_from_damage(-0.1, 1_000.0)


# ---------------------------------------------------------------------------
# compute_life_margin
# ---------------------------------------------------------------------------

class TestComputeLifeMargin(unittest.TestCase):

    def test_adjusted_equals_required_gives_zero_margin(self):
        self.assertAlmostEqual(compute_life_margin(1_000.0, 1_000.0), 0.0)

    def test_positive_margin_when_life_exceeds_requirement(self):
        margin = compute_life_margin(2_000.0, 1_000.0)
        self.assertGreater(margin, 0.0)
        self.assertAlmostEqual(margin, 1.0)

    def test_negative_margin_when_life_below_requirement(self):
        margin = compute_life_margin(500.0, 1_000.0)
        self.assertLess(margin, 0.0)
        self.assertAlmostEqual(margin, -0.5)

    def test_non_positive_required_life_raises(self):
        with self.assertRaises(ValueError):
            compute_life_margin(1_000.0, 0.0)


# ---------------------------------------------------------------------------
# assess_fatigue_location (full workflow)
# ---------------------------------------------------------------------------

class TestAssessFatigueLocation(unittest.TestCase):

    def _compliant_spectrum(self):
        # 100 cycles at 200 MPa; N=1000 -> D=0.1, life=1000 cycles,
        # adjusted life = 1000/4 = 250 cycles; required = 100 -> margin = 1.5 (positive)
        return _make_spectrum("loc1", (200.0, 0.0, 100.0))

    def _noncompliant_spectrum(self):
        # 900 cycles at 200 MPa; N=1000 -> D=0.9, life=1000 cycles,
        # adjusted life = 1000/4 = 250 cycles; required = 1000 -> margin < 0
        return _make_spectrum("loc2", (200.0, 0.0, 900.0))

    def test_compliant_location_returns_positive_margin(self):
        result = assess_fatigue_location(
            "bracket_A", self._compliant_spectrum(), _sn_two_point(),
            required_life=100.0, scatter_factor=4.0
        )
        self.assertIsInstance(result, FatigueResult)
        self.assertTrue(result.compliant)
        self.assertGreaterEqual(result.margin, 0.0)

    def test_noncompliant_location_returns_negative_margin(self):
        result = assess_fatigue_location(
            "bracket_B", self._noncompliant_spectrum(), _sn_two_point(),
            required_life=1_000.0, scatter_factor=4.0
        )
        self.assertFalse(result.compliant)
        self.assertLess(result.margin, 0.0)

    def test_result_fields_are_consistent(self):
        sp = self._compliant_spectrum()
        r = assess_fatigue_location(
            "flange", sp, _sn_two_point(),
            required_life=100.0, scatter_factor=4.0
        )
        expected_adjusted = r.life_cycles / 4.0
        self.assertAlmostEqual(r.adjusted_life, expected_adjusted, places=6)
        expected_margin = (r.adjusted_life / 100.0) - 1.0
        self.assertAlmostEqual(r.margin, expected_margin, places=6)

    def test_zero_damage_spectrum_gives_infinite_life(self):
        sp = FatigueSpectrum(name="zero", cycles=())
        r = assess_fatigue_location(
            "idle_bracket", sp, _sn_two_point(),
            required_life=1_000.0, scatter_factor=4.0
        )
        self.assertTrue(math.isinf(r.life_cycles))
        self.assertTrue(r.compliant)

    def test_invalid_required_life_raises(self):
        sp = self._compliant_spectrum()
        with self.assertRaises(ValueError):
            assess_fatigue_location(
                "loc", sp, _sn_two_point(),
                required_life=0.0, scatter_factor=4.0
            )

    def test_invalid_scatter_factor_raises(self):
        sp = self._compliant_spectrum()
        with self.assertRaises(ValueError):
            assess_fatigue_location(
                "loc", sp, _sn_two_point(),
                required_life=100.0, scatter_factor=0.0
            )

    def test_location_name_preserved_in_result(self):
        sp = self._compliant_spectrum()
        r = assess_fatigue_location(
            "rib_web_7", sp, _sn_two_point(),
            required_life=100.0, scatter_factor=4.0
        )
        self.assertEqual(r.location, "rib_web_7")

    def test_scatter_factor_four_applied_correctly(self):
        # 250 cycles at 200 MPa -> D=0.25, life=250/0.25=1000
        # adjusted = 1000/4 = 250
        sp = _make_spectrum("sf4", (200.0, 0.0, 250.0))
        r = assess_fatigue_location(
            "test_loc", sp, _sn_two_point(),
            required_life=1_000.0, scatter_factor=4.0
        )
        self.assertAlmostEqual(r.adjusted_life, 250.0, places=4)
        self.assertAlmostEqual(r.scatter_factor, 4.0)


if __name__ == "__main__":
    unittest.main()
