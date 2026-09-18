"""Contract tests for the build-file and job control logic."""

import copy
import math
import unittest

from q7080_build_file_and_job_control_logic import (
    DIGEST_LENGTH,
    angle_difference_deg,
    assess_build_job,
    check_build_file_identity,
    check_orientation,
    check_revision_binding,
    clearance_mm,
    footprint_box,
    footprint_extent,
    nest_clearance_findings,
    platform_violation,
    validate_envelope,
    validate_part,
)

ENVELOPE = (250.0, 250.0, 300.0)
DIGEST = "ab" * 32
APPROVED_SETS = ["PS-TI64-030", "PS-TI64-060"]
RELEASED = {"PN-100": "C", "PN-200": "A"}
ORIENTATIONS = {"PN-100": (0.0, 0.0), "PN-200": (15.0, 90.0)}


def part(identifier, number, revision, bbox, position, rotation=0.0, orientation=(0.0, 0.0)):
    return {
        "id": identifier,
        "part_number": number,
        "design_revision": revision,
        "bbox_mm": list(bbox),
        "position_mm": list(position),
        "platform_rotation_deg": rotation,
        "orientation_deg": None if orientation is None else list(orientation),
    }


def nest():
    return [
        part("n1", "PN-100", "C", (60.0, 40.0, 80.0), (60.0, 60.0)),
        part("n2", "PN-200", "A", (50.0, 50.0, 120.0), (160.0, 60.0), 90.0, (15.0, 90.0)),
        part("n3", "PN-100", "C", (60.0, 40.0, 80.0), (60.0, 160.0)),
    ]


def job():
    return {
        "build_file_version": "BF-2026-014",
        "build_file_digest": DIGEST,
        "parameter_set_id": "PS-TI64-030",
    }


def spec(parts=None, the_job=None):
    return {
        "job": job() if the_job is None else the_job,
        "parts": nest() if parts is None else parts,
        "envelope_mm": ENVELOPE,
        "released_index": dict(RELEASED),
        "approved_orientations": copy.deepcopy(ORIENTATIONS),
        "approved_parameter_sets": list(APPROVED_SETS),
        "minimum_clearance_mm": 5.0,
        "edge_margin_mm": 5.0,
        "orientation_tolerance_deg": 1.0,
    }


class ValidationTests(unittest.TestCase):
    def test_envelope_returned_as_floats(self):
        self.assertEqual(validate_envelope((250, 250, 300)), (250.0, 250.0, 300.0))

    def test_zero_envelope_axis_rejected(self):
        with self.assertRaises(ValueError):
            validate_envelope((250.0, 0.0, 300.0))

    def test_malformed_envelope_rejected(self):
        with self.assertRaises(ValueError):
            validate_envelope((250.0, 250.0))

    def test_part_record_normalised(self):
        record = validate_part(nest()[0])
        self.assertEqual(record["part_number"], "PN-100")
        self.assertAlmostEqual(record["bbox_mm"][2], 80.0, places=9)

    def test_part_without_revision_rejected(self):
        broken = nest()[0]
        del broken["design_revision"]
        with self.assertRaises(ValueError):
            validate_part(broken)

    def test_negative_bbox_axis_rejected(self):
        with self.assertRaises(ValueError):
            validate_part(part("n9", "PN-100", "C", (60.0, -40.0, 80.0), (60.0, 60.0)))

    def test_non_finite_rotation_rejected(self):
        with self.assertRaises(ValueError):
            validate_part(part("n9", "PN-100", "C", (60.0, 40.0, 80.0), (60.0, 60.0),
                               float("inf")))


class FootprintTests(unittest.TestCase):
    def test_unrotated_footprint_is_the_bbox(self):
        width, depth = footprint_extent((60.0, 40.0, 80.0), 0.0)
        self.assertAlmostEqual(width, 60.0, places=9)
        self.assertAlmostEqual(depth, 40.0, places=9)

    def test_quarter_turn_swaps_the_axes(self):
        width, depth = footprint_extent((60.0, 40.0, 80.0), 90.0)
        self.assertAlmostEqual(width, 40.0, places=9)
        self.assertAlmostEqual(depth, 60.0, places=9)

    def test_diagonal_rotation_grows_both_axes(self):
        width, depth = footprint_extent((60.0, 40.0, 80.0), 45.0)
        self.assertAlmostEqual(width, 100.0 / math.sqrt(2.0), places=9)
        self.assertAlmostEqual(depth, 100.0 / math.sqrt(2.0), places=9)

    def test_footprint_box_is_centred_on_the_position(self):
        xmin, xmax, ymin, ymax = footprint_box(nest()[0])
        self.assertAlmostEqual(xmin, 30.0, places=9)
        self.assertAlmostEqual(xmax, 90.0, places=9)
        self.assertAlmostEqual(ymin, 40.0, places=9)
        self.assertAlmostEqual(ymax, 80.0, places=9)


class PlatformTests(unittest.TestCase):
    def test_nested_part_is_inside_the_platform(self):
        self.assertIsNone(platform_violation(nest()[0], ENVELOPE, 5.0))

    def test_part_over_the_platform_edge_reported(self):
        stray = part("n9", "PN-100", "C", (60.0, 40.0, 80.0), (20.0, 60.0))
        self.assertEqual(platform_violation(stray, ENVELOPE, 5.0)["reason"], "outside-platform")

    def test_part_taller_than_the_envelope_reported(self):
        tall = part("n9", "PN-100", "C", (60.0, 40.0, 400.0), (60.0, 60.0))
        self.assertEqual(
            platform_violation(tall, ENVELOPE, 5.0)["reason"], "above-vertical-envelope"
        )

    def test_negative_edge_margin_rejected(self):
        with self.assertRaises(ValueError):
            platform_violation(nest()[0], ENVELOPE, -1.0)


class ClearanceTests(unittest.TestCase):
    def test_separated_parts_report_the_gap(self):
        parts = nest()
        self.assertAlmostEqual(clearance_mm(parts[0], parts[1]), 45.0, places=9)

    def test_diagonally_separated_parts_use_the_plane_distance(self):
        parts = nest()
        self.assertAlmostEqual(
            clearance_mm(parts[1], parts[2]), math.hypot(45.0, 55.0), places=9
        )

    def test_touching_parts_report_zero(self):
        a = part("a", "PN-100", "C", (60.0, 40.0, 80.0), (60.0, 60.0))
        b = part("b", "PN-100", "C", (60.0, 40.0, 80.0), (60.0, 100.0))
        self.assertAlmostEqual(clearance_mm(a, b), 0.0, places=9)

    def test_overlapping_parts_report_a_negative_gap(self):
        a = part("a", "PN-100", "C", (60.0, 40.0, 80.0), (60.0, 60.0))
        b = part("b", "PN-100", "C", (60.0, 40.0, 80.0), (60.0, 70.0))
        self.assertAlmostEqual(clearance_mm(a, b), -30.0, places=9)

    def test_compliant_nest_has_no_clearance_findings(self):
        self.assertEqual(nest_clearance_findings(nest(), 5.0), [])

    def test_gap_exactly_at_the_minimum_is_accepted(self):
        parts = nest()
        parts[2]["position_mm"] = [60.0, 105.0]
        self.assertAlmostEqual(clearance_mm(parts[0], parts[2]), 5.0, places=9)
        self.assertEqual(nest_clearance_findings(parts, 5.0), [])

    def test_gap_below_the_minimum_is_a_finding(self):
        parts = nest()
        parts[2]["position_mm"] = [60.0, 100.0]
        findings = nest_clearance_findings(parts, 5.0)
        self.assertEqual(findings[0]["reason"], "below-minimum-clearance")

    def test_overlap_is_named_as_an_overlap(self):
        parts = nest()
        parts[2]["position_mm"] = [60.0, 70.0]
        findings = nest_clearance_findings(parts, 5.0)
        self.assertEqual(findings[0]["reason"], "overlap")

    def test_negative_minimum_clearance_rejected(self):
        with self.assertRaises(ValueError):
            nest_clearance_findings(nest(), -1.0)


class BuildFileIdentityTests(unittest.TestCase):
    def test_clean_job_has_no_findings(self):
        self.assertEqual(check_build_file_identity(job(), APPROVED_SETS), [])

    def test_missing_version_reported(self):
        broken = job()
        broken["build_file_version"] = ""
        self.assertEqual(
            check_build_file_identity(broken, APPROVED_SETS)[0]["reason"],
            "build-file-version-missing",
        )

    def test_short_digest_reported(self):
        broken = job()
        broken["build_file_digest"] = "ab" * 8
        self.assertTrue(
            any("digest" in f["reason"] for f in check_build_file_identity(broken, APPROVED_SETS))
        )

    def test_non_hex_digest_reported(self):
        broken = job()
        broken["build_file_digest"] = "z" * DIGEST_LENGTH
        self.assertTrue(
            any("digest" in f["reason"] for f in check_build_file_identity(broken, APPROVED_SETS))
        )

    def test_unapproved_parameter_set_reported(self):
        broken = job()
        broken["parameter_set_id"] = "PS-EXPERIMENT-9"
        self.assertEqual(
            check_build_file_identity(broken, APPROVED_SETS)[0]["reason"],
            "parameter-set-not-approved",
        )

    def test_empty_approved_set_list_rejected(self):
        with self.assertRaises(ValueError):
            check_build_file_identity(job(), [])


class RevisionBindingTests(unittest.TestCase):
    def test_bound_nest_has_no_findings(self):
        self.assertEqual(check_revision_binding(nest(), RELEASED), [])

    def test_superseded_revision_reported(self):
        parts = nest()
        parts[0]["design_revision"] = "B"
        finding = check_revision_binding(parts, RELEASED)[0]
        self.assertEqual(finding["reason"], "revision-mismatch")
        self.assertEqual(finding["released"], "C")

    def test_part_absent_from_the_index_reported(self):
        parts = nest()
        parts[1]["part_number"] = "PN-999"
        self.assertEqual(
            check_revision_binding(parts, RELEASED)[0]["reason"], "not-in-released-index"
        )

    def test_empty_index_rejected(self):
        with self.assertRaises(ValueError):
            check_revision_binding(nest(), {})


class OrientationTests(unittest.TestCase):
    def test_wrapped_angles_compare_by_the_short_way(self):
        self.assertAlmostEqual(angle_difference_deg(359.0, 1.0), 2.0, places=9)

    def test_identical_angles_differ_by_zero(self):
        self.assertAlmostEqual(angle_difference_deg(90.0, 90.0), 0.0, places=9)

    def test_approved_nest_has_no_orientation_findings(self):
        self.assertEqual(check_orientation(nest(), ORIENTATIONS, 1.0), [])

    def test_unrecorded_orientation_reported(self):
        parts = nest()
        parts[0]["orientation_deg"] = None
        self.assertEqual(
            check_orientation(parts, ORIENTATIONS, 1.0)[0]["reason"], "orientation-unrecorded"
        )

    def test_orientation_off_approved_reported(self):
        parts = nest()
        parts[1]["orientation_deg"] = [18.0, 90.0]
        finding = check_orientation(parts, ORIENTATIONS, 1.0)[0]
        self.assertEqual(finding["reason"], "orientation-off-approved")
        self.assertEqual(finding["axis"], "tilt")

    def test_orientation_exactly_at_tolerance_accepted(self):
        parts = nest()
        parts[1]["orientation_deg"] = [16.0, 90.0]
        self.assertEqual(check_orientation(parts, ORIENTATIONS, 1.0), [])

    def test_part_without_an_approved_orientation_reported(self):
        parts = nest()
        parts[0]["part_number"] = "PN-300"
        self.assertEqual(
            check_orientation(parts, ORIENTATIONS, 1.0)[0]["reason"], "no-approved-orientation"
        )

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            check_orientation(nest(), ORIENTATIONS, -1.0)


class AssessmentTests(unittest.TestCase):
    def test_clean_job_is_released(self):
        result = assess_build_job(spec())
        self.assertEqual(result["verdict"], "release")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["part_count"], 3)

    def test_revision_break_holds_the_job(self):
        parts = nest()
        parts[2]["design_revision"] = "B"
        result = assess_build_job(spec(parts=parts))
        self.assertEqual(result["verdict"], "hold")

    def test_nest_overlap_holds_the_job(self):
        parts = nest()
        parts[2]["position_mm"] = [60.0, 70.0]
        result = assess_build_job(spec(parts=parts))
        self.assertEqual(result["verdict"], "hold")
        self.assertTrue(any(f.get("reason") == "overlap" for f in result["findings"]))

    def test_duplicate_part_id_rejected(self):
        parts = nest()
        parts[2]["id"] = "n1"
        with self.assertRaises(ValueError):
            assess_build_job(spec(parts=parts))

    def test_empty_nest_rejected(self):
        with self.assertRaises(ValueError):
            assess_build_job(spec(parts=[]))

    def test_missing_spec_key_rejected(self):
        broken = spec()
        del broken["released_index"]
        with self.assertRaises(ValueError):
            assess_build_job(broken)


if __name__ == "__main__":
    unittest.main(verbosity=1)
