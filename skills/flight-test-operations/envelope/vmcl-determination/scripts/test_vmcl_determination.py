"""Contract test for vmcl-determination (flight-test-operations/envelope).

Exercises the SKILL.md workflow end to end: step 1 fixes the landing
configuration and atmosphere for the leg (most favorable or most
unfavorable reference approach weight, reference landing flap with the
landing-configuration lift coefficient model, ISA density ratio sigma),
steps 2 and 3 identify the first and second critical cuts and build the
asymmetric yawing moment of the cut over the operating engine set as the
engine-by-engine sum of the go-around thrusts at their signed arms,
steps 4 and 5 solve the rudder authority limited airspeed and the
pedal-force limited airspeed with the boost factor against the 667 N
(150 lbf) pedal force criterion, step 6 corrects each run speed to
standard conditions (calibrated airspeed correction, weight correction
to the leg reference weight, flap normalization through the
landing-configuration lift coefficient) and classifies the run into the
control-lost, at-limit and with-margin classes from the measured CAS
with the bank-5-degree and 20-degree-heading-change observed criteria,
step 7 reduces the qualifying at-limit runs to the demonstrated VMCL
verdict with the bracket consistency check against the control-lost and
with-margin brackets, step 8 combines the legs with the governing
(higher) demonstrated value, step 9 checks the demonstration at the
verdict (required deflection below the rudder limit, required pedal
force within the 667 N limit, authority margin, lateral control roll
demand check), and step 10 applies the stall protection guard on the
landing-configuration reference stall speed and the approach margin
check against the operating approach speed set.

Fact terms exercised: asymmetric yawing moment, go-around thrust,
critical-engine cut, second critical cut, rudder authority limited
airspeed, pedal-force limited airspeed, boost factor, 667 N pedal force
criterion, calibrated airspeed, most favorable weight, most unfavorable
weight, reference landing flap, landing-configuration lift coefficient,
control-lost run, at-limit run, with-margin run, VMCL verdict, bracket
consistency check, stall protection guard, lateral control roll demand,
operating approach speed set. Procedure terms exercised: fix, identify,
build, solve, correct, classify, reduce, combine, check, apply.

All anchors are real outputs of the spec worked example (the module's
own outputs under the quad reference condition set: most favorable
weight 170000 kg and most unfavorable weight 185000 kg at the reference
landing flap 25 deg with cl_0 0.90 and cl_per_deg 0.030 per deg).
Offline, deterministic, stdlib only; run with
python3 scripts/test_vmcl_determination.py and under the pre-push hook
interpreter. No exact-float equality on computed aggregates.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vmcl_determination_logic as L  # noqa: E402

# Worked example configuration (spec section, module constants).
W_REF_1 = 170000.0      # most favorable (minimum) approach weight, (f) leg
W_REF_2 = 185000.0      # most unfavorable (maximum) approach weight, (g) leg
FLAP_REF = 25.0
CL_0 = 0.90
CL_PER_DEG = 0.030
S_V = 42.0
L_V = 21.0
CLV_DR = 0.90
DELTA_MAX = math.radians(30.0)
S_R = 9.5
C_R = 1.5
CH_DR = 0.05
PEDAL_ARM = 0.35
BOOST = 0.20
VS0 = 52.7
V_APP_REF = 1.3 * VS0   # v-speeds model places it at 1.3*vs0

QUAD = [{"thrust_N": 96000.0, "y_m": -8.0},
        {"thrust_N": 96000.0, "y_m": -3.5},
        {"thrust_N": 96000.0, "y_m": 3.5},
        {"thrust_N": 96000.0, "y_m": 8.0}]
TWIN = [{"thrust_N": 96000.0, "y_m": -8.0},
        {"thrust_N": 96000.0, "y_m": 8.0}]
TRI = [{"thrust_N": 85000.0, "y_m": -7.5},
       {"thrust_N": 85000.0, "y_m": 0.0},
       {"thrust_N": 85000.0, "y_m": 7.5}]

N1 = L.post_cut_moment(QUAD, [0])
N2 = L.post_cut_moment(QUAD, [0, 1])
V_AUTH1 = L.authority_limited_airspeed(N1, 8.0, S_V, L_V, CLV_DR, DELTA_MAX)
V_AUTH2 = L.authority_limited_airspeed(N2, 3.5, S_V, L_V, CLV_DR, DELTA_MAX)
V_FORCE = L.force_limited_airspeed(L.F_LIM, PEDAL_ARM, S_R, C_R, CH_DR,
                                   DELTA_MAX, BOOST)

LEG1_RUNS = [
    {"id": "L1A", "speed": 52.8, "weight": 178000.0, "flap": 25.0,
     "bank_max_deg": 6.3, "heading_change_deg": 24.0},
    {"id": "L1B", "speed": 56.3, "weight": 175000.0, "flap": 25.0,
     "bank_max_deg": 3.1, "heading_change_deg": 12.0},
    {"id": "L1C", "speed": 58.0, "weight": 170000.0, "flap": 25.0,
     "bank_max_deg": 2.6, "heading_change_deg": 9.0},
    {"id": "L1D", "speed": 66.8, "weight": 172000.0, "flap": 25.0,
     "bank_max_deg": 2.2, "heading_change_deg": 7.0,
     "h_p": 500.0, "dt_isa": 8.0, "tas_input": True},
    {"id": "L1E", "speed": 72.5, "weight": 170000.0, "flap": 25.0,
     "bank_max_deg": 1.8, "heading_change_deg": 5.0},
    {"id": "L1F", "speed": 58.5, "weight": 170000.0, "flap": 20.0,
     "bank_max_deg": 3.0, "heading_change_deg": 11.0},
]
LEG2_RUNS = [
    {"id": "L2A", "speed": 64.5, "weight": 186000.0, "flap": 25.0,
     "bank_max_deg": 5.8, "heading_change_deg": 22.0},
    {"id": "L2B", "speed": 66.9, "weight": 185000.0, "flap": 25.0,
     "bank_max_deg": 3.4, "heading_change_deg": 13.0},
    {"id": "L2C", "speed": 68.4, "weight": 183000.0, "flap": 25.0,
     "bank_max_deg": 3.8, "heading_change_deg": 15.0},
    {"id": "L2D", "speed": 70.6, "weight": 185000.0, "flap": 25.0,
     "bank_max_deg": 4.2, "heading_change_deg": 16.0},
    {"id": "L2E", "speed": 73.5, "weight": 185000.0, "flap": 25.0,
     "bank_max_deg": 2.9, "heading_change_deg": 8.0},
]


def scenario():
    """Run the full worked scenario (steps 1 to 8 of the SKILL.md
    workflow: fix the reference conditions, identify the cuts, solve the
    limits, correct and classify, reduce to the verdicts, combine)."""
    v1 = L.leg_verdict(LEG1_RUNS, "vmcl-1", V_AUTH1, V_FORCE, W_REF_1,
                       FLAP_REF, CL_0, CL_PER_DEG)
    v2 = L.leg_verdict(LEG2_RUNS, "vmcl-2", V_AUTH2, V_FORCE, W_REF_2,
                       FLAP_REF, CL_0, CL_PER_DEG)
    return v1, v2, L.demonstration_summary(v1, v2)


class TestIsaAtmosphere(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: fix the landing configuration and
    atmosphere with the ISA density ratio sigma at the test pressure
    altitude and temperature deviation."""

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
        """ValueError rejection of step 1: pressure altitude outside
        [0, 11000] m and a non-positive ambient temperature raise."""
        with self.assertRaises(ValueError):
            L.isa_sigma(-1.0, 0.0)
        with self.assertRaises(ValueError):
            L.isa_sigma(12000.0, 0.0)
        with self.assertRaises(ValueError):
            L.isa_sigma(11000.0, -220.0)

    def test_tas_to_cas_warm_day_anchor_and_identity(self):
        """Step 1 airspeed correction: tas_to_cas(66.8, 500, 8) is
        64.310260 m/s through the sigma density ratio and degenerates to
        the input exactly at sea level standard conditions; a zero true
        airspeed raises."""
        self.assertAlmostEqual(L.tas_to_cas(66.8, 500.0, 8.0),
                               64.310260, delta=1e-3)
        self.assertEqual(L.tas_to_cas(66.8, 0.0, 0.0), 66.8)
        with self.assertRaises(ValueError):
            L.tas_to_cas(0.0, 0.0, 0.0)


class TestStandardConditionCorrections(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: correct each run speed to
    standard conditions with the weight correction to the leg reference
    weight (most favorable or most unfavorable approach weight) and the
    flap normalization through the landing-configuration lift
    coefficient."""

    def test_weight_corrected_anchors_and_same_weight(self):
        """Step 6 weight correction: v*sqrt(w_ref/w_test) gives 120.0
        from 60.0 at a 4:1 reference ratio, the worked (f) leg factor
        sqrt(170000/175000) is 0.985611, and the same-weight call
        returns the input exactly; a zero test weight raises."""
        self.assertAlmostEqual(L.weight_corrected_speed(60.0, 100.0, 400.0),
                               120.0, delta=1e-9)
        self.assertAlmostEqual(math.sqrt(W_REF_1 / 175000.0), 0.985611,
                               delta=1e-6)
        self.assertEqual(L.weight_corrected_speed(60.0, 170000.0, 170000.0),
                         60.0)
        with self.assertRaises(ValueError):
            L.weight_corrected_speed(60.0, 0.0, W_REF_1)

    def test_flap_normalized_anchor_round_trip_and_invalid(self):
        """Step 6 flap normalization through the landing-configuration
        lift coefficient CL(f) = cl_0 + cl_per_deg*f: 58.5 m/s at flap 20
        normalizes down to 55.777561 m/s at the reference landing flap
        25 (CL 1.500 to 1.650); the same-flap call returns the input, the
        20-to-25-to-20 round trip returns 58.5 within 1e-9, and a
        negative flap or a zero cl_0 raises."""
        self.assertAlmostEqual(
            L.flap_normalized_speed(58.5, 20.0, FLAP_REF, CL_0, CL_PER_DEG),
            55.777561, delta=1e-3)
        v = 58.5
        self.assertEqual(L.flap_normalized_speed(v, FLAP_REF, FLAP_REF,
                                                 CL_0, CL_PER_DEG), v)
        down = L.flap_normalized_speed(v, 20.0, 25.0, CL_0, CL_PER_DEG)
        back = L.flap_normalized_speed(down, 25.0, 20.0, CL_0, CL_PER_DEG)
        self.assertAlmostEqual(back, v, delta=1e-9)
        with self.assertRaises(ValueError):
            L.flap_normalized_speed(58.5, -1.0, 25.0, CL_0, CL_PER_DEG)
        with self.assertRaises(ValueError):
            L.flap_normalized_speed(58.5, 20.0, 25.0, 0.0, CL_PER_DEG)

    def test_corrected_run_speed_tas_chain_anchor(self):
        """Step 6 full reduction: corrected_run_speed on the L1D side
        (TAS 66.8 at 500 m +8 K to the most favorable weight 170000 kg
        at the reference flap) equals the manual chain
        weight_corrected_speed(tas_to_cas(66.8, 500, 8), ...) with a
        unit flap factor, 63.935270 m/s."""
        c = L.corrected_run_speed(66.8, 172000.0, W_REF_1, 25.0, FLAP_REF,
                                  CL_0, CL_PER_DEG, 500.0, 8.0,
                                  tas_input=True)
        self.assertAlmostEqual(c, 63.935270, delta=1e-3)
        manual = L.weight_corrected_speed(
            L.tas_to_cas(66.8, 500.0, 8.0), 172000.0, W_REF_1)
        self.assertAlmostEqual(c, manual, delta=1e-9)

    def test_corrected_run_speed_cas_path_and_raises(self):
        """Step 6 CAS path: a calibrated airspeed input at the reference
        weight and flap needs no correction (L1C returns 58.0 exactly),
        while the flap-20 run L1F corrects to 55.777561; a non-positive
        measured speed raises."""
        self.assertEqual(L.corrected_run_speed(58.0, 170000.0, W_REF_1,
                                               25.0, FLAP_REF, CL_0,
                                               CL_PER_DEG), 58.0)
        c = L.corrected_run_speed(58.5, 170000.0, W_REF_1, 20.0, FLAP_REF,
                                  CL_0, CL_PER_DEG)
        self.assertAlmostEqual(c, 55.777561, delta=1e-3)
        with self.assertRaises(ValueError):
            L.corrected_run_speed(0.0, 170000.0, W_REF_1, 25.0, FLAP_REF,
                                  CL_0, CL_PER_DEG)


class TestCutSelectionAndMoments(unittest.TestCase):
    """Steps 2 and 3 of the SKILL.md workflow: identify the first and
    second critical cuts and build the asymmetric yawing moment of the
    cut over the operating engine set (the engine-by-engine sum of the
    go-around thrusts at their signed lateral arms, the cut engines
    contributing nothing)."""

    def test_post_cut_moment_quad_first_and_second_cut(self):
        """Step 2 moment anchor: cutting the outer left engine (index 0)
        of the worked quad leaves 768000.0 N m over the operating set;
        the second critical cut of the same-side inner engine (index 1
        with index 0 out) leaves 1104000.0 N m (96000 * 11.5)."""
        self.assertAlmostEqual(N1, 768000.0, delta=1e-6)
        self.assertAlmostEqual(N2, 1104000.0, delta=1e-6)

    def test_first_and_second_cut_indices_quad(self):
        """Steps 2 and 3: on the equal-thrust symmetric quad the first
        critical cut is index 0 (outer left) and, with it inoperative,
        the second critical cut is index 1 (the same-side inner engine,
        whose loss leaves the residual outboard moment)."""
        self.assertEqual(L.first_cut_index(QUAD), 0)
        self.assertEqual(L.second_cut_index(QUAD, 0), 1)

    def test_twin_identity_family_static_form(self):
        """Step 2 shared-core identity: for two equal-thrust symmetric
        engines the engine-sum moment equals the family static form
        T_op*|y_fail| exactly (768000.0 N m on both sides), the identity
        the vmc and vmcg siblings exercise."""
        n = L.post_cut_moment(TWIN, [0])
        self.assertAlmostEqual(n, 768000.0, delta=1e-6)
        self.assertAlmostEqual(n, 96000.0 * 8.0, delta=1e-6)

    def test_quad_contrast_resultant_convention_deviation(self):
        """Step 2 deviation record: on the four-engine layout the
        engine-set sum gives 768000.0 N m for the first cut while the
        T_op*|y_fail| resultant convention of the sibling logic files
        (288000 N of operating thrust at the 8.0 m cut arm) gives
        2304000.0 N m; the engine set sum is the pinned multi-engine
        form here."""
        self.assertAlmostEqual(N1, 768000.0, delta=1e-6)
        resultant = 288000.0 * 8.0
        self.assertAlmostEqual(resultant, 2304000.0, delta=1e-6)
        self.assertNotAlmostEqual(N1, resultant, delta=1e-3)

    def test_tri_jet_second_cut_tail_engine_identity(self):
        """Step 3 tri-jet identity: for the three-engine layout with wing
        engines at +-7.5 m and the centerline tail engine at y = 0 the
        second critical cut is the tail engine (index 1) and the VMCL-2
        moment equals the VMCL-1 moment exactly (637500.0 N m both
        legs), the case the engine-set sum exists for."""
        self.assertEqual(L.first_cut_index(TRI), 0)
        self.assertEqual(L.second_cut_index(TRI, 0), 1)
        m1 = L.post_cut_moment(TRI, [0])
        m2 = L.post_cut_moment(TRI, [0, 1])
        self.assertAlmostEqual(m1, 637500.0, delta=1e-6)
        self.assertAlmostEqual(m2, 637500.0, delta=1e-6)
        self.assertAlmostEqual(m2, m1, delta=1e-9)

    def test_cut_selection_value_errors(self):
        """ValueError rejection of steps 2 and 3: an empty engine list,
        an empty cut set, an out-of-range cut index, a non-positive
        go-around thrust and a second critical cut on a twin layout
        raise."""
        with self.assertRaises(ValueError):
            L.post_cut_moment([], [0])
        with self.assertRaises(ValueError):
            L.post_cut_moment(QUAD, [])
        with self.assertRaises(ValueError):
            L.post_cut_moment(QUAD, [4])
        with self.assertRaises(ValueError):
            L.post_cut_moment([{"thrust_N": 0.0, "y_m": 8.0}], [0])
        with self.assertRaises(ValueError):
            L.second_cut_index(TWIN, 0)


class TestAuthorityAndForceLimits(unittest.TestCase):
    """Steps 4 and 5 of the SKILL.md workflow: solve the rudder authority
    limited airspeed from the closed form and the pedal-force limited
    airspeed with the boost factor against the 667 N (150 lbf) pedal
    force criterion."""

    def test_authority_limited_airspeed_first_cut_anchor(self):
        """Step 4 anchor: the authority limit of the first-cut leg is
        54.925334 m/s (106.766308 kt), the airspeed where the required
        deflection reaches the 30 deg rudder limit under the first-cut
        moment; below it the rudder cannot balance within the 5 degree
        bank allowance."""
        self.assertAlmostEqual(V_AUTH1, 54.925334, delta=1e-3)
        self.assertAlmostEqual(V_AUTH1 / L.KT2MS, 106.766308, delta=0.01)

    def test_authority_limited_airspeed_second_cut_ratio(self):
        """Step 4 second-cut boundary: V_auth2 is 65.853162 m/s
        (128.008306 kt) and exceeds V_auth1 by the sqrt of the moment
        ratio sqrt(11.5/8) = 1.198957 within 1e-5, so the second-cut leg
        is the harder demonstration for the quad."""
        self.assertAlmostEqual(V_AUTH2, 65.853162, delta=1e-3)
        self.assertAlmostEqual(V_AUTH2 / L.KT2MS, 128.008306, delta=0.01)
        self.assertAlmostEqual(V_AUTH2 / V_AUTH1, math.sqrt(11.5 / 8.0),
                               delta=1e-5)
        self.assertAlmostEqual(V_AUTH2 / V_AUTH1, 1.198957, delta=1e-5)

    def test_authority_limited_airspeed_invalid(self):
        """Step 4 ValueError rejection: a rudder limit at 61 deg, a zero
        cut arm, a non-positive moment and a negative windmilling drag
        area raise; a non-positive authority denominator returns None."""
        with self.assertRaises(ValueError):
            L.authority_limited_airspeed(N1, 8.0, S_V, L_V, CLV_DR,
                                         math.radians(61.0))
        with self.assertRaises(ValueError):
            L.authority_limited_airspeed(N1, 0.0, S_V, L_V, CLV_DR,
                                         DELTA_MAX)
        with self.assertRaises(ValueError):
            L.authority_limited_airspeed(0.0, 8.0, S_V, L_V, CLV_DR,
                                         DELTA_MAX)
        with self.assertRaises(ValueError):
            L.authority_limited_airspeed(N1, 8.0, S_V, L_V, CLV_DR,
                                         DELTA_MAX, s_f_cd=-1.0)
        self.assertIsNone(L.authority_limited_airspeed(
            N1, 8.0, S_V, L_V, CLV_DR, DELTA_MAX, s_f_cd=1000.0))

    def test_force_limited_airspeed_anchor(self):
        """Step 5 anchor: the force-limited airspeed is 71.472200 m/s
        (138.930842 kt) at boost 0.20, leg-independent (it depends only
        on the rudder geometry and the boost factor); a boost outside
        (0, 1] raises."""
        self.assertAlmostEqual(V_FORCE, 71.472200, delta=1e-3)
        self.assertAlmostEqual(V_FORCE / L.KT2MS, 138.930842, delta=0.01)
        self.assertAlmostEqual(
            L.force_limited_airspeed(L.F_LIM, PEDAL_ARM, S_R, C_R, CH_DR,
                                     DELTA_MAX, BOOST),
            L.force_limited_airspeed(L.F_LIM, PEDAL_ARM, S_R, C_R, CH_DR,
                                     DELTA_MAX, BOOST), delta=1e-12)
        with self.assertRaises(ValueError):
            L.force_limited_airspeed(L.F_LIM, PEDAL_ARM, S_R, C_R, CH_DR,
                                     DELTA_MAX, 1.5)

    def test_required_deflection_and_full_deflection_pedal_force(self):
        """Steps 4, 5 and 9: at the leg-2 verdict dynamic pressure
        2741.311125 Pa the required deflection to balance 1104000 N m is
        0.507341 rad (29.068477 deg) below the 0.523599 rad limit, and
        the full-deflection pedal force at that q is 584.391339 N within
        the 667 N limit; the deflection scales inverse to q."""
        q = 0.5 * L.RHO_SL * 66.9 ** 2
        self.assertAlmostEqual(q, 2741.311125, delta=1e-2)
        d = L.required_deflection(N2, q, S_V, L_V, CLV_DR)
        self.assertAlmostEqual(d, 0.507341, delta=1e-5)
        self.assertAlmostEqual(math.degrees(d), 29.068477, delta=1e-3)
        self.assertLess(d, DELTA_MAX)
        f_full = L.pedal_force(q, S_R, C_R, CH_DR, DELTA_MAX, BOOST,
                               PEDAL_ARM)
        self.assertAlmostEqual(f_full, 584.391339, delta=1e-2)
        self.assertLessEqual(f_full, L.F_LIM)
        d2 = L.required_deflection(N2, 2.0 * q, S_V, L_V, CLV_DR)
        self.assertAlmostEqual(d2, 0.5 * d, delta=1e-12)
        with self.assertRaises(ValueError):
            L.required_deflection(0.0, q, S_V, L_V, CLV_DR)
        with self.assertRaises(ValueError):
            L.pedal_force(q, S_R, C_R, CH_DR, DELTA_MAX, 0.0, PEDAL_ARM)


class TestRunClasses(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: classify each approach-cut run
    from the measured CAS with the bank-5-degree and 20-degree-heading-
    change observed recovery criteria."""

    def test_class_boundaries_and_exact_strings(self):
        """Step 6 class boundaries: V_auth itself is at-limit (boundary
        included), V_auth - 0.01 is control-lost, V_force itself is
        with-margin (boundary included), and the three class strings are
        exactly the spec strings control-lost, at-limit, with-margin."""
        self.assertEqual(L.approach_run_class(V_AUTH1, V_AUTH1, V_FORCE),
                         "at-limit")
        self.assertEqual(L.approach_run_class(V_AUTH2, V_AUTH2, V_FORCE),
                         "at-limit")
        self.assertEqual(L.approach_run_class(V_AUTH1 - 0.01, V_AUTH1,
                                              V_FORCE), "control-lost")
        self.assertEqual(L.approach_run_class(V_FORCE, V_AUTH1, V_FORCE),
                         "with-margin")
        self.assertEqual(L.approach_run_class(60.0, V_AUTH1, V_FORCE),
                         "at-limit")
        self.assertEqual(L.approach_run_class(75.0, V_AUTH1, V_FORCE),
                         "with-margin")

    def test_observed_criteria_violation_overrides(self):
        """Step 6 override rule: an observed bank beyond 5 degrees or a
        recovery heading change beyond 20 degrees overrides at-limit and
        with-margin speeds to control-lost (bank 5.8 / heading 23 at 70.0
        and bank 6.1 / heading 19 at 60.0), while observed compliance
        never overrides a speed-based loss."""
        self.assertEqual(L.approach_run_class(70.0, V_AUTH1, V_FORCE,
                                              bank_max_deg=5.8,
                                              heading_change_deg=23.0),
                         "control-lost")
        self.assertEqual(L.approach_run_class(60.0, V_AUTH1, V_FORCE,
                                              bank_max_deg=6.1,
                                              heading_change_deg=19.0),
                         "control-lost")
        self.assertEqual(L.approach_run_class(60.0, V_AUTH1, V_FORCE,
                                              bank_max_deg=3.0,
                                              heading_change_deg=24.0),
                         "control-lost")
        self.assertEqual(L.approach_run_class(60.0, V_AUTH1, V_FORCE,
                                              bank_max_deg=4.9,
                                              heading_change_deg=19.0),
                         "at-limit")
        self.assertEqual(L.approach_run_class(75.0, V_AUTH1, V_FORCE,
                                              bank_max_deg=3.0,
                                              heading_change_deg=5.0),
                         "with-margin")

    def test_class_invalid_inputs_raise(self):
        """Step 6 ValueError rejection: a non-positive run speed and
        None or non-positive authority and force limits raise."""
        with self.assertRaises(ValueError):
            L.approach_run_class(0.0, V_AUTH1, V_FORCE)
        with self.assertRaises(ValueError):
            L.approach_run_class(60.0, None, V_FORCE)
        with self.assertRaises(ValueError):
            L.approach_run_class(60.0, V_AUTH1, 0.0)


class TestLegVerdicts(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: reduce the qualifying at-limit
    runs of each leg to the demonstrated VMCL verdict with the bracket
    consistency check against the control-lost and with-margin
    brackets."""

    def test_leg1_verdict_anchors(self):
        """Step 7 leg-1 verdict (25.149(f), most favorable weight 170000
        kg): vmcl_1 is 55.489886 m/s (107.863709 KCAS), exactly the
        corrected speed of the slowest qualifying run L1B, with
        v_lost_max 51.599843 below the verdict and v_margin_min
        72.500000 at or above it, bracket_ok True and counts 4
        qualifying, 1 lost, 1 margin."""
        v1 = L.leg_verdict(LEG1_RUNS, "vmcl-1", V_AUTH1, V_FORCE, W_REF_1,
                           FLAP_REF, CL_0, CL_PER_DEG)
        self.assertAlmostEqual(v1["vmcl_cas"], 55.489886, delta=1e-3)
        l1b = L.corrected_run_speed(56.3, 175000.0, W_REF_1, 25.0, FLAP_REF,
                                    CL_0, CL_PER_DEG)
        self.assertAlmostEqual(v1["vmcl_cas"], l1b, delta=1e-9)
        self.assertAlmostEqual(v1["vmcl_knots"], 107.863709, delta=0.01)
        self.assertAlmostEqual(v1["v_lost_max"], 51.599843, delta=1e-3)
        self.assertAlmostEqual(v1["v_margin_min"], 72.500000, delta=1e-3)
        self.assertLess(v1["v_lost_max"], v1["vmcl_cas"])
        self.assertLessEqual(v1["vmcl_cas"], v1["v_margin_min"])
        self.assertTrue(v1["bracket_ok"])
        self.assertEqual((v1["n_qualifying"], v1["n_lost"], v1["n_margin"]),
                         (4, 1, 1))

    def test_leg1_corrected_run_table(self):
        """Step 7 leg-1 corrected run table: the six leg-1 runs correct
        to 51.599843 (control-lost, observed bank and heading beyond the
        criteria), 55.489886, 58.000000, 63.935270 (the TAS run at 500 m
        +8 K), 72.500000 (with-margin) and 55.777561 (the flap-20 run
        normalized down to the reference landing flap), each within
        1e-3."""
        v1 = L.leg_verdict(LEG1_RUNS, "vmcl-1", V_AUTH1, V_FORCE, W_REF_1,
                           FLAP_REF, CL_0, CL_PER_DEG)
        expected = [("L1A", "control-lost", 51.599843),
                    ("L1B", "at-limit", 55.489886),
                    ("L1C", "at-limit", 58.000000),
                    ("L1D", "at-limit", 63.935270),
                    ("L1E", "with-margin", 72.500000),
                    ("L1F", "at-limit", 55.777561)]
        self.assertEqual(len(v1["runs"]), 6)
        for run, (rid, cls, corr) in zip(v1["runs"], expected):
            self.assertEqual(run["id"], rid)
            self.assertEqual(run["class"], cls)
            self.assertAlmostEqual(run["corrected"], corr, delta=1e-3)

    def test_leg2_verdict_anchors(self):
        """Step 7 leg-2 verdict (25.149(g), most unfavorable weight
        185000 kg): vmcl_2 is 66.900000 m/s (130.043197 KCAS), exactly
        the corrected speed of the slowest qualifying run L2B, with
        v_lost_max 64.326379 below the verdict and v_margin_min
        73.500000 at or above it, bracket_ok True and counts 3
        qualifying, 1 lost, 1 margin."""
        v2 = L.leg_verdict(LEG2_RUNS, "vmcl-2", V_AUTH2, V_FORCE, W_REF_2,
                           FLAP_REF, CL_0, CL_PER_DEG)
        self.assertAlmostEqual(v2["vmcl_cas"], 66.900000, delta=1e-3)
        l2b = L.corrected_run_speed(66.9, 185000.0, W_REF_2, 25.0, FLAP_REF,
                                    CL_0, CL_PER_DEG)
        self.assertAlmostEqual(v2["vmcl_cas"], l2b, delta=1e-9)
        self.assertAlmostEqual(v2["vmcl_knots"], 130.043197, delta=0.01)
        self.assertAlmostEqual(v2["v_lost_max"], 64.326379, delta=1e-3)
        self.assertAlmostEqual(v2["v_margin_min"], 73.500000, delta=1e-3)
        self.assertLess(v2["v_lost_max"], v2["vmcl_cas"])
        self.assertLessEqual(v2["vmcl_cas"], v2["v_margin_min"])
        self.assertTrue(v2["bracket_ok"])
        self.assertEqual((v2["n_qualifying"], v2["n_lost"], v2["n_margin"]),
                         (3, 1, 1))

    def test_leg2_corrected_run_table(self):
        """Step 7 leg-2 corrected run table: the five leg-2 runs correct
        to 64.326379 (control-lost, observed bank 5.8 beyond the
        criterion), 66.900000, 68.772755, 70.600000 (at-limit) and
        73.500000 (with-margin), each within 1e-3."""
        v2 = L.leg_verdict(LEG2_RUNS, "vmcl-2", V_AUTH2, V_FORCE, W_REF_2,
                           FLAP_REF, CL_0, CL_PER_DEG)
        expected = [("L2A", "control-lost", 64.326379),
                    ("L2B", "at-limit", 66.900000),
                    ("L2C", "at-limit", 68.772755),
                    ("L2D", "at-limit", 70.600000),
                    ("L2E", "with-margin", 73.500000)]
        self.assertEqual(len(v2["runs"]), 5)
        for run, (rid, cls, corr) in zip(v2["runs"], expected):
            self.assertEqual(run["id"], rid)
            self.assertEqual(run["class"], cls)
            self.assertAlmostEqual(run["corrected"], corr, delta=1e-3)

    def test_single_sided_bracket_and_flipped_bracket(self):
        """Step 7 bracket logic: removing the with-margin runs keeps
        bracket_ok True (single-sided brackets allowed), while a
        manufactured verdict at or below the control-lost max flips
        bracket_ok False."""
        no_margin = [r for r in LEG1_RUNS if r["id"] != "L1E"]
        v1 = L.leg_verdict(no_margin, "vmcl-1", V_AUTH1, V_FORCE, W_REF_1,
                           FLAP_REF, CL_0, CL_PER_DEG)
        self.assertTrue(v1["bracket_ok"])
        self.assertIsNone(v1["v_margin_min"])
        self.assertAlmostEqual(v1["vmcl_cas"], 55.489886, delta=1e-3)
        flipped = [
            {"id": "F1", "speed": 60.0, "weight": 170000.0, "flap": 25.0,
             "bank_max_deg": 6.0, "heading_change_deg": 12.0},
            {"id": "F2", "speed": 55.5, "weight": 170000.0, "flap": 25.0,
             "bank_max_deg": 3.0, "heading_change_deg": 10.0},
        ]
        vf = L.leg_verdict(flipped, "vmcl-1", V_AUTH1, V_FORCE, W_REF_1,
                           FLAP_REF, CL_0, CL_PER_DEG)
        self.assertFalse(vf["bracket_ok"])
        self.assertGreater(vf["v_lost_max"], vf["vmcl_cas"])

    def test_leg_verdict_raises(self):
        """Step 7 ValueError rejection: an empty run list and a run list
        whose only run is control-lost (no at-limit run, VMCL undefined
        by the data) raise."""
        with self.assertRaises(ValueError):
            L.leg_verdict([], "vmcl-1", V_AUTH1, V_FORCE, W_REF_1, FLAP_REF,
                          CL_0, CL_PER_DEG)
        only_lost = [{"id": "X1", "speed": 52.0, "weight": 170000.0,
                      "flap": 25.0, "bank_max_deg": 6.0,
                      "heading_change_deg": 8.0}]
        with self.assertRaises(ValueError):
            L.leg_verdict(only_lost, "vmcl-1", V_AUTH1, V_FORCE, W_REF_1,
                          FLAP_REF, CL_0, CL_PER_DEG)


class TestDemonstrationSummary(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: combine the legs, the governing
    leg carries the higher demonstrated value."""

    def test_combined_summary_governing_leg(self):
        """Step 8 combined demonstrated VMCL: the governing leg carries
        the higher demonstrated value, vmcl = 66.900000 m/s (130.043197
        KCAS) from leg 2 with governing_leg "vmcl-2"; with only the
        leg-1 verdict the summary returns 55.489886 and "vmcl-1"."""
        _, v2, summary = scenario()
        self.assertAlmostEqual(summary["vmcl_cas"], 66.900000, delta=1e-9)
        self.assertAlmostEqual(summary["vmcl_knots"], 130.043197, delta=0.01)
        self.assertEqual(summary["governing_leg"], "vmcl-2")
        self.assertGreater(summary["vmcl_cas"], v2["vmcl_cas"] - 1.0)
        v1 = L.leg_verdict(LEG1_RUNS, "vmcl-1", V_AUTH1, V_FORCE, W_REF_1,
                           FLAP_REF, CL_0, CL_PER_DEG)
        single = L.demonstration_summary(v1)
        self.assertAlmostEqual(single["vmcl_cas"], 55.489886, delta=1e-3)
        self.assertEqual(single["governing_leg"], "vmcl-1")


class TestAtVerdictChecks(unittest.TestCase):
    """Step 9 of the SKILL.md workflow: check the demonstration at the
    verdict, required deflection below the rudder limit, required pedal
    force within the 667 N limit and the authority margin."""

    def test_at_verdict_checks_leg2(self):
        """Step 9 leg-2 at-verdict check: q 2741.311125 Pa, required
        deflection 0.507341 rad (29.068477 deg) below the 0.523599 rad
        limit, required pedal force 566.245546 N within the 667 N limit
        (force_ok), and the authority margin vmcl - V_auth2 = 1.046838
        m/s above the analytic second-cut boundary."""
        _, v2, _ = scenario()
        q = 0.5 * L.RHO_SL * v2["vmcl_cas"] ** 2
        self.assertAlmostEqual(q, 2741.311125, delta=1e-2)
        d = L.required_deflection(N2, q, S_V, L_V, CLV_DR)
        self.assertAlmostEqual(d, 0.507341, delta=1e-5)
        self.assertAlmostEqual(math.degrees(d), 29.068477, delta=1e-3)
        self.assertLess(d, DELTA_MAX)
        f = L.pedal_force(q, S_R, C_R, CH_DR, d, BOOST, PEDAL_ARM)
        self.assertAlmostEqual(f, 566.245546, delta=1e-2)
        self.assertLessEqual(f, L.F_LIM)
        margin = v2["vmcl_cas"] - V_AUTH2
        self.assertAlmostEqual(margin, 1.046838, delta=1e-5)

    def test_at_verdict_checks_leg1(self):
        """Step 9 leg-1 at-verdict check: q 1885.965550 Pa, required
        deflection 0.512999 rad (29.392668 deg) below the limit,
        required pedal force 393.909945 N within the 667 N limit, and
        the authority margin vmcl_1 - V_auth1 = 0.564552 m/s."""
        v1 = L.leg_verdict(LEG1_RUNS, "vmcl-1", V_AUTH1, V_FORCE, W_REF_1,
                           FLAP_REF, CL_0, CL_PER_DEG)
        q = 0.5 * L.RHO_SL * v1["vmcl_cas"] ** 2
        self.assertAlmostEqual(q, 1885.965550, delta=1e-2)
        d = L.required_deflection(N1, q, S_V, L_V, CLV_DR)
        self.assertAlmostEqual(d, 0.512999, delta=1e-5)
        self.assertAlmostEqual(math.degrees(d), 29.392668, delta=1e-3)
        self.assertLess(d, DELTA_MAX)
        f = L.pedal_force(q, S_R, C_R, CH_DR, d, BOOST, PEDAL_ARM)
        self.assertAlmostEqual(f, 393.909945, delta=1e-2)
        self.assertLessEqual(f, L.F_LIM)
        margin = v1["vmcl_cas"] - V_AUTH1
        self.assertAlmostEqual(margin, 0.564552, delta=1e-5)


class TestStallGuardLateralMargin(unittest.TestCase):
    """Step 10 of the SKILL.md workflow: apply the stall protection guard
    on the landing-configuration reference stall speed, the lateral
    control roll demand check and the approach margin check against the
    operating approach speed set."""

    def test_stall_guard_check(self):
        """Step 10 stall guard: guard_speed 1.05*52.7 = 55.335000 m/s
        clears the governing verdict (stall-guard-ok, proximity
        1.269450), while the leg-1 proximity 1.052939 sits below the
        1.10 threshold that keeps the guard relevant."""
        g = L.stall_guard_check(66.9, VS0)
        self.assertAlmostEqual(g["guard_speed"], 55.335000, delta=1e-9)
        self.assertEqual(g["guard_verdict"], "stall-guard-ok")
        self.assertAlmostEqual(g["proximity"], 1.269450, delta=1e-5)
        g1 = L.stall_guard_check(55.489886, VS0)
        self.assertEqual(g1["guard_verdict"], "stall-guard-ok")
        self.assertAlmostEqual(g1["proximity"], 1.052939, delta=1e-5)
        self.assertLess(g1["proximity"], 1.10)
        with self.assertRaises(ValueError):
            L.stall_guard_check(0.0, VS0)
        with self.assertRaises(ValueError):
            L.stall_guard_check(66.9, 0.0)

    def test_lateral_control_check(self):
        """Step 9 lateral control: the required average roll rate is
        20/5 = 4.000000 deg/s and the available 4.8 deg/s clears it
        (lateral-control-ok), while 3.5 deg/s is
        lateral-control-insufficient; a zero available rate raises."""
        ok = L.lateral_control_check(4.8)
        self.assertAlmostEqual(ok["required_rate_deg_s"], 4.000000,
                               delta=1e-9)
        self.assertEqual(ok["verdict"], "lateral-control-ok")
        bad = L.lateral_control_check(3.5)
        self.assertEqual(bad["verdict"], "lateral-control-insufficient")
        with self.assertRaises(ValueError):
            L.lateral_control_check(0.0)

    def test_approach_margin_check(self):
        """Step 10 approach margin: v_app_ref 68.510000 m/s (1.3*52.7)
        clears the demonstrated VMCL with ratio 1.024066 and clearance
        1.610000 m/s (margin-ok), while 66.3 m/s gives vmcl-governs with
        v_app_required 66.9; zero speeds raise."""
        m = L.approach_margin_check(66.9, V_APP_REF)
        self.assertTrue(m["margin_ok"])
        self.assertEqual(m["verdict"], "margin-ok")
        self.assertAlmostEqual(m["ratio"], 1.024066, delta=1e-5)
        self.assertAlmostEqual(m["clearance"], 1.610000, delta=1e-6)
        g = L.approach_margin_check(66.9, 66.3)
        self.assertFalse(g["margin_ok"])
        self.assertEqual(g["verdict"], "vmcl-governs")
        self.assertAlmostEqual(g["v_app_required"], 66.9, delta=1e-9)
        with self.assertRaises(ValueError):
            L.approach_margin_check(0.0, V_APP_REF)
        with self.assertRaises(ValueError):
            L.approach_margin_check(66.9, 0.0)


class TestDeterminismAndConstants(unittest.TestCase):
    """Module-level guarantees: deterministic closed form, fixed
    constants, no imports beyond math."""

    def test_determinism_two_full_runs_identical(self):
        """Two full runs of the worked scenario (steps 1 to 8: fix the
        reference conditions, identify the cuts, solve the limits,
        correct and classify, reduce, combine) produce byte-identical
        verdict output."""
        v1a, v2a, sa = scenario()
        v1b, v2b, sb = scenario()
        self.assertEqual(repr((v1a, v2a, sa)), repr((v1b, v2b, sb)))

    def test_module_constants(self):
        """Module constants are fixed: EXP about 5.2559, KT2MS
        0.514444444444, F_LIM 667.0, BANK_LIM_DEG 5.0, HEADING_LIM_DEG
        20.0, ROLL_DEG 20.0, ROLL_TIME_S 5.0 and STALL_GUARD 1.05."""
        self.assertAlmostEqual(L.EXP, 5.2559, delta=1e-3)
        self.assertAlmostEqual(L.KT2MS, 0.514444444444, delta=1e-12)
        self.assertAlmostEqual(L.KT2MS, 1852.0 / 3600.0, delta=1e-12)
        self.assertEqual(L.F_LIM, 667.0)
        self.assertEqual(L.BANK_LIM_DEG, 5.0)
        self.assertEqual(L.HEADING_LIM_DEG, 20.0)
        self.assertEqual(L.ROLL_DEG, 20.0)
        self.assertEqual(L.ROLL_TIME_S, 5.0)
        self.assertEqual(L.STALL_GUARD, 1.05)


if __name__ == "__main__":
    unittest.main()
