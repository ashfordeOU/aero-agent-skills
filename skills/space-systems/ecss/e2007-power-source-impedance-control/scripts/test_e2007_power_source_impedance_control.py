#!/usr/bin/env python3
"""Contract test for the clause 5.2.4 supply-impedance-control logic.

Standard library unittest only; offline and deterministic.
Run: python3 test_e2007_power_source_impedance_control.py
"""

import math
import unittest

from e2007_power_source_impedance_control_logic import (
    STABILIZED_ROLES,
    SUPPLY_ROLES,
    assess_supply_impedance_control,
    evaluate_campaign_drift,
    evaluate_frequency_sweep,
    evaluate_line_coverage,
    relative_deviation,
    stabilization_network_impedance,
    within_tolerance,
)

NETWORK = {"damping_resistance_ohm": 5.0, "series_inductance_h": 5.0e-6}


def sweep_from_model(frequencies, scale=1.0):
    """Build a sweep that tracks the modelled network by a fixed factor."""
    points = []
    for frequency in frequencies:
        modelled = stabilization_network_impedance(
            NETWORK["damping_resistance_ohm"],
            NETWORK["series_inductance_h"],
            frequency,
        )
        points.append({"frequency_hz": frequency, "measured_ohm": modelled * scale})
    return points


def good_setup():
    return {
        "lines": [
            {"id": "pwr-a", "role": "primary-supply", "stabilization_network": True},
            {"id": "pwr-b", "role": "redundant-supply", "stabilization_network": True},
            {"id": "ret-a", "role": "supply-return", "stabilization_network": True},
            {"id": "sig-ret", "role": "signal-return"},
        ],
        "network": dict(NETWORK),
        "sweep_points": sweep_from_model([1.0e4, 1.0e5, 1.0e6, 1.0e7]),
        "tolerance_fraction": 0.05,
        "checkpoints": [
            {"label": "campaign-open", "sequence": 1, "measured_ohm": 50.0},
            {"label": "mid-campaign", "sequence": 2, "measured_ohm": 50.4},
            {"label": "campaign-close", "sequence": 3, "measured_ohm": 49.7},
        ],
        "drift_tolerance_fraction": 0.02,
    }


class TestNetworkImpedance(unittest.TestCase):
    def test_impedance_at_dc_equals_damping_resistance(self):
        self.assertAlmostEqual(stabilization_network_impedance(5.0, 5.0e-6, 0.0), 5.0)

    def test_impedance_known_value_at_one_megahertz(self):
        value = stabilization_network_impedance(5.0, 5.0e-6, 1.0e6)
        reactance = 2.0 * math.pi * 1.0e6 * 5.0e-6
        self.assertAlmostEqual(value, math.sqrt(25.0 + reactance * reactance))

    def test_impedance_rises_with_frequency(self):
        low = stabilization_network_impedance(5.0, 5.0e-6, 1.0e5)
        high = stabilization_network_impedance(5.0, 5.0e-6, 1.0e7)
        self.assertGreater(high, low)

    def test_impedance_is_inductive_dominated_well_above_the_corner(self):
        value = stabilization_network_impedance(5.0, 5.0e-6, 1.0e8)
        reactance = 2.0 * math.pi * 1.0e8 * 5.0e-6
        self.assertAlmostEqual(value / reactance, 1.0, places=5)

    def test_zero_damping_resistance_is_accepted(self):
        value = stabilization_network_impedance(0.0, 5.0e-6, 1.0e6)
        self.assertAlmostEqual(value, 2.0 * math.pi * 1.0e6 * 5.0e-6)

    def test_negative_damping_resistance_rejected(self):
        with self.assertRaises(ValueError):
            stabilization_network_impedance(-1.0, 5.0e-6, 1.0e6)

    def test_non_positive_inductance_rejected(self):
        with self.assertRaises(ValueError):
            stabilization_network_impedance(5.0, 0.0, 1.0e6)

    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            stabilization_network_impedance(5.0, 5.0e-6, -1.0)

    def test_non_numeric_frequency_rejected(self):
        with self.assertRaises(ValueError):
            stabilization_network_impedance(5.0, 5.0e-6, "1 MHz")

    def test_infinite_inductance_rejected(self):
        with self.assertRaises(ValueError):
            stabilization_network_impedance(5.0, float("inf"), 1.0e6)


class TestDeviationAndTolerance(unittest.TestCase):
    def test_deviation_is_zero_for_an_exact_match(self):
        self.assertAlmostEqual(relative_deviation(50.0, 50.0), 0.0)

    def test_deviation_is_symmetric_in_sign(self):
        self.assertAlmostEqual(relative_deviation(55.0, 50.0), 0.1)
        self.assertAlmostEqual(relative_deviation(45.0, 50.0), 0.1)

    def test_deviation_rejects_non_positive_reference(self):
        with self.assertRaises(ValueError):
            relative_deviation(50.0, 0.0)

    def test_deviation_rejects_negative_measurement(self):
        with self.assertRaises(ValueError):
            relative_deviation(-1.0, 50.0)

    def test_tolerance_band_accepts_an_inside_point(self):
        self.assertTrue(within_tolerance(51.0, 50.0, 0.05))

    def test_tolerance_band_rejects_an_outside_point(self):
        self.assertFalse(within_tolerance(60.0, 50.0, 0.05))

    def test_exact_boundary_case_survives_representation_error(self):
        measured = 3.3 * 1.05
        self.assertGreater(relative_deviation(measured, 3.3), 0.05)
        self.assertTrue(within_tolerance(measured, 3.3, 0.05))

    def test_a_real_exceedance_is_not_absorbed(self):
        self.assertFalse(within_tolerance(3.3 * 1.0500001, 3.3, 0.05))

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            within_tolerance(50.0, 50.0, -0.01)

    def test_tolerance_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            within_tolerance(50.0, 50.0, 1.5)


class TestLineCoverage(unittest.TestCase):
    def test_all_source_conductors_stabilized(self):
        result = evaluate_line_coverage(good_setup()["lines"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(sorted(result["stabilized"]), ["pwr-a", "pwr-b", "ret-a"])

    def test_uncovered_source_conductor_is_flagged(self):
        lines = good_setup()["lines"]
        lines[1] = {"id": "pwr-b", "role": "redundant-supply"}
        result = evaluate_line_coverage(lines)
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["finding"], "no-stabilization-network")

    def test_de_energized_conductor_is_exempt_not_flagged(self):
        lines = [
            {"id": "pwr-a", "role": "primary-supply", "stabilization_network": True},
            {"id": "pwr-b", "role": "redundant-supply", "energized": False},
        ]
        result = evaluate_line_coverage(lines)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["exempt"][0]["reason"], "conductor-de-energized")

    def test_reference_conductor_role_is_exempt(self):
        result = evaluate_line_coverage(
            [
                {"id": "pwr-a", "role": "primary-supply", "stabilization_network": True},
                {"id": "bond", "role": "chassis-bond"},
            ]
        )
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["exempt"][0]["reason"], "role-not-a-source")

    def test_unrecognized_role_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_line_coverage([{"id": "x", "role": "umbilical"}])

    def test_duplicate_conductor_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_line_coverage(
                [
                    {"id": "pwr-a", "role": "primary-supply"},
                    {"id": "pwr-a", "role": "supply-return"},
                ]
            )

    def test_missing_conductor_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_line_coverage([{"role": "primary-supply"}])

    def test_empty_conductor_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_line_coverage([])

    def test_every_stabilized_role_is_a_known_role(self):
        for role in STABILIZED_ROLES:
            self.assertIn(role, SUPPLY_ROLES)


class TestFrequencySweep(unittest.TestCase):
    def test_sweep_tracking_the_model_is_within_tolerance(self):
        result = evaluate_frequency_sweep(
            dict(NETWORK), sweep_from_model([1.0e4, 1.0e6]), 0.05
        )
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["points"]), 2)

    def test_sweep_point_outside_the_band_is_flagged(self):
        points = sweep_from_model([1.0e4, 1.0e6])
        points[1]["measured_ohm"] *= 1.4
        result = evaluate_frequency_sweep(dict(NETWORK), points, 0.05)
        self.assertEqual(len(result["findings"]), 1)
        self.assertAlmostEqual(result["findings"][0]["deviation"], 0.4)

    def test_modelled_impedance_is_reported_per_point(self):
        result = evaluate_frequency_sweep(
            dict(NETWORK), sweep_from_model([1.0e6]), 0.05
        )
        self.assertAlmostEqual(
            result["points"][0]["modelled_ohm"],
            stabilization_network_impedance(5.0, 5.0e-6, 1.0e6),
        )

    def test_non_increasing_sweep_frequency_rejected(self):
        points = [
            {"frequency_hz": 1.0e6, "measured_ohm": 31.8},
            {"frequency_hz": 1.0e6, "measured_ohm": 31.8},
        ]
        with self.assertRaises(ValueError):
            evaluate_frequency_sweep(dict(NETWORK), points, 0.05)

    def test_empty_sweep_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_frequency_sweep(dict(NETWORK), [], 0.05)

    def test_network_missing_inductance_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_frequency_sweep(
                {"damping_resistance_ohm": 5.0}, sweep_from_model([1.0e6]), 0.05
            )

    def test_sweep_point_missing_measurement_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_frequency_sweep(dict(NETWORK), [{"frequency_hz": 1.0e6}], 0.05)


class TestCampaignDrift(unittest.TestCase):
    def test_stable_campaign_reports_no_finding(self):
        result = evaluate_campaign_drift(good_setup()["checkpoints"], 0.02)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["baseline_ohm"], 50.0)

    def test_drifted_checkpoint_is_flagged(self):
        checkpoints = good_setup()["checkpoints"]
        checkpoints[2]["measured_ohm"] = 60.0
        result = evaluate_campaign_drift(checkpoints, 0.02)
        self.assertEqual(len(result["findings"]), 1)
        self.assertAlmostEqual(result["findings"][0]["drift"], 0.2)

    def test_drift_is_measured_against_the_opening_baseline(self):
        checkpoints = [
            {"label": "open", "sequence": 1, "measured_ohm": 50.0},
            {"label": "mid", "sequence": 2, "measured_ohm": 52.5},
        ]
        result = evaluate_campaign_drift(checkpoints, 0.10)
        self.assertAlmostEqual(result["checkpoints"][0]["drift"], 0.05)

    def test_single_checkpoint_cannot_demonstrate_stability(self):
        with self.assertRaises(ValueError):
            evaluate_campaign_drift(
                [{"label": "open", "sequence": 1, "measured_ohm": 50.0}], 0.02
            )

    def test_non_increasing_checkpoint_sequence_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_campaign_drift(
                [
                    {"label": "open", "sequence": 2, "measured_ohm": 50.0},
                    {"label": "close", "sequence": 1, "measured_ohm": 50.0},
                ],
                0.02,
            )

    def test_checkpoint_missing_reading_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_campaign_drift(
                [
                    {"label": "open", "sequence": 1, "measured_ohm": 50.0},
                    {"label": "close", "sequence": 2},
                ],
                0.02,
            )

    def test_non_positive_baseline_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_campaign_drift(
                [
                    {"label": "open", "sequence": 1, "measured_ohm": 0.0},
                    {"label": "close", "sequence": 2, "measured_ohm": 50.0},
                ],
                0.02,
            )


class TestCampaignAssessment(unittest.TestCase):
    def test_clean_campaign_is_compliant(self):
        result = assess_supply_impedance_control(good_setup())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_findings_from_every_stage_are_aggregated(self):
        setup = good_setup()
        setup["lines"][0] = {"id": "pwr-a", "role": "primary-supply"}
        setup["sweep_points"][2]["measured_ohm"] *= 2.0
        setup["checkpoints"][1]["measured_ohm"] = 70.0
        result = assess_supply_impedance_control(setup)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 3)

    def test_missing_setup_section_rejected(self):
        setup = good_setup()
        del setup["checkpoints"]
        with self.assertRaises(ValueError):
            assess_supply_impedance_control(setup)

    def test_setup_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_supply_impedance_control(["lines"])


if __name__ == "__main__":
    unittest.main()
