"""Contract tests for the clause 8.7.5.3.1 cut-off definition logic."""

import unittest

from e2008_reflectance_cut_off_definition_logic import (
    ABSOLUTE_HALF_LEVEL_BASIS,
    CUT_OFF_BEYOND_SCAN_RANGE,
    CUT_OFF_DETERMINED,
    DEFAULT_CUT_OFF_POLICY,
    HALF_LEVEL_BASIS_MISAPPLIED,
    REFLECTANCE_BAND_TOO_WEAK,
    absolute_peak_reflectance,
    band_is_strong_enough,
    band_width_nm,
    cut_off_is_resolvable,
    cut_off_wavelength,
    cut_on_wavelength,
    determine_cut_off,
    half_level_from_reference,
    half_of_absolute_reflectance,
    scan_upper_limit_nm,
    validate_cut_off_policy,
    validate_reflectance_trace,
)

# A red reflector band peaking at 80 percent. The half level is 40 percent.
# The falling edge crosses it midway between 1100 and 1140 nm, at 1120 nm;
# the rising edge crosses it midway between 340 and 360 nm, at 350 nm.
BAND_TRACE = [
    (300.0, 0.0),
    (340.0, 0.0),
    (360.0, 80.0),
    (700.0, 80.0),
    (1100.0, 80.0),
    (1140.0, 0.0),
    (1200.0, 0.0),
]

# The same band on a coating that only reaches 8 percent: a half level of
# 4 percent describes instrument noise, not a reflectance band.
WEAK_TRACE = [
    (300.0, 0.0),
    (340.0, 0.0),
    (360.0, 8.0),
    (700.0, 8.0),
    (1100.0, 8.0),
    (1140.0, 0.0),
    (1200.0, 0.0),
]

# A scan stopped at 1000 nm while the band is still flat: the cut-off is
# somewhere past the end of the scan, which is not a measured cut-off.
SHORT_SCAN_TRACE = [
    (300.0, 0.0),
    (340.0, 0.0),
    (360.0, 80.0),
    (700.0, 80.0),
    (1000.0, 80.0),
]

# A scan that opens already inside the band: the cut-off is measurable,
# the cut-on is not, so no band width can be stated.
NO_RISING_EDGE_TRACE = [
    (400.0, 80.0),
    (700.0, 80.0),
    (1100.0, 80.0),
    (1140.0, 0.0),
    (1200.0, 0.0),
]


def _policy(**overrides):
    policy = dict(DEFAULT_CUT_OFF_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "half_level_basis": ABSOLUTE_HALF_LEVEL_BASIS,
        "trace": list(BAND_TRACE),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_cut_off_policy(DEFAULT_CUT_OFF_POLICY), DEFAULT_CUT_OFF_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_off_policy("half")

    def test_peak_floor_above_the_reflectance_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_off_policy(_policy(min_usable_peak_percent=160.0))

    def test_a_fraction_at_or_above_the_whole_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_off_policy(_policy(half_level_fraction=1.0))

    def test_a_zero_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_off_policy(_policy(half_level_fraction=0.0))

    def test_scan_point_floor_below_three_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_off_policy(_policy(min_scan_points=2))


class TraceTests(unittest.TestCase):
    def test_a_well_formed_trace_is_returned_ordered(self):
        points = validate_reflectance_trace(BAND_TRACE)
        self.assertEqual(len(points), len(BAND_TRACE))
        self.assertAlmostEqual(points[-1][0], 1200.0, places=9)

    def test_a_non_sequence_trace_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_trace(1120.0)

    def test_a_malformed_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_trace(
                [(300.0,), (340.0, 0.0), (360.0, 80.0), (1100.0, 80.0),
                 (1140.0, 0.0)]
            )

    def test_a_decreasing_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_trace(
                [(360.0, 80.0), (340.0, 0.0), (700.0, 80.0), (1100.0, 80.0),
                 (1140.0, 0.0)]
            )

    def test_a_reflectance_above_the_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_trace(
                [(300.0, 0.0), (340.0, 0.0), (360.0, 101.5), (1100.0, 80.0),
                 (1140.0, 0.0)]
            )

    def test_a_boolean_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_trace(
                [(True, 0.0), (340.0, 0.0), (360.0, 80.0), (1100.0, 80.0),
                 (1140.0, 0.0)]
            )

    def test_a_trace_shorter_than_the_policy_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_trace([(300.0, 0.0), (1140.0, 0.0)])

    def test_the_scan_upper_limit_is_the_longest_wavelength(self):
        self.assertAlmostEqual(scan_upper_limit_nm(BAND_TRACE), 1200.0, places=9)


class HalfLevelTests(unittest.TestCase):
    def test_the_peak_is_the_absolute_measured_maximum(self):
        self.assertAlmostEqual(absolute_peak_reflectance(BAND_TRACE), 80.0, places=9)

    def test_the_half_level_is_half_of_that_absolute_peak(self):
        self.assertAlmostEqual(
            half_of_absolute_reflectance(BAND_TRACE), 40.0, places=9
        )

    def test_a_weaker_band_puts_its_half_level_lower(self):
        self.assertAlmostEqual(half_of_absolute_reflectance(WEAK_TRACE), 4.0, places=9)

    def test_a_normalised_basis_gives_a_different_level(self):
        self.assertAlmostEqual(half_level_from_reference(100.0), 50.0, places=9)

    def test_the_normalised_level_differs_from_the_absolute_one(self):
        absolute = half_of_absolute_reflectance(BAND_TRACE)
        normalised = half_level_from_reference(100.0)
        self.assertAlmostEqual(normalised - absolute, 10.0, places=9)

    def test_a_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            half_level_from_reference(0.0)

    def test_a_band_above_the_floor_is_strong_enough(self):
        self.assertTrue(band_is_strong_enough(BAND_TRACE, _policy()))

    def test_a_peak_exactly_on_the_floor_is_strong_enough(self):
        self.assertTrue(
            band_is_strong_enough(BAND_TRACE, _policy(min_usable_peak_percent=80.0))
        )

    def test_a_weak_band_is_not_strong_enough(self):
        self.assertFalse(band_is_strong_enough(WEAK_TRACE, _policy()))


class CutOffTests(unittest.TestCase):
    def test_the_cut_off_sits_on_the_falling_half_level_crossing(self):
        self.assertAlmostEqual(cut_off_wavelength(BAND_TRACE), 1120.0, places=9)

    def test_the_cut_off_is_the_long_wavelength_edge_not_the_short_one(self):
        self.assertGreater(
            cut_off_wavelength(BAND_TRACE), cut_on_wavelength(BAND_TRACE)
        )

    def test_the_cut_on_partner_sits_on_the_rising_crossing(self):
        self.assertAlmostEqual(cut_on_wavelength(BAND_TRACE), 350.0, places=9)

    def test_the_band_width_spans_the_two_half_level_edges(self):
        self.assertAlmostEqual(band_width_nm(BAND_TRACE), 770.0, places=9)

    def test_a_resolvable_cut_off_is_reported_resolvable(self):
        self.assertTrue(cut_off_is_resolvable(BAND_TRACE))

    def test_a_scan_stopping_inside_the_band_cannot_resolve_the_cut_off(self):
        self.assertFalse(cut_off_is_resolvable(SHORT_SCAN_TRACE))

    def test_an_unresolvable_cut_off_raises(self):
        with self.assertRaises(ValueError):
            cut_off_wavelength(SHORT_SCAN_TRACE)

    def test_a_scan_opening_inside_the_band_has_no_cut_on(self):
        with self.assertRaises(ValueError):
            cut_on_wavelength(NO_RISING_EDGE_TRACE)

    def test_a_sloped_falling_edge_is_interpolated_not_snapped(self):
        trace = [
            (300.0, 0.0),
            (360.0, 80.0),
            (1100.0, 60.0),
            (1140.0, 20.0),
            (1200.0, 0.0),
        ]
        self.assertAlmostEqual(cut_off_wavelength(trace), 1120.0, places=9)

    def test_a_lower_peak_moves_the_half_level_and_the_cut_off(self):
        trace = [
            (300.0, 0.0),
            (340.0, 0.0),
            (360.0, 40.0),
            (1100.0, 40.0),
            (1140.0, 0.0),
        ]
        self.assertAlmostEqual(cut_off_wavelength(trace), 1120.0, places=9)
        self.assertAlmostEqual(half_of_absolute_reflectance(trace), 20.0, places=9)


class DeterminationTests(unittest.TestCase):
    def test_a_measured_band_yields_a_cut_off(self):
        result = determine_cut_off(_case())
        self.assertEqual(result["verdict"], CUT_OFF_DETERMINED)
        self.assertAlmostEqual(result["cut_off_nm"], 1120.0, places=9)

    def test_the_half_level_and_peak_are_reported(self):
        result = determine_cut_off(_case())
        self.assertAlmostEqual(result["absolute_peak_percent"], 80.0, places=9)
        self.assertAlmostEqual(result["half_level_percent"], 40.0, places=9)

    def test_the_band_width_accompanies_a_two_edge_scan(self):
        result = determine_cut_off(_case())
        self.assertAlmostEqual(result["band_width_nm"], 770.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_a_normalised_basis_is_not_this_definition(self):
        result = determine_cut_off(
            _case(half_level_basis="normalised-to-reference-reflectance")
        )
        self.assertEqual(result["verdict"], HALF_LEVEL_BASIS_MISAPPLIED)
        self.assertIsNone(result["cut_off_nm"])

    def test_a_fixed_nominal_basis_is_not_this_definition_either(self):
        result = determine_cut_off(_case(half_level_basis="fixed-nominal-percent"))
        self.assertEqual(result["verdict"], HALF_LEVEL_BASIS_MISAPPLIED)

    def test_an_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            determine_cut_off(_case(half_level_basis="eyeball"))

    def test_a_weak_band_carries_no_meaningful_half_level(self):
        result = determine_cut_off(_case(trace=list(WEAK_TRACE)))
        self.assertEqual(result["verdict"], REFLECTANCE_BAND_TOO_WEAK)

    def test_a_short_scan_places_the_cut_off_past_its_end(self):
        result = determine_cut_off(_case(trace=list(SHORT_SCAN_TRACE)))
        self.assertEqual(result["verdict"], CUT_OFF_BEYOND_SCAN_RANGE)
        self.assertAlmostEqual(result["scan_upper_limit_nm"], 1000.0, places=9)

    def test_a_cut_off_without_a_cut_on_still_determines_the_cut_off(self):
        result = determine_cut_off(_case(trace=list(NO_RISING_EDGE_TRACE)))
        self.assertEqual(result["verdict"], CUT_OFF_DETERMINED)
        self.assertIsNone(result["band_width_nm"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_missing_trace_key_rejected(self):
        case = _case()
        del case["trace"]
        with self.assertRaises(ValueError):
            determine_cut_off(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            determine_cut_off([BAND_TRACE])

    def test_the_default_basis_is_the_absolute_one(self):
        case = _case()
        del case["half_level_basis"]
        result = determine_cut_off(case)
        self.assertEqual(result["half_level_basis"], ABSOLUTE_HALF_LEVEL_BASIS)
        self.assertEqual(result["verdict"], CUT_OFF_DETERMINED)


if __name__ == "__main__":
    unittest.main()
