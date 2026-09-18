"""Contract tests for the cross-cut and tape adhesion verification logic."""

import unittest

from q7031_adhesion_verification_logic import (
    CROSSCUT_BAND_EDGES,
    DEFAULT_CUTS_PER_DIRECTION,
    MAX_LATTICE_DFT_UM,
    RATING_TOLERANCE,
    assess_adhesion,
    assess_test_area,
    crosscut_rating,
    cut_spacing_mm,
    detached_area_percent,
    lattice_square_count,
    pull_off_verdict,
    validate_positive,
)


def area(**overrides):
    base = {"name": "panel-a", "dft_um": 45.0, "detached_squares": 0}
    base.update(overrides)
    return base


class ValidatorTests(unittest.TestCase):
    def test_positive_returns_float(self):
        self.assertEqual(validate_positive(45, "x"), 45.0)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "x")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "x")


class CutSpacingTests(unittest.TestCase):
    def test_thin_film_on_a_hard_substrate_takes_one_millimetre(self):
        self.assertAlmostEqual(cut_spacing_mm(45.0, "hard"), 1.0, places=12)

    def test_thin_film_on_a_soft_substrate_takes_two_millimetres(self):
        self.assertAlmostEqual(cut_spacing_mm(45.0, "soft"), 2.0, places=12)

    def test_exactly_on_the_first_edge_keeps_the_thin_spacing(self):
        self.assertAlmostEqual(cut_spacing_mm(60.0, "hard"), 1.0, places=12)

    def test_mid_range_film_takes_two_millimetres_on_either_substrate(self):
        self.assertAlmostEqual(cut_spacing_mm(90.0, "hard"), 2.0, places=12)
        self.assertAlmostEqual(cut_spacing_mm(90.0, "soft"), 2.0, places=12)

    def test_thick_film_takes_three_millimetres(self):
        self.assertAlmostEqual(cut_spacing_mm(200.0, "hard"), 3.0, places=12)

    def test_film_exactly_on_the_lattice_limit_is_still_cuttable(self):
        self.assertAlmostEqual(cut_spacing_mm(MAX_LATTICE_DFT_UM), 3.0, places=12)

    def test_film_over_the_lattice_limit_is_refused(self):
        with self.assertRaises(ValueError):
            cut_spacing_mm(400.0)

    def test_unknown_substrate_rejected(self):
        with self.assertRaises(ValueError):
            cut_spacing_mm(45.0, "springy")

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            cut_spacing_mm(0.0)


class LatticeTests(unittest.TestCase):
    def test_six_cuts_give_twenty_five_squares(self):
        self.assertEqual(lattice_square_count(6), 25)

    def test_eleven_cuts_give_a_hundred_squares(self):
        self.assertEqual(lattice_square_count(11), 100)

    def test_default_cut_count_is_six(self):
        self.assertEqual(lattice_square_count(), lattice_square_count(DEFAULT_CUTS_PER_DIRECTION))

    def test_one_cut_bounds_nothing(self):
        with self.assertRaises(ValueError):
            lattice_square_count(1)

    def test_float_cut_count_rejected(self):
        with self.assertRaises(ValueError):
            lattice_square_count(6.0)


class DetachedAreaTests(unittest.TestCase):
    def test_nothing_detached_is_zero_percent(self):
        self.assertAlmostEqual(detached_area_percent(0, 25), 0.0, places=12)

    def test_one_of_twenty_five_squares(self):
        self.assertAlmostEqual(detached_area_percent(1, 25), 4.0, places=12)

    def test_partial_squares_count_by_their_fraction(self):
        self.assertAlmostEqual(
            detached_area_percent(0, 25, [0.5, 0.5]), 4.0, places=12
        )

    def test_whole_and_partial_squares_add(self):
        self.assertAlmostEqual(
            detached_area_percent(2, 25, [0.5]), 10.0, places=12
        )

    def test_a_whole_square_cannot_be_a_partial_fraction(self):
        with self.assertRaises(ValueError):
            detached_area_percent(0, 25, [1.0])

    def test_more_affected_squares_than_the_lattice_holds_rejected(self):
        with self.assertRaises(ValueError):
            detached_area_percent(26, 25)

    def test_negative_detached_count_rejected(self):
        with self.assertRaises(ValueError):
            detached_area_percent(-1, 25)

    def test_empty_lattice_rejected(self):
        with self.assertRaises(ValueError):
            detached_area_percent(0, 0)


class RatingTests(unittest.TestCase):
    def test_clean_lattice_is_rating_zero(self):
        self.assertEqual(crosscut_rating(0.0), 0)

    def test_exactly_five_percent_is_rating_one(self):
        self.assertEqual(crosscut_rating(5.0), 1)

    def test_just_over_five_percent_is_rating_two(self):
        self.assertEqual(crosscut_rating(5.5), 2)

    def test_exactly_fifteen_percent_is_rating_two(self):
        self.assertEqual(crosscut_rating(15.0), 2)

    def test_exactly_thirty_five_percent_is_rating_three(self):
        self.assertEqual(crosscut_rating(35.0), 3)

    def test_exactly_sixty_five_percent_is_rating_four(self):
        self.assertEqual(crosscut_rating(65.0), 4)

    def test_beyond_the_last_edge_is_rating_five(self):
        self.assertEqual(crosscut_rating(90.0), len(CROSSCUT_BAND_EDGES))

    def test_one_square_of_twenty_five_lands_in_rating_one(self):
        percent = detached_area_percent(1, 25)
        self.assertAlmostEqual(percent, 4.0, places=12)
        self.assertEqual(crosscut_rating(percent), 1)

    def test_percentage_over_a_hundred_rejected(self):
        with self.assertRaises(ValueError):
            crosscut_rating(101.0)

    def test_negative_percentage_rejected(self):
        with self.assertRaises(ValueError):
            crosscut_rating(-1.0)


class TestAreaTests(unittest.TestCase):
    def test_clean_area_passes_at_rating_zero(self):
        record = assess_test_area(area(), 0)
        self.assertEqual(record["rating"], 0)
        self.assertTrue(record["passed"])

    def test_spacing_is_reported_with_the_result(self):
        self.assertAlmostEqual(assess_test_area(area(), 1)["cut_spacing_mm"], 1.0, places=12)

    def test_lattice_size_follows_the_cut_count(self):
        record = assess_test_area(area(cuts_per_direction=11), 1)
        self.assertEqual(record["lattice_squares"], 100)

    def test_one_detached_square_still_passes_at_rating_one(self):
        record = assess_test_area(area(detached_squares=1), 1)
        self.assertEqual(record["rating"], 1)
        self.assertTrue(record["passed"])

    def test_heavy_detachment_fails_the_allowed_rating(self):
        record = assess_test_area(area(detached_squares=12), 1)
        self.assertFalse(record["passed"])
        self.assertEqual(len(record["findings"]), 1)

    def test_missing_area_key_rejected(self):
        broken = area()
        del broken["dft_um"]
        with self.assertRaises(ValueError):
            assess_test_area(broken, 1)

    def test_max_rating_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_area(area(), 9)

    def test_float_max_rating_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_area(area(), 1.0)


class PullOffTests(unittest.TestCase):
    def test_strength_above_the_minimum_is_met(self):
        self.assertTrue(pull_off_verdict(3.5, 2.0)["met"])

    def test_strength_exactly_on_the_minimum_is_met(self):
        record = pull_off_verdict(2.0, 2.0)
        self.assertTrue(record["met"])
        self.assertEqual(record["findings"], [])

    def test_strength_below_the_minimum_is_a_finding(self):
        record = pull_off_verdict(1.0, 2.0)
        self.assertFalse(record["met"])
        self.assertEqual(len(record["findings"]), 1)

    def test_negative_strength_rejected(self):
        with self.assertRaises(ValueError):
            pull_off_verdict(-1.0, 2.0)

    def test_zero_minimum_rejected(self):
        with self.assertRaises(ValueError):
            pull_off_verdict(3.0, 0.0)


class AssessAdhesionTests(unittest.TestCase):
    def test_single_clean_area_verifies(self):
        result = assess_adhesion({"test_areas": [area()], "max_rating": 1})
        self.assertTrue(result["adhesion_verified"])
        self.assertEqual(result["worst_rating"], 0)

    def test_worst_area_governs_the_result(self):
        result = assess_adhesion(
            {
                "test_areas": [area(name="a"), area(name="b", detached_squares=12)],
                "max_rating": 1,
            }
        )
        self.assertFalse(result["adhesion_verified"])
        self.assertEqual(result["worst_rating"], 4)

    def test_too_few_test_areas_is_a_finding(self):
        result = assess_adhesion(
            {"test_areas": [area()], "max_rating": 1, "min_test_areas": 3}
        )
        self.assertFalse(result["coverage_met"])

    def test_enough_test_areas_meets_coverage(self):
        result = assess_adhesion(
            {
                "test_areas": [area(name="a"), area(name="b"), area(name="c")],
                "max_rating": 1,
                "min_test_areas": 3,
            }
        )
        self.assertTrue(result["coverage_met"])

    def test_scattered_ratings_breach_the_spread_limit(self):
        result = assess_adhesion(
            {
                "test_areas": [area(name="a"), area(name="b", detached_squares=12)],
                "max_rating": 4,
                "max_rating_spread": 1,
            }
        )
        self.assertFalse(result["spread_within_limit"])
        self.assertFalse(result["adhesion_verified"])

    def test_consistent_ratings_pass_the_spread_limit(self):
        result = assess_adhesion(
            {
                "test_areas": [area(name="a"), area(name="b", detached_squares=1)],
                "max_rating": 1,
                "max_rating_spread": 1,
            }
        )
        self.assertTrue(result["spread_within_limit"])

    def test_pull_off_result_joins_the_verdict(self):
        result = assess_adhesion(
            {
                "test_areas": [area()],
                "max_rating": 1,
                "pull_off_strength_mpa": 1.0,
                "min_pull_off_mpa": 2.0,
            }
        )
        self.assertFalse(result["adhesion_verified"])
        self.assertIsNotNone(result["pull_off"])

    def test_pull_off_needs_its_minimum(self):
        with self.assertRaises(ValueError):
            assess_adhesion(
                {"test_areas": [area()], "max_rating": 1, "pull_off_strength_mpa": 3.0}
            )

    def test_empty_test_area_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_adhesion({"test_areas": [], "max_rating": 1})

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_adhesion({"test_areas": [area()]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_adhesion([area()])

    def test_bad_minimum_area_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_adhesion({"test_areas": [area()], "max_rating": 1, "min_test_areas": 0})

    def test_tolerance_is_small(self):
        self.assertAlmostEqual(RATING_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=1)
