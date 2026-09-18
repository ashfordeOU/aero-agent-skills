"""Contract test for the q7030-wrapping-operation leaf (stdlib unittest)."""

import unittest

from q7030_wrapping_operation_logic import (
    ACCEPTED,
    BASE_START_TOLERANCE_MM,
    MAX_LEVELS_PER_POST,
    REFUSED,
    WIRE_GAUGE_SCHEDULE,
    assess_operation,
    assess_position,
    assess_tightness,
    assess_turn_count,
    assess_wrapping_operations,
    gauge_spec,
    insulated_turn_window,
    required_bare_turns,
    single_gap_limit_mm,
    total_gap_limit_mm,
    usable_post_length_mm,
    validate_operation,
    wrap_height_mm,
)


def operation(wrap_id="W-1", gauge=26, **kw):
    record = {
        "id": wrap_id,
        "gauge": gauge,
        "wrap_type": "modified",
        "bare_turns": 6,
        "insulated_turns": 1.0,
        "level": 1,
        "post_corners": 4,
        "corner_contacts": 24,
        "turn_gaps_mm": [0.0, 0.0, 0.0, 0.0, 0.0],
        "post_length_mm": 12.0,
        "base_offset_mm": 0.0,
        "occupied_length_mm": 0.0,
        "start_height_mm": 0.0,
        "insulation_wall_mm": 0.2,
    }
    record.update(kw)
    return record


class TestGaugeSchedule(unittest.TestCase):
    def test_every_gauge_carries_a_diameter_and_a_turn_count(self):
        for gauge, spec in WIRE_GAUGE_SCHEDULE.items():
            self.assertGreater(spec["conductor_diameter_mm"], 0.0)
            self.assertGreaterEqual(spec["min_bare_turns"], 4)
            self.assertEqual(required_bare_turns(gauge), spec["min_bare_turns"])

    def test_finer_wire_owes_at_least_as_many_turns(self):
        gauges = sorted(WIRE_GAUGE_SCHEDULE)
        for coarse, fine in zip(gauges, gauges[1:]):
            self.assertLessEqual(
                required_bare_turns(coarse), required_bare_turns(fine)
            )

    def test_unknown_gauge_raises(self):
        with self.assertRaises(ValueError):
            gauge_spec(18)

    def test_non_integer_gauge_raises(self):
        with self.assertRaises(ValueError):
            gauge_spec("26")

    def test_gauge_spec_returns_a_copy(self):
        spec = gauge_spec(26)
        spec["min_bare_turns"] = 99
        self.assertEqual(required_bare_turns(26), 6)


class TestInsulatedTurnWindow(unittest.TestCase):
    def test_conventional_wrap_carries_no_insulated_turn(self):
        self.assertEqual(insulated_turn_window("conventional"), (0.0, 0.0))

    def test_modified_wrap_carries_at_least_half_a_turn(self):
        low, high = insulated_turn_window("modified")
        self.assertAlmostEqual(low, 0.5, places=9)
        self.assertGreater(high, low)

    def test_unknown_wrap_type_raises(self):
        with self.assertRaises(ValueError):
            insulated_turn_window("spiral")


class TestGeometry(unittest.TestCase):
    def test_bare_wrap_height_is_turns_times_conductor(self):
        height = wrap_height_mm(26, 6, 0.0, 0.2)
        self.assertAlmostEqual(height, 6 * 0.404, places=9)

    def test_insulated_turn_adds_both_insulation_walls(self):
        bare = wrap_height_mm(26, 6, 0.0, 0.2)
        modified = wrap_height_mm(26, 6, 1.0, 0.2)
        self.assertAlmostEqual(modified - bare, 0.404 + 0.4, places=9)

    def test_negative_insulation_wall_raises(self):
        with self.assertRaises(ValueError):
            wrap_height_mm(26, 6, 1.0, -0.1)

    def test_usable_length_subtracts_offset_and_occupied(self):
        self.assertAlmostEqual(usable_post_length_mm(12.0, 1.0, 3.0), 8.0, places=9)

    def test_usable_length_may_be_exactly_zero(self):
        self.assertAlmostEqual(usable_post_length_mm(12.0, 2.0, 10.0), 0.0, places=9)

    def test_over_committed_post_raises(self):
        with self.assertRaises(ValueError):
            usable_post_length_mm(12.0, 2.0, 11.0)

    def test_non_positive_post_length_raises(self):
        with self.assertRaises(ValueError):
            usable_post_length_mm(0.0, 0.0, 0.0)

    def test_gap_limits_scale_with_the_conductor(self):
        self.assertAlmostEqual(single_gap_limit_mm(26), 0.404 * 0.5, places=9)
        self.assertAlmostEqual(total_gap_limit_mm(26), 0.404, places=9)


class TestValidation(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_operation(["W-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_operation(operation(""))

    def test_fractional_bare_turns_raise(self):
        with self.assertRaises(ValueError):
            validate_operation(operation(bare_turns=6.5))

    def test_negative_corner_contacts_raise(self):
        with self.assertRaises(ValueError):
            validate_operation(operation(corner_contacts=-1))

    def test_level_below_one_raises(self):
        with self.assertRaises(ValueError):
            validate_operation(operation(level=0))

    def test_gaps_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_operation(operation(turn_gaps_mm=0.1))

    def test_negative_gap_raises(self):
        with self.assertRaises(ValueError):
            validate_operation(operation(turn_gaps_mm=[-0.01]))

    def test_defaults_fill_in_missing_geometry(self):
        norm = validate_operation({"id": "W-9", "gauge": 24})
        self.assertEqual(norm["wrap_type"], "modified")
        self.assertEqual(norm["level"], 1)
        self.assertEqual(norm["post_corners"], 4)


class TestTurnCount(unittest.TestCase):
    def test_schedule_met_gives_no_finding(self):
        self.assertEqual(assess_turn_count(operation()), [])

    def test_one_turn_short_is_a_finding(self):
        self.assertIn(
            "bare-turn-count-below-gauge-schedule",
            assess_turn_count(operation(bare_turns=5)),
        )

    def test_conventional_wrap_with_an_insulated_turn_is_a_finding(self):
        findings = assess_turn_count(
            operation(wrap_type="conventional", insulated_turns=1.0)
        )
        self.assertIn("insulated-turns-above-configuration-window", findings)

    def test_modified_wrap_without_an_insulated_turn_is_a_finding(self):
        findings = assess_turn_count(operation(insulated_turns=0.0))
        self.assertIn("insulated-turns-below-configuration-window", findings)

    def test_exactly_half_an_insulated_turn_is_accepted(self):
        self.assertEqual(assess_turn_count(operation(insulated_turns=0.5)), [])


class TestTightness(unittest.TestCase):
    def test_full_corner_contact_gives_no_finding(self):
        self.assertEqual(assess_tightness(operation()), [])

    def test_one_missed_corner_is_a_finding(self):
        findings = assess_tightness(operation(corner_contacts=23))
        self.assertIn("turns-not-seated-on-every-post-corner", findings)

    def test_single_gap_above_half_a_conductor_is_a_finding(self):
        findings = assess_tightness(operation(turn_gaps_mm=[0.25]))
        self.assertIn("single-turn-gap-above-limit", findings)

    def test_gap_exactly_on_the_single_limit_is_accepted(self):
        limit = single_gap_limit_mm(26)
        self.assertAlmostEqual(limit, 0.202, places=9)
        self.assertEqual(assess_tightness(operation(turn_gaps_mm=[limit])), [])

    def test_many_small_gaps_trip_the_cumulative_limit(self):
        findings = assess_tightness(operation(turn_gaps_mm=[0.15, 0.15, 0.15]))
        self.assertIn("cumulative-turn-gap-above-limit", findings)
        self.assertNotIn("single-turn-gap-above-limit", findings)


class TestPosition(unittest.TestCase):
    def test_first_level_at_the_base_gives_no_finding(self):
        self.assertEqual(assess_position(operation()), [])

    def test_first_level_lifted_off_the_base_is_a_finding(self):
        findings = assess_position(
            operation(start_height_mm=BASE_START_TOLERANCE_MM + 0.5)
        )
        self.assertIn("first-level-not-started-at-post-base", findings)

    def test_second_level_below_the_first_is_a_finding(self):
        findings = assess_position(
            operation(level=2, occupied_length_mm=2.6, start_height_mm=1.0)
        )
        self.assertIn("level-started-below-the-wrap-under-it", findings)

    def test_second_level_seated_on_the_first_is_accepted(self):
        self.assertEqual(
            assess_position(
                operation(level=2, occupied_length_mm=2.6, start_height_mm=2.6)
            ),
            [],
        )

    def test_level_above_post_capacity_is_a_finding(self):
        findings = assess_position(
            operation(
                level=MAX_LEVELS_PER_POST + 1,
                occupied_length_mm=3.0,
                start_height_mm=3.0,
            )
        )
        self.assertIn("level-index-above-post-capacity", findings)

    def test_wrap_taller_than_the_free_post_is_a_finding(self):
        findings = assess_position(operation(post_length_mm=2.0))
        self.assertIn("wrap-height-exceeds-usable-post-length", findings)


class TestAssessOperation(unittest.TestCase):
    def test_clean_operation_is_accepted(self):
        result = assess_operation(operation())
        self.assertEqual(result["status"], ACCEPTED)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["required_bare_turns"], 6)

    def test_defective_operation_is_refused_with_reasons(self):
        result = assess_operation(operation(bare_turns=3, corner_contacts=4))
        self.assertEqual(result["status"], REFUSED)
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_reported_height_matches_the_geometry_helper(self):
        result = assess_operation(operation())
        self.assertAlmostEqual(
            result["wrap_height_mm"], wrap_height_mm(26, 6, 1.0, 0.2), places=9
        )


class TestCampaign(unittest.TestCase):
    def test_all_clean_set_is_compliant(self):
        summary = assess_wrapping_operations(
            [operation("W-1"), operation("W-2"), operation("W-3")]
        )
        self.assertTrue(summary["compliant"])
        self.assertEqual(summary["refused_ids"], [])
        self.assertEqual(len(summary["accepted_ids"]), 3)

    def test_one_bad_wrap_fails_the_set(self):
        summary = assess_wrapping_operations(
            [operation("W-1"), operation("W-2", bare_turns=2)]
        )
        self.assertFalse(summary["compliant"])
        self.assertEqual(summary["refused_ids"], ["W-2"])

    def test_duplicate_ids_raise(self):
        with self.assertRaises(ValueError):
            assess_wrapping_operations([operation("W-1"), operation("W-1")])

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_wrapping_operations([])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_wrapping_operations(operation())


if __name__ == "__main__":
    unittest.main()
