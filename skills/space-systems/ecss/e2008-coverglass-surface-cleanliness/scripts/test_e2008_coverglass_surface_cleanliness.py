"""Contract tests for the clause 8.7.1.3.7 coverglass cleanliness screen."""

import math
import unittest

from e2008_coverglass_surface_cleanliness_logic import (
    ACCEPT,
    CLEAN_AND_REINSPECT,
    DEFAULT_CLEANLINESS_POLICY,
    DEPOSIT_FILM,
    DEPOSIT_FINGERPRINT,
    DEPOSIT_PARTICULATE,
    DEPOSIT_STAIN,
    LOT_ACCEPTED,
    LOT_OUTSTANDING,
    LOT_RECORD_INCOMPLETE,
    REFER_FOR_REVIEW,
    REJECT,
    SURFACE_INNER,
    SURFACE_OUTER,
    assess_coverglass,
    assess_surface,
    assess_surface_cleanliness,
    deposit_area_mm2,
    deposit_is_removable,
    disposition_deposit,
    obscured_area_fraction,
    oversize_particle_count,
    permanent_obscured_area_mm2,
    post_clean_state,
    validate_cleanliness_policy,
    worst_disposition,
)

SURFACE_AREA_MM2 = 1600.0


def _policy(**overrides):
    policy = dict(DEFAULT_CLEANLINESS_POLICY)
    policy.update(overrides)
    return policy


def _stain(area_mm2=0.02):
    return {"kind": DEPOSIT_STAIN, "area_mm2": area_mm2, "removable": False}


def _particle(diameter_mm=0.04, removable=False):
    return {
        "kind": DEPOSIT_PARTICULATE,
        "diameter_mm": diameter_mm,
        "removable": removable,
    }


def _soiling(kind=DEPOSIT_FINGERPRINT, area_mm2=12.0):
    return {"kind": kind, "area_mm2": area_mm2, "removable": True}


def _surface(name=SURFACE_OUTER, deposits=None, **overrides):
    record = {
        "surface": name,
        "surface_area_mm2": SURFACE_AREA_MM2,
        "deposits": list(deposits or []),
    }
    record.update(overrides)
    return record


def _item(identifier="cg-01", outer=None, inner=None):
    return {
        "id": identifier,
        "surfaces": [
            _surface(SURFACE_OUTER, outer or []),
            _surface(SURFACE_INNER, inner or []),
        ],
    }


def _case(**overrides):
    case = {
        "declared_coverglass_count": 2,
        "coverglasses": [_item("cg-01"), _item("cg-02")],
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_cleanliness_policy(DEFAULT_CLEANLINESS_POLICY),
            DEFAULT_CLEANLINESS_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_cleanliness_policy("clean")

    def test_a_whole_surface_obscuration_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_cleanliness_policy(_policy(max_obscured_area_fraction=1.0))

    def test_a_negative_oversize_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_cleanliness_policy(_policy(max_oversize_particle_count=-1))

    def test_a_boolean_oversize_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_cleanliness_policy(_policy(max_oversize_particle_count=True))

    def test_a_zero_single_deposit_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_cleanliness_policy(_policy(max_single_deposit_area_mm2=0.0))


class DepositTests(unittest.TestCase):
    def test_a_particle_area_comes_from_its_diameter(self):
        self.assertAlmostEqual(
            deposit_area_mm2(_particle(0.2)), math.pi * 0.25 * 0.04, places=12
        )

    def test_a_film_area_is_the_declared_one(self):
        self.assertAlmostEqual(
            deposit_area_mm2({"kind": DEPOSIT_FILM, "area_mm2": 3.5, "removable": True}),
            3.5,
            places=12,
        )

    def test_an_unknown_deposit_kind_rejected(self):
        with self.assertRaises(ValueError):
            deposit_area_mm2({"kind": "smudge", "area_mm2": 1.0, "removable": True})

    def test_a_particle_with_no_diameter_rejected(self):
        with self.assertRaises(ValueError):
            deposit_area_mm2({"kind": DEPOSIT_PARTICULATE, "removable": False})

    def test_a_negative_deposit_area_rejected(self):
        with self.assertRaises(ValueError):
            deposit_area_mm2(_stain(-1.0))

    def test_a_non_boolean_removable_flag_rejected(self):
        with self.assertRaises(ValueError):
            deposit_is_removable({"kind": DEPOSIT_STAIN, "area_mm2": 1.0, "removable": "yes"})

    def test_removable_soiling_goes_back_for_cleaning(self):
        disposition, reason = disposition_deposit(_soiling())
        self.assertEqual(disposition, CLEAN_AND_REINSPECT)
        self.assertIn("cleaned", reason)

    def test_small_permanent_contamination_goes_to_review(self):
        disposition, _reason = disposition_deposit(_stain(0.02))
        self.assertEqual(disposition, REFER_FOR_REVIEW)

    def test_contamination_above_the_single_deposit_allowance_rejects(self):
        disposition, _reason = disposition_deposit(_stain(0.5))
        self.assertEqual(disposition, REJECT)

    def test_contamination_exactly_on_the_single_deposit_allowance_is_reviewed(self):
        limit = DEFAULT_CLEANLINESS_POLICY["max_single_deposit_area_mm2"]
        self.assertAlmostEqual(deposit_area_mm2(_stain(limit)), limit, places=12)
        disposition, _reason = disposition_deposit(_stain(limit))
        self.assertEqual(disposition, REFER_FOR_REVIEW)


class AccumulationTests(unittest.TestCase):
    def test_removable_soiling_carries_no_permanent_area(self):
        self.assertAlmostEqual(
            permanent_obscured_area_mm2([_soiling(area_mm2=50.0)]), 0.0, places=12
        )

    def test_permanent_deposits_accumulate(self):
        self.assertAlmostEqual(
            permanent_obscured_area_mm2([_stain(0.02), _stain(0.03)]), 0.05, places=12
        )

    def test_the_obscured_fraction_is_area_over_the_surface(self):
        self.assertAlmostEqual(
            obscured_area_fraction([_stain(1.6)], SURFACE_AREA_MM2), 0.001, places=12
        )

    def test_a_zero_surface_area_rejected(self):
        with self.assertRaises(ValueError):
            obscured_area_fraction([_stain()], 0.0)

    def test_removable_particles_do_not_count_as_oversize(self):
        deposits = [_particle(0.5, removable=True)] * 6
        self.assertEqual(oversize_particle_count(deposits), 0)

    def test_a_particle_exactly_on_the_oversize_diameter_counts(self):
        limit = DEFAULT_CLEANLINESS_POLICY["oversize_particle_diameter_mm"]
        self.assertEqual(oversize_particle_count([_particle(limit)]), 1)

    def test_a_particle_below_the_oversize_diameter_does_not_count(self):
        self.assertEqual(oversize_particle_count([_particle(0.02)]), 0)

    def test_the_worst_disposition_governs(self):
        self.assertEqual(
            worst_disposition([ACCEPT, CLEAN_AND_REINSPECT, REJECT, REFER_FOR_REVIEW]),
            REJECT,
        )

    def test_an_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition([ACCEPT, "pass"])


class SurfaceTests(unittest.TestCase):
    def test_a_clean_surface_is_accepted(self):
        result = assess_surface(_surface())
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_an_unknown_surface_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface(_surface("edge-ground"))

    def test_soiling_with_no_second_look_holds_the_surface_open(self):
        result = assess_surface(_surface(deposits=[_soiling()]))
        self.assertEqual(result["disposition"], CLEAN_AND_REINSPECT)
        self.assertTrue(result["removable_soiling_present"])

    def test_a_clean_post_clean_result_closes_the_soiling(self):
        record = _surface(deposits=[_soiling()])
        record["post_clean_reinspection"] = {
            "performed": True,
            "surface_free_of_residue": True,
        }
        result = assess_surface(record)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_residue_surviving_the_clean_becomes_contamination(self):
        record = _surface(deposits=[_soiling()])
        record["post_clean_reinspection"] = {
            "performed": True,
            "surface_free_of_residue": False,
        }
        result = assess_surface(record)
        self.assertEqual(result["disposition"], REFER_FOR_REVIEW)

    def test_an_unperformed_post_clean_record_reads_as_no_record(self):
        record = _surface(deposits=[_soiling()])
        record["post_clean_reinspection"] = {
            "performed": False,
            "surface_free_of_residue": True,
        }
        self.assertIsNone(post_clean_state(record))
        self.assertEqual(assess_surface(record)["disposition"], CLEAN_AND_REINSPECT)

    def test_cumulative_obscuration_rejects_a_surface_of_legal_deposits(self):
        deposits = [_stain(0.04) for _ in range(240)]
        for deposit in deposits:
            self.assertEqual(disposition_deposit(deposit)[0], REFER_FOR_REVIEW)
        result = assess_surface(_surface(deposits=deposits))
        self.assertEqual(result["disposition"], REJECT)

    def test_obscuration_exactly_on_the_allowance_is_not_a_rejection(self):
        allowance = DEFAULT_CLEANLINESS_POLICY["max_obscured_area_fraction"]
        area = SURFACE_AREA_MM2 * allowance
        result = assess_surface(_surface(deposits=[_stain(area)]), _policy(
            max_single_deposit_area_mm2=area
        ))
        self.assertAlmostEqual(result["obscured_area_fraction"], allowance, places=12)
        self.assertEqual(result["disposition"], REFER_FOR_REVIEW)

    def test_a_peppered_surface_goes_to_review_on_the_oversize_count(self):
        deposits = [_particle(0.12) for _ in range(4)]
        result = assess_surface(_surface(deposits=deposits))
        self.assertEqual(result["oversize_particle_count"], 4)
        self.assertEqual(result["disposition"], REFER_FOR_REVIEW)

    def test_a_non_sequence_deposit_record_rejected(self):
        with self.assertRaises(ValueError):
            record = _surface()
            record["deposits"] = "none"
            assess_surface(record)


class CoverglassTests(unittest.TestCase):
    def test_both_surfaces_screened_and_clean_is_accepted(self):
        result = assess_coverglass(_item())
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertTrue(result["record_complete"])
        self.assertEqual(result["surfaces_screened"], (SURFACE_INNER, SURFACE_OUTER))

    def test_a_one_sided_screen_leaves_the_item_incomplete(self):
        item = {"id": "cg-09", "surfaces": [_surface(SURFACE_OUTER)]}
        result = assess_coverglass(item)
        self.assertFalse(result["record_complete"])
        self.assertEqual(result["missing_surfaces"], (SURFACE_INNER,))

    def test_a_surface_recorded_twice_rejected(self):
        item = {"id": "cg-09", "surfaces": [_surface(SURFACE_OUTER), _surface(SURFACE_OUTER)]}
        with self.assertRaises(ValueError):
            assess_coverglass(item)

    def test_an_item_with_no_surface_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass({"id": "cg-09", "surfaces": []})

    def test_a_blank_coverglass_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass({"id": "   ", "surfaces": [_surface()]})

    def test_the_inner_surface_drives_the_item_disposition(self):
        result = assess_coverglass(_item(inner=[_stain(0.4)]))
        self.assertEqual(result["disposition"], REJECT)
        self.assertEqual(result["surfaces"][SURFACE_OUTER]["disposition"], ACCEPT)


class LotTests(unittest.TestCase):
    def test_a_complete_clean_lot_is_accepted(self):
        result = assess_surface_cleanliness(_case())
        self.assertEqual(result["verdict"], LOT_ACCEPTED)
        self.assertEqual(result["outstanding_ids"], ())
        self.assertEqual(result["surfaces_screened"], 4)

    def test_a_short_record_set_leaves_the_lot_incomplete(self):
        case = _case(declared_coverglass_count=5)
        result = assess_surface_cleanliness(case)
        self.assertEqual(result["verdict"], LOT_RECORD_INCOMPLETE)
        self.assertEqual(result["recorded_coverglass_count"], 2)

    def test_more_records_than_the_declared_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_cleanliness(_case(declared_coverglass_count=1))

    def test_a_duplicate_coverglass_id_rejected(self):
        case = _case()
        case["coverglasses"][1]["id"] = "cg-01"
        with self.assertRaises(ValueError):
            assess_surface_cleanliness(case)

    def test_soiling_on_one_item_leaves_the_lot_outstanding(self):
        case = _case()
        case["coverglasses"][0]["surfaces"][0]["deposits"] = [_soiling()]
        result = assess_surface_cleanliness(case)
        self.assertEqual(result["verdict"], LOT_OUTSTANDING)
        self.assertEqual(result["outstanding_ids"], ("cg-01",))
        self.assertEqual(result["worst_disposition"], CLEAN_AND_REINSPECT)

    def test_a_one_sided_item_makes_the_whole_lot_incomplete(self):
        case = _case()
        case["coverglasses"][1]["surfaces"] = [_surface(SURFACE_OUTER)]
        result = assess_surface_cleanliness(case)
        self.assertEqual(result["verdict"], LOT_RECORD_INCOMPLETE)
        self.assertFalse(result["record_complete"])

    def test_an_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_cleanliness(_case(coverglasses=[]))

    def test_a_missing_declared_count_rejected(self):
        case = _case()
        del case["declared_coverglass_count"]
        with self.assertRaises(ValueError):
            assess_surface_cleanliness(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_cleanliness(["cg-01"])

    def test_every_finding_names_the_item_it_came_from(self):
        case = _case()
        case["coverglasses"][1]["surfaces"][1]["deposits"] = [_stain(0.9)]
        result = assess_surface_cleanliness(case)
        self.assertTrue(result["findings"])
        self.assertTrue(all("cg-02" in finding for finding in result["findings"]))


if __name__ == "__main__":
    unittest.main()
