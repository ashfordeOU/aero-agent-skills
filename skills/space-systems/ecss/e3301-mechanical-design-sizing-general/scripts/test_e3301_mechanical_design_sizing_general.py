"""Contract tests for the clause 4.7.5.1 general part-sizing logic."""

import math
import unittest

from e3301_mechanical_design_sizing_general_logic import (
    KNOCKDOWN_KEYS,
    allowable_cycles,
    assess_part_sizing,
    axial_stress_pa,
    bending_stress_pa,
    first_mode_margin,
    knocked_down_allowable_pa,
    margin_of_safety,
    miner_damage,
    shear_stress_pa,
    von_mises_stress_pa,
)

SPECTRUM = [
    {"stress_pa": 4.0e7, "cycles": 1000.0},
    {"stress_pa": 2.0e7, "cycles": 50000.0},
]


def base_spec(**overrides):
    """Return a representative machined mechanism bracket."""
    spec = {
        "area_m2": 1.5e-4,
        "section_modulus_m3": 5.0e-7,
        "shear_area_m2": 1.0e-4,
        "load_cases": [
            {
                "name": "launch-quasi-static",
                "axial_load_n": 3000.0,
                "bending_moment_nm": 12.0,
                "shear_load_n": 800.0,
            },
            {
                "name": "operational-thermal",
                "axial_load_n": 500.0,
                "bending_moment_nm": 3.0,
                "shear_load_n": 100.0,
            },
        ],
        "yield_allowable_pa": 2.7e8,
        "ultimate_allowable_pa": 3.1e8,
        "yield_factor": 1.25,
        "ultimate_factor": 2.0,
        "knockdowns": {"temperature": 0.9, "ageing": 0.95},
        "spectrum": SPECTRUM,
        "reference_stress_pa": 1.0e8,
        "reference_cycles": 1.0e4,
        "sn_exponent": 5.0,
        "damage_limit": 0.5,
        "first_mode_hz": 180.0,
        "required_first_mode_hz": 140.0,
    }
    spec.update(overrides)
    return spec


class StressTests(unittest.TestCase):
    def test_axial_stress_is_load_over_area(self):
        self.assertAlmostEqual(axial_stress_pa(3000.0, 1.5e-4), 2.0e7, places=3)

    def test_compression_comes_back_negative(self):
        self.assertAlmostEqual(axial_stress_pa(-3000.0, 1.5e-4), -2.0e7, places=3)

    def test_bending_stress_is_moment_over_modulus(self):
        self.assertAlmostEqual(bending_stress_pa(12.0, 5.0e-7), 2.4e7, places=3)

    def test_shear_stress_is_load_over_shear_area(self):
        self.assertAlmostEqual(shear_stress_pa(800.0, 1.0e-4), 8.0e6, places=3)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            axial_stress_pa(3000.0, 0.0)

    def test_non_numeric_moment_rejected(self):
        with self.assertRaises(ValueError):
            bending_stress_pa("12", 5.0e-7)

    def test_von_mises_reduces_to_the_normal_stress_without_shear(self):
        self.assertAlmostEqual(von_mises_stress_pa(4.4e7), 4.4e7, places=3)

    def test_von_mises_weights_shear_by_three(self):
        self.assertAlmostEqual(
            von_mises_stress_pa(4.4e7, 8.0e6),
            math.sqrt(4.4e7 ** 2 + 3.0 * 8.0e6 ** 2),
            places=3,
        )

    def test_pure_shear_reaches_root_three_times_the_shear(self):
        self.assertAlmostEqual(
            von_mises_stress_pa(0.0, 1.0e7), math.sqrt(3.0) * 1.0e7, places=3
        )


class KnockdownTests(unittest.TestCase):
    def test_factors_multiply_onto_the_allowable(self):
        self.assertAlmostEqual(
            knocked_down_allowable_pa(2.7e8, {"temperature": 0.9, "ageing": 0.95}),
            2.7e8 * 0.855, places=3,
        )

    def test_absent_knockdowns_leave_the_allowable(self):
        self.assertAlmostEqual(knocked_down_allowable_pa(2.7e8), 2.7e8, places=3)

    def test_factor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            knocked_down_allowable_pa(2.7e8, {"temperature": 1.1})

    def test_unknown_environment_rejected(self):
        with self.assertRaises(ValueError):
            knocked_down_allowable_pa(2.7e8, {"vibration": 0.9})

    def test_every_documented_environment_is_accepted(self):
        factors = dict((name, 0.95) for name in KNOCKDOWN_KEYS)
        value = knocked_down_allowable_pa(1.0e8, factors)
        self.assertAlmostEqual(value, 1.0e8 * 0.95 ** len(KNOCKDOWN_KEYS), places=3)


class MarginTests(unittest.TestCase):
    def test_margin_definition(self):
        self.assertAlmostEqual(margin_of_safety(2.0e8, 5.0e7, 2.0), 1.0, places=12)

    def test_zero_margin_at_the_exact_allowable(self):
        self.assertAlmostEqual(margin_of_safety(1.0e8, 5.0e7, 2.0), 0.0, places=12)

    def test_safety_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            margin_of_safety(2.0e8, 5.0e7, 0.9)

    def test_first_mode_margin_definition(self):
        self.assertAlmostEqual(first_mode_margin(180.0, 140.0), 180.0 / 140.0 - 1.0, places=12)

    def test_first_mode_exactly_at_the_requirement_is_zero(self):
        self.assertAlmostEqual(first_mode_margin(140.0, 140.0), 0.0, places=12)


class FatigueTests(unittest.TestCase):
    def test_allowable_cycles_at_the_reference_stress(self):
        self.assertAlmostEqual(allowable_cycles(1.0e8, 1.0e8, 1.0e4, 5.0), 1.0e4, places=6)

    def test_halving_the_stress_multiplies_life_by_the_slope(self):
        self.assertAlmostEqual(
            allowable_cycles(5.0e7, 1.0e8, 1.0e4, 5.0), 1.0e4 * 32.0, places=3
        )

    def test_zero_stress_rejected(self):
        with self.assertRaises(ValueError):
            allowable_cycles(0.0, 1.0e8, 1.0e4, 5.0)

    def test_damage_sums_over_the_blocks(self):
        damage = miner_damage(SPECTRUM, 1.0e8, 1.0e4, 5.0)
        expected = (
            1000.0 / allowable_cycles(4.0e7, 1.0e8, 1.0e4, 5.0)
            + 50000.0 / allowable_cycles(2.0e7, 1.0e8, 1.0e4, 5.0)
        )
        self.assertAlmostEqual(damage, expected, places=12)

    def test_damage_reaches_unity_at_the_allowable_life(self):
        allowed = allowable_cycles(4.0e7, 1.0e8, 1.0e4, 5.0)
        damage = miner_damage(
            [{"stress_pa": 4.0e7, "cycles": allowed}], 1.0e8, 1.0e4, 5.0
        )
        self.assertAlmostEqual(damage, 1.0, places=12)

    def test_empty_spectrum_rejected(self):
        with self.assertRaises(ValueError):
            miner_damage([], 1.0e8, 1.0e4, 5.0)

    def test_malformed_block_rejected(self):
        with self.assertRaises(ValueError):
            miner_damage([{"stress_pa": 4.0e7}], 1.0e8, 1.0e4, 5.0)


class AssessPartSizingTests(unittest.TestCase):
    def test_representative_bracket_is_compliant(self):
        result = assess_part_sizing(base_spec())
        self.assertTrue(result["compliant"], result["findings"])
        self.assertEqual(result["governing_case"], "launch-quasi-static")

    def test_knockdowns_reach_both_allowables(self):
        result = assess_part_sizing(base_spec())
        self.assertAlmostEqual(result["yield_allowable_pa"], 2.7e8 * 0.855, places=3)
        self.assertAlmostEqual(result["ultimate_allowable_pa"], 3.1e8 * 0.855, places=3)

    def test_thin_section_fails_both_static_checks(self):
        result = assess_part_sizing(
            base_spec(area_m2=1.5e-5, section_modulus_m3=5.0e-8, shear_area_m2=1.0e-5)
        )
        self.assertFalse(result["compliant"])
        self.assertLess(result["worst_margin_of_safety"], 0.0)
        self.assertTrue(any("yield margin" in f for f in result["findings"]))

    def test_severe_temperature_knockdown_turns_a_pass_into_a_finding(self):
        result = assess_part_sizing(base_spec(knockdowns={"temperature": 0.15}))
        self.assertFalse(result["compliant"])

    def test_long_spectrum_breaks_the_damage_limit(self):
        result = assess_part_sizing(
            base_spec(spectrum=[{"stress_pa": 4.0e7, "cycles": 1.0e6}])
        )
        self.assertFalse(result["compliant"])
        self.assertGreater(result["cumulative_damage"], 0.5)

    def test_soft_part_fails_the_stiffness_requirement(self):
        result = assess_part_sizing(base_spec(first_mode_hz=100.0))
        self.assertFalse(result["compliant"])
        self.assertLess(result["first_mode_margin"], 0.0)

    def test_governing_check_is_named(self):
        result = assess_part_sizing(base_spec())
        self.assertIn(result["governing_check"], ("yield", "ultimate"))

    def test_ultimate_below_yield_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_sizing(base_spec(ultimate_allowable_pa=2.0e8))

    def test_half_declared_stiffness_check_rejected(self):
        spec = base_spec()
        del spec["required_first_mode_hz"]
        with self.assertRaises(ValueError):
            assess_part_sizing(spec)

    def test_spectrum_without_an_sn_line_rejected(self):
        spec = base_spec()
        del spec["sn_exponent"]
        with self.assertRaises(ValueError):
            assess_part_sizing(spec)

    def test_empty_load_case_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_sizing(base_spec(load_cases=[]))

    def test_unloaded_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_sizing(
                base_spec(
                    load_cases=[
                        {
                            "name": "no-load",
                            "axial_load_n": 0.0,
                            "bending_moment_nm": 0.0,
                            "shear_load_n": 0.0,
                        }
                    ]
                )
            )

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["shear_area_m2"]
        with self.assertRaises(ValueError):
            assess_part_sizing(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_sizing(["area_m2", 1.5e-4])


if __name__ == "__main__":
    unittest.main()
