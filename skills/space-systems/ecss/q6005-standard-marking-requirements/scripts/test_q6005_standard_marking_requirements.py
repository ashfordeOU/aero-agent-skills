#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 10.2.1 body-marking leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_standard_marking_requirements.py
"""

import unittest

from q6005_standard_marking_requirements_logic import (
    ACCEPTANCE_INDEX,
    AMBIGUOUS_SERIAL_CHARACTERS,
    FIELD_STATE_CREDIT,
    FIELD_WEIGHTS,
    INDICATOR_FORMS,
    KNOWN_SOLVENTS,
    LARGE_BODY_AREA_MM2,
    LARGE_BODY_CHARACTER_HEIGHT_MM,
    MANDATORY_BODY_FIELDS,
    MARKING_TOLERANCE,
    MAXIMUM_ISO_WEEK,
    MEDIUM_BODY_AREA_MM2,
    MEDIUM_BODY_CHARACTER_HEIGHT_MM,
    MINIMUM_CONTRAST_RATIO,
    REQUIRED_DISTINCT_SOLVENTS,
    REQUIRED_IMMERSION_MINUTES,
    SMALL_BODY_CHARACTER_HEIGHT_MM,
    UNAIDED_READING_HEIGHT_MM,
    VERDICTS,
    applicable_field_set,
    assess_body_marking,
    assess_character_height,
    assess_durability,
    assess_field,
    contrast_is_sufficient,
    contrast_ratio,
    field_format_findings,
    field_state_credit,
    field_weight,
    marking_completeness_index,
    minimum_character_height_mm,
    normalize_exposure,
    optional_body_fields,
    validate_date_code,
    validate_indicator,
    validate_manufacturer_identification,
    validate_part_number,
    validate_serial_number,
)

SPARE_OPTIONAL = "country-of-origin"


def body_fields(**overrides):
    """A complete and well formed body mark."""
    record = {
        "manufacturer-identification": "AH7",
        "part-or-type-number": "HYB-1234-01",
        "lot-date-code": "2614",
        "serial-number": "SN0042",
        "pin-one-or-polarity-indicator": "printed-dot",
    }
    record.update(overrides)
    return record


def solvent_exposures(**overrides):
    """One immersion in each required solution, all left fully legible."""
    exposures = []
    for solvent in KNOWN_SOLVENTS:
        entry = {
            "solvent": solvent,
            "immersion_minutes": REQUIRED_IMMERSION_MINUTES,
            "post_test_legibility": "fully-legible",
        }
        if solvent in overrides:
            entry.update(overrides[solvent])
        exposures.append(entry)
    return exposures


def run(**overrides):
    """Grade one delivered unit's body mark."""
    case = {
        "unit_id": "HYB-1234-SN0042",
        "fields": body_fields(),
        "character_height_mm": 0.8,
        "body_area_mm2": 120.0,
        "mark_reflectance": 0.15,
        "body_reflectance": 0.60,
        "solvent_exposures": solvent_exposures(),
        "applicable_optional": (),
    }
    case.update(overrides)
    return assess_body_marking(**case)


class FieldSetTests(unittest.TestCase):
    def test_every_mandatory_field_carries_a_published_weight(self):
        for name in MANDATORY_BODY_FIELDS:
            self.assertIn(name, FIELD_WEIGHTS)

    def test_the_optional_fields_are_the_ones_left_over(self):
        self.assertEqual(
            set(optional_body_fields()) & set(MANDATORY_BODY_FIELDS), set()
        )

    def test_a_delivery_calling_for_nothing_extra_is_graded_on_the_mandatory_set(self):
        self.assertEqual(set(applicable_field_set()), set(MANDATORY_BODY_FIELDS))

    def test_a_called_for_optional_field_joins_the_graded_set(self):
        self.assertIn(SPARE_OPTIONAL, applicable_field_set([SPARE_OPTIONAL]))

    def test_naming_a_mandatory_field_as_optional_is_rejected(self):
        with self.assertRaises(ValueError):
            applicable_field_set(["serial-number"])

    def test_an_unknown_field_name_is_rejected(self):
        with self.assertRaises(ValueError):
            field_weight("batch-colour")

    def test_an_unknown_field_state_is_rejected(self):
        with self.assertRaises(ValueError):
            field_state_credit("roughly-there")


class FieldFormatTests(unittest.TestCase):
    def test_a_well_formed_manufacturer_code_raises_nothing(self):
        self.assertEqual(validate_manufacturer_identification("AH7"), [])

    def test_a_long_manufacturer_code_is_reported(self):
        self.assertIn(
            "manufacturer-code-length-outside-the-allowed-range",
            validate_manufacturer_identification("ASHFORDE"),
        )

    def test_a_lowercase_manufacturer_code_is_reported(self):
        self.assertIn(
            "manufacturer-code-uses-characters-outside-the-set",
            validate_manufacturer_identification("ah7"),
        )

    def test_a_well_formed_part_number_raises_nothing(self):
        self.assertEqual(validate_part_number("HYB-1234-01"), [])

    def test_a_part_number_with_a_space_is_reported(self):
        self.assertIn(
            "part-number-uses-characters-outside-the-set", validate_part_number("HYB 1234")
        )

    def test_a_well_formed_date_code_raises_nothing(self):
        self.assertEqual(validate_date_code("2614"), [])

    def test_a_three_figure_date_code_is_reported(self):
        self.assertIn("date-code-is-not-four-figures", validate_date_code("261"))

    def test_a_date_code_with_letters_is_reported(self):
        self.assertIn("date-code-is-not-all-figures", validate_date_code("26AB"))

    def test_a_week_past_the_calendar_is_reported(self):
        self.assertIn("date-code-week-outside-the-calendar", validate_date_code("2699"))

    def test_the_last_week_of_the_calendar_is_accepted(self):
        self.assertEqual(validate_date_code("26%02d" % (MAXIMUM_ISO_WEEK,)), [])

    def test_a_zero_week_is_reported(self):
        self.assertIn("date-code-week-outside-the-calendar", validate_date_code("2600"))

    def test_a_well_formed_serial_raises_nothing(self):
        self.assertEqual(validate_serial_number("SN0042"), [])

    def test_a_serial_using_look_alike_characters_is_reported(self):
        character = sorted(AMBIGUOUS_SERIAL_CHARACTERS)[0]
        self.assertIn(
            "serial-number-uses-characters-that-read-alike",
            validate_serial_number("SN00" + character),
        )

    def test_a_serial_longer_than_the_field_allows_is_reported(self):
        self.assertIn(
            "serial-number-length-outside-the-allowed-range",
            validate_serial_number("SN0000000042"),
        )

    def test_every_published_indicator_form_is_accepted(self):
        for form in INDICATOR_FORMS:
            self.assertEqual(validate_indicator(form), [], form)

    def test_an_indicator_nobody_publishes_is_reported(self):
        self.assertIn(
            "indicator-form-not-one-of-the-accepted-forms", validate_indicator("a-smiley")
        )

    def test_a_blank_field_value_is_rejected(self):
        with self.assertRaises(ValueError):
            field_format_findings("serial-number", "   ")

    def test_a_format_check_on_an_unknown_field_is_rejected(self):
        with self.assertRaises(ValueError):
            field_format_findings("batch-colour", "red")


class FieldGradingTests(unittest.TestCase):
    def test_a_valid_field_earns_its_full_weight(self):
        record = assess_field("serial-number", "SN0042")
        self.assertEqual(record["state"], "present-and-valid")
        self.assertAlmostEqual(
            record["weighted_credit"], FIELD_WEIGHTS["serial-number"], places=9
        )

    def test_an_absent_mandatory_field_is_marked_absent(self):
        record = assess_field("lot-date-code", None)
        self.assertTrue(record["mandatory_absent"])
        self.assertFalse(record["mandatory_malformed"])
        self.assertIn("field-absent-from-the-body-mark", record["findings"])

    def test_a_malformed_mandatory_field_is_a_different_failure_from_an_absent_one(self):
        record = assess_field("lot-date-code", "26AB")
        self.assertTrue(record["mandatory_malformed"])
        self.assertFalse(record["mandatory_absent"])

    def test_a_malformed_field_earns_partial_credit(self):
        record = assess_field("lot-date-code", "26AB")
        self.assertAlmostEqual(
            record["weighted_credit"],
            FIELD_WEIGHTS["lot-date-code"] * FIELD_STATE_CREDIT["present-with-format-finding"],
            places=9,
        )

    def test_an_absent_optional_field_is_not_a_mandatory_failure(self):
        record = assess_field(SPARE_OPTIONAL, None)
        self.assertFalse(record["mandatory_absent"])

    def test_a_complete_mark_reaches_a_full_index(self):
        records = [assess_field(name, body_fields()[name]) for name in MANDATORY_BODY_FIELDS]
        self.assertAlmostEqual(marking_completeness_index(records), 1.0, places=9)

    def test_an_empty_field_set_is_rejected(self):
        with self.assertRaises(ValueError):
            marking_completeness_index([])


class CharacterHeightTests(unittest.TestCase):
    def test_a_large_body_carries_the_tallest_minimum(self):
        self.assertAlmostEqual(
            minimum_character_height_mm(LARGE_BODY_AREA_MM2 + 50.0),
            LARGE_BODY_CHARACTER_HEIGHT_MM,
            places=9,
        )

    def test_the_large_body_threshold_is_met_exactly_at_its_area(self):
        self.assertAlmostEqual(
            minimum_character_height_mm(LARGE_BODY_AREA_MM2),
            LARGE_BODY_CHARACTER_HEIGHT_MM,
            places=9,
        )

    def test_a_medium_body_carries_the_middle_minimum(self):
        self.assertAlmostEqual(
            minimum_character_height_mm(MEDIUM_BODY_AREA_MM2 + 1.0),
            MEDIUM_BODY_CHARACTER_HEIGHT_MM,
            places=9,
        )

    def test_a_small_body_carries_the_floor_and_goes_no_lower(self):
        self.assertAlmostEqual(
            minimum_character_height_mm(4.0), SMALL_BODY_CHARACTER_HEIGHT_MM, places=9
        )

    def test_a_body_with_no_area_is_rejected(self):
        with self.assertRaises(ValueError):
            minimum_character_height_mm(0.0)

    def test_lettering_at_the_minimum_for_its_body_is_adequate(self):
        record = assess_character_height(LARGE_BODY_CHARACTER_HEIGHT_MM, 150.0)
        self.assertTrue(record["adequate"])
        self.assertEqual(record["findings"], [])

    def test_lettering_under_the_minimum_for_its_body_is_reported(self):
        record = assess_character_height(0.4, 150.0)
        self.assertFalse(record["adequate"])
        self.assertIn("character-height-below-the-minimum-for-this-body", record["findings"])

    def test_small_but_compliant_lettering_is_an_open_action_not_a_failure(self):
        record = assess_character_height(MEDIUM_BODY_CHARACTER_HEIGHT_MM, 30.0)
        self.assertTrue(record["adequate"])
        self.assertIn("marking-readable-only-under-magnification", record["findings"])

    def test_the_unaided_reading_height_is_not_below_the_large_body_minimum(self):
        self.assertAlmostEqual(
            UNAIDED_READING_HEIGHT_MM, LARGE_BODY_CHARACTER_HEIGHT_MM, places=9
        )

    def test_a_negative_character_height_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_character_height(-0.5, 150.0)


class ContrastTests(unittest.TestCase):
    def test_a_dark_mark_on_a_pale_body_stands_out(self):
        self.assertAlmostEqual(contrast_ratio(0.15, 0.60), 4.0, places=9)

    def test_the_ratio_does_not_depend_on_which_is_darker(self):
        self.assertAlmostEqual(contrast_ratio(0.60, 0.15), contrast_ratio(0.15, 0.60), places=9)

    def test_a_ratio_exactly_at_the_minimum_is_sufficient(self):
        self.assertAlmostEqual(contrast_ratio(0.30, 0.60), MINIMUM_CONTRAST_RATIO, places=9)
        self.assertTrue(contrast_is_sufficient(0.30, 0.60))

    def test_lettering_the_shade_of_the_package_is_not_sufficient(self):
        self.assertFalse(contrast_is_sufficient(0.55, 0.60))

    def test_a_reflectance_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            contrast_ratio(1.4, 0.6)

    def test_a_zero_reflectance_is_rejected(self):
        with self.assertRaises(ValueError):
            contrast_ratio(0.0, 0.6)


class DurabilityTests(unittest.TestCase):
    def test_a_full_solvent_set_demonstrates_durability(self):
        record = assess_durability(solvent_exposures())
        self.assertTrue(record["demonstrated"])
        self.assertTrue(record["complete"])
        self.assertEqual(record["findings"], [])

    def test_an_immersion_exactly_at_the_required_dwell_counts(self):
        record = assess_durability(solvent_exposures())
        self.assertEqual(record["short_immersions"], 0)
        self.assertEqual(len(record["solvents"]), REQUIRED_DISTINCT_SOLVENTS)

    def test_a_missing_solution_leaves_the_test_incomplete(self):
        record = assess_durability(solvent_exposures()[:2])
        self.assertFalse(record["complete"])
        self.assertIn("durability-evidence-misses-a-required-solvent", record["findings"])

    def test_a_short_immersion_leaves_the_test_incomplete(self):
        exposures = solvent_exposures(**{KNOWN_SOLVENTS[0]: {"immersion_minutes": 0.2}})
        record = assess_durability(exposures)
        self.assertFalse(record["complete"])
        self.assertIn("immersion-shorter-than-the-required-dwell", record["findings"])

    def test_lettering_lost_after_an_exposure_is_a_marking_failure_not_a_short_test(self):
        exposures = solvent_exposures(**{KNOWN_SOLVENTS[1]: {"post_test_legibility": "removed"}})
        record = assess_durability(exposures)
        self.assertTrue(record["complete"])
        self.assertFalse(record["demonstrated"])
        self.assertIn("lettering-not-fully-legible-after-exposure", record["findings"])

    def test_a_smeared_mark_is_not_fully_legible(self):
        exposures = solvent_exposures(**{KNOWN_SOLVENTS[2]: {"post_test_legibility": "smeared"}})
        self.assertEqual(assess_durability(exposures)["exposures_losing_legibility"], 1)

    def test_an_unknown_solvent_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_exposure(
                {
                    "solvent": "tap-water",
                    "immersion_minutes": 1.0,
                    "post_test_legibility": "fully-legible",
                }
            )

    def test_an_unknown_post_test_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_exposure(
                {
                    "solvent": KNOWN_SOLVENTS[0],
                    "immersion_minutes": 1.0,
                    "post_test_legibility": "looked-fine",
                }
            )

    def test_a_negative_immersion_time_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_exposure(
                {
                    "solvent": KNOWN_SOLVENTS[0],
                    "immersion_minutes": -1.0,
                    "post_test_legibility": "fully-legible",
                }
            )

    def test_an_exposure_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_durability(["polar-solvent"])


class WholeMarkTests(unittest.TestCase):
    def test_a_complete_durable_mark_passes_with_no_findings(self):
        result = run()
        self.assertEqual(result["verdict"], "body-marking-meets-standard-requirements")
        self.assertTrue(result["marking_accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["marking_completeness_index"], 1.0, places=9)

    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_mark_with_no_serial_number_is_incomplete(self):
        fields = body_fields()
        del fields["serial-number"]
        result = run(fields=fields)
        self.assertEqual(result["verdict"], "body-marking-assessment-incomplete")

    def test_a_malformed_date_code_fails_rather_than_leaving_the_mark_incomplete(self):
        result = run(fields=body_fields(**{"lot-date-code": "26AB"}))
        self.assertEqual(result["verdict"], "body-marking-does-not-meet-requirements")
        self.assertFalse(result["marking_accepted"])

    def test_lettering_under_the_height_floor_fails(self):
        result = run(character_height_mm=0.4)
        self.assertEqual(result["verdict"], "body-marking-does-not-meet-requirements")

    def test_lettering_without_contrast_fails(self):
        result = run(mark_reflectance=0.55)
        self.assertEqual(result["verdict"], "body-marking-does-not-meet-requirements")
        self.assertFalse(result["contrast_sufficient"])

    def test_a_mark_removed_by_a_solvent_fails(self):
        exposures = solvent_exposures(**{KNOWN_SOLVENTS[0]: {"post_test_legibility": "removed"}})
        result = run(solvent_exposures=exposures)
        self.assertEqual(result["verdict"], "body-marking-does-not-meet-requirements")

    def test_a_short_solvent_test_leaves_the_assessment_incomplete(self):
        result = run(solvent_exposures=solvent_exposures()[:1])
        self.assertEqual(result["verdict"], "body-marking-assessment-incomplete")

    def test_small_lettering_within_its_minimum_leaves_open_actions(self):
        result = run(character_height_mm=0.5, body_area_mm2=30.0)
        self.assertEqual(result["verdict"], "body-marking-meets-requirements-with-open-actions")
        self.assertTrue(result["marking_accepted"])

    def test_an_optional_field_nobody_called_for_is_not_graded(self):
        result = run()
        self.assertNotIn(SPARE_OPTIONAL, result["graded_fields"])
        self.assertEqual(len(result["field_records"]), len(MANDATORY_BODY_FIELDS))

    def test_an_optional_field_the_delivery_calls_for_is_graded_when_absent(self):
        result = run(applicable_optional=[SPARE_OPTIONAL])
        self.assertIn(SPARE_OPTIONAL, result["graded_fields"])
        self.assertIn(
            "field-absent-from-the-body-mark", [f["finding"] for f in result["findings"]]
        )
        self.assertEqual(result["verdict"], "body-marking-meets-requirements-with-open-actions")

    def test_a_mark_missing_every_called_for_field_sinks_below_the_index(self):
        result = run(applicable_optional=list(optional_body_fields()))
        self.assertLess(result["marking_completeness_index"], ACCEPTANCE_INDEX)
        self.assertEqual(result["verdict"], "body-marking-does-not-meet-requirements")

    def test_an_optional_field_supplied_uncalled_for_is_still_checked(self):
        result = run(fields=body_fields(**{SPARE_OPTIONAL: "DEU"}))
        self.assertIn(SPARE_OPTIONAL, result["graded_fields"])
        self.assertIn(
            "country-code-is-not-two-letters", [f["finding"] for f in result["findings"]]
        )

    def test_a_field_the_body_mark_has_no_place_for_is_rejected(self):
        with self.assertRaises(ValueError):
            run(fields=body_fields(**{"batch-colour": "red"}))

    def test_a_blank_unit_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(unit_id="   ")

    def test_a_field_map_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            run(fields=["SN0042"])


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(MARKING_TOLERANCE, 1e-6)

    def test_the_field_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(FIELD_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(FIELD_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_complete_mark(self):
        self.assertLess(ACCEPTANCE_INDEX, 1.0)

    def test_the_height_steps_fall_with_the_body_area(self):
        self.assertGreater(LARGE_BODY_CHARACTER_HEIGHT_MM, MEDIUM_BODY_CHARACTER_HEIGHT_MM)
        self.assertGreater(MEDIUM_BODY_CHARACTER_HEIGHT_MM, SMALL_BODY_CHARACTER_HEIGHT_MM)

    def test_the_body_area_steps_are_ordered(self):
        self.assertGreater(LARGE_BODY_AREA_MM2, MEDIUM_BODY_AREA_MM2)

    def test_the_durability_evidence_spans_every_published_solution(self):
        self.assertEqual(len(KNOWN_SOLVENTS), REQUIRED_DISTINCT_SOLVENTS)


if __name__ == "__main__":
    unittest.main()
