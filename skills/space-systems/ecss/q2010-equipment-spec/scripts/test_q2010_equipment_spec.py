"""Contract tests for the clause 5.1.2 off-the-shelf equipment-specification logic."""

import unittest

from q2010_equipment_spec_logic import (
    COMPARISON_TOLERANCE,
    assess_equipment_spec,
    build_specification,
    compliance_ratio,
    evaluate_requirement,
    match_candidate,
    specification_gaps,
    validate_requirement,
)

MASS = {"id": "PERF-01", "category": "performance", "obligation": "mandatory",
        "kind": "max", "limit": 2.5, "unit": "kg"}
POWER = {"id": "PERF-02", "category": "performance", "obligation": "desirable",
         "kind": "max", "limit": 12.0, "unit": "W"}
BUS = {"id": "IF-01", "category": "interface", "obligation": "mandatory",
       "kind": "capability", "required": True}
BAND = {"id": "PERF-03", "category": "performance", "obligation": "mandatory",
        "kind": "range", "lower": -40.0, "upper": 85.0, "unit": "degC"}
RATE = {"id": "FUN-01", "category": "functional", "obligation": "mandatory",
        "kind": "min", "limit": 10.0, "unit": "Hz"}
ALIGN = {"id": "IF-02", "category": "interface", "obligation": "desirable",
         "kind": "target", "target": 0.0, "tolerance": 0.5, "unit": "mm"}

FULL_SPEC = [MASS, POWER, BUS, BAND, RATE, ALIGN]


class ValidateRequirementTests(unittest.TestCase):
    def test_normalises_a_max_requirement(self):
        entry = validate_requirement(MASS)
        self.assertEqual(entry["id"], "PERF-01")
        self.assertEqual(entry["kind"], "max")
        self.assertAlmostEqual(entry["limit"], 2.5, places=9)

    def test_obligation_defaults_to_mandatory(self):
        entry = validate_requirement({"id": "X", "category": "functional", "kind": "capability"})
        self.assertEqual(entry["obligation"], "mandatory")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "X", "category": "cosmetic", "kind": "capability"})

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "X", "category": "functional", "kind": "vibes"})

    def test_empty_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "  ", "category": "functional", "kind": "capability"})

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "X", "category": "performance", "kind": "range",
                                  "lower": 85.0, "upper": -40.0})

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "X", "category": "interface", "kind": "target",
                                  "target": 0.0, "tolerance": -0.1})

    def test_non_numeric_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "X", "category": "performance", "kind": "max",
                                  "limit": "2.5"})

    def test_boolean_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "X", "category": "performance", "kind": "min",
                                  "limit": True})


class BuildSpecificationTests(unittest.TestCase):
    def test_builds_every_requirement(self):
        self.assertEqual(len(build_specification(FULL_SPEC)), 6)

    def test_empty_specification_rejected(self):
        with self.assertRaises(ValueError):
            build_specification([])

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            build_specification([MASS, dict(MASS)])

    def test_gaps_name_the_unpopulated_categories(self):
        spec = build_specification([MASS, POWER])
        self.assertEqual(specification_gaps(spec), ["functional", "interface"])

    def test_no_gaps_when_every_category_present(self):
        self.assertEqual(specification_gaps(build_specification(FULL_SPEC)), [])


class EvaluateRequirementTests(unittest.TestCase):
    def test_value_under_a_ceiling_is_met(self):
        self.assertEqual(evaluate_requirement(MASS, 2.1)["status"], "met")

    def test_value_over_a_ceiling_is_not_met(self):
        self.assertEqual(evaluate_requirement(MASS, 2.9)["status"], "not-met")

    def test_value_exactly_on_the_ceiling_is_met(self):
        record = evaluate_requirement(MASS, 2.5)
        self.assertEqual(record["status"], "met")
        self.assertAlmostEqual(record["margin"], 0.0, places=9)

    def test_value_exactly_on_a_floor_is_met(self):
        record = evaluate_requirement(RATE, 10.0)
        self.assertEqual(record["status"], "met")
        self.assertAlmostEqual(record["margin"], 0.0, places=9)

    def test_range_edges_are_met(self):
        self.assertEqual(evaluate_requirement(BAND, -40.0)["status"], "met")
        self.assertEqual(evaluate_requirement(BAND, 85.0)["status"], "met")

    def test_outside_the_range_is_not_met(self):
        self.assertEqual(evaluate_requirement(BAND, 90.0)["status"], "not-met")

    def test_target_deviation_exactly_on_tolerance_is_met(self):
        record = evaluate_requirement(ALIGN, 0.5)
        self.assertEqual(record["status"], "met")
        self.assertAlmostEqual(record["margin"], 0.0, places=9)

    def test_target_deviation_past_tolerance_is_not_met(self):
        self.assertEqual(evaluate_requirement(ALIGN, 0.8)["status"], "not-met")

    def test_absent_capability_is_not_met(self):
        self.assertEqual(evaluate_requirement(BUS, False)["status"], "not-met")

    def test_capability_expects_a_boolean_datum(self):
        with self.assertRaises(ValueError):
            evaluate_requirement(BUS, 1.0)

    def test_missing_datum_is_undeclared_not_zero(self):
        record = evaluate_requirement(MASS, None)
        self.assertEqual(record["status"], "undeclared")
        self.assertIsNone(record["margin"])

    def test_tolerance_constant_is_tight(self):
        self.assertLess(COMPARISON_TOLERANCE, 1e-6)


class ComplianceRatioTests(unittest.TestCase):
    def test_undeclared_records_are_kept_out_of_the_ratio(self):
        records = [
            {"status": "met", "obligation": "mandatory"},
            {"status": "not-met", "obligation": "mandatory"},
            {"status": "undeclared", "obligation": "desirable"},
        ]
        self.assertAlmostEqual(compliance_ratio(records), 0.5, places=9)

    def test_all_undeclared_gives_no_ratio(self):
        self.assertIsNone(compliance_ratio([{"status": "undeclared"}]))

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            compliance_ratio("records")


class MatchCandidateTests(unittest.TestCase):
    def _declared(self, **over):
        base = {"PERF-01": 2.1, "PERF-02": 9.0, "IF-01": True,
                "PERF-03": 20.0, "FUN-01": 25.0, "IF-02": 0.1}
        base.update(over)
        return base

    def test_fully_matching_candidate_is_compliant(self):
        result = match_candidate(FULL_SPEC, self._declared())
        self.assertEqual(result["verdict"], "compliant")
        self.assertAlmostEqual(result["compliance_ratio"], 1.0, places=9)

    def test_unmet_mandatory_requirement_rejects(self):
        result = match_candidate(FULL_SPEC, self._declared(**{"PERF-01": 3.0}))
        self.assertEqual(result["verdict"], "rejected")
        self.assertEqual(result["blocking"], ["PERF-01"])

    def test_unmet_desirable_requirement_is_a_gap_not_a_rejection(self):
        result = match_candidate(FULL_SPEC, self._declared(**{"PERF-02": 15.0}))
        self.assertEqual(result["verdict"], "acceptable-with-gaps")
        self.assertEqual(result["gaps"], ["PERF-02"])

    def test_undeclared_mandatory_datum_blocks_assessment(self):
        declared = self._declared()
        del declared["IF-01"]
        result = match_candidate(FULL_SPEC, declared)
        self.assertEqual(result["verdict"], "not-assessable")
        self.assertEqual(result["undeclared_mandatory"], ["IF-01"])

    def test_an_unmet_mandatory_outranks_an_undeclared_one(self):
        declared = self._declared(**{"PERF-01": 3.0})
        del declared["IF-01"]
        self.assertEqual(match_candidate(FULL_SPEC, declared)["verdict"], "rejected")

    def test_datum_for_an_unknown_requirement_rejected(self):
        with self.assertRaises(ValueError):
            match_candidate(FULL_SPEC, self._declared(**{"PERF-99": 1.0}))

    def test_declared_data_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            match_candidate(FULL_SPEC, [("PERF-01", 2.1)])


class AssessEquipmentSpecTests(unittest.TestCase):
    def _spec(self, **over):
        base = {
            "requirements": FULL_SPEC,
            "candidates": {
                "unit-alpha": {"PERF-01": 2.1, "PERF-02": 9.0, "IF-01": True,
                               "PERF-03": 20.0, "FUN-01": 25.0, "IF-02": 0.1},
                "unit-beta": {"PERF-01": 2.4, "PERF-02": 15.0, "IF-01": True,
                              "PERF-03": 20.0, "FUN-01": 12.0, "IF-02": 0.1},
                "unit-gamma": {"PERF-01": 3.4, "PERF-02": 9.0, "IF-01": True,
                               "PERF-03": 20.0, "FUN-01": 25.0, "IF-02": 0.1},
            },
        }
        base.update(over)
        return base

    def test_shortlist_drops_the_rejected_candidate(self):
        result = assess_equipment_spec(self._spec())
        self.assertNotIn("unit-gamma", result["shortlist"])
        self.assertIn("unit-alpha", result["shortlist"])

    def test_shortlist_orders_by_compliance_then_name(self):
        self.assertEqual(assess_equipment_spec(self._spec())["shortlist"],
                         ["unit-alpha", "unit-beta"])

    def test_specification_without_interfaces_is_flagged_unusable(self):
        result = assess_equipment_spec(self._spec(
            requirements=[MASS, RATE],
            candidates={"unit-alpha": {"PERF-01": 2.1, "FUN-01": 25.0}},
        ))
        self.assertFalse(result["specification_usable"])
        self.assertEqual(result["missing_categories"], ["interface"])
        self.assertTrue(result["findings"])

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_spec({"requirements": FULL_SPEC})

    def test_empty_candidate_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_spec(self._spec(candidates={}))

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_equipment_spec([FULL_SPEC])


if __name__ == "__main__":
    unittest.main()
