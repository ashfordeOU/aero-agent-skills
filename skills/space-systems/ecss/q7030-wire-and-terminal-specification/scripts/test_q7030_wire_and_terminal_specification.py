"""Contract tests for the wire and terminal specification logic."""

import math
import unittest

from q7030_wire_and_terminal_specification_logic import (
    BOUND_TOLERANCE,
    END_CLEARANCE_MM,
    MIN_DIAGONAL_TO_DIAMETER,
    PROHIBITED_FINISHES,
    QUALIFIED_FINISHES,
    REFERENCE_DIAMETER_MM,
    REFERENCE_GAUGE,
    TURNS_BY_GAUGE,
    assess_wire_and_terminal,
    awg_conductor_diameter_mm,
    diagonal_to_diameter_ratio,
    finish_findings,
    minimum_post_length_mm,
    post_diagonal_mm,
    required_turns,
    wrap_length_per_level_mm,
)


def _spec(**over):
    base = {
        "gauge_awg": 26,
        "planned_turns": 6,
        "post_width_mm": 0.635,
        "post_thickness_mm": 0.635,
        "available_post_length_mm": 12.7,
        "wire_finish": "silver",
        "post_finish": "gold-over-nickel",
    }
    base.update(over)
    return base


class ConductorDiameterTests(unittest.TestCase):
    def test_the_reference_gauge_returns_the_reference_diameter(self):
        self.assertAlmostEqual(
            awg_conductor_diameter_mm(REFERENCE_GAUGE - 4),
            REFERENCE_DIAMETER_MM * (92.0 ** (4.0 / 39.0)),
            places=9,
        )

    def test_a_thicker_gauge_number_is_a_thinner_wire(self):
        self.assertGreater(awg_conductor_diameter_mm(20), awg_conductor_diameter_mm(30))

    def test_diameter_is_monotonic_across_the_wrappable_span(self):
        thickest = TURNS_BY_GAUGE[0][0]
        thinnest = TURNS_BY_GAUGE[-1][1]
        previous = None
        for gauge in range(thickest, thinnest + 1):
            value = awg_conductor_diameter_mm(gauge)
            if previous is not None:
                self.assertLess(value, previous)
            previous = value

    def test_a_gauge_thicker_than_the_span_is_rejected(self):
        with self.assertRaises(ValueError):
            awg_conductor_diameter_mm(TURNS_BY_GAUGE[0][0] - 1)

    def test_a_gauge_thinner_than_the_span_is_rejected(self):
        with self.assertRaises(ValueError):
            awg_conductor_diameter_mm(TURNS_BY_GAUGE[-1][1] + 1)

    def test_a_boolean_gauge_is_rejected(self):
        with self.assertRaises(ValueError):
            awg_conductor_diameter_mm(True)

    def test_a_fractional_gauge_is_rejected(self):
        with self.assertRaises(ValueError):
            awg_conductor_diameter_mm(26.0)


class TurnCountTests(unittest.TestCase):
    def test_every_gauge_in_the_span_has_a_turn_count(self):
        thickest = TURNS_BY_GAUGE[0][0]
        thinnest = TURNS_BY_GAUGE[-1][1]
        for gauge in range(thickest, thinnest + 1):
            self.assertGreaterEqual(required_turns(gauge), 5)

    def test_a_thinner_wire_owes_at_least_as_many_turns(self):
        self.assertGreaterEqual(required_turns(30), required_turns(20))

    def test_the_band_edges_take_their_own_band_count(self):
        for thickest, thinnest, turns in TURNS_BY_GAUGE:
            self.assertEqual(required_turns(thickest), turns)
            self.assertEqual(required_turns(thinnest), turns)

    def test_a_gauge_outside_the_span_has_no_turn_count(self):
        with self.assertRaises(ValueError):
            required_turns(40)


class PostSectionTests(unittest.TestCase):
    def test_the_diagonal_is_the_hypotenuse_of_the_section(self):
        self.assertAlmostEqual(post_diagonal_mm(0.3, 0.4), 0.5, places=9)

    def test_a_square_post_diagonal_is_root_two_times_its_side(self):
        self.assertAlmostEqual(
            post_diagonal_mm(0.635, 0.635), 0.635 * math.sqrt(2.0), places=9
        )

    def test_a_zero_thickness_post_is_rejected(self):
        with self.assertRaises(ValueError):
            post_diagonal_mm(0.635, 0.0)

    def test_the_ratio_falls_as_the_wire_gets_thicker(self):
        thin = diagonal_to_diameter_ratio(0.635, 0.635, 30)
        thick = diagonal_to_diameter_ratio(0.635, 0.635, 20)
        self.assertGreater(thin, thick)

    def test_a_standard_post_clears_the_ratio_for_a_fine_wire(self):
        self.assertGreater(
            diagonal_to_diameter_ratio(0.635, 0.635, 28), MIN_DIAGONAL_TO_DIAMETER
        )


class WrapLengthTests(unittest.TestCase):
    def test_one_level_is_turns_times_the_conductor_diameter(self):
        self.assertAlmostEqual(
            wrap_length_per_level_mm(26, 6),
            6 * awg_conductor_diameter_mm(26),
            places=9,
        )

    def test_an_insulated_turn_adds_the_insulated_diameter(self):
        bare = wrap_length_per_level_mm(26, 6)
        modified = wrap_length_per_level_mm(26, 6, 1, 0.8)
        self.assertAlmostEqual(modified - bare, 0.8, places=9)

    def test_an_insulated_turn_without_its_diameter_is_rejected(self):
        with self.assertRaises(ValueError):
            wrap_length_per_level_mm(26, 6, 1)

    def test_an_insulated_diameter_under_the_bare_diameter_is_rejected(self):
        with self.assertRaises(ValueError):
            wrap_length_per_level_mm(26, 6, 1, 0.1)

    def test_post_length_stacks_the_levels_and_adds_clearance(self):
        per_level = wrap_length_per_level_mm(26, 6)
        self.assertAlmostEqual(
            minimum_post_length_mm(26, 6, 3),
            3 * per_level + END_CLEARANCE_MM,
            places=9,
        )

    def test_zero_levels_are_rejected(self):
        with self.assertRaises(ValueError):
            minimum_post_length_mm(26, 6, 0)

    def test_a_negative_clearance_is_rejected(self):
        with self.assertRaises(ValueError):
            minimum_post_length_mm(26, 6, 1, 0, None, -0.1)


class FinishTests(unittest.TestCase):
    def test_a_qualified_pairing_raises_nothing(self):
        self.assertEqual(finish_findings("silver", "gold-over-nickel"), [])

    def test_every_qualified_finish_is_accepted_on_the_post(self):
        for finish in QUALIFIED_FINISHES:
            self.assertEqual(finish_findings("silver", finish), [])

    def test_an_unalloyed_tin_wire_is_critical(self):
        findings = finish_findings(PROHIBITED_FINISHES[0], "nickel")
        self.assertEqual(findings[0]["severity"], "critical")
        self.assertEqual(findings[0]["control"], "prohibited-finish")

    def test_an_unalloyed_tin_post_is_critical(self):
        findings = finish_findings("silver", PROHIBITED_FINISHES[1])
        self.assertEqual(findings[0]["control"], "prohibited-finish")

    def test_an_unknown_finish_is_major_not_fatal(self):
        findings = finish_findings("silver", "anodised-aluminium")
        self.assertEqual(findings[0]["severity"], "major")
        self.assertEqual(findings[0]["control"], "unqualified-finish")

    def test_finish_tokens_are_normalised(self):
        self.assertEqual(finish_findings("  Silver ", "GOLD-OVER-NICKEL"), [])

    def test_a_blank_finish_is_rejected(self):
        with self.assertRaises(ValueError):
            finish_findings("", "nickel")


class AssessmentTests(unittest.TestCase):
    def test_a_conforming_pairing_is_compatible(self):
        result = assess_wire_and_terminal(_spec())
        self.assertEqual(result["disposition"], "compatible")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["required_turns"], 6)

    def test_too_few_turns_is_critical(self):
        result = assess_wire_and_terminal(_spec(planned_turns=4))
        self.assertEqual(result["disposition"], "not-compatible")
        self.assertEqual(result["findings"][0]["control"], "turn-count")

    def test_extra_turns_are_not_a_finding(self):
        result = assess_wire_and_terminal(_spec(planned_turns=8))
        self.assertEqual(result["disposition"], "compatible")

    def test_a_post_exactly_at_the_needed_length_is_accepted(self):
        needed = minimum_post_length_mm(26, 6, 1)
        result = assess_wire_and_terminal(_spec(available_post_length_mm=needed))
        self.assertAlmostEqual(result["minimum_post_length_mm"], needed, places=9)
        self.assertEqual(result["disposition"], "compatible")

    def test_a_short_post_is_critical(self):
        result = assess_wire_and_terminal(_spec(available_post_length_mm=1.0))
        controls = [f["control"] for f in result["findings"]]
        self.assertIn("post-length", controls)
        self.assertEqual(result["disposition"], "not-compatible")

    def test_three_levels_need_a_longer_post_than_one(self):
        one = assess_wire_and_terminal(_spec())["minimum_post_length_mm"]
        three = assess_wire_and_terminal(_spec(levels=3))["minimum_post_length_mm"]
        self.assertGreater(three, one)

    def test_a_thick_wire_on_a_fine_post_raises_the_section_finding(self):
        result = assess_wire_and_terminal(_spec(gauge_awg=18, planned_turns=5))
        controls = [f["control"] for f in result["findings"]]
        self.assertIn("post-section", controls)
        self.assertLess(result["diagonal_to_diameter_ratio"], MIN_DIAGONAL_TO_DIAMETER)

    def test_a_prohibited_finish_alone_makes_the_pairing_not_compatible(self):
        result = assess_wire_and_terminal(_spec(post_finish="pure-tin"))
        self.assertEqual(result["disposition"], "not-compatible")

    def test_an_unqualified_finish_alone_asks_for_actions(self):
        result = assess_wire_and_terminal(_spec(wire_finish="chromate"))
        self.assertEqual(result["disposition"], "compatible-with-actions")

    def test_findings_are_ranked_critical_first(self):
        result = assess_wire_and_terminal(
            _spec(planned_turns=3, wire_finish="chromate")
        )
        self.assertEqual(result["findings"][0]["severity"], "critical")
        self.assertEqual(result["findings"][-1]["severity"], "major")

    def test_a_modified_wrap_needs_more_post_than_a_conventional_one(self):
        conventional = assess_wire_and_terminal(_spec())["minimum_post_length_mm"]
        modified = assess_wire_and_terminal(
            _spec(insulation_turns=1, insulated_diameter_mm=0.8)
        )["minimum_post_length_mm"]
        self.assertGreater(modified, conventional)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["post_width_mm"]
        with self.assertRaises(ValueError):
            assess_wire_and_terminal(spec)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_wire_and_terminal([_spec()])

    def test_bound_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(BOUND_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=1)
