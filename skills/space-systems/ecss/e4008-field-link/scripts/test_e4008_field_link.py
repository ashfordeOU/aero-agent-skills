"""Contract tests for the clause 5.2.7.4 field-link logic."""

import unittest

from e4008_field_link_logic import (
    READABLE_DIRECTIONS,
    WRITEABLE_DIRECTIONS,
    FieldLinkError,
    assess_field_links,
    detect_dataflow_cycles,
    field_shape,
    resolve_field_endpoint,
    shapes_match,
)

CATALOGUE = {
    "Gyro": {
        "fields": {
            "rate_out": {"direction": "output", "datatype": "Float64", "dimensions": [3]},
            "bias": {"direction": "state", "datatype": "Float64", "dimensions": [3]},
            "enable_in": {"direction": "input", "datatype": "Bool"},
        }
    },
    "Estimator": {
        "fields": {
            "rate_in": {"direction": "input", "datatype": "Float64", "dimensions": [3]},
            "count_in": {"direction": "input", "datatype": "Int32"},
            "attitude_out": {"direction": "output", "datatype": "Float64", "dimensions": [4]},
            "enable_out": {"direction": "output", "datatype": "Bool"},
        }
    },
    "Controller": {
        "fields": {
            "attitude_in": {"direction": "input", "datatype": "Float64", "dimensions": [4]},
            "torque_out": {"direction": "output", "datatype": "Float64", "dimensions": [3]},
            "enable_in": {"direction": "input", "datatype": "Bool"},
        }
    },
}

INSTANCES = {
    "sat.aocs.gyro": "Gyro",
    "sat.aocs.estimator": "Estimator",
    "sat.aocs.controller": "Controller",
}


def base_links():
    return [
        {
            "name": "rate_flow",
            "source": "sat.aocs.gyro",
            "source_field": "rate_out",
            "target": "sat.aocs.estimator",
            "target_field": "rate_in",
        },
        {
            "name": "attitude_flow",
            "source": "sat.aocs.estimator",
            "source_field": "attitude_out",
            "target": "sat.aocs.controller",
            "target_field": "attitude_in",
        },
    ]


class ShapeTests(unittest.TestCase):
    def test_scalar_field_has_an_empty_shape(self):
        self.assertEqual(field_shape({"datatype": "Bool"}), ())

    def test_array_field_reports_its_extent(self):
        self.assertEqual(field_shape({"datatype": "Float64", "dimensions": [3]}), (3,))

    def test_multidimensional_shape_is_kept_in_order(self):
        self.assertEqual(field_shape({"datatype": "Float64", "dimensions": [3, 4]}), (3, 4))

    def test_zero_extent_rejected(self):
        with self.assertRaises(ValueError):
            field_shape({"datatype": "Float64", "dimensions": [0]})

    def test_empty_dimension_list_rejected(self):
        with self.assertRaises(ValueError):
            field_shape({"datatype": "Float64", "dimensions": []})

    def test_equal_shapes_match(self):
        left = {"datatype": "Float64", "dimensions": [3]}
        self.assertTrue(shapes_match(left, dict(left)))

    def test_scalar_and_array_do_not_match(self):
        self.assertFalse(
            shapes_match({"datatype": "Float64"}, {"datatype": "Float64", "dimensions": [1]})
        )


class ResolveTests(unittest.TestCase):
    def test_output_field_resolves_as_a_source(self):
        resolved = resolve_field_endpoint(
            CATALOGUE, INSTANCES, "sat.aocs.gyro", "rate_out", "source"
        )
        self.assertEqual(resolved["shape"], (3,))
        self.assertEqual(resolved["path"], "sat.aocs.gyro.rate_out")

    def test_state_field_can_be_a_source(self):
        resolved = resolve_field_endpoint(
            CATALOGUE, INSTANCES, "sat.aocs.gyro", "bias", "source"
        )
        self.assertEqual(resolved["direction"], "state")

    def test_state_field_can_also_be_a_target(self):
        resolved = resolve_field_endpoint(
            CATALOGUE, INSTANCES, "sat.aocs.gyro", "bias", "target"
        )
        self.assertEqual(resolved["direction"], "state")

    def test_input_field_cannot_be_a_source(self):
        with self.assertRaises(FieldLinkError):
            resolve_field_endpoint(
                CATALOGUE, INSTANCES, "sat.aocs.estimator", "rate_in", "source"
            )

    def test_output_field_cannot_be_a_target(self):
        with self.assertRaises(FieldLinkError):
            resolve_field_endpoint(
                CATALOGUE, INSTANCES, "sat.aocs.gyro", "rate_out", "target"
            )

    def test_undeclared_field_refused(self):
        with self.assertRaises(FieldLinkError):
            resolve_field_endpoint(CATALOGUE, INSTANCES, "sat.aocs.gyro", "drift", "source")

    def test_unknown_instance_refused(self):
        with self.assertRaises(FieldLinkError):
            resolve_field_endpoint(CATALOGUE, INSTANCES, "sat.payload", "rate_out", "source")

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            resolve_field_endpoint(CATALOGUE, INSTANCES, "sat.aocs.gyro", "rate_out", "reader")

    def test_direction_sets_are_the_declared_ones(self):
        self.assertEqual(set(READABLE_DIRECTIONS), {"output", "state"})
        self.assertEqual(set(WRITEABLE_DIRECTIONS), {"input", "state"})


class CycleTests(unittest.TestCase):
    def test_acyclic_chain_has_no_cycle_members(self):
        result = assess_field_links(
            {"catalogue": CATALOGUE, "instances": INSTANCES, "links": base_links()}
        )
        self.assertEqual(result["cycle_members"], [])

    def test_cycle_is_detected_and_reported_as_an_advisory(self):
        links = base_links()
        links.append(
            {
                "name": "enable_back",
                "source": "sat.aocs.estimator",
                "source_field": "enable_out",
                "target": "sat.aocs.gyro",
                "target_field": "enable_in",
            }
        )
        result = assess_field_links(
            {"catalogue": CATALOGUE, "instances": INSTANCES, "links": links}
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(
            result["cycle_members"], ["sat.aocs.estimator", "sat.aocs.gyro"]
        )
        self.assertEqual(len(result["advisories"]), 1)

    def test_malformed_accepted_link_rejected(self):
        with self.assertRaises(ValueError):
            detect_dataflow_cycles([{"source": {"instance": "a"}}])


class AssessmentTests(unittest.TestCase):
    def _spec(self, links=None, **overrides):
        spec = {
            "catalogue": CATALOGUE,
            "instances": INSTANCES,
            "links": base_links() if links is None else links,
        }
        spec.update(overrides)
        return spec

    def test_clean_field_link_set_is_compliant(self):
        result = assess_field_links(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(len(result["accepted"]), 2)

    def test_driven_fields_are_reported_for_the_configuration_check(self):
        result = assess_field_links(self._spec())
        self.assertEqual(
            result["driven_fields"],
            ["sat.aocs.controller.attitude_in", "sat.aocs.estimator.rate_in"],
        )

    def test_datatype_mismatch_is_flagged(self):
        links = [
            {
                "name": "rate_to_count",
                "source": "sat.aocs.gyro",
                "source_field": "rate_out",
                "target": "sat.aocs.estimator",
                "target_field": "count_in",
            }
        ]
        result = assess_field_links(self._spec(links=links))
        self.assertFalse(result["compliant"])
        self.assertIn("does not convert", result["findings"][0])

    def test_shape_mismatch_is_flagged(self):
        links = [
            {
                "name": "attitude_into_rate",
                "source": "sat.aocs.estimator",
                "source_field": "attitude_out",
                "target": "sat.aocs.estimator",
                "target_field": "rate_in",
            }
        ]
        result = assess_field_links(self._spec(links=links, allow_self_links=True))
        self.assertIn("does not match target shape", result["findings"][0])

    def test_second_writer_into_one_target_is_flagged(self):
        links = base_links()
        links.append(
            {
                "name": "bias_flow",
                "source": "sat.aocs.gyro",
                "source_field": "bias",
                "target": "sat.aocs.estimator",
                "target_field": "rate_in",
            }
        )
        result = assess_field_links(self._spec(links=links))
        self.assertFalse(result["compliant"])
        self.assertIn("already written by link", result["findings"][0])

    def test_input_used_as_a_source_is_flagged(self):
        links = [
            {
                "name": "backwards",
                "source": "sat.aocs.estimator",
                "source_field": "rate_in",
                "target": "sat.aocs.controller",
                "target_field": "attitude_in",
            }
        ]
        result = assess_field_links(self._spec(links=links))
        self.assertIn("cannot be the source", result["findings"][0])

    def test_self_link_on_one_instance_is_refused_by_default(self):
        links = [
            {
                "name": "bias_self",
                "source": "sat.aocs.gyro",
                "source_field": "rate_out",
                "target": "sat.aocs.gyro",
                "target_field": "bias",
            }
        ]
        result = assess_field_links(self._spec(links=links))
        self.assertIn("self-link", result["findings"][0])

    def test_field_linked_to_itself_is_refused_even_when_self_links_are_allowed(self):
        links = [
            {
                "name": "bias_identity",
                "source": "sat.aocs.gyro",
                "source_field": "bias",
                "target": "sat.aocs.gyro",
                "target_field": "bias",
            }
        ]
        result = assess_field_links(self._spec(links=links, allow_self_links=True))
        self.assertIn("linked to itself", result["findings"][0])

    def test_empty_link_set_is_vacuously_compliant(self):
        result = assess_field_links(self._spec(links=[]))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["driven_fields"], [])

    def test_link_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_field_links(self._spec(links=[{"name": "x", "source": "sat.aocs.gyro"}]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_field_links(["catalogue"])

    def test_spec_missing_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            assess_field_links({"instances": INSTANCES, "links": []})


if __name__ == "__main__":
    unittest.main()
