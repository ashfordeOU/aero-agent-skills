"""Contract tests for the clause 5.8.8 general GSE quality assurance logic."""

import unittest

from q20_gse_general_logic import (
    BASE_RECORDS,
    GSE_CATEGORIES,
    IDENTIFICATION_PATTERN,
    SAFETY_PROVISIONS,
    assess_gse_general,
    identification_findings,
    normalize_token,
    record_findings,
    required_records,
    retention_shortfall,
    safety_provision_findings,
    validate_item,
)

ITEM = {
    "register_mark": "GSEH-00412",
    "marked_on_item": "GSEH-00412",
    "category": "general-purpose",
}

SAFETY_ITEM = dict(ITEM, category="safety-critical")


def _spec(**overrides):
    item = dict(ITEM)
    item.update(overrides.pop("item", {}))
    spec = {
        "items": [item],
        "records_held": list(required_records(item)),
        "provisions_in_place": list(SAFETY_PROVISIONS),
        "applied_retention_years": 12.0,
        "service_life_years": 10.0,
    }
    spec.update(overrides)
    return spec


class NormalizeTokenTests(unittest.TestCase):
    def test_case_and_separator_folded(self):
        self.assertEqual(normalize_token("Usage_Log"), "usage-log")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(" ")


class ValidateItemTests(unittest.TestCase):
    def test_marks_are_folded_to_tokens(self):
        record = validate_item(ITEM)
        self.assertEqual(record["register_mark"], "gseh-00412")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(dict(ITEM, category="handy"))

    def test_missing_mark_rejected(self):
        with self.assertRaises(ValueError):
            validate_item({"category": "general-purpose"})

    def test_durability_defaults_to_true(self):
        self.assertTrue(validate_item(ITEM)["mark_is_durable"])

    def test_non_boolean_durability_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(dict(ITEM, mark_is_durable="yes"))

    def test_category_vocabulary_is_closed(self):
        self.assertEqual(len(GSE_CATEGORIES), 3)
        self.assertIn("safety-critical", GSE_CATEGORIES)


class IdentificationTests(unittest.TestCase):
    def test_well_formed_register_is_clean(self):
        self.assertEqual(identification_findings([ITEM]), [])

    def test_marking_scheme_accepts_a_type_prefix_and_serial(self):
        self.assertTrue(IDENTIFICATION_PATTERN.match("gseh-00412"))
        self.assertIsNone(IDENTIFICATION_PATTERN.match("412"))

    def test_malformed_mark_named(self):
        findings = identification_findings([dict(ITEM, register_mark="trolley 7", marked_on_item="trolley 7")])
        self.assertTrue(any("marking scheme" in f for f in findings))

    def test_repeated_mark_named(self):
        findings = identification_findings([ITEM, dict(ITEM)])
        self.assertTrue(any("more than one item" in f for f in findings))

    def test_non_durable_mark_is_a_finding(self):
        findings = identification_findings([dict(ITEM, mark_is_durable=False)])
        self.assertTrue(any("not applied durably" in f for f in findings))

    def test_unmarked_item_is_a_finding(self):
        item = dict(ITEM)
        del item["marked_on_item"]
        findings = identification_findings([item])
        self.assertTrue(any("carries no mark" in f for f in findings))

    def test_mark_disagreeing_with_the_register_is_a_finding(self):
        findings = identification_findings([dict(ITEM, marked_on_item="GSEH-00413")])
        self.assertTrue(any("while the register holds" in f for f in findings))

    def test_empty_register_rejected(self):
        with self.assertRaises(ValueError):
            identification_findings([])


class RecordTests(unittest.TestCase):
    def test_general_purpose_item_owes_the_base_set(self):
        self.assertEqual(required_records(ITEM), list(BASE_RECORDS))

    def test_safety_critical_item_owes_two_more_records(self):
        records = required_records(SAFETY_ITEM)
        self.assertIn("operator-training-record", records)
        self.assertEqual(len(records), len(BASE_RECORDS) + 2)

    def test_calibrated_item_owes_a_calibration_history(self):
        self.assertIn("calibration-history", required_records(dict(ITEM, calibrated=True)))

    def test_software_driven_item_owes_a_configuration_record(self):
        self.assertIn(
            "software-configuration-record", required_records(dict(ITEM, software_driven=True))
        )

    def test_missing_record_named(self):
        findings = record_findings(list(BASE_RECORDS[:-1]), list(BASE_RECORDS))
        self.assertEqual(len(findings), 1)
        self.assertIn(BASE_RECORDS[-1], findings[0])

    def test_case_difference_is_not_a_gap(self):
        self.assertEqual(record_findings(["Usage Log"], ["usage-log"]), [])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            record_findings("usage-log", ["usage-log"])


class RetentionTests(unittest.TestCase):
    def test_retention_beyond_life_plus_margin_has_no_shortfall(self):
        self.assertAlmostEqual(retention_shortfall(15.0, 10.0), 0.0, places=9)

    def test_retention_exactly_at_life_plus_margin_has_no_shortfall(self):
        self.assertAlmostEqual(retention_shortfall(12.0, 10.0), 0.0, places=9)

    def test_short_retention_reports_the_gap_in_years(self):
        self.assertAlmostEqual(retention_shortfall(7.0, 10.0), 5.0, places=9)

    def test_margin_is_adjustable(self):
        self.assertAlmostEqual(retention_shortfall(10.0, 10.0, margin_years=0.0), 0.0, places=9)

    def test_negative_retention_rejected(self):
        with self.assertRaises(ValueError):
            retention_shortfall(-1.0, 10.0)

    def test_non_numeric_life_rejected(self):
        with self.assertRaises(ValueError):
            retention_shortfall(10.0, "ten")


class SafetyProvisionTests(unittest.TestCase):
    def test_general_purpose_item_owes_no_safety_provision(self):
        self.assertEqual(safety_provision_findings(ITEM, []), [])

    def test_safety_critical_item_with_every_provision_is_clean(self):
        self.assertEqual(safety_provision_findings(SAFETY_ITEM, list(SAFETY_PROVISIONS)), [])

    def test_each_absent_provision_is_named_separately(self):
        findings = safety_provision_findings(SAFETY_ITEM, [])
        self.assertEqual(len(findings), len(SAFETY_PROVISIONS))

    def test_absent_hazard_notice_named(self):
        findings = safety_provision_findings(SAFETY_ITEM, list(SAFETY_PROVISIONS[:-1]))
        self.assertEqual(len(findings), 1)
        self.assertIn("point-of-use-hazard-notice", findings[0])

    def test_non_sequence_provisions_rejected(self):
        with self.assertRaises(ValueError):
            safety_provision_findings(SAFETY_ITEM, "written-operating-procedure")


class AssessGseGeneralTests(unittest.TestCase):
    def test_clean_item_is_fit_for_registered_use(self):
        result = assess_gse_general(_spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["fit_for_registered_use"])
        self.assertAlmostEqual(result["retention_shortfall_years"], 0.0, places=9)

    def test_safety_critical_item_without_provisions_is_not_fit(self):
        spec = _spec(item={"category": "safety-critical"}, provisions_in_place=[])
        spec["records_held"] = list(required_records(dict(ITEM, category="safety-critical")))
        result = assess_gse_general(spec)
        self.assertFalse(result["fit_for_registered_use"])
        self.assertEqual(len(result["safety_provision_findings"]), len(SAFETY_PROVISIONS))

    def test_retention_shortfall_is_reported_in_years(self):
        result = assess_gse_general(_spec(applied_retention_years=5.0))
        self.assertAlmostEqual(result["retention_shortfall_years"], 7.0, places=9)
        self.assertEqual(len(result["retention_findings"]), 1)

    def test_repeated_mark_across_the_register_is_caught(self):
        spec = _spec()
        spec["items"] = [dict(ITEM), dict(ITEM)]
        result = assess_gse_general(spec)
        self.assertFalse(result["fit_for_registered_use"])

    def test_empty_register_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_general(_spec(items=[]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["records_held"]
        with self.assertRaises(ValueError):
            assess_gse_general(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_general(["items"])

    def test_findings_accumulate_across_every_check(self):
        spec = _spec(
            item={"category": "safety-critical", "register_mark": "trolley", "marked_on_item": "cart"},
            records_held=[],
            provisions_in_place=[],
            applied_retention_years=1.0,
        )
        result = assess_gse_general(spec)
        self.assertGreaterEqual(len(result["findings"]), 15)


if __name__ == "__main__":
    unittest.main()
