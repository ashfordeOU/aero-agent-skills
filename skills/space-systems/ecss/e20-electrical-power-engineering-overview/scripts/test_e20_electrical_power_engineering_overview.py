#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.1 electrical power
engineering overview.

Exercises scripts/e20_electrical_power_engineering_overview_logic.py
(stdlib unittest, offline). Contract: docs/harness-contract.md gate 3 --
every recognized element type lands in exactly one of the four chain
stages and an unrecognized type raises; the bus architecture follows
the regulation state in sunlight and eclipse, with regulation in
eclipse only rejected; eclipse energy divides the load energy by the
distribution efficiency; required capacity divides that by the depth of
discharge and the discharge efficiency; required generation adds the
recharge power to the sunlit load and divides by the conditioning
efficiency; the power margin is fractional headroom; each of those
raises across its whole invalid input domain; an unpopulated stage is
flagged; and the overview closes only when the chain, storage and
generation finding lists are all empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_electrical_power_engineering_overview_logic as pw  # noqa: E402


class CategorizePowerElementTest(unittest.TestCase):
    def test_solar_array_is_generation(self):
        self.assertEqual(pw.categorize_power_element("solar_array"), "generation")

    def test_secondary_battery_is_storage(self):
        self.assertEqual(
            pw.categorize_power_element("secondary_battery"), "storage"
        )

    def test_peak_power_tracker_is_conditioning(self):
        self.assertEqual(
            pw.categorize_power_element("peak_power_tracker"), "conditioning"
        )

    def test_latching_current_limiter_is_distribution(self):
        self.assertEqual(
            pw.categorize_power_element("latching_current_limiter"), "distribution"
        )

    def test_hyphen_and_case_are_normalized(self):
        self.assertEqual(
            pw.categorize_power_element("Power-Harness"), "distribution"
        )

    def test_every_recognized_element_lands_in_a_chain_stage(self):
        for element_type in sorted(pw.ELEMENT_STAGES):
            self.assertIn(
                pw.categorize_power_element(element_type), pw.CHAIN_STAGES
            )

    def test_unknown_element_raises(self):
        with self.assertRaises(ValueError):
            pw.categorize_power_element("perpetual_motion_module")

    def test_non_string_element_raises(self):
        with self.assertRaises(ValueError):
            pw.categorize_power_element(42)


class BusArchitectureTest(unittest.TestCase):
    def test_regulated_both_ways_is_fully_regulated(self):
        self.assertEqual(
            pw.bus_architecture(True, True), pw.FULLY_REGULATED_BUS
        )

    def test_regulated_in_sunlight_only_is_sun_regulated(self):
        self.assertEqual(pw.bus_architecture(True, False), pw.SUN_REGULATED_BUS)

    def test_regulated_in_neither_is_unregulated(self):
        self.assertEqual(pw.bus_architecture(False, False), pw.UNREGULATED_BUS)

    def test_regulated_in_eclipse_only_raises(self):
        with self.assertRaises(ValueError):
            pw.bus_architecture(False, True)


class EclipseEnergyTest(unittest.TestCase):
    def test_lossless_hour_of_eclipse_is_the_load_energy(self):
        self.assertAlmostEqual(
            pw.eclipse_energy_wh(100.0, 3600.0, 1.0), 100.0, places=9
        )

    def test_distribution_loss_increases_the_delivered_energy(self):
        self.assertAlmostEqual(
            pw.eclipse_energy_wh(100.0, 3600.0, 0.5), 200.0, places=9
        )

    def test_half_hour_eclipse_halves_the_energy(self):
        self.assertAlmostEqual(
            pw.eclipse_energy_wh(240.0, 1800.0, 1.0), 120.0, places=9
        )

    def test_zero_eclipse_delivers_nothing(self):
        self.assertAlmostEqual(
            pw.eclipse_energy_wh(500.0, 0.0, 0.9), 0.0, places=12
        )

    def test_negative_load_raises(self):
        with self.assertRaises(ValueError):
            pw.eclipse_energy_wh(-1.0, 1800.0, 0.9)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            pw.eclipse_energy_wh(100.0, -1.0, 0.9)

    def test_zero_distribution_efficiency_raises(self):
        with self.assertRaises(ValueError):
            pw.eclipse_energy_wh(100.0, 1800.0, 0.0)

    def test_distribution_efficiency_above_one_raises(self):
        with self.assertRaises(ValueError):
            pw.eclipse_energy_wh(100.0, 1800.0, 1.01)


class RequiredBatteryCapacityTest(unittest.TestCase):
    def test_quarter_depth_of_discharge_quadruples_the_capacity(self):
        self.assertAlmostEqual(
            pw.required_battery_capacity_wh(100.0, 0.25, 1.0), 400.0, places=9
        )

    def test_discharge_loss_inflates_the_capacity(self):
        self.assertAlmostEqual(
            pw.required_battery_capacity_wh(100.0, 0.5, 0.8), 250.0, places=9
        )

    def test_full_depth_and_lossless_needs_exactly_the_energy(self):
        self.assertAlmostEqual(
            pw.required_battery_capacity_wh(100.0, 1.0, 1.0), 100.0, places=9
        )

    def test_negative_energy_raises(self):
        with self.assertRaises(ValueError):
            pw.required_battery_capacity_wh(-1.0, 0.5, 0.9)

    def test_zero_depth_of_discharge_raises(self):
        with self.assertRaises(ValueError):
            pw.required_battery_capacity_wh(100.0, 0.0, 0.9)

    def test_depth_of_discharge_above_one_raises(self):
        with self.assertRaises(ValueError):
            pw.required_battery_capacity_wh(100.0, 1.5, 0.9)

    def test_zero_discharge_efficiency_raises(self):
        with self.assertRaises(ValueError):
            pw.required_battery_capacity_wh(100.0, 0.5, 0.0)


class RequiredGenerationPowerTest(unittest.TestCase):
    def test_no_recharge_is_the_conditioned_sunlit_load(self):
        self.assertAlmostEqual(
            pw.required_generation_power_w(90.0, 0.0, 3600.0, 0.9, 0.9),
            100.0,
            places=9,
        )

    def test_recharge_adds_to_the_requirement(self):
        self.assertAlmostEqual(
            pw.required_generation_power_w(100.0, 90.0, 3600.0, 0.9, 1.0),
            200.0,
            places=9,
        )

    def test_shorter_sunlit_arc_raises_the_recharge_power(self):
        short = pw.required_generation_power_w(0.0, 100.0, 1800.0, 1.0, 1.0)
        long = pw.required_generation_power_w(0.0, 100.0, 3600.0, 1.0, 1.0)
        self.assertAlmostEqual(short, 200.0, places=9)
        self.assertAlmostEqual(long, 100.0, places=9)

    def test_negative_sunlit_load_raises(self):
        with self.assertRaises(ValueError):
            pw.required_generation_power_w(-1.0, 0.0, 3600.0, 0.9, 0.9)

    def test_negative_recharge_energy_raises(self):
        with self.assertRaises(ValueError):
            pw.required_generation_power_w(100.0, -1.0, 3600.0, 0.9, 0.9)

    def test_zero_sunlit_duration_raises(self):
        with self.assertRaises(ValueError):
            pw.required_generation_power_w(100.0, 50.0, 0.0, 0.9, 0.9)

    def test_zero_charge_efficiency_raises(self):
        with self.assertRaises(ValueError):
            pw.required_generation_power_w(100.0, 50.0, 3600.0, 0.0, 0.9)

    def test_conditioning_efficiency_above_one_raises(self):
        with self.assertRaises(ValueError):
            pw.required_generation_power_w(100.0, 50.0, 3600.0, 0.9, 1.2)


class PowerMarginTest(unittest.TestCase):
    def test_headroom_is_fractional(self):
        self.assertAlmostEqual(pw.power_margin(120.0, 100.0), 0.2, places=9)

    def test_exact_balance_is_zero_margin(self):
        self.assertAlmostEqual(pw.power_margin(100.0, 100.0), 0.0, places=12)

    def test_shortfall_is_negative(self):
        self.assertAlmostEqual(pw.power_margin(80.0, 100.0), -0.2, places=9)

    def test_negative_available_power_raises(self):
        with self.assertRaises(ValueError):
            pw.power_margin(-1.0, 100.0)

    def test_zero_requirement_raises(self):
        with self.assertRaises(ValueError):
            pw.power_margin(100.0, 0.0)


COMPLETE_CHAIN = (
    "solar_array",
    "secondary_battery",
    "battery_charge_regulator",
    "power_distribution_switch",
)


class ChainFindingsTest(unittest.TestCase):
    def test_complete_chain_has_no_finding(self):
        self.assertEqual(pw.chain_findings(COMPLETE_CHAIN), [])

    def test_missing_storage_and_conditioning_are_flagged(self):
        findings = pw.chain_findings(("solar_array", "power_harness"))
        stages = sorted(finding["stage"] for finding in findings)
        self.assertEqual(stages, ["conditioning", "storage"])

    def test_many_elements_in_one_stage_do_not_populate_the_rest(self):
        findings = pw.chain_findings(
            ("solar_array", "radioisotope_generator", "fuel_cell")
        )
        self.assertEqual(len(findings), 3)

    def test_unknown_element_raises(self):
        with self.assertRaises(ValueError):
            pw.chain_findings(("solar_array", "warp_core"))


def _budget(**overrides):
    budget = {
        "eclipse_load_w": 500.0,
        "eclipse_duration_s": 2100.0,
        "distribution_efficiency": 0.95,
        "depth_of_discharge": 0.4,
        "discharge_efficiency": 0.95,
        "installed_capacity_wh": 1200.0,
        "sunlit_load_w": 600.0,
        "sunlit_duration_s": 3600.0,
        "charge_efficiency": 0.9,
        "conditioning_efficiency": 0.92,
        "available_generation_w": 1200.0,
    }
    budget.update(overrides)
    return budget


class PowerChainReviewTest(unittest.TestCase):
    def test_healthy_chain_closes_with_expected_sizing(self):
        review = pw.power_chain_review(COMPLETE_CHAIN, _budget())
        self.assertTrue(pw.is_power_chain_consistent(review))
        sizing = review["sizing"]
        self.assertAlmostEqual(sizing["eclipse_energy_wh"], 307.017544, places=5)
        self.assertAlmostEqual(sizing["required_capacity_wh"], 807.940905, places=5)
        self.assertAlmostEqual(
            sizing["required_generation_w"], 1022.968048, places=5
        )
        self.assertAlmostEqual(sizing["power_margin"], 0.173057, places=5)

    def test_undersized_storage_is_flagged(self):
        review = pw.power_chain_review(
            COMPLETE_CHAIN, _budget(installed_capacity_wh=400.0)
        )
        self.assertEqual(len(review["storage"]), 1)
        self.assertEqual(
            review["storage"][0]["issue"],
            "installed_storage_below_eclipse_requirement",
        )
        self.assertFalse(pw.is_power_chain_consistent(review))

    def test_thin_generation_margin_is_flagged(self):
        review = pw.power_chain_review(
            COMPLETE_CHAIN, _budget(available_generation_w=1030.0)
        )
        self.assertEqual(len(review["generation"]), 1)
        self.assertEqual(
            review["generation"][0]["issue"], "power_margin_below_minimum"
        )
        self.assertFalse(pw.is_power_chain_consistent(review))

    def test_incomplete_chain_breaks_consistency_with_healthy_numbers(self):
        review = pw.power_chain_review(("solar_array",), _budget())
        self.assertEqual(review["storage"], [])
        self.assertEqual(review["generation"], [])
        self.assertEqual(len(review["chain"]), 3)
        self.assertFalse(pw.is_power_chain_consistent(review))

    def test_negative_installed_capacity_raises(self):
        with self.assertRaises(ValueError):
            pw.power_chain_review(
                COMPLETE_CHAIN, _budget(installed_capacity_wh=-1.0)
            )

    def test_invalid_efficiency_in_budget_raises(self):
        with self.assertRaises(ValueError):
            pw.power_chain_review(
                COMPLETE_CHAIN, _budget(conditioning_efficiency=0.0)
            )


if __name__ == "__main__":
    unittest.main()
