"""Contract test for beam-column-analysis (wave-41, structures/fem).

Offline, deterministic, stdlib only. Runs via:
    python3 scripts/test_beam_column_analysis.py

The test suite exercises the numbered SKILL.md workflow end to end: the
limit load case framing at the critical station (step 1), the Euler load
traverse that computes P_E = pi^2 E I / (K L)^2 and the axial ratio P/P_E
(step 2), the moment amplification traverse that grows the primary moment
by delta = c_m / (1 - P/P_E) (step 3), the secant-formula stress traverse
that evaluates the peak compressive stress of the eccentrically loaded
column from the load eccentricity, the radius of gyration and the axial
stress P/A (step 4), and the interaction-ratio traverse that returns the
axial-plus-bending ratio, the margin of safety 1/ratio - 1 and the pass
verdict (step 5). Step 6 of the workflow, the contract-test confirmation,
is this file.

Worked-example anchors (wave-41 spec, real module outputs recorded):
steel member E = 200 GPa, I = 1e-6 m^4, A = 1e-3 m^2, L = 3.0 m,
pinned-pinned K = 1.0, r = sqrt(I/A) = 0.0316228 m, c = 2 r = 0.0632456 m,
P = 100 kN, M = 1 kN m at e = M/P = 10 mm:
  P_E     = 219324.542 N          (K 0.5 -> 877298.169 N, K 2.0 -> 54831.136 N)
  delta   = 1.838051 at 100 kN    (1.295291 at 50 kN, 3.163736 at 150 kN)
  sigma   = 2.295230e8 Pa         (229.5230 MPa, ecc = 0 -> 1.0e8 Pa exact)
  M_cap   = 3952.847 N m          (yield moment 250 MPa section)
  ratio   = 0.920939, margin +0.085848, PASS at P = 100 kN, M = 1 kN m
  overload P = 130 kN, M = 1.2 kN m: ratio 1.3381, margin -0.2527, FAIL
  M = 0 degeneration: ratio 0.455945, margin +1.193245 (the pure-axial
  margin-of-safety identity of the buckling-analysis anchor).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import beam_column_analysis_logic as bca

E_STEEL = 200e9
I_BAR = 1e-6
A_BAR = 1e-3
L_BAR = 3.0
R_BAR = math.sqrt(I_BAR / A_BAR)      # 0.03162277660168379 m
C_BAR = 2.0 * R_BAR                    # 0.06324555320336758 m
K_PIN = 1.0
P_E_ANCHOR = 219324.54224643015        # euler_load(200e9, 1e-6, 3.0)
M_CAP_ANCHOR = 3952.8470752104745      # 250e6 * I_BAR / C_BAR
P_WORK = 100e3
M_WORK = 1000.0


class BeamColumnEulerLoadTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the Euler load traverse."""

    def test_euler_load_anchor_pinned_pinned_worked_example(self):
        """Euler load traverse anchor: euler_load(200e9, 1e-6, 3.0) returns
        219324.542 N, the P_E that feeds the amplification denominator of
        steps 3 and 5."""
        self.assertAlmostEqual(bca.euler_load(E_STEEL, I_BAR, L_BAR, K_PIN),
                               P_E_ANCHOR, delta=1e-3)

    def test_euler_load_effective_k_scaling(self):
        """Euler load traverse, K scaling: K = 0.5 (fixed-fixed) gives
        877298.169 N and K = 2.0 (cantilever) gives 54831.136 N, each
        within 1e-3 N."""
        self.assertAlmostEqual(bca.euler_load(E_STEEL, I_BAR, L_BAR, 0.5),
                               877298.169, delta=1e-3)
        self.assertAlmostEqual(bca.euler_load(E_STEEL, I_BAR, L_BAR, 2.0),
                               54831.136, delta=1e-3)

    def test_euler_load_k_squared_ratio_exact(self):
        """Euler load traverse identity: the pinned-pinned to fixed-fixed
        load ratio is 4.0 exactly because K enters squared."""
        p_pin = bca.euler_load(E_STEEL, I_BAR, L_BAR, 1.0)
        p_fix = bca.euler_load(E_STEEL, I_BAR, L_BAR, 0.5)
        self.assertEqual(p_fix / p_pin, 4.0)

    def test_euler_load_valueerror_non_physical(self):
        """Euler load traverse rejection: zero or negative modulus, area
        moment, length and effective length factor each raise ValueError."""
        for bad_e in (0.0, -200e9):
            with self.assertRaises(ValueError):
                bca.euler_load(bad_e, I_BAR, L_BAR)
        for bad_i in (0.0, -1e-6):
            with self.assertRaises(ValueError):
                bca.euler_load(E_STEEL, bad_i, L_BAR)
        for bad_l in (0.0, -3.0):
            with self.assertRaises(ValueError):
                bca.euler_load(E_STEEL, I_BAR, bad_l)
        for bad_k in (0.0, -1.0):
            with self.assertRaises(ValueError):
                bca.euler_load(E_STEEL, I_BAR, L_BAR, bad_k)


class BeamColumnMomentAmplificationTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the moment amplification traverse."""

    def test_moment_amplification_anchor_100_kilonewton(self):
        """Moment amplification traverse anchor: at P = 100 kN the factor
        delta = c_m / (1 - P/P_E) returns 1.838051 within 1e-6, so the
        amplified primary moment is 1.838 kN m."""
        self.assertAlmostEqual(
            bca.moment_amplification(P_WORK, P_E_ANCHOR), 1.838051, delta=1e-6)

    def test_moment_amplification_series_monotone_increasing(self):
        """Moment amplification traverse series: 1.295291 at 50 kN and
        3.163736 at 150 kN within 1e-6, and the factor rises monotonically
        with the axial load toward the P_E pole."""
        d50 = bca.moment_amplification(50e3, P_E_ANCHOR)
        d100 = bca.moment_amplification(100e3, P_E_ANCHOR)
        d150 = bca.moment_amplification(150e3, P_E_ANCHOR)
        self.assertAlmostEqual(d50, 1.295291, delta=1e-6)
        self.assertAlmostEqual(d150, 3.163736, delta=1e-6)
        self.assertLess(d50, d100)
        self.assertLess(d100, d150)

    def test_moment_amplification_zero_load_exact_one(self):
        """Moment amplification traverse limit: the factor is 1.0 exactly at
        zero axial load, where no amplification occurs."""
        self.assertEqual(bca.moment_amplification(0.0, P_E_ANCHOR), 1.0)

    def test_moment_amplification_cm_factor_scaling(self):
        """Moment amplification traverse, equivalent moment factor: c_m = 0.85
        scales the worst-case constant-moment factor linearly, since
        delta = c_m / (1 - P/P_E)."""
        base = bca.moment_amplification(P_WORK, P_E_ANCHOR)
        scaled = bca.moment_amplification(P_WORK, P_E_ANCHOR, c_m=0.85)
        self.assertAlmostEqual(scaled, 0.85 * base, places=12)

    def test_moment_amplification_valueerror_pole_and_non_physical(self):
        """Moment amplification traverse rejection: the factor raises
        ValueError at p = P_E and p > P_E (the divergence pole), and for
        negative p, non-positive p_euler and non-positive c_m."""
        with self.assertRaises(ValueError):
            bca.moment_amplification(P_E_ANCHOR, P_E_ANCHOR)
        with self.assertRaises(ValueError):
            bca.moment_amplification(P_E_ANCHOR + 1.0, P_E_ANCHOR)
        with self.assertRaises(ValueError):
            bca.moment_amplification(-1.0, P_E_ANCHOR)
        for bad_pe in (0.0, -1.0):
            with self.assertRaises(ValueError):
                bca.moment_amplification(P_WORK, bad_pe)
        for bad_cm in (0.0, -0.5):
            with self.assertRaises(ValueError):
                bca.moment_amplification(P_WORK, P_E_ANCHOR, c_m=bad_cm)

    def test_amplified_moment_and_utilization_bridge_steps_3_to_5(self):
        """Moment amplification traverse bridging steps 3 and 5 of the
        workflow: the amplified moment delta * M is 1838.0506 N m, the
        unamplified bending utilization M / M_cap is 0.252982, the amplified
        utilization delta * M / M_cap is 0.464994, and that amplified
        utilization equals the bending term of the step 5 interaction ratio
        to machine precision."""
        delta = bca.moment_amplification(P_WORK, P_E_ANCHOR)
        m_amp = delta * M_WORK
        self.assertAlmostEqual(m_amp, 1838.050564597843, places=6)
        util_plain = M_WORK / M_CAP_ANCHOR
        util_amp = delta * M_WORK / M_CAP_ANCHOR
        self.assertAlmostEqual(util_plain, 0.252982, places=5)
        self.assertAlmostEqual(util_amp, 0.464994, places=5)
        res = bca.interaction_check(P_WORK, P_E_ANCHOR, M_WORK,
                                    M_CAP_ANCHOR, P_E_ANCHOR)
        bending_term = res["ratio"] - P_WORK / P_E_ANCHOR
        self.assertAlmostEqual(bending_term, util_amp, places=9)


class BeamColumnSecantStressTests(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the secant-formula stress traverse."""

    def test_secant_stress_worked_example(self):
        """Secant-formula stress traverse anchor: the peak compressive stress
        of the column loaded at e = 10 mm eccentricity is 2.295230e8 Pa
        (229.5230 MPa), within 1e2 Pa, at 0.9181 of the 250 MPa yield."""
        sigma = bca.secant_stress(P_WORK, A_BAR, 0.010, C_BAR, R_BAR,
                                  L_BAR, E_STEEL, K_PIN)
        self.assertAlmostEqual(sigma, 2.295230e8, delta=1e2)

    def test_secant_stress_ecc_zero_pure_axial_exact(self):
        """Secant-formula stress traverse consistency limit: at ecc = 0 the
        function returns P / A = 1.0e8 Pa exactly, the pure axial stress."""
        sigma = bca.secant_stress(P_WORK, A_BAR, 0.0, C_BAR, R_BAR,
                                  L_BAR, E_STEEL, K_PIN)
        self.assertEqual(sigma, 1.0e8)

    def test_secant_stress_monotone_in_eccentricity(self):
        """Secant-formula stress traverse monotonicity: at fixed axial load
        the peak stress rises as the load eccentricity increases from 5 mm
        through 10 mm to 15 mm."""
        s5 = bca.secant_stress(P_WORK, A_BAR, 0.005, C_BAR, R_BAR,
                               L_BAR, E_STEEL, K_PIN)
        s10 = bca.secant_stress(P_WORK, A_BAR, 0.010, C_BAR, R_BAR,
                                L_BAR, E_STEEL, K_PIN)
        s15 = bca.secant_stress(P_WORK, A_BAR, 0.015, C_BAR, R_BAR,
                                L_BAR, E_STEEL, K_PIN)
        self.assertLess(s5, s10)
        self.assertLess(s10, s15)
        self.assertGreater(s10, 1.0e8)

    def test_secant_argument_pi_half_at_euler_pole(self):
        """Secant-formula stress traverse divergence consistency: the secant
        argument (K L / (2 r)) sqrt(P / (E A)) equals pi/2 = 1.570796 rad at
        P = P_E, the same load at which the moment amplification factor of
        step 3 diverges."""
        arg = (K_PIN * L_BAR / (2.0 * R_BAR)) * math.sqrt(
            P_E_ANCHOR / (E_STEEL * A_BAR))
        self.assertAlmostEqual(arg, math.pi / 2.0, places=9)

    def test_secant_stress_divergence_near_euler_load(self):
        """Secant-formula stress traverse near the pole: at P = 0.999 P_E the
        peak stress is orders of magnitude above the 100 kN working value,
        showing the divergence as the axial load approaches the Euler
        load."""
        near = 0.999 * P_E_ANCHOR
        sigma_near = bca.secant_stress(near, A_BAR, 0.010, C_BAR, R_BAR,
                                       L_BAR, E_STEEL, K_PIN)
        sigma_work = bca.secant_stress(P_WORK, A_BAR, 0.010, C_BAR, R_BAR,
                                       L_BAR, E_STEEL, K_PIN)
        self.assertGreater(sigma_near, 100.0 * sigma_work)

    def test_secant_stress_overload_exceeds_yield(self):
        """Secant-formula stress traverse overload case: at P = 130 kN with
        M = 1.2 kN m (e = 9.23 mm) the peak stress is 344.611 MPa, above the
        250 MPa yield strength, so the member fails the peak stress check of
        step 4."""
        sigma = bca.secant_stress(130e3, A_BAR, 1200.0 / 130e3, C_BAR,
                                  R_BAR, L_BAR, E_STEEL, K_PIN)
        self.assertAlmostEqual(sigma, 3.446111170502527e8, delta=1e4)
        self.assertGreater(sigma, 250e6)

    def test_secant_stress_valueerror_above_pole(self):
        """Secant-formula stress traverse rejection at the pole: p = P_E + 1.0
        N is strictly above the Euler load, the secant argument passes
        pi/2, and the guard raises ValueError."""
        with self.assertRaises(ValueError):
            bca.secant_stress(P_E_ANCHOR + 1.0, A_BAR, 0.010, C_BAR, R_BAR,
                              L_BAR, E_STEEL, K_PIN)

    def test_secant_stress_valueerror_non_physical(self):
        """Secant-formula stress traverse rejection: zero or negative p,
        area, c, r, l, E and K, and negative eccentricity, each raise
        ValueError before any trigonometric evaluation."""
        good = dict(area=A_BAR, ecc=0.010, c=C_BAR, r=R_BAR, l=L_BAR,
                    e_mod=E_STEEL, k=K_PIN)
        cases = [
            dict(p=0.0), dict(p=-100e3), dict(area=0.0), dict(area=-1e-3),
            dict(ecc=-0.001), dict(c=0.0), dict(c=-0.01), dict(r=0.0),
            dict(r=-0.01), dict(l=0.0), dict(l=-3.0), dict(e_mod=0.0),
            dict(e_mod=-200e9), dict(k=0.0), dict(k=-1.0),
        ]
        for over in cases:
            kw = dict(good)
            kw.update(over)
            with self.assertRaises(ValueError):
                bca.secant_stress(kw.pop("p", P_WORK), **kw)


class BeamColumnInteractionTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the interaction-ratio traverse."""

    def test_interaction_check_pass_case(self):
        """Interaction-ratio traverse pass case: at P = 100 kN, M = 1 kN m the
        axial-plus-bending ratio is 0.920939 within 1e-6, the margin of
        safety 1/ratio - 1 is +0.085848, and the verdict is pass True."""
        res = bca.interaction_check(P_WORK, P_E_ANCHOR, M_WORK,
                                    M_CAP_ANCHOR, P_E_ANCHOR)
        self.assertAlmostEqual(res["ratio"], 0.920939, delta=1e-6)
        self.assertAlmostEqual(res["margin"], 0.085848, delta=1e-6)
        self.assertTrue(res["pass"])

    def test_interaction_check_overload_fail_case(self):
        """Interaction-ratio traverse overload: at P = 130 kN, M = 1.2 kN m
        the ratio is 1.3381 within 1e-4, the margin -0.2527, and the verdict
        is fail False."""
        res = bca.interaction_check(130e3, P_E_ANCHOR, 1200.0,
                                    M_CAP_ANCHOR, P_E_ANCHOR)
        self.assertAlmostEqual(res["ratio"], 1.3381, delta=1e-4)
        self.assertAlmostEqual(res["margin"], -0.2527, delta=1e-4)
        self.assertFalse(res["pass"])

    def test_interaction_check_pure_axial_identity(self):
        """Interaction-ratio traverse degeneration: with m_applied = 0 the
        ratio is 0.455945 and the margin +1.193245 within 1e-6, exactly the
        buckling-analysis margin of safety MS = Pcr / P - 1 = 1.19 anchor of
        the pure-axial sibling."""
        res = bca.interaction_check(P_WORK, P_E_ANCHOR, 0.0,
                                    M_CAP_ANCHOR, P_E_ANCHOR)
        self.assertAlmostEqual(res["ratio"], 0.455945, delta=1e-6)
        self.assertAlmostEqual(res["margin"], 1.193245, delta=1e-6)
        self.assertTrue(res["pass"])

    def test_interaction_check_inclusive_boundary(self):
        """Interaction-ratio traverse inclusive boundary: a crafted moment
        m = M_cap (1 - P/P_E) (1 - P/P_cr) drives the ratio to 1.0 exactly
        and the margin to zero, and the pass verdict is True at the
        inclusive ratio = 1.0 limit."""
        m_edge = (M_CAP_ANCHOR * (1.0 - P_WORK / P_E_ANCHOR)
                  * (1.0 - P_WORK / P_E_ANCHOR))
        res = bca.interaction_check(P_WORK, P_E_ANCHOR, m_edge,
                                    M_CAP_ANCHOR, P_E_ANCHOR)
        self.assertAlmostEqual(res["ratio"], 1.0, places=9)
        self.assertAlmostEqual(res["margin"], 0.0, places=8)
        self.assertTrue(res["pass"])

    def test_interaction_check_dict_keys_exact(self):
        """Interaction-ratio traverse output contract: the returned dict keys
        are exactly ratio, margin, pass in that order, with no extras."""
        res = bca.interaction_check(P_WORK, P_E_ANCHOR, M_WORK,
                                    M_CAP_ANCHOR, P_E_ANCHOR)
        self.assertEqual(list(res.keys()), ["ratio", "margin", "pass"])

    def test_interaction_check_margin_recomputed(self):
        """Interaction-ratio traverse identity: the margin of safety equals
        1/ratio - 1 recomputed from the returned ratio."""
        res = bca.interaction_check(P_WORK, P_E_ANCHOR, M_WORK,
                                    M_CAP_ANCHOR, P_E_ANCHOR)
        self.assertAlmostEqual(res["margin"], 1.0 / res["ratio"] - 1.0,
                               places=12)

    def test_interaction_check_valueerror_pole_and_non_physical(self):
        """Interaction-ratio traverse rejection: the check raises ValueError
        at p = P_E and above, for negative axial load and applied moment,
        and for non-positive p_cr, m_capacity and p_euler."""
        with self.assertRaises(ValueError):
            bca.interaction_check(P_E_ANCHOR, P_E_ANCHOR, M_WORK,
                                  M_CAP_ANCHOR, P_E_ANCHOR)
        with self.assertRaises(ValueError):
            bca.interaction_check(P_E_ANCHOR + 1.0, P_E_ANCHOR, M_WORK,
                                  M_CAP_ANCHOR, P_E_ANCHOR)
        with self.assertRaises(ValueError):
            bca.interaction_check(-1.0, P_E_ANCHOR, M_WORK,
                                  M_CAP_ANCHOR, P_E_ANCHOR)
        with self.assertRaises(ValueError):
            bca.interaction_check(P_WORK, 0.0, M_WORK,
                                  M_CAP_ANCHOR, P_E_ANCHOR)
        with self.assertRaises(ValueError):
            bca.interaction_check(P_WORK, P_E_ANCHOR, -1.0,
                                  M_CAP_ANCHOR, P_E_ANCHOR)
        with self.assertRaises(ValueError):
            bca.interaction_check(P_WORK, P_E_ANCHOR, M_WORK,
                                  0.0, P_E_ANCHOR)
        with self.assertRaises(ValueError):
            bca.interaction_check(P_WORK, P_E_ANCHOR, M_WORK,
                                  M_CAP_ANCHOR, 0.0)


class BeamColumnRobustnessTests(unittest.TestCase):
    """Cross-step determinism and verdict typing checks (workflow steps 2 to
    6 of the SKILL.md body)."""

    def test_determinism_repeated_full_evaluation(self):
        """Contract-test confirmation (step 6 of the workflow): repeated
        evaluation of the Euler load traverse, the moment amplification
        traverse, the secant-formula stress traverse and the
        interaction-ratio traverse returns bit-identical values."""
        first = bca.interaction_check(P_WORK, P_E_ANCHOR, M_WORK,
                                      M_CAP_ANCHOR, P_E_ANCHOR)
        second = bca.interaction_check(P_WORK, P_E_ANCHOR, M_WORK,
                                       M_CAP_ANCHOR, P_E_ANCHOR)
        self.assertEqual(first, second)
        self.assertEqual(bca.euler_load(E_STEEL, I_BAR, L_BAR),
                         bca.euler_load(E_STEEL, I_BAR, L_BAR))
        self.assertEqual(bca.moment_amplification(P_WORK, P_E_ANCHOR),
                         bca.moment_amplification(P_WORK, P_E_ANCHOR))
        s1 = bca.secant_stress(P_WORK, A_BAR, 0.010, C_BAR, R_BAR,
                               L_BAR, E_STEEL)
        s2 = bca.secant_stress(P_WORK, A_BAR, 0.010, C_BAR, R_BAR,
                               L_BAR, E_STEEL)
        self.assertEqual(s1, s2)

    def test_pass_verdict_is_boolean(self):
        """Interaction-ratio traverse verdict type: the pass value is a bool,
        never a pass or fail verdict string."""
        res = bca.interaction_check(P_WORK, P_E_ANCHOR, M_WORK,
                                    M_CAP_ANCHOR, P_E_ANCHOR)
        self.assertIsInstance(res["pass"], bool)


if __name__ == "__main__":
    unittest.main()
