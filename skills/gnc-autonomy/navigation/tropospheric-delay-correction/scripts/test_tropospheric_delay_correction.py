"""Contract test for tropospheric-delay-correction (gnc-autonomy/navigation).

Exercises the SKILL.md Workflow steps: step 1 (saturation and water-vapour
partial pressure from the Magnus form), step 2 (the gravity/height
factor), step 3 (the zenith-hydrostatic-delay), step 4 (the zenith-wet-
delay), step 5 (the zenith total delay), step 6 (the cosecant elevation-
mapping-function), and step 7 (the slant-tropospheric-delay via the
saastamoinen-model pipeline). Stdlib unittest, offline, deterministic.
No exact-float equality on computed sums; all numeric asserts use
assertAlmostEqual or math.isclose.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tropospheric_delay_correction_logic as tropo

P_EX = 1013.25
T_EX = 288.15
RH_EX = 50.0
PHI_EX = 40.0
H_EX = 0.0
EL_EX = 30.0
E_EX = 8.5083601202965298

SWEEP = [
    (10.0, 13.784328232455502, 5.7587704831436337),
    (15.0, 9.2482509429728381, 3.8637033051562737),
    (20.0, 6.9984868571016552, 2.9238044001630876),
    (30.0, 4.7872469558574346, 2.0000000000000004),
    (45.0, 3.3850947857014484, 1.4142135623730951),
    (60.0, 2.7639183186415059, 1.1547005383792517),
    (90.0, 2.3936234779287169, 1.0),
]

LAT_H_ROWS = [
    (0.0, 0.0, 0.997340000000, 2.313323691018),
    (40.0, 0.0, 0.999538095847, 2.308236433994),
    (45.0, 0.0, 1.000000000000, 2.307170250000),
    (90.0, 0.0, 1.002660000000, 2.301049458441),
    (45.0, 1.0, 0.999720000000, 2.307816438603),
    (45.0, 5.0, 0.998600000000, 2.310404816743),
]


class TestTroposphericDelayCorrection(unittest.TestCase):
    """Worked-example anchors and boundary behavior of the Saastamoinen pipeline."""

    def test_step1_saturation_vapor_pressure(self):
        """Step 1 of the SKILL.md workflow: the Magnus saturation vapour pressure."""
        es = tropo.saturation_vapor_pressure_hpa(T_EX)
        self.assertTrue(math.isclose(es, 17.01672024059306, rel_tol=1e-6))

    def test_step1_water_vapor_pressure(self):
        """Step 1 of the SKILL.md workflow: the water-vapour partial pressure from humidity."""
        e = tropo.water_vapor_pressure_hpa(T_EX, RH_EX)
        self.assertTrue(math.isclose(e, E_EX, rel_tol=1e-6))

    def test_step2_gravity_factor(self):
        """Step 2 of the SKILL.md workflow: the gravity and height factor f(phi, H)."""
        f = tropo.gravity_factor(PHI_EX, H_EX)
        self.assertTrue(math.isclose(f, 0.99953809584740594, rel_tol=1e-6))

    def test_step3_zenith_hydrostatic_delay(self):
        """Step 3 of the SKILL.md workflow: the zenith-hydrostatic-delay ZHD."""
        zhd = tropo.zenith_hydrostatic_delay_m(P_EX, PHI_EX, H_EX)
        self.assertTrue(math.isclose(zhd, 2.3082364339940309, rel_tol=1e-6))

    def test_step4_zenith_wet_delay(self):
        """Step 4 of the SKILL.md workflow: the zenith-wet-delay ZWD."""
        zwd = tropo.zenith_wet_delay_m(E_EX, T_EX, PHI_EX, H_EX)
        self.assertTrue(math.isclose(zwd, 0.085387043934685852, rel_tol=1e-6))

    def test_step5_zenith_total_delay(self):
        """Step 5 of the SKILL.md workflow: the zenith total delay ZTD = ZHD + ZWD."""
        ztd = tropo.zenith_total_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX)
        self.assertTrue(math.isclose(ztd, 2.3936234779287169, rel_tol=1e-6))

    def test_step6_elevation_mapping_factor(self):
        """Step 6 of the SKILL.md workflow: the cosecant elevation-mapping-function m(E)."""
        m = tropo.slant_mapping_factor(30.0)
        self.assertTrue(math.isclose(m, 2.0000000000000004, rel_tol=1e-6))

    def test_step7_slant_hydrostatic_delay(self):
        """Step 7 of the SKILL.md workflow: the slant hydrostatic delay ZHD * m(E)."""
        sh = tropo.slant_hydrostatic_delay_m(P_EX, PHI_EX, H_EX, EL_EX)
        self.assertTrue(math.isclose(sh, 4.6164728679880627, rel_tol=1e-6))

    def test_step7_slant_wet_delay(self):
        """Step 7 of the SKILL.md workflow: the slant wet delay ZWD * m(E)."""
        sw = tropo.slant_wet_delay_m(E_EX, T_EX, PHI_EX, H_EX, EL_EX)
        self.assertTrue(math.isclose(sw, 0.17077408786937173, rel_tol=1e-6))

    def test_step7_slant_total_delay(self):
        """Step 7 of the SKILL.md workflow: the full saastamoinen-model slant-tropospheric-delay."""
        st = tropo.slant_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX, EL_EX)
        self.assertTrue(math.isclose(st, 4.7872469558574346, rel_tol=1e-6))

    def test_slant_equals_mapping_times_zenith_total(self):
        """Step 7 mapping identity: slant total delay equals m(E) * ZTD (SKILL.md workflow)."""
        st = tropo.slant_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX, EL_EX)
        m = tropo.slant_mapping_factor(EL_EX)
        ztd = tropo.zenith_total_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX)
        self.assertTrue(math.isclose(st, m * ztd, rel_tol=1e-12))

    def test_elevation_sweep_anchors(self):
        """Elevation sweep of step 6/7: slant total delay and mapping factor at each row."""
        for el_deg, expected_slant, expected_m in SWEEP:
            slant = tropo.slant_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX, el_deg)
            m = tropo.slant_mapping_factor(el_deg)
            self.assertTrue(math.isclose(slant, expected_slant, rel_tol=1e-6))
            self.assertTrue(math.isclose(m, expected_m, rel_tol=1e-6))

    def test_elevation_sweep_monotone(self):
        """Elevation sweep: slant total delay is monotone decreasing across the sweep rows."""
        slants = [
            tropo.slant_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX, el_deg)
            for el_deg, _, _ in SWEEP
        ]
        for earlier, later in zip(slants, slants[1:]):
            self.assertGreater(earlier, later)

    def test_zenith_row_equals_zenith_total(self):
        """Sweep zenith row: slant at 90 deg equals zenith_total_delay_m within 1e-12 (m(90) = 1)."""
        slant_90 = tropo.slant_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX, 90.0)
        ztd = tropo.zenith_total_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX)
        self.assertTrue(math.isclose(slant_90, ztd, rel_tol=1e-12))

    def test_mapping_factor_at_zenith(self):
        """Step 6 mapping identity: slant_mapping_factor(90) = 1.0 within 1e-12."""
        self.assertAlmostEqual(tropo.slant_mapping_factor(90.0), 1.0, delta=1e-12)

    def test_mapping_cosecant_identity(self):
        """Step 6 mapping identity: m(E) * sin(E) = 1.0 within 1e-12 (cosecant by definition)."""
        m = tropo.slant_mapping_factor(30.0)
        self.assertAlmostEqual(m * math.sin(math.radians(30.0)), 1.0, delta=1e-12)

    def test_mapping_factor_strictly_decreasing(self):
        """Step 6: the elevation-mapping-function is strictly decreasing on (0, 90]."""
        m60 = tropo.slant_mapping_factor(60.0)
        m30 = tropo.slant_mapping_factor(30.0)
        m10 = tropo.slant_mapping_factor(10.0)
        self.assertLess(m60, m30)
        self.assertLess(m30, m10)

    def test_mapping_factor_minimum_at_zenith(self):
        """Step 6: slant_mapping_factor(90) is the minimum over (0, 90]."""
        m90 = tropo.slant_mapping_factor(90.0)
        for el_deg in (1.0, 10.0, 30.0, 60.0, 89.0):
            self.assertGreater(tropo.slant_mapping_factor(el_deg), m90)

    def test_gravity_factor_at_45_deg(self):
        """Step 2 identity: gravity_factor(45, 0) = 1.0 within 1e-12 (cos(80 deg... cos(90)=0)."""
        self.assertAlmostEqual(tropo.gravity_factor(45.0, 0.0), 1.0, delta=1e-12)

    def test_gravity_factor_equator_and_pole(self):
        """Step 2 identity: gravity_factor at the equator and pole equal 1 -/+ 0.00266."""
        f_eq = tropo.gravity_factor(0.0, 0.0)
        f_pole = tropo.gravity_factor(90.0, 0.0)
        self.assertTrue(math.isclose(f_eq, 0.99734, rel_tol=1e-15))
        self.assertTrue(math.isclose(f_pole, 1.00266, rel_tol=1e-15))

    def test_gravity_factor_height_slope(self):
        """Step 2 identity: gravity_factor is linear in height, slope -0.00028 per km."""
        diff = tropo.gravity_factor(45.0, 1.0) - tropo.gravity_factor(45.0, 0.0)
        self.assertAlmostEqual(diff, -0.00028, delta=1e-12)

    def test_gravity_factor_stays_positive_over_window(self):
        """Step 2: the gravity/height factor stays inside (0.99, 1.01) over the valid window."""
        for phi_deg in (-90.0, -45.0, 0.0, 45.0, 90.0):
            for h_km in (-1.0, 0.0, 10.0):
                f = tropo.gravity_factor(phi_deg, h_km)
                self.assertGreater(f, 0.99)
                self.assertLess(f, 1.01)

    def test_latitude_height_variation_anchors(self):
        """Latitude/height variation table: f and ZHD anchors at P = 1013.25 hPa."""
        for phi_deg, h_km, expected_f, expected_zhd in LAT_H_ROWS:
            f = tropo.gravity_factor(phi_deg, h_km)
            zhd = tropo.zenith_hydrostatic_delay_m(P_EX, phi_deg, h_km)
            self.assertTrue(math.isclose(f, expected_f, rel_tol=1e-6))
            self.assertTrue(math.isclose(zhd, expected_zhd, rel_tol=1e-6))

    def test_zenith_hydrostatic_f_equals_one_collapse(self):
        """Step 3 closed form: at f = 1 (phi=45, H=0), ZHD = 0.002277 * P exactly within 1e-12."""
        zhd = tropo.zenith_hydrostatic_delay_m(1000.0, 45.0, 0.0)
        self.assertTrue(math.isclose(zhd, 2.277, rel_tol=1e-12))

    def test_zenith_hydrostatic_linear_in_pressure(self):
        """Step 3: ZHD scales linearly in P (ZHD(2P) = 2 * ZHD(P)) within 1e-12."""
        zhd_1000 = tropo.zenith_hydrostatic_delay_m(1000.0, 40.0, 0.5)
        zhd_500 = tropo.zenith_hydrostatic_delay_m(500.0, 40.0, 0.5)
        self.assertTrue(math.isclose(zhd_1000, 2.0 * zhd_500, rel_tol=1e-12))

    def test_zenith_wet_linear_in_partial_pressure(self):
        """Step 4: ZWD scales linearly in e (ZWD(e/2) = ZWD(e)/2) within 1e-12."""
        e_half = tropo.water_vapor_pressure_hpa(T_EX, RH_EX / 2.0)
        zwd_half = tropo.zenith_wet_delay_m(e_half, T_EX, PHI_EX, H_EX)
        zwd_full = tropo.zenith_wet_delay_m(E_EX, T_EX, PHI_EX, H_EX)
        self.assertTrue(math.isclose(zwd_half, zwd_full / 2.0, rel_tol=1e-12))

    def test_zenith_wet_zero_at_zero_partial_pressure(self):
        """Step 4: ZWD(e = 0) = 0 exactly (isclose with abs_tol 1e-15)."""
        zwd = tropo.zenith_wet_delay_m(0.0, T_EX, PHI_EX, H_EX)
        self.assertTrue(math.isclose(zwd, 0.0, abs_tol=1e-15))

    def test_zenith_total_equals_sum_of_components(self):
        """Step 5: ZTD equals the sum of ZHD and ZWD within 1e-15 relative."""
        zhd = tropo.zenith_hydrostatic_delay_m(P_EX, PHI_EX, H_EX)
        zwd = tropo.zenith_wet_delay_m(E_EX, T_EX, PHI_EX, H_EX)
        ztd = tropo.zenith_total_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX)
        self.assertTrue(math.isclose(ztd, zhd + zwd, rel_tol=1e-15))

    def test_wet_factor_shape(self):
        """Step 4: the wet factor (1255/T + 0.05) matches the real anchor and decreases in T."""
        wet_factor_ex = tropo.WET_T_NUM / T_EX + tropo.WET_T_C
        self.assertTrue(math.isclose(wet_factor_ex, 4.4053704667707789, rel_tol=1e-12))
        wet_200 = tropo.WET_T_NUM / 200.0 + tropo.WET_T_C
        wet_340 = tropo.WET_T_NUM / 340.0 + tropo.WET_T_C
        self.assertGreater(wet_200, wet_340)

    def test_dry_wet_share_at_worked_scenario(self):
        """Physical sanity: ZWD is between 2 and 6 percent of ZHD at the worked scenario."""
        zhd = tropo.zenith_hydrostatic_delay_m(P_EX, PHI_EX, H_EX)
        zwd = tropo.zenith_wet_delay_m(E_EX, T_EX, PHI_EX, H_EX)
        ratio = zwd / zhd
        self.assertGreater(ratio, 0.02)
        self.assertLess(ratio, 0.06)

    def test_physical_sanity_windows_worked_scenario(self):
        """Physical sanity: ZHD, ZWD, ZTD and the two slant totals fall in their magnitude bounds."""
        zhd = tropo.zenith_hydrostatic_delay_m(P_EX, PHI_EX, H_EX)
        zwd = tropo.zenith_wet_delay_m(E_EX, T_EX, PHI_EX, H_EX)
        ztd = tropo.zenith_total_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX)
        slant_30 = tropo.slant_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX, 30.0)
        slant_10 = tropo.slant_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX, 10.0)
        self.assertTrue(2.0 <= zhd <= 2.6)
        self.assertTrue(0.03 <= zwd <= 0.20)
        self.assertTrue(2.2 <= ztd <= 2.6)
        self.assertTrue(4.0 <= slant_30 <= 5.5)
        self.assertTrue(8.0 <= slant_10 <= 15.0)

    def test_slant_exceeds_zenith_total_below_zenith(self):
        """Physical sanity: every slant delay below zenith exceeds its zenith total."""
        ztd = tropo.zenith_total_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX)
        for el_deg in (5.0, 15.0, 45.0, 89.0):
            slant = tropo.slant_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX, el_deg)
            self.assertGreater(slant, ztd)

    def test_pressure_window_bounds(self):
        """Physical-sanity bounds: ZHD at the pressure/latitude/height window extremes."""
        zhd_high = tropo.zenith_hydrostatic_delay_m(1100.0, 90.0, 0.0)
        zhd_low = tropo.zenith_hydrostatic_delay_m(300.0, 0.0, 10.0)
        self.assertLess(zhd_high, 2.6)
        self.assertGreater(zhd_low, 0.65)

    def test_determinism_slant_delay(self):
        """Determinism: two identical calls to slant_delay_m are bitwise identical."""
        a = tropo.slant_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX, EL_EX)
        b = tropo.slant_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX, EL_EX)
        self.assertEqual(a, b)

    def test_determinism_zenith_total_delay(self):
        """Determinism: two identical calls to zenith_total_delay_m are bitwise identical."""
        a = tropo.zenith_total_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX)
        b = tropo.zenith_total_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX)
        self.assertEqual(a, b)

    def test_valueerror_elevation_rejections(self):
        """ValueError rejection: elevation at 0, -5, 90.1 and nan on slant functions."""
        for el_deg in (0.0, -5.0, 90.1, float("nan")):
            with self.assertRaises(ValueError):
                tropo.slant_mapping_factor(el_deg)
            with self.assertRaises(ValueError):
                tropo.slant_hydrostatic_delay_m(P_EX, PHI_EX, H_EX, el_deg)
            with self.assertRaises(ValueError):
                tropo.slant_wet_delay_m(E_EX, T_EX, PHI_EX, H_EX, el_deg)
            with self.assertRaises(ValueError):
                tropo.slant_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX, el_deg)

    def test_valueerror_elevation_never_zero_division(self):
        """Full-pipeline rejection: elevation of 0 deg raises ValueError, never ZeroDivisionError."""
        try:
            tropo.slant_delay_m(P_EX, E_EX, T_EX, PHI_EX, H_EX, 0.0)
            self.fail("expected ValueError")
        except ZeroDivisionError:
            self.fail("elevation must be validated before division")
        except ValueError:
            pass

    def test_valueerror_latitude_height_rejections(self):
        """ValueError rejection: geodetic latitude and height out of window on gravity_factor."""
        for phi_deg in (90.5, -91.0):
            with self.assertRaises(ValueError):
                tropo.gravity_factor(phi_deg, 0.0)
        for h_km in (10.5, -1.5):
            with self.assertRaises(ValueError):
                tropo.gravity_factor(45.0, h_km)

    def test_valueerror_pressure_rejections(self):
        """ValueError rejection: pressure outside [300, 1100] hPa on zenith_hydrostatic_delay_m."""
        for p_hpa in (200.0, 1200.0):
            with self.assertRaises(ValueError):
                tropo.zenith_hydrostatic_delay_m(p_hpa, PHI_EX, H_EX)

    def test_valueerror_wet_delay_rejections(self):
        """ValueError rejection: partial pressure and temperature bounds on zenith_wet_delay_m."""
        with self.assertRaises(ValueError):
            tropo.zenith_wet_delay_m(-1.0, T_EX, PHI_EX, H_EX)
        es_ex = tropo.saturation_vapor_pressure_hpa(T_EX)
        with self.assertRaises(ValueError):
            tropo.zenith_wet_delay_m(es_ex + 1.0, T_EX, PHI_EX, H_EX)
        with self.assertRaises(ValueError):
            tropo.zenith_wet_delay_m(1.0, 180.0, PHI_EX, H_EX)
        with self.assertRaises(ValueError):
            tropo.zenith_wet_delay_m(1.0, 350.0, PHI_EX, H_EX)

    def test_valueerror_humidity_and_saturation_rejections(self):
        """ValueError rejection: relative humidity and saturation temperature bounds."""
        for rh_pct in (-1.0, 101.0):
            with self.assertRaises(ValueError):
                tropo.water_vapor_pressure_hpa(T_EX, rh_pct)
        with self.assertRaises(ValueError):
            tropo.saturation_vapor_pressure_hpa(150.0)

    def test_valueerror_propagates_through_full_pipeline(self):
        """Full-pipeline rejection: each non-physical input propagates ValueError through slant_delay_m."""
        es_ex = tropo.saturation_vapor_pressure_hpa(T_EX)
        bad_calls = [
            (200.0, E_EX, T_EX, PHI_EX, H_EX, EL_EX),
            (P_EX, E_EX, T_EX, 90.5, H_EX, EL_EX),
            (P_EX, E_EX, T_EX, PHI_EX, 10.5, EL_EX),
            (P_EX, -1.0, T_EX, PHI_EX, H_EX, EL_EX),
            (P_EX, es_ex + 1.0, T_EX, PHI_EX, H_EX, EL_EX),
            (P_EX, E_EX, 180.0, PHI_EX, H_EX, EL_EX),
        ]
        for args in bad_calls:
            with self.assertRaises(ValueError):
                tropo.slant_delay_m(*args)


if __name__ == "__main__":
    unittest.main()
