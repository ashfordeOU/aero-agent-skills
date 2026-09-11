"""
Stdlib unittest for e1009_mech_frames_logic.py.
Offline, deterministic. Run: python3 test_e1009_mech_frames.py
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from e1009_mech_frames_logic import (
    validate_dcm,
    validate_frame,
    validate_alignment,
    assess_frame_set,
    check_frame_fields,
    check_frame_type,
    check_frame_parent,
    detect_parent_cycle,
    ORTHO_TOL,
)

# --- shared fixtures ---

ID3 = [[1.0, 0.0, 0.0],
       [0.0, 1.0, 0.0],
       [0.0, 0.0, 1.0]]

# 90° rotation about z-axis
ROT_Z90 = [[0.0, -1.0, 0.0],
           [1.0,  0.0, 0.0],
           [0.0,  0.0, 1.0]]

# reflection (det = -1): negate the z row of ID3
REFLECT = [[1.0, 0.0,  0.0],
           [0.0, 1.0,  0.0],
           [0.0, 0.0, -1.0]]

# badly non-orthogonal
NOT_ORTHO = [[2.0, 0.0, 0.0],
             [0.0, 1.0, 0.0],
             [0.0, 0.0, 1.0]]

SPACECRAFT_FRAME = {
    "name": "SCF",
    "type": "spacecraft",
    "parent": None,
    "origin": [0.0, 0.0, 0.0],
    "dcm": ID3,
}

EQUIPMENT_FRAME = {
    "name": "EQ1",
    "type": "equipment",
    "parent": "SCF",
    "origin": [1.0, 0.0, 0.5],
    "dcm": ROT_Z90,
}

SENSOR_FRAME = {
    "name": "ST1",
    "type": "sensor",
    "parent": "SCF",
    "origin": [0.5, 0.5, 0.0],
    "dcm": ID3,
}

ALIGNMENT_EQ1 = {
    "frame_name": "EQ1",
    "nominal_dcm": ROT_Z90,
    "measurement_status": "measured",
    "measured_dcm": ROT_Z90,
}

ALIGNMENT_ST1 = {
    "frame_name": "ST1",
    "nominal_dcm": ID3,
    "measurement_status": "nominal",
}


class TestDCMValidation(unittest.TestCase):

    def test_identity_passes(self):
        errs = validate_dcm(ID3)
        self.assertEqual(errs, [], f"Identity should pass: {errs}")

    def test_valid_rotation_passes(self):
        errs = validate_dcm(ROT_Z90)
        self.assertEqual(errs, [], f"ROT_Z90 should pass: {errs}")

    def test_reflection_fails_determinant(self):
        errs = validate_dcm(REFLECT)
        self.assertTrue(
            any("determinant" in e for e in errs),
            f"Reflection should fail determinant check: {errs}",
        )

    def test_non_orthogonal_matrix_fails(self):
        errs = validate_dcm(NOT_ORTHO)
        self.assertTrue(
            any("orthogonal" in e for e in errs),
            f"Scale matrix should fail orthogonality: {errs}",
        )

    def test_wrong_shape_fails(self):
        errs = validate_dcm([[1, 0], [0, 1]])
        self.assertTrue(len(errs) > 0, "2x2 matrix should fail shape check")

    def test_custom_label_appears_in_error(self):
        errs = validate_dcm(REFLECT, label="MyDCM")
        self.assertTrue(any("MyDCM" in e for e in errs))


class TestFrameFieldChecks(unittest.TestCase):

    def test_complete_spacecraft_frame_has_no_missing_fields(self):
        missing = check_frame_fields(SPACECRAFT_FRAME)
        self.assertEqual(missing, [])

    def test_missing_fields_reported(self):
        minimal = {"name": "X", "type": "spacecraft"}
        missing = check_frame_fields(minimal)
        self.assertIn("dcm", missing)
        self.assertIn("origin", missing)
        self.assertIn("parent", missing)

    def test_invalid_frame_type_reported(self):
        bad = {**SPACECRAFT_FRAME, "type": "inertial"}
        errs = check_frame_type(bad)
        self.assertTrue(len(errs) > 0)
        self.assertIn("inertial", errs[0])

    def test_valid_frame_types_accepted(self):
        for ft in ("spacecraft", "equipment", "sensor"):
            frame = {**SPACECRAFT_FRAME, "type": ft}
            errs = check_frame_type(frame)
            self.assertEqual(errs, [], f"Type '{ft}' should be accepted")


class TestParentChecks(unittest.TestCase):

    def test_spacecraft_with_none_parent_passes(self):
        registry = {}
        errs = check_frame_parent(SPACECRAFT_FRAME, registry)
        self.assertEqual(errs, [])

    def test_spacecraft_with_nonnull_parent_fails(self):
        bad = {**SPACECRAFT_FRAME, "parent": "SCF"}
        errs = check_frame_parent(bad, {})
        self.assertTrue(len(errs) > 0)

    def test_equipment_frame_without_parent_fails(self):
        bad = {**EQUIPMENT_FRAME, "parent": None}
        errs = check_frame_parent(bad, {"SCF": SPACECRAFT_FRAME})
        self.assertTrue(len(errs) > 0)

    def test_equipment_frame_unknown_parent_fails(self):
        errs = check_frame_parent(EQUIPMENT_FRAME, {})  # SCF not in registry
        self.assertTrue(any("not found" in e for e in errs))

    def test_equipment_frame_known_parent_passes(self):
        errs = check_frame_parent(EQUIPMENT_FRAME, {"SCF": SPACECRAFT_FRAME})
        self.assertEqual(errs, [])


class TestCycleDetection(unittest.TestCase):

    def test_linear_chain_no_cycle(self):
        registry = {
            "SCF": {"name": "SCF", "type": "spacecraft", "parent": None},
            "EQ1": {"name": "EQ1", "type": "equipment", "parent": "SCF"},
        }
        errs = detect_parent_cycle("EQ1", registry)
        self.assertEqual(errs, [])

    def test_direct_self_reference_is_cycle(self):
        registry = {
            "EQ1": {"name": "EQ1", "type": "equipment", "parent": "EQ1"},
        }
        errs = detect_parent_cycle("EQ1", registry)
        self.assertTrue(len(errs) > 0)
        self.assertIn("Cyclic", errs[0])

    def test_mutual_cycle_detected(self):
        registry = {
            "A": {"name": "A", "parent": "B"},
            "B": {"name": "B", "parent": "A"},
        }
        errs = detect_parent_cycle("A", registry)
        self.assertTrue(len(errs) > 0)


class TestAlignmentValidation(unittest.TestCase):

    def test_complete_alignment_passes(self):
        registry = {"EQ1": EQUIPMENT_FRAME}
        result = validate_alignment(ALIGNMENT_EQ1, registry)
        self.assertEqual(result["errors"], [], result["errors"])

    def test_missing_alignment_fields_reported(self):
        bad = {"frame_name": "EQ1"}
        result = validate_alignment(bad, {"EQ1": EQUIPMENT_FRAME})
        self.assertTrue(len(result["errors"]) > 0)

    def test_invalid_measurement_status_reported(self):
        bad = {**ALIGNMENT_EQ1, "measurement_status": "unknown"}
        result = validate_alignment(bad, {"EQ1": EQUIPMENT_FRAME})
        self.assertTrue(any("measurement_status" in e for e in result["errors"]))

    def test_unknown_frame_ref_reported(self):
        result = validate_alignment(ALIGNMENT_EQ1, {})  # empty registry
        self.assertTrue(any("unknown frame" in e for e in result["errors"]))

    def test_invalid_nominal_dcm_reported(self):
        bad = {**ALIGNMENT_ST1, "frame_name": "ST1", "nominal_dcm": REFLECT}
        result = validate_alignment(bad, {"ST1": SENSOR_FRAME})
        self.assertTrue(any("determinant" in e for e in result["errors"]))

    def test_measured_status_without_measured_dcm_warns(self):
        aln = {
            "frame_name": "ST1",
            "nominal_dcm": ID3,
            "measurement_status": "measured",
        }
        result = validate_alignment(aln, {"ST1": SENSOR_FRAME})
        self.assertEqual(result["errors"], [])
        self.assertTrue(len(result["warnings"]) > 0)
        self.assertIn("measured_dcm", result["warnings"][0])


class TestFullSetAssessment(unittest.TestCase):

    def test_valid_frame_set_passes(self):
        frames = [SPACECRAFT_FRAME, EQUIPMENT_FRAME, SENSOR_FRAME]
        alignments = [ALIGNMENT_EQ1, ALIGNMENT_ST1]
        result = assess_frame_set(frames, alignments)
        self.assertTrue(result["pass"], result)

    def test_frame_set_with_bad_dcm_fails(self):
        bad_eq = {**EQUIPMENT_FRAME, "dcm": REFLECT}
        frames = [SPACECRAFT_FRAME, bad_eq]
        alignments = [ALIGNMENT_EQ1]
        result = assess_frame_set(frames, alignments)
        self.assertFalse(result["pass"])

    def test_unaligned_equipment_frame_produces_warning(self):
        frames = [SPACECRAFT_FRAME, EQUIPMENT_FRAME]
        alignments = []  # no alignment records at all
        result = assess_frame_set(frames, alignments)
        self.assertTrue(len(result["unaligned_warnings"]) > 0)
        self.assertIn("EQ1", result["unaligned_warnings"][0])

    def test_spacecraft_frame_with_wrong_parent_fails(self):
        bad_sc = {**SPACECRAFT_FRAME, "parent": "ROOT"}
        result = assess_frame_set([bad_sc], [])
        self.assertFalse(result["pass"])

    def test_sensor_parented_to_equipment_passes(self):
        sensor_on_eq = {**SENSOR_FRAME, "name": "ST2", "parent": "EQ1"}
        alignment_st2 = {**ALIGNMENT_ST1, "frame_name": "ST2"}
        frames = [SPACECRAFT_FRAME, EQUIPMENT_FRAME, sensor_on_eq]
        alignments = [ALIGNMENT_EQ1, alignment_st2]
        result = assess_frame_set(frames, alignments)
        self.assertTrue(result["pass"], result)

    def test_empty_frame_set_passes(self):
        result = assess_frame_set([], [])
        self.assertTrue(result["pass"])


if __name__ == "__main__":
    unittest.main()
