"""Contract test for the pressure-bulkhead dome sizing logic.

Offline, deterministic, stdlib unittest only. Run from the repo root:

    python3 scripts/test_pressure_bulkhead.py

Covers the wave-33 pressure-bulkhead spec: the narrowbody worked
example (a = 1.88 m, DeltaP = 0.0593 MPa, t = 2 mm, 7075 Ftu = 469 MPa,
FS = 1.5), the cylinder identities, the sphere limit of the ellipsoid,
the 2:1 knuckle compression, the hemispherical zero-ring case, cap
rise, junction ring sizing, dict key contracts, ValueError rejection
of non-physical inputs, and run-to-run determinism.
"""

import math
import sys
import unittest
from os.path import abspath, dirname, join

sys.path.insert(0, dirname(abspath(__file__)))
import pressure_bulkhead_logic as pb

# Narrowbody worked-example parameters (spec section Worked example).
P = 0.0593e6          # cabin differential pressure, Pa
A = 1.88              # barrel radius, m
T = 0.002             # dome thickness, m
FTU = 469e6           # 7075 ultimate tensile strength, Pa
FS = 1.5              # FAR 25.303 factor of safety
R_CAP = 3.76          # spherical cap radius 2*a, m
B_2TO1 = 0.94         # 2:1 ellipsoid depth a/2, m

# Real module outputs of the worked example (smoke-checked magnitudes:
# hoop 55.7 MPa, rise 0.504 m, q 96.5 kN/m, tension 181.5 kN, ring area
# about 581 mm^2, spherical-cap MS about 4.61).
HOOP_EXACT = P * A / T                      # 55.742 MPa
LONG_EXACT = HOOP_EXACT / 2.0               # 27.871 MPa
RISE_EXACT = 0.5037444817705108
Q_EXACT = 96547.97611550435                 # N/m
TENSION_EXACT = 181510.1950971482           # N
AREA_EXACT_M2 = 5.805230120377873e-4        # about 581 mm^2


def mpa(value_pa):
    """Stresses to MPa rounded to one decimal for magnitude gates."""
    return round(value_pa / 1e6, 1)


class TestCylinderMembrane(unittest.TestCase):
    """Barrel cross-check stresses: hoop and longitudinal."""

    def test_worked_barrel_stress_magnitudes(self):
        hoop, long_stress = pb.cylinder_membrane_stresses(P, A, T)
        self.assertEqual(mpa(hoop), 55.7)
        self.assertEqual(mpa(long_stress), 27.9)
        self.assertAlmostEqual(hoop, HOOP_EXACT, places=0)
        self.assertAlmostEqual(long_stress, LONG_EXACT, places=0)
        self.assertIsInstance((hoop, long_stress), tuple)

    def test_hoop_is_twice_longitudinal_exact(self):
        hoop, long_stress = pb.cylinder_membrane_stresses(P, A, T)
        self.assertEqual(hoop, 2.0 * long_stress)
        self.assertEqual(len(pb.cylinder_membrane_stresses(P, A, T)), 2)

    def test_nonpositive_inputs_value_error(self):
        for bad_p in (0.0, -1.0):
            with self.assertRaises(ValueError):
                pb.cylinder_membrane_stresses(bad_p, A, T)
        for bad_r in (0.0, -0.5):
            with self.assertRaises(ValueError):
                pb.cylinder_membrane_stresses(P, bad_r, T)
        for bad_t in (0.0, -2e-3):
            with self.assertRaises(ValueError):
                pb.cylinder_membrane_stresses(P, A, bad_t)


class TestSphericalDome(unittest.TestCase):
    """Uniform spherical cap membrane stress p*R/(2*t)."""

    def test_worked_cap_stress_55_7_mpa(self):
        sigma = pb.spherical_dome_stress(P, R_CAP, T)
        self.assertEqual(mpa(sigma), 55.7)
        self.assertAlmostEqual(sigma, HOOP_EXACT, places=0)
        self.assertEqual(sigma, P * R_CAP / (2.0 * T))

    def test_sphere_radius_2a_matches_barrel_hoop_exact(self):
        cap = pb.spherical_dome_stress(P, 2.0 * A, T)
        hoop, _ = pb.cylinder_membrane_stresses(P, A, T)
        self.assertEqual(cap, hoop)

    def test_nonpositive_inputs_value_error(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                pb.spherical_dome_stress(bad, R_CAP, T)
            with self.assertRaises(ValueError):
                pb.spherical_dome_stress(P, bad, T)
            with self.assertRaises(ValueError):
                pb.spherical_dome_stress(P, R_CAP, bad)


class TestHemisphere(unittest.TestCase):
    """Hemispherical dome R = a: 27.9 MPa everywhere, zero ring."""

    def test_hemisphere_stress_and_margin(self):
        sigma = pb.spherical_dome_stress(P, A, T)
        self.assertEqual(mpa(sigma), 27.9)
        self.assertAlmostEqual(sigma, P * A / (2.0 * T), places=0)
        summary = pb.bulkhead_summary(P, A, T, "hemisphere", FTU, FS, None)
        expected = (FTU / FS) / (P * A / (2.0 * T)) - 1.0
        self.assertAlmostEqual(summary["margin_of_safety"], expected, places=4)

    def test_hemisphere_summary_ring_zero_and_geometry(self):
        summary = pb.bulkhead_summary(P, A, T, "hemisphere", FTU, FS, None)
        self.assertEqual(summary["q_n_per_m"], 0.0)
        self.assertEqual(summary["ring_tension_N"], 0.0)
        self.assertEqual(summary["ring_area_m2"], 0.0)
        self.assertEqual(summary["geometry_m"]["sphere_radius_m"], A)
        self.assertEqual(summary["geometry_m"]["cap_rise_m"], A)
        for key in ("sigma_meridional_pa", "sigma_circumferential_pa"):
            self.assertEqual(summary["stresses_pa"][key], P * A / (2.0 * T))
        self.assertEqual(summary["sigma_max_pa"], P * A / (2.0 * T))


class TestEllipsoidDome(unittest.TestCase):
    """Ellipsoidal dome semi-axes a, b: apex and equator stresses."""

    def test_2to1_apex_55_7_mpa(self):
        stresses = pb.ellipsoid_dome_stresses(P, A, B_2TO1, T)
        self.assertEqual(mpa(stresses["sigma_apex"]), 55.7)
        expected = P * A * A / (2.0 * B_2TO1 * T)
        self.assertAlmostEqual(stresses["sigma_apex"], expected, places=0)

    def test_2to1_equator_meridional_27_9_mpa(self):
        stresses = pb.ellipsoid_dome_stresses(P, A, B_2TO1, T)
        self.assertEqual(mpa(stresses["sigma_equator_meridional"]), 27.9)

    def test_2to1_equator_hoop_compressive_55_7_mpa(self):
        stresses = pb.ellipsoid_dome_stresses(P, A, B_2TO1, T)
        self.assertEqual(mpa(stresses["sigma_equator_hoop"]), -55.7)
        self.assertAlmostEqual(stresses["sigma_equator_hoop"], -HOOP_EXACT,
                               places=0)

    def test_2to1_equator_hoop_formula_and_sign(self):
        stresses = pb.ellipsoid_dome_stresses(P, A, B_2TO1, T)
        self.assertLess(stresses["sigma_equator_hoop"], 0.0)
        self.assertAlmostEqual(
            stresses["sigma_equator_hoop"],
            HOOP_EXACT * (1.0 - A * A / (2.0 * B_2TO1 * B_2TO1)),
            places=0,
        )

    def test_sphere_limit_b_equals_a_identity(self):
        sphere_value = P * A / (2.0 * T)
        stresses = pb.ellipsoid_dome_stresses(P, A, A, T)
        self.assertAlmostEqual(stresses["sigma_apex"], sphere_value, places=0)
        self.assertAlmostEqual(stresses["sigma_equator_meridional"],
                               sphere_value, places=0)
        self.assertAlmostEqual(stresses["sigma_equator_hoop"], sphere_value,
                               places=0)

    def test_dict_keys_exact(self):
        stresses = pb.ellipsoid_dome_stresses(P, A, B_2TO1, T)
        self.assertEqual(
            set(stresses.keys()),
            {"sigma_apex", "sigma_equator_meridional", "sigma_equator_hoop"},
        )

    def test_nonpositive_inputs_value_error(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                pb.ellipsoid_dome_stresses(bad, A, B_2TO1, T)
            with self.assertRaises(ValueError):
                pb.ellipsoid_dome_stresses(P, bad, B_2TO1, T)
            with self.assertRaises(ValueError):
                pb.ellipsoid_dome_stresses(P, A, bad, T)
            with self.assertRaises(ValueError):
                pb.ellipsoid_dome_stresses(P, A, B_2TO1, bad)


class TestDomeCapRise(unittest.TestCase):
    """Spherical-cap rise h = R - sqrt(R^2 - a^2)."""

    def test_worked_rise_about_0_504_m(self):
        h = pb.dome_cap_rise(R_CAP, A)
        self.assertAlmostEqual(h, RISE_EXACT, places=6)
        self.assertTrue(0.50 <= h <= 0.51)
        self.assertAlmostEqual(h, R_CAP - math.sqrt(R_CAP**2 - A**2), places=9)

    def test_rise_equals_radius_at_hemisphere_boundary(self):
        self.assertEqual(pb.dome_cap_rise(A, A), A)

    def test_value_error_barrel_exceeds_sphere(self):
        with self.assertRaises(ValueError):
            pb.dome_cap_rise(3.76, 4.0)
        with self.assertRaises(ValueError):
            pb.dome_cap_rise(0.0, A)
        with self.assertRaises(ValueError):
            pb.dome_cap_rise(R_CAP, 0.0)


class TestJunctionRing(unittest.TestCase):
    """Unbalanced spherical-cap junction ring load and tension."""

    def test_worked_q_about_96_5_kn_m(self):
        ring = pb.junction_ring_load(P, A, R_CAP, RISE_EXACT)
        self.assertAlmostEqual(ring["q_n_per_m"], Q_EXACT, delta=Q_EXACT * 0.01)
        self.assertTrue(96.0e3 <= ring["q_n_per_m"] <= 97.0e3)

    def test_worked_tension_about_181_5_kn(self):
        ring = pb.junction_ring_load(P, A, R_CAP, RISE_EXACT)
        self.assertAlmostEqual(ring["ring_tension_N"], TENSION_EXACT,
                               delta=TENSION_EXACT * 0.01)
        self.assertTrue(180.0e3 <= ring["ring_tension_N"] <= 183.0e3)
        self.assertEqual(ring["ring_tension_N"], ring["q_n_per_m"] * A)

    def test_dict_keys_exact(self):
        ring = pb.junction_ring_load(P, A, R_CAP, RISE_EXACT)
        self.assertEqual(set(ring.keys()), {"q_n_per_m", "ring_tension_N"})

    def test_hemisphere_zero_exact(self):
        ring = pb.junction_ring_load(P, A, A, A)
        self.assertEqual(ring["q_n_per_m"], 0.0)
        self.assertEqual(ring["ring_tension_N"], 0.0)

    def test_value_errors(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                pb.junction_ring_load(bad, A, R_CAP, RISE_EXACT)
            with self.assertRaises(ValueError):
                pb.junction_ring_load(P, bad, R_CAP, RISE_EXACT)
            with self.assertRaises(ValueError):
                pb.junction_ring_load(P, A, bad, RISE_EXACT)
            with self.assertRaises(ValueError):
                pb.junction_ring_load(P, A, R_CAP, bad)
        with self.assertRaises(ValueError):
            pb.junction_ring_load(P, A, R_CAP, R_CAP + 0.1)


class TestJunctionRingArea(unittest.TestCase):
    """Required ring cross-section area A = F*FS/sigma_ultimate."""

    def test_worked_area_about_581_mm2(self):
        area_m2 = pb.junction_ring_area(TENSION_EXACT, FTU, FS)
        self.assertAlmostEqual(area_m2, AREA_EXACT_M2, delta=AREA_EXACT_M2 * 0.01)
        self.assertTrue(570.0 <= area_m2 * 1e6 <= 590.0)
        self.assertAlmostEqual(area_m2 * 1e6, 581.0, delta=1.0)
        self.assertEqual(area_m2, TENSION_EXACT * FS / FTU)

    def test_nonpositive_inputs_value_error(self):
        for bad in (0.0, -100.0):
            with self.assertRaises(ValueError):
                pb.junction_ring_area(bad, FTU, FS)
            with self.assertRaises(ValueError):
                pb.junction_ring_area(TENSION_EXACT, bad, FS)
            with self.assertRaises(ValueError):
                pb.junction_ring_area(TENSION_EXACT, FTU, bad)


class TestBulkheadSummary(unittest.TestCase):
    """Full sizing summary: stresses, margin, ring area."""

    def test_spherical_cap_margin_about_4_61(self):
        summary = pb.bulkhead_summary(P, A, T, "spherical-cap", FTU, FS, R_CAP)
        self.assertAlmostEqual(summary["margin_of_safety"], 4.61, delta=0.02)
        self.assertAlmostEqual(summary["reserve_factor"], 5.61, delta=0.02)
        expected = (FTU / FS) / HOOP_EXACT - 1.0
        self.assertAlmostEqual(summary["margin_of_safety"], expected, places=4)

    def test_spherical_cap_ring_terms_and_keys(self):
        summary = pb.bulkhead_summary(P, A, T, "spherical-cap", FTU, FS, R_CAP)
        self.assertAlmostEqual(summary["q_n_per_m"], Q_EXACT, delta=1.0)
        self.assertAlmostEqual(summary["ring_tension_N"], TENSION_EXACT,
                               delta=1.0)
        self.assertAlmostEqual(summary["ring_area_m2"], AREA_EXACT_M2,
                               delta=1e-6)
        self.assertEqual(summary["sigma_max_pa"], HOOP_EXACT)
        for key in ("sigma_meridional_pa", "sigma_circumferential_pa"):
            self.assertEqual(summary["stresses_pa"][key], HOOP_EXACT)
        self.assertEqual(
            set(summary.keys()),
            {"dome_type", "geometry_m", "stresses_pa", "sigma_max_pa",
             "allowable_pa", "margin_of_safety", "reserve_factor",
             "q_n_per_m", "ring_tension_N", "ring_area_m2"},
        )

    def test_ellipsoidal_summary_values_and_no_ring(self):
        summary = pb.bulkhead_summary(P, A, T, "ellipsoidal", FTU, FS, B_2TO1)
        stresses = summary["stresses_pa"]
        self.assertEqual(mpa(stresses["sigma_apex"]), 55.7)
        self.assertEqual(mpa(stresses["sigma_equator_meridional"]), 27.9)
        self.assertEqual(mpa(stresses["sigma_equator_hoop"]), -55.7)
        self.assertEqual(summary["sigma_max_pa"], HOOP_EXACT)
        self.assertAlmostEqual(summary["margin_of_safety"], 4.61, delta=0.02)
        self.assertIsNone(summary["q_n_per_m"])
        self.assertIsNone(summary["ring_tension_N"])
        self.assertIsNone(summary["ring_area_m2"])
        self.assertEqual(summary["geometry_m"]["semi_axis_a_m"], A)
        self.assertEqual(summary["geometry_m"]["semi_axis_b_m"], B_2TO1)

    def test_ellipsoid_axes_tuple_contract(self):
        matching = pb.bulkhead_summary(P, A, T, "ellipsoidal", FTU, FS,
                                       (A, B_2TO1))
        depth_only = pb.bulkhead_summary(P, A, T, "ellipsoidal", FTU, FS,
                                         B_2TO1)
        self.assertEqual(matching["stresses_pa"], depth_only["stresses_pa"])
        with self.assertRaises(ValueError):
            pb.bulkhead_summary(P, A, T, "ellipsoidal", FTU, FS, (A + 0.1, 1.0))
        with self.assertRaises(ValueError):
            pb.bulkhead_summary(P, A, T, "ellipsoidal", FTU, FS, (A,))

    def test_ellipsoid_margin_matches_formula(self):
        summary = pb.bulkhead_summary(P, A, T, "ellipsoidal", FTU, FS, B_2TO1)
        expected = (FTU / FS) / HOOP_EXACT - 1.0
        self.assertAlmostEqual(summary["margin_of_safety"], expected, places=4)

    def test_nonpositive_and_unknown_inputs_value_error(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                pb.bulkhead_summary(bad, A, T, "spherical-cap", FTU, FS, R_CAP)
            with self.assertRaises(ValueError):
                pb.bulkhead_summary(P, bad, T, "spherical-cap", FTU, FS, R_CAP)
            with self.assertRaises(ValueError):
                pb.bulkhead_summary(P, A, bad, "spherical-cap", FTU, FS, R_CAP)
            with self.assertRaises(ValueError):
                pb.bulkhead_summary(P, A, T, "spherical-cap", bad, FS, R_CAP)
            with self.assertRaises(ValueError):
                pb.bulkhead_summary(P, A, T, "spherical-cap", FTU, bad, R_CAP)
        with self.assertRaises(ValueError):
            pb.bulkhead_summary(P, A, T, "torispherical", FTU, FS, R_CAP)
        with self.assertRaises(ValueError):
            pb.bulkhead_summary(P, A, T, "spherical-cap", FTU, FS, A - 0.5)


class TestDeterminism(unittest.TestCase):
    """Identical floats run to run (no RNG, no state)."""

    def test_run_to_run_identical_and_consistent(self):
        first = pb.bulkhead_summary(P, A, T, "spherical-cap", FTU, FS, R_CAP)
        second = pb.bulkhead_summary(P, A, T, "spherical-cap", FTU, FS, R_CAP)
        self.assertEqual(first, second)
        self.assertEqual(pb.cylinder_membrane_stresses(P, A, T),
                         pb.cylinder_membrane_stresses(P, A, T))
        summary = pb.bulkhead_summary(P, A, T, "ellipsoidal", FTU, FS, B_2TO1)
        direct = pb.ellipsoid_dome_stresses(P, A, B_2TO1, T)
        self.assertEqual(summary["stresses_pa"], direct)


if __name__ == "__main__":
    unittest.main()
