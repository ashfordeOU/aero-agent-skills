"""Contract test for the wiring-and-shielding-verification leaf (stdlib unittest)."""

import unittest

from e2007_wiring_and_shielding_verification_logic import (
    FULL_INSPECTION_FRACTION,
    MAX_PIGTAIL_LENGTH_MM,
    SAMPLED_INSPECTION_FRACTION,
    TERMINATION_CIRCUMFERENTIAL,
    TERMINATION_PIGTAIL,
    assess_run,
    assess_wiring_and_shielding_verification,
    category_agreement_findings,
    coverage_findings,
    design_review_findings,
    inspection_coverage,
    physical_inspection_findings,
    required_inspection_fraction,
    required_termination,
    shield_treatment_findings,
    validate_run,
)


def run(rid="W-1", category="signal", **kw):
    record = {
        "id": rid,
        "declared_category": category,
        "inspected_category": category,
        "declared_termination": "pigtail",
        "inspected_termination": "pigtail",
        "declared_pigtail_length_mm": 12.0,
        "inspected_pigtail_length_mm": 12.0,
        "shielded": True,
        "design_review_done": True,
        "physical_inspection_done": True,
        "design_review_evidence": "DRW-4471 rev C",
        "inspection_evidence": "INS-0912 sheet 3",
    }
    record.update(kw)
    return record


def sensitive(rid="W-S", **kw):
    record = run(
        rid,
        category="sensitive",
        declared_termination="full-circumference",
        inspected_termination="full-circumference",
        declared_pigtail_length_mm=None,
        inspected_pigtail_length_mm=None,
    )
    record.update(kw)
    return record


class TestValidateRun(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_run(
            {"id": "W-1", "declared_category": "signal",
             "declared_termination": "pigtail"}
        )
        self.assertTrue(norm["shielded"])
        self.assertFalse(norm["design_review_done"])
        self.assertFalse(norm["physical_inspection_done"])
        self.assertIsNone(norm["inspected_category"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_run(["W-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_run(run(""))

    def test_unknown_declared_category_raises(self):
        with self.assertRaises(ValueError):
            validate_run(run("W-1", category="mystery"))

    def test_unknown_inspected_category_raises(self):
        with self.assertRaises(ValueError):
            validate_run(run("W-1", inspected_category="mystery"))

    def test_unknown_termination_raises(self):
        with self.assertRaises(ValueError):
            validate_run(run("W-1", declared_termination="tape-wrap"))

    def test_negative_pigtail_length_raises(self):
        with self.assertRaises(ValueError):
            validate_run(run("W-1", declared_pigtail_length_mm=-5.0))

    def test_non_boolean_stage_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_run(run("W-1", design_review_done="yes"))

    def test_non_string_evidence_raises(self):
        with self.assertRaises(ValueError):
            validate_run(run("W-1", inspection_evidence=17))


class TestDesignReviewStage(unittest.TestCase):
    def test_complete_review_is_clean(self):
        self.assertEqual(design_review_findings(run()), [])

    def test_missing_review_is_flagged(self):
        self.assertEqual(
            design_review_findings(run("W-1", design_review_done=False)),
            ["design-review-not-performed"],
        )

    def test_review_without_evidence_is_flagged(self):
        self.assertIn(
            "design-review-without-an-evidence-reference",
            design_review_findings(run("W-1", design_review_evidence=None)),
        )

    def test_undocumented_pigtail_length_is_flagged(self):
        self.assertIn(
            "declared-pigtail-length-not-documented",
            design_review_findings(run("W-1", declared_pigtail_length_mm=None)),
        )


class TestPhysicalInspectionStage(unittest.TestCase):
    def test_complete_inspection_is_clean(self):
        self.assertEqual(physical_inspection_findings(run()), [])

    def test_missing_inspection_is_flagged(self):
        self.assertEqual(
            physical_inspection_findings(run("W-1", physical_inspection_done=False)),
            ["physical-inspection-not-performed"],
        )

    def test_inspection_without_evidence_is_flagged(self):
        self.assertIn(
            "physical-inspection-without-an-evidence-reference",
            physical_inspection_findings(run("W-1", inspection_evidence="")),
        )

    def test_unrecorded_category_is_flagged(self):
        self.assertIn(
            "inspected-category-not-recorded",
            physical_inspection_findings(run("W-1", inspected_category=None)),
        )

    def test_unrecorded_termination_is_flagged(self):
        self.assertIn(
            "inspected-termination-not-recorded",
            physical_inspection_findings(run("W-1", inspected_termination=None)),
        )

    def test_unrecorded_pigtail_length_is_flagged(self):
        self.assertIn(
            "inspected-pigtail-length-not-recorded",
            physical_inspection_findings(run("W-1", inspected_pigtail_length_mm=None)),
        )


class TestCategoryAgreement(unittest.TestCase):
    def test_matching_categories_are_clean(self):
        self.assertEqual(category_agreement_findings(run()), [])

    def test_mismatched_categories_are_flagged(self):
        self.assertEqual(
            category_agreement_findings(run("W-1", inspected_category="power")),
            ["as-built-category-differs-from-the-documented-category"],
        )

    def test_uninspected_run_yields_no_agreement_finding(self):
        self.assertEqual(
            category_agreement_findings(
                run("W-1", physical_inspection_done=False, inspected_category=None)
            ),
            [],
        )


class TestShieldTreatment(unittest.TestCase):
    def test_signal_pigtail_within_limit_is_clean(self):
        self.assertEqual(shield_treatment_findings(run()), [])

    def test_sensitive_run_needs_a_full_circumference_termination(self):
        self.assertEqual(required_termination("sensitive"), TERMINATION_CIRCUMFERENTIAL)
        self.assertEqual(required_termination("interfering"), TERMINATION_CIRCUMFERENTIAL)

    def test_signal_run_may_use_a_pigtail(self):
        self.assertEqual(required_termination("signal"), TERMINATION_PIGTAIL)
        self.assertEqual(required_termination("power"), TERMINATION_PIGTAIL)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            required_termination("mystery")

    def test_sensitive_run_on_a_pigtail_is_flagged(self):
        findings = shield_treatment_findings(
            sensitive(
                "W-S",
                declared_termination="pigtail",
                inspected_termination="pigtail",
                declared_pigtail_length_mm=10.0,
                inspected_pigtail_length_mm=10.0,
            )
        )
        self.assertIn("category-needs-a-full-circumference-termination", findings)

    def test_untermimated_shield_is_flagged(self):
        findings = shield_treatment_findings(
            run("W-1", declared_termination="none", inspected_termination="none",
                declared_pigtail_length_mm=None, inspected_pigtail_length_mm=None)
        )
        self.assertEqual(findings, ["shielded-run-with-no-shield-termination"])

    def test_pigtail_over_limit_is_flagged(self):
        findings = shield_treatment_findings(
            run("W-1", inspected_pigtail_length_mm=40.0)
        )
        self.assertIn("pigtail-longer-than-its-limit", findings)

    def test_pigtail_exactly_on_limit_is_accepted(self):
        findings = shield_treatment_findings(
            run("W-1", declared_pigtail_length_mm=MAX_PIGTAIL_LENGTH_MM,
                inspected_pigtail_length_mm=MAX_PIGTAIL_LENGTH_MM)
        )
        self.assertEqual(findings, [])

    def test_as_built_termination_change_is_flagged(self):
        findings = shield_treatment_findings(
            run("W-1", inspected_termination="full-circumference",
                inspected_pigtail_length_mm=None)
        )
        self.assertIn("as-built-termination-differs-from-the-documented-one", findings)

    def test_unshielded_run_declaring_a_termination_is_flagged(self):
        findings = shield_treatment_findings(
            run("W-1", shielded=False)
        )
        self.assertEqual(findings, ["unshielded-run-declares-a-shield-termination"])

    def test_unshielded_run_with_no_termination_is_clean(self):
        findings = shield_treatment_findings(
            run("W-1", shielded=False, declared_termination="none",
                inspected_termination="none", declared_pigtail_length_mm=None,
                inspected_pigtail_length_mm=None)
        )
        self.assertEqual(findings, [])


class TestInspectionCoverage(unittest.TestCase):
    def test_required_fractions(self):
        self.assertAlmostEqual(
            required_inspection_fraction("sensitive"), FULL_INSPECTION_FRACTION, places=9
        )
        self.assertAlmostEqual(
            required_inspection_fraction("signal"), SAMPLED_INSPECTION_FRACTION, places=9
        )

    def test_full_coverage_fraction_is_one(self):
        coverage = inspection_coverage([run("W-1"), run("W-2")])
        self.assertAlmostEqual(coverage["signal"]["fraction"], 1.0, places=9)

    def test_partial_coverage_fraction(self):
        runs = [run("W-%d" % i) for i in range(1, 6)]
        runs[1]["physical_inspection_done"] = False
        runs[2]["physical_inspection_done"] = False
        runs[3]["physical_inspection_done"] = False
        runs[4]["physical_inspection_done"] = False
        coverage = inspection_coverage(runs)
        self.assertEqual(coverage["signal"]["inspected"], 1)
        self.assertEqual(coverage["signal"]["total"], 5)
        self.assertAlmostEqual(coverage["signal"]["fraction"], 0.2, places=9)

    def test_sample_exactly_on_the_floor_is_accepted(self):
        runs = [run("W-%d" % i) for i in range(1, 6)]
        for r in runs[1:]:
            r["physical_inspection_done"] = False
            r["inspected_category"] = None
            r["inspected_termination"] = None
            r["inspected_pigtail_length_mm"] = None
        self.assertEqual(coverage_findings(runs), [])

    def test_sample_under_the_floor_is_flagged(self):
        runs = [run("W-%d" % i) for i in range(1, 7)]
        for r in runs[1:]:
            r["physical_inspection_done"] = False
        self.assertEqual(coverage_findings(runs), ["signal-inspection-coverage-below-floor"])

    def test_uninspected_sensitive_run_breaks_full_coverage(self):
        runs = [sensitive("W-S1"), sensitive("W-S2")]
        runs[1]["physical_inspection_done"] = False
        self.assertEqual(
            coverage_findings(runs), ["sensitive-inspection-coverage-below-floor"]
        )

    def test_empty_run_list_raises(self):
        with self.assertRaises(ValueError):
            inspection_coverage([])


class TestAssessRun(unittest.TestCase):
    def test_clean_run_is_compliant(self):
        result = assess_run(run())
        self.assertTrue(result["compliant"])
        self.assertTrue(result["stages_complete"])
        self.assertEqual(result["required_termination"], TERMINATION_PIGTAIL)

    def test_review_only_run_is_incomplete(self):
        result = assess_run(
            run("W-1", physical_inspection_done=False, inspected_category=None,
                inspected_termination=None, inspected_pigtail_length_mm=None)
        )
        self.assertFalse(result["stages_complete"])
        self.assertFalse(result["compliant"])
        self.assertIn("physical-inspection-not-performed", result["findings"])

    def test_inspection_only_run_is_incomplete(self):
        result = assess_run(run("W-1", design_review_done=False))
        self.assertFalse(result["stages_complete"])
        self.assertIn("design-review-not-performed", result["findings"])

    def test_sensitive_run_with_a_proper_termination_is_compliant(self):
        self.assertTrue(assess_run(sensitive())["compliant"])


class TestAssessVerification(unittest.TestCase):
    def test_clean_set_is_compliant(self):
        report = assess_wiring_and_shielding_verification(
            [run("W-1"), sensitive("W-S")]
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["non_compliant_ids"], [])
        self.assertEqual(report["coverage_findings"], [])

    def test_category_mismatch_fails_the_set(self):
        report = assess_wiring_and_shielding_verification(
            [run("W-1"), run("W-2", inspected_category="power")]
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_ids"], ["W-2"])

    def test_coverage_shortfall_fails_the_set_on_its_own(self):
        runs = [sensitive("W-S1"), sensitive("W-S2")]
        runs[1]["physical_inspection_done"] = True
        runs[1]["inspection_evidence"] = "INS-0912 sheet 4"
        report = assess_wiring_and_shielding_verification(runs)
        self.assertTrue(report["compliant"])
        runs[1]["physical_inspection_done"] = False
        runs[1]["inspected_category"] = None
        runs[1]["inspected_termination"] = None
        report = assess_wiring_and_shielding_verification(runs)
        self.assertFalse(report["compliant"])

    def test_duplicate_run_id_raises(self):
        with self.assertRaises(ValueError):
            assess_wiring_and_shielding_verification([run("W-1"), run("W-1")])

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_wiring_and_shielding_verification([])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_wiring_and_shielding_verification(run())


if __name__ == "__main__":
    unittest.main()
