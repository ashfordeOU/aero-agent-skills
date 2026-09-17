"""Contract test for the ECSS-Q-ST-60C clause 5.2.3.1 Class 2 evaluation-need leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q60_class_2_evaluation_general_requirements.py
"""

import unittest

from q60_class_2_evaluation_general_requirements_logic import (
    COVERAGE_TOLERANCE,
    DECISIONS,
    EVIDENCE_SOURCES,
    EVIDENCE_VALIDITY_MONTHS,
    FULL_PROGRAMME,
    LINE_TIED_ELEMENTS,
    TAILORED_PROGRAMME_THRESHOLD,
    TARGET_ASSURANCE_CLASS,
    assess_class_2_evaluation_need,
    assess_evidence,
    carries_to_target_class,
    evaluation_coverage,
    evidence_admissible,
    normalize_context,
    normalize_covered_elements,
    novelty_forces_full_programme,
    residual_programme,
    source_profile,
    strongest_admissible,
)


def catalogue_context(**overrides):
    """A plain catalogue part whose tailoring the customer has agreed."""
    context = {
        "technology_maturity": "catalogue-standard-product",
        "tailoring_agreed_with_customer": True,
    }
    context.update(overrides)
    return context


def good_evidence(**overrides):
    """A prior record that satisfies every admissibility rule."""
    item = {
        "kind": "qualification-to-approved-space-specification",
        "same_manufacturing_line": True,
        "same_part_variant": True,
        "process_change_notified": False,
        "evidence_age_months": 18.0,
        "mission_demand_ratio": 1.3,
        "covered_elements": [
            "electrical-characterisation-over-temperature",
            "endurance-and-environmental-testing",
        ],
    }
    item.update(overrides)
    return item


class SourceProfileTests(unittest.TestCase):
    def test_an_approved_space_specification_covers_a_whole_programme(self):
        profile = source_profile("qualification-to-approved-space-specification")
        self.assertAlmostEqual(profile["coverage_ceiling"], 1.0, places=9)
        self.assertEqual(profile["earned_at_class"], 1)

    def test_a_datasheet_declaration_covers_nothing(self):
        profile = source_profile("datasheet-declaration-only")
        self.assertAlmostEqual(profile["coverage_ceiling"], 0.0, places=9)

    def test_the_coverage_scale_runs_from_nothing_to_a_whole_programme(self):
        ceilings = [entry["coverage"] for entry in EVIDENCE_SOURCES.values()]
        self.assertAlmostEqual(min(ceilings), 0.0, places=9)
        self.assertAlmostEqual(max(ceilings), 1.0, places=9)

    def test_unknown_evidence_kind_rejected(self):
        with self.assertRaises(ValueError):
            source_profile("the-supplier-said-it-was-fine")


class DirectionTests(unittest.TestCase):
    def test_a_stricter_class_record_carries_down(self):
        self.assertTrue(carries_to_target_class("class-1-evaluation-on-the-same-part"))

    def test_a_same_class_record_carries(self):
        self.assertTrue(
            carries_to_target_class(
                "customer-accepted-class-2-evaluation-on-the-same-part"
            )
        )

    def test_a_looser_class_record_never_carries_up(self):
        self.assertFalse(carries_to_target_class("class-3-evaluation-on-the-same-part"))
        self.assertFalse(
            carries_to_target_class("manufacturer-commercial-qualification-only")
        )

    def test_the_target_class_is_the_one_this_leaf_decides_for(self):
        self.assertEqual(TARGET_ASSURANCE_CLASS, 2)

    def test_direction_is_read_before_anything_else_about_the_record(self):
        admissible, reasons = evidence_admissible(
            good_evidence(kind="class-3-evaluation-on-the-same-part")
        )
        self.assertFalse(admissible)
        self.assertIn("evidence-earned-below-the-target-assurance-class", reasons)


class AdmissibilityTests(unittest.TestCase):
    def test_a_complete_record_is_admissible(self):
        admissible, reasons = evidence_admissible(good_evidence())
        self.assertTrue(admissible)
        self.assertEqual(reasons, [])

    def test_another_manufacturing_line_breaks_admissibility(self):
        admissible, reasons = evidence_admissible(
            good_evidence(same_manufacturing_line=False)
        )
        self.assertFalse(admissible)
        self.assertIn("evidence-from-another-manufacturing-line", reasons)

    def test_another_part_variant_breaks_admissibility(self):
        admissible, reasons = evidence_admissible(good_evidence(same_part_variant=False))
        self.assertFalse(admissible)
        self.assertIn("evidence-from-another-part-variant", reasons)

    def test_a_notified_process_change_supersedes_the_record(self):
        admissible, reasons = evidence_admissible(
            good_evidence(process_change_notified=True)
        )
        self.assertFalse(admissible)
        self.assertIn("evidence-superseded-by-process-change", reasons)

    def test_a_record_at_the_validity_limit_still_stands(self):
        admissible, reasons = evidence_admissible(
            good_evidence(evidence_age_months=float(EVIDENCE_VALIDITY_MONTHS))
        )
        self.assertTrue(admissible)
        self.assertEqual(reasons, [])

    def test_a_record_past_the_validity_limit_falls(self):
        admissible, reasons = evidence_admissible(
            good_evidence(evidence_age_months=float(EVIDENCE_VALIDITY_MONTHS) + 1.0)
        )
        self.assertFalse(admissible)
        self.assertIn("evidence-out-of-validity-window", reasons)

    def test_an_equally_demanding_mission_still_carries(self):
        ratio = 1.0
        self.assertAlmostEqual(ratio, 1.0, places=9)
        admissible, reasons = evidence_admissible(
            good_evidence(mission_demand_ratio=ratio)
        )
        self.assertTrue(admissible)
        self.assertEqual(reasons, [])

    def test_a_milder_mission_profile_breaks_admissibility(self):
        admissible, reasons = evidence_admissible(good_evidence(mission_demand_ratio=0.6))
        self.assertFalse(admissible)
        self.assertIn("evidence-mission-profile-less-demanding", reasons)

    def test_every_broken_rule_is_named_at_once(self):
        admissible, reasons = evidence_admissible(
            good_evidence(same_manufacturing_line=False, same_part_variant=False)
        )
        self.assertFalse(admissible)
        self.assertEqual(len(reasons), 2)

    def test_negative_record_age_rejected(self):
        with self.assertRaises(ValueError):
            evidence_admissible(good_evidence(evidence_age_months=-1.0))

    def test_non_positive_mission_demand_ratio_rejected(self):
        with self.assertRaises(ValueError):
            evidence_admissible(good_evidence(mission_demand_ratio=0.0))

    def test_non_boolean_line_flag_rejected(self):
        with self.assertRaises(ValueError):
            evidence_admissible(good_evidence(same_manufacturing_line="yes"))

    def test_non_mapping_evidence_rejected(self):
        with self.assertRaises(ValueError):
            evidence_admissible(["same line"])


class CoveredElementTests(unittest.TestCase):
    def test_declared_elements_are_kept_in_order_and_deduplicated(self):
        covered = normalize_covered_elements(
            [
                "constructional-analysis",
                "manufacturer-assessment",
                "constructional-analysis",
            ]
        )
        self.assertEqual(covered, ("constructional-analysis", "manufacturer-assessment"))

    def test_an_absent_declaration_covers_nothing(self):
        self.assertEqual(normalize_covered_elements(None), ())

    def test_an_unknown_programme_element_rejected(self):
        with self.assertRaises(ValueError):
            normalize_covered_elements(["a-quick-look-at-the-datasheet"])

    def test_a_bare_string_is_not_a_element_list(self):
        with self.assertRaises(ValueError):
            normalize_covered_elements("constructional-analysis")


class AssessEvidenceTests(unittest.TestCase):
    def test_an_admissible_record_earns_its_whole_ceiling(self):
        record = assess_evidence(good_evidence())
        self.assertAlmostEqual(record["coverage"], record["coverage_ceiling"], places=9)
        self.assertEqual(record["reasons"], [])

    def test_a_broken_record_earns_nothing_and_names_why(self):
        record = assess_evidence(good_evidence(same_part_variant=False))
        self.assertAlmostEqual(record["coverage"], 0.0, places=9)
        self.assertIn("evidence-from-another-part-variant", record["reasons"])

    def test_unknown_kind_rejected_before_the_admissibility_rules(self):
        with self.assertRaises(ValueError):
            assess_evidence(good_evidence(kind="word-of-mouth"))


class CoverageTests(unittest.TestCase):
    def test_coverage_is_the_strongest_admissible_record(self):
        records = [
            assess_evidence(good_evidence(kind="class-3-evaluation-on-the-same-part")),
            assess_evidence(
                good_evidence(kind="space-agency-qualification-of-the-same-part")
            ),
        ]
        self.assertAlmostEqual(
            evaluation_coverage(records),
            EVIDENCE_SOURCES["space-agency-qualification-of-the-same-part"]["coverage"],
            places=9,
        )

    def test_weak_records_never_add_up_to_a_strong_one(self):
        weak = [
            assess_evidence(
                good_evidence(kind="space-agency-qualification-of-the-same-part")
            )
            for _ in range(4)
        ]
        self.assertAlmostEqual(
            evaluation_coverage(weak),
            EVIDENCE_SOURCES["space-agency-qualification-of-the-same-part"]["coverage"],
            places=9,
        )

    def test_no_records_give_no_coverage(self):
        self.assertAlmostEqual(evaluation_coverage([]), 0.0, places=9)
        self.assertIsNone(strongest_admissible([]))

    def test_an_inadmissible_record_is_never_the_strongest(self):
        records = [assess_evidence(good_evidence(process_change_notified=True))]
        self.assertIsNone(strongest_admissible(records))

    def test_coverage_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            evaluation_coverage({"coverage": 1.0})


class ContextTests(unittest.TestCase):
    def test_unknown_maturity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_context(catalogue_context(technology_maturity="probably-fine"))

    def test_missing_tailoring_agreement_flag_rejected(self):
        with self.assertRaises(ValueError):
            normalize_context({"technology_maturity": "catalogue-standard-product"})

    def test_non_mapping_context_rejected(self):
        with self.assertRaises(ValueError):
            normalize_context("a capacitor")

    def test_new_technology_forces_the_full_programme(self):
        self.assertTrue(
            novelty_forces_full_programme(
                catalogue_context(
                    technology_maturity="new-technology-not-previously-flown"
                )
            )
        )

    def test_a_plain_catalogue_part_forces_nothing(self):
        self.assertFalse(novelty_forces_full_programme(catalogue_context()))


class ResidualProgrammeTests(unittest.TestCase):
    def test_a_waiver_leaves_no_programme(self):
        self.assertEqual(residual_programme("class-2-evaluation-not-required"), ())

    def test_a_full_decision_owes_everything(self):
        self.assertEqual(
            residual_programme("class-2-full-evaluation-required"), FULL_PROGRAMME
        )

    def test_a_tailored_programme_still_owes_the_line_tied_elements(self):
        record = assess_evidence(
            good_evidence(
                kind="space-agency-qualification-of-the-same-part",
                covered_elements=list(FULL_PROGRAMME),
            )
        )
        residual = residual_programme("class-2-tailored-evaluation-required", record)
        self.assertEqual(residual, LINE_TIED_ELEMENTS)

    def test_an_element_the_record_never_covered_stays_outstanding(self):
        record = assess_evidence(good_evidence(covered_elements=[]))
        residual = residual_programme("class-2-tailored-evaluation-required", record)
        self.assertEqual(residual, FULL_PROGRAMME)

    def test_every_line_tied_element_is_in_the_full_programme(self):
        for element in LINE_TIED_ELEMENTS:
            self.assertIn(element, FULL_PROGRAMME)

    def test_unknown_decision_rejected(self):
        with self.assertRaises(ValueError):
            residual_programme("looks-ok-to-me")


class EvaluationNeedTests(unittest.TestCase):
    def test_a_whole_space_qualification_removes_the_evaluation(self):
        report = assess_class_2_evaluation_need(
            "dev-01", catalogue_context(), [good_evidence()]
        )
        self.assertEqual(report["decision"], "class-2-evaluation-not-required")
        self.assertFalse(report["evaluation_required"])
        self.assertEqual(report["residual_programme"], [])
        self.assertEqual(report["findings"], [])

    def test_an_agency_qualification_buys_a_tailored_programme_only(self):
        report = assess_class_2_evaluation_need(
            "dev-01",
            catalogue_context(),
            [
                good_evidence(
                    kind="space-agency-qualification-of-the-same-part",
                    covered_elements=list(FULL_PROGRAMME),
                )
            ],
        )
        self.assertEqual(report["decision"], "class-2-tailored-evaluation-required")
        self.assertEqual(report["residual_programme"], list(LINE_TIED_ELEMENTS))

    def test_tailoring_the_customer_never_agreed_leaves_the_full_programme(self):
        report = assess_class_2_evaluation_need(
            "dev-01",
            catalogue_context(tailoring_agreed_with_customer=False),
            [good_evidence(kind="space-agency-qualification-of-the-same-part")],
        )
        self.assertEqual(report["decision"], "class-2-full-evaluation-required")
        self.assertIn(
            "tailoring-not-agreed-with-customer",
            [f["finding"] for f in report["findings"]],
        )

    def test_coverage_on_the_tailored_bound_is_absorbed_not_refused(self):
        self.assertAlmostEqual(
            EVIDENCE_SOURCES["space-agency-qualification-of-the-same-part"]["coverage"],
            0.7,
            places=9,
        )
        self.assertGreater(
            EVIDENCE_SOURCES["space-agency-qualification-of-the-same-part"]["coverage"],
            TAILORED_PROGRAMME_THRESHOLD,
        )

    def test_a_class_3_record_never_lifts_a_class_2_part(self):
        report = assess_class_2_evaluation_need(
            "dev-01",
            catalogue_context(),
            [good_evidence(kind="class-3-evaluation-on-the-same-part")],
        )
        self.assertEqual(report["decision"], "class-2-full-evaluation-required")
        self.assertIn(
            "lower-class-evidence-does-not-carry-upward",
            [f["finding"] for f in report["findings"]],
        )

    def test_nothing_on_offer_gives_the_full_programme(self):
        report = assess_class_2_evaluation_need("dev-01", catalogue_context(), [])
        self.assertEqual(report["decision"], "class-2-full-evaluation-required")
        self.assertEqual(report["residual_programme"], list(FULL_PROGRAMME))
        self.assertAlmostEqual(report["evaluation_coverage"], 0.0, places=9)

    def test_novelty_beats_a_perfect_qualification_record(self):
        report = assess_class_2_evaluation_need(
            "dev-01",
            catalogue_context(
                technology_maturity="new-technology-not-previously-flown"
            ),
            [good_evidence()],
        )
        self.assertEqual(report["decision"], "class-2-full-evaluation-required")
        self.assertIn(
            "new-technology-forces-full-programme",
            [f["finding"] for f in report["findings"]],
        )

    def test_a_broken_record_is_reported_and_earns_nothing(self):
        report = assess_class_2_evaluation_need(
            "dev-01",
            catalogue_context(),
            [good_evidence(process_change_notified=True)],
        )
        findings = [f["finding"] for f in report["findings"]]
        self.assertIn("prior-evidence-not-admissible", findings)
        self.assertIn("no-admissible-prior-evidence", findings)
        self.assertEqual(report["decision"], "class-2-full-evaluation-required")

    def test_stacked_partial_arguments_are_reported_as_not_additive(self):
        report = assess_class_2_evaluation_need(
            "dev-01",
            catalogue_context(),
            [
                good_evidence(kind="space-agency-qualification-of-the-same-part"),
                good_evidence(
                    kind="customer-accepted-class-2-evaluation-on-the-same-part"
                ),
            ],
        )
        self.assertIn(
            "partial-evidence-is-not-additive",
            [f["finding"] for f in report["findings"]],
        )

    def test_every_decision_name_is_one_the_module_publishes(self):
        seen = set()
        seen.add(
            assess_class_2_evaluation_need(
                "p", catalogue_context(), [good_evidence()]
            )["decision"]
        )
        seen.add(assess_class_2_evaluation_need("p", catalogue_context(), [])["decision"])
        seen.add(
            assess_class_2_evaluation_need(
                "p",
                catalogue_context(),
                [good_evidence(kind="space-agency-qualification-of-the-same-part")],
            )["decision"]
        )
        self.assertEqual(seen, set(DECISIONS))

    def test_empty_part_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_evaluation_need("   ", catalogue_context(), [])

    def test_non_sequence_evidence_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_evaluation_need("dev-01", catalogue_context(), {"kind": "x"})

    def test_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
