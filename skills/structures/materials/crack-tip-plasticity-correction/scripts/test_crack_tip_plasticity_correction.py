#!/usr/bin/env python3
"""Gate 3 contract test: crack-tip plastic-zone correction.

Exercises scripts/crack_tip_plasticity_correction_logic.py (stdlib
unittest, offline, deterministic). Covers the SKILL.md workflow steps:
step 1 evaluates the uncorrected elastic stress intensity
K = Y*sigma*sqrt(pi*a); step 2 evaluates the Irwin plastic-zone radius
in both constraint states, the plane stress irwin-plastic-zone and the
reduced plane-strain zone; step 3 forms the effective-crack-length
a_eff = a + r_p and the corrected stress intensity K_eff (the
k-eff-correction ratio K_eff/K = sqrt(a_eff/a)); step 4 runs the
small-scale-yielding-check size rule and reports the LEFM-validity
verdict; step 5 applies the dugdale-strip-yield-model to a center
crack, its exact secant zone and small-scale-yielding asymptote, and
the plastic-zone-radius comparison between the two models.

Anchors (7075-T6, sigma_ys = 503 MPa, prep anchor
/tmp/w46spec/anchor_crack_tip_plasticity.py, real module outputs):
case 1 (5 mm edge crack, Y=1.12, sigma=180 MPa) K=25.266813008280486
MPa*sqrt(m); case 1b (same crack, sigma=120 MPa) K=16.844542005520324;
case 2 (10 mm center crack, sigma_0=503 MPa, sigma=452.7 MPa)
K=80.23898583049271.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import crack_tip_plasticity_correction_logic as ctpc


SIGMA_YS = 503.0


class StressIntensityTests(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: the uncorrected elastic K."""

    def test_case1_and_case2_stress_intensity(self):
        self.assertAlmostEqual(
            ctpc.stress_intensity(180.0, 0.005, 1.12), 25.266813008280486, delta=1e-6
        )
        self.assertAlmostEqual(
            ctpc.stress_intensity(452.7, 0.010, 1.0), 80.23898583049271, delta=1e-6
        )

    def test_matches_direct_formula(self):
        k = ctpc.stress_intensity(180.0, 0.005, 1.12)
        direct = 1.12 * 180.0 * math.sqrt(math.pi * 0.005)
        self.assertAlmostEqual(k, direct, delta=1e-9)

    def test_rejects_non_positive_inputs(self):
        with self.assertRaises(ValueError):
            ctpc.stress_intensity(0.0, 0.005, 1.12)
        with self.assertRaises(ValueError):
            ctpc.stress_intensity(-10.0, 0.005, 1.12)
        with self.assertRaises(ValueError):
            ctpc.stress_intensity(180.0, 0.0, 1.12)
        with self.assertRaises(ValueError):
            ctpc.stress_intensity(180.0, 0.005, 0.0)


class IrwinPlasticZoneTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the irwin-plastic-zone radius."""

    def setUp(self):
        self.k1 = ctpc.stress_intensity(180.0, 0.005, 1.12)

    def test_plane_stress_and_plane_strain_zones(self):
        r_p_ps = ctpc.irwin_plastic_zone(self.k1, SIGMA_YS, "plane-stress")
        r_p_pe = ctpc.irwin_plastic_zone(self.k1, SIGMA_YS, "plane-strain")
        self.assertAlmostEqual(r_p_ps, 8.031840764557785e-04, delta=1e-10)
        self.assertAlmostEqual(r_p_pe, 2.677280254852595e-04, delta=1e-10)

    def test_plane_strain_is_exactly_one_third_of_plane_stress(self):
        r_p_ps = ctpc.irwin_plastic_zone(self.k1, SIGMA_YS, "plane-stress")
        r_p_pe = ctpc.irwin_plastic_zone(self.k1, SIGMA_YS, "plane-strain")
        self.assertAlmostEqual(r_p_pe, r_p_ps / 3.0, delta=1e-12)

    def test_plane_strain_below_plane_stress_and_increasing_in_k(self):
        r_p_low = ctpc.irwin_plastic_zone(10.0, SIGMA_YS, "plane-stress")
        r_p_high = ctpc.irwin_plastic_zone(30.0, SIGMA_YS, "plane-stress")
        self.assertLess(r_p_low, r_p_high)
        r_p_ps = ctpc.irwin_plastic_zone(self.k1, SIGMA_YS, "plane-stress")
        r_p_pe = ctpc.irwin_plastic_zone(self.k1, SIGMA_YS, "plane-strain")
        self.assertLess(r_p_pe, r_p_ps)

    def test_rejects_non_positive_and_bad_constraint(self):
        with self.assertRaises(ValueError):
            ctpc.irwin_plastic_zone(0.0, SIGMA_YS, "plane-stress")
        with self.assertRaises(ValueError):
            ctpc.irwin_plastic_zone(self.k1, 0.0, "plane-stress")
        with self.assertRaises(ValueError):
            ctpc.irwin_plastic_zone(self.k1, SIGMA_YS, "plane")


class EffectiveCrackLengthTests(unittest.TestCase):
    def test_case1_effective_crack(self):
        a_eff = ctpc.effective_crack_length(0.005, 8.031840764557785e-04)
        self.assertAlmostEqual(a_eff, 0.005803184076456, delta=1e-9)

    def test_accepts_zero_r_p(self):
        a_eff = ctpc.effective_crack_length(0.005, 0.0)
        self.assertAlmostEqual(a_eff, 0.005, delta=1e-12)

    def test_rejects_non_positive_a_and_negative_r_p(self):
        with self.assertRaises(ValueError):
            ctpc.effective_crack_length(0.0, 1e-4)
        with self.assertRaises(ValueError):
            ctpc.effective_crack_length(0.005, -1e-4)


class IrwinEffectiveCorrectionTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the effective-crack-length
    correction and the k-eff-correction ratio."""

    def test_case1_plane_stress(self):
        c = ctpc.irwin_effective_correction(180.0, 0.005, 1.12, SIGMA_YS, "plane-stress")
        self.assertAlmostEqual(c["k_mpa_sqrtm"], 25.266813008280486, delta=1e-6)
        self.assertAlmostEqual(c["r_p_m"], 8.031840764557785e-04, delta=1e-9)
        self.assertAlmostEqual(c["a_eff_m"], 0.005803184076456, delta=1e-9)
        self.assertAlmostEqual(c["k_eff_mpa_sqrtm"], 27.220659146174018, delta=1e-6)
        self.assertAlmostEqual(c["k_eff_over_k"], 1.077328554940950, delta=1e-9)

    def test_case1_plane_strain(self):
        c = ctpc.irwin_effective_correction(180.0, 0.005, 1.12, SIGMA_YS, "plane-strain")
        self.assertAlmostEqual(c["r_p_m"], 2.677280254852595e-04, delta=1e-9)
        self.assertAlmostEqual(c["a_eff_m"], 0.005267728025485, delta=1e-9)
        self.assertAlmostEqual(c["k_eff_mpa_sqrtm"], 25.934455611168520, delta=1e-6)
        self.assertAlmostEqual(c["k_eff_over_k"], 1.026423696675526, delta=1e-9)

    def test_case1b_plane_stress(self):
        c = ctpc.irwin_effective_correction(120.0, 0.005, 1.12, SIGMA_YS, "plane-stress")
        self.assertAlmostEqual(c["k_mpa_sqrtm"], 16.844542005520324, delta=1e-6)
        self.assertAlmostEqual(c["r_p_m"], 3.569707006470125e-04, delta=1e-9)
        self.assertAlmostEqual(c["a_eff_m"], 0.005356970700647, delta=1e-9)
        self.assertAlmostEqual(c["k_eff_mpa_sqrtm"], 17.435477292409118, delta=1e-6)
        self.assertAlmostEqual(c["k_eff_over_k"], 1.035081706982305, delta=1e-9)

    def test_k_eff_over_k_matches_sqrt_a_ratio_identity(self):
        for constraint in ("plane-stress", "plane-strain"):
            c = ctpc.irwin_effective_correction(180.0, 0.005, 1.12, SIGMA_YS, constraint)
            expected = math.sqrt(c["a_eff_m"] / 0.005)
            self.assertTrue(math.isclose(c["k_eff_over_k"], expected, rel_tol=1e-9))

    def test_correction_grows_with_load_ratio(self):
        c_1b = ctpc.irwin_effective_correction(120.0, 0.005, 1.12, SIGMA_YS, "plane-stress")
        c_1 = ctpc.irwin_effective_correction(180.0, 0.005, 1.12, SIGMA_YS, "plane-stress")
        c_2 = ctpc.dugdale_effective_correction(452.7, 0.010, SIGMA_YS)
        self.assertLess(c_1b["k_eff_over_k"], c_1["k_eff_over_k"])
        self.assertLess(c_1["k_eff_over_k"], c_2["k_eff_over_k"])

    def test_ssy_limit_recovery_at_high_yield_strength(self):
        c = ctpc.irwin_effective_correction(180.0, 0.005, 1.12, 1.0e9, "plane-stress")
        self.assertAlmostEqual(c["k_eff_over_k"] - 1.0, 0.0, delta=1e-12)

    def test_rejects_negative_sigma(self):
        with self.assertRaises(ValueError):
            ctpc.irwin_effective_correction(-180.0, 0.005, 1.12, SIGMA_YS, "plane-stress")


class DugdaleStripZoneTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the dugdale-strip-yield-model
    exact secant zone."""

    def test_case2_exact_zone(self):
        rho = ctpc.dugdale_strip_zone(0.010, 452.7, 503.0)
        self.assertAlmostEqual(rho, 5.392453221499650e-02, delta=1e-9)

    def test_zone_grows_without_bound_toward_full_strip_yield(self):
        rho_low = ctpc.dugdale_strip_zone(0.010, 0.9 * 503.0, 503.0)
        rho_high = ctpc.dugdale_strip_zone(0.010, 0.999 * 503.0, 503.0)
        self.assertGreater(rho_high, rho_low * 10.0)

    def test_asymptote_collapse_at_one_percent_of_flow_stress(self):
        sigma = 0.01 * 503.0
        rho = ctpc.dugdale_strip_zone(0.010, sigma, 503.0)
        k = ctpc.stress_intensity(sigma, 0.010, 1.0)
        rho_ssy = ctpc.dugdale_ssy_zone(k, 503.0)
        self.assertTrue(math.isclose(rho / rho_ssy, 1.000102818695661, rel_tol=1e-6))

    def test_rejects_at_and_above_full_strip_yield_and_bad_a(self):
        with self.assertRaises(ValueError):
            ctpc.dugdale_strip_zone(0.010, 452.7, 452.7)
        with self.assertRaises(ValueError):
            ctpc.dugdale_strip_zone(0.010, 600.0, 503.0)
        with self.assertRaises(ValueError):
            ctpc.dugdale_strip_zone(0.0, 452.7, 503.0)


class DugdaleSsyZoneTests(unittest.TestCase):
    def test_case2_ssy_asymptote(self):
        k2 = ctpc.stress_intensity(452.7, 0.010, 1.0)
        rho_ssy = ctpc.dugdale_ssy_zone(k2, 503.0)
        self.assertAlmostEqual(rho_ssy, 9.992974456102975e-03, delta=1e-9)

    def test_matches_closed_form(self):
        k1 = ctpc.stress_intensity(180.0, 0.005, 1.12)
        rho_ssy = ctpc.dugdale_ssy_zone(k1, 503.0)
        direct = (math.pi / 8.0) * (k1 / 503.0) ** 2
        self.assertAlmostEqual(rho_ssy, direct, delta=1e-12)

    def test_zone_coefficient_identity(self):
        k1 = ctpc.stress_intensity(180.0, 0.005, 1.12)
        rho_ssy = ctpc.dugdale_ssy_zone(k1, 503.0)
        r_p_ps = ctpc.irwin_plastic_zone(k1, 503.0, "plane-stress")
        self.assertTrue(math.isclose(rho_ssy / r_p_ps, math.pi ** 2 / 8.0, rel_tol=1e-12))
        self.assertAlmostEqual(ctpc.RHO_OVER_RP_PS, math.pi ** 2 / 8.0, delta=1e-12)

    def test_rejects_non_positive_inputs(self):
        with self.assertRaises(ValueError):
            ctpc.dugdale_ssy_zone(0.0, 503.0)
        with self.assertRaises(ValueError):
            ctpc.dugdale_ssy_zone(80.0, 0.0)


class DugdaleEffectiveCorrectionTests(unittest.TestCase):
    def test_case2_full_correction(self):
        d = ctpc.dugdale_effective_correction(452.7, 0.010, 503.0)
        self.assertAlmostEqual(d["k_mpa_sqrtm"], 80.238985830492709, delta=1e-6)
        self.assertAlmostEqual(d["rho_m"], 5.392453221499650e-02, delta=1e-9)
        self.assertAlmostEqual(d["a_eff_m"], 0.063924532214996, delta=1e-8)
        self.assertAlmostEqual(d["k_eff_mpa_sqrtm"], 202.870645082888728, delta=1e-5)
        self.assertAlmostEqual(d["k_eff_over_k"], 2.528330125102268, delta=1e-9)

    def test_k_eff_over_k_matches_sqrt_a_ratio_identity(self):
        d = ctpc.dugdale_effective_correction(452.7, 0.010, 503.0)
        expected = math.sqrt(d["a_eff_m"] / 0.010)
        self.assertTrue(math.isclose(d["k_eff_over_k"], expected, rel_tol=1e-9))

    def test_propagates_strip_zone_valueerror(self):
        with self.assertRaises(ValueError):
            ctpc.dugdale_effective_correction(600.0, 0.010, 503.0)


class SxyValidityTests(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the small-scale-yielding-check
    LEFM-validity verdict."""

    def test_case1_invalid_verdict(self):
        k1 = ctpc.stress_intensity(180.0, 0.005, 1.12)
        v = ctpc.sxy_validity(k1, SIGMA_YS, 0.005)
        self.assertAlmostEqual(v["required_a_m"], 0.006308192985184, delta=1e-9)
        self.assertAlmostEqual(v["a_over_required"], 0.792620012060999, delta=1e-9)
        self.assertAlmostEqual(v["r_p_ps_over_a"], 0.160636815291156, delta=1e-9)
        self.assertAlmostEqual(v["r_p_pe_over_a"], 0.053545605097052, delta=1e-9)
        self.assertFalse(v["valid"])

    def test_case1b_valid_verdict(self):
        k1b = ctpc.stress_intensity(120.0, 0.005, 1.12)
        v = ctpc.sxy_validity(k1b, SIGMA_YS, 0.005)
        self.assertAlmostEqual(v["required_a_m"], 0.002803641326749, delta=1e-9)
        self.assertTrue(v["valid"])

    def test_case2_invalid_verdict(self):
        k2 = ctpc.stress_intensity(452.7, 0.010, 1.0)
        v = ctpc.sxy_validity(k2, SIGMA_YS, 0.010)
        self.assertAlmostEqual(v["required_a_m"], 0.06361725123519331, delta=1e-8)
        self.assertAlmostEqual(v["a_over_required"], 0.157190067251255, delta=1e-9)
        self.assertFalse(v["valid"])

    def test_required_a_matches_zone_identity(self):
        k1 = ctpc.stress_intensity(180.0, 0.005, 1.12)
        v = ctpc.sxy_validity(k1, SIGMA_YS, 0.005)
        r_p_ps = ctpc.irwin_plastic_zone(k1, SIGMA_YS, "plane-stress")
        self.assertTrue(math.isclose(v["required_a_m"], 2.5 * math.pi * r_p_ps, rel_tol=1e-9))

    def test_rejects_non_positive_inputs(self):
        with self.assertRaises(ValueError):
            ctpc.sxy_validity(-1.0, SIGMA_YS, 0.005)
        with self.assertRaises(ValueError):
            ctpc.sxy_validity(25.0, 0.0, 0.005)
        with self.assertRaises(ValueError):
            ctpc.sxy_validity(25.0, SIGMA_YS, 0.0)


class DeterminismTests(unittest.TestCase):
    """Determinism check: identical inputs give identical bits, pure
    math module, no RNG."""

    def test_repeated_runs_identical(self):
        first = ctpc.irwin_effective_correction(180.0, 0.005, 1.12, SIGMA_YS, "plane-stress")
        second = ctpc.irwin_effective_correction(180.0, 0.005, 1.12, SIGMA_YS, "plane-stress")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
