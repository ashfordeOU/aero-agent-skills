"""Contract tests for the clause 5.8.3 communication security logic."""

import unittest

from e50_security_logic import (
    COMPLETE,
    DEFICIENT,
    assess_security,
    counter_space,
    min_counter_bits,
    protected_payload_bps,
    rekey_interval_s,
    required_services,
    security_overhead_bits,
    security_overhead_fraction,
    service_coverage,
    validate_count,
    validate_positive,
    validate_sensitivity,
    validate_width,
)

SENSITIVE = {
    "name": "payload-downlink",
    "sensitivity": "sensitive",
    "services": ["integrity", "authentication", "replay-protection"],
}
CRITICAL = {
    "name": "telecommand-uplink",
    "sensitivity": "critical",
    "services": [
        "integrity",
        "authentication",
        "replay-protection",
        "confidentiality",
    ],
}


def graded(**override):
    args = {
        "flows": [SENSITIVE, CRITICAL],
        "tag_bits": 128,
        "iv_bits": 96,
        "counter_bits": 32,
        "payload_bits": 8192.0,
        "capacity_bps": 1000000.0,
        "overhead_allowance": 0.05,
        "frame_rate_per_s": 50.0,
        "key_frame_limit": 100000000,
        "required_key_lifetime_s": 3600.0,
    }
    args.update(override)
    return assess_security(**args)


class ValidationTests(unittest.TestCase):
    def test_a_zero_width_field_is_an_absent_field(self):
        self.assertEqual(validate_width(0, "iv_bits"), 0)

    def test_a_negative_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_width(-8, "tag_bits")

    def test_a_fractional_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_width(12.5, "tag_bits")

    def test_a_boolean_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_width(True, "tag_bits")

    def test_a_zero_frame_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "frame_rate_per_s")

    def test_a_zero_key_frame_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(0, "key_frame_limit")

    def test_an_unknown_sensitivity_group_rejected(self):
        with self.assertRaises(ValueError):
            validate_sensitivity("top-priority")

    def test_sensitivity_case_and_padding_tolerated(self):
        self.assertEqual(validate_sensitivity(" Critical "), "critical")

    def test_an_unknown_service_name_rejected(self):
        with self.assertRaises(ValueError):
            service_coverage("routine", ["integrity", "obfuscation"])

    def test_a_blank_service_name_rejected(self):
        with self.assertRaises(ValueError):
            service_coverage("routine", ["integrity", " "])

    def test_services_must_be_a_collection(self):
        with self.assertRaises(ValueError):
            service_coverage("routine", "integrity")

    def test_an_empty_flow_set_rejected(self):
        with self.assertRaises(ValueError):
            graded(flows=[])


class CoverageTests(unittest.TestCase):
    def test_a_heavier_group_keeps_everything_the_lighter_one_asked_for(self):
        self.assertTrue(required_services("routine") <= required_services("sensitive"))
        self.assertTrue(
            required_services("sensitive") <= required_services("critical")
        )

    def test_only_a_critical_flow_needs_confidentiality(self):
        self.assertIn("confidentiality", required_services("critical"))
        self.assertNotIn("confidentiality", required_services("sensitive"))

    def test_a_fully_served_flow_is_complete(self):
        self.assertTrue(
            service_coverage(SENSITIVE["sensitivity"], SENSITIVE["services"])["complete"]
        )

    def test_a_missing_service_is_named(self):
        coverage = service_coverage("sensitive", ["integrity", "authentication"])
        self.assertEqual(coverage["missing"], ["replay-protection"])

    def test_confidentiality_does_not_substitute_for_authentication(self):
        coverage = service_coverage(
            "sensitive", ["integrity", "confidentiality", "replay-protection"]
        )
        self.assertEqual(coverage["missing"], ["authentication"])

    def test_a_service_beyond_the_requirement_is_reported_separately(self):
        coverage = service_coverage(
            "sensitive",
            ["integrity", "authentication", "replay-protection", "confidentiality"],
        )
        self.assertEqual(coverage["beyond_requirement"], ["confidentiality"])

    def test_a_service_beyond_the_requirement_does_not_break_completeness(self):
        coverage = service_coverage(
            "routine", ["integrity", "authentication"]
        )
        self.assertTrue(coverage["complete"])

    def test_service_names_tolerate_case_and_padding(self):
        coverage = service_coverage("routine", [" Integrity "])
        self.assertTrue(coverage["complete"])


class OverheadTests(unittest.TestCase):
    def test_overhead_is_the_sum_of_the_security_fields(self):
        self.assertEqual(security_overhead_bits(128, 96, 32), 256)

    def test_an_absent_field_costs_nothing(self):
        self.assertEqual(security_overhead_bits(128, 0, 32), 160)

    def test_overhead_fraction_is_taken_over_the_whole_frame(self):
        self.assertAlmostEqual(
            security_overhead_fraction(256, 8192.0), 256.0 / (256.0 + 8192.0), places=12
        )

    def test_a_bigger_frame_dilutes_the_security_fields(self):
        self.assertLess(
            security_overhead_fraction(256, 16384.0),
            security_overhead_fraction(256, 2048.0),
        )

    def test_protected_payload_is_capacity_less_the_security_share(self):
        self.assertAlmostEqual(
            protected_payload_bps(1000000.0, 256, 8192.0),
            1000000.0 * 8192.0 / (256.0 + 8192.0),
            places=6,
        )

    def test_protected_payload_never_reaches_capacity(self):
        self.assertLess(protected_payload_bps(1000000.0, 256, 8192.0), 1000000.0)

    def test_a_zero_payload_rejected(self):
        with self.assertRaises(ValueError):
            security_overhead_fraction(256, 0.0)


class KeyLifetimeTests(unittest.TestCase):
    def test_counter_space_is_two_to_the_width(self):
        self.assertEqual(counter_space(16), 65536)

    def test_a_zero_width_counter_numbers_nothing(self):
        self.assertEqual(counter_space(0), 0)

    def test_a_zero_width_counter_cannot_bound_a_key(self):
        with self.assertRaises(ValueError):
            rekey_interval_s(0, 50.0, 1000)

    def test_the_counter_binds_when_it_is_the_smaller_space(self):
        key = rekey_interval_s(16, 50.0, 100000000)
        self.assertEqual(key["binding_bound"], "replay-counter")

    def test_the_key_schedule_binds_when_the_counter_is_wide(self):
        key = rekey_interval_s(32, 50.0, 100000)
        self.assertEqual(key["binding_bound"], "key-frame-limit")

    def test_the_interval_is_the_binding_frame_count_over_the_rate(self):
        key = rekey_interval_s(16, 50.0, 100000000)
        self.assertAlmostEqual(key["interval_s"], 65536.0 / 50.0, places=9)

    def test_a_faster_frame_rate_shortens_the_key_life(self):
        slow = rekey_interval_s(16, 10.0, 100000000)["interval_s"]
        fast = rekey_interval_s(16, 100.0, 100000000)["interval_s"]
        self.assertLess(fast, slow)

    def test_the_narrowest_counter_survives_the_lifetime(self):
        bits = min_counter_bits(50.0, 3600.0)
        self.assertGreaterEqual(counter_space(bits) / 50.0, 3600.0)

    def test_one_bit_narrower_does_not_survive_the_lifetime(self):
        bits = min_counter_bits(50.0, 3600.0)
        self.assertLess(counter_space(bits - 1) / 50.0, 3600.0)

    def test_a_frame_count_on_a_power_of_two_does_not_round_up(self):
        self.assertEqual(min_counter_bits(65536.0, 1.0), 16)

    def test_one_frame_past_a_power_of_two_needs_another_bit(self):
        self.assertEqual(min_counter_bits(65537.0, 1.0), 17)


class AssessmentTests(unittest.TestCase):
    def test_a_sound_design_is_complete(self):
        self.assertEqual(graded()["verdict"], COMPLETE)

    def test_a_sound_design_raises_no_findings(self):
        self.assertEqual(graded()["findings"], [])

    def test_an_unprotected_critical_flow_is_deficient(self):
        weak = dict(CRITICAL, services=["integrity", "authentication"])
        self.assertEqual(graded(flows=[SENSITIVE, weak])["verdict"], DEFICIENT)

    def test_the_unprotected_flow_is_named_with_its_group(self):
        weak = dict(CRITICAL, services=["integrity", "authentication"])
        result = graded(flows=[SENSITIVE, weak])
        self.assertTrue(
            any("telecommand-uplink is a critical flow" in f for f in result["findings"])
        )

    def test_an_overhead_breach_is_deficient(self):
        self.assertEqual(graded(payload_bits=1024.0)["verdict"], DEFICIENT)

    def test_an_overhead_breach_states_the_frame_size_that_fits(self):
        result = graded(payload_bits=1024.0)
        self.assertTrue(any("at least" in f for f in result["findings"]))

    def test_overhead_landing_on_the_allowance_passes(self):
        exact = security_overhead_fraction(256, 8192.0)
        self.assertTrue(graded(overhead_allowance=exact)["overhead_within_allowance"])

    def test_a_counter_that_wraps_under_one_key_is_deficient(self):
        self.assertEqual(graded(counter_bits=8)["verdict"], DEFICIENT)

    def test_a_wrapping_counter_is_told_the_width_it_needs(self):
        result = graded(counter_bits=8)
        fixed = graded(counter_bits=result["required_counter_bits"])
        self.assertTrue(fixed["key_lifetime_met"])

    def test_a_short_key_schedule_is_named_as_the_bound_instead(self):
        result = graded(key_frame_limit=1000)
        self.assertTrue(any("the key schedule is" in f for f in result["findings"]))

    def test_a_key_lifetime_met_exactly_still_passes(self):
        exact = graded()["key"]["interval_s"]
        self.assertTrue(graded(required_key_lifetime_s=exact)["key_lifetime_met"])

    def test_a_flow_without_a_name_is_rejected(self):
        with self.assertRaises(ValueError):
            graded(flows=[{"sensitivity": "routine", "services": ["integrity"]}])

    def test_an_allowance_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            graded(overhead_allowance=1.2)


if __name__ == "__main__":
    unittest.main()
