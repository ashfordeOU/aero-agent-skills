#!/usr/bin/env python3
"""Contract test: rotorcraft turn performance (banked level turn).

Exercises scripts/rotorcraft_turn_performance_logic.py (stdlib
unittest, offline, deterministic). Contract per the wave-41 spec: the
momentum-theory turning-flight-inflow of a banked level turn at load
factors above one (the rotor thrust rises to n times the weight and the
turning induced velocity follows the Glauert-style disk momentum solve
at that thrust), the banked-turn-power breakdown into induced, profile
and parasite terms, the sustained-load-factor an available power
supports at the turn speed with its power-limited-bank-angle, and the
turn rate and turn radius of the sustained maneuver.

The test methods name the SKILL.md workflow steps they exercise.
Workflow step 2 (raise the thrust to the load factor with
thrust_for_turn) is exercised by the test_workflow_step2_* methods;
Workflow step 3 (solve the turning-flight-inflow with
generalized_induced_velocity) by the test_workflow_step3_* methods;
Workflow step 4 (break down the banked-turn-power with turn_power,
induced_power, profile_power, parasite_power) by the
test_workflow_step4_* methods; Workflow step 5 (invert for the
power-sustained-load-factor with sustained_load_factor and
max_bank_from_power) by the test_workflow_step5_* methods; Workflow
step 6 (close the maneuver kinematics with bank_from_load_factor,
turn_rate, turn_radius) by the test_workflow_step6_* methods;
Workflow step 7 (run the contract test and confirm determinism) by the
test_workflow_step7_* methods.

Worked rotor (same as the hover and forward-flight leaves): R = 5.0 m
(A = 78.5398 m2), m = 2200 kg (W = 21574.63 N), rho = 1.225 kg/m3,
solidity 0.08, Cd0 0.012, tip speed 220 m/s, f = 2.2 m2, k = 1.15.
Real module outputs are the assert targets; spec magnitude bounds are
checked too.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rotorcraft_turn_performance_logic as rtp  # noqa: E402

# Worked rotor inputs (SI).
AREA = math.pi * 5.0 * 5.0     # 78.5398 m2
WEIGHT = 2200.0 * rtp.G0       # 21574.63 N
RHO = 1.225
SOLIDITY = 0.08
CD0 = 0.012
TIP_SPEED = 220.0
FLAT_PLATE = 2.2               # m2, equivalent flat-plate drag area
V60 = 60.0
V40 = 40.0
V50 = 50.0


def turn_power_at(load_factor, speed):
    """turn_power on the worked rotor at the given load factor and speed."""
    return rtp.turn_power(load_factor, WEIGHT, AREA, RHO, speed, SOLIDITY,
                          CD0, TIP_SPEED, FLAT_PLATE)


def sustained_at(available_power, speed):
    """sustained_load_factor on the worked rotor at the given power/speed."""
    return rtp.sustained_load_factor(available_power, WEIGHT, AREA, RHO,
                                     speed, SOLIDITY, CD0, TIP_SPEED,
                                     FLAT_PLATE)


class WorkflowStep2ThrustTests(unittest.TestCase):
    """Workflow step 2: thrust_for_turn raises the rotor thrust to n * W."""

    def test_workflow_step2_thrust_at_load_factor_two(self):
        """Workflow step 2: at n = 2 the turn thrust is 2 * W = 43149.26 N."""
        thrust = rtp.thrust_for_turn(2.0, WEIGHT)
        self.assertAlmostEqual(thrust, 43149.26, delta=1e-2)
        self.assertAlmostEqual(thrust, 2.0 * WEIGHT, delta=1e-9)

    def test_workflow_step2_thrust_at_load_factor_one(self):
        """Workflow step 2: at n = 1 the turn thrust equals the weight W."""
        self.assertAlmostEqual(rtp.thrust_for_turn(1.0, WEIGHT), WEIGHT,
                               delta=1e-9)

    def test_workflow_step2_thrust_valueerrors(self):
        """Workflow step 2: load factor below 1 and non-positive weight raise
        ValueError."""
        with self.assertRaises(ValueError):
            rtp.thrust_for_turn(0.99, WEIGHT)
        with self.assertRaises(ValueError):
            rtp.thrust_for_turn(2.0, 0.0)
        with self.assertRaises(ValueError):
            rtp.thrust_for_turn(2.0, -100.0)


class WorkflowStep3InflowTests(unittest.TestCase):
    """Workflow step 3: generalized_induced_velocity turning-flight-inflow."""

    def test_workflow_step3_level_flight_glauert_identity_n1_v60(self):
        """Workflow step 3: n = 1 at 60 m/s gives the level-flight Glauert
        inflow 1.86778 m/s (the forward-flight leaf identity)."""
        v_i = rtp.generalized_induced_velocity(1.0, WEIGHT, AREA, RHO, V60)
        self.assertAlmostEqual(v_i, 1.86778, delta=1e-4)

    def test_workflow_step3_turn_inflow_n2_v60(self):
        """Workflow step 3: the turning-flight-inflow at n = 2, 60 m/s is
        3.73017 m/s (spec bound 3.5 to 4.0), about twice the level value."""
        v_i = rtp.generalized_induced_velocity(2.0, WEIGHT, AREA, RHO, V60)
        self.assertAlmostEqual(v_i, 3.73017, delta=1e-4)
        self.assertTrue(3.5 <= v_i <= 4.0)

    def test_workflow_step3_turn_inflow_n15_v40(self):
        """Workflow step 3: the turning-flight-inflow at n = 1.5, 40 m/s is
        4.18175 m/s (spec bound 3.9 to 4.5)."""
        v_i = rtp.generalized_induced_velocity(1.5, WEIGHT, AREA, RHO, V40)
        self.assertAlmostEqual(v_i, 4.18175, delta=1e-4)
        self.assertTrue(3.9 <= v_i <= 4.5)

    def test_workflow_step3_turn_inflow_n3_v60(self):
        """Workflow step 3: the turning-flight-inflow at n = 3, 60 m/s is
        5.58195 m/s."""
        v_i = rtp.generalized_induced_velocity(3.0, WEIGHT, AREA, RHO, V60)
        self.assertAlmostEqual(v_i, 5.58195, delta=1e-4)

    def test_workflow_step3_speed_zero_hover_identities(self):
        """Workflow step 3: at speed zero the inflow returns v_h = 10.5887
        m/s at n = 1 and sqrt(2) * v_h = 14.9747 m/s at n = 2 (spec bound
        14.8 to 15.2)."""
        v_h = rtp.generalized_induced_velocity(1.0, WEIGHT, AREA, RHO, 0.0)
        v2 = rtp.generalized_induced_velocity(2.0, WEIGHT, AREA, RHO, 0.0)
        self.assertAlmostEqual(v_h, 10.5887, delta=1e-4)
        self.assertAlmostEqual(v_h, math.sqrt(WEIGHT / (2.0 * RHO * AREA)),
                               delta=1e-9)
        self.assertAlmostEqual(v2, 14.9747, delta=1e-4)
        self.assertTrue(14.8 <= v2 <= 15.2)
        self.assertAlmostEqual(v2, math.sqrt(2.0) * v_h, delta=1e-9)

    def test_workflow_step3_inflow_falls_as_speed_grows(self):
        """Workflow step 3: at fixed n = 2 the turning-flight-inflow is
        monotone decreasing in speed (0 m/s above 40 m/s above 60 m/s)."""
        v0 = rtp.generalized_induced_velocity(2.0, WEIGHT, AREA, RHO, 0.0)
        v40 = rtp.generalized_induced_velocity(2.0, WEIGHT, AREA, RHO, 40.0)
        v60 = rtp.generalized_induced_velocity(2.0, WEIGHT, AREA, RHO, 60.0)
        self.assertGreater(v0, v40)
        self.assertGreater(v40, v60)

    def test_workflow_step3_inflow_valueerrors(self):
        """Workflow step 3: load factor below 1, weight 0, area 0, rho 0 and
        negative speed each raise ValueError."""
        with self.assertRaises(ValueError):
            rtp.generalized_induced_velocity(0.99, WEIGHT, AREA, RHO, V60)
        with self.assertRaises(ValueError):
            rtp.generalized_induced_velocity(2.0, 0.0, AREA, RHO, V60)
        with self.assertRaises(ValueError):
            rtp.generalized_induced_velocity(2.0, WEIGHT, 0.0, RHO, V60)
        with self.assertRaises(ValueError):
            rtp.generalized_induced_velocity(2.0, WEIGHT, AREA, 0.0, V60)
        with self.assertRaises(ValueError):
            rtp.generalized_induced_velocity(2.0, WEIGHT, AREA, RHO, -1.0)


class WorkflowStep4PowerBreakdownTests(unittest.TestCase):
    """Workflow step 4: banked-turn-power breakdown into the power terms."""

    def test_workflow_step4_profile_power_anchor(self):
        """Workflow step 4: profile_power is 122935 W on the worked rotor
        (spec bound 115000 to 130000)."""
        p = rtp.profile_power(RHO, AREA, SOLIDITY, CD0, TIP_SPEED)
        self.assertAlmostEqual(p, 122935.0, delta=1e-1)
        self.assertTrue(115000.0 <= p <= 130000.0)

    def test_workflow_step4_parasite_power_anchor_v60(self):
        """Workflow step 4: parasite_power at 60 m/s is 291060 W (spec bound
        280000 to 305000)."""
        p = rtp.parasite_power(RHO, V60, FLAT_PLATE)
        self.assertAlmostEqual(p, 291060.0, delta=1e-1)
        self.assertTrue(280000.0 <= p <= 305000.0)

    def test_workflow_step4_induced_power_anchor_n2(self):
        """Workflow step 4: induced_power at n = 2, 60 m/s is
        k * n * W * v_i = 185097 W with the induced power factor k = 1.15."""
        v_i = rtp.generalized_induced_velocity(2.0, WEIGHT, AREA, RHO, V60)
        p = rtp.induced_power(2.0, WEIGHT, v_i)
        self.assertAlmostEqual(p, 185097.0, delta=1.0)
        self.assertAlmostEqual(p, rtp.K_DEFAULT * 2.0 * WEIGHT * v_i,
                               delta=1e-6)

    def test_workflow_step4_power_term_valueerrors(self):
        """Workflow step 4: profile, parasite and induced power reject every
        non-positive or negative input class with ValueError."""
        with self.assertRaises(ValueError):
            rtp.profile_power(0.0, AREA, SOLIDITY, CD0, TIP_SPEED)
        with self.assertRaises(ValueError):
            rtp.profile_power(RHO, AREA, 0.0, CD0, TIP_SPEED)
        with self.assertRaises(ValueError):
            rtp.profile_power(RHO, AREA, SOLIDITY, CD0, 0.0)
        with self.assertRaises(ValueError):
            rtp.parasite_power(0.0, V60, FLAT_PLATE)
        with self.assertRaises(ValueError):
            rtp.parasite_power(RHO, -1.0, FLAT_PLATE)
        with self.assertRaises(ValueError):
            rtp.parasite_power(RHO, V60, -1.0)
        with self.assertRaises(ValueError):
            rtp.induced_power(2.0, WEIGHT, 3.0, k=0.0)
        with self.assertRaises(ValueError):
            rtp.induced_power(0.99, WEIGHT, 3.0)
        with self.assertRaises(ValueError):
            rtp.induced_power(2.0, 0.0, 3.0)
        with self.assertRaises(ValueError):
            rtp.induced_power(2.0, WEIGHT, -1.0)

    def test_workflow_step4_turn_power_anchors(self):
        """Workflow step 4: turn_power at n = 2, 60 m/s gives induced
        velocity 3.73017 m/s, induced power 185097 W (bound 170000 to
        200000) and total power 599092 W (bound 570000 to 630000); the
        n = 1.5, 40 m/s state totals 364804 W."""
        result = turn_power_at(2.0, V60)
        self.assertAlmostEqual(result["induced_velocity"], 3.73017,
                               delta=1e-4)
        self.assertAlmostEqual(result["induced_power"], 185097.0, delta=1.0)
        self.assertTrue(170000.0 <= result["induced_power"] <= 200000.0)
        self.assertAlmostEqual(result["total_power"], 599092.0, delta=1.0)
        self.assertTrue(570000.0 <= result["total_power"] <= 630000.0)
        state15 = turn_power_at(1.5, V40)
        self.assertAlmostEqual(state15["induced_velocity"], 4.18175,
                               delta=1e-4)
        self.assertAlmostEqual(state15["induced_power"], 155629.0, delta=1.0)
        self.assertAlmostEqual(state15["total_power"], 364804.0, delta=1.0)

    def test_workflow_step4_turn_power_dict_keys_exact(self):
        """Workflow step 4: turn_power dict keys are exactly load_factor,
        thrust, induced_velocity, induced_power, profile_power,
        parasite_power, total_power, and the terms sum consistently."""
        result = turn_power_at(2.0, V60)
        self.assertEqual(list(result.keys()),
                         ["load_factor", "thrust", "induced_velocity",
                          "induced_power", "profile_power", "parasite_power",
                          "total_power"])
        self.assertEqual(result["load_factor"], 2.0)
        self.assertAlmostEqual(result["thrust"], 2.0 * WEIGHT, delta=1e-6)
        self.assertAlmostEqual(result["profile_power"],
                               rtp.profile_power(RHO, AREA, SOLIDITY, CD0,
                                                 TIP_SPEED),
                               delta=1e-6)
        self.assertAlmostEqual(result["parasite_power"],
                               rtp.parasite_power(RHO, V60, FLAT_PLATE),
                               delta=1e-6)
        self.assertAlmostEqual(result["total_power"],
                               result["induced_power"]
                               + result["profile_power"]
                               + result["parasite_power"],
                               delta=1e-6)

    def test_workflow_step4_n1_identity_level_flight_total(self):
        """Workflow step 4: at n = 1 and 60 m/s the total power is 460336 W,
        the level-flight total of the forward-flight leaf at the same speed
        (the shared fixed point and power conventions)."""
        result = turn_power_at(1.0, V60)
        self.assertAlmostEqual(result["total_power"], 460336.0, delta=1e-1)
        self.assertAlmostEqual(result["induced_velocity"], 1.86778,
                               delta=1e-4)

    def test_workflow_step4_total_power_monotone_in_load_factor(self):
        """Workflow step 4: the total turn power strictly increases with the
        load factor at fixed speed (n = 1 below n = 1.5 below n = 2 below
        n = 3)."""
        p1 = turn_power_at(1.0, V60)["total_power"]
        p15 = turn_power_at(1.5, V60)["total_power"]
        p2 = turn_power_at(2.0, V60)["total_power"]
        p3 = turn_power_at(3.0, V60)["total_power"]
        self.assertLess(p1, p15)
        self.assertLess(p15, p2)
        self.assertLess(p2, p3)

    def test_workflow_step4_turn_power_valueerror_propagation(self):
        """Workflow step 4: turn_power propagates the component ValueErrors
        (load factor below 1 and non-positive weight)."""
        with self.assertRaises(ValueError):
            turn_power_at(0.99, V60)
        with self.assertRaises(ValueError):
            rtp.turn_power(2.0, 0.0, AREA, RHO, V60, SOLIDITY, CD0,
                           TIP_SPEED, FLAT_PLATE)


class WorkflowStep5SustainedLoadFactorTests(unittest.TestCase):
    """Workflow step 5: sustained-load-factor inversion from available
    power."""

    def test_workflow_step5_sustained_600kw_full_state(self):
        """Workflow step 5: available power 600000 W at 60 m/s sustains load
        factor 2.00491 (bound 1.95 to 2.06) with bank angle 1.04861 rad,
        turning induced velocity 3.73929 m/s, induced power 186005 W and
        total power 600000 W; turn_power at the returned load factor
        reproduces the available power (round trip)."""
        result = sustained_at(600000.0, V60)
        self.assertAlmostEqual(result["load_factor"], 2.00491, delta=1e-4)
        self.assertTrue(1.95 <= result["load_factor"] <= 2.06)
        self.assertEqual(result["note"], "power-limited")
        self.assertAlmostEqual(result["bank_angle"], 1.04861, delta=1e-4)
        self.assertAlmostEqual(result["induced_velocity"], 3.73929,
                               delta=1e-4)
        self.assertAlmostEqual(result["induced_power"], 186005.0, delta=1.0)
        self.assertAlmostEqual(result["total_power"], 600000.0, delta=1e-1)
        check = turn_power_at(result["load_factor"], V60)
        self.assertAlmostEqual(check["total_power"], 600000.0, delta=1e-1)

    def test_workflow_step5_sustained_falls_with_speed_450kw(self):
        """Workflow step 5: at 450000 W the sustained-load-factor falls as
        the speed rises, 1.86867 at 40 m/s above 1.69094 at 50 m/s (the
        parasite V**3 growth cutting the sustained load factor)."""
        at40 = sustained_at(450000.0, V40)
        at50 = sustained_at(450000.0, V50)
        self.assertAlmostEqual(at40["load_factor"], 1.86867, delta=1e-4)
        self.assertAlmostEqual(at50["load_factor"], 1.69094, delta=1e-4)
        self.assertGreater(at40["load_factor"], at50["load_factor"])

    def test_workflow_step5_sustained_rises_with_available_power(self):
        """Workflow step 5: at fixed speed the sustained-load-factor rises
        with the available power (700000 W above 600000 W, both above 1)."""
        p600 = sustained_at(600000.0, V60)["load_factor"]
        p700 = sustained_at(700000.0, V60)["load_factor"]
        self.assertGreater(p700, p600)
        self.assertGreater(p600, 1.0)

    def test_workflow_step5_max_bank_from_power_identity(self):
        """Workflow step 5: max_bank_from_power returns 1.04861 rad at
        600000 W, equal to acos(1 / n_sustained) from the single solve."""
        bank = rtp.max_bank_from_power(600000.0, WEIGHT, AREA, RHO, V60,
                                       SOLIDITY, CD0, TIP_SPEED, FLAT_PLATE)
        result = sustained_at(600000.0, V60)
        self.assertAlmostEqual(bank, 1.04861, delta=1e-4)
        self.assertAlmostEqual(bank, math.acos(1.0 / result["load_factor"]),
                               delta=1e-9)
        self.assertAlmostEqual(bank, result["bank_angle"], delta=1e-12)

    def test_workflow_step5_sustained_valueerrors(self):
        """Workflow step 5: available power below the n = 1 total at the
        speed (level flight not sustainable) and non-positive available
        power raise ValueError."""
        with self.assertRaises(ValueError):
            sustained_at(400000.0, V60)
        with self.assertRaises(ValueError):
            sustained_at(0.0, V60)
        with self.assertRaises(ValueError):
            sustained_at(-1.0, V60)

    def test_workflow_step5_sustained_excess_above_ceiling(self):
        """Workflow step 5: available power above the total power at n =
        ceiling returns load_factor 10.0 with note power-excess above
        ceiling."""
        ceiling_total = turn_power_at(rtp.N_CEILING, V60)["total_power"]
        result = sustained_at(ceiling_total + 1.0, V60)
        self.assertEqual(result["load_factor"], rtp.N_CEILING)
        self.assertEqual(result["note"], "power-excess above ceiling")
        self.assertLess(result["total_power"], ceiling_total + 1.0)

    def test_workflow_step5_sustained_ceiling_and_rotor_valueerrors(self):
        """Workflow step 5: a ceiling at or below 1.0, non-positive rotor
        inputs, negative speed and non-positive k raise ValueError, and
        max_bank_from_power propagates them."""
        with self.assertRaises(ValueError):
            rtp.sustained_load_factor(600000.0, WEIGHT, AREA, RHO, V60,
                                      SOLIDITY, CD0, TIP_SPEED, FLAT_PLATE,
                                      ceiling=1.0)
        with self.assertRaises(ValueError):
            rtp.sustained_load_factor(600000.0, WEIGHT, AREA, RHO, V60,
                                      SOLIDITY, CD0, TIP_SPEED, FLAT_PLATE,
                                      ceiling=0.5)
        with self.assertRaises(ValueError):
            rtp.sustained_load_factor(600000.0, WEIGHT, AREA, RHO, -1.0,
                                      SOLIDITY, CD0, TIP_SPEED, FLAT_PLATE)
        with self.assertRaises(ValueError):
            rtp.sustained_load_factor(600000.0, 0.0, AREA, RHO, V60,
                                      SOLIDITY, CD0, TIP_SPEED, FLAT_PLATE)
        with self.assertRaises(ValueError):
            rtp.sustained_load_factor(600000.0, WEIGHT, 0.0, RHO, V60,
                                      SOLIDITY, CD0, TIP_SPEED, FLAT_PLATE)
        with self.assertRaises(ValueError):
            rtp.sustained_load_factor(600000.0, WEIGHT, AREA, RHO, V60,
                                      SOLIDITY, 0.0, TIP_SPEED, FLAT_PLATE)
        with self.assertRaises(ValueError):
            rtp.sustained_load_factor(600000.0, WEIGHT, AREA, RHO, V60,
                                      SOLIDITY, CD0, TIP_SPEED, FLAT_PLATE,
                                      k=-1.0)
        with self.assertRaises(ValueError):
            rtp.max_bank_from_power(0.0, WEIGHT, AREA, RHO, V60, SOLIDITY,
                                    CD0, TIP_SPEED, FLAT_PLATE)


class WorkflowStep6KinematicsTests(unittest.TestCase):
    """Workflow step 6: bank_from_load_factor, turn_rate, turn_radius."""

    def test_workflow_step6_bank_angle_identity(self):
        """Workflow step 6: bank_from_load_factor at n = 2 is acos(1/2) =
        1.0472 rad and cos(bank) = 1 / n holds for the level turn."""
        bank = rtp.bank_from_load_factor(2.0)
        self.assertAlmostEqual(bank, 1.0472, delta=1e-5)
        self.assertAlmostEqual(math.cos(bank), 1.0 / 2.0, delta=1e-12)

    def test_workflow_step6_turn_rate_and_radius_anchors(self):
        """Workflow step 6: turn_rate at n = 2, 60 m/s is 0.283094 rad/s
        (bound 0.27 to 0.30), turn_radius is 211.944 m (bound 200 to 225),
        and omega * R equals the turn speed V exactly."""
        omega = rtp.turn_rate(2.0, V60)
        radius = rtp.turn_radius(2.0, V60)
        self.assertAlmostEqual(omega, 0.283094, delta=1e-5)
        self.assertTrue(0.27 <= omega <= 0.30)
        self.assertAlmostEqual(radius, 211.944, delta=1e-3)
        self.assertTrue(200.0 <= radius <= 225.0)
        self.assertAlmostEqual(omega * radius, V60, delta=1e-9)

    def test_workflow_step6_sustained_maneuver_kinematics_600kw(self):
        """Workflow step 6: at the 600000 W sustained point the turn rate is
        0.28402 rad/s and the turn radius 211.253 m, with omega * R = V."""
        result = sustained_at(600000.0, V60)
        omega = rtp.turn_rate(result["load_factor"], V60)
        radius = rtp.turn_radius(result["load_factor"], V60)
        self.assertAlmostEqual(omega, 0.28402, delta=1e-4)
        self.assertAlmostEqual(radius, 211.253, delta=1e-2)
        self.assertAlmostEqual(omega * radius, V60, delta=1e-6)

    def test_workflow_step6_sustained_maneuver_kinematics_450kw(self):
        """Workflow step 6: at 450000 W the 40 m/s sustained point gives
        turn rate 0.387015 rad/s and radius 103.355 m; at 50 m/s rate
        0.267439 rad/s and radius 186.959 m."""
        at40 = sustained_at(450000.0, V40)
        omega40 = rtp.turn_rate(at40["load_factor"], V40)
        radius40 = rtp.turn_radius(at40["load_factor"], V40)
        self.assertAlmostEqual(omega40, 0.387015, delta=1e-5)
        self.assertAlmostEqual(radius40, 103.355, delta=1e-2)
        at50 = sustained_at(450000.0, V50)
        omega50 = rtp.turn_rate(at50["load_factor"], V50)
        radius50 = rtp.turn_radius(at50["load_factor"], V50)
        self.assertAlmostEqual(omega50, 0.267439, delta=1e-5)
        self.assertAlmostEqual(radius50, 186.959, delta=1e-2)

    def test_workflow_step6_kinematics_valueerrors(self):
        """Workflow step 6: bank, rate and radius reject a load factor below
        1 and rate and radius reject zero speed."""
        with self.assertRaises(ValueError):
            rtp.bank_from_load_factor(0.99)
        with self.assertRaises(ValueError):
            rtp.turn_rate(0.99, V60)
        with self.assertRaises(ValueError):
            rtp.turn_rate(2.0, 0.0)
        with self.assertRaises(ValueError):
            rtp.turn_radius(0.99, V60)
        with self.assertRaises(ValueError):
            rtp.turn_radius(2.0, 0.0)


class WorkflowStep7DeterminismTests(unittest.TestCase):
    """Workflow step 7: contract test run, determinism and module surface."""

    def test_workflow_step7_module_constants(self):
        """Workflow step 7: the module constants G0, K_DEFAULT, CD0_DEFAULT,
        N_CEILING and BISECT_ITER match the spec values."""
        self.assertEqual(rtp.G0, 9.80665)
        self.assertEqual(rtp.K_DEFAULT, 1.15)
        self.assertEqual(rtp.CD0_DEFAULT, 0.012)
        self.assertEqual(rtp.N_CEILING, 10.0)
        self.assertEqual(rtp.BISECT_ITER, 120)

    def test_workflow_step7_inflow_deterministic_bit_identical(self):
        """Workflow step 7: two identical turning-flight-inflow calls return
        bit-identical values."""
        a = rtp.generalized_induced_velocity(2.0, WEIGHT, AREA, RHO, V60)
        b = rtp.generalized_induced_velocity(2.0, WEIGHT, AREA, RHO, V60)
        self.assertEqual(a, b)

    def test_workflow_step7_sustained_deterministic_and_fixed_notes(self):
        """Workflow step 7: two identical sustained solves are bit-identical
        and the note strings are fixed across states."""
        a = sustained_at(600000.0, V60)
        b = sustained_at(600000.0, V60)
        self.assertEqual(a, b)
        self.assertEqual(a["note"], "power-limited")


if __name__ == "__main__":
    unittest.main()
