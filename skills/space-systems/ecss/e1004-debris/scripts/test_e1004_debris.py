#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 10.2.2.1 debris flux model selection.

Exercises scripts/e1004_debris_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a mission envelope must be
complete and sane before use; a model is only selected when its declared
envelope fully covers the mission envelope on every field; a mandated
family further restricts eligibility; among eligible candidates selection
is deterministic; a model run request must carry ascending positive
diameter thresholds, a positive exposure duration, and a surface id; and a
prior result needs re-assessment once the mission epoch exceeds the
model's declared validity or the orbit regime changed.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1004_debris_logic import (
    build_run_request,
    envelope_covers,
    needs_reassessment,
    select_model,
    validate_envelope,
)


def make_envelope(altitude=(400, 800), inclination=(0, 98), epoch=(2025, 2035), diameter=(1, 100)):
    return {
        "altitude_km": altitude,
        "inclination_deg": inclination,
        "epoch_year": epoch,
        "diameter_mm": diameter,
    }


class TestValidateEnvelope(unittest.TestCase):
    def test_complete_envelope_has_no_issues(self):
        self.assertEqual(validate_envelope(make_envelope()), [])

    def test_missing_field_is_flagged(self):
        envelope = make_envelope()
        del envelope["diameter_mm"]
        issues = validate_envelope(envelope)
        self.assertTrue(any("missing envelope field" in issue for issue in issues))

    def test_inverted_range_is_flagged(self):
        envelope = make_envelope(altitude=(800, 400))
        issues = validate_envelope(envelope)
        self.assertTrue(any("greater than max" in issue for issue in issues))


class TestEnvelopeCovers(unittest.TestCase):
    def test_model_envelope_covers_mission_envelope(self):
        model_envelope = make_envelope(altitude=(200, 40000), inclination=(0, 180), epoch=(2020, 2040), diameter=(0.001, 10000))
        self.assertEqual(envelope_covers(model_envelope, make_envelope()), [])

    def test_narrow_model_envelope_reports_gap(self):
        model_envelope = make_envelope(epoch=(2010, 2020))
        gaps = envelope_covers(model_envelope, make_envelope(epoch=(2025, 2035)))
        self.assertTrue(any("epoch_year" in gap for gap in gaps))


class TestSelectModel(unittest.TestCase):
    def setUp(self):
        self.wide_master = {
            "name": "MASTER-2025",
            "family": "MASTER",
            "envelope": make_envelope(altitude=(200, 40000), inclination=(0, 180), epoch=(2020, 2040), diameter=(0.001, 10000)),
        }
        self.wide_ordem = {
            "name": "ORDEM-3.2",
            "family": "ORDEM",
            "envelope": make_envelope(altitude=(200, 40000), inclination=(0, 180), epoch=(2020, 2040), diameter=(0.001, 10000)),
        }
        self.narrow_epoch = {
            "name": "MASTER-2009",
            "family": "MASTER",
            "envelope": make_envelope(epoch=(2005, 2015)),
        }

    def test_selects_alphabetically_first_covering_candidate(self):
        name, issues = select_model(
            [self.wide_ordem, self.wide_master], make_envelope()
        )
        self.assertEqual(issues, [])
        self.assertEqual(name, "MASTER-2025")

    def test_mandated_family_restricts_choice(self):
        name, issues = select_model(
            [self.wide_ordem, self.wide_master], make_envelope(), mandated_family="ORDEM"
        )
        self.assertEqual(issues, [])
        self.assertEqual(name, "ORDEM-3.2")

    def test_no_covering_candidate_reports_issue(self):
        name, issues = select_model([self.narrow_epoch], make_envelope())
        self.assertIsNone(name)
        self.assertTrue(issues)

    def test_invalid_mission_envelope_short_circuits(self):
        bad_envelope = make_envelope(altitude=(800, 400))
        name, issues = select_model([self.wide_master], bad_envelope)
        self.assertIsNone(name)
        self.assertTrue(any("greater than max" in issue for issue in issues))

    def test_mandated_family_with_no_match_reports_issue(self):
        name, issues = select_model(
            [self.wide_master], make_envelope(), mandated_family="ORDEM"
        )
        self.assertIsNone(name)
        self.assertTrue(any("mandated family" in issue for issue in issues))


class TestBuildRunRequest(unittest.TestCase):
    def test_complete_request_is_built(self):
        request, issues = build_run_request([1.0, 10.0, 100.0], 3650, "spacecraft-bus")
        self.assertEqual(issues, [])
        self.assertEqual(
            request,
            {
                "diameter_thresholds_mm": [1.0, 10.0, 100.0],
                "exposure_days": 3650,
                "surface_id": "spacecraft-bus",
            },
        )

    def test_empty_thresholds_is_flagged(self):
        request, issues = build_run_request([], 3650, "spacecraft-bus")
        self.assertIsNone(request)
        self.assertTrue(any("at least one threshold" in issue for issue in issues))

    def test_non_positive_threshold_is_flagged(self):
        request, issues = build_run_request([0, 10], 3650, "spacecraft-bus")
        self.assertIsNone(request)
        self.assertTrue(any("strictly positive" in issue for issue in issues))

    def test_unordered_thresholds_is_flagged(self):
        request, issues = build_run_request([10, 1], 3650, "spacecraft-bus")
        self.assertIsNone(request)
        self.assertTrue(any("ascending order" in issue for issue in issues))

    def test_non_positive_exposure_is_flagged(self):
        request, issues = build_run_request([1, 10], 0, "spacecraft-bus")
        self.assertIsNone(request)
        self.assertTrue(any("exposure_days" in issue for issue in issues))

    def test_missing_surface_id_is_flagged(self):
        request, issues = build_run_request([1, 10], 3650, "")
        self.assertIsNone(request)
        self.assertTrue(any("surface_id" in issue for issue in issues))


class TestNeedsReassessment(unittest.TestCase):
    def test_epoch_exceeded_triggers_reassessment(self):
        self.assertTrue(
            needs_reassessment(model_epoch_max_year=2035, mission_end_year=2040, orbit_changed=False)
        )

    def test_orbit_change_triggers_reassessment(self):
        self.assertTrue(
            needs_reassessment(model_epoch_max_year=2040, mission_end_year=2035, orbit_changed=True)
        )

    def test_within_epoch_no_orbit_change_does_not_trigger(self):
        self.assertFalse(
            needs_reassessment(model_epoch_max_year=2040, mission_end_year=2035, orbit_changed=False)
        )


if __name__ == "__main__":
    unittest.main()
