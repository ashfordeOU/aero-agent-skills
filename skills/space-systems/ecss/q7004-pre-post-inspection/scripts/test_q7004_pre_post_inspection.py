"""Contract tests for the ECSS-Q-ST-70-04C pre-test and post-test inspection logic."""

import unittest

from q7004_pre_post_inspection_logic import (
    COMPARISON_TOLERANCE,
    CRITICAL_DEFECT_KINDS,
    DEFECT_KINDS,
    assess_pre_post_inspection,
    defect_comparison,
    dimension_comparison,
    disposition_for,
    index_defects,
    mass_change_fraction,
    performance_degradation,
    validate_defect,
)

PRE_DIMENSIONS = {"flange_flatness_mm": 0.050, "bore_diameter_mm": 25.000}
POST_DIMENSIONS = {"flange_flatness_mm": 0.058, "bore_diameter_mm": 25.004}
TOLERANCES = {"flange_flatness_mm": 0.020, "bore_diameter_mm": 0.010}

PRE_DEFECTS = [
    {"id": "D-01", "kind": "discolouration", "size_mm": 2.0, "location": "web"},
]
POST_DEFECTS = [
    {"id": "D-01", "kind": "discolouration", "size_mm": 2.1, "location": "web"},
]


def spec(**overrides):
    base = {
        "pre_dimensions": dict(PRE_DIMENSIONS),
        "post_dimensions": dict(POST_DIMENSIONS),
        "dimension_tolerances": dict(TOLERANCES),
        "pre_defects": [dict(d) for d in PRE_DEFECTS],
        "post_defects": [dict(d) for d in POST_DEFECTS],
        "defect_growth_tolerance_mm": 0.5,
        "pre_mass_g": 480.0,
        "post_mass_g": 479.9,
        "allowable_mass_loss_fraction": 0.001,
        "performance": {
            "insertion_loss_db": {"pre": 0.40, "post": 0.41, "allowable_fraction": 0.05}
        },
    }
    base.update(overrides)
    return base


class DefectRecordTests(unittest.TestCase):
    def test_valid_defect_is_normalised(self):
        record = validate_defect({"id": " D-02 ", "kind": "crack", "size_mm": 1})
        self.assertEqual(record["id"], "D-02")
        self.assertAlmostEqual(record["size_mm"], 1.0, places=12)

    def test_location_defaults_to_unrecorded(self):
        record = validate_defect({"id": "D-02", "kind": "crack", "size_mm": 1.0})
        self.assertEqual(record["location"], "unrecorded")

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_defect({"id": "D-02", "kind": "smudge", "size_mm": 1.0})

    def test_negative_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_defect({"id": "D-02", "kind": "crack", "size_mm": -1.0})

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_defect({"id": "  ", "kind": "crack", "size_mm": 1.0})

    def test_duplicate_identifier_rejected(self):
        register = [
            {"id": "D-01", "kind": "crack", "size_mm": 1.0},
            {"id": "D-01", "kind": "crack", "size_mm": 2.0},
        ]
        with self.assertRaises(ValueError):
            index_defects(register)

    def test_critical_kinds_are_a_subset_of_the_kinds(self):
        self.assertTrue(set(CRITICAL_DEFECT_KINDS).issubset(set(DEFECT_KINDS)))


class DimensionTests(unittest.TestCase):
    def test_small_movement_is_within_tolerance(self):
        results = dimension_comparison(PRE_DIMENSIONS, POST_DIMENSIONS, TOLERANCES)
        self.assertTrue(all(r["within_tolerance"] for r in results))

    def test_distortion_is_the_absolute_difference(self):
        results = dimension_comparison(PRE_DIMENSIONS, POST_DIMENSIONS, TOLERANCES)
        flatness = [r for r in results if r["dimension"] == "flange_flatness_mm"][0]
        self.assertAlmostEqual(flatness["distortion_mm"], 0.008, places=9)

    def test_distortion_exactly_on_the_tolerance_is_accepted(self):
        post = {"flange_flatness_mm": 0.070, "bore_diameter_mm": 25.000}
        results = dimension_comparison(PRE_DIMENSIONS, post, TOLERANCES)
        flatness = [r for r in results if r["dimension"] == "flange_flatness_mm"][0]
        self.assertTrue(flatness["within_tolerance"])
        self.assertLessEqual(
            flatness["distortion_mm"] - flatness["tolerance_mm"], COMPARISON_TOLERANCE
        )

    def test_excess_distortion_is_refused(self):
        post = {"flange_flatness_mm": 0.200, "bore_diameter_mm": 25.000}
        results = dimension_comparison(PRE_DIMENSIONS, post, TOLERANCES)
        flatness = [r for r in results if r["dimension"] == "flange_flatness_mm"][0]
        self.assertFalse(flatness["within_tolerance"])

    def test_dimension_missing_after_the_test_is_not_a_pass(self):
        results = dimension_comparison(PRE_DIMENSIONS, {"bore_diameter_mm": 25.0}, TOLERANCES)
        flatness = [r for r in results if r["dimension"] == "flange_flatness_mm"][0]
        self.assertFalse(flatness["measured_both"])
        self.assertFalse(flatness["within_tolerance"])

    def test_empty_tolerance_set_rejected(self):
        with self.assertRaises(ValueError):
            dimension_comparison(PRE_DIMENSIONS, POST_DIMENSIONS, {})

    def test_non_mapping_dimensions_rejected(self):
        with self.assertRaises(ValueError):
            dimension_comparison(["flange"], POST_DIMENSIONS, TOLERANCES)


class DefectComparisonTests(unittest.TestCase):
    def test_small_growth_is_not_reported(self):
        result = defect_comparison(PRE_DEFECTS, POST_DEFECTS, 0.5)
        self.assertEqual(result["grown"], [])
        self.assertEqual(len(result["unchanged"]), 1)

    def test_growth_exactly_on_the_tolerance_is_not_growth(self):
        post = [{"id": "D-01", "kind": "discolouration", "size_mm": 2.5}]
        result = defect_comparison(PRE_DEFECTS, post, 0.5)
        self.assertEqual(result["grown"], [])

    def test_growth_beyond_the_tolerance_is_reported(self):
        post = [{"id": "D-01", "kind": "discolouration", "size_mm": 4.0}]
        result = defect_comparison(PRE_DEFECTS, post, 0.5)
        self.assertEqual(len(result["grown"]), 1)
        self.assertAlmostEqual(result["grown"][0]["growth_mm"], 2.0, places=9)

    def test_new_defect_is_reported(self):
        post = POST_DEFECTS + [{"id": "D-02", "kind": "coating-loss", "size_mm": 3.0}]
        result = defect_comparison(PRE_DEFECTS, post, 0.5)
        self.assertEqual([r["id"] for r in result["new"]], ["D-02"])

    def test_new_crack_is_grouped_as_critical(self):
        post = POST_DEFECTS + [{"id": "D-03", "kind": "crack", "size_mm": 1.0}]
        result = defect_comparison(PRE_DEFECTS, post, 0.5)
        self.assertEqual([r["id"] for r in result["critical"]], ["D-03"])

    def test_grown_delamination_is_grouped_as_critical(self):
        pre = [{"id": "D-04", "kind": "delamination", "size_mm": 1.0}]
        post = [{"id": "D-04", "kind": "delamination", "size_mm": 5.0}]
        result = defect_comparison(pre, post, 0.5)
        self.assertEqual([r["id"] for r in result["critical"]], ["D-04"])

    def test_defect_absent_afterwards_is_unaccounted(self):
        result = defect_comparison(PRE_DEFECTS, [], 0.5)
        self.assertEqual([r["id"] for r in result["unaccounted"]], ["D-01"])

    def test_negative_growth_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            defect_comparison(PRE_DEFECTS, POST_DEFECTS, -0.1)


class MassAndPerformanceTests(unittest.TestCase):
    def test_mass_loss_is_negative(self):
        self.assertAlmostEqual(mass_change_fraction(100.0, 99.0), -0.01, places=9)

    def test_mass_gain_is_positive(self):
        self.assertAlmostEqual(mass_change_fraction(100.0, 101.0), 0.01, places=9)

    def test_zero_pre_mass_rejected(self):
        with self.assertRaises(ValueError):
            mass_change_fraction(0.0, 99.0)

    def test_negative_post_mass_rejected(self):
        with self.assertRaises(ValueError):
            mass_change_fraction(100.0, -1.0)

    def test_degradation_is_signless(self):
        self.assertAlmostEqual(performance_degradation(0.40, 0.36), 0.1, places=9)

    def test_degradation_against_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            performance_degradation(0.0, 0.36)


class DispositionTests(unittest.TestCase):
    def test_nothing_found_accepts(self):
        self.assertEqual(disposition_for([], []), "accept")

    def test_reviewable_only_reviews(self):
        self.assertEqual(disposition_for([], ["mass loss"]), "review")

    def test_blocking_rejects_even_with_reviewables(self):
        self.assertEqual(disposition_for(["crack"], ["mass loss"]), "reject")

    def test_non_sequence_group_rejected(self):
        with self.assertRaises(ValueError):
            disposition_for(None, [])


class AssessmentTests(unittest.TestCase):
    def test_clean_item_is_accepted(self):
        result = assess_pre_post_inspection(spec())
        self.assertEqual(result["disposition"], "accept")
        self.assertEqual(result["findings"], [])

    def test_mass_loss_fraction_is_positive_for_a_loss(self):
        result = assess_pre_post_inspection(spec())
        self.assertGreater(result["mass_loss_fraction"], 0.0)
        self.assertLess(result["mass_change_fraction"], 0.0)

    def test_mass_gain_never_counts_as_loss(self):
        result = assess_pre_post_inspection(spec(post_mass_g=481.0))
        self.assertAlmostEqual(result["mass_loss_fraction"], 0.0, places=12)
        self.assertTrue(result["mass_within_allowance"])

    def test_excess_mass_loss_sends_the_item_to_review(self):
        result = assess_pre_post_inspection(spec(post_mass_g=470.0))
        self.assertEqual(result["disposition"], "review")
        self.assertTrue(any("mass loss" in f for f in result["findings"]))

    def test_new_crack_rejects_the_item(self):
        post = POST_DEFECTS + [{"id": "D-09", "kind": "crack", "size_mm": 1.5}]
        result = assess_pre_post_inspection(spec(post_defects=post))
        self.assertEqual(result["disposition"], "reject")

    def test_distortion_beyond_tolerance_rejects_the_item(self):
        result = assess_pre_post_inspection(
            spec(post_dimensions={"flange_flatness_mm": 0.30, "bore_diameter_mm": 25.004})
        )
        self.assertEqual(result["disposition"], "reject")
        self.assertTrue(any("moved" in f for f in result["findings"]))

    def test_new_coating_loss_only_sends_the_item_to_review(self):
        post = POST_DEFECTS + [{"id": "D-07", "kind": "coating-loss", "size_mm": 4.0}]
        result = assess_pre_post_inspection(spec(post_defects=post))
        self.assertEqual(result["disposition"], "review")

    def test_performance_degradation_beyond_allowance_reviews(self):
        performance = {
            "insertion_loss_db": {"pre": 0.40, "post": 0.60, "allowable_fraction": 0.05}
        }
        result = assess_pre_post_inspection(spec(performance=performance))
        self.assertEqual(result["disposition"], "review")
        self.assertTrue(any("degraded" in f for f in result["findings"]))

    def test_degradation_exactly_on_the_allowance_is_acceptable(self):
        performance = {
            "insertion_loss_db": {"pre": 0.40, "post": 0.42, "allowable_fraction": 0.05}
        }
        result = assess_pre_post_inspection(spec(performance=performance))
        self.assertEqual(result["disposition"], "accept")
        entry = result["performance"][0]
        self.assertAlmostEqual(entry["degradation"], entry["allowable_fraction"], places=9)

    def test_vanished_pre_test_defect_is_reviewed(self):
        result = assess_pre_post_inspection(spec(post_defects=[]))
        self.assertEqual(result["disposition"], "review")
        self.assertTrue(any("absent afterwards" in f for f in result["findings"]))

    def test_performance_block_is_optional(self):
        base = spec()
        del base["performance"]
        result = assess_pre_post_inspection(base)
        self.assertEqual(result["performance"], [])
        self.assertEqual(result["disposition"], "accept")

    def test_missing_spec_key_rejected(self):
        bad = spec()
        del bad["pre_mass_g"]
        with self.assertRaises(ValueError):
            assess_pre_post_inspection(bad)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_pre_post_inspection("inspection")

    def test_malformed_performance_entry_rejected(self):
        with self.assertRaises(ValueError):
            assess_pre_post_inspection(spec(performance={"loss": {"pre": 1.0}}))


if __name__ == "__main__":
    unittest.main()
