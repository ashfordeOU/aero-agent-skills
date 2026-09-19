"""Contract tests for the ECSS-E-ST-33-01 clause 4.2.2 specification-register logic."""

import datetime
import unittest

from e3301_specific_mechanism_specification_sms_logic import (
    AGREEMENT_ABSENT,
    AGREEMENT_AGREED,
    AGREEMENT_LATE,
    AGREEMENT_MISDATED,
    AGREEMENT_PENDING,
    ANNEX_A_SECTIONS,
    agreement_state,
    assess_specification_register,
    content_completeness,
    map_register,
    missing_sections,
    parse_date,
    validate_mechanism,
    validate_specification,
)

MECHANISMS = [
    {"id": "MECH-SADM", "name": "solar array drive mechanism"},
    {"id": "MECH-HDRM", "name": "hold-down and release mechanism"},
]


def specification(**overrides):
    """Return a complete, agreed specification for the drive mechanism."""
    document = {
        "id": "SMS-SADM-01",
        "mechanism_ids": ["MECH-SADM"],
        "issue": "1",
        "issue_date": "2026-02-01",
        "sections": list(ANNEX_A_SECTIONS),
        "customer_agreement": {
            "status": "agreed",
            "date": "2026-03-10",
            "reference": "CUST-LTR-114",
        },
    }
    document.update(overrides)
    return document


def second_specification(**overrides):
    """Return a complete, agreed specification for the release mechanism."""
    document = specification(
        id="SMS-HDRM-01",
        mechanism_ids=["MECH-HDRM"],
    )
    document.update(overrides)
    return document


class DateTests(unittest.TestCase):
    def test_iso_string_parses(self):
        self.assertEqual(parse_date("2026-03-10"), datetime.date(2026, 3, 10))

    def test_date_object_passes_through(self):
        value = datetime.date(2026, 3, 10)
        self.assertEqual(parse_date(value), value)

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("10/03/2026")

    def test_empty_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("")


class ValidationTests(unittest.TestCase):
    def test_mechanism_is_normalised(self):
        record = validate_mechanism({"id": " MECH-SADM ", "name": "drive"})
        self.assertEqual(record["id"], "MECH-SADM")

    def test_mechanism_without_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_mechanism({"id": "MECH-SADM"})

    def test_specification_is_normalised(self):
        record = validate_specification(specification())
        self.assertEqual(record["mechanism_ids"], ["MECH-SADM"])
        self.assertEqual(len(record["sections"]), len(ANNEX_A_SECTIONS))

    def test_specification_without_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification(specification(mechanism_ids=[]))

    def test_specification_repeating_a_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification(
                specification(mechanism_ids=["MECH-SADM", "MECH-SADM"]))

    def test_unrecognised_section_heading_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification(specification(sections=["cost-breakdown"]))

    def test_non_mapping_agreement_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification(specification(customer_agreement="agreed"))


class ContentTests(unittest.TestCase):
    def test_complete_specification_misses_nothing(self):
        self.assertEqual(missing_sections(specification()), [])

    def test_complete_specification_scores_one(self):
        self.assertAlmostEqual(content_completeness(specification()), 1.0, places=9)

    def test_missing_headings_are_reported_in_annex_order(self):
        partial = list(ANNEX_A_SECTIONS)[:6]
        absent = missing_sections(specification(sections=partial))
        self.assertEqual(absent, list(ANNEX_A_SECTIONS)[6:])

    def test_partial_specification_scores_the_fraction(self):
        partial = list(ANNEX_A_SECTIONS)[:6]
        value = content_completeness(specification(sections=partial))
        self.assertAlmostEqual(value, 6.0 / len(ANNEX_A_SECTIONS), places=9)

    def test_empty_specification_scores_zero(self):
        self.assertAlmostEqual(content_completeness(specification(sections=[])), 0.0,
                               places=9)

    def test_repeated_heading_does_not_inflate_the_score(self):
        doubled = list(ANNEX_A_SECTIONS)[:5] + list(ANNEX_A_SECTIONS)[:5]
        value = content_completeness(specification(sections=doubled))
        self.assertAlmostEqual(value, 5.0 / len(ANNEX_A_SECTIONS), places=9)


class AgreementTests(unittest.TestCase):
    def test_recorded_agreement_is_agreed(self):
        self.assertEqual(agreement_state(specification()), AGREEMENT_AGREED)

    def test_absent_agreement_is_not_submitted(self):
        self.assertEqual(
            agreement_state(specification(customer_agreement=None)), AGREEMENT_ABSENT)

    def test_non_agreed_status_is_pending(self):
        document = specification(customer_agreement={"status": "under review"})
        self.assertEqual(agreement_state(document), AGREEMENT_PENDING)

    def test_agreement_before_the_issue_is_misdated(self):
        document = specification(customer_agreement={
            "status": "agreed", "date": "2026-01-05", "reference": "CUST-LTR-100"})
        self.assertEqual(agreement_state(document), AGREEMENT_MISDATED)

    def test_agreement_on_the_issue_date_is_accepted(self):
        document = specification(customer_agreement={
            "status": "agreed", "date": "2026-02-01", "reference": "CUST-LTR-101"})
        self.assertEqual(agreement_state(document), AGREEMENT_AGREED)

    def test_agreement_after_the_milestone_is_late(self):
        state = agreement_state(specification(), milestone_date="2026-03-01")
        self.assertEqual(state, AGREEMENT_LATE)

    def test_agreement_on_the_milestone_date_is_accepted(self):
        state = agreement_state(specification(), milestone_date="2026-03-10")
        self.assertEqual(state, AGREEMENT_AGREED)

    def test_agreed_without_a_date_rejected(self):
        document = specification(customer_agreement={
            "status": "agreed", "reference": "CUST-LTR-102"})
        with self.assertRaises(ValueError):
            agreement_state(document)

    def test_agreed_without_a_reference_rejected(self):
        document = specification(customer_agreement={
            "status": "agreed", "date": "2026-03-10"})
        with self.assertRaises(ValueError):
            agreement_state(document)


class RegisterMappingTests(unittest.TestCase):
    def test_one_specification_per_mechanism_maps_cleanly(self):
        register = map_register(MECHANISMS, [specification(), second_specification()])
        self.assertEqual(register["findings"], [])
        self.assertEqual(register["mapping"]["MECH-SADM"], ["SMS-SADM-01"])

    def test_mechanism_without_a_specification_is_a_finding(self):
        register = map_register(MECHANISMS, [specification()])
        self.assertTrue(any("MECH-HDRM" in f for f in register["findings"]))

    def test_two_specifications_for_one_mechanism_is_a_finding(self):
        extra = specification(id="SMS-SADM-02")
        register = map_register(MECHANISMS, [specification(), extra, second_specification()])
        self.assertTrue(any("covered by 2 specifications" in f for f in register["findings"]))

    def test_specification_spanning_two_mechanisms_is_a_finding(self):
        shared = specification(mechanism_ids=["MECH-SADM", "MECH-HDRM"])
        register = map_register(MECHANISMS, [shared])
        self.assertTrue(any("covers 2 mechanisms" in f for f in register["findings"]))

    def test_specification_for_an_unknown_mechanism_is_a_finding(self):
        stray = specification(id="SMS-XX-01", mechanism_ids=["MECH-GHOST"])
        register = map_register(MECHANISMS, [specification(), second_specification(), stray])
        self.assertTrue(any("not in the register" in f for f in register["findings"]))

    def test_repeated_mechanism_identifier_rejected(self):
        with self.assertRaises(ValueError):
            map_register(MECHANISMS + [MECHANISMS[0]], [specification()])

    def test_repeated_specification_identifier_rejected(self):
        with self.assertRaises(ValueError):
            map_register(MECHANISMS, [specification(), specification()])

    def test_empty_mechanism_list_rejected(self):
        with self.assertRaises(ValueError):
            map_register([], [specification()])


class RegisterAssessmentTests(unittest.TestCase):
    def test_clean_register_is_compliant(self):
        result = assess_specification_register({
            "mechanisms": MECHANISMS,
            "specifications": [specification(), second_specification()],
        })
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)

    def test_missing_specification_halves_the_coverage(self):
        result = assess_specification_register({
            "mechanisms": MECHANISMS,
            "specifications": [specification()],
        })
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["coverage_fraction"], 0.5, places=9)

    def test_incomplete_content_blocks_the_specification(self):
        partial = specification(sections=list(ANNEX_A_SECTIONS)[:4])
        result = assess_specification_register({
            "mechanisms": MECHANISMS,
            "specifications": [partial, second_specification()],
        })
        self.assertFalse(result["compliant"])
        self.assertFalse(result["records"][0]["ready"])
        self.assertIn("SMS-SADM-01", result["unused"])

    def test_pending_agreement_blocks_the_specification(self):
        pending = specification(customer_agreement={"status": "in work"})
        result = assess_specification_register({
            "mechanisms": MECHANISMS,
            "specifications": [pending, second_specification()],
        })
        self.assertFalse(result["compliant"])
        self.assertEqual(result["records"][0]["agreement_state"], AGREEMENT_PENDING)

    def test_milestone_makes_a_late_agreement_a_finding(self):
        result = assess_specification_register({
            "mechanisms": MECHANISMS,
            "specifications": [specification(), second_specification()],
            "milestone_date": "2026-03-01",
        })
        self.assertFalse(result["compliant"])
        self.assertTrue(any("agreed-after-the-milestone" in f for f in result["findings"]))

    def test_record_carries_the_completeness_fraction(self):
        partial = specification(sections=list(ANNEX_A_SECTIONS)[:5])
        result = assess_specification_register({
            "mechanisms": MECHANISMS,
            "specifications": [partial, second_specification()],
        })
        self.assertAlmostEqual(
            result["records"][0]["content_completeness"],
            5.0 / len(ANNEX_A_SECTIONS),
            places=9,
        )

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_specification_register({"mechanisms": MECHANISMS})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_specification_register(["mechanisms"])

    def test_annex_a_list_has_ten_headings(self):
        self.assertEqual(len(ANNEX_A_SECTIONS), 10)


if __name__ == "__main__":
    unittest.main()
