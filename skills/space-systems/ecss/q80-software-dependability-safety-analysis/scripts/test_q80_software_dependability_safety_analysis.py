"""Contract tests for the software dependability and safety analysis logic."""

import unittest

from q80_software_dependability_safety_analysis_logic import (
    check_analysis_currency,
    check_hsia_coverage,
    critical_item_candidates,
    grade_sfmea,
    normalise_severity,
    propagate_criticality,
    track_recommendations,
)


def _row(rid, comp, sev, mitigation="", requirement="", effect="loss of attitude control"):
    return {"id": rid, "component": comp, "failure_mode": "stuck output",
            "effect": effect, "severity": sev, "mitigation": mitigation,
            "requirement": requirement}


class SeverityTests(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(normalise_severity("catastrophic"), "I")
        self.assertEqual(normalise_severity("3"), "III")
        self.assertEqual(normalise_severity("iv"), "IV")
        with self.assertRaises(ValueError):
            normalise_severity("severe")


class SfmeaTests(unittest.TestCase):
    def test_severe_row_needs_mitigation(self):
        res = grade_sfmea([_row("F1", "aocs", "I")])
        self.assertIn(("F1", "severity I failure mode without a mitigation"), res["findings"])
        self.assertEqual(res["suggested_category"], {"aocs": "A"})

    def test_mitigation_needs_requirement(self):
        res = grade_sfmea([_row("F1", "aocs", "II", mitigation="watchdog reset")])
        self.assertIn(("F1", "mitigation not traced to a requirement"), res["findings"])

    def test_clean_worksheet_and_worst_severity(self):
        res = grade_sfmea([
            _row("F1", "aocs", "III", "range check", "SRS-10"),
            _row("F2", "aocs", "II", "voter", "SRS-11"),
            _row("F3", "tm", "IV"),
        ])
        self.assertEqual(res["findings"], [])
        self.assertEqual(res["worst_severity"], {"aocs": "II", "tm": "IV"})
        self.assertEqual(res["suggested_category"], {"aocs": "B", "tm": "D"})
        self.assertEqual(res["row_component"]["F3"], "tm")

    def test_missing_effect_and_duplicate(self):
        res = grade_sfmea([_row("F1", "tm", "IV", effect="")])
        self.assertIn(("F1", "no effect stated, so the severity is unsupported"), res["findings"])
        with self.assertRaises(ValueError):
            grade_sfmea([_row("F1", "tm", "IV"), _row("F1", "tm", "IV")])


class PropagationTests(unittest.TestCase):
    def test_unprevented_shared_resource_raises(self):
        res = propagate_criticality(
            {"fdir": "A", "housekeeping": "C", "payload": "D"},
            [{"source": "housekeeping", "target": "fdir", "mechanism": "shared-resource"}])
        self.assertEqual(res["effective"]["housekeeping"], "A")
        self.assertEqual(res["effective"]["payload"], "D")
        self.assertEqual(res["raised"], [("housekeeping", "C", "A", ["fdir", "housekeeping"])])

    def test_partitioned_link_does_not_raise(self):
        res = propagate_criticality(
            {"fdir": "A", "housekeeping": "C"},
            [{"source": "housekeeping", "target": "fdir", "prevented": True}])
        self.assertEqual(res["raised"], [])

    def test_transitive_group(self):
        res = propagate_criticality(
            {"a": "B", "b": "D", "c": "C"},
            [{"source": "b", "target": "c"}, {"source": "c", "target": "a"}])
        self.assertEqual(set(res["effective"].values()), {"B"})

    def test_unknown_component_rejected(self):
        with self.assertRaises(ValueError):
            propagate_criticality({"a": "A"}, [{"source": "a", "target": "z"}])


class HsiaTests(unittest.TestCase):
    def test_gaps(self):
        res = check_hsia_coverage(
            ["HW-1", "HW-2", "HW-3"],
            {"HW-1": ["SRS-1"], "HW-2": ["SRS-2", "SRS-3"]},
            {"SRS-1": "pass", "SRS-2": "fail"})
        self.assertEqual(res["uncovered"], ["HW-3"])
        self.assertEqual(res["failed"], ["SRS-2"])
        self.assertEqual(res["unverified"], ["SRS-3"])
        self.assertEqual(res["verdict"], "incomplete")

    def test_complete(self):
        res = check_hsia_coverage(["HW-1"], {"HW-1": ["SRS-1"]}, {"SRS-1": "pass"})
        self.assertEqual(res["verdict"], "complete")


class RecommendationTests(unittest.TestCase):
    def test_overdue_and_export(self):
        recs = [
            {"id": "R1", "level": "software", "status": "implemented", "due": "cdr"},
            {"id": "R2", "level": "system", "status": "open", "due": "qr"},
            {"id": "R3", "level": "software", "status": "rejected", "due": "pdr"},
            {"id": "R4", "level": "software", "status": "verified", "due": "cdr"},
        ]
        res = track_recommendations(recs, "cdr")
        self.assertEqual(res["overdue"], ["R1"])
        self.assertEqual(res["export_to_system"], ["R2"])
        self.assertEqual(res["rejected_without_rationale"], ["R3"])

    def test_bad_status(self):
        with self.assertRaises(ValueError):
            track_recommendations([{"id": "R1", "status": "parked"}], "pdr")


class CurrencyTests(unittest.TestCase):
    def test_missing_and_stale(self):
        res = check_analysis_currency({"pdr": "SDSA-1", "cdr": "SDSA-1"}, "qr")
        self.assertEqual(res["missing"], ["qr"])
        self.assertEqual(res["stale"], ["cdr"])
        self.assertFalse(res["current"])

    def test_nothing_owed_at_srr(self):
        self.assertTrue(check_analysis_currency({}, "srr")["current"])


class CriticalItemTests(unittest.TestCase):
    def test_candidates(self):
        sfmea = grade_sfmea([_row("F1", "tm", "II")])
        hsia = check_hsia_coverage(["HW-1"], {"HW-1": ["SRS-9"]}, {})
        hsia["requirement_owner"] = {"SRS-9": "power"}
        res = dict(critical_item_candidates(
            {"fdir": "A", "tm": "C", "power": "C", "gui": "D"}, sfmea, hsia, ["gui"]))
        self.assertEqual(res["fdir"], ["effective category A"])
        self.assertIn("unmitigated severe failure mode F1", res["tm"])
        self.assertIn("HSIA requirement SRS-9 not shown to pass", res["power"])
        self.assertEqual(res["gui"], ["technology new to the supplier"])


if __name__ == "__main__":
    unittest.main()
