#!/usr/bin/env python3
"""Gate 3 contract test: parametric aircraft geometry builder.

Exercises scripts/openvsp_geometry_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - parametric wing planform
geometry, derived area and aspect ratio, mean aerodynamic chord,
wetted areas, component volumes and centroids; invalid inputs raise
ValueError. Imports are stdlib plus the sibling module only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import openvsp_geometry_logic as geo  # noqa: E402


class WingPlanformTest(unittest.TestCase):
    def test_rectangular_wing_mac_equals_chord(self):
        w = geo.wing_planform(10.0, 2.0, 2.0)
        self.assertAlmostEqual(w["mean_aerodynamic_chord"], 2.0, places=9)
        self.assertAlmostEqual(w["mean_geometric_chord"], 2.0, places=9)

    def test_aspect_ratio_formula(self):
        # Rectangular wing: S = b * c, AR = b / c.
        w = geo.wing_planform(12.0, 2.0, 2.0)
        self.assertAlmostEqual(w["area"], 24.0, places=9)
        self.assertAlmostEqual(w["aspect_ratio"], 6.0, places=9)

    def test_tapered_wing_area_and_mac(self):
        b, cr, ct = 10.0, 3.0, 1.0
        w = geo.wing_planform(b, cr, ct)
        self.assertAlmostEqual(w["area"], 0.5 * b * (cr + ct), places=9)
        lam = ct / cr
        mac = (2.0 / 3.0) * cr * (1 + lam + lam * lam) / (1 + lam)
        self.assertAlmostEqual(w["mean_aerodynamic_chord"], mac, places=9)
        self.assertAlmostEqual(w["mac_span_station"],
                               (b / 6.0) * (1 + 2 * lam) / (1 + lam), places=9)

    def test_rectangular_wing_sweep_conversion_identity(self):
        # With no taper the quarter chord line parallels the LE line.
        w = geo.wing_planform(10.0, 2.0, 2.0, le_sweep_deg=25.0)
        self.assertAlmostEqual(w["qc_sweep_deg"], 25.0, places=9)

    def test_tapered_wing_quarter_chord_less_swept(self):
        w = geo.wing_planform(20.0, 4.0, 1.0, le_sweep_deg=30.0)
        self.assertLess(w["qc_sweep_deg"], w["le_sweep_deg"])

    def test_centroid_at_mac_station(self):
        w = geo.wing_planform(12.0, 2.0, 1.0, le_sweep_deg=20.0,
                              dihedral_deg=5.0)
        xc, yc, zc = w["centroid"]
        self.assertAlmostEqual(yc, w["mac_span_station"], places=9)
        self.assertAlmostEqual(zc, yc * math.tan(math.radians(5.0)), places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            geo.wing_planform(0.0, 2.0, 2.0)
        with self.assertRaises(ValueError):
            geo.wing_planform(10.0, -1.0, 2.0)
        with self.assertRaises(ValueError):
            geo.wing_planform(10.0, 2.0, 3.0)  # tip > root
        with self.assertRaises(ValueError):
            geo.wing_planform(10.0, 2.0, 2.0, le_sweep_deg=-5.0)


class WettedAreaTest(unittest.TestCase):
    def test_wetted_area_increases_with_size(self):
        small = geo.wetted_surface(20.0)
        large = geo.wetted_surface(40.0)
        self.assertGreater(large, small)
        self.assertAlmostEqual(large, 2.0 * small, places=9)

    def test_wetted_to_planform_ratio(self):
        r = geo.wetted_to_planform(25.0, thickness_ratio=0.12)
        self.assertAlmostEqual(r, 2.0 * (1.0 + 0.2 * 0.12), places=9)

    def test_wetted_areas_of_assembled_geometry(self):
        g = geo.build_geometry(
            wing={"b": 12.0, "c_root": 2.0, "c_tip": 2.0},
            fuselage=[(0.0, 0.0), (10.0, 1.0), (20.0, 0.0)],
            tails=[{"name": "ht", "b": 4.0, "c_root": 1.0, "c_tip": 0.5}],
            nacelles=[(3.0, 1.2)],
        )
        wing_wet = g["components"][0]["wetted_area"]
        self.assertAlmostEqual(wing_wet, 2.0 * 24.0 * (1.0 + 0.2 * 0.12),
                               places=9)
        # Total wetted area is the sum of the component wetted areas.
        self.assertAlmostEqual(
            g["totals"]["wetted_area"],
            sum(c["wetted_area"] for c in g["components"]), places=9)


class FuselageVolumeTest(unittest.TestCase):
    def test_cylinder_volume_consistency(self):
        f = geo.fuselage_cylinder(20.0, 4.0)
        self.assertAlmostEqual(f["volume"], math.pi * 4.0 * 20.0, places=9)
        self.assertAlmostEqual(f["wetted_area"], math.pi * 4.0 * 20.0,
                               places=9)
        self.assertAlmostEqual(f["centroid"][0], 10.0, places=9)

    def test_cylinder_equivalent_to_stations(self):
        # Two stations at constant radius reproduce the cylinder.
        f1 = geo.fuselage_cylinder(10.0, 2.0)
        f2 = geo.fuselage_from_stations([(0.0, 1.0), (10.0, 1.0)])
        self.assertAlmostEqual(f1["volume"], f2["volume"], places=6)
        self.assertAlmostEqual(f1["wetted_area"], f2["wetted_area"], places=6)

    def test_volume_grows_with_length(self):
        short = geo.fuselage_cylinder(10.0, 2.0)
        long = geo.fuselage_cylinder(20.0, 2.0)
        self.assertGreater(long["volume"], short["volume"])
        self.assertAlmostEqual(long["volume"], 2.0 * short["volume"], places=9)

    def test_invalid_stations_raise(self):
        with self.assertRaises(ValueError):
            geo.fuselage_from_stations([(0.0, 1.0)])
        with self.assertRaises(ValueError):
            geo.fuselage_from_stations([(0.0, 1.0), (0.0, 1.0)])
        with self.assertRaises(ValueError):
            geo.fuselage_from_stations([(0.0, -1.0), (10.0, 1.0)])


class NacelleAndAssemblyTest(unittest.TestCase):
    def test_nacelle_volume_consistency(self):
        n = geo.nacelle_geometry(4.0, 1.6)
        expected = (math.pi * 1.6 ** 2 * 4.0 / 4.0
                    - math.pi * 1.6 ** 3 / 24.0)
        self.assertAlmostEqual(n["volume"], expected, places=9)
        self.assertAlmostEqual(n["wetted_area"], math.pi * 1.6 * 4.0,
                               places=9)

    def test_component_volume_total(self):
        g = geo.build_geometry(
            fuselage=[(0.0, 1.0), (10.0, 1.0)],
            nacelles=[(3.0, 1.0)],
        )
        expected = (math.pi * 10.0
                    + math.pi * 1.0 ** 2 * 3.0 / 4.0 - math.pi / 24.0)
        self.assertAlmostEqual(g["totals"]["component_volume"], expected,
                               places=6)

    def test_fuselage_centroid_mid_length(self):
        f = geo.fuselage_from_stations([(0.0, 1.0), (10.0, 1.0)])
        self.assertAlmostEqual(f["centroid"][0], 5.0, places=9)

    def test_nacelle_invalid_raises(self):
        with self.assertRaises(ValueError):
            geo.nacelle_geometry(0.5, 1.6)  # length below cap radius
        with self.assertRaises(ValueError):
            geo.nacelle_geometry(3.0, -1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
