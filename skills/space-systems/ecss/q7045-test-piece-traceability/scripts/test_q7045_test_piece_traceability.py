"""Contract tests for the metallic test-piece traceability logic."""

import unittest

from q7045_test_piece_traceability_logic import (
    MAX_SINGLE_HEAT_FRACTION,
    assess_traceability,
    cross_check_release,
    duplicate_identifiers,
    heat_concentration,
    location_coverage,
    normalise_location,
    normalise_orientation,
    orientation_coverage,
    resolve_depth,
    validate_piece,
)


def record(piece_id="TP-01", heat="H-1", lot="L-1", orientation="L",
           location="mid-thickness", **extra):
    """One fully traceable test-piece record from a rolled plate."""
    item = {
        "piece_id": piece_id,
        "heat_id": heat,
        "lot_id": lot,
        "product_form": "plate",
        "orientation": orientation,
        "location": location,
    }
    item.update(extra)
    return item


def release(heat="H-1", lot="L-1"):
    """One release-documentation entry."""
    return {"heat_id": heat, "lot_id": lot}


class OrientationTests(unittest.TestCase):
    def test_short_code_maps_to_the_axis(self):
        self.assertEqual(normalise_orientation("L"), "longitudinal")
        self.assertEqual(normalise_orientation("ST"), "short-transverse")

    def test_spelt_out_axis_is_accepted(self):
        self.assertEqual(normalise_orientation(" Long-Transverse "), "long-transverse")

    def test_rolling_direction_is_longitudinal(self):
        self.assertEqual(normalise_orientation("rolling-direction"), "longitudinal")

    def test_unmapped_orientation_is_refused_not_defaulted(self):
        with self.assertRaises(ValueError):
            normalise_orientation("diagonal")

    def test_blank_orientation_rejected(self):
        with self.assertRaises(ValueError):
            normalise_orientation("   ")


class LocationTests(unittest.TestCase):
    def test_named_locations_normalise(self):
        self.assertEqual(normalise_location("skin"), "surface")
        self.assertEqual(normalise_location("t/2"), "mid-thickness")

    def test_unmapped_location_refused(self):
        with self.assertRaises(ValueError):
            normalise_location("somewhere-in-the-middle")

    def test_depth_inside_the_thickness_is_returned(self):
        self.assertAlmostEqual(resolve_depth(12.5, 50.0), 12.5, places=9)

    def test_depth_exactly_at_the_thickness_is_accepted(self):
        self.assertAlmostEqual(resolve_depth(50.0, 50.0), 50.0, places=9)

    def test_depth_beyond_the_thickness_rejected(self):
        with self.assertRaises(ValueError):
            resolve_depth(60.0, 50.0)

    def test_negative_depth_rejected(self):
        with self.assertRaises(ValueError):
            resolve_depth(-1.0, 50.0)

    def test_depth_without_a_thickness_rejected(self):
        with self.assertRaises(ValueError):
            validate_piece(record(depth_mm=10.0))


class RecordValidationTests(unittest.TestCase):
    def test_a_complete_record_is_traceable(self):
        result = validate_piece(record())
        self.assertTrue(result["traceable"])
        self.assertEqual(result["record"]["orientation"], "longitudinal")

    def test_a_missing_heat_is_a_finding(self):
        item = record()
        del item["heat_id"]
        result = validate_piece(item)
        self.assertFalse(result["traceable"])
        self.assertTrue(any("heat_id" in f for f in result["findings"]))

    def test_a_blank_lot_is_a_finding(self):
        result = validate_piece(record(lot="   "))
        self.assertFalse(result["traceable"])

    def test_an_unmarked_orientation_is_not_defaulted_to_longitudinal(self):
        item = record()
        del item["orientation"]
        result = validate_piece(item)
        self.assertFalse(result["traceable"])
        self.assertIsNone(result["record"]["orientation"])

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_piece("TP-01")

    def test_declared_depth_is_carried_through(self):
        result = validate_piece(record(depth_mm=12.5, product_thickness_mm=50.0))
        self.assertAlmostEqual(result["record"]["depth_mm"], 12.5, places=9)


class ReleaseCrossCheckTests(unittest.TestCase):
    def test_a_piece_on_the_paperwork_is_not_orphaned(self):
        self.assertEqual(cross_check_release([record()], [release()]), [])

    def test_a_heat_absent_from_the_paperwork_orphans_the_piece(self):
        orphans = cross_check_release([record(heat="H-9")], [release()])
        self.assertEqual(len(orphans), 1)
        self.assertTrue(any("heat" in r for r in orphans[0]["reasons"]))

    def test_a_lot_absent_from_the_paperwork_orphans_the_piece(self):
        orphans = cross_check_release([record(lot="L-9")], [release()])
        self.assertTrue(any("lot" in r for r in orphans[0]["reasons"]))

    def test_release_entry_without_a_heat_rejected(self):
        with self.assertRaises(ValueError):
            cross_check_release([record()], [{"lot_id": "L-1"}])

    def test_non_sequence_release_records_rejected(self):
        with self.assertRaises(ValueError):
            cross_check_release([record()], "H-1")


class SetCoverageTests(unittest.TestCase):
    def test_duplicate_identifiers_are_reported(self):
        self.assertEqual(
            duplicate_identifiers([record(), record(), record("TP-02")]), ["tp-01"]
        )

    def test_distinct_identifiers_produce_no_duplicates(self):
        self.assertEqual(duplicate_identifiers([record("TP-01"), record("TP-02")]), [])

    def test_missing_orientation_shows_in_the_coverage_gap(self):
        coverage = orientation_coverage([record(orientation="L")], ["L", "ST"])
        self.assertEqual(coverage["missing"], ["short-transverse"])

    def test_covered_orientations_leave_no_gap(self):
        coverage = orientation_coverage(
            [record(orientation="L"), record(orientation="ST")], ["L", "ST"]
        )
        self.assertEqual(coverage["missing"], [])

    def test_empty_required_orientation_list_rejected(self):
        with self.assertRaises(ValueError):
            orientation_coverage([record()], [])

    def test_location_coverage_reports_the_unsampled_position(self):
        coverage = location_coverage(
            [record(location="surface")], ["surface", "mid-thickness"]
        )
        self.assertEqual(coverage["missing"], ["mid-thickness"])

    def test_heat_concentration_finds_the_dominant_melt(self):
        pieces = [record(heat="H-1"), record(heat="H-1"), record(heat="H-2")]
        concentration = heat_concentration(pieces)
        self.assertEqual(concentration["dominant_heat"], "h-1")
        self.assertAlmostEqual(concentration["fraction"], 2.0 / 3.0, places=9)

    def test_heat_concentration_of_an_untraced_set_is_none(self):
        self.assertIsNone(heat_concentration([{"piece_id": "TP-01"}])["fraction"])


class AssessmentTests(unittest.TestCase):
    def test_a_clean_set_is_traceable(self):
        pieces = [
            record("TP-01", heat="H-1", orientation="L"),
            record("TP-02", heat="H-2", orientation="ST"),
        ]
        result = assess_traceability(
            pieces,
            [release("H-1"), release("H-2")],
            required_orientations=["L", "ST"],
        )
        self.assertEqual(result["status"], "traceable")
        self.assertTrue(result["every_piece_traceable"])

    def test_an_orphaned_piece_fails_the_set(self):
        pieces = [record("TP-01", heat="H-1"), record("TP-02", heat="H-9")]
        result = assess_traceability(pieces, [release("H-1")])
        self.assertEqual(result["status"], "traceability-finding")
        self.assertFalse(result["every_piece_traceable"])

    def test_a_duplicate_identifier_fails_the_set(self):
        result = assess_traceability([record("TP-01"), record("TP-01")])
        self.assertTrue(any("duplicate" in f for f in result["findings"]))

    def test_a_missing_orientation_in_the_set_is_a_coverage_finding(self):
        result = assess_traceability(
            [record("TP-01", orientation="L")], required_orientations=["L", "ST"]
        )
        self.assertTrue(any("never sampled" in f for f in result["findings"]))

    def test_every_piece_traceable_can_still_fail_coverage(self):
        pieces = [record("TP-%02d" % i, heat="H-1") for i in range(4)]
        result = assess_traceability(pieces, [release("H-1")])
        self.assertTrue(result["every_piece_traceable"])
        self.assertFalse(result["set_acceptable"])

    def test_heat_share_exactly_at_the_limit_is_accepted(self):
        pieces = [
            record("TP-01", heat="H-1"),
            record("TP-02", heat="H-2"),
        ]
        result = assess_traceability(pieces, [release("H-1"), release("H-2")])
        self.assertAlmostEqual(
            result["heat_concentration"]["fraction"], MAX_SINGLE_HEAT_FRACTION, places=9
        )
        self.assertFalse(any("one melt" in f for f in result["findings"]))

    def test_heat_share_well_over_the_limit_is_a_finding(self):
        pieces = [record("TP-%02d" % i, heat="H-1") for i in range(3)]
        pieces.append(record("TP-99", heat="H-2"))
        result = assess_traceability(
            pieces, [release("H-1"), release("H-2")], max_single_heat_fraction=0.5
        )
        self.assertTrue(any("one melt" in f for f in result["findings"]))

    def test_an_unsampled_required_location_is_a_finding(self):
        result = assess_traceability(
            [record("TP-01", location="surface")],
            required_locations=["surface", "mid-thickness"],
        )
        self.assertTrue(
            any("through-thickness location" in f for f in result["findings"])
        )

    def test_empty_piece_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_traceability([])

    def test_out_of_range_heat_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_traceability([record()], max_single_heat_fraction=1.5)

    def test_per_piece_results_travel_with_the_assessment(self):
        result = assess_traceability([record("TP-01"), record("TP-02")])
        self.assertEqual(len(result["pieces"]), 2)


if __name__ == "__main__":
    unittest.main()
