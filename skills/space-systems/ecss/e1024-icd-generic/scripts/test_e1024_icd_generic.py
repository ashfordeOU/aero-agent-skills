#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-24C §5.7 generic ICD structure
and content check.

Exercises scripts/e1024_icd_generic_logic.py (stdlib unittest,
offline, deterministic). Contract: an ICD type outside the recognized
set raises; a blank interface_id raises; the section-presence check
returns all required section names absent from the input; the
identification-block check returns every required field absent or
empty; a requirement entry is flagged for each missing required field
and for an unrecognized verification method; duplicate requirement IDs
are detected; the configuration-control check returns missing authority
and revision-history fields; a fully populated record produces no
findings and is compliant; any single deficiency makes the record
non-compliant.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1024_icd_generic_logic as icd  # noqa: E402


def _compliant_icd():
    return {
        "icd_type": "EICD",
        "interface_id": "IF-SAT-GND-001",
        "sections_present": [
            "identification",
            "applicable_documents",
            "interface_description",
            "requirements",
            "verification",
            "configuration_control",
        ],
        "identification": {
            "document_number": "EICD-001",
            "revision": "A",
            "date": "2026-09-11",
            "project": "SAT-1",
            "interface_name": "RF Uplink",
            "provider": "Ground Station",
            "requester": "Satellite Comms",
        },
        "requirements": [
            {
                "id": "EICD-REQ-001",
                "statement": "The uplink carrier frequency shall be 2100 MHz.",
                "parent_requirement": "SYS-REQ-005",
                "provider_allocation": "Ground Station",
                "requester_allocation": "Satellite Comms",
                "verification_method": "test",
            }
        ],
        "configuration_control": {
            "authority": "Chief Systems Engineer",
            "revision_history": [
                {"rev": "A", "date": "2026-09-11", "description": "Initial issue"}
            ],
        },
    }


class ValidateIcdTypeTest(unittest.TestCase):
    def test_eicd_accepted(self):
        self.assertEqual(icd.validate_icd_type("EICD"), "EICD")

    def test_micd_accepted(self):
        self.assertEqual(icd.validate_icd_type("MICD"), "MICD")

    def test_ticd_accepted(self):
        self.assertEqual(icd.validate_icd_type("TICD"), "TICD")

    def test_generic_icd_accepted(self):
        self.assertEqual(icd.validate_icd_type("ICD"), "ICD")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            icd.validate_icd_type("XICD")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            icd.validate_icd_type("")


class ValidateInterfaceIdTest(unittest.TestCase):
    def test_valid_id_accepted(self):
        self.assertTrue(icd.validate_interface_id("IF-SAT-GND-001"))

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            icd.validate_interface_id("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            icd.validate_interface_id("   ")

    def test_none_raises(self):
        with self.assertRaises(ValueError):
            icd.validate_interface_id(None)


class CheckRequiredSectionsTest(unittest.TestCase):
    def test_all_sections_present_returns_empty(self):
        sections = [
            "identification",
            "applicable_documents",
            "interface_description",
            "requirements",
            "verification",
            "configuration_control",
        ]
        self.assertEqual(icd.check_required_sections(sections), [])

    def test_missing_single_section_reported(self):
        sections = [
            "identification",
            "applicable_documents",
            "interface_description",
            "requirements",
            "verification",
        ]
        missing = icd.check_required_sections(sections)
        self.assertIn("configuration_control", missing)
        self.assertEqual(len(missing), 1)

    def test_empty_input_returns_all_six(self):
        missing = icd.check_required_sections([])
        self.assertEqual(len(missing), 6)

    def test_extra_section_does_not_affect_result(self):
        sections = [
            "identification",
            "applicable_documents",
            "interface_description",
            "requirements",
            "verification",
            "configuration_control",
            "annex_a",
        ]
        self.assertEqual(icd.check_required_sections(sections), [])


class CheckIdentificationBlockTest(unittest.TestCase):
    def test_complete_block_returns_empty(self):
        block = {
            "document_number": "EICD-001",
            "revision": "A",
            "date": "2026-09-11",
            "project": "SAT-1",
            "interface_name": "RF Link",
            "provider": "Ground Station",
            "requester": "Satellite Comms",
        }
        self.assertEqual(icd.check_identification_block(block), [])

    def test_missing_provider_reported(self):
        block = {
            "document_number": "EICD-001",
            "revision": "A",
            "date": "2026-09-11",
            "project": "SAT-1",
            "interface_name": "RF Link",
            "requester": "Satellite Comms",
        }
        missing = icd.check_identification_block(block)
        self.assertIn("provider", missing)

    def test_empty_string_field_treated_as_missing(self):
        block = {
            "document_number": "",
            "revision": "A",
            "date": "2026-09-11",
            "project": "SAT-1",
            "interface_name": "RF Link",
            "provider": "Ground Station",
            "requester": "Satellite Comms",
        }
        missing = icd.check_identification_block(block)
        self.assertIn("document_number", missing)

    def test_non_dict_returns_all_fields(self):
        missing = icd.check_identification_block(None)
        self.assertEqual(len(missing), 7)


class CheckRequirementEntryTest(unittest.TestCase):
    def test_complete_requirement_returns_empty(self):
        req = {
            "id": "ICD-REQ-001",
            "statement": "The interface shall operate at 2.4 GHz.",
            "parent_requirement": "SYS-REQ-010",
            "provider_allocation": "Comms Subsystem",
            "requester_allocation": "Ground Segment",
            "verification_method": "test",
        }
        self.assertEqual(icd.check_requirement_entry(req), [])

    def test_analysis_method_accepted(self):
        req = {
            "id": "ICD-REQ-002",
            "statement": "The thermal flux at the interface shall be below 50 W/m2.",
            "parent_requirement": "SYS-REQ-020",
            "provider_allocation": "Thermal Subsystem",
            "requester_allocation": "Structure",
            "verification_method": "analysis",
        }
        self.assertEqual(icd.check_requirement_entry(req), [])

    def test_inspection_method_accepted(self):
        req = {
            "id": "ICD-REQ-003",
            "statement": "The connector shall be D-SUB 9-pin.",
            "parent_requirement": "SYS-REQ-030",
            "provider_allocation": "Mech Subsystem",
            "requester_allocation": "Integration",
            "verification_method": "inspection",
        }
        self.assertEqual(icd.check_requirement_entry(req), [])

    def test_review_of_design_method_accepted(self):
        req = {
            "id": "ICD-REQ-004",
            "statement": "The software protocol shall comply with CCSDS 133.0-B-2.",
            "parent_requirement": "SYS-REQ-040",
            "provider_allocation": "OBC",
            "requester_allocation": "Ground",
            "verification_method": "review_of_design",
        }
        self.assertEqual(icd.check_requirement_entry(req), [])

    def test_missing_parent_requirement_flagged(self):
        req = {
            "id": "ICD-REQ-005",
            "statement": "The voltage shall be 28 V.",
            "parent_requirement": "",
            "provider_allocation": "Power",
            "requester_allocation": "Payload",
            "verification_method": "test",
        }
        issues = icd.check_requirement_entry(req)
        self.assertIn("missing_field:parent_requirement", issues)

    def test_unknown_verification_method_flagged(self):
        req = {
            "id": "ICD-REQ-006",
            "statement": "The data rate shall be 10 Mbps.",
            "parent_requirement": "SYS-REQ-050",
            "provider_allocation": "Comms",
            "requester_allocation": "OBC",
            "verification_method": "prayer",
        }
        issues = icd.check_requirement_entry(req)
        self.assertIn("unknown_verification_method:prayer", issues)

    def test_missing_id_flagged(self):
        req = {
            "id": "",
            "statement": "The mass shall be below 1 kg.",
            "parent_requirement": "SYS-REQ-060",
            "provider_allocation": "Structure",
            "requester_allocation": "Integration",
            "verification_method": "test",
        }
        issues = icd.check_requirement_entry(req)
        self.assertIn("missing_field:id", issues)


class CheckUniqueIdsTest(unittest.TestCase):
    def test_unique_ids_returns_empty(self):
        reqs = [{"id": "R-001"}, {"id": "R-002"}, {"id": "R-003"}]
        self.assertEqual(icd.check_unique_ids(reqs), [])

    def test_single_duplicate_reported(self):
        reqs = [{"id": "R-001"}, {"id": "R-001"}, {"id": "R-002"}]
        dups = icd.check_unique_ids(reqs)
        self.assertIn("R-001", dups)
        self.assertNotIn("R-002", dups)

    def test_empty_list_returns_empty(self):
        self.assertEqual(icd.check_unique_ids([]), [])


class CheckConfigurationControlTest(unittest.TestCase):
    def test_complete_config_returns_empty(self):
        config = {
            "authority": "Chief Systems Engineer",
            "revision_history": [{"rev": "A", "date": "2026-09-11"}],
        }
        self.assertEqual(icd.check_configuration_control(config), [])

    def test_missing_authority_flagged(self):
        config = {
            "revision_history": [{"rev": "A"}],
        }
        missing = icd.check_configuration_control(config)
        self.assertIn("authority", missing)

    def test_empty_revision_history_flagged(self):
        config = {
            "authority": "Systems Engineer",
            "revision_history": [],
        }
        missing = icd.check_configuration_control(config)
        self.assertIn("revision_history", missing)

    def test_non_dict_returns_both_fields(self):
        missing = icd.check_configuration_control(None)
        self.assertIn("authority", missing)
        self.assertIn("revision_history", missing)


class IcdGenericReviewTest(unittest.TestCase):
    def test_compliant_icd_has_no_findings(self):
        review = icd.icd_generic_review(_compliant_icd())
        self.assertEqual(review["structure_findings"], [])
        self.assertEqual(review["identification_findings"], [])
        self.assertEqual(review["requirement_findings"], [])
        self.assertEqual(review["config_findings"], [])
        self.assertTrue(icd.is_icd_compliant(review))

    def test_unknown_icd_type_raises(self):
        doc = _compliant_icd()
        doc["icd_type"] = "XICD"
        with self.assertRaises(ValueError):
            icd.icd_generic_review(doc)

    def test_empty_interface_id_raises(self):
        doc = _compliant_icd()
        doc["interface_id"] = ""
        with self.assertRaises(ValueError):
            icd.icd_generic_review(doc)

    def test_missing_section_surfaces_structure_finding(self):
        doc = _compliant_icd()
        doc["sections_present"].remove("verification")
        review = icd.icd_generic_review(doc)
        self.assertIn("verification", review["structure_findings"])
        self.assertFalse(icd.is_icd_compliant(review))

    def test_missing_identification_field_surfaces_finding(self):
        doc = _compliant_icd()
        del doc["identification"]["requester"]
        review = icd.icd_generic_review(doc)
        self.assertIn("requester", review["identification_findings"])
        self.assertFalse(icd.is_icd_compliant(review))

    def test_requirement_without_parent_surfaces_finding(self):
        doc = _compliant_icd()
        doc["requirements"][0]["parent_requirement"] = ""
        review = icd.icd_generic_review(doc)
        self.assertTrue(review["requirement_findings"])
        self.assertFalse(icd.is_icd_compliant(review))

    def test_duplicate_requirement_id_surfaces_finding(self):
        doc = _compliant_icd()
        dup = dict(doc["requirements"][0])
        dup["statement"] = "Duplicate requirement statement."
        doc["requirements"].append(dup)
        review = icd.icd_generic_review(doc)
        dup_issues = [
            f for f in review["requirement_findings"]
            if "duplicate_id" in f.get("issues", [])
        ]
        self.assertTrue(dup_issues)
        self.assertFalse(icd.is_icd_compliant(review))

    def test_missing_config_authority_surfaces_finding(self):
        doc = _compliant_icd()
        doc["configuration_control"]["authority"] = ""
        review = icd.icd_generic_review(doc)
        self.assertIn("authority", review["config_findings"])
        self.assertFalse(icd.is_icd_compliant(review))

    def test_micd_type_accepted(self):
        doc = _compliant_icd()
        doc["icd_type"] = "MICD"
        review = icd.icd_generic_review(doc)
        self.assertTrue(icd.is_icd_compliant(review))

    def test_ticd_type_accepted(self):
        doc = _compliant_icd()
        doc["icd_type"] = "TICD"
        review = icd.icd_generic_review(doc)
        self.assertTrue(icd.is_icd_compliant(review))

    def test_input_not_mutated(self):
        doc = _compliant_icd()
        original_sections = list(doc["sections_present"])
        icd.icd_generic_review(doc)
        self.assertEqual(doc["sections_present"], original_sections)


if __name__ == "__main__":
    unittest.main()
