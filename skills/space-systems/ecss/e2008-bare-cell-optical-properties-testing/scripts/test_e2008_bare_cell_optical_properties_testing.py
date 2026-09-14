"""Contract tests for the clause 7.5.6 bare cell optical property logic."""

import unittest

from e2008_bare_cell_optical_properties_testing_logic import (
    COVERGLASS_GAIN_NOT_MEASURED,
    DEFAULT_OPTICAL_POLICY,
    OPTICAL_PERFORMANCE_ACCEPTED,
    OPTICAL_PERFORMANCE_DEFICIENT,
    SCAN_INADEQUATE,
    assess_bare_cell_optical_properties,
    band_averaged_reflectance,
    coverglass_gain,
    coverglass_gain_percent,
    effective_absorptance,
    max_sample_gap_nm,
    normalise_reflectance_scan,
    scan_band_span_nm,
    scan_covers_band,
    validate_optical_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_OPTICAL_POLICY)
    policy.update(overrides)
    return policy


def _scan(reflectance=0.08, start=400.0, end=1800.0, step=50.0):
    samples = []
    wavelength = start
    while wavelength < end:
        samples.append((wavelength, reflectance))
        wavelength += step
    samples.append((end, reflectance))
    return samples


def _case(**overrides):
    case = {
        "reflectance_scan": _scan(),
        "coverglass": {
            "bare_short_circuit_a": 0.500,
            "covered_short_circuit_a": 0.505,
        },
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_optical_policy(DEFAULT_OPTICAL_POLICY), DEFAULT_OPTICAL_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_optical_policy("band")

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_optical_policy(_policy(band_start_nm=1800.0, band_end_nm=400.0))

    def test_reflectance_ceiling_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_optical_policy(_policy(max_band_reflectance=1.4))

    def test_fractional_minimum_point_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_optical_policy(_policy(min_scan_points=8.5))


class ScanTests(unittest.TestCase):
    def test_samples_are_ordered_by_wavelength(self):
        ordered = normalise_reflectance_scan(
            [(900.0, 0.05), (400.0, 0.09), (1800.0, 0.07)]
        )
        self.assertEqual([point[0] for point in ordered], [400.0, 900.0, 1800.0])

    def test_span_reports_the_first_and_last_wavelength(self):
        self.assertEqual(scan_band_span_nm(_scan()), (400.0, 1800.0))

    def test_widest_step_is_reported(self):
        scan = [(400.0, 0.08), (450.0, 0.08), (700.0, 0.08)]
        self.assertAlmostEqual(_ratio(max_sample_gap_nm(scan), 250.0), 1.0, places=12)

    def test_a_scan_reaching_both_edges_covers_the_band(self):
        self.assertTrue(scan_covers_band(_scan(), _policy()))

    def test_a_scan_stopping_short_does_not_cover_the_band(self):
        self.assertFalse(scan_covers_band(_scan(end=1200.0), _policy()))

    def test_a_scan_landing_exactly_on_both_edges_covers_the_band(self):
        policy = _policy()
        span = scan_band_span_nm(_scan())
        self.assertAlmostEqual(span[0], policy["band_start_nm"], places=9)
        self.assertAlmostEqual(span[1], policy["band_end_nm"], places=9)
        self.assertTrue(scan_covers_band(_scan(), policy))

    def test_percentage_reflectance_rejected_as_a_unit_error(self):
        with self.assertRaises(ValueError):
            normalise_reflectance_scan([(400.0, 8.0), (1800.0, 7.0)])

    def test_negative_reflectance_rejected(self):
        with self.assertRaises(ValueError):
            normalise_reflectance_scan([(400.0, -0.01), (1800.0, 0.07)])

    def test_repeated_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            normalise_reflectance_scan([(400.0, 0.08), (400.0, 0.07)])

    def test_single_sample_scan_rejected(self):
        with self.assertRaises(ValueError):
            normalise_reflectance_scan([(400.0, 0.08)])

    def test_malformed_sample_rejected(self):
        with self.assertRaises(ValueError):
            normalise_reflectance_scan([(400.0, 0.08), (1800.0,)])


class AverageTests(unittest.TestCase):
    def test_a_flat_scan_averages_to_its_own_value(self):
        self.assertAlmostEqual(
            _ratio(band_averaged_reflectance(_scan(reflectance=0.08)), 0.08),
            1.0,
            places=12,
        )

    def test_a_linear_ramp_averages_to_its_midpoint(self):
        scan = [(400.0, 0.00), (1800.0, 0.20)]
        self.assertAlmostEqual(
            _ratio(band_averaged_reflectance(scan), 0.10), 1.0, places=12
        )

    def test_weighting_pulls_the_average_toward_the_bright_end(self):
        scan = [(400.0, 0.30), (900.0, 0.10), (1800.0, 0.10)]
        unweighted = band_averaged_reflectance(scan)
        weighted = band_averaged_reflectance(scan, [0.01, 1.0, 1.0])
        self.assertLess(weighted, unweighted)

    def test_weight_count_must_match_the_sample_count(self):
        with self.assertRaises(ValueError):
            band_averaged_reflectance(_scan(), [1.0, 1.0])

    def test_zero_spectral_weight_rejected(self):
        scan = [(400.0, 0.08), (900.0, 0.08), (1800.0, 0.08)]
        with self.assertRaises(ValueError):
            band_averaged_reflectance(scan, [1.0, 0.0, 1.0])

    def test_absorptance_is_the_complement_of_reflectance(self):
        self.assertAlmostEqual(_ratio(effective_absorptance(0.08), 0.92), 1.0,
                               places=12)

    def test_absorptance_of_an_out_of_range_reflectance_rejected(self):
        with self.assertRaises(ValueError):
            effective_absorptance(1.5)


class CoverglassGainTests(unittest.TestCase):
    def test_gain_is_the_covered_over_bare_current_ratio(self):
        self.assertAlmostEqual(_ratio(coverglass_gain(0.500, 0.505), 1.01), 1.0,
                               places=12)

    def test_an_equal_current_is_unity_gain(self):
        self.assertAlmostEqual(coverglass_gain(0.500, 0.500), 1.0, places=9)

    def test_a_clouded_glass_gives_a_gain_below_one(self):
        self.assertLess(coverglass_gain(0.500, 0.470), 1.0)

    def test_gain_percent_is_the_signed_change(self):
        self.assertAlmostEqual(coverglass_gain_percent(1.01), 1.0, places=9)

    def test_zero_bare_current_rejected(self):
        with self.assertRaises(ValueError):
            coverglass_gain(0.0, 0.505)

    def test_boolean_current_rejected(self):
        with self.assertRaises(ValueError):
            coverglass_gain(True, 0.505)


class AssessmentTests(unittest.TestCase):
    def test_a_clean_measurement_is_accepted(self):
        result = assess_bare_cell_optical_properties(_case())
        self.assertEqual(result["verdict"], OPTICAL_PERFORMANCE_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_the_band_average_and_absorptance_are_reported(self):
        result = assess_bare_cell_optical_properties(_case())
        self.assertAlmostEqual(
            _ratio(result["band_averaged_reflectance"], 0.08), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(result["effective_absorptance"], 0.92), 1.0, places=12
        )

    def test_a_reflectance_exactly_on_the_ceiling_is_accepted(self):
        policy = _policy(max_band_reflectance=0.08)
        result = assess_bare_cell_optical_properties(_case(), policy)
        self.assertAlmostEqual(
            _ratio(result["band_averaged_reflectance"],
                   policy["max_band_reflectance"]),
            1.0,
            places=12,
        )
        self.assertEqual(result["verdict"], OPTICAL_PERFORMANCE_ACCEPTED)

    def test_a_reflectance_above_the_ceiling_is_deficient(self):
        result = assess_bare_cell_optical_properties(
            _case(reflectance_scan=_scan(reflectance=0.22))
        )
        self.assertEqual(result["verdict"], OPTICAL_PERFORMANCE_DEFICIENT)

    def test_a_short_scan_stops_the_judgement(self):
        result = assess_bare_cell_optical_properties(
            _case(reflectance_scan=_scan(end=1200.0))
        )
        self.assertEqual(result["verdict"], SCAN_INADEQUATE)
        self.assertIsNone(result["coverglass_gain"])

    def test_a_coarse_scan_stops_the_judgement(self):
        result = assess_bare_cell_optical_properties(
            _case(reflectance_scan=_scan(step=200.0))
        )
        self.assertEqual(result["verdict"], SCAN_INADEQUATE)

    def test_every_scan_finding_is_reported_not_only_the_first(self):
        result = assess_bare_cell_optical_properties(
            _case(reflectance_scan=[(500.0, 0.08), (1200.0, 0.08)])
        )
        self.assertEqual(result["verdict"], SCAN_INADEQUATE)
        self.assertEqual(len(result["findings"]), 3)

    def test_a_missing_covered_measurement_is_its_own_verdict(self):
        case = _case()
        del case["coverglass"]
        result = assess_bare_cell_optical_properties(case)
        self.assertEqual(result["verdict"], COVERGLASS_GAIN_NOT_MEASURED)
        self.assertIsNone(result["coverglass_gain"])

    def test_a_lossy_coverglass_is_deficient(self):
        result = assess_bare_cell_optical_properties(
            _case(
                coverglass={
                    "bare_short_circuit_a": 0.500,
                    "covered_short_circuit_a": 0.450,
                }
            )
        )
        self.assertEqual(result["verdict"], OPTICAL_PERFORMANCE_DEFICIENT)
        self.assertLess(result["coverglass_gain_percent"], 0.0)

    def test_a_gain_exactly_on_the_floor_is_accepted(self):
        policy = _policy(min_coverglass_gain=1.01)
        result = assess_bare_cell_optical_properties(_case(), policy)
        self.assertAlmostEqual(
            _ratio(result["coverglass_gain"], policy["min_coverglass_gain"]),
            1.0,
            places=12,
        )
        self.assertEqual(result["verdict"], OPTICAL_PERFORMANCE_ACCEPTED)

    def test_supplying_weights_marks_the_average_solar_weighted(self):
        scan = _scan()
        case = _case(reflectance_scan=scan, spectral_weights=[1.0] * len(scan))
        result = assess_bare_cell_optical_properties(case)
        self.assertTrue(result["solar_weighted"])

    def test_absent_scan_key_rejected(self):
        case = _case()
        del case["reflectance_scan"]
        with self.assertRaises(ValueError):
            assess_bare_cell_optical_properties(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_optical_properties(["reflectance_scan"])

    def test_non_mapping_coverglass_block_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_optical_properties(_case(coverglass=[0.5, 0.505]))


if __name__ == "__main__":
    unittest.main()
