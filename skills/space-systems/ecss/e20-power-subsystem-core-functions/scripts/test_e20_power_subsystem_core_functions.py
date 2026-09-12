#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.2.2.1 power subsystem
core functions.

Exercises scripts/e20_power_subsystem_core_functions_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 - each
recognized element type maps onto the core functions it performs and an
uncategorized type raises; the coverage map lists every performing
element per function and rejects a blank or duplicated identifier; a
core function with no element is flagged, a function carried by one
element is flagged unless single-string operation is accepted, and an
energy-carrying element absent from telemetry is flagged; delivered
power is the generated power through both chain efficiencies, an
efficiency outside (0, 1] raises, and the aggregated review is
compliant only when every finding list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_power_subsystem_core_functions_logic as cf  # noqa: E402


def _elements(*pairs):
    return [
        {"element_id": element_id, "element_type": element_type}
        for element_id, element_type in pairs
    ]


COMPLETE_ELEMENTS = _elements(
    ("sa_a", "solar_array"),
    ("sa_b", "solar_array"),
    ("pcu_a", "power_conditioning_unit"),
    ("pcu_b", "power_conditioning_unit"),
    ("bat_a", "secondary_battery"),
    ("bat_b", "secondary_battery"),
    ("lcl_a", "latching_current_limiter"),
    ("lcl_b", "latching_current_limiter"),
    ("isense_a", "current_sensor"),
    ("vsense_a", "voltage_sensor"),
)

COMPLETE_MONITORED = [
    "sa_a",
    "sa_b",
    "pcu_a",
    "pcu_b",
    "bat_a",
    "bat_b",
    "lcl_a",
    "lcl_b",
]


class ElementFunctionsTest(unittest.TestCase):
    def test_solar_array_generates(self):
        self.assertEqual(cf.element_functions("solar_array"), ("generation",))

    def test_secondary_battery_stores(self):
        self.assertEqual(cf.element_functions("secondary_battery"), ("storage",))

    def test_combined_unit_performs_three_functions(self):
        functions = cf.element_functions("power_conditioning_and_distribution_unit")
        self.assertEqual(
            set(functions), {"conditioning", "distribution", "monitoring"}
        )

    def test_fuel_cell_generates_and_stores(self):
        self.assertEqual(set(cf.element_functions("fuel_cell")), {"generation", "storage"})

    def test_uncategorized_element_type_raises(self):
        with self.assertRaises(ValueError):
            cf.element_functions("flux_capacitor")


class FunctionCoverageTest(unittest.TestCase):
    def test_every_core_function_is_a_key(self):
        coverage = cf.function_coverage(COMPLETE_ELEMENTS)
        self.assertEqual(set(coverage), set(cf.CORE_FUNCTIONS))

    def test_elements_land_under_each_function(self):
        coverage = cf.function_coverage(COMPLETE_ELEMENTS)
        self.assertEqual(coverage["generation"], ["sa_a", "sa_b"])
        self.assertEqual(coverage["storage"], ["bat_a", "bat_b"])
        self.assertEqual(coverage["monitoring"], ["isense_a", "vsense_a"])

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            cf.function_coverage(_elements(("", "solar_array")))

    def test_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            cf.function_coverage(_elements(("sa_a", "solar_array"), ("sa_a", "solar_array")))


class AllocationFindingsTest(unittest.TestCase):
    def test_complete_subsystem_covers_all_five(self):
        coverage = cf.function_coverage(COMPLETE_ELEMENTS)
        self.assertEqual(cf.uncovered_functions(coverage), ())
        self.assertEqual(cf.allocation_findings(coverage), [])

    def test_missing_storage_is_flagged(self):
        coverage = cf.function_coverage(
            _elements(
                ("sa_a", "solar_array"),
                ("pcu_a", "power_conditioning_unit"),
                ("lcl_a", "latching_current_limiter"),
                ("isense_a", "current_sensor"),
            )
        )
        self.assertEqual(cf.uncovered_functions(coverage), ("storage",))
        findings = cf.allocation_findings(coverage)
        self.assertEqual(findings[0]["issue"], "core_function_not_allocated")
        self.assertEqual(findings[0]["function"], "storage")

    def test_empty_subsystem_flags_all_five(self):
        coverage = cf.function_coverage([])
        self.assertEqual(len(cf.allocation_findings(coverage)), 5)


class RedundancyFindingsTest(unittest.TestCase):
    def test_dual_string_subsystem_is_clean(self):
        coverage = cf.function_coverage(COMPLETE_ELEMENTS)
        self.assertEqual(cf.redundancy_findings(coverage, ["monitoring"]), [])

    def test_single_element_function_is_flagged(self):
        coverage = cf.function_coverage(
            _elements(
                ("sa_a", "solar_array"),
                ("sa_b", "solar_array"),
                ("pcu_a", "power_conditioning_unit"),
                ("bat_a", "secondary_battery"),
                ("bat_b", "secondary_battery"),
                ("lcl_a", "latching_current_limiter"),
                ("lcl_b", "latching_current_limiter"),
                ("isense_a", "current_sensor"),
                ("vsense_b", "voltage_sensor"),
            )
        )
        findings = cf.redundancy_findings(coverage)
        flagged = {f["function"] for f in findings}
        self.assertIn("conditioning", flagged)
        self.assertNotIn("generation", flagged)

    def test_accepted_single_string_is_not_flagged(self):
        coverage = cf.function_coverage(
            _elements(
                ("sa_a", "solar_array"),
                ("sa_b", "solar_array"),
                ("pcu_a", "power_conditioning_unit"),
                ("bat_a", "secondary_battery"),
                ("bat_b", "secondary_battery"),
                ("lcl_a", "latching_current_limiter"),
                ("lcl_b", "latching_current_limiter"),
                ("isense_a", "current_sensor"),
                ("vsense_b", "voltage_sensor"),
            )
        )
        findings = cf.redundancy_findings(coverage, ["conditioning"])
        self.assertEqual(findings, [])

    def test_uncategorized_accepted_function_raises(self):
        coverage = cf.function_coverage(COMPLETE_ELEMENTS)
        with self.assertRaises(ValueError):
            cf.redundancy_findings(coverage, ["propulsion"])


class MonitoringFindingsTest(unittest.TestCase):
    def test_fully_monitored_subsystem_is_clean(self):
        self.assertEqual(
            cf.monitoring_findings(COMPLETE_ELEMENTS, COMPLETE_MONITORED), []
        )

    def test_unmonitored_battery_is_flagged(self):
        monitored = [e for e in COMPLETE_MONITORED if e != "bat_b"]
        findings = cf.monitoring_findings(COMPLETE_ELEMENTS, monitored)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["element_id"], "bat_b")
        self.assertEqual(findings[0]["issue"], "element_not_observable_in_telemetry")

    def test_sensor_itself_needs_no_observation(self):
        findings = cf.monitoring_findings(COMPLETE_ELEMENTS, COMPLETE_MONITORED)
        self.assertEqual([f["element_id"] for f in findings], [])

    def test_monitoring_an_undeclared_element_raises(self):
        with self.assertRaises(ValueError):
            cf.monitoring_findings(COMPLETE_ELEMENTS, ["ghost_unit"])


class DeliveredPowerTest(unittest.TestCase):
    def test_chain_efficiencies_multiply(self):
        self.assertAlmostEqual(
            cf.end_to_end_delivered_power(1000.0, 0.9, 0.95), 855.0
        )

    def test_unit_efficiency_delivers_everything(self):
        self.assertAlmostEqual(cf.end_to_end_delivered_power(500.0, 1.0, 1.0), 500.0)

    def test_zero_generation_delivers_nothing(self):
        self.assertAlmostEqual(cf.end_to_end_delivered_power(0.0, 0.9, 0.9), 0.0)

    def test_negative_generation_raises(self):
        with self.assertRaises(ValueError):
            cf.end_to_end_delivered_power(-1.0, 0.9, 0.9)

    def test_zero_efficiency_raises(self):
        with self.assertRaises(ValueError):
            cf.end_to_end_delivered_power(100.0, 0.0, 0.9)

    def test_efficiency_above_unity_raises(self):
        with self.assertRaises(ValueError):
            cf.end_to_end_delivered_power(100.0, 0.9, 1.2)

    def test_loss_is_the_chain_difference(self):
        self.assertAlmostEqual(cf.conversion_loss_w(1000.0, 855.0), 145.0)

    def test_delivered_above_generated_raises(self):
        with self.assertRaises(ValueError):
            cf.conversion_loss_w(100.0, 101.0)

    def test_negative_loss_input_raises(self):
        with self.assertRaises(ValueError):
            cf.conversion_loss_w(-1.0, 0.0)


class SubsystemReviewTest(unittest.TestCase):
    def test_complete_subsystem_is_compliant(self):
        review = cf.subsystem_review(
            {
                "elements": COMPLETE_ELEMENTS,
                "monitored_element_ids": COMPLETE_MONITORED,
                "single_string_accepted": ["monitoring"],
                "generated_power_w": 1000.0,
                "conditioning_efficiency": 0.9,
                "distribution_efficiency": 0.95,
            }
        )
        self.assertAlmostEqual(review["delivered_power_w"], 855.0)
        self.assertAlmostEqual(review["conversion_loss_w"], 145.0)
        self.assertTrue(cf.is_core_function_compliant(review))

    def test_gapped_subsystem_is_not_compliant(self):
        review = cf.subsystem_review(
            {
                "elements": _elements(
                    ("sa_a", "solar_array"),
                    ("pcu_a", "power_conditioning_unit"),
                    ("lcl_a", "latching_current_limiter"),
                ),
                "monitored_element_ids": [],
                "single_string_accepted": [],
                "generated_power_w": 200.0,
                "conditioning_efficiency": 0.85,
                "distribution_efficiency": 0.98,
            }
        )
        self.assertEqual(len(review["allocation"]), 2)
        self.assertEqual(len(review["monitoring"]), 3)
        self.assertFalse(cf.is_core_function_compliant(review))


if __name__ == "__main__":
    unittest.main()
