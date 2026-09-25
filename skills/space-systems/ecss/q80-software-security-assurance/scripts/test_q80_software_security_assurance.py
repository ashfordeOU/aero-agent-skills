"""Contract tests for the software security assurance logic."""

import unittest

from q80_software_security_assurance_logic import (
    SECURITY_MEASURES,
    change_impact,
    check_board_security,
    check_security_measures,
    check_supplier_security_package,
    determine_sensitivity,
    propagate_sensitivity,
    sensitivity_clauses,
)


class SensitivityTests(unittest.TestCase):
    def test_threshold_and_driver(self):
        res = determine_sensitivity({
            "tc-auth": {"confidentiality": "low", "integrity": "severe"},
            "hk": {"availability": "low"},
        }, threshold="moderate")
        self.assertTrue(res["tc-auth"]["sensitive"])
        self.assertEqual(res["tc-auth"]["driver"], "integrity")
        self.assertFalse(res["hk"]["sensitive"])

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            determine_sensitivity({"x": {"integrity": "extreme"}})


class ClauseTests(unittest.TestCase):
    def test_category_d_sensitive_switches_clauses_back_on(self):
        clauses = dict(sensitivity_clauses("D", True))
        self.assertIn("6.3.4.4", clauses)
        self.assertIn("6.3.5.2", clauses)
        self.assertIn("6.2.10.1-6.2.10.4", clauses)

    def test_not_sensitive_keeps_plan_only(self):
        clauses = [c for c, _ in sensitivity_clauses("A", False)]
        self.assertEqual(clauses, ["6.2.9.1"])

    def test_suppliers_and_existing_software(self):
        clauses = [c for c, _ in sensitivity_clauses("B", False, True, True)]
        self.assertIn("5.4.5", clauses)
        self.assertIn("6.2.7.3", clauses)


class PropagationTests(unittest.TestCase):
    def test_unstopped_link_spreads_and_conflicts(self):
        comps = {"fdir": {"category": "A", "sensitive": False},
                 "crypto": {"category": "C", "sensitive": True},
                 "gui": {"category": "D", "sensitive": False}}
        res = propagate_sensitivity(comps, [
            {"source": "fdir", "target": "crypto"},
            {"source": "gui", "target": "crypto", "stopped": True},
        ])
        self.assertEqual(res["added"], ["fdir"])
        self.assertEqual(res["conflicts"], [("crypto", "fdir")])

    def test_stopped_link_neither_spreads_nor_conflicts(self):
        comps = {"a": {"category": "A", "sensitive": False},
                 "b": {"category": "D", "sensitive": True}}
        res = propagate_sensitivity(comps, [{"source": "a", "target": "b", "stopped": True}])
        self.assertEqual(res["added"], [])
        self.assertEqual(res["conflicts"], [])


class MeasureTests(unittest.TestCase):
    def test_met(self):
        res = check_security_measures(
            {"fuzzing": {"justification": "parser of uplinked files",
                         "applied_evidence": "FUZZ-REP-3"}}, True)
        self.assertEqual(res["verdict"], "met")

    def test_gaps(self):
        res = check_security_measures(
            {"penetration-testing": {"justification": ""},
             "magic-firewall": {"justification": "x", "applied_evidence": "y"}}, True)
        self.assertEqual(res["verdict"], "not-met")
        self.assertEqual(res["unknown"], ["magic-firewall"])
        self.assertEqual(res["unjustified"], ["penetration-testing"])
        self.assertEqual(res["not_applied"], ["penetration-testing"])
        self.assertIn("penetration-testing", SECURITY_MEASURES)

    def test_not_sensitive(self):
        self.assertEqual(check_security_measures({}, False)["verdict"], "not-applicable")


class ChangeTests(unittest.TestCase):
    def test_platform_change_both(self):
        res = change_impact("platform-functionality-change")
        self.assertTrue(res["regression"])
        self.assertTrue(res["analyse_more_vv"])

    def test_threat_knowledge_analyse_only(self):
        res = change_impact("threat-or-vulnerability-knowledge-change")
        self.assertFalse(res["regression"])
        self.assertTrue(res["analyse_more_vv"])

    def test_minor_tool_change_binary_identical(self):
        res = change_impact("build-tool-change", minor_tool_change=True, binary_identical=True)
        self.assertFalse(res["regression"])
        self.assertIn("binary comparison", res["note"])
        with self.assertRaises(ValueError):
            change_impact("moon-phase-change")


class BoardAndSupplierTests(unittest.TestCase):
    def test_board_needs_security_rep(self):
        board = [{"name": "A", "role": "software-product-assurance"},
                 {"name": "B", "role": "software-engineering"}]
        self.assertEqual(check_board_security({"id": "NCR-4", "possible_security_impact": True}, board),
                         ["software-security"])
        self.assertEqual(check_board_security({"id": "NCR-5"}, board), [])

    def test_supplier_package(self):
        missing = check_supplier_security_package({"sensitivity_stated": True}, True)
        self.assertEqual(len(missing), 2)
        self.assertEqual(check_supplier_security_package({"sensitivity_stated": True}, False), [])


if __name__ == "__main__":
    unittest.main()
