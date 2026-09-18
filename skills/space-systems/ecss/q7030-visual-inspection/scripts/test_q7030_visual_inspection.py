"""Contract test for the q7030-visual-inspection leaf (stdlib unittest)."""

import unittest

from q7030_visual_inspection_logic import (
    ACCEPTED,
    CONDUCTOR_DIAMETER_MM,
    FINDING_SEVERITY,
    MAJOR,
    MINOR,
    REWORK,
    assess_visual_inspection,
    assess_wrap,
    conductor_diameter_mm,
    end_tail_limit_mm,
    finding_codes,
    group_findings,
    minimum_bare_turns,
    severity_of,
    single_gap_limit_mm,
    total_gap_limit_mm,
    validate_observation,
)


def observation(wrap_id="W-1", gauge=26, **kw):
    record = {
        "id": wrap_id,
        "gauge": gauge,
        "wrap_type": "modified",
        "bare_turns": 6,
        "insulated_turns": 1.0,
        "overlapping_turns": 0,
        "lifted_turns": 0,
        "turn_gaps_mm": [0.0, 0.0, 0.0, 0.0, 0.0],
        "end_tail_mm": 0.1,
        "conductor_damaged": False,
        "post_damaged": False,
    }
    record.update(kw)
    return record


class TestLimits(unittest.TestCase):
    def test_every_gauge_has_a_minimum_turn_count(self):
        for gauge in CONDUCTOR_DIAMETER_MM:
            self.assertGreaterEqual(minimum_bare_turns(gauge), 4)

    def test_limits_scale_with_the_conductor(self):
        self.assertAlmostEqual(single_gap_limit_mm(26), 0.202, places=9)
        self.assertAlmostEqual(total_gap_limit_mm(26), 0.404, places=9)
        self.assertAlmostEqual(end_tail_limit_mm(26), 0.404, places=9)

    def test_a_finer_gauge_carries_a_tighter_gap_limit(self):
        self.assertLess(single_gap_limit_mm(30), single_gap_limit_mm(20))

    def test_unknown_gauge_raises(self):
        with self.assertRaises(ValueError):
            conductor_diameter_mm(18)

    def test_non_integer_gauge_raises(self):
        with self.assertRaises(ValueError):
            conductor_diameter_mm(26.0)


class TestSeverity(unittest.TestCase):
    def test_every_code_has_a_severity(self):
        for code in FINDING_SEVERITY:
            self.assertIn(severity_of(code), (MAJOR, MINOR))

    def test_contact_losing_defects_are_major(self):
        for code in ("overlapping-turn", "lifted-turn-not-seated"):
            self.assertEqual(severity_of(code), MAJOR)

    def test_end_tail_is_minor(self):
        self.assertEqual(severity_of("end-tail-above-limit"), MINOR)

    def test_unknown_code_raises(self):
        with self.assertRaises(ValueError):
            severity_of("wrap-looks-untidy")

    def test_grouping_splits_the_two_severities(self):
        grouped = group_findings(["overlapping-turn", "end-tail-above-limit"])
        self.assertEqual(grouped[MAJOR], ["overlapping-turn"])
        self.assertEqual(grouped[MINOR], ["end-tail-above-limit"])

    def test_grouping_a_non_sequence_raises(self):
        with self.assertRaises(ValueError):
            group_findings("overlapping-turn")


class TestValidation(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_observation(["W-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_observation(observation(""))

    def test_unknown_wrap_type_raises(self):
        with self.assertRaises(ValueError):
            validate_observation(observation(wrap_type="spiral"))

    def test_negative_lifted_turns_raise(self):
        with self.assertRaises(ValueError):
            validate_observation(observation(lifted_turns=-1))

    def test_non_boolean_damage_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_observation(observation(conductor_damaged="yes"))

    def test_gaps_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_observation(observation(turn_gaps_mm=0.05))

    def test_negative_end_tail_raises(self):
        with self.assertRaises(ValueError):
            validate_observation(observation(end_tail_mm=-0.1))


class TestFindingCodes(unittest.TestCase):
    def test_clean_wrap_raises_nothing(self):
        self.assertEqual(finding_codes(observation()), [])

    def test_one_overlapping_turn_is_reported(self):
        self.assertIn("overlapping-turn", finding_codes(observation(overlapping_turns=1)))

    def test_one_lifted_turn_is_reported(self):
        self.assertIn(
            "lifted-turn-not-seated", finding_codes(observation(lifted_turns=1))
        )

    def test_short_turn_count_is_reported(self):
        self.assertIn(
            "bare-turn-count-below-minimum", finding_codes(observation(bare_turns=4))
        )

    def test_gap_exactly_on_the_single_limit_is_accepted(self):
        limit = single_gap_limit_mm(26)
        self.assertEqual(finding_codes(observation(turn_gaps_mm=[limit])), [])

    def test_gap_past_the_single_limit_is_reported(self):
        codes = finding_codes(observation(turn_gaps_mm=[0.30]))
        self.assertIn("single-turn-gap-above-limit", codes)

    def test_small_gaps_still_trip_the_cumulative_limit(self):
        codes = finding_codes(observation(turn_gaps_mm=[0.15, 0.15, 0.15]))
        self.assertIn("cumulative-turn-gap-above-limit", codes)
        self.assertNotIn("single-turn-gap-above-limit", codes)

    def test_end_tail_exactly_on_the_limit_is_accepted(self):
        self.assertEqual(
            finding_codes(observation(end_tail_mm=end_tail_limit_mm(26))), []
        )

    def test_long_end_tail_is_reported(self):
        self.assertIn("end-tail-above-limit", finding_codes(observation(end_tail_mm=1.0)))

    def test_missing_insulation_turn_is_reported_on_a_modified_wrap(self):
        self.assertIn(
            "insulation-turn-missing-on-modified-wrap",
            finding_codes(observation(insulated_turns=0.0)),
        )

    def test_conventional_wrap_without_insulation_is_clean(self):
        self.assertEqual(
            finding_codes(observation(wrap_type="conventional", insulated_turns=0.0)), []
        )

    def test_damaged_conductor_and_post_are_both_reported(self):
        codes = finding_codes(observation(conductor_damaged=True, post_damaged=True))
        self.assertIn("nicked-or-scraped-conductor", codes)
        self.assertIn("post-damaged-by-wrapping", codes)


class TestAssessWrap(unittest.TestCase):
    def test_clean_wrap_is_accepted(self):
        result = assess_wrap(observation())
        self.assertEqual(result["status"], ACCEPTED)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["required_bare_turns"], 6)

    def test_one_major_finding_sends_the_wrap_to_rework(self):
        result = assess_wrap(observation(overlapping_turns=2))
        self.assertEqual(result["status"], REWORK)
        self.assertEqual(result["major_findings"], ["overlapping-turn"])

    def test_a_single_minor_finding_is_still_accepted(self):
        result = assess_wrap(observation(end_tail_mm=1.0))
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["minor_findings"]), 1)

    def test_two_minor_findings_send_the_wrap_to_rework(self):
        result = assess_wrap(observation(end_tail_mm=1.0, insulated_turns=0.0))
        self.assertFalse(result["accepted"])
        self.assertEqual(len(result["minor_findings"]), 2)
        self.assertEqual(result["major_findings"], [])


class TestLot(unittest.TestCase):
    def test_all_clean_lot_is_accepted(self):
        summary = assess_visual_inspection(
            [observation("W-1"), observation("W-2"), observation("W-3")]
        )
        self.assertTrue(summary["accepted"])
        self.assertEqual(summary["rework_ids"], [])
        self.assertEqual(summary["major_finding_count"], 0)

    def test_one_bad_wrap_fails_the_lot(self):
        summary = assess_visual_inspection(
            [observation("W-1"), observation("W-2", lifted_turns=3)]
        )
        self.assertFalse(summary["accepted"])
        self.assertEqual(summary["rework_ids"], ["W-2"])
        self.assertEqual(summary["major_finding_count"], 1)

    def test_minor_findings_are_totalled_across_the_lot(self):
        summary = assess_visual_inspection(
            [observation("W-1", end_tail_mm=1.0), observation("W-2", end_tail_mm=1.0)]
        )
        self.assertEqual(summary["minor_finding_count"], 2)
        self.assertTrue(summary["accepted"])

    def test_duplicate_ids_raise(self):
        with self.assertRaises(ValueError):
            assess_visual_inspection([observation("W-1"), observation("W-1")])

    def test_empty_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_visual_inspection([])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_visual_inspection(observation())


if __name__ == "__main__":
    unittest.main()
