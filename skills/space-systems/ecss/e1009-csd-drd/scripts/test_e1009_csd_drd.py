#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-09C Annex A CSD DRD validation.

Exercises scripts/e1009_csd_drd_logic.py (stdlib unittest, offline).
Contract: every defined coordinate frame carries a unique non-empty
identifier, a recognised frame type, and fully specified axes; each
frame-to-frame transformation references existing frames by ID, names
a valid rotation sequence, and provides exactly three angle and three
translation components; each parameter-table entry has a non-empty
name, a unit, and an optional frame reference that must resolve; the
DRD completeness check requires title, issue number, at least one
inertial frame, at least one body-fixed frame, at least one
transformation, and a non-empty parameter table; a rotation matrix
built from any valid Euler sequence is orthonormal and has unit
determinant; frame definitions are groupable by type; and a
transformation-path search returns a valid hop chain or an empty list
when no path exists.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1009_csd_drd_logic as csd  # noqa: E402


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_frame(frame_id="SC_BF", frame_type="body-fixed",
                origin="spacecraft centre of mass",
                x_axis="forward along thrust axis",
                y_axis="starboard lateral",
                z_axis="nadir-pointing",
                body_attachment="main_bus"):
    return {
        "frame_id": frame_id,
        "frame_type": frame_type,
        "origin": origin,
        "x_axis": x_axis,
        "y_axis": y_axis,
        "z_axis": z_axis,
        "body_attachment": body_attachment,
    }


def _make_transform(source, target, seq="ZYX",
                    angles=(0.0, 0.0, 0.0),
                    trans=(0.0, 0.0, 0.0)):
    return {
        "source_frame": source,
        "target_frame": target,
        "rotation_sequence": seq,
        "angles_deg": angles,
        "translation_m": trans,
    }


def _make_param(name="x_offset", value=0.05, unit="m", frame_id="SC_BF"):
    return {"name": name, "value": value, "unit": unit, "frame_id": frame_id}


def _minimal_valid_doc():
    """Minimal CSD that satisfies all validation checks."""
    return {
        "title": "Spacecraft Coordinate Systems Document",
        "issue": "1.0",
        "frames": [
            _make_frame(
                "J2000", "inertial",
                origin="Earth centre of mass",
                x_axis="vernal equinox direction",
                y_axis="ecliptic plane 90 deg from X",
                z_axis="celestial north pole",
                body_attachment=None,
            ),
            _make_frame("SC_BF", "body-fixed"),
        ],
        "transformations": [
            _make_transform("J2000", "SC_BF"),
        ],
        "parameters": [
            _make_param("x_offset", 0.05, "m", "SC_BF"),
        ],
    }


# ---------------------------------------------------------------------------
# Frame validation
# ---------------------------------------------------------------------------

class FrameValidationTest(unittest.TestCase):
    def test_valid_frame_has_no_errors(self):
        self.assertEqual(csd.validate_frame(_make_frame()), [])

    def test_empty_frame_id_is_caught(self):
        errors = csd.validate_frame(_make_frame(frame_id=""))
        self.assertTrue(any("frame_id" in e for e in errors))

    def test_unrecognised_frame_type_is_caught(self):
        errors = csd.validate_frame(_make_frame(frame_type="galactic-drift"))
        self.assertTrue(any("frame_type" in e for e in errors))

    def test_missing_origin_is_caught(self):
        errors = csd.validate_frame(_make_frame(origin=""))
        self.assertTrue(any("origin" in e for e in errors))

    def test_missing_x_axis_is_caught(self):
        errors = csd.validate_frame(_make_frame(x_axis=""))
        self.assertTrue(any("x_axis" in e for e in errors))

    def test_missing_y_axis_is_caught(self):
        errors = csd.validate_frame(_make_frame(y_axis=""))
        self.assertTrue(any("y_axis" in e for e in errors))


# ---------------------------------------------------------------------------
# Transformation validation
# ---------------------------------------------------------------------------

class TransformationValidationTest(unittest.TestCase):
    _FRAMES = {"J2000", "SC_BF"}

    def test_valid_transformation_has_no_errors(self):
        t = _make_transform("J2000", "SC_BF")
        self.assertEqual(csd.validate_transformation(t, self._FRAMES), [])

    def test_unknown_source_frame_is_caught(self):
        t = _make_transform("GHOST", "SC_BF")
        errors = csd.validate_transformation(t, self._FRAMES)
        self.assertTrue(any("source_frame" in e for e in errors))

    def test_unknown_target_frame_is_caught(self):
        t = _make_transform("J2000", "GHOST")
        errors = csd.validate_transformation(t, self._FRAMES)
        self.assertTrue(any("target_frame" in e for e in errors))

    def test_self_reference_is_caught(self):
        t = _make_transform("SC_BF", "SC_BF")
        errors = csd.validate_transformation(t, self._FRAMES)
        self.assertTrue(any("identical" in e for e in errors))

    def test_unrecognised_rotation_sequence_is_caught(self):
        t = _make_transform("J2000", "SC_BF", seq="ABC")
        errors = csd.validate_transformation(t, self._FRAMES)
        self.assertTrue(any("rotation_sequence" in e for e in errors))

    def test_wrong_angle_count_is_caught(self):
        t = _make_transform("J2000", "SC_BF", angles=(0.0, 0.0))
        errors = csd.validate_transformation(t, self._FRAMES)
        self.assertTrue(any("angles_deg" in e for e in errors))

    def test_wrong_translation_count_is_caught(self):
        t = _make_transform("J2000", "SC_BF", trans=(0.0, 0.0))
        errors = csd.validate_transformation(t, self._FRAMES)
        self.assertTrue(any("translation_m" in e for e in errors))


# ---------------------------------------------------------------------------
# Parameter validation
# ---------------------------------------------------------------------------

class ParameterValidationTest(unittest.TestCase):
    _FRAMES = {"SC_BF"}

    def test_valid_parameter_has_no_errors(self):
        self.assertEqual(csd.validate_parameter(_make_param(), self._FRAMES), [])

    def test_empty_param_name_is_caught(self):
        errors = csd.validate_parameter(_make_param(name=""), self._FRAMES)
        self.assertTrue(any("name" in e for e in errors))

    def test_missing_unit_is_caught(self):
        errors = csd.validate_parameter(_make_param(unit=""), self._FRAMES)
        self.assertTrue(any("unit" in e for e in errors))

    def test_unknown_frame_reference_is_caught(self):
        errors = csd.validate_parameter(
            _make_param(frame_id="GHOST_FRAME"), self._FRAMES
        )
        self.assertTrue(any("frame" in e for e in errors))


# ---------------------------------------------------------------------------
# DRD completeness
# ---------------------------------------------------------------------------

class DRDCompletenessTest(unittest.TestCase):
    def test_missing_inertial_frame_is_flagged(self):
        doc = _minimal_valid_doc()
        doc["frames"] = [_make_frame("SC_BF", "body-fixed")]
        findings = csd.check_drd_completeness(doc)
        self.assertTrue(any("inertial" in f for f in findings))

    def test_missing_body_fixed_frame_is_flagged(self):
        doc = _minimal_valid_doc()
        doc["frames"] = [
            _make_frame(
                "J2000", "inertial",
                origin="Earth CoM",
                x_axis="vernal equinox",
                y_axis="ecliptic 90deg",
                z_axis="north pole",
                body_attachment=None,
            )
        ]
        findings = csd.check_drd_completeness(doc)
        self.assertTrue(any("body-fixed" in f for f in findings))

    def test_empty_transformations_is_flagged(self):
        doc = _minimal_valid_doc()
        doc["transformations"] = []
        findings = csd.check_drd_completeness(doc)
        self.assertTrue(any("transformation" in f for f in findings))

    def test_empty_parameter_table_is_flagged(self):
        doc = _minimal_valid_doc()
        doc["parameters"] = []
        findings = csd.check_drd_completeness(doc)
        self.assertTrue(any("parameter" in f for f in findings))

    def test_missing_title_is_flagged(self):
        doc = _minimal_valid_doc()
        doc["title"] = ""
        findings = csd.check_drd_completeness(doc)
        self.assertTrue(any("title" in f for f in findings))

    def test_missing_issue_number_is_flagged(self):
        doc = _minimal_valid_doc()
        doc["issue"] = ""
        findings = csd.check_drd_completeness(doc)
        self.assertTrue(any("issue" in f for f in findings))


# ---------------------------------------------------------------------------
# Full CSD validation and compliance
# ---------------------------------------------------------------------------

class FullCSDValidationTest(unittest.TestCase):
    def test_minimal_valid_doc_is_compliant(self):
        findings = csd.validate_csd(_minimal_valid_doc())
        self.assertTrue(csd.is_compliant(findings))

    def test_duplicate_frame_id_is_flagged(self):
        doc = _minimal_valid_doc()
        doc["frames"].append(
            _make_frame(
                "SC_BF", "sensor",
                origin="sensor mount",
                x_axis="optical axis",
                y_axis="detector row",
                z_axis="detector normal",
                body_attachment="optical_bench",
            )
        )
        findings = csd.validate_csd(doc)
        self.assertTrue(any("DUPLICATE" in f for f in findings["frames"]))

    def test_duplicate_transformation_pair_is_flagged(self):
        doc = _minimal_valid_doc()
        doc["transformations"].append(_make_transform("J2000", "SC_BF"))
        findings = csd.validate_csd(doc)
        self.assertTrue(
            any("DUPLICATE" in f for f in findings["transformations"])
        )


# ---------------------------------------------------------------------------
# Rotation matrix
# ---------------------------------------------------------------------------

class RotationMatrixTest(unittest.TestCase):
    def test_zero_angles_give_identity(self):
        r = csd.build_rotation_matrix("ZYX", (0.0, 0.0, 0.0))
        for i in range(3):
            for j in range(3):
                expected = 1.0 if i == j else 0.0
                self.assertAlmostEqual(r[i][j], expected, places=12)

    def test_computed_matrix_is_orthonormal(self):
        r = csd.build_rotation_matrix("ZYX", (30.0, 20.0, 10.0))
        self.assertTrue(csd.check_orthonormality(r))

    def test_non_orthonormal_matrix_is_detected(self):
        bad = [[2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        self.assertFalse(csd.check_orthonormality(bad))

    def test_unrecognised_sequence_raises(self):
        with self.assertRaises(ValueError):
            csd.build_rotation_matrix("QQQ", (0.0, 0.0, 0.0))

    def test_wrong_angle_count_raises(self):
        with self.assertRaises(ValueError):
            csd.build_rotation_matrix("ZYX", (0.0, 0.0))

    def test_90deg_rotation_about_z(self):
        # ZYX with angles (90, 0, 0) applies Rz(90) only
        r = csd.build_rotation_matrix("ZYX", (90.0, 0.0, 0.0))
        self.assertAlmostEqual(r[0][0], 0.0, places=12)
        self.assertAlmostEqual(r[0][1], -1.0, places=12)
        self.assertAlmostEqual(r[1][0], 1.0, places=12)
        self.assertAlmostEqual(r[2][2], 1.0, places=12)
        self.assertTrue(csd.check_orthonormality(r))

    def test_all_valid_sequences_produce_orthonormal_matrices(self):
        for seq in sorted(csd.VALID_ROTATION_SEQUENCES):
            r = csd.build_rotation_matrix(seq, (15.0, 30.0, 45.0))
            self.assertTrue(
                csd.check_orthonormality(r),
                msg="sequence %s failed orthonormality check" % seq,
            )


# ---------------------------------------------------------------------------
# Frame categorization
# ---------------------------------------------------------------------------

class FrameCategorizationTest(unittest.TestCase):
    def test_groups_frames_by_type(self):
        frames = [
            {"frame_id": "J2000", "frame_type": "inertial"},
            {"frame_id": "SC_BF", "frame_type": "body-fixed"},
            {"frame_id": "ORB", "frame_type": "orbital"},
            {"frame_id": "SNS1", "frame_type": "sensor"},
        ]
        groups = csd.categorize_frames(frames)
        self.assertEqual(groups["inertial"], ["J2000"])
        self.assertEqual(groups["body-fixed"], ["SC_BF"])
        self.assertEqual(groups["orbital"], ["ORB"])
        self.assertEqual(groups["sensor"], ["SNS1"])

    def test_multiple_frames_of_same_type(self):
        frames = [
            {"frame_id": "SNS1", "frame_type": "sensor"},
            {"frame_id": "SNS2", "frame_type": "sensor"},
        ]
        groups = csd.categorize_frames(frames)
        self.assertIn("SNS1", groups["sensor"])
        self.assertIn("SNS2", groups["sensor"])
        self.assertEqual(len(groups["sensor"]), 2)


# ---------------------------------------------------------------------------
# Transformation path search
# ---------------------------------------------------------------------------

class TransformationPathTest(unittest.TestCase):
    def _transforms(self):
        return [
            _make_transform("J2000", "SC_BF"),
            _make_transform("SC_BF", "SNS1"),
        ]

    def test_direct_path_is_found(self):
        path = csd.find_transformation_path("J2000", "SC_BF", self._transforms())
        self.assertEqual(path, [("J2000", "SC_BF")])

    def test_indirect_path_is_found(self):
        path = csd.find_transformation_path("J2000", "SNS1", self._transforms())
        self.assertEqual(len(path), 2)
        self.assertEqual(path[0][0], "J2000")
        self.assertEqual(path[-1][1], "SNS1")

    def test_reverse_path_is_found(self):
        # Transformations are bidirectional
        path = csd.find_transformation_path("SNS1", "J2000", self._transforms())
        self.assertGreater(len(path), 0)
        self.assertEqual(path[0][0], "SNS1")
        self.assertEqual(path[-1][1], "J2000")

    def test_no_path_returns_empty_list(self):
        path = csd.find_transformation_path(
            "J2000", "ORPHAN", self._transforms()
        )
        self.assertEqual(path, [])

    def test_same_source_and_target_returns_empty_list(self):
        path = csd.find_transformation_path(
            "J2000", "J2000", self._transforms()
        )
        self.assertEqual(path, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
