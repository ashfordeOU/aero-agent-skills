"""Contract test for the cleanliness requirement flowdown leaf (stdlib unittest)."""

import unittest

from q7001_cleanliness_requirements_flowdown_logic import (
    KIND_MOLECULAR,
    KIND_OBSCURATION,
    ROLE_AIT,
    ROLE_PROCUREMENT,
    assess_flowdown,
    is_at_least_as_strict,
    strictness_ratio,
    validate_carried_clause,
    validate_document,
    validate_requirement,
)


def requirement(rid="CLN-010", **kw):
    record = {
        "id": rid,
        "kind": KIND_MOLECULAR,
        "limit": 1.0,
        "surface": "optical bench mounting face",
    }
    record.update(kw)
    return record


def clause(rid="CLN-010", **kw):
    record = {
        "requirement_id": rid,
        "kind": KIND_MOLECULAR,
        "limit": 1.0,
        "verification_method": "solvent rinse and gravimetric residue",
    }
    record.update(kw)
    return record


def document(did="PO-4471", role=ROLE_PROCUREMENT, clauses=None):
    return {"id": did, "role": role, "clauses": clauses or [clause()]}


def both_documents(**kw):
    return [
        document("PO-4471", ROLE_PROCUREMENT, [clause(**kw)]),
        document("AIT-PR-22", ROLE_AIT, [clause(**kw)]),
    ]


class TestValidateRequirement(unittest.TestCase):
    def test_a_valid_requirement_is_normalized(self):
        norm = validate_requirement(requirement())
        self.assertEqual(norm["id"], "CLN-010")
        self.assertEqual(norm["required_roles"], (ROLE_PROCUREMENT, ROLE_AIT))

    def test_an_unknown_requirement_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(kind="looks-clean-enough"))

    def test_a_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(limit=0.0))

    def test_a_negative_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(limit=-1.0))

    def test_a_blank_id_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement("   "))

    def test_an_unknown_required_role_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(required_roles=["marketing"]))

    def test_a_non_mapping_requirement_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement("CLN-010")


class TestValidateDocument(unittest.TestCase):
    def test_a_valid_document_is_normalized(self):
        norm = validate_document(document())
        self.assertEqual(norm["role"], ROLE_PROCUREMENT)
        self.assertEqual(len(norm["clauses"]), 1)

    def test_an_unknown_document_role_raises(self):
        with self.assertRaises(ValueError):
            validate_document(document(role="hallway-poster"))

    def test_a_document_with_no_clauses_raises(self):
        with self.assertRaises(ValueError):
            validate_document({"id": "PO-1", "role": ROLE_AIT, "clauses": []})

    def test_a_document_carrying_one_requirement_twice_raises(self):
        with self.assertRaises(ValueError):
            validate_document(document(clauses=[clause(), clause()]))

    def test_a_clause_with_a_non_numeric_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_carried_clause(clause(limit="one milligram"))


class TestStrictness(unittest.TestCase):
    def test_an_equal_limit_is_strict_enough(self):
        self.assertTrue(is_at_least_as_strict(1.0, 1.0))

    def test_a_tighter_limit_is_strict_enough(self):
        self.assertTrue(is_at_least_as_strict(0.5, 1.0))

    def test_a_looser_limit_is_not_strict_enough(self):
        self.assertFalse(is_at_least_as_strict(2.0, 1.0))

    def test_a_limit_reassembled_from_thirds_still_counts_as_equal(self):
        carried = 1.0 / 3.0 + 1.0 / 3.0 + 1.0 / 3.0
        self.assertTrue(is_at_least_as_strict(carried, 1.0))

    def test_the_strictness_ratio_of_an_equal_limit_is_one(self):
        self.assertAlmostEqual(strictness_ratio(1.0, 1.0), 1.0, places=9)

    def test_the_strictness_ratio_halves_with_a_halved_limit(self):
        self.assertAlmostEqual(strictness_ratio(0.5, 1.0), 0.5, places=9)


class TestFlowdown(unittest.TestCase):
    def test_a_requirement_in_both_families_is_clear(self):
        report = assess_flowdown([requirement()], both_documents())
        self.assertTrue(report["clear"])
        self.assertEqual(report["verdict"], "flowdown-complete")
        self.assertAlmostEqual(report["coverage_fraction"], 1.0, places=12)

    def test_a_requirement_reaching_nothing_is_a_gap(self):
        report = assess_flowdown(
            [requirement(), requirement("CLN-020")], both_documents()
        )
        self.assertEqual(report["gap_requirement_ids"], ["CLN-020"])
        self.assertIn("requirement-reaches-no-document", report["findings"])
        self.assertAlmostEqual(report["coverage_fraction"], 0.5, places=12)

    def test_a_procurement_only_flowdown_misses_the_ait_family(self):
        report = assess_flowdown([requirement()], [document()])
        self.assertIn("requirement-missing-a-ait-document", report["findings"])
        self.assertEqual(report["verdict"], "flowdown-incomplete")

    def test_an_ait_only_flowdown_misses_procurement(self):
        report = assess_flowdown(
            [requirement()], [document("AIT-PR-22", ROLE_AIT)]
        )
        self.assertIn("requirement-missing-a-procurement-document", report["findings"])

    def test_a_stricter_carried_limit_is_accepted(self):
        report = assess_flowdown([requirement()], both_documents(limit=0.4))
        self.assertTrue(report["clear"])
        self.assertAlmostEqual(
            report["requirements"][0]["tightest_carried_limit"], 0.4, places=12
        )

    def test_a_looser_carried_limit_is_a_relaxation(self):
        report = assess_flowdown([requirement()], both_documents(limit=2.0))
        self.assertIn("carried-limit-looser-than-the-parent", report["findings"])
        self.assertIn("relaxation-carried-without-a-waiver", report["findings"])

    def test_a_waived_relaxation_drops_the_waiver_finding(self):
        report = assess_flowdown(
            [requirement()], both_documents(limit=2.0, waiver_reference="WVR-08")
        )
        self.assertIn("carried-limit-looser-than-the-parent", report["findings"])
        self.assertNotIn("relaxation-carried-without-a-waiver", report["findings"])

    def test_a_clause_with_no_verification_method_is_a_finding(self):
        report = assess_flowdown(
            [requirement()], both_documents(verification_method=None)
        )
        self.assertIn(
            "carried-clause-names-no-verification-method", report["findings"]
        )

    def test_a_clause_for_an_unknown_requirement_is_a_finding(self):
        docs = both_documents()
        docs[0]["clauses"].append(clause("CLN-999"))
        report = assess_flowdown([requirement()], docs)
        self.assertIn(
            "document-carries-a-requirement-no-parent-defines", report["findings"]
        )

    def test_a_clause_changing_the_requirement_kind_is_a_finding(self):
        docs = both_documents()
        docs[0]["clauses"][0]["kind"] = KIND_OBSCURATION
        report = assess_flowdown([requirement()], docs)
        self.assertIn(
            "carried-clause-changes-the-requirement-kind", report["findings"]
        )

    def test_duplicate_requirement_ids_raise(self):
        with self.assertRaises(ValueError):
            assess_flowdown([requirement(), requirement()], both_documents())

    def test_duplicate_document_ids_raise(self):
        with self.assertRaises(ValueError):
            assess_flowdown([requirement()], [document(), document()])

    def test_an_empty_requirement_list_raises(self):
        with self.assertRaises(ValueError):
            assess_flowdown([], both_documents())

    def test_an_empty_document_list_raises(self):
        with self.assertRaises(ValueError):
            assess_flowdown([requirement()], [])

    def test_a_procurement_only_requirement_needs_only_procurement(self):
        report = assess_flowdown(
            [requirement(required_roles=[ROLE_PROCUREMENT])], [document()]
        )
        self.assertTrue(report["clear"])
        self.assertEqual(report["requirements"][0]["missing_roles"], [])


if __name__ == "__main__":
    unittest.main()
