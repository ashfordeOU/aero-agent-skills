"""Contract tests for the clause 7.5.1.5.2 welding area void diameter limit."""

import math
import unittest

from e2008_bare_cell_welding_area_limits_logic import (
    ACCEPT,
    AREA_EQUIVALENT,
    BUBBLE,
    DEFAULT_WELDING_AREA_CRITERIA,
    LIMIT_NOT_ESTABLISHED,
    MAJOR_AXIS,
    OUTSIDE_WELDING_AREA,
    REFER_FOR_REVIEW,
    REJECT,
    STATED_DIAMETER,
    VOID,
    assess_bare_cell_welding_area_limits,
    assess_welding_area,
    categorize_void,
    circle_area_mm2,
    ellipse_area_mm2,
    equivalent_diameter_mm,
    governing_void_diameter_mm,
    validate_void,
    validate_welding_area,
    validate_welding_area_criteria,
    void_area_fraction,
    void_area_mm2,
    void_inside_welding_area,
    voids_in_welding_area,
    welding_area_mm2,
    within_diameter_limit,
    worst_disposition,
)

LIMIT = 0.5


def _criteria(**overrides):
    criteria = dict(DEFAULT_WELDING_AREA_CRITERIA)
    criteria.update(overrides)
    return criteria


def _area(**overrides):
    area = {
        "id": "weld-zone-1",
        "x_mm": 0.0,
        "y_mm": 0.0,
        "width_mm": 2.0,
        "length_mm": 4.0,
        "max_permitted_void_diameter_mm": LIMIT,
        "drawing_reference": "CAD-8802 issue B",
    }
    area.update(overrides)
    return area


def _void(**overrides):
    void = {"kind": VOID, "x_mm": 1.0, "y_mm": 1.0, "diameter_mm": 0.2}
    void.update(overrides)
    return void


def _ratio(value, expected):
    return value / expected


class CriteriaTests(unittest.TestCase):
    def test_the_default_criteria_validate(self):
        self.assertIs(
            validate_welding_area_criteria(DEFAULT_WELDING_AREA_CRITERIA),
            DEFAULT_WELDING_AREA_CRITERIA,
        )

    def test_a_non_mapping_criteria_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_welding_area_criteria("half a millimetre")

    def test_a_negative_measurement_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            validate_welding_area_criteria(_criteria(measurement_uncertainty_mm=-0.01))

    def test_a_void_area_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_welding_area_criteria(_criteria(max_void_area_fraction=1.4))


class DiameterAlgebraTests(unittest.TestCase):
    def test_the_equivalent_diameter_inverts_the_circle_area(self):
        self.assertAlmostEqual(
            _ratio(equivalent_diameter_mm(circle_area_mm2(0.4)), 0.4), 1.0, places=12
        )

    def test_a_round_void_has_the_expected_area(self):
        self.assertAlmostEqual(
            _ratio(circle_area_mm2(2.0), math.pi), 1.0, places=12
        )

    def test_an_elongated_void_area_uses_both_axes(self):
        self.assertAlmostEqual(
            _ratio(ellipse_area_mm2(0.8, 0.2), math.pi * 0.8 * 0.2 / 4.0),
            1.0,
            places=12,
        )

    def test_axes_the_wrong_way_round_rejected(self):
        with self.assertRaises(ValueError):
            ellipse_area_mm2(0.2, 0.8)

    def test_a_zero_area_rejected_by_the_equivalent_diameter(self):
        with self.assertRaises(ValueError):
            equivalent_diameter_mm(0.0)


class VoidValidationTests(unittest.TestCase):
    def test_an_unknown_void_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_void(_void(kind="pit"))

    def test_a_void_describing_nothing_rejected(self):
        with self.assertRaises(ValueError):
            validate_void({"kind": VOID, "x_mm": 1.0, "y_mm": 1.0})

    def test_a_major_axis_without_its_minor_rejected(self):
        with self.assertRaises(ValueError):
            validate_void(
                {"kind": VOID, "x_mm": 1.0, "y_mm": 1.0, "major_axis_mm": 0.4}
            )

    def test_a_minor_axis_larger_than_the_major_rejected(self):
        with self.assertRaises(ValueError):
            validate_void(
                {
                    "kind": VOID,
                    "x_mm": 1.0,
                    "y_mm": 1.0,
                    "major_axis_mm": 0.2,
                    "minor_axis_mm": 0.4,
                }
            )

    def test_a_negative_diameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_void(_void(diameter_mm=-0.2))


class GoverningDiameterTests(unittest.TestCase):
    def test_a_stated_diameter_governs_itself(self):
        diameter, source = governing_void_diameter_mm(_void())
        self.assertAlmostEqual(_ratio(diameter, 0.2), 1.0, places=12)
        self.assertEqual(source, STATED_DIAMETER)

    def test_the_major_axis_governs_an_elongated_void(self):
        diameter, source = governing_void_diameter_mm(
            {
                "kind": VOID,
                "x_mm": 1.0,
                "y_mm": 1.0,
                "major_axis_mm": 0.8,
                "minor_axis_mm": 0.1,
            }
        )
        self.assertAlmostEqual(_ratio(diameter, 0.8), 1.0, places=12)
        self.assertEqual(source, MAJOR_AXIS)

    def test_the_major_axis_beats_the_area_equivalent_figure(self):
        elongated = {
            "kind": VOID,
            "x_mm": 1.0,
            "y_mm": 1.0,
            "major_axis_mm": 0.8,
            "minor_axis_mm": 0.1,
        }
        major, _source = governing_void_diameter_mm(elongated)
        area_equivalent = equivalent_diameter_mm(void_area_mm2(elongated))
        self.assertGreater(major, area_equivalent * 2.0)

    def test_an_area_only_record_falls_back_to_the_equivalent_diameter(self):
        diameter, source = governing_void_diameter_mm(
            {"kind": BUBBLE, "x_mm": 1.0, "y_mm": 1.0, "area_mm2": 0.04}
        )
        self.assertEqual(source, AREA_EQUIVALENT)
        self.assertAlmostEqual(
            _ratio(diameter, equivalent_diameter_mm(0.04)), 1.0, places=12
        )

    def test_a_void_area_follows_the_description_it_carries(self):
        self.assertAlmostEqual(
            _ratio(void_area_mm2(_void()), circle_area_mm2(0.2)), 1.0, places=12
        )


class WeldingAreaTests(unittest.TestCase):
    def test_the_welding_area_footprint_is_width_times_length(self):
        self.assertAlmostEqual(_ratio(welding_area_mm2(_area()), 8.0), 1.0, places=12)

    def test_a_blank_welding_area_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_welding_area(_area(id="   "))

    def test_a_limit_larger_than_the_zone_rejected(self):
        with self.assertRaises(ValueError):
            validate_welding_area(_area(max_permitted_void_diameter_mm=9.0))

    def test_a_limit_with_no_drawing_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_welding_area(_area(drawing_reference=None))

    def test_an_area_with_neither_a_limit_nor_a_reference_is_unestablished(self):
        normalised = validate_welding_area(
            _area(max_permitted_void_diameter_mm=None, drawing_reference=None)
        )
        self.assertIsNone(normalised["max_permitted_void_diameter_mm"])


class ContainmentTests(unittest.TestCase):
    def test_a_void_in_the_middle_is_inside(self):
        self.assertTrue(void_inside_welding_area(_void(), _area()))

    def test_a_void_well_clear_is_outside(self):
        self.assertFalse(void_inside_welding_area(_void(x_mm=20.0), _area()))

    def test_a_void_straddling_the_edge_still_reaches_the_zone(self):
        self.assertTrue(void_inside_welding_area(_void(x_mm=2.05), _area()))

    def test_only_the_reaching_voids_are_collected(self):
        voids = [_void(), _void(x_mm=20.0), _void(y_mm=2.0)]
        self.assertEqual(len(voids_in_welding_area(voids, _area())), 2)

    def test_a_non_sequence_void_record_rejected(self):
        with self.assertRaises(ValueError):
            voids_in_welding_area("one bubble", _area())


class LimitComparisonTests(unittest.TestCase):
    def test_a_void_under_the_limit_is_within_it(self):
        self.assertTrue(within_diameter_limit(0.2, LIMIT))

    def test_a_void_over_the_limit_is_not(self):
        self.assertFalse(within_diameter_limit(0.9, LIMIT))

    def test_a_void_exactly_on_the_limit_is_within_it(self):
        derived = equivalent_diameter_mm(circle_area_mm2(LIMIT))
        self.assertAlmostEqual(_ratio(derived, LIMIT), 1.0, places=9)
        self.assertTrue(within_diameter_limit(derived, LIMIT))

    def test_a_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            within_diameter_limit(0.2, 0.0)


class VoidDispositionTests(unittest.TestCase):
    def test_a_small_void_inside_the_zone_is_accepted(self):
        disposition, _reason = categorize_void(_void(), _area(), _criteria())
        self.assertEqual(disposition, ACCEPT)

    def test_an_oversize_void_is_rejected_against_the_drawing_limit(self):
        disposition, reason = categorize_void(
            _void(diameter_mm=0.9), _area(), _criteria()
        )
        self.assertEqual(disposition, REJECT)
        self.assertIn("CAD-8802", reason)

    def test_an_elongated_void_is_judged_on_its_long_chord(self):
        elongated = {
            "kind": VOID,
            "x_mm": 1.0,
            "y_mm": 1.0,
            "major_axis_mm": 0.9,
            "minor_axis_mm": 0.05,
        }
        disposition, reason = categorize_void(elongated, _area(), _criteria())
        self.assertEqual(disposition, REJECT)
        self.assertIn(MAJOR_AXIS, reason)

    def test_a_void_inside_the_limit_by_less_than_the_uncertainty_goes_to_review(self):
        disposition, reason = categorize_void(
            _void(diameter_mm=LIMIT - 0.005), _area(), _criteria()
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("better look", reason)

    def test_an_area_only_void_goes_to_review_even_when_it_measures_small(self):
        disposition, reason = categorize_void(
            {"kind": BUBBLE, "x_mm": 1.0, "y_mm": 1.0, "area_mm2": 0.002},
            _area(),
            _criteria(),
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("round void", reason)

    def test_a_void_clear_of_the_zone_is_not_this_clause(self):
        disposition, reason = categorize_void(
            _void(x_mm=20.0, diameter_mm=0.9), _area(), _criteria()
        )
        self.assertEqual(disposition, OUTSIDE_WELDING_AREA)
        self.assertIn("another clause", reason)

    def test_a_void_cannot_be_dispositioned_without_a_drawing_limit(self):
        with self.assertRaises(ValueError):
            categorize_void(
                _void(),
                _area(max_permitted_void_diameter_mm=None, drawing_reference=None),
                _criteria(),
            )

    def test_a_zero_uncertainty_lets_a_near_limit_void_pass(self):
        disposition, _reason = categorize_void(
            _void(diameter_mm=LIMIT - 0.005),
            _area(),
            _criteria(measurement_uncertainty_mm=0.0),
        )
        self.assertEqual(disposition, ACCEPT)


class WorstDispositionTests(unittest.TestCase):
    def test_an_empty_set_accepts(self):
        self.assertEqual(worst_disposition([]), ACCEPT)

    def test_severity_beats_record_order(self):
        self.assertEqual(
            worst_disposition([REJECT, ACCEPT, REFER_FOR_REVIEW]), REJECT
        )

    def test_an_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition([ACCEPT, "small enough"])


class WeldingAreaAssessmentTests(unittest.TestCase):
    def test_a_sound_welding_area_is_accepted(self):
        result = assess_welding_area(_area(), [_void()], _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["voids_in_area"], 1)

    def test_the_largest_void_diameter_is_reported(self):
        voids = [_void(), _void(y_mm=2.0, diameter_mm=0.35)]
        result = assess_welding_area(_area(), voids, _criteria())
        self.assertAlmostEqual(
            _ratio(result["largest_void_diameter_mm"], 0.35), 1.0, places=12
        )

    def test_one_oversize_void_rejects_the_welding_area(self):
        result = assess_welding_area(
            _area(), [_void(), _void(y_mm=2.0, diameter_mm=0.9)], _criteria()
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_an_area_with_no_drawing_limit_is_unestablished(self):
        result = assess_welding_area(
            _area(max_permitted_void_diameter_mm=None, drawing_reference=None),
            [_void()],
            _criteria(),
        )
        self.assertEqual(result["verdict"], LIMIT_NOT_ESTABLISHED)
        self.assertIsNone(result["void_area_fraction"])

    def test_a_void_outside_the_zone_is_advised_not_counted(self):
        result = assess_welding_area(_area(), [_void(x_mm=20.0)], _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["voids_in_area"], 0)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_crowded_but_individually_sound_zone_goes_to_review(self):
        voids = [
            _void(x_mm=0.3 + 0.3 * index, y_mm=1.0, diameter_mm=0.3)
            for index in range(4)
        ]
        result = assess_welding_area(
            _area(), voids, _criteria(max_void_area_fraction=0.02)
        )
        self.assertEqual(result["verdict"], REFER_FOR_REVIEW)

    def test_too_many_voids_go_to_review(self):
        voids = [
            _void(x_mm=1.0, y_mm=0.3 + 0.4 * index, diameter_mm=0.1)
            for index in range(7)
        ]
        result = assess_welding_area(_area(), voids, _criteria())
        self.assertEqual(result["verdict"], REFER_FOR_REVIEW)
        self.assertEqual(result["voids_in_area"], 7)

    def test_the_void_area_fraction_is_reported(self):
        result = assess_welding_area(_area(), [_void()], _criteria())
        self.assertAlmostEqual(
            _ratio(result["void_area_fraction"], circle_area_mm2(0.2) / 8.0),
            1.0,
            places=9,
        )

    def test_the_standalone_fraction_matches_the_assessment(self):
        self.assertAlmostEqual(
            _ratio(
                void_area_fraction([_void()], _area()),
                circle_area_mm2(0.2) / 8.0,
            ),
            1.0,
            places=9,
        )

    def test_a_non_sequence_void_record_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_welding_area(_area(), "one void", _criteria())


class CellRollupTests(unittest.TestCase):
    def test_a_cell_with_sound_weld_zones_is_accepted(self):
        case = {
            "id": "cell-01",
            "welding_areas": [_area(), _area(id="weld-zone-2", x_mm=6.0)],
            "voids": [_void()],
        }
        result = assess_bare_cell_welding_area_limits(case, _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["welding_areas_assessed"], 2)

    def test_one_bad_zone_governs_the_cell(self):
        case = {
            "id": "cell-02",
            "welding_areas": [_area(), _area(id="weld-zone-2", x_mm=6.0)],
            "voids": [_void(x_mm=7.0, diameter_mm=0.9)],
        }
        result = assess_bare_cell_welding_area_limits(case, _criteria())
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["welding_areas_not_accepted"], ("weld-zone-2",))

    def test_a_zone_without_a_limit_closes_the_cell_assessment(self):
        case = {
            "id": "cell-03",
            "welding_areas": [
                _area(),
                _area(
                    id="weld-zone-2",
                    x_mm=6.0,
                    max_permitted_void_diameter_mm=None,
                    drawing_reference=None,
                ),
            ],
            "voids": [_void()],
        }
        result = assess_bare_cell_welding_area_limits(case, _criteria())
        self.assertEqual(result["verdict"], LIMIT_NOT_ESTABLISHED)
        self.assertEqual(result["welding_areas_without_a_limit"], ("weld-zone-2",))

    def test_the_largest_void_across_the_cell_is_reported(self):
        case = {
            "id": "cell-04",
            "welding_areas": [_area(), _area(id="weld-zone-2", x_mm=6.0)],
            "voids": [_void(), _void(x_mm=7.0, diameter_mm=0.4)],
        }
        result = assess_bare_cell_welding_area_limits(case, _criteria())
        self.assertAlmostEqual(
            _ratio(result["largest_void_diameter_mm"], 0.4), 1.0, places=12
        )

    def test_a_duplicate_welding_area_id_rejected(self):
        case = {"id": "cell-05", "welding_areas": [_area(), _area()], "voids": []}
        with self.assertRaises(ValueError):
            assess_bare_cell_welding_area_limits(case, _criteria())

    def test_a_cell_declaring_no_welding_area_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_welding_area_limits(
                {"id": "cell-06", "welding_areas": [], "voids": []}
            )

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_welding_area_limits(["weld-zone-1"])


if __name__ == "__main__":
    unittest.main()
