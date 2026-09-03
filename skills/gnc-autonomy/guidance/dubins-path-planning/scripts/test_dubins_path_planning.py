"""Offline deterministic contract test for dubins-path-planning.

Runs with: python3 scripts/test_dubins_path_planning.py
Covers arc centers, tangent points, the six CSC/CCC families, the
degenerate straight path, the close-poses (d < 2*rho) CCC feasibility,
symmetry under path reversal and the ValueError rejections.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dubins_path_planning_logic import (  # noqa: E402
    FAMILY_NAMES,
    TURN_LEFT,
    TURN_RIGHT,
    arc_center,
    dubins_candidates,
    dubins_path,
    path_length,
    tangent_points,
)

LEN_TOL = 1e-6
GEO_TOL = 1e-9

START = {"x": 0.0, "y": 0.0, "heading_rad": 0.0}


def pose(x, y, heading_rad):
    return {"x": x, "y": y, "heading_rad": heading_rad}


def reverse(pose_value):
    return pose(pose_value["x"], pose_value["y"],
                pose_value["heading_rad"] + math.pi)


def segment_sum(segments, rho):
    return sum(path_length([segment], rho) for segment in segments)


class TestArcCenter(unittest.TestCase):
    def test_left_center_at_origin_east(self):
        self.assertAlmostEqual(arc_center(0.0, 0.0, 0.0, 10.0,
                                          TURN_LEFT)[0], 0.0, places=9)
        self.assertAlmostEqual(arc_center(0.0, 0.0, 0.0, 10.0,
                                          TURN_LEFT)[1], 10.0, places=9)

    def test_right_center_at_origin_east(self):
        center = arc_center(0.0, 0.0, 0.0, 10.0, TURN_RIGHT)
        self.assertAlmostEqual(center[0], 0.0, places=9)
        self.assertAlmostEqual(center[1], -10.0, places=9)

    def test_left_center_heading_north(self):
        # Heading pi/2 (north): left is west, center at (-rho, 0).
        center = arc_center(0.0, 0.0, math.pi / 2.0, 10.0, TURN_LEFT)
        self.assertAlmostEqual(center[0], -10.0, places=9)
        self.assertAlmostEqual(center[1], 0.0, places=9)

    def test_right_center_heading_north(self):
        center = arc_center(0.0, 0.0, math.pi / 2.0, 10.0, TURN_RIGHT)
        self.assertAlmostEqual(center[0], 10.0, places=9)
        self.assertAlmostEqual(center[1], 0.0, places=9)

    def test_center_radius_distance_property(self):
        for heading in (0.0, 0.7, math.pi / 3.0, 2.4, -1.1):
            for direction in (TURN_LEFT, TURN_RIGHT):
                cx, cy = arc_center(3.0, -2.0, heading, 7.0, direction)
                radius = math.hypot(cx - 3.0, cy + 2.0)
                self.assertAlmostEqual(radius, 7.0, places=9)

    def test_arc_center_valueerror_on_nonpositive_rho(self):
        with self.assertRaises(ValueError):
            arc_center(0.0, 0.0, 0.0, 0.0, TURN_LEFT)
        with self.assertRaises(ValueError):
            arc_center(0.0, 0.0, 0.0, -5.0, TURN_LEFT)

    def test_arc_center_valueerror_on_bad_direction(self):
        with self.assertRaises(ValueError):
            arc_center(0.0, 0.0, 0.0, 10.0, 0)


class TestTangentPoints(unittest.TestCase):
    def test_external_tangent_same_direction(self):
        # LSL circle pair for the straight 100 m case.
        p1, p2 = tangent_points((0.0, 10.0), (100.0, 10.0),
                                TURN_LEFT, TURN_LEFT, 10.0)
        self.assertAlmostEqual(p1[0], 0.0, places=9)
        self.assertAlmostEqual(p1[1], 0.0, places=9)
        self.assertAlmostEqual(p2[0], 100.0, places=9)
        self.assertAlmostEqual(p2[1], 0.0, places=9)
        self.assertAlmostEqual(math.hypot(p1[0], p1[1] - 10.0), 10.0,
                               places=9)
        self.assertAlmostEqual(math.hypot(p2[0] - 100.0, p2[1] - 10.0),
                               10.0, places=9)

    def test_internal_tangent_opposite_direction(self):
        # RSL circle pair for the d = 40 m opposite-heading case.
        p1, p2 = tangent_points((0.0, -10.0), (0.0, 30.0),
                                TURN_RIGHT, TURN_LEFT, 10.0)
        self.assertAlmostEqual(math.hypot(p1[0], p1[1] + 10.0), 10.0,
                               places=9)
        self.assertAlmostEqual(math.hypot(p2[0], p2[1] - 30.0), 10.0,
                               places=9)
        straight = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        self.assertAlmostEqual(straight, math.sqrt(1600.0 - 400.0),
                               places=6)

    def test_internal_tangent_infeasible_separation(self):
        # Centers only 10 apart with rho = 10: no inner tangent.
        with self.assertRaises(ValueError):
            tangent_points((0.0, 10.0), (10.0, 10.0),
                           TURN_LEFT, TURN_RIGHT, 10.0)


class TestDubinsPath(unittest.TestCase):
    def test_straight_100_m(self):
        goal = pose(100.0, 0.0, 0.0)
        path = dubins_path(START, goal, 10.0)
        self.assertAlmostEqual(path["length"], 100.0, places=6)
        self.assertTrue(path["feasible"])
        straight_segments = [seg for seg in path["segments"]
                             if seg["kind"] == "straight"]
        self.assertEqual(len(straight_segments), 1)
        self.assertAlmostEqual(straight_segments[0]["length"], 100.0,
                               places=6)

    def test_straight_100_m_segments_sum_to_total(self):
        goal = pose(100.0, 0.0, 0.0)
        path = dubins_path(START, goal, 10.0)
        self.assertAlmostEqual(path["length"], 100.0, places=6)
        self.assertAlmostEqual(segment_sum(path["segments"], 10.0),
                               path["length"], places=9)

    def test_straight_100_m_waypoint_chain(self):
        goal = pose(100.0, 0.0, 0.0)
        path = dubins_path(START, goal, 10.0)
        waypoints = path["waypoints"]
        self.assertEqual(len(waypoints), 4)
        self.assertAlmostEqual(waypoints[0][0], 0.0, places=9)
        self.assertAlmostEqual(waypoints[-1][0], 100.0, places=9)
        # LSL degenerate straight: left centers sit 10 m off the +x line.
        self.assertAlmostEqual(path["arc_centers"][0][1], 10.0, places=9)
        self.assertAlmostEqual(path["arc_centers"][1][1], 10.0, places=9)
        self.assertAlmostEqual(path["arc_centers"][0][0], 0.0, places=9)
        self.assertAlmostEqual(path["arc_centers"][1][0], 100.0, places=9)

    def test_opposite_heading_d40_total_above_20(self):
        goal = pose(0.0, 40.0, math.pi)
        path = dubins_path(START, goal, 10.0)
        self.assertGreater(path["length"], 20.0)
        self.assertTrue(math.isfinite(path["length"]))

    def test_opposite_heading_d40_segments_sum_equals_total(self):
        goal = pose(0.0, 40.0, math.pi)
        path = dubins_path(START, goal, 10.0)
        self.assertAlmostEqual(segment_sum(path["segments"], 10.0),
                               path["length"], places=9)
        self.assertAlmostEqual(path["length"], 51.415927, places=4)

    def test_six_families_all_present_far_poses(self):
        goal = pose(0.0, 40.0, math.pi)
        candidates = dubins_candidates(START, goal, 10.0)
        self.assertEqual(set(candidates.keys()), set(FAMILY_NAMES))
        # RSR circle centers are 60 apart here, beyond the CCC bound.
        self.assertIsNone(candidates["RLR"])

    def test_close_poses_d_below_two_rho_ccc_feasible(self):
        # d = 10 < 2*rho = 20: no inner tangent for the LSR pairing.
        goal = pose(0.0, 10.0, math.pi / 2.0)
        candidates = dubins_candidates(START, goal, 10.0)
        self.assertIsNone(candidates["LSR"])
        for family in ("RLR", "LRL"):
            candidate = candidates[family]
            self.assertIsNotNone(candidate)
            self.assertGreater(candidate["length"], 10.0)
            self.assertTrue(math.isfinite(candidate["length"]))

    def test_close_poses_returns_feasible_finite_path(self):
        goal = pose(0.0, 10.0, math.pi / 2.0)
        path = dubins_path(START, goal, 10.0)
        self.assertTrue(path["feasible"])
        self.assertIn(path["type"], FAMILY_NAMES)
        self.assertGreater(path["length"], 10.0)
        self.assertTrue(math.isfinite(path["length"]))

    def test_path_type_in_family_names(self):
        goals = [pose(100.0, 0.0, 0.0), pose(0.0, 40.0, math.pi),
                 pose(0.0, 10.0, math.pi / 2.0), pose(-30.0, 20.0, 1.2)]
        for goal in goals:
            path = dubins_path(START, goal, 10.0)
            self.assertIn(path["type"], FAMILY_NAMES)

    def test_symmetry_under_reversal(self):
        goal = pose(0.0, 40.0, math.pi)
        forward = dubins_path(START, goal, 10.0)
        backward = dubins_path(reverse(goal), reverse(START), 10.0)
        self.assertAlmostEqual(forward["length"], backward["length"],
                               places=9)

    def test_symmetry_under_reversal_second_case(self):
        goal = pose(-30.0, 20.0, 1.2)
        forward = dubins_path(START, goal, 7.0)
        backward = dubins_path(reverse(goal), reverse(START), 7.0)
        self.assertAlmostEqual(forward["length"], backward["length"],
                               places=9)

    def test_identical_poses_zero_length(self):
        path = dubins_path(START, dict(START), 10.0)
        self.assertAlmostEqual(path["length"], 0.0, places=9)

    def test_segments_have_positive_lengths(self):
        goal = pose(0.0, 40.0, math.pi)
        path = dubins_path(START, goal, 10.0)
        for segment in path["segments"]:
            self.assertGreaterEqual(segment["length"], 0.0)
            if segment["kind"] == "arc":
                self.assertIn(segment["direction"], (TURN_LEFT, TURN_RIGHT))

    def test_valueerror_rho_zero(self):
        with self.assertRaises(ValueError):
            dubins_path(START, pose(10.0, 0.0, 0.0), 0.0)

    def test_valueerror_rho_negative(self):
        with self.assertRaises(ValueError):
            dubins_path(START, pose(10.0, 0.0, 0.0), -3.0)

    def test_valueerror_missing_key(self):
        with self.assertRaises(ValueError):
            dubins_path({"x": 0.0, "y": 0.0}, pose(10.0, 0.0, 0.0), 10.0)
        with self.assertRaises(ValueError):
            dubins_path(START, {"x": 10.0, "heading_rad": 0.0}, 10.0)

    def test_valueerror_nonfinite_x(self):
        with self.assertRaises(ValueError):
            dubins_path(pose(float("nan"), 0.0, 0.0),
                        pose(10.0, 0.0, 0.0), 10.0)

    def test_valueerror_nonfinite_heading(self):
        with self.assertRaises(ValueError):
            dubins_path(START, pose(10.0, 0.0, float("inf")), 10.0)

    def test_valueerror_nonfinite_rho(self):
        with self.assertRaises(ValueError):
            dubins_path(START, pose(10.0, 0.0, 0.0), float("nan"))


class TestPathStitching(unittest.TestCase):
    """Analytically integrate every segment from the start pose and
    assert the path arrives at the goal pose (position and heading)."""

    def _stitch(self, path):
        x = 0.0
        y = 0.0
        heading = 0.0
        centers = list(path["arc_centers"])
        waypoints = list(path["waypoints"])
        self.assertAlmostEqual(waypoints[0][0], 0.0, places=9)
        self.assertAlmostEqual(waypoints[0][1], 0.0, places=9)
        point_index = 1
        for segment in path["segments"]:
            if segment["kind"] == "straight":
                length = segment["length"]
                self.assertAlmostEqual(
                    waypoints[point_index][0],
                    x + length * math.cos(heading), places=6)
                self.assertAlmostEqual(
                    waypoints[point_index][1],
                    y + length * math.sin(heading), places=6)
                x += length * math.cos(heading)
                y += length * math.sin(heading)
            else:
                direction = segment["direction"]
                angle = segment["angle_rad"]
                cx, cy = centers.pop(0)
                end_heading = heading + direction * angle
                radius = math.hypot(x - cx, y - cy)
                self.assertAlmostEqual(radius, 10.0, places=6)
                x = cx + 10.0 * direction * math.sin(end_heading)
                y = cy - 10.0 * direction * math.cos(end_heading)
                heading = end_heading
                self.assertAlmostEqual(waypoints[point_index][0], x,
                                       places=6)
                self.assertAlmostEqual(waypoints[point_index][1], y,
                                       places=6)
            point_index += 1
        return x, y, heading

    def test_stitch_straight_100_m(self):
        goal = pose(100.0, 0.0, 0.0)
        x, y, heading = self._stitch(dubins_path(START, goal, 10.0))
        self.assertAlmostEqual(x, 100.0, places=6)
        self.assertAlmostEqual(y, 0.0, places=6)
        self.assertAlmostEqual(heading % (2.0 * math.pi), 0.0, places=6)

    def test_stitch_opposite_heading_d40(self):
        goal = pose(0.0, 40.0, math.pi)
        x, y, heading = self._stitch(dubins_path(START, goal, 10.0))
        self.assertAlmostEqual(x, 0.0, places=6)
        self.assertAlmostEqual(y, 40.0, places=6)
        self.assertAlmostEqual(heading % (2.0 * math.pi), math.pi,
                               places=6)

    def test_stitch_close_poses_every_feasible_family(self):
        goal = pose(0.0, 10.0, math.pi / 2.0)
        candidates = dubins_candidates(START, goal, 10.0)
        for family, candidate in candidates.items():
            if candidate is None:
                continue
            x, y, heading = self._stitch(candidate)
            self.assertAlmostEqual(x, 0.0, places=6)
            self.assertAlmostEqual(y, 10.0, places=6)
            self.assertAlmostEqual(heading % (2.0 * math.pi),
                                   math.pi / 2.0, places=6)


if __name__ == "__main__":
    unittest.main()
