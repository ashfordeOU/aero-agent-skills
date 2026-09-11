#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §5.3.2 standard notation.

Exercises scripts/e1009_notation_logic.py (stdlib unittest, offline).
Contract: frame labels must be uppercase alphanumeric starting with a
letter; rotation matrices must be orthogonal with determinant +1;
quaternions must carry unit norm; Euler-angle sequences must be
three distinct-adjacent-axis codes; annotated vectors must carry a frame
label; exchange records must supply frame, representation, and payload
(plus euler_sequence when representation is euler_angles); transformation
chains must be gap-free between consecutive steps.

Run: python3 test_e1009_notation.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1009_notation_logic as nl  # noqa: E402


# ---------------------------------------------------------------------------
# Frame label tests
# ---------------------------------------------------------------------------

class FrameLabelTest(unittest.TestCase):

    def test_uppercase_alpha_label_passes(self):
        self.assertTrue(nl.validate_frame_label("ECI")["ok"])

    def test_label_with_digits_and_underscore_passes(self):
        self.assertTrue(nl.validate_frame_label("BODY_1")["ok"])

    def test_lvlh_label_passes(self):
        self.assertTrue(nl.validate_frame_label("LVLH")["ok"])

    def test_empty_string_fails(self):
        r = nl.validate_frame_label("")
        self.assertFalse(r["ok"])
        self.assertIn("non-empty", r["reason"])

    def test_lowercase_label_fails(self):
        r = nl.validate_frame_label("eci")
        self.assertFalse(r["ok"])

    def test_label_starting_with_digit_fails(self):
        r = nl.validate_frame_label("1ECI")
        self.assertFalse(r["ok"])
        self.assertIn("letter", r["reason"])

    def test_hyphen_in_label_fails(self):
        r = nl.validate_frame_label("ECI-INERTIAL")
        self.assertFalse(r["ok"])
        self.assertIn("invalid character", r["reason"])

    def test_non_string_input_fails(self):
        r = nl.validate_frame_label(42)
        self.assertFalse(r["ok"])


# ---------------------------------------------------------------------------
# Rotation matrix tests
# ---------------------------------------------------------------------------

def _rot_z(theta):
    c, s = math.cos(theta), math.sin(theta)
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def _identity():
    return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


class RotationMatrixTest(unittest.TestCase):

    def test_identity_matrix_passes(self):
        self.assertTrue(nl.validate_rotation_matrix(_identity())["ok"])

    def test_45_degree_z_rotation_passes(self):
        self.assertTrue(nl.validate_rotation_matrix(_rot_z(math.pi / 4))["ok"])

    def test_180_degree_z_rotation_passes(self):
        self.assertTrue(nl.validate_rotation_matrix(_rot_z(math.pi))["ok"])

    def test_wrong_row_count_fails(self):
        r = nl.validate_rotation_matrix([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        self.assertFalse(r["ok"])
        self.assertIn("3 rows", r["reason"])

    def test_non_orthogonal_matrix_fails(self):
        bad = [[2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        r = nl.validate_rotation_matrix(bad)
        self.assertFalse(r["ok"])
        self.assertIn("orthogonal", r["reason"])

    def test_reflection_matrix_det_minus_one_fails(self):
        bad = [[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        r = nl.validate_rotation_matrix(bad)
        self.assertFalse(r["ok"])
        self.assertIn("determinant", r["reason"])

    def test_non_numeric_element_fails(self):
        bad = [[1.0, 0.0, "x"], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        r = nl.validate_rotation_matrix(bad)
        self.assertFalse(r["ok"])
        self.assertIn("numeric", r["reason"])

    def test_wrong_column_count_fails(self):
        bad = [[1.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        r = nl.validate_rotation_matrix(bad)
        self.assertFalse(r["ok"])


# ---------------------------------------------------------------------------
# Quaternion tests
# ---------------------------------------------------------------------------

class QuaternionTest(unittest.TestCase):

    def test_identity_quaternion_passes(self):
        self.assertTrue(nl.validate_quaternion([1.0, 0.0, 0.0, 0.0])["ok"])

    def test_non_trivial_unit_quaternion_passes(self):
        v = 1.0 / math.sqrt(2.0)
        self.assertTrue(nl.validate_quaternion([v, v, 0.0, 0.0])["ok"])

    def test_all_equal_components_unit_quaternion_passes(self):
        v = 0.5
        self.assertTrue(nl.validate_quaternion([v, v, v, v])["ok"])

    def test_unnormalised_quaternion_fails(self):
        r = nl.validate_quaternion([2.0, 0.0, 0.0, 0.0])
        self.assertFalse(r["ok"])
        self.assertIn("norm", r["reason"])

    def test_zero_quaternion_fails(self):
        r = nl.validate_quaternion([0.0, 0.0, 0.0, 0.0])
        self.assertFalse(r["ok"])

    def test_wrong_length_fails(self):
        r = nl.validate_quaternion([1.0, 0.0, 0.0])
        self.assertFalse(r["ok"])

    def test_non_numeric_element_fails(self):
        r = nl.validate_quaternion([1.0, 0.0, "a", 0.0])
        self.assertFalse(r["ok"])
        self.assertIn("numeric", r["reason"])

    def test_non_sequence_input_fails(self):
        r = nl.validate_quaternion("1000")
        self.assertFalse(r["ok"])


# ---------------------------------------------------------------------------
# Euler sequence tests
# ---------------------------------------------------------------------------

class EulerSequenceTest(unittest.TestCase):

    def test_313_sequence_passes(self):
        self.assertTrue(nl.validate_euler_sequence("313")["ok"])

    def test_321_sequence_passes(self):
        self.assertTrue(nl.validate_euler_sequence("321")["ok"])

    def test_123_sequence_passes(self):
        self.assertTrue(nl.validate_euler_sequence("123")["ok"])

    def test_212_sequence_passes(self):
        self.assertTrue(nl.validate_euler_sequence("212")["ok"])

    def test_adjacent_identical_first_two_fails(self):
        r = nl.validate_euler_sequence("113")
        self.assertFalse(r["ok"])
        self.assertIn("consecutive", r["reason"])

    def test_adjacent_identical_last_two_fails(self):
        r = nl.validate_euler_sequence("311")
        self.assertFalse(r["ok"])
        self.assertIn("consecutive", r["reason"])

    def test_too_short_fails(self):
        r = nl.validate_euler_sequence("31")
        self.assertFalse(r["ok"])
        self.assertIn("3 characters", r["reason"])

    def test_too_long_fails(self):
        r = nl.validate_euler_sequence("3131")
        self.assertFalse(r["ok"])

    def test_invalid_axis_digit_fails(self):
        r = nl.validate_euler_sequence("304")
        self.assertFalse(r["ok"])
        self.assertIn("axis index", r["reason"])

    def test_non_string_input_fails(self):
        r = nl.validate_euler_sequence(313)
        self.assertFalse(r["ok"])
        self.assertIn("string", r["reason"])


# ---------------------------------------------------------------------------
# Annotated vector tests
# ---------------------------------------------------------------------------

class VectorAnnotationTest(unittest.TestCase):

    def test_valid_annotated_vector_passes(self):
        v = {"frame": "ECI", "components": [1.0, 0.0, 0.0]}
        self.assertTrue(nl.validate_vector_annotation(v)["ok"])

    def test_missing_frame_fails(self):
        v = {"components": [1.0, 0.0, 0.0]}
        r = nl.validate_vector_annotation(v)
        self.assertFalse(r["ok"])
        self.assertIn("frame", r["reason"])

    def test_missing_components_fails(self):
        v = {"frame": "ECI"}
        r = nl.validate_vector_annotation(v)
        self.assertFalse(r["ok"])
        self.assertIn("components", r["reason"])

    def test_wrong_component_count_fails(self):
        v = {"frame": "ECI", "components": [1.0, 0.0]}
        r = nl.validate_vector_annotation(v)
        self.assertFalse(r["ok"])

    def test_invalid_frame_label_propagates(self):
        v = {"frame": "eci", "components": [1.0, 0.0, 0.0]}
        r = nl.validate_vector_annotation(v)
        self.assertFalse(r["ok"])
        self.assertIn("frame", r["reason"])

    def test_non_dict_input_fails(self):
        r = nl.validate_vector_annotation([1.0, 0.0, 0.0])
        self.assertFalse(r["ok"])


# ---------------------------------------------------------------------------
# Exchange record tests
# ---------------------------------------------------------------------------

class ExchangeRecordTest(unittest.TestCase):

    def test_valid_matrix_record_passes(self):
        record = {
            "frame": "BODY",
            "representation": "matrix",
            "payload": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        }
        self.assertEqual(nl.validate_exchange_record(record), [])

    def test_valid_quaternion_record_passes(self):
        record = {
            "frame": "ECI",
            "representation": "quaternion",
            "payload": [1.0, 0.0, 0.0, 0.0],
        }
        self.assertEqual(nl.validate_exchange_record(record), [])

    def test_valid_euler_angles_record_passes(self):
        record = {
            "frame": "LVLH",
            "representation": "euler_angles",
            "euler_sequence": "321",
            "payload": [0.1, 0.2, 0.3],
        }
        self.assertEqual(nl.validate_exchange_record(record), [])

    def test_missing_frame_is_reported(self):
        record = {"representation": "matrix", "payload": []}
        findings = nl.validate_exchange_record(record)
        self.assertTrue(any("frame" in f for f in findings))

    def test_missing_representation_is_reported(self):
        record = {"frame": "ECI", "payload": []}
        findings = nl.validate_exchange_record(record)
        self.assertTrue(any("representation" in f for f in findings))

    def test_unknown_representation_is_reported(self):
        record = {"frame": "ECI", "representation": "axis_angle", "payload": []}
        findings = nl.validate_exchange_record(record)
        self.assertTrue(any("representation" in f for f in findings))

    def test_euler_angles_missing_sequence_is_reported(self):
        record = {
            "frame": "ECI",
            "representation": "euler_angles",
            "payload": [0.0, 0.0, 0.0],
        }
        findings = nl.validate_exchange_record(record)
        self.assertTrue(any("euler_sequence" in f for f in findings))

    def test_euler_angles_bad_sequence_is_reported(self):
        record = {
            "frame": "ECI",
            "representation": "euler_angles",
            "euler_sequence": "113",
            "payload": [0.0, 0.0, 0.0],
        }
        findings = nl.validate_exchange_record(record)
        self.assertTrue(any("euler_sequence" in f for f in findings))

    def test_missing_payload_is_reported(self):
        record = {"frame": "ECI", "representation": "quaternion"}
        findings = nl.validate_exchange_record(record)
        self.assertTrue(any("payload" in f for f in findings))

    def test_none_payload_is_reported(self):
        record = {"frame": "ECI", "representation": "quaternion", "payload": None}
        findings = nl.validate_exchange_record(record)
        self.assertTrue(any("payload" in f for f in findings))

    def test_multiple_missing_fields_each_reported(self):
        findings = nl.validate_exchange_record({})
        self.assertGreaterEqual(len(findings), 3)


# ---------------------------------------------------------------------------
# Transformation chain tests
# ---------------------------------------------------------------------------

class TransformationChainTest(unittest.TestCase):

    def test_single_step_chain_passes(self):
        chain = [{"from_frame": "ECI", "to_frame": "BODY"}]
        self.assertEqual(nl.check_transformation_chain(chain), [])

    def test_continuous_two_step_chain_passes(self):
        chain = [
            {"from_frame": "ECI", "to_frame": "LVLH"},
            {"from_frame": "LVLH", "to_frame": "BODY"},
        ]
        self.assertEqual(nl.check_transformation_chain(chain), [])

    def test_three_step_chain_passes(self):
        chain = [
            {"from_frame": "ECI", "to_frame": "LVLH"},
            {"from_frame": "LVLH", "to_frame": "BODY"},
            {"from_frame": "BODY", "to_frame": "SENSOR"},
        ]
        self.assertEqual(nl.check_transformation_chain(chain), [])

    def test_gap_between_steps_is_reported(self):
        chain = [
            {"from_frame": "ECI", "to_frame": "LVLH"},
            {"from_frame": "BODY", "to_frame": "SENSOR"},
        ]
        findings = nl.check_transformation_chain(chain)
        self.assertGreater(len(findings), 0)
        self.assertTrue(any("break" in f for f in findings))

    def test_empty_chain_is_reported(self):
        findings = nl.check_transformation_chain([])
        self.assertGreater(len(findings), 0)

    def test_missing_to_frame_key_is_reported(self):
        chain = [{"from_frame": "ECI"}]
        findings = nl.check_transformation_chain(chain)
        self.assertGreater(len(findings), 0)
        self.assertTrue(any("to_frame" in f for f in findings))

    def test_missing_from_frame_key_is_reported(self):
        chain = [{"to_frame": "BODY"}]
        findings = nl.check_transformation_chain(chain)
        self.assertGreater(len(findings), 0)
        self.assertTrue(any("from_frame" in f for f in findings))

    def test_non_list_input_is_reported(self):
        findings = nl.check_transformation_chain("ECI->BODY")
        self.assertGreater(len(findings), 0)


if __name__ == "__main__":
    unittest.main()
