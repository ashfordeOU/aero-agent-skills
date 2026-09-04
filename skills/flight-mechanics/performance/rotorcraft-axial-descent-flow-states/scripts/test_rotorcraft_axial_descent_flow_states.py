"""Contract test for rotorcraft_axial_descent_flow_states_logic.

Offline, deterministic, stdlib unittest. Run from the repo root:

    python3 skills/flight-mechanics/performance/\
        rotorcraft-axial-descent-flow-states/scripts/\
        test_rotorcraft_axial_descent_flow_states.py

The reference rotor (shared with the hover and blade-element siblings):
R = 5.0 m, m = 2200 kg (T = m * G), rho = 1.225 kg/m^3,
A = pi R^2, v_h about 10.5887 m/s, P_profile = 122935 W, k = 1.15,
Vtip = 220 m/s (Omega = 44 rad/s). Real module outputs used as assert
targets: v_h 10.588726, band (0, 21.1775), v_i(2 v_h) = v_h exactly,
P(2 v_h) -139780.0 W, v_i(25) 5.85704 (0.553 v_h), P(25) -352017.6 W,
v_i(30) 4.37555 (0.413 v_h), P(30) -512828.7 W, Q(30, Omega 44)
-11655.2 N m, P(40) -794246.6 W, c = P_profile / (k T) 4.95489 < v_h
with momentum_root_Vd None (the formal crossing at about 27.6 m/s
would need v_i = v_h^2 / c about 22.6 m/s above v_h, so it never lies
on the physical windmill-brake branch). All magnitudes fall inside the
spec bounds (v_h about 10.59, P values about -139780 / -352019 /
-512829 / -794247 W, Q about -11655 N m, c about 4.955).
"""

import math
import os
import sys
import unittest

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPTS)
import rotorcraft_axial_descent_flow_states_logic as logic  # noqa: E402

# Reference rotor (spec worked example).
MASS = 2200.0
RADIUS = 5.0
RHO = 1.225
PROFILE_POWER = 122935.0
K = logic.K_INDUCED_DEFAULT
VTIP = 220.0

THRUST = MASS * logic.G
AREA = math.pi * RADIUS ** 2
VH = math.sqrt(THRUST / (2.0 * RHO * AREA))
OMEGA = VTIP / RADIUS


def _induced(rate):
    """v_i for the worked rotor at a windmill-brake descent rate."""
    return logic.windmill_brake_induced_velocity(rate, VH)


def _power(rate):
    """Signed power for the worked rotor at a windmill-brake rate."""
    return logic.rotor_descent_power(THRUST, rate, _induced(rate),
                                     PROFILE_POWER, K)


class TestAxialFlowState(unittest.TestCase):
    """Flow-state categorization at and around the 2 v_h boundary."""

    def test_hover_at_zero_descent_rate(self):
        self.assertEqual(logic.axial_flow_state(0.0, VH), "hover")

    def test_vortex_ring_band_interior(self):
        self.assertEqual(logic.axial_flow_state(VH, VH), "vortex-ring-band")
        self.assertEqual(logic.axial_flow_state(0.5 * VH, VH),
                         "vortex-ring-band")

    def test_just_below_2vh_is_vortex_ring_band(self):
        self.assertEqual(logic.axial_flow_state(2.0 * VH * (1.0 - 1e-9), VH),
                         "vortex-ring-band")

    def test_at_2vh_is_windmill_brake(self):
        self.assertEqual(logic.axial_flow_state(2.0 * VH, VH),
                         "windmill-brake")

    def test_above_2vh_is_windmill_brake(self):
        self.assertEqual(logic.axial_flow_state(3.0 * VH, VH),
                         "windmill-brake")
        self.assertEqual(logic.axial_flow_state(25.0, VH), "windmill-brake")

    def test_rejects_climb_rate(self):
        with self.assertRaisesRegex(ValueError, "climb is not a descent"):
            logic.axial_flow_state(-1.0, VH)

    def test_rejects_nonpositive_vh(self):
        with self.assertRaises(ValueError):
            logic.axial_flow_state(10.0, 0.0)
        with self.assertRaises(ValueError):
            logic.axial_flow_state(10.0, -2.0)


class TestVortexRingBandLimits(unittest.TestCase):
    """Band limits from the hover induced velocity."""

    def test_band_limits_worked_rotor(self):
        lo, hi = logic.vortex_ring_band_limits(VH)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 2.0 * VH, places=9)
        # Spec magnitude bound: band (0, 21.18) m/s.
        self.assertAlmostEqual(hi, 21.18, delta=0.01)
        self.assertAlmostEqual(VH, 10.5887, delta=5e-4)

    def test_rejects_nonpositive_vh(self):
        with self.assertRaises(ValueError):
            logic.vortex_ring_band_limits(0.0)
        with self.assertRaises(ValueError):
            logic.vortex_ring_band_limits(-3.0)


class TestWindmillBrakeInducedVelocity(unittest.TestCase):
    """Physical-branch induced velocity in the windmill-brake state."""

    def test_boundary_identity_v_i_at_2vh_equals_vh(self):
        self.assertAlmostEqual(_induced(2.0 * VH), VH, places=9)

    def test_worked_vd25_induced_velocity(self):
        vi = _induced(25.0)
        self.assertAlmostEqual(vi, 5.85704, delta=5e-4)
        # Spec magnitude: about 5.857 m/s, 0.553 v_h.
        self.assertAlmostEqual(vi, 5.857, delta=0.01)
        self.assertAlmostEqual(vi / VH, 0.553, delta=0.005)

    def test_worked_vd30_induced_velocity(self):
        vi = _induced(30.0)
        self.assertAlmostEqual(vi, 4.37555, delta=5e-4)
        # Spec magnitude: about 4.376 m/s, 0.413 v_h.
        self.assertAlmostEqual(vi, 4.376, delta=0.01)
        self.assertAlmostEqual(vi / VH, 0.413, delta=0.005)

    def test_asymptote_at_5vh(self):
        # v_i / v_h about 0.2087 at w = 5, approaching 1 / w as Vd grows.
        vi = _induced(5.0 * VH)
        self.assertAlmostEqual(vi / VH, 0.2087, delta=1e-3)

    def test_momentum_quadratic_identity(self):
        # v_i is a root of v_i^2 - Vd v_i + v_h^2 = 0, so
        # v_i * (Vd - v_i) == v_h^2 exactly on the physical branch.
        for rate in (2.0 * VH, 25.0, 30.0, 40.0, 8.0 * VH):
            vi = _induced(rate)
            self.assertAlmostEqual(vi * (rate - vi), VH * VH, places=6)

    def test_rejects_below_2vh_and_climb(self):
        with self.assertRaisesRegex(ValueError, "vortex-ring band"):
            logic.windmill_brake_induced_velocity(1.9 * VH, VH)
        with self.assertRaisesRegex(ValueError, "climb is not a descent"):
            logic.windmill_brake_induced_velocity(-5.0, VH)
        with self.assertRaises(ValueError):
            logic.windmill_brake_induced_velocity(10.0, 0.0)


class TestRotorDescentPower(unittest.TestCase):
    """Signed shaft power P = k T (-Vd + v_i) + P_profile."""

    def test_power_at_2vh_magnitude(self):
        p = _power(2.0 * VH)
        self.assertAlmostEqual(p, -139780.0, delta=1.0)
        # Spec magnitude bound: about -139780 W.
        self.assertAlmostEqual(p, -139780.0, delta=10.0)

    def test_power_worked_vd25(self):
        p = _power(25.0)
        self.assertAlmostEqual(p, -352017.6, delta=1.0)
        self.assertAlmostEqual(p, -352019.0, delta=10.0)  # spec magnitude

    def test_power_worked_vd30(self):
        p = _power(30.0)
        self.assertAlmostEqual(p, -512828.7, delta=1.0)
        self.assertAlmostEqual(p, -512829.0, delta=10.0)  # spec magnitude

    def test_power_worked_vd40(self):
        p = _power(40.0)
        self.assertAlmostEqual(p, -794246.6, delta=1.0)
        self.assertAlmostEqual(p, -794247.0, delta=10.0)  # spec magnitude

    def test_power_negative_across_windmill_band(self):
        # Profile power never overcomes the descent term for this rotor.
        for rate in (2.0 * VH, 22.0, 25.0, 30.0, 40.0, 60.0):
            self.assertLess(_power(rate), 0.0)

    def test_rejects_nonphysical_inputs(self):
        with self.assertRaises(ValueError):
            logic.rotor_descent_power(0.0, 25.0, 5.0, PROFILE_POWER, K)
        with self.assertRaises(ValueError):
            logic.rotor_descent_power(-100.0, 25.0, 5.0, PROFILE_POWER, K)
        with self.assertRaises(ValueError):
            logic.rotor_descent_power(THRUST, -25.0, 5.0, PROFILE_POWER, K)
        with self.assertRaises(ValueError):
            logic.rotor_descent_power(THRUST, 25.0, -1.0, PROFILE_POWER, K)
        with self.assertRaises(ValueError):
            logic.rotor_descent_power(THRUST, 25.0, 5.0, -1.0, K)
        with self.assertRaises(ValueError):
            logic.rotor_descent_power(THRUST, 25.0, 5.0, PROFILE_POWER, 0.0)


class TestRotorDescentTorque(unittest.TestCase):
    """Signed torque Q = P / Omega."""

    def test_torque_worked_vd30(self):
        q = logic.rotor_descent_torque(_power(30.0), OMEGA)
        self.assertAlmostEqual(q, -11655.2, delta=1.0)
        # Spec magnitude bound: about -11655 N m (Omega = Vtip / R = 44).
        self.assertAlmostEqual(q, -11655.0, delta=10.0)

    def test_torque_equals_power_over_omega(self):
        for rate in (2.0 * VH, 25.0, 40.0):
            p = _power(rate)
            self.assertAlmostEqual(
                logic.rotor_descent_torque(p, OMEGA), p / OMEGA, places=12)

    def test_rejects_nonpositive_omega(self):
        with self.assertRaises(ValueError):
            logic.rotor_descent_torque(-100.0, 0.0)
        with self.assertRaises(ValueError):
            logic.rotor_descent_torque(-100.0, -44.0)


class TestTorqueReversalCondition(unittest.TestCase):
    """Zero-shaft-power reachability, c = P_profile / (k T) versus v_h."""

    def test_worked_c_below_vh_momentum_unreachable(self):
        info = logic.torque_reversal_condition(PROFILE_POWER, THRUST, K, VH)
        self.assertAlmostEqual(info["c"], 4.95489, delta=1e-3)
        # Spec magnitude: c about 4.955 m/s.
        self.assertAlmostEqual(info["c"], 4.955, delta=0.01)
        self.assertTrue(info["c_less_than_vh"])
        self.assertIsNone(info["momentum_root_Vd"])
        self.assertIn("momentum-unreachable", info["verdict"])
        self.assertIn("autorotative equilibrium", info["verdict"])
        # The formal crossing would sit at about 27.6 m/s only on the
        # non-physical branch (v_i = v_h^2 / c about 22.6 m/s > v_h), so
        # no root is reported and 27.6 m/s is never a momentum root.
        self.assertGreater(VH * VH / info["c"], VH)

    def test_synthetic_reachable_rotor(self):
        # Large profile power, c = 2 v_h: root reachable at
        # Vd = c + v_h^2 / c, which is >= 2 v_h by AM-GM.
        big_profile = K * THRUST * (2.0 * VH)
        info = logic.torque_reversal_condition(big_profile, THRUST, K, VH)
        self.assertAlmostEqual(info["c"], 2.0 * VH, places=9)
        self.assertFalse(info["c_less_than_vh"])
        root = info["momentum_root_Vd"]
        self.assertIsNotNone(root)
        self.assertAlmostEqual(root, 2.0 * VH + VH / 2.0, places=6)
        self.assertGreaterEqual(root, 2.0 * VH)
        self.assertIn("momentum-reachable", info["verdict"])

    def test_boundary_c_equal_vh_root_at_2vh(self):
        profile = K * THRUST * VH  # c = v_h exactly
        info = logic.torque_reversal_condition(profile, THRUST, K, VH)
        self.assertFalse(info["c_less_than_vh"])
        self.assertAlmostEqual(info["momentum_root_Vd"], 2.0 * VH, places=6)

    def test_rejects_nonphysical_inputs(self):
        with self.assertRaises(ValueError):
            logic.torque_reversal_condition(-1.0, THRUST, K, VH)
        with self.assertRaises(ValueError):
            logic.torque_reversal_condition(PROFILE_POWER, 0.0, K, VH)
        with self.assertRaises(ValueError):
            logic.torque_reversal_condition(PROFILE_POWER, THRUST, 0.0, VH)
        with self.assertRaises(ValueError):
            logic.torque_reversal_condition(PROFILE_POWER, THRUST, K, 0.0)


class TestDescentSummary(unittest.TestCase):
    """Convenience dict bundle for one operating point."""

    KEYS = {"flow_state", "v_h", "band_limits", "induced_velocity",
            "power_W", "torque_Nm", "momentum_root_reachable"}

    def test_worked_windmill_bundle(self):
        s = logic.descent_summary(THRUST, RADIUS, PROFILE_POWER, 30.0,
                                  rotor_speed_rad_s=OMEGA)
        self.assertEqual(set(s.keys()), self.KEYS)
        self.assertEqual(s["flow_state"], "windmill-brake")
        self.assertAlmostEqual(s["v_h"], VH, places=9)
        self.assertEqual(s["band_limits"], (0.0, 2.0 * VH))
        self.assertAlmostEqual(s["induced_velocity"], 4.37555, delta=5e-4)
        self.assertAlmostEqual(s["power_W"], -512828.7, delta=1.0)
        self.assertAlmostEqual(s["torque_Nm"], -11655.2, delta=1.0)
        self.assertFalse(s["momentum_root_reachable"])

    def test_inside_band_fields_none(self):
        s = logic.descent_summary(THRUST, RADIUS, PROFILE_POWER, 15.0,
                                  rotor_speed_rad_s=OMEGA)
        self.assertEqual(s["flow_state"], "vortex-ring-band")
        self.assertIsNone(s["induced_velocity"])
        self.assertIsNone(s["power_W"])
        self.assertIsNone(s["torque_Nm"])
        self.assertFalse(s["momentum_root_reachable"])

    def test_hover_state(self):
        s = logic.descent_summary(THRUST, RADIUS, PROFILE_POWER, 0.0)
        self.assertEqual(s["flow_state"], "hover")
        self.assertIsNone(s["induced_velocity"])
        self.assertIsNone(s["power_W"])
        self.assertIsNone(s["torque_Nm"])

    def test_torque_none_without_omega(self):
        s = logic.descent_summary(THRUST, RADIUS, PROFILE_POWER, 30.0)
        self.assertEqual(s["flow_state"], "windmill-brake")
        self.assertIsNotNone(s["power_W"])
        self.assertIsNone(s["torque_Nm"])

    def test_rejects_nonphysical_inputs(self):
        with self.assertRaises(ValueError):
            logic.descent_summary(0.0, RADIUS, PROFILE_POWER, 30.0)
        with self.assertRaises(ValueError):
            logic.descent_summary(THRUST, 0.0, PROFILE_POWER, 30.0)
        with self.assertRaises(ValueError):
            logic.descent_summary(THRUST, RADIUS, PROFILE_POWER, -2.0)
        with self.assertRaises(ValueError):
            logic.descent_summary(THRUST, RADIUS, PROFILE_POWER, 30.0,
                                  rho=0.0)
        with self.assertRaises(ValueError):
            logic.descent_summary(THRUST, RADIUS, PROFILE_POWER, 30.0,
                                  rotor_speed_rad_s=0.0)


class TestDeterminism(unittest.TestCase):
    """Identical floats run to run (no RNG anywhere)."""

    def test_repeat_calls_identical(self):
        first = [
            logic.axial_flow_state(25.0, VH),
            logic.windmill_brake_induced_velocity(25.0, VH),
            logic.rotor_descent_power(THRUST, 25.0, _induced(25.0),
                                      PROFILE_POWER, K),
            logic.rotor_descent_torque(_power(30.0), OMEGA),
            logic.torque_reversal_condition(PROFILE_POWER, THRUST, K, VH),
            logic.descent_summary(THRUST, RADIUS, PROFILE_POWER, 30.0,
                                  rotor_speed_rad_s=OMEGA),
        ]
        second = [
            logic.axial_flow_state(25.0, VH),
            logic.windmill_brake_induced_velocity(25.0, VH),
            logic.rotor_descent_power(THRUST, 25.0, _induced(25.0),
                                      PROFILE_POWER, K),
            logic.rotor_descent_torque(_power(30.0), OMEGA),
            logic.torque_reversal_condition(PROFILE_POWER, THRUST, K, VH),
            logic.descent_summary(THRUST, RADIUS, PROFILE_POWER, 30.0,
                                  rotor_speed_rad_s=OMEGA),
        ]
        for a, b in zip(first, second):
            self.assertEqual(a, b)
        # Pinned module constants.
        self.assertAlmostEqual(logic.RHO_SL, 1.225, places=12)
        self.assertAlmostEqual(logic.G, 9.80665, places=12)
        self.assertAlmostEqual(logic.K_INDUCED_DEFAULT, 1.15, places=12)


if __name__ == "__main__":
    unittest.main()
