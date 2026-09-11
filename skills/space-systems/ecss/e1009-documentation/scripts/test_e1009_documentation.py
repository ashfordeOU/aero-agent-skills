import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1009_documentation_logic import (
    validate_cs_entry,
    check_axis_completeness,
    check_cs_id_uniqueness,
    check_lifecycle_transition,
    check_phase_coverage,
    validate_csd,
    compute_csd_readiness_score,
)


def _make_valid_entry(cs_id="CSF-001"):
    return {
        "cs_id": cs_id,
        "name": "Spacecraft Body Frame",
        "origin": "Center of mass of the spacecraft",
        "axes": {
            "x": "Aligned with the spacecraft longitudinal axis pointing forward",
            "y": "Perpendicular to x in the principal plane pointing port",
            "z": "Completes the right-hand triad pointing nadir",
        },
        "reference_frame": "ECI (Earth-Centered Inertial)",
        "applicable_phases": ["Phase B", "Phase C", "Phase D"],
        "status": "approved",
    }


def _make_valid_csd(entries=None):
    if entries is None:
        entries = [_make_valid_entry("CSF-001"), _make_valid_entry("CSF-002")]
    return {
        "doc_id": "CSD-SC-001",
        "revision": "A",
        "lifecycle_state": "approved",
        "entries": entries,
    }


class TestValidateCsEntry(unittest.TestCase):

    def test_valid_entry_returns_no_issues(self):
        self.assertEqual(validate_cs_entry(_make_valid_entry()), [])

    def test_missing_cs_id_reported(self):
        entry = _make_valid_entry()
        del entry["cs_id"]
        issues = validate_cs_entry(entry)
        self.assertTrue(any("cs_id" in i for i in issues))

    def test_missing_origin_reported(self):
        entry = _make_valid_entry()
        del entry["origin"]
        issues = validate_cs_entry(entry)
        self.assertTrue(any("origin" in i for i in issues))

    def test_missing_axes_reported(self):
        entry = _make_valid_entry()
        del entry["axes"]
        issues = validate_cs_entry(entry)
        self.assertTrue(any("axes" in i for i in issues))

    def test_missing_reference_frame_reported(self):
        entry = _make_valid_entry()
        del entry["reference_frame"]
        issues = validate_cs_entry(entry)
        self.assertTrue(any("reference_frame" in i for i in issues))

    def test_invalid_status_reported(self):
        entry = _make_valid_entry()
        entry["status"] = "obsolete"
        issues = validate_cs_entry(entry)
        self.assertTrue(any("status" in i for i in issues))

    def test_empty_applicable_phases_reported(self):
        entry = _make_valid_entry()
        entry["applicable_phases"] = []
        issues = validate_cs_entry(entry)
        self.assertTrue(any("applicable_phases" in i for i in issues))

    def test_non_list_applicable_phases_reported(self):
        entry = _make_valid_entry()
        entry["applicable_phases"] = "Phase B"
        issues = validate_cs_entry(entry)
        self.assertTrue(any("applicable_phases" in i for i in issues))

    def test_empty_cs_id_string_reported(self):
        entry = _make_valid_entry()
        entry["cs_id"] = "   "
        issues = validate_cs_entry(entry)
        self.assertTrue(any("cs_id" in i for i in issues))

    def test_non_dict_entry_reported(self):
        issues = validate_cs_entry("not a dict")
        self.assertGreater(len(issues), 0)

    def test_all_valid_statuses_accepted(self):
        for status in ("draft", "review", "approved", "superseded"):
            entry = _make_valid_entry()
            entry["status"] = status
            self.assertEqual(validate_cs_entry(entry), [],
                             msg=f"status '{status}' should be valid")


class TestCheckAxisCompleteness(unittest.TestCase):

    def test_complete_axes_returns_no_issues(self):
        axes = {
            "x": "Forward along longitudinal axis",
            "y": "Port side perpendicular",
            "z": "Nadir completing the right-hand triad",
        }
        self.assertEqual(check_axis_completeness(axes), [])

    def test_missing_z_axis_reported(self):
        axes = {"x": "Forward", "y": "Port"}
        issues = check_axis_completeness(axes)
        self.assertTrue(any("z" in i for i in issues))

    def test_missing_y_axis_reported(self):
        axes = {"x": "Forward", "z": "Nadir"}
        issues = check_axis_completeness(axes)
        self.assertTrue(any("y" in i for i in issues))

    def test_empty_string_axis_definition_reported(self):
        axes = {"x": "Forward", "y": "", "z": "Nadir"}
        issues = check_axis_completeness(axes)
        self.assertTrue(any("'y'" in i for i in issues))

    def test_whitespace_only_axis_definition_reported(self):
        axes = {"x": "Forward", "y": "Port", "z": "   "}
        issues = check_axis_completeness(axes)
        self.assertTrue(any("'z'" in i for i in issues))

    def test_non_dict_axes_reported(self):
        issues = check_axis_completeness(["x", "y", "z"])
        self.assertGreater(len(issues), 0)


class TestCheckCsIdUniqueness(unittest.TestCase):

    def test_unique_ids_returns_empty_list(self):
        entries = [_make_valid_entry("CSF-001"), _make_valid_entry("CSF-002")]
        self.assertEqual(check_cs_id_uniqueness(entries), [])

    def test_duplicate_id_returned(self):
        entries = [_make_valid_entry("CSF-001"), _make_valid_entry("CSF-001")]
        duplicates = check_cs_id_uniqueness(entries)
        self.assertIn("CSF-001", duplicates)

    def test_no_entries_returns_empty_list(self):
        self.assertEqual(check_cs_id_uniqueness([]), [])

    def test_three_duplicates_all_returned(self):
        entries = [_make_valid_entry("CSF-001")] * 3
        duplicates = check_cs_id_uniqueness(entries)
        self.assertIn("CSF-001", duplicates)


class TestCheckLifecycleTransition(unittest.TestCase):

    def test_draft_to_review_allowed(self):
        self.assertTrue(check_lifecycle_transition("draft", "review"))

    def test_review_to_approved_allowed(self):
        self.assertTrue(check_lifecycle_transition("review", "approved"))

    def test_review_to_draft_allowed_for_rework(self):
        self.assertTrue(check_lifecycle_transition("review", "draft"))

    def test_approved_to_superseded_allowed(self):
        self.assertTrue(check_lifecycle_transition("approved", "superseded"))

    def test_draft_to_superseded_allowed(self):
        self.assertTrue(check_lifecycle_transition("draft", "superseded"))

    def test_approved_to_draft_not_allowed(self):
        self.assertFalse(check_lifecycle_transition("approved", "draft"))

    def test_draft_to_approved_skip_not_allowed(self):
        self.assertFalse(check_lifecycle_transition("draft", "approved"))

    def test_superseded_to_approved_not_allowed(self):
        self.assertFalse(check_lifecycle_transition("superseded", "approved"))

    def test_unrecognized_from_state_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_lifecycle_transition("unknown", "draft")

    def test_unrecognized_to_state_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_lifecycle_transition("draft", "unknown")


class TestCheckPhaseCoverage(unittest.TestCase):

    def test_all_required_phases_covered_returns_empty(self):
        entries = [_make_valid_entry()]
        missing = check_phase_coverage(entries, ["Phase B", "Phase C", "Phase D"])
        self.assertEqual(missing, set())

    def test_uncovered_phase_returned(self):
        entries = [_make_valid_entry()]
        missing = check_phase_coverage(entries, ["Phase A", "Phase B"])
        self.assertIn("Phase A", missing)

    def test_empty_entries_all_phases_uncovered(self):
        missing = check_phase_coverage([], ["Phase B", "Phase C"])
        self.assertEqual(missing, {"Phase B", "Phase C"})

    def test_partial_coverage_returns_only_missing(self):
        entries = [_make_valid_entry()]
        missing = check_phase_coverage(entries, ["Phase B", "Phase E"])
        self.assertIn("Phase E", missing)
        self.assertNotIn("Phase B", missing)


class TestValidateCsd(unittest.TestCase):

    def test_valid_csd_is_valid(self):
        result = validate_csd(_make_valid_csd())
        self.assertTrue(result["valid"])
        self.assertEqual(result["doc_issues"], [])
        self.assertEqual(result["entry_issues"], {})
        self.assertEqual(result["duplicate_ids"], [])

    def test_duplicate_entry_ids_fail(self):
        csd = _make_valid_csd(entries=[_make_valid_entry("CSF-001"),
                                        _make_valid_entry("CSF-001")])
        result = validate_csd(csd)
        self.assertFalse(result["valid"])
        self.assertIn("CSF-001", result["duplicate_ids"])

    def test_missing_doc_id_reported(self):
        csd = _make_valid_csd()
        del csd["doc_id"]
        result = validate_csd(csd)
        self.assertFalse(result["valid"])
        self.assertTrue(any("doc_id" in i for i in result["doc_issues"]))

    def test_missing_lifecycle_state_reported(self):
        csd = _make_valid_csd()
        del csd["lifecycle_state"]
        result = validate_csd(csd)
        self.assertFalse(result["valid"])

    def test_invalid_lifecycle_state_reported(self):
        csd = _make_valid_csd()
        csd["lifecycle_state"] = "locked"
        result = validate_csd(csd)
        self.assertFalse(result["valid"])
        self.assertTrue(any("lifecycle_state" in i for i in result["doc_issues"]))

    def test_invalid_entry_surfaces_in_entry_issues(self):
        bad_entry = _make_valid_entry("CSF-BAD")
        del bad_entry["origin"]
        csd = _make_valid_csd(entries=[bad_entry])
        result = validate_csd(csd)
        self.assertFalse(result["valid"])
        self.assertIn("CSF-BAD", result["entry_issues"])

    def test_non_dict_csd_fails_gracefully(self):
        result = validate_csd("not a dict")
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["doc_issues"]), 0)


class TestComputeCsdReadinessScore(unittest.TestCase):

    def test_empty_dict_returns_low_score(self):
        score = compute_csd_readiness_score({})
        self.assertLess(score, 30)

    def test_approved_csd_with_valid_entries_returns_high_score(self):
        score = compute_csd_readiness_score(_make_valid_csd())
        self.assertGreaterEqual(score, 80)

    def test_draft_csd_returns_lower_than_approved(self):
        draft = _make_valid_csd()
        draft["lifecycle_state"] = "draft"
        approved = _make_valid_csd()
        self.assertLess(
            compute_csd_readiness_score(draft),
            compute_csd_readiness_score(approved),
        )

    def test_score_never_exceeds_100(self):
        csd = _make_valid_csd(
            entries=[_make_valid_entry(f"CSF-{i:03d}") for i in range(20)]
        )
        self.assertLessEqual(compute_csd_readiness_score(csd), 100)

    def test_none_returns_zero(self):
        self.assertEqual(compute_csd_readiness_score(None), 0)

    def test_csd_with_no_entries_scores_below_full(self):
        csd = _make_valid_csd(entries=[])
        score = compute_csd_readiness_score(csd)
        self.assertLess(score, 100)


if __name__ == "__main__":
    unittest.main()
