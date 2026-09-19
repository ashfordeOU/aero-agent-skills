#!/usr/bin/env python3
"""Contract test for the assembly Instance requirements of 4.2.2.3 (offline)."""

import copy
import unittest

from e4008_assembly_instance_logic import (
    NORMATIVE_ITEMS,
    child_path,
    declared_exports,
    direct_child_names,
    evaluate_assembly_instance,
    flatten_containment,
    is_legal_identifier,
    parse_endpoint,
    resolve_link,
    validate_identifier,
)

ASSEMBLY = {
    "name": "tcs",
    "definition": "ThermalControl",
    "parent_path": "/sat",
    "children": [
        {"name": "thermostat_a", "definition": "Thermostat"},
        {"name": "heater_a", "definition": "Heater"},
        {"name": "sensor_a", "definition": "Sensor"},
    ],
    "exports": ["loop_setpoint", "loop_status"],
    "links": [
        {"name": "cmd", "source": "thermostat_a.command", "target": "heater_a.drive"},
        {"name": "fb", "source": "sensor_a.reading", "target": "thermostat_a.measured"},
        {"name": "sp", "source": "self.loop_setpoint", "target": "thermostat_a.setpoint"},
        {"name": "st", "source": "thermostat_a.status", "target": "self.loop_status"},
    ],
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


def _item(result, identifier):
    for entry in result["items"]:
        if entry["item"] == identifier:
            return entry
    raise AssertionError("item %s not graded" % identifier)


class IdentifierTests(unittest.TestCase):
    def test_a_plain_child_name_is_legal(self):
        self.assertTrue(is_legal_identifier("heater_a"))

    def test_a_name_with_a_dot_is_not_legal(self):
        self.assertFalse(is_legal_identifier("heater.a"))

    def test_validate_identifier_raises_on_a_bad_name(self):
        with self.assertRaises(ValueError):
            validate_identifier("1heater", "child name")

    def test_child_path_is_built_under_the_assembly(self):
        self.assertEqual(child_path("/sat/tcs", "heater_a"), "/sat/tcs/heater_a")

    def test_a_relative_parent_path_rejected(self):
        with self.assertRaises(ValueError):
            child_path("sat/tcs", "heater_a")


class EndpointTests(unittest.TestCase):
    def test_an_endpoint_splits_into_owner_and_port(self):
        self.assertEqual(parse_endpoint("heater_a.drive"), ("heater_a", "drive"))

    def test_a_self_endpoint_keeps_the_self_owner(self):
        self.assertEqual(parse_endpoint("self.loop_setpoint"), ("self", "loop_setpoint"))

    def test_an_endpoint_without_a_port_rejected(self):
        with self.assertRaises(ValueError):
            parse_endpoint("heater_a")

    def test_a_two_level_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            parse_endpoint("tcs.heater_a.drive")

    def test_a_non_string_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            parse_endpoint(None)


class ContainmentTests(unittest.TestCase):
    def test_the_containment_walk_finds_every_node(self):
        nodes = flatten_containment(ASSEMBLY)
        self.assertEqual(len(nodes), 4)
        self.assertIn("/sat/tcs/heater_a", nodes)

    def test_a_nested_assembly_is_walked_through(self):
        nested = _case(ASSEMBLY)
        nested["children"].append(
            {
                "name": "pump_bay",
                "definition": "PumpBay",
                "children": [{"name": "pump_a", "definition": "Pump"}],
            }
        )
        nodes = flatten_containment(nested)
        self.assertIn("/sat/tcs/pump_bay/pump_a", nodes)

    def test_a_duplicate_child_name_rejected(self):
        broken = _case(ASSEMBLY)
        broken["children"].append({"name": "heater_a", "definition": "Heater"})
        with self.assertRaises(ValueError):
            flatten_containment(broken)

    def test_a_containment_cycle_rejected(self):
        broken = _case(ASSEMBLY)
        broken["children"].append(
            {
                "name": "inner",
                "definition": "ThermalControl",
                "children": [{"name": "deeper", "definition": "Heater"}],
            }
        )
        with self.assertRaises(ValueError):
            flatten_containment(broken)

    def test_a_child_that_is_not_a_mapping_rejected(self):
        broken = _case(ASSEMBLY, children=["heater_a"])
        with self.assertRaises(ValueError):
            flatten_containment(broken)

    def test_direct_child_names_are_listed_in_order(self):
        self.assertEqual(
            direct_child_names(ASSEMBLY), ["thermostat_a", "heater_a", "sensor_a"]
        )


class ExportTests(unittest.TestCase):
    def test_declared_exports_are_returned(self):
        self.assertEqual(declared_exports(ASSEMBLY), ["loop_setpoint", "loop_status"])

    def test_an_assembly_with_no_exports_returns_an_empty_list(self):
        self.assertEqual(declared_exports(_case(ASSEMBLY, exports=[])), [])

    def test_a_repeated_export_rejected(self):
        with self.assertRaises(ValueError):
            declared_exports(_case(ASSEMBLY, exports=["loop_status", "loop_status"]))

    def test_an_illegal_export_name_rejected(self):
        with self.assertRaises(ValueError):
            declared_exports(_case(ASSEMBLY, exports=["loop status"]))


class LinkResolutionTests(unittest.TestCase):
    def test_a_link_between_two_children_resolves(self):
        result = resolve_link(
            ASSEMBLY["links"][0], direct_child_names(ASSEMBLY), declared_exports(ASSEMBLY)
        )
        self.assertTrue(result["resolved"])
        self.assertEqual(result["endpoints"]["target"], ("child", "heater_a"))

    def test_a_link_through_an_export_resolves(self):
        result = resolve_link(
            ASSEMBLY["links"][2], direct_child_names(ASSEMBLY), declared_exports(ASSEMBLY)
        )
        self.assertEqual(result["endpoints"]["source"], ("export", "loop_setpoint"))

    def test_a_link_to_an_absent_child_does_not_resolve(self):
        link = {"name": "bad", "source": "thermostat_a.command", "target": "valve_a.drive"}
        result = resolve_link(link, direct_child_names(ASSEMBLY), declared_exports(ASSEMBLY))
        self.assertFalse(result["resolved"])
        self.assertTrue(any("does not contain" in note for note in result["findings"]))

    def test_a_self_endpoint_without_an_export_does_not_resolve(self):
        link = {"name": "bad", "source": "self.loop_power", "target": "heater_a.drive"}
        result = resolve_link(link, direct_child_names(ASSEMBLY), declared_exports(ASSEMBLY))
        self.assertFalse(result["resolved"])
        self.assertTrue(any("exported interface" in note for note in result["findings"]))

    def test_both_ends_can_fail_at_once(self):
        link = {"name": "bad", "source": "valve_a.out", "target": "self.loop_power"}
        result = resolve_link(link, direct_child_names(ASSEMBLY), declared_exports(ASSEMBLY))
        self.assertEqual(len(result["findings"]), 2)

    def test_a_link_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            resolve_link({"source": "a.b", "target": "c.d"}, ["a", "c"], [])


class AssemblyEvaluationTests(unittest.TestCase):
    def test_a_well_formed_assembly_satisfies_both_items(self):
        result = evaluate_assembly_instance(ASSEMBLY)
        self.assertEqual(result["satisfied"], 2)
        self.assertEqual(result["required"], len(NORMATIVE_ITEMS))
        self.assertEqual(result["verdict"], "assembly-instance-compliant")

    def test_both_normative_items_are_graded_exactly_once(self):
        result = evaluate_assembly_instance(ASSEMBLY)
        graded = [entry["item"] for entry in result["items"]]
        self.assertEqual(sorted(graded), sorted(NORMATIVE_ITEMS))

    def test_the_contained_paths_are_reported(self):
        result = evaluate_assembly_instance(ASSEMBLY)
        self.assertIn("/sat/tcs/sensor_a", result["contained_paths"])

    def test_an_assembly_with_no_children_fails_the_containment_item(self):
        result = evaluate_assembly_instance(_case(ASSEMBLY, children=[], links=[]))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[0])["satisfied"])

    def test_a_duplicate_child_name_fails_the_containment_item(self):
        broken = _case(ASSEMBLY)
        broken["children"].append({"name": "sensor_a", "definition": "Sensor"})
        result = evaluate_assembly_instance(broken)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[0])["satisfied"])
        self.assertTrue(any("twice" in note for note in result["findings"]))

    def test_a_containment_cycle_fails_the_containment_item(self):
        broken = _case(ASSEMBLY)
        broken["children"].append({"name": "inner", "definition": "ThermalControl"})
        result = evaluate_assembly_instance(broken)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[0])["satisfied"])
        self.assertTrue(any("cycle" in note for note in result["findings"]))

    def test_a_dangling_link_fails_the_link_item_only(self):
        broken = _case(ASSEMBLY)
        broken["links"].append(
            {"name": "leak", "source": "heater_a.telltale", "target": "valve_a.in"}
        )
        result = evaluate_assembly_instance(broken)
        self.assertTrue(_item(result, NORMATIVE_ITEMS[0])["satisfied"])
        self.assertFalse(_item(result, NORMATIVE_ITEMS[1])["satisfied"])

    def test_a_link_reaching_out_without_an_export_fails_the_link_item(self):
        broken = _case(ASSEMBLY, exports=["loop_setpoint"])
        result = evaluate_assembly_instance(broken)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[1])["satisfied"])

    def test_an_unlinked_child_is_listed_without_failing_an_item(self):
        quiet = _case(ASSEMBLY)
        quiet["children"].append({"name": "spare_heater", "definition": "Heater"})
        result = evaluate_assembly_instance(quiet)
        self.assertEqual(result["unlinked_children"], ["spare_heater"])
        self.assertTrue(result["compliant"])

    def test_a_repeated_link_name_rejected(self):
        broken = _case(ASSEMBLY)
        broken["links"].append(dict(ASSEMBLY["links"][0]))
        with self.assertRaises(ValueError):
            evaluate_assembly_instance(broken)

    def test_a_non_mapping_assembly_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_assembly_instance("tcs")

    def test_a_non_sequence_link_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_assembly_instance(_case(ASSEMBLY, links="cmd"))


if __name__ == "__main__":
    unittest.main()
