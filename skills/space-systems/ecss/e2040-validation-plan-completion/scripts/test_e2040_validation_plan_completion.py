"""Contract test for the validation-plan-completion leaf (stdlib unittest)."""

import unittest

from e2040_validation_plan_completion_logic import (
    COMPLETION_TOLERANCE,
    FINAL_MATURITY,
    MANDATED_SECTIONS,
    MATURITY_ORDER,
    VALIDATION_METHODS,
    assess_validation_plan_completion,
    case_readiness,
    completion_index,
    requirement_coverage,
    section_completion,
    stale_configuration_cases,
    validate_case,
    validate_plan,
    validate_requirement,
)

BASELINE = "DEV-BUILD-07"


def plan(**kw):
    record = {
        "baseline_configuration_id": BASELINE,
        "issue": FINAL_MATURITY,
        "sections": {name: FINAL_MATURITY for name in MANDATED_SECTIONS},
    }
    record.update(kw)
    return record


def case(cid="VC-1", reqs=("R-1",), **kw):
    record = {
        "id": cid,
        "method": "test",
        "requirement_ids": list(reqs),
        "environment": "flight-representative-bench",
        "pass_criterion": "functional response inside the specified window",
        "configuration_id": BASELINE,
    }
    record.update(kw)
    return record


def requirement(rid="R-1", **kw):
    record = {"id": rid, "validation_required": True, "category": "B"}
    record.update(kw)
    return record


def clean_spec():
    return {
        "plan": plan(),
        "requirements": [requirement("R-1"), requirement("R-2")],
        "cases": [case("VC-1", ("R-1",)), case("VC-2", ("R-2",))],
    }


class TestValidateRequirement(unittest.TestCase):
    def test_defaults_validation_required_to_true(self):
        norm = validate_requirement({"id": "R-9"})
        self.assertTrue(norm["validation_required"])
        self.assertEqual(norm["category"], "A")

    def test_category_is_upper_cased(self):
        self.assertEqual(validate_requirement({"id": "R-9", "category": "c"})["category"], "C")

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(["R-9"])

    def test_blank_id_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "   "})

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "R-9", "category": "E"})

    def test_non_boolean_validation_required_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "R-9", "validation_required": "yes"})


class TestValidateCase(unittest.TestCase):
    def test_method_is_lower_cased(self):
        self.assertEqual(validate_case(case(method="Analysis"))["method"], "analysis")

    def test_every_declared_method_is_accepted(self):
        for method in VALIDATION_METHODS:
            self.assertEqual(validate_case(case(method=method))["method"], method)

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_case(case(method="hand-waving"))

    def test_requirement_ids_as_string_raises(self):
        with self.assertRaises(ValueError):
            validate_case(case(requirement_ids="R-1"))

    def test_repeated_requirement_id_in_one_case_raises(self):
        with self.assertRaises(ValueError):
            validate_case(case(requirement_ids=["R-1", "R-1"]))

    def test_missing_configuration_id_raises(self):
        broken = case()
        del broken["configuration_id"]
        with self.assertRaises(ValueError):
            validate_case(broken)

    def test_absent_pass_criterion_is_kept_as_none(self):
        self.assertIsNone(validate_case(case(pass_criterion=None))["pass_criterion"])


class TestValidatePlan(unittest.TestCase):
    def test_issue_is_lower_cased(self):
        self.assertEqual(validate_plan(plan(issue="Final"))["issue"], "final")

    def test_unknown_issue_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan(issue="signed-off"))

    def test_empty_sections_raises(self):
        with self.assertRaises(ValueError):
            validate_plan(plan(sections={}))

    def test_unknown_section_name_raises(self):
        sections = {name: FINAL_MATURITY for name in MANDATED_SECTIONS}
        sections["catering-arrangements"] = FINAL_MATURITY
        with self.assertRaises(ValueError):
            validate_plan(plan(sections=sections))

    def test_unknown_section_maturity_raises(self):
        sections = {name: FINAL_MATURITY for name in MANDATED_SECTIONS}
        sections["pass-criteria"] = "nearly"
        with self.assertRaises(ValueError):
            validate_plan(plan(sections=sections))

    def test_maturity_ladder_is_ordered(self):
        self.assertLess(MATURITY_ORDER["draft"], MATURITY_ORDER["preliminary"])
        self.assertLess(MATURITY_ORDER["consolidated"], MATURITY_ORDER[FINAL_MATURITY])


class TestRequirementCoverage(unittest.TestCase):
    def test_full_coverage_is_exactly_one(self):
        trace = requirement_coverage(
            [requirement("R-1"), requirement("R-2")],
            [case("VC-1", ("R-1", "R-2"))],
        )
        self.assertAlmostEqual(trace["coverage_fraction"], 1.0, places=9)
        self.assertEqual(trace["uncovered_requirement_ids"], [])

    def test_uncovered_requirement_is_named(self):
        trace = requirement_coverage(
            [requirement("R-1"), requirement("R-2")],
            [case("VC-1", ("R-1",))],
        )
        self.assertEqual(trace["uncovered_requirement_ids"], ["R-2"])
        self.assertAlmostEqual(trace["coverage_fraction"], 0.5, places=9)

    def test_requirement_not_owing_validation_is_out_of_the_denominator(self):
        trace = requirement_coverage(
            [requirement("R-1"), requirement("R-2", validation_required=False)],
            [case("VC-1", ("R-1",))],
        )
        self.assertEqual(trace["owing_count"], 1)
        self.assertAlmostEqual(trace["coverage_fraction"], 1.0, places=9)

    def test_case_tracing_a_non_owing_requirement_is_reported(self):
        trace = requirement_coverage(
            [requirement("R-1"), requirement("R-2", validation_required=False)],
            [case("VC-1", ("R-1",)), case("VC-2", ("R-2",))],
        )
        self.assertEqual(trace["over_traced_requirement_ids"], ["R-2"])

    def test_orphan_case_is_named(self):
        trace = requirement_coverage(
            [requirement("R-1")],
            [case("VC-1", ("R-1",)), case("VC-2", ())],
        )
        self.assertEqual(trace["orphan_case_ids"], ["VC-2"])

    def test_unknown_requirement_reference_raises(self):
        with self.assertRaises(ValueError):
            requirement_coverage([requirement("R-1")], [case("VC-1", ("R-404",))])

    def test_duplicate_requirement_id_raises(self):
        with self.assertRaises(ValueError):
            requirement_coverage([requirement("R-1"), requirement("R-1")], [case()])

    def test_duplicate_case_id_raises(self):
        with self.assertRaises(ValueError):
            requirement_coverage([requirement("R-1")], [case("VC-1"), case("VC-1")])

    def test_register_where_nothing_owes_validation_raises(self):
        with self.assertRaises(ValueError):
            requirement_coverage(
                [requirement("R-1", validation_required=False)],
                [case("VC-1", ())],
            )

    def test_empty_case_register_raises(self):
        with self.assertRaises(ValueError):
            requirement_coverage([requirement("R-1")], [])


class TestCaseReadiness(unittest.TestCase):
    def test_all_runnable_is_exactly_one(self):
        ready = case_readiness([case("VC-1"), case("VC-2")])
        self.assertAlmostEqual(ready["runnable_fraction"], 1.0, places=9)

    def test_missing_pass_criterion_is_named(self):
        ready = case_readiness([case("VC-1"), case("VC-2", pass_criterion=None)])
        self.assertEqual(ready["cases_without_pass_criterion"], ["VC-2"])
        self.assertAlmostEqual(ready["runnable_fraction"], 0.5, places=9)

    def test_test_case_without_environment_is_named(self):
        ready = case_readiness([case("VC-1", environment=None)])
        self.assertEqual(ready["test_cases_without_environment"], ["VC-1"])

    def test_analysis_case_needs_no_environment(self):
        ready = case_readiness([case("VC-1", method="analysis", environment=None)])
        self.assertEqual(ready["test_cases_without_environment"], [])
        self.assertAlmostEqual(ready["runnable_fraction"], 1.0, places=9)

    def test_one_case_failing_both_checks_is_counted_once(self):
        ready = case_readiness(
            [case("VC-1"), case("VC-2", environment=None, pass_criterion=None)]
        )
        self.assertAlmostEqual(ready["runnable_fraction"], 0.5, places=9)


class TestStaleConfiguration(unittest.TestCase):
    def test_baseline_matched_cases_are_not_stale(self):
        self.assertEqual(stale_configuration_cases([case("VC-1")], BASELINE), [])

    def test_superseded_build_is_named(self):
        stale = stale_configuration_cases(
            [case("VC-1"), case("VC-2", configuration_id="DEV-BUILD-06")], BASELINE
        )
        self.assertEqual(stale, ["VC-2"])

    def test_blank_baseline_raises(self):
        with self.assertRaises(ValueError):
            stale_configuration_cases([case("VC-1")], "  ")


class TestSectionCompletion(unittest.TestCase):
    def test_all_final_is_exactly_one(self):
        self.assertAlmostEqual(section_completion(plan())["section_fraction"], 1.0, places=9)

    def test_missing_section_is_named(self):
        sections = {name: FINAL_MATURITY for name in MANDATED_SECTIONS}
        del sections["anomaly-handling"]
        report = section_completion(plan(sections=sections))
        self.assertEqual(report["missing_sections"], ["anomaly-handling"])

    def test_immature_section_is_named(self):
        sections = {name: FINAL_MATURITY for name in MANDATED_SECTIONS}
        sections["pass-criteria"] = "consolidated"
        report = section_completion(plan(sections=sections))
        self.assertEqual(report["immature_sections"], ["pass-criteria"])


class TestCompletionIndex(unittest.TestCase):
    def test_all_measures_one_gives_unity(self):
        self.assertAlmostEqual(completion_index(1.0, 1.0, 1.0), 1.0, places=9)

    def test_all_measures_zero_gives_zero(self):
        self.assertAlmostEqual(completion_index(0.0, 0.0, 0.0), 0.0, places=9)

    def test_weights_are_applied(self):
        self.assertAlmostEqual(completion_index(1.0, 0.0, 0.0), 0.5, places=9)

    def test_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            completion_index(1.2, 1.0, 1.0)

    def test_non_numeric_fraction_raises(self):
        with self.assertRaises(ValueError):
            completion_index("1.0", 1.0, 1.0)


class TestAssessment(unittest.TestCase):
    def test_clean_plan_lets_validation_begin(self):
        report = assess_validation_plan_completion(clean_spec())
        self.assertTrue(report["validation_may_begin"])
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["completion_index"], 1.0, places=9)

    def test_uncovered_requirement_blocks_the_start(self):
        spec = clean_spec()
        spec["cases"] = [case("VC-1", ("R-1",))]
        report = assess_validation_plan_completion(spec)
        self.assertFalse(report["validation_may_begin"])
        self.assertEqual(report["uncovered_requirement_ids"], ["R-2"])

    def test_stale_case_configuration_blocks_the_start(self):
        spec = clean_spec()
        spec["cases"][1] = case("VC-2", ("R-2",), configuration_id="DEV-BUILD-06")
        report = assess_validation_plan_completion(spec)
        self.assertFalse(report["validation_may_begin"])
        self.assertEqual(report["stale_configuration_case_ids"], ["VC-2"])

    def test_draft_issue_blocks_even_with_full_coverage(self):
        spec = clean_spec()
        spec["plan"] = plan(issue="draft")
        report = assess_validation_plan_completion(spec)
        self.assertFalse(report["validation_may_begin"])
        self.assertAlmostEqual(report["completion_index"], 1.0, places=9)

    def test_missing_spec_key_raises(self):
        spec = clean_spec()
        del spec["cases"]
        with self.assertRaises(ValueError):
            assess_validation_plan_completion(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_validation_plan_completion([clean_spec()])

    def test_tolerance_is_small_and_positive(self):
        self.assertGreater(COMPLETION_TOLERANCE, 0.0)
        self.assertLess(COMPLETION_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
