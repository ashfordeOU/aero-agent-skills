"""Contract tests for the clause 7.4.3.1 telemetry secondary header logic."""

import unittest

from e7041_telemetry_packet_secondary_header_logic import (
    DEFAULT_WIDTHS_BITS,
    FIELD_ORDER,
    MANDATORY_FIELDS,
    OPTIONAL_FIELDS,
    PUS_C_VERSION_NUMBER,
    assess_counter_sequence,
    assess_secondary_header,
    counter_step,
    is_octet_aligned,
    layout_length_bits,
    layout_length_octets,
    pack_header,
    resolve_layout,
    unpack_header,
    validate_field_width,
    validate_identifier,
    validate_pus_version_number,
    validate_unsigned_field,
)

FULL_OPTIONALS = [
    "spacecraft-time-reference-status",
    "message-type-counter",
    "destination-id",
    "time-field",
]


def full_values():
    return {
        "pus-version-number": PUS_C_VERSION_NUMBER,
        "spacecraft-time-reference-status": 1,
        "service-type-id": 3,
        "message-subtype-id": 25,
        "message-type-counter": 1234,
        "destination-id": 7,
        "time-field": 123456789,
    }


class FieldWidthTests(unittest.TestCase):
    def test_default_width_accepted(self):
        self.assertEqual(validate_field_width("service-type-id", 8), 8)

    def test_unknown_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width("apid", 11)

    def test_zero_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width("destination-id", 0)

    def test_negative_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width("destination-id", -4)

    def test_boolean_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width("destination-id", True)

    def test_absurd_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width("time-field", 4096)


class LayoutTests(unittest.TestCase):
    def test_mandatory_only_layout_has_three_fields(self):
        layout = resolve_layout()
        self.assertEqual([entry[0] for entry in layout], list(MANDATORY_FIELDS))

    def test_mandatory_only_layout_is_twenty_bits(self):
        self.assertEqual(layout_length_bits(resolve_layout()), 20)

    def test_mandatory_only_layout_is_not_octet_aligned(self):
        self.assertFalse(is_octet_aligned(resolve_layout()))

    def test_misaligned_layout_refuses_an_octet_length(self):
        with self.assertRaises(ValueError):
            layout_length_octets(resolve_layout())

    def test_full_layout_is_octet_aligned(self):
        layout = resolve_layout(FULL_OPTIONALS)
        self.assertTrue(is_octet_aligned(layout))
        self.assertEqual(layout_length_octets(layout), 13)

    def test_layout_keeps_the_wire_field_order(self):
        layout = resolve_layout(FULL_OPTIONALS)
        names = [entry[0] for entry in layout]
        self.assertEqual(names, list(FIELD_ORDER))

    def test_offsets_are_contiguous(self):
        layout = resolve_layout(FULL_OPTIONALS)
        running = 0
        for _name, offset, width in layout:
            self.assertEqual(offset, running)
            running += width

    def test_optional_field_absent_by_default(self):
        names = [entry[0] for entry in resolve_layout(["destination-id"])]
        self.assertNotIn("time-field", names)
        self.assertIn("destination-id", names)

    def test_mandatory_field_cannot_be_listed_as_optional(self):
        with self.assertRaises(ValueError):
            resolve_layout(["service-type-id"])

    def test_duplicate_optional_rejected(self):
        with self.assertRaises(ValueError):
            resolve_layout(["destination-id", "destination-id"])

    def test_width_override_changes_the_length(self):
        layout = resolve_layout(FULL_OPTIONALS, {"destination-id": 8})
        self.assertEqual(layout_length_bits(layout), 96)

    def test_override_for_absent_field_rejected(self):
        with self.assertRaises(ValueError):
            resolve_layout(["destination-id"], {"time-field": 32})

    def test_layout_with_a_hole_rejected(self):
        with self.assertRaises(ValueError):
            layout_length_bits([("service-type-id", 0, 8), ("message-subtype-id", 9, 8)])

    def test_optional_set_matches_the_field_order(self):
        self.assertEqual(
            set(OPTIONAL_FIELDS), set(FIELD_ORDER) - set(MANDATORY_FIELDS)
        )


class FieldValueTests(unittest.TestCase):
    def test_value_fits_its_width(self):
        self.assertEqual(validate_unsigned_field("service-type-id", 255, 8), 255)

    def test_value_above_the_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_unsigned_field("service-type-id", 256, 8)

    def test_negative_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_unsigned_field("destination-id", -1, 16)

    def test_zero_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("service-type-id", 0, 8)

    def test_allocated_identifier_accepted(self):
        self.assertEqual(validate_identifier("message-subtype-id", 25, 8), 25)

    def test_pus_c_version_is_recognised(self):
        value, is_pus_c = validate_pus_version_number(PUS_C_VERSION_NUMBER)
        self.assertEqual(value, PUS_C_VERSION_NUMBER)
        self.assertTrue(is_pus_c)

    def test_other_version_is_not_pus_c(self):
        _value, is_pus_c = validate_pus_version_number(1)
        self.assertFalse(is_pus_c)

    def test_version_beyond_the_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_pus_version_number(16)


class PackingTests(unittest.TestCase):
    def test_round_trip_preserves_every_field(self):
        layout = resolve_layout(FULL_OPTIONALS)
        values = full_values()
        self.assertEqual(unpack_header(layout, pack_header(layout, values)), values)

    def test_packing_is_most_significant_field_first(self):
        layout = resolve_layout()
        packed = pack_header(
            layout,
            {
                "pus-version-number": 2,
                "service-type-id": 3,
                "message-subtype-id": 25,
            },
        )
        self.assertEqual(packed, (2 << 16) | (3 << 8) | 25)

    def test_missing_value_rejected(self):
        layout = resolve_layout()
        with self.assertRaises(ValueError):
            pack_header(layout, {"pus-version-number": 2, "service-type-id": 3})

    def test_extra_value_rejected(self):
        layout = resolve_layout()
        with self.assertRaises(ValueError):
            pack_header(
                layout,
                {
                    "pus-version-number": 2,
                    "service-type-id": 3,
                    "message-subtype-id": 25,
                    "time-field": 1,
                },
            )

    def test_unpack_refuses_an_oversized_word(self):
        layout = resolve_layout()
        with self.assertRaises(ValueError):
            unpack_header(layout, 1 << 40)

    def test_unpack_refuses_a_negative_word(self):
        with self.assertRaises(ValueError):
            unpack_header(resolve_layout(), -1)


class CounterTests(unittest.TestCase):
    def test_consecutive_step_is_one(self):
        self.assertEqual(counter_step(10, 11, 16), 1)

    def test_wrap_step_is_one(self):
        self.assertEqual(counter_step(65535, 0, 16), 1)

    def test_repeat_step_is_zero(self):
        self.assertEqual(counter_step(10, 10, 16), 0)

    def test_continuous_sequence_reports_no_findings(self):
        result = assess_counter_sequence([4, 5, 6, 7])
        self.assertTrue(result["continuous"])
        self.assertEqual(result["missing_total"], 0)

    def test_wrap_is_not_reported_as_a_gap(self):
        result = assess_counter_sequence([65534, 65535, 0, 1])
        self.assertTrue(result["continuous"])
        self.assertEqual(result["wraps"], 1)

    def test_gap_counts_the_missing_reports(self):
        result = assess_counter_sequence([4, 9])
        self.assertEqual(result["missing_total"], 4)
        self.assertFalse(result["continuous"])

    def test_repeat_is_reported_separately_from_a_gap(self):
        result = assess_counter_sequence([4, 4, 5])
        self.assertEqual(result["repeats"], [1])
        self.assertEqual(result["gaps"], [])

    def test_single_reading_rejected(self):
        with self.assertRaises(ValueError):
            assess_counter_sequence([4])

    def test_reading_outside_the_width_rejected(self):
        with self.assertRaises(ValueError):
            assess_counter_sequence([4, 300], 8)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "optional_fields": list(FULL_OPTIONALS),
            "values": full_values(),
        }
        spec.update(overrides)
        return spec

    def test_well_formed_header_is_compliant(self):
        result = assess_secondary_header(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_length_is_reported_in_octets(self):
        result = assess_secondary_header(self._spec())
        self.assertEqual(result["length_octets"], 13)

    def test_service_and_subtype_are_reported_as_the_message_key(self):
        result = assess_secondary_header(self._spec())
        self.assertEqual(result["apid_message_key"], (3, 25))

    def test_misaligned_layout_is_flagged(self):
        values = full_values()
        del values["time-field"]
        spec = self._spec(
            optional_fields=[
                "spacecraft-time-reference-status",
                "message-type-counter",
                "destination-id",
            ],
            values=values,
            width_overrides={"destination-id": 13},
        )
        result = assess_secondary_header(spec)
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["length_octets"])
        self.assertIn("octet boundary", result["findings"][0])

    def test_non_pus_c_version_is_flagged(self):
        values = full_values()
        values["pus-version-number"] = 1
        result = assess_secondary_header(self._spec(values=values))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("version number" in f for f in result["findings"]))

    def test_counter_gap_is_flagged(self):
        result = assess_secondary_header(self._spec(counter_readings=[1, 2, 9]))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("skipped" in f for f in result["findings"]))

    def test_counter_repeat_is_flagged(self):
        result = assess_secondary_header(self._spec(counter_readings=[1, 1, 2]))
        self.assertTrue(any("repeated" in f for f in result["findings"]))

    def test_clean_counter_leaves_the_header_compliant(self):
        result = assess_secondary_header(self._spec(counter_readings=[1, 2, 3]))
        self.assertTrue(result["compliant"])
        self.assertTrue(result["counter_assessment"]["continuous"])

    def test_counter_readings_without_the_field_rejected(self):
        spec = {
            "optional_fields": [],
            "values": {
                "pus-version-number": 2,
                "service-type-id": 3,
                "message-subtype-id": 25,
            },
            "counter_readings": [1, 2],
        }
        with self.assertRaises(ValueError):
            assess_secondary_header(spec)

    def test_zero_service_type_rejected(self):
        values = full_values()
        values["service-type-id"] = 0
        with self.assertRaises(ValueError):
            assess_secondary_header(self._spec(values=values))

    def test_missing_values_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_secondary_header({"optional_fields": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_secondary_header(["values"])

    def test_default_widths_cover_every_field(self):
        self.assertEqual(set(DEFAULT_WIDTHS_BITS), set(FIELD_ORDER))


if __name__ == "__main__":
    unittest.main()
