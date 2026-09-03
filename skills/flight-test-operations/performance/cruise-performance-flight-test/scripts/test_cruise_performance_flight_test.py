"""Contract test for cruise-performance-flight-test (wave-28).

Offline, deterministic, stdlib only. Runs via:
    python3 scripts/test_cruise_performance_flight_test.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cruise_performance_flight_test_logic as cp

W_REF = 200000.0
ALT = 10668.0
MACH_LIST = [0.72, 0.74, 0.76, 0.78, 0.80, 0.82, 0.84]
W_LIST = [209000.0, 207000.0, 205000.0, 203000.0, 201000.0, 199000.0, 197000.0]


def rp_model(mach):
    """Exact quadratic range performance model behind the fixture."""
    return 90.0 - 6000.0 * (mach - 0.80) ** 2


def build_fixture_points():
    """Build measured runs from the exact model, inverted through the
    weight correction so the reduction recovers the parabola exactly."""
    points = []
    for mach, w_test in zip(MACH_LIST, W_LIST):
        tas = cp.tas_from_mach(mach, ALT)
        wf_corr = tas / rp_model(mach)
        wf_measured = wf_corr * math.sqrt(w_test / W_REF)
        points.append(
            {
                "mach": mach,
                "altitude_m": ALT,
                "w_test_kg": w_test,
                "wf_measured_kg_s": wf_measured,
            }
        )
    return points


class IsaSpeedOfSoundTests(unittest.TestCase):
    def test_speed_of_sound_sea_level(self):
        self.assertAlmostEqual(cp.isa_speed_of_sound(0.0), 340.29, delta=0.1)

    def test_speed_of_sound_cruise_altitude(self):
        self.assertAlmostEqual(cp.isa_speed_of_sound(ALT), 296.51, delta=0.1)

    def test_speed_of_sound_stratosphere_isothermal(self):
        self.assertAlmostEqual(
            cp.isa_speed_of_sound(12000.0), cp.isa_speed_of_sound(20000.0),
            places=9)

    def test_speed_of_sound_invalid_altitude_raises(self):
        with self.assertRaises(ValueError):
            cp.isa_speed_of_sound(-100.0)


class TasTests(unittest.TestCase):
    def test_tas_from_mach_at_cruise(self):
        self.assertAlmostEqual(cp.tas_from_mach(0.8, ALT), 237.21, delta=0.1)

    def test_tas_scales_with_mach(self):
        tas_a = cp.tas_from_mach(0.72, ALT)
        tas_b = cp.tas_from_mach(0.84, ALT)
        self.assertAlmostEqual(tas_b / tas_a, 0.84 / 0.72, places=9)

    def test_tas_edges(self):
        self.assertEqual(cp.tas_from_mach(0.0, 0.0), 0.0)
        with self.assertRaises(ValueError):
            cp.tas_from_mach(-0.1, ALT)


class WeightCorrectionTests(unittest.TestCase):
    def test_correction_factor_equal_weights(self):
        self.assertEqual(cp.weight_correction_factor(W_REF, W_REF), 1.0)

    def test_correction_factor_direction_and_inverse(self):
        factor = cp.weight_correction_factor(201000.0, W_REF)
        self.assertAlmostEqual(factor, math.sqrt(W_REF / 201000.0), places=12)
        self.assertLess(factor, 1.0)
        f1 = cp.weight_correction_factor(209000.0, W_REF)
        f2 = cp.weight_correction_factor(W_REF, 209000.0)
        self.assertAlmostEqual(f1 * f2, 1.0, places=12)

    def test_correction_factor_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            cp.weight_correction_factor(0.0, W_REF)
        with self.assertRaises(ValueError):
            cp.weight_correction_factor(-1000.0, W_REF)
        with self.assertRaises(ValueError):
            cp.weight_correction_factor(200000.0, 0.0)


class CorrectedFuelFlowTests(unittest.TestCase):
    def test_corrected_fuel_flow_work_anchor(self):
        flow = cp.corrected_fuel_flow(2.6423, 201000.0, W_REF)
        self.assertAlmostEqual(flow, 2.6357, delta=1e-3)

    def test_corrected_fuel_flow_round_trip(self):
        flow = cp.corrected_fuel_flow(2.0, 180000.0, W_REF)
        expected = 2.0 * math.sqrt(W_REF / 180000.0)
        self.assertAlmostEqual(flow, expected, places=9)
        self.assertGreater(flow, 2.0)
        wf_corr = cp.corrected_fuel_flow(3.1, 195500.0, W_REF)
        self.assertAlmostEqual(wf_corr * math.sqrt(195500.0 / W_REF), 3.1,
                               places=9)

    def test_corrected_fuel_flow_invalid_raises(self):
        with self.assertRaises(ValueError):
            cp.corrected_fuel_flow(-0.5, 200000.0, W_REF)
        with self.assertRaises(ValueError):
            cp.corrected_fuel_flow(2.0, 0.0, W_REF)
        with self.assertRaises(ValueError):
            cp.corrected_fuel_flow(2.0, 200000.0, -1.0)


class RangePerformanceTests(unittest.TestCase):
    def test_range_performance_work_anchor(self):
        rp = cp.range_performance(237.21, 237.21 / 90.0)
        self.assertAlmostEqual(rp, 90.0, delta=1e-6)

    def test_range_performance_simple_ratio(self):
        self.assertAlmostEqual(cp.range_performance(250.0, 2.5), 100.0,
                               places=9)

    def test_range_performance_invalid_raises(self):
        with self.assertRaises(ValueError):
            cp.range_performance(200.0, 0.0)
        with self.assertRaises(ValueError):
            cp.range_performance(200.0, -2.0)


class FixtureReductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = cp.reduce_cruise_test(build_fixture_points(), W_REF)

    def test_reduce_recovers_vertex(self):
        self.assertAlmostEqual(self.result["max_rp_mach"], 0.800000,
                               delta=1e-6)

    def test_reduce_recovers_maximum(self):
        self.assertAlmostEqual(self.result["max_rp"], 90.0, delta=1e-6)

    def test_reduce_recovers_coefficients(self):
        c2, c1, c0 = self.result["coefficients"]
        self.assertAlmostEqual(c2, -6000.0, delta=1e-3)
        self.assertAlmostEqual(c1, 9600.0, delta=1e-3)
        self.assertAlmostEqual(c0, -3750.0, delta=1e-3)

    def test_reduce_recovers_lrc_root(self):
        # Exact root of -6000 M^2 + 9600 M - 3750 = 0.99 * 90:
        # (9600 + sqrt(21600)) / 12000 = 0.8122474487, which rounds to
        # the spec anchor 0.81225.
        self.assertAlmostEqual(self.result["lrc_mach"], 0.8122474487,
                               delta=1e-6)
        self.assertLess(abs(self.result["lrc_mach"] - 0.81225), 1e-5)
        self.assertGreater(self.result["lrc_mach"], self.result["max_rp_mach"])

    def test_reduce_residuals_noise_free(self):
        for residual in self.result["residuals"]:
            self.assertLess(abs(residual), 1e-9)

    def test_reduce_verdict_maximum_found(self):
        self.assertEqual(self.result["verdict"], "maximum-found")

    def test_reduce_point_table(self):
        table = self.result["points"]
        self.assertEqual(len(table), 7)
        for entry in table:
            for key in ("mach", "tas", "wf_corr", "rp"):
                self.assertIn(key, entry)
            self.assertAlmostEqual(entry["rp"], rp_model(entry["mach"]),
                                   delta=1e-6)
            self.assertAlmostEqual(
                entry["tas"], cp.tas_from_mach(entry["mach"], ALT), places=9)

    def test_reduce_point_at_mach_080(self):
        entry = next(p for p in self.result["points"] if p["mach"] == 0.80)
        self.assertAlmostEqual(entry["wf_corr"], 2.6357, delta=1e-3)
        self.assertAlmostEqual(entry["rp"], 90.0, delta=1e-6)
        self.assertEqual(entry["w_test_kg"], 201000.0)

    def test_ordering_verdict_lrc_faster(self):
        self.assertEqual(
            cp.verify_speed_ordering(
                self.result["max_rp_mach"], self.result["lrc_mach"]),
            "lrc-faster")


class SanityAndEdgeTests(unittest.TestCase):
    def test_reduce_linear_data_c2_near_zero(self):
        # Range performance linear in Mach: rp = 60 + 40*M, so the fit
        # must return a near-zero quadratic coefficient.
        points = [
            {"mach": m, "altitude_m": ALT, "w_test_kg": 200000.0,
             "wf_measured_kg_s": cp.tas_from_mach(m, ALT)
             / (60.0 + 40.0 * m)}
            for m in [0.60, 0.65, 0.70, 0.75, 0.80]
        ]
        result = cp.reduce_cruise_test(points, W_REF)
        c2, _c1, _c0 = result["coefficients"]
        self.assertLess(abs(c2), 1e-6)

    def test_reduce_upward_bowed_no_maximum(self):
        points = [
            {"mach": m, "altitude_m": ALT, "w_test_kg": 200000.0,
             "wf_measured_kg_s": cp.tas_from_mach(m, ALT)
             / (40.0 + 20.0 * m + 30.0 * m * m)}
            for m in [0.60, 0.65, 0.70, 0.75, 0.80]
        ]
        result = cp.reduce_cruise_test(points, W_REF)
        self.assertIsNone(result["max_rp_mach"])
        self.assertIsNone(result["max_rp"])
        self.assertIsNone(result["lrc_mach"])
        self.assertEqual(result["verdict"], "no-maximum")
        # The LRC helper is deliberately inert; the root comes from the fit.
        self.assertIsNone(cp.lrc_99(0.8))
        self.assertIsNone(cp.lrc_99(None))

    def test_ordering_verdict_edges(self):
        self.assertEqual(cp.verify_speed_ordering(0.82, 0.81),
                         "lrc-not-faster")
        self.assertEqual(cp.verify_speed_ordering(None, None), "no-maximum")
        self.assertEqual(cp.verify_speed_ordering(0.8, None), "no-maximum")

    def test_reduce_invalid_inputs_raises(self):
        two = build_fixture_points()[:2]
        with self.assertRaises(ValueError):
            cp.reduce_cruise_test(two, W_REF)
        with self.assertRaises(ValueError):
            cp.reduce_cruise_test(build_fixture_points(), 0.0)

    def test_reduce_invalid_mach_raises(self):
        points = build_fixture_points()
        points[1] = dict(points[0], w_test_kg=206000.0)
        with self.assertRaises(ValueError):
            cp.reduce_cruise_test(points, W_REF)
        points = build_fixture_points()
        points[0] = dict(points[0], mach=0.25)
        with self.assertRaises(ValueError):
            cp.reduce_cruise_test(points, W_REF)
        points = build_fixture_points()
        points[3] = dict(points[3], mach=1.05)
        with self.assertRaises(ValueError):
            cp.reduce_cruise_test(points, W_REF)

    def test_reduce_nonpositive_quantities_raises(self):
        points = build_fixture_points()
        points[2] = dict(points[2], w_test_kg=0.0)
        with self.assertRaises(ValueError):
            cp.reduce_cruise_test(points, W_REF)
        points = build_fixture_points()
        points[0] = dict(points[0], wf_measured_kg_s=-1.0)
        with self.assertRaises(ValueError):
            cp.reduce_cruise_test(points, W_REF)
        points = build_fixture_points()
        points[4] = dict(points[4], wf_measured_kg_s=0.0)
        with self.assertRaises(ValueError):
            cp.reduce_cruise_test(points, W_REF)


class PlanTestMatrixTests(unittest.TestCase):
    def test_plan_matrix_linear_weight_ramp(self):
        card = cp.plan_test_matrix(MACH_LIST, ALT, 209000.0, 197000.0, 3.0)
        self.assertEqual(len(card), 7)
        self.assertEqual(card[0]["w_test_kg"], 209000.0)
        self.assertEqual(card[-1]["w_test_kg"], 197000.0)
        self.assertEqual(card[3]["w_test_kg"], 203000.0)
        self.assertAlmostEqual(
            card[5]["w_test_kg"] - card[6]["w_test_kg"], 2000.0, places=6)
        for entry, mach in zip(card, MACH_LIST):
            self.assertEqual(entry["mach"], mach)
            self.assertEqual(entry["altitude_m"], ALT)
            self.assertEqual(entry["run_minutes"], 3.0)

    def test_plan_matrix_single_mach(self):
        card = cp.plan_test_matrix([0.78], ALT, 205000.0, 199000.0, 5.0)
        self.assertEqual(len(card), 1)
        self.assertEqual(card[0]["w_test_kg"], 205000.0)

    def test_plan_matrix_invalid_raises(self):
        with self.assertRaises(ValueError):
            cp.plan_test_matrix([], ALT, 209000.0, 197000.0, 3.0)
        with self.assertRaises(ValueError):
            cp.plan_test_matrix(MACH_LIST, -1000.0, 209000.0, 197000.0, 3.0)
        with self.assertRaises(ValueError):
            cp.plan_test_matrix(MACH_LIST, ALT, 0.0, 197000.0, 3.0)
        with self.assertRaises(ValueError):
            cp.plan_test_matrix(MACH_LIST, ALT, 209000.0, 197000.0, 0.0)


class FixtureInverseConsistencyTests(unittest.TestCase):
    def test_fixture_inverse_weight_build_reduces_to_model(self):
        for point in build_fixture_points():
            tas = cp.tas_from_mach(point["mach"], ALT)
            wf_corr = cp.corrected_fuel_flow(
                point["wf_measured_kg_s"], point["w_test_kg"], W_REF)
            self.assertAlmostEqual(wf_corr, tas / rp_model(point["mach"]),
                                   places=9)
            self.assertAlmostEqual(
                cp.range_performance(tas, wf_corr),
                rp_model(point["mach"]), places=9)


if __name__ == "__main__":
    unittest.main()
