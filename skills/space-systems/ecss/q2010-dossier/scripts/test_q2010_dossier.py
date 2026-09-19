"""Contract tests for the clause 5.1.3 off-the-shelf evaluation-dossier logic."""

import datetime
import unittest

from q2010_dossier_logic import (
    DEFAULT_DRD_SECTIONS,
    add_entry,
    assess_dossier,
    candidates,
    coverage,
    current_entries,
    new_dossier,
    open_findings,
    parse_iso_date,
    stale_entries,
    superseded_entries,
    validate_entry,
)


def entry(ident, section, outcome="pass", candidate="unit-alpha",
          date="2026-03-01", revision=1, evidence="TR-%s"):
    return {
        "id": ident,
        "candidate": candidate,
        "section": section,
        "outcome": outcome,
        "evidence_ref": evidence % ident if "%s" in evidence else evidence,
        "date": date,
        "revision": revision,
    }


def full_set(candidate="unit-alpha", date="2026-03-01"):
    return [entry("E%02d" % i, section, candidate=candidate, date=date)
            for i, section in enumerate(DEFAULT_DRD_SECTIONS, start=1)]


class ParseIsoDateTests(unittest.TestCase):
    def test_parses_a_string(self):
        self.assertEqual(parse_iso_date("2026-03-01"), datetime.date(2026, 3, 1))

    def test_passes_a_date_through(self):
        self.assertEqual(parse_iso_date(datetime.date(2026, 3, 1)),
                         datetime.date(2026, 3, 1))

    def test_rejects_a_non_date_string(self):
        with self.assertRaises(ValueError):
            parse_iso_date("March 2026")

    def test_rejects_a_number(self):
        with self.assertRaises(ValueError):
            parse_iso_date(20260301)


class ValidateEntryTests(unittest.TestCase):
    def test_normalises_a_good_entry(self):
        record = validate_entry(entry("E01", "functional-evaluation"))
        self.assertEqual(record["candidate"], "unit-alpha")
        self.assertEqual(record["revision"], 1)
        self.assertIsNone(record["superseded_by"])

    def test_missing_evidence_reference_rejected(self):
        bad = entry("E01", "functional-evaluation")
        bad["evidence_ref"] = "   "
        with self.assertRaises(ValueError):
            validate_entry(bad)

    def test_unknown_outcome_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(entry("E01", "functional-evaluation", outcome="probably-fine"))

    def test_missing_candidate_rejected(self):
        bad = entry("E01", "functional-evaluation")
        del bad["candidate"]
        with self.assertRaises(ValueError):
            validate_entry(bad)

    def test_zero_revision_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(entry("E01", "functional-evaluation", revision=0))

    def test_boolean_revision_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(entry("E01", "functional-evaluation", revision=True))

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(["E01"])


class AppendOnlyTests(unittest.TestCase):
    def test_same_id_same_revision_rejected(self):
        dossier = new_dossier()
        add_entry(dossier, entry("E01", "functional-evaluation"))
        with self.assertRaises(ValueError):
            add_entry(dossier, entry("E01", "functional-evaluation"))

    def test_lower_revision_does_not_supersede(self):
        dossier = new_dossier()
        add_entry(dossier, entry("E01", "functional-evaluation", revision=3))
        with self.assertRaises(ValueError):
            add_entry(dossier, entry("E01", "functional-evaluation", revision=2))

    def test_higher_revision_supersedes_and_keeps_history(self):
        dossier = new_dossier()
        add_entry(dossier, entry("E01", "functional-evaluation", outcome="open"))
        add_entry(dossier, entry("E01", "functional-evaluation", outcome="pass", revision=2))
        self.assertEqual(len(dossier["entries"]), 2)
        self.assertEqual(len(current_entries(dossier)), 1)
        self.assertEqual(current_entries(dossier)[0]["outcome"], "pass")
        self.assertEqual(len(superseded_entries(dossier)), 1)

    def test_a_revision_may_not_move_the_entry_to_another_candidate(self):
        dossier = new_dossier()
        add_entry(dossier, entry("E01", "functional-evaluation"))
        with self.assertRaises(ValueError):
            add_entry(dossier, entry("E01", "functional-evaluation",
                                     candidate="unit-beta", revision=2))

    def test_dossier_shape_is_checked(self):
        with self.assertRaises(ValueError):
            add_entry({"records": []}, entry("E01", "functional-evaluation"))

    def test_candidates_are_listed_alphabetically(self):
        dossier = new_dossier()
        add_entry(dossier, entry("E01", "functional-evaluation", candidate="unit-beta"))
        add_entry(dossier, entry("E02", "functional-evaluation", candidate="unit-alpha"))
        self.assertEqual(candidates(dossier), ["unit-alpha", "unit-beta"])


class CoverageTests(unittest.TestCase):
    def _loaded(self):
        dossier = new_dossier()
        for item in full_set():
            add_entry(dossier, item)
        return dossier

    def test_full_set_covers_every_section(self):
        cover = coverage(self._loaded(), "unit-alpha")
        self.assertEqual(cover["missing"], [])
        self.assertAlmostEqual(cover["ratio"], 1.0, places=9)

    def test_missing_sections_are_named_in_drd_order(self):
        dossier = new_dossier()
        add_entry(dossier, entry("E01", "item-identification"))
        add_entry(dossier, entry("E02", "interface-evaluation"))
        cover = coverage(dossier, "unit-alpha")
        self.assertEqual(cover["covered"], ["item-identification", "interface-evaluation"])
        self.assertEqual(cover["missing"][0], "functional-evaluation")
        self.assertAlmostEqual(cover["ratio"], 2.0 / len(DEFAULT_DRD_SECTIONS), places=9)

    def test_a_section_outside_the_drd_is_reported_separately(self):
        dossier = new_dossier()
        add_entry(dossier, entry("E01", "supplier-lunch-notes"))
        cover = coverage(dossier, "unit-alpha")
        self.assertEqual(cover["outside_the_drd"], ["supplier-lunch-notes"])
        self.assertEqual(cover["covered"], [])

    def test_superseded_entry_does_not_count_as_coverage(self):
        dossier = new_dossier()
        add_entry(dossier, entry("E01", "functional-evaluation"))
        add_entry(dossier, entry("E01", "performance-evaluation", revision=2))
        cover = coverage(dossier, "unit-alpha")
        self.assertIn("functional-evaluation", cover["missing"])
        self.assertIn("performance-evaluation", cover["covered"])

    def test_empty_section_list_rejected(self):
        with self.assertRaises(ValueError):
            coverage(self._loaded(), "unit-alpha", [])

    def test_empty_candidate_name_rejected(self):
        with self.assertRaises(ValueError):
            coverage(self._loaded(), "  ")


class StalenessAndFindingsTests(unittest.TestCase):
    def _loaded(self, date="2026-03-01"):
        dossier = new_dossier()
        for item in full_set(date=date):
            add_entry(dossier, item)
        return dossier

    def test_recent_evidence_is_not_stale(self):
        self.assertEqual(stale_entries(self._loaded(), "2026-09-01", 730), [])

    def test_evidence_past_the_window_is_stale(self):
        self.assertEqual(len(stale_entries(self._loaded("2022-01-01"), "2026-09-01", 730)),
                         len(DEFAULT_DRD_SECTIONS))

    def test_evidence_exactly_on_the_window_is_not_yet_stale(self):
        self.assertEqual(stale_entries(self._loaded("2026-03-01"), "2026-03-31", 30), [])

    def test_one_day_past_the_window_is_stale(self):
        self.assertEqual(len(stale_entries(self._loaded("2026-03-01"), "2026-04-01", 30)),
                         len(DEFAULT_DRD_SECTIONS))

    def test_entry_dated_after_the_as_of_date_rejected(self):
        with self.assertRaises(ValueError):
            stale_entries(self._loaded("2026-12-01"), "2026-09-01", 730)

    def test_zero_validity_window_rejected(self):
        with self.assertRaises(ValueError):
            stale_entries(self._loaded(), "2026-09-01", 0)

    def test_open_and_failed_outcomes_are_findings(self):
        dossier = new_dossier()
        add_entry(dossier, entry("E01", "functional-evaluation", outcome="open"))
        add_entry(dossier, entry("E02", "performance-evaluation", outcome="fail"))
        add_entry(dossier, entry("E03", "interface-evaluation", outcome="not-applicable"))
        self.assertEqual([e["id"] for e in open_findings(dossier)], ["E01", "E02"])


class AssessDossierTests(unittest.TestCase):
    def _spec(self, **over):
        base = {"entries": full_set(), "as_of": "2026-09-01"}
        base.update(over)
        return base

    def test_complete_candidate_reported_complete(self):
        result = assess_dossier(self._spec())
        self.assertEqual(result["candidates"]["unit-alpha"]["verdict"], "complete")
        self.assertEqual(result["complete_candidates"], ["unit-alpha"])

    def test_missing_section_outranks_an_open_finding(self):
        entries = full_set()[:-1]
        entries[0] = dict(entries[0], outcome="open")
        result = assess_dossier(self._spec(entries=entries))
        self.assertEqual(result["candidates"]["unit-alpha"]["verdict"], "incomplete")

    def test_open_finding_blocks_a_fully_covered_candidate(self):
        entries = full_set()
        entries[2] = dict(entries[2], outcome="open")
        result = assess_dossier(self._spec(entries=entries))
        self.assertEqual(result["candidates"]["unit-alpha"]["verdict"], "open-findings")
        self.assertFalse(result["any_complete"])

    def test_stale_evidence_blocks_a_fully_covered_candidate(self):
        result = assess_dossier(self._spec(entries=full_set(date="2021-01-01")))
        self.assertEqual(result["candidates"]["unit-alpha"]["verdict"], "stale-evidence")

    def test_history_is_retained_and_counted(self):
        entries = full_set() + [entry("E01", "functional-evaluation", revision=2)]
        result = assess_dossier(self._spec(entries=entries))
        self.assertEqual(result["history_retained"], 1)
        self.assertEqual(result["entries_held"], len(DEFAULT_DRD_SECTIONS) + 1)

    def test_two_candidates_are_graded_independently(self):
        entries = full_set("unit-alpha") + [
            entry("F01", "item-identification", candidate="unit-beta")]
        result = assess_dossier(self._spec(entries=entries))
        self.assertEqual(result["candidates"]["unit-alpha"]["verdict"], "complete")
        self.assertEqual(result["candidates"]["unit-beta"]["verdict"], "incomplete")

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_dossier({"entries": full_set()})

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_dossier(full_set())


if __name__ == "__main__":
    unittest.main()
