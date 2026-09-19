#!/usr/bin/env python3
"""Gate 3 contract test for q2007-specimen.

stdlib unittest, offline, deterministic. Run:
    python3 test_q2007_specimen.py
"""

import unittest

from q2007_specimen_logic import (
    SPECIMEN_ACCEPTED,
    SPECIMEN_ACCEPTED_WITH_NONCONFORMANCE,
    SPECIMEN_QUARANTINED,
    assess_specimen_control,
    configuration_matches,
    custody_chain_findings,
    identification_findings,
    mass_within_allowance,
    missing_documents,
    normalise,
    specimen_disposition,
    validate_custody_events,
    validate_specimen_record,
)

ALL_DOCUMENTS = [
    "shipping-note",
    "handling-instruction",
    "declared-configuration-list",
]


def good_chain():
    return [
        {"time_s": 0.0, "released_by": "courier", "received_by": "goods inwards"},
        {"time_s": 3600.0, "released_by": "goods inwards", "received_by": "bay 3 lead"},
    ]


def good_specimen(**over):
    record = {
        "identifier": "CU-5512 serial 004",
        "declared_configuration": "flight build, harness dress B",
        "as_received_configuration": "Flight build,  harness dress B",
        "receipt_inspection_performed": True,
        "damage_observed": False,
        "protective_packaging_intact": True,
        "mass_kg": 12.4,
        "declared_mass_kg": 12.5,
        "mass_allowance_kg": 0.2,
        "accompanying_documents": list(ALL_DOCUMENTS),
    }
    record.update(over)
    return record


class TestRecordValidation(unittest.TestCase):
    def test_good_record_normalizes(self):
        specimen = validate_specimen_record(good_specimen())
        self.assertEqual(specimen["identifier"], "CU-5512 serial 004")
        self.assertAlmostEqual(specimen["mass_kg"], 12.4, places=9)

    def test_blank_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen_record(good_specimen(identifier="   "))

    def test_missing_as_received_configuration_is_rejected(self):
        record = good_specimen()
        del record["as_received_configuration"]
        with self.assertRaises(ValueError):
            validate_specimen_record(record)

    def test_non_boolean_damage_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen_record(good_specimen(damage_observed="none seen"))

    def test_zero_mass_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen_record(good_specimen(mass_kg=0.0))

    def test_documents_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_specimen_record(good_specimen(accompanying_documents="all three"))


class TestIdentification(unittest.TestCase):
    def test_a_unique_marking_has_no_findings(self):
        self.assertEqual(identification_findings("CU-5512 serial 004", []), [])

    def test_a_marking_already_in_the_register_is_a_finding(self):
        findings = identification_findings(
            "CU-5512 serial 004", ["CU-5512 SERIAL 004", "CU-5512 serial 009"]
        )
        self.assertEqual(len(findings), 1)

    def test_a_placeholder_marking_is_a_finding(self):
        self.assertEqual(len(identification_findings("TBD", [])), 1)

    def test_a_blank_marking_is_rejected(self):
        with self.assertRaises(ValueError):
            identification_findings("  ", [])

    def test_a_non_sequence_register_is_rejected(self):
        with self.assertRaises(ValueError):
            identification_findings("CU-5512 serial 004", "CU-5512 serial 004")


class TestConfigurationAndMass(unittest.TestCase):
    def test_case_and_spacing_are_not_a_configuration_difference(self):
        self.assertTrue(configuration_matches("Build A  rev 2", "build a rev 2"))

    def test_a_different_build_does_not_match(self):
        self.assertFalse(configuration_matches("Build A rev 2", "Build A rev 3"))

    def test_normalise_collapses_whitespace(self):
        self.assertEqual(normalise("  Build   A  "), "build a")

    def test_mass_inside_the_allowance_passes(self):
        self.assertTrue(mass_within_allowance(12.4, 12.5, 0.2))

    def test_mass_exactly_on_the_allowance_passes(self):
        self.assertTrue(mass_within_allowance(12.3, 12.5, 0.2))

    def test_mass_outside_the_allowance_fails(self):
        self.assertFalse(mass_within_allowance(12.0, 12.5, 0.2))

    def test_zero_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            mass_within_allowance(12.4, 12.5, 0.0)


class TestDocuments(unittest.TestCase):
    def test_a_full_set_leaves_nothing_missing(self):
        self.assertEqual(missing_documents(ALL_DOCUMENTS), [])

    def test_an_absent_document_is_listed(self):
        self.assertEqual(
            missing_documents(["shipping-note", "handling-instruction"]),
            ["declared-configuration-list"],
        )

    def test_document_names_are_matched_case_insensitively(self):
        self.assertEqual(missing_documents(["SHIPPING-NOTE  ", "Handling-Instruction",
                                            "Declared-Configuration-List"]), [])

    def test_a_non_sequence_document_set_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_documents("shipping-note")


class TestCustody(unittest.TestCase):
    def test_a_connected_chain_has_no_findings(self):
        self.assertEqual(custody_chain_findings(good_chain()), [])

    def test_a_broken_join_is_a_finding(self):
        chain = good_chain()
        chain[1]["released_by"] = "stores"
        self.assertEqual(len(custody_chain_findings(chain)), 1)

    def test_out_of_order_handovers_are_rejected(self):
        chain = good_chain()
        chain[1]["time_s"] = -10.0
        with self.assertRaises(ValueError):
            validate_custody_events(chain)

    def test_two_handovers_at_the_same_instant_are_rejected(self):
        chain = good_chain()
        chain[1]["time_s"] = chain[0]["time_s"]
        with self.assertRaises(ValueError):
            validate_custody_events(chain)

    def test_a_handover_without_a_receiver_is_rejected(self):
        chain = good_chain()
        chain[0]["received_by"] = ""
        with self.assertRaises(ValueError):
            validate_custody_events(chain)

    def test_an_empty_chain_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_custody_events([])


class TestDisposition(unittest.TestCase):
    def test_a_clean_intake_is_accepted(self):
        self.assertEqual(specimen_disposition([], [], []), SPECIMEN_ACCEPTED)

    def test_a_nonconformance_still_accepts_the_item(self):
        self.assertEqual(
            specimen_disposition([], ["missing shipping note"], []),
            SPECIMEN_ACCEPTED_WITH_NONCONFORMANCE,
        )

    def test_a_quarantine_reason_overrides_everything(self):
        self.assertEqual(
            specimen_disposition([], ["missing shipping note"], ["damage on receipt"]),
            SPECIMEN_QUARANTINED,
        )

    def test_a_non_sequence_finding_list_is_rejected(self):
        with self.assertRaises(ValueError):
            specimen_disposition("none", [], [])


class TestFullIntake(unittest.TestCase):
    def test_a_clean_item_is_accepted(self):
        report = assess_specimen_control(good_specimen(), [], good_chain())
        self.assertEqual(report["disposition"], SPECIMEN_ACCEPTED)
        self.assertEqual(report["nonconformances"], [])
        self.assertTrue(report["configuration_matches"])

    def test_an_undeclared_build_raises_a_nonconformance(self):
        report = assess_specimen_control(
            good_specimen(as_received_configuration="flight build, harness dress C"),
            [],
            good_chain(),
        )
        self.assertEqual(report["disposition"], SPECIMEN_ACCEPTED_WITH_NONCONFORMANCE)
        self.assertFalse(report["configuration_matches"])

    def test_an_out_of_allowance_mass_raises_a_nonconformance(self):
        report = assess_specimen_control(good_specimen(mass_kg=13.5), [], good_chain())
        self.assertFalse(report["mass_within_allowance"])
        self.assertEqual(report["disposition"], SPECIMEN_ACCEPTED_WITH_NONCONFORMANCE)

    def test_a_missing_document_raises_a_nonconformance(self):
        report = assess_specimen_control(
            good_specimen(accompanying_documents=["shipping-note"]), [], good_chain()
        )
        self.assertEqual(len(report["missing_documents"]), 2)
        self.assertEqual(report["disposition"], SPECIMEN_ACCEPTED_WITH_NONCONFORMANCE)

    def test_damage_on_receipt_quarantines_the_item(self):
        report = assess_specimen_control(
            good_specimen(damage_observed=True), [], good_chain()
        )
        self.assertEqual(report["disposition"], SPECIMEN_QUARANTINED)

    def test_a_skipped_receipt_inspection_quarantines_the_item(self):
        report = assess_specimen_control(
            good_specimen(receipt_inspection_performed=False), [], good_chain()
        )
        self.assertEqual(report["disposition"], SPECIMEN_QUARANTINED)

    def test_broken_packaging_alone_does_not_quarantine(self):
        report = assess_specimen_control(
            good_specimen(protective_packaging_intact=False), [], good_chain()
        )
        self.assertEqual(report["disposition"], SPECIMEN_ACCEPTED_WITH_NONCONFORMANCE)

    def test_a_broken_custody_chain_quarantines_the_item(self):
        chain = good_chain()
        chain[1]["released_by"] = "stores"
        report = assess_specimen_control(good_specimen(), [], chain)
        self.assertEqual(report["disposition"], SPECIMEN_QUARANTINED)
        self.assertEqual(len(report["custody_findings"]), 1)

    def test_a_duplicate_marking_is_reported_against_the_register(self):
        report = assess_specimen_control(
            good_specimen(), ["cu-5512 serial 004"], good_chain()
        )
        self.assertEqual(len(report["identification_findings"]), 1)
        self.assertEqual(report["disposition"], SPECIMEN_ACCEPTED_WITH_NONCONFORMANCE)

    def test_intake_propagates_a_record_error(self):
        with self.assertRaises(ValueError):
            assess_specimen_control(good_specimen(declared_mass_kg=0.0), [], good_chain())


if __name__ == "__main__":
    unittest.main()
