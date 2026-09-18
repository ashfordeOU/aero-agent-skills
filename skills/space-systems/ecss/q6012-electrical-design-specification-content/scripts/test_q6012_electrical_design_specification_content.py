"""Contract tests for the clause 7.2.1 electrical-specification content logic."""

import unittest

from q6012_electrical_design_specification_content_logic import (
    MANDATED_INTERFACES,
    MANDATED_PARAMETERS,
    assess_electrical_specification,
    build_parameter_set,
    completeness_ratio,
    interface_gaps,
    missing_test_conditions,
    out_of_envelope_conditions,
    parameter_coverage,
    unit_mismatches,
    validate_interface,
    validate_parameter,
    validate_range,
)

TEMPERATURE_RANGE = (-30.0, 85.0)
SUPPLY_RANGE = (4.5, 5.5)


def parameter(name, unit=None, minimum=None, maximum=None,
              condition="25 C, 5 V, 50 ohm system", temperature=25.0, supply=5.0):
    if unit is None:
        unit = MANDATED_PARAMETERS.get(name, "dB")
    if minimum is None and maximum is None:
        minimum = 1.0
    return {
        "name": name,
        "unit": unit,
        "minimum": minimum,
        "maximum": maximum,
        "test_condition": condition,
        "condition_temperature_c": temperature,
        "condition_supply_v": supply,
    }


def full_parameters():
    return [parameter(name) for name in sorted(MANDATED_PARAMETERS)]


def full_interfaces():
    return [
        {"name": "rf-input", "impedance_ohm": 50.0},
        {"name": "rf-output", "impedance_ohm": 50.0},
        {"name": "dc-bias", "bias_voltage_v": 5.0},
        {"name": "ground-reference"},
    ]


class ValidateRangeTests(unittest.TestCase):
    def test_returns_float_pair(self):
        self.assertEqual(validate_range((-30, 85), "t"), (-30.0, 85.0))

    def test_equal_bounds_allowed(self):
        self.assertEqual(validate_range((5.0, 5.0), "v"), (5.0, 5.0))

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_range((85.0, -30.0), "t")

    def test_wrong_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_range((1.0, 2.0, 3.0), "t")

    def test_non_numeric_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_range(("cold", 85.0), "t")


class ValidateParameterTests(unittest.TestCase):
    def test_canonicalises_the_name(self):
        record = validate_parameter(parameter("Noise Figure"))
        self.assertEqual(record["name"], "noise-figure")

    def test_a_maximum_alone_is_a_valid_bound(self):
        record = validate_parameter(parameter("noise-figure", minimum=None, maximum=2.5))
        self.assertIsNone(record["minimum"])
        self.assertAlmostEqual(record["maximum"], 2.5, places=9)

    def test_unbounded_parameter_rejected(self):
        bad = parameter("noise-figure")
        bad["minimum"] = None
        bad["maximum"] = None
        with self.assertRaises(ValueError):
            validate_parameter(bad)

    def test_minimum_above_maximum_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter("small-signal-gain", minimum=20.0, maximum=15.0))

    def test_equal_minimum_and_maximum_accepted(self):
        record = validate_parameter(
            parameter("supply-voltage", unit="V", minimum=5.0, maximum=5.0)
        )
        self.assertAlmostEqual(record["minimum"], record["maximum"], places=9)

    def test_boolean_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter("noise-figure", minimum=True))

    def test_non_finite_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter("noise-figure", maximum=float("nan")))

    def test_blank_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter("noise-figure", unit="   "))

    def test_absent_unit_recorded_as_none(self):
        record = validate_parameter(
            {"name": "noise-figure", "maximum": 2.5, "test_condition": "25 C"}
        )
        self.assertIsNone(record["unit"])

    def test_missing_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter({"maximum": 2.5})

    def test_non_mapping_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(["noise-figure", 2.5])


class BuildParameterSetTests(unittest.TestCase):
    def test_builds_every_mandated_parameter(self):
        records = build_parameter_set(full_parameters())
        self.assertEqual(len(records), len(MANDATED_PARAMETERS))

    def test_repeated_parameter_rejected(self):
        with self.assertRaises(ValueError):
            build_parameter_set([parameter("noise-figure"), parameter("Noise figure")])

    def test_empty_parameter_set_rejected(self):
        with self.assertRaises(ValueError):
            build_parameter_set([])


class ParameterCoverageTests(unittest.TestCase):
    def test_full_draft_has_no_gap(self):
        coverage = parameter_coverage(build_parameter_set(full_parameters()))
        self.assertEqual(coverage["missing"], [])

    def test_omitted_parameter_named(self):
        params = [p for p in full_parameters() if p["name"] != "gain-flatness"]
        coverage = parameter_coverage(build_parameter_set(params))
        self.assertEqual(coverage["missing"], ["gain-flatness"])

    def test_project_addition_is_not_a_gap(self):
        params = full_parameters() + [parameter("third-order-intercept", unit="dBm")]
        coverage = parameter_coverage(build_parameter_set(params))
        self.assertEqual(coverage["missing"], [])
        self.assertEqual(coverage["additional"], ["third-order-intercept"])


class UnitAndConditionTests(unittest.TestCase):
    def test_wrong_unit_reported_with_the_expected_one(self):
        params = full_parameters()
        for item in params:
            if item["name"] == "noise-figure":
                item["unit"] = "dBm"
        findings = unit_mismatches(build_parameter_set(params))
        self.assertIn(("noise-figure", "dBm", "dB"), findings)

    def test_absent_unit_is_a_mismatch(self):
        records = build_parameter_set(
            [{"name": "noise-figure", "maximum": 2.5, "test_condition": "25 C"}]
        )
        self.assertEqual(unit_mismatches(records), [("noise-figure", None, "dB")])

    def test_additional_parameter_unit_is_not_graded(self):
        records = build_parameter_set([parameter("third-order-intercept", unit="kg")])
        self.assertEqual(unit_mismatches(records), [])

    def test_missing_test_condition_named(self):
        params = full_parameters()
        params[1]["test_condition"] = None
        records = build_parameter_set(params)
        self.assertEqual(missing_test_conditions(records), [params[1]["name"]])

    def test_full_draft_states_every_test_condition(self):
        self.assertEqual(missing_test_conditions(build_parameter_set(full_parameters())), [])


class EnvelopeTests(unittest.TestCase):
    def test_condition_inside_the_envelope_is_clean(self):
        records = build_parameter_set(full_parameters())
        self.assertEqual(
            out_of_envelope_conditions(records, TEMPERATURE_RANGE, SUPPLY_RANGE), []
        )

    def test_hot_condition_reported(self):
        params = full_parameters()
        params[0]["condition_temperature_c"] = 125.0
        records = build_parameter_set(params)
        findings = out_of_envelope_conditions(records, TEMPERATURE_RANGE, SUPPLY_RANGE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0][1], "condition_temperature_c")

    def test_supply_above_the_envelope_reported(self):
        params = full_parameters()
        params[2]["condition_supply_v"] = 6.0
        records = build_parameter_set(params)
        findings = out_of_envelope_conditions(records, TEMPERATURE_RANGE, SUPPLY_RANGE)
        self.assertEqual(findings[0][1], "condition_supply_v")

    def test_condition_exactly_on_the_envelope_bound_is_inside(self):
        params = full_parameters()
        params[0]["condition_temperature_c"] = TEMPERATURE_RANGE[1]
        params[0]["condition_supply_v"] = SUPPLY_RANGE[0]
        records = build_parameter_set(params)
        self.assertAlmostEqual(
            records[0]["condition_temperature_c"], TEMPERATURE_RANGE[1], places=9
        )
        self.assertEqual(
            out_of_envelope_conditions(records, TEMPERATURE_RANGE, SUPPLY_RANGE), []
        )

    def test_unstated_condition_is_not_an_envelope_finding(self):
        params = full_parameters()
        for item in params:
            item["condition_temperature_c"] = None
            item["condition_supply_v"] = None
        records = build_parameter_set(params)
        self.assertEqual(
            out_of_envelope_conditions(records, TEMPERATURE_RANGE, SUPPLY_RANGE), []
        )


class InterfaceTests(unittest.TestCase):
    def test_full_interface_set_is_clean(self):
        gaps = interface_gaps(full_interfaces())
        self.assertEqual(gaps["absent"], [])
        self.assertEqual(gaps["no_impedance"], [])
        self.assertEqual(gaps["no_bias"], [])

    def test_absent_port_named(self):
        gaps = interface_gaps([i for i in full_interfaces() if i["name"] != "dc-bias"])
        self.assertEqual(gaps["absent"], ["dc-bias"])

    def test_rf_port_without_impedance_named(self):
        interfaces = full_interfaces()
        del interfaces[1]["impedance_ohm"]
        self.assertEqual(interface_gaps(interfaces)["no_impedance"], ["rf-output"])

    def test_dc_port_without_bias_named(self):
        interfaces = full_interfaces()
        del interfaces[2]["bias_voltage_v"]
        self.assertEqual(interface_gaps(interfaces)["no_bias"], ["dc-bias"])

    def test_non_positive_impedance_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface({"name": "rf-input", "impedance_ohm": 0.0})

    def test_duplicate_interface_rejected(self):
        with self.assertRaises(ValueError):
            interface_gaps(full_interfaces() + [{"name": "RF Input", "impedance_ohm": 50.0}])

    def test_negative_bias_voltage_is_accepted(self):
        record = validate_interface({"name": "dc-bias", "bias_voltage_v": -5.0})
        self.assertAlmostEqual(record["bias_voltage_v"], -5.0, places=9)


class CompletenessRatioTests(unittest.TestCase):
    def test_full_draft_scores_one(self):
        records = build_parameter_set(full_parameters())
        gaps = interface_gaps(full_interfaces())
        self.assertAlmostEqual(completeness_ratio(records, gaps), 1.0, places=9)

    def test_one_missing_parameter_lowers_the_ratio(self):
        params = [p for p in full_parameters() if p["name"] != "noise-figure"]
        records = build_parameter_set(params)
        gaps = interface_gaps(full_interfaces())
        total = len(MANDATED_PARAMETERS) + len(MANDATED_INTERFACES)
        self.assertAlmostEqual(
            completeness_ratio(records, gaps), (total - 1) / float(total), places=9
        )


class AssessElectricalSpecificationTests(unittest.TestCase):
    def _spec(self, **kwargs):
        spec = {
            "parameters": full_parameters(),
            "interfaces": full_interfaces(),
            "temperature_range_c": TEMPERATURE_RANGE,
            "supply_range_v": SUPPLY_RANGE,
        }
        spec.update(kwargs)
        return spec

    def test_complete_draft_is_released(self):
        result = assess_electrical_specification(self._spec())
        self.assertTrue(result["released"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["completeness_ratio"], 1.0, places=9)

    def test_missing_parameter_holds_the_draft(self):
        params = [p for p in full_parameters() if p["name"] != "output-power"]
        result = assess_electrical_specification(self._spec(parameters=params))
        self.assertFalse(result["released"])
        self.assertEqual(result["missing_parameters"], ["output-power"])

    def test_wrong_unit_holds_the_draft(self):
        params = full_parameters()
        for item in params:
            if item["name"] == "supply-current":
                item["unit"] = "A"
        result = assess_electrical_specification(self._spec(parameters=params))
        self.assertFalse(result["released"])
        self.assertTrue(result["unit_mismatches"])

    def test_missing_test_condition_holds_the_draft(self):
        params = full_parameters()
        params[3]["test_condition"] = None
        result = assess_electrical_specification(self._spec(parameters=params))
        self.assertFalse(result["released"])
        self.assertEqual(result["missing_test_conditions"], [params[3]["name"]])

    def test_condition_outside_the_envelope_holds_the_draft(self):
        params = full_parameters()
        params[4]["condition_temperature_c"] = -60.0
        result = assess_electrical_specification(self._spec(parameters=params))
        self.assertFalse(result["released"])
        self.assertTrue(result["out_of_envelope"])

    def test_undefined_interface_holds_the_draft(self):
        interfaces = [i for i in full_interfaces() if i["name"] != "ground-reference"]
        result = assess_electrical_specification(self._spec(interfaces=interfaces))
        self.assertFalse(result["released"])
        self.assertEqual(result["absent_interfaces"], ["ground-reference"])

    def test_rf_port_without_impedance_holds_the_draft(self):
        interfaces = full_interfaces()
        del interfaces[0]["impedance_ohm"]
        result = assess_electrical_specification(self._spec(interfaces=interfaces))
        self.assertFalse(result["released"])
        self.assertEqual(result["rf_ports_without_impedance"], ["rf-input"])

    def test_additional_parameter_does_not_hold_the_draft(self):
        params = full_parameters() + [parameter("third-order-intercept", unit="dBm")]
        result = assess_electrical_specification(self._spec(parameters=params))
        self.assertTrue(result["released"])
        self.assertEqual(result["additional_parameters"], ["third-order-intercept"])

    def test_inverted_supply_envelope_rejected(self):
        with self.assertRaises(ValueError):
            assess_electrical_specification(self._spec(supply_range_v=(5.5, 4.5)))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["interfaces"]
        with self.assertRaises(ValueError):
            assess_electrical_specification(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_electrical_specification(["parameters"])

    def test_several_defects_are_reported_together(self):
        params = [p for p in full_parameters() if p["name"] != "gain-flatness"]
        params[0]["test_condition"] = None
        interfaces = [i for i in full_interfaces() if i["name"] != "dc-bias"]
        result = assess_electrical_specification(
            self._spec(parameters=params, interfaces=interfaces)
        )
        self.assertFalse(result["released"])
        self.assertGreaterEqual(len(result["findings"]), 3)


if __name__ == "__main__":
    unittest.main()
