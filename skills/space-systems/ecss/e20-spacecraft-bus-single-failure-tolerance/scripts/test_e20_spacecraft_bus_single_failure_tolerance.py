#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.7.2 spacecraft bus
single-failure tolerance.

Exercises scripts/e20_spacecraft_bus_single_failure_tolerance_logic.py
(stdlib unittest, offline). Contract: a failure mode maps to exactly
one chain effect and an unrecognized mode raises; a redundancy scheme
maps to exactly one recovery category and an unrecognized scheme
raises; the minimum-mission demand sums only the loads flagged
essential; the surviving capability drops the failed branch when it is
single string, keeps it when a powered or standby element is behind it,
and keeps only the degraded fraction when the output is reduced; the
capability during a cold-standby switchover excludes the branch for the
outage; the energy that bridges the outage is deficit times outage; a
capability that equals the demand to within floating-point
representation error is compliant; a non-redundant essential function
is reported whatever the margin; and the aggregated review is tolerant
only when every list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_spacecraft_bus_single_failure_tolerance_logic as sft  # noqa: E402


def _clean_units():
    """A power chain that tolerates every single fault in it."""
    return [
        {
            "unit_id": "sa_section_a",
            "capability_w": 150.0,
            "failure_mode": "open_circuit",
            "redundancy_scheme": "single_string",
        },
        {
            "unit_id": "sa_section_b",
            "capability_w": 150.0,
            "failure_mode": "open_circuit",
            "redundancy_scheme": "single_string",
        },
        {
            "unit_id": "regulator_branch_a",
            "capability_w": 200.0,
            "failure_mode": "short_circuit",
            "redundancy_scheme": "hot_standby",
        },
        {
            "unit_id": "battery_branch",
            "capability_w": 120.0,
            "failure_mode": "open_circuit",
            "redundancy_scheme": "cold_standby",
            "reconfiguration_time_s": 10.0,
            "function_essential": True,
        },
    ]


def _clean_loads():
    return [
        {
            "load_id": "avionics_core",
            "power_w": 200.0,
            "essential_for_minimum_mission": True,
        },
        {
            "load_id": "survival_heaters",
            "power_w": 60.0,
            "essential_for_minimum_mission": True,
        },
        {
            "load_id": "payload_imager",
            "power_w": 300.0,
            "essential_for_minimum_mission": False,
        },
    ]


def _clean_chain():
    return {
        "units": _clean_units(),
        "loads": _clean_loads(),
        "battery_usable_energy_wh": 40.0,
    }


class TestFailureModeCategorization(unittest.TestCase):
    def test_short_circuit_is_loss_of_output(self):
        self.assertEqual(
            sft.categorize_failure_mode("short_circuit"), "loss_of_output"
        )

    def test_open_circuit_is_loss_of_output(self):
        self.assertEqual(
            sft.categorize_failure_mode("open_circuit"), "loss_of_output"
        )

    def test_switch_stuck_open_is_loss_of_output(self):
        self.assertEqual(
            sft.categorize_failure_mode("switch_stuck_open"), "loss_of_output"
        )

    def test_degraded_output_keeps_its_own_effect(self):
        self.assertEqual(
            sft.categorize_failure_mode("degraded_output"), "degraded_output"
        )

    def test_switch_stuck_closed_is_loss_of_control_path(self):
        self.assertEqual(
            sft.categorize_failure_mode("switch_stuck_closed"),
            "loss_of_control_path",
        )

    def test_every_recognized_mode_maps_to_a_known_effect(self):
        effects = {"loss_of_output", "degraded_output", "loss_of_control_path"}
        for mode in sft.FAILURE_MODE_EFFECTS:
            self.assertIn(sft.categorize_failure_mode(mode), effects)

    def test_unrecognized_failure_mode_raises(self):
        with self.assertRaises(ValueError):
            sft.categorize_failure_mode("melted_a_bit")

    def test_unhashable_failure_mode_raises_value_error(self):
        with self.assertRaises(ValueError):
            sft.categorize_failure_mode(["open_circuit"])


class TestRedundancyCategorization(unittest.TestCase):
    def test_single_string_has_no_recovery(self):
        self.assertEqual(sft.categorize_redundancy("single_string"), "none")

    def test_cold_standby_is_standby(self):
        self.assertEqual(sft.categorize_redundancy("cold_standby"), "standby")

    def test_hot_standby_is_active(self):
        self.assertEqual(sft.categorize_redundancy("hot_standby"), "active")

    def test_cross_strapped_keeps_its_own_category(self):
        self.assertEqual(
            sft.categorize_redundancy("cross_strapped"), "cross_strapped"
        )

    def test_unrecognized_redundancy_scheme_raises(self):
        with self.assertRaises(ValueError):
            sft.categorize_redundancy("triple_modular")


class TestMinimumMissionDemand(unittest.TestCase):
    def test_sums_only_the_essential_loads(self):
        self.assertAlmostEqual(
            sft.minimum_mission_demand_w(_clean_loads()), 260.0, places=9
        )

    def test_empty_load_list_is_zero_demand(self):
        self.assertAlmostEqual(sft.minimum_mission_demand_w([]), 0.0, places=9)

    def test_unflagged_load_is_not_essential(self):
        loads = [{"load_id": "heater", "power_w": 25.0}]
        self.assertAlmostEqual(sft.minimum_mission_demand_w(loads), 0.0, places=9)

    def test_missing_power_key_raises(self):
        with self.assertRaises(ValueError):
            sft.minimum_mission_demand_w([{"load_id": "heater"}])

    def test_negative_load_power_raises(self):
        with self.assertRaises(ValueError):
            sft.minimum_mission_demand_w(
                [{"load_id": "heater", "power_w": -1.0}]
            )


class TestChainValidation(unittest.TestCase):
    def test_empty_chain_raises(self):
        with self.assertRaises(ValueError):
            sft.post_fault_capability_w([], "sa_section_a")

    def test_duplicate_unit_id_raises(self):
        units = _clean_units()
        units[1]["unit_id"] = "sa_section_a"
        with self.assertRaises(ValueError):
            sft.post_fault_capability_w(units, "sa_section_a")

    def test_missing_required_unit_key_raises(self):
        units = _clean_units()
        del units[0]["capability_w"]
        with self.assertRaises(ValueError):
            sft.post_fault_capability_w(units, "sa_section_b")

    def test_negative_capability_raises(self):
        units = _clean_units()
        units[0]["capability_w"] = -5.0
        with self.assertRaises(ValueError):
            sft.post_fault_capability_w(units, "sa_section_a")

    def test_degraded_fraction_above_one_raises(self):
        units = _clean_units()
        units[0]["degraded_output_fraction"] = 1.5
        with self.assertRaises(ValueError):
            sft.post_fault_capability_w(units, "sa_section_a")

    def test_negative_reconfiguration_time_raises(self):
        units = _clean_units()
        units[3]["reconfiguration_time_s"] = -2.0
        with self.assertRaises(ValueError):
            sft.post_fault_capability_w(units, "battery_branch")

    def test_unknown_failed_unit_id_raises(self):
        with self.assertRaises(ValueError):
            sft.post_fault_capability_w(_clean_units(), "not_a_unit")


class TestPostFaultCapability(unittest.TestCase):
    def test_single_string_loss_removes_its_branch(self):
        self.assertAlmostEqual(
            sft.post_fault_capability_w(_clean_units(), "sa_section_a"),
            470.0,
            places=9,
        )

    def test_hot_standby_keeps_full_capability(self):
        self.assertAlmostEqual(
            sft.post_fault_capability_w(_clean_units(), "regulator_branch_a"),
            620.0,
            places=9,
        )

    def test_cold_standby_restores_capability_after_switchover(self):
        self.assertAlmostEqual(
            sft.post_fault_capability_w(_clean_units(), "battery_branch"),
            620.0,
            places=9,
        )

    def test_degraded_single_string_keeps_its_fraction(self):
        units = _clean_units()
        units[0]["failure_mode"] = "degraded_output"
        units[0]["degraded_output_fraction"] = 0.4
        self.assertAlmostEqual(
            sft.post_fault_capability_w(units, "sa_section_a"), 530.0, places=9
        )

    def test_control_path_loss_removes_the_branch(self):
        units = _clean_units()
        units[0]["failure_mode"] = "switch_stuck_closed"
        self.assertAlmostEqual(
            sft.post_fault_capability_w(units, "sa_section_a"), 470.0, places=9
        )

    def test_cross_strapped_branch_survives_its_own_fault(self):
        units = _clean_units()
        units[0]["redundancy_scheme"] = "cross_strapped"
        self.assertAlmostEqual(
            sft.post_fault_capability_w(units, "sa_section_a"), 620.0, places=9
        )


class TestTransientCapability(unittest.TestCase):
    def test_cold_standby_branch_is_absent_during_the_outage(self):
        self.assertAlmostEqual(
            sft.transient_capability_w(_clean_units(), "battery_branch"),
            500.0,
            places=9,
        )

    def test_hot_standby_branch_is_present_during_the_outage(self):
        self.assertAlmostEqual(
            sft.transient_capability_w(_clean_units(), "regulator_branch_a"),
            620.0,
            places=9,
        )

    def test_single_string_transient_equals_its_steady_state(self):
        units = _clean_units()
        self.assertAlmostEqual(
            sft.transient_capability_w(units, "sa_section_a"),
            sft.post_fault_capability_w(units, "sa_section_a"),
            places=9,
        )

    def test_unknown_unit_id_raises(self):
        with self.assertRaises(ValueError):
            sft.transient_capability_w(_clean_units(), "ghost_branch")


class TestReconfigurationTiming(unittest.TestCase):
    def test_standby_unit_reports_its_switchover_time(self):
        self.assertAlmostEqual(
            sft.reconfiguration_outage_s(_clean_units()[3]), 10.0, places=9
        )

    def test_continuously_redundant_unit_has_no_outage(self):
        self.assertAlmostEqual(
            sft.reconfiguration_outage_s(_clean_units()[2]), 0.0, places=9
        )

    def test_single_string_unit_reports_no_switchover(self):
        self.assertAlmostEqual(
            sft.reconfiguration_outage_s(_clean_units()[0]), 0.0, places=9
        )

    def test_energy_is_deficit_times_outage_in_hours(self):
        self.assertAlmostEqual(
            sft.reconfiguration_energy_wh(180.0, 60.0), 3.0, places=9
        )

    def test_zero_deficit_needs_no_energy(self):
        self.assertAlmostEqual(
            sft.reconfiguration_energy_wh(0.0, 120.0), 0.0, places=9
        )

    def test_negative_deficit_raises(self):
        with self.assertRaises(ValueError):
            sft.reconfiguration_energy_wh(-1.0, 60.0)

    def test_negative_outage_raises(self):
        with self.assertRaises(ValueError):
            sft.reconfiguration_energy_wh(10.0, -1.0)


class TestCapabilityFindings(unittest.TestCase):
    def test_tolerant_chain_reports_nothing(self):
        self.assertEqual(sft.capability_findings(_clean_units(), 260.0), [])

    def test_starving_demand_flags_each_single_string_branch(self):
        findings = sft.capability_findings(_clean_units(), 600.0)
        flagged = {f["unit"] for f in findings}
        self.assertEqual(flagged, {"sa_section_a", "sa_section_b"})
        self.assertEqual(
            findings[0]["issue"], "single_fault_below_minimum_mission_demand"
        )

    def test_capability_exactly_equal_to_demand_is_compliant(self):
        self.assertEqual(sft.capability_findings(_clean_units(), 470.0), [])

    def test_representation_error_at_the_boundary_is_absorbed(self):
        units = [
            {
                "unit_id": "branch_a",
                "capability_w": 0.3,
                "failure_mode": "open_circuit",
                "redundancy_scheme": "single_string",
            },
            {
                "unit_id": "branch_b",
                "capability_w": 0.3,
                "failure_mode": "open_circuit",
                "redundancy_scheme": "hot_standby",
            },
        ]
        demand_w = sft.minimum_mission_demand_w(
            [
                {
                    "load_id": "l%d" % i,
                    "power_w": 0.1,
                    "essential_for_minimum_mission": True,
                }
                for i in range(3)
            ]
        )
        self.assertGreater(demand_w, 0.3)  # 0.1+0.1+0.1 overshoots in binary
        self.assertEqual(sft.capability_findings(units, demand_w), [])

    def test_a_real_shortfall_is_still_flagged(self):
        findings = sft.capability_findings(_clean_units(), 470.001)
        self.assertEqual(len(findings), 2)

    def test_negative_demand_raises(self):
        with self.assertRaises(ValueError):
            sft.capability_findings(_clean_units(), -1.0)


class TestSinglePointFailureFindings(unittest.TestCase):
    def test_redundant_essential_function_is_not_a_single_point(self):
        self.assertEqual(sft.single_point_failure_findings(_clean_units()), [])

    def test_non_redundant_essential_function_is_reported(self):
        units = _clean_units()
        units[3]["redundancy_scheme"] = "single_string"
        findings = sft.single_point_failure_findings(units)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["unit"], "battery_branch")
        self.assertEqual(
            findings[0]["issue"], "single_point_failure_in_essential_function"
        )

    def test_non_essential_single_string_branch_is_not_reported(self):
        self.assertEqual(
            [
                f["unit"]
                for f in sft.single_point_failure_findings(_clean_units())
            ],
            [],
        )

    def test_invalid_chain_raises(self):
        with self.assertRaises(ValueError):
            sft.single_point_failure_findings([])


class TestReconfigurationFindings(unittest.TestCase):
    def test_covered_switchover_reports_nothing(self):
        self.assertEqual(
            sft.reconfiguration_findings(_clean_units(), 260.0, 40.0), []
        )

    def test_deficit_beyond_stored_energy_is_flagged(self):
        units = _clean_units()
        units[3]["reconfiguration_time_s"] = 1800.0
        findings = sft.reconfiguration_findings(units, 560.0, 1.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "reconfiguration_outage_not_energy_covered"
        )
        self.assertAlmostEqual(findings[0]["deficit_w"], 60.0, places=9)
        self.assertAlmostEqual(findings[0]["required_wh"], 30.0, places=9)

    def test_sufficient_stored_energy_clears_the_same_outage(self):
        units = _clean_units()
        units[3]["reconfiguration_time_s"] = 1800.0
        self.assertEqual(sft.reconfiguration_findings(units, 560.0, 30.0), [])

    def test_branch_with_no_outage_is_skipped(self):
        units = _clean_units()
        units[3]["reconfiguration_time_s"] = 0.0
        self.assertEqual(
            sft.reconfiguration_findings(units, 10000.0, 0.0), []
        )

    def test_negative_demand_raises(self):
        with self.assertRaises(ValueError):
            sft.reconfiguration_findings(_clean_units(), -1.0, 40.0)

    def test_negative_usable_energy_raises(self):
        with self.assertRaises(ValueError):
            sft.reconfiguration_findings(_clean_units(), 260.0, -1.0)


class TestChainReview(unittest.TestCase):
    def test_clean_chain_is_tolerant(self):
        review = sft.single_fault_tolerance_review(_clean_chain())
        self.assertEqual(review["capability"], [])
        self.assertEqual(review["single_point"], [])
        self.assertEqual(review["reconfiguration"], [])
        self.assertTrue(sft.is_single_fault_tolerant(review))

    def test_heavy_essential_load_makes_the_chain_intolerant(self):
        chain = _clean_chain()
        chain["loads"][2]["essential_for_minimum_mission"] = True
        review = sft.single_fault_tolerance_review(chain)
        self.assertTrue(len(review["capability"]) > 0)
        self.assertFalse(sft.is_single_fault_tolerant(review))

    def test_removing_battery_redundancy_raises_a_single_point(self):
        chain = _clean_chain()
        chain["units"][3]["redundancy_scheme"] = "single_string"
        review = sft.single_fault_tolerance_review(chain)
        self.assertEqual(len(review["single_point"]), 1)
        self.assertFalse(sft.is_single_fault_tolerant(review))

    def test_review_does_not_mutate_its_input(self):
        chain = _clean_chain()
        before = repr(chain)
        sft.single_fault_tolerance_review(chain)
        self.assertEqual(repr(chain), before)

    def test_review_is_deterministic(self):
        chain = _clean_chain()
        self.assertEqual(
            sft.single_fault_tolerance_review(chain),
            sft.single_fault_tolerance_review(chain),
        )

    def test_invalid_unit_propagates_through_the_review(self):
        chain = _clean_chain()
        chain["units"][0]["failure_mode"] = "gremlins"
        with self.assertRaises(ValueError):
            sft.single_fault_tolerance_review(chain)


if __name__ == "__main__":
    unittest.main()
