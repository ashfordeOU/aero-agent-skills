"""
Stdlib unittest for e1006_char_tolerance_logic.
Run: python3 test_e1006_char_tolerance.py
"""

import unittest

from e1006_char_tolerance_logic import (
    Requirement,
    audit_requirements,
    check_tolerance_stated,
    requirement_from_bounds,
    tolerance_bounds,
)


class TestCheckToleranceStated(unittest.TestCase):

    def test_qualitative_requirement_passes(self):
        req = Requirement("REQ-001", is_quantitative=False)
        ok, reason = check_tolerance_stated(req)
        self.assertTrue(ok)
        self.assertIn("qualitative", reason)

    def test_quantitative_symmetric_tolerance_passes(self):
        req = Requirement("REQ-002", True, nominal=100.0, plus_tol=5.0, minus_tol=5.0)
        ok, reason = check_tolerance_stated(req)
        self.assertTrue(ok)
        self.assertEqual(reason, "tolerance complete")

    def test_quantitative_asymmetric_tolerance_passes(self):
        req = Requirement("REQ-003", True, nominal=50.0, plus_tol=2.0, minus_tol=1.0)
        ok, reason = check_tolerance_stated(req)
        self.assertTrue(ok)

    def test_quantitative_zero_tolerance_passes(self):
        req = Requirement("REQ-004", True, nominal=5.0, plus_tol=0.0, minus_tol=0.0)
        ok, reason = check_tolerance_stated(req)
        self.assertTrue(ok)

    def test_quantitative_missing_both_tolerances_fails(self):
        req = Requirement("REQ-005", True, nominal=200.0)
        ok, reason = check_tolerance_stated(req)
        self.assertFalse(ok)
        self.assertIn("missing", reason.lower())

    def test_quantitative_missing_plus_tolerance_fails(self):
        req = Requirement("REQ-006", True, nominal=10.0, minus_tol=1.0)
        ok, reason = check_tolerance_stated(req)
        self.assertFalse(ok)
        self.assertIn("plus-tolerance", reason)

    def test_quantitative_missing_minus_tolerance_fails(self):
        req = Requirement("REQ-007", True, nominal=10.0, plus_tol=1.0)
        ok, reason = check_tolerance_stated(req)
        self.assertFalse(ok)
        self.assertIn("minus-tolerance", reason)

    def test_negative_plus_tolerance_fails(self):
        req = Requirement("REQ-008", True, nominal=10.0, plus_tol=-1.0, minus_tol=1.0)
        ok, reason = check_tolerance_stated(req)
        self.assertFalse(ok)
        self.assertIn("negative", reason)

    def test_negative_minus_tolerance_fails(self):
        req = Requirement("REQ-009", True, nominal=10.0, plus_tol=1.0, minus_tol=-0.5)
        ok, reason = check_tolerance_stated(req)
        self.assertFalse(ok)
        self.assertIn("negative", reason)

    def test_non_requirement_argument_raises(self):
        with self.assertRaises(TypeError):
            check_tolerance_stated({"req_id": "REQ-X"})


class TestAuditRequirements(unittest.TestCase):

    def test_empty_list_is_compliant(self):
        result = audit_requirements([])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["failing"], 0)
        self.assertEqual(result["findings"], [])

    def test_all_passing_is_compliant(self):
        reqs = [
            Requirement("REQ-A", True, 100.0, 5.0, 5.0),
            Requirement("REQ-B", False),
        ]
        result = audit_requirements(reqs)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["passing"], 2)
        self.assertEqual(result["failing"], 0)

    def test_one_failing_marks_non_compliant(self):
        reqs = [
            Requirement("REQ-C", True, 100.0, 5.0, 5.0),
            Requirement("REQ-D", True, 200.0),
        ]
        result = audit_requirements(reqs)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["failing"], 1)
        self.assertEqual(result["findings"][0]["id"], "REQ-D")

    def test_multiple_failures_all_reported(self):
        reqs = [
            Requirement("REQ-E", True, 10.0),
            Requirement("REQ-F", True, 20.0, plus_tol=1.0),
            Requirement("REQ-G", True, 30.0, 2.0, 2.0),
        ]
        result = audit_requirements(reqs)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["failing"], 2)
        self.assertEqual(result["passing"], 1)
        failing_ids = {f["id"] for f in result["findings"]}
        self.assertIn("REQ-E", failing_ids)
        self.assertIn("REQ-F", failing_ids)
        self.assertNotIn("REQ-G", failing_ids)

    def test_findings_contain_reason(self):
        reqs = [Requirement("REQ-H", True, 5.0, plus_tol=1.0, minus_tol=-2.0)]
        result = audit_requirements(reqs)
        self.assertEqual(result["failing"], 1)
        self.assertIn("reason", result["findings"][0])

    def test_non_list_argument_raises(self):
        with self.assertRaises(TypeError):
            audit_requirements("not-a-list")


class TestToleranceBounds(unittest.TestCase):

    def test_symmetric_bounds(self):
        lo, hi = tolerance_bounds(100.0, 5.0, 5.0)
        self.assertAlmostEqual(lo, 95.0)
        self.assertAlmostEqual(hi, 105.0)

    def test_asymmetric_bounds(self):
        lo, hi = tolerance_bounds(10.0, 2.0, 1.0)
        self.assertAlmostEqual(lo, 9.0)
        self.assertAlmostEqual(hi, 12.0)

    def test_zero_tolerance_yields_point_bounds(self):
        lo, hi = tolerance_bounds(42.0, 0.0, 0.0)
        self.assertAlmostEqual(lo, 42.0)
        self.assertAlmostEqual(hi, 42.0)

    def test_negative_plus_tolerance_raises(self):
        with self.assertRaises(ValueError):
            tolerance_bounds(10.0, -1.0, 1.0)

    def test_negative_minus_tolerance_raises(self):
        with self.assertRaises(ValueError):
            tolerance_bounds(10.0, 1.0, -0.5)


class TestRequirementFromBounds(unittest.TestCase):

    def test_builds_symmetric_requirement(self):
        req = requirement_from_bounds("REQ-X", 90.0, 110.0)
        self.assertAlmostEqual(req.nominal, 100.0)
        self.assertAlmostEqual(req.plus_tol, 10.0)
        self.assertAlmostEqual(req.minus_tol, 10.0)
        self.assertTrue(req.is_quantitative)

    def test_equal_bounds_yield_zero_tolerance(self):
        req = requirement_from_bounds("REQ-Y", 50.0, 50.0)
        self.assertAlmostEqual(req.nominal, 50.0)
        self.assertAlmostEqual(req.plus_tol, 0.0)
        self.assertAlmostEqual(req.minus_tol, 0.0)

    def test_inverted_bounds_raise(self):
        with self.assertRaises(ValueError):
            requirement_from_bounds("REQ-Z", 110.0, 90.0)

    def test_derived_requirement_passes_audit(self):
        req = requirement_from_bounds("REQ-W", 95.0, 105.0)
        ok, _ = check_tolerance_stated(req)
        self.assertTrue(ok)


class TestRequirementConstruction(unittest.TestCase):

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            Requirement("", True, 10.0)

    def test_quantitative_without_nominal_raises(self):
        with self.assertRaises(ValueError):
            Requirement("REQ-Z", True)

    def test_qualitative_without_nominal_is_valid(self):
        req = Requirement("REQ-QA", is_quantitative=False)
        self.assertIsNone(req.nominal)

    def test_req_id_stored_correctly(self):
        req = Requirement("REQ-ID-CHECK", True, 1.0, 0.1, 0.1)
        self.assertEqual(req.req_id, "REQ-ID-CHECK")


if __name__ == "__main__":
    unittest.main()
