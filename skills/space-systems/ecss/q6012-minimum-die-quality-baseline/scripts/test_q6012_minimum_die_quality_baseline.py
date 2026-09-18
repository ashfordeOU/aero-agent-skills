"""Contract tests for the clause 4.3 minimum die quality baseline logic."""

import unittest

from q6012_minimum_die_quality_baseline_logic import (
    ABSOLUTE_FLOOR,
    COMPARISON_TOLERANCE,
    CRITICALITY_BASE,
    LONG_MISSION_YEARS,
    MAX_UPGRADE_STEPS,
    QUALITY_LADDER,
    RADIATION_THRESHOLD_KRAD,
    assess_die_quality,
    base_floor,
    escalation_steps,
    level_at_rank,
    level_rank,
    required_floor,
    upgrade_path,
    validate_application,
    validate_level,
)


def base_spec(**overrides):
    spec = {
        "criticality": "non-critical",
        "mission_years": 3.0,
        "total_dose_krad": 5.0,
        "single_point_failure": False,
        "offered_level": "level-3",
    }
    spec.update(overrides)
    return spec


class LadderTests(unittest.TestCase):
    def test_ladder_is_ascending_and_unique(self):
        self.assertEqual(len(QUALITY_LADDER), len(set(QUALITY_LADDER)))

    def test_absolute_floor_is_on_the_ladder(self):
        self.assertIn(ABSOLUTE_FLOOR, QUALITY_LADDER)

    def test_absolute_floor_is_not_the_bottom_rung(self):
        self.assertGreater(level_rank(ABSOLUTE_FLOOR), 0)

    def test_rank_orders_the_ladder(self):
        self.assertLess(level_rank("commercial"), level_rank("level-3"))
        self.assertLess(level_rank("level-3"), level_rank("level-1"))

    def test_level_at_rank_round_trips(self):
        for rung in QUALITY_LADDER:
            self.assertEqual(level_at_rank(level_rank(rung)), rung)

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_level("space-grade")

    def test_non_string_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_level(3)

    def test_level_token_is_case_insensitive(self):
        self.assertEqual(validate_level("Level-2"), "level-2")

    def test_rank_outside_the_ladder_rejected(self):
        with self.assertRaises(ValueError):
            level_at_rank(len(QUALITY_LADDER))

    def test_boolean_rank_rejected(self):
        with self.assertRaises(ValueError):
            level_at_rank(True)

    def test_every_criticality_maps_onto_the_ladder(self):
        for rung in CRITICALITY_BASE.values():
            self.assertIn(rung, QUALITY_LADDER)


class ApplicationValidationTests(unittest.TestCase):
    def test_defaults_fill_the_optional_keys(self):
        spec = {
            "criticality": "mission-critical",
            "mission_years": 2.0,
            "total_dose_krad": 1.0,
            "offered_level": "level-2",
        }
        application = validate_application(spec)
        self.assertFalse(application["single_point_failure"])
        self.assertIsNone(application["programme_floor"])

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(["criticality"])

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["total_dose_krad"]
        with self.assertRaises(ValueError):
            validate_application(spec)

    def test_unknown_key_rejected_rather_than_ignored(self):
        with self.assertRaises(ValueError):
            validate_application(base_spec(single_point_faliure=True))

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(base_spec(criticality="quite-important"))

    def test_negative_mission_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(base_spec(mission_years=-1.0))

    def test_non_finite_dose_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(base_spec(total_dose_krad=float("nan")))

    def test_non_boolean_single_point_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(base_spec(single_point_failure="yes"))

    def test_unknown_programme_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_application(base_spec(programme_floor="mil-spec"))


class EscalationTests(unittest.TestCase):
    def test_benign_application_earns_no_escalation(self):
        steps, reasons = escalation_steps(validate_application(base_spec()))
        self.assertEqual(steps, 0)
        self.assertEqual(reasons, [])

    def test_long_mission_escalates_one_rung(self):
        steps, _ = escalation_steps(
            validate_application(base_spec(mission_years=LONG_MISSION_YEARS + 2.0))
        )
        self.assertEqual(steps, 1)

    def test_duration_exactly_on_the_threshold_does_not_escalate(self):
        steps, _ = escalation_steps(
            validate_application(base_spec(mission_years=LONG_MISSION_YEARS))
        )
        self.assertEqual(steps, 0)

    def test_dose_exactly_on_the_threshold_does_escalate(self):
        steps, _ = escalation_steps(
            validate_application(base_spec(total_dose_krad=RADIATION_THRESHOLD_KRAD))
        )
        self.assertEqual(steps, 1)

    def test_dose_just_under_the_threshold_does_not_escalate(self):
        steps, _ = escalation_steps(
            validate_application(base_spec(total_dose_krad=RADIATION_THRESHOLD_KRAD * 0.5))
        )
        self.assertEqual(steps, 0)

    def test_single_point_failure_escalates_one_rung(self):
        steps, reasons = escalation_steps(
            validate_application(base_spec(single_point_failure=True))
        )
        self.assertEqual(steps, 1)
        self.assertIn("single point of failure", reasons[0])

    def test_escalations_accumulate(self):
        steps, _ = escalation_steps(validate_application(base_spec(
            mission_years=12.0, total_dose_krad=100.0, single_point_failure=True
        )))
        self.assertEqual(steps, 3)

    def test_escalation_rejects_a_raw_spec(self):
        with self.assertRaises(ValueError):
            escalation_steps(["criticality"])

    def test_tolerance_is_small_and_relative(self):
        self.assertLess(COMPARISON_TOLERANCE, 1e-6)


class RequiredFloorTests(unittest.TestCase):
    def test_base_floor_follows_criticality(self):
        self.assertEqual(base_floor("safety-critical"), "level-1")
        self.assertEqual(base_floor("non-critical"), "level-3")

    def test_base_floor_rejects_an_unknown_token(self):
        with self.assertRaises(ValueError):
            base_floor("critical-ish")

    def test_benign_non_critical_application_sits_at_the_absolute_floor(self):
        floor = required_floor(validate_application(base_spec()))
        self.assertEqual(floor["level"], ABSOLUTE_FLOOR)

    def test_escalation_raises_the_floor(self):
        floor = required_floor(validate_application(base_spec(single_point_failure=True)))
        self.assertEqual(floor["level"], "level-2")

    def test_escalation_is_capped_at_the_top_rung(self):
        floor = required_floor(validate_application(base_spec(
            criticality="safety-critical", mission_years=12.0,
            total_dose_krad=100.0, single_point_failure=True, offered_level="level-1"
        )))
        self.assertEqual(floor["level"], QUALITY_LADDER[-1])
        self.assertTrue(floor["capped_at_top"])

    def test_programme_floor_can_raise_but_not_lower(self):
        raised = required_floor(validate_application(base_spec(programme_floor="level-1")))
        self.assertEqual(raised["level"], "level-1")
        self.assertTrue(raised["programme_raised"])
        lowered = required_floor(validate_application(base_spec(programme_floor="commercial")))
        self.assertEqual(lowered["level"], ABSOLUTE_FLOOR)
        self.assertFalse(lowered["programme_raised"])

    def test_floor_reports_its_reasons(self):
        floor = required_floor(validate_application(base_spec(
            criticality="mission-critical", single_point_failure=True,
            offered_level="level-1"
        )))
        self.assertTrue(floor["reasons"])


class UpgradePathTests(unittest.TestCase):
    def test_one_rung_path_names_the_target_actions(self):
        path = upgrade_path("screened-industrial", "level-3")
        self.assertEqual(len(path), 1)
        self.assertEqual(path[0]["to_level"], "level-3")
        self.assertTrue(path[0]["actions"])

    def test_two_rung_path_is_reported_rung_by_rung(self):
        path = upgrade_path("industrial", "level-3")
        self.assertEqual([r["to_level"] for r in path], ["screened-industrial", "level-3"])

    def test_same_level_gives_an_empty_path(self):
        self.assertEqual(upgrade_path("level-2", "level-2"), [])

    def test_downward_target_rejected(self):
        with self.assertRaises(ValueError):
            upgrade_path("level-1", "level-3")

    def test_unknown_level_in_the_path_rejected(self):
        with self.assertRaises(ValueError):
            upgrade_path("level-3", "space-grade")

    def test_path_rungs_are_contiguous(self):
        path = upgrade_path("commercial", "level-2")
        for record in path:
            self.assertEqual(level_rank(record["to_level"]) - level_rank(record["from_level"]), 1)


class AssessmentTests(unittest.TestCase):
    def test_die_at_the_floor_is_acceptable_as_procured(self):
        result = assess_die_quality(base_spec())
        self.assertTrue(result["acceptable_as_procured"])
        self.assertTrue(result["clear"])
        self.assertEqual(result["gap_rungs"], 0)

    def test_die_above_the_floor_is_accepted_with_a_note(self):
        result = assess_die_quality(base_spec(offered_level="level-1"))
        self.assertTrue(result["acceptable_as_procured"])
        self.assertTrue(any("above the floor" in n for n in result["notes"]))

    def test_one_rung_short_is_upgradable(self):
        result = assess_die_quality(base_spec(offered_level="screened-industrial"))
        self.assertFalse(result["acceptable_as_procured"])
        self.assertTrue(result["upgradable"])
        self.assertEqual(result["gap_rungs"], 1)
        self.assertEqual(len(result["upgrade_path"]), 1)

    def test_two_rungs_short_is_still_upgradable(self):
        result = assess_die_quality(base_spec(offered_level="industrial"))
        self.assertTrue(result["upgradable"])
        self.assertEqual(len(result["upgrade_path"]), MAX_UPGRADE_STEPS)

    def test_three_rungs_short_is_refused_not_uprated(self):
        result = assess_die_quality(base_spec(offered_level="commercial"))
        self.assertFalse(result["upgradable"])
        self.assertEqual(result["upgrade_path"], [])
        self.assertTrue(any("refused" in f for f in result["findings"]))

    def test_below_the_absolute_floor_is_always_a_finding(self):
        result = assess_die_quality(base_spec(offered_level="industrial"))
        self.assertTrue(any(ABSOLUTE_FLOOR in f and "lowest rung" in f
                            for f in result["findings"]))

    def test_escalated_floor_moves_an_acceptable_die_into_a_gap(self):
        clean = assess_die_quality(base_spec(offered_level="level-3"))
        escalated = assess_die_quality(
            base_spec(offered_level="level-3", single_point_failure=True)
        )
        self.assertTrue(clean["acceptable_as_procured"])
        self.assertFalse(escalated["acceptable_as_procured"])

    def test_required_level_and_reasons_are_reported(self):
        result = assess_die_quality(base_spec(criticality="safety-critical",
                                              offered_level="level-1"))
        self.assertEqual(result["required_level"], "level-1")
        self.assertIsInstance(result["required_reasons"], list)

    def test_programme_floor_drives_the_assessment(self):
        result = assess_die_quality(base_spec(offered_level="level-3",
                                              programme_floor="level-2"))
        self.assertFalse(result["acceptable_as_procured"])
        self.assertEqual(result["required_level"], "level-2")

    def test_capped_escalation_is_noted(self):
        result = assess_die_quality(base_spec(
            criticality="safety-critical", mission_years=12.0,
            total_dose_krad=100.0, single_point_failure=True,
            offered_level="level-1"
        ))
        self.assertTrue(any("capped" in n for n in result["notes"]))

    def test_assessment_rejects_a_bad_spec(self):
        with self.assertRaises(ValueError):
            assess_die_quality(base_spec(offered_level="space-grade"))

    def test_assessment_echoes_the_normalised_application(self):
        result = assess_die_quality(base_spec(criticality="Mission-Critical",
                                              offered_level="level-2"))
        self.assertEqual(result["application"]["criticality"], "mission-critical")


if __name__ == "__main__":
    unittest.main()
