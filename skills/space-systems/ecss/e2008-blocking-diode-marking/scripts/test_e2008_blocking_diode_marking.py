#!/usr/bin/env python3
"""Contract test for planar blocking diode marking approaches (offline).

Walks the clause workflow step by step: the five standings a marking
agreement can hold and which of them bind, the identity code sized
against the face it is put on at the minimum legible character height,
the handling stage a mark on each carrier survives to, the number of
diodes one mark resolves a delivered part to, the ranked approach
verdict, the approach the catalogue would recommend instead, and the
roll-up into one delivery verdict. This is the gate 3 review evidence
for the leaf.
"""

import copy
import unittest

from e2008_blocking_diode_marking_logic import (
    AGREEMENT_ABSENT,
    AGREEMENT_PROPOSED,
    AGREEMENT_RECORDED,
    AGREEMENT_SUPERSEDED,
    AGREEMENT_VERBAL,
    APPROACH_ACCEPTABLE,
    APPROACH_CODE_DOES_NOT_FIT,
    APPROACH_GRANULARITY_SHORT,
    APPROACH_NOT_AGREED,
    APPROACH_RETENTION_SHORT,
    CARRIER_BODY,
    CARRIER_LOT_BAG,
    CARRIER_PACKAGE,
    GRAIN_LOT,
    GRAIN_PACKAGE,
    GRAIN_PART,
    MARKING_ACCEPTED,
    MARKING_APPROACHES,
    MARKING_NOT_ACCEPTED,
    assess_blocking_diode_marking,
    assess_face_fit,
    assess_marking_approach,
    code_footprint_mm,
    identity_granularity,
    resolve_policy,
    retention_reach,
    select_marking_approach,
    validate_agreement,
)

LASER = "planar-blocking-diode-laser-body-mark"
INK = "planar-blocking-diode-ink-body-mark"
CARRIER_LABEL = "planar-blocking-diode-carrier-label"
LOT_LABEL = "planar-blocking-diode-lot-bag-label"


def _case(**overrides):
    case = {
        "part_id": "BD-PLANAR-12",
        "identity_code": "BD12A7",
        "lot_size": 500,
        "package_size": 25,
        "faces_mm": {
            CARRIER_BODY: (2.0, 0.6),
            CARRIER_PACKAGE: (30.0, 10.0),
            CARRIER_LOT_BAG: (60.0, 40.0),
        },
        "agreement": {
            "standing": AGREEMENT_RECORDED,
            "approach": LASER,
            "reference": "MRK-AGR-004",
        },
    }
    case.update(copy.deepcopy(overrides))
    return case


class AgreementStandingTests(unittest.TestCase):
    def test_a_recorded_agreement_naming_a_document_binds(self):
        result = validate_agreement(_case()["agreement"])
        self.assertTrue(result["binds"])
        self.assertEqual(result["findings"], [])

    def test_a_recorded_agreement_naming_no_document_does_not_bind(self):
        result = validate_agreement({"standing": AGREEMENT_RECORDED, "approach": LASER})
        self.assertFalse(result["binds"])
        self.assertTrue(any("nothing for either side" in f for f in result["findings"]))

    def test_a_verbal_agreement_binds_only_where_policy_says_so(self):
        block = {"standing": AGREEMENT_VERBAL, "approach": LASER}
        self.assertFalse(validate_agreement(block)["binds"])
        self.assertTrue(
            validate_agreement(block, {"accept_verbal_agreement": True})["binds"]
        )

    def test_a_superseded_agreement_does_not_bind_and_is_reported(self):
        result = validate_agreement({"standing": AGREEMENT_SUPERSEDED, "approach": INK})
        self.assertFalse(result["binds"])
        self.assertTrue(any("superseded" in f for f in result["findings"]))

    def test_a_proposal_nobody_answered_does_not_bind(self):
        result = validate_agreement({"standing": AGREEMENT_PROPOSED, "approach": LASER})
        self.assertFalse(result["binds"])

    def test_an_absent_agreement_does_not_bind(self):
        result = validate_agreement({"standing": AGREEMENT_ABSENT})
        self.assertFalse(result["binds"])
        self.assertTrue(any("settled with the customer" in f for f in result["findings"]))

    def test_an_agreement_naming_no_approach_cannot_bind(self):
        result = validate_agreement(
            {"standing": AGREEMENT_RECORDED, "reference": "MRK-AGR-004"}
        )
        self.assertFalse(result["binds"])
        self.assertTrue(any("names no marking approach" in f for f in result["findings"]))

    def test_an_unknown_standing_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_agreement({"standing": "sort-of-agreed", "approach": LASER})

    def test_an_uncatalogued_approach_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_agreement(
                {"standing": AGREEMENT_RECORDED, "approach": "sharpie-on-the-bag"}
            )


class CodeFootprintTests(unittest.TestCase):
    def test_a_code_footprint_grows_with_the_character_count(self):
        short = code_footprint_mm("BD12", 0.25)
        long = code_footprint_mm("BD12A7", 0.25)
        self.assertEqual(short["characters"], 4)
        self.assertGreater(long["width_mm"], short["width_mm"])

    def test_the_footprint_matches_the_declared_layout_rule(self):
        footprint = code_footprint_mm("ABCD", 0.5)
        self.assertAlmostEqual(footprint["width_mm"], 1.5, places=9)
        self.assertAlmostEqual(footprint["height_mm"], 0.5, places=9)

    def test_an_empty_code_is_rejected(self):
        with self.assertRaises(ValueError):
            code_footprint_mm("   ", 0.25)

    def test_a_non_positive_character_height_is_rejected(self):
        with self.assertRaises(ValueError):
            code_footprint_mm("BD12A7", 0.0)


class FaceFitTests(unittest.TestCase):
    def test_a_code_that_fits_the_diode_body_is_accepted(self):
        fit = assess_face_fit(LASER, "BD12A7", (2.0, 0.6))
        self.assertTrue(fit["fits"])
        self.assertEqual(fit["findings"], [])

    def test_a_code_wider_than_its_face_does_not_fit(self):
        fit = assess_face_fit(LASER, "BD12A7-REV-B-2026", (2.0, 0.6))
        self.assertFalse(fit["fits"])
        self.assertTrue(any("across a face" in f for f in fit["findings"]))

    def test_a_face_exactly_the_width_of_the_code_still_fits(self):
        footprint = code_footprint_mm("BD12A7", 0.25)
        fit = assess_face_fit(LASER, "BD12A7", (footprint["width_mm"], 0.25))
        self.assertTrue(fit["fits"])

    def test_a_character_height_below_the_legible_minimum_is_refused(self):
        fit = assess_face_fit(LASER, "BD12A7", (20.0, 20.0), 0.10)
        self.assertFalse(fit["legible"])
        self.assertFalse(fit["fits"])

    def test_a_character_height_exactly_on_the_minimum_stays_legible(self):
        minimum = MARKING_APPROACHES[INK]["min_character_height_mm"]
        fit = assess_face_fit(INK, "BD12A7", (20.0, 20.0), minimum)
        self.assertTrue(fit["legible"])
        self.assertTrue(fit["fits"])

    def test_a_face_that_is_not_a_width_height_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_face_fit(LASER, "BD12A7", 2.0)


class RetentionTests(unittest.TestCase):
    def test_a_laser_body_mark_reaches_integration(self):
        reach = retention_reach(LASER, "solar-array-integration")
        self.assertTrue(reach["reaches"])

    def test_an_ink_body_mark_stops_before_integration(self):
        reach = retention_reach(INK, "solar-array-integration")
        self.assertFalse(reach["reaches"])
        self.assertTrue(any("survives to" in f for f in reach["findings"]))

    def test_a_carrier_label_stops_at_incoming_inspection(self):
        self.assertFalse(retention_reach(CARRIER_LABEL, "diode-cleaning")["reaches"])
        self.assertTrue(
            retention_reach(CARRIER_LABEL, "diode-incoming-inspection")["reaches"]
        )

    def test_an_unknown_handling_stage_is_rejected(self):
        with self.assertRaises(ValueError):
            retention_reach(LASER, "sometime-later")


class GranularityTests(unittest.TestCase):
    def test_a_part_level_mark_resolves_one_diode(self):
        grain = identity_granularity(LASER, 500, 25)
        self.assertEqual(grain["granularity"], GRAIN_PART)
        self.assertEqual(grain["parts_per_mark"], 1)

    def test_a_package_level_mark_resolves_the_package(self):
        grain = identity_granularity(CARRIER_LABEL, 500, 25)
        self.assertEqual(grain["granularity"], GRAIN_PACKAGE)
        self.assertEqual(grain["parts_per_mark"], 25)

    def test_a_lot_level_mark_resolves_the_whole_lot(self):
        grain = identity_granularity(LOT_LABEL, 500, 25)
        self.assertEqual(grain["granularity"], GRAIN_LOT)
        self.assertEqual(grain["parts_per_mark"], 500)

    def test_a_package_larger_than_its_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            identity_granularity(CARRIER_LABEL, 10, 25)

    def test_a_fractional_lot_size_is_rejected(self):
        with self.assertRaises(ValueError):
            identity_granularity(LOT_LABEL, 500.5, 25)


class ApproachVerdictTests(unittest.TestCase):
    def test_the_laser_body_mark_is_acceptable_by_default(self):
        result = assess_marking_approach(LASER, _case())
        self.assertEqual(result["verdict"], APPROACH_ACCEPTABLE)
        self.assertEqual(result["findings"], [])

    def test_a_short_lived_mark_is_reported_as_retention_short(self):
        result = assess_marking_approach(INK, _case())
        self.assertEqual(result["verdict"], APPROACH_RETENTION_SHORT)

    def test_a_lot_label_is_reported_before_its_granularity_when_it_dies_first(self):
        result = assess_marking_approach(LOT_LABEL, _case())
        self.assertEqual(result["verdict"], APPROACH_RETENTION_SHORT)

    def test_granularity_is_the_verdict_once_retention_is_long_enough(self):
        case = _case(policy={"required_identity_through": "diode-incoming-inspection"})
        result = assess_marking_approach(CARRIER_LABEL, case)
        self.assertEqual(result["verdict"], APPROACH_GRANULARITY_SHORT)
        self.assertFalse(result["meets_granularity"])

    def test_a_code_that_does_not_fit_outranks_every_other_finding(self):
        case = _case(identity_code="BD12A7-REV-B-LOT-2026-0044")
        result = assess_marking_approach(LASER, case)
        self.assertEqual(result["verdict"], APPROACH_CODE_DOES_NOT_FIT)

    def test_an_approach_with_no_declared_face_is_rejected(self):
        case = _case(faces_mm={CARRIER_PACKAGE: (30.0, 10.0)})
        with self.assertRaises(ValueError):
            assess_marking_approach(LASER, case)


class SelectionTests(unittest.TestCase):
    def test_the_selection_recommends_the_longest_lived_workable_approach(self):
        options = select_marking_approach(_case())
        self.assertEqual(options["recommended"], LASER)
        self.assertEqual(options["acceptable"], [LASER])

    def test_a_selection_with_no_declared_face_at_all_is_rejected(self):
        with self.assertRaises(ValueError):
            select_marking_approach(_case(faces_mm={}))

    def test_a_relaxed_policy_widens_the_acceptable_set(self):
        case = _case(
            policy={
                "required_identity_through": "diode-incoming-inspection",
                "max_parts_per_mark": 25,
            }
        )
        options = select_marking_approach(case)
        self.assertIn(LASER, options["acceptable"])
        self.assertIn(CARRIER_LABEL, options["acceptable"])
        self.assertEqual(options["recommended"], LASER)


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve(self):
        settings = resolve_policy()
        self.assertEqual(settings["max_parts_per_mark"], 1)
        self.assertFalse(settings["accept_verbal_agreement"])

    def test_an_unknown_required_stage_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"required_identity_through": "eventually"})

    def test_a_zero_parts_per_mark_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"max_parts_per_mark": 0})


class DeliveryRollUpTests(unittest.TestCase):
    def test_an_agreed_workable_approach_is_accepted(self):
        result = assess_blocking_diode_marking(_case())
        self.assertEqual(result["verdict"], MARKING_ACCEPTED)
        self.assertEqual(result["approach_verdict"], APPROACH_ACCEPTABLE)
        self.assertEqual(result["findings"], [])

    def test_an_unagreed_approach_fails_before_the_mark_is_looked_at(self):
        case = _case(
            agreement={"standing": AGREEMENT_PROPOSED, "approach": LASER}
        )
        result = assess_blocking_diode_marking(case)
        self.assertEqual(result["verdict"], MARKING_NOT_ACCEPTED)
        self.assertEqual(result["approach_verdict"], APPROACH_NOT_AGREED)

    def test_an_agreed_but_short_lived_approach_is_held_and_an_option_named(self):
        case = _case(
            agreement={
                "standing": AGREEMENT_RECORDED,
                "approach": INK,
                "reference": "MRK-AGR-007",
            }
        )
        result = assess_blocking_diode_marking(case)
        self.assertEqual(result["verdict"], MARKING_NOT_ACCEPTED)
        self.assertEqual(result["approach_verdict"], APPROACH_RETENTION_SHORT)
        self.assertEqual(result["recommended_approach"], LASER)
        self.assertTrue(any("settle with the customer" in f for f in result["findings"]))

    def test_an_empty_part_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_marking(_case(part_id="  "))


if __name__ == "__main__":
    unittest.main(verbosity=1)
