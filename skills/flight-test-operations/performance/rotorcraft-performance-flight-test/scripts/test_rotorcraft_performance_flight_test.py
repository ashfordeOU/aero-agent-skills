"""Contract test for rotorcraft-performance-flight-test logic.

Deterministic stdlib unittest, offline, no RNG. Run from the leaf
directory (or repo root):

    python3 scripts/test_rotorcraft_performance_flight_test.py

Covers the worked-example anchors of the wave-31 spec (shaft power
400,005 W in 380,000-420,000 W; ideal induced power 228,448 W in
210,000-240,000 W at the reference hover condition; measured figure of
merit 0.5711 in 0.52-0.62; corrected hover power 391,727 W in
370,000-410,000 W; corrected rate of climb 8.34 m/s in 7.5-8.5 m/s;
torque check within_rated True at 450 kW rated with 5% tolerance),
the ValueError rejections of non-physical inputs, the closed-form
identities (reference-condition correction returns the measured power
unchanged; corrected ROC scales linearly with the weight ratio), the
hover ceiling interpolation and its None returns, determinism, and the
exact convenience-dict keys.

NOTE on the FM evaluation condition: the spec worked-example anchor
0.5711 equals ideal_induced_power(weight_ref, rho_ref, area) over the
measured mean shaft power; evaluating the same measured power with the
test-day weight and density (22,500 N at rho 1.10) yields FM 0.642,
outside the spec's 0.52-0.62 band. The reduction therefore reports the
figure of merit at the reference hover condition, the same basis as
the corrected hover power.
"""

import math
import os
import sys
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.abspath(__file__)))
import rotorcraft_performance_flight_test_logic as rpf

AREA = math.pi * 5.0 ** 2
TORQUE = 14815.0
OMEGA = 27.0
MEASURED_POWER = TORQUE * OMEGA  # 400,005.0 W
W_MEAS = 22500.0
W_REF = 21574.63
RHO_MEAS = 1.10
RHO_REF = 1.225
RATED = 450000.0


class TestShaftPower(unittest.TestCase):
    def test_shaft_power_worked_example(self):
        # 14815 * 27 = 400,005 W, inside the 380,000-420,000 W anchor.
        power = rpf.shaft_power_from_torque(TORQUE, OMEGA)
        self.assertAlmostEqual(power, 400005.0, places=3)
        self.assertTrue(380000.0 <= power <= 420000.0)

    def test_shaft_power_scales_with_torque_and_omega(self):
        # P = torque * omega: doubling either factor doubles the power.
        base = rpf.shaft_power_from_torque(1000.0, 20.0)
        self.assertAlmostEqual(rpf.shaft_power_from_torque(2000.0, 20.0), 2.0 * base)
        self.assertAlmostEqual(rpf.shaft_power_from_torque(1000.0, 40.0), 2.0 * base)

    def test_shaft_power_zero_torque_allowed(self):
        self.assertEqual(rpf.shaft_power_from_torque(0.0, 27.0), 0.0)

    def test_shaft_power_rejects_negative_torque_and_nonpositive_omega(self):
        with self.assertRaises(ValueError):
            rpf.shaft_power_from_torque(-1.0, 27.0)
        with self.assertRaises(ValueError):
            rpf.shaft_power_from_torque(1000.0, 0.0)
        with self.assertRaises(ValueError):
            rpf.shaft_power_from_torque(1000.0, -27.0)


class TestIdealInducedPower(unittest.TestCase):
    def test_ideal_induced_power_worked_example_anchor(self):
        # Reference hover condition: 228,448 W inside 210,000-240,000 W.
        p_ideal = rpf.ideal_induced_power(W_REF, RHO_REF, AREA)
        self.assertAlmostEqual(p_ideal, 228448.0, delta=5.0)
        self.assertTrue(210000.0 <= p_ideal <= 240000.0)

    def test_ideal_induced_power_test_day_exceeds_reference(self):
        # Higher weight at lower density raises the induced power.
        p_test = rpf.ideal_induced_power(W_MEAS, RHO_MEAS, AREA)
        p_ref = rpf.ideal_induced_power(W_REF, RHO_REF, AREA)
        self.assertGreater(p_test, p_ref)

    def test_ideal_induced_power_scaling_identity(self):
        # P_ideal ~ T^1.5 / sqrt(rho): doubling thrust multiplies by
        # 2^1.5; doubling density divides by sqrt(2).
        base = rpf.ideal_induced_power(10000.0, 1.225, AREA)
        self.assertAlmostEqual(
            rpf.ideal_induced_power(20000.0, 1.225, AREA),
            base * 2.0 ** 1.5, places=6)
        self.assertAlmostEqual(
            rpf.ideal_induced_power(10000.0, 2.45, AREA),
            base / math.sqrt(2.0), places=6)

    def test_ideal_induced_power_rejects_nonpositive_inputs(self):
        for bad in (0.0, -100.0):
            with self.assertRaises(ValueError):
                rpf.ideal_induced_power(bad, RHO_REF, AREA)
            with self.assertRaises(ValueError):
                rpf.ideal_induced_power(10000.0, bad, AREA)
            with self.assertRaises(ValueError):
                rpf.ideal_induced_power(10000.0, RHO_REF, bad)


class TestMeasuredFigureOfMerit(unittest.TestCase):
    def test_figure_of_merit_worked_example_anchor(self):
        # FM = 228,448 / 400,005 = 0.5711, inside 0.52-0.62 (about 0.57).
        fm = rpf.measured_figure_of_merit(W_REF, RHO_REF, AREA, MEASURED_POWER)
        self.assertAlmostEqual(fm, 0.5711, places=4)
        self.assertTrue(0.52 <= fm <= 0.62)

    def test_figure_of_merit_unity_when_power_matches_ideal(self):
        # FM = 1 when the measured power equals the ideal induced power.
        p_ideal = rpf.ideal_induced_power(10000.0, 1.225, AREA)
        self.assertAlmostEqual(
            rpf.measured_figure_of_merit(10000.0, 1.225, AREA, p_ideal), 1.0)

    def test_figure_of_merit_rejects_nonphysical_inputs(self):
        # Non-positive measured power and non-positive density raise.
        with self.assertRaises(ValueError):
            rpf.measured_figure_of_merit(W_REF, RHO_REF, AREA, 0.0)
        with self.assertRaises(ValueError):
            rpf.measured_figure_of_merit(W_REF, RHO_REF, AREA, -400005.0)
        with self.assertRaises(ValueError):
            rpf.measured_figure_of_merit(W_REF, -1.225, AREA, MEASURED_POWER)

    def test_figure_of_merit_rejects_ideal_above_measured(self):
        # P_ideal > P_measured means FM > 1, non-physical.
        with self.assertRaises(ValueError):
            rpf.measured_figure_of_merit(W_MEAS, RHO_MEAS, AREA, 200000.0)


class TestPowerCorrection(unittest.TestCase):
    def test_power_correction_worked_example(self):
        # About 391,700 W, inside 370,000-410,000 W and within 3% of
        # the measured value (measurement near the reference condition).
        corrected = rpf.power_correction_weight_density(
            MEASURED_POWER, W_MEAS, W_REF, RHO_MEAS, RHO_REF, 0.6)
        self.assertAlmostEqual(corrected, 391727.5, delta=5.0)
        self.assertTrue(370000.0 <= corrected <= 410000.0)
        self.assertLess(abs(corrected - MEASURED_POWER) / MEASURED_POWER, 0.03)

    def test_power_correction_identity_at_reference(self):
        # At the reference weight and density the power is unchanged.
        corrected = rpf.power_correction_weight_density(
            MEASURED_POWER, W_REF, W_REF, RHO_REF, RHO_REF, 0.6)
        self.assertAlmostEqual(corrected, MEASURED_POWER, places=6)

    def test_power_correction_direction_with_weight(self):
        # Heavier reference weight raises the corrected power; lighter
        # reference weight lowers it (same density).
        up = rpf.power_correction_weight_density(
            MEASURED_POWER, W_MEAS, 24000.0, RHO_REF, RHO_REF, 0.6)
        down = rpf.power_correction_weight_density(
            MEASURED_POWER, W_MEAS, 20000.0, RHO_REF, RHO_REF, 0.6)
        self.assertGreater(up, MEASURED_POWER)
        self.assertLess(down, MEASURED_POWER)

    def test_power_correction_induced_fraction_endpoints(self):
        # f_i = 1 keeps only the induced term; f_i = 0 keeps only the
        # profile density term.
        f_one = rpf.power_correction_weight_density(
            MEASURED_POWER, W_MEAS, W_REF, RHO_MEAS, RHO_REF, 1.0)
        expect_one = (MEASURED_POWER * (W_REF / W_MEAS) ** 1.5
                      * math.sqrt(RHO_MEAS / RHO_REF))
        self.assertAlmostEqual(f_one, expect_one, places=6)
        f_zero = rpf.power_correction_weight_density(
            MEASURED_POWER, W_MEAS, W_REF, RHO_MEAS, RHO_REF, 0.0)
        self.assertAlmostEqual(f_zero, MEASURED_POWER * RHO_REF / RHO_MEAS,
                               places=6)

    def test_power_correction_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            rpf.power_correction_weight_density(-1.0, W_MEAS, W_REF, RHO_MEAS, RHO_REF)
        with self.assertRaises(ValueError):
            rpf.power_correction_weight_density(MEASURED_POWER, 0.0, W_REF, RHO_MEAS, RHO_REF)
        with self.assertRaises(ValueError):
            rpf.power_correction_weight_density(MEASURED_POWER, W_MEAS, 0.0, RHO_MEAS, RHO_REF)
        with self.assertRaises(ValueError):
            rpf.power_correction_weight_density(MEASURED_POWER, W_MEAS, W_REF, 0.0, RHO_REF)
        with self.assertRaises(ValueError):
            rpf.power_correction_weight_density(MEASURED_POWER, W_MEAS, W_REF, RHO_MEAS, -1.225)
        for bad_fraction in (-0.1, 1.1):
            with self.assertRaises(ValueError):
                rpf.power_correction_weight_density(
                    MEASURED_POWER, W_MEAS, W_REF, RHO_MEAS, RHO_REF, bad_fraction)


class TestCorrectedRateOfClimb(unittest.TestCase):
    def test_corrected_roc_worked_example(self):
        # 8.0 * 22500 / 21574.63 = 8.34 m/s, inside 7.5-8.5 m/s.
        roc = rpf.corrected_vertical_rate_of_climb(8.0, W_MEAS, W_REF)
        self.assertAlmostEqual(roc, 8.3431, places=4)
        self.assertTrue(7.5 <= roc <= 8.5)

    def test_corrected_roc_scales_linearly_with_weight_ratio(self):
        # ROC_corr = ROC_meas * W_meas / W_ref: doubling the measured
        # weight doubles the corrected rate at fixed reference weight,
        # and the identity holds at the reference weight.
        base = rpf.corrected_vertical_rate_of_climb(5.0, 10000.0, 20000.0)
        self.assertAlmostEqual(base, 2.5, places=9)
        doubled = rpf.corrected_vertical_rate_of_climb(5.0, 20000.0, 20000.0)
        self.assertAlmostEqual(doubled, 5.0, places=9)
        self.assertAlmostEqual(
            doubled, 2.0 * base, places=9)
        identity = rpf.corrected_vertical_rate_of_climb(6.5, 18000.0, 18000.0)
        self.assertAlmostEqual(identity, 6.5, places=9)

    def test_corrected_roc_allows_negative_measured_roc(self):
        # A descent test point is a valid measurement.
        roc = rpf.corrected_vertical_rate_of_climb(-3.0, W_MEAS, W_REF)
        self.assertAlmostEqual(roc, -3.0 * W_MEAS / W_REF, places=9)
        self.assertLess(roc, 0.0)

    def test_corrected_roc_rejects_nonpositive_weights(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                rpf.corrected_vertical_rate_of_climb(8.0, bad, W_REF)
            with self.assertRaises(ValueError):
                rpf.corrected_vertical_rate_of_climb(8.0, W_MEAS, bad)


class TestHoverCeiling(unittest.TestCase):
    ALT = [0.0, 500.0, 1000.0, 1500.0]
    REQ = [395000.0, 403000.0, 411000.0, 419000.0]

    def test_hover_ceiling_worked_example(self):
        # 415 kW available: the 411 kW point at 1000 m and the 419 kW
        # point at 1500 m bracket it halfway, so the ceiling is 1250 m.
        ceiling = rpf.hover_ceiling_altitude(415000.0, self.ALT, self.REQ)
        self.assertAlmostEqual(ceiling, 1250.0, places=6)

    def test_hover_ceiling_at_lowest_and_highest_endpoints(self):
        # Available power equal to an endpoint power returns that
        # endpoint altitude.
        low = rpf.hover_ceiling_altitude(395000.0, self.ALT, self.REQ)
        high = rpf.hover_ceiling_altitude(419000.0, self.ALT, self.REQ)
        self.assertAlmostEqual(low, 0.0, places=6)
        self.assertAlmostEqual(high, 1500.0, places=6)

    def test_hover_ceiling_none_below_lowest_point(self):
        # Required power at the lowest altitude already exceeds the
        # available power: hover is not achieved in the tested band.
        ceiling = rpf.hover_ceiling_altitude(390000.0, self.ALT, self.REQ)
        self.assertIsNone(ceiling)

    def test_hover_ceiling_none_above_highest_point(self):
        # Required power at the highest altitude is still below the
        # available power: no ceiling within the tested range.
        ceiling = rpf.hover_ceiling_altitude(430000.0, self.ALT, self.REQ)
        self.assertIsNone(ceiling)

    def test_hover_ceiling_rejects_bad_lists(self):
        with self.assertRaises(ValueError):
            rpf.hover_ceiling_altitude(415000.0, self.ALT, self.REQ[:-1])
        with self.assertRaises(ValueError):
            rpf.hover_ceiling_altitude(415000.0, [0.0], [395000.0])

    def test_hover_ceiling_rejects_negative_inputs(self):
        with self.assertRaises(ValueError):
            rpf.hover_ceiling_altitude(-1.0, self.ALT, self.REQ)
        with self.assertRaises(ValueError):
            rpf.hover_ceiling_altitude(
                415000.0, [-100.0, 500.0], [395000.0, 403000.0])
        with self.assertRaises(ValueError):
            rpf.hover_ceiling_altitude(
                415000.0, self.ALT, [395000.0, -1.0, 411000.0, 419000.0])


class TestTorqueCheck(unittest.TestCase):
    def test_torque_check_worked_example(self):
        # 400,005 W against 450 kW rated with 5% tolerance: inside.
        result = rpf.torque_to_power_check(TORQUE, OMEGA, RATED)
        self.assertAlmostEqual(result["shaft_power_w"], 400005.0, places=3)
        self.assertTrue(result["within_rated"])

    def test_torque_check_limit_is_inclusive(self):
        # 540 kW exceeds the 472.5 kW limit (450 kW + 5%): outside;
        # exactly at rated * (1 + tolerance) is still within rated.
        result = rpf.torque_to_power_check(20000.0, 27.0, RATED)
        self.assertAlmostEqual(result["shaft_power_w"], 540000.0, places=3)
        self.assertFalse(result["within_rated"])
        boundary = rpf.torque_to_power_check(RATED * 1.05 / 27.0, 27.0, RATED)
        self.assertTrue(boundary["within_rated"])

    def test_torque_check_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            rpf.torque_to_power_check(-1.0, 27.0, RATED)
        with self.assertRaises(ValueError):
            rpf.torque_to_power_check(1000.0, 0.0, RATED)


class TestReductionChain(unittest.TestCase):
    ARGS = ([TORQUE], OMEGA, W_MEAS, W_REF, RHO_MEAS, RHO_REF, AREA, RATED)

    def test_reduction_worked_example_values_and_keys(self):
        result = rpf.rotorcraft_performance_test_reduction(*self.ARGS)
        # Exact documented keys only.
        self.assertEqual(
            set(result.keys()),
            {"mean_shaft_power_w", "measured_figure_of_merit",
             "corrected_power_w", "within_rated"})
        self.assertAlmostEqual(result["mean_shaft_power_w"], 400005.0, places=3)
        self.assertAlmostEqual(result["measured_figure_of_merit"], 0.5711,
                               places=4)
        self.assertTrue(0.52 <= result["measured_figure_of_merit"] <= 0.62)
        self.assertAlmostEqual(result["corrected_power_w"], 391727.5, delta=5.0)
        self.assertTrue(370000.0 <= result["corrected_power_w"] <= 410000.0)
        self.assertTrue(result["within_rated"])

    def test_reduction_multi_point_uses_mean_torque(self):
        # Points at constant rotor speed: the mean power is the mean
        # torque times the rotor speed, and the torque check runs on
        # the mean torque point.
        torques = [14000.0, 14815.0, 15630.0]
        result = rpf.rotorcraft_performance_test_reduction(
            torques, OMEGA, W_MEAS, W_REF, RHO_MEAS, RHO_REF, AREA, RATED)
        self.assertAlmostEqual(result["mean_shaft_power_w"], 400005.0, places=3)
        self.assertTrue(result["within_rated"])

    def test_reduction_deterministic_across_runs(self):
        first = rpf.rotorcraft_performance_test_reduction(*self.ARGS)
        second = rpf.rotorcraft_performance_test_reduction(*self.ARGS)
        self.assertEqual(first, second)

    def test_reduction_propagates_valueerrors(self):
        with self.assertRaises(ValueError):
            rpf.rotorcraft_performance_test_reduction(
                [-100.0], OMEGA, W_MEAS, W_REF, RHO_MEAS, RHO_REF, AREA, RATED)
        with self.assertRaises(ValueError):
            rpf.rotorcraft_performance_test_reduction(
                [], OMEGA, W_MEAS, W_REF, RHO_MEAS, RHO_REF, AREA, RATED)
        with self.assertRaises(ValueError):
            rpf.rotorcraft_performance_test_reduction(
                [TORQUE], OMEGA, 0.0, W_REF, RHO_MEAS, RHO_REF, AREA, RATED)
        with self.assertRaises(ValueError):
            rpf.rotorcraft_performance_test_reduction(
                [TORQUE], [27.0, 26.5], W_MEAS, W_REF, RHO_MEAS, RHO_REF,
                AREA, RATED)

    def test_module_source_has_no_rng(self):
        # Determinism contract: the module never imports or seeds random.
        import rotorcraft_performance_flight_test_logic as module_file
        with open(module_file.__file__) as handle:
            source = handle.read()
        self.assertNotIn("import random", source)
        self.assertNotIn("from random", source)


if __name__ == "__main__":
    unittest.main()
