#!/usr/bin/env python3
"""Gate 3 contract test: balanced field length.

Exercises scripts/balanced_field_length_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the balanced
field length workflow of SKILL.md: split the thrust on the remaining
engines, compute the constant accelerations and braking deceleration,
trace the accelerate-stop distance curve and the accelerate-go
distance curve, solve the V1 balance quadratic for the balanced
decision speed, read the balanced field length, and sanity-check the
bracket; invalid inputs raise ValueError. Worked example: twin-engine
transport, W = 600000 N, total installed thrust 150000 N, V_LOF = 80
m/s, mu_roll 0.03, mu_brake 0.45, OEI climb gradient 0.024, 35-ft
obstacle, 1 s reaction and rotation times. Prep-verified anchors:
balanced V1 77.2815 m/s and balanced field length 2138.10 m; the
module's real outputs are the assert targets.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import balanced_field_length_logic as bfl  # noqa: E402

# Worked example (spec): twin-engine transport, 600000 N, 150000 N
# installed thrust, lift-off speed 80 m/s, rolling friction 0.03,
# brake friction 0.45, OEI climb gradient 0.024, 35-ft obstacle.
W = 600000.0
T_ALL = 150000.0
V_LOF = 80.0
MU_ROLL = 0.03
MU_BRAKE = 0.45
GRAD = 0.024
N_ENG = 2
A_ALL = 2.157463
A_OEI = 0.93163175
A_BRAKE = 4.4129925
V1_BAL = 77.2815
BFL_ANCHOR = 2138.10


class OEIThrustTest(unittest.TestCase):
    def test_oei_thrust_twin_anchor(self):
        # Workflow step 2 (split the thrust on the remaining engines)
        # at engine_count 2 keeps one engine of two.
        self.assertAlmostEqual(bfl.oei_thrust(150000, 2), 75000, delta=1e-9)

    def test_oei_thrust_trijet_and_quad(self):
        # Workflow step 2 (split the thrust on the remaining engines)
        # for the trijet and quad engine counts.
        self.assertAlmostEqual(bfl.oei_thrust(150000, 3), 100000, delta=1e-9)
        self.assertAlmostEqual(bfl.oei_thrust(150000, 4), 112500, delta=1e-9)

    def test_oei_thrust_rejects_single_engine_and_bad_thrust(self):
        with self.assertRaises(ValueError):
            bfl.oei_thrust(150000, 1)
        with self.assertRaises(ValueError):
            bfl.oei_thrust(150000, 0)
        with self.assertRaises(ValueError):
            bfl.oei_thrust(0, 2)
        with self.assertRaises(ValueError):
            bfl.oei_thrust(-150000, 2)


class GroundAccelerationTest(unittest.TestCase):
    def test_all_engine_ground_acceleration_anchor(self):
        # Workflow step 3 (compute the constant accelerations): the
        # all-engine ground acceleration of the worked example.
        self.assertAlmostEqual(
            bfl.ground_acceleration(T_ALL, W, MU_ROLL), A_ALL, delta=1e-4
        )

    def test_oei_ground_acceleration_anchor(self):
        # Workflow step 3 (compute the constant accelerations): the
        # engine-out ground acceleration on the remaining engine.
        self.assertAlmostEqual(
            bfl.ground_acceleration(75000, W, MU_ROLL), A_OEI, delta=1e-4
        )

    def test_ground_acceleration_rejects_non_physical(self):
        with self.assertRaises(ValueError):
            bfl.ground_acceleration(T_ALL, 0, MU_ROLL)
        with self.assertRaises(ValueError):
            bfl.ground_acceleration(0, W, MU_ROLL)
        with self.assertRaises(ValueError):
            bfl.ground_acceleration(T_ALL, W, 1.0)
        with self.assertRaises(ValueError):
            bfl.ground_acceleration(T_ALL, W, -0.1)
        with self.assertRaises(ValueError):
            bfl.ground_acceleration(15000, W, MU_ROLL)


class BrakingDecelerationTest(unittest.TestCase):
    def test_braking_deceleration_anchor(self):
        # Workflow step 3 (compute the constant accelerations) covers
        # the braking deceleration from the brake friction.
        self.assertAlmostEqual(
            bfl.braking_deceleration(0.45), A_BRAKE, delta=1e-4
        )

    def test_braking_deceleration_rejects_zero_and_unity(self):
        with self.assertRaises(ValueError):
            bfl.braking_deceleration(0.0)
        with self.assertRaises(ValueError):
            bfl.braking_deceleration(1.0)


class AccelerateDistanceTest(unittest.TestCase):
    def test_roll_zero_to_liftoff_anchor(self):
        # Workflow step 4 (trace the accelerate-stop distance curve)
        # needs the roll distance to the lift-off speed: (0 to 80) at
        # the all-engine acceleration is 1483.22 m.
        self.assertAlmostEqual(
            bfl.accelerate_distance(0.0, V_LOF, A_ALL), 1483.22, delta=0.05
        )

    def test_oei_leg_distance(self):
        # Workflow step 5 (trace the accelerate-go distance curve)
        # rolls from the balanced V1 to lift-off on the remaining
        # engine only.
        self.assertAlmostEqual(
            bfl.accelerate_distance(V1_BAL, V_LOF, A_OEI), 229.48, delta=0.05
        )

    def test_accelerate_distance_rejects_degenerate_segments(self):
        with self.assertRaises(ValueError):
            bfl.accelerate_distance(40.0, 30.0, 2.0)
        with self.assertRaises(ValueError):
            bfl.accelerate_distance(40.0, 40.0, 2.0)
        with self.assertRaises(ValueError):
            bfl.accelerate_distance(-10.0, 40.0, 2.0)
        with self.assertRaises(ValueError):
            bfl.accelerate_distance(0.0, 40.0, 0.0)


class StopDistanceTest(unittest.TestCase):
    def test_stop_distance_at_balanced_v1(self):
        # Workflow step 4 (trace the accelerate-stop distance curve)
        # brakes from the balanced V1 to a full stop: 676.69 m.
        self.assertAlmostEqual(
            bfl.stop_distance(V1_BAL, A_BRAKE), 676.69, delta=0.05
        )

    def test_stop_distance_rejects_negative_speed(self):
        with self.assertRaises(ValueError):
            bfl.stop_distance(-5.0, A_BRAKE)
        with self.assertRaises(ValueError):
            bfl.stop_distance(80.0, 0.0)


class AccelerateStopDistanceTest(unittest.TestCase):
    def test_asd_zero_at_rest(self):
        # Workflow step 4 (trace the accelerate-stop distance curve)
        # starts at ASD(0) = 0 for a decision made at rest.
        self.assertEqual(bfl.accelerate_stop_distance(0.0, T_ALL, W, MU_ROLL, MU_BRAKE), 0.0)

    def test_asd_at_balanced_v1_anchor(self):
        # Workflow step 4 (trace the accelerate-stop distance curve)
        # at the balanced V1 gives the 2138.10 m anchor.
        self.assertAlmostEqual(
            bfl.accelerate_stop_distance(V1_BAL, T_ALL, W, MU_ROLL, MU_BRAKE),
            BFL_ANCHOR,
            delta=0.1,
        )

    def test_asd_strictly_increasing_over_bracket(self):
        # Workflow step 8 (sanity-check the bracket): the
        # accelerate-stop distance curve rises with the decision
        # speed, ASD(0) < ASD(40) < ASD(80).
        asd0 = bfl.accelerate_stop_distance(0.0, T_ALL, W, MU_ROLL, MU_BRAKE)
        asd40 = bfl.accelerate_stop_distance(40.0, T_ALL, W, MU_ROLL, MU_BRAKE)
        asd80 = bfl.accelerate_stop_distance(80.0, T_ALL, W, MU_ROLL, MU_BRAKE)
        self.assertLess(asd0, asd40)
        self.assertLess(asd40, asd80)
        self.assertAlmostEqual(asd80, 2288.36, delta=0.1)

    def test_asd_rejects_negative_reaction_time(self):
        with self.assertRaises(ValueError):
            bfl.accelerate_stop_distance(V1_BAL, T_ALL, W, MU_ROLL, MU_BRAKE,
                                         reaction_time_s=-1.0)

    def test_asd_rejects_negative_speed_and_uses_default_reaction(self):
        # Workflow step 4 defaults the reaction time to the module
        # constant 1.0 s, so the explicit and default calls agree.
        with self.assertRaises(ValueError):
            bfl.accelerate_stop_distance(-1.0, T_ALL, W, MU_ROLL, MU_BRAKE)
        self.assertAlmostEqual(
            bfl.accelerate_stop_distance(50.0, T_ALL, W, MU_ROLL, MU_BRAKE),
            bfl.accelerate_stop_distance(50.0, T_ALL, W, MU_ROLL, MU_BRAKE,
                                         reaction_time_s=1.0),
            delta=1e-9,
        )


class AccelerateGoDistanceTest(unittest.TestCase):
    def test_agd_at_balanced_v1_anchor(self):
        # Workflow step 5 (trace the accelerate-go distance curve) at
        # the balanced V1 equals the accelerate-stop distance there:
        # 2138.10 m is the balance anchor.
        self.assertAlmostEqual(
            bfl.accelerate_go_distance(V1_BAL, T_ALL, N_ENG, W, MU_ROLL,
                                       V_LOF, GRAD),
            BFL_ANCHOR,
            delta=0.1,
        )

    def test_agd_at_rest_bracket_value(self):
        # Workflow step 8 (sanity-check the bracket): AGD(0) is the
        # full engine-out run from rest, 3959.33 m.
        self.assertAlmostEqual(
            bfl.accelerate_go_distance(0.0, T_ALL, N_ENG, W, MU_ROLL,
                                       V_LOF, GRAD),
            3959.33,
            delta=0.1,
        )

    def test_agd_at_liftoff_bracket_value(self):
        # Workflow step 8 (sanity-check the bracket): AGD(V_LOF) ends
        # the curve at 2007.72 m with a zero-length engine-out leg.
        self.assertAlmostEqual(
            bfl.accelerate_go_distance(V_LOF, T_ALL, N_ENG, W, MU_ROLL,
                                       V_LOF, GRAD),
            2007.72,
            delta=0.1,
        )

    def test_agd_strictly_decreasing_over_bracket(self):
        # Workflow step 8 (sanity-check the bracket): the
        # accelerate-go distance curve falls as the decision speed
        # rises, AGD(0) > AGD(40) > AGD(80).
        agd0 = bfl.accelerate_go_distance(0.0, T_ALL, N_ENG, W, MU_ROLL, V_LOF, GRAD)
        agd40 = bfl.accelerate_go_distance(40.0, T_ALL, N_ENG, W, MU_ROLL, V_LOF, GRAD)
        agd80 = bfl.accelerate_go_distance(V_LOF, T_ALL, N_ENG, W, MU_ROLL, V_LOF, GRAD)
        self.assertGreater(agd0, agd40)
        self.assertGreater(agd40, agd80)

    def test_agd_rejects_decision_beyond_liftoff_and_negative_v1(self):
        with self.assertRaises(ValueError):
            bfl.accelerate_go_distance(85.0, T_ALL, N_ENG, W, MU_ROLL, V_LOF, GRAD)
        with self.assertRaises(ValueError):
            bfl.accelerate_go_distance(-5.0, T_ALL, N_ENG, W, MU_ROLL, V_LOF, GRAD)

    def test_agd_rejects_bad_gradient_and_engine_count(self):
        with self.assertRaises(ValueError):
            bfl.accelerate_go_distance(V1_BAL, T_ALL, N_ENG, W, MU_ROLL, V_LOF, 0.0)
        with self.assertRaises(ValueError):
            bfl.accelerate_go_distance(V1_BAL, T_ALL, N_ENG, W, MU_ROLL, V_LOF, -0.024)
        with self.assertRaises(ValueError):
            bfl.accelerate_go_distance(V1_BAL, T_ALL, 1, W, MU_ROLL, V_LOF, GRAD)


class BalancedV1Test(unittest.TestCase):
    def test_balanced_v1_anchor(self):
        # Workflow step 6 (solve the V1 balance) finds the balanced
        # decision speed 77.2815 m/s inside [0, V_LOF].
        v1 = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, GRAD)
        self.assertAlmostEqual(v1, V1_BAL, delta=0.01)
        self.assertGreaterEqual(v1, 0.0)
        self.assertLessEqual(v1, V_LOF)

    def test_balance_identity_asd_equals_agd(self):
        # Workflow step 7 (read the balanced field length): at the
        # balanced V1 the accelerate-stop distance equals the
        # accelerate-go distance to machine precision.
        v1 = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, GRAD)
        asd = bfl.accelerate_stop_distance(v1, T_ALL, W, MU_ROLL, MU_BRAKE)
        agd = bfl.accelerate_go_distance(v1, T_ALL, N_ENG, W, MU_ROLL, V_LOF, GRAD)
        self.assertAlmostEqual(asd, agd, places=6)

    def test_minimax_property_over_bracket(self):
        # Workflow step 8 (sanity-check the bracket): every other
        # decision speed needs at least as much runway as the balanced
        # field length because one of the two curves exceeds it.
        v1 = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, GRAD)
        bfl_len = bfl.balanced_field_length(v1, T_ALL, N_ENG, W, MU_ROLL,
                                            MU_BRAKE, V_LOF, GRAD)
        for probe in (0.0, 40.0, V_LOF):
            asd = bfl.accelerate_stop_distance(probe, T_ALL, W, MU_ROLL, MU_BRAKE)
            agd = bfl.accelerate_go_distance(probe, T_ALL, N_ENG, W, MU_ROLL, V_LOF, GRAD)
            self.assertGreaterEqual(max(asd, agd), bfl_len)

    def test_no_balance_outside_bracket_raises(self):
        # Workflow step 6 (solve the V1 balance) discloses a case
        # where the root falls beyond lift-off, so no balanced
        # decision exists in the physical range.
        with self.assertRaises(ValueError):
            bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, 0.8, V_LOF, GRAD)

    def test_gradient_sensitivity_lowers_balanced_v1(self):
        # Workflow step 8 (sanity-check the bracket): a steeper OEI
        # climb gradient shortens the accelerate-go distance and
        # lowers the balanced V1.
        v1_base = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, GRAD)
        v1_steep = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, 0.03)
        self.assertLess(v1_steep, v1_base)

    def test_brake_sensitivity_raises_balanced_v1(self):
        # Workflow step 8 (sanity-check the bracket): stronger brakes
        # shorten the accelerate-stop distance and raise the balanced
        # V1.
        v1_base = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, GRAD)
        v1_strong = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, 0.55, V_LOF, GRAD)
        self.assertGreater(v1_strong, v1_base)


class BalancedFieldLengthTest(unittest.TestCase):
    def test_balanced_field_length_anchor(self):
        # Workflow step 7 (read the balanced field length) gives the
        # 2138.10 m anchor for the worked example.
        v1 = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, GRAD)
        self.assertAlmostEqual(
            bfl.balanced_field_length(v1, T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE,
                                      V_LOF, GRAD),
            BFL_ANCHOR,
            delta=0.1,
        )

    def test_balanced_field_length_matches_both_curves_at_balance(self):
        # Workflow step 7 (read the balanced field length): the field
        # length equals ASD and AGD at the balanced decision speed.
        v1 = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, GRAD)
        length = bfl.balanced_field_length(v1, T_ALL, N_ENG, W, MU_ROLL,
                                           MU_BRAKE, V_LOF, GRAD)
        asd = bfl.accelerate_stop_distance(v1, T_ALL, W, MU_ROLL, MU_BRAKE)
        agd = bfl.accelerate_go_distance(v1, T_ALL, N_ENG, W, MU_ROLL, V_LOF, GRAD)
        self.assertAlmostEqual(length, asd, delta=1e-6)
        self.assertAlmostEqual(length, agd, delta=1e-6)

    def test_gradient_sensitivity_shortens_field_length(self):
        # Workflow step 8 (sanity-check the bracket): the balanced
        # field length falls when the OEI climb gradient steepens.
        v1 = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, GRAD)
        length = bfl.balanced_field_length(v1, T_ALL, N_ENG, W, MU_ROLL,
                                           MU_BRAKE, V_LOF, GRAD)
        v1b = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, 0.03)
        length_b = bfl.balanced_field_length(v1b, T_ALL, N_ENG, W, MU_ROLL,
                                             MU_BRAKE, V_LOF, 0.03)
        self.assertLess(length_b, length)

    def test_brake_sensitivity_shortens_field_length(self):
        # Workflow step 8 (sanity-check the bracket): the balanced
        # field length falls when the brakes strengthen even though
        # the balanced V1 rises.
        v1 = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, GRAD)
        length = bfl.balanced_field_length(v1, T_ALL, N_ENG, W, MU_ROLL,
                                           MU_BRAKE, V_LOF, GRAD)
        v1c = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, 0.55, V_LOF, GRAD)
        length_c = bfl.balanced_field_length(v1c, T_ALL, N_ENG, W, MU_ROLL,
                                             0.55, V_LOF, GRAD)
        self.assertLess(length_c, length)


class DeterminismTest(unittest.TestCase):
    def test_repeated_calls_return_identical_values(self):
        # The whole workflow (steps 2 through 7) is deterministic:
        # repeated calls return identical balanced speeds and lengths.
        v1a = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, GRAD)
        v1b = bfl.balanced_v1(T_ALL, N_ENG, W, MU_ROLL, MU_BRAKE, V_LOF, GRAD)
        self.assertEqual(v1a, v1b)
        la = bfl.balanced_field_length(v1a, T_ALL, N_ENG, W, MU_ROLL,
                                       MU_BRAKE, V_LOF, GRAD)
        lb = bfl.balanced_field_length(v1a, T_ALL, N_ENG, W, MU_ROLL,
                                       MU_BRAKE, V_LOF, GRAD)
        self.assertEqual(la, lb)


if __name__ == "__main__":
    unittest.main(verbosity=2)
