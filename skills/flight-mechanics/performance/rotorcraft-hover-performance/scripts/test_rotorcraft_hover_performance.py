"""Contract test for the rotorcraft-hover-performance momentum-theory model.

Deterministic, offline, stdlib unittest. Run from the leaf directory:

    python3 scripts/test_rotorcraft_hover_performance.py

Covers the worked example (R = 5.0 m, 2200 kg, sea level, solidity 0.08,
Cd0 = 0.012, tip speed 220 m/s, k = 1.15) with the spec magnitude bounds,
every validation rule from the spec, the figure-of-merit round trip, the
convenience-chain identity, determinism, and dict key idempotence.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rotorcraft_hover_performance_logic as rhp

# Worked example inputs.
RADIUS = 5.0
WEIGHT_KG = 2200.0
RHO = 1.225
SOLIDITY = 0.08
CD0 = 0.012
TIP_SPEED = 220.0
K = 1.15

# Worked example module outputs (run once, taken as assert targets).
TARGET_AREA = 78.53981633974483
TARGET_V_I = 10.588725632796958
TARGET_IDEAL_POWER = 228447.8376991102
TARGET_PROFILE_POWER = 122934.91876468362
TARGET_TOTAL_POWER = 385649.9321186603
TARGET_FM = 0.5923710045638471
TARGET_DL = 274.6967207902958


class TestDiskArea(unittest.TestCase):

    def test_worked_example_area(self):
        self.assertAlmostEqual(rhp.disk_area(RADIUS), TARGET_AREA, places=6)
        self.assertAlmostEqual(rhp.disk_area(RADIUS), math.pi * 25.0,
                               places=12)

    def test_area_scales_with_radius_squared(self):
        a1 = rhp.disk_area(2.0)
        a2 = rhp.disk_area(4.0)
        self.assertAlmostEqual(a2 / a1, 4.0, places=12)

    def test_nonpositive_radius_raises(self):
        for bad_radius in (0.0, -1.0):
            with self.assertRaises(ValueError):
                rhp.disk_area(bad_radius)


class TestInducedVelocity(unittest.TestCase):

    def test_worked_example_velocity_in_spec_bounds(self):
        v = rhp.induced_velocity(WEIGHT_KG * rhp.G0, TARGET_AREA, RHO)
        self.assertAlmostEqual(v, TARGET_V_I, places=6)
        self.assertTrue(9.5 <= v <= 11.5, "induced velocity outside 9.5-11.5 m/s")

    def test_matches_momentum_theory_closed_form(self):
        thrust = WEIGHT_KG * rhp.G0
        self.assertAlmostEqual(
            rhp.induced_velocity(thrust, TARGET_AREA, RHO),
            math.sqrt(thrust / (2.0 * RHO * TARGET_AREA)), places=12)

    def test_nonpositive_thrust_raises(self):
        for bad_thrust in (0.0, -100.0):
            with self.assertRaises(ValueError):
                rhp.induced_velocity(bad_thrust, 10.0, RHO)

    def test_nonpositive_area_or_rho_raises(self):
        with self.assertRaises(ValueError):
            rhp.induced_velocity(10000.0, 0.0, RHO)
        with self.assertRaises(ValueError):
            rhp.induced_velocity(10000.0, 10.0, 0.0)


class TestIdealPower(unittest.TestCase):

    def test_worked_example_ideal_power_in_spec_bounds(self):
        thrust = WEIGHT_KG * rhp.G0
        p = rhp.ideal_power(thrust, TARGET_V_I)
        self.assertAlmostEqual(p, TARGET_IDEAL_POWER, places=6)
        self.assertTrue(200000.0 <= p <= 260000.0,
                        "ideal power outside 200000-260000 W")

    def test_equals_thrust_times_velocity(self):
        self.assertAlmostEqual(
            rhp.ideal_power(21574.63, TARGET_V_I),
            21574.63 * TARGET_V_I, places=6)
        self.assertEqual(rhp.ideal_power(0.0, 10.0), 0.0)

    def test_negative_inputs_raise(self):
        with self.assertRaises(ValueError):
            rhp.ideal_power(-1.0, 10.0)
        with self.assertRaises(ValueError):
            rhp.ideal_power(1000.0, -1.0)


class TestProfilePower(unittest.TestCase):

    def test_worked_example_profile_power_in_spec_bounds(self):
        p = rhp.profile_power(RHO, TARGET_AREA, SOLIDITY, CD0, TIP_SPEED)
        self.assertAlmostEqual(p, TARGET_PROFILE_POWER, places=6)
        self.assertTrue(100000.0 <= p <= 150000.0,
                        "profile power outside 100000-150000 W")

    def test_matches_average_section_drag_formula(self):
        expected = (1.0 / 8.0) * RHO * SOLIDITY * CD0 * TARGET_AREA \
            * TIP_SPEED ** 3
        self.assertAlmostEqual(
            rhp.profile_power(RHO, TARGET_AREA, SOLIDITY, CD0, TIP_SPEED),
            expected, places=6)

    def test_cubic_scaling_with_tip_speed(self):
        p1 = rhp.profile_power(RHO, TARGET_AREA, SOLIDITY, CD0, 200.0)
        p2 = rhp.profile_power(RHO, TARGET_AREA, SOLIDITY, CD0, 400.0)
        self.assertAlmostEqual(p2 / p1, 8.0, places=6)

    def test_nonpositive_inputs_raise(self):
        bad = [
            dict(rho=0.0), dict(rho=-1.0),
            dict(area=0.0), dict(area=-1.0),
            dict(solidity=0.0), dict(solidity=-0.1),
            dict(drag_coefficient=0.0), dict(drag_coefficient=-0.01),
            dict(tip_speed=0.0), dict(tip_speed=-1.0),
        ]
        base = dict(rho=1.0, area=1.0, solidity=1.0,
                    drag_coefficient=1.0, tip_speed=1.0)
        for kwargs in bad:
            params = dict(base)
            params.update(kwargs)
            with self.assertRaises(ValueError):
                rhp.profile_power(**params)


class TestTotalPower(unittest.TestCase):

    def test_worked_example_total_power_in_spec_bounds(self):
        thrust = WEIGHT_KG * rhp.G0
        p = rhp.total_power(TARGET_IDEAL_POWER, TARGET_V_I, thrust,
                            TARGET_PROFILE_POWER, K)
        self.assertAlmostEqual(p, TARGET_TOTAL_POWER, places=6)
        self.assertTrue(350000.0 <= p <= 430000.0,
                        "total power outside 350000-430000 W")

    def test_matches_induced_power_factor_model(self):
        thrust = WEIGHT_KG * rhp.G0
        expected = K * thrust * TARGET_V_I + TARGET_PROFILE_POWER
        self.assertAlmostEqual(
            rhp.total_power(TARGET_IDEAL_POWER, TARGET_V_I, thrust,
                            TARGET_PROFILE_POWER, K),
            expected, places=6)

    def test_default_k_matches_module_constant(self):
        thrust = WEIGHT_KG * rhp.G0
        p_default = rhp.total_power(TARGET_IDEAL_POWER, TARGET_V_I,
                                    thrust, TARGET_PROFILE_POWER)
        p_explicit = rhp.total_power(TARGET_IDEAL_POWER, TARGET_V_I,
                                     thrust, TARGET_PROFILE_POWER,
                                     rhp.K_DEFAULT)
        self.assertAlmostEqual(p_default, p_explicit, places=12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rhp.total_power(-1.0, 10.0, 1000.0, 100.0)
        with self.assertRaises(ValueError):
            rhp.total_power(1000.0, 10.0, 1000.0, -1.0)
        for bad_k in (0.0, -1.15):
            with self.assertRaises(ValueError):
                rhp.total_power(1000.0, 10.0, 1000.0, 100.0, bad_k)


class TestFigureOfMerit(unittest.TestCase):

    def test_worked_example_fm_in_spec_bounds(self):
        fm = rhp.figure_of_merit(TARGET_IDEAL_POWER, TARGET_TOTAL_POWER)
        self.assertAlmostEqual(fm, TARGET_FM, places=6)
        self.assertTrue(0.50 <= fm <= 0.70,
                        "figure of merit outside 0.50-0.70")
        self.assertAlmostEqual(fm, TARGET_IDEAL_POWER / TARGET_TOTAL_POWER,
                               places=12)

    def test_round_trip_through_power_from_figure_of_merit(self):
        fm = rhp.figure_of_merit(TARGET_IDEAL_POWER, TARGET_TOTAL_POWER)
        p_back = rhp.power_from_figure_of_merit(TARGET_IDEAL_POWER, fm)
        self.assertAlmostEqual(p_back, TARGET_TOTAL_POWER, places=6)
        self.assertAlmostEqual(p_back / TARGET_TOTAL_POWER, 1.0, places=9)
        self.assertAlmostEqual(rhp.power_from_figure_of_merit(1000.0, 1.0),
                               1000.0, places=12)

    def test_equality_allowed_gives_unit_fm(self):
        self.assertEqual(rhp.figure_of_merit(5000.0, 5000.0), 1.0)

    def test_nonphysical_ideal_total_pairs_raise(self):
        with self.assertRaises(ValueError):
            rhp.figure_of_merit(6000.0, 5000.0)
        for bad_total in (0.0, -5000.0):
            with self.assertRaises(ValueError):
                rhp.figure_of_merit(1000.0, bad_total)
        with self.assertRaises(ValueError):
            rhp.figure_of_merit(-1.0, 5000.0)

    def test_power_from_fm_rejects_out_of_range_fm(self):
        with self.assertRaises(ValueError):
            rhp.power_from_figure_of_merit(1000.0, 0.0)
        with self.assertRaises(ValueError):
            rhp.power_from_figure_of_merit(1000.0, 1.1)
        with self.assertRaises(ValueError):
            rhp.power_from_figure_of_merit(-1.0, 0.5)


class TestDiskLoading(unittest.TestCase):

    def test_worked_example_dl_in_spec_bounds(self):
        thrust = WEIGHT_KG * rhp.G0
        dl = rhp.disk_loading(thrust, TARGET_AREA)
        self.assertAlmostEqual(dl, TARGET_DL, places=6)
        self.assertTrue(260.0 <= dl <= 290.0,
                        "disk loading outside 260-290 Pa")

    def test_matches_thrust_over_area(self):
        self.assertAlmostEqual(
            rhp.disk_loading(21574.63, TARGET_AREA),
            21574.63 / TARGET_AREA, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rhp.disk_loading(-1.0, TARGET_AREA)
        for bad_area in (0.0, -5.0):
            with self.assertRaises(ValueError):
                rhp.disk_loading(1000.0, bad_area)


class TestHoverPerformanceChain(unittest.TestCase):

    CHAIN_KEYS = {"thrust_N", "area_m2", "induced_velocity",
                  "ideal_power_W", "profile_power_W", "total_power_W",
                  "figure_of_merit", "disk_loading_Pa"}

    def test_chain_dict_has_exact_keys(self):
        out = rhp.hover_performance(WEIGHT_KG, RADIUS, RHO, SOLIDITY,
                                    CD0, TIP_SPEED, K)
        self.assertEqual(set(out.keys()), self.CHAIN_KEYS)

    def test_chain_matches_primitives(self):
        out = rhp.hover_performance(WEIGHT_KG, RADIUS, RHO, SOLIDITY,
                                    CD0, TIP_SPEED, K)
        thrust = WEIGHT_KG * rhp.G0
        area = rhp.disk_area(RADIUS)
        v_i = rhp.induced_velocity(thrust, area, RHO)
        self.assertAlmostEqual(out["thrust_N"], thrust, places=9)
        self.assertAlmostEqual(out["area_m2"], area, places=9)
        self.assertAlmostEqual(out["induced_velocity"], v_i, places=9)
        self.assertAlmostEqual(out["ideal_power_W"],
                               rhp.ideal_power(thrust, v_i), places=6)
        self.assertAlmostEqual(out["profile_power_W"],
                               rhp.profile_power(RHO, area, SOLIDITY, CD0,
                                                 TIP_SPEED), places=6)
        self.assertAlmostEqual(out["total_power_W"],
                               rhp.total_power(out["ideal_power_W"], v_i,
                                               thrust,
                                               out["profile_power_W"], K),
                               places=6)
        self.assertAlmostEqual(out["figure_of_merit"],
                               rhp.figure_of_merit(out["ideal_power_W"],
                                                   out["total_power_W"]),
                               places=12)
        self.assertAlmostEqual(out["disk_loading_Pa"],
                               rhp.disk_loading(thrust, area), places=9)

    def test_chain_worked_example_outputs(self):
        out = rhp.hover_performance(WEIGHT_KG, RADIUS, RHO, SOLIDITY,
                                    CD0, TIP_SPEED, K)
        self.assertAlmostEqual(out["induced_velocity"], TARGET_V_I, places=6)
        self.assertAlmostEqual(out["ideal_power_W"], TARGET_IDEAL_POWER,
                               places=6)
        self.assertAlmostEqual(out["profile_power_W"], TARGET_PROFILE_POWER,
                               places=6)
        self.assertAlmostEqual(out["total_power_W"], TARGET_TOTAL_POWER,
                               places=6)
        self.assertAlmostEqual(out["figure_of_merit"], TARGET_FM, places=6)
        self.assertAlmostEqual(out["disk_loading_Pa"], TARGET_DL, places=6)

    def test_chain_defaults_use_module_constants(self):
        out_default = rhp.hover_performance(WEIGHT_KG, RADIUS)
        out_explicit = rhp.hover_performance(WEIGHT_KG, RADIUS,
                                             rhp.RHO_SL, 0.08, 0.012,
                                             220.0, rhp.K_DEFAULT)
        for key in self.CHAIN_KEYS:
            self.assertAlmostEqual(out_default[key], out_explicit[key],
                                   places=12)

    def test_chain_invalid_inputs_propagate_valueerror(self):
        with self.assertRaises(ValueError):
            rhp.hover_performance(0.0, RADIUS)
        with self.assertRaises(ValueError):
            rhp.hover_performance(WEIGHT_KG, -1.0)
        with self.assertRaises(ValueError):
            rhp.hover_performance(WEIGHT_KG, RADIUS, RHO, 0.0, CD0,
                                  TIP_SPEED)

    def test_determinism_repeated_calls_identical(self):
        a = rhp.hover_performance(WEIGHT_KG, RADIUS, RHO, SOLIDITY, CD0,
                                  TIP_SPEED, K)
        b = rhp.hover_performance(WEIGHT_KG, RADIUS, RHO, SOLIDITY, CD0,
                                  TIP_SPEED, K)
        for key in self.CHAIN_KEYS:
            self.assertEqual(a[key], b[key])

    def test_module_has_no_random_or_external_imports(self):
        with open(rhp.__file__, "r") as handle:
            imports = [line for line in handle
                       if line.startswith(("import ", "from "))]
        self.assertEqual(imports, ["import math\n"])


if __name__ == "__main__":
    unittest.main()
