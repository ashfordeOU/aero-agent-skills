"""Gate 3 contract test for the ECSS-E-ST-20C 5.5.3 array power leaf.

stdlib unittest, offline, deterministic. Run:
    python3 test_e20_solar_array_power_computation.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_solar_array_power_computation_logic as logic  # noqa: E402


def cell(**overrides):
    record = {
        "cell_id": "3J-A17",
        "isc_a": 0.500,
        "voc_v": 2.700,
        "imp_a": 0.480,
        "vmp_v": 2.350,
        "provenance": "assembly-measured",
    }
    record.update(overrides)
    return record


def section(**overrides):
    entry = {
        "section_id": "wing-1-section-A",
        "measurement": cell(),
        "series_count": 20,
        "parallel_count": 10,
        "temperature_c": 28.0,
        "solar_distance_au": 1.0,
        "sun_incidence_deg": 0.0,
        "fluence_1mev_e_cm2": 0.0,
    }
    entry.update(overrides)
    return entry


class TestProvenance(unittest.TestCase):
    def test_assembly_measurement_keeps_its_category(self):
        self.assertEqual(
            logic.categorize_provenance("assembly-measured"), "assembly-measured"
        )

    def test_source_token_is_case_insensitive(self):
        self.assertEqual(
            logic.categorize_provenance("  Coupon-Measured "), "coupon-measured"
        )

    def test_datasheet_source_is_uncategorized(self):
        self.assertEqual(
            logic.categorize_provenance("catalogue-datasheet"),
            logic.UNCATEGORIZED_PROVENANCE,
        )

    def test_heritage_source_is_uncategorized(self):
        self.assertEqual(
            logic.categorize_provenance("heritage-assumption"),
            logic.UNCATEGORIZED_PROVENANCE,
        )

    def test_unknown_source_is_an_input_error(self):
        with self.assertRaises(ValueError):
            logic.categorize_provenance("guessed-by-the-intern")

    def test_empty_source_is_an_input_error(self):
        with self.assertRaises(ValueError):
            logic.categorize_provenance("   ")

    def test_weights_are_ordered_by_directness(self):
        self.assertGreater(
            logic.provenance_weight("assembly-measured"),
            logic.provenance_weight("coupon-measured"),
        )
        self.assertGreater(
            logic.provenance_weight("coupon-measured"),
            logic.provenance_weight("lot-sample-measured"),
        )

    def test_untraceable_category_has_no_weight(self):
        with self.assertRaises(ValueError):
            logic.provenance_weight(logic.UNCATEGORIZED_PROVENANCE)

    def test_unknown_category_has_no_weight(self):
        with self.assertRaises(ValueError):
            logic.provenance_weight("measured-somehow")


class TestMeasurementValidation(unittest.TestCase):
    def test_fill_factor_matches_hand_calculation(self):
        self.assertAlmostEqual(logic.fill_factor(cell()), 0.8355555556, places=9)

    def test_fill_factor_needs_positive_reference_points(self):
        with self.assertRaises(ValueError):
            logic.fill_factor(cell(isc_a=0.0))

    def test_valid_record_is_normalised(self):
        record = logic.validate_cell_measurement(cell())
        self.assertEqual(record["provenance"], "assembly-measured")
        self.assertAlmostEqual(record["fill_factor"], 0.8355555556, places=9)

    def test_rejects_non_mapping(self):
        with self.assertRaises(ValueError):
            logic.validate_cell_measurement([0.5, 2.7])

    def test_rejects_missing_cell_id(self):
        record = cell()
        del record["cell_id"]
        with self.assertRaises(ValueError):
            logic.validate_cell_measurement(record)

    def test_rejects_maximum_power_current_above_short_circuit(self):
        with self.assertRaises(ValueError):
            logic.validate_cell_measurement(cell(imp_a=0.520))

    def test_rejects_maximum_power_voltage_at_open_circuit(self):
        with self.assertRaises(ValueError):
            logic.validate_cell_measurement(cell(vmp_v=2.700))

    def test_rejects_non_positive_short_circuit_current(self):
        with self.assertRaises(ValueError):
            logic.validate_cell_measurement(cell(isc_a=-0.1, imp_a=-0.2))

    def test_rejects_implausible_fill_factor(self):
        with self.assertRaises(ValueError):
            logic.validate_cell_measurement(cell(imp_a=0.200, vmp_v=1.000))

    def test_rejects_untraceable_record_only_at_prediction_time(self):
        record = logic.validate_cell_measurement(cell(provenance="analytical-estimate"))
        self.assertEqual(record["provenance"], logic.UNCATEGORIZED_PROVENANCE)


class TestOperatingPointCorrection(unittest.TestCase):
    def test_reference_condition_returns_the_measured_point(self):
        out = logic.correct_to_operating_point(cell(), 28.0, 1.0, 0.0)
        self.assertAlmostEqual(out["imp_a"], 0.480, places=9)
        self.assertAlmostEqual(out["vmp_v"], 2.350, places=9)
        self.assertAlmostEqual(out["pmp_w"], 1.128, places=9)

    def test_incidence_angle_scales_current_by_cosine(self):
        out = logic.correct_to_operating_point(cell(), 28.0, 1.0, 60.0)
        self.assertAlmostEqual(out["imp_a"], 0.240, places=9)
        self.assertAlmostEqual(out["vmp_v"], 2.350, places=9)

    def test_solar_distance_scales_current_by_inverse_square(self):
        out = logic.correct_to_operating_point(cell(), 28.0, 2.0, 0.0)
        self.assertAlmostEqual(out["imp_a"], 0.120, places=9)
        self.assertAlmostEqual(out["intensity_ratio"], 0.25, places=9)

    def test_temperature_raises_current_and_drops_voltage(self):
        out = logic.correct_to_operating_point(cell(), 78.0, 1.0, 0.0)
        self.assertAlmostEqual(out["imp_a"], 0.49104, places=9)
        self.assertAlmostEqual(out["vmp_v"], 2.09150, places=9)

    def test_rejects_temperature_below_absolute_zero(self):
        with self.assertRaises(ValueError):
            logic.correct_to_operating_point(cell(), -300.0, 1.0, 0.0)

    def test_rejects_non_positive_solar_distance(self):
        with self.assertRaises(ValueError):
            logic.correct_to_operating_point(cell(), 28.0, 0.0, 0.0)

    def test_rejects_incidence_at_ninety_degrees(self):
        with self.assertRaises(ValueError):
            logic.correct_to_operating_point(cell(), 28.0, 1.0, 90.0)

    def test_rejects_a_positive_voltage_temperature_coefficient(self):
        with self.assertRaises(ValueError):
            logic.correct_to_operating_point(
                cell(), 28.0, 1.0, 0.0, voltage_temp_coeff_per_c=0.004
            )

    def test_rejects_a_negative_current_temperature_coefficient(self):
        with self.assertRaises(ValueError):
            logic.correct_to_operating_point(
                cell(), 28.0, 1.0, 0.0, current_temp_coeff_per_c=-0.001
            )

    def test_rejects_an_operating_point_outside_the_model(self):
        with self.assertRaises(ValueError):
            logic.correct_to_operating_point(
                cell(), 700.0, 1.0, 0.0, voltage_temp_coeff_per_c=-0.01
            )


class TestRetention(unittest.TestCase):
    def test_zero_fluence_leaves_only_optical_losses(self):
        self.assertAlmostEqual(logic.retention_factor(0.0), 0.9506, places=9)

    def test_one_decade_of_fluence_matches_hand_calculation(self):
        self.assertAlmostEqual(logic.retention_factor(9.0e13), 0.836528, places=9)

    def test_retention_decreases_with_fluence(self):
        self.assertLess(logic.retention_factor(1.0e15), logic.retention_factor(1.0e14))

    def test_rejects_negative_fluence(self):
        with self.assertRaises(ValueError):
            logic.retention_factor(-1.0)

    def test_rejects_ultraviolet_loss_at_one(self):
        with self.assertRaises(ValueError):
            logic.retention_factor(0.0, ultraviolet_loss=1.0)

    def test_rejects_non_positive_reference_fluence(self):
        with self.assertRaises(ValueError):
            logic.retention_factor(1.0e13, reference_fluence=0.0)

    def test_rejects_a_fluence_outside_the_logarithmic_model(self):
        with self.assertRaises(ValueError):
            logic.retention_factor(1.0e25)


class TestSectionOutput(unittest.TestCase):
    def setUp(self):
        self.corrected = {"imp_a": 0.480, "vmp_v": 2.350}

    def test_section_power_matches_hand_calculation(self):
        out = logic.section_output(self.corrected, 20, 10, 1.0)
        self.assertAlmostEqual(out["string_voltage_v"], 46.25, places=9)
        self.assertAlmostEqual(out["string_current_a"], 4.65696, places=9)
        self.assertAlmostEqual(out["power_w"], 212.153634, places=6)

    def test_blocking_diode_is_a_voltage_not_a_power_loss(self):
        with_diode = logic.section_output(self.corrected, 20, 10, 1.0)
        without = logic.section_output(
            self.corrected, 20, 10, 1.0, losses={"blocking_diode_v": 0.0}
        )
        self.assertAlmostEqual(without["string_voltage_v"], 47.0, places=9)
        self.assertGreater(without["power_w"], with_diode["power_w"])

    def test_rejects_a_diode_drop_that_exceeds_the_string(self):
        with self.assertRaises(ValueError):
            logic.section_output({"imp_a": 0.48, "vmp_v": 0.50}, 1, 10, 1.0)

    def test_rejects_non_integer_series_count(self):
        with self.assertRaises(ValueError):
            logic.section_output(self.corrected, 20.5, 10, 1.0)

    def test_rejects_zero_parallel_count(self):
        with self.assertRaises(ValueError):
            logic.section_output(self.corrected, 20, 0, 1.0)

    def test_rejects_retention_above_one(self):
        with self.assertRaises(ValueError):
            logic.section_output(self.corrected, 20, 10, 1.2)

    def test_rejects_unknown_loss_key(self):
        with self.assertRaises(ValueError):
            logic.section_output(self.corrected, 20, 10, 1.0, losses={"shadow": 0.1})

    def test_rejects_a_loss_fraction_at_one(self):
        with self.assertRaises(ValueError):
            logic.section_output(
                self.corrected, 20, 10, 1.0, losses={"string_mismatch": 1.0}
            )


class TestPredictArrayOutput(unittest.TestCase):
    def test_single_measured_section_matches_hand_calculation(self):
        result = logic.predict_array_output([section()], 180.0)
        self.assertAlmostEqual(result["predicted_power_w"], 201.6732445, places=4)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_margin_shortfall_is_a_finding(self):
        result = logic.predict_array_output([section()], 400.0)
        self.assertFalse(result["compliant"])
        self.assertLess(result["margin"], 0.0)

    def test_untraceable_section_is_excluded_and_flagged(self):
        entry = section(measurement=cell(provenance="catalogue-datasheet"))
        result = logic.predict_array_output([entry], 180.0)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["sections"][0]["admissible"])
        self.assertAlmostEqual(result["sections"][0]["predicted_power_w"], 0.0, places=9)
        self.assertTrue(any("untraceable" in f for f in result["findings"]))

    def test_lower_confidence_provenance_lowers_the_prediction(self):
        direct = logic.predict_array_output([section()], 180.0)
        indirect = logic.predict_array_output(
            [section(measurement=cell(provenance="lot-sample-measured"))], 180.0
        )
        self.assertLess(
            indirect["predicted_power_w"], direct["predicted_power_w"]
        )

    def test_two_sections_sum(self):
        first = section(section_id="wing-1")
        second = section(section_id="wing-2")
        one = logic.predict_array_output([first], 180.0)
        two = logic.predict_array_output([first, second], 180.0)
        self.assertAlmostEqual(
            two["predicted_power_w"], 2.0 * one["predicted_power_w"], places=6
        )

    def test_rejects_empty_section_list(self):
        with self.assertRaises(ValueError):
            logic.predict_array_output([], 180.0)

    def test_rejects_non_positive_demand(self):
        with self.assertRaises(ValueError):
            logic.predict_array_output([section()], 0.0)

    def test_rejects_negative_required_margin(self):
        with self.assertRaises(ValueError):
            logic.predict_array_output([section()], 180.0, required_margin=-0.1)

    def test_rejects_section_without_an_identifier(self):
        entry = section()
        del entry["section_id"]
        with self.assertRaises(ValueError):
            logic.predict_array_output([entry], 180.0)

    def test_prediction_is_deterministic_across_runs(self):
        first = logic.predict_array_output([section()], 180.0)
        second = logic.predict_array_output([section()], 180.0)
        self.assertAlmostEqual(
            first["predicted_power_w"], second["predicted_power_w"], places=12
        )


if __name__ == "__main__":
    unittest.main()
