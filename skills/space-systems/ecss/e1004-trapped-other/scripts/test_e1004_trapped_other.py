#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 9.2 trapped-radiation
environment handling for non-LEO/GEO/MEO orbits (HEO, GTO,
interplanetary transfer).

Exercises scripts/e1004_trapped_other_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - an orbit whose
perigee/apogee lie wholly within the LEO, MEO, or GEO band raises and
redirects to the dedicated sibling leaf, while a GTO/HEO/unbounded-
apogee orbit categorizes into exactly "gto", "heo", or
"interplanetary_transfer"; a radial distance splits into the trapped
domain or the interplanetary domain against the nominal or storm-
compressed magnetopause standoff distance, and a negative distance or
dwell raises; trajectory segments split into trapped vs interplanetary
groups without dropping any segment; both proton and electron coverage
are required wherever trapped-domain dwell is nonzero, and missing
coverage is flagged only then; the assessment is compliant only when
segments were supplied and no coverage finding remains.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_trapped_other_logic as to  # noqa: E402


class ClassifyOrbitRegimeTest(unittest.TestCase):
    def test_gto_categorized(self):
        self.assertEqual(to.classify_orbit_regime(300.0, 35786.0), "gto")

    def test_heo_categorized(self):
        self.assertEqual(to.classify_orbit_regime(500.0, 60000.0), "heo")

    def test_interplanetary_transfer_unbounded_apogee(self):
        self.assertEqual(
            to.classify_orbit_regime(300.0, None), "interplanetary_transfer"
        )

    def test_wholly_leo_raises(self):
        with self.assertRaises(ValueError):
            to.classify_orbit_regime(400.0, 800.0)

    def test_wholly_meo_raises(self):
        with self.assertRaises(ValueError):
            to.classify_orbit_regime(10000.0, 20000.0)

    def test_wholly_geo_raises(self):
        with self.assertRaises(ValueError):
            to.classify_orbit_regime(35700.0, 35850.0)

    def test_apogee_below_perigee_raises(self):
        with self.assertRaises(ValueError):
            to.classify_orbit_regime(40000.0, 300.0)

    def test_negative_perigee_raises(self):
        with self.assertRaises(ValueError):
            to.classify_orbit_regime(-1.0, 40000.0)


class MagnetopauseStandoffTest(unittest.TestCase):
    def test_nominal_standoff(self):
        self.assertAlmostEqual(
            to.magnetopause_standoff_km(False),
            to.NOMINAL_MAGNETOPAUSE_STANDOFF_RE * to.EARTH_RADIUS_KM,
        )

    def test_compressed_standoff_is_smaller(self):
        self.assertLess(
            to.magnetopause_standoff_km(True),
            to.magnetopause_standoff_km(False),
        )


class ClassifyDomainTest(unittest.TestCase):
    def test_inside_nominal_standoff_is_trapped(self):
        self.assertEqual(
            to.classify_domain(5 * to.EARTH_RADIUS_KM, storm_compressed=False),
            to.TRAPPED_DOMAIN,
        )

    def test_beyond_nominal_standoff_is_interplanetary(self):
        self.assertEqual(
            to.classify_domain(12 * to.EARTH_RADIUS_KM, storm_compressed=False),
            to.INTERPLANETARY_DOMAIN,
        )

    def test_compression_can_flip_domain(self):
        distance_km = 8 * to.EARTH_RADIUS_KM
        self.assertEqual(
            to.classify_domain(distance_km, storm_compressed=False),
            to.TRAPPED_DOMAIN,
        )
        self.assertEqual(
            to.classify_domain(distance_km, storm_compressed=True),
            to.INTERPLANETARY_DOMAIN,
        )

    def test_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            to.classify_domain(-1.0)


class SplitTrajectorySegmentsTest(unittest.TestCase):
    def test_splits_without_dropping_segments(self):
        segments = [
            {"radial_distance_km": 2 * to.EARTH_RADIUS_KM, "dwell_seconds": 100.0},
            {"radial_distance_km": 15 * to.EARTH_RADIUS_KM, "dwell_seconds": 200.0},
            {"radial_distance_km": 4 * to.EARTH_RADIUS_KM, "dwell_seconds": 50.0},
        ]
        trapped, interplanetary = to.split_trajectory_segments(segments)
        self.assertEqual(len(trapped) + len(interplanetary), len(segments))
        self.assertEqual(len(trapped), 2)
        self.assertEqual(len(interplanetary), 1)

    def test_negative_dwell_raises(self):
        segments = [{"radial_distance_km": 1.0, "dwell_seconds": -5.0}]
        with self.assertRaises(ValueError):
            to.split_trajectory_segments(segments)

    def test_empty_segments_returns_empty_groups(self):
        trapped, interplanetary = to.split_trajectory_segments([])
        self.assertEqual(trapped, [])
        self.assertEqual(interplanetary, [])


class RequiredSpeciesCoverageTest(unittest.TestCase):
    def test_gto_requires_both_species(self):
        self.assertEqual(
            to.required_species_coverage("gto"), frozenset({"proton", "electron"})
        )

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            to.required_species_coverage("leo")


class TrappedOtherAssessmentTest(unittest.TestCase):
    def _mission(self, **overrides):
        mission = {
            "mission_id": "gto-comsat-1",
            "perigee_alt_km": 300.0,
            "apogee_alt_km": 35786.0,
            "storm_compressed": False,
            "segments": [
                {"radial_distance_km": 2 * to.EARTH_RADIUS_KM, "dwell_seconds": 1800.0},
                {"radial_distance_km": 6.6 * to.EARTH_RADIUS_KM, "dwell_seconds": 3600.0},
            ],
            "species_covered": ["proton", "electron"],
        }
        mission.update(overrides)
        return mission

    def test_fully_covered_mission_is_compliant(self):
        assessment = to.trapped_other_assessment(self._mission())
        self.assertEqual(assessment["regime"], "gto")
        self.assertEqual(assessment["findings"], [])
        self.assertTrue(to.is_trapped_other_compliant(assessment))

    def test_missing_species_flagged(self):
        assessment = to.trapped_other_assessment(
            self._mission(species_covered=["proton"])
        )
        self.assertFalse(to.is_trapped_other_compliant(assessment))
        issues = [f["issue"] for f in assessment["findings"]]
        self.assertIn("missing_trapped_species_coverage", issues)

    def test_no_segments_flagged(self):
        assessment = to.trapped_other_assessment(self._mission(segments=[]))
        self.assertFalse(to.is_trapped_other_compliant(assessment))
        issues = [f["issue"] for f in assessment["findings"]]
        self.assertIn("no_trajectory_segments_supplied", issues)

    def test_interplanetary_segments_counted_not_dropped(self):
        mission = self._mission(
            apogee_alt_km=None,
            segments=[
                {"radial_distance_km": 2 * to.EARTH_RADIUS_KM, "dwell_seconds": 1800.0},
                {"radial_distance_km": 50 * to.EARTH_RADIUS_KM, "dwell_seconds": 90000.0},
            ],
        )
        assessment = to.trapped_other_assessment(mission)
        self.assertEqual(assessment["regime"], "interplanetary_transfer")
        self.assertEqual(assessment["excluded_segment_count"], 1)
        self.assertAlmostEqual(assessment["interplanetary_seconds"], 90000.0)
        self.assertAlmostEqual(assessment["trapped_seconds"], 1800.0)

    def test_wholly_leo_mission_raises(self):
        with self.assertRaises(ValueError):
            to.trapped_other_assessment(
                self._mission(perigee_alt_km=400.0, apogee_alt_km=800.0)
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
