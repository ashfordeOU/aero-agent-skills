"""Contract tests for the clause 5.4.1.4.1 on-command spacing logic."""

import unittest

from e2020_minimum_interval_between_on_commands_logic import (
    EXTERNALLY_COMMANDED_CATEGORIES,
    INTERVAL_CONTRIBUTORS,
    INTERVAL_TOLERANCE_MS,
    LIMITER_CATEGORIES,
    assess_on_command_spacing,
    command_gaps_ms,
    earliest_admissible_time_ms,
    governing_constraint,
    max_on_command_rate_hz,
    normalise_category,
    repair_schedule_ms,
    required_interval_ms,
    spacing_violations,
    validate_constraints,
    validate_schedule,
)

# A latching channel that declares a 100 ms minimum between on commands, with
# a schedule that respects it exactly.
BASE = {
    "category": "latching",
    "declared_min_interval_ms": 100.0,
    "command_times_ms": [0.0, 100.0, 300.0, 600.0],
}


def spec(**overrides):
    merged = dict(BASE)
    merged["command_times_ms"] = list(BASE["command_times_ms"])
    merged.update(overrides)
    return merged


class NormalisationTests(unittest.TestCase):
    def test_category_aliases_are_folded(self):
        self.assertEqual(normalise_category("LCL"), "latching")
        self.assertEqual(normalise_category(" HPC "), "high-power")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalise_category("contactor")

    def test_non_string_category_rejected(self):
        with self.assertRaises(ValueError):
            normalise_category(None)

    def test_vocabularies_are_fixed(self):
        self.assertEqual(
            EXTERNALLY_COMMANDED_CATEGORIES, ("latching", "high-power")
        )
        self.assertIn("retriggerable", LIMITER_CATEGORIES)
        self.assertEqual(INTERVAL_CONTRIBUTORS[0], "declared_min_interval_ms")


class ConstraintValidationTests(unittest.TestCase):
    def test_declared_interval_alone_is_a_valid_constraint_set(self):
        constraints = validate_constraints(spec())
        self.assertAlmostEqual(
            constraints["declared_min_interval_ms"], 100.0, places=9
        )
        self.assertNotIn("thermal_recovery_ms", constraints)

    def test_optional_contributors_are_carried_when_present(self):
        constraints = validate_constraints(spec(thermal_recovery_ms=250.0))
        self.assertAlmostEqual(constraints["thermal_recovery_ms"], 250.0, places=9)

    def test_none_valued_optional_contributor_is_ignored(self):
        constraints = validate_constraints(spec(inrush_settling_ms=None))
        self.assertNotIn("inrush_settling_ms", constraints)

    def test_non_mapping_constraints_rejected(self):
        with self.assertRaises(ValueError):
            validate_constraints(["latching"])

    def test_missing_declared_interval_rejected(self):
        broken = spec()
        del broken["declared_min_interval_ms"]
        with self.assertRaises(ValueError):
            validate_constraints(broken)

    def test_zero_declared_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_constraints(spec(declared_min_interval_ms=0.0))

    def test_negative_thermal_recovery_rejected(self):
        with self.assertRaises(ValueError):
            validate_constraints(spec(thermal_recovery_ms=-10.0))

    def test_boolean_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_constraints(spec(declared_min_interval_ms=True))


class ScheduleValidationTests(unittest.TestCase):
    def test_ascending_schedule_is_accepted(self):
        self.assertEqual(validate_schedule([0.0, 100.0]), [0.0, 100.0])

    def test_empty_schedule_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule([])

    def test_non_sequence_schedule_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule(100.0)

    def test_out_of_order_schedule_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule([0.0, 200.0, 150.0])

    def test_repeated_command_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule([0.0, 100.0, 100.0])

    def test_negative_command_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule([-1.0, 100.0])

    def test_non_numeric_command_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule([0.0, "100"])


class IntervalTests(unittest.TestCase):
    def test_declared_figure_governs_when_it_is_the_longest(self):
        constraints = validate_constraints(
            spec(thermal_recovery_ms=40.0, inrush_settling_ms=20.0)
        )
        self.assertAlmostEqual(required_interval_ms(constraints), 100.0, places=9)
        self.assertEqual(governing_constraint(constraints), "declared_min_interval_ms")

    def test_thermal_recovery_governs_when_it_is_longer(self):
        constraints = validate_constraints(spec(thermal_recovery_ms=250.0))
        self.assertAlmostEqual(required_interval_ms(constraints), 250.0, places=9)
        self.assertEqual(governing_constraint(constraints), "thermal_recovery_ms")

    def test_inrush_settling_can_govern_on_its_own(self):
        constraints = validate_constraints(
            spec(thermal_recovery_ms=120.0, inrush_settling_ms=400.0)
        )
        self.assertEqual(governing_constraint(constraints), "inrush_settling_ms")

    def test_a_tie_resolves_to_the_declared_figure(self):
        constraints = validate_constraints(spec(thermal_recovery_ms=100.0))
        self.assertEqual(governing_constraint(constraints), "declared_min_interval_ms")

    def test_command_rate_is_the_reciprocal_of_the_governing_interval(self):
        constraints = validate_constraints(spec())
        self.assertAlmostEqual(max_on_command_rate_hz(constraints), 10.0, places=9)

    def test_command_rate_falls_when_a_longer_contributor_governs(self):
        constraints = validate_constraints(spec(thermal_recovery_ms=250.0))
        self.assertAlmostEqual(max_on_command_rate_hz(constraints), 4.0, places=9)

    def test_earliest_admissible_time_adds_the_governing_interval(self):
        constraints = validate_constraints(spec())
        self.assertAlmostEqual(
            earliest_admissible_time_ms(300.0, constraints), 400.0, places=9
        )

    def test_earliest_admissible_time_rejects_a_negative_instant(self):
        constraints = validate_constraints(spec())
        with self.assertRaises(ValueError):
            earliest_admissible_time_ms(-1.0, constraints)


class SpacingTests(unittest.TestCase):
    def test_gaps_are_one_shorter_than_the_schedule(self):
        gaps = command_gaps_ms([0.0, 100.0, 300.0, 600.0])
        self.assertEqual(len(gaps), 3)
        self.assertAlmostEqual(gaps[0], 100.0, places=9)
        self.assertAlmostEqual(gaps[2], 300.0, places=9)

    def test_gap_exactly_on_the_interval_is_admissible(self):
        constraints = validate_constraints(spec())
        self.assertEqual(spacing_violations(constraints, [0.0, 100.0]), [])

    def test_gap_below_the_interval_is_a_violation_with_its_shortfall(self):
        constraints = validate_constraints(spec())
        violations = spacing_violations(constraints, [0.0, 60.0])
        self.assertEqual(len(violations), 1)
        self.assertAlmostEqual(violations[0]["shortfall_ms"], 40.0, places=9)
        self.assertEqual(violations[0]["index"], 1)

    def test_every_offending_pair_is_reported_not_just_the_first(self):
        constraints = validate_constraints(spec())
        violations = spacing_violations(constraints, [0.0, 10.0, 20.0, 400.0])
        self.assertEqual([v["index"] for v in violations], [1, 2])

    def test_single_command_schedule_has_no_pairs_to_grade(self):
        constraints = validate_constraints(spec())
        self.assertEqual(spacing_violations(constraints, [0.0]), [])


class RepairTests(unittest.TestCase):
    def test_admissible_schedule_is_returned_unchanged(self):
        constraints = validate_constraints(spec())
        self.assertEqual(
            repair_schedule_ms(constraints, [0.0, 100.0, 300.0]), [0.0, 100.0, 300.0]
        )

    def test_repair_pushes_a_close_command_to_the_earliest_instant(self):
        constraints = validate_constraints(spec())
        repaired = repair_schedule_ms(constraints, [0.0, 60.0])
        self.assertAlmostEqual(repaired[1], 100.0, places=9)

    def test_repair_cascades_through_the_commands_behind_it(self):
        constraints = validate_constraints(spec())
        repaired = repair_schedule_ms(constraints, [0.0, 10.0, 20.0])
        self.assertAlmostEqual(repaired[1], 100.0, places=9)
        self.assertAlmostEqual(repaired[2], 200.0, places=9)

    def test_repair_never_moves_a_command_earlier_than_requested(self):
        constraints = validate_constraints(spec())
        repaired = repair_schedule_ms(constraints, [0.0, 10.0, 900.0])
        self.assertAlmostEqual(repaired[2], 900.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_schedule_respecting_the_interval_is_compliant(self):
        result = assess_on_command_spacing(spec())
        self.assertEqual(result["verdict"], "compliant")
        self.assertTrue(result["admissible"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["schedule_shift_ms"], 0.0, places=9)

    def test_high_power_category_is_graded_the_same_way(self):
        result = assess_on_command_spacing(spec(category="high-power"))
        self.assertEqual(result["verdict"], "compliant")

    def test_crowded_schedule_is_non_compliant_and_names_the_shortfall(self):
        result = assess_on_command_spacing(spec(command_times_ms=[0.0, 60.0, 500.0]))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("40 ms short" in f for f in result["findings"]))

    def test_repair_is_reported_alongside_the_violation(self):
        result = assess_on_command_spacing(spec(command_times_ms=[0.0, 10.0, 20.0]))
        self.assertEqual(result["repaired_schedule_ms"], [0.0, 100.0, 200.0])
        self.assertAlmostEqual(result["schedule_shift_ms"], 180.0, places=9)

    def test_declared_figure_shorter_than_thermal_recovery_is_a_finding(self):
        result = assess_on_command_spacing(
            spec(thermal_recovery_ms=250.0, command_times_ms=[0.0, 300.0, 600.0])
        )
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(result["governing_constraint"], "thermal_recovery_ms")
        self.assertTrue(any("re-triggers" in f for f in result["findings"]))

    def test_governing_interval_drives_the_violation_list(self):
        result = assess_on_command_spacing(
            spec(thermal_recovery_ms=250.0, command_times_ms=[0.0, 150.0])
        )
        self.assertAlmostEqual(result["required_interval_ms"], 250.0, places=9)
        self.assertEqual(len(result["violations"]), 1)
        self.assertAlmostEqual(result["violations"][0]["shortfall_ms"], 100.0, places=9)

    def test_gap_exactly_on_the_governing_interval_still_passes(self):
        result = assess_on_command_spacing(
            spec(thermal_recovery_ms=100.0, command_times_ms=[0.0, 100.0])
        )
        self.assertAlmostEqual(result["gaps_ms"][0], 100.0, places=9)
        self.assertEqual(result["verdict"], "compliant")

    def test_retriggerable_category_is_reported_out_of_scope(self):
        result = assess_on_command_spacing(spec(category="retriggerable"))
        self.assertEqual(result["verdict"], "out-of-scope")
        self.assertFalse(result["in_scope"])

    def test_missing_schedule_key_rejected(self):
        broken = spec()
        del broken["command_times_ms"]
        with self.assertRaises(ValueError):
            assess_on_command_spacing(broken)

    def test_command_count_and_rate_are_reported(self):
        result = assess_on_command_spacing(spec())
        self.assertEqual(result["command_count"], 4)
        self.assertAlmostEqual(result["max_on_command_rate_hz"], 10.0, places=9)

    def test_interval_tolerance_is_representation_sized(self):
        self.assertLess(INTERVAL_TOLERANCE_MS, 1e-6)


if __name__ == "__main__":
    unittest.main()
