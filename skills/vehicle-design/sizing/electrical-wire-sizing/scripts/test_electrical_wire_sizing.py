"""Contract test for electrical_wire_sizing_logic (stdlib unittest).

Run offline: python3 scripts/test_electrical_wire_sizing.py
Covers the wave-37 electrical-wire-sizing contract: ampacity derating
anchors at 45 C, the select_gauge truth table, resistance and
voltage-drop anchors of the worked example (25 A, 10 m, 28 V bus,
45 C ambient and conductor), the identities (length doubling, percent
relation), determinism, dict key contract, and ValueError rejection of
non-physical inputs.
"""

import unittest

import electrical_wire_sizing_logic as ews


class TestAmpacity(unittest.TestCase):
    def test_ampacity_at_30c_reference(self):
        self.assertAlmostEqual(ews.ampacity("22", 30.0), 5.0 * 0.60, places=6)
        self.assertAlmostEqual(ews.ampacity("6", 30.0), 60.0 * 0.60, places=6)

    def test_ampacity_10awg_45c_anchor(self):
        # 33 * 0.60 * 0.91 = 18.0 A anchor, module output 18.018
        self.assertAlmostEqual(ews.ampacity("10", 45.0), 18.0, delta=0.2)

    def test_ampacity_8awg_45c_anchor(self):
        # 46 * 0.60 * 0.91 = 25.1 A anchor, module output 25.116
        self.assertAlmostEqual(ews.ampacity("8", 45.0), 25.1, delta=0.2)

    def test_ampacity_6awg_45c_anchor(self):
        # 60 * 0.60 * 0.91 = 32.8 A anchor, module output 32.76
        self.assertAlmostEqual(ews.ampacity("6", 45.0), 32.8, delta=0.2)

    def test_ampacity_40c_matches_0_94_constant(self):
        # linear model value at 40 C equals the documented 0.94 constant
        self.assertAlmostEqual(
            ews.ampacity("8", 40.0), 46.0 * 0.60 * ews.TEMP_DERATE, places=6
        )

    def test_ampacity_ambient_band_edges(self):
        self.assertAlmostEqual(ews.ampacity("22", 30.0), 3.0, places=6)
        self.assertAlmostEqual(
            ews.ampacity("22", 100.0), 5.0 * 0.60 * 0.58, places=6
        )

    def test_ampacity_unknown_gauge_rejected(self):
        with self.assertRaises(ValueError):
            ews.ampacity("5", 30.0)
        with self.assertRaises(ValueError):
            ews.ampacity("4/0", 30.0)

    def test_ampacity_ambient_outside_band_rejected(self):
        with self.assertRaises(ValueError):
            ews.ampacity("10", 29.0)
        with self.assertRaises(ValueError):
            ews.ampacity("10", 101.0)


class TestSelectGauge(unittest.TestCase):
    def test_select_5a_at_30c_truth_table(self):
        # 22 AWG 3.0 A, 20 AWG 4.5 A, 18 AWG 6.0 A -> smallest is 18
        self.assertEqual(ews.select_gauge(5.0, 30.0), "18")

    def test_select_25a_at_45c_anchor(self):
        # 10 AWG 18.0 A not enough, 8 AWG 25.1 A meets -> "8"
        self.assertEqual(ews.select_gauge(25.0, 45.0), "8")

    def test_select_10a_at_30c_monotone_boundary(self):
        self.assertEqual(ews.select_gauge(10.0, 30.0), "14")
        self.assertLess(ews.ampacity("16", 30.0), 10.0)
        self.assertGreaterEqual(ews.ampacity("14", 30.0), 10.0)

    def test_select_at_exact_ampacity_boundary(self):
        # 18 AWG ampacity at 30 C is exactly 6.0 A, so 6.0 A selects it
        self.assertEqual(ews.select_gauge(6.0, 30.0), "18")

    def test_select_non_positive_load_rejected(self):
        with self.assertRaises(ValueError):
            ews.select_gauge(0.0, 30.0)
        with self.assertRaises(ValueError):
            ews.select_gauge(-5.0, 30.0)

    def test_select_beyond_table_rejected(self):
        # 6 AWG derated ampacity is 36.0 A at 30 C and 32.76 A at 45 C
        with self.assertRaises(ValueError):
            ews.select_gauge(37.0, 30.0)
        with self.assertRaises(ValueError):
            ews.select_gauge(33.0, 45.0)

    def test_select_ambient_outside_band_rejected(self):
        with self.assertRaises(ValueError):
            ews.select_gauge(10.0, 29.0)


class TestResistance(unittest.TestCase):
    def test_resistance_8awg_45c_anchor(self):
        # model anchor 2.257e-3 ohm/m within 5 percent
        value = ews.resistance_per_meter("8", 45.0)
        self.assertAlmostEqual(value, 2.257e-3, delta=0.05 * 2.257e-3)

    def test_resistance_6awg_45c_anchor(self):
        self.assertAlmostEqual(ews.resistance_per_meter("6", 45.0), 1.420e-3, places=6)

    def test_resistance_temperature_ratio(self):
        # ratio r(45)/r(20) = 1 + 0.00393 * 25 = 1.09825
        ratio = ews.resistance_per_meter("8", 45.0) / ews.resistance_per_meter(
            "8", 20.0
        )
        self.assertAlmostEqual(ratio, 1.09825, places=5)

    def test_resistance_area_scaling(self):
        # resistance scales with the inverse area ratio 13.3 / 8.37
        ratio = ews.resistance_per_meter("6", 45.0) / ews.resistance_per_meter(
            "8", 45.0
        )
        self.assertAlmostEqual(ratio, 8.37 / 13.3, places=5)

    def test_resistance_unknown_gauge_rejected(self):
        with self.assertRaises(ValueError):
            ews.resistance_per_meter("0", 45.0)


class TestVoltageDrop(unittest.TestCase):
    def test_voltage_drop_8awg_anchor(self):
        # worked example drop 1.128 V within 0.05 V, module output 1.1284
        self.assertAlmostEqual(ews.voltage_drop(25.0, 10.0, "8", 45.0), 1.128, delta=0.05)

    def test_voltage_drop_6awg_anchor(self):
        # worked example drop 0.710 V within 0.05 V, module output 0.7101
        self.assertAlmostEqual(ews.voltage_drop(25.0, 10.0, "6", 45.0), 0.710, delta=0.05)

    def test_voltage_drop_doubling_length_identity(self):
        base = ews.voltage_drop(25.0, 10.0, "8", 45.0)
        doubled = ews.voltage_drop(25.0, 20.0, "8", 45.0)
        self.assertAlmostEqual(doubled, 2.0 * base, places=9)

    def test_voltage_drop_zero_length_is_zero(self):
        self.assertEqual(ews.voltage_drop(25.0, 0.0, "8", 45.0), 0.0)

    def test_voltage_drop_negative_inputs_rejected(self):
        with self.assertRaises(ValueError):
            ews.voltage_drop(25.0, -1.0, "8", 45.0)
        with self.assertRaises(ValueError):
            ews.voltage_drop(-25.0, 10.0, "8", 45.0)


class TestPercentDrop(unittest.TestCase):
    def test_percent_drop_identity(self):
        drop = ews.voltage_drop(25.0, 10.0, "8", 45.0)
        self.assertAlmostEqual(
            ews.percent_drop(drop, 28.0), 100.0 * drop / 28.0, places=9
        )

    def test_percent_drop_8awg_fail_value(self):
        # 4.03 percent exceeds the 3.0 percent bus tolerance
        self.assertAlmostEqual(
            ews.percent_drop(ews.voltage_drop(25.0, 10.0, "8", 45.0), 28.0),
            4.03,
            delta=0.05,
        )

    def test_percent_drop_non_positive_bus_rejected(self):
        with self.assertRaises(ValueError):
            ews.percent_drop(1.0, 0.0)
        with self.assertRaises(ValueError):
            ews.percent_drop(1.0, -28.0)


class TestWireSizeReview(unittest.TestCase):
    def test_review_dict_keys_exact(self):
        result = ews.wire_size_review(25.0, 10.0, 28.0, 45.0, 45.0)
        self.assertEqual(
            set(result.keys()),
            {"gauge", "ampacity", "margin_A", "voltage_drop_V", "percent_drop",
             "verdict"},
        )

    def test_review_worked_example_fail_verdict(self):
        # gauge 8 meets ampacity but 4.03 percent drop fails the 3 percent bus
        result = ews.wire_size_review(25.0, 10.0, 28.0, 45.0, 45.0)
        self.assertEqual(result["gauge"], "8")
        self.assertAlmostEqual(result["ampacity"], 25.1, delta=0.2)
        self.assertAlmostEqual(result["voltage_drop_V"], 1.128, delta=0.05)
        self.assertAlmostEqual(result["percent_drop"], 4.03, delta=0.05)
        self.assertEqual(result["verdict"], "fail")

    def test_review_short_run_pass_verdict(self):
        # same gauge over 2 m: 0.81 percent drop passes the bus tolerance
        result = ews.wire_size_review(25.0, 2.0, 28.0, 45.0, 45.0)
        self.assertEqual(result["gauge"], "8")
        self.assertEqual(result["verdict"], "pass")

    def test_review_margin_is_ampacity_minus_load(self):
        result = ews.wire_size_review(25.0, 10.0, 28.0, 45.0, 45.0)
        self.assertAlmostEqual(
            result["margin_A"], result["ampacity"] - 25.0, places=9
        )

    def test_review_upsize_to_6awg_passes(self):
        # manual upsize check: 6 AWG drop 0.710 V, 2.54 percent -> pass
        amp6 = ews.ampacity("6", 45.0)
        drop6 = ews.voltage_drop(25.0, 10.0, "6", 45.0)
        pct6 = ews.percent_drop(drop6, 28.0)
        self.assertAlmostEqual(amp6, 32.8, delta=0.2)
        self.assertAlmostEqual(drop6, 0.710, delta=0.05)
        self.assertAlmostEqual(pct6, 2.54, delta=0.05)
        self.assertLessEqual(pct6, ews.MAX_PERCENT_DROP)

    def test_review_inherits_value_errors(self):
        with self.assertRaises(ValueError):
            ews.wire_size_review(0.0, 10.0, 28.0, 45.0, 45.0)
        with self.assertRaises(ValueError):
            ews.wire_size_review(25.0, -1.0, 28.0, 45.0, 45.0)
        with self.assertRaises(ValueError):
            ews.wire_size_review(25.0, 10.0, 0.0, 45.0, 45.0)


class TestDeterminism(unittest.TestCase):
    def test_repeat_calls_identical(self):
        first = ews.wire_size_review(25.0, 10.0, 28.0, 45.0, 45.0)
        second = ews.wire_size_review(25.0, 10.0, 28.0, 45.0, 45.0)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
