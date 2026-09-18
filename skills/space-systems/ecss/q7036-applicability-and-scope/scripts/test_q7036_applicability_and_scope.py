"""Contract tests for the SCC applicability-and-scope logic."""

import unittest

from q7036_applicability_and_scope_logic import (
    COVERAGE_TOLERANCE,
    METALLIC_FAMILIES,
    assess_scope,
    disposition_part,
    effective_family,
    family_in_scope,
    has_tabulated_rating,
    is_metallic,
    normalize_family,
    normalize_form,
)


def part(pid, family, form="wrought", **extra):
    record = {"id": pid, "family": family, "form": form}
    record.update(extra)
    return record


class NormalizationTests(unittest.TestCase):
    def test_alias_maps_to_canonical_family(self):
        self.assertEqual(normalize_family("Aluminum"), "aluminium")

    def test_whitespace_and_case_tolerated(self):
        self.assertEqual(normalize_family("  Stainless Steel "), "stainless-steel")

    def test_underscore_form_normalized(self):
        self.assertEqual(normalize_family("titanium_alloy"), "titanium")

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family("unobtainium")

    def test_blank_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family("   ")

    def test_non_string_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family(7036)

    def test_form_normalized(self):
        self.assertEqual(normalize_form("Weldment"), "weldment")

    def test_unknown_form_rejected(self):
        with self.assertRaises(ValueError):
            normalize_form("sintered-felt")


class ScopePredicateTests(unittest.TestCase):
    def test_every_listed_metal_is_metallic(self):
        for family in METALLIC_FAMILIES:
            self.assertTrue(is_metallic(family), family)

    def test_composite_is_not_metallic(self):
        self.assertFalse(is_metallic("cfrp"))

    def test_metal_is_in_scope(self):
        self.assertTrue(family_in_scope("magnesium"))

    def test_polymer_is_out_of_scope(self):
        self.assertFalse(family_in_scope("polymer"))

    def test_common_alloys_carry_a_published_rating(self):
        self.assertTrue(has_tabulated_rating("aluminium"))
        self.assertTrue(has_tabulated_rating("copper"))

    def test_refractory_metal_has_no_published_rating(self):
        self.assertFalse(has_tabulated_rating("refractory-metal"))

    def test_non_metal_never_carries_a_rating(self):
        self.assertFalse(has_tabulated_rating("ceramic"))


class EffectiveFamilyTests(unittest.TestCase):
    def test_plain_part_governs_itself(self):
        self.assertEqual(effective_family(part("p1", "titanium")), "titanium")

    def test_coating_follows_its_substrate(self):
        record = part("p2", "nickel", form="coating", substrate_family="aluminium")
        self.assertEqual(effective_family(record), "aluminium")

    def test_coating_without_substrate_rejected(self):
        with self.assertRaises(ValueError):
            effective_family(part("p3", "nickel", form="coating"))

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            effective_family({"id": "p4", "family": "aluminium"})

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            effective_family(["p5", "aluminium", "wrought"])


class DispositionTests(unittest.TestCase):
    def test_rated_metal_is_in_scope_rated(self):
        record = disposition_part(part("b1", "aluminium"))
        self.assertEqual(record["disposition"], "in-scope-rated")
        self.assertTrue(record["in_scope"])

    def test_unrated_metal_owes_evidence(self):
        record = disposition_part(part("b2", "niobium"))
        self.assertEqual(record["disposition"], "in-scope-evidence-required")
        self.assertTrue(record["in_scope"])
        self.assertFalse(record["tabulated_rating"])

    def test_non_metal_is_out_of_scope(self):
        record = disposition_part(part("b3", "ceramic"))
        self.assertEqual(record["disposition"], "out-of-scope-non-metallic")
        self.assertFalse(record["in_scope"])

    def test_coated_part_is_dispositioned_on_the_substrate(self):
        record = disposition_part(
            part("b4", "titanium", form="coating", substrate_family="magnesium")
        )
        self.assertEqual(record["governing_family"], "magnesium")
        self.assertEqual(record["declared_family"], "titanium")

    def test_blank_part_id_rejected(self):
        with self.assertRaises(ValueError):
            disposition_part(part("", "aluminium"))


class AssessScopeTests(unittest.TestCase):
    def test_all_rated_list_is_fully_covered(self):
        result = assess_scope([part("a", "aluminium"), part("b", "titanium")])
        self.assertTrue(result["fully_covered"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage_ratio"], 1.0, places=9)

    def test_unrated_metal_produces_a_finding(self):
        result = assess_scope([part("a", "aluminium"), part("b", "tantalum")])
        self.assertFalse(result["fully_covered"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("refractory-metal", result["findings"][0])

    def test_coverage_counts_only_in_scope_parts(self):
        result = assess_scope(
            [part("a", "aluminium"), part("b", "cfrp"), part("c", "cfrp")]
        )
        self.assertEqual(result["in_scope_count"], 1)
        self.assertEqual(result["out_of_scope_count"], 2)
        self.assertAlmostEqual(result["coverage_ratio"], 1.0, places=9)

    def test_half_covered_list_reports_one_half(self):
        result = assess_scope([part("a", "aluminium"), part("b", "beryllium")])
        self.assertAlmostEqual(result["coverage_ratio"], 0.5, places=9)

    def test_all_non_metallic_list_is_vacuously_covered(self):
        result = assess_scope([part("a", "polymer"), part("b", "glass")])
        self.assertEqual(result["in_scope_count"], 0)
        self.assertTrue(result["fully_covered"])

    def test_coverage_tolerance_is_tight(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)

    def test_duplicate_part_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_scope([part("a", "aluminium"), part("a", "titanium")])

    def test_empty_parts_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_scope([])

    def test_non_sequence_parts_rejected(self):
        with self.assertRaises(ValueError):
            assess_scope({"id": "a", "family": "aluminium", "form": "wrought"})

    def test_record_count_matches_input(self):
        result = assess_scope(
            [part("a", "aluminium"), part("b", "steel"), part("c", "polymer")]
        )
        self.assertEqual(result["total_parts"], 3)
        self.assertEqual(len(result["records"]), 3)


if __name__ == "__main__":
    unittest.main()
