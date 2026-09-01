#!/usr/bin/env python3
"""Gate 3 contract test: ARP4761A zonal safety analysis.

Exercises scripts/zonal_safety_analysis_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - zone hazard
severity classification, severity rollup, zonal hazard checklist
coverage and completeness, separation and containment verdicts, ZSA
report rollup, and invalid-input handling.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import zonal_safety_analysis_logic as zsa  # noqa: E402


class ZoneIdentificationTest(unittest.TestCase):
    """zone_identification: normalize zone numbers, validate format."""

    def test_numeric_zone(self):
        self.assertEqual(zsa.zone_identification("141"), "141")

    def test_letter_suffix_normalized(self):
        self.assertEqual(zsa.zone_identification("141a"), "141A")

    def test_stripped_and_uppercased(self):
        self.assertEqual(zsa.zone_identification(" 241A "), "241A")

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            zsa.zone_identification("")

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            zsa.zone_identification(141)

    def test_bad_chars_raise(self):
        with self.assertRaises(ValueError):
            zsa.zone_identification("14x!")


class SeverityRankTest(unittest.TestCase):
    """severity_rank: minor=1, major=2, hazardous=3, catastrophic=4."""

    def test_minor_is_one(self):
        self.assertEqual(zsa.severity_rank("minor"), 1)

    def test_major_is_two(self):
        self.assertEqual(zsa.severity_rank("major"), 2)

    def test_hazardous_is_three(self):
        self.assertEqual(zsa.severity_rank("hazardous"), 3)

    def test_catastrophic_is_four(self):
        self.assertEqual(zsa.severity_rank("catastrophic"), 4)

    def test_case_insensitive(self):
        self.assertEqual(zsa.severity_rank("HAZARDOUS"), 3)

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            zsa.severity_rank("severe")


class ZoneSeverityRollupTest(unittest.TestCase):
    """zone_severity_rollup: highest severity present wins."""

    def test_mixed_findings_rollup_hazardous(self):
        self.assertEqual(
            zsa.zone_severity_rollup(["minor", "major", "hazardous"]), "hazardous"
        )

    def test_major_over_minor(self):
        self.assertEqual(zsa.zone_severity_rollup(["major", "minor"]), "major")

    def test_catastrophic_dominates(self):
        self.assertEqual(
            zsa.zone_severity_rollup(["major", "catastrophic", "hazardous"]),
            "catastrophic",
        )

    def test_empty_findings_none(self):
        self.assertEqual(zsa.zone_severity_rollup([]), "none")

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            zsa.zone_severity_rollup("major")


class ChecklistCoverageTest(unittest.TestCase):
    """checklist_coverage: assessed / total, validated."""

    def test_nine_of_twelve(self):
        self.assertAlmostEqual(zsa.checklist_coverage(9, 12), 0.75)

    def test_full_coverage(self):
        self.assertEqual(zsa.checklist_coverage(12, 12), 1.0)

    def test_zero_assessed(self):
        self.assertEqual(zsa.checklist_coverage(0, 5), 0.0)

    def test_zero_total_returns_zero(self):
        self.assertEqual(zsa.checklist_coverage(0, 0), 0.0)

    def test_assessed_exceeds_total_raises(self):
        with self.assertRaises(ValueError):
            zsa.checklist_coverage(6, 5)

    def test_negative_total_raises(self):
        with self.assertRaises(ValueError):
            zsa.checklist_coverage(0, -1)


class ChecklistCompleteTest(unittest.TestCase):
    """checklist_complete: true only at coverage 1.0."""

    def test_complete_when_all_assessed(self):
        self.assertTrue(zsa.checklist_complete(12, 12))

    def test_incomplete_when_partial(self):
        self.assertFalse(zsa.checklist_complete(9, 12))

    def test_incomplete_when_none(self):
        self.assertFalse(zsa.checklist_complete(0, 5))


class SeparationVerdictTest(unittest.TestCase):
    """separation_verdict: gap at least required is ok."""

    def test_exact_gap_ok(self):
        self.assertEqual(zsa.separation_verdict(50.0, 50.0), "ok")

    def test_gap_shortfall_action(self):
        self.assertEqual(zsa.separation_verdict(49.0, 50.0), "action")

    def test_large_gap_ok(self):
        self.assertEqual(zsa.separation_verdict(120.0, 50.0), "ok")

    def test_zero_gap_action(self):
        self.assertEqual(zsa.separation_verdict(0.0, 10.0), "action")

    def test_negative_gap_raises(self):
        with self.assertRaises(ValueError):
            zsa.separation_verdict(-1.0, 50.0)

    def test_negative_required_raises(self):
        with self.assertRaises(ValueError):
            zsa.separation_verdict(50.0, -1.0)


class ContainmentVerdictTest(unittest.TestCase):
    """containment_verdict: barrier rating at least hazard energy."""

    def test_rating_meets_energy_ok(self):
        self.assertEqual(zsa.containment_verdict(3, 2), "ok")

    def test_rating_below_energy_action(self):
        self.assertEqual(zsa.containment_verdict(2, 3), "action")

    def test_equal_rating_ok(self):
        self.assertEqual(zsa.containment_verdict(4, 4), "ok")

    def test_max_rating_ok(self):
        self.assertEqual(zsa.containment_verdict(5, 1), "ok")

    def test_rating_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            zsa.containment_verdict(0, 2)
        with self.assertRaises(ValueError):
            zsa.containment_verdict(6, 2)

    def test_energy_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            zsa.containment_verdict(3, 0)


class ZsaReportTest(unittest.TestCase):
    """zsa_report: rollup, checklist totals, verdict."""

    ZONES = [
        {
            "id": "141",
            "findings": ["minor", "major"],
            "assessed": 10,
            "total": 10,
            "separation": "ok",
            "containment": "ok",
        },
        {
            "id": "142",
            "findings": ["hazardous"],
            "assessed": 8,
            "total": 10,
            "separation": "ok",
            "containment": "action",
        },
        {
            "id": "143",
            "findings": [],
            "assessed": 6,
            "total": 6,
            "separation": "action",
            "containment": "ok",
        },
    ]

    def test_total_zones(self):
        r = zsa.zsa_report(self.ZONES)
        self.assertEqual(r["total_zones"], 3)

    def test_severity_counts(self):
        r = zsa.zsa_report(self.ZONES)
        self.assertEqual(r["severity_counts"]["major"], 1)
        self.assertEqual(r["severity_counts"]["hazardous"], 1)
        self.assertEqual(r["severity_counts"]["catastrophic"], 0)

    def test_checklist_totals(self):
        r = zsa.zsa_report(self.ZONES)
        self.assertEqual(r["checklist_assessed"], 24)
        self.assertEqual(r["checklist_total"], 26)

    def test_coverage(self):
        r = zsa.zsa_report(self.ZONES)
        self.assertAlmostEqual(r["coverage"], 24 / 26)

    def test_action_zones(self):
        r = zsa.zsa_report(self.ZONES)
        self.assertEqual(r["action_zones"], ["142", "143"])

    def test_verdict_action(self):
        r = zsa.zsa_report(self.ZONES)
        self.assertEqual(r["verdict"], "action")

    def test_clean_zones_accept(self):
        zones = [
            {
                "id": "144",
                "findings": ["minor"],
                "assessed": 9,
                "total": 9,
                "separation": "ok",
                "containment": "ok",
            }
        ]
        r = zsa.zsa_report(zones)
        self.assertEqual(r["verdict"], "accept")
        self.assertEqual(r["action_zones"], [])

    def test_bad_separation_raises(self):
        zones = [dict(self.ZONES[0], separation="maybe")]
        with self.assertRaises(ValueError):
            zsa.zsa_report(zones)


if __name__ == "__main__":
    unittest.main(verbosity=2)
