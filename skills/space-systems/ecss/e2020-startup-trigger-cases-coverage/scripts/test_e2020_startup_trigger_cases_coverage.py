"""Contract tests for the clause 5.2.7.6.1 trigger coverage logic."""

import unittest

from e2020_startup_trigger_cases_coverage_logic import (
    FRACTION_TOLERANCE,
    TRIGGER_ROUTES,
    assess_trigger_coverage,
    build_matrix,
    coverage_fraction,
    normalise_condition,
    normalise_outcome,
    normalise_trigger,
    required_cells,
    uncovered_cells,
    validate_case,
    validate_case_set,
    validate_conditions,
)

CONDITIONS = ["hard short", "partial overload"]


def case(cid, trigger, condition, outcome="pass"):
    return {
        "id": cid,
        "trigger": trigger,
        "fault_condition": condition,
        "outcome": outcome,
    }


FULL_SET = [
    case("t1", "commanded turn on", "hard short"),
    case("t2", "rising bus voltage", "hard short"),
    case("t3", "commanded turn on", "partial overload"),
    case("t4", "rising bus voltage", "partial overload"),
]


class NormaliseTriggerTests(unittest.TestCase):
    def test_commanded_route_folds(self):
        self.assertEqual(normalise_trigger("commanded turn on"), "commanded-turn-on")

    def test_telecommand_folds_onto_the_commanded_route(self):
        self.assertEqual(normalise_trigger("Telecommand"), "commanded-turn-on")

    def test_bus_power_up_folds_onto_the_rising_route(self):
        self.assertEqual(normalise_trigger("bus_power_up"), "rising-bus-voltage")

    def test_main_bus_rise_folds_onto_the_rising_route(self):
        self.assertEqual(normalise_trigger("  Main-Bus-Rise "), "rising-bus-voltage")

    def test_unknown_trigger_is_refused_not_guessed(self):
        with self.assertRaises(ValueError):
            normalise_trigger("watchdog reset")

    def test_empty_trigger_rejected(self):
        with self.assertRaises(ValueError):
            normalise_trigger("   ")

    def test_non_string_trigger_rejected(self):
        with self.assertRaises(ValueError):
            normalise_trigger(7)

    def test_only_two_routes_exist(self):
        self.assertEqual(len(TRIGGER_ROUTES), 2)


class NormaliseConditionAndOutcomeTests(unittest.TestCase):
    def test_condition_tokenised(self):
        self.assertEqual(normalise_condition("Hard  Short"), "hard-short")

    def test_underscores_fold_to_hyphens(self):
        self.assertEqual(normalise_condition("partial_overload"), "partial-overload")

    def test_empty_condition_rejected(self):
        with self.assertRaises(ValueError):
            normalise_condition("")

    def test_passed_folds_to_pass(self):
        self.assertEqual(normalise_outcome("Passed"), "pass")

    def test_planned_folds_to_not_run(self):
        self.assertEqual(normalise_outcome("planned"), "not-run")

    def test_unknown_outcome_rejected(self):
        with self.assertRaises(ValueError):
            normalise_outcome("inconclusive")


class ValidateTests(unittest.TestCase):
    def test_case_keeps_the_declared_trigger_text(self):
        record = validate_case(case("t1", "Telecommand", "hard short"), 0)
        self.assertEqual(record["declared_trigger"], "Telecommand")
        self.assertEqual(record["trigger"], "commanded-turn-on")

    def test_case_id_defaults_from_the_index(self):
        record = validate_case(
            {"trigger": "power-up", "fault_condition": "hard short", "outcome": "pass"},
            3,
        )
        self.assertEqual(record["id"], "case-3")

    def test_case_missing_outcome_rejected(self):
        with self.assertRaises(ValueError):
            validate_case({"trigger": "power-up", "fault_condition": "hard short"}, 0)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(["t1", "power-up"], 0)

    def test_repeated_case_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_case_set([case("t1", "power-up", "hard short"),
                               case("t1", "commanded", "hard short")])

    def test_empty_case_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_case_set([])

    def test_conditions_deduplicated_by_refusal(self):
        with self.assertRaises(ValueError):
            validate_conditions(["hard short", "Hard_Short"])

    def test_empty_condition_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditions([])

    def test_conditions_returned_as_tokens(self):
        self.assertEqual(validate_conditions(CONDITIONS), ["hard-short", "partial-overload"])


class MatrixTests(unittest.TestCase):
    def test_required_cells_are_conditions_times_routes(self):
        cells = required_cells(CONDITIONS)
        self.assertEqual(len(cells), 4)
        self.assertIn(("hard-short", "rising-bus-voltage"), cells)

    def test_full_set_fills_every_cell(self):
        built = build_matrix(FULL_SET, CONDITIONS)
        self.assertEqual(uncovered_cells(built["matrix"]), [])

    def test_coverage_fraction_of_a_full_set_is_one(self):
        built = build_matrix(FULL_SET, CONDITIONS)
        self.assertAlmostEqual(coverage_fraction(built["matrix"]), 1.0, places=9)

    def test_commanded_only_set_leaves_the_rising_route_uncovered(self):
        built = build_matrix(
            [FULL_SET[0], FULL_SET[2]], CONDITIONS
        )
        uncovered = uncovered_cells(built["matrix"])
        self.assertEqual(len(uncovered), 2)
        self.assertTrue(all(cell[1] == "rising-bus-voltage" for cell in uncovered))

    def test_half_a_matrix_is_half_covered(self):
        built = build_matrix([FULL_SET[0], FULL_SET[2]], CONDITIONS)
        self.assertAlmostEqual(coverage_fraction(built["matrix"]), 0.5, places=9)

    def test_failed_case_does_not_cover_its_cell(self):
        built = build_matrix(
            [case("t1", "commanded", "hard short", "failed")], CONDITIONS
        )
        self.assertIn(("hard-short", "commanded-turn-on"), uncovered_cells(built["matrix"]))

    def test_open_case_does_not_cover_its_cell(self):
        built = build_matrix(
            [case("t1", "commanded", "hard short", "planned")], CONDITIONS
        )
        self.assertIn(("hard-short", "commanded-turn-on"), uncovered_cells(built["matrix"]))

    def test_case_outside_the_declared_conditions_is_set_aside(self):
        built = build_matrix(
            FULL_SET + [case("t5", "commanded", "open circuit")], CONDITIONS
        )
        self.assertEqual([r["id"] for r in built["undeclared"]], ["t5"])

    def test_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            uncovered_cells({})

    def test_coverage_fraction_of_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction({})


class AssessTriggerCoverageTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {"fault_conditions": CONDITIONS, "cases": FULL_SET}
        spec.update(over)
        return spec

    def test_both_routes_on_both_conditions_is_compliant(self):
        result = assess_trigger_coverage(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_full_coverage_meets_the_default_required_fraction(self):
        result = assess_trigger_coverage(self._spec())
        self.assertTrue(result["meets_required_fraction"])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)

    def test_commanded_only_evidence_is_named_as_a_one_route_gap(self):
        result = assess_trigger_coverage(
            self._spec(cases=[FULL_SET[0], FULL_SET[2]])
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("route only" in f for f in result["findings"])
        )

    def test_a_route_absent_from_the_whole_set_is_its_own_finding(self):
        result = assess_trigger_coverage(
            self._spec(cases=[FULL_SET[0], FULL_SET[2]])
        )
        self.assertTrue(
            any("no case anywhere in the set" in f for f in result["findings"])
        )

    def test_condition_with_no_case_at_all_is_reported_on_both_routes(self):
        result = assess_trigger_coverage(
            self._spec(cases=[FULL_SET[0], FULL_SET[1]])
        )
        gaps = [f for f in result["findings"] if "has no passing case" in f]
        self.assertEqual(len(gaps), 2)

    def test_failed_case_is_reported_even_when_a_twin_covers_the_cell(self):
        cases = FULL_SET + [case("t5", "commanded", "hard short", "failed")]
        result = assess_trigger_coverage(self._spec(cases=cases))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("failed on" in f for f in result["findings"]))

    def test_open_case_is_reported_even_at_full_coverage(self):
        cases = FULL_SET + [case("t5", "power-up", "partial overload", "pending")]
        result = assess_trigger_coverage(self._spec(cases=cases))
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)
        self.assertFalse(result["compliant"])

    def test_undeclared_condition_is_reported(self):
        cases = FULL_SET + [case("t5", "commanded", "open circuit")]
        result = assess_trigger_coverage(self._spec(cases=cases))
        self.assertTrue(any("not in the declared set" in f for f in result["findings"]))

    def test_partial_coverage_can_meet_a_relaxed_required_fraction(self):
        result = assess_trigger_coverage(
            self._spec(cases=[FULL_SET[0], FULL_SET[2]], required_fraction=0.5)
        )
        self.assertTrue(result["meets_required_fraction"])

    def test_a_fraction_exactly_at_the_requirement_is_met(self):
        result = assess_trigger_coverage(
            self._spec(cases=[FULL_SET[0], FULL_SET[1]], required_fraction=0.5)
        )
        self.assertAlmostEqual(result["coverage_fraction"], 0.5, places=9)
        self.assertTrue(result["meets_required_fraction"])

    def test_meeting_the_fraction_does_not_by_itself_make_it_compliant(self):
        result = assess_trigger_coverage(
            self._spec(cases=[FULL_SET[0], FULL_SET[2]], required_fraction=0.5)
        )
        self.assertFalse(result["compliant"])

    def test_required_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_trigger_coverage(self._spec(required_fraction=1.5))

    def test_negative_required_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_trigger_coverage(self._spec(required_fraction=-0.1))

    def test_non_numeric_required_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_trigger_coverage(self._spec(required_fraction="all"))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["cases"]
        with self.assertRaises(ValueError):
            assess_trigger_coverage(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_trigger_coverage(CONDITIONS)

    def test_fraction_tolerance_is_representation_sized(self):
        self.assertLess(FRACTION_TOLERANCE, 1e-9)


if __name__ == "__main__":
    unittest.main()
