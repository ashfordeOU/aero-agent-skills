"""Contract tests for the clause 12.6.13 contact evenness assessment.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused weld policy, a
contact with no declared weld footprint, a footprint the map never reached,
a footprint straddling the weldable band, a footprint too uneven for one
schedule, and a set of footprints whose means disagree too far for a single
schedule to serve them all.
"""

import unittest

from e2008_blocking_diode_contact_uniformity_logic import (
    CONTACT_MAP_INCOMPLETE,
    CONTACT_NOT_WELD_READY,
    CONTACT_READY_FOR_WELDING,
    DEFAULT_WELD_POLICY,
    GRADE_ABOVE_WELD_CEILING,
    GRADE_BELOW_WELD_FLOOR,
    GRADE_NOT_MAPPED,
    GRADE_UNEVEN_ACROSS_FOOTPRINT,
    GRADE_WELDABLE,
    WELD_FOOTPRINTS_NOT_ESTABLISHED,
    assess_blocking_diode_contact_uniformity,
    footprint_mean_spread_fraction,
    footprint_statistics,
    grade_weld_footprint,
    grade_weld_footprints,
    marginal_footprint_advisories,
    readings_in_footprint,
    unmapped_footprints,
    validate_thickness_reading,
    validate_weld_footprint,
    validate_weld_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_WELD_POLICY)
    policy.update(overrides)
    return policy


def _footprints():
    return [
        {"id": "wf-a", "start_mm": 0.0, "end_mm": 1.0},
        {"id": "wf-b", "start_mm": 2.0, "end_mm": 3.0},
    ]


def _readings():
    return [
        {"id": "r01", "position_mm": 0.1, "thickness_um": 7.8},
        {"id": "r02", "position_mm": 0.5, "thickness_um": 8.0},
        {"id": "r03", "position_mm": 0.9, "thickness_um": 8.2},
        {"id": "r04", "position_mm": 2.1, "thickness_um": 8.1},
        {"id": "r05", "position_mm": 2.5, "thickness_um": 7.9},
        {"id": "r06", "position_mm": 2.9, "thickness_um": 8.0},
    ]


def _case(**overrides):
    case = {"weld_footprints": _footprints(), "thickness_readings": _readings()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_weld_policy(DEFAULT_WELD_POLICY), DEFAULT_WELD_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_weld_policy("min_weldable_thickness_um")

    def test_an_inverted_weldable_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_weld_policy(
                _policy(min_weldable_thickness_um=12.0, max_weldable_thickness_um=4.0)
            )

    def test_a_zero_width_weldable_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_weld_policy(_policy(min_weldable_thickness_um=12.0))

    def test_an_advisory_spread_above_the_allowed_spread_rejected(self):
        with self.assertRaises(ValueError):
            validate_weld_policy(_policy(advisory_spread_fraction=0.4))

    def test_an_advisory_spread_equal_to_the_allowed_spread_is_admitted(self):
        self.assertIsNotNone(
            validate_weld_policy(_policy(advisory_spread_fraction=0.20))
        )

    def test_a_footprint_spread_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_weld_policy(_policy(max_footprint_spread_fraction=1.5))

    def test_a_fractional_reading_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_weld_policy(_policy(min_readings_per_footprint=2.5))

    def test_a_zero_reading_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_weld_policy(_policy(min_readings_per_footprint=0))


class ReadingAndFootprintTests(unittest.TestCase):
    def test_a_reading_is_read_back(self):
        checked = validate_thickness_reading(_readings()[0])
        self.assertEqual(checked["id"], "r01")
        self.assertAlmostEqual(checked["thickness_um"], 7.8, places=12)

    def test_a_blank_reading_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_reading(
                {"id": "  ", "position_mm": 0.1, "thickness_um": 7.8}
            )

    def test_a_negative_thickness_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_reading(
                {"id": "r99", "position_mm": 0.1, "thickness_um": -7.8}
            )

    def test_a_negative_position_is_admitted(self):
        checked = validate_thickness_reading(
            {"id": "r98", "position_mm": -0.4, "thickness_um": 7.8}
        )
        self.assertAlmostEqual(checked["position_mm"], -0.4, places=12)

    def test_a_footprint_is_read_back(self):
        span = validate_weld_footprint(_footprints()[0])
        self.assertEqual(span["id"], "wf-a")

    def test_a_footprint_ending_where_it_starts_rejected(self):
        with self.assertRaises(ValueError):
            validate_weld_footprint({"id": "wf-z", "start_mm": 1.0, "end_mm": 1.0})

    def test_a_non_mapping_footprint_rejected(self):
        with self.assertRaises(ValueError):
            validate_weld_footprint("wf-a")


class SelectionTests(unittest.TestCase):
    def test_only_the_readings_inside_the_span_are_taken(self):
        inside = readings_in_footprint(_readings(), _footprints()[0])
        self.assertEqual([one["id"] for one in inside], ["r01", "r02", "r03"])

    def test_a_reading_on_the_edge_is_inside(self):
        inside = readings_in_footprint(
            [{"id": "r-edge", "position_mm": 1.0, "thickness_um": 8.0}],
            _footprints()[0],
        )
        self.assertEqual(len(inside), 1)

    def test_a_reading_beyond_the_span_is_outside(self):
        inside = readings_in_footprint(
            [{"id": "r-out", "position_mm": 1.6, "thickness_um": 8.0}],
            _footprints()[0],
        )
        self.assertEqual(inside, ())

    def test_non_sequence_readings_rejected(self):
        with self.assertRaises(ValueError):
            readings_in_footprint("r01", _footprints()[0])


class StatisticsTests(unittest.TestCase):
    def test_the_mean_is_the_average_of_the_readings(self):
        inside = readings_in_footprint(_readings(), _footprints()[0])
        self.assertAlmostEqual(footprint_statistics(inside)["mean_um"], 8.0, places=9)

    def test_the_spread_is_taken_against_the_footprint_mean(self):
        inside = readings_in_footprint(_readings(), _footprints()[0])
        self.assertAlmostEqual(
            footprint_statistics(inside)["spread_fraction"], 0.4 / 8.0, places=9
        )

    def test_a_flat_footprint_has_no_spread(self):
        inside = [
            {"id": "f1", "position_mm": 0.1, "thickness_um": 8.0},
            {"id": "f2", "position_mm": 0.2, "thickness_um": 8.0},
        ]
        self.assertAlmostEqual(
            footprint_statistics(inside)["spread_fraction"], 0.0, places=12
        )

    def test_an_empty_footprint_has_no_statistics(self):
        with self.assertRaises(ValueError):
            footprint_statistics([])


class GradeTests(unittest.TestCase):
    def test_an_even_footprint_is_weldable(self):
        graded = grade_weld_footprint(_footprints()[0], _readings())
        self.assertEqual(graded["grade"], GRADE_WELDABLE)
        self.assertTrue(graded["weldable"])

    def test_a_sparse_footprint_is_left_unmapped(self):
        readings = [{"id": "r01", "position_mm": 0.1, "thickness_um": 7.8}]
        graded = grade_weld_footprint(_footprints()[0], readings)
        self.assertEqual(graded["grade"], GRADE_NOT_MAPPED)
        self.assertIsNone(graded["spread_fraction"])

    def test_a_thin_site_drops_below_the_weld_floor(self):
        readings = [
            {"id": "r01", "position_mm": 0.1, "thickness_um": 3.0},
            {"id": "r02", "position_mm": 0.5, "thickness_um": 3.2},
            {"id": "r03", "position_mm": 0.9, "thickness_um": 3.1},
        ]
        graded = grade_weld_footprint(_footprints()[0], readings)
        self.assertEqual(graded["grade"], GRADE_BELOW_WELD_FLOOR)

    def test_a_thick_site_rises_above_the_weld_ceiling(self):
        readings = [
            {"id": "r01", "position_mm": 0.1, "thickness_um": 14.0},
            {"id": "r02", "position_mm": 0.5, "thickness_um": 14.2},
            {"id": "r03", "position_mm": 0.9, "thickness_um": 14.1},
        ]
        graded = grade_weld_footprint(_footprints()[0], readings)
        self.assertEqual(graded["grade"], GRADE_ABOVE_WELD_CEILING)

    def test_a_footprint_on_both_band_edges_is_weldable(self):
        readings = [
            {
                "id": "r01",
                "position_mm": 0.1,
                "thickness_um": DEFAULT_WELD_POLICY["min_weldable_thickness_um"],
            },
            {"id": "r02", "position_mm": 0.5, "thickness_um": 4.2},
            {"id": "r03", "position_mm": 0.9, "thickness_um": 4.1},
        ]
        graded = grade_weld_footprint(_footprints()[0], readings)
        self.assertTrue(graded["weldable"])

    def test_an_uneven_footprint_inside_the_band_still_fails(self):
        readings = [
            {"id": "r01", "position_mm": 0.1, "thickness_um": 5.0},
            {"id": "r02", "position_mm": 0.5, "thickness_um": 8.0},
            {"id": "r03", "position_mm": 0.9, "thickness_um": 11.0},
        ]
        graded = grade_weld_footprint(_footprints()[0], readings)
        self.assertEqual(graded["grade"], GRADE_UNEVEN_ACROSS_FOOTPRINT)
        self.assertFalse(graded["weldable"])

    def test_a_footprint_can_carry_more_than_one_reason(self):
        readings = [
            {"id": "r01", "position_mm": 0.1, "thickness_um": 2.0},
            {"id": "r02", "position_mm": 0.5, "thickness_um": 8.0},
            {"id": "r03", "position_mm": 0.9, "thickness_um": 15.0},
        ]
        graded = grade_weld_footprint(_footprints()[0], readings)
        self.assertEqual(len(graded["reasons"]), 3)

    def test_a_duplicate_footprint_id_rejected(self):
        footprints = _footprints()
        footprints[1]["id"] = "wf-a"
        with self.assertRaises(ValueError):
            grade_weld_footprints(footprints, _readings())

    def test_an_empty_footprint_set_rejected(self):
        with self.assertRaises(ValueError):
            grade_weld_footprints([], _readings())


class ReproducibilityTests(unittest.TestCase):
    def test_agreeing_footprints_have_almost_no_mean_spread(self):
        graded = grade_weld_footprints(_footprints(), _readings())
        self.assertAlmostEqual(
            footprint_mean_spread_fraction(graded), 0.0, places=9
        )

    def test_disagreeing_footprints_show_their_mean_spread(self):
        readings = _readings()
        for reading in readings[3:]:
            reading["thickness_um"] = reading["thickness_um"] + 4.0
        graded = grade_weld_footprints(_footprints(), readings)
        self.assertAlmostEqual(
            footprint_mean_spread_fraction(graded), 0.4, places=9
        )

    def test_an_unmapped_set_carries_no_mean_spread(self):
        graded = grade_weld_footprints(
            _footprints(), [{"id": "r01", "position_mm": 0.1, "thickness_um": 8.0}]
        )
        with self.assertRaises(ValueError):
            footprint_mean_spread_fraction(graded)

    def test_unmapped_footprints_are_named(self):
        graded = grade_weld_footprints(
            _footprints(), [{"id": "r01", "position_mm": 0.1, "thickness_um": 8.0}]
        )
        self.assertEqual(unmapped_footprints(graded), ("wf-a", "wf-b"))


class AdvisoryTests(unittest.TestCase):
    def test_a_comfortable_contact_raises_no_advisory(self):
        graded = grade_weld_footprints(_footprints(), _readings())
        self.assertEqual(marginal_footprint_advisories(graded), ())

    def test_a_footprint_near_the_spread_limit_raises_an_advisory(self):
        readings = [
            {"id": "r01", "position_mm": 0.1, "thickness_um": 7.4},
            {"id": "r02", "position_mm": 0.5, "thickness_um": 8.0},
            {"id": "r03", "position_mm": 0.9, "thickness_um": 8.8},
        ]
        graded = grade_weld_footprints([_footprints()[0]], readings)
        advisories = marginal_footprint_advisories(graded)
        self.assertEqual(len(advisories), 1)
        self.assertIn("wf-a", advisories[0])


class AssessmentTests(unittest.TestCase):
    def test_an_even_contact_is_ready_for_welding(self):
        result = assess_blocking_diode_contact_uniformity(_case())
        self.assertEqual(result["verdict"], CONTACT_READY_FOR_WELDING)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["weldable_footprints"]), 2)

    def test_a_contact_with_no_weld_footprint_closes_the_assessment(self):
        case = _case()
        del case["weld_footprints"]
        result = assess_blocking_diode_contact_uniformity(case)
        self.assertEqual(result["verdict"], WELD_FOOTPRINTS_NOT_ESTABLISHED)

    def test_a_contact_with_no_reading_is_unknown_not_adequate(self):
        result = assess_blocking_diode_contact_uniformity(
            _case(thickness_readings=[])
        )
        self.assertEqual(result["verdict"], CONTACT_MAP_INCOMPLETE)
        self.assertTrue(result["findings"])

    def test_a_footprint_the_map_missed_closes_the_assessment(self):
        readings = _readings()[:4]
        result = assess_blocking_diode_contact_uniformity(
            _case(thickness_readings=readings)
        )
        self.assertEqual(result["verdict"], CONTACT_MAP_INCOMPLETE)
        self.assertIn("wf-b", result["unmapped_footprints"])

    def test_a_thin_footprint_makes_the_contact_not_weld_ready(self):
        readings = _readings()
        readings[0]["thickness_um"] = 2.0
        result = assess_blocking_diode_contact_uniformity(
            _case(thickness_readings=readings)
        )
        self.assertEqual(result["verdict"], CONTACT_NOT_WELD_READY)
        self.assertIn("wf-a", result["rejected_footprints"])

    def test_footprints_that_each_pass_can_still_fail_together(self):
        readings = [
            {"id": "r01", "position_mm": 0.1, "thickness_um": 5.0},
            {"id": "r02", "position_mm": 0.5, "thickness_um": 5.1},
            {"id": "r03", "position_mm": 0.9, "thickness_um": 5.2},
            {"id": "r04", "position_mm": 2.1, "thickness_um": 11.0},
            {"id": "r05", "position_mm": 2.5, "thickness_um": 11.1},
            {"id": "r06", "position_mm": 2.9, "thickness_um": 11.2},
        ]
        result = assess_blocking_diode_contact_uniformity(
            _case(thickness_readings=readings)
        )
        self.assertEqual(len(result["weldable_footprints"]), 2)
        self.assertEqual(result["verdict"], CONTACT_NOT_WELD_READY)

    def test_the_worst_footprint_travels_with_the_verdict(self):
        result = assess_blocking_diode_contact_uniformity(_case())
        self.assertEqual(result["worst_footprint_id"], "wf-a")
        self.assertGreater(result["worst_footprint_spread_fraction"], 0.0)

    def test_the_mean_spread_is_reported(self):
        result = assess_blocking_diode_contact_uniformity(_case())
        self.assertAlmostEqual(
            result["footprint_mean_spread_fraction"], 0.0, places=9
        )

    def test_every_failing_footprint_is_named(self):
        readings = _readings()
        readings[0]["thickness_um"] = 2.0
        readings[3]["thickness_um"] = 16.0
        result = assess_blocking_diode_contact_uniformity(
            _case(thickness_readings=readings)
        )
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_advisories_do_not_move_a_ready_verdict(self):
        readings = [
            {"id": "r01", "position_mm": 0.1, "thickness_um": 7.4},
            {"id": "r02", "position_mm": 0.5, "thickness_um": 8.0},
            {"id": "r03", "position_mm": 0.9, "thickness_um": 8.8},
        ]
        result = assess_blocking_diode_contact_uniformity(
            _case(weld_footprints=[_footprints()[0]], thickness_readings=readings)
        )
        self.assertEqual(result["verdict"], CONTACT_READY_FOR_WELDING)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_contact_uniformity(["weld_footprints"])


if __name__ == "__main__":
    unittest.main()
