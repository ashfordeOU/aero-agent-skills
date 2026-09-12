#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clause 4.6.3 COSPE with
homogeneous non-metallic liner.

Exercises scripts/cospe_nonmetallic_liner_logic.py (stdlib unittest,
offline). Contract: a liner material is categorized as nonmetallic when
it is in the recognized set and an unrecognized type raises; the proof
factor check flags a ratio below 1.1 and passes at or above it; the
burst factor check applies a degradation multiplier before comparing to
1.5 and rejects invalid degradation values; liner strain at proof is
compared against the liner allowable strain; fiber volume fraction is
checked against both a lower bound (0.50) and an upper bound (0.70);
and the full assessment aggregates all findings, returning compliant
only when every check passes.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cospe_nonmetallic_liner_logic as cl  # noqa: E402


class CategorizeLinerTypeTest(unittest.TestCase):
    def test_polymer_is_nonmetallic(self):
        self.assertEqual(cl.categorize_liner_type("polymer"), "nonmetallic")

    def test_elastomer_is_nonmetallic(self):
        self.assertEqual(cl.categorize_liner_type("elastomer"), "nonmetallic")

    def test_thermoplastic_is_nonmetallic(self):
        self.assertEqual(cl.categorize_liner_type("thermoplastic"), "nonmetallic")

    def test_thermoset_is_nonmetallic(self):
        self.assertEqual(cl.categorize_liner_type("thermoset"), "nonmetallic")

    def test_fluoropolymer_is_nonmetallic(self):
        self.assertEqual(cl.categorize_liner_type("fluoropolymer"), "nonmetallic")

    def test_unknown_liner_material_raises(self):
        with self.assertRaises(ValueError):
            cl.categorize_liner_type("titanium")

    def test_empty_string_liner_raises(self):
        with self.assertRaises(ValueError):
            cl.categorize_liner_type("")


class ProofFactorTest(unittest.TestCase):
    def test_proof_factor_above_minimum_passes(self):
        self.assertEqual(cl.check_proof_factor(1.2, 1.0), [])

    def test_proof_factor_exactly_at_minimum_passes(self):
        violations = cl.check_proof_factor(1.1, 1.0)
        self.assertEqual(violations, [])

    def test_proof_factor_below_minimum_flagged(self):
        violations = cl.check_proof_factor(1.05, 1.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "proof_factor_below_minimum")

    def test_proof_factor_violation_records_factor_value(self):
        violations = cl.check_proof_factor(0.9, 1.0)
        self.assertAlmostEqual(violations[0]["proof_factor"], 0.9)
        self.assertAlmostEqual(violations[0]["min_proof_factor"], cl.MIN_PROOF_FACTOR)

    def test_zero_mawp_raises(self):
        with self.assertRaises(ValueError):
            cl.check_proof_factor(1.5, 0.0)

    def test_negative_mawp_raises(self):
        with self.assertRaises(ValueError):
            cl.check_proof_factor(1.5, -1.0)


class BurstFactorTest(unittest.TestCase):
    def test_burst_factor_above_minimum_passes(self):
        self.assertEqual(cl.check_burst_factor(1.6, 1.0), [])

    def test_burst_factor_exactly_at_minimum_passes(self):
        self.assertEqual(cl.check_burst_factor(1.5, 1.0), [])

    def test_burst_factor_below_minimum_flagged(self):
        violations = cl.check_burst_factor(1.4, 1.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "burst_factor_below_minimum")

    def test_degradation_reduces_effective_burst_factor(self):
        # burst=1.6, mawp=1.0, degradation=0.9 → effective=1.44 < 1.5
        violations = cl.check_burst_factor(1.6, 1.0, degradation_factor=0.9)
        self.assertEqual(len(violations), 1)
        self.assertAlmostEqual(violations[0]["effective_burst_factor"], 1.44)

    def test_full_degradation_factor_of_one_passes_nominal(self):
        self.assertEqual(cl.check_burst_factor(2.0, 1.0, degradation_factor=1.0), [])

    def test_zero_degradation_factor_raises(self):
        with self.assertRaises(ValueError):
            cl.check_burst_factor(2.0, 1.0, degradation_factor=0.0)

    def test_degradation_factor_above_one_raises(self):
        with self.assertRaises(ValueError):
            cl.check_burst_factor(2.0, 1.0, degradation_factor=1.01)

    def test_zero_mawp_raises(self):
        with self.assertRaises(ValueError):
            cl.check_burst_factor(2.0, 0.0)


class LinerStrainTest(unittest.TestCase):
    def test_strain_within_allowable_passes(self):
        self.assertEqual(cl.check_liner_strain(0.005, 0.010), [])

    def test_strain_equal_to_allowable_passes(self):
        self.assertEqual(cl.check_liner_strain(0.010, 0.010), [])

    def test_strain_exceeds_allowable_flagged(self):
        violations = cl.check_liner_strain(0.012, 0.010)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "liner_strain_exceeds_allowable")

    def test_strain_violation_records_values(self):
        violations = cl.check_liner_strain(0.015, 0.010)
        self.assertAlmostEqual(violations[0]["liner_strain_at_proof"], 0.015)
        self.assertAlmostEqual(violations[0]["liner_allowable_strain"], 0.010)


class FiberVolumeFractionTest(unittest.TestCase):
    def test_fvf_in_valid_range_passes(self):
        self.assertEqual(cl.check_fiber_volume_fraction(0.60), [])

    def test_fvf_at_lower_bound_passes(self):
        self.assertEqual(cl.check_fiber_volume_fraction(0.50), [])

    def test_fvf_at_upper_bound_passes(self):
        self.assertEqual(cl.check_fiber_volume_fraction(0.70), [])

    def test_fvf_below_lower_bound_flagged(self):
        violations = cl.check_fiber_volume_fraction(0.45)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "fiber_volume_fraction_below_minimum")

    def test_fvf_above_upper_bound_flagged(self):
        violations = cl.check_fiber_volume_fraction(0.75)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "fiber_volume_fraction_above_maximum")


class CospeNonmetallicLinerAssessmentTest(unittest.TestCase):
    def _compliant_vessel(self):
        return {
            "liner_material": "thermoplastic",
            "proof_pressure": 1.15,
            "burst_pressure": 1.6,
            "mawp": 1.0,
            "liner_strain_at_proof": 0.008,
            "liner_allowable_strain": 0.012,
            "fiber_volume_fraction": 0.60,
            "degradation_factor": 0.95,
        }

    def test_fully_compliant_vessel_has_no_violations(self):
        result = cl.cospe_nonmetallic_liner_assessment(self._compliant_vessel())
        self.assertEqual(result["violations"], [])
        self.assertTrue(cl.is_cospe_compliant(result))

    def test_assessment_with_low_proof_factor_flagged(self):
        vessel = self._compliant_vessel()
        vessel["proof_pressure"] = 1.05
        result = cl.cospe_nonmetallic_liner_assessment(vessel)
        issues = [v["issue"] for v in result["violations"]]
        self.assertIn("proof_factor_below_minimum", issues)
        self.assertFalse(cl.is_cospe_compliant(result))

    def test_assessment_with_multiple_violations(self):
        vessel = {
            "liner_material": "polymer",
            "proof_pressure": 1.05,    # below 1.1 → violation
            "burst_pressure": 1.3,     # 1.3 * 1.0 / 1.0 = 1.3 < 1.5 → violation
            "mawp": 1.0,
            "liner_strain_at_proof": 0.015,   # > 0.010 allowable → violation
            "liner_allowable_strain": 0.010,
            "fiber_volume_fraction": 0.40,    # < 0.50 → violation
            "degradation_factor": 1.0,
        }
        result = cl.cospe_nonmetallic_liner_assessment(vessel)
        self.assertEqual(len(result["violations"]), 4)
        self.assertFalse(cl.is_cospe_compliant(result))

    def test_unrecognized_liner_material_raises(self):
        vessel = self._compliant_vessel()
        vessel["liner_material"] = "unobtanium"
        with self.assertRaises(ValueError):
            cl.cospe_nonmetallic_liner_assessment(vessel)

    def test_default_degradation_factor_is_one(self):
        vessel = self._compliant_vessel()
        del vessel["degradation_factor"]
        vessel["burst_pressure"] = 1.5  # factor exactly 1.5 with default 1.0
        result = cl.cospe_nonmetallic_liner_assessment(vessel)
        burst_violations = [
            v for v in result["violations"]
            if v["issue"] == "burst_factor_below_minimum"
        ]
        self.assertEqual(burst_violations, [])


if __name__ == "__main__":
    unittest.main()
