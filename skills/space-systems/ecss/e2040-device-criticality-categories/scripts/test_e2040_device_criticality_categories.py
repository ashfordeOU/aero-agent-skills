#!/usr/bin/env python3
"""Contract test for device criticality categorisation (offline)."""

import copy
import unittest

from e2040_device_criticality_categories_logic import (
    CATEGORIES,
    DERATING_PARAMETERS,
    REDUNDANCY_SCHEMES,
    SEVERITY_LEVELS,
    base_category,
    categorise_device,
    categorise_device_list,
    category_implications,
    demote_one_step,
    derated_limit,
    redundancy_credit,
    within_derating,
)

MITIGATED_DEVICE = {
    "id": "PCU-A",
    "severity": "catastrophic",
    "redundancy_scheme": "cross-strapped",
    "independent_redundancy": True,
    "detection_route": "detected-on-ground",
}

SIMPLEX_DEVICE = {
    "id": "LATCH-1",
    "severity": "critical",
    "redundancy_scheme": "none",
    "independent_redundancy": False,
    "detection_route": "detected-onboard",
}


def _device(base, **overrides):
    device = copy.deepcopy(base)
    device.update(overrides)
    return device


class BaseCategoryTests(unittest.TestCase):
    def test_a_catastrophic_effect_starts_in_the_top_category(self):
        self.assertEqual(base_category("catastrophic"), "category-1")

    def test_a_minor_effect_starts_in_the_bottom_category(self):
        self.assertEqual(base_category("minor"), "category-4")

    def test_every_severity_maps_to_a_known_category(self):
        for severity in SEVERITY_LEVELS:
            self.assertIn(base_category(severity), CATEGORIES)

    def test_an_unknown_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            base_category("annoying")

    def test_demotion_moves_exactly_one_step(self):
        self.assertEqual(demote_one_step("category-1"), "category-2")
        self.assertEqual(demote_one_step("category-2"), "category-3")

    def test_the_bottom_category_does_not_move(self):
        self.assertEqual(demote_one_step("category-4"), "category-4")

    def test_demoting_an_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            demote_one_step("category-9")


class RedundancyCreditTests(unittest.TestCase):
    def test_an_independent_detected_cross_strap_earns_the_credit(self):
        result = redundancy_credit("cross-strapped", True, "detected-on-ground")
        self.assertTrue(result["credited"])
        self.assertEqual(result["findings"], [])

    def test_no_redundant_path_earns_nothing(self):
        result = redundancy_credit("none", False, "detected-onboard")
        self.assertFalse(result["credited"])
        self.assertTrue(any("no redundant path" in f for f in result["findings"]))

    def test_a_shared_cause_kills_the_credit(self):
        result = redundancy_credit("hot-standby", False, "detected-onboard")
        self.assertFalse(result["credited"])
        self.assertTrue(any("shares a cause" in f for f in result["findings"]))

    def test_a_cold_standby_needs_onboard_detection(self):
        self.assertFalse(
            redundancy_credit("cold-standby", True, "detected-on-ground")["credited"]
        )
        self.assertTrue(
            redundancy_credit("cold-standby", True, "detected-onboard")["credited"]
        )

    def test_an_undetected_failure_never_earns_the_credit(self):
        for scheme in REDUNDANCY_SCHEMES:
            self.assertFalse(
                redundancy_credit(scheme, True, "undetected")["credited"]
            )

    def test_an_unknown_detection_route_is_rejected(self):
        with self.assertRaises(ValueError):
            redundancy_credit("hot-standby", True, "probably-noticed")

    def test_a_non_boolean_independence_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            redundancy_credit("hot-standby", "yes", "detected-onboard")


class ImplicationTests(unittest.TestCase):
    def test_the_top_two_categories_forbid_a_single_point_failure(self):
        for category in ("category-1", "category-2"):
            self.assertFalse(
                category_implications(category)["single_point_failure_permitted"]
            )

    def test_the_lower_categories_permit_one(self):
        for category in ("category-3", "category-4"):
            self.assertTrue(
                category_implications(category)["single_point_failure_permitted"]
            )

    def test_every_category_carries_a_documentation_set(self):
        for category in CATEGORIES:
            self.assertTrue(category_implications(category)["documentation"])

    def test_every_category_carries_a_factor_for_every_parameter(self):
        for category in CATEGORIES:
            factors = category_implications(category)["derating_factors"]
            for parameter in DERATING_PARAMETERS:
                self.assertIn(parameter, factors)

    def test_an_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            category_implications("category-0")


class DeratingTests(unittest.TestCase):
    def test_the_top_category_halves_a_voltage_rating(self):
        self.assertAlmostEqual(derated_limit(100.0, "category-1", "voltage"), 50.0, places=9)

    def test_a_lower_category_allows_more_stress(self):
        self.assertGreater(
            derated_limit(100.0, "category-4", "current"),
            derated_limit(100.0, "category-1", "current"),
        )

    def test_a_stress_exactly_on_the_limit_is_compliant(self):
        limit = derated_limit(37.0, "category-2", "power")
        self.assertTrue(within_derating(limit, 37.0, "category-2", "power"))

    def test_a_stress_above_the_limit_is_not_compliant(self):
        self.assertFalse(within_derating(60.0, 100.0, "category-1", "voltage"))

    def test_a_zero_stress_is_compliant(self):
        self.assertTrue(within_derating(0.0, 100.0, "category-1", "voltage"))

    def test_a_negative_applied_stress_is_rejected(self):
        with self.assertRaises(ValueError):
            within_derating(-1.0, 100.0, "category-1", "voltage")

    def test_a_zero_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            derated_limit(0.0, "category-1", "voltage")

    def test_an_unknown_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            derated_limit(100.0, "category-1", "vibration")


class DeviceTests(unittest.TestCase):
    def test_a_mitigated_catastrophic_device_drops_one_category(self):
        result = categorise_device(MITIGATED_DEVICE)
        self.assertEqual(result["base_category"], "category-1")
        self.assertEqual(result["category"], "category-2")
        self.assertTrue(result["redundancy_credited"])
        self.assertFalse(result["single_point_failure"])

    def test_a_simplex_device_keeps_its_base_category(self):
        result = categorise_device(SIMPLEX_DEVICE)
        self.assertEqual(result["category"], "category-2")
        self.assertFalse(result["redundancy_credited"])
        self.assertTrue(result["single_point_failure"])

    def test_a_simplex_top_category_device_raises_the_deviation_duty(self):
        result = categorise_device(_device(SIMPLEX_DEVICE, severity="catastrophic"))
        self.assertEqual(result["category"], "category-1")
        self.assertTrue(any("approved deviation" in f for f in result["findings"]))

    def test_a_dormant_standby_is_not_credited(self):
        result = categorise_device(
            _device(MITIGATED_DEVICE, redundancy_scheme="cold-standby",
                    detection_route="detected-on-ground")
        )
        self.assertFalse(result["redundancy_credited"])
        self.assertEqual(result["category"], "category-1")

    def test_credit_is_never_two_steps(self):
        result = categorise_device(MITIGATED_DEVICE)
        base_index = CATEGORIES.index(result["base_category"])
        final_index = CATEGORIES.index(result["category"])
        self.assertEqual(final_index - base_index, 1)

    def test_an_overstressed_device_reports_the_derating_finding(self):
        device = _device(
            MITIGATED_DEVICE,
            applied_stress={"voltage": {"rating": 100.0, "applied": 75.0}},
        )
        result = categorise_device(device)
        self.assertFalse(result["derating_verdicts"]["voltage"]["compliant"])
        self.assertTrue(any("derated limit" in f for f in result["findings"]))

    def test_a_device_on_the_derating_limit_is_compliant(self):
        limit = derated_limit(100.0, "category-2", "voltage")
        device = _device(
            MITIGATED_DEVICE,
            applied_stress={"voltage": {"rating": 100.0, "applied": limit}},
        )
        result = categorise_device(device)
        self.assertTrue(result["derating_verdicts"]["voltage"]["compliant"])

    def test_a_device_without_an_id_is_rejected(self):
        with self.assertRaises(ValueError):
            categorise_device(_device(MITIGATED_DEVICE, id=""))

    def test_a_non_mapping_device_is_rejected(self):
        with self.assertRaises(ValueError):
            categorise_device("PCU-A")

    def test_a_non_mapping_applied_stress_is_rejected(self):
        with self.assertRaises(ValueError):
            categorise_device(_device(MITIGATED_DEVICE, applied_stress=[1, 2]))


class DeviceListTests(unittest.TestCase):
    def test_the_roll_up_counts_every_device(self):
        summary = categorise_device_list([MITIGATED_DEVICE, SIMPLEX_DEVICE])
        self.assertEqual(sum(summary["counts"].values()), 2)

    def test_the_governing_category_is_the_most_severe_present(self):
        summary = categorise_device_list(
            [MITIGATED_DEVICE, _device(SIMPLEX_DEVICE, severity="catastrophic")]
        )
        self.assertEqual(summary["governing_category"], "category-1")

    def test_the_single_point_failure_list_names_the_simplex_device(self):
        summary = categorise_device_list([MITIGATED_DEVICE, SIMPLEX_DEVICE])
        self.assertEqual(summary["single_point_failures"], ["LATCH-1"])

    def test_the_deviation_list_names_only_the_forbidden_cases(self):
        summary = categorise_device_list(
            [SIMPLEX_DEVICE, _device(SIMPLEX_DEVICE, id="HEATER-3", severity="minor")]
        )
        self.assertEqual(summary["deviation_required"], ["LATCH-1"])

    def test_a_duplicate_device_id_is_rejected(self):
        with self.assertRaises(ValueError):
            categorise_device_list([SIMPLEX_DEVICE, copy.deepcopy(SIMPLEX_DEVICE)])

    def test_an_empty_device_list_is_rejected(self):
        with self.assertRaises(ValueError):
            categorise_device_list([])


if __name__ == "__main__":
    unittest.main()
