"""Contract tests for the clause 6.3.1 solar cell assembly acceptance logic."""

import copy
import unittest

from e2008_sca_acceptance_testing_general_logic import (
    ARTICLE_ACCEPTED,
    ARTICLE_TEST_FAILED,
    ARTICLE_TEST_NOT_RUN,
    ARTICLE_TESTS_MISSING,
    LOT_ACCEPTED,
    LOT_INCOMPLETE,
    REQUIRED_SCA_ACCEPTANCE_TESTS,
    assess_article,
    assess_lot_acceptance,
    exempted_populations,
    population_summary,
    validate_identifier,
    validate_test_record,
)


def _records(**overrides):
    """Return a full pass record set, with named activities overridden."""
    out = []
    for test in REQUIRED_SCA_ACCEPTANCE_TESTS:
        key = test.replace("-", "_")
        out.append({"test": test, "result": overrides.get(key, "pass")})
    return out


def _article(article_id, population, records=None):
    return {
        "article_id": article_id,
        "population": population,
        "test_records": _records() if records is None else copy.deepcopy(records),
    }


def _spec(**overrides):
    spec = {
        "lot_id": "SCA-LOT-2026-014",
        "articles": [
            _article("SCA-0001", "delivery"),
            _article("SCA-0002", "delivery"),
            _article("SCA-0003", "delivery"),
            _article("QC-0001", "qualification-allocated"),
            _article("QC-0002", "qualification-allocated"),
        ],
    }
    spec.update(overrides)
    return spec


def _swap(spec, article_id, records):
    out = copy.deepcopy(spec)
    for article in out["articles"]:
        if article["article_id"] == article_id:
            article["test_records"] = copy.deepcopy(records)
    return out


class ValidationHelperTests(unittest.TestCase):
    def test_identifier_is_trimmed(self):
        self.assertEqual(validate_identifier("  SCA-0001 ", "id"), "SCA-0001")

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("", "id")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(1, "id")

    def test_valid_record_is_normalised(self):
        row = validate_test_record({"test": "sca-visual-inspection", "result": "pass"})
        self.assertEqual(row["result"], "pass")

    def test_record_outside_the_acceptance_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_record({"test": "sca-thermal-cycling", "result": "pass"})

    def test_unknown_result_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_record({"test": "sca-visual-inspection", "result": "waived"})

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_record(["sca-visual-inspection"])


class ArticleTests(unittest.TestCase):
    def test_fully_tested_delivery_article_is_accepted(self):
        row = assess_article(_article("SCA-0001", "delivery"))
        self.assertEqual(row["verdict"], ARTICLE_ACCEPTED)
        self.assertAlmostEqual(row["activity_coverage"], 1.0, places=9)

    def test_qualification_article_is_held_to_the_same_set(self):
        row = assess_article(_article("QC-0001", "qualification-allocated"))
        self.assertEqual(row["verdict"], ARTICLE_ACCEPTED)
        self.assertEqual(row["missing_tests"], [])

    def test_unknown_population_rejected(self):
        with self.assertRaises(ValueError):
            assess_article(_article("SCA-0001", "engineering-model"))

    def test_article_with_no_records_at_all_is_missing_every_test(self):
        row = assess_article(_article("SCA-0009", "delivery", records=[]))
        self.assertEqual(row["verdict"], ARTICLE_TESTS_MISSING)
        self.assertEqual(len(row["missing_tests"]), len(REQUIRED_SCA_ACCEPTANCE_TESTS))
        self.assertAlmostEqual(row["activity_coverage"], 0.0, places=9)

    def test_partial_record_names_the_absent_activity(self):
        records = [r for r in _records() if r["test"] != "sca-dimensional-measurement"]
        row = assess_article(_article("SCA-0010", "delivery", records=records))
        self.assertEqual(row["missing_tests"], ["sca-dimensional-measurement"])

    def test_not_run_is_distinguished_from_missing(self):
        row = assess_article(
            _article(
                "SCA-0011", "delivery", records=_records(sca_dimensional_measurement="not-run")
            )
        )
        self.assertEqual(row["verdict"], ARTICLE_TEST_NOT_RUN)
        self.assertEqual(row["missing_tests"], [])

    def test_failed_activity_is_reported_as_a_failure(self):
        row = assess_article(
            _article("SCA-0012", "delivery", records=_records(sca_visual_inspection="fail"))
        )
        self.assertEqual(row["verdict"], ARTICLE_TEST_FAILED)
        self.assertEqual(row["failed_tests"], ["sca-visual-inspection"])

    def test_missing_outranks_a_failure(self):
        records = [
            r for r in _records(sca_visual_inspection="fail")
            if r["test"] != "sca-dimensional-measurement"
        ]
        row = assess_article(_article("SCA-0013", "delivery", records=records))
        self.assertEqual(row["verdict"], ARTICLE_TESTS_MISSING)
        self.assertEqual(row["rank"], 0)

    def test_duplicate_activity_record_rejected(self):
        records = _records() + [{"test": "sca-visual-inspection", "result": "pass"}]
        with self.assertRaises(ValueError):
            assess_article(_article("SCA-0014", "delivery", records=records))

    def test_policy_may_carry_a_dispositioned_failure(self):
        row = assess_article(
            _article("SCA-0015", "delivery", records=_records(sca_visual_inspection="fail")),
            {"allow_failed_article": True},
        )
        self.assertTrue(row["acceptable"])

    def test_partial_activity_coverage_is_a_fraction(self):
        records = _records()[:2]
        row = assess_article(_article("SCA-0016", "delivery", records=records))
        self.assertAlmostEqual(row["activity_coverage"], 0.5, places=9)


class PopulationTests(unittest.TestCase):
    def test_summary_counts_only_its_own_population(self):
        graded = [assess_article(a) for a in _spec()["articles"]]
        summary = population_summary(graded, "delivery")
        self.assertEqual(summary["article_count"], 3)
        self.assertAlmostEqual(summary["coverage_share"], 1.0, places=9)

    def test_absent_population_reports_itself_absent(self):
        graded = [assess_article(_article("SCA-0001", "delivery"))]
        summary = population_summary(graded, "qualification-allocated")
        self.assertFalse(summary["present"])
        self.assertEqual(summary["article_count"], 0)

    def test_unknown_population_rejected_by_the_summary(self):
        with self.assertRaises(ValueError):
            population_summary([], "flight-spare")

    def test_population_with_no_acceptance_work_is_exempted(self):
        graded = [
            assess_article(_article("SCA-0001", "delivery")),
            assess_article(_article("QC-0001", "qualification-allocated", records=[])),
        ]
        self.assertEqual(exempted_populations(graded), ["qualification-allocated"])

    def test_a_partially_tested_population_is_not_exempted(self):
        graded = [
            assess_article(
                _article("QC-0001", "qualification-allocated", records=_records()[:1])
            )
        ]
        self.assertEqual(exempted_populations(graded), [])


class LotAssessmentTests(unittest.TestCase):
    def test_clean_lot_is_accepted(self):
        result = assess_lot_acceptance(_spec())
        self.assertEqual(result["verdict"], LOT_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["lot_coverage_share"], 1.0, places=9)

    def test_exempting_the_qualification_articles_fails_the_lot(self):
        spec = _swap(_spec(), "QC-0001", [])
        spec = _swap(spec, "QC-0002", [])
        result = assess_lot_acceptance(spec)
        self.assertEqual(result["verdict"], LOT_INCOMPLETE)
        self.assertEqual(result["exempted_populations"], ["qualification-allocated"])
        self.assertTrue(any("exempted" in f for f in result["findings"]))

    def test_a_lot_with_no_qualification_article_is_reported(self):
        spec = _spec()
        spec["articles"] = [a for a in spec["articles"] if a["population"] == "delivery"]
        result = assess_lot_acceptance(spec)
        self.assertTrue(
            any("carries no qualification-allocated" in f for f in result["findings"])
        )

    def test_single_failed_article_keeps_the_lot_open(self):
        spec = _swap(_spec(), "SCA-0002", _records(sca_visual_inspection="fail"))
        result = assess_lot_acceptance(spec)
        self.assertEqual(result["verdict"], LOT_INCOMPLETE)
        self.assertIn("SCA-0002", result["articles_by_verdict"][ARTICLE_TEST_FAILED])

    def test_policy_can_accept_a_dispositioned_failure_but_coverage_still_drops(self):
        spec = _swap(_spec(), "SCA-0002", _records(sca_visual_inspection="fail"))
        spec["policy"] = {"allow_failed_article": True, "min_population_coverage": 0.5}
        result = assess_lot_acceptance(spec)
        self.assertEqual(result["verdict"], LOT_ACCEPTED)
        self.assertAlmostEqual(result["lot_coverage_share"], 1.0, places=9)

    def test_coverage_exactly_on_the_policy_minimum_passes(self):
        spec = _swap(_spec(), "SCA-0002", _records(sca_visual_inspection="fail"))
        spec["policy"] = {"min_population_coverage": 2.0 / 3.0, "allow_failed_article": True}
        result = assess_lot_acceptance(spec)
        self.assertAlmostEqual(
            result["populations"]["delivery"]["coverage_share"], 2.0 / 3.0, places=9
        )
        self.assertEqual(result["verdict"], LOT_ACCEPTED)

    def test_articles_are_grouped_by_verdict(self):
        spec = _swap(_spec(), "QC-0002", _records(sca_dimensional_measurement="not-run"))
        result = assess_lot_acceptance(spec)
        self.assertEqual(
            result["articles_by_verdict"][ARTICLE_TEST_NOT_RUN], ["QC-0002"]
        )
        self.assertEqual(len(result["articles_by_verdict"][ARTICLE_ACCEPTED]), 4)

    def test_duplicate_article_identifier_rejected(self):
        spec = _spec()
        spec["articles"] = spec["articles"] + [_article("SCA-0001", "delivery")]
        with self.assertRaises(ValueError):
            assess_lot_acceptance(spec)

    def test_empty_article_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance(_spec(articles=[]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["lot_id"]
        with self.assertRaises(ValueError):
            assess_lot_acceptance(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance(["SCA-LOT-2026-014"])

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance(_spec(policy={"min_coverage": 1.0}))

    def test_out_of_range_coverage_policy_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance(_spec(policy={"min_population_coverage": 1.5}))

    def test_lot_id_is_trimmed_in_the_report(self):
        result = assess_lot_acceptance(_spec(lot_id="  SCA-LOT-2026-014  "))
        self.assertEqual(result["lot_id"], "SCA-LOT-2026-014")


if __name__ == "__main__":
    unittest.main()
