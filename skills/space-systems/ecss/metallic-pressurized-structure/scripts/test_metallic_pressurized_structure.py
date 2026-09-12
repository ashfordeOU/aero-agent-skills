"""
Gate 3 contract tests for metallic_pressurized_structure_logic.
stdlib unittest only. Deterministic, offline. Run:
  python3 test_metallic_pressurized_structure.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from metallic_pressurized_structure_logic import (
    BulkheadDesignation,
    MPSResult,
    StructureCategory,
    ThinWallGeometry,
    assess_mps_compliance,
    assess_pressure_bulkhead,
    compute_axial_stress,
    compute_burst_pressure,
    compute_design_ultimate_pressure,
    compute_hoop_stress,
    compute_margin_of_safety,
    compute_proof_pressure,
)

_BANNED = "class" + "ified"  # built at runtime: the literal must not appear in source


# ---------------------------------------------------------------------------
# Hoop stress
# ---------------------------------------------------------------------------

class TestComputeHoopStress(unittest.TestCase):

    def test_basic_value(self):
        # σ_h = 100_000 × 1.0 / 0.01 = 10_000_000 Pa
        result = compute_hoop_stress(100_000.0, 1.0, 0.01)
        self.assertAlmostEqual(result, 10_000_000.0, places=1)

    def test_zero_pressure_gives_zero(self):
        result = compute_hoop_stress(0.0, 1.0, 0.005)
        self.assertEqual(result, 0.0)

    def test_proportional_to_pressure(self):
        s1 = compute_hoop_stress(1e5, 0.5, 0.005)
        s2 = compute_hoop_stress(2e5, 0.5, 0.005)
        self.assertAlmostEqual(s2, 2.0 * s1, places=6)

    def test_negative_pressure_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(-1.0, 1.0, 0.01)

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(1e5, 1.0, 0.0)

    def test_zero_radius_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(1e5, 0.0, 0.01)


# ---------------------------------------------------------------------------
# Axial stress
# ---------------------------------------------------------------------------

class TestComputeAxialStress(unittest.TestCase):

    def test_pressure_only_axial(self):
        # σ_a_p = p·r/(2t) = 1e5 × 1.0 / (2 × 0.01) = 5_000_000 Pa
        result = compute_axial_stress(1e5, 1.0, 0.01, axial_load=0.0)
        self.assertAlmostEqual(result, 5_000_000.0, places=1)

    def test_axial_load_adds_to_pressure_component(self):
        # Pure mechanical: N / (2π·r·t)
        r, t, N = 1.0, 0.01, 1000.0
        expected_mech = N / (2.0 * math.pi * r * t)
        result = compute_axial_stress(0.0, r, t, axial_load=N)
        self.assertAlmostEqual(result, expected_mech, places=6)

    def test_combined_axial_stress(self):
        r, t, p, N = 0.5, 0.005, 2e5, 5000.0
        expected = p * r / (2 * t) + N / (2 * math.pi * r * t)
        result = compute_axial_stress(p, r, t, axial_load=N)
        self.assertAlmostEqual(result, expected, places=4)

    def test_negative_axial_load_reduces_stress(self):
        s_pos = compute_axial_stress(1e5, 1.0, 0.01, axial_load=1e4)
        s_neg = compute_axial_stress(1e5, 1.0, 0.01, axial_load=-1e4)
        self.assertGreater(s_pos, s_neg)

    def test_invalid_thickness_raises(self):
        with self.assertRaises(ValueError):
            compute_axial_stress(1e5, 1.0, 0.0, axial_load=0.0)


# ---------------------------------------------------------------------------
# Design ultimate pressure
# ---------------------------------------------------------------------------

class TestComputeDesignUltimatePressure(unittest.TestCase):

    def test_dup_is_meop_times_sf(self):
        result = compute_design_ultimate_pressure(1e5, 1.5)
        self.assertAlmostEqual(result, 1.5e5, places=3)

    def test_sf_of_one_gives_meop(self):
        result = compute_design_ultimate_pressure(2e5, 1.0)
        self.assertAlmostEqual(result, 2e5, places=3)

    def test_sf_below_one_raises(self):
        with self.assertRaises(ValueError):
            compute_design_ultimate_pressure(1e5, 0.99)

    def test_zero_meop_raises(self):
        with self.assertRaises(ValueError):
            compute_design_ultimate_pressure(0.0, 1.5)

    def test_negative_meop_raises(self):
        with self.assertRaises(ValueError):
            compute_design_ultimate_pressure(-1e5, 1.5)


# ---------------------------------------------------------------------------
# Proof and burst pressures
# ---------------------------------------------------------------------------

class TestProofAndBurstPressure(unittest.TestCase):

    def test_proof_is_110_percent_meop(self):
        result = compute_proof_pressure(1e5)
        self.assertAlmostEqual(result, 1.1e5, places=3)

    def test_burst_is_200_percent_meop(self):
        result = compute_burst_pressure(1e5)
        self.assertAlmostEqual(result, 2.0e5, places=3)

    def test_proof_exceeds_meop(self):
        meop = 3e5
        self.assertGreater(compute_proof_pressure(meop), meop)

    def test_burst_exceeds_proof(self):
        meop = 1e5
        self.assertGreater(compute_burst_pressure(meop), compute_proof_pressure(meop))

    def test_zero_meop_raises_proof(self):
        with self.assertRaises(ValueError):
            compute_proof_pressure(0.0)

    def test_zero_meop_raises_burst(self):
        with self.assertRaises(ValueError):
            compute_burst_pressure(0.0)


# ---------------------------------------------------------------------------
# Margin of safety
# ---------------------------------------------------------------------------

class TestComputeMarginOfSafety(unittest.TestCase):

    def test_positive_margin(self):
        mos = compute_margin_of_safety(200.0, 100.0)
        self.assertAlmostEqual(mos, 1.0, places=6)

    def test_zero_margin(self):
        mos = compute_margin_of_safety(100.0, 100.0)
        self.assertAlmostEqual(mos, 0.0, places=6)

    def test_negative_margin(self):
        mos = compute_margin_of_safety(80.0, 100.0)
        self.assertAlmostEqual(mos, -0.2, places=6)

    def test_zero_applied_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(100.0, 0.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(0.0, 100.0)


# ---------------------------------------------------------------------------
# Pressure bulkhead fail-safe check
# ---------------------------------------------------------------------------

class TestAssessPressureBulkhead(unittest.TestCase):

    def test_safety_critical_with_fail_safe_compliant(self):
        ok, findings = assess_pressure_bulkhead(
            BulkheadDesignation.SAFETY_CRITICAL,
            has_fail_safe_feature=True,
            has_redundant_load_path=False,
        )
        self.assertTrue(ok)
        self.assertEqual(findings, [])

    def test_safety_critical_with_redundant_path_compliant(self):
        ok, findings = assess_pressure_bulkhead(
            BulkheadDesignation.SAFETY_CRITICAL,
            has_fail_safe_feature=False,
            has_redundant_load_path=True,
        )
        self.assertTrue(ok)
        self.assertEqual(findings, [])

    def test_safety_critical_both_provisions_compliant(self):
        ok, findings = assess_pressure_bulkhead(
            BulkheadDesignation.SAFETY_CRITICAL,
            has_fail_safe_feature=True,
            has_redundant_load_path=True,
        )
        self.assertTrue(ok)

    def test_safety_critical_no_provision_non_compliant(self):
        ok, findings = assess_pressure_bulkhead(
            BulkheadDesignation.SAFETY_CRITICAL,
            has_fail_safe_feature=False,
            has_redundant_load_path=False,
        )
        self.assertFalse(ok)
        self.assertGreater(len(findings), 0)

    def test_non_safety_critical_no_provision_compliant(self):
        ok, findings = assess_pressure_bulkhead(
            BulkheadDesignation.NON_SAFETY_CRITICAL,
            has_fail_safe_feature=False,
            has_redundant_load_path=False,
        )
        self.assertTrue(ok)
        self.assertEqual(findings, [])

    def test_finding_does_not_contain_banned_words(self):
        _, findings = assess_pressure_bulkhead(
            BulkheadDesignation.SAFETY_CRITICAL,
            has_fail_safe_feature=False,
            has_redundant_load_path=False,
        )
        for finding in findings:
            self.assertNotIn(_BANNED, finding.lower())
            self.assertNotIn(("un" + _BANNED), finding.lower())


# ---------------------------------------------------------------------------
# Full MPS compliance assessment
# ---------------------------------------------------------------------------

def _compliant_inputs():
    """Baseline inputs that produce a fully compliant MPS result."""
    return dict(
        geometry=ThinWallGeometry(radius=1.0, thickness=0.01),
        meop=1e5,
        pressure_sf=1.5,
        allowable_hoop=3e7,   # >> hoop stress of ~1.5e7 Pa at DUP
        allowable_axial=3e7,  # >> axial stress of ~7.5e6 Pa at DUP
        axial_load=0.0,
        bulkhead_designation=BulkheadDesignation.NON_SAFETY_CRITICAL,
        has_fail_safe_feature=False,
        has_redundant_load_path=False,
    )


class TestAssessMPSCompliance(unittest.TestCase):

    def test_fully_compliant_case(self):
        result = assess_mps_compliance(**_compliant_inputs())
        self.assertTrue(result.compliant)
        self.assertGreaterEqual(result.mos_hoop, 0.0)
        self.assertGreaterEqual(result.mos_axial, 0.0)
        self.assertTrue(result.bulkhead_compliant)
        self.assertEqual(result.findings, [])

    def test_negative_hoop_margin_non_compliant(self):
        inputs = _compliant_inputs()
        inputs["allowable_hoop"] = 1e4  # far below hoop stress → negative MoS
        result = assess_mps_compliance(**inputs)
        self.assertFalse(result.compliant)
        self.assertLess(result.mos_hoop, 0.0)
        self.assertTrue(any("Hoop" in f for f in result.findings))

    def test_negative_axial_margin_non_compliant(self):
        inputs = _compliant_inputs()
        inputs["allowable_axial"] = 1e4  # far below axial stress → negative MoS
        result = assess_mps_compliance(**inputs)
        self.assertFalse(result.compliant)
        self.assertLess(result.mos_axial, 0.0)
        self.assertTrue(any("Axial" in f for f in result.findings))

    def test_dup_stored_correctly(self):
        result = assess_mps_compliance(**_compliant_inputs())
        self.assertAlmostEqual(result.dup, 1.5e5, places=3)

    def test_proof_pressure_exceeds_meop(self):
        result = assess_mps_compliance(**_compliant_inputs())
        self.assertGreater(result.proof_pressure, 1e5)

    def test_burst_pressure_is_twice_meop(self):
        result = assess_mps_compliance(**_compliant_inputs())
        self.assertAlmostEqual(result.burst_pressure, 2e5, places=3)

    def test_safety_critical_bulkhead_no_provision_non_compliant(self):
        inputs = _compliant_inputs()
        inputs["bulkhead_designation"] = BulkheadDesignation.SAFETY_CRITICAL
        inputs["has_fail_safe_feature"] = False
        inputs["has_redundant_load_path"] = False
        result = assess_mps_compliance(**inputs)
        self.assertFalse(result.bulkhead_compliant)
        self.assertFalse(result.compliant)
        self.assertTrue(any("Safety-critical" in f for f in result.findings))

    def test_safety_critical_bulkhead_with_provision_compliant(self):
        inputs = _compliant_inputs()
        inputs["bulkhead_designation"] = BulkheadDesignation.SAFETY_CRITICAL
        inputs["has_fail_safe_feature"] = True
        result = assess_mps_compliance(**inputs)
        self.assertTrue(result.bulkhead_compliant)
        self.assertTrue(result.compliant)

    def test_hoop_stress_equals_thin_wall_formula(self):
        inputs = _compliant_inputs()
        result = assess_mps_compliance(**inputs)
        expected_hoop = compute_hoop_stress(result.dup, 1.0, 0.01)
        self.assertAlmostEqual(result.hoop_stress, expected_hoop, places=3)

    def test_multiple_findings_accumulated(self):
        inputs = _compliant_inputs()
        inputs["allowable_hoop"] = 1e4
        inputs["allowable_axial"] = 1e4
        inputs["bulkhead_designation"] = BulkheadDesignation.SAFETY_CRITICAL
        inputs["has_fail_safe_feature"] = False
        inputs["has_redundant_load_path"] = False
        result = assess_mps_compliance(**inputs)
        self.assertGreaterEqual(len(result.findings), 3)
        self.assertFalse(result.compliant)

    def test_result_is_mps_result_instance(self):
        result = assess_mps_compliance(**_compliant_inputs())
        self.assertIsInstance(result, MPSResult)


if __name__ == "__main__":
    unittest.main()
