"""
Gate 3 contract tests for e1009-frame logic.

Covers: frame naming, origin description, unit vectors, orthogonality,
right-handedness, time-dependence consistency, epoch requirement,
parent-frame chain traceability, and the make_frame convenience helper.

Run with: python3 test_e1009_frame.py
"""

import math
import sys
import os
import unittest

# Allow importing the logic module from the same directory.
sys.path.insert(0, os.path.dirname(__file__))

from e1009_frame_logic import (
    validate_frame,
    check_frame_chain,
    check_frame_name,
    check_unit_vectors,
    check_orthogonality,
    check_right_handedness,
    check_time_dependence,
    derive_third_axis,
    normalize,
    make_frame,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _eci():
    """Return a minimal valid inertial (ECI J2000) frame dict."""
    return {
        "name": "ECI_J2000",
        "origin": "Earth centre of mass",
        "axes": [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)],
        "frame_type": "inertial",
        "time_dependent": False,
        "epoch": "J2000.0",
        "parent_frame": None,
    }


def _body():
    """Return a minimal valid body-fixed frame dict."""
    return {
        "name": "SC_BODY",
        "origin": "Spacecraft centre of mass (dry)",
        "axes": [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)],
        "frame_type": "body_fixed",
        "time_dependent": True,
        "epoch": None,
        "parent_frame": "ECI_J2000",
    }


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestValidInertialFrame(unittest.TestCase):
    def test_valid_inertial_frame_passes(self):
        result = validate_frame(_eci())
        self.assertTrue(result["valid"], result["issues"])
        self.assertEqual(result["issues"], [])


class TestValidBodyFixedFrame(unittest.TestCase):
    def test_valid_body_fixed_frame_passes(self):
        result = validate_frame(_body())
        self.assertTrue(result["valid"], result["issues"])
        self.assertEqual(result["issues"], [])


class TestValidOrbitReferencedFrame(unittest.TestCase):
    def test_valid_orbit_referenced_frame_passes(self):
        frame = {
            "name": "RTN_ORB",
            "origin": "Spacecraft centre of mass projected onto the orbit plane",
            "axes": [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)],
            "frame_type": "orbit_referenced",
            "time_dependent": True,
            "epoch": None,
            "parent_frame": "ECI_J2000",
        }
        result = validate_frame(frame)
        self.assertTrue(result["valid"], result["issues"])


class TestNonUnitAxisFlagged(unittest.TestCase):
    def test_non_unit_x_axis_flagged(self):
        frame = _eci()
        frame["axes"] = [(2.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
        result = validate_frame(frame)
        self.assertFalse(result["valid"])
        self.assertTrue(any("magnitude" in iss for iss in result["issues"]))

    def test_zero_axis_flagged(self):
        frame = _eci()
        frame["axes"] = [(0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
        result = validate_frame(frame)
        self.assertFalse(result["valid"])


class TestNonOrthogonalAxesFlagged(unittest.TestCase):
    def test_non_orthogonal_xy_flagged(self):
        s = math.sqrt(0.5)
        frame = _eci()
        # x and y both point partly in the same direction
        frame["axes"] = [(1.0, 0.0, 0.0), (s, s, 0.0), (0.0, 0.0, 1.0)]
        result = validate_frame(frame)
        self.assertFalse(result["valid"])
        self.assertTrue(any("orthogon" in iss for iss in result["issues"]))


class TestLeftHandedSystemFlagged(unittest.TestCase):
    def test_left_handed_axes_flagged(self):
        # Flip z to make it left-handed: z = -(x × y)
        frame = _eci()
        frame["axes"] = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, -1.0)]
        result = validate_frame(frame)
        self.assertFalse(result["valid"])
        self.assertTrue(any("right-hand" in iss or "right_hand" in iss or
                             "right-handed" in iss for iss in result["issues"]))


class TestInertialMarkedTimeDependentFlagged(unittest.TestCase):
    def test_inertial_time_dependent_flagged(self):
        frame = _eci()
        frame["time_dependent"] = True
        result = validate_frame(frame)
        self.assertFalse(result["valid"])
        self.assertTrue(any("time-independent" in iss or "time_dependent" in iss
                             for iss in result["issues"]))


class TestBodyFixedMarkedTimeIndependentFlagged(unittest.TestCase):
    def test_body_fixed_time_independent_flagged(self):
        frame = _body()
        frame["time_dependent"] = False
        result = validate_frame(frame)
        self.assertFalse(result["valid"])
        self.assertTrue(any("time-varying" in iss or "time_dependent" in iss
                             for iss in result["issues"]))


class TestInertialWithoutEpochFlagged(unittest.TestCase):
    def test_inertial_missing_epoch_flagged(self):
        frame = _eci()
        frame["epoch"] = None
        result = validate_frame(frame)
        self.assertFalse(result["valid"])
        self.assertTrue(any("epoch" in iss for iss in result["issues"]))

    def test_inertial_empty_string_epoch_flagged(self):
        frame = _eci()
        frame["epoch"] = ""
        result = validate_frame(frame)
        self.assertFalse(result["valid"])


class TestEmptyOriginDescriptionFlagged(unittest.TestCase):
    def test_empty_origin_flagged(self):
        frame = _eci()
        frame["origin"] = ""
        result = validate_frame(frame)
        self.assertFalse(result["valid"])
        self.assertTrue(any("origin" in iss for iss in result["issues"]))

    def test_short_origin_flagged(self):
        frame = _eci()
        frame["origin"] = "CoM"   # too short
        result = validate_frame(frame)
        self.assertFalse(result["valid"])


class TestFrameNameConvention(unittest.TestCase):
    def test_lowercase_name_flagged(self):
        issues = check_frame_name("eci_j2000")
        self.assertTrue(len(issues) > 0)

    def test_mixed_case_name_flagged(self):
        issues = check_frame_name("Eci_J2000")
        self.assertTrue(len(issues) > 0)

    def test_empty_name_flagged(self):
        issues = check_frame_name("")
        self.assertTrue(len(issues) > 0)

    def test_name_starting_with_digit_flagged(self):
        issues = check_frame_name("1ECI")
        self.assertTrue(len(issues) > 0)

    def test_too_long_name_flagged(self):
        issues = check_frame_name("A" * 65)
        self.assertTrue(len(issues) > 0)

    def test_valid_names_pass(self):
        for name in ("ECI_J2000", "SC_BODY", "RTN_ORB", "ECEF", "A"):
            with self.subTest(name=name):
                self.assertEqual(check_frame_name(name), [])


class TestFrameChainTraceability(unittest.TestCase):
    def test_missing_parent_flagged(self):
        frames = [
            {"name": "SC_BODY", "parent_frame": "ECI_MISSING"},
        ]
        issues = check_frame_chain(frames)
        self.assertTrue(len(issues) > 0)
        self.assertIn("ECI_MISSING", issues[0])

    def test_valid_chain_passes(self):
        frames = [
            {"name": "ECI_J2000", "parent_frame": None},
            {"name": "SC_BODY", "parent_frame": "ECI_J2000"},
            {"name": "SENSOR_A", "parent_frame": "SC_BODY"},
        ]
        issues = check_frame_chain(frames)
        self.assertEqual(issues, [])

    def test_root_with_no_parent_passes(self):
        frames = [{"name": "ECI_J2000", "parent_frame": None}]
        issues = check_frame_chain(frames)
        self.assertEqual(issues, [])


class TestDeriveThirdAxis(unittest.TestCase):
    def test_standard_axes(self):
        z = derive_third_axis((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        self.assertAlmostEqual(z[0], 0.0, places=9)
        self.assertAlmostEqual(z[1], 0.0, places=9)
        self.assertAlmostEqual(z[2], 1.0, places=9)

    def test_result_is_unit_vector(self):
        z = derive_third_axis((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        mag = math.sqrt(sum(c ** 2 for c in z))
        self.assertAlmostEqual(mag, 1.0, places=9)

    def test_zero_vector_raises(self):
        with self.assertRaises(ValueError):
            derive_third_axis((0.0, 0.0, 0.0), (0.0, 1.0, 0.0))


class TestMakeFrameHelper(unittest.TestCase):
    def test_make_inertial_frame_valid(self):
        _, result = make_frame(
            name="ECI_J2000",
            origin="Earth centre of mass",
            x_axis=(1.0, 0.0, 0.0),
            y_axis=(0.0, 1.0, 0.0),
            frame_type="inertial",
            time_dependent=False,
            epoch="J2000.0",
        )
        self.assertTrue(result["valid"], result["issues"])

    def test_make_body_frame_valid(self):
        _, result = make_frame(
            name="SC_BODY",
            origin="Spacecraft centre of mass (dry)",
            x_axis=(1.0, 0.0, 0.0),
            y_axis=(0.0, 1.0, 0.0),
            frame_type="body_fixed",
            time_dependent=True,
            parent_frame="ECI_J2000",
        )
        self.assertTrue(result["valid"], result["issues"])


class TestUnknownFrameTypeFlagged(unittest.TestCase):
    def test_unknown_frame_type_flagged(self):
        frame = _eci()
        frame["frame_type"] = "galactic"
        result = validate_frame(frame)
        self.assertFalse(result["valid"])
        self.assertTrue(any("unknown frame type" in iss for iss in result["issues"]))


class TestPlanetFixedFrame(unittest.TestCase):
    def test_planet_fixed_time_varying_passes(self):
        frame = {
            "name": "ECEF",
            "origin": "Earth centre of mass (terrestrial reference)",
            "axes": [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)],
            "frame_type": "planet_fixed",
            "time_dependent": True,
            "epoch": None,
            "parent_frame": "ECI_J2000",
        }
        result = validate_frame(frame)
        self.assertTrue(result["valid"], result["issues"])

    def test_planet_fixed_time_independent_flagged(self):
        frame = {
            "name": "ECEF",
            "origin": "Earth centre of mass (terrestrial reference)",
            "axes": [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)],
            "frame_type": "planet_fixed",
            "time_dependent": False,
            "epoch": None,
            "parent_frame": "ECI_J2000",
        }
        result = validate_frame(frame)
        self.assertFalse(result["valid"])


class TestAxisCountEnforced(unittest.TestCase):
    def test_two_axes_flagged(self):
        frame = _eci()
        frame["axes"] = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        result = validate_frame(frame)
        self.assertFalse(result["valid"])

    def test_four_axes_flagged(self):
        frame = _eci()
        frame["axes"] = [
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
            (0.0, 0.0, 1.0),
        ]
        result = validate_frame(frame)
        self.assertFalse(result["valid"])


if __name__ == "__main__":
    unittest.main()
