"""Contract tests for the clause 6.2.2.5 Class 3 derating logic."""

import unittest

from q60_class_3_component_derating_rules_logic import (
    DEFAULT_CLASS_3_MARGINS,
    DERATING_EXCEEDED,
    DERATING_INDETERMINATE,
    DERATING_SATISFIED,
    ELECTRICAL_STRESSES,
    ON_MARGIN,
    OVER_MARGIN,
    PART_CATEGORIES,
    RATING_SOURCE_FACTORS,
    WITHIN_MARGIN,
    allowable_applied_stress,
    applied_stress_with_uncertainty,
    assess_equipment_derating,
    assess_part,
    class_3_margin,
    grade_case_temperature,
    grade_stress,
    rating_source_factor,
    temperature_derated_rating,
    validate_margin_table,
)


def _rating(**overrides):
    rating = {
        "rated_value": 100.0,
        "reference_temperature_c": 25.0,
        "zero_rating_temperature_c": 125.0,
        "source": "guaranteed-limit",
    }
    rating.update(overrides)
    return rating


def _part(**overrides):
    part = {
        "part_reference": "R101",
        "category": "resistor",
        "quantity": 4,
        "case_temperature_c": 25.0,
        "rated_max_case_temperature_c": 125.0,
        "stresses": {
            "voltage": {"nominal": 20.0, "rating": _rating(rated_value=100.0)},
            "power": {
                "nominal": 0.10,
                "measurement_uncertainty_fraction": 0.05,
                "rating": _rating(rated_value=0.50),
            },
        },
    }
    part.update(overrides)
    return part


def _equipment(**overrides):
    equipment = {
        "equipment_name": "Class 3 payload interface board",
        "parts": [
            _part(),
            _part(
                part_reference="U201",
                category="integrated-circuit",
                quantity=1,
                case_temperature_c=60.0,
                rated_max_case_temperature_c=105.0,
                stresses={
                    "voltage": {
                        "nominal": 3.3,
                        "rating": _rating(
                            rated_value=12.0, source="datasheet-typical"
                        ),
                    }
                },
            ),
        ],
    }
    equipment.update(overrides)
    return equipment


class MarginTableTests(unittest.TestCase):
    def test_default_table_validates(self):
        self.assertIs(validate_margin_table(DEFAULT_CLASS_3_MARGINS),
                      DEFAULT_CLASS_3_MARGINS)

    def test_every_category_carries_every_stress(self):
        for category in PART_CATEGORIES:
            for stress in ELECTRICAL_STRESSES:
                self.assertGreater(class_3_margin(category, stress), 0.0)

    def test_missing_category_rejected(self):
        table = {k: v for k, v in DEFAULT_CLASS_3_MARGINS.items() if k != "capacitor"}
        with self.assertRaises(ValueError):
            validate_margin_table(table)

    def test_missing_stress_rejected(self):
        table = {k: dict(v) for k, v in DEFAULT_CLASS_3_MARGINS.items()}
        del table["resistor"]["power"]
        with self.assertRaises(ValueError):
            validate_margin_table(table)

    def test_margin_above_unity_rejected(self):
        table = {k: dict(v) for k, v in DEFAULT_CLASS_3_MARGINS.items()}
        table["resistor"]["power"] = 1.4
        with self.assertRaises(ValueError):
            validate_margin_table(table)

    def test_missing_case_step_down_rejected(self):
        table = {k: dict(v) for k, v in DEFAULT_CLASS_3_MARGINS.items()}
        del table["relay-and-switch"]["case_step_down_c"]
        with self.assertRaises(ValueError):
            validate_margin_table(table)

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            class_3_margin("crystal-oscillator", "voltage")

    def test_unknown_stress_rejected(self):
        with self.assertRaises(ValueError):
            class_3_margin("resistor", "frequency")


class RatingSourceTests(unittest.TestCase):
    def test_guaranteed_limit_is_undiscounted(self):
        self.assertAlmostEqual(rating_source_factor("guaranteed-limit"), 1.0, places=9)

    def test_typical_column_is_discounted(self):
        self.assertLess(rating_source_factor("datasheet-typical"), 1.0)

    def test_vendor_estimate_is_the_deepest_discount(self):
        self.assertLess(
            rating_source_factor("vendor-estimate"),
            rating_source_factor("datasheet-typical"),
        )

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            rating_source_factor("rumour")

    def test_every_factor_is_a_usable_fraction(self):
        for factor in RATING_SOURCE_FACTORS.values():
            self.assertGreater(factor, 0.0)
            self.assertLessEqual(factor, 1.0)


class TemperatureDeratingTests(unittest.TestCase):
    def test_below_reference_keeps_the_full_rating(self):
        self.assertAlmostEqual(
            temperature_derated_rating(100.0, 25.0, 125.0, -10.0), 100.0, places=9
        )

    def test_exactly_at_reference_keeps_the_full_rating(self):
        self.assertAlmostEqual(
            temperature_derated_rating(100.0, 25.0, 125.0, 25.0), 100.0, places=9
        )

    def test_midpoint_leaves_half_the_rating(self):
        self.assertAlmostEqual(
            temperature_derated_rating(100.0, 25.0, 125.0, 75.0), 50.0, places=9
        )

    def test_at_the_zero_point_nothing_is_left(self):
        self.assertAlmostEqual(
            temperature_derated_rating(100.0, 25.0, 125.0, 125.0), 0.0, places=9
        )

    def test_above_the_zero_point_nothing_is_left(self):
        self.assertAlmostEqual(
            temperature_derated_rating(100.0, 25.0, 125.0, 180.0), 0.0, places=9
        )

    def test_inverted_derating_line_rejected(self):
        with self.assertRaises(ValueError):
            temperature_derated_rating(100.0, 125.0, 25.0, 50.0)

    def test_equal_reference_and_zero_point_rejected(self):
        with self.assertRaises(ValueError):
            temperature_derated_rating(100.0, 85.0, 85.0, 50.0)

    def test_non_positive_rating_rejected(self):
        with self.assertRaises(ValueError):
            temperature_derated_rating(0.0, 25.0, 125.0, 50.0)

    def test_sub_absolute_zero_case_rejected(self):
        with self.assertRaises(ValueError):
            temperature_derated_rating(100.0, 25.0, 125.0, -300.0)

    def test_boolean_case_temperature_rejected(self):
        with self.assertRaises(ValueError):
            temperature_derated_rating(100.0, 25.0, 125.0, True)


class AppliedStressTests(unittest.TestCase):
    def test_zero_uncertainty_leaves_the_nominal(self):
        self.assertAlmostEqual(applied_stress_with_uncertainty(12.0), 12.0, places=9)

    def test_uncertainty_opens_the_nominal_out(self):
        self.assertAlmostEqual(
            applied_stress_with_uncertainty(12.0, 0.25), 15.0, places=9
        )

    def test_negative_nominal_rejected(self):
        with self.assertRaises(ValueError):
            applied_stress_with_uncertainty(-1.0)

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            applied_stress_with_uncertainty(12.0, -0.05)

    def test_uncertainty_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            applied_stress_with_uncertainty(12.0, 1.5)


class AllowableTests(unittest.TestCase):
    def test_all_three_corrections_multiply(self):
        record = allowable_applied_stress(
            "resistor", "power", _rating(rated_value=1.0), 75.0
        )
        self.assertAlmostEqual(record["temperature_derated_rating"], 0.5, places=9)
        self.assertAlmostEqual(record["allowable"], 0.5 * 1.0 * 0.40, places=9)

    def test_source_discount_lands_on_the_corrected_rating(self):
        record = allowable_applied_stress(
            "resistor",
            "power",
            _rating(rated_value=1.0, source="datasheet-typical"),
            75.0,
        )
        self.assertAlmostEqual(record["allowable"], 0.5 * 0.80 * 0.40, places=9)

    def test_margin_is_never_applied_to_the_printed_number(self):
        record = allowable_applied_stress(
            "resistor", "power", _rating(rated_value=1.0), 75.0
        )
        self.assertLess(record["allowable"], record["printed_rating"] * 0.40)

    def test_rating_block_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            allowable_applied_stress("resistor", "power", [1.0, 25.0, 125.0], 50.0)

    def test_rating_block_missing_key_rejected(self):
        rating = _rating()
        del rating["zero_rating_temperature_c"]
        with self.assertRaises(ValueError):
            allowable_applied_stress("resistor", "power", rating, 50.0)

    def test_source_defaults_to_guaranteed_limit(self):
        rating = _rating()
        del rating["source"]
        record = allowable_applied_stress("resistor", "power", rating, 25.0)
        self.assertEqual(record["rating_source"], "guaranteed-limit")


class StressGradingTests(unittest.TestCase):
    def test_stress_exactly_on_its_allowable_is_on_margin(self):
        allowable = 100.0 * 1.0 * 0.50
        record = grade_stress(
            "resistor", "voltage", {"nominal": allowable, "rating": _rating()}, 25.0
        )
        self.assertEqual(record["verdict"], ON_MARGIN)
        self.assertTrue(record["compliant"])
        self.assertAlmostEqual(record["utilisation"], 1.0, places=9)

    def test_stress_below_its_allowable_is_within_margin(self):
        record = grade_stress(
            "resistor", "voltage", {"nominal": 10.0, "rating": _rating()}, 25.0
        )
        self.assertEqual(record["verdict"], WITHIN_MARGIN)

    def test_stress_above_its_allowable_is_over_margin(self):
        record = grade_stress(
            "resistor", "voltage", {"nominal": 90.0, "rating": _rating()}, 25.0
        )
        self.assertEqual(record["verdict"], OVER_MARGIN)
        self.assertFalse(record["compliant"])

    def test_a_hot_part_loses_its_headroom(self):
        cool = grade_stress(
            "resistor", "voltage", {"nominal": 30.0, "rating": _rating()}, 25.0
        )
        hot = grade_stress(
            "resistor", "voltage", {"nominal": 30.0, "rating": _rating()}, 100.0
        )
        self.assertGreater(cool["headroom"], hot["headroom"])

    def test_part_at_its_zero_rating_point_has_no_allowable(self):
        record = grade_stress(
            "resistor", "voltage", {"nominal": 1.0, "rating": _rating()}, 125.0
        )
        self.assertEqual(record["verdict"], OVER_MARGIN)
        self.assertIsNone(record["utilisation"])

    def test_stress_entry_missing_nominal_rejected(self):
        with self.assertRaises(ValueError):
            grade_stress("resistor", "voltage", {"rating": _rating()}, 25.0)

    def test_stress_entry_missing_rating_rejected(self):
        with self.assertRaises(ValueError):
            grade_stress("resistor", "voltage", {"nominal": 5.0}, 25.0)

    def test_non_mapping_stress_entry_rejected(self):
        with self.assertRaises(ValueError):
            grade_stress("resistor", "voltage", 5.0, 25.0)


class CaseTemperatureTests(unittest.TestCase):
    def test_case_exactly_on_the_ceiling_is_on_margin(self):
        record = grade_case_temperature(
            "resistor",
            {"case_temperature_c": 95.0, "rated_max_case_temperature_c": 125.0},
        )
        self.assertEqual(record["verdict"], ON_MARGIN)
        self.assertAlmostEqual(record["headroom_c"], 0.0, places=9)

    def test_case_below_the_ceiling_is_within_margin(self):
        record = grade_case_temperature(
            "resistor",
            {"case_temperature_c": 40.0, "rated_max_case_temperature_c": 125.0},
        )
        self.assertEqual(record["verdict"], WITHIN_MARGIN)

    def test_case_above_the_ceiling_is_over_margin(self):
        record = grade_case_temperature(
            "resistor",
            {"case_temperature_c": 120.0, "rated_max_case_temperature_c": 125.0},
        )
        self.assertFalse(record["compliant"])

    def test_absent_rated_maximum_returns_no_record(self):
        self.assertIsNone(
            grade_case_temperature("resistor", {"case_temperature_c": 40.0})
        )

    def test_ceiling_is_a_step_down_from_the_rated_maximum(self):
        record = grade_case_temperature(
            "integrated-circuit",
            {"case_temperature_c": 40.0, "rated_max_case_temperature_c": 105.0},
        )
        self.assertAlmostEqual(record["derated_max_case_temperature_c"], 80.0, places=9)


class PartTests(unittest.TestCase):
    def test_clean_part_is_compliant(self):
        record = assess_part(_part())
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])

    def test_part_without_case_temperature_is_indeterminate(self):
        part = _part()
        del part["case_temperature_c"]
        record = assess_part(part)
        self.assertTrue(record["indeterminate"])
        self.assertFalse(record["compliant"])
        self.assertEqual(len(record["findings"]), 1)

    def test_part_without_rated_maximum_is_indeterminate(self):
        part = _part()
        del part["rated_max_case_temperature_c"]
        record = assess_part(part)
        self.assertTrue(record["indeterminate"])

    def test_tightest_stress_is_named(self):
        record = assess_part(_part())
        self.assertIn(record["tightest_stress"], ELECTRICAL_STRESSES)

    def test_uncategorized_part_rejected(self):
        with self.assertRaises(ValueError):
            assess_part(_part(category="mystery-widget"))

    def test_blank_part_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_part(_part(part_reference="   "))

    def test_unknown_stress_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_part(_part(stresses={"flux": {"nominal": 1.0, "rating": _rating()}}))

    def test_empty_stress_map_rejected(self):
        with self.assertRaises(ValueError):
            assess_part(_part(stresses={}))

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            assess_part(_part(quantity=0))

    def test_every_breached_stress_is_named_not_only_the_first(self):
        part = _part(
            stresses={
                "voltage": {"nominal": 95.0, "rating": _rating()},
                "power": {"nominal": 0.45, "rating": _rating(rated_value=0.5)},
            }
        )
        record = assess_part(part)
        self.assertEqual(len(record["findings"]), 2)


class EquipmentTests(unittest.TestCase):
    def test_clean_equipment_is_satisfied(self):
        result = assess_equipment_derating(_equipment())
        self.assertEqual(result["verdict"], DERATING_SATISFIED)
        self.assertTrue(result["compliant"])

    def test_one_missing_case_temperature_makes_it_indeterminate(self):
        equipment = _equipment()
        del equipment["parts"][1]["case_temperature_c"]
        result = assess_equipment_derating(equipment)
        self.assertEqual(result["verdict"], DERATING_INDETERMINATE)
        self.assertEqual(result["indeterminate_parts"], ["U201"])

    def test_a_breach_outranks_an_indeterminate_part(self):
        equipment = _equipment()
        del equipment["parts"][1]["case_temperature_c"]
        equipment["parts"][0]["stresses"]["voltage"]["nominal"] = 99.0
        result = assess_equipment_derating(equipment)
        self.assertEqual(result["verdict"], DERATING_EXCEEDED)

    def test_quantity_fraction_graded_is_reported(self):
        equipment = _equipment()
        del equipment["parts"][1]["case_temperature_c"]
        result = assess_equipment_derating(equipment)
        self.assertAlmostEqual(result["quantity_fraction_graded"], 4.0 / 5.0, places=9)

    def test_tightest_part_is_named_across_the_equipment(self):
        result = assess_equipment_derating(_equipment())
        self.assertIn(result["tightest_part"], ("R101", "U201"))

    def test_duplicate_part_reference_rejected(self):
        equipment = _equipment()
        equipment["parts"][1]["part_reference"] = "R101"
        with self.assertRaises(ValueError):
            assess_equipment_derating(equipment)

    def test_empty_parts_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_derating(_equipment(parts=[]))

    def test_non_mapping_equipment_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_derating(["board"])

    def test_blank_equipment_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_derating(_equipment(equipment_name=""))

    def test_findings_roll_up_from_the_parts(self):
        equipment = _equipment()
        equipment["parts"][0]["stresses"]["voltage"]["nominal"] = 99.0
        result = assess_equipment_derating(equipment)
        self.assertTrue(any("R101" in item for item in result["findings"]))


if __name__ == "__main__":
    unittest.main()
