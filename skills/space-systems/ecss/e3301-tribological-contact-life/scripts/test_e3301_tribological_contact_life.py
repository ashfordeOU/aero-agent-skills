"""Contract tests for the clause 4.7.3.4.1 contact-pair life logic."""

import unittest

from e3301_tribological_contact_life_logic import (
    DEFAULT_LIFE_FACTOR,
    archard_wear_volume_mm3,
    assess_contact_life,
    demonstrated_life_ratio,
    limiting_wear_depth_mm,
    required_test_cycles,
    sliding_distance_m,
    transfer_limited_cycles,
    wear_depth_mm,
    worst_case_wear_coefficient,
)


def base_spec(**overrides):
    """Return a representative dry-lubricated hinge contact pair."""
    spec = {
        "stroke_mm": 20.0,
        "passes_per_cycle": 2.0,
        "mission_cycles": 50000,
        "contact_load_n": 40.0,
        "nominal_wear_coefficient": 1.0e-6,
        "hardness_mpa": 2000.0,
        "contact_area_mm2": 4.0,
        "allowable_wear_depth_mm": 0.05,
        "life_factor": 2.0,
    }
    spec.update(overrides)
    return spec


class SlidingDistanceTests(unittest.TestCase):
    def test_reciprocating_pair_counts_both_passes(self):
        self.assertAlmostEqual(sliding_distance_m(20.0, 2.0, 1000), 40.0, places=9)

    def test_ground_test_cycles_spend_the_same_life(self):
        flight = sliding_distance_m(20.0, 2.0, 1000)
        with_ground = sliding_distance_m(20.0, 2.0, 1000, ground_test_cycles=500)
        self.assertAlmostEqual(with_ground, flight * 1.5, places=9)

    def test_zero_stroke_rejected(self):
        with self.assertRaises(ValueError):
            sliding_distance_m(0.0, 2.0, 1000)

    def test_non_integer_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            sliding_distance_m(20.0, 2.0, 1000.5)

    def test_negative_ground_cycles_rejected(self):
        with self.assertRaises(ValueError):
            sliding_distance_m(20.0, 2.0, 1000, ground_test_cycles=-1)


class WorstCaseCoefficientTests(unittest.TestCase):
    def test_factors_multiply_onto_the_nominal_value(self):
        k = worst_case_wear_coefficient(
            1.0e-6, {"vacuum": 3.0, "temperature": 2.0}
        )
        self.assertAlmostEqual(k, 6.0e-6, places=15)

    def test_absent_factor_set_leaves_the_nominal_value(self):
        self.assertAlmostEqual(worst_case_wear_coefficient(2.5e-7), 2.5e-7, places=15)

    def test_relieving_factor_refused(self):
        with self.assertRaises(ValueError):
            worst_case_wear_coefficient(1.0e-6, {"vacuum": 0.5})

    def test_unknown_condition_name_refused(self):
        with self.assertRaises(ValueError):
            worst_case_wear_coefficient(1.0e-6, {"humidity": 2.0})

    def test_unity_factor_is_accepted_as_no_derating(self):
        self.assertAlmostEqual(
            worst_case_wear_coefficient(1.0e-6, {"dwell": 1.0}), 1.0e-6, places=15
        )


class ArchardTests(unittest.TestCase):
    def test_volume_follows_load_and_distance(self):
        volume = archard_wear_volume_mm3(1.0e-6, 40.0, 100.0, 2000.0)
        self.assertAlmostEqual(volume, 1.0e-6 * 40.0 * 100000.0 / 2000.0, places=12)

    def test_zero_distance_gives_zero_volume(self):
        self.assertAlmostEqual(archard_wear_volume_mm3(1.0e-6, 40.0, 0.0, 2000.0), 0.0, places=15)

    def test_harder_counterface_wears_less(self):
        soft = archard_wear_volume_mm3(1.0e-6, 40.0, 100.0, 1000.0)
        hard = archard_wear_volume_mm3(1.0e-6, 40.0, 100.0, 4000.0)
        self.assertAlmostEqual(soft, hard * 4.0, places=12)

    def test_zero_hardness_rejected(self):
        with self.assertRaises(ValueError):
            archard_wear_volume_mm3(1.0e-6, 40.0, 100.0, 0.0)

    def test_depth_spreads_volume_over_the_apparent_area(self):
        self.assertAlmostEqual(wear_depth_mm(0.2, 4.0), 0.05, places=12)

    def test_zero_contact_area_rejected(self):
        with self.assertRaises(ValueError):
            wear_depth_mm(0.2, 0.0)


class LimitingDepthTests(unittest.TestCase):
    def test_coating_thinner_than_allowance_governs(self):
        limit, name = limiting_wear_depth_mm(0.05, coating_thickness_mm=0.012)
        self.assertAlmostEqual(limit, 0.012, places=12)
        self.assertEqual(name, "dry-film-coating-thickness")

    def test_allowance_governs_a_thick_coating(self):
        limit, name = limiting_wear_depth_mm(0.05, coating_thickness_mm=0.5)
        self.assertAlmostEqual(limit, 0.05, places=12)
        self.assertEqual(name, "allowable-wear-depth")

    def test_uncoated_pair_uses_the_allowance(self):
        limit, name = limiting_wear_depth_mm(0.08)
        self.assertAlmostEqual(limit, 0.08, places=12)
        self.assertEqual(name, "allowable-wear-depth")

    def test_negative_allowance_rejected(self):
        with self.assertRaises(ValueError):
            limiting_wear_depth_mm(-0.01)


class TransferFilmTests(unittest.TestCase):
    def test_reservoir_converts_to_cycles(self):
        cycles = transfer_limited_cycles(2.0, 1.0e-4, 0.04)
        self.assertAlmostEqual(cycles, 500000.0, places=6)

    def test_faster_transfer_rate_shortens_life(self):
        slow = transfer_limited_cycles(2.0, 1.0e-4, 0.04)
        fast = transfer_limited_cycles(2.0, 2.0e-4, 0.04)
        self.assertAlmostEqual(slow, fast * 2.0, places=6)

    def test_zero_reservoir_rejected(self):
        with self.assertRaises(ValueError):
            transfer_limited_cycles(0.0, 1.0e-4, 0.04)


class LifeFactorTests(unittest.TestCase):
    def test_default_factor_doubles_the_mission_cycles(self):
        self.assertEqual(required_test_cycles(1000), int(1000 * DEFAULT_LIFE_FACTOR))

    def test_fractional_requirement_rounds_up(self):
        self.assertEqual(required_test_cycles(1000, 1.5), 1500)
        self.assertEqual(required_test_cycles(999, 1.5), 1499)

    def test_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            required_test_cycles(1000, 0.9)

    def test_ratio_of_one_when_exactly_demonstrated(self):
        self.assertAlmostEqual(demonstrated_life_ratio(2000, 1000, 2.0), 1.0, places=9)

    def test_negative_test_cycles_rejected(self):
        with self.assertRaises(ValueError):
            demonstrated_life_ratio(-1, 1000, 2.0)


class AssessContactLifeTests(unittest.TestCase):
    def test_lightly_loaded_pair_is_compliant(self):
        result = assess_contact_life(base_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["life_limiter"], "none")
        self.assertEqual(result["findings"], [])

    def test_worst_case_derating_can_turn_a_nominal_pass_into_a_finding(self):
        nominal = assess_contact_life(base_spec())
        derated = assess_contact_life(
            base_spec(environment_factors={"vacuum": 8.0, "contamination": 4.0})
        )
        self.assertTrue(nominal["compliant"])
        self.assertFalse(derated["compliant"])
        self.assertAlmostEqual(
            derated["wear_depth_mm"], nominal["wear_depth_mm"] * 32.0, places=12
        )

    def test_thin_coating_becomes_the_governing_limit(self):
        result = assess_contact_life(base_spec(coating_thickness_mm=0.001))
        self.assertEqual(result["governing_depth_limit"], "dry-film-coating-thickness")
        self.assertFalse(result["compliant"])

    def test_transfer_starvation_is_reported_as_the_life_limiter(self):
        result = assess_contact_life(
            base_spec(reservoir_volume_mm3=0.5, transfer_rate_mm3_per_m=1.0e-3)
        )
        self.assertEqual(result["life_limiter"], "transfer-film-starvation")
        self.assertFalse(result["compliant"])

    def test_half_run_demonstration_is_a_finding(self):
        result = assess_contact_life(base_spec(test_cycles=50000))
        self.assertEqual(result["required_test_cycles"], 100000)
        self.assertAlmostEqual(result["demonstrated_life_ratio"], 0.5, places=12)
        self.assertFalse(result["compliant"])

    def test_fully_run_demonstration_raises_no_finding(self):
        result = assess_contact_life(base_spec(test_cycles=100000))
        self.assertAlmostEqual(result["demonstrated_life_ratio"], 1.0, places=12)
        self.assertTrue(result["compliant"])

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["hardness_mpa"]
        with self.assertRaises(ValueError):
            assess_contact_life(spec)

    def test_half_declared_transfer_check_rejected(self):
        with self.assertRaises(ValueError):
            assess_contact_life(base_spec(reservoir_volume_mm3=0.5))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_contact_life([("stroke_mm", 20.0)])


if __name__ == "__main__":
    unittest.main()
