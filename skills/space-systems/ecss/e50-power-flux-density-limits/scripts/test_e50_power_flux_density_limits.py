"""Contract tests for the clause 5.6.12.4 power flux density limit logic."""

import unittest

from e50_power_flux_density_limits_logic import (
    DEFAULT_LIMIT_SCHEDULE,
    LIMIT_EXCEEDED,
    MARGIN_SHORT,
    WITHIN_LIMIT,
    assess_pfd,
    assess_pfd_profile,
    bandwidth_referral_db,
    normalize_limit_schedule,
    pfd_at_surface_dbw_per_m2,
    pfd_limit_dbw_per_m2,
    refer_to_reference_bandwidth,
    spreading_loss_db,
    validate_bandwidth,
    validate_elevation,
)

REFERENCE_BW = 4000.0


class ValidationTests(unittest.TestCase):
    def test_horizon_accepted(self):
        self.assertAlmostEqual(validate_elevation(0.0), 0.0, places=9)

    def test_zenith_accepted(self):
        self.assertAlmostEqual(validate_elevation(90.0), 90.0, places=9)

    def test_angle_beyond_zenith_rejected(self):
        with self.assertRaises(ValueError):
            validate_elevation(90.5)

    def test_negative_angle_rejected(self):
        with self.assertRaises(ValueError):
            validate_elevation(-1.0)

    def test_boolean_angle_rejected(self):
        with self.assertRaises(ValueError):
            validate_elevation(True)

    def test_zero_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            validate_bandwidth(0.0)


class ScheduleTests(unittest.TestCase):
    def test_schedule_is_sorted_by_angle(self):
        points = normalize_limit_schedule([(25.0, -140.0), (0.0, -150.0)])
        self.assertAlmostEqual(points[0][0], 0.0, places=9)

    def test_single_breakpoint_schedule_rejected(self):
        with self.assertRaises(ValueError):
            normalize_limit_schedule([(0.0, -150.0)])

    def test_duplicate_angles_rejected(self):
        with self.assertRaises(ValueError):
            normalize_limit_schedule([(5.0, -150.0), (5.0, -140.0)])

    def test_mapping_breakpoints_accepted(self):
        points = normalize_limit_schedule(
            [
                {"arrival_angle_deg": 0.0, "limit_dbw_per_m2": -150.0},
                {"arrival_angle_deg": 25.0, "limit_dbw_per_m2": -140.0},
            ]
        )
        self.assertEqual(len(points), 2)

    def test_limit_on_the_low_plateau(self):
        self.assertAlmostEqual(pfd_limit_dbw_per_m2(2.0), -150.0, places=9)

    def test_limit_exactly_at_the_transition_start(self):
        self.assertAlmostEqual(pfd_limit_dbw_per_m2(5.0), -150.0, places=9)

    def test_limit_is_interpolated_through_the_transition(self):
        self.assertAlmostEqual(pfd_limit_dbw_per_m2(15.0), -145.0, places=9)

    def test_limit_exactly_at_the_transition_end(self):
        self.assertAlmostEqual(pfd_limit_dbw_per_m2(25.0), -140.0, places=9)

    def test_limit_on_the_high_plateau(self):
        self.assertAlmostEqual(pfd_limit_dbw_per_m2(90.0), -140.0, places=9)

    def test_the_default_schedule_spans_horizon_to_zenith(self):
        points = normalize_limit_schedule(DEFAULT_LIMIT_SCHEDULE)
        self.assertAlmostEqual(points[0][0], 0.0, places=9)
        self.assertAlmostEqual(points[-1][0], 90.0, places=9)
        self.assertAlmostEqual(points[0][1], -150.0, places=9)

    def test_an_overriding_schedule_displaces_the_default(self):
        tight = [(0.0, -160.0), (90.0, -160.0)]
        self.assertAlmostEqual(pfd_limit_dbw_per_m2(15.0, tight), -160.0, places=9)


class SpreadingTests(unittest.TestCase):
    def test_doubling_the_range_costs_six_decibels(self):
        delta = spreading_loss_db(2000.0) - spreading_loss_db(1000.0)
        self.assertAlmostEqual(delta, 6.020599913279624, places=9)

    def test_spreading_loss_at_a_kilometre(self):
        self.assertAlmostEqual(spreading_loss_db(1000.0), 70.99209864022097, places=6)

    def test_flux_is_eirp_less_the_spreading(self):
        flux = pfd_at_surface_dbw_per_m2(10.0, 1000.0)
        self.assertAlmostEqual(flux, -60.99209864022097, places=6)

    def test_zero_range_rejected(self):
        with self.assertRaises(ValueError):
            spreading_loss_db(0.0)


class BandwidthReferralTests(unittest.TestCase):
    def test_measurement_in_the_reference_bandwidth_needs_no_correction(self):
        self.assertAlmostEqual(bandwidth_referral_db(4000.0, 4000.0), 0.0, places=9)

    def test_narrower_measurement_needs_no_correction(self):
        self.assertAlmostEqual(bandwidth_referral_db(1000.0, 4000.0), 0.0, places=9)

    def test_ten_times_wider_measurement_sheds_ten_decibels(self):
        self.assertAlmostEqual(bandwidth_referral_db(40000.0, 4000.0), -10.0, places=9)

    def test_referral_is_applied_to_the_flux_density(self):
        referred = refer_to_reference_bandwidth(-145.0, 40000.0, 4000.0)
        self.assertAlmostEqual(referred, -155.0, places=9)

    def test_zero_reference_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            bandwidth_referral_db(4000.0, 0.0)


class AssessPfdTests(unittest.TestCase):
    def test_comfortable_observation_is_within_limit(self):
        result = assess_pfd(
            {
                "pfd_dbw_per_m2": -160.0,
                "measured_bandwidth_hz": 4000.0,
                "arrival_angle_deg": 0.0,
            },
            REFERENCE_BW,
        )
        self.assertEqual(result["verdict"], WITHIN_LIMIT)
        self.assertAlmostEqual(result["margin_db"], 10.0, places=9)

    def test_observation_exactly_on_the_limit_is_compliant_but_thin(self):
        result = assess_pfd(
            {
                "pfd_dbw_per_m2": -150.0,
                "measured_bandwidth_hz": 4000.0,
                "arrival_angle_deg": 0.0,
            },
            REFERENCE_BW,
        )
        self.assertAlmostEqual(result["margin_db"], 0.0, places=9)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], MARGIN_SHORT)

    def test_observation_over_the_limit_is_reported(self):
        result = assess_pfd(
            {
                "pfd_dbw_per_m2": -145.0,
                "measured_bandwidth_hz": 4000.0,
                "arrival_angle_deg": 0.0,
            },
            REFERENCE_BW,
        )
        self.assertEqual(result["verdict"], LIMIT_EXCEEDED)
        self.assertFalse(result["compliant"])

    def test_referral_brings_a_wide_band_measurement_under_the_limit(self):
        result = assess_pfd(
            {
                "pfd_dbw_per_m2": -145.0,
                "measured_bandwidth_hz": 40000.0,
                "arrival_angle_deg": 0.0,
            },
            REFERENCE_BW,
        )
        self.assertAlmostEqual(result["bandwidth_referral_db"], -10.0, places=9)
        self.assertAlmostEqual(result["referred_pfd_dbw_per_m2"], -155.0, places=9)
        self.assertEqual(result["verdict"], WITHIN_LIMIT)

    def test_the_same_flux_passes_at_high_elevation_and_fails_at_the_horizon(self):
        low = assess_pfd(
            {
                "pfd_dbw_per_m2": -145.0,
                "measured_bandwidth_hz": 4000.0,
                "arrival_angle_deg": 0.0,
            },
            REFERENCE_BW,
        )
        high = assess_pfd(
            {
                "pfd_dbw_per_m2": -145.0,
                "measured_bandwidth_hz": 4000.0,
                "arrival_angle_deg": 25.0,
            },
            REFERENCE_BW,
        )
        self.assertEqual(low["verdict"], LIMIT_EXCEEDED)
        self.assertEqual(high["verdict"], WITHIN_LIMIT)

    def test_observation_missing_the_arrival_angle_rejected(self):
        with self.assertRaises(ValueError):
            assess_pfd(
                {"pfd_dbw_per_m2": -150.0, "measured_bandwidth_hz": 4000.0},
                REFERENCE_BW,
            )

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            assess_pfd(
                {
                    "pfd_dbw_per_m2": -160.0,
                    "measured_bandwidth_hz": 4000.0,
                    "arrival_angle_deg": 0.0,
                },
                REFERENCE_BW,
                required_margin_db=-1.0,
            )


class ProfileTests(unittest.TestCase):
    PROFILE = [
        {
            "pfd_dbw_per_m2": -152.0,
            "measured_bandwidth_hz": 4000.0,
            "arrival_angle_deg": 0.0,
        },
        {
            "pfd_dbw_per_m2": -148.0,
            "measured_bandwidth_hz": 4000.0,
            "arrival_angle_deg": 25.0,
        },
    ]

    def test_a_clean_profile_is_within_limit(self):
        result = assess_pfd_profile(self.PROFILE, REFERENCE_BW)
        self.assertEqual(result["verdict"], WITHIN_LIMIT)
        self.assertTrue(result["compliant"])

    def test_the_governing_angle_is_not_the_highest_flux(self):
        result = assess_pfd_profile(self.PROFILE, REFERENCE_BW)
        self.assertAlmostEqual(result["governing_angle_deg"], 0.0, places=9)
        self.assertAlmostEqual(result["worst_margin_db"], 2.0, places=9)

    def test_an_exceedance_anywhere_governs_the_profile(self):
        profile = list(self.PROFILE) + [
            {
                "pfd_dbw_per_m2": -130.0,
                "measured_bandwidth_hz": 4000.0,
                "arrival_angle_deg": 45.0,
            }
        ]
        result = assess_pfd_profile(profile, REFERENCE_BW)
        self.assertEqual(result["verdict"], LIMIT_EXCEEDED)
        self.assertEqual(result["exceedance_count"], 1)

    def test_findings_quantify_the_overshoot(self):
        profile = list(self.PROFILE) + [
            {
                "pfd_dbw_per_m2": -130.0,
                "measured_bandwidth_hz": 4000.0,
                "arrival_angle_deg": 45.0,
            }
        ]
        result = assess_pfd_profile(profile, REFERENCE_BW)
        self.assertTrue(any("over the limit" in f for f in result["findings"]))

    def test_a_thin_margin_is_its_own_verdict(self):
        profile = [
            {
                "pfd_dbw_per_m2": -150.5,
                "measured_bandwidth_hz": 4000.0,
                "arrival_angle_deg": 0.0,
            }
        ]
        result = assess_pfd_profile(profile, REFERENCE_BW)
        self.assertEqual(result["verdict"], MARGIN_SHORT)
        self.assertTrue(result["compliant"])

    def test_empty_profile_rejected(self):
        with self.assertRaises(ValueError):
            assess_pfd_profile([], REFERENCE_BW)

    def test_non_list_profile_rejected(self):
        with self.assertRaises(ValueError):
            assess_pfd_profile(self.PROFILE[0], REFERENCE_BW)


if __name__ == "__main__":
    unittest.main()
