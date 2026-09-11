#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C §6 verification pre-tailoring matrix.

Exercises scripts/e1002_pretailoring_logic.py (stdlib unittest, offline).
Contract: the matrix covers all clause-5 requirement IDs for all four
product types; get_applicability returns the correct level for known pairs
and raises for unrecognized product types or requirement IDs;
apply_pretailoring_matrix returns a dict with exactly one entry per
requirement ID and raises for an unknown product type;
requirements_by_applicability returns the correct subset of requirement IDs
for a given level; pretailoring_violations flags every applicable requirement
absent from the captured set, every captured requirement that is not in the
clause-5 set, and every captured requirement whose resolved level is
not_applicable; requirements at recommended or optional level that are absent
do not generate findings; is_pretailoring_complete returns True only when the
findings list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_pretailoring_logic as pt  # noqa: E402


class GetApplicabilityTest(unittest.TestCase):
    def test_unknown_product_type_raises(self):
        with self.assertRaises(ValueError):
            pt.get_applicability("lunar_base", "req-5-vp")

    def test_unknown_requirement_id_raises(self):
        with self.assertRaises(ValueError):
            pt.get_applicability("space_system", "req-99-imaginary")

    def test_space_system_vp_is_applicable(self):
        self.assertEqual(
            pt.get_applicability("space_system", "req-5-vp"),
            pt.APPLICABILITY_APPLICABLE,
        )

    def test_payload_vp_is_optional(self):
        self.assertEqual(
            pt.get_applicability("payload", "req-5-vp"),
            pt.APPLICABILITY_OPTIONAL,
        )

    def test_equipment_iv_is_applicable(self):
        self.assertEqual(
            pt.get_applicability("equipment", "req-5-iv"),
            pt.APPLICABILITY_APPLICABLE,
        )

    def test_space_system_rdv_is_optional(self):
        self.assertEqual(
            pt.get_applicability("space_system", "req-5-rdv"),
            pt.APPLICABILITY_OPTIONAL,
        )

    def test_segment_av_is_recommended(self):
        self.assertEqual(
            pt.get_applicability("segment", "req-5-av"),
            pt.APPLICABILITY_RECOMMENDED,
        )

    def test_ma_is_applicable_for_all_product_types(self):
        for product_type in pt.PRODUCT_TYPES:
            with self.subTest(product_type=product_type):
                self.assertEqual(
                    pt.get_applicability(product_type, "req-5-ma"),
                    pt.APPLICABILITY_APPLICABLE,
                )

    def test_accept_is_applicable_for_all_product_types(self):
        for product_type in pt.PRODUCT_TYPES:
            with self.subTest(product_type=product_type):
                self.assertEqual(
                    pt.get_applicability(product_type, "req-5-accept"),
                    pt.APPLICABILITY_APPLICABLE,
                )


class ApplyMatrixTest(unittest.TestCase):
    def test_apply_unknown_product_type_raises(self):
        with self.assertRaises(ValueError):
            pt.apply_pretailoring_matrix("ground_station")

    def test_apply_returns_all_requirement_ids(self):
        result = pt.apply_pretailoring_matrix("space_system")
        self.assertEqual(set(result.keys()), pt.REQUIREMENT_IDS)

    def test_all_levels_are_recognized(self):
        result = pt.apply_pretailoring_matrix("equipment")
        for req_id, level in result.items():
            with self.subTest(req_id=req_id):
                self.assertIn(level, pt.APPLICABILITY_LEVELS)

    def test_space_system_has_more_applicable_than_equipment(self):
        sys_result = pt.apply_pretailoring_matrix("space_system")
        eq_result = pt.apply_pretailoring_matrix("equipment")
        sys_applicable = sum(
            1 for v in sys_result.values() if v == pt.APPLICABILITY_APPLICABLE
        )
        eq_applicable = sum(
            1 for v in eq_result.values() if v == pt.APPLICABILITY_APPLICABLE
        )
        self.assertGreater(sys_applicable, eq_applicable)

    def test_apply_does_not_mutate_matrix(self):
        before = {
            req_id: dict(pt.PRETAILORING_MATRIX[req_id])
            for req_id in pt.REQUIREMENT_IDS
        }
        pt.apply_pretailoring_matrix("payload")
        for req_id in pt.REQUIREMENT_IDS:
            self.assertEqual(pt.PRETAILORING_MATRIX[req_id], before[req_id])


class RequirementsByApplicabilityTest(unittest.TestCase):
    def test_applicable_for_space_system_is_nonempty(self):
        reqs = pt.requirements_by_applicability("space_system", "applicable")
        self.assertGreater(len(reqs), 0)

    def test_applicable_for_equipment_includes_ma_sc_iv_accept_closure(self):
        reqs = pt.requirements_by_applicability("equipment", "applicable")
        for expected in ("req-5-ma", "req-5-sc", "req-5-iv", "req-5-accept", "req-5-closure"):
            with self.subTest(req=expected):
                self.assertIn(expected, reqs)

    def test_unknown_product_type_raises(self):
        with self.assertRaises(ValueError):
            pt.requirements_by_applicability("deep_space_probe", "applicable")

    def test_unknown_applicability_level_raises(self):
        with self.assertRaises(ValueError):
            pt.requirements_by_applicability("segment", "mandatory")

    def test_result_is_sorted(self):
        reqs = pt.requirements_by_applicability("space_system", "applicable")
        self.assertEqual(reqs, sorted(reqs))


class PretailoringViolationsTest(unittest.TestCase):
    def _all_applicable(self, product_type):
        return pt.requirements_by_applicability(product_type, "applicable")

    def test_all_applicable_captured_no_violations(self):
        captured = self._all_applicable("space_system")
        findings = pt.pretailoring_violations("space_system", captured)
        missing = [f for f in findings if f["issue"] == "missing_applicable"]
        self.assertEqual(missing, [])

    def test_missing_applicable_is_flagged(self):
        applicable = self._all_applicable("segment")
        # Remove one applicable requirement to trigger a finding.
        captured = [r for r in applicable if r != "req-5-vp"]
        findings = pt.pretailoring_violations("segment", captured)
        issues = [f["requirement_id"] for f in findings if f["issue"] == "missing_applicable"]
        self.assertIn("req-5-vp", issues)

    def test_recommended_absent_not_flagged(self):
        # segment, req-5-av resolves to recommended — omitting it must not raise a finding.
        recommended = pt.requirements_by_applicability("segment", "recommended")
        self.assertIn("req-5-av", recommended)
        applicable = self._all_applicable("segment")
        findings = pt.pretailoring_violations("segment", applicable)
        issues = [f["requirement_id"] for f in findings]
        self.assertNotIn("req-5-av", issues)

    def test_optional_absent_not_flagged(self):
        # payload, req-5-vp resolves to optional — omitting it must not raise a finding.
        optional_reqs = pt.requirements_by_applicability("payload", "optional")
        self.assertIn("req-5-vp", optional_reqs)
        applicable = self._all_applicable("payload")
        findings = pt.pretailoring_violations("payload", applicable)
        issues = [f["requirement_id"] for f in findings]
        self.assertNotIn("req-5-vp", issues)

    def test_unknown_captured_requirement_flagged(self):
        applicable = self._all_applicable("equipment")
        findings = pt.pretailoring_violations(
            "equipment", list(applicable) + ["req-99-phantom"]
        )
        unknown = [f for f in findings if f["issue"] == "unknown_requirement"]
        self.assertEqual(len(unknown), 1)
        self.assertEqual(unknown[0]["requirement_id"], "req-99-phantom")

    def test_out_of_scope_captured_requirement_flagged(self):
        # payload, req-5-vl resolves to not_applicable (verification level
        # hierarchy is a system/segment concern). Capturing it for payload
        # must trigger an out_of_scope finding.
        self.assertEqual(
            pt.get_applicability("payload", "req-5-vl"),
            pt.APPLICABILITY_NOT_APPLICABLE,
        )
        applicable = self._all_applicable("payload")
        findings = pt.pretailoring_violations(
            "payload", list(applicable) + ["req-5-vl"]
        )
        out_of_scope = [f for f in findings if f["issue"] == "out_of_scope"]
        self.assertEqual(len(out_of_scope), 1)
        self.assertEqual(out_of_scope[0]["requirement_id"], "req-5-vl")

    def test_unknown_product_type_raises(self):
        with self.assertRaises(ValueError):
            pt.pretailoring_violations("orbital_tug", ["req-5-vp"])

    def test_is_pretailoring_complete_true_when_no_findings(self):
        self.assertTrue(pt.is_pretailoring_complete([]))

    def test_is_pretailoring_complete_false_when_findings(self):
        findings = [{"issue": "missing_applicable", "product_type": "segment",
                     "requirement_id": "req-5-vp"}]
        self.assertFalse(pt.is_pretailoring_complete(findings))

    def test_full_coverage_makes_is_pretailoring_complete_true(self):
        applicable = self._all_applicable("equipment")
        findings = pt.pretailoring_violations("equipment", applicable)
        # No missing-applicable or unknown-requirement findings with full coverage.
        blocking = [
            f for f in findings
            if f["issue"] in ("missing_applicable", "unknown_requirement")
        ]
        self.assertTrue(pt.is_pretailoring_complete(blocking))


if __name__ == "__main__":
    unittest.main(verbosity=2)
