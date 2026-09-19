"""Contract test for the device-validation-execution leaf (stdlib unittest)."""

import unittest

from e2040_device_validation_execution_logic import (
    COMPLETENESS_TOLERANCE,
    EXECUTION_STATES,
    PASSING_RESULTS,
    RESULTS,
    assess_validation_execution,
    completeness_index,
    configuration_mismatches,
    evidence_gaps,
    execution_coverage,
    outcome_split,
    retest_closure,
    validate_execution_record,
    validate_ledger,
)

DELIVERED = "DEV-FM-02"


def run_case(cid="VC-1", **kw):
    record = {
        "id": cid,
        "state": "run",
        "result": "pass",
        "configuration_id": DELIVERED,
        "evidence_ref": "VR-%s" % cid,
        "depends_on": [],
    }
    record.update(kw)
    return record


def pending_case(cid="VC-9", **kw):
    record = {"id": cid, "state": "not-run", "depends_on": []}
    record.update(kw)
    return record


def clean_spec():
    return {
        "ledger": [run_case("VC-1"), run_case("VC-2")],
        "delivered_configuration_id": DELIVERED,
    }


class TestValidateExecutionRecord(unittest.TestCase):
    def test_state_is_lower_cased(self):
        self.assertEqual(validate_execution_record(run_case(state="RUN"))["state"], "run")

    def test_every_declared_state_is_reachable(self):
        self.assertEqual(set(EXECUTION_STATES), {"not-run", "run", "aborted"})

    def test_every_declared_result_is_accepted(self):
        for result in RESULTS:
            self.assertEqual(validate_execution_record(run_case(result=result))["result"], result)

    def test_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            validate_execution_record(run_case(state="in-progress"))

    def test_unknown_result_raises(self):
        with self.assertRaises(ValueError):
            validate_execution_record(run_case(result="probably-fine"))

    def test_run_without_result_raises(self):
        with self.assertRaises(ValueError):
            validate_execution_record(run_case(result=None))

    def test_not_run_carrying_a_result_raises(self):
        with self.assertRaises(ValueError):
            validate_execution_record(pending_case(result="pass"))

    def test_run_without_configuration_raises(self):
        with self.assertRaises(ValueError):
            validate_execution_record(run_case(configuration_id=None))

    def test_self_dependency_raises(self):
        with self.assertRaises(ValueError):
            validate_execution_record(run_case("VC-1", depends_on=["VC-1"]))

    def test_repeated_dependency_raises(self):
        with self.assertRaises(ValueError):
            validate_execution_record(run_case("VC-1", depends_on=["VC-2", "VC-2"]))

    def test_dependency_string_raises(self):
        with self.assertRaises(ValueError):
            validate_execution_record(run_case("VC-1", depends_on="VC-2"))


class TestValidateLedger(unittest.TestCase):
    def test_empty_ledger_raises(self):
        with self.assertRaises(ValueError):
            validate_ledger([])

    def test_duplicate_case_id_raises(self):
        with self.assertRaises(ValueError):
            validate_ledger([run_case("VC-1"), run_case("VC-1")])

    def test_unknown_dependency_raises(self):
        with self.assertRaises(ValueError):
            validate_ledger([run_case("VC-1", depends_on=["VC-404"])])

    def test_known_dependency_is_accepted(self):
        ledger = validate_ledger([run_case("VC-1"), run_case("VC-2", depends_on=["VC-1"])])
        self.assertEqual(ledger[1]["depends_on"], ["VC-1"])


class TestExecutionCoverage(unittest.TestCase):
    def test_all_run_is_fraction_one(self):
        report = execution_coverage([run_case("VC-1"), run_case("VC-2")])
        self.assertAlmostEqual(report["execution_fraction"], 1.0, places=9)

    def test_half_run_is_fraction_one_half(self):
        report = execution_coverage([run_case("VC-1"), pending_case("VC-2")])
        self.assertAlmostEqual(report["execution_fraction"], 0.5, places=9)
        self.assertEqual(report["not_run_case_ids"], ["VC-2"])

    def test_aborted_case_is_named_and_not_counted_as_run(self):
        report = execution_coverage([run_case("VC-1"), pending_case("VC-2", state="aborted")])
        self.assertEqual(report["aborted_case_ids"], ["VC-2"])
        self.assertEqual(report["run_count"], 1)


class TestOutcomeSplit(unittest.TestCase):
    def test_all_pass_is_fraction_one(self):
        report = outcome_split([run_case("VC-1"), run_case("VC-2")])
        self.assertAlmostEqual(report["pass_fraction"], 1.0, places=9)

    def test_failure_lowers_the_pass_fraction(self):
        report = outcome_split([run_case("VC-1"), run_case("VC-2", result="fail")])
        self.assertAlmostEqual(report["pass_fraction"], 0.5, places=9)
        self.assertEqual(report["failed_case_ids"], ["VC-2"])

    def test_deviation_counts_as_a_pass_but_is_still_named(self):
        report = outcome_split([run_case("VC-1", result="pass-with-deviation")])
        self.assertAlmostEqual(report["pass_fraction"], 1.0, places=9)
        self.assertEqual(report["deviation_case_ids"], ["VC-1"])

    def test_nothing_run_gives_zero_not_a_division_error(self):
        report = outcome_split([pending_case("VC-1")])
        self.assertAlmostEqual(report["pass_fraction"], 0.0, places=9)
        self.assertEqual(report["run_count"], 0)

    def test_passing_results_are_a_subset_of_results(self):
        for result in PASSING_RESULTS:
            self.assertIn(result, RESULTS)


class TestEvidenceGaps(unittest.TestCase):
    def test_documented_run_is_fraction_one(self):
        report = evidence_gaps([run_case("VC-1")])
        self.assertAlmostEqual(report["documentation_fraction"], 1.0, places=9)

    def test_missing_evidence_reference_is_named(self):
        report = evidence_gaps([run_case("VC-1"), run_case("VC-2", evidence_ref=None)])
        self.assertEqual(report["undocumented_case_ids"], ["VC-2"])
        self.assertAlmostEqual(report["documentation_fraction"], 0.5, places=9)

    def test_case_never_run_is_not_an_evidence_gap(self):
        report = evidence_gaps([run_case("VC-1"), pending_case("VC-2")])
        self.assertEqual(report["undocumented_case_ids"], [])


class TestConfigurationMismatches(unittest.TestCase):
    def test_delivered_article_is_not_a_mismatch(self):
        self.assertEqual(configuration_mismatches([run_case("VC-1")], DELIVERED), [])

    def test_earlier_article_is_a_mismatch(self):
        mismatched = configuration_mismatches(
            [run_case("VC-1"), run_case("VC-2", configuration_id="DEV-EM-01")], DELIVERED
        )
        self.assertEqual(mismatched, ["VC-2"])

    def test_blank_delivered_configuration_raises(self):
        with self.assertRaises(ValueError):
            configuration_mismatches([run_case("VC-1")], "   ")


class TestRetestClosure(unittest.TestCase):
    def test_no_failure_means_no_retest(self):
        self.assertEqual(retest_closure([run_case("VC-1"), run_case("VC-2")]), [])

    def test_a_failure_puts_itself_in_the_retest_set(self):
        self.assertEqual(retest_closure([run_case("VC-1", result="fail")]), ["VC-1"])

    def test_retest_propagates_transitively(self):
        ledger = [
            run_case("VC-1", result="fail"),
            run_case("VC-2", depends_on=["VC-1"]),
            run_case("VC-3", depends_on=["VC-2"]),
            run_case("VC-4"),
        ]
        self.assertEqual(retest_closure(ledger), ["VC-1", "VC-2", "VC-3"])

    def test_independent_branch_is_untouched_by_a_failure(self):
        ledger = [
            run_case("VC-1", result="fail"),
            run_case("VC-2", depends_on=["VC-1"]),
            run_case("VC-3"),
        ]
        self.assertNotIn("VC-3", retest_closure(ledger))

    def test_dependency_cycle_raises(self):
        ledger = [
            run_case("VC-1", depends_on=["VC-2"]),
            run_case("VC-2", depends_on=["VC-1"]),
        ]
        with self.assertRaises(ValueError):
            retest_closure(ledger)


class TestCompletenessIndex(unittest.TestCase):
    def test_all_measures_one_gives_unity(self):
        self.assertAlmostEqual(completeness_index(1.0, 1.0, 1.0), 1.0, places=9)

    def test_all_measures_zero_gives_zero(self):
        self.assertAlmostEqual(completeness_index(0.0, 0.0, 0.0), 0.0, places=9)

    def test_documentation_carries_the_smallest_weight(self):
        self.assertAlmostEqual(completeness_index(0.0, 0.0, 1.0), 0.2, places=9)

    def test_fraction_below_zero_raises(self):
        with self.assertRaises(ValueError):
            completeness_index(-0.1, 1.0, 1.0)

    def test_boolean_fraction_raises(self):
        with self.assertRaises(ValueError):
            completeness_index(True, 1.0, 1.0)


class TestAssessment(unittest.TestCase):
    def test_clean_ledger_declares_validation_complete(self):
        report = assess_validation_execution(clean_spec())
        self.assertTrue(report["validation_complete"])
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["completeness_index"], 1.0, places=9)

    def test_unrun_case_blocks_completion(self):
        spec = clean_spec()
        spec["ledger"].append(pending_case("VC-3"))
        report = assess_validation_execution(spec)
        self.assertFalse(report["validation_complete"])
        self.assertEqual(report["not_run_case_ids"], ["VC-3"])

    def test_failure_reports_both_the_failure_and_its_dependents(self):
        spec = clean_spec()
        spec["ledger"] = [
            run_case("VC-1", result="fail"),
            run_case("VC-2", depends_on=["VC-1"]),
        ]
        report = assess_validation_execution(spec)
        self.assertEqual(report["failed_case_ids"], ["VC-1"])
        self.assertEqual(report["retest_case_ids"], ["VC-1", "VC-2"])

    def test_evidence_on_the_wrong_article_blocks_completion(self):
        spec = clean_spec()
        spec["ledger"][1] = run_case("VC-2", configuration_id="DEV-EM-01")
        report = assess_validation_execution(spec)
        self.assertEqual(report["wrong_configuration_case_ids"], ["VC-2"])
        self.assertFalse(report["validation_complete"])

    def test_undocumented_run_blocks_completion_even_when_it_passed(self):
        spec = clean_spec()
        spec["ledger"][1] = run_case("VC-2", evidence_ref=None)
        report = assess_validation_execution(spec)
        self.assertEqual(report["undocumented_case_ids"], ["VC-2"])
        self.assertFalse(report["validation_complete"])

    def test_missing_spec_key_raises(self):
        spec = clean_spec()
        del spec["delivered_configuration_id"]
        with self.assertRaises(ValueError):
            assess_validation_execution(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_validation_execution([clean_spec()])

    def test_tolerance_is_small_and_positive(self):
        self.assertGreater(COMPLETENESS_TOLERANCE, 0.0)
        self.assertLess(COMPLETENESS_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
