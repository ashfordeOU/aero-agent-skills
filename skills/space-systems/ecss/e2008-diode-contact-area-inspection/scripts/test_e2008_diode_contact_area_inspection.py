"""Contract tests for the clause 9.6.2.5.1 diode contact area inspection."""

import unittest

from e2008_diode_contact_area_inspection_logic import (
    ABSENT,
    ACCEPT,
    ANODE,
    CATHODE,
    DEFAULT_DIODE_CONTACT_CRITERIA,
    DIG,
    INSIDE,
    INTACT,
    NOT_ESTABLISHED,
    OFF_CONTACT,
    OUTSIDE,
    PROBE_MARK,
    REFER_FOR_REVIEW,
    REJECT,
    SCRATCH,
    STRADDLING,
    THINNED,
    assess_diode_contact,
    assess_protection_diode_contacts,
    bared_mm2,
    categorize_contact_mark,
    clear_weld_land_fraction,
    diode_contact_mm2,
    disturbed_mm2,
    mark_footprint_mm2,
    mark_placement,
    overlap_mm2,
    probe_witness_count,
    validate_contact_mark,
    validate_diode_contact,
    validate_diode_contact_criteria,
    worst_disposition,
)


def _criteria(**overrides):
    criteria = dict(DEFAULT_DIODE_CONTACT_CRITERIA)
    criteria.update(overrides)
    return criteria


def _contact(**overrides):
    contact = {
        "id": "anode-land",
        "polarity": ANODE,
        "x_mm": 0.0,
        "y_mm": 0.0,
        "width_mm": 2.0,
        "length_mm": 2.0,
    }
    contact.update(overrides)
    return contact


def _cathode(**overrides):
    contact = {
        "id": "cathode-land",
        "polarity": CATHODE,
        "x_mm": 5.0,
        "y_mm": 0.0,
        "width_mm": 2.0,
        "length_mm": 2.0,
    }
    contact.update(overrides)
    return contact


def _mark(**overrides):
    mark = {
        "kind": DIG,
        "x_mm": 0.5,
        "y_mm": 0.5,
        "width_mm": 0.2,
        "length_mm": 0.2,
        "metallisation": INTACT,
    }
    mark.update(overrides)
    return mark


def _case(**overrides):
    case = {
        "id": "diode-01",
        "contacts": [_contact(), _cathode()],
        "marks": [_mark()],
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class CriteriaTests(unittest.TestCase):
    def test_the_default_criteria_validate(self):
        self.assertIs(
            validate_diode_contact_criteria(DEFAULT_DIODE_CONTACT_CRITERIA),
            DEFAULT_DIODE_CONTACT_CRITERIA,
        )

    def test_a_non_mapping_criteria_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_contact_criteria("keep the lands clean")

    def test_a_working_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_contact_criteria(
                _criteria(min_remaining_metallisation_fraction=1.4)
            )

    def test_a_negative_probe_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_contact_criteria(_criteria(max_probe_witnesses_per_contact=-1))


class ContactGeometryTests(unittest.TestCase):
    def test_a_contact_footprint_is_its_width_times_its_length(self):
        self.assertAlmostEqual(_ratio(diode_contact_mm2(_contact()), 4.0), 1.0,
                               places=12)

    def test_an_unknown_polarity_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_contact(_contact(polarity="middle"))

    def test_a_blank_contact_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_contact(_contact(id="  "))

    def test_a_zero_width_contact_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_contact(_contact(width_mm=0.0))

    def test_a_non_mapping_contact_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_contact("anode-land")


class PlacementTests(unittest.TestCase):
    def test_a_mark_footprint_is_its_own_extent(self):
        self.assertAlmostEqual(_ratio(mark_footprint_mm2(_mark()), 0.04), 1.0,
                               places=12)

    def test_a_mark_fully_on_the_land_overlaps_by_its_whole_footprint(self):
        self.assertAlmostEqual(
            _ratio(overlap_mm2(_mark(), _contact()), 0.04), 1.0, places=12
        )

    def test_a_mark_clear_of_the_land_overlaps_by_nothing(self):
        self.assertAlmostEqual(overlap_mm2(_mark(x_mm=3.0), _contact()), 0.0,
                               places=12)

    def test_a_straddling_mark_contributes_only_its_overlap(self):
        straddler = _mark(x_mm=1.9, width_mm=0.2)
        self.assertAlmostEqual(
            _ratio(overlap_mm2(straddler, _contact()), 0.02), 1.0, places=9
        )

    def test_placement_names_a_contained_mark_inside(self):
        self.assertEqual(mark_placement(_mark(), _contact()), INSIDE)

    def test_placement_names_a_straddling_mark(self):
        self.assertEqual(
            mark_placement(_mark(x_mm=1.9, width_mm=0.2), _contact()), STRADDLING
        )

    def test_placement_names_a_distant_mark_outside(self):
        self.assertEqual(mark_placement(_mark(x_mm=3.0), _contact()), OUTSIDE)

    def test_a_mark_touching_the_edge_without_crossing_is_outside(self):
        self.assertEqual(mark_placement(_mark(x_mm=2.0), _contact()), OUTSIDE)


class MarkValidationTests(unittest.TestCase):
    def test_an_unknown_mark_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_mark(_mark(kind="smudge"))

    def test_an_unknown_metallisation_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_mark(_mark(metallisation="mostly there"))

    def test_a_thinned_mark_without_a_remaining_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_mark(_mark(metallisation=THINNED))

    def test_a_thinned_mark_with_a_zero_remaining_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_mark(
                _mark(metallisation=THINNED, remaining_metallisation_fraction=0.0)
            )

    def test_a_negative_mark_extent_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_mark(_mark(length_mm=-0.2))

    def test_a_negative_coordinate_is_admissible(self):
        self.assertAlmostEqual(
            validate_contact_mark(_mark(y_mm=-1.0))["y_mm"], -1.0, places=12
        )


class MarkDispositionTests(unittest.TestCase):
    def test_a_mark_off_the_land_belongs_to_another_clause(self):
        disposition, reason = categorize_contact_mark(
            _mark(x_mm=3.0), _contact(), _criteria()
        )
        self.assertEqual(disposition, OFF_CONTACT)
        self.assertIn("another clause", reason)

    def test_a_mark_baring_the_semiconductor_rejects(self):
        disposition, reason = categorize_contact_mark(
            _mark(metallisation=ABSENT), _contact(), _criteria()
        )
        self.assertEqual(disposition, REJECT)
        self.assertIn("welded", reason)

    def test_a_straddling_mark_that_bares_metal_still_rejects(self):
        disposition, _reason = categorize_contact_mark(
            _mark(x_mm=1.9, width_mm=0.2, metallisation=ABSENT), _contact(),
            _criteria(),
        )
        self.assertEqual(disposition, REJECT)

    def test_a_dig_that_left_the_conductor_intact_is_accepted(self):
        disposition, _reason = categorize_contact_mark(_mark(), _contact(), _criteria())
        self.assertEqual(disposition, ACCEPT)

    def test_a_lightly_thinned_mark_is_accepted(self):
        disposition, _reason = categorize_contact_mark(
            _mark(metallisation=THINNED, remaining_metallisation_fraction=0.85),
            _contact(), _criteria(),
        )
        self.assertEqual(disposition, ACCEPT)

    def test_a_mark_thinned_past_the_working_fraction_goes_to_review(self):
        disposition, reason = categorize_contact_mark(
            _mark(metallisation=THINNED, remaining_metallisation_fraction=0.2),
            _contact(), _criteria(),
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("probe landing", reason)

    def test_a_mark_exactly_on_the_working_fraction_is_accepted(self):
        limit = DEFAULT_DIODE_CONTACT_CRITERIA["min_remaining_metallisation_fraction"]
        self.assertAlmostEqual(_ratio(limit, 0.5), 1.0, places=12)
        disposition, _reason = categorize_contact_mark(
            _mark(metallisation=THINNED, remaining_metallisation_fraction=limit),
            _contact(), _criteria(),
        )
        self.assertEqual(disposition, ACCEPT)

    def test_a_probe_mark_is_dispositioned_on_the_same_rule_as_a_scratch(self):
        probe, _reason = categorize_contact_mark(
            _mark(kind=PROBE_MARK, metallisation=ABSENT), _contact(), _criteria()
        )
        scratch, _reason2 = categorize_contact_mark(
            _mark(kind=SCRATCH, metallisation=ABSENT), _contact(), _criteria()
        )
        self.assertEqual(probe, REJECT)
        self.assertEqual(scratch, REJECT)


class ContactTotalTests(unittest.TestCase):
    def test_bared_area_counts_only_the_marks_that_went_through(self):
        marks = [_mark(), _mark(y_mm=1.2, metallisation=ABSENT)]
        self.assertAlmostEqual(_ratio(bared_mm2(marks, _contact()), 0.04), 1.0,
                               places=12)

    def test_disturbed_area_counts_every_mark_on_the_land(self):
        marks = [_mark(), _mark(y_mm=1.2, metallisation=ABSENT)]
        self.assertAlmostEqual(_ratio(disturbed_mm2(marks, _contact()), 0.08), 1.0,
                               places=12)

    def test_disturbed_area_ignores_marks_off_the_land(self):
        marks = [_mark(), _mark(x_mm=3.0)]
        self.assertAlmostEqual(_ratio(disturbed_mm2(marks, _contact()), 0.04), 1.0,
                               places=12)

    def test_the_clear_fraction_is_what_the_marks_left_alone(self):
        self.assertAlmostEqual(
            clear_weld_land_fraction([_mark()], _contact()), 0.99, places=9
        )

    def test_the_clear_fraction_floors_at_zero_when_marks_overlap(self):
        marks = [_mark(width_mm=2.0, length_mm=2.0, x_mm=0.0, y_mm=0.0)] * 3
        self.assertAlmostEqual(
            clear_weld_land_fraction(marks, _contact()), 0.0, places=12
        )

    def test_probe_witnesses_count_only_probe_marks_on_the_land(self):
        marks = [
            _mark(kind=PROBE_MARK),
            _mark(kind=PROBE_MARK, y_mm=1.2),
            _mark(kind=PROBE_MARK, x_mm=3.0),
            _mark(kind=SCRATCH, y_mm=1.6),
        ]
        self.assertEqual(probe_witness_count(marks, _contact()), 2)

    def test_a_non_sequence_mark_record_rejected(self):
        with self.assertRaises(ValueError):
            disturbed_mm2("one dig", _contact())


class WorstDispositionTests(unittest.TestCase):
    def test_an_empty_set_accepts(self):
        self.assertEqual(worst_disposition([]), ACCEPT)

    def test_severity_beats_record_order(self):
        self.assertEqual(worst_disposition([ACCEPT, REJECT, OFF_CONTACT]), REJECT)

    def test_a_bared_land_outranks_an_uninspected_polarity(self):
        self.assertEqual(worst_disposition([NOT_ESTABLISHED, REJECT]), REJECT)

    def test_an_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition([ACCEPT, "looks clean"])


class ContactAssessmentTests(unittest.TestCase):
    def test_a_clean_land_is_accepted(self):
        result = assess_diode_contact(_contact(), [], _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_one_bared_mark_rejects_the_land(self):
        result = assess_diode_contact(
            _contact(), [_mark(metallisation=ABSENT)], _criteria()
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertAlmostEqual(_ratio(result["bared_mm2"], 0.04), 1.0, places=12)

    def test_a_mark_off_the_land_is_advised_not_counted(self):
        result = assess_diode_contact(_contact(), [_mark(x_mm=3.0)], _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["marks_on_contact"], 0)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_used_up_weld_land_goes_to_review(self):
        result = assess_diode_contact(
            _contact(), [_mark(width_mm=0.7, length_mm=0.7)], _criteria()
        )
        self.assertEqual(result["verdict"], REFER_FOR_REVIEW)
        self.assertAlmostEqual(
            result["clear_weld_land_fraction"], 1.0 - 0.49 / 4.0, places=9
        )

    def test_a_land_exactly_on_the_clear_fraction_is_accepted(self):
        result = assess_diode_contact(
            _contact(), [_mark(width_mm=0.5, length_mm=0.8)], _criteria()
        )
        self.assertAlmostEqual(
            result["clear_weld_land_fraction"],
            DEFAULT_DIODE_CONTACT_CRITERIA["min_clear_weld_land_fraction"],
            places=9,
        )
        self.assertEqual(result["verdict"], ACCEPT)

    def test_too_many_probe_witnesses_go_to_review(self):
        marks = [
            _mark(kind=PROBE_MARK, y_mm=0.2 * index) for index in range(1, 5)
        ]
        result = assess_diode_contact(_contact(), marks, _criteria())
        self.assertEqual(result["verdict"], REFER_FOR_REVIEW)
        self.assertEqual(result["probe_witnesses"], 4)

    def test_probe_witnesses_on_the_allowance_do_not_trigger_a_review(self):
        marks = [_mark(kind=PROBE_MARK), _mark(kind=PROBE_MARK, y_mm=1.2)]
        result = assess_diode_contact(_contact(), marks, _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["probe_witnesses"], 2)

    def test_a_bared_mark_outranks_a_land_level_review(self):
        marks = [
            _mark(width_mm=0.7, length_mm=0.7),
            _mark(y_mm=1.5, metallisation=ABSENT),
        ]
        result = assess_diode_contact(_contact(), marks, _criteria())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_non_sequence_mark_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_contact(_contact(), "one dig", _criteria())


class DiodeRollupTests(unittest.TestCase):
    def test_a_diode_with_both_lands_clean_is_accepted(self):
        result = assess_protection_diode_contacts(_case(), _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["contacts_assessed"], 2)
        self.assertEqual(result["polarities_without_a_record"], ())

    def test_a_diode_inspected_on_one_polarity_cannot_be_accepted(self):
        result = assess_protection_diode_contacts(
            _case(contacts=[_contact()]), _criteria()
        )
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)
        self.assertEqual(result["polarities_without_a_record"], (CATHODE,))
        self.assertIn("not a", result["rollup_findings"][0])

    def test_a_missing_anode_record_is_named_too(self):
        result = assess_protection_diode_contacts(
            _case(contacts=[_cathode()], marks=[]), _criteria()
        )
        self.assertEqual(result["polarities_without_a_record"], (ANODE,))

    def test_a_bared_land_outranks_the_uninspected_polarity(self):
        result = assess_protection_diode_contacts(
            _case(contacts=[_contact()], marks=[_mark(metallisation=ABSENT)]),
            _criteria(),
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_one_bad_land_governs_the_diode(self):
        result = assess_protection_diode_contacts(
            _case(marks=[_mark(x_mm=5.5, metallisation=ABSENT)]), _criteria()
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["contacts_not_accepted"], ("cathode-land",))

    def test_the_total_bared_area_sums_across_both_lands(self):
        result = assess_protection_diode_contacts(
            _case(
                marks=[
                    _mark(metallisation=ABSENT),
                    _mark(x_mm=5.5, metallisation=ABSENT),
                ]
            ),
            _criteria(),
        )
        self.assertAlmostEqual(_ratio(result["total_bared_mm2"], 0.08), 1.0,
                               places=12)

    def test_a_mark_on_neither_land_is_named_and_does_not_reject(self):
        result = assess_protection_diode_contacts(
            _case(marks=[_mark(x_mm=3.0, metallisation=ABSENT)]), _criteria()
        )
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["marks_off_every_contact"], (DIG,))

    def test_a_duplicate_contact_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_protection_diode_contacts(
                _case(contacts=[_contact(), _contact()]), _criteria()
            )

    def test_a_diode_declaring_no_contact_rejected(self):
        with self.assertRaises(ValueError):
            assess_protection_diode_contacts(_case(contacts=[]), _criteria())

    def test_a_non_sequence_contact_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_protection_diode_contacts(_case(contacts="anode-land"), _criteria())

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_protection_diode_contacts(["diode-01"], _criteria())


if __name__ == "__main__":
    unittest.main()
