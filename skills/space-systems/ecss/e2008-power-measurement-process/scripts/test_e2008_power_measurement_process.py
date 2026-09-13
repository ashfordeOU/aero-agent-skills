"""Contract tests for the clause 5.5.3.4.2 string-measurement process logic."""

import unittest

from e2008_power_measurement_process_logic import (
    DEFAULT_STRING_MEASUREMENT_POLICY,
    EXTRAPOLATION_EXCESSIVE,
    INSTRUMENTATION_INADEQUATE,
    PLANE_SHORT_OF_CONNECTOR,
    PROCESS_CONFORMS,
    assess_power_measurement_process,
    extrapolation_is_credible,
    extrapolation_span_k,
    harness_power_loss_w,
    harness_voltage_drop_v,
    sweep_is_dense_enough,
    sweep_spans_string,
    temperature_corrected_current_a,
    temperature_corrected_power_w,
    temperature_corrected_voltage_v,
    unmeasured_resistance_ohm,
    validate_measurement_plane,
    validate_string_definition,
    validate_string_measurement_policy,
)

HARNESS = {"connector-harness": 0.05, "string-interconnect": 0.02}


def _policy(**overrides):
    policy = dict(DEFAULT_STRING_MEASUREMENT_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "string": {
            "cells_in_series": 24,
            "strings_in_parallel": 1,
            "interface_connector_id": "SA-J1",
        },
        "measurement_plane": "interface-connector",
        "measured": {
            "temperature_c": 28.0,
            "open_circuit_voltage_v": 60.0,
            "short_circuit_current_a": 2.0,
            "maximum_power_w": 96.0,
        },
        "temperature_coefficients": {
            "beta_v_per_k": -0.1,
            "alpha_a_per_k": 0.001,
            "gamma_per_k": -0.004,
        },
        "harness_resistance_ohm": dict(HARNESS),
        "sweep": {"voltage_range_v": 80.0, "current_range_a": 3.0, "points": 250},
    }
    case.update(overrides)
    return case


class PolicyAndDefinitionTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_string_measurement_policy(DEFAULT_STRING_MEASUREMENT_POLICY),
            DEFAULT_STRING_MEASUREMENT_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_string_measurement_policy("reference")

    def test_zero_extrapolation_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_string_measurement_policy(_policy(max_extrapolation_k=0.0))

    def test_single_point_sweep_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_string_measurement_policy(_policy(min_sweep_points=1))

    def test_string_definition_needs_a_named_connector(self):
        with self.assertRaises(ValueError):
            validate_string_definition(
                {
                    "cells_in_series": 24,
                    "strings_in_parallel": 1,
                    "interface_connector_id": "   ",
                }
            )

    def test_fractional_cell_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_string_definition(
                {
                    "cells_in_series": 24.5,
                    "strings_in_parallel": 1,
                    "interface_connector_id": "SA-J1",
                }
            )

    def test_unknown_measurement_plane_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurement_plane("oscilloscope-probe")

    def test_interface_connector_plane_is_recognised(self):
        self.assertEqual(
            validate_measurement_plane("interface-connector"), "interface-connector"
        )


class MeasurementPlaneTests(unittest.TestCase):
    def test_interface_connector_leaves_nothing_unmeasured(self):
        self.assertAlmostEqual(
            unmeasured_resistance_ohm("interface-connector", HARNESS), 0.0, places=12
        )

    def test_bus_bar_plane_leaves_the_connector_harness_out(self):
        self.assertAlmostEqual(
            unmeasured_resistance_ohm("string-bus-bar", HARNESS), 0.05, places=12
        )

    def test_cell_probe_plane_leaves_both_segments_out(self):
        self.assertAlmostEqual(
            unmeasured_resistance_ohm("cell-level-probe", HARNESS), 0.07, places=12
        )

    def test_undeclared_segment_resistance_rejected(self):
        with self.assertRaises(ValueError):
            unmeasured_resistance_ohm("string-bus-bar", {"string-interconnect": 0.02})

    def test_unknown_harness_segment_rejected(self):
        with self.assertRaises(ValueError):
            unmeasured_resistance_ohm("interface-connector", {"slip-ring": 0.01})

    def test_loss_is_the_square_of_the_current_times_resistance(self):
        self.assertAlmostEqual(harness_power_loss_w(2.0, 0.05), 0.2, places=12)

    def test_doubling_the_current_quadruples_the_loss(self):
        self.assertAlmostEqual(
            harness_power_loss_w(4.0, 0.05),
            4.0 * harness_power_loss_w(2.0, 0.05),
            places=12,
        )

    def test_drop_is_the_current_times_resistance(self):
        self.assertAlmostEqual(harness_voltage_drop_v(2.0, 0.05), 0.1, places=12)

    def test_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            harness_power_loss_w(2.0, -0.05)


class TemperatureCorrectionTests(unittest.TestCase):
    def test_warm_measurement_corrects_the_voltage_upward(self):
        self.assertAlmostEqual(
            temperature_corrected_voltage_v(60.0, 45.0, 25.0, -0.1), 62.0, places=9
        )

    def test_cold_measurement_corrects_the_voltage_downward(self):
        self.assertAlmostEqual(
            temperature_corrected_voltage_v(60.0, 5.0, 25.0, -0.1), 58.0, places=9
        )

    def test_measurement_at_reference_needs_no_voltage_correction(self):
        self.assertAlmostEqual(
            temperature_corrected_voltage_v(60.0, 25.0, 25.0, -0.1), 60.0, places=9
        )

    def test_warm_measurement_corrects_the_current_downward(self):
        self.assertAlmostEqual(
            temperature_corrected_current_a(2.0, 45.0, 25.0, 0.001), 1.98, places=9
        )

    def test_warm_measurement_corrects_the_power_upward(self):
        self.assertAlmostEqual(
            temperature_corrected_power_w(96.0, 50.0, 25.0, -0.004), 105.6, places=9
        )

    def test_power_correction_at_reference_is_the_identity(self):
        self.assertAlmostEqual(
            temperature_corrected_power_w(96.0, 25.0, 25.0, -0.004), 96.0, places=9
        )

    def test_unphysical_power_correction_rejected(self):
        with self.assertRaises(ValueError):
            temperature_corrected_power_w(96.0, -250.0, 25.0, -0.004)

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            temperature_corrected_voltage_v(60.0, -300.0, 25.0, -0.1)

    def test_span_is_symmetric_about_the_reference(self):
        self.assertAlmostEqual(
            extrapolation_span_k(35.0, 25.0), extrapolation_span_k(15.0, 25.0),
            places=12,
        )

    def test_span_exactly_at_the_limit_is_credible(self):
        policy = _policy(max_extrapolation_k=10.0)
        self.assertAlmostEqual(
            extrapolation_span_k(35.0, policy["reference_temperature_c"]),
            policy["max_extrapolation_k"],
            places=9,
        )
        self.assertTrue(extrapolation_is_credible(35.0, policy))

    def test_span_beyond_the_limit_is_not_credible(self):
        self.assertFalse(extrapolation_is_credible(60.0, _policy()))


class SweepTests(unittest.TestCase):
    def test_a_sweep_that_reaches_both_ends_spans_the_string(self):
        self.assertTrue(
            sweep_spans_string(
                {"voltage_range_v": 80.0, "current_range_a": 3.0}, 60.0, 2.0
            )
        )

    def test_a_range_exactly_at_the_string_end_spans_it(self):
        self.assertTrue(
            sweep_spans_string(
                {"voltage_range_v": 60.0, "current_range_a": 2.0}, 60.0, 2.0
            )
        )

    def test_a_short_voltage_range_does_not_span_the_string(self):
        self.assertFalse(
            sweep_spans_string(
                {"voltage_range_v": 40.0, "current_range_a": 3.0}, 60.0, 2.0
            )
        )

    def test_a_sweep_at_the_minimum_density_is_dense_enough(self):
        self.assertTrue(sweep_is_dense_enough({"points": 100}, _policy()))

    def test_a_sparse_sweep_is_not_dense_enough(self):
        self.assertFalse(sweep_is_dense_enough({"points": 12}, _policy()))

    def test_zero_sweep_range_rejected(self):
        with self.assertRaises(ValueError):
            sweep_spans_string(
                {"voltage_range_v": 0.0, "current_range_a": 3.0}, 60.0, 2.0
            )


class ProcessAssessmentTests(unittest.TestCase):
    def test_a_connector_plane_measurement_near_reference_conforms(self):
        result = assess_power_measurement_process(_case())
        self.assertEqual(result["verdict"], PROCESS_CONFORMS)
        self.assertTrue(result["conforms"])
        self.assertEqual(result["findings"], [])

    def test_the_corrected_power_is_referred_to_the_reference(self):
        result = assess_power_measurement_process(_case())
        self.assertAlmostEqual(
            result["corrected_maximum_power_w"], 97.152, places=9
        )

    def test_a_bus_bar_plane_is_short_of_the_connector(self):
        result = assess_power_measurement_process(
            _case(measurement_plane="string-bus-bar")
        )
        self.assertEqual(result["verdict"], PLANE_SHORT_OF_CONNECTOR)
        self.assertGreater(result["uncharged_power_loss_w"], 0.0)

    def test_a_short_plane_overstates_the_delivered_power(self):
        result = assess_power_measurement_process(
            _case(measurement_plane="cell-level-probe")
        )
        self.assertGreater(
            result["corrected_maximum_power_w"],
            result["power_at_interface_connector_w"],
        )

    def test_the_connector_plane_charges_nothing_to_the_harness(self):
        result = assess_power_measurement_process(_case())
        self.assertAlmostEqual(
            result["power_at_interface_connector_w"],
            result["corrected_maximum_power_w"],
            places=12,
        )

    def test_a_far_measurement_is_an_excessive_extrapolation(self):
        case = _case()
        case["measured"]["temperature_c"] = 70.0
        result = assess_power_measurement_process(case)
        self.assertEqual(result["verdict"], EXTRAPOLATION_EXCESSIVE)
        self.assertFalse(result["extrapolation_credible"])

    def test_a_sparse_sweep_makes_the_instrumentation_inadequate(self):
        result = assess_power_measurement_process(
            _case(
                sweep={"voltage_range_v": 80.0, "current_range_a": 3.0, "points": 10}
            )
        )
        self.assertEqual(result["verdict"], INSTRUMENTATION_INADEQUATE)

    def test_instrumentation_outranks_a_short_plane(self):
        result = assess_power_measurement_process(
            _case(
                measurement_plane="string-bus-bar",
                sweep={"voltage_range_v": 10.0, "current_range_a": 3.0, "points": 250},
            )
        )
        self.assertEqual(result["verdict"], INSTRUMENTATION_INADEQUATE)
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_the_connector_identifier_is_carried_into_the_record(self):
        result = assess_power_measurement_process(_case())
        self.assertEqual(result["interface_connector_id"], "SA-J1")

    def test_missing_measured_block_rejected(self):
        case = _case()
        del case["measured"]
        with self.assertRaises(ValueError):
            assess_power_measurement_process(case)

    def test_missing_temperature_coefficients_rejected(self):
        case = _case()
        del case["temperature_coefficients"]
        with self.assertRaises(ValueError):
            assess_power_measurement_process(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_power_measurement_process(["string"])

    def test_missing_measurement_plane_rejected(self):
        case = _case()
        del case["measurement_plane"]
        with self.assertRaises(ValueError):
            assess_power_measurement_process(case)


if __name__ == "__main__":
    unittest.main()
