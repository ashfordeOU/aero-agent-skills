#!/usr/bin/env python3
"""Contract test for the Class 1 baseline selection rules (offline).

Walks the clause workflow step by step: the candidate part validation,
the certified quality system, the franchised distribution path as a hard
rule, flight lot homogeneity, the temperature envelope arithmetic
including the exact-boundary case, the change-notification agreement,
the conditional heritage-or-evaluation rule and its distinct verdict,
and the roll-up over a whole design part set. This is the gate 3 review
evidence for the leaf.
"""

import copy
import unittest

from q6013_class_1_selection_rules_logic import (
    DESIGN_ADMISSIBLE,
    DESIGN_NOT_ADMISSIBLE,
    HARD_RULES,
    PART_ADMISSIBLE,
    PART_ADMISSIBLE_WITH_EVALUATION,
    PART_NOT_ADMISSIBLE,
    SELECTION_RULES,
    apply_selection_rules,
    assess_design_part_set,
    resolve_policy,
    temperature_envelope,
    validate_part,
    validate_range,
)


def _part(part_id, **overrides):
    record = {
        "part_id": part_id,
        "quality_system": "certified",
        "distribution_path": "franchised-distributor",
        "wafer_lots": 1,
        "assembly_lots": 1,
        "rated_temperature_range": (-55.0, 125.0),
        "mission_temperature_range": (-40.0, 85.0),
        "change_notification_agreement": True,
        "qualification_heritage": True,
        "evaluation_plan": False,
    }
    record.update(copy.deepcopy(overrides))
    return record


def _case(count=4):
    return {
        "design_id": "DSN-6013",
        "parts": [_part("PRT-%02d" % index) for index in range(count)],
    }


def _rule(result, name):
    return next(r for r in result["rules"] if r["rule"] == name)


class PartValidationTests(unittest.TestCase):
    def test_a_sound_part_validates(self):
        record = validate_part(_part("PRT-00"))
        self.assertEqual(record["distribution_path"], "franchised-distributor")
        self.assertEqual(record["wafer_lots"], 1)

    def test_an_unknown_distribution_path_rejected(self):
        with self.assertRaises(ValueError):
            validate_part(_part("PRT-00", distribution_path="a friend of the team"))

    def test_an_unknown_quality_system_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_part(_part("PRT-00", quality_system="probably-fine"))

    def test_a_zero_lot_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_part(_part("PRT-00", wafer_lots=0))

    def test_a_non_boolean_agreement_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_part(_part("PRT-00", change_notification_agreement="yes"))

    def test_an_inverted_temperature_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_range("rated_temperature_range", (125.0, -55.0))

    def test_a_three_element_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_range("rated_temperature_range", (-55.0, 25.0, 125.0))


class TemperatureEnvelopeTests(unittest.TestCase):
    def test_a_wide_rated_range_envelopes_the_mission(self):
        result = temperature_envelope((-55.0, 125.0), (-40.0, 85.0))
        self.assertTrue(result["envelopes"])
        self.assertAlmostEqual(result["cold_margin_k"], 15.0, places=9)
        self.assertAlmostEqual(result["hot_margin_k"], 40.0, places=9)
        self.assertAlmostEqual(result["worst_margin_k"], 15.0, places=9)

    def test_an_exactly_matching_range_sits_on_the_zero_margin_bound(self):
        result = temperature_envelope((-40.0, 85.0), (-40.0, 85.0), 0.0)
        self.assertAlmostEqual(result["cold_margin_k"], 0.0, places=9)
        self.assertAlmostEqual(result["hot_margin_k"], 0.0, places=9)
        self.assertTrue(result["envelopes"])
        self.assertEqual(result["findings"], [])

    def test_a_declared_margin_turns_the_boundary_case_into_a_shortfall(self):
        result = temperature_envelope((-40.0, 85.0), (-40.0, 85.0), 10.0)
        self.assertFalse(result["envelopes"])
        self.assertEqual(len(result["findings"]), 2)

    def test_a_cold_end_shortfall_is_named_on_its_own(self):
        result = temperature_envelope((-20.0, 125.0), (-40.0, 85.0))
        self.assertFalse(result["envelopes"])
        self.assertAlmostEqual(result["cold_margin_k"], -20.0, places=9)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("cold end", result["findings"][0])

    def test_a_negative_declared_margin_rejected(self):
        with self.assertRaises(ValueError):
            temperature_envelope((-55.0, 125.0), (-40.0, 85.0), -5.0)


class BaselineRuleTests(unittest.TestCase):
    def test_a_clean_part_is_admissible(self):
        result = apply_selection_rules(_part("PRT-00"))
        self.assertEqual(result["verdict"], PART_ADMISSIBLE)
        self.assertEqual(result["failed_rules"], [])
        self.assertEqual(result["findings"], [])

    def test_every_baseline_rule_is_applied(self):
        result = apply_selection_rules(_part("PRT-00"))
        self.assertEqual(
            [r["rule"] for r in result["rules"]], list(SELECTION_RULES)
        )

    def test_a_broker_source_bars_the_part_outright(self):
        result = apply_selection_rules(
            _part("PRT-00", distribution_path="open-market-broker")
        )
        self.assertEqual(result["verdict"], PART_NOT_ADMISSIBLE)
        self.assertIn("franchised-distribution-path", result["failed_rules"])
        self.assertTrue(any("chain of custody" in f for f in result["findings"]))

    def test_a_self_declared_quality_system_bars_the_part(self):
        result = apply_selection_rules(_part("PRT-00", quality_system="self-declared"))
        self.assertEqual(result["verdict"], PART_NOT_ADMISSIBLE)
        self.assertIn("manufacturer-quality-system", result["failed_rules"])

    def test_a_multi_lot_flight_build_bars_the_part(self):
        result = apply_selection_rules(_part("PRT-00", assembly_lots=3))
        self.assertEqual(result["verdict"], PART_NOT_ADMISSIBLE)
        self.assertIn("flight-lot-homogeneity", result["failed_rules"])

    def test_a_relaxed_lot_limit_admits_the_same_part(self):
        result = apply_selection_rules(
            _part("PRT-00", assembly_lots=3), {"max_flight_lots": 3}
        )
        self.assertEqual(result["verdict"], PART_ADMISSIBLE)

    def test_a_missing_change_notification_agreement_bars_the_part(self):
        result = apply_selection_rules(
            _part("PRT-00", change_notification_agreement=False)
        )
        self.assertEqual(result["verdict"], PART_NOT_ADMISSIBLE)
        self.assertIn("change-notification-agreement", result["failed_rules"])

    def test_an_evaluation_plan_replaces_heritage_but_not_silently(self):
        result = apply_selection_rules(
            _part("PRT-00", qualification_heritage=False, evaluation_plan=True)
        )
        self.assertEqual(result["verdict"], PART_ADMISSIBLE_WITH_EVALUATION)
        self.assertEqual(result["failed_rules"], [])
        self.assertTrue(
            any("committed activity" in f for f in result["findings"])
        )

    def test_neither_heritage_nor_plan_bars_the_part(self):
        result = apply_selection_rules(
            _part("PRT-00", qualification_heritage=False, evaluation_plan=False)
        )
        self.assertEqual(result["verdict"], PART_NOT_ADMISSIBLE)
        self.assertIn("qualification-heritage-or-plan", result["failed_rules"])

    def test_a_policy_refusing_plans_for_heritage_bars_the_part(self):
        result = apply_selection_rules(
            _part("PRT-00", qualification_heritage=False, evaluation_plan=True),
            {"accept_evaluation_for_heritage": False},
        )
        self.assertEqual(result["verdict"], PART_NOT_ADMISSIBLE)

    def test_the_hard_rules_are_marked_hard(self):
        result = apply_selection_rules(_part("PRT-00"))
        for name in HARD_RULES:
            self.assertTrue(_rule(result, name)["hard"])
        self.assertFalse(_rule(result, "qualification-heritage-or-plan")["hard"])


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve_to_a_single_lot_and_zero_margin(self):
        settings = resolve_policy()
        self.assertAlmostEqual(settings["min_temperature_margin_k"], 0.0, places=9)
        self.assertEqual(settings["max_flight_lots"], 1)

    def test_a_negative_declared_margin_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"min_temperature_margin_k": -1.0})

    def test_a_fractional_lot_limit_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"max_flight_lots": 1.5})


class DesignRollUpTests(unittest.TestCase):
    def test_a_clean_part_set_is_admissible(self):
        result = assess_design_part_set(_case())
        self.assertEqual(result["verdict"], DESIGN_ADMISSIBLE)
        self.assertEqual(result["evaluations_owed"], [])

    def test_one_barred_part_bars_the_set(self):
        case = _case()
        case["parts"][2]["distribution_path"] = "unknown-source"
        result = assess_design_part_set(case)
        self.assertEqual(result["verdict"], DESIGN_NOT_ADMISSIBLE)
        self.assertEqual(result["weakest_part"], "PRT-02")

    def test_the_evaluations_owed_are_listed_without_barring_the_set(self):
        case = _case()
        case["parts"][1]["qualification_heritage"] = False
        case["parts"][1]["evaluation_plan"] = True
        result = assess_design_part_set(case)
        self.assertEqual(result["verdict"], DESIGN_ADMISSIBLE)
        self.assertEqual(result["evaluations_owed"], ["PRT-01"])

    def test_a_design_margin_policy_reaches_every_part(self):
        case = _case(count=2)
        case["policy"] = {"min_temperature_margin_k": 20.0}
        result = assess_design_part_set(case)
        self.assertEqual(result["verdict"], DESIGN_NOT_ADMISSIBLE)
        self.assertEqual(len(result["grouped_parts"][PART_NOT_ADMISSIBLE]), 2)

    def test_a_part_listed_twice_rejected(self):
        case = _case()
        case["parts"].append(copy.deepcopy(case["parts"][0]))
        with self.assertRaises(ValueError):
            assess_design_part_set(case)

    def test_an_empty_part_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_part_set({"design_id": "DSN-6013", "parts": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_part_set("the distributor said it was franchised")


if __name__ == "__main__":
    unittest.main()
