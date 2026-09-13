#!/usr/bin/env python3
"""Gate 3 contract test for the clause 7.5 verification close-out logic."""

import unittest

from e20_rf_power_and_intermodulation_verification_logic import (
    MARGIN_TOLERANCE_DB,
    admissible_methods,
    assess_rf_power_and_intermodulation_verification,
    check_documentation,
    check_gate_closure,
    check_margin,
    check_method_admissibility,
    evaluate_item,
    gate_index,
    normalize_item,
    required_margin_db,
)


def _item(**overrides):
    item = {
        "id": "vp-01",
        "family": "multipactor",
        "method": "campaign",
        "nominal_dbm": 40.0,
        "demonstrated_dbm": 43.0,
        "plan_ref": "RF-VP-001",
        "report_ref": "RF-VR-001",
    }
    item.update(overrides)
    return item


class TestGateOrdering(unittest.TestCase):
    def test_gates_are_ordered(self):
        self.assertLess(gate_index("pdr"), gate_index("cdr"))
        self.assertLess(gate_index("cdr"), gate_index("qr"))
        self.assertLess(gate_index("qr"), gate_index("ar"))

    def test_gate_name_is_case_insensitive(self):
        self.assertEqual(gate_index("QR"), gate_index("qr"))

    def test_unknown_gate_is_rejected(self):
        with self.assertRaises(ValueError):
            gate_index("frr")

    def test_non_string_gate_is_rejected(self):
        with self.assertRaises(ValueError):
            gate_index(2)


class TestMethodTables(unittest.TestCase):
    def test_every_family_has_admissible_methods(self):
        for family in ("rf-power-handling", "multipactor", "corona", "passive-intermodulation"):
            self.assertTrue(admissible_methods(family))

    def test_intermodulation_does_not_admit_analysis(self):
        self.assertNotIn("analysis", admissible_methods("passive-intermodulation"))

    def test_corona_does_not_admit_similarity(self):
        self.assertNotIn("similarity", admissible_methods("corona"))

    def test_unknown_family_is_rejected(self):
        with self.assertRaises(ValueError):
            admissible_methods("radiation")

    def test_inferring_method_carries_the_larger_margin(self):
        self.assertGreater(
            required_margin_db("multipactor", "analysis"),
            required_margin_db("multipactor", "campaign"),
        )

    def test_corona_campaign_margin_value(self):
        self.assertAlmostEqual(required_margin_db("corona", "campaign"), 6.0)

    def test_inadmissible_pairing_has_no_margin(self):
        with self.assertRaises(ValueError):
            required_margin_db("passive-intermodulation", "analysis")

    def test_unknown_method_is_rejected(self):
        with self.assertRaises(ValueError):
            required_margin_db("multipactor", "handwave")


class TestItemNormalization(unittest.TestCase):
    def test_defaults_the_closure_gate_from_the_family(self):
        entry = normalize_item(_item(family="rf-power-handling"))
        self.assertEqual(entry["closure_gate"], "cdr")

    def test_intermodulation_defaults_to_the_qualification_gate(self):
        entry = normalize_item(_item(family="passive-intermodulation", method="campaign"))
        self.assertEqual(entry["closure_gate"], "qr")

    def test_missing_evidence_is_kept_as_none(self):
        entry = normalize_item(_item(demonstrated_dbm=None, report_ref=""))
        self.assertIsNone(entry["demonstrated_dbm"])

    def test_rejects_non_mapping(self):
        with self.assertRaises(ValueError):
            normalize_item(["vp-01"])

    def test_rejects_blank_identifier(self):
        with self.assertRaises(ValueError):
            normalize_item(_item(id="  "))

    def test_rejects_unknown_family(self):
        with self.assertRaises(ValueError):
            normalize_item(_item(family="thermal"))

    def test_rejects_unknown_method(self):
        with self.assertRaises(ValueError):
            normalize_item(_item(method="assume"))

    def test_rejects_non_finite_nominal_level(self):
        with self.assertRaises(ValueError):
            normalize_item(_item(nominal_dbm=float("nan")))

    def test_rejects_unknown_closure_gate(self):
        with self.assertRaises(ValueError):
            normalize_item(_item(closure_gate="lrr"))

    def test_rejects_unknown_design_delta(self):
        with self.assertRaises(ValueError):
            normalize_item(_item(design_delta="cosmetic"))

    def test_rejects_negative_required_margin_override(self):
        with self.assertRaises(ValueError):
            normalize_item(_item(required_margin_db=-1.0))

    def test_rejects_non_string_heritage_reference(self):
        with self.assertRaises(ValueError):
            normalize_item(_item(method="similarity", heritage_reference=17))

    def test_normalization_is_idempotent(self):
        once = normalize_item(_item())
        twice = normalize_item(once)
        self.assertEqual(once, twice)


class TestAdmissibilityFindings(unittest.TestCase):
    def test_admissible_campaign_raises_no_finding(self):
        self.assertEqual(check_method_admissibility(_item()), [])

    def test_analysis_for_intermodulation_is_a_finding(self):
        findings = check_method_admissibility(
            _item(family="passive-intermodulation", method="analysis")
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("not admissible", findings[0])

    def test_similarity_without_heritage_is_a_finding(self):
        findings = check_method_admissibility(
            _item(method="similarity", design_delta="none")
        )
        self.assertTrue(any("heritage" in f for f in findings))

    def test_similarity_without_design_delta_is_a_finding(self):
        findings = check_method_admissibility(
            _item(method="similarity", heritage_reference="HERITAGE-7")
        )
        self.assertTrue(any("design-delta" in f for f in findings))

    def test_major_design_delta_invalidates_similarity(self):
        findings = check_method_admissibility(
            _item(
                method="similarity",
                heritage_reference="HERITAGE-7",
                design_delta="major",
            )
        )
        self.assertTrue(any("beyond minor" in f for f in findings))

    def test_minor_delta_with_heritage_is_accepted(self):
        self.assertEqual(
            check_method_admissibility(
                _item(
                    method="similarity",
                    heritage_reference="HERITAGE-7",
                    design_delta="minor",
                    demonstrated_dbm=46.0,
                )
            ),
            [],
        )

    def test_review_of_design_is_admissible_nowhere_here(self):
        findings = check_method_admissibility(_item(method="review-of-design"))
        self.assertTrue(findings)


class TestMarginCheck(unittest.TestCase):
    def test_campaign_margin_is_met(self):
        result = check_margin(_item())
        self.assertAlmostEqual(result["required_margin_db"], 3.0)
        self.assertAlmostEqual(result["achieved_margin_db"], 3.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["shortfall_db"], 0.0)

    def test_shortfall_is_reported(self):
        result = check_margin(_item(demonstrated_dbm=41.5))
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["shortfall_db"], 1.5)

    def test_analysis_needs_the_larger_margin(self):
        result = check_margin(_item(method="analysis"))
        self.assertAlmostEqual(result["required_margin_db"], 6.0)
        self.assertFalse(result["compliant"])

    def test_no_evidence_is_not_compliant(self):
        result = check_margin(_item(demonstrated_dbm=None, report_ref=""))
        self.assertFalse(result["evidence"])
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["achieved_margin_db"])

    def test_project_override_can_raise_the_requirement(self):
        result = check_margin(_item(required_margin_db=5.0))
        self.assertAlmostEqual(result["required_margin_db"], 5.0)
        self.assertFalse(result["compliant"])

    def test_project_override_cannot_weaken_the_requirement(self):
        result = check_margin(_item(required_margin_db=1.0, demonstrated_dbm=42.0))
        self.assertAlmostEqual(result["required_margin_db"], 3.0)
        self.assertFalse(result["compliant"])

    def test_exactly_met_margin_survives_representation_error(self):
        result = check_margin(_item(nominal_dbm=43.3, demonstrated_dbm=46.3))
        self.assertAlmostEqual(result["achieved_margin_db"], 3.0, places=9)
        self.assertTrue(result["compliant"])

    def test_tolerance_is_tight_enough_to_catch_a_real_shortfall(self):
        result = check_margin(_item(demonstrated_dbm=43.0 - 1000 * MARGIN_TOLERANCE_DB))
        self.assertFalse(result["compliant"])

    def test_margin_cannot_be_judged_for_an_inadmissible_method(self):
        with self.assertRaises(ValueError):
            check_margin(_item(family="passive-intermodulation", method="analysis"))


class TestGateClosure(unittest.TestCase):
    def test_evidence_closes_the_item(self):
        self.assertEqual(check_gate_closure(_item(), "qr")["status"], "closed")

    def test_no_evidence_before_the_gate_is_open(self):
        status = check_gate_closure(_item(demonstrated_dbm=None, report_ref=""), "pdr")
        self.assertEqual(status["status"], "open")

    def test_no_evidence_at_the_gate_is_overdue(self):
        status = check_gate_closure(_item(demonstrated_dbm=None, report_ref=""), "qr")
        self.assertEqual(status["status"], "overdue")

    def test_no_evidence_past_the_gate_is_overdue(self):
        status = check_gate_closure(_item(demonstrated_dbm=None, report_ref=""), "ar")
        self.assertEqual(status["status"], "overdue")

    def test_unknown_current_gate_is_rejected(self):
        with self.assertRaises(ValueError):
            check_gate_closure(_item(), "orr")


class TestDocumentation(unittest.TestCase):
    def test_complete_documentation_raises_no_finding(self):
        self.assertEqual(check_documentation(_item()), [])

    def test_missing_plan_reference_is_a_finding(self):
        findings = check_documentation(_item(plan_ref=""))
        self.assertTrue(any("verification-plan" in f for f in findings))

    def test_evidence_without_a_report_reference_is_a_finding(self):
        findings = check_documentation(_item(report_ref=""))
        self.assertTrue(any("verification-report" in f for f in findings))

    def test_report_is_not_required_before_evidence_exists(self):
        findings = check_documentation(_item(demonstrated_dbm=None, report_ref=""))
        self.assertEqual(findings, [])


class TestItemEvaluation(unittest.TestCase):
    def test_clean_item_is_compliant(self):
        result = evaluate_item(_item(), "qr")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["margin"]["compliant"])

    def test_inadmissible_method_skips_the_margin_judgement(self):
        result = evaluate_item(
            _item(family="passive-intermodulation", method="analysis"), "qr"
        )
        self.assertIsNone(result["margin"])
        self.assertFalse(result["compliant"])

    def test_short_margin_is_reported_as_a_finding(self):
        result = evaluate_item(_item(demonstrated_dbm=41.0), "qr")
        self.assertTrue(any("short of the required" in f for f in result["findings"]))

    def test_overdue_item_is_reported_as_a_finding(self):
        result = evaluate_item(
            _item(demonstrated_dbm=None, report_ref=""), "ar"
        )
        self.assertTrue(any("no evidence" in f for f in result["findings"]))


class TestAssessment(unittest.TestCase):
    def test_all_clean_items_pass_the_gate(self):
        items = [
            _item(),
            _item(
                id="vp-02",
                family="passive-intermodulation",
                method="campaign",
                nominal_dbm=38.0,
                demonstrated_dbm=41.0,
                plan_ref="RF-VP-002",
                report_ref="RF-VR-002",
            ),
        ]
        result = assess_rf_power_and_intermodulation_verification(items, "qr")
        self.assertTrue(result["gate_passable"])
        self.assertAlmostEqual(result["closure_fraction"], 1.0)
        self.assertEqual(result["overdue_count"], 0)

    def test_mixed_set_reports_a_partial_closure_fraction(self):
        items = [
            _item(),
            _item(id="vp-02", demonstrated_dbm=None, report_ref=""),
        ]
        result = assess_rf_power_and_intermodulation_verification(items, "qr")
        self.assertFalse(result["gate_passable"])
        self.assertAlmostEqual(result["closure_fraction"], 0.5)
        self.assertEqual(result["overdue_count"], 1)

    def test_findings_are_collected_across_items(self):
        items = [
            _item(plan_ref=""),
            _item(id="vp-02", family="corona", method="similarity"),
        ]
        result = assess_rf_power_and_intermodulation_verification(items, "cdr")
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_empty_item_set_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_rf_power_and_intermodulation_verification([], "qr")

    def test_non_list_item_set_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_rf_power_and_intermodulation_verification(_item(), "qr")

    def test_duplicate_item_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_rf_power_and_intermodulation_verification([_item(), _item()], "qr")

    def test_unknown_current_gate_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_rf_power_and_intermodulation_verification([_item()], "srr")


if __name__ == "__main__":
    unittest.main()
