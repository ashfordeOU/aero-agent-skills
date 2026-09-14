"""Contract tests for the clause 8.7.2 coverglass transmission-into-air reduction."""

import unittest

from e2008_coverglass_transmission_into_air_logic import (
    AVERAGE_BELOW_REQUIREMENT,
    AVERAGE_MEETS_REQUIREMENT,
    BAND_NOT_COVERED,
    BASELINE_NOT_REFERENCED,
    DEFAULT_SCAN_POLICY,
    SAMPLING_TOO_COARSE,
    assess_transmission_into_air,
    band_average_transmittance,
    covers_band,
    cut_on_wavelength_nm,
    interpolate_transmittance,
    max_sample_interval_nm,
    meets_requirement,
    scan_span_nm,
    validate_scan,
    validate_scan_policy,
    validate_weighting,
    weighted_band_average_transmittance,
)

BAND_START = 350.0
BAND_END = 1800.0


def _policy(**overrides):
    policy = dict(DEFAULT_SCAN_POLICY)
    policy.update(overrides)
    return policy


def _flat_scan(value=0.94, step=10.0):
    points = []
    wavelength = BAND_START
    while wavelength <= BAND_END + 1e-9:
        points.append((wavelength, value))
        wavelength += step
    return points


def _ramp_scan():
    """Rises linearly from 0.10 at 350 nm to 0.98 at 1800 nm."""
    points = []
    wavelength = BAND_START
    while wavelength <= BAND_END + 1e-9:
        fraction = (wavelength - BAND_START) / (BAND_END - BAND_START)
        points.append((wavelength, 0.10 + 0.88 * fraction))
        wavelength += 10.0
    return points


def _flat_weighting(value=1.0):
    return [(BAND_START, value), (BAND_END, value)]


def _case(**overrides):
    case = {
        "scan": _flat_scan(),
        "baseline_reference": "SPEC-CAL-2026-031",
        "required_minimum_transmittance": 0.90,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_scan_policy(DEFAULT_SCAN_POLICY), DEFAULT_SCAN_POLICY)

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan_policy("350-1800")

    def test_an_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan_policy(_policy(band_start_nm=1800.0, band_end_nm=350.0))

    def test_an_interval_wider_than_the_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan_policy(_policy(max_sample_interval_nm=5000.0))

    def test_a_cut_on_threshold_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan_policy(_policy(cut_on_transmittance=1.0))


class ScanValidationTests(unittest.TestCase):
    def test_a_well_formed_scan_validates(self):
        points = validate_scan(_flat_scan())
        self.assertEqual(len(points), 146)

    def test_mapping_points_are_accepted(self):
        points = validate_scan(
            [
                {"wavelength_nm": 400.0, "transmittance": 0.9},
                {"wavelength_nm": 500.0, "transmittance": 0.92},
            ]
        )
        self.assertAlmostEqual(points[1][1], 0.92, places=12)

    def test_a_single_point_scan_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan([(400.0, 0.9)])

    def test_a_descending_scan_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan([(500.0, 0.9), (400.0, 0.9)])

    def test_a_repeated_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan([(400.0, 0.9), (400.0, 0.91)])

    def test_a_transmittance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan([(400.0, 1.4), (500.0, 0.9)])

    def test_a_negative_transmittance_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan([(400.0, -0.1), (500.0, 0.9)])

    def test_a_malformed_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan([(400.0, 0.9, 3), (500.0, 0.9)])

    def test_the_scan_span_is_its_first_and_last_wavelength(self):
        first, last = scan_span_nm(_flat_scan())
        self.assertAlmostEqual(first, BAND_START, places=9)
        self.assertAlmostEqual(last, BAND_END, places=9)


class CoverageTests(unittest.TestCase):
    def test_a_scan_reaching_both_edges_covers_the_band(self):
        self.assertTrue(covers_band(_flat_scan(), BAND_START, BAND_END))

    def test_a_scan_stopping_short_does_not_cover_the_band(self):
        short = [(400.0, 0.9), (1500.0, 0.95)]
        self.assertFalse(covers_band(short, BAND_START, BAND_END))

    def test_a_scan_landing_exactly_on_the_edges_covers_the_band(self):
        exact = [(BAND_START, 0.9), (BAND_END, 0.95)]
        self.assertTrue(covers_band(exact, BAND_START, BAND_END))

    def test_an_inverted_band_rejected_by_the_coverage_check(self):
        with self.assertRaises(ValueError):
            covers_band(_flat_scan(), BAND_END, BAND_START)

    def test_the_widest_sample_gap_is_reported(self):
        scan = [(BAND_START, 0.9), (500.0, 0.9), (BAND_END, 0.95)]
        self.assertAlmostEqual(max_sample_interval_nm(scan), 1300.0, places=9)


class InterpolationTests(unittest.TestCase):
    def test_a_midpoint_interpolates_linearly(self):
        scan = [(400.0, 0.20), (600.0, 0.80)]
        self.assertAlmostEqual(
            interpolate_transmittance(scan, 500.0), 0.50, places=12
        )

    def test_a_sample_wavelength_returns_its_own_value(self):
        scan = [(400.0, 0.20), (600.0, 0.80)]
        self.assertAlmostEqual(
            interpolate_transmittance(scan, 600.0), 0.80, places=12
        )

    def test_a_wavelength_outside_the_scan_rejected(self):
        scan = [(400.0, 0.20), (600.0, 0.80)]
        with self.assertRaises(ValueError):
            interpolate_transmittance(scan, 900.0)


class BandAverageTests(unittest.TestCase):
    def test_a_flat_scan_averages_to_its_own_level(self):
        self.assertAlmostEqual(
            band_average_transmittance(_flat_scan(0.94), BAND_START, BAND_END),
            0.94,
            places=12,
        )

    def test_a_linear_ramp_averages_to_its_midpoint(self):
        self.assertAlmostEqual(
            band_average_transmittance(_ramp_scan(), BAND_START, BAND_END),
            0.54,
            places=9,
        )

    def test_a_dense_region_does_not_carry_the_average(self):
        """Ordinate averaging would report far above the true half."""
        scan = [(BAND_START, 1.0)]
        wavelength = BAND_START + 1.0
        while wavelength <= 400.0:
            scan.append((wavelength, 1.0))
            wavelength += 1.0
        scan.append((400.0 + 1e-6, 0.0))
        scan.append((BAND_END, 0.0))
        ordinate_mean = sum(t for _w, t in scan) / len(scan)
        integral_mean = band_average_transmittance(scan, BAND_START, BAND_END)
        self.assertAlmostEqual(integral_mean, 50.0 / 1450.0, places=6)
        self.assertGreater(ordinate_mean, 0.9)

    def test_a_band_wider_than_the_scan_rejected(self):
        with self.assertRaises(ValueError):
            band_average_transmittance(_flat_scan(), 300.0, BAND_END)

    def test_a_sub_band_average_uses_interpolated_edges(self):
        scan = [(400.0, 0.0), (600.0, 1.0)]
        self.assertAlmostEqual(
            band_average_transmittance(scan, 450.0, 550.0), 0.50, places=12
        )


class WeightingTests(unittest.TestCase):
    def test_a_flat_weighting_reproduces_the_unweighted_average(self):
        scan = _ramp_scan()
        self.assertAlmostEqual(
            weighted_band_average_transmittance(
                scan, _flat_weighting(), BAND_START, BAND_END
            ),
            band_average_transmittance(scan, BAND_START, BAND_END),
            places=9,
        )

    def test_a_weighting_biased_to_the_red_end_raises_a_rising_average(self):
        scan = _ramp_scan()
        red = [(BAND_START, 0.0), (BAND_END, 1.0)]
        weighted = weighted_band_average_transmittance(
            scan, red, BAND_START, BAND_END
        )
        plain = band_average_transmittance(scan, BAND_START, BAND_END)
        self.assertGreater(weighted - plain, 1e-3)

    def test_an_all_zero_weighting_rejected(self):
        with self.assertRaises(ValueError):
            validate_weighting([(BAND_START, 0.0), (BAND_END, 0.0)])

    def test_a_negative_weighting_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_weighting([(BAND_START, -1.0), (BAND_END, 1.0)])

    def test_a_weighting_short_of_the_band_rejected(self):
        with self.assertRaises(ValueError):
            weighted_band_average_transmittance(
                _flat_scan(), [(500.0, 1.0), (900.0, 1.0)], BAND_START, BAND_END
            )

    def test_a_descending_weighting_rejected(self):
        with self.assertRaises(ValueError):
            validate_weighting([(BAND_END, 1.0), (BAND_START, 1.0)])


class CutOnTests(unittest.TestCase):
    def test_the_cut_on_is_interpolated_between_samples(self):
        scan = [(300.0, 0.0), (400.0, 1.0), (500.0, 1.0)]
        self.assertAlmostEqual(cut_on_wavelength_nm(scan, 0.5), 350.0, places=9)

    def test_a_scan_that_never_rises_has_no_cut_on(self):
        self.assertIsNone(cut_on_wavelength_nm([(300.0, 0.0), (900.0, 0.1)], 0.5))

    def test_a_scan_starting_above_the_threshold_rejected(self):
        with self.assertRaises(ValueError):
            cut_on_wavelength_nm([(300.0, 0.9), (900.0, 0.95)], 0.5)

    def test_a_threshold_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            cut_on_wavelength_nm([(300.0, 0.0), (900.0, 0.9)], 1.5)


class RequirementTests(unittest.TestCase):
    def test_an_average_above_the_requirement_meets_it(self):
        self.assertTrue(meets_requirement(0.94, 0.90))

    def test_an_average_exactly_on_the_requirement_meets_it(self):
        self.assertAlmostEqual(0.90, 0.90, places=12)
        self.assertTrue(meets_requirement(0.90, 0.90))

    def test_an_average_below_the_requirement_does_not_meet_it(self):
        self.assertFalse(meets_requirement(0.88, 0.90))

    def test_a_requirement_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            meets_requirement(0.94, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_a_good_scan_meets_the_requirement(self):
        result = assess_transmission_into_air(_case())
        self.assertEqual(result["verdict"], AVERAGE_MEETS_REQUIREMENT)
        self.assertEqual(result["findings"], [])

    def test_the_band_average_and_margin_are_reported(self):
        result = assess_transmission_into_air(_case())
        self.assertAlmostEqual(
            result["band_average_transmittance"], 0.94, places=12
        )
        self.assertAlmostEqual(result["margin"], 0.04, places=9)

    def test_a_missing_baseline_reference_stops_the_reduction(self):
        result = assess_transmission_into_air(_case(baseline_reference=""))
        self.assertEqual(result["verdict"], BASELINE_NOT_REFERENCED)
        self.assertIsNone(result["band_average_transmittance"])

    def test_a_scan_short_of_the_band_stops_the_reduction(self):
        result = assess_transmission_into_air(
            _case(scan=[(500.0, 0.94), (1500.0, 0.94)])
        )
        self.assertEqual(result["verdict"], BAND_NOT_COVERED)
        self.assertIsNone(result["band_average_transmittance"])

    def test_a_coarse_scan_stops_the_reduction(self):
        result = assess_transmission_into_air(
            _case(scan=[(BAND_START, 0.94), (BAND_END, 0.94)])
        )
        self.assertEqual(result["verdict"], SAMPLING_TOO_COARSE)
        self.assertAlmostEqual(
            result["max_sample_interval_nm"], 1450.0, places=9
        )

    def test_a_sample_gap_exactly_on_the_interval_is_not_too_coarse(self):
        result = assess_transmission_into_air(_case(scan=_flat_scan(0.94, 10.0)))
        self.assertAlmostEqual(result["max_sample_interval_nm"], 10.0, places=9)
        self.assertEqual(result["verdict"], AVERAGE_MEETS_REQUIREMENT)

    def test_a_short_average_fails_against_the_requirement(self):
        result = assess_transmission_into_air(
            _case(scan=_flat_scan(0.85), required_minimum_transmittance=0.90)
        )
        self.assertEqual(result["verdict"], AVERAGE_BELOW_REQUIREMENT)
        self.assertEqual(len(result["findings"]), 1)

    def test_the_weighted_average_is_reported_when_a_weighting_is_given(self):
        result = assess_transmission_into_air(
            _case(spectral_irradiance_weighting=_flat_weighting())
        )
        self.assertAlmostEqual(
            result["weighted_band_average_transmittance"], 0.94, places=9
        )

    def test_no_weighted_average_is_invented_without_a_weighting(self):
        result = assess_transmission_into_air(_case())
        self.assertIsNone(result["weighted_band_average_transmittance"])

    def test_a_flat_scan_above_the_cut_on_raises_an_advisory(self):
        result = assess_transmission_into_air(_case())
        self.assertIsNone(result["cut_on_wavelength_nm"])
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_cut_on_is_reported_for_a_scan_that_rises_through_it(self):
        result = assess_transmission_into_air(
            _case(scan=_ramp_scan(), required_minimum_transmittance=0.50)
        )
        self.assertIsNotNone(result["cut_on_wavelength_nm"])
        self.assertAlmostEqual(
            result["cut_on_wavelength_nm"],
            BAND_START + (0.40 / 0.88) * (BAND_END - BAND_START),
            places=6,
        )

    def test_no_declared_minimum_reports_the_average_with_an_advisory(self):
        case = _case()
        del case["required_minimum_transmittance"]
        result = assess_transmission_into_air(case)
        self.assertIsNone(result["required_minimum"])
        self.assertTrue(result["advisories"])

    def test_the_baseline_reference_travels_with_the_verdict(self):
        result = assess_transmission_into_air(_case())
        self.assertEqual(result["baseline_reference"], "SPEC-CAL-2026-031")

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_transmission_into_air(["scan"])

    def test_a_missing_scan_rejected(self):
        case = _case()
        del case["scan"]
        with self.assertRaises(ValueError):
            assess_transmission_into_air(case)


if __name__ == "__main__":
    unittest.main()
