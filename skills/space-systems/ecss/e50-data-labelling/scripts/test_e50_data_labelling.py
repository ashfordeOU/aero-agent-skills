"""Contract tests for the clause 5.8.2 data labelling logic."""

import unittest

from e50_data_labelling_logic import (
    DEFICIENT,
    SUFFICIENT,
    addressable_values,
    assess_labelling,
    effective_payload_bps,
    field_coverage,
    label_bits,
    label_overhead_fraction,
    min_sequence_bits,
    required_identifier_bits,
    validate_count,
    validate_fields,
    validate_positive,
    validate_width,
    wrap_period_s,
)

LABEL = {
    "source-identifier": 8,
    "destination-identifier": 8,
    "data-type": 8,
    "sequence-count": 14,
    "generation-time": 48,
}


def graded(**override):
    args = {
        "fields": LABEL,
        "distinct_sources": 40,
        "distinct_destinations": 12,
        "rate_per_s": 20.0,
        "ambiguity_window_s": 600.0,
        "payload_bits": 8192.0,
        "capacity_bps": 1000000.0,
        "overhead_allowance": 0.02,
    }
    args.update(override)
    return assess_labelling(**args)


class ValidationTests(unittest.TestCase):
    def test_a_positive_width_is_accepted(self):
        self.assertEqual(validate_width(8), 8)

    def test_a_zero_width_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_width(0)

    def test_a_fractional_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_width(8.5)

    def test_a_boolean_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_width(True)

    def test_an_empty_label_rejected(self):
        with self.assertRaises(ValueError):
            validate_fields({})

    def test_a_label_that_is_not_a_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_fields(["source-identifier"])

    def test_a_blank_field_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_fields({"  ": 8})

    def test_a_field_declared_twice_rejected(self):
        with self.assertRaises(ValueError):
            validate_fields({"Source-Identifier": 8, "source-identifier": 16})

    def test_a_zero_distinct_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(0, "distinct_values")

    def test_a_zero_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "rate_per_s")


class CoverageTests(unittest.TestCase):
    def test_a_full_label_is_complete(self):
        self.assertTrue(field_coverage(LABEL)["complete"])

    def test_a_dropped_field_is_named(self):
        partial = {k: v for k, v in LABEL.items() if k != "generation-time"}
        self.assertEqual(field_coverage(partial)["missing"], ["generation-time"])

    def test_an_unrecognised_field_is_reported(self):
        extra = dict(LABEL, checksum=16)
        self.assertEqual(field_coverage(extra)["unrecognised"], ["checksum"])

    def test_case_and_padding_do_not_hide_a_field(self):
        renamed = {k: v for k, v in LABEL.items() if k != "data-type"}
        renamed[" Data-Type "] = 8
        self.assertEqual(field_coverage(renamed)["missing"], [])

    def test_an_extra_field_does_not_replace_a_missing_one(self):
        partial = {k: v for k, v in LABEL.items() if k != "data-type"}
        partial["apid"] = 11
        self.assertEqual(field_coverage(partial)["missing"], ["data-type"])


class WidthTests(unittest.TestCase):
    def test_one_distinct_value_still_needs_a_bit(self):
        self.assertEqual(required_identifier_bits(1), 1)

    def test_two_distinct_values_need_one_bit(self):
        self.assertEqual(required_identifier_bits(2), 1)

    def test_a_count_on_a_power_of_two_does_not_round_up(self):
        self.assertEqual(required_identifier_bits(256), 8)

    def test_one_past_a_power_of_two_needs_another_bit(self):
        self.assertEqual(required_identifier_bits(257), 9)

    def test_just_under_a_power_of_two_fits(self):
        self.assertEqual(required_identifier_bits(255), 8)

    def test_a_field_addresses_two_to_the_width(self):
        self.assertEqual(addressable_values(8), 256)

    def test_the_required_width_actually_addresses_the_count(self):
        for count in (1, 2, 3, 40, 255, 256, 257, 1000):
            self.assertGreaterEqual(
                addressable_values(required_identifier_bits(count)), count
            )

    def test_one_bit_narrower_does_not_address_the_count(self):
        for count in (3, 40, 257, 1000):
            width = required_identifier_bits(count)
            self.assertLess(addressable_values(width - 1), count)


class SequenceTests(unittest.TestCase):
    def test_wrap_period_is_the_count_space_over_the_rate(self):
        self.assertAlmostEqual(wrap_period_s(14, 20.0), 819.2, places=6)

    def test_a_wider_counter_wraps_later(self):
        self.assertGreater(wrap_period_s(16, 20.0), wrap_period_s(14, 20.0))

    def test_a_faster_source_wraps_sooner(self):
        self.assertLess(wrap_period_s(14, 40.0), wrap_period_s(14, 20.0))

    def test_the_narrowest_counter_covers_the_window(self):
        bits = min_sequence_bits(20.0, 600.0)
        self.assertGreaterEqual(wrap_period_s(bits, 20.0), 600.0)

    def test_one_bit_narrower_wraps_inside_the_window(self):
        bits = min_sequence_bits(20.0, 600.0)
        self.assertLess(wrap_period_s(bits - 1, 20.0), 600.0)

    def test_a_window_landing_on_a_power_of_two_does_not_round_up(self):
        self.assertEqual(min_sequence_bits(16384.0, 1.0), 14)

    def test_one_unit_past_a_power_of_two_needs_another_bit(self):
        self.assertEqual(min_sequence_bits(16385.0, 1.0), 15)

    def test_a_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            min_sequence_bits(20.0, 0.0)


class OverheadTests(unittest.TestCase):
    def test_label_bits_is_the_sum_of_the_fields(self):
        self.assertEqual(label_bits(LABEL), 86)

    def test_overhead_is_label_over_the_whole_unit(self):
        self.assertAlmostEqual(
            label_overhead_fraction(LABEL, 8192.0), 86.0 / (86.0 + 8192.0), places=12
        )

    def test_a_bigger_payload_dilutes_the_label(self):
        self.assertLess(
            label_overhead_fraction(LABEL, 16384.0),
            label_overhead_fraction(LABEL, 4096.0),
        )

    def test_effective_payload_is_capacity_less_the_label_share(self):
        delivered = effective_payload_bps(1000000.0, LABEL, 8192.0)
        self.assertAlmostEqual(
            delivered, 1000000.0 * 8192.0 / (86.0 + 8192.0), places=6
        )

    def test_effective_payload_never_exceeds_capacity(self):
        self.assertLess(effective_payload_bps(1000000.0, LABEL, 8192.0), 1000000.0)

    def test_a_zero_payload_rejected(self):
        with self.assertRaises(ValueError):
            label_overhead_fraction(LABEL, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_a_sound_label_is_sufficient(self):
        self.assertEqual(graded()["verdict"], SUFFICIENT)

    def test_a_sound_label_raises_no_findings(self):
        self.assertEqual(graded()["findings"], [])

    def test_a_missing_field_makes_it_deficient(self):
        partial = {k: v for k, v in LABEL.items() if k != "generation-time"}
        self.assertEqual(graded(fields=partial)["verdict"], DEFICIENT)

    def test_a_missing_field_is_reported(self):
        partial = {k: v for k, v in LABEL.items() if k != "generation-time"}
        result = graded(fields=partial)
        self.assertTrue(any("generation-time" in f for f in result["findings"]))

    def test_too_many_sources_for_the_field_is_deficient(self):
        self.assertEqual(graded(distinct_sources=400)["verdict"], DEFICIENT)

    def test_a_narrow_source_field_is_told_the_width_it_needs(self):
        result = graded(distinct_sources=400)
        width = [w for w in result["identifier_widths"] if w["field"] == "source-identifier"][0]
        self.assertEqual(width["required_bits"], 9)

    def test_the_stated_width_actually_carries_the_sources(self):
        result = graded(distinct_sources=400)
        width = [w for w in result["identifier_widths"] if w["field"] == "source-identifier"][0]
        fixed = graded(
            fields=dict(LABEL, **{"source-identifier": width["required_bits"]}),
            distinct_sources=400,
        )
        self.assertTrue(fixed["identifier_widths"][0]["wide_enough"])

    def test_a_field_addressing_exactly_the_count_is_wide_enough(self):
        result = graded(distinct_sources=256)
        self.assertTrue(result["identifier_widths"][0]["wide_enough"])

    def test_a_counter_wrapping_inside_the_window_is_deficient(self):
        self.assertEqual(graded(ambiguity_window_s=3600.0)["verdict"], DEFICIENT)

    def test_the_stated_counter_width_closes_the_ambiguity(self):
        result = graded(ambiguity_window_s=3600.0)
        fixed = graded(
            fields=dict(LABEL, **{"sequence-count": result["required_sequence_bits"]}),
            ambiguity_window_s=3600.0,
        )
        self.assertTrue(fixed["sequence_unambiguous"])

    def test_an_overhead_breach_makes_it_deficient(self):
        self.assertEqual(graded(payload_bits=256.0)["verdict"], DEFICIENT)

    def test_an_overhead_breach_states_the_payload_that_fits(self):
        result = graded(payload_bits=256.0)
        self.assertTrue(any("at least" in f for f in result["findings"]))

    def test_overhead_landing_on_the_allowance_passes(self):
        exact = label_overhead_fraction(LABEL, 8192.0)
        self.assertTrue(graded(overhead_allowance=exact)["overhead_within_allowance"])

    def test_an_allowance_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            graded(overhead_allowance=1.5)

    def test_an_unrecognised_field_alone_does_not_fail_the_label(self):
        self.assertEqual(graded(fields=dict(LABEL, checksum=16))["verdict"], SUFFICIENT)

    def test_an_unrecognised_field_is_still_surfaced(self):
        result = graded(fields=dict(LABEL, checksum=16))
        self.assertTrue(any("unrecognised label field" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
