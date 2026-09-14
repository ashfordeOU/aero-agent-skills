"""Contract tests for the clause 7.5.1.4.3 bare cell crack and print screen."""

import unittest

from e2008_bare_cell_cracks_and_fingerprints_logic import (
    ACCEPT,
    CLEAN_AND_REINSPECT,
    CRACK,
    DEFAULT_BARE_CELL_CRITERIA,
    FINGERPRINT,
    INSPECTION_INCOMPLETE,
    REFER_FOR_REVIEW,
    REJECT,
    assess_bare_cell_cracks_and_fingerprints,
    assess_cell,
    categorize_crack_indication,
    categorize_fingerprint_indication,
    condition_findings,
    crack_detection_floor_mm,
    validate_bare_cell_criteria,
    validate_indication,
    validate_inspection_conditions,
    worst_disposition,
)


def _criteria(**overrides):
    criteria = dict(DEFAULT_BARE_CELL_CRITERIA)
    criteria.update(overrides)
    return criteria


def _conditions(**overrides):
    conditions = {
        "working_distance_mm": 300.0,
        "magnification": 1.0,
        "illuminance_lux": 1500.0,
    }
    conditions.update(overrides)
    return conditions


def _crack(**overrides):
    indication = {"kind": CRACK, "length_mm": 2.0, "confirmed": True}
    indication.update(overrides)
    return indication


def _print(**overrides):
    indication = {
        "kind": FINGERPRINT,
        "area_mm2": 8.0,
        "removable": True,
        "on_contact_area": False,
    }
    indication.update(overrides)
    return indication


def _cell(**overrides):
    cell = {
        "id": "cell-01",
        "declared_faces": 2,
        "faces_examined": 2,
        "cleaning_cycles_used": 0,
        "conditions": _conditions(),
        "indications": [],
    }
    cell.update(overrides)
    return cell


def _ratio(value, expected):
    return value / expected


class CriteriaTests(unittest.TestCase):
    def test_the_default_criteria_validate(self):
        self.assertIs(
            validate_bare_cell_criteria(DEFAULT_BARE_CELL_CRITERIA),
            DEFAULT_BARE_CELL_CRITERIA,
        )

    def test_a_non_mapping_criteria_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_bare_cell_criteria("no crack, no print")

    def test_a_zero_illuminance_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_bare_cell_criteria(_criteria(min_illuminance_lux=0.0))

    def test_a_criteria_set_allowing_no_cleaning_rejected(self):
        with self.assertRaises(ValueError):
            validate_bare_cell_criteria(_criteria(max_cleaning_cycles=0))

    def test_a_non_integer_cleaning_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_bare_cell_criteria(_criteria(max_cleaning_cycles=2.5))


class DetectionFloorTests(unittest.TestCase):
    def test_the_floor_at_three_hundred_millimetres_is_about_a_tenth(self):
        floor = crack_detection_floor_mm(300.0, 1.0, 1.0)
        self.assertAlmostEqual(_ratio(floor, 0.0873), 1.0, places=3)

    def test_the_floor_scales_with_the_working_distance(self):
        near = crack_detection_floor_mm(300.0, 1.0, 1.0)
        far = crack_detection_floor_mm(600.0, 1.0, 1.0)
        self.assertAlmostEqual(_ratio(far, 2.0 * near), 1.0, places=9)

    def test_magnification_divides_the_floor(self):
        unaided = crack_detection_floor_mm(300.0, 1.0, 1.0)
        aided = crack_detection_floor_mm(300.0, 1.0, 10.0)
        self.assertAlmostEqual(_ratio(unaided, 10.0 * aided), 1.0, places=9)

    def test_a_zero_working_distance_rejected(self):
        with self.assertRaises(ValueError):
            crack_detection_floor_mm(0.0, 1.0, 1.0)

    def test_a_negative_magnification_rejected(self):
        with self.assertRaises(ValueError):
            crack_detection_floor_mm(300.0, 1.0, -2.0)


class ConditionTests(unittest.TestCase):
    def test_sound_conditions_raise_no_finding(self):
        self.assertEqual(condition_findings(_conditions(), _criteria()), ())

    def test_an_under_lit_examination_is_flagged(self):
        findings = condition_findings(
            _conditions(illuminance_lux=200.0), _criteria()
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("lux", findings[0])

    def test_illuminance_exactly_at_the_floor_is_admissible(self):
        floor = DEFAULT_BARE_CELL_CRITERIA["min_illuminance_lux"]
        self.assertAlmostEqual(_ratio(floor, 1000.0), 1.0, places=12)
        self.assertEqual(
            condition_findings(_conditions(illuminance_lux=floor), _criteria()), ()
        )

    def test_an_over_long_working_distance_is_flagged(self):
        findings = condition_findings(
            _conditions(working_distance_mm=900.0), _criteria()
        )
        self.assertEqual(len(findings), 1)

    def test_both_conditions_can_fail_at_once(self):
        findings = condition_findings(
            _conditions(working_distance_mm=900.0, illuminance_lux=50.0), _criteria()
        )
        self.assertEqual(len(findings), 2)

    def test_missing_conditions_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_conditions(None, _criteria())

    def test_a_negative_illuminance_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_conditions(
                _conditions(illuminance_lux=-5.0), _criteria()
            )


class IndicationValidationTests(unittest.TestCase):
    def test_an_unknown_indication_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_indication({"kind": "scratch", "length_mm": 1.0})

    def test_a_crack_without_a_confirmation_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_indication({"kind": CRACK, "length_mm": 1.0})

    def test_a_print_without_a_contact_area_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_indication(
                {"kind": FINGERPRINT, "area_mm2": 4.0, "removable": True}
            )

    def test_a_non_boolean_confirmation_rejected(self):
        with self.assertRaises(ValueError):
            validate_indication(_crack(confirmed="yes"))


class CrackDispositionTests(unittest.TestCase):
    def test_a_confirmed_crack_is_rejected_however_short(self):
        disposition, reason = categorize_crack_indication(
            _crack(length_mm=0.2), 0.09, _criteria()
        )
        self.assertEqual(disposition, REJECT)
        self.assertIn("no crack", reason)

    def test_a_long_confirmed_crack_is_rejected_too(self):
        disposition, _reason = categorize_crack_indication(
            _crack(length_mm=30.0), 0.09, _criteria()
        )
        self.assertEqual(disposition, REJECT)

    def test_an_unconfirmed_indication_above_the_floor_goes_to_review(self):
        disposition, reason = categorize_crack_indication(
            _crack(length_mm=1.0, confirmed=False), 0.09, _criteria()
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("confirming look", reason)

    def test_an_unconfirmed_indication_below_the_floor_questions_provenance(self):
        disposition, reason = categorize_crack_indication(
            _crack(length_mm=0.01, confirmed=False), 0.09, _criteria()
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("provenance", reason)

    def test_an_indication_exactly_at_the_floor_is_above_it(self):
        floor = crack_detection_floor_mm(300.0, 1.0, 1.0)
        self.assertAlmostEqual(_ratio(floor, floor), 1.0, places=12)
        _disposition, reason = categorize_crack_indication(
            _crack(length_mm=floor, confirmed=False), floor, _criteria()
        )
        self.assertIn("confirming look", reason)

    def test_a_print_handed_to_the_crack_router_rejected(self):
        with self.assertRaises(ValueError):
            categorize_crack_indication(_print(), 0.09, _criteria())


class FingerprintDispositionTests(unittest.TestCase):
    def test_a_removable_print_away_from_the_contacts_is_cleaned(self):
        disposition, _reason = categorize_fingerprint_indication(
            _print(), 0, _criteria()
        )
        self.assertEqual(disposition, CLEAN_AND_REINSPECT)

    def test_a_print_on_a_contact_area_is_rejected(self):
        disposition, reason = categorize_fingerprint_indication(
            _print(on_contact_area=True), 0, _criteria()
        )
        self.assertEqual(disposition, REJECT)
        self.assertIn("weld zone", reason)

    def test_a_print_that_will_not_come_off_is_rejected(self):
        disposition, _reason = categorize_fingerprint_indication(
            _print(removable=False), 0, _criteria()
        )
        self.assertEqual(disposition, REJECT)

    def test_a_cell_out_of_cleaning_cycles_is_rejected(self):
        disposition, reason = categorize_fingerprint_indication(
            _print(), 2, _criteria()
        )
        self.assertEqual(disposition, REJECT)
        self.assertIn("cleaning cycles", reason)

    def test_an_oversize_print_goes_to_review_rather_than_straight_to_cleaning(self):
        disposition, _reason = categorize_fingerprint_indication(
            _print(area_mm2=400.0), 0, _criteria()
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)

    def test_a_print_exactly_at_the_cleanable_area_is_still_cleaned(self):
        limit = DEFAULT_BARE_CELL_CRITERIA["max_cleanable_fingerprint_area_mm2"]
        self.assertAlmostEqual(_ratio(limit, 25.0), 1.0, places=12)
        disposition, _reason = categorize_fingerprint_indication(
            _print(area_mm2=limit), 0, _criteria()
        )
        self.assertEqual(disposition, CLEAN_AND_REINSPECT)

    def test_a_crack_handed_to_the_print_router_rejected(self):
        with self.assertRaises(ValueError):
            categorize_fingerprint_indication(_crack(), 0, _criteria())


class WorstDispositionTests(unittest.TestCase):
    def test_an_empty_set_accepts(self):
        self.assertEqual(worst_disposition([]), ACCEPT)

    def test_severity_beats_record_order(self):
        self.assertEqual(
            worst_disposition([REJECT, CLEAN_AND_REINSPECT, ACCEPT]), REJECT
        )

    def test_review_outranks_cleaning(self):
        self.assertEqual(
            worst_disposition([CLEAN_AND_REINSPECT, REFER_FOR_REVIEW]),
            REFER_FOR_REVIEW,
        )

    def test_an_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition([ACCEPT, "maybe"])


class CellAssessmentTests(unittest.TestCase):
    def test_a_clean_uncracked_cell_is_accepted(self):
        result = assess_cell(_cell(), _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_the_detection_floor_travels_with_the_verdict(self):
        result = assess_cell(_cell(), _criteria())
        self.assertAlmostEqual(
            _ratio(
                result["crack_detection_floor_mm"],
                crack_detection_floor_mm(300.0, 1.0, 1.0),
            ),
            1.0,
            places=12,
        )

    def test_one_confirmed_crack_rejects_the_cell(self):
        result = assess_cell(_cell(indications=[_crack()]), _criteria())
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["crack_indications"], 1)

    def test_a_crack_found_under_poor_light_still_rejects(self):
        result = assess_cell(
            _cell(
                conditions=_conditions(illuminance_lux=50.0),
                indications=[_crack()],
            ),
            _criteria(),
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_an_acceptance_under_poor_light_is_withheld(self):
        result = assess_cell(
            _cell(conditions=_conditions(illuminance_lux=50.0)), _criteria()
        )
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertFalse(result["examination_sound"])

    def test_an_unexamined_face_withholds_the_acceptance(self):
        result = assess_cell(_cell(faces_examined=1), _criteria())
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)

    def test_more_faces_examined_than_declared_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell(_cell(faces_examined=5), _criteria())

    def test_a_magnified_record_is_advised_not_discarded(self):
        result = assess_cell(
            _cell(conditions=_conditions(magnification=10.0), indications=[_crack()]),
            _criteria(),
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_unaided_floor_is_reported_beside_the_aided_one(self):
        result = assess_cell(
            _cell(conditions=_conditions(magnification=10.0)), _criteria()
        )
        self.assertAlmostEqual(
            _ratio(
                result["unaided_detection_floor_mm"],
                10.0 * result["crack_detection_floor_mm"],
            ),
            1.0,
            places=9,
        )

    def test_a_cleanable_print_leaves_the_cell_in_cleaning(self):
        result = assess_cell(_cell(indications=[_print()]), _criteria())
        self.assertEqual(result["verdict"], CLEAN_AND_REINSPECT)
        self.assertEqual(result["fingerprint_indications"], 1)

    def test_a_crack_outranks_a_cleanable_print_on_the_same_cell(self):
        result = assess_cell(_cell(indications=[_print(), _crack()]), _criteria())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_blank_cell_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell(_cell(id="   "), _criteria())

    def test_a_non_sequence_indication_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell(_cell(indications="one crack"), _criteria())


class LotRollupTests(unittest.TestCase):
    def test_a_healthy_lot_accepts_every_cell(self):
        lot = {"id": "lot-a", "cells": [_cell(), _cell(id="cell-02")]}
        result = assess_bare_cell_cracks_and_fingerprints(lot, _criteria())
        self.assertEqual(result["counts"][ACCEPT], 2)
        self.assertAlmostEqual(result["accepted_fraction"], 1.0, places=9)

    def test_the_rejected_fraction_is_reported(self):
        lot = {
            "id": "lot-b",
            "cells": [
                _cell(),
                _cell(id="cell-02", indications=[_crack()]),
                _cell(id="cell-03", indications=[_crack()]),
                _cell(id="cell-04"),
            ],
        }
        result = assess_bare_cell_cracks_and_fingerprints(lot, _criteria())
        self.assertAlmostEqual(result["rejected_fraction"], 0.5, places=9)

    def test_the_cells_not_accepted_are_named(self):
        lot = {
            "id": "lot-c",
            "cells": [_cell(), _cell(id="cell-02", indications=[_print()])],
        }
        result = assess_bare_cell_cracks_and_fingerprints(lot, _criteria())
        self.assertEqual(result["cells_not_accepted"], ("cell-02",))

    def test_the_worst_detection_floor_across_the_lot_is_reported(self):
        lot = {
            "id": "lot-d",
            "cells": [
                _cell(),
                _cell(
                    id="cell-02",
                    conditions=_conditions(working_distance_mm=390.0),
                ),
            ],
        }
        result = assess_bare_cell_cracks_and_fingerprints(lot, _criteria())
        self.assertAlmostEqual(
            _ratio(
                result["worst_detection_floor_mm"],
                crack_detection_floor_mm(390.0, 1.0, 1.0),
            ),
            1.0,
            places=12,
        )

    def test_a_duplicate_cell_id_rejected(self):
        lot = {"id": "lot-e", "cells": [_cell(), _cell()]}
        with self.assertRaises(ValueError):
            assess_bare_cell_cracks_and_fingerprints(lot, _criteria())

    def test_an_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_cracks_and_fingerprints({"id": "lot-f", "cells": []})

    def test_a_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_cracks_and_fingerprints(["cell-01"])


if __name__ == "__main__":
    unittest.main()
