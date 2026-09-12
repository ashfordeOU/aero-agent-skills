#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.4 power interface
specification.

Exercises scripts/e20_power_interface_specification_logic.py (stdlib
unittest, offline). Contract: an interface kind maps to exactly one
category and an unrecognized kind raises; the mandatory field list
follows the category, and a field that is absent or left as None is
reported; the delivered voltage is the source voltage less the harness
drop and is checked at the maximum-current/minimum-source corner and
the minimum-current/maximum-source corner, with an inverted load window
raising; the constant-power load impedance is voltage squared over
power; the source output impedance is the series resistance and
inductance magnitude at the analysis frequency; the separation margin
is twenty times the base-ten logarithm of the impedance ratio against a
required minimum; and the aggregated review is compliant only when
every list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_power_interface_specification_logic as ps  # noqa: E402


def _full_external_fields():
    return {
        "nominal_voltage_v": 28.0,
        "voltage_range_v": (26.0, 29.0),
        "current_limit_a": 5.0,
        "source_impedance_ohm": 0.05,
        "load_impedance_ohm": 15.7,
        "return_and_bonding": "single-point return, bonded chassis",
        "connector_pin_allocation": "D38999 pins 1/2 power, 3/4 return",
        "isolation_and_protection": "latching current limiter, 6 A",
    }


def _clean_interface():
    """An external interface that satisfies every clause 5.4 check."""
    return {
        "interface_id": "EPS-PLD-01",
        "interface_kind": "payload_power_feed",
        "declared_fields": _full_external_fields(),
        "static_case": {
            "source_voltage_min_v": 26.0,
            "source_voltage_max_v": 29.0,
            "current_max_a": 4.0,
            "current_min_a": 0.5,
            "harness_resistance_ohm": 0.1,
            "load_voltage_min_v": 22.0,
            "load_voltage_max_v": 30.0,
        },
        "interface_voltage_v": 28.0,
        "load_power_w": 50.0,
        "source_series_resistance_ohm": 0.05,
        "source_series_inductance_h": 2.0e-6,
        "analysis_frequency_hz": 1000.0,
    }


class CategorizeInterfaceTest(unittest.TestCase):
    def test_array_to_regulator_is_internal(self):
        self.assertEqual(ps.categorize_interface("array_to_regulator"), "internal")

    def test_battery_to_bus_is_internal(self):
        self.assertEqual(ps.categorize_interface("battery_to_bus"), "internal")

    def test_payload_power_feed_is_external(self):
        self.assertEqual(
            ps.categorize_interface("payload_power_feed"), "external"
        )

    def test_umbilical_is_external(self):
        self.assertEqual(ps.categorize_interface("umbilical"), "external")

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            ps.categorize_interface("thermal_strap")


class RequiredFieldsTest(unittest.TestCase):
    def test_internal_requires_regulation_mode(self):
        self.assertIn(
            "regulation_mode", ps.required_specification_fields("internal")
        )

    def test_external_requires_connector_pin_allocation(self):
        self.assertIn(
            "connector_pin_allocation",
            ps.required_specification_fields("external"),
        )

    def test_external_does_not_require_regulation_mode(self):
        self.assertNotIn(
            "regulation_mode", ps.required_specification_fields("external")
        )

    def test_both_categories_require_impedance_pair(self):
        for category in ("internal", "external"):
            fields = ps.required_specification_fields(category)
            self.assertIn("source_impedance_ohm", fields)
            self.assertIn("load_impedance_ohm", fields)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            ps.required_specification_fields("orbital")


class MissingFieldsTest(unittest.TestCase):
    def test_complete_sheet_has_no_missing_field(self):
        self.assertEqual(
            ps.missing_specification_fields(_full_external_fields(), "external"),
            [],
        )

    def test_absent_field_is_reported(self):
        fields = _full_external_fields()
        del fields["source_impedance_ohm"]
        self.assertEqual(
            ps.missing_specification_fields(fields, "external"),
            ["source_impedance_ohm"],
        )

    def test_field_present_as_none_counts_as_missing(self):
        fields = _full_external_fields()
        fields["load_impedance_ohm"] = None
        self.assertEqual(
            ps.missing_specification_fields(fields, "external"),
            ["load_impedance_ohm"],
        )

    def test_missing_fields_are_sorted(self):
        missing = ps.missing_specification_fields({}, "internal")
        self.assertEqual(missing, sorted(missing))
        self.assertEqual(len(missing), 7)

    def test_external_sheet_checked_against_external_list_only(self):
        fields = _full_external_fields()
        self.assertNotIn(
            "regulation_mode",
            ps.missing_specification_fields(fields, "external"),
        )


class HarnessAndDeliveredVoltageTest(unittest.TestCase):
    def test_harness_drop_is_current_times_resistance(self):
        self.assertAlmostEqual(ps.harness_voltage_drop(4.0, 0.1), 0.4)

    def test_zero_current_gives_zero_drop(self):
        self.assertAlmostEqual(ps.harness_voltage_drop(0.0, 0.1), 0.0)

    def test_delivered_voltage_subtracts_the_drop(self):
        self.assertAlmostEqual(ps.delivered_voltage(28.0, 4.0, 0.1), 27.6)

    def test_negative_current_raises(self):
        with self.assertRaises(ValueError):
            ps.harness_voltage_drop(-1.0, 0.1)

    def test_negative_resistance_raises(self):
        with self.assertRaises(ValueError):
            ps.harness_voltage_drop(4.0, -0.1)

    def test_non_positive_source_voltage_raises(self):
        with self.assertRaises(ValueError):
            ps.delivered_voltage(0.0, 4.0, 0.1)


class StaticInterfaceFindingsTest(unittest.TestCase):
    def test_compatible_case_has_no_finding(self):
        self.assertEqual(
            ps.static_interface_findings(
                "IF-1", _clean_interface()["static_case"]
            ),
            [],
        )

    def test_excessive_harness_drop_is_reported(self):
        case = _clean_interface()["static_case"]
        case["harness_resistance_ohm"] = 1.5
        findings = ps.static_interface_findings("IF-1", case)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "delivered_voltage_below_load_window"
        )
        self.assertAlmostEqual(findings[0]["delivered_v"], 20.0)

    def test_high_corner_above_load_window_is_reported(self):
        case = _clean_interface()["static_case"]
        case["load_voltage_max_v"] = 28.5
        findings = ps.static_interface_findings("IF-1", case)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "delivered_voltage_above_load_window"
        )

    def test_both_corners_can_fail_together(self):
        case = _clean_interface()["static_case"]
        case["load_voltage_min_v"] = 27.0
        case["load_voltage_max_v"] = 28.0
        self.assertEqual(len(ps.static_interface_findings("IF-1", case)), 2)

    def test_inverted_load_window_raises(self):
        case = _clean_interface()["static_case"]
        case["load_voltage_min_v"] = 31.0
        with self.assertRaises(ValueError):
            ps.static_interface_findings("IF-1", case)


class ImpedanceTest(unittest.TestCase):
    def test_constant_power_impedance_is_v_squared_over_p(self):
        self.assertAlmostEqual(
            ps.constant_power_load_impedance(28.0, 50.0), 15.68
        )

    def test_constant_power_impedance_falls_with_power(self):
        low_power = ps.constant_power_load_impedance(28.0, 10.0)
        high_power = ps.constant_power_load_impedance(28.0, 100.0)
        self.assertGreater(low_power, high_power)

    def test_non_positive_interface_voltage_raises(self):
        with self.assertRaises(ValueError):
            ps.constant_power_load_impedance(0.0, 50.0)

    def test_non_positive_load_power_raises(self):
        with self.assertRaises(ValueError):
            ps.constant_power_load_impedance(28.0, 0.0)

    def test_source_impedance_at_zero_frequency_is_resistance(self):
        self.assertAlmostEqual(
            ps.source_output_impedance(0.05, 2.0e-6, 0.0), 0.05
        )

    def test_source_impedance_includes_reactance(self):
        expected = math.sqrt(0.05**2 + (2 * math.pi * 100000.0 * 2.0e-6) ** 2)
        self.assertAlmostEqual(
            ps.source_output_impedance(0.05, 2.0e-6, 100000.0), expected
        )

    def test_zero_impedance_source_raises(self):
        with self.assertRaises(ValueError):
            ps.source_output_impedance(0.0, 0.0, 1000.0)

    def test_negative_inductance_raises(self):
        with self.assertRaises(ValueError):
            ps.source_output_impedance(0.05, -1.0e-6, 1000.0)

    def test_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            ps.source_output_impedance(0.05, 2.0e-6, -1.0)

    def test_negative_resistance_raises(self):
        with self.assertRaises(ValueError):
            ps.source_output_impedance(-0.05, 2.0e-6, 1000.0)


class ImpedanceMarginTest(unittest.TestCase):
    def test_decade_separation_is_twenty_db(self):
        self.assertAlmostEqual(ps.impedance_margin_db(0.1, 1.0), 20.0)

    def test_equal_impedances_give_zero_db(self):
        self.assertAlmostEqual(ps.impedance_margin_db(2.0, 2.0), 0.0)

    def test_load_below_source_is_negative_db(self):
        self.assertLess(ps.impedance_margin_db(10.0, 1.0), 0.0)

    def test_non_positive_source_impedance_raises(self):
        with self.assertRaises(ValueError):
            ps.impedance_margin_db(0.0, 15.0)

    def test_non_positive_load_impedance_raises(self):
        with self.assertRaises(ValueError):
            ps.impedance_margin_db(0.05, -1.0)

    def test_wide_separation_has_no_finding(self):
        self.assertEqual(ps.stability_findings("IF-1", 0.05, 15.68), [])

    def test_thin_separation_is_reported(self):
        findings = ps.stability_findings("IF-1", 8.0, 15.68)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "insufficient_impedance_separation"
        )
        self.assertAlmostEqual(
            findings[0]["margin_db"], 20.0 * math.log10(15.68 / 8.0)
        )

    def test_non_positive_minimum_margin_raises(self):
        with self.assertRaises(ValueError):
            ps.stability_findings("IF-1", 0.05, 15.68, 0.0)


class InterfaceReviewTest(unittest.TestCase):
    def test_clean_interface_is_compliant(self):
        review = ps.interface_review(_clean_interface())
        self.assertTrue(ps.is_interface_compliant(review))

    def test_missing_field_breaks_compliance(self):
        interface = _clean_interface()
        del interface["declared_fields"]["source_impedance_ohm"]
        review = ps.interface_review(interface)
        self.assertFalse(ps.is_interface_compliant(review))
        self.assertEqual(len(review["specification"]), 1)
        self.assertEqual(
            review["specification"][0]["field"], "source_impedance_ohm"
        )

    def test_soft_source_breaks_stability_only(self):
        interface = _clean_interface()
        interface["source_series_resistance_ohm"] = 10.0
        review = ps.interface_review(interface)
        self.assertEqual(len(review["stability"]), 1)
        self.assertEqual(review["specification"], [])
        self.assertEqual(review["static"], [])

    def test_unrecognized_kind_raises_in_review(self):
        interface = _clean_interface()
        interface["interface_kind"] = "thermal_strap"
        with self.assertRaises(ValueError):
            ps.interface_review(interface)

    def test_review_does_not_mutate_input(self):
        interface = _clean_interface()
        snapshot = {
            "declared_fields": dict(interface["declared_fields"]),
            "static_case": dict(interface["static_case"]),
        }
        ps.interface_review(interface)
        self.assertEqual(interface["declared_fields"], snapshot["declared_fields"])
        self.assertEqual(interface["static_case"], snapshot["static_case"])


if __name__ == "__main__":
    unittest.main()
