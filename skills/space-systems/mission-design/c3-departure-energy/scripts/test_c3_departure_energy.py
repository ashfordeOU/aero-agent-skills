"""test_c3_departure_energy.py

Contract test for the c3-departure-energy leaf (space-systems,
mission-design pack). Deterministic, offline, stdlib unittest only.

Run from the repo root:
    python3 skills/space-systems/mission-design/c3-departure-energy/scripts/test_c3_departure_energy.py
"""

import math
import unittest

from c3_departure_energy_logic import (
    MU_EARTH,
    G0,
    c3_from_excess_speed,
    excess_speed_from_c3,
    circular_speed,
    injection_speed,
    injection_delta_v,
    parking_period,
    asymptote_declination,
    departure_energy_assessment,
)

MU = MU_EARTH
R_PARK = 6578.0e3       # 300 km circular parking orbit radius (m)
V_INF = 3000.0          # target hyperbolic excess (m/s)


class TestConstants(unittest.TestCase):
    def test_module_constants(self):
        self.assertEqual(MU_EARTH, 3.986004418e14)
        self.assertEqual(G0, 9.80665)


class TestC3Conversions(unittest.TestCase):
    def test_c3_excess_worked_example(self):
        # C3 = 9 km2/s2 for 3000 m/s excess; sqrt recovers the excess.
        self.assertEqual(c3_from_excess_speed(V_INF), 9.0e6)
        self.assertEqual(c3_from_excess_speed(V_INF) / 1.0e6, 9.0)
        self.assertAlmostEqual(excess_speed_from_c3(9.0e6), V_INF,
                               delta=1e-6)

    def test_c3_from_excess_zero(self):
        self.assertEqual(c3_from_excess_speed(0.0), 0.0)

    def test_c3_from_excess_negative_raises(self):
        with self.assertRaises(ValueError):
            c3_from_excess_speed(-1.0)

    def test_excess_from_c3_negative_raises(self):
        with self.assertRaises(ValueError):
            excess_speed_from_c3(-0.1)

    def test_excess_round_trip(self):
        # Round trip within 1e-6 for a sweep of physical excess speeds.
        for v in (0.0, 100.0, 1000.0, V_INF, 4200.0, 1.2e4):
            self.assertAlmostEqual(
                excess_speed_from_c3(c3_from_excess_speed(v)), v,
                delta=1e-6)


class TestCircularSpeed(unittest.TestCase):
    def test_circular_speed_worked_example(self):
        vc = circular_speed(MU, R_PARK)
        expected = math.sqrt(MU / R_PARK)
        self.assertAlmostEqual(vc, expected, delta=1e-3)
        self.assertAlmostEqual(vc, 7784.342809549733, delta=1e-3)
        # Spec magnitude bound 7700-7900 m/s.
        self.assertTrue(7700.0 <= vc <= 7900.0, vc)

    def test_circular_speed_geo_known_value(self):
        # GEO radius 42164 km gives about 3074.7 m/s.
        vc = circular_speed(MU, 42164000.0)
        self.assertAlmostEqual(vc, 3074.66, delta=0.5)

    def test_circular_speed_invalid_mu_raises(self):
        with self.assertRaises(ValueError):
            circular_speed(0.0, R_PARK)
        with self.assertRaises(ValueError):
            circular_speed(-MU, R_PARK)

    def test_circular_speed_invalid_radius_raises(self):
        with self.assertRaises(ValueError):
            circular_speed(MU, 0.0)
        with self.assertRaises(ValueError):
            circular_speed(MU, -R_PARK)


class TestInjectionSpeedAndDeltaV(unittest.TestCase):
    def test_injection_speed_worked_example(self):
        vp = injection_speed(MU, R_PARK, V_INF)
        expected = math.sqrt(V_INF ** 2 + 2.0 * MU / R_PARK)
        self.assertAlmostEqual(vp, expected, delta=1e-3)
        self.assertAlmostEqual(vp, 11410.170285897457, delta=1e-3)
        # Spec magnitude bound 11200-11700 m/s.
        self.assertTrue(11200.0 <= vp <= 11700.0, vp)

    def test_injection_delta_v_worked_example(self):
        dv = injection_delta_v(MU, R_PARK, V_INF)
        self.assertAlmostEqual(dv, 3625.827476347724, delta=1e-3)
        # Spec magnitude bound 3400-3900 m/s.
        self.assertTrue(3400.0 <= dv <= 3900.0, dv)

    def test_delta_v_equals_vp_minus_vc_exactly(self):
        vc = circular_speed(MU, R_PARK)
        vp = injection_speed(MU, R_PARK, V_INF)
        dv = injection_delta_v(MU, R_PARK, V_INF)
        self.assertEqual(dv, vp - vc)

    def test_delta_v_positive(self):
        for r in (6.6e6, 7.0e6, 4.22e7):
            self.assertGreater(injection_delta_v(MU, r, V_INF), 0.0)

    def test_zero_excess_is_local_escape_speed(self):
        # v_inf = 0 is the parabolic escape trajectory: v_p equals the
        # local escape speed sqrt(2*mu/r), above the circular speed.
        v_esc = math.sqrt(2.0 * MU / R_PARK)
        self.assertEqual(injection_speed(MU, R_PARK, 0.0), v_esc)
        self.assertAlmostEqual(injection_speed(MU, R_PARK, 0.0),
                               injection_delta_v(MU, R_PARK, 0.0) +
                               circular_speed(MU, R_PARK), delta=1e-9)
        self.assertGreater(injection_delta_v(MU, R_PARK, 0.0), 0.0)

    def test_vis_viva_identity_far_radius(self):
        # Closed form: v_p**2 - v_inf**2 = 2*mu/r at any radius.
        vp = injection_speed(MU, 1.0e9, V_INF)
        self.assertAlmostEqual(vp ** 2 - V_INF ** 2, 2.0 * MU / 1.0e9,
                               delta=1e-3)

    def test_far_radius_within_50_m_s(self):
        # At 1e9 m the excess term 2*mu/r is under 1% of v_inf**2 for a
        # 12 km/s excess, so v_p approaches v_inf within 50 m/s.
        vp = injection_speed(MU, 1.0e9, 12000.0)
        self.assertLess(abs(vp - 12000.0), 50.0)

    def test_far_radius_residual_shrinks(self):
        # Worked example excess: residual v_p - v_inf strictly decreases
        # as the radius grows and drops below 1 m/s by 1e12 m.
        residual = [injection_speed(MU, r, V_INF) - V_INF
                    for r in (1.0e7, 1.0e8, 1.0e9, 1.0e12)]
        for i in range(1, len(residual)):
            self.assertLess(residual[i], residual[i - 1])
        self.assertLess(residual[-1], 1.0)

    def test_injection_speed_invalid_mu_raises(self):
        with self.assertRaises(ValueError):
            injection_speed(0.0, R_PARK, V_INF)
        with self.assertRaises(ValueError):
            injection_speed(-MU, R_PARK, V_INF)

    def test_injection_speed_invalid_radius_raises(self):
        with self.assertRaises(ValueError):
            injection_speed(MU, 0.0, V_INF)
        with self.assertRaises(ValueError):
            injection_speed(MU, -R_PARK, V_INF)

    def test_injection_speed_negative_excess_raises(self):
        with self.assertRaises(ValueError):
            injection_speed(MU, R_PARK, -V_INF)
        with self.assertRaises(ValueError):
            injection_delta_v(MU, R_PARK, -1.0)


class TestParkingPeriod(unittest.TestCase):
    def test_parking_period_worked_example(self):
        t = parking_period(MU, R_PARK)
        expected = 2.0 * math.pi * math.sqrt(R_PARK ** 3 / MU)
        self.assertAlmostEqual(t, expected, delta=1e-3)
        self.assertAlmostEqual(t, 5309.477493709967, delta=1e-3)
        # Spec magnitude bound 5300-5600 s (about 90 min).
        self.assertTrue(5300.0 <= t <= 5600.0, t)
        self.assertAlmostEqual(t / 60.0, 88.5, delta=2.0)

    def test_parking_period_geo_sidereal_day(self):
        # A GEO parking radius gives one sidereal day (86164.0905 s).
        t = parking_period(MU, 42164000.0)
        self.assertAlmostEqual(t, 86164.0905, delta=1.0)

    def test_parking_period_invalid_mu_raises(self):
        with self.assertRaises(ValueError):
            parking_period(0.0, R_PARK)
        with self.assertRaises(ValueError):
            parking_period(-MU, R_PARK)

    def test_parking_period_invalid_radius_raises(self):
        with self.assertRaises(ValueError):
            parking_period(MU, 0.0)
        with self.assertRaises(ValueError):
            parking_period(MU, -1.0)


class TestAsymptoteDeclination(unittest.TestCase):
    def test_declination_worked_example(self):
        # v = (2000, 2000, 1000) m/s has magnitude 3000, so the vector
        # matches C3 = 9 km2/s2; dec = asin(1/3) in degrees.
        dec = asymptote_declination(2000.0, 2000.0, 1000.0)
        expected = math.degrees(math.asin(1000.0 / 3000.0))
        self.assertAlmostEqual(dec, expected, delta=1e-9)
        self.assertAlmostEqual(dec, 19.47122063449069, delta=1e-9)
        # Spec magnitude bound 16-20 deg.
        self.assertTrue(16.0 <= dec <= 20.0, dec)

    def test_declination_equatorial_and_poles(self):
        self.assertAlmostEqual(asymptote_declination(3000.0, 0.0, 0.0),
                               0.0, delta=1e-12)
        self.assertAlmostEqual(asymptote_declination(0.0, 3000.0, 0.0),
                               0.0, delta=1e-12)
        self.assertAlmostEqual(asymptote_declination(0.0, 0.0, 3000.0),
                               90.0, delta=1e-9)
        self.assertAlmostEqual(asymptote_declination(0.0, 0.0, -3000.0),
                               -90.0, delta=1e-9)

    def test_declination_matches_excess_magnitude(self):
        # Magnitude of (2000, 2000, 1000) is exactly 3000 m/s.
        mag = math.sqrt(2000.0 ** 2 + 2000.0 ** 2 + 1000.0 ** 2)
        self.assertEqual(mag, 3000.0)

    def test_declination_zero_vector_raises(self):
        with self.assertRaises(ValueError):
            asymptote_declination(0.0, 0.0, 0.0)


class TestDepartureEnergyAssessment(unittest.TestCase):
    def test_assessment_worked_example_with_components(self):
        a = departure_energy_assessment(MU, R_PARK, V_INF,
                                        2000.0, 2000.0, 1000.0)
        self.assertAlmostEqual(a["c3_m2_s2"], 9.0e6, delta=1e-3)
        self.assertAlmostEqual(a["c3_km2_s2"], 9.0, delta=1e-9)
        self.assertEqual(a["excess_speed_m_s"], V_INF)
        self.assertAlmostEqual(a["circular_speed_m_s"],
                               circular_speed(MU, R_PARK), delta=1e-6)
        self.assertAlmostEqual(a["injection_speed_m_s"],
                               injection_speed(MU, R_PARK, V_INF),
                               delta=1e-6)
        self.assertAlmostEqual(a["injection_delta_v_m_s"],
                               injection_delta_v(MU, R_PARK, V_INF),
                               delta=1e-6)
        self.assertAlmostEqual(a["parking_period_s"],
                               parking_period(MU, R_PARK), delta=1e-6)
        self.assertAlmostEqual(a["asymptote_declination_deg"],
                               19.47122063449069, delta=1e-9)

    def test_assessment_declination_none_without_components(self):
        a = departure_energy_assessment(MU, R_PARK, V_INF)
        self.assertIsNone(a["asymptote_declination_deg"])
        a = departure_energy_assessment(MU, R_PARK, V_INF, 2000.0, None, None)
        self.assertIsNone(a["asymptote_declination_deg"])

    def test_assessment_dict_has_exact_keys(self):
        a = departure_energy_assessment(MU, R_PARK, V_INF,
                                        2000.0, 2000.0, 1000.0)
        self.assertEqual(
            set(a.keys()),
            {"c3_m2_s2", "c3_km2_s2", "excess_speed_m_s",
             "circular_speed_m_s", "injection_speed_m_s",
             "injection_delta_v_m_s", "parking_period_s",
             "asymptote_declination_deg"})

    def test_assessment_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            departure_energy_assessment(0.0, R_PARK, V_INF)
        with self.assertRaises(ValueError):
            departure_energy_assessment(MU, 0.0, V_INF)
        with self.assertRaises(ValueError):
            departure_energy_assessment(MU, R_PARK, -1.0)
        with self.assertRaises(ValueError):
            departure_energy_assessment(MU, R_PARK, V_INF,
                                        0.0, 0.0, 0.0)

    def test_assessment_c3_km2_s2_units(self):
        a = departure_energy_assessment(MU, R_PARK, V_INF)
        self.assertEqual(a["c3_m2_s2"], a["c3_km2_s2"] * 1.0e6)


class TestDeterminism(unittest.TestCase):
    def test_deterministic_no_rng(self):
        # Run-to-run identical floats: no RNG anywhere in the chain.
        first = departure_energy_assessment(MU, R_PARK, V_INF,
                                            2000.0, 2000.0, 1000.0)
        second = departure_energy_assessment(MU, R_PARK, V_INF,
                                             2000.0, 2000.0, 1000.0)
        self.assertEqual(first, second)
        for _ in range(5):
            a = departure_energy_assessment(MU, 7000.0e3, 4500.0,
                                            1000.0, -2000.0, 3000.0)
            b = departure_energy_assessment(MU, 7000.0e3, 4500.0,
                                            1000.0, -2000.0, 3000.0)
            self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
