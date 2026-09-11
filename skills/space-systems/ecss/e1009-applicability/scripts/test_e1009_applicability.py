"""
test_e1009_applicability.py

Offline, deterministic unittest suite for e1009_applicability_logic.
Run: python3 test_e1009_applicability.py
Expected output: OK
"""

import sys
import os
import unittest

# Allow running from the scripts/ directory directly
sys.path.insert(0, os.path.dirname(__file__))

from e1009_applicability_logic import (
    CoordinateFrame,
    Finding,
    ApplicabilityReport,
    REQUIRED_DOMAINS,
    VALID_FRAME_TYPES,
    DOMAIN_REQUIRED_TYPES,
    validate_frame,
    check_duplicate_names,
    check_domain_coverage,
    assess_single_domain,
    completeness_gate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_domain_frames() -> list:
    """Return a minimal set of frames that satisfies every §5.3.1 domain."""
    return [
        CoordinateFrame("J2000_MD",    "inertial",    "mission_definition"),
        CoordinateFrame("ECEF_MD",     "earth_fixed", "mission_definition"),
        CoordinateFrame("SC_BODY",     "body",        "engineering"),
        CoordinateFrame("SC_STR",      "structural",  "engineering"),
        CoordinateFrame("SC_BODY_V",   "body",        "verification"),
        CoordinateFrame("J2000_V",     "inertial",    "verification"),
        CoordinateFrame("J2000_OPS",   "inertial",    "operations"),
        CoordinateFrame("ECEF_OPS",    "earth_fixed", "operations"),
        CoordinateFrame("LVLH_OPS",    "orbital",     "operations"),
        CoordinateFrame("J2000_DP",    "inertial",    "data_processing"),
        CoordinateFrame("CAM_BORE",    "instrument",  "data_processing"),
    ]


# ---------------------------------------------------------------------------
# validate_frame
# ---------------------------------------------------------------------------

class TestValidateFrame(unittest.TestCase):

    def test_valid_frame_returns_no_errors(self):
        f = CoordinateFrame("J2000", "inertial", "mission_definition")
        self.assertEqual(validate_frame(f), [])

    def test_empty_name_produces_error(self):
        f = CoordinateFrame("", "inertial", "mission_definition")
        errs = validate_frame(f)
        self.assertTrue(any("name" in e for e in errs))

    def test_whitespace_only_name_produces_error(self):
        f = CoordinateFrame("   ", "inertial", "mission_definition")
        errs = validate_frame(f)
        self.assertTrue(any("name" in e for e in errs))

    def test_unknown_frame_type_produces_error(self):
        f = CoordinateFrame("MYFRAME", "galactic", "engineering")
        errs = validate_frame(f)
        self.assertTrue(any("frame_type" in e for e in errs))

    def test_unknown_domain_produces_error(self):
        f = CoordinateFrame("MYFRAME", "inertial", "manufacturing")
        errs = validate_frame(f)
        self.assertTrue(any("domain" in e for e in errs))

    def test_multiple_errors_returned_together(self):
        f = CoordinateFrame("", "galactic", "manufacturing")
        errs = validate_frame(f)
        self.assertGreaterEqual(len(errs), 2)

    def test_all_valid_frame_types_accepted(self):
        for ftype in VALID_FRAME_TYPES:
            f = CoordinateFrame(f"frame_{ftype}", ftype, "engineering")
            self.assertEqual(validate_frame(f), [],
                             msg=f"frame_type '{ftype}' should be valid")

    def test_all_required_domains_accepted(self):
        for domain in REQUIRED_DOMAINS:
            f = CoordinateFrame(f"frame_{domain}", "inertial", domain)
            self.assertEqual(validate_frame(f), [],
                             msg=f"domain '{domain}' should be valid")


# ---------------------------------------------------------------------------
# check_duplicate_names
# ---------------------------------------------------------------------------

class TestCheckDuplicateNames(unittest.TestCase):

    def test_unique_names_return_no_errors(self):
        frames = [
            CoordinateFrame("A", "inertial", "engineering"),
            CoordinateFrame("B", "body",     "engineering"),
        ]
        self.assertEqual(check_duplicate_names(frames), [])

    def test_duplicate_name_returns_error(self):
        frames = [
            CoordinateFrame("J2000", "inertial", "mission_definition"),
            CoordinateFrame("J2000", "inertial", "verification"),
        ]
        errs = check_duplicate_names(frames)
        self.assertEqual(len(errs), 1)
        self.assertIn("J2000", errs[0])

    def test_triplicate_name_counted_correctly(self):
        frames = [
            CoordinateFrame("X", "body", "engineering"),
            CoordinateFrame("X", "body", "verification"),
            CoordinateFrame("X", "body", "verification"),
        ]
        errs = check_duplicate_names(frames)
        self.assertEqual(len(errs), 1)
        self.assertIn("3", errs[0])


# ---------------------------------------------------------------------------
# check_domain_coverage
# ---------------------------------------------------------------------------

class TestCheckDomainCoverage(unittest.TestCase):

    def test_full_coverage_is_compliant(self):
        report = check_domain_coverage(_all_domain_frames())
        self.assertTrue(report.compliant)
        self.assertEqual(len(report.findings), 0)
        self.assertEqual(sorted(report.covered_domains), sorted(REQUIRED_DOMAINS))
        self.assertEqual(report.missing_domains, [])

    def test_missing_entire_domain_is_not_compliant(self):
        frames = [f for f in _all_domain_frames() if f.domain != "operations"]
        report = check_domain_coverage(frames)
        self.assertFalse(report.compliant)
        self.assertIn("operations", report.missing_domains)

    def test_missing_frame_type_in_domain_is_not_compliant(self):
        # Remove the orbital frame from operations — LVLH_OPS
        frames = [f for f in _all_domain_frames() if f.name != "LVLH_OPS"]
        report = check_domain_coverage(frames)
        self.assertFalse(report.compliant)
        ops_findings = [fn for fn in report.findings if fn.domain == "operations"]
        self.assertTrue(len(ops_findings) > 0)
        self.assertTrue(any("orbital" in fn.issue for fn in ops_findings))

    def test_duplicate_frames_reported_as_error(self):
        frames = _all_domain_frames()
        # Inject a duplicate name — reuse J2000_MD
        frames.append(CoordinateFrame("J2000_MD", "inertial", "verification"))
        # validate_frame will pass (valid frame) so check_domain_coverage runs
        report = check_domain_coverage(frames)
        global_findings = [fn for fn in report.findings if fn.domain == "global"]
        self.assertTrue(len(global_findings) > 0)

    def test_invalid_frame_raises_value_error(self):
        bad = CoordinateFrame("BAD", "unknown_type", "engineering")
        with self.assertRaises(ValueError):
            check_domain_coverage([bad])

    def test_empty_frame_list_missing_all_domains(self):
        report = check_domain_coverage([])
        self.assertFalse(report.compliant)
        self.assertEqual(sorted(report.missing_domains), sorted(REQUIRED_DOMAINS))

    def test_covered_domains_not_in_missing_domains(self):
        report = check_domain_coverage(_all_domain_frames())
        for d in report.covered_domains:
            self.assertNotIn(d, report.missing_domains)


# ---------------------------------------------------------------------------
# assess_single_domain
# ---------------------------------------------------------------------------

class TestAssessSingleDomain(unittest.TestCase):

    def test_valid_domain_with_correct_frames_is_covered(self):
        frames = _all_domain_frames()
        result = assess_single_domain("mission_definition", frames)
        self.assertTrue(result["covered"])
        self.assertEqual(result["missing_types"], [])
        self.assertEqual(result["findings"], [])

    def test_valid_domain_missing_frame_type_not_covered(self):
        # operations needs inertial + earth_fixed + orbital
        frames = [
            CoordinateFrame("J2000_OPS", "inertial",    "operations"),
            CoordinateFrame("ECEF_OPS",  "earth_fixed", "operations"),
            # orbital is absent
        ]
        result = assess_single_domain("operations", frames)
        self.assertFalse(result["covered"])
        self.assertIn("orbital", result["missing_types"])

    def test_domain_with_no_frames_not_covered(self):
        result = assess_single_domain("data_processing", [])
        self.assertFalse(result["covered"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_unknown_domain_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_single_domain("manufacturing", [])

    def test_result_contains_expected_keys(self):
        result = assess_single_domain("engineering", _all_domain_frames())
        for key in ("domain", "covered", "present_types", "missing_types", "findings"):
            self.assertIn(key, result)

    def test_present_types_reflects_actual_frames(self):
        frames = [
            CoordinateFrame("SC_BODY", "body",       "engineering"),
            CoordinateFrame("SC_STR",  "structural", "engineering"),
        ]
        result = assess_single_domain("engineering", frames)
        self.assertIn("body", result["present_types"])
        self.assertIn("structural", result["present_types"])


# ---------------------------------------------------------------------------
# completeness_gate
# ---------------------------------------------------------------------------

class TestCompletenessGate(unittest.TestCase):

    def test_complete_set_passes(self):
        gate = completeness_gate(_all_domain_frames())
        self.assertTrue(gate["pass"])
        self.assertEqual(gate["pre_validation_errors"], [])
        self.assertEqual(gate["gaps"], [])
        self.assertEqual(sorted(gate["covered_domains"]), sorted(REQUIRED_DOMAINS))

    def test_invalid_frame_type_triggers_pre_validation_error(self):
        frames = _all_domain_frames()
        frames.append(CoordinateFrame("BAD_FRAME", "galactic", "engineering"))
        gate = completeness_gate(frames)
        self.assertFalse(gate["pass"])
        self.assertTrue(len(gate["pre_validation_errors"]) > 0)

    def test_missing_domain_appears_in_gaps(self):
        frames = [f for f in _all_domain_frames() if f.domain != "verification"]
        gate = completeness_gate(frames)
        self.assertFalse(gate["pass"])
        self.assertTrue(any("verification" in g for g in gate["gaps"]))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
