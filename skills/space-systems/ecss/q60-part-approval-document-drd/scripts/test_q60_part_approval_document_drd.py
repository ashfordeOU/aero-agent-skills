"""Contract tests for the Annex D part approval document data item logic."""

import unittest

from q60_part_approval_document_drd_logic import (
    COVERAGE_TOLERANCE,
    DECISION_VALUES,
    DOCUMENT_BLOCKS,
    OBLIGED_CATEGORY,
    SHEET_FIELDS,
    approved_installation_fraction,
    assess_part_approval_document_drd,
    decision_facts,
    document_block_coverage,
    evaluate_sheet,
    obliged_parts,
    sheet_completeness,
    validate_part_type,
)

PART = "voltage-regulator"


def blocks(**overrides):
    """Return a complete set of document content blocks."""
    base = {name: "text for %s" % name for name in DOCUMENT_BLOCKS}
    base.update(overrides)
    return base


def part(**overrides):
    """Return one flight EEE part type with optional overrides."""
    base = {
        "part_type": PART,
        "approval_category": "eee-flight",
        "installed_count": 40,
    }
    base.update(overrides)
    return base


def sheet(**overrides):
    """Return one approvable part sheet with optional overrides."""
    base = {
        "sheet_id": "PAD-001",
        "part_type": PART,
        "manufacturer": "supplier-north",
        "part_number": "VR-4410",
        "procurement_reference": "PS-4410-B",
        "evaluation_evidence": "evaluation report ER-4410 issue 2",
        "decision": "approved",
        "decision_authority": "customer product assurance",
        "decision_date": "2026-05-06",
    }
    base.update(overrides)
    return base


def index(*parts):
    return {entry["part_type"].lower(): entry for entry in parts}


class PartTypeTests(unittest.TestCase):
    def test_designation_is_stripped(self):
        self.assertEqual(validate_part_type("  voltage-regulator "), PART)

    def test_blank_designation_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_type("   ")

    def test_non_string_designation_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_type(4410)


class DocumentBlockTests(unittest.TestCase):
    def test_complete_document_scores_one(self):
        absent, coverage = document_block_coverage(blocks())
        self.assertEqual(absent, ())
        self.assertAlmostEqual(coverage, 1.0, places=9)

    def test_coverage_is_weighted_not_counted(self):
        light = blocks()
        del light["scope-and-applicability"]
        heavy = blocks()
        del heavy["approval-summary"]
        _, light_coverage = document_block_coverage(light)
        _, heavy_coverage = document_block_coverage(heavy)
        self.assertGreater(light_coverage, heavy_coverage)

    def test_absent_block_is_named(self):
        incomplete = blocks()
        del incomplete["signature-and-date"]
        absent, _ = document_block_coverage(incomplete)
        self.assertEqual(absent, ("signature-and-date",))

    def test_blank_block_counts_as_absent(self):
        absent, _ = document_block_coverage(blocks(**{"approval-summary": "  "}))
        self.assertIn("approval-summary", absent)

    def test_weighted_value_matches_the_table(self):
        incomplete = blocks()
        del incomplete["identification"]
        _, coverage = document_block_coverage(incomplete)
        total = sum(DOCUMENT_BLOCKS.values())
        expected = (total - DOCUMENT_BLOCKS["identification"]) / total
        self.assertAlmostEqual(coverage, expected, places=9)

    def test_non_mapping_blocks_rejected(self):
        with self.assertRaises(ValueError):
            document_block_coverage(["identification"])


class DecisionTests(unittest.TestCase):
    def test_approval_is_settled_and_permits_use(self):
        facts = decision_facts("approved")
        self.assertTrue(facts["settled"])
        self.assertTrue(facts["permits_use"])

    def test_refusal_is_settled_and_refuses_use(self):
        facts = decision_facts("not-approved")
        self.assertTrue(facts["settled"])
        self.assertFalse(facts["permits_use"])

    def test_deferral_is_not_a_decision(self):
        self.assertFalse(decision_facts("deferred")["settled"])

    def test_decision_lookup_is_case_insensitive(self):
        self.assertEqual(decision_facts("APPROVED")["decision"], "approved")

    def test_unknown_decision_rejected(self):
        with self.assertRaises(ValueError):
            decision_facts("agreed-in-the-meeting")

    def test_every_known_decision_answers_both_facts(self):
        for value in DECISION_VALUES:
            facts = decision_facts(value)
            self.assertIsInstance(facts["settled"], bool)
            self.assertIsInstance(facts["permits_use"], bool)


class SheetCompletenessTests(unittest.TestCase):
    def test_complete_sheet_scores_one(self):
        missing, fraction = sheet_completeness(sheet())
        self.assertEqual(missing, ())
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_missing_evidence_is_reported(self):
        incomplete = sheet()
        del incomplete["evaluation_evidence"]
        missing, fraction = sheet_completeness(incomplete)
        self.assertIn("evaluation_evidence", missing)
        self.assertAlmostEqual(
            fraction, (len(SHEET_FIELDS) - 1) / len(SHEET_FIELDS), places=9
        )

    def test_blank_authority_counts_as_missing(self):
        missing, _ = sheet_completeness(sheet(decision_authority="  "))
        self.assertIn("decision_authority", missing)

    def test_none_date_counts_as_missing(self):
        missing, _ = sheet_completeness(sheet(decision_date=None))
        self.assertIn("decision_date", missing)

    def test_non_mapping_sheet_rejected(self):
        with self.assertRaises(ValueError):
            sheet_completeness("PAD-001")


class ObligedPartTests(unittest.TestCase):
    def test_flight_eee_parts_are_obliged(self):
        self.assertEqual(obliged_parts([part()]), (PART,))

    def test_other_categories_are_not_obliged(self):
        obliged = obliged_parts(
            [part(), part(part_type="test-lead", approval_category="ground-support")]
        )
        self.assertEqual(obliged, (PART,))

    def test_category_matching_is_case_insensitive(self):
        self.assertEqual(
            obliged_parts([part(approval_category="EEE-Flight")]), (PART,)
        )
        self.assertEqual(OBLIGED_CATEGORY, "eee-flight")

    def test_repeated_part_type_rejected(self):
        with self.assertRaises(ValueError):
            obliged_parts([part(), part()])

    def test_non_positive_installed_count_rejected(self):
        with self.assertRaises(ValueError):
            obliged_parts([part(installed_count=0)])

    def test_build_with_no_obliged_part_rejected(self):
        with self.assertRaises(ValueError):
            obliged_parts([part(approval_category="non-flight")])

    def test_empty_part_sequence_rejected(self):
        with self.assertRaises(ValueError):
            obliged_parts([])


class EvaluateSheetTests(unittest.TestCase):
    def test_clean_sheet_is_accepted(self):
        record = evaluate_sheet(sheet(), index(part()))
        self.assertEqual(record["disposition"], "accepted")
        self.assertTrue(record["accepted"])

    def test_incomplete_sheet_is_not_graded_further(self):
        record = evaluate_sheet(sheet(decision=None), index(part()))
        self.assertEqual(record["disposition"], "sheet-incomplete")
        self.assertIsNone(record["decision"])

    def test_sheet_for_a_part_not_in_the_build(self):
        record = evaluate_sheet(sheet(part_type="mystery-part"), index(part()))
        self.assertEqual(record["disposition"], "unknown-part-type")

    def test_sheet_for_another_category_is_outside_the_obligation(self):
        other = part(part_type="test-lead", approval_category="ground-support")
        record = evaluate_sheet(
            sheet(part_type="test-lead"), index(part(), other)
        )
        self.assertEqual(record["disposition"], "outside-obligation")

    def test_unknown_decision_is_its_own_disposition(self):
        record = evaluate_sheet(sheet(decision="waved-through"), index(part()))
        self.assertEqual(record["disposition"], "unknown-decision")

    def test_limited_approval_without_limitations_is_blocked(self):
        record = evaluate_sheet(
            sheet(decision="approved-with-limitations"), index(part())
        )
        self.assertEqual(record["disposition"], "limitation-not-recorded")

    def test_limited_approval_with_limitations_is_accepted(self):
        record = evaluate_sheet(
            sheet(
                decision="approved-with-limitations",
                limitations="not for use above 85 degrees case temperature",
            ),
            index(part()),
        )
        self.assertEqual(record["disposition"], "accepted")

    def test_deferral_and_refusal_are_separate_dispositions(self):
        deferred = evaluate_sheet(sheet(decision="deferred"), index(part()))
        refused = evaluate_sheet(sheet(decision="not-approved"), index(part()))
        self.assertEqual(deferred["disposition"], "decision-deferred")
        self.assertEqual(refused["disposition"], "part-not-approved")
        self.assertNotEqual(deferred["disposition"], refused["disposition"])

    def test_second_sheet_for_a_decided_part_is_a_duplicate(self):
        record = evaluate_sheet(
            sheet(sheet_id="PAD-002"), index(part()), already_decided={PART}
        )
        self.assertEqual(record["disposition"], "duplicate-sheet")

    def test_empty_part_index_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sheet(sheet(), {})


class ApprovedFractionTests(unittest.TestCase):
    def test_fraction_is_weighted_by_installation_count(self):
        second = part(part_type="opto-coupler", installed_count=10)
        part_index = index(part(), second)
        records = [
            evaluate_sheet(sheet(), part_index),
            evaluate_sheet(
                sheet(
                    sheet_id="PAD-002",
                    part_type="opto-coupler",
                    decision="deferred",
                ),
                part_index,
            ),
        ]
        fraction = approved_installation_fraction(
            records, part_index, (PART, "opto-coupler")
        )
        self.assertAlmostEqual(fraction, 40 / 50, places=9)

    def test_fraction_is_one_when_every_obliged_part_is_approved(self):
        part_index = index(part())
        records = [evaluate_sheet(sheet(), part_index)]
        self.assertAlmostEqual(
            approved_installation_fraction(records, part_index, (PART,)), 1.0, places=9
        )

    def test_a_duplicate_approval_is_not_counted_twice(self):
        part_index = index(part())
        record = evaluate_sheet(sheet(), part_index)
        self.assertAlmostEqual(
            approved_installation_fraction(
                [record, dict(record)], part_index, (PART,)
            ),
            1.0,
            places=9,
        )

    def test_empty_obliged_sequence_rejected(self):
        with self.assertRaises(ValueError):
            approved_installation_fraction([], index(part()), ())

    def test_record_without_a_disposition_rejected(self):
        with self.assertRaises(ValueError):
            approved_installation_fraction(
                [{"part_type": PART}], index(part()), (PART,)
            )


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "blocks": blocks(),
            "parts": [part()],
            "sheets": [sheet()],
        }
        spec.update(overrides)
        return spec

    def test_clean_deliverable_is_submittable(self):
        result = assess_part_approval_document_drd(self._spec())
        self.assertEqual(result["verdict"], "submit")
        self.assertTrue(result["submittable"])
        self.assertEqual(result["findings"], [])

    def test_absent_document_block_holds_the_deliverable(self):
        light = blocks()
        del light["approval-summary"]
        result = assess_part_approval_document_drd(self._spec(blocks=light))
        self.assertEqual(result["verdict"], "hold")
        self.assertEqual(result["findings"][0]["disposition"], "document-block-absent")

    def test_part_without_a_sheet_is_reported(self):
        second = part(part_type="opto-coupler", installed_count=10)
        result = assess_part_approval_document_drd(
            self._spec(parts=[part(), second])
        )
        self.assertEqual(result["parts_without_a_sheet"], ("opto-coupler",))
        dispositions = [entry["disposition"] for entry in result["findings"]]
        self.assertIn("sheet-absent", dispositions)

    def test_findings_are_ranked_worst_first(self):
        result = assess_part_approval_document_drd(
            self._spec(
                sheets=[
                    sheet(decision="not-approved"),
                    sheet(sheet_id="PAD-002", decision_authority="  "),
                ]
            )
        )
        severities = [entry["severity"] for entry in result["findings"]]
        self.assertEqual(severities, sorted(severities))
        self.assertEqual(result["findings"][0]["disposition"], "sheet-incomplete")

    def test_a_resubmission_after_a_refusal_is_not_a_duplicate(self):
        result = assess_part_approval_document_drd(
            self._spec(
                sheets=[sheet(decision="not-approved"), sheet(sheet_id="PAD-002")]
            )
        )
        dispositions = [entry["disposition"] for entry in result["findings"]]
        self.assertNotIn("duplicate-sheet", dispositions)
        self.assertAlmostEqual(
            result["approved_installation_fraction"], 1.0, places=9
        )

    def test_a_second_sheet_after_an_approval_is_a_duplicate(self):
        result = assess_part_approval_document_drd(
            self._spec(sheets=[sheet(), sheet(sheet_id="PAD-002")])
        )
        dispositions = [entry["disposition"] for entry in result["findings"]]
        self.assertIn("duplicate-sheet", dispositions)

    def test_other_category_sheet_is_neither_covered_nor_a_shortfall(self):
        other = part(part_type="test-lead", approval_category="ground-support")
        result = assess_part_approval_document_drd(
            self._spec(
                parts=[part(), other],
                sheets=[sheet(), sheet(sheet_id="PAD-002", part_type="test-lead")],
            )
        )
        self.assertEqual(result["obliged_parts"], (PART,))
        self.assertAlmostEqual(
            result["approved_installation_fraction"], 1.0, places=9
        )
        self.assertEqual(result["verdict"], "submit")

    def test_exactly_met_fraction_still_holds_on_findings(self):
        second = part(part_type="opto-coupler", installed_count=10)
        result = assess_part_approval_document_drd(
            self._spec(
                parts=[part(), second],
                sheets=[
                    sheet(),
                    sheet(
                        sheet_id="PAD-002",
                        part_type="opto-coupler",
                        decision="deferred",
                    ),
                ],
                required_approved_fraction=0.8,
            )
        )
        self.assertAlmostEqual(
            result["approved_installation_fraction"], 0.8, places=9
        )
        self.assertEqual(result["verdict"], "hold")

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)

    def test_missing_sheets_key_rejected(self):
        spec = self._spec()
        del spec["sheets"]
        with self.assertRaises(ValueError):
            assess_part_approval_document_drd(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_approval_document_drd(["blocks"])

    def test_out_of_range_required_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_approval_document_drd(
                self._spec(required_approved_fraction=1.6)
            )

    def test_boolean_required_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_approval_document_drd(
                self._spec(required_approved_fraction=True)
            )


if __name__ == "__main__":
    unittest.main()
