"""
Offline deterministic tests for cops_nonmetallic_liner_and_cps_logic.py.
stdlib unittest only — no network, no external dependencies.
Run: python3 test_cops_nonmetallic_liner_and_cps.py
"""

import sys
import os
import unittest

# Allow import from sibling scripts/ directory when run directly.
sys.path.insert(0, os.path.dirname(__file__))

from cops_nonmetallic_liner_and_cps_logic import (
    SystemVariant,
    PressureSystemInput,
    AssessmentResult,
    FindingItem,
    assess_system,
    check_proof_margin,
    check_burst_margin,
    check_cycle_life,
    check_fracture_control,
    check_liner_permeation,
    check_liner_buckling,
    burst_margin_ratio,
    proof_margin_ratio,
    PROOF_FACTOR,
    BURST_FACTOR,
    CYCLE_LIFE_FACTOR,
)


def _make_cops_nml_compliant(**overrides) -> PressureSystemInput:
    """Return a fully-compliant COPS non-metallic liner input."""
    defaults = dict(
        variant=SystemVariant.COPS_NONMETALLIC_LINER,
        meop_mpa=20.0,
        proof_pressure_mpa=22.5,       # 1.125 × 20 >= 1.1 × 20 = 22.0
        burst_pressure_predicted_mpa=42.0,  # 2.1 × 20 >= 2.0 × 20 = 40.0
        design_cycles=50,
        qualified_cycles=210,           # 4.2 × 50 >= 4 × 50 = 200
        lbb_demonstrated=True,
        safe_life_approach=False,
        permeation_rate_cc_per_s=1e-6,
        allowable_permeation_cc_per_s=5e-6,
        liner_buckling_ratio=2.5,
    )
    defaults.update(overrides)
    return PressureSystemInput(**defaults)


def _make_cps_compliant(**overrides) -> PressureSystemInput:
    """Return a fully-compliant all-composite CPS input."""
    defaults = dict(
        variant=SystemVariant.ALL_COMPOSITE_CPS,
        meop_mpa=15.0,
        proof_pressure_mpa=17.0,       # 1.133 × 15 >= 1.1 × 15 = 16.5
        burst_pressure_predicted_mpa=32.0,  # 2.13 × 15 >= 2.0 × 15 = 30.0
        design_cycles=30,
        qualified_cycles=125,           # 4.17 × 30 >= 4 × 30 = 120
        lbb_demonstrated=True,
        safe_life_approach=False,
    )
    defaults.update(overrides)
    return PressureSystemInput(**defaults)


class TestCopsNmlCompliantItem(unittest.TestCase):

    def test_cops_nml_all_checks_pass(self):
        result = assess_system(_make_cops_nml_compliant())
        self.assertTrue(result.compliant)
        self.assertEqual(len(result.fails()), 0)

    def test_cops_nml_variant_label(self):
        result = assess_system(_make_cops_nml_compliant())
        self.assertEqual(result.variant, "cops_nonmetallic_liner")

    def test_cops_nml_six_findings_produced(self):
        result = assess_system(_make_cops_nml_compliant())
        # proof, burst, cycle_life, fracture_control, liner_permeation, liner_buckling
        self.assertEqual(len(result.findings), 6)


class TestProofPressureCheck(unittest.TestCase):

    def test_proof_insufficient_fails(self):
        inp = _make_cops_nml_compliant(proof_pressure_mpa=21.0)  # < 22.0
        result = assess_system(inp)
        self.assertFalse(result.compliant)
        fail_checks = [f.check for f in result.fails()]
        self.assertIn("proof_pressure", fail_checks)

    def test_proof_exactly_at_threshold_passes(self):
        meop = 20.0
        proof = meop * PROOF_FACTOR  # exactly 22.0
        result = check_proof_margin(meop, proof)
        self.assertEqual(result.status, "PASS")

    def test_proof_margin_ratio_above_one_is_compliant(self):
        ratio = proof_margin_ratio(20.0, 25.0)
        self.assertGreater(ratio, 1.0)

    def test_proof_margin_ratio_below_one_is_deficient(self):
        ratio = proof_margin_ratio(20.0, 21.0)
        self.assertLess(ratio, 1.0)


class TestBurstPressureCheck(unittest.TestCase):

    def test_burst_insufficient_fails(self):
        inp = _make_cops_nml_compliant(burst_pressure_predicted_mpa=38.0)  # < 40.0
        result = assess_system(inp)
        self.assertFalse(result.compliant)
        fail_checks = [f.check for f in result.fails()]
        self.assertIn("burst_pressure", fail_checks)

    def test_burst_exactly_at_threshold_passes(self):
        meop = 20.0
        burst = meop * BURST_FACTOR  # exactly 40.0
        result = check_burst_margin(meop, burst)
        self.assertEqual(result.status, "PASS")

    def test_burst_margin_ratio_helper(self):
        ratio = burst_margin_ratio(20.0, 40.0)
        self.assertAlmostEqual(ratio, 1.0)


class TestCycleLifeCheck(unittest.TestCase):

    def test_cycle_life_insufficient_fails(self):
        inp = _make_cops_nml_compliant(design_cycles=50, qualified_cycles=190)
        result = assess_system(inp)
        fail_checks = [f.check for f in result.fails()]
        self.assertIn("cycle_life", fail_checks)

    def test_cycle_life_exactly_at_factor_passes(self):
        result = check_cycle_life(design_cycles=50, qualified_cycles=200)
        self.assertEqual(result.status, "PASS")

    def test_cycle_life_factor_is_four(self):
        self.assertEqual(CYCLE_LIFE_FACTOR, 4)


class TestFractureControlCheck(unittest.TestCase):

    def test_neither_lbb_nor_safe_life_fails(self):
        inp = _make_cops_nml_compliant(lbb_demonstrated=False, safe_life_approach=False)
        result = assess_system(inp)
        fail_checks = [f.check for f in result.fails()]
        self.assertIn("fracture_control", fail_checks)

    def test_safe_life_alone_passes(self):
        result = check_fracture_control(lbb_demonstrated=False, safe_life_approach=True)
        self.assertEqual(result.status, "PASS")
        self.assertIn("safe-life", result.detail)

    def test_lbb_demonstrated_passes(self):
        result = check_fracture_control(lbb_demonstrated=True, safe_life_approach=False)
        self.assertEqual(result.status, "PASS")

    def test_both_lbb_and_safe_life_passes(self):
        result = check_fracture_control(lbb_demonstrated=True, safe_life_approach=True)
        self.assertEqual(result.status, "PASS")


class TestLinerPermeationCheck(unittest.TestCase):

    def test_permeation_exceeded_fails(self):
        inp = _make_cops_nml_compliant(
            permeation_rate_cc_per_s=8e-6,
            allowable_permeation_cc_per_s=5e-6,
        )
        result = assess_system(inp)
        fail_checks = [f.check for f in result.fails()]
        self.assertIn("liner_permeation", fail_checks)

    def test_missing_permeation_rate_fails(self):
        result = check_liner_permeation(rate=None, allowable=5e-6)
        self.assertEqual(result.status, "FAIL")
        self.assertIn("not provided", result.detail)

    def test_missing_allowable_permeation_fails(self):
        result = check_liner_permeation(rate=1e-6, allowable=None)
        self.assertEqual(result.status, "FAIL")
        self.assertIn("not provided", result.detail)

    def test_permeation_at_limit_passes(self):
        result = check_liner_permeation(rate=5e-6, allowable=5e-6)
        self.assertEqual(result.status, "PASS")


class TestLinerBucklingCheck(unittest.TestCase):

    def test_buckling_ratio_below_one_fails(self):
        inp = _make_cops_nml_compliant(liner_buckling_ratio=0.85)
        result = assess_system(inp)
        fail_checks = [f.check for f in result.fails()]
        self.assertIn("liner_buckling", fail_checks)

    def test_missing_buckling_ratio_fails(self):
        result = check_liner_buckling(ratio=None)
        self.assertEqual(result.status, "FAIL")

    def test_buckling_ratio_exactly_one_passes(self):
        result = check_liner_buckling(ratio=1.0)
        self.assertEqual(result.status, "PASS")


class TestAllCompositeCPS(unittest.TestCase):

    def test_cps_compliant_all_pass(self):
        result = assess_system(_make_cps_compliant())
        self.assertTrue(result.compliant)

    def test_cps_four_findings_no_liner_checks(self):
        result = assess_system(_make_cps_compliant())
        # proof, burst, cycle_life, fracture_control only
        self.assertEqual(len(result.findings), 4)

    def test_cps_burst_insufficient_fails(self):
        inp = _make_cps_compliant(burst_pressure_predicted_mpa=28.0)  # < 30.0
        result = assess_system(inp)
        fail_checks = [f.check for f in result.fails()]
        self.assertIn("burst_pressure", fail_checks)

    def test_cps_variant_label(self):
        result = assess_system(_make_cps_compliant())
        self.assertEqual(result.variant, "all_composite_cps")

    def test_cps_no_fracture_control_fails(self):
        inp = _make_cps_compliant(lbb_demonstrated=False, safe_life_approach=False)
        result = assess_system(inp)
        self.assertFalse(result.compliant)


class TestInputValidation(unittest.TestCase):

    def test_negative_meop_raises(self):
        with self.assertRaises(ValueError):
            assess_system(_make_cps_compliant(meop_mpa=-1.0))

    def test_zero_meop_raises(self):
        with self.assertRaises(ValueError):
            assess_system(_make_cps_compliant(meop_mpa=0.0))

    def test_negative_proof_raises(self):
        with self.assertRaises(ValueError):
            assess_system(_make_cps_compliant(proof_pressure_mpa=-5.0))

    def test_negative_burst_raises(self):
        with self.assertRaises(ValueError):
            assess_system(_make_cps_compliant(burst_pressure_predicted_mpa=-1.0))

    def test_negative_design_cycles_raises(self):
        with self.assertRaises(ValueError):
            assess_system(_make_cps_compliant(design_cycles=-1))

    def test_zero_meop_burst_ratio_raises(self):
        with self.assertRaises(ValueError):
            burst_margin_ratio(0.0, 40.0)

    def test_zero_meop_proof_ratio_raises(self):
        with self.assertRaises(ValueError):
            proof_margin_ratio(0.0, 22.0)


class TestFindingItem(unittest.TestCase):

    def test_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            FindingItem("some_check", "UNKNOWN", "detail text")

    def test_pass_status_accepted(self):
        item = FindingItem("check_x", "PASS", "all good")
        self.assertEqual(item.status, "PASS")

    def test_fail_status_accepted(self):
        item = FindingItem("check_x", "FAIL", "out of bounds")
        self.assertEqual(item.status, "FAIL")


class TestMultipleFailsAggregated(unittest.TestCase):

    def test_two_fails_both_listed(self):
        inp = _make_cops_nml_compliant(
            proof_pressure_mpa=10.0,  # too low
            burst_pressure_predicted_mpa=15.0,  # too low
        )
        result = assess_system(inp)
        fail_checks = {f.check for f in result.fails()}
        self.assertIn("proof_pressure", fail_checks)
        self.assertIn("burst_pressure", fail_checks)

    def test_compliant_true_only_when_all_pass(self):
        inp = _make_cops_nml_compliant(
            lbb_demonstrated=False,
            safe_life_approach=False,
        )
        result = assess_system(inp)
        self.assertFalse(result.compliant)


if __name__ == "__main__":
    unittest.main()
