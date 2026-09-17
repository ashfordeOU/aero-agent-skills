#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-Q-ST-60-03C Annex C device reuse file DRD.

Exercises scripts/q6003_device_reuse_file_drd_logic.py (stdlib unittest,
offline). Contract: section coverage, heritage item traceability,
evidence-reference resolution, heritage envelope comparison against the
new duty, change-record rigour, the aggregate disposition, and
ValueError on invalid input.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import q6003_device_reuse_file_drd_logic as reusedrd  # noqa: E402


FULL_FILE = {key: "content for %s" % key for key in reusedrd.REQUIRED_FILE_SECTIONS}

FULL_ITEMS = [
    {
        "element_id": "DEV-ASIC-1",
        "previous_application": "earlier payload controller",
        "qualification_state": "fully-qualified",
        "evidence_reference": "EVR-101",
    },
    {
        "element_id": "DEV-ASIC-2",
        "previous_application": "earlier bus interface",
        "qualification_state": "qualified-with-limitations",
        "evidence_reference": "EVR-102",
    },
]

REGISTER = ["EVR-101", "EVR-102", "EVR-103"]

ENVELOPE = {
    "max-junction-temperature-c": {"bound": 125.0, "direction": "max"},
    "min-junction-temperature-c": {"bound": -55.0, "direction": "min"},
    "total-ionising-dose-krad": {"bound": 100.0, "direction": "max"},
    "thermal-cycle-count": {"bound": 2000.0, "direction": "max"},
}

DUTY = {
    "max-junction-temperature-c": 110.0,
    "min-junction-temperature-c": -40.0,
    "total-ionising-dose-krad": 60.0,
    "thermal-cycle-count": 1500.0,
}

CHANGES = [
    {
        "change_id": "CHG-1",
        "impact_assessment": "package change assessed against thermal path",
        "verification_action": "re-run thermal cycling coupon",
    }
]


def full_spec(**overrides):
    spec = {
        "reuse_file": dict(FULL_FILE),
        "heritage_items": [dict(i) for i in FULL_ITEMS],
        "evidence_register": list(REGISTER),
        "heritage_envelope": {k: dict(v) for k, v in ENVELOPE.items()},
        "new_duty": dict(DUTY),
        "changes": [dict(c) for c in CHANGES],
    }
    spec.update(overrides)
    return spec


class MissingFileSectionsTest(unittest.TestCase):
    def test_complete_file_has_no_missing_sections(self):
        self.assertEqual(reusedrd.missing_file_sections(FULL_FILE), [])

    def test_blank_body_counts_as_absent(self):
        drafted = dict(FULL_FILE)
        drafted["reuse-justification"] = "\t "
        self.assertEqual(
            reusedrd.missing_file_sections(drafted), ["reuse-justification"]
        )

    def test_empty_file_returns_every_section_in_drd_order(self):
        self.assertEqual(
            reusedrd.missing_file_sections({}), list(reusedrd.REQUIRED_FILE_SECTIONS)
        )

    def test_non_mapping_file_raises(self):
        with self.assertRaises(ValueError):
            reusedrd.missing_file_sections(["introduction"])


class HeritageItemTest(unittest.TestCase):
    def test_complete_items_are_not_deficient(self):
        self.assertEqual(reusedrd.heritage_item_deficiencies(FULL_ITEMS), [])

    def test_missing_field_tagged(self):
        items = [dict(FULL_ITEMS[0])]
        del items[0]["previous_application"]
        records = reusedrd.heritage_item_deficiencies(items)
        self.assertEqual(records[0]["element_id"], "DEV-ASIC-1")
        self.assertIn("missing-previous-application", records[0]["deficiencies"])

    def test_weak_qualification_state_tagged(self):
        items = [dict(FULL_ITEMS[0])]
        items[0]["qualification_state"] = "development-only"
        records = reusedrd.heritage_item_deficiencies(items)
        self.assertIn("weak-qualification-state", records[0]["deficiencies"])

    def test_item_without_identifier_falls_back_to_its_index(self):
        records = reusedrd.heritage_item_deficiencies([{}])
        self.assertEqual(records[0]["element_id"], "items[0]")

    def test_unknown_qualification_state_raises(self):
        items = [dict(FULL_ITEMS[0])]
        items[0]["qualification_state"] = "probably-fine"
        with self.assertRaises(ValueError):
            reusedrd.heritage_item_deficiencies(items)

    def test_empty_item_list_raises(self):
        with self.assertRaises(ValueError):
            reusedrd.heritage_item_deficiencies([])


class EvidenceReferenceTest(unittest.TestCase):
    def test_resolved_references_are_clean(self):
        self.assertEqual(
            reusedrd.unresolved_evidence_references(FULL_ITEMS, REGISTER), []
        )

    def test_unresolved_reference_reported(self):
        items = [dict(FULL_ITEMS[0])]
        items[0]["evidence_reference"] = "EVR-999"
        self.assertEqual(
            reusedrd.unresolved_evidence_references(items, REGISTER), ["EVR-999"]
        )

    def test_duplicate_unresolved_reference_collapsed(self):
        items = [dict(FULL_ITEMS[0]), dict(FULL_ITEMS[1])]
        items[0]["evidence_reference"] = "EVR-999"
        items[1]["evidence_reference"] = "EVR-999"
        self.assertEqual(
            reusedrd.unresolved_evidence_references(items, REGISTER), ["EVR-999"]
        )

    def test_non_sequence_register_raises(self):
        with self.assertRaises(ValueError):
            reusedrd.unresolved_evidence_references(FULL_ITEMS, "EVR-101")


class EnvelopeTest(unittest.TestCase):
    def test_duty_inside_the_envelope_is_clean(self):
        record = reusedrd.envelope_exceedances(ENVELOPE, DUTY)
        self.assertEqual(record["exceeded"], [])
        self.assertEqual(record["undeclared"], [])

    def test_duty_exactly_on_an_upper_bound_is_inside_it(self):
        duty = dict(DUTY)
        duty["total-ionising-dose-krad"] = 100.0
        record = reusedrd.envelope_exceedances(ENVELOPE, duty)
        self.assertEqual(record["exceeded"], [])

    def test_duty_exactly_on_a_lower_bound_is_inside_it(self):
        duty = dict(DUTY)
        duty["min-junction-temperature-c"] = -55.0
        record = reusedrd.envelope_exceedances(ENVELOPE, duty)
        self.assertEqual(record["exceeded"], [])

    def test_upper_bound_exceedance_measured(self):
        duty = dict(DUTY)
        duty["total-ionising-dose-krad"] = 130.0
        record = reusedrd.envelope_exceedances(ENVELOPE, duty)
        self.assertEqual(len(record["exceeded"]), 1)
        self.assertEqual(record["exceeded"][0]["parameter"], "total-ionising-dose-krad")
        self.assertAlmostEqual(record["exceeded"][0]["exceeded_by"], 30.0, places=9)

    def test_lower_bound_exceedance_measured(self):
        duty = dict(DUTY)
        duty["min-junction-temperature-c"] = -65.0
        record = reusedrd.envelope_exceedances(ENVELOPE, duty)
        self.assertEqual(record["exceeded"][0]["parameter"], "min-junction-temperature-c")
        self.assertAlmostEqual(record["exceeded"][0]["exceeded_by"], 10.0, places=9)

    def test_magnitude_bound_applies_either_way(self):
        envelope = {"offset-drift-mv": {"bound": 5.0, "direction": "abs"}}
        clean = reusedrd.envelope_exceedances(envelope, {"offset-drift-mv": -5.0})
        self.assertEqual(clean["exceeded"], [])
        exceeded = reusedrd.envelope_exceedances(envelope, {"offset-drift-mv": -7.5})
        self.assertAlmostEqual(exceeded["exceeded"][0]["exceeded_by"], 2.5, places=9)

    def test_parameter_the_duty_never_declares_is_reported(self):
        duty = dict(DUTY)
        del duty["thermal-cycle-count"]
        record = reusedrd.envelope_exceedances(ENVELOPE, duty)
        self.assertEqual(record["undeclared"], ["thermal-cycle-count"])

    def test_duty_parameter_outside_the_envelope_raises(self):
        duty = dict(DUTY)
        duty["vibration-grms"] = 12.0
        with self.assertRaises(ValueError):
            reusedrd.envelope_exceedances(ENVELOPE, duty)

    def test_unknown_direction_raises(self):
        with self.assertRaises(ValueError):
            reusedrd.envelope_exceedances(
                {"p": {"bound": 1.0, "direction": "sideways"}}, {"p": 0.5}
            )

    def test_negative_magnitude_bound_raises(self):
        with self.assertRaises(ValueError):
            reusedrd.envelope_exceedances(
                {"p": {"bound": -1.0, "direction": "abs"}}, {"p": 0.5}
            )

    def test_empty_envelope_raises(self):
        with self.assertRaises(ValueError):
            reusedrd.envelope_exceedances({}, {})

    def test_non_real_duty_value_raises(self):
        with self.assertRaises(ValueError):
            reusedrd.envelope_exceedances(
                {"p": {"bound": 1.0, "direction": "max"}}, {"p": "hot"}
            )


class ChangeRecordTest(unittest.TestCase):
    def test_assessed_change_is_clean(self):
        self.assertEqual(reusedrd.unassessed_changes(CHANGES), [])

    def test_change_without_impact_assessment_tagged(self):
        changes = [dict(CHANGES[0])]
        del changes[0]["impact_assessment"]
        records = reusedrd.unassessed_changes(changes)
        self.assertIn("missing-impact-assessment", records[0]["deficiencies"])

    def test_change_without_verification_action_tagged(self):
        changes = [dict(CHANGES[0])]
        changes[0]["verification_action"] = "  "
        records = reusedrd.unassessed_changes(changes)
        self.assertIn("missing-verification-action", records[0]["deficiencies"])

    def test_empty_change_list_is_clean(self):
        self.assertEqual(reusedrd.unassessed_changes([]), [])

    def test_anonymous_change_raises(self):
        with self.assertRaises(ValueError):
            reusedrd.unassessed_changes([{"impact_assessment": "assessed"}])


class AggregateVerdictTest(unittest.TestCase):
    def test_clean_file_substantiates_the_reuse(self):
        verdict = reusedrd.assess_device_reuse_file_drd(full_spec())
        self.assertEqual(verdict["disposition"], "reuse-substantiated")
        self.assertEqual(verdict["findings"], [])

    def test_envelope_exceedance_alone_forces_a_delta_qualification(self):
        duty = dict(DUTY)
        duty["total-ionising-dose-krad"] = 150.0
        verdict = reusedrd.assess_device_reuse_file_drd(full_spec(new_duty=duty))
        self.assertEqual(verdict["disposition"], "delta-qualification-required")
        self.assertEqual(verdict["documentary_findings"], [])
        self.assertEqual(len(verdict["envelope_findings"]), 1)

    def test_documentary_defect_leaves_the_reuse_unsubstantiated(self):
        drafted = dict(FULL_FILE)
        del drafted["change-record"]
        verdict = reusedrd.assess_device_reuse_file_drd(full_spec(reuse_file=drafted))
        self.assertEqual(verdict["disposition"], "reuse-not-substantiated")
        self.assertIn("change-record", verdict["missing_sections"])

    def test_known_textbook_case_names_every_finding(self):
        drafted = dict(FULL_FILE)
        del drafted["verification-evidence"]
        items = [dict(FULL_ITEMS[0])]
        items[0]["evidence_reference"] = "EVR-999"
        items[0]["qualification_state"] = "development-only"
        duty = dict(DUTY)
        duty["max-junction-temperature-c"] = 140.0
        verdict = reusedrd.assess_device_reuse_file_drd(
            full_spec(
                reuse_file=drafted,
                heritage_items=items,
                new_duty=duty,
                changes=[{"change_id": "CHG-2"}],
            )
        )
        self.assertEqual(verdict["disposition"], "reuse-not-substantiated")
        self.assertIn("verification-evidence", verdict["missing_sections"])
        self.assertEqual(verdict["unresolved_evidence"], ["EVR-999"])
        self.assertEqual(len(verdict["envelope_findings"]), 1)
        self.assertGreater(len(verdict["findings"]), 4)

    def test_spec_missing_key_raises(self):
        spec = full_spec()
        del spec["changes"]
        with self.assertRaises(ValueError):
            reusedrd.assess_device_reuse_file_drd(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            reusedrd.assess_device_reuse_file_drd("reuse-file")


if __name__ == "__main__":
    unittest.main(verbosity=2)
