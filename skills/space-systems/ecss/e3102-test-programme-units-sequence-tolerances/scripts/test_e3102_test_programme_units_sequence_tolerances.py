"""Contract test for the test-programme definition leaf (stdlib unittest)."""

import unittest

from e3102_test_programme_units_sequence_tolerances_logic import (
    ACCURACY_TO_TOLERANCE_RATIO,
    EQUIPMENT_TYPES,
    MODEL_PHILOSOPHIES,
    REQUIRED_STEPS,
    assess_applied_tolerance,
    assess_measurement_accuracy,
    assess_sequence,
    assess_test_programme,
    assess_unit_count,
    minimum_unit_count,
    resolve_limit,
    tolerance_band,
    validate_equipment_type,
    validate_model_philosophy,
)

HP_FLOW = list(REQUIRED_STEPS["heat-pipe"])
CDL_FLOW = list(REQUIRED_STEPS["capillary-driven-loop"])


def good_parameters():
    return [
        {
            "quantity": "temperature_k", "nominal": 300.0,
            "tolerance_kind": "absolute", "tolerance_value": 2.0,
            "accuracy_kind": "absolute", "accuracy_value": 0.5,
        },
        {
            "quantity": "heat_load_w", "nominal": 100.0,
            "tolerance_kind": "relative", "tolerance_value": 0.02,
            "accuracy_kind": "relative", "accuracy_value": 0.005,
        },
        {
            "quantity": "pressure_pa", "nominal": 1.0e6,
            "tolerance_kind": "relative", "tolerance_value": 0.02,
            "accuracy_kind": "relative", "accuracy_value": 0.005,
        },
    ]


def good_spec(**overrides):
    spec = {
        "equipment_type": "capillary-driven-loop",
        "model_philosophy": "qualification-model",
        "declared_units": 2,
        "sequence": list(CDL_FLOW),
        "parameters": good_parameters(),
    }
    spec.update(overrides)
    return spec


class TestValidators(unittest.TestCase):
    def test_equipment_type_is_normalised(self):
        self.assertEqual(validate_equipment_type("  Heat-Pipe "), "heat-pipe")

    def test_unknown_equipment_type_raises(self):
        with self.assertRaises(ValueError):
            validate_equipment_type("thermal-strap")

    def test_empty_equipment_type_raises(self):
        with self.assertRaises(ValueError):
            validate_equipment_type("")

    def test_model_philosophy_is_normalised(self):
        self.assertEqual(
            validate_model_philosophy("Protoflight-Model"), "protoflight-model"
        )

    def test_unknown_model_philosophy_raises(self):
        with self.assertRaises(ValueError):
            validate_model_philosophy("engineering-model")


class TestUnitCount(unittest.TestCase):
    def test_every_type_and_philosophy_has_a_minimum(self):
        for equipment in EQUIPMENT_TYPES:
            for philosophy in MODEL_PHILOSOPHIES:
                self.assertGreaterEqual(minimum_unit_count(equipment, philosophy), 1)

    def test_qualification_needs_more_units_than_protoflight(self):
        for equipment in EQUIPMENT_TYPES:
            self.assertGreater(
                minimum_unit_count(equipment, "qualification-model"),
                minimum_unit_count(equipment, "protoflight-model"),
            )

    def test_declared_units_meeting_the_minimum_pass(self):
        result = assess_unit_count(3, "heat-pipe", "qualification-model")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["shortfall"], 0)

    def test_short_unit_count_reports_the_shortfall(self):
        result = assess_unit_count(1, "heat-pipe", "qualification-model")
        self.assertFalse(result["compliant"])
        self.assertEqual(result["shortfall"], 2)

    def test_override_replaces_the_tabulated_minimum(self):
        result = assess_unit_count(
            4, "heat-pipe", "protoflight-model",
            {("heat-pipe", "protoflight-model"): 5},
        )
        self.assertEqual(result["required_units"], 5)
        self.assertFalse(result["compliant"])

    def test_non_integer_unit_count_raises(self):
        with self.assertRaises(ValueError):
            assess_unit_count(2.5, "heat-pipe", "qualification-model")

    def test_boolean_unit_count_raises(self):
        with self.assertRaises(ValueError):
            assess_unit_count(True, "heat-pipe", "qualification-model")

    def test_zero_override_raises(self):
        with self.assertRaises(ValueError):
            minimum_unit_count("heat-pipe", "protoflight-model",
                               {("heat-pipe", "protoflight-model"): 0})


class TestSequence(unittest.TestCase):
    def test_reference_heat_pipe_flow_is_compliant(self):
        result = assess_sequence("heat-pipe", HP_FLOW)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_reference_capillary_loop_flow_is_compliant(self):
        self.assertTrue(assess_sequence("capillary-driven-loop", CDL_FLOW)["compliant"])

    def test_loop_flow_adds_start_up_and_regulation(self):
        self.assertNotIn("start-up", REQUIRED_STEPS["heat-pipe"])
        self.assertIn("start-up", REQUIRED_STEPS["capillary-driven-loop"])
        self.assertIn("regulation", REQUIRED_STEPS["capillary-driven-loop"])

    def test_heat_pipe_flow_rejected_for_a_capillary_loop(self):
        result = assess_sequence("capillary-driven-loop", HP_FLOW)
        self.assertFalse(result["compliant"])
        self.assertIn("start-up", result["missing_steps"])

    def test_burst_before_pressure_cycle_is_a_precedence_violation(self):
        flow = list(HP_FLOW)
        flow[flow.index("burst")], flow[flow.index("pressure-cycle")] = (
            "pressure-cycle", "burst",
        )
        result = assess_sequence("heat-pipe", flow)
        self.assertFalse(result["compliant"])
        self.assertIn(("pressure-cycle", "burst"), result["precedence_violations"])

    def test_performance_before_proof_pressure_is_a_violation(self):
        flow = ["thermal-performance", "proof-pressure", "leak", "thermal-cycling",
                "vibration", "pressure-cycle", "burst"]
        result = assess_sequence("heat-pipe", flow)
        self.assertFalse(result["compliant"])
        self.assertIn(("leak", "thermal-performance"), result["precedence_violations"])

    def test_unknown_step_is_reported(self):
        result = assess_sequence("heat-pipe", HP_FLOW + ["taste-test"])
        self.assertFalse(result["compliant"])
        self.assertEqual(result["unknown_steps"], ["taste-test"])

    def test_repeated_step_is_reported(self):
        result = assess_sequence("heat-pipe", HP_FLOW + ["leak"])
        self.assertFalse(result["compliant"])
        self.assertEqual(result["repeated_steps"], ["leak"])

    def test_empty_sequence_raises(self):
        with self.assertRaises(ValueError):
            assess_sequence("heat-pipe", [])

    def test_non_string_step_raises(self):
        with self.assertRaises(ValueError):
            assess_sequence("heat-pipe", ["proof-pressure", 7])


class TestTolerances(unittest.TestCase):
    def test_absolute_band_is_symmetric_about_the_nominal(self):
        low, high = tolerance_band(300.0, "absolute", 2.0)
        self.assertAlmostEqual(low, 298.0, places=9)
        self.assertAlmostEqual(high, 302.0, places=9)

    def test_relative_band_scales_with_the_nominal(self):
        low, high = tolerance_band(1.0e6, "relative", 0.02)
        self.assertAlmostEqual(low, 980000.0, places=9)
        self.assertAlmostEqual(high, 1020000.0, places=9)

    def test_unknown_tolerance_kind_raises(self):
        with self.assertRaises(ValueError):
            tolerance_band(300.0, "percentish", 2.0)

    def test_negative_tolerance_value_raises(self):
        with self.assertRaises(ValueError):
            tolerance_band(300.0, "absolute", -1.0)

    def test_tolerance_exactly_at_the_allowable_passes(self):
        result = assess_applied_tolerance("temperature_k", 300.0, "absolute", 2.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["applied_half_width"], 2.0, places=9)
        self.assertAlmostEqual(result["allowable_half_width"], 2.0, places=9)

    def test_wider_tolerance_than_allowable_fails(self):
        result = assess_applied_tolerance("temperature_k", 300.0, "absolute", 5.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])

    def test_relative_tolerance_is_converted_before_grading(self):
        result = assess_applied_tolerance("pressure_pa", 1.0e6, "relative", 0.01)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["applied_half_width"], 10000.0, places=9)

    def test_untabulated_quantity_raises(self):
        with self.assertRaises(ValueError):
            assess_applied_tolerance("wick_porosity", 0.5, "relative", 0.01)

    def test_resolve_limit_normalises_the_quantity_name(self):
        name, limit = resolve_limit("  Temperature_K ",
                                    {"temperature_k": ("absolute", 2.0)}, "tolerance")
        self.assertEqual(name, "temperature_k")
        self.assertEqual(limit, ("absolute", 2.0))


class TestMeasurementAccuracy(unittest.TestCase):
    def test_accuracy_exactly_at_the_requirement_passes(self):
        result = assess_measurement_accuracy("temperature_k", 300.0, "absolute", 0.5)
        self.assertTrue(result["meets_requirement"])
        self.assertAlmostEqual(result["declared_half_width"], 0.5, places=9)

    def test_coarser_accuracy_than_required_fails(self):
        result = assess_measurement_accuracy("temperature_k", 300.0, "absolute", 1.5)
        self.assertFalse(result["meets_requirement"])
        self.assertFalse(result["compliant"])

    def test_instrument_too_coarse_to_police_the_band_is_reported(self):
        result = assess_measurement_accuracy(
            "temperature_k", 300.0, "absolute", 0.5, applied_half_width=0.9
        )
        self.assertTrue(result["meets_requirement"])
        self.assertFalse(result["resolves_band"])
        self.assertFalse(result["compliant"])

    def test_band_resolution_boundary_is_treated_as_met(self):
        result = assess_measurement_accuracy(
            "temperature_k", 300.0, "absolute", 0.5,
            applied_half_width=0.5 * ACCURACY_TO_TOLERANCE_RATIO,
        )
        self.assertTrue(result["resolves_band"])

    def test_zero_applied_band_raises(self):
        with self.assertRaises(ValueError):
            assess_measurement_accuracy("temperature_k", 300.0, "absolute", 0.5,
                                        applied_half_width=0.0)


class TestWholeProgramme(unittest.TestCase):
    def test_reference_programme_is_compliant(self):
        report = assess_test_programme(good_spec())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])

    def test_short_unit_count_fails_the_programme(self):
        report = assess_test_programme(good_spec(declared_units=1))
        self.assertFalse(report["compliant"])
        self.assertTrue(any(f.startswith("units:") for f in report["findings"]))

    def test_wrong_flow_fails_the_programme(self):
        report = assess_test_programme(good_spec(sequence=list(HP_FLOW)))
        self.assertFalse(report["compliant"])
        self.assertTrue(any(f.startswith("sequence:") for f in report["findings"]))

    def test_loose_tolerance_fails_the_programme(self):
        params = good_parameters()
        params[0]["tolerance_value"] = 6.0
        report = assess_test_programme(good_spec(parameters=params))
        self.assertFalse(report["compliant"])
        self.assertTrue(any(f.startswith("tolerance:") for f in report["findings"]))

    def test_coarse_instrument_fails_the_programme(self):
        params = good_parameters()
        params[0]["accuracy_value"] = 1.2
        report = assess_test_programme(good_spec(parameters=params))
        self.assertFalse(report["compliant"])
        self.assertTrue(any(f.startswith("accuracy:") for f in report["findings"]))

    def test_repeated_quantity_raises(self):
        params = good_parameters()
        params.append(dict(params[0]))
        with self.assertRaises(ValueError):
            assess_test_programme(good_spec(parameters=params))

    def test_missing_parameter_key_raises(self):
        params = good_parameters()
        del params[1]["accuracy_kind"]
        with self.assertRaises(ValueError):
            assess_test_programme(good_spec(parameters=params))

    def test_empty_parameter_list_raises(self):
        with self.assertRaises(ValueError):
            assess_test_programme(good_spec(parameters=[]))

    def test_missing_spec_key_raises(self):
        spec = good_spec()
        del spec["sequence"]
        with self.assertRaises(ValueError):
            assess_test_programme(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_test_programme("capillary-driven-loop")


if __name__ == "__main__":
    unittest.main()
