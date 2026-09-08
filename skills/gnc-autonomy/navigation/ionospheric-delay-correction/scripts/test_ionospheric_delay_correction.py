"""Contract test for ionospheric-delay-correction (gnc-autonomy/navigation).

Exercises the SKILL.md Workflow steps: step 1 (earth-centred angle and the
subionospheric point), step 2 (pierce-point geomagnetic latitude and local
time of day), step 3 (amplitude and period broadcast-alpha-beta-coefficient
polynomials), step 4 (day-curve shape and vertical delay), step 5
(elevation obliquity factor and slant delay via the klobuchar-broadcast-
model pipeline), and step 6 (metre conversion). Stdlib unittest, offline,
deterministic. No exact-float equality on computed sums; all numeric
asserts use assertAlmostEqual or math.isclose.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ionospheric_delay_correction_logic as iono

ALPHA_EX = [0.8382e-08, -0.7451e-08, -0.5960e-07, 0.1192e-06]
BETA_EX = [0.1306e+06, -0.3277e+05, -0.6554e+05, 0.1311e+06]
LAT_EX = 40.0
LON_EX = -105.0
EL_EX = 40.0
AZ_EX = 160.0
TOW_EX = 0.0


class TestIonosphericDelayCorrection(unittest.TestCase):
    """Worked-example anchors and boundary behavior of the Klobuchar pierce-point pipeline."""

    def test_step1_earth_center_angle(self):
        """Step 1 of the SKILL.md workflow: the earth-centred angle to the pierce point."""
        psi = iono.earth_center_angle_deg(EL_EX)
        self.assertAlmostEqual(psi, 3.46274247491639, delta=1e-6)

    def test_step1_subionospheric_point(self):
        """Step 1 of the SKILL.md workflow: the subionospheric point from user geometry."""
        lat_i, lon_i = iono.subionospheric_point_deg(LAT_EX, LON_EX, EL_EX, AZ_EX)
        self.assertTrue(math.isclose(lat_i, 36.7460864486391, rel_tol=1e-6))
        self.assertTrue(math.isclose(lon_i, -103.521982351049, rel_tol=1e-6))

    def test_step2_geomagnetic_latitude(self):
        """Step 2 of the SKILL.md workflow: pierce-point geomagnetic latitude phi_m."""
        phi_m = iono.geomagnetic_latitude_deg(36.7460864486391, -103.521982351049)
        self.assertTrue(math.isclose(phi_m, 46.2306740519375, rel_tol=1e-6))

    def test_step2_local_time(self):
        """Step 2 of the SKILL.md workflow: local time of day at the pierce point."""
        t_local = iono.local_time_seconds(-103.521982351049, 0.0)
        self.assertTrue(math.isclose(t_local, 61554.7242357482, rel_tol=1e-6))

    def test_step3_amplitude(self):
        """Step 3 of the SKILL.md workflow: amplitude broadcast-alpha-coefficient polynomial."""
        amp = iono.amplitude_seconds(ALPHA_EX, 46.2306740519375)
        self.assertTrue(math.isclose(amp, 4.55630181644608e-09, rel_tol=1e-6))

    def test_step3_period(self):
        """Step 3 of the SKILL.md workflow: period broadcast-beta-coefficient polynomial."""
        per = iono.period_seconds(BETA_EX, 46.2306740519375)
        self.assertTrue(math.isclose(per, 120081.223784471, rel_tol=1e-6))

    def test_step4_day_shape_factor(self):
        """Step 4 of the SKILL.md workflow: day-curve shape about the 14:00 local-time peak."""
        c = iono.day_shape_factor(61554.7242357482, 120081.223784471)
        self.assertTrue(math.isclose(c, 0.834503142819751, rel_tol=1e-6))

    def test_step4_vertical_delay(self):
        """Step 4 of the SKILL.md workflow: vertical delay from the 5 ns base and the day shape."""
        t_vert = iono.vertical_delay_seconds(
            ALPHA_EX, BETA_EX, 46.2306740519375, 61554.7242357482
        )
        self.assertTrue(math.isclose(t_vert, 8.80224818545959e-09, rel_tol=1e-6))

    def test_step5_slant_factor(self):
        """Step 5 of the SKILL.md workflow: elevation obliquity factor F."""
        f_val = iono.slant_factor(EL_EX)
        self.assertTrue(math.isclose(f_val, 1.48179972565158, rel_tol=1e-6))

    def test_step5_slant_delay_seconds(self):
        """Step 5 of the SKILL.md workflow: full slant-delay-correction pipeline in seconds."""
        t_slant = iono.slant_delay_seconds(
            ALPHA_EX, BETA_EX, LAT_EX, LON_EX, EL_EX, AZ_EX, TOW_EX
        )
        self.assertTrue(math.isclose(t_slant, 1.30431689463311e-08, rel_tol=1e-6))

    def test_step6_slant_delay_meters_identity(self):
        """Step 6 of the SKILL.md workflow: metre conversion equals seconds times c."""
        t_slant = iono.slant_delay_seconds(
            ALPHA_EX, BETA_EX, LAT_EX, LON_EX, EL_EX, AZ_EX, TOW_EX
        )
        d_m = iono.slant_delay_meters(ALPHA_EX, BETA_EX, LAT_EX, LON_EX, EL_EX, AZ_EX, TOW_EX)
        self.assertTrue(math.isclose(d_m, 3.910244, rel_tol=1e-5))
        self.assertTrue(math.isclose(d_m, t_slant * iono.C_LIGHT, rel_tol=1e-12))

    def test_elevation_sweep_slant_delay_factor_and_meters(self):
        """Step 5 of the SKILL.md workflow: elevation sweep exercises the pierce-point-geometry shift."""
        expected = {
            10.0: (2.52683707319819e-08, 2.745010, 7.575267),
            30.0: (1.58796414198594e-08, 1.788741, 4.760597),
            40.0: (1.30431689463311e-08, 1.481800, 3.910244),
            60.0: (9.82787591714463e-09, 1.128000, 2.946323),
            90.0: (8.64857899766712e-09, 1.000593, 2.592779),
        }
        prior_m = None
        for el_deg in (10.0, 30.0, 40.0, 60.0, 90.0):
            expected_t_slant, expected_f, expected_m = expected[el_deg]
            t_slant = iono.slant_delay_seconds(ALPHA_EX, BETA_EX, LAT_EX, LON_EX, el_deg, AZ_EX, TOW_EX)
            self.assertTrue(math.isclose(t_slant, expected_t_slant, rel_tol=1e-6))
            self.assertTrue(math.isclose(iono.slant_factor(el_deg), expected_f, rel_tol=1e-5))
            m_val = iono.slant_delay_meters(ALPHA_EX, BETA_EX, LAT_EX, LON_EX, el_deg, AZ_EX, TOW_EX)
            self.assertTrue(math.isclose(m_val, expected_m, rel_tol=1e-5))
            if prior_m is not None:
                self.assertGreater(prior_m, m_val)
            prior_m = m_val

    def test_obliquity_zenith_closed_form(self):
        """Obliquity identity: slant_factor(90) equals the closed form 1 + 2*(6/90)^3."""
        f90 = iono.slant_factor(90.0)
        self.assertAlmostEqual(f90, 1.00059259259259, delta=1e-12)
        self.assertAlmostEqual(f90, 1.0 + 2.0 * (6.0 / 90.0) ** 3, delta=1e-12)

    def test_obliquity_monotone_bounds_and_low_elevation_limit(self):
        """Obliquity identity: F is strictly decreasing in elevation, bounded on (0, 90], and approaches its supremum as el -> 0+."""
        f10 = iono.slant_factor(10.0)
        f90 = iono.slant_factor(90.0)
        self.assertGreater(f10, f90)
        supremum = 1.0 + 2.0 * (96.0 / 90.0) ** 3
        self.assertAlmostEqual(supremum, 3.4272592592592593, delta=1e-12)
        for el_deg in (0.5, 1.0, 5.0, 20.0, 50.0, 90.0):
            f_val = iono.slant_factor(el_deg)
            self.assertGreater(f_val, 1.00059259259259 - 1e-12)
            self.assertLessEqual(f_val, supremum + 1e-12)
        f_near_zero = iono.slant_factor(0.0001)
        self.assertAlmostEqual(f_near_zero, supremum, delta=1e-4)

    def test_zenith_slant_to_vertical_ratio(self):
        """Zenith limit: at elevation 90 the slant-to-vertical ratio equals F(90)."""
        lat_i, lon_i = iono.subionospheric_point_deg(LAT_EX, LON_EX, 90.0, AZ_EX)
        phi_m = iono.geomagnetic_latitude_deg(lat_i, lon_i)
        t_local = iono.local_time_seconds(lon_i, TOW_EX)
        t_vert = iono.vertical_delay_seconds(ALPHA_EX, BETA_EX, phi_m, t_local)
        t_slant = iono.slant_delay_seconds(ALPHA_EX, BETA_EX, LAT_EX, LON_EX, 90.0, AZ_EX, TOW_EX)
        ratio = t_slant / t_vert
        self.assertAlmostEqual(ratio, iono.slant_factor(90.0), delta=1e-12)

    def test_peak_identity(self):
        """Peak identity: at t_local 50400 the day shape is 1.0 and T_vert is the 5 ns base plus A."""
        phi_m = 46.2306740519375
        shape = iono.day_shape_factor(50400.0, 120081.223784471)
        self.assertAlmostEqual(shape, 1.0, delta=1e-12)
        t_vert = iono.vertical_delay_seconds(ALPHA_EX, BETA_EX, phi_m, 50400.0)
        amp = iono.amplitude_seconds(ALPHA_EX, phi_m)
        self.assertTrue(math.isclose(t_vert, iono.T_BASE + amp, rel_tol=1e-12))
        self.assertTrue(math.isclose(amp, 4.55630181644608e-09, rel_tol=1e-6))

    def test_night_floor(self):
        """Night floor: at t_local 3600 the shape is 0.0 and T_vert equals exactly the 5 ns base."""
        phi_m = 46.2306740519375
        shape = iono.day_shape_factor(3600.0, 120081.223784471)
        self.assertEqual(shape, 0.0)
        t_vert = iono.vertical_delay_seconds(ALPHA_EX, BETA_EX, phi_m, 3600.0)
        self.assertTrue(math.isclose(t_vert, 5e-9, rel_tol=0.0, abs_tol=1e-20))

    def test_geomagnetic_equator_polynomial_collapse(self):
        """Polynomial collapse: at phi_m 0 the amplitude and period equal their constant terms."""
        amp0 = iono.amplitude_seconds(ALPHA_EX, 0.0)
        per0 = iono.period_seconds(BETA_EX, 0.0)
        self.assertTrue(math.isclose(amp0, ALPHA_EX[0], rel_tol=1e-15))
        self.assertTrue(math.isclose(per0, BETA_EX[0], rel_tol=1e-15))

    def test_amplitude_clamp_to_zero(self):
        """Model clamp: a negative raw amplitude clamps to 0.0 (not an error)."""
        amp = iono.amplitude_seconds([1.0e-9, -1.0e-8, 0.0, 0.0], 60.0)
        self.assertEqual(amp, 0.0)

    def test_period_clamp_to_minimum(self):
        """Model clamp: a raw period below 72000 s clamps to the 72000 s minimum."""
        per = iono.period_seconds([70000.0, 0.0, 0.0, 0.0], 10.0)
        self.assertEqual(per, 72000.0)

    def test_day_shape_bounds_over_range(self):
        """Shape bounds: day_shape_factor stays in [0, 1] over the whole local-time range."""
        for t_local in (0.0, 10000.0, 30000.0, 50400.0, 61554.72, 80000.0, 86399.0):
            c = iono.day_shape_factor(t_local, 120081.223784471)
            self.assertGreaterEqual(c, 0.0)
            self.assertLessEqual(c, 1.0 + 1e-12)

    def test_longitude_normalization(self):
        """Longitude normalization: the wrapped pierce point stays in [-180, 180) and matches the unwrap identity."""
        lat_i, lon_i = iono.subionospheric_point_deg(0.0, 179.0, 5.0, 90.0)
        self.assertGreaterEqual(lon_i, -180.0)
        self.assertLess(lon_i, 180.0)
        self.assertTrue(math.isclose(lon_i, -167.061612903226, rel_tol=1e-9, abs_tol=1e-9))
        unwrapped = lon_i + 360.0
        self.assertTrue(math.isclose(lon_i, unwrapped - 360.0, rel_tol=0.0, abs_tol=1e-12))
        iono.local_time_seconds(lon_i, 0.0)

    def test_determinism_slant_and_vertical_delay(self):
        """Determinism: two identical slant_delay_seconds and vertical_delay_seconds calls are bitwise identical."""
        a = iono.slant_delay_seconds(ALPHA_EX, BETA_EX, LAT_EX, LON_EX, EL_EX, AZ_EX, TOW_EX)
        b = iono.slant_delay_seconds(ALPHA_EX, BETA_EX, LAT_EX, LON_EX, EL_EX, AZ_EX, TOW_EX)
        self.assertEqual(a, b)
        c = iono.vertical_delay_seconds(ALPHA_EX, BETA_EX, 46.2306740519375, 61554.7242357482)
        d = iono.vertical_delay_seconds(ALPHA_EX, BETA_EX, 46.2306740519375, 61554.7242357482)
        self.assertEqual(c, d)

    def test_value_errors_earth_center_angle_and_slant_factor(self):
        """ValueError rejection: elevation at 0, -5, 90.1 and nan on both elevation-only functions."""
        for bad_el in (0.0, -5.0, 90.1, float("nan")):
            with self.assertRaises(ValueError):
                iono.earth_center_angle_deg(bad_el)
            with self.assertRaises(ValueError):
                iono.slant_factor(bad_el)

    def test_value_errors_subionospheric_point(self):
        """ValueError rejection: user latitude, longitude and azimuth out of range."""
        with self.assertRaises(ValueError):
            iono.subionospheric_point_deg(90.5, LON_EX, EL_EX, AZ_EX)
        with self.assertRaises(ValueError):
            iono.subionospheric_point_deg(-91.0, LON_EX, EL_EX, AZ_EX)
        with self.assertRaises(ValueError):
            iono.subionospheric_point_deg(LAT_EX, 181.0, EL_EX, AZ_EX)
        with self.assertRaises(ValueError):
            iono.subionospheric_point_deg(LAT_EX, LON_EX, EL_EX, 360.0)
        with self.assertRaises(ValueError):
            iono.subionospheric_point_deg(LAT_EX, LON_EX, EL_EX, -1.0)

    def test_value_errors_local_time(self):
        """ValueError rejection: GPS time of week at 604800 and -1 on local_time_seconds."""
        with self.assertRaises(ValueError):
            iono.local_time_seconds(LON_EX, 604800.0)
        with self.assertRaises(ValueError):
            iono.local_time_seconds(LON_EX, -1.0)

    def test_value_errors_geomagnetic_latitude(self):
        """ValueError rejection: subionospheric latitude 95 and longitude 181 on geomagnetic_latitude_deg."""
        with self.assertRaises(ValueError):
            iono.geomagnetic_latitude_deg(95.0, LON_EX)
        with self.assertRaises(ValueError):
            iono.geomagnetic_latitude_deg(LAT_EX, 181.0)

    def test_value_errors_amplitude(self):
        """ValueError rejection: alpha of length 3, a nan entry and a negative alpha0."""
        with self.assertRaises(ValueError):
            iono.amplitude_seconds([1.0, 2.0, 3.0], 46.0)
        with self.assertRaises(ValueError):
            iono.amplitude_seconds([1.0, float("nan"), 0.0, 0.0], 46.0)
        with self.assertRaises(ValueError):
            iono.amplitude_seconds([-0.5e-08, 0.0, 0.0, 0.0], 46.0)

    def test_value_errors_period(self):
        """ValueError rejection: a negative beta0 constant period coefficient."""
        with self.assertRaises(ValueError):
            iono.period_seconds([-1000.0, 0.0, 0.0, 0.0], 46.0)

    def test_value_errors_phi_m_bounds(self):
        """ValueError rejection: geomagnetic latitude at 91 and -91 on both polynomial functions."""
        with self.assertRaises(ValueError):
            iono.amplitude_seconds(ALPHA_EX, 91.0)
        with self.assertRaises(ValueError):
            iono.amplitude_seconds(ALPHA_EX, -91.0)
        with self.assertRaises(ValueError):
            iono.period_seconds(BETA_EX, 91.0)
        with self.assertRaises(ValueError):
            iono.period_seconds(BETA_EX, -91.0)

    def test_value_errors_day_shape_factor(self):
        """ValueError rejection: t_local at 86400 and -1, and period at 0 on day_shape_factor."""
        with self.assertRaises(ValueError):
            iono.day_shape_factor(86400.0, 120000.0)
        with self.assertRaises(ValueError):
            iono.day_shape_factor(-1.0, 120000.0)
        with self.assertRaises(ValueError):
            iono.day_shape_factor(50000.0, 0.0)

    def test_value_error_delay_meters(self):
        """ValueError rejection: a negative delay on delay_meters."""
        with self.assertRaises(ValueError):
            iono.delay_meters(-1.0)

    def test_full_pipeline_rejection(self):
        """Full-pipeline rejection: every invalid input (elevation, latitude, azimuth, tow, coefficients) propagates through slant_delay_seconds."""
        with self.assertRaises(ValueError):
            iono.slant_delay_seconds(ALPHA_EX, BETA_EX, LAT_EX, LON_EX, 0.0, AZ_EX, TOW_EX)
        with self.assertRaises(ValueError):
            iono.slant_delay_seconds(ALPHA_EX, BETA_EX, 90.5, LON_EX, EL_EX, 360.0, TOW_EX)
        with self.assertRaises(ValueError):
            iono.slant_delay_seconds(ALPHA_EX, BETA_EX, LAT_EX, LON_EX, EL_EX, AZ_EX, 604800.0)
        with self.assertRaises(ValueError):
            iono.slant_delay_seconds([-1.0e-8] + ALPHA_EX[1:], BETA_EX, LAT_EX, LON_EX, EL_EX, AZ_EX, TOW_EX)
        with self.assertRaises(ValueError):
            iono.slant_delay_seconds(ALPHA_EX, BETA_EX[:3], LAT_EX, LON_EX, EL_EX, AZ_EX, TOW_EX)

    def test_physical_sanity_primary_scenario(self):
        """Physical sanity: vertical and slant delay of the primary scenario fall in the spec bounds."""
        t_vert = iono.vertical_delay_seconds(ALPHA_EX, BETA_EX, 46.2306740519375, 61554.7242357482)
        t_slant = iono.slant_delay_seconds(ALPHA_EX, BETA_EX, LAT_EX, LON_EX, EL_EX, AZ_EX, TOW_EX)
        t_slant_m = iono.delay_meters(t_slant)
        self.assertGreaterEqual(t_vert, 5e-9)
        self.assertLessEqual(t_vert, 2e-8)
        self.assertGreaterEqual(t_slant, 1e-8)
        self.assertLessEqual(t_slant, 4e-8)
        self.assertGreaterEqual(t_slant_m, 2.0)
        self.assertLessEqual(t_slant_m, 8.0)

    def test_vertical_delay_never_below_base(self):
        """Physical sanity: vertical delay never falls below the 5e-9 s base at any valid input."""
        for t_local in (0.0, 3600.0, 25000.0, 50400.0, 70000.0, 86399.0):
            t_vert = iono.vertical_delay_seconds(ALPHA_EX, BETA_EX, 46.2306740519375, t_local)
            self.assertGreaterEqual(t_vert, 5e-9 - 1e-20)


if __name__ == "__main__":
    unittest.main()
