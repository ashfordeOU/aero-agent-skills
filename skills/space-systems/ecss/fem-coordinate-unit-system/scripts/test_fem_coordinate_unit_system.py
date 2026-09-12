"""
test_fem_coordinate_unit_system.py

stdlib unittest for fem_coordinate_unit_system_logic.py.
Offline, deterministic. Run: python3 test_fem_coordinate_unit_system.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from fem_coordinate_unit_system_logic import (
    check_right_hand_rule,
    validate_coordinate_frame,
    validate_unit_system,
    validate_fem_exchange_package,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_GLOBAL_FRAME = {
    "label": "BASIC",
    "origin_ref": "BASIC",
    "x_axis": (1.0, 0.0, 0.0),
    "y_axis": (0.0, 1.0, 0.0),
    "z_axis": (0.0, 0.0, 1.0),
}

_LOCAL_FRAME = {
    "label": "PANEL_CS",
    "origin_ref": "BASIC",
    "x_axis": (0.0, 1.0, 0.0),
    "y_axis": (0.0, 0.0, 1.0),
    "z_axis": (1.0, 0.0, 0.0),
}

_SI_UNITS = {"force": "N", "mass": "kg", "length": "m", "pressure": "Pa"}
_MM_UNITS = {"force": "N", "mass": "t", "length": "mm", "pressure": "MPa"}


# ---------------------------------------------------------------------------
# Right-hand rule
# ---------------------------------------------------------------------------

class TestRightHandRule(unittest.TestCase):

    def test_standard_basis_passes(self):
        ok, msg = check_right_hand_rule((1, 0, 0), (0, 1, 0), (0, 0, 1))
        self.assertTrue(ok, msg)

    def test_permuted_basis_passes(self):
        # y->z->x permutation is also right-handed
        ok, msg = check_right_hand_rule((0, 1, 0), (0, 0, 1), (1, 0, 0))
        self.assertTrue(ok, msg)

    def test_left_hand_frame_fails(self):
        # Negate z to make it left-handed
        ok, msg = check_right_hand_rule((1, 0, 0), (0, 1, 0), (0, 0, -1))
        self.assertFalse(ok)
        self.assertIn("right-hand rule", msg)

    def test_non_orthogonal_xy_fails(self):
        # x and y are not orthogonal
        ok, msg = check_right_hand_rule((1, 0, 0), (0.5, 0.866, 0), (0, 0, 1))
        self.assertFalse(ok)

    def test_zero_vector_fails(self):
        ok, msg = check_right_hand_rule((0, 0, 0), (0, 1, 0), (0, 0, 1))
        self.assertFalse(ok)
        self.assertIn("normalisation", msg)

    def test_scaled_axes_pass(self):
        # Non-unit-length but still right-handed
        ok, msg = check_right_hand_rule((2, 0, 0), (0, 3, 0), (0, 0, 5))
        self.assertTrue(ok, msg)


# ---------------------------------------------------------------------------
# Coordinate frame validation
# ---------------------------------------------------------------------------

class TestCoordinateFrame(unittest.TestCase):

    def test_valid_global_frame(self):
        errs = validate_coordinate_frame(_GLOBAL_FRAME)
        self.assertEqual(errs, [])

    def test_valid_local_frame(self):
        errs = validate_coordinate_frame(_LOCAL_FRAME)
        self.assertEqual(errs, [])

    def test_missing_label_detected(self):
        frame = {k: v for k, v in _GLOBAL_FRAME.items() if k != "label"}
        errs = validate_coordinate_frame(frame)
        self.assertTrue(any("label" in e for e in errs))

    def test_missing_origin_ref_detected(self):
        frame = {k: v for k, v in _GLOBAL_FRAME.items() if k != "origin_ref"}
        errs = validate_coordinate_frame(frame)
        self.assertTrue(any("origin_ref" in e for e in errs))

    def test_left_handed_frame_rejected(self):
        frame = {
            "label": "LH",
            "origin_ref": "BASIC",
            "x_axis": (1, 0, 0),
            "y_axis": (0, 1, 0),
            "z_axis": (0, 0, -1),  # negated → left-handed
        }
        errs = validate_coordinate_frame(frame)
        self.assertGreater(len(errs), 0)

    def test_empty_label_rejected(self):
        frame = dict(_GLOBAL_FRAME)
        frame = {**frame, "label": "   "}
        errs = validate_coordinate_frame(frame)
        self.assertTrue(any("label" in e for e in errs))


# ---------------------------------------------------------------------------
# Unit system validation
# ---------------------------------------------------------------------------

class TestUnitSystem(unittest.TestCase):

    def test_si_accepted(self):
        ok, issues = validate_unit_system(_SI_UNITS)
        self.assertTrue(ok, issues)
        self.assertEqual(issues, [])

    def test_mm_n_t_accepted(self):
        ok, issues = validate_unit_system(_MM_UNITS)
        self.assertTrue(ok, issues)
        self.assertEqual(issues, [])

    def test_inconsistent_pressure_rejected(self):
        bad = {**_SI_UNITS, "pressure": "MPa"}  # MPa not valid for SI (m-based)
        ok, issues = validate_unit_system(bad)
        self.assertFalse(ok)
        self.assertTrue(any("pressure" in i.lower() for i in issues))

    def test_inconsistent_mass_rejected(self):
        # kg is not consistent with N and mm
        bad = {**_MM_UNITS, "mass": "kg"}
        ok, issues = validate_unit_system(bad)
        self.assertFalse(ok)
        self.assertTrue(any("mass" in i.lower() for i in issues))

    def test_missing_field_rejected(self):
        incomplete = {"force": "N", "mass": "kg", "length": "m"}
        ok, issues = validate_unit_system(incomplete)
        self.assertFalse(ok)
        self.assertTrue(any("pressure" in i for i in issues))

    def test_unknown_force_length_rejected(self):
        bad = {"force": "kN", "mass": "kg", "length": "m", "pressure": "Pa"}
        ok, issues = validate_unit_system(bad)
        self.assertFalse(ok)


# ---------------------------------------------------------------------------
# Full exchange package validation
# ---------------------------------------------------------------------------

class TestFemExchangePackage(unittest.TestCase):

    def _valid_package(self):
        return {
            "unit_system": _SI_UNITS,
            "coordinate_frames": [dict(_GLOBAL_FRAME), dict(_LOCAL_FRAME)],
            "global_frame_label": "BASIC",
        }

    def test_valid_si_package_passes(self):
        result = validate_fem_exchange_package(self._valid_package())
        self.assertTrue(result["ok"])
        self.assertEqual(result["unit_errors"], [])
        self.assertEqual(result["frame_errors"], [])
        self.assertEqual(result["global_frame_errors"], [])

    def test_valid_mm_package_passes(self):
        pkg = self._valid_package()
        pkg["unit_system"] = _MM_UNITS
        result = validate_fem_exchange_package(pkg)
        self.assertTrue(result["ok"])

    def test_missing_unit_system_fails(self):
        pkg = self._valid_package()
        del pkg["unit_system"]
        result = validate_fem_exchange_package(pkg)
        self.assertFalse(result["ok"])
        self.assertTrue(len(result["unit_errors"]) > 0)

    def test_no_frames_fails(self):
        pkg = self._valid_package()
        pkg["coordinate_frames"] = []
        result = validate_fem_exchange_package(pkg)
        self.assertFalse(result["ok"])
        self.assertTrue(len(result["frame_errors"]) > 0)

    def test_missing_global_frame_label_fails(self):
        pkg = self._valid_package()
        del pkg["global_frame_label"]
        result = validate_fem_exchange_package(pkg)
        self.assertFalse(result["ok"])
        self.assertTrue(len(result["global_frame_errors"]) > 0)

    def test_global_frame_not_in_list_fails(self):
        pkg = self._valid_package()
        pkg["global_frame_label"] = "NONEXISTENT_CS"
        result = validate_fem_exchange_package(pkg)
        self.assertFalse(result["ok"])
        self.assertTrue(any("NONEXISTENT_CS" in e for e in result["global_frame_errors"]))

    def test_bad_frame_propagates_to_frame_errors(self):
        pkg = self._valid_package()
        left_handed = {
            "label": "BAD_CS",
            "origin_ref": "BASIC",
            "x_axis": (1, 0, 0),
            "y_axis": (0, 1, 0),
            "z_axis": (0, 0, -1),
        }
        pkg["coordinate_frames"].append(left_handed)
        result = validate_fem_exchange_package(pkg)
        self.assertFalse(result["ok"])
        self.assertTrue(len(result["frame_errors"]) > 0)

    def test_inconsistent_units_propagates(self):
        pkg = self._valid_package()
        pkg["unit_system"] = {**_SI_UNITS, "pressure": "MPa"}
        result = validate_fem_exchange_package(pkg)
        self.assertFalse(result["ok"])
        self.assertTrue(len(result["unit_errors"]) > 0)

    def test_ok_field_is_bool(self):
        result = validate_fem_exchange_package(self._valid_package())
        self.assertIsInstance(result["ok"], bool)


if __name__ == "__main__":
    unittest.main()
