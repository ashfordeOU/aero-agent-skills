"""Deterministic contract tests for airborne_weather_radar_logic.py.

Offline, stdlib unittest only. Run from the leaf scripts directory:

    python3 test_airborne_weather_radar.py

Covers the wave-31 spec validation list: worked-example magnitude bounds and
real module values, Z-R round trip, monotonicity, ground clutter geometry
verdicts, echo level banding, the convenience chain keys, determinism and
ValueError rejection of every non-physical input.
"""

import math
import unittest

import airborne_weather_radar_logic as awr

# Worked example inputs: rainfall 20 mm/h, own 3048 m, cell top 12192 m,
# slant 111120 m (60 NM), terrain 0 m, beam width 3 deg.
OWN_ALT = 3048.0
CELL_TOP = 12192.0
SLANT = 111120.0


class ReflectivityRainfallTests(unittest.TestCase):
    def test_reflectivity_20mmh_value_and_spec_bound(self):
        z = awr.reflectivity_from_rainfall(20.0)
        self.assertTrue(20000.0 <= z <= 28000.0)
        self.assertTrue(math.isclose(z, 24136.70534618066, rel_tol=1e-9,
                                     abs_tol=1e-6))

    def test_reflectivity_20mmh_dBZ_about_43_8(self):
        dbz = 10.0 * math.log10(awr.reflectivity_from_rainfall(20.0))
        self.assertTrue(math.isclose(dbz, 43.82677988726351, rel_tol=1e-9,
                                     abs_tol=1e-6))

    def test_reflectivity_50mmh_value_and_spec_bound(self):
        z = awr.reflectivity_from_rainfall(50.0)
        self.assertTrue(90000.0 <= z <= 120000.0)
        self.assertTrue(math.isclose(z, 104563.95525912735, rel_tol=1e-9,
                                     abs_tol=1e-6))

    def test_reflectivity_zero_rainfall_is_zero(self):
        self.assertEqual(awr.reflectivity_from_rainfall(0.0), 0.0)

    def test_rainfall_round_trip_20mmh_within_one_percent(self):
        rain = awr.rainfall_from_reflectivity(
            awr.reflectivity_from_rainfall(20.0))
        self.assertTrue(abs(rain - 20.0) / 20.0 < 0.01)

    def test_rainfall_round_trip_within_1e_6_relative(self):
        for rate in (5.0, 20.0, 50.0, 80.0):
            back = awr.rainfall_from_reflectivity(
                awr.reflectivity_from_rainfall(rate))
            self.assertTrue(abs(back - rate) / rate < 1e-6,
                            "round trip failed at %r" % rate)

    def test_rainfall_round_trip_custom_ab(self):
        back = awr.rainfall_from_reflectivity(
            awr.reflectivity_from_rainfall(30.0, a=300.0, b=1.4),
            a=300.0, b=1.4)
        self.assertTrue(abs(back - 30.0) / 30.0 < 1e-6)

    def test_rainfall_from_zero_reflectivity_is_zero(self):
        self.assertEqual(awr.rainfall_from_reflectivity(0.0), 0.0)

    def test_monotonicity_both_directions(self):
        zs = [awr.reflectivity_from_rainfall(r) for r in (5.0, 10.0, 20.0,
                                                          40.0)]
        self.assertEqual(zs, sorted(zs))
        rains = [awr.rainfall_from_reflectivity(z) for z in (1000.0,
                                                             10000.0,
                                                             100000.0)]
        self.assertEqual(rains, sorted(rains))


class TiltAndRangeTests(unittest.TestCase):
    def test_tilt_example_value_and_spec_bound(self):
        tilt = awr.tilt_to_cell_top(OWN_ALT, CELL_TOP, SLANT)
        self.assertTrue(3.5 <= tilt <= 6.0)
        self.assertTrue(math.isclose(tilt, 4.704237067623307, rel_tol=1e-9,
                                     abs_tol=1e-9))

    def test_tilt_increases_as_cell_top_rises(self):
        low = awr.tilt_to_cell_top(OWN_ALT, 12192.0, SLANT)
        high = awr.tilt_to_cell_top(OWN_ALT, 15000.0, SLANT)
        self.assertGreater(high, low)

    def test_tilt_negative_when_cell_below_aircraft(self):
        tilt = awr.tilt_to_cell_top(3048.0, 2000.0, 111120.0)
        expected = math.degrees(math.atan((2000.0 - 3048.0) / 111120.0))
        self.assertTrue(math.isclose(tilt, expected, rel_tol=1e-12,
                                     abs_tol=1e-12))
        self.assertLess(tilt, 0.0)

    def test_tilt_zero_when_cell_at_own_altitude(self):
        self.assertAlmostEqual(awr.tilt_to_cell_top(5000.0, 5000.0, 20000.0),
                               0.0, places=12)

    def test_tilt_zero_slant_rejected(self):
        with self.assertRaises(ValueError):
            awr.tilt_to_cell_top(3048.0, 12192.0, 0.0)
        with self.assertRaises(ValueError):
            awr.tilt_to_cell_top(3048.0, 12192.0, -5000.0)

    def test_ground_range_example_value_and_spec_bound(self):
        gr = awr.ground_range_from_slant(SLANT, OWN_ALT)
        self.assertTrue(abs(gr - SLANT) / SLANT < 0.005)
        self.assertTrue(math.isclose(gr, 111078.18911019391, rel_tol=1e-9,
                                     abs_tol=1e-3))

    def test_ground_range_closed_form_identity_and_zero_case(self):
        slant, own, target = 10000.0, 6000.0, 1000.0
        gr = awr.ground_range_from_slant(slant, own, target)
        self.assertTrue(math.isclose(gr * gr + (own - target) ** 2,
                                     slant * slant, rel_tol=1e-12))
        self.assertAlmostEqual(awr.ground_range_from_slant(3000.0, 3000.0,
                                                           0.0), 0.0,
                               places=12)
        self.assertEqual(awr.ground_range_from_slant(5000.0, 4000.0, 1000.0),
                         4000.0)

    def test_ground_range_non_physical_slant_rejected(self):
        with self.assertRaises(ValueError):
            awr.ground_range_from_slant(5000.0, 6000.0, 0.0)
        with self.assertRaises(ValueError):
            awr.ground_range_from_slant(100.0, 3048.0, 0.0)


class ClutterAndEchoTests(unittest.TestCase):
    def test_clutter_work_example_lowest_edge_and_verdict(self):
        tilt = awr.tilt_to_cell_top(OWN_ALT, CELL_TOP, SLANT)
        clutter = awr.clutter_check(tilt, OWN_ALT, SLANT, 0.0, 3.0)
        self.assertTrue(math.isclose(clutter["beam_lowest_edge_deg"],
                                     3.204237067623307, rel_tol=1e-9,
                                     abs_tol=1e-9))
        self.assertTrue(math.isclose(clutter["beam_lowest_edge_deg"],
                                     tilt - 1.5, rel_tol=1e-12,
                                     abs_tol=1e-12))
        self.assertFalse(clutter["clutter_verdict"])

    def test_clutter_verdict_true_when_terrain_angle_exceeds_beam_edge(self):
        clutter = awr.clutter_check(0.0, 500.0, 5000.0, 1000.0, 3.0)
        self.assertTrue(clutter["clutter_verdict"])
        self.assertEqual(clutter["beam_lowest_edge_deg"], -1.5)

    def test_clutter_verdict_false_when_beam_clear_of_terrain(self):
        # Terrain at own altitude gives a 0 deg terrain angle; a 5 deg tilt
        # with 3 deg width keeps the lowest edge (3.5 deg) above it.
        clutter = awr.clutter_check(5.0, 3000.0, 10000.0, 3000.0, 3.0)
        self.assertFalse(clutter["clutter_verdict"])

    def test_clutter_verdict_toggles_around_the_terrain_angle(self):
        # Own 500 m over terrain 1000 m at 10000 m slant: terrain angle is
        # atan(500 / 10000) about 2.86 deg. With a 3 deg beam the lowest edge
        # (tilt - 1.5) sits below 2.86 deg at tilt 4.0 (clutter) and above it
        # at tilt 5.0 (clear).
        self.assertTrue(
            awr.clutter_check(4.0, 500.0, 10000.0, 1000.0, 3.0)[
                "clutter_verdict"])
        self.assertFalse(
            awr.clutter_check(5.0, 500.0, 10000.0, 1000.0, 3.0)[
                "clutter_verdict"])

    def test_clutter_rejects_non_positive_slant_and_beam(self):
        with self.assertRaises(ValueError):
            awr.clutter_check(4.7, OWN_ALT, 0.0)
        with self.assertRaises(ValueError):
            awr.clutter_check(4.7, OWN_ALT, -100.0)
        with self.assertRaises(ValueError):
            awr.clutter_check(4.7, OWN_ALT, SLANT, beam_width_deg=0.0)
        with self.assertRaises(ValueError):
            awr.clutter_check(4.7, OWN_ALT, SLANT, beam_width_deg=-2.0)

    def test_echo_level_worked_example_is_3(self):
        z = awr.reflectivity_from_rainfall(20.0)
        self.assertEqual(awr.echo_level(z), 3)

    def test_echo_level_thresholds_and_dBZ_bands(self):
        self.assertEqual(awr.echo_level(0.0), 1)
        self.assertEqual(awr.echo_level(999.999), 1)
        self.assertEqual(awr.echo_level(1000.0), 2)
        self.assertEqual(awr.echo_level(9999.999), 2)
        self.assertEqual(awr.echo_level(10000.0), 3)
        self.assertEqual(awr.echo_level(99999.999), 3)
        self.assertEqual(awr.echo_level(100000.0), 4)
        self.assertEqual(awr.echo_level(1e8), 4)
        self.assertEqual(awr.echo_level(10 ** (25.0 / 10.0)), 1)
        self.assertEqual(awr.echo_level(10 ** (35.0 / 10.0)), 2)
        self.assertEqual(awr.echo_level(10 ** (45.0 / 10.0)), 3)
        self.assertEqual(awr.echo_level(10 ** (55.0 / 10.0)), 4)

    def test_echo_level_rejects_negative_reflectivity(self):
        with self.assertRaises(ValueError):
            awr.echo_level(-1.0)


class InputValidationTests(unittest.TestCase):
    def test_zr_value_errors(self):
        with self.assertRaises(ValueError):
            awr.reflectivity_from_rainfall(-0.1)
        with self.assertRaises(ValueError):
            awr.reflectivity_from_rainfall(20.0, a=0.0)
        with self.assertRaises(ValueError):
            awr.reflectivity_from_rainfall(20.0, a=-5.0)
        with self.assertRaises(ValueError):
            awr.rainfall_from_reflectivity(-1.0)
        with self.assertRaises(ValueError):
            awr.rainfall_from_reflectivity(1000.0, a=0.0)
        with self.assertRaises(ValueError):
            awr.rainfall_from_reflectivity(1000.0, b=0.0)
        with self.assertRaises(ValueError):
            awr.rainfall_from_reflectivity(1000.0, b=-1.6)


class AssessmentAndDeterminismTests(unittest.TestCase):
    def test_assessment_dict_has_exact_keys(self):
        result = awr.weather_radar_assessment(20.0, OWN_ALT, CELL_TOP, SLANT)
        self.assertEqual(
            sorted(result.keys()),
            ["clutter", "echo_level", "ground_range_m", "rainfall_rate",
             "reflectivity", "tilt_to_cell_top_deg"])
        self.assertEqual(sorted(result["clutter"].keys()),
                         ["beam_lowest_edge_deg", "clutter_verdict"])

    def test_assessment_matches_individual_calls(self):
        result = awr.weather_radar_assessment(20.0, OWN_ALT, CELL_TOP, SLANT)
        self.assertTrue(math.isclose(result["reflectivity"],
                                     awr.reflectivity_from_rainfall(20.0),
                                     rel_tol=1e-12))
        self.assertTrue(math.isclose(result["tilt_to_cell_top_deg"],
                                     awr.tilt_to_cell_top(OWN_ALT, CELL_TOP,
                                                          SLANT),
                                     rel_tol=1e-12))
        self.assertTrue(math.isclose(result["ground_range_m"],
                                     awr.ground_range_from_slant(SLANT,
                                                                 OWN_ALT),
                                     rel_tol=1e-12))
        self.assertEqual(result["clutter"],
                         awr.clutter_check(4.704237067623307, OWN_ALT, SLANT))
        self.assertEqual(result["rainfall_rate"], 20.0)
        self.assertEqual(result["echo_level"], 3)

    def test_assessment_forwards_terrain_and_beam_width(self):
        result = awr.weather_radar_assessment(20.0, OWN_ALT, CELL_TOP, SLANT,
                                              terrain_elevation_m=500.0,
                                              beam_width_deg=4.0)
        self.assertEqual(result["clutter"], awr.clutter_check(
            result["tilt_to_cell_top_deg"], OWN_ALT, SLANT,
            terrain_elevation_m=500.0, beam_width_deg=4.0))

    def test_deterministic_run_to_run_identical(self):
        first = awr.weather_radar_assessment(20.0, OWN_ALT, CELL_TOP, SLANT)
        second = awr.weather_radar_assessment(20.0, OWN_ALT, CELL_TOP, SLANT)
        self.assertEqual(first, second)
        self.assertEqual(awr.reflectivity_from_rainfall(20.0),
                         awr.reflectivity_from_rainfall(20.0))
        self.assertEqual(awr.tilt_to_cell_top(OWN_ALT, CELL_TOP, SLANT),
                         awr.tilt_to_cell_top(OWN_ALT, CELL_TOP, SLANT))

    def test_all_outputs_are_floats(self):
        z = awr.reflectivity_from_rainfall(20.0)
        self.assertIsInstance(z, float)
        self.assertIsInstance(awr.rainfall_from_reflectivity(z), float)
        self.assertIsInstance(awr.tilt_to_cell_top(OWN_ALT, CELL_TOP, SLANT),
                              float)
        self.assertIsInstance(awr.ground_range_from_slant(SLANT, OWN_ALT),
                              float)

    def test_module_constant_values(self):
        self.assertEqual(awr.A_DEFAULT, 200.0)
        self.assertEqual(awr.B_DEFAULT, 1.6)
        self.assertEqual(awr.RE_ARTH, 6371000.0)
        self.assertEqual(awr.PI, math.pi)


if __name__ == "__main__":
    unittest.main()
