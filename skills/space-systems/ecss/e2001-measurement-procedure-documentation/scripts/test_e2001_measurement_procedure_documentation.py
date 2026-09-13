#!/usr/bin/env python3
"""Gate 3 contract test for e2001-measurement-procedure-documentation.

stdlib unittest, offline, deterministic. Exercises item categorization,
recorded-detail depth assessment, reference-list validation, sample
description validation, completeness scoring and the aggregate clause
9.5.1 disposition, including every ValueError path.
"""

import unittest

import e2001_measurement_procedure_documentation_logic as logic


def full_record():
    """A procedure record satisfying every mandatory item comfortably."""
    filler = "recorded detail sentence describing the step in operational terms"
    return {
        "normative-references": "applicable standards and issue dates are listed " + filler,
        "measurement-facility-description": "chamber pumping arrangement and base pressure " + filler,
        "electron-gun-parameters": "energy span beam current spot geometry incidence angle " + filler,
        "sample-description": "material batch thickness and surface finish are stated " + filler,
        "sample-preparation": "cleaning handling mounting and grounding path " + filler,
        "measurement-method": "bias scheme collector arrangement and pulse duration " + filler,
        "data-reduction": "yield derived from measured currents " + filler,
        "uncertainty-budget": "contributions listed and combined " + filler,
        "environmental-conditions": "temperature and pressure during the run " + filler,
        "record-identification": "operator date and document reference " + filler,
    }


def good_references():
    return [
        {"id": "ECSS-E-ST-20-01C", "issue": "rev 1"},
        {"id": "ECSS-Q-ST-70-01C", "issue": "2023-04-01"},
    ]


def good_sample():
    return {
        "material": "aluminium-6061",
        "batch_identifier": "BATCH-77A",
        "thickness_mm": 1.5,
        "surface_finish": "as-received-oxidized",
        "exposed_area_cm2": 4.0,
    }


class TestNormalizeItemKey(unittest.TestCase):
    def test_folds_case_spaces_and_underscores(self):
        self.assertEqual(
            logic.normalize_item_key("  Sample_Description  "), "sample-description"
        )

    def test_collapses_repeated_hyphens(self):
        self.assertEqual(logic.normalize_item_key("data--reduction"), "data-reduction")

    def test_multiword_key_becomes_hyphenated(self):
        self.assertEqual(
            logic.normalize_item_key("electron gun parameters"),
            "electron-gun-parameters",
        )

    def test_non_string_key_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_item_key(17)

    def test_blank_key_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_item_key("   ")

    def test_hyphen_only_key_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_item_key("---")


class TestCategorizeProcedureItem(unittest.TestCase):
    def test_mandatory_item_is_recognized(self):
        self.assertEqual(
            logic.categorize_procedure_item("uncertainty_budget"),
            (logic.MANDATORY, "uncertainty-budget"),
        )

    def test_optional_item_is_recognized(self):
        self.assertEqual(
            logic.categorize_procedure_item("beam-alignment-record"),
            (logic.OPTIONAL, "beam-alignment-record"),
        )

    def test_unknown_item_is_uncategorized(self):
        category, key = logic.categorize_procedure_item("local-lab-annex")
        self.assertEqual(category, logic.UNCATEGORIZED)
        self.assertEqual(key, "local-lab-annex")

    def test_every_mandatory_key_round_trips(self):
        for key in logic.MANDATORY_ITEMS:
            self.assertEqual(
                logic.categorize_procedure_item(key), (logic.MANDATORY, key)
            )


class TestDetailFloor(unittest.TestCase):
    def test_mandatory_floor_is_returned(self):
        self.assertEqual(logic.detail_floor("record-identification"), 6)

    def test_optional_floor_is_returned(self):
        self.assertEqual(logic.detail_floor("surface-analysis-record"), 6)

    def test_uncategorized_key_has_no_floor(self):
        with self.assertRaises(ValueError):
            logic.detail_floor("local-lab-annex")


class TestAssessItemDetail(unittest.TestCase):
    def test_detail_above_floor_is_sufficient(self):
        text = " ".join(["word"] * 12)
        self.assertEqual(
            logic.assess_item_detail("record-identification", text), logic.SUFFICIENT
        )

    def test_detail_exactly_at_floor_is_sufficient(self):
        text = " ".join(["word"] * 6)
        self.assertEqual(
            logic.assess_item_detail("record-identification", text), logic.SUFFICIENT
        )

    def test_detail_one_word_below_floor_is_thin(self):
        text = " ".join(["word"] * 5)
        self.assertEqual(
            logic.assess_item_detail("record-identification", text),
            logic.PRESENT_BUT_THIN,
        )

    def test_non_string_detail_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_item_detail("record-identification", None)

    def test_blank_detail_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_item_detail("record-identification", "   ")


class TestCheckReferenceList(unittest.TestCase):
    def test_clean_list_yields_no_findings(self):
        self.assertEqual(logic.check_reference_list(good_references()), [])

    def test_missing_issue_is_a_finding(self):
        refs = [{"id": "ECSS-E-ST-20-01C", "issue": ""}]
        findings = logic.check_reference_list(refs)
        self.assertEqual(len(findings), 1)
        self.assertIn("issue", findings[0])

    def test_duplicate_identifier_is_a_finding(self):
        refs = [
            {"id": "ECSS-E-ST-20-01C", "issue": "rev 1"},
            {"id": "ECSS-E-ST-20-01C", "issue": "rev 1"},
        ]
        findings = logic.check_reference_list(refs)
        self.assertEqual(len(findings), 1)
        self.assertIn("more than once", findings[0])

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            logic.check_reference_list([])

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            logic.check_reference_list({"id": "x"})

    def test_non_mapping_entry_raises(self):
        with self.assertRaises(ValueError):
            logic.check_reference_list(["ECSS-E-ST-20-01C"])

    def test_entry_without_identifier_raises(self):
        with self.assertRaises(ValueError):
            logic.check_reference_list([{"issue": "rev 1"}])


class TestCheckSampleDescription(unittest.TestCase):
    def test_complete_sample_yields_no_findings(self):
        self.assertEqual(logic.check_sample_description(good_sample()), [])

    def test_sample_without_optional_area_is_accepted(self):
        sample = good_sample()
        del sample["exposed_area_cm2"]
        self.assertEqual(logic.check_sample_description(sample), [])

    def test_area_exactly_at_footprint_floor_is_accepted(self):
        sample = good_sample()
        sample["exposed_area_cm2"] = 0.25
        self.assertEqual(logic.check_sample_description(sample), [])

    def test_area_below_footprint_floor_is_a_finding(self):
        sample = good_sample()
        sample["exposed_area_cm2"] = 0.1
        findings = logic.check_sample_description(sample)
        self.assertEqual(len(findings), 1)
        self.assertIn("beam-footprint", findings[0])

    def test_missing_material_raises(self):
        sample = good_sample()
        sample["material"] = ""
        with self.assertRaises(ValueError):
            logic.check_sample_description(sample)

    def test_missing_batch_identifier_raises(self):
        sample = good_sample()
        del sample["batch_identifier"]
        with self.assertRaises(ValueError):
            logic.check_sample_description(sample)

    def test_missing_surface_finish_raises(self):
        sample = good_sample()
        del sample["surface_finish"]
        with self.assertRaises(ValueError):
            logic.check_sample_description(sample)

    def test_non_numeric_thickness_raises(self):
        sample = good_sample()
        sample["thickness_mm"] = "1.5"
        with self.assertRaises(ValueError):
            logic.check_sample_description(sample)

    def test_zero_thickness_raises(self):
        sample = good_sample()
        sample["thickness_mm"] = 0.0
        with self.assertRaises(ValueError):
            logic.check_sample_description(sample)

    def test_negative_area_raises(self):
        sample = good_sample()
        sample["exposed_area_cm2"] = -1.0
        with self.assertRaises(ValueError):
            logic.check_sample_description(sample)

    def test_non_mapping_sample_raises(self):
        with self.assertRaises(ValueError):
            logic.check_sample_description("aluminium")


class TestAuditProcedureRecord(unittest.TestCase):
    def test_full_record_has_no_missing_items(self):
        audit = logic.audit_procedure_record(full_record())
        self.assertEqual(audit["missing_mandatory"], [])
        self.assertEqual(audit["thin_items"], [])
        self.assertEqual(audit["uncategorized_items"], [])

    def test_missing_item_is_reported(self):
        record = full_record()
        del record["data-reduction"]
        audit = logic.audit_procedure_record(record)
        self.assertEqual(audit["missing_mandatory"], ["data-reduction"])

    def test_thin_item_is_reported_but_still_present(self):
        record = full_record()
        record["uncertainty-budget"] = "budget noted"
        audit = logic.audit_procedure_record(record)
        self.assertIn("uncertainty-budget", audit["thin_items"])
        self.assertEqual(
            audit["present_mandatory"]["uncertainty-budget"], logic.PRESENT_BUT_THIN
        )

    def test_unrecognized_entry_lands_in_the_uncategorized_list(self):
        record = full_record()
        record["local-lab-annex"] = "site specific notes"
        audit = logic.audit_procedure_record(record)
        self.assertEqual(audit["uncategorized_items"], ["local-lab-annex"])
        self.assertEqual(audit["missing_mandatory"], [])

    def test_optional_entry_is_kept_separate(self):
        record = full_record()
        record["witness-specimen-record"] = " ".join(["word"] * 9)
        audit = logic.audit_procedure_record(record)
        self.assertIn("witness-specimen-record", audit["present_optional"])
        self.assertNotIn("witness-specimen-record", audit["present_mandatory"])

    def test_empty_record_raises(self):
        with self.assertRaises(ValueError):
            logic.audit_procedure_record({})

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            logic.audit_procedure_record(["sample-description"])


class TestCompletenessScore(unittest.TestCase):
    def test_full_record_scores_unity(self):
        audit = logic.audit_procedure_record(full_record())
        self.assertAlmostEqual(logic.completeness_score(audit), 1.0, places=12)

    def test_one_missing_item_drops_the_score(self):
        record = full_record()
        del record["sample-preparation"]
        audit = logic.audit_procedure_record(record)
        self.assertAlmostEqual(logic.completeness_score(audit), 0.9, places=12)

    def test_thin_item_does_not_count_as_satisfied(self):
        record = full_record()
        record["record-identification"] = "logged"
        audit = logic.audit_procedure_record(record)
        self.assertAlmostEqual(logic.completeness_score(audit), 0.9, places=12)

    def test_optional_items_do_not_inflate_the_score(self):
        record = full_record()
        del record["data-reduction"]
        record["surface-analysis-record"] = " ".join(["word"] * 9)
        record["beam-alignment-record"] = " ".join(["word"] * 9)
        audit = logic.audit_procedure_record(record)
        self.assertAlmostEqual(logic.completeness_score(audit), 0.9, places=12)

    def test_non_audit_mapping_raises(self):
        with self.assertRaises(ValueError):
            logic.completeness_score({"foo": 1})


class TestMeetsCompleteness(unittest.TestCase):
    def test_unity_passes(self):
        self.assertTrue(logic.meets_completeness(1.0))

    def test_one_ulp_below_unity_is_absorbed(self):
        self.assertTrue(logic.meets_completeness(1.0 - 1e-12))

    def test_genuine_shortfall_fails(self):
        self.assertFalse(logic.meets_completeness(0.9))

    def test_score_above_one_raises(self):
        with self.assertRaises(ValueError):
            logic.meets_completeness(1.2)

    def test_negative_score_raises(self):
        with self.assertRaises(ValueError):
            logic.meets_completeness(-0.1)

    def test_non_numeric_score_raises(self):
        with self.assertRaises(ValueError):
            logic.meets_completeness("1.0")


class TestEvaluateProcedure(unittest.TestCase):
    def test_complete_procedure_is_compliant(self):
        result = logic.evaluate_procedure(
            full_record(), good_references(), good_sample()
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["completeness_score"], 1.0, places=12)

    def test_missing_item_makes_it_non_compliant(self):
        record = full_record()
        del record["measurement-method"]
        result = logic.evaluate_procedure(record, good_references(), good_sample())
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("measurement-method" in f for f in result["findings"])
        )

    def test_thin_item_makes_it_non_compliant(self):
        record = full_record()
        record["environmental-conditions"] = "ambient"
        result = logic.evaluate_procedure(record, good_references(), good_sample())
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("recorded-detail floor" in f for f in result["findings"])
        )

    def test_reference_defect_makes_it_non_compliant(self):
        refs = [{"id": "ECSS-E-ST-20-01C", "issue": None}]
        result = logic.evaluate_procedure(full_record(), refs, good_sample())
        self.assertFalse(result["compliant"])

    def test_uncategorized_entry_alone_stays_compliant(self):
        record = full_record()
        record["local-lab-annex"] = "site specific notes"
        result = logic.evaluate_procedure(record, good_references(), good_sample())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["uncategorized_items"], ["local-lab-annex"])

    def test_bad_sample_propagates_the_error(self):
        sample = good_sample()
        sample["thickness_mm"] = -0.2
        with self.assertRaises(ValueError):
            logic.evaluate_procedure(full_record(), good_references(), sample)


if __name__ == "__main__":
    unittest.main()
