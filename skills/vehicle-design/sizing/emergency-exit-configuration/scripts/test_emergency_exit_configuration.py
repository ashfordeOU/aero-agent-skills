"""Contract test for emergency-exit-configuration (vehicle-design/sizing).

Exercises the emergency exit configuration workflow of SKILL.md against
the pure stdlib logic module emergency_exit_configuration_logic.py. Step 2
of the SKILL.md workflow, the exit-type lookup of the module constant
table, is exercised by TestExitTypeLookup; step 3, the per-side capacity
sum, by TestPerSideCapacity; step 4, the capacity-band rule and the
required per-side exit set, by TestRequiredExitSet; step 5, the
exit-count-check adequacy verdict with the failing-rule list, by
TestExitCountCheck; step 6, the adjacent-exit spacing rule with the
60 ft limit and the implied maximum seat distance to an exit, by
TestExitPlacement; step 7, the aggregate evacuation demand ratio, by
TestEvacuationDemandRatio. Offline, deterministic, stdlib only.

Run: python3 scripts/test_emergency_exit_configuration.py
"""

import unittest

from emergency_exit_configuration_logic import (
    MAX_ADJACENT_EXIT_SPACING_FT,
    evacuation_demand_ratio,
    exit_count_check,
    exit_placement_check,
    exit_type_dimensions,
    required_exits_by_capacity,
    side_exit_capacity,
)

TYPE_A = {"width_in": 42, "height_in": 72, "seating_credit": 110}
TYPE_B = {"width_in": 32, "height_in": 72, "seating_credit": 75}
TYPE_C = {"width_in": 30, "height_in": 48, "seating_credit": 55}
TYPE_I = {"width_in": 24, "height_in": 48, "seating_credit": 45}
TYPE_II = {"width_in": 20, "height_in": 44, "seating_credit": 40}
TYPE_III = {"width_in": 20, "height_in": 36, "seating_credit": 35}
TYPE_IV = {"width_in": 19, "height_in": 26, "seating_credit": 9}


class TestExitTypeLookup(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the exit-type lookup."""

    def test_exit_type_dimensions_type_a_opening_and_credit(self):
        """Step 2 exit-type lookup: a Type A exit opens 42 by 72 inches and
        credits 110 seats, the largest per-exit seating credit."""
        self.assertEqual(exit_type_dimensions("A"), TYPE_A)

    def test_exit_type_dimensions_full_constant_table(self):
        """Step 2 exit-type lookup: all seven types of the constant table,
        Type B, C, I, II, III and IV with their openings and credits."""
        expected = {
            "A": TYPE_A,
            "B": TYPE_B,
            "C": TYPE_C,
            "I": TYPE_I,
            "II": TYPE_II,
            "III": TYPE_III,
            "IV": TYPE_IV,
        }
        for exit_type, dims in expected.items():
            self.assertEqual(exit_type_dimensions(exit_type), dims,
                             msg="type %s" % exit_type)
        self.assertEqual(
            sorted(exit_type_dimensions("B")),
            ["height_in", "seating_credit", "width_in"])

    def test_exit_type_dimensions_unknown_type_value_error(self):
        """Step 2 exit-type lookup: an unknown type id such as F raises
        ValueError instead of fabricating an opening or a credit."""
        with self.assertRaises(ValueError):
            exit_type_dimensions("F")


class TestPerSideCapacity(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the per-side capacity sum."""

    def test_side_exit_capacity_type_a_and_type_c(self):
        """Step 3 per-side capacity sum: a Type A door (110 seats) plus a
        Type C door (55 seats) credit 165 seats on one side."""
        self.assertEqual(side_exit_capacity(["A", "C"]), 165)

    def test_side_exit_capacity_two_type_a_identity(self):
        """Step 3 per-side capacity sum: two Type A exits per side credit
        220 seats, the identity the spec lists for the worked example."""
        self.assertEqual(side_exit_capacity(["A", "A"]), 220)

    def test_side_exit_capacity_single_type_iv_identity(self):
        """Step 3 per-side capacity sum: a single Type IV exit credits
        exactly 9 seats, matching the 1 to 9 seat band coverage."""
        self.assertEqual(side_exit_capacity(["IV"]), 9)


class TestRequiredExitSet(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the capacity-band rule and the
    required per-side exit set."""

    def test_required_exits_nine_seats_single_type_iv(self):
        """Step 4 capacity-band rule: 9 seats fall in the 1-9 band and the
        required per-side exit set is one Type IV, credit exactly 9 with
        zero excess seats."""
        result = required_exits_by_capacity(9)
        self.assertEqual(result["band"], "1-9")
        self.assertEqual(result["required_per_side"], ["IV"])
        self.assertEqual(result["covered"], 9)
        self.assertEqual(result["excess_seats"], 0)

    def test_required_exits_sixty_seats_type_i_and_type_iii(self):
        """Step 4 capacity-band rule: 60 seats fall in the 41-110 band and
        the required per-side exit set is one Type I floor-level exit plus
        one Type III overwing exit, covering 80 seats with 20 excess."""
        result = required_exits_by_capacity(60)
        self.assertEqual(result["band"], "41-110")
        self.assertEqual(result["required_per_side"], ["I", "III"])
        self.assertEqual(result["covered"], 80)
        self.assertEqual(result["excess_seats"], 20)

    def test_required_exits_180_seats_type_a_and_type_b(self):
        """Step 4 capacity-band rule: 180 seats fall in the over-110 band
        and the required per-side exit set is a Type A plus a Type B,
        covering 185 seats with 5 excess."""
        result = required_exits_by_capacity(180)
        self.assertEqual(result["band"], ">110")
        self.assertEqual(result["required_per_side"], ["A", "B"])
        self.assertEqual(result["covered"], 185)
        self.assertEqual(result["excess_seats"], 5)

    def test_required_exits_853_seats_eight_type_a(self):
        """Step 4 capacity-band rule: 853 seats need eight Type A exits per
        side (covered 880, excess 27), the enumeration cap case."""
        result = required_exits_by_capacity(853)
        self.assertEqual(result["required_per_side"], ["A"] * 8)
        self.assertEqual(result["covered"], 880)
        self.assertEqual(result["excess_seats"], 27)

    def test_required_exits_band_boundary_mapping(self):
        """Step 4 capacity-band rule: the band labels map 9 to 1-9, 19 to
        10-19, 40 to 20-40, 110 to 41-110 and 111 to over-110."""
        for capacity, band in ((9, "1-9"), (19, "10-19"), (40, "20-40"),
                               (110, "41-110"), (111, ">110")):
            self.assertEqual(required_exits_by_capacity(capacity)["band"], band)

    def test_required_exits_dict_keys_covered_excess_identity(self):
        """Step 4 required per-side exit set: the result dict carries the
        documented keys and covered minus the capacity equals the excess,
        the identity behind the demand-side verdict."""
        result = required_exits_by_capacity(180)
        self.assertEqual(
            sorted(result),
            ["band", "covered", "excess_seats", "min_exits_per_side",
             "required_per_side"])
        self.assertEqual(result["covered"] - 180, result["excess_seats"])
        # Required sets are reported largest type first.
        ranks = {"IV": 0, "III": 1, "II": 2, "I": 3, "C": 4, "B": 5, "A": 6}
        required = result["required_per_side"]
        self.assertTrue(all(ranks[a] >= ranks[b]
                            for a, b in zip(required, required[1:])))

    def test_required_exits_capacity_below_one_value_error(self):
        """Step 4 capacity-band rule: a passenger capacity of 0 raises
        ValueError (non-physical input rejection)."""
        with self.assertRaises(ValueError):
            required_exits_by_capacity(0)
        with self.assertRaises(ValueError):
            required_exits_by_capacity(-5)

    def test_required_exits_above_per_side_ceiling_value_error(self):
        """Step 4 required per-side exit set: a capacity beyond 12 Type A
        exits per side (1320 seats) raises ValueError instead of silently
        under-sizing the exit set."""
        with self.assertRaises(ValueError):
            required_exits_by_capacity(1500)


class TestExitCountCheck(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the exit-count-check adequacy
    verdict with the per-side failing-rule list."""

    def test_exit_count_check_180_ac_capacity_failure(self):
        """Step 5 exit-count-check: Type A and Type C doors on each side of
        the 180-seat cabin credit 165 seats per side, fail capacity with
        shortfall 15, and the verdict is not adequate."""
        result = exit_count_check(180, ["A", "C"], ["A", "C"])
        self.assertFalse(result["adequate"])
        self.assertEqual(result["left_capacity"], 165)
        self.assertEqual(result["left_failures"], ["capacity"])
        self.assertEqual(result["right_failures"], ["capacity"])
        self.assertEqual(result["shortfall"], 15)

    def test_exit_count_check_180_ab_adequate(self):
        """Step 5 exit-count-check: Type A and Type B doors per side credit
        185 seats, cover the 180-seat cabin on each side alone, and the
        verdict is adequate with no failing rules."""
        result = exit_count_check(180, ["A", "B"], ["A", "B"])
        self.assertTrue(result["adequate"])
        self.assertEqual(result["left_failures"], [])
        self.assertEqual(result["right_failures"], [])
        self.assertEqual(result["shortfall"], 0)

    def test_exit_count_check_60_ci_two_c_rule_failure(self):
        """Step 5 exit-count-check: a Type C door on the 60-seat regional
        forces a second Type C or larger exit on that side, so Type C plus
        Type I fails the two-C-or-larger-when-ABC-installed rule."""
        result = exit_count_check(60, ["C", "I"], ["C", "I"])
        self.assertFalse(result["adequate"])
        self.assertEqual(result["left_failures"],
                         ["two-C-or-larger-when-ABC-installed"])

    def test_exit_count_check_60_cc_adequate(self):
        """Step 5 exit-count-check: two Type C doors per side on the
        60-seat cabin cover 110 seats each side, satisfy the Type C or
        larger pair rule, and the verdict is adequate."""
        result = exit_count_check(60, ["C", "C"], ["C", "C"])
        self.assertTrue(result["adequate"])
        self.assertEqual(result["left_failures"], [])

    def test_exit_count_check_60_single_exit_failure_lists(self):
        """Step 5 exit-count-check: a single Type C door per side on the
        60-seat cabin fails capacity (55 below 60), the minimum-exit-count
        band rule and the two-C-or-larger rule, in that order; a lone
        Type A door fails the same count and C-pair rules while covering
        the capacity."""
        single_c = exit_count_check(60, ["C"], ["C"])
        self.assertEqual(
            single_c["left_failures"],
            ["capacity", "minimum-exit-count",
             "two-C-or-larger-when-ABC-installed"])
        single_a = exit_count_check(60, ["A"], ["A"])
        self.assertEqual(single_a["left_failures"],
                         ["minimum-exit-count",
                          "two-C-or-larger-when-ABC-installed"])
        self.assertEqual(single_a["left_capacity"], 110)

    def test_exit_count_check_25_iii_iii_one_exit_minimum_type(self):
        """Step 5 exit-count-check: capacity 25 sits in the 20-40 band,
        which demands one exit of Type II or larger per side, so a Type III
        pair fails one-exit-minimum-type."""
        result = exit_count_check(25, ["III", "III"], ["III", "III"])
        self.assertFalse(result["adequate"])
        self.assertEqual(result["left_failures"], ["one-exit-minimum-type"])

    def test_exit_count_check_180_type_i_pair_capacity_only(self):
        """Step 5 exit-count-check: two Type I exits per side on 180 seats
        do satisfy the two Type I or larger minimum of the over-110 band
        (two-exits-minimum-type is NOT triggered) but still fail capacity,
        because 90 credits fall below 180."""
        result = exit_count_check(180, ["I", "I"], ["I", "I"])
        self.assertEqual(result["left_failures"], ["capacity"])
        self.assertNotIn("two-exits-minimum-type", result["left_failures"])

    def test_exit_count_check_853_all_exits_minimum_type(self):
        """Step 5 exit-count-check: on the over-110 band every exit must be
        Type III or larger, so a Type A with a Type IV on 853 seats fails
        capacity, all-exits-minimum-type, two-exits-minimum-type and the
        two-C-or-larger rule."""
        result = exit_count_check(853, ["A", "IV"], ["A", "IV"])
        self.assertEqual(
            result["left_failures"],
            ["capacity", "all-exits-minimum-type", "two-exits-minimum-type",
             "two-C-or-larger-when-ABC-installed"])

    def test_exit_count_check_asymmetric_sides_report_independently(self):
        """Step 5 exit-count-check: the sides are judged independently, so
        one good side cannot rescue a failing side; a single Type C on the
        left with Type C doors on the right leaves the right side clean."""
        result = exit_count_check(60, ["C"], ["C", "C"])
        self.assertFalse(result["adequate"])
        self.assertNotEqual(result["left_failures"], [])
        self.assertEqual(result["right_failures"], [])

    def test_exit_count_check_validation_errors(self):
        """Step 5 exit-count-check: an unknown exit type on either side and
        a passenger capacity below 1 raise ValueError (non-physical input
        rejection)."""
        with self.assertRaises(ValueError):
            exit_count_check(180, ["A", "X"], ["A", "B"])
        with self.assertRaises(ValueError):
            exit_count_check(0, ["A"], ["A"])

    def test_exit_count_check_dict_keys_exact(self):
        """Step 5 exit-count-check: the verdict dict carries exactly the
        documented keys, passenger_capacity through shortfall."""
        result = exit_count_check(180, ["A", "B"], ["A", "B"])
        self.assertEqual(
            sorted(result),
            ["adequate", "left_capacity", "left_exits", "left_failures",
             "passenger_capacity", "right_capacity", "right_exits",
             "right_failures", "shortfall"])


class TestExitPlacement(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the adjacent-exit spacing rule on
    one side of the fuselage."""

    def test_exit_placement_four_exits_32_inch_gaps(self):
        """Step 6 adjacent-exit spacing rule: exits at rows 1, 12, 23 and
        32 at 32 inch seat pitch give centerline gaps of 29.33, 29.33 and
        24.0 ft, all under the 60 ft limit, verdict adequate."""
        result = exit_placement_check([1, 12, 23, 32], 32)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["spacing_violations"], [])
        self.assertAlmostEqual(result["adjacent_gap_ft"][0], 29.3333, places=3)
        self.assertAlmostEqual(result["adjacent_gap_ft"][1], 29.3333, places=3)
        self.assertAlmostEqual(result["adjacent_gap_ft"][2], 24.0, places=3)

    def test_exit_placement_max_implied_seat_distance(self):
        """Step 6 adjacent-exit spacing rule: the implied maximum seat
        distance to an exit is half the largest adjacent gap, 14.667 ft for
        the four-exit 32 inch layout."""
        result = exit_placement_check([1, 12, 23, 32], 32)
        self.assertAlmostEqual(result["max_implied_seat_distance_ft"],
                               14.667, places=3)

    def test_exit_placement_82_667_ft_gap_spacing_violation(self):
        """Step 6 adjacent-exit spacing rule: exits only at rows 1 and 32
        at 32 inch seat pitch leave an 82.67 ft gap, flagged as a spacing
        violation of the 60 ft limit with the trailing exit index."""
        result = exit_placement_check([1, 32], 32)
        self.assertFalse(result["adequate"])
        self.assertEqual(len(result["spacing_violations"]), 1)
        index, gap = result["spacing_violations"][0]
        self.assertEqual(index, 1)
        self.assertAlmostEqual(gap, 82.6667, places=3)

    def test_exit_placement_regional_rows_49_ft_gap_passes(self):
        """Step 6 adjacent-exit spacing rule: the regional layout, 20 rows
        at 31 inch seat pitch with exits at rows 1 and 20, gives a 49.08 ft
        gap under the 60 ft limit with a 24.542 ft implied seat distance."""
        result = exit_placement_check([1, 20], 31)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["spacing_violations"], [])
        self.assertAlmostEqual(result["adjacent_gap_ft"][0], 49.0833, places=3)
        self.assertAlmostEqual(result["max_implied_seat_distance_ft"],
                               24.542, places=3)

    def test_exit_placement_rows_sorted_and_validation(self):
        """Step 6 adjacent-exit spacing rule: row lists are reported
        sorted, and empty, non-positive or zero-pitch inputs raise
        ValueError (non-physical input rejection)."""
        self.assertEqual(exit_placement_check([32, 1], 32)["exit_row_numbers"],
                         [1, 32])
        for bad_rows, pitch in (([], 32), ([0, 5], 32), ([-1], 32)):
            with self.assertRaises(ValueError):
                exit_placement_check(bad_rows, pitch)
        with self.assertRaises(ValueError):
            exit_placement_check([1, 5], 0)


class TestEvacuationDemandRatio(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the aggregate evacuation demand
    ratio over the exit capacity sums."""

    def test_evacuation_demand_ratio_inadequate_aggregate(self):
        """Step 7 evacuation demand ratio: 180 seats against 165 seats of
        per-side exit credit gives 1.090909, above 1.0, the inadequate
        aggregate the Type A plus Type C layout produced."""
        ratio = evacuation_demand_ratio(180, 165)
        self.assertAlmostEqual(ratio, 1.090909, places=5)
        self.assertGreater(ratio, 1.0)

    def test_evacuation_demand_ratio_adequate_aggregate(self):
        """Step 7 evacuation demand ratio: 180 seats against the 185 seats
        of the Type A plus Type B layout gives 0.972973, at or below 1.0,
        the adequate aggregate verdict."""
        ratio = evacuation_demand_ratio(180, 185)
        self.assertAlmostEqual(ratio, 0.972973, places=5)
        self.assertLessEqual(ratio, 1.0)

    def test_evacuation_demand_ratio_unity_at_equal_credit_sum(self):
        """Step 7 evacuation demand ratio: the ratio is exactly 1.0 when
        the passenger capacity equals the exit credit sum, the boundary
        where the aggregate capacity just covers the cabin."""
        self.assertEqual(evacuation_demand_ratio(100, 100), 1.0)

    def test_evacuation_demand_ratio_validation_errors(self):
        """Step 7 evacuation demand ratio: a zero exit capacity sum or a
        passenger capacity below 1 raises ValueError (non-physical input
        rejection)."""
        with self.assertRaises(ValueError):
            evacuation_demand_ratio(180, 0)
        with self.assertRaises(ValueError):
            evacuation_demand_ratio(180, -10)
        with self.assertRaises(ValueError):
            evacuation_demand_ratio(0, 100)


class TestDeterminism(unittest.TestCase):
    """Whole-workflow determinism across the exit-count-check, the
    adjacent-exit spacing rule and the required per-side exit set."""

    def test_repeated_calls_are_deterministic(self):
        """The exit-count-check of step 5, the adjacent-exit spacing rule
        of step 6 and the required per-side exit set of step 4 return equal
        dicts on repeated calls (no hidden state, offline)."""
        count_once = exit_count_check(60, ["C", "C"], ["C", "C"])
        count_twice = exit_count_check(60, ["C", "C"], ["C", "C"])
        self.assertEqual(count_once, count_twice)
        place_once = exit_placement_check([1, 12, 23, 32], 32)
        place_twice = exit_placement_check([1, 12, 23, 32], 32)
        self.assertEqual(place_once, place_twice)
        req_once = required_exits_by_capacity(180)
        req_twice = required_exits_by_capacity(180)
        self.assertEqual(req_once, req_twice)
        self.assertEqual(MAX_ADJACENT_EXIT_SPACING_FT, 60.0)


if __name__ == "__main__":
    unittest.main()
