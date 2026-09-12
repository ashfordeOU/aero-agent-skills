#!/usr/bin/env python3
"""Gate 3 contract test for e20-reliable-insulation-applicability-scope.

stdlib unittest, offline, deterministic. Run:
python3 test_e20_reliable_insulation_applicability_scope.py
"""

import copy
import unittest

from e20_reliable_insulation_applicability_scope_logic import (
    HAZARDOUS_FAULT_POWER_W,
    HAZARDOUS_STORED_ENERGY_J,
    HAZARDOUS_VOLTAGE_V,
    INDETERMINATE,
    IN_SCOPE,
    OUT_OF_SCOPE,
    categorize_net,
    coverage_gaps,
    hazardous_energy_drivers,
    is_scope_complete,
    net_applicability,
    scope_review,
    severity_rank,
)


def _benign_signal_net(**overrides):
    net = {
        "net_id": "TM-SENSE-11",
        "net_type": "telemetry_sense_line",
        "voltage_v": 5.0,
        "available_fault_current_a": 0.05,
        "stored_energy_j": 0.0,
        "failure_severity": "marginal",
        "single_point": False,
        "reliable_insulation_declared": False,
    }
    net.update(overrides)
    return net


class TestNetCategorization(unittest.TestCase):
    def test_every_family_is_reachable(self):
        self.assertEqual(categorize_net("primary_power_bus"), "power_distribution")
        self.assertEqual(categorize_net("pyrotechnic_firing_line"), "ordnance")
        self.assertEqual(categorize_net("electric_propulsion_line"), "high_voltage")
        self.assertEqual(categorize_net("command_signal_net"), "signal")
        self.assertEqual(categorize_net("structure_bond"), "bonding")

    def test_unrecognized_net_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_net("waveguide_run")

    def test_unhashable_net_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_net(["primary_power_bus"])


class TestHazardousEnergyDrivers(unittest.TestCase):
    def test_benign_net_has_no_driver(self):
        self.assertEqual(hazardous_energy_drivers(5.0, 0.05, 0.0), [])

    def test_voltage_threshold_is_inclusive(self):
        self.assertIn(
            "voltage_at_or_above_threshold",
            hazardous_energy_drivers(HAZARDOUS_VOLTAGE_V, 0.0, 0.0),
        )
        self.assertEqual(
            hazardous_energy_drivers(HAZARDOUS_VOLTAGE_V - 0.1, 0.0, 0.0), []
        )

    def test_low_voltage_high_current_still_trips_fault_power(self):
        drivers = hazardous_energy_drivers(
            28.0, HAZARDOUS_FAULT_POWER_W / 28.0, 0.0
        )
        self.assertEqual(drivers, ["fault_power_at_or_above_threshold"])

    def test_stored_energy_threshold_is_inclusive(self):
        self.assertIn(
            "stored_energy_at_or_above_threshold",
            hazardous_energy_drivers(5.0, 0.0, HAZARDOUS_STORED_ENERGY_J),
        )

    def test_drivers_are_returned_sorted_and_can_coexist(self):
        drivers = hazardous_energy_drivers(100.0, 10.0, 50.0)
        self.assertEqual(len(drivers), 3)
        self.assertEqual(drivers, sorted(drivers))

    def test_negative_input_raises(self):
        with self.assertRaises(ValueError):
            hazardous_energy_drivers(-1.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            hazardous_energy_drivers(5.0, -0.1, 0.0)
        with self.assertRaises(ValueError):
            hazardous_energy_drivers(5.0, 0.1, -2.0)


class TestSeverityRank(unittest.TestCase):
    def test_ranks_are_ordered(self):
        self.assertTrue(
            severity_rank("negligible")
            < severity_rank("marginal")
            < severity_rank("critical")
            < severity_rank("catastrophic")
        )

    def test_unrecognized_severity_raises(self):
        with self.assertRaises(ValueError):
            severity_rank("annoying")


class TestNetApplicability(unittest.TestCase):
    def test_ordnance_family_is_in_scope_on_identity(self):
        result = net_applicability(
            {"net_id": "PYRO-01", "net_type": "pyrotechnic_firing_line"}
        )
        self.assertEqual(result["decision"], IN_SCOPE)
        self.assertEqual(result["drivers"], ["family_always_in_scope"])

    def test_battery_main_line_is_in_scope_without_numbers(self):
        result = net_applicability(
            {"net_id": "BAT-MAIN", "net_type": "battery_main_line"}
        )
        self.assertEqual(result["decision"], IN_SCOPE)
        self.assertEqual(result["drivers"], ["net_type_always_in_scope"])

    def test_benign_signal_net_is_out_of_scope(self):
        result = net_applicability(_benign_signal_net())
        self.assertEqual(result["decision"], OUT_OF_SCOPE)
        self.assertEqual(result["drivers"], [])

    def test_critical_single_point_signal_net_is_in_scope(self):
        result = net_applicability(
            _benign_signal_net(
                net_type="command_signal_net",
                failure_severity="catastrophic",
                single_point=True,
            )
        )
        self.assertEqual(result["decision"], IN_SCOPE)
        self.assertIn("critical_single_point_path", result["drivers"])

    def test_critical_but_redundant_net_stays_out_of_scope(self):
        result = net_applicability(
            _benign_signal_net(failure_severity="catastrophic", single_point=False)
        )
        self.assertEqual(result["decision"], OUT_OF_SCOPE)

    def test_energy_route_is_independent_of_criticality(self):
        result = net_applicability(
            _benign_signal_net(
                net_type="secondary_power_bus", voltage_v=120.0
            )
        )
        self.assertEqual(result["decision"], IN_SCOPE)
        self.assertIn("voltage_at_or_above_threshold", result["drivers"])

    def test_missing_electrical_data_is_indeterminate_not_out_of_scope(self):
        result = net_applicability(_benign_signal_net(stored_energy_j=None))
        self.assertEqual(result["decision"], INDETERMINATE)
        self.assertIn("electrical_data_missing", result["drivers"])

    def test_missing_criticality_data_is_indeterminate(self):
        result = net_applicability(_benign_signal_net(single_point=None))
        self.assertEqual(result["decision"], INDETERMINATE)
        self.assertIn("criticality_data_missing", result["drivers"])

    def test_missing_net_id_raises(self):
        with self.assertRaises(ValueError):
            net_applicability({"net_type": "command_signal_net"})

    def test_negative_electrical_figure_raises(self):
        with self.assertRaises(ValueError):
            net_applicability(_benign_signal_net(voltage_v=-5.0))

    def test_unrecognized_severity_raises(self):
        with self.assertRaises(ValueError):
            net_applicability(_benign_signal_net(failure_severity="spicy"))


class TestScopeReview(unittest.TestCase):
    def _net_set(self):
        return [
            {
                "net_id": "PYRO-01",
                "net_type": "pyrotechnic_firing_line",
                "reliable_insulation_declared": True,
            },
            _benign_signal_net(),
            _benign_signal_net(
                net_id="CMD-04",
                net_type="command_signal_net",
                failure_severity="critical",
                single_point=True,
                reliable_insulation_declared=True,
            ),
        ]

    def test_review_partitions_every_net(self):
        review = scope_review(self._net_set())
        self.assertEqual(len(review[IN_SCOPE]), 2)
        self.assertEqual(len(review[OUT_OF_SCOPE]), 1)
        self.assertEqual(review[INDETERMINATE], [])
        self.assertEqual(review["gaps"], [])
        self.assertTrue(is_scope_complete(review))

    def test_in_scope_net_without_declaration_is_a_gap(self):
        nets = self._net_set()
        nets[0]["reliable_insulation_declared"] = False
        review = scope_review(nets)
        self.assertEqual(len(review["gaps"]), 1)
        self.assertEqual(review["gaps"][0]["net_id"], "PYRO-01")
        self.assertFalse(is_scope_complete(review))

    def test_indeterminate_net_blocks_completion(self):
        nets = self._net_set()
        nets[1]["failure_severity"] = None
        review = scope_review(nets)
        self.assertEqual(len(review[INDETERMINATE]), 1)
        self.assertFalse(is_scope_complete(review))

    def test_out_of_scope_net_is_never_a_gap(self):
        review = scope_review([_benign_signal_net()])
        self.assertEqual(review["gaps"], [])
        self.assertTrue(is_scope_complete(review))

    def test_duplicate_net_id_raises(self):
        nets = self._net_set()
        nets[2]["net_id"] = nets[1]["net_id"]
        with self.assertRaises(ValueError):
            scope_review(nets)

    def test_empty_net_list_raises(self):
        with self.assertRaises(ValueError):
            scope_review([])

    def test_mismatched_assessment_length_raises(self):
        nets = self._net_set()
        with self.assertRaises(ValueError):
            coverage_gaps(nets, [net_applicability(nets[0])])

    def test_review_does_not_mutate_the_nets(self):
        nets = self._net_set()
        snapshot = copy.deepcopy(nets)
        scope_review(nets)
        self.assertEqual(nets, snapshot)


if __name__ == "__main__":
    unittest.main()
