"""Contract tests for the clause 5.5.7 telemetry protection logic."""

import unittest

from e50_telemetry_authentication_and_encryption_logic import (
    MINIMUM_KEY_BITS_BY_PERIOD,
    THROUGHPUT_TOLERANCE_BPS,
    TIER_SERVICES,
    assess_telemetry_protection,
    counter_exhaustion_findings,
    counter_span,
    frames_under_one_key,
    key_strength_findings,
    minimum_key_bits,
    protection_overhead_bits,
    service_gaps,
    services_owed,
    useful_throughput_bps,
    validate_stream,
    validate_stream_set,
)


def _stream(name, tier, payload_bits=8192, rate_hz=4.0, auth=True, conf=False):
    return {
        "name": name,
        "tier": tier,
        "frame_payload_bits": payload_bits,
        "frame_rate_hz": rate_hz,
        "authentication_applied": auth,
        "confidentiality_applied": conf,
    }


def _streams():
    return [
        _stream("housekeeping", "attributable", 8192, 4.0, True, False),
        _stream("payload-science", "sensitive", 8192, 2.0, True, True),
    ]


class ValidateStreamTests(unittest.TestCase):
    def test_returns_normalised_record(self):
        record = validate_stream(_stream("housekeeping", "attributable"))
        self.assertEqual(record["tier"], "attributable")
        self.assertEqual(record["frame_payload_bits"], 8192)

    def test_services_default_to_not_applied(self):
        stream = _stream("housekeeping", "open")
        del stream["authentication_applied"]
        del stream["confidentiality_applied"]
        record = validate_stream(stream)
        self.assertFalse(record["authentication_applied"])
        self.assertFalse(record["confidentiality_applied"])

    def test_unknown_tier_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream(_stream("housekeeping", "top-tier"))

    def test_missing_key_rejected(self):
        stream = _stream("housekeeping", "open")
        del stream["frame_rate_hz"]
        with self.assertRaises(ValueError):
            validate_stream(stream)

    def test_zero_payload_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream(_stream("housekeeping", "open", payload_bits=0))

    def test_float_payload_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream(_stream("housekeeping", "open", payload_bits=8192.0))

    def test_non_boolean_service_flag_rejected(self):
        stream = _stream("housekeeping", "open")
        stream["authentication_applied"] = "yes"
        with self.assertRaises(ValueError):
            validate_stream(stream)

    def test_empty_stream_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream_set([])

    def test_duplicate_stream_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream_set(_streams() + [_stream("housekeeping", "open")])


class TierMappingTests(unittest.TestCase):
    def test_open_tier_owes_nothing(self):
        self.assertEqual(
            services_owed("open"), {"authentication": False, "confidentiality": False}
        )

    def test_attributable_tier_owes_authentication_only(self):
        owed = services_owed("attributable")
        self.assertTrue(owed["authentication"])
        self.assertFalse(owed["confidentiality"])

    def test_sensitive_tier_owes_both(self):
        owed = services_owed("sensitive")
        self.assertTrue(owed["authentication"])
        self.assertTrue(owed["confidentiality"])

    def test_every_published_tier_is_mapped(self):
        for tier in TIER_SERVICES:
            self.assertEqual(sorted(services_owed(tier)), ["authentication", "confidentiality"])

    def test_unknown_tier_rejected(self):
        with self.assertRaises(ValueError):
            services_owed("unmapped")

    def test_matching_services_give_no_gap(self):
        self.assertEqual(service_gaps(_streams()[0]), [])

    def test_missing_authentication_is_a_gap(self):
        findings = service_gaps(_stream("housekeeping", "attributable", auth=False))
        self.assertEqual(len(findings), 1)
        self.assertIn("owes authentication", findings[0])

    def test_missing_confidentiality_is_a_gap(self):
        findings = service_gaps(
            _stream("payload-science", "sensitive", auth=True, conf=False)
        )
        self.assertTrue(any("owes confidentiality" in f for f in findings))

    def test_encryption_without_integrity_is_refused(self):
        findings = service_gaps(
            _stream("payload-science", "sensitive", auth=False, conf=True)
        )
        self.assertTrue(any("without an integrity service" in f for f in findings))

    def test_over_protection_above_the_tier_is_not_a_gap(self):
        self.assertEqual(
            service_gaps(_stream("housekeeping", "open", auth=True, conf=True)), []
        )


class OverheadTests(unittest.TestCase):
    def test_authentication_costs_the_tag(self):
        overhead = protection_overhead_bits(
            _stream("housekeeping", "attributable", 8192, 4.0, True, False), 128, 96, 128
        )
        self.assertEqual(overhead, 128)

    def test_unprotected_stream_costs_nothing(self):
        overhead = protection_overhead_bits(
            _stream("open-beacon", "open", 8192, 4.0, False, False), 128, 96, 128
        )
        self.assertEqual(overhead, 0)

    def test_encryption_adds_the_initialisation_vector(self):
        overhead = protection_overhead_bits(
            _stream("payload-science", "sensitive", 8192, 2.0, True, True), 128, 96, 128
        )
        # 8192 is a whole number of 128-bit blocks, so no padding.
        self.assertEqual(overhead, 128 + 96)

    def test_block_padding_fills_the_last_block(self):
        overhead = protection_overhead_bits(
            _stream("payload-science", "sensitive", 8200, 2.0, True, True), 128, 96, 128
        )
        # 8200 mod 128 = 8, so 120 bits of padding.
        self.assertEqual(overhead, 128 + 96 + 120)

    def test_zero_tag_length_rejected(self):
        with self.assertRaises(ValueError):
            protection_overhead_bits(_streams()[0], 0, 96, 128)

    def test_negative_block_size_rejected(self):
        with self.assertRaises(ValueError):
            protection_overhead_bits(_streams()[0], 128, 96, -128)

    def test_throughput_drops_by_the_overhead(self):
        stream = _stream("housekeeping", "attributable", 8192, 4.0, True, False)
        self.assertAlmostEqual(useful_throughput_bps(stream, 128), (8192 - 128) * 4.0)

    def test_unprotected_throughput_is_the_full_payload(self):
        stream = _stream("open-beacon", "open", 8192, 4.0, False, False)
        self.assertAlmostEqual(useful_throughput_bps(stream, 0), 8192 * 4.0)

    def test_overhead_larger_than_the_frame_leaves_nothing(self):
        stream = _stream("tiny", "sensitive", 64, 1.0, True, True)
        self.assertAlmostEqual(useful_throughput_bps(stream, 256), 0.0)

    def test_negative_overhead_rejected(self):
        with self.assertRaises(ValueError):
            useful_throughput_bps(_streams()[0], -1)


class KeyAndCounterTests(unittest.TestCase):
    def test_short_period_takes_the_lowest_rung(self):
        self.assertEqual(minimum_key_bits(1.0), MINIMUM_KEY_BITS_BY_PERIOD[0][1])

    def test_decade_period_needs_the_middle_rung(self):
        self.assertEqual(minimum_key_bits(10.0), 128)

    def test_thirty_year_period_needs_the_long_key(self):
        self.assertEqual(minimum_key_bits(30.0), 256)

    def test_beyond_the_table_stays_at_the_longest_key(self):
        self.assertEqual(minimum_key_bits(100.0), 256)

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            minimum_key_bits(0.0)

    def test_short_key_for_a_long_period_is_flagged(self):
        findings = key_strength_findings(128, 30.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("256 bits", findings[0])

    def test_adequate_key_is_clean(self):
        self.assertEqual(key_strength_findings(256, 30.0), [])

    def test_key_exactly_at_the_minimum_is_accepted(self):
        self.assertEqual(key_strength_findings(128, 10.0), [])

    def test_frames_under_one_key_is_rate_times_period(self):
        self.assertAlmostEqual(frames_under_one_key(2.0, 86400.0), 172800.0)

    def test_counter_span_is_a_power_of_two(self):
        self.assertEqual(counter_span(16), 65536)

    def test_counter_span_rejects_zero_bits(self):
        with self.assertRaises(ValueError):
            counter_span(0)

    def test_counter_exhaustion_is_flagged(self):
        findings = counter_exhaustion_findings(
            _stream("payload-science", "sensitive", 8192, 2.0, True, True), 16, 86400.0
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("share an initialisation vector", findings[0])

    def test_wide_counter_is_clean(self):
        self.assertEqual(
            counter_exhaustion_findings(
                _stream("payload-science", "sensitive", 8192, 2.0, True, True),
                32,
                86400.0,
            ),
            [],
        )

    def test_counter_exactly_filled_is_accepted(self):
        # 2 frames per second for 32768 seconds fills a 16-bit counter exactly.
        self.assertEqual(
            counter_exhaustion_findings(
                _stream("payload-science", "sensitive", 8192, 2.0, True, True),
                16,
                32768.0,
            ),
            [],
        )

    def test_unencrypted_stream_has_no_counter_concern(self):
        self.assertEqual(
            counter_exhaustion_findings(
                _stream("housekeeping", "attributable", 8192, 100.0, True, False),
                8,
                86400.0,
            ),
            [],
        )


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "streams": _streams(),
            "tag_bits": 128,
            "iv_bits": 96,
            "block_bits": 128,
            "key_bits": 256,
            "protection_years": 30.0,
            "counter_bits": 32,
            "key_period_s": 86400.0,
        }
        spec.update(overrides)
        return spec

    def test_clean_design_is_compliant(self):
        result = assess_telemetry_protection(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_every_stream_is_reported(self):
        result = assess_telemetry_protection(self._spec())
        self.assertEqual(sorted(result["per_stream"]), ["housekeeping", "payload-science"])

    def test_overhead_is_reported_per_stream(self):
        result = assess_telemetry_protection(self._spec())
        self.assertEqual(result["per_stream"]["housekeeping"]["overhead_bits"], 128)
        self.assertEqual(result["per_stream"]["payload-science"]["overhead_bits"], 224)

    def test_useful_throughput_is_reported(self):
        result = assess_telemetry_protection(self._spec())
        self.assertAlmostEqual(
            result["per_stream"]["housekeeping"]["useful_throughput_bps"],
            (8192 - 128) * 4.0,
        )

    def test_demand_above_the_protected_throughput_is_flagged(self):
        result = assess_telemetry_protection(
            self._spec(demand_bps={"housekeeping": 40000.0})
        )
        self.assertFalse(result["compliant"])
        self.assertFalse(result["per_stream"]["housekeeping"]["carries_demand"])

    def test_demand_exactly_at_the_throughput_still_carries(self):
        throughput = (8192 - 128) * 4.0
        result = assess_telemetry_protection(
            self._spec(demand_bps={"housekeeping": throughput})
        )
        self.assertTrue(result["per_stream"]["housekeeping"]["carries_demand"])

    def test_throughput_tolerance_is_representation_sized(self):
        self.assertLess(THROUGHPUT_TOLERANCE_BPS, 1e-6)

    def test_short_key_is_flagged(self):
        result = assess_telemetry_protection(self._spec(key_bits=128))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("credible over" in f for f in result["findings"]))

    def test_unauthenticated_encryption_is_flagged(self):
        streams = _streams()
        streams[1] = _stream("payload-science", "sensitive", 8192, 2.0, False, True)
        result = assess_telemetry_protection(self._spec(streams=streams))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("integrity service" in f for f in result["findings"]))

    def test_narrow_counter_is_flagged(self):
        result = assess_telemetry_protection(self._spec(counter_bits=16))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("initialisation vector" in f for f in result["findings"]))

    def test_counter_span_is_reported(self):
        result = assess_telemetry_protection(self._spec(counter_bits=24))
        self.assertEqual(result["counter_span"], 16777216)

    def test_findings_accumulate_across_defect_kinds(self):
        streams = _streams()
        streams[1] = _stream("payload-science", "sensitive", 8192, 2.0, False, True)
        result = assess_telemetry_protection(
            self._spec(streams=streams, key_bits=128, counter_bits=16)
        )
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["counter_bits"]
        with self.assertRaises(ValueError):
            assess_telemetry_protection(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_telemetry_protection(["streams"])

    def test_demand_map_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_telemetry_protection(self._spec(demand_bps=[40000.0]))


if __name__ == "__main__":
    unittest.main()
