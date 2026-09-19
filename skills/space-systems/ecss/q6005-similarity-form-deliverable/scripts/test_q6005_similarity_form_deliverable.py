"""Contract tests for the Annex C similarity form deliverable."""

import unittest

from q6005_similarity_form_deliverable_logic import (
    APPROVAL_STATUS_VOCABULARY,
    MANDATED_ATTRIBUTES,
    MANDATED_IDENTITY_FIELDS,
    assess_similarity_form,
    derived_verdict,
    documented_evidence_ratio,
    missing_attribute_rows,
    normalise_row,
    normalise_rows,
    normalise_text,
    row_findings,
    unsupported_divergences,
    validate_identity_block,
)


def identity(**overrides):
    block = {
        "candidate_designation": "HYB-221B",
        "reference_designation": "HYB-221A",
        "reference_approval_reference": "APR-2024-118",
        "reference_approval_status": "approved",
        "reference_quality_level": "class 1",
        "candidate_quality_level": "class 1",
        "claim_prepared_by": "Design authority",
        "claim_date": "2026-05-11",
    }
    block.update(overrides)
    return {k: v for k, v in block.items() if v is not Ellipsis}


def same_rows():
    return [
        {
            "attribute": name,
            "candidate_value": "baseline %s" % name,
            "reference_value": "baseline %s" % name,
            "declared_verdict": "same",
        }
        for name in MANDATED_ATTRIBUTES
    ]


def clean_form():
    return {"identity": identity(), "rows": same_rows()}


class NormaliseTextTests(unittest.TestCase):
    def test_surrounding_space_is_dropped(self):
        self.assertEqual(normalise_text("  thick film  ", "x"), "thick film")

    def test_none_becomes_blank(self):
        self.assertEqual(normalise_text(None, "x"), "")

    def test_number_is_kept_as_text(self):
        self.assertEqual(normalise_text(3, "x"), "3")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            normalise_text(True, "x")

    def test_list_rejected(self):
        with self.assertRaises(ValueError):
            normalise_text(["a"], "x")


class IdentityBlockTests(unittest.TestCase):
    def test_complete_block_is_clean(self):
        result = validate_identity_block(identity())
        self.assertEqual(result["absent_fields"], ())
        self.assertEqual(result["blank_fields"], ())
        self.assertTrue(result["reference_currently_approved"])

    def test_dropped_entry_is_reported_absent(self):
        block = identity()
        del block["claim_date"]
        self.assertEqual(validate_identity_block(block)["absent_fields"], ("claim_date",))

    def test_blank_entry_is_reported_blank_not_absent(self):
        result = validate_identity_block(identity(reference_approval_reference=""))
        self.assertEqual(result["blank_fields"], ("reference_approval_reference",))
        self.assertEqual(result["absent_fields"], ())

    def test_lapsed_status_is_recognised_but_not_current(self):
        result = validate_identity_block(identity(reference_approval_status="approval lapsed"))
        self.assertTrue(result["approval_status_known"])
        self.assertFalse(result["reference_currently_approved"])

    def test_unknown_status_is_flagged(self):
        result = validate_identity_block(identity(reference_approval_status="probably fine"))
        self.assertFalse(result["approval_status_known"])

    def test_duplicate_identity_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_identity_block({"Claim-Date": "a", "claim_date": "b"})

    def test_non_mapping_block_rejected(self):
        with self.assertRaises(ValueError):
            validate_identity_block([("claim_date", "a")])

    def test_status_vocabulary_holds_the_current_value(self):
        self.assertIn("approved", APPROVAL_STATUS_VOCABULARY)

    def test_identity_field_list_is_not_empty(self):
        self.assertTrue(MANDATED_IDENTITY_FIELDS)


class RowNormalisationTests(unittest.TestCase):
    def test_attribute_spelling_is_folded(self):
        row = normalise_row({"attribute": "Die-Attach Process", "candidate_value": "a",
                             "reference_value": "a"})
        self.assertEqual(row["attribute"], "die_attach_process")

    def test_absent_verdict_is_left_blank(self):
        row = normalise_row({"attribute": "x", "candidate_value": "a", "reference_value": "a"})
        self.assertEqual(row["declared_verdict"], "")

    def test_unrecognised_verdict_rejected(self):
        with self.assertRaises(ValueError):
            normalise_row({"attribute": "x", "candidate_value": "a",
                           "reference_value": "b", "declared_verdict": "probably"})

    def test_missing_reference_value_rejected(self):
        with self.assertRaises(ValueError):
            normalise_row({"attribute": "x", "candidate_value": "a"})

    def test_blank_attribute_rejected(self):
        with self.assertRaises(ValueError):
            normalise_row({"attribute": "  ", "candidate_value": "a", "reference_value": "a"})

    def test_repeated_attribute_rejected(self):
        rows = same_rows() + [same_rows()[0]]
        with self.assertRaises(ValueError):
            normalise_rows(rows)

    def test_non_sequence_rows_rejected(self):
        with self.assertRaises(ValueError):
            normalise_rows({"attribute": "x"})


class DerivedVerdictTests(unittest.TestCase):
    def test_identical_values_support_same(self):
        self.assertEqual(derived_verdict("Thick Film", "thick-film"), "same")

    def test_different_values_support_differs(self):
        self.assertEqual(derived_verdict("thick film", "thin film"), "differs")

    def test_blank_value_cannot_support_a_verdict(self):
        with self.assertRaises(ValueError):
            derived_verdict("", "thin film")

    def test_non_string_value_rejected(self):
        with self.assertRaises(ValueError):
            derived_verdict(None, "thin film")


class RowFindingTests(unittest.TestCase):
    def test_consistent_same_row_is_clean(self):
        record = normalise_rows([same_rows()[0]])[0]
        self.assertEqual(row_findings(record)["findings"], [])

    def test_likeness_declared_over_two_different_values_is_caught(self):
        record = normalise_rows([{
            "attribute": "wire_bond_process", "candidate_value": "wedge",
            "reference_value": "ball", "declared_verdict": "same"}])[0]
        outcome = row_findings(record)
        self.assertTrue(any("support" in f for f in outcome["findings"]))

    def test_divergent_row_without_justification_is_caught(self):
        record = normalise_rows([{
            "attribute": "wire_bond_process", "candidate_value": "wedge",
            "reference_value": "ball", "declared_verdict": "differs",
            "impact_statement": "no change to interconnect strength"}])[0]
        self.assertTrue(any("justification" in f for f in row_findings(record)["findings"]))

    def test_divergent_row_without_impact_statement_is_caught(self):
        record = normalise_rows([{
            "attribute": "wire_bond_process", "candidate_value": "wedge",
            "reference_value": "ball", "declared_verdict": "differs",
            "justification": "same alloy, same pull strength envelope"}])[0]
        self.assertTrue(any("impact" in f for f in row_findings(record)["findings"]))

    def test_supported_divergent_row_is_clean(self):
        record = normalise_rows([{
            "attribute": "wire_bond_process", "candidate_value": "wedge",
            "reference_value": "ball", "declared_verdict": "differs",
            "justification": "same alloy and pull strength envelope",
            "impact_statement": "no change to the qualification evidence"}])[0]
        self.assertEqual(row_findings(record)["findings"], [])

    def test_row_with_no_verdict_is_read_from_the_values(self):
        record = normalise_rows([{
            "attribute": "substrate_material", "candidate_value": "alumina",
            "reference_value": "alumina"}])[0]
        self.assertEqual(row_findings(record)["effective_verdict"], "same")

    def test_blank_compared_value_is_reported(self):
        record = normalise_rows([{
            "attribute": "substrate_material", "candidate_value": "",
            "reference_value": "alumina", "declared_verdict": "same"}])[0]
        self.assertTrue(any("blank" in f for f in row_findings(record)["findings"]))


class CoverageTests(unittest.TestCase):
    def test_full_set_leaves_nothing_missing(self):
        self.assertEqual(missing_attribute_rows(normalise_rows(same_rows())), ())

    def test_dropped_attribute_is_reported(self):
        rows = [r for r in same_rows() if r["attribute"] != "screening_sequence"]
        self.assertEqual(
            missing_attribute_rows(normalise_rows(rows)), ("screening_sequence",)
        )

    def test_unsupported_divergence_is_listed(self):
        rows = same_rows()
        rows[3] = dict(rows[3], reference_value="other", declared_verdict="differs")
        self.assertEqual(
            unsupported_divergences(normalise_rows(rows)),
            (MANDATED_ATTRIBUTES[3],),
        )

    def test_supported_divergence_is_not_listed(self):
        rows = same_rows()
        rows[3] = dict(rows[3], reference_value="other", declared_verdict="differs",
                       justification="equivalent process window",
                       impact_statement="no delta testing owed")
        self.assertEqual(unsupported_divergences(normalise_rows(rows)), ())


class EvidenceRatioTests(unittest.TestCase):
    def test_clean_record_scores_one(self):
        self.assertAlmostEqual(
            documented_evidence_ratio(normalise_rows(same_rows())), 1.0, places=9
        )

    def test_missing_row_lowers_the_ratio(self):
        kept = [r for r in same_rows() if r["attribute"] != "screening_sequence"]
        self.assertEqual(len(kept), len(MANDATED_ATTRIBUTES) - 1)
        short = documented_evidence_ratio(normalise_rows(kept))
        n = len(MANDATED_ATTRIBUTES)
        expected = (2 * n - 2) / (2 * n - 1)
        self.assertAlmostEqual(short, expected, places=9)

    def test_supported_divergence_still_scores_one(self):
        rows = same_rows()
        rows[0] = dict(rows[0], reference_value="other", declared_verdict="differs",
                       justification="equivalent function", impact_statement="none")
        self.assertAlmostEqual(
            documented_evidence_ratio(normalise_rows(rows)), 1.0, places=9
        )

    def test_empty_row_set_scores_zero_coverage(self):
        self.assertAlmostEqual(documented_evidence_ratio([]), 0.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_clean_form_is_record_complete(self):
        result = assess_similarity_form(clean_form())
        self.assertEqual(result["verdict"], "record-complete")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["record_complete"])

    def test_lapsed_reference_is_a_record_finding(self):
        form = clean_form()
        form["identity"] = identity(reference_approval_status="approval withdrawn")
        result = assess_similarity_form(form)
        self.assertEqual(result["verdict"], "record-incomplete")
        self.assertTrue(any("withdrawn" in f for f in result["findings"]))

    def test_extra_attribute_row_only_earns_a_remark(self):
        form = clean_form()
        form["rows"] = same_rows() + [{
            "attribute": "supplier_part_number", "candidate_value": "a",
            "reference_value": "a", "declared_verdict": "same"}]
        self.assertEqual(
            assess_similarity_form(form)["verdict"], "record-complete-with-remarks"
        )

    def test_unsupported_divergence_makes_the_record_incomplete(self):
        form = clean_form()
        rows = same_rows()
        rows[5] = dict(rows[5], reference_value="different package",
                       declared_verdict="differs")
        form["rows"] = rows
        result = assess_similarity_form(form)
        self.assertEqual(result["verdict"], "record-incomplete")
        self.assertIn(MANDATED_ATTRIBUTES[5], result["unsupported_divergences"])

    def test_missing_rows_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_similarity_form({"identity": identity()})

    def test_non_mapping_form_rejected(self):
        with self.assertRaises(ValueError):
            assess_similarity_form("form")


if __name__ == "__main__":
    unittest.main()
