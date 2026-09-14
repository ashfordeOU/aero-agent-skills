"""Contract tests for the clause 9.6.2.5.2 diode contact void limits."""

import math
import unittest

from e2008_diode_contact_void_limits_logic import (
    ACCEPT,
    ANODE,
    BUBBLE,
    CATHODE,
    DEFAULT_VOID_CRITERIA,
    NOT_ESTABLISHED,
    REFER_FOR_REVIEW,
    REJECT,
    VOID,
    assess_contact_voids,
    assess_diode_contact_voids,
    categorize_void_group,
    centre_separation_mm,
    coalesced_groups,
    group_extent_mm,
    void_area_mm2,
    void_elongation,
    void_equivalent_diameter_mm,
    void_max_extent_mm,
    voided_area_fraction,
    voided_area_mm2,
    voids_coalesce,
    validate_void,
    validate_void_contact,
    validate_void_criteria,
    worst_disposition,
)


def _criteria(**overrides):
    criteria = dict(DEFAULT_VOID_CRITERIA)
    criteria.update(overrides)
    return criteria


def _void(**overrides):
    cavity = {
        "id": "v1",
        "kind": VOID,
        "polarity": ANODE,
        "x_mm": 0.0,
        "y_mm": 0.0,
        "major_mm": 0.15,
        "minor_mm": 0.10,
    }
    cavity.update(overrides)
    return cavity


def _anode(**overrides):
    contact = {"id": "anode-land", "polarity": ANODE, "area_mm2": 1.0}
    contact.update(overrides)
    return contact


def _cathode(**overrides):
    contact = {"id": "cathode-land", "polarity": CATHODE, "area_mm2": 1.0}
    contact.update(overrides)
    return contact


def _case(**overrides):
    case = {
        "id": "diode-01",
        "contacts": [_anode(), _cathode()],
        "voids": [_void()],
    }
    case.update(overrides)
    return case


def _spread(count, **overrides):
    """count cavities far enough apart that none of them coalesce."""
    return [
        _void(id="v%d" % index, x_mm=float(index), **overrides)
        for index in range(count)
    ]


def _ratio(value, expected):
    return value / expected


class CriteriaTests(unittest.TestCase):
    def test_the_default_criteria_validate(self):
        self.assertIs(validate_void_criteria(DEFAULT_VOID_CRITERIA),
                      DEFAULT_VOID_CRITERIA)

    def test_the_ceiling_is_a_quarter_of_a_millimetre(self):
        self.assertAlmostEqual(
            DEFAULT_VOID_CRITERIA["max_void_extent_mm"], 0.25, places=12
        )

    def test_a_non_mapping_criteria_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_void_criteria("no bubbles please")

    def test_a_zero_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_void_criteria(_criteria(max_void_extent_mm=0.0))

    def test_a_negative_coalescence_gap_rejected(self):
        with self.assertRaises(ValueError):
            validate_void_criteria(_criteria(coalescence_gap_mm=-0.01))

    def test_a_review_band_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_void_criteria(_criteria(review_extent_fraction=1.6))


class VoidValidationTests(unittest.TestCase):
    def test_an_unknown_cavity_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_void(_void(kind="pinhole"))

    def test_a_bubble_is_a_recognised_kind(self):
        self.assertEqual(validate_void(_void(kind=BUBBLE))["kind"], BUBBLE)

    def test_an_unknown_polarity_rejected(self):
        with self.assertRaises(ValueError):
            validate_void(_void(polarity="either"))

    def test_a_minor_extent_longer_than_the_major_rejected(self):
        with self.assertRaises(ValueError):
            validate_void(_void(major_mm=0.10, minor_mm=0.20))

    def test_a_round_cavity_with_equal_extents_is_admissible(self):
        normalised = validate_void(_void(major_mm=0.12, minor_mm=0.12))
        self.assertAlmostEqual(
            _ratio(normalised["minor_mm"], 0.12), 1.0, places=12
        )

    def test_a_zero_major_extent_rejected(self):
        with self.assertRaises(ValueError):
            validate_void(_void(major_mm=0.0))

    def test_a_blank_void_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_void(_void(id="   "))

    def test_a_non_mapping_void_rejected(self):
        with self.assertRaises(ValueError):
            validate_void("a bubble near the edge")

    def test_a_blank_contact_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_void_contact(_anode(id=" "))

    def test_a_zero_area_contact_rejected(self):
        with self.assertRaises(ValueError):
            validate_void_contact(_anode(area_mm2=0.0))


class MeasureTests(unittest.TestCase):
    def test_the_governing_extent_is_the_major_dimension(self):
        self.assertAlmostEqual(
            _ratio(void_max_extent_mm(_void()), 0.15), 1.0, places=12
        )

    def test_an_elongated_bubble_passes_on_the_equivalent_diameter(self):
        stretched = _void(major_mm=0.40, minor_mm=0.10)
        self.assertAlmostEqual(void_equivalent_diameter_mm(stretched), 0.2,
                               places=9)
        self.assertAlmostEqual(void_max_extent_mm(stretched), 0.4, places=9)

    def test_the_cavity_area_is_the_ellipse_of_the_measured_extents(self):
        self.assertAlmostEqual(
            _ratio(void_area_mm2(_void(major_mm=0.2, minor_mm=0.2)),
                   math.pi / 4.0 * 0.04),
            1.0,
            places=9,
        )

    def test_elongation_is_the_ratio_of_the_extents(self):
        self.assertAlmostEqual(
            void_elongation(_void(major_mm=0.40, minor_mm=0.10)), 4.0, places=9
        )

    def test_centre_separation_is_the_plane_distance(self):
        self.assertAlmostEqual(
            centre_separation_mm(_void(), _void(id="v2", x_mm=0.3, y_mm=0.4)),
            0.5,
            places=9,
        )


class CoalescenceTests(unittest.TestCase):
    def test_two_cavities_that_have_closed_coalesce(self):
        self.assertTrue(
            voids_coalesce(_void(), _void(id="v2", x_mm=0.18), _criteria())
        )

    def test_two_cavities_far_apart_do_not_coalesce(self):
        self.assertFalse(
            voids_coalesce(_void(), _void(id="v2", x_mm=0.50), _criteria())
        )

    def test_cavities_exactly_on_the_coalescence_reach_still_merge(self):
        reach = (0.15 + 0.15) / 2.0 + DEFAULT_VOID_CRITERIA["coalescence_gap_mm"]
        self.assertAlmostEqual(reach, 0.2, places=9)
        self.assertTrue(
            voids_coalesce(_void(), _void(id="v2", x_mm=reach), _criteria())
        )

    def test_cavities_on_opposite_polarities_never_merge(self):
        self.assertFalse(
            voids_coalesce(
                _void(), _void(id="v2", polarity=CATHODE), _criteria()
            )
        )

    def test_separate_cavities_form_separate_groups(self):
        groups = coalesced_groups(_spread(3), _criteria())
        self.assertEqual(len(groups), 3)

    def test_a_closed_pair_forms_one_group(self):
        groups = coalesced_groups(
            [_void(), _void(id="v2", x_mm=0.18)], _criteria()
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)

    def test_a_chain_of_cavities_forms_one_group(self):
        chain = [
            _void(id="v1", x_mm=0.00),
            _void(id="v2", x_mm=0.18),
            _void(id="v3", x_mm=0.36),
        ]
        groups = coalesced_groups(chain, _criteria())
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 3)

    def test_a_non_sequence_void_list_rejected(self):
        with self.assertRaises(ValueError):
            coalesced_groups(_void(), _criteria())


class GroupExtentTests(unittest.TestCase):
    def test_a_lone_cavity_spans_its_own_major_extent(self):
        self.assertAlmostEqual(
            _ratio(group_extent_mm([_void()], _criteria()), 0.15), 1.0, places=9
        )

    def test_a_closed_pair_spans_the_distance_plus_both_radii(self):
        pair = [_void(), _void(id="v2", x_mm=0.18)]
        self.assertAlmostEqual(
            group_extent_mm(pair, _criteria()), 0.18 + 0.075 + 0.075, places=9
        )

    def test_an_empty_group_rejected(self):
        with self.assertRaises(ValueError):
            group_extent_mm([], _criteria())

    def test_a_non_sequence_group_rejected(self):
        with self.assertRaises(ValueError):
            group_extent_mm(_void(), _criteria())


class GroupDispositionTests(unittest.TestCase):
    def test_a_small_cavity_is_accepted(self):
        disposition, _reason = categorize_void_group([_void()], _criteria())
        self.assertEqual(disposition, ACCEPT)

    def test_a_cavity_past_the_ceiling_rejects(self):
        disposition, reason = categorize_void_group(
            [_void(major_mm=0.40, minor_mm=0.10)], _criteria()
        )
        self.assertEqual(disposition, REJECT)
        self.assertIn("ceiling", reason)

    def test_a_cavity_exactly_on_the_ceiling_is_not_rejected(self):
        on_limit = _void(major_mm=0.25, minor_mm=0.25)
        self.assertAlmostEqual(
            group_extent_mm([on_limit], _criteria()),
            DEFAULT_VOID_CRITERIA["max_void_extent_mm"],
            places=9,
        )
        disposition, _reason = categorize_void_group([on_limit], _criteria())
        self.assertEqual(disposition, REFER_FOR_REVIEW)

    def test_a_cavity_in_the_review_band_goes_to_review(self):
        disposition, reason = categorize_void_group(
            [_void(major_mm=0.22, minor_mm=0.10)], _criteria()
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("review band", reason)

    def test_a_cavity_exactly_on_the_review_band_goes_to_review(self):
        band = (
            DEFAULT_VOID_CRITERIA["review_extent_fraction"]
            * DEFAULT_VOID_CRITERIA["max_void_extent_mm"]
        )
        self.assertAlmostEqual(band, 0.2, places=9)
        disposition, _reason = categorize_void_group(
            [_void(major_mm=band, minor_mm=0.1)], _criteria()
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)

    def test_two_passing_cavities_that_closed_reject_together(self):
        pair = [_void(), _void(id="v2", x_mm=0.18)]
        for cavity in pair:
            lone, _reason = categorize_void_group([cavity], _criteria())
            self.assertEqual(lone, ACCEPT)
        disposition, reason = categorize_void_group(pair, _criteria())
        self.assertEqual(disposition, REJECT)
        self.assertIn("alone would have passed", reason)


class WorstDispositionTests(unittest.TestCase):
    def test_an_empty_set_accepts(self):
        self.assertEqual(worst_disposition([]), ACCEPT)

    def test_severity_beats_record_order(self):
        self.assertEqual(worst_disposition([REFER_FOR_REVIEW, REJECT, ACCEPT]),
                         REJECT)

    def test_an_unsurveyed_polarity_outranks_a_review(self):
        self.assertEqual(
            worst_disposition([REFER_FOR_REVIEW, NOT_ESTABLISHED]), NOT_ESTABLISHED
        )

    def test_an_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition([ACCEPT, "small enough"])


class ContactSurveyTests(unittest.TestCase):
    def test_a_contact_with_no_cavities_is_accepted(self):
        result = assess_contact_voids(_anode(), [], _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["cavities_surveyed"], 0)
        self.assertAlmostEqual(result["largest_extent_mm"], 0.0, places=12)

    def test_a_contact_only_takes_the_cavities_of_its_own_polarity(self):
        result = assess_contact_voids(
            _anode(), [_void(), _void(id="v2", polarity=CATHODE)], _criteria()
        )
        self.assertEqual(result["cavities_surveyed"], 1)

    def test_an_oversized_cavity_rejects_the_contact(self):
        result = assess_contact_voids(
            _anode(), [_void(major_mm=0.40, minor_mm=0.10)], _criteria()
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_the_elongated_cavity_an_equivalent_diameter_would_pass_is_named(self):
        result = assess_contact_voids(
            _anode(), [_void(major_mm=0.40, minor_mm=0.10)], _criteria()
        )
        self.assertEqual(
            result["cavities_an_equivalent_diameter_would_have_passed"], ("v1",)
        )

    def test_a_round_oversized_cavity_is_not_named_as_elongated(self):
        result = assess_contact_voids(
            _anode(), [_void(major_mm=0.40, minor_mm=0.40)], _criteria()
        )
        self.assertEqual(
            result["cavities_an_equivalent_diameter_would_have_passed"], ()
        )

    def test_the_voided_area_totals_across_the_contact(self):
        cavities = _spread(3, major_mm=0.2, minor_mm=0.2)
        self.assertAlmostEqual(
            _ratio(voided_area_mm2(cavities), 3.0 * math.pi / 4.0 * 0.04),
            1.0,
            places=9,
        )
        self.assertAlmostEqual(
            voided_area_fraction(cavities, _anode(area_mm2=2.0)),
            voided_area_mm2(cavities) / 2.0,
            places=12,
        )

    def test_many_small_cavities_use_the_land_up(self):
        result = assess_contact_voids(
            _anode(), _spread(6, major_mm=0.15, minor_mm=0.15), _criteria()
        )
        self.assertEqual(result["verdict"], REFER_FOR_REVIEW)
        self.assertEqual(result["groups_formed"], 6)
        self.assertIn("mostly cavity", result["findings"][0])

    def test_the_same_cavities_one_fewer_stay_inside_the_area_allowance(self):
        result = assess_contact_voids(
            _anode(), _spread(5, major_mm=0.15, minor_mm=0.15), _criteria()
        )
        self.assertEqual(result["verdict"], ACCEPT)

    def test_an_oversized_group_outranks_the_area_allowance(self):
        cavities = _spread(6, major_mm=0.15, minor_mm=0.15)
        cavities.append(_void(id="big", x_mm=20.0, major_mm=0.40, minor_mm=0.10))
        result = assess_contact_voids(_anode(), cavities, _criteria())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_non_sequence_void_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_contact_voids(_anode(), "one bubble", _criteria())


class DiodeRollupTests(unittest.TestCase):
    def test_a_diode_surveyed_on_both_polarities_is_accepted(self):
        result = assess_diode_contact_voids(_case(), _criteria())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["contacts_assessed"], 2)
        self.assertEqual(result["polarities_without_a_survey"], ())

    def test_a_diode_surveyed_on_one_polarity_cannot_be_accepted(self):
        result = assess_diode_contact_voids(
            _case(contacts=[_anode()]), _criteria()
        )
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)
        self.assertEqual(result["polarities_without_a_survey"], (CATHODE,))
        self.assertIn("either polarity", result["rollup_findings"][0])

    def test_a_missing_anode_survey_is_named_too(self):
        result = assess_diode_contact_voids(
            _case(contacts=[_cathode()], voids=[]), _criteria()
        )
        self.assertEqual(result["polarities_without_a_survey"], (ANODE,))

    def test_a_cavity_on_an_undeclared_polarity_is_never_sentenced(self):
        result = assess_diode_contact_voids(
            _case(contacts=[_anode()], voids=[_void(id="vx", polarity=CATHODE)]),
            _criteria(),
        )
        self.assertEqual(result["cavities_on_an_undeclared_polarity"], ("vx",))
        self.assertEqual(result["verdict"], NOT_ESTABLISHED)

    def test_an_oversized_cavity_outranks_an_unsurveyed_polarity(self):
        result = assess_diode_contact_voids(
            _case(
                contacts=[_anode()],
                voids=[_void(major_mm=0.40, minor_mm=0.10)],
            ),
            _criteria(),
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_one_bad_land_governs_the_diode(self):
        result = assess_diode_contact_voids(
            _case(
                voids=[
                    _void(),
                    _void(id="v2", polarity=CATHODE, major_mm=0.40, minor_mm=0.10),
                ]
            ),
            _criteria(),
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["contacts_not_accepted"], ("cathode-land",))

    def test_the_largest_extent_is_reported_across_both_lands(self):
        result = assess_diode_contact_voids(
            _case(
                voids=[
                    _void(),
                    _void(id="v2", polarity=CATHODE, major_mm=0.22, minor_mm=0.10),
                ]
            ),
            _criteria(),
        )
        self.assertAlmostEqual(result["largest_extent_mm"], 0.22, places=9)

    def test_a_duplicate_contact_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_contact_voids(
                _case(contacts=[_anode(), _anode()]), _criteria()
            )

    def test_a_diode_declaring_no_contact_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_contact_voids(_case(contacts=[]), _criteria())

    def test_a_non_sequence_contact_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_contact_voids(_case(contacts="anode-land"), _criteria())

    def test_a_non_sequence_void_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_contact_voids(_case(voids="one bubble"), _criteria())

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_contact_voids(["diode-01"], _criteria())


if __name__ == "__main__":
    unittest.main()
