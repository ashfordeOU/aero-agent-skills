#!/usr/bin/env python3
"""Gate 3 contract test: level acceleration flight test logic.

Exercises scripts/level_acceleration_test_logic.py (stdlib unittest,
offline). Contract: ISA conditions at altitude, true airspeed from
equivalent airspeed, moving average smoothing, acceleration from the
smoothed trace by central differences, specific excess power by the
total energy method, excess thrust from P_s, the drag polar chain (CL,
CD, drag, thrust available estimate), the weight and density
corrections to reference conditions, and the one-pass
level_acceleration_summary reduction; invalid inputs raise ValueError.

Worked scenario: accelerated level flight at 8000 m, linear true
airspeed 150 to 170 m/s over 20 s sampled at 1 s (21 samples),
W 250000 N, S 122.6 m^2, cd0 0.02, k 0.042, ISA density at 8000 m
0.525167 kg/m^3, smoothing window 5. Pinned values from the
deterministic model: acceleration 1.0 m/s^2, P_s 16.3155 m/s at
160 m/s, excess thrust 25492.9 N (W/g per 1 m/s^2), drag at 160 m/s
19667.8 N, thrust available 45160.8 N; the assessment region spans
samples 3 to 17 inclusive (mean over the region where the window and
the central difference stencil are both full). ISA anchors: at 8000 m
T 236.15 K, P 35599.8 Pa, rho 0.52517 kg/m^3; 110 m/s equivalent
airspeed gives 168.0 m/s true airspeed.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_acceleration_test_logic as la  # noqa: E402

W = 250000.0
S = 122.6
CD0 = 0.02
K = 0.042
N = 21
T_S = [float(i) for i in range(N)]
V_RAMP = [150.0 + i for i in range(N)]


def rho_8000():
    return la.isa_conditions(8000.0)[2]


class IsaConditionsTest(unittest.TestCase):
    def test_sea_level_anchor(self):
        t, p, rho = la.isa_conditions(0)
        self.assertAlmostEqual(t, 288.15, places=6)
        self.assertAlmostEqual(p, 101325.0, places=2)
        self.assertAlmostEqual(rho, 1.225, places=5)

    def test_8000_m_anchor(self):
        t, p, rho = la.isa_conditions(8000.0)
        self.assertAlmostEqual(t, 236.15, places=6)
        self.assertAlmostEqual(p, 35599.79, places=2)
        self.assertAlmostEqual(rho, 0.525167, places=5)
        self.assertAlmostEqual(rho / la.RHO0, 0.42871, places=4)

    def test_tropopause_isothermal_and_falling_density(self):
        t, _, rho = la.isa_conditions(11000.0)
        self.assertAlmostEqual(t, 216.65, places=6)
        # isothermal above the tropopause: 15000 m keeps the same T
        self.assertAlmostEqual(la.isa_conditions(15000.0)[0], 216.65, places=6)
        # density ratio at the tropopause about 0.2971, still falling above
        self.assertAlmostEqual(rho / la.RHO0, 0.29708, places=4)
        self.assertLess(la.isa_conditions(15000.0)[2], rho)

    def test_invalid_altitude_raises(self):
        with self.assertRaises(ValueError):
            la.isa_conditions(-100.0)
        with self.assertRaises(ValueError):
            la.isa_conditions(21000.0)


class TrueAirspeedTest(unittest.TestCase):
    def test_sea_level_identity_and_altitude_trend(self):
        self.assertAlmostEqual(la.true_airspeed_from_eas(160.0, la.RHO0),
                               160.0, places=6)
        tas_high = la.true_airspeed_from_eas(110.0, la.isa_conditions(11000.0)[2])
        self.assertGreater(tas_high, la.true_airspeed_from_eas(110.0, rho_8000()))

    def test_8000_m_conversion_anchor(self):
        # 110 m/s EAS at rho 0.525167: 110 * sqrt(1.225 / 0.525167) = 168.0
        self.assertAlmostEqual(la.true_airspeed_from_eas(110.0, rho_8000()),
                               168.001, delta=0.005)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            la.true_airspeed_from_eas(0.0, rho_8000())
        with self.assertRaises(ValueError):
            la.true_airspeed_from_eas(110.0, 0.0)
        with self.assertRaises(ValueError):
            la.true_airspeed_from_eas(110.0, rho_8000(), rho0=0.0)


class SmoothTraceTest(unittest.TestCase):
    def test_linear_ramp_preserved_interior(self):
        # window 5: samples 2..18 carry full windows and stay on the ramp
        out = la.smooth_trace(V_RAMP, 5)
        self.assertEqual(len(out), N)
        for i in range(2, 19):
            self.assertAlmostEqual(out[i], V_RAMP[i], places=9)

    def test_constant_trace_unchanged_and_window_one(self):
        out = la.smooth_trace([160.0] * N, 5)
        for i in range(N):
            self.assertAlmostEqual(out[i], 160.0, places=9)
        self.assertEqual(la.smooth_trace(V_RAMP, 1), V_RAMP)

    def test_invalid_windows_raise(self):
        with self.assertRaises(ValueError):
            la.smooth_trace(V_RAMP, 4)      # even window
        with self.assertRaises(ValueError):
            la.smooth_trace(V_RAMP, 0)
        with self.assertRaises(ValueError):
            la.smooth_trace(V_RAMP, -3)
        with self.assertRaises(ValueError):
            la.smooth_trace(V_RAMP, 5.5)    # non integer
        with self.assertRaises(ValueError):
            la.smooth_trace([], 5)


class AccelerationFromTraceTest(unittest.TestCase):
    def test_linear_ramp_gives_slope(self):
        a = la.acceleration_from_trace(V_RAMP, T_S)
        for i in range(N):
            self.assertAlmostEqual(a[i], 1.0, places=9)

    def test_constant_trace_gives_zero(self):
        a = la.acceleration_from_trace([160.0] * N, T_S)
        for i in range(N):
            self.assertAlmostEqual(a[i], 0.0, places=9)

    def test_quadratic_interior_central_difference(self):
        # v = t^2 sampled at t = 1..21 s: central difference a = 2*t
        v = [float((i + 1) * (i + 1)) for i in range(N)]
        t = [float(i + 1) for i in range(N)]
        a = la.acceleration_from_trace(v, t)
        for i in range(1, N - 1):
            self.assertAlmostEqual(a[i], 2.0 * (i + 1), places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            la.acceleration_from_trace(V_RAMP, T_S[:-1])      # length mismatch
        with self.assertRaises(ValueError):
            la.acceleration_from_trace([150.0], [0.0])        # too short
        with self.assertRaises(ValueError):
            la.acceleration_from_trace(V_RAMP, list(reversed(T_S)))
        with self.assertRaises(ValueError):
            la.acceleration_from_trace([0.0, 10.0, 20.0], [0.0, 1.0, 2.0])


class SpecificExcessPowerTest(unittest.TestCase):
    def test_level_anchor_and_deceleration_sign(self):
        # P_s = V * a / g at 160 m/s and 1 m/s^2
        self.assertAlmostEqual(la.specific_excess_power(160.0, 1.0),
                               16.31546, places=4)
        self.assertLess(la.specific_excess_power(160.0, -0.5), 0.0)

    def test_non_level_run_adds_climb_rate(self):
        # 1.5 m/s climb rate on top of the level value
        self.assertAlmostEqual(la.specific_excess_power(160.0, 1.0, dh_dt=1.5),
                               17.81546, places=4)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            la.specific_excess_power(0.0, 1.0)
        with self.assertRaises(ValueError):
            la.specific_excess_power(160.0, 1.0, g=0.0)


class ExcessThrustTest(unittest.TestCase):
    def test_worked_anchor_and_zero_boundary(self):
        # W * P_s / V = 250000 * 16.31546 / 160 = 25492.9 N
        ps = la.specific_excess_power(160.0, 1.0)
        self.assertAlmostEqual(la.excess_thrust_from_ps(ps, 160.0, W),
                               25492.905, places=2)
        self.assertAlmostEqual(la.excess_thrust_from_ps(0.0, 160.0, W),
                               0.0, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            la.excess_thrust_from_ps(1.0, 0.0, W)
        with self.assertRaises(ValueError):
            la.excess_thrust_from_ps(1.0, 160.0, 0.0)


class PolarChainTest(unittest.TestCase):
    def test_cl_and_cd_at_160(self):
        cl = la.lift_coefficient(W, 160.0, rho_8000(), S)
        self.assertAlmostEqual(cl, 0.30335, places=4)
        self.assertAlmostEqual(la.drag_coefficient(CD0, K, cl), 0.023865, places=5)

    def test_drag_anchors_150_160_170(self):
        rho = rho_8000()
        self.assertAlmostEqual(la.drag_from_polar(150.0, rho, S, W, CD0, K),
                               18110.74, places=1)
        self.assertAlmostEqual(la.drag_from_polar(160.0, rho, S, W, CD0, K),
                               19667.85, places=1)
        self.assertAlmostEqual(la.drag_from_polar(170.0, rho, S, W, CD0, K),
                               21428.86, places=1)

    def test_thrust_available_anchor(self):
        # T = delta_T + D at 160 m/s: 25492.905 + 19667.85 = 45160.75 N
        self.assertAlmostEqual(
            la.thrust_available_estimate(25492.905, 19667.846),
            45160.751, places=2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            la.lift_coefficient(0.0, 160.0, rho_8000(), S)
        with self.assertRaises(ValueError):
            la.drag_coefficient(-0.01, K, 0.3)
        with self.assertRaises(ValueError):
            la.drag_coefficient(CD0, -0.01, 0.3)
        with self.assertRaises(ValueError):
            la.drag_from_polar(160.0, 0.0, S, W, CD0, K)
        with self.assertRaises(ValueError):
            la.drag_from_polar(160.0, rho_8000(), S, 0.0, CD0, K)
        with self.assertRaises(ValueError):
            la.thrust_available_estimate(-30000.0, 0.0)


class CorrectionsTest(unittest.TestCase):
    def test_weight_correction_anchor(self):
        # 16.31546 * 250000 / 240000 = 16.99527 m/s
        self.assertAlmostEqual(la.weight_corrected_ps(16.31546, 250000.0, 240000.0),
                               16.99527, places=4)

    def test_density_correction_anchor(self):
        # 16.31546 * 0.9^0.2 = 15.97526 m/s
        self.assertAlmostEqual(la.density_corrected_ps(16.31546, 0.9 * la.RHO0),
                               15.97526, places=4)

    def test_combined_correction_and_identities(self):
        # weight factor 250/240 then the 0.9 density ratio: 16.64089 m/s
        self.assertAlmostEqual(
            la.ps_at_reference_conditions(16.31546, 250000.0, 240000.0,
                                          0.9 * la.RHO0),
            16.64089, places=4)
        self.assertAlmostEqual(la.weight_corrected_ps(16.31546, W, W),
                               16.31546, places=9)
        self.assertAlmostEqual(la.density_corrected_ps(16.31546, la.RHO0),
                               16.31546, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            la.weight_corrected_ps(16.31546, 0.0, 240000.0)
        with self.assertRaises(ValueError):
            la.weight_corrected_ps(16.31546, 250000.0, 0.0)
        with self.assertRaises(ValueError):
            la.density_corrected_ps(16.31546, 0.0)
        with self.assertRaises(ValueError):
            la.density_corrected_ps(16.31546, 0.9 * la.RHO0, lapse_exp=0.0)
        with self.assertRaises(ValueError):
            la.density_corrected_ps(16.31546, 0.9 * la.RHO0, lapse_exp=1.5)


class LevelAccelerationSummaryTest(unittest.TestCase):
    def test_worked_mean_anchors(self):
        res = la.level_acceleration_summary(T_S, V_RAMP, W, altitude_m=8000.0,
                                            s_m2=S, cd0=CD0, k=K)
        self.assertEqual((res["assessment_start"], res["assessment_end"]), (3, 18))
        self.assertAlmostEqual(res["mean_acceleration"], 1.0, places=9)
        self.assertAlmostEqual(res["mean_specific_excess_power"], 16.31546,
                               places=4)
        self.assertAlmostEqual(res["mean_excess_thrust"], 25492.905, places=2)
        self.assertTrue(res["sustained_over_band"])
        self.assertTrue(all(res["accelerating"]))

    def test_worked_point_and_polar_anchors(self):
        res = la.level_acceleration_summary(T_S, V_RAMP, W, altitude_m=8000.0,
                                            s_m2=S, cd0=CD0, k=K)
        self.assertAlmostEqual(res["v_smoothed"][10], 160.0, places=9)
        self.assertAlmostEqual(res["acceleration"][10], 1.0, places=9)
        self.assertAlmostEqual(res["specific_excess_power"][10], 16.31546,
                               places=4)
        self.assertAlmostEqual(res["excess_thrust"][10], 25492.905, places=2)
        self.assertAlmostEqual(res["drag"][10], 19667.85, places=1)
        self.assertAlmostEqual(res["thrust_available"][10], 45160.75, places=1)
        self.assertAlmostEqual(res["mean_drag"], 19686.85, places=2)
        self.assertAlmostEqual(res["mean_thrust_available"], 45179.75, places=2)

    def test_summary_matches_scalar_chain(self):
        # one-pass reduction equals per-point scalar calls over the region
        res = la.level_acceleration_summary(T_S, V_RAMP, W, altitude_m=8000.0,
                                            s_m2=S, cd0=CD0, k=K)
        start, end = res["assessment_start"], res["assessment_end"]
        drags = [la.drag_from_polar(res["v_smoothed"][i], res["density_kgm3"],
                                    S, W, CD0, K) for i in range(start, end)]
        self.assertAlmostEqual(res["mean_drag"], sum(drags) / (end - start),
                               places=9)
        # thrust available identity: mean T_avail = mean drag + mean excess thrust
        self.assertAlmostEqual(res["mean_thrust_available"],
                               res["mean_drag"] + res["mean_excess_thrust"],
                               places=6)

    def test_constant_speed_subcase_is_zero(self):
        # V constant: a = 0, P_s = 0, excess thrust = 0, not sustained
        res = la.level_acceleration_summary(T_S, [160.0] * N, W, altitude_m=8000.0,
                                            s_m2=S, cd0=CD0, k=K)
        self.assertAlmostEqual(res["mean_acceleration"], 0.0, places=9)
        self.assertAlmostEqual(res["mean_specific_excess_power"], 0.0, places=9)
        self.assertAlmostEqual(res["mean_excess_thrust"], 0.0, places=9)
        self.assertFalse(res["sustained_over_band"])
        self.assertFalse(any(res["accelerating"]))
        # at constant speed the drag is the constant 160 m/s drag
        self.assertAlmostEqual(res["drag"][10], 19667.85, places=1)
        self.assertAlmostEqual(res["thrust_available"][10], res["drag"][10],
                               places=6)

    def test_slightly_non_level_run(self):
        res = la.level_acceleration_summary(T_S, V_RAMP, W, altitude_m=8000.0,
                                            dh_dt=1.5)
        self.assertAlmostEqual(res["mean_specific_excess_power"], 17.81546,
                               places=4)
        self.assertAlmostEqual(res["specific_excess_power"][10], 17.81546,
                               places=4)

    def test_reference_condition_corrections(self):
        rho = rho_8000()
        res = la.level_acceleration_summary(T_S, V_RAMP, W, rho=rho,
                                            w_ref_n=240000.0, rho_std=rho)
        self.assertAlmostEqual(res["mean_ps_reference_weight"], 16.99527,
                               places=4)
        # standard-day-at-altitude identity: rho_std equals the test density
        self.assertAlmostEqual(res["mean_ps_reference_conditions"],
                               res["mean_ps_reference_weight"], places=9)
        # scalar cross check on the region mean
        self.assertAlmostEqual(
            la.weight_corrected_ps(res["mean_specific_excess_power"], W, 240000.0),
            res["mean_ps_reference_weight"], places=9)

    def test_altitude_and_density_equivalence(self):
        res_alt = la.level_acceleration_summary(T_S, V_RAMP, W, altitude_m=8000.0)
        res_rho = la.level_acceleration_summary(T_S, V_RAMP, W, rho=rho_8000())
        self.assertAlmostEqual(res_alt["density_kgm3"], res_rho["density_kgm3"],
                               places=12)
        self.assertAlmostEqual(res_alt["mean_excess_thrust"],
                               res_rho["mean_excess_thrust"], places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            la.level_acceleration_summary(T_S, V_RAMP, W, rho=rho_8000(), window=4)
        with self.assertRaises(ValueError):
            la.level_acceleration_summary(T_S, V_RAMP[:-2], W, rho=rho_8000())
        with self.assertRaises(ValueError):
            la.level_acceleration_summary(T_S, [0.0] * N, W, rho=rho_8000())
        with self.assertRaises(ValueError):
            la.level_acceleration_summary(T_S, V_RAMP, 0.0, rho=rho_8000())
        with self.assertRaises(ValueError):
            la.level_acceleration_summary(T_S, V_RAMP, W)          # no rho/altitude
        with self.assertRaises(ValueError):
            la.level_acceleration_summary(T_S, V_RAMP, W, altitude_m=21000.0)
        with self.assertRaises(ValueError):
            la.level_acceleration_summary(T_S, V_RAMP, W, rho=rho_8000(),
                                          dh_dt=[1.5] * 5)        # length mismatch
        with self.assertRaises(ValueError):
            la.level_acceleration_summary(T_S, V_RAMP, W, rho=rho_8000(),
                                          s_m2=S)                 # partial polar
        with self.assertRaises(ValueError):
            la.level_acceleration_summary(T_S, V_RAMP, W, rho=rho_8000(),
                                          w_ref_n=0.0)
        with self.assertRaises(ValueError):
            la.level_acceleration_summary(T_S[:5], V_RAMP[:5], W, rho=rho_8000(),
                                          window=5)               # trace too short


if __name__ == "__main__":
    unittest.main(verbosity=2)
