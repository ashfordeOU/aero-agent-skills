"""Contract test for flight-test-operations/performance/
rotorcraft-height-velocity-diagram-test.

Exercises the SKILL.md height-velocity demonstration reduction workflow:
step 1 fix the demonstration record (speed, starting height, trace marks),
step 2 measure the engine-failure recognition delay, step 3 measure the
establishment and flare times, step 4 split the measured height loss into
the loss to the flare and the flare recovery altitude, step 5 give the
touchdown verdict, step 6 apply the reaction time allowance, step 7
interpolate the height-velocity boundary height, step 8 build the measured
avoid-region map, step 9 judge clearance against the predicted
height-velocity diagram, and step 10 confirm with this contract test.

The record side embeds the documented deterministic trace generator of the
spec worked example (generator side only; the leaf module reads measured
marks and never contains the generator): after the engine-failure event at
t = 0 the sink rate ramps linearly from 0 to the recognition-window end
sink over the recognition delay, then to the steady autorotative sink over
the establishment time; a demonstration whose height runs out in either
phase touches down during establishment; otherwise the flare begins at the
declared minimum flare altitude (or at the height available when it is
below that) and bleeds the sink to the touchdown value at the measured
flare deceleration. All asserted values are the real prep outputs of the
wave-43 anchor /tmp/w43spec/anchor_hvtest.py (stdlib math, exit 0), which
replicates these module functions exactly.

Pure stdlib, offline, deterministic, no randomness, no exact-float asserts
on computed aggregates (order-safe deltas only).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rotorcraft_height_velocity_diagram_test_logic import (  # noqa: E402
    REACTION_ALLOWANCE_S,
    SAFE_TOUCHDOWN_FPM,
    build_avoid_map,
    clearance_verdict,
    flare_recovery_altitude,
    height_lost_to_flare,
    interpolate_boundary_height,
    recognition_delay,
    recognition_loss_with_allowance,
    time_to_establish_autorotation,
    touchdown_verdict,
)

# ---------------------------------------------------------------------------
# Generator-side representative demonstration record (worked example of the
# SKILL.md; quoted-input steady autorotative sink values come from the
# flight-mechanics autorotative-descent analytic leaf, never re-derived).
# ---------------------------------------------------------------------------

SPEEDS_KT = [0.0, 10.0, 20.0, 30.0, 40.0]
TAU_R_S = {0.0: 0.6, 10.0: 0.7, 20.0: 0.8, 30.0: 0.9, 40.0: 1.0}
V_REC_END_FPS = 6.0
V_SINK_FPS = {0.0: 33.0, 10.0: 33.0, 20.0: 32.0, 30.0: 30.0, 40.0: 28.0}
T_ENTRY_S = {0.0: 2.2, 10.0: 2.4, 20.0: 2.4, 30.0: 2.1, 40.0: 1.7}
H_FLARE_CONS_FT = {0.0: 28.0, 10.0: 33.0, 20.0: 31.0, 30.0: 22.0, 40.0: 14.0}
H0_GRID_FT = [20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0,
              120.0, 150.0, 200.0]
V_TD_STD_FPM = 300.0
FLARE_DECEL_FRAC_PRED = 0.45
G_FPS2 = 32.174


def _recognition_loss(v, tau_r):
    return 0.5 * V_REC_END_FPS * tau_r


def _entry_loss(v, tau_r):
    return 0.5 * (V_REC_END_FPS + V_SINK_FPS[v]) * T_ENTRY_S[v]


def _need_height_ft(v, tau_r):
    return _recognition_loss(v, tau_r) + _entry_loss(v, tau_r)


def _flare_decel_fps2(v):
    limit_fps = SAFE_TOUCHDOWN_FPM / 60.0
    return (V_SINK_FPS[v] ** 2 - limit_fps ** 2) / (2.0 * H_FLARE_CONS_FT[v])


def _flare_std_height_ft(v):
    vtd_fps = V_TD_STD_FPM / 60.0
    return (V_SINK_FPS[v] ** 2 - vtd_fps ** 2) / (2.0 * _flare_decel_fps2(v))


def model_required_height_ft(v):
    tau_r = TAU_R_S[v]
    return (_recognition_loss(v, tau_r) + _entry_loss(v, tau_r)
            + H_FLARE_CONS_FT[v])


def predicted_diagram_height(v):
    """Predicted height-velocity diagram boundary height at speed v, ft:
    the standard energy reduction on the flight-mechanics
    autorotative-descent sink model quoted in the SKILL.md (recognition at
    the full steady sink over the measured delay, the entry with the
    linear sink build, and the flare arresting the steady sink to the
    limit sink at a declared 0.45 g mean deceleration). Test-side input
    table construction; the leaf module only subtracts the table."""
    tau_r = TAU_R_S[v]
    limit_fps = SAFE_TOUCHDOWN_FPM / 60.0
    return (V_SINK_FPS[v] * tau_r + _entry_loss(v, tau_r)
            + (V_SINK_FPS[v] ** 2 - limit_fps ** 2)
            / (2.0 * FLARE_DECEL_FRAC_PRED * G_FPS2))


def demo_reduction(h0_ft, v):
    """Deterministic trace-model reduction of one demonstration, producing
    the measured marks (failure, first control input, flare initiation,
    touchdown) and the touchdown sink the module functions reduce."""
    tau_r = TAU_R_S[v]
    v_sink = V_SINK_FPS[v]
    t_entry = T_ENTRY_S[v]
    h_rec = _recognition_loss(v, tau_r)
    h_need = _need_height_ft(v, tau_r)
    h_req = model_required_height_ft(v)
    a_flare = _flare_decel_fps2(v)
    vtd_fps = None
    t_contact = None
    t_flare = None
    h_flare = None
    flare_started = False
    if h0_ft < h_rec:
        a_rec = V_REC_END_FPS / tau_r
        t_contact = math.sqrt(2.0 * h0_ft / a_rec)
        vtd_fps = math.sqrt(2.0 * a_rec * h0_ft)
    elif h0_ft < h_need:
        a_entry = (v_sink - V_REC_END_FPS) / t_entry
        t_contact = tau_r + ((-V_REC_END_FPS + math.sqrt(
            V_REC_END_FPS ** 2 + 2.0 * a_entry * (h0_ft - h_rec))) / a_entry)
        vtd_fps = math.sqrt(V_REC_END_FPS ** 2
                            + 2.0 * a_entry * (h0_ft - h_rec))
    elif h0_ft < h_req:
        t_flare = tau_r + t_entry
        h_flare_avail = h0_ft - h_need
        h_flare = h_flare_avail
        flare_started = True
        vtd_fps = math.sqrt(v_sink ** 2 - 2.0 * a_flare * h_flare_avail)
        t_contact = t_flare + (v_sink - vtd_fps) / a_flare
    else:
        t_entry_end = tau_r + t_entry
        h_above_need = h0_ft - h_need
        h_flare_std = _flare_std_height_ft(v)
        h_flare = min(h_flare_std, h_above_need)
        t_steady = max(h_above_need - h_flare, 0.0) / v_sink
        t_flare = t_entry_end + t_steady
        flare_started = True
        vtd_fps = math.sqrt(max(v_sink ** 2 - 2.0 * a_flare * h_flare, 0.0))
        t_contact = t_flare + (v_sink - vtd_fps) / a_flare
    return {"h0_ft": h0_ft, "speed_kt": v, "t_failure_s": 0.0,
            "t_reaction_s": tau_r,
            "t_flare_s": t_flare if flare_started else None,
            "t_contact_s": t_contact,
            "h_flare_ft": h_flare if flare_started else None,
            "touchdown_sink_fpm": vtd_fps * 60.0,
            "flare_started": flare_started}


def sample_trace(h0_ft, v, dt=0.5):
    """Sampled baro/radar altitude-vs-time trace of one demonstration,
    ft AGL at dt-second spacing from the failure event to touchdown."""
    r = demo_reduction(h0_ft, v)
    tau_r = TAU_R_S[v]
    v_sink = V_SINK_FPS[v]
    t_entry = T_ENTRY_S[v]
    h_rec = _recognition_loss(v, tau_r)
    h_need = _need_height_ft(v, tau_r)
    a_entry = (v_sink - V_REC_END_FPS) / t_entry
    a_flare = _flare_decel_fps2(v)
    t_end = r["t_contact_s"]
    t_entry_end = tau_r + t_entry
    out = []
    t = 0.0
    while t < t_end:
        if t <= tau_r:
            a_rec = V_REC_END_FPS / tau_r
            h = h0_ft - 0.5 * a_rec * t * t
        elif t <= t_entry_end:
            dtc = t - tau_r
            h = h0_ft - h_rec - (V_REC_END_FPS * dtc
                                 + 0.5 * a_entry * dtc * dtc)
        elif t <= r["t_flare_s"]:
            h = h0_ft - h_need - v_sink * (t - t_entry_end)
        else:
            dtf = t - r["t_flare_s"]
            h = r["h_flare_ft"] - (v_sink * dtf - 0.5 * a_flare * dtf * dtf)
            if h < 0.0:
                h = 0.0
        out.append((t, h))
        t += dt
    out.append((t_end, 0.0))
    return out


# Bracketing demonstration pairs per speed (highest FAIL / lowest PASS),
# from the worked record, and the predicted height-velocity diagram heights
# quoted from the flight-mechanics autorotative-descent sink model.
BRACKET = {0.0: (70.0, 80.0, 838.6, 300.0), 10.0: (80.0, 90.0, 751.7, 300.0),
           20.0: (70.0, 80.0, 1151.4, 502.7), 30.0: (60.0, 70.0, 829.0, 300.0),
           40.0: (40.0, 50.0, 1182.3, 300.0)}
PREDICTED_FT = {0.0: 96.855, 10.0: 104.055, 20.0: 103.110, 30.0: 92.428,
                40.0: 80.522}
QUOTED_BOUNDARY_FT = {0.0: 74.430, 10.0: 83.358, 20.0: 78.500, 30.0: 64.329,
                      40.0: 46.600}


class TestRecognitionDelay(unittest.TestCase):
    """Workflow step 2, measure the engine-failure recognition delay."""

    def test_worked_hover_record_and_identity(self):
        # The 80 ft hover demonstration: first control input 0.6 s after
        # the failure mark at t = 0; the delay is the mark subtraction at
        # any valid pair.
        self.assertAlmostEqual(recognition_delay(0.6, 0.0), 0.6, delta=1e-9)
        for t_reaction, t_failure in [(2.957, 0.0), (3.4, 1.1), (5.0, 2.5)]:
            self.assertAlmostEqual(
                recognition_delay(t_reaction, t_failure),
                t_reaction - t_failure, delta=1e-9)

    def test_valueerror_rejections(self):
        # Failure mark before the record start; zero delay (reaction at the
        # failure mark); control input before the failure mark.
        for t_reaction, t_failure in [(0.5, -1.0), (0.6, 0.6), (0.5, 0.6)]:
            with self.assertRaises(ValueError):
                recognition_delay(t_reaction, t_failure)


class TestRecognitionLossWithAllowance(unittest.TestCase):
    """Workflow step 6, apply the reaction time allowance to the
    recognition-phase height loss."""

    def test_worked_hover_record_default_allowance(self):
        # Measured 1.8 ft over the recognition window plus 6.0 ft/s of sink
        # over the declared 1.0 s allowance.
        self.assertAlmostEqual(recognition_loss_with_allowance(1.8, 6.0),
                               7.8, delta=1e-9)
        self.assertEqual(REACTION_ALLOWANCE_S, 1.0)

    def test_zero_allowance_returns_measured_loss(self):
        self.assertAlmostEqual(
            recognition_loss_with_allowance(1.8, 6.0, allowance_s=0.0),
            1.8, delta=1e-9)

    def test_valueerror_rejections(self):
        with self.assertRaises(ValueError):
            recognition_loss_with_allowance(-1.0, 6.0)
        with self.assertRaises(ValueError):
            recognition_loss_with_allowance(1.8, -6.0)
        with self.assertRaises(ValueError):
            recognition_loss_with_allowance(1.8, 6.0, -0.5)


class TestEstablishmentAndFlareTimes(unittest.TestCase):
    """Workflow step 3, measure the establishment and flare times from the
    first control input and flare-initiation marks."""

    def test_marginal_hover_pass_mark(self):
        # 80 ft hover demonstration: flare-initiation mark at 2.957 s, first
        # control input at 0.6 s.
        self.assertAlmostEqual(
            time_to_establish_autorotation(2.957, 0.6), 2.357, delta=1e-9)

    def test_identity_subtraction(self):
        for t_flare, t_reaction in [(3.9, 0.8), (5.5, 2.0)]:
            self.assertAlmostEqual(
                time_to_establish_autorotation(t_flare, t_reaction),
                t_flare - t_reaction, delta=1e-9)

    def test_valueerror_rejections(self):
        # Flare mark at the first input (zero establishment) and a reaction
        # time before the record start.
        with self.assertRaises(ValueError):
            time_to_establish_autorotation(2.0, 2.0)
        with self.assertRaises(ValueError):
            time_to_establish_autorotation(2.0, -1.0)


class TestHeightLossSplit(unittest.TestCase):
    """Workflow step 4, split the measured height loss into the height lost
    to the flare and the flare recovery altitude."""

    def test_height_lost_to_flare_worked_and_identity(self):
        # 80 ft hover pass: flare-initiation altitude 30.123 ft gives a
        # 49.877 ft loss; the loss is the starting-height subtraction at
        # any valid pair.
        self.assertAlmostEqual(height_lost_to_flare(80.0, 30.123), 49.877,
                               delta=1e-9)
        self.assertAlmostEqual(height_lost_to_flare(90.0, 35.503),
                               90.0 - 35.503, delta=1e-9)

    def test_height_lost_valueerror_rejections(self):
        with self.assertRaises(ValueError):
            height_lost_to_flare(0.0, 20.0)
        with self.assertRaises(ValueError):
            height_lost_to_flare(80.0, 0.0)
        with self.assertRaises(ValueError):
            height_lost_to_flare(80.0, 90.0)

    def test_flare_recovery_altitude_worked(self):
        # Recovery altitude equals the flare-initiation altitude above the
        # touchdown altitude (0 ft for a touchdown).
        self.assertAlmostEqual(flare_recovery_altitude(30.123, 0.0), 30.123,
                               delta=1e-9)

    def test_flare_recovery_valueerror_rejections(self):
        with self.assertRaises(ValueError):
            flare_recovery_altitude(0.0)
        with self.assertRaises(ValueError):
            flare_recovery_altitude(30.0, 30.0)
        with self.assertRaises(ValueError):
            flare_recovery_altitude(30.0, -1.0)


class TestTouchdownVerdict(unittest.TestCase):
    """Workflow step 5, give the PASS or FAIL touchdown verdict against the
    declared safe-touchdown sink limit."""

    def test_thresholds_inclusive_and_custom_limit(self):
        self.assertEqual(SAFE_TOUCHDOWN_FPM, 600.0)
        self.assertEqual(touchdown_verdict(300.0), "PASS")
        self.assertEqual(touchdown_verdict(600.0), "PASS")   # inclusive
        self.assertEqual(touchdown_verdict(600.1), "FAIL")
        self.assertEqual(touchdown_verdict(300.0, limit_fpm=250.0), "FAIL")
        self.assertEqual(touchdown_verdict(250.0, limit_fpm=250.0), "PASS")

    def test_valueerror_rejections(self):
        with self.assertRaises(ValueError):
            touchdown_verdict(-100.0)
        with self.assertRaises(ValueError):
            touchdown_verdict(500.0, 0.0)


class TestBoundaryInterpolation(unittest.TestCase):
    """Workflow step 7, interpolate the height-velocity boundary height at
    one speed from the bracketing FAIL and PASS demonstration pair."""

    def test_worked_hover_bracket_inside_bracket(self):
        # The reduced 74.430 ft hover boundary lies strictly inside the
        # 70 ft FAIL to 80 ft PASS bracket.
        b = interpolate_boundary_height(70.0, 80.0, 838.6, 300.0)
        self.assertAlmostEqual(b, 74.430, delta=0.01)
        self.assertGreater(b, 70.0)
        self.assertLess(b, 80.0)

    def test_reaction_allowance_rise(self):
        # Workflow step 6 on the reduced boundary: the published boundary
        # rises by exactly the sink rate times the allowance, 6.0 ft in the
        # worked record, and the quoted boundary 74.430 carries the 1.0 s
        # allowance to 80.430.
        b = interpolate_boundary_height(70.0, 80.0, 838.6, 300.0)
        self.assertAlmostEqual(recognition_loss_with_allowance(b, 6.0) - b,
                               6.0, delta=1e-9)
        self.assertAlmostEqual(recognition_loss_with_allowance(74.430, 6.0),
                               80.430, delta=1e-9)

    def test_speed_ordering_dead_man_curve_knee(self):
        # The reduced boundary rises from hover to a knee near 10 KTAS and
        # falls as recoverable translational energy grows.
        heights = []
        for v in SPEEDS_KT:
            hf, hp, sf, sp = BRACKET[v]
            heights.append(interpolate_boundary_height(hf, hp, sf, sp))
            self.assertAlmostEqual(heights[-1], QUOTED_BOUNDARY_FT[v],
                                   delta=0.01)
        self.assertLess(heights[0], heights[1])
        self.assertGreater(heights[1], heights[2])
        self.assertGreater(heights[2], heights[3])
        self.assertGreater(heights[3], heights[4])
        # Each boundary with the 1.0 s allowance is 6.0 ft higher.
        for v, b in zip(SPEEDS_KT, heights):
            self.assertAlmostEqual(recognition_loss_with_allowance(b, 6.0)
                                   - b, 6.0, delta=1e-9)

    def test_valueerror_rejections(self):
        cases = [(70.0, 70.0, 839.0, 300.0),   # equal bracket heights
                 (70.0, 80.0, 500.0, 300.0),   # failing sink at/under limit
                 (70.0, 80.0, 839.0, 700.0),   # passing sink above limit
                 (70.0, 80.0, 839.0, 839.0),   # flat sink line
                 (-5.0, 80.0, 839.0, 300.0),   # non-positive height
                 (70.0, 80.0, 839.0, 300.0, -1.0)]  # non-positive limit
        for c in cases:
            with self.assertRaises(ValueError):
                interpolate_boundary_height(*c)


class TestHoverColumnReduction(unittest.TestCase):
    """Workflow steps 1 to 5 across the full hover (0 KTAS) height sweep of
    the worked record."""

    QUOTED_SINKS = [1318.3, 1619.1, 1872.2, 1801.8, 1405.3, 838.6,
                    300.0, 300.0, 300.0, 300.0, 300.0, 300.0]
    QUOTED_CONTACT = [1.901, 2.310, 2.654, 2.968, 3.342, 3.877, 4.542,
                      4.845, 5.148, 5.754, 6.664, 8.179]

    def test_full_sweep_verdicts_and_sinks(self):
        for i, h0 in enumerate(H0_GRID_FT):
            r = demo_reduction(h0, 0.0)
            self.assertAlmostEqual(r["touchdown_sink_fpm"],
                                   self.QUOTED_SINKS[i], delta=0.05)
            self.assertAlmostEqual(r["t_contact_s"], self.QUOTED_CONTACT[i],
                                   delta=1e-3)
            self.assertEqual(r["h0_ft"], h0)
            expected = "PASS" if i >= 6 else "FAIL"
            self.assertEqual(touchdown_verdict(r["touchdown_sink_fpm"]),
                             expected)

    def test_verdict_flip_brackets_the_boundary(self):
        # The 70 ft hover demonstration FAILS at 838.6 fpm and the 80 ft
        # demonstration PASSES at 300.0 fpm: the verdict flip that brackets
        # the reduced 74.4 ft boundary.
        r70 = demo_reduction(70.0, 0.0)
        r80 = demo_reduction(80.0, 0.0)
        self.assertEqual(touchdown_verdict(r70["touchdown_sink_fpm"]), "FAIL")
        self.assertEqual(touchdown_verdict(r80["touchdown_sink_fpm"]), "PASS")
        self.assertAlmostEqual(r70["touchdown_sink_fpm"], 838.6, delta=0.05)
        self.assertAlmostEqual(r80["touchdown_sink_fpm"], 300.0, delta=0.05)


class TestSampledTraceReduction(unittest.TestCase):
    """Workflow steps 2 to 4 on the sampled baro/radar altitude trace of the
    passing 80 ft hover demonstration."""

    def test_reduced_marks_and_time_identity(self):
        r = demo_reduction(80.0, 0.0)
        delay = recognition_delay(r["t_reaction_s"], r["t_failure_s"])
        establish = time_to_establish_autorotation(r["t_flare_s"],
                                                   r["t_reaction_s"])
        flare_dur = r["t_contact_s"] - r["t_flare_s"]
        # Read-off marks: first control input 0.6 s, flare-initiation mark
        # 2.957 s (the hover marginal-pass steady segment lasts about 0.16
        # s), touchdown 4.542 s. The quoted 2.36 s establishment is the
        # 2-dp read-off of the 2.357 s literal-mark reduction.
        self.assertAlmostEqual(delay, 0.60, delta=1e-9)
        self.assertAlmostEqual(time_to_establish_autorotation(2.957, 0.6),
                               2.357, delta=1e-9)
        self.assertAlmostEqual(establish, 2.36, delta=0.005)
        self.assertAlmostEqual(r["t_contact_s"], 4.542, delta=1e-3)
        self.assertAlmostEqual(flare_dur, 1.585, delta=1e-3)
        # The time identity: 0.60 + 2.36 + 1.585 = 4.542 s.
        self.assertAlmostEqual(delay + establish + flare_dur,
                               r["t_contact_s"], delta=1e-9)

    def test_sampled_trace_samples(self):
        trace = dict(sample_trace(80.0, 0.0))
        self.assertAlmostEqual(trace[0.0], 80.0, delta=1e-9)
        self.assertAlmostEqual(trace[0.5], 78.8, delta=0.06)
        self.assertAlmostEqual(trace[2.0], 57.8, delta=0.06)
        self.assertAlmostEqual(trace[4.0], 5.3, delta=0.06)
        self.assertAlmostEqual(trace[4.5], 0.2, delta=0.06)


class TestMarginalPassIdentities(unittest.TestCase):
    """Workflow step 4 split identity and step 2 to 3 time identity on the
    marginal passing demonstration of every speed."""

    def test_height_split_identity_all_speeds(self):
        # The anchor residual is 0.00e+00 at every speed: height lost to the
        # flare plus the flare recovery altitude equals the starting height.
        for v in SPEEDS_KT:
            hp = BRACKET[v][1]
            r = demo_reduction(hp, v)
            lost = height_lost_to_flare(hp, r["h_flare_ft"])
            recovery = flare_recovery_altitude(r["h_flare_ft"])
            self.assertAlmostEqual(lost + recovery, hp, delta=1e-9)

    def test_time_identity_all_speeds(self):
        # Recognition delay plus establishment time plus flare duration
        # equals the measured failure-to-touchdown time at every speed.
        for v in SPEEDS_KT:
            hp = BRACKET[v][1]
            r = demo_reduction(hp, v)
            delay = recognition_delay(r["t_reaction_s"], r["t_failure_s"])
            establish = time_to_establish_autorotation(r["t_flare_s"],
                                                       r["t_reaction_s"])
            flare_dur = r["t_contact_s"] - r["t_flare_s"]
            self.assertAlmostEqual(delay + establish + flare_dur,
                                   r["t_contact_s"], delta=1e-9)


class TestAvoidRegionMap(unittest.TestCase):
    """Workflow step 8, build the measured avoid-region map over the
    (height AGL, speed KTAS) grid."""

    def test_worked_grid_counts(self):
        boundary_table = []
        for v in SPEEDS_KT:
            hf, hp, sf, sp = BRACKET[v]
            boundary_table.append(interpolate_boundary_height(hf, hp, sf, sp))
        cells = build_avoid_map(H0_GRID_FT, SPEEDS_KT, boundary_table)
        self.assertEqual(len(cells), 60)
        self.assertEqual(sum(1 for c in cells if c["region"] == "AVOID"), 27)
        self.assertEqual(sum(1 for c in cells if c["region"] == "SAFE"), 33)
        per_speed = {0.0: 6, 10.0: 7, 20.0: 6, 30.0: 5, 40.0: 3}
        for v in SPEEDS_KT:
            col = [c for c in cells if c["speed_kt"] == v]
            self.assertEqual(sum(1 for c in col if c["region"] == "AVOID"),
                             per_speed[v])

    def test_region_rule_strictly_below(self):
        # AVOID strictly below the boundary at that speed; SAFE at or above
        # it, inclusive at an integer boundary height.
        cells = build_avoid_map([50.0, 80.0, 90.0], [0.0], [80.0])
        by_height = {c["height_ft"]: c["region"] for c in cells}
        self.assertEqual(by_height[50.0], "AVOID")
        self.assertEqual(by_height[80.0], "SAFE")
        self.assertEqual(by_height[90.0], "SAFE")

    def test_valueerror_rejections(self):
        with self.assertRaises(ValueError):
            build_avoid_map([], [0.0], [70.0])
        with self.assertRaises(ValueError):
            build_avoid_map([20.0], [0.0, 10.0], [70.0])
        with self.assertRaises(ValueError):
            build_avoid_map([20.0, -5.0], [0.0], [70.0])
        with self.assertRaises(ValueError):
            build_avoid_map([20.0], [0.0], [-70.0])


class TestClearanceVerdict(unittest.TestCase):
    """Workflow step 9, judge the clearance of the measured boundary
    against the predicted height-velocity diagram at each speed."""

    def test_worked_speeds_all_pass(self):
        for v in SPEEDS_KT:
            hf, hp, sf, sp = BRACKET[v]
            measured = recognition_loss_with_allowance(
                interpolate_boundary_height(hf, hp, sf, sp), 6.0)
            cv = clearance_verdict(measured, PREDICTED_FT[v])
            self.assertEqual(cv["verdict"], "PASS")
            self.assertAlmostEqual(cv["measured_boundary_ft"], measured,
                                   delta=1e-9)
            self.assertAlmostEqual(cv["predicted_boundary_ft"],
                                   PREDICTED_FT[v], delta=1e-9)
            self.assertAlmostEqual(cv["margin_ft"],
                                   PREDICTED_FT[v] - measured, delta=1e-9)

    def test_quoted_margins(self):
        # Margins of the worked record: the measured boundary with the
        # reaction allowance against the predicted height-velocity diagram,
        # quoted within 1e-3. The predicted table is rebuilt test-side with
        # the anchor's standard energy reduction so the unrounded anchor
        # values are compared, not the 3-dp printed table.
        quoted_margins = {0.0: 16.424, 10.0: 14.697, 20.0: 18.610,
                          30.0: 22.098, 40.0: 27.922}
        for v in SPEEDS_KT:
            self.assertAlmostEqual(predicted_diagram_height(v),
                                   PREDICTED_FT[v], delta=0.01)
            hf, hp, sf, sp = BRACKET[v]
            measured = recognition_loss_with_allowance(
                interpolate_boundary_height(hf, hp, sf, sp), 6.0)
            cv = clearance_verdict(measured, predicted_diagram_height(v))
            self.assertEqual(cv["verdict"], "PASS")
            self.assertAlmostEqual(cv["margin_ft"], quoted_margins[v],
                                   delta=1e-3)

    def test_inclusive_equal_and_fail_cases(self):
        # PASS inclusive when predicted equals measured (margin 0.0); FAIL
        # when the predicted boundary sits below the measured boundary.
        self.assertEqual(clearance_verdict(80.0, 80.0)["verdict"], "PASS")
        self.assertAlmostEqual(clearance_verdict(80.0, 80.0)["margin_ft"],
                               0.0, delta=1e-9)
        self.assertEqual(clearance_verdict(100.0, 80.0)["verdict"], "FAIL")
        self.assertAlmostEqual(clearance_verdict(100.0, 80.0)["margin_ft"],
                               -20.0, delta=1e-9)

    def test_valueerror_rejections(self):
        with self.assertRaises(ValueError):
            clearance_verdict(-1.0, 100.0)
        with self.assertRaises(ValueError):
            clearance_verdict(80.0, -1.0)


class TestModuleDiscipline(unittest.TestCase):
    """Workflow step 10, confirm the reduction with the deterministic
    contract test."""

    def test_valueerror_suite_all_anchor_cases(self):
        # The 26 offending-input cases of the wave-43 anchor across the nine
        # module functions, every one raising ValueError.
        ve_cases = [
            lambda: recognition_delay(0.6, 0.6),
            lambda: recognition_delay(0.5, 0.6),
            lambda: recognition_delay(0.5, -1.0),
            lambda: recognition_loss_with_allowance(-1.0, 6.0),
            lambda: recognition_loss_with_allowance(1.8, -6.0),
            lambda: recognition_loss_with_allowance(1.8, 6.0, -0.5),
            lambda: time_to_establish_autorotation(2.0, 2.0),
            lambda: time_to_establish_autorotation(2.0, -1.0),
            lambda: height_lost_to_flare(0.0, 20.0),
            lambda: height_lost_to_flare(80.0, 0.0),
            lambda: height_lost_to_flare(80.0, 90.0),
            lambda: flare_recovery_altitude(0.0),
            lambda: flare_recovery_altitude(30.0, 30.0),
            lambda: flare_recovery_altitude(30.0, -1.0),
            lambda: touchdown_verdict(-100.0),
            lambda: touchdown_verdict(500.0, 0.0),
            lambda: interpolate_boundary_height(70.0, 70.0, 839.0, 300.0),
            lambda: interpolate_boundary_height(70.0, 80.0, 500.0, 300.0),
            lambda: interpolate_boundary_height(70.0, 80.0, 839.0, 700.0),
            lambda: interpolate_boundary_height(70.0, 80.0, 839.0, 839.0),
            lambda: build_avoid_map([], [0.0], [70.0]),
            lambda: build_avoid_map([20.0], [0.0, 10.0], [70.0]),
            lambda: build_avoid_map([20.0, -5.0], [0.0], [70.0]),
            lambda: build_avoid_map([20.0], [0.0], [-70.0]),
            lambda: clearance_verdict(-1.0, 100.0),
            lambda: clearance_verdict(80.0, -1.0),
        ]
        self.assertEqual(len(ve_cases), 26)
        for fn in ve_cases:
            with self.assertRaises(ValueError):
                fn()

    def test_determinism_repeated_calls(self):
        boundary_table = []
        for v in SPEEDS_KT:
            hf, hp, sf, sp = BRACKET[v]
            boundary_table.append(interpolate_boundary_height(hf, hp, sf, sp))
        first = build_avoid_map(H0_GRID_FT, SPEEDS_KT, boundary_table)
        second = build_avoid_map(H0_GRID_FT, SPEEDS_KT, boundary_table)
        self.assertEqual(first, second)
        self.assertEqual(interpolate_boundary_height(70.0, 80.0, 838.6,
                                                     300.0),
                         interpolate_boundary_height(70.0, 80.0, 838.6,
                                                     300.0))

    def test_no_randomness_no_imports_beyond_math(self):
        logic_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "rotorcraft_height_velocity_diagram_test_"
                                  "logic.py")
        with open(logic_path, "r") as fh:
            src = fh.read()
        self.assertIn("import math", src)
        self.assertNotIn("import random", src)
        self.assertNotIn("numpy", src)
        self.assertNotIn("scipy", src)
        self.assertNotIn("random.", src)


if __name__ == "__main__":
    unittest.main()
