#!/usr/bin/env python3
"""Contract test for build-lot and first-article qualification (offline)."""

import copy
import unittest

from q7080_build_lot_qualification_logic import (
    CONFIGURATION_ITEMS,
    DEFAULT_QUALIFICATION_POLICY,
    DELTA_QUALIFICATION,
    NO_IMPACT,
    PART_TYPES,
    REQUALIFICATION,
    assess_build_lot_qualification,
    change_impact,
    coefficient_of_variation,
    combined_change_impact,
    lower_tolerance_bound,
    required_witness_count,
    sample_mean,
    sample_standard_deviation,
    tolerance_factor,
    validate_qualification_policy,
)

COUPONS = [920.0, 905.0, 935.0, 912.0, 928.0]

LOT_CASE = {
    "part_type": "secondary-structure",
    "is_first_article": False,
    "changed_items": ["operator"],
    "witness_results": COUPONS,
    "design_allowable_mpa": 800.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_qualification_policy(DEFAULT_QUALIFICATION_POLICY),
            DEFAULT_QUALIFICATION_POLICY,
        )

    def test_policy_covers_every_configuration_item(self):
        for item in CONFIGURATION_ITEMS:
            self.assertIn(item, DEFAULT_QUALIFICATION_POLICY["change_impact"])

    def test_policy_covers_every_part_type(self):
        for part_type in PART_TYPES:
            self.assertIn(part_type, DEFAULT_QUALIFICATION_POLICY["witness_count"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_qualification_policy("default")

    def test_policy_missing_an_item_rejected(self):
        broken = copy.deepcopy(DEFAULT_QUALIFICATION_POLICY)
        del broken["change_impact"]["powder-lot"]
        with self.assertRaises(ValueError):
            validate_qualification_policy(broken)

    def test_non_monotonic_tolerance_table_rejected(self):
        broken = copy.deepcopy(DEFAULT_QUALIFICATION_POLICY)
        broken["tolerance_factor"][10] = 9.9
        with self.assertRaises(ValueError):
            validate_qualification_policy(broken)


class ChangeTests(unittest.TestCase):
    def test_a_new_machine_breaks_the_baseline(self):
        self.assertEqual(change_impact("machine"), REQUALIFICATION)

    def test_a_new_powder_lot_is_a_delta(self):
        self.assertEqual(change_impact("powder-lot"), DELTA_QUALIFICATION)

    def test_an_operator_change_carries_no_impact(self):
        self.assertEqual(change_impact("operator"), NO_IMPACT)

    def test_unknown_configuration_item_rejected(self):
        with self.assertRaises(ValueError):
            change_impact("room-temperature")

    def test_worst_change_governs_and_is_named(self):
        combined = combined_change_impact(["powder-lot", "machine", "operator"])
        self.assertEqual(combined["impact"], REQUALIFICATION)
        self.assertEqual(combined["drivers"], ["machine"])

    def test_several_deltas_are_all_named(self):
        combined = combined_change_impact(["powder-lot", "build-orientation"])
        self.assertEqual(combined["impact"], DELTA_QUALIFICATION)
        self.assertEqual(len(combined["drivers"]), 2)

    def test_no_changes_leaves_the_baseline_standing(self):
        combined = combined_change_impact([])
        self.assertEqual(combined["impact"], NO_IMPACT)
        self.assertEqual(combined["drivers"], [])

    def test_non_sequence_change_list_rejected(self):
        with self.assertRaises(ValueError):
            combined_change_impact("machine")


class StatisticsTests(unittest.TestCase):
    def test_mean_of_the_coupons(self):
        self.assertAlmostEqual(sample_mean(COUPONS), 920.0, places=9)

    def test_spread_uses_the_sample_divisor(self):
        self.assertAlmostEqual(
            sample_standard_deviation([1.0, 2.0, 3.0, 4.0, 5.0]),
            (10.0 / 4.0) ** 0.5,
            places=9,
        )

    def test_single_coupon_has_no_spread(self):
        with self.assertRaises(ValueError):
            sample_standard_deviation([920.0])

    def test_empty_coupon_set_rejected(self):
        with self.assertRaises(ValueError):
            sample_mean([])

    def test_negative_strength_rejected(self):
        with self.assertRaises(ValueError):
            sample_mean([920.0, -5.0])

    def test_scatter_is_spread_over_mean(self):
        self.assertAlmostEqual(
            coefficient_of_variation(COUPONS),
            sample_standard_deviation(COUPONS) / 920.0,
            places=12,
        )


class ToleranceBoundTests(unittest.TestCase):
    def test_factor_falls_as_coupons_are_added(self):
        self.assertGreater(tolerance_factor(3), tolerance_factor(10))

    def test_untabulated_count_takes_the_lower_entry(self):
        self.assertAlmostEqual(tolerance_factor(12), tolerance_factor(10), places=12)

    def test_too_few_coupons_for_a_bound_rejected(self):
        with self.assertRaises(ValueError):
            tolerance_factor(2)

    def test_bound_sits_below_the_mean(self):
        bound = lower_tolerance_bound(COUPONS)
        self.assertLess(bound, sample_mean(COUPONS))

    def test_bound_matches_the_mean_less_factor_times_spread(self):
        expected = sample_mean(COUPONS) - tolerance_factor(5) * sample_standard_deviation(
            COUPONS
        )
        self.assertAlmostEqual(lower_tolerance_bound(COUPONS), expected, places=9)

    def test_more_coupons_of_the_same_material_lift_the_bound(self):
        few = lower_tolerance_bound(COUPONS)
        many = lower_tolerance_bound(COUPONS + COUPONS)
        self.assertGreater(many, few)


class WitnessCountTests(unittest.TestCase):
    def test_primary_structure_owes_more_than_non_structural(self):
        self.assertGreater(
            required_witness_count("primary-structure", False),
            required_witness_count("non-structural", False),
        )

    def test_first_article_doubles_the_count(self):
        self.assertEqual(
            required_witness_count("secondary-structure", True),
            2 * required_witness_count("secondary-structure", False),
        )

    def test_unknown_part_type_rejected(self):
        with self.assertRaises(ValueError):
            required_witness_count("bracketry", False)

    def test_non_boolean_first_article_flag_rejected(self):
        with self.assertRaises(ValueError):
            required_witness_count("secondary-structure", "yes")


class AssessmentTests(unittest.TestCase):
    def test_clean_lot_is_qualified(self):
        result = assess_build_lot_qualification(LOT_CASE)
        self.assertTrue(result["qualified"])
        self.assertEqual(result["verdict"], "lot-qualified")

    def test_machine_change_forces_requalification(self):
        result = assess_build_lot_qualification(
            _case(LOT_CASE, changed_items=["machine"])
        )
        self.assertFalse(result["qualified"])
        self.assertEqual(result["verdict"], "requalification-required")

    def test_powder_lot_change_is_supported_by_fresh_coupons(self):
        result = assess_build_lot_qualification(
            _case(LOT_CASE, changed_items=["powder-lot"])
        )
        self.assertTrue(result["qualified"])
        self.assertEqual(result["verdict"], "delta-qualification-supported")

    def test_too_few_coupons_leaves_the_lot_unqualified(self):
        result = assess_build_lot_qualification(
            _case(LOT_CASE, witness_results=COUPONS[:3])
        )
        self.assertFalse(result["qualified"])
        self.assertEqual(result["verdict"], "witness-evidence-insufficient")

    def test_first_article_needs_the_doubled_coupon_set(self):
        result = assess_build_lot_qualification(_case(LOT_CASE, is_first_article=True))
        self.assertEqual(result["required_witness_count"], 10)
        self.assertEqual(result["verdict"], "witness-evidence-insufficient")

    def test_allowable_above_the_bound_is_not_supported(self):
        result = assess_build_lot_qualification(
            _case(LOT_CASE, design_allowable_mpa=900.0)
        )
        self.assertFalse(result["qualified"])
        self.assertEqual(result["verdict"], "allowable-not-supported")
        self.assertFalse(result["supports_allowable"])

    def test_allowable_exactly_on_the_bound_is_supported(self):
        bound = lower_tolerance_bound(COUPONS)
        result = assess_build_lot_qualification(
            _case(LOT_CASE, design_allowable_mpa=bound)
        )
        self.assertAlmostEqual(
            result["witness_statistics"]["tolerance_bound_mpa"], bound, places=9
        )
        self.assertTrue(result["supports_allowable"])

    def test_wide_scatter_is_reported(self):
        noisy = [980.0, 700.0, 1100.0, 820.0, 900.0]
        result = assess_build_lot_qualification(
            _case(LOT_CASE, witness_results=noisy)
        )
        self.assertTrue(any("scatter" in f for f in result["findings"]))

    def test_single_coupon_has_no_statistical_evidence(self):
        result = assess_build_lot_qualification(
            _case(LOT_CASE, witness_results=[920.0])
        )
        self.assertIsNone(result["witness_statistics"])
        self.assertEqual(result["verdict"], "witness-evidence-insufficient")

    def test_every_part_type_is_assessable(self):
        for part_type in PART_TYPES:
            result = assess_build_lot_qualification(
                _case(LOT_CASE, part_type=part_type, witness_results=COUPONS * 4)
            )
            self.assertEqual(result["part_type"], part_type)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_build_lot_qualification("secondary-structure")

    def test_missing_allowable_rejected(self):
        case = _case(LOT_CASE)
        del case["design_allowable_mpa"]
        with self.assertRaises(ValueError):
            assess_build_lot_qualification(case)

    def test_non_sequence_witness_results_rejected(self):
        with self.assertRaises(ValueError):
            assess_build_lot_qualification(_case(LOT_CASE, witness_results=920.0))


if __name__ == "__main__":
    unittest.main()
