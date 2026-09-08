"""Contract test for landing-gear-height-sizing.

Exercises the SKILL.md workflow: step 1 fixes the wheelbase and hard point
geometry, step 2 solves the static-ground-line with static_ground_line,
step 3 derives the main and nose gear heights with gear_heights, step 4
reports the achieved clearance and margin of every hard point at both
attitudes with clearance_at_attitude and clearance_margin, step 5 evaluates
the tail strike margin of the solved geometry with tail_strike_angle_deg,
step 6 checks the nose gear static load share with static_load_share, and
step 7 issues the height verdict from the margins and gear heights.
"""

import importlib.util
import math
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LOGIC_PATH = os.path.join(_HERE, "landing_gear_height_sizing_logic.py")
_spec = importlib.util.spec_from_file_location("landing_gear_height_sizing_logic", _LOGIC_PATH)
logic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(logic)

# Worked example (spec anchor anchor_landing_gear_height.py), real module
# outputs.
X_NG = 1.40
X_MG = 7.40
X_CG = 6.80
THETA_ROT = 10.0
Z_NA = -1.00
X_TAIL = 12.40
Z_TAIL = -0.45
TAIL_CLEARANCE_ROT = 0.25
HUB_Z = 0.10
PROP_RADIUS = 1.15
X_PROP = 4.90
PROP_CLEARANCE_LEVEL = 0.20
X_NACELLE = 5.30
Z_NACELLE = -0.60
NACELLE_CLEARANCE_LEVEL = 0.15
NACELLE_CLEARANCE_ROT = 0.15

H_GL_EXPECTED = 1.585491556514
H_MG_EXPECTED = 1.585491556514
H_NG_EXPECTED = 0.585491556514
H_TAIL_CONTACT_EXPECTED = 1.135491556514
THETA_TS_EXPECTED = 12.794763238232


def _worked_points():
    """Step 1 of the SKILL.md workflow: fix the hard point geometry."""
    prop_z = logic.propeller_low_point(HUB_Z, PROP_RADIUS)
    return [
        {
            "station": X_TAIL,
            "z_body": Z_TAIL,
            "clearance_level": 0.0,
            "clearance_rotation": TAIL_CLEARANCE_ROT,
            "name": "tail cone lowest point",
        },
        {
            "station": X_PROP,
            "z_body": prop_z,
            "clearance_level": PROP_CLEARANCE_LEVEL,
            "clearance_rotation": None,
            "name": "propeller disc lowest point",
        },
        {
            "station": X_NACELLE,
            "z_body": Z_NACELLE,
            "clearance_level": NACELLE_CLEARANCE_LEVEL,
            "clearance_rotation": NACELLE_CLEARANCE_ROT,
            "name": "nacelle lowest point",
        },
    ]


class TestStaticGroundLine(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: solve the static-ground-line."""

    def test_solves_worked_ground_line(self):
        h_gl, binding = logic.static_ground_line(_worked_points(), THETA_ROT, X_MG, X_NG)
        self.assertAlmostEqual(h_gl, H_GL_EXPECTED, delta=1e-9)
        self.assertEqual(binding, "tail cone lowest point")

    def test_per_constraint_required_ground_lines(self):
        prop_z = logic.propeller_low_point(HUB_Z, PROP_RADIUS)
        tail_level = logic.required_ground_line(Z_TAIL, X_TAIL, X_MG, 0.0, 0.0)
        tail_rot = logic.required_ground_line(Z_TAIL, X_TAIL, X_MG, THETA_ROT, TAIL_CLEARANCE_ROT)
        prop_level = logic.required_ground_line(prop_z, X_PROP, X_MG, 0.0, PROP_CLEARANCE_LEVEL)
        nacelle_level = logic.required_ground_line(Z_NACELLE, X_NACELLE, X_MG, 0.0, NACELLE_CLEARANCE_LEVEL)
        nacelle_rot = logic.required_ground_line(Z_NACELLE, X_NACELLE, X_MG, THETA_ROT, NACELLE_CLEARANCE_ROT)
        self.assertAlmostEqual(tail_level, 0.450000000000, delta=1e-9)
        self.assertAlmostEqual(tail_rot, 1.585491556514, delta=1e-9)
        self.assertAlmostEqual(prop_level, 1.250000000000, delta=1e-9)
        self.assertAlmostEqual(nacelle_level, 0.750000000000, delta=1e-9)
        self.assertAlmostEqual(nacelle_rot, 0.382027332295, delta=1e-9)

    def test_rejects_non_positive_wheelbase(self):
        with self.assertRaises(ValueError):
            logic.static_ground_line(_worked_points(), THETA_ROT, X_NG, X_NG)

    def test_rejects_rotation_band_edges(self):
        with self.assertRaises(ValueError):
            logic.static_ground_line(_worked_points(), 0.0, X_MG, X_NG)
        with self.assertRaises(ValueError):
            logic.static_ground_line(_worked_points(), 25.5, X_MG, X_NG)

    def test_rejects_empty_points(self):
        with self.assertRaises(ValueError):
            logic.static_ground_line([], THETA_ROT, X_MG, X_NG)

    def test_rejects_negative_clearance_level(self):
        bad_points = _worked_points()
        bad_points[0]["clearance_level"] = -0.1
        with self.assertRaises(ValueError):
            logic.static_ground_line(bad_points, THETA_ROT, X_MG, X_NG)

    def test_rejects_negative_clearance_rotation(self):
        bad_points = _worked_points()
        bad_points[0]["clearance_rotation"] = -0.1
        with self.assertRaises(ValueError):
            logic.static_ground_line(bad_points, THETA_ROT, X_MG, X_NG)


class TestGearHeights(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: derive the main and nose gear heights."""

    def test_worked_gear_heights(self):
        gh = logic.gear_heights(H_GL_EXPECTED, Z_NA)
        self.assertAlmostEqual(gh["main_gear_height"], H_MG_EXPECTED, delta=1e-9)
        self.assertAlmostEqual(gh["nose_gear_height"], H_NG_EXPECTED, delta=1e-9)
        self.assertAlmostEqual(gh["height_difference"], 1.000000000000, delta=1e-9)

    def test_rejects_non_positive_ground_line(self):
        with self.assertRaises(ValueError):
            logic.gear_heights(0.0, Z_NA)

    def test_rejects_nose_gear_height_not_positive(self):
        with self.assertRaises(ValueError):
            logic.gear_heights(1.0, -1.0)


class TestClearancesAndMargins(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: report achieved clearance and margin."""

    def test_tail_rotation_clearance(self):
        c = logic.clearance_at_attitude(Z_TAIL, X_TAIL, X_MG, H_GL_EXPECTED, THETA_ROT)
        self.assertAlmostEqual(c, 0.250000000000, delta=1e-9)

    def test_tail_level_clearance(self):
        c = logic.clearance_at_attitude(Z_TAIL, X_TAIL, X_MG, H_GL_EXPECTED, 0.0)
        self.assertAlmostEqual(c, 1.135491556514, delta=1e-9)

    def test_propeller_level_and_rotation_clearance(self):
        prop_z = logic.propeller_low_point(HUB_Z, PROP_RADIUS)
        c_level = logic.clearance_at_attitude(prop_z, X_PROP, X_MG, H_GL_EXPECTED, 0.0)
        c_rot = logic.clearance_at_attitude(prop_z, X_PROP, X_MG, H_GL_EXPECTED, THETA_ROT)
        self.assertAlmostEqual(c_level, 0.535491556514, delta=1e-9)
        self.assertAlmostEqual(c_rot, 0.961476680695, delta=1e-9)

    def test_nacelle_level_and_rotation_clearance(self):
        c_level = logic.clearance_at_attitude(Z_NACELLE, X_NACELLE, X_MG, H_GL_EXPECTED, 0.0)
        c_rot = logic.clearance_at_attitude(Z_NACELLE, X_NACELLE, X_MG, H_GL_EXPECTED, THETA_ROT)
        self.assertAlmostEqual(c_level, 0.985491556514, delta=1e-9)
        self.assertAlmostEqual(c_rot, 1.335180898483, delta=1e-9)

    def test_margins(self):
        tail_margin = logic.clearance_margin(Z_TAIL, X_TAIL, X_MG, H_GL_EXPECTED, THETA_ROT, TAIL_CLEARANCE_ROT)
        prop_z = logic.propeller_low_point(HUB_Z, PROP_RADIUS)
        prop_margin = logic.clearance_margin(prop_z, X_PROP, X_MG, H_GL_EXPECTED, 0.0, PROP_CLEARANCE_LEVEL)
        nacelle_level_margin = logic.clearance_margin(
            Z_NACELLE, X_NACELLE, X_MG, H_GL_EXPECTED, 0.0, NACELLE_CLEARANCE_LEVEL
        )
        nacelle_rot_margin = logic.clearance_margin(
            Z_NACELLE, X_NACELLE, X_MG, H_GL_EXPECTED, THETA_ROT, NACELLE_CLEARANCE_ROT
        )
        self.assertAlmostEqual(tail_margin, 0.0, delta=1e-12)
        self.assertAlmostEqual(prop_margin, 0.335491556514, delta=1e-9)
        self.assertAlmostEqual(nacelle_level_margin, 0.835491556514, delta=1e-9)
        self.assertAlmostEqual(nacelle_rot_margin, 1.185180898483, delta=1e-9)
        for margin in (tail_margin, prop_margin, nacelle_level_margin, nacelle_rot_margin):
            self.assertGreaterEqual(margin, -1e-12)

    def test_rejects_invalid_clearance_inputs(self):
        with self.assertRaises(ValueError):
            logic.clearance_at_attitude(Z_TAIL, X_TAIL, X_MG, 0.0, THETA_ROT)
        with self.assertRaises(ValueError):
            logic.clearance_margin(Z_TAIL, X_TAIL, X_MG, H_GL_EXPECTED, THETA_ROT, -0.1)
        with self.assertRaises(ValueError):
            logic.required_ground_line(Z_TAIL, X_TAIL, X_MG, THETA_ROT, -0.1)


class TestTailStrikeAngle(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: evaluate the tail strike margin."""

    def test_worked_tail_strike_angle(self):
        theta_ts = logic.tail_strike_angle_deg(H_TAIL_CONTACT_EXPECTED, 5.00)
        self.assertAlmostEqual(theta_ts, THETA_TS_EXPECTED, delta=1e-6)
        margin = theta_ts - THETA_ROT
        self.assertAlmostEqual(margin, 2.794763238232, delta=1e-6)
        self.assertGreater(margin, 0.0)

    def test_rejects_non_positive_contact_height(self):
        with self.assertRaises(ValueError):
            logic.tail_strike_angle_deg(0.0, 5.00)

    def test_rejects_non_positive_tail_arm(self):
        with self.assertRaises(ValueError):
            logic.tail_strike_angle_deg(H_TAIL_CONTACT_EXPECTED, 0.0)


class TestStaticLoadShare(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: check the nose gear static load share."""

    def test_worked_load_share(self):
        nose_share = logic.static_load_share(X_CG, X_MG, X_NG)
        self.assertAlmostEqual(nose_share, 0.100000000000, delta=1e-12)
        main_share = 1.0 - nose_share
        self.assertAlmostEqual(main_share, 0.900000000000, delta=1e-12)
        self.assertAlmostEqual(nose_share + main_share, 1.0, delta=1e-12)

    def test_rejects_non_positive_wheelbase(self):
        with self.assertRaises(ValueError):
            logic.static_load_share(X_CG, X_NG, X_NG)

    def test_rejects_cg_at_gear_stations(self):
        with self.assertRaises(ValueError):
            logic.static_load_share(X_MG, X_MG, X_NG)
        with self.assertRaises(ValueError):
            logic.static_load_share(X_NG, X_MG, X_NG)

    def test_rejects_cg_forward_of_nose_gear(self):
        with self.assertRaises(ValueError):
            logic.static_load_share(0.5, X_MG, X_NG)

    def test_propeller_low_point_worked(self):
        z = logic.propeller_low_point(HUB_Z, PROP_RADIUS)
        self.assertAlmostEqual(z, -1.050000000000, delta=1e-12)

    def test_propeller_low_point_rejects_non_positive_radius(self):
        with self.assertRaises(ValueError):
            logic.propeller_low_point(HUB_Z, -1.0)


class TestIdentities(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: closed-form identities behind the
    height verdict."""

    def test_identity_i1_binding_rotation_round_trip(self):
        theta = THETA_ROT * logic.DEG2RAD
        recomputed = (H_GL_EXPECTED + Z_TAIL) * math.cos(theta) - (X_TAIL - X_MG) * math.sin(theta)
        self.assertAlmostEqual(recomputed, TAIL_CLEARANCE_ROT, delta=1e-9)

    def test_identity_i2_exact_tangent_algebra(self):
        theta = THETA_ROT * logic.DEG2RAD
        lhs = H_TAIL_CONTACT_EXPECTED - TAIL_CLEARANCE_ROT / math.cos(theta)
        rhs = (X_TAIL - X_MG) * math.tan(theta)
        self.assertAlmostEqual(lhs, 0.881634903542, delta=1e-9)
        self.assertAlmostEqual(rhs, 0.881634903542, delta=1e-9)
        self.assertAlmostEqual(lhs, rhs, delta=1e-9)

    def test_identity_i3_small_angle_consistency(self):
        theta = THETA_ROT * logic.DEG2RAD
        exact_rise = H_TAIL_CONTACT_EXPECTED - TAIL_CLEARANCE_ROT
        tangent_rise = (X_TAIL - X_MG) * math.tan(theta)
        diff = exact_rise - tangent_rise
        expected = TAIL_CLEARANCE_ROT * (1.0 / math.cos(theta) - 1.0)
        self.assertAlmostEqual(diff, 0.003856652971, delta=1e-12)
        self.assertAlmostEqual(diff, expected, delta=1e-12)
        self.assertLess(abs(diff) / exact_rise, 0.01)

    def test_identity_i4_sibling_contact_identity(self):
        theta_ts = logic.tail_strike_angle_deg(H_TAIL_CONTACT_EXPECTED, X_TAIL - X_MG)
        c_at_ts = logic.clearance_at_attitude(Z_TAIL, X_TAIL, X_MG, H_GL_EXPECTED, theta_ts)
        self.assertAlmostEqual(c_at_ts, 0.0, delta=1e-9)
        self.assertGreater(theta_ts, THETA_ROT)

    def test_identity_i5_leveling_identity(self):
        gh = logic.gear_heights(H_GL_EXPECTED, Z_NA)
        self.assertAlmostEqual(gh["main_gear_height"], gh["nose_gear_height"] - Z_NA, delta=1e-9)

    def test_identity_i6_forward_point_rise(self):
        prop_z = logic.propeller_low_point(HUB_Z, PROP_RADIUS)
        c_level = logic.clearance_at_attitude(prop_z, X_PROP, X_MG, H_GL_EXPECTED, 0.0)
        c_rot = logic.clearance_at_attitude(prop_z, X_PROP, X_MG, H_GL_EXPECTED, THETA_ROT)
        self.assertGreater(c_rot, c_level)

    def test_level_attitude_round_trip(self):
        for point in _worked_points():
            achieved = logic.clearance_at_attitude(
                point["z_body"], point["station"], X_MG, H_GL_EXPECTED, 0.0
            )
            self.assertAlmostEqual(achieved, H_GL_EXPECTED + point["z_body"], delta=1e-9)
            self.assertGreaterEqual(achieved - point["clearance_level"], -1e-9)


class TestDeterminism(unittest.TestCase):
    """Determinism and module hygiene checks."""

    def test_repeated_solves_match(self):
        h_gl_1, binding_1 = logic.static_ground_line(_worked_points(), THETA_ROT, X_MG, X_NG)
        h_gl_2, binding_2 = logic.static_ground_line(_worked_points(), THETA_ROT, X_MG, X_NG)
        self.assertEqual(binding_1, binding_2)
        self.assertAlmostEqual(h_gl_1, h_gl_2, delta=1e-15)

    def test_module_constants_fixed(self):
        self.assertAlmostEqual(logic.DEG2RAD, math.pi / 180.0, delta=1e-15)
        self.assertEqual(logic.MAX_ROTATION_DEG, 25.0)


if __name__ == "__main__":
    unittest.main()
