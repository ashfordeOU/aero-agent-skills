"""Contract test for vmcg-determination (flight-test-operations/envelope).

Exercises the SKILL.md workflow end to end: step 1 fixes the ground roll
configuration and atmosphere with the ISA density ratio sigma, step 2
builds the engine-out yawing moment on the ground roll from the
operating-engine thrust at the failed engine lateral arm, step 3 applies
the nosewheel steering authority below the steering cutout speed with
the friction-limited steering restoring moment, step 4 solves the
steering-free rudder authority limited ground speed from the closed
form, step 5 solves the pedal-force limited ground speed with the boost
factor against the 667 N (150 lbf) pedal force criterion, step 6
corrects each run speed to standard conditions (calibrated airspeed
correction, weight correction to the reference takeoff weight, flap
normalization through the rotation-limit lift coefficient) and classifies
the run into the steering-held, departed, at-limit and with-margin
classes, step 7 reduces the qualifying at-limit runs to the Vmcg verdict
with the bracket consistency check against the departed and with-margin
brackets, step 8 checks the demonstration at the verdict (required
deflection below the rudder limit, full-deflection pedal force within
the 667 N limit with the boost factor, authority margin) and applies the
stall protection guard on the reference stall speed, and step 9 gates
the balanced-field V1 schedule against the demonstrated Vmcg.

Fact terms exercised: engine-out yawing moment, steering cutout speed,
nosewheel steering authority, steering restoring moment, rudder
authority limited ground speed, pedal-force limited ground speed, boost
factor, 667 N pedal force criterion, calibrated airspeed, reference
takeoff weight, rotation-limit lift coefficient, at-limit run, departed
run, with-margin run, steering-held run, Vmcg verdict, bracket
consistency check, stall protection guard, reference stall speed,
balanced-field V1 schedule. Procedure terms exercised: fix, build,
apply, solve, correct, classify, reduce, check, gate.

All anchors are real outputs of the spec worked example (the module's
own outputs under the reference takeoff weight 65000 kg, reference takeoff
flap 15 deg with cl_0 1.10 and cl_per_deg 0.020 per deg). Offline,
deterministic, stdlib only; run with python3 scripts/test_vmcg_determination.py
and under the pre-push hook interpreter.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vmcg_determination_logic as L  # noqa: E402

# Worked example configuration (spec section, module constants).
W_REF = 65000.0
FLAP_REF = 15.0
CL_0 = 1.10
CL_PER_DEG = 0.020
T_OP = 55000.0
Y_FAIL = 8.0
S_V = 26.0
L_V = 16.0
CLV_DR = 0.85
DELTA_MAX = math.radians(30.0)
S_R = 8.5
C_R = 1.3
CH_DR = 0.045
PEDAL_ARM = 0.35
BOOST = 0.34
V_CUT = 40.0
V_AUTH = L.authority_limited_ground_speed(T_OP, Y_FAIL, S_V, L_V,
                                          CLV_DR, DELTA_MAX)
V_FORCE = L.force_limited_ground_speed(L.F_LIM, PEDAL_ARM, S_R, C_R,
                                       CH_DR, DELTA_MAX, BOOST)

WORKED_RUNS = [
    {"id": "R1", "speed": 36.8, "weight": 63800.0, "flap": 15.0,
     "steering_on": True},
    {"id": "R2", "speed": 52.4, "weight": 65000.0, "flap": 15.0,
     "steering_on": False},
    {"id": "R3", "speed": 58.6, "weight": 64000.0, "flap": 15.0,
     "steering_on": False},
    {"id": "R4", "speed": 62.8, "weight": 64500.0, "flap": 15.0,
     "steering_on": False},
    {"id": "R5", "speed": 67.4, "weight": 65000.0, "flap": 15.0,
     "steering_on": False, "h_p": 600.0, "dt_isa": 12.0,
     "tas_input": True},
    {"id": "R6", "speed": 66.9, "weight": 64700.0, "flap": 15.0,
     "steering_on": False},
    {"id": "R7", "speed": 69.5, "weight": 65000.0, "flap": 15.0,
     "steering_on": False},
]


def verdict():
    """Run the worked seven-run reduction once (step 7 helper)."""
    return L.vmcg_verdict(WORKED_RUNS, V_AUTH, V_FORCE, W_REF, FLAP_REF,
                          CL_0, CL_PER_DEG)


class TestIsaAtmosphere(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: fix the ground roll configuration
    and atmosphere with the ISA density ratio sigma."""

    def test_isa_sigma_sea_level_and_altitude_anchors(self):
        """Step 1 atmosphere anchors: isa_sigma(0, 0) is exactly 1.0, and
        at 600 m with +12 K the warm-day sigma 0.905430 (sqrt 0.951541)
        sits below the standard-day 0.943654 and below 1."""
        self.assertEqual(L.isa_sigma(0.0, 0.0), 1.0)
        sigma_warm = L.isa_sigma(600.0, 12.0)
        sigma_std = L.isa_sigma(600.0, 0.0)
        self.assertAlmostEqual(sigma_warm, 0.905430, delta=1e-5)
        self.assertAlmostEqual(sigma_std, 0.943654, delta=1e-5)
        self.assertAlmostEqual(math.sqrt(sigma_warm), 0.951541, delta=1e-5)
        self.assertLess(sigma_warm, sigma_std)
        self.assertLess(sigma_std, 1.0)

    def test_isa_sigma_invalid_inputs_raise(self):
        """ValueError rejection: pressure altitude outside [0, 11000] m
        and a non-positive ambient temperature raise."""
        with self.assertRaises(ValueError):
            L.isa_sigma(-1.0, 0.0)
        with self.assertRaises(ValueError):
            L.isa_sigma(12000.0, 0.0)
        with self.assertRaises(ValueError):
            L.isa_sigma(11000.0, -220.0)

    def test_tas_to_cas_warm_day_anchor_and_identity(self):
        """Step 1 airspeed correction: tas_to_cas(67.4, 600, 12) is
        64.133853 m/s through the sigma density ratio and degenerates to
        the input exactly at sea level standard conditions; a zero true
        airspeed raises."""
        self.assertAlmostEqual(L.tas_to_cas(67.4, 600.0, 12.0),
                               64.133853, delta=1e-3)
        self.assertEqual(L.tas_to_cas(67.4, 0.0, 0.0), 67.4)
        with self.assertRaises(ValueError):
            L.tas_to_cas(0.0, 0.0, 0.0)


class TestStandardConditionCorrections(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: correct each run speed to
    standard conditions with the weight correction to the reference
    takeoff weight and the flap normalization through the rotation-limit
    lift coefficient."""

    def test_weight_corrected_anchors(self):
        """Step 6 weight correction: v*sqrt(w_ref/w_test) gives 120.0 from
        60.0 at a 4:1 reference ratio, and the worked weight factors
        sqrt(65000/64000) 1.007782, sqrt(65000/64500) 1.003868 and
        sqrt(65000/64700) 1.002316 pull the light-run speeds up."""
        self.assertAlmostEqual(L.weight_corrected_speed(60.0, 100.0, 400.0),
                               120.0, delta=1e-9)
        self.assertAlmostEqual(math.sqrt(W_REF / 64000.0), 1.007782,
                               delta=1e-6)
        self.assertAlmostEqual(math.sqrt(W_REF / 64500.0), 1.003868,
                               delta=1e-6)
        self.assertAlmostEqual(math.sqrt(W_REF / 64700.0), 1.002316,
                               delta=1e-6)

    def test_weight_corrected_same_weight_and_raises(self):
        """Step 6 degeneracy: the same-weight call returns the input
        exactly; a zero test weight raises ValueError."""
        self.assertEqual(L.weight_corrected_speed(60.0, 65000.0, 65000.0),
                         60.0)
        with self.assertRaises(ValueError):
            L.weight_corrected_speed(60.0, 0.0, 65000.0)

    def test_flap_normalized_lower_to_reference_anchor(self):
        """Step 6 flap normalization: a speed measured at the lower 10 deg
        setting rises to 60.611957 m/s when normalized up to the 15 deg
        reference (CL 1.300 to 1.400)."""
        self.assertAlmostEqual(
            L.flap_normalized_speed(62.9, 10.0, FLAP_REF, CL_0, CL_PER_DEG),
            60.611957, delta=1e-3)

    def test_flap_normalized_round_trip_and_invalid(self):
        """Step 6 flap round trip: the same-flap call returns the input,
        the 10-to-15-to-10 normalization returns 62.9 within 1e-9, and a
        negative flap or a zero cl_0 raises."""
        v = 62.9
        self.assertEqual(L.flap_normalized_speed(v, FLAP_REF, FLAP_REF,
                                                 CL_0, CL_PER_DEG), v)
        up = L.flap_normalized_speed(v, 10.0, 15.0, CL_0, CL_PER_DEG)
        back = L.flap_normalized_speed(up, 15.0, 10.0, CL_0, CL_PER_DEG)
        self.assertAlmostEqual(back, v, delta=1e-9)
        with self.assertRaises(ValueError):
            L.flap_normalized_speed(62.9, -1.0, 15.0, CL_0, CL_PER_DEG)
        with self.assertRaises(ValueError):
            L.flap_normalized_speed(62.9, 10.0, 15.0, 0.0, CL_PER_DEG)

    def test_corrected_run_speed_tas_chain_anchor(self):
        """Step 6 full reduction: corrected_run_speed on the R5 side (TAS
        67.4 at 600 m +12 K, reference weight and flap) equals the manual
        chain weight_corrected_speed(tas_to_cas(67.4, 600, 12), ...) with
        a unit flap factor, 64.133853 m/s."""
        c = L.corrected_run_speed(67.4, 65000.0, W_REF, 15.0, FLAP_REF,
                                  CL_0, CL_PER_DEG, 600.0, 12.0,
                                  tas_input=True)
        self.assertAlmostEqual(c, 64.133853, delta=1e-3)
        manual = L.weight_corrected_speed(
            L.tas_to_cas(67.4, 600.0, 12.0), 65000.0, W_REF)
        self.assertAlmostEqual(c, manual, delta=1e-9)

    def test_corrected_run_speed_cas_path_anchor(self):
        """Step 6 CAS path: a calibrated airspeed input needs no density
        correction, only the weight and flap factors, so R4 corrects to
        63.042941 m/s; a non-positive measured speed raises."""
        c = L.corrected_run_speed(62.8, 64500.0, W_REF, 15.0, FLAP_REF,
                                  CL_0, CL_PER_DEG)
        self.assertAlmostEqual(c, 63.042941, delta=1e-3)
        with self.assertRaises(ValueError):
            L.corrected_run_speed(0.0, 64500.0, W_REF, 15.0, FLAP_REF,
                                  CL_0, CL_PER_DEG)


class TestEngineOutYawingMomentAndAuthority(unittest.TestCase):
    """Steps 2, 4 and 5 of the SKILL.md workflow: build the engine-out
    yawing moment on the ground roll, solve the steering-free rudder
    authority limited ground speed, solve the pedal-force limited ground
    speed with the boost factor."""

    def test_asym_yaw_moment_anchor_and_raises(self):
        """Step 2 anchor: 55000 N at the 8.0 m failed engine lateral arm
        gives 440000.0 N m exactly; non-positive thrust or arm raises."""
        self.assertEqual(L.asym_yaw_moment_static(T_OP, Y_FAIL), 440000.0)
        with self.assertRaises(ValueError):
            L.asym_yaw_moment_static(0.0, Y_FAIL)
        with self.assertRaises(ValueError):
            L.asym_yaw_moment_static(T_OP, 0.0)

    def test_authority_limited_ground_speed_anchors(self):
        """Step 4 anchor and windmilling variant: the steering-free
        authority limit over the ground speed is 62.289931 m/s
        (121.081940 kt); with the optional s_f_cd 1.2 m2 drag area the
        denominator shrinks and the speed rises to 63.970485 m/s, about
        1.68 m/s above the no-windmilling value. A rudder limit at 61 deg
        raises ValueError."""
        self.assertAlmostEqual(V_AUTH, 62.289931, delta=1e-3)
        self.assertAlmostEqual(V_AUTH / L.KT2MS, 121.081940, delta=0.01)
        v_wm = L.authority_limited_ground_speed(T_OP, Y_FAIL, S_V, L_V,
                                                CLV_DR, DELTA_MAX,
                                                s_f_cd=1.2)
        self.assertAlmostEqual(v_wm, 63.970485, delta=1e-3)
        self.assertAlmostEqual(v_wm - V_AUTH, 1.680554, delta=1e-3)
        with self.assertRaises(ValueError):
            L.authority_limited_ground_speed(T_OP, Y_FAIL, S_V, L_V,
                                             CLV_DR, math.radians(61.0))
        with self.assertRaises(ValueError):
            L.authority_limited_ground_speed(T_OP, Y_FAIL, S_V, L_V,
                                             CLV_DR, 0.0)

    def test_required_deflection_verdict_and_scaling(self):
        """Steps 4 and 8: at the verdict dynamic pressure 2434.327597 Pa
        the required deflection to balance 440000 N m is 0.511165 rad
        (29.287617 deg), below the 0.52360 rad rudder limit, and the
        deflection scales inverse to q."""
        q = 0.5 * L.RHO_SL * 63.042941 ** 2
        self.assertAlmostEqual(q, 2434.327597, delta=1e-2)
        d = L.required_deflection(440000.0, q, S_V, L_V, CLV_DR)
        self.assertAlmostEqual(d, 0.511165, delta=1e-5)
        self.assertAlmostEqual(math.degrees(d), 29.287617, delta=1e-3)
        self.assertLess(d, DELTA_MAX)
        d2 = L.required_deflection(440000.0, 2.0 * q, S_V, L_V, CLV_DR)
        self.assertAlmostEqual(d2, 0.5 * d, delta=1e-12)
        with self.assertRaises(ValueError):
            L.required_deflection(0.0, q, S_V, L_V, CLV_DR)

    def test_pedal_force_boosted_and_manual_anchors(self):
        """Steps 5 and 8: the full-deflection pedal force at the authority
        speed is 601.071429 N boosted (within the 667 N limit, force_ok)
        and 1767.857143 N manual (above it, not force_ok)."""
        q = 0.5 * L.RHO_SL * V_AUTH ** 2
        f_b = L.pedal_force(q, S_R, C_R, CH_DR, DELTA_MAX, BOOST, PEDAL_ARM)
        f_m = L.pedal_force(q, S_R, C_R, CH_DR, DELTA_MAX, 1.0, PEDAL_ARM)
        self.assertAlmostEqual(f_b, 601.071429, delta=1e-2)
        self.assertAlmostEqual(f_m, 1767.857143, delta=1e-2)
        self.assertLessEqual(f_b, L.F_LIM)
        self.assertGreater(f_m, L.F_LIM)

    def test_force_limited_ground_speed_anchors(self):
        """Step 5 anchors: the speed where a full-deflection input demands
        the 667 N limit is 65.617205 m/s (127.549642 kt) boosted and
        38.261077 m/s (74.373583 kt) manual."""
        self.assertAlmostEqual(V_FORCE, 65.617205, delta=1e-3)
        self.assertAlmostEqual(V_FORCE / L.KT2MS, 127.549642, delta=0.01)
        v_man = L.force_limited_ground_speed(L.F_LIM, PEDAL_ARM, S_R, C_R,
                                             CH_DR, DELTA_MAX, 1.0)
        self.assertAlmostEqual(v_man, 38.261077, delta=1e-3)
        self.assertAlmostEqual(v_man / L.KT2MS, 74.373583, delta=0.01)

    def test_pedal_and_force_limit_invalid_raises(self):
        """ValueError rejection: a zero hinge moment coefficient, boost
        outside (0, 1] and a non-positive pedal arm raise in both the
        pedal force and the pedal-force-limited ground speed."""
        with self.assertRaises(ValueError):
            L.pedal_force(1000.0, S_R, C_R, 0.0, DELTA_MAX, BOOST, PEDAL_ARM)
        with self.assertRaises(ValueError):
            L.pedal_force(1000.0, S_R, C_R, CH_DR, DELTA_MAX, 0.0, PEDAL_ARM)
        with self.assertRaises(ValueError):
            L.force_limited_ground_speed(L.F_LIM, 0.0, S_R, C_R, CH_DR,
                                         DELTA_MAX, BOOST)
        with self.assertRaises(ValueError):
            L.force_limited_ground_speed(L.F_LIM, PEDAL_ARM, S_R, C_R,
                                         CH_DR, DELTA_MAX, 1.5)


class TestNosewheelSteeringAuthority(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: apply the nosewheel steering
    authority below the steering cutout speed with the friction-limited
    steering restoring moment at the nose gear."""

    def test_steering_moment_anchor_and_raises(self):
        """Step 3 anchor: mu 0.8 at the 0.09 nose gear load fraction on
        65000 kg at the 13.0 m arm gives a 596636.586 N m steering
        restoring moment, 1.355992 times the 440000 N m asymmetric
        moment: the steering out-moments the failed engine below the
        cutout. Non-positive inputs raise."""
        sm = L.steering_moment(65000.0, 0.09, 0.8, 13.0)
        self.assertAlmostEqual(sm, 596636.586, delta=1.0)
        self.assertAlmostEqual(sm / L.asym_yaw_moment_static(T_OP, Y_FAIL),
                               1.355992, delta=1e-5)
        with self.assertRaises(ValueError):
            L.steering_moment(0.0, 0.09, 0.8, 13.0)
        with self.assertRaises(ValueError):
            L.steering_moment(65000.0, 0.09, 0.0, 13.0)

    def test_steering_engaged_at_cutout_and_raises(self):
        """Step 3 cutout check: the steering is engaged at 36.8 m/s below
        the 40.0 m/s cutout (77.753780 kt) and disengaged at 40.0
        (boundary excluded) and at 42.0 m/s; negative or non-positive
        speeds raise."""
        self.assertTrue(L.steering_engaged(36.8, V_CUT))
        self.assertFalse(L.steering_engaged(40.0, V_CUT))
        self.assertFalse(L.steering_engaged(42.0, V_CUT))
        self.assertAlmostEqual(V_CUT / L.KT2MS, 77.753780, delta=0.01)
        with self.assertRaises(ValueError):
            L.steering_engaged(-1.0, V_CUT)
        with self.assertRaises(ValueError):
            L.steering_engaged(36.8, 0.0)


class TestRunClassificationAndVerdict(unittest.TestCase):
    """Steps 6 and 7 of the SKILL.md workflow: classify the run into the
    steering-held, departed, at-limit and with-margin classes and reduce
    the qualifying at-limit runs to the Vmcg verdict with the bracket
    consistency check."""

    def test_ground_run_class_boundary_strings(self):
        """Step 6 class boundaries: v_auth itself is at-limit (boundary
        included), v_force itself is with-margin, just below v_auth is
        departed and a steering-engaged run is steering-held, with the
        exact spec class strings; a non-positive run speed raises."""
        self.assertEqual(L.ground_run_class(True, 36.8, V_AUTH, V_FORCE),
                         "steering-held")
        self.assertEqual(L.ground_run_class(False, 62.28, V_AUTH, V_FORCE),
                         "departed")
        self.assertEqual(L.ground_run_class(False, V_AUTH, V_AUTH, V_FORCE),
                         "at-limit")
        self.assertEqual(L.ground_run_class(False, 64.134, V_AUTH, V_FORCE),
                         "at-limit")
        self.assertEqual(L.ground_run_class(False, V_FORCE, V_AUTH, V_FORCE),
                         "with-margin")
        self.assertEqual(L.ground_run_class(False, 69.5, V_AUTH, V_FORCE),
                         "with-margin")
        with self.assertRaises(ValueError):
            L.ground_run_class(False, 0.0, V_AUTH, V_FORCE)
        with self.assertRaises(ValueError):
            L.ground_run_class(False, 62.28, None, V_FORCE)

    def test_vmcg_verdict_worked_data_and_table(self):
        """Step 7 verdict on the worked seven-run data: vmcg_cas is
        63.042941 m/s (122.545674 kt), exactly the corrected speed of the
        slowest qualifying run R4, bracketed by v_departed_max 59.056038
        below and v_margin_min 67.054921 at or above it, counts 2/2/2/1,
        and the corrected run table matches the worked data within 1e-3
        per run (R5 is the TAS run at 64.133853)."""
        ver = verdict()
        self.assertAlmostEqual(ver["vmcg_cas"], 63.042941, delta=1e-3)
        self.assertAlmostEqual(ver["vmcg_cas"], ver["runs"][3]["corrected"],
                               delta=1e-9)
        self.assertAlmostEqual(ver["vmcg_knots"], 122.545674, delta=0.01)
        self.assertAlmostEqual(ver["v_departed_max"], 59.056038, delta=1e-3)
        self.assertAlmostEqual(ver["v_margin_min"], 67.054921, delta=1e-3)
        self.assertTrue(ver["bracket_ok"])
        self.assertEqual(ver["n_qualifying"], 2)
        self.assertEqual(ver["n_departed"], 2)
        self.assertEqual(ver["n_margin"], 2)
        self.assertEqual(ver["n_steering_held"], 1)
        expected = [("R1", 37.144469, "steering-held"),
                    ("R2", 52.400000, "departed"),
                    ("R3", 59.056038, "departed"),
                    ("R4", 63.042941, "at-limit"),
                    ("R5", 64.133853, "at-limit"),
                    ("R6", 67.054921, "with-margin"),
                    ("R7", 69.500000, "with-margin")]
        for got, (rid, corr, cls) in zip(ver["runs"], expected):
            self.assertEqual(got["id"], rid)
            self.assertEqual(got["class"], cls)
            self.assertAlmostEqual(got["corrected"], corr, delta=1e-3)

    def test_vmcg_verdict_single_sided_bracket_ok(self):
        """Step 7 bracket logic: removing the with-margin runs keeps
        bracket_ok True with a single-sided bracket and v_margin_min
        reported as None."""
        runs = [r for r in WORKED_RUNS if r["id"] not in ("R6", "R7")]
        ver = L.vmcg_verdict(runs, V_AUTH, V_FORCE, W_REF, FLAP_REF,
                             CL_0, CL_PER_DEG)
        self.assertIsNone(ver["v_margin_min"])
        self.assertTrue(ver["bracket_ok"])
        self.assertEqual(ver["n_margin"], 0)

    def test_vmcg_verdict_below_departed_max_flips_bracket(self):
        """Step 7 bracket logic: a qualifying verdict at or below the
        departed max flips bracket_ok to False; here a heavy R4 run at
        74000 kg corrects below the R3 departed speed."""
        runs = [dict(r) for r in WORKED_RUNS]
        runs[3]["weight"] = 74000.0
        ver = L.vmcg_verdict(runs, V_AUTH, V_FORCE, W_REF, FLAP_REF,
                             CL_0, CL_PER_DEG)
        self.assertLessEqual(ver["vmcg_cas"], ver["v_departed_max"])
        self.assertFalse(ver["bracket_ok"])
        self.assertEqual(ver["runs"][3]["class"], "at-limit")

    def test_vmcg_verdict_invalid_raises(self):
        """ValueError rejection: an empty run list and a list with no
        at-limit run (only departed) leave Vmcg undefined and raise."""
        with self.assertRaises(ValueError):
            L.vmcg_verdict([], V_AUTH, V_FORCE, W_REF, FLAP_REF, CL_0,
                           CL_PER_DEG)
        only_departed = [{"id": "D1", "speed": 52.4, "weight": 65000.0,
                          "flap": 15.0, "steering_on": False}]
        with self.assertRaises(ValueError):
            L.vmcg_verdict(only_departed, V_AUTH, V_FORCE, W_REF, FLAP_REF,
                           CL_0, CL_PER_DEG)


class TestDemonstrationChecksGuardsAndGates(unittest.TestCase):
    """Steps 8 and 9 of the SKILL.md workflow: check the demonstration at
    the verdict, apply the stall protection guard on the reference stall
    speed and gate the balanced-field V1 schedule against the
    demonstrated Vmcg."""

    def test_at_verdict_demonstration_checks(self):
        """Step 8 at-verdict check: at the verdict 63.042941 m/s the
        dynamic pressure is 2434.327597 Pa, the required deflection is
        below the 0.52360 rad rudder limit, the boosted pedal force
        601.071429 N sits within the 667 N limit with force_ok True and
        an authority margin of 0.753010 m/s over V_auth; the manual
        boost 1.0 variant reaches 1767.857143 N, exceeds the limit and
        force_ok is False, so the flight test cannot clear with the
        unboosted rudder."""
        ver = verdict()
        q = 0.5 * L.RHO_SL * ver["vmcg_cas"] ** 2
        self.assertAlmostEqual(q, 2434.327597, delta=1e-2)
        d = L.required_deflection(440000.0, q, S_V, L_V, CLV_DR)
        self.assertLess(d, DELTA_MAX)
        f_b = L.pedal_force(q, S_R, C_R, CH_DR, d, BOOST, PEDAL_ARM)
        f_m = L.pedal_force(q, S_R, C_R, CH_DR, d, 1.0, PEDAL_ARM)
        self.assertAlmostEqual(f_b, 601.071429, delta=1e-2)
        self.assertLessEqual(f_b, L.F_LIM)
        self.assertAlmostEqual(f_m, 1767.857143, delta=1e-2)
        self.assertGreater(f_m, L.F_LIM)
        self.assertAlmostEqual(ver["vmcg_cas"] - V_AUTH, 0.753010,
                               delta=1e-3)

    def test_stall_guard_check_verdict(self):
        """Step 8 stall protection guard on the reference stall speed:
        vs1 58.0 m/s gives guard_speed 60.9 m/s below the verdict,
        verdict stall-guard-ok and proximity 1.086947 below the 1.10
        threshold that keeps the guard relevant."""
        ver = verdict()
        g = L.stall_guard_check(ver["vmcg_cas"], 58.0)
        self.assertAlmostEqual(g["guard_speed"], 60.9, delta=1e-9)
        self.assertEqual(g["guard_verdict"], "stall-guard-ok")
        self.assertAlmostEqual(g["proximity"], 1.086947, delta=1e-5)
        self.assertLess(g["proximity"], 1.10)
        self.assertLess(g["guard_speed"], ver["vmcg_cas"])

    def test_stall_guard_governs_when_verdict_low(self):
        """Step 8 stall guard governs when the verdict fails to clear the
        1.05 Vs1 guard; zero speeds raise."""
        g = L.stall_guard_check(60.0, 58.0)
        self.assertEqual(g["guard_verdict"], "stall-guard-governs")
        with self.assertRaises(ValueError):
            L.stall_guard_check(0.0, 58.0)
        with self.assertRaises(ValueError):
            L.stall_guard_check(63.0, 0.0)

    def test_v1_gate_vmcg_gated_case(self):
        """Step 9 V1 gate: the scheduled balanced-field V1 61.5 m/s falls
        below the demonstrated Vmcg 63.042941, so v1_gate_met is False,
        the verdict is vmcg-gated with v1_required equal to the verdict
        (122.545674 kt) and the legal window [63.042941, 63.9] against
        the scheduled rotation speed is only 0.857059 m/s wide; the
        scheduled liftoff speed 66.4 m/s clears the verdict by
        3.357059 m/s, ratio 1.053250."""
        ver = verdict()
        vmcg = ver["vmcg_cas"]
        g = L.v1_gate(vmcg, 61.5, 63.9)
        self.assertFalse(g["v1_gate_met"])
        self.assertEqual(g["verdict"], "vmcg-gated")
        self.assertEqual(g["v1_required"], vmcg)
        self.assertAlmostEqual(g["v1_required"] / L.KT2MS, 122.545674,
                               delta=0.01)
        self.assertAlmostEqual(g["width"], 0.857059, delta=1e-5)
        self.assertAlmostEqual(66.4 - vmcg, 3.357059, delta=1e-3)
        self.assertAlmostEqual(66.4 / vmcg, 1.053250, delta=1e-5)

    def test_v1_gate_ok_and_infeasible_cases(self):
        """Step 9 V1 gate: V1 at or above Vmcg gives ok; a scheduled
        rotation speed below Vmcg gives schedule-infeasible (no legal V1
        below rotation exists); zero speeds raise."""
        ver = verdict()
        g_ok = L.v1_gate(ver["vmcg_cas"], 64.0, 63.9)
        self.assertTrue(g_ok["v1_gate_met"])
        self.assertEqual(g_ok["verdict"], "ok")
        g_inf = L.v1_gate(ver["vmcg_cas"], 61.5, 62.0)
        self.assertEqual(g_inf["verdict"], "schedule-infeasible")
        with self.assertRaises(ValueError):
            L.v1_gate(0.0, 61.5)
        with self.assertRaises(ValueError):
            L.v1_gate(63.042941, 0.0)
        with self.assertRaises(ValueError):
            L.v1_gate(63.042941, 61.5, 0.0)

    def test_windmilling_shift_reclassifies_runs(self):
        """Step 4 windmilling recheck: with s_f_cd 1.2 m2 the authority
        speed rises to 63.970485 m/s, so the R4 run (measured 62.8)
        reclasses from at-limit to departed while R5 (measured 64.134
        CAS) stays at-limit."""
        v_wm = L.authority_limited_ground_speed(T_OP, Y_FAIL, S_V, L_V,
                                                CLV_DR, DELTA_MAX,
                                                s_f_cd=1.2)
        self.assertEqual(L.ground_run_class(False, 62.8, v_wm, V_FORCE),
                         "departed")
        self.assertEqual(
            L.ground_run_class(False, L.tas_to_cas(67.4, 600.0, 12.0),
                               v_wm, V_FORCE), "at-limit")

    def test_constants_and_determinism(self):
        """Module invariants: EXP about 5.2559, KT2MS the exact knot
        factor, F_LIM 667.0, and the verdict reduction is deterministic
        across repeated runs."""
        self.assertAlmostEqual(L.EXP, 5.2559, delta=1e-3)
        self.assertEqual(L.KT2MS, 0.514444444444)
        self.assertEqual(L.F_LIM, 667.0)
        a = verdict()
        b = verdict()
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
