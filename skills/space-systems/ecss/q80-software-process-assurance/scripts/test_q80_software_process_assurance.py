"""Contract tests for the software process assurance logic."""

import unittest

from q80_software_process_assurance_logic import (
    CANDIDATE_MEASURES,
    FIXED_CRITICAL_OBLIGATIONS,
    assess_autocode,
    assess_reuse,
    check_critical_software,
    check_lifecycle,
    check_verification_independence,
    critical_software_obligations,
    normalise_review,
    triage_nonconformances,
)

ALL_B = [k for k, _, cats in FIXED_CRITICAL_OBLIGATIONS if "B" in cats]


class LifecycleTests(unittest.TestCase):
    def test_review_aliases(self):
        self.assertEqual(normalise_review("Preliminary Design Review"), "pdr")
        with self.assertRaises(ValueError):
            normalise_review("mdr")

    def test_first_open_gate(self):
        res = check_lifecycle({
            "srr": {"held": True, "closed": True},
            "pdr": {"held": True, "closed": False, "open_actions": 3},
        })
        self.assertEqual(res["first_open"], "pdr")
        self.assertEqual(res["closed"], ["srr"])

    def test_work_ahead_of_gate(self):
        res = check_lifecycle({"srr": {"held": True, "closed": True}},
                              work_started=["pdr", "cdr"])
        self.assertEqual(res["first_open"], "pdr")
        self.assertEqual(res["ahead_of_gate"], ["pdr", "cdr"])

    def test_closed_with_open_actions_inconsistent(self):
        res = check_lifecycle({"srr": {"held": True, "closed": True, "open_actions": 2}})
        self.assertEqual(res["inconsistent"], ["srr"])
        self.assertEqual(res["first_open"], "srr")

    def test_all_closed(self):
        full = {r: {"held": True, "closed": True} for r in ("srr", "pdr", "cdr", "qr", "ar")}
        self.assertIsNone(check_lifecycle(full)["first_open"])


class CriticalSoftwareTests(unittest.TestCase):
    def test_obligations_by_category(self):
        a = [k for k, _ in critical_software_obligations("A")]
        c = [k for k, _ in critical_software_obligations("C")]
        self.assertIn("unit-integration-rerun-uninstrumented", a)
        self.assertNotIn("unit-integration-rerun-uninstrumented", c)
        self.assertEqual(critical_software_obligations("D"), [])

    def test_met(self):
        res = check_critical_software("B", {"defensive-programming": "input checks on all TCs"}, ALL_B)
        self.assertEqual(res["verdict"], "met")

    def test_unjustified_measure_and_missing_obligation(self):
        res = check_critical_software("B", {"full-code-inspection": ""}, ALL_B[:-1])
        self.assertEqual(res["verdict"], "not-met")
        self.assertEqual(res["unjustified"], ["full-code-inspection"])
        self.assertEqual(len(res["missing_obligations"]), 1)

    def test_no_measure_at_all_fails(self):
        self.assertEqual(check_critical_software("A", {}, ALL_B)["verdict"], "not-met")

    def test_unknown_measure_flagged(self):
        res = check_critical_software("C", {"good-vibes": "trust"}, ALL_B)
        self.assertEqual(res["unknown"], ["good-vibes"])

    def test_category_d_not_applicable(self):
        self.assertEqual(check_critical_software("D", {}, ())["verdict"], "not-applicable")

    def test_candidate_list_unique(self):
        self.assertEqual(len(CANDIDATE_MEASURES), len(set(CANDIDATE_MEASURES)))


class IndependenceTests(unittest.TestCase):
    def test_self_verification(self):
        self.assertIn("author verifies own item",
                      check_verification_independence("D", "Ana", "ana", True))

    def test_category_b_same_org(self):
        self.assertEqual(len(check_verification_independence("B", "Ana", "Ben", True)), 1)
        self.assertEqual(check_verification_independence("B", "Ana", "Ben", True, True), [])
        self.assertEqual(check_verification_independence("C", "Ana", "Ben", True), [])


class ReuseTests(unittest.TestCase):
    BASE = {"name": "lib", "original_category": "B", "has_reuse_file": True,
            "configuration_known": True, "documentation_complete": True}

    def test_reuse_as_is(self):
        self.assertEqual(assess_reuse(self.BASE, "B")["verdict"], "reuse-as-is")

    def test_stricter_target_needs_delta(self):
        res = assess_reuse(self.BASE, "A")
        self.assertEqual(res["verdict"], "reuse-with-delta")
        self.assertTrue(any("close the evidence gap" in a for a in res["actions"]))

    def test_missing_reuse_file_blocks(self):
        comp = dict(self.BASE, has_reuse_file=False)
        self.assertEqual(assess_reuse(comp, "C")["verdict"], "not-reusable-yet")

    def test_platform_change_triggers_regression(self):
        comp = dict(self.BASE, platform_changed=True, open_problems=2)
        res = assess_reuse(comp, "C")
        self.assertEqual(res["verdict"], "reuse-with-delta")
        self.assertEqual(len(res["actions"]), 2)


class AutocodeTests(unittest.TestCase):
    def test_clean_generator(self):
        gen = {"modelling_standard": True, "model_verified": True,
               "output_under_cm": True, "output_verified": True}
        self.assertEqual(assess_autocode(gen, "A"), [])

    def test_unqualified_unverified_generator(self):
        gen = {"modelling_standard": True, "model_verified": True, "output_under_cm": True}
        self.assertEqual(len(assess_autocode(gen, "B")), 1)
        self.assertEqual(assess_autocode(gen, "D"), [])


class NonconformanceTests(unittest.TestCase):
    def test_triage(self):
        items = [
            {"id": "NCR-1", "kind": "ncr", "severity": "major", "status": "open"},
            {"id": "NCR-2", "kind": "ncr", "severity": "major", "status": "closed"},
            {"id": "SPR-7", "kind": "spr", "severity": "minor", "status": "open"},
        ]
        res = triage_nonconformances(items, [{"name": "QA", "software_expert": False}])
        self.assertEqual(res["open_major"], ["NCR-1"])
        self.assertEqual(res["major_without_board_decision"], ["NCR-2"])
        self.assertTrue(res["board_gap"])

    def test_bad_items_rejected(self):
        with self.assertRaises(ValueError):
            triage_nonconformances([{"id": "X", "kind": "ncr", "severity": "huge", "status": "open"}])
        dup = {"id": "X", "kind": "spr", "severity": "minor", "status": "open"}
        with self.assertRaises(ValueError):
            triage_nonconformances([dup, dup])


if __name__ == "__main__":
    unittest.main()
