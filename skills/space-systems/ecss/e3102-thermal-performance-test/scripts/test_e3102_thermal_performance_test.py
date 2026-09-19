#!/usr/bin/env python3
"""Contract test for the two-phase thermal performance test (offline)."""

import copy
import unittest

from e3102_thermal_performance_test_logic import (
    DEFAULT_STEADY_RATE_LIMIT_K_PER_MIN,
    assess_regulation,
    assess_start_up,
    assess_steady_state,
    capability_at_temperature_w,
    grade_capability_utilisation,
    grade_mapping_point,
    mapping_coverage,
    run_thermal_performance_test,
    temperature_drop_k,
    transport_conductance_w_per_k,
    transported_power_w,
    validate_capability_curve,
)

CURVE = [(273.0, 100.0), (293.0, 140.0), (313.0, 160.0)]

GOOD_POINT = {
    "applied_power_w": 62.0,
    "parasitic_loss_w": 2.0,
    "evaporator_temp_k": 296.0,
    "condenser_temp_k": 293.0,
    "drift_k_per_min": 0.02,
}

CAMPAIGN = {
    "capability_curve": CURVE,
    "points": [
        dict(GOOD_POINT),
        {
            "applied_power_w": 102.0,
            "parasitic_loss_w": 2.0,
            "evaporator_temp_k": 298.0,
            "condenser_temp_k": 293.0,
            "drift_k_per_min": 0.05,
        },
    ],
    "required_cells": [(62.0, 293.0), (102.0, 293.0)],
    "max_drop_k": 8.0,
    "start_up": {
        "initial_temperature_k": 253.0,
        "time_to_transport_s": 240.0,
        "time_limit_s": 600.0,
        "transport_established": True,
    },
    "regulation": {
        "setpoint_k": 293.0,
        "band_k": 1.0,
        "samples_k": [292.6, 293.2, 293.0, 292.9],
    },
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class TransportedPowerTests(unittest.TestCase):
    def test_parasitic_leak_is_subtracted(self):
        self.assertAlmostEqual(transported_power_w(62.0, 2.0), 60.0, places=9)

    def test_no_leak_leaves_the_applied_power(self):
        self.assertAlmostEqual(transported_power_w(45.0), 45.0, places=9)

    def test_leak_equal_to_the_applied_power_rejected(self):
        with self.assertRaises(ValueError):
            transported_power_w(40.0, 40.0)

    def test_negative_leak_rejected(self):
        with self.assertRaises(ValueError):
            transported_power_w(40.0, -1.0)

    def test_non_numeric_applied_power_rejected(self):
        with self.assertRaises(ValueError):
            transported_power_w("62 W", 2.0)


class TemperatureDropTests(unittest.TestCase):
    def test_drop_is_the_evaporator_minus_condenser(self):
        self.assertAlmostEqual(temperature_drop_k(296.0, 293.0), 3.0, places=9)

    def test_equal_ends_give_a_zero_drop(self):
        self.assertAlmostEqual(temperature_drop_k(293.0, 293.0), 0.0, places=9)

    def test_reversed_transport_direction_rejected(self):
        with self.assertRaises(ValueError):
            temperature_drop_k(290.0, 296.0)

    def test_conductance_is_power_over_drop(self):
        self.assertAlmostEqual(
            transport_conductance_w_per_k(60.0, 3.0), 20.0, places=9
        )

    def test_zero_drop_conductance_rejected(self):
        with self.assertRaises(ValueError):
            transport_conductance_w_per_k(60.0, 0.0)


class CapabilityCurveTests(unittest.TestCase):
    def test_valid_curve_is_returned_cleaned(self):
        self.assertEqual(len(validate_capability_curve(CURVE)), 3)

    def test_single_point_curve_rejected(self):
        with self.assertRaises(ValueError):
            validate_capability_curve([(293.0, 140.0)])

    def test_non_monotonic_curve_rejected(self):
        with self.assertRaises(ValueError):
            validate_capability_curve([(293.0, 140.0), (273.0, 100.0)])

    def test_capability_on_a_declared_node(self):
        self.assertAlmostEqual(
            capability_at_temperature_w(CURVE, 293.0), 140.0, places=9
        )

    def test_capability_interpolates_between_nodes(self):
        self.assertAlmostEqual(
            capability_at_temperature_w(CURVE, 283.0), 120.0, places=9
        )

    def test_capability_at_the_upper_end_of_the_span(self):
        self.assertAlmostEqual(
            capability_at_temperature_w(CURVE, 313.0), 160.0, places=9
        )

    def test_temperature_below_the_span_refuses_to_extrapolate(self):
        with self.assertRaises(ValueError):
            capability_at_temperature_w(CURVE, 250.0)

    def test_temperature_above_the_span_refuses_to_extrapolate(self):
        with self.assertRaises(ValueError):
            capability_at_temperature_w(CURVE, 340.0)


class UtilisationGradingTests(unittest.TestCase):
    def test_comfortable_point_is_within_capability(self):
        result = grade_capability_utilisation(60.0, 140.0)
        self.assertEqual(result["grade"], "within-capability")

    def test_point_exactly_on_the_capability_is_at_capability(self):
        result = grade_capability_utilisation(140.0, 140.0)
        self.assertEqual(result["grade"], "at-capability")
        self.assertAlmostEqual(result["utilisation"], 1.0, places=9)

    def test_point_over_the_capability_is_beyond_capability(self):
        result = grade_capability_utilisation(150.0, 140.0)
        self.assertEqual(result["grade"], "beyond-capability")

    def test_zero_capability_rejected(self):
        with self.assertRaises(ValueError):
            grade_capability_utilisation(60.0, 0.0)


class SteadyStateTests(unittest.TestCase):
    def test_slow_drift_is_steady(self):
        self.assertTrue(assess_steady_state(0.02)["steady"])

    def test_drift_exactly_on_the_limit_is_steady(self):
        result = assess_steady_state(DEFAULT_STEADY_RATE_LIMIT_K_PER_MIN)
        self.assertAlmostEqual(
            result["drift_k_per_min"], DEFAULT_STEADY_RATE_LIMIT_K_PER_MIN, places=9
        )
        self.assertTrue(result["steady"])

    def test_fast_drift_is_not_steady(self):
        self.assertEqual(assess_steady_state(0.9)["verdict"], "not-steady")

    def test_negative_drift_is_taken_on_magnitude(self):
        self.assertTrue(assess_steady_state(-0.03)["steady"])

    def test_non_numeric_drift_rejected(self):
        with self.assertRaises(ValueError):
            assess_steady_state("slow")


class MappingPointTests(unittest.TestCase):
    def test_good_point_is_accepted(self):
        result = grade_mapping_point(GOOD_POINT, CURVE)
        self.assertTrue(result["accepted"])
        self.assertAlmostEqual(result["transported_power_w"], 60.0, places=9)
        self.assertAlmostEqual(result["conductance_w_per_k"], 20.0, places=9)

    def test_point_beyond_the_capability_is_rejected(self):
        point = _case(GOOD_POINT, applied_power_w=162.0)
        result = grade_mapping_point(point, CURVE)
        self.assertEqual(result["grade"], "beyond-capability")
        self.assertFalse(result["accepted"])

    def test_unsettled_point_is_rejected(self):
        point = _case(GOOD_POINT, drift_k_per_min=1.5)
        result = grade_mapping_point(point, CURVE)
        self.assertFalse(result["steady"])
        self.assertFalse(result["accepted"])

    def test_drop_over_the_allowance_is_reported(self):
        point = _case(GOOD_POINT, evaporator_temp_k=305.0)
        result = grade_mapping_point(point, CURVE, max_drop_k=8.0)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("temperature drop" in note for note in result["findings"]))

    def test_isothermal_point_reports_an_unresolvable_conductance(self):
        point = _case(GOOD_POINT, evaporator_temp_k=293.0)
        result = grade_mapping_point(point, CURVE)
        self.assertIsNone(result["conductance_w_per_k"])
        self.assertTrue(any("not resolvable" in note for note in result["findings"]))

    def test_point_without_an_applied_power_rejected(self):
        point = _case(GOOD_POINT)
        del point["applied_power_w"]
        with self.assertRaises(ValueError):
            grade_mapping_point(point, CURVE)


class CoverageTests(unittest.TestCase):
    def test_every_required_cell_is_covered(self):
        result = mapping_coverage(CAMPAIGN["points"], CAMPAIGN["required_cells"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])

    def test_a_cell_never_run_is_reported_missing(self):
        result = mapping_coverage(
            CAMPAIGN["points"], CAMPAIGN["required_cells"] + [(140.0, 313.0)]
        )
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing"], [(140.0, 313.0)])

    def test_empty_required_matrix_rejected(self):
        with self.assertRaises(ValueError):
            mapping_coverage(CAMPAIGN["points"], [])

    def test_malformed_cell_rejected(self):
        with self.assertRaises(ValueError):
            mapping_coverage(CAMPAIGN["points"], [(62.0,)])


class StartUpTests(unittest.TestCase):
    def test_start_up_inside_the_limit_is_demonstrated(self):
        result = assess_start_up(CAMPAIGN["start_up"])
        self.assertTrue(result["demonstrated"])
        self.assertEqual(result["verdict"], "start-up-demonstrated")

    def test_start_up_exactly_on_the_limit_is_demonstrated(self):
        start_up = _case(CAMPAIGN["start_up"], time_to_transport_s=600.0)
        result = assess_start_up(start_up)
        self.assertAlmostEqual(result["time_to_transport_s"], 600.0, places=9)
        self.assertTrue(result["demonstrated"])

    def test_slow_start_up_is_reported(self):
        start_up = _case(CAMPAIGN["start_up"], time_to_transport_s=900.0)
        self.assertEqual(assess_start_up(start_up)["verdict"], "start-up-too-slow")

    def test_transport_never_established_is_not_demonstrated(self):
        start_up = _case(CAMPAIGN["start_up"], transport_established=False)
        result = assess_start_up(start_up)
        self.assertEqual(result["verdict"], "start-up-not-demonstrated")
        self.assertIsNone(result["time_to_transport_s"])

    def test_non_boolean_establishment_flag_rejected(self):
        start_up = _case(CAMPAIGN["start_up"], transport_established="yes")
        with self.assertRaises(ValueError):
            assess_start_up(start_up)


class RegulationTests(unittest.TestCase):
    def test_regulation_inside_the_band_is_held(self):
        result = assess_regulation(CAMPAIGN["regulation"])
        self.assertTrue(result["held"])
        self.assertEqual(result["samples"], 4)

    def test_deviation_exactly_on_the_band_is_held(self):
        regulation = _case(
            CAMPAIGN["regulation"], samples_k=[292.0, 293.0, 294.0, 293.0]
        )
        result = assess_regulation(regulation)
        self.assertAlmostEqual(result["worst_deviation_k"], 1.0, places=9)
        self.assertTrue(result["held"])

    def test_excursion_outside_the_band_is_reported(self):
        regulation = _case(CAMPAIGN["regulation"], samples_k=[293.0, 296.5])
        result = assess_regulation(regulation)
        self.assertEqual(result["verdict"], "regulation-exceeded")
        self.assertFalse(result["held"])

    def test_single_sample_rejected(self):
        regulation = _case(CAMPAIGN["regulation"], samples_k=[293.0])
        with self.assertRaises(ValueError):
            assess_regulation(regulation)

    def test_zero_band_rejected(self):
        regulation = _case(CAMPAIGN["regulation"], band_k=0.0)
        with self.assertRaises(ValueError):
            assess_regulation(regulation)


class CampaignTests(unittest.TestCase):
    def test_complete_campaign_is_demonstrated(self):
        result = run_thermal_performance_test(CAMPAIGN)
        self.assertEqual(result["verdict"], "performance-demonstrated")
        self.assertTrue(result["demonstrated"])
        self.assertEqual(result["accepted_points"], 2)
        self.assertEqual(result["findings"], [])

    def test_missing_start_up_blocks_the_verdict(self):
        campaign = _case(CAMPAIGN)
        del campaign["start_up"]
        result = run_thermal_performance_test(campaign)
        self.assertFalse(result["demonstrated"])
        self.assertTrue(any("start-up" in note for note in result["findings"]))

    def test_missing_regulation_blocks_the_verdict(self):
        campaign = _case(CAMPAIGN)
        del campaign["regulation"]
        result = run_thermal_performance_test(campaign)
        self.assertEqual(result["verdict"], "performance-not-demonstrated")

    def test_uncovered_cell_blocks_the_verdict(self):
        campaign = _case(
            CAMPAIGN, required_cells=CAMPAIGN["required_cells"] + [(140.0, 313.0)]
        )
        result = run_thermal_performance_test(campaign)
        self.assertFalse(result["coverage"]["complete"])
        self.assertFalse(result["demonstrated"])

    def test_worst_utilisation_is_reported(self):
        result = run_thermal_performance_test(CAMPAIGN)
        self.assertAlmostEqual(result["worst_utilisation"], 100.0 / 140.0, places=9)

    def test_campaign_without_points_rejected(self):
        campaign = _case(CAMPAIGN, points=[])
        with self.assertRaises(ValueError):
            run_thermal_performance_test(campaign)

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            run_thermal_performance_test("campaign")


if __name__ == "__main__":
    unittest.main()
