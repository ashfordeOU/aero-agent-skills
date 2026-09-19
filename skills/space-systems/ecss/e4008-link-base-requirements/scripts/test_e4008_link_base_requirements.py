#!/usr/bin/env python3
"""Contract test for the SMP link base base requirements (offline)."""

import copy
import unittest

from e4008_link_base_requirements_logic import (
    FINDING_BINDING_DUPLICATE,
    FINDING_INTERFACE_NOT_PROVIDED,
    FINDING_LINK_DUPLICATE_NAME,
    FINDING_LINK_UNNAMED,
    FINDING_MULTIPLICITY_HIGH,
    FINDING_MULTIPLICITY_LOW,
    FINDING_SELF_BINDING,
    FINDING_SOURCE_INSTANCE,
    FINDING_SOURCE_REFERENCE,
    FINDING_TARGET_INSTANCE,
    VERDICT_REJECTED,
    VERDICT_RESOLVABLE,
    count_bindings,
    evaluate_link_base,
    interface_closure,
    provided_interfaces,
    reference_spec,
    validate_model,
)

INTERFACES = {
    "IRateSource": {"base": None},
    "IGyroRateSource": {"base": "IRateSource"},
    "IThermalSink": {"base": None},
}

TYPES = {
    "AocsModel": {
        "references": {
            "rates": {"interface": "IRateSource", "lower": 1, "upper": 2},
            "peer": {"interface": "IRateSource", "lower": 0, "upper": 1, "allow_self": True},
        },
        "provides": ["IRateSource"],
    },
    "GyroModel": {"references": {}, "provides": ["IGyroRateSource"]},
    "HeaterModel": {"references": {}, "provides": ["IThermalSink"]},
}

INSTANCES = {
    "aocs": {"type": "AocsModel"},
    "gyro": {"type": "GyroModel"},
    "heater": {"type": "HeaterModel"},
}

LINKS = [{"name": "rate-primary", "source": "aocs", "reference": "rates", "target": "gyro"}]


def _links(*extra):
    return copy.deepcopy(LINKS) + [copy.deepcopy(item) for item in extra]


def _codes(result):
    return set(result["finding_codes"])


class InterfaceTests(unittest.TestCase):
    def test_closure_of_a_root_interface_is_itself(self):
        self.assertEqual(interface_closure("IRateSource", INTERFACES), {"IRateSource"})

    def test_closure_of_a_derived_interface_includes_its_base(self):
        self.assertEqual(
            interface_closure("IGyroRateSource", INTERFACES),
            {"IGyroRateSource", "IRateSource"},
        )

    def test_closure_of_an_undeclared_interface_is_itself(self):
        self.assertEqual(interface_closure("IUnknown", INTERFACES), {"IUnknown"})

    def test_cyclic_interface_inheritance_raises(self):
        cyclic = {"IA": {"base": "IB"}, "IB": {"base": "IA"}}
        with self.assertRaises(ValueError):
            interface_closure("IA", cyclic)

    def test_provided_interfaces_are_closed_over_inheritance(self):
        self.assertIn("IRateSource", provided_interfaces("GyroModel", TYPES, INTERFACES))

    def test_provided_interfaces_of_an_undeclared_type_raises(self):
        with self.assertRaises(ValueError):
            provided_interfaces("StarTrackerModel", TYPES, INTERFACES)


class ModelTests(unittest.TestCase):
    def test_reference_model_validates(self):
        self.assertTrue(validate_model(INSTANCES, TYPES, INTERFACES))

    def test_empty_assembly_raises(self):
        with self.assertRaises(ValueError):
            validate_model({}, TYPES, INTERFACES)

    def test_instance_naming_an_undeclared_type_raises(self):
        broken = dict(INSTANCES, imu={"type": "ImuModel"})
        with self.assertRaises(ValueError):
            validate_model(broken, TYPES, INTERFACES)

    def test_reference_with_an_inverted_multiplicity_raises(self):
        broken = copy.deepcopy(TYPES)
        broken["AocsModel"]["references"]["rates"] = {
            "interface": "IRateSource",
            "lower": 3,
            "upper": 1,
        }
        with self.assertRaises(ValueError):
            validate_model(INSTANCES, broken, INTERFACES)

    def test_reference_without_an_interface_raises(self):
        broken = copy.deepcopy(TYPES)
        del broken["AocsModel"]["references"]["rates"]["interface"]
        with self.assertRaises(ValueError):
            validate_model(INSTANCES, broken, INTERFACES)

    def test_reference_spec_resolves_a_declared_reference(self):
        self.assertIsNotNone(reference_spec("aocs", "rates", INSTANCES, TYPES))

    def test_reference_spec_returns_none_for_an_absent_instance(self):
        self.assertIsNone(reference_spec("imu", "rates", INSTANCES, TYPES))


class CountTests(unittest.TestCase):
    def test_bindings_are_counted_per_reference(self):
        counts = count_bindings(
            _links({"name": "rate-backup", "source": "aocs", "reference": "rates", "target": "aocs"})
        )
        self.assertEqual(counts[("aocs", "rates")], 2)

    def test_counting_a_non_list_raises(self):
        with self.assertRaises(ValueError):
            count_bindings("rate-primary")


class LinkBaseTests(unittest.TestCase):
    def test_reference_link_base_resolves(self):
        result = evaluate_link_base(LINKS, INSTANCES, TYPES, INTERFACES)
        self.assertTrue(result["resolvable"])
        self.assertEqual(result["verdict"], VERDICT_RESOLVABLE)
        self.assertEqual(result["resolved_count"], 1)

    def test_derived_interface_satisfies_a_base_interface_reference(self):
        result = evaluate_link_base(LINKS, INSTANCES, TYPES, INTERFACES)
        self.assertEqual(result["resolved_links"][0]["interface"], "IRateSource")

    def test_unnamed_link_is_a_finding(self):
        case = _links()
        case[0]["name"] = "  "
        result = evaluate_link_base(case, INSTANCES, TYPES, INTERFACES)
        self.assertIn(FINDING_LINK_UNNAMED, _codes(result))

    def test_duplicate_link_identity_is_a_finding(self):
        case = _links({"name": "rate-primary", "source": "aocs", "reference": "peer", "target": "aocs"})
        result = evaluate_link_base(case, INSTANCES, TYPES, INTERFACES)
        self.assertIn(FINDING_LINK_DUPLICATE_NAME, _codes(result))

    def test_unresolved_source_instance_is_a_finding(self):
        case = _links()
        case[0]["source"] = "imu"
        result = evaluate_link_base(case, INSTANCES, TYPES, INTERFACES)
        self.assertIn(FINDING_SOURCE_INSTANCE, _codes(result))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)

    def test_reference_not_on_the_source_type_is_a_finding(self):
        case = _links()
        case[0]["reference"] = "attitude"
        result = evaluate_link_base(case, INSTANCES, TYPES, INTERFACES)
        self.assertIn(FINDING_SOURCE_REFERENCE, _codes(result))

    def test_unresolved_target_instance_is_a_finding(self):
        case = _links()
        case[0]["target"] = "imu"
        result = evaluate_link_base(case, INSTANCES, TYPES, INTERFACES)
        self.assertIn(FINDING_TARGET_INSTANCE, _codes(result))

    def test_target_not_providing_the_interface_is_a_finding(self):
        case = _links()
        case[0]["target"] = "heater"
        result = evaluate_link_base(case, INSTANCES, TYPES, INTERFACES)
        self.assertIn(FINDING_INTERFACE_NOT_PROVIDED, _codes(result))

    def test_reference_below_its_lower_bound_is_a_finding(self):
        result = evaluate_link_base([], INSTANCES, TYPES, INTERFACES)
        self.assertIn(FINDING_MULTIPLICITY_LOW, _codes(result))

    def test_reference_above_its_upper_bound_is_a_finding(self):
        wide = dict(INSTANCES)
        wide["gyro2"] = {"type": "GyroModel"}
        wide["gyro3"] = {"type": "GyroModel"}
        case = [
            {"name": "a", "source": "aocs", "reference": "rates", "target": "gyro"},
            {"name": "b", "source": "aocs", "reference": "rates", "target": "gyro2"},
            {"name": "c", "source": "aocs", "reference": "rates", "target": "gyro3"},
        ]
        result = evaluate_link_base(case, wide, TYPES, INTERFACES)
        self.assertEqual(result["binding_counts"][("aocs", "rates")], 3)
        self.assertIn(FINDING_MULTIPLICITY_HIGH, _codes(result))

    def test_reference_exactly_on_its_upper_bound_is_accepted(self):
        wide = dict(INSTANCES)
        wide["gyro2"] = {"type": "GyroModel"}
        case = [
            {"name": "a", "source": "aocs", "reference": "rates", "target": "gyro"},
            {"name": "b", "source": "aocs", "reference": "rates", "target": "gyro2"},
        ]
        result = evaluate_link_base(case, wide, TYPES, INTERFACES)
        self.assertTrue(result["resolvable"])

    def test_self_binding_is_refused_where_the_reference_forbids_it(self):
        case = [{"name": "self", "source": "aocs", "reference": "rates", "target": "aocs"}]
        strict = copy.deepcopy(TYPES)
        strict["AocsModel"]["references"]["rates"]["allow_self"] = False
        result = evaluate_link_base(case, INSTANCES, strict, INTERFACES)
        self.assertIn(FINDING_SELF_BINDING, _codes(result))

    def test_self_binding_is_accepted_where_the_reference_permits_it(self):
        case = [
            {"name": "rate-primary", "source": "aocs", "reference": "rates", "target": "gyro"},
            {"name": "peer-self", "source": "aocs", "reference": "peer", "target": "aocs"},
        ]
        result = evaluate_link_base(case, INSTANCES, TYPES, INTERFACES)
        self.assertNotIn(FINDING_SELF_BINDING, _codes(result))
        self.assertTrue(result["resolvable"])

    def test_the_same_binding_registered_twice_is_a_finding(self):
        case = _links({"name": "rate-again", "source": "aocs", "reference": "rates", "target": "gyro"})
        result = evaluate_link_base(case, INSTANCES, TYPES, INTERFACES)
        self.assertIn(FINDING_BINDING_DUPLICATE, _codes(result))

    def test_link_order_does_not_change_the_verdict(self):
        forward = [
            {"name": "a", "source": "aocs", "reference": "rates", "target": "gyro"},
            {"name": "c", "source": "aocs", "reference": "peer", "target": "aocs"},
        ]
        result_forward = evaluate_link_base(forward, INSTANCES, TYPES, INTERFACES)
        result_reverse = evaluate_link_base(
            list(reversed(forward)), INSTANCES, TYPES, INTERFACES
        )
        self.assertEqual(result_forward["verdict"], result_reverse["verdict"])
        self.assertEqual(result_forward["resolved_count"], result_reverse["resolved_count"])

    def test_link_without_a_target_raises(self):
        case = _links()
        del case[0]["target"]
        with self.assertRaises(ValueError):
            evaluate_link_base(case, INSTANCES, TYPES, INTERFACES)

    def test_non_list_link_base_raises(self):
        with self.assertRaises(ValueError):
            evaluate_link_base("rate-primary", INSTANCES, TYPES, INTERFACES)


if __name__ == "__main__":
    unittest.main()
