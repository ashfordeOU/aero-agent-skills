"""
Gate 3 contract tests for e1012-shield-unc logic.

Run: python3 test_e1012_shield_unc.py
Requires: stdlib only, offline, deterministic. Minimum 10 tests.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_shield_unc_logic import (
    COMBINATION_METHODS,
    FAMILY_CROSS_SECTION,
    FAMILY_GEOMETRY,
    FAMILY_MODEL,
    UNCERTAINTY_FAMILIES,
    apply_margin,
    assess_shielding_uncertainty,
    check_duplicate_contributors,
    check_requirement,
    combine_uncertainties,
    dominant_family,
    family_totals,
    resolve_family,
    validate_contributor,
)


def contributor(cid, family, fraction, substantiated=True):
    """Build a well-formed contributor dict for the tests."""
    return {
        "id": cid,
        "family": family,
        "fractional_uncertainty": fraction,
        "substantiated": substantiated,
        "rationale": f"test rationale for {cid}",
    }


THREE = [
    contributor("c1_model", "model", 0.10),
    contributor("c2_geometry", "geometry", 0.20),
    contributor("c3_xsec", "cross_section", 0.05),
]
RSS_THREE = math.sqrt(0.10 ** 2 + 0.20 ** 2 + 0.05 ** 2)


# ---------------------------------------------------------------------------
# resolve_family
# ---------------------------------------------------------------------------

class TestResolveFamily(unittest.TestCase):

    def test_canonical_names_pass_through(self):
        for family in UNCERTAINTY_FAMILIES:
            self.assertEqual(resolve_family(family), family)

    def test_transport_code_maps_to_model(self):
        self.assertEqual(resolve_family("transport_code"), FAMILY_MODEL)

    def test_mesh_maps_to_geometry(self):
        self.assertEqual(resolve_family("mesh"), FAMILY_GEOMETRY)

    def test_nuclear_data_maps_to_cross_section(self):
        self.assertEqual(resolve_family("nuclear_data"), FAMILY_CROSS_SECTION)

    def test_case_and_spacing_insensitive(self):
        self.assertEqual(resolve_family("  Cross-Section  "), FAMILY_CROSS_SECTION)
        self.assertEqual(resolve_family("Transport Code"), FAMILY_MODEL)

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            resolve_family("astrology")

    def test_non_string_family_raises(self):
        with self.assertRaises(ValueError):
            resolve_family(42)

    def test_empty_family_raises(self):
        with self.assertRaises(ValueError):
            resolve_family("   ")


# ---------------------------------------------------------------------------
# validate_contributor
# ---------------------------------------------------------------------------

class TestValidateContributor(unittest.TestCase):

    def test_normalises_family(self):
        result = validate_contributor(contributor("a", "transport_code", 0.1))
        self.assertEqual(result["family"], FAMILY_MODEL)

    def test_defaults_substantiated_true(self):
        result = validate_contributor(
            {"id": "a", "family": "model", "fractional_uncertainty": 0.2}
        )
        self.assertTrue(result["substantiated"])

    def test_zero_fraction_allowed(self):
        result = validate_contributor(contributor("a", "model", 0.0))
        self.assertEqual(result["fractional_uncertainty"], 0.0)

    def test_one_fraction_allowed(self):
        result = validate_contributor(contributor("a", "model", 1.0))
        self.assertEqual(result["fractional_uncertainty"], 1.0)

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(["id", "family"])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor({"family": "model", "fractional_uncertainty": 0.1})

    def test_missing_family_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor({"id": "a", "fractional_uncertainty": 0.1})

    def test_missing_fraction_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor({"id": "a", "family": "model"})

    def test_blank_id_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(contributor("   ", "model", 0.1))

    def test_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(contributor("a", "model", 1.5))

    def test_negative_fraction_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(contributor("a", "model", -0.1))

    def test_non_numeric_fraction_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(contributor("a", "model", "high"))

    def test_non_boolean_substantiated_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(
                {
                    "id": "a",
                    "family": "model",
                    "fractional_uncertainty": 0.1,
                    "substantiated": "yes",
                }
            )


# ---------------------------------------------------------------------------
# check_duplicate_contributors
# ---------------------------------------------------------------------------

class TestCheckDuplicates(unittest.TestCase):

    def test_unique_list_has_no_duplicates(self):
        self.assertEqual(check_duplicate_contributors(THREE), [])

    def test_repeated_id_is_reported(self):
        dupes = check_duplicate_contributors(
            [
                contributor("same", "model", 0.1),
                contributor("same", "geometry", 0.2),
            ]
        )
        self.assertEqual(dupes, ["same"])

    def test_duplicate_detection_is_sorted(self):
        dupes = check_duplicate_contributors(
            [
                contributor("zeta", "model", 0.1),
                contributor("alpha", "geometry", 0.1),
                contributor("zeta", "model", 0.2),
                contributor("alpha", "geometry", 0.2),
            ]
        )
        self.assertEqual(dupes, ["alpha", "zeta"])

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            check_duplicate_contributors([])

    def test_non_sequence_raises(self):
        with self.assertRaises(ValueError):
            check_duplicate_contributors("model")


# ---------------------------------------------------------------------------
# family_totals
# ---------------------------------------------------------------------------

class TestFamilyTotals(unittest.TestCase):

    def test_per_family_sum_of_squares(self):
        totals = family_totals(THREE)
        self.assertAlmostEqual(totals[FAMILY_MODEL], 0.01)
        self.assertAlmostEqual(totals[FAMILY_GEOMETRY], 0.04)
        self.assertAlmostEqual(totals[FAMILY_CROSS_SECTION], 0.0025)

    def test_all_families_present_as_keys(self):
        totals = family_totals(THREE)
        self.assertEqual(sorted(totals), sorted(UNCERTAINTY_FAMILIES))

    def test_duplicates_raise(self):
        with self.assertRaises(ValueError):
            family_totals(
                [contributor("d", "model", 0.1), contributor("d", "model", 0.1)]
            )


# ---------------------------------------------------------------------------
# combine_uncertainties
# ---------------------------------------------------------------------------

class TestCombineUncertainties(unittest.TestCase):

    def test_rss_of_three(self):
        self.assertAlmostEqual(combine_uncertainties(THREE, "rss"), RSS_THREE, places=9)

    def test_worst_case_is_linear_sum(self):
        self.assertAlmostEqual(
            combine_uncertainties(THREE, "worst_case"), 0.35, places=9
        )

    def test_rss_default_method(self):
        self.assertAlmostEqual(combine_uncertainties(THREE), RSS_THREE, places=9)

    def test_rss_smaller_than_worst_case(self):
        self.assertLess(
            combine_uncertainties(THREE, "rss"),
            combine_uncertainties(THREE, "worst_case"),
        )

    def test_single_contributor(self):
        single = [contributor("only", "model", 0.25)]
        self.assertAlmostEqual(combine_uncertainties(single, "rss"), 0.25)
        self.assertAlmostEqual(combine_uncertainties(single, "worst_case"), 0.25)

    def test_zero_contributors_combine_to_zero(self):
        zeros = [
            contributor("a", "model", 0.0),
            contributor("b", "geometry", 0.0),
        ]
        self.assertEqual(combine_uncertainties(zeros), 0.0)

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            combine_uncertainties(THREE, "quadrature")

    def test_empty_contributor_list_raises(self):
        with self.assertRaises(ValueError):
            combine_uncertainties([])

    def test_duplicate_ids_raise(self):
        with self.assertRaises(ValueError):
            combine_uncertainties(
                [contributor("d", "model", 0.1), contributor("d", "geometry", 0.1)]
            )

    def test_methods_constant_exposes_both(self):
        self.assertEqual(set(COMBINATION_METHODS), {"rss", "worst_case"})


# ---------------------------------------------------------------------------
# dominant_family
# ---------------------------------------------------------------------------

class TestDominantFamily(unittest.TestCase):

    def test_geometry_dominates(self):
        self.assertEqual(dominant_family(THREE), FAMILY_GEOMETRY)

    def test_model_dominates(self):
        data = [
            contributor("a", "model", 0.5),
            contributor("b", "geometry", 0.1),
        ]
        self.assertEqual(dominant_family(data), FAMILY_MODEL)

    def test_cross_section_dominates(self):
        data = [
            contributor("a", "model", 0.1),
            contributor("b", "cross_section", 0.4),
        ]
        self.assertEqual(dominant_family(data), FAMILY_CROSS_SECTION)

    def test_tie_breaks_by_fixed_order(self):
        data = [
            contributor("a", "geometry", 0.2),
            contributor("b", "model", 0.2),
        ]
        self.assertEqual(dominant_family(data), FAMILY_MODEL)

    def test_all_zero_returns_none(self):
        data = [
            contributor("a", "model", 0.0),
            contributor("b", "geometry", 0.0),
        ]
        self.assertIsNone(dominant_family(data))

    def test_duplicates_raise(self):
        with self.assertRaises(ValueError):
            dominant_family(
                [contributor("d", "model", 0.1), contributor("d", "model", 0.2)]
            )


# ---------------------------------------------------------------------------
# apply_margin
# ---------------------------------------------------------------------------

class TestApplyMargin(unittest.TestCase):

    def test_two_sigma_margin(self):
        # 1000 * (1 + 2 * 0.35) = 1700
        self.assertAlmostEqual(apply_margin(1000.0, 0.35, 2.0), 1700.0)

    def test_one_sigma_margin(self):
        self.assertAlmostEqual(apply_margin(1000.0, 0.10, 1.0), 1100.0)

    def test_three_sigma_margin(self):
        self.assertAlmostEqual(apply_margin(500.0, 0.20, 3.0), 800.0)

    def test_zero_uncertainty_returns_nominal(self):
        self.assertAlmostEqual(apply_margin(1000.0, 0.0, 2.0), 1000.0)

    def test_zero_nominal_returns_zero(self):
        self.assertAlmostEqual(apply_margin(0.0, 0.5, 2.0), 0.0)

    def test_missing_k_raises(self):
        with self.assertRaises(ValueError):
            apply_margin(1000.0, 0.20, None)

    def test_zero_k_raises(self):
        with self.assertRaises(ValueError):
            apply_margin(1000.0, 0.20, 0.0)

    def test_negative_k_raises(self):
        with self.assertRaises(ValueError):
            apply_margin(1000.0, 0.20, -1.0)

    def test_negative_nominal_raises(self):
        with self.assertRaises(ValueError):
            apply_margin(-1.0, 0.20, 2.0)

    def test_combined_above_one_raises(self):
        with self.assertRaises(ValueError):
            apply_margin(1000.0, 1.5, 2.0)

    def test_non_numeric_combined_raises(self):
        with self.assertRaises(ValueError):
            apply_margin(1000.0, "0.2", 2.0)


# ---------------------------------------------------------------------------
# check_requirement
# ---------------------------------------------------------------------------

class TestCheckRequirement(unittest.TestCase):

    def test_within_requirement(self):
        result = check_requirement(1700.0, 2000.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["exceedance_ratio"], 0.85)

    def test_exceeds_requirement(self):
        result = check_requirement(2500.0, 2000.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["exceedance_ratio"], 1.25)

    def test_exactly_at_requirement_is_compliant(self):
        result = check_requirement(2000.0, 2000.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["exceedance_ratio"], 1.0)

    def test_echoes_inputs(self):
        result = check_requirement(1500.0, 3000.0)
        self.assertEqual(result["margined"], 1500.0)
        self.assertEqual(result["requirement"], 3000.0)

    def test_zero_requirement_raises(self):
        with self.assertRaises(ValueError):
            check_requirement(1000.0, 0.0)

    def test_negative_margined_raises(self):
        with self.assertRaises(ValueError):
            check_requirement(-1.0, 2000.0)


# ---------------------------------------------------------------------------
# assess_shielding_uncertainty
# ---------------------------------------------------------------------------

class TestAssessShieldingUncertainty(unittest.TestCase):

    def test_full_pipeline_rss(self):
        result = assess_shielding_uncertainty(1000.0, THREE, 2000.0, 2.0)
        self.assertAlmostEqual(result["combined_uncertainty"], RSS_THREE, places=9)
        self.assertAlmostEqual(
            result["margined"], 1000.0 * (1.0 + 2.0 * RSS_THREE), places=9
        )
        self.assertTrue(result["compliant"])
        self.assertTrue(result["accepted"])
        self.assertEqual(result["dominant_family"], FAMILY_GEOMETRY)
        self.assertEqual(result["method"], "rss")

    def test_full_pipeline_worst_case(self):
        result = assess_shielding_uncertainty(
            1000.0, THREE, 2000.0, 2.0, method="worst_case"
        )
        self.assertAlmostEqual(result["combined_uncertainty"], 0.35)
        self.assertAlmostEqual(result["margined"], 1700.0)
        self.assertTrue(result["compliant"])

    def test_non_compliant_result(self):
        # worst_case 0.35, k=3 -> 1000 * 2.05 = 2050 > 2000
        result = assess_shielding_uncertainty(
            1000.0, THREE, 2000.0, 3.0, method="worst_case"
        )
        self.assertFalse(result["compliant"])
        self.assertFalse(result["accepted"])

    def test_unsubstantiated_blocks_acceptance(self):
        data = [
            contributor("c1", "model", 0.10),
            contributor("c2", "geometry", 0.10, substantiated=False),
        ]
        result = assess_shielding_uncertainty(1000.0, data, 5000.0, 2.0)
        self.assertTrue(result["compliant"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["unsubstantiated"], ["c2"])

    def test_duplicate_ids_raise(self):
        data = [
            contributor("dup", "model", 0.10),
            contributor("dup", "geometry", 0.10),
        ]
        with self.assertRaises(ValueError):
            assess_shielding_uncertainty(1000.0, data, 5000.0, 2.0)

    def test_unsubstantiated_ids_are_sorted(self):
        data = [
            contributor("zeta", "model", 0.05, substantiated=False),
            contributor("alpha", "geometry", 0.05, substantiated=False),
            contributor("mid", "cross_section", 0.05),
        ]
        result = assess_shielding_uncertainty(1000.0, data, 9000.0, 1.0)
        self.assertEqual(result["unsubstantiated"], ["alpha", "zeta"])

    def test_accepted_requires_compliant(self):
        result = assess_shielding_uncertainty(1000.0, THREE, 100.0, 2.0)
        self.assertFalse(result["accepted"])

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            assess_shielding_uncertainty(1000.0, THREE, 2000.0, 2.0, method="mean")

    def test_empty_contributors_raise(self):
        with self.assertRaises(ValueError):
            assess_shielding_uncertainty(1000.0, [], 2000.0, 2.0)

    def test_zero_k_raises(self):
        with self.assertRaises(ValueError):
            assess_shielding_uncertainty(1000.0, THREE, 2000.0, 0.0)

    def test_result_carries_nominal_and_k(self):
        result = assess_shielding_uncertainty(1234.0, THREE, 9999.0, 1.5)
        self.assertEqual(result["nominal"], 1234.0)
        self.assertEqual(result["k"], 1.5)


if __name__ == "__main__":
    unittest.main()
