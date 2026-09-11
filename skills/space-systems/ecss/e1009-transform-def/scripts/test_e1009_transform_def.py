"""
test_e1009_transform_def.py

Offline stdlib unittest for e1009_transform_def_logic.
Run: python3 test_e1009_transform_def.py
Must print OK with 10+ tests passing.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1009_transform_def_logic import (
    CONVENTION_DCM,
    CONVENTION_ACTIVE,
    CONVENTION_PASSIVE,
    KNOWN_CONVENTIONS,
    TransformEntry,
    TransformValidationResult,
    parse_transform_entry,
    check_verbal_description,
    check_graphical_reference,
    check_parent_frame_defined,
    check_orthogonality,
    check_precision_consistency,
    check_matrix_convention,
    validate_transform_completeness,
    audit_transform_set,
    _identity_3,
    _determinant_3x3,
    _precision_level,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rot_z(deg: float):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def _rot_x(deg: float):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]


def _rot_y(deg: float):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def _make_entry(
    name="T_body_ref",
    parent_frame="REFERENCE",
    child_frame="BODY",
    verbal="Rotation from REFERENCE to BODY frame about Z-axis.",
    matrix=None,
    convention=CONVENTION_DCM,
    graphical_reference="fig-3.2",
):
    if matrix is None:
        matrix = _rot_z(30.0)
    return TransformEntry(
        name=name,
        parent_frame=parent_frame,
        child_frame=child_frame,
        verbal_description=verbal,
        matrix=matrix,
        convention=convention,
        graphical_reference=graphical_reference,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParseTransformEntry(unittest.TestCase):

    def test_parse_valid_entry_succeeds(self):
        raw = {
            "name": "T1",
            "parent_frame": "ECI",
            "child_frame": "BODY",
            "verbal_description": "Rotation from ECI to BODY frame.",
            "matrix": _rot_z(45.0),
            "convention": "DCM",
            "graphical_reference": "fig-1",
        }
        entry = parse_transform_entry(raw)
        self.assertEqual(entry.name, "T1")
        self.assertEqual(entry.parent_frame, "ECI")
        self.assertEqual(entry.convention, "DCM")
        self.assertEqual(entry.graphical_reference, "fig-1")

    def test_parse_missing_required_field_raises(self):
        raw = {"name": "T1", "parent_frame": "ECI"}
        with self.assertRaises(ValueError):
            parse_transform_entry(raw)

    def test_parse_unknown_convention_raises(self):
        raw = {
            "name": "T1",
            "parent_frame": "ECI",
            "child_frame": "BODY",
            "verbal_description": "Rotation from ECI frame.",
            "matrix": _rot_z(0.0),
            "convention": "EULER",
        }
        with self.assertRaises(ValueError):
            parse_transform_entry(raw)

    def test_parse_non_square_matrix_raises(self):
        raw = {
            "name": "T1",
            "parent_frame": "ECI",
            "child_frame": "BODY",
            "verbal_description": "Rotation from ECI frame.",
            "matrix": [[1, 0], [0, 1]],
            "convention": "DCM",
        }
        with self.assertRaises(ValueError):
            parse_transform_entry(raw)

    def test_parse_normalises_convention_case(self):
        raw = {
            "name": "T1",
            "parent_frame": "ECI",
            "child_frame": "BODY",
            "verbal_description": "Rotation from ECI frame.",
            "matrix": _rot_x(0.0),
            "convention": "dcm",
        }
        entry = parse_transform_entry(raw)
        self.assertEqual(entry.convention, "DCM")

    def test_parse_non_numeric_matrix_entry_raises(self):
        raw = {
            "name": "T1",
            "parent_frame": "ECI",
            "child_frame": "BODY",
            "verbal_description": "Rotation from ECI frame.",
            "matrix": [["a", 0, 0], [0, 1, 0], [0, 0, 1]],
            "convention": "DCM",
        }
        with self.assertRaises(ValueError):
            parse_transform_entry(raw)


class TestVerbalDescription(unittest.TestCase):

    def test_valid_verbal_passes(self):
        entry = _make_entry()
        self.assertIsNone(check_verbal_description(entry))

    def test_missing_parent_frame_reference_fails(self):
        entry = _make_entry(verbal="A rotation to the child frame only.")
        err = check_verbal_description(entry)
        self.assertIsNotNone(err)
        self.assertIn("parent frame", err)

    def test_too_short_verbal_fails(self):
        entry = _make_entry(verbal="Short", parent_frame="REFERENCE")
        err = check_verbal_description(entry)
        self.assertIsNotNone(err)
        self.assertIn("too short", err)

    def test_parent_frame_in_verbal_case_insensitive(self):
        entry = _make_entry(
            parent_frame="ECI",
            verbal="Rotation from eci inertial frame to BODY.",
        )
        self.assertIsNone(check_verbal_description(entry))


class TestGraphicalReference(unittest.TestCase):

    def test_present_graphical_reference_passes(self):
        entry = _make_entry(graphical_reference="fig-3.2")
        self.assertIsNone(check_graphical_reference(entry))

    def test_missing_graphical_reference_fails(self):
        entry = _make_entry(graphical_reference=None)
        err = check_graphical_reference(entry)
        self.assertIsNotNone(err)
        self.assertIn("graphical_reference", err)


class TestParentFrameDefined(unittest.TestCase):

    def test_parent_frame_in_known_set_passes(self):
        entry = _make_entry(parent_frame="ECI")
        self.assertIsNone(check_parent_frame_defined(entry, ["ECI", "BODY", "LVLH"]))

    def test_parent_frame_not_in_known_set_fails(self):
        entry = _make_entry(parent_frame="MYSTERY")
        err = check_parent_frame_defined(entry, ["ECI", "BODY"])
        self.assertIsNotNone(err)
        self.assertIn("MYSTERY", err)


class TestOrthogonality(unittest.TestCase):

    def test_identity_matrix_passes(self):
        entry = _make_entry(matrix=_identity_3())
        self.assertIsNone(check_orthogonality(entry))

    def test_90_degree_rotation_z_passes(self):
        entry = _make_entry(matrix=_rot_z(90.0))
        self.assertIsNone(check_orthogonality(entry))

    def test_arbitrary_rotation_x_passes(self):
        entry = _make_entry(matrix=_rot_x(37.5))
        self.assertIsNone(check_orthogonality(entry))

    def test_scale_matrix_fails_orthogonality(self):
        bad = [[2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        entry = _make_entry(matrix=bad)
        err = check_orthogonality(entry)
        self.assertIsNotNone(err)
        self.assertIn("orthogonal", err)

    def test_reflection_fails_determinant_check(self):
        reflection = [[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        entry = _make_entry(matrix=reflection)
        err = check_orthogonality(entry)
        self.assertIsNotNone(err)
        self.assertIn("determinant", err)


class TestPrecisionConsistency(unittest.TestCase):

    def test_uniform_float_precision_passes(self):
        e1 = _make_entry(name="T1", matrix=_rot_z(30.0))
        e2 = _make_entry(name="T2", matrix=_rot_x(45.0))
        errors = check_precision_consistency([e1, e2])
        self.assertEqual(errors, [])

    def test_integer_matrix_versus_float_matrix_flagged(self):
        int_matrix = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        float_matrix = _rot_z(30.0)
        e1 = _make_entry(name="T_int", matrix=int_matrix)
        e2 = _make_entry(name="T_float", matrix=float_matrix)
        errors = check_precision_consistency([e1, e2])
        flagged = [err.split("]")[0].lstrip("[") for err in errors]
        self.assertIn("T_int", flagged)

    def test_empty_list_returns_no_errors(self):
        self.assertEqual(check_precision_consistency([]), [])

    def test_single_entry_returns_no_errors(self):
        e = _make_entry(matrix=_rot_y(20.0))
        self.assertEqual(check_precision_consistency([e]), [])


class TestConventionCheck(unittest.TestCase):

    def test_matching_convention_passes(self):
        entry = _make_entry(convention=CONVENTION_DCM)
        self.assertIsNone(check_matrix_convention(entry, CONVENTION_DCM))

    def test_mismatched_convention_fails(self):
        entry = _make_entry(convention=CONVENTION_ACTIVE)
        err = check_matrix_convention(entry, CONVENTION_DCM)
        self.assertIsNotNone(err)
        self.assertIn("ACTIVE", err)

    def test_passive_convention_accepted(self):
        entry = _make_entry(convention=CONVENTION_PASSIVE)
        self.assertIsNone(check_matrix_convention(entry, CONVENTION_PASSIVE))

    def test_invalid_expected_convention_raises(self):
        entry = _make_entry()
        with self.assertRaises(ValueError):
            check_matrix_convention(entry, "QUATERNION")


class TestValidateTransformCompleteness(unittest.TestCase):

    def test_fully_complete_entry_has_no_errors(self):
        entry = _make_entry()
        errors = validate_transform_completeness(entry)
        self.assertEqual(errors, [])

    def test_missing_graphical_reference_is_reported(self):
        entry = _make_entry(graphical_reference=None)
        errors = validate_transform_completeness(entry)
        self.assertTrue(any("graphical_reference" in e for e in errors))


class TestAuditTransformSet(unittest.TestCase):

    def test_compliant_two_entry_set_passes(self):
        frames = ["ECI", "BODY", "LVLH"]
        e1 = _make_entry(
            name="T_eci_body",
            parent_frame="ECI",
            child_frame="BODY",
            verbal="Rotation from ECI inertial frame to BODY.",
            matrix=_rot_z(30.0),
            graphical_reference="fig-2.1",
        )
        e2 = _make_entry(
            name="T_eci_lvlh",
            parent_frame="ECI",
            child_frame="LVLH",
            verbal="Rotation from ECI frame to LVLH orbit frame.",
            matrix=_rot_x(15.0),
            graphical_reference="fig-2.2",
        )
        result = audit_transform_set([e1, e2], frames, CONVENTION_DCM)
        self.assertTrue(result.is_compliant())
        self.assertEqual(result.error_count(), 0)

    def test_undefined_parent_frame_produces_finding(self):
        e = _make_entry(
            parent_frame="GHOST_FRAME",
            verbal="Rotation from GHOST_FRAME to BODY.",
        )
        result = audit_transform_set([e], ["ECI", "BODY"], CONVENTION_DCM)
        self.assertFalse(result.is_compliant())
        checks = [f["check"] for f in result.findings]
        self.assertIn("parent_frame", checks)

    def test_wrong_convention_produces_finding(self):
        e = _make_entry(convention=CONVENTION_ACTIVE)
        result = audit_transform_set([e], ["REFERENCE", "BODY"], CONVENTION_DCM)
        self.assertFalse(result.is_compliant())
        checks = [f["check"] for f in result.findings]
        self.assertIn("convention", checks)

    def test_missing_graphical_reference_completeness_finding(self):
        e = _make_entry(graphical_reference=None)
        result = audit_transform_set([e], ["REFERENCE", "BODY"], CONVENTION_DCM)
        checks = [f["check"] for f in result.findings]
        self.assertIn("completeness", checks)


class TestLinearAlgebraHelpers(unittest.TestCase):

    def test_identity_determinant_is_one(self):
        self.assertAlmostEqual(_determinant_3x3(_identity_3()), 1.0)

    def test_diagonal_matrix_determinant(self):
        m = [[2.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 4.0]]
        self.assertAlmostEqual(_determinant_3x3(m), 24.0)

    def test_identity_is_3x3(self):
        I = _identity_3()
        self.assertEqual(len(I), 3)
        self.assertTrue(all(len(row) == 3 for row in I))

    def test_precision_level_boundaries(self):
        self.assertEqual(_precision_level(0), "LOW")
        self.assertEqual(_precision_level(2), "LOW")
        self.assertEqual(_precision_level(3), "MEDIUM")
        self.assertEqual(_precision_level(6), "MEDIUM")
        self.assertEqual(_precision_level(7), "HIGH")
        self.assertEqual(_precision_level(15), "HIGH")


if __name__ == "__main__":
    unittest.main()
