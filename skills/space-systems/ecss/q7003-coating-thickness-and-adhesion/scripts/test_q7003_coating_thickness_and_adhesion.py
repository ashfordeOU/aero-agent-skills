#!/usr/bin/env python3
"""Contract test for anodized coating quality verification (offline)."""

import copy
import unittest

from q7003_coating_thickness_and_adhesion_logic import (
    ADHESION_OUTCOMES,
    VERDICT_ACCEPT,
    VERDICT_REJECT,
    VERDICT_REVIEW,
    evaluate_adhesion,
    evaluate_colour_uniformity,
    evaluate_coverage,
    evaluate_thickness,
    verify_coating,
)

GOOD_CASE = {
    "readings_um": [16.0, 17.5, 18.2, 16.9],
    "min_um": 15.0,
    "max_um": 20.0,
    "total_area_mm2": 4000.0,
    "masked_area_mm2": 200.0,
    "uncoated_area_mm2": 0.0,
    "max_uncoated_fraction": 0.001,
    "adhesion_outcome": "no-separation",
    "part_form": "flat",
    "colour_samples": [52.0, 52.4, 51.7],
    "colour_reference": 52.0,
    "colour_tolerance": 1.0,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class ThicknessTests(unittest.TestCase):
    def test_all_readings_in_band_accept(self):
        result = evaluate_thickness([16.0, 17.0, 18.0], 15.0, 20.0)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["in_band"], 3)
        self.assertEqual(result["findings"], [])

    def test_reading_exactly_on_the_minimum_is_in_band(self):
        # 0.1 + 0.2 lands one unit in the last place above 0.3, and the
        # same representation error reaches a converted thickness reading.
        edge = 15.0 + (0.1 + 0.2 - 0.3)
        result = evaluate_thickness([edge], 15.0, 20.0)
        self.assertEqual(result["below_minimum"], 0)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_reading_exactly_on_the_maximum_is_in_band(self):
        result = evaluate_thickness([20.0], 15.0, 20.0)
        self.assertEqual(result["above_maximum"], 0)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_thin_reading_rejects_and_is_counted(self):
        result = evaluate_thickness([16.0, 12.0, 18.0], 15.0, 20.0)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertEqual(result["below_minimum"], 1)
        self.assertTrue(any("minimum" in f for f in result["findings"]))

    def test_thick_reading_rejects_too(self):
        result = evaluate_thickness([16.0, 24.0], 15.0, 20.0)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertEqual(result["above_maximum"], 1)

    def test_statistics_are_reported(self):
        result = evaluate_thickness([16.0, 18.0, 20.0], 15.0, 21.0)
        self.assertAlmostEqual(result["mean_um"], 18.0, places=9)
        self.assertAlmostEqual(result["min_um"], 16.0, places=9)
        self.assertAlmostEqual(result["max_um"], 20.0, places=9)

    def test_empty_reading_set_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_thickness([], 15.0, 20.0)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_thickness([16.0], 20.0, 15.0)

    def test_non_numeric_reading_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_thickness([16.0, "17 um"], 15.0, 20.0)

    def test_negative_reading_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_thickness([-1.0], 15.0, 20.0)


class CoverageTests(unittest.TestCase):
    def test_fully_coated_graded_area_accepts(self):
        result = evaluate_coverage(1000.0, masked_area_mm2=100.0)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)
        self.assertAlmostEqual(result["graded_area_mm2"], 900.0, places=9)

    def test_masking_is_removed_from_the_graded_area(self):
        result = evaluate_coverage(
            1000.0, masked_area_mm2=500.0, uncoated_area_mm2=5.0,
            max_uncoated_fraction=0.02,
        )
        self.assertAlmostEqual(result["uncoated_fraction"], 0.01, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_uncoated_fraction_exactly_on_the_allowance_accepts(self):
        result = evaluate_coverage(
            1000.0, uncoated_area_mm2=10.0, max_uncoated_fraction=0.01
        )
        self.assertAlmostEqual(result["uncoated_fraction"], 0.01, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_bare_area_beyond_the_allowance_rejects(self):
        result = evaluate_coverage(
            1000.0, uncoated_area_mm2=50.0, max_uncoated_fraction=0.01
        )
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(result["findings"])

    def test_masking_consuming_the_surface_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_coverage(1000.0, masked_area_mm2=1000.0)

    def test_uncoated_area_above_the_graded_area_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_coverage(1000.0, masked_area_mm2=900.0, uncoated_area_mm2=200.0)

    def test_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_coverage(1000.0, max_uncoated_fraction=1.5)

    def test_zero_total_area_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_coverage(0.0)


class AdhesionTests(unittest.TestCase):
    def test_intact_coating_accepts(self):
        self.assertEqual(
            evaluate_adhesion("no-separation")["verdict"], VERDICT_ACCEPT
        )

    def test_crazing_on_a_formed_part_is_a_review(self):
        result = evaluate_adhesion("crazing-only", part_form="formed")
        self.assertEqual(result["verdict"], VERDICT_REVIEW)
        self.assertTrue(any("forming radius" in f for f in result["findings"]))

    def test_crazing_on_a_flat_part_rejects(self):
        result = evaluate_adhesion("crazing-only", part_form="flat")
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_flaking_and_detachment_both_reject(self):
        for outcome in ("flaking", "detachment"):
            self.assertEqual(
                evaluate_adhesion(outcome, part_form="formed")["verdict"],
                VERDICT_REJECT,
            )

    def test_every_grouped_outcome_is_handled(self):
        for outcome in ADHESION_OUTCOMES:
            self.assertIn(
                evaluate_adhesion(outcome)["verdict"],
                (VERDICT_ACCEPT, VERDICT_REVIEW, VERDICT_REJECT),
            )

    def test_unknown_outcome_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_adhesion("looked-fine")

    def test_unknown_part_form_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_adhesion("no-separation", part_form="welded")


class ColourTests(unittest.TestCase):
    def test_tight_sample_accepts(self):
        result = evaluate_colour_uniformity([52.0, 52.2, 51.9], 52.0, 1.0)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertAlmostEqual(result["max_deviation"], 0.2, places=9)

    def test_deviation_exactly_on_the_tolerance_accepts(self):
        result = evaluate_colour_uniformity([53.0], 52.0, 1.0)
        self.assertAlmostEqual(result["max_deviation"], 1.0, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_wide_sample_rejects(self):
        result = evaluate_colour_uniformity([52.0, 56.0], 52.0, 1.0)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(result["findings"])

    def test_spread_is_reported_independently_of_the_reference(self):
        result = evaluate_colour_uniformity([50.0, 54.0], 52.0, 5.0)
        self.assertAlmostEqual(result["spread"], 4.0, places=9)
        self.assertAlmostEqual(result["mean_deviation"], 2.0, places=9)

    def test_empty_sample_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_colour_uniformity([], 52.0, 1.0)

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_colour_uniformity([52.0], 52.0, -1.0)


class VerifyCoatingTests(unittest.TestCase):
    def test_good_batch_accepts(self):
        result = verify_coating(GOOD_CASE)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["driving_characteristics"], [])
        self.assertEqual(result["findings"], [])

    def test_thin_coating_drives_the_verdict(self):
        result = verify_coating(_case(readings_um=[16.0, 11.0]))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertEqual(result["driving_characteristics"], ["thickness"])

    def test_review_outcome_survives_when_nothing_rejects(self):
        result = verify_coating(
            _case(adhesion_outcome="crazing-only", part_form="formed")
        )
        self.assertEqual(result["verdict"], VERDICT_REVIEW)
        self.assertEqual(result["driving_characteristics"], ["adhesion"])

    def test_a_reject_outranks_a_review(self):
        result = verify_coating(
            _case(
                adhesion_outcome="crazing-only",
                part_form="formed",
                colour_samples=[52.0, 60.0],
            )
        )
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertEqual(result["driving_characteristics"], ["colour"])

    def test_two_failing_characteristics_are_both_named(self):
        result = verify_coating(
            _case(readings_um=[9.0], uncoated_area_mm2=400.0)
        )
        self.assertEqual(
            result["driving_characteristics"], ["coverage", "thickness"]
        )

    def test_findings_are_prefixed_by_characteristic(self):
        result = verify_coating(_case(readings_um=[9.0]))
        self.assertTrue(any(f.startswith("thickness:") for f in result["findings"]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            verify_coating("a good batch")

    def test_missing_colour_tolerance_rejected(self):
        case = _case()
        del case["colour_tolerance"]
        with self.assertRaises(ValueError):
            verify_coating(case)


if __name__ == "__main__":
    unittest.main()
