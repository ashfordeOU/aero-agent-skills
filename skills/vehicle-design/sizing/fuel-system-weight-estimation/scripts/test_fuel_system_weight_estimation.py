"""Contract test for fuel-system-weight-estimation (vehicle-design/sizing).

Exercises the SKILL.md Workflow steps: step 1 (fix the total fuel weight
and the tank arrangement), step 2 (fuel_system_count_allowance_kg fixed
count term), step 3 (fuel_system_volume_term_kg volume-scaled tankage
term), step 4 (fuel_system_group_weight sum and the fuel_system_group_fraction
of the total fuel weight and MTOW), step 5 (the fuel weight and tank
count power-law identities and the sublinear fraction fall), and step 6
(ValueError rejection of non-physical inputs).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fuel_system_weight_estimation_logic as fswe

TOTAL_FUEL_KG = 22000.0
N_TANKS = 3
N_ENGINES = 2
MTOW_KG = 79000.0

EXPECTED_COUNT_ALLOWANCE_KG = 145.149558400
EXPECTED_VOLUME_TERM_KG = 229.697449925
EXPECTED_GROUP_KG = 374.847008325
EXPECTED_FRACTION_FUEL = 0.017038500
EXPECTED_FRACTION_MTOW = 0.004744899


class WorkedExampleTests(unittest.TestCase):
    """Step 1-4 of the SKILL.md Workflow: fix the total fuel weight and
    tank arrangement, evaluate the fuel_system_count_allowance_kg and
    fuel_system_volume_term_kg terms, and sum them into the
    fuel_system_group_weight for the 180-seat narrowbody worked example."""

    def setUp(self):
        self.w_a = fswe.fuel_system_count_allowance_kg(N_TANKS, N_ENGINES)
        self.w_v = fswe.fuel_system_volume_term_kg(TOTAL_FUEL_KG, N_TANKS)
        self.w_fs = fswe.fuel_system_group_weight(TOTAL_FUEL_KG, N_TANKS, N_ENGINES)

    def test_count_allowance_worked_example(self):
        self.assertAlmostEqual(
            self.w_a, EXPECTED_COUNT_ALLOWANCE_KG, delta=1e-6 * EXPECTED_COUNT_ALLOWANCE_KG
        )

    def test_volume_term_worked_example(self):
        self.assertAlmostEqual(
            self.w_v, EXPECTED_VOLUME_TERM_KG, delta=1e-6 * EXPECTED_VOLUME_TERM_KG
        )

    def test_group_weight_worked_example(self):
        self.assertAlmostEqual(
            self.w_fs, EXPECTED_GROUP_KG, delta=1e-6 * EXPECTED_GROUP_KG
        )

    def test_group_fraction_of_total_fuel_weight(self):
        frac = fswe.fuel_system_group_fraction(self.w_fs, TOTAL_FUEL_KG)
        self.assertAlmostEqual(frac, EXPECTED_FRACTION_FUEL, delta=1e-6)

    def test_group_fraction_of_mtow(self):
        frac = fswe.fuel_system_group_fraction(self.w_fs, MTOW_KG)
        self.assertAlmostEqual(frac, EXPECTED_FRACTION_MTOW, delta=1e-6)


class PhysicalSanityBandTests(unittest.TestCase):
    """Step 4 of the Workflow, the class-II physical-sanity band checks
    on the fuel system group mass and its fractions of the total fuel
    weight and MTOW."""

    def setUp(self):
        self.w_fs = fswe.fuel_system_group_weight(TOTAL_FUEL_KG, N_TANKS, N_ENGINES)

    def test_group_mass_positive(self):
        self.assertGreater(self.w_fs, 0.0)

    def test_group_below_total_fuel_weight(self):
        self.assertLess(self.w_fs, TOTAL_FUEL_KG)

    def test_group_below_mtow(self):
        self.assertLess(self.w_fs, MTOW_KG)

    def test_fuel_weight_fraction_in_band(self):
        frac = fswe.fuel_system_group_fraction(self.w_fs, TOTAL_FUEL_KG)
        self.assertGreaterEqual(frac, 0.010)
        self.assertLessEqual(frac, 0.025)

    def test_mtow_fraction_in_band(self):
        frac = fswe.fuel_system_group_fraction(self.w_fs, MTOW_KG)
        self.assertGreaterEqual(frac, 0.003)
        self.assertLessEqual(frac, 0.010)

    def test_mtow_fraction_far_below_empty_weight_band(self):
        frac = fswe.fuel_system_group_fraction(self.w_fs, MTOW_KG)
        self.assertLess(frac, 0.42)


class PowerLawIdentityTests(unittest.TestCase):
    """Step 5 of the Workflow, the exact-power identities: recomputing
    fuel_system_volume_term_kg at a doubled regressor scales the term by
    exactly 2 raised to that regressor's published exponent, and the
    fixed count allowance is exactly additive per extra tank or engine."""

    def setUp(self):
        self.w_v = fswe.fuel_system_volume_term_kg(TOTAL_FUEL_KG, N_TANKS)
        self.w_a = fswe.fuel_system_count_allowance_kg(N_TANKS, N_ENGINES)

    def test_fuel_weight_power_law(self):
        w_v2 = fswe.fuel_system_volume_term_kg(2 * TOTAL_FUEL_KG, N_TANKS)
        self.assertTrue(
            math.isclose(w_v2 / self.w_v, 2 ** (1.0 / 3.0), rel_tol=1e-9)
        )

    def test_tank_count_power_law(self):
        w_v2 = fswe.fuel_system_volume_term_kg(TOTAL_FUEL_KG, 2 * N_TANKS)
        self.assertTrue(math.isclose(w_v2 / self.w_v, 2 ** 0.5, rel_tol=1e-9))

    def test_count_allowance_additive_extra_tank(self):
        w_a2 = fswe.fuel_system_count_allowance_kg(N_TANKS + 1, N_ENGINES)
        self.assertAlmostEqual(w_a2 - self.w_a, 36.287389600, delta=1e-6)

    def test_count_allowance_additive_extra_engine(self):
        w_a2 = fswe.fuel_system_count_allowance_kg(N_TANKS, N_ENGINES + 1)
        self.assertAlmostEqual(w_a2 - self.w_a, 36.287389600, delta=1e-6)

    def test_count_allowance_fuel_independent(self):
        w_a_at_double_fuel = fswe.fuel_system_count_allowance_kg(N_TANKS, N_ENGINES)
        self.assertEqual(w_a_at_double_fuel, self.w_a)


class GroupAdditivityTests(unittest.TestCase):
    """Step 4 of the Workflow: the fuel_system_group_weight equals the
    count allowance plus the volume term, the two published terms of the
    source equation."""

    def test_group_equals_sum_of_terms(self):
        w_a = fswe.fuel_system_count_allowance_kg(N_TANKS, N_ENGINES)
        w_v = fswe.fuel_system_volume_term_kg(TOTAL_FUEL_KG, N_TANKS)
        w_fs = fswe.fuel_system_group_weight(TOTAL_FUEL_KG, N_TANKS, N_ENGINES)
        self.assertAlmostEqual(w_fs, w_a + w_v, delta=1e-12 * w_fs)


class SublinearScalingAndMonotonicityTests(unittest.TestCase):
    """Step 5 of the Workflow: the sublinear fraction fall as the total
    fuel weight doubles, and step 1-4 monotonicity of the group mass in
    the total fuel weight and the tank count."""

    def test_sublinear_scaling_and_fraction_fall(self):
        w_fs1 = fswe.fuel_system_group_weight(TOTAL_FUEL_KG, N_TANKS, N_ENGINES)
        w_fs2 = fswe.fuel_system_group_weight(2 * TOTAL_FUEL_KG, N_TANKS, N_ENGINES)
        ratio = w_fs2 / w_fs1
        self.assertAlmostEqual(ratio, 1.159273519641, delta=1e-9)
        self.assertLess(ratio, 2 ** (1.0 / 3.0))

        frac1 = fswe.fuel_system_group_fraction(w_fs1, TOTAL_FUEL_KG)
        frac2 = fswe.fuel_system_group_fraction(w_fs2, 2 * TOTAL_FUEL_KG)
        self.assertAlmostEqual(frac1, EXPECTED_FRACTION_FUEL, delta=1e-6)
        self.assertAlmostEqual(frac2, 0.009876141, delta=1e-6)
        self.assertLess(frac2, frac1)

    def test_monotonicity_one_percent_higher_fuel_weight(self):
        w_fs1 = fswe.fuel_system_group_weight(TOTAL_FUEL_KG, N_TANKS, N_ENGINES)
        w_fs2 = fswe.fuel_system_group_weight(1.01 * TOTAL_FUEL_KG, N_TANKS, N_ENGINES)
        self.assertAlmostEqual(w_fs2, 375.610128382, delta=1e-6)
        self.assertGreater(w_fs2, w_fs1)

    def test_monotonicity_one_more_tank(self):
        w_fs1 = fswe.fuel_system_group_weight(TOTAL_FUEL_KG, N_TANKS, N_ENGINES)
        w_fs2 = fswe.fuel_system_group_weight(TOTAL_FUEL_KG, N_TANKS + 1, N_ENGINES)
        self.assertAlmostEqual(w_fs2, 446.668717092, delta=1e-6)
        self.assertGreater(w_fs2, w_fs1)


class ValueErrorRejectionTests(unittest.TestCase):
    """Step 6 of the Workflow: ValueError rejection of every non-physical
    input across fuel_system_count_allowance_kg, fuel_system_volume_term_kg
    and fuel_system_group_weight, with the exact documented messages."""

    def test_zero_total_fuel_weight(self):
        with self.assertRaises(ValueError) as ctx:
            fswe.fuel_system_group_weight(0.0, N_TANKS, N_ENGINES)
        self.assertEqual(
            str(ctx.exception), "total fuel weight must be positive, got 0.0"
        )

    def test_negative_total_fuel_weight(self):
        with self.assertRaises(ValueError) as ctx:
            fswe.fuel_system_group_weight(-1.0, N_TANKS, N_ENGINES)
        self.assertEqual(
            str(ctx.exception), "total fuel weight must be positive, got -1.0"
        )

    def test_nonnumber_total_fuel_weight(self):
        with self.assertRaises(ValueError) as ctx:
            fswe.fuel_system_group_weight("a", N_TANKS, N_ENGINES)
        self.assertEqual(
            str(ctx.exception), "total fuel weight must be a number, got 'a'"
        )

    def test_tank_count_below_minimum(self):
        with self.assertRaises(ValueError) as ctx:
            fswe.fuel_system_group_weight(TOTAL_FUEL_KG, 0, N_ENGINES)
        self.assertEqual(
            str(ctx.exception),
            "number of separate fuel tanks must be at least 1, got 0",
        )

    def test_fractional_tank_count(self):
        with self.assertRaises(ValueError) as ctx:
            fswe.fuel_system_group_weight(TOTAL_FUEL_KG, 2.5, N_ENGINES)
        self.assertEqual(
            str(ctx.exception),
            "number of separate fuel tanks must be a whole number, got 2.5",
        )

    def test_engine_count_below_minimum(self):
        with self.assertRaises(ValueError) as ctx:
            fswe.fuel_system_count_allowance_kg(N_TANKS, 0)
        self.assertEqual(
            str(ctx.exception), "number of engines must be at least 1, got 0"
        )

    def test_tank_count_below_engine_count(self):
        with self.assertRaises(ValueError) as ctx:
            fswe.fuel_system_group_weight(TOTAL_FUEL_KG, 1, 2)
        self.assertEqual(
            str(ctx.exception),
            "number of separate fuel tanks must be at least the number of "
            "engines, got tanks 1 and engines 2",
        )

    def test_fractional_engine_count(self):
        with self.assertRaises(ValueError) as ctx:
            fswe.fuel_system_count_allowance_kg(N_TANKS, 1.5)
        self.assertEqual(
            str(ctx.exception), "number of engines must be a whole number, got 1.5"
        )

    def test_zero_fuel_weight_rejected_by_volume_term(self):
        with self.assertRaises(ValueError):
            fswe.fuel_system_volume_term_kg(0.0, N_TANKS)

    def test_negative_group_fraction_reference_rejected(self):
        with self.assertRaises(ValueError):
            fswe.fuel_system_group_fraction(10.0, -1.0)


class DeterminismTests(unittest.TestCase):
    """Step 6 of the Workflow: identical outputs run to run, confirming
    no randomness anywhere in the closed-form power-law arithmetic."""

    def test_repeated_calls_are_identical(self):
        run1 = fswe.fuel_system_group_weight(TOTAL_FUEL_KG, N_TANKS, N_ENGINES)
        run2 = fswe.fuel_system_group_weight(TOTAL_FUEL_KG, N_TANKS, N_ENGINES)
        self.assertEqual(run1, run2)

    def test_repeated_volume_term_calls_are_identical(self):
        run1 = fswe.fuel_system_volume_term_kg(TOTAL_FUEL_KG, N_TANKS)
        run2 = fswe.fuel_system_volume_term_kg(TOTAL_FUEL_KG, N_TANKS)
        self.assertEqual(run1, run2)


if __name__ == "__main__":
    unittest.main()
