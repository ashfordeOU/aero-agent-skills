#!/usr/bin/env python3
"""Gate 3 contract test for e2007-ambient-conducted-level-check.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_ambient_conducted_level_check.py
"""

import unittest

from e2007_ambient_conducted_level_check_logic import (
    CATEGORY_COMPLIANT,
    CATEGORY_EXCEEDANCE,
    CATEGORY_MARGINAL,
    DB_TOL,
    DEFAULT_REQUIRED_HEADROOM_DB,
    RECOGNIZED_LEADS,
    assess_ambient_conducted_level,
    at_least,
    categorize_point,
    current_tolerance_band,
    governing_lead,
    grade_lead,
    normalize_lead,
    point_headroom_db,
    validate_conducted_configuration,
    validate_dummy_load,
    validate_lead_sweep,
)


def good_config(**over):
    record = {
        "unit_connected": False,
        "dummy_load_installed": True,
        "support_equipment_powered": True,
        "lisn_inductance_uh": 5.0,
        "receiver_bandwidth_hz": 10000.0,
    }
    record.update(over)
    return record


def good_unit(**over):
    record = {"nominal_current_a": 3.0, "bus_voltage_v": 28.0}
    record.update(over)
    return record


def good_load(**over):
    record = {"resistive": True, "current_a": 2.95, "bus_voltage_v": 28.0}
    record.update(over)
    return record


def quiet_sweep():
    return [
        {"frequency_hz": 30.0e3, "background_dbuv": 40.0, "limit_dbuv": 70.0},
        {"frequency_hz": 100.0e3, "background_dbuv": 38.0, "limit_dbuv": 68.0},
        {"frequency_hz": 1.0e6, "background_dbuv": 32.0, "limit_dbuv": 60.0},
        {"frequency_hz": 10.0e6, "background_dbuv": 28.0, "limit_dbuv": 56.0},
    ]


def two_lead_sweeps():
    return {
        "primary-positive": quiet_sweep(),
        "primary-return": quiet_sweep(),
    }


class TestCurrentBand(unittest.TestCase):
    def test_band_brackets_the_nominal_draw(self):
        low, high = current_tolerance_band(3.0)
        self.assertAlmostEqual(low, 2.7)
        self.assertAlmostEqual(high, 3.3)

    def test_tighter_fraction_narrows_the_band(self):
        low, high = current_tolerance_band(3.0, tolerance_fraction=0.02)
        self.assertAlmostEqual(low, 2.94)
        self.assertAlmostEqual(high, 3.06)

    def test_zero_nominal_current_rejected(self):
        with self.assertRaises(ValueError):
            current_tolerance_band(0.0)

    def test_fraction_of_one_rejected(self):
        with self.assertRaises(ValueError):
            current_tolerance_band(3.0, tolerance_fraction=1.0)

    def test_zero_fraction_rejected(self):
        with self.assertRaises(ValueError):
            current_tolerance_band(3.0, tolerance_fraction=0.0)


class TestDummyLoadValidation(unittest.TestCase):
    def test_representative_load_accepted(self):
        record = validate_dummy_load(good_load(), good_unit())
        self.assertTrue(record["resistive"])
        self.assertAlmostEqual(record["current_a"], 2.95)
        self.assertAlmostEqual(record["nominal_current_a"], 3.0)

    def test_non_resistive_load_rejected(self):
        with self.assertRaises(ValueError):
            validate_dummy_load(good_load(resistive=False), good_unit())

    def test_missing_resistive_flag_rejected(self):
        record = good_load()
        del record["resistive"]
        with self.assertRaises(ValueError):
            validate_dummy_load(record, good_unit())

    def test_load_current_too_low_rejected(self):
        with self.assertRaises(ValueError):
            validate_dummy_load(good_load(current_a=0.3), good_unit())

    def test_load_current_too_high_rejected(self):
        with self.assertRaises(ValueError):
            validate_dummy_load(good_load(current_a=4.2), good_unit())

    def test_zero_load_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_dummy_load(good_load(current_a=0.0), good_unit())

    def test_bus_voltage_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            validate_dummy_load(good_load(bus_voltage_v=50.0), good_unit())

    def test_bus_voltage_within_relative_tolerance_accepted(self):
        record = validate_dummy_load(good_load(bus_voltage_v=28.3), good_unit())
        self.assertAlmostEqual(record["bus_voltage_v"], 28.3)

    def test_non_mapping_load_rejected(self):
        with self.assertRaises(ValueError):
            validate_dummy_load("50 ohm", good_unit())

    def test_non_mapping_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_dummy_load(good_load(), "3 A at 28 V")

    def test_missing_unit_nominal_current_rejected(self):
        record = good_unit()
        del record["nominal_current_a"]
        with self.assertRaises(ValueError):
            validate_dummy_load(good_load(), record)

    def test_band_edge_current_accepted_despite_float_error(self):
        # 1.3 * 0.9 is 1.1700000000000002, so a load drawing exactly the
        # physically-correct 1.17 A edge reads outside the computed band.
        low, _high = current_tolerance_band(1.3)
        self.assertGreater(low, 1.17)
        record = validate_dummy_load(
            good_load(current_a=1.17), good_unit(nominal_current_a=1.3)
        )
        self.assertAlmostEqual(record["current_a"], 1.17)

    def test_tighter_tolerance_rejects_a_previously_ok_load(self):
        validate_dummy_load(good_load(current_a=2.75), good_unit())
        with self.assertRaises(ValueError):
            validate_dummy_load(
                good_load(current_a=2.75), good_unit(), tolerance_fraction=0.02
            )


class TestConfigurationValidation(unittest.TestCase):
    def test_good_configuration_normalizes(self):
        config = validate_conducted_configuration(good_config())
        self.assertFalse(config["unit_connected"])
        self.assertAlmostEqual(config["lisn_inductance_uh"], 5.0)

    def test_connected_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_conducted_configuration(good_config(unit_connected=True))

    def test_missing_dummy_load_rejected(self):
        with self.assertRaises(ValueError):
            validate_conducted_configuration(good_config(dummy_load_installed=False))

    def test_support_equipment_off_rejected(self):
        with self.assertRaises(ValueError):
            validate_conducted_configuration(
                good_config(support_equipment_powered=False)
            )

    def test_unrecognized_lisn_inductance_rejected(self):
        with self.assertRaises(ValueError):
            validate_conducted_configuration(good_config(lisn_inductance_uh=1.0))

    def test_fifty_microhenry_network_accepted(self):
        config = validate_conducted_configuration(good_config(lisn_inductance_uh=50.0))
        self.assertAlmostEqual(config["lisn_inductance_uh"], 50.0)

    def test_zero_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            validate_conducted_configuration(good_config(receiver_bandwidth_hz=0.0))

    def test_bandwidth_matching_reference_accepted(self):
        config = validate_conducted_configuration(
            good_config(), reference_bandwidth_hz=10000.0
        )
        self.assertAlmostEqual(config["receiver_bandwidth_hz"], 10000.0)

    def test_bandwidth_mismatch_with_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_conducted_configuration(good_config(), reference_bandwidth_hz=1000.0)

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_conducted_configuration(good_config(unit_connected="no"))

    def test_non_mapping_configuration_rejected(self):
        with self.assertRaises(ValueError):
            validate_conducted_configuration(["unit removed"])


class TestLeadAndSweepValidation(unittest.TestCase):
    def test_every_recognized_lead_normalizes(self):
        for lead in RECOGNIZED_LEADS:
            self.assertEqual(normalize_lead(lead.upper()), lead)

    def test_unrecognized_lead_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lead("chassis-bond")

    def test_non_string_lead_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lead(1)

    def test_clean_sweep_normalizes(self):
        sweep = validate_lead_sweep(quiet_sweep())
        self.assertEqual(len(sweep), 4)
        self.assertAlmostEqual(sweep[0]["background_dbuv"], 40.0)

    def test_empty_sweep_rejected(self):
        with self.assertRaises(ValueError):
            validate_lead_sweep([])

    def test_non_list_sweep_rejected(self):
        with self.assertRaises(ValueError):
            validate_lead_sweep({"frequency_hz": 30.0e3})

    def test_missing_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_lead_sweep([{"frequency_hz": 30.0e3, "background_dbuv": 40.0}])

    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_lead_sweep(
                [{"frequency_hz": -30.0, "background_dbuv": 40.0, "limit_dbuv": 70.0}]
            )

    def test_decreasing_frequency_rejected(self):
        points = quiet_sweep()
        points[2]["frequency_hz"] = 50.0e3
        with self.assertRaises(ValueError):
            validate_lead_sweep(points)

    def test_duplicate_frequency_rejected(self):
        points = quiet_sweep()
        points[1]["frequency_hz"] = points[0]["frequency_hz"]
        with self.assertRaises(ValueError):
            validate_lead_sweep(points)


class TestHeadroomCategorization(unittest.TestCase):
    def test_headroom_is_limit_minus_background(self):
        point = {"frequency_hz": 30.0e3, "background_dbuv": 41.5, "limit_dbuv": 70.0}
        self.assertAlmostEqual(point_headroom_db(point), 28.5)

    def test_wide_headroom_is_compliant(self):
        point = {"frequency_hz": 30.0e3, "background_dbuv": 40.0, "limit_dbuv": 70.0}
        self.assertEqual(categorize_point(point), CATEGORY_COMPLIANT)

    def test_headroom_just_short_is_marginal(self):
        point = {"frequency_hz": 30.0e3, "background_dbuv": 66.0, "limit_dbuv": 70.0}
        self.assertEqual(categorize_point(point), CATEGORY_MARGINAL)

    def test_background_above_limit_is_exceedance(self):
        point = {"frequency_hz": 30.0e3, "background_dbuv": 75.0, "limit_dbuv": 70.0}
        self.assertEqual(categorize_point(point), CATEGORY_EXCEEDANCE)

    def test_background_equal_to_limit_is_exceedance(self):
        point = {"frequency_hz": 30.0e3, "background_dbuv": 70.0, "limit_dbuv": 70.0}
        self.assertEqual(categorize_point(point), CATEGORY_EXCEEDANCE)

    def test_exact_required_headroom_is_compliant_despite_float_error(self):
        # 32.3 - 26.3 is 5.9999999999999964 in binary floating point, so a
        # physically compliant 6.0 dB separation reads short of the limit.
        point = {"frequency_hz": 30.0e3, "background_dbuv": 26.3, "limit_dbuv": 32.3}
        self.assertLess(point_headroom_db(point), DEFAULT_REQUIRED_HEADROOM_DB)
        self.assertEqual(categorize_point(point), CATEGORY_COMPLIANT)

    def test_negative_required_headroom_rejected(self):
        point = {"frequency_hz": 30.0e3, "background_dbuv": 40.0, "limit_dbuv": 70.0}
        with self.assertRaises(ValueError):
            categorize_point(point, required_headroom_db=-2.0)

    def test_non_numeric_required_headroom_rejected(self):
        point = {"frequency_hz": 30.0e3, "background_dbuv": 40.0, "limit_dbuv": 70.0}
        with self.assertRaises(ValueError):
            categorize_point(point, required_headroom_db="six")

    def test_at_least_absorbs_float_error_only(self):
        self.assertTrue(at_least(6.0, 6.0))
        self.assertTrue(at_least(6.0 - DB_TOL / 2.0, 6.0))
        self.assertFalse(at_least(5.5, 6.0))


class TestLeadGrading(unittest.TestCase):
    def test_quiet_lead_is_usable(self):
        report = grade_lead("primary-positive", quiet_sweep())
        self.assertTrue(report["usable"])
        self.assertEqual(report["counts"][CATEGORY_COMPLIANT], 4)

    def test_worst_case_is_the_smallest_headroom(self):
        points = quiet_sweep()
        points[2]["background_dbuv"] = 56.0
        report = grade_lead("primary-return", points)
        self.assertAlmostEqual(report["worst_case"]["frequency_hz"], 1.0e6)
        self.assertAlmostEqual(report["worst_case"]["headroom_db"], 4.0)

    def test_exceedance_makes_a_lead_unusable(self):
        points = quiet_sweep()
        points[0]["background_dbuv"] = 72.0
        report = grade_lead("primary-positive", points)
        self.assertFalse(report["usable"])
        self.assertEqual(report["counts"][CATEGORY_EXCEEDANCE], 1)

    def test_grade_lead_rejects_unrecognized_lead(self):
        with self.assertRaises(ValueError):
            grade_lead("antenna-feed", quiet_sweep())

    def test_grade_lead_rejects_empty_sweep(self):
        with self.assertRaises(ValueError):
            grade_lead("primary-positive", [])

    def test_governing_lead_is_the_worst_lead(self):
        quiet = grade_lead("primary-positive", quiet_sweep())
        noisy_points = quiet_sweep()
        noisy_points[1]["background_dbuv"] = 64.0
        noisy = grade_lead("primary-return", noisy_points)
        self.assertEqual(governing_lead([quiet, noisy])["lead"], "primary-return")

    def test_governing_lead_rejects_empty_set(self):
        with self.assertRaises(ValueError):
            governing_lead([])


class TestAssessment(unittest.TestCase):
    def test_clean_baseline_is_usable(self):
        report = assess_ambient_conducted_level(
            good_config(), good_load(), good_unit(), two_lead_sweeps()
        )
        self.assertEqual(report["verdict"], "usable-baseline")
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["leads"]), 2)

    def test_exceedance_rejects_the_baseline(self):
        sweeps = two_lead_sweeps()
        sweeps["primary-return"][3]["background_dbuv"] = 58.0
        report = assess_ambient_conducted_level(
            good_config(), good_load(), good_unit(), sweeps
        )
        self.assertEqual(report["verdict"], "baseline-rejected")
        self.assertEqual(report["governing_lead"], "primary-return")
        self.assertTrue(any("background exceedance" in f for f in report["findings"]))

    def test_marginal_point_is_a_limitation_not_a_finding(self):
        sweeps = two_lead_sweeps()
        sweeps["primary-positive"][0]["background_dbuv"] = 67.0
        report = assess_ambient_conducted_level(
            good_config(), good_load(), good_unit(), sweeps
        )
        self.assertEqual(report["verdict"], "usable-baseline")
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("marginal headroom" in l for l in report["limitations"]))

    def test_governing_point_carries_the_smallest_headroom(self):
        sweeps = two_lead_sweeps()
        sweeps["primary-positive"][1]["background_dbuv"] = 61.0
        report = assess_ambient_conducted_level(
            good_config(), good_load(), good_unit(), sweeps
        )
        self.assertEqual(report["governing_lead"], "primary-positive")
        self.assertAlmostEqual(report["governing_point"]["headroom_db"], 7.0)

    def test_leads_are_graded_in_a_stable_order(self):
        report = assess_ambient_conducted_level(
            good_config(), good_load(), good_unit(), two_lead_sweeps()
        )
        self.assertEqual(
            [r["lead"] for r in report["leads"]],
            ["primary-positive", "primary-return"],
        )

    def test_empty_lead_mapping_rejected(self):
        with self.assertRaises(ValueError):
            assess_ambient_conducted_level(
                good_config(), good_load(), good_unit(), {}
            )

    def test_non_mapping_lead_sweeps_rejected(self):
        with self.assertRaises(ValueError):
            assess_ambient_conducted_level(
                good_config(), good_load(), good_unit(), [quiet_sweep()]
            )

    def test_assessment_propagates_configuration_error(self):
        with self.assertRaises(ValueError):
            assess_ambient_conducted_level(
                good_config(unit_connected=True),
                good_load(),
                good_unit(),
                two_lead_sweeps(),
            )

    def test_assessment_propagates_load_error(self):
        with self.assertRaises(ValueError):
            assess_ambient_conducted_level(
                good_config(), good_load(resistive=False), good_unit(), two_lead_sweeps()
            )

    def test_assessment_propagates_bandwidth_mismatch(self):
        with self.assertRaises(ValueError):
            assess_ambient_conducted_level(
                good_config(),
                good_load(),
                good_unit(),
                two_lead_sweeps(),
                reference_bandwidth_hz=1000.0,
            )

    def test_substitution_record_is_returned(self):
        report = assess_ambient_conducted_level(
            good_config(), good_load(), good_unit(), two_lead_sweeps()
        )
        self.assertAlmostEqual(report["substitution"]["current_a"], 2.95)
        self.assertAlmostEqual(report["substitution"]["current_band_a"][0], 2.7)


if __name__ == "__main__":
    unittest.main()
