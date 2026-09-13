"""Contract tests for the clause 5.3.2.1 design-analysis applicability logic."""

import math
import unittest

from e2001_design_analysis_general_requirements_logic import (
    ANALYSIS_ITEMS,
    EQUIPMENT_TYPES,
    VOLTAGE_TOLERANCE_REL,
    assess_design_analysis_coverage,
    assess_equipment_item,
    average_carrier_power_w,
    carrier_case,
    environment_route,
    gap_voltage_v,
    normalize_environment,
    normalize_equipment_type,
    peak_envelope_power_w,
    required_analysis_items,
    screen_equipment,
)


def item(**overrides):
    base = {
        "id": "omux-ch3",
        "equipment_type": "output-multiplexer",
        "environment": "vented-to-vacuum",
        "carrier_powers_w": [120.0],
        "impedance_ohm": 50.0,
        "lowest_threshold_v": 60.0,
        "declared_analyses": ["single-carrier-design-analysis"],
    }
    base.update(overrides)
    return base


class EquipmentTypeTests(unittest.TestCase):
    def test_canonical_key_returned(self):
        self.assertEqual(normalize_equipment_type("Waveguide-Filter"), "waveguide-filter")

    def test_surrounding_whitespace_tolerated(self):
        self.assertEqual(normalize_equipment_type("  rotary-joint "), "rotary-joint")

    def test_unknown_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_equipment_type("solar-wing-hinge")

    def test_empty_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_equipment_type("   ")

    def test_non_string_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_equipment_type(17)

    def test_rf_carrying_flag_present_for_every_type(self):
        for key, spec in EQUIPMENT_TYPES.items():
            self.assertIn("rf_power_carrying", spec, key)

    def test_harness_is_not_rf_power_carrying(self):
        self.assertFalse(EQUIPMENT_TYPES["dc-power-harness"]["rf_power_carrying"])


class EnvironmentTests(unittest.TestCase):
    def test_vacuum_maps_to_multipaction_route(self):
        self.assertEqual(environment_route("vented-to-vacuum"), "multipaction-route")

    def test_sealed_unit_maps_to_gas_discharge_route(self):
        self.assertEqual(
            environment_route("hermetically-sealed-pressurised"), "gas-discharge-route"
        )

    def test_case_folding(self):
        self.assertEqual(normalize_environment("OPEN-TO-VACUUM"), "open-to-vacuum")

    def test_unknown_environment_rejected(self):
        with self.assertRaises(ValueError):
            normalize_environment("cryogenic-bath")

    def test_non_string_environment_rejected(self):
        with self.assertRaises(ValueError):
            normalize_environment(None)


class CarrierTests(unittest.TestCase):
    def test_one_carrier_is_the_single_carrier_case(self):
        self.assertEqual(carrier_case([100.0]), "single-carrier")

    def test_two_carriers_are_the_multicarrier_case(self):
        self.assertEqual(carrier_case([50.0, 50.0]), "multicarrier")

    def test_peak_envelope_is_the_coherent_amplitude_sum(self):
        self.assertAlmostEqual(peak_envelope_power_w([25.0, 25.0]), 100.0)

    def test_peak_envelope_of_four_equal_carriers_scales_as_n_squared(self):
        self.assertAlmostEqual(peak_envelope_power_w([10.0] * 4), 160.0)

    def test_peak_envelope_exceeds_the_average_power(self):
        carriers = [30.0, 20.0, 10.0]
        self.assertGreater(
            peak_envelope_power_w(carriers), average_carrier_power_w(carriers)
        )

    def test_single_carrier_peak_equals_its_power(self):
        self.assertAlmostEqual(peak_envelope_power_w([73.5]), 73.5)

    def test_average_power_is_the_plain_sum(self):
        self.assertAlmostEqual(average_carrier_power_w([30.0, 20.0, 10.0]), 60.0)

    def test_empty_carrier_set_rejected(self):
        with self.assertRaises(ValueError):
            carrier_case([])

    def test_non_sequence_carrier_set_rejected(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w(100.0)

    def test_zero_carrier_power_rejected(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([100.0, 0.0])

    def test_negative_carrier_power_rejected(self):
        with self.assertRaises(ValueError):
            average_carrier_power_w([-5.0])

    def test_boolean_carrier_power_rejected(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([True])


class GapVoltageTests(unittest.TestCase):
    def test_closed_form_voltage(self):
        self.assertAlmostEqual(gap_voltage_v(100.0, 50.0), 100.0)

    def test_magnification_scales_the_voltage(self):
        self.assertAlmostEqual(gap_voltage_v(100.0, 50.0, 2.5), 250.0)

    def test_quadrupling_power_doubles_the_voltage(self):
        self.assertAlmostEqual(gap_voltage_v(400.0, 50.0), 2.0 * gap_voltage_v(100.0, 50.0))

    def test_zero_impedance_rejected(self):
        with self.assertRaises(ValueError):
            gap_voltage_v(100.0, 0.0)

    def test_non_finite_power_rejected(self):
        with self.assertRaises(ValueError):
            gap_voltage_v(float("nan"), 50.0)


class ScreeningTests(unittest.TestCase):
    def test_far_below_threshold_is_screened_out(self):
        self.assertTrue(screen_equipment(20.0, 60.0))

    def test_far_above_threshold_is_not_screened_out(self):
        self.assertFalse(screen_equipment(600.0, 60.0))

    def test_exact_threshold_equality_is_screened_out(self):
        voltage = gap_voltage_v(100.0, 50.0)
        self.assertTrue(screen_equipment(voltage, 100.0))

    def test_representation_error_above_threshold_is_absorbed(self):
        just_over = math.nextafter(100.0, 200.0)
        self.assertGreater(just_over, 100.0)
        self.assertTrue(screen_equipment(just_over, 100.0))

    def test_engineering_limit_is_not_widened(self):
        self.assertFalse(screen_equipment(100.0 * (1.0 + 1e-6), 100.0))
        self.assertLess(VOLTAGE_TOLERANCE_REL, 1e-6)

    def test_non_positive_threshold_rejected(self):
        with self.assertRaises(ValueError):
            screen_equipment(50.0, 0.0)


class RequiredCoverageTests(unittest.TestCase):
    def test_single_carrier_demands_one_item(self):
        self.assertEqual(
            required_analysis_items("single-carrier", True, False),
            ["single-carrier-design-analysis"],
        )

    def test_multicarrier_demands_both_items(self):
        self.assertEqual(
            required_analysis_items("multicarrier", True, False), list(ANALYSIS_ITEMS)
        )

    def test_out_of_scope_demands_nothing(self):
        self.assertEqual(required_analysis_items("multicarrier", False, False), [])

    def test_screened_item_demands_nothing(self):
        self.assertEqual(required_analysis_items("single-carrier", True, True), [])

    def test_unknown_case_rejected(self):
        with self.assertRaises(ValueError):
            required_analysis_items("dual-polarised", True, False)

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            required_analysis_items("single-carrier", "yes", False)


class ItemAssessmentTests(unittest.TestCase):
    def test_compliant_single_carrier_item(self):
        record = assess_equipment_item(item())
        self.assertTrue(record["in_scope"])
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])

    def test_multicarrier_item_missing_the_envelope_analysis(self):
        record = assess_equipment_item(
            item(carrier_powers_w=[60.0, 60.0],
                 declared_analyses=["single-carrier-design-analysis"])
        )
        self.assertEqual(record["missing_analyses"], ["multicarrier-design-analysis"])
        self.assertFalse(record["compliant"])

    def test_multicarrier_peak_envelope_is_reported(self):
        record = assess_equipment_item(item(carrier_powers_w=[25.0, 25.0]))
        self.assertAlmostEqual(record["peak_envelope_power_w"], 100.0)
        self.assertAlmostEqual(record["average_power_w"], 50.0)

    def test_low_power_item_is_screened_out_and_demands_nothing(self):
        record = assess_equipment_item(
            item(carrier_powers_w=[0.01], lowest_threshold_v=60.0, declared_analyses=[])
        )
        self.assertTrue(record["screened_out"])
        self.assertEqual(record["required_analyses"], [])
        self.assertTrue(record["compliant"])

    def test_non_rf_item_is_out_of_scope(self):
        record = assess_equipment_item(
            item(id="harness-1", equipment_type="dc-power-harness", declared_analyses=[])
        )
        self.assertFalse(record["in_scope"])
        self.assertEqual(record["required_analyses"], [])

    def test_sealed_rf_item_is_routed_to_the_gas_discharge_case(self):
        record = assess_equipment_item(
            item(environment="hermetically-sealed-pressurised", declared_analyses=[])
        )
        self.assertEqual(record["route"], "gas-discharge-route")
        self.assertFalse(record["in_scope"])
        self.assertEqual(len(record["findings"]), 1)

    def test_extraneous_declaration_is_flagged(self):
        record = assess_equipment_item(
            item(declared_analyses=["single-carrier-design-analysis",
                                    "multicarrier-design-analysis"])
        )
        self.assertFalse(record["compliant"])
        self.assertIn("does not demand it", record["findings"][0])

    def test_magnification_raises_the_gap_voltage(self):
        plain = assess_equipment_item(item())
        magnified = assess_equipment_item(item(magnification=3.0))
        self.assertAlmostEqual(
            magnified["peak_gap_voltage_v"], 3.0 * plain["peak_gap_voltage_v"]
        )

    def test_missing_key_rejected(self):
        bad = item()
        del bad["impedance_ohm"]
        with self.assertRaises(ValueError):
            assess_equipment_item(bad)

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_item(["omux"])

    def test_blank_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_item(item(id="   "))

    def test_unknown_declared_item_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_item(item(declared_analyses=["corona-design-analysis"]))

    def test_declared_analyses_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_equipment_item(item(declared_analyses="single-carrier-design-analysis"))


class CoverageAggregationTests(unittest.TestCase):
    def test_aggregate_counts(self):
        result = assess_design_analysis_coverage([
            item(),
            item(id="omux-ch4", carrier_powers_w=[60.0, 60.0],
                 declared_analyses=list(ANALYSIS_ITEMS)),
            item(id="harness-1", equipment_type="dc-power-harness", declared_analyses=[]),
        ])
        self.assertEqual(result["in_scope_count"], 2)
        self.assertEqual(result["multicarrier_count"], 1)
        self.assertTrue(result["compliant"])

    def test_findings_are_aggregated_across_items(self):
        result = assess_design_analysis_coverage([
            item(declared_analyses=[]),
            item(id="omux-ch4", carrier_powers_w=[60.0, 60.0], declared_analyses=[]),
        ])
        self.assertEqual(len(result["findings"]), 3)
        self.assertFalse(result["compliant"])

    def test_screened_count_is_reported(self):
        result = assess_design_analysis_coverage([
            item(carrier_powers_w=[0.01], declared_analyses=[]),
            item(id="omux-ch4"),
        ])
        self.assertEqual(result["screened_out_count"], 1)

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_analysis_coverage([item(), item()])

    def test_empty_equipment_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_analysis_coverage([])


if __name__ == "__main__":
    unittest.main()
