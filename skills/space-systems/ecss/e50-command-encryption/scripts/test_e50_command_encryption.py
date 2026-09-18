"""Contract tests for the clause 5.4.6 command-protection logic."""

import unittest

from e50_command_encryption_logic import (
    PROTECTION_AUTHENTICATE,
    PROTECTION_AUTHENTICATE_AND_ENCRYPT,
    PROTECTION_NONE,
    USAGE_TOLERANCE,
    assess_command_encryption,
    categorize_commands,
    commands_per_key_period,
    effective_key_bits,
    key_usage_ratio,
    required_protection,
    strength_floor_bits,
)

DICTIONARY = [
    {"name": "TC_HK_DUMP", "hazard_category": "routine"},
    {"name": "TC_MODE_SET", "hazard_category": "mission-critical"},
    {"name": "TC_PYRO_ARM", "hazard_category": "hazardous"},
]


def base_spec(**overrides):
    spec = {
        "commands": DICTIONARY,
        "algorithm": "aes",
        "key_bits": 128,
        "protection_provided": PROTECTION_AUTHENTICATE_AND_ENCRYPT,
        "command_rate_per_day": 400.0,
        "rotation_interval_days": 30.0,
        "commands_per_key_limit": 100000.0,
    }
    spec.update(overrides)
    return spec


class RequiredProtectionTests(unittest.TestCase):
    def test_routine_command_owes_nothing(self):
        self.assertEqual(required_protection("routine"), PROTECTION_NONE)

    def test_mission_critical_owes_authentication(self):
        self.assertEqual(required_protection("mission-critical"), PROTECTION_AUTHENTICATE)

    def test_hazardous_owes_authentication_and_encryption(self):
        self.assertEqual(
            required_protection("hazardous"), PROTECTION_AUTHENTICATE_AND_ENCRYPT
        )

    def test_category_lookup_is_case_insensitive(self):
        self.assertEqual(required_protection("  Hazardous "), PROTECTION_AUTHENTICATE_AND_ENCRYPT)

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            required_protection("fairly-important")

    def test_non_string_category_rejected(self):
        with self.assertRaises(ValueError):
            required_protection(3)

    def test_strength_floor_rises_with_hazard(self):
        self.assertEqual(strength_floor_bits("routine"), 0)
        self.assertEqual(strength_floor_bits("mission-critical"), 112)
        self.assertEqual(strength_floor_bits("hazardous"), 128)


class EffectiveKeyBitsTests(unittest.TestCase):
    def test_aes_delivers_its_declared_length(self):
        self.assertEqual(effective_key_bits("aes", 128), 128)

    def test_two_key_triple_construction_loses_half(self):
        self.assertEqual(effective_key_bits("triple-des-two-key", 112), 56)

    def test_three_key_triple_construction_loses_its_meet_in_the_middle_margin(self):
        self.assertEqual(effective_key_bits("triple-des-three-key", 168), 73)

    def test_block_size_caps_a_long_key(self):
        self.assertEqual(effective_key_bits("aes", 256, block_bits=64), 128)

    def test_unknown_algorithm_rejected(self):
        with self.assertRaises(ValueError):
            effective_key_bits("rot13", 128)

    def test_zero_key_length_rejected(self):
        with self.assertRaises(ValueError):
            effective_key_bits("aes", 0)

    def test_boolean_key_length_rejected(self):
        with self.assertRaises(ValueError):
            effective_key_bits("aes", True)


class KeyBudgetTests(unittest.TestCase):
    def test_commands_per_period_is_rate_times_interval(self):
        self.assertAlmostEqual(commands_per_key_period(400.0, 30.0), 12000.0)

    def test_zero_command_rate_is_allowed(self):
        self.assertAlmostEqual(commands_per_key_period(0.0, 30.0), 0.0)

    def test_usage_ratio_is_the_consumed_fraction(self):
        self.assertAlmostEqual(key_usage_ratio(400.0, 30.0, 60000.0), 0.2)

    def test_usage_ratio_lands_on_one_at_the_limit(self):
        self.assertAlmostEqual(key_usage_ratio(400.0, 30.0, 12000.0), 1.0, places=9)

    def test_negative_rotation_interval_rejected(self):
        with self.assertRaises(ValueError):
            key_usage_ratio(400.0, -30.0, 12000.0)

    def test_zero_per_key_limit_rejected(self):
        with self.assertRaises(ValueError):
            key_usage_ratio(400.0, 30.0, 0.0)


class CategorizeCommandsTests(unittest.TestCase):
    def test_each_command_lands_in_one_group(self):
        grouping = categorize_commands(DICTIONARY)
        grouped = grouping["grouped"]
        self.assertEqual(grouped[PROTECTION_NONE], ["TC_HK_DUMP"])
        self.assertEqual(grouped[PROTECTION_AUTHENTICATE], ["TC_MODE_SET"])
        self.assertEqual(grouped[PROTECTION_AUTHENTICATE_AND_ENCRYPT], ["TC_PYRO_ARM"])

    def test_strictest_floor_is_carried_out(self):
        self.assertEqual(categorize_commands(DICTIONARY)["strength_floor_bits"], 128)

    def test_routine_only_dictionary_has_a_zero_floor(self):
        only_routine = [{"name": "TC_HK_DUMP", "hazard_category": "routine"}]
        self.assertEqual(categorize_commands(only_routine)["strength_floor_bits"], 0)

    def test_duplicate_command_name_rejected(self):
        with self.assertRaises(ValueError):
            categorize_commands(DICTIONARY + [DICTIONARY[0]])

    def test_empty_dictionary_rejected(self):
        with self.assertRaises(ValueError):
            categorize_commands([])

    def test_command_missing_hazard_category_rejected(self):
        with self.assertRaises(ValueError):
            categorize_commands([{"name": "TC_X"}])


class AssessmentTests(unittest.TestCase):
    def test_well_protected_uplink_is_compliant(self):
        result = assess_command_encryption(base_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_authentication_only_fails_a_hazardous_dictionary(self):
        result = assess_command_encryption(
            base_spec(protection_provided=PROTECTION_AUTHENTICATE)
        )
        self.assertFalse(result["duty_met"])
        self.assertFalse(result["compliant"])

    def test_under_strength_suite_is_flagged_even_when_present(self):
        result = assess_command_encryption(
            base_spec(algorithm="triple-des-two-key", key_bits=112)
        )
        self.assertFalse(result["strength_met"])
        self.assertEqual(result["effective_key_bits"], 56)

    def test_exhausted_key_schedule_is_flagged_with_an_adequate_algorithm(self):
        result = assess_command_encryption(base_spec(commands_per_key_limit=10000.0))
        self.assertTrue(result["strength_met"])
        self.assertFalse(result["key_budget_met"])

    def test_usage_exactly_at_the_limit_still_passes(self):
        result = assess_command_encryption(base_spec(commands_per_key_limit=12000.0))
        self.assertTrue(result["key_budget_met"])
        self.assertAlmostEqual(result["key_usage_ratio"], 1.0, places=9)
        self.assertLessEqual(abs(result["key_usage_ratio"] - 1.0), USAGE_TOLERANCE)

    def test_protection_without_a_demand_raises_a_categorization_finding(self):
        result = assess_command_encryption(
            base_spec(commands=[{"name": "TC_HK_DUMP", "hazard_category": "routine"}])
        )
        self.assertTrue(any("categorization" in f for f in result["findings"]))

    def test_demanded_protection_is_the_strictest_in_the_dictionary(self):
        result = assess_command_encryption(base_spec())
        self.assertEqual(result["demanded_protection"], PROTECTION_AUTHENTICATE_AND_ENCRYPT)

    def test_unknown_protection_value_rejected(self):
        with self.assertRaises(ValueError):
            assess_command_encryption(base_spec(protection_provided="obfuscated"))

    def test_missing_spec_key_rejected(self):
        spec = base_spec()
        del spec["key_bits"]
        with self.assertRaises(ValueError):
            assess_command_encryption(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_command_encryption(["commands"])


if __name__ == "__main__":
    unittest.main()
