#!/usr/bin/env python3
"""Gate 3 contract test: propellant selection.

Exercises scripts/propellant_selection_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - density impulse,
mixture bulk density, required propellant mass fraction, propellant
family classification, mission suitability verdict, and O/F ratio
verdict; invalid inputs raise ValueError.

Hand-computed anchors (written here as the analytic values):
- density_impulse(300, 1000) = 300 * 1000 = 300000 kg s/m^3
- density_impulse(450, 850) = 450 * 850 = 382500 kg s/m^3
- bulk_density(2.0, 1000, 2000) = (1+2)*1000*2000/(2000+2*1000)
  = 6000000/4000 = 1500 kg/m^3
- bulk_density(1.0, 1000, 1000) = 2*1000*1000/(1000+1000) = 1000 kg/m^3
- bulk_density(0.0, 1000, 2000) = 1*1000*2000/2000 = 1000 kg/m^3 (pure fuel)
- required_mass_fraction(4078.59, 300): mass ratio exp(4078.59/
  (9.80665*300)) = exp(ln 4) = 4, so the fraction is 1 - 1/4 = 0.75
- required_mass_fraction(9000, 450) = 1 - exp(-9000/(9.80665*450))
  = 1 - exp(-2.0394) = 0.8699
- required_mass_fraction(0.0, 300) = 1 - exp(0) = 0.0
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import propellant_selection_logic as psl  # noqa: E402


class DensityImpulseTest(unittest.TestCase):
    def test_anchor_values(self):
        self.assertAlmostEqual(psl.density_impulse(300, 1000), 300000.0)
        self.assertAlmostEqual(psl.density_impulse(450, 850), 382500.0)

    def test_higher_isp_or_density_raises_impulse(self):
        self.assertGreater(
            psl.density_impulse(350, 1000), psl.density_impulse(300, 1000)
        )
        self.assertGreater(
            psl.density_impulse(300, 1100), psl.density_impulse(300, 1000)
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.density_impulse(0, 1000)  # isp <= 0
        with self.assertRaises(ValueError):
            psl.density_impulse(-300, 1000)
        with self.assertRaises(ValueError):
            psl.density_impulse(300, 0)  # density <= 0
        with self.assertRaises(ValueError):
            psl.density_impulse(300, -1000)


class BulkDensityTest(unittest.TestCase):
    def test_anchor_values(self):
        # (1+2)*1000*2000/(2000+2*1000) = 1500 kg/m^3
        self.assertAlmostEqual(psl.bulk_density(2.0, 1000.0, 2000.0), 1500.0)
        # 2*1000*1000/(1000+1000) = 1000 kg/m^3
        self.assertAlmostEqual(psl.bulk_density(1.0, 1000.0, 1000.0), 1000.0)
        # ratio 0 is pure fuel: 1*1000*2000/2000 = 1000 kg/m^3
        self.assertAlmostEqual(psl.bulk_density(0.0, 1000.0, 2000.0), 1000.0)

    def test_bulk_density_between_component_densities(self):
        rho = psl.bulk_density(2.0, 800.0, 1200.0)
        self.assertGreater(rho, 800.0)
        self.assertLess(rho, 1200.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.bulk_density(-1.0, 1000.0, 2000.0)  # ratio < 0
        with self.assertRaises(ValueError):
            psl.bulk_density(2.0, 0.0, 2000.0)  # fuel density <= 0
        with self.assertRaises(ValueError):
            psl.bulk_density(2.0, 1000.0, 0.0)  # oxidizer density <= 0
        with self.assertRaises(ValueError):
            psl.bulk_density(2.0, -1000.0, 2000.0)


class RequiredMassFractionTest(unittest.TestCase):
    def test_anchor_values(self):
        # ratio 4 -> fraction 0.75
        self.assertAlmostEqual(
            psl.required_mass_fraction(4078.59, 300), 0.75, delta=1e-3
        )
        # 1 - exp(-9000/(9.80665*450)) = 1 - exp(-2.0394) = 0.8699
        self.assertAlmostEqual(
            psl.required_mass_fraction(9000, 450), 0.8699, delta=1e-3
        )

    def test_zero_delta_v_needs_no_propellant(self):
        self.assertAlmostEqual(psl.required_mass_fraction(0.0, 300), 0.0)

    def test_fraction_between_zero_and_one(self):
        f = psl.required_mass_fraction(3000, 300)
        self.assertGreater(f, 0.0)
        self.assertLess(f, 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.required_mass_fraction(-1.0, 300)  # delta_v < 0
        with self.assertRaises(ValueError):
            psl.required_mass_fraction(1000, 0)  # isp <= 0
        with self.assertRaises(ValueError):
            psl.required_mass_fraction(1000, -300)


class PropellantFamilyTest(unittest.TestCase):
    def test_family_classification(self):
        self.assertEqual(psl.propellant_family("LOX"), "cryogenic")
        self.assertEqual(psl.propellant_family("LH2"), "cryogenic")
        self.assertEqual(psl.propellant_family("RP-1"), "storable")
        self.assertEqual(psl.propellant_family("MMH"), "hypergolic")
        self.assertEqual(psl.propellant_family("NTO"), "hypergolic")
        self.assertEqual(psl.propellant_family("HTPB"), "solid")

    def test_case_and_space_insensitive(self):
        self.assertEqual(psl.propellant_family("  mmh "), "hypergolic")

    def test_invalid_name_raises(self):
        with self.assertRaises(ValueError):
            psl.propellant_family("water")
        with self.assertRaises(ValueError):
            psl.propellant_family("")


class PropellantVerdictTest(unittest.TestCase):
    def test_screening_heuristics(self):
        self.assertEqual(psl.propellant_verdict("cryogenic", "booster"),
                         "suitable")
        self.assertEqual(psl.propellant_verdict("cryogenic",
                                                "long-duration"), "caveat")
        self.assertEqual(psl.propellant_verdict("cryogenic",
                                                "quick-response"),
                         "unsuitable")
        self.assertEqual(psl.propellant_verdict("hypergolic",
                                                "long-duration"), "suitable")
        self.assertEqual(psl.propellant_verdict("storable", "long-duration"),
                         "suitable")
        self.assertEqual(psl.propellant_verdict("solid", "deep-space"),
                         "unsuitable")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.propellant_verdict("water", "booster")  # unknown class
        with self.assertRaises(ValueError):
            psl.propellant_verdict("cryogenic", "mars")  # unknown mission
        with self.assertRaises(ValueError):
            psl.propellant_verdict("cryogenic", "")


class OFOptimumVerdictTest(unittest.TestCase):
    def test_optimum_verdicts(self):
        self.assertEqual(psl.o_f_optimum_verdict(2.4, 2.4), "near-optimum")
        # |2.5-2.4|/2.4 = 0.0417, inside the default 5% tolerance
        self.assertEqual(psl.o_f_optimum_verdict(2.5, 2.4), "near-optimum")
        # |2.0-2.4|/2.4 = 0.167 > 0.05, below optimum
        self.assertEqual(psl.o_f_optimum_verdict(2.0, 2.4), "fuel-rich")
        # |2.8-2.4|/2.4 = 0.167 > 0.05, above optimum
        self.assertEqual(psl.o_f_optimum_verdict(2.8, 2.4), "oxidizer-rich")
        # ratio 0 is pure fuel, always fuel-rich
        self.assertEqual(psl.o_f_optimum_verdict(0.0, 2.4), "fuel-rich")

    def test_tighter_tolerance_flips_verdict(self):
        # 5% off the optimum, tolerance 2% -> no longer near-optimum
        self.assertEqual(
            psl.o_f_optimum_verdict(2.52, 2.4, tolerance=0.02),
            "oxidizer-rich",
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.o_f_optimum_verdict(-0.5, 2.4)  # ratio < 0
        with self.assertRaises(ValueError):
            psl.o_f_optimum_verdict(2.4, 0.0)  # optimum <= 0
        with self.assertRaises(ValueError):
            psl.o_f_optimum_verdict(2.4, 2.4, tolerance=0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
