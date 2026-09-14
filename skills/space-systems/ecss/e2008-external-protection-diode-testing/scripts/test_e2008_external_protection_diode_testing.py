#!/usr/bin/env python3
"""Contract test for the external protection diode testing check (offline)."""

import unittest

from e2008_external_protection_diode_testing_logic import (
    CONDITION_ESCALATED,
    CONDITION_OFF_BASELINE,
    CONDITION_RELAXED,
    CONDITION_REUSED,
    CONDITION_SENSES,
    DEFAULT_CARRY_POLICY,
    DOCUMENT_SOURCES,
    PROGRAMME_ACCEPTED,
    PROGRAMME_OPEN,
    TEST_CONDITION_ESCALATED,
    TEST_CONDITION_INVENTED,
    TEST_CONDITION_OFF_BASELINE,
    TEST_CONDITION_OMITTED,
    TEST_CONDITION_RELAXED,
    TEST_CONFORMING,
    TEST_DRAWING_SUPERSEDED,
    TEST_DRAWING_UNRESOLVED,
    TEST_FOREIGN_DRAWING,
    TEST_METHOD_SUBSTITUTED,
    VERDICT_RANK,
    assess_declared_test,
    compare_condition,
    evaluate_diode_test_programme,
    normalize_sense,
    validate_carry_policy,
    validate_declared_test,
    validate_drawing,
    validate_drawings,
)

PART = "dio-ext-4001"


def _reference_conditions():
    return [
        {"name": "reverse-bias-volts", "sense": "floor", "value": 40.0},
        {"name": "junction-temperature-celsius", "sense": "nominal", "value": 25.0,
         "tolerance": 2.0},
        {"name": "dwell-seconds", "sense": "ceiling", "value": 30.0},
    ]


def _drawing(drawing_id="scd-4001", part_number=PART, issue=3, governing=3,
             tests=None):
    return {
        "drawing_id": drawing_id,
        "part_number": part_number,
        "issue": issue,
        "governing_issue": governing,
        "tests": tests
        if tests is not None
        else [
            {
                "test_name": "reverse-leakage",
                "method": "curve-tracer-sweep",
                "conditions": _reference_conditions(),
            }
        ],
    }


def _declared(**overrides):
    test = {
        "test_name": "reverse-leakage",
        "governing_document": "source-control-drawing",
        "drawing_id": "scd-4001",
        "declared_issue": 3,
        "method": "curve-tracer-sweep",
        "conditions": [
            {"name": "reverse-bias-volts", "value": 40.0},
            {"name": "junction-temperature-celsius", "value": 25.0},
            {"name": "dwell-seconds", "value": 30.0},
        ],
    }
    test.update(overrides)
    return test


def _spec(**overrides):
    spec = {
        "programme_id": "diode-test-2026-08",
        "part_number": PART,
        "drawings": [_drawing()],
        "declared_tests": [_declared()],
    }
    spec.update(overrides)
    return spec


def _assess(declared, drawings=None, part_number=PART, policy=None):
    resolved = validate_drawings(drawings if drawings is not None else [_drawing()])
    return assess_declared_test(declared, resolved, part_number, policy)


class VocabularyTests(unittest.TestCase):
    def test_only_the_drawing_is_a_governing_source(self):
        self.assertIn("source-control-drawing", DOCUMENT_SOURCES)
        self.assertIn("in-house-test-specification", DOCUMENT_SOURCES)

    def test_three_condition_senses_are_told_apart(self):
        self.assertEqual(CONDITION_SENSES, ("floor", "ceiling", "nominal"))

    def test_sense_is_trimmed_and_lowercased(self):
        self.assertEqual(normalize_sense("  Ceiling "), "ceiling")

    def test_unknown_sense_rejected(self):
        with self.assertRaises(ValueError):
            normalize_sense("thereabouts")

    def test_verdict_rank_runs_worst_first(self):
        self.assertEqual(VERDICT_RANK[0], TEST_DRAWING_UNRESOLVED)
        self.assertEqual(VERDICT_RANK[-1], TEST_CONFORMING)

    def test_escalation_does_not_block_by_default(self):
        self.assertFalse(DEFAULT_CARRY_POLICY["escalation_blocks"])
        self.assertTrue(DEFAULT_CARRY_POLICY["off_baseline_blocks"])

    def test_unknown_carry_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_carry_policy({"relaxation_blocks": False})


class DrawingValidationTests(unittest.TestCase):
    def test_drawing_identifiers_are_lowercased(self):
        drawing = validate_drawing(_drawing(drawing_id="SCD-4001"))
        self.assertEqual(drawing["drawing_id"], "scd-4001")

    def test_drawing_with_no_test_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing(_drawing(tests=[]))

    def test_set_point_without_a_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing(
                _drawing(
                    tests=[
                        {
                            "test_name": "reverse-leakage",
                            "method": "curve-tracer-sweep",
                            "conditions": [
                                {"name": "junction-temperature-celsius",
                                 "sense": "nominal", "value": 25.0}
                            ],
                        }
                    ]
                )
            )

    def test_repeated_condition_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing(
                _drawing(
                    tests=[
                        {
                            "test_name": "reverse-leakage",
                            "method": "curve-tracer-sweep",
                            "conditions": [
                                {"name": "dwell-seconds", "sense": "ceiling",
                                 "value": 30.0},
                                {"name": "dwell-seconds", "sense": "ceiling",
                                 "value": 40.0},
                            ],
                        }
                    ]
                )
            )

    def test_repeated_drawing_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawings([_drawing(), _drawing()])

    def test_non_integer_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing(_drawing(issue=3.5))

    def test_declared_test_needs_a_drawing_when_it_cites_one(self):
        record = _declared()
        del record["drawing_id"]
        with self.assertRaises(ValueError):
            validate_declared_test(record)

    def test_declared_condition_value_must_be_a_number(self):
        with self.assertRaises(ValueError):
            validate_declared_test(
                _declared(conditions=[{"name": "dwell-seconds", "value": "thirty"}])
            )


class ConditionComparisonTests(unittest.TestCase):
    def test_floor_met_exactly_is_reused(self):
        reference = {"name": "reverse-bias-volts", "sense": "floor", "value": 40.0,
                     "tolerance": 0.0}
        self.assertEqual(compare_condition(40.0, reference)["state"], CONDITION_REUSED)

    def test_floor_below_the_drawing_is_relaxed(self):
        reference = {"name": "reverse-bias-volts", "sense": "floor", "value": 40.0,
                     "tolerance": 0.0}
        self.assertEqual(compare_condition(25.0, reference)["state"],
                         CONDITION_RELAXED)

    def test_floor_above_the_drawing_is_an_over_test(self):
        reference = {"name": "reverse-bias-volts", "sense": "floor", "value": 40.0,
                     "tolerance": 0.0}
        self.assertEqual(compare_condition(60.0, reference)["state"],
                         CONDITION_ESCALATED)

    def test_ceiling_weakens_in_the_opposite_direction(self):
        reference = {"name": "dwell-seconds", "sense": "ceiling", "value": 30.0,
                     "tolerance": 0.0}
        self.assertEqual(compare_condition(45.0, reference)["state"],
                         CONDITION_RELAXED)
        self.assertEqual(compare_condition(10.0, reference)["state"],
                         CONDITION_ESCALATED)

    def test_set_point_inside_its_band_is_reused(self):
        reference = {"name": "junction-temperature-celsius", "sense": "nominal",
                     "value": 25.0, "tolerance": 2.0}
        self.assertEqual(compare_condition(26.5, reference)["state"],
                         CONDITION_REUSED)

    def test_set_point_exactly_on_its_band_edge_is_reused(self):
        reference = {"name": "junction-temperature-celsius", "sense": "nominal",
                     "value": 25.0, "tolerance": 2.0}
        result = compare_condition(27.0, reference)
        self.assertAlmostEqual(
            abs(result["declared_value"] - result["drawing_value"]), 2.0, places=9
        )
        self.assertEqual(result["state"], CONDITION_REUSED)

    def test_set_point_outside_its_band_is_off_baseline_either_way(self):
        reference = {"name": "junction-temperature-celsius", "sense": "nominal",
                     "value": 25.0, "tolerance": 2.0}
        self.assertEqual(compare_condition(30.0, reference)["state"],
                         CONDITION_OFF_BASELINE)
        self.assertEqual(compare_condition(20.0, reference)["state"],
                         CONDITION_OFF_BASELINE)

    def test_a_floor_arrived_at_by_arithmetic_still_counts_as_met(self):
        reference = {"name": "reverse-bias-volts", "sense": "floor", "value": 0.3,
                     "tolerance": 0.0}
        self.assertEqual(
            compare_condition(0.1 + 0.2, reference)["state"], CONDITION_REUSED
        )


class DeclaredTestTests(unittest.TestCase):
    def test_a_test_following_its_own_drawing_conforms(self):
        result = _assess(_declared())
        self.assertEqual(result["state"], TEST_CONFORMING)
        self.assertFalse(result["blocking"])

    def test_a_house_specification_leaves_the_test_ungoverned(self):
        result = _assess(
            _declared(governing_document="in-house-test-specification",
                      drawing_id=None)
        )
        self.assertEqual(result["state"], TEST_DRAWING_UNRESOLVED)
        self.assertTrue(result["blocking"])

    def test_a_datasheet_leaves_the_test_ungoverned(self):
        result = _assess(
            _declared(governing_document="supplier-datasheet", drawing_id=None)
        )
        self.assertEqual(result["state"], TEST_DRAWING_UNRESOLVED)

    def test_a_drawing_nobody_supplied_is_unresolved(self):
        result = _assess(_declared(drawing_id="scd-9999"))
        self.assertEqual(result["state"], TEST_DRAWING_UNRESOLVED)

    def test_another_parts_drawing_is_its_own_finding(self):
        result = _assess(
            _declared(),
            drawings=[_drawing(part_number="dio-ext-7777")],
        )
        self.assertEqual(result["state"], TEST_FOREIGN_DRAWING)

    def test_a_superseded_issue_is_reported_before_any_condition(self):
        result = _assess(
            _declared(declared_issue=1),
            drawings=[_drawing(issue=4, governing=4)],
        )
        self.assertEqual(result["state"], TEST_DRAWING_SUPERSEDED)
        self.assertEqual(result["conditions"], ())

    def test_a_substituted_method_settles_before_the_conditions(self):
        result = _assess(_declared(method="handheld-probe"))
        self.assertEqual(result["state"], TEST_METHOD_SUBSTITUTED)
        self.assertEqual(result["conditions"], ())

    def test_an_omitted_condition_is_a_change_to_the_defined_test(self):
        result = _assess(
            _declared(
                conditions=[
                    {"name": "reverse-bias-volts", "value": 40.0},
                    {"name": "junction-temperature-celsius", "value": 25.0},
                ]
            )
        )
        self.assertEqual(result["state"], TEST_CONDITION_OMITTED)
        self.assertEqual(result["omitted_conditions"], ("dwell-seconds",))

    def test_an_invented_condition_is_reported_separately(self):
        conditions = [
            {"name": "reverse-bias-volts", "value": 40.0},
            {"name": "junction-temperature-celsius", "value": 25.0},
            {"name": "dwell-seconds", "value": 30.0},
            {"name": "illuminance-lux", "value": 500.0},
        ]
        result = _assess(_declared(conditions=conditions))
        self.assertEqual(result["state"], TEST_CONDITION_INVENTED)
        self.assertEqual(result["invented_conditions"], ("illuminance-lux",))

    def test_a_relaxed_condition_blocks(self):
        conditions = [
            {"name": "reverse-bias-volts", "value": 20.0},
            {"name": "junction-temperature-celsius", "value": 25.0},
            {"name": "dwell-seconds", "value": 30.0},
        ]
        result = _assess(_declared(conditions=conditions))
        self.assertEqual(result["state"], TEST_CONDITION_RELAXED)
        self.assertTrue(result["blocking"])

    def test_an_over_test_is_reported_but_carried_by_default(self):
        conditions = [
            {"name": "reverse-bias-volts", "value": 80.0},
            {"name": "junction-temperature-celsius", "value": 25.0},
            {"name": "dwell-seconds", "value": 30.0},
        ]
        result = _assess(_declared(conditions=conditions))
        self.assertEqual(result["state"], TEST_CONDITION_ESCALATED)
        self.assertFalse(result["blocking"])
        self.assertTrue(result["reasons"])

    def test_the_project_may_make_an_over_test_block(self):
        conditions = [
            {"name": "reverse-bias-volts", "value": 80.0},
            {"name": "junction-temperature-celsius", "value": 25.0},
            {"name": "dwell-seconds", "value": 30.0},
        ]
        result = _assess(
            _declared(conditions=conditions), policy={"escalation_blocks": True}
        )
        self.assertTrue(result["blocking"])

    def test_an_off_baseline_set_point_blocks_by_default(self):
        conditions = [
            {"name": "reverse-bias-volts", "value": 40.0},
            {"name": "junction-temperature-celsius", "value": 40.0},
            {"name": "dwell-seconds", "value": 30.0},
        ]
        result = _assess(_declared(conditions=conditions))
        self.assertEqual(result["state"], TEST_CONDITION_OFF_BASELINE)
        self.assertTrue(result["blocking"])

    def test_a_test_the_drawing_never_defines_is_unresolved(self):
        result = _assess(_declared(test_name="thermal-shock"))
        self.assertEqual(result["state"], TEST_DRAWING_UNRESOLVED)


class ProgrammeTests(unittest.TestCase):
    def test_a_clean_programme_is_accepted(self):
        result = evaluate_diode_test_programme(_spec())
        self.assertEqual(result["verdict"], PROGRAMME_ACCEPTED)
        self.assertEqual(result["findings"], ())
        self.assertAlmostEqual(result["conformance_fraction"], 1.0, places=9)

    def test_a_test_the_drawing_defines_and_nobody_ran_is_a_hole(self):
        drawing = _drawing(
            tests=[
                {
                    "test_name": "reverse-leakage",
                    "method": "curve-tracer-sweep",
                    "conditions": _reference_conditions(),
                },
                {
                    "test_name": "forward-drop",
                    "method": "four-wire-measurement",
                    "conditions": [
                        {"name": "forward-current-amps", "sense": "floor",
                         "value": 1.0}
                    ],
                },
            ]
        )
        result = evaluate_diode_test_programme(_spec(drawings=[drawing]))
        self.assertEqual(result["uncovered_tests"], ("forward-drop",))
        self.assertEqual(result["verdict"], PROGRAMME_OPEN)

    def test_the_weakest_test_is_reported_first(self):
        spec = _spec(
            drawings=[
                _drawing(
                    tests=[
                        {
                            "test_name": "reverse-leakage",
                            "method": "curve-tracer-sweep",
                            "conditions": _reference_conditions(),
                        },
                        {
                            "test_name": "forward-drop",
                            "method": "four-wire-measurement",
                            "conditions": [
                                {"name": "forward-current-amps", "sense": "floor",
                                 "value": 1.0}
                            ],
                        },
                    ]
                )
            ],
            declared_tests=[
                _declared(),
                {
                    "test_name": "forward-drop",
                    "governing_document": "in-house-test-specification",
                    "method": "four-wire-measurement",
                    "conditions": [{"name": "forward-current-amps", "value": 1.0}],
                },
            ],
        )
        result = evaluate_diode_test_programme(spec)
        self.assertEqual(result["weakest_test"], "forward-drop")
        self.assertEqual(result["weakest_state"], TEST_DRAWING_UNRESOLVED)
        self.assertAlmostEqual(result["conformance_fraction"], 0.5, places=9)

    def test_a_programme_with_no_drawing_for_its_part_is_open(self):
        result = evaluate_diode_test_programme(
            _spec(drawings=[_drawing(part_number="dio-ext-7777")])
        )
        self.assertEqual(result["verdict"], PROGRAMME_OPEN)

    def test_a_carried_over_test_does_not_open_the_programme(self):
        conditions = [
            {"name": "reverse-bias-volts", "value": 80.0},
            {"name": "junction-temperature-celsius", "value": 25.0},
            {"name": "dwell-seconds", "value": 30.0},
        ]
        result = evaluate_diode_test_programme(
            _spec(declared_tests=[_declared(conditions=conditions)])
        )
        self.assertEqual(result["verdict"], PROGRAMME_ACCEPTED)
        self.assertEqual(result["tests"][0]["state"], TEST_CONDITION_ESCALATED)

    def test_repeated_declared_test_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_diode_test_programme(
                _spec(declared_tests=[_declared(), _declared()])
            )

    def test_empty_declared_test_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_diode_test_programme(_spec(declared_tests=[]))

    def test_spec_missing_a_key_rejected(self):
        spec = _spec()
        del spec["drawings"]
        with self.assertRaises(ValueError):
            evaluate_diode_test_programme(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_diode_test_programme("test the diodes")


if __name__ == "__main__":
    unittest.main()
