#!/usr/bin/env python3
"""Contract test for coverglass test methods and conditions (offline).

Walks the clause workflow step by step: the activity record validation,
the pointer that resolves to nothing, the substituted method settled
before any condition is compared, each condition sense with its own
direction of relaxation and escalation, the referenced bounds a float
arrives at by arithmetic, the omitted and invented conditions, the
carry positions a project holds, and the roll-up into one reuse
verdict. This is the gate 3 review evidence for the leaf.
"""

import unittest

from e2008_coverglass_test_methods_conditions_logic import (
    ACTIVITY_CONDITION_ESCALATED,
    ACTIVITY_CONDITION_INVENTED,
    ACTIVITY_CONDITION_OFF_BASELINE,
    ACTIVITY_CONDITION_OMITTED,
    ACTIVITY_CONDITION_RELAXED,
    ACTIVITY_CONFORMING,
    ACTIVITY_METHOD_SUBSTITUTED,
    ACTIVITY_REFERENCE_UNRESOLVED,
    CONDITION_CONFORMING,
    CONDITION_ESCALATED,
    CONDITION_OFF_BASELINE,
    CONDITION_RELAXED,
    PROCEDURE_DEPARTS_FROM_DEFINITIONS,
    PROCEDURE_REUSES_DEFINITIONS,
    REFERENCE_DEFINITIONS,
    SENSE_CEILING,
    SENSE_FLOOR,
    SENSE_NOMINAL,
    assess_activity_reuse,
    assess_coverglass_reuse,
    compare_condition,
    resolve_reference,
    resolve_reuse_policy,
    validate_activity_record,
)

DIMENSIONAL = "coverglass-dimensional-measurement"
VISUAL = "coverglass-visual-inspection"
OPTICAL = "coverglass-optical-transmission-measurement"
CONDUCTIVITY = "coverglass-surface-conductivity-measurement"


def _activity(name, method=None, conditions=None, drop=()):
    reference = REFERENCE_DEFINITIONS[name]
    declared = {
        label: entry["value"] for label, entry in reference["conditions"].items()
    }
    if conditions:
        declared.update(conditions)
    for label in drop:
        declared.pop(label, None)
    return {
        "activity": name,
        "method": method or reference["method"],
        "conditions": declared,
    }


def _procedure(*entries, **overrides):
    listed = list(entries)
    if not listed:
        listed = [_activity(name) for name in sorted(REFERENCE_DEFINITIONS)]
    case = {"procedure_id": "CG-PROC-8", "activities": listed}
    case.update(overrides)
    return case


class ActivityValidationTests(unittest.TestCase):
    def test_a_sound_activity_validates(self):
        record = validate_activity_record(_activity(VISUAL))
        self.assertEqual(record["activity"], VISUAL)
        self.assertEqual(len(record["conditions"]), 2)

    def test_a_missing_method_rejected(self):
        entry = _activity(VISUAL)
        entry["method"] = ""
        with self.assertRaises(ValueError):
            validate_activity_record(entry)

    def test_a_non_numeric_condition_rejected(self):
        entry = _activity(VISUAL, conditions={"inspection-magnification": "ten-ish"})
        with self.assertRaises(ValueError):
            validate_activity_record(entry)

    def test_a_non_mapping_condition_block_rejected(self):
        entry = _activity(VISUAL)
        entry["conditions"] = "as defined further down"
        with self.assertRaises(ValueError):
            validate_activity_record(entry)

    def test_an_empty_activity_label_rejected(self):
        entry = _activity(VISUAL)
        entry["activity"] = "   "
        with self.assertRaises(ValueError):
            validate_activity_record(entry)


class PointerTests(unittest.TestCase):
    def test_a_defined_activity_resolves(self):
        reference = resolve_reference(VISUAL)
        self.assertEqual(reference["method"], "magnified-visual-examination")

    def test_an_undefined_activity_resolves_to_nothing(self):
        self.assertIsNone(resolve_reference("coverglass-taste-test"))

    def test_a_dangling_pointer_ranks_worst(self):
        result = assess_activity_reuse(
            {
                "activity": "coverglass-taste-test",
                "method": "unaided-visual-examination",
                "conditions": {"panel-size": 4.0},
            }
        )
        self.assertEqual(result["verdict"], ACTIVITY_REFERENCE_UNRESOLVED)
        self.assertEqual(result["invented"], ["panel-size"])
        self.assertTrue(any("no other end" in f for f in result["findings"]))


class MethodTests(unittest.TestCase):
    def test_a_substituted_method_is_settled_before_any_condition(self):
        result = assess_activity_reuse(
            _activity(VISUAL, method="unaided-visual-examination")
        )
        self.assertEqual(result["verdict"], ACTIVITY_METHOD_SUBSTITUTED)
        self.assertEqual(result["conditions"], [])

    def test_the_referenced_method_is_reported_alongside(self):
        result = assess_activity_reuse(
            _activity(OPTICAL, method="handheld-transmission-probe")
        )
        self.assertEqual(
            result["reference_method"], "spectrophotometer-transmission-scan"
        )
        self.assertFalse(result["method_reused"])


class ConditionSenseTests(unittest.TestCase):
    FLOOR = {"sense": SENSE_FLOOR, "value": 10.0}
    CEILING = {"sense": SENSE_CEILING, "value": 50.0}
    NOMINAL = {"sense": SENSE_NOMINAL, "value": 23.0, "tolerance": 2.0}

    def test_a_floor_met_exactly_is_reused(self):
        item = compare_condition("inspection-magnification", 10.0, self.FLOOR)
        self.assertEqual(item["state"], CONDITION_CONFORMING)
        self.assertAlmostEqual(item["margin"], 0.0, places=9)

    def test_a_floor_reached_by_arithmetic_is_still_reused(self):
        declared = sum([0.1] * 100)
        item = compare_condition("inspection-magnification", declared, self.FLOOR)
        self.assertAlmostEqual(declared, 10.0, places=9)
        self.assertEqual(item["state"], CONDITION_CONFORMING)

    def test_below_a_floor_is_a_relaxation(self):
        item = compare_condition("inspection-magnification", 4.0, self.FLOOR)
        self.assertEqual(item["state"], CONDITION_RELAXED)

    def test_above_a_floor_is_an_escalation(self):
        item = compare_condition("inspection-magnification", 40.0, self.FLOOR)
        self.assertEqual(item["state"], CONDITION_ESCALATED)

    def test_above_a_ceiling_is_a_relaxation(self):
        item = compare_condition("measurement-humidity-percent", 70.0, self.CEILING)
        self.assertEqual(item["state"], CONDITION_RELAXED)

    def test_below_a_ceiling_is_an_escalation(self):
        item = compare_condition("measurement-humidity-percent", 30.0, self.CEILING)
        self.assertEqual(item["state"], CONDITION_ESCALATED)

    def test_a_ceiling_met_exactly_is_reused(self):
        item = compare_condition("measurement-humidity-percent", 50.0, self.CEILING)
        self.assertEqual(item["state"], CONDITION_CONFORMING)
        self.assertAlmostEqual(item["margin"], 0.0, places=9)

    def test_a_nominal_set_point_inside_its_band_is_reused(self):
        item = compare_condition("ambient-temperature-celsius", 24.0, self.NOMINAL)
        self.assertEqual(item["state"], CONDITION_CONFORMING)

    def test_a_nominal_deviation_arriving_exactly_on_tolerance_is_reused(self):
        declared = 23.0 + sum([0.1] * 20)
        item = compare_condition("ambient-temperature-celsius", declared, self.NOMINAL)
        self.assertAlmostEqual(abs(item["margin"]), 2.0, places=9)
        self.assertEqual(item["state"], CONDITION_CONFORMING)

    def test_a_nominal_set_point_outside_its_band_is_off_baseline(self):
        item = compare_condition("ambient-temperature-celsius", 30.0, self.NOMINAL)
        self.assertEqual(item["state"], CONDITION_OFF_BASELINE)

    def test_an_unknown_sense_rejected(self):
        with self.assertRaises(ValueError):
            compare_condition("whatever", 1.0, {"sense": "vibes", "value": 1.0})

    def test_a_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            compare_condition(
                "ambient-temperature-celsius",
                23.0,
                {"sense": SENSE_NOMINAL, "value": 23.0, "tolerance": -1.0},
            )


class ActivityVerdictTests(unittest.TestCase):
    def test_a_full_reuse_conforms(self):
        result = assess_activity_reuse(_activity(DIMENSIONAL))
        self.assertEqual(result["verdict"], ACTIVITY_CONFORMING)
        self.assertEqual(result["findings"], [])

    def test_an_omitted_condition_outranks_an_invented_one(self):
        entry = _activity(VISUAL, drop=["inspection-illuminance-lux"])
        entry["conditions"]["bench-tidiness"] = 1.0
        result = assess_activity_reuse(entry)
        self.assertEqual(result["verdict"], ACTIVITY_CONDITION_OMITTED)
        self.assertEqual(result["omitted"], ["inspection-illuminance-lux"])
        self.assertEqual(result["invented"], ["bench-tidiness"])

    def test_an_invented_condition_is_its_own_state(self):
        entry = _activity(VISUAL)
        entry["conditions"]["bench-tidiness"] = 1.0
        result = assess_activity_reuse(entry)
        self.assertEqual(result["verdict"], ACTIVITY_CONDITION_INVENTED)

    def test_a_relaxation_blocks_the_activity(self):
        result = assess_activity_reuse(
            _activity(VISUAL, conditions={"inspection-magnification": 4.0})
        )
        self.assertEqual(result["verdict"], ACTIVITY_CONDITION_RELAXED)
        self.assertTrue(any("weaker than the definition" in f for f in result["findings"]))

    def test_an_escalation_is_reported_but_carried_by_default(self):
        result = assess_activity_reuse(
            _activity(VISUAL, conditions={"inspection-magnification": 40.0})
        )
        self.assertEqual(result["verdict"], ACTIVITY_CONFORMING)
        self.assertTrue(any("over-tests" in f for f in result["findings"]))

    def test_policy_can_refuse_to_carry_an_escalation(self):
        result = assess_activity_reuse(
            _activity(VISUAL, conditions={"inspection-magnification": 40.0}),
            {"carry_escalation": False},
        )
        self.assertEqual(result["verdict"], ACTIVITY_CONDITION_ESCALATED)

    def test_an_off_baseline_set_point_blocks_by_default(self):
        result = assess_activity_reuse(
            _activity(DIMENSIONAL, conditions={"ambient-temperature-celsius": 40.0})
        )
        self.assertEqual(result["verdict"], ACTIVITY_CONDITION_OFF_BASELINE)

    def test_policy_can_carry_an_off_baseline_set_point(self):
        result = assess_activity_reuse(
            _activity(DIMENSIONAL, conditions={"ambient-temperature-celsius": 40.0}),
            {"carry_off_baseline": True},
        )
        self.assertEqual(result["verdict"], ACTIVITY_CONFORMING)


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve(self):
        settings = resolve_reuse_policy()
        self.assertTrue(settings["carry_escalation"])
        self.assertFalse(settings["carry_off_baseline"])

    def test_a_non_boolean_carry_position_rejected(self):
        with self.assertRaises(ValueError):
            resolve_reuse_policy({"carry_escalation": "sometimes"})

    def test_a_coverage_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            resolve_reuse_policy({"min_activity_coverage": 1.5})


class ProcedureRollUpTests(unittest.TestCase):
    def test_a_full_procedure_reuses_every_definition(self):
        result = assess_coverglass_reuse(_procedure())
        self.assertEqual(result["verdict"], PROCEDURE_REUSES_DEFINITIONS)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["reuse_fraction"], 1.0, places=9)

    def test_a_definition_nobody_picks_up_is_named(self):
        result = assess_coverglass_reuse(
            _procedure(_activity(VISUAL), _activity(DIMENSIONAL))
        )
        self.assertEqual(result["verdict"], PROCEDURE_DEPARTS_FROM_DEFINITIONS)
        self.assertEqual(
            result["unreferenced_definitions"], sorted([OPTICAL, CONDUCTIVITY])
        )
        self.assertAlmostEqual(result["definition_coverage"], 0.5, places=9)

    def test_coverage_landing_exactly_on_a_relaxed_floor_is_carried(self):
        result = assess_coverglass_reuse(
            _procedure(
                _activity(VISUAL),
                _activity(DIMENSIONAL),
                policy={"min_activity_coverage": 0.5},
            )
        )
        self.assertTrue(result["meets_coverage"])
        self.assertEqual(result["verdict"], PROCEDURE_REUSES_DEFINITIONS)

    def test_the_weakest_activity_is_named_by_rank(self):
        result = assess_coverglass_reuse(
            _procedure(
                _activity(VISUAL, conditions={"inspection-magnification": 4.0}),
                _activity(DIMENSIONAL, method="laser-scan-dimensional-measurement"),
                _activity(OPTICAL),
                _activity(CONDUCTIVITY),
            )
        )
        self.assertEqual(result["weakest_activity"], DIMENSIONAL)
        self.assertIn(ACTIVITY_METHOD_SUBSTITUTED, result["grouped_activities"])
        self.assertIn(ACTIVITY_CONDITION_RELAXED, result["grouped_activities"])

    def test_an_activity_listed_twice_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_reuse(_procedure(_activity(VISUAL), _activity(VISUAL)))

    def test_an_empty_procedure_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_reuse({"procedure_id": "CG-PROC-8", "activities": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_reuse("run it the way clause eight says")


if __name__ == "__main__":
    unittest.main()
