"""Contract test for the hydraulic-actuator-sizing logic module.

Offline, deterministic, stdlib unittest. Run from the repo root:

    python3 skills/vehicle-design/sizing/hydraulic-actuator-sizing/\
        scripts/test_hydraulic_actuator_sizing.py

Worked example (spec): load 40000 N, system pressure 207 bar (20.7e6
Pa), rod length 0.35 m, stroke 0.20 m. Real module outputs used as
assert targets: piston_area = 2.3618e-3 m2 (spec 2.361e-3), bore
54.84 mm (spec 54.8), rod buckling diameter 17.72 mm (spec 17.7 within
1 mm), preferred bore 63 mm and rod 20 mm, annulus area 2.8031e-3 m2
(spec 2.807e-3), retract capability 47474 N (spec 47530, within 1%),
rod stress 127.3 MPa below the 1100 MPa yield, mass 3.13 kg (spec 3.13
within 10%), verdict pass. The review fails when the annulus cannot
carry the load (30000 N at 0.20 m rod length gives retract 29849 N).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hydraulic_actuator_sizing_logic import (  # noqa: E402
    PRESSURE_MARGIN,
    MECHANICAL_EFFICIENCY,
    BUCKLING_FACTOR_OF_SAFETY,
    MODULUS_ROD,
    ROD_DENSITY,
    STEEL_YIELD,
    PREFERRED_BORES_MM,
    PREFERRED_RODS_MM,
    piston_area,
    bore_diameter,
    annulus_area,
    retract_capability,
    rod_buckling_diameter,
    select_preferred,
    actuator_mass,
    actuator_review,
)

LOAD = 40000.0
PRESSURE = 20.7e6
ROD_LENGTH = 0.35
STROKE = 0.20


class TestPistonArea(unittest.TestCase):
    def test_anchor_value(self):
        area = piston_area(LOAD, PRESSURE)
        self.assertAlmostEqual(area, 2.361e-3, delta=2.361e-3 * 0.001)
        self.assertAlmostEqual(area, LOAD * PRESSURE_MARGIN
                               / (PRESSURE * MECHANICAL_EFFICIENCY), places=12)

    def test_linear_in_load(self):
        self.assertAlmostEqual(
            piston_area(2 * LOAD, PRESSURE),
            2 * piston_area(LOAD, PRESSURE), places=12)

    def test_nonpositive_inputs_raise(self):
        for bad in (0.0, -1000.0):
            with self.assertRaises(ValueError):
                piston_area(bad, PRESSURE)
            with self.assertRaises(ValueError):
                piston_area(LOAD, bad)


class TestBoreDiameter(unittest.TestCase):
    def test_anchor_millimetres(self):
        bore_mm = bore_diameter(piston_area(LOAD, PRESSURE)) * 1000.0
        self.assertAlmostEqual(bore_mm, 54.8, delta=0.1)

    def test_area_inverse_identity(self):
        area = piston_area(LOAD, PRESSURE)
        bore = bore_diameter(area)
        self.assertAlmostEqual(math.pi / 4.0 * bore ** 2, area, places=12)

    def test_known_area_value(self):
        # A 63.0 mm bore corresponds to a 3.1172e-3 m2 piston area.
        bore = bore_diameter(3.117245e-3)
        self.assertAlmostEqual(bore * 1000.0, 63.0, delta=0.01)

    def test_nonpositive_area_raises(self):
        for bad in (0.0, -1e-4):
            with self.assertRaises(ValueError):
                bore_diameter(bad)


class TestAnnulusArea(unittest.TestCase):
    def test_anchor_value(self):
        annulus = annulus_area(0.063, 0.020)
        self.assertAlmostEqual(annulus, 2.807e-3, delta=2.807e-3 * 0.01)

    def test_zero_rod_equals_bore_area(self):
        # As the rod diameter tends to zero the annulus tends to the
        # full piston area of the bore.
        self.assertAlmostEqual(
            annulus_area(0.063, 1e-9),
            math.pi / 4.0 * 0.063 ** 2, delta=1e-12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            annulus_area(0.0, 0.02)
        with self.assertRaises(ValueError):
            annulus_area(0.063, 0.0)
        with self.assertRaises(ValueError):
            annulus_area(0.063, 0.063)
        with self.assertRaises(ValueError):
            annulus_area(0.040, 0.063)


class TestRetractCapability(unittest.TestCase):
    def test_anchor_value(self):
        retract = retract_capability(annulus_area(0.063, 0.020), PRESSURE)
        self.assertAlmostEqual(retract, 47530.0, delta=47530.0 * 0.01)
        self.assertGreaterEqual(retract, LOAD)

    def test_linear_in_annulus(self):
        annulus = annulus_area(0.063, 0.020)
        self.assertAlmostEqual(
            retract_capability(2 * annulus, PRESSURE),
            2 * retract_capability(annulus, PRESSURE), places=9)

    def test_oversized_rod_undercuts_load(self):
        # Rod 40 mm in the 63 mm bore: annulus too small for 40000 N.
        retract = retract_capability(annulus_area(0.063, 0.040), PRESSURE)
        self.assertLess(retract, LOAD)

    def test_nonpositive_inputs_raise(self):
        with self.assertRaises(ValueError):
            retract_capability(0.0, PRESSURE)
        with self.assertRaises(ValueError):
            retract_capability(1e-3, 0.0)


class TestRodBucklingDiameter(unittest.TestCase):
    def test_anchor_value(self):
        diameter_mm = rod_buckling_diameter(LOAD, ROD_LENGTH) * 1000.0
        self.assertAlmostEqual(diameter_mm, 17.7, delta=1.0)

    def test_length_doubling_scales_sqrt2(self):
        ratio = (rod_buckling_diameter(LOAD, 2 * ROD_LENGTH)
                 / rod_buckling_diameter(LOAD, ROD_LENGTH))
        self.assertAlmostEqual(ratio, math.sqrt(2.0), places=9)

    def test_load_doubling_scales_fourth_root(self):
        ratio = (rod_buckling_diameter(2 * LOAD, ROD_LENGTH)
                 / rod_buckling_diameter(LOAD, ROD_LENGTH))
        self.assertAlmostEqual(ratio, 2.0 ** 0.25, places=9)

    def test_nonpositive_inputs_raise(self):
        for bad in (0.0, -40000.0):
            with self.assertRaises(ValueError):
                rod_buckling_diameter(bad, ROD_LENGTH)
            with self.assertRaises(ValueError):
                rod_buckling_diameter(LOAD, bad)


class TestSelectPreferred(unittest.TestCase):
    def test_bore_anchor_selects_63(self):
        bore = bore_diameter(piston_area(LOAD, PRESSURE))
        self.assertEqual(select_preferred(bore, PREFERRED_BORES_MM), 63.0)

    def test_rod_anchor_selects_20(self):
        rod = rod_buckling_diameter(LOAD, ROD_LENGTH)
        self.assertEqual(select_preferred(rod, PREFERRED_RODS_MM), 20.0)

    def test_exact_preferred_size_stays(self):
        self.assertEqual(select_preferred(0.063, PREFERRED_BORES_MM), 63.0)
        self.assertEqual(select_preferred(0.016, PREFERRED_RODS_MM), 16.0)

    def test_small_value_takes_first_preferred(self):
        self.assertEqual(select_preferred(0.004, PREFERRED_RODS_MM), 12.0)

    def test_no_coverage_raises(self):
        with self.assertRaises(ValueError):
            select_preferred(0.150, PREFERRED_BORES_MM)
        with self.assertRaises(ValueError):
            select_preferred(0.0, PREFERRED_RODS_MM)


class TestActuatorMass(unittest.TestCase):
    def test_anchor_value(self):
        mass = actuator_mass(0.063, 0.020, STROKE)
        self.assertAlmostEqual(mass, 3.13, delta=3.13 * 0.10)
        self.assertAlmostEqual(mass, 3.1337371011594923, places=9)

    def test_linear_in_stroke(self):
        self.assertAlmostEqual(
            actuator_mass(0.063, 0.020, 2 * STROKE),
            2 * actuator_mass(0.063, 0.020, STROKE), places=9)

    def test_density_factor_form(self):
        # mass = density * stroke * pi/4 * (0.6*bore^2 + 0.4*rod^2)
        expect = (ROD_DENSITY * STROKE * math.pi / 4.0
                  * (0.6 * 0.063 ** 2 + 0.4 * 0.020 ** 2))
        self.assertAlmostEqual(actuator_mass(0.063, 0.020, STROKE),
                               expect, places=9)

    def test_nonpositive_inputs_raise(self):
        for bad in (0.0, -0.2):
            with self.assertRaises(ValueError):
                actuator_mass(0.063, 0.020, bad)
        with self.assertRaises(ValueError):
            actuator_mass(0.063, 0.063, STROKE)


class TestActuatorReview(unittest.TestCase):
    def test_dict_keys_exact(self):
        review = actuator_review(LOAD, PRESSURE, ROD_LENGTH, STROKE)
        self.assertEqual(list(review.keys()), [
            "piston_area", "bore_mm", "annulus_area", "rod_buckling_mm",
            "bore_pref_mm", "rod_pref_mm", "retract_capability_N",
            "rod_stress_Pa", "buckling_margin", "mass_kg", "verdict"])

    def test_anchor_verdict_pass(self):
        review = actuator_review(LOAD, PRESSURE, ROD_LENGTH, STROKE)
        self.assertEqual(review["verdict"], "pass")
        self.assertEqual(review["bore_pref_mm"], 63.0)
        self.assertEqual(review["rod_pref_mm"], 20.0)
        self.assertAlmostEqual(review["piston_area"], 2.361e-3,
                               delta=2.361e-3 * 0.001)
        self.assertGreaterEqual(review["retract_capability_N"], LOAD)

    def test_annulus_too_small_verdict_fail(self):
        # 30000 N with a 0.20 m rod: bore 50 mm, rod 16 mm, retract
        # 29849 N cannot cover the load.
        review = actuator_review(30000.0, PRESSURE, 0.20, 0.15)
        self.assertEqual(review["verdict"], "fail")
        self.assertEqual(review["bore_pref_mm"], 50.0)
        self.assertEqual(review["rod_pref_mm"], 16.0)
        self.assertLess(review["retract_capability_N"], 30000.0)

    def test_rod_stress_below_yield(self):
        review = actuator_review(LOAD, PRESSURE, ROD_LENGTH, STROKE)
        self.assertAlmostEqual(review["rod_stress_Pa"], 127.3e6,
                               delta=127.3e6 * 0.01)
        self.assertLessEqual(review["rod_stress_Pa"], STEEL_YIELD)
        self.assertAlmostEqual(
            review["rod_stress_Pa"],
            LOAD / (math.pi / 4.0 * 0.020 ** 2), places=6)

    def test_buckling_margin_at_least_fos(self):
        review = actuator_review(LOAD, PRESSURE, ROD_LENGTH, STROKE)
        self.assertGreaterEqual(review["buckling_margin"],
                                BUCKLING_FACTOR_OF_SAFETY)
        # Euler critical load on the 20 mm preferred rod over 0.35 m.
        inertia = math.pi / 64.0 * 0.020 ** 4
        critical = (math.pi ** 2 * MODULUS_ROD * inertia / ROD_LENGTH ** 2)
        self.assertAlmostEqual(review["buckling_margin"],
                               critical / LOAD, places=9)

    def test_mass_uses_preferred_sizes(self):
        review = actuator_review(LOAD, PRESSURE, ROD_LENGTH, STROKE)
        self.assertAlmostEqual(review["mass_kg"],
                               actuator_mass(0.063, 0.020, STROKE), places=9)

    def test_nonpositive_inputs_raise(self):
        with self.assertRaises(ValueError):
            actuator_review(0.0, PRESSURE, ROD_LENGTH, STROKE)
        with self.assertRaises(ValueError):
            actuator_review(LOAD, 0.0, ROD_LENGTH, STROKE)
        with self.assertRaises(ValueError):
            actuator_review(LOAD, PRESSURE, 0.0, STROKE)
        with self.assertRaises(ValueError):
            actuator_review(LOAD, PRESSURE, ROD_LENGTH, 0.0)

    def test_deterministic_repeat(self):
        first = actuator_review(LOAD, PRESSURE, ROD_LENGTH, STROKE)
        second = actuator_review(LOAD, PRESSURE, ROD_LENGTH, STROKE)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
