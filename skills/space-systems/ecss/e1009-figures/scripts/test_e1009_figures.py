"""
Tests for e1009_figures_logic — ECSS-E-ST-10-09C §5.3.3 figure conventions.
stdlib unittest only; deterministic and offline.
Run: python3 test_e1009_figures.py
"""

import math
import unittest

from e1009_figures_logic import (
    AxisVector,
    CoordinateFrame,
    FigureSpec,
    CheckResult,
    validate_right_hand_rule,
    validate_frame_type,
    validate_euler_sequence,
    check_figure_completeness,
    validate_figure_spec,
    describe_axis_orientation,
    summarize_frame,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _axes(x, y, z):
    return [
        AxisVector("x", x),
        AxisVector("y", y),
        AxisVector("z", z),
    ]


def _standard_frame(name="SC_BODY", ftype="body"):
    return CoordinateFrame(
        name=name,
        frame_type=ftype,
        origin_description="spacecraft centre of mass",
        axes=_axes((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    )


def _good_spec(figure_id="FIG-001", euler_seq=None, euler_ang=None):
    return FigureSpec(
        figure_id=figure_id,
        title="Spacecraft Body Frame",
        frame=_standard_frame(),
        reference_frame="ECI",
        euler_sequence=euler_seq,
        euler_angles_deg=euler_ang,
    )


# ---------------------------------------------------------------------------
# Right-hand rule tests
# ---------------------------------------------------------------------------

class TestRightHandRule(unittest.TestCase):

    def test_canonical_body_axes_pass(self):
        r = validate_right_hand_rule(_axes((1, 0, 0), (0, 1, 0), (0, 0, 1)))
        self.assertTrue(r.passed, r.findings)

    def test_left_handed_triad_fails(self):
        # z points in −Z direction → left-handed
        r = validate_right_hand_rule(_axes((1, 0, 0), (0, 1, 0), (0, 0, -1)))
        self.assertFalse(r.passed)
        combined = " ".join(r.findings).lower()
        self.assertIn("left-handed", combined)

    def test_non_orthogonal_xy_fails(self):
        r = validate_right_hand_rule(_axes((1, 0, 0), (1, 1, 0), (0, 0, 1)))
        self.assertFalse(r.passed)
        self.assertTrue(any("orthogonal" in f for f in r.findings))

    def test_wrong_axis_count_fails(self):
        axes = [AxisVector("x", (1, 0, 0)), AxisVector("y", (0, 1, 0))]
        r = validate_right_hand_rule(axes)
        self.assertFalse(r.passed)

    def test_scaled_axes_pass(self):
        # Scaling individual axes must not affect the right-hand result
        r = validate_right_hand_rule(_axes((3, 0, 0), (0, 2, 0), (0, 0, 7)))
        self.assertTrue(r.passed, r.findings)

    def test_45_degree_rotation_passes(self):
        a = math.pi / 4
        r = validate_right_hand_rule(_axes(
            (math.cos(a), math.sin(a), 0),
            (-math.sin(a), math.cos(a), 0),
            (0, 0, 1),
        ))
        self.assertTrue(r.passed, r.findings)

    def test_duplicate_axis_label_fails(self):
        # Two axes labelled "x" — not a valid triad
        axes = [
            AxisVector("x", (1, 0, 0)),
            AxisVector("x", (0, 1, 0)),
            AxisVector("z", (0, 0, 1)),
        ]
        r = validate_right_hand_rule(axes)
        self.assertFalse(r.passed)


# ---------------------------------------------------------------------------
# Frame-type tests
# ---------------------------------------------------------------------------

class TestFrameType(unittest.TestCase):

    def test_body_is_valid(self):
        self.assertTrue(validate_frame_type("body").passed)

    def test_inertial_is_valid(self):
        self.assertTrue(validate_frame_type("inertial").passed)

    def test_orbital_is_valid(self):
        self.assertTrue(validate_frame_type("orbital").passed)

    def test_sensor_is_valid(self):
        self.assertTrue(validate_frame_type("sensor").passed)

    def test_structural_is_valid(self):
        self.assertTrue(validate_frame_type("structural").passed)

    def test_unknown_type_fails(self):
        r = validate_frame_type("galactic")
        self.assertFalse(r.passed)
        self.assertEqual(len(r.findings), 1)
        self.assertIn("galactic", r.findings[0])


# ---------------------------------------------------------------------------
# Euler sequence tests
# ---------------------------------------------------------------------------

class TestEulerSequence(unittest.TestCase):

    def test_321_is_valid(self):
        self.assertTrue(validate_euler_sequence("321").passed)

    def test_313_is_valid(self):
        self.assertTrue(validate_euler_sequence("313").passed)

    def test_123_is_valid(self):
        self.assertTrue(validate_euler_sequence("123").passed)

    def test_consecutive_axes_fails(self):
        # "112" has consecutive identical first axes
        r = validate_euler_sequence("112")
        self.assertFalse(r.passed)
        self.assertTrue(any("consecutive" in f.lower() for f in r.findings))

    def test_too_short_fails(self):
        r = validate_euler_sequence("31")
        self.assertFalse(r.passed)

    def test_too_long_fails(self):
        r = validate_euler_sequence("3121")
        self.assertFalse(r.passed)

    def test_invalid_character_fails(self):
        r = validate_euler_sequence("3a1")
        self.assertFalse(r.passed)
        self.assertTrue(any("invalid" in f.lower() for f in r.findings))


# ---------------------------------------------------------------------------
# Figure completeness tests
# ---------------------------------------------------------------------------

class TestFigureCompleteness(unittest.TestCase):

    def test_complete_spec_passes(self):
        spec = FigureSpec(
            figure_id="FIG-002",
            title="Orbital Reference Frame",
            frame=_standard_frame("ORF", "orbital"),
        )
        r = check_figure_completeness(spec)
        self.assertTrue(r.passed, r.findings)

    def test_blank_figure_id_fails(self):
        spec = FigureSpec(
            figure_id="",
            title="Some Frame",
            frame=_standard_frame(),
        )
        r = check_figure_completeness(spec)
        self.assertFalse(r.passed)
        self.assertTrue(any("ID" in f for f in r.findings))

    def test_missing_z_axis_label_fails(self):
        frame = CoordinateFrame(
            name="F",
            frame_type="body",
            origin_description="origin",
            axes=[AxisVector("x", (1, 0, 0)), AxisVector("y", (0, 1, 0))],
        )
        spec = FigureSpec(figure_id="FIG-003", title="T", frame=frame)
        r = check_figure_completeness(spec)
        self.assertFalse(r.passed)
        self.assertTrue(any("'z'" in f for f in r.findings))

    def test_blank_origin_description_fails(self):
        frame = CoordinateFrame(
            name="F2",
            frame_type="inertial",
            origin_description="   ",
            axes=_axes((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        )
        spec = FigureSpec(figure_id="FIG-004", title="ECI Frame", frame=frame)
        r = check_figure_completeness(spec)
        self.assertFalse(r.passed)


# ---------------------------------------------------------------------------
# Full figure-spec validation tests
# ---------------------------------------------------------------------------

class TestValidateFigureSpec(unittest.TestCase):

    def test_valid_spec_passes(self):
        r = validate_figure_spec(_good_spec())
        self.assertTrue(r.passed, r.findings)

    def test_blank_title_fails(self):
        spec = _good_spec()
        spec.title = "  "
        r = validate_figure_spec(spec)
        self.assertFalse(r.passed)

    def test_angles_without_sequence_fails(self):
        spec = _good_spec(euler_ang=(10.0, 20.0, 30.0))
        r = validate_figure_spec(spec)
        self.assertFalse(r.passed)
        self.assertTrue(any("euler_sequence" in f for f in r.findings))

    def test_angles_with_valid_sequence_passes(self):
        spec = _good_spec(euler_seq="321", euler_ang=(10.0, 20.0, 30.0))
        r = validate_figure_spec(spec)
        self.assertTrue(r.passed, r.findings)

    def test_invalid_euler_sequence_propagates(self):
        spec = _good_spec(euler_seq="221")
        r = validate_figure_spec(spec)
        self.assertFalse(r.passed)

    def test_left_handed_frame_fails(self):
        frame = CoordinateFrame(
            name="LH",
            frame_type="body",
            origin_description="centre of mass",
            axes=_axes((1, 0, 0), (0, 1, 0), (0, 0, -1)),
        )
        spec = FigureSpec(figure_id="FIG-005", title="Bad Frame", frame=frame)
        r = validate_figure_spec(spec)
        self.assertFalse(r.passed)

    def test_unknown_frame_type_fails(self):
        spec = _good_spec()
        spec.frame.frame_type = "galactic"
        r = validate_figure_spec(spec)
        self.assertFalse(r.passed)


# ---------------------------------------------------------------------------
# Describe axis orientation tests
# ---------------------------------------------------------------------------

class TestDescribeAxisOrientation(unittest.TestCase):

    def test_positive_x_axis(self):
        desc = describe_axis_orientation(AxisVector("x", (1, 0, 0)))
        self.assertIn("+X", desc)

    def test_negative_y_axis(self):
        desc = describe_axis_orientation(AxisVector("y", (0, -1, 0)))
        self.assertIn("-Y", desc)

    def test_zero_vector_description(self):
        desc = describe_axis_orientation(AxisVector("z", (0, 0, 0)))
        self.assertIn("zero vector", desc)


# ---------------------------------------------------------------------------
# Summarize frame tests
# ---------------------------------------------------------------------------

class TestSummarizeFrame(unittest.TestCase):

    def test_summary_keys_present(self):
        s = summarize_frame(_standard_frame())
        for key in ("name", "type", "origin", "axes"):
            self.assertIn(key, s)

    def test_axes_list_length(self):
        s = summarize_frame(_standard_frame())
        self.assertEqual(len(s["axes"]), 3)


if __name__ == "__main__":
    unittest.main()
