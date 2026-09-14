#!/usr/bin/env python3
"""Contract test for the coverglass corner chip limits (offline)."""

import copy
import math
import unittest

from e2008_coverglass_corner_chips_logic import (
    ACCEPT,
    CORNER_A,
    CORNER_B,
    CORNER_C,
    COVERGLASS_CORNERS,
    DEFAULT_CORNER_CHIP_CRITERIA,
    EDGE_CLAUSE_ROUTE,
    GLASS_ACCEPTED,
    GLASS_REFERRED,
    GLASS_REJECTED,
    REFER,
    REJECT,
    assess_corner_chip,
    assess_coverglass_corners,
    corner_area_mm2,
    corner_reach_mm,
    derive_hypotenuse_mm,
    leg_ratio,
    resolve_corner_chip,
    validate_corner_chip_criteria,
    validate_coverglass_geometry,
)

GEOMETRY = {
    "length_mm": 42.0,
    "width_mm": 42.0,
    "thickness_um": 100.0,
    "overhang_mm": 0.5,
}


def _chip(**overrides):
    chip = {
        "id": "K1",
        "corner": CORNER_A,
        "leg_a_mm": 0.45,
        "leg_b_mm": 0.60,
    }
    chip.update(overrides)
    return chip


def _glass(chips=None, **overrides):
    glass = {
        "coverglass_id": "CG-101",
        "geometry": copy.deepcopy(GEOMETRY),
        "corner_chips": copy.deepcopy(chips) if chips else [],
    }
    glass.update(overrides)
    return glass


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_corner_chip_criteria(DEFAULT_CORNER_CHIP_CRITERIA),
            DEFAULT_CORNER_CHIP_CRITERIA,
        )

    def test_clause_ceiling_is_three_quarters_of_a_millimetre(self):
        self.assertAlmostEqual(
            DEFAULT_CORNER_CHIP_CRITERIA["max_hypotenuse_mm"], 0.75, places=9
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_corner_chip_criteria("default")

    def test_missing_hypotenuse_ceiling_rejected(self):
        broken = dict(DEFAULT_CORNER_CHIP_CRITERIA)
        del broken["max_hypotenuse_mm"]
        with self.assertRaises(ValueError):
            validate_corner_chip_criteria(broken)

    def test_leg_ratio_below_one_rejected(self):
        broken = dict(DEFAULT_CORNER_CHIP_CRITERIA, max_leg_ratio=0.5)
        with self.assertRaises(ValueError):
            validate_corner_chip_criteria(broken)

    def test_agreement_fraction_above_one_rejected(self):
        broken = dict(
            DEFAULT_CORNER_CHIP_CRITERIA, max_hypotenuse_mismatch_fraction=1.5
        )
        with self.assertRaises(ValueError):
            validate_corner_chip_criteria(broken)

    def test_review_factor_below_one_rejected(self):
        broken = dict(DEFAULT_CORNER_CHIP_CRITERIA, hypotenuse_review_factor=0.9)
        with self.assertRaises(ValueError):
            validate_corner_chip_criteria(broken)

    def test_non_integer_corner_allowance_rejected(self):
        broken = dict(DEFAULT_CORNER_CHIP_CRITERIA, max_corners_affected=1.5)
        with self.assertRaises(ValueError):
            validate_corner_chip_criteria(broken)


class GeometryTests(unittest.TestCase):
    def test_geometry_derives_the_corner_reach_available(self):
        resolved = validate_coverglass_geometry(GEOMETRY)
        self.assertAlmostEqual(
            resolved["corner_reach_available_mm"], 0.5 * math.sqrt(2.0), places=9
        )

    def test_geometry_derives_face_and_aperture_area(self):
        resolved = validate_coverglass_geometry(GEOMETRY)
        self.assertAlmostEqual(resolved["face_area_mm2"], 1764.0, places=9)
        self.assertAlmostEqual(resolved["aperture_area_mm2"], 41.0 * 41.0, places=9)

    def test_overhang_that_swallows_the_aperture_rejected(self):
        broken = dict(GEOMETRY, overhang_mm=30.0)
        with self.assertRaises(ValueError):
            validate_coverglass_geometry(broken)

    def test_non_mapping_geometry_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverglass_geometry("42x42")


class ChordGeometryTests(unittest.TestCase):
    def test_chord_closes_the_two_legs(self):
        self.assertAlmostEqual(derive_hypotenuse_mm(0.45, 0.60), 0.75, places=9)

    def test_chord_rejects_a_non_positive_leg(self):
        with self.assertRaises(ValueError):
            derive_hypotenuse_mm(0.45, 0.0)

    def test_corner_area_is_half_the_product_of_the_legs(self):
        self.assertAlmostEqual(corner_area_mm2(0.45, 0.60), 0.135, places=9)

    def test_reach_is_shorter_than_either_leg(self):
        reach = corner_reach_mm(0.45, 0.60)
        self.assertAlmostEqual(reach, 0.36, places=9)
        self.assertLess(reach, 0.45)

    def test_reach_of_a_symmetric_bite_is_the_half_diagonal(self):
        self.assertAlmostEqual(
            corner_reach_mm(1.0, 1.0), 1.0 / math.sqrt(2.0), places=9
        )

    def test_leg_ratio_is_one_for_a_symmetric_bite(self):
        self.assertAlmostEqual(leg_ratio(0.5, 0.5), 1.0, places=9)

    def test_leg_ratio_is_order_independent(self):
        self.assertAlmostEqual(leg_ratio(0.1, 0.7), leg_ratio(0.7, 0.1), places=9)


class MeasurementReconciliationTests(unittest.TestCase):
    def test_legs_alone_resolve_without_a_measured_chord(self):
        measurement = resolve_corner_chip(_chip())
        self.assertIsNone(measurement["measured_hypotenuse_mm"])
        self.assertIsNone(measurement["hypotenuse_mismatch_fraction"])
        self.assertAlmostEqual(measurement["hypotenuse_mm"], 0.75, places=9)

    def test_agreeing_measured_chord_is_kept(self):
        measurement = resolve_corner_chip(_chip(measured_hypotenuse_mm=0.76))
        self.assertLess(measurement["hypotenuse_mismatch_fraction"], 0.02)

    def test_chord_shorter_than_the_longest_leg_rejected(self):
        with self.assertRaises(ValueError):
            resolve_corner_chip(_chip(measured_hypotenuse_mm=0.50))

    def test_chord_longer_than_the_two_legs_together_rejected(self):
        with self.assertRaises(ValueError):
            resolve_corner_chip(_chip(measured_hypotenuse_mm=1.20))

    def test_unknown_corner_rejected(self):
        with self.assertRaises(ValueError):
            resolve_corner_chip(_chip(corner="corner-e"))

    def test_missing_leg_rejected(self):
        chip = _chip()
        del chip["leg_b_mm"]
        with self.assertRaises(ValueError):
            resolve_corner_chip(chip)

    def test_non_mapping_chip_rejected(self):
        with self.assertRaises(ValueError):
            resolve_corner_chip("corner chip")

    def test_every_named_corner_resolves(self):
        for corner in COVERGLASS_CORNERS:
            measurement = resolve_corner_chip(_chip(corner=corner))
            self.assertEqual(measurement["corner"], corner)


class ChipDispositionTests(unittest.TestCase):
    def test_small_corner_bite_accepted(self):
        result = assess_corner_chip(_chip(leg_a_mm=0.3, leg_b_mm=0.4), GEOMETRY)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_chord_exactly_on_the_ceiling_still_accepts(self):
        result = assess_corner_chip(_chip(), GEOMETRY)
        self.assertAlmostEqual(result["hypotenuse_mm"], 0.75, places=9)
        self.assertAlmostEqual(result["hypotenuse_margin_mm"], 0.0, places=9)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_chord_past_the_ceiling_is_referred(self):
        result = assess_corner_chip(_chip(leg_a_mm=0.48, leg_b_mm=0.64), GEOMETRY)
        self.assertAlmostEqual(result["hypotenuse_mm"], 0.8, places=9)
        self.assertEqual(result["disposition"], REFER)

    def test_chord_exactly_on_the_review_limit_is_still_only_referred(self):
        result = assess_corner_chip(_chip(leg_a_mm=0.54, leg_b_mm=0.72), GEOMETRY)
        self.assertAlmostEqual(result["hypotenuse_mm"], 0.9, places=9)
        self.assertEqual(result["disposition"], REFER)

    def test_chord_past_the_review_limit_rejects(self):
        result = assess_corner_chip(_chip(leg_a_mm=0.9, leg_b_mm=1.2), GEOMETRY)
        self.assertEqual(result["disposition"], REJECT)

    def test_reach_past_the_overhang_diagonal_rejects_an_otherwise_legal_chord(self):
        tight = dict(GEOMETRY, overhang_mm=0.2)
        on_wide = assess_corner_chip(_chip(), GEOMETRY)
        on_tight = assess_corner_chip(_chip(), tight)
        self.assertEqual(on_wide["disposition"], ACCEPT)
        self.assertEqual(on_tight["disposition"], REJECT)

    def test_reach_available_follows_the_declared_overhang(self):
        result = assess_corner_chip(_chip(), GEOMETRY)
        self.assertAlmostEqual(
            result["corner_reach_available_mm"], 0.5 * math.sqrt(2.0), places=9
        )
        self.assertAlmostEqual(result["corner_reach_mm"], 0.36, places=9)

    def test_lopsided_bite_is_routed_to_the_edge_clause(self):
        result = assess_corner_chip(_chip(leg_a_mm=0.1, leg_b_mm=0.7), GEOMETRY)
        self.assertEqual(result["disposition"], REFER)
        self.assertEqual(result["routed_to"], EDGE_CLAUSE_ROUTE)

    def test_a_lopsided_bite_can_still_pass_the_chord_ceiling(self):
        result = assess_corner_chip(_chip(leg_a_mm=0.1, leg_b_mm=0.7), GEOMETRY)
        self.assertLess(result["hypotenuse_mm"], 0.75)

    def test_disagreeing_measured_chord_is_referred(self):
        result = assess_corner_chip(_chip(measured_hypotenuse_mm=0.90), GEOMETRY)
        self.assertEqual(result["disposition"], REFER)

    def test_agreeing_measured_chord_leaves_the_chip_accepted(self):
        result = assess_corner_chip(_chip(measured_hypotenuse_mm=0.76), GEOMETRY)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_zero_leg_rejected(self):
        with self.assertRaises(ValueError):
            assess_corner_chip(_chip(leg_a_mm=0.0), GEOMETRY)

    def test_negative_leg_rejected(self):
        with self.assertRaises(ValueError):
            assess_corner_chip(_chip(leg_b_mm=-0.3), GEOMETRY)


class GlassRollupTests(unittest.TestCase):
    def test_clean_glass_is_accepted(self):
        result = assess_coverglass_corners(_glass([_chip()]))
        self.assertEqual(result["verdict"], GLASS_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["not_accepted_ids"], [])

    def test_glass_with_no_corner_chips_is_accepted(self):
        result = assess_coverglass_corners(_glass())
        self.assertEqual(result["verdict"], GLASS_ACCEPTED)
        self.assertAlmostEqual(result["largest_hypotenuse_mm"], 0.0, places=9)
        self.assertAlmostEqual(result["deepest_corner_reach_mm"], 0.0, places=9)

    def test_worst_corner_sets_the_glass_verdict(self):
        result = assess_coverglass_corners(
            _glass(
                [
                    _chip(),
                    _chip(id="K2", corner=CORNER_B, leg_a_mm=0.9, leg_b_mm=1.2),
                ]
            )
        )
        self.assertEqual(result["verdict"], GLASS_REJECTED)
        self.assertEqual(result["not_accepted_ids"], ["K2"])

    def test_largest_chord_is_reported_for_the_glass(self):
        result = assess_coverglass_corners(
            _glass(
                [
                    _chip(leg_a_mm=0.3, leg_b_mm=0.4),
                    _chip(id="K2", corner=CORNER_B),
                ]
            )
        )
        self.assertAlmostEqual(result["largest_hypotenuse_mm"], 0.75, places=9)

    def test_cumulative_corner_area_catches_individually_clean_bites(self):
        criteria = dict(
            DEFAULT_CORNER_CHIP_CRITERIA, max_cumulative_corner_area_fraction=1e-5
        )
        result = assess_coverglass_corners(_glass([_chip()]), criteria)
        self.assertEqual(result["corner_chips"][0]["disposition"], ACCEPT)
        self.assertAlmostEqual(result["corner_area_mm2"], 0.135, places=9)
        self.assertEqual(result["verdict"], GLASS_REFERRED)

    def test_too_many_chipped_corners_is_referred(self):
        chips = [
            _chip(id="K1", corner=CORNER_A),
            _chip(id="K2", corner=CORNER_B),
            _chip(id="K3", corner=CORNER_C),
        ]
        result = assess_coverglass_corners(_glass(chips))
        for chip in result["corner_chips"]:
            self.assertEqual(chip["disposition"], ACCEPT)
        self.assertEqual(len(result["corners_affected"]), 3)
        self.assertEqual(result["verdict"], GLASS_REFERRED)

    def test_two_bites_recorded_at_one_corner_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_corners(
                _glass([_chip(id="K1"), _chip(id="K2", corner=CORNER_A)])
            )

    def test_duplicate_chip_ids_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_corners(
                _glass([_chip(id="D"), _chip(id="D", corner=CORNER_B)])
            )

    def test_lopsided_bites_are_listed_for_the_edge_clause(self):
        result = assess_coverglass_corners(
            _glass(
                [
                    _chip(id="K1", leg_a_mm=0.1, leg_b_mm=0.7),
                    _chip(id="K2", corner=CORNER_B),
                ]
            )
        )
        self.assertEqual(result["routed_to_edge_clause"], ["K1"])

    def test_glass_without_an_id_rejected(self):
        glass = _glass([_chip()])
        glass["coverglass_id"] = "  "
        with self.assertRaises(ValueError):
            assess_coverglass_corners(glass)

    def test_non_list_corner_collection_rejected(self):
        glass = _glass()
        glass["corner_chips"] = _chip()
        with self.assertRaises(ValueError):
            assess_coverglass_corners(glass)

    def test_input_is_not_mutated_by_the_screen(self):
        glass = _glass([_chip(), _chip(id="K2", corner=CORNER_B)])
        before = copy.deepcopy(glass)
        assess_coverglass_corners(glass)
        self.assertEqual(glass, before)


if __name__ == "__main__":
    unittest.main()
