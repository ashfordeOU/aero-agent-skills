#!/usr/bin/env python3
"""Gate 3 contract test: aerospace unit conversion.

Exercises scripts/unit_conversion_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - deterministic factor
conversion for length, speed (incl. Mach), temperature (offset
scales), pressure, density, mass, force; altitude conventions;
invalid-input handling.

Expected values below are hand-computed:
- 1000 m / 0.3048 = 3280.8399 ft
- 1 NM = 1852 m; 1852 / 0.3048 = 6076.1155 ft
- 250 kt * 1852/3600 = 128.6111 m/s
- 1 kt = (1852/3600)/0.3048 = 1.6878 ft/s
- 0.5 mach at ISA sea level = 0.5 * 340.294 = 170.147 m/s
- 32 F = (32+459.67)*5/9 K = 273.15 K = 0 C
- 100 C = 373.15 K = 671.67 R - 459.67 = 212 F
- 1 psi = 6894.757293168 Pa; 101325 Pa = 14.6959 psi
- 29.92 inHg * 3386.389 / 100 = 1013.2076 hPa
- 1 slug = 14.59390294 kg = 32.1740 lb
- 1 lbf = 0.45359237 kg * 9.80665 = 4.4482216152605 N
- ISA tropopause pressure 22632.06 Pa inverts to about 11000 m
- geopotential of 11000 m = 11000 * 6356766/6367766 = 10981.0 m
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unit_conversion_logic as uc  # noqa: E402


class LengthTest(unittest.TestCase):
    def test_m_to_ft(self):
        # 1000 m / 0.3048 = 3280.8399 ft
        self.assertAlmostEqual(uc.convert_length(1000.0, "m", "ft"),
                               3280.8399, places=4)

    def test_nm_to_m(self):
        # 1 NM = 1852 m exactly
        self.assertAlmostEqual(uc.convert_length(1.0, "NM", "m"), 1852.0,
                               places=9)

    def test_nm_to_ft(self):
        # 1852 / 0.3048 = 6076.1155 ft
        self.assertAlmostEqual(uc.convert_length(1.0, "nm", "ft"),
                               6076.1155, places=4)

    def test_identity(self):
        self.assertEqual(uc.convert_length(3.0, "ft", "foot"), 3.0)


class SpeedTest(unittest.TestCase):
    def test_kt_to_mps(self):
        # 250 * 1852/3600 = 128.6111 m/s
        self.assertAlmostEqual(uc.convert_speed(250.0, "kt", "m/s"),
                               128.6111, places=4)

    def test_kt_to_fps(self):
        # (1852/3600)/0.3048 = 1.6878 ft/s
        self.assertAlmostEqual(uc.convert_speed(1.0, "kts", "ft/s"),
                               1.6878, places=4)

    def test_mach_to_mps_default_sos(self):
        # 0.5 * 340.294 = 170.147 m/s
        self.assertAlmostEqual(uc.convert_speed(0.5, "mach", "m/s"),
                               170.147, places=4)

    def test_mps_to_mach_explicit_sos(self):
        # 300 m/s at a 300 m/s speed of sound is exactly Mach 1
        self.assertAlmostEqual(uc.convert_speed(300.0, "m/s", "mach",
                                                speed_of_sound_mps=300.0),
                               1.0, places=9)

    def test_mach_from_speed(self):
        # 170.147 / 340.294 = 0.5
        self.assertAlmostEqual(uc.mach_from_speed(170.147, 340.294),
                               0.5, places=6)
        self.assertAlmostEqual(uc.mach_from_speed(340.294, 340.294),
                               1.0, places=9)

    def test_mach_to_mach(self):
        self.assertAlmostEqual(uc.convert_speed(0.8, "mach", "mach"),
                               0.8, places=9)


class TemperatureTest(unittest.TestCase):
    def test_c_to_k(self):
        # 0 C = 273.15 K
        self.assertAlmostEqual(uc.convert_temperature(0.0, "c", "k"),
                               273.15, places=9)

    def test_f_to_c(self):
        # 32 F = (32+459.67)*5/9 - 273.15 = 0 C
        self.assertAlmostEqual(uc.convert_temperature(32.0, "f", "c"),
                               0.0, places=9)

    def test_k_to_f(self):
        # 273.15 K = 273.15*9/5 - 459.67 = 32 F
        self.assertAlmostEqual(uc.convert_temperature(273.15, "k", "f"),
                               32.0, places=9)

    def test_r_to_c(self):
        # 491.67 R = 491.67*5/9 - 273.15 = 0 C
        self.assertAlmostEqual(uc.convert_temperature(491.67, "r", "c"),
                               0.0, places=9)

    def test_c_to_f(self):
        # 100 C = (100+273.15)*9/5 - 459.67 = 212 F
        self.assertAlmostEqual(uc.convert_temperature(100.0, "c", "f"),
                               212.0, places=9)

    def test_k_to_r(self):
        # 273.15 K = 273.15*9/5 = 491.67 R
        self.assertAlmostEqual(uc.convert_temperature(273.15, "k", "r"),
                               491.67, places=9)


class PressureTest(unittest.TestCase):
    def test_pa_to_hpa(self):
        # 101325 Pa = 1013.25 hPa
        self.assertAlmostEqual(uc.convert_pressure(101325.0, "pa", "hpa"),
                               1013.25, places=9)

    def test_pa_to_psi(self):
        # 101325 / 6894.757293168 = 14.6959 psi
        self.assertAlmostEqual(uc.convert_pressure(101325.0, "pa", "psi"),
                               14.6959, places=4)

    def test_inhg_to_hpa(self):
        # 29.92 * 3386.389 / 100 = 1013.2076 hPa
        self.assertAlmostEqual(uc.convert_pressure(29.92, "inhg", "hpa"),
                               1013.2076, places=4)


class DensityMassForceTest(unittest.TestCase):
    def test_kgm3_to_slugft3(self):
        # 1.225 / 515.3788184 = 0.0023769 slug/ft3
        self.assertAlmostEqual(uc.convert_density(1.225, "kg/m3", "slug/ft3"),
                               0.0023769, places=7)

    def test_slug_to_kg(self):
        # 1 slug = 14.59390294 kg exactly
        self.assertAlmostEqual(uc.convert_mass(1.0, "slug", "kg"),
                               14.59390294, places=9)

    def test_slug_to_lb(self):
        # 14.59390294 / 0.45359237 = 32.1740 lb
        self.assertAlmostEqual(uc.convert_mass(1.0, "slug", "lb"),
                               32.1740, places=4)

    def test_lb_to_kg(self):
        # 1 lb = 0.45359237 kg exactly
        self.assertAlmostEqual(uc.convert_mass(1.0, "lb", "kg"),
                               0.45359237, places=9)

    def test_lbf_to_n(self):
        # 1 lbf = 4.4482216152605 N exactly
        self.assertAlmostEqual(uc.convert_force(1.0, "lbf", "n"),
                               4.4482216152605, places=9)

    def test_n_to_lbf(self):
        self.assertAlmostEqual(uc.convert_force(4.4482216152605, "n", "lbf"),
                               1.0, places=9)


class AltitudeTest(unittest.TestCase):
    def test_sea_level_pressure_altitude(self):
        # 101325 Pa inverts to 0 m pressure altitude
        self.assertEqual(uc.pressure_altitude_m(101325.0), 0.0)

    def test_tropopause_pressure_altitude(self):
        # 22632.06 Pa inverts to about 11000 m (ISA tropopause)
        self.assertAlmostEqual(uc.pressure_altitude_m(22632.06), 11000.0,
                               delta=50.0)

    def test_pressure_altitude_monotone(self):
        self.assertGreater(uc.pressure_altitude_m(50000.0),
                           uc.pressure_altitude_m(80000.0))

    def test_geometric_to_geopotential(self):
        # 11000 * 6356766/6367766 = 10981.0 m
        self.assertAlmostEqual(uc.geometric_to_geopotential_m(11000.0),
                               10981.0, delta=1.0)

    def test_geopotential_roundtrip(self):
        h_geom = 11000.0
        h_gp = uc.geometric_to_geopotential_m(h_geom)
        self.assertAlmostEqual(uc.geopotential_to_geometric_m(h_gp),
                               h_geom, delta=1.0)

    def test_altitude_convention_convert(self):
        self.assertAlmostEqual(
            uc.convert_altitude(11000.0, "geom", "geopotential"),
            uc.geometric_to_geopotential_m(11000.0), places=9)


class InvalidInputTest(unittest.TestCase):
    def test_bad_length_unit(self):
        with self.assertRaises(ValueError):
            uc.convert_length(1.0, "m", "parsec")

    def test_bad_speed_unit(self):
        with self.assertRaises(ValueError):
            uc.convert_speed(1.0, "kph", "m/s")

    def test_bad_temperature_unit(self):
        with self.assertRaises(ValueError):
            uc.convert_temperature(1.0, "x", "k")

    def test_bad_pressure_unit(self):
        with self.assertRaises(ValueError):
            uc.convert_pressure(1.0, "bar", "pa")

    def test_bad_density_unit(self):
        with self.assertRaises(ValueError):
            uc.convert_density(1.0, "kg/m3", "lb/ft3")

    def test_bad_mass_unit(self):
        with self.assertRaises(ValueError):
            uc.convert_mass(1.0, "kg", "stone")

    def test_bad_force_unit(self):
        with self.assertRaises(ValueError):
            uc.convert_force(1.0, "n", "dyne")

    def test_bad_altitude_unit(self):
        with self.assertRaises(ValueError):
            uc.convert_altitude(1000.0, "geom", "barometric")

    def test_nonpositive_speed_of_sound(self):
        with self.assertRaises(ValueError):
            uc.convert_speed(1.0, "m/s", "mach", speed_of_sound_mps=0.0)
        with self.assertRaises(ValueError):
            uc.mach_from_speed(100.0, 0.0)

    def test_nonpositive_pressure(self):
        with self.assertRaises(ValueError):
            uc.pressure_altitude_m(-1.0)

    def test_geometric_below_radius(self):
        with self.assertRaises(ValueError):
            uc.geometric_to_geopotential_m(-uc.EARTH_RADIUS_M)


if __name__ == "__main__":
    unittest.main(verbosity=2)
