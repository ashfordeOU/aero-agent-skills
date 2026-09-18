"""Contract tests for the ECSS-Q-ST-70-31C paint-system applicability logic."""

import unittest

from q7031_applicability_and_paint_systems_logic import (
    DFT_TOLERANCE_UM,
    DISPOSITIONS,
    LAYER_ROLES,
    METALLIC_SUBSTRATES,
    ORGANIC_BINDERS,
    assess_applicability,
    build_within_limit,
    finish_category,
    normalize_key,
    normalize_layer,
    normalize_stack,
    stack_findings,
    total_dft_um,
)

PRIMER = {
    "role": "primer",
    "binder": "epoxy",
    "nominal_dft_um": 20.0,
    "minus_tolerance_um": 5.0,
    "plus_tolerance_um": 5.0,
}
TOPCOAT = {
    "role": "topcoat",
    "binder": "polyurethane",
    "nominal_dft_um": 60.0,
    "minus_tolerance_um": 10.0,
    "plus_tolerance_um": 20.0,
}


def item(**overrides):
    base = {
        "finish_family": "primer-topcoat-system",
        "substrate": "aluminium-alloy",
        "layers": [dict(PRIMER), dict(TOPCOAT)],
    }
    base.update(overrides)
    return base


class KeyNormalisationTests(unittest.TestCase):
    def test_key_is_trimmed_and_case_folded(self):
        self.assertEqual(normalize_key("  Aluminium-Alloy ", "substrate"), "aluminium-alloy")

    def test_empty_key_rejected(self):
        with self.assertRaises(ValueError):
            normalize_key("   ", "substrate")

    def test_non_string_key_rejected(self):
        with self.assertRaises(ValueError):
            normalize_key(7, "substrate")


class FinishCategoryTests(unittest.TestCase):
    def test_paint_family_is_a_paint_system(self):
        self.assertEqual(finish_category("thermal-control-paint"), "paint-system")

    def test_anodising_is_a_surface_treatment(self):
        self.assertEqual(finish_category("Anodising"), "surface-treatment")

    def test_unlisted_family_is_unknown(self):
        self.assertEqual(finish_category("plasma-sprayed-ceramic"), "unknown")


class LayerNormalisationTests(unittest.TestCase):
    def test_layer_band_derived_from_tolerance(self):
        rec = normalize_layer(PRIMER)
        self.assertAlmostEqual(rec["min_dft_um"], 15.0)
        self.assertAlmostEqual(rec["max_dft_um"], 25.0)

    def test_organic_binder_flagged(self):
        self.assertTrue(normalize_layer(PRIMER)["organic"])
        self.assertIn("epoxy", ORGANIC_BINDERS)

    def test_inorganic_binder_not_flagged_organic(self):
        rec = normalize_layer(dict(PRIMER, binder="potassium-silicate"))
        self.assertFalse(rec["organic"])

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            normalize_layer(dict(PRIMER, role="sealer"))

    def test_missing_thickness_rejected(self):
        bad = {"role": "primer", "binder": "epoxy"}
        with self.assertRaises(ValueError):
            normalize_layer(bad)

    def test_minus_tolerance_removing_the_layer_rejected(self):
        with self.assertRaises(ValueError):
            normalize_layer(dict(PRIMER, minus_tolerance_um=20.0))

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            normalize_layer(dict(PRIMER, plus_tolerance_um=-1.0))

    def test_empty_stack_rejected(self):
        with self.assertRaises(ValueError):
            normalize_stack([])

    def test_roles_are_ordered_primer_first(self):
        self.assertEqual(LAYER_ROLES[0], "primer")
        self.assertEqual(LAYER_ROLES[-1], "topcoat")


class StackFindingTests(unittest.TestCase):
    def test_well_formed_stack_has_no_findings(self):
        self.assertEqual(stack_findings([PRIMER, TOPCOAT], "aluminium-alloy"), [])

    def test_inverted_stack_reported(self):
        self.assertIn(
            "layers-out-of-order", stack_findings([TOPCOAT, PRIMER], "aluminium-alloy")
        )

    def test_repeated_role_reported(self):
        found = stack_findings([PRIMER, dict(PRIMER), TOPCOAT], "aluminium-alloy")
        self.assertIn("repeated-primer-layer", found)

    def test_topcoat_straight_on_metal_reported(self):
        found = stack_findings([TOPCOAT], "titanium-alloy")
        self.assertIn("topcoat-on-unprimed-metallic-substrate", found)

    def test_topcoat_on_laminate_is_not_that_finding(self):
        found = stack_findings([TOPCOAT], "cfrp-laminate")
        self.assertNotIn("topcoat-on-unprimed-metallic-substrate", found)

    def test_all_inorganic_stack_reported(self):
        found = stack_findings(
            [dict(PRIMER, binder="potassium-silicate")], "cfrp-laminate"
        )
        self.assertIn("no-organic-binder-layer", found)

    def test_unrecognised_substrate_reported(self):
        found = stack_findings([PRIMER, TOPCOAT], "beryllium-billet")
        self.assertIn("unrecognised-substrate", found)

    def test_metallic_substrate_list_is_populated(self):
        self.assertIn("aluminium-alloy", METALLIC_SUBSTRATES)


class BuildTests(unittest.TestCase):
    def test_band_sums_every_layer(self):
        band = total_dft_um([PRIMER, TOPCOAT])
        self.assertAlmostEqual(band["min_um"], 65.0)
        self.assertAlmostEqual(band["nominal_um"], 80.0)
        self.assertAlmostEqual(band["max_um"], 105.0)

    def test_build_under_limit_passes(self):
        self.assertTrue(build_within_limit(total_dft_um([PRIMER, TOPCOAT]), 130.0))

    def test_build_over_limit_fails(self):
        self.assertFalse(build_within_limit(total_dft_um([PRIMER, TOPCOAT]), 90.0))

    def test_build_exactly_at_limit_passes(self):
        band = total_dft_um([PRIMER, TOPCOAT])
        self.assertTrue(build_within_limit(band, band["max_um"]))

    def test_representation_error_at_the_limit_is_absorbed(self):
        band = total_dft_um([PRIMER, TOPCOAT])
        nudged = band["max_um"] - DFT_TOLERANCE_UM / 2.0
        self.assertTrue(build_within_limit(band, nudged))

    def test_band_requires_a_mapping(self):
        with self.assertRaises(ValueError):
            build_within_limit(100.0, 120.0)


class DispositionTests(unittest.TestCase):
    def test_clean_paint_system_is_in_scope(self):
        out = assess_applicability(item())
        self.assertEqual(out["disposition"], "in-scope")
        self.assertEqual(out["findings"], [])

    def test_surface_treatment_is_out_of_scope(self):
        out = assess_applicability(item(finish_family="electroplating", layers=[]))
        self.assertEqual(out["disposition"], "out-of-scope")
        self.assertIn("finish-is-a-surface-treatment", out["findings"])

    def test_unknown_family_is_an_incomplete_declaration(self):
        out = assess_applicability(item(finish_family="mystery-coat", layers=[]))
        self.assertEqual(out["disposition"], "incomplete-declaration")

    def test_unrecognised_substrate_blocks_the_scope_call(self):
        out = assess_applicability(item(substrate="beryllium-billet"))
        self.assertEqual(out["disposition"], "incomplete-declaration")

    def test_over_limit_build_is_reported_as_a_finding(self):
        out = assess_applicability(item(max_build_um=90.0))
        self.assertIn("worst-case-build-over-limit", out["findings"])

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_applicability({"finish_family": "single-coat-paint"})

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            assess_applicability(["single-coat-paint"])

    def test_every_disposition_is_a_declared_one(self):
        for spec in (item(), item(finish_family="anodising", layers=[]),
                     item(finish_family="mystery-coat", layers=[])):
            self.assertIn(assess_applicability(spec)["disposition"], DISPOSITIONS)


if __name__ == "__main__":
    unittest.main()
