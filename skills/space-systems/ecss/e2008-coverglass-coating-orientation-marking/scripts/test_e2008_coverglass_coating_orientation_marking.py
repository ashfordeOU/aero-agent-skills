#!/usr/bin/env python3
"""Contract test for coverglass coating-face identification (offline).

Walks the clause workflow step by step: whether an indicator may sit
where it is declared and the pairings that are refused outright, whether
it still names a face after the piece is turned over, whether it
survives the clean before bonding, what it costs inside the clear
aperture against the policy cap, how many cues remain usable at the
point of use, and the one thing no single piece can show -- whether one
convention holds across the lot. This is the gate 3 review evidence for
the leaf.
"""

import copy
import unittest

from e2008_coverglass_coating_orientation_marking_logic import (
    ORIENTATION_AMBIGUOUS,
    ORIENTATION_NOT_ESTABLISHED,
    ORIENTATION_UNAMBIGUOUS,
    aperture_loss_fraction,
    assess_coverglass_lot_orientation,
    assess_coverglass_orientation,
    convention_consistency,
    indicator_admissibility,
    indicator_resolves_faces,
    indicator_survives_preparation,
    usable_orientation_cues,
)

EDGE_ARROW = {
    "indicator_means": "engraved-edge-arrow",
    "indicator_location": "coverglass-edge",
    "indicator_area_mm2": 0.5,
}

SOUND_PIECE = {
    "piece_id": "CG-1",
    "marked_face": "coated-face",
    "clear_aperture_mm2": 1800.0,
    "cleaning_process": "ultrasonic-bath",
    "cues": [dict(EDGE_ARROW)],
}


def _piece(piece_id, **overrides):
    record = copy.deepcopy(SOUND_PIECE)
    record["piece_id"] = piece_id
    record.update(copy.deepcopy(overrides))
    return record


class AdmissibilityTests(unittest.TestCase):
    def test_an_engraved_arrow_on_the_rim_is_admissible(self):
        result = indicator_admissibility(
            "engraved-edge-arrow", "coverglass-edge"
        )
        self.assertTrue(result["admissible"])
        self.assertEqual(result["findings"], [])

    def test_no_indicator_at_all_is_refused(self):
        result = indicator_admissibility("none", "coverglass-edge")
        self.assertFalse(result["admissible"])
        self.assertTrue(result["findings"])

    def test_a_label_on_the_cell_facing_face_is_refused(self):
        result = indicator_admissibility("adhesive-face-label", "uncoated-face")
        self.assertFalse(result["admissible"])

    def test_ink_inside_the_clear_aperture_is_refused(self):
        result = indicator_admissibility("printed-face-arrow", "coated-face")
        self.assertFalse(result["admissible"])

    def test_an_outline_feature_declared_on_a_face_is_refused(self):
        result = indicator_admissibility("corner-cut", "coated-face")
        self.assertFalse(result["admissible"])

    def test_a_packaging_scheme_declared_on_the_glass_is_refused(self):
        result = indicator_admissibility(
            "packaging-orientation-only", "coverglass-edge"
        )
        self.assertFalse(result["admissible"])

    def test_a_label_inside_the_aperture_is_admissible_but_reported(self):
        result = indicator_admissibility("adhesive-face-label", "coated-face")
        self.assertTrue(result["admissible"])
        self.assertTrue(result["findings"])

    def test_a_carrier_indicator_is_admissible_but_reported(self):
        result = indicator_admissibility(
            "packaging-orientation-only", "packaging-carrier"
        )
        self.assertTrue(result["admissible"])
        self.assertTrue(result["findings"])

    def test_unknown_indicator_means_rejected(self):
        with self.assertRaises(ValueError):
            indicator_admissibility("felt-pen-dot", "coverglass-edge")

    def test_unknown_indicator_location_rejected(self):
        with self.assertRaises(ValueError):
            indicator_admissibility("engraved-edge-arrow", "cell-busbar")


class FaceResolutionTests(unittest.TestCase):
    def test_an_engraved_arrow_names_a_face(self):
        self.assertTrue(
            indicator_resolves_faces("engraved-edge-arrow")["resolves_faces"]
        )

    def test_a_bevel_ground_into_one_face_names_a_face(self):
        self.assertTrue(
            indicator_resolves_faces("edge-bevel-notch")["resolves_faces"]
        )

    def test_a_cut_corner_mirrors_when_the_piece_is_turned_over(self):
        result = indicator_resolves_faces("corner-cut")
        self.assertFalse(result["resolves_faces"])
        self.assertTrue(result["findings"])

    def test_packaging_knows_which_way_up_and_the_piece_does_not(self):
        result = indicator_resolves_faces("packaging-orientation-only")
        self.assertFalse(result["resolves_faces"])
        self.assertTrue(result["findings"])

    def test_unknown_means_rejected_by_the_resolution_check(self):
        with self.assertRaises(ValueError):
            indicator_resolves_faces("scribed-serial")


class SurvivalTests(unittest.TestCase):
    def test_geometry_survives_every_clean(self):
        for cleaning in ("none", "solvent-wipe", "ultrasonic-bath", "plasma-clean"):
            self.assertTrue(
                indicator_survives_preparation("edge-bevel-notch", cleaning)[
                    "survives_preparation"
                ]
            )

    def test_ink_is_gone_after_a_solvent_wipe(self):
        result = indicator_survives_preparation(
            "printed-face-arrow", "solvent-wipe"
        )
        self.assertFalse(result["survives_preparation"])
        self.assertTrue(result["findings"])

    def test_a_label_survives_a_wipe_and_not_an_ultrasonic_bath(self):
        self.assertTrue(
            indicator_survives_preparation("adhesive-face-label", "solvent-wipe")[
                "survives_preparation"
            ]
        )
        self.assertFalse(
            indicator_survives_preparation(
                "adhesive-face-label", "ultrasonic-bath"
            )["survives_preparation"]
        )

    def test_unknown_cleaning_process_rejected(self):
        with self.assertRaises(ValueError):
            indicator_survives_preparation("edge-bevel-notch", "bead-blast")


class ApertureLossTests(unittest.TestCase):
    def test_an_edge_indicator_costs_no_transmission(self):
        self.assertAlmostEqual(
            aperture_loss_fraction(9.0, 1800.0, "coverglass-edge"),
            0.0,
            places=12,
        )

    def test_an_indicator_inside_the_aperture_costs_its_footprint(self):
        self.assertAlmostEqual(
            aperture_loss_fraction(2.7, 1800.0, "coated-face"),
            0.0015,
            places=12,
        )

    def test_an_indicator_larger_than_the_aperture_rejected(self):
        with self.assertRaises(ValueError):
            aperture_loss_fraction(1800.0, 1800.0, "coated-face")

    def test_a_negative_footprint_rejected(self):
        with self.assertRaises(ValueError):
            aperture_loss_fraction(-1.0, 1800.0, "coated-face")

    def test_a_zero_aperture_rejected(self):
        with self.assertRaises(ValueError):
            aperture_loss_fraction(1.0, 0.0, "coated-face")


class UsableCueTests(unittest.TestCase):
    def test_one_sound_cue_counts(self):
        result = usable_orientation_cues([dict(EDGE_ARROW)], "plasma-clean")
        self.assertEqual(result["usable_cues"], 1)

    def test_a_cue_that_does_not_survive_the_clean_does_not_count(self):
        result = usable_orientation_cues(
            [
                {
                    "indicator_means": "adhesive-face-label",
                    "indicator_location": "coated-face",
                    "indicator_area_mm2": 1.0,
                }
            ],
            "plasma-clean",
        )
        self.assertEqual(result["usable_cues"], 0)

    def test_a_cue_that_does_not_name_a_face_does_not_count(self):
        result = usable_orientation_cues(
            [
                {
                    "indicator_means": "corner-cut",
                    "indicator_location": "coverglass-edge",
                }
            ],
            "none",
        )
        self.assertEqual(result["usable_cues"], 0)
        self.assertEqual(result["declared_cues"], 1)

    def test_two_independent_cues_both_count(self):
        result = usable_orientation_cues(
            [
                dict(EDGE_ARROW),
                {
                    "indicator_means": "adhesive-face-label",
                    "indicator_location": "coated-face",
                    "indicator_area_mm2": 1.0,
                },
            ],
            "solvent-wipe",
        )
        self.assertEqual(result["usable_cues"], 2)

    def test_the_same_cue_declared_twice_is_rejected(self):
        with self.assertRaises(ValueError):
            usable_orientation_cues(
                [dict(EDGE_ARROW), dict(EDGE_ARROW)], "none"
            )

    def test_non_sequence_cues_rejected(self):
        with self.assertRaises(ValueError):
            usable_orientation_cues("an arrow on the edge", "none")


class PieceTests(unittest.TestCase):
    def test_a_sound_piece_is_unambiguous(self):
        result = assess_coverglass_orientation(_piece("CG-1"))
        self.assertEqual(result["verdict"], ORIENTATION_UNAMBIGUOUS)
        self.assertEqual(result["usable_cues"], 1)

    def test_a_piece_whose_only_cue_is_a_cut_corner_is_not_established(self):
        result = assess_coverglass_orientation(
            _piece(
                "CG-2",
                cues=[
                    {
                        "indicator_means": "corner-cut",
                        "indicator_location": "coverglass-edge",
                    }
                ],
            )
        )
        self.assertEqual(result["verdict"], ORIENTATION_NOT_ESTABLISHED)

    def test_an_indicator_exactly_at_the_aperture_cap_is_within_it(self):
        result = assess_coverglass_orientation(
            _piece(
                "CG-3",
                cleaning_process="solvent-wipe",
                cues=[
                    {
                        "indicator_means": "adhesive-face-label",
                        "indicator_location": "coated-face",
                        "indicator_area_mm2": 2.7,
                    }
                ],
            )
        )
        self.assertTrue(result["within_aperture_cap"])
        self.assertAlmostEqual(
            result["aperture_loss_fraction"], 0.0015, places=12
        )
        self.assertEqual(result["verdict"], ORIENTATION_UNAMBIGUOUS)

    def test_an_indicator_over_the_aperture_cap_is_ambiguous(self):
        result = assess_coverglass_orientation(
            _piece(
                "CG-4",
                cleaning_process="solvent-wipe",
                cues=[
                    {
                        "indicator_means": "adhesive-face-label",
                        "indicator_location": "coated-face",
                        "indicator_area_mm2": 10.0,
                    }
                ],
            )
        )
        self.assertFalse(result["within_aperture_cap"])
        self.assertEqual(result["verdict"], ORIENTATION_AMBIGUOUS)

    def test_a_policy_asking_for_two_cues_downgrades_a_single_cue_piece(self):
        piece = _piece("CG-5")
        self.assertEqual(
            assess_coverglass_orientation(piece)["verdict"],
            ORIENTATION_UNAMBIGUOUS,
        )
        self.assertEqual(
            assess_coverglass_orientation(piece, {"min_usable_cues": 2})[
                "verdict"
            ],
            ORIENTATION_AMBIGUOUS,
        )

    def test_a_piece_with_no_cues_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_orientation(_piece("CG-6", cues=[]))

    def test_an_unknown_marked_face_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_orientation(_piece("CG-7", marked_face="either"))

    def test_a_missing_clear_aperture_rejected(self):
        piece = _piece("CG-8")
        del piece["clear_aperture_mm2"]
        with self.assertRaises(ValueError):
            assess_coverglass_orientation(piece)


class LotTests(unittest.TestCase):
    @staticmethod
    def _case(pieces, policy=None):
        case = {"lot_id": "LOT-1", "pieces": pieces}
        if policy is not None:
            case["policy"] = policy
        return case

    def test_a_clean_lot_is_secure(self):
        result = assess_coverglass_lot_orientation(
            self._case([_piece("CG-1"), _piece("CG-2")])
        )
        self.assertEqual(result["verdict"], ORIENTATION_UNAMBIGUOUS)
        self.assertTrue(result["lot_orientation_secure"])
        self.assertAlmostEqual(result["unambiguous_share"], 1.0, places=12)

    def test_a_lot_marking_two_different_faces_is_ambiguous(self):
        result = assess_coverglass_lot_orientation(
            self._case(
                [_piece("CG-1"), _piece("CG-2", marked_face="uncoated-face")]
            )
        )
        self.assertFalse(result["convention"]["consistent"])
        self.assertEqual(result["verdict"], ORIENTATION_AMBIGUOUS)

    def test_a_lot_mixing_two_usable_means_is_reported(self):
        result = assess_coverglass_lot_orientation(
            self._case(
                [
                    _piece("CG-1"),
                    _piece(
                        "CG-2",
                        cues=[
                            {
                                "indicator_means": "edge-bevel-notch",
                                "indicator_location": "coverglass-edge",
                            }
                        ],
                    ),
                ]
            )
        )
        self.assertEqual(len(result["convention"]["indicator_means"]), 2)
        self.assertFalse(result["lot_orientation_secure"])

    def test_pieces_with_no_orientation_are_named(self):
        result = assess_coverglass_lot_orientation(
            self._case(
                [
                    _piece("CG-1"),
                    _piece(
                        "CG-9",
                        cues=[
                            {
                                "indicator_means": "none",
                                "indicator_location": "coverglass-edge",
                            }
                        ],
                    ),
                ]
            )
        )
        self.assertEqual(result["not_established"], ["CG-9"])
        self.assertEqual(result["verdict"], ORIENTATION_NOT_ESTABLISHED)
        self.assertEqual(result["weakest_piece"], "CG-9")
        self.assertAlmostEqual(result["unambiguous_share"], 0.5, places=12)

    def test_a_repeated_piece_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_lot_orientation(
                self._case([_piece("CG-1"), _piece("CG-1")])
            )

    def test_an_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_lot_orientation(self._case([]))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_lot_orientation("every piece had an arrow")

    def test_convention_consistency_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            convention_consistency([])


if __name__ == "__main__":
    unittest.main()
