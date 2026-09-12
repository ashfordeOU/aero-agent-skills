#!/usr/bin/env python3
"""Gate 3 contract test for e20-failure-propagation-general-requirements.

stdlib unittest, offline, deterministic. Run:
python3 test_e20_failure_propagation_general_requirements.py
"""

import unittest

from e20_failure_propagation_general_requirements_logic import (
    DEFAULT_CLEARING_MARGIN,
    DEFAULT_LOAD_MARGIN,
    barrier_blocks,
    containment_review,
    containment_violations,
    fault_family,
    is_single_fault_contained,
    propagation_blocked,
    protection_selectivity,
    protection_violations,
)


class TestFaultFamily(unittest.TestCase):
    def test_conducted_overcurrent_modes_share_a_family(self):
        self.assertEqual(fault_family("short_to_ground"), "conducted_overcurrent")
        self.assertEqual(fault_family("pin_to_pin_short"), "conducted_overcurrent")

    def test_each_family_is_reachable(self):
        self.assertEqual(fault_family("regulator_runaway"), "conducted_overvoltage")
        self.assertEqual(fault_family("open_circuit"), "loss_of_continuity")
        self.assertEqual(
            fault_family("surface_arc_tracking"), "dielectric_breakdown"
        )

    def test_unrecognized_fault_mode_raises(self):
        with self.assertRaises(ValueError):
            fault_family("cosmic_ray_upset")

    def test_unhashable_fault_mode_raises_value_error(self):
        with self.assertRaises(ValueError):
            fault_family(["short_to_ground"])


class TestBarrierCoverage(unittest.TestCase):
    def test_protection_device_covers_bus_overcurrent_only(self):
        self.assertTrue(
            barrier_blocks(
                "series_protection_device",
                "conducted_overcurrent",
                "shared_power_bus",
            )
        )
        self.assertFalse(
            barrier_blocks(
                "series_protection_device",
                "loss_of_continuity",
                "shared_power_bus",
            )
        )

    def test_redundant_branch_is_the_continuity_barrier(self):
        self.assertTrue(
            barrier_blocks(
                "redundant_supply_branch",
                "loss_of_continuity",
                "shared_power_bus",
            )
        )
        self.assertFalse(
            barrier_blocks(
                "redundant_supply_branch",
                "conducted_overcurrent",
                "shared_power_bus",
            )
        )

    def test_barrier_outside_its_path_is_not_credited(self):
        self.assertFalse(
            barrier_blocks(
                "dedicated_return",
                "conducted_overcurrent",
                "harness_adjacency",
            )
        )

    def test_unrecognized_barrier_raises(self):
        with self.assertRaises(ValueError):
            barrier_blocks("kapton_tape", "conducted_overcurrent", "shared_power_bus")

    def test_unrecognized_family_raises(self):
        with self.assertRaises(ValueError):
            barrier_blocks("dedicated_return", "magnetic_coupling", "shared_power_bus")

    def test_unrecognized_path_raises(self):
        with self.assertRaises(ValueError):
            barrier_blocks(
                "dedicated_return", "conducted_overcurrent", "rf_backdoor"
            )


class TestPropagationBlocked(unittest.TestCase):
    def test_first_covering_barrier_is_named(self):
        result = propagation_blocked(
            "short_to_ground",
            "shared_power_bus",
            ["dedicated_return", "series_protection_device"],
        )
        self.assertTrue(result["blocked"])
        self.assertEqual(result["barrier"], "series_protection_device")
        self.assertEqual(result["family"], "conducted_overcurrent")

    def test_empty_barrier_set_leaves_pair_uncontained(self):
        result = propagation_blocked("short_to_supply", "common_connector_pin", [])
        self.assertFalse(result["blocked"])
        self.assertIsNone(result["barrier"])

    def test_unrecognized_path_raises(self):
        with self.assertRaises(ValueError):
            propagation_blocked("short_to_ground", "rf_backdoor", [])


class TestProtectionSelectivity(unittest.TestCase):
    def test_selective_device_reports_both_ratios(self):
        result = protection_selectivity(2.0, 4.0, 12.0)
        self.assertTrue(result["selective"])
        self.assertAlmostEqual(result["load_ratio"], 2.0)
        self.assertAlmostEqual(result["clearing_ratio"], 3.0)
        self.assertEqual(result["findings"], [])

    def test_margins_exactly_met_are_selective(self):
        result = protection_selectivity(
            4.0, 4.0 * DEFAULT_LOAD_MARGIN, 4.0 * DEFAULT_LOAD_MARGIN * DEFAULT_CLEARING_MARGIN
        )
        self.assertTrue(result["selective"])
        self.assertAlmostEqual(result["load_ratio"], DEFAULT_LOAD_MARGIN)
        self.assertAlmostEqual(result["clearing_ratio"], DEFAULT_CLEARING_MARGIN)

    def test_rating_too_close_to_demand_is_flagged(self):
        result = protection_selectivity(4.0, 4.4, 20.0)
        self.assertFalse(result["selective"])
        self.assertIn("protection_rating_below_load_margin", result["findings"])
        self.assertAlmostEqual(result["load_ratio"], 1.1)

    def test_source_limiting_before_the_device_is_flagged(self):
        result = protection_selectivity(2.0, 6.0, 9.0)
        self.assertFalse(result["selective"])
        self.assertIn("source_limits_before_protection_clears", result["findings"])
        self.assertAlmostEqual(result["clearing_ratio"], 1.5)

    def test_both_failures_reported_together(self):
        result = protection_selectivity(5.0, 5.5, 6.0)
        self.assertEqual(len(result["findings"]), 2)

    def test_non_positive_current_raises(self):
        with self.assertRaises(ValueError):
            protection_selectivity(0.0, 4.0, 12.0)
        with self.assertRaises(ValueError):
            protection_selectivity(2.0, -4.0, 12.0)
        with self.assertRaises(ValueError):
            protection_selectivity(2.0, 4.0, 0.0)

    def test_margin_below_unity_raises(self):
        with self.assertRaises(ValueError):
            protection_selectivity(2.0, 4.0, 12.0, load_margin=0.9)
        with self.assertRaises(ValueError):
            protection_selectivity(2.0, 4.0, 12.0, clearing_margin=0.5)


class TestItemReview(unittest.TestCase):
    def _contained_item(self):
        return {
            "item_id": "PCDU-LCL-07",
            "fault_modes": ["short_to_ground", "open_circuit"],
            "couplings": [{"neighbour": "RW-A", "path": "shared_power_bus"}],
            "barriers": ["series_protection_device", "redundant_supply_branch"],
            "protection": {
                "steady_demand_a": 2.0,
                "protection_rating_a": 4.0,
                "source_current_limit_a": 12.0,
            },
        }

    def test_fully_contained_item_reports_no_findings(self):
        review = containment_review(self._contained_item())
        self.assertEqual(review["propagation"], [])
        self.assertEqual(review["protection"], [])
        self.assertTrue(is_single_fault_contained(review))

    def test_missing_continuity_barrier_is_a_propagation_finding(self):
        item = self._contained_item()
        item["barriers"] = ["series_protection_device"]
        findings = containment_violations(item)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["fault_mode"], "open_circuit")
        self.assertEqual(findings[0]["family"], "loss_of_continuity")
        self.assertEqual(findings[0]["neighbour"], "RW-A")

    def test_every_uncontained_pair_is_reported(self):
        item = self._contained_item()
        item["barriers"] = []
        item["couplings"].append(
            {"neighbour": "STR-B", "path": "harness_adjacency"}
        )
        findings = containment_violations(item)
        self.assertEqual(len(findings), 4)

    def test_credited_protection_device_without_sizing_is_a_finding(self):
        item = self._contained_item()
        del item["protection"]
        findings = protection_violations(item)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "credited_protection_device_not_sized"
        )

    def test_item_without_protection_device_needs_no_sizing(self):
        item = {
            "item_id": "SA-STR-03",
            "fault_modes": ["insulation_breakdown"],
            "couplings": [{"neighbour": "SA-STR-04", "path": "harness_adjacency"}],
            "barriers": ["physical_separation"],
        }
        review = containment_review(item)
        self.assertTrue(is_single_fault_contained(review))

    def test_unsized_protection_defeats_the_argument(self):
        item = self._contained_item()
        item["protection"]["source_current_limit_a"] = 5.0
        review = containment_review(item)
        self.assertEqual(review["propagation"], [])
        self.assertFalse(is_single_fault_contained(review))

    def test_missing_item_id_raises(self):
        with self.assertRaises(ValueError):
            containment_violations({"fault_modes": [], "couplings": []})
        with self.assertRaises(ValueError):
            protection_violations({"item_id": "", "barriers": []})

    def test_review_does_not_mutate_the_item(self):
        item = self._contained_item()
        before = {
            "fault_modes": list(item["fault_modes"]),
            "barriers": list(item["barriers"]),
            "couplings": list(item["couplings"]),
        }
        containment_review(item)
        self.assertEqual(item["fault_modes"], before["fault_modes"])
        self.assertEqual(item["barriers"], before["barriers"])
        self.assertEqual(item["couplings"], before["couplings"])


if __name__ == "__main__":
    unittest.main()
