"""Contract tests for the Annex C unit logbook DRD logic."""

import unittest
from datetime import date

from q20_logbook_drd_logic import (
    COMMON_FIELDS,
    ENTRY_FIELDS,
    ENTRY_TYPES,
    INSPECTION_RESULTS,
    assess_logbook,
    chronology_findings,
    configuration_trace_findings,
    cumulative_exposure,
    environmental_excursions,
    inspection_result_findings,
    normalise_identifier,
    normalise_logbook,
    parse_day,
    sequence_findings,
    validate_entry,
)

INITIAL = "cfg-a"


def history(sequence=1, entry_date="2026-01-05"):
    return {
        "sequence": sequence,
        "entry_date": entry_date,
        "entry_type": "history",
        "signed_by": "assembly-operator",
        "activity": "receipt-into-store",
        "location": "clean-room-2",
        "reference": "wo-1001",
    }


def inspection(sequence=2, entry_date="2026-01-08", result="pass", nonconformance=None):
    entry = {
        "sequence": sequence,
        "entry_date": entry_date,
        "entry_type": "inspection",
        "signed_by": "quality-inspector",
        "inspection_type": "visual",
        "result": result,
        "reference": "insp-0042",
    }
    if nonconformance is not None:
        entry["nonconformance"] = nonconformance
    return entry


def modification(sequence=3, entry_date="2026-02-01", before="cfg-a", after="cfg-b"):
    return {
        "sequence": sequence,
        "entry_date": entry_date,
        "entry_type": "modification",
        "signed_by": "design-authority",
        "modification_reference": "ecr-77",
        "configuration_before": before,
        "configuration_after": after,
    }


def environmental(
    sequence=4,
    entry_date="2026-02-10",
    parameter="storage-humidity",
    value=40.0,
    limit=60.0,
    hours=120.0,
    nonconformance=None,
):
    entry = {
        "sequence": sequence,
        "entry_date": entry_date,
        "entry_type": "environmental",
        "signed_by": "store-keeper",
        "parameter": parameter,
        "value": value,
        "unit": "percent-rh",
        "duration_hours": hours,
        "limit": limit,
    }
    if nonconformance is not None:
        entry["nonconformance"] = nonconformance
    return entry


def clean_book():
    return [history(), inspection(), modification(), environmental()]


class VocabularyTests(unittest.TestCase):
    def test_four_entry_types(self):
        self.assertEqual(ENTRY_TYPES, ("history", "inspection", "modification", "environmental"))

    def test_every_type_names_its_fields(self):
        self.assertEqual(set(ENTRY_FIELDS), set(ENTRY_TYPES))

    def test_common_fields_are_shared(self):
        self.assertIn("signed_by", COMMON_FIELDS)
        self.assertIn("entry_date", COMMON_FIELDS)

    def test_inspection_results_include_conditional(self):
        self.assertIn("conditional", INSPECTION_RESULTS)

    def test_identifier_normalised(self):
        self.assertEqual(normalise_identifier(" CFG-B ", "c"), "cfg-b")

    def test_day_parsed_from_iso(self):
        self.assertEqual(parse_day("2026-03-04", "d"), date(2026, 3, 4))

    def test_bad_day_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("04/03/2026", "d")


class EntryValidationTests(unittest.TestCase):
    def test_clean_entry_validates(self):
        entry = validate_entry(history(), 0)
        self.assertEqual(entry["entry_type"], "history")
        self.assertEqual(entry["entry_date"], date(2026, 1, 5))

    def test_unknown_entry_type_rejected(self):
        bad = history()
        bad["entry_type"] = "shipment"
        with self.assertRaises(ValueError):
            validate_entry(bad, 0)

    def test_zero_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(history(sequence=0), 0)

    def test_boolean_sequence_rejected(self):
        bad = history()
        bad["sequence"] = True
        with self.assertRaises(ValueError):
            validate_entry(bad, 0)

    def test_missing_type_field_rejected(self):
        bad = modification()
        del bad["configuration_after"]
        with self.assertRaises(ValueError):
            validate_entry(bad, 0)

    def test_unknown_inspection_result_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(inspection(result="probably-fine"), 0)

    def test_non_numeric_environmental_value_rejected(self):
        bad = environmental()
        bad["value"] = "forty"
        with self.assertRaises(ValueError):
            validate_entry(bad, 0)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(environmental(hours=-1.0), 0)

    def test_empty_logbook_rejected(self):
        with self.assertRaises(ValueError):
            normalise_logbook([])


class SequenceTests(unittest.TestCase):
    def test_clean_sequence_has_no_finding(self):
        self.assertEqual(sequence_findings(normalise_logbook(clean_book())), [])

    def test_gap_in_the_numbering_is_a_finding(self):
        book = [history(1), inspection(2), modification(5)]
        findings = sequence_findings(normalise_logbook(book))
        self.assertIn("no entry numbered 3", findings[0])

    def test_repeated_number_is_a_finding(self):
        book = [history(1), inspection(2), modification(2)]
        findings = sequence_findings(normalise_logbook(book))
        self.assertIn("more than once", findings[0])


class ChronologyTests(unittest.TestCase):
    def test_clean_chronology_has_no_finding(self):
        self.assertEqual(chronology_findings(normalise_logbook(clean_book())), [])

    def test_backdated_entry_is_a_finding(self):
        book = [history(1, "2026-01-05"), inspection(2, "2025-12-30")]
        findings = chronology_findings(normalise_logbook(book))
        self.assertIn("before entry 1", findings[0])

    def test_same_day_entries_are_accepted(self):
        book = [history(1, "2026-01-05"), inspection(2, "2026-01-05")]
        self.assertEqual(chronology_findings(normalise_logbook(book)), [])


class ConfigurationTraceTests(unittest.TestCase):
    def test_single_modification_moves_the_unit_forward(self):
        findings, state = configuration_trace_findings(
            normalise_logbook(clean_book()), INITIAL
        )
        self.assertEqual(findings, [])
        self.assertEqual(state, "cfg-b")

    def test_chained_modifications_join_up(self):
        book = [
            history(1),
            modification(2, "2026-02-01", "cfg-a", "cfg-b"),
            modification(3, "2026-03-01", "cfg-b", "cfg-c"),
        ]
        findings, state = configuration_trace_findings(normalise_logbook(book), INITIAL)
        self.assertEqual(findings, [])
        self.assertEqual(state, "cfg-c")

    def test_broken_chain_is_a_finding(self):
        book = [
            history(1),
            modification(2, "2026-02-01", "cfg-a", "cfg-b"),
            modification(3, "2026-03-01", "cfg-a", "cfg-d"),
        ]
        findings, _ = configuration_trace_findings(normalise_logbook(book), INITIAL)
        self.assertIn("while the unit stands at cfg-b", findings[0])

    def test_modification_that_changes_nothing_is_a_finding(self):
        book = [modification(1, "2026-02-01", "cfg-a", "cfg-a")]
        findings, _ = configuration_trace_findings(normalise_logbook(book), INITIAL)
        self.assertIn("leaves the configuration unchanged", findings[0])

    def test_logbook_without_modifications_keeps_the_initial_state(self):
        findings, state = configuration_trace_findings(
            normalise_logbook([history(1), inspection(2)]), INITIAL
        )
        self.assertEqual(findings, [])
        self.assertEqual(state, "cfg-a")


class EnvironmentalTests(unittest.TestCase):
    def test_within_limit_records_no_excursion(self):
        self.assertEqual(environmental_excursions(normalise_logbook(clean_book())), [])

    def test_beyond_limit_records_an_excursion_with_its_margin(self):
        book = [environmental(1, value=75.0, limit=60.0)]
        excursions = environmental_excursions(normalise_logbook(book))
        self.assertEqual(len(excursions), 1)
        self.assertAlmostEqual(excursions[0]["margin"], 15.0, places=9)

    def test_value_exactly_on_the_limit_is_not_an_excursion(self):
        book = [environmental(1, value=60.0, limit=60.0)]
        self.assertEqual(environmental_excursions(normalise_logbook(book)), [])

    def test_entry_with_no_limit_is_not_graded(self):
        entry = environmental(1, value=999.0)
        entry["limit"] = None
        self.assertEqual(environmental_excursions(normalise_logbook([entry])), [])

    def test_exposure_accumulates_per_parameter(self):
        book = [
            environmental(1, parameter="storage-humidity", hours=120.0),
            environmental(2, "2026-02-20", parameter="storage-humidity", hours=36.5),
            environmental(3, "2026-03-01", parameter="storage-temperature", hours=48.25),
        ]
        exposure = cumulative_exposure(normalise_logbook(book))
        self.assertAlmostEqual(exposure["per_parameter"]["storage-humidity"], 156.5, places=9)
        self.assertAlmostEqual(exposure["total_hours"], 204.75, places=9)

    def test_exposure_of_a_logbook_without_environmental_entries_is_zero(self):
        exposure = cumulative_exposure(normalise_logbook([history(1), inspection(2)]))
        self.assertAlmostEqual(exposure["total_hours"], 0.0, places=9)


class InspectionResultTests(unittest.TestCase):
    def test_passed_inspection_needs_no_reference(self):
        self.assertEqual(inspection_result_findings(normalise_logbook(clean_book())), [])

    def test_failed_inspection_without_a_reference_is_a_finding(self):
        book = [inspection(1, result="fail")]
        findings = inspection_result_findings(normalise_logbook(book))
        self.assertIn("fail inspection with no nonconformance", findings[0])

    def test_failed_inspection_with_a_reference_is_clean(self):
        book = [inspection(1, result="fail", nonconformance="ncr-9")]
        self.assertEqual(inspection_result_findings(normalise_logbook(book)), [])


class AssessmentTests(unittest.TestCase):
    def test_clean_logbook_is_conformant(self):
        result = assess_logbook(clean_book(), INITIAL)
        self.assertEqual(result["verdict"], "logbook-conformant")
        self.assertEqual(result["entry_count"], 4)

    def test_entry_counts_are_reported_for_evidence(self):
        result = assess_logbook(clean_book(), INITIAL)
        self.assertEqual(result["entry_counts"]["modification"], 1)
        self.assertEqual(result["entry_counts"]["environmental"], 1)

    def test_final_configuration_is_reported(self):
        self.assertEqual(assess_logbook(clean_book(), INITIAL)["final_configuration"], "cfg-b")

    def test_excursion_without_a_reference_makes_it_nonconformant(self):
        book = [history(1), environmental(2, value=75.0, limit=60.0)]
        result = assess_logbook(book, INITIAL)
        self.assertEqual(result["verdict"], "logbook-nonconformant")
        self.assertIn("no nonconformance reference", result["findings"][0])

    def test_excursion_with_a_reference_is_reported_but_not_a_finding(self):
        book = [history(1), environmental(2, value=75.0, limit=60.0, nonconformance="ncr-3")]
        result = assess_logbook(book, INITIAL)
        self.assertEqual(result["verdict"], "logbook-conformant")
        self.assertEqual(len(result["excursions"]), 1)

    def test_broken_sequence_makes_it_nonconformant(self):
        result = assess_logbook([history(1), inspection(4)], INITIAL)
        self.assertEqual(result["verdict"], "logbook-nonconformant")

    def test_exposure_is_reported_for_evidence(self):
        result = assess_logbook(clean_book(), INITIAL)
        self.assertAlmostEqual(result["exposure"]["total_hours"], 120.0, places=9)

    def test_unknown_initial_configuration_rejected(self):
        with self.assertRaises(ValueError):
            assess_logbook(clean_book(), "   ")


if __name__ == "__main__":
    unittest.main()
