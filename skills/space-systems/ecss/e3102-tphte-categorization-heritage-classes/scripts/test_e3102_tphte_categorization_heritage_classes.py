"""Contract tests for the clause 4.1 and 5.4 two-phase grouping logic."""

import unittest

from e3102_tphte_categorization_heritage_classes_logic import (
    CATEGORY_TESTS,
    CATEGORY_UNITS,
    EQUIPMENT_TYPES,
    HERITAGE_CATEGORIES,
    RATIO_TOLERANCE,
    SCALING_NEW_DEVELOPMENT_RATIO,
    TEMPERATURE_EXTENSION_NEW_DEVELOPMENT_K,
    TYPE_TESTS,
    assess_tphte_item,
    assess_tphte_programme,
    heritage_category,
    qualification_tests,
    qualification_units,
    ratio_is_unity,
    scaling_ratio,
    temperature_extension_k,
    validate_equipment_type,
    validate_range_k,
)


def _reference(**overrides):
    reference = {
        "equipment_type": "constant-conductance-heat-pipe",
        "working_fluid": "ammonia",
        "envelope_material": "aluminium-6063",
        "wick_type": "axial-groove",
        "application": "telecom-platform-radiator",
        "length_m": 1.20,
        "transport_power_w": 250.0,
        "operating_range_k": (253.0, 323.0),
    }
    reference.update(overrides)
    return reference


class VocabularyTests(unittest.TestCase):
    def test_four_equipment_types_are_held(self):
        self.assertEqual(len(EQUIPMENT_TYPES), 4)

    def test_equipment_type_is_normalised(self):
        self.assertEqual(
            validate_equipment_type(" Diode-Heat-Pipe "), "diode-heat-pipe"
        )

    def test_unknown_equipment_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_equipment_type("pumped-single-phase-loop")

    def test_three_heritage_categories_are_held(self):
        self.assertEqual(HERITAGE_CATEGORIES, ("A", "B", "C"))

    def test_deeper_category_owes_more_tests(self):
        self.assertLess(len(CATEGORY_TESTS["A"]), len(CATEGORY_TESTS["B"]))
        self.assertLess(len(CATEGORY_TESTS["B"]), len(CATEGORY_TESTS["C"]))

    def test_deeper_category_owes_more_units(self):
        self.assertLess(CATEGORY_UNITS["A"], CATEGORY_UNITS["B"])
        self.assertLess(CATEGORY_UNITS["B"], CATEGORY_UNITS["C"])

    def test_every_equipment_type_has_a_type_test_entry(self):
        for name in EQUIPMENT_TYPES:
            self.assertIn(name, TYPE_TESTS)


class RangeAndRatioTests(unittest.TestCase):
    def test_range_is_returned_as_floats(self):
        self.assertEqual(validate_range_k((253, 323), "range"), (253.0, 323.0))

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_range_k((323.0, 253.0), "range")

    def test_range_of_wrong_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_range_k((253.0,), "range")

    def test_ratio_is_a_quotient(self):
        self.assertAlmostEqual(scaling_ratio(1.8, 1.2), 1.5, places=9)

    def test_identical_values_give_unity(self):
        self.assertTrue(ratio_is_unity(scaling_ratio(1.2, 1.2)))

    def test_changed_value_is_not_unity(self):
        self.assertFalse(ratio_is_unity(scaling_ratio(1.32, 1.2)))

    def test_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            scaling_ratio(1.2, 0.0)

    def test_negative_ratio_rejected(self):
        with self.assertRaises(ValueError):
            ratio_is_unity(-1.0)

    def test_range_inside_the_qualified_one_extends_nothing(self):
        self.assertAlmostEqual(
            temperature_extension_k((263.0, 313.0), (253.0, 323.0)), 0.0, places=9
        )

    def test_hot_extension_is_measured(self):
        self.assertAlmostEqual(
            temperature_extension_k((253.0, 340.0), (253.0, 323.0)), 17.0, places=9
        )

    def test_cold_extension_is_measured(self):
        self.assertAlmostEqual(
            temperature_extension_k((230.0, 323.0), (253.0, 323.0)), 23.0, places=9
        )

    def test_the_larger_of_the_two_extensions_wins(self):
        self.assertAlmostEqual(
            temperature_extension_k((248.0, 340.0), (253.0, 323.0)), 17.0, places=9
        )


class HeritageCategoryTests(unittest.TestCase):
    def test_unchanged_item_in_the_same_application_is_category_a(self):
        result = heritage_category(_reference(), _reference())
        self.assertEqual(result["category"], "A")

    def test_new_application_alone_is_category_b(self):
        result = heritage_category(
            _reference(application="earth-observation-instrument-bench"), _reference()
        )
        self.assertEqual(result["category"], "B")

    def test_modest_length_growth_is_category_b(self):
        result = heritage_category(_reference(length_m=1.32), _reference())
        self.assertEqual(result["category"], "B")

    def test_length_growth_beyond_the_envelope_is_category_c(self):
        result = heritage_category(_reference(length_m=2.40), _reference())
        self.assertEqual(result["category"], "C")

    def test_length_exactly_at_the_envelope_ratio_stays_category_b(self):
        stretched = 1.20 * SCALING_NEW_DEVELOPMENT_RATIO
        result = heritage_category(_reference(length_m=stretched), _reference())
        self.assertEqual(result["category"], "B")

    def test_power_growth_beyond_the_envelope_is_category_c(self):
        result = heritage_category(_reference(transport_power_w=600.0), _reference())
        self.assertEqual(result["category"], "C")

    def test_fluid_change_is_category_c(self):
        result = heritage_category(_reference(working_fluid="propylene"), _reference())
        self.assertEqual(result["category"], "C")

    def test_envelope_material_change_is_category_c(self):
        result = heritage_category(
            _reference(envelope_material="stainless-steel-316l"), _reference()
        )
        self.assertEqual(result["category"], "C")

    def test_wick_change_is_category_c(self):
        result = heritage_category(_reference(wick_type="sintered-powder"), _reference())
        self.assertEqual(result["category"], "C")

    def test_equipment_type_change_is_category_c(self):
        result = heritage_category(
            _reference(equipment_type="diode-heat-pipe"), _reference()
        )
        self.assertEqual(result["category"], "C")

    def test_small_range_extension_is_category_b(self):
        result = heritage_category(
            _reference(operating_range_k=(253.0, 333.0)), _reference()
        )
        self.assertEqual(result["category"], "B")

    def test_large_range_extension_is_category_c(self):
        result = heritage_category(
            _reference(operating_range_k=(253.0, 353.0)), _reference()
        )
        self.assertEqual(result["category"], "C")

    def test_extension_exactly_at_the_threshold_stays_category_b(self):
        high = 323.0 + TEMPERATURE_EXTENSION_NEW_DEVELOPMENT_K
        result = heritage_category(
            _reference(operating_range_k=(253.0, high)), _reference()
        )
        self.assertEqual(result["category"], "B")

    def test_reasons_are_carried_with_the_placement(self):
        result = heritage_category(_reference(working_fluid="propylene"), _reference())
        self.assertTrue(any("working fluid" in reason for reason in result["reasons"]))

    def test_missing_attribute_rejected(self):
        candidate = _reference()
        del candidate["wick_type"]
        with self.assertRaises(ValueError):
            heritage_category(candidate, _reference())

    def test_blank_attribute_rejected(self):
        with self.assertRaises(ValueError):
            heritage_category(_reference(working_fluid="  "), _reference())

    def test_non_mapping_reference_rejected(self):
        with self.assertRaises(ValueError):
            heritage_category(_reference(), ["reference"])


class QualificationDepthTests(unittest.TestCase):
    def test_category_a_heat_pipe_owes_acceptance_only(self):
        self.assertEqual(
            qualification_tests("A", "constant-conductance-heat-pipe"),
            ("acceptance-performance-test",),
        )

    def test_category_a_variable_conductance_pipe_still_owes_its_type_tests(self):
        tests = qualification_tests("A", "variable-conductance-heat-pipe")
        self.assertIn("reservoir-gas-inventory-test", tests)

    def test_diode_owes_its_reverse_mode_demonstration(self):
        self.assertIn(
            "reverse-mode-shutoff-test", qualification_tests("B", "diode-heat-pipe")
        )

    def test_capillary_loop_owes_start_up_and_load_sharing(self):
        tests = qualification_tests("C", "capillary-driven-loop")
        self.assertIn("start-up-test", tests)
        self.assertIn("heat-load-sharing-test", tests)

    def test_category_c_adds_life_and_burst_over_category_b(self):
        deeper = set(qualification_tests("C", "constant-conductance-heat-pipe"))
        shallower = set(qualification_tests("B", "constant-conductance-heat-pipe"))
        self.assertTrue(shallower.issubset(deeper))
        self.assertIn("life-test", deeper - shallower)

    def test_test_set_is_sorted_and_free_of_duplicates(self):
        tests = qualification_tests("C", "capillary-driven-loop")
        self.assertEqual(list(tests), sorted(set(tests)))

    def test_category_name_is_case_insensitive(self):
        self.assertEqual(
            qualification_tests("c", "diode-heat-pipe"),
            qualification_tests("C", "diode-heat-pipe"),
        )

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            qualification_tests("D", "diode-heat-pipe")

    def test_units_follow_the_category(self):
        self.assertEqual(qualification_units("A"), 0)
        self.assertEqual(qualification_units("C"), 2)

    def test_unknown_category_units_rejected(self):
        with self.assertRaises(ValueError):
            qualification_units("Z")


class ItemAndProgrammeTests(unittest.TestCase):
    def _item(self, identifier, **candidate_overrides):
        return {
            "id": identifier,
            "candidate": _reference(**candidate_overrides),
            "reference": _reference(),
        }

    def test_unchanged_item_is_acceptance_only(self):
        record = assess_tphte_item(self._item("HP-01"))
        self.assertTrue(record["acceptance_only"])
        self.assertEqual(record["qualification_units"], 0)

    def test_new_development_item_owes_two_units(self):
        record = assess_tphte_item(self._item("CDL-01", working_fluid="propylene"))
        self.assertEqual(record["category"], "C")
        self.assertEqual(record["qualification_units"], 2)

    def test_item_keeps_its_identifier(self):
        self.assertEqual(assess_tphte_item(self._item("HP-02"))["id"], "HP-02")

    def test_blank_item_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_tphte_item(self._item("   "))

    def test_missing_item_key_rejected(self):
        item = self._item("HP-03")
        del item["reference"]
        with self.assertRaises(ValueError):
            assess_tphte_item(item)

    def test_programme_counts_the_categories(self):
        result = assess_tphte_programme({"items": [
            self._item("HP-01"),
            self._item("HP-02", length_m=1.32),
            self._item("HP-03", working_fluid="propylene"),
        ]})
        self.assertEqual(result["category_counts"], {"A": 1, "B": 1, "C": 1})

    def test_programme_names_the_deepest_item(self):
        result = assess_tphte_programme({"items": [
            self._item("HP-01"),
            self._item("HP-03", working_fluid="propylene"),
        ]})
        self.assertEqual(result["deepest_qualification_item"], "HP-03")

    def test_programme_sums_the_qualification_units(self):
        result = assess_tphte_programme({"items": [
            self._item("HP-01"),
            self._item("HP-02", length_m=1.32),
            self._item("HP-03", working_fluid="propylene"),
        ]})
        self.assertEqual(result["total_qualification_units"], 3)

    def test_combined_test_set_is_the_union(self):
        result = assess_tphte_programme({"items": [
            self._item("HP-01"),
            self._item("CDL-01", equipment_type="capillary-driven-loop"),
        ]})
        self.assertIn("start-up-test", result["combined_test_set"])
        self.assertIn("acceptance-performance-test", result["combined_test_set"])

    def test_duplicate_item_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_tphte_programme({"items": [self._item("HP-01"), self._item("HP-01")]})

    def test_empty_item_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_tphte_programme({"items": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_tphte_programme(["items"])

    def test_ratio_tolerance_relaxes_nothing_measurable(self):
        self.assertLess(RATIO_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
