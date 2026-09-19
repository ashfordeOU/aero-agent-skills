"""Contract tests for the clause 4.7.3.1 lubricant selection logic."""

import math
import unittest

from e3301_tribology_general_lubricant_selection_logic import (
    DEFAULT_LIFE_FACTOR,
    MARGIN_TOLERANCE,
    assess_lubricant_selection,
    at_least,
    dn_value,
    duty_from_interface,
    hertz_point_contact_pressure_mpa,
    rank_candidates,
    required_life_cycles,
    screen_candidate,
    sliding_speed_m_s,
    temperature_gap,
    validate_non_negative,
    validate_positive,
)

INTERFACE = {
    "load_n": 4.0,
    "contact_radius_mm": 3.175,
    "effective_modulus_mpa": 115000.0,
    "radius_mm": 20.0,
    "speed_rpm": 60.0,
    "duty_cycles": 100000.0,
    "temperature_c": (-40.0, 80.0),
    "bore_mm": 15.0,
}

CANDIDATES = [
    {
        "name": "pfpe-grease-qualified",
        "qualified": True,
        "max_contact_pressure_mpa": 1500.0,
        "max_sliding_speed_m_s": 2.0,
        "qualified_cycles": 5.0e6,
        "temperature_c": (-60.0, 120.0),
    },
    {
        "name": "mos2-dry-film",
        "qualified": True,
        "max_contact_pressure_mpa": 2200.0,
        "max_sliding_speed_m_s": 0.2,
        "qualified_cycles": 5.0e5,
        "temperature_c": (-150.0, 300.0),
    },
    {
        "name": "mineral-oil-unqualified",
        "qualified": False,
        "max_contact_pressure_mpa": 1200.0,
        "max_sliding_speed_m_s": 5.0,
        "qualified_cycles": 1.0e6,
        "temperature_c": (-20.0, 100.0),
    },
    {
        "name": "ptfe-composite",
        "qualified": True,
        "max_contact_pressure_mpa": 300.0,
        "max_sliding_speed_m_s": 0.5,
        "qualified_cycles": 1.0e6,
        "temperature_c": (-100.0, 200.0),
    },
]


def independent_peak_pressure_mpa(load_n, radius_mm, modulus_mpa):
    """Closed form arranged differently from the implementation under test."""
    radius_m = radius_mm / 1000.0
    modulus_pa = modulus_mpa * 1.0e6
    pressure_pa = (
        6.0 * load_n * modulus_pa * modulus_pa / (math.pi ** 3 * radius_m * radius_m)
    ) ** (1.0 / 3.0)
    return pressure_pa / 1.0e6


class ValidationTests(unittest.TestCase):
    def test_positive_validator_returns_float(self):
        self.assertAlmostEqual(validate_positive("x", 5), 5.0)

    def test_positive_validator_rejects_zero(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0)

    def test_non_negative_validator_accepts_zero(self):
        self.assertAlmostEqual(validate_non_negative("x", 0.0), 0.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_non_negative("x", True)

    def test_at_least_accepts_exact_equality(self):
        self.assertTrue(at_least(1500.0, 1500.0))

    def test_at_least_rejects_a_real_shortfall(self):
        self.assertFalse(at_least(1499.0, 1500.0))


class DutyQuantityTests(unittest.TestCase):
    def test_sliding_speed_matches_the_closed_form(self):
        self.assertAlmostEqual(sliding_speed_m_s(20.0, 60.0), 2.0 * math.pi * 0.02, places=12)

    def test_zero_speed_is_allowed(self):
        self.assertAlmostEqual(sliding_speed_m_s(20.0, 0.0), 0.0)

    def test_zero_radius_rejected(self):
        with self.assertRaises(ValueError):
            sliding_speed_m_s(0.0, 60.0)

    def test_dn_value_is_bore_times_speed(self):
        self.assertAlmostEqual(dn_value(15.0, 6000.0), 90000.0)

    def test_negative_speed_rejected_by_dn(self):
        with self.assertRaises(ValueError):
            dn_value(15.0, -1.0)

    def test_peak_pressure_matches_an_independent_closed_form(self):
        computed = hertz_point_contact_pressure_mpa(4.0, 3.175, 115000.0)
        expected = independent_peak_pressure_mpa(4.0, 3.175, 115000.0)
        self.assertAlmostEqual(computed, expected, delta=abs(expected) * 1e-9)

    def test_peak_pressure_scales_with_the_cube_root_of_load(self):
        single = hertz_point_contact_pressure_mpa(4.0, 3.175, 115000.0)
        double = hertz_point_contact_pressure_mpa(8.0, 3.175, 115000.0)
        self.assertAlmostEqual(double / single, 2.0 ** (1.0 / 3.0), places=9)

    def test_larger_ball_lowers_the_peak_pressure(self):
        small = hertz_point_contact_pressure_mpa(4.0, 3.175, 115000.0)
        large = hertz_point_contact_pressure_mpa(4.0, 6.35, 115000.0)
        self.assertLess(large, small)

    def test_zero_load_rejected_by_hertz(self):
        with self.assertRaises(ValueError):
            hertz_point_contact_pressure_mpa(0.0, 3.175, 115000.0)

    def test_life_factor_multiplies_the_duty_cycles(self):
        self.assertAlmostEqual(required_life_cycles(100000.0), 100000.0 * DEFAULT_LIFE_FACTOR)

    def test_life_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            required_life_cycles(100000.0, 0.5)


class DutyReductionTests(unittest.TestCase):
    def test_duty_carries_all_four_selection_quantities(self):
        duty = duty_from_interface(INTERFACE)
        for key in (
            "contact_pressure_mpa",
            "sliding_speed_m_s",
            "required_cycles",
            "temperature_c",
        ):
            self.assertIn(key, duty)

    def test_duty_includes_the_dn_value_when_a_bore_is_given(self):
        self.assertAlmostEqual(duty_from_interface(INTERFACE)["dn_value"], 900.0)

    def test_duty_omits_the_dn_value_without_a_bore(self):
        spec = dict(INTERFACE)
        del spec["bore_mm"]
        self.assertNotIn("dn_value", duty_from_interface(spec))

    def test_inverted_duty_temperature_rejected(self):
        spec = dict(INTERFACE)
        spec["temperature_c"] = (80.0, -40.0)
        with self.assertRaises(ValueError):
            duty_from_interface(spec)

    def test_scalar_duty_temperature_rejected(self):
        spec = dict(INTERFACE)
        spec["temperature_c"] = 20.0
        with self.assertRaises(ValueError):
            duty_from_interface(spec)

    def test_missing_interface_key_rejected(self):
        spec = dict(INTERFACE)
        del spec["load_n"]
        with self.assertRaises(ValueError):
            duty_from_interface(spec)


class TemperatureGapTests(unittest.TestCase):
    def test_covered_range_has_no_gap(self):
        self.assertEqual(temperature_gap((-40.0, 80.0), (-60.0, 120.0)), (0.0, 0.0))

    def test_cold_shortfall_is_reported(self):
        cold, hot = temperature_gap((-40.0, 80.0), (-20.0, 120.0))
        self.assertAlmostEqual(cold, 20.0)
        self.assertAlmostEqual(hot, 0.0)

    def test_hot_shortfall_is_reported(self):
        cold, hot = temperature_gap((-40.0, 80.0), (-60.0, 60.0))
        self.assertAlmostEqual(hot, 20.0)

    def test_coincident_limits_leave_no_gap(self):
        self.assertEqual(temperature_gap((-40.0, 80.0), (-40.0, 80.0)), (0.0, 0.0))

    def test_inverted_candidate_range_rejected(self):
        with self.assertRaises(ValueError):
            temperature_gap((-40.0, 80.0), (120.0, -60.0))


class ScreeningTests(unittest.TestCase):
    def _duty(self):
        return duty_from_interface(INTERFACE)

    def test_qualified_candidate_survives(self):
        record = screen_candidate(CANDIDATES[0], self._duty())
        self.assertTrue(record["suitable"])
        self.assertEqual(record["reasons"], [])

    def test_unqualified_candidate_is_eliminated(self):
        record = screen_candidate(CANDIDATES[2], self._duty())
        self.assertFalse(record["suitable"])
        self.assertIn("not qualified", record["reasons"][0])

    def test_underrated_pressure_is_the_reason(self):
        record = screen_candidate(CANDIDATES[3], self._duty())
        self.assertFalse(record["suitable"])
        self.assertTrue(any("contact pressure" in reason for reason in record["reasons"]))

    def test_governing_margin_is_the_smallest_ratio(self):
        record = screen_candidate(CANDIDATES[1], self._duty())
        self.assertAlmostEqual(
            record["governing_margin"],
            min(record["pressure_margin"], record["speed_margin"], record["cycle_margin"]),
            places=12,
        )

    def test_a_static_interface_leaves_the_speed_margin_unbounded(self):
        spec = dict(INTERFACE)
        spec["speed_rpm"] = 0.0
        record = screen_candidate(CANDIDATES[0], duty_from_interface(spec))
        self.assertTrue(math.isinf(record["speed_margin"]))
        self.assertTrue(record["suitable"])

    def test_capability_exactly_equal_to_the_duty_survives(self):
        duty = self._duty()
        candidate = dict(CANDIDATES[0])
        candidate["max_contact_pressure_mpa"] = duty["contact_pressure_mpa"]
        record = screen_candidate(candidate, duty)
        self.assertTrue(record["suitable"])
        self.assertAlmostEqual(record["pressure_margin"], 1.0, places=9)

    def test_cold_shortfall_eliminates_a_candidate(self):
        candidate = dict(CANDIDATES[0])
        candidate["temperature_c"] = (-20.0, 120.0)
        record = screen_candidate(candidate, self._duty())
        self.assertFalse(record["suitable"])

    def test_non_boolean_qualified_flag_rejected(self):
        candidate = dict(CANDIDATES[0])
        candidate["qualified"] = "yes"
        with self.assertRaises(ValueError):
            screen_candidate(candidate, self._duty())

    def test_missing_candidate_key_rejected(self):
        candidate = dict(CANDIDATES[0])
        del candidate["qualified_cycles"]
        with self.assertRaises(ValueError):
            screen_candidate(candidate, self._duty())


class RankingAndAssessmentTests(unittest.TestCase):
    def test_ranking_puts_survivors_first(self):
        ranked = rank_candidates(CANDIDATES, duty_from_interface(INTERFACE))
        self.assertTrue(ranked[0]["suitable"])
        self.assertFalse(ranked[-1]["suitable"])

    def test_duplicate_candidate_names_rejected(self):
        duplicated = list(CANDIDATES) + [dict(CANDIDATES[0])]
        with self.assertRaises(ValueError):
            rank_candidates(duplicated, duty_from_interface(INTERFACE))

    def test_empty_candidate_list_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([], duty_from_interface(INTERFACE))

    def test_selection_takes_the_highest_governing_margin(self):
        result = assess_lubricant_selection(
            {"interface": INTERFACE, "candidates": CANDIDATES}
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["selected"]["name"], "mos2-dry-film")

    def test_two_survivors_are_reported(self):
        result = assess_lubricant_selection(
            {"interface": INTERFACE, "candidates": CANDIDATES}
        )
        self.assertEqual(len(result["survivors"]), 2)

    def test_no_survivor_raises_a_finding_naming_every_reason(self):
        harsh = dict(INTERFACE)
        harsh["load_n"] = 400.0
        result = assess_lubricant_selection({"interface": harsh, "candidates": CANDIDATES})
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["selected"])
        self.assertEqual(len(result["findings"]), 1)
        for candidate in CANDIDATES:
            self.assertIn(candidate["name"], result["findings"][0])

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_lubricant_selection({"interface": INTERFACE})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_lubricant_selection(["interface"])

    def test_margin_tolerance_is_representation_sized(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
