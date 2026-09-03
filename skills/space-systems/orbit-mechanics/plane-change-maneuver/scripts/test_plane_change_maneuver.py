"""Contract test for the plane-change-maneuver logic module.

Deterministic, offline, stdlib-only unittest. Covers the worked-example
anchors: LEO circular speed 7.7258 km/s and pure 28.5 deg plane change
3.803 km/s, GEO circular speed 3.0747 km/s and pure change 1.514 km/s,
the GTO apogee vis-viva speed at semimajor axis 24421 km (exact model
value 1.6078 km/s; the spec's 1.6057 classic reference sits within
1e-2), the combined-burn anchor 1.832 km/s from the spec's rounded
inputs (1.6057, 3.0747), the separate total 2.983 km/s within 0.01, the
combined-cheaper verdict, the di = 90 sanity value 10.926 km/s, the di =
0 zero delta-v and the di = 180 full-retrograde cases, and ValueError
rejection of non-positive radii and semimajor axes, points off the
ellipse (2a <= r), negative speeds, and inclination changes outside
(-180, 180]. Run offline:

    python3 scripts/test_plane_change_maneuver.py
"""

import math
import unittest

import plane_change_maneuver_logic as pcm

MU = pcm.MU_EARTH
LEO_R = 6678.0  # 300 km circular orbit radius, km
GEO_R = 42164.0  # geostationary orbit radius, km
GTO_A = (LEO_R + GEO_R) / 2.0  # 24421.0 km transfer semimajor axis


class TestCircularOrbitSpeed(unittest.TestCase):
    def test_circular_orbit_speed_leo_anchor(self):
        self.assertAlmostEqual(
            pcm.circular_orbit_speed(MU, LEO_R), 7.7258, delta=1e-3
        )

    def test_circular_orbit_speed_geo_anchor(self):
        self.assertAlmostEqual(
            pcm.circular_orbit_speed(MU, GEO_R), 3.0747, delta=1e-3
        )

    def test_circular_orbit_speed_sqrt_mu_over_r_identity(self):
        v = pcm.circular_orbit_speed(MU, LEO_R)
        self.assertAlmostEqual(v * v, MU / LEO_R, delta=1e-9)

    def test_circular_orbit_speed_rejects_nonpositive_radius(self):
        for bad in (0.0, -100.0):
            with self.assertRaises(ValueError):
                pcm.circular_orbit_speed(MU, bad)

    def test_circular_orbit_speed_rejects_nonpositive_mu(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                pcm.circular_orbit_speed(bad, LEO_R)


class TestPlaneChangeDv(unittest.TestCase):
    def test_plane_change_dv_leo_28_5_anchor(self):
        self.assertAlmostEqual(
            pcm.plane_change_dv(7.7258, 28.5), 3.803, delta=0.001
        )

    def test_plane_change_dv_geo_28_5_anchor(self):
        self.assertAlmostEqual(
            pcm.plane_change_dv(3.0747, 28.5), 1.514, delta=0.001
        )

    def test_plane_change_dv_two_v_sin_half_formula(self):
        v = pcm.circular_orbit_speed(MU, LEO_R)
        for di in (0.0, 15.0, 28.5, 60.0, 90.0, 180.0):
            dv = pcm.plane_change_dv(v, di)
            self.assertAlmostEqual(
                dv, 2.0 * v * math.sin(math.radians(di) / 2.0), delta=1e-9
            )

    def test_plane_change_dv_zero_change_is_zero(self):
        self.assertEqual(pcm.plane_change_dv(7.7258, 0.0), 0.0)

    def test_plane_change_dv_90_deg_sanity_sqrt2(self):
        self.assertAlmostEqual(
            pcm.plane_change_dv(7.7258, 90.0), 10.926, delta=0.001
        )
        v = pcm.circular_orbit_speed(MU, LEO_R)
        self.assertAlmostEqual(
            pcm.plane_change_dv(v, 90.0), v * math.sqrt(2.0), delta=1e-9
        )

    def test_plane_change_dv_180_deg_is_two_v(self):
        v = pcm.circular_orbit_speed(MU, GEO_R)
        self.assertAlmostEqual(pcm.plane_change_dv(v, 180.0), 2.0 * v, delta=1e-9)
        # -180 is outside the open interval, a small negative angle mirrors.
        self.assertEqual(pcm.plane_change_dv(7.7258, -90.0),
                         -pcm.plane_change_dv(7.7258, 90.0))

    def test_plane_change_dv_rejects_out_of_range(self):
        for bad in (-180.0, -200.0, 181.0, 360.0):
            with self.assertRaises(ValueError):
                pcm.plane_change_dv(7.7258, bad)

    def test_plane_change_dv_accepts_180_boundary(self):
        self.assertGreater(pcm.plane_change_dv(7.7258, 180.0), 0.0)


class TestTransferSpeedAtRadius(unittest.TestCase):
    def test_transfer_speed_at_radius_gto_apogee_anchor(self):
        v = pcm.transfer_speed_at_radius(MU, GEO_R, GTO_A)
        self.assertAlmostEqual(v, 1.6078, delta=1e-3)
        # Spec reference 1.6057 km/s (classic GTO apogee quote) sits within
        # 1e-2 of the exact model value for the a = 24421 km ellipse.
        self.assertLess(abs(v - 1.6057), 1e-2)

    def test_transfer_speed_at_radius_vis_viva_identity(self):
        v = pcm.transfer_speed_at_radius(MU, GEO_R, GTO_A)
        self.assertAlmostEqual(
            v * v, MU * (2.0 / GEO_R - 1.0 / GTO_A), delta=1e-9
        )

    def test_transfer_speed_at_radius_perigee_sanity(self):
        v_p = pcm.transfer_speed_at_radius(MU, LEO_R, GTO_A)
        v_c = pcm.circular_orbit_speed(MU, LEO_R)
        self.assertAlmostEqual(v_p, 10.1516, delta=1e-3)
        self.assertGreater(v_p, v_c)

    def test_transfer_speed_at_radius_rejects_nonpositive_radius(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                pcm.transfer_speed_at_radius(MU, bad, GTO_A)

    def test_transfer_speed_at_radius_rejects_nonpositive_sma(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                pcm.transfer_speed_at_radius(MU, GEO_R, bad)

    def test_transfer_speed_at_radius_rejects_off_ellipse_point(self):
        with self.assertRaises(ValueError):
            pcm.transfer_speed_at_radius(MU, GEO_R, 21000.0)

    def test_transfer_speed_at_radius_rejects_2a_equal_r_boundary(self):
        with self.assertRaises(ValueError):
            pcm.transfer_speed_at_radius(MU, 20000.0, 10000.0)


class TestCombinedBurnDv(unittest.TestCase):
    def test_combined_burn_dv_gto_anchor_spec_inputs(self):
        self.assertAlmostEqual(
            pcm.combined_burn_dv(1.6057, 3.0747, 28.5), 1.832, delta=0.001
        )

    def test_combined_burn_dv_law_of_cosines_identity(self):
        v1, v2, di = 1.6078, 3.0747, 28.5
        dv = pcm.combined_burn_dv(v1, v2, di)
        expected = math.sqrt(
            v1 * v1 + v2 * v2 - 2.0 * v1 * v2 * math.cos(math.radians(di))
        )
        self.assertAlmostEqual(dv, expected, delta=1e-9)

    def test_combined_burn_dv_zero_change_is_speed_difference(self):
        v1, v2 = 1.6078, 3.0747
        self.assertAlmostEqual(
            pcm.combined_burn_dv(v1, v2, 0.0), v2 - v1, delta=1e-9
        )

    def test_combined_burn_dv_180_deg_is_speed_sum(self):
        v1, v2 = 1.6078, 3.0747
        self.assertAlmostEqual(
            pcm.combined_burn_dv(v1, v2, 180.0), v1 + v2, delta=1e-9
        )

    def test_combined_burn_dv_rejects_negative_speed(self):
        for bad in (-0.5, -1.0):
            with self.assertRaises(ValueError):
                pcm.combined_burn_dv(bad, 3.0747, 28.5)
            with self.assertRaises(ValueError):
                pcm.combined_burn_dv(1.6057, bad, 28.5)

    def test_combined_burn_dv_rejects_out_of_range_di(self):
        for bad in (-180.0, -181.0, 181.0, 360.0):
            with self.assertRaises(ValueError):
                pcm.combined_burn_dv(1.6057, 3.0747, bad)


class TestManeuverVerdict(unittest.TestCase):
    def test_maneuver_verdict_combined_cheaper(self):
        self.assertEqual(pcm.maneuver_verdict(2.983, 1.832), "combined-cheaper")

    def test_maneuver_verdict_tie_goes_pure(self):
        self.assertEqual(
            pcm.maneuver_verdict(1.832, 1.832 - 1e-10), "pure-cheaper-or-equal"
        )

    def test_maneuver_verdict_pure_cheaper(self):
        self.assertEqual(pcm.maneuver_verdict(1.0, 2.0), "pure-cheaper-or-equal")


class TestAnalyzePlaneChange(unittest.TestCase):
    def test_analyze_pure_only_dict(self):
        result = pcm.analyze_plane_change(MU, LEO_R, 28.5)
        self.assertAlmostEqual(result["speed_km_s"], 7.7258, delta=1e-3)
        self.assertAlmostEqual(
            result["pure_plane_change_dv_km_s"], 3.803, delta=0.001
        )
        self.assertIsNone(result["combined_dv_km_s"])
        self.assertIsNone(result["separate_total_km_s"])
        self.assertEqual(result["verdict"], "pure-only")

    def test_analyze_combined_gto_chain(self):
        result = pcm.analyze_plane_change(MU, LEO_R, 28.5, GTO_A, GEO_R)
        self.assertAlmostEqual(
            result["speed_at_maneuver_km_s"], 1.6078, delta=1e-3
        )
        self.assertAlmostEqual(
            result["circular_speed_km_s"], 3.0747, delta=1e-3
        )
        self.assertAlmostEqual(
            result["pure_plane_change_dv_km_s"], 1.514, delta=0.001
        )
        # Exact chain value 1.8302 km/s; the classic 1.832 km/s quote uses
        # the spec's rounded 1.6057 km/s apogee input, both ~1.83 km/s.
        self.assertAlmostEqual(
            result["combined_dv_km_s"], 1.8302, delta=1e-3
        )
        self.assertAlmostEqual(
            result["separate_total_km_s"], 2.983, delta=0.01
        )
        self.assertEqual(result["verdict"], "combined-cheaper")

    def test_analyze_combined_saves_about_1_15_km_s(self):
        result = pcm.analyze_plane_change(MU, LEO_R, 28.5, GTO_A, GEO_R)
        saving = result["separate_total_km_s"] - result["combined_dv_km_s"]
        self.assertAlmostEqual(saving, 1.15, delta=0.05)
        self.assertEqual(result["verdict"], "combined-cheaper")

    def test_analyze_combined_matches_component_functions(self):
        result = pcm.analyze_plane_change(MU, LEO_R, 28.5, GTO_A, GEO_R)
        v_before = pcm.transfer_speed_at_radius(MU, GEO_R, GTO_A)
        v_after = pcm.circular_orbit_speed(MU, GEO_R)
        self.assertAlmostEqual(
            result["combined_dv_km_s"],
            pcm.combined_burn_dv(v_before, v_after, 28.5),
            delta=1e-9,
        )
        expected_separate = (v_after - v_before) + pcm.plane_change_dv(
            v_after, 28.5
        )
        self.assertAlmostEqual(
            result["separate_total_km_s"], expected_separate, delta=1e-9
        )

    def test_analyze_di_zero_separate_equals_speed_gap(self):
        result = pcm.analyze_plane_change(MU, LEO_R, 0.0, GTO_A, GEO_R)
        v_before = pcm.transfer_speed_at_radius(MU, GEO_R, GTO_A)
        v_after = pcm.circular_orbit_speed(MU, GEO_R)
        self.assertAlmostEqual(
            result["combined_dv_km_s"], v_after - v_before, delta=1e-9
        )
        self.assertAlmostEqual(
            result["separate_total_km_s"], v_after - v_before, delta=1e-9
        )
        self.assertEqual(result["verdict"], "pure-cheaper-or-equal")

    def test_analyze_valueerrors_propagate(self):
        with self.assertRaises(ValueError):
            pcm.analyze_plane_change(MU, 0.0, 28.5)
        with self.assertRaises(ValueError):
            pcm.analyze_plane_change(MU, LEO_R, 200.0)
        with self.assertRaises(ValueError):
            pcm.analyze_plane_change(MU, LEO_R, 28.5, GTO_A, 99999.0)
        with self.assertRaises(ValueError):
            pcm.analyze_plane_change(MU, LEO_R, 28.5, None, GEO_R)
        with self.assertRaises(ValueError):
            pcm.analyze_plane_change(MU, LEO_R, 28.5, GTO_A, None)


if __name__ == "__main__":
    unittest.main()
