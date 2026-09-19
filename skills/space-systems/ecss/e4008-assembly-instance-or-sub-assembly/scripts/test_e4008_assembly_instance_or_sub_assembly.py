"""Contract tests for the clause 5.2.9 instance / sub-assembly logic."""

import copy
import unittest

from e4008_assembly_instance_or_sub_assembly_logic import (
    UNBOUNDED,
    AssemblyError,
    assess_assembly,
    container_multiplicity,
    detect_sub_assembly_cycles,
    flatten_instances,
    instance_path,
    validate_instance_name,
)

CATALOGUE = {
    "Gyro": {"abstract": False},
    "Board": {},
    "AbstractSensor": {"abstract": True},
    "Rack": {"container": {"lower": 1, "upper": 2}},
    "OpenRack": {"container": {"lower": 0, "upper": UNBOUNDED}},
}


def base_spec():
    return {
        "catalogue": copy.deepcopy(CATALOGUE),
        "assemblies": {
            "SatelliteAssembly": {
                "instances": [
                    {"name": "aocs", "assembly": "AocsAssembly"},
                    {
                        "name": "rack",
                        "type": "Rack",
                        "instances": [{"name": "board_a", "type": "Board"}],
                    },
                ]
            },
            "AocsAssembly": {
                "instances": [
                    {"name": "gyro", "type": "Gyro"},
                    {"name": "estimator", "type": "Board"},
                ]
            },
        },
        "root": "SatelliteAssembly",
        "max_depth": 8,
    }


class NameTests(unittest.TestCase):
    def test_valid_name_returned(self):
        self.assertEqual(validate_instance_name("gyro_a"), "gyro_a")

    def test_missing_name_refused(self):
        with self.assertRaises(AssemblyError):
            validate_instance_name(None)

    def test_hyphenated_name_refused(self):
        with self.assertRaises(AssemblyError):
            validate_instance_name("gyro-a")

    def test_non_string_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_instance_name(3)

    def test_root_level_path_is_the_name(self):
        self.assertEqual(instance_path("", "aocs"), "aocs")

    def test_nested_path_is_dotted(self):
        self.assertEqual(instance_path("sat.aocs", "gyro"), "sat.aocs.gyro")


class ContainerTests(unittest.TestCase):
    def test_absent_container_returns_none(self):
        self.assertIsNone(container_multiplicity({"abstract": False}))

    def test_declared_container_returns_its_bounds(self):
        self.assertEqual(container_multiplicity(CATALOGUE["Rack"]), (1, 2))

    def test_unbounded_upper_is_kept_as_the_sentinel(self):
        self.assertEqual(container_multiplicity(CATALOGUE["OpenRack"]), (0, UNBOUNDED))

    def test_negative_lower_rejected(self):
        with self.assertRaises(ValueError):
            container_multiplicity({"container": {"lower": -1, "upper": 2}})

    def test_upper_below_lower_rejected(self):
        with self.assertRaises(ValueError):
            container_multiplicity({"container": {"lower": 3, "upper": 1}})

    def test_boolean_bound_rejected(self):
        with self.assertRaises(ValueError):
            container_multiplicity({"container": {"lower": True, "upper": 2}})


class CycleTests(unittest.TestCase):
    def test_acyclic_set_has_no_members(self):
        self.assertEqual(detect_sub_assembly_cycles(base_spec()["assemblies"]), [])

    def test_self_reference_is_a_cycle(self):
        assemblies = {"A": {"instances": [{"name": "a", "assembly": "A"}]}}
        self.assertEqual(detect_sub_assembly_cycles(assemblies), ["A"])

    def test_mutual_reference_is_a_cycle(self):
        assemblies = {
            "A": {"instances": [{"name": "b", "assembly": "B"}]},
            "B": {"instances": [{"name": "a", "assembly": "A"}]},
        }
        self.assertEqual(detect_sub_assembly_cycles(assemblies), ["A", "B"])

    def test_empty_assembly_set_rejected(self):
        with self.assertRaises(ValueError):
            detect_sub_assembly_cycles({})


class FlattenTests(unittest.TestCase):
    def test_clean_tree_is_compliant(self):
        result = assess_assembly(base_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_every_node_is_flattened_once(self):
        result = assess_assembly(base_spec())
        paths = [record["path"] for record in result["instances"]]
        self.assertEqual(
            sorted(paths),
            ["aocs", "aocs.estimator", "aocs.gyro", "rack", "rack.board_a"],
        )

    def test_reported_depth_is_the_deepest_node(self):
        self.assertEqual(assess_assembly(base_spec())["depth"], 2)

    def test_sub_assembly_node_records_the_assembly_it_names(self):
        result = assess_assembly(base_spec())
        aocs = [r for r in result["instances"] if r["path"] == "aocs"][0]
        self.assertEqual(aocs["assembly"], "AocsAssembly")
        self.assertIsNone(aocs["type"])

    def test_flatten_returns_the_visited_assemblies(self):
        _, _, visited = flatten_instances(base_spec())
        self.assertEqual(visited, {"SatelliteAssembly", "AocsAssembly"})


class FindingTests(unittest.TestCase):
    def test_duplicate_sibling_name_is_flagged(self):
        spec = base_spec()
        spec["assemblies"]["AocsAssembly"]["instances"].append(
            {"name": "gyro", "type": "Board"}
        )
        result = assess_assembly(spec)
        self.assertFalse(result["compliant"])
        self.assertIn("already used by a sibling", result["findings"][0])

    def test_invalid_name_is_flagged_not_raised(self):
        spec = base_spec()
        spec["assemblies"]["AocsAssembly"]["instances"][0]["name"] = "1gyro"
        result = assess_assembly(spec)
        self.assertIn("not a valid identifier", result["findings"][0])

    def test_node_naming_both_a_type_and_a_sub_assembly_is_flagged(self):
        spec = base_spec()
        spec["assemblies"]["AocsAssembly"]["instances"][0]["assembly"] = "AocsAssembly"
        result = assess_assembly(spec)
        self.assertIn("names both", result["findings"][0])

    def test_node_naming_neither_is_flagged(self):
        spec = base_spec()
        del spec["assemblies"]["AocsAssembly"]["instances"][0]["type"]
        result = assess_assembly(spec)
        self.assertIn("names neither", result["findings"][0])

    def test_undeclared_model_type_is_flagged(self):
        spec = base_spec()
        spec["assemblies"]["AocsAssembly"]["instances"][0]["type"] = "Magnetometer"
        result = assess_assembly(spec)
        self.assertIn("not declared in the catalogue", result["findings"][0])

    def test_abstract_type_cannot_be_instantiated(self):
        spec = base_spec()
        spec["assemblies"]["AocsAssembly"]["instances"][0]["type"] = "AbstractSensor"
        result = assess_assembly(spec)
        self.assertIn("is abstract", result["findings"][0])

    def test_undeclared_sub_assembly_is_flagged(self):
        spec = base_spec()
        spec["assemblies"]["SatelliteAssembly"]["instances"][0]["assembly"] = "PayloadAssembly"
        result = assess_assembly(spec)
        self.assertIn("is not declared", result["findings"][0])

    def test_children_on_a_non_container_are_flagged(self):
        spec = base_spec()
        spec["assemblies"]["AocsAssembly"]["instances"][0]["instances"] = [
            {"name": "inner", "type": "Board"}
        ]
        result = assess_assembly(spec)
        self.assertIn("declares no containment", result["findings"][0])

    def test_container_below_its_lower_multiplicity_is_flagged(self):
        spec = base_spec()
        spec["assemblies"]["SatelliteAssembly"]["instances"][1]["instances"] = []
        result = assess_assembly(spec)
        self.assertIn("at least 1", result["findings"][0])

    def test_container_above_its_upper_multiplicity_is_flagged(self):
        spec = base_spec()
        spec["assemblies"]["SatelliteAssembly"]["instances"][1]["instances"] = [
            {"name": "board_a", "type": "Board"},
            {"name": "board_b", "type": "Board"},
            {"name": "board_c", "type": "Board"},
        ]
        result = assess_assembly(spec)
        self.assertIn("at most 2", result["findings"][0])

    def test_sub_assembly_node_cannot_carry_its_own_children(self):
        spec = base_spec()
        spec["assemblies"]["SatelliteAssembly"]["instances"][0]["instances"] = [
            {"name": "extra", "type": "Board"}
        ]
        result = assess_assembly(spec)
        self.assertIn("cannot declare", result["findings"][0])

    def test_depth_beyond_the_declared_maximum_is_flagged(self):
        spec = base_spec()
        spec["max_depth"] = 1
        result = assess_assembly(spec)
        self.assertTrue(any("exceeds the declared maximum" in f for f in result["findings"]))

    def test_unreachable_assembly_is_flagged(self):
        spec = base_spec()
        spec["assemblies"]["PayloadAssembly"] = {
            "instances": [{"name": "camera", "type": "Board"}]
        }
        result = assess_assembly(spec)
        self.assertEqual(result["unreachable_assemblies"], ["PayloadAssembly"])
        self.assertIn("never reached from the root", result["findings"][-1])

    def test_cyclic_expansion_is_flagged_and_terminates(self):
        spec = base_spec()
        spec["assemblies"]["AocsAssembly"]["instances"].append(
            {"name": "again", "assembly": "SatelliteAssembly"}
        )
        result = assess_assembly(spec)
        self.assertTrue(any("composition is cyclic" in f for f in result["findings"]))
        self.assertEqual(
            result["cycle_members"], ["AocsAssembly", "SatelliteAssembly"]
        )

    def test_undeclared_root_rejected(self):
        spec = base_spec()
        spec["root"] = "MissingAssembly"
        with self.assertRaises(ValueError):
            assess_assembly(spec)

    def test_non_positive_max_depth_rejected(self):
        spec = base_spec()
        spec["max_depth"] = 0
        with self.assertRaises(ValueError):
            assess_assembly(spec)

    def test_non_mapping_node_rejected(self):
        spec = base_spec()
        spec["assemblies"]["AocsAssembly"]["instances"].append("gyro_b")
        with self.assertRaises(ValueError):
            assess_assembly(spec)

    def test_spec_missing_a_key_rejected(self):
        spec = base_spec()
        del spec["catalogue"]
        with self.assertRaises(ValueError):
            assess_assembly(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly(["catalogue"])


if __name__ == "__main__":
    unittest.main()
