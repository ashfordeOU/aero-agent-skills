#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §5.4.2 coordinate system definition.

Exercises scripts/e1009_csys_logic.py (stdlib unittest, offline).
Contract: a coordinate system definition requires a non-empty name, a
recognised frame type, a recognised coordinate representation, a non-empty
origin, and a non-empty direction string for every required coordinate label;
rotating, orbital, and topocentric frame types are inherently time-dependent
and cannot have that flag overridden to False; body-fixed and inertial frames
accept an explicit time_dependent value; the definability check returns False
with an issue list for any missing or empty axis; flag_time_dependent_frames
returns exactly the names with time_dependent True; parent-frame references
must resolve to a known name in the registered set; and the registry summary
is compliant only when no underdefined frames and no broken parent references
exist.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1009_csys_logic as csys  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _eci():
    return csys.define_coordinate_system(
        name="ECI",
        frame_type="INERTIAL",
        coord_type="CARTESIAN",
        origin="Earth centre of mass",
        axes={
            "x": "vernal equinox direction at J2000 epoch",
            "y": "90 deg east of x in the mean equatorial plane",
            "z": "north celestial pole",
        },
    )


def _ecef():
    return csys.define_coordinate_system(
        name="ECEF",
        frame_type="ROTATING",
        coord_type="CARTESIAN",
        origin="Earth centre of mass",
        axes={
            "x": "intersection of Greenwich meridian and equatorial plane",
            "y": "90 deg east of x in the equatorial plane",
            "z": "north pole",
        },
    )


def _body():
    return csys.define_coordinate_system(
        name="SC_BODY",
        frame_type="BODY_FIXED",
        coord_type="CARTESIAN",
        origin="spacecraft centre of mass",
        axes={
            "x": "positive roll axis",
            "y": "positive pitch axis",
            "z": "positive yaw axis",
        },
        time_dependent=True,
    )


def _spher():
    return csys.define_coordinate_system(
        name="ECI_SPHER",
        frame_type="INERTIAL",
        coord_type="SPHERICAL",
        origin="Earth centre of mass",
        axes={
            "r": "radial outward from origin",
            "theta": "colatitude from north celestial pole",
            "phi": "right ascension east of vernal equinox",
        },
    )


def _orbital_cartesian():
    return csys.define_coordinate_system(
        name="LVLH",
        frame_type="ORBITAL",
        coord_type="CARTESIAN",
        origin="spacecraft centre of mass in reference orbit",
        axes={
            "x": "radial outward from orbit focus",
            "y": "along-track in direction of motion",
            "z": "cross-track toward angular momentum vector",
        },
        parent_frame="ECI",
    )


def _cylindrical_topo():
    return csys.define_coordinate_system(
        name="TOPO_CYL",
        frame_type="TOPOCENTRIC",
        coord_type="CYLINDRICAL",
        origin="ground station antenna phase centre",
        axes={
            "rho": "horizontal distance from station vertical axis",
            "phi": "azimuth east of geographic north",
            "z": "upward along local vertical",
        },
    )


# ---------------------------------------------------------------------------
# Tests: define_coordinate_system
# ---------------------------------------------------------------------------

class TestDefineCoordinateSystem(unittest.TestCase):

    def test_valid_cartesian_inertial_is_time_invariant(self):
        cs = _eci()
        self.assertEqual(cs["name"], "ECI")
        self.assertEqual(cs["frame_type"], "INERTIAL")
        self.assertFalse(cs["time_dependent"])

    def test_valid_cartesian_rotating_inherits_time_dependence(self):
        cs = _ecef()
        self.assertTrue(cs["time_dependent"])

    def test_valid_spherical_inertial(self):
        cs = _spher()
        self.assertEqual(cs["coord_type"], "SPHERICAL")
        self.assertFalse(cs["time_dependent"])

    def test_valid_cylindrical_topocentric_is_time_dependent(self):
        cs = _cylindrical_topo()
        self.assertEqual(cs["coord_type"], "CYLINDRICAL")
        self.assertTrue(cs["time_dependent"])

    def test_valid_orbital_cartesian_is_time_dependent(self):
        cs = _orbital_cartesian()
        self.assertTrue(cs["time_dependent"])
        self.assertEqual(cs["parent_frame"], "ECI")

    def test_body_fixed_explicit_time_dependent_true(self):
        cs = _body()
        self.assertTrue(cs["time_dependent"])

    def test_body_fixed_defaults_to_time_invariant_when_unset(self):
        cs = csys.define_coordinate_system(
            name="SC_STATIC",
            frame_type="BODY_FIXED",
            coord_type="CARTESIAN",
            origin="spacecraft centre of mass",
            axes={"x": "roll axis", "y": "pitch axis", "z": "yaw axis"},
        )
        self.assertFalse(cs["time_dependent"])

    def test_invalid_frame_type_raises(self):
        with self.assertRaises(csys.CoordSystemError):
            csys.define_coordinate_system(
                name="BAD",
                frame_type="GALACTIC_FIXED",
                coord_type="CARTESIAN",
                origin="Sun",
                axes={"x": "galactic centre", "y": "north galactic pole cross x", "z": "north galactic pole"},
            )

    def test_invalid_coord_type_raises(self):
        with self.assertRaises(csys.CoordSystemError):
            csys.define_coordinate_system(
                name="BAD2",
                frame_type="INERTIAL",
                coord_type="POLAR_2D",
                origin="Earth CoM",
                axes={"r": "radial", "phi": "azimuth"},
            )

    def test_empty_origin_raises(self):
        with self.assertRaises(csys.CoordSystemError):
            csys.define_coordinate_system(
                name="NO_ORIGIN",
                frame_type="INERTIAL",
                coord_type="CARTESIAN",
                origin="",
                axes={"x": "v.e.", "y": "east", "z": "north"},
            )

    def test_missing_cartesian_axis_raises(self):
        with self.assertRaises(csys.CoordSystemError):
            csys.define_coordinate_system(
                name="INCOMPLETE",
                frame_type="INERTIAL",
                coord_type="CARTESIAN",
                origin="Earth CoM",
                axes={"x": "vernal equinox", "y": "east"},  # missing z
            )

    def test_empty_axis_direction_raises(self):
        with self.assertRaises(csys.CoordSystemError):
            csys.define_coordinate_system(
                name="EMPTY_AX",
                frame_type="BODY_FIXED",
                coord_type="CARTESIAN",
                origin="spacecraft CoM",
                axes={"x": "roll axis", "y": "", "z": "yaw axis"},
            )

    def test_override_time_dependent_false_on_rotating_raises(self):
        with self.assertRaises(csys.CoordSystemError):
            csys.define_coordinate_system(
                name="BAD_ECEF",
                frame_type="ROTATING",
                coord_type="CARTESIAN",
                origin="Earth CoM",
                axes={"x": "Greenwich", "y": "east", "z": "north pole"},
                time_dependent=False,
            )

    def test_override_time_dependent_false_on_orbital_raises(self):
        with self.assertRaises(csys.CoordSystemError):
            csys.define_coordinate_system(
                name="BAD_LVLH",
                frame_type="ORBITAL",
                coord_type="CARTESIAN",
                origin="spacecraft CoM",
                axes={"x": "radial", "y": "along-track", "z": "cross-track"},
                time_dependent=False,
            )

    def test_empty_name_raises(self):
        with self.assertRaises(csys.CoordSystemError):
            csys.define_coordinate_system(
                name="",
                frame_type="INERTIAL",
                coord_type="CARTESIAN",
                origin="Earth CoM",
                axes={"x": "v.e.", "y": "east", "z": "north"},
            )

    def test_whitespace_only_name_raises(self):
        with self.assertRaises(csys.CoordSystemError):
            csys.define_coordinate_system(
                name="   ",
                frame_type="INERTIAL",
                coord_type="CARTESIAN",
                origin="Earth CoM",
                axes={"x": "v.e.", "y": "east", "z": "north"},
            )

    def test_axes_dict_not_mutated(self):
        original = {"x": "v.e.", "y": "east", "z": "north"}
        cs = csys.define_coordinate_system(
            name="ECI2", frame_type="INERTIAL", coord_type="CARTESIAN",
            origin="Earth CoM", axes=original,
        )
        cs["axes"]["x"] = "MUTATED"
        self.assertEqual(original["x"], "v.e.")

    def test_missing_spherical_axis_raises(self):
        with self.assertRaises(csys.CoordSystemError):
            csys.define_coordinate_system(
                name="BAD_SPHER",
                frame_type="INERTIAL",
                coord_type="SPHERICAL",
                origin="Earth CoM",
                axes={"r": "radial", "theta": "colatitude"},  # missing phi
            )


# ---------------------------------------------------------------------------
# Tests: check_coordinates_definable
# ---------------------------------------------------------------------------

class TestCheckCoordinatesDefinable(unittest.TestCase):

    def test_complete_cartesian_is_definable(self):
        ok, issues = csys.check_coordinates_definable(_eci())
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_complete_spherical_is_definable(self):
        ok, issues = csys.check_coordinates_definable(_spher())
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_partial_dict_missing_axis_not_definable(self):
        cs = {
            "name": "PARTIAL",
            "coord_type": "CARTESIAN",
            "axes": {"x": "vernal equinox", "y": "east"},
        }
        ok, issues = csys.check_coordinates_definable(cs)
        self.assertFalse(ok)
        self.assertTrue(any("z" in i for i in issues))

    def test_partial_dict_empty_axis_not_definable(self):
        cs = {
            "name": "EMPTY_PHI",
            "coord_type": "SPHERICAL",
            "axes": {"r": "radial", "theta": "colatitude", "phi": ""},
        }
        ok, issues = csys.check_coordinates_definable(cs)
        self.assertFalse(ok)
        self.assertTrue(any("phi" in i for i in issues))

    def test_unknown_coord_type_not_definable(self):
        cs = {"name": "UNK", "coord_type": "HEXAGONAL", "axes": {}}
        ok, issues = csys.check_coordinates_definable(cs)
        self.assertFalse(ok)
        self.assertTrue(len(issues) > 0)


# ---------------------------------------------------------------------------
# Tests: flag_time_dependent_frames
# ---------------------------------------------------------------------------

class TestFlagTimeDependentFrames(unittest.TestCase):

    def test_rotating_frame_flagged(self):
        flagged = csys.flag_time_dependent_frames([_eci(), _ecef()])
        self.assertIn("ECEF", flagged)
        self.assertNotIn("ECI", flagged)

    def test_orbital_frame_flagged(self):
        flagged = csys.flag_time_dependent_frames([_orbital_cartesian()])
        self.assertIn("LVLH", flagged)

    def test_topocentric_frame_flagged(self):
        flagged = csys.flag_time_dependent_frames([_cylindrical_topo()])
        self.assertIn("TOPO_CYL", flagged)

    def test_inertial_frame_not_flagged(self):
        flagged = csys.flag_time_dependent_frames([_eci()])
        self.assertEqual(flagged, [])

    def test_empty_list_returns_empty(self):
        self.assertEqual(csys.flag_time_dependent_frames([]), [])


# ---------------------------------------------------------------------------
# Tests: categorize_frames_by_time_dependence
# ---------------------------------------------------------------------------

class TestCategorizeFrames(unittest.TestCase):

    def test_mixed_list_separated_correctly(self):
        cs_list = [_eci(), _ecef(), _body()]
        time_dep, time_inv = csys.categorize_frames_by_time_dependence(cs_list)
        self.assertIn("ECEF", time_dep)
        self.assertIn("SC_BODY", time_dep)
        self.assertIn("ECI", time_inv)
        self.assertNotIn("ECI", time_dep)

    def test_all_inertial_all_time_invariant(self):
        cs_list = [_eci(), _spher()]
        time_dep, time_inv = csys.categorize_frames_by_time_dependence(cs_list)
        self.assertEqual(time_dep, [])
        self.assertEqual(len(time_inv), 2)

    def test_counts_match_total(self):
        cs_list = [_eci(), _ecef(), _spher(), _body()]
        time_dep, time_inv = csys.categorize_frames_by_time_dependence(cs_list)
        self.assertEqual(len(time_dep) + len(time_inv), len(cs_list))


# ---------------------------------------------------------------------------
# Tests: get_underdefined_frames
# ---------------------------------------------------------------------------

class TestGetUnderdefinedFrames(unittest.TestCase):

    def test_no_underdefined_in_valid_list(self):
        result = csys.get_underdefined_frames([_eci(), _ecef()])
        self.assertEqual(result, [])

    def test_underdefined_frame_detected(self):
        bad = {
            "name": "MISSING_Z",
            "coord_type": "CARTESIAN",
            "axes": {"x": "v.e.", "y": "east"},
        }
        result = csys.get_underdefined_frames([bad])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "MISSING_Z")

    def test_multiple_underdefined_all_returned(self):
        bad1 = {"name": "B1", "coord_type": "CARTESIAN", "axes": {"x": "a"}}
        bad2 = {"name": "B2", "coord_type": "SPHERICAL", "axes": {"r": "b"}}
        result = csys.get_underdefined_frames([bad1, bad2])
        names = [r[0] for r in result]
        self.assertIn("B1", names)
        self.assertIn("B2", names)


# ---------------------------------------------------------------------------
# Tests: validate_parent_frame_chain
# ---------------------------------------------------------------------------

class TestValidateParentFrameChain(unittest.TestCase):

    def test_valid_chain_no_issues(self):
        cs_list = [_eci(), _orbital_cartesian()]
        issues = csys.validate_parent_frame_chain(cs_list)
        self.assertEqual(issues, [])

    def test_unknown_parent_flagged(self):
        orphan = csys.define_coordinate_system(
            name="ORPHAN",
            frame_type="BODY_FIXED",
            coord_type="CARTESIAN",
            origin="spacecraft CoM",
            axes={"x": "roll", "y": "pitch", "z": "yaw"},
            parent_frame="NONEXISTENT_FRAME",
        )
        issues = csys.validate_parent_frame_chain([orphan])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0][0], "ORPHAN")
        self.assertEqual(issues[0][1], "NONEXISTENT_FRAME")

    def test_root_frame_with_no_parent_no_issue(self):
        issues = csys.validate_parent_frame_chain([_eci()])
        self.assertEqual(issues, [])


# ---------------------------------------------------------------------------
# Tests: summarize_registry
# ---------------------------------------------------------------------------

class TestSummarizeRegistry(unittest.TestCase):

    def test_summary_counts_are_correct(self):
        cs_list = [_eci(), _ecef()]
        report = csys.summarize_registry(cs_list)
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["time_dependent_count"], 1)
        self.assertEqual(report["time_invariant_count"], 1)

    def test_summary_compliant_for_valid_registry(self):
        cs_list = [_eci(), _ecef()]
        report = csys.summarize_registry(cs_list)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["underdefined_count"], 0)
        self.assertEqual(report["bad_parent_count"], 0)

    def test_summary_non_compliant_when_underdefined(self):
        bad = {
            "name": "PARTIAL",
            "coord_type": "CARTESIAN",
            "axes": {"x": "v.e."},
            "time_dependent": False,
            "parent_frame": None,
        }
        report = csys.summarize_registry([bad])
        self.assertFalse(report["compliant"])
        self.assertGreater(report["underdefined_count"], 0)
        self.assertIn("PARTIAL", report["underdefined_frames"])

    def test_summary_non_compliant_when_bad_parent(self):
        orphan = csys.define_coordinate_system(
            name="ORPHAN2",
            frame_type="BODY_FIXED",
            coord_type="CARTESIAN",
            origin="CoM",
            axes={"x": "roll", "y": "pitch", "z": "yaw"},
            parent_frame="GHOST",
        )
        report = csys.summarize_registry([orphan])
        self.assertFalse(report["compliant"])
        self.assertEqual(report["bad_parent_count"], 1)

    def test_empty_registry_is_compliant(self):
        report = csys.summarize_registry([])
        self.assertEqual(report["total"], 0)
        self.assertTrue(report["compliant"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
