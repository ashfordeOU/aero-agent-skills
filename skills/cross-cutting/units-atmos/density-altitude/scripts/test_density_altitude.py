#!/usr/bin/env python3
"""Contract test: density altitude (cross-cutting/units-atmos).

Exercises scripts/density_altitude_logic.py (stdlib unittest, offline).
Covers the ISA identity, the worked magnitude anchors (sea level hot
day, 10000 ft warm and cold days), the domain-precedent cross-check,
monotonicity, closed-form versus bisection agreement on both branches,
ValueError rejection of non-physical inputs, the summary dict
contract, and run-to-run determinism.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import density_altitude_logic as da  # noqa: E402


def _isa_density_ratio_m(h_m):
    """Independent forward ISA density ratio used only by the bisection."""
    if h_m <= da.TROPOPAUSE:
        return (1.0 - da.L * h_m / da.T0) ** da.DENSITY_EXP
    return da.SIGMA_TROP * math.exp(-(h_m - da.TROPOPAUSE) / da.STRAT_SCALE)


def _bisect_density_altitude_m(hp_m, oat_k):
    """Bisection inverse of the ISA density law (200 iterations)."""
    sigma = da.isa_pressure_ratio(hp_m) * da.T0 / oat_k
    lo, hi = -1000.0, 60000.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _isa_density_ratio_m(mid) > sigma:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


class ConstantsAndSeaLevelTest(unittest.TestCase):
    def test_module_constants(self):
        self.assertEqual(da.T0, 288.15)
        self.assertEqual(da.L, 0.0065)
        self.assertEqual(da.G, 9.80665)
        self.assertEqual(da.R, 287.0)
        self.assertEqual(da.P0, 101325.0)
        self.assertEqual(da.TROPOPAUSE, 11000.0)
        self.assertEqual(da.T_STRAT, 216.65)

    def test_sea_level_state(self):
        self.assertAlmostEqual(da.isa_temperature_k(0.0), 288.15, places=6)
        self.assertAlmostEqual(da.isa_pressure_ratio(0.0), 1.0, places=9)
        self.assertAlmostEqual(da.isa_deviation_k(0.0, 288.15), 0.0, places=9)


class IsaTemperatureTest(unittest.TestCase):
    def test_troposphere_linear_lapse(self):
        self.assertAlmostEqual(da.isa_temperature_k(3048.0), 268.338, delta=1e-9)

    def test_tropopause_and_stratosphere_isothermal(self):
        self.assertAlmostEqual(da.isa_temperature_k(11000.0), 216.65, places=9)
        self.assertAlmostEqual(da.isa_temperature_k(20000.0), 216.65, places=9)

    def test_small_negative_geopotential_and_boundary(self):
        # -500 m allowed (below-sea-level field altitude); -1000 m boundary ok.
        self.assertAlmostEqual(da.isa_temperature_k(-500.0), 291.4, delta=1e-9)
        self.assertAlmostEqual(da.isa_temperature_k(-1000.0), 294.65, delta=1e-9)
        with self.assertRaises(ValueError):
            da.isa_temperature_k(-1000.5)


class IsaPressureRatioTest(unittest.TestCase):
    def test_sea_level_and_tropopause_anchors(self):
        self.assertAlmostEqual(da.isa_pressure_ratio(0.0), 1.0, places=9)
        self.assertAlmostEqual(da.isa_pressure_ratio(11000.0), 0.2233, delta=1e-3)

    def test_monotone_decrease(self):
        vals = [da.isa_pressure_ratio(h) for h in (-500.0, 0.0, 3048.0, 11000.0, 20000.0)]
        self.assertEqual(vals, sorted(vals, reverse=True))
        self.assertGreater(vals[0], vals[-1])

    def test_continuous_across_tropopause(self):
        a = da.isa_pressure_ratio(11000.0)
        b = da.isa_pressure_ratio(11000.0 + 1e-6)
        self.assertAlmostEqual(a, b, delta=1e-9)
        self.assertLess(b, a)

    def test_rejects_low_altitude(self):
        with self.assertRaises(ValueError):
            da.isa_pressure_ratio(-2000.0)


class IsaDeviationTest(unittest.TestCase):
    def test_zero_on_isa_day(self):
        oat = da.isa_temperature_k(3048.0)
        self.assertAlmostEqual(da.isa_deviation_k(3048.0, oat), 0.0, places=9)

    def test_warm_positive_and_cold_negative(self):
        self.assertAlmostEqual(da.isa_deviation_k(0.0, 303.15), 15.0, places=9)
        self.assertAlmostEqual(
            da.isa_deviation_k(3048.0, da.isa_temperature_k(3048.0) - 10.0),
            -10.0,
            places=9,
        )
        with self.assertRaises(ValueError):
            da.isa_deviation_k(0.0, 0.0)


class DensityRatioTest(unittest.TestCase):
    def test_standard_and_hot_day_ratio(self):
        self.assertAlmostEqual(
            da.density_ratio_from_pressure_temperature(101325.0, 288.15), 1.0, places=9
        )
        self.assertAlmostEqual(
            da.density_ratio_from_pressure_temperature(101325.0, 303.15),
            288.15 / 303.15,
            places=9,
        )

    def test_scales_with_pressure(self):
        self.assertAlmostEqual(
            da.density_ratio_from_pressure_temperature(80000.0, 288.15),
            80000.0 / 101325.0,
            places=9,
        )

    def test_rejects_non_physical_inputs(self):
        for bad_p in (0.0, -100.0):
            with self.assertRaises(ValueError):
                da.density_ratio_from_pressure_temperature(bad_p, 288.15)
        for bad_t in (0.0, -273.15):
            with self.assertRaises(ValueError):
                da.density_ratio_from_pressure_temperature(101325.0, bad_t)


class IsaIdentityTest(unittest.TestCase):
    def test_density_altitude_equals_pressure_altitude_on_isa_day(self):
        # Troposphere: 0 m and 3048 m (10000 ft) identities.
        self.assertAlmostEqual(da.density_altitude_m(0.0, 288.15), 0.0, places=9)
        self.assertAlmostEqual(
            da.density_altitude_m(3048.0, da.isa_temperature_k(3048.0)),
            3048.0,
            delta=0.2,
        )
        self.assertAlmostEqual(
            da.density_altitude_m(11000.0, 216.65), 11000.0, delta=0.2
        )
        # Stratosphere: 40000 ft (12192 m) with the isothermal OAT.
        self.assertAlmostEqual(
            da.density_altitude_m(12192.0, 216.65), 12192.0, delta=0.5
        )


class WorkedMagnitudeTest(unittest.TestCase):
    def test_sea_level_hot_day_worked_bounds(self):
        # OAT 30 C (15 K above the standard day), sea level.
        h_m = da.density_altitude_m(0.0, 303.15)
        self.assertAlmostEqual(h_m, 525.3365385691164, delta=0.05)
        self.assertAlmostEqual(h_m, 525.46, delta=0.5)
        h_ft = da.density_altitude_ft(0.0, 30.0)
        self.assertAlmostEqual(h_ft, 1723.5450740456574, delta=0.05)
        self.assertAlmostEqual(h_ft, 1723.94, delta=1.0)

    def test_ten_k_ft_warm_day_worked_bounds(self):
        # 10000 ft pressure altitude, OAT = ISA + 10 K (5.19 C).
        oat_c = da.isa_temperature_k(3048.0) - 273.15 + 10.0
        h_ft = da.density_altitude_ft(10000.0, oat_c)
        self.assertAlmostEqual(h_ft, 11159.175096010893, delta=0.05)
        self.assertAlmostEqual(h_ft, 11159.44, delta=1.0)
        self.assertGreater(h_ft, 10000.0)

    def test_ten_k_ft_cold_day_worked_bounds(self):
        # 10000 ft pressure altitude, OAT = ISA - 10 K (-14.81 C).
        oat_c = da.isa_temperature_k(3048.0) - 273.15 - 10.0
        h_ft = da.density_altitude_ft(10000.0, oat_c)
        self.assertAlmostEqual(h_ft, 8786.211124211623, delta=0.05)
        self.assertAlmostEqual(h_ft, 8785.93, delta=1.0)
        self.assertLess(h_ft, 10000.0)

    def test_domain_precedent_cross_check(self):
        # climb-performance-flight-test bisection: 10000 ft, OAT 15 C
        # absolute (ISA +19.8 K) gives about 12248.13 ft.
        self.assertAlmostEqual(da.density_altitude_ft(10000.0, 15.0), 12248.13, delta=1.0)

    def test_warm_raises_cold_lowers_around_isa_day(self):
        cold = da.density_altitude_m(3048.0, da.isa_temperature_k(3048.0) - 10.0)
        isa = da.density_altitude_m(3048.0, da.isa_temperature_k(3048.0))
        warm = da.density_altitude_m(3048.0, da.isa_temperature_k(3048.0) + 10.0)
        self.assertLess(cold, isa)
        self.assertLess(isa, warm)


class MonotonicityTest(unittest.TestCase):
    def test_hotter_oat_raises_density_altitude(self):
        vals = [da.density_altitude_m(3048.0, oat) for oat in (250.0, 270.0, 288.15, 310.0, 330.0)]
        self.assertEqual(vals, sorted(vals))

    def test_higher_pressure_altitude_raises_density_altitude(self):
        vals = [da.density_altitude_m(hp, 288.15) for hp in (-500.0, 0.0, 1524.0, 3048.0, 6096.0)]
        self.assertEqual(vals, sorted(vals))


class ClosedFormVersusBisectionTest(unittest.TestCase):
    def test_troposphere_closed_form_matches_bisection(self):
        for hp_m, oat_k in (
            (0.0, 303.15),
            (3048.0, 278.338),
            (3048.0, 258.338),
            (-500.0, 320.0),
            (9000.0, 300.0),
            (11000.0, 216.65),
        ):
            self.assertAlmostEqual(
                da.density_altitude_m(hp_m, oat_k),
                _bisect_density_altitude_m(hp_m, oat_k),
                delta=1e-6,
            )

    def test_stratosphere_closed_form_matches_bisection(self):
        for hp_m, oat_k in (
            (12000.0, 250.0),
            (12192.0, 216.65),
            (20000.0, 230.0),
            (20000.0, 320.0),
        ):
            h = da.density_altitude_m(hp_m, oat_k)
            self.assertGreater(h, 11000.0)
            self.assertAlmostEqual(h, _bisect_density_altitude_m(hp_m, oat_k), delta=1e-6)

    def test_continuous_across_tropopause_switch(self):
        a = da.density_altitude_m(11000.0 - 1e-3, 250.0)
        b = da.density_altitude_m(11000.0 + 1e-3, 250.0)
        self.assertAlmostEqual(a, b, delta=1e-2)


class ValidationTest(unittest.TestCase):
    def test_density_altitude_m_rejects_non_physical(self):
        for bad_hp in (-1000.5, -5000.0):
            with self.assertRaises(ValueError):
                da.density_altitude_m(bad_hp, 288.15)
        for bad_oat in (0.0, -5.0, -273.15):
            with self.assertRaises(ValueError):
                da.density_altitude_m(0.0, bad_oat)

    def test_low_boundary_altitude_allowed(self):
        # -1000 m geopotential is the allowed boundary, in m and ft.
        h = da.density_altitude_m(-1000.0, 288.15)
        self.assertLess(h, 0.0)
        self.assertAlmostEqual(
            da.density_altitude_ft(-1000.0 / 0.3048, 15.0), h / 0.3048, places=9
        )

    def test_density_altitude_ft_rejects_non_physical(self):
        with self.assertRaises(ValueError):
            da.density_altitude_ft(-4000.0, 15.0)
        with self.assertRaises(ValueError):
            da.density_altitude_ft(10000.0, -280.0)
        with self.assertRaises(ValueError):
            da.density_altitude_ft(10000.0, -273.15)

    def test_summary_rejects_non_physical(self):
        with self.assertRaises(ValueError):
            da.density_altitude_summary(-2000.0, 288.15)
        with self.assertRaises(ValueError):
            da.density_altitude_summary(0.0, -10.0)


class FtWrapperTest(unittest.TestCase):
    def test_wrapper_matches_meter_form(self):
        self.assertAlmostEqual(
            da.density_altitude_ft(0.0, 30.0),
            da.density_altitude_m(0.0, 303.15) / 0.3048,
            places=9,
        )
        self.assertAlmostEqual(
            da.density_altitude_ft(10000.0, -14.812),
            da.density_altitude_m(3048.0, -14.812 + 273.15) / 0.3048,
            places=9,
        )

    def test_isa_day_identity_in_feet(self):
        oat_c = da.isa_temperature_k(3048.0) - 273.15
        self.assertAlmostEqual(da.density_altitude_ft(10000.0, oat_c), 10000.0, delta=0.2)


class SummaryTest(unittest.TestCase):
    def test_summary_keys_exact(self):
        keys = set(da.density_altitude_summary(3048.0, 303.15).keys())
        self.assertEqual(
            keys,
            {
                "hp_m",
                "oat_k",
                "isa_temp_k",
                "deviation_k",
                "density_ratio",
                "density_altitude_m",
                "density_altitude_ft",
            },
        )

    def test_summary_consistent_with_functions(self):
        s = da.density_altitude_summary(3048.0, 303.15)
        self.assertAlmostEqual(s["isa_temp_k"], da.isa_temperature_k(3048.0), places=9)
        self.assertAlmostEqual(s["deviation_k"], da.isa_deviation_k(3048.0, 303.15), places=9)
        self.assertAlmostEqual(
            s["density_ratio"],
            da.isa_pressure_ratio(3048.0) * da.T0 / 303.15,
            places=12,
        )
        self.assertAlmostEqual(s["density_altitude_m"], da.density_altitude_m(3048.0, 303.15), places=9)
        self.assertAlmostEqual(
            s["density_altitude_ft"], da.density_altitude_m(3048.0, 303.15) / 0.3048, places=9
        )

    def test_isa_day_density_ratio_anchor(self):
        # Standard density ratio at 10000 ft pressure altitude: about 0.7384.
        s = da.density_altitude_summary(3048.0, da.isa_temperature_k(3048.0))
        self.assertAlmostEqual(s["density_ratio"], 0.7384, delta=1e-4)


class DeterminismTest(unittest.TestCase):
    def test_run_to_run_identical(self):
        cases = [(hp, oat) for hp in (-500.0, 0.0, 3048.0, 11000.0, 20000.0) for oat in (216.65, 250.0, 288.15, 303.15)]
        first = [da.density_altitude_m(hp, oat) for hp, oat in cases]
        second = [da.density_altitude_m(hp, oat) for hp, oat in cases]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
