#!/usr/bin/env python3
"""Contract test for external protection diode marking (offline).

Walks the clause workflow step by step: the standing of the agreement
that picked the approach and the carrier change the customer never saw,
how far down the handling chain a mark on each carrier survives, the
shortfall against the stage identity is owed to, whether the code
physically fits the face it is put on, what a coarse granularity really
resolves a delivered part to, the per-type verdict and the roll-up into
one delivery verdict. This is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_protection_diode_marking_logic import (
    GRANULARITY_ITEM,
    GRANULARITY_LOT,
    GRANULARITY_NONE,
    GRANULARITY_PACKAGE,
    MARKING_AGREED,
    MARKING_NOT_AGREED,
    MARKING_SHORT,
    agreement_standing,
    assess_diode_marking,
    assess_diode_marking_scheme,
    carrier_retention_stage,
    code_fits_marking_face,
    identity_resolution,
    retention_shortfall,
)

SOUND_TYPE = {
    "part_type": "PD-BODY-A",
    "agreement_standing": "agreed-and-recorded",
    "agreed_carrier": "diode-body",
    "mark_carrier": "diode-body",
    "granularity": GRANULARITY_ITEM,
    "items_delivered": 40,
    "items_per_package": 10,
    "code_characters": 8,
    "character_pitch_mm": 0.5,
    "face_length_mm": 6.0,
}


def _diode(part_type, **overrides):
    record = copy.deepcopy(SOUND_TYPE)
    record["part_type"] = part_type
    record.update(overrides)
    return record


class AgreementTests(unittest.TestCase):
    def test_a_recorded_agreement_binds_with_no_findings(self):
        result = agreement_standing("agreed-and-recorded")
        self.assertTrue(result["binding"])
        self.assertFalse(result["needs_concession"])
        self.assertEqual(result["findings"], [])

    def test_a_scheme_the_supplier_chose_alone_does_not_bind(self):
        result = agreement_standing("not-sought")
        self.assertFalse(result["binding"])
        self.assertTrue(result["findings"])

    def test_a_proposal_nobody_answered_does_not_bind(self):
        self.assertFalse(agreement_standing("proposed-not-agreed")["binding"])

    def test_a_verbal_agreement_binds_only_under_concession(self):
        result = agreement_standing("agreed-verbally")
        self.assertTrue(result["binding"])
        self.assertTrue(result["needs_concession"])

    def test_a_superseded_agreement_binds_only_under_concession(self):
        result = agreement_standing("superseded")
        self.assertTrue(result["binding"])
        self.assertTrue(result["needs_concession"])

    def test_a_carrier_change_the_customer_never_saw_is_reported(self):
        result = agreement_standing(
            "agreed-and-recorded", "diode-body", "unit-package"
        )
        self.assertTrue(result["needs_concession"])
        self.assertTrue(any("has not seen" in f for f in result["findings"]))

    def test_unknown_standing_rejected(self):
        with self.assertRaises(ValueError):
            agreement_standing("everyone-seemed-happy")


class RetentionTests(unittest.TestCase):
    def test_a_mark_on_the_part_survives_to_mounting(self):
        result = carrier_retention_stage("diode-body")
        self.assertEqual(result["retention_stage"], "mounted-on-panel")
        self.assertEqual(result["findings"], [])

    def test_a_mark_on_a_lead_is_lost_when_the_lead_is_formed(self):
        result = carrier_retention_stage("diode-lead")
        self.assertEqual(result["retention_stage"], "kitted-loose")
        self.assertTrue(result["findings"])

    def test_a_mark_on_the_bag_ends_when_the_part_leaves_it(self):
        self.assertEqual(
            carrier_retention_stage("unit-package")["retention_stage"],
            "incoming-inspection",
        )

    def test_a_mark_on_the_tray_ends_at_the_shipper(self):
        self.assertEqual(
            carrier_retention_stage("shipping-tray")["retention_stage"],
            "sealed-package",
        )

    def test_no_carrier_retains_nothing(self):
        result = carrier_retention_stage("none")
        self.assertIsNone(result["retention_stage"])
        self.assertEqual(result["retention_rank"], -1)

    def test_unknown_carrier_rejected(self):
        with self.assertRaises(ValueError):
            carrier_retention_stage("the-delivery-note")

    def test_shortfall_is_counted_in_handling_steps(self):
        gap = retention_shortfall("mounted-on-panel", "incoming-inspection")
        self.assertEqual(gap["steps_short"], 2)
        self.assertFalse(gap["meets_requirement"])

    def test_surviving_past_the_required_stage_still_meets_it(self):
        gap = retention_shortfall("kitted-loose", "mounted-on-panel")
        self.assertEqual(gap["steps_short"], 0)
        self.assertTrue(gap["meets_requirement"])

    def test_an_unmarked_delivery_is_short_of_every_stage(self):
        gap = retention_shortfall("sealed-package", None)
        self.assertEqual(gap["steps_short"], 1)


class CodeFitTests(unittest.TestCase):
    def test_a_short_code_fits_a_long_face(self):
        result = code_fits_marking_face(8, 0.5, 6.0)
        self.assertTrue(result["fits"])
        self.assertAlmostEqual(result["required_length_mm"], 4.0, places=9)

    def test_a_code_cut_exactly_to_the_face_is_accepted(self):
        result = code_fits_marking_face(3, 0.1, 0.3)
        self.assertTrue(result["fits"])
        self.assertAlmostEqual(result["required_length_mm"], 0.3, places=9)

    def test_a_code_longer_than_the_face_is_reported(self):
        result = code_fits_marking_face(20, 0.5, 6.0)
        self.assertFalse(result["fits"])
        self.assertTrue(result["findings"])

    def test_zero_character_code_rejected(self):
        with self.assertRaises(ValueError):
            code_fits_marking_face(0, 0.5, 6.0)

    def test_non_positive_pitch_rejected(self):
        with self.assertRaises(ValueError):
            code_fits_marking_face(8, 0.0, 6.0)

    def test_non_positive_face_rejected(self):
        with self.assertRaises(ValueError):
            code_fits_marking_face(8, 0.5, -1.0)


class ResolutionTests(unittest.TestCase):
    def test_item_granularity_resolves_a_part_to_itself(self):
        result = identity_resolution(GRANULARITY_ITEM, 40)
        self.assertEqual(result["resolved_set_size"], 1)
        self.assertAlmostEqual(result["resolution_share"], 1.0, places=9)

    def test_package_granularity_resolves_a_part_to_its_bag(self):
        result = identity_resolution(GRANULARITY_PACKAGE, 40, 10)
        self.assertEqual(result["resolved_set_size"], 10)
        self.assertAlmostEqual(result["resolution_share"], 0.1, places=9)

    def test_lot_granularity_resolves_a_part_to_the_whole_delivery(self):
        result = identity_resolution(GRANULARITY_LOT, 40, 10)
        self.assertAlmostEqual(result["resolution_share"], 1.0 / 40.0, places=9)

    def test_no_granularity_resolves_nothing(self):
        result = identity_resolution(GRANULARITY_NONE, 40)
        self.assertAlmostEqual(result["resolution_share"], 0.0, places=9)

    def test_a_package_larger_than_the_delivery_rejected(self):
        with self.assertRaises(ValueError):
            identity_resolution(GRANULARITY_PACKAGE, 5, 10)

    def test_zero_delivered_items_rejected(self):
        with self.assertRaises(ValueError):
            identity_resolution(GRANULARITY_ITEM, 0)


class TypeVerdictTests(unittest.TestCase):
    def test_a_sound_type_is_agreed_and_adequate(self):
        result = assess_diode_marking(_diode("PD-1"))
        self.assertEqual(result["verdict"], MARKING_AGREED)
        self.assertEqual(result["findings"], [])

    def test_a_scheme_nobody_agreed_to_fails_however_good_the_mark(self):
        result = assess_diode_marking(
            _diode("PD-2", agreement_standing="not-sought")
        )
        self.assertEqual(result["verdict"], MARKING_NOT_AGREED)

    def test_an_unmarked_type_is_graded_without_code_geometry(self):
        result = assess_diode_marking(
            _diode(
                "PD-3",
                mark_carrier="none",
                agreed_carrier=None,
                code_characters=None,
                character_pitch_mm=None,
                face_length_mm=None,
            )
        )
        self.assertEqual(result["verdict"], MARKING_NOT_AGREED)
        self.assertIsNone(result["code_fit"])

    def test_a_mark_on_the_bag_falls_short_of_the_mounting_stage(self):
        result = assess_diode_marking(
            _diode("PD-4", mark_carrier="unit-package",
                   agreed_carrier="unit-package")
        )
        self.assertEqual(result["verdict"], MARKING_SHORT)
        self.assertEqual(result["shortfall"]["steps_short"], 2)

    def test_a_package_level_code_is_below_the_resolution_floor(self):
        result = assess_diode_marking(
            _diode("PD-5", granularity=GRANULARITY_PACKAGE)
        )
        self.assertEqual(result["verdict"], MARKING_SHORT)
        self.assertFalse(result["resolves_enough"])

    def test_a_code_that_does_not_fit_the_body_is_short(self):
        result = assess_diode_marking(_diode("PD-6", code_characters=24))
        self.assertEqual(result["verdict"], MARKING_SHORT)
        self.assertFalse(result["code_fit"]["fits"])

    def test_a_verbal_agreement_alone_holds_the_type_at_short(self):
        result = assess_diode_marking(
            _diode("PD-7", agreement_standing="agreed-verbally")
        )
        self.assertEqual(result["verdict"], MARKING_SHORT)

    def test_policy_can_relax_the_required_retention_stage(self):
        record = _diode("PD-8", mark_carrier="diode-lead",
                        agreed_carrier="diode-lead")
        strict = assess_diode_marking(record)
        relaxed = assess_diode_marking(record, {"required_retention_stage":
                                                "kitted-loose"})
        self.assertEqual(strict["verdict"], MARKING_SHORT)
        self.assertEqual(relaxed["verdict"], MARKING_AGREED)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_marking("the diodes were all marked on the body")


class DeliveryRollUpTests(unittest.TestCase):
    def _case(self, records, policy=None):
        case = {"delivery_id": "DEL-401", "diode_types": records}
        if policy is not None:
            case["policy"] = policy
        return case

    def test_a_sound_delivery_is_fully_adequate(self):
        result = assess_diode_marking_scheme(
            self._case([_diode("PD-1"), _diode("PD-2")])
        )
        self.assertEqual(result["verdict"], MARKING_AGREED)
        self.assertTrue(result["fully_adequate"])
        self.assertAlmostEqual(result["adequate_share"], 1.0, places=9)

    def test_one_weak_type_pulls_the_delivery_verdict_down(self):
        result = assess_diode_marking_scheme(
            self._case(
                [_diode("PD-1"), _diode("PD-2", granularity=GRANULARITY_PACKAGE)]
            )
        )
        self.assertEqual(result["verdict"], MARKING_SHORT)
        self.assertEqual(result["weakest_type"], "PD-2")
        self.assertAlmostEqual(result["adequate_share"], 0.5, places=9)

    def test_unmarked_types_are_named(self):
        result = assess_diode_marking_scheme(
            self._case(
                [_diode("PD-1"), _diode("PD-9", agreement_standing="not-sought")]
            )
        )
        self.assertEqual(result["unmarked_types"], ["PD-9"])
        self.assertEqual(result["verdict"], MARKING_NOT_AGREED)

    def test_a_repeated_part_type_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_marking_scheme(
                self._case([_diode("PD-1"), _diode("PD-1")])
            )

    def test_empty_delivery_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_marking_scheme(self._case([]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_marking_scheme("marking was agreed with the customer")


if __name__ == "__main__":
    unittest.main()
