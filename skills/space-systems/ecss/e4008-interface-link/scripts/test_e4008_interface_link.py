"""Contract tests for the clause 5.2.7.2 interface-link logic."""

import unittest

from e4008_interface_link_logic import (
    UNBOUNDED,
    InterfaceLinkError,
    assess_interface_links,
    interface_derives_from,
    multiplicity_report,
    resolve_provided_interface,
    resolve_reference,
    validate_multiplicity,
)

HIERARCHY = {
    "IRegulatedPowerRail": "IPowerRail",
    "ISwitchedPowerRail": "IRegulatedPowerRail",
    "IRateSource": "ISensorSource",
}

CATALOGUE = {
    "Gyro": {
        "references": {
            "supply": {"interface": "IPowerRail", "lower": 1, "upper": 1},
            "monitors": {"interface": "ISensorSource", "lower": 0, "upper": UNBOUNDED},
        },
        "interfaces": {"rate": "IRateSource"},
    },
    "PowerBus": {
        "references": {},
        "interfaces": {"rail_a": "IRegulatedPowerRail", "rail_b": "ISwitchedPowerRail"},
    },
    "Estimator": {
        "references": {"rate_in": {"interface": "IRateSource", "lower": 1, "upper": 2}},
        "interfaces": {"health": "IHealthReport"},
    },
}

INSTANCES = {
    "sat.aocs.gyro": "Gyro",
    "sat.aocs.estimator": "Estimator",
    "sat.power.bus": "PowerBus",
}


def base_links():
    return [
        {
            "name": "gyro_supply",
            "consumer": "sat.aocs.gyro",
            "reference": "supply",
            "provider": "sat.power.bus",
            "interface": "rail_a",
        },
        {
            "name": "estimator_rate",
            "consumer": "sat.aocs.estimator",
            "reference": "rate_in",
            "provider": "sat.aocs.gyro",
            "interface": "rate",
        },
    ]


class MultiplicityTests(unittest.TestCase):
    def test_valid_pair_returned(self):
        self.assertEqual(validate_multiplicity(1, 2), (1, 2))

    def test_unbounded_upper_accepted(self):
        self.assertEqual(validate_multiplicity(0, UNBOUNDED), (0, UNBOUNDED))

    def test_negative_lower_rejected(self):
        with self.assertRaises(ValueError):
            validate_multiplicity(-1, 2)

    def test_upper_below_lower_rejected(self):
        with self.assertRaises(ValueError):
            validate_multiplicity(3, 2)

    def test_boolean_multiplicity_rejected(self):
        with self.assertRaises(ValueError):
            validate_multiplicity(True, 2)

    def test_report_marks_an_over_bound_reference(self):
        reference = {"instance": "a.b", "name": "supply", "lower": 1, "upper": 1}
        report = multiplicity_report(reference, 2)
        self.assertTrue(report["over_bound"])
        self.assertFalse(report["satisfied"])

    def test_report_marks_an_unbound_mandatory_reference(self):
        reference = {"instance": "a.b", "name": "supply", "lower": 1, "upper": 1}
        self.assertTrue(multiplicity_report(reference, 0)["under_bound"])

    def test_unbounded_upper_never_over_binds(self):
        reference = {"instance": "a.b", "name": "monitors", "lower": 0, "upper": UNBOUNDED}
        self.assertTrue(multiplicity_report(reference, 9)["satisfied"])

    def test_negative_bound_count_rejected(self):
        reference = {"instance": "a.b", "name": "supply", "lower": 1, "upper": 1}
        with self.assertRaises(ValueError):
            multiplicity_report(reference, -1)


class HierarchyTests(unittest.TestCase):
    def test_identical_interface_satisfies_itself(self):
        self.assertTrue(interface_derives_from(HIERARCHY, "IPowerRail", "IPowerRail"))

    def test_direct_derivation_satisfies_the_base(self):
        self.assertTrue(interface_derives_from(HIERARCHY, "IRegulatedPowerRail", "IPowerRail"))

    def test_transitive_derivation_satisfies_the_base(self):
        self.assertTrue(interface_derives_from(HIERARCHY, "ISwitchedPowerRail", "IPowerRail"))

    def test_unrelated_interface_does_not_satisfy(self):
        self.assertFalse(interface_derives_from(HIERARCHY, "IRateSource", "IPowerRail"))

    def test_base_does_not_satisfy_its_derived_interface(self):
        self.assertFalse(interface_derives_from(HIERARCHY, "IPowerRail", "IRegulatedPowerRail"))

    def test_cyclic_hierarchy_rejected(self):
        with self.assertRaises(ValueError):
            interface_derives_from({"IA": "IB", "IB": "IA"}, "IA", "IZ")


class ResolutionTests(unittest.TestCase):
    def test_declared_reference_resolves(self):
        reference = resolve_reference(CATALOGUE, INSTANCES, "sat.aocs.gyro", "supply")
        self.assertEqual(reference["interface"], "IPowerRail")
        self.assertEqual(reference["upper"], 1)

    def test_undeclared_reference_refused(self):
        with self.assertRaises(InterfaceLinkError):
            resolve_reference(CATALOGUE, INSTANCES, "sat.aocs.gyro", "clock")

    def test_unknown_consumer_instance_refused(self):
        with self.assertRaises(InterfaceLinkError):
            resolve_reference(CATALOGUE, INSTANCES, "sat.payload.camera", "supply")

    def test_published_interface_resolves(self):
        provided = resolve_provided_interface(
            CATALOGUE, INSTANCES, "sat.power.bus", "rail_b"
        )
        self.assertEqual(provided["interface"], "ISwitchedPowerRail")

    def test_unpublished_interface_refused(self):
        with self.assertRaises(InterfaceLinkError):
            resolve_provided_interface(CATALOGUE, INSTANCES, "sat.power.bus", "rail_c")

    def test_instance_of_an_undeclared_type_rejected(self):
        with self.assertRaises(ValueError):
            resolve_reference(CATALOGUE, {"sat.x": "Missing"}, "sat.x", "supply")


class AssessmentTests(unittest.TestCase):
    def _spec(self, links=None, **overrides):
        spec = {
            "catalogue": CATALOGUE,
            "instances": INSTANCES,
            "interface_hierarchy": HIERARCHY,
            "links": base_links() if links is None else links,
        }
        spec.update(overrides)
        return spec

    def test_clean_binding_set_is_compliant(self):
        result = assess_interface_links(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(len(result["accepted"]), 2)

    def test_derived_interface_satisfies_the_required_base(self):
        result = assess_interface_links(self._spec())
        supply = [r for r in result["reference_reports"] if r["reference"].endswith("supply")]
        self.assertTrue(supply[0]["satisfied"])

    def test_wrong_interface_type_is_flagged(self):
        links = base_links()
        links[0]["provider"] = "sat.aocs.gyro"
        links[0]["interface"] = "rate"
        result = assess_interface_links(self._spec(links=links))
        self.assertFalse(result["compliant"])
        self.assertIn("does not satisfy", result["findings"][0])

    def test_over_bound_reference_is_flagged(self):
        links = base_links()
        links.append(
            {
                "name": "gyro_supply_b",
                "consumer": "sat.aocs.gyro",
                "reference": "supply",
                "provider": "sat.power.bus",
                "interface": "rail_b",
            }
        )
        result = assess_interface_links(self._spec(links=links))
        self.assertFalse(result["compliant"])
        self.assertIn("at most 1 binding", result["findings"][0])

    def test_unbound_mandatory_reference_is_flagged(self):
        result = assess_interface_links(self._spec(links=[base_links()[1]]))
        self.assertFalse(result["compliant"])
        self.assertIn("is mandatory", result["findings"][-1])

    def test_duplicate_binding_of_the_same_interface_is_flagged(self):
        links = base_links()
        links.append(dict(links[1], name="estimator_rate_again"))
        result = assess_interface_links(self._spec(links=links))
        self.assertIn("already bound", result["findings"][0])

    def test_self_binding_is_refused_by_default(self):
        links = [
            {
                "name": "gyro_self",
                "consumer": "sat.aocs.gyro",
                "reference": "monitors",
                "provider": "sat.aocs.gyro",
                "interface": "rate",
            },
            base_links()[0],
            base_links()[1],
        ]
        result = assess_interface_links(self._spec(links=links))
        self.assertIn("self-binding", result["findings"][0])

    def test_self_binding_allowed_when_the_assembly_permits_it(self):
        links = [
            {
                "name": "gyro_self",
                "consumer": "sat.aocs.gyro",
                "reference": "monitors",
                "provider": "sat.aocs.gyro",
                "interface": "rate",
            },
            base_links()[0],
            base_links()[1],
        ]
        result = assess_interface_links(self._spec(links=links, allow_self_binding=True))
        self.assertTrue(result["compliant"])

    def test_unbounded_reference_takes_many_bindings(self):
        links = base_links()
        links.append(
            {
                "name": "gyro_monitor",
                "consumer": "sat.aocs.gyro",
                "reference": "monitors",
                "provider": "sat.aocs.estimator",
                "interface": "health",
            }
        )
        spec = self._spec(links=links)
        spec["interface_hierarchy"] = dict(HIERARCHY, IHealthReport="ISensorSource")
        result = assess_interface_links(spec)
        self.assertTrue(result["compliant"])

    def test_link_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_interface_links(self._spec(links=[{"name": "x", "consumer": "sat.aocs.gyro"}]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_interface_links(["catalogue"])

    def test_spec_missing_instances_rejected(self):
        with self.assertRaises(ValueError):
            assess_interface_links({"catalogue": CATALOGUE, "links": []})


if __name__ == "__main__":
    unittest.main()
