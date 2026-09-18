"""Contract tests for the wire stripping and end preparation logic."""

import unittest

from q7030_wire_stripping_and_prep_logic import (
    BOUND_TOLERANCE,
    DEFAULT_TAIL_ALLOWANCE_MM,
    MAX_DIAMETER_REDUCTION,
    MAX_NICK_FRACTION,
    MAX_RESTRIPS,
    STRIP_LENGTH_TOLERANCE_MM,
    WRAPPABLE_GAUGE_SPAN,
    assess_wire_preparation,
    awg_conductor_diameter_mm,
    deformation_findings,
    diameter_reduction_fraction,
    insulation_findings,
    nick_depth_fraction,
    nick_findings,
    preparation_disposition,
    required_strip_length_mm,
    restrips_remaining,
    strip_length_findings,
)

GAUGE = 26


def _spec(**over):
    base = {
        "gauge_awg": GAUGE,
        "turns": 6,
        "measured_strip_length_mm": required_strip_length_mm(GAUGE, 6),
        "nick_depth_mm": 0.0,
        "measured_diameter_mm": awg_conductor_diameter_mm(GAUGE),
        "insulation_setback_mm": 0.2,
        "allowable_setback_mm": 0.5,
        "insulation_damaged": False,
        "restrip_count": 0,
    }
    base.update(over)
    return base


class StripLengthTests(unittest.TestCase):
    def test_the_strip_length_is_turns_times_diameter_plus_the_tail(self):
        self.assertAlmostEqual(
            required_strip_length_mm(GAUGE, 6),
            6 * awg_conductor_diameter_mm(GAUGE) + DEFAULT_TAIL_ALLOWANCE_MM,
            places=9,
        )

    def test_more_turns_need_more_stripped_conductor(self):
        self.assertGreater(
            required_strip_length_mm(GAUGE, 7), required_strip_length_mm(GAUGE, 6)
        )

    def test_a_thicker_wire_needs_more_stripped_conductor_at_equal_turns(self):
        self.assertGreater(
            required_strip_length_mm(20, 6), required_strip_length_mm(30, 6)
        )

    def test_an_insulated_turn_adds_the_insulated_diameter(self):
        bare = required_strip_length_mm(GAUGE, 6)
        modified = required_strip_length_mm(GAUGE, 6, 1, 0.8)
        self.assertAlmostEqual(modified - bare, 0.8, places=9)

    def test_an_insulated_turn_without_its_diameter_is_rejected(self):
        with self.assertRaises(ValueError):
            required_strip_length_mm(GAUGE, 6, 1)

    def test_an_insulated_diameter_under_the_bare_diameter_is_rejected(self):
        with self.assertRaises(ValueError):
            required_strip_length_mm(GAUGE, 6, 1, 0.05)

    def test_zero_turns_are_rejected(self):
        with self.assertRaises(ValueError):
            required_strip_length_mm(GAUGE, 0)

    def test_a_gauge_outside_the_span_is_rejected(self):
        with self.assertRaises(ValueError):
            required_strip_length_mm(WRAPPABLE_GAUGE_SPAN[1] + 1, 6)

    def test_a_strip_on_the_requirement_raises_nothing(self):
        required = required_strip_length_mm(GAUGE, 6)
        self.assertEqual(strip_length_findings(required, required), [])

    def test_a_strip_exactly_on_the_tolerance_edge_is_accepted(self):
        required = required_strip_length_mm(GAUGE, 6)
        self.assertEqual(
            strip_length_findings(required + STRIP_LENGTH_TOLERANCE_MM, required), []
        )

    def test_a_short_strip_is_critical(self):
        required = required_strip_length_mm(GAUGE, 6)
        findings = strip_length_findings(required - 2.0, required)
        self.assertEqual(findings[0]["control"], "strip-length-short")
        self.assertEqual(findings[0]["severity"], "critical")

    def test_a_long_strip_is_major_not_fatal(self):
        required = required_strip_length_mm(GAUGE, 6)
        findings = strip_length_findings(required + 3.0, required)
        self.assertEqual(findings[0]["control"], "strip-length-long")
        self.assertEqual(findings[0]["severity"], "major")

    def test_a_negative_measured_length_is_rejected(self):
        with self.assertRaises(ValueError):
            strip_length_findings(-1.0, 5.0)


class ConductorDamageTests(unittest.TestCase):
    def test_a_nick_is_reported_against_the_conductor_diameter(self):
        diameter = awg_conductor_diameter_mm(GAUGE)
        self.assertAlmostEqual(
            nick_depth_fraction(diameter * 0.02, GAUGE), 0.02, places=9
        )

    def test_the_same_nick_is_worse_on_a_finer_wire(self):
        self.assertGreater(nick_depth_fraction(0.01, 30), nick_depth_fraction(0.01, 20))

    def test_an_undamaged_conductor_raises_nothing(self):
        self.assertEqual(nick_findings(0.0, GAUGE), [])

    def test_a_shallow_nick_is_major(self):
        diameter = awg_conductor_diameter_mm(GAUGE)
        findings = nick_findings(diameter * 0.02, GAUGE)
        self.assertEqual(findings[0]["severity"], "major")
        self.assertEqual(findings[0]["control"], "conductor-nick")

    def test_a_nick_exactly_on_the_limit_is_still_only_major(self):
        diameter = awg_conductor_diameter_mm(GAUGE)
        findings = nick_findings(diameter * MAX_NICK_FRACTION, GAUGE)
        self.assertEqual(findings[0]["severity"], "major")

    def test_a_deep_nick_is_critical(self):
        diameter = awg_conductor_diameter_mm(GAUGE)
        findings = nick_findings(diameter * 0.20, GAUGE)
        self.assertEqual(findings[0]["control"], "conductor-nick-deep")
        self.assertEqual(findings[0]["severity"], "critical")

    def test_a_negative_nick_depth_is_rejected(self):
        with self.assertRaises(ValueError):
            nick_findings(-0.01, GAUGE)

    def test_an_undeformed_conductor_shows_no_reduction(self):
        self.assertAlmostEqual(
            diameter_reduction_fraction(awg_conductor_diameter_mm(GAUGE), GAUGE),
            0.0,
            places=9,
        )

    def test_an_oversize_measurement_is_not_a_negative_reduction(self):
        wide = awg_conductor_diameter_mm(GAUGE) * 1.05
        self.assertAlmostEqual(diameter_reduction_fraction(wide, GAUGE), 0.0, places=9)

    def test_a_reduction_inside_the_limit_raises_nothing(self):
        measured = awg_conductor_diameter_mm(GAUGE) * (1.0 - 0.01)
        self.assertEqual(deformation_findings(measured, GAUGE), [])

    def test_a_reduction_exactly_on_the_limit_is_accepted(self):
        measured = awg_conductor_diameter_mm(GAUGE) * (1.0 - MAX_DIAMETER_REDUCTION)
        self.assertEqual(deformation_findings(measured, GAUGE), [])

    def test_a_crushed_conductor_is_critical(self):
        measured = awg_conductor_diameter_mm(GAUGE) * 0.8
        findings = deformation_findings(measured, GAUGE)
        self.assertEqual(findings[0]["control"], "conductor-deformation")
        self.assertEqual(findings[0]["severity"], "critical")

    def test_a_zero_measured_diameter_is_rejected(self):
        with self.assertRaises(ValueError):
            deformation_findings(0.0, GAUGE)


class InsulationTests(unittest.TestCase):
    def test_an_undamaged_end_inside_its_setback_raises_nothing(self):
        self.assertEqual(insulation_findings(0.2, 0.5, False), [])

    def test_a_setback_exactly_on_its_allowance_is_accepted(self):
        self.assertEqual(insulation_findings(0.5, 0.5, False), [])

    def test_an_excessive_setback_is_major(self):
        findings = insulation_findings(1.5, 0.5, False)
        self.assertEqual(findings[0]["control"], "insulation-setback")

    def test_damaged_insulation_is_major(self):
        findings = insulation_findings(0.2, 0.5, True)
        self.assertEqual(findings[0]["control"], "insulation-damage")

    def test_both_insulation_findings_can_be_raised_together(self):
        self.assertEqual(len(insulation_findings(1.5, 0.5, True)), 2)

    def test_a_non_boolean_damage_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            insulation_findings(0.2, 0.5, "no")


class RestripTests(unittest.TestCase):
    def test_a_fresh_end_has_its_whole_allowance(self):
        self.assertEqual(restrips_remaining(0), MAX_RESTRIPS)

    def test_each_restrip_spends_one(self):
        self.assertEqual(restrips_remaining(1), MAX_RESTRIPS - 1)

    def test_the_allowance_never_goes_negative(self):
        self.assertEqual(restrips_remaining(MAX_RESTRIPS + 3), 0)

    def test_a_fractional_restrip_count_is_rejected(self):
        with self.assertRaises(ValueError):
            restrips_remaining(1.5)

    def test_a_clean_end_is_accepted(self):
        self.assertEqual(preparation_disposition([], 2), "accept")

    def test_a_finding_with_budget_left_asks_for_a_restrip(self):
        findings = [{"severity": "major", "control": "x", "detail": "y"}]
        self.assertEqual(preparation_disposition(findings, 1), "restrip-required")

    def test_a_finding_with_no_budget_left_rejects_the_end(self):
        findings = [{"severity": "major", "control": "x", "detail": "y"}]
        self.assertEqual(preparation_disposition(findings, 0), "reject-wire-end")

    def test_an_unknown_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            preparation_disposition([{"severity": "urgent"}], 1)


class AssessmentTests(unittest.TestCase):
    def test_a_correctly_prepared_end_is_accepted(self):
        result = assess_wire_preparation(_spec())
        self.assertEqual(result["disposition"], "accept")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["restrips_remaining"], MAX_RESTRIPS)

    def test_a_short_strip_sends_the_end_back_for_a_restrip(self):
        result = assess_wire_preparation(
            _spec(measured_strip_length_mm=required_strip_length_mm(GAUGE, 6) - 2.0)
        )
        self.assertEqual(result["disposition"], "restrip-required")
        self.assertEqual(result["findings"][0]["control"], "strip-length-short")

    def test_a_nicked_conductor_is_reported_as_a_fraction(self):
        diameter = awg_conductor_diameter_mm(GAUGE)
        result = assess_wire_preparation(_spec(nick_depth_mm=diameter * 0.10))
        self.assertAlmostEqual(result["nick_depth_fraction"], 0.10, places=9)
        self.assertEqual(result["disposition"], "restrip-required")

    def test_a_crushed_conductor_is_reported_as_a_reduction(self):
        result = assess_wire_preparation(
            _spec(measured_diameter_mm=awg_conductor_diameter_mm(GAUGE) * 0.75)
        )
        self.assertAlmostEqual(result["diameter_reduction_fraction"], 0.25, places=9)
        self.assertEqual(result["disposition"], "restrip-required")

    def test_an_end_out_of_restrips_is_rejected(self):
        result = assess_wire_preparation(
            _spec(insulation_damaged=True, restrip_count=MAX_RESTRIPS)
        )
        self.assertEqual(result["disposition"], "reject-wire-end")
        controls = [f["control"] for f in result["findings"]]
        self.assertIn("restrip-budget", controls)

    def test_an_end_out_of_restrips_with_nothing_wrong_is_still_accepted(self):
        result = assess_wire_preparation(_spec(restrip_count=MAX_RESTRIPS))
        self.assertEqual(result["disposition"], "accept")
        self.assertEqual(result["restrips_remaining"], 0)

    def test_a_modified_wrap_needs_a_longer_strip(self):
        conventional = assess_wire_preparation(_spec())["required_strip_length_mm"]
        modified = assess_wire_preparation(
            _spec(insulation_turns=1, insulated_diameter_mm=0.8)
        )["required_strip_length_mm"]
        self.assertGreater(modified, conventional)

    def test_findings_are_ranked_critical_first(self):
        result = assess_wire_preparation(
            _spec(
                measured_strip_length_mm=required_strip_length_mm(GAUGE, 6) - 2.0,
                insulation_damaged=True,
            )
        )
        self.assertEqual(result["findings"][0]["severity"], "critical")
        self.assertEqual(result["findings"][-1]["severity"], "major")

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["nick_depth_mm"]
        with self.assertRaises(ValueError):
            assess_wire_preparation(spec)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_wire_preparation([_spec()])

    def test_bound_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(BOUND_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=1)
