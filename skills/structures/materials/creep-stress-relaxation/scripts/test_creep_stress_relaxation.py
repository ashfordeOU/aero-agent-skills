#!/usr/bin/env python3
"""Gate 3 contract test: creep stress relaxation of preloaded parts.

Exercises scripts/creep_stress_relaxation_logic.py (stdlib unittest,
offline, deterministic). Contract: the fixed-total-strain relaxation of
an initially elastic preload stress under Norton power-law creep, the
relaxed stress from the closed-form integral of the relaxation ODE
d(sigma)/dt = -E*A*sigma^n*exp(-Q/(R*T)), the retained-preload
fraction, the time to relax to a target fraction, and the
preload-retention margin verdict against a required retained fraction;
every non-physical input raises ValueError.

Workflow coverage: step 1 (fix the operating point: preload stress in
Pa, temperature in K, hold time in s, material selection) is exercised
by the anchor tests; step 2 (the closed-form relaxation integral,
relaxed_stress) by test_anchor_* and test_zero_hold_time; step 3 (the
retained-preload fraction, retained_fraction) by test_anchor_retained*;
step 4 (the time-to-fraction inversion, time_to_relaxed_fraction) by
test_time_to_fraction* and the round trips; step 5 (the
preload-retention margin verdict, preload_margin) by test_margin*;
step 6 (interpretation: PASS holds, FAIL needs re-torque, the
steady-state-only assumption and the power-law tail) by test_monotone*
and test_long_time_tail; step 7 (the contract test itself) by this file.

Anchors (default alloy, sigma_0 = 200 MPa = 2.0e8 Pa, T = 700 C =
973.15 K unless noted):
- 100 h (3.6e5 s): relaxed 114410840.82577138 Pa, retained 0.5720542041288569
- 1000 h (3.6e6 s): relaxed 78364659.4406817 Pa, retained 0.39182329720340847
- 600 C and 650 C at 1000 h: 169638258.38946512 and 116399871.02150063 Pa
- time to 0.9/0.8/0.5: 11527.301420325737 / 36800.19442005393 /
  823680.8543417541 s (strictly ordered)
- 1e4 h retained fraction 0.26709127676828587
"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import creep_stress_relaxation_logic as csr  # noqa: E402

SIGMA = 2.0e8  # 200 MPa bolt preload in Pa
T700 = 973.15  # 700 C in K
T650 = 923.15  # 650 C in K
T600 = 873.15  # 600 C in K
HOUR_S = 3600.0

# Default alloy constants (reference-only typicals, Inconel-718 class).
A_DEFAULT = csr.MATERIALS["inconel-718"]["norton_a"]
N_DEFAULT = csr.MATERIALS["inconel-718"]["norton_n"]
Q_DEFAULT = csr.MATERIALS["inconel-718"]["norton_q"]
E_DEFAULT = csr.MATERIALS["inconel-718"]["elastic_modulus"]


def _norton_rate(sigma, temp_k):
    """Norton creep rate A * sigma^n * exp(-Q / (R*T)) from module constants."""
    return A_DEFAULT * sigma ** N_DEFAULT * math.exp(-Q_DEFAULT / (csr.R_GAS * temp_k))


class WorkedExampleTest(unittest.TestCase):
    def test_anchor_relaxed_100h(self):
        # Step 2 of the SKILL.md workflow, the closed-form relaxation
        # integral relaxed_stress at the 100 h hold.
        self.assertAlmostEqual(
            csr.relaxed_stress(SIGMA, 3.6e5, T700), 114410840.82577138, delta=1.0
        )

    def test_anchor_relaxed_1000h(self):
        # Step 2 of the SKILL.md workflow at the 1000 h hold: the drop
        # from 0.572 to 0.392 shows the slowing power-law tail.
        self.assertAlmostEqual(
            csr.relaxed_stress(SIGMA, 3.6e6, T700), 78364659.4406817, delta=1.0
        )

    def test_anchor_retained_100h(self):
        # Step 3 of the SKILL.md workflow, the retained-preload fraction
        # after the 100 h hold: 57.21 percent of the preload remains.
        self.assertAlmostEqual(
            csr.retained_fraction(SIGMA, 3.6e5, T700), 0.5720542041288569, delta=1e-6
        )

    def test_anchor_retained_1000h(self):
        # Step 3 of the SKILL.md workflow at 1000 h: 39.18 percent
        # retained against the 200 MPa preload.
        self.assertAlmostEqual(
            csr.retained_fraction(SIGMA, 3.6e6, T700), 0.39182329720340847, delta=1e-6
        )

    def test_anchor_600c_1000h(self):
        # Step 1 (operating point) and step 2 at 600 C: the same alloy
        # retains 0.8482, nearly double the 700 C fraction.
        self.assertAlmostEqual(
            csr.relaxed_stress(SIGMA, 3.6e6, T600), 169638258.38946512, delta=1.0
        )

    def test_anchor_650c_1000h(self):
        # Step 2 at 650 C: 0.5820 retained, the Arrhenius sensitivity of
        # exp(-Q / (R * T)) between the temperature points.
        self.assertAlmostEqual(
            csr.relaxed_stress(SIGMA, 3.6e6, T650), 116399871.02150063, delta=1.0
        )

    def test_anchor_retained_600c_1000h(self):
        # Step 3 at 600 C: 0.8482 retained against the 1000 h hold.
        self.assertAlmostEqual(
            csr.retained_fraction(SIGMA, 3.6e6, T600), 0.8481912919473256, delta=1e-6
        )

    def test_anchor_retained_650c_1000h(self):
        # Step 3 at 650 C: 0.5820 retained.
        self.assertAlmostEqual(
            csr.retained_fraction(SIGMA, 3.6e6, T650), 0.5819993551075031, delta=1e-6
        )


class TimeToFractionTest(unittest.TestCase):
    def test_time_to_090(self):
        # Step 4 of the SKILL.md workflow, the time-to-fraction inversion
        # of the closed form at 0.9 of the preload.
        self.assertAlmostEqual(
            csr.time_to_relaxed_fraction(0.9, SIGMA, T700), 11527.301420325737,
            delta=1e-4,
        )

    def test_time_to_080(self):
        # Step 4 at 0.8 of the preload: 36800.19 s = 10.22 h.
        self.assertAlmostEqual(
            csr.time_to_relaxed_fraction(0.8, SIGMA, T700), 36800.19442005393,
            delta=1e-4,
        )

    def test_time_to_050(self):
        # Step 4 at 0.5 of the preload: 823680.85 s = 228.8 h.
        self.assertAlmostEqual(
            csr.time_to_relaxed_fraction(0.5, SIGMA, T700), 823680.8543417541,
            delta=1e-3,
        )

    def test_time_strictly_ordered(self):
        # Step 4 monotonicity: relaxing to a smaller retained fraction
        # takes longer, 3.2 h < 10.2 h < 228.8 h.
        t09 = csr.time_to_relaxed_fraction(0.9, SIGMA, T700)
        t08 = csr.time_to_relaxed_fraction(0.8, SIGMA, T700)
        t05 = csr.time_to_relaxed_fraction(0.5, SIGMA, T700)
        self.assertLess(t09, t08)
        self.assertLess(t08, t05)

    def test_time_to_1_0_is_zero(self):
        # Step 4 limit: relaxing to 100 percent of the preload needs a
        # zero hold; fraction 1.0 is the allowed upper edge of (0, 1].
        self.assertAlmostEqual(
            csr.time_to_relaxed_fraction(1.0, SIGMA, T700), 0.0, delta=1e-12
        )

    def test_round_trip_recovers_fraction(self):
        # Step 4 and step 3 round trip: relaxing for the time computed by
        # time_to_relaxed_fraction(f, ...) and reading the retained
        # fraction recovers f for several targets.
        for f in (0.3, 0.5, 0.8, 0.95):
            t = csr.time_to_relaxed_fraction(f, SIGMA, T700)
            self.assertAlmostEqual(csr.retained_fraction(SIGMA, t, T700), f, delta=1e-9)

    def test_round_trip_anchor_080(self):
        # Step 3 and step 4 round trip at the worked-example 0.8 anchor.
        t80 = csr.time_to_relaxed_fraction(0.8, SIGMA, T700)
        self.assertAlmostEqual(csr.retained_fraction(SIGMA, t80, T700), 0.8, delta=1e-9)


class MarginTest(unittest.TestCase):
    def test_margin_pass_035(self):
        # Step 5 of the SKILL.md workflow, the preload-retention margin
        # check: 39.18 percent retained against a 35 percent requirement
        # PASSes with margin 0.1195.
        result = csr.preload_margin(SIGMA, 3.6e6, T700, 0.35)
        self.assertEqual(result["verdict"], "PASS")
        self.assertAlmostEqual(result["retained_fraction"], 0.39182329720340847,
                               delta=1e-9)
        self.assertAlmostEqual(result["margin"], 0.11949513486688135, delta=1e-9)

    def test_margin_fail_045(self):
        # Step 5 verdict at a 45 percent requirement: retention is short,
        # the joint needs re-torque or a higher initial preload.
        result = csr.preload_margin(SIGMA, 3.6e6, T700, 0.45)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertAlmostEqual(result["margin"], -0.12928156177020345, delta=1e-9)

    def test_margin_boundary_equality_passes(self):
        # Step 5 boundary: a required fraction equal to the achieved
        # retention gives margin 0.0 and PASS (margin >= 0 includes
        # equality); never assert at exact float equality.
        req = 0.39182329720340847
        result = csr.preload_margin(SIGMA, 3.6e6, T700, req)
        self.assertAlmostEqual(result["margin"], 0.0, delta=1e-12)
        self.assertEqual(result["verdict"], "PASS")

    def test_margin_scale_with_requirement(self):
        # Step 5 sensitivity: the margin falls monotonically as the
        # required fraction rises toward 1.
        m_low = csr.preload_margin(SIGMA, 3.6e6, T700, 0.2)["margin"]
        m_mid = csr.preload_margin(SIGMA, 3.6e6, T700, 0.35)["margin"]
        m_high = csr.preload_margin(SIGMA, 3.6e6, T700, 0.45)["margin"]
        self.assertGreater(m_low, m_mid)
        self.assertGreater(m_mid, m_high)


class IdentityTest(unittest.TestCase):
    def test_zero_hold_time(self):
        # Step 2 limit check: a zero hold time returns the initial
        # preload stress (199999999.9999998 Pa, float-power roundoff of
        # 2.0e8, within 1e-6 relative).
        self.assertAlmostEqual(
            csr.relaxed_stress(SIGMA, 0.0, T700), SIGMA, delta=SIGMA * 1e-6
        )
        self.assertAlmostEqual(csr.retained_fraction(SIGMA, 0.0, T700), 1.0,
                               delta=1e-12)

    def test_initial_relaxation_rate(self):
        # Step 2 and step 6: the stress first falls at the elastic rate
        # of the Norton creep strain, d(sigma)/dt = -E * eps_dot; the
        # 1 ms finite difference matches E * eps_dot within 1e-6 relative.
        eps0 = _norton_rate(SIGMA, T700)
        e_eps0 = E_DEFAULT * eps0  # 2549.5311550955244 Pa/s
        fd = (csr.relaxed_stress(SIGMA, 1e-3, T700) - SIGMA) / 1e-3
        self.assertAlmostEqual(fd, -e_eps0, delta=abs(e_eps0) * 1e-6)

    def test_linear_branch_equals_exponential(self):
        # Step 2 n = 1 branch: with the Newtonian override K = E * A =
        # 1.05e-4 1/s the relaxed stress equals sigma_0 * exp(-K * t)
        # within 1e-12 relative at several hold times.
        ov = {"norton_a": 5.0e-16, "norton_n": 1.0, "norton_q": 0.0}
        k_lin = E_DEFAULT * 5.0e-16
        for t in (1e3, 1e4, 3.6e5):
            got = csr.relaxed_stress(SIGMA, t, T600, ov)
            want = SIGMA * math.exp(-k_lin * t)
            self.assertAlmostEqual(got, want, delta=abs(want) * 1e-12)

    def test_linear_branch_anchors(self):
        # Step 2 anchors on the n = 1 branch at 600 C: 180064904.51725313
        # Pa at 1e3 s and 69987549.82223107 Pa at 1e4 s.
        ov = {"norton_a": 5.0e-16, "norton_n": 1.0, "norton_q": 0.0}
        self.assertAlmostEqual(
            csr.relaxed_stress(SIGMA, 1e3, T600, ov), 180064904.51725313, delta=1e-3
        )
        self.assertAlmostEqual(
            csr.relaxed_stress(SIGMA, 1e4, T600, ov), 69987549.82223107, delta=1e-3
        )

    def test_n_to_one_limit(self):
        # Step 2 continuity: the power branch at n = 1 + 1e-9 tends to
        # the exponential branch; 69987546.61987615 against the exact
        # exponential 69987549.82223107 within 1e-6 relative is the
        # epsilon-perturbation gap, not a model error.
        ov_lim = {"norton_a": 5.0e-16, "norton_n": 1.0 + 1e-9, "norton_q": 0.0}
        ov_lin = {"norton_a": 5.0e-16, "norton_n": 1.0, "norton_q": 0.0}
        got = csr.relaxed_stress(SIGMA, 1e4, T600, ov_lim)
        want = csr.relaxed_stress(SIGMA, 1e4, T600, ov_lin)
        self.assertAlmostEqual(got, want, delta=abs(want) * 1e-6)


class DecayTest(unittest.TestCase):
    def test_monotone_decay_grid(self):
        # Step 6: over the hold grid the relaxed stress falls strictly at
        # every step and stays positive (never reaches zero in finite
        # time for n = 7).
        grid = [0.0, 1e3, 1e4, 3.6e5, 3.6e6, 3.6e7]
        vals = [csr.relaxed_stress(SIGMA, t, T700) for t in grid]
        for prev, cur in zip(vals, vals[1:]):
            self.assertLess(cur, prev)
            self.assertGreater(cur, 0.0)

    def test_long_time_power_law_tail(self):
        # Step 6: at 1e4 h (3.6e7 s) the retained fraction
        # 0.26709127676828587 sits in (0.2, 0.4), the t^(-1/6) tail of
        # the n = 7 power law still positive.
        f = csr.retained_fraction(SIGMA, 3.6e7, T700)
        self.assertAlmostEqual(f, 0.26709127676828587, delta=1e-9)
        self.assertGreater(f, 0.2)
        self.assertLess(f, 0.4)

    def test_temperature_monotonicity(self):
        # Step 1 and step 3: retained fraction after 1000 h falls as the
        # temperature rises over the four operating points, the
        # exp(-Q / (R * T)) Arrhenius sensitivity.
        rets = [csr.retained_fraction(SIGMA, 3.6e6, t) for t in (T600, T650, T700, 1023.15)]
        for prev, cur in zip(rets, rets[1:]):
            self.assertGreater(prev, cur)
        self.assertAlmostEqual(rets[0], 0.8481912919473256, delta=1e-6)
        self.assertAlmostEqual(rets[1], 0.5819993551075031, delta=1e-6)
        self.assertAlmostEqual(rets[2], 0.39182329720340847, delta=1e-6)

    def test_higher_preload_lower_retained_fraction(self):
        # Step 1 and step 3 at fixed temperature and hold: for n > 1 the
        # retained fraction FALLS as the preload rises (100 MPa 0.757,
        # 200 MPa 0.392, 400 MPa 0.196), consistent with the closed-form
        # tail sigma(t) ~ [(n-1)Kt]^(1/(1-n)) that is independent of
        # sigma_0 at long time.
        f_low = csr.retained_fraction(1.0e8, 3.6e6, T700)
        f_mid = csr.retained_fraction(2.0e8, 3.6e6, T700)
        f_high = csr.retained_fraction(4.0e8, 3.6e6, T700)
        self.assertGreater(f_low, f_mid)
        self.assertGreater(f_mid, f_high)

    def test_relaxed_stress_rises_with_preload(self):
        # Step 2 sanity: the absolute relaxed stress after the hold still
        # rises with the initial preload even as the retained fraction
        # falls.
        s100 = csr.relaxed_stress(1.0e8, 3.6e6, T700)
        s200 = csr.relaxed_stress(2.0e8, 3.6e6, T700)
        self.assertGreater(s200, s100)


class MaterialTest(unittest.TestCase):
    def test_default_material_parity_with_override(self):
        # Step 1 material selection: the dict override reproducing the
        # default alloy constants gives the same numbers within 1e-12
        # relative.
        ov = {"norton_a": 2.0e-47, "norton_n": 7.0, "norton_q": 360000.0,
              "elastic_modulus": 2.1e11}
        got = csr.relaxed_stress(SIGMA, 3.6e6, T700, ov)
        want = csr.relaxed_stress(SIGMA, 3.6e6, T700)
        self.assertAlmostEqual(got, want, delta=abs(want) * 1e-12)

    def test_shared_creep_rate_constants(self):
        # Step 1 parity with the creep-rupture sibling: the default alloy
        # Norton rate at 300 MPa and 600 C inside this module equals the
        # creep-rupture anchor 1.2698242552930268e-09 1/s within 1e-6
        # relative, proving the shared constant set (consumed internally
        # through the relaxation coefficient K, never claimed as a
        # standalone product here).
        rate = _norton_rate(3.0e8, T600)
        self.assertAlmostEqual(rate, 1.2698242552930268e-09, delta=1e-15)

    def test_override_subset(self):
        # Step 1: a partial override dict (temperature-independent
        # Newtonian branch) is merged over the default alloy constants.
        ov = {"norton_n": 1.0, "norton_q": 0.0, "norton_a": 5.0e-16}
        k = E_DEFAULT * 5.0e-16
        self.assertAlmostEqual(
            csr.retained_fraction(SIGMA, 1e4, T600, ov), math.exp(-k * 1e4),
            delta=1e-12,
        )

    def test_unknown_material_raises(self):
        # Step 1: an unregistered material name raises ValueError listing
        # the known names.
        with self.assertRaises(ValueError) as ctx:
            csr.relaxed_stress(SIGMA, 3.6e6, T700, "titanium-6al-4v")
        self.assertIn("known: inconel-718", str(ctx.exception))
        self.assertIn("unknown material", str(ctx.exception))


class ValueErrorTest(unittest.TestCase):
    def test_nonpositive_stress_raises(self):
        # Step 1 rejection: a non-positive initial stress is not a
        # physical preload.
        for bad in (0.0, -1.0):
            for fn in (csr.relaxed_stress, csr.retained_fraction):
                with self.assertRaises(ValueError) as ctx:
                    fn(bad, 3.6e6, T700)
                self.assertIn("initial stress must be > 0 Pa", str(ctx.exception))

    def test_negative_time_raises(self):
        # Step 2 rejection: a negative hold time is unphysical.
        for fn in (csr.relaxed_stress, csr.retained_fraction):
            with self.assertRaises(ValueError) as ctx:
                fn(SIGMA, -1.0, T700)
            self.assertIn("hold time must be >= 0 s", str(ctx.exception))

    def test_nonpositive_temperature_raises(self):
        # Step 1 rejection: temperature enters as exp(-Q / (R * T)) and
        # must be positive Kelvin.
        for bad in (0.0, -300.0):
            for fn in (csr.relaxed_stress, csr.retained_fraction):
                with self.assertRaises(ValueError) as ctx:
                    fn(SIGMA, 3.6e6, bad)
                self.assertIn("temperature must be > 0 K", str(ctx.exception))

    def test_fraction_out_of_range_raises(self):
        # Step 4 rejection: the target retained fraction must lie in
        # (0, 1]; 0, negative and above-1 fractions are unphysical.
        for bad in (0.0, -0.2, 1.5):
            with self.assertRaises(ValueError) as ctx:
                csr.time_to_relaxed_fraction(bad, SIGMA, T700)
            self.assertIn("retained fraction must be in (0, 1]", str(ctx.exception))

    def test_required_fraction_out_of_range_raises(self):
        # Step 5 rejection: the required retained fraction must lie in
        # (0, 1] for the margin check.
        for bad in (0.0, -0.2, 1.5):
            with self.assertRaises(ValueError) as ctx:
                csr.preload_margin(SIGMA, 3.6e6, T700, bad)
            self.assertIn("required fraction must be in (0, 1]", str(ctx.exception))

    def test_subunit_exponent_raises(self):
        # Step 2 rejection: a stress exponent below 1 makes the power
        # branch base cross zero at finite time, outside the contract.
        ov = {"norton_n": 0.8}
        for fn in (csr.relaxed_stress, csr.retained_fraction,
                   csr.time_to_relaxed_fraction):
            with self.assertRaises(ValueError) as ctx:
                if fn is csr.time_to_relaxed_fraction:
                    fn(0.5, SIGMA, T700, ov)
                else:
                    fn(SIGMA, 3.6e6, T700, ov)
            self.assertIn("stress exponent must be >= 1", str(ctx.exception))

    def test_non_dict_material_raises(self):
        # Step 1 rejection: a material that is neither a registered name
        # nor a constant dict is rejected.
        with self.assertRaises(ValueError):
            csr.relaxed_stress(SIGMA, 3.6e6, T700, 42)


class DeterminismTest(unittest.TestCase):
    def test_deterministic_repeat_runs(self):
        # Step 7: identical outputs run to run, no randomness anywhere.
        first = csr.relaxed_stress(SIGMA, 3.6e6, T700)
        second = csr.relaxed_stress(SIGMA, 3.6e6, T700)
        self.assertEqual(first, second)
        self.assertEqual(
            csr.time_to_relaxed_fraction(0.8, SIGMA, T700),
            csr.time_to_relaxed_fraction(0.8, SIGMA, T700),
        )

    def test_module_constants(self):
        # Step 1 and step 7: the module carries the pinned gas constant
        # and the reference-only default alloy block.
        self.assertEqual(csr.R_GAS, 8.314)
        self.assertEqual(csr.DEFAULT_MATERIAL, "inconel-718")
        self.assertEqual(A_DEFAULT, 2.0e-47)
        self.assertEqual(N_DEFAULT, 7.0)
        self.assertEqual(Q_DEFAULT, 360000.0)
        self.assertEqual(E_DEFAULT, 2.1e11)


if __name__ == "__main__":
    unittest.main()
