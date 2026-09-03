"""Deterministic contract test for buffet_boundary_testing_logic.

Builds the measured-RMS fixture from the wave-28 spec onset model
n_onset(M) = 1.90 - 1.50*(M - 0.74) and asserts the spec anchors:
detected onset 1.94 g at M 0.74, boundary lift coefficients within 0.01,
n_buf_cruise ~1.85 within 0.01 and margins +0.55 / -0.15 within 0.02.

The spec q column carries hand-rounding spread up to about 10 Pa, so the
q anchors are asserted with a 10 Pa window while q is also checked
exactly against the module's own ISA state (identity). The M 0.78 and
M 0.80 onset detections land at 1.8667 and 1.8444 g because the 0.1 g
sample grid cannot place a sample on the off-grid model onset (1.84 and
1.81 g); both stay within 0.02 of the idealized crossing anchors.

Run offline: python3 scripts/test_buffet_boundary_testing.py
"""

import math
import os
import sys
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.abspath(__file__))
)

import buffet_boundary_testing_logic as bb

# --- wave-28 spec fixture ------------------------------------------------
W = 195000.0  # kg test gross weight
S = 360.0  # m2 wing area
ALT = 10668.0  # m test altitude
MACHS = [0.74, 0.76, 0.78, 0.80, 0.82]
CRUISE = 0.80
N_SAMPLES = 13  # load factor samples 1.0 .. 2.2 every 0.1 g


def n_onset_model(mach):
    """Fixture model of the true onset load factor at mach."""
    return 1.90 - 1.50 * (mach - 0.74)


def build_fixture_rows():
    """rms(n) = 0.004 for n <= onset else 0.004 + 0.4*(n - onset)."""
    rows = []
    for mach in MACHS:
        onset = n_onset_model(mach)
        row = []
        for i in range(N_SAMPLES):
            n = 1.0 + 0.1 * i
            rms = (
                bb.RMS_FLOOR_G
                if n <= onset
                else bb.RMS_FLOOR_G + bb.RMS_RISE_PER_G * (n - onset)
            )
            row.append((n, rms))
        rows.append(row)
    return rows


RMS_ROWS = build_fixture_rows()

# Spec anchors: cl_buf per Mach (tolerance 0.01), ideal onset crossings
# (n_onset + 0.04), and printed q values (hand-rounded).
CL_BUF_ANCHORS = [1.1276, 1.0526, 0.9838, 0.9206, 0.8622]
ONSET_ANCHORS = [1.94, 1.91, 1.88, 1.85, 1.82]
Q_ANCHORS = [9139.5, 9638.7, 10150.6, 10675.1, 11212.4]


def default_inputs(**overrides):
    inputs = {
        "weight_kg": W,
        "wing_area_m2": S,
        "mach_list": list(MACHS),
        "altitude_m": ALT,
        "rms_table": [list(row) for row in RMS_ROWS],
        "cruise_mach": CRUISE,
        "buffet_target_n": 1.3,
    }
    inputs.update(overrides)
    return inputs


class TestIsaState(unittest.TestCase):
    def test_isa_state_sea_level(self):
        st = bb.isa_state(0.0)
        self.assertAlmostEqual(st["T"], 288.15, delta=1e-9)
        self.assertAlmostEqual(st["P"], 101325.0, delta=1e-6)
        self.assertAlmostEqual(st["rho"], 1.225, delta=0.001)

    def test_isa_state_at_10668m(self):
        st = bb.isa_state(ALT)
        self.assertAlmostEqual(st["T"], 218.81, delta=0.1)
        self.assertAlmostEqual(st["P"], 23843.0, delta=1.0)
        self.assertAlmostEqual(st["rho"], 0.3796, delta=1e-4)
        a = math.sqrt(1.4 * 287.05 * st["T"])
        self.assertAlmostEqual(a, 296.51, delta=0.1)

    def test_isa_state_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            bb.isa_state(-1.0)


class TestDynamicPressure(unittest.TestCase):
    def test_dynamic_pressure_matches_analytic_identity(self):
        st = bb.isa_state(ALT)
        a = math.sqrt(1.4 * 287.05 * st["T"])
        for mach in MACHS:
            q_ref = 0.5 * st["rho"] * (mach * a) ** 2
            self.assertAlmostEqual(
                bb.dynamic_pressure(mach, ALT), q_ref, delta=1e-6
            )

    def test_dynamic_pressure_spec_anchors(self):
        for mach, q_anchor in zip(MACHS, Q_ANCHORS):
            self.assertAlmostEqual(
                bb.dynamic_pressure(mach, ALT), q_anchor, delta=10.0
            )

    def test_dynamic_pressure_mach_out_of_range_raises(self):
        for bad in (0.05, 0.1, 2.0, 3.0):
            with self.assertRaises(ValueError):
                bb.dynamic_pressure(bad, ALT)


class TestOnsetDetect(unittest.TestCase):
    def test_onset_detect_exact_194_at_mach_074(self):
        onset = bb.onset_detect(RMS_ROWS[0], bb.RMS_ONSET_G)
        self.assertAlmostEqual(onset, 1.94, delta=1e-6)

    def test_onset_detect_all_mach_ideal_anchors(self):
        for row, mach, anchor in zip(RMS_ROWS, MACHS, ONSET_ANCHORS):
            onset = bb.onset_detect(row, bb.RMS_ONSET_G)
            # idealized continuous crossing sits at n_onset + 0.04
            self.assertAlmostEqual(onset, n_onset_model(mach) + 0.04,
                                   delta=0.02)
            self.assertAlmostEqual(onset, anchor, delta=0.02)

    def test_onset_detect_default_threshold_used(self):
        self.assertAlmostEqual(
            bb.onset_detect(RMS_ROWS[0]), 1.94, delta=1e-6
        )

    def test_onset_detect_no_crossing_raises(self):
        flat = [(1.0 + 0.1 * i, 0.004) for i in range(N_SAMPLES)]
        with self.assertRaises(ValueError):
            bb.onset_detect(flat, bb.RMS_ONSET_G)

    def test_onset_detect_non_monotonic_rms_raises(self):
        row = list(reversed(RMS_ROWS[2]))
        with self.assertRaises(ValueError):
            bb.onset_detect(row, bb.RMS_ONSET_G)

    def test_onset_detect_single_sample_raises(self):
        with self.assertRaises(ValueError):
            bb.onset_detect([(1.0, 0.004)], bb.RMS_ONSET_G)

    def test_onset_detect_empty_table_raises(self):
        with self.assertRaises(ValueError):
            bb.onset_detect([], bb.RMS_ONSET_G)

    def test_onset_detect_nonpositive_threshold_raises(self):
        with self.assertRaises(ValueError):
            bb.onset_detect(RMS_ROWS[0], 0.0)


class TestBoundaryLiftCoefficient(unittest.TestCase):
    def test_cl_buf_spec_anchors(self):
        for mach, row, anchor in zip(MACHS, RMS_ROWS, CL_BUF_ANCHORS):
            q = bb.dynamic_pressure(mach, ALT)
            onset = bb.onset_detect(row, bb.RMS_ONSET_G)
            cl_buf = bb.boundary_lift_coefficient(onset, q, W, S)
            self.assertAlmostEqual(cl_buf, anchor, delta=0.01)

    def test_boundary_lift_nonpositive_weight_raises(self):
        q = bb.dynamic_pressure(0.80, ALT)
        for bad in (0.0, -100.0):
            with self.assertRaises(ValueError):
                bb.boundary_lift_coefficient(1.85, q, bad, S)

    def test_boundary_lift_nonpositive_area_raises(self):
        q = bb.dynamic_pressure(0.80, ALT)
        with self.assertRaises(ValueError):
            bb.boundary_lift_coefficient(1.85, q, W, 0.0)

    def test_boundary_lift_round_trip_identity(self):
        q = bb.dynamic_pressure(0.80, ALT)
        for onset_n in (1.82, 1.85, 1.94):
            cl = bb.boundary_lift_coefficient(onset_n, q, W, S)
            n_back = cl * q * S / (W * bb.G0)
            self.assertAlmostEqual(n_back, onset_n, delta=1e-9)


class TestFitBoundaryLine(unittest.TestCase):
    def test_fit_slope_negative_about_minus_3_3(self):
        cl_buf = [
            bb.boundary_lift_coefficient(
                bb.onset_detect(row, bb.RMS_ONSET_G),
                bb.dynamic_pressure(mach, ALT), W, S)
            for mach, row in zip(MACHS, RMS_ROWS)
        ]
        fit = bb.fit_boundary_line(MACHS, cl_buf, CRUISE)
        self.assertLess(fit["slope"], 0.0)
        self.assertAlmostEqual(fit["slope"], -3.337, delta=0.05)

    def test_fit_line_at_cruise_mach_anchor(self):
        cl_buf = [
            bb.boundary_lift_coefficient(
                bb.onset_detect(row, bb.RMS_ONSET_G),
                bb.dynamic_pressure(mach, ALT), W, S)
            for mach, row in zip(MACHS, RMS_ROWS)
        ]
        fit = bb.fit_boundary_line(MACHS, cl_buf, 0.80)
        self.assertAlmostEqual(fit["cl_at_cruise"], 0.9206, delta=0.01)

    def test_fit_residual_length_and_values(self):
        cl_buf = [
            bb.boundary_lift_coefficient(
                bb.onset_detect(row, bb.RMS_ONSET_G),
                bb.dynamic_pressure(mach, ALT), W, S)
            for mach, row in zip(MACHS, RMS_ROWS)
        ]
        fit = bb.fit_boundary_line(MACHS, cl_buf, CRUISE)
        self.assertEqual(len(fit["residuals"]), len(MACHS))
        for mach, cl, resid in zip(MACHS, cl_buf, fit["residuals"]):
            line_val = fit["slope"] * mach + fit["intercept"]
            self.assertAlmostEqual(resid, cl - line_val, delta=1e-9)

    def test_fit_cl_at_cruise_none_without_cruise_mach(self):
        cl_buf = [1.1, 1.0, 0.9]
        fit = bb.fit_boundary_line([0.74, 0.78, 0.82], cl_buf)
        self.assertIsNone(fit["cl_at_cruise"])
        self.assertAlmostEqual(
            fit["cl_at_cruise"] if fit["cl_at_cruise"] is not None else
            fit["slope"] * 0.80 + fit["intercept"],
            fit["slope"] * 0.80 + fit["intercept"], delta=1e-12)

    def test_fit_fewer_than_two_points_raises(self):
        with self.assertRaises(ValueError):
            bb.fit_boundary_line([0.80], [0.9])
        with self.assertRaises(ValueError):
            bb.fit_boundary_line([], [])

    def test_fit_mismatched_lengths_raises(self):
        with self.assertRaises(ValueError):
            bb.fit_boundary_line([0.74, 0.80], [1.0, 0.9, 0.8])


class TestBuffetMargin(unittest.TestCase):
    def test_buffet_margin_positive_pass(self):
        self.assertAlmostEqual(
            bb.buffet_margin(1.85, 1.3), 0.55, delta=1e-9
        )

    def test_buffet_margin_negative_fail(self):
        self.assertAlmostEqual(
            bb.buffet_margin(1.85, 2.0), -0.15, delta=1e-9
        )

    def test_buffet_margin_nonpositive_target_raises(self):
        with self.assertRaises(ValueError):
            bb.buffet_margin(1.85, 0.0)
        with self.assertRaises(ValueError):
            bb.buffet_margin(1.85, -1.0)


class TestAnalyze(unittest.TestCase):
    def test_analyze_pass_verdict_and_anchors(self):
        res = bb.analyze(default_inputs())
        self.assertEqual(res["verdict"], "buffet-margin-pass")
        self.assertAlmostEqual(res["n_buf_cruise"], 1.85, delta=0.01)
        self.assertAlmostEqual(res["margin_n"], 0.55, delta=0.02)
        self.assertAlmostEqual(res["cl_buf_cruise"], 0.9206, delta=0.01)

    def test_analyze_fail_verdict_target_20(self):
        res = bb.analyze(default_inputs(buffet_target_n=2.0))
        self.assertEqual(res["verdict"], "buffet-margin-fail")
        self.assertAlmostEqual(res["margin_n"], -0.15, delta=0.02)

    def test_analyze_per_mach_points(self):
        res = bb.analyze(default_inputs())
        for point, q_anchor, cl_anchor, onset_anchor in zip(
                res["points"], Q_ANCHORS, CL_BUF_ANCHORS, ONSET_ANCHORS):
            self.assertAlmostEqual(point["q"], q_anchor, delta=10.0)
            self.assertAlmostEqual(point["cl_buf"], cl_anchor, delta=0.01)
            self.assertAlmostEqual(point["onset_n"], onset_anchor,
                                   delta=0.02)

    def test_analyze_cruise_outside_fitted_band_raises(self):
        with self.assertRaises(ValueError):
            bb.analyze(default_inputs(cruise_mach=0.70))

    def test_analyze_cruise_at_band_edge_allowed(self):
        res = bb.analyze(default_inputs(cruise_mach=0.82))
        self.assertEqual(res["verdict"], "buffet-margin-pass")
        self.assertGreater(res["margin_n"], 0.0)

    def test_analyze_zero_weight_raises(self):
        with self.assertRaises(ValueError):
            bb.analyze(default_inputs(weight_kg=0.0))

    def test_analyze_nonpositive_target_raises(self):
        with self.assertRaises(ValueError):
            bb.analyze(default_inputs(buffet_target_n=0.0))

    def test_analyze_mismatched_table_length_raises(self):
        with self.assertRaises(ValueError):
            bb.analyze(default_inputs(rms_table=RMS_ROWS[:-1]))

    def test_analyze_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            bb.analyze(default_inputs(altitude_m=-100.0))

    def test_analyze_default_onset_threshold_matches_explicit(self):
        explicit = bb.analyze(
            default_inputs(onset_rms_g=bb.RMS_ONSET_G)
        )
        implicit = bb.analyze(default_inputs())
        self.assertAlmostEqual(
            implicit["n_buf_cruise"], explicit["n_buf_cruise"], delta=1e-9
        )

    def test_analyze_fewer_than_two_mach_points_raises(self):
        with self.assertRaises(ValueError):
            bb.analyze(default_inputs(mach_list=[0.80],
                                      rms_table=[RMS_ROWS[3]]))


if __name__ == "__main__":
    unittest.main()
