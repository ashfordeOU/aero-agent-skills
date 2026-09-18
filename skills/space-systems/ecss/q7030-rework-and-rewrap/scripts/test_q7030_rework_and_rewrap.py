"""Contract test for the q7030-rework-and-rewrap leaf (stdlib unittest)."""

import unittest

from q7030_rework_and_rewrap_logic import (
    MAX_LEVELS_PER_POST,
    MAX_REMOVALS_PER_POST,
    PROCEED,
    REPLACE_TERMINAL,
    REPLACE_WIRE,
    assess_post_condition,
    assess_removal_method,
    assess_rework,
    assess_rework_campaign,
    assess_wire_length,
    conductor_diameter_mm,
    minimum_bare_turns,
    post_perimeter_mm,
    removals_remaining,
    validate_rework,
    wire_length_required_mm,
)


def rework(post_id="P-1", gauge=26, **kw):
    record = {
        "post_id": post_id,
        "gauge": gauge,
        "previous_removals": 1,
        "levels_in_place": 1,
        "removal_method": "unwrapping-tool",
        "corner_state": "sharp",
        "used_length_cut_off": True,
        "planned_turns": 6,
        "post_width_mm": 0.64,
        "post_thickness_mm": 0.64,
        "available_wire_mm": 60.0,
        "service_loop_mm": 10.0,
    }
    record.update(kw)
    return record


class TestGeometry(unittest.TestCase):
    def test_perimeter_of_a_square_post(self):
        self.assertAlmostEqual(post_perimeter_mm(0.64, 0.64), 2.56, places=9)

    def test_perimeter_of_a_rectangular_post(self):
        self.assertAlmostEqual(post_perimeter_mm(1.0, 0.5), 3.0, places=9)

    def test_zero_cross_section_raises(self):
        with self.assertRaises(ValueError):
            post_perimeter_mm(0.0, 0.64)

    def test_negative_cross_section_raises(self):
        with self.assertRaises(ValueError):
            post_perimeter_mm(0.64, -0.1)

    def test_required_wire_covers_turns_allowance_strip_and_loop(self):
        needed = wire_length_required_mm(26, 6, 0.64, 0.64, 10.0)
        self.assertAlmostEqual(needed, 6 * 2.56 * 1.10 + 3.0 + 10.0, places=9)

    def test_more_turns_need_more_wire(self):
        self.assertGreater(
            wire_length_required_mm(26, 8, 0.64, 0.64),
            wire_length_required_mm(26, 6, 0.64, 0.64),
        )

    def test_zero_turns_raise(self):
        with self.assertRaises(ValueError):
            wire_length_required_mm(26, 0, 0.64, 0.64)

    def test_unknown_gauge_raises(self):
        with self.assertRaises(ValueError):
            conductor_diameter_mm(18)

    def test_every_gauge_has_a_turn_minimum(self):
        for gauge in (20, 22, 24, 26, 28, 30):
            self.assertGreaterEqual(minimum_bare_turns(gauge), 4)


class TestRemovalAllowance(unittest.TestCase):
    def test_a_fresh_post_has_the_full_allowance(self):
        self.assertEqual(removals_remaining(0), MAX_REMOVALS_PER_POST)

    def test_each_removal_spends_one(self):
        self.assertEqual(removals_remaining(1), MAX_REMOVALS_PER_POST - 1)

    def test_the_allowance_does_not_go_negative(self):
        self.assertEqual(removals_remaining(MAX_REMOVALS_PER_POST + 5), 0)

    def test_negative_removals_raise(self):
        with self.assertRaises(ValueError):
            removals_remaining(-1)

    def test_non_integer_removals_raise(self):
        with self.assertRaises(ValueError):
            removals_remaining(1.5)


class TestValidation(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_rework(["P-1"])

    def test_empty_post_id_raises(self):
        with self.assertRaises(ValueError):
            validate_rework(rework(""))

    def test_unknown_removal_method_raises(self):
        with self.assertRaises(ValueError):
            validate_rework(rework(removal_method="unscrewed"))

    def test_unknown_corner_state_raises(self):
        with self.assertRaises(ValueError):
            validate_rework(rework(corner_state="shiny"))

    def test_non_boolean_cut_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_rework(rework(used_length_cut_off="yes"))

    def test_planned_turns_default_to_the_gauge_schedule(self):
        record = rework()
        del record["planned_turns"]
        self.assertEqual(validate_rework(record)["planned_turns"], 6)


class TestPostCondition(unittest.TestCase):
    def test_a_sound_post_with_allowance_left_is_clean(self):
        self.assertEqual(assess_post_condition(rework()), [])

    def test_deformed_corners_are_reported(self):
        findings = assess_post_condition(rework(corner_state="deformed"))
        self.assertIn("post-corners-deformed-by-removal", findings)

    def test_rounded_corners_are_reported(self):
        findings = assess_post_condition(rework(corner_state="rounded"))
        self.assertIn("post-corners-rounded-by-removal", findings)

    def test_exhausted_allowance_is_reported(self):
        findings = assess_post_condition(
            rework(previous_removals=MAX_REMOVALS_PER_POST)
        )
        self.assertIn("post-rewrap-allowance-exhausted", findings)

    def test_a_full_post_is_reported(self):
        findings = assess_post_condition(
            rework(levels_in_place=MAX_LEVELS_PER_POST)
        )
        self.assertIn("post-levels-already-at-capacity", findings)


class TestRemovalMethod(unittest.TestCase):
    def test_unwinding_is_clean(self):
        self.assertEqual(assess_removal_method(rework()), [])

    def test_pulling_the_wrap_off_is_reported(self):
        self.assertIn(
            "wrap-pulled-off-instead-of-unwound",
            assess_removal_method(rework(removal_method="pulled-off")),
        )

    def test_an_unrecorded_removal_is_reported(self):
        self.assertIn(
            "no-removal-method-on-record",
            assess_removal_method(rework(removal_method="none")),
        )


class TestWireLength(unittest.TestCase):
    def test_enough_wire_and_a_clean_cut_give_no_finding(self):
        findings, needed = assess_wire_length(rework())
        self.assertEqual(findings, [])
        self.assertGreater(needed, 0.0)

    def test_uncut_used_length_is_reported(self):
        findings, _ = assess_wire_length(rework(used_length_cut_off=False))
        self.assertIn("used-wire-length-not-cut-away", findings)

    def test_short_wire_is_reported(self):
        findings, _ = assess_wire_length(rework(available_wire_mm=5.0))
        self.assertIn("remaining-wire-too-short-for-a-new-wrap", findings)

    def test_wire_exactly_long_enough_is_accepted(self):
        needed = wire_length_required_mm(26, 6, 0.64, 0.64, 10.0)
        findings, reported = assess_wire_length(rework(available_wire_mm=needed))
        self.assertEqual(findings, [])
        self.assertAlmostEqual(reported, needed, places=9)


class TestDisposition(unittest.TestCase):
    def test_a_clean_rework_proceeds(self):
        result = assess_rework(rework())
        self.assertEqual(result["disposition"], PROCEED)
        self.assertTrue(result["permitted"])
        self.assertEqual(result["removals_remaining"], MAX_REMOVALS_PER_POST - 1)

    def test_a_damaged_post_goes_to_terminal_replacement(self):
        result = assess_rework(rework(corner_state="deformed"))
        self.assertEqual(result["disposition"], REPLACE_TERMINAL)
        self.assertFalse(result["permitted"])

    def test_an_exhausted_post_goes_to_terminal_replacement(self):
        result = assess_rework(rework(previous_removals=MAX_REMOVALS_PER_POST))
        self.assertEqual(result["disposition"], REPLACE_TERMINAL)

    def test_uncut_wire_goes_to_wire_replacement(self):
        result = assess_rework(rework(used_length_cut_off=False))
        self.assertEqual(result["disposition"], REPLACE_WIRE)

    def test_a_pulled_off_wrap_on_a_sound_post_goes_to_wire_replacement(self):
        result = assess_rework(rework(removal_method="pulled-off"))
        self.assertEqual(result["disposition"], REPLACE_WIRE)

    def test_a_short_turn_plan_blocks_the_rewrap(self):
        result = assess_rework(rework(planned_turns=3))
        self.assertIn("planned-turns-below-gauge-schedule", result["findings"])
        self.assertFalse(result["permitted"])

    def test_post_damage_outranks_a_wire_finding(self):
        result = assess_rework(
            rework(corner_state="deformed", used_length_cut_off=False)
        )
        self.assertEqual(result["disposition"], REPLACE_TERMINAL)


class TestCampaign(unittest.TestCase):
    def test_a_clean_set_is_all_permitted(self):
        summary = assess_rework_campaign([rework("P-1"), rework("P-2")])
        self.assertTrue(summary["all_permitted"])
        self.assertEqual(summary["replace_terminal_ids"], [])

    def test_the_set_splits_by_disposition(self):
        summary = assess_rework_campaign(
            [
                rework("P-1"),
                rework("P-2", corner_state="deformed"),
                rework("P-3", used_length_cut_off=False),
            ]
        )
        self.assertEqual(summary["permitted_ids"], ["P-1"])
        self.assertEqual(summary["replace_terminal_ids"], ["P-2"])
        self.assertEqual(summary["replace_wire_ids"], ["P-3"])

    def test_duplicate_post_ids_raise(self):
        with self.assertRaises(ValueError):
            assess_rework_campaign([rework("P-1"), rework("P-1")])

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_rework_campaign([])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_rework_campaign(rework())


if __name__ == "__main__":
    unittest.main()
