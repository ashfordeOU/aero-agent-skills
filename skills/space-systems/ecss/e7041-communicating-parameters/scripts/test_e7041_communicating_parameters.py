"""Contract test for the OBCP parameter-communication leaf (stdlib unittest)."""

import unittest

from e7041_communicating_parameters_logic import (
    DIRECTION_IN,
    DIRECTION_IN_OUT,
    DIRECTION_OUT,
    FINDING_DEFAULT_SUBSTITUTED,
    FINDING_MANDATORY_MISSING,
    FINDING_NO_OBSERVABLE_OUTPUT,
    FINDING_OUT_OF_RANGE,
    FINDING_SUPPLIED_AN_OUTPUT,
    FINDING_UNKNOWN_PARAMETER,
    FINDING_WRITE_TO_INPUT,
    FINDING_WRONG_TYPE,
    TYPE_BOOLEAN,
    TYPE_ENUMERATED,
    TYPE_INTEGER,
    TYPE_REAL,
    assess_parameter_communication,
    bind_activation,
    build_interface,
    check_procedure_writes,
    check_value,
    normalise_parameter,
    observable_outputs,
)


def interface_declarations():
    return [
        {
            "name": "heater-setpoint-k",
            "direction": DIRECTION_IN,
            "type": TYPE_REAL,
            "low": 250.0,
            "high": 320.0,
        },
        {
            "name": "dwell-cycles",
            "direction": DIRECTION_IN,
            "type": TYPE_INTEGER,
            "low": 1,
            "high": 10,
            "default": 3,
        },
        {
            "name": "reached-setpoint",
            "direction": DIRECTION_OUT,
            "type": TYPE_BOOLEAN,
        },
    ]


def findings_of(report):
    return [f["finding"] for f in report["findings"]]


class TestDeclarationValidation(unittest.TestCase):
    def test_a_well_formed_declaration_normalises(self):
        parameter = normalise_parameter(
            {"name": "dwell-cycles", "type": TYPE_INTEGER, "low": 1, "high": 10}
        )
        self.assertEqual(parameter["direction"], DIRECTION_IN)
        self.assertTrue(parameter["mandatory"])

    def test_an_unnamed_parameter_raises(self):
        with self.assertRaises(ValueError):
            normalise_parameter({"type": TYPE_INTEGER})

    def test_an_unknown_direction_raises(self):
        with self.assertRaises(ValueError):
            normalise_parameter({"name": "p", "direction": "sideways"})

    def test_an_inverted_range_raises(self):
        with self.assertRaises(ValueError):
            normalise_parameter(
                {"name": "p", "type": TYPE_REAL, "low": 10.0, "high": 1.0}
            )

    def test_half_a_range_raises(self):
        with self.assertRaises(ValueError):
            normalise_parameter({"name": "p", "type": TYPE_REAL, "low": 1.0})

    def test_an_enumerated_parameter_without_permitted_values_raises(self):
        with self.assertRaises(ValueError):
            normalise_parameter({"name": "mode", "type": TYPE_ENUMERATED})

    def test_an_output_parameter_cannot_carry_an_activation_default(self):
        with self.assertRaises(ValueError):
            normalise_parameter(
                {"name": "p", "direction": DIRECTION_OUT, "type": TYPE_BOOLEAN,
                 "default": True}
            )

    def test_a_default_of_the_wrong_type_raises(self):
        with self.assertRaises(ValueError):
            normalise_parameter(
                {"name": "p", "type": TYPE_INTEGER, "default": "three"}
            )

    def test_a_duplicate_declaration_raises(self):
        with self.assertRaises(ValueError):
            build_interface(
                [{"name": "p", "type": TYPE_INTEGER}, {"name": "p", "type": TYPE_REAL}]
            )

    def test_an_empty_interface_raises(self):
        with self.assertRaises(ValueError):
            build_interface([])


class TestObservability(unittest.TestCase):
    def test_outputs_and_in_outs_are_observable(self):
        interface = build_interface(
            interface_declarations()
            + [{"name": "retry-count", "direction": DIRECTION_IN_OUT,
                "type": TYPE_INTEGER, "default": 0}]
        )
        self.assertEqual(
            observable_outputs(interface), ["reached-setpoint", "retry-count"]
        )

    def test_an_interface_of_inputs_alone_is_observable_only_at_completion(self):
        interface = build_interface([{"name": "p", "type": TYPE_INTEGER}])
        self.assertEqual(observable_outputs(interface), [])

    def test_an_empty_interface_cannot_be_asked_for_outputs(self):
        with self.assertRaises(ValueError):
            observable_outputs({})


class TestValueChecking(unittest.TestCase):
    def test_a_value_on_the_low_bound_is_accepted(self):
        parameter = normalise_parameter(
            {"name": "p", "type": TYPE_REAL, "low": 250.0, "high": 320.0}
        )
        self.assertIsNone(check_value(parameter, 250.0))

    def test_a_value_below_the_low_bound_is_out_of_range(self):
        parameter = normalise_parameter(
            {"name": "p", "type": TYPE_REAL, "low": 250.0, "high": 320.0}
        )
        self.assertEqual(check_value(parameter, 249.5), FINDING_OUT_OF_RANGE)

    def test_a_boolean_supplied_for_an_integer_is_the_wrong_type(self):
        parameter = normalise_parameter({"name": "p", "type": TYPE_INTEGER})
        self.assertEqual(check_value(parameter, True), FINDING_WRONG_TYPE)

    def test_an_enumerated_value_outside_the_permitted_list_is_out_of_range(self):
        parameter = normalise_parameter(
            {"name": "mode", "type": TYPE_ENUMERATED, "permitted": ["hold", "ramp"]}
        )
        self.assertIsNone(check_value(parameter, "ramp"))
        self.assertEqual(check_value(parameter, "coast"), FINDING_OUT_OF_RANGE)


class TestBinding(unittest.TestCase):
    def setUp(self):
        self.interface = build_interface(interface_declarations())

    def test_a_complete_activation_binds_every_input(self):
        result = bind_activation(
            self.interface, {"heater-setpoint-k": 300.0, "dwell-cycles": 5}
        )
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["bound"]["heater-setpoint-k"], 300.0, places=9)
        self.assertEqual(result["bound"]["dwell-cycles"], 5)

    def test_an_omitted_optional_input_takes_its_default(self):
        result = bind_activation(self.interface, {"heater-setpoint-k": 300.0})
        self.assertEqual(result["bound"]["dwell-cycles"], 3)
        self.assertIn(FINDING_DEFAULT_SUBSTITUTED, [f["finding"] for f in result["findings"]])

    def test_an_omitted_mandatory_input_is_a_finding(self):
        result = bind_activation(self.interface, {"dwell-cycles": 5})
        self.assertIn(FINDING_MANDATORY_MISSING, [f["finding"] for f in result["findings"]])

    def test_an_undeclared_name_is_rejected_rather_than_dropped(self):
        result = bind_activation(
            self.interface, {"heater-setpoint-k": 300.0, "soak-minutes": 4}
        )
        self.assertIn(FINDING_UNKNOWN_PARAMETER, [f["finding"] for f in result["findings"]])
        self.assertNotIn("soak-minutes", result["bound"])

    def test_supplying_an_output_only_parameter_is_rejected(self):
        result = bind_activation(
            self.interface, {"heater-setpoint-k": 300.0, "reached-setpoint": True}
        )
        self.assertIn(
            FINDING_SUPPLIED_AN_OUTPUT, [f["finding"] for f in result["findings"]]
        )

    def test_supplied_arguments_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            bind_activation(self.interface, [("heater-setpoint-k", 300.0)])


class TestProcedureWrites(unittest.TestCase):
    def test_writing_to_an_input_only_parameter_is_a_finding(self):
        interface = build_interface(interface_declarations())
        findings = check_procedure_writes(interface, ["heater-setpoint-k"])
        self.assertEqual(findings[0]["finding"], FINDING_WRITE_TO_INPUT)

    def test_writing_to_an_output_parameter_is_clean(self):
        interface = build_interface(interface_declarations())
        self.assertEqual(check_procedure_writes(interface, ["reached-setpoint"]), [])

    def test_writing_to_an_undeclared_parameter_is_a_finding(self):
        interface = build_interface(interface_declarations())
        findings = check_procedure_writes(interface, ["soak-minutes"])
        self.assertEqual(findings[0]["finding"], FINDING_UNKNOWN_PARAMETER)

    def test_writes_must_be_a_list(self):
        interface = build_interface(interface_declarations())
        with self.assertRaises(ValueError):
            check_procedure_writes(interface, "heater-setpoint-k")


class TestAssessment(unittest.TestCase):
    def test_a_clean_activation_is_accepted(self):
        report = assess_parameter_communication(
            interface_declarations(),
            {"heater-setpoint-k": 300.0, "dwell-cycles": 5},
            writes=["reached-setpoint"],
        )
        self.assertTrue(report["activation_accepted"])
        self.assertEqual(report["declared_count"], 3)
        self.assertEqual(report["bound_count"], 2)

    def test_a_default_substitution_alone_does_not_block_the_activation(self):
        report = assess_parameter_communication(
            interface_declarations(), {"heater-setpoint-k": 300.0}
        )
        self.assertTrue(report["activation_accepted"])
        self.assertIn(FINDING_DEFAULT_SUBSTITUTED, findings_of(report))

    def test_an_out_of_range_value_blocks_the_activation(self):
        report = assess_parameter_communication(
            interface_declarations(), {"heater-setpoint-k": 400.0, "dwell-cycles": 5}
        )
        self.assertFalse(report["activation_accepted"])
        self.assertIn(FINDING_OUT_OF_RANGE, findings_of(report))

    def test_an_interface_with_no_output_is_flagged_but_still_activates(self):
        report = assess_parameter_communication(
            [{"name": "dwell-cycles", "type": TYPE_INTEGER, "default": 3}], {}
        )
        self.assertTrue(report["activation_accepted"])
        self.assertIn(FINDING_NO_OBSERVABLE_OUTPUT, findings_of(report))
        self.assertEqual(report["observable_outputs"], [])

    def test_a_write_to_an_input_blocks_the_activation_report(self):
        report = assess_parameter_communication(
            interface_declarations(),
            {"heater-setpoint-k": 300.0, "dwell-cycles": 5},
            writes=["dwell-cycles"],
        )
        self.assertFalse(report["activation_accepted"])
        self.assertIn(FINDING_WRITE_TO_INPUT, findings_of(report))


if __name__ == "__main__":
    unittest.main()
