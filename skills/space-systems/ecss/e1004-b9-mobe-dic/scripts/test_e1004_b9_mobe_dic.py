#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C Annex B.9 Mobius/Directional
Intensity Change (DIC) geomagnetic transmission model.

Exercises scripts/e1004_b9_mobe_dic_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the vertical cutoff follows
Cst*cos^4(latitude) and rejects an out-of-range latitude; the directional
(DIC) cutoff equals the vertical cutoff at zenith angle 0 regardless of
azimuth, exceeds it toward geomagnetic east (azimuth 90) and falls below it
toward geomagnetic west (azimuth 270), growing in magnitude toward the
horizon, and rejects an out-of-range zenith angle or east-west amplitude;
transmission probability is 0 at/below the penumbra's lower edge, 1 at/above
its upper edge, ramps linearly between, and rejects a negative rigidity/
cutoff or an out-of-range penumbra fraction; classification maps those
probabilities to forbidden/penumbra/allowed; transmitted flux sums
flux-weighted-by-probability across a spectrum and rejects a negative
rigidity or flux; the worst-case direction is the horizon-grazing
due-geomagnetic-west direction and yields the analytic minimum cutoff; and
a case review flags a worst-case-required case only when its evaluated
direction is not at least as conservative as that worst case.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_b9_mobe_dic_logic as dic  # noqa: E402


class VerticalCutoffRigidityTest(unittest.TestCase):
    def test_equator_is_full_stormer_constant(self):
        self.assertAlmostEqual(
            dic.vertical_cutoff_rigidity_gv(0.0), dic.STORMER_CUTOFF_CONSTANT_GV
        )

    def test_pole_is_zero(self):
        self.assertAlmostEqual(dic.vertical_cutoff_rigidity_gv(90.0), 0.0)
        self.assertAlmostEqual(dic.vertical_cutoff_rigidity_gv(-90.0), 0.0)

    def test_monotonic_decrease_with_latitude_magnitude(self):
        low_lat = dic.vertical_cutoff_rigidity_gv(20.0)
        high_lat = dic.vertical_cutoff_rigidity_gv(60.0)
        self.assertGreater(low_lat, high_lat)

    def test_symmetric_in_hemisphere(self):
        self.assertAlmostEqual(
            dic.vertical_cutoff_rigidity_gv(30.0), dic.vertical_cutoff_rigidity_gv(-30.0)
        )

    def test_latitude_above_range_raises(self):
        with self.assertRaises(ValueError):
            dic.vertical_cutoff_rigidity_gv(91.0)

    def test_latitude_below_range_raises(self):
        with self.assertRaises(ValueError):
            dic.vertical_cutoff_rigidity_gv(-91.0)


class DirectionalCutoffRigidityTest(unittest.TestCase):
    def test_zenith_zero_matches_vertical_regardless_of_azimuth(self):
        vertical = dic.vertical_cutoff_rigidity_gv(40.0)
        for azimuth in (0.0, 90.0, 180.0, 270.0):
            with self.subTest(azimuth=azimuth):
                self.assertAlmostEqual(
                    dic.directional_cutoff_rigidity_gv(40.0, 0.0, azimuth), vertical
                )

    def test_east_raises_cutoff_above_vertical(self):
        vertical = dic.vertical_cutoff_rigidity_gv(40.0)
        east = dic.directional_cutoff_rigidity_gv(40.0, 90.0, dic.EAST_AZIMUTH_DEG)
        self.assertGreater(east, vertical)

    def test_west_lowers_cutoff_below_vertical(self):
        vertical = dic.vertical_cutoff_rigidity_gv(40.0)
        west = dic.directional_cutoff_rigidity_gv(40.0, 90.0, dic.WEST_AZIMUTH_DEG)
        self.assertLess(west, vertical)

    def test_effect_grows_toward_horizon(self):
        near_vertical = dic.directional_cutoff_rigidity_gv(40.0, 10.0, dic.WEST_AZIMUTH_DEG)
        near_horizon = dic.directional_cutoff_rigidity_gv(40.0, 89.0, dic.WEST_AZIMUTH_DEG)
        vertical = dic.vertical_cutoff_rigidity_gv(40.0)
        self.assertLess(vertical - near_horizon, vertical)  # sanity: still finite
        self.assertGreater(vertical - near_horizon, vertical - near_vertical)

    def test_zenith_below_range_raises(self):
        with self.assertRaises(ValueError):
            dic.directional_cutoff_rigidity_gv(40.0, -1.0, 90.0)

    def test_zenith_above_range_raises(self):
        with self.assertRaises(ValueError):
            dic.directional_cutoff_rigidity_gv(40.0, 91.0, 90.0)

    def test_amplitude_at_upper_bound_raises(self):
        with self.assertRaises(ValueError):
            dic.directional_cutoff_rigidity_gv(40.0, 90.0, 90.0, east_west_amplitude=1.0)

    def test_amplitude_negative_raises(self):
        with self.assertRaises(ValueError):
            dic.directional_cutoff_rigidity_gv(40.0, 90.0, 90.0, east_west_amplitude=-0.1)


class TransmissionProbabilityTest(unittest.TestCase):
    def test_at_or_below_lower_edge_is_zero(self):
        self.assertEqual(dic.transmission_probability(9.0, 10.0, 0.1), 0.0)
        self.assertEqual(dic.transmission_probability(0.0, 10.0, 0.1), 0.0)

    def test_at_or_above_upper_edge_is_one(self):
        self.assertEqual(dic.transmission_probability(11.0, 10.0, 0.1), 1.0)
        self.assertEqual(dic.transmission_probability(100.0, 10.0, 0.1), 1.0)

    def test_midpoint_is_half(self):
        self.assertAlmostEqual(dic.transmission_probability(10.0, 10.0, 0.1), 0.5)

    def test_ramp_is_linear(self):
        # lower=9.0, upper=11.0; 9.5 -> 0.25 of the way up.
        self.assertAlmostEqual(dic.transmission_probability(9.5, 10.0, 0.1), 0.25)

    def test_negative_rigidity_raises(self):
        with self.assertRaises(ValueError):
            dic.transmission_probability(-1.0, 10.0, 0.1)

    def test_negative_cutoff_raises(self):
        with self.assertRaises(ValueError):
            dic.transmission_probability(1.0, -10.0, 0.1)

    def test_penumbra_fraction_zero_raises(self):
        with self.assertRaises(ValueError):
            dic.transmission_probability(1.0, 10.0, 0.0)

    def test_penumbra_fraction_at_one_raises(self):
        with self.assertRaises(ValueError):
            dic.transmission_probability(1.0, 10.0, 1.0)


class ClassifyTransmissionTest(unittest.TestCase):
    def test_below_penumbra_is_forbidden(self):
        self.assertEqual(dic.classify_transmission(1.0, 10.0, 0.1), dic.FORBIDDEN)

    def test_above_penumbra_is_allowed(self):
        self.assertEqual(dic.classify_transmission(20.0, 10.0, 0.1), dic.ALLOWED)

    def test_inside_penumbra_is_penumbra(self):
        self.assertEqual(dic.classify_transmission(10.0, 10.0, 0.1), dic.PENUMBRA)


class DirectionalIntensityChangeTest(unittest.TestCase):
    def test_returns_expected_keys_and_consistent_category(self):
        result = dic.directional_intensity_change(30.0, 40.0, 90.0, dic.WEST_AZIMUTH_DEG)
        self.assertEqual(
            set(result), {"cutoff_rigidity_gv", "transmission_probability", "category"}
        )
        recomputed = dic.classify_transmission(30.0, result["cutoff_rigidity_gv"])
        self.assertEqual(result["category"], recomputed)


class TransmittedFluxTest(unittest.TestCase):
    def test_sums_flux_weighted_by_probability(self):
        spectrum = [
            {"rigidity_gv": 1.0, "flux": 100.0},  # far below any reasonable cutoff
            {"rigidity_gv": 1000.0, "flux": 5.0},  # far above -> fully transmitted
        ]
        total = dic.transmitted_flux(spectrum, 40.0, 0.0, 0.0)
        self.assertAlmostEqual(total, 5.0)

    def test_empty_spectrum_is_zero(self):
        self.assertEqual(dic.transmitted_flux([], 40.0, 0.0, 0.0), 0.0)

    def test_negative_rigidity_in_spectrum_raises(self):
        with self.assertRaises(ValueError):
            dic.transmitted_flux([{"rigidity_gv": -1.0, "flux": 1.0}], 40.0, 0.0, 0.0)

    def test_negative_flux_in_spectrum_raises(self):
        with self.assertRaises(ValueError):
            dic.transmitted_flux([{"rigidity_gv": 1.0, "flux": -1.0}], 40.0, 0.0, 0.0)


class WorstCaseDirectionCutoffTest(unittest.TestCase):
    def test_is_horizon_grazing_due_west(self):
        worst_case = dic.worst_case_direction_cutoff(40.0)
        self.assertEqual(worst_case["zenith_angle_deg"], dic.HORIZON_ZENITH_DEG)
        self.assertEqual(
            worst_case["azimuth_from_geomagnetic_north_deg"], dic.WEST_AZIMUTH_DEG
        )

    def test_is_analytic_minimum_over_sampled_directions(self):
        worst_case = dic.worst_case_direction_cutoff(40.0)
        for zenith in (0.0, 30.0, 60.0, 90.0):
            for azimuth in (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0):
                sampled = dic.directional_cutoff_rigidity_gv(40.0, zenith, azimuth)
                self.assertGreaterEqual(sampled, worst_case["cutoff_rigidity_gv"] - 1e-9)


class DirectionCaseReviewTest(unittest.TestCase):
    def test_worst_case_direction_case_has_no_findings(self):
        case = {
            "case_id": "see-case-1",
            "geomagnetic_latitude_deg": 40.0,
            "particle_rigidity_gv": 5.0,
            "zenith_angle_deg": dic.HORIZON_ZENITH_DEG,
            "azimuth_from_geomagnetic_north_deg": dic.WEST_AZIMUTH_DEG,
            "worst_case_required": True,
        }
        review = dic.direction_case_review(case)
        self.assertEqual(review["findings"], [])
        self.assertTrue(dic.is_direction_case_compliant(review))

    def test_non_worst_case_direction_flagged_when_required(self):
        case = {
            "case_id": "see-case-2",
            "geomagnetic_latitude_deg": 40.0,
            "particle_rigidity_gv": 5.0,
            "zenith_angle_deg": 0.0,
            "azimuth_from_geomagnetic_north_deg": 0.0,
            "worst_case_required": True,
        }
        review = dic.direction_case_review(case)
        self.assertEqual(len(review["findings"]), 1)
        self.assertEqual(review["findings"][0]["issue"], "non_worst_case_direction_used")
        self.assertFalse(dic.is_direction_case_compliant(review))

    def test_non_worst_case_direction_not_flagged_when_not_required(self):
        case = {
            "case_id": "dose-case-1",
            "geomagnetic_latitude_deg": 40.0,
            "particle_rigidity_gv": 5.0,
            "zenith_angle_deg": 0.0,
            "azimuth_from_geomagnetic_north_deg": 0.0,
            "worst_case_required": False,
        }
        review = dic.direction_case_review(case)
        self.assertEqual(review["findings"], [])
        self.assertTrue(dic.is_direction_case_compliant(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
