"""Contract test for aircraft-electrical-load-analysis (wave-35).

Deterministic stdlib unittest, runs offline with:

    python3 scripts/test_aircraft_electrical_load_analysis.py

Asserts the worked-example module outputs (continuous load 45.75 kVA,
coincident peak 38.8875 kVA, essential load 21.5 kVA, generator-out
margin 0.6417 with verdict PASS, load fraction 0.38125), the identities
(diversity 1.0 keeps the coincident peak equal to the continuous load;
essential load exactly at the (n-1) generator capacity gives margin 0),
boundary cases, and ValueError rejection of non-physical inputs.
"""

import unittest

from aircraft_electrical_load_analysis_logic import (
    continuous_load,
    diversity_peak,
    ela_summary,
    essential_load,
    generator_out_margin,
    load_fraction,
)

# Worked example reference system from the wave-35 spec.
WORKED_CONSUMERS = {
    "avionics": (4.0, 1.0),
    "flight-control": (12.0, 0.6),
    "comm-nav": (2.5, 1.0),
    "lighting": (6.0, 0.5),
    "galley": (35.0, 0.35),
    "anti-ice": (18.0, 0.25),
    "hydraulic-pumps": (12.0, 0.8),
    "fuel-boost": (3.0, 0.9),
}
ESSENTIAL_NAMES = ["avionics", "flight-control", "comm-nav", "fuel-boost"]
ALL_NAMES = list(WORKED_CONSUMERS.keys())
TOL = 1e-9


class TestContinuousLoad(unittest.TestCase):
    def test_worked_example_continuous_load(self):
        # 4 + 7.2 + 2.5 + 3 + 12.25 + 4.5 + 9.6 + 2.7 = 45.75 kVA.
        result = continuous_load(WORKED_CONSUMERS)
        self.assertAlmostEqual(result["continuous_kva"], 45.75, delta=TOL)

    def test_worked_example_rollup_values(self):
        result = continuous_load(WORKED_CONSUMERS)
        expected = [4.0, 7.2, 2.5, 3.0, 12.25, 4.5, 9.6, 2.7]
        self.assertEqual(len(result["rollup"]), len(expected))
        for got, want in zip(result["rollup"], expected):
            self.assertAlmostEqual(got, want, delta=TOL)

    def test_rollup_order_preserved(self):
        result = continuous_load(WORKED_CONSUMERS)
        self.assertEqual(
            result["rollup"],
            [p * d for p, d in WORKED_CONSUMERS.values()],
        )

    def test_single_consumer_duty_one(self):
        result = continuous_load({"avionics": (10.0, 1.0)})
        self.assertAlmostEqual(result["continuous_kva"], 10.0, delta=TOL)
        self.assertAlmostEqual(result["rollup"][0], 10.0, delta=TOL)

    def test_single_consumer_duty_half(self):
        result = continuous_load({"avionics": (10.0, 0.5)})
        self.assertAlmostEqual(result["continuous_kva"], 5.0, delta=TOL)

    def test_doubling_power_doubles_contribution(self):
        base = continuous_load({"avionics": (10.0, 0.5)})
        doubled = continuous_load({"avionics": (20.0, 0.5)})
        self.assertAlmostEqual(
            doubled["continuous_kva"], 2.0 * base["continuous_kva"], delta=TOL
        )

    def test_valueerror_empty_consumers(self):
        with self.assertRaises(ValueError):
            continuous_load({})

    def test_valueerror_duty_out_of_range(self):
        # Duty 1.2 (above one) and duty -0.1 (below zero) both rejected.
        with self.assertRaises(ValueError):
            continuous_load({"avionics": (10.0, 1.2)})
        with self.assertRaises(ValueError):
            continuous_load({"avionics": (10.0, -0.1)})

    def test_valueerror_negative_power(self):
        with self.assertRaises(ValueError):
            continuous_load({"avionics": (-5.0, 0.5)})


class TestDiversityPeak(unittest.TestCase):
    def test_worked_example_coincident_peak(self):
        # 0.85 * 45.75 = 38.8875 kVA.
        self.assertAlmostEqual(diversity_peak(45.75, 0.85), 38.8875, delta=TOL)

    def test_diversity_one_identity(self):
        # With diversity 1.0 the coincident peak equals the continuous load.
        self.assertEqual(diversity_peak(45.75, 1.0), 45.75)

    def test_diversity_half_halves(self):
        self.assertAlmostEqual(diversity_peak(45.75, 0.5), 22.875, delta=TOL)

    def test_valueerror_diversity_zero(self):
        with self.assertRaises(ValueError):
            diversity_peak(45.75, 0.0)

    def test_valueerror_diversity_above_one(self):
        with self.assertRaises(ValueError):
            diversity_peak(45.75, 1.5)

    def test_valueerror_negative_continuous(self):
        with self.assertRaises(ValueError):
            diversity_peak(-1.0, 0.85)


class TestEssentialLoad(unittest.TestCase):
    def test_worked_example_essential_load(self):
        # 4 + 12 + 2.5 + 3 = 21.5 kVA at full rated power.
        result = essential_load(WORKED_CONSUMERS, ESSENTIAL_NAMES)
        self.assertAlmostEqual(result["essential_kva"], 21.5, delta=TOL)
        self.assertEqual(result["essential_consumers"], ESSENTIAL_NAMES)

    def test_essential_all_consumers_full_sum(self):
        # All consumers essential: 92.5 kVA (full powers only).
        result = essential_load(WORKED_CONSUMERS, ALL_NAMES)
        self.assertAlmostEqual(result["essential_kva"], 92.5, delta=TOL)

    def test_essential_single_at_full_power_not_duty(self):
        # flight-control draws 12 kVA at duty 0.6; essential books full 12.
        result = essential_load(WORKED_CONSUMERS, ["flight-control"])
        self.assertAlmostEqual(result["essential_kva"], 12.0, delta=TOL)

    def test_essential_no_names(self):
        result = essential_load(WORKED_CONSUMERS, [])
        self.assertAlmostEqual(result["essential_kva"], 0.0, delta=TOL)
        self.assertEqual(result["essential_consumers"], [])

    def test_valueerror_essential_name_missing(self):
        with self.assertRaises(ValueError):
            essential_load(WORKED_CONSUMERS, ["avionics", "apu-starter"])

    def test_valueerror_essential_empty_consumers(self):
        with self.assertRaises(ValueError):
            essential_load({}, ["avionics"])


class TestGeneratorOutMargin(unittest.TestCase):
    def test_worked_example_margin(self):
        # Two 60 kVA generators: remaining 60 kVA; (60 - 21.5) / 60.
        result = generator_out_margin(2, 60.0, 21.5)
        self.assertAlmostEqual(result["remaining_kva"], 60.0, delta=TOL)
        self.assertAlmostEqual(result["margin"], 0.6416666666666667, delta=TOL)
        self.assertEqual(result["verdict"], "PASS")

    def test_margin_zero_identity(self):
        # Essential exactly at the (n-1) generator capacity: margin 0 PASS.
        result = generator_out_margin(2, 60.0, 60.0)
        self.assertAlmostEqual(result["margin"], 0.0, delta=TOL)
        self.assertEqual(result["verdict"], "PASS")

    def test_margin_fail_negative(self):
        # Essential 80 kVA with two 60 kVA generators: (60 - 80) / 60.
        result = generator_out_margin(2, 60.0, 80.0)
        self.assertAlmostEqual(result["margin"], -1.0 / 3.0, delta=TOL)
        self.assertEqual(result["verdict"], "FAIL")

    def test_single_generator_no_redundancy(self):
        result = generator_out_margin(1, 60.0, 21.5)
        self.assertAlmostEqual(result["remaining_kva"], 0.0, delta=TOL)
        self.assertAlmostEqual(result["margin"], -1.0, delta=TOL)
        self.assertEqual(result["verdict"], "FAIL")

    def test_valueerror_zero_generators(self):
        with self.assertRaises(ValueError):
            generator_out_margin(0, 60.0, 21.5)

    def test_valueerror_zero_generator_kva(self):
        with self.assertRaises(ValueError):
            generator_out_margin(2, 0.0, 21.5)

    def test_valueerror_negative_essential(self):
        with self.assertRaises(ValueError):
            generator_out_margin(2, 60.0, -1.0)


class TestLoadFraction(unittest.TestCase):
    def test_worked_example_load_fraction(self):
        # 45.75 / 120 = 0.38125 (38.1%).
        self.assertAlmostEqual(load_fraction(45.75, 120.0), 0.38125, delta=TOL)

    def test_doubling_installed_halves_fraction(self):
        fraction = load_fraction(45.75, 120.0)
        self.assertAlmostEqual(load_fraction(45.75, 240.0), fraction / 2.0,
                               delta=TOL)

    def test_valueerror_installed_kva_non_positive(self):
        with self.assertRaises(ValueError):
            load_fraction(45.75, 0.0)
        with self.assertRaises(ValueError):
            load_fraction(45.75, -120.0)


class TestSummaryAndDeterminism(unittest.TestCase):
    SUMMARY_KEYS = {
        "continuous_kva", "rollup", "coincident_peak_kva", "essential_kva",
        "essential_consumers", "remaining_kva", "margin", "verdict",
        "load_fraction", "installed_kva",
    }

    def test_summary_worked_example(self):
        result = ela_summary(WORKED_CONSUMERS, 0.85, ESSENTIAL_NAMES, 2, 60.0)
        self.assertAlmostEqual(result["continuous_kva"], 45.75, delta=TOL)
        self.assertAlmostEqual(result["coincident_peak_kva"], 38.8875, delta=TOL)
        self.assertAlmostEqual(result["essential_kva"], 21.5, delta=TOL)
        self.assertAlmostEqual(result["remaining_kva"], 60.0, delta=TOL)
        self.assertAlmostEqual(result["margin"], 0.6416666666666667, delta=TOL)
        self.assertEqual(result["verdict"], "PASS")
        self.assertAlmostEqual(result["load_fraction"], 0.38125, delta=TOL)
        self.assertAlmostEqual(result["installed_kva"], 120.0, delta=TOL)
        self.assertEqual(len(result["rollup"]), 8)
        self.assertEqual(result["essential_consumers"], ESSENTIAL_NAMES)

    def test_summary_key_set_exact(self):
        result = ela_summary(WORKED_CONSUMERS, 0.85, ESSENTIAL_NAMES, 2, 60.0)
        self.assertEqual(set(result.keys()), self.SUMMARY_KEYS)

    def test_summary_single_generator_fail(self):
        result = ela_summary(WORKED_CONSUMERS, 0.85, ESSENTIAL_NAMES, 1, 60.0)
        self.assertAlmostEqual(result["remaining_kva"], 0.0, delta=TOL)
        self.assertAlmostEqual(result["margin"], -1.0, delta=TOL)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertAlmostEqual(result["installed_kva"], 60.0, delta=TOL)

    def test_determinism_identical_inputs_identical_outputs(self):
        first = ela_summary(WORKED_CONSUMERS, 0.85, ESSENTIAL_NAMES, 2, 60.0)
        second = ela_summary(WORKED_CONSUMERS, 0.85, ESSENTIAL_NAMES, 2, 60.0)
        self.assertEqual(first, second)
        self.assertEqual(
            continuous_load(WORKED_CONSUMERS),
            continuous_load(WORKED_CONSUMERS),
        )


if __name__ == "__main__":
    unittest.main()
