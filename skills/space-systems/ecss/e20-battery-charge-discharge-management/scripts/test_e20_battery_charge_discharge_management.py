#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.7.3 battery charge and
discharge management.

Exercises scripts/e20_battery_charge_discharge_management_logic.py
(stdlib unittest, offline). Contract: a cell voltage maps to exactly
one terminal state across the zero-volt, deep-discharge, operating and
overvoltage bands, with the band edges inclusive on the side the design
intends and a negative voltage rejected; each state permits exactly one
charge stage and an unrecognized state raises; a stage current limit is
its C-rate times the rated capacity; the recovery trickle time is the
recovered capacity over that current; depth of discharge is charge
removed over rated capacity and cannot exceed it; a commanded current,
cell voltage, charge temperature or depth of discharge sitting exactly
on a limit is compliant even when it arrives as a float sum that
overshoots in the last place; a zero-volt pack needs a charger that
declares it can restart from there; and the aggregated review is
compliant only when every list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_battery_charge_discharge_management_logic as bm  # noqa: E402


def _clean_battery():
    """A battery in the normal band whose charger command, temperature,
    recovery capability and discharge state all hold."""
    return {
        "battery_id": "bat_main",
        "capacity_ah": 50.0,
        "cell_voltage_v": 3.7,
        "cell_temperature_c": 15.0,
        "charge_temperature_window_c": (0.0, 45.0),
        "command": {
            "stage": "bulk_constant_current",
            "current_a": 25.0,
            "cell_voltage_v": 3.7,
        },
        "charger": {
            "supports_zero_volt_recovery": True,
            "recovery_fraction": 0.05,
            "maximum_recovery_time_h": 6.0,
        },
        "discharge": {
            "discharged_ah": 15.0,
            "capacity_ah": 50.0,
            "end_of_discharge_voltage_v": 3.0,
        },
        "discharge_limits": {
            "maximum_depth_of_discharge": 0.4,
            "end_of_discharge_voltage_floor_v": 2.8,
        },
    }


def _zero_volt_battery():
    battery = _clean_battery()
    battery["cell_voltage_v"] = 0.2
    battery["command"] = {
        "stage": "recovery_trickle",
        "current_a": 1.0,
        "cell_voltage_v": 0.2,
    }
    return battery


class TestCellThresholds(unittest.TestCase):
    def test_defaults_are_returned_when_none_given(self):
        limits = bm.validate_cell_thresholds(None)
        self.assertAlmostEqual(limits["zero_volt_ceiling_v"], 0.5, places=9)
        self.assertAlmostEqual(limits["max_charge_voltage_v"], 4.2, places=9)

    def test_custom_thresholds_are_accepted(self):
        limits = bm.validate_cell_thresholds(
            {
                "zero_volt_ceiling_v": 0.3,
                "deep_discharge_ceiling_v": 2.2,
                "max_charge_voltage_v": 4.1,
            }
        )
        self.assertAlmostEqual(limits["deep_discharge_ceiling_v"], 2.2, places=9)

    def test_missing_threshold_key_raises(self):
        with self.assertRaises(ValueError):
            bm.validate_cell_thresholds(
                {"zero_volt_ceiling_v": 0.5, "max_charge_voltage_v": 4.2}
            )

    def test_non_positive_threshold_raises(self):
        with self.assertRaises(ValueError):
            bm.validate_cell_thresholds(
                {
                    "zero_volt_ceiling_v": 0.0,
                    "deep_discharge_ceiling_v": 2.5,
                    "max_charge_voltage_v": 4.2,
                }
            )

    def test_non_increasing_thresholds_raise(self):
        with self.assertRaises(ValueError):
            bm.validate_cell_thresholds(
                {
                    "zero_volt_ceiling_v": 2.6,
                    "deep_discharge_ceiling_v": 2.5,
                    "max_charge_voltage_v": 4.2,
                }
            )


class TestCellStateCategorization(unittest.TestCase):
    def test_normal_band_is_operating(self):
        self.assertEqual(bm.categorize_cell_state(3.7), "operating")

    def test_flat_cell_is_zero_volt(self):
        self.assertEqual(bm.categorize_cell_state(0.2), "zero_volt")

    def test_exactly_at_the_zero_volt_ceiling_is_zero_volt(self):
        self.assertEqual(bm.categorize_cell_state(0.5), "zero_volt")

    def test_between_the_ceilings_is_deep_discharge(self):
        self.assertEqual(bm.categorize_cell_state(2.0), "deep_discharge")

    def test_exactly_at_the_deep_discharge_ceiling_is_operating(self):
        self.assertEqual(bm.categorize_cell_state(2.5), "operating")

    def test_exactly_at_the_maximum_charge_voltage_is_operating(self):
        self.assertEqual(bm.categorize_cell_state(4.2), "operating")

    def test_above_the_maximum_charge_voltage_is_overvoltage(self):
        self.assertEqual(bm.categorize_cell_state(4.3), "overvoltage")

    def test_zero_volts_is_the_zero_volt_state(self):
        self.assertEqual(bm.categorize_cell_state(0.0), "zero_volt")

    def test_negative_cell_voltage_raises(self):
        with self.assertRaises(ValueError):
            bm.categorize_cell_state(-0.1)

    def test_custom_thresholds_move_the_bands(self):
        thresholds = {
            "zero_volt_ceiling_v": 1.0,
            "deep_discharge_ceiling_v": 3.0,
            "max_charge_voltage_v": 4.0,
        }
        self.assertEqual(bm.categorize_cell_state(0.9, thresholds), "zero_volt")
        self.assertEqual(
            bm.categorize_cell_state(2.9, thresholds), "deep_discharge"
        )
        self.assertEqual(bm.categorize_cell_state(4.1, thresholds), "overvoltage")

    def test_invalid_thresholds_propagate(self):
        with self.assertRaises(ValueError):
            bm.categorize_cell_state(3.7, {"zero_volt_ceiling_v": 0.5})


class TestChargeStageSelection(unittest.TestCase):
    def test_zero_volt_gets_the_recovery_trickle(self):
        self.assertEqual(
            bm.charge_stage_for_state("zero_volt"), "recovery_trickle"
        )

    def test_deep_discharge_gets_the_precharge(self):
        self.assertEqual(bm.charge_stage_for_state("deep_discharge"), "precharge")

    def test_operating_gets_bulk_constant_current(self):
        self.assertEqual(
            bm.charge_stage_for_state("operating"), "bulk_constant_current"
        )

    def test_overvoltage_inhibits_charging(self):
        self.assertEqual(bm.charge_stage_for_state("overvoltage"), "charge_inhibit")

    def test_unrecognized_state_raises(self):
        with self.assertRaises(ValueError):
            bm.charge_stage_for_state("mostly_fine")

    def test_unhashable_state_raises_value_error(self):
        with self.assertRaises(ValueError):
            bm.charge_stage_for_state(["operating"])


class TestStageCurrentLimit(unittest.TestCase):
    def test_bulk_limit_is_the_c_rate_times_capacity(self):
        self.assertAlmostEqual(
            bm.stage_current_limit_a("bulk_constant_current", 50.0), 25.0, places=9
        )

    def test_recovery_trickle_is_a_small_fraction_of_capacity(self):
        self.assertAlmostEqual(
            bm.stage_current_limit_a("recovery_trickle", 50.0), 1.0, places=9
        )

    def test_precharge_sits_between_trickle_and_bulk(self):
        self.assertAlmostEqual(
            bm.stage_current_limit_a("precharge", 50.0), 2.5, places=9
        )

    def test_inhibit_allows_no_current(self):
        self.assertAlmostEqual(
            bm.stage_current_limit_a("charge_inhibit", 50.0), 0.0, places=9
        )

    def test_custom_c_rates_are_used(self):
        self.assertAlmostEqual(
            bm.stage_current_limit_a("precharge", 40.0, {"precharge": 0.1}),
            4.0,
            places=9,
        )

    def test_non_positive_capacity_raises(self):
        with self.assertRaises(ValueError):
            bm.stage_current_limit_a("precharge", 0.0)

    def test_stage_without_a_declared_rate_raises(self):
        with self.assertRaises(ValueError):
            bm.stage_current_limit_a("float_charge", 50.0)

    def test_negative_c_rate_raises(self):
        with self.assertRaises(ValueError):
            bm.stage_current_limit_a("precharge", 50.0, {"precharge": -0.1})


class TestRecoveryChargeTime(unittest.TestCase):
    def test_time_is_recovered_capacity_over_current(self):
        self.assertAlmostEqual(
            bm.recovery_charge_time_h(50.0, 0.05, 1.0), 2.5, places=9
        )

    def test_a_full_recovery_fraction_is_allowed(self):
        self.assertAlmostEqual(
            bm.recovery_charge_time_h(10.0, 1.0, 2.0), 5.0, places=9
        )

    def test_zero_recovery_fraction_raises(self):
        with self.assertRaises(ValueError):
            bm.recovery_charge_time_h(50.0, 0.0, 1.0)

    def test_recovery_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            bm.recovery_charge_time_h(50.0, 1.2, 1.0)

    def test_zero_charge_current_raises(self):
        with self.assertRaises(ValueError):
            bm.recovery_charge_time_h(50.0, 0.05, 0.0)

    def test_non_positive_capacity_raises(self):
        with self.assertRaises(ValueError):
            bm.recovery_charge_time_h(0.0, 0.05, 1.0)


class TestDepthOfDischarge(unittest.TestCase):
    def test_ratio_of_charge_removed_to_capacity(self):
        self.assertAlmostEqual(bm.depth_of_discharge(15.0, 50.0), 0.3, places=9)

    def test_untouched_battery_is_zero(self):
        self.assertAlmostEqual(bm.depth_of_discharge(0.0, 50.0), 0.0, places=9)

    def test_fully_removed_capacity_is_one(self):
        self.assertAlmostEqual(bm.depth_of_discharge(50.0, 50.0), 1.0, places=9)

    def test_negative_charge_removed_raises(self):
        with self.assertRaises(ValueError):
            bm.depth_of_discharge(-1.0, 50.0)

    def test_non_positive_capacity_raises(self):
        with self.assertRaises(ValueError):
            bm.depth_of_discharge(10.0, 0.0)

    def test_charge_removed_beyond_capacity_raises(self):
        with self.assertRaises(ValueError):
            bm.depth_of_discharge(50.1, 50.0)

    def test_summed_charge_removed_at_the_capacity_boundary_is_accepted(self):
        removed_ah = 0.0
        for _ in range(3):
            removed_ah += 0.1
        self.assertGreater(removed_ah, 0.3)  # overshoots in binary
        self.assertAlmostEqual(
            bm.depth_of_discharge(removed_ah, 0.3), 1.0, places=9
        )


class TestStageSelectionFindings(unittest.TestCase):
    def test_matching_stage_reports_nothing(self):
        self.assertEqual(
            bm.stage_selection_findings("bat", "operating", "bulk_constant_current"),
            [],
        )

    def test_mismatched_stage_is_reported(self):
        findings = bm.stage_selection_findings(
            "bat", "zero_volt", "bulk_constant_current"
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "charge_stage_does_not_match_cell_state"
        )
        self.assertEqual(findings[0]["expected_stage"], "recovery_trickle")

    def test_unrecognized_state_raises(self):
        with self.assertRaises(ValueError):
            bm.stage_selection_findings("bat", "sleepy", "precharge")


class TestChargeTemperatureFindings(unittest.TestCase):
    def test_inside_the_window_reports_nothing(self):
        self.assertEqual(
            bm.charge_temperature_findings("bat", 15.0, (0.0, 45.0)), []
        )

    def test_charging_a_cold_cell_is_reported(self):
        findings = bm.charge_temperature_findings("bat", -5.0, (0.0, 45.0))
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "charge_below_minimum_cell_temperature"
        )

    def test_charging_a_hot_cell_is_reported(self):
        findings = bm.charge_temperature_findings("bat", 50.0, (0.0, 45.0))
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "charge_above_maximum_cell_temperature"
        )

    def test_both_window_edges_are_inclusive(self):
        self.assertEqual(bm.charge_temperature_findings("bat", 0.0, (0.0, 45.0)), [])
        self.assertEqual(
            bm.charge_temperature_findings("bat", 45.0, (0.0, 45.0)), []
        )

    def test_summed_temperature_rise_at_the_upper_edge_is_accepted(self):
        temperature_c = 0.0
        for _ in range(3):
            temperature_c += 0.1
        self.assertGreater(temperature_c, 0.3)
        self.assertEqual(
            bm.charge_temperature_findings("bat", temperature_c, (-10.0, 0.3)), []
        )

    def test_inverted_window_raises(self):
        with self.assertRaises(ValueError):
            bm.charge_temperature_findings("bat", 15.0, (45.0, 0.0))

    def test_window_that_is_not_a_pair_raises(self):
        with self.assertRaises(ValueError):
            bm.charge_temperature_findings("bat", 15.0, 45.0)


class TestChargeCommandFindings(unittest.TestCase):
    def test_command_inside_every_limit_reports_nothing(self):
        battery = _clean_battery()
        self.assertEqual(
            bm.charge_command_findings("bat", battery["command"], 50.0), []
        )

    def test_current_above_the_stage_limit_is_reported(self):
        command = {
            "stage": "bulk_constant_current",
            "current_a": 26.0,
            "cell_voltage_v": 3.7,
        }
        findings = bm.charge_command_findings("bat", command, 50.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "charge_current_above_stage_limit")
        self.assertAlmostEqual(findings[0]["limit_a"], 25.0, places=9)

    def test_current_exactly_at_the_stage_limit_is_compliant(self):
        command = {
            "stage": "recovery_trickle",
            "current_a": 1.0,
            "cell_voltage_v": 0.2,
        }
        self.assertEqual(bm.charge_command_findings("bat", command, 50.0), [])

    def test_summed_current_at_the_stage_limit_is_compliant(self):
        current_a = 0.0
        for _ in range(3):
            current_a += 0.1
        self.assertGreater(current_a, 0.3)
        command = {
            "stage": "bulk_constant_current",
            "current_a": current_a,
            "cell_voltage_v": 3.7,
        }
        self.assertEqual(bm.charge_command_findings("bat", command, 0.6), [])

    def test_current_commanded_while_inhibited_is_reported(self):
        command = {
            "stage": "charge_inhibit",
            "current_a": 0.5,
            "cell_voltage_v": 4.3,
        }
        issues = {
            f["issue"] for f in bm.charge_command_findings("bat", command, 50.0)
        }
        self.assertIn("charge_not_inhibited_at_overvoltage", issues)
        self.assertIn("charge_current_above_stage_limit", issues)
        self.assertIn("cell_voltage_above_maximum_charge_voltage", issues)

    def test_cell_voltage_above_the_charge_limit_is_reported(self):
        command = {
            "stage": "bulk_constant_current",
            "current_a": 10.0,
            "cell_voltage_v": 4.35,
        }
        findings = bm.charge_command_findings("bat", command, 50.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "cell_voltage_above_maximum_charge_voltage"
        )

    def test_missing_command_key_raises(self):
        with self.assertRaises(ValueError):
            bm.charge_command_findings(
                "bat", {"stage": "precharge", "current_a": 1.0}, 50.0
            )

    def test_negative_commanded_current_raises(self):
        command = {
            "stage": "precharge",
            "current_a": -1.0,
            "cell_voltage_v": 2.0,
        }
        with self.assertRaises(ValueError):
            bm.charge_command_findings("bat", command, 50.0)

    def test_negative_commanded_cell_voltage_raises(self):
        command = {
            "stage": "precharge",
            "current_a": 1.0,
            "cell_voltage_v": -2.0,
        }
        with self.assertRaises(ValueError):
            bm.charge_command_findings("bat", command, 50.0)


class TestRecoveryFindings(unittest.TestCase):
    def test_operating_battery_needs_no_recovery(self):
        battery = _clean_battery()
        self.assertEqual(
            bm.recovery_findings("bat", "operating", 50.0, battery["charger"]), []
        )

    def test_supported_zero_volt_recovery_inside_budget_is_clean(self):
        battery = _clean_battery()
        self.assertEqual(
            bm.recovery_findings("bat", "zero_volt", 50.0, battery["charger"]), []
        )

    def test_charger_without_zero_volt_capability_is_reported(self):
        charger = _clean_battery()["charger"]
        charger["supports_zero_volt_recovery"] = False
        issues = {
            f["issue"]
            for f in bm.recovery_findings("bat", "zero_volt", 50.0, charger)
        }
        self.assertIn("charger_cannot_recover_zero_volt_battery", issues)

    def test_deep_discharge_does_not_need_zero_volt_capability(self):
        charger = _clean_battery()["charger"]
        charger["supports_zero_volt_recovery"] = False
        self.assertEqual(
            bm.recovery_findings("bat", "deep_discharge", 50.0, charger), []
        )

    def test_recovery_slower_than_the_budget_is_reported(self):
        charger = _clean_battery()["charger"]
        charger["maximum_recovery_time_h"] = 1.0
        findings = bm.recovery_findings("bat", "zero_volt", 50.0, charger)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "recovery_time_exceeds_budget")
        self.assertAlmostEqual(findings[0]["recovery_time_h"], 2.5, places=9)

    def test_recovery_exactly_at_the_budget_is_compliant(self):
        charger = _clean_battery()["charger"]
        charger["maximum_recovery_time_h"] = 2.5
        self.assertEqual(bm.recovery_findings("bat", "zero_volt", 50.0, charger), [])

    def test_missing_charger_key_raises(self):
        with self.assertRaises(ValueError):
            bm.recovery_findings(
                "bat", "zero_volt", 50.0, {"supports_zero_volt_recovery": True}
            )

    def test_non_positive_budget_raises(self):
        charger = _clean_battery()["charger"]
        charger["maximum_recovery_time_h"] = 0.0
        with self.assertRaises(ValueError):
            bm.recovery_findings("bat", "zero_volt", 50.0, charger)

    def test_invalid_recovery_fraction_raises(self):
        charger = _clean_battery()["charger"]
        charger["recovery_fraction"] = 0.0
        with self.assertRaises(ValueError):
            bm.recovery_findings("bat", "zero_volt", 50.0, charger)

    def test_unrecognized_state_raises(self):
        charger = _clean_battery()["charger"]
        with self.assertRaises(ValueError):
            bm.recovery_findings("bat", "a_bit_low", 50.0, charger)


class TestDischargeFindings(unittest.TestCase):
    def test_discharge_inside_the_limits_reports_nothing(self):
        battery = _clean_battery()
        self.assertEqual(
            bm.discharge_findings(
                "bat", battery["discharge"], battery["discharge_limits"]
            ),
            [],
        )

    def test_depth_of_discharge_above_the_limit_is_reported(self):
        battery = _clean_battery()
        battery["discharge"]["discharged_ah"] = 30.0
        findings = bm.discharge_findings(
            "bat", battery["discharge"], battery["discharge_limits"]
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "depth_of_discharge_above_limit")
        self.assertAlmostEqual(findings[0]["depth_of_discharge"], 0.6, places=9)

    def test_depth_of_discharge_exactly_at_the_limit_is_compliant(self):
        battery = _clean_battery()
        battery["discharge"]["discharged_ah"] = 20.0
        self.assertEqual(
            bm.discharge_findings(
                "bat", battery["discharge"], battery["discharge_limits"]
            ),
            [],
        )

    def test_summed_charge_removed_at_the_depth_limit_is_compliant(self):
        removed_ah = 0.0
        for _ in range(3):
            removed_ah += 0.1
        self.assertGreater(removed_ah, 0.3)
        discharge = {
            "discharged_ah": removed_ah,
            "capacity_ah": 1.0,
            "end_of_discharge_voltage_v": 3.0,
        }
        limits = {
            "maximum_depth_of_discharge": 0.3,
            "end_of_discharge_voltage_floor_v": 2.8,
        }
        self.assertEqual(bm.discharge_findings("bat", discharge, limits), [])

    def test_end_of_discharge_voltage_below_the_floor_is_reported(self):
        battery = _clean_battery()
        battery["discharge"]["end_of_discharge_voltage_v"] = 2.5
        findings = bm.discharge_findings(
            "bat", battery["discharge"], battery["discharge_limits"]
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "end_of_discharge_voltage_below_floor"
        )

    def test_summed_pack_voltage_at_the_floor_is_compliant(self):
        pack_voltage_v = 0.0
        for _ in range(8):
            pack_voltage_v += 2.9
        self.assertLess(pack_voltage_v, 23.2)  # undershoots in binary
        discharge = {
            "discharged_ah": 10.0,
            "capacity_ah": 50.0,
            "end_of_discharge_voltage_v": pack_voltage_v,
        }
        limits = {
            "maximum_depth_of_discharge": 0.4,
            "end_of_discharge_voltage_floor_v": 23.2,
        }
        self.assertEqual(bm.discharge_findings("bat", discharge, limits), [])

    def test_both_discharge_limits_can_be_breached_together(self):
        discharge = {
            "discharged_ah": 45.0,
            "capacity_ah": 50.0,
            "end_of_discharge_voltage_v": 2.0,
        }
        limits = {
            "maximum_depth_of_discharge": 0.4,
            "end_of_discharge_voltage_floor_v": 2.8,
        }
        self.assertEqual(len(bm.discharge_findings("bat", discharge, limits)), 2)

    def test_missing_discharge_key_raises(self):
        limits = {
            "maximum_depth_of_discharge": 0.4,
            "end_of_discharge_voltage_floor_v": 2.8,
        }
        with self.assertRaises(ValueError):
            bm.discharge_findings(
                "bat", {"discharged_ah": 10.0, "capacity_ah": 50.0}, limits
            )

    def test_missing_limit_key_raises(self):
        battery = _clean_battery()
        with self.assertRaises(ValueError):
            bm.discharge_findings(
                "bat", battery["discharge"], {"maximum_depth_of_discharge": 0.4}
            )

    def test_maximum_depth_outside_the_unit_range_raises(self):
        battery = _clean_battery()
        limits = dict(battery["discharge_limits"])
        limits["maximum_depth_of_discharge"] = 1.5
        with self.assertRaises(ValueError):
            bm.discharge_findings("bat", battery["discharge"], limits)

    def test_non_positive_voltage_floor_raises(self):
        battery = _clean_battery()
        limits = dict(battery["discharge_limits"])
        limits["end_of_discharge_voltage_floor_v"] = 0.0
        with self.assertRaises(ValueError):
            bm.discharge_findings("bat", battery["discharge"], limits)


class TestBatteryReview(unittest.TestCase):
    def test_clean_battery_is_compliant(self):
        review = bm.battery_management_review(_clean_battery())
        for key in ("stage", "charge", "thermal", "recovery", "discharge"):
            self.assertEqual(review[key], [])
        self.assertTrue(bm.is_charge_management_compliant(review))

    def test_zero_volt_battery_with_a_capable_charger_is_compliant(self):
        review = bm.battery_management_review(_zero_volt_battery())
        self.assertTrue(bm.is_charge_management_compliant(review))

    def test_zero_volt_battery_without_recovery_capability_is_flagged(self):
        battery = _zero_volt_battery()
        battery["charger"]["supports_zero_volt_recovery"] = False
        review = bm.battery_management_review(battery)
        self.assertEqual(len(review["recovery"]), 1)
        self.assertFalse(bm.is_charge_management_compliant(review))

    def test_bulk_charging_an_overvoltage_cell_is_flagged(self):
        battery = _clean_battery()
        battery["cell_voltage_v"] = 4.3
        battery["command"]["cell_voltage_v"] = 4.3
        review = bm.battery_management_review(battery)
        self.assertEqual(len(review["stage"]), 1)
        self.assertEqual(len(review["charge"]), 1)
        self.assertFalse(bm.is_charge_management_compliant(review))

    def test_cold_charge_is_flagged_through_the_thermal_list(self):
        battery = _clean_battery()
        battery["cell_temperature_c"] = -10.0
        review = bm.battery_management_review(battery)
        self.assertEqual(len(review["thermal"]), 1)
        self.assertFalse(bm.is_charge_management_compliant(review))

    def test_review_does_not_mutate_its_input(self):
        battery = _clean_battery()
        before = repr(battery)
        bm.battery_management_review(battery)
        self.assertEqual(repr(battery), before)

    def test_review_is_deterministic(self):
        battery = _clean_battery()
        self.assertEqual(
            bm.battery_management_review(battery),
            bm.battery_management_review(battery),
        )

    def test_invalid_capacity_propagates_through_the_review(self):
        battery = _clean_battery()
        battery["capacity_ah"] = 0.0
        with self.assertRaises(ValueError):
            bm.battery_management_review(battery)


if __name__ == "__main__":
    unittest.main()
