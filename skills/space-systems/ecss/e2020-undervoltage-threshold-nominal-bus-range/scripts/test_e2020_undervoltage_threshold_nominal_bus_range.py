"""Contract tests for the clause 5.4.3.1.1 adjustable trip point assessment.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a ladder of one setting, a
repeated trip point, a point at or above nominal, a setting band reaching
into the normal bus range, a band under the equipment floor, a usable span
that misses the required range, a step coarser than the design allows, an
adjustment reachable in flight, and a band landing exactly on its ceiling.
"""

import unittest

from e2020_undervoltage_threshold_nominal_bus_range_logic import (
    ADJUSTMENT_NOT_GROUND_ONLY,
    BELOW_EQUIPMENT_FLOOR,
    NOMINAL_BUS_NOT_ESTABLISHED,
    NUISANCE_TRIP_RISK,
    REQUIRED_RANGE_NOT_ESTABLISHED,
    SETTING_LADDER_NOT_ESTABLISHED,
    THRESHOLD_RANGE_COMPLIANT,
    THRESHOLD_RANGE_DEFICIENT,
    USABLE,
    adjustment_is_ground_only,
    assess_undervoltage_threshold_range,
    coarsest_step_percent,
    grade_ladder,
    grade_setting,
    range_coverage,
    setting_band,
    threshold_volts,
    usable_span_percent,
    validate_setting,
    validate_setting_ladder,
)

NOMINAL_V = 28.0


def _settings(points=(60.0, 65.0, 70.0, 75.0, 80.0)):
    return [
        {"id": "s%d" % index, "percent_of_nominal": point}
        for index, point in enumerate(points, start=1)
    ]


def _limits(**overrides):
    limits = {
        "relative_tolerance": 0.02,
        "absolute_tolerance_v": 0.1,
        "minimum_steady_state_bus_v": 24.0,
        "nuisance_clearance_v": 1.0,
        "equipment_minimum_operating_v": 16.0,
    }
    limits.update(overrides)
    return limits


def _case(**overrides):
    case = {
        "unit_id": "pcdu-uvp-1",
        "settings": _settings(),
        "nominal_bus_v": NOMINAL_V,
        "required_low_percent": 60.0,
        "required_high_percent": 80.0,
        "max_step_percent": 5.0,
        "adjustment_means": "ground-fitted strap",
        "limits": _limits(),
    }
    case.update(overrides)
    return case


class LadderTests(unittest.TestCase):
    def test_the_reference_ladder_validates_in_rising_order(self):
        ladder = validate_setting_ladder(_settings((80.0, 60.0, 70.0)))
        self.assertEqual(
            [entry["percent_of_nominal"] for entry in ladder], [60.0, 70.0, 80.0]
        )

    def test_a_single_setting_is_not_an_adjustable_threshold(self):
        with self.assertRaises(ValueError):
            validate_setting_ladder(_settings((60.0,)))

    def test_a_repeated_trip_point_is_refused(self):
        with self.assertRaises(ValueError):
            validate_setting_ladder(_settings((60.0, 60.0, 70.0)))

    def test_a_duplicate_setting_id_is_refused(self):
        with self.assertRaises(ValueError):
            validate_setting_ladder(
                [
                    {"id": "s1", "percent_of_nominal": 60.0},
                    {"id": "s1", "percent_of_nominal": 70.0},
                ]
            )

    def test_a_trip_point_at_nominal_is_not_an_undervoltage_trip(self):
        with self.assertRaises(ValueError):
            validate_setting({"id": "s1", "percent_of_nominal": 100.0})

    def test_a_blank_setting_id_is_refused(self):
        with self.assertRaises(ValueError):
            validate_setting({"id": "  ", "percent_of_nominal": 60.0})

    def test_a_non_mapping_setting_is_refused(self):
        with self.assertRaises(ValueError):
            validate_setting(["s1", 60.0])

    def test_the_coarsest_step_is_the_widest_neighbouring_gap(self):
        self.assertAlmostEqual(
            coarsest_step_percent(_settings((60.0, 65.0, 78.0))), 13.0, places=9
        )


class ConversionTests(unittest.TestCase):
    def test_a_share_of_nominal_becomes_volts(self):
        self.assertAlmostEqual(threshold_volts(60.0, NOMINAL_V), 16.8, places=9)

    def test_the_same_share_follows_a_different_bus(self):
        self.assertAlmostEqual(threshold_volts(60.0, 50.0), 30.0, places=9)

    def test_a_zero_nominal_bus_is_refused(self):
        with self.assertRaises(ValueError):
            threshold_volts(60.0, 0.0)

    def test_the_band_widens_the_point_both_ways(self):
        band = setting_band(21.0, 0.02, 0.1)
        self.assertAlmostEqual(band["spread_v"], 0.52, places=9)
        self.assertAlmostEqual(band["lower_v"], 20.48, places=9)
        self.assertAlmostEqual(band["upper_v"], 21.52, places=9)

    def test_a_relative_tolerance_at_unity_is_refused(self):
        with self.assertRaises(ValueError):
            setting_band(21.0, 1.0, 0.0)

    def test_a_negative_absolute_tolerance_is_refused(self):
        with self.assertRaises(ValueError):
            setting_band(21.0, 0.0, -0.1)


class GradeTests(unittest.TestCase):
    def test_a_setting_clear_of_both_bounds_is_usable(self):
        graded = grade_setting(
            {"id": "s1", "percent_of_nominal": 70.0}, NOMINAL_V, _limits()
        )
        self.assertTrue(graded["usable"])
        self.assertEqual(graded["outcome"], USABLE)

    def test_a_setting_reaching_into_the_normal_bus_range_is_not_usable(self):
        graded = grade_setting(
            {"id": "s1", "percent_of_nominal": 85.0}, NOMINAL_V, _limits()
        )
        self.assertFalse(graded["usable"])
        self.assertIn(NUISANCE_TRIP_RISK, graded["reasons"])

    def test_a_setting_under_the_equipment_floor_is_not_usable(self):
        graded = grade_setting(
            {"id": "s1", "percent_of_nominal": 55.0}, NOMINAL_V, _limits()
        )
        self.assertFalse(graded["usable"])
        self.assertIn(BELOW_EQUIPMENT_FLOOR, graded["reasons"])

    def test_a_band_landing_exactly_on_the_ceiling_is_usable(self):
        limits = _limits(relative_tolerance=0.0, absolute_tolerance_v=0.0)
        percent = 23.0 / NOMINAL_V * 100.0
        graded = grade_setting(
            {"id": "s1", "percent_of_nominal": percent}, NOMINAL_V, limits
        )
        self.assertAlmostEqual(graded["band_upper_v"], 23.0, places=9)
        self.assertTrue(graded["usable"])

    def test_a_band_landing_exactly_on_the_floor_is_usable(self):
        limits = _limits(relative_tolerance=0.0, absolute_tolerance_v=0.0)
        percent = 16.0 / NOMINAL_V * 100.0
        graded = grade_setting(
            {"id": "s1", "percent_of_nominal": percent}, NOMINAL_V, limits
        )
        self.assertAlmostEqual(graded["band_lower_v"], 16.0, places=9)
        self.assertTrue(graded["usable"])

    def test_a_missing_minimum_bus_voltage_is_refused(self):
        limits = _limits()
        del limits["minimum_steady_state_bus_v"]
        with self.assertRaises(ValueError):
            grade_setting({"id": "s1", "percent_of_nominal": 70.0}, NOMINAL_V, limits)

    def test_the_graded_ladder_keeps_rising_order(self):
        graded = grade_ladder(_settings((80.0, 60.0)), NOMINAL_V, _limits())
        self.assertAlmostEqual(graded[0]["percent_of_nominal"], 60.0, places=9)


class SpanTests(unittest.TestCase):
    def test_the_usable_span_is_the_extremes_of_the_usable_settings(self):
        graded = grade_ladder(
            _settings((55.0, 60.0, 70.0, 80.0, 85.0)), NOMINAL_V, _limits()
        )
        span = usable_span_percent(graded)
        self.assertAlmostEqual(span["low_percent"], 60.0, places=9)
        self.assertAlmostEqual(span["high_percent"], 80.0, places=9)
        self.assertEqual(span["usable_count"], 3)

    def test_a_ladder_with_nothing_usable_has_no_span(self):
        graded = grade_ladder(_settings((50.0, 90.0)), NOMINAL_V, _limits())
        self.assertIsNone(usable_span_percent(graded))

    def test_a_span_reaching_both_ends_covers_the_requirement(self):
        span = {"low_percent": 60.0, "high_percent": 80.0, "usable_count": 5}
        self.assertTrue(range_coverage(span, 60.0, 80.0)["covered"])

    def test_a_span_short_at_the_top_reports_the_shortfall(self):
        span = {"low_percent": 60.0, "high_percent": 72.0, "usable_count": 3}
        coverage = range_coverage(span, 60.0, 80.0)
        self.assertFalse(coverage["covered"])
        self.assertAlmostEqual(coverage["high_shortfall_percent"], 8.0, places=9)

    def test_a_required_range_that_does_not_rise_is_refused(self):
        with self.assertRaises(ValueError):
            range_coverage(None, 80.0, 60.0)

    def test_a_ground_strap_is_a_ground_activity(self):
        self.assertTrue(adjustment_is_ground_only("ground-fitted strap"))
        self.assertTrue(adjustment_is_ground_only("selection resistor"))

    def test_a_telecommand_is_not_a_ground_activity(self):
        self.assertFalse(adjustment_is_ground_only("in-flight telecommand"))

    def test_a_blank_means_of_adjustment_is_refused(self):
        with self.assertRaises(ValueError):
            adjustment_is_ground_only("   ")


class AssessmentTests(unittest.TestCase):
    def test_the_nominal_ladder_is_compliant(self):
        result = assess_undervoltage_threshold_range(_case())
        self.assertEqual(result["verdict"], THRESHOLD_RANGE_COMPLIANT)
        self.assertEqual(result["findings"], [])

    def test_a_missing_ladder_closes_the_assessment(self):
        case = _case()
        del case["settings"]
        self.assertEqual(
            assess_undervoltage_threshold_range(case)["verdict"],
            SETTING_LADDER_NOT_ESTABLISHED,
        )

    def test_a_missing_nominal_bus_closes_the_assessment(self):
        case = _case()
        del case["nominal_bus_v"]
        self.assertEqual(
            assess_undervoltage_threshold_range(case)["verdict"],
            NOMINAL_BUS_NOT_ESTABLISHED,
        )

    def test_a_missing_required_range_closes_the_assessment(self):
        case = _case()
        del case["required_high_percent"]
        self.assertEqual(
            assess_undervoltage_threshold_range(case)["verdict"],
            REQUIRED_RANGE_NOT_ESTABLISHED,
        )

    def test_an_in_flight_adjustment_closes_the_assessment(self):
        result = assess_undervoltage_threshold_range(
            _case(adjustment_means="in-flight telecommand")
        )
        self.assertEqual(result["verdict"], ADJUSTMENT_NOT_GROUND_ONLY)
        self.assertIn("not a ground activity", result["findings"][0])

    def test_an_undeclared_means_of_adjustment_is_advised(self):
        case = _case()
        del case["adjustment_means"]
        result = assess_undervoltage_threshold_range(case)
        self.assertEqual(result["verdict"], THRESHOLD_RANGE_COMPLIANT)
        self.assertTrue(
            any("ground-only part" in note for note in result["advisories"])
        )

    def test_a_usable_span_short_of_the_requirement_is_deficient(self):
        result = assess_undervoltage_threshold_range(
            _case(settings=_settings((60.0, 65.0, 70.0)), max_step_percent=10.0)
        )
        self.assertEqual(result["verdict"], THRESHOLD_RANGE_DEFICIENT)
        self.assertTrue(any("miss the required" in note for note in result["findings"]))

    def test_an_unusable_setting_inside_the_required_range_is_a_finding(self):
        result = assess_undervoltage_threshold_range(
            _case(
                settings=_settings((60.0, 65.0, 70.0, 75.0, 79.0)),
                limits=_limits(minimum_steady_state_bus_v=23.0),
            )
        )
        self.assertEqual(result["verdict"], THRESHOLD_RANGE_DEFICIENT)
        self.assertTrue(
            any("normal operation" in note for note in result["findings"])
        )

    def test_an_unusable_setting_outside_the_required_range_is_only_advised(self):
        result = assess_undervoltage_threshold_range(
            _case(settings=_settings((60.0, 65.0, 70.0, 75.0, 80.0, 85.0)))
        )
        self.assertEqual(result["verdict"], THRESHOLD_RANGE_COMPLIANT)
        self.assertTrue(
            any("stays selectable" in note for note in result["advisories"])
        )

    def test_a_ladder_with_nothing_usable_is_deficient(self):
        result = assess_undervoltage_threshold_range(
            _case(settings=_settings((50.0, 90.0)), max_step_percent=40.0)
        )
        self.assertEqual(result["verdict"], THRESHOLD_RANGE_DEFICIENT)
        self.assertIsNone(result["usable_span_percent"])
        self.assertTrue(
            any("not adjustable anywhere" in note for note in result["findings"])
        )

    def test_a_step_coarser_than_the_design_allows_is_a_finding(self):
        result = assess_undervoltage_threshold_range(
            _case(settings=_settings((60.0, 70.0, 80.0)), max_step_percent=5.0)
        )
        self.assertEqual(result["verdict"], THRESHOLD_RANGE_DEFICIENT)
        self.assertTrue(any("coarser than" in note for note in result["findings"]))

    def test_a_step_exactly_on_the_resolution_limit_passes(self):
        result = assess_undervoltage_threshold_range(_case(max_step_percent=5.0))
        self.assertAlmostEqual(result["coarsest_step_percent"], 5.0, places=9)
        self.assertEqual(result["verdict"], THRESHOLD_RANGE_COMPLIANT)

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_undervoltage_threshold_range(["settings"])


if __name__ == "__main__":
    unittest.main()
