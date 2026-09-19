#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 10.2.2 special marking leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_special_marking_cases.py
"""

import unittest

from q6005_special_marking_cases_logic import (
    ACCEPTANCE_INDEX,
    COMPENSATING_CONTROLS,
    CONTROL_STATE_CREDIT,
    CONTROL_WEIGHTS,
    DIRECT_MARKING_COMPATIBLE_FINISHES,
    DIRECT_MARKING_INCOMPATIBLE_FINISHES,
    IDENTIFICATION_ARRANGEMENTS,
    MANDATORY_IDENTIFICATION_FIELDS,
    MARKING_TOLERANCE,
    MINIMUM_CHARACTER_HEIGHT_MM,
    VERDICTS,
    admissible_arrangements,
    arrangement_rank,
    assess_control,
    assess_special_marking_case,
    control_state_credit,
    finish_permits_direct_marking,
    identification_adequacy_index,
    mark_line_length_mm,
    required_controls,
    required_mark_area_mm2,
    select_identification_arrangement,
    special_case_reason,
)

SMALL_BODY_MM2 = 2.0
LARGE_BODY_MM2 = 50.0
GOOD_FINISH = "plated-metal-lid"
BAD_FINISH = "soft-polymer-overcoat"

ALL_ARRANGEMENTS = (
    "permanent-attached-tag",
    "individual-sealed-container-marking",
    "intermediate-package-marking",
)


def every_control(state="implemented-and-evidenced"):
    """Every compensating control in one state."""
    return {name: state for name in CONTROL_WEIGHTS}


def run(**overrides):
    """Grade one special marking case."""
    case = {
        "unit_id": "HYB-SM-1",
        "free_body_area_mm2": SMALL_BODY_MM2,
        "body_finish": GOOD_FINISH,
        "available_arrangements": ALL_ARRANGEMENTS,
        "controls": every_control(),
        "proposed_arrangement": None,
    }
    case.update(overrides)
    return assess_special_marking_case(**case)


class MarkFootprintTests(unittest.TestCase):
    def test_a_longer_field_needs_a_longer_line(self):
        short = mark_line_length_mm(4, MINIMUM_CHARACTER_HEIGHT_MM)
        long = mark_line_length_mm(12, MINIMUM_CHARACTER_HEIGHT_MM)
        self.assertGreater(long, short)

    def test_a_single_character_line_carries_no_inter_character_pitch(self):
        self.assertAlmostEqual(
            mark_line_length_mm(1, 1.0), 0.62, places=9
        )

    def test_a_zero_character_field_is_rejected(self):
        with self.assertRaises(ValueError):
            mark_line_length_mm(0, 1.0)

    def test_a_taller_character_needs_more_body_area(self):
        small = required_mark_area_mm2(MINIMUM_CHARACTER_HEIGHT_MM)
        big = required_mark_area_mm2(1.0)
        self.assertGreater(big, small)

    def test_an_unknown_identification_field_is_rejected(self):
        with self.assertRaises(ValueError):
            required_mark_area_mm2(1.0, ["batch-colour-dot"])

    def test_a_non_positive_character_height_is_rejected(self):
        with self.assertRaises(ValueError):
            required_mark_area_mm2(0.0)

    def test_every_mandatory_field_carries_a_character_budget(self):
        for name, characters in MANDATORY_IDENTIFICATION_FIELDS.items():
            self.assertGreaterEqual(characters, 1, name)


class SpecialCaseSubstantiationTests(unittest.TestCase):
    def test_a_compatible_finish_permits_a_direct_mark(self):
        for finish in DIRECT_MARKING_COMPATIBLE_FINISHES:
            self.assertTrue(finish_permits_direct_marking(finish))

    def test_an_incompatible_finish_does_not_permit_a_direct_mark(self):
        for finish in DIRECT_MARKING_INCOMPATIBLE_FINISHES:
            self.assertFalse(finish_permits_direct_marking(finish))

    def test_an_unknown_finish_is_an_input_error_not_a_silent_pass(self):
        with self.assertRaises(ValueError):
            finish_permits_direct_marking("whatever-the-shop-had")

    def test_a_body_with_room_is_not_a_special_case(self):
        self.assertIsNone(special_case_reason(LARGE_BODY_MM2, GOOD_FINISH))

    def test_a_body_too_small_for_the_field_set_is_a_special_case(self):
        self.assertEqual(
            special_case_reason(SMALL_BODY_MM2, GOOD_FINISH), "free-body-area-too-small"
        )

    def test_a_finish_that_cannot_hold_lettering_is_a_special_case(self):
        self.assertEqual(
            special_case_reason(LARGE_BODY_MM2, BAD_FINISH),
            "body-finish-cannot-hold-a-mark",
        )

    def test_the_area_test_is_taken_at_the_legibility_floor(self):
        needed = required_mark_area_mm2(MINIMUM_CHARACTER_HEIGHT_MM)
        self.assertIsNone(special_case_reason(needed, GOOD_FINISH))

    def test_lettering_below_the_legibility_floor_is_rejected(self):
        with self.assertRaises(ValueError):
            special_case_reason(LARGE_BODY_MM2, GOOD_FINISH, 0.05)


class ArrangementSelectionTests(unittest.TestCase):
    def test_a_direct_mark_ranks_ahead_of_every_alternative(self):
        for name, rank in IDENTIFICATION_ARRANGEMENTS.items():
            if name != "direct-body-marking":
                self.assertGreater(rank, IDENTIFICATION_ARRANGEMENTS["direct-body-marking"])

    def test_an_unknown_arrangement_is_rejected(self):
        with self.assertRaises(ValueError):
            arrangement_rank("write-it-on-the-box-in-pencil")

    def test_a_case_that_is_not_special_admits_only_the_direct_mark(self):
        self.assertEqual(admissible_arrangements(None), ("direct-body-marking",))

    def test_a_finish_limited_case_cannot_fall_back_to_a_group_package(self):
        self.assertNotIn(
            "intermediate-package-marking",
            admissible_arrangements("body-finish-cannot-hold-a-mark"),
        )

    def test_the_best_admissible_arrangement_is_selected(self):
        selected = select_identification_arrangement(
            "free-body-area-too-small", ALL_ARRANGEMENTS
        )
        self.assertEqual(selected, "permanent-attached-tag")

    def test_a_carrier_register_alone_is_never_admissible(self):
        selected = select_identification_arrangement(
            "free-body-area-too-small", ["carrier-position-register-only"]
        )
        self.assertIsNone(selected)

    def test_an_empty_availability_list_is_rejected(self):
        with self.assertRaises(ValueError):
            select_identification_arrangement("free-body-area-too-small", [])


class CompensatingControlTests(unittest.TestCase):
    def test_a_weaker_arrangement_makes_more_controls_mandatory(self):
        tag = required_controls("permanent-attached-tag")
        group = required_controls("intermediate-package-marking")
        self.assertGreater(len(group), len(tag))

    def test_every_mandatory_control_carries_a_weight(self):
        for name in COMPENSATING_CONTROLS:
            self.assertIn(name, CONTROL_WEIGHTS)

    def test_an_unknown_control_state_is_rejected(self):
        with self.assertRaises(ValueError):
            control_state_credit("someone-said-it-was-fine")

    def test_an_absent_mandatory_control_is_marked_missing(self):
        record = assess_control(
            "serial-register-held-by-manufacturer", "absent", "permanent-attached-tag"
        )
        self.assertTrue(record["mandatory_missing"])
        self.assertIn("mandatory-compensating-control-missing", record["findings"])

    def test_an_implemented_control_earns_its_full_weight(self):
        record = assess_control(
            "serial-register-held-by-manufacturer",
            "implemented-and-evidenced",
            "permanent-attached-tag",
        )
        self.assertAlmostEqual(
            record["weighted_credit"],
            CONTROL_WEIGHTS["serial-register-held-by-manufacturer"],
            places=9,
        )
        self.assertEqual(record["findings"], [])

    def test_a_full_control_set_reaches_a_full_index(self):
        records = [
            assess_control(name, "implemented-and-evidenced", "intermediate-package-marking")
            for name in required_controls("intermediate-package-marking")
        ]
        self.assertAlmostEqual(identification_adequacy_index(records), 1.0, places=9)

    def test_an_empty_control_set_is_rejected(self):
        with self.assertRaises(ValueError):
            identification_adequacy_index([])


class WholeCaseTests(unittest.TestCase):
    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_substantiated_case_with_full_controls_is_accepted(self):
        result = run()
        self.assertEqual(result["verdict"], "alternative-identification-accepted")
        self.assertTrue(result["identification_accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["identification_adequacy_index"], 1.0, places=9)

    def test_a_body_that_can_be_marked_directly_needs_no_alternative(self):
        result = run(free_body_area_mm2=LARGE_BODY_MM2, proposed_arrangement=None)
        self.assertEqual(result["verdict"], "direct-body-marking-required")
        self.assertEqual(result["selected_arrangement"], "direct-body-marking")

    def test_an_alternative_on_a_markable_body_is_not_substantiated(self):
        result = run(
            free_body_area_mm2=LARGE_BODY_MM2,
            proposed_arrangement="intermediate-package-marking",
        )
        self.assertEqual(result["verdict"], "special-marking-case-not-substantiated")
        self.assertFalse(result["identification_accepted"])

    def test_a_missing_mandatory_control_denies_the_arrangement(self):
        controls = every_control()
        del controls["serial-register-held-by-manufacturer"]
        result = run(controls=controls)
        self.assertEqual(result["verdict"], "alternative-identification-not-accepted")
        self.assertIn(
            "mandatory-compensating-control-missing",
            [f["finding"] for f in result["findings"]],
        )

    def test_one_unevidenced_control_leaves_the_arrangement_open_not_denied(self):
        result = run(
            controls={
                "serial-register-held-by-manufacturer": "implemented-not-evidenced",
                "arrangement-named-in-delivery-documentation": "implemented-and-evidenced",
            },
            available_arrangements=["permanent-attached-tag"],
        )
        self.assertEqual(
            result["verdict"], "alternative-identification-accepted-with-open-actions"
        )
        self.assertGreater(result["identification_adequacy_index"], ACCEPTANCE_INDEX)

    def test_a_wholly_unevidenced_control_set_falls_under_the_acceptance_index(self):
        result = run(
            controls=every_control("implemented-not-evidenced"),
            available_arrangements=["permanent-attached-tag"],
        )
        self.assertLess(result["identification_adequacy_index"], ACCEPTANCE_INDEX)
        self.assertEqual(result["verdict"], "alternative-identification-not-accepted")

    def test_proposing_a_weaker_arrangement_than_available_is_a_finding(self):
        result = run(proposed_arrangement="individual-sealed-container-marking")
        self.assertEqual(result["selected_arrangement"], "permanent-attached-tag")
        self.assertIn(
            "weaker-arrangement-than-available", [f["finding"] for f in result["findings"]]
        )

    def test_an_arrangement_the_case_does_not_admit_is_denied(self):
        result = run(
            free_body_area_mm2=LARGE_BODY_MM2,
            body_finish=BAD_FINISH,
            available_arrangements=ALL_ARRANGEMENTS,
            proposed_arrangement="intermediate-package-marking",
        )
        self.assertEqual(result["verdict"], "alternative-identification-not-accepted")

    def test_a_case_with_no_admissible_arrangement_is_denied(self):
        result = run(available_arrangements=["carrier-position-register-only"])
        self.assertIsNone(result["selected_arrangement"])
        self.assertEqual(result["verdict"], "alternative-identification-not-accepted")

    def test_an_unknown_compensating_control_is_rejected(self):
        with self.assertRaises(ValueError):
            run(controls={"promise-from-the-shop-floor": "implemented-and-evidenced"})

    def test_a_blank_unit_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(unit_id="   ")

    def test_a_non_mapping_control_argument_is_rejected(self):
        with self.assertRaises(ValueError):
            run(controls=["serial-register-held-by-manufacturer"])


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(MARKING_TOLERANCE, 1e-6)

    def test_the_control_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(CONTROL_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(CONTROL_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_full_control_set(self):
        self.assertLess(ACCEPTANCE_INDEX, 1.0)


if __name__ == "__main__":
    unittest.main()
