#!/usr/bin/env python3
"""Gate 3 contract test for e2001-multipactor-nominal-power-definition.

Anchor: ECSS-E-ST-20-01C clause 4.3.1.1. Stdlib unittest, offline,
deterministic. Run: python3 test_e2001_multipactor_nominal_power_definition.py
"""

import math
import unittest

from e2001_multipactor_nominal_power_definition_logic import (
    DEFAULT_ROUTE_MARGINS_DB,
    aggregate_uncertainty_db,
    apply_power_margin,
    assess_nominal_power_definition,
    combine_carrier_powers,
    dbm_to_watt,
    derive_nominal_multipactor_free_power,
    peak_to_average_ratio_db,
    route_margin_db,
    validate_carrier_powers,
    verify_declared_power,
    watt_to_dbm,
)


def _budget():
    return [
        {"name": "harness-loss", "kind": "bias", "db": -0.4},
        {"name": "amplifier-drive-tolerance", "kind": "uncertainty", "db": 0.3},
        {"name": "telemetry-read-back", "kind": "uncertainty", "db": 0.2},
    ]


def _spec(**overrides):
    spec = {
        "carrier_watts": [100.0, 100.0],
        "combining_rule": "coherent-peak",
        "budget_terms": _budget(),
        "budget_method": "arithmetic-sum",
        "declared_nominal_dbm": 57.0,
        "verification_route": "multipactor-test",
    }
    spec.update(overrides)
    return spec


class TestUnitConversion(unittest.TestCase):
    def test_one_watt_is_thirty_dbm(self):
        self.assertAlmostEqual(watt_to_dbm(1.0), 30.0)

    def test_one_milliwatt_is_zero_dbm(self):
        self.assertAlmostEqual(watt_to_dbm(0.001), 0.0)

    def test_conversion_round_trips(self):
        self.assertAlmostEqual(dbm_to_watt(watt_to_dbm(250.0)), 250.0, places=9)

    def test_doubling_power_adds_three_decibel(self):
        self.assertAlmostEqual(watt_to_dbm(200.0) - watt_to_dbm(100.0), 10.0 * math.log10(2.0))

    def test_zero_watt_raises(self):
        with self.assertRaises(ValueError):
            watt_to_dbm(0.0)

    def test_negative_watt_raises(self):
        with self.assertRaises(ValueError):
            watt_to_dbm(-5.0)

    def test_non_numeric_watt_raises(self):
        with self.assertRaises(ValueError):
            watt_to_dbm("100 W")

    def test_boolean_is_not_a_power(self):
        with self.assertRaises(ValueError):
            watt_to_dbm(True)

    def test_infinite_level_raises(self):
        with self.assertRaises(ValueError):
            dbm_to_watt(float("inf"))

    def test_nan_level_raises(self):
        with self.assertRaises(ValueError):
            dbm_to_watt(float("nan"))


class TestCarrierValidation(unittest.TestCase):
    def test_valid_carriers_pass_through(self):
        self.assertEqual(validate_carrier_powers([10.0, 20.0]), [10.0, 20.0])

    def test_integers_are_accepted_as_watt(self):
        self.assertEqual(validate_carrier_powers([10, 20]), [10.0, 20.0])

    def test_empty_carrier_list_raises(self):
        with self.assertRaises(ValueError):
            validate_carrier_powers([])

    def test_non_list_carriers_raise(self):
        with self.assertRaises(ValueError):
            validate_carrier_powers(100.0)

    def test_zero_carrier_power_raises(self):
        with self.assertRaises(ValueError):
            validate_carrier_powers([100.0, 0.0])

    def test_negative_carrier_power_raises(self):
        with self.assertRaises(ValueError):
            validate_carrier_powers([-100.0])

    def test_non_numeric_carrier_power_raises(self):
        with self.assertRaises(ValueError):
            validate_carrier_powers([100.0, None])


class TestCarrierCombining(unittest.TestCase):
    def test_two_equal_carriers_give_four_times_the_peak(self):
        self.assertAlmostEqual(combine_carrier_powers([100.0, 100.0], "coherent-peak"), 400.0)

    def test_three_equal_carriers_give_nine_times_the_peak(self):
        self.assertAlmostEqual(
            combine_carrier_powers([10.0, 10.0, 10.0], "coherent-peak"), 90.0
        )

    def test_average_sum_adds_the_powers(self):
        self.assertAlmostEqual(combine_carrier_powers([100.0, 100.0], "average-sum"), 200.0)

    def test_unequal_carriers_combine_on_amplitude(self):
        expected = (math.sqrt(90.0) + math.sqrt(10.0)) ** 2
        self.assertAlmostEqual(
            combine_carrier_powers([90.0, 10.0], "coherent-peak"), expected
        )

    def test_single_carrier_rule_returns_the_carrier(self):
        self.assertAlmostEqual(combine_carrier_powers([75.0], "single-carrier"), 75.0)

    def test_single_carrier_rule_rejects_two_carriers(self):
        with self.assertRaises(ValueError):
            combine_carrier_powers([75.0, 75.0], "single-carrier")

    def test_one_carrier_is_identical_under_every_rule(self):
        self.assertAlmostEqual(
            combine_carrier_powers([75.0], "coherent-peak"),
            combine_carrier_powers([75.0], "average-sum"),
        )

    def test_unknown_combining_rule_raises(self):
        with self.assertRaises(ValueError):
            combine_carrier_powers([100.0], "worst-case-guess")

    def test_non_string_combining_rule_raises(self):
        with self.assertRaises(ValueError):
            combine_carrier_powers([100.0], 2)

    def test_peak_exceeds_average_for_multiple_carriers(self):
        self.assertGreater(
            combine_carrier_powers([50.0, 50.0], "coherent-peak"),
            combine_carrier_powers([50.0, 50.0], "average-sum"),
        )


class TestPeakToAverage(unittest.TestCase):
    def test_two_equal_carriers_give_three_decibel(self):
        self.assertAlmostEqual(peak_to_average_ratio_db([50.0, 50.0]), 10.0 * math.log10(2.0))

    def test_four_equal_carriers_give_six_decibel(self):
        self.assertAlmostEqual(
            peak_to_average_ratio_db([5.0] * 4), 10.0 * math.log10(4.0), places=9
        )

    def test_single_carrier_has_no_ratio(self):
        self.assertAlmostEqual(peak_to_average_ratio_db([120.0]), 0.0)

    def test_unequal_carriers_fall_below_the_equal_case(self):
        self.assertLess(
            peak_to_average_ratio_db([99.0, 1.0]), peak_to_average_ratio_db([50.0, 50.0])
        )

    def test_invalid_carrier_raises(self):
        with self.assertRaises(ValueError):
            peak_to_average_ratio_db([0.0, 50.0])


class TestBudgetAggregation(unittest.TestCase):
    def test_arithmetic_sum_adds_magnitudes(self):
        result = aggregate_uncertainty_db(_budget(), "arithmetic-sum")
        self.assertAlmostEqual(result["uncertainty_db"], 0.5)
        self.assertAlmostEqual(result["bias_db"], -0.4)
        self.assertAlmostEqual(result["total_db"], 0.1)

    def test_root_sum_square_is_smaller_than_the_linear_sum(self):
        rss = aggregate_uncertainty_db(_budget(), "root-sum-square")
        linear = aggregate_uncertainty_db(_budget(), "arithmetic-sum")
        self.assertAlmostEqual(rss["uncertainty_db"], math.sqrt(0.09 + 0.04))
        self.assertLess(rss["uncertainty_db"], linear["uncertainty_db"])

    def test_kind_defaults_to_uncertainty(self):
        result = aggregate_uncertainty_db([{"name": "drive", "db": 0.6}])
        self.assertAlmostEqual(result["uncertainty_db"], 0.6)
        self.assertAlmostEqual(result["bias_db"], 0.0)

    def test_positive_bias_raises_the_total(self):
        result = aggregate_uncertainty_db(
            [{"name": "pre-amplifier-gain", "kind": "bias", "db": 1.5}]
        )
        self.assertAlmostEqual(result["total_db"], 1.5)

    def test_empty_budget_is_neutral(self):
        result = aggregate_uncertainty_db([])
        self.assertAlmostEqual(result["total_db"], 0.0)
        self.assertEqual(result["terms"], [])

    def test_negative_uncertainty_magnitude_raises(self):
        with self.assertRaises(ValueError):
            aggregate_uncertainty_db([{"name": "drive", "kind": "uncertainty", "db": -0.3}])

    def test_unknown_term_kind_raises(self):
        with self.assertRaises(ValueError):
            aggregate_uncertainty_db([{"name": "drive", "kind": "guess", "db": 0.3}])

    def test_unnamed_term_raises(self):
        with self.assertRaises(ValueError):
            aggregate_uncertainty_db([{"kind": "bias", "db": 0.3}])

    def test_non_mapping_term_raises(self):
        with self.assertRaises(ValueError):
            aggregate_uncertainty_db(["0.3 dB"])

    def test_unknown_budget_method_raises(self):
        with self.assertRaises(ValueError):
            aggregate_uncertainty_db([], "engineering-judgement")

    def test_non_list_budget_raises(self):
        with self.assertRaises(ValueError):
            aggregate_uncertainty_db({"name": "drive", "db": 0.3})


class TestDerivation(unittest.TestCase):
    def test_worst_case_sits_above_the_combined_level(self):
        result = derive_nominal_multipactor_free_power([100.0, 100.0], "coherent-peak", _budget())
        self.assertAlmostEqual(result["combined_w"], 400.0)
        self.assertAlmostEqual(result["combined_dbm"], watt_to_dbm(400.0))
        self.assertAlmostEqual(result["worst_case_dbm"], watt_to_dbm(400.0) + 0.1)

    def test_worst_case_watt_matches_its_level(self):
        result = derive_nominal_multipactor_free_power([100.0, 100.0], "coherent-peak", _budget())
        self.assertAlmostEqual(
            result["worst_case_w"], dbm_to_watt(result["worst_case_dbm"]), places=9
        )

    def test_average_rule_lowers_the_worst_case(self):
        peak = derive_nominal_multipactor_free_power([100.0, 100.0], "coherent-peak")
        average = derive_nominal_multipactor_free_power([100.0, 100.0], "average-sum")
        self.assertGreater(peak["worst_case_dbm"], average["worst_case_dbm"])

    def test_carrier_count_is_reported(self):
        result = derive_nominal_multipactor_free_power([10.0, 10.0, 10.0], "coherent-peak")
        self.assertEqual(result["carrier_count"], 3)

    def test_invalid_rule_propagates(self):
        with self.assertRaises(ValueError):
            derive_nominal_multipactor_free_power([100.0], "peak-ish")


class TestDeclarationCheck(unittest.TestCase):
    def test_declared_above_the_worst_case_covers_it(self):
        result = verify_declared_power(58.0, 56.5)
        self.assertTrue(result["covers_worst_case"])
        self.assertAlmostEqual(result["headroom_db"], 1.5)
        self.assertAlmostEqual(result["shortfall_db"], 0.0)

    def test_declared_below_the_worst_case_reports_the_shortfall(self):
        result = verify_declared_power(55.0, 56.5)
        self.assertFalse(result["covers_worst_case"])
        self.assertAlmostEqual(result["shortfall_db"], 1.5)

    def test_exact_equality_covers_the_worst_case(self):
        self.assertTrue(verify_declared_power(56.5, 56.5)["covers_worst_case"])

    def test_one_unit_of_representation_error_below_still_covers(self):
        required = derive_nominal_multipactor_free_power(
            [100.0, 100.0], "coherent-peak", _budget()
        )["worst_case_dbm"]
        declared = math.nextafter(required, -math.inf)
        self.assertLess(declared, required)
        self.assertTrue(verify_declared_power(declared, required)["covers_worst_case"])

    def test_a_hundredth_of_a_decibel_below_does_not_cover(self):
        required = 56.5
        self.assertFalse(verify_declared_power(required - 0.01, required)["covers_worst_case"])

    def test_watt_round_trip_of_the_requirement_still_covers(self):
        required = derive_nominal_multipactor_free_power(
            [40.0, 60.0], "coherent-peak", _budget()
        )["worst_case_dbm"]
        declared = watt_to_dbm(dbm_to_watt(required))
        self.assertTrue(verify_declared_power(declared, required)["covers_worst_case"])

    def test_non_numeric_declared_power_raises(self):
        with self.assertRaises(ValueError):
            verify_declared_power("57 dBm", 56.5)


class TestRouteMargin(unittest.TestCase):
    def test_default_route_margins_resolve(self):
        self.assertAlmostEqual(
            route_margin_db("multipactor-test"), DEFAULT_ROUTE_MARGINS_DB["multipactor-test"]
        )

    def test_analysis_owes_more_than_a_test(self):
        self.assertGreater(
            route_margin_db("multipactor-analysis"), route_margin_db("multipactor-test")
        )

    def test_override_replaces_the_default(self):
        self.assertAlmostEqual(
            route_margin_db("multipactor-test", {"multipactor-test": 4.5}), 4.5
        )

    def test_override_can_add_a_project_route(self):
        self.assertAlmostEqual(route_margin_db("breadboard", {"breadboard": 10.0}), 10.0)

    def test_negative_override_raises(self):
        with self.assertRaises(ValueError):
            route_margin_db("multipactor-test", {"multipactor-test": -1.0})

    def test_unknown_route_raises(self):
        with self.assertRaises(ValueError):
            route_margin_db("gut-feel")

    def test_non_mapping_override_raises(self):
        with self.assertRaises(ValueError):
            route_margin_db("multipactor-test", [4.5])

    def test_applying_a_margin_raises_the_level(self):
        self.assertAlmostEqual(apply_power_margin(50.0, 3.0), 53.0)

    def test_zero_margin_leaves_the_level(self):
        self.assertAlmostEqual(apply_power_margin(50.0, 0.0), 50.0)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            apply_power_margin(50.0, -3.0)


class TestSpecificationAssessment(unittest.TestCase):
    def test_sound_specification_is_compliant(self):
        result = assess_nominal_power_definition(_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(
            result["demonstration_level_dbm"], 57.0 + DEFAULT_ROUTE_MARGINS_DB["multipactor-test"]
        )

    def test_demonstration_level_in_watt_matches_its_level(self):
        result = assess_nominal_power_definition(_spec())
        self.assertAlmostEqual(
            result["demonstration_level_w"], dbm_to_watt(result["demonstration_level_dbm"]),
            places=6,
        )

    def test_declared_power_below_the_worst_case_is_not_compliant(self):
        result = assess_nominal_power_definition(_spec(declared_nominal_dbm=50.0))
        self.assertFalse(result["compliant"])
        self.assertFalse(result["declaration"]["covers_worst_case"])

    def test_declaration_in_watt_is_accepted(self):
        spec = _spec()
        del spec["declared_nominal_dbm"]
        spec["declared_nominal_w"] = 500.0
        result = assess_nominal_power_definition(spec)
        self.assertAlmostEqual(result["declaration"]["declared_dbm"], watt_to_dbm(500.0))

    def test_multi_carrier_on_the_average_rule_is_flagged(self):
        result = assess_nominal_power_definition(_spec(combining_rule="average-sum"))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("in-phase envelope" in f for f in result["findings"]))

    def test_single_carrier_under_the_peak_rule_is_flagged(self):
        result = assess_nominal_power_definition(_spec(carrier_watts=[300.0]))
        self.assertTrue(any("single-carrier" in f for f in result["findings"]))

    def test_empty_budget_is_flagged(self):
        result = assess_nominal_power_definition(_spec(budget_terms=[]))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no uncertainty" in f for f in result["findings"]))

    def test_analysis_route_raises_the_demonstration_level(self):
        test_route = assess_nominal_power_definition(_spec())
        analysis_route = assess_nominal_power_definition(
            _spec(verification_route="multipactor-analysis")
        )
        self.assertGreater(
            analysis_route["demonstration_level_dbm"], test_route["demonstration_level_dbm"]
        )

    def test_peak_to_average_is_reported_for_the_carrier_set(self):
        result = assess_nominal_power_definition(_spec())
        self.assertAlmostEqual(result["peak_to_average_db"], 10.0 * math.log10(2.0))

    def test_specification_without_a_declaration_raises(self):
        spec = _spec()
        del spec["declared_nominal_dbm"]
        with self.assertRaises(ValueError):
            assess_nominal_power_definition(spec)

    def test_non_mapping_specification_raises(self):
        with self.assertRaises(ValueError):
            assess_nominal_power_definition([100.0, 100.0])

    def test_specification_without_carriers_raises(self):
        with self.assertRaises(ValueError):
            assess_nominal_power_definition({"declared_nominal_dbm": 57.0})

    def test_unknown_route_in_the_specification_raises(self):
        with self.assertRaises(ValueError):
            assess_nominal_power_definition(_spec(verification_route="hand-waving"))


if __name__ == "__main__":
    unittest.main()
