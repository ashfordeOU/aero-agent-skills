"""Contract tests for the clause 5.8.4.1 GSE end item data package logic."""

import unittest

from q20_gse_eidp_logic import (
    BASE_EIDP_SECTIONS,
    SECTION_STATES,
    assess_gse_eidp,
    nonconformance_findings,
    normalize_token,
    package_completeness,
    required_eidp_sections,
    section_findings,
    validate_gse_item,
    validate_sections,
)

ITEM = {"item_id": "GSE-2210", "designation": "handling-trolley"}


def _sections(names, state="approved", approver="quality-assurance"):
    return [{"name": n, "state": state, "approver": approver} for n in names]


def _spec(**overrides):
    item = dict(ITEM)
    item.update(overrides.pop("item", {}))
    spec = {
        "item": item,
        "sections": _sections(required_eidp_sections(item)),
        "open_nonconformances": [],
        "listed_nonconformances": [],
    }
    spec.update(overrides)
    return spec


class NormalizeTokenTests(unittest.TestCase):
    def test_case_and_separator_folded(self):
        self.assertEqual(normalize_token("Acceptance_Test Report"), "acceptance-test-report")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("   ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(17)


class ValidateItemTests(unittest.TestCase):
    def test_states_default_to_false(self):
        record = validate_gse_item(ITEM)
        self.assertFalse(record["pressurised"])
        self.assertEqual(record["item_id"], "gse-2210")

    def test_missing_designation_rejected(self):
        with self.assertRaises(ValueError):
            validate_gse_item({"item_id": "GSE-1"})

    def test_non_boolean_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_gse_item(dict(ITEM, lifting_duty="yes"))

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            validate_gse_item(["GSE-1"])


class RequiredSectionTests(unittest.TestCase):
    def test_plain_item_owes_the_base_set(self):
        self.assertEqual(required_eidp_sections(ITEM), list(BASE_EIDP_SECTIONS))

    def test_lifting_duty_adds_the_proof_load_certificate(self):
        sections = required_eidp_sections(dict(ITEM, lifting_duty=True))
        self.assertIn("proof-load-certificate", sections)

    def test_pressurised_item_adds_pressure_certification(self):
        sections = required_eidp_sections(dict(ITEM, pressurised=True))
        self.assertIn("pressure-system-certification", sections)

    def test_safety_critical_item_adds_its_assessment_record(self):
        sections = required_eidp_sections(dict(ITEM, safety_critical=True))
        self.assertIn("safety-critical-gse-assessment-record", sections)

    def test_every_state_at_once_adds_six_sections(self):
        sections = required_eidp_sections(
            dict(
                ITEM,
                pressurised=True,
                lifting_duty=True,
                software_driven=True,
                calibrated=True,
                safety_critical=True,
                limited_life_items=True,
            )
        )
        self.assertEqual(len(sections), len(BASE_EIDP_SECTIONS) + 6)


class ValidateSectionTests(unittest.TestCase):
    def test_duplicate_section_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections(
                _sections(["acceptance-test-report", "Acceptance Test Report"])
            )

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections([{"name": "statement-of-conformity", "state": "issued"}])

    def test_missing_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections([{"name": "statement-of-conformity"}])

    def test_state_vocabulary_is_closed_and_non_empty(self):
        self.assertIn("approved", SECTION_STATES)
        self.assertEqual(len(SECTION_STATES), 3)


class SectionFindingTests(unittest.TestCase):
    def test_complete_approved_package_is_clean(self):
        required = required_eidp_sections(ITEM)
        self.assertEqual(section_findings(_sections(required), required), [])

    def test_absent_section_named(self):
        required = required_eidp_sections(ITEM)
        findings = section_findings(_sections(required[:-1]), required)
        self.assertEqual(len(findings), 1)
        self.assertIn(required[-1], findings[0])

    def test_draft_section_blocks_delivery(self):
        required = required_eidp_sections(ITEM)
        sections = _sections(required)
        sections[0]["state"] = "draft"
        findings = section_findings(sections, required)
        self.assertTrue(any("draft" in f for f in findings))

    def test_approved_section_without_approver_is_a_finding(self):
        required = required_eidp_sections(ITEM)
        sections = _sections(required)
        sections[1]["approver"] = None
        findings = section_findings(sections, required)
        self.assertTrue(any("no approver" in f for f in findings))

    def test_superseded_section_is_a_finding(self):
        required = required_eidp_sections(ITEM)
        sections = _sections(required)
        sections[2]["state"] = "superseded"
        findings = section_findings(sections, required)
        self.assertTrue(any("superseded" in f for f in findings))

    def test_extra_sections_are_not_findings(self):
        required = required_eidp_sections(ITEM)
        sections = _sections(required + ["spares-list"])
        self.assertEqual(section_findings(sections, required), [])


class NonconformanceTests(unittest.TestCase):
    def test_listed_nonconformance_is_clean(self):
        self.assertEqual(nonconformance_findings(["NCR-12"], ["ncr-12"]), [])

    def test_unlisted_nonconformance_named(self):
        findings = nonconformance_findings(["NCR-12", "NCR-13"], ["NCR-12"])
        self.assertEqual(len(findings), 1)
        self.assertIn("ncr-13", findings[0])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            nonconformance_findings("NCR-12", [])


class CompletenessTests(unittest.TestCase):
    def test_full_package_is_unity(self):
        required = required_eidp_sections(ITEM)
        self.assertAlmostEqual(package_completeness(_sections(required), required), 1.0, places=9)

    def test_half_package_is_one_half(self):
        required = list(BASE_EIDP_SECTIONS)
        sections = _sections(required[:3])
        self.assertAlmostEqual(package_completeness(sections, required), 0.5, places=9)

    def test_draft_section_does_not_count_as_approved(self):
        required = list(BASE_EIDP_SECTIONS)
        sections = _sections(required)
        sections[0]["state"] = "draft"
        expected = (len(required) - 1) / float(len(required))
        self.assertAlmostEqual(package_completeness(sections, required), expected, places=9)

    def test_empty_required_set_rejected(self):
        with self.assertRaises(ValueError):
            package_completeness([], [])


class AssessGseEidpTests(unittest.TestCase):
    def test_clean_package_is_releasable(self):
        result = assess_gse_eidp(_spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["package_releasable"])
        self.assertAlmostEqual(result["completeness"], 1.0, places=9)

    def test_lifting_item_without_proof_load_is_held(self):
        item = dict(ITEM, lifting_duty=True)
        spec = _spec(item={"lifting_duty": True})
        spec["sections"] = _sections(list(BASE_EIDP_SECTIONS))
        result = assess_gse_eidp(spec)
        self.assertFalse(result["package_releasable"])
        self.assertTrue(any("proof-load-certificate" in f for f in result["findings"]))
        self.assertIn("proof-load-certificate", required_eidp_sections(item))

    def test_unlisted_nonconformance_holds_the_package(self):
        spec = _spec(open_nonconformances=["NCR-77"], listed_nonconformances=[])
        result = assess_gse_eidp(spec)
        self.assertFalse(result["package_releasable"])
        self.assertEqual(len(result["nonconformance_findings"]), 1)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["sections"]
        with self.assertRaises(ValueError):
            assess_gse_eidp(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_eidp(["item"])

    def test_findings_accumulate_across_every_check(self):
        spec = _spec(
            item={"pressurised": True, "calibrated": True, "safety_critical": True},
            open_nonconformances=["NCR-1", "NCR-2"],
            listed_nonconformances=[],
        )
        spec["sections"] = _sections(list(BASE_EIDP_SECTIONS)[:2], state="draft")
        result = assess_gse_eidp(spec)
        self.assertGreaterEqual(len(result["findings"]), 9)
        self.assertLess(result["completeness"], 0.5)


if __name__ == "__main__":
    unittest.main()
