"""Contract tests for the software criticality and tailoring logic."""

import unittest

from q80_software_criticality_tailoring_logic import (
    APPLICABILITY_EXCEPTIONS,
    CATEGORIES,
    REDUCTION_NOTES,
    REQUIREMENT_IDS,
    applicability,
    assign_category,
    group_summary,
    heading_of,
    normalise_category,
    normalise_requirement_id,
    normalise_severity,
    project_category,
    relaxed_requirements,
    tailoring_matrix,
)


class NormalisationTests(unittest.TestCase):
    def test_category_forms(self):
        self.assertEqual(normalise_category("b"), "B")
        self.assertEqual(normalise_category("Cat-C"), "C")
        self.assertEqual(normalise_category("category D"), "D")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalise_category("E")
        with self.assertRaises(ValueError):
            normalise_category(2)

    def test_severity_forms(self):
        self.assertEqual(normalise_severity("catastrophic"), "I")
        self.assertEqual(normalise_severity(3), "III")
        self.assertEqual(normalise_severity("cat II"), "II")
        self.assertEqual(normalise_severity("negligible"), "IV")
        with self.assertRaises(ValueError):
            normalise_severity("V")

    def test_requirement_id_item_letter_cut(self):
        self.assertEqual(normalise_requirement_id("6.2.3.4a"), "6.2.3.4")
        self.assertEqual(normalise_requirement_id(" 6.2.3.4.a "), "6.2.3.4")
        with self.assertRaises(ValueError):
            normalise_requirement_id("clause six")


class AssignmentTests(unittest.TestCase):
    def test_base_mapping_without_provisions(self):
        got = [assign_category(s)["category"] for s in ("I", "II", "III", "IV")]
        self.assertEqual(got, ["A", "B", "C", "D"])

    def test_provision_lowers_one_step(self):
        res = assign_category("I", ["hardware"])
        self.assertEqual(res["category"], "B")
        self.assertTrue(res["lowered_by_provision"])

    def test_software_provision_constraint(self):
        res = assign_category("II", ["sw"])
        self.assertEqual(res["category"], "C")
        self.assertTrue(any("category B" in c for c in res["constraints"]))

    def test_severity_iv_takes_no_credit(self):
        res = assign_category("IV", ["operational"])
        self.assertEqual(res["category"], "D")
        self.assertFalse(res["lowered_by_provision"])

    def test_software_that_is_the_provision_gets_no_credit(self):
        res = assign_category("III", ["hardware"], provides_provision_for="I")
        self.assertEqual(res["category"], "A")

    def test_unknown_provision_rejected(self):
        with self.assertRaises(ValueError):
            assign_category("I", ["prayer"])


class MatrixTests(unittest.TestCase):
    def test_catalogue_is_ordered_and_unique(self):
        self.assertEqual(len(set(REQUIREMENT_IDS)), len(REQUIREMENT_IDS))
        keys = [[int(p) for p in r.split(".")] for r in REQUIREMENT_IDS]
        self.assertEqual(keys, sorted(keys))

    def test_every_reduced_code_has_a_note(self):
        for rid, code in APPLICABILITY_EXCEPTIONS.items():
            if "R" in code:
                self.assertIn(rid, REDUCTION_NOTES, rid)

    def test_category_a_applies_everything_but_security(self):
        for rid in REQUIREMENT_IDS:
            status = applicability(rid, "A")
            self.assertIn(status, ("applicable", "security-driven"), rid)

    def test_known_category_d_exclusions(self):
        self.assertEqual(applicability("5.7.1", "D"), "not-applicable")
        self.assertEqual(applicability("6.2.3.2", "D"), "not-applicable")
        self.assertEqual(applicability("7.1.8", "D"), "not-applicable")
        self.assertEqual(applicability("5.1.1", "D"), "applicable")

    def test_category_c_drops_independent_verification(self):
        self.assertEqual(applicability("6.2.6.13", "B"), "applicable")
        self.assertEqual(applicability("6.2.6.13", "C"), "not-applicable")

    def test_unknown_requirement_rejected(self):
        with self.assertRaises(ValueError):
            applicability("9.9.9", "A")

    def test_security_rows_follow_sensitivity(self):
        plain = {r["requirement"]: r for r in tailoring_matrix("B")}
        sens = {r["requirement"]: r for r in tailoring_matrix("B", security_sensitive=True)}
        self.assertEqual(plain["6.2.9.1"]["status"], "not-applicable")
        self.assertEqual(sens["6.2.9.1"]["status"], "applicable")

    def test_reduced_rows_carry_notes(self):
        rows = {r["requirement"]: r for r in tailoring_matrix("D")}
        self.assertEqual(rows["6.3.5.3"]["status"], "reduced")
        self.assertIn("sampling", rows["6.3.5.3"]["note"])

    def test_group_summary_verdicts(self):
        groups = {g["heading"]: g for g in group_summary("D")}
        self.assertEqual(groups["5.7.2"]["verdict"], "none")
        self.assertEqual(groups["5.1.1"]["verdict"], "full")
        self.assertEqual(groups["5.1.3"]["verdict"], "partial")

    def test_heading_lookup(self):
        self.assertEqual(heading_of("6.2.3.4")[1], "critical software")
        self.assertEqual(heading_of("7.1.8")[0], "7.1.8")


class RelaxationTests(unittest.TestCase):
    def test_downgrade_lists_relaxations(self):
        rel = relaxed_requirements("B", "C")
        ids = [r["requirement"] for r in rel]
        self.assertIn("6.2.6.13", ids)
        self.assertIn("6.2.3.7", ids)
        self.assertNotIn("5.7.1", ids)

    def test_upgrade_relaxes_nothing(self):
        self.assertEqual(relaxed_requirements("D", "A"), [])

    def test_monotone_across_categories(self):
        total = [len(relaxed_requirements("A", c)) for c in CATEGORIES]
        self.assertEqual(total, sorted(total))


class ProjectCategoryTests(unittest.TestCase):
    def test_highest_component_wins(self):
        res = project_category([
            {"name": "obsw", "category": "B"},
            {"name": "payload", "category": "C"},
        ])
        self.assertEqual(res["product_category"], "B")
        self.assertEqual(res["raised"], ["payload"])
        self.assertEqual(res["per_component"]["payload"], "B")

    def test_partition_keeps_own_category(self):
        res = project_category([
            {"name": "obsw", "category": "B"},
            {"name": "payload", "category": "C"},
        ], partitioned=True)
        self.assertEqual(res["per_component"]["payload"], "C")
        self.assertEqual(res["raised"], [])

    def test_duplicate_and_empty_rejected(self):
        with self.assertRaises(ValueError):
            project_category([])
        with self.assertRaises(ValueError):
            project_category([{"name": "x", "category": "A"}, {"name": "x", "category": "B"}])


if __name__ == "__main__":
    unittest.main()
