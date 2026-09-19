"""Contract tests for the clause 5.2.7.1 general link-rule logic."""

import unittest

from e4008_link_general_logic import (
    LINK_KINDS,
    LinkError,
    assess_link_set,
    endpoint_signature,
    instance_scope,
    link_signature,
    normalize_path,
    resolve_endpoint,
    validate_identifier,
)

INSTANCES = [
    "sat.aocs.gyro",
    "sat.aocs.estimator",
    "sat.power.bus",
    "sat.aocs",
]
SCOPE = instance_scope(INSTANCES)


class IdentifierTests(unittest.TestCase):
    def test_plain_identifier_accepted(self):
        self.assertEqual(validate_identifier("rate_out"), "rate_out")

    def test_leading_digit_refused(self):
        with self.assertRaises(LinkError):
            validate_identifier("2rate")

    def test_hyphen_refused(self):
        with self.assertRaises(LinkError):
            validate_identifier("rate-out")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(7)


class PathTests(unittest.TestCase):
    def test_dotted_path_splits_into_segments(self):
        self.assertEqual(normalize_path("sat.aocs.gyro"), ("sat", "aocs", "gyro"))

    def test_blank_path_rejected(self):
        with self.assertRaises(ValueError):
            normalize_path("  ")

    def test_empty_segment_refused(self):
        with self.assertRaises(LinkError):
            normalize_path("sat..gyro")

    def test_duplicate_instance_declaration_rejected(self):
        with self.assertRaises(ValueError):
            instance_scope(["sat.a", "sat.a"])

    def test_empty_instance_list_rejected(self):
        with self.assertRaises(ValueError):
            instance_scope([])


class ResolveEndpointTests(unittest.TestCase):
    def test_longest_declared_prefix_wins(self):
        resolved = resolve_endpoint(SCOPE, "sat.aocs.gyro.rate_out")
        self.assertEqual(resolved["instance"], "sat.aocs.gyro")
        self.assertEqual(resolved["element"], "rate_out")

    def test_shallower_instance_still_resolves(self):
        resolved = resolve_endpoint(SCOPE, "sat.aocs.mode_in")
        self.assertEqual(resolved["instance"], "sat.aocs")
        self.assertEqual(resolved["element"], "mode_in")

    def test_nested_element_path_is_kept_whole(self):
        resolved = resolve_endpoint(SCOPE, "sat.power.bus.rail.voltage")
        self.assertEqual(resolved["element"], "rail.voltage")

    def test_endpoint_outside_the_assembly_refused(self):
        with self.assertRaises(LinkError):
            resolve_endpoint(SCOPE, "ground.station.clock")

    def test_endpoint_naming_only_an_instance_refused(self):
        with self.assertRaises(LinkError):
            resolve_endpoint(SCOPE, "sat.power.bus")

    def test_signature_joins_instance_and_element(self):
        resolved = resolve_endpoint(SCOPE, "sat.aocs.gyro.rate_out")
        self.assertEqual(endpoint_signature(resolved), "sat.aocs.gyro.rate_out")

    def test_malformed_resolved_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            endpoint_signature({"instance": "sat.aocs"})


class SignatureTests(unittest.TestCase):
    def test_three_kinds_are_declared(self):
        self.assertEqual(set(LINK_KINDS), {"interface", "event", "field"})

    def test_signature_carries_the_kind(self):
        source = resolve_endpoint(SCOPE, "sat.aocs.gyro.rate_out")
        target = resolve_endpoint(SCOPE, "sat.aocs.estimator.rate_in")
        self.assertEqual(link_signature("field", source, target)[0], "field")

    def test_unknown_kind_refused(self):
        source = resolve_endpoint(SCOPE, "sat.aocs.gyro.rate_out")
        with self.assertRaises(LinkError):
            link_signature("telemetry", source, source)


class AssessLinkSetTests(unittest.TestCase):
    def _spec(self, links=None, **overrides):
        spec = {
            "instances": INSTANCES,
            "links": links
            if links is not None
            else [
                {
                    "name": "rate_to_estimator",
                    "kind": "field",
                    "source": "sat.aocs.gyro.rate_out",
                    "target": "sat.aocs.estimator.rate_in",
                },
                {
                    "name": "power_to_gyro",
                    "kind": "interface",
                    "source": "sat.aocs.gyro.supply",
                    "target": "sat.power.bus.rail_a",
                },
            ],
        }
        spec.update(overrides)
        return spec

    def test_clean_link_set_is_compliant(self):
        result = assess_link_set(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(len(result["accepted"]), 2)

    def test_per_kind_tally_is_reported(self):
        result = assess_link_set(self._spec())
        self.assertEqual(result["per_kind"]["field"], 1)
        self.assertEqual(result["per_kind"]["event"], 0)

    def test_repeated_link_name_is_flagged(self):
        links = self._spec()["links"]
        links.append(dict(links[0], source="sat.power.bus.rail_b"))
        result = assess_link_set(self._spec(links=links))
        self.assertFalse(result["compliant"])
        self.assertIn("already used", result["findings"][0])

    def test_dangling_endpoint_is_flagged(self):
        links = [
            {
                "name": "to_nowhere",
                "kind": "field",
                "source": "sat.aocs.gyro.rate_out",
                "target": "sat.payload.camera.rate_in",
            }
        ]
        result = assess_link_set(self._spec(links=links))
        self.assertIn("does not resolve", result["findings"][0])

    def test_unknown_kind_is_flagged(self):
        links = [
            {
                "name": "odd_kind",
                "kind": "dataflow",
                "source": "sat.aocs.gyro.rate_out",
                "target": "sat.aocs.estimator.rate_in",
            }
        ]
        result = assess_link_set(self._spec(links=links))
        self.assertIn("is not one of", result["findings"][0])

    def test_duplicate_link_is_flagged_once(self):
        links = self._spec()["links"]
        links.append(dict(links[0], name="rate_again"))
        result = assess_link_set(self._spec(links=links))
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("duplicates link", result["findings"][0])

    def test_self_link_is_refused_by_default(self):
        links = [
            {
                "name": "loop_back",
                "kind": "field",
                "source": "sat.aocs.gyro.rate_out",
                "target": "sat.aocs.gyro.rate_in",
            }
        ]
        result = assess_link_set(self._spec(links=links))
        self.assertIn("self-link", result["findings"][0])

    def test_self_link_allowed_when_the_assembly_permits_it(self):
        links = [
            {
                "name": "loop_back",
                "kind": "field",
                "source": "sat.aocs.gyro.rate_out",
                "target": "sat.aocs.gyro.rate_in",
            }
        ]
        result = assess_link_set(self._spec(links=links, allow_self_links=True))
        self.assertTrue(result["compliant"])

    def test_invalid_link_name_is_flagged_not_raised(self):
        links = [
            {
                "name": "rate-to-estimator",
                "kind": "field",
                "source": "sat.aocs.gyro.rate_out",
                "target": "sat.aocs.estimator.rate_in",
            }
        ]
        result = assess_link_set(self._spec(links=links))
        self.assertIn("not a valid identifier", result["findings"][0])

    def test_empty_link_set_is_vacuously_compliant(self):
        result = assess_link_set(self._spec(links=[]))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["accepted"], [])

    def test_link_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_link_set(self._spec(links=[{"name": "x", "kind": "field"}]))

    def test_non_mapping_link_rejected(self):
        with self.assertRaises(ValueError):
            assess_link_set(self._spec(links=["rate_to_estimator"]))

    def test_spec_without_links_rejected(self):
        with self.assertRaises(ValueError):
            assess_link_set({"instances": INSTANCES})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_link_set(["instances"])


if __name__ == "__main__":
    unittest.main()
