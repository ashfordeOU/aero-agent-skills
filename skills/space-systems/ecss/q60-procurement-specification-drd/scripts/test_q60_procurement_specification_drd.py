"""Contract tests for the Annex C part purchasing specification logic."""

import unittest

from q60_procurement_specification_drd_logic import (
    COVERAGE_TOLERANCE,
    HEADER_FIELDS,
    LOT_ACCEPTANCE_FIELDS,
    MANDATED_SCREENING_FAMILIES,
    REQUIRED_SECTIONS,
    SCREENING_STEP_FIELDS,
    assess_procurement_specification_drd,
    lot_acceptance_findings,
    probability_of_acceptance,
    screening_family_coverage,
    screening_sequence_findings,
    screening_step_completeness,
    section_coverage,
    validate_specification_header,
)


def header(**overrides):
    """Return one controlled specification header with optional overrides."""
    base = {
        "specification_id": "PS-4410",
        "issue": "B",
        "part_type": "voltage-regulator",
        "issue_date": "2026-03-11",
        "approving_authority": "customer product assurance",
    }
    base.update(overrides)
    return base


def sections(**overrides):
    """Return a complete set of required content sections."""
    base = {name: "text for %s" % name for name in REQUIRED_SECTIONS}
    base.update(overrides)
    return base


def step(family, sequence, **overrides):
    """Return one executable screening step with optional overrides."""
    base = {
        "step_id": "S%02d" % sequence,
        "sequence": sequence,
        "family": family,
        "test_name": "%s screen" % family,
        "condition": "as stated in the flow",
        "reject_criterion": "any deviation outside the stated limit",
    }
    base.update(overrides)
    return base


def full_flow():
    """Return a screening flow covering every mandated family once."""
    return [
        step(family, position)
        for position, family in enumerate(MANDATED_SCREENING_FAMILIES, start=1)
    ]


def plan(**overrides):
    """Return one discriminating lot acceptance plan with optional overrides."""
    base = {
        "test_name": "lot acceptance electrical",
        "lot_size": 100,
        "sample_size": 20,
        "accept_number": 0,
    }
    base.update(overrides)
    return base


class HeaderTests(unittest.TestCase):
    def test_complete_header_validates(self):
        self.assertEqual(
            validate_specification_header(header())["specification_id"], "PS-4410"
        )

    def test_values_are_stripped(self):
        self.assertEqual(validate_specification_header(header(issue=" B "))["issue"], "B")

    def test_blank_approving_authority_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification_header(header(approving_authority="  "))

    def test_every_named_header_field_is_required(self):
        for field in HEADER_FIELDS:
            incomplete = header()
            del incomplete[field]
            with self.assertRaises(ValueError):
                validate_specification_header(incomplete)

    def test_non_mapping_header_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification_header("PS-4410")


class SectionCoverageTests(unittest.TestCase):
    def test_complete_sections_score_one(self):
        absent, coverage = section_coverage(sections())
        self.assertEqual(absent, ())
        self.assertAlmostEqual(coverage, 1.0, places=9)

    def test_coverage_is_weighted_not_counted(self):
        light = sections()
        del light["packaging-and-handling"]
        heavy = sections()
        del heavy["lot-acceptance-testing"]
        _, light_coverage = section_coverage(light)
        _, heavy_coverage = section_coverage(heavy)
        self.assertGreater(light_coverage, heavy_coverage)

    def test_absent_section_is_named(self):
        incomplete = sections()
        del incomplete["screening-sequence"]
        absent, _ = section_coverage(incomplete)
        self.assertEqual(absent, ("screening-sequence",))

    def test_blank_section_counts_as_absent(self):
        absent, _ = section_coverage(sections(**{"marking-and-traceability": "   "}))
        self.assertIn("marking-and-traceability", absent)

    def test_weighted_value_matches_the_table(self):
        incomplete = sections()
        del incomplete["applicable-documents"]
        _, coverage = section_coverage(incomplete)
        total = sum(REQUIRED_SECTIONS.values())
        expected = (total - REQUIRED_SECTIONS["applicable-documents"]) / total
        self.assertAlmostEqual(coverage, expected, places=9)

    def test_non_mapping_sections_rejected(self):
        with self.assertRaises(ValueError):
            section_coverage(["identification"])


class ScreeningStepTests(unittest.TestCase):
    def test_complete_step_scores_one(self):
        missing, fraction = screening_step_completeness(step("burn-in", 4))
        self.assertEqual(missing, ())
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_step_without_a_reject_criterion_is_incomplete(self):
        broken = step("burn-in", 4)
        del broken["reject_criterion"]
        missing, fraction = screening_step_completeness(broken)
        self.assertIn("reject_criterion", missing)
        self.assertAlmostEqual(
            fraction,
            (len(SCREENING_STEP_FIELDS) - 1) / len(SCREENING_STEP_FIELDS),
            places=9,
        )

    def test_blank_condition_counts_as_missing(self):
        missing, _ = screening_step_completeness(step("burn-in", 4, condition="  "))
        self.assertIn("condition", missing)

    def test_non_mapping_step_rejected(self):
        with self.assertRaises(ValueError):
            screening_step_completeness("S04")

    def test_clean_flow_raises_no_sequence_finding(self):
        self.assertEqual(screening_sequence_findings(full_flow()), [])

    def test_repeated_sequence_position_is_reported(self):
        flow = full_flow()
        flow.append(step("electrical-measurement", 2, step_id="S99"))
        dispositions = [
            entry["disposition"] for entry in screening_sequence_findings(flow)
        ]
        self.assertIn("sequence-position-repeated", dispositions)

    def test_incomplete_step_is_reported_before_its_position_is_read(self):
        flow = full_flow()
        broken = step("burn-in", 4, step_id="S90")
        del broken["test_name"]
        flow.append(broken)
        dispositions = [
            entry["disposition"] for entry in screening_sequence_findings(flow)
        ]
        self.assertIn("step-incomplete", dispositions)
        self.assertNotIn("sequence-position-repeated", dispositions)

    def test_non_positive_sequence_rejected(self):
        broken = step("burn-in", 4)
        broken["sequence"] = 0
        with self.assertRaises(ValueError):
            screening_sequence_findings([broken])

    def test_empty_flow_rejected(self):
        with self.assertRaises(ValueError):
            screening_sequence_findings([])


class ScreeningFamilyTests(unittest.TestCase):
    def test_full_flow_covers_every_family(self):
        absent, coverage = screening_family_coverage(full_flow())
        self.assertEqual(absent, ())
        self.assertAlmostEqual(coverage, 1.0, places=9)

    def test_missing_family_is_named(self):
        flow = [entry for entry in full_flow() if entry["family"] != "burn-in"]
        absent, coverage = screening_family_coverage(flow)
        self.assertEqual(absent, ("burn-in",))
        self.assertAlmostEqual(
            coverage,
            (len(MANDATED_SCREENING_FAMILIES) - 1) / len(MANDATED_SCREENING_FAMILIES),
            places=9,
        )

    def test_depth_in_one_family_does_not_replace_another(self):
        flow = [entry for entry in full_flow() if entry["family"] != "burn-in"]
        flow.append(step("electrical-measurement", 20, step_id="S20"))
        flow.append(step("electrical-measurement", 21, step_id="S21"))
        absent, _ = screening_family_coverage(flow)
        self.assertIn("burn-in", absent)

    def test_family_lookup_is_case_insensitive(self):
        flow = [entry for entry in full_flow() if entry["family"] != "burn-in"]
        flow.append(step("BURN-IN", 20, step_id="S20"))
        absent, _ = screening_family_coverage(flow)
        self.assertEqual(absent, ())

    def test_incomplete_step_contributes_no_family(self):
        flow = [entry for entry in full_flow() if entry["family"] != "burn-in"]
        broken = step("burn-in", 20, step_id="S20")
        del broken["condition"]
        flow.append(broken)
        absent, _ = screening_family_coverage(flow)
        self.assertIn("burn-in", absent)


class AcceptanceProbabilityTests(unittest.TestCase):
    def test_a_clean_lot_always_passes(self):
        self.assertAlmostEqual(
            probability_of_acceptance(100, 20, 0, 0), 1.0, places=9
        )

    def test_defectives_within_the_accept_number_always_pass(self):
        self.assertAlmostEqual(
            probability_of_acceptance(100, 20, 2, 2), 1.0, places=9
        )

    def test_known_small_case_is_exact(self):
        self.assertAlmostEqual(probability_of_acceptance(10, 5, 0, 1), 0.5, places=9)

    def test_a_fully_defective_lot_never_passes(self):
        self.assertAlmostEqual(
            probability_of_acceptance(10, 5, 0, 10), 0.0, places=9
        )

    def test_more_defectives_are_harder_to_accept(self):
        light = probability_of_acceptance(200, 40, 1, 4)
        heavy = probability_of_acceptance(200, 40, 1, 40)
        self.assertLess(heavy, light)

    def test_a_larger_sample_is_harder_to_accept(self):
        small = probability_of_acceptance(200, 10, 0, 20)
        large = probability_of_acceptance(200, 80, 0, 20)
        self.assertLess(large, small)

    def test_a_sample_larger_than_the_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            probability_of_acceptance(10, 20, 0, 1)

    def test_more_defectives_than_the_lot_holds_is_rejected(self):
        with self.assertRaises(ValueError):
            probability_of_acceptance(10, 5, 0, 11)

    def test_negative_accept_number_rejected(self):
        with self.assertRaises(ValueError):
            probability_of_acceptance(10, 5, -1, 1)

    def test_zero_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            probability_of_acceptance(0, 5, 0, 0)


class LotAcceptanceTests(unittest.TestCase):
    def test_discriminating_plan_raises_no_finding(self):
        self.assertEqual(lot_acceptance_findings(plan()), [])

    def test_sample_larger_than_the_lot_is_reported(self):
        dispositions = [
            entry["disposition"]
            for entry in lot_acceptance_findings(plan(lot_size=10, sample_size=20))
        ]
        self.assertIn("sample-exceeds-lot", dispositions)

    def test_accept_number_at_the_sample_size_is_reported(self):
        dispositions = [
            entry["disposition"]
            for entry in lot_acceptance_findings(plan(accept_number=20))
        ]
        self.assertIn("accept-number-not-discriminating", dispositions)

    def test_incomplete_plan_is_its_own_finding(self):
        incomplete = plan()
        del incomplete["sample_size"]
        findings = lot_acceptance_findings(incomplete)
        self.assertEqual(findings[0]["disposition"], "lot-plan-incomplete")

    def test_every_named_plan_field_is_required(self):
        for field in LOT_ACCEPTANCE_FIELDS:
            incomplete = plan()
            del incomplete[field]
            findings = lot_acceptance_findings(incomplete)
            self.assertEqual(findings[0]["disposition"], "lot-plan-incomplete")

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            lot_acceptance_findings(["lot_size"])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "header": header(),
            "sections": sections(),
            "screening_steps": full_flow(),
            "lot_acceptance": plan(),
        }
        spec.update(overrides)
        return spec

    def test_clean_specification_is_orderable(self):
        result = assess_procurement_specification_drd(self._spec())
        self.assertEqual(result["verdict"], "issue")
        self.assertTrue(result["orderable"])
        self.assertEqual(result["findings"], [])

    def test_absent_section_holds_the_specification(self):
        light = sections()
        del light["lot-acceptance-testing"]
        result = assess_procurement_specification_drd(self._spec(sections=light))
        self.assertEqual(result["verdict"], "hold")
        self.assertEqual(result["findings"][0]["disposition"], "section-absent")

    def test_findings_are_ranked_worst_first(self):
        light = sections()
        del light["identification"]
        result = assess_procurement_specification_drd(
            self._spec(sections=light, lot_acceptance=plan(accept_number=20))
        )
        severities = [entry["severity"] for entry in result["findings"]]
        self.assertEqual(severities, sorted(severities))

    def test_missing_screening_family_is_a_finding(self):
        flow = [entry for entry in full_flow() if entry["family"] != "burn-in"]
        result = assess_procurement_specification_drd(self._spec(screening_steps=flow))
        dispositions = [entry["disposition"] for entry in result["findings"]]
        self.assertIn("screening-family-absent", dispositions)
        self.assertLess(result["screening_family_coverage"], 1.0)

    def test_acceptance_probability_is_reported_for_a_usable_plan(self):
        result = assess_procurement_specification_drd(
            self._spec(assumed_defectives=1)
        )
        self.assertAlmostEqual(result["acceptance_probability"], 0.8, places=9)

    def test_acceptance_probability_is_withheld_when_the_plan_is_incomplete(self):
        incomplete = plan()
        del incomplete["accept_number"]
        result = assess_procurement_specification_drd(
            self._spec(lot_acceptance=incomplete)
        )
        self.assertIsNone(result["acceptance_probability"])

    def test_exactly_met_section_coverage_still_holds_on_findings(self):
        flow = [entry for entry in full_flow() if entry["family"] != "burn-in"]
        result = assess_procurement_specification_drd(
            self._spec(screening_steps=flow, required_section_coverage=1.0)
        )
        self.assertAlmostEqual(result["section_coverage"], 1.0, places=9)
        self.assertEqual(result["verdict"], "hold")

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)

    def test_missing_lot_acceptance_key_rejected(self):
        spec = self._spec()
        del spec["lot_acceptance"]
        with self.assertRaises(ValueError):
            assess_procurement_specification_drd(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_specification_drd(["header"])

    def test_out_of_range_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_specification_drd(
                self._spec(required_section_coverage=1.9)
            )

    def test_boolean_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_specification_drd(
                self._spec(required_section_coverage=True)
            )


if __name__ == "__main__":
    unittest.main()
