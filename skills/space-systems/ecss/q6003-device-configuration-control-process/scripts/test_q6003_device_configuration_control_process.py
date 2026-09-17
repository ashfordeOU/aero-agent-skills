"""Contract tests for the clause 8.3 device change-control logic."""

import unittest

from q6003_device_configuration_control_process_logic import (
    ALL_IMPACTS,
    APPROVAL_AUTHORITIES,
    BASELINE_STAGES,
    CHANGE_CATEGORIES,
    DISPOSITIONS,
    EXTERNAL_IMPACTS,
    INTERNAL_IMPACTS,
    absent_evidence,
    approval_authority,
    assess_change,
    categorize_change,
    format_baseline_version,
    implementation_allowed,
    next_baseline_version,
    normalize_impacts,
    normalize_stage,
    normalize_token,
    parse_baseline_version,
    parse_iso_date,
    required_evidence,
    sequence_findings,
    validate_baseline,
)


def baseline(**overrides):
    base = {"stage": "design", "version": "2.3", "established": True}
    base.update(overrides)
    return base


def record(**overrides):
    base = {
        "raised_on": "2026-03-01",
        "dispositioned_on": "2026-03-15",
        "implemented_on": "2026-03-20",
    }
    base.update(overrides)
    return base


def full_spec(**overrides):
    base = {
        "baseline": baseline(),
        "impacts": ["internal-implementation-detail"],
        "record": record(),
        "disposition": "approved",
        "declared_evidence": ["impact-assessment", "updated-item-data-list"],
    }
    base.update(overrides)
    return base


class NormalisationTests(unittest.TestCase):
    def test_token_is_trimmed_and_lower_cased(self):
        self.assertEqual(normalize_token(" Approved ", "disposition"), "approved")

    def test_blank_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("   ", "disposition")

    def test_stage_vocabulary_is_closed(self):
        self.assertEqual(normalize_stage(" Product "), "product")
        with self.assertRaises(ValueError):
            normalize_stage("provisional")

    def test_stage_list_is_ordered_from_functional(self):
        self.assertEqual(BASELINE_STAGES[0], "functional")

    def test_unknown_impact_rejected(self):
        with self.assertRaises(ValueError):
            normalize_impacts(["affects-vibes"])

    def test_impacts_deduplicated_and_sorted(self):
        got = normalize_impacts(
            ["external-interface", "External-Interface", "form-fit-or-function"]
        )
        self.assertEqual(got, ["external-interface", "form-fit-or-function"])

    def test_impact_vocabulary_partitions(self):
        self.assertEqual(len(ALL_IMPACTS), len(EXTERNAL_IMPACTS) + len(INTERNAL_IMPACTS))
        self.assertEqual(set(EXTERNAL_IMPACTS) & set(INTERNAL_IMPACTS), set())


class BaselineTests(unittest.TestCase):
    def test_version_parsed(self):
        self.assertEqual(parse_baseline_version(" 2.3 "), (2, 3))

    def test_three_field_version_rejected(self):
        with self.assertRaises(ValueError):
            parse_baseline_version("2.3.1")

    def test_non_numeric_version_rejected(self):
        with self.assertRaises(ValueError):
            parse_baseline_version("2.x")

    def test_zero_major_rejected(self):
        with self.assertRaises(ValueError):
            parse_baseline_version("0.9")

    def test_version_round_trips(self):
        self.assertEqual(format_baseline_version((2, 3)), "2.3")

    def test_unestablished_baseline_refused(self):
        with self.assertRaises(ValueError):
            validate_baseline(baseline(established=False))

    def test_non_boolean_established_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline(baseline(established="yes"))

    def test_valid_baseline_normalised(self):
        got = validate_baseline(baseline(stage=" Design "))
        self.assertEqual(got["stage"], "design")
        self.assertEqual(got["version"], (2, 3))


class CategoryTests(unittest.TestCase):
    def test_internal_only_change_is_second_category(self):
        category, triggers = categorize_change(["internal-implementation-detail"])
        self.assertEqual(category, "second-category")
        self.assertEqual(triggers, [])

    def test_external_interface_pulls_it_to_first_category(self):
        category, triggers = categorize_change(
            ["internal-implementation-detail", "external-interface"]
        )
        self.assertEqual(category, "first-category")
        self.assertEqual(triggers, ["external-interface"])

    def test_every_external_impact_triggers_on_its_own(self):
        for impact in EXTERNAL_IMPACTS:
            category, triggers = categorize_change([impact])
            self.assertEqual(category, "first-category")
            self.assertEqual(triggers, [impact])

    def test_no_declared_impact_rejected(self):
        with self.assertRaises(ValueError):
            categorize_change([])

    def test_category_vocabulary_is_closed(self):
        self.assertEqual(set(CHANGE_CATEGORIES), set(APPROVAL_AUTHORITIES))


class RoutingTests(unittest.TestCase):
    def test_first_category_goes_to_the_customer_board(self):
        self.assertEqual(approval_authority("first-category"), "customer-change-board")

    def test_second_category_stays_with_the_supplier_board(self):
        self.assertEqual(
            approval_authority("second-category"), "supplier-configuration-board"
        )

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            approval_authority("third-category")


class EvidenceTests(unittest.TestCase):
    def test_first_category_demands_more_than_second(self):
        first = required_evidence("first-category", "design")
        second = required_evidence("second-category", "design")
        self.assertGreater(len(first), len(second))

    def test_product_stage_adds_the_recall_assessment(self):
        self.assertIn(
            "as-built-recall-assessment",
            required_evidence("second-category", "product"),
        )

    def test_design_stage_does_not_demand_a_recall_assessment(self):
        self.assertNotIn(
            "as-built-recall-assessment",
            required_evidence("second-category", "design"),
        )

    def test_absent_evidence_listed(self):
        absent = absent_evidence("first-category", "design", ["impact-assessment"])
        self.assertIn("re-verification-plan", absent)
        self.assertNotIn("impact-assessment", absent)

    def test_complete_package_has_no_absent_items(self):
        demanded = required_evidence("first-category", "product")
        self.assertEqual(absent_evidence("first-category", "product", demanded), [])

    def test_declared_evidence_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            absent_evidence("second-category", "design", "impact-assessment")


class SequenceTests(unittest.TestCase):
    def test_clean_order_has_no_findings(self):
        self.assertEqual(sequence_findings(record()), [])

    def test_implementation_before_disposition_is_a_finding(self):
        findings = sequence_findings(record(implemented_on="2026-03-10"))
        self.assertIn("implemented before it was dispositioned", " ".join(findings))

    def test_implementation_with_no_disposition_is_a_finding(self):
        findings = sequence_findings(
            {"raised_on": "2026-03-01", "implemented_on": "2026-03-10"}
        )
        self.assertIn("no disposition on record", " ".join(findings))

    def test_disposition_before_raising_is_a_finding(self):
        findings = sequence_findings(record(dispositioned_on="2026-02-01"))
        self.assertIn("dispositioned before it was raised", " ".join(findings))

    def test_open_change_with_no_implementation_is_clean(self):
        self.assertEqual(sequence_findings({"raised_on": "2026-03-01"}), [])

    def test_missing_raised_date_rejected(self):
        with self.assertRaises(ValueError):
            sequence_findings({"implemented_on": "2026-03-10"})

    def test_bad_date_form_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026/03/01")


class ImplementationGateTests(unittest.TestCase):
    def test_approved_complete_and_ordered_is_allowed(self):
        self.assertTrue(implementation_allowed("approved", True, True))

    def test_deferred_change_is_not_allowed(self):
        self.assertFalse(implementation_allowed("deferred", True, True))

    def test_incomplete_evidence_blocks_an_approved_change(self):
        self.assertFalse(implementation_allowed("approved", False, True))

    def test_out_of_order_record_blocks_an_approved_change(self):
        self.assertFalse(implementation_allowed("approved", True, False))

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            implementation_allowed("pending-vibes", True, True)

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            implementation_allowed("approved", "yes", True)

    def test_disposition_vocabulary_is_closed(self):
        self.assertIn("not-dispositioned", DISPOSITIONS)


class BaselineIncrementTests(unittest.TestCase):
    def test_first_category_bumps_the_major_and_resets_the_minor(self):
        self.assertEqual(next_baseline_version("2.3", "first-category"), (3, 0))

    def test_second_category_bumps_the_minor(self):
        self.assertEqual(next_baseline_version("2.3", "second-category"), (2, 4))

    def test_pair_input_accepted(self):
        self.assertEqual(next_baseline_version((2, 3), "second-category"), (2, 4))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            next_baseline_version("2.3", "third-category")

    def test_malformed_current_version_rejected(self):
        with self.assertRaises(ValueError):
            next_baseline_version(23, "second-category")


class AssessmentTests(unittest.TestCase):
    def test_clean_second_category_change_is_under_control(self):
        result = assess_change(full_spec())
        self.assertEqual(result["category"], "second-category")
        self.assertTrue(result["implementation_allowed"])
        self.assertTrue(result["under_control"])
        self.assertEqual(result["resulting_baseline_version"], "2.4")

    def test_first_category_change_routes_and_increments_differently(self):
        spec = full_spec(
            impacts=["external-interface"],
            declared_evidence=list(required_evidence("first-category", "design")),
        )
        result = assess_change(spec)
        self.assertEqual(result["approval_authority"], "customer-change-board")
        self.assertEqual(result["resulting_baseline_version"], "3.0")

    def test_missing_evidence_blocks_and_holds_the_baseline(self):
        spec = full_spec(impacts=["external-interface"])
        result = assess_change(spec)
        self.assertFalse(result["implementation_allowed"])
        self.assertEqual(result["resulting_baseline_version"], "2.3")
        self.assertIn("re-verification-plan", result["absent_evidence"])

    def test_out_of_order_implementation_is_reported(self):
        result = assess_change(full_spec(record=record(implemented_on="2026-03-02")))
        self.assertFalse(result["implementation_allowed"])
        self.assertTrue(result["order_findings"])

    def test_open_change_is_reported_against_its_board(self):
        spec = full_spec(
            disposition="not-dispositioned",
            record={"raised_on": "2026-03-01"},
        )
        result = assess_change(spec)
        self.assertFalse(result["implementation_allowed"])
        self.assertIn("supplier-configuration-board", " ".join(result["findings"]))

    def test_product_stage_change_demands_the_recall_assessment(self):
        result = assess_change(full_spec(baseline=baseline(stage="product")))
        self.assertIn("as-built-recall-assessment", result["absent_evidence"])

    def test_unestablished_baseline_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_change(full_spec(baseline=baseline(established=False)))

    def test_spec_missing_disposition_rejected(self):
        spec = full_spec()
        del spec["disposition"]
        with self.assertRaises(ValueError):
            assess_change(spec)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_change(["baseline"])


if __name__ == "__main__":
    unittest.main()
