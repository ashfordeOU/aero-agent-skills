"""Contract test for rotorcraft-forward-flight-performance-test logic.

Deterministic stdlib unittest, offline, no RNG. Run from the repo root
(or the leaf directory):

    python3 skills/flight-test-operations/performance/\
rotorcraft-forward-flight-performance-test/scripts/\
test_rotorcraft_forward_flight_performance_test.py

Covers the wave-32 spec worked example with the module's REAL outputs
as assert targets: shaft powers about [330000, 271400, 251800, 259400,
304200, 376000, 487000] W (each within +-2000 W), identity corrections
at standard day and reference weight, fit coefficients a in 100-130
(about 114.04), b in -7000 to -5000 (about -6030.36), c in
320000-340000 (about 329300.0), best-endurance speed 26.44 m/s in
23-30, best-range speed 53.74 m/s in 48-58 with the tangent condition
a*V^2 = c, maximum level-flight speed 70.40 m/s in 66-74 at 470 kW
available, the ValueError rejections of every non-physical input, the
closed-form identities (standard-day density identity, reference-weight
identity, density scaling, induced-fraction endpoints, polar-minimum
single root), scale invariance of the characteristic speeds, the
vh_beyond_measured flag, determinism, and the exact dict keys.
"""

import math
import os
import sys
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.abspath(__file__)))
import rotorcraft_forward_flight_performance_test_logic as rff

OMEGA = 27.0
RHO_STD = 1.225
W_REF = 21000.0
F_I = 0.6
P_AVAIL = 470000.0
P_KW = [330.0, 271.4, 251.8, 259.4, 304.2, 376.0, 487.0]
SPEEDS = [0.0, 12.0, 24.0, 36.0, 48.0, 60.0, 72.0]
POWERS = [p * 1000.0 for p in P_KW]
TORQUES = [p / OMEGA for p in POWERS]
# Real module outputs from the worked example (smoke run).
A_FIT, B_FIT, C_FIT = 114.037698, -6030.357143, 329300.0
V_BEN = 26.440191
V_BR = 53.736781
VH = 70.40479355165094


def polar_power(a, b, c, v):
    """Evaluate the fitted polar at speed v."""
    return a * v * v + b * v + c


class TestShaftPower(unittest.TestCase):
    def test_hover_torque_worked_value(self):
        # 12 222 Nm at 27 rad/s gives about 330 000 W.
        self.assertAlmostEqual(rff.shaft_power(12222.0, OMEGA),
                               330000.0, delta=2000.0)

    def test_sweep_torques_recover_listed_powers(self):
        for torque, expected in zip(TORQUES, POWERS):
            self.assertAlmostEqual(rff.shaft_power(torque, OMEGA),
                                   expected, delta=2000.0)
        self.assertEqual(rff.shaft_power(0.0, OMEGA), 0.0)
        self.assertAlmostEqual(rff.shaft_power(2 * 12222.0, OMEGA),
                               2.0 * rff.shaft_power(12222.0, OMEGA),
                               places=6)

    def test_nonphysical_torque_and_omega_rejected(self):
        with self.assertRaises(ValueError):
            rff.shaft_power(-1.0, OMEGA)
        with self.assertRaises(ValueError):
            rff.shaft_power(1000.0, 0.0)
        with self.assertRaises(ValueError):
            rff.shaft_power(1000.0, -27.0)


class TestPowerCorrections(unittest.TestCase):
    def test_density_correction_identity_and_scaling(self):
        self.assertAlmostEqual(
            rff.density_correct_power(330000.0, RHO_STD),
            330000.0, places=6)
        got = rff.density_correct_power(330000.0, 1.10)
        self.assertAlmostEqual(got, 330000.0 * RHO_STD / 1.10,
                               delta=50.0)

    def test_weight_correction_identity_and_endpoints(self):
        self.assertAlmostEqual(
            rff.weight_correct_power(330000.0, W_REF, W_REF, F_I),
            330000.0, places=6)
        lin = rff.weight_correct_power(330000.0, 22000.0, 21000.0, 0.0)
        self.assertAlmostEqual(lin, 330000.0 * 21000.0 / 22000.0,
                               places=6)
        induced = rff.weight_correct_power(330000.0, 22000.0,
                                           21000.0, 1.0)
        self.assertAlmostEqual(
            induced, 330000.0 * (21000.0 / 22000.0) ** 1.5, delta=1.0)

    def test_correction_valueerrors(self):
        for bad_call in (
                lambda: rff.density_correct_power(-1.0, RHO_STD),
                lambda: rff.density_correct_power(330000.0, 0.0),
                lambda: rff.density_correct_power(330000.0, -1.0),
                lambda: rff.weight_correct_power(-1.0, W_REF, W_REF, F_I),
                lambda: rff.weight_correct_power(330000.0, 0.0, W_REF, F_I),
                lambda: rff.weight_correct_power(330000.0, W_REF, -1.0, F_I),
                lambda: rff.weight_correct_power(330000.0, W_REF, W_REF,
                                                 -0.1),
                lambda: rff.weight_correct_power(330000.0, W_REF, W_REF,
                                                 1.1)):
            with self.assertRaises(ValueError):
                bad_call()

    def test_reference_chain_matches_density_then_weight(self):
        got = rff.correct_to_reference(330000.0, 22000.0, W_REF, F_I,
                                       1.10)
        manual = rff.weight_correct_power(
            rff.density_correct_power(330000.0, 1.10),
            22000.0, W_REF, F_I)
        self.assertAlmostEqual(got, manual, places=6)
        identity = rff.correct_to_reference(330000.0, W_REF, W_REF, F_I,
                                            RHO_STD)
        self.assertAlmostEqual(identity, 330000.0, places=6)


class TestPolarFit(unittest.TestCase):
    def test_worked_example_coefficients_and_bounds(self):
        a, b, c = rff.fit_power_polar(SPEEDS, POWERS)
        self.assertAlmostEqual(a, A_FIT, delta=0.01)
        self.assertAlmostEqual(b, B_FIT, delta=0.01)
        self.assertAlmostEqual(c, C_FIT, delta=1.0)
        self.assertTrue(100.0 <= a <= 130.0, a)
        self.assertTrue(-7000.0 <= b <= -5000.0, b)
        self.assertTrue(320000.0 <= c <= 340000.0, c)

    def test_exact_quadratic_reproduction_and_flat_polar(self):
        xs = [10.0, 20.0, 30.0, 40.0]
        ys = [2.0 * x * x + 3.0 * x + 5.0 for x in xs]
        a, b, c = rff.fit_power_polar(xs, ys)
        self.assertAlmostEqual(a, 2.0, places=6)
        self.assertAlmostEqual(b, 3.0, places=6)
        self.assertAlmostEqual(c, 5.0, places=6)
        a2, b2, c2 = rff.fit_power_polar([10.0, 20.0, 30.0, 40.0, 50.0],
                                         [250000.0] * 5)
        self.assertAlmostEqual(c2, 250000.0, delta=1e-6)
        self.assertAlmostEqual(a2, 0.0, delta=1e-6)

    def test_fit_valueerrors(self):
        with self.assertRaises(ValueError):
            rff.fit_power_polar([10.0, 20.0, 30.0], [1.0, 1.0, 1.0])
        with self.assertRaises(ValueError):
            rff.fit_power_polar([10.0, 20.0, 30.0, 40.0], [1.0, 1.0])
        with self.assertRaises(ValueError):
            rff.fit_power_polar([-5.0, 20.0, 30.0, 40.0],
                                [1.0, 1.0, 1.0, 1.0])
        with self.assertRaises(ValueError):
            rff.fit_power_polar([10.0, 20.0, 30.0, 40.0],
                                [1.0, -1.0, 1.0, 1.0])

    def test_downward_concave_data_degenerate_rejected(self):
        # Strongly concave data fit a downward parabola (a about -0.5):
        # a < 0 on non-constant powers is non-physical for a polar.
        xs = [10.0, 20.0, 30.0, 40.0]
        ys = [-0.5 * x * x + 30.0 * x + 500.0 for x in xs]
        with self.assertRaises(ValueError):
            rff.fit_power_polar(xs, ys)


class TestCharacteristicSpeeds(unittest.TestCase):
    def test_best_endurance_worked_vertex(self):
        v = rff.best_endurance_speed(A_FIT, B_FIT)
        self.assertAlmostEqual(v, V_BEN, delta=0.01)
        self.assertTrue(23.0 <= v <= 30.0, v)
        self.assertAlmostEqual(v, -B_FIT / (2.0 * A_FIT), places=9)
        p_min = polar_power(A_FIT, B_FIT, C_FIT, v)
        self.assertAlmostEqual(p_min / 1000.0, 250.0, delta=5.0)

    def test_best_endurance_flat_polar_none_and_negative_a(self):
        self.assertIsNone(rff.best_endurance_speed(0.0, 0.0))
        self.assertIsNone(rff.best_endurance_speed(0.0, -5.0))
        with self.assertRaises(ValueError):
            rff.best_endurance_speed(-1.0, 100.0)

    def test_best_range_worked_tangent_condition(self):
        v = rff.best_range_speed(A_FIT, C_FIT)
        self.assertAlmostEqual(v, V_BR, delta=0.01)
        self.assertTrue(48.0 <= v <= 58.0, v)
        self.assertGreater(v, rff.best_endurance_speed(A_FIT, B_FIT))
        self.assertAlmostEqual(A_FIT * v * v, C_FIT, delta=1e-6)
        dv = 2.0 * A_FIT * v + B_FIT
        ratio = polar_power(A_FIT, B_FIT, C_FIT, v) / v
        self.assertAlmostEqual(dv, ratio, delta=1e-6)

    def test_best_range_none_and_valueerrors(self):
        self.assertIsNone(rff.best_range_speed(100.0, 0.0))
        with self.assertRaises(ValueError):
            rff.best_range_speed(0.0, 100.0)
        with self.assertRaises(ValueError):
            rff.best_range_speed(100.0, -1.0)

    def test_max_level_speed_worked_value(self):
        v = rff.max_level_speed(A_FIT, B_FIT, C_FIT, P_AVAIL)
        self.assertAlmostEqual(v, VH, delta=0.01)
        self.assertTrue(66.0 <= v <= 74.0, v)
        self.assertLessEqual(v, max(SPEEDS))
        vbr = rff.best_range_speed(A_FIT, C_FIT)
        self.assertAlmostEqual(v / vbr, 1.31, delta=0.01)

    def test_max_level_speed_at_minimum_and_below(self):
        v_ben = rff.best_endurance_speed(A_FIT, B_FIT)
        p_min = polar_power(A_FIT, B_FIT, C_FIT, v_ben)
        vh = rff.max_level_speed(A_FIT, B_FIT, C_FIT, p_min)
        self.assertAlmostEqual(vh, v_ben, places=6)
        self.assertIsNone(rff.max_level_speed(A_FIT, B_FIT, C_FIT,
                                              p_min - 1000.0))

    def test_max_level_speed_negative_a_rejected(self):
        with self.assertRaises(ValueError):
            rff.max_level_speed(-1.0, 100.0, 100.0, P_AVAIL)


class TestSpeedOrder(unittest.TestCase):
    def test_worked_example_order_ok(self):
        order = rff.validate_speed_order(V_BEN, V_BR, VH)
        self.assertTrue(order["ben_lt_br"])
        self.assertTrue(order["br_lt_vh_or_none"])
        self.assertTrue(order["order_ok"])

    def test_order_violations_and_none_handling(self):
        bad1 = rff.validate_speed_order(60.0, 40.0, 70.0)
        self.assertFalse(bad1["ben_lt_br"])
        self.assertFalse(bad1["order_ok"])
        bad2 = rff.validate_speed_order(20.0, 80.0, 70.0)
        self.assertFalse(bad2["br_lt_vh_or_none"])
        self.assertFalse(bad2["order_ok"])
        self.assertTrue(rff.validate_speed_order(None, None, None)
                        ["order_ok"])
        self.assertTrue(rff.validate_speed_order(None, 50.0, None)
                        ["order_ok"])
        self.assertTrue(rff.validate_speed_order(20.0, None, 70.0)
                        ["order_ok"])


class TestSweepReduction(unittest.TestCase):
    def _reduce(self, torques=None, speeds=None, p_avail=P_AVAIL):
        torques = torques if torques is not None else TORQUES
        speeds = speeds if speeds is not None else SPEEDS
        return rff.reduce_level_flight_sweep(
            torques, [OMEGA] * len(speeds), speeds, RHO_STD, W_REF,
            W_REF, F_I, p_avail_max_continuous_w=p_avail)

    def test_worked_example_end_to_end(self):
        res = self._reduce()
        for got, expected in zip(res["shaft_powers_W"], POWERS):
            self.assertAlmostEqual(got, expected, delta=2000.0)
        for got, raw in zip(res["corrected_powers_W"],
                            res["shaft_powers_W"]):
            self.assertAlmostEqual(got, raw, places=6)
        a, b, c = res["fit"]
        self.assertAlmostEqual(a, A_FIT, delta=0.01)
        self.assertAlmostEqual(b, B_FIT, delta=0.01)
        self.assertAlmostEqual(c, C_FIT, delta=1.0)
        self.assertAlmostEqual(res["best_endurance_speed_ms"], V_BEN,
                               delta=0.01)
        self.assertAlmostEqual(res["best_range_speed_ms"], V_BR,
                               delta=0.01)
        self.assertAlmostEqual(res["max_level_speed_ms"], VH, delta=0.01)
        self.assertEqual(res["point_count"], 7)
        self.assertTrue(res["speed_order"]["order_ok"])
        self.assertFalse(res["vh_beyond_measured"])

    def test_dict_contains_exactly_documented_keys(self):
        self.assertEqual(
            set(self._reduce().keys()),
            {"shaft_powers_W", "corrected_powers_W", "fit",
             "best_endurance_speed_ms", "best_range_speed_ms",
             "max_level_speed_ms", "speed_order", "point_count",
             "vh_beyond_measured"})

    def test_vh_beyond_measured_flag(self):
        high = self._reduce(p_avail=560000.0)
        self.assertIsNotNone(high["max_level_speed_ms"])
        self.assertGreater(high["max_level_speed_ms"], max(SPEEDS))
        self.assertTrue(high["vh_beyond_measured"])

    def test_no_available_power_returns_none_vh(self):
        res = self._reduce(p_avail=None)
        self.assertIsNone(res["max_level_speed_ms"])
        self.assertFalse(res["vh_beyond_measured"])
        self.assertTrue(res["speed_order"]["order_ok"])

    def test_scale_invariance_of_characteristic_speeds(self):
        base = self._reduce()
        scaled = self._reduce(torques=[2.0 * t for t in TORQUES],
                              p_avail=2.0 * P_AVAIL)
        self.assertAlmostEqual(scaled["best_endurance_speed_ms"],
                               base["best_endurance_speed_ms"], places=9)
        self.assertAlmostEqual(scaled["best_range_speed_ms"],
                               base["best_range_speed_ms"], places=9)

    def test_sweep_array_valueerrors(self):
        with self.assertRaises(ValueError):
            self._reduce(torques=TORQUES[:-1])
        with self.assertRaises(ValueError):
            self._reduce(torques=TORQUES[:3], speeds=SPEEDS[:3])
        n = rff.MAX_SPEED_SWEEP + 1
        with self.assertRaises(ValueError):
            rff.reduce_level_flight_sweep(
                [1000.0] * n, [OMEGA] * n, [float(i) for i in range(n)],
                RHO_STD, W_REF, W_REF, F_I)
        with self.assertRaises(ValueError):
            rff.reduce_level_flight_sweep(
                [-1.0, 9000.0, 9000.0, 9000.0], [OMEGA] * 4,
                [10.0, 20.0, 30.0, 40.0], RHO_STD, W_REF, W_REF, F_I)
        with self.assertRaises(ValueError):
            rff.reduce_level_flight_sweep(
                TORQUES[:4], [OMEGA] * 4, [10.0, 20.0, 30.0, 40.0],
                RHO_STD, W_REF, W_REF, 1.5)

    def test_determinism_and_module_constants(self):
        res_a = self._reduce()
        res_b = self._reduce()
        self.assertEqual(res_a["fit"], res_b["fit"])
        self.assertEqual(res_a["best_endurance_speed_ms"],
                         res_b["best_endurance_speed_ms"])
        self.assertEqual(res_a["best_range_speed_ms"],
                         res_b["best_range_speed_ms"])
        self.assertEqual(res_a["max_level_speed_ms"],
                         res_b["max_level_speed_ms"])
        self.assertEqual(rff.RHO_STD, 1.225)
        self.assertEqual(rff.G0, 9.80665)
        self.assertEqual(rff.MIN_SPEED_SWEEP, 4)
        self.assertEqual(rff.MAX_SPEED_SWEEP, 40)
        self.assertEqual(rff.FIT_ORDER, 2)
        self.assertEqual(rff.RANGE_TANGENT_EPS, 1e-9)


if __name__ == "__main__":
    unittest.main()
