#!/usr/bin/env python3
"""Contract test: rotorcraft forward-flight performance.

Exercises scripts/rotorcraft_forward_flight_performance_logic.py
(stdlib unittest, offline, deterministic). Contract per the wave-30
spec: the Glauert induced velocity at a flight speed by fixed-point
iteration of v = thrust / (2 * rho * area * sqrt(speed**2 + v**2)),
induced power, parasite power from the equivalent flat-plate drag
area, profile power from blade solidity and tip speed, total power
through the induced power factor, the total power speed sweep, and
the best endurance and best range speeds. Non-physical inputs raise
ValueError; a non-converging Glauert iteration raises RuntimeError.

Worked rotor (same as the hover leaf): R = 5.0 m (A = 78.5398 m2),
m = 2200 kg (T = 21574.63 N), rho = 1.225 kg/m3, solidity 0.08,
Cd0 = 0.012, tip speed 220 m/s, f = 2.2 m2, V = 60 m/s. Real module
outputs are the assert targets; spec magnitude bounds are checked too.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rotorcraft_forward_flight_performance_logic as rffp  # noqa: E402

# Worked rotor inputs (SI).
AREA = math.pi * 5.0 * 5.0     # 78.5398 m2
THRUST = 2200.0 * rffp.G0      # 21574.63 N
RHO = 1.225
SOLIDITY = 0.08
CD0 = 0.012
TIP_SPEED = 220.0
FLAT_PLATE = 2.2               # m2, equivalent flat-plate drag area
V60 = 60.0

# Real module outputs on the worked rotor (assert targets).
V_HOVER = 10.588725632796958      # m/s
V_60 = 1.8677804021557536         # m/s
P_INDUCED_60 = 40296.67109776158  # W (ideal induced, thrust * v)
P_PARASITE_60 = 291060.0          # W
P_PROFILE = 122934.91876468362    # W
P_TOTAL_60 = 460336.09052710945   # W
BEST_ENDURANCE = 28.0             # m/s
BEST_RANGE = 45.0                 # m/s (see BestSpeedTest note)
BEST_RANGE_RATIO = 6832.216977872984  # W per (m/s) at best range speed


class ModuleConstantsTest(unittest.TestCase):
    def test_module_constants(self):
        self.assertEqual(rffp.G0, 9.80665)
        self.assertEqual(rffp.RHO_SL, 1.225)
        self.assertEqual(rffp.K_DEFAULT, 1.15)
        self.assertEqual(rffp.CD0_DEFAULT, 0.012)
        self.assertEqual(rffp.MAX_ITER, 60)
        self.assertEqual(rffp.TOL, 1e-9)
        self.assertEqual(rffp.PI, math.pi)


class HoverInducedVelocityTest(unittest.TestCase):
    def test_worked_value(self):
        vh = rffp.hover_induced_velocity(THRUST, AREA, RHO)
        self.assertAlmostEqual(vh, V_HOVER, delta=1e-9)
        # Hand value: sqrt(21574.63 / (2 * 1.225 * 78.5398)) ~ 10.59.
        self.assertAlmostEqual(vh, 10.59, delta=0.01)

    def test_closed_form(self):
        vh = rffp.hover_induced_velocity(80000.0, 40.0, 1.225)
        self.assertAlmostEqual(
            vh, math.sqrt(80000.0 / (2.0 * 1.225 * 40.0)), delta=1e-12)

    def test_nonphysical_inputs_raise(self):
        base = {"thrust": THRUST, "area": AREA, "rho": RHO}
        for kw in ({"thrust": 0.0}, {"thrust": -1.0}, {"area": 0.0},
                   {"area": -5.0}, {"rho": 0.0}, {"rho": -1.0}):
            args = dict(base)
            args.update(kw)
            with self.assertRaises(ValueError):
                rffp.hover_induced_velocity(**args)


class GlauertInducedVelocityTest(unittest.TestCase):
    def test_worked_sixty_bounds(self):
        v = rffp.glauert_induced_velocity(THRUST, AREA, RHO, V60)
        # Spec magnitude bound: 1.5-2.3 m/s at 60 m/s.
        self.assertGreater(v, 1.5)
        self.assertLess(v, 2.3)
        self.assertAlmostEqual(v, 1.868, delta=0.0005)

    def test_speed_zero_returns_hover_value(self):
        # Identity: glauert at speed 0 must equal the hover value.
        v0 = rffp.glauert_induced_velocity(THRUST, AREA, RHO, 0.0)
        vh = rffp.hover_induced_velocity(THRUST, AREA, RHO)
        self.assertAlmostEqual(v0, vh, delta=1e-6)

    def test_induced_velocity_decreases_with_speed(self):
        v20 = rffp.glauert_induced_velocity(THRUST, AREA, RHO, 20.0)
        v60 = rffp.glauert_induced_velocity(THRUST, AREA, RHO, V60)
        self.assertGreater(v20, v60)

    def test_high_speed_asymptote(self):
        # For V >> v_h the Glauert solution tends to v ~ v_h**2 / V.
        v = rffp.glauert_induced_velocity(THRUST, AREA, RHO, 100.0)
        vh2 = rffp.hover_induced_velocity(THRUST, AREA, RHO) ** 2
        self.assertAlmostEqual(v * 100.0, vh2, delta=0.15)

    def test_nonphysical_inputs_raise(self):
        base = {"thrust": THRUST, "area": AREA, "rho": RHO, "speed": V60}
        for kw in ({"speed": -1.0}, {"thrust": 0.0}, {"thrust": -5.0},
                   {"area": 0.0}, {"area": -1.0}, {"rho": 0.0},
                   {"rho": -1.0}):
            args = dict(base)
            args.update(kw)
            with self.assertRaises(ValueError):
                rffp.glauert_induced_velocity(**args)

    def test_max_iter_exceeded_raises_runtime_error(self):
        # Forcing max_iter=2 must surface the failure mode.
        with self.assertRaises(RuntimeError):
            rffp.glauert_induced_velocity(THRUST, AREA, RHO, V60,
                                          max_iter=2)

    def test_default_cap_converges_at_sweep_low_end(self):
        # The default sweep starts at 5 m/s; plain substitution would
        # need more than MAX_ITER passes near hover, the accelerated
        # fixed point must converge within the default cap.
        v5 = rffp.glauert_induced_velocity(THRUST, AREA, RHO, 5.0)
        self.assertGreater(v5, 9.0)
        self.assertLess(v5, 11.0)

    def test_deterministic(self):
        a = rffp.glauert_induced_velocity(THRUST, AREA, RHO, V60)
        b = rffp.glauert_induced_velocity(THRUST, AREA, RHO, V60)
        self.assertEqual(a, b)


class InducedPowerTest(unittest.TestCase):
    def test_worked_sixty_bounds(self):
        v = rffp.glauert_induced_velocity(THRUST, AREA, RHO, V60)
        p = rffp.induced_power(THRUST, v)
        # Spec magnitude bound: 35000-50000 W at 60 m/s.
        self.assertGreater(p, 35000.0)
        self.assertLess(p, 50000.0)
        self.assertAlmostEqual(p, 40297.0, delta=1.0)

    def test_thrust_times_velocity(self):
        p = rffp.induced_power(80000.0, 6.5)
        self.assertAlmostEqual(p, 80000.0 * 6.5, delta=1e-6)

    def test_nonphysical_inputs_raise(self):
        base = {"thrust": THRUST, "induced_velocity": 5.0}
        for kw in ({"thrust": 0.0}, {"thrust": -1.0},
                   {"induced_velocity": -0.5}):
            args = dict(base)
            args.update(kw)
            with self.assertRaises(ValueError):
                rffp.induced_power(**args)


class ParasitePowerTest(unittest.TestCase):
    def test_worked_sixty_bounds(self):
        p = rffp.parasite_power(RHO, V60, FLAT_PLATE)
        # Spec magnitude bound: 270000-320000 W at 60 m/s.
        self.assertGreater(p, 270000.0)
        self.assertLess(p, 320000.0)
        self.assertAlmostEqual(p, 291060.0, delta=1.0)

    def test_closed_form_and_zero_speed(self):
        p = rffp.parasite_power(1.225, 30.0, 1.0)
        self.assertAlmostEqual(p, 0.5 * 1.225 * 30.0 ** 3, delta=1e-6)
        self.assertEqual(rffp.parasite_power(RHO, 0.0, FLAT_PLATE), 0.0)

    def test_monotonic_in_speed(self):
        # Sanity: parasite power at 20 m/s below that at 80 m/s.
        p20 = rffp.parasite_power(RHO, 20.0, FLAT_PLATE)
        p80 = rffp.parasite_power(RHO, 80.0, FLAT_PLATE)
        self.assertLess(p20, p80)

    def test_nonphysical_inputs_raise(self):
        base = {"rho": RHO, "speed": V60, "flat_plate_area": FLAT_PLATE}
        for kw in ({"speed": -1.0}, {"flat_plate_area": -2.2},
                   {"rho": 0.0}, {"rho": -1.0}):
            args = dict(base)
            args.update(kw)
            with self.assertRaises(ValueError):
                rffp.parasite_power(**args)


class ProfilePowerTest(unittest.TestCase):
    def test_worked_bounds_and_default_cd0(self):
        p = rffp.profile_power(RHO, AREA, SOLIDITY, CD0, TIP_SPEED)
        # Spec magnitude bound: 100000-150000 W (as in the hover leaf).
        self.assertGreater(p, 100000.0)
        self.assertLess(p, 150000.0)
        self.assertAlmostEqual(p, 122935.0, delta=1.0)
        # Default drag coefficient matches the explicit Cd0.
        p_def = rffp.profile_power(RHO, AREA, SOLIDITY,
                                   tip_speed=TIP_SPEED)
        self.assertAlmostEqual(p_def, p, delta=1e-9)

    def test_eighth_formula(self):
        p = rffp.profile_power(RHO, AREA, SOLIDITY, CD0, TIP_SPEED)
        expected = (1.0 / 8.0) * RHO * SOLIDITY * CD0 * AREA \
            * TIP_SPEED ** 3
        self.assertAlmostEqual(p, expected, delta=1e-6)

    def test_nonphysical_inputs_raise(self):
        base = {"rho": RHO, "area": AREA, "solidity": SOLIDITY,
                "drag_coefficient": CD0, "tip_speed": TIP_SPEED}
        for kw in ({"solidity": 0.0}, {"solidity": -0.1},
                   {"drag_coefficient": 0.0}, {"drag_coefficient": -0.5},
                   {"tip_speed": 0.0}, {"tip_speed": -10.0},
                   {"rho": 0.0}, {"area": 0.0}):
            args = dict(base)
            args.update(kw)
            with self.assertRaises(ValueError):
                rffp.profile_power(**args)


class TotalPowerTest(unittest.TestCase):
    def test_worked_sixty_bounds(self):
        v = rffp.glauert_induced_velocity(THRUST, AREA, RHO, V60)
        p_prof = rffp.profile_power(RHO, AREA, SOLIDITY, CD0, TIP_SPEED)
        p_par = rffp.parasite_power(RHO, V60, FLAT_PLATE)
        p_tot = rffp.total_power(THRUST, v, p_prof, p_par, k=1.15)
        # Spec magnitude bound: 420000-500000 W at 60 m/s.
        self.assertGreater(p_tot, 420000.0)
        self.assertLess(p_tot, 500000.0)
        self.assertAlmostEqual(p_tot, 460336.0, delta=1.0)

    def test_sum_of_components(self):
        p_tot = rffp.total_power(THRUST, 3.0, 50000.0, 20000.0, k=1.15)
        self.assertAlmostEqual(p_tot, 1.15 * THRUST * 3.0 + 70000.0,
                               delta=1e-6)

    def test_nonphysical_inputs_raise(self):
        base = {"thrust": THRUST, "induced_velocity": 3.0,
                "profile_power": 50000.0, "parasite_power": 20000.0}
        for kw in ({"thrust": 0.0}, {"induced_velocity": -1.0},
                   {"profile_power": -1.0}, {"parasite_power": -1.0},
                   {"k": 0.0}, {"k": -1.15}):
            args = dict(base)
            args.update(kw)
            with self.assertRaises(ValueError):
                rffp.total_power(**args)


class PowerSweepTest(unittest.TestCase):
    def test_default_sweep_length_and_span(self):
        sweep = rffp.power_sweep(THRUST, AREA, RHO, FLAT_PLATE, SOLIDITY)
        # Defaults: 5.0 to 100.0 m/s in 1.0 m/s steps -> 96 pairs.
        self.assertEqual(len(sweep), 96)
        self.assertEqual(sweep[0][0], 5.0)
        self.assertEqual(sweep[-1][0], 100.0)

    def test_sixty_metres_per_second_total(self):
        sweep = rffp.power_sweep(THRUST, AREA, RHO, FLAT_PLATE, SOLIDITY)
        p60 = dict(sweep)[V60]
        self.assertAlmostEqual(p60, P_TOTAL_60, delta=1e-6)

    def test_custom_speeds(self):
        sweep = rffp.power_sweep(THRUST, AREA, RHO, FLAT_PLATE, SOLIDITY,
                                 speeds=[10.0, 20.0, 30.0])
        self.assertEqual([s for s, _ in sweep], [10.0, 20.0, 30.0])

    def test_negative_speed_raises(self):
        with self.assertRaises(ValueError):
            rffp.power_sweep(THRUST, AREA, RHO, FLAT_PLATE, SOLIDITY,
                             speeds=[10.0, -5.0])


class BestSpeedTest(unittest.TestCase):
    def test_best_endurance_bounds(self):
        # Spec magnitude bound: best endurance speed in 25-45 m/s.
        v_be = rffp.best_endurance_speed(
            THRUST, AREA, RHO, FLAT_PLATE, SOLIDITY)
        self.assertGreaterEqual(v_be, 25.0)
        self.assertLessEqual(v_be, 45.0)
        self.assertEqual(v_be, BEST_ENDURANCE)

    def test_best_range_above_best_endurance(self):
        # Physics check: best range speed strictly above best endurance.
        v_be = rffp.best_endurance_speed(
            THRUST, AREA, RHO, FLAT_PLATE, SOLIDITY)
        v_br = rffp.best_range_speed(
            THRUST, AREA, RHO, FLAT_PLATE, SOLIDITY)
        self.assertGreater(v_br[0], v_be)

    def test_best_range_module_output(self):
        # Real module output on the worked rotor. The spec draft
        # window of 50-90 m/s is not reachable by its own model at
        # f = 2.2 m2: momentum theory places the P/V minimum at about
        # 45 m/s (best endurance 28 m/s), so the module value is the
        # assert target with a wide physical sanity band.
        v_br = rffp.best_range_speed(
            THRUST, AREA, RHO, FLAT_PLATE, SOLIDITY)
        self.assertEqual(v_br[0], BEST_RANGE)
        self.assertGreaterEqual(v_br[0], 40.0)
        self.assertLessEqual(v_br[0], 60.0)
        self.assertAlmostEqual(v_br[1], BEST_RANGE_RATIO, delta=1e-6)

    def test_best_endurance_is_sweep_minimum(self):
        sweep = rffp.power_sweep(THRUST, AREA, RHO, FLAT_PLATE, SOLIDITY)
        v_be = rffp.best_endurance_speed(
            THRUST, AREA, RHO, FLAT_PLATE, SOLIDITY)
        p_min = min(p for _, p in sweep)
        self.assertAlmostEqual(dict(sweep)[v_be], p_min, delta=1e-6)

    def test_best_range_is_p_over_v_minimum(self):
        sweep = rffp.power_sweep(THRUST, AREA, RHO, FLAT_PLATE, SOLIDITY)
        v_br, ratio = rffp.best_range_speed(
            THRUST, AREA, RHO, FLAT_PLATE, SOLIDITY)
        ratios = {s: p / s for s, p in sweep if s > 0}
        self.assertAlmostEqual(ratio, min(ratios.values()), delta=1e-6)
        self.assertAlmostEqual(ratios[v_br], ratio, delta=1e-6)


if __name__ == "__main__":
    unittest.main()
