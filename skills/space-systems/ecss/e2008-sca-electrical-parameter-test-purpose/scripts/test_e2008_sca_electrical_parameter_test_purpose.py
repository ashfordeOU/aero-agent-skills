#!/usr/bin/env python3
"""Contract test for the assembly electrical parameter purpose check (offline)."""

import copy
import math
import unittest

from e2008_sca_electrical_parameter_test_purpose_logic import (
    COEFFICIENT_SOURCE,
    DEFAULT_ELECTRICAL_PARAMETER_POLICY,
    PARAMETER_DESIGN_USE,
    PARAMETER_SET_ESTABLISHED,
    PARAMETER_SET_INCOMPLETE,
    PARAMETER_SET_INCONSISTENT,
    RECOGNISED_PARAMETERS,
    UNCERTAINTY_INSUFFICIENT,
    assess_electrical_parameter_test,
    coefficient_uncertainty_pct,
    established_parameters,
    fill_factor,
    power_consistency_error_pct,
    temperature_coefficient,
    validate_electrical_parameter_policy,
)

ISC_A = 0.500
VOC_V = 8.10
IMP_A = 0.480
VMP_V = 7.20


def _measured():
    return {
        "short-circuit-current": {"value": ISC_A, "uncertainty_pct": 0.2},
        "open-circuit-voltage": {"value": VOC_V, "uncertainty_pct": 1.0},
        "current-at-maximum-power": {"value": IMP_A, "uncertainty_pct": 1.2},
        "voltage-at-maximum-power": {"value": VMP_V, "uncertainty_pct": 1.2},
    }


def _series():
    return {
        "open-circuit-voltage": [
            {"temperature_c": -100.0, "value": 9.05},
            {"temperature_c": 28.0, "value": VOC_V},
            {"temperature_c": 80.0, "value": 7.71},
        ],
        "short-circuit-current": [
            {"temperature_c": -100.0, "value": 0.4880},
            {"temperature_c": 28.0, "value": ISC_A},
            {"temperature_c": 80.0, "value": 0.5050},
        ],
    }


def _case(measured=None, series=None, condition=None, assembly_id="SCA-001"):
    return {
        "assembly_id": assembly_id,
        "measurement_condition": (
            {"irradiance_w_m2": 1367.0, "temperature_c": 28.0}
            if condition is None
            else condition
        ),
        "measured": _measured() if measured is None else measured,
        "temperature_series": _series() if series is None else series,
    }


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_electrical_parameter_policy(
                DEFAULT_ELECTRICAL_PARAMETER_POLICY
            ),
            DEFAULT_ELECTRICAL_PARAMETER_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_electrical_parameter_policy("default")

    def test_unrecognised_required_parameter_rejected(self):
        broken = copy.deepcopy(DEFAULT_ELECTRICAL_PARAMETER_POLICY)
        broken["required_parameters"] = ("series-resistance",)
        with self.assertRaises(ValueError):
            validate_electrical_parameter_policy(broken)

    def test_missing_uncertainty_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_ELECTRICAL_PARAMETER_POLICY)
        del broken["max_uncertainty_pct"]["fill-factor"]
        with self.assertRaises(ValueError):
            validate_electrical_parameter_policy(broken)

    def test_zero_power_consistency_tolerance_rejected(self):
        broken = copy.deepcopy(DEFAULT_ELECTRICAL_PARAMETER_POLICY)
        broken["power_consistency_tolerance_pct"] = 0.0
        with self.assertRaises(ValueError):
            validate_electrical_parameter_policy(broken)

    def test_every_recognised_parameter_names_a_design_activity(self):
        self.assertEqual(len(RECOGNISED_PARAMETERS), len(PARAMETER_DESIGN_USE))
        for parameter in RECOGNISED_PARAMETERS:
            self.assertTrue(PARAMETER_DESIGN_USE[parameter].strip())


class ParameterArithmeticTests(unittest.TestCase):
    def test_fill_factor_is_power_over_the_open_short_product(self):
        self.assertAlmostEqual(
            fill_factor(ISC_A, VOC_V, IMP_A * VMP_V),
            (IMP_A * VMP_V) / (ISC_A * VOC_V),
            places=9,
        )

    def test_fill_factor_rejects_a_zero_current(self):
        with self.assertRaises(ValueError):
            fill_factor(0.0, VOC_V, 3.456)

    def test_consistent_power_reports_no_error(self):
        error = power_consistency_error_pct(IMP_A * VMP_V, IMP_A, VMP_V)
        self.assertAlmostEqual(error, 0.0, places=9)

    def test_mismatched_power_is_measured_as_a_percentage(self):
        error = power_consistency_error_pct(3.5, IMP_A, VMP_V)
        self.assertAlmostEqual(error, abs(3.5 - IMP_A * VMP_V) / 3.5 * 100.0, places=9)

    def test_open_circuit_voltage_slope_is_negative(self):
        fit = temperature_coefficient(_series()["open-circuit-voltage"])
        self.assertEqual(fit["point_count"], 3)
        self.assertAlmostEqual(fit["span_c"], 180.0, places=9)
        self.assertLess(fit["slope_per_k"], -0.001)

    def test_a_single_point_cannot_give_a_slope(self):
        with self.assertRaises(ValueError):
            temperature_coefficient([{"temperature_c": 28.0, "value": VOC_V}])

    def test_points_at_one_temperature_cannot_give_a_slope(self):
        with self.assertRaises(ValueError):
            temperature_coefficient(
                [
                    {"temperature_c": 28.0, "value": VOC_V},
                    {"temperature_c": 28.0, "value": 8.11},
                ]
            )

    def test_a_narrow_span_inflates_the_slope_uncertainty(self):
        wide = temperature_coefficient(_series()["open-circuit-voltage"])
        narrow = temperature_coefficient(
            [
                {"temperature_c": 20.0, "value": 8.16},
                {"temperature_c": 36.0, "value": 8.04},
            ]
        )
        wide_pct = coefficient_uncertainty_pct(1.0, VOC_V, wide)
        narrow_pct = coefficient_uncertainty_pct(1.0, VOC_V, narrow)
        self.assertGreater(narrow_pct, wide_pct * 5.0)

    def test_slope_uncertainty_combines_two_readings_in_quadrature(self):
        fit = temperature_coefficient(_series()["open-circuit-voltage"])
        expected = (
            math.sqrt(2.0)
            * (1.0 / 100.0 * VOC_V)
            / abs(fit["measured_change"])
            * 100.0
        )
        self.assertAlmostEqual(
            coefficient_uncertainty_pct(1.0, VOC_V, fit), expected, places=9
        )


class EstablishmentTests(unittest.TestCase):
    def test_maximum_power_is_derived_rather_than_demanded_twice(self):
        established, _, _ = established_parameters(
            _measured(), _series(), DEFAULT_ELECTRICAL_PARAMETER_POLICY
        )
        self.assertEqual(established["maximum-power"]["source"], "derived")
        self.assertAlmostEqual(
            established["maximum-power"]["value"], IMP_A * VMP_V, places=9
        )

    def test_fill_factor_is_derived_from_the_established_set(self):
        established, _, _ = established_parameters(
            _measured(), _series(), DEFAULT_ELECTRICAL_PARAMETER_POLICY
        )
        self.assertEqual(established["fill-factor"]["source"], "derived")
        self.assertAlmostEqual(
            established["fill-factor"]["value"],
            (IMP_A * VMP_V) / (ISC_A * VOC_V),
            places=9,
        )

    def test_a_measured_maximum_power_is_kept_over_the_derivation(self):
        measured = _measured()
        measured["maximum-power"] = {"value": 3.40, "uncertainty_pct": 2.0}
        established, _, _ = established_parameters(
            measured, _series(), DEFAULT_ELECTRICAL_PARAMETER_POLICY
        )
        self.assertEqual(established["maximum-power"]["source"], "measured")
        self.assertAlmostEqual(established["maximum-power"]["value"], 3.40, places=9)

    def test_coefficients_are_fitted_from_the_declared_series(self):
        established, fits, short = established_parameters(
            _measured(), _series(), DEFAULT_ELECTRICAL_PARAMETER_POLICY
        )
        self.assertEqual(short, [])
        self.assertEqual(len(fits), len(COEFFICIENT_SOURCE))
        for coefficient in COEFFICIENT_SOURCE:
            self.assertEqual(established[coefficient]["source"], "fitted")

    def test_unrecognised_measured_parameter_rejected(self):
        measured = _measured()
        measured["series-resistance"] = {"value": 0.4, "uncertainty_pct": 5.0}
        with self.assertRaises(ValueError):
            established_parameters(
                measured, _series(), DEFAULT_ELECTRICAL_PARAMETER_POLICY
            )

    def test_measurement_without_an_uncertainty_rejected(self):
        measured = _measured()
        measured["open-circuit-voltage"] = {"value": VOC_V}
        with self.assertRaises(ValueError):
            established_parameters(
                measured, _series(), DEFAULT_ELECTRICAL_PARAMETER_POLICY
            )


class PurposeVerdictTests(unittest.TestCase):
    def test_a_complete_consistent_set_is_established(self):
        result = assess_electrical_parameter_test(_case())
        self.assertEqual(result["verdict"], PARAMETER_SET_ESTABLISHED)
        self.assertEqual(result["missing_parameters"], [])
        self.assertEqual(result["design_activities_blocked"], [])
        self.assertEqual(len(result["design_activities_supported"]), 7)
        self.assertAlmostEqual(
            result["power_consistency_error_pct"], 0.0, places=9
        )

    def test_a_missing_reading_blocks_the_design_activity_that_reads_it(self):
        measured = _measured()
        del measured["open-circuit-voltage"]
        series = _series()
        del series["open-circuit-voltage"]
        result = assess_electrical_parameter_test(_case(measured, series))
        self.assertEqual(result["verdict"], PARAMETER_SET_INCOMPLETE)
        self.assertIn("open-circuit-voltage", result["missing_parameters"])
        self.assertIn(
            "solar-generator-string-length-sizing",
            result["design_activities_blocked"],
        )
        self.assertNotIn(
            "solar-generator-string-length-sizing",
            result["design_activities_supported"],
        )

    def test_a_coarse_reading_leaves_the_parameter_unusable(self):
        measured = _measured()
        measured["short-circuit-current"]["uncertainty_pct"] = 6.0
        result = assess_electrical_parameter_test(_case(measured))
        self.assertEqual(result["verdict"], UNCERTAINTY_INSUFFICIENT)
        self.assertIn("short-circuit-current", result["coarse_parameters"])
        self.assertIn(
            "solar-generator-string-current-sizing",
            result["design_activities_blocked"],
        )

    def test_an_uncertainty_exactly_on_the_limit_is_adequate(self):
        allowed = float(
            DEFAULT_ELECTRICAL_PARAMETER_POLICY["max_uncertainty_pct"][
                "voltage-at-maximum-power"
            ]
        )
        measured = _measured()
        measured["voltage-at-maximum-power"]["uncertainty_pct"] = allowed
        result = assess_electrical_parameter_test(_case(measured))
        self.assertAlmostEqual(
            result["established"]["voltage-at-maximum-power"]["uncertainty_pct"],
            allowed,
            places=9,
        )
        self.assertEqual(result["coarse_parameters"], [])
        self.assertEqual(result["verdict"], PARAMETER_SET_ESTABLISHED)

    def test_a_reading_at_its_own_limit_can_still_ruin_the_slope_it_feeds(self):
        allowed = float(
            DEFAULT_ELECTRICAL_PARAMETER_POLICY["max_uncertainty_pct"][
                "open-circuit-voltage"
            ]
        )
        measured = _measured()
        measured["open-circuit-voltage"]["uncertainty_pct"] = allowed
        result = assess_electrical_parameter_test(_case(measured))
        self.assertNotIn("open-circuit-voltage", result["coarse_parameters"])
        self.assertEqual(
            result["coarse_parameters"],
            ["temperature-coefficient-open-circuit-voltage"],
        )
        self.assertEqual(result["verdict"], UNCERTAINTY_INSUFFICIENT)

    def test_a_reported_power_that_contradicts_its_own_point_is_inconsistent(self):
        measured = _measured()
        measured["maximum-power"] = {"value": 3.90, "uncertainty_pct": 2.0}
        result = assess_electrical_parameter_test(_case(measured))
        self.assertEqual(result["verdict"], PARAMETER_SET_INCONSISTENT)
        self.assertIn("maximum-power", result["inconsistencies"])

    def test_a_power_error_exactly_on_the_tolerance_is_consistent(self):
        reported = 3.50
        error = abs(reported - IMP_A * VMP_V) / reported * 100.0
        policy = copy.deepcopy(DEFAULT_ELECTRICAL_PARAMETER_POLICY)
        policy["power_consistency_tolerance_pct"] = error
        measured = _measured()
        measured["maximum-power"] = {"value": reported, "uncertainty_pct": 2.0}
        result = assess_electrical_parameter_test(_case(measured), policy)
        self.assertAlmostEqual(
            result["power_consistency_error_pct"], error, places=9
        )
        self.assertEqual(result["inconsistencies"], [])
        self.assertEqual(result["verdict"], PARAMETER_SET_ESTABLISHED)

    def test_a_fill_factor_above_unity_is_inconsistent(self):
        measured = _measured()
        measured["current-at-maximum-power"]["value"] = 0.625
        measured["voltage-at-maximum-power"]["value"] = 8.0
        result = assess_electrical_parameter_test(_case(measured))
        self.assertEqual(result["verdict"], PARAMETER_SET_INCONSISTENT)
        self.assertEqual(result["inconsistencies"], ["fill-factor"])
        self.assertGreater(result["fill_factor"], 1.0)

    def test_parameters_taken_at_the_wrong_irradiance_are_inconsistent(self):
        result = assess_electrical_parameter_test(
            _case(condition={"irradiance_w_m2": 1000.0, "temperature_c": 28.0})
        )
        self.assertEqual(result["verdict"], PARAMETER_SET_INCONSISTENT)
        self.assertIn("irradiance", result["inconsistencies"])

    def test_parameters_taken_at_the_wrong_temperature_are_inconsistent(self):
        result = assess_electrical_parameter_test(
            _case(condition={"irradiance_w_m2": 1367.0, "temperature_c": 25.0})
        )
        self.assertEqual(result["verdict"], PARAMETER_SET_INCONSISTENT)
        self.assertIn("temperature", result["inconsistencies"])

    def test_a_narrow_temperature_span_establishes_no_coefficient(self):
        series = _series()
        series["open-circuit-voltage"] = [
            {"temperature_c": 20.0, "value": 8.16},
            {"temperature_c": 36.0, "value": 8.04},
        ]
        result = assess_electrical_parameter_test(_case(series=series))
        self.assertEqual(result["verdict"], PARAMETER_SET_INCOMPLETE)
        self.assertIn(
            "temperature-coefficient-open-circuit-voltage",
            result["short_span_coefficients"],
        )
        self.assertIn(
            "solar-generator-cold-case-voltage-margin",
            result["design_activities_blocked"],
        )

    def test_no_temperature_series_leaves_both_coefficients_missing(self):
        result = assess_electrical_parameter_test(_case(series={}))
        self.assertEqual(result["verdict"], PARAMETER_SET_INCOMPLETE)
        self.assertEqual(len(result["missing_parameters"]), 2)
        self.assertEqual(result["short_span_coefficients"], [])

    def test_inconsistency_outranks_an_incomplete_set(self):
        measured = _measured()
        measured["maximum-power"] = {"value": 3.90, "uncertainty_pct": 2.0}
        result = assess_electrical_parameter_test(_case(measured, series={}))
        self.assertEqual(result["verdict"], PARAMETER_SET_INCONSISTENT)
        self.assertTrue(result["missing_parameters"])

    def test_a_shared_activity_is_blocked_by_either_parameter_that_feeds_it(self):
        measured = _measured()
        measured["current-at-maximum-power"]["uncertainty_pct"] = 9.0
        result = assess_electrical_parameter_test(_case(measured))
        self.assertIn(
            "solar-generator-power-budget", result["design_activities_blocked"]
        )
        self.assertNotIn(
            "solar-generator-power-budget", result["design_activities_supported"]
        )

    def test_a_case_without_measurements_is_refused(self):
        case = _case()
        del case["measured"]
        with self.assertRaises(ValueError):
            assess_electrical_parameter_test(case)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_electrical_parameter_test("SCA-001")

    def test_missing_assembly_id_refused(self):
        case = _case()
        del case["assembly_id"]
        with self.assertRaises(ValueError):
            assess_electrical_parameter_test(case)

    def test_a_stricter_project_policy_is_honoured(self):
        strict = copy.deepcopy(DEFAULT_ELECTRICAL_PARAMETER_POLICY)
        strict["max_uncertainty_pct"]["open-circuit-voltage"] = 0.5
        loose = assess_electrical_parameter_test(_case())
        tight = assess_electrical_parameter_test(_case(), strict)
        self.assertEqual(loose["verdict"], PARAMETER_SET_ESTABLISHED)
        self.assertEqual(tight["verdict"], UNCERTAINTY_INSUFFICIENT)
        self.assertEqual(tight["coarse_parameters"], ["open-circuit-voltage"])


if __name__ == "__main__":
    unittest.main()
