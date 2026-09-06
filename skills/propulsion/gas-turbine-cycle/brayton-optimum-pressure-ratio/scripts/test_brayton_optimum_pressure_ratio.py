"""Contract test for propulsion/gas-turbine-cycle/brayton-optimum-pressure-ratio.

Exercises the SKILL.md workflow of the leaf, whose numbered steps are:
1. Fix the cycle temperature limits T1, T3 and the component efficiencies
   eta_c, eta_t (temperature and efficiency validation), 2. Select the
   ideal max-work pressure ratio with ideal_optimum_pressure_ratio
   (x_opt = sqrt(tau) at tau = T3/T1), 3. Select the lossy max-work
   pressure ratio with optimum_pressure_ratio (x_opt =
   sqrt(tau*eta_c*eta_t), degenerating exactly to the ideal closed form
   at unit efficiencies), 4. Cross-check the zero-work limiting ratio
   with zero_work_pressure_ratio (the factored work form gives r_zero =
   r_opt**2 exactly), 5. Evaluate the net specific work at the optimum
   with net_specific_work and confirm the peak against the
   log-symmetric neighbours of the ratio, 6. Verify the maximum by the
   derivative sign change of d(w)/dx across x_opt, 7. Issue the
   efficiency-versus-work verdict with design_verdict (the ideal
   efficiency rises monotonically with the pressure ratio, no finite
   maximizer, while the lossy-cycle efficiency peaks at the quadratic
   root r_eta_max above r_opt and returns to zero at r_zero), 8. Close
   out with this deterministic contract test.

Worked example: T1 = 288.15 K, T3 = 1500 K (tau = 5.205622), eta_c =
eta_t = 0.87 for the lossy cycle. All numeric asserts are order-safe
tolerances (assertAlmostEqual delta or math.isclose); exact equality is
used only for literal constants and deterministic round-trips. Offline,
deterministic, stdlib unittest only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import brayton_optimum_pressure_ratio_logic as m

T1 = 288.15
T3 = 1500.0
EC = 0.87
ET = 0.87


def _dwdx_closed_form(x):
    """Closed-form d(w)/dx of the factored work form w = cp*T1*(x-1)*
    (A-x)/(x*eta_c), A = tau*eta_c*eta_t: the derivative is
    (cp*T1/eta_c)*(A/x**2 - 1). Uses only public module constants and
    spec quantities, evaluated at the pressure variable x = r**KAPPA."""
    a_value = (T3 / T1) * EC * ET
    return (m.CP * T1 / EC) * (a_value / (x * x) - 1.0)


class TestIdealMaxWorkPressureRatio(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, ideal max-work pressure ratio
    selection: the d(w)/dx = 0 closed form r_opt = tau**1.75 at unit
    component efficiencies."""

    def test_ideal_optimum_pressure_ratio_anchor(self):
        """Ideal max-work pressure ratio selection (step 2) at T1 =
        288.15, T3 = 1500 must return 17.940 within 1e-3, the
        tau**(GAMMA/(2*(GAMMA-1))) closed form with tau = T3/T1."""
        self.assertAlmostEqual(
            m.ideal_optimum_pressure_ratio(T1, T3), 17.940, delta=1.0e-3)

    def test_ideal_optimum_pressure_ratio_scales_with_temperature_ratio(self):
        """Step 2 selection depends only on the cycle temperature limits
        through tau: doubling tau multiplies r_opt by 2**1.75 (the ratio
        of tau powers is exact by the closed form)."""
        r_lo = m.ideal_optimum_pressure_ratio(T1, 1000.0)
        r_hi = m.ideal_optimum_pressure_ratio(T1, 2000.0)
        self.assertAlmostEqual(r_hi / r_lo, 2.0 ** 1.75, delta=1.0e-9)

    def test_optimum_pressure_ratio_degenerates_to_ideal(self):
        """Step 3 degeneracy: optimum_pressure_ratio with eta_c = eta_t =
        1.0 equals ideal_optimum_pressure_ratio (both tau**(1/(2*KAPPA))),
        and the lossy selection x_opt = sqrt(tau*eta_c*eta_t) collapses to
        sqrt(tau) at unit efficiencies."""
        lossless = m.optimum_pressure_ratio(T1, T3, 1.0, 1.0)
        ideal = m.ideal_optimum_pressure_ratio(T1, T3)
        self.assertTrue(math.isclose(lossless, ideal, rel_tol=1.0e-12))
        x_opt_lossless = lossless ** m.KAPPA
        self.assertTrue(math.isclose(
            x_opt_lossless, math.sqrt(T3 / T1), rel_tol=1.0e-12))

    def test_x_opt_is_sqrt_tau_times_eta_product(self):
        """Step 3 closed form: the lossy selection obeys x_opt =
        sqrt(tau*eta_c*eta_t), i.e. r_opt**KAPPA squared equals
        tau*eta_c*eta_t."""
        r_opt = m.optimum_pressure_ratio(T1, T3, EC, ET)
        x_opt = r_opt ** m.KAPPA
        self.assertTrue(math.isclose(
            x_opt * x_opt, (T3 / T1) * EC * ET, rel_tol=1.0e-12))


class TestLossyMaxWorkPressureRatio(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, lossy max-work pressure ratio
    selection with the compressor and turbine component efficiencies."""

    def test_lossy_optimum_pressure_ratio_anchor(self):
        """Lossy max-work pressure ratio selection (step 3) at eta_c =
        eta_t = 0.87 must return 11.019 within 1e-3, pulled below the
        ideal 17.940 by the component efficiencies."""
        self.assertAlmostEqual(
            m.optimum_pressure_ratio(T1, T3, EC, ET), 11.019, delta=1.0e-3)

    def test_losses_pull_the_optimum_down(self):
        """Step 3 ordering: component losses pull x_opt below sqrt(tau),
        so the lossy max-work pressure ratio falls below the ideal one
        (17.940 down to 11.019) at equal 0.87 component efficiencies."""
        ideal = m.ideal_optimum_pressure_ratio(T1, T3)
        lossy = m.optimum_pressure_ratio(T1, T3, EC, ET)
        self.assertLess(lossy, ideal)
        x_opt = lossy ** m.KAPPA
        self.assertLess(x_opt, math.sqrt(T3 / T1))
        self.assertAlmostEqual(ideal, 17.940, delta=1.0e-3)
        self.assertAlmostEqual(lossy, 11.019, delta=1.0e-3)

    def test_optimum_ratio_independent_of_cp(self):
        """Step 3 selection is a pure ratio: CP never enters the optimum,
        and the module constant CP = 1005.0 only scales the net specific
        work quotation in J/kg."""
        self.assertEqual(m.CP, 1005.0)
        self.assertEqual(m.ideal_optimum_pressure_ratio(T1, T3),
                         m.ideal_optimum_pressure_ratio(T1 * 2.0, T3 * 2.0))
        self.assertEqual(m.optimum_pressure_ratio(T1, T3, EC, ET),
                         m.optimum_pressure_ratio(T1 * 2.0, T3 * 2.0, EC, ET))


class TestZeroWorkLimitingRatio(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the zero-work limiting ratio
    cross-check: the factored form w = cp*T1*(x-1)*(A-x)/(x*eta_c) with
    A = tau*eta_c*eta_t bounds the power-producing band (1, r_zero)."""

    def test_zero_work_pressure_ratio_anchor(self):
        """Zero-work limiting ratio cross-check (step 4) at eta_c = eta_t
        = 0.87 must return 121.420 within 1e-3, where the compressor work
        overtakes the turbine output."""
        self.assertAlmostEqual(
            m.zero_work_pressure_ratio(T1, T3, EC, ET), 121.420,
            delta=1.0e-3)

    def test_zero_work_degenerates_to_tau_power(self):
        """Step 4 at unit efficiencies: zero_work_pressure_ratio equals
        tau**(1/KAPPA), the square of the ideal max-work pressure ratio
        r_opt_ideal**2."""
        r_zero = m.zero_work_pressure_ratio(T1, T3, 1.0, 1.0)
        ideal = m.ideal_optimum_pressure_ratio(T1, T3)
        self.assertTrue(math.isclose(
            r_zero, (T3 / T1) ** (1.0 / m.KAPPA), rel_tol=1.0e-12))
        self.assertTrue(math.isclose(r_zero, ideal * ideal, rel_tol=1.0e-12))

    def test_r_zero_is_r_opt_squared(self):
        """Step 4 identity: x_zero = tau*eta_c*eta_t = x_opt**2 exactly,
        so r_zero = r_opt**2 holds to float noise (lossy anchor relative
        difference 2.34e-16)."""
        r_opt = m.optimum_pressure_ratio(T1, T3, EC, ET)
        r_zero = m.zero_work_pressure_ratio(T1, T3, EC, ET)
        x_opt = r_opt ** m.KAPPA
        x_zero = r_zero ** m.KAPPA
        self.assertTrue(math.isclose(x_zero, x_opt * x_opt,
                                     rel_tol=1.0e-12))
        self.assertTrue(math.isclose(r_zero, r_opt * r_opt,
                                     rel_tol=1.0e-9))

    def test_power_band_span_is_one_optimum_decade(self):
        """Step 4 band geometry: the power-producing band (1, r_zero)
        spans r_zero/r_opt = 11.019059 = r_opt, one decade above the
        max-work pressure ratio."""
        r_opt = m.optimum_pressure_ratio(T1, T3, EC, ET)
        r_zero = m.zero_work_pressure_ratio(T1, T3, EC, ET)
        self.assertTrue(math.isclose(r_zero / r_opt, r_opt,
                                     rel_tol=1.0e-6))

    def test_zero_work_scaled_residual_below_1e9(self):
        """Step 4 residual: the net specific work at the zero-work
        limiting ratio vanishes with scaled residual below 1e-9 (lossy
        anchor 3.945e-16), the x = A root of the factored form."""
        r_zero = m.zero_work_pressure_ratio(T1, T3, EC, ET)
        w_zero = m.net_specific_work(T1, T3, r_zero, EC, ET)
        self.assertLess(abs(w_zero) / (m.CP * T1), 1.0e-9)

    def test_factored_form_reproduces_net_specific_work(self):
        """Step 4/5 identity: the factored zero-work form cp*T1*(x-1)*
        (A-x)/(x*eta_c) reproduces net_specific_work at every sampled
        ratio inside the power band, and vanishes exactly at its x = 1
        root (no compression)."""
        a_value = (T3 / T1) * EC * ET
        for r in (1.001, 2.0, m.optimum_pressure_ratio(T1, T3, EC, ET),
                  30.0, m.zero_work_pressure_ratio(T1, T3, EC, ET)):
            x = r ** m.KAPPA
            factored = (m.CP * T1 * (x - 1.0) * (a_value - x) /
                        (x * EC))
            w = m.net_specific_work(T1, T3, r, EC, ET)
            self.assertTrue(math.isclose(
                factored, w, rel_tol=1.0e-9, abs_tol=1.0e-6))
        self.assertEqual(
            m.CP * T1 * (1.0 - 1.0) * (a_value - 1.0) / (1.0 * EC), 0.0)


class TestNetSpecificWorkAtOptimum(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, net specific work evaluation at
    the optimum with the peak confirmed against log-symmetric
    neighbours of the pressure ratio."""

    def test_lossy_net_specific_work_anchor(self):
        """Net specific work at the optimum (step 5) for the lossy cycle
        must be 322937.1 J/kg (322.9 kJ/kg), evaluated at the module
        max-work pressure ratio."""
        r_opt = m.optimum_pressure_ratio(T1, T3, EC, ET)
        w_opt = m.net_specific_work(T1, T3, r_opt, EC, ET)
        self.assertAlmostEqual(w_opt, 322937.1, delta=1.0e-1)

    def test_ideal_net_specific_work_anchor(self):
        """Step 5 at unit efficiencies: the ideal net specific work at
        the ideal max-work pressure ratio must be 475639.9 J/kg (475.6
        kJ/kg)."""
        r_opt_i = m.ideal_optimum_pressure_ratio(T1, T3)
        w_opt = m.net_specific_work(T1, T3, r_opt_i, 1.0, 1.0)
        self.assertAlmostEqual(w_opt, 475639.9, delta=1.0e-1)

    def test_lossy_neighbours_equal_and_below_the_peak(self):
        """Step 5 peak property (lossy): the log-symmetric neighbours
        w(r_opt/sqrt(2)) and w(r_opt*sqrt(2)) are equal (316453.3 J/kg)
        and sit below the peak w(r_opt)."""
        r_opt = m.optimum_pressure_ratio(T1, T3, EC, ET)
        w_opt = m.net_specific_work(T1, T3, r_opt, EC, ET)
        w_lo = m.net_specific_work(T1, T3, r_opt / math.sqrt(2.0), EC, ET)
        w_hi = m.net_specific_work(T1, T3, r_opt * math.sqrt(2.0), EC, ET)
        self.assertTrue(math.isclose(w_lo, w_hi, rel_tol=1.0e-9))
        self.assertAlmostEqual(w_lo, 316453.3, delta=1.0e-1)
        self.assertGreater(w_opt, w_lo)
        self.assertGreater(w_opt, w_hi)

    def test_ideal_neighbours_equal_and_below_the_peak(self):
        """Step 5 peak property (ideal): w(r_opt_ideal/4) equals
        w(4*r_opt_ideal) (370621.4 J/kg) and both sit below the ideal
        peak w(r_opt_ideal)."""
        r_opt_i = m.ideal_optimum_pressure_ratio(T1, T3)
        w_opt = m.net_specific_work(T1, T3, r_opt_i, 1.0, 1.0)
        w_lo = m.net_specific_work(T1, T3, r_opt_i / 4.0, 1.0, 1.0)
        w_hi = m.net_specific_work(T1, T3, 4.0 * r_opt_i, 1.0, 1.0)
        self.assertTrue(math.isclose(w_lo, w_hi, rel_tol=1.0e-9))
        self.assertAlmostEqual(w_lo, 370621.4, delta=1.0e-1)
        self.assertGreater(w_opt, w_lo)
        self.assertGreater(w_opt, w_hi)

    def test_work_scales_linearly_with_cp(self):
        """Step 5 quotation: doubling the specific heat argument doubles
        the net specific work in J/kg, since CP enters only as a
        multiplier on the temperature-difference work."""
        r_opt = m.optimum_pressure_ratio(T1, T3, EC, ET)
        w_base = m.net_specific_work(T1, T3, r_opt, EC, ET)
        w_double = m.net_specific_work(T1, T3, r_opt, EC, ET,
                                       cp=2.0 * m.CP)
        self.assertTrue(math.isclose(w_double, 2.0 * w_base,
                                     rel_tol=1.0e-12))


class TestDerivativeSignChange(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, maximum verification by the
    derivative sign change of d(w)/dx across x_opt."""

    def test_derivative_positive_below_x_opt(self):
        """Derivative sign change (step 6): the closed-form derivative
        d(w)/dx = (cp*T1/eta_c)*(A/x**2 - 1) of the factored form is
        positive just below x_opt (lossy anchor +66.583 at x_opt*(1 -
        1e-4))."""
        x_opt = m.optimum_pressure_ratio(T1, T3, EC, ET) ** m.KAPPA
        dwdx = _dwdx_closed_form(x_opt * (1.0 - 1.0e-4))
        self.assertGreater(dwdx, 50.0)
        self.assertAlmostEqual(dwdx, 66.583, delta=1.0)

    def test_derivative_zero_at_x_opt(self):
        """Step 6 stationary point: d(w)/dx vanishes at x_opt to within
        1e-6 (lossy anchor 5.7e-11), the d(w)/dx = 0 maximum
        condition."""
        x_opt = m.optimum_pressure_ratio(T1, T3, EC, ET) ** m.KAPPA
        self.assertLess(abs(_dwdx_closed_form(x_opt)), 1.0e-6)

    def test_derivative_negative_above_x_opt(self):
        """Step 6 sign change completion: d(w)/dx is negative just above
        x_opt (lossy anchor -66.563 at x_opt*(1 + 1e-4)), so the
        stationary point is a maximum of the net specific work."""
        x_opt = m.optimum_pressure_ratio(T1, T3, EC, ET) ** m.KAPPA
        dwdx = _dwdx_closed_form(x_opt * (1.0 + 1.0e-4))
        self.assertLess(dwdx, -50.0)
        self.assertAlmostEqual(dwdx, -66.563, delta=1.0)


class TestEfficiencyVersusWorkVerdict(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, the efficiency-versus-work
    verdict: the max-efficiency pressure ratio diverges from the
    max-work ratio."""

    def test_ideal_efficiency_monotone_no_maximizer(self):
        """Step 7 ideal arm: eta = 1 - 1/x rises monotonically with the
        pressure ratio, eta(1.01) < eta(r_opt_ideal) < eta(2*r_opt_ideal)
        < eta(1e6), so the ideal cycle has no finite efficiency
        maximizer (0.002839, 0.561708, 0.640453, 0.980693)."""
        r_opt_i = m.ideal_optimum_pressure_ratio(T1, T3)
        e_low = m.ideal_cycle_efficiency(1.01)
        e_opt = m.ideal_cycle_efficiency(r_opt_i)
        e_high = m.ideal_cycle_efficiency(2.0 * r_opt_i)
        e_very_high = m.ideal_cycle_efficiency(1.0e6)
        self.assertLess(e_low, e_opt)
        self.assertLess(e_opt, e_high)
        self.assertLess(e_high, e_very_high)
        self.assertAlmostEqual(e_low, 0.002839, delta=1.0e-6)
        self.assertAlmostEqual(e_high, 0.640453, delta=1.0e-6)
        self.assertAlmostEqual(e_very_high, 0.980693, delta=1.0e-6)

    def test_ideal_efficiency_anchor_at_ideal_optimum(self):
        """Step 7 anchor: the ideal-cycle efficiency at the ideal
        max-work pressure ratio is 0.561708 within 1e-6."""
        r_opt_i = m.ideal_optimum_pressure_ratio(T1, T3)
        self.assertAlmostEqual(
            m.ideal_cycle_efficiency(r_opt_i), 0.561708, delta=1.0e-6)

    def test_verdict_real_efficiency_at_r_opt_anchor(self):
        """Efficiency-versus-work verdict (step 7): the lossy-cycle
        thermal efficiency at the max-work pressure ratio is 0.362832
        within 1e-6, below the peak available at a higher ratio."""
        verdict = m.design_verdict(T1, T3, EC, ET)
        self.assertAlmostEqual(
            verdict["eta_real_at_r_opt"], 0.362832, delta=1.0e-6)

    def test_verdict_efficiency_optimum_above_work_optimum(self):
        """Step 7 divergence: the closed-form quadratic root places the
        lossy efficiency maximum at r_eta_max_real = 26.994 within 0.02,
        strictly above the max-work pressure ratio 11.019."""
        verdict = m.design_verdict(T1, T3, EC, ET)
        r_opt = m.optimum_pressure_ratio(T1, T3, EC, ET)
        self.assertAlmostEqual(
            verdict["r_eta_max_real"], 26.994, delta=0.02)
        self.assertGreater(verdict["r_eta_max_real"], r_opt)
        self.assertGreater(verdict["x_eta_max_real"], r_opt ** m.KAPPA)

    def test_verdict_eta_at_eta_max_anchor(self):
        """Step 7 verdict peak: the lossy-cycle thermal efficiency at its
        own optimum ratio is 0.400699 within 1e-6, about 3.8 points
        above the efficiency at the max-work pressure ratio."""
        verdict = m.design_verdict(T1, T3, EC, ET)
        r_opt = m.optimum_pressure_ratio(T1, T3, EC, ET)
        self.assertAlmostEqual(
            verdict["eta_real_at_eta_max"], 0.400699, delta=1.0e-6)
        self.assertGreater(verdict["eta_real_at_eta_max"],
                           verdict["eta_real_at_r_opt"])
        self.assertAlmostEqual(
            m.cycle_efficiency(T1, T3, r_opt, EC, ET),
            verdict["eta_real_at_r_opt"], delta=1.0e-12)

    def test_verdict_eta_zero_at_zero_work_ratio(self):
        """Step 7 closure: the lossy-cycle efficiency returns to zero at
        the zero-work limiting ratio where the net work vanishes (within
        1e-9)."""
        verdict = m.design_verdict(T1, T3, EC, ET)
        r_zero = m.zero_work_pressure_ratio(T1, T3, EC, ET)
        self.assertLess(abs(verdict["eta_real_at_r_zero"]), 1.0e-9)
        self.assertLess(
            abs(m.cycle_efficiency(T1, T3, r_zero, EC, ET)), 1.0e-9)

    def test_verdict_ideal_arm_keys_monotone(self):
        """Step 7 verdict dict: the ideal arm keys eta_ideal_low,
        eta_ideal_at_r_opt_ideal and eta_ideal_high_r rise in order
        (monotone arm, no finite ideal efficiency maximizer), with the
        middle value 0.561708."""
        verdict = m.design_verdict(T1, T3, EC, ET)
        self.assertLess(verdict["eta_ideal_low"],
                        verdict["eta_ideal_at_r_opt_ideal"])
        self.assertLess(verdict["eta_ideal_at_r_opt_ideal"],
                        verdict["eta_ideal_high_r"])
        self.assertAlmostEqual(
            verdict["eta_ideal_at_r_opt_ideal"], 0.561708, delta=1.0e-6)

    def test_cycle_efficiency_matches_w_over_qin(self):
        """Step 7 definition: cycle_efficiency equals the net specific
        work divided by q_in = cp*(t3 - t2), t2 = t1*(1 + (x-1)/eta_c),
        recomputed here from the module constants at two ratios."""
        r_opt = m.optimum_pressure_ratio(T1, T3, EC, ET)
        for r in (r_opt, 30.0):
            x = r ** m.KAPPA
            t2 = T1 * (1.0 + (x - 1.0) / EC)
            q_in = m.CP * (T3 - t2)
            w = m.net_specific_work(T1, T3, r, EC, ET)
            self.assertTrue(math.isclose(
                m.cycle_efficiency(T1, T3, r, EC, ET), w / q_in,
                rel_tol=1.0e-9))


class TestValueErrorRejection(unittest.TestCase):
    """Workflow step 1 validation: the module rejects non-physical
    inputs, the temperature limits and component efficiency checks that
    open the SKILL.md workflow."""

    def test_valueerror_t1_nonpositive(self):
        """Step 1 temperature check: t1 at 0 and -1 raises ValueError on
        every entry point of the workflow."""
        for bad_t1 in (0.0, -1.0):
            with self.assertRaises(ValueError):
                m.ideal_optimum_pressure_ratio(bad_t1, T3)
            with self.assertRaises(ValueError):
                m.optimum_pressure_ratio(bad_t1, T3, EC, ET)
            with self.assertRaises(ValueError):
                m.zero_work_pressure_ratio(bad_t1, T3, EC, ET)
            with self.assertRaises(ValueError):
                m.design_verdict(bad_t1, T3, EC, ET)
        r_opt = m.optimum_pressure_ratio(T1, T3, EC, ET)
        for fn in (m.net_specific_work, m.cycle_efficiency):
            for bad_t1 in (0.0, -1.0):
                with self.assertRaises(ValueError):
                    fn(bad_t1, T3, r_opt, EC, ET)

    def test_valueerror_t3_not_above_t1(self):
        """Step 1 temperature check: t3 equal to or below t1 (t3 =
        288.15) raises ValueError across the workflow functions."""
        with self.assertRaises(ValueError):
            m.ideal_optimum_pressure_ratio(T1, 288.15)
        with self.assertRaises(ValueError):
            m.optimum_pressure_ratio(T1, 200.0, EC, ET)
        with self.assertRaises(ValueError):
            m.zero_work_pressure_ratio(T1, 288.15, EC, ET)
        with self.assertRaises(ValueError):
            m.design_verdict(T1, 100.0, EC, ET)
        r_opt = m.optimum_pressure_ratio(T1, T3, EC, ET)
        with self.assertRaises(ValueError):
            m.net_specific_work(T1, 288.15, r_opt, EC, ET)
        with self.assertRaises(ValueError):
            m.cycle_efficiency(T1, 100.0, r_opt, EC, ET)

    def test_valueerror_eta_out_of_range(self):
        """Step 1 efficiency check: eta_c and eta_t at 0, 1.5 and 1.01
        raise ValueError on every eta argument of the lossy-cycle
        functions."""
        r_opt = m.optimum_pressure_ratio(T1, T3, EC, ET)
        eta_funcs = (m.optimum_pressure_ratio, m.zero_work_pressure_ratio,
                     m.design_verdict)
        work_funcs = (m.net_specific_work, m.cycle_efficiency)
        for bad_eta in (0.0, 1.5, 1.01):
            for fn in eta_funcs:
                with self.assertRaises(ValueError):
                    fn(T1, T3, bad_eta, ET)
                with self.assertRaises(ValueError):
                    fn(T1, T3, EC, bad_eta)
            for fn in work_funcs:
                with self.assertRaises(ValueError):
                    fn(T1, T3, r_opt, bad_eta, ET)
                with self.assertRaises(ValueError):
                    fn(T1, T3, r_opt, EC, bad_eta)

    def test_valueerror_ratio_at_or_below_one(self):
        """Step 1 ratio check: pressure ratios of 1.0 and 0.5 raise
        ValueError on the work and efficiency evaluators (ratios of 1 or
        below are non-physical, sibling convention)."""
        for bad_r in (1.0, 0.5):
            with self.assertRaises(ValueError):
                m.net_specific_work(T1, T3, bad_r, EC, ET)
            with self.assertRaises(ValueError):
                m.ideal_cycle_efficiency(bad_r)
            with self.assertRaises(ValueError):
                m.cycle_efficiency(T1, T3, bad_r, EC, ET)


class TestDeterminismAndConstants(unittest.TestCase):
    """Workflow step 8 close-out: the module is deterministic, stdlib
    only, with the air-standard constants fixed."""

    def test_air_standard_constants_and_determinism(self):
        """Step 8 constants and determinism: GAMMA is fixed at 1.4 (air),
        KAPPA equals (GAMMA - 1)/GAMMA = 2/7, CP is 1005.0 J/(kg K), and
        repeated calls on identical inputs return identical results,
        including the verdict dict."""
        self.assertEqual(m.GAMMA, 1.4)
        self.assertAlmostEqual(m.KAPPA, 2.0 / 7.0, delta=1.0e-15)
        self.assertEqual(m.KAPPA, (m.GAMMA - 1.0) / m.GAMMA)
        self.assertEqual(m.CP, 1005.0)
        self.assertEqual(m.ideal_optimum_pressure_ratio(T1, T3),
                         m.ideal_optimum_pressure_ratio(T1, T3))
        self.assertEqual(m.design_verdict(T1, T3, EC, ET),
                         m.design_verdict(T1, T3, EC, ET))

    def test_stdlib_only_no_external_imports(self):
        """Step 8 dependency check: the logic module imports nothing
        beyond the stdlib math module (no numpy, scipy or pandas)."""
        import inspect
        source = inspect.getsource(m)
        self.assertIn("import math", source)
        for banned in ("import numpy", "from numpy", "import scipy",
                       "from scipy", "import pandas", "from pandas",
                       "import random"):
            self.assertNotIn(banned, source)


if __name__ == "__main__":
    unittest.main()
