#!/usr/bin/env python3
"""Contract test for the unaided coupon cleanliness inspection (offline)."""

import copy
import unittest

from e2008_cleanliness_visual_inspection_logic import (
    ACCEPT,
    CLEAN,
    DEFAULT_CLEANLINESS_CRITERIA,
    DEPOSIT_KINDS,
    INSPECTION_INCOMPLETE,
    REFER,
    REJECT,
    assess_deposit,
    assess_surface,
    inspect_coupon_cleanliness,
    resolvable_feature_mm,
    validate_cleanliness_criteria,
)

SURFACE_AREA_MM2 = 10000.0
FLOOR_MM = resolvable_feature_mm(300.0)

BARE_SURFACE = {
    "surface_id": "S-FRONT",
    "area_mm2": SURFACE_AREA_MM2,
    "viewing_distance_mm": 300.0,
    "illuminance_lux": 1200.0,
    "magnification": 1.0,
    "deposits": [],
}


def _surface(deposits=None, **overrides):
    record = copy.deepcopy(BARE_SURFACE)
    record["deposits"] = copy.deepcopy(deposits) if deposits else []
    record.update(overrides)
    return record


def _particles(**overrides):
    deposit = {
        "id": "D1",
        "kind": "particulate",
        "max_dimension_mm": 0.2,
        "count": 3,
    }
    deposit.update(overrides)
    return deposit


def _film(**overrides):
    deposit = {
        "id": "D2",
        "kind": "smear-or-film",
        "area_mm2": 20.0,
        "removable": True,
    }
    deposit.update(overrides)
    return deposit


def _coupon(records, declared=None, **overrides):
    coupon = {
        "coupon_id": "CPN-01",
        "declared_surface_count": declared if declared is not None else len(records),
        "surfaces": records,
    }
    coupon.update(overrides)
    return coupon


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_cleanliness_criteria(DEFAULT_CLEANLINESS_CRITERIA),
            DEFAULT_CLEANLINESS_CRITERIA,
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_cleanliness_criteria("default")

    def test_missing_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_CLEANLINESS_CRITERIA)
        del broken["min_illuminance_lux"]
        with self.assertRaises(ValueError):
            validate_cleanliness_criteria(broken)

    def test_magnification_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_CLEANLINESS_CRITERIA)
        broken["max_magnification"] = 0.5
        with self.assertRaises(ValueError):
            validate_cleanliness_criteria(broken)

    def test_area_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_CLEANLINESS_CRITERIA)
        broken["max_deposit_area_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_cleanliness_criteria(broken)

    def test_non_integer_particle_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_CLEANLINESS_CRITERIA)
        broken["max_particles_per_100cm2"] = 4.5
        with self.assertRaises(ValueError):
            validate_cleanliness_criteria(broken)


class DetectionFloorTests(unittest.TestCase):
    def test_unaided_floor_is_about_a_tenth_of_a_millimetre(self):
        self.assertAlmostEqual(resolvable_feature_mm(300.0), 0.087266463, places=8)

    def test_floor_grows_with_the_working_distance(self):
        near = resolvable_feature_mm(300.0)
        far = resolvable_feature_mm(600.0)
        self.assertAlmostEqual(far, 2.0 * near, places=9)

    def test_an_aid_divides_the_floor_by_its_power(self):
        unaided = resolvable_feature_mm(300.0)
        aided = resolvable_feature_mm(300.0, magnification=10.0)
        self.assertAlmostEqual(aided, unaided / 10.0, places=12)

    def test_magnification_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_feature_mm(300.0, magnification=0.5)

    def test_non_numeric_distance_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_feature_mm("300")


class ParticulateTests(unittest.TestCase):
    def test_few_small_particles_accept(self):
        result = assess_deposit(_particles(), SURFACE_AREA_MM2, FLOOR_MM)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertFalse(result["below_detection_floor"])

    def test_particle_exactly_on_the_floor_is_still_a_real_observation(self):
        deposit = _particles(max_dimension_mm=FLOOR_MM)
        result = assess_deposit(deposit, SURFACE_AREA_MM2, FLOOR_MM)
        self.assertAlmostEqual(deposit["max_dimension_mm"], FLOOR_MM, places=12)
        self.assertFalse(result["below_detection_floor"])
        self.assertEqual(result["disposition"], ACCEPT)

    def test_particle_under_the_unaided_floor_goes_to_review(self):
        result = assess_deposit(
            _particles(max_dimension_mm=0.01), SURFACE_AREA_MM2, FLOOR_MM
        )
        self.assertTrue(result["below_detection_floor"])
        self.assertEqual(result["disposition"], REFER)

    def test_oversize_particle_is_cleaned_and_looked_at_again(self):
        result = assess_deposit(
            _particles(max_dimension_mm=0.7), SURFACE_AREA_MM2, FLOOR_MM
        )
        self.assertEqual(result["disposition"], CLEAN)

    def test_far_oversize_particle_rejects(self):
        result = assess_deposit(
            _particles(max_dimension_mm=3.0), SURFACE_AREA_MM2, FLOOR_MM
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_many_small_particles_exceed_the_density_allowance(self):
        result = assess_deposit(
            _particles(count=9), SURFACE_AREA_MM2, FLOOR_MM
        )
        self.assertEqual(result["disposition"], CLEAN)

    def test_particulate_needs_a_count(self):
        deposit = _particles()
        del deposit["count"]
        with self.assertRaises(ValueError):
            assess_deposit(deposit, SURFACE_AREA_MM2, FLOOR_MM)

    def test_particulate_count_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            assess_deposit(_particles(count=0), SURFACE_AREA_MM2, FLOOR_MM)


class DepositKindTests(unittest.TestCase):
    def test_removable_film_is_cleaned_and_looked_at_again(self):
        result = assess_deposit(_film(), SURFACE_AREA_MM2, FLOOR_MM)
        self.assertEqual(result["disposition"], CLEAN)

    def test_fixed_film_goes_to_review(self):
        result = assess_deposit(
            _film(removable=False), SURFACE_AREA_MM2, FLOOR_MM
        )
        self.assertEqual(result["disposition"], REFER)

    def test_large_fixed_film_rejects(self):
        result = assess_deposit(
            _film(removable=False, area_mm2=400.0), SURFACE_AREA_MM2, FLOOR_MM
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_large_removable_film_still_goes_to_review(self):
        result = assess_deposit(
            _film(area_mm2=100.0), SURFACE_AREA_MM2, FLOOR_MM
        )
        self.assertEqual(result["disposition"], REFER)

    def test_fingerprint_is_never_accepted_at_size(self):
        deposit = {"id": "D3", "kind": "fingerprint", "area_mm2": 1.0}
        result = assess_deposit(deposit, SURFACE_AREA_MM2, FLOOR_MM)
        self.assertEqual(result["disposition"], CLEAN)

    def test_staining_goes_to_review_because_cleaning_does_not_answer_it(self):
        deposit = {"id": "D4", "kind": "staining", "area_mm2": 2.0}
        result = assess_deposit(deposit, SURFACE_AREA_MM2, FLOOR_MM)
        self.assertEqual(result["disposition"], REFER)

    def test_short_fibre_is_cleaned_and_long_fibre_referred(self):
        short = {"id": "D5", "kind": "fibre", "length_mm": 1.5}
        long_one = {"id": "D6", "kind": "fibre", "length_mm": 6.0}
        self.assertEqual(
            assess_deposit(short, SURFACE_AREA_MM2, FLOOR_MM)["disposition"], CLEAN
        )
        self.assertEqual(
            assess_deposit(long_one, SURFACE_AREA_MM2, FLOOR_MM)["disposition"], REFER
        )

    def test_fibre_footprint_is_not_its_length(self):
        deposit = {"id": "D5", "kind": "fibre", "length_mm": 2.0}
        result = assess_deposit(deposit, SURFACE_AREA_MM2, FLOOR_MM)
        self.assertAlmostEqual(result["deposit_area_mm2"], 0.2, places=9)

    def test_adhesive_residue_needs_a_boolean_removable(self):
        deposit = {
            "id": "D7",
            "kind": "adhesive-residue",
            "area_mm2": 3.0,
            "removable": "no",
        }
        with self.assertRaises(ValueError):
            assess_deposit(deposit, SURFACE_AREA_MM2, FLOOR_MM)

    def test_unknown_deposit_kind_rejected(self):
        deposit = {"id": "D8", "kind": "corrosion-pit", "area_mm2": 1.0}
        with self.assertRaises(ValueError):
            assess_deposit(deposit, SURFACE_AREA_MM2, FLOOR_MM)

    def test_every_declared_kind_is_dispositioned(self):
        self.assertEqual(len(DEPOSIT_KINDS), 6)

    def test_deposit_larger_than_the_surface_rejected(self):
        with self.assertRaises(ValueError):
            assess_deposit(_film(area_mm2=20000.0), SURFACE_AREA_MM2, FLOOR_MM)


class SurfaceTests(unittest.TestCase):
    def test_clean_surface_under_good_conditions_accepts(self):
        result = assess_surface(_surface())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["appears_clean"])
        self.assertTrue(result["conditions_met"])
        self.assertAlmostEqual(result["detection_floor_mm"], FLOOR_MM, places=12)

    def test_illuminance_exactly_on_the_floor_still_counts(self):
        result = assess_surface(_surface(illuminance_lux=1000.0))
        self.assertTrue(result["conditions_met"])
        self.assertEqual(result["verdict"], ACCEPT)

    def test_dim_examination_withholds_the_clean_statement(self):
        result = assess_surface(_surface(illuminance_lux=200.0))
        self.assertFalse(result["conditions_met"])
        self.assertFalse(result["appears_clean"])
        self.assertEqual(result["verdict"], REFER)

    def test_an_aided_look_is_not_the_unaided_statement(self):
        result = assess_surface(_surface(magnification=10.0))
        self.assertTrue(result["aided"])
        self.assertFalse(result["appears_clean"])
        self.assertAlmostEqual(
            result["detection_floor_mm"], FLOOR_MM / 10.0, places=12
        )
        self.assertAlmostEqual(
            result["unaided_detection_floor_mm"], FLOOR_MM, places=12
        )

    def test_unity_magnification_is_not_aided(self):
        result = assess_surface(_surface(magnification=1.0))
        self.assertFalse(result["aided"])

    def test_a_long_working_distance_withholds_the_statement(self):
        result = assess_surface(_surface(viewing_distance_mm=900.0))
        self.assertFalse(result["conditions_met"])

    def test_small_deposits_together_exceed_the_coverage_allowance(self):
        deposits = [
            _film(id="D%d" % n, area_mm2=12.0, removable=False) for n in range(5)
        ]
        result = assess_surface(_surface(deposits))
        self.assertAlmostEqual(result["deposit_coverage_fraction"], 0.006, places=9)
        self.assertTrue(
            any("together" in finding for finding in result["findings"])
        )

    def test_duplicate_deposit_ids_rejected(self):
        deposits = [_film(id="D2"), _film(id="D2")]
        with self.assertRaises(ValueError):
            assess_surface(_surface(deposits))

    def test_missing_surface_id_rejected(self):
        record = _surface()
        record["surface_id"] = "  "
        with self.assertRaises(ValueError):
            assess_surface(record)

    def test_non_list_deposits_rejected(self):
        record = _surface()
        record["deposits"] = "none"
        with self.assertRaises(ValueError):
            assess_surface(record)

    def test_magnification_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface(_surface(magnification=0.4))


class CouponTests(unittest.TestCase):
    def test_every_surface_clean_gives_a_bounded_clean_coupon(self):
        records = [_surface(surface_id="S-%d" % n) for n in range(3)]
        result = inspect_coupon_cleanliness(_coupon(records))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["appears_clean_unaided"])
        self.assertAlmostEqual(result["statement_bounded_at_mm"], FLOOR_MM, places=12)

    def test_a_missing_surface_leaves_the_coupon_open(self):
        records = [_surface(surface_id="S-%d" % n) for n in range(2)]
        result = inspect_coupon_cleanliness(_coupon(records, declared=4))
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["missing_record_count"], 2)
        self.assertFalse(result["appears_clean_unaided"])

    def test_the_bound_follows_the_worst_surface(self):
        records = [
            _surface(surface_id="S-0"),
            _surface(surface_id="S-1", viewing_distance_mm=450.0),
        ]
        result = inspect_coupon_cleanliness(_coupon(records))
        self.assertAlmostEqual(
            result["statement_bounded_at_mm"], resolvable_feature_mm(450.0), places=12
        )

    def test_worst_surface_drives_the_coupon_verdict(self):
        dirty = _surface(
            [_film(removable=False, area_mm2=400.0)], surface_id="S-REAR"
        )
        records = [_surface(surface_id="S-FRONT"), dirty]
        result = inspect_coupon_cleanliness(_coupon(records))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["not_accepted_ids"], ["S-REAR"])

    def test_more_records_than_declared_rejected(self):
        records = [_surface(surface_id="S-%d" % n) for n in range(3)]
        with self.assertRaises(ValueError):
            inspect_coupon_cleanliness(_coupon(records, declared=2))

    def test_duplicate_surface_ids_rejected(self):
        records = [_surface(surface_id="S-0") for _ in range(2)]
        with self.assertRaises(ValueError):
            inspect_coupon_cleanliness(_coupon(records))

    def test_non_integer_declared_count_rejected(self):
        records = [_surface(surface_id="S-0")]
        with self.assertRaises(ValueError):
            inspect_coupon_cleanliness(_coupon(records, declared="two"))

    def test_non_mapping_coupon_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_cleanliness("CPN-01")


if __name__ == "__main__":
    unittest.main()
