"""Contract test for rotorcraft_blade_element_hover_performance_logic.

Offline, deterministic, stdlib unittest. Run from the repo root:

    python3 skills/flight-mechanics/performance/\
        rotorcraft-blade-element-hover-performance/scripts/\
        test_rotorcraft_blade_element_hover_performance.py

The reference rotor (identical to the momentum hover-leaf example):
R = 5.0 m, m = 2200 kg (T = m * G), rho = 1.225 kg/m^3, sigma = 0.08,
Cd0 = 0.012, Vtip = 220 m/s, a = 5.73 1/rad. Real module outputs used
as assert targets: C_T ~ 0.0046331, theta0 (B = 1) ~ 0.132839 rad,
theta0 (B = 0.97) ~ 0.140874 rad, C_Q ~ 3.4299e-4, Q ~ 7985.97 N m,
P ~ 351382.76 W, FM ~ 0.650140. The cross-leaf identity at B = 1 ties
the shaft power and FM to the momentum-theory model when one is
importable, with the plain momentum formulas as the fallback.
"""

import importlib.util
import inspect
import math
import os
import sys
import unittest

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPTS)
import rotorcraft_blade_element_hover_performance_logic as logic  # noqa: E402

# Reference rotor (spec worked example).
MASS = 2200.0
RADIUS = 5.0
RHO = 1.225
SIGMA = 0.08
CD0 = 0.012
VTIP = 220.0
A_LIFT = 5.73

THRUST = MASS * logic.G
AREA = math.pi * RADIUS ** 2
CT_WORKED = THRUST / (RHO * AREA * VTIP ** 2)          # about 0.0046331
LAMBDA_WORKED = logic.inflow_ratio_from_ct(CT_WORKED)  # about 0.0481306
CQ_WORKED = logic.torque_coefficient(CT_WORKED, LAMBDA_WORKED, SIGMA, CD0)
Q_WORKED = logic.rotor_torque(CQ_WORKED, RHO, AREA, VTIP, RADIUS)
P_WORKED = logic.rotor_power_from_torque(CQ_WORKED, RHO, AREA, VTIP,
                                         RADIUS)
FM_WORKED = logic.figure_of_merit_from_coefficients(CT_WORKED, CQ_WORKED)
THETA0_WORKED = logic.collective_for_thrust_coefficient(
    CT_WORKED, SIGMA, A_LIFT, 1.0)
THETA0_B097 = logic.collective_for_thrust_coefficient(
    CT_WORKED, SIGMA, A_LIFT, 0.97)

# Momentum-theory reference model (hover leaf): P_ideal = T * v_i with
# v_i = sqrt(T / (2 * rho * A)), P_profile = (1/8) * rho * sigma * Cd0 *
# A * Vtip^3. Imported from the sibling leaf when present, else computed
# inline with the identical formulas.
_MOM_SCRIPTS = os.path.join(
    _SCRIPTS, "..", "..", "..", "rotorcraft-hover-performance", "scripts")
_MOM_PATH = os.path.normpath(os.path.join(
    _MOM_SCRIPTS, "rotorcraft_hover_performance_logic.py"))


def _momentum_ideal_profile():
    """Return (P_ideal, P_profile) from the momentum hover model."""
    if os.path.exists(_MOM_PATH):
        spec = importlib.util.spec_from_file_location(
            "rotorcraft_hover_performance_logic", _MOM_PATH)
        if spec is not None and spec.loader is not None:
            mom = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mom)
            v_i = mom.induced_velocity(THRUST, AREA, RHO)
            return mom.ideal_power(THRUST, v_i), mom.profile_power(
                RHO, AREA, SIGMA, CD0, VTIP)
    v_i = math.sqrt(THRUST / (2.0 * RHO * AREA))
    return (THRUST * v_i,
            (1.0 / 8.0) * RHO * SIGMA * CD0 * AREA * VTIP ** 3)


P_IDEAL_MOM, P_PROFILE_MOM = _momentum_ideal_profile()
P_MOM_TOTAL = P_IDEAL_MOM + P_PROFILE_MOM
FM_MOM = P_IDEAL_MOM / P_MOM_TOTAL


class TestWorkedExampleMagnitudes(unittest.TestCase):
    """Spec worked-example magnitudes from real module outputs."""

    def test_ct_and_inflow_magnitudes(self):
        self.assertAlmostEqual(CT_WORKED, 0.0046331, delta=0.0005)
        self.assertTrue(0.0042 < CT_WORKED < 0.0051)
        self.assertAlmostEqual(LAMBDA_WORKED, 0.0481306, delta=0.0008)
        self.assertTrue(0.046 < LAMBDA_WORKED < 0.050)

    def test_collective_required_b1(self):
        self.assertAlmostEqual(THETA0_WORKED, 0.1328386, delta=0.004)
        self.assertAlmostEqual(math.degrees(THETA0_WORKED), 7.61,
                               delta=0.25)
        self.assertTrue(0.125 < THETA0_WORKED < 0.140)

    def test_collective_b097_and_tip_loss_effect(self):
        self.assertAlmostEqual(THETA0_B097, 0.1408739, delta=0.004)
        self.assertAlmostEqual(math.degrees(THETA0_B097), 8.07,
                               delta=0.25)
        self.assertTrue(0.134 < THETA0_B097 < 0.148)
        self.assertAlmostEqual(THETA0_B097 / THETA0_WORKED, 1.0605,
                               delta=0.01)
        self.assertGreater(THETA0_B097, THETA0_WORKED)

    def test_torque_split_magnitudes(self):
        induced = LAMBDA_WORKED * CT_WORKED
        self.assertAlmostEqual(induced, 2.2299e-4, delta=0.5e-5)
        self.assertAlmostEqual(SIGMA * CD0 / 8.0, 1.2e-4, delta=1e-9)
        self.assertAlmostEqual(CQ_WORKED, 3.4299e-4, delta=0.5e-5)

    def test_torque_and_power_magnitudes(self):
        self.assertAlmostEqual(Q_WORKED, 7986.0, delta=220.0)
        self.assertTrue(7750.0 < Q_WORKED < 8250.0)
        self.assertAlmostEqual(P_WORKED, 351383.0, delta=9000.0)
        self.assertTrue(344000.0 < P_WORKED < 359000.0)

    def test_figure_of_merit_bounds_and_ideal_limit(self):
        self.assertAlmostEqual(FM_WORKED, 0.65014, delta=0.01)
        self.assertTrue(0.63 < FM_WORKED < 0.67)
        self.assertTrue(0.0 < FM_WORKED < 1.0)
        ideal_cq = CT_WORKED ** 1.5 / math.sqrt(2.0)
        fm_ideal = logic.figure_of_merit_from_coefficients(CT_WORKED,
                                                           ideal_cq)
        self.assertAlmostEqual(fm_ideal, 1.0, delta=1e-12)
        self.assertLessEqual(fm_ideal, 1.0)

    def test_momentum_split_magnitudes(self):
        self.assertAlmostEqual(P_IDEAL_MOM, 228448.0, delta=6000.0)
        self.assertAlmostEqual(P_PROFILE_MOM, 122935.0, delta=4000.0)
        self.assertAlmostEqual(P_MOM_TOTAL, 351383.0, delta=9000.0)


class TestSpecFormulas(unittest.TestCase):
    """Closed-form checks computed independently of the module."""

    def test_thrust_coefficient_formula(self):
        expected = (SIGMA * A_LIFT / 2.0) * (
            THETA0_WORKED * 1.0 ** 3 / 3.0
            - LAMBDA_WORKED * 1.0 ** 2 / 2.0)
        got = logic.thrust_coefficient(THETA0_WORKED, SIGMA, A_LIFT,
                                       LAMBDA_WORKED, 1.0)
        self.assertAlmostEqual(got, expected, delta=1e-12 * expected)

    def test_inflow_closure_hand_compute(self):
        self.assertAlmostEqual(LAMBDA_WORKED, math.sqrt(CT_WORKED / 2.0),
                               delta=1e-12)

    def test_collective_recovery_formula(self):
        lam = math.sqrt(CT_WORKED / 2.0)
        expected = 3.0 * (2.0 * CT_WORKED / (SIGMA * A_LIFT) + lam / 2.0)
        self.assertAlmostEqual(THETA0_WORKED, expected, delta=1e-12)

    def test_collective_round_trip_b1(self):
        back = logic.thrust_coefficient(THETA0_WORKED, SIGMA, A_LIFT,
                                        LAMBDA_WORKED, 1.0)
        self.assertAlmostEqual(back, CT_WORKED, delta=1e-9)

    def test_collective_round_trip_with_tip_loss(self):
        lam = logic.inflow_ratio_from_ct(CT_WORKED)
        back = logic.thrust_coefficient(THETA0_B097, SIGMA, A_LIFT, lam,
                                        0.97)
        self.assertAlmostEqual(back, CT_WORKED, delta=1e-9)

    def test_torque_split_identity(self):
        induced = LAMBDA_WORKED * CT_WORKED
        profile = SIGMA * CD0 / 8.0
        self.assertAlmostEqual(induced + profile, CQ_WORKED, delta=1e-12)
        self.assertEqual(profile, SIGMA * CD0 / 8.0)

    def test_power_scaling_identities(self):
        omega = VTIP / RADIUS
        self.assertAlmostEqual(P_WORKED, Q_WORKED * omega, delta=1e-6)
        p2 = logic.rotor_power_from_torque(CQ_WORKED, RHO, AREA, 230.0,
                                           RADIUS)
        self.assertAlmostEqual(p2 / P_WORKED, (230.0 / VTIP) ** 3,
                               delta=1e-9)

    def test_cross_leaf_identities(self):
        self.assertLess(abs(P_WORKED - P_MOM_TOTAL) / P_MOM_TOTAL, 1e-6)
        self.assertLess(abs(FM_WORKED - FM_MOM) / FM_MOM, 1e-9)


class TestSummaryAndPolar(unittest.TestCase):
    """Convenience chains: dict keys, contents, fixed-point closure."""

    SUMMARY_KEYS = {
        "thrust_coefficient", "inflow_ratio", "torque_coefficient_induced",
        "torque_coefficient_profile", "torque_coefficient_total",
        "rotor_torque_Nm", "rotor_power_W", "figure_of_merit",
    }

    def _summary(self, tip_loss=1.0, collective=None):
        if collective is None:
            collective = THETA0_WORKED if tip_loss == 1.0 else THETA0_B097
        return logic.hover_blade_element_summary(
            THRUST, RADIUS, RHO, SIGMA, A_LIFT, CD0, VTIP, tip_loss,
            collective)

    def test_summary_dict_keys_exact(self):
        self.assertEqual(set(self._summary().keys()), self.SUMMARY_KEYS)

    def test_summary_values_match_primitives(self):
        out = self._summary()
        self.assertAlmostEqual(out["thrust_coefficient"], CT_WORKED,
                               delta=1e-12)
        self.assertAlmostEqual(out["inflow_ratio"], LAMBDA_WORKED,
                               delta=1e-12)
        self.assertAlmostEqual(out["rotor_torque_Nm"], Q_WORKED,
                               delta=1e-6)
        self.assertAlmostEqual(out["rotor_power_W"], P_WORKED, delta=1e-6)
        self.assertAlmostEqual(out["figure_of_merit"], FM_WORKED,
                               delta=1e-12)
        self.assertAlmostEqual(
            out["torque_coefficient_induced"]
            + out["torque_coefficient_profile"],
            out["torque_coefficient_total"], delta=1e-12)

    def test_summary_tip_loss_coherent_and_rejects_mismatch(self):
        out = self._summary(tip_loss=0.97)
        self.assertAlmostEqual(out["thrust_coefficient"], CT_WORKED,
                               delta=1e-9)
        with self.assertRaises(ValueError):
            self._summary(collective=THETA0_WORKED + 0.02)

    def test_polar_dict_keys_and_count(self):
        cols = [0.100, THETA0_WORKED, 0.160]
        pol = logic.collective_pitch_polar(cols, RADIUS, RHO, SIGMA,
                                           A_LIFT, CD0, VTIP, 1.0)
        self.assertEqual(len(pol), 3)
        expected = self.SUMMARY_KEYS | {"collective_rad"}
        for entry in pol:
            self.assertEqual(set(entry.keys()), expected)

    def test_polar_fixed_point_and_monotonicity(self):
        cols = [0.100, THETA0_WORKED, 0.140, 0.160]
        pol = logic.collective_pitch_polar(cols, RADIUS, RHO, SIGMA,
                                           A_LIFT, CD0, VTIP, 1.0)
        self.assertAlmostEqual(pol[1]["thrust_coefficient"], CT_WORKED,
                               delta=1e-9)
        self.assertAlmostEqual(pol[1]["inflow_ratio"], LAMBDA_WORKED,
                               delta=1e-9)
        cts = [e["thrust_coefficient"] for e in pol]
        pows = [e["rotor_power_W"] for e in pol]
        self.assertEqual(cts, sorted(cts))
        self.assertEqual(pows, sorted(pows))

    def test_polar_fm_in_unit_interval(self):
        pol = logic.collective_pitch_polar([0.100, 0.140], RADIUS, RHO,
                                           SIGMA, A_LIFT, CD0, VTIP, 1.0)
        for entry in pol:
            self.assertTrue(0.0 < entry["figure_of_merit"] < 1.0)

    def test_determinism_and_no_external_imports(self):
        args = (THRUST, RADIUS, RHO, SIGMA, A_LIFT, CD0, VTIP, 1.0,
                THETA0_WORKED)
        self.assertEqual(logic.hover_blade_element_summary(*args),
                         logic.hover_blade_element_summary(*args))
        cols = [0.100, 0.120, 0.140]
        pargs = (cols, RADIUS, RHO, SIGMA, A_LIFT, CD0, VTIP, 1.0)
        self.assertEqual(logic.collective_pitch_polar(*pargs),
                         logic.collective_pitch_polar(*pargs))
        source = inspect.getsource(logic)
        for banned in ("import random", "import numpy", "import scipy",
                       "from random", "from numpy", "from scipy"):
            self.assertNotIn(banned, source)


class TestValueErrorRejection(unittest.TestCase):
    """Every non-physical input in the spec validation list."""

    def test_thrust_coefficient_non_physical(self):
        for args in ((-0.1, SIGMA, A_LIFT, 0.05, 1.0),
                     (0.13, 0.0, A_LIFT, 0.05, 1.0),
                     (0.13, SIGMA, 0.0, 0.05, 1.0),
                     (0.13, SIGMA, A_LIFT, -0.05, 1.0)):
            with self.assertRaises(ValueError):
                logic.thrust_coefficient(*args)

    def test_tip_loss_out_of_range(self):
        for bad in (0.0, -0.1, 1.0001, 2.0):
            with self.assertRaises(ValueError):
                logic.thrust_coefficient(0.13, SIGMA, A_LIFT, 0.05, bad)
            with self.assertRaises(ValueError):
                logic.collective_for_thrust_coefficient(0.005, SIGMA,
                                                        A_LIFT, bad)

    def test_inflow_closure_negative_ct(self):
        with self.assertRaises(ValueError):
            logic.inflow_ratio_from_ct(-0.001)

    def test_collective_for_ct_non_physical(self):
        with self.assertRaises(ValueError):
            logic.collective_for_thrust_coefficient(-0.001, SIGMA,
                                                    A_LIFT, 1.0)
        with self.assertRaises(ValueError):
            logic.collective_for_thrust_coefficient(0.005, 0.0, A_LIFT,
                                                    1.0)
        with self.assertRaises(ValueError):
            logic.collective_for_thrust_coefficient(0.005, SIGMA, 0.0,
                                                    1.0)

    def test_torque_coefficient_non_physical(self):
        for args in ((-0.001, 0.05, SIGMA, CD0),
                     (0.005, -0.05, SIGMA, CD0),
                     (0.005, 0.05, 0.0, CD0),
                     (0.005, 0.05, SIGMA, 0.0)):
            with self.assertRaises(ValueError):
                logic.torque_coefficient(*args)

    def test_rotor_torque_non_positive(self):
        for kwargs in ({"c_q": 0.0}, {"rho": 0.0}, {"area": -1.0},
                       {"tip_speed": 0.0}, {"radius": 0.0}):
            args = dict(c_q=3.4e-4, rho=RHO, area=AREA, tip_speed=VTIP,
                        radius=RADIUS)
            args.update(kwargs)
            with self.assertRaises(ValueError):
                logic.rotor_torque(**args)

    def test_rotor_power_non_positive(self):
        for kwargs in ({"c_q": 0.0}, {"rho": -1.0}, {"area": 0.0},
                       {"tip_speed": 0.0}, {"radius": 0.0}):
            args = dict(c_q=3.4e-4, rho=RHO, area=AREA, tip_speed=VTIP,
                        radius=RADIUS)
            args.update(kwargs)
            with self.assertRaises(ValueError):
                logic.rotor_power_from_torque(**args)

    def test_figure_of_merit_non_physical(self):
        for args in ((0.0, 3.4e-4), (-0.005, 3.4e-4), (0.005, 0.0),
                     (0.005, -1e-4)):
            with self.assertRaises(ValueError):
                logic.figure_of_merit_from_coefficients(*args)

    def test_summary_non_physical(self):
        good = dict(thrust_N=THRUST, radius_m=RADIUS, rho=RHO,
                    solidity=SIGMA, lift_slope=A_LIFT,
                    drag_coefficient=CD0, tip_speed=VTIP, tip_loss=1.0,
                    collective_rad=THETA0_WORKED)
        for key in ("thrust_N", "radius_m", "rho", "solidity",
                    "lift_slope", "drag_coefficient", "tip_speed"):
            args = dict(good)
            args[key] = 0.0
            with self.assertRaises(ValueError):
                logic.hover_blade_element_summary(**args)
        for bad_tip in (0.0, 1.5):
            args = dict(good)
            args["tip_loss"] = bad_tip
            with self.assertRaises(ValueError):
                logic.hover_blade_element_summary(**args)

    def test_polar_value_error_propagation(self):
        with self.assertRaises(ValueError):
            logic.collective_pitch_polar([-0.01, 0.13], RADIUS, RHO,
                                         SIGMA, A_LIFT, CD0, VTIP, 1.0)
        with self.assertRaises(ValueError):
            logic.collective_pitch_polar([0.13], RADIUS, RHO, 0.0,
                                         A_LIFT, CD0, VTIP, 1.0)


class TestModuleConstants(unittest.TestCase):
    """Module constants match the spec exactly."""

    def test_module_constants(self):
        self.assertEqual(logic.RHO_SL, 1.225)
        self.assertEqual(logic.G, 9.80665)
        self.assertEqual(logic.A_LIFT_DEFAULT, 5.73)
        self.assertAlmostEqual(logic.PI, math.pi, delta=1e-15)

    def test_thrust_equals_weight(self):
        self.assertAlmostEqual(THRUST, 2200.0 * 9.80665, delta=1e-9)
        self.assertAlmostEqual(THRUST, 21574.63, delta=0.01)


if __name__ == "__main__":
    unittest.main()
