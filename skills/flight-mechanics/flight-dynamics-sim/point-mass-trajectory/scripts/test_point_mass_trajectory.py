#!/usr/bin/env python3
"""Gate 3 contract test: point-mass trajectory simulation logic.

Exercises scripts/point_mass_trajectory_logic.py (stdlib unittest,
offline, deterministic, runs in well under 20 s). Contract: ISA
atmosphere anchors, the parabolic drag polar, the thrust altitude
lapse, the vertical-plane point-mass derivatives, the fixed-step RK4
propagator with the ground-reference clamp, the worked-example
climb-out trajectory, the closed-form steady-climb consistency check,
the level-cruise force balance identity, and ValueError rejection of
every non-physical input class.

Worked example (transport-like climb): m = 70000 kg, S = 122.6 m^2,
CD0 = 0.021, e = 0.81, AR = 9.3, T_sl = 2 * 110000 N, rho_sl = 1.225
kg/m^3, constant CL = 1.07 (fixed-alpha climb assumption), start at
h0 = 0, V0 = 90 m/s, gamma0 = 0, dt = 0.5 s, n_steps = 600. Real run
anchors used below: dV/dt(t=0) = 2.54 m/s^2 (positive), h(t=300) =
4788.0 m, V(t=300) = 172.7 m/s, final closed-form steady-climb
gamma = 9.49 deg versus mean sin(gamma) over the last 50 s = 0.1284
(ratio 0.78, inside the 30% consistency band).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import point_mass_trajectory_logic as pm


class TestIsaAtmosphere(unittest.TestCase):
    """ISA atmosphere anchors and monotonicity."""

    def test_isa_sea_level_conditions(self):
        a = pm.isa_atmosphere(0.0)
        self.assertAlmostEqual(a["rho"], 1.225, delta=0.01)  # within 0.5%
        self.assertAlmostEqual(a["p"], 101325.0, delta=50.0)
        self.assertAlmostEqual(a["T_K"], 288.15, delta=0.05)

    def test_isa_tropopause_conditions(self):
        a = pm.isa_atmosphere(11000.0)
        self.assertAlmostEqual(a["rho"], 0.3639, delta=0.0036)  # within 1%
        self.assertAlmostEqual(a["T_K"], 216.65, delta=0.05)

    def test_isa_troposphere_and_stratosphere(self):
        # Troposphere lapse below 11000 m; isothermal stratosphere
        # above with the exponential pressure decay.
        a2000 = pm.isa_atmosphere(2000.0)
        self.assertAlmostEqual(a2000["T_K"], 288.15 - 0.0065 * 2000.0, delta=0.05)
        self.assertGreater(pm.isa_atmosphere(0.0)["rho"], a2000["rho"])
        a15 = pm.isa_atmosphere(15000.0)
        self.assertAlmostEqual(a15["T_K"], 216.65, delta=0.01)
        expected_p = 22632.0 * math.exp(-4000.0 / 6341.62)
        self.assertAlmostEqual(a15["p"], expected_p, delta=5.0)

    def test_isa_density_monotonic_decreasing_to_20000(self):
        hs = [0.0, 2000.0, 4000.0, 6000.0, 8000.0, 11000.0, 14000.0, 17000.0, 20000.0]
        rhos = [pm.isa_atmosphere(h)["rho"] for h in hs]
        for i in range(1, len(rhos)):
            self.assertGreater(rhos[i - 1], rhos[i])

    def test_isa_negative_altitude_rejected(self):
        with self.assertRaises(ValueError):
            pm.isa_atmosphere(-1.0)


class TestDragPolarAndThrust(unittest.TestCase):
    """Parabolic drag polar and thrust altitude lapse."""

    def test_drag_polar_parabolic_values(self):
        self.assertAlmostEqual(pm.drag_polar_cd(0.021, 0.042255, 0.0), 0.021, places=6)
        self.assertAlmostEqual(pm.drag_polar_cd(0.021, 0.042255, 1.0), 0.063255, places=6)

    def test_drag_polar_negative_inputs_rejected(self):
        with self.assertRaises(ValueError):
            pm.drag_polar_cd(-0.01, 0.04, 0.5)
        with self.assertRaises(ValueError):
            pm.drag_polar_cd(0.02, -0.04, 0.5)

    def test_thrust_at_sea_level_and_lapse(self):
        self.assertAlmostEqual(
            pm.thrust_at_altitude(220000.0, 1.225, 1.225), 220000.0, places=1
        )
        t_high = pm.thrust_at_altitude(220000.0, 0.5, 1.225, 0.7)
        self.assertLess(t_high, 220000.0)
        self.assertGreater(t_high, 0.0)

    def test_thrust_lapse_exponent_behavior(self):
        # Zero exponent keeps thrust; lower density at fixed exponent
        # lowers thrust.
        self.assertAlmostEqual(
            pm.thrust_at_altitude(220000.0, 0.3, 1.225, 0.0), 220000.0, places=1
        )
        t1 = pm.thrust_at_altitude(220000.0, 0.9, 1.225, 0.7)
        t2 = pm.thrust_at_altitude(220000.0, 0.5, 1.225, 0.7)
        self.assertGreater(t1, t2)

    def test_thrust_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            pm.thrust_at_altitude(0.0, 1.0, 1.225)
        with self.assertRaises(ValueError):
            pm.thrust_at_altitude(100.0, 1.0, 0.0)


class TestDerivativesAndRk4(unittest.TestCase):
    """Point-mass derivatives and the fixed-step RK4 propagator."""

    def test_initial_acceleration_positive(self):
        p = pm.default_params()
        d = pm.point_mass_derivs([90.0, 0.0, 0.0, 0.0], p)
        self.assertGreater(d[0], 0.0)  # excess thrust accelerates

    def test_derivs_kinematic_identities(self):
        p = pm.default_params()
        v = 120.0
        gam = math.radians(10.0)
        d = pm.point_mass_derivs([v, gam, 3000.0, 0.0], p)
        self.assertEqual(len(d), 4)
        self.assertAlmostEqual(d[2], v * math.sin(gam), places=6)
        self.assertAlmostEqual(d[3], v * math.cos(gam), places=6)

    def test_level_cruise_force_balance_zero_derivs(self):
        # CL set so L = W and T = D: dV/dt and dgamma/dt are ~0.
        p = pm.default_params()
        rho = pm.isa_atmosphere(0.0)["rho"]
        cl = 1.13
        v = math.sqrt(2.0 * p["m"] * p["g0"] / (rho * p["S"] * cl))
        cd = pm.drag_polar_cd(p["cd0"], p["k"], cl)
        drag = 0.5 * rho * v * v * p["S"] * cd
        pc = dict(p)
        pc["cl"] = cl
        pc["thrust_sl"] = drag
        pc["thrust_lapse_exponent"] = 0.0
        d = pm.point_mass_derivs([v, 0.0, 0.0, 0.0], pc)
        self.assertAlmostEqual(d[0], 0.0, delta=1e-6)
        self.assertAlmostEqual(d[1], 0.0, delta=1e-9)

    def test_rk4_level_cruise_round_trip(self):
        # 10 steps at the exact cruise speed: speed stays within 0.5%.
        p = pm.default_params()
        rho = pm.isa_atmosphere(1000.0)["rho"]
        cl = 1.0
        v_cruise = math.sqrt(2.0 * p["m"] * p["g0"] / (rho * p["S"] * cl))
        cd = pm.drag_polar_cd(p["cd0"], p["k"], cl)
        drag = 0.5 * rho * v_cruise * v_cruise * p["S"] * cd
        pc = dict(p)
        pc["cl"] = cl
        pc["thrust_sl"] = drag
        pc["thrust_lapse_exponent"] = 0.0
        state = [v_cruise, 0.0, 1000.0, 0.0]
        for _ in range(10):
            state = pm.rk4_step(state, pc, 0.5)
        drift = abs(state[0] - v_cruise) / v_cruise
        self.assertLess(drift, 0.005)

    def test_unpowered_state_decelerates_and_bad_speed_rejected(self):
        # No thrust: decelerates. Negative airspeed: ValueError.
        p = pm.default_params()
        pc = dict(p)
        pc["thrust_sl"] = 1.0
        pc["thrust_lapse_exponent"] = 0.0
        pc["cl"] = 0.4
        d = pm.point_mass_derivs([90.0, 0.0, 1000.0, 0.0], pc)
        self.assertLess(d[0], 0.0)
        with self.assertRaises(ValueError):
            pm.point_mass_derivs([-5.0, 0.0, 0.0, 0.0], p)


class TestWorkedExample(unittest.TestCase):
    """Worked-example transport climb-out (module defaults)."""

    def setUp(self):
        self.p = pm.default_params()  # CL = 1.07, T_sl = 220 kN
        self.traj = pm.simulate_trajectory(
            (90.0, 0.0, 0.0, 0.0), self.p, dt=0.5, n_steps=600
        )
        self.states = self.traj["states"]
        self.derived = self.traj["derived"]

    def test_initial_acceleration_positive_and_climb(self):
        d0 = pm.point_mass_derivs([90.0, 0.0, 0.0, 0.0], self.p)
        self.assertGreater(d0[0], 0.0)
        self.assertGreater(self.states[-1][2], self.states[0][2])

    def test_altitude_at_300s_in_band(self):
        h300 = self.states[600][2]
        self.assertGreater(h300, 1500.0)
        self.assertLess(h300, 5000.0)
        self.assertAlmostEqual(h300, 4788.0, delta=80.0)

    def test_speed_at_300s(self):
        v300 = self.states[600][0]
        self.assertAlmostEqual(v300, 172.7, delta=3.0)
        self.assertGreater(v300, 90.0)

    def test_altitude_monotone_trend(self):
        hs = [self.states[i][2] for i in range(0, 601, 60)]
        self.assertGreater(hs[-1], hs[0])

    def test_state_and_derived_consistency(self):
        self.assertEqual(len(self.states), 601)
        self.assertEqual(len(self.derived), 600)
        d = self.derived[299]
        for key in ("q", "CD", "L", "D", "T"):
            self.assertGreater(d[key], 0.0)
        self.assertGreater(d["CL"], 0.0)
        weight = self.p["m"] * self.p["g0"]
        self.assertAlmostEqual(d["load_factor"], d["L"] / weight, places=9)

    def test_thrust_lapses_with_altitude(self):
        self.assertLess(self.derived[300]["T"], self.derived[0]["T"])

    def test_ground_reference_respected(self):
        for s in self.states:
            self.assertGreaterEqual(s[2], -1e-9)

    def test_no_ground_return_after_initial_climb(self):
        # After the initial climb-out the altitude never returns to
        # the ground, even at the phugoid troughs.
        for s in self.states[200:]:
            self.assertGreater(s[2], 10.0)

    def test_stall_events_recorded(self):
        n_stall = sum(1 for d in self.derived if d["stall_event"])
        self.assertGreater(n_stall, 0)  # low-speed phugoid troughs flag
        self.assertLessEqual(n_stall, len(self.derived))

    def test_steady_climb_consistency_within_30_percent(self):
        # Closed form at the end state: sin(gamma) = (T - D) / W with
        # L = W. Compare with the mean sin(gamma) over the last 50 s.
        s = self.states[600]
        rho = pm.isa_atmosphere(s[2])["rho"]
        thrust = pm.thrust_at_altitude(
            self.p["thrust_sl"], rho, self.p["rho_sl"], self.p["thrust_lapse_exponent"]
        )
        gamma_cf, cl_cf, cd_cf = pm.steady_climb_angle(
            s[0], thrust, self.p["m"], self.p["cd0"], self.p["k"], self.p["S"], rho
        )
        sin_cf = math.sin(math.radians(gamma_cf))
        tail = self.states[500:601]
        mean_sin = sum(math.sin(x[1]) for x in tail) / len(tail)
        ratio = mean_sin / sin_cf
        self.assertGreater(ratio, 0.5)  # well inside the 30% band
        self.assertLess(ratio, 1.5)


class TestValueErrors(unittest.TestCase):
    """ValueError rejection of every non-physical input class."""

    def _params(self):
        return pm.default_params()

    def test_bad_initial_state(self):
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, -10.0, 0.0), self._params())
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((0.0, 0.0, 0.0, 0.0), self._params())
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((-10.0, 0.0, 0.0, 0.0), self._params())
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0), self._params())

    def test_bad_dt_and_n_steps(self):
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), self._params(), dt=0.0)
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), self._params(), dt=-0.5)
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), self._params(), n_steps=0)

    def test_nonphysical_mass_area_thrust(self):
        p = self._params()
        p["m"] = 0.0
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), p)
        p = self._params()
        p["S"] = -5.0
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), p)
        p = self._params()
        p["thrust_sl"] = 0.0
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), p)

    def test_nonphysical_polar_and_geometry(self):
        p = self._params()
        p["cd0"] = -0.01
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), p)
        p = self._params()
        p["e"] = 1.5
        p["k"] = 1.0 / (math.pi * 1.5 * p["AR"])
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), p)
        p = self._params()
        p["e"] = 0.0
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), p)
        p = self._params()
        p["AR"] = 0.0
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), p)

    def test_k_inconsistent_with_e_ar_and_missing_keys(self):
        p = self._params()
        p["k"] = 0.1  # does not equal 1/(pi e AR)
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), p)
        p = self._params()
        del p["S"]
        with self.assertRaises(ValueError):
            pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), p)

    def test_steady_climb_and_summary_bad_inputs(self):
        rho = pm.isa_atmosphere(0.0)["rho"]
        with self.assertRaises(ValueError):
            pm.steady_climb_angle(90.0, 1000.0, -70000.0, 0.021, 0.04, 122.6, rho)
        with self.assertRaises(ValueError):
            pm.steady_climb_angle(90.0, -1.0, 70000.0, 0.021, 0.04, 122.6, rho)
        with self.assertRaises(ValueError):
            pm.end_of_sim_summary([])
        with self.assertRaises(ValueError):
            pm.level_trim_cl(0.0, 90.0, 122.6, 1.225)
        with self.assertRaises(ValueError):
            pm.level_trim_cl(70000.0, -90.0, 122.6, 1.225)


class TestSummaryHelpers(unittest.TestCase):
    """Summary dicts and the trim/steady-climb helpers."""

    def test_summary_fields_and_identity(self):
        p = pm.default_params()
        traj = pm.simulate_trajectory((90.0, 0.0, 0.0, 0.0), p, dt=0.5, n_steps=60)
        sm = pm.end_of_sim_summary(traj["states"])
        for key in ("final_state", "initial_state", "climb", "range", "speed_change"):
            self.assertIn(key, sm)
        self.assertAlmostEqual(
            sm["climb"], sm["final_state"][2] - sm["initial_state"][2], places=6
        )
        self.assertEqual(len(sm["final_state"]), 4)

    def test_level_trim_cl_formula(self):
        # CL = 2 W / (rho V^2 S): at V=90, h=0, CL ~= 1.1286, below
        # the CL_max = 1.5 limit, so the takeoff state is not stalled.
        cl = pm.level_trim_cl(70000.0, 90.0, 122.6, 1.225)
        self.assertAlmostEqual(cl, 1.1286, delta=0.001)
        self.assertLess(cl, 1.5)

    def test_steady_climb_angle_positive(self):
        rho = pm.isa_atmosphere(0.0)["rho"]
        gam, cl, cd = pm.steady_climb_angle(
            140.0, 220000.0, 70000.0, 0.021, 0.042255, 122.6, rho
        )
        self.assertGreater(gam, 0.0)
        self.assertGreater(cd, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
