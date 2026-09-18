"""Contract tests for the clause 5.5.3 telemetry source-identification logic."""

import unittest

from e50_telemetry_source_identification_logic import (
    WINDOW_TOLERANCE_S,
    ambiguity_window_s,
    assess_source_identification,
    duplicate_tuples,
    enumeration_bits,
    field_overflows,
    identifier_tuple,
    premature_reuses,
    required_field_bits,
    validate_stream,
    validate_stream_set,
    value_bits,
)


def _stream(name, spacecraft_id, source_id, virtual_channel=0):
    return {
        "name": name,
        "spacecraft_id": spacecraft_id,
        "source_id": source_id,
        "virtual_channel": virtual_channel,
    }


def _fleet():
    return [
        _stream("sat-a-platform", 42, 10, 0),
        _stream("sat-a-payload", 42, 11, 1),
        _stream("sat-a-recorder", 42, 300, 1),
        _stream("sat-b-platform", 43, 10, 0),
    ]


class ValidateStreamTests(unittest.TestCase):
    def test_returns_normalised_record(self):
        record = validate_stream(_stream("sat-a-platform", 42, 10))
        self.assertEqual(record["spacecraft_id"], 42)
        self.assertEqual(record["source_id"], 10)

    def test_virtual_channel_may_be_absent(self):
        stream = _stream("sat-a-platform", 42, 10)
        del stream["virtual_channel"]
        self.assertIsNone(validate_stream(stream)["virtual_channel"])

    def test_missing_key_rejected(self):
        stream = _stream("sat-a-platform", 42, 10)
        del stream["source_id"]
        with self.assertRaises(ValueError):
            validate_stream(stream)

    def test_negative_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream(_stream("sat-a-platform", 42, -1))

    def test_float_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream(_stream("sat-a-platform", 42.0, 10))

    def test_boolean_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream(_stream("sat-a-platform", True, 10))

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream(_stream("   ", 42, 10))

    def test_non_mapping_stream_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream(("sat-a-platform", 42, 10))

    def test_zero_identifier_allowed(self):
        self.assertEqual(validate_stream(_stream("idle", 0, 0))["source_id"], 0)


class StreamSetTests(unittest.TestCase):
    def test_fleet_validates(self):
        self.assertEqual(len(validate_stream_set(_fleet())), 4)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream_set([])

    def test_duplicate_stream_name_rejected(self):
        streams = _fleet()
        streams.append(_stream("sat-a-platform", 44, 12))
        with self.assertRaises(ValueError):
            validate_stream_set(streams)

    def test_mapping_instead_of_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream_set({"name": "sat-a-platform"})


class TupleTests(unittest.TestCase):
    def test_tuple_pairs_spacecraft_and_source(self):
        self.assertEqual(identifier_tuple(_stream("sat-a-platform", 42, 10)), (42, 10))

    def test_same_source_on_two_spacecraft_is_not_a_duplicate(self):
        self.assertEqual(duplicate_tuples(_fleet()), {})

    def test_repeated_tuple_within_one_spacecraft_is_a_duplicate(self):
        streams = _fleet()
        streams.append(_stream("sat-a-shadow", 42, 10, 2))
        duplicates = duplicate_tuples(streams)
        self.assertEqual(
            duplicates[(42, 10)], ["sat-a-platform", "sat-a-shadow"]
        )

    def test_duplicate_report_lists_only_the_clashing_tuple(self):
        streams = _fleet()
        streams.append(_stream("sat-a-shadow", 42, 11, 2))
        self.assertEqual(sorted(duplicate_tuples(streams)), [(42, 11)])


class FieldWidthTests(unittest.TestCase):
    def test_enumeration_bits_of_one_value(self):
        self.assertEqual(enumeration_bits(1), 1)

    def test_enumeration_bits_of_a_power_of_two(self):
        self.assertEqual(enumeration_bits(8), 3)

    def test_enumeration_bits_just_over_a_power_of_two(self):
        self.assertEqual(enumeration_bits(9), 4)

    def test_enumeration_bits_rejects_zero(self):
        with self.assertRaises(ValueError):
            enumeration_bits(0)

    def test_value_bits_of_zero_is_one(self):
        self.assertEqual(value_bits(0), 1)

    def test_value_bits_of_three_hundred(self):
        self.assertEqual(value_bits(300), 9)

    def test_value_bits_rejects_negative(self):
        with self.assertRaises(ValueError):
            value_bits(-5)

    def test_sparse_plan_is_sized_by_the_largest_value_not_the_count(self):
        # four sources would enumerate in two bits; 300 needs nine.
        self.assertEqual(required_field_bits([10, 11, 300, 10]), 9)

    def test_dense_plan_is_sized_by_the_count(self):
        self.assertEqual(required_field_bits([0, 1, 2, 3]), 2)

    def test_required_bits_rejects_an_empty_plan(self):
        with self.assertRaises(ValueError):
            required_field_bits([])

    def test_overflowing_source_identifier_is_reported(self):
        findings = field_overflows(_fleet(), 8, 8)
        self.assertEqual(len(findings), 1)
        self.assertIn("sat-a-recorder", findings[0])

    def test_wide_enough_fields_report_nothing(self):
        self.assertEqual(field_overflows(_fleet(), 8, 11), [])

    def test_zero_field_width_rejected(self):
        with self.assertRaises(ValueError):
            field_overflows(_fleet(), 0, 11)


class ReuseWindowTests(unittest.TestCase):
    def test_window_sums_the_contributors(self):
        self.assertAlmostEqual(ambiguity_window_s(86400.0, 3600.0, 1800.0), 91800.0)

    def test_ingest_delay_defaults_to_zero(self):
        self.assertAlmostEqual(ambiguity_window_s(100.0, 10.0), 110.0)

    def test_negative_contributor_rejected(self):
        with self.assertRaises(ValueError):
            ambiguity_window_s(-1.0, 10.0)

    def test_reuse_inside_the_window_is_flagged(self):
        findings = premature_reuses(
            [{"source_id": 11, "elapsed_since_retirement_s": 3600.0}], 91800.0
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("11", findings[0])

    def test_reuse_well_outside_the_window_is_clean(self):
        self.assertEqual(
            premature_reuses(
                [{"source_id": 11, "elapsed_since_retirement_s": 200000.0}], 91800.0
            ),
            [],
        )

    def test_reuse_exactly_at_the_window_is_accepted(self):
        window = 91800.0
        self.assertEqual(
            premature_reuses(
                [{"source_id": 11, "elapsed_since_retirement_s": window}], window
            ),
            [],
        )
        self.assertAlmostEqual(window - window, 0.0, places=9)

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(WINDOW_TOLERANCE_S, 1e-6)

    def test_malformed_reuse_record_rejected(self):
        with self.assertRaises(ValueError):
            premature_reuses([{"source_id": 11}], 100.0)

    def test_negative_elapsed_time_rejected(self):
        with self.assertRaises(ValueError):
            premature_reuses(
                [{"source_id": 11, "elapsed_since_retirement_s": -1.0}], 100.0
            )


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "streams": _fleet(),
            "spacecraft_id_bits": 8,
            "source_id_bits": 11,
            "storage_retention_s": 86400.0,
            "playback_delay_s": 3600.0,
            "archive_ingest_s": 1800.0,
            "reuses": [],
        }
        spec.update(overrides)
        return spec

    def test_clean_plan_is_compliant(self):
        result = assess_source_identification(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_tuple_map_is_reported(self):
        result = assess_source_identification(self._spec())
        self.assertEqual(result["tuples"]["sat-b-platform"], (43, 10))

    def test_required_widths_are_reported(self):
        result = assess_source_identification(self._spec())
        self.assertEqual(result["required_source_id_bits"], 9)
        self.assertEqual(result["required_spacecraft_id_bits"], 6)

    def test_duplicate_tuple_is_flagged(self):
        streams = _fleet()
        streams.append(_stream("sat-a-shadow", 42, 10, 3))
        result = assess_source_identification(self._spec(streams=streams))
        self.assertFalse(result["compliant"])
        self.assertIn((42, 10), result["duplicate_tuples"])

    def test_narrow_field_is_flagged(self):
        result = assess_source_identification(self._spec(source_id_bits=8))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("carries 8" in f for f in result["findings"]))

    def test_premature_reuse_is_flagged(self):
        result = assess_source_identification(
            self._spec(reuses=[{"source_id": 11, "elapsed_since_retirement_s": 60.0}])
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("ambiguity window" in f for f in result["findings"]))

    def test_window_is_the_sum_of_the_declared_delays(self):
        result = assess_source_identification(self._spec())
        self.assertAlmostEqual(result["ambiguity_window_s"], 91800.0)

    def test_channel_used_as_identifier_is_flagged(self):
        result = assess_source_identification(
            self._spec(channel_used_as_identifier=True)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("virtual channel" in f for f in result["findings"]))

    def test_findings_accumulate_across_defect_kinds(self):
        streams = _fleet()
        streams.append(_stream("sat-a-shadow", 42, 10, 3))
        result = assess_source_identification(
            self._spec(
                streams=streams,
                source_id_bits=8,
                reuses=[{"source_id": 11, "elapsed_since_retirement_s": 60.0}],
                channel_used_as_identifier=True,
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 4)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["source_id_bits"]
        with self.assertRaises(ValueError):
            assess_source_identification(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_source_identification(["streams"])

    def test_non_boolean_channel_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_source_identification(self._spec(channel_used_as_identifier="yes"))


if __name__ == "__main__":
    unittest.main()
