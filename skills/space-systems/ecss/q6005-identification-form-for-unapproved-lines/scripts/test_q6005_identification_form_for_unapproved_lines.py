"""Contract tests for the clause 6.2.4 unapproved-line form-content logic."""

import unittest

from q6005_identification_form_for_unapproved_lines_logic import (
    BASE_BLOCKS,
    CONTENT_BLOCKS,
    UNAPPROVED_ONLY_BLOCKS,
    assess_unapproved_line_form,
    block_report,
    completeness_counts,
    completeness_ratio,
    deciding_gaps,
    field_supplied,
    form_reports,
    is_admissible,
    required_blocks,
    supporting_gaps,
    validate_form,
)


def full_form(blocks=None):
    """A form carrying every field of every named block."""
    names = blocks if blocks is not None else tuple(CONTENT_BLOCKS)
    return {
        name: {field: "stated" for field in CONTENT_BLOCKS[name]["fields"]}
        for name in names
    }


class FieldSuppliedTests(unittest.TestCase):
    def test_text_counts(self):
        self.assertTrue(field_supplied("PN-4471"))

    def test_blank_text_does_not_count(self):
        self.assertFalse(field_supplied("   "))

    def test_none_does_not_count(self):
        self.assertFalse(field_supplied(None))

    def test_empty_list_does_not_count(self):
        self.assertFalse(field_supplied([]))

    def test_populated_list_counts(self):
        self.assertTrue(field_supplied(["EL-1", "EL-2"]))

    def test_zero_counts_as_a_stated_value(self):
        self.assertTrue(field_supplied(0))

    def test_non_finite_number_does_not_count(self):
        self.assertFalse(field_supplied(float("nan")))


class RequiredBlockTests(unittest.TestCase):
    def test_approved_line_owes_the_base_blocks_only(self):
        self.assertEqual(required_blocks(True), BASE_BLOCKS)

    def test_unapproved_line_owes_the_stand_in_blocks_too(self):
        owed = required_blocks(False)
        self.assertEqual(owed, BASE_BLOCKS + UNAPPROVED_ONLY_BLOCKS)
        for block in UNAPPROVED_ONLY_BLOCKS:
            self.assertIn(block, owed)

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            required_blocks("no")


class ValidateFormTests(unittest.TestCase):
    def test_full_form_round_trips(self):
        self.assertEqual(set(validate_form(full_form())), set(CONTENT_BLOCKS))

    def test_unknown_block_rejected(self):
        form = full_form()
        form["commercial-terms"] = {"price": "on request"}
        with self.assertRaises(ValueError):
            validate_form(form)

    def test_unknown_field_rejected(self):
        form = full_form(("supplier-identity",))
        form["supplier-identity"]["contact-email"] = "someone"
        with self.assertRaises(ValueError):
            validate_form(form)

    def test_non_mapping_block_rejected(self):
        with self.assertRaises(ValueError):
            validate_form({"supplier-identity": ["supplier-name"]})

    def test_non_mapping_form_rejected(self):
        with self.assertRaises(ValueError):
            validate_form(list(CONTENT_BLOCKS))


class BlockReportTests(unittest.TestCase):
    def test_complete_block(self):
        report = block_report("supplier-identity", full_form()["supplier-identity"])
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["missing_deciding"], ())

    def test_partial_block_names_the_deciding_gap(self):
        cells = dict(full_form()["hybrid-definition"])
        del cells["drawing-issue"]
        report = block_report("hybrid-definition", cells)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["missing_deciding"], ("drawing-issue",))

    def test_partial_block_separates_supporting_gaps(self):
        cells = dict(full_form()["hybrid-definition"])
        del cells["package-outline"]
        report = block_report("hybrid-definition", cells)
        self.assertEqual(report["missing_deciding"], ())
        self.assertEqual(report["missing_supporting"], ("package-outline",))

    def test_absent_block(self):
        report = block_report("compensating-controls", None)
        self.assertEqual(report["status"], "absent")
        self.assertEqual(len(report["missing_deciding"]), 2)

    def test_blank_cell_reads_as_absent(self):
        cells = dict(full_form()["element-list"])
        cells["element-procurement-level"] = ""
        report = block_report("element-list", cells)
        self.assertIn("element-procurement-level", report["missing_deciding"])

    def test_unknown_block_rejected(self):
        with self.assertRaises(ValueError):
            block_report("thermal-analysis", {})

    def test_non_mapping_cells_rejected(self):
        with self.assertRaises(ValueError):
            block_report("element-list", ["element-part-numbers"])


class CompletenessTests(unittest.TestCase):
    def test_full_unapproved_form_is_entirely_supplied(self):
        supplied, owed = completeness_counts(full_form(), False)
        self.assertEqual(supplied, owed)
        self.assertAlmostEqual(completeness_ratio(full_form(), False), 1.0, places=9)

    def test_unapproved_case_owes_more_fields_than_the_approved_one(self):
        _, owed_unapproved = completeness_counts(full_form(), False)
        _, owed_approved = completeness_counts(full_form(), True)
        self.assertGreater(owed_unapproved, owed_approved)

    def test_base_only_form_covers_the_approved_case_fully(self):
        form = full_form(BASE_BLOCKS)
        self.assertAlmostEqual(completeness_ratio(form, True), 1.0, places=9)

    def test_base_only_form_is_short_for_an_unapproved_line(self):
        form = full_form(BASE_BLOCKS)
        supplied, owed = completeness_counts(form, False)
        self.assertAlmostEqual(completeness_ratio(form, False), supplied / float(owed), places=9)
        self.assertLess(supplied, owed)

    def test_reports_cover_exactly_the_owed_blocks(self):
        reports = form_reports(full_form(), True)
        self.assertEqual(tuple(r["block"] for r in reports), BASE_BLOCKS)


class AdmissibilityTests(unittest.TestCase):
    def test_full_form_is_admissible(self):
        self.assertTrue(is_admissible(full_form(), False))

    def test_base_only_form_is_not_admissible_for_an_unapproved_line(self):
        self.assertFalse(is_admissible(full_form(BASE_BLOCKS), False))

    def test_base_only_form_is_admissible_for_an_approved_line(self):
        self.assertTrue(is_admissible(full_form(BASE_BLOCKS), True))

    def test_supporting_gap_alone_keeps_the_form_admissible(self):
        form = full_form()
        del form["hybrid-definition"]["package-outline"]
        self.assertTrue(is_admissible(form, False))
        self.assertIn(("hybrid-definition", "package-outline"), supporting_gaps(form, False))

    def test_deciding_gap_alone_makes_the_form_inadmissible(self):
        form = full_form()
        del form["compensating-controls"]["delta-screening-plan"]
        self.assertFalse(is_admissible(form, False))
        self.assertEqual(
            deciding_gaps(form, False), (("compensating-controls", "delta-screening-plan"),)
        )

    def test_gaps_are_reported_in_registry_order(self):
        form = full_form()
        del form["comparable-build-evidence"]["line-capability-data"]
        del form["supplier-identity"]["supplier-name"]
        gaps = deciding_gaps(form, False)
        self.assertEqual(gaps[0][0], "supplier-identity")
        self.assertEqual(gaps[-1][0], "comparable-build-evidence")


class AssessmentTests(unittest.TestCase):
    def test_full_unapproved_form_is_clean(self):
        out = assess_unapproved_line_form({"form": full_form(), "line_approved": False})
        self.assertTrue(out["admissible"])
        self.assertEqual(out["findings"], [])
        self.assertAlmostEqual(out["completeness_ratio"], 1.0, places=9)

    def test_missing_stand_in_blocks_named_explicitly(self):
        out = assess_unapproved_line_form(
            {"form": full_form(BASE_BLOCKS), "line_approved": False}
        )
        self.assertEqual(out["absent_blocks"], UNAPPROVED_ONLY_BLOCKS)
        self.assertFalse(out["admissible"])
        self.assertTrue(
            any("nothing in place of the missing approval" in f for f in out["findings"])
        )

    def test_absent_block_is_reported_once_not_per_field(self):
        out = assess_unapproved_line_form(
            {"form": full_form(BASE_BLOCKS), "line_approved": False}
        )
        for block in UNAPPROVED_ONLY_BLOCKS:
            per_field = [f for f in out["findings"] if f.startswith("deciding field absent: %s" % block)]
            self.assertEqual(per_field, [])

    def test_partial_block_listed_as_partial(self):
        form = full_form()
        del form["screening-and-test-plan"]["test-conditions"]
        out = assess_unapproved_line_form({"form": form, "line_approved": False})
        self.assertIn("screening-and-test-plan", out["partial_blocks"])
        self.assertTrue(out["admissible"])

    def test_stand_in_blocks_on_an_approved_line_are_flagged_as_not_owed(self):
        out = assess_unapproved_line_form({"form": full_form(), "line_approved": True})
        self.assertEqual(set(out["blocks_not_owed"]), set(UNAPPROVED_ONLY_BLOCKS))
        self.assertTrue(any("does not owe" in f for f in out["findings"]))

    def test_field_counts_reported(self):
        out = assess_unapproved_line_form({"form": full_form(), "line_approved": False})
        self.assertEqual(out["fields_supplied"], out["fields_owed"])

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_unapproved_line_form({"form": full_form()})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_unapproved_line_form(["form"])

    def test_non_boolean_line_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_unapproved_line_form({"form": full_form(), "line_approved": "unapproved"})

    def test_unknown_block_in_submitted_form_rejected(self):
        form = full_form()
        form["delivery-schedule"] = {"date": "2026-08-01"}
        with self.assertRaises(ValueError):
            assess_unapproved_line_form({"form": form, "line_approved": False})


if __name__ == "__main__":
    unittest.main()
