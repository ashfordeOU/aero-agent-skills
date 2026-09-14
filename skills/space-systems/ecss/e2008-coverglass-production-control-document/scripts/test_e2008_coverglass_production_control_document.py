#!/usr/bin/env python3
"""Contract test for the coverglass production control document (offline).

Walks the clause workflow step by step: the readings a control
parameter owes -- does its band bracket the nominal, is it tight enough
to control anything, is it still wider than the measurement behind it
can resolve -- the standing of qualification evidence against the date
the document was issued, the four parts of a declared process entry,
coverage against the processes a coverglass genuinely depends on, and
the roll-up into one document verdict. This is the gate 3 review
evidence for the leaf.
"""

import copy
import unittest

from e2008_coverglass_production_control_document_logic import (
    DOCUMENT_ACCEPTED,
    DOCUMENT_INCOMPLETE,
    ENTRY_ACCEPTED,
    ENTRY_DOCUMENT_MISSING,
    ENTRY_EVIDENCE_MISSING,
    ENTRY_EVIDENCE_PREDATES_DOCUMENT,
    ENTRY_PARAMETER_DEFECT,
    ENTRY_PARAMETERS_MISSING,
    PARAMETER_BAND_BELOW_RESOLUTION,
    PARAMETER_BAND_EXCLUDES_NOMINAL,
    PARAMETER_BAND_TOO_WIDE,
    PARAMETER_CONTROLLED,
    REQUIRED_COVERGLASS_PROCESSES,
    assess_control_parameter,
    assess_process_entry,
    assess_production_control_document,
    evidence_standing,
    process_coverage,
    validate_identifier,
    validate_iso_date,
    validate_positive,
    validate_real,
)

ISSUE_DATE = "2026-01-15"
CAMPAIGN_START = "2026-02-01"

SOUND_PARAMETER = {
    "name": "bath-temperature-k",
    "nominal": 320.0,
    "lower": 315.0,
    "upper": 325.0,
    "measurement_uncertainty": 0.5,
}


def _parameter(**overrides):
    record = copy.deepcopy(SOUND_PARAMETER)
    record.update(overrides)
    return record


def _entry(process, **overrides):
    record = {
        "process": process,
        "controlling_document": "PD-%s-01" % process.upper(),
        "control_parameters": [_parameter()],
        "evidence_reference": "QR-%s-01" % process.upper(),
        "evidence_date": "2026-03-04",
    }
    record.update(copy.deepcopy(overrides))
    return record


def _full_entries():
    return [_entry(name) for name in sorted(REQUIRED_COVERGLASS_PROCESSES)]


def _spec(entries=None, **overrides):
    record = {
        "document_id": "CG-PCD-001",
        "issue_date": ISSUE_DATE,
        "campaign_start_date": CAMPAIGN_START,
        "entries": _full_entries() if entries is None else entries,
    }
    record.update(copy.deepcopy(overrides))
    return record


class ValidationTests(unittest.TestCase):
    def test_an_identifier_is_trimmed(self):
        self.assertEqual(validate_identifier("  PD-01  ", "doc"), "PD-01")

    def test_a_blank_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("   ", "doc")

    def test_an_iso_date_is_read(self):
        self.assertEqual(
            validate_iso_date("2026-01-15", "issue").isoformat(), "2026-01-15"
        )

    def test_a_malformed_date_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_iso_date("15 January 2026", "issue")

    def test_a_non_finite_number_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_real(float("inf"), "nominal")

    def test_a_non_positive_number_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "nominal")

    def test_a_boolean_is_not_a_number(self):
        with self.assertRaises(ValueError):
            validate_real(True, "nominal")


class ControlParameterTests(unittest.TestCase):
    def test_a_sound_parameter_is_controlled(self):
        result = assess_control_parameter(_parameter())
        self.assertEqual(result["status"], PARAMETER_CONTROLLED)
        self.assertEqual(result["findings"], [])

    def test_a_band_that_excludes_its_own_nominal_is_caught(self):
        result = assess_control_parameter(
            _parameter(nominal=340.0, lower=315.0, upper=325.0)
        )
        self.assertEqual(result["status"], PARAMETER_BAND_EXCLUDES_NOMINAL)
        self.assertFalse(result["brackets_nominal"])

    def test_a_band_wider_than_the_cap_is_a_range_and_not_a_tolerance(self):
        result = assess_control_parameter(
            _parameter(nominal=100.0, lower=40.0, upper=160.0)
        )
        self.assertEqual(result["status"], PARAMETER_BAND_TOO_WIDE)

    def test_a_band_exactly_at_the_width_cap_is_within_it(self):
        result = assess_control_parameter(
            _parameter(
                nominal=0.3,
                lower=0.225,
                upper=0.375,
                measurement_uncertainty=0.01,
            )
        )
        self.assertAlmostEqual(result["relative_half_width"], 0.25, places=9)
        self.assertTrue(result["within_width_cap"])
        self.assertEqual(result["status"], PARAMETER_CONTROLLED)

    def test_a_band_narrower_than_the_measurement_can_see_is_caught(self):
        result = assess_control_parameter(
            _parameter(measurement_uncertainty=4.0)
        )
        self.assertEqual(result["status"], PARAMETER_BAND_BELOW_RESOLUTION)
        self.assertFalse(result["resolvable"])

    def test_an_uncertainty_ratio_exactly_at_the_floor_is_accepted(self):
        result = assess_control_parameter(
            _parameter(
                nominal=320.0, lower=318.0, upper=322.0, measurement_uncertainty=0.5
            )
        )
        self.assertAlmostEqual(result["uncertainty_ratio"], 4.0, places=9)
        self.assertTrue(result["resolvable"])
        self.assertEqual(result["status"], PARAMETER_CONTROLLED)

    def test_an_inverted_band_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_control_parameter(_parameter(lower=325.0, upper=315.0))

    def test_a_zero_measurement_uncertainty_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_control_parameter(_parameter(measurement_uncertainty=0.0))

    def test_a_parameter_with_no_nominal_is_rejected(self):
        record = _parameter()
        del record["nominal"]
        with self.assertRaises(ValueError):
            assess_control_parameter(record)

    def test_a_policy_may_relax_the_uncertainty_ratio(self):
        thin = _parameter(measurement_uncertainty=2.5)
        strict = assess_control_parameter(thin)
        relaxed = assess_control_parameter(thin, {"min_uncertainty_ratio": 2.0})
        self.assertEqual(strict["status"], PARAMETER_BAND_BELOW_RESOLUTION)
        self.assertEqual(relaxed["status"], PARAMETER_CONTROLLED)


class EvidenceStandingTests(unittest.TestCase):
    def test_evidence_after_the_issue_discharges_the_commitment(self):
        result = evidence_standing("QR-1", "2026-03-04", ISSUE_DATE)
        self.assertTrue(result["postdates_document"])
        self.assertEqual(result["findings"], [])

    def test_evidence_on_the_issue_date_discharges_the_commitment(self):
        result = evidence_standing("QR-1", ISSUE_DATE, ISSUE_DATE)
        self.assertTrue(result["postdates_document"])

    def test_evidence_older_than_the_document_discharges_nothing(self):
        result = evidence_standing("QR-1", "2025-11-02", ISSUE_DATE)
        self.assertFalse(result["postdates_document"])
        self.assertTrue(result["findings"])

    def test_an_entry_that_cites_no_evidence_is_reported(self):
        result = evidence_standing(None, None, ISSUE_DATE)
        self.assertFalse(result["present"])
        self.assertTrue(result["findings"])

    def test_a_malformed_evidence_date_is_rejected(self):
        with self.assertRaises(ValueError):
            evidence_standing("QR-1", "March 2026", ISSUE_DATE)


class ProcessEntryTests(unittest.TestCase):
    def test_a_sound_entry_is_accepted(self):
        result = assess_process_entry(_entry("cleaning"), ISSUE_DATE)
        self.assertEqual(result["status"], ENTRY_ACCEPTED)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["criticality"], "qualification-critical")

    def test_naming_a_process_without_its_controlling_document_is_half_a_declaration(
        self,
    ):
        result = assess_process_entry(
            _entry("cleaning", controlling_document="  "), ISSUE_DATE
        )
        self.assertEqual(result["status"], ENTRY_DOCUMENT_MISSING)

    def test_an_entry_with_no_control_parameters_holds_nothing(self):
        result = assess_process_entry(
            _entry("cleaning", control_parameters=[]), ISSUE_DATE
        )
        self.assertEqual(result["status"], ENTRY_PARAMETERS_MISSING)

    def test_a_defective_parameter_takes_the_entry_with_it(self):
        result = assess_process_entry(
            _entry(
                "cleaning",
                control_parameters=[_parameter(measurement_uncertainty=4.0)],
            ),
            ISSUE_DATE,
        )
        self.assertEqual(result["status"], ENTRY_PARAMETER_DEFECT)
        self.assertEqual(result["defective_parameters"], ["bath-temperature-k"])

    def test_an_entry_with_no_evidence_is_never_put_forward(self):
        result = assess_process_entry(
            _entry("cleaning", evidence_reference=None, evidence_date=None),
            ISSUE_DATE,
        )
        self.assertEqual(result["status"], ENTRY_EVIDENCE_MISSING)

    def test_evidence_predating_the_document_inverts_the_gate(self):
        result = assess_process_entry(
            _entry("cleaning", evidence_date="2025-09-30"), ISSUE_DATE
        )
        self.assertEqual(result["status"], ENTRY_EVIDENCE_PREDATES_DOCUMENT)

    def test_a_control_parameter_declared_twice_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_process_entry(
                _entry(
                    "cleaning", control_parameters=[_parameter(), _parameter()]
                ),
                ISSUE_DATE,
            )

    def test_a_process_outside_the_required_set_needs_its_own_criticality(self):
        with self.assertRaises(ValueError):
            assess_process_entry(_entry("annealing"), ISSUE_DATE)

    def test_a_declared_extra_process_with_a_criticality_is_graded(self):
        result = assess_process_entry(
            _entry("annealing", criticality="control-only"), ISSUE_DATE
        )
        self.assertEqual(result["status"], ENTRY_ACCEPTED)


class ProcessCoverageTests(unittest.TestCase):
    def test_the_full_required_set_covers(self):
        result = process_coverage(_full_entries())
        self.assertTrue(result["covers_required_set"])
        self.assertEqual(result["missing"], [])

    def test_a_missing_qualification_critical_process_is_named(self):
        entries = [e for e in _full_entries() if e["process"] != "cleaning"]
        result = process_coverage(entries)
        self.assertEqual(result["missing_critical"], ["cleaning"])
        self.assertFalse(result["covers_critical_set"])

    def test_a_missing_control_only_process_is_a_baseline_gap(self):
        entries = [e for e in _full_entries() if e["process"] != "edge-finishing"]
        result = process_coverage(entries)
        self.assertEqual(result["missing"], ["edge-finishing"])
        self.assertTrue(result["covers_critical_set"])
        self.assertTrue(result["findings"])

    def test_an_extra_declared_process_is_carried_as_baseline(self):
        entries = _full_entries() + [_entry("annealing", criticality="control-only")]
        result = process_coverage(entries)
        self.assertEqual(result["extra"], ["annealing"])
        self.assertTrue(result["covers_required_set"])

    def test_a_process_declared_twice_is_rejected(self):
        with self.assertRaises(ValueError):
            process_coverage(_full_entries() + [_entry("cleaning")])


class DocumentRollupTests(unittest.TestCase):
    def test_a_complete_document_is_accepted(self):
        result = assess_production_control_document(_spec())
        self.assertEqual(result["verdict"], DOCUMENT_ACCEPTED)
        self.assertTrue(result["fully_accepted"])
        self.assertAlmostEqual(result["accepted_share"], 1.0, places=12)

    def test_a_missing_critical_process_makes_the_document_incomplete(self):
        entries = [e for e in _full_entries() if e["process"] != "ar-coating-deposition"]
        result = assess_production_control_document(_spec(entries))
        self.assertEqual(result["verdict"], DOCUMENT_INCOMPLETE)
        self.assertEqual(result["coverage"]["missing_critical"], ["ar-coating-deposition"])

    def test_a_document_written_after_the_campaign_started_is_not_a_gate(self):
        result = assess_production_control_document(
            _spec(issue_date="2026-04-01")
        )
        self.assertFalse(result["precedes_campaign"])
        self.assertEqual(result["verdict"], DOCUMENT_INCOMPLETE)

    def test_the_weakest_entry_is_the_worst_status(self):
        entries = _full_entries()
        entries[0]["evidence_reference"] = None
        entries[0]["evidence_date"] = None
        entries[1]["controlling_document"] = ""
        result = assess_production_control_document(_spec(entries))
        self.assertEqual(result["weakest_entry"], entries[1]["process"])
        self.assertEqual(len(result["rejected_entries"]), 2)

    def test_an_empty_entry_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_production_control_document(_spec([]))

    def test_a_non_mapping_specification_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_production_control_document("every process was declared")

    def test_a_missing_campaign_start_is_rejected(self):
        record = _spec()
        del record["campaign_start_date"]
        with self.assertRaises(ValueError):
            assess_production_control_document(record)

    def test_a_policy_may_substitute_its_own_required_process_set(self):
        entries = [_entry("cleaning")]
        strict = assess_production_control_document(_spec(entries))
        relaxed = assess_production_control_document(
            _spec(
                entries,
                policy={"required_processes": {"cleaning": "qualification-critical"}},
            )
        )
        self.assertEqual(strict["verdict"], DOCUMENT_INCOMPLETE)
        self.assertEqual(relaxed["verdict"], DOCUMENT_ACCEPTED)


if __name__ == "__main__":
    unittest.main()
