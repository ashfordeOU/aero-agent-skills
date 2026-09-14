"""Contract tests for the clause 7.5.1.5.1 contact area general condition."""

import unittest

from e2008_bare_cell_contact_area_general_logic import (
    ABSENT,
    ACCEPT,
    DEFAULT_CONTACT_AREA_CRITERIA,
    DIG,
    INSIDE,
    INTACT,
    OUTSIDE,
    OUTSIDE_CONTACT_AREA,
    PROBE_MARK,
    REFER_FOR_REVIEW,
    REJECT,
    SCRATCH,
    STRADDLING,
    THINNED,
    assess_bare_cell_contact_area,
    assess_contact_area,
    categorize_contact_defect,
    contact_area_mm2,
    defect_footprint_mm2,
    defect_placement,
    disturbed_area_fraction,
    disturbed_area_mm2,
    exposed_area_mm2,
    overlap_area_mm2,
    probe_witness_count,
    validate_contact_area,
    validate_contact_area_criteria,
    validate_defect,
    worst_disposition,
)


def _criteria(**overrides):
    criteria = dict(DEFAULT_CONTACT_AREA_CRITERIA)
    criteria.update(overrides)
    return criteria


def _area(**overrides):
    area = {
        "id": "front-bar-1",
        "x_mm": 0.0,
        "y_mm": 0.0,
        "width_mm": 2.0,
        "length_mm": 20.0,
    }
    area.update(overrides)
    return area


def _mark(**overrides):
    mark = {
        "kind": DIG,
        "x_mm": 0.5,
        "y_mm": 5.0,
        "width_mm": 0.2,
        "length_mm": 0.2,
        "metallisation": INTACT,
    }
    mark.update(overrides)
    return mark


def _ratio(value, expected):
    return value / expected


class CriteriaTests(unittest.TestCase):
    def test_the_default_criteria_validate(self):
        self.assertIs(
            validate_contact_area_criteria(DEFAULT_CONTACT_AREA_CRITERIA),
            DEFAULT_CONTACT_AREA_CRITERIA,
        )

    def test_a_non_mapping_criteria_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_area_criteria("keep the contacts clear")

    def test_a_working_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_area_criteria(
                _criteria(min_remaining_metallisation_fraction=1.5)
            )

    def test_a_negative_probe_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_area_criteria(
                _criteria(max_probe_witnesses_per_contact_area=-1)
            )


class GeometryTests(unittest.TestCase):
    def test_a_contact_area_footprint_is_its_width_times_its_length(self):
        self.assertAlmostEqual(_ratio(contact_area_mm2(_area()), 40.0), 1.0, places=12)

    def test_a_zero_width_contact_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_area(_area(width_mm=0.0))

    def test_a_blank_contact_area_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_area(_area(id="  "))

    def test_a_mark_footprint_is_its_own_extent(self):
        self.assertAlmostEqual(
            _ratio(defect_footprint_mm2(_mark()), 0.04), 1.0, places=12
        )

    def test_a_mark_fully_inside_overlaps_by_its_whole_footprint(self):
        self.assertAlmostEqual(
            _ratio(overlap_area_mm2(_mark(), _area()), 0.04), 1.0, places=12
        )

    def test_a_mark_clear_of_the_area_overlaps_by_nothing(self):
        self.assertAlmostEqual(
            overlap_area_mm2(_mark(x_mm=10.0), _area()), 0.0, places=12
        )

    def test_a_straddling_mark_contributes_only_its_overlap(self):
        straddler = _mark(x_mm=1.9, width_mm=0.2)
        self.assertAlmostEqual(
            _ratio(overlap_area_mm2(straddler, _area()), 0.02), 1.0, places=9
        )

    def test_placement_names_a_contained_mark_inside(self):
        self.assertEqual(defect_placement(_mark(), _area()), INSIDE)

    def test_placement_names_a_straddling_mark(self):
        self.assertEqual(
            defect_placement(_mark(x_mm=1.9, width_mm=0.2), _area()), STRADDLING
        )

    def test_placement_names_a_distant_mark_outside(self):
        self.assertEqual(defect_placement(_mark(x_mm=10.0), _area()), OUTSIDE)

    def test_a_mark_touching_the_edge_without_crossing_is_outside(self):
        self.assertEqual(defect_placement(_mark(x_mm=2.0), _area()), OUTSIDE)


class DefectValidationTests(unittest.TestCase):
    def test_an_unknown_mark_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_defect(_mark(kind="crater"))

    def test_an_unknown_metallisation_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_defect(_mark(metallisation="mostly there"))

    def test_a_thinned_mark_without_a_remaining_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_defect(_mark(metallisation=THINNED))

    def test_a_thinned_mark_with_a_zero_remaining_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_defect(
                _mark(metallisation=THINNED, remaining_metallisation_fraction=0.0)
            )

    def test_a_negative_mark_extent_rejected(self):
        with self.assertRaises(ValueError):
            validate_defect(_mark(width_mm=-0.2))

    def test_a_negative_coordinate_is_admissible(self):
        normalised = validate_defect(_mark(x_mm=-3.0))
        self.assertAlmostEqual(normalised["x_mm"], -3.0, places=12)


class DefectDispositionTests(unittest.TestCase):
    def test_a_mark_outside_every_contact_area_is_not_this_clause(self):
        disposition, reason = categorize_contact_defect(
            _mark(x_mm=10.0), _area(), _criteria()
        )
        self.assertEqual(disposition, OUTSIDE_CONTACT_AREA)
        self.assertIn("not what this clause", reason)

    def test_a_mark_baring_the_semiconductor_rejects(self):
        disposition, reason = categorize_contact_defect(
            _mark(metallisation=ABSENT), _area(), _criteria()
        )
        self.assertEqual(disposition, REJECT)
        self.assertIn("weld", reason)

    def test_a_straddling_mark_that_bares_metal_still_rejects(self):
        disposition, _reason = categorize_contact_defect(
            _mark(x_mm=1.9, width_mm=0.2, metallisation=ABSENT), _area(), _criteria()
        )
        self.assertEqual(disposition, REJECT)

    def test_a_dig_that_left_the_conductor_intact_is_accepted(self):
        disposition, _reason = categorize_contact_defect(
            _mark(), _area(), _criteria()
        )
        self.assertEqual(disposition, ACCEPT)

    def test_a_lightly_thinned_mark_is_accepted(self):
        disposition, _reason = categorize_contact_defect(
            _mark(metallisation=THINNED, remaining_metallisation_fraction=0.8),
            _area(),
            _criteria(),
        )
        self.assertEqual(disposition, ACCEPT)

    def test_a_mark_thinned_past_the_working_fraction_goes_to_review(self):
        disposition, reason = categorize_contact_defect(
            _mark(metallisation=THINNED, remaining_metallisation_fraction=0.2),
            _area(),
            _criteria(),
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("probe landing", reason)

    def test_a_mark_exactly_at_the_working_fraction_is_accepted(self):
        limit = DEFAULT_CONTACT_AREA_CRITERIA[
            "min_remaining_metallisation_fraction"
        ]
        self.assertAlmostEqual(_ratio(limit, 0.5), 1.0, places=12)
        disposition, _reason = categorize_contact_defect(
            _mark(metallisation=THINNED, remaining_metallisation_fraction=limit),
            _area(),
            _criteria(),
        )
        self.assertEqual(disposition, ACCEPT)

    def test_a_scratch_is_dispositioned_on_the_same_rule_as_a_dig(self):
        disposition, _reason = categorize_contact_defect(
            _mark(kind=SCRATCH, metallisation=ABSENT), _area(), _criteria()
        )
        self.assertEqual(disposition, REJECT)


class AreaTotalTests(unittest.TestCase):
    def test_exposed_area_counts_only_the_bared_marks(self):
        marks = [_mark(), _mark(y_mm=8.0, metallisation=ABSENT)]
        self.assertAlmostEqual(
            _ratio(exposed_area_mm2(marks, _area()), 0.04), 1.0, places=12
        )

    def test_disturbed_area_counts_every_mark_in_the_area(self):
        marks = [_mark(), _mark(y_mm=8.0, metallisation=ABSENT)]
        self.assertAlmostEqual(
            _ratio(disturbed_area_mm2(marks, _area()), 0.08), 1.0, places=12
        )

    def test_disturbed_area_ignores_marks_outside_the_area(self):
        marks = [_mark(), _mark(x_mm=10.0)]
        self.assertAlmostEqual(
            _ratio(disturbed_area_mm2(marks, _area()), 0.04), 1.0, places=12
        )

    def test_the_disturbed_fraction_divides_by_the_contact_footprint(self):
        marks = [_mark()]
        self.assertAlmostEqual(
            _ratio(disturbed_area_fraction(marks, _area()), 0.04 / 40.0),
            1.0,
            places=9,
        )

    def test_probe_witnesses_count_only_probe_marks_on_the_area(self):
        marks = [
            _mark(kind=PROBE_MARK),
            _mark(kind=PROBE_MARK, y_mm=9.0),
            _mark(kind=PROBE_MARK, x_mm=10.0),
            _mark(kind=SCRATCH, y_mm=12.0),
        ]
        self.assertEqual(probe_witness_count(marks, _area()), 2)

    def test_a_non_sequence_mark_record_rejected(self):
        with self.assertRaises(ValueError):
            disturbed_area_mm2("one dig", _area())


class WorstDispositionTests(unittest.TestCase):
    def test_an_empty_set_accepts(self):
        self.assertEqual(worst_disposition([]), ACCEPT)

    def test_severity_beats_record_order(self):
        self.assertEqual(
            worst_disposition([REJECT, ACCEPT, OUTSIDE_CONTACT_AREA]), REJECT
        )

    def test_an_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition([ACCEPT, "probably fine"])


class ContactAreaAssessmentTests(unittest.TestCase):
    def test_a_clear_contact_area_is_accepted(self):
        result = assess_contact_area(_area(), [], _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_one_bared_mark_rejects_the_contact_area(self):
        result = assess_contact_area(
            _area(), [_mark(metallisation=ABSENT)], _criteria()
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertAlmostEqual(
            _ratio(result["exposed_area_mm2"], 0.04), 1.0, places=12
        )

    def test_a_mark_off_the_contact_area_is_advised_not_counted(self):
        result = assess_contact_area(_area(), [_mark(x_mm=10.0)], _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["marks_in_area"], 0)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_worked_over_but_sound_area_goes_to_review(self):
        marks = [
            _mark(y_mm=1.0, width_mm=1.5, length_mm=1.5),
            _mark(y_mm=6.0, width_mm=1.5, length_mm=1.5),
        ]
        result = assess_contact_area(_area(), marks, _criteria())
        self.assertEqual(result["verdict"], REFER_FOR_REVIEW)
        self.assertAlmostEqual(
            _ratio(result["disturbed_area_fraction"], 4.5 / 40.0), 1.0, places=9
        )

    def test_too_many_probe_witnesses_go_to_review(self):
        marks = [
            _mark(kind=PROBE_MARK, y_mm=float(index)) for index in range(1, 6)
        ]
        result = assess_contact_area(_area(), marks, _criteria())
        self.assertEqual(result["verdict"], REFER_FOR_REVIEW)
        self.assertEqual(result["probe_witnesses"], 5)

    def test_probe_witnesses_at_the_allowance_do_not_trigger_a_review(self):
        marks = [
            _mark(kind=PROBE_MARK, y_mm=float(index)) for index in range(1, 4)
        ]
        result = assess_contact_area(_area(), marks, _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["probe_witnesses"], 3)

    def test_a_bared_mark_outranks_an_area_level_review(self):
        marks = [
            _mark(y_mm=1.0, width_mm=1.5, length_mm=1.5),
            _mark(y_mm=6.0, width_mm=1.5, length_mm=1.5, metallisation=ABSENT),
        ]
        result = assess_contact_area(_area(), marks, _criteria())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_non_sequence_defect_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_contact_area(_area(), "one dig", _criteria())


class CellRollupTests(unittest.TestCase):
    def test_a_cell_with_clear_contacts_is_accepted(self):
        case = {
            "id": "cell-01",
            "contact_areas": [_area(), _area(id="front-bar-2", x_mm=5.0)],
            "defects": [],
        }
        result = assess_bare_cell_contact_area(case, _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["contact_areas_assessed"], 2)

    def test_one_bad_contact_area_governs_the_cell(self):
        case = {
            "id": "cell-02",
            "contact_areas": [_area(), _area(id="front-bar-2", x_mm=5.0)],
            "defects": [_mark(x_mm=5.5, metallisation=ABSENT)],
        }
        result = assess_bare_cell_contact_area(case, _criteria())
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["contact_areas_not_accepted"], ("front-bar-2",))

    def test_a_mark_on_no_contact_area_is_named_and_does_not_reject(self):
        case = {
            "id": "cell-03",
            "contact_areas": [_area()],
            "defects": [_mark(x_mm=30.0, metallisation=ABSENT)],
        }
        result = assess_bare_cell_contact_area(case, _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["marks_outside_every_contact_area"], (DIG,))

    def test_the_total_exposed_area_sums_across_contact_areas(self):
        case = {
            "id": "cell-04",
            "contact_areas": [_area(), _area(id="front-bar-2", x_mm=5.0)],
            "defects": [
                _mark(metallisation=ABSENT),
                _mark(x_mm=5.5, metallisation=ABSENT),
            ],
        }
        result = assess_bare_cell_contact_area(case, _criteria())
        self.assertAlmostEqual(
            _ratio(result["total_exposed_area_mm2"], 0.08), 1.0, places=12
        )

    def test_a_duplicate_contact_area_id_rejected(self):
        case = {"id": "cell-05", "contact_areas": [_area(), _area()], "defects": []}
        with self.assertRaises(ValueError):
            assess_bare_cell_contact_area(case, _criteria())

    def test_a_cell_declaring_no_contact_area_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_contact_area(
                {"id": "cell-06", "contact_areas": [], "defects": []}
            )

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_contact_area(["front-bar-1"])


if __name__ == "__main__":
    unittest.main()
