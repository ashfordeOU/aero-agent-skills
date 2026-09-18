#!/usr/bin/env python3
"""Contract tests for the clause 7.3 MMIC design-review programme logic."""

import unittest

from q6012_mmic_design_review_process_logic import (
    CANONICAL_CHECKPOINTS,
    CLOSURE_TOLERANCE,
    action_closure_ratio,
    assess_design_review_process,
    coverage_fraction,
    missing_checkpoints,
    normalise_programme,
    programme_slip_days,
    release_readiness,
    schedule_slip_days,
    sequence_violations,
    validate_checkpoint,
)


def full_programme(**overrides):
    """A five-gate programme held in order with every action closed."""
    base = [
        {"key": "requirements", "planned_day": 10, "held_day": 10,
         "actions_raised": 4, "actions_closed": 4},
        {"key": "architecture", "planned_day": 30, "held_day": 32,
         "actions_raised": 6, "actions_closed": 6},
        {"key": "detailed-design", "planned_day": 60, "held_day": 61,
         "actions_raised": 9, "actions_closed": 9},
        {"key": "layout", "planned_day": 90, "held_day": 90,
         "actions_raised": 3, "actions_closed": 3},
        {"key": "pre-release", "planned_day": 110, "held_day": 112,
         "actions_raised": 2, "actions_closed": 2},
    ]
    by_key = {entry["key"]: entry for entry in base}
    for key, patch in overrides.items():
        by_key[key.replace("_", "-")].update(patch)
    return list(by_key.values())


def spec(**kwargs):
    payload = {
        "checkpoints": full_programme(),
        "fabrication_release_day": 120,
        "required_closure_ratio": 1.0,
        "quiet_period_days": 5,
    }
    payload.update(kwargs)
    return payload


class ValidateCheckpointTests(unittest.TestCase):
    def test_normalises_a_held_gate(self):
        record = validate_checkpoint(
            {"key": "layout", "planned_day": 90, "held_day": 93}
        )
        self.assertTrue(record["held"])
        self.assertEqual(record["order"], CANONICAL_CHECKPOINTS.index("layout"))

    def test_unheld_gate_carries_none_day(self):
        record = validate_checkpoint({"key": "layout", "planned_day": 90})
        self.assertIsNone(record["held_day"])
        self.assertFalse(record["held"])

    def test_unknown_checkpoint_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_checkpoint({"key": "tape-out-party", "planned_day": 5})

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_checkpoint(["layout", 90])

    def test_boolean_planned_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_checkpoint({"key": "layout", "planned_day": True})

    def test_negative_planned_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_checkpoint({"key": "layout", "planned_day": -1})

    def test_float_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_checkpoint({"key": "layout", "planned_day": 90.5})

    def test_closing_more_actions_than_raised_rejected(self):
        with self.assertRaises(ValueError):
            validate_checkpoint(
                {"key": "layout", "planned_day": 90, "held_day": 90,
                 "actions_raised": 2, "actions_closed": 3}
            )

    def test_unheld_gate_cannot_raise_actions(self):
        with self.assertRaises(ValueError):
            validate_checkpoint(
                {"key": "layout", "planned_day": 90, "actions_raised": 2}
            )

    def test_non_boolean_mandatory_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_checkpoint(
                {"key": "layout", "planned_day": 90, "mandatory": "yes"}
            )


class NormaliseProgrammeTests(unittest.TestCase):
    def test_sorts_into_canonical_order(self):
        shuffled = list(reversed(full_programme()))
        keys = [r["key"] for r in normalise_programme(shuffled)]
        self.assertEqual(tuple(keys), CANONICAL_CHECKPOINTS)

    def test_duplicate_checkpoint_rejected(self):
        entries = full_programme()
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            normalise_programme(entries)

    def test_empty_programme_rejected(self):
        with self.assertRaises(ValueError):
            normalise_programme([])

    def test_non_sequence_programme_rejected(self):
        with self.assertRaises(ValueError):
            normalise_programme({"key": "layout"})


class MissingAndSequenceTests(unittest.TestCase):
    def test_complete_programme_misses_nothing(self):
        self.assertEqual(missing_checkpoints(normalise_programme(full_programme())), [])

    def test_absent_gate_is_missing(self):
        entries = [e for e in full_programme() if e["key"] != "layout"]
        self.assertEqual(missing_checkpoints(normalise_programme(entries)), ["layout"])

    def test_planned_but_unheld_gate_is_missing(self):
        entries = full_programme(pre_release={"held_day": None, "actions_raised": 0,
                                              "actions_closed": 0})
        self.assertIn("pre-release", missing_checkpoints(normalise_programme(entries)))

    def test_optional_unheld_gate_is_not_missing(self):
        entries = full_programme(layout={"held_day": None, "actions_raised": 0,
                                         "actions_closed": 0, "mandatory": False})
        self.assertNotIn("layout", missing_checkpoints(normalise_programme(entries)))

    def test_in_order_programme_has_no_violation(self):
        self.assertEqual(sequence_violations(normalise_programme(full_programme())), [])

    def test_gate_held_too_early_is_a_violation(self):
        entries = full_programme(layout={"held_day": 40})
        violations = sequence_violations(normalise_programme(entries))
        self.assertIn(("detailed-design", "layout"), violations)

    def test_same_day_gates_are_not_a_violation(self):
        entries = full_programme(layout={"held_day": 61})
        self.assertEqual(sequence_violations(normalise_programme(entries)), [])


class SlipAndRatioTests(unittest.TestCase):
    def test_slip_is_held_minus_planned(self):
        record = validate_checkpoint(
            {"key": "architecture", "planned_day": 30, "held_day": 32}
        )
        self.assertEqual(schedule_slip_days(record), 2)

    def test_early_gate_has_negative_slip(self):
        record = validate_checkpoint(
            {"key": "architecture", "planned_day": 30, "held_day": 28}
        )
        self.assertEqual(schedule_slip_days(record), -2)

    def test_unheld_gate_has_no_slip(self):
        record = validate_checkpoint({"key": "architecture", "planned_day": 30})
        with self.assertRaises(ValueError):
            schedule_slip_days(record)

    def test_programme_slip_is_the_worst_positive_slip(self):
        self.assertEqual(programme_slip_days(normalise_programme(full_programme())), 2)

    def test_programme_ahead_of_plan_reports_zero_slip(self):
        entries = full_programme(
            requirements={"held_day": 8}, architecture={"held_day": 29},
            detailed_design={"held_day": 59}, layout={"held_day": 88},
            pre_release={"held_day": 105},
        )
        self.assertEqual(programme_slip_days(normalise_programme(entries)), 0)

    def test_closure_ratio_of_a_clean_programme_is_one(self):
        self.assertAlmostEqual(
            action_closure_ratio(normalise_programme(full_programme())), 1.0, places=9
        )

    def test_closure_ratio_counts_only_held_gates(self):
        entries = full_programme(pre_release={"actions_closed": 0})
        ratio = action_closure_ratio(normalise_programme(entries))
        self.assertAlmostEqual(ratio, 22.0 / 24.0, places=9)

    def test_closure_ratio_without_actions_is_one(self):
        entries = [
            {"key": key, "planned_day": 10 * i, "held_day": 10 * i}
            for i, key in enumerate(CANONICAL_CHECKPOINTS, start=1)
        ]
        self.assertAlmostEqual(action_closure_ratio(normalise_programme(entries)), 1.0,
                               places=9)

    def test_coverage_of_a_full_programme_is_one(self):
        self.assertAlmostEqual(
            coverage_fraction(normalise_programme(full_programme())), 1.0, places=9
        )

    def test_coverage_drops_when_a_gate_is_absent(self):
        entries = [e for e in full_programme() if e["key"] != "layout"]
        self.assertAlmostEqual(
            coverage_fraction(normalise_programme(entries)), 0.8, places=9
        )


class ReleaseReadinessTests(unittest.TestCase):
    def test_clean_programme_releases(self):
        verdict = release_readiness(
            normalise_programme(full_programme()), 120, 1.0, 5
        )
        self.assertTrue(verdict["released"])

    def test_release_inside_the_quiet_period_is_held(self):
        verdict = release_readiness(
            normalise_programme(full_programme()), 114, 1.0, 5
        )
        self.assertFalse(verdict["quiet_period_met"])
        self.assertFalse(verdict["released"])

    def test_release_exactly_on_the_quiet_period_boundary_is_met(self):
        verdict = release_readiness(
            normalise_programme(full_programme()), 117, 1.0, 5
        )
        self.assertTrue(verdict["quiet_period_met"])
        self.assertTrue(verdict["released"])

    def test_closure_ratio_exactly_at_the_required_value_passes(self):
        entries = full_programme(pre_release={"actions_closed": 0})
        verdict = release_readiness(normalise_programme(entries), 120, 22.0 / 24.0, 5)
        self.assertAlmostEqual(
            verdict["closure_ratio"], verdict["required_closure_ratio"], places=9
        )
        self.assertTrue(verdict["closure_ratio_met"])

    def test_closure_ratio_below_the_required_value_holds_release(self):
        entries = full_programme(pre_release={"actions_closed": 0})
        verdict = release_readiness(normalise_programme(entries), 120, 1.0, 5)
        self.assertFalse(verdict["closure_ratio_met"])
        self.assertFalse(verdict["released"])

    def test_required_ratio_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            release_readiness(normalise_programme(full_programme()), 120, 1.5, 0)

    def test_boolean_required_ratio_rejected(self):
        with self.assertRaises(ValueError):
            release_readiness(normalise_programme(full_programme()), 120, True, 0)

    def test_negative_quiet_period_rejected(self):
        with self.assertRaises(ValueError):
            release_readiness(normalise_programme(full_programme()), 120, 1.0, -1)

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(CLOSURE_TOLERANCE, 1e-6)


class AssessDesignReviewProcessTests(unittest.TestCase):
    def test_clean_programme_has_no_findings(self):
        result = assess_design_review_process(spec())
        self.assertTrue(result["released"])
        self.assertEqual(result["findings"], [])

    def test_missing_gate_is_reported_and_blocks_release(self):
        entries = [e for e in full_programme() if e["key"] != "architecture"]
        result = assess_design_review_process(spec(checkpoints=entries))
        self.assertFalse(result["released"])
        self.assertTrue(any("architecture" in f for f in result["findings"]))

    def test_out_of_sequence_gate_is_reported(self):
        result = assess_design_review_process(
            spec(checkpoints=full_programme(layout={"held_day": 40}))
        )
        self.assertFalse(result["released"])
        self.assertTrue(any("held before" in f for f in result["findings"]))

    def test_open_actions_are_reported(self):
        result = assess_design_review_process(
            spec(checkpoints=full_programme(detailed_design={"actions_closed": 5}))
        )
        self.assertFalse(result["released"])
        self.assertTrue(any("closure ratio" in f for f in result["findings"]))

    def test_max_slip_is_carried_into_the_result(self):
        result = assess_design_review_process(
            spec(checkpoints=full_programme(layout={"held_day": 99}))
        )
        self.assertEqual(result["max_slip_days"], 9)

    def test_missing_spec_key_rejected(self):
        payload = spec()
        del payload["fabrication_release_day"]
        with self.assertRaises(ValueError):
            assess_design_review_process(payload)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_review_process(["checkpoints"])


if __name__ == "__main__":
    unittest.main()
