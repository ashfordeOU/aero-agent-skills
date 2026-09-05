"""Contract test for the laminate-plate-buckling leaf
(structures/composites/laminate-plate-buckling, AeroSkills wave-39).

Each method docstring names the SKILL.md workflow step it exercises:
step 2 evaluates the energy-method critical load for one half-wave mode
with critical_load, step 3 sweeps the half-wave mode counts with
buckling_mode, step 4 computes the stability margin with
buckling_margin, step 5 sanity-checks the isotropic reduction, and
step 6 confirms the deterministic contract test run. Deterministic,
offline, stdlib only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import laminate_plate_buckling_logic as lpb

# Worked example: a = 0.5 m (load direction), b = 0.25 m,
# D11 = 200 N m, D22 = 120 N m, D12 = 25 N m, D66 = 45 N m.
A = 0.5
B = 0.25
D11 = 200.0
D22 = 120.0
D12 = 25.0
D66 = 45.0

# Isotropic reduction material: E = 70 GPa, nu = 0.3, t = 2 mm,
# b = 250 mm, plate length a = 1.0 m in the load direction.
E_ISO = 70e9
NU_ISO = 0.3
T_ISO = 0.002
B_ISO = 0.25
A_ISO = 1.0
D_ISO = E_ISO * T_ISO ** 3 / (12.0 * (1.0 - NU_ISO ** 2))


class TestCriticalLoad(unittest.TestCase):
    """Workflow steps 2 and 5: critical_load mode evaluation."""

    def test_step2_worked_example_mode_21_anchor(self):
        """Step 2 critical_load at mode (2, 1) returns 86.85 kN/m within
        0.1 kN/m of the prep anchor."""
        n_cr = lpb.critical_load(D11, D22, D12, D66, A, B, 2, 1)
        self.assertAlmostEqual(n_cr, 86852.5, delta=1.0)
        self.assertLessEqual(abs(n_cr / 1000.0 - 86.85), 0.1)

    def test_step2_critical_load_strictly_positive(self):
        """Step 2 critical_load returns a positive N/m value for a valid
        half-wave mode on the worked example."""
        for (m, n) in [(1, 1), (2, 1), (1, 2), (3, 1)]:
            self.assertGreater(lpb.critical_load(D11, D22, D12, D66,
                                                 A, B, m, n), 0.0)

    def test_step2_mode_11_forced_load_value(self):
        """Step 2 critical_load at the forced m = 1 mode (1, 1) sits near
        120014 N/m, above the minimized 86.85 kN/m load."""
        self.assertAlmostEqual(lpb.critical_load(D11, D22, D12, D66,
                                                 A, B, 1, 1),
                               120014.4, delta=1.0)

    def test_step5_isotropic_reduction_sigma_anchor(self):
        """Step 5 isotropic reduction: D = 51.28 N m and the minimized
        load over a = 1.0 m, b = 0.25 m gives 16.196 MPa, within 0.05 MPa
        of the classic k = 4 anchor 16.20 MPa."""
        n_min, _, _ = lpb.buckling_mode(D_ISO, D_ISO, NU_ISO * D_ISO,
                                        (1.0 - NU_ISO) * D_ISO / 2.0,
                                        A_ISO, B_ISO)
        sigma = n_min / T_ISO / 1e6
        self.assertAlmostEqual(D_ISO, 51.28, delta=0.01)
        self.assertLessEqual(abs(sigma - 16.20), 0.05)

    def test_step5_classic_k4_identity(self):
        """Step 5 isotropic reduction identity: the minimized load equals
        the classic k = 4 result 4 * pi^2 * D / b^2 on the long plate."""
        n_min, m, n = lpb.buckling_mode(D_ISO, D_ISO, NU_ISO * D_ISO,
                                        (1.0 - NU_ISO) * D_ISO / 2.0,
                                        A_ISO, B_ISO)
        classic = 4.0 * math.pi ** 2 * D_ISO / (B_ISO ** 2)
        self.assertEqual((m, n), (4, 1))
        self.assertAlmostEqual(n_min, classic, delta=1e-6 * classic)

    def test_step5_long_plate_mode_tracks_aspect_ratio(self):
        """Step 5 long plate check: doubling a to 2.0 m doubles the
        governing half-wave count to m = 8 at the same k = 4 load."""
        n_min, m, n = lpb.buckling_mode(D_ISO, D_ISO, NU_ISO * D_ISO,
                                        (1.0 - NU_ISO) * D_ISO / 2.0,
                                        2.0, B_ISO)
        self.assertEqual((m, n), (8, 1))
        self.assertAlmostEqual(n_min, 32392.55, delta=1.0)


class TestBucklingMode(unittest.TestCase):
    """Workflow step 3: the half-wave mode count sweep."""

    def test_step3_governing_mode_pair(self):
        """Step 3 buckling_mode over the default sweep returns the
        governing pair (2, 1) for the worked example."""
        n_min, m, n = lpb.buckling_mode(D11, D22, D12, D66, A, B)
        self.assertEqual((m, n), (2, 1))

    def test_step3_minimized_load_value(self):
        """Step 3 buckling_mode minimized load is 86852.5 N/m on the
        worked example, within the 86.85 kN/m prep magnitude."""
        n_min, _, _ = lpb.buckling_mode(D11, D22, D12, D66, A, B)
        self.assertAlmostEqual(n_min, 86852.5, delta=1.0)
        self.assertAlmostEqual(n_min / 1000.0, 86.85, delta=0.1)

    def test_step3_sweep_capture_at_reduced_bounds(self):
        """Step 3 mode count sweep with m_max = 2 and n_max = 2 still
        captures the (2, 1) mode on the worked example."""
        n_min, m, n = lpb.buckling_mode(D11, D22, D12, D66, A, B,
                                        m_max=2, n_max=2)
        self.assertEqual((m, n), (2, 1))
        self.assertAlmostEqual(n_min, 86852.5, delta=1.0)

    def test_step3_forced_m1_gives_higher_load(self):
        """Step 3 sweep truncated to m_max = 1 forces m = 1 and returns
        the higher 120014 N/m load at mode (1, 1)."""
        n_min, m, n = lpb.buckling_mode(D11, D22, D12, D66, A, B,
                                        m_max=1)
        self.assertEqual((m, n), (1, 1))
        self.assertAlmostEqual(n_min, 120014.4, delta=1.0)
        self.assertGreater(n_min, 86852.5)

    def test_step3_minimized_load_not_above_single_modes(self):
        """Step 3 minimized load is at or below every single-mode load
        sampled across the half-wave sweep."""
        n_min, _, _ = lpb.buckling_mode(D11, D22, D12, D66, A, B,
                                        m_max=4, n_max=3)
        for m in range(1, 5):
            for n in range(1, 4):
                self.assertLessEqual(
                    n_min, lpb.critical_load(D11, D22, D12, D66, A, B,
                                             m, n) + 1e-9)

    def test_step3_determinism_repeat_runs(self):
        """Step 3 buckling_mode is deterministic: repeat runs return the
        identical minimized load and governing pair."""
        first = lpb.buckling_mode(D11, D22, D12, D66, A, B)
        second = lpb.buckling_mode(D11, D22, D12, D66, A, B)
        self.assertEqual(first, second)

    def test_step3_tie_resolution_smallest_pair(self):
        """Step 3 tie resolution: with N(1, 1) = N(2, 1) = 12830.49 N/m
        as the minimum, the sweep returns the smallest (m, n) pair,
        (1, 1)."""
        n_min, m, n = lpb.buckling_mode(100.0, 25.0, 20.0, 40.0,
                                        1.0, 0.5)
        self.assertEqual((m, n), (1, 1))
        self.assertAlmostEqual(n_min, 12830.49, delta=0.01)

    def test_step3_tied_pair_loads_equal(self):
        """Step 3 tie setup check: critical_load agrees at the tied modes
        (1, 1) and (2, 1) for the symmetric minimum scenario."""
        n11 = lpb.critical_load(100.0, 25.0, 20.0, 40.0, 1.0, 0.5, 1, 1)
        n21 = lpb.critical_load(100.0, 25.0, 20.0, 40.0, 1.0, 0.5, 2, 1)
        self.assertEqual(n11, n21)

    def test_step3_default_sweep_bounds(self):
        """Step 3 default sweep bounds: DEFAULT_M_MAX = 20 and
        DEFAULT_N_MAX = 20 bound the half-wave mode counts."""
        self.assertEqual(lpb.DEFAULT_M_MAX, 20)
        self.assertEqual(lpb.DEFAULT_N_MAX, 20)

    def test_step3_monotonic_rising_d11(self):
        """Step 3 sweep responds to stiffness: the critical load rises
        when D11 rises from 200 to 250 N m on the worked example."""
        low = lpb.critical_load(D11, D22, D12, D66, A, B, 2, 1)
        high = lpb.critical_load(250.0, D22, D12, D66, A, B, 2, 1)
        self.assertGreater(high, low)

    def test_step3_monotonic_rising_d22(self):
        """Step 3 sweep responds to stiffness: the critical load rises
        when D22 rises from 120 to 150 N m on the worked example."""
        low = lpb.critical_load(D11, D22, D12, D66, A, B, 2, 1)
        high = lpb.critical_load(D11, 150.0, D12, D66, A, B, 2, 1)
        self.assertGreater(high, low)

    def test_step3_monotonic_narrower_width(self):
        """Step 3 sweep responds to geometry: a narrower width b = 0.2 m
        raises the critical load on the worked example."""
        wide = lpb.critical_load(D11, D22, D12, D66, A, B, 2, 1)
        narrow = lpb.critical_load(D11, D22, D12, D66, A, 0.2, 2, 1)
        self.assertGreater(narrow, wide)


class TestBucklingMargin(unittest.TestCase):
    """Workflow step 4: the stability margin against the applied load."""

    def test_step4_margin_worked_example(self):
        """Step 4 buckling_margin at 40 kN/m applied returns 2.171,
        within 0.01 of the prep anchor 2.17."""
        margin = lpb.buckling_margin(D11, D22, D12, D66, A, B, 40000.0)
        self.assertAlmostEqual(margin, 2.171, delta=0.01)

    def test_step4_margin_is_load_ratio(self):
        """Step 4 buckling_margin equals the minimized critical load over
        the applied in-plane compression load."""
        n_min, _, _ = lpb.buckling_mode(D11, D22, D12, D66, A, B)
        applied = 40000.0
        margin = lpb.buckling_margin(D11, D22, D12, D66, A, B, applied)
        self.assertAlmostEqual(margin, n_min / applied, delta=1e-9)

    def test_step4_margin_below_unity_buckles(self):
        """Step 4 margin drops below 1.0 when the applied load exceeds
        the minimized critical load on the worked example."""
        margin = lpb.buckling_margin(D11, D22, D12, D66, A, B, 100000.0)
        self.assertLess(margin, 1.0)

    def test_step4_margin_rises_as_applied_falls(self):
        """Step 4 buckling_margin is monotone in the applied load: half
        the applied load doubles the margin on the worked example."""
        m1 = lpb.buckling_margin(D11, D22, D12, D66, A, B, 40000.0)
        m2 = lpb.buckling_margin(D11, D22, D12, D66, A, B, 20000.0)
        self.assertAlmostEqual(m2 / m1, 2.0, delta=1e-9)


class TestValueErrorRejection(unittest.TestCase):
    """Workflow step 6 contract coverage: non-physical inputs raise
    ValueError instead of returning numbers."""

    def test_step6_valueerror_zero_d11(self):
        """Step 6 rejection: a zero D11 raises ValueError in
        critical_load."""
        with self.assertRaises(ValueError):
            lpb.critical_load(0.0, D22, D12, D66, A, B, 2, 1)

    def test_step6_valueerror_negative_d22(self):
        """Step 6 rejection: a negative D22 raises ValueError in
        critical_load."""
        with self.assertRaises(ValueError):
            lpb.critical_load(D11, -10.0, D12, D66, A, B, 2, 1)

    def test_step6_valueerror_zero_d12(self):
        """Step 6 rejection: a zero D12 raises ValueError in
        critical_load."""
        with self.assertRaises(ValueError):
            lpb.critical_load(D11, D22, 0.0, D66, A, B, 2, 1)

    def test_step6_valueerror_negative_d66(self):
        """Step 6 rejection: a negative D66 raises ValueError in
        critical_load."""
        with self.assertRaises(ValueError):
            lpb.critical_load(D11, D22, D12, -5.0, A, B, 2, 1)

    def test_step6_valueerror_zero_length_a(self):
        """Step 6 rejection: a zero load-direction length a raises
        ValueError in critical_load."""
        with self.assertRaises(ValueError):
            lpb.critical_load(D11, D22, D12, D66, 0.0, B, 2, 1)

    def test_step6_valueerror_negative_width_b(self):
        """Step 6 rejection: a negative width b raises ValueError in
        critical_load."""
        with self.assertRaises(ValueError):
            lpb.critical_load(D11, D22, D12, D66, A, -0.25, 2, 1)

    def test_step6_valueerror_zero_mode_m(self):
        """Step 6 rejection: m = 0 raises ValueError in critical_load."""
        with self.assertRaises(ValueError):
            lpb.critical_load(D11, D22, D12, D66, A, B, 0, 1)

    def test_step6_valueerror_zero_mode_n(self):
        """Step 6 rejection: n = 0 raises ValueError in critical_load."""
        with self.assertRaises(ValueError):
            lpb.critical_load(D11, D22, D12, D66, A, B, 2, 0)

    def test_step6_valueerror_non_integer_mode(self):
        """Step 6 rejection: a fractional half-wave count m = 1.5 raises
        ValueError in critical_load."""
        with self.assertRaises(ValueError):
            lpb.critical_load(D11, D22, D12, D66, A, B, 1.5, 1)

    def test_step6_valueerror_zero_applied_load(self):
        """Step 6 rejection: a zero applied load raises ValueError in
        buckling_margin."""
        with self.assertRaises(ValueError):
            lpb.buckling_margin(D11, D22, D12, D66, A, B, 0.0)

    def test_step6_valueerror_negative_applied_load(self):
        """Step 6 rejection: a negative applied load raises ValueError in
        buckling_margin."""
        with self.assertRaises(ValueError):
            lpb.buckling_margin(D11, D22, D12, D66, A, B, -40000.0)

    def test_step6_valueerror_zero_mmax(self):
        """Step 6 rejection: m_max = 0 raises ValueError in
        buckling_mode."""
        with self.assertRaises(ValueError):
            lpb.buckling_mode(D11, D22, D12, D66, A, B, m_max=0)

    def test_step6_valueerror_fractional_nmax(self):
        """Step 6 rejection: a fractional n_max raises ValueError in
        buckling_mode."""
        with self.assertRaises(ValueError):
            lpb.buckling_mode(D11, D22, D12, D66, A, B, n_max=2.5)


if __name__ == "__main__":
    unittest.main()
