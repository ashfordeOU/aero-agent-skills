"""Contract tests for the clause 8.7.5.2.3 cut-on requirement logic."""

import unittest

from e2008_reflectance_cut_on_requirement_logic import (
    ABSOLUTE_HALF_LEVEL_BASIS,
    CUT_ON_MATCHES_DRAWING,
    CUT_ON_NOT_MEASURED,
    CUT_ON_NOT_RESOLVED,
    CUT_ON_OUTSIDE_DRAWING_TOLERANCE,
    DEFAULT_CUT_ON_POLICY,
    DRAWING_CUT_ON_ENTRY_MISSING,
    HALF_LEVEL_BASIS_MISAPPLIED,
    REFLECTANCE_BAND_TOO_WEAK,
    absolute_peak_reflectance,
    assess_cut_on_requirement,
    band_is_strong_enough,
    cut_on_deviation_nm,
    cut_on_is_resolvable,
    cut_on_matches_drawing,
    cut_on_wavelength,
    drawing_cut_on,
    half_of_absolute_reflectance,
    tolerance_band_nm,
    validate_cut_on_policy,
    validate_reflectance_trace,
)

# A blue reflector band: dark below 340 nm, 80 percent across the band,
# falling away again past 900 nm. The half level is 40 percent and the
# rising edge crosses it midway between 340 and 360 nm, at 350 nm.
BAND_TRACE = [
    (300.0, 0.0),
    (340.0, 0.0),
    (360.0, 80.0),
    (600.0, 80.0),
    (880.0, 80.0),
    (920.0, 0.0),
]

WEAK_TRACE = [
    (300.0, 0.0),
    (340.0, 0.0),
    (360.0, 8.0),
    (600.0, 8.0),
    (880.0, 8.0),
    (920.0, 0.0),
]

# A scan that starts already inside the band: the rising edge sits below
# the shortest wavelength measured, so no cut-on can be taken from it.
TRUNCATED_TRACE = [
    (400.0, 80.0),
    (500.0, 80.0),
    (600.0, 80.0),
    (880.0, 80.0),
    (920.0, 0.0),
]


def _policy(**overrides):
    policy = dict(DEFAULT_CUT_ON_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "drawing": {"cut_on_nm": 350.0, "tolerance_nm": 10.0},
        "measurement": {
            "half_level_basis": ABSOLUTE_HALF_LEVEL_BASIS,
            "trace": list(BAND_TRACE),
        },
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_cut_on_policy(DEFAULT_CUT_ON_POLICY), DEFAULT_CUT_ON_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_policy("tolerance")

    def test_zero_tolerance_default_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_policy(_policy(default_tolerance_nm=0.0))

    def test_peak_floor_above_the_reflectance_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_policy(_policy(min_usable_peak_percent=140.0))

    def test_scan_point_floor_below_three_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_policy(_policy(min_scan_points=2))

    def test_boolean_scan_point_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_policy(_policy(min_scan_points=True))


class TraceTests(unittest.TestCase):
    def test_a_well_formed_trace_is_returned_ordered(self):
        points = validate_reflectance_trace(BAND_TRACE)
        self.assertEqual(len(points), len(BAND_TRACE))
        self.assertAlmostEqual(points[0][0], 300.0, places=9)

    def test_a_non_sequence_trace_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_trace(350.0)

    def test_a_three_element_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_trace(
                [(300.0, 0.0, 1.0), (340.0, 0.0), (360.0, 80.0), (600.0, 80.0),
                 (920.0, 0.0)]
            )

    def test_a_repeated_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_trace(
                [(300.0, 0.0), (300.0, 5.0), (360.0, 80.0), (600.0, 80.0),
                 (920.0, 0.0)]
            )

    def test_a_reflectance_above_the_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_trace(
                [(300.0, 0.0), (340.0, 0.0), (360.0, 180.0), (600.0, 80.0),
                 (920.0, 0.0)]
            )

    def test_a_reflectance_exactly_at_the_ceiling_accepted(self):
        points = validate_reflectance_trace(
            [(300.0, 0.0), (340.0, 0.0), (360.0, 100.0), (600.0, 100.0),
             (920.0, 0.0)]
        )
        self.assertAlmostEqual(points[2][1], 100.0, places=9)

    def test_a_negative_reflectance_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_trace(
                [(300.0, -1.0), (340.0, 0.0), (360.0, 80.0), (600.0, 80.0),
                 (920.0, 0.0)]
            )

    def test_a_short_trace_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_trace([(300.0, 0.0), (360.0, 80.0)])


class HalfLevelTests(unittest.TestCase):
    def test_the_peak_is_the_largest_measured_reflectance(self):
        self.assertAlmostEqual(absolute_peak_reflectance(BAND_TRACE), 80.0, places=9)

    def test_the_half_level_is_half_the_absolute_peak(self):
        self.assertAlmostEqual(
            half_of_absolute_reflectance(BAND_TRACE), 40.0, places=9
        )

    def test_a_band_above_the_floor_is_strong_enough(self):
        self.assertTrue(band_is_strong_enough(BAND_TRACE, _policy()))

    def test_a_peak_exactly_on_the_floor_is_strong_enough(self):
        policy = _policy(min_usable_peak_percent=80.0)
        self.assertTrue(band_is_strong_enough(BAND_TRACE, policy))

    def test_a_weak_band_is_not_strong_enough(self):
        self.assertFalse(band_is_strong_enough(WEAK_TRACE, _policy()))


class CutOnTests(unittest.TestCase):
    def test_the_cut_on_sits_on_the_rising_half_level_crossing(self):
        self.assertAlmostEqual(cut_on_wavelength(BAND_TRACE), 350.0, places=9)

    def test_the_cut_on_is_resolvable_inside_the_scan(self):
        self.assertTrue(cut_on_is_resolvable(BAND_TRACE))

    def test_a_scan_starting_inside_the_band_cannot_resolve_the_cut_on(self):
        self.assertFalse(cut_on_is_resolvable(TRUNCATED_TRACE))

    def test_an_unresolvable_cut_on_raises(self):
        with self.assertRaises(ValueError):
            cut_on_wavelength(TRUNCATED_TRACE)

    def test_a_shallower_rising_edge_moves_the_cut_on(self):
        trace = [
            (300.0, 0.0),
            (340.0, 20.0),
            (360.0, 60.0),
            (600.0, 80.0),
            (920.0, 0.0),
        ]
        self.assertAlmostEqual(cut_on_wavelength(trace), 350.0, places=9)

    def test_a_deeper_band_moves_the_half_level_and_the_cut_on(self):
        trace = [
            (300.0, 0.0),
            (340.0, 0.0),
            (360.0, 40.0),
            (600.0, 40.0),
            (920.0, 0.0),
        ]
        self.assertAlmostEqual(cut_on_wavelength(trace), 350.0, places=9)


class DrawingTests(unittest.TestCase):
    def test_the_drawing_figure_and_tolerance_are_read_back(self):
        nominal, tolerance = drawing_cut_on({"cut_on_nm": 350.0, "tolerance_nm": 8.0})
        self.assertAlmostEqual(nominal, 350.0, places=9)
        self.assertAlmostEqual(tolerance, 8.0, places=9)

    def test_a_drawing_without_a_tolerance_takes_the_policy_default(self):
        _, tolerance = drawing_cut_on({"cut_on_nm": 350.0})
        self.assertAlmostEqual(
            tolerance, float(DEFAULT_CUT_ON_POLICY["default_tolerance_nm"]), places=9
        )

    def test_a_drawing_without_a_cut_on_entry_raises(self):
        with self.assertRaises(ValueError):
            drawing_cut_on({"cut_off_nm": 1150.0})

    def test_a_non_mapping_drawing_rejected(self):
        with self.assertRaises(ValueError):
            drawing_cut_on([350.0])

    def test_the_tolerance_band_brackets_the_drawing_figure(self):
        lower, upper = tolerance_band_nm(350.0, 10.0)
        self.assertAlmostEqual(lower, 340.0, places=9)
        self.assertAlmostEqual(upper, 360.0, places=9)

    def test_the_deviation_is_signed_against_the_drawing(self):
        self.assertAlmostEqual(cut_on_deviation_nm(356.0, 350.0), 6.0, places=9)
        self.assertAlmostEqual(cut_on_deviation_nm(344.0, 350.0), -6.0, places=9)

    def test_a_cut_on_inside_the_tolerance_matches(self):
        self.assertTrue(cut_on_matches_drawing(356.0, 350.0, 10.0))

    def test_a_cut_on_exactly_on_the_tolerance_edge_matches(self):
        self.assertTrue(cut_on_matches_drawing(360.0, 350.0, 10.0))

    def test_a_cut_on_beyond_the_tolerance_does_not_match(self):
        self.assertFalse(cut_on_matches_drawing(372.0, 350.0, 10.0))


class RequirementAssessmentTests(unittest.TestCase):
    def test_a_coating_on_the_drawing_figure_conforms(self):
        result = assess_cut_on_requirement(_case())
        self.assertEqual(result["verdict"], CUT_ON_MATCHES_DRAWING)
        self.assertEqual(result["findings"], [])

    def test_the_measured_cut_on_is_reported(self):
        result = assess_cut_on_requirement(_case())
        self.assertAlmostEqual(result["measured_cut_on_nm"], 350.0, places=9)
        self.assertAlmostEqual(result["deviation_nm"], 0.0, places=9)

    def test_the_half_level_is_reported_alongside_the_peak(self):
        result = assess_cut_on_requirement(_case())
        self.assertAlmostEqual(result["absolute_peak_percent"], 80.0, places=9)
        self.assertAlmostEqual(result["half_level_percent"], 40.0, places=9)

    def test_a_drawing_with_no_cut_on_entry_is_its_own_verdict(self):
        result = assess_cut_on_requirement(_case(drawing={"cut_off_nm": 1150.0}))
        self.assertEqual(result["verdict"], DRAWING_CUT_ON_ENTRY_MISSING)
        self.assertIsNone(result["drawing_cut_on_nm"])

    def test_an_absent_drawing_block_is_not_a_cut_on_of_zero(self):
        result = assess_cut_on_requirement(_case(drawing=None))
        self.assertEqual(result["verdict"], DRAWING_CUT_ON_ENTRY_MISSING)

    def test_a_missing_drawing_key_rejected(self):
        case = _case()
        del case["drawing"]
        with self.assertRaises(ValueError):
            assess_cut_on_requirement(case)

    def test_an_unmeasured_lot_is_not_a_lot_at_the_nominal(self):
        result = assess_cut_on_requirement(_case(measurement=None))
        self.assertEqual(result["verdict"], CUT_ON_NOT_MEASURED)
        self.assertIsNone(result["measured_cut_on_nm"])

    def test_a_measurement_block_without_a_trace_is_not_a_measurement(self):
        result = assess_cut_on_requirement(_case(measurement={"operator": "lab-a"}))
        self.assertEqual(result["verdict"], CUT_ON_NOT_MEASURED)

    def test_the_drawing_window_survives_an_unmeasured_lot(self):
        result = assess_cut_on_requirement(_case(measurement=None))
        self.assertEqual(result["tolerance_band_nm"], (340.0, 360.0))

    def test_a_weak_band_cannot_carry_a_half_level(self):
        result = assess_cut_on_requirement(
            _case(measurement={"trace": list(WEAK_TRACE)})
        )
        self.assertEqual(result["verdict"], REFLECTANCE_BAND_TOO_WEAK)

    def test_a_truncated_scan_leaves_the_cut_on_unresolved(self):
        result = assess_cut_on_requirement(
            _case(measurement={"trace": list(TRUNCATED_TRACE)})
        )
        self.assertEqual(result["verdict"], CUT_ON_NOT_RESOLVED)

    def test_a_normalised_half_level_is_not_the_clause_basis(self):
        result = assess_cut_on_requirement(
            _case(
                measurement={
                    "half_level_basis": "normalised-to-reference-reflectance",
                    "trace": list(BAND_TRACE),
                }
            )
        )
        self.assertEqual(result["verdict"], HALF_LEVEL_BASIS_MISAPPLIED)

    def test_an_unknown_half_level_basis_rejected(self):
        with self.assertRaises(ValueError):
            assess_cut_on_requirement(
                _case(measurement={"half_level_basis": "eyeball", "trace": []})
            )

    def test_a_coating_off_the_drawing_figure_fails_the_requirement(self):
        result = assess_cut_on_requirement(
            _case(drawing={"cut_on_nm": 320.0, "tolerance_nm": 10.0})
        )
        self.assertEqual(result["verdict"], CUT_ON_OUTSIDE_DRAWING_TOLERANCE)
        self.assertAlmostEqual(result["deviation_nm"], 30.0, places=9)

    def test_a_cut_on_exactly_on_the_tolerance_edge_still_conforms(self):
        result = assess_cut_on_requirement(
            _case(drawing={"cut_on_nm": 340.0, "tolerance_nm": 10.0})
        )
        self.assertEqual(result["verdict"], CUT_ON_MATCHES_DRAWING)

    def test_a_tighter_drawing_tolerance_turns_the_same_lot_around(self):
        loose = assess_cut_on_requirement(
            _case(drawing={"cut_on_nm": 344.0, "tolerance_nm": 10.0})
        )
        tight = assess_cut_on_requirement(
            _case(drawing={"cut_on_nm": 344.0, "tolerance_nm": 2.0})
        )
        self.assertEqual(loose["verdict"], CUT_ON_MATCHES_DRAWING)
        self.assertEqual(tight["verdict"], CUT_ON_OUTSIDE_DRAWING_TOLERANCE)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_cut_on_requirement(["drawing"])

    def test_a_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_cut_on_requirement(_case(measurement=[BAND_TRACE]))


if __name__ == "__main__":
    unittest.main()
