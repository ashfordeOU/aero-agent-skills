"""Contract tests for the clause 7.2.2 mask-set design-variation logic."""

import unittest

from q6012_design_variation_handling_logic import (
    MIN_SITES_PER_VARIANT,
    assess_mask_set,
    baseline_findings,
    build_variant_set,
    derivation_chain,
    duplicate_markings,
    marking_gaps,
    normalise_option,
    occupied_area_mm2,
    process_option_conflict,
    site_shortfalls,
    validate_variant,
)


def variant(identifier, baseline=None, option="standard-phemt",
            marking=None, sites=8, area=4.0):
    return {
        "id": identifier,
        "baseline": baseline,
        "process_option": option,
        "marking": marking if marking is not None else identifier.lower(),
        "sites": sites,
        "die_area_mm2": area,
    }


def full_set():
    return [
        variant("V0"),
        variant("V1", baseline="V0"),
        variant("V2", baseline="V1"),
        variant("V3", baseline="V0"),
    ]


class NormaliseOptionTests(unittest.TestCase):
    def test_lowercases_and_hyphenates(self):
        self.assertEqual(normalise_option("Standard pHEMT"), "standard-phemt")

    def test_underscores_become_hyphens(self):
        self.assertEqual(normalise_option("thick_metal"), "thick-metal")

    def test_empty_option_rejected(self):
        with self.assertRaises(ValueError):
            normalise_option("  ")

    def test_non_string_option_rejected(self):
        with self.assertRaises(ValueError):
            normalise_option(3)


class ValidateVariantTests(unittest.TestCase):
    def test_returns_canonical_record(self):
        record = validate_variant(variant("V1", option="Thick Metal"))
        self.assertEqual(record["process_option"], "thick-metal")
        self.assertEqual(record["sites"], 8)

    def test_absent_baseline_marks_a_root(self):
        self.assertIsNone(validate_variant(variant("V0"))["baseline"])

    def test_self_derivation_rejected(self):
        with self.assertRaises(ValueError):
            validate_variant(variant("V1", baseline="V1"))

    def test_blank_marking_becomes_none(self):
        self.assertIsNone(validate_variant(variant("V1", marking="   "))["marking"])

    def test_zero_sites_rejected(self):
        with self.assertRaises(ValueError):
            validate_variant(variant("V1", sites=0))

    def test_non_integer_sites_rejected(self):
        with self.assertRaises(ValueError):
            validate_variant(variant("V1", sites=8.0))

    def test_boolean_sites_rejected(self):
        with self.assertRaises(ValueError):
            validate_variant(variant("V1", sites=True))

    def test_zero_die_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_variant(variant("V1", area=0.0))

    def test_non_finite_die_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_variant(variant("V1", area=float("inf")))

    def test_missing_key_rejected(self):
        bad = variant("V1")
        del bad["process_option"]
        with self.assertRaises(ValueError):
            validate_variant(bad)

    def test_non_mapping_variant_rejected(self):
        with self.assertRaises(ValueError):
            validate_variant(["V1"])


class BuildVariantSetTests(unittest.TestCase):
    def test_builds_every_declared_variant(self):
        self.assertEqual(len(build_variant_set(full_set())), 4)

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            build_variant_set([variant("V1"), variant("V1", marking="other")])

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            build_variant_set([])


class DerivationTests(unittest.TestCase):
    def test_root_chain_is_itself(self):
        self.assertEqual(derivation_chain(build_variant_set(full_set()), "V0"), ["V0"])

    def test_chain_walks_back_to_the_root(self):
        self.assertEqual(
            derivation_chain(build_variant_set(full_set()), "V2"), ["V2", "V1", "V0"]
        )

    def test_undeclared_baseline_rejected(self):
        records = build_variant_set([variant("V1", baseline="V9")])
        with self.assertRaises(ValueError):
            derivation_chain(records, "V1")

    def test_unknown_variant_rejected(self):
        with self.assertRaises(ValueError):
            derivation_chain(build_variant_set(full_set()), "V9")

    def test_derivation_loop_rejected(self):
        records = build_variant_set(
            [variant("VA", baseline="VB"), variant("VB", baseline="VA")]
        )
        with self.assertRaises(ValueError):
            derivation_chain(records, "VA")

    def test_clean_set_has_no_baseline_finding(self):
        self.assertEqual(baseline_findings(build_variant_set(full_set())), [])

    def test_baseline_finding_names_the_variant(self):
        records = build_variant_set(full_set() + [variant("V4", baseline="V9")])
        self.assertEqual([item[0] for item in baseline_findings(records)], ["V4"])


class ProcessOptionTests(unittest.TestCase):
    def test_single_option_never_conflicts(self):
        self.assertEqual(process_option_conflict(build_variant_set(full_set())), [])

    def test_two_options_conflict_without_a_compatible_group(self):
        records = build_variant_set(full_set() + [variant("V4", option="thick-metal")])
        self.assertEqual(
            process_option_conflict(records), ["standard-phemt", "thick-metal"]
        )

    def test_declared_compatible_group_clears_the_conflict(self):
        records = build_variant_set(full_set() + [variant("V4", option="thick-metal")])
        self.assertEqual(
            process_option_conflict(records, [["standard-phemt", "Thick Metal"]]), []
        )

    def test_partial_compatible_group_still_conflicts(self):
        records = build_variant_set(
            full_set()
            + [variant("V4", option="thick-metal"), variant("V5", option="back-via")]
        )
        self.assertEqual(
            process_option_conflict(records, [["standard-phemt", "thick-metal"]]),
            ["back-via", "standard-phemt", "thick-metal"],
        )

    def test_malformed_compatible_group_rejected(self):
        records = build_variant_set(full_set())
        with self.assertRaises(ValueError):
            process_option_conflict(records, ["standard-phemt"])


class MarkingTests(unittest.TestCase):
    def test_clean_set_has_no_marking_gap(self):
        self.assertEqual(marking_gaps(build_variant_set(full_set())), [])

    def test_unmarked_variant_named(self):
        variants = full_set()
        variants[1]["marking"] = None
        self.assertEqual(marking_gaps(build_variant_set(variants)), ["V1"])

    def test_shared_marking_reported(self):
        variants = full_set()
        variants[2]["marking"] = variants[1]["marking"]
        self.assertEqual(duplicate_markings(build_variant_set(variants)), ["v1"])

    def test_unmarked_variants_do_not_count_as_duplicates(self):
        variants = full_set()
        variants[1]["marking"] = None
        variants[2]["marking"] = None
        self.assertEqual(duplicate_markings(build_variant_set(variants)), [])


class SiteCountTests(unittest.TestCase):
    def test_clean_set_meets_the_minimum(self):
        self.assertEqual(site_shortfalls(build_variant_set(full_set())), [])

    def test_shortfall_reported_with_its_count(self):
        variants = full_set()
        variants[3]["sites"] = 2
        self.assertEqual(site_shortfalls(build_variant_set(variants)), [("V3", 2)])

    def test_site_count_exactly_at_the_minimum_is_not_a_shortfall(self):
        variants = full_set()
        variants[0]["sites"] = MIN_SITES_PER_VARIANT
        self.assertEqual(site_shortfalls(build_variant_set(variants)), [])

    def test_minimum_can_be_raised_for_a_qualification_lot(self):
        records = build_variant_set(full_set())
        self.assertEqual(len(site_shortfalls(records, minimum_sites=10)), 4)

    def test_non_integer_minimum_rejected(self):
        with self.assertRaises(ValueError):
            site_shortfalls(build_variant_set(full_set()), minimum_sites=5.0)

    def test_zero_minimum_rejected(self):
        with self.assertRaises(ValueError):
            site_shortfalls(build_variant_set(full_set()), minimum_sites=0)


class AreaTests(unittest.TestCase):
    def test_area_is_sites_times_die_area_summed(self):
        self.assertAlmostEqual(
            occupied_area_mm2(build_variant_set(full_set())), 4 * 8 * 4.0, places=9
        )

    def test_area_tracks_a_changed_site_count(self):
        variants = full_set()
        variants[0]["sites"] = 16
        self.assertAlmostEqual(
            occupied_area_mm2(build_variant_set(variants)), (16 + 8 + 8 + 8) * 4.0,
            places=9,
        )


class AssessMaskSetTests(unittest.TestCase):
    def _spec(self, **kwargs):
        spec = {"variants": full_set(), "reticle_field_area_mm2": 200.0}
        spec.update(kwargs)
        return spec

    def test_clean_mask_set_is_releasable(self):
        result = assess_mask_set(self._spec())
        self.assertTrue(result["releasable"])
        self.assertEqual(result["findings"], [])

    def test_area_utilisation_reported(self):
        result = assess_mask_set(self._spec())
        self.assertAlmostEqual(result["area_utilisation"], 128.0 / 200.0, places=9)

    def test_area_exactly_at_the_budget_is_absorbed(self):
        result = assess_mask_set(self._spec(reticle_field_area_mm2=128.0))
        self.assertAlmostEqual(result["occupied_area_mm2"], 128.0, places=9)
        self.assertTrue(result["releasable"])

    def test_area_over_the_budget_blocks_release(self):
        result = assess_mask_set(self._spec(reticle_field_area_mm2=100.0))
        self.assertFalse(result["releasable"])
        self.assertTrue(any("reticle field" in f for f in result["findings"]))

    def test_undeclared_baseline_blocks_release(self):
        variants = full_set() + [variant("V4", baseline="V9")]
        result = assess_mask_set(self._spec(variants=variants))
        self.assertFalse(result["releasable"])
        self.assertEqual([item[0] for item in result["baseline_findings"]], ["V4"])

    def test_derivation_loop_blocks_release(self):
        variants = [variant("VA", baseline="VB"), variant("VB", baseline="VA")]
        result = assess_mask_set(self._spec(variants=variants))
        self.assertFalse(result["releasable"])
        self.assertEqual(len(result["baseline_findings"]), 2)

    def test_process_option_conflict_blocks_release(self):
        variants = full_set() + [variant("V4", option="back-via")]
        result = assess_mask_set(self._spec(variants=variants))
        self.assertFalse(result["releasable"])
        self.assertEqual(result["process_option_conflict"], ["back-via", "standard-phemt"])

    def test_compatible_group_lets_two_options_share_the_wafer(self):
        variants = full_set() + [variant("V4", option="back-via")]
        result = assess_mask_set(
            self._spec(
                variants=variants,
                compatible_process_groups=[["standard-phemt", "back-via"]],
            )
        )
        self.assertEqual(result["process_option_conflict"], [])
        self.assertTrue(result["releasable"])

    def test_unmarked_variant_blocks_release(self):
        variants = full_set()
        variants[0]["marking"] = None
        result = assess_mask_set(self._spec(variants=variants))
        self.assertFalse(result["releasable"])
        self.assertEqual(result["unmarked_variants"], ["V0"])

    def test_shared_marking_blocks_release(self):
        variants = full_set()
        variants[3]["marking"] = variants[0]["marking"]
        result = assess_mask_set(self._spec(variants=variants))
        self.assertFalse(result["releasable"])
        self.assertEqual(result["duplicate_markings"], ["v0"])

    def test_site_shortfall_blocks_release(self):
        variants = full_set()
        variants[2]["sites"] = 1
        result = assess_mask_set(self._spec(variants=variants))
        self.assertFalse(result["releasable"])
        self.assertEqual(result["site_shortfalls"], [("V2", 1)])

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_mask_set({"variants": full_set()})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_mask_set(["variants"])

    def test_non_positive_reticle_budget_rejected(self):
        with self.assertRaises(ValueError):
            assess_mask_set(self._spec(reticle_field_area_mm2=0.0))

    def test_several_defects_are_reported_together(self):
        variants = full_set()
        variants[0]["marking"] = None
        variants[1]["sites"] = 1
        variants.append(variant("V4", option="back-via"))
        result = assess_mask_set(self._spec(variants=variants))
        self.assertFalse(result["releasable"])
        self.assertGreaterEqual(len(result["findings"]), 3)


if __name__ == "__main__":
    unittest.main()
