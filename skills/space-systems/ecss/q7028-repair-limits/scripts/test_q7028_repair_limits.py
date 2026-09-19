"""Contract tests for the board repair-limit logic."""

import unittest

from q7028_repair_limits_logic import (
    MAX_REPAIRS_PER_CONDUCTOR,
    MIN_SEPARATION_OPPOSITE_SIDES_MM,
    MIN_SEPARATION_SAME_SIDE_MM,
    assess_repair_limits,
    conductor_violations,
    density_allowance,
    minimum_separation_mm,
    normalise_sites,
    proximity_violations,
    repair_allowance,
    repair_density_per_100_cm2,
    separation_mm,
)


def site(site_id, x, y, side="top", conductor=None):
    entry = {"id": site_id, "side": side, "x_mm": x, "y_mm": y}
    if conductor is not None:
        entry["conductor"] = conductor
    return entry


def base_board(**overrides):
    """A 200 cm2 board carrying two well-separated repairs at level 2."""
    board = {
        "board_area_cm2": 200.0,
        "assurance_level": 2,
        "existing_repairs": [
            site("r1", 0.0, 0.0, "top", "net-a"),
            site("r2", 40.0, 0.0, "top", "net-b"),
        ],
        "proposed_repairs": [],
    }
    board.update(overrides)
    return board


class AllowanceTests(unittest.TestCase):
    def test_level_two_carries_an_allowance(self):
        self.assertEqual(repair_allowance(2), 5)

    def test_the_strictest_level_allows_the_fewest_repairs(self):
        self.assertLess(repair_allowance(1), repair_allowance(3))

    def test_the_strictest_level_allows_the_lowest_density(self):
        self.assertLess(density_allowance(1), density_allowance(3))

    def test_unknown_assurance_level_rejected(self):
        with self.assertRaises(ValueError):
            repair_allowance(9)

    def test_non_integer_assurance_level_rejected(self):
        with self.assertRaises(ValueError):
            density_allowance("2")


class DensityTests(unittest.TestCase):
    def test_density_is_repairs_per_hundred_square_centimetres(self):
        self.assertAlmostEqual(repair_density_per_100_cm2(4, 200.0), 2.0, places=9)

    def test_a_bare_board_has_no_density(self):
        self.assertAlmostEqual(repair_density_per_100_cm2(0, 200.0), 0.0, places=9)

    def test_a_smaller_board_reaches_the_density_sooner(self):
        self.assertGreater(
            repair_density_per_100_cm2(3, 100.0), repair_density_per_100_cm2(3, 400.0)
        )

    def test_zero_board_area_rejected(self):
        with self.assertRaises(ValueError):
            repair_density_per_100_cm2(3, 0.0)

    def test_negative_repair_count_rejected(self):
        with self.assertRaises(ValueError):
            repair_density_per_100_cm2(-1, 200.0)


class SiteTests(unittest.TestCase):
    def test_sites_normalise_with_a_status(self):
        sites = normalise_sites([site("r1", 0.0, 0.0)], "proposed")
        self.assertEqual(sites[0]["status"], "proposed")

    def test_site_identity_and_side_are_lowercased(self):
        sites = normalise_sites([{"id": "R1", "side": "Top", "x_mm": 0.0, "y_mm": 0.0}])
        self.assertEqual(sites[0]["id"], "r1")
        self.assertEqual(sites[0]["side"], "top")

    def test_a_site_with_no_conductor_records_none(self):
        self.assertIsNone(normalise_sites([site("r1", 0.0, 0.0)])[0]["conductor"])

    def test_a_site_missing_a_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            normalise_sites([{"id": "r1", "side": "top", "x_mm": 0.0}])

    def test_a_site_on_an_unknown_side_rejected(self):
        with self.assertRaises(ValueError):
            normalise_sites([site("r1", 0.0, 0.0, "edge")])

    def test_a_mapping_of_sites_rejected(self):
        with self.assertRaises(ValueError):
            normalise_sites({"r1": (0.0, 0.0)})


class SeparationTests(unittest.TestCase):
    def test_separation_is_the_in_plane_distance(self):
        self.assertAlmostEqual(
            separation_mm(site("a", 0.0, 0.0), site("b", 3.0, 4.0)), 5.0, places=9
        )

    def test_separation_is_symmetric(self):
        first = separation_mm(site("a", 0.0, 0.0), site("b", 12.0, 5.0))
        second = separation_mm(site("b", 12.0, 5.0), site("a", 0.0, 0.0))
        self.assertAlmostEqual(first, second, places=9)

    def test_two_sites_on_one_face_take_the_longer_minimum(self):
        self.assertAlmostEqual(
            minimum_separation_mm(site("a", 0, 0, "top"), site("b", 0, 0, "top")),
            MIN_SEPARATION_SAME_SIDE_MM,
            places=9,
        )

    def test_two_sites_on_opposite_faces_take_the_shorter_minimum(self):
        self.assertAlmostEqual(
            minimum_separation_mm(site("a", 0, 0, "top"), site("b", 0, 0, "bottom")),
            MIN_SEPARATION_OPPOSITE_SIDES_MM,
            places=9,
        )

    def test_an_unknown_side_in_a_pair_rejected(self):
        with self.assertRaises(ValueError):
            minimum_separation_mm(site("a", 0, 0, "top"), {"side": "edge"})

    def test_well_separated_sites_report_nothing(self):
        sites = normalise_sites([site("r1", 0.0, 0.0), site("r2", 40.0, 0.0)])
        self.assertEqual(proximity_violations(sites), [])

    def test_a_pair_exactly_on_the_minimum_is_acceptable(self):
        sites = normalise_sites(
            [site("r1", 0.0, 0.0), site("r2", MIN_SEPARATION_SAME_SIDE_MM, 0.0)]
        )
        self.assertEqual(proximity_violations(sites), [])

    def test_a_crowded_pair_on_one_face_is_reported(self):
        sites = normalise_sites([site("r1", 0.0, 0.0), site("r2", 4.0, 0.0)])
        violations = proximity_violations(sites)
        self.assertEqual(len(violations), 1)
        self.assertTrue(violations[0]["same_side"])

    def test_the_same_spacing_passes_across_the_board(self):
        sites = normalise_sites(
            [site("r1", 0.0, 0.0, "top"), site("r2", 7.0, 0.0, "bottom")]
        )
        self.assertEqual(proximity_violations(sites), [])

    def test_every_crowded_pair_is_reported_not_just_the_first(self):
        sites = normalise_sites(
            [site("r1", 0.0, 0.0), site("r2", 2.0, 0.0), site("r3", 4.0, 0.0)]
        )
        self.assertEqual(len(proximity_violations(sites)), 3)


class ConductorTests(unittest.TestCase):
    def test_one_repair_per_conductor_is_clean(self):
        sites = normalise_sites(
            [site("r1", 0.0, 0.0, "top", "net-a"), site("r2", 40.0, 0.0, "top", "net-b")]
        )
        self.assertEqual(conductor_violations(sites), [])

    def test_a_twice_repaired_conductor_is_reported(self):
        sites = normalise_sites(
            [site("r1", 0.0, 0.0, "top", "net-a"), site("r2", 40.0, 0.0, "top", "net-a")]
        )
        violations = conductor_violations(sites)
        self.assertEqual(violations[0]["conductor"], "net-a")
        self.assertGreater(violations[0]["count"], MAX_REPAIRS_PER_CONDUCTOR)

    def test_sites_with_no_conductor_are_not_grouped_together(self):
        sites = normalise_sites([site("r1", 0.0, 0.0), site("r2", 40.0, 0.0)])
        self.assertEqual(conductor_violations(sites), [])


class AssessmentTests(unittest.TestCase):
    def test_a_lightly_repaired_board_is_within_limits(self):
        result = assess_repair_limits(base_board())
        self.assertTrue(result["within_limits"])
        self.assertEqual(result["findings"], [])

    def test_the_counts_and_the_density_are_reported(self):
        result = assess_repair_limits(base_board())
        self.assertEqual(result["total_count"], 2)
        self.assertAlmostEqual(result["density_per_100_cm2"], 1.0, places=9)

    def test_a_board_exactly_on_its_density_allowance_stays_within_limits(self):
        board = base_board(
            existing_repairs=[
                site("r1", 0.0, 0.0),
                site("r2", 40.0, 0.0),
                site("r3", 80.0, 0.0),
                site("r4", 120.0, 0.0),
            ]
        )
        result = assess_repair_limits(board)
        self.assertAlmostEqual(result["density_per_100_cm2"], density_allowance(2), places=9)
        self.assertTrue(result["within_limits"])

    def test_too_many_repairs_exceed_the_allowance(self):
        board = base_board(
            existing_repairs=[site("r%d" % i, i * 40.0, 0.0) for i in range(6)],
            board_area_cm2=2000.0,
        )
        result = assess_repair_limits(board)
        self.assertFalse(result["within_limits"])
        self.assertTrue(any("exceed the allowance" in f for f in result["findings"]))

    def test_a_small_crowded_board_breaches_the_density_first(self):
        board = base_board(
            board_area_cm2=50.0,
            existing_repairs=[site("r1", 0.0, 0.0), site("r2", 40.0, 0.0)],
        )
        result = assess_repair_limits(board)
        self.assertFalse(result["within_limits"])
        self.assertEqual(result["governing_limit"], "repair-density")

    def test_a_proposal_that_crowds_an_existing_site_is_implicated(self):
        board = base_board(proposed_repairs=[site("p1", 3.0, 0.0, "top", "net-c")])
        result = assess_repair_limits(board)
        self.assertFalse(result["within_limits"])
        self.assertTrue(result["proposal_implicated"])

    def test_a_proposal_clear_of_everything_is_not_implicated(self):
        board = base_board(proposed_repairs=[site("p1", 80.0, 0.0, "top", "net-c")])
        result = assess_repair_limits(board)
        self.assertTrue(result["within_limits"])
        self.assertFalse(result["proposal_implicated"])

    def test_a_proposal_on_an_already_repaired_conductor_is_implicated(self):
        board = base_board(proposed_repairs=[site("p1", 80.0, 0.0, "top", "net-a")])
        result = assess_repair_limits(board)
        self.assertFalse(result["within_limits"])
        self.assertTrue(result["proposal_implicated"])

    def test_the_closest_pair_is_reported(self):
        result = assess_repair_limits(base_board())
        self.assertEqual(set(result["closest_pair"]["sites"]), {"r1", "r2"})
        self.assertAlmostEqual(result["closest_pair"]["separation_mm"], 40.0, places=9)

    def test_a_single_repair_has_no_closest_pair(self):
        board = base_board(existing_repairs=[site("r1", 0.0, 0.0)])
        self.assertIsNone(assess_repair_limits(board)["closest_pair"])

    def test_the_tighter_assurance_level_can_refuse_the_same_board(self):
        board = base_board(
            assurance_level=1,
            existing_repairs=[site("r1", 0.0, 0.0), site("r2", 40.0, 0.0), site("r3", 80.0, 0.0)],
        )
        self.assertFalse(assess_repair_limits(board)["within_limits"])
        relaxed = dict(board, assurance_level=2)
        self.assertTrue(assess_repair_limits(relaxed)["within_limits"])

    def test_a_reused_site_identity_rejected(self):
        board = base_board(proposed_repairs=[site("r1", 80.0, 0.0)])
        with self.assertRaises(ValueError):
            assess_repair_limits(board)

    def test_a_board_with_no_area_rejected(self):
        board = base_board()
        del board["board_area_cm2"]
        with self.assertRaises(ValueError):
            assess_repair_limits(board)

    def test_non_mapping_board_rejected(self):
        with self.assertRaises(ValueError):
            assess_repair_limits("PCA-4471-02")


if __name__ == "__main__":
    unittest.main()
