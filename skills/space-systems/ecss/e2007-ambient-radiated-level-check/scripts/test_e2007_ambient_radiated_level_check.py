#!/usr/bin/env python3
"""Gate 3 contract test for e2007-ambient-radiated-level-check.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_ambient_radiated_level_check.py
"""

import unittest

from e2007_ambient_radiated_level_check_logic import (
    AMBIENT_LIMITED_DB,
    CATEGORY_COMPLIANT,
    CATEGORY_EXCEEDANCE,
    CATEGORY_MARGINAL,
    DB_TOL,
    DEFAULT_REQUIRED_HEADROOM_DB,
    UNIT_DOMINANCE_DB,
    assess_ambient_radiated_level,
    at_least,
    attribute_reading,
    categorize_point,
    check_band_coverage,
    identify_narrowband_ambient,
    point_headroom_db,
    validate_ambient_configuration,
    validate_sweep,
)


def good_config(**over):
    record = {
        "unit_powered": False,
        "support_equipment_powered": True,
        "enclosure_door_closed": True,
        "receiver_bandwidth_hz": 120000.0,
        "antenna_polarization": "vertical",
        "standoff_m": 1.0,
    }
    record.update(over)
    return record


def clean_sweep():
    return [
        {"frequency_hz": 30.0e6, "ambient_dbuv_m": 20.0, "limit_dbuv_m": 40.0},
        {"frequency_hz": 40.0e6, "ambient_dbuv_m": 21.0, "limit_dbuv_m": 40.0},
        {"frequency_hz": 55.0e6, "ambient_dbuv_m": 22.0, "limit_dbuv_m": 42.0},
        {"frequency_hz": 80.0e6, "ambient_dbuv_m": 23.0, "limit_dbuv_m": 44.0},
        {"frequency_hz": 100.0e6, "ambient_dbuv_m": 24.0, "limit_dbuv_m": 46.0},
    ]


class TestConfigurationValidation(unittest.TestCase):
    def test_good_configuration_normalizes(self):
        config = validate_ambient_configuration(good_config())
        self.assertFalse(config["unit_powered"])
        self.assertEqual(config["antenna_polarization"], "vertical")
        self.assertAlmostEqual(config["receiver_bandwidth_hz"], 120000.0)

    def test_polarization_case_is_normalized(self):
        config = validate_ambient_configuration(good_config(antenna_polarization="Horizontal"))
        self.assertEqual(config["antenna_polarization"], "horizontal")

    def test_powered_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_ambient_configuration(good_config(unit_powered=True))

    def test_support_equipment_off_rejected(self):
        with self.assertRaises(ValueError):
            validate_ambient_configuration(good_config(support_equipment_powered=False))

    def test_open_door_rejected(self):
        with self.assertRaises(ValueError):
            validate_ambient_configuration(good_config(enclosure_door_closed=False))

    def test_missing_flag_rejected(self):
        record = good_config()
        del record["support_equipment_powered"]
        with self.assertRaises(ValueError):
            validate_ambient_configuration(record)

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_ambient_configuration(good_config(unit_powered="no"))

    def test_zero_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            validate_ambient_configuration(good_config(receiver_bandwidth_hz=0.0))

    def test_unrecognized_polarization_rejected(self):
        with self.assertRaises(ValueError):
            validate_ambient_configuration(good_config(antenna_polarization="circular"))

    def test_non_string_polarization_rejected(self):
        with self.assertRaises(ValueError):
            validate_ambient_configuration(good_config(antenna_polarization=90))

    def test_zero_standoff_rejected(self):
        with self.assertRaises(ValueError):
            validate_ambient_configuration(good_config(standoff_m=0.0))

    def test_bandwidth_matching_reference_accepted(self):
        config = validate_ambient_configuration(good_config(), reference_bandwidth_hz=120000.0)
        self.assertAlmostEqual(config["receiver_bandwidth_hz"], 120000.0)

    def test_bandwidth_mismatch_with_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_ambient_configuration(good_config(), reference_bandwidth_hz=9000.0)

    def test_non_mapping_configuration_rejected(self):
        with self.assertRaises(ValueError):
            validate_ambient_configuration(["unit off"])


class TestSweepValidation(unittest.TestCase):
    def test_clean_sweep_normalizes(self):
        sweep = validate_sweep(clean_sweep())
        self.assertEqual(len(sweep), 5)
        self.assertAlmostEqual(sweep[0]["frequency_hz"], 30.0e6)

    def test_empty_sweep_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep([])

    def test_non_list_sweep_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep({"frequency_hz": 30.0e6})

    def test_non_mapping_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep([(30.0e6, 20.0, 40.0)])

    def test_missing_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep([{"frequency_hz": 30.0e6, "ambient_dbuv_m": 20.0}])

    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep(
                [{"frequency_hz": -1.0, "ambient_dbuv_m": 20.0, "limit_dbuv_m": 40.0}]
            )

    def test_decreasing_frequency_rejected(self):
        points = clean_sweep()
        points[2]["frequency_hz"] = 35.0e6
        with self.assertRaises(ValueError):
            validate_sweep(points)

    def test_duplicate_frequency_rejected(self):
        points = clean_sweep()
        points[1]["frequency_hz"] = points[0]["frequency_hz"]
        with self.assertRaises(ValueError):
            validate_sweep(points)


class TestHeadroomCategorization(unittest.TestCase):
    def test_headroom_is_limit_minus_ambient(self):
        point = {"frequency_hz": 30.0e6, "ambient_dbuv_m": 21.5, "limit_dbuv_m": 40.0}
        self.assertAlmostEqual(point_headroom_db(point), 18.5)

    def test_wide_headroom_is_compliant(self):
        point = {"frequency_hz": 30.0e6, "ambient_dbuv_m": 10.0, "limit_dbuv_m": 40.0}
        self.assertEqual(categorize_point(point), CATEGORY_COMPLIANT)

    def test_headroom_just_short_is_marginal(self):
        point = {"frequency_hz": 30.0e6, "ambient_dbuv_m": 35.0, "limit_dbuv_m": 40.0}
        self.assertEqual(categorize_point(point), CATEGORY_MARGINAL)

    def test_ambient_above_limit_is_exceedance(self):
        point = {"frequency_hz": 30.0e6, "ambient_dbuv_m": 45.0, "limit_dbuv_m": 40.0}
        self.assertEqual(categorize_point(point), CATEGORY_EXCEEDANCE)

    def test_ambient_equal_to_limit_is_exceedance(self):
        point = {"frequency_hz": 30.0e6, "ambient_dbuv_m": 40.0, "limit_dbuv_m": 40.0}
        self.assertEqual(categorize_point(point), CATEGORY_EXCEEDANCE)

    def test_exact_required_headroom_is_compliant_despite_float_error(self):
        # 32.3 - 26.3 is 5.9999999999999964 in binary floating point, so a
        # physically compliant 6.0 dB headroom reads short of the requirement.
        point = {"frequency_hz": 30.0e6, "ambient_dbuv_m": 26.3, "limit_dbuv_m": 32.3}
        self.assertLess(point_headroom_db(point), DEFAULT_REQUIRED_HEADROOM_DB)
        self.assertEqual(categorize_point(point), CATEGORY_COMPLIANT)

    def test_negative_required_headroom_rejected(self):
        point = {"frequency_hz": 30.0e6, "ambient_dbuv_m": 10.0, "limit_dbuv_m": 40.0}
        with self.assertRaises(ValueError):
            categorize_point(point, required_headroom_db=-1.0)

    def test_non_numeric_required_headroom_rejected(self):
        point = {"frequency_hz": 30.0e6, "ambient_dbuv_m": 10.0, "limit_dbuv_m": 40.0}
        with self.assertRaises(ValueError):
            categorize_point(point, required_headroom_db="six")

    def test_tighter_requirement_moves_a_point_to_marginal(self):
        point = {"frequency_hz": 30.0e6, "ambient_dbuv_m": 30.0, "limit_dbuv_m": 40.0}
        self.assertEqual(categorize_point(point), CATEGORY_COMPLIANT)
        self.assertEqual(
            categorize_point(point, required_headroom_db=12.0), CATEGORY_MARGINAL
        )

    def test_at_least_absorbs_float_error_only(self):
        self.assertTrue(at_least(6.0, 6.0))
        self.assertTrue(at_least(6.0 - DB_TOL / 2.0, 6.0))
        self.assertFalse(at_least(5.9, 6.0))


class TestNarrowbandIdentification(unittest.TestCase):
    def test_flat_floor_has_no_peaks(self):
        self.assertEqual(identify_narrowband_ambient(clean_sweep()), [])

    def test_discrete_carrier_is_identified(self):
        points = clean_sweep()
        points[2]["ambient_dbuv_m"] = 38.0
        peaks = identify_narrowband_ambient(points)
        self.assertEqual(len(peaks), 1)
        self.assertAlmostEqual(peaks[0]["frequency_hz"], 55.0e6)
        self.assertAlmostEqual(peaks[0]["prominence_db"], 15.0)

    def test_edge_point_is_not_a_peak(self):
        points = clean_sweep()
        points[0]["ambient_dbuv_m"] = 38.0
        self.assertEqual(identify_narrowband_ambient(points), [])

    def test_prominence_threshold_is_honoured(self):
        points = clean_sweep()
        points[2]["ambient_dbuv_m"] = 27.0
        self.assertEqual(identify_narrowband_ambient(points), [])
        self.assertEqual(len(identify_narrowband_ambient(points, prominence_db=4.0)), 1)

    def test_zero_prominence_rejected(self):
        with self.assertRaises(ValueError):
            identify_narrowband_ambient(clean_sweep(), prominence_db=0.0)


class TestBandCoverage(unittest.TestCase):
    def test_covered_band_has_no_gaps(self):
        self.assertEqual(
            check_band_coverage(clean_sweep(), 30.0e6, 100.0e6, max_step_ratio=1.5), []
        )

    def test_uncovered_band_start_reported(self):
        gaps = check_band_coverage(clean_sweep(), 10.0e6, 100.0e6)
        self.assertTrue(any("band start" in g for g in gaps))

    def test_uncovered_band_stop_reported(self):
        gaps = check_band_coverage(clean_sweep(), 30.0e6, 200.0e6)
        self.assertTrue(any("band stop" in g for g in gaps))

    def test_coarse_step_reported(self):
        points = [
            {"frequency_hz": 30.0e6, "ambient_dbuv_m": 20.0, "limit_dbuv_m": 40.0},
            {"frequency_hz": 300.0e6, "ambient_dbuv_m": 20.0, "limit_dbuv_m": 40.0},
        ]
        gaps = check_band_coverage(points, 30.0e6, 300.0e6)
        self.assertTrue(any("ratio" in g for g in gaps))

    def test_step_exactly_at_ratio_is_not_a_gap(self):
        points = [
            {"frequency_hz": 100.0e6, "ambient_dbuv_m": 20.0, "limit_dbuv_m": 40.0},
            {"frequency_hz": 150.0e6, "ambient_dbuv_m": 20.0, "limit_dbuv_m": 40.0},
        ]
        self.assertEqual(check_band_coverage(points, 100.0e6, 150.0e6, 1.5), [])

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            check_band_coverage(clean_sweep(), 100.0e6, 30.0e6)

    def test_zero_band_start_rejected(self):
        with self.assertRaises(ValueError):
            check_band_coverage(clean_sweep(), 0.0, 100.0e6)

    def test_step_ratio_of_one_rejected(self):
        with self.assertRaises(ValueError):
            check_band_coverage(clean_sweep(), 30.0e6, 100.0e6, max_step_ratio=1.0)


class TestAttribution(unittest.TestCase):
    def test_reading_well_above_ambient_is_unit_dominated(self):
        self.assertEqual(attribute_reading(40.0, 20.0), "unit-dominated")

    def test_reading_exactly_at_dominance_threshold(self):
        self.assertEqual(
            attribute_reading(20.0 + UNIT_DOMINANCE_DB, 20.0), "unit-dominated"
        )

    def test_reading_on_the_floor_is_ambient_limited(self):
        self.assertEqual(attribute_reading(20.0, 20.0), "ambient-limited")

    def test_reading_just_above_the_floor_is_ambient_limited(self):
        self.assertEqual(
            attribute_reading(20.0 + AMBIENT_LIMITED_DB, 20.0), "ambient-limited"
        )

    def test_reading_between_thresholds_is_indeterminate(self):
        self.assertEqual(attribute_reading(23.0, 20.0), "indeterminate")

    def test_reading_below_ambient_rejected(self):
        with self.assertRaises(ValueError):
            attribute_reading(15.0, 20.0)

    def test_non_numeric_reading_rejected(self):
        with self.assertRaises(ValueError):
            attribute_reading("40", 20.0)


class TestAssessment(unittest.TestCase):
    def test_clean_baseline_is_usable(self):
        report = assess_ambient_radiated_level(
            good_config(), clean_sweep(), 30.0e6, 100.0e6
        )
        self.assertEqual(report["verdict"], "usable-baseline")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["counts"][CATEGORY_COMPLIANT], 5)

    def test_worst_case_is_the_smallest_headroom(self):
        points = clean_sweep()
        points[3]["ambient_dbuv_m"] = 39.0
        report = assess_ambient_radiated_level(good_config(), points, 30.0e6, 100.0e6)
        self.assertAlmostEqual(report["worst_case"]["frequency_hz"], 80.0e6)
        self.assertAlmostEqual(report["worst_case"]["headroom_db"], 5.0)

    def test_exceedance_rejects_the_baseline(self):
        points = clean_sweep()
        points[1]["ambient_dbuv_m"] = 48.0
        report = assess_ambient_radiated_level(good_config(), points, 30.0e6, 100.0e6)
        self.assertEqual(report["verdict"], "baseline-rejected")
        self.assertEqual(report["counts"][CATEGORY_EXCEEDANCE], 1)
        self.assertTrue(any("ambient exceedance" in f for f in report["findings"]))

    def test_marginal_point_is_a_limitation_not_a_finding(self):
        points = clean_sweep()
        points[3]["ambient_dbuv_m"] = 41.0
        report = assess_ambient_radiated_level(good_config(), points, 30.0e6, 100.0e6)
        self.assertEqual(report["counts"][CATEGORY_MARGINAL], 1)
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("marginal headroom" in l for l in report["limitations"]))
        self.assertEqual(report["verdict"], "usable-baseline")

    def test_coverage_gap_rejects_the_baseline(self):
        report = assess_ambient_radiated_level(
            good_config(), clean_sweep(), 30.0e6, 1000.0e6
        )
        self.assertEqual(report["verdict"], "baseline-rejected")
        self.assertTrue(any("coverage gap" in f for f in report["findings"]))

    def test_narrowband_peak_appears_as_a_limitation(self):
        points = clean_sweep()
        points[2]["ambient_dbuv_m"] = 33.0
        report = assess_ambient_radiated_level(good_config(), points, 30.0e6, 100.0e6)
        self.assertEqual(len(report["narrowband_ambient"]), 1)
        self.assertTrue(
            any("narrowband ambient signal" in l for l in report["limitations"])
        )

    def test_assessment_propagates_configuration_error(self):
        with self.assertRaises(ValueError):
            assess_ambient_radiated_level(
                good_config(unit_powered=True), clean_sweep(), 30.0e6, 100.0e6
            )

    def test_assessment_propagates_bandwidth_mismatch(self):
        with self.assertRaises(ValueError):
            assess_ambient_radiated_level(
                good_config(),
                clean_sweep(),
                30.0e6,
                100.0e6,
                reference_bandwidth_hz=9000.0,
            )

    def test_assessment_propagates_sweep_error(self):
        with self.assertRaises(ValueError):
            assess_ambient_radiated_level(good_config(), [], 30.0e6, 100.0e6)

    def test_every_point_carries_a_category(self):
        report = assess_ambient_radiated_level(
            good_config(), clean_sweep(), 30.0e6, 100.0e6
        )
        self.assertEqual(len(report["points"]), 5)
        for entry in report["points"]:
            self.assertIn(
                entry["category"],
                (CATEGORY_COMPLIANT, CATEGORY_MARGINAL, CATEGORY_EXCEEDANCE),
            )


if __name__ == "__main__":
    unittest.main()
