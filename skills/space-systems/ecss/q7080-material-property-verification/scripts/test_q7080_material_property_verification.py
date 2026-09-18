#!/usr/bin/env python3
"""Contract test for witness-coupon property verification (offline)."""

import copy
import unittest

from q7080_material_property_verification_logic import (
    BUILD_DIRECTION_ORIENTATION,
    ORIENTATIONS,
    VERDICT_ACCEPT,
    VERDICT_REJECT,
    VERDICT_REVIEW,
    anisotropy_ratio,
    assess_material_properties,
    grade_coupon,
    orientation_coverage,
    orientation_means,
    property_statistics,
    select_witness_coupons,
    validate_coupon,
)

BUILD_ID = "B-114"
LOT_ID = "HT-9"

MINIMA = {"uts_mpa": 900.0, "ys_mpa": 800.0, "elongation_pct": 6.0}


def coupon(identifier, orientation, uts, ys=880.0, elongation=9.0,
           build_id=BUILD_ID, lot=LOT_ID):
    return {
        "id": identifier,
        "orientation": orientation,
        "build_id": build_id,
        "heat_treat_lot": lot,
        "uts_mpa": uts,
        "ys_mpa": ys,
        "elongation_pct": elongation,
    }


COUPONS = [
    coupon("c1", "xy", 1050.0),
    coupon("c2", "xy", 1040.0),
    coupon("c3", "xy", 1060.0),
    coupon("c4", "xz", 1030.0),
    coupon("c5", "xz", 1020.0),
    coupon("c6", "xz", 1035.0),
    coupon("c7", "zx", 960.0),
    coupon("c8", "zx", 950.0),
    coupon("c9", "zx", 970.0),
]

GOOD_CASE = {
    "coupons": COUPONS,
    "build_id": BUILD_ID,
    "heat_treat_lot": LOT_ID,
    "minima": MINIMA,
    "min_per_orientation": 3,
    "min_anisotropy_ratio": 0.85,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class ValidateCouponTests(unittest.TestCase):
    def test_properties_come_back_as_floats(self):
        record = validate_coupon(coupon("c1", "xy", 1050))
        self.assertAlmostEqual(record["uts_mpa"], 1050.0, places=9)
        self.assertEqual(record["orientation"], "xy")

    def test_unknown_orientation_rejected(self):
        with self.assertRaises(ValueError):
            validate_coupon(coupon("c1", "diagonal", 1050.0))

    def test_missing_property_rejected(self):
        broken = coupon("c1", "xy", 1050.0)
        del broken["ys_mpa"]
        with self.assertRaises(ValueError):
            validate_coupon(broken)

    def test_non_positive_property_rejected(self):
        with self.assertRaises(ValueError):
            validate_coupon(coupon("c1", "xy", 0.0))

    def test_non_mapping_coupon_rejected(self):
        with self.assertRaises(ValueError):
            validate_coupon(["c1"])


class SelectionTests(unittest.TestCase):
    def test_coupons_of_this_build_and_lot_are_kept(self):
        selection = select_witness_coupons(COUPONS, BUILD_ID, LOT_ID)
        self.assertEqual(len(selection["accepted"]), 9)
        self.assertEqual(selection["excluded"], [])

    def test_coupon_from_another_build_is_excluded_by_name(self):
        mixed = COUPONS + [coupon("x1", "zx", 1100.0, build_id="B-115")]
        selection = select_witness_coupons(mixed, BUILD_ID, LOT_ID)
        self.assertEqual(len(selection["accepted"]), 9)
        self.assertEqual(selection["excluded"][0]["id"], "x1")

    def test_coupon_from_another_furnace_lot_is_excluded(self):
        mixed = COUPONS + [coupon("x2", "zx", 1100.0, lot="HT-10")]
        selection = select_witness_coupons(mixed, BUILD_ID, LOT_ID)
        self.assertIn("lot", selection["excluded"][0]["reason"])

    def test_batch_with_no_own_coupon_rejected(self):
        with self.assertRaises(ValueError):
            select_witness_coupons(COUPONS, "B-999", LOT_ID)

    def test_empty_coupon_set_rejected(self):
        with self.assertRaises(ValueError):
            select_witness_coupons([], BUILD_ID, LOT_ID)


class CoverageTests(unittest.TestCase):
    def _records(self, coupons=None):
        return select_witness_coupons(coupons or COUPONS, BUILD_ID, LOT_ID)["accepted"]

    def test_full_population_accepts(self):
        result = orientation_coverage(self._records())
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["counts"]["zx"], 3)

    def test_missing_build_direction_rejects(self):
        records = self._records([c for c in COUPONS if c["orientation"] != "zx"])
        result = orientation_coverage(records)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(
            any(BUILD_DIRECTION_ORIENTATION in text for text in result["findings"])
        )

    def test_thin_orientation_is_a_review(self):
        records = self._records([c for c in COUPONS if c["id"] != "c9"])
        result = orientation_coverage(records)
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_required_set_can_be_narrowed(self):
        records = self._records([c for c in COUPONS if c["orientation"] != "xz"])
        result = orientation_coverage(records, required_orientations=("xy", "zx"))
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_zero_minimum_per_orientation_rejected(self):
        with self.assertRaises(ValueError):
            orientation_coverage(self._records(), min_per_orientation=0)

    def test_unknown_required_orientation_rejected(self):
        with self.assertRaises(ValueError):
            orientation_coverage(self._records(), required_orientations=("yy",))


class GradeCouponTests(unittest.TestCase):
    def test_coupon_above_every_minimum_accepts(self):
        record = validate_coupon(coupon("c1", "xy", 1050.0))
        self.assertEqual(grade_coupon(record, MINIMA)["verdict"], VERDICT_ACCEPT)

    def test_coupon_exactly_on_a_minimum_accepts(self):
        record = validate_coupon(coupon("c1", "xy", 900.0))
        self.assertEqual(grade_coupon(record, MINIMA)["verdict"], VERDICT_ACCEPT)

    def test_coupon_below_a_minimum_rejects_and_names_the_property(self):
        record = validate_coupon(coupon("c1", "zx", 860.0))
        result = grade_coupon(record, MINIMA)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(any("uts_mpa" in text for text in result["findings"]))

    def test_low_elongation_alone_rejects(self):
        record = validate_coupon(coupon("c1", "zx", 1050.0, elongation=3.0))
        self.assertEqual(grade_coupon(record, MINIMA)["verdict"], VERDICT_REJECT)

    def test_unknown_property_in_the_minima_rejected(self):
        record = validate_coupon(coupon("c1", "xy", 1050.0))
        with self.assertRaises(ValueError):
            grade_coupon(record, {"hardness_hv": 300.0})

    def test_empty_minima_rejected(self):
        record = validate_coupon(coupon("c1", "xy", 1050.0))
        with self.assertRaises(ValueError):
            grade_coupon(record, {})


class StatisticsTests(unittest.TestCase):
    def test_mean_and_extremes(self):
        stats = property_statistics([1050.0, 1040.0, 1060.0])
        self.assertAlmostEqual(stats["mean"], 1050.0, places=9)
        self.assertAlmostEqual(stats["minimum"], 1040.0, places=9)
        self.assertAlmostEqual(stats["maximum"], 1060.0, places=9)

    def test_sample_standard_deviation(self):
        stats = property_statistics([1050.0, 1040.0, 1060.0])
        self.assertAlmostEqual(stats["std_dev"], 10.0, places=9)

    def test_single_value_has_no_spread(self):
        stats = property_statistics([1050.0])
        self.assertAlmostEqual(stats["std_dev"], 0.0, places=9)
        self.assertEqual(stats["count"], 1)

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            property_statistics([])

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            property_statistics([1050.0, "1040"])


class AnisotropyTests(unittest.TestCase):
    def _means(self):
        records = select_witness_coupons(COUPONS, BUILD_ID, LOT_ID)["accepted"]
        return orientation_means(records, "uts_mpa")

    def test_means_are_taken_per_orientation(self):
        means = self._means()
        self.assertAlmostEqual(means["xy"], 1050.0, places=9)
        self.assertAlmostEqual(means["zx"], 960.0, places=9)

    def test_unknown_property_rejected(self):
        records = select_witness_coupons(COUPONS, BUILD_ID, LOT_ID)["accepted"]
        with self.assertRaises(ValueError):
            orientation_means(records, "hardness_hv")

    def test_ratio_is_weakest_over_strongest(self):
        result = anisotropy_ratio(self._means(), 0.85)
        self.assertAlmostEqual(result["ratio"], 960.0 / 1050.0, places=9)
        self.assertEqual(result["weakest"], "zx")
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_ratio_exactly_on_the_floor_accepts(self):
        result = anisotropy_ratio({"zx": 850.0, "xy": 1000.0}, 0.85)
        self.assertAlmostEqual(result["ratio"], 0.85, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_collapsed_ratio_rejects(self):
        result = anisotropy_ratio(self._means(), 0.95)
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_single_orientation_cannot_form_a_ratio(self):
        result = anisotropy_ratio({"xy": 1050.0}, 0.85)
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_floor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            anisotropy_ratio(self._means(), 1.2)

    def test_non_positive_mean_rejected(self):
        with self.assertRaises(ValueError):
            anisotropy_ratio({"xy": 1050.0, "zx": 0.0}, 0.85)


class AssessMaterialPropertiesTests(unittest.TestCase):
    def test_compliant_batch_accepts_with_no_findings(self):
        result = assess_material_properties(_case())
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["accepted_coupons"], 9)

    def test_statistics_are_reported_for_every_property(self):
        result = assess_material_properties(_case())
        self.assertAlmostEqual(result["statistics"]["uts_mpa"]["count"], 9, places=9)
        self.assertAlmostEqual(
            result["statistics"]["uts_mpa"]["minimum"], 950.0, places=9
        )

    def test_foreign_coupon_is_excluded_and_reported(self):
        mixed = COUPONS + [coupon("x1", "zx", 1100.0, build_id="B-115")]
        result = assess_material_properties(_case(coupons=mixed))
        self.assertEqual(result["accepted_coupons"], 9)
        self.assertTrue(any("provenance" in text for text in result["findings"]))

    def test_low_coupon_drives_the_verdict(self):
        weak = [c for c in COUPONS if c["id"] != "c7"] + [coupon("c7", "zx", 700.0)]
        result = assess_material_properties(_case(coupons=weak))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("coupon-minima", result["driving_properties"])

    def test_missing_orientation_drives_the_verdict(self):
        thin = [c for c in COUPONS if c["orientation"] != "zx"]
        result = assess_material_properties(_case(coupons=thin))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("orientation-coverage", result["driving_properties"])

    def test_anisotropy_drives_the_verdict_with_every_coupon_above_minimum(self):
        result = assess_material_properties(_case(min_anisotropy_ratio=0.95))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertEqual(result["driving_properties"], ["anisotropy"])

    def test_orientation_set_is_the_declared_one(self):
        self.assertIn(BUILD_DIRECTION_ORIENTATION, ORIENTATIONS)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_material_properties(COUPONS)


if __name__ == "__main__":
    unittest.main()
