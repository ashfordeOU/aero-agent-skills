"""Contract tests for the clause 7.3.10 absolute-time data-type logic."""

import unittest

from e7041_absolute_time_logic import (
    CUC_MAX_COARSE_OCTETS,
    CUC_MAX_FINE_OCTETS,
    EPOCH_OFFSETS_S,
    SECONDS_PER_DAY,
    assess_absolute_time_definition,
    cds_resolution_s,
    cds_span_s,
    cuc_resolution_s,
    cuc_span_s,
    decode_cds,
    decode_cuc,
    encode_cds,
    encode_cuc,
    epoch_offset_s,
    rebase_epoch,
    validate_cds_spec,
    validate_cuc_spec,
)

CUC_4_2 = validate_cuc_spec(4, 2)
CUC_4_1 = validate_cuc_spec(4, 1)
CUC_2_1 = validate_cuc_spec(2, 1)
CDS_2_0 = validate_cds_spec(2, 0)


class EpochTests(unittest.TestCase):
    def test_agency_epoch_is_the_datum(self):
        self.assertEqual(epoch_offset_s("agency"), 0)

    def test_a_mission_epoch_is_a_forward_offset(self):
        self.assertGreater(epoch_offset_s("mission-2000"), 0)

    def test_every_named_epoch_is_a_whole_number_of_seconds(self):
        for name, offset in EPOCH_OFFSETS_S.items():
            self.assertIsInstance(offset, int, name)

    def test_unknown_epoch_refused(self):
        with self.assertRaises(ValueError):
            epoch_offset_s("launch")

    def test_non_string_epoch_refused(self):
        with self.assertRaises(ValueError):
            epoch_offset_s(1958)


class CucSpecTests(unittest.TestCase):
    def test_field_octets_are_the_two_counts(self):
        self.assertEqual(CUC_4_2["field_octets"], 6)

    def test_a_fine_free_definition_is_whole_seconds(self):
        spec = validate_cuc_spec(4, 0)
        self.assertAlmostEqual(cuc_resolution_s(spec), 1.0, places=9)

    def test_one_fine_octet_resolves_to_a_two_hundred_fifty_sixth(self):
        self.assertAlmostEqual(cuc_resolution_s(CUC_4_1), 1.0 / 256.0, places=12)

    def test_each_fine_octet_divides_the_resolution_by_two_hundred_fifty_six(self):
        self.assertAlmostEqual(
            cuc_resolution_s(CUC_4_2) * 256.0, cuc_resolution_s(CUC_4_1), places=12
        )

    def test_span_is_set_by_the_coarse_field(self):
        self.assertEqual(cuc_span_s(CUC_4_2), 2 ** 32)

    def test_zero_coarse_octets_refused(self):
        with self.assertRaises(ValueError):
            validate_cuc_spec(0, 2)

    def test_too_many_coarse_octets_refused(self):
        with self.assertRaises(ValueError):
            validate_cuc_spec(CUC_MAX_COARSE_OCTETS + 1, 2)

    def test_too_many_fine_octets_refused(self):
        with self.assertRaises(ValueError):
            validate_cuc_spec(4, CUC_MAX_FINE_OCTETS + 1)

    def test_non_integer_widths_refused(self):
        with self.assertRaises(ValueError):
            validate_cuc_spec(4.0, 2)

    def test_boolean_width_refused(self):
        with self.assertRaises(ValueError):
            validate_cuc_spec(True, 2)


class CucCodingTests(unittest.TestCase):
    def test_a_whole_second_has_no_fine_part(self):
        out = encode_cuc(120.0, CUC_4_1)
        self.assertEqual((out["coarse"], out["fine"]), (120, 0))

    def test_a_half_second_fills_half_the_fine_field(self):
        out = encode_cuc(10.5, CUC_4_1)
        self.assertEqual((out["coarse"], out["fine"]), (10, 128))

    def test_encoding_truncates_downwards(self):
        out = encode_cuc(10.9999, CUC_4_1)
        self.assertEqual(out["coarse"], 10)
        self.assertLess(out["fine"], 256)

    def test_the_decoded_time_never_exceeds_the_original(self):
        # Coarse/fine coding truncates, so a round trip loses a
        # quantisation remainder in [0, one tick) and never gains one.
        # Asserting the remainder states that directly and catches a decode
        # that overshoots. The old form, back <= value + 1e-12, was no
        # tolerance at all at the top of the range: one place at 99999.5 is
        # 1.5e-11, so the addition was a no-op and the slack disappeared.
        tick = cuc_resolution_s(CUC_4_2)
        for value in (0.0, 1.0, 3.7, 12345.6789, 99999.5):
            out = encode_cuc(value, CUC_4_2)
            back = decode_cuc(out["coarse"], out["fine"], CUC_4_2)
            remainder = value - back
            self.assertGreaterEqual(remainder, 0.0, value)
            self.assertLess(remainder, tick, value)

    def test_round_trip_is_exact_on_a_resolution_boundary(self):
        out = encode_cuc(7.25, CUC_4_1)
        self.assertAlmostEqual(decode_cuc(out["coarse"], out["fine"], CUC_4_1), 7.25, places=9)

    def test_a_time_before_the_epoch_refused(self):
        with self.assertRaises(ValueError):
            encode_cuc(-1.0, CUC_4_1)

    def test_a_time_past_the_coarse_span_refused_not_wrapped(self):
        with self.assertRaises(ValueError):
            encode_cuc(float(cuc_span_s(CUC_2_1)), CUC_2_1)

    def test_the_last_second_inside_the_span_is_accepted(self):
        out = encode_cuc(float(cuc_span_s(CUC_2_1) - 1), CUC_2_1)
        self.assertEqual(out["coarse"], cuc_span_s(CUC_2_1) - 1)

    def test_a_non_finite_time_refused(self):
        with self.assertRaises(ValueError):
            encode_cuc(float("inf"), CUC_4_1)

    def test_a_fine_count_overflowing_its_field_refused(self):
        with self.assertRaises(ValueError):
            decode_cuc(10, 256, CUC_4_1)

    def test_a_coarse_count_overflowing_its_field_refused(self):
        with self.assertRaises(ValueError):
            decode_cuc(cuc_span_s(CUC_2_1), 0, CUC_2_1)

    def test_a_negative_count_refused(self):
        with self.assertRaises(ValueError):
            decode_cuc(-1, 0, CUC_4_1)


class CdsCodingTests(unittest.TestCase):
    def test_millisecond_resolution_by_default(self):
        self.assertAlmostEqual(cds_resolution_s(CDS_2_0), 1e-3, places=12)

    def test_a_microsecond_segment_refines_the_resolution(self):
        self.assertAlmostEqual(cds_resolution_s(validate_cds_spec(2, 1)), 1e-6, places=15)

    def test_span_is_whole_days(self):
        self.assertEqual(cds_span_s(CDS_2_0), (2 ** 16) * SECONDS_PER_DAY)

    def test_a_time_splits_into_day_and_millisecond_of_day(self):
        out = encode_cds(float(SECONDS_PER_DAY) + 1.5, CDS_2_0)
        self.assertEqual(out["day"], 1)
        self.assertEqual(out["ms_of_day"], 1500)

    def test_cds_round_trip(self):
        out = encode_cds(90061.25, CDS_2_0)
        self.assertAlmostEqual(decode_cds(out["day"], out["ms_of_day"], CDS_2_0), 90061.25,
                               places=6)

    def test_a_time_past_the_day_field_refused(self):
        with self.assertRaises(ValueError):
            encode_cds(float(cds_span_s(CDS_2_0)), CDS_2_0)

    def test_a_millisecond_count_beyond_a_day_refused(self):
        with self.assertRaises(ValueError):
            decode_cds(1, 86400000, CDS_2_0)

    def test_an_unsupported_day_width_refused(self):
        with self.assertRaises(ValueError):
            validate_cds_spec(4, 0)

    def test_an_unsupported_submillisecond_segment_refused(self):
        with self.assertRaises(ValueError):
            validate_cds_spec(2, 3)


class RebaseTests(unittest.TestCase):
    def test_rebasing_to_the_same_epoch_changes_nothing(self):
        self.assertAlmostEqual(rebase_epoch(500.0, "agency", "agency"), 500.0, places=9)

    def test_rebasing_to_a_later_epoch_reduces_the_count(self):
        offset = epoch_offset_s("mission-2000")
        self.assertAlmostEqual(
            rebase_epoch(offset + 10.0, "agency", "mission-2000"), 10.0, places=6
        )

    def test_rebasing_before_the_target_epoch_refused(self):
        with self.assertRaises(ValueError):
            rebase_epoch(10.0, "agency", "mission-2000")

    def test_rebasing_an_unknown_epoch_refused(self):
        with self.assertRaises(ValueError):
            rebase_epoch(10.0, "agency", "launch")


class AssessmentTests(unittest.TestCase):
    def test_an_adequate_definition_reports_no_findings(self):
        report = assess_absolute_time_definition(
            CUC_4_2, samples=[0.0, 1.5, 1000.25], required_resolution_s=1e-3,
            mission_end_s=1.0e9
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["adequate"])

    def test_a_coarse_definition_fails_the_resolution_need(self):
        report = assess_absolute_time_definition(
            validate_cuc_spec(4, 0), samples=[1.5], required_resolution_s=1e-3
        )
        self.assertTrue(any("coarser than" in f for f in report["findings"]))

    def test_a_short_span_fails_the_mission_end(self):
        report = assess_absolute_time_definition(CUC_2_1, mission_end_s=1.0e9)
        self.assertTrue(any("short of the mission end" in f for f in report["findings"]))

    def test_a_sample_outside_the_span_is_refused_and_reported(self):
        report = assess_absolute_time_definition(CUC_2_1, samples=[1.0e9])
        self.assertEqual(len(report["refused"]), 1)
        self.assertFalse(report["adequate"])

    def test_truncation_is_never_negative(self):
        report = assess_absolute_time_definition(CUC_4_1, samples=[3.7, 11.9, 0.004])
        for record in report["encoded"]:
            self.assertGreaterEqual(record["truncation_s"], 0.0)

    def test_worst_truncation_stays_inside_the_resolution(self):
        report = assess_absolute_time_definition(CUC_4_1, samples=[3.7, 11.9, 0.004])
        self.assertLessEqual(report["worst_truncation_s"], cuc_resolution_s(CUC_4_1))

    def test_a_cds_definition_is_assessable_too(self):
        report = assess_absolute_time_definition(CDS_2_0, samples=[1.5, 2.25])
        self.assertEqual(report["findings"], [])

    def test_a_non_definition_refused(self):
        with self.assertRaises(ValueError):
            assess_absolute_time_definition({"code": "cuc-p"})

    def test_a_non_positive_required_resolution_refused(self):
        with self.assertRaises(ValueError):
            assess_absolute_time_definition(CUC_4_1, required_resolution_s=0.0)

    def test_the_epoch_is_carried_into_the_report(self):
        report = assess_absolute_time_definition(validate_cuc_spec(4, 2, "mission-2000"))
        self.assertEqual(report["epoch"], "mission-2000")


if __name__ == "__main__":
    unittest.main()
