"""Contract test for the ECSS-Q-ST-60C clause 4.2.3.1 evaluation-need leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q60_class_1_evaluation_general_requirements.py
"""

import unittest

from q60_class_1_evaluation_general_requirements_logic import (
    CONFIDENCE_TOLERANCE,
    DECISIONS,
    EVIDENCE_CREDIT,
    EVIDENCE_VALIDITY_MONTHS,
    FULL_PROGRAMME,
    LINE_SPECIFIC_ELEMENTS,
    PROGRAMME_SPECIFIC_FAMILIES,
    REDUCED_PROGRAMME_THRESHOLD,
    assess_evaluation_need,
    assess_evidence,
    evidence_credit,
    evidence_transferable,
    normalize_part,
    novelty_forces_full_programme,
    programme_for,
    qualification_confidence,
)


def catalogue_part(**overrides):
    """A plain catalogue part with nothing novel about it."""
    part = {
        "technology_maturity": "catalogue-standard-product",
        "part_family": "monolithic-integrated-circuit",
    }
    part.update(overrides)
    return part


def good_evidence(**overrides):
    """A prior-evidence item that satisfies every transfer rule."""
    item = {
        "kind": "qualification-to-approved-space-specification",
        "same_manufacturing_line": True,
        "same_part_variant": True,
        "process_change_notified": False,
        "evidence_age_months": 12.0,
        "environment_severity_ratio": 1.4,
    }
    item.update(overrides)
    return item


class EvidenceCreditTests(unittest.TestCase):
    def test_an_approved_space_specification_could_stand_alone(self):
        self.assertAlmostEqual(
            evidence_credit("qualification-to-approved-space-specification"),
            1.0,
            places=9,
        )

    def test_a_datasheet_declaration_is_worth_nothing(self):
        self.assertAlmostEqual(evidence_credit("datasheet-declaration-only"), 0.0, places=9)

    def test_the_credit_scale_runs_from_nothing_to_a_full_qualification(self):
        self.assertAlmostEqual(min(EVIDENCE_CREDIT.values()), 0.0, places=9)
        self.assertAlmostEqual(max(EVIDENCE_CREDIT.values()), 1.0, places=9)

    def test_a_commercial_qualification_cannot_reach_a_reduced_programme(self):
        self.assertLess(
            evidence_credit("manufacturer-commercial-qualification-only"),
            REDUCED_PROGRAMME_THRESHOLD,
        )

    def test_unknown_evidence_kind_rejected(self):
        with self.assertRaises(ValueError):
            evidence_credit("the-supplier-said-it-was-fine")


class EvidenceTransferTests(unittest.TestCase):
    def test_a_complete_item_transfers(self):
        transferable, reasons = evidence_transferable(good_evidence())
        self.assertTrue(transferable)
        self.assertEqual(reasons, [])

    def test_another_manufacturing_line_breaks_the_transfer(self):
        transferable, reasons = evidence_transferable(
            good_evidence(same_manufacturing_line=False)
        )
        self.assertFalse(transferable)
        self.assertIn("evidence-from-another-manufacturing-line", reasons)

    def test_a_notified_process_change_supersedes_the_item(self):
        transferable, reasons = evidence_transferable(
            good_evidence(process_change_notified=True)
        )
        self.assertFalse(transferable)
        self.assertIn("evidence-superseded-by-process-change", reasons)

    def test_evidence_at_the_validity_limit_still_transfers(self):
        transferable, reasons = evidence_transferable(
            good_evidence(evidence_age_months=float(EVIDENCE_VALIDITY_MONTHS))
        )
        self.assertTrue(transferable)
        self.assertEqual(reasons, [])

    def test_evidence_past_the_validity_limit_falls(self):
        transferable, reasons = evidence_transferable(
            good_evidence(evidence_age_months=float(EVIDENCE_VALIDITY_MONTHS) + 1.0)
        )
        self.assertFalse(transferable)
        self.assertIn("evidence-out-of-validity", reasons)

    def test_an_equally_severe_environment_still_transfers(self):
        ratio = 1.0
        self.assertAlmostEqual(ratio, 1.0, places=9)
        transferable, reasons = evidence_transferable(
            good_evidence(environment_severity_ratio=ratio)
        )
        self.assertTrue(transferable)
        self.assertEqual(reasons, [])

    def test_a_milder_environment_breaks_the_transfer(self):
        transferable, reasons = evidence_transferable(
            good_evidence(environment_severity_ratio=0.5)
        )
        self.assertFalse(transferable)
        self.assertIn("evidence-environment-less-severe", reasons)

    def test_every_broken_rule_is_named_at_once(self):
        transferable, reasons = evidence_transferable(
            good_evidence(same_manufacturing_line=False, same_part_variant=False)
        )
        self.assertFalse(transferable)
        self.assertEqual(len(reasons), 2)

    def test_negative_evidence_age_rejected(self):
        with self.assertRaises(ValueError):
            evidence_transferable(good_evidence(evidence_age_months=-1.0))

    def test_non_positive_severity_ratio_rejected(self):
        with self.assertRaises(ValueError):
            evidence_transferable(good_evidence(environment_severity_ratio=0.0))

    def test_non_boolean_variant_flag_rejected(self):
        with self.assertRaises(ValueError):
            evidence_transferable(good_evidence(same_part_variant="yes"))

    def test_non_mapping_evidence_rejected(self):
        with self.assertRaises(ValueError):
            evidence_transferable(["same line"])


class AssessEvidenceTests(unittest.TestCase):
    def test_a_transferring_item_earns_its_whole_ceiling(self):
        record = assess_evidence(good_evidence())
        self.assertAlmostEqual(record["credit"], record["credit_ceiling"], places=9)
        self.assertEqual(record["reasons"], [])

    def test_a_broken_item_earns_nothing_and_names_why(self):
        record = assess_evidence(good_evidence(same_part_variant=False))
        self.assertAlmostEqual(record["credit"], 0.0, places=9)
        self.assertIn("evidence-from-another-part-variant", record["reasons"])

    def test_unknown_kind_rejected_before_the_transfer_rules(self):
        with self.assertRaises(ValueError):
            assess_evidence(good_evidence(kind="word-of-mouth"))


class ConfidenceTests(unittest.TestCase):
    def test_confidence_is_the_strongest_admissible_claim(self):
        records = [
            assess_evidence(good_evidence(kind="flight-heritage-in-comparable-environment")),
            assess_evidence(good_evidence(kind="qualification-by-another-space-agency")),
        ]
        self.assertAlmostEqual(
            qualification_confidence(records),
            EVIDENCE_CREDIT["qualification-by-another-space-agency"],
            places=9,
        )

    def test_weak_claims_never_add_up_to_a_strong_one(self):
        weak = [
            assess_evidence(good_evidence(kind="flight-heritage-in-comparable-environment"))
            for _ in range(4)
        ]
        self.assertAlmostEqual(
            qualification_confidence(weak),
            EVIDENCE_CREDIT["flight-heritage-in-comparable-environment"],
            places=9,
        )

    def test_no_evidence_gives_no_confidence(self):
        self.assertAlmostEqual(qualification_confidence([]), 0.0, places=9)

    def test_confidence_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            qualification_confidence({"credit": 1.0})


class PartDescriptionTests(unittest.TestCase):
    def test_unknown_maturity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_part(catalogue_part(technology_maturity="probably-fine"))

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_part(catalogue_part(part_family="widget"))

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            normalize_part("a capacitor")

    def test_new_technology_forces_the_full_programme(self):
        self.assertTrue(
            novelty_forces_full_programme(
                catalogue_part(technology_maturity="new-technology-not-previously-flown")
            )
        )

    def test_a_programme_specific_family_forces_the_full_programme(self):
        for family in PROGRAMME_SPECIFIC_FAMILIES:
            self.assertTrue(novelty_forces_full_programme(catalogue_part(part_family=family)))

    def test_a_plain_catalogue_part_forces_nothing(self):
        self.assertFalse(novelty_forces_full_programme(catalogue_part()))


class ProgrammeTests(unittest.TestCase):
    def test_a_waiver_leaves_no_programme(self):
        self.assertEqual(programme_for("class-1-evaluation-not-required"), ())

    def test_a_reduced_programme_still_owes_the_line_specific_elements(self):
        self.assertEqual(programme_for("class-1-reduced-evaluation-required"), LINE_SPECIFIC_ELEMENTS)

    def test_every_line_specific_element_is_in_the_full_programme(self):
        for element in LINE_SPECIFIC_ELEMENTS:
            self.assertIn(element, FULL_PROGRAMME)

    def test_unknown_decision_rejected(self):
        with self.assertRaises(ValueError):
            programme_for("looks-ok-to-me")


class EvaluationNeedTests(unittest.TestCase):
    def test_a_full_space_qualification_removes_the_evaluation(self):
        report = assess_evaluation_need("dev-01", catalogue_part(), [good_evidence()])
        self.assertEqual(report["decision"], "class-1-evaluation-not-required")
        self.assertFalse(report["evaluation_required"])
        self.assertEqual(report["required_programme"], [])
        self.assertEqual(report["findings"], [])

    def test_an_agency_qualification_buys_a_reduced_programme_only(self):
        report = assess_evaluation_need(
            "dev-01",
            catalogue_part(),
            [good_evidence(kind="qualification-by-another-space-agency")],
        )
        self.assertEqual(report["decision"], "class-1-reduced-evaluation-required")
        self.assertEqual(report["required_programme"], list(LINE_SPECIFIC_ELEMENTS))

    def test_confidence_above_the_reduced_threshold_reduces_the_programme(self):
        confidence = EVIDENCE_CREDIT["evaluation-on-same-part-from-same-line"]
        self.assertGreaterEqual(confidence, REDUCED_PROGRAMME_THRESHOLD)
        report = assess_evaluation_need(
            "dev-01",
            catalogue_part(),
            [good_evidence(kind="evaluation-on-same-part-from-same-line")],
        )
        self.assertEqual(report["decision"], "class-1-reduced-evaluation-required")

    def test_nothing_on_offer_gives_the_full_programme(self):
        report = assess_evaluation_need("dev-01", catalogue_part(), [])
        self.assertEqual(report["decision"], "class-1-full-evaluation-required")
        self.assertEqual(report["required_programme"], list(FULL_PROGRAMME))
        self.assertAlmostEqual(report["qualification_confidence"], 0.0, places=9)

    def test_novelty_beats_a_perfect_qualification_record(self):
        report = assess_evaluation_need(
            "dev-01",
            catalogue_part(technology_maturity="new-technology-not-previously-flown"),
            [good_evidence()],
        )
        self.assertEqual(report["decision"], "class-1-full-evaluation-required")
        self.assertIn(
            "novelty-forces-full-programme",
            [f["finding"] for f in report["findings"]],
        )

    def test_a_broken_record_is_reported_and_earns_nothing(self):
        report = assess_evaluation_need(
            "dev-01",
            catalogue_part(),
            [good_evidence(process_change_notified=True)],
        )
        findings = [f["finding"] for f in report["findings"]]
        self.assertIn("prior-evidence-does-not-transfer", findings)
        self.assertIn("no-admissible-prior-evidence", findings)
        self.assertEqual(report["decision"], "class-1-full-evaluation-required")

    def test_stacked_partial_arguments_are_reported_as_not_additive(self):
        report = assess_evaluation_need(
            "dev-01",
            catalogue_part(),
            [
                good_evidence(kind="flight-heritage-in-comparable-environment"),
                good_evidence(kind="manufacturer-commercial-qualification-only"),
                good_evidence(kind="evaluation-on-same-part-from-same-line"),
            ],
        )
        self.assertIn(
            "partial-evidence-is-not-additive",
            [f["finding"] for f in report["findings"]],
        )

    def test_every_decision_name_is_one_the_module_publishes(self):
        seen = set()
        seen.add(assess_evaluation_need("p", catalogue_part(), [good_evidence()])["decision"])
        seen.add(assess_evaluation_need("p", catalogue_part(), [])["decision"])
        seen.add(
            assess_evaluation_need(
                "p",
                catalogue_part(),
                [good_evidence(kind="qualification-by-another-space-agency")],
            )["decision"]
        )
        self.assertEqual(seen, set(DECISIONS))

    def test_empty_part_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_need("   ", catalogue_part(), [])

    def test_non_sequence_evidence_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_need("dev-01", catalogue_part(), {"kind": "x"})

    def test_tolerance_is_small_enough_to_separate_the_thresholds(self):
        self.assertLess(CONFIDENCE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
