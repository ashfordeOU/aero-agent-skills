"""Contract tests for the software product assurance plan logic."""

import unittest

from q80_software_product_assurance_plan_logic import (
    SPAP_OUTLINE,
    assess_spap,
    assess_tools,
    check_organisation,
    check_supplier_control,
    normalise_category,
    normalise_section_id,
    outline_section,
    plan_maturity_due,
)

FILLER = " ".join(["word"] * 60)


def _full_plan(scope=()):
    """A plan with every owed leaf section written out."""
    ids = [s for s, _, _, _ in SPAP_OUTLINE]
    leaves = [s for s in ids if not any(o.startswith(s + ".") for o in ids)]
    res = assess_spap({}, scope=scope)
    return {sid: FILLER for sid in leaves if sid in res["owed"]}


class OutlineTests(unittest.TestCase):
    def test_section_id_forms(self):
        self.assertEqual(normalise_section_id("<5.3>"), "5.3")
        self.assertEqual(normalise_section_id(8), "8")
        self.assertEqual(normalise_section_id("06.07."), "6.7")
        with self.assertRaises(ValueError):
            normalise_section_id("five")

    def test_outline_unique_and_lookup(self):
        ids = [s for s, _, _, _ in SPAP_OUTLINE]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(outline_section("<5.7>")["condition"], "suppliers")
        with self.assertRaises(ValueError):
            outline_section("9")

    def test_category_rejects_unknown(self):
        self.assertEqual(normalise_category(" c "), "C")
        with self.assertRaises(ValueError):
            normalise_category("E")


class AssessPlanTests(unittest.TestCase):
    def test_full_plan_complete(self):
        res = assess_spap(_full_plan())
        self.assertEqual(res["verdict"], "complete")
        self.assertEqual(res["coverage"], 1.0)

    def test_conditional_sections_not_owed_outside_scope(self):
        res = assess_spap(_full_plan())
        self.assertIn("5.7", res["not_owed"])
        self.assertIn("6.7", res["not_owed"])

    def test_scope_turns_conditional_section_on(self):
        res = assess_spap(_full_plan(), scope=["suppliers"])
        self.assertIn("5.7", res["missing"])
        self.assertEqual(res["verdict"], "incomplete")

    def test_thin_section_flagged(self):
        plan = _full_plan()
        plan["5.1"] = "the team is organised"
        res = assess_spap(plan)
        self.assertEqual(res["thin"], ["5.1"])
        self.assertLess(res["coverage"], 1.0)

    def test_unknown_and_duplicate_sections(self):
        plan = _full_plan()
        plan["11"] = FILLER
        self.assertEqual(assess_spap(plan)["unknown"], ["11"])
        with self.assertRaises(ValueError):
            assess_spap({"5.1": FILLER, "<5.1>": FILLER})

    def test_unknown_scope_rejected(self):
        with self.assertRaises(ValueError):
            assess_spap({}, scope=["weather"])


class OrganisationTests(unittest.TestCase):
    def test_sound_organisation(self):
        org = {"spa_lead": "R. Weber", "reports_to": "project manager",
               "development_lead": "L. Costa"}
        self.assertEqual(check_organisation(org), [])

    def test_dual_role_and_reporting_line(self):
        org = {"spa_lead": "L. Costa", "reports_to": "software development lead",
               "development_lead": "L. Costa"}
        codes = {f["code"] for f in check_organisation(org)}
        self.assertEqual(codes, {"dual-role", "reporting-through-development"})

    def test_delegation_without_plan(self):
        org = {"spa_lead": "R. Weber", "reports_to": "project manager",
               "delegated_to_suppliers": ["Acme", "Beta"], "supplier_plans": ["Acme"]}
        codes = [f["code"] for f in check_organisation(org)]
        self.assertEqual(codes, ["delegation-without-plan"])


class SupplierTests(unittest.TestCase):
    def test_clean_supplier(self):
        sup = {"name": "Acme", "category": "B", "category_flowed": True,
               "requirements_flowed": True, "plan_received": True,
               "pre_award_assessed": True, "monitoring": "reviews"}
        self.assertEqual(check_supplier_control([sup], "B"), {"Acme": []})

    def test_weak_supplier_findings(self):
        sup = {"name": "Beta", "category": "C", "monitoring": "reports"}
        found = check_supplier_control([sup], "B")["Beta"]
        self.assertTrue(any("less strict" in f for f in found))
        self.assertTrue(any("plan not received" in f for f in found))
        self.assertTrue(any("below 'reviews'" in f for f in found))

    def test_duplicate_supplier_rejected(self):
        with self.assertRaises(ValueError):
            check_supplier_control([{"name": "X"}, {"name": "X"}], "C")


class ToolTests(unittest.TestCase):
    def test_category_a_code_generator_needs_qualification(self):
        res = assess_tools([{"name": "gen", "role": "generates-code",
                             "justified": True}], "A")
        self.assertEqual(res[0]["impact"], "executable")
        self.assertTrue(any("qualification" in f for f in res[0]["findings"]))

    def test_category_d_needs_prior_use_only(self):
        res = assess_tools([{"name": "cc", "role": "compiles", "justified": True,
                             "previously_used": True}], "D")
        self.assertEqual(res[0]["findings"], [])

    def test_indirect_tool_needs_only_justification(self):
        res = assess_tools([{"name": "wiki", "role": "documents"}], "A")
        self.assertEqual(res[0]["findings"], ["no justification of suitability in the plan"])

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            assess_tools([{"name": "x", "role": "decorates"}], "B")


class MaturityTests(unittest.TestCase):
    def test_maturity_by_review(self):
        self.assertEqual(plan_maturity_due("SRR"), "issued")
        self.assertEqual(plan_maturity_due("critical design review"), "updated")
        with self.assertRaises(ValueError):
            plan_maturity_due("xyz")


if __name__ == "__main__":
    unittest.main()
