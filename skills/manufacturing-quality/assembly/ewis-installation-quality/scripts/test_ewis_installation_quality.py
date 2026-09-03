"""Contract test for EWIS installation quality checks (offline, stdlib).

Run: python3 scripts/test_ewis_installation_quality.py
"""

import unittest

from ewis_installation_quality_logic import (
    PI,
    BEND_FACTOR_DEFAULT,
    FILL_LIMIT,
    VOLTAGE_DROP_LIMIT_PCT,
    bend_radius_check,
    bundle_fill_ratio,
    ewis_installation_report,
    fill_check,
    round_trip_resistance,
    separation_check,
    voltage_drop,
    wire_area,
)


class WireAreaTests(unittest.TestCase):
    def test_wire_area_worked_conductor(self):
        self.assertAlmostEqual(wire_area(2.0), PI, places=9)

    def test_wire_area_unit_and_scaling(self):
        self.assertAlmostEqual(wire_area(1.0), PI / 4.0, places=9)
        self.assertAlmostEqual(wire_area(4.0), 4.0 * wire_area(2.0),
                               places=9)


class BundleFillRatioTests(unittest.TestCase):
    def test_fill_ratio_worked_example_bound(self):
        ratio = bundle_fill_ratio([2.0] * 12, 12.0)
        self.assertAlmostEqual(ratio, 1.0 / 3.0, places=6)
        self.assertGreaterEqual(ratio, 0.30)
        self.assertLessEqual(ratio, 0.37)

    def test_fill_ratio_area_identity(self):
        # N wires of diameter d in conduit D: fill = N * d**2 / D**2.
        self.assertAlmostEqual(bundle_fill_ratio([1.0] * 8, 4.0),
                               8.0 * 1.0 / 16.0, places=9)

    def test_fill_ratio_mixed_diameters(self):
        # 2 x 2 mm plus 1 x 4 mm in a 10 mm conduit: 6*pi / 25*pi = 6/25.
        self.assertAlmostEqual(bundle_fill_ratio([2.0, 2.0, 4.0], 10.0),
                               6.0 / 25.0, places=9)

    def test_fill_ratio_valueerrors(self):
        bad_calls = [([2.0], 0.0), ([2.0], -1.0), ([], 12.0),
                     ([2.0, 0.0], 12.0), ([-2.0], 12.0)]
        for wires, conduit in bad_calls:
            with self.subTest(wires=wires, conduit=conduit):
                with self.assertRaises(ValueError):
                    bundle_fill_ratio(wires, conduit)


class FillCheckTests(unittest.TestCase):
    def test_fill_check_worked_example_pass(self):
        verdict = fill_check(1.0 / 3.0)
        self.assertTrue(verdict["pass_bool"])
        self.assertAlmostEqual(verdict["margin"], FILL_LIMIT - 1.0 / 3.0,
                               places=9)

    def test_fill_check_boundary_exactly_at_limit_passes(self):
        verdict = fill_check(FILL_LIMIT)
        self.assertTrue(verdict["pass_bool"])
        self.assertAlmostEqual(verdict["margin"], 0.0, places=9)

    def test_fill_check_above_limit_fails(self):
        verdict = fill_check(0.45)
        self.assertFalse(verdict["pass_bool"])
        self.assertLess(verdict["margin"], 0.0)

    def test_fill_check_custom_limit(self):
        self.assertTrue(fill_check(0.50, limit=0.55)["pass_bool"])
        self.assertFalse(fill_check(0.60, limit=0.55)["pass_bool"])


class RoundTripResistanceTests(unittest.TestCase):
    def test_round_trip_worked_example_exact(self):
        self.assertEqual(round_trip_resistance(0.008, 15.0), 0.24)

    def test_round_trip_scales_and_zero_length(self):
        self.assertEqual(round_trip_resistance(0.01, 10.0), 0.2)
        self.assertEqual(round_trip_resistance(0.008, 0.0), 0.0)


class VoltageDropTests(unittest.TestCase):
    def test_voltage_drop_worked_example(self):
        verdict = voltage_drop(28.0, 5.0, 0.24)
        self.assertAlmostEqual(verdict["drop_V"], 1.2, places=9)
        self.assertAlmostEqual(verdict["drop_pct"],
                               100.0 * 1.2 / 28.0, delta=1e-9)

    def test_voltage_drop_round_trip_integration(self):
        verdict = voltage_drop(28.0, 5.0,
                               round_trip_resistance(0.008, 15.0))
        self.assertAlmostEqual(verdict["drop_pct"], 4.285714285714286,
                               places=9)

    def test_voltage_drop_zero_current_and_resistance(self):
        self.assertEqual(voltage_drop(28.0, 0.0, 0.24)["drop_V"], 0.0)
        self.assertEqual(voltage_drop(28.0, 5.0, 0.0)["drop_pct"], 0.0)

    def test_voltage_drop_valueerrors(self):
        bad_calls = [(0.0, 5.0, 0.24), (-28.0, 5.0, 0.24),
                     (28.0, -1.0, 0.24), (28.0, 5.0, -0.1)]
        for voltage, current, resistance in bad_calls:
            with self.subTest(voltage=voltage, current=current):
                with self.assertRaises(ValueError):
                    voltage_drop(voltage, current, resistance)


class BendRadiusCheckTests(unittest.TestCase):
    def test_bend_radius_worked_example_fail(self):
        verdict = bend_radius_check(2.0, 8.0)
        self.assertFalse(verdict["pass_bool"])
        self.assertEqual(verdict["required_radius"], 12.0)
        self.assertAlmostEqual(verdict["margin"], 8.0 / 12.0 - 1.0,
                               places=9)

    def test_bend_radius_default_factor_constant(self):
        self.assertEqual(BEND_FACTOR_DEFAULT, 6.0)

    def test_bend_radius_at_required_passes(self):
        verdict = bend_radius_check(2.0, 12.0)
        self.assertTrue(verdict["pass_bool"])
        self.assertAlmostEqual(verdict["margin"], 0.0, places=9)

    def test_bend_radius_above_required_passes(self):
        self.assertTrue(bend_radius_check(2.0, 15.0)["pass_bool"])

    def test_bend_radius_custom_factor(self):
        verdict = bend_radius_check(2.0, 8.0, factor=10.0)
        self.assertEqual(verdict["required_radius"], 20.0)
        self.assertFalse(verdict["pass_bool"])

    def test_bend_radius_valueerrors(self):
        for diameter in (0.0, -1.0):
            with self.subTest(diameter=diameter):
                with self.assertRaises(ValueError):
                    bend_radius_check(diameter, 8.0)
        with self.assertRaises(ValueError):
            bend_radius_check(2.0, -0.5)
        for factor in (0.0, -6.0):
            with self.subTest(factor=factor):
                with self.assertRaises(ValueError):
                    bend_radius_check(2.0, 8.0, factor=factor)


class SeparationCheckTests(unittest.TestCase):
    def test_separation_worked_example_fail(self):
        verdict = separation_check(60.0, 150.0)
        self.assertFalse(verdict["pass_bool"])
        self.assertAlmostEqual(verdict["margin"], 60.0 / 150.0 - 1.0,
                               places=9)

    def test_separation_at_required_passes(self):
        verdict = separation_check(150.0, 150.0)
        self.assertTrue(verdict["pass_bool"])
        self.assertAlmostEqual(verdict["margin"], 0.0, places=9)

    def test_separation_above_required_passes(self):
        self.assertTrue(separation_check(200.0, 150.0)["pass_bool"])

    def test_separation_valueerrors(self):
        for required in (0.0, -10.0):
            with self.subTest(required=required):
                with self.assertRaises(ValueError):
                    separation_check(60.0, required)
        with self.assertRaises(ValueError):
            separation_check(-1.0, 150.0)


class ReportTests(unittest.TestCase):
    WORKED_ARGS = (28.0, [2.0] * 12, 12.0, 0.008, 15.0, 5.0, 8.0, 60.0,
                   150.0)

    def test_report_worked_example_overall_fail(self):
        report = ewis_installation_report(*self.WORKED_ARGS)
        self.assertFalse(report["overall_pass"])
        self.assertEqual(report["failing_checks"],
                         ["voltage_drop", "bend_radius", "separation"])

    def test_report_worked_example_subverdicts(self):
        report = ewis_installation_report(*self.WORKED_ARGS)
        self.assertTrue(report["fill"]["pass_bool"])
        self.assertFalse(report["voltage_drop"]["pass_bool"])
        self.assertFalse(report["bend_radius"]["pass_bool"])
        self.assertFalse(report["separation"]["pass_bool"])
        self.assertAlmostEqual(report["fill"]["fill_ratio"], 1.0 / 3.0,
                               places=6)
        self.assertAlmostEqual(report["voltage_drop"]["drop_pct"],
                               4.285714285714286, places=9)
        self.assertEqual(report["voltage_drop"]["limit_pct"],
                         VOLTAGE_DROP_LIMIT_PCT)
        self.assertEqual(report["bend_radius"]["required_radius"], 12.0)

    def test_report_all_pass_case(self):
        report = ewis_installation_report(
            28.0, [2.0] * 12, 12.0, 0.008, 5.0, 5.0, 15.0, 150.0, 150.0)
        self.assertTrue(report["overall_pass"])
        self.assertEqual(report["failing_checks"], [])

    def test_report_custom_limits(self):
        report = ewis_installation_report(
            28.0, [2.0] * 12, 12.0, 0.008, 5.0, 5.0, 15.0, 150.0, 150.0,
            drop_limit_pct=1.0)
        self.assertFalse(report["overall_pass"])
        self.assertEqual(report["failing_checks"], ["voltage_drop"])

    def test_report_valueerror_propagates_empty_wires(self):
        with self.assertRaises(ValueError):
            ewis_installation_report(28.0, [], 12.0, 0.008, 15.0, 5.0,
                                     8.0, 60.0, 150.0)

    def test_report_determinism(self):
        first = ewis_installation_report(*self.WORKED_ARGS)
        second = ewis_installation_report(*self.WORKED_ARGS)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
