"""Contract tests for the Annex H device data sheet data-item logic."""

import unittest

from e2040_device_data_sheet_data_item_logic import (
    DERATING_TOLERANCE,
    REQUIRED_SECTIONS,
    assess_data_sheet,
    characteristic_findings,
    derating_margin,
    envelope_containment,
    grade_rating,
    missing_sections,
    validate_characteristic,
    validate_characteristics,
    validate_rating,
    validate_ratings,
    worst_margin_parameter,
)

ALL_SECTIONS = list(REQUIRED_SECTIONS)


def characteristic(identifier="ICC", unit="mA", minimum=8.0, typical=10.0, maximum=12.0,
                   conditions="Vcc = 3.3 V, Tj = 25 C"):
    return {
        "id": identifier,
        "unit": unit,
        "minimum": minimum,
        "typical": typical,
        "maximum": maximum,
        "test_conditions": conditions,
    }


def rating(identifier="VCC", absolute_max=100.0, recommended_max=80.0,
           absolute_min=None, recommended_min=None):
    entry = {
        "id": identifier,
        "absolute_maximum": absolute_max,
        "recommended_maximum": recommended_max,
    }
    if absolute_min is not None:
        entry["absolute_minimum"] = absolute_min
    if recommended_min is not None:
        entry["recommended_minimum"] = recommended_min
    return entry


class SectionTests(unittest.TestCase):
    def test_complete_section_list_has_no_gap(self):
        self.assertEqual(missing_sections(ALL_SECTIONS), [])

    def test_absent_absolute_ratings_section_is_named(self):
        partial = [s for s in ALL_SECTIONS if s != "absolute-maximum-ratings"]
        self.assertEqual(missing_sections(partial), ["absolute-maximum-ratings"])

    def test_section_match_ignores_case(self):
        self.assertEqual(missing_sections([s.upper() for s in ALL_SECTIONS]), [])

    def test_non_sequence_section_list_rejected(self):
        with self.assertRaises(ValueError):
            missing_sections(3.0)


class CharacteristicTests(unittest.TestCase):
    def test_ordered_triple_accepted(self):
        record = validate_characteristic(characteristic())
        self.assertAlmostEqual(record["typical"], 10.0)

    def test_absent_edges_are_allowed(self):
        record = validate_characteristic(characteristic(minimum=None, maximum=None))
        self.assertIsNone(record["minimum"])
        self.assertIsNone(record["maximum"])

    def test_inverted_edges_rejected(self):
        with self.assertRaises(ValueError):
            validate_characteristic(characteristic(minimum=12.0, typical=10.0, maximum=8.0))

    def test_typical_below_the_minimum_rejected(self):
        with self.assertRaises(ValueError):
            validate_characteristic(characteristic(minimum=9.0, typical=8.0))

    def test_typical_above_the_maximum_rejected(self):
        with self.assertRaises(ValueError):
            validate_characteristic(characteristic(typical=13.0))

    def test_non_finite_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_characteristic(characteristic(maximum=float("nan")))

    def test_empty_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_characteristic(characteristic(unit="  "))

    def test_duplicate_characteristic_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_characteristics([characteristic(), characteristic()])

    def test_placeholder_unit_is_a_content_finding(self):
        records = validate_characteristics([characteristic(unit="TBD")])
        self.assertTrue(any("placeholder unit" in f for f in characteristic_findings(records)))

    def test_absent_test_conditions_is_a_content_finding(self):
        records = validate_characteristics([characteristic(conditions=None)])
        self.assertTrue(any("no test conditions" in f for f in characteristic_findings(records)))

    def test_typical_alone_is_a_content_finding(self):
        records = validate_characteristics([characteristic(minimum=None, maximum=None)])
        self.assertTrue(
            any("no guaranteed edge" in f for f in characteristic_findings(records))
        )

    def test_entirely_empty_characteristic_is_a_content_finding(self):
        records = validate_characteristics(
            [characteristic(minimum=None, typical=None, maximum=None)]
        )
        self.assertTrue(any("no value at all" in f for f in characteristic_findings(records)))

    def test_clean_characteristic_has_no_content_finding(self):
        records = validate_characteristics([characteristic()])
        self.assertEqual(characteristic_findings(records), [])


class RatingTests(unittest.TestCase):
    def test_recommended_inside_absolute_is_contained(self):
        record = validate_rating(rating())
        self.assertEqual(envelope_containment(record), [])

    def test_recommended_on_the_absolute_maximum_is_not_contained(self):
        record = validate_rating(rating(recommended_max=100.0))
        self.assertEqual(len(envelope_containment(record)), 1)

    def test_recommended_beyond_the_absolute_maximum_is_not_contained(self):
        record = validate_rating(rating(recommended_max=120.0))
        self.assertTrue(envelope_containment(record))

    def test_two_sided_rating_checks_the_low_end(self):
        record = validate_rating(
            rating(absolute_min=-100.0, recommended_min=-100.0)
        )
        self.assertTrue(any("recommended minimum" in r for r in envelope_containment(record)))

    def test_two_sided_rating_inside_both_ends_is_contained(self):
        record = validate_rating(rating(absolute_min=-100.0, recommended_min=-80.0))
        self.assertEqual(envelope_containment(record), [])

    def test_non_positive_absolute_maximum_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(rating(absolute_max=0.0))

    def test_absolute_minimum_above_the_maximum_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(rating(absolute_min=150.0))

    def test_recommended_minimum_without_an_absolute_minimum_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(rating(recommended_min=10.0))

    def test_inverted_recommended_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(rating(absolute_min=-100.0, recommended_min=90.0,
                                   recommended_max=20.0))

    def test_duplicate_rating_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_ratings([rating(), rating()])


class DeratingTests(unittest.TestCase):
    def test_margin_is_the_unused_fraction(self):
        self.assertAlmostEqual(derating_margin(80.0, 100.0), 0.2, places=9)

    def test_full_use_leaves_no_margin(self):
        self.assertAlmostEqual(derating_margin(100.0, 100.0), 0.0, places=9)

    def test_zero_absolute_rating_rejected(self):
        with self.assertRaises(ValueError):
            derating_margin(80.0, 0.0)

    def test_margin_exactly_at_the_requirement_is_met(self):
        record = grade_rating(rating(recommended_max=80.0), 0.2)
        self.assertTrue(record["margin_met"])
        self.assertLessEqual(
            abs(record["derating_margin"] - record["required_margin"]), DERATING_TOLERANCE
        )

    def test_margin_below_the_requirement_is_not_met(self):
        record = grade_rating(rating(recommended_max=95.0), 0.2)
        self.assertFalse(record["margin_met"])
        self.assertAlmostEqual(record["derating_margin"], 0.05, places=9)

    def test_generous_margin_is_met(self):
        record = grade_rating(rating(recommended_max=50.0), 0.2)
        self.assertTrue(record["margin_met"])

    def test_required_margin_at_one_rejected(self):
        with self.assertRaises(ValueError):
            grade_rating(rating(), 1.0)

    def test_worst_margin_parameter_is_the_tightest(self):
        graded = [
            grade_rating(rating("VCC", 100.0, 50.0), 0.2),
            grade_rating(rating("IOUT", 100.0, 90.0), 0.2),
        ]
        self.assertEqual(worst_margin_parameter(graded)["id"], "IOUT")

    def test_worst_margin_tie_is_broken_by_identifier(self):
        graded = [
            grade_rating(rating("VCC", 100.0, 80.0), 0.2),
            grade_rating(rating("IOUT", 50.0, 40.0), 0.2),
        ]
        self.assertEqual(worst_margin_parameter(graded)["id"], "IOUT")

    def test_empty_graded_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_margin_parameter([])


class AssessmentTests(unittest.TestCase):
    def _sheet(self, **overrides):
        sheet = {
            "sections": list(ALL_SECTIONS),
            "characteristics": [characteristic()],
            "ratings": [rating("VCC", 100.0, 75.0), rating("IOUT", 200.0, 120.0)],
            "required_derating_margin": 0.2,
        }
        sheet.update(overrides)
        return sheet

    def test_clean_sheet_is_compliant(self):
        result = assess_data_sheet(self._sheet())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_worst_margin_parameter_is_reported(self):
        result = assess_data_sheet(self._sheet())
        self.assertEqual(result["worst_margin_parameter"], "VCC")
        self.assertAlmostEqual(result["worst_derating_margin"], 0.25, places=9)

    def test_rating_on_the_absolute_maximum_is_a_finding(self):
        result = assess_data_sheet(
            self._sheet(ratings=[rating("VCC", 100.0, 100.0)])
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("at or beyond the absolute maximum" in f for f in result["findings"]))

    def test_thin_derating_is_a_finding(self):
        result = assess_data_sheet(self._sheet(ratings=[rating("VCC", 100.0, 95.0)]))
        self.assertTrue(any("below the required" in f for f in result["findings"]))

    def test_exact_derating_requirement_is_compliant(self):
        result = assess_data_sheet(self._sheet(ratings=[rating("VCC", 100.0, 80.0)]))
        self.assertTrue(result["compliant"])

    def test_characteristic_defect_is_a_finding(self):
        result = assess_data_sheet(
            self._sheet(characteristics=[characteristic(conditions=None)])
        )
        self.assertFalse(result["compliant"])

    def test_absent_section_is_a_finding(self):
        sections = [s for s in ALL_SECTIONS if s != "test-conditions"]
        result = assess_data_sheet(self._sheet(sections=sections))
        self.assertEqual(result["missing_sections"], ["test-conditions"])

    def test_required_margin_outside_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_sheet(self._sheet(required_derating_margin=-0.1))

    def test_missing_sheet_key_rejected(self):
        sheet = self._sheet()
        del sheet["ratings"]
        with self.assertRaises(ValueError):
            assess_data_sheet(sheet)

    def test_non_mapping_sheet_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_sheet(["sections"])


if __name__ == "__main__":
    unittest.main()
