"""Contract tests for the clause 4.1.6 engineering qualification model logic."""

import unittest

from q6013_class_1_eqm_components_logic import (
    DEFAULT_ATTRIBUTE_WEIGHTS,
    DEVIATION_IMPACT,
    FUNDAMENTAL_ATTRIBUTES,
    INDEX_TOLERANCE,
    PART_CATEGORIES,
    assess_eqm_representativeness,
    compare_component,
    evaluate_component,
    invalidated_domains,
    part_category,
    representativeness_index,
    retest_set,
    validate_weights,
)

FLIGHT = {
    "manufacturer": "Vendor-A",
    "part_number": "LM317-SMD",
    "package": "SOT-223",
    "die_lot": "LOT-4471",
    "screening_level": "upscreened-b",
    "mounting_technology": "smt",
}


def fitted(**overrides):
    """Return a fitted component identical to the flight build unless overridden."""
    base = dict(FLIGHT)
    base.update(overrides)
    return base


def item(reference="U1", quantity=1, **overrides):
    """Return an EQM component item for the assessment entry point."""
    return {
        "reference": reference,
        "quantity": quantity,
        "fitted": fitted(**overrides),
        "intended": dict(FLIGHT),
    }


class ValidateWeightsTests(unittest.TestCase):
    def test_default_weights_sum_to_unity(self):
        weights = validate_weights()
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=9)

    def test_default_set_covers_every_impacting_attribute(self):
        self.assertEqual(set(DEFAULT_ATTRIBUTE_WEIGHTS), set(DEVIATION_IMPACT))

    def test_weights_not_summing_to_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_weights({"package": 0.5, "die_lot": 0.2})

    def test_negative_weight_rejected(self):
        bad = dict(DEFAULT_ATTRIBUTE_WEIGHTS)
        bad["package"] = -0.15
        with self.assertRaises(ValueError):
            validate_weights(bad)

    def test_attribute_without_declared_impact_rejected(self):
        with self.assertRaises(ValueError):
            validate_weights({"paint_colour": 1.0})

    def test_empty_weight_map_rejected(self):
        with self.assertRaises(ValueError):
            validate_weights({})


class CompareComponentTests(unittest.TestCase):
    def test_identical_build_standard_has_no_deviation(self):
        self.assertEqual(compare_component(fitted(), dict(FLIGHT)), ())

    def test_package_substitution_is_found(self):
        self.assertEqual(compare_component(fitted(package="TO-220"), dict(FLIGHT)), ("package",))

    def test_deviations_are_returned_sorted(self):
        deviations = compare_component(
            fitted(package="TO-220", die_lot="LOT-9000"), dict(FLIGHT)
        )
        self.assertEqual(deviations, ("die_lot", "package"))

    def test_comparison_ignores_case_and_padding(self):
        self.assertEqual(compare_component(fitted(package=" sot-223 "), dict(FLIGHT)), ())

    def test_missing_attribute_on_the_fitted_part_rejected(self):
        broken = fitted()
        del broken["die_lot"]
        with self.assertRaises(ValueError):
            compare_component(broken, dict(FLIGHT))

    def test_blank_attribute_rejected(self):
        with self.assertRaises(ValueError):
            compare_component(fitted(package="  "), dict(FLIGHT))

    def test_non_mapping_component_rejected(self):
        with self.assertRaises(ValueError):
            compare_component(["Vendor-A"], dict(FLIGHT))


class RepresentativenessIndexTests(unittest.TestCase):
    def test_no_deviation_scores_unity(self):
        self.assertAlmostEqual(representativeness_index(()), 1.0, places=9)

    def test_package_deviation_costs_its_weight(self):
        self.assertAlmostEqual(
            representativeness_index(("package",)), 1.0 - DEFAULT_ATTRIBUTE_WEIGHTS["package"],
            places=9,
        )

    def test_deviations_accumulate(self):
        expected = 1.0 - DEFAULT_ATTRIBUTE_WEIGHTS["package"] - DEFAULT_ATTRIBUTE_WEIGHTS["die_lot"]
        self.assertAlmostEqual(representativeness_index(("package", "die_lot")), expected, places=9)

    def test_every_attribute_deviating_scores_zero(self):
        self.assertAlmostEqual(
            representativeness_index(tuple(sorted(DEFAULT_ATTRIBUTE_WEIGHTS))), 0.0, places=9
        )

    def test_repeated_deviation_rejected(self):
        with self.assertRaises(ValueError):
            representativeness_index(("package", "package"))

    def test_unweighted_deviation_rejected(self):
        with self.assertRaises(ValueError):
            representativeness_index(("paint_colour",))


class InvalidatedDomainTests(unittest.TestCase):
    def test_package_breaks_the_mechanical_and_thermal_argument(self):
        self.assertEqual(invalidated_domains(("package",)), ("mechanical", "thermal"))

    def test_die_lot_breaks_lifetime_and_radiation(self):
        self.assertEqual(invalidated_domains(("die_lot",)), ("lifetime", "radiation"))

    def test_domains_are_a_sorted_union(self):
        self.assertEqual(
            invalidated_domains(("package", "die_lot")),
            ("lifetime", "mechanical", "radiation", "thermal"),
        )

    def test_no_deviation_invalidates_nothing(self):
        self.assertEqual(invalidated_domains(()), ())

    def test_unknown_deviation_rejected(self):
        with self.assertRaises(ValueError):
            invalidated_domains(("paint_colour",))


class PartCategoryTests(unittest.TestCase):
    def test_identical_part_is_representative(self):
        self.assertEqual(part_category(1.0, (), 0.6), "representative")

    def test_small_deviation_is_partially_representative(self):
        self.assertEqual(part_category(0.85, ("package",), 0.6), "partially-representative")

    def test_large_deviation_is_not_representative(self):
        self.assertEqual(part_category(0.4, ("manufacturer", "package"), 0.6), "non-representative")

    def test_index_exactly_on_the_threshold_still_transfers_partially(self):
        index = representativeness_index(("package",))
        self.assertEqual(part_category(index, ("package",), 0.85), "partially-representative")

    def test_out_of_range_index_rejected(self):
        with self.assertRaises(ValueError):
            part_category(1.4, ("package",), 0.6)

    def test_out_of_range_threshold_rejected(self):
        with self.assertRaises(ValueError):
            part_category(0.8, ("package",), 1.4)

    def test_part_number_deviation_is_never_rescued_by_the_index(self):
        index = representativeness_index(("part_number",))
        self.assertAlmostEqual(index, 0.8, places=9)
        self.assertEqual(part_category(index, ("part_number",), 0.1), "non-representative")

    def test_fundamental_attributes_are_weighted_attributes(self):
        for attribute in FUNDAMENTAL_ATTRIBUTES:
            self.assertIn(attribute, DEFAULT_ATTRIBUTE_WEIGHTS)

    def test_category_set_has_three_members(self):
        self.assertEqual(len(PART_CATEGORIES), 3)


class EvaluateComponentTests(unittest.TestCase):
    def test_matching_component_transfers_everything(self):
        record = evaluate_component(item())
        self.assertEqual(record["category"], "representative")
        self.assertEqual(record["invalidated_domains"], ())
        self.assertAlmostEqual(record["index"], 1.0, places=9)

    def test_package_substitution_limits_the_transfer(self):
        record = evaluate_component(item(package="TO-220"))
        self.assertEqual(record["category"], "partially-representative")
        self.assertEqual(record["invalidated_domains"], ("mechanical", "thermal"))

    def test_different_manufacturer_breaks_the_transfer(self):
        record = evaluate_component(item(manufacturer="Vendor-B"))
        self.assertEqual(record["category"], "non-representative")
        self.assertAlmostEqual(record["index"], 0.8, places=9)

    def test_missing_reference_rejected(self):
        broken = item()
        del broken["reference"]
        with self.assertRaises(ValueError):
            evaluate_component(broken)

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_component(item(quantity=0))

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_component(["U1"])


class RetestSetTests(unittest.TestCase):
    def test_representative_parts_add_nothing(self):
        self.assertEqual(retest_set([evaluate_component(item())]), ())

    def test_retest_set_is_the_union_of_deviating_parts(self):
        records = [
            evaluate_component(item("U1", package="TO-220")),
            evaluate_component(item("U2", die_lot="LOT-9000")),
        ]
        self.assertEqual(retest_set(records), ("lifetime", "mechanical", "radiation", "thermal"))

    def test_empty_records_rejected(self):
        with self.assertRaises(ValueError):
            retest_set([])


class AssessEqmRepresentativenessTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {"components": [item("U1"), item("U2")]}
        base.update(overrides)
        return base

    def test_matching_build_standard_transfers(self):
        result = assess_eqm_representativeness(self._spec())
        self.assertEqual(result["verdict"], "transferable")
        self.assertEqual(result["retest_domains"], ())
        self.assertAlmostEqual(result["model_index"], 1.0, places=9)

    def test_one_partial_component_forces_a_retest(self):
        spec = self._spec(components=[item("U1"), item("U2", package="TO-220")])
        result = assess_eqm_representativeness(spec)
        self.assertEqual(result["verdict"], "transferable-with-retest")
        self.assertEqual(result["retest_domains"], ("mechanical", "thermal"))

    def test_one_non_representative_component_stops_the_transfer(self):
        spec = self._spec(components=[item("U1"), item("U2", manufacturer="Vendor-B")])
        result = assess_eqm_representativeness(spec)
        self.assertEqual(result["verdict"], "not-transferable")
        self.assertEqual(result["category_counts"]["non-representative"], 1)

    def test_model_index_is_weighted_by_quantity(self):
        spec = self._spec(
            components=[item("U1", quantity=3), item("U2", quantity=1, package="TO-220")]
        )
        result = assess_eqm_representativeness(spec)
        expected = (3.0 * 1.0 + 1.0 * (1.0 - DEFAULT_ATTRIBUTE_WEIGHTS["package"])) / 4.0
        self.assertAlmostEqual(result["model_index"], expected, places=9)

    def test_findings_rank_the_non_representative_part_first(self):
        spec = self._spec(
            components=[item("U1", package="TO-220"), item("U2", manufacturer="Vendor-B")]
        )
        result = assess_eqm_representativeness(spec)
        self.assertEqual(result["findings"][0]["reference"], "U2")
        self.assertEqual(result["findings"][0]["severity"], 0)

    def test_raising_the_threshold_can_demote_a_partial_part(self):
        spec = self._spec(components=[item("U1", package="TO-220")], threshold=0.95)
        result = assess_eqm_representativeness(spec)
        self.assertEqual(result["verdict"], "not-transferable")

    def test_custom_weights_change_the_index(self):
        weights = {
            "manufacturer": 0.1,
            "part_number": 0.1,
            "package": 0.5,
            "die_lot": 0.1,
            "screening_level": 0.1,
            "mounting_technology": 0.1,
        }
        spec = self._spec(components=[item("U1", package="TO-220")], weights=weights)
        result = assess_eqm_representativeness(spec)
        self.assertAlmostEqual(result["model_index"], 0.5, places=9)

    def test_missing_components_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_representativeness({})

    def test_empty_components_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_representativeness(self._spec(components=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_representativeness(["components"])

    def test_tolerance_is_representation_sized(self):
        self.assertLess(INDEX_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
