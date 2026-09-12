"""
Gate-3 contract tests for fracture_critical_parts_logic.
Run: python3 test_fracture_critical_parts.py
Requires stdlib only. Deterministic, offline.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fracture_critical_parts_logic import (
    FailureConsequence,
    FractureControlMethod,
    PartRecord,
    StructuralRole,
    check_nde_compliance,
    check_proof_test_compliance,
    compute_proof_detectable_crack_mm,
    evaluate_fracture_control_compliance,
    screen_fracture_critical,
    MIN_PROOF_FACTOR,
    NDE_MARGIN,
)


def _make_part(**kwargs) -> PartRecord:
    defaults = dict(
        part_id="P-001",
        material="Ti-6Al-4V",
        consequence=FailureConsequence.CATASTROPHIC,
        structural_role=StructuralRole.PRIMARY,
        applied_stress_mpa=300.0,
        yield_strength_mpa=800.0,
        fracture_toughness_mpa_sqrtm=55.0,
        is_pressurized=False,
        fracture_control_method=FractureControlMethod.NONE,
    )
    defaults.update(kwargs)
    return PartRecord(**defaults)


class TestScreening(unittest.TestCase):

    def test_primary_structure_catastrophic_is_fracture_critical(self):
        part = _make_part(
            structural_role=StructuralRole.PRIMARY,
            consequence=FailureConsequence.CATASTROPHIC,
        )
        result = screen_fracture_critical(part)
        self.assertTrue(result.is_fracture_critical)
        self.assertTrue(any("primary" in r for r in result.reasons))

    def test_minor_consequence_not_fracture_critical(self):
        part = _make_part(
            consequence=FailureConsequence.MINOR,
            structural_role=StructuralRole.PRIMARY,
            is_pressurized=True,
        )
        result = screen_fracture_critical(part)
        self.assertFalse(result.is_fracture_critical)
        self.assertTrue(any("threshold" in r for r in result.reasons))

    def test_major_consequence_not_fracture_critical(self):
        part = _make_part(
            consequence=FailureConsequence.MAJOR,
            structural_role=StructuralRole.PRIMARY,
            is_pressurized=True,
        )
        result = screen_fracture_critical(part)
        self.assertFalse(result.is_fracture_critical)

    def test_pressurized_critical_is_fracture_critical(self):
        part = _make_part(
            is_pressurized=True,
            consequence=FailureConsequence.CRITICAL,
            structural_role=StructuralRole.SECONDARY,
            applied_stress_mpa=100.0,
            yield_strength_mpa=800.0,
        )
        result = screen_fracture_critical(part)
        self.assertTrue(result.is_fracture_critical)
        self.assertTrue(any("pressurized" in r for r in result.reasons))

    def test_high_stress_ratio_catastrophic_is_fracture_critical(self):
        # stress ratio = 500/800 = 0.625 >= 0.50
        part = _make_part(
            consequence=FailureConsequence.CATASTROPHIC,
            structural_role=StructuralRole.SECONDARY,
            is_pressurized=False,
            applied_stress_mpa=500.0,
            yield_strength_mpa=800.0,
        )
        result = screen_fracture_critical(part)
        self.assertTrue(result.is_fracture_critical)
        self.assertTrue(any("stress ratio" in r for r in result.reasons))

    def test_low_stress_secondary_non_pressurized_critical_not_fracture_critical(self):
        # stress ratio = 100/800 = 0.125 < 0.50, secondary, non-pressurized
        part = _make_part(
            consequence=FailureConsequence.CRITICAL,
            structural_role=StructuralRole.SECONDARY,
            is_pressurized=False,
            applied_stress_mpa=100.0,
            yield_strength_mpa=800.0,
        )
        result = screen_fracture_critical(part)
        self.assertFalse(result.is_fracture_critical)
        self.assertTrue(any("no structural trigger" in r for r in result.reasons))

    def test_stress_ratio_exactly_at_threshold_is_fracture_critical(self):
        # stress ratio = 400/800 = 0.50 exactly
        part = _make_part(
            consequence=FailureConsequence.CATASTROPHIC,
            structural_role=StructuralRole.SECONDARY,
            is_pressurized=False,
            applied_stress_mpa=400.0,
            yield_strength_mpa=800.0,
        )
        result = screen_fracture_critical(part)
        self.assertTrue(result.is_fracture_critical)


class TestStressRatioAndValidation(unittest.TestCase):

    def test_stress_ratio_calculation(self):
        part = _make_part(applied_stress_mpa=300.0, yield_strength_mpa=600.0)
        self.assertAlmostEqual(part.stress_ratio(), 0.5)

    def test_invalid_yield_strength_zero_raises(self):
        part = _make_part(yield_strength_mpa=0.0)
        with self.assertRaises(ValueError):
            part.stress_ratio()

    def test_invalid_yield_strength_negative_raises(self):
        part = _make_part(yield_strength_mpa=-100.0)
        with self.assertRaises(ValueError):
            screen_fracture_critical(part)


class TestProofTestCompliance(unittest.TestCase):

    def test_proof_test_compliant_at_minimum(self):
        part = _make_part(
            proof_factor=MIN_PROOF_FACTOR,
            critical_crack_size_mm=10.0,
            fracture_control_method=FractureControlMethod.PROOF_TEST,
        )
        ok, findings = check_proof_test_compliance(part)
        self.assertTrue(ok)
        self.assertEqual(findings, [])

    def test_proof_test_compliant_above_minimum(self):
        part = _make_part(
            proof_factor=1.5,
            critical_crack_size_mm=10.0,
            fracture_control_method=FractureControlMethod.PROOF_TEST,
        )
        ok, findings = check_proof_test_compliance(part)
        self.assertTrue(ok)

    def test_proof_test_insufficient_factor(self):
        part = _make_part(
            proof_factor=1.1,
            critical_crack_size_mm=10.0,
            fracture_control_method=FractureControlMethod.PROOF_TEST,
        )
        ok, findings = check_proof_test_compliance(part)
        self.assertFalse(ok)
        self.assertTrue(any("minimum" in f for f in findings))

    def test_proof_test_missing_proof_factor(self):
        part = _make_part(
            proof_factor=None,
            critical_crack_size_mm=10.0,
            fracture_control_method=FractureControlMethod.PROOF_TEST,
        )
        ok, findings = check_proof_test_compliance(part)
        self.assertFalse(ok)
        self.assertTrue(any("proof_factor" in f for f in findings))

    def test_proof_test_missing_critical_crack_size(self):
        part = _make_part(
            proof_factor=1.3,
            critical_crack_size_mm=None,
            fracture_control_method=FractureControlMethod.PROOF_TEST,
        )
        ok, findings = check_proof_test_compliance(part)
        self.assertFalse(ok)
        self.assertTrue(any("critical_crack_size_mm" in f for f in findings))


class TestNDECompliance(unittest.TestCase):

    def test_nde_compliant(self):
        # detectable = 1mm, critical = 4mm, required <= 4/2 = 2mm → pass
        part = _make_part(
            nde_detectable_crack_mm=1.0,
            critical_crack_size_mm=4.0,
            fracture_control_method=FractureControlMethod.NDE,
        )
        ok, findings = check_nde_compliance(part)
        self.assertTrue(ok)
        self.assertEqual(findings, [])

    def test_nde_insufficient_sensitivity(self):
        # detectable = 3mm, critical = 4mm, required <= 2mm → fail
        part = _make_part(
            nde_detectable_crack_mm=3.0,
            critical_crack_size_mm=4.0,
            fracture_control_method=FractureControlMethod.NDE,
        )
        ok, findings = check_nde_compliance(part)
        self.assertFalse(ok)
        self.assertTrue(any("required limit" in f for f in findings))

    def test_nde_missing_detectable_crack(self):
        part = _make_part(
            nde_detectable_crack_mm=None,
            critical_crack_size_mm=4.0,
            fracture_control_method=FractureControlMethod.NDE,
        )
        ok, findings = check_nde_compliance(part)
        self.assertFalse(ok)
        self.assertTrue(any("nde_detectable_crack_mm" in f for f in findings))

    def test_nde_missing_critical_crack_size(self):
        part = _make_part(
            nde_detectable_crack_mm=1.0,
            critical_crack_size_mm=None,
            fracture_control_method=FractureControlMethod.NDE,
        )
        ok, findings = check_nde_compliance(part)
        self.assertFalse(ok)
        self.assertTrue(any("critical_crack_size_mm" in f for f in findings))

    def test_nde_exactly_at_limit_compliant(self):
        # detectable = 2mm, critical = 4mm, required <= 2mm → boundary pass
        part = _make_part(
            nde_detectable_crack_mm=2.0,
            critical_crack_size_mm=4.0,
            fracture_control_method=FractureControlMethod.NDE,
        )
        ok, findings = check_nde_compliance(part)
        self.assertTrue(ok)


class TestComputeProofDetectableCrack(unittest.TestCase):

    def test_formula_result(self):
        # critical = 10mm, factor = 1.25 → surviving = 10 / 1.25^2 = 6.4mm
        result = compute_proof_detectable_crack_mm(10.0, 1.25)
        self.assertAlmostEqual(result, 6.4, places=6)

    def test_higher_factor_smaller_surviving_crack(self):
        r1 = compute_proof_detectable_crack_mm(10.0, 1.25)
        r2 = compute_proof_detectable_crack_mm(10.0, 1.5)
        self.assertLess(r2, r1)

    def test_invalid_factor_raises(self):
        with self.assertRaises(ValueError):
            compute_proof_detectable_crack_mm(10.0, 1.0)

    def test_invalid_crack_size_raises(self):
        with self.assertRaises(ValueError):
            compute_proof_detectable_crack_mm(0.0, 1.3)


class TestEvaluateFractureControlCompliance(unittest.TestCase):

    def test_non_fracture_critical_part_is_compliant(self):
        part = _make_part(
            consequence=FailureConsequence.MINOR,
            fracture_control_method=FractureControlMethod.NONE,
        )
        result = evaluate_fracture_control_compliance(part)
        self.assertTrue(result.compliant)
        self.assertEqual(result.findings, [])
        self.assertEqual(result.method, FractureControlMethod.NONE)

    def test_fracture_critical_no_method_non_compliant(self):
        part = _make_part(
            structural_role=StructuralRole.PRIMARY,
            consequence=FailureConsequence.CATASTROPHIC,
            fracture_control_method=FractureControlMethod.NONE,
        )
        result = evaluate_fracture_control_compliance(part)
        self.assertFalse(result.compliant)
        self.assertTrue(any("no fracture control method" in f for f in result.findings))

    def test_fracture_critical_proof_test_compliant(self):
        part = _make_part(
            structural_role=StructuralRole.PRIMARY,
            consequence=FailureConsequence.CATASTROPHIC,
            fracture_control_method=FractureControlMethod.PROOF_TEST,
            proof_factor=1.3,
            critical_crack_size_mm=8.0,
        )
        result = evaluate_fracture_control_compliance(part)
        self.assertTrue(result.compliant)
        self.assertEqual(result.findings, [])

    def test_fracture_critical_nde_compliant(self):
        part = _make_part(
            structural_role=StructuralRole.PRIMARY,
            consequence=FailureConsequence.CATASTROPHIC,
            fracture_control_method=FractureControlMethod.NDE,
            nde_detectable_crack_mm=1.5,
            critical_crack_size_mm=6.0,
        )
        result = evaluate_fracture_control_compliance(part)
        self.assertTrue(result.compliant)

    def test_fracture_critical_both_methods_one_fails(self):
        # NDE fails (detectable > critical/2), proof test passes
        part = _make_part(
            structural_role=StructuralRole.PRIMARY,
            consequence=FailureConsequence.CATASTROPHIC,
            fracture_control_method=FractureControlMethod.BOTH,
            proof_factor=1.3,
            critical_crack_size_mm=8.0,
            nde_detectable_crack_mm=5.0,  # 5 > 8/2=4 → fail
        )
        result = evaluate_fracture_control_compliance(part)
        self.assertFalse(result.compliant)
        self.assertTrue(any("required limit" in f for f in result.findings))

    def test_fracture_critical_both_methods_both_pass(self):
        part = _make_part(
            structural_role=StructuralRole.PRIMARY,
            consequence=FailureConsequence.CATASTROPHIC,
            fracture_control_method=FractureControlMethod.BOTH,
            proof_factor=1.4,
            critical_crack_size_mm=8.0,
            nde_detectable_crack_mm=3.0,  # 3 <= 8/2=4 → pass
        )
        result = evaluate_fracture_control_compliance(part)
        self.assertTrue(result.compliant)


if __name__ == "__main__":
    unittest.main()
