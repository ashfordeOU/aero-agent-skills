"""
Contract test for strength_functionality_logic.py
ECSS-E-ST-32C clause 4.3.2 — strength functionality.

stdlib unittest; deterministic; offline.
Run: python3 test_strength_functionality.py
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from strength_functionality_logic import (
    DEFAULT_FOS_ULTIMATE,
    DEFAULT_FOS_YIELD,
    StressState,
    StrengthCheck,
    assess_all_levels,
    assess_strength,
    compute_dul,
    compute_dyl,
    margin_of_safety,
    von_mises_stress,
)


class TestVonMisesStress(unittest.TestCase):
    """Von Mises equivalent stress computation."""

    def test_uniaxial_tension(self):
        """Pure uniaxial σx → σ_vm equals |σx|."""
        s = StressState(sigma_x=100.0)
        self.assertAlmostEqual(von_mises_stress(s), 100.0)

    def test_uniaxial_compression(self):
        """Negative σx still yields positive von Mises stress."""
        s = StressState(sigma_x=-200.0)
        self.assertAlmostEqual(von_mises_stress(s), 200.0)

    def test_pure_shear(self):
        """Pure shear τxy → σ_vm = τxy × sqrt(3)."""
        tau = 80.0
        s = StressState(tau_xy=tau)
        self.assertAlmostEqual(von_mises_stress(s), tau * math.sqrt(3), places=10)

    def test_biaxial_equal_tension(self):
        """Equal biaxial σx = σy → σ_vm = |σx|."""
        s = StressState(sigma_x=150.0, sigma_y=150.0)
        self.assertAlmostEqual(von_mises_stress(s), 150.0)

    def test_triaxial_hydrostatic(self):
        """Hydrostatic state σx=σy=σz → σ_vm = 0 (no deviatoric component)."""
        s = StressState(sigma_x=200.0, sigma_y=200.0, sigma_z=200.0)
        self.assertAlmostEqual(von_mises_stress(s), 0.0, places=10)

    def test_zero_stress(self):
        """All-zero stress tensor → σ_vm = 0."""
        self.assertAlmostEqual(von_mises_stress(StressState()), 0.0)


class TestDesignLoads(unittest.TestCase):
    """DYL and DUL scaling from limit load."""

    def test_dyl_default_fos(self):
        """DYL = limit × DEFAULT_FOS_YIELD."""
        self.assertAlmostEqual(compute_dyl(1000.0), 1000.0 * DEFAULT_FOS_YIELD)

    def test_dul_default_fos(self):
        """DUL = limit × DEFAULT_FOS_ULTIMATE."""
        self.assertAlmostEqual(compute_dul(1000.0), 1000.0 * DEFAULT_FOS_ULTIMATE)

    def test_dyl_custom_fos(self):
        """DYL uses the supplied factor of safety."""
        self.assertAlmostEqual(compute_dyl(500.0, 1.25), 625.0)

    def test_dul_custom_fos(self):
        """DUL uses the supplied factor of safety."""
        self.assertAlmostEqual(compute_dul(500.0, 2.0), 1000.0)

    def test_dyl_invalid_fos_raises(self):
        """Non-positive fos_yield must raise ValueError."""
        with self.assertRaises(ValueError):
            compute_dyl(1000.0, fos_yield=0.0)

    def test_dul_invalid_fos_raises(self):
        """Non-positive fos_ultimate must raise ValueError."""
        with self.assertRaises(ValueError):
            compute_dul(1000.0, fos_ultimate=-1.0)

    def test_dyl_dul_ordering(self):
        """DUL must exceed DYL for any positive limit load (default FoS)."""
        ll = 800.0
        self.assertGreater(compute_dul(ll), compute_dyl(ll))


class TestMarginOfSafety(unittest.TestCase):
    """Margin of safety arithmetic."""

    def test_positive_mos(self):
        """Allowable exceeds applied → positive MoS."""
        mos = margin_of_safety(300.0, 200.0)
        self.assertAlmostEqual(mos, 0.5)

    def test_zero_mos(self):
        """Allowable equals applied → MoS exactly zero."""
        mos = margin_of_safety(250.0, 250.0)
        self.assertAlmostEqual(mos, 0.0)

    def test_negative_mos(self):
        """Applied exceeds allowable → negative MoS (non-compliance)."""
        mos = margin_of_safety(100.0, 120.0)
        self.assertLess(mos, 0.0)

    def test_zero_applied_raises(self):
        """Zero applied stress is undefined for MoS and must raise ValueError."""
        with self.assertRaises(ValueError):
            margin_of_safety(300.0, 0.0)


class TestAssessStrength(unittest.TestCase):
    """Single assembly-level strength assessment."""

    def _passing_check(self, level="component"):
        """Return a StrengthCheck that passes both yield and ultimate gates."""
        return StrengthCheck(
            assembly_level=level,
            limit_load=1000.0,
            stress_at_dyl=StressState(sigma_x=100.0),   # vm = 100 MPa
            stress_at_dul=StressState(sigma_x=130.0),   # vm = 130 MPa
            yield_strength=200.0,   # MoS_yield  = 200/100 - 1 = 1.0
            ultimate_strength=300.0,  # MoS_ult = 300/130 - 1 ≈ 1.31
        )

    def test_compliant_component(self):
        """A component-level check with ample margin must be compliant."""
        result = assess_strength(self._passing_check("component"))
        self.assertTrue(result.compliant)
        self.assertTrue(result.yield_pass)
        self.assertTrue(result.ultimate_pass)
        self.assertGreaterEqual(result.mos_yield, 0.0)
        self.assertGreaterEqual(result.mos_ultimate, 0.0)

    def test_compliant_subsystem(self):
        """Subsystem-level check passes."""
        result = assess_strength(self._passing_check("subsystem"))
        self.assertTrue(result.compliant)

    def test_compliant_system(self):
        """System-level check passes."""
        result = assess_strength(self._passing_check("system"))
        self.assertTrue(result.compliant)

    def test_dyl_and_dul_values(self):
        """Reported DYL and DUL match expected scaling."""
        check = self._passing_check()
        result = assess_strength(check)
        self.assertAlmostEqual(result.dyl, 1000.0 * DEFAULT_FOS_YIELD)
        self.assertAlmostEqual(result.dul, 1000.0 * DEFAULT_FOS_ULTIMATE)

    def test_yield_failure(self):
        """Stress at DYL above yield strength → yield_pass is False."""
        check = StrengthCheck(
            assembly_level="component",
            limit_load=1000.0,
            stress_at_dyl=StressState(sigma_x=250.0),  # vm = 250 > yield 200
            stress_at_dul=StressState(sigma_x=280.0),
            yield_strength=200.0,
            ultimate_strength=350.0,
        )
        result = assess_strength(check)
        self.assertFalse(result.yield_pass)
        self.assertFalse(result.compliant)
        self.assertLess(result.mos_yield, 0.0)

    def test_ultimate_failure(self):
        """Stress at DUL above ultimate strength → ultimate_pass is False."""
        check = StrengthCheck(
            assembly_level="subsystem",
            limit_load=1000.0,
            stress_at_dyl=StressState(sigma_x=150.0),  # vm = 150 < yield 200 → pass
            stress_at_dul=StressState(sigma_x=400.0),  # vm = 400 > ult 350 → fail
            yield_strength=200.0,
            ultimate_strength=350.0,
        )
        result = assess_strength(check)
        self.assertTrue(result.yield_pass)
        self.assertFalse(result.ultimate_pass)
        self.assertFalse(result.compliant)

    def test_invalid_assembly_level(self):
        """An unrecognized assembly level must raise ValueError."""
        check = self._passing_check()
        check.assembly_level = "widget"
        with self.assertRaises(ValueError):
            assess_strength(check)

    def test_ultimate_below_yield_raises(self):
        """ultimate_strength < yield_strength is physically invalid."""
        check = self._passing_check()
        check.ultimate_strength = check.yield_strength - 10.0
        with self.assertRaises(ValueError):
            assess_strength(check)

    def test_zero_limit_load_raises(self):
        """Zero limit load is not a valid structural check input."""
        check = self._passing_check()
        check.limit_load = 0.0
        with self.assertRaises(ValueError):
            assess_strength(check)


class TestAssessAllLevels(unittest.TestCase):
    """Multi-level assessment across the full assembly hierarchy."""

    def _make_check(self, level, vm_dyl, vm_dul, fy=200.0, fu=350.0):
        return StrengthCheck(
            assembly_level=level,
            limit_load=1000.0,
            stress_at_dyl=StressState(sigma_x=vm_dyl),
            stress_at_dul=StressState(sigma_x=vm_dul),
            yield_strength=fy,
            ultimate_strength=fu,
        )

    def test_all_levels_pass(self):
        """All three assembly levels passing → overall compliant."""
        checks = [
            self._make_check("component", 100.0, 130.0),
            self._make_check("subsystem", 110.0, 140.0),
            self._make_check("system", 120.0, 150.0),
        ]
        results, overall = assess_all_levels(checks)
        self.assertEqual(len(results), 3)
        self.assertTrue(overall)
        self.assertTrue(all(r.compliant for r in results))

    def test_one_level_fails_overall(self):
        """One failing level makes the overall result non-compliant."""
        checks = [
            self._make_check("component", 100.0, 130.0),
            self._make_check("subsystem", 250.0, 300.0),  # DYL stress > yield 200
            self._make_check("system", 120.0, 150.0),
        ]
        results, overall = assess_all_levels(checks)
        self.assertFalse(overall)
        self.assertFalse(results[1].yield_pass)
        self.assertTrue(results[0].compliant)
        self.assertTrue(results[2].compliant)

    def test_empty_checks_raises(self):
        """Passing an empty list must raise ValueError."""
        with self.assertRaises(ValueError):
            assess_all_levels([])

    def test_result_count_matches_input(self):
        """Number of results equals number of input checks."""
        checks = [
            self._make_check("component", 90.0, 120.0),
            self._make_check("system", 95.0, 125.0),
        ]
        results, _ = assess_all_levels(checks)
        self.assertEqual(len(results), len(checks))


if __name__ == "__main__":
    unittest.main()
